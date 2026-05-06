"""
DIRECTIVE #300 Stages 9+10
Stage 9: LinkedIn Company Scrape (300i)
Stage 10: LinkedIn DM Profile Scrape (300j)

Stage 9: 370 non-NOT_TRYING domains — re-scrape for linkedin_company URLs, then BD scrape
Stage 10: 260 DM-found domains — BD scrape of dm_linkedin_url

Bright Data: $0.00075/record. GLOBAL_SEM_BRIGHTDATA=15
"""

import asyncio
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv

load_dotenv("/home/elliotbot/.config/agency-os/.env")

from src.config.settings import settings
from src.integrations.httpx_scraper import HttpxScraper
from src.pipeline.social_enrichment import (
    scrape_linkedin_company,
    scrape_linkedin_dm,
    GLOBAL_SEM_BRIGHTDATA,
)
from src.utils.asyncpg_connection import get_asyncpg_pool

INPUT_INTENT = os.path.join(os.path.dirname(__file__), "output", "300e_intent.json")
INPUT_DM = os.path.join(os.path.dirname(__file__), "output", "300f_dm.json")
OUTPUT_CO = os.path.join(os.path.dirname(__file__), "output", "300i_linkedin_co.json")
OUTPUT_DM = os.path.join(os.path.dirname(__file__), "output", "300j_linkedin_dm.json")

BD_COST = 0.00075
SEM_SCRAPE = asyncio.Semaphore(15)


async def live_scrape_linkedin_company(domain: str, scraper: HttpxScraper) -> str | None:
    """Re-scrape domain and extract linkedin_company URL."""
    async with SEM_SCRAPE:
        try:
            result = await scraper.scrape(domain)
            if result and result.get("contact_data"):
                return result["contact_data"].get("linkedin_company")
        except Exception:
            pass
    return None


