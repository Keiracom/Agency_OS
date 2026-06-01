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
IDLE_TIMEOUT_MIN = 40    # min idle (no pane change) before wake without restart

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
    pane_content as _pane_content_util,
    safe_send,
    wait_for_prompt,
)


def pane_capture(target: str) -> str:
    try:
        r = subprocess.run(["tmux", "capture-pane", "-p", "-t", target],
                           capture_output=True, text=True, timeout=5)
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

PERMISSION_PROMPT_TOKENS = ("⏵⏵", "bypass permiss")
GENUINE_STALL_INDICATORS = (
    "Error:", "APIError:", "ConnectionError", "TimeoutError", "Traceback",
)
TOOL_CALL_PREFIXES = ("● Bash(", "● Read(", "● Write(")
AUTO_APPROVE_PATTERNS = [
    "git log", "git status", "git diff", "git branch", "git show", "git grep",
    "git add", "git commit",
    "gh pr view", "gh pr list", "gh pr checks", "gh pr diff",
    "gh issue view", "gh issue list",
    "gh pr comment",
    "tmux capture-pane",
]
ESCALATION_COOLDOWN_SEC = 300  # 5 min — anti-spam window for unknown-tool escalations
PR_NUMBER_RE = re.compile(r"·\s*PR\s*#(\d+)\s*·")


def is_permission_prompt(pane: str) -> bool:
    """True iff the pane is hung on a Claude Code permission prompt."""
    return any(tok in pane for tok in PERMISSION_PROMPT_TOKENS)


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


def is_merge_with_dual_concur(tool_str: str, pr_number: int | None) -> bool:
    """True iff the pending tool is `gh pr merge` AND the PR shows 2+ REVIEW:approve.

    Best-effort: any gh failure (missing auth, network, JSON parse) returns
    False so the request escalates to Dave rather than being silently approved.
    """
    if not tool_str or "gh pr merge" not in tool_str or pr_number is None:
        return False
    try:
        r = subprocess.run(
            ["gh", "pr", "view", str(pr_number), "--json", "comments", "-q",
             ".comments[].body"],
            capture_output=True, text=True, timeout=15, check=False,
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
        subprocess.run(["tmux", "send-keys", "-t", target, "Tab"],
                       timeout=5, check=False)
    except Exception:
        pass


def handle_permission_prompt(name: str, target: str, pane: str, state: dict) -> dict:
    """Dispatch a permission prompt: auto-approve safe tools, escalate unknowns.

    NEVER /clears the pane — the agent is waiting on a decision, not stalled.
    Anti-spam: if we escalated within ESCALATION_COOLDOWN_SEC, skip re-escalation.
    """
    now = time.time()
    tool_str = extract_pending_tool(pane)
    pr_number = extract_pr_number(pane)
    if tool_str is None:
        last_escalated = state.get(f"{name}_escalated_at", 0)
        if now - last_escalated >= ESCALATION_COOLDOWN_SEC:
            slack_ceo(
                f"[ELLIOT] Watchdog: {name} hung on permission prompt but tool "
                "call could not be identified. Approve manually or kill."
            )
            state[f"{name}_escalated_at"] = now
        return state

    if is_auto_approvable(tool_str):
        send_tab(target)
        print(f"[watchdog] auto-approved {name}: {tool_str[:80]}")
        return state

    if is_merge_with_dual_concur(tool_str, pr_number):
        send_tab(target)
        print(f"[watchdog] auto-approved merge {name} PR#{pr_number} (dual concur verified)")
        return state

    last_escalated = state.get(f"{name}_escalated_at", 0)
    if now - last_escalated < ESCALATION_COOLDOWN_SEC:
        return state
    slack_ceo(
        f"[ELLIOT] Watchdog: {name} needs permission for: {tool_str[:120]}\n"
        "Approve? (agent will wait — NOT being cleared)"
    )
    state[f"{name}_escalated_at"] = now
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
        subprocess.run([VENV_PYTHON, SLACK_RELAY, "--channel", "ceo", "--text", msg],
                       env={**os.environ, "CALLSIGN": "elliot"},
                       timeout=15, check=False)
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
        subprocess.run([VENV_PYTHON, WRITE_COMPACT], timeout=30,
                       cwd=str(REPO), check=False,
                       env={**os.environ})
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
        if is_context_full(pane):
            revive_agent(name, target, "context-full", last_task=last_task)
            state[key_revive] = now
        elif is_genuinely_stuck(pane):
            revive_agent(name, target, "error-detected", last_task=last_task)
            state[key_revive] = now
    return state


def main() -> None:
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
                f"{WAKE_TIMEOUT_SEC//60}min after restart. Needs manual intervention."
            )
            state["elliot_wake_sent"] = 0  # reset to avoid spam loop
    elif not wake_sent:
        # No active wake; check for idle-too-long (Problem B standalone)
        idle_secs = now - state.get("elliot_last_hash_ts", now)
        if idle_secs > IDLE_TIMEOUT_MIN * 60:
            state = wake_idle_elliot(state, now)

    # ── Other agents ─────────────────────────────────────────────────────
    state = check_other_agents(state)

    save_state(state)
    print(f"[{datetime.now(UTC).strftime('%H:%M UTC')}] watchdog cycle complete")


if __name__ == "__main__":
    main()
