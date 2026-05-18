#!/usr/bin/env python3
"""fleet_heartbeat_writer.py — KEI-97 per-agent-process heartbeat (30s cadence).

One-shot script invoked by fleet-heartbeat@<callsign>.timer every 30 seconds.
Upserts public.fleet_agents.last_heartbeat=NOW() for the configured callsign.

Sibling to KEI-105's heartbeat_writer.py (which tracks per-task heartbeats at
15 min cadence). This script tracks per-process liveness at 30s cadence so the
CEO fleet-check can flag zombies — tmux pane responsive but agent process
dead and no longer pinging.

Exit codes:
  0 — success, or transient DB error (fail-open so the timer keeps firing)
  2 — CALLSIGN env var unset (configuration error; fix before retrying)

Usage (direct):
    CALLSIGN=scout DATABASE_URL=postgresql://... python3 fleet_heartbeat_writer.py
"""

from __future__ import annotations

import logging
import os
import sys

logger = logging.getLogger("fleet_heartbeat_writer")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

_UPSERT_SQL = """
INSERT INTO public.fleet_agents (callsign, last_heartbeat)
VALUES (%s, NOW())
ON CONFLICT (callsign) DO UPDATE
    SET last_heartbeat = EXCLUDED.last_heartbeat
RETURNING callsign, last_heartbeat
"""


def _resolve_dsn() -> str | None:
    """Return a psycopg-compatible DSN, stripping the asyncpg dialect prefix."""
    raw = os.environ.get("DATABASE_URL") or os.environ.get("SUPABASE_DB_URL", "")
    if not raw:
        return None
    return raw.replace("postgresql+asyncpg://", "postgresql://", 1)


def main() -> int:
    callsign = os.environ.get("CALLSIGN", "").strip()
    if not callsign:
        print(
            "fleet_heartbeat_writer: CALLSIGN env var is required but unset",
            file=sys.stderr,
        )
        return 2

    dsn = _resolve_dsn()
    if not dsn:
        logger.warning("fleet_heartbeat_writer: DATABASE_URL / SUPABASE_DB_URL unset — fail-open")
        return 0

    try:
        import psycopg

        with psycopg.connect(dsn, prepare_threshold=None) as conn:
            with conn.cursor() as cur:
                cur.execute(_UPSERT_SQL, (callsign,))
                row = cur.fetchone()
            conn.commit()
        if row:
            logger.info("fleet_heartbeat_writer: %s at %s", row[0], row[1].isoformat())
    except Exception as exc:  # noqa: BLE001 — fail-open so timer keeps firing
        logger.warning("fleet_heartbeat_writer: DB error for %s — fail-open: %s", callsign, exc)

    return 0


if __name__ == "__main__":
    sys.exit(main())
