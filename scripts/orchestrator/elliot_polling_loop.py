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
# KEI-27 — broader "silently died" stale threshold. Linear KEI In Progress
# for >24h with no commit/comment/status change → #ceo alert. Distinct lane
# from STALE_LINEAR_HOURS (12h orchestrator-stale): KEI_STALE captures work
# that's quietly dropped between sessions.
STALE_KEI_HOURS = 24
IDLE_AGENT_MINUTES = 30
PREFECT_WINDOW_MINUTES = 5
# KEI-34 strict-cycle reading per Dave verbatim ts ~1778629860: 'Idle agents
# with unblocked work is the failure we're fixing. 15 minutes is too long.'
# Component 1 fires when an agent has been idle >= ORCHESTRATOR_IDLE_CYCLES *
# current_cycle_period_seconds (60s peak, 3600s off-peak).
ORCHESTRATOR_IDLE_CYCLES = 1
PEAK_CYCLE_SECONDS = 60
OFF_PEAK_CYCLE_SECONDS = 3600
# KEI-34 v3 HOLE A — canonical long-running-command patterns to detect
# detached subprocesses (e.g., Cognee ingest PID 844898 detached from
# claude session tree, invisible to pane-pid descendant walk). System-wide
# ps scan filtered by these patterns. Narrow allowlist: conservative
# false-negative bias > false-positive on incidental Python (pytest, mypy).
_LONG_RUNNING_CMD_PATTERNS: tuple[str, ...] = (
    r"cognee_ingest",
    r"pipeline_runner",
    r"ingest --streams",
    r"--scrape",
    r"cohort_runner",
)
_LONG_RUNNING_CMD_RE = re.compile("|".join(_LONG_RUNNING_CMD_PATTERNS), re.IGNORECASE)
# KEI-34 v3 HOLE B — escalate to #ceo if a callsign with an active long-
# running subprocess has not posted to #execution within this many minutes.
LONG_RUNNING_TRACK_PROGRESS_MIN = 30

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

# Duration-extraction patterns (KEI-19 GAP A fix). Two sources surface a
# numeric wait time: HTTP `retry-after: <seconds>` and Anthropic's CLI banner
# `Brewed for <N> <unit>`. Both return (duration_min, source); unknown → (0, "unknown").
_RETRY_AFTER_RE = re.compile(r"retry-?after[:\s]+(\d+)", re.IGNORECASE)
_BREWED_FOR_RE = re.compile(
    r"brewed for\s+(\d+)\s*(seconds?|secs?|minutes?|mins?|hours?|hrs?|h|m|s)?",
    re.IGNORECASE,
)


