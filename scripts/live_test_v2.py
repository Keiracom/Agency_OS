#!/usr/bin/env python3
"""
Calibration Run — Directive #268
Fresh 100 domains through full S1-S7 pipeline.
Purpose: establish real funnel conversion rates for tier cost projections.
Budget cap: $10 USD.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
import time
from datetime import datetime

import asyncpg
from dotenv import load_dotenv

load_dotenv("/home/elliotbot/.config/agency-os/.env", override=True)

from src.enrichment.signal_config import SignalConfigRepository
from src.integrations.anthropic import AnthropicClient
from src.integrations.bright_data_gmb_client import BrightDataGMBClient
from src.integrations.dfs_labs_client import DFSLabsClient
from src.integrations.leadmagic import LeadmagicClient
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

BUDGET_CAP = 10.0
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
            raise RuntimeError(f"BUDGET CAP APPROACHING: ${self.total:.4f} of ${self.cap}")

    def report(self):
        log.info("=== COST BREAKDOWN ===")
        for stage, cost in self.breakdown.items():
            log.info(f"  {stage}: ${cost:.4f}")
        log.info(f"  TOTAL: ${self.total:.4f}")


async def count_at_stage(conn, stage: int) -> int:
    row = await conn.fetchrow(
        "SELECT COUNT(*) AS n FROM business_universe WHERE pipeline_stage = $1", stage
    )
    return row["n"] if row else 0


async def main():
    start_time = time.time()
    bugs: list[str] = []
    cost = CostTracker(cap=BUDGET_CAP)
    funnel: dict[str, dict] = {}

    log.info("=== CALIBRATION RUN — DIRECTIVE #268 ===")
    log.info(f"Time: {datetime.utcnow().isoformat()}")
    log.info(f"Budget cap: ${BUDGET_CAP}")
    log.info(f"Vertical: {VERTICAL}")

    dsn = os.environ.get("DATABASE_URL", "").replace("postgresql+asyncpg://", "postgresql://")
    conn = await asyncpg.connect(dsn, statement_cache_size=0)
    await conn.set_type_codec(
        "jsonb", encoder=json.dumps, decoder=json.loads, schema="pg_catalog", format="text"
    )
    await conn.set_type_codec(
        "json", encoder=json.dumps, decoder=json.loads, schema="pg_catalog", format="text"
    )
    log.info("DB connected")

    try:
        # Baseline before run
        pre_s1 = await count_at_stage(conn, 1)
        log.info(f"[PRE-RUN] stage=1 baseline: {pre_s1} rows")

        dfs_client = DFSLabsClient(
            login=os.environ["DATAFORSEO_LOGIN"],
            password=os.environ["DATAFORSEO_PASSWORD"],
        )
        gmb_client = BrightDataGMBClient()
        leadmagic_client = LeadmagicClient()
        anthropic_client = AnthropicClient()
        signal_repo = SignalConfigRepository(conn)
        log.info("Clients initialised")

        # ─────────────────────────────────────────── S1
        t0 = time.time()
        log.info("--- S1: DFS Discovery (max 25/tech) ---")
        try:
            stage1 = Stage1Discovery(dfs_client, signal_repo, conn)
            config = await signal_repo.get_config(VERTICAL)
            result1 = await stage1.run_batch(
                vertical_slug=VERTICAL,
                technologies=config.all_dfs_technologies,
                max_domains_per_tech=25,
            )
            log.info(f"S1: {result1}")
            cost.add("S1", float(result1.get("cost_usd", 0)))
            post_s1 = await count_at_stage(conn, 1)
            s1_new = post_s1 - pre_s1
            funnel["S1"] = {
                "in": "-",
                "out": result1.get("discovered", 0),
                "cost": float(result1.get("cost_usd", 0)),
                "time": time.time() - t0,
            }
            log.info(
                f"[FUNNEL] S1: {result1.get('discovered', 0)} new discovered, {result1.get('duplicates_skipped', 0)} dupes skipped, {result1.get('blocklist_filtered', 0)} blocklisted"
            )
        except Exception as e:
            bugs.append(f"S1: {e}")
            log.error(f"S1 error: {e}", exc_info=True)
            funnel["S1"] = {"in": "-", "out": 0, "cost": 0}

        # ─────────────────────────────────────────── S2
        t0 = time.time()
        log.info("--- S2: GMB Reverse Lookup (batch_size=41) ---")
        try:
            stage2 = Stage2GMBLookup(gmb_client, conn)
            result2 = await stage2.run(batch_size=41)
            log.info(f"S2: {result2}")
            cost.add("S2", float(result2.get("cost_usd", 0)))
            n_s2 = await count_at_stage(conn, 2)
            funnel["S2"] = {
                "in": funnel.get("S1", {}).get("out", 0),
                "out": result2.get("enriched", 0) + result2.get("already_enriched", 0),
                "cost": float(result2.get("cost_usd", 0)),
                "time": time.time() - t0,
            }
            log.info(
                f"[FUNNEL] S2 → stage=2: {n_s2} rows | enriched={result2.get('enriched', 0)} already={result2.get('already_enriched', 0)} no_gmb={result2.get('no_gmb_found', 0)}"
            )
        except Exception as e:
            bugs.append(f"S2: {e}")
            log.error(f"S2 error: {e}", exc_info=True)
            funnel["S2"] = {"in": 0, "out": 0, "cost": 0}

        # ─────────────────────────────────────────── S3
        t0 = time.time()
        log.info("--- S3: DFS Profile (batch_size=41) ---")
        try:
            stage3 = Stage3DFSProfile(dfs_client, signal_repo, conn, delay=0.2)
            result3 = await stage3.run(VERTICAL, batch_size=41)
            log.info(f"S3: {result3}")
            cost.add("S3", float(result3.get("cost_usd", 0)))
            n_s3 = await count_at_stage(conn, 3)
            funnel["S3"] = {
                "in": funnel.get("S2", {}).get("out", 0),
                "out": result3.get("profiled", 0),
                "cost": float(result3.get("cost_usd", 0)),
                "time": time.time() - t0,
            }
            log.info(f"[FUNNEL] S3 → stage=3: {n_s3} rows | profiled={result3.get('profiled', 0)}")
        except Exception as e:
            bugs.append(f"S3: {e}")
            log.error(f"S3 error: {e}", exc_info=True)
            funnel["S3"] = {"in": 0, "out": 0, "cost": 0}

        # ─────────────────────────────────────────── S4
        t0 = time.time()
        log.info("--- S4: Scoring + Qualification ---")
        try:
            stage4 = Stage4Scorer(signal_repo, conn)
            result4 = await stage4.run(VERTICAL)
            log.info(f"S4: {result4}")
            cost.add("S4", 0.0)
            n_s4 = await count_at_stage(conn, 4)

            # Detailed score distribution query
            dist = await conn.fetch("""
                SELECT
                    CASE
                        WHEN propensity_score = 0 THEN '0 (disqualified)'
                        WHEN propensity_score <= 20 THEN '1-20'
                        WHEN propensity_score <= 40 THEN '21-40'
                        WHEN propensity_score <= 60 THEN '41-60'
                        WHEN propensity_score <= 80 THEN '61-80'
                        ELSE '81-100'
                    END as bucket,
                    COUNT(*) as count,
                    best_match_service
                FROM business_universe
                WHERE pipeline_stage = 4
                  AND pipeline_updated_at > NOW() - INTERVAL '10 minutes'
                GROUP BY bucket, best_match_service
                ORDER BY bucket
            """)
            log.info("[S4] Score distribution (this run):")
            for row in dist:
                log.info(
                    f"  {row['bucket']:20s} | {row['best_match_service'] or 'none':20s} | {row['count']} rows"
                )

            # Disqualification reasons
            disq = await conn.fetch("""
                SELECT score_reason, COUNT(*) as count
                FROM business_universe
                WHERE pipeline_stage = 4
                  AND propensity_score = 0
                  AND pipeline_updated_at > NOW() - INTERVAL '10 minutes'
                GROUP BY score_reason
                ORDER BY count DESC
                LIMIT 10
            """)
            if disq:
                log.info("[S4] Disqualification reasons:")
                for row in disq:
                    log.info(f"  {row['count']:3d}x {row['score_reason']}")

            # Avg score for qualified
            avg_row = await conn.fetchrow("""
                SELECT AVG(propensity_score) as avg_score, COUNT(*) as qualified_count
                FROM business_universe
                WHERE pipeline_stage = 4
                  AND propensity_score > 0
                  AND pipeline_updated_at > NOW() - INTERVAL '10 minutes'
            """)
            if avg_row:
                log.info(
                    f"[S4] Qualified: {avg_row['qualified_count']} | Avg propensity: {float(avg_row['avg_score'] or 0):.1f}"
                )

            funnel["S4"] = {
                "in": funnel.get("S3", {}).get("out", 0),
                "out": result4.get("above_threshold", 0),
                "qualified": result4.get("scored", 0) - result4.get("below_threshold", 0),
                "cost": 0,
                "time": time.time() - t0,
            }
            log.info(
                f"[FUNNEL] S4 → stage=4: {n_s4} rows | above_gate={result4.get('above_threshold', 0)} below={result4.get('below_threshold', 0)}"
            )
        except Exception as e:
            bugs.append(f"S4: {e}")
            log.error(f"S4 error: {e}", exc_info=True)
            funnel["S4"] = {"in": 0, "out": 0, "cost": 0}

        # ─────────────────────────────────────────── S5
        t0 = time.time()
        log.info("--- S5: DM Waterfall (batch_size=20) ---")
        try:
            stage5 = Stage5DMWaterfall(leadmagic_client, signal_repo, conn)
            result5 = await stage5.run(VERTICAL, batch_size=20)
            log.info(f"S5: {result5}")
            cost.add("S5", float(result5.get("cost_usd", 0)))
            n_s5 = await count_at_stage(conn, 5)
            sources = result5.get("sources_used", {})
            log.info(f"[S5] Sources used: {sources}")
            funnel["S5"] = {
                "in": funnel.get("S4", {}).get("out", 0),
                "out": result5.get("found", 0),
                "cost": float(result5.get("cost_usd", 0)),
                "time": time.time() - t0,
            }
            log.info(
                f"[FUNNEL] S5 → stage=5: {n_s5} rows | DMs found={result5.get('found', 0)} not_found={result5.get('not_found', 0)}"
            )
        except Exception as e:
            bugs.append(f"S5: {e}")
            log.error(f"S5 error: {e}", exc_info=True)
            funnel["S5"] = {"in": 0, "out": 0, "cost": 0}

        # ─────────────────────────────────────────── S6
        t0 = time.time()
        log.info("--- S6: Reachability ---")
        try:
            stage6 = Stage6Reachability(signal_repo, conn)
            result6 = await stage6.run(VERTICAL, batch_size=100)
            log.info(f"S6: {result6}")
            cost.add("S6", 0.0)
            channels = result6.get("channels_confirmed", {})
            n_s6 = await count_at_stage(conn, 6)
            total_validated = result6.get("validated", 0)
            log.info(f"[S6] Channel breakdown: {channels}")
            if total_validated:
                for ch, cnt in channels.items():
                    log.info(f"  {ch}: {cnt}/{total_validated} = {cnt * 100 // total_validated}%")
            funnel["S6"] = {
                "in": funnel.get("S5", {}).get("out", 0),
                "out": total_validated,
                "cost": 0,
                "time": time.time() - t0,
            }
            log.info(f"[FUNNEL] S6 → stage=6: {n_s6} rows | validated={total_validated}")
        except Exception as e:
            bugs.append(f"S6: {e}")
            log.error(f"S6 error: {e}", exc_info=True)
            funnel["S6"] = {"in": 0, "out": 0, "cost": 0}

        # ─────────────────────────────────────────── S7
        t0 = time.time()
        log.info("--- S7: Haiku Message Generation (batch_size=10) ---")
        try:
            stage7 = Stage7Haiku(anthropic_client, signal_repo, conn)
            result7 = await stage7.run(VERTICAL, agency_profile=AGENCY_PROFILE, batch_size=10)
            log.info(f"S7: {result7}")
            cost.add("S7", float(result7.get("cost_usd", 0)))
            n_s7 = await count_at_stage(conn, 7)
            funnel["S7"] = {
                "in": funnel.get("S6", {}).get("out", 0),
                "out": result7.get("messages_generated", 0),
                "cost": float(result7.get("cost_usd", 0)),
                "time": time.time() - t0,
            }
            log.info(
                f"[FUNNEL] S7 → stage=7: {n_s7} rows | messages={result7.get('messages_generated', 0)}"
            )
        except Exception as e:
            bugs.append(f"S7: {e}")
            log.error(f"S7 error: {e}", exc_info=True)
            funnel["S7"] = {"in": 0, "out": 0, "cost": 0}

        # ─────────────────────────────────────────── Print samples
        log.info("=== HAIKU MESSAGE SAMPLES ===")
        try:
            rows = await conn.fetch("""
                SELECT domain, display_name, dm_name, dm_title, outreach_messages, propensity_score
                FROM business_universe
                WHERE pipeline_stage = 7
                  AND outreach_messages IS NOT NULL
                  AND pipeline_updated_at > NOW() - INTERVAL '30 minutes'
                ORDER BY propensity_score DESC NULLS LAST
                LIMIT 3
            """)
            for i, row in enumerate(rows, 1):
                msgs = row["outreach_messages"]
                if isinstance(msgs, str):
                    msgs = json.loads(msgs)
                print(f"\n{'=' * 60}")
                print(f"Sample {i}: {row['display_name'] or row['domain']}")
                print(
                    f"DM: {row['dm_name']} ({row['dm_title']}) | Score: {row['propensity_score']}"
                )
                if isinstance(msgs, dict):
                    for ch, txt in msgs.items():
                        print(f"\n  [{ch.upper()}]\n{txt}")
        except Exception as e:
            log.error(f"Sample query error: {e}")

    except RuntimeError as budget_err:
        log.error(f"STOPPED: {budget_err}")
        bugs.append(f"BUDGET: {budget_err}")
    except Exception as e:
        log.error(f"FATAL: {e}", exc_info=True)
        bugs.append(f"FATAL: {e}")
    finally:
        await conn.close()
        elapsed = time.time() - start_time

        # ─────────────────────────────────────────── FUNNEL TABLE
        print("\n" + "=" * 70)
        print("FUNNEL CONVERSION TABLE")
        print("=" * 70)
        print(f"{'STAGE':<12} {'IN':>6} {'OUT':>6} {'RATE':>7} {'COST':>8}")
        print("-" * 70)
        stages = ["S1", "S2", "S3", "S4", "S5", "S6", "S7"]
        total_cost = 0.0
        for s in stages:
            d = funnel.get(s, {})
            inn = d.get("in", "-")
            out = d.get("out", 0)
            rate = f"{out * 100 // inn:.0f}%" if isinstance(inn, int) and inn > 0 else "-"
            c = d.get("cost", 0)
            total_cost += c
            print(f"{s:<12} {str(inn):>6} {str(out):>6} {rate:>7} ${c:>7.4f}")
        print("-" * 70)
        print(f"{'TOTAL':<12} {'':>6} {'':>6} {'':>7} ${total_cost:>7.4f}")

        # ─────────────────────────────────────────── TIER PROJECTIONS
        s1_out = funnel.get("S1", {}).get("out", 1)
        s7_out = funnel.get("S7", {}).get("out", 0)
        overall_rate = s7_out / max(s1_out, 1)
        cost_per_s1 = total_cost / max(s1_out, 1)

        print("\n" + "=" * 70)
        print("TIER PROJECTIONS (based on this run)")
        print("=" * 70)
        print(f"Overall S1→S7 conversion rate: {overall_rate * 100:.1f}%")
        print(f"Cost per S1 domain: ${cost_per_s1:.4f}")
        print()
        print(f"{'TIER':<12} {'TARGET':>8} {'S1 NEEDED':>10} {'EST COST':>10}")
        print("-" * 45)
        for tier, target in [("Spark", 150), ("Ignition", 600), ("Velocity", 1500)]:
            if overall_rate > 0:
                s1_needed = int(target / overall_rate)
                est_cost = s1_needed * cost_per_s1
            else:
                s1_needed = "N/A"
                est_cost = 0
            print(f"{tier:<12} {target:>8} {str(s1_needed):>10} ${est_cost:>9.2f}")

        print(f"\nTotal time: {elapsed:.1f}s")
        cost.report()
        if bugs:
            print("\n=== BUGS FOUND ===")
            for b in bugs:
                print(f"  {b}")
        else:
            print("\n=== NO BUGS ===")
        print("=== CALIBRATION RUN END ===")


if __name__ == "__main__":
    asyncio.run(main())
