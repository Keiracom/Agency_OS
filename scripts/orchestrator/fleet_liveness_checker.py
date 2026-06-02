#!/usr/bin/env python3
"""fleet_liveness_checker.py — on-box ground-truth liveness probe (5min cadence).

Invoked by fleet-liveness-checker.timer every 5 minutes. For each callsign
in CALLSIGNS, probes signals from outside the agent's own process and writes
one row to public.fleet_liveness:

  1. tmux_alive   — `tmux has-session -t <callsign>` (or <callsign>bot fallback
                    for elliottbot / maxbot)
  2. nats_last_publish_at — last message timestamp on
                            keiracom.agent.status.<callsign> via NATS JetStream
  3. backend_health — trimmed body from http://localhost:8000/health (256 chars)
  4. active_task_id — current claimed-active task for the callsign
  5. reported_callsign — CALLSIGN env var actually exported in the agent's
                         tmux pane process tree (pane leader + descendants).
                         Catches the bug where an agent runs under the wrong
                         callsign without anyone noticing.
  6. callsign_match — TRUE/FALSE when reported_callsign is observable;
                      NULL when the pane has no readable process or env var.

Side effect: for every callsign with tmux_alive=True AND active_task_id IS NOT
NULL, also updates public.tasks.heartbeat_at=NOW() — revives the heartbeat
column as a liveness signal for agents that have not wired the per-task
heartbeat themselves.

All external calls are fail-graceful: a missing tmux session, NATS down,
backend unreachable, or DB read error never crash the script. The timer
keeps firing.

Exit codes:
  0 — all writes attempted (some may have failed gracefully and logged)
  2 — fatal configuration error (DATABASE_URL unset)
"""

from __future__ import annotations

import json
import logging
import os
import shutil
import subprocess
import sys
from datetime import UTC, datetime

logger = logging.getLogger("fleet_liveness_checker")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

CALLSIGNS = ["elliot", "aiden", "max", "atlas", "orion", "scout", "nova"]

# tmux session name overrides — elliot runs in `elliottbot`, max in `maxbot`.
TMUX_ALIASES = {"elliot": "elliottbot", "max": "maxbot"}

BACKEND_HEALTH_URL = "http://localhost:8000/health"
BACKEND_TIMEOUT_SEC = 2
NATS_TIMEOUT_SEC = 3
NATS_STREAM = "agent_status"
NATS_SUBJECT_FMT = "keiracom.agent.status.{callsign}"
HEALTH_BODY_MAX = 256

_INSERT_SQL = """
INSERT INTO public.fleet_liveness
    (callsign, checked_at, tmux_alive, nats_last_publish_at, backend_health,
     active_task_id, reported_callsign, callsign_match)
VALUES (%s, NOW(), %s, %s, %s, %s, %s, %s)
"""

_CALLSIGN_PROBE_MAX_DEPTH = 4

_ACTIVE_TASK_SQL = """
SELECT id::text FROM public.tasks
WHERE claimed_by = %s AND status = 'active'
ORDER BY claimed_at DESC NULLS LAST
LIMIT 1
"""

_HEARTBEAT_UPDATE_SQL = """
UPDATE public.tasks SET heartbeat_at = NOW()
WHERE claimed_by = %s AND status = 'active'
"""


def _resolve_dsn() -> str | None:
    raw = os.environ.get("DATABASE_URL") or os.environ.get("SUPABASE_DB_URL", "")
    if not raw:
        return None
    return raw.replace("postgresql+asyncpg://", "postgresql://", 1)


def _probe_tmux(callsign: str) -> bool:
    """True when tmux session exists. Tries <callsign> then <callsign>bot."""
    if not shutil.which("tmux"):
        return False
    candidates = [callsign]
    alias = TMUX_ALIASES.get(callsign)
    if alias and alias != callsign:
        candidates.append(alias)
    for name in candidates:
        try:
            # `=<name>` forces exact-match — otherwise tmux uses prefix matching
            # and e.g. `nova-paused` would satisfy a probe for `nova`.
            result = subprocess.run(
                ["tmux", "has-session", "-t", f"={name}"],
                capture_output=True,
                timeout=3,
                check=False,
            )
            if result.returncode == 0:
                return True
        except (subprocess.TimeoutExpired, OSError) as exc:
            logger.debug("tmux probe %s failed: %s", name, exc)
    return False


def _read_callsign_env(pid: int) -> str | None:
    """Read CALLSIGN= out of /proc/<pid>/environ, or None if absent/unreadable."""
    try:
        with open(f"/proc/{pid}/environ", "rb") as fh:
            data = fh.read()
    except (OSError, PermissionError):
        return None
    prefix = b"CALLSIGN="
    for raw in data.split(b"\x00"):
        if raw.startswith(prefix):
            return raw[len(prefix) :].decode("utf-8", errors="replace").strip() or None
    return None


def _probe_reported_callsign(callsign: str) -> str | None:
    """Return the CALLSIGN env var exported in the agent's tmux pane process tree.

    Walks the pane leader PID and its descendants (claude is typically a child of
    a shell that may not itself export CALLSIGN). Returns the first observed
    value or None if no descendant exports CALLSIGN. Fail-graceful on every
    subprocess / proc-fs path — exceptions log at DEBUG and return None.
    """
    if not shutil.which("tmux"):
        return None
    candidates = [callsign]
    alias = TMUX_ALIASES.get(callsign)
    if alias and alias != callsign:
        candidates.append(alias)
    for name in candidates:
        try:
            result = subprocess.run(
                ["tmux", "list-panes", "-t", f"={name}", "-F", "#{pane_pid}"],
                capture_output=True,
                timeout=3,
                check=False,
                text=True,
            )
        except (subprocess.TimeoutExpired, OSError) as exc:
            logger.debug("reported-callsign list-panes %s failed: %s", name, exc)
            continue
        if result.returncode != 0:
            continue
        for line in result.stdout.splitlines():
            pid_str = line.strip()
            if not pid_str.isdigit():
                continue
            found = _walk_pid_tree_for_callsign(int(pid_str))
            if found:
                return found
    return None


