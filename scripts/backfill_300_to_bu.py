"""
Backfill integration test data (#300a-d) to business_universe table.

Reads JSON outputs from test stages and upserts to BU with:
- Stage 1 (discovery): domain, organic_etv, category, pipeline_stage=1
- Stage 2 (scrape): website_cms, content signals
- Stage 3 (comprehend): entity_type signals, tech stack
- Stage 4 (affordability): gst_registered, entity_type, abn_matched, scores

claimed_by = NULL (unclaimed inventory).
From Stage 5 onwards: write to BOTH JSON and BU directly.
"""
import asyncio
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv
load_dotenv("/home/elliotbot/.config/agency-os/.env")

import asyncpg
from src.config.settings import settings

STAGE1 = os.path.join(os.path.dirname(__file__), "output", "300a_rerun.json")
STAGE2 = os.path.join(os.path.dirname(__file__), "output", "300b_scrape.json")
STAGE3 = os.path.join(os.path.dirname(__file__), "output", "300c_comprehend.json")
STAGE4 = os.path.join(os.path.dirname(__file__), "output", "300d_afford.json")


async def main():
    print("=" * 60)
    print("Backfill #300 test data to business_universe")
    print("=" * 60)

    dsn = settings.database_url.replace("postgresql+asyncpg://", "postgresql://")
    pool = await asyncpg.create_pool(dsn, min_size=5, max_size=25, statement_cache_size=0)
    await pool.execute("SET search_path TO public")

    t0 = time.monotonic()

    # ── Load all stage data ───────────────────────────────────────────────────
    with open(STAGE1) as f: s1 = json.load(f)
    with open(STAGE2) as f: s2 = json.load(f)
    with open(STAGE3) as f: s3 = json.load(f)
    with open(STAGE4) as f: s4 = json.load(f)

    # Index by domain
    s2_by_domain = {r["domain"]: r for r in s2["domains"]}
    s3_by_domain = {r["domain"]: r for r in s3["domains"]}
    s4_by_domain = {r["domain"]: r for r in s4["domains"]}

    # Stage 1 = canonical domain list (1,500)
    all_domains = s1["all_domains"]
    print(f"Stage 1 domains: {len(all_domains)}")
    print(f"Stage 2 domains: {len(s2_by_domain)}")
    print(f"Stage 3 domains: {len(s3_by_domain)}")
    print(f"Stage 4 domains: {len(s4_by_domain)}")
    print()

    # ── Upsert all domains ────────────────────────────────────────────────────
    inserted = 0
    updated  = 0
    errors   = 0
    done     = 0

    async def upsert_domain(item):
        nonlocal inserted, updated, errors, done
        domain = item["domain"]
        cat_code = item.get("category_code")
        cat_name = item.get("category", "")
        organic_etv = item.get("organic_etv", 0.0)

        # Stage 2 enrichment
        s2 = s2_by_domain.get(domain, {})
        scraper = s2.get("scraper_used", "")
        content_len = s2.get("content_length", 0)
        au_pass = s2.get("au_filter") == "pass"
        title = s2.get("title", "")

        # Stage 3 comprehension
        s3 = s3_by_domain.get(domain, {})
        comp = s3.get("comprehension") or {}
        tech = comp.get("technology_signals") or {}
        has_analytics = bool(tech.get("has_analytics"))
        has_ads_tag   = bool(tech.get("has_ads_tag"))
        has_pixel     = bool(tech.get("has_meta_pixel"))
        has_booking   = bool(tech.get("has_booking_system"))
        cms           = tech.get("cms") or ""
        team_size     = comp.get("team_size_indicator", "unknown")
        content_fresh = comp.get("content_freshness", "unknown")
        services      = json.dumps(comp.get("services", []))

        # Stage 4 affordability
        s4r = s4_by_domain.get(domain, {})
        abn_matched   = bool(s4r.get("abn_matched"))
        entity_type   = s4r.get("abn_entity_type")
        gst_reg       = s4r.get("gst_registered")
        afford_score  = s4r.get("afford_score", 0)
        afford_band   = s4r.get("afford_band", "unknown")
        afford_reject = bool(s4r.get("afford_hard_gate"))
        abn_conf      = s4r.get("abn_confidence", "none")

        # Determine furthest stage and status
        if domain in s4_by_domain:
            stage  = 4
            status = "rejected" if afford_reject else "afford_passed"
        elif domain in s3_by_domain:
            stage  = 3
            status = "comprehended"
        elif domain in s2_by_domain:
            stage  = 2
            status = "scraped" if au_pass else "non_au"
        else:
            stage  = 1
            status = "discovered"

        try:
            async with pool.acquire() as conn:
                # Check-then-insert/update pattern (partial unique index on domain)
                existing = await conn.fetchrow(
                    "SELECT id, pipeline_stage FROM business_universe WHERE domain = $1",
                    domain,
                )
                if existing:
                    if stage >= (existing["pipeline_stage"] or 0):
                        await conn.execute(
                            """UPDATE business_universe SET
                                dfs_organic_etv      = COALESCE($2, dfs_organic_etv),
                                pipeline_stage       = $3,
                                pipeline_status      = $4,
                                has_google_analytics = $5,
                                has_google_ads       = $6,
                                has_facebook_pixel   = $7,
                                has_booking_system   = $8,
                                website_cms          = NULLIF($9, ''),
                                abn_matched          = $10,
                                entity_type          = COALESCE(NULLIF($11, ''), entity_type),
                                gst_registered       = COALESCE($12, gst_registered),
                                pipeline_updated_at  = NOW(),
                                updated_at           = NOW()
                            WHERE domain = $1""",
                            domain, organic_etv, stage, status,
                            has_analytics, has_ads_tag, has_pixel, has_booking,
                            cms, abn_matched, entity_type, gst_reg,
                        )
                    updated += 1
                else:
                    # display_name is NOT NULL — use title or domain as fallback
                    display = title or domain
                    await conn.execute(
                        """INSERT INTO business_universe (
                            domain, website, display_name, dfs_organic_etv, pipeline_stage,
                            pipeline_status, has_google_analytics, has_google_ads,
                            has_facebook_pixel, has_booking_system, website_cms,
                            abn_matched, entity_type, gst_registered,
                            discovery_source, discovered_at, pipeline_updated_at,
                            created_at, updated_at
                        ) VALUES (
                            $1, $2, $3, $4, $5,
                            $6, $7, $8,
                            $9, $10, $11,
                            $12, $13, $14,
                            'dfs_domain_metrics', NOW(), NOW(),
                            NOW(), NOW()
                        )""",
                        domain, f"https://{domain}", display, organic_etv, stage,
                        status, has_analytics, has_ads_tag,
                        has_pixel, has_booking, cms,
                        abn_matched, entity_type, gst_reg,
                    )
                    inserted += 1
        except Exception as exc:
            errors += 1
            if errors <= 5:
                print(f"  ERROR {domain}: {exc}")

        done += 1
        if done % 200 == 0:
            elapsed = time.monotonic() - t0
            print(f"  {done}/{len(all_domains)} | {elapsed:.0f}s | inserted={inserted} updated={updated} errors={errors}")

    # Run with concurrency (pool handles DB side)
    sem = asyncio.Semaphore(25)
    async def bounded(item):
        async with sem:
            await upsert_domain(item)

    await asyncio.gather(*[bounded(item) for item in all_domains])

    elapsed = time.monotonic() - t0
    print(f"\n{'='*60}")
    print(f"BACKFILL COMPLETE")
    print(f"  Inserted: {inserted}")
    print(f"  Updated:  {updated}")
    print(f"  Errors:   {errors}")
    print(f"  Total:    {inserted + updated}")
    print(f"  Elapsed:  {elapsed:.2f}s")

    # Verify BU counts
    async with pool.acquire() as conn:
        total_bu = await conn.fetchval("SELECT COUNT(*) FROM business_universe")
        stage_counts = await conn.fetch(
            "SELECT pipeline_stage, pipeline_status, COUNT(*) as n "
            "FROM business_universe "
            "WHERE discovery_source = 'dfs_domain_metrics' "
            "GROUP BY pipeline_stage, pipeline_status ORDER BY pipeline_stage, n DESC"
        )

    print(f"\n  Total BU rows (all sources): {total_bu:,}")
    print(f"  BU rows from this backfill (by stage/status):")
    for r in stage_counts:
        print(f"    stage={r['pipeline_stage']} status={r['pipeline_status']}: {r['n']}")

    await pool.close()


if __name__ == "__main__":
    asyncio.run(main())
