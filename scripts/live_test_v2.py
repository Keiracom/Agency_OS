#!/usr/bin/env python3
"""
Live Test v2 — Full Pipeline Validation
Directive #265

Runs the complete v5 pipeline (S1-S7) against real APIs.
Budget cap: $15 USD. Stop if approaching.
"""
from __future__ import annotations

import asyncio
import logging
import os
import sys
import time
from datetime import datetime
from decimal import Decimal

import asyncpg
from dotenv import load_dotenv

load_dotenv("/home/elliotbot/.config/agency-os/.env")

# -- stage and client imports --
from src.clients.dfs_labs_client import DFSLabsClient
from src.clients.bright_data_gmb_client import BrightDataGMBClient
from src.integrations.leadmagic import LeadmagicClient
from src.integrations.anthropic import AnthropicClient
from src.enrichment.signal_config import SignalConfigRepository
from src.pipeline.stage_1_discovery import Stage1Discovery
from src.pipeline.stage_2_gmb_lookup import Stage2GMBLookup
from src.pipeline.stage_3_dfs_profile import Stage3DFSProfile
from src.pipeline.stage_4_scoring import Stage4Scorer
from src.pipeline.stage_5_dm_waterfall import Stage5DMWaterfall
from src.pipeline.stage_6_reachability import Stage6Reachability
from src.pipeline.stage_7_haiku import Stage7Haiku

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    stream=sys.stdout,
)
log = logging.getLogger(__name__)

BUDGET_CAP = 15.0
VERTICAL = "marketing_agency"

AGENCY_PROFILE = {
    "name": "Keiracom Digital",
    "services": ["SEO", "Paid Search", "Marketing Automation"],
    "tone": "direct, results-focused, no fluff",
    "founder_name": "Dave",
    "case_study": "Helped a home services business increase qualified leads by 40% in 60 days through Google Ads optimisation",
}


class CostTracker:
    def __init__(self, cap: float):
        self.cap = cap
        self.total = 0.0
        self.breakdown: dict[str, float] = {}

    def add(self, stage: str, amount: float):
        self.total += amount
        self.breakdown[stage] = self.breakdown.get(stage, 0.0) + amount
        log.info(f"[COST] {stage}: +${amount:.4f} (total: ${self.total:.4f})")
        if self.total >= self.cap * 0.9:
            raise RuntimeError(
                f"BUDGET CAP APPROACHING: ${self.total:.4f} of ${self.cap} — stopping pipeline"
            )

    def report(self):
        log.info("=== COST BREAKDOWN ===")
        for stage, cost in self.breakdown.items():
            log.info(f"  {stage}: ${cost:.4f}")
        log.info(f"  TOTAL: ${self.total:.4f}")


def stage_timer(name: str):
    """Context helper — returns elapsed seconds."""
    class _T:
        def __enter__(self):
            self._t = time.time()
            log.info(f"--- {name} START ---")
            return self
        def __exit__(self, *_):
            self.elapsed = time.time() - self._t
            log.info(f"--- {name} DONE ({self.elapsed:.1f}s) ---")
    return _T()


async def count_at_stage(conn, stage: int) -> int:
    row = await conn.fetchrow(
        "SELECT COUNT(*) AS n FROM business_universe WHERE pipeline_stage = $1", stage
    )
    return row["n"] if row else 0


