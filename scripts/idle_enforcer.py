#!/usr/bin/env python3
"""idle_enforcer.py — KEI-45 Layer 3 idle enforcement daemon.

Polls all 6 agents every IDLE_CHECK_INTERVAL_SECONDS. Per cycle, per agent:

  1. Capture tail of agent's tmux pane (reuses elliot_polling_loop primitives).
  2. Weekly-cap detection — if Anthropic banner "You've used X% of your weekly
     limit · resets <date>" matches → post #ceo, suppress retries until reset.
  3. Transient throttle detection (THROTTLE_RE: 429 / "Server is temporarily
     limiting requests" / "Brewed for") → exponential backoff, no escalation.
  4. BUSY-guard — if pane shows recent [BUSY:<callsign>:<task>] tag, skip
     (the agent is actively working; don't double-dispatch).
  5. Idle-derivation — file mtime of HEARTBEAT.md (per-worktree) is the
     freshness signal, since the template's structured fields are placeholders
     unless an agent explicitly populated them. Augments (not replaces) the
     existing keiracom_admin.agent_status_observations source.
  6. Idle >= IDLE_DISPATCH_MINUTES (10) + unclaimed bd ready work + no rate
     limit + not BUSY → mechanical tmux send-keys injection of the work brief.
     This is Layer 3 mechanical: cannot be bypassed by agent reasoning.
  7. Idle >= IDLE_ESCALATION_MINUTES (30) + still has pending work → #ceo
     escalation (one-shot per cycle, deduped by callsign).
  8. Upsert per-agent state into public.ceo_memory key ceo:boot_state_current
     (jsonb), schema documented in BOOT_STATE_SCHEMA below.

Idempotent + best-effort: any agent's failure logs + continues. Daemon survives
reboots via Restart=on-failure + WantedBy=default.target (KEI-43 pattern).
"""

from __future__ import annotations

import json
import logging
import os
import re
import subprocess
import sys
import time
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

# Reuse existing primitives from elliot_polling_loop.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from orchestrator.elliot_polling_loop import (  # noqa: E402
    CALLSIGN_TO_TMUX,
    THROTTLE_RE,
    _capture_pane_tail,
    _extract_throttle_duration,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
logger = logging.getLogger("idle_enforcer")

# Tuning constants ──────────────────────────────────────────────────────────
IDLE_CHECK_INTERVAL_SECONDS = int(os.environ.get("IDLE_CHECK_INTERVAL_SECONDS", "300"))
IDLE_DISPATCH_MINUTES = int(os.environ.get("IDLE_DISPATCH_MINUTES", "10"))
IDLE_ESCALATION_MINUTES = int(os.environ.get("IDLE_ESCALATION_MINUTES", "30"))
BUSY_GUARD_PANE_LINES = 20

WORKTREE_BASE = "/home/elliotbot/clawd"
CALLSIGN_TO_WORKTREE: dict[str, str] = {
    "elliot": f"{WORKTREE_BASE}/Agency_OS",
    "aiden": f"{WORKTREE_BASE}/Agency_OS-aiden",
    "max": f"{WORKTREE_BASE}/Agency_OS-max",
    "atlas": f"{WORKTREE_BASE}/Agency_OS-atlas",
    "orion": f"{WORKTREE_BASE}/Agency_OS-orion",
    "scout": f"{WORKTREE_BASE}/Agency_OS-scout",
}

# Weekly-cap banner — Anthropic CLI prints e.g.:
#   "You've used 92% of your weekly limit · resets 2026-05-20"
#   "You've used 100% of your weekly limit. Resets Friday at 10am UTC"
# Loose match: capture % + the resets-prefixed remainder so the parser can
# extract whatever date format Anthropic uses today (string, no enforcement).
WEEKLY_CAP_RE = re.compile(
    r"you[''']?ve used\s+(?P<pct>\d{1,3})%\s+of your weekly limit"
    r"[\s.·,-]*resets?[\s:]+(?P<resets>[A-Za-z0-9 ,.\-:/]+?)(?:[\n\r]|$)",
    re.IGNORECASE,
)

# BUSY tag emitted by agents per orchestrator-discipline (KEI-39 protocol).
BUSY_RE = re.compile(r"\[BUSY:(?P<callsign>\w+):(?P<task>[^\]]+)\]", re.IGNORECASE)

CEO_CHANNEL_NAME = "ceo"

BOOT_STATE_SCHEMA = """
{
  "<callsign>": {
    "last_activity": "<ISO-8601 UTC>",
    "idle_minutes": int,
    "work_available_count": int,
    "last_dispatch_at": "<ISO-8601 UTC | null>",
    "rate_limit_state": "ok | transient | weekly_cap_until=<date>"
  }
}
"""


