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
WAKE_TIMEOUT_SEC = 600   # 10 min after wake sent — if still dead, escalate
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


def is_stuck(pane: str) -> bool:
    indicators = ["Error:", "APIError:", "ConnectionError", "TimeoutError", "Traceback"]
    if any(s in pane for s in indicators):
        return True
    # Permission-prompt detection (Dave-identified failure mode 2026-05-30):
    # tmux pane hung on a Claude permission prompt → silent stall the watchdog
    # previously could not see. Three independent signals; any one is enough.
    if "⏵⏵" in pane or "bypass permiss" in pane:
        return True
    return "Allow" in pane and "Deny" in pane


def load_state() -> dict:
    if WATCHDOG_STATE_FILE.exists():
        try:
            return json.loads(WATCHDOG_STATE_FILE.read_text())
        except Exception:
            pass
    return {}


def save_state(state: dict) -> None:
    WATCHDOG_STATE_FILE.write_text(json.dumps(state))


def slack_ceo(msg: str) -> None:
    try:
        subprocess.run([VENV_PYTHON, SLACK_RELAY, "--channel", "ceo", "--text", msg],
                       env={**os.environ, "CALLSIGN": "elliot"},
                       timeout=15, check=False)
    except Exception:
        pass


def send_pane(target: str, text: str, delay: float = 1.5) -> None:
    try:
        subprocess.run(["tmux", "send-keys", "-t", target, text, "Enter"],
                       timeout=5, check=False)
        if delay > 0:
            time.sleep(delay)
    except Exception:
        pass


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
    """Write compact state → /clear Elliot pane → inject wake prompt."""
    compact = ensure_compact_state()
    # /clear the wedged pane
    send_pane(ELLIOT_PANE, "/clear", delay=4.0)
    # Inject wake prompt pointing at the state file
    wake_prompt = build_wake_prompt(str(STATE_FILE))
    send_pane(ELLIOT_PANE, wake_prompt, delay=1.0)

    slack_ceo(
        "[ELLIOT] Context-cycle watchdog: 100% context detected. "
        "Compact state written, session restarted. Monitoring for resume."
    )
    state["elliot_wake_sent"] = now
    state["elliot_wake_reason"] = "context-full"
    pane = pane_capture(ELLIOT_PANE)
    state["elliot_last_hash"] = pane_hash(pane)
    return state


def wake_idle_elliot(state: dict, now: float) -> dict:
    """Send wake prompt to idle Elliot (no /clear — context is fine)."""
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
    send_pane(target, "/clear", delay=3.0)
    if last_task:
        body = (
            f"REVIVED by watchdog ({reason}). Last task: {last_task}. "
            "Read IDENTITY.md, resume that task. "
            "No paid chain runs without approval."
        )
    else:
        body = (
            f"REVIVED by watchdog ({reason}). Read IDENTITY.md, "
            "check bd ready, resume last task. No paid chain runs without approval."
        )
    send_pane(target, body, delay=0.5)
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

        last_task = state.get(f"{name}_last_task", "")
        if is_context_full(pane):
            revive_agent(name, target, "context-full", last_task=last_task)
            state[key_revive] = now
        elif is_stuck(pane):
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

    if is_context_full(elliot_pane):
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
