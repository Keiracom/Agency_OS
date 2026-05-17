#!/usr/bin/env python3
"""heartbeat_monitor.py — KEI-91 Gate 4 monitor (systemd timer entry-point).

Runs every 5 minutes via heartbeat-monitor.timer. Scans every
`heartbeat:<service>` row in public.ceo_memory and emits an alert to #ceo
(via scripts/slack_relay.py) when any of the following conditions fire:

  - `last_tick_ts` is more than `MAX_STALE_TICK_MINUTES` minutes ago
    (process is dead or wedged — aliveness gate)
  - `last_outcome_counter_value` is 0 during the current period AND
    the current time is in the business-hours window (silent-regression
    gate — service is alive but doing nothing meaningful)
  - `last_status` == "error" (the service self-reported an error on its
    most recent tick)

The monitor itself emits a heartbeat on its own service name so it's
recursively observable.

Per-service thresholds live in HEARTBEAT_THRESHOLDS (env-overridable). The
defaults are intentionally generous so first-pass tuning isn't a blocker.

Usage:
    python3 scripts/orchestrator/heartbeat_monitor.py            # one pass + exit
    python3 scripts/orchestrator/heartbeat_monitor.py --dry-run  # log alerts only
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import logging
import os
import subprocess
import sys
from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import psycopg

logger = logging.getLogger("heartbeat_monitor")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

SELF_SERVICE = "heartbeat-monitor"

# Per-service thresholds. Each value can be overridden via env:
#   HEARTBEAT_THRESHOLD_<SERVICE_UPPER_SNAKE>=stale_min,zero_outcome_window,bh_only
HEARTBEAT_THRESHOLDS: dict[str, ServiceThreshold] = {}
DEFAULT_STALE_MINUTES = int(os.environ.get("HEARTBEAT_DEFAULT_STALE_MIN", "10"))
DEFAULT_ZERO_OUTCOME_WINDOW = int(os.environ.get("HEARTBEAT_DEFAULT_ZERO_WIN_MIN", "30"))
BUSINESS_HOURS_START = int(os.environ.get("HEARTBEAT_BH_START_UTC", "0"))  # 00:00 UTC = 11:00 AEST
BUSINESS_HOURS_END = int(
    os.environ.get("HEARTBEAT_BH_END_UTC", "24")
)  # 24:00 UTC = next-day window — default to always-on


@dataclass(frozen=True)
class ServiceThreshold:
    """Per-service alert tuning."""

    stale_minutes: int = DEFAULT_STALE_MINUTES
    zero_outcome_window_minutes: int = DEFAULT_ZERO_OUTCOME_WINDOW
    business_hours_only: bool = True


@dataclass(frozen=True)
class Alert:
    service: str
    reason: str
    detail: str


def _dsn() -> str:
    raw = os.environ.get("DATABASE_URL") or os.environ.get("SUPABASE_DB_URL")
    if not raw:
        raise SystemExit("heartbeat_monitor: DATABASE_URL or SUPABASE_DB_URL must be set")
    return raw.replace("postgresql+asyncpg://", "postgresql://", 1)


def _now() -> _dt.datetime:
    return _dt.datetime.now(_dt.UTC)


def _is_business_hours(now: _dt.datetime) -> bool:
    return BUSINESS_HOURS_START <= now.hour < BUSINESS_HOURS_END


def _load_state(value: Any) -> dict[str, Any] | None:
    if isinstance(value, str):
        with suppress(ValueError):
            return json.loads(value)
        return None
    return value if isinstance(value, dict) else None


def evaluate(
    service: str,
    state: dict[str, Any],
    *,
    now: _dt.datetime,
    threshold: ServiceThreshold,
) -> list[Alert]:
    """Pure function — returns the alerts that should fire for one heartbeat
    row. Separated from I/O so the threshold logic is unit-testable.
    """
    alerts: list[Alert] = []

    last_tick_raw = state.get("last_tick_ts", "")
    last_tick: _dt.datetime | None = None
    with suppress(ValueError, TypeError):
        last_tick = _dt.datetime.fromisoformat(last_tick_raw)

    if last_tick is None:
        alerts.append(
            Alert(
                service=service,
                reason="missing_last_tick_ts",
                detail=f"heartbeat row exists but last_tick_ts is missing/unparseable: {last_tick_raw!r}",
            )
        )
    else:
        stale_for = (now - last_tick).total_seconds() / 60.0
        if stale_for > threshold.stale_minutes:
            alerts.append(
                Alert(
                    service=service,
                    reason="stale_tick",
                    detail=f"last tick {stale_for:.1f}min ago (threshold {threshold.stale_minutes}min)",
                )
            )

    if state.get("last_status") == "error":
        alerts.append(
            Alert(
                service=service,
                reason="self_reported_error",
                detail=str(state.get("last_error_message") or "no message"),
            )
        )

    if threshold.business_hours_only and not _is_business_hours(now):
        return alerts

    counter_value = state.get("last_outcome_counter_value", 0)
    with suppress(ValueError, TypeError):
        counter_value = int(counter_value)
    if isinstance(counter_value, int) and counter_value == 0:
        # Only fire zero-outcome if the current period has been running long
        # enough to be suspicious — the configured window.
        last_period_start_raw = state.get("last_period_start", "")
        last_period_start: _dt.datetime | None = None
        with suppress(ValueError, TypeError):
            last_period_start = _dt.datetime.fromisoformat(last_period_start_raw)
        if last_period_start is not None:
            period_age_min = (now - last_period_start).total_seconds() / 60.0
            if period_age_min >= threshold.zero_outcome_window_minutes:
                alerts.append(
                    Alert(
                        service=service,
                        reason="zero_outcome_window",
                        detail=(
                            f"counter=0 for {period_age_min:.1f}min "
                            f"(window {threshold.zero_outcome_window_minutes}min)"
                        ),
                    )
                )

    return alerts


def scan_all(conn: psycopg.Connection, *, now: _dt.datetime) -> list[Alert]:
    alerts: list[Alert] = []
    with conn.cursor() as cur:
        cur.execute(
            "SELECT key, value FROM public.ceo_memory WHERE key LIKE %s",
            (f"{'heartbeat:'}%",),
        )
        rows = cur.fetchall()
    for key, value in rows:
        service = key[len("heartbeat:") :]
        state = _load_state(value)
        if state is None:
            alerts.append(
                Alert(
                    service=service,
                    reason="unparseable_state",
                    detail=f"value type={type(value).__name__}",
                )
            )
            continue
        threshold = HEARTBEAT_THRESHOLDS.get(service, ServiceThreshold())
        alerts.extend(evaluate(service, state, now=now, threshold=threshold))
    return alerts


def emit_ceo_alert(alert: Alert, *, dry_run: bool = False) -> None:
    msg = f"[HEARTBEAT-ALERT] {alert.service} :: {alert.reason} :: {alert.detail}"
    if dry_run:
        logger.info("dry-run: %s", msg)
        return
    relay = Path("/home/elliotbot/clawd/Agency_OS/scripts/slack_relay.py")
    if not relay.exists():
        logger.warning("slack_relay.py not found at %s — falling back to log only", relay)
        logger.warning("%s", msg)
        return
    try:
        subprocess.run(
            ["python3", str(relay), "-c", "ceo", msg],
            check=False,
            timeout=15,
        )
    except (subprocess.SubprocessError, OSError) as exc:
        logger.warning("slack_relay.py invoke failed (%s) — alert was: %s", exc, msg)


def tick_self(status: str = "ok", outcome: int = 1) -> None:
    """Recursive observability — the monitor heartbeats too."""
    with suppress(Exception):
        # Local import to avoid hard dependency at module load time.
        sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
        from observability.heartbeat import tick  # type: ignore[import-not-found]

        tick(SELF_SERVICE, outcome_increment=outcome, status=status)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    now = _now()
    with psycopg.connect(_dsn(), autocommit=True) as conn:
        alerts = scan_all(conn, now=now)
    logger.info("scan complete — %d alerts", len(alerts))
    for alert in alerts:
        emit_ceo_alert(alert, dry_run=args.dry_run)
    tick_self()


if __name__ == "__main__":
    main()
    sys.exit(0)
