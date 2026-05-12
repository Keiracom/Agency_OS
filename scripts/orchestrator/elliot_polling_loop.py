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
import re
import subprocess
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("elliot_polling_loop")

# Time-of-day window. AEST = UTC+10.
PEAK_HOURS_UTC = set(list(range(21, 24)) + list(range(0, 14)))  # 21–13 UTC inclusive = 07–23 AEST
STALE_LINEAR_HOURS = 12
IDLE_AGENT_MINUTES = 30
PREFECT_WINDOW_MINUTES = 5
# KEI-34 strict-cycle reading per Dave verbatim ts ~1778629860: 'Idle agents
# with unblocked work is the failure we're fixing. 15 minutes is too long.'
# Component 1 fires when an agent has been idle >= ORCHESTRATOR_IDLE_CYCLES *
# current_cycle_period_seconds (60s peak, 3600s off-peak).
ORCHESTRATOR_IDLE_CYCLES = 1
PEAK_CYCLE_SECONDS = 60
OFF_PEAK_CYCLE_SECONDS = 3600

EXECUTION_CHANNEL_NAME = "#execution"
CEO_CHANNEL_NAME = "#ceo"

CLONES = ("atlas", "orion", "scout")
PRIMES = ("aiden", "max")  # elliot orchestrates; she doesn't dispatch to herself

# Inbox-path map for clones (Dave directive ts ~1778584800 — polling hole A).
# Clones receive dispatches via inbox-watcher JSON drops, NOT via Slack channel
# fan-out (the listener path is uptime-sensitive; direct inbox write is the
# Layer 3 mechanical close).
# NOSONAR S5443 ×3 below: /tmp/telegram-relay-<cs>/inbox is the systemd
# inotify-watcher contract (per .claude/hooks/inbox_check_hook.sh + the
# per-callsign relay-watcher services). Cannot migrate to ~/.local/state
# without a coordinated watcher refactor. Defense-in-depth: callsign keys
# are regex-validated upstream (PR #757 state_paths.resolve_state_dir
# pattern + per_callsign_outbound_allowlist in slack_relay.py); no user
# input reaches the path string. Same justification as central_listener.py
# inbox-watcher integration.
INBOX_PATHS: dict[str, str] = {
    "atlas": "/tmp/telegram-relay-atlas/inbox",  # NOSONAR
    "orion": "/tmp/telegram-relay-orion/inbox",  # NOSONAR
    "scout": "/tmp/telegram-relay-scout/inbox",  # NOSONAR
}


# tmux session name per callsign (empirical 2026-05-12: elliot+max sessions
# are named with -bot suffix; clones + aiden use bare callsign).
CALLSIGN_TO_TMUX: dict[str, str] = {
    "elliot": "elliottbot",
    "aiden": "aiden",
    "max": "maxbot",
    "atlas": "atlas",
    "orion": "orion",
    "scout": "scout",
}

# Anthropic throttle signal patterns. Case-insensitive substring match on the
# last 10 lines of the agent's tmux pane. Anchored loosely — agents writing
# the string 'rate limit' into source code mid-edit will trip false positives,
# but the alternative is missing the actual throttle. Acceptable tradeoff per
# Dave directive ts ~1778619750.
THROTTLE_PATTERNS: tuple[str, ...] = (
    r"rate limit",
    r"\b429\b",
    r"retry-?after",
    r"brewed for",
)
THROTTLE_RE = re.compile("|".join(THROTTLE_PATTERNS), re.IGNORECASE)


def _cycle_period_seconds(now: datetime | None = None) -> int:
    """KEI-34: return the current polling-cycle period in seconds.
    Peak hours = 60s (run-every-minute); off-peak = 3600s (run-every-hour).
    Used by _orchestrator_discipline_check to enforce strict-cycle staleness.
    """
    n = now or datetime.now(UTC)
    if n.hour in PEAK_HOURS_UTC:
        return PEAK_CYCLE_SECONDS
    return OFF_PEAK_CYCLE_SECONDS


@dataclass
class CycleSignals:
    bd_ready: list[dict]
    linear_stale: list[dict]
    idle_agents: list[str]
    prefect_failures: list[dict]
    rate_limit_transitions: list[tuple[str, str, int]] = field(default_factory=list)
    # KEI-34 component 1 — agents idle >= ORCHESTRATOR_IDLE_CYCLES * cycle_period
    # (strict-cycle threshold; tighter than idle_agents which uses IDLE_AGENT_MINUTES).
    orchestrator_idle_agents: list[str] = field(default_factory=list)
    """List of (callsign, transition, duration_min) where transition is
    'throttled' (first detection) or 'resumed' (clearing detection). Duration
    is minutes-since-throttle-start for 'resumed' (0 for 'throttled')."""

    def is_silent(self) -> bool:
        return not (
            self.bd_ready
            or self.linear_stale
            or self.idle_agents
            or self.prefect_failures
            or self.rate_limit_transitions
        )


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


