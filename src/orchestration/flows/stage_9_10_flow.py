"""
Stage 9→10 Pipeline Flow — P4
Directive V3 Closeout

Automated execution of:
  Stage 9: VR generation + ContactOut BDM enrichment
  Stage 10: 4-channel message generation (Sonnet email + Haiku others)

Inputs: BDM IDs (explicit list) OR top-N by propensity with dedup
Outputs: dm_messages rows with status='draft'
Budget: hard cap per run (default $5 USD)
Concurrency: anthropic=12, contactout=15
Alerting: Telegram on failure
"""
from __future__ import annotations

import json
import logging
import os
from typing import Any

import asyncpg
from prefect import flow, task
from prefect.cache_policies import NO_CACHE

try:
    from prefect import get_run_logger as _get_run_logger
except ImportError:
    _get_run_logger = None


def _logger() -> logging.Logger:
    """Return Prefect run logger if in a flow context, else standard logger."""
    if _get_run_logger is not None:
        try:
            return _get_run_logger()
        except Exception:
            pass
    return logging.getLogger(__name__)

from src.pipeline.stage_9_vulnerability_enrichment import Stage9VulnerabilityEnrichment
from src.pipeline.stage_10_message_generator import Stage10MessageGenerator
from src.enrichment.signal_config import SignalConfigRepository
from src.prefect_utils.hooks import on_failure_hook
from src.exceptions import AgencyProfileMissingError

_REQUIRED_AGENCY_FIELDS = {"name", "services", "tone", "founder_name"}

logger = logging.getLogger(__name__)


async def _init_jsonb_codec(conn):
    """Register JSONB codec for connections behind pgbouncer (statement_cache_size=0)."""
    await conn.set_type_codec(
        'jsonb',
        encoder=json.dumps,
        decoder=json.loads,
        schema='pg_catalog',
    )


_DEDUP_SQL = """
WITH deduped AS (
    SELECT DISTINCT ON (bdm.linkedin_url)
        bdm.id AS bdm_id
    FROM business_decision_makers bdm
    JOIN business_universe bu ON bu.id = bdm.business_universe_id
    WHERE bdm.is_current = TRUE
      AND bdm.linkedin_url IS NOT NULL
      AND bdm.name IS NOT NULL AND bdm.name != 'Unknown'
      AND bu.pipeline_stage = 9
      AND (bu.domain LIKE '%.com.au' OR bu.domain LIKE '%.net.au'
           OR bu.domain LIKE '%.id.au' OR bu.domain LIKE '%.asn.au'
           OR bu.domain LIKE '%.sydney' OR bu.domain LIKE '%.melbourne'
           OR bu.domain LIKE '%.perth' OR bu.domain LIKE '%.brisbane')
      AND bu.domain NOT LIKE '%.gov.au'
      AND bu.domain NOT LIKE '%.gov'
    ORDER BY bdm.linkedin_url, bu.propensity_score DESC
)
SELECT bdm_id FROM deduped LIMIT $1
"""


@task(name="select-bdms", retries=1, cache_policy=NO_CACHE)
async def select_bdms(
    pool: asyncpg.Pool,
    bdm_ids: list[str] | None,
    batch_size: int,
) -> list[str]:
    """Select deduped BDM IDs — DISTINCT ON linkedin_url, blocklist filtered."""
    if bdm_ids:
        return list(bdm_ids)
    async with pool.acquire() as conn:
        rows = await conn.fetch(_DEDUP_SQL, batch_size)
    return [str(r["bdm_id"]) for r in rows]


@task(name="run-stage-9", retries=0, cache_policy=NO_CACHE)
async def run_stage_9(pool: asyncpg.Pool, bdm_ids: list[str]) -> dict:
    """Run Stage 9 VR + ContactOut enrichment."""
    stage = Stage9VulnerabilityEnrichment(pool)
    return await stage.run(bdm_ids=bdm_ids)


@task(name="verify-stage-9", retries=1, cache_policy=NO_CACHE)
async def verify_stage_9(pool: asyncpg.Pool, bdm_ids: list[str]) -> int:
    """Verify all BDMs have VRs. Return count."""
    async with pool.acquire() as conn:
        count = await conn.fetchval(
            """
            SELECT COUNT(*) FROM business_universe
            WHERE id IN (
                SELECT business_universe_id
                FROM business_decision_makers
                WHERE id = ANY($1::uuid[])
            )
              AND vulnerability_report IS NOT NULL
            """,
            bdm_ids,
        )
    return int(count)


@task(name="run-stage-10", retries=0, cache_policy=NO_CACHE)
async def run_stage_10(
    pool: asyncpg.Pool,
    bdm_ids: list[str],
    vertical_slug: str,
    agency_profile: dict,
) -> dict:
    """Run Stage 10 message generation."""
    from src.integrations.anthropic import AnthropicClient
    from src.intelligence.gemini_client import GeminiClient
    ai = AnthropicClient()
    signal_repo = SignalConfigRepository(pool)
    gemini = GeminiClient(api_key=os.environ.get("GEMINI_API_KEY"))
    gen = Stage10MessageGenerator(ai, signal_repo, pool, gemini_client=gemini, agency_profile=agency_profile)
    return await gen.run(vertical_slug, agency_profile, batch_size=len(bdm_ids))


