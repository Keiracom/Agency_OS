#!/usr/bin/env python3
"""auto_session_recovery.py — KEI-35: detect dead agent tmux sessions + recover.

Implements the verbatim recovery path from ceo_memory key
`orchestration:agent_session_recovery` (Dave directive ts ~1778647600):

  1. `tmux new-session -d -s <callsign> -c <worktree-path>`
  2. `tmux send-keys "claude --resume <session-id> --dangerously-skip-permissions" Enter`
  3. Select option 1 (Resume from summary) for context-budget-respect
  4. Brief the recovered agent via send-keys with current orchestration state

Two-attempt threshold (Dave): orchestrator retries once before escalating to
`#ceo`. State persisted at ~/.local/state/agency-os/session-recovery-attempts.json
so the threshold survives across cycle invocations.

Exit codes:
  0 — happy path OR no dead sessions OR successful recovery OR escalated
  2 — operator misconfig (unexpected — should not occur in normal operation)

This script is invoked by a systemd timer (every minute, peak hours) OR can
be called ad-hoc by Elliot's orchestration tooling.
"""

from __future__ import annotations

import argparse
import logging
import os
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

from src.bot_common.state_store import load_state, resolve_state_path, save_state

logger = logging.getLogger("auto_session_recovery")
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

# Canonical callsign → tmux session name map. Mirrors CALLSIGN_TO_TMUX in
# elliot_polling_loop.py (elliot+max use -bot suffix; clones + aiden bare).
# KEI-69 — nova added so session recovery covers all 7 fleet sessions.
CALLSIGN_TO_TMUX: dict[str, str] = {
    "elliot": "elliottbot",
    "aiden": "aiden",
    "max": "maxbot",
    "atlas": "atlas",
    "orion": "orion",
    "scout": "scout",
    "nova": "nova",
}

# Per-callsign worktree paths. elliot → main; others → -<callsign> suffix.
_WORKTREE_ROOT = "/home/elliotbot/clawd"
CALLSIGN_TO_WORKTREE: dict[str, str] = {
    "elliot": f"{_WORKTREE_ROOT}/Agency_OS",
    "aiden": f"{_WORKTREE_ROOT}/Agency_OS-aiden",
    "max": f"{_WORKTREE_ROOT}/Agency_OS-max",
    "atlas": f"{_WORKTREE_ROOT}/Agency_OS-atlas",
    "orion": f"{_WORKTREE_ROOT}/Agency_OS-orion",
    "scout": f"{_WORKTREE_ROOT}/Agency_OS-scout",
    "nova": f"{_WORKTREE_ROOT}/Agency_OS-nova",
}

CLAUDE_PROJECTS_ROOT = Path.home() / ".claude" / "projects"

_DEFAULT_STATE_PATH = os.path.expanduser("~/.local/state/agency-os/session-recovery-attempts.json")
_STATE_ENV_VAR = "AGENCY_OS_SESSION_RECOVERY_STATE"

# Two-attempt threshold (Dave verbatim): retry once, escalate on second fail.
MAX_RECOVERY_ATTEMPTS = 2
SLACK_RELAY_PATH = "/home/elliotbot/clawd/Agency_OS/scripts/slack_relay.py"


def _state_path() -> Path:
    return resolve_state_path(_STATE_ENV_VAR, _DEFAULT_STATE_PATH)


def _load_state() -> dict[str, dict]:
    return load_state(_state_path())


def _save_state(state: dict[str, dict]) -> None:
    save_state(_state_path(), state, logger, label="recovery-state")


