"""
ABN Match Sweep — back-fill abn / abn_matched / abn_status_code / abr_last_updated
on business_universe rows that were never matched against the local abn_registry.

DIRECTIVE: BU Closed-Loop Engine — Substep 1 of 4 (instrumentation writes).
COST: AUD 0. Pure local SQL via asyncpg. Zero external API calls.
SAFETY: Only updates rows where fuzzy-match confidence >= MIN_CONFIDENCE.

Column mapping (dispatch named -> existing BU column, since the dispatch
forbids new schema migrations):
  dispatch.abn_status     -> business_universe.abn_status_code  (migration 086)
  dispatch.abr_matched_at -> business_universe.abr_last_updated (migration 086)
  dispatch.abn            -> business_universe.abn              (migration 086)
  dispatch.abn_matched    -> business_universe.abn_matched      (migration 098)

abn_registry shape (from src/pipeline/free_enrichment.py usage):
  abn, legal_name, trading_name, gst_registered, entity_type,
  registration_date, state.
NOTE: abn_registry has no `suburb` column, so the dispatch's
"display_name + suburb + state" fuzzy match is implemented as
"display_name + state" with display_name resolved from the BU row's
trading_name | abr_trading_name | legal_name | display_name fallback chain.

Usage:
    python scripts/abn_match_sweep.py --batch-size 200 --min-confidence 0.7
    python scripts/abn_match_sweep.py --dry-run        # plan only, no writes
    python scripts/abn_match_sweep.py --bu-ids <id>,<id>  # restrict to ids
"""
from __future__ import annotations

import argparse
import asyncio
import logging
import os
import sys
from typing import Any

import asyncpg

logger = logging.getLogger("abn_match_sweep")

DEFAULT_BATCH_SIZE = 200
MIN_CONFIDENCE = 0.7  # pg_trgm similarity threshold


def _resolve_db_url() -> str:
    url = os.environ.get("DATABASE_URL", "")
    if not url:
        raise SystemExit(
            "DATABASE_URL not set. Source the env file before running:\n"
            "  source /home/elliotbot/.config/agency-os/.env"
        )
    # Normalise SQLAlchemy-style URL to asyncpg-friendly form.
    return url.replace("postgresql+asyncpg://", "postgresql://")


async def _select_unmatched_bus(
    conn: asyncpg.Connection,
    batch_size: int,
    bu_ids: list[str] | None,
) -> list[asyncpg.Record]:
    """Pull BU rows where abn_matched IS NOT TRUE (covers FALSE and NULL)."""
    if bu_ids:
        return await conn.fetch(
            """SELECT id, domain, state,
                      legal_name, trading_name, abr_trading_name, display_name
                 FROM business_universe
                WHERE abn_matched IS NOT TRUE
                  AND id = ANY($1::uuid[])
                ORDER BY id
                LIMIT $2""",
            bu_ids, batch_size,
        )
    return await conn.fetch(
        """SELECT id, domain, state,
                  legal_name, trading_name, abr_trading_name, display_name
             FROM business_universe
            WHERE abn_matched IS NOT TRUE
            ORDER BY id
            LIMIT $1""",
        batch_size,
    )


def _resolve_search_name(row: asyncpg.Record) -> str | None:
    """Pick the best available human-readable name for fuzzy matching."""
    for key in ("trading_name", "abr_trading_name", "legal_name", "display_name"):
        v = row.get(key) if hasattr(row, "get") else row[key]
        if v and str(v).strip():
            return str(v).strip()
    return None


async def _fuzzy_match_one(
    conn: asyncpg.Connection,
    name: str,
    state: str | None,
    min_confidence: float,
) -> dict[str, Any] | None:
    """Return the best abn_registry match for `name` (optionally constrained
    to `state`) when similarity >= min_confidence. None otherwise.

    Uses pg_trgm similarity() on the greater of trading_name / legal_name
    similarity. State is an optional exact-match tiebreaker.
    """
    sql = """
        SELECT abn,
               legal_name,
               trading_name,
               gst_registered,
               entity_type,
               registration_date,
               state,
               GREATEST(
                   COALESCE(similarity(trading_name, $1), 0.0),
                   COALESCE(similarity(legal_name,   $1), 0.0)
               ) AS confidence
          FROM abn_registry
         WHERE (
                 trading_name % $1
              OR legal_name   % $1
               )
           AND ($2::text IS NULL OR state IS NULL OR UPPER(state) = UPPER($2))
         ORDER BY confidence DESC
         LIMIT 1
    """
    row = await conn.fetchrow(sql, name, state)
    if row is None:
        return None
    confidence = float(row["confidence"] or 0.0)
    if confidence < min_confidence:
        return None
    return {
        "abn": row["abn"],
        "legal_name": row["legal_name"],
        "trading_name": row["trading_name"],
        "entity_type": row["entity_type"],
        "registration_date": row["registration_date"],
        "state": row["state"],
        "confidence": confidence,
    }