async def upsert_linkedin(pool, domain: str, co_data: dict | None, dm_data: dict | None) -> None:
    try:
        async with pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE business_universe SET
                    pipeline_stage = GREATEST(pipeline_stage, 9)
                WHERE domain = $1
                """,
                domain,
            )
    except Exception:
        pass


# ── STAGE 9 ───────────────────────────────────────────────────────────────────


async def run_stage9(scraper: HttpxScraper, pool) -> list[dict]:
    print("=" * 60)
    print("STAGE 9 — LinkedIn Company Scrape")
    print("=" * 60)

    with open(INPUT_INTENT) as f:
        intent_data = json.load(f)

    prospects = [d for d in intent_data["domains"] if d.get("intent_band") != "NOT_TRYING"]
    print(f"Loaded {len(prospects)} non-NOT_TRYING domains")
    print("Re-scraping to collect linkedin_company URLs...")

    t_scrape = time.monotonic()
    scrape_tasks = [live_scrape_linkedin_company(p["domain"], scraper) for p in prospects]
    linkedin_co_urls = await asyncio.gather(*scrape_tasks)
    print(
        f"Scrape done: {time.monotonic() - t_scrape:.1f}s | "
        f"Company LinkedIn found: {sum(1 for u in linkedin_co_urls if u)}/{len(prospects)}\n"
    )

    # Only scrape domains that have a company LinkedIn URL
    to_scrape = [
        (prospects[i], linkedin_co_urls[i]) for i in range(len(prospects)) if linkedin_co_urls[i]
    ]
    print(f"Running Bright Data on {len(to_scrape)} domains with company LinkedIn URLs...")

    t0 = time.monotonic()
    done = [0]

    async def process_co(p: dict, co_url: str) -> dict:
        domain = p["domain"]
        category = p.get("category", "")
        result = await scrape_linkedin_company(co_url, domain)
        done[0] += 1
        if done[0] % 10 == 0:
            print(f"  {done[0]}/{len(to_scrape)} | {time.monotonic() - t0:.0f}s")
        return {
            "domain": domain,
            "category": category,
            "intent_band": p.get("intent_band", ""),
            "linkedin_company_url": co_url,
            "scraped": result is not None,
            "data": result,
            "bd_cost_usd": BD_COST if result else 0.0,
        }

    tasks = [process_co(p, url) for p, url in to_scrape]
    results_scraped = await asyncio.gather(*tasks, return_exceptions=True)
    elapsed = time.monotonic() - t0

    # Normalise
    results: list[dict] = []
    for i, r in enumerate(results_scraped):
        if isinstance(r, Exception):
            results.append({"domain": to_scrape[i][0]["domain"], "_exception": str(r)})
        else:
            results.append(r)

    # Add not-scraped domains (no company URL)
    no_url = [
        {
            "domain": p["domain"],
            "category": p.get("category", ""),
            "intent_band": p.get("intent_band", ""),
            "linkedin_company_url": None,
            "scraped": False,
            "data": None,
            "bd_cost_usd": 0.0,
        }
        for p in prospects
        if not linkedin_co_urls[prospects.index(p)]
    ]
    all_results = results + no_url

    # Stats
    ok = [r for r in results if not r.get("_exception")]
    with_data = [r for r in ok if r.get("data")]
    errors = [r for r in results if r.get("_exception")]
    total_cost = round(sum(r.get("bd_cost_usd", 0) for r in ok), 4)

    cat_stats = {}
    for cat in ["Dental", "Construction", "Legal"]:
        cat_r = [r for r in results if r.get("category") == cat]
        cat_data = sum(1 for r in cat_r if r.get("data"))
        cat_stats[cat] = {"processed": len(cat_r), "with_data": cat_data}

    print()
    print("── STAGE 9 REPORT ──")
    print(
        f"1. Processed: {len(results)} with URL | No URL (skipped): {len(no_url)} | Errors: {len(errors)}"
    )
    print(
        f"2. Hit rate: {len(with_data)}/{len(results)} = {len(with_data) / max(len(results), 1) * 100:.1f}%"
    )
    print("3. Per-category:")
    for cat, s in cat_stats.items():
        print(f"   {cat}: processed={s['processed']} with_data={s['with_data']}")
    print(f"4. Cost: ${total_cost:.4f} USD")
    print(f"5. Wall-clock: {elapsed:.1f}s")
    print()
    print("6. Three examples:")

    ex_recent = next((r for r in with_data if r.get("data", {}).get("recent_posts")), None)
    ex_dormant = next(
        (r for r in with_data if r.get("data", {}).get("activity_level") in ("lurker", "inactive")),
        None,
    )
    ex_failed = next(
        (r for r in results if not r.get("data") and r.get("linkedin_company_url")), None
    )

    def show(label, r):
        if r is None:
            print(f"\n[{label}]: NOT FOUND")
            return
        print(f"\n[{label}]")
        print(
            json.dumps({k: v for k, v in r.items() if not k.startswith("_")}, indent=2, default=str)
        )

    show("With recent posts", ex_recent)
    show("Dormant company", ex_dormant)
    show("Scrape failed (had URL but no data)", ex_failed)

    os.makedirs(os.path.dirname(OUTPUT_CO), exist_ok=True)
    with open(OUTPUT_CO, "w") as f:
        json.dump(
            {
                "stage": "300i_linkedin_co",
                "summary": {
                    "processed_with_url": len(results),
                    "no_url": len(no_url),
                    "with_data": len(with_data),
                    "errors": len(errors),
                    "total_cost_usd": total_cost,
                    "elapsed_seconds": round(elapsed, 1),
                    "per_category": cat_stats,
                },
                "domains": all_results,
            },
            f,
            indent=2,
            default=str,
        )
    print(f"\nSaved: {OUTPUT_CO}")
    return all_results


# ── STAGE 10 ──────────────────────────────────────────────────────────────────


async def run_stage10(pool) -> list[dict]:
    print()
    print("=" * 60)
    print("STAGE 10 — LinkedIn DM Profile Scrape")
    print("=" * 60)

    with open(INPUT_DM) as f:
        dm_data = json.load(f)

    dm_found = [d for d in dm_data["domains"] if d.get("dm_found") and d.get("dm_linkedin_url")]
    print(f"Loaded {len(dm_found)} DM-found domains with LinkedIn URLs")

    t0 = time.monotonic()
    done = [0]

    async def process_dm(p: dict) -> dict:
        domain = p["domain"]
        profile_url = p["dm_linkedin_url"]
        result = await scrape_linkedin_dm(profile_url, domain)
        done[0] += 1
        if done[0] % 20 == 0:
            print(f"  {done[0]}/{len(dm_found)} | {time.monotonic() - t0:.0f}s")
        return {
            "domain": domain,
            "category": p.get("category", ""),
            "intent_band": p.get("intent_band", ""),
            "dm_name": p.get("dm_name"),
            "dm_title": p.get("dm_title"),
            "dm_linkedin_url": profile_url,
            "scraped": result is not None,
            "data": result,
            "bd_cost_usd": BD_COST if result else 0.0,
        }

    tasks = [process_dm(p) for p in dm_found]
    raw_results = await asyncio.gather(*tasks, return_exceptions=True)
    elapsed = time.monotonic() - t0

    results: list[dict] = []
    for i, r in enumerate(raw_results):
        if isinstance(r, Exception):
            results.append({"domain": dm_found[i]["domain"], "_exception": str(r)})
        else:
            results.append(r)

    ok = [r for r in results if not r.get("_exception")]
    with_data = [r for r in ok if r.get("data")]
    errors = [r for r in results if r.get("_exception")]
    total_cost = round(sum(r.get("bd_cost_usd", 0) for r in ok), 4)

    cat_stats = {}
    for cat in ["Dental", "Construction", "Legal"]:
        cat_r = [r for r in ok if r.get("category") == cat]
        cat_data = sum(1 for r in cat_r if r.get("data"))
        cat_stats[cat] = {"processed": len(cat_r), "with_data": cat_data}

    print()
    print("── STAGE 10 REPORT ──")
    print(f"1. Processed: {len(results)} | Errors: {len(errors)}")
    print(
        f"2. Hit rate: {len(with_data)}/{len(results)} = {len(with_data) / max(len(results), 1) * 100:.1f}%"
    )
    print("3. Per-category:")
    for cat, s in cat_stats.items():
        print(f"   {cat}: processed={s['processed']} with_data={s['with_data']}")
    print(f"4. Cost: ${total_cost:.4f} USD")
    print(f"5. Wall-clock: {elapsed:.1f}s")
    print()
    print("6. Three examples:")

    ex_active = next(
        (r for r in with_data if r.get("data", {}).get("activity_level") == "active"), None
    )
    ex_lurker = next(
        (r for r in with_data if r.get("data", {}).get("activity_level") == "lurker"), None
    )
    ex_founder = next(
        (
            r
            for r in with_data
            if any(
                e.get("title", "").lower() in ("owner", "founder", "co-founder", "principal")
                for e in (r.get("data", {}).get("career_history") or [])
                if e.get("current")
            )
        ),
        None,
    )

    def show(label, r):
        if r is None:
            print(f"\n[{label}]: NOT FOUND")
            return
        print(f"\n[{label}]")
        print(
            json.dumps({k: v for k, v in r.items() if not k.startswith("_")}, indent=2, default=str)
        )

    show("Recent activity (active)", ex_active)
    show("Lurker", ex_lurker)
    show("Founder/owner in career history", ex_founder)

    os.makedirs(os.path.dirname(OUTPUT_DM), exist_ok=True)
    with open(OUTPUT_DM, "w") as f:
        json.dump(
            {
                "stage": "300j_linkedin_dm",
                "summary": {
                    "processed": len(results),
                    "with_data": len(with_data),
                    "errors": len(errors),
                    "total_cost_usd": total_cost,
                    "elapsed_seconds": round(elapsed, 1),
                    "per_category": cat_stats,
                },
                "domains": results,
            },
            f,
            indent=2,
            default=str,
        )
    print(f"\nSaved: {OUTPUT_DM}")
    return results


async def main():
    dsn = settings.database_url.replace("postgresql+asyncpg://", "postgresql://").replace(
        "postgres://", "postgresql://"
    )
    pool = await get_asyncpg_pool(dsn, min_size=1, max_size=10)
    scraper = HttpxScraper()

    try:
        await run_stage9(scraper, pool)
        await run_stage10(pool)
    finally:
        await scraper.close()
        await pool.close()

    print("\n✅ Stages 9+10 complete.")


if __name__ == "__main__":
    asyncio.run(main())