@dataclass
class AgentState:
    callsign: str
    last_activity: str
    idle_minutes: int
    work_available_count: int = 0
    last_dispatch_at: str | None = None
    rate_limit_state: str = "ok"


# Suppress escalation re-emission for the same callsign more often than this.
_last_escalation_at: dict[str, datetime] = {}
ESCALATION_DEDUP_MINUTES = 60


def _heartbeat_mtime(callsign: str) -> datetime | None:
    """Return UTC mtime of the callsign's HEARTBEAT.md, or None on miss."""
    wt = CALLSIGN_TO_WORKTREE.get(callsign)
    if not wt:
        return None
    p = Path(wt) / "HEARTBEAT.md"
    if not p.is_file():
        return None
    try:
        ts = p.stat().st_mtime
    except OSError:
        return None
    return datetime.fromtimestamp(ts, tz=UTC)


def _compute_idle_minutes(callsign: str, now: datetime) -> tuple[int, str]:
    """Return (idle_minutes, last_activity_iso). Falls back to 0 if unknown."""
    mtime = _heartbeat_mtime(callsign)
    if mtime is None:
        return 0, now.isoformat()
    delta = now - mtime
    return max(0, int(delta.total_seconds() // 60)), mtime.isoformat()


def detect_weekly_cap(pane_text: str) -> tuple[bool, str | None]:
    """Return (matched, resets_string). resets_string is None if no match."""
    m = WEEKLY_CAP_RE.search(pane_text)
    if not m:
        return False, None
    return True, m.group("resets").strip()


def detect_busy(pane_text: str, callsign: str) -> bool:
    """True iff a [BUSY:<callsign>:<task>] tag appears in the pane tail."""
    return any(m.group("callsign").lower() == callsign.lower() for m in BUSY_RE.finditer(pane_text))


def bd_ready_for(callsign: str) -> list[dict]:
    """Return ready bd issues assigned to callsign. Best-effort."""
    try:
        proc = subprocess.run(
            ["bd", "ready", "--assignee", callsign, "--json"],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError) as exc:
        logger.warning("bd ready failed for %s: %s", callsign, exc)
        return []
    if proc.returncode != 0:
        return []
    try:
        data = json.loads(proc.stdout or "[]")
    except json.JSONDecodeError:
        return []
    return data if isinstance(data, list) else []


def inject_dispatch(callsign: str, brief: str) -> bool:
    """Mechanically inject brief into agent tmux via send-keys. Returns success."""
    session = CALLSIGN_TO_TMUX.get(callsign)
    if not session:
        logger.warning("no tmux mapping for callsign %r", callsign)
        return False
    # Defensive: verify session is alive before injecting.
    try:
        check = subprocess.run(
            ["tmux", "has-session", "-t", session],
            capture_output=True,
            timeout=5,
            check=False,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return False
    if check.returncode != 0:
        return False
    # Send-keys: target the first pane of window 0.
    target = f"{session}:0"
    try:
        # First the brief text...
        subprocess.run(
            ["tmux", "send-keys", "-t", target, brief],
            capture_output=True,
            timeout=5,
            check=False,
        )
        # ...then Enter as a separate key so the brief doesn't have an embedded \n.
        subprocess.run(
            ["tmux", "send-keys", "-t", target, "Enter"],
            capture_output=True,
            timeout=5,
            check=False,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError) as exc:
        logger.warning("send-keys failed for %s: %s", callsign, exc)
        return False
    logger.info("injected dispatch into %s (callsign=%s)", session, callsign)
    return True


def post_ceo(message: str) -> None:
    """Post to #ceo via slack_relay.py. Best-effort."""
    relay = Path(__file__).resolve().parent / "slack_relay.py"
    if not relay.is_file():
        logger.warning("slack_relay.py missing at %s — dropping ceo post", relay)
        return
    try:
        subprocess.run(
            ["python3", str(relay), "-c", CEO_CHANNEL_NAME, message],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
    except (subprocess.TimeoutExpired, OSError) as exc:
        logger.warning("slack_relay -c ceo failed: %s", exc)


def upsert_boot_state(states: dict[str, AgentState]) -> None:
    """Upsert per-agent state into public.ceo_memory key ceo:boot_state_current."""
    dsn = os.environ.get("DATABASE_URL", "") or os.environ.get("DATABASE_URL_MIGRATIONS", "")
    if not dsn:
        logger.info("DATABASE_URL unset — skipping boot_state write (dry mode)")
        return
    try:
        import asyncio

        import asyncpg
    except ImportError:
        logger.warning("asyncpg unavailable — skipping boot_state write")
        return

    payload = {cs: asdict(s) for cs, s in states.items()}

    async def _run() -> None:
        conn = await asyncpg.connect(
            dsn.replace("postgresql+asyncpg://", "postgresql://"),
            statement_cache_size=0,
        )
        try:
            await conn.execute(
                """
                INSERT INTO public.ceo_memory (key, value, updated_at)
                VALUES ($1, $2::jsonb, NOW())
                ON CONFLICT (key) DO UPDATE
                  SET value = EXCLUDED.value, updated_at = NOW()
                """,
                "ceo:boot_state_current",
                json.dumps(payload),
            )
        finally:
            await conn.close()

    try:
        asyncio.run(_run())
    except (OSError, RuntimeError, Exception) as exc:  # noqa: BLE001 — best-effort
        logger.warning("boot_state upsert failed: %s", exc)


def _parse_weekly_cap_until(resets: str) -> str:
    """Cap state string. Stores raw resets string when we can't parse a date."""
    return f"weekly_cap_until={resets}"


def process_callsign(callsign: str, now: datetime) -> AgentState:
    """One agent's full per-cycle evaluation. Returns the snapshot state."""
    pane = _capture_pane_tail(CALLSIGN_TO_TMUX[callsign], lines=BUSY_GUARD_PANE_LINES)
    idle_min, last_activity = _compute_idle_minutes(callsign, now)
    state = AgentState(
        callsign=callsign,
        last_activity=last_activity,
        idle_minutes=idle_min,
    )

    weekly_hit, resets = detect_weekly_cap(pane)
    if weekly_hit:
        state.rate_limit_state = _parse_weekly_cap_until(resets or "unknown")
        last = _last_escalation_at.get(f"weekly:{callsign}")
        if last is None or (now - last) >= timedelta(minutes=ESCALATION_DEDUP_MINUTES):
            post_ceo(
                f":octagonal_sign: [{callsign}] hit Anthropic weekly cap. "
                f"Resets: {resets or 'unknown'}. Daemon will suppress retries "
                f"until reset. Source: pane capture (idle_enforcer KEI-45)."
            )
            _last_escalation_at[f"weekly:{callsign}"] = now
        return state

    if pane and THROTTLE_RE.search(pane):
        dur_min, source = _extract_throttle_duration(pane)
        state.rate_limit_state = f"transient(retry_in={dur_min}m,source={source})"
        return state

    if detect_busy(pane, callsign):
        # Agent is actively working; do not dispatch — but BUSY counts as activity.
        state.idle_minutes = 0
        state.last_activity = now.isoformat()
        return state

    work = bd_ready_for(callsign)
    state.work_available_count = len(work)

    if idle_min >= IDLE_DISPATCH_MINUTES and work:
        first = work[0]
        issue_id = first.get("id", "unknown")
        title = (first.get("title", "no title"))[:160]
        brief = (
            f"[ENFORCER:KEI-45] Idle {idle_min}m + ready work — pick up {issue_id}: "
            f"{title}. Run: bd update {issue_id} --claim. Source: idle_enforcer."
        )
        if inject_dispatch(callsign, brief):
            state.last_dispatch_at = now.isoformat()

    if idle_min >= IDLE_ESCALATION_MINUTES and work:
        last = _last_escalation_at.get(f"idle:{callsign}")
        if last is None or (now - last) >= timedelta(minutes=ESCALATION_DEDUP_MINUTES):
            post_ceo(
                f":hourglass_flowing_sand: [{callsign}] idle {idle_min}m with "
                f"{len(work)} ready work item(s). Mechanical inject attempted; "
                f"escalating to #ceo (idle_enforcer KEI-45)."
            )
            _last_escalation_at[f"idle:{callsign}"] = now

    return state


def run_cycle(now: datetime | None = None) -> dict[str, AgentState]:
    """One pass over all callsigns. Returns per-callsign state."""
    ts = now or datetime.now(UTC)
    states: dict[str, AgentState] = {}
    for cs in CALLSIGN_TO_TMUX:
        try:
            states[cs] = process_callsign(cs, ts)
        except (OSError, RuntimeError, Exception) as exc:  # noqa: BLE001
            logger.warning("cycle failed for %s: %s", cs, exc)
            states[cs] = AgentState(callsign=cs, last_activity=ts.isoformat(), idle_minutes=0)
    upsert_boot_state(states)
    return states


def main() -> int:
    once = "--once" in sys.argv
    logger.info(
        "idle_enforcer starting (interval=%ds, dispatch>=%dm, escalate>=%dm, once=%s)",
        IDLE_CHECK_INTERVAL_SECONDS,
        IDLE_DISPATCH_MINUTES,
        IDLE_ESCALATION_MINUTES,
        once,
    )
    while True:
        run_cycle()
        if once:
            return 0
        time.sleep(IDLE_CHECK_INTERVAL_SECONDS)


if __name__ == "__main__":
    sys.exit(main())