async def main():
    start_time = time.time()
    bugs: list[str] = []
    cost = CostTracker(cap=BUDGET_CAP)

    log.info("=== LIVE TEST v2 START ===")
    log.info(f"Time: {datetime.utcnow().isoformat()}")
    log.info(f"Budget cap: ${BUDGET_CAP}")
    log.info(f"Vertical: {VERTICAL}")

    # -- DB connection --
    dsn = os.environ.get("DATABASE_URL") or os.environ.get("SUPABASE_DB_URL")
    if not dsn:
        raise RuntimeError("No DATABASE_URL found in environment")
    # Strip SQLAlchemy dialect prefix (+asyncpg) if present
    dsn = dsn.replace("postgresql+asyncpg://", "postgresql://")
    log.info(f"Connecting to DB (DSN found: yes)")
    conn = await asyncpg.connect(dsn, statement_cache_size=0)
    # PgBouncer in transaction mode returns JSONB as text — register codec
    import json as _json
    await conn.set_type_codec(
        "jsonb",
        encoder=_json.dumps,
        decoder=_json.loads,
        schema="pg_catalog",
        format="text",
    )
    await conn.set_type_codec(
        "json",
        encoder=_json.dumps,
        decoder=_json.loads,
        schema="pg_catalog",
        format="text",
    )
    log.info("DB connected")

    try:
        # -- Baseline counts --
        for s in range(1, 8):
            n = await count_at_stage(conn, s)
            log.info(f"[BASELINE] pipeline_stage={s}: {n} rows")

        # -- Client setup --
        dfs_login = os.environ.get("DATAFORSEO_LOGIN", "")
        dfs_password = os.environ.get("DATAFORSEO_PASSWORD", "")
        if not dfs_login or not dfs_password:
            raise RuntimeError("DATAFORSEO_LOGIN / DATAFORSEO_PASSWORD not set")

        dfs_client = DFSLabsClient(login=dfs_login, password=dfs_password)
        gmb_client = BrightDataGMBClient()
        leadmagic_client = LeadmagicClient()
        anthropic_client = AnthropicClient()

        signal_repo = SignalConfigRepository(conn)
        log.info("All clients initialised")

        # ------------------------------------------------------------------ S1
        with stage_timer("S1: DFS Discovery") as t1:
            try:
                stage1 = Stage1Discovery(dfs_client, signal_repo, conn)
                # Use run_batch() to cap domains per tech (run() defaults to 1000)
                config = await signal_repo.get_config(VERTICAL)
                result1 = await stage1.run_batch(
                    vertical_slug=VERTICAL,
                    technologies=config.all_dfs_technologies,
                    max_domains_per_tech=50,
                )
                log.info(f"S1 result: {result1}")
                s1_cost = float(result1.get("cost_usd", 0))
                cost.add("S1_discovery", s1_cost)
                n_s1 = await count_at_stage(conn, 1)
                log.info(f"[FUNNEL] After S1: {n_s1} rows at stage=1")
            except Exception as e:
                bugs.append(f"S1 FATAL: {e}")
                log.error(f"S1 error: {e}", exc_info=True)

        # ------------------------------------------------------------------ S2
        with stage_timer("S2: GMB Lookup") as t2:
            try:
                stage2 = Stage2GMBLookup(gmb_client, conn)
                result2 = await stage2.run(batch_size=30)
                log.info(f"S2 result: {result2}")
                s2_cost = float(result2.get("cost_usd", 0))
                cost.add("S2_gmb", s2_cost)
                n_s2 = await count_at_stage(conn, 2)
                log.info(f"[FUNNEL] After S2: {n_s2} rows at stage=2")
            except Exception as e:
                bugs.append(f"S2 FATAL: {e}")
                log.error(f"S2 error: {e}", exc_info=True)

        # ------------------------------------------------------------------ S3
        with stage_timer("S3: DFS Profile") as t3:
            try:
                stage3 = Stage3DFSProfile(dfs_client, signal_repo, conn, delay=0.2)
                result3 = await stage3.run(VERTICAL, batch_size=30)
                log.info(f"S3 result: {result3}")
                s3_cost = float(result3.get("cost_usd", 0))
                cost.add("S3_dfs_profile", s3_cost)
                n_s3 = await count_at_stage(conn, 3)
                log.info(f"[FUNNEL] After S3: {n_s3} rows at stage=3")
            except Exception as e:
                bugs.append(f"S3 FATAL: {e}")
                log.error(f"S3 error: {e}", exc_info=True)

        # ------------------------------------------------------------------ S4
        with stage_timer("S4: Scoring") as t4:
            try:
                stage4 = Stage4Scorer(signal_repo, conn)
                result4 = await stage4.run(VERTICAL)
                log.info(f"S4 result: {result4}")
                cost.add("S4_scoring", 0.0)  # free
                n_s4 = await count_at_stage(conn, 4)
                log.info(f"[FUNNEL] After S4: {n_s4} rows at stage=4")
            except Exception as e:
                bugs.append(f"S4 FATAL: {e}")
                log.error(f"S4 error: {e}", exc_info=True)

        # ------------------------------------------------------------------ S5
        with stage_timer("S5: DM Waterfall") as t5:
            try:
                stage5 = Stage5DMWaterfall(leadmagic_client, signal_repo, conn, extra_sources=None)
                result5 = await stage5.run(VERTICAL, batch_size=10)
                log.info(f"S5 result: {result5}")
                s5_cost = float(result5.get("cost_usd", 0))
                cost.add("S5_dm_waterfall", s5_cost)
                n_s5 = await count_at_stage(conn, 5)
                log.info(f"[FUNNEL] After S5: {n_s5} rows at stage=5")
            except Exception as e:
                bugs.append(f"S5 FATAL: {e}")
                log.error(f"S5 error: {e}", exc_info=True)

        # ------------------------------------------------------------------ S6
        with stage_timer("S6: Reachability") as t6:
            try:
                stage6 = Stage6Reachability(signal_repo, conn)
                result6 = await stage6.run(VERTICAL, batch_size=100)
                log.info(f"S6 result: {result6}")
                cost.add("S6_reachability", 0.0)  # free
                n_s6 = await count_at_stage(conn, 6)
                log.info(f"[FUNNEL] After S6: {n_s6} rows at stage=6")
            except Exception as e:
                bugs.append(f"S6 FATAL: {e}")
                log.error(f"S6 error: {e}", exc_info=True)

        # ------------------------------------------------------------------ S7
        with stage_timer("S7: Haiku Message Generation") as t7:
            try:
                stage7 = Stage7Haiku(anthropic_client, signal_repo, conn)
                result7 = await stage7.run(VERTICAL, agency_profile=AGENCY_PROFILE, batch_size=5)
                log.info(f"S7 result: {result7}")
                s7_cost = float(result7.get("cost_usd", 0))
                cost.add("S7_haiku", s7_cost)
                n_s7 = await count_at_stage(conn, 7)
                log.info(f"[FUNNEL] After S7: {n_s7} rows at stage=7")
            except Exception as e:
                bugs.append(f"S7 FATAL: {e}")
                log.error(f"S7 error: {e}", exc_info=True)

        # ------------------------------------------------------------------ Print Haiku samples
        log.info("=== HAIKU MESSAGE SAMPLES ===")
        try:
            rows = await conn.fetch(
                """
                SELECT domain, display_name, outreach_messages
                FROM business_universe
                WHERE outreach_messages IS NOT NULL
                  AND pipeline_stage = 7
                ORDER BY propensity_score DESC NULLS LAST
                LIMIT 3
                """
            )
            if not rows:
                log.info("No Haiku messages found (0 rows at stage=7 with outreach_messages)")
            for i, row in enumerate(rows, 1):
                log.info(f"\n--- Sample {i}: {row['display_name']} ({row['domain']}) ---")
                import json
                msgs = row["outreach_messages"]
                if isinstance(msgs, str):
                    msgs = json.loads(msgs)
                if isinstance(msgs, dict):
                    for channel, text in msgs.items():
                        log.info(f"  [{channel.upper()}]\n{text}\n")
                else:
                    log.info(f"  {msgs}")
        except Exception as e:
            bugs.append(f"HAIKU_SAMPLE_QUERY: {e}")
            log.error(f"Error fetching haiku samples: {e}", exc_info=True)

        # -- FINAL PIPELINE FUNNEL --
        log.info("=== FINAL PIPELINE FUNNEL ===")
        for s in range(1, 8):
            n = await count_at_stage(conn, s)
            log.info(f"  stage={s}: {n} rows")

    except RuntimeError as budget_err:
        log.error(f"STOPPED: {budget_err}")
        bugs.append(f"BUDGET: {budget_err}")
    except Exception as e:
        log.error(f"PIPELINE ERROR: {e}", exc_info=True)
        bugs.append(f"FATAL: {e}")
    finally:
        await conn.close()
        elapsed = time.time() - start_time
        log.info("=== SUMMARY ===")
        log.info(f"Total time: {elapsed:.1f}s")
        cost.report()
        if bugs:
            log.info("=== BUGS FOUND ===")
            for b in bugs:
                log.info(f"  {b}")
        else:
            log.info("=== NO BUGS — ALL STAGES PASSED ===")
        log.info("=== LIVE TEST v2 END ===")


if __name__ == "__main__":
    asyncio.run(main())