def _extract_throttle_duration(text: str) -> tuple[int, str]:
    """Return (duration_min, source) parsed from throttle text.

    source ∈ {'retry_after', 'brewed_for', 'unknown'}. Sub-minute durations
    round UP to 1 (zero-duration would re-trigger GAP A — the alert must
    always have a non-zero ETA if a duration was advertised).
    """
    m = _BREWED_FOR_RE.search(text)
    if m:
        value = int(m.group(1))
        unit = (m.group(2) or "minute").lower()
        if unit.startswith(("hour", "hr", "h")):
            return value * 60, "brewed_for"
        if unit.startswith(("min", "m")):
            return max(1, value), "brewed_for"
        return max(1, (value + 59) // 60), "brewed_for"  # seconds → ceil minutes
    m = _RETRY_AFTER_RE.search(text)
    if m:
        seconds = int(m.group(1))  # HTTP spec: retry-after value is seconds
        return max(1, (seconds + 59) // 60), "retry_after"
    return 0, "unknown"


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
    rate_limit_transitions: list[tuple[str, str, int, str]] = field(default_factory=list)
    """List of (callsign, transition, duration_min, source) where transition is
    'throttled' (first detection) or 'resumed' (clearing detection). For
    'throttled': duration_min is parsed wait-ETA (>=1 if advertised, 0 if
    unknown), source ∈ {'retry_after', 'brewed_for', 'unknown'}. For
    'resumed': duration_min is minutes-since-throttle-start, source is ''.
    (KEI-19 GAP A — source/duration on onset, not retrospective only.)"""
    # KEI-34 component 1 — agents idle >= ORCHESTRATOR_IDLE_CYCLES * cycle_period
    # (strict-cycle threshold; tighter than idle_agents which uses IDLE_AGENT_MINUTES).
    orchestrator_idle_agents: list[str] = field(default_factory=list)
    # KEI-27 — Linear KEI In Progress for >STALE_KEI_HOURS with no activity.
    # Broader "silently died" lane vs linear_stale (orchestrator stale lane).
    kei_stale: list[dict] = field(default_factory=list)
    # KEI-34 v3 HOLE B — callsigns with active long-running subprocess but
    # no #execution post within LONG_RUNNING_TRACK_PROGRESS_MIN minutes.
    long_running_silent_callsigns: list[tuple[str, int]] = field(default_factory=list)
    """List of (callsign, minutes_since_last_post)."""

    def is_silent(self) -> bool:
        return not (
            self.bd_ready
            or self.linear_stale
            or self.idle_agents
            or self.prefect_failures
            or self.rate_limit_transitions
            or self.kei_stale
            or self.long_running_silent_callsigns
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


def _query_linear_stale(hours: int, now: datetime | None) -> list[dict]:
    """Shared Linear GraphQL: state=started + updatedAt < (now-hours)."""
    api_key = os.environ.get("LINEAR_API_KEY", "")
    if not api_key:
        return []
    cutoff = (now or datetime.now(UTC)) - timedelta(hours=hours)
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
        logger.warning("Linear stale query failed (%dh): %s", hours, exc)
        return []


def poll_linear_stale(now: datetime | None = None) -> list[dict]:
    """Linear In-Progress issues with no activity > STALE_LINEAR_HOURS (12h —
    orchestrator-stale lane)."""
    return _query_linear_stale(STALE_LINEAR_HOURS, now)


def poll_kei_stale(now: datetime | None = None) -> list[dict]:
    """KEI-27: Linear KEI In Progress with no activity > STALE_KEI_HOURS (24h
    — silently-died lane). Distinct from poll_linear_stale (12h orchestrator
    lane); both stay. Reuses shared _query_linear_stale helper."""
    return _query_linear_stale(STALE_KEI_HOURS, now)


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


def _descendant_pids(pid: int) -> list[int]:
    """Walk the process tree under pid, returning all descendant PIDs.

    KEI-34 v2 Addition 3 — empirical Max diagnostic 2026-05-13:
      bash pane_pid (S 0% CPU) → bash wrapper child (S) → bash -c child (S)
      → python3 ingest grandchild (R 78% CPU). Single-level pgrep -P misses
      the long-running grandchild. Recursive walk is required.
    """
    descendants: list[int] = []
    frontier = [pid]
    seen: set[int] = {pid}
    while frontier:
        next_frontier: list[int] = []
        for p in frontier:
            try:
                proc = subprocess.run(  # noqa: S603 — controlled args, no shell, pid is int
                    ["pgrep", "-P", str(p)],
                    capture_output=True,
                    text=True,
                    timeout=3,
                    check=False,
                )
            except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
                continue
            if proc.returncode != 0:
                continue
            for line in proc.stdout.splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    child = int(line)
                except ValueError:
                    continue
                if child in seen:
                    continue
                seen.add(child)
                descendants.append(child)
                next_frontier.append(child)
        frontier = next_frontier
    return descendants


def _agent_has_active_subprocess(callsign: str) -> bool:
    """KEI-34 v2 Addition 3 — return True iff the callsign's tmux session has
    ANY descendant process in R state OR with CPU > 0%.

    Walks the full process tree under the pane_pid (per Max's diagnostic
    ts ~1778631099: bash parent S 0% CPU + python3 grandchild R 78% CPU
    is the canonical false-positive case). Single-level pgrep -P missed
    the grandchild.

    Best-effort: any subprocess/tmux failure returns False (conservative —
    don't suppress idle dispatch if we can't probe).
    """
    session = CALLSIGN_TO_TMUX.get(callsign.lower())
    if not session:
        return False
    try:
        pane_proc = subprocess.run(  # noqa: S603 — controlled args, no shell
            ["tmux", "list-panes", "-t", f"{session}:0", "-F", "#{pane_pid}"],
            capture_output=True,
            text=True,
            timeout=3,
            check=False,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return False
    if pane_proc.returncode != 0:
        return False
    try:
        pane_pid = int(pane_proc.stdout.strip().splitlines()[0])
    except (IndexError, ValueError):
        return False
    pids_to_check = [pane_pid, *_descendant_pids(pane_pid)]
    try:
        ps_proc = subprocess.run(  # noqa: S603 — controlled args, no shell
            ["ps", "-p", ",".join(str(p) for p in pids_to_check), "-o", "stat=,pcpu="],
            capture_output=True,
            text=True,
            timeout=3,
            check=False,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return False
    if ps_proc.returncode != 0:
        return False
    for line in ps_proc.stdout.splitlines():
        parts = line.split()
        if len(parts) < 2:
            continue
        stat = parts[0]
        try:
            cpu = float(parts[1])
        except ValueError:
            continue
        # R = running; CPU > 0 = active in last sample window.
        if "R" in stat or cpu > 0.0:
            return True
    # KEI-34 v3 HOLE A fallback — detached subprocess case. The canonical
    # example is Max's Cognee ingest PID 844898 reparented away from claude
    # session tree (recursive pgrep -P pane_pid misses it). System-wide ps
    # scan + canonical long-running command pattern allowlist + same-user
    # filter (single-user box = elliotbot). Narrow allowlist prevents
    # false-positives on incidental Python (pytest, mypy, etc.).
    return _system_wide_long_running_subprocess()


def _system_wide_long_running_subprocess() -> bool:
    """KEI-34 v3 HOLE A — system-wide scan for long-running detached subprocess
    matching _LONG_RUNNING_CMD_PATTERNS. Returns True if any canonical long-
    running command is active under the polling-loop user."""
    try:
        ps_proc = subprocess.run(  # noqa: S603 — controlled args, no shell
            ["ps", "-eo", "args"],
            capture_output=True,
            text=True,
            timeout=3,
            check=False,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return False
    if ps_proc.returncode != 0:
        return False
    return any(_LONG_RUNNING_CMD_RE.search(line) for line in ps_proc.stdout.splitlines())


def poll_long_running_silent(now: datetime | None = None) -> list[tuple[str, int]]:
    """KEI-34 v3 HOLE B — for each callsign with an active long-running
    subprocess, check time-since-last-Slack-post. Return list of
    (callsign, minutes_since_last_post) for those silent
    >= LONG_RUNNING_TRACK_PROGRESS_MIN.

    Reads ~/.local/state/agency-os/callsign-last-post.json written by
    scripts/slack_relay.py on every outbound. Best-effort; returns []
    on any read/parse failure.
    """
    state_path = Path(os.path.expanduser("~/.local/state/agency-os/callsign-last-post.json"))
    if not state_path.exists():
        return []
    try:
        last_posts = json.loads(state_path.read_text() or "{}")
    except (OSError, json.JSONDecodeError):
        return []
    n = now or datetime.now(UTC)
    threshold = timedelta(minutes=LONG_RUNNING_TRACK_PROGRESS_MIN)
    out: list[tuple[str, int]] = []
    for callsign in CALLSIGN_TO_TMUX:
        if not _agent_has_active_subprocess(callsign):
            continue
        last_iso = last_posts.get(callsign, "")
        if not last_iso:
            continue
        try:
            last_dt = datetime.fromisoformat(last_iso)
        except ValueError:
            continue
        elapsed = n - last_dt
        if elapsed >= threshold:
            out.append((callsign, int(elapsed.total_seconds() // 60)))
    return out


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
        timestamp_idle = asyncio.run(_q())
    except (OSError, RuntimeError, Exception) as exc:  # noqa: BLE001 — best-effort
        logger.warning("orchestrator-idle query failed: %s", exc)
        return []
    # KEI-34 v2 Addition 3 — filter out callsigns whose tmux session has an
    # active descendant subprocess (Cognee ingest / long-running tool case).
    return [cs for cs in timestamp_idle if not _agent_has_active_subprocess(cs)]


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
) -> list[tuple[str, str, int, str]]:
    """Return list of (callsign, transition, duration_min, source) for THIS cycle.

    transition ∈ {'throttled', 'resumed'}.
    For 'throttled': duration_min is the parsed wait ETA from the pane text
    (>=1 if a value was advertised, 0 if no parseable duration), and source is
    one of {'retry_after', 'brewed_for', 'unknown'} indicating which pattern
    surfaced the value (KEI-19 GAP A fix — wait duration on onset, not just
    retrospectively on resume).
    For 'resumed': duration_min is minutes-since-throttle-start; source is ''.
    """
    ts_now = now or datetime.now(UTC)
    prior = _load_throttle_state()
    next_state = dict(prior)
    transitions: list[tuple[str, str, int, str]] = []

    for callsign, session in CALLSIGN_TO_TMUX.items():
        tail = _capture_pane_tail(session)
        is_throttled = bool(THROTTLE_RE.search(tail)) if tail else False
        prev_throttled_since = prior.get(callsign)

        if is_throttled and not prev_throttled_since:
            duration_min, source = _extract_throttle_duration(tail)
            transitions.append((callsign, "throttled", duration_min, source))
            next_state[callsign] = ts_now.isoformat()
        elif not is_throttled and prev_throttled_since:
            try:
                start = datetime.fromisoformat(prev_throttled_since)
                duration_min = max(0, int((ts_now - start).total_seconds() // 60))
            except ValueError:
                duration_min = 0
            transitions.append((callsign, "resumed", duration_min, ""))
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
        kei_stale=poll_kei_stale(now),
        long_running_silent_callsigns=poll_long_running_silent(now),
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

    if signals.kei_stale:
        # KEI-27: 24h+ stale KEI alert. Dedupe against linear_stale (12h
        # subset) so we don't double-post the same issues to #ceo.
        already_in_linear_stale = {it.get("identifier") for it in signals.linear_stale}
        kei_extras = [it for it in signals.kei_stale if it.get("identifier") not in already_in_linear_stale]
        if kei_extras:
            lines = [
                f"  - {it.get('identifier', '?')} {it.get('title', '?')} "
                f"(last update {it.get('updatedAt', '?')}, assignee {(it.get('assignee') or {}).get('name', '?')})"
                for it in kei_extras[:10]
            ]
            msg = (
                f"[PROPOSE:elliot] KEI silently-died sweep — "
                f"{len(kei_extras)} issue(s) In Progress > {STALE_KEI_HOURS}h with "
                f"no commit/comment/status-change:\n"
                + "\n".join(lines)
            )
            dispatches.append((CEO_CHANNEL_NAME, msg))

    if signals.long_running_silent_callsigns:
        # KEI-34 v3 HOLE B — long-running-track-without-progress-post escalation.
        lines = [
            f"  - {cs} running long task with no progress-post for {mins}m"
            for cs, mins in signals.long_running_silent_callsigns
        ]
        msg = (
            f"[PROPOSE:elliot] Long-running track silent — "
            f"{len(signals.long_running_silent_callsigns)} callsign(s) with active "
            f"long-running subprocess and no #execution post for "
            f">{LONG_RUNNING_TRACK_PROGRESS_MIN}m:\n"
            + "\n".join(lines)
            + "\nRequest status snapshot."
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
            (cs, dur, src)
            for cs, t, dur, src in signals.rate_limit_transitions
            if t == "throttled"
        ]
        resumed = [
            (cs, dur) for cs, t, dur, _src in signals.rate_limit_transitions if t == "resumed"
        ]
        if throttled:
            # KEI-19 GAP A/B fix: surface per-agent wait ETA on onset (not just
            # on resume) and drop the "informational not actionable" framing —
            # the alert IS the action (Dave's awareness, no manual check).
            def _line(cs: str, dur: int, src: str) -> str:
                if dur > 0:
                    return f"  - {cs}: wait ~{dur}m (source: {src})"
                return f"  - {cs}: throttled (no ETA parsed)"

            lines = [_line(cs, dur, src) for cs, dur, src in throttled]
            msg = (
                f"[PROPOSE:elliot] Anthropic throttle detected — {len(throttled)} agent(s):\n"
                + "\n".join(lines)
                + "\nAuto-clearing on resume; per-agent resumed-after duration follows."
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
        _emit_dispatch_outcome_heartbeat([], None, no_work=True)
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
        _emit_dispatch_outcome_heartbeat([], signals, no_work=True)
        return 0
    dispatches = compose_dispatches(signals)
    for channel, text in dispatches:
        send_dispatch(channel, text)
    _emit_dispatch_outcome_heartbeat(dispatches, signals, no_work=False)
    return len(dispatches)


def _emit_dispatch_outcome_heartbeat(
    dispatches: list[tuple[str, str]],
    signals: CycleSignals | None,
    *,
    no_work: bool,
) -> None:
    """KEI-34 v2 Addition 1 — Better Stack dispatch-outcome heartbeat per Dave
    verbatim ts ~1778631000.

    Fires the heartbeat URL only when:
      (a) one or more dispatches were emitted this cycle, OR
      (b) no_work=True (genuine no-work state — silent skip OR is_silent()).

    If the loop runs but idle agents exist AND ready work exists AND no
    dispatch fires → no heartbeat fires → Better Stack alerts within 2 min
    (per Dave's spec).

    Env: BETTERSTACK_HB_DISPATCH_OUTCOME (operator-provisioned post-merge).
    """
    url = os.environ.get("BETTERSTACK_HB_DISPATCH_OUTCOME", "")
    if not url:
        return
    # Suppress heartbeat when there IS work but no dispatch fired — that's
    # the orchestrator-discipline-gap case BS should alert on.
    if not no_work and not dispatches:
        if signals is not None and (signals.bd_ready or signals.orchestrator_idle_agents):
            return
    try:
        subprocess.run(  # noqa: S603 — controlled args, no shell
            ["curl", "-fsS", "-m", "5", url],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except (subprocess.TimeoutExpired, OSError) as exc:
        logger.warning("BS dispatch-outcome heartbeat failed: %s", exc)


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
