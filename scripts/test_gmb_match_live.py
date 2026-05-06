#!/usr/bin/env python3
"""
LIVE ABN→GMB Fuzzy Match Rate Test
CEO Directive #008 Research

Uses real Google Maps searches to test match rates.
"""

import asyncio
import json
import random
import re
from datetime import datetime
from pathlib import Path
from urllib.parse import quote_plus

import httpx
from fuzzywuzzy import fuzz

FUZZY_MATCH_THRESHOLD = 70

# Realistic Australian business names (ABN legal name format)
# Mix of: Direct matches, trading-as variations, holding companies
ABN_RECORDS = [
    # Service businesses - likely direct matches
    {"name": "Sydney Digital Marketing Pty Ltd", "state": "NSW", "postcode": "2000"},
    {"name": "Melbourne Web Design Studio Pty Ltd", "state": "VIC", "postcode": "3000"},
    {"name": "Brisbane IT Solutions Pty Ltd", "state": "QLD", "postcode": "4000"},
    {"name": "Perth Creative Agency Pty Ltd", "state": "WA", "postcode": "6000"},
    {"name": "Adelaide Accounting Services Pty Ltd", "state": "SA", "postcode": "5000"},
    {"name": "Canberra Consulting Group Pty Ltd", "state": "ACT", "postcode": "2600"},
    {"name": "Gold Coast Real Estate Pty Ltd", "state": "QLD", "postcode": "4217"},
    {"name": "Bondi Beach Fitness Pty Ltd", "state": "NSW", "postcode": "2026"},
    {"name": "Parramatta Legal Services Pty Ltd", "state": "NSW", "postcode": "2150"},
    {"name": "Geelong Motor Repairs Pty Ltd", "state": "VIC", "postcode": "3220"},
    # Professional services
    {"name": "Smith & Partners Lawyers Pty Ltd", "state": "NSW", "postcode": "2000"},
    {"name": "Johnson Accounting Pty Ltd", "state": "VIC", "postcode": "3000"},
    {"name": "Williams Financial Planning Pty Ltd", "state": "QLD", "postcode": "4000"},
    {"name": "Brown Medical Centre Pty Ltd", "state": "NSW", "postcode": "2065"},
    {"name": "Taylor Dental Clinic Pty Ltd", "state": "VIC", "postcode": "3121"},
    {"name": "Anderson Engineering Pty Ltd", "state": "WA", "postcode": "6000"},
    {"name": "Thompson Construction Pty Ltd", "state": "QLD", "postcode": "4000"},
    {"name": "Wilson Plumbing Services Pty Ltd", "state": "NSW", "postcode": "2148"},
    {"name": "Martin Electrical Pty Ltd", "state": "VIC", "postcode": "3000"},
    {"name": "Harris Landscaping Pty Ltd", "state": "SA", "postcode": "5000"},
    # Retail/Hospitality
    {"name": "Harbour View Restaurant Pty Ltd", "state": "NSW", "postcode": "2000"},
    {"name": "Central Coffee House Pty Ltd", "state": "VIC", "postcode": "3000"},
    {"name": "Riverside Cafe Pty Ltd", "state": "QLD", "postcode": "4000"},
    {"name": "Ocean Breeze Bakery Pty Ltd", "state": "WA", "postcode": "6000"},
    {"name": "Mountain View Hotel Pty Ltd", "state": "VIC", "postcode": "3777"},
    {"name": "City Central Pharmacy Pty Ltd", "state": "NSW", "postcode": "2000"},
    {"name": "Suburban Hardware Store Pty Ltd", "state": "VIC", "postcode": "3150"},
    {"name": "Coastal Pet Supplies Pty Ltd", "state": "QLD", "postcode": "4217"},
    {"name": "Urban Fitness Centre Pty Ltd", "state": "NSW", "postcode": "2000"},
    {"name": "Village Butcher Shop Pty Ltd", "state": "SA", "postcode": "5000"},
    # Trades
    {"name": "Aussie Plumbers Pty Ltd", "state": "NSW", "postcode": "2000"},
    {"name": "Sydney Sparkies Electrical Pty Ltd", "state": "NSW", "postcode": "2150"},
    {"name": "Melbourne Roofing Solutions Pty Ltd", "state": "VIC", "postcode": "3000"},
    {"name": "Brisbane Air Conditioning Pty Ltd", "state": "QLD", "postcode": "4000"},
    {"name": "Perth Pest Control Pty Ltd", "state": "WA", "postcode": "6000"},
    {"name": "Adelaide Locksmiths Pty Ltd", "state": "SA", "postcode": "5000"},
    {"name": "Canberra Carpet Cleaning Pty Ltd", "state": "ACT", "postcode": "2600"},
    {"name": "Darwin Pool Services Pty Ltd", "state": "NT", "postcode": "0800"},
    {"name": "Hobart Heating Systems Pty Ltd", "state": "TAS", "postcode": "7000"},
    {"name": "Newcastle Tiling Pty Ltd", "state": "NSW", "postcode": "2300"},
    # More specific businesses
    {"name": "Eastern Suburbs Dentistry Pty Ltd", "state": "NSW", "postcode": "2026"},
    {"name": "Northern Beaches Physio Pty Ltd", "state": "NSW", "postcode": "2100"},
    {"name": "Inner West Chiropractic Pty Ltd", "state": "NSW", "postcode": "2040"},
    {"name": "South Melbourne Pilates Pty Ltd", "state": "VIC", "postcode": "3205"},
    {"name": "North Sydney Yoga Studio Pty Ltd", "state": "NSW", "postcode": "2060"},
    {"name": "Surry Hills Hair Salon Pty Ltd", "state": "NSW", "postcode": "2010"},
    {"name": "Fitzroy Beauty Spa Pty Ltd", "state": "VIC", "postcode": "3065"},
    {"name": "Newtown Tattoo Parlour Pty Ltd", "state": "NSW", "postcode": "2042"},
    {"name": "Fremantle Fish Market Pty Ltd", "state": "WA", "postcode": "6160"},
    {"name": "Byron Bay Surf School Pty Ltd", "state": "NSW", "postcode": "2481"},
    # Generic/Holding company names (likely to fail)
    {"name": "JKL Holdings Pty Ltd", "state": "NSW", "postcode": "2000"},
    {"name": "XYZ Enterprises Pty Ltd", "state": "VIC", "postcode": "3000"},
    {"name": "ABC Investments Pty Ltd", "state": "QLD", "postcode": "4000"},
    {"name": "Family Trust Services Pty Ltd", "state": "NSW", "postcode": "2000"},
    {"name": "Smith Family Holdings Pty Ltd", "state": "VIC", "postcode": "3000"},
    {"name": "123 Properties Pty Ltd", "state": "QLD", "postcode": "4000"},
    {"name": "AAA Business Solutions Pty Ltd", "state": "WA", "postcode": "6000"},
    {"name": "First Choice Ventures Pty Ltd", "state": "SA", "postcode": "5000"},
    {"name": "Premium Services Group Pty Ltd", "state": "NSW", "postcode": "2000"},
    {"name": "Global Trading Co Pty Ltd", "state": "VIC", "postcode": "3000"},
    # Tech/Digital
    {"name": "Digital Spark Agency Pty Ltd", "state": "NSW", "postcode": "2000"},
    {"name": "Cloud Nine Computing Pty Ltd", "state": "VIC", "postcode": "3000"},
    {"name": "Pixel Perfect Design Pty Ltd", "state": "QLD", "postcode": "4000"},
    {"name": "Code Warriors Software Pty Ltd", "state": "NSW", "postcode": "2000"},
    {"name": "Data Insights Analytics Pty Ltd", "state": "VIC", "postcode": "3000"},
    {"name": "App Factory Mobile Pty Ltd", "state": "NSW", "postcode": "2000"},
    {"name": "Cyber Shield Security Pty Ltd", "state": "VIC", "postcode": "3000"},
    {"name": "Tech Support Geeks Pty Ltd", "state": "QLD", "postcode": "4000"},
    {"name": "Network Solutions Australia Pty Ltd", "state": "NSW", "postcode": "2000"},
    {"name": "Digital Marketing Experts Pty Ltd", "state": "VIC", "postcode": "3000"},
    # More trades
    {"name": "Sydney Mobile Mechanic Pty Ltd", "state": "NSW", "postcode": "2000"},
    {"name": "Melbourne Glass Repairs Pty Ltd", "state": "VIC", "postcode": "3000"},
    {"name": "Brisbane Concreting Pty Ltd", "state": "QLD", "postcode": "4000"},
    {"name": "Perth Fencing Solutions Pty Ltd", "state": "WA", "postcode": "6000"},
    {"name": "Adelaide Tree Services Pty Ltd", "state": "SA", "postcode": "5000"},
    {"name": "Canberra Gutter Cleaning Pty Ltd", "state": "ACT", "postcode": "2600"},
    {"name": "Gold Coast Painting Pty Ltd", "state": "QLD", "postcode": "4217"},
    {"name": "Newcastle Removalists Pty Ltd", "state": "NSW", "postcode": "2300"},
    {"name": "Wollongong Skip Bins Pty Ltd", "state": "NSW", "postcode": "2500"},
    {"name": "Townsville Hire Equipment Pty Ltd", "state": "QLD", "postcode": "4810"},
    # Medical/Health
    {"name": "Sydney Skin Clinic Pty Ltd", "state": "NSW", "postcode": "2000"},
    {"name": "Melbourne Eye Centre Pty Ltd", "state": "VIC", "postcode": "3000"},
    {"name": "Brisbane Heart Specialists Pty Ltd", "state": "QLD", "postcode": "4000"},
    {"name": "Perth Orthopaedic Clinic Pty Ltd", "state": "WA", "postcode": "6000"},
    {"name": "Adelaide IVF Centre Pty Ltd", "state": "SA", "postcode": "5000"},
    {"name": "Canberra Sports Medicine Pty Ltd", "state": "ACT", "postcode": "2600"},
    {"name": "Parramatta Radiology Pty Ltd", "state": "NSW", "postcode": "2150"},
    {"name": "St Kilda Pathology Pty Ltd", "state": "VIC", "postcode": "3182"},
    {"name": "Toowoomba Aged Care Pty Ltd", "state": "QLD", "postcode": "4350"},
    {"name": "Ballarat Mental Health Pty Ltd", "state": "VIC", "postcode": "3350"},
    # Auto
    {"name": "Sydney Smash Repairs Pty Ltd", "state": "NSW", "postcode": "2000"},
    {"name": "Melbourne Auto Electrics Pty Ltd", "state": "VIC", "postcode": "3000"},
    {"name": "Brisbane Car Detailing Pty Ltd", "state": "QLD", "postcode": "4000"},
    {"name": "Perth Tyre Centre Pty Ltd", "state": "WA", "postcode": "6000"},
    {"name": "Adelaide Windscreens Pty Ltd", "state": "SA", "postcode": "5000"},
]

