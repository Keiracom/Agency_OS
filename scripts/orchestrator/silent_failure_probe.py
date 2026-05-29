#!/usr/bin/env python3
"""silent_failure_probe.py — Agency_OS-52wu: comprehensive silent-failure alerting.

Runs every 5 minutes via silent-failure-probe.timer. Checks EVERY critical
background service/watcher defined in config/silent_failure_registry.yaml:

  - systemd services: `systemctl --user is-active <name>` (persistent services)
  - timer services:   last trigger age vs configured window (oneshot+timer pairs)
  - heartbeat keys:   `heartbeat:<name>` in ceo_memory, checks last_tick_ts age

On any liveness miss:
  - P0 → posts plain-English alert to #ceo via slack_relay.py
  - P1 → posts to #execution
  - writes `liveness_debt:<service>` to ceo_memory (idempotent — one alert per miss)
  - when service recovers, flips debt row status pending → resolved

Anchor incidents (both found by audit, not alerting):
  - keiracom-temporal-worker dual-publish dead 5 days (systemd active, silent)
  - migration-apply-watcher schema gate failed silently (timer never re-triggered)

Self-heartbeats so the monitor itself is recursively observable.

Usage:
    python3 scripts/orchestrator/silent_failure_probe.py            # one pass
    python3 scripts/orchestrator/silent_failure_probe.py --dry-run  # log only
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
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from src.governance.ceo_memory_writer import upsert_ceo_memory_key  # noqa: E402

logger = logging.getLogger("silent_failure_probe")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

REGISTRY_PATH = Path(__file__).resolve().parents[2] / "config" / "silent_failure_registry.yaml"
SELF_SERVICE = "silent-failure-probe"
DEBT_KEY_PREFIX = "liveness_debt:"

# Slack channel IDs
CHANNEL_CEO = "C0B2PM3TV0B"
CHANNEL_EXECUTION = "C0B3QB0K1GQ"


@dataclass(frozen=True)
class ServiceEntry:
    name: str
    check: str  # "systemd" | "timer" | "heartbeat"
    criticality: str  # "P0" | "P1"
    description: str
    stale_minutes: int = 10
    timer_window_hours: float = 1.0


@dataclass(frozen=True)
class LivenessMiss:
    service: str
    reason: str
    detail: str
    criticality: str  # "P0" | "P1"


def load_registry(path: Path = REGISTRY_PATH) -> list[ServiceEntry]:
    """Parse the YAML registry into ServiceEntry objects."""
    with path.open(encoding="utf-8") as fh:
        doc = yaml.safe_load(fh)
    entries: list[ServiceEntry] = []
    for item in doc.get("services", []):
        entries.append(
            ServiceEntry(
                name=item["name"],
                check=item["check"],
                criticality=item.get("criticality", "P1"),
                description=item.get("description", ""),
                stale_minutes=int(item.get("stale_minutes", 10)),
                timer_window_hours=float(item.get("timer_window_hours", 1.0)),
            )
        )
    return entries


# ── Pure evaluation functions ───────────────────────────────────────────────


def evaluate_systemd(entry: ServiceEntry, systemd_state: str) -> LivenessMiss | None:
    """Returns a miss if the service is not active."""
    if systemd_state == "active":
        return None
    return LivenessMiss(
        service=entry.name,
        reason="systemd_not_active",
        detail=f"state={systemd_state!r} (expected active)",
        criticality=entry.criticality,
    )


def evaluate_timer(
    entry: ServiceEntry,
    last_trigger: _dt.datetime | None,
    now: _dt.datetime,
) -> LivenessMiss | None:
    """Returns a miss if the timer has never fired or is past its window."""
    if last_trigger is None:
        return LivenessMiss(
            service=entry.name,
            reason="timer_never_run",
            detail="LastTriggerUSec empty — timer has never fired",
            criticality=entry.criticality,
        )
    age_hours = (now - last_trigger).total_seconds() / 3600.0
    if age_hours > entry.timer_window_hours:
        return LivenessMiss(
            service=entry.name,
            reason="timer_stale",
            detail=(f"last run {age_hours:.1f}h ago (window {entry.timer_window_hours:.1f}h)"),
            criticality=entry.criticality,
        )
    return None


def evaluate_heartbeat(
    entry: ServiceEntry,
    hb_state: dict[str, Any] | None,
    now: _dt.datetime,
) -> LivenessMiss | None:
    """Returns a miss if the heartbeat key is absent or last_tick_ts is stale."""
    if hb_state is None:
        return LivenessMiss(
            service=entry.name,
            reason="heartbeat_missing",
            detail=f"no heartbeat:{entry.name} key found in ceo_memory",
            criticality=entry.criticality,
        )
    last_tick: _dt.datetime | None = None
    with suppress(ValueError, TypeError):
        last_tick = _dt.datetime.fromisoformat(hb_state.get("last_tick_ts", ""))
    if last_tick is None:
        return LivenessMiss(
            service=entry.name,
            reason="heartbeat_unparseable",
            detail=f"last_tick_ts missing or unparseable: {hb_state.get('last_tick_ts')!r}",
            criticality=entry.criticality,
        )
    stale_min = (now - last_tick).total_seconds() / 60.0
    if stale_min > entry.stale_minutes:
        return LivenessMiss(
            service=entry.name,
            reason="heartbeat_stale",
            detail=(f"last tick {stale_min:.1f}min ago (threshold {entry.stale_minutes}min)"),
            criticality=entry.criticality,
        )
    return None


# ── I/O helpers ─────────────────────────────────────────────────────────────


def query_systemd_state(service_name: str) -> str:
    """Return systemd ActiveState string. Fails open to 'unknown'."""
    try:
        result = subprocess.run(
            ["systemctl", "--user", "is-active", service_name],
            capture_output=True,
            text=True,
            timeout=10,
        )
        state = result.stdout.strip() or "unknown"
        return state if state else "unknown"
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return "unknown"


def query_timer_last_trigger(timer_name: str) -> _dt.datetime | None:
    """Return the last trigger timestamp for a .timer unit, or None if never run."""
    try:
        result = subprocess.run(
            [
                "systemctl",
                "--user",
                "show",
                f"{timer_name}.timer",
                "--property=LastTriggerUSec",
                "--value",
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return None

    raw = result.stdout.strip()
    if not raw:
        return None
    # Format: "Thu 2026-05-28 03:30:01 UTC" — parse robustly
    with suppress(ValueError):
        dt = _dt.datetime.strptime(raw, "%a %Y-%m-%d %H:%M:%S %Z")
        return dt.replace(tzinfo=_dt.UTC)
    return None


def query_heartbeat_state(conn: psycopg.Connection, service_name: str) -> dict[str, Any] | None:
    """Return the heartbeat state dict from ceo_memory, or None if absent."""
    key = f"heartbeat:{service_name}"
    with conn.cursor() as cur:
        cur.execute("SELECT value FROM public.ceo_memory WHERE key = %s", (key,))
        row = cur.fetchone()
    if row is None:
        return None
    value = row[0]
    if isinstance(value, dict):
        return value
    with suppress(ValueError, TypeError):
        return json.loads(value)
    return None


# ── Debt idempotency ─────────────────────────────────────────────────────────


def get_debt_row(conn: psycopg.Connection, service: str) -> dict[str, Any] | None:
    key = DEBT_KEY_PREFIX + service
    with conn.cursor() as cur:
        cur.execute("SELECT value FROM public.ceo_memory WHERE key = %s", (key,))
        row = cur.fetchone()
    if row is None:
        return None
    value = row[0]
    if isinstance(value, dict):
        return value
    with suppress(ValueError, TypeError):
        return json.loads(value)
    return None


def upsert_debt_row(service: str, *, status: str, reason: str) -> None:
    callsign = os.environ.get("CALLSIGN", "system")
    key = DEBT_KEY_PREFIX + service
    upsert_ceo_memory_key(
        callsign,
        key,
        {
            "service": service,
            "status": status,
            "reason": reason,
            "updated_at": _dt.datetime.now(_dt.UTC).isoformat(),
            "source": SELF_SERVICE,
        },
    )


# ── Alert emission ───────────────────────────────────────────────────────────


def emit_alert(miss: LivenessMiss, *, dry_run: bool = False) -> None:
    """Post a plain-English alert to #ceo (P0) or #execution (P1)."""
    channel = "ceo" if miss.criticality == "P0" else "execution"
    msg = (
        f"*Silent Failure Detected — {miss.criticality}*\n"
        f"- Service: `{miss.service}`\n"
        f"- Reason: {miss.reason}\n"
        f"- Detail: {miss.detail}\n"
        f"- Alert will clear automatically when the service recovers."
    )
    if dry_run:
        logger.info("dry-run alert [%s → #%s]: %s", miss.criticality, channel, miss.detail)
        return
    relay = Path(__file__).resolve().parents[1] / "slack_relay.py"
    if not relay.exists():
        logger.warning("slack_relay.py not at %s — alert logged only: %s", relay, msg)
        return
    with suppress(subprocess.SubprocessError, OSError):
        subprocess.run(
            ["python3", str(relay), "-c", channel, msg],
            check=False,
            timeout=15,
        )


