"""
Directive #253 Task C — Stages 4-7 live pipeline test.
Runs against dentist cohort (propensity >= 40) already in BU at stage=3.
"""
import asyncio
import json
import logging
import time
from decimal import Decimal
from uuid import UUID

import asyncpg

from src.config.settings import get_settings
from src.clients.dfs_serp_client import DFSSerpClient
from src.integrations.leadmagic import LeadmagicClient
from src.integrations.anthropic import AnthropicClient
from src.pipeline.stage4_dm_identification import Stage4DMIdentification
from src.pipeline.stage5_email_enrichment import Stage5EmailEnrichment
from src.pipeline.stage6_reachability import Stage6Reachability
from src.pipeline.campaign_claimer import CampaignClaimer
from src.pipeline.stage7_personalisation import Stage7Personalisation

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

# Model redirect: claude-3-5-haiku-20241022 not available on this API key.
# Redirect to claude-haiku-4-5-20251001 (confirmed available).
# This subclass lives in the runner only — no pipeline source files are modified.
HAIKU_REDIRECT = {
    "claude-3-5-haiku-20241022": "claude-haiku-4-5-20251001",
}


import re as _re


class HaikuCompatClient(AnthropicClient):
    """
    Thin wrapper to:
    1. Redirect deprecated Haiku model name (claude-3-5-haiku-20241022 → claude-haiku-4-5-20251001)
    2. Strip markdown code fences from JSON responses (new Haiku wraps JSON in ```json...``` despite instructions)
    No pipeline source files are modified.
    """

    @staticmethod
    def _strip_markdown_json(text: str) -> str:
        """Strip ```json ... ``` or ``` ... ``` fences from model output."""
        text = text.strip()
        # Match ```json\n...\n``` or ```\n...\n```
        m = _re.match(r'^```(?:json)?\s*\n(.*?)\n```\s*$', text, _re.DOTALL)
        if m:
            return m.group(1).strip()
        return text

    async def complete(self, prompt, system=None, max_tokens=1024, temperature=0.7,
                       model="claude-3-5-haiku-20241022", enable_caching=True, **kwargs):
        model = HAIKU_REDIRECT.get(model, model)
        result = await super().complete(
            prompt=prompt, system=system, max_tokens=max_tokens,
            temperature=temperature, model=model, enable_caching=enable_caching, **kwargs,
        )
        # Strip markdown code fences so json.loads() in Stage7 can parse the response
        if isinstance(result.get("content"), str):
            result["content"] = self._strip_markdown_json(result["content"])
        return result


CLIENT_ID = UUID("79113059-5b71-4f79-a321-d2ba326598bc")
CAMPAIGN_ID = UUID("4c894b10-fa19-48c9-b2c6-87941f6870e5")

# Spend caps
STAGE4_SPEND_CAP = 3.0
STAGE5_SPEND_CAP = 5.0
STAGE6_SPEND_CAP = 2.0