def _walk_pid_tree_for_callsign(root_pid: int) -> str | None:
    """BFS over PID + descendants (depth-bounded), return first CALLSIGN seen."""
    stack: list[tuple[int, int]] = [(root_pid, 0)]
    seen: set[int] = set()
    while stack:
        pid, depth = stack.pop()
        if pid in seen or depth > _CALLSIGN_PROBE_MAX_DEPTH:
            continue
        seen.add(pid)
        value = _read_callsign_env(pid)
        if value:
            return value
        try:
            result = subprocess.run(
                ["pgrep", "-P", str(pid)],
                capture_output=True,
                timeout=2,
                check=False,
                text=True,
            )
        except (subprocess.TimeoutExpired, OSError) as exc:
            logger.debug("pgrep -P %d failed: %s", pid, exc)
            continue
        if result.returncode != 0:
            continue
        for line in result.stdout.splitlines():
            child = line.strip()
            if child.isdigit():
                stack.append((int(child), depth + 1))
    return None


def _probe_nats_last_publish(callsign: str) -> datetime | None:
    """Last message timestamp on keiracom.agent.status.<callsign>, or None."""
    if not shutil.which("nats"):
        return None
    subject = NATS_SUBJECT_FMT.format(callsign=callsign)
    try:
        result = subprocess.run(
            ["nats", "stream", "get", NATS_STREAM, "--last-for", subject, "--json"],
            capture_output=True,
            timeout=NATS_TIMEOUT_SEC,
            check=False,
            text=True,
        )
    except (subprocess.TimeoutExpired, OSError) as exc:
        logger.debug("nats probe %s failed: %s", subject, exc)
        return None
    if result.returncode != 0 or not result.stdout.strip():
        return None
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError:
        return None
    ts_raw = payload.get("time") or payload.get("timestamp")
    if not ts_raw:
        return None
    try:
        return datetime.fromisoformat(ts_raw.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return None


def _probe_backend_health() -> str | None:
    """Trimmed response body from BACKEND_HEALTH_URL, or None on failure."""
    if not shutil.which("curl"):
        return None
    try:
        result = subprocess.run(
            ["curl", "-sS", "-m", str(BACKEND_TIMEOUT_SEC), "-f", BACKEND_HEALTH_URL],
            capture_output=True,
            timeout=BACKEND_TIMEOUT_SEC + 1,
            check=False,
            text=True,
        )
    except (subprocess.TimeoutExpired, OSError) as exc:
        logger.debug("backend health probe failed: %s", exc)
        return None
    if result.returncode != 0:
        return None
    body = (result.stdout or "").strip()
    return body[:HEALTH_BODY_MAX] if body else None


def _query_active_task(cur, callsign: str) -> str | None:
    try:
        cur.execute(_ACTIVE_TASK_SQL, (callsign,))
        row = cur.fetchone()
        return row[0] if row else None
    except Exception as exc:  # noqa: BLE001 — fail-graceful per script contract
        logger.warning("active-task lookup failed for %s: %s", callsign, exc)
        return None


def _revive_task_heartbeat(cur, callsign: str) -> None:
    try:
        cur.execute(_HEARTBEAT_UPDATE_SQL, (callsign,))
    except Exception as exc:  # noqa: BLE001
        logger.warning("heartbeat revive failed for %s: %s", callsign, exc)


def main() -> int:
    dsn = _resolve_dsn()
    if not dsn:
        print("fleet_liveness_checker: DATABASE_URL unset", file=sys.stderr)
        return 2

    try:
        import psycopg
    except ImportError:
        print("fleet_liveness_checker: psycopg not installed", file=sys.stderr)
        return 2

    written = 0
    revived = 0
    started = datetime.now(UTC)

    try:
        with psycopg.connect(dsn, prepare_threshold=None) as conn:
            with conn.cursor() as cur:
                for callsign in CALLSIGNS:
                    tmux_alive = _probe_tmux(callsign)
                    nats_ts = _probe_nats_last_publish(callsign)
                    health = _probe_backend_health()
                    active_task = _query_active_task(cur, callsign)
                    reported = _probe_reported_callsign(callsign) if tmux_alive else None
                    match = (reported == callsign) if reported is not None else None

                    try:
                        cur.execute(
                            _INSERT_SQL,
                            (
                                callsign,
                                tmux_alive,
                                nats_ts,
                                health,
                                active_task,
                                reported,
                                match,
                            ),
                        )
                        written += 1
                    except Exception as exc:  # noqa: BLE001
                        logger.warning("fleet_liveness insert failed for %s: %s", callsign, exc)
                        conn.rollback()
                        continue

                    if tmux_alive and active_task:
                        _revive_task_heartbeat(cur, callsign)
                        revived += 1

            conn.commit()
    except Exception as exc:  # noqa: BLE001 — fail-graceful at the outer connection level
        logger.warning("fleet_liveness_checker: DB error — fail-open: %s", exc)
        return 0

    elapsed = (datetime.now(UTC) - started).total_seconds()
    logger.info(
        "fleet_liveness_checker: wrote %d/%d rows, revived %d task heartbeats in %.2fs",
        written,
        len(CALLSIGNS),
        revived,
        elapsed,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