# ── Core probe logic ─────────────────────────────────────────────────────────


def probe_service(
    entry: ServiceEntry,
    conn: psycopg.Connection,
    now: _dt.datetime,
) -> LivenessMiss | None:
    """Run the appropriate check for one entry. Returns a miss or None."""
    if entry.check == "systemd":
        state = query_systemd_state(entry.name)
        return evaluate_systemd(entry, state)
    if entry.check == "timer":
        last_trigger = query_timer_last_trigger(entry.name)
        return evaluate_timer(entry, last_trigger, now)
    if entry.check == "heartbeat":
        hb_state = query_heartbeat_state(conn, entry.name)
        return evaluate_heartbeat(entry, hb_state, now)
    logger.warning("unknown check type %r for service %s", entry.check, entry.name)
    return None


def process_miss(
    miss: LivenessMiss,
    conn: psycopg.Connection,
    *,
    dry_run: bool,
) -> None:
    """Emit alert (idempotent) and write/update debt row."""
    debt = get_debt_row(conn, miss.service)
    if debt and debt.get("status") == "pending":
        logger.info("%s: debt already pending — skipping duplicate alert", miss.service)
        return
    logger.warning("%s: liveness miss — %s (%s)", miss.service, miss.reason, miss.detail)
    emit_alert(miss, dry_run=dry_run)
    if not dry_run:
        upsert_debt_row(miss.service, status="pending", reason=miss.reason)


