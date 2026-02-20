#!/usr/bin/env python3
"""
Test ABN→GMB Fuzzy Match Rate
CEO Directive #008 Research

Tests whether ABN legal names successfully match to GMB trading names
using the Tier 2 fuzzy matcher from siege_waterfall.py.

Target: 200 random ABN records (service industry, active GST)
Output: Match rate + 10 failure examples
"""

import asyncio
import json
import random
import sys
from datetime import datetime
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from fuzzywuzzy import fuzz

# Reuse constants from siege_waterfall
FUZZY_MATCH_THRESHOLD = 70

# Service industry search terms (common agency/service businesses)
SERVICE_SEARCH_TERMS = [
    "marketing agency",
    "digital agency",
    "creative agency",
    "advertising agency",
    "web design",
    "consulting",
    "accounting",
    "law firm",
    "real estate",
    "recruitment",
    "IT services",
    "financial services",
    "insurance broker",
    "mortgage broker",
]

# States to sample from
STATES = ["NSW", "VIC", "QLD", "WA", "SA"]


async def fetch_abn_records(target_count: int = 200) -> list[dict]:
    """Fetch ABN records via API."""
    from src.integrations.abn_client import ABNClient

    records = []
    client = ABNClient()

    print(f"[ABN] Fetching {target_count} records...")

    try:
        # Search across different terms and states
        for term in SERVICE_SEARCH_TERMS:
            if len(records) >= target_count:
                break

            for state in STATES:
                if len(records) >= target_count:
                    break

                try:
                    results = await client.search_by_name(
                        name=term,
                        state=state,
                        limit=20,
                    )

                    for r in results:
                        if r.get("status") == "Active" and r.get("business_name"):
                            records.append(r)
                            if len(records) >= target_count:
                                break

                    # Rate limit
                    await asyncio.sleep(0.3)

                except Exception as e:
                    print(f"[ABN] Search failed for {term}/{state}: {e}")
                    continue

        print(f"[ABN] Fetched {len(records)} records")

    finally:
        await client.close()

    return records[:target_count]


async def search_gmb(business_name: str, state: str) -> dict | None:
    """Search GMB for a business name."""
    from src.integrations.gmb_scraper import GMBScraper

    try:
        scraper = GMBScraper()
        location = f"{state}, Australia"
        result = await scraper.search_business(business_name, location)
        return result.to_dict() if hasattr(result, 'to_dict') else result
    except Exception as e:
        return {"found": False, "error": str(e)}


def fuzzy_match(abn_name: str, gmb_name: str) -> tuple[int, bool]:
    """
    Run fuzzy match like siege_waterfall.py does.
    Returns (score, passes_threshold)
    """
    if not abn_name or not gmb_name:
        return 0, False

    # Use same logic as siege_waterfall.py tier2_gmb
    score = max(
        fuzz.ratio(abn_name.lower(), gmb_name.lower()),
        fuzz.token_set_ratio(abn_name.lower(), gmb_name.lower()),
    )

    return score, score >= FUZZY_MATCH_THRESHOLD


async def run_test():
    """Run the match rate test."""
    print("=" * 60)
    print("ABN→GMB FUZZY MATCH RATE TEST")
    print(f"Threshold: {FUZZY_MATCH_THRESHOLD}%")
    print(f"Started: {datetime.now().isoformat()}")
    print("=" * 60)

    # Fetch ABN records
    abn_records = await fetch_abn_records(200)

    if len(abn_records) < 50:
        print(f"[ERROR] Only got {len(abn_records)} records - need at least 50")
        return

    # Shuffle for randomness
    random.shuffle(abn_records)

    results = []
    passes = 0
    fails = 0
    errors = 0

    print(f"\n[TEST] Running GMB matches for {len(abn_records)} businesses...")
    print("-" * 60)

    for i, record in enumerate(abn_records):
        abn_name = record.get("business_name", "")
        state = record.get("state", "NSW")
        abn = record.get("abn_raw", record.get("abn", ""))

        if not abn_name:
            continue

        # Search GMB
        gmb_result = await search_gmb(abn_name, state)

        # Extract GMB name
        gmb_name = ""
        if gmb_result and gmb_result.get("found"):
            gmb_name = gmb_result.get("name", "")

        # Fuzzy match
        score, passed = fuzzy_match(abn_name, gmb_name)

        result = {
            "abn": abn,
            "abn_name": abn_name,
            "state": state,
            "gmb_name": gmb_name if gmb_name else "(not found)",
            "match_score": score,
            "passed": passed,
            "gmb_error": gmb_result.get("error") if gmb_result else None,
        }
        results.append(result)

        if gmb_result and gmb_result.get("error"):
            errors += 1
            status = "ERROR"
        elif passed:
            passes += 1
            status = "PASS"
        else:
            fails += 1
            status = "FAIL"

        # Progress update every 10
        if (i + 1) % 10 == 0:
            print(f"[{i+1}/{len(abn_records)}] {status}: {abn_name[:40]:<40} → {gmb_name[:30] if gmb_name else '(none)':<30} ({score}%)")

        # Rate limit GMB requests
        await asyncio.sleep(2.5)  # 2.5s between GMB requests

    # Calculate stats
    total_tested = passes + fails
    match_rate = (passes / total_tested * 100) if total_tested > 0 else 0

    print("\n" + "=" * 60)
    print("RESULTS")
    print("=" * 60)
    print(f"Total records: {len(abn_records)}")
    print(f"Successfully tested: {total_tested}")
    print(f"GMB errors/timeouts: {errors}")
    print(f"Matches (≥{FUZZY_MATCH_THRESHOLD}%): {passes}")
    print(f"Failures (<{FUZZY_MATCH_THRESHOLD}%): {fails}")
    print(f"\n>>> MATCH RATE: {match_rate:.1f}% <<<")
    print("=" * 60)

    # Show failure examples
    failures = [r for r in results if not r["passed"] and not r.get("gmb_error")]
    print("\n10 FAILURE EXAMPLES (for CEO review):")
    print("-" * 60)

    for i, fail in enumerate(failures[:10]):
        print(f"{i+1}. ABN: {fail['abn_name']}")
        print(f"   GMB: {fail['gmb_name']}")
        print(f"   Score: {fail['match_score']}% (threshold: {FUZZY_MATCH_THRESHOLD}%)")
        print()

    # Save full results
    output_file = Path(__file__).parent / "abn_gmb_match_results.json"
    with open(output_file, "w") as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "threshold": FUZZY_MATCH_THRESHOLD,
            "total_records": len(abn_records),
            "tested": total_tested,
            "errors": errors,
            "passes": passes,
            "fails": fails,
            "match_rate_percent": round(match_rate, 1),
            "results": results,
        }, f, indent=2)

    print(f"\nFull results saved to: {output_file}")

    return match_rate, failures[:10]


if __name__ == "__main__":
    asyncio.run(run_test())
