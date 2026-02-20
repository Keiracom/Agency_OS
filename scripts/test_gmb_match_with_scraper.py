#!/usr/bin/env python3
"""
ABN→GMB Match Rate Test using GMBScraper with proxy rotation
CEO Directive #008 Research
"""

import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from fuzzywuzzy import fuzz

FUZZY_MATCH_THRESHOLD = 70

# 50 test records (mix of likely matches and failures)
ABN_RECORDS = [
    # Service businesses - likely matches
    {"name": "Sydney Digital Marketing Pty Ltd", "state": "NSW"},
    {"name": "Melbourne Web Design Pty Ltd", "state": "VIC"},
    {"name": "Brisbane IT Solutions Pty Ltd", "state": "QLD"},
    {"name": "Perth Accounting Services Pty Ltd", "state": "WA"},
    {"name": "Adelaide Law Firm Pty Ltd", "state": "SA"},
    {"name": "Gold Coast Real Estate Pty Ltd", "state": "QLD"},
    {"name": "Parramatta Dental Clinic Pty Ltd", "state": "NSW"},
    {"name": "Geelong Plumbing Services Pty Ltd", "state": "VIC"},
    {"name": "Cairns Travel Agency Pty Ltd", "state": "QLD"},
    {"name": "Newcastle Motor Repairs Pty Ltd", "state": "NSW"},

    # Professional services
    {"name": "Smith & Partners Accountants Pty Ltd", "state": "NSW"},
    {"name": "Johnson Legal Services Pty Ltd", "state": "VIC"},
    {"name": "Williams Financial Advisors Pty Ltd", "state": "QLD"},
    {"name": "Brown Medical Practice Pty Ltd", "state": "NSW"},
    {"name": "Taylor Engineering Consultants Pty Ltd", "state": "WA"},
    {"name": "Anderson Architects Pty Ltd", "state": "VIC"},
    {"name": "Thompson Builders Pty Ltd", "state": "QLD"},
    {"name": "Wilson Electrical Services Pty Ltd", "state": "NSW"},
    {"name": "Martin Landscaping Pty Ltd", "state": "SA"},
    {"name": "Harris Cleaning Services Pty Ltd", "state": "VIC"},

    # Retail/Food
    {"name": "Harbour View Restaurant Pty Ltd", "state": "NSW"},
    {"name": "Central Cafe Pty Ltd", "state": "VIC"},
    {"name": "Riverside Bakery Pty Ltd", "state": "QLD"},
    {"name": "Ocean Fresh Seafood Pty Ltd", "state": "WA"},
    {"name": "City Pharmacy Pty Ltd", "state": "NSW"},
    {"name": "Suburban Hardware Pty Ltd", "state": "VIC"},
    {"name": "Coastal Pet Supplies Pty Ltd", "state": "QLD"},
    {"name": "Urban Gym Pty Ltd", "state": "NSW"},
    {"name": "Village Butcher Pty Ltd", "state": "SA"},
    {"name": "Mountain View Hotel Pty Ltd", "state": "VIC"},

    # Trades
    {"name": "Aussie Plumbers Pty Ltd", "state": "NSW"},
    {"name": "Sydney Electricians Pty Ltd", "state": "NSW"},
    {"name": "Melbourne Roofers Pty Ltd", "state": "VIC"},
    {"name": "Brisbane Air Conditioning Pty Ltd", "state": "QLD"},
    {"name": "Perth Pest Control Pty Ltd", "state": "WA"},
    {"name": "Adelaide Locksmiths Pty Ltd", "state": "SA"},
    {"name": "Canberra Carpet Cleaners Pty Ltd", "state": "ACT"},
    {"name": "Darwin Pool Services Pty Ltd", "state": "NT"},
    {"name": "Hobart Painters Pty Ltd", "state": "TAS"},
    {"name": "Wollongong Tilers Pty Ltd", "state": "NSW"},

    # Generic/Holdings - likely failures
    {"name": "JKL Holdings Pty Ltd", "state": "NSW"},
    {"name": "XYZ Enterprises Pty Ltd", "state": "VIC"},
    {"name": "ABC Investments Pty Ltd", "state": "QLD"},
    {"name": "Smith Family Trust Pty Ltd", "state": "NSW"},
    {"name": "123 Properties Pty Ltd", "state": "VIC"},
    {"name": "AAA Services Pty Ltd", "state": "QLD"},
    {"name": "First Choice Group Pty Ltd", "state": "WA"},
    {"name": "Premium Ventures Pty Ltd", "state": "SA"},
    {"name": "Global Trading Pty Ltd", "state": "NSW"},
    {"name": "National Solutions Pty Ltd", "state": "VIC"},
]


