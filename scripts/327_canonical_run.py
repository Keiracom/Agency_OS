"""
Script: scripts/327_canonical_run.py
Directive: #327 — Canonical V7 + ContactOut Validation

Replicates Directive #300 (730→260 cards, $0.09/card) with ContactOut
wired as Layer 1 primary email and Layer 0 primary mobile.

Expected outcome: ~260 prospect cards, ~75% verified email,
~50% AU mobile, ~$25-30 USD total cost.

DO NOT modify parameters without explicit CEO directive.
These values are the proven Pipeline Provenance Ledger entries.

Categories: 10514 (dental), 10282 (construction), 10163 (legal)
Location: Australia (code 2036)
Cap: 500 per category (let categories exhaust naturally — #300 produced 730 raw)
ETV: 100-50,000 (next_batch path, NOT pull_batch's 200-5000)
Workers: 10 (Ignition default, NOT orchestrator default of 4)
ContactOut: enabled (Layer 1 email, Layer 0 mobile)

Usage (CEO approval required — this costs real money):
    python3 scripts/327_canonical_run.py --dry-run   # imports only, no API calls
    python3 scripts/327_canonical_run.py              # full live run (~$27 USD)

num_workers=10 is intentional. This is the proven Ignition tier value.
Do not change without explicit CEO directive. The orchestrator default
of 4 was identified as a bottleneck in the #323 forensic audit.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
import time
from datetime import datetime
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("327_canonical")

# ── CANONICAL PARAMETERS (Pipeline Provenance Ledger) ────────────────────────
# These are the proven #300 values. DO NOT modify without CEO directive.

CATEGORIES = [10514, 10282, 10163]  # dental, construction, legal
CATEGORY_NAMES = {
    10514: "Dentists & Dental Services",
    10282: "Building Construction & Maintenance",
    10163: "Legal",
}
LOCATION = "Australia"  # National — code 2036
CAP_PER_CATEGORY = 500  # Same as #300 — let categories exhaust naturally
ETV_MIN = 100.0  # next_batch path (NOT pull_batch's 200)
ETV_MAX = 50000.0  # next_batch path (NOT pull_batch's 5000)
NUM_WORKERS = 10  # Ignition default (NOT orchestrator default of 4)
USE_CONTACTOUT = True  # Layer 1 email + Layer 0 mobile

OUTPUT = os.path.join(os.path.dirname(__file__), "output", "327_canonical_run.json")

# Cost estimate: ~$27 USD = ~$42 AUD for ~730 domains through full pipeline
COST_ESTIMATE = {"usd": 27.0, "aud": 42.0}


async def run_canonical():
    """Run the canonical V7 + ContactOut validation."""
    start = time.time()

    # ── Environment ──────────────────────────────────────────────────────────
    env_file = Path("/home/elliotbot/.config/agency-os/.env")
    if env_file.exists():
        from dotenv import load_dotenv

        load_dotenv(env_file)
        logger.info("Loaded env from %s", env_file)

    co_key = os.getenv("CONTACTOUT_API_KEY", "")
    if USE_CONTACTOUT and not co_key:
        logger.error("CONTACTOUT_API_KEY not set — cannot run with use_contactout=True")
        sys.exit(1)

    logger.info("=== Directive #327 — Canonical V7 + ContactOut Validation ===")
    logger.info(
        "categories=%s cap=%d etv=%s-%s workers=%d contactout=%s",
        CATEGORIES,
        CAP_PER_CATEGORY,
        ETV_MIN,
        ETV_MAX,
        NUM_WORKERS,
        USE_CONTACTOUT,
    )
    logger.warning(
        "LIVE RUN — estimated cost: ~$%.0f USD (~$%.0f AUD)",
        COST_ESTIMATE["usd"],
        COST_ESTIMATE["aud"],
    )

    # ── Build dependencies ───────────────────────────────────────────────────
    from src.pipeline.pipeline_orchestrator import PipelineOrchestrator
    from src.pipeline.discovery import MultiCategoryDiscovery
    from src.pipeline.free_enrichment import FreeEnrichment
    from src.pipeline.prospect_scorer import ProspectScorer
    from src.pipeline.dm_identification import DMIdentification
    from src.integrations.dfs_labs_client import DFSLabsClient
    from src.integrations.bright_data_linkedin_client import BrightDataLinkedInClient
    from src.utils.asyncpg_connection import get_asyncpg_pool
    from src.config.settings import settings
    from src.pipeline import intelligence as _intelligence_module

    db_url = settings.database_url.replace("postgresql+asyncpg://", "postgresql://")
    pool = await get_asyncpg_pool(db_url, min_size=1, max_size=10)

    dfs_client = DFSLabsClient(
        login=os.getenv("DATAFORSEO_LOGIN", ""),
        password=os.getenv("DATAFORSEO_PASSWORD", ""),
    )
    bd_client = BrightDataLinkedInClient()

    discovery = MultiCategoryDiscovery(dfs_client)
    logger.info(
        "Discovery: %s (has next_batch: %s)",
        type(discovery).__name__,
        hasattr(discovery, "next_batch"),
    )

    free_enrichment = FreeEnrichment(conn=pool)
    scorer = ProspectScorer()
    dm_identification = DMIdentification(bd_client=bd_client, dfs_client=dfs_client)

    cards_received: list = []

    async def on_card(card):
        cards_received.append(card)
        logger.info(
            "CARD: domain=%s dm=%s email=%s(%s/%s) mobile=%s(%s)",
            card.domain,
            card.dm_name,
            card.dm_email,
            card.dm_email_source,
            card.dm_email_confidence,
            card.dm_mobile,
            getattr(card, "dm_mobile_source", "?"),
        )

    orchestrator = PipelineOrchestrator(
        discovery=discovery,
        free_enrichment=free_enrichment,
        scorer=scorer,
        dm_identification=dm_identification,
        gmb_client=dfs_client,
        intelligence=_intelligence_module,
        on_card=on_card,
    )

    # run_parallel with discover_all=True: paginated next_batch() walking.
    # num_workers=10 is the Ignition default — NOT the orchestrator default of 4.
    # target_count = 1500 max (500 × 3 categories), natural exhaustion expected ~730.
    pipeline_result = await orchestrator.run_parallel(
        category_codes=[str(c) for c in CATEGORIES],
        location=LOCATION,
        target_count=CAP_PER_CATEGORY * len(CATEGORIES),  # 1500 max, natural exhaustion
        num_workers=NUM_WORKERS,  # 10 — Ignition default, NOT orchestrator default of 4
        discover_all=True,
    )

    await pool.close()
    elapsed = time.time() - start

    # ── Output ───────────────────────────────────────────────────────────────
    results = []
    for card in pipeline_result.prospects:
        results.append(
            {
                "domain": card.domain,
                "company_name": card.company_name,
                "dm_name": card.dm_name,
                "dm_email": card.dm_email,
                "dm_email_source": card.dm_email_source,
                "dm_email_confidence": card.dm_email_confidence,
                "dm_email_verified": card.dm_email_verified,
                "dm_mobile": card.dm_mobile,
                "dm_mobile_source": getattr(card, "dm_mobile_source", None),
                "dm_mobile_tier": getattr(card, "dm_mobile_tier", None),
                "intent_score": card.intent_score,
                "affordability_score": card.affordability_score,
            }
        )

    # Attribution stats
    email_sources = {}
    mobile_sources = {}
    for r in results:
        src = r.get("dm_email_source", "none")
        email_sources[src] = email_sources.get(src, 0) + 1
        msrc = r.get("dm_mobile_source") or "none"
        mobile_sources[msrc] = mobile_sources.get(msrc, 0) + 1

    has_email = sum(1 for r in results if r["dm_email"])
    has_mobile = sum(1 for r in results if r["dm_mobile"])
    verified = sum(1 for r in results if r.get("dm_email_verified"))

    summary = {
        "directive": "#327 — Canonical V7 + ContactOut Validation",
        "run_date": datetime.utcnow().isoformat(),
        "elapsed_seconds": round(elapsed, 1),
        "parameters": {
            "categories": CATEGORIES,
            "cap_per_category": CAP_PER_CATEGORY,
            "etv_range": [ETV_MIN, ETV_MAX],
            "num_workers": NUM_WORKERS,
            "use_contactout": USE_CONTACTOUT,
        },
        "stats": getattr(pipeline_result, "stats", {}),
        "cards_total": len(results),
        "cards_with_email": has_email,
        "cards_with_verified_email": verified,
        "cards_with_mobile": has_mobile,
        "email_pct": round(has_email / len(results) * 100, 1) if results else 0,
        "verified_pct": round(verified / len(results) * 100, 1) if results else 0,
        "mobile_pct": round(has_mobile / len(results) * 100, 1) if results else 0,
        "email_source_attribution": email_sources,
        "mobile_source_attribution": mobile_sources,
        "comparison_to_300": {
            "300_cards": 260,
            "300_email_pct": 12,
            "300_mobile_pct": 0,
            "327_cards": len(results),
            "327_email_pct": round(has_email / len(results) * 100, 1) if results else 0,
            "327_mobile_pct": round(has_mobile / len(results) * 100, 1) if results else 0,
        },
        "prospects": results,
    }

    os.makedirs(os.path.dirname(OUTPUT), exist_ok=True)
    with open(OUTPUT, "w") as f:
        json.dump(summary, f, indent=2, default=str)

    logger.info("=== #327 COMPLETE ===")
    logger.info(
        "Cards: %d | Email: %d (%.1f%%) | Verified: %d (%.1f%%) | Mobile: %d (%.1f%%)",
        len(results),
        has_email,
        has_email / len(results) * 100 if results else 0,
        verified,
        verified / len(results) * 100 if results else 0,
        has_mobile,
        has_mobile / len(results) * 100 if results else 0,
    )
    logger.info("Email sources: %s", email_sources)
    logger.info("Mobile sources: %s", mobile_sources)
    logger.info("Elapsed: %.1fs | Output: %s", elapsed, OUTPUT)

    return summary


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Directive #327 — Canonical V7 + ContactOut Validation"
    )
    parser.add_argument("--dry-run", action="store_true", help="Verify imports only, no API calls")
    args = parser.parse_args()

    if args.dry_run:
        logger.info("DRY RUN — verifying imports only")
        try:
            from src.pipeline.pipeline_orchestrator import PipelineOrchestrator
            from src.pipeline.discovery import MultiCategoryDiscovery
            from src.pipeline.contactout_enricher import enrich_dm_via_contactout
            from src.pipeline.email_waterfall import discover_email, GLOBAL_SEM_LEADMAGIC
            from src.pipeline.mobile_waterfall import run_mobile_waterfall

            logger.info("All imports OK")
            logger.info("PipelineOrchestrator: %s", PipelineOrchestrator)
            logger.info(
                "MultiCategoryDiscovery has next_batch: %s",
                hasattr(MultiCategoryDiscovery, "next_batch"),
            )
            logger.info("GLOBAL_SEM_LEADMAGIC value: %d", GLOBAL_SEM_LEADMAGIC._value)
        except ImportError as e:
            logger.error("Import failed: %s", e)
            sys.exit(1)
        return

    asyncio.run(run_canonical())


if __name__ == "__main__":
    main()
