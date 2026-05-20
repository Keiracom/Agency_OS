"""heartbeat.py — KEI-91 / KEI-128 Gate 4: outcome + aliveness heartbeat.

Every long-running service calls `heartbeat.tick(...)` periodically. Each
tick updates a row in `public.ceo_memory` keyed `heartbeat:<service_name>`
with both:

  1. ALIVENESS — `last_tick_ts` (a recent timestamp proves the process is alive
     and reaching the database).
  2. OUTCOME counter — running count of meaningful events in the current period
     window (rows processed, webhooks HMAC-passed, etc). The monitor alerts when
     this stays at zero during a business-hours window even though `last_tick_ts`
     is recent (this is the "alive but silently broken" class — today's
     webhook-was-alive-returning-200-but-HMAC-failing pattern was exactly this).

Aliveness alone is NOT enough — a service can return HTTP 200 while doing the
wrong thing. The outcome counter forces the service to declare "I did N
meaningful things this period" instead of just "I'm still here."

The monitor lives in `scripts/orchestrator/heartbeat_monitor.py`.

Wire-up:

    from observability.heartbeat import tick

    # In the worker's main loop, after processing N rows:
    tick("completion-sync-worker", outcome_increment=N_processed, status="ok")

    # On error path:
    tick("completion-sync-worker", outcome_increment=0, status="error",
         error_message=str(exc))
"""

from __future__ import annotations

import datetime as _dt
import json
import logging
import os
from contextlib import suppress
from typing import Any

import psycopg

from src.governance.ceo_memory_writer import upsert_ceo_memory_key

logger = logging.getLogger("heartbeat")

PERIOD_SECONDS = int(os.environ.get("HEARTBEAT_PERIOD_SECONDS", "300"))  # 5 min default
HEARTBEAT_KEY_PREFIX = "heartbeat:"


def _dsn() -> str | None:
    raw = os.environ.get("DATABASE_URL") or os.environ.get("SUPABASE_DB_URL")
    if not raw:
        return None
    return raw.replace("postgresql+asyncpg://", "postgresql://", 1)


def _now() -> _dt.datetime:
    return _dt.datetime.now(_dt.UTC)


def _period_start_for(now: _dt.datetime, period_seconds: int = PERIOD_SECONDS) -> _dt.datetime:
    """Round `now` down to the start of its period bucket. Each tick falls
    into exactly one bucket; rolling over starts a fresh counter."""
    epoch = int(now.timestamp())
    bucket_epoch = (epoch // period_seconds) * period_seconds
    return _dt.datetime.fromtimestamp(bucket_epoch, tz=_dt.UTC)


def compute_next_state(
    previous: dict[str, Any] | None,
    *,
    now: _dt.datetime,
    outcome_increment: int,
    status: str,
    error_message: str | None,
    period_seconds: int = PERIOD_SECONDS,
) -> dict[str, Any]:
    """Pure function. Given previous heartbeat state + a new tick, return the
    next state. Separated from DB I/O so the period-rollover + counter logic
    is unit-testable without psycopg.
    """
    period_start = _period_start_for(now, period_seconds)
    previous_period_start: _dt.datetime | None = None
    previous_counter = 0
    if previous:
        with suppress(ValueError, TypeError):
            previous_period_start = _dt.datetime.fromisoformat(
                previous.get("last_period_start", "1970-01-01T00:00:00+00:00")
            )
        with suppress(ValueError, TypeError):
            previous_counter = int(previous.get("last_outcome_counter_value", 0))

    if previous_period_start == period_start:
        # Same bucket — accumulate.
        next_counter = previous_counter + outcome_increment
    else:
        # New bucket — reset.
        next_counter = outcome_increment

    return {
        "last_tick_ts": now.isoformat(),
        "last_period_start": period_start.isoformat(),
        "last_outcome_counter_period_seconds": period_seconds,
        "last_outcome_counter_value": next_counter,
        "last_status": status,
        "last_error_message": error_message,
    }


def _read_previous(conn: psycopg.Connection, key: str) -> dict[str, Any] | None:
    with conn.cursor() as cur:
        cur.execute("SELECT value FROM public.ceo_memory WHERE key=%s", (key,))
        row = cur.fetchone()
    if not row:
        return None
    value = row[0]
    if isinstance(value, str):
        with suppress(ValueError):
            return json.loads(value)
        return None
    return value if isinstance(value, dict) else None


def tick(
    service_name: str,
    *,
    outcome_increment: int = 1,
    status: str = "ok",
    error_message: str | None = None,
    period_seconds: int = PERIOD_SECONDS,
) -> None:
    """Emit one heartbeat tick for `service_name`. Fail-open — a heartbeat
    write failure must never crash the calling service."""
    dsn = _dsn()
    if not dsn:
        logger.warning("heartbeat.tick(%s) — no DSN, skipping", service_name)
        return
    key = HEARTBEAT_KEY_PREFIX + service_name
    callsign = os.environ.get("CALLSIGN", "system")
    try:
        with psycopg.connect(dsn, autocommit=True, prepare_threshold=None) as conn:
            previous = _read_previous(conn, key)
        next_state = compute_next_state(
            previous,
            now=_now(),
            outcome_increment=outcome_increment,
            status=status,
            error_message=error_message,
            period_seconds=period_seconds,
        )
        upsert_ceo_memory_key(callsign, key, next_state)
    except Exception:
        # Fail-open — the calling service's main work matters more than the
        # heartbeat. Log and move on.
        logger.exception("heartbeat.tick(%s) failed — non-fatal", service_name)
