#!/usr/bin/env python3
"""GOV-PHASE2 Auditor — periodic governance_events → Phoenix span exporter.

Watermark loop:
  1. read last_export_timestamp from state file (or NOW()-1h on first run)
  2. fetch governance_events rows where timestamp > last_export_timestamp
  3. for each row, call src.observability.phoenix_client.export_event(tracer, row)
  4. advance the watermark to MAX(timestamp) of fetched rows
  5. sleep PHOENIX_EXPORT_INTERVAL_S seconds, repeat

State file (default: /home/elliotbot/clawd/state/phoenix_watermark.txt) holds an
ISO-8601 timestamp string. Failures (DB unreachable, OTLP unreachable) are
logged and the loop continues — observability never crashes the service.

Usage:
    PYTHONPATH=. python3 scripts/phoenix_export_loop.py
    PHOENIX_EXPORT_INTERVAL_S=30 python3 scripts/phoenix_export_loop.py  # tune
"""
from __future__ import annotations

import asyncio
import logging
import os
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="[phoenix-export] %(levelname)s: %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger(__name__)

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

WATERMARK_PATH = Path(
    os.environ.get(
        "PHOENIX_WATERMARK_PATH",
        "/home/elliotbot/clawd/state/phoenix_watermark.txt",
    )
)
INTERVAL_S = int(os.environ.get("PHOENIX_EXPORT_INTERVAL_S", "60"))
BATCH_LIMIT = int(os.environ.get("PHOENIX_EXPORT_BATCH_LIMIT", "500"))


def read_watermark() -> datetime:
    """Read the last-exported timestamp. Defaults to NOW()-1h on first run."""
    try:
        if WATERMARK_PATH.exists():
            raw = WATERMARK_PATH.read_text(encoding="utf-8").strip()
            if raw:
                return datetime.fromisoformat(raw)
    except (OSError, ValueError) as exc:
        logger.warning("watermark read failed (%s) — defaulting to NOW()-1h", exc)
    return datetime.now(UTC) - timedelta(hours=1)


def write_watermark(ts: datetime) -> None:
    """Persist the watermark. Best-effort — never raises."""
    try:
        WATERMARK_PATH.parent.mkdir(parents=True, exist_ok=True)
        WATERMARK_PATH.write_text(ts.isoformat(), encoding="utf-8")
    except OSError as exc:
        logger.warning("watermark write failed: %s", exc)


async def fetch_events(since: datetime, dsn: str, limit: int = BATCH_LIMIT) -> list[dict]:
    """Fetch governance_events rows with timestamp > since. Returns [] on failure."""
    try:
        import asyncpg
    except ImportError:
        logger.error("asyncpg missing — install via requirements.txt")
        return []
    try:
        conn = await asyncpg.connect(dsn, statement_cache_size=0)
        try:
            rows = await conn.fetch(
                """
                SELECT id, callsign, event_type, event_data, tool_name,
                       file_path, directive_id, timestamp
                FROM public.governance_events
                WHERE timestamp > $1
                ORDER BY timestamp ASC
                LIMIT $2
                """,
                since,
                limit,
            )
            return [dict(r) for r in rows]
        finally:
            await conn.close()
    except Exception as exc:  # noqa: BLE001 - logged, not raised
        logger.warning("fetch_events failed: %s", exc)
        return []


def _resolve_dsn() -> str | None:
    raw = (
        os.environ.get("DATABASE_URL")
        or os.environ.get("SUPABASE_DB_URL")
        or ""
    ).strip()
    if not raw:
        return None
    return raw.replace("postgresql+asyncpg://", "postgresql://")


async def run_one_cycle(tracer) -> int:
    """One iteration of the export loop. Returns the number of events exported."""
    from src.observability.phoenix_client import export_event

    dsn = _resolve_dsn()
    if not dsn:
        logger.warning("no DSN configured — skipping cycle")
        return 0

    since = read_watermark()
    events = await fetch_events(since, dsn)
    exported = 0
    latest_ts = since
    for ev in events:
        if export_event(tracer, ev):
            exported += 1
        ts = ev.get("timestamp")
        if isinstance(ts, datetime) and ts > latest_ts:
            latest_ts = ts
    if latest_ts > since:
        write_watermark(latest_ts)
    if events:
        logger.info(
            "cycle: fetched=%d exported=%d watermark_advanced=%s",
            len(events), exported, latest_ts.isoformat(),
        )
    return exported


async def main() -> int:
    from src.observability.phoenix_client import init_tracer

    tracer = init_tracer()
    if tracer is None:
        logger.error("Phoenix tracer unavailable — exiting (will retry on next service restart)")
        return 1

    logger.info(
        "Phoenix export loop started — interval=%ds, batch_limit=%d, watermark_path=%s",
        INTERVAL_S, BATCH_LIMIT, WATERMARK_PATH,
    )
    while True:
        try:
            await run_one_cycle(tracer)
        except Exception as exc:  # noqa: BLE001
            logger.error("cycle error (continuing): %s", exc)
        await asyncio.sleep(INTERVAL_S)


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
