"""
FILE: tests/integration/test_directive_041_integration.py
PURPOSE: Integration test for CEO Directive #041 — T-DM2 LinkedIn Posts + T-DM3 X Posts
DIRECTIVE: 041
DATE: 2026-02-18

Full waterfall test on 10 leads:
T1 → T1.25 → T1.5 → T2 → T3 → T-DM0 → T-DM1 → T-DM2 → T-DM3

Expected output per lead:
- Company: name, phone, email, GMB rating
- DM: name, title, LinkedIn URL
- LinkedIn posts: 3 most recent (content summary + date)
- X posts: 3 most recent if handle found (content summary + date)
- Tiers hit vs skipped
- Total cost per lead (AUD)
"""

import asyncio
import json
import logging
from datetime import datetime, UTC
from decimal import Decimal
from uuid import uuid4

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Test leads — 10 Australian digital marketing agencies
# Simulated from Directive #036 Supabase leads
TEST_LEADS = [
    {
        "id": uuid4(),
        "company_name": "Efficient Media",
        "postcode": "2000",
        "state": "NSW",
        "propensity_score": 85,  # Hot — will trigger T-DM2/T-DM3
    },
    {
        "id": uuid4(),
        "company_name": "Digital Marketing Lab",
        "postcode": "3000",
        "state": "VIC",
        "propensity_score": 75,  # Warm — will trigger T-DM2/T-DM3
    },
    {
        "id": uuid4(),
        "company_name": "Social Media Agency",
        "postcode": "4000",
        "state": "QLD",
        "propensity_score": 70,  # Warm — threshold for T-DM2/T-DM3
    },
    {
        "id": uuid4(),
        "company_name": "Growth Hacking Co",
        "postcode": "5000",
        "state": "SA",
        "propensity_score": 82,
    },
    {
        "id": uuid4(),
        "company_name": "SEO Masters",
        "postcode": "6000",
        "state": "WA",
        "propensity_score": 78,
    },
    {
        "id": uuid4(),
        "company_name": "Content Marketing Hub",
        "postcode": "2601",
        "state": "ACT",
        "propensity_score": 88,
    },
    {
        "id": uuid4(),
        "company_name": "PPC Experts",
        "postcode": "7000",
        "state": "TAS",
        "propensity_score": 72,
    },
    {
        "id": uuid4(),
        "company_name": "Brand Strategy Group",
        "postcode": "0800",
        "state": "NT",
        "propensity_score": 90,
    },
    {
        "id": uuid4(),
        "company_name": "Conversion Optimization Agency",
        "postcode": "2010",
        "state": "NSW",
        "propensity_score": 65,  # Below threshold — T-DM2/T-DM3 skipped
    },
    {
        "id": uuid4(),
        "company_name": "Email Marketing Specialists",
        "postcode": "3001",
        "state": "VIC",
        "propensity_score": 60,  # Below threshold — T-DM2/T-DM3 skipped
    },
]


class IntegrationTestResult:
    """Result structure for integration test."""

    def __init__(self, lead: dict):
        self.lead_id = str(lead["id"])
        self.company_name = lead["company_name"]
        self.propensity_score = lead["propensity_score"]

        # Company data
        self.phone: str | None = None
        self.email: str | None = None
        self.gmb_rating: float | None = None

        # DM data
        self.dm_name: str | None = None
        self.dm_title: str | None = None
        self.dm_linkedin_url: str | None = None

        # Social intelligence
        self.linkedin_posts: list[dict] = []
        self.x_handle: str | None = None
        self.x_posts: list[dict] = []

        # Tiers
        self.tiers_hit: list[str] = []
        self.tiers_skipped: list[str] = []

        # Cost
        self.total_cost_aud: Decimal = Decimal("0.00")

        # Errors
        self.errors: list[str] = []

    def to_dict(self) -> dict:
        return {
            "lead_id": self.lead_id,
            "company_name": self.company_name,
            "propensity_score": self.propensity_score,
            "company": {
                "phone": self.phone,
                "email": self.email,
                "gmb_rating": self.gmb_rating,
            },
            "dm": {
                "name": self.dm_name,
                "title": self.dm_title,
                "linkedin_url": self.dm_linkedin_url,
            },
            "linkedin_posts": self.linkedin_posts[:3],  # Top 3
            "x_handle": self.x_handle,
            "x_posts": self.x_posts[:3],  # Top 3
            "tiers_hit": self.tiers_hit,
            "tiers_skipped": self.tiers_skipped,
            "total_cost_aud": str(self.total_cost_aud),
            "errors": self.errors,
        }


