#!/usr/bin/env python3
"""verify_kei100_id_alignment.py — KEI-100 post-migration assertion.

Acceptance per dispatch: "zero ID mismatches between Linear and Supabase tasks
table". After the migration lands, run this script. Exits non-zero if any row
is misaligned, with a per-row report on stdout.

Mismatch shapes:
  1. linear_url set but linear_id NULL (trigger failed to populate)
  2. linear_url set and linear_id set but they disagree
  3. id ~ '^KEI-[0-9]+$' but linear_id IS NULL (id-side fallback didn't fire)
  4. linear_id set but doesn't match '^KEI-[0-9]+$' (extraction polluted)

Usage:
    DATABASE_URL=postgresql://... python3 verify_kei100_id_alignment.py
"""

from __future__ import annotations

import logging
import os
import sys

logger = logging.getLogger("verify_kei100")
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

_CHECK_SQL = """
SELECT id, linear_id, linear_url,
       CASE
         WHEN linear_url IS NOT NULL AND linear_id IS NULL THEN 'url_set_id_null'
         WHEN linear_url IS NOT NULL
              AND linear_id IS NOT NULL
              AND substring(linear_url FROM 'KEI-[0-9]+') IS DISTINCT FROM linear_id
              THEN 'url_id_disagree'
         WHEN id ~ '^KEI-[0-9]+$' AND linear_id IS NULL THEN 'id_kei_but_linear_id_null'
         WHEN linear_id IS NOT NULL AND linear_id !~ '^KEI-[0-9]+$' THEN 'linear_id_malformed'
       END AS mismatch
  FROM public.tasks
 WHERE (linear_url IS NOT NULL AND linear_id IS NULL)
    OR (linear_url IS NOT NULL
        AND linear_id IS NOT NULL
        AND substring(linear_url FROM 'KEI-[0-9]+') IS DISTINCT FROM linear_id)
    OR (id ~ '^KEI-[0-9]+$' AND linear_id IS NULL)
    OR (linear_id IS NOT NULL AND linear_id !~ '^KEI-[0-9]+$')
"""


def _resolve_dsn() -> str | None:
    raw = os.environ.get("DATABASE_URL") or os.environ.get("SUPABASE_DB_URL", "")
    if not raw:
        return None
    return raw.replace("postgresql+asyncpg://", "postgresql://", 1)


def main() -> int:
    dsn = _resolve_dsn()
    if not dsn:
        print("ERROR: DATABASE_URL / SUPABASE_DB_URL unset", file=sys.stderr)
        return 2
    try:
        import psycopg

        with psycopg.connect(dsn, prepare_threshold=None) as conn, conn.cursor() as cur:
            cur.execute(_CHECK_SQL)
            rows = cur.fetchall()
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: DB query failed: {exc}", file=sys.stderr)
        return 2

    if not rows:
        print("OK: 0 ID mismatches between Linear and Supabase tasks table.")
        return 0

    print(f"FAIL: {len(rows)} mismatched row(s):")
    for r in rows:
        print(f"  id={r[0]} linear_id={r[1]} linear_url={r[2]} reason={r[3]}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