# Absolute path to the bd binary. systemd --user services inherit a restricted
# PATH that does NOT include ~/.local/bin (where pipx-installed bd lives), so a
# bare "bd" command resolves to FileNotFoundError under systemd. Path-in-code
# is more robust against future systemd unit edits — Scout's recommendation
# in docs/wave2/polling_loop_bug_diagnosis.md.
_BD_BIN = os.path.expanduser("~/.local/bin/bd")


def poll_bd_ready() -> list[dict]:
    try:
        proc = subprocess.run(  # noqa: S603 — absolute path, no shell, no user input
            [_BD_BIN, "ready", "--json"],
            capture_output=True,
            text=True,
            timeout=10,
        )
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
        # statement_cache_size=0 disables asyncpg's automatic prepared-statement
        # caching, which collides with Supabase's pgbouncer running in
        # transaction pool mode. pgbouncer's own hint surfaces in the error:
        # "pgbouncer with pool_mode set to transaction or statement does not
        # support prepared statements properly." Per Scout's diagnosis in
        # docs/wave2/polling_loop_bug_diagnosis.md.
        conn = await asyncpg.connect(
            dsn.replace("postgresql+asyncpg://", "postgresql://"),
            statement_cache_size=0,
        )
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


def poll_orchestrator_idle_agents(now: datetime | None = None) -> list[str]:
    """KEI-34 strict-cycle threshold per Dave verbatim ts ~1778629860.

    Returns callsigns whose last_activity_at is older than
    ORCHESTRATOR_IDLE_CYCLES * _cycle_period_seconds(now). At peak hours
    cycle period = 60s; off-peak = 3600s. Tighter than IDLE_AGENT_MINUTES
    (30m) — by design, per Dave's '15 minutes is too long' override.

    Same DB query shape as poll_idle_agents but with the strict cutoff.
    Best-effort: DB failure or DSN-unset returns []."""
    dsn = os.environ.get("DATABASE_URL", "") or os.environ.get("DATABASE_URL_MIGRATIONS", "")
    if not dsn:
        return []
    n = now or datetime.now(UTC)
    threshold_s = ORCHESTRATOR_IDLE_CYCLES * _cycle_period_seconds(n)
    cutoff = n - timedelta(seconds=threshold_s)
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
        return []

    async def _q() -> list[str]:
        conn = await asyncpg.connect(
            dsn.replace("postgresql+asyncpg://", "postgresql://"),
            statement_cache_size=0,
        )
        try:
            rows = await conn.fetch(sql, candidates)
        finally:
            await conn.close()
        return [
            r["callsign"]
            for r in rows
            if r["last_activity_at"] and r["last_activity_at"] < cutoff
        ]

    try:
        return asyncio.run(_q())
    except (OSError, RuntimeError, Exception) as exc:  # noqa: BLE001 — best-effort
        logger.warning("orchestrator-idle query failed: %s", exc)
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


# Rate-limit detection ───────────────────────────────────────────────────────
#
# Per Dave directive ts ~1778619750. Poll each callsign's tmux pane for
# Anthropic throttle signals; emit (callsign, transition, duration_min) on
# state change. State persists across cycles via JSON file at /tmp/...
#
# State machine:
#   (prev=clean, current=clean)      → no-op
#   (prev=clean, current=throttled)  → emit ('throttled', 0); record start ts
#   (prev=throttled, current=throttled) → no-op (already alerted)
#   (prev=throttled, current=clean)  → emit ('resumed', duration_min); clear

_THROTTLE_STATE_PATH_DEFAULT = "/tmp/elliot-polling-loop-throttle-state.json"  # NOSONAR — canonical state path for systemd-user loop, not user-supplied


def _throttle_state_path() -> str:
    return os.environ.get("AGENCY_OS_THROTTLE_STATE_PATH", _THROTTLE_STATE_PATH_DEFAULT)


def _load_throttle_state() -> dict[str, str]:
    """Return {callsign: throttled_since_iso}. Empty dict on missing/corrupt file."""
    p = Path(_throttle_state_path())
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text() or "{}")
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning("throttle state load failed: %s", exc)
        return {}


def _save_throttle_state(state: dict[str, str]) -> None:
    p = Path(_throttle_state_path())
    try:
        p.write_text(json.dumps(state, indent=2, sort_keys=True))
    except OSError as exc:
        logger.warning("throttle state save failed: %s", exc)