async def _apply_match(
    conn: asyncpg.Connection,
    bu_id: str,
    match: dict[str, Any],
) -> None:
    """Write the match back to business_universe.

    Maps dispatch field names to existing BU columns:
      abn_status     -> abn_status_code   (text)
      abr_matched_at -> abr_last_updated  (timestamptz)
    """
    # Derive an abn_status_code from entity-level signals. abn_registry does
    # not carry a status column, so we infer 'active' for any matched row;
    # downstream ABR refresh will overwrite with authoritative status.
    abn_status_code = "active"
    await conn.execute(
        """UPDATE business_universe
              SET abn               = COALESCE($2, abn),
                  abn_matched       = TRUE,
                  abn_status_code   = COALESCE(abn_status_code, $3),
                  abr_last_updated  = NOW(),
                  updated_at        = NOW()
            WHERE id = $1""",
        bu_id, match["abn"], abn_status_code,
    )


async def sweep(
    db_url: str,
    batch_size: int,
    min_confidence: float,
    dry_run: bool,
    bu_ids: list[str] | None,
) -> dict[str, int]:
    stats = {"total": 0, "matched": 0, "skipped_no_name": 0, "skipped_low_conf": 0, "errors": 0}
    pool = await asyncpg.create_pool(
        db_url, min_size=1, max_size=4, statement_cache_size=0,
    )
    try:
        async with pool.acquire() as conn:
            rows = await _select_unmatched_bus(conn, batch_size, bu_ids)
            stats["total"] = len(rows)
            for row in rows:
                bu_id = str(row["id"])
                name = _resolve_search_name(row)
                if not name:
                    stats["skipped_no_name"] += 1
                    print(f"SKIP no_name bu_id={bu_id} domain={row.get('domain')}")
                    continue
                state = row.get("state")
                try:
                    match = await _fuzzy_match_one(conn, name, state, min_confidence)
                except Exception as exc:
                    stats["errors"] += 1
                    print(f"ERROR bu_id={bu_id} name={name!r}: {exc}")
                    continue
                if match is None:
                    stats["skipped_low_conf"] += 1
                    print(f"SKIP low_conf bu_id={bu_id} name={name!r} state={state}")
                    continue
                if dry_run:
                    print(
                        f"DRY-RUN match bu_id={bu_id} name={name!r} -> "
                        f"abn={match['abn']} conf={match['confidence']:.3f}"
                    )
                else:
                    try:
                        await _apply_match(conn, bu_id, match)
                        stats["matched"] += 1
                        print(
                            f"MATCH bu_id={bu_id} name={name!r} -> "
                            f"abn={match['abn']} conf={match['confidence']:.3f}"
                        )
                    except Exception as exc:
                        stats["errors"] += 1
                        print(f"ERROR write bu_id={bu_id}: {exc}")
    finally:
        await pool.close()
    return stats


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--batch-size", type=int, default=DEFAULT_BATCH_SIZE,
                   help=f"Rows per sweep (default {DEFAULT_BATCH_SIZE})")
    p.add_argument("--min-confidence", type=float, default=MIN_CONFIDENCE,
                   help=f"pg_trgm similarity threshold (default {MIN_CONFIDENCE})")
    p.add_argument("--dry-run", action="store_true",
                   help="Plan only; do not write to BU")
    p.add_argument("--bu-ids", default=None,
                   help="Comma-separated UUIDs to restrict the sweep")
    return p.parse_args()


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    args = _parse_args()
    bu_ids = [s.strip() for s in args.bu_ids.split(",")] if args.bu_ids else None
    db_url = _resolve_db_url()
    stats = asyncio.run(sweep(
        db_url=db_url,
        batch_size=args.batch_size,
        min_confidence=args.min_confidence,
        dry_run=args.dry_run,
        bu_ids=bu_ids,
    ))
    print(f"\nSWEEP SUMMARY: {stats}")
    sys.exit(0 if stats["errors"] == 0 else 1)


if __name__ == "__main__":
    main()
