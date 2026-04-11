"""
Script: scripts/317_live_validation.py
Purpose: Live v7 pipeline validation run — Directive #317 Task C
Directive: #317

DO NOT RUN without explicit CEO approval.
Estimated cost: see COST_ESTIMATE below.

Usage (after approval):
    python scripts/317_live_validation.py --domains 10 --dry-run
    python scripts/317_live_validation.py --domains 10

Flags:
    --dry-run       Skip paid API layers (ContactOut, Leadmagic) — free layers only
    --domains N     Number of domains to process (default: 10, max: 50 for validation)
    --category STR  GMB category (default: "dentist")
    --location STR  Location slug (default: "sydney-nsw")
    --output PATH   JSON output file (default: scripts/output/317_validation.json)
"""
from __future__ import annotations

import argparse
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

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("317_validation")

# ── COST ESTIMATE ─────────────────────────────────────────────────────────────
# Per domain (worst-case — all layers triggered):
#   DFS discovery:      $0.001 USD × N domains     = ~$0.010 per 10 domains
#   Bright Data scrape: $0.004 USD × N domains     = ~$0.040 per 10 domains
#   DFS DM enrichment:  $0.0465 USD × N domains    = ~$0.465 per 10 domains
#   BD LinkedIn DM:     $0.0015 USD × N domains    = ~$0.015 per 10 domains
#   ContactOut:         ~$0.03 USD × N DMs found   = ~$0.300 per 10 DMs
#   Leadmagic email:    $0.015 USD × fallback only = ~$0.075 per 5 fallbacks
#   Leadmagic mobile:   $0.077 USD (rarely — ContactOut covers AU)
#
# Per 10 domains: ~$0.90 USD = ~$1.40 AUD
# Per 50 domains: ~$4.50 USD = ~$7.00 AUD
# Per 250 domains (full run): ~$22.50 USD = ~$34.90 AUD

COST_ESTIMATE_PER_10 = {"usd": 0.90, "aud": 1.40}
COST_ESTIMATE_PER_50 = {"usd": 4.50, "aud": 7.00}
COST_ESTIMATE_PER_250 = {"usd": 22.50, "aud": 34.90}


