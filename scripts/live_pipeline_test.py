#!/usr/bin/env python3
"""
scripts/live_pipeline_test.py
Live pipeline test — Directive #253
5 inner Sydney suburbs, "digital marketing agency" category
Stages 1-3 (controlled, real APIs)
"""

import asyncio
import json
import logging
import os
import sys
import time
from datetime import datetime, timezone
from decimal import Decimal

import asyncpg
from dotenv import load_dotenv

# Load env from config/.env (symlinked to /home/elliotbot/.config/agency-os/.env)
load_dotenv("config/.env")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(
            f"logs/live_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        ),
    ],
)
log = logging.getLogger("live_test")

# ── CONFIGURATION ──────────────────────────────────────────────────────────────
CAMPAIGN_ID = "4c894b10-fa19-48c9-b2c6-87941f6870e5"
CLIENT_ID = "79113059-5b71-4f79-a321-d2ba326598bc"

TEST_SUBURBS = [
    {"name": "Surry Hills",  "state": "NSW", "lat": -33.8837, "lng": 151.2128},
    {"name": "Newtown",      "state": "NSW", "lat": -33.8983, "lng": 151.1775},
    {"name": "Paddington",   "state": "NSW", "lat": -33.8842, "lng": 151.2315},
    {"name": "Redfern",      "state": "NSW", "lat": -33.8928, "lng": 151.2041},
    {"name": "Darlinghurst", "state": "NSW", "lat": -33.8794, "lng": 151.2193},
]
CATEGORY = "dentist"
STAGE1_SPEND_CAP = 5.0  # AUD — for 5 suburbs this should be ~$0.15

# ── IMPORTS ────────────────────────────────────────────────────────────────────
from src.clients.dfs_gmaps_client import DFSGMapsClient, get_dfs_gmaps_client
from src.pipeline.stage2_free_signals import Stage2FreeSignals
from src.pipeline.stage3_propensity import Stage3Propensity


async def get_db_pool():
    db_url = os.getenv("DATABASE_URL", "")
    # Strip SQLAlchemy prefix if present
    raw_url = db_url.replace("postgresql+asyncpg://", "postgresql://")
    pool = await asyncpg.create_pool(raw_url, statement_cache_size=0, min_size=2, max_size=5)
    return pool


async def checkpoint(db_pool, label, sql, *params):
    async with db_pool.acquire() as conn:
        result = await conn.fetch(sql, *params)
        log.info(f"CHECKPOINT [{label}]: {[dict(r) for r in result]}")
    return result


async def run_stage1(dfs_client: DFSGMapsClient, db_pool):
    """
    Stage 1: Direct DFSGMapsClient calls per suburb.

    LAW I-A findings:
    - discover_by_coordinates(lat, lng, category, zoom=14, depth=100)
      returns pre-mapped list of bu-column dicts (map_to_bu_columns already called internally)
    - Returned dicts have pipeline_stage=0, pipeline_status="discovered" — we override to stage=1
    - Dedup: ON CONFLICT (gmb_place_id) DO NOTHING
    - ABR match done at end against abn_registry on display_name+state
    """
    log.info("=== STAGE 1: DISCOVERY (direct coordinate calls) ===")
    total_discovered = 0
    total_inserted = 0
    total_deduped = 0
    errors = []
    inserted_ids = []

    async with db_pool.acquire() as conn:
        for suburb in TEST_SUBURBS:
            log.info(
                f"  Discovering: {suburb['name']} "
                f"({suburb['lat']}, {suburb['lng']}) "
                f"[cost so far: AUD {float(dfs_client.estimated_cost_aud):.4f}]"
            )

            # Spend cap check
            from src.clients.dfs_gmaps_client import COST_PER_SEARCH_AUD
            if dfs_client.estimated_cost_aud + COST_PER_SEARCH_AUD > Decimal(str(STAGE1_SPEND_CAP)):
                log.warning(
                    f"  Spend cap AUD {STAGE1_SPEND_CAP} reached — stopping discovery"
                )
                break

            try:
                # discover_by_coordinates returns pre-mapped bu-column dicts
                t_call = time.time()
                results = await dfs_client.discover_by_coordinates(
                    lat=suburb["lat"],
                    lng=suburb["lng"],
                    category=CATEGORY,
                    zoom=14,
                    depth=100,
                )
                elapsed = time.time() - t_call
                log.info(f"    {suburb['name']}: {len(results)} results in {elapsed:.2f}s")
                total_discovered += len(results)

                for bu_row in results:
                    # Override pipeline_stage/status + add suburb/state
                    bu_row["pipeline_stage"] = 1
                    bu_row["pipeline_status"] = "discovered"
                    bu_row["suburb"] = suburb["name"]
                    bu_row["state"] = suburb["state"]

                    # Dynamic INSERT
                    cols = list(bu_row.keys())
                    placeholders = [f"${i+1}" for i in range(len(cols))]
                    values = [bu_row[c] for c in cols]

                    try:
                        inserted_id = await conn.fetchval(
                            f"""INSERT INTO business_universe ({', '.join(cols)})
                                VALUES ({', '.join(placeholders)})
                                ON CONFLICT (gmb_place_id) DO NOTHING
                                RETURNING id""",
                            *values,
                        )
                        if inserted_id:
                            total_inserted += 1
                            inserted_ids.append(inserted_id)
                        else:
                            total_deduped += 1
                    except Exception as e:
                        errors.append({
                            "suburb": suburb["name"],
                            "business": bu_row.get("display_name", ""),
                            "error": str(e),
                        })

            except Exception as e:
                log.error(f"    {suburb['name']} DFS error: {e}")
                errors.append({"suburb": suburb["name"], "error": str(e)})

    # ABR match for newly inserted records
    abr_matched = 0
    if inserted_ids:
        log.info(f"  Running ABR match for {len(inserted_ids)} inserted records...")
        async with db_pool.acquire() as conn:
            abr_result = await conn.execute(
                """
                UPDATE business_universe bu
                SET
                    abn = ar.abn,
                    entity_type = ar.entity_type,
                    gst_registered = CASE WHEN ar.gst_registered = true THEN true ELSE false END,
                    registration_date = ar.registration_date,
                    abr_matched_at = NOW()
                FROM abn_registry ar
                WHERE bu.id = ANY($1::uuid[])
                  AND bu.abn IS NULL
                  AND LOWER(bu.display_name) = LOWER(ar.display_name)
                  AND LOWER(bu.state) = LOWER(ar.state)
                  AND NOT EXISTS (
                    SELECT 1 FROM business_universe other
                    WHERE other.abn = ar.abn AND other.id != bu.id
                  )
                """,
                inserted_ids,
            )
            abr_matched = int(abr_result.split()[-1]) if abr_result else 0
        log.info(f"  ABR matched: {abr_matched} records")

    result = {
        "discovered": total_discovered,
        "inserted": total_inserted,
        "deduped": total_deduped,
        "abr_matched": abr_matched,
        "cost_aud": float(dfs_client.estimated_cost_aud),
        "errors": errors,
    }
    log.info(f"Stage 1 result: {json.dumps(result, indent=2, default=str)}")
    return result