def _capture_pane_tail(session: str, lines: int = 10) -> str:
    try:
        proc = subprocess.run(  # noqa: S603 — controlled args, no shell
            ["tmux", "capture-pane", "-t", f"{session}:0", "-p"],
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return ""
    if proc.returncode != 0:
        return ""
    out_lines = proc.stdout.splitlines()
    return "\n".join(out_lines[-lines:])


def poll_rate_limited_agents(
    now: datetime | None = None,
) -> list[tuple[str, str, int]]:
    """Return list of (callsign, transition, duration_min) for THIS cycle.

    transition ∈ {'throttled', 'resumed'}. duration_min is 0 for 'throttled'
    and minutes-since-throttle-start for 'resumed'.
    """
    ts_now = now or datetime.now(UTC)
    prior = _load_throttle_state()
    next_state = dict(prior)
    transitions: list[tuple[str, str, int]] = []

    for callsign, session in CALLSIGN_TO_TMUX.items():
        tail = _capture_pane_tail(session)
        is_throttled = bool(THROTTLE_RE.search(tail)) if tail else False
        prev_throttled_since = prior.get(callsign)

        if is_throttled and not prev_throttled_since:
            transitions.append((callsign, "throttled", 0))
            next_state[callsign] = ts_now.isoformat()
        elif not is_throttled and prev_throttled_since:
            try:
                start = datetime.fromisoformat(prev_throttled_since)
                duration_min = max(0, int((ts_now - start).total_seconds() // 60))
            except ValueError:
                duration_min = 0
            transitions.append((callsign, "resumed", duration_min))
            next_state.pop(callsign, None)
        # else: no transition

    if next_state != prior:
        _save_throttle_state(next_state)

    return transitions


# Aggregator + dispatcher ────────────────────────────────────────────────────


def collect_signals(now: datetime | None = None) -> CycleSignals:
    return CycleSignals(
        bd_ready=poll_bd_ready(),
        linear_stale=poll_linear_stale(now),
        idle_agents=poll_idle_agents(now),
        prefect_failures=poll_prefect_failures(now),
        rate_limit_transitions=poll_rate_limited_agents(now),
        orchestrator_idle_agents=poll_orchestrator_idle_agents(now),
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
        # Clones receive dispatches via inbox-watcher JSON (Dave directive
        # ts ~1778584800 polling hole A — direct write, not Slack fan-out).
        # Primes (aiden/max) get the #execution post for human visibility.
        if callsign in CLONES:
            dispatches.append((f"inbox:{callsign}", msg))
        else:
            dispatches.append((EXECUTION_CHANNEL_NAME, msg))

    if signals.linear_stale:
        lines = [
            f"  - {it.get('identifier', '?')} {it.get('title', '?')} "
            # `(it.get('assignee') or {})` — Linear returns assignee=null on
            # unassigned issues (key present, value None); plain default-{}
            # access returns None and .get('name') raises AttributeError.
            f"(last update {it.get('updatedAt', '?')}, assignee {(it.get('assignee') or {}).get('name', '?')})"
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

    if signals.rate_limit_transitions:
        throttled = [
            (cs, dur) for cs, t, dur in signals.rate_limit_transitions if t == "throttled"
        ]
        resumed = [
            (cs, dur) for cs, t, dur in signals.rate_limit_transitions if t == "resumed"
        ]
        if throttled:
            names = ", ".join(cs for cs, _ in throttled)
            msg = (
                f"[PROPOSE:elliot] Anthropic throttle detected — {len(throttled)} agent(s): {names}.\n"
                f"Throttle signal grep on tmux pane tail (rate limit / 429 / retry-after / brewed). "
                f"Agents will resume on next clean cycle; this is informational not actionable."
            )
            dispatches.append((CEO_CHANNEL_NAME, msg))
        if resumed:
            lines = [f"  - {cs} resumed after {dur}m throttle" for cs, dur in resumed]
            msg = (
                f"[PROPOSE:elliot] Anthropic throttle cleared — {len(resumed)} agent(s):\n"
                + "\n".join(lines)
            )
            dispatches.append((CEO_CHANNEL_NAME, msg))

    _orchestrator_discipline_check(signals, dispatches)
    return dispatches


def _orchestrator_discipline_check(signals: CycleSignals, dispatches: list[tuple[str, str]]) -> None:
    """KEI-34 component 1: surface orchestrator-discipline gap to #ceo when
    bd_ready has unblocked items AND any agent is idle ≥1 cycle AND
    compose_dispatches did NOT pair every idle agent (or no dispatch fired).

    Per Dave verbatim ts ~1778629860 strict-cycle override:
      'KEI-34 threshold: 1 polling cycle. Not 15 minutes. Idle agents with
       unblocked work is the failure we're fixing.'

    Uses signals.orchestrator_idle_agents (gated by ORCHESTRATOR_IDLE_CYCLES *
    _cycle_period_seconds — 60s peak, 3600s off-peak). Distinct from
    signals.idle_agents which is gated by IDLE_AGENT_MINUTES (30m, used for
    the normal idle×ready pairing dispatch).

    Fire conditions (EITHER):
      (1) bd_ready has unblocked items AND zero idle-this-cycle agents have
          been paired by compose_dispatches yet (compose_dispatches uses
          idle_agents which is the looser 30m threshold — strict-cycle agents
          may be a subset; if no strict-cycle agents got paired, we fire).
      (2) Excess unblocked ready work beyond the dispatched pairs.

    Mutates dispatches list in place. Always returns None.
    """
    ready_n = len(signals.bd_ready)
    if ready_n == 0:
        return
    strict_idle = list(signals.orchestrator_idle_agents)
    strict_idle_n = len(strict_idle)
    loose_idle_n = len(signals.idle_agents)
    paired_n = min(ready_n, loose_idle_n)
    excess_ready = ready_n - paired_n
    # Fire when:
    #   (i)  strict-idle agents exist but compose_dispatches yielded fewer
    #        pairings than strict-idle count (strict-idle ⊆ loose-idle, so
    #        we expect every strict-idle to be in pairs)
    #   (ii) excess ready work beyond loose pairing
    #   (iii) zero loose-idle but non-zero ready
    fire = False
    if strict_idle_n > 0 and paired_n < strict_idle_n:
        fire = True
    if excess_ready > 0:
        fire = True
    if loose_idle_n == 0 and ready_n > 0:
        fire = True
    if not fire:
        return
    strict_idle_summary = ", ".join(strict_idle) if strict_idle else "none"
    top = signals.bd_ready[0]
    msg = (
        f"[PROPOSE:elliot] {ready_n} unblocked item(s), "
        f"{strict_idle_n} agent(s) idle ≥1 cycle, "
        f"{loose_idle_n} agent(s) idle ≥{IDLE_AGENT_MINUTES}m, "
        f"{paired_n} paired — orchestrator-discipline gap. "
        f"Strict-idle: {strict_idle_summary}. "
        f"Top ready: {top.get('id', '?')} (P{top.get('priority', '?')})."
    )
    dispatches.append((CEO_CHANNEL_NAME, msg))


def _write_inbox_dispatch(callsign: str, text: str) -> None:
    """Write a dispatch JSON to the clone's inbox directory (Dave polling hole A
    fix ts ~1778584800). Clones' inbox-watchers pick up the file + inject into
    their tmux session. Direct write — doesn't depend on central listener
    Slack fan-out being live.
    """
    inbox = INBOX_PATHS.get(callsign)
    if not inbox:
        logger.warning("no inbox path for callsign %r — dropping dispatch", callsign)
        return
    inbox_dir = Path(inbox)
    if not inbox_dir.is_dir():
        logger.warning("inbox dir %s missing — dropping dispatch", inbox)
        return
    import uuid

    payload = {
        "type": "task_dispatch",
        "from": "elliot_polling_loop",
        "brief": text,
        "polled_at": datetime.now(UTC).isoformat(),
    }
    fname = f"{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}_polling_{uuid.uuid4().hex[:8]}.json"
    target = inbox_dir / fname
    try:
        target.write_text(json.dumps(payload, indent=2))
    except OSError as exc:
        logger.warning("inbox write %s failed: %s", target, exc)


def send_dispatch(channel: str, text: str) -> None:
    """Route dispatch by target type. Best-effort; failures log + drop.

    - 'inbox:<callsign>' → write JSON to clone's inbox dir (Dave polling hole A).
    - '#execution' / '#ceo' / other → scripts/slack_relay.py.
    """
    if channel.startswith("inbox:"):
        callsign = channel.split(":", 1)[1]
        _write_inbox_dispatch(callsign, text)
        return

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
    # Defense-in-depth per Scout's peak-window diagnosis (f42cc4d4): log the
    # in-process PEAK_HOURS_UTC set every cycle so future drift between code
    # and the worktree's actual checked-out file is diff-able from log alone.
    n = now or datetime.now(UTC)
    logger.info(
        "cycle start — PEAK_HOURS_UTC=%s now=%s",
        sorted(PEAK_HOURS_UTC),
        n.isoformat(),
    )
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


def _heartbeat() -> None:
    """Better Stack heartbeat ping (Dave directive ts ~1778588500). Sent as the
    LAST step of each cycle so the monitor only ticks on a clean cycle.
    Best-effort: no key set → skip; subprocess failure → log + drop.
    """
    url = os.environ.get("BETTERSTACK_HB_ELLIOT_POLLING_LOOP", "")
    if not url:
        return
    try:
        subprocess.run(
            ["curl", "-fsS", "-m", "5", url],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except (subprocess.TimeoutExpired, OSError) as exc:
        logger.warning("betterstack heartbeat failed: %s", exc)


def main() -> int:
    sent = run_cycle()
    logger.info("cycle complete — %d dispatch(es) sent", sent)
    _heartbeat()
    return 0


if __name__ == "__main__":
    sys.exit(main())
