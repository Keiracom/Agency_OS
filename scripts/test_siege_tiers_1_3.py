#!/usr/bin/env python3
"""
Test Siege Waterfall Tiers 1-3 with real Australian businesses.

Usage:
    python scripts/test_siege_tiers_1_3.py

Target: $0.05/lead for discovery (Tiers 1-3 only, skip 4-5)
"""

import asyncio
import json
import logging
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.integrations.siege_waterfall import (
    EnrichmentTier,
    SiegeWaterfall,
    get_siege_waterfall,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

# 10 real Australian businesses for testing
TEST_BUSINESSES = [
    {
        "company_name": "Atlassian",
        "abn": "53 102 443 916",
        "state": "NSW",
        "expected_found": True,
    },
    {
        "company_name": "Canva",
        "abn": "40 158 929 938",
        "state": "NSW",
        "expected_found": True,
    },
    {
        "company_name": "REA Group",
        "abn": "54 068 349 066",
        "state": "VIC",
        "expected_found": True,
    },
    {
        "company_name": "Xero Australia",
        "abn": "73 127 184 442",
        "state": "VIC",
        "expected_found": True,
    },
    {
        "company_name": "Culture Amp",
        "abn": "89 146 676 815",
        "state": "VIC",
        "expected_found": True,
    },
    {
        "company_name": "SafetyCulture",
        "abn": "36 159 206 116",
        "state": "QLD",
        "expected_found": True,
    },
    {
        "company_name": "Employment Hero",
        "abn": "11 160 047 832",
        "state": "NSW",
        "expected_found": True,
    },
    {
        "company_name": "Deputy",
        "abn": "84 633 465 810",
        "state": "NSW",
        "expected_found": True,
    },
    {
        "company_name": "Envato",
        "abn": "11 119 159 741",
        "state": "VIC",
        "expected_found": True,
    },
    {
        "company_name": "Campaign Monitor",
        "abn": "74 142 145 602",
        "state": "NSW",
        "expected_found": True,
    },
]


async def enrich_single_business(
    waterfall: SiegeWaterfall,
    business: dict,
) -> dict:
    """Enrich a single business through Tiers 1-3.

    Note: Renamed from test_single_business to avoid pytest collection.
    This is a script helper, not a pytest test.
    """
    logger.info(f"\n{'='*60}")
    logger.info(f"Testing: {business['company_name']} (ABN: {business.get('abn', 'N/A')})")
    logger.info(f"{'='*60}")

    try:
        result = await waterfall.enrich_lead(
            lead=business,
            skip_tiers=[EnrichmentTier.PROXYCURL, EnrichmentTier.IDENTITY],
        )

        # Extract tier results
        tier_summary = {}
        for tr in result.tier_results:
            tier_summary[tr.tier.value] = {
                "success": tr.success,
                "skipped": tr.skipped,
                "error": tr.error,
                "cost_aud": tr.cost_aud,
            }

        # Success = at least one tier succeeded
        any_tier_success = any(tr.success for tr in result.tier_results)

        return {
            "company_name": business["company_name"],
            "success": any_tier_success,
            "total_cost_aud": result.total_cost_aud,
            "tier_summary": tier_summary,
            "data_fields": list(result.enriched_data.keys()) if result.enriched_data else [],
            "error": None,
        }

    except Exception as e:
        logger.error(f"Error testing {business['company_name']}: {e}")
        return {
            "company_name": business["company_name"],
            "success": False,
            "total_cost_aud": 0,
            "tier_summary": {},
            "data_fields": [],
            "error": str(e),
        }


async def run_tests():
    """Run all tests and report results."""
    logger.info("=" * 60)
    logger.info("SIEGE WATERFALL TIERS 1-3 TEST")
    logger.info("Target: $0.05/lead discovery cost")
    logger.info("=" * 60)

    # Get waterfall instance
    waterfall = get_siege_waterfall()

    results = []
    for business in TEST_BUSINESSES:
        result = await enrich_single_business(waterfall, business)
        results.append(result)

    # Calculate stats
    total_tested = len(results)
    tier1_success = sum(1 for r in results if r["tier_summary"].get("tier1_abn", {}).get("success"))
    tier2_success = sum(1 for r in results if r["tier_summary"].get("tier2_gmb", {}).get("success"))
    tier3_success = sum(1 for r in results if r["tier_summary"].get("tier3_hunter", {}).get("success"))
    total_cost = sum(r["total_cost_aud"] for r in results)
    avg_cost = total_cost / total_tested if total_tested > 0 else 0

    # Print summary
    logger.info("\n" + "=" * 60)
    logger.info("RESULTS SUMMARY")
    logger.info("=" * 60)

    print(f"\n{'Business':<30} {'Tier1':<8} {'Tier2':<8} {'Tier3':<8} {'Cost':<10}")
    print("-" * 70)

    for r in results:
        t1 = "✅" if r["tier_summary"].get("tier1_abn", {}).get("success") else "❌"
        t2 = "✅" if r["tier_summary"].get("tier2_gmb", {}).get("success") else "❌"
        t3 = "✅" if r["tier_summary"].get("tier3_hunter", {}).get("success") else "❌"
        cost = f"${r['total_cost_aud']:.3f}"
        print(f"{r['company_name']:<30} {t1:<8} {t2:<8} {t3:<8} {cost:<10}")

    print("-" * 70)
    print("\n📊 TIER SUCCESS RATES:")
    print(f"   Tier 1 (ABN):    {tier1_success}/{total_tested} ({tier1_success/total_tested*100:.0f}%)")
    print(f"   Tier 2 (GMB):    {tier2_success}/{total_tested} ({tier2_success/total_tested*100:.0f}%)")
    print(f"   Tier 3 (Hunter): {tier3_success}/{total_tested} ({tier3_success/total_tested*100:.0f}%)")

    print("\n💰 COST ANALYSIS:")
    print(f"   Total cost: ${total_cost:.3f} AUD")
    print(f"   Avg per lead: ${avg_cost:.4f} AUD")
    print("   Target: $0.05/lead")
    print(f"   Status: {'✅ UNDER BUDGET' if avg_cost <= 0.05 else '⚠️ OVER BUDGET'}")

    # Return results for further analysis
    return {
        "total_tested": total_tested,
        "tier1_success_rate": tier1_success / total_tested,
        "tier2_success_rate": tier2_success / total_tested,
        "tier3_success_rate": tier3_success / total_tested,
        "total_cost_aud": total_cost,
        "avg_cost_per_lead": avg_cost,
        "under_budget": avg_cost <= 0.05,
        "results": results,
    }


if __name__ == "__main__":
    result = asyncio.run(run_tests())

    # Save results to file
    output_path = Path(__file__).parent / "tier_test_results.json"
    with open(output_path, "w") as f:
        json.dump(result, f, indent=2, default=str)

    print(f"\n📁 Results saved to: {output_path}")

    # Exit code based on success
    sys.exit(0 if result["under_budget"] else 1)