@task(name="verify-stage-10", cache_policy=NO_CACHE)
async def verify_stage_10(pool: asyncpg.Pool, bdm_ids: list[str]) -> dict:
    """Verify dm_messages counts by channel."""
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT channel, COUNT(*) as cnt FROM dm_messages
            WHERE business_decision_makers_id = ANY($1::uuid[])
            GROUP BY channel ORDER BY channel
            """,
            bdm_ids,
        )
    return {r["channel"]: int(r["cnt"]) for r in rows}


@flow(
    name="stage-9-10-pipeline",
    on_failure=[on_failure_hook],
    timeout_seconds=600,
)
async def stage_9_10_pipeline(
    bdm_ids: list[str] | None = None,
    batch_size: int = 25,
    budget_cap_usd: float = 5.0,
    vertical_slug: str = "marketing_agency",
    agency_profile: dict | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    """
    Orchestrate Stage 9 (VR + ContactOut) followed by Stage 10 (4-channel messages).

    Parameters
    ----------
    bdm_ids:        Explicit list of BDM UUIDs. Auto-selected from pipeline_stage=9 if None.
    batch_size:     Max BDMs to pull when auto-selecting (ignored when bdm_ids provided).
    budget_cap_usd: Hard spend ceiling for the run.
    vertical_slug:  Signal config vertical passed to Stage 10.
    agency_profile: Agency context for message generation. Required — no default fallback.
    dry_run:        If True, select BDMs then stop — no enrichment or generation.
    """
    if not agency_profile or not isinstance(agency_profile, dict):
        raise AgencyProfileMissingError("agency_profile is required for outreach generation")
    missing = _REQUIRED_AGENCY_FIELDS - set(agency_profile.keys())
    if missing:
        raise AgencyProfileMissingError(f"agency_profile missing required fields: {missing}")

    flow_logger = _logger()

    db_url = os.environ["DATABASE_URL"].replace("postgresql+asyncpg://", "postgresql://")
    pool = await asyncpg.create_pool(
        db_url,
        min_size=5,
        max_size=15,
        statement_cache_size=0,
        init=_init_jsonb_codec,
    )

    try:
        # 1. Select BDMs
        selected = await select_bdms(pool, bdm_ids, batch_size)
        flow_logger.info("Selected %d BDMs", len(selected))

        if dry_run:
            flow_logger.info("DRY RUN — skipping execution")
            # Resolve dependencies and estimate costs without API calls
            s9_vr_cost = len(selected) * 0.025  # Sonnet VR per domain
            s9_co_cost = len(selected) * 0.033  # ContactOut per profile
            s10_cost = len(selected) * 0.007    # 4 channels per DM
            total_est = s9_vr_cost + s9_co_cost + s10_cost
            return {
                "dry_run": True,
                "bdm_ids": selected,
                "bdm_count": len(selected),
                "cost_estimate": {
                    "stage_9_vr_usd": round(s9_vr_cost, 4),
                    "stage_9_contactout_usd": round(s9_co_cost, 4),
                    "stage_10_messages_usd": round(s10_cost, 4),
                    "total_usd": round(total_est, 4),
                    "total_aud": round(total_est * 1.55, 4),
                },
                "expected_writes": {
                    "business_universe.vulnerability_report": len(selected),
                    "business_decision_makers (ContactOut fields)": len(selected),
                    "dm_messages": len(selected) * 4,
                },
                "budget_cap_usd": budget_cap_usd,
                "within_budget": total_est <= budget_cap_usd,
            }

        if not selected:
            flow_logger.warning("No BDMs selected — nothing to process")
            return {"bdms_processed": 0, "stage_9": {}, "stage_10": {}, "channel_counts": {}}

        # 2. Budget preflight: ~$0.065 USD per DM (Stage 9 + Stage 10)
        estimated_cost = len(selected) * 0.065
        if estimated_cost > budget_cap_usd:
            raise ValueError(
                f"Estimated cost ${estimated_cost:.2f} exceeds cap ${budget_cap_usd:.2f}"
            )

        # 3. Stage 9
        s9_result = await run_stage_9(pool, selected)
        flow_logger.info("Stage 9 complete: %s", s9_result)

        # 4. Verify Stage 9
        vr_count = await verify_stage_9(pool, selected)
        if vr_count < len(selected):
            raise RuntimeError(
                f"Stage 9 incomplete: {vr_count}/{len(selected)} VRs generated"
            )

        # 5. Post-S9 budget gate
        s9_cost = float(s9_result.get("cost_total_usd", 0))
        remaining = budget_cap_usd - s9_cost
        if remaining <= 0:
            raise ValueError(
                f"Budget exhausted after Stage 9: ${s9_cost:.2f} of ${budget_cap_usd:.2f}"
            )

        # 6. Stage 10
        s10_result = await run_stage_10(pool, selected, vertical_slug, agency_profile)
        flow_logger.info("Stage 10 complete: %s", s10_result)

        # 7. Verify Stage 10
        channel_counts = await verify_stage_10(pool, selected)
        for ch, cnt in channel_counts.items():
            if cnt < len(selected):
                flow_logger.warning("Channel %s: %d/%d messages", ch, cnt, len(selected))

        total_cost = s9_cost + float(s10_result.get("cost_usd", 0))

        return {
            "bdms_processed": len(selected),
            "stage_9": s9_result,
            "stage_10": s10_result,
            "channel_counts": channel_counts,
            "total_cost_usd": round(total_cost, 6),
            "total_cost_aud": round(total_cost * 1.55, 4),
            "budget_cap_usd": budget_cap_usd,
        }

    finally:
        await pool.close()