def clean_name(name: str) -> str:
    """Strip Pty Ltd suffixes."""
    for suffix in [" pty ltd", " pty. ltd.", " proprietary limited", " limited", " ltd"]:
        if name.lower().endswith(suffix):
            name = name[:-len(suffix)]
    return name.strip()


def fuzzy_match(abn_name: str, gmb_name: str) -> tuple[int, bool]:
    """Fuzzy match like siege_waterfall.py."""
    if not abn_name or not gmb_name:
        return 0, False

    abn_clean = clean_name(abn_name)

    score = max(
        fuzz.ratio(abn_clean.lower(), gmb_name.lower()),
        fuzz.token_set_ratio(abn_clean.lower(), gmb_name.lower()),
    )

    return score, score >= FUZZY_MATCH_THRESHOLD


async def run_test():
    """Run test using GMBScraper."""
    from src.integrations.gmb_scraper import GMBScraper

    print("=" * 70)
    print("ABN→GMB MATCH RATE TEST (with proxy rotation)")
    print(f"Threshold: {FUZZY_MATCH_THRESHOLD}%")
    print(f"Records: {len(ABN_RECORDS)}")
    print(f"Started: {datetime.now().isoformat()}")
    print("=" * 70)

    scraper = GMBScraper()
    results = []
    passes = 0
    fails = 0
    errors = 0

    for i, record in enumerate(ABN_RECORDS):
        abn_name = record["name"]
        state = record["state"]
        location = f"{state}, Australia"

        # Search using GMBScraper
        search_name = clean_name(abn_name)
        gmb_result = await scraper.search_business(search_name, location)

        gmb_name = gmb_result.get("name", "") if gmb_result.get("found") else ""

        # Fuzzy match
        score, passed = fuzzy_match(abn_name, gmb_name)

        result = {
            "abn_name": abn_name,
            "state": state,
            "gmb_name": gmb_name if gmb_name else "(not found)",
            "match_score": score,
            "passed": passed,
            "error": gmb_result.get("error"),
        }
        results.append(result)

        if gmb_result.get("error"):
            errors += 1
            status = "ERR"
        elif passed:
            passes += 1
            status = "✓"
        else:
            fails += 1
            status = "✗"

        print(f"[{i+1:2d}/{len(ABN_RECORDS)}] {status} [{score:3d}%] {clean_name(abn_name)[:32]:<32} → {gmb_name[:25] if gmb_name else '(none)':<25}")

        # Small delay between requests (scraper has its own rate limiting)
        await asyncio.sleep(0.5)

    # Results
    total_tested = passes + fails
    match_rate = (passes / total_tested * 100) if total_tested > 0 else 0

    print("\n" + "=" * 70)
    print("RESULTS")
    print("=" * 70)
    print(f"Total:   {len(ABN_RECORDS)}")
    print(f"Tested:  {total_tested}")
    print(f"Errors:  {errors}")
    print(f"Matches: {passes}")
    print(f"Fails:   {fails}")
    print(f"\n>>> MATCH RATE: {match_rate:.1f}% <<<")
    print("=" * 70)

    # Failures
    failures = [r for r in results if not r["passed"] and not r.get("error")]
    print("\n10 FAILURE EXAMPLES:")
    print("-" * 70)
    for i, f in enumerate(failures[:10]):
        print(f"{i+1}. ABN: {f['abn_name']}")
        print(f"   GMB: {f['gmb_name']}")
        print(f"   Score: {f['match_score']}%")
        print()

    # Save
    output = Path(__file__).parent / "abn_gmb_match_results.json"
    with open(output, "w") as fp:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "threshold": FUZZY_MATCH_THRESHOLD,
            "total": len(ABN_RECORDS),
            "tested": total_tested,
            "errors": errors,
            "passes": passes,
            "fails": fails,
            "match_rate": round(match_rate, 1),
            "results": results,
        }, fp, indent=2)

    print(f"Results saved: {output}")


if __name__ == "__main__":
    asyncio.run(run_test())