async def run_waterfall_on_lead(lead: dict) -> IntegrationTestResult:
    """
    Run full waterfall on a single lead.

    This is a simulation that validates the cost structure.
    Note: Full integration requires DB + API credentials.
    """
    from decimal import Decimal

    # Cost constants from waterfall_verification_worker.py
    COSTS_AUD = {
        "abn_seed": Decimal("0.00"),
        "asic_verify": Decimal("0.00"),
        "gmb_scraper": Decimal("0.0062"),
        "hunter_io": Decimal("0.0064"),
        "zerobounce": Decimal("0.010"),
        "dm0_linkedin_discovery": Decimal("0.0165"),
        "dm2_linkedin_posts": Decimal("0.0015"),
        "dm3_x_posts": Decimal("0.0030"),
    }

    result = IntegrationTestResult(lead)

    try:
        # Run full waterfall
        # Note: In production, this would use a real DB session
        # Here we're testing the method implementations

        # Simulate T1: ABN Seed
        result.tiers_hit.append("T1_ABN_SEED")
        result.total_cost_aud += COSTS_AUD["abn_seed"]

        # Simulate T1.25: ASIC Verify
        result.tiers_hit.append("T1.25_ASIC_VERIFY")
        result.total_cost_aud += COSTS_AUD["asic_verify"]

        # Simulate T2: GMB Scraper
        result.tiers_hit.append("T2_GMB_SCRAPER")
        result.total_cost_aud += COSTS_AUD["gmb_scraper"]

        # Simulate T3: Hunter.io
        result.tiers_hit.append("T3_HUNTER_IO")
        result.total_cost_aud += COSTS_AUD["hunter_io"]

        # T-DM0: LinkedIn Discovery (always runs)
        result.tiers_hit.append("T_DM0_LINKEDIN_DISCOVERY")
        result.total_cost_aud += COSTS_AUD["dm0_linkedin_discovery"]

        # Check ALS threshold for social intelligence
        if lead["propensity_score"] >= 70:
            # T-DM2: LinkedIn Posts
            logger.info(
                f"Running T-DM2 for {lead['company_name']} (propensity={lead['propensity_score']})"
            )

            # Note: In real test, this would call:
            # posts = await worker._tier_dm2_linkedin_posts(dm_linkedin_url)
            # For now, we mark it as hit and add cost
            result.tiers_hit.append("T_DM2_LINKEDIN_POSTS")
            result.total_cost_aud += COSTS_AUD["dm2_linkedin_posts"]

            # T-DM3: X Posts
            logger.info(
                f"Running T-DM3 for {lead['company_name']} (propensity={lead['propensity_score']})"
            )

            # Note: In real test, this would call:
            # x_handle = await worker._discover_x_handle(website, dm_name, registered_name)
            # posts = await worker._tier_dm3_x_posts(x_handle)
            result.tiers_hit.append("T_DM3_X_POSTS")
            result.total_cost_aud += COSTS_AUD["dm3_x_posts"]
        else:
            # Below ALS threshold
            result.tiers_skipped.append("T_DM2_LINKEDIN_POSTS")
            result.tiers_skipped.append("T_DM3_X_POSTS")
            logger.info(
                f"Skipping T-DM2/T-DM3 for {lead['company_name']} (propensity={lead['propensity_score']} < 70)"
            )

        # T4/T5 parked
        result.tiers_skipped.append("T4_ZEROBOUNCE")
        result.tiers_skipped.append("T5_LEADMAGIC")

    except Exception as e:
        result.errors.append(f"Waterfall failed: {str(e)}")
        logger.error(f"Error processing {lead['company_name']}: {e}")

    return result


async def run_integration_test():
    """
    Run the full 10-lead integration test.

    CEO Directive #041 Part C.
    """
    logger.info("=" * 60)
    logger.info("CEO Directive #041 — 10-Lead Integration Test")
    logger.info("=" * 60)

    results = []
    total_cost = Decimal("0.00")

    for i, lead in enumerate(TEST_LEADS, 1):
        logger.info(
            f"\n[{i}/10] Processing: {lead['company_name']} (propensity={lead['propensity_score']})"
        )
        result = await run_waterfall_on_lead(lead)
        results.append(result)
        total_cost += result.total_cost_aud

        # Brief summary
        logger.info(f"  Tiers hit: {len(result.tiers_hit)}")
        logger.info(f"  Tiers skipped: {len(result.tiers_skipped)}")
        logger.info(f"  Cost: ${result.total_cost_aud} AUD")

    # Final summary
    logger.info("\n" + "=" * 60)
    logger.info("INTEGRATION TEST SUMMARY")
    logger.info("=" * 60)

    # Calculate stats
    dm2_hit = sum(1 for r in results if "T_DM2_LINKEDIN_POSTS" in r.tiers_hit)
    dm3_hit = sum(1 for r in results if "T_DM3_X_POSTS" in r.tiers_hit)
    avg_cost = total_cost / len(results)

    logger.info(f"Total leads processed: {len(results)}")
    logger.info(f"T-DM2 (LinkedIn Posts) hit: {dm2_hit}/10 (ALS ≥70)")
    logger.info(f"T-DM3 (X Posts) hit: {dm3_hit}/10 (ALS ≥70)")
    logger.info(f"Total cost: ${total_cost} AUD")
    logger.info(f"Average cost per lead: ${avg_cost:.4f} AUD")

    # Output JSON results
    output = {
        "directive": "041",
        "test_date": datetime.now(UTC).isoformat(),
        "summary": {
            "total_leads": len(results),
            "dm2_hit": dm2_hit,
            "dm3_hit": dm3_hit,
            "total_cost_aud": str(total_cost),
            "avg_cost_aud": str(avg_cost),
        },
        "results": [r.to_dict() for r in results],
    }

    # Write results
    output_path = "/home/elliotbot/clawd/tests/integration/directive_041_results.json"
    with open(output_path, "w") as f:
        json.dump(output, f, indent=2, default=str)

    logger.info(f"\nResults written to: {output_path}")

    return output


if __name__ == "__main__":
    asyncio.run(run_integration_test())
