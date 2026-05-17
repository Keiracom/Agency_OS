#!/usr/bin/env python3
"""heartbeat_writer.py — KEI-105 periodic heartbeat writer (systemd timer entry-point).

One-shot script invoked by heartbeat-writer@<callsign>.timer every 15 minutes.
Touches heartbeat_at on every task currently claimed-and-active by CALLSIGN.

Exit codes:
  0 — success, or transient DB error (fail-open so timer keeps firing)
  2 — CALLSIGN env var unset (configuration error; fix before retrying)

Usage (direct):
    CALLSIGN=orion DATABASE_URL=postgresql://... python3 heartbeat_writer.py
"""

from __future__ import annotations

import logging
import os
import sys

logger = logging.getLogger("heartbeat_writer")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

_UPDATE_SQL = """
UPDATE public.tasks
   SET heartbeat_at = NOW()
 WHERE claimed_by = %s
   AND status = 'active'
   AND heartbeat_at IS DISTINCT FROM NOW()
RETURNING id
"""


def _resolve_dsn() -> str | None:
    """Return a psycopg-compatible DSN, stripping asyncpg dialect prefix."""
    raw = os.environ.get("DATABASE_URL") or os.environ.get("SUPABASE_DB_URL", "")
    if not raw:
        return None
    return raw.replace("postgresql+asyncpg://", "postgresql://", 1)


def main() -> int:
    callsign = os.environ.get("CALLSIGN", "").strip()
    if not callsign:
        print(
            "heartbeat_writer: CALLSIGN env var is required but unset",
            file=sys.stderr,
        )
        return 2

    dsn = _resolve_dsn()
    if not dsn:
        logger.warning(
            "heartbeat_writer: DATABASE_URL / SUPABASE_DB_URL unset — skipping (fail-open)"
        )
        return 0

    try:
        import psycopg

        with psycopg.connect(dsn, prepare_threshold=None) as conn:
            with conn.cursor() as cur:
                cur.execute(_UPDATE_SQL, (callsign,))
                rows = cur.fetchall()
            conn.commit()

        ids = [r[0] for r in rows]
        if ids:
            logger.info(
                "heartbeat_writer: touched %d task(s) for %s: %s",
                len(ids),
                callsign,
                ids,
            )
        else:
            logger.debug("heartbeat_writer: no active claims for %s", callsign)

    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "heartbeat_writer: DB error for %s — fail-open: %s",
            callsign,
            exc,
        )

    return 0


if __name__ == "__main__":
    sys.exit(main())