def _alive_sessions() -> set[str]:
    """Return set of currently-attached/detached tmux session names."""
    # Static argv list (no shell, no untrusted interpolation); S603 noqa is the
    # canonical pattern for these in-repo subprocess wrappers.
    try:
        proc = subprocess.run(  # noqa: S603
            ["tmux", "list-sessions", "-F", "#{session_name}"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except (subprocess.TimeoutExpired, OSError) as exc:
        # FileNotFoundError is a subclass of OSError — single catch covers both.
        logger.warning("tmux list-sessions failed: %s", exc)
        return set()
    if proc.returncode != 0:
        # No server running = no sessions = empty set (not an error).
        return set()
    return {line.strip() for line in proc.stdout.splitlines() if line.strip()}


def detect_dead_callsigns() -> list[str]:
    """Return callsigns whose expected tmux session is missing.

    Filtered to callsigns in CALLSIGN_TO_TMUX — any new callsign needs an
    explicit map entry before recovery can run.
    """
    alive = _alive_sessions()
    return [cs for cs, sess in CALLSIGN_TO_TMUX.items() if sess not in alive]


def _project_dir_for(worktree: str) -> Path:
    """Translate a worktree path to its Claude project-dir name.

    Claude Code converts BOTH `/` and `_` to `-` in the project-dir slug — e.g.
    `/home/elliotbot/clawd/Agency_OS-scout` → `-home-elliotbot-clawd-Agency-OS-scout`
    (verified by `ls ~/.claude/projects/` 2026-05-13).
    """
    slug = "-" + worktree.lstrip("/").replace("/", "-").replace("_", "-")
    return CLAUDE_PROJECTS_ROOT / slug


def latest_session_id(callsign: str) -> str | None:
    """Return the most-recently-modified .jsonl filename (without extension) for
    the callsign's worktree, or None if the project dir is missing/empty.
    """
    worktree = CALLSIGN_TO_WORKTREE.get(callsign)
    if not worktree:
        return None
    project_dir = _project_dir_for(worktree)
    if not project_dir.is_dir():
        return None
    try:
        jsonls = sorted(
            (p for p in project_dir.iterdir() if p.suffix == ".jsonl"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
    except OSError as exc:
        logger.warning("project dir scan failed for %s: %s", callsign, exc)
        return None
    return jsonls[0].stem if jsonls else None


def _tmux(*args: str) -> bool:
    """Run a tmux subcommand; return True on rc=0."""
    # `args` is internally-constructed (callers in this module pass fixed
    # subcommand + session names from CALLSIGN_TO_TMUX); no shell, no
    # untrusted interpolation.
    try:
        proc = subprocess.run(  # noqa: S603
            ["tmux", *args],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
    except (subprocess.TimeoutExpired, OSError) as exc:
        # FileNotFoundError ⊂ OSError — single catch covers both.
        logger.warning("tmux %s failed: %s", args[0] if args else "?", exc)
        return False
    if proc.returncode != 0:
        logger.warning(
            "tmux %s rc=%d: %s",
            args[0] if args else "?",
            proc.returncode,
            proc.stderr.strip()[:200],
        )
    return proc.returncode == 0


def _brief_text(callsign: str) -> str:
    """Generic post-recovery brief — kept terse so we don't fabricate state."""
    return (
        f"# AUTO-RECOVERED SESSION — {callsign}\n"
        "You were auto-restarted by the orchestrator after a dead-tmux detection.\n"
        "Read IDENTITY.md + HEARTBEAT.md for current callsign state.\n"
        "Check #execution recent traffic + bd ready for in-flight work.\n"
        "If any PR or dispatch is in-flight on your branch, recover that first."
    )


def recover_session(callsign: str) -> bool:
    """Attempt the 4-step recovery for `callsign`. Returns True if all four
    steps reported success (does NOT verify the agent is responsive — that's
    the caller's next-cycle re-check).
    """
    session = CALLSIGN_TO_TMUX[callsign]
    worktree = CALLSIGN_TO_WORKTREE[callsign]
    session_id = latest_session_id(callsign)
    if session_id is None:
        logger.warning("no prior session jsonl for %s; cannot --resume", callsign)
        return False

    # Step 1: create the tmux session.
    if not _tmux("new-session", "-d", "-s", session, "-c", worktree):
        return False

    # Step 2: send the claude --resume command + Enter.
    claude_cmd = f"claude --resume {session_id} --dangerously-skip-permissions"
    if not _tmux("send-keys", "-t", session, claude_cmd, "Enter"):
        return False

    # Step 3: select option 1 (Resume from summary). Claude's resume prompt
    # appears after a brief load; send "1" + Enter. Per ceo_memory pattern.
    if not _tmux("send-keys", "-t", session, "1", "Enter"):
        return False

    # Step 4: brief the agent. Multi-line briefing via the literal text.
    return _tmux("send-keys", "-t", session, _brief_text(callsign), "Enter")


def _escalate_to_ceo(callsign: str, attempts: int) -> None:
    """Post a #ceo message after two failed recovery attempts (Dave threshold)."""
    msg = (
        f"[PROPOSE:elliot] Auto-recovery of {callsign} failed after {attempts} attempts.\n"
        f"tmux session `{CALLSIGN_TO_TMUX[callsign]}` is still dead. "
        "Manual intervention required: check worktree state, claude session jsonl, "
        "and any in-flight PR/dispatch on that callsign's branch."
    )
    # SLACK_RELAY_PATH is a module-level constant pointing at a repo-internal
    # script; argv is fully internal. Reason captured in this surrounding
    # comment rather than as inline noqa text (Sonar parses inline noqa
    # trailing-text as malformed).
    try:
        subprocess.run(  # noqa: S603
            ["python3", SLACK_RELAY_PATH, "-c", "ceo", msg],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
    except (subprocess.TimeoutExpired, OSError) as exc:
        logger.warning("slack_relay escalation failed for %s: %s", callsign, exc)


def run(now: datetime | None = None) -> int:
    ts_now = now or datetime.now(UTC)
    state = _load_state()
    state_changed = False
    dead = detect_dead_callsigns()

    if not dead:
        logger.info("all expected callsign sessions alive — no recovery needed")
        # Still clear stale state for any callsign that's now confirmed alive.
        return _reap_alive_state(state, state_changed)

    for callsign in dead:
        record = state.get(callsign, {"attempts": 0, "first_attempt_at": ts_now.isoformat()})
        attempts = int(record.get("attempts", 0))

        if attempts >= MAX_RECOVERY_ATTEMPTS:
            logger.warning(
                "%s: already at %d attempts (threshold), skipping further auto-recovery",
                callsign,
                attempts,
            )
            continue

        success = recover_session(callsign)
        attempts += 1
        state[callsign] = {
            "attempts": attempts,
            "first_attempt_at": record.get("first_attempt_at", ts_now.isoformat()),
            "last_attempt_at": ts_now.isoformat(),
            "last_attempt_success": success,
        }
        state_changed = True

        if success:
            logger.info("%s: recovery attempt %d apparently succeeded", callsign, attempts)
        elif attempts >= MAX_RECOVERY_ATTEMPTS:
            logger.error(
                "%s: recovery failed at attempt %d — escalating to #ceo", callsign, attempts
            )
            _escalate_to_ceo(callsign, attempts)
        else:
            logger.warning(
                "%s: recovery attempt %d failed; will retry next cycle (threshold %d)",
                callsign,
                attempts,
                MAX_RECOVERY_ATTEMPTS,
            )

    return _reap_alive_state(state, state_changed)


def _reap_alive_state(state: dict[str, dict], state_changed: bool) -> int:
    """Clear recovery-state entries for callsigns now confirmed alive.

    Lets a recovered agent re-arm its attempt counter so a future crash starts
    a fresh threshold rather than inheriting the prior cycle's count.
    """
    alive_now = _alive_sessions()
    for cs in list(state.keys()):
        tmux_name = CALLSIGN_TO_TMUX.get(cs)
        if tmux_name and tmux_name in alive_now:
            logger.info("%s: session confirmed alive — clearing recovery state", cs)
            state.pop(cs, None)
            state_changed = True

    if state_changed:
        _save_state(state)

    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="KEI-35 auto session recovery")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Detect dead sessions and log, but do not attempt recovery.",
    )
    args = parser.parse_args()

    if args.dry_run:
        dead = detect_dead_callsigns()
        if dead:
            logger.info("dry-run: would attempt recovery on %s", ", ".join(dead))
        else:
            logger.info("dry-run: no dead sessions")
        return 0

    return run()


if __name__ == "__main__":
    sys.exit(main())
