#!/usr/bin/env python3
"""Backfill BU rows stuck at pipeline_stage=0 through the cohort runner.

Selects domains from business_universe where pipeline_stage=0 (discovered
but never enriched) and feeds them into the existing cohort_runner pipeline
in configurable batch sizes.

Usage:
    # Dry run (default) — shows which domains would be processed
    python scripts/backfill_stage0.py --batch 50

    # Live run — actually processes domains through the pipeline
    python scripts/backfill_stage0.py --batch 50 --live

    # Offset for resumption after partial run
    python scripts/backfill_stage0.py --batch 50 --offset 100 --live
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv

load_dotenv("/home/elliotbot/.config/agency-os/.env")
load_dotenv("/home/elliotbot/clawd/Agency_OS/config/.env")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


async def fetch_stage0_domains(batch_size: int, offset: int = 0) -> list[str]:
    """Query BU for domains stuck at pipeline_stage=0."""
    import asyncpg

    dsn = os.environ.get("DATABASE_URL_MIGRATIONS") or os.environ.get("DATABASE_URL", "")
    if dsn.startswith("postgresql+asyncpg://"):
        dsn = dsn.replace("postgresql+asyncpg://", "postgresql://", 1)

    conn = await asyncpg.connect(dsn)
    try:
        rows = await conn.fetch(
            "SELECT domain FROM public.business_universe "
            "WHERE pipeline_stage = 0 AND domain IS NOT NULL "
            "ORDER BY created_at DESC "
            "LIMIT $1 OFFSET $2",
            batch_size,
            offset,
        )
        return [r["domain"] for r in rows]
    finally:
        await conn.close()


async def count_stage0() -> int:
    """Count total BU rows at pipeline_stage=0."""
    import asyncpg

    dsn = os.environ.get("DATABASE_URL_MIGRATIONS") or os.environ.get("DATABASE_URL", "")
    if dsn.startswith("postgresql+asyncpg://"):
        dsn = dsn.replace("postgresql+asyncpg://", "postgresql://", 1)

    conn = await asyncpg.connect(dsn)
    try:
        row = await conn.fetchrow(
            "SELECT count(*) as cnt FROM public.business_universe WHERE pipeline_stage = 0"
        )
        return row["cnt"] if row else 0
    finally:
        await conn.close()


async def main():
    parser = argparse.ArgumentParser(description="Backfill stage-0 BU rows through pipeline")
    parser.add_argument("--batch", type=int, default=50, help="Domains per batch (default 50)")
    parser.add_argument("--offset", type=int, default=0, help="Skip first N rows (for resumption)")
    parser.add_argument(
        "--live", action="store_true", help="Actually run pipeline (default: dry run)"
    )
    parser.add_argument("--output", help="Output directory for results")
    args = parser.parse_args()

    total = await count_stage0()
    logger.info("Stage-0 rows in BU: %d", total)

    if total == 0:
        print("No stage-0 rows to backfill.")
        return

    domains = await fetch_stage0_domains(args.batch, args.offset)
    logger.info("Fetched %d domains (batch=%d, offset=%d)", len(domains), args.batch, args.offset)

    if not domains:
        print("No domains in this batch range.")
        return

    mode = "LIVE" if args.live else "DRY-RUN"
    cost_estimate = len(domains) * 0.25
    print(f"\n{'=' * 60}")
    print(f"Stage-0 Backfill — {mode}")
    print(f"{'=' * 60}")
    print(f"  Total stage-0 rows:  {total}")
    print(f"  This batch:          {len(domains)} domains")
    print(f"  Offset:              {args.offset}")
    print(f"  Est. cost:           ${cost_estimate:.2f} USD (${cost_estimate * 1.55:.2f} AUD)")
    print(f"  Remaining after:     {total - args.offset - len(domains)}")
    print(f"{'=' * 60}\n")

    if not args.live:
        print("Domains that would be processed:")
        for i, d in enumerate(domains, 1):
            print(f"  {i}. {d}")
        print("\nDry run complete. Use --live to process.")
        return

    confirm = input(
        f"About to process {len(domains)} domains (~${cost_estimate:.2f} USD). "
        "Type BACKFILL to confirm: "
    ).strip()
    if confirm != "BACKFILL":
        print("Aborted.")
        return

    from src.orchestration.cohort_runner import run_cohort

    logger.info("Starting cohort run for %d domains...", len(domains))
    try:
        result = await run_cohort(
            categories=[],
            domains_per_category=0,
            domains=domains,
            output_dir=args.output,
        )
        summary = result.get("summary", {})
        print(f"\n{'=' * 60}")
        print("Backfill Complete")
        print(f"{'=' * 60}")
        print(f"  Processed:  {summary.get('total_processed', len(domains))}")
        print(f"  Passed:     {summary.get('passed', 'N/A')}")
        print(f"  Dropped:    {summary.get('dropped', 'N/A')}")
        print(f"  Errors:     {summary.get('errors', 'N/A')}")
        print(f"  Cost:       ${summary.get('total_cost_usd', 0):.2f} USD")
        print(f"{'=' * 60}")
    except Exception as exc:
        logger.error("Backfill failed: %s", exc)
        raise


if __name__ == "__main__":
    asyncio.run(main())