async def run_test():
    log.info("=" * 60)
    log.info("DIRECTIVE #253 — LIVE PIPELINE TEST")
    log.info(f"CAMPAIGN_ID: {CAMPAIGN_ID}")
    log.info(f"CLIENT_ID: {CLIENT_ID}")
    log.info(f"Suburbs: {[s['name'] for s in TEST_SUBURBS]}")
    log.info("=" * 60)

    db_pool = await get_db_pool()
    dfs_client = get_dfs_gmaps_client()

    try:
        # ── STAGE 1 ──────────────────────────────────────
        t0 = time.time()
        s1_result = await run_stage1(dfs_client, db_pool)
        log.info(f"Stage 1 completed in {time.time()-t0:.1f}s")

        # Checkpoint
        await checkpoint(
            db_pool, "After Stage 1",
            "SELECT COUNT(*) as count, pipeline_stage FROM business_universe "
            "WHERE pipeline_stage = 1 GROUP BY pipeline_stage",
        )

        if s1_result["inserted"] == 0:
            log.warning("STOPPING: No new businesses inserted. Check dedup or DFS results.")
            return

        # ── STAGE 2 ──────────────────────────────────────
        log.info("=== STAGE 2: FREE SIGNALS ===")
        t0 = time.time()
        async with db_pool.acquire() as conn:
            s2 = Stage2FreeSignals(conn)
            s2_result = await s2.run(batch_size=100)
        log.info(
            f"Stage 2 complete in {time.time()-t0:.1f}s: "
            f"{json.dumps(s2_result, indent=2, default=str)}"
        )

        await checkpoint(
            db_pool, "After Stage 2",
            "SELECT COUNT(*) as count FROM business_universe WHERE pipeline_stage = 2",
        )

        # ── STAGE 3 ──────────────────────────────────────
        log.info("=== STAGE 3: PROPENSITY SCORING ===")
        t0 = time.time()
        async with db_pool.acquire() as conn:
            s3 = Stage3Propensity(conn)
            s3_result = await s3.run(batch_size=200)
        log.info(
            f"Stage 3 complete in {time.time()-t0:.1f}s: "
            f"{json.dumps(s3_result, indent=2, default=str)}"
        )

        await checkpoint(
            db_pool, "After Stage 3",
            """SELECT
                COUNT(*) as total,
                COUNT(*) FILTER (WHERE propensity_score >= 70) as high,
                COUNT(*) FILTER (WHERE propensity_score >= 40 AND propensity_score < 70) as medium,
                COUNT(*) FILTER (WHERE propensity_score < 40) as low,
                ROUND(AVG(propensity_score), 1) as avg_score
            FROM business_universe WHERE pipeline_stage = 3""",
        )

        log.info("=== STAGES 1-3 COMPLETE — STOPPING FOR REVIEW ===")

    finally:
        await dfs_client.close()
        await db_pool.close()


if __name__ == "__main__":
    asyncio.run(run_test())
