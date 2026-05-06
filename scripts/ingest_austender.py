#!/usr/bin/env python3
"""Daily AusTender ingest — fetch supplier awards and write to BU.

Defaults to dry-run (no DB writes) unless --live is passed. Live mode
prompts for explicit "INGEST" confirmation before any writes.

Usage:
    # Yesterday's awards, dry run
    python scripts/ingest_austender.py

    # Yesterday's awards, live ingest
    python scripts/ingest_austender.py --live

    # 30-day backfill on first run
    python scripts/ingest_austender.py --backfill-days 30 --live

    # Specific date range
    python scripts/ingest_austender.py --date-from 2026-04-01 --date-to 2026-04-07

    # Lower value threshold for noise tuning
    python scripts/ingest_austender.py --min-value 25000
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import os
import sys
from datetime import date, datetime, timedelta
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


def _parse_date(s: str) -> date:
    return datetime.strptime(s, "%Y-%m-%d").date()


async def _connect():
    """Open an asyncpg connection from DATABASE_URL or DATABASE_URL_MIGRATIONS."""
    import asyncpg

    dsn = os.environ.get("DATABASE_URL_MIGRATIONS") or os.environ.get("DATABASE_URL", "")
    if not dsn:
        sys.exit("ERROR: DATABASE_URL not configured (looked in env + .env file)")
    if dsn.startswith("postgresql+asyncpg://"):
        dsn = dsn.replace("postgresql+asyncpg://", "postgresql://", 1)
    return await asyncpg.connect(dsn)


async def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--date-from", type=_parse_date, help="Inclusive lower bound (YYYY-MM-DD)")
    ap.add_argument("--date-to", type=_parse_date, help="Inclusive upper bound (YYYY-MM-DD)")
    ap.add_argument(
        "--backfill-days",
        type=int,
        default=None,
        help="Backfill last N days (overrides date-from/date-to). Use 30 for first-run seed.",
    )
    ap.add_argument(
        "--min-value",
        type=int,
        default=50000,
        help="Minimum AUD contract value (default 50000). Below 1000 rejected as noise.",
    )
    ap.add_argument(
        "--live",
        action="store_true",
        help="Actually write to BU (default = dry run, no DB writes).",
    )
    args = ap.parse_args()

    # Resolve date range
    today = date.today()
    if args.backfill_days is not None:
        if args.backfill_days < 1 or args.backfill_days > 90:
            sys.exit("ERROR: --backfill-days must be between 1 and 90")
        date_from = today - timedelta(days=args.backfill_days)
        date_to = today - timedelta(days=1)
    elif args.date_from and args.date_to:
        date_from = args.date_from
        date_to = args.date_to
    else:
        # Default: yesterday only
        date_from = today - timedelta(days=1)
        date_to = today - timedelta(days=1)

    if date_to >= today:
        sys.exit(f"ERROR: date_to {date_to} must be < today {today}")
    if date_to < date_from:
        sys.exit(f"ERROR: date_to {date_to} before date_from {date_from}")

    mode = "LIVE" if args.live else "DRY-RUN"
    days = (date_to - date_from).days + 1

    print(f"\n{'=' * 60}")
    print(f"AusTender Ingest — {mode}")
    print(f"{'=' * 60}")
    print(f"  Date range:        {date_from} → {date_to}  ({days} day{'s' if days != 1 else ''})")
    print(f"  Min value (AUD):   {args.min_value:,}")
    print(f"  Output to BU:      {'YES (writes)' if args.live else 'NO (dry-run logging only)'}")
    print(f"{'=' * 60}\n")

    if args.live:
        confirm = input(
            "About to ingest into business_universe. Type INGEST to confirm: "
        ).strip()
        if confirm != "INGEST":
            print("Aborted.")
            return 1

    from src.pipeline.austender_discovery import run_ingest

    conn = await _connect() if args.live else None
    try:
        result = await run_ingest(
            date_from=date_from,
            date_to=date_to,
            conn=conn,
            value_min_aud=args.min_value,
            dry_run=not args.live,
        )
    finally:
        if conn is not None:
            await conn.close()

    print(f"\n{'=' * 60}")
    print(f"Ingest Result — {mode}")
    print(f"{'=' * 60}")
    print(f"  Fetched (raw OCDS):      {result.fetched}")
    print(f"  Parsed (typed events):   {result.parsed}")
    print(f"  Filtered non-AU:         {result.filtered_non_au}")
    print(f"  Filtered low-value:      {result.filtered_low_value}")
    if args.live:
        print(f"  Inserted (new BU rows):  {result.inserted}")
        print(f"  Updated (existing rows): {result.updated}")
    else:
        eligible = result.parsed - result.filtered_non_au - result.filtered_low_value
        print(f"  Would-write (eligible):  {eligible}")
    print(f"  Errors:                  {result.errors}")
    print(f"{'=' * 60}\n")

    return 0 if result.errors == 0 else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