async def run_validation(
    domains: int = 10,
    dry_run: bool = False,
    category: str = "dentist",
    location: str = "sydney-nsw",
    output_path: str = "scripts/output/317_validation.json",
) -> dict:
    """Run the live v7 pipeline validation and return results."""

    logger.info("=== Directive #317 — Live v7 Validation Run ===")
    logger.info("domains=%d dry_run=%s category=%s location=%s", domains, dry_run, category, location)

    if not dry_run:
        approx_aud = (domains / 10) * COST_ESTIMATE_PER_10["aud"]
        co_credits = domains  # worst-case: 1 credit per domain
        logger.warning(
            "LIVE RUN — estimated cost: ~$%.2f AUD, ~%d ContactOut credits",
            approx_aud, co_credits,
        )

    start = time.time()

    # ── Environment check ─────────────────────────────────────────────────────
    env_file = Path("/home/elliotbot/.config/agency-os/.env")
    if env_file.exists():
        from dotenv import load_dotenv
        load_dotenv(env_file)
        logger.info("Loaded env from %s", env_file)
    else:
        logger.warning("Env file not found at %s — relying on process env", env_file)

    # Check ContactOut key
    co_key = os.getenv("CONTACTOUT_API_KEY", "")
    logger.info(
        "ContactOut configured: %s (key=%s...)",
        bool(co_key),
        co_key[:8] if co_key else "none",
    )

    # ── Pipeline run ──────────────────────────────────────────────────────────
    results: list[dict] = []
    errors: list[dict] = []

    if dry_run:
        logger.info("DRY RUN — skipping paid API calls")
        # In dry-run: verify imports only
        try:
            from src.pipeline.contactout_enricher import enrich_dm_via_contactout
            from src.pipeline.email_waterfall import discover_email
            from src.pipeline.mobile_waterfall import run_mobile_waterfall
            from src.pipeline.pipeline_orchestrator import PipelineOrchestrator
            logger.info("All imports OK")
        except ImportError as e:
            logger.error("Import failed: %s", e)
            errors.append({"type": "import_error", "error": str(e)})
    else:
        # Full live run via PipelineOrchestrator
        try:
            from src.pipeline.pipeline_orchestrator import PipelineOrchestrator, PipelineConfig

            config = PipelineConfig(
                category=category,
                location=location,
                target_count=domains,
            )

            cards_received: list = []

            async def on_card(card):
                cards_received.append(card)
                logger.info(
                    "card: domain=%s dm=%s email=%s(%s) mobile=%s",
                    card.domain,
                    card.dm_name,
                    card.dm_email,
                    card.dm_email_source,
                    card.dm_mobile,
                )

            orchestrator = PipelineOrchestrator(config=config, on_prospect_found=on_card)
            pipeline_result = await orchestrator.run()

            for card in pipeline_result.prospects:
                results.append({
                    "domain": card.domain,
                    "company_name": card.company_name,
                    "dm_name": card.dm_name,
                    "dm_email": card.dm_email,
                    "dm_email_source": card.dm_email_source,
                    "dm_email_confidence": card.dm_email_confidence,
                    "dm_email_verified": card.dm_email_verified,
                    "dm_mobile": card.dm_mobile,
                    "dm_mobile_source": card.dm_mobile_source,
                    "dm_mobile_tier": card.dm_mobile_tier,
                    "intent_score": card.intent_score,
                    "affordability_score": card.affordability_score,
                })

            stats = pipeline_result.stats
            logger.info(
                "Pipeline stats: discovered=%s dm_found=%s unreachable=%s",
                getattr(stats, "discovered", "?"),
                getattr(stats, "dm_found", "?"),
                getattr(stats, "unreachable", "?"),
            )
        except Exception as exc:
            logger.error("Pipeline run failed: %s", exc, exc_info=True)
            errors.append({"type": "pipeline_error", "error": str(exc)})

    elapsed = time.time() - start

    # ── Metrics ───────────────────────────────────────────────────────────────
    contactout_hits = sum(
        1 for r in results if r.get("dm_email_source") == "contactout"
    )
    mobile_hits = sum(
        1 for r in results if r.get("dm_mobile_source") == "contactout"
    )

    summary = {
        "run_at": datetime.utcnow().isoformat(),
        "dry_run": dry_run,
        "category": category,
        "location": location,
        "target_domains": domains,
        "prospects_built": len(results),
        "errors": len(errors),
        "elapsed_secs": round(elapsed, 1),
        "contactout_email_hits": contactout_hits,
        "contactout_mobile_hits": mobile_hits,
        "email_source_breakdown": {},
        "mobile_source_breakdown": {},
        "results": results,
        "errors_detail": errors,
    }

    for r in results:
        es = r.get("dm_email_source") or "none"
        ms = r.get("dm_mobile_source") or "none"
        summary["email_source_breakdown"][es] = summary["email_source_breakdown"].get(es, 0) + 1
        summary["mobile_source_breakdown"][ms] = summary["mobile_source_breakdown"].get(ms, 0) + 1

    # ── Write output ──────────────────────────────────────────────────────────
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(summary, indent=2))
    logger.info("Results written to %s", out)

    # ── Print summary table ───────────────────────────────────────────────────
    print("\n=== VALIDATION SUMMARY ===")
    print(f"Prospects built:          {summary['prospects_built']}")
    print(f"ContactOut email hits:    {summary['contactout_email_hits']}")
    print(f"ContactOut mobile hits:   {summary['contactout_mobile_hits']}")
    print(f"Email source breakdown:   {summary['email_source_breakdown']}")
    print(f"Mobile source breakdown:  {summary['mobile_source_breakdown']}")
    print(f"Elapsed:                  {summary['elapsed_secs']}s")
    print(f"Errors:                   {summary['errors']}")
    print(f"Output:                   {out}")

    return summary


def main():
    parser = argparse.ArgumentParser(description="Directive #317 live v7 validation run")
    parser.add_argument("--domains", type=int, default=10, help="Number of domains to process")
    parser.add_argument("--dry-run", action="store_true", help="Skip paid API calls (import check only)")
    parser.add_argument("--category", default="dentist", help="GMB category")
    parser.add_argument("--location", default="sydney-nsw", help="Location slug")
    parser.add_argument(
        "--output",
        default="scripts/output/317_validation.json",
        help="Output JSON path",
    )
    args = parser.parse_args()

    asyncio.run(
        run_validation(
            domains=args.domains,
            dry_run=args.dry_run,
            category=args.category,
            location=args.location,
            output_path=args.output,
        )
    )


if __name__ == "__main__":
    main()
