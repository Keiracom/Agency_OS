#!/usr/bin/env python3
"""elliot_polling_loop.py — KEI-17 mechanical orchestrator polling loop.

Per Dave priority-reset ts 1778570450 + Elliot KEI-17 dispatch. Closes the
idle-agent miss-mode permanently: every cycle (1 min peak, 60 min overnight)
polls 4 sources and dispatches if any signals are actionable.

Sources:
  1. bd ready (--json)            — unblocked Beads issues
  2. Linear In-Progress staleness — issues with no activity > STALE_HOURS
  3. Idle agents                  — outbox mtime / inbox empty for > IDLE_MINUTES
  4. Prefect flow failures        — failed flow runs in last cycle window

Action surface:
  - bd ready + idle agent      → [DISPATCH-PROPOSAL:<callsign>] in #execution
  - Linear stale issue         → [PROPOSE:elliot] in #ceo (Dave-facing)
  - Prefect failure            → new Linear KEI tagged pipeline-incident
                                   (script logs intent; KEI creation deferred to
                                    follow-up if Linear MCP write API is wired)

Cycle is best-effort: source failures are isolated + logged; downstream sends
are wrapped so one bad source can't block the other three.

Time-of-day gate (per dispatch spec): 07:00–21:00 AEST (21:00–11:00 UTC next
day) runs every minute; outside that window the loop short-circuits unless the
minute hits :00 (hourly cadence overnight). Implemented in code, not systemd —
keeps the timer dumb (minutely) and the schedule testable.

Honors silent-is-status: no pings if zero signals. Only emits when there's
an actual dispatch target.
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("elliot_polling_loop")

# Time-of-day window. AEST = UTC+10.
PEAK_HOURS_UTC = set(list(range(21, 24)) + list(range(0, 11)))  # 21–10 UTC inclusive
STALE_LINEAR_HOURS = 12
IDLE_AGENT_MINUTES = 30
PREFECT_WINDOW_MINUTES = 5

EXECUTION_CHANNEL_NAME = "#execution"
CEO_CHANNEL_NAME = "#ceo"

CLONES = ("atlas", "orion", "scout")
PRIMES = ("aiden", "max")  # elliot orchestrates; she doesn't dispatch to herself


@dataclass
class CycleSignals:
    bd_ready: list[dict]
    linear_stale: list[dict]
    idle_agents: list[str]
    prefect_failures: list[dict]

    def is_silent(self) -> bool:
        return not (self.bd_ready or self.linear_stale or self.idle_agents or self.prefect_failures)


# Time-of-day gate ───────────────────────────────────────────────────────────


def should_run_now(now: datetime | None = None) -> bool:
    """True if the current UTC hour is in peak AEST window OR minute==0 overnight.

    Peak (1-min cadence): UTC hours in PEAK_HOURS_UTC.
    Overnight throttle (60-min cadence): UTC hours NOT in peak, only when minute==0.
    """
    n = now or datetime.now(UTC)
    if n.hour in PEAK_HOURS_UTC:
        return True
    return n.minute == 0


# Source pollers ─────────────────────────────────────────────────────────────


def poll_bd_ready() -> list[dict]:
    try:
        proc = subprocess.run(["bd", "ready", "--json"], capture_output=True, text=True, timeout=10)
        if proc.returncode != 0:
            logger.warning("bd ready exit %d: %s", proc.returncode, proc.stderr[:200])
            return []
        return json.loads(proc.stdout or "[]")
    except (subprocess.TimeoutExpired, FileNotFoundError, json.JSONDecodeError, OSError) as exc:
        logger.warning("bd ready failed: %s", exc)
        return []


def poll_linear_stale(now: datetime | None = None) -> list[dict]:
    """Linear In-Progress issues with no activity > STALE_LINEAR_HOURS."""
    api_key = os.environ.get("LINEAR_API_KEY", "")
    if not api_key:
        return []
    cutoff = (now or datetime.now(UTC)) - timedelta(hours=STALE_LINEAR_HOURS)
    query = """
    query StaleIssues($since: DateTimeOrDuration!) {
      issues(filter: {state: {type: {eq: "started"}}, updatedAt: {lt: $since}}, first: 20) {
        nodes { identifier title updatedAt assignee { name } }
      }
    }
    """
    try:
        req = urllib.request.Request(
            "https://api.linear.app/graphql",
            data=json.dumps({"query": query, "variables": {"since": cutoff.isoformat()}}).encode(),
            headers={"Authorization": api_key, "Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            body = json.loads(resp.read())
        return body.get("data", {}).get("issues", {}).get("nodes", []) or []
    except (urllib.error.URLError, json.JSONDecodeError, KeyError, OSError) as exc:
        logger.warning("Linear stale query failed: %s", exc)
        return []


def poll_idle_agents(now: datetime | None = None) -> list[str]:
    """Callsigns whose last_activity_at is older than IDLE_AGENT_MINUTES per
    `keiracom_admin.agent_status_observations` (Scout's reuse-over-rebuild call
    in docs/wave2/polling_loop_design.md).

    Uses the existing 15-min `collect_agent_status` observability layer rather
    than re-deriving idleness from /tmp outbox mtime. Best-effort: DB failure
    or DSN-unset returns empty list (no false idle dispatch).
    """
    dsn = os.environ.get("DATABASE_URL", "") or os.environ.get("DATABASE_URL_MIGRATIONS", "")
    if not dsn:
        return []
    cutoff = (now or datetime.now(UTC)) - timedelta(minutes=IDLE_AGENT_MINUTES)
    sql = (
        "SELECT DISTINCT ON (callsign) callsign, last_activity_at "
        "FROM keiracom_admin.agent_status_observations "
        "WHERE callsign = ANY($1::text[]) "
        "ORDER BY callsign, observed_at DESC"
    )
    candidates = list(PRIMES) + list(CLONES)
    try:
        import asyncio

        import asyncpg
    except ImportError:
        logger.warning("asyncpg not available — skipping idle-agent check")
        return []

    async def _q() -> list[str]:
        conn = await asyncpg.connect(dsn.replace("postgresql+asyncpg://", "postgresql://"))
        try:
            rows = await conn.fetch(sql, candidates)
        finally:
            await conn.close()
        return [
            r["callsign"] for r in rows if r["last_activity_at"] and r["last_activity_at"] < cutoff
        ]

    try:
        return asyncio.run(_q())
    except (OSError, RuntimeError, Exception) as exc:  # noqa: BLE001 — best-effort
        logger.warning("idle-agent query failed: %s", exc)
        return []


def poll_prefect_failures(now: datetime | None = None) -> list[dict]:
    """Failed Prefect flow runs in the last PREFECT_WINDOW_MINUTES."""
    api_url = os.environ.get("PREFECT_API_URL", "").rstrip("/")
    api_key = os.environ.get("PREFECT_API_KEY", "")
    if not api_url:
        return []
    since = (now or datetime.now(UTC)) - timedelta(minutes=PREFECT_WINDOW_MINUTES)
    body = json.dumps(
        {
            "flow_runs": {
                "state": {"type": {"any_": ["FAILED", "CRASHED"]}},
                "end_time": {"after_": since.isoformat()},
            },
            "limit": 20,
        }
    ).encode()
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    try:
        req = urllib.request.Request(f"{api_url}/flow_runs/filter", data=body, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read()) or []
    except (urllib.error.URLError, json.JSONDecodeError, OSError) as exc:
        logger.warning("Prefect failure query failed: %s", exc)
        return []


# Aggregator + dispatcher ────────────────────────────────────────────────────


def collect_signals(now: datetime | None = None) -> CycleSignals:
    return CycleSignals(
        bd_ready=poll_bd_ready(),
        linear_stale=poll_linear_stale(now),
        idle_agents=poll_idle_agents(now),
        prefect_failures=poll_prefect_failures(now),
    )


def compose_dispatches(signals: CycleSignals) -> list[tuple[str, str]]:
    """Return list of (channel_name, message_text) tuples for this cycle.

    Pairing rule: each idle agent gets one bd-ready item (FIFO). Linear stale
    + Prefect failures escalate to #ceo as [PROPOSE:elliot]. No LLM call —
    keeps this deterministic + testable; LLM phrasing is a v2 enhancement.
    """
    dispatches: list[tuple[str, str]] = []

    # Pair idle agents with bd-ready issues, FIFO. strict=False intentional:
    # the lists have independent lengths and we truncate to the shorter.
    paired = list(zip(signals.idle_agents, signals.bd_ready, strict=False))
    for callsign, issue in paired:
        issue_id = issue.get("id", "?")
        title = issue.get("title", "?")
        priority = issue.get("priority", "?")
        msg = (
            f"[DISPATCH-PROPOSAL:{callsign}] {issue_id} (priority={priority}) — {title}\n"
            f"Polled by KEI-17 elliot_polling_loop; agent {callsign} idle "
            f"≥{IDLE_AGENT_MINUTES}m, this Beads item is ready (no blockers)."
        )
        dispatches.append((EXECUTION_CHANNEL_NAME, msg))

    if signals.linear_stale:
        lines = [
            f"  - {it.get('identifier', '?')} {it.get('title', '?')} "
            f"(last update {it.get('updatedAt', '?')}, assignee {it.get('assignee', {}).get('name', '?')})"
            for it in signals.linear_stale[:10]
        ]
        msg = (
            f"[PROPOSE:elliot] Linear stale-In-Progress sweep — "
            f"{len(signals.linear_stale)} issue(s) untouched > {STALE_LINEAR_HOURS}h:\n"
            + "\n".join(lines)
        )
        dispatches.append((CEO_CHANNEL_NAME, msg))

    if signals.prefect_failures:
        lines = [
            f"  - flow_run {fr.get('id', '?')[:8]} state={fr.get('state', {}).get('type', '?')} "
            f"end={fr.get('end_time', '?')}"
            for fr in signals.prefect_failures[:10]
        ]
        msg = (
            f"[PROPOSE:elliot] Prefect failure sweep — "
            f"{len(signals.prefect_failures)} flow(s) failed/crashed in last "
            f"{PREFECT_WINDOW_MINUTES}m:\n"
            + "\n".join(lines)
            + "\nIntent: create Linear KEI tagged pipeline-incident (manual until Linear MCP write wired)."
        )
        dispatches.append((CEO_CHANNEL_NAME, msg))

    return dispatches


def send_dispatch(channel: str, text: str) -> None:
    """Post via scripts/slack_relay.py. Best-effort; relay failure logs + drops."""
    relay = Path(__file__).resolve().parent / "slack_relay.py"
    flag = "-g" if channel == EXECUTION_CHANNEL_NAME else "-c"
    try:
        subprocess.run(
            ["python3", str(relay), flag, text]
            if flag == "-g"
            else ["python3", str(relay), "-c", channel.lstrip("#"), text],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
    except (subprocess.TimeoutExpired, OSError) as exc:
        logger.warning("slack_relay failed for %s: %s", channel, exc)


# Entry point ────────────────────────────────────────────────────────────────


def run_cycle(now: datetime | None = None) -> int:
    """Returns the number of dispatches sent (0 = silent cycle)."""
    if not should_run_now(now):
        logger.info("outside peak window + minute!=0 → silent skip")
        return 0
    signals = collect_signals(now)
    if signals.is_silent():
        logger.info(
            "no signals this cycle (bd_ready=%d, linear_stale=%d, idle=%d, prefect=%d)",
            len(signals.bd_ready),
            len(signals.linear_stale),
            len(signals.idle_agents),
            len(signals.prefect_failures),
        )
        return 0
    dispatches = compose_dispatches(signals)
    for channel, text in dispatches:
        send_dispatch(channel, text)
    return len(dispatches)


def main() -> int:
    sent = run_cycle()
    logger.info("cycle complete — %d dispatch(es) sent", sent)
    return 0


if __name__ == "__main__":
    sys.exit(main())
