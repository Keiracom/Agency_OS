#!/usr/bin/env python3
"""One-shot backfill — populate `business_universe.abn` for existing rows where
`company_name` is set but `abn` is NULL.

Per BU audit gap #9: 142 rows have `abn_matched=true` from seed-era imports
but no `abn` value persisted. The matcher logic is correct (`_match_abn` in
free_enrichment.py); this script re-runs the local matching path against
existing rows so they get the raw ABN populated.

Strategy:
  1. Query rows with company_name populated and abn IS NULL
  2. For each, call FreeEnrichment._local_abn_match(company_name, state, suburb)
  3. If match found, UPDATE abn + gst_registered + entity_type + registration_date

Usage:
    python scripts/backfill_abn_for_existing_rows.py [--limit N] [--dry-run]

Idempotent — running twice on same row = no-op (filtered by `abn IS NULL`).
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import os
import sys
from pathlib import Path

import asyncpg

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from src.pipeline.free_enrichment import FreeEnrichment  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("backfill_abn")


SELECT_SQL = """
    SELECT id, domain, company_name, state, gmb_address
      FROM business_universe
     WHERE abn IS NULL
       AND company_name IS NOT NULL
       AND company_name != ''
     ORDER BY id
     LIMIT $1
"""

UPDATE_SQL = """
    UPDATE business_universe
       SET abn = $2,
           gst_registered = COALESCE($3, gst_registered),
           entity_type = COALESCE($4, entity_type),
           registration_date = COALESCE($5, registration_date),
           abn_matched = true,
           updated_at = NOW()
     WHERE id = $1
"""


async def backfill(limit: int, dry_run: bool) -> tuple[int, int]:
    """Returns (rows_processed, rows_matched)."""
    db_url = os.environ.get("DATABASE_URL", "").replace("postgresql+asyncpg://", "postgresql://")
    if not db_url:
        raise RuntimeError("DATABASE_URL not set")

    conn = await asyncpg.connect(db_url, statement_cache_size=0)
    try:
        rows = await conn.fetch(SELECT_SQL, limit)
        logger.info("Fetched %d candidate rows", len(rows))

        fe = FreeEnrichment(conn)
        matched = 0
        for row in rows:
            try:
                # Build a minimal title for the local matcher to consume.
                # _local_abn_match expects (search_title, state_hint, suburb)
                suburb = None
                if row["gmb_address"]:
                    parts = row["gmb_address"].split(",")
                    suburb = parts[-2].strip() if len(parts) >= 2 else None
                result = await fe._local_abn_match(
                    row["company_name"], state_hint=row["state"], suburb=suburb
                )
            except Exception as exc:
                logger.warning("match failed id=%s domain=%s: %s", row["id"], row["domain"], exc)
                continue

            if not result or not result.get("abn"):
                continue

            matched += 1
            if dry_run:
                logger.info(
                    "DRY-RUN id=%s domain=%s → abn=%s",
                    row["id"],
                    row["domain"],
                    result.get("abn"),
                )
                continue

            await conn.execute(
                UPDATE_SQL,
                row["id"],
                result.get("abn"),
                result.get("gst_registered"),
                result.get("entity_type"),
                result.get("registration_date"),
            )

        return len(rows), matched
    finally:
        await conn.close()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=10000)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    processed, matched = asyncio.run(backfill(args.limit, args.dry_run))
    logger.info(
        "Backfill complete: processed=%d matched=%d (dry_run=%s)", processed, matched, args.dry_run
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
