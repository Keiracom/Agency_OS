"""Stage 9+10 subset runner — social signals + VR/outreach for BU rows missing outreach_messages.

Usage:  python scripts/stage_subset_runner.py [--dry-run]
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import subprocess
import sys

import asyncpg

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from src.integrations.bright_data_client import BrightDataClient
from src.intelligence.enhanced_vr import run_stage10_vr_and_messaging
from src.intelligence.stage9_social import run_stage9_social

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

STAGE9_COST = 0.027  # USD per domain
STAGE10_COST = 0.001  # USD per domain (Gemini is cheap)
BUDGET_CAP_USD = 0.50

QUERY = """
SELECT id, domain, dm_name, dm_email, propensity_score,
       signal_checked_at, stage_metrics
FROM business_universe
WHERE dm_name IS NOT NULL AND dm_email IS NOT NULL AND propensity_score > 0
  AND dm_email LIKE '%@%.%' AND dm_email NOT LIKE '%.webp'
  AND (outreach_messages IS NULL OR LENGTH(outreach_messages::text) < 10)
ORDER BY propensity_score DESC
"""


def _tg(msg: str) -> None:
    try:
        subprocess.run(["tg", "-g", msg], timeout=10, check=False)
    except Exception as exc:
        logger.warning("tg send failed: %s", exc)


async def _process_one(
    row: dict, bd: BrightDataClient, dry_run: bool, cost: list[float], conn: asyncpg.Connection
) -> None:
    domain = row["domain"]
    needs_s9 = row["signal_checked_at"] is None
    projected = cost[0] + (STAGE9_COST if needs_s9 else 0) + STAGE10_COST

    if projected > BUDGET_CAP_USD:
        logger.warning(
            "BUDGET CAP: skipping %s (projected $%.3f > cap $%.2f)",
            domain,
            projected,
            BUDGET_CAP_USD,
        )
        return

    sm = row["stage_metrics"] or {}
    stage9_data: dict = sm.get("stage9") or {}

    # Stage 9 — social signals (only if signal_checked_at is NULL)
    if needs_s9:
        logger.info("[%s] Stage 9 — social signals", domain)
        # LinkedIn URLs live in stage_metrics (stage8_contacts / stage2)
        dm_li = ((sm.get("stage8_contacts") or {}).get("linkedin", {}) or {}).get("linkedin_url")
        company_li = (sm.get("stage2") or {}).get("serp_company_linkedin")
        if not dry_run:
            stage9_data = await run_stage9_social(
                bd=bd,
                dm_linkedin_url=dm_li,
                company_linkedin_url=company_li,
                dm_name=row.get("dm_name"),
            )
            await conn.execute(
                "UPDATE business_universe SET stage_metrics = COALESCE(stage_metrics,'{}'::"
                "jsonb) || $1::jsonb, signal_checked_at = NOW(), updated_at = NOW() WHERE id = $2",
                json.dumps({"stage9": stage9_data}),
                row["id"],
            )
        else:
            logger.info("[%s] DRY-RUN: would run Stage 9", domain)
        cost[0] += STAGE9_COST

    # Stage 10 — VR + outreach messaging
    logger.info("[%s] Stage 10 — VR+messaging", domain)
    stage3 = sm.get("stage3") or {"dm_candidate": {"name": row.get("dm_name")}}
    stage8 = sm.get("stage8_contacts") or {"email": {"email": row.get("dm_email")}}

    if not dry_run:
        result = await run_stage10_vr_and_messaging(
            stage3_identity=stage3,
            stage4_signals=sm.get("stage4") or {},
            stage5_scores=sm.get("stage5") or {"propensity_score": row.get("propensity_score", 0)},
            stage7_analyse=sm.get("stage7") or {},
            stage8_contacts=stage8,
            stage9_social=stage9_data,
        )
        cost[0] += result.get("cost_usd", STAGE10_COST)
        await conn.execute(
            """UPDATE business_universe SET
               outreach_messages = $1::jsonb, pipeline_stage = 10,
               pipeline_updated_at = NOW(), updated_at = NOW()
               WHERE id = $2""",
            json.dumps(result.get("outreach") or {}),
            row["id"],
        )
        logger.info("[%s] written — cumulative cost $%.4f USD", domain, cost[0])
    else:
        cost[0] += STAGE10_COST
        logger.info("[%s] DRY-RUN: would write outreach_messages", domain)


async def main(dry_run: bool) -> None:
    db_url = os.environ.get("DATABASE_URL", "").replace("postgresql+asyncpg://", "postgresql://")
    if not db_url:
        logger.error("DATABASE_URL not set")
        sys.exit(1)

    bd = BrightDataClient(api_key=os.environ.get("BRIGHTDATA_API_KEY", ""))
    conn = await asyncpg.connect(db_url, statement_cache_size=0)
    try:
        raw = await conn.fetch(QUERY)
        rows = []
        for r in raw:
            d = dict(r)
            if isinstance(d.get("stage_metrics"), str):
                d["stage_metrics"] = json.loads(d["stage_metrics"])
            rows.append(d)
        logger.info("Prospects matching filter: %d", len(rows))
        if not rows:
            logger.info("Nothing to process.")
            return

        cost: list[float] = [0.0]
        processed = 0
        for row in rows:
            if cost[0] >= BUDGET_CAP_USD:
                logger.warning(
                    "BUDGET CAP $%.2f reached — stopping after %d processed",
                    BUDGET_CAP_USD,
                    processed,
                )
                break
            await _process_one(row, bd, dry_run, cost, conn)
            processed += 1

        total_aud = cost[0] * 1.55
        summary = (
            f"stage_subset_runner: {processed} processed, "
            f"${cost[0]:.4f} USD (${total_aud:.4f} AUD){' [DRY-RUN]' if dry_run else ''}"
        )
        logger.info(summary)
        _tg(summary)
    finally:
        await conn.close()


if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Stage 9+10 subset runner")
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()
    asyncio.run(main(dry_run=args.dry_run))