# Ensure we have 100
ABN_RECORDS = ABN_RECORDS[:100]


async def search_google_maps(query: str, client: httpx.AsyncClient) -> dict | None:
    """Search Google Maps and extract top result name."""
    try:
        # Use Google Maps search URL
        search_url = f"https://www.google.com/maps/search/{quote_plus(query)}"

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-AU,en;q=0.9",
        }

        response = await client.get(search_url, headers=headers, follow_redirects=True)

        if response.status_code != 200:
            return {"found": False, "error": f"HTTP {response.status_code}"}

        html = response.text

        # Check for blocks
        if "unusual traffic" in html.lower() or "captcha" in html.lower():
            return {"found": False, "error": "blocked"}

        # Extract business name from title
        title_match = re.search(r"<title>([^<]+)</title>", html, re.IGNORECASE)
        if title_match:
            title = title_match.group(1)
            # Clean up title - remove " - Google Maps" suffix
            name = re.sub(r"\s*[-–]\s*Google Maps.*$", "", title).strip()

            # Skip if it's just "Google Maps" (no result)
            if name.lower() in ["google maps", "google", ""]:
                return {"found": False, "name": None}

            return {"found": True, "name": name}

        return {"found": False, "name": None}

    except Exception as e:
        return {"found": False, "error": str(e)}


