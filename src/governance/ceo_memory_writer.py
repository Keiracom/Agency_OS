"""KEI-87 — canonical wrapper for ceo_memory writes.

The trigger at supabase/migrations/20260517_kei87_ceo_memory_write_guard.sql
refuses any UPDATE/INSERT on a 'ceo:*' key when the PostgreSQL session variable
`agency_os.callsign` is missing or not in the allowlist. This wrapper is the
only path that should ever issue such writes.

Existing call-sites are being migrated from raw psycopg.execute() to
`upsert_ceo_memory_key(...)` / `update_ceo_memory_value(...)` in a follow-up
KEI; until then the trigger remains UNAPPLIED on prod (see the migration's
deployment-order banner).

Public API:
    upsert_ceo_memory_key(callsign, key, value)
    update_ceo_memory_value(callsign, key, jsonb_path, new_value)

Both helpers run inside a single transaction:
    BEGIN
    SET LOCAL agency_os.callsign = '<callsign>'
    INSERT/UPDATE ...
    COMMIT
"""

from __future__ import annotations

import json
import os
from collections.abc import Mapping
from typing import Any


def _dsn() -> str:
    dsn = os.environ.get("DATABASE_URL") or os.environ.get("SUPABASE_DB_URL", "")
    if not dsn:
        raise RuntimeError("DATABASE_URL / SUPABASE_DB_URL not set")
    return dsn.replace("postgresql+asyncpg://", "postgresql://", 1)


def _require_callsign(callsign: str) -> str:
    cs = (callsign or "").strip().lower()
    if not cs:
        raise ValueError("KEI-87 ceo_memory_writer: callsign argument is required")
    return cs


def upsert_ceo_memory_key(callsign: str, key: str, value: Mapping[str, Any]) -> None:
    """Idempotent upsert into public.ceo_memory under the KEI-87 write-guard."""
    import psycopg  # local import — keeps callers without psycopg from paying import cost

    cs = _require_callsign(callsign)
    with psycopg.connect(_dsn()) as conn, conn.cursor() as cur:
        cur.execute("SET LOCAL agency_os.callsign = %s", (cs,))
        cur.execute(
            """
            INSERT INTO public.ceo_memory (key, value, updated_at)
            VALUES (%s, %s::jsonb, NOW())
            ON CONFLICT (key) DO UPDATE
              SET value = EXCLUDED.value, updated_at = NOW()
            """,
            (key, json.dumps(dict(value))),
        )
        conn.commit()


def update_ceo_memory_value(callsign: str, key: str, value: Mapping[str, Any]) -> None:
    """Update only — refuses if the row is missing (caller should upsert)."""
    import psycopg

    cs = _require_callsign(callsign)
    with psycopg.connect(_dsn()) as conn, conn.cursor() as cur:
        cur.execute("SET LOCAL agency_os.callsign = %s", (cs,))
        cur.execute(
            "UPDATE public.ceo_memory SET value = %s::jsonb, updated_at = NOW() WHERE key = %s",
            (json.dumps(dict(value)), key),
        )
        if cur.rowcount == 0:
            raise KeyError(f"ceo_memory key not found: {key!r}")
        conn.commit()