async def run_test():
    settings = get_settings()
    db_url = settings.database_url.replace("postgresql+asyncpg://", "postgresql://")
    db_pool = await asyncpg.create_pool(db_url, min_size=2, max_size=5, statement_cache_size=0)

    log.info("=" * 60)
    log.info("DIRECTIVE #253 TASK C — STAGES 4-7 LIVE TEST")
    log.info(f"CAMPAIGN_ID: {CAMPAIGN_ID}")
    log.info(f"CLIENT_ID: {CLIENT_ID}")
    log.info("=" * 60)

    # Init clients
    serp_client = DFSSerpClient(
        login=settings.dataforseo_login,
        password=settings.dataforseo_password,
    )
    leadmagic = LeadmagicClient()
    anthropic = HaikuCompatClient()

    # --- STAGE 4 ---
    log.info("=== STAGE 4: DM IDENTIFICATION ===")
    t4 = time.time()
    stage4 = Stage4DMIdentification(serp_client, db_pool)
    s4_result = await stage4.run(batch_size=100, daily_spend_cap_aud=STAGE4_SPEND_CAP)
    log.info(f"Stage 4 complete in {time.time()-t4:.1f}s: {json.dumps(s4_result, default=str)}")

    # checkpoint
    s4_check = await db_pool.fetch("SELECT pipeline_stage, COUNT(*) as n FROM business_universe WHERE pipeline_stage >= 4 GROUP BY pipeline_stage ORDER BY pipeline_stage")
    log.info(f"CHECKPOINT [After Stage 4]: {[dict(r) for r in s4_check]}")

    # --- STAGE 5 ---
    log.info("=== STAGE 5: EMAIL ENRICHMENT ===")
    t5 = time.time()
    stage5 = Stage5EmailEnrichment(leadmagic, db_pool)
    s5_result = await stage5.run(batch_size=100, daily_spend_cap_aud=STAGE5_SPEND_CAP)
    log.info(f"Stage 5 complete in {time.time()-t5:.1f}s: {json.dumps(s5_result, default=str)}")

    s5_check = await db_pool.fetch("SELECT pipeline_stage, COUNT(*) as n FROM business_universe WHERE pipeline_stage >= 5 GROUP BY pipeline_stage ORDER BY pipeline_stage")
    log.info(f"CHECKPOINT [After Stage 5]: {[dict(r) for r in s5_check]}")

    # --- STAGE 6 ---
    log.info("=== STAGE 6: REACHABILITY SCORING ===")
    t6 = time.time()
    stage6 = Stage6Reachability(leadmagic, db_pool)
    s6_result = await stage6.run(batch_size=100, mobile_spend_cap_aud=STAGE6_SPEND_CAP)
    log.info(f"Stage 6 complete in {time.time()-t6:.1f}s: {json.dumps(s6_result, default=str)}")

    s6_check = await db_pool.fetch("SELECT pipeline_stage, pipeline_status, COUNT(*) as n FROM business_universe WHERE pipeline_stage = 6 GROUP BY pipeline_stage, pipeline_status ORDER BY pipeline_status")
    log.info(f"CHECKPOINT [After Stage 6]: {[dict(r) for r in s6_check]}")

    # --- CAMPAIGN CLAIMER ---
    # CampaignClaimer uses db.transaction() which requires a connection, not a pool
    log.info("=== CAMPAIGN CLAIMER ===")
    t_claim = time.time()
    async with db_pool.acquire() as claim_conn:
        claimer = CampaignClaimer(claim_conn)
        claim_result = await claimer.claim_for_campaign(
            campaign_id=CAMPAIGN_ID,
            client_id=CLIENT_ID,
            filters={"min_propensity": 40, "min_reachability": 0},
            max_claims=200,
        )
    log.info(f"Claim complete in {time.time()-t_claim:.1f}s: {json.dumps(claim_result, default=str)}")

    claim_check = await db_pool.fetchval("SELECT COUNT(*) FROM campaign_leads WHERE campaign_id = $1", CAMPAIGN_ID)
    log.info(f"CHECKPOINT [campaign_leads]: {claim_check} rows")

    if claim_check == 0:
        log.warning("STOPPING: No leads claimed. Stage 7 skipped.")
        await db_pool.close()
        return

    # --- STAGE 7 ---
    log.info("=== STAGE 7: PERSONALISATION ===")
    t7 = time.time()
    stage7 = Stage7Personalisation(anthropic, db_pool)
    s7_result = await stage7.run(campaign_id=CAMPAIGN_ID, batch_size=20)
    log.info(f"Stage 7 complete in {time.time()-t7:.1f}s: {json.dumps(s7_result, default=str)}")

    # Sample messages
    msgs = await db_pool.fetch("""
        SELECT cl.id, bu.display_name, bu.suburb, bu.propensity_score,
               m.channel, m.subject, m.body, m.generation_cost_aud, m.status
        FROM campaign_leads cl
        JOIN business_universe bu ON bu.id = cl.business_universe_id
        JOIN campaign_lead_messages m ON m.campaign_lead_id = cl.id
        WHERE cl.campaign_id = $1
        ORDER BY bu.propensity_score DESC
        LIMIT 3
    """, CAMPAIGN_ID)
    log.info(f"SAMPLE MESSAGES ({len(msgs)} shown):")
    for m in msgs:
        log.info(f"  [{m['display_name']} / {m['suburb']} / score {m['propensity_score']}]")
        log.info(f"  Subject: {m['subject']}")
        log.info(f"  Body: {m['body'][:500]}...")
        log.info(f"  Cost: AUD {m['generation_cost_aud']}")

    log.info("=== STAGES 4-7 COMPLETE ===")
    await db_pool.close()


asyncio.run(run_test())