def clean_abn_name(name: str) -> str:
    """Strip Pty Ltd and common suffixes for matching."""
    cleaned = name
    # Remove common suffixes
    suffixes = [" pty ltd", " pty. ltd.", " proprietary limited", " limited", " ltd"]
    for suffix in suffixes:
        if cleaned.lower().endswith(suffix):
            cleaned = cleaned[: -len(suffix)]
    return cleaned.strip()


def fuzzy_match(abn_name: str, gmb_name: str) -> tuple[int, bool]:
    """Run fuzzy match like siege_waterfall.py."""
    if not abn_name or not gmb_name:
        return 0, False

    # Clean ABN name (strip Pty Ltd)
    abn_clean = clean_abn_name(abn_name)

    score = max(
        fuzz.ratio(abn_clean.lower(), gmb_name.lower()),
        fuzz.token_set_ratio(abn_clean.lower(), gmb_name.lower()),
    )

    return score, score >= FUZZY_MATCH_THRESHOLD


async def run_test():
    """Run the live match rate test."""
    print("=" * 70)
    print("LIVE ABN→GMB FUZZY MATCH RATE TEST")
    print(f"Threshold: {FUZZY_MATCH_THRESHOLD}%")
    print(f"Records: {len(ABN_RECORDS)}")
    print(f"Started: {datetime.now().isoformat()}")
    print("=" * 70)

    results = []
    passes = 0
    fails = 0
    errors = 0

    async with httpx.AsyncClient(timeout=30.0) as client:
        for i, record in enumerate(ABN_RECORDS):
            abn_name = record["name"]
            state = record["state"]
            record["postcode"]

            # Build search query: business name + location
            query = f"{clean_abn_name(abn_name)} {state} Australia"

            # Search GMB
            gmb_result = await search_google_maps(query, client)

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

            # Progress
            print(
                f"[{i + 1:3d}/{len(ABN_RECORDS)}] {status} [{score:3d}%] {clean_abn_name(abn_name)[:35]:<35} → {gmb_name[:25] if gmb_name else '(none)':<25}"
            )

            # Rate limit (be nice to Google)
            await asyncio.sleep(2.0 + random.random())

            # Stop early if we get blocked
            if errors > 10 and errors > len(results) * 0.5:
                print("\n[ABORT] Too many errors - likely blocked. Stopping.")
                break

    # Stats
    total_tested = passes + fails
    match_rate = (passes / total_tested * 100) if total_tested > 0 else 0

    print("\n" + "=" * 70)
    print("RESULTS")
    print("=" * 70)
    print(f"Total records:    {len(ABN_RECORDS)}")
    print(f"Successfully tested: {total_tested}")
    print(f"Errors/blocked:   {errors}")
    print(f"Matches (≥{FUZZY_MATCH_THRESHOLD}%):   {passes}")
    print(f"Failures (<{FUZZY_MATCH_THRESHOLD}%):  {fails}")
    print(f"\n>>> MATCH RATE: {match_rate:.1f}% <<<")
    print("=" * 70)

    # Failure examples
    failures = [r for r in results if not r["passed"] and not r.get("error")]
    print("\n10 FAILURE EXAMPLES:")
    print("-" * 70)

    for i, fail in enumerate(failures[:10]):
        print(f"{i + 1}. ABN:   {fail['abn_name']}")
        print(f"   GMB:   {fail['gmb_name']}")
        print(f"   Score: {fail['match_score']}% (threshold: {FUZZY_MATCH_THRESHOLD}%)")
        print()

    # Save results
    output_file = Path(__file__).parent / "abn_gmb_match_results.json"
    with open(output_file, "w") as f:
        json.dump(
            {
                "timestamp": datetime.now().isoformat(),
                "threshold": FUZZY_MATCH_THRESHOLD,
                "total_records": len(ABN_RECORDS),
                "tested": total_tested,
                "errors": errors,
                "passes": passes,
                "fails": fails,
                "match_rate_percent": round(match_rate, 1),
                "results": results,
            },
            f,
            indent=2,
        )

    print(f"\nFull results saved to: {output_file}")

    return match_rate


if __name__ == "__main__":
    asyncio.run(run_test())
