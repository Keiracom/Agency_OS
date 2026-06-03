#!/usr/bin/env python3
"""context_watchdog.py — Context-cycling watchdog for Elliot and fleet agents.

Detect → (compact+restart if context-full) → wake/resume → escalate-if-still-dead.

Runs as a SEPARATE systemd timer (elliot-context-watchdog.timer).
NOT inside Elliot's session — survives when Elliot is wedged.

Full sequence per Dave directive 2026-05-31:
  1. Detect: context-full OR idle >IDLE_TIMEOUT_MIN with no action.
  2. If context-full → write compact state → /clear wedged pane → inject wake prompt.
  3. Wake/resume (always after restart, also for plain idle): fresh Elliot reads state,
     does fleet sweep, dispatches cleared work, posts #ceo.
  4. If pane unchanged after WAKE_TIMEOUT_SEC → escalate to #ceo.

Hard rule: NEVER auto-authorise paid chain runs.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
STATE_FILE = Path("/tmp/elliot-compact-state.md")
WATCHDOG_STATE_FILE = Path("/tmp/elliot-watchdog-state.json")
SLACK_RELAY = str(REPO / "scripts" / "slack_relay.py")
WRITE_COMPACT = str(REPO / "scripts" / "orchestrator" / "write_compact_state.py")
VENV_PYTHON = str(REPO / ".venv" / "bin" / "python3")

ELLIOT_PANE = "elliottbot:0.0"
WAKE_TIMEOUT_SEC = 1200  # 20 min — two timer cycles before escalating (was 600 = single-shot)
IDLE_TIMEOUT_MIN = 40  # min idle (no pane change) before wake without restart

AGENTS = {
    "atlas": "atlas:0.0",
    "orion": "orion:0.0",
    "aiden": "aiden:0.0",
    "maxbot": "maxbot:0.0",
    "scout": "scout:0.0",
    "nova": "nova:0.0",
}

sys.path.insert(0, str(REPO))
from dotenv import load_dotenv

load_dotenv("/home/elliotbot/.config/agency-os/.env")

from scripts.utils.tmux_send import (  # noqa: E402
    safe_send,
    wait_for_prompt,
)


def pane_capture(target: str) -> str:
    try:
        r = subprocess.run(
            ["tmux", "capture-pane", "-p", "-t", target], capture_output=True, text=True, timeout=5
        )
        return r.stdout if r.returncode == 0 else ""
    except Exception:
        return ""


def pane_hash(pane: str) -> str:
    return hashlib.md5(pane[-600:].encode()).hexdigest()


def is_context_full(pane: str) -> bool:
    return "100% context used" in pane or "Usage credits required" in pane


# Permission-prompt vs genuine-stall split (Dave approved 2026-06-01).
# Old is_stuck() conflated the two and /cleared agents waiting on a
# routine read-only tool — destroying their context. The split lets us
# auto-approve safe tools, escalate unknown tools, and only /clear on
# real failure (Error:, Traceback, etc.). ⏵⏵ and 'bypass permiss' are
# permission-prompt-only; the Allow+Deny pane pattern stays under
# is_genuinely_stuck (the loose-substring check is unreliable as a
# permission signal in isolation).

# Flap-guard (agent_activity wire-up — nova-agent-activity-watchdog-wire).
# If the same agent is classified as needing wake N times within a rolling
# window, STOP auto-waking and post #ceo so a human triages the blocker.
# Per-agent state lives in /tmp/watchdog-flap-<callsign>.json so a stuck
# single agent does not contaminate the shared watchdog state file.
FLAP_WINDOW_SEC = 30 * 60  # 30-minute rolling window
FLAP_THRESHOLD = 3  # 3 wakes in window → flap
FLAP_STATE_PATH_TEMPLATE = "/tmp/watchdog-flap-{name}.json"

PERMISSION_PROMPT_TOKENS = ("⏵⏵", "bypass permiss")
GENUINE_STALL_INDICATORS = (
    "Error:",
    "APIError:",
    "ConnectionError",
    "TimeoutError",
    "Traceback",
)
# All tool-call prefix patterns that appear in Claude Code permission prompts.
# MCP tools appear as "● mcp__<server>__<tool>(" in the pane.
TOOL_CALL_PREFIXES = ("● Bash(", "● Read(", "● Write(", "● Edit(", "● mcp__", "● Task(")
AUTO_APPROVE_PATTERNS = [
    # git — read + routine write on feature branches.
    # `git checkout -b` (branch creation) ONLY — NOT bare `git checkout`,
    # which covers `git checkout -- .` (destructive working-tree reset) and
    # `git checkout main` (silent branch switch). Max HOLD blocker #1 on
    # PR #1385 (binding_dissent wire, Dave directive 2026-06-02).
    "git log",
    "git status",
    "git diff",
    "git branch",
    "git show",
    "git grep",
    "git add",
    "git commit",
    "git fetch",
    "git pull",
    "git stash",
    "git push",
    "git checkout -b",
    "git rev-parse",
    # GitHub CLI — read. `gh api ` substring REMOVED — it cannot distinguish
    # read endpoints from write endpoints (`gh api … -X PUT/POST/DELETE` and
    # endpoints like `/pulls/N/merge` are writes wearing a read prefix). Max
    # HOLD blocker #2 on PR #1385.
    "gh pr view",
    "gh pr list",
    "gh pr checks",
    "gh pr diff",
    "gh issue view",
    "gh issue list",
    "gh run view",
    "gh run list",
    # GitHub CLI — routine write ops. `gh pr merge` substring REMOVED —
    # merges land code in main and MUST gate on verified dual-concur, not on
    # an unconditional auto-approve. The verified path lives in
    # is_merge_with_dual_concur (PR comments must contain ≥2 REVIEW:approve
    # before send_tab fires). Max HOLD blocker #3 + binding_dissent
    # nucleus on PR #1385 (Dave directive 2026-06-02).
    "gh pr comment",
    "gh pr create",
    # tmux read ops
    "tmux capture-pane",
    "tmux list-sessions",
    "tmux list-panes",
    "tmux list-windows",
    # Local scripts — diagnostic, test, lint (no external API spend)
    "python3 scripts/",
    "python3 -m pytest",
    "python3 -B -m",
    "python3 -c ",
    "python3 <<",
    "pytest",
    "ruff ",
    "mypy ",
    # Beads / bd task ops
    "bd ready",
    "bd show",
    "bd close",
    "bd claim",
    "bd update",
    "bd create",
    # File + environment ops
    "cat ",
    "ls ",
    "find ",
    "grep ",
    "head ",
    "tail ",
    "wc ",
    "echo ",
    "source ",
    "env ",
    "which ",
    "type ",
]
ESCALATION_COOLDOWN_SEC = 300  # 5 min — anti-spam window for unknown-tool escalations
PR_NUMBER_RE = re.compile(r"·\s*PR\s*#(\d+)\s*·")

# Structural proven/attest DENY bar (HEAD-OF-OPS DIRECTIVE 2026-06-03).
# Any tool_str containing one of these patterns is HARD-DENIED by the watchdog —
# no Tab is sent, the prompt stays pending for human decision, and the DENY is
# logged to state[f"{name}_deny_log"] for audit. Supersedes both
# AUTO_APPROVE_PATTERNS and is_merge_with_dual_concur.
#
# Rationale: status changes on gate_roadmap.* to 'proven' AND gh pr merge land
# code/state that affects ratified-decisions surface. Those must go through a
# human, not the watchdog's pattern matcher.
STRUCTURAL_DENY_SUBSTRINGS = (
    "status=proven",
    "gate_proof_runs",
    "gh pr merge",
)
STRUCTURAL_DENY_REGEXES = (re.compile(r"INSERT.*proven", re.IGNORECASE),)

# Credential-redaction patterns (SECURITY P1, 2026-06-03). Any pane content
# that flows into slack_ceo() must pass through _redact_secrets() first —
# panes can carry psql DSNs, PGPASSWORD env lines, bearer tokens.
_REDACT_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"postgresql(\+\w+)?://[^@\s]+@"), r"postgresql\1://***@"),
    (re.compile(r"(PGPASSWORD)=\S+"), r"\1=***"),
    (re.compile(r"(DATABASE_URL)=\S+"), r"\1=***"),
    (re.compile(r":[^:@/\s]{8,}@"), ":***@"),
    (re.compile(r"Bearer [A-Za-z0-9_.\-]{20,}"), "Bearer ***"),
)


def _redact_secrets(text: str) -> str:
    """Mask credential patterns before they hit Slack."""
    if not text:
        return text
    for pat, repl in _REDACT_PATTERNS:
        text = pat.sub(repl, text)
    return text


# Ground-truth progress sources (HEAD-OF-OPS DIRECTIVE 2026-06-03).
# If ANY of these shows activity within IDLE_TIMEOUT_MIN, the fleet is NOT
# stalled — the watchdog should skip revive even if a pane looks idle.
WORKER_LOG_PATHS = (
    Path("/home/elliotbot/clawd/logs/keiracom-temporal-worker.log"),
    Path("/home/elliotbot/clawd/logs/dispatcher.log"),
    Path("/home/elliotbot/clawd/logs/fleet-supervisor.log"),
)


def is_permission_prompt(pane: str) -> bool:
    """True iff the pane is hung on a Claude Code permission prompt.

    Requires both the bypass-mode token AND evidence of an actual tool call
    being prompted. The ⏵⏵ / 'bypass permiss' tokens appear in the status bar
    of EVERY Claude Code session; checking them alone causes false positives on
    every idle pane and prevents is_context_full from ever running.
    """
    if not any(tok in pane for tok in PERMISSION_PROMPT_TOKENS):
        return False
    has_tool_call = any(prefix in pane for prefix in TOOL_CALL_PREFIXES)
    has_allow_deny = "Allow" in pane and ("Deny" in pane or "Tab to" in pane)
    return has_tool_call or has_allow_deny


def is_genuinely_stuck(pane: str) -> bool:
    """True iff the pane shows a real failure (not a permission prompt)."""
    if any(s in pane for s in GENUINE_STALL_INDICATORS):
        return True
    return "Allow" in pane and "Deny" in pane


def extract_pending_tool(pane: str) -> str | None:
    """Return the most recent tool-call line above the ⏵⏵ marker, capped at 200 chars.

    Returns None if the pane lacks a ⏵⏵ marker or no recognised tool call
    appears above it.
    """
    lines = pane.splitlines()
    chevron_idx = None
    for i in range(len(lines) - 1, -1, -1):
        if "⏵⏵" in lines[i]:
            chevron_idx = i
            break
    if chevron_idx is None:
        return None
    for i in range(chevron_idx - 1, -1, -1):
        line = lines[i]
        if any(prefix in line for prefix in TOOL_CALL_PREFIXES):
            return line.strip()[:200]
    return None


def extract_pr_number(pane: str) -> int | None:
    """Pull the active PR number from a `· PR #NNNN ·` status-line marker."""
    m = PR_NUMBER_RE.search(pane)
    if not m:
        return None
    try:
        return int(m.group(1))
    except ValueError:
        return None


def is_auto_approvable(tool_str: str) -> bool:
    """True iff `tool_str` contains any AUTO_APPROVE_PATTERNS substring."""
    if not tool_str:
        return False
    return any(pat in tool_str for pat in AUTO_APPROVE_PATTERNS)


def is_structurally_denied(tool_str: str) -> bool:
    """True iff `tool_str` matches any STRUCTURAL_DENY pattern (HARD DENY).

    Overrides every auto-approve path. The watchdog must NOT advance the
    permission prompt; the human reviews + decides.
    """
    if not tool_str:
        return False
    if any(sub in tool_str for sub in STRUCTURAL_DENY_SUBSTRINGS):
        return True
    return any(rx.search(tool_str) for rx in STRUCTURAL_DENY_REGEXES)


def _git_recent_commit(since_seconds: int) -> bool:
    try:
        r = subprocess.run(
            ["git", "log", f"--since={since_seconds} seconds ago", "--oneline", "-1"],
            capture_output=True,
            text=True,
            timeout=5,
            cwd=str(REPO),
            check=False,
        )
        return r.returncode == 0 and bool(r.stdout.strip())
    except Exception:
        return False


def _gate_roadmap_recent_change(since_seconds: int) -> bool:
    """Postgres lookup — any gate_roadmap_history row in the last `since_seconds`."""
    try:
        import psycopg  # noqa: PLC0415
    except ImportError:
        return False
    dsn = os.environ.get("DATABASE_URL_MIGRATIONS") or os.environ.get("DATABASE_URL", "")
    dsn = dsn.replace("postgresql+asyncpg://", "postgresql://", 1)
    if not dsn:
        return False
    try:
        with (
            psycopg.connect(dsn, prepare_threshold=None, connect_timeout=5) as conn,
            conn.cursor() as cur,
        ):
            cur.execute(
                "SELECT 1 FROM public.gate_roadmap_history "
                "WHERE changed_at > NOW() - make_interval(secs => %s) LIMIT 1",
                (since_seconds,),
            )
            return cur.fetchone() is not None
    except Exception:
        return False


def _worker_log_recent_mtime(since_seconds: int) -> bool:
    cutoff = time.time() - since_seconds
    for p in WORKER_LOG_PATHS:
        try:
            if p.exists() and p.stat().st_mtime > cutoff:
                return True
        except OSError:
            continue
    return False


def check_ground_truth_progress(since_seconds: int) -> bool:
    """True iff ANY ground-truth source shows progress in the last `since_seconds`.

    Sources:
      1. public.gate_roadmap_history (status changes).
      2. Worker log mtime (Temporal worker / dispatcher / fleet-supervisor).
      3. Recent git commits in the repo.

    Used before declaring an agent 'stalled' — if the fleet is shipping work,
    individual pane idleness is not stall.
    """
    if since_seconds <= 0:
        return False
    return (
        _gate_roadmap_recent_change(since_seconds)
        or _worker_log_recent_mtime(since_seconds)
        or _git_recent_commit(since_seconds)
    )


def sd_notify_watchdog() -> None:
    """Send WATCHDOG=1 heartbeat to systemd if NOTIFY_SOCKET is wired.

    Harmless on Type=oneshot units (NotifyAccess defaults make this a no-op);
    enables the systemd watchdog timer when the unit is converted to
    Type=notify + WatchdogSec=N (see infra/systemd/agents/elliot-context-
    watchdog.service for the converted unit + companion ops alert).
    """
    if not os.environ.get("NOTIFY_SOCKET"):
        return
    try:
        subprocess.run(["systemd-notify", "WATCHDOG=1"], timeout=2, check=False)
    except Exception:
        pass


def is_merge_with_dual_concur(tool_str: str, pr_number: int | None) -> bool:
    """True iff the pending tool is `gh pr merge` AND the PR shows 2+ REVIEW:approve.

    Best-effort: any gh failure (missing auth, network, JSON parse) returns
    False so the request escalates to Dave rather than being silently approved.
    """
    if not tool_str or "gh pr merge" not in tool_str or pr_number is None:
        return False
    try:
        r = subprocess.run(
            ["gh", "pr", "view", str(pr_number), "--json", "comments", "-q", ".comments[].body"],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
        if r.returncode != 0:
            return False
        approve_lines = [ln for ln in r.stdout.splitlines() if "REVIEW:approve" in ln]
        return len(approve_lines) >= 2
    except Exception:
        return False


def send_tab(target: str) -> None:
    """Send a single Tab keystroke to a tmux pane (advances past a Claude prompt)."""
    try:
        subprocess.run(["tmux", "send-keys", "-t", target, "Tab"], timeout=5, check=False)
    except Exception:
        pass


def handle_permission_prompt(name: str, target: str, pane: str, state: dict) -> dict:
    """Dispatch a permission prompt: auto-approve safe tools, escalate+approve unknowns.

    Every path that reaches here sends Tab so the agent unblocks — report to
    #ceo first for non-auto-approvable tools, but ALWAYS send the keystroke.
    A fleet that freezes waiting on a prompt that the watchdog only reports is
    the #1 availability bug (Dave directive 2026-06-02).

    NEVER /clears the pane — the agent is waiting on a decision, not stalled.
    Anti-spam: if we escalated within ESCALATION_COOLDOWN_SEC, skip re-escalation.
    """
    now = time.time()
    tool_str = extract_pending_tool(pane)
    pr_number = extract_pr_number(pane)

    # Structural proven/attest bar fires FIRST — overrides every auto-approve
    # path. Tab is NOT sent; prompt stays pending. DENY logged to state file.
    if tool_str is not None and is_structurally_denied(tool_str):
        deny_log = state.setdefault(f"{name}_deny_log", [])
        deny_log.append(
            {
                "ts": now,
                "tool": tool_str[:200],
                "reason": "structural_deny_proven_or_merge",
            }
        )
        # Cap to last 50 entries to keep state file bounded.
        state[f"{name}_deny_log"] = deny_log[-50:]
        last_escalated = state.get(f"{name}_escalated_at", 0)
        if now - last_escalated >= ESCALATION_COOLDOWN_SEC:
            slack_ceo(
                f"[ELLIOT] Watchdog DENIED {name}: structural bar (proven/merge). "
                f"Tool: {_redact_secrets(tool_str[:120])}. Prompt left pending — needs human."
            )
            state[f"{name}_escalated_at"] = now
        print(f"[watchdog] DENY {name}: {tool_str[:80]}")
        return state

    if tool_str is None:
        # Tool not visible above ⏵⏵ — report once per cooldown, then send Tab.
        last_escalated = state.get(f"{name}_escalated_at", 0)
        if now - last_escalated >= ESCALATION_COOLDOWN_SEC:
            tail_lines = [ln.strip() for ln in pane.splitlines() if ln.strip()][-3:]
            pane_tail = _redact_secrets(" | ".join(tail_lines))
            slack_ceo(
                f"[ELLIOT] Watchdog: {name} — unidentified prompt, Tab auto-sent.\n"
                f"Pane tail: {pane_tail[:200]}"
            )
            state[f"{name}_escalated_at"] = now
        send_tab(target)
        return state

    if is_auto_approvable(tool_str):
        send_tab(target)
        print(f"[watchdog] auto-approved {name}: {tool_str[:80]}")
        return state

    if is_merge_with_dual_concur(tool_str, pr_number):
        send_tab(target)
        print(f"[watchdog] auto-approved merge {name} PR#{pr_number} (dual concur verified)")
        return state

    # Known tool, not in auto-approve list: escalate to #ceo AND send Tab so
    # agent unblocks. Escalation is rate-limited; Tab is always sent.
    last_escalated = state.get(f"{name}_escalated_at", 0)
    if now - last_escalated >= ESCALATION_COOLDOWN_SEC:
        slack_ceo(
            f"[ELLIOT] Watchdog: {name} — non-standard tool auto-approved: {_redact_secrets(tool_str[:120])}\n"
            "Tab sent — agent unblocked. Review if unexpected."
        )
        state[f"{name}_escalated_at"] = now
    send_tab(target)
    return state


def load_state() -> dict:
    if WATCHDOG_STATE_FILE.exists():
        try:
            return json.loads(WATCHDOG_STATE_FILE.read_text())
        except Exception:
            pass
    return {}


def save_state(state: dict) -> None:
    WATCHDOG_STATE_FILE.write_text(json.dumps(state))


def record_agent_task(name: str, task_summary: str) -> None:
    """Persist `state[f"{name}_last_task"]` so a subsequent watchdog revive
    can tell the agent EXACTLY what it was working on (Fix C feed, 2026-05-31).

    Called by dispatch producers (sign_dispatch.py, elliot_polling_loop) right
    after a dispatch file lands in the agent's inbox. Best-effort: any failure
    here is silent — losing the breadcrumb degrades to the `bd ready` fallback
    in revive_agent(), it does NOT block the dispatch itself.

    The summary is squashed to a single line and capped at 240 chars to fit a
    `tmux send-keys` line without wrapping.
    """
    if not name or not task_summary:
        return
    summary = " ".join(task_summary.split())[:240]
    try:
        state = load_state()
        state[f"{name}_last_task"] = summary
        save_state(state)
    except Exception:
        pass


def slack_ceo(msg: str) -> None:
    try:
        subprocess.run(
            [VENV_PYTHON, SLACK_RELAY, "--channel", "ceo", "--text", msg],
            env={**os.environ, "CALLSIGN": "elliot"},
            timeout=15,
            check=False,
        )
    except Exception:
        pass


# send_pane and wait_for_prompt are now imported from scripts.utils.tmux_send.
# Thin wrappers kept for callers that pass delay= kwargs.


def send_pane(target: str, text: str, delay: float = 0) -> bool:
    """Verified pane injection via scripts.utils.tmux_send.safe_send.

    delay= arg is accepted for backwards-compat but ignored — safe_send
    manages its own settle/commit timing internally.
    Returns True if message was confirmed submitted.
    """
    return safe_send(target, text, skip_prompt_wait=True)


def ensure_compact_state() -> str:
    """Refresh compact state file. Returns content."""
    try:
        subprocess.run(
            [VENV_PYTHON, WRITE_COMPACT], timeout=30, cwd=str(REPO), check=False, env={**os.environ}
        )
    except Exception:
        pass
    if STATE_FILE.exists():
        return STATE_FILE.read_text()
    return "(compact state unavailable)"


def build_wake_prompt(state_path: str) -> str:
    return (
        "CONTEXT-CYCLE RESUME — fresh context started by watchdog. "
        f"Read {state_path} for current state. "
        "Do NOT reload full history. "
        "Run fleet sweep, dispatch cleared work, post #ceo 'resumed at [phase/task]'. "
        "No paid chain runs without explicit Dave approval."
    )


def restart_elliot(state: dict, now: float) -> dict:
    """Write compact state → /clear Elliot pane → wait for ❯ → inject wake prompt.

    Root-cause fix (2026-05-31): the Stop hook on /clear runs write_heartbeat.py
    with an 8-second timeout. The old fixed 4-second delay sent the wake prompt
    while the hook was still executing and /clear hadn't started a new context yet.
    Claude Code resets terminal input when the new context starts, losing the
    buffered wake prompt. The pane stayed at the empty ❯ screen for 10 minutes
    and the watchdog escalated — 5 consecutive overnight failures.

    Fix: after /clear, poll for the ❯ prompt (up to 30 seconds) before injecting
    the wake prompt. This mirrors the inbox watcher's proven pattern and ensures
    the Stop hook has finished and the new context is ready.
    """
    ensure_compact_state()
    # /clear the wedged pane — Stop hook (write_heartbeat.py, 8s timeout) fires here
    send_pane(ELLIOT_PANE, "/clear", delay=0)
    # Wait for new ❯ prompt (Stop hook + new context must both complete first)
    ready = wait_for_prompt(ELLIOT_PANE, timeout=30.0)
    if not ready:
        slack_ceo(
            "[ELLIOT] Watchdog: /clear sent but ❯ prompt not seen after 30s — "
            "pane may be hung. Skipping wake injection; will retry next cycle."
        )
        state["elliot_wake_sent"] = now
        state["elliot_wake_reason"] = "context-full-clear-hung"
        pane = pane_capture(ELLIOT_PANE)
        state["elliot_last_hash"] = pane_hash(pane)
        return state

    # ❯ prompt confirmed — inject wake prompt now
    wake_prompt = build_wake_prompt(str(STATE_FILE))
    send_pane(ELLIOT_PANE, wake_prompt, delay=2.0)

    slack_ceo(
        "[ELLIOT] Context-cycle watchdog: 100% context detected. "
        "Compact state written, /clear sent, ❯ confirmed, wake prompt injected."
    )
    state["elliot_wake_sent"] = now
    state["elliot_wake_reason"] = "context-full"
    pane = pane_capture(ELLIOT_PANE)
    state["elliot_last_hash"] = pane_hash(pane)
    return state


def wake_idle_elliot(state: dict, now: float) -> dict:
    """Send wake prompt to idle Elliot (no /clear — context is fine)."""
    # For idle wake, ❯ should already be showing — verify before injecting
    if not wait_for_prompt(ELLIOT_PANE, timeout=10.0):
        # Pane doesn't have ❯ — might not be at an input prompt; skip this cycle
        state["elliot_wake_sent"] = now
        state["elliot_wake_reason"] = "idle-no-prompt"
        pane = pane_capture(ELLIOT_PANE)
        state["elliot_last_hash"] = pane_hash(pane)
        return state
    wake_prompt = build_wake_prompt(str(STATE_FILE))
    send_pane(ELLIOT_PANE, wake_prompt, delay=1.0)
    state["elliot_wake_sent"] = now
    state["elliot_wake_reason"] = "idle"
    pane = pane_capture(ELLIOT_PANE)
    state["elliot_last_hash"] = pane_hash(pane)
    return state


def revive_agent(name: str, target: str, reason: str, last_task: str = "") -> None:
    """Revive a non-Elliot stuck/context-full agent.

    `last_task` (when Elliot writes state[f"{name}_last_task"] at dispatch
    time) tells the revived agent EXACTLY what to resume — falls back to
    `bd ready` when blank.
    """
    # Send /clear (no prompt-wait needed — stuck agent is at ❯ already)
    safe_send(target, "/clear", skip_prompt_wait=True, wait_prompt=0)
    # Wait for new ❯ (Stop hook may delay the new context — same race as Elliot)
    if not wait_for_prompt(target, timeout=30.0):
        slack_ceo(f"[ELLIOT] Watchdog: {name} /clear hung (❯ not seen 30s). Revive skipped.")
        return
    task_hint = f" Last task: {last_task}." if last_task else ""
    revive_msg = (
        f"REVIVED by watchdog ({reason}).{task_hint} Read IDENTITY.md, "
        "check bd ready, resume last task. No paid chain runs without approval."
    )
    safe_send(target, revive_msg, skip_prompt_wait=True)
    slack_ceo(f"[ELLIOT] Watchdog revived {name} ({reason}).")


def _flap_state_path(name: str) -> Path:
    return Path(FLAP_STATE_PATH_TEMPLATE.format(name=name))


def load_flap_events(name: str, now: float) -> list[float]:
    """Return wake-event timestamps for `name` within FLAP_WINDOW_SEC of `now`.

    Drops events outside the window and silently swallows read errors — the
    flap signal is advisory, not load-bearing.
    """
    path = _flap_state_path(name)
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text())
        events = data.get("events", [])
    except Exception:
        return []
    return [t for t in events if isinstance(t, (int, float)) and (now - t) < FLAP_WINDOW_SEC]


def record_flap_event(name: str, now: float) -> None:
    """Append a wake event for `name` at `now`; prune the file to the active window."""
    events = load_flap_events(name, now)
    events.append(now)
    try:
        _flap_state_path(name).write_text(json.dumps({"events": events}))
    except Exception:
        pass


def is_flap_tripped(name: str, now: float) -> bool:
    """True iff `name` has been woken FLAP_THRESHOLD+ times within the window.

    Threshold check uses >= so the third wake inside the window arms the guard
    — the fourth wake is the one that's suppressed. This matches the dispatch's
    'woken 3x' phrasing (the 3rd wake is the alarm trigger; further wakes are
    blocked until events age out of the window).
    """
    return len(load_flap_events(name, now)) >= FLAP_THRESHOLD


def _try_classify_activity(name: str) -> str:
    """Best-effort wrapper around scripts.orchestrator.agent_activity.

    Returns 'no_data' on any error (import miss, DB unreachable, callsign
    absent). The fail-open contract lets the watchdog fall through to its
    existing pane-based detection (is_genuinely_stuck) when the activity
    signal is uninformative.
    """
    try:
        from scripts.orchestrator.agent_activity import (  # noqa: PLC0415
            compute_activity_state,
        )

        return compute_activity_state(name)
    except Exception as exc:  # noqa: BLE001 — fail-open: never block watchdog cycle
        print(f"[watchdog] activity-state lookup failed for {name}: {exc}")
        return "no_data"


def check_other_agents(state: dict) -> dict:
    """Check non-Elliot agents for context-full or stuck.

    Two-cycle verification for revives (Dave failure mode 2026-05-30):
      cycle N   : detect → revive → record state[f"{name}_revive_sent"] = now.
      cycle N+1 : if pane hash CHANGED → revive worked, clear revive_sent.
                  if pane unchanged AND (now - revive_sent) > WAKE_TIMEOUT_SEC
                  → escalate to #ceo + reset revive_sent (avoid spam loop).
                  if pane unchanged AND still within timeout → wait, no re-revive.
    Mirrors the existing Elliot escalation pattern at the top of main().
    """
    now = time.time()
    for name, target in AGENTS.items():
        pane = pane_capture(target)
        if not pane:
            continue
        h = pane_hash(pane)
        key_hash = f"{name}_last_hash"
        key_ts = f"{name}_last_change"
        key_revive = f"{name}_revive_sent"
        prev_hash = state.get(key_hash, "")
        if h != prev_hash:
            state[key_hash] = h
            state[key_ts] = now
            # Pane moved → any prior revive worked; clear the in-flight flag.
            state[key_revive] = 0

        # Post-revive verification (Fix B). Mirrors Elliot's wake_sent check.
        revive_sent = state.get(key_revive, 0)
        if revive_sent and (now - revive_sent) > WAKE_TIMEOUT_SEC:
            # Expired AND pane hash still unchanged → revive FAILED.
            if h == state.get(key_hash, ""):
                slack_ceo(
                    f"[ELLIOT] Watchdog: {name} revive FAILED — pane unchanged "
                    f"{WAKE_TIMEOUT_SEC // 60}min after restart. Task work may be lost."
                )
                state[key_revive] = 0  # reset to avoid spam loop
            continue  # don't double-revive in the same cycle

        # Don't re-fire revive while a prior revive is still in-flight.
        if revive_sent:
            continue

        # Permission prompts come BEFORE genuine-stall: the agent is waiting on
        # a tool-call decision, not crashed. /clear here would destroy context.
        if is_permission_prompt(pane):
            state = handle_permission_prompt(name, target, pane, state)
            continue

        last_task = state.get(f"{name}_last_task", "")
        # Context-full is a structural pane signal — revive regardless of
        # ground-truth (the agent itself cannot continue without a /clear).
        if is_context_full(pane):
            revive_agent(name, target, "context-full", last_task=last_task)
            state[key_revive] = now
            continue
        if is_genuinely_stuck(pane):
            # Ground-truth gate: if the fleet is shipping work in the recent
            # window, individual pane idleness is not a stall — skip revive.
            if check_ground_truth_progress(IDLE_TIMEOUT_MIN * 60):
                print(f"[watchdog] {name} pane idle but ground-truth shows progress — skip revive")
                continue
            revive_agent(name, target, "error-detected", last_task=last_task)
            state[key_revive] = now
            continue

        # Activity-state wire-up (nova-agent-activity-watchdog-wire). The
        # pane-hash-stable false-green that masked Scout + Nova idle for 48-51min
        # is closed here: tool_call_log activity (per Scout's compute_activity_
        # state) is the finer signal that the pane cannot reveal — an agent
        # sitting at a quiet ❯ with 0 tool calls in 10 min is silent regardless
        # of whether the pane bytes changed.
        #
        # Five-class dispatch:
        #   active                -> skip (calls in the last 10 min)
        #   idle_with_work_queued -> revive (inbox has dispatch waiting; the
        #                             inbox-watcher delivers on wake)
        #   idle                  -> leave (NO THRASH — no inbox = no fresh work)
        #   no_data               -> skip (DB / helper unavailable; the
        #                             pane-based context-full + genuine-stuck
        #                             branches above already covered the
        #                             pane-visible failure modes)
        #
        # Flap guard: 3 wakes in FLAP_WINDOW_SEC for the same agent suspends
        # further auto-wakes and posts #ceo — protects against thrash when a
        # wake fails to land work (agent stalls again immediately).
        activity_state = _try_classify_activity(name)
        if activity_state == "idle_with_work_queued":
            if is_flap_tripped(name, now):
                flap_key = f"{name}_flap_alerted_at"
                last_alert = state.get(flap_key, 0)
                if now - last_alert >= ESCALATION_COOLDOWN_SEC:
                    slack_ceo(
                        f"[ELLIOT] FLAP: {name} woken {FLAP_THRESHOLD}x in "
                        f"{FLAP_WINDOW_SEC // 60}min — possible blocker. "
                        "Auto-wake suspended until events age out of window."
                    )
                    state[flap_key] = now
                print(f"[watchdog] {name} FLAP guard tripped — wake suspended")
                continue
            revive_agent(name, target, "idle_with_work_queued", last_task=last_task)
            state[key_revive] = now
            record_flap_event(name, now)
            print(f"[watchdog] {name} idle_with_work_queued — wake injected")
        elif activity_state == "active":
            # Tool calls within the last 10 min — agent is doing work.
            pass
        elif activity_state == "idle":
            # No work queued — NO THRASH. Leaving the agent untouched is the
            # whole point of the inbox check: an agent that finished its work
            # cleanly and is awaiting dispatch must not be repeatedly woken.
            print(f"[watchdog] {name} idle (no inbox) — leave (no-thrash)")
        # activity_state == "no_data" falls through silently (pane-based
        # branches above are the safety net).
    return state


def main() -> None:
    sd_notify_watchdog()
    now = time.time()
    state = load_state()

    # ── Elliot self-check ─────────────────────────────────────────────────
    elliot_pane = pane_capture(ELLIOT_PANE)
    elliot_hash = pane_hash(elliot_pane)
    prev_hash = state.get("elliot_last_hash", "")
    prev_hash_ts = state.get("elliot_last_hash_ts", now)

    if elliot_hash != prev_hash:
        state["elliot_last_hash"] = elliot_hash
        state["elliot_last_hash_ts"] = now
        state["elliot_wake_sent"] = 0  # pane moved — clear any pending wake
    else:
        state.setdefault("elliot_last_hash_ts", prev_hash_ts)

    wake_sent = state.get("elliot_wake_sent", 0)

    # Permission prompts come BEFORE context-full: a hung tool-call decision
    # must not trigger /clear (mirrors the check_other_agents ordering).
    if is_permission_prompt(elliot_pane):
        state = handle_permission_prompt("elliot", ELLIOT_PANE, elliot_pane, state)
    elif is_context_full(elliot_pane):
        # Problem A: context full → compact+restart, then wake/resume
        state = restart_elliot(state, now)
    elif wake_sent and (now - wake_sent) > WAKE_TIMEOUT_SEC:
        # Wake was sent but pane still hasn't changed → escalate
        if elliot_hash == state.get("elliot_last_hash", ""):
            slack_ceo(
                "[ELLIOT] Watchdog: auto-resume FAILED — Elliot pane unchanged "
                f"{WAKE_TIMEOUT_SEC // 60}min after restart. Needs manual intervention."
            )
            state["elliot_wake_sent"] = 0  # reset to avoid spam loop
    elif not wake_sent:
        # No active wake. Check tool_call_log first — the 10-min activity-
        # signal supersedes the 40-min pane-hash idle check (the pane-hash was
        # the false-green source that masked Scout/Nova for 48-51min; pane
        # bytes can stay stable at a quiet ❯ while the agent makes zero tool
        # calls). Pane-hash kept ONLY as the no_data fallback below.
        activity_state = _try_classify_activity("elliot")
        if activity_state == "idle_with_work_queued":
            if is_flap_tripped("elliot", now):
                last_alert = state.get("elliot_flap_alerted_at", 0)
                if now - last_alert >= ESCALATION_COOLDOWN_SEC:
                    slack_ceo(
                        f"[ELLIOT] FLAP: elliot woken {FLAP_THRESHOLD}x in "
                        f"{FLAP_WINDOW_SEC // 60}min — possible blocker. "
                        "Auto-wake suspended until events age out of window."
                    )
                    state["elliot_flap_alerted_at"] = now
                print("[watchdog] elliot FLAP guard tripped — wake suspended")
            else:
                state = wake_idle_elliot(state, now)
                record_flap_event("elliot", now)
                print("[watchdog] elliot idle_with_work_queued — wake injected")
        elif activity_state == "idle":
            # No inbox work → leave (NO THRASH).
            print("[watchdog] elliot idle (no inbox) — leave (no-thrash)")
        elif activity_state == "active":
            # Tool calls within 10 min — Elliot is driving the fleet.
            pass
        else:  # no_data — fall back to the legacy pane-hash idle check.
            idle_secs = now - state.get("elliot_last_hash_ts", now)
            if idle_secs > IDLE_TIMEOUT_MIN * 60:
                if check_ground_truth_progress(IDLE_TIMEOUT_MIN * 60):
                    print("[watchdog] elliot idle but ground-truth shows progress — skip wake")
                else:
                    state = wake_idle_elliot(state, now)

    # ── Other agents ─────────────────────────────────────────────────────
    state = check_other_agents(state)

    save_state(state)
    print(f"[{datetime.now(UTC).strftime('%H:%M UTC')}] watchdog cycle complete")


if __name__ == "__main__":
    main()
