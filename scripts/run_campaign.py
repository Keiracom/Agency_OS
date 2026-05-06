#!/usr/bin/env python3
"""Run a campaign step against BU prospects.

Usage:
    # Dry run (default — prints what would be sent)
    python scripts/run_campaign.py --sequence campaigns/dental_v1.json --step 1

    # Live send (requires explicit flag + confirmation)
    python scripts/run_campaign.py --sequence campaigns/dental_v1.json --step 1 --live

    # Filter by industry, custom limit
    python scripts/run_campaign.py --sequence campaigns/dental_v1.json --step 1 --industry dental --limit 20
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv

load_dotenv("/home/elliotbot/clawd/Agency_OS/config/.env")
load_dotenv("/home/elliotbot/.config/agency-os/.env")

from src.engines.campaign_executor import CampaignExecutor

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)


async def main():
    parser = argparse.ArgumentParser(description="Run campaign step")
    parser.add_argument("--sequence", required=True, help="Path to sequence JSON")
    parser.add_argument("--step", type=int, default=1, help="Step number to execute")
    parser.add_argument("--limit", type=int, default=50, help="Max prospects per run")
    parser.add_argument("--industry", help="Filter by industry (ILIKE match)")
    parser.add_argument("--min-confidence", type=int, default=70, help="Min dm_email_confidence")
    parser.add_argument("--from-address", help="Sender email address")
    parser.add_argument("--live", action="store_true", help="Actually send (default: dry run)")
    args = parser.parse_args()

    dry_run = not args.live

    if args.live:
        print("\n⚠️  LIVE MODE — emails will be sent for real.")
        confirm = input("Type SEND to confirm: ").strip()
        if confirm != "SEND":
            print("Aborted.")
            sys.exit(0)

    executor = CampaignExecutor(
        sequence_path=args.sequence,
        step=args.step,
        daily_limit=args.limit,
        dry_run=dry_run,
        from_address=args.from_address,
        filter_industry=args.industry,
        min_confidence=args.min_confidence,
    )

    results = await executor.run()
    summary = executor.summary()

    print("\n" + "=" * 60)
    print(f"Campaign Step {args.step} — {'DRY RUN' if dry_run else 'LIVE'}")
    print("=" * 60)
    print(f"  Total prospects: {summary['total']}")
    print(f"  Sent:           {summary['sent']}")
    print(f"  Dry run:        {summary['dry_run_count']}")
    print(f"  Errors:         {summary['errors']}")
    print(f"  Suppressed:     {summary['suppressed']}")
    print("=" * 60)

    if dry_run and results:
        print("\nFirst 5 dry-run previews:")
        for r in results[:5]:
            print(f"  → {r.email} ({r.status})")


if __name__ == "__main__":
    asyncio.run(main())