def process_healthy(service_name: str, conn: psycopg.Connection, *, dry_run: bool) -> None:
    """When a service is healthy, resolve any pending debt row."""
    debt = get_debt_row(conn, service_name)
    if debt and debt.get("status") == "pending":
        logger.info("%s: recovered — resolving debt row", service_name)
        if not dry_run:
            upsert_debt_row(service_name, status="resolved", reason="auto-recovered")


def tick_self(*, error: bool = False) -> None:
    """Emit probe's own heartbeat so it is recursively observable."""
    with suppress(Exception):
        from src.observability.heartbeat import tick  # type: ignore[import-not-found]

        tick(SELF_SERVICE, outcome_increment=0 if error else 1, status="error" if error else "ok")


def _dsn() -> str:
    raw = os.environ.get("DATABASE_URL") or os.environ.get("SUPABASE_DB_URL")
    if not raw:
        raise SystemExit("silent_failure_probe: DATABASE_URL or SUPABASE_DB_URL must be set")
    return raw.replace("postgresql+asyncpg://", "postgresql://", 1)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="silent_failure_probe — liveness check for all critical services"
    )
    parser.add_argument("--dry-run", action="store_true", help="log alerts, do not post or write")
    parser.add_argument(
        "--registry",
        default=str(REGISTRY_PATH),
        help="path to silent_failure_registry.yaml",
    )
    args = parser.parse_args(argv)

    entries = load_registry(Path(args.registry))
    logger.info("loaded %d service entries from registry", len(entries))

    now = _dt.datetime.now(_dt.UTC)
    misses: list[LivenessMiss] = []

    try:
        with psycopg.connect(_dsn(), autocommit=True, prepare_threshold=None) as conn:
            for entry in entries:
                miss = probe_service(entry, conn, now)
                if miss is not None:
                    misses.append(miss)
                    process_miss(miss, conn, dry_run=args.dry_run)
                else:
                    process_healthy(entry.name, conn, dry_run=args.dry_run)
    except psycopg.OperationalError as exc:
        logger.exception("DB connection failed: %s", exc)
        tick_self(error=True)
        sys.exit(1)

    p0 = sum(1 for m in misses if m.criticality == "P0")
    p1 = sum(1 for m in misses if m.criticality == "P1")
    logger.info(
        "probe complete — %d/%d services checked, %d misses (P0=%d P1=%d)",
        len(entries),
        len(entries),
        len(misses),
        p0,
        p1,
    )
    tick_self()


if __name__ == "__main__":
    main()
    sys.exit(0)
