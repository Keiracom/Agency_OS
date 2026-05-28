"""alerting.py — backup-failure alerting via ceo_memory.

On any backup failure, write `ceo:backup_alert:{date}` so the fleet sees the
incident even though the failing job is a headless systemd unit. Uses the
canonical KEI-87 writer (write-guarded ceo_memory). Best-effort: alerting must
never raise out of the failure path it is reporting on.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

logger = logging.getLogger(__name__)

# Must be on the KEI-87 ceo_memory write-guard allowlist (only 'elliot'/'dave');
# a 'nova' write is silently rejected, so backup alerts would never land.
CALLSIGN = "elliot"
WriterFn = Callable[[str, str, dict[str, Any]], None]


def _default_writer(callsign: str, key: str, value: dict[str, Any]) -> None:
    from src.governance.ceo_memory_writer import upsert_ceo_memory_key

    upsert_ceo_memory_key(callsign, key, value)


def write_backup_alert(
    component: str,
    error: str,
    *,
    writer: WriterFn | None = None,
    now: datetime | None = None,
) -> str | None:
    """Write a backup-failure alert to ceo_memory. Returns the key, or None on
    write failure (never raises — it's reporting a failure, not adding one)."""
    stamp = (now or datetime.now(UTC)).astimezone(UTC)
    key = f"ceo:backup_alert:{stamp.strftime('%Y-%m-%d')}"
    value = {
        "component": component,
        "error": error[:1000],
        "severity": "P1",
        "alerted_at": stamp.isoformat(),
        "source": "keiracom_system.backup",
    }
    write = writer or _default_writer
    try:
        write(CALLSIGN, key, value)
    except Exception as exc:  # noqa: BLE001 — alerting must not raise
        logger.error("backup alert write failed for %s: %s", component, exc)
        return None
    logger.error("BACKUP ALERT %s: %s — %s", key, component, error[:200])
    return key
