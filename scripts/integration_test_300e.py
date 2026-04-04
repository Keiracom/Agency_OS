"""
DIRECTIVE #300e — Integration Test: Stage 5
Intent Classification + DFS Ads + DFS GMB

517 affordability-passed domains:
  1. DFS Google Ads detection  (~$0.002/domain = ~$1.03)
  2. DFS Maps SERP GMB         (~$0.0035/domain = ~$1.81)
  3. Sonnet intent classify    (~$0.023/domain  = ~$12)
  Total: ~$14 USD

Ramp Sonnet: start 5 concurrent, +5 every 2s until sem=55.
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
from src.clients.dfs_labs_client import DFSLabsClient
from src.pipeline.intelligence import classify_intent, analyse_reviews
from src.utils.asyncpg_connection import get_asyncpg_pool

INPUT_AFFORD   = os.path.join(os.path.dirname(__file__), "output", "300d_afford.json")
INPUT_COMPREHEND = os.path.join(os.path.dirname(__file__), "output", "300c_comprehend.json")
OUTPUT_FILE    = os.path.join(os.path.dirname(__file__), "output", "300e_intent.json")

# Sonnet-4.5 pricing (USD per token)
SONNET_IN_COST  = 3.00 / 1_000_000
SONNET_OUT_COST = 15.0 / 1_000_000

# DFS pricing
DFS_ADS_COST = 0.002
DFS_GMB_COST = 0.0035

# Semaphores
SEM_DFS    = asyncio.Semaphore(28)
SEM_SONNET = asyncio.Semaphore(5)   # starts at 5, ramped up to 55


async def ramp_sonnet():
    """Gradually increase Sonnet semaphore from 5→55, +5 every 2s."""
    global SEM_SONNET
    current = 5
    while current < 55:
        await asyncio.sleep(2)
        current = min(current + 5, 55)
        # Release additional slots into the semaphore
        for _ in range(5):
            SEM_SONNET.release()


async def fetch_ads(dfs: DFSLabsClient, domain: str) -> dict:
    async with SEM_DFS:
        try:
            result = await dfs.ads_search_by_domain(domain)
            return result or {"is_running_ads": False, "ad_count": 0, "formats": [], "first_shown": None, "last_shown": None}
        except Exception as exc:
            return {"is_running_ads": False, "ad_count": 0, "_error": str(exc)}


async def fetch_gmb(dfs: DFSLabsClient, domain: str, company_name: str) -> dict:
    async with SEM_DFS:
        try:
            result = await dfs.maps_search_gmb(company_name or domain)
            return result or {"gmb_found": False}
        except Exception as exc:
            return {"gmb_found": False, "_error": str(exc)}


async def run_intent(domain: str, website_data: dict, gmb_data: dict, ads_data: dict) -> dict:
    async with SEM_SONNET:
        try:
            result = await classify_intent(domain, website_data, gmb_data, ads_data)
            return result
        except Exception as exc:
            return {
                "band": "NOT_TRYING", "score": 0, "confidence": "LOW",
                "evidence": [], "primary_signal": "", "recommended_entry_point": "",
                "_error": str(exc),
            }


async def run_reviews(domain: str, reviews: list) -> dict | None:
    if not reviews:
        return None
    async with SEM_SONNET:
        try:
            return await analyse_reviews(domain, reviews)
        except Exception as exc:
            return {"_error": str(exc)}


async def upsert_domain(pool: asyncpg.Pool, result: dict) -> None:
    """Write Stage 5 results back to business_universe."""
    try:
        async with pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE business_universe SET
                    google_ads_active       = $2,
                    google_ads_count        = $3,
                    gmb_rating              = $4,
                    gmb_review_count        = $5,
                    gmb_enriched_at         = CASE WHEN $6 THEN NOW() ELSE gmb_enriched_at END,
                    intent_band             = $7,
                    intent_score            = $8,
                    intent_evidence         = $9::jsonb,
                    pipeline_stage          = GREATEST(pipeline_stage, 5)
                WHERE domain = $1
                """,
                result["domain"],
                result.get("google_ads_active", False),
                result.get("google_ads_count", 0),
                result.get("gmb_rating"),
                result.get("gmb_review_count", 0),
                result.get("gmb_found", False),
                result.get("intent_band", "NOT_TRYING"),
                result.get("intent_score", 0),
                json.dumps(result.get("evidence", [])),
            )
    except Exception as exc:
        pass  # non-fatal; JSON output is primary record


async def process_domain(
    dfs: DFSLabsClient,
    pool: asyncpg.Pool,
    afford_item: dict,
    comp_item: dict | None,
    done: list,
    total: int,
    t0: float,
) -> dict:
    domain       = afford_item["domain"]
    category     = afford_item.get("category", "")
    comprehension = (comp_item or {}).get("comprehension") or {}

    # Build website_data from Stage 3 comprehension
    website_data = {
        "has_analytics":          (comprehension.get("technology_signals") or {}).get("has_analytics", False),
        "has_ads_tag":            (comprehension.get("technology_signals") or {}).get("has_ads_tag", False),
        "has_meta_pixel":         (comprehension.get("technology_signals") or {}).get("has_meta_pixel", False),
        "has_booking_system":     (comprehension.get("technology_signals") or {}).get("has_booking_system", False),
        "has_conversion_tracking":(comprehension.get("technology_signals") or {}).get("has_conversion_tracking", False),
        "cms":                    (comprehension.get("technology_signals") or {}).get("cms"),
        "services":               comprehension.get("services", []),
        "team_size_indicator":    comprehension.get("team_size_indicator", ""),
    }

    # Derive company name for GMB lookup
    _d = domain[4:] if domain.startswith("www.") else domain
    company_name = _d.split(".")[0].replace("-", " ").title()

    # Run Ads + GMB concurrently, then Sonnet
    ads_task = asyncio.create_task(fetch_ads(dfs, domain))
    gmb_task = asyncio.create_task(fetch_gmb(dfs, domain, company_name))
    ads_data, gmb_data = await asyncio.gather(ads_task, gmb_task)

    # Intent classification
    intent_t0 = time.monotonic()
    intent_result = await run_intent(domain, website_data, gmb_data, ads_data)
    intent_ms = round((time.monotonic() - intent_t0) * 1000)

    # Review analysis (if GMB returned review count > 0 — reviews_text rarely present in maps SERP)
    reviews = gmb_data.get("reviews") or []
    review_analysis = None
    if reviews:
        review_analysis = await run_reviews(domain, reviews)

    # Estimate tokens (intelligence.py uses ~600 max_tokens for classify_intent)
    tokens_in  = intent_result.pop("input_tokens", 800)   # prompt caching estimate
    tokens_out = intent_result.pop("output_tokens", 400)

    out = {
        "domain":            domain,
        "category":          category,
        "google_ads_active": ads_data.get("is_running_ads", False),
        "google_ads_count":  ads_data.get("ad_count", 0),
        "gmb_found":         gmb_data.get("gmb_found", False),
        "gmb_rating":        gmb_data.get("gmb_rating"),
        "gmb_review_count":  gmb_data.get("gmb_review_count", 0),
        "gmb_reviews_text":  bool(reviews),
        "intent_band":       intent_result.get("band", "NOT_TRYING"),
        "intent_score":      intent_result.get("score", 0),
        "evidence":          intent_result.get("evidence", []),
        "review_analysis":   review_analysis,
        "sonnet_tokens_in":  tokens_in,
        "sonnet_tokens_out": tokens_out,
        "dfs_cost_usd":      round(DFS_ADS_COST + DFS_GMB_COST, 4),
        "sonnet_cost_usd":   round(tokens_in * SONNET_IN_COST + tokens_out * SONNET_OUT_COST, 4),
        "_intent_ms":        intent_ms,
        "_ads_error":        ads_data.get("_error"),
        "_gmb_error":        gmb_data.get("_error"),
    }

    # Write to BU
    await upsert_domain(pool, out)

    done[0] += 1
    if done[0] % 25 == 0:
        elapsed = time.monotonic() - t0
        rate = done[0] / elapsed
        eta  = (total - done[0]) / rate if rate > 0 else 0
        print(f"  {done[0]}/{total} | {elapsed:.0f}s elapsed | ETA {eta:.0f}s")

    return out


async def main():
    print("=" * 60)
    print("DIRECTIVE #300e — Stage 5: Intent Classification")
    print("517 domains: DFS Ads + GMB + Sonnet intent")
    print("=" * 60)

    # Load inputs
    with open(INPUT_AFFORD) as f:
        afford_data = json.load(f)
    with open(INPUT_COMPREHEND) as f:
        comp_data = json.load(f)

    # Build passed-domain list and comp lookup
    passed = [d for d in afford_data["domains"] if not d.get("afford_hard_gate")]
    comp_map = {d["domain"]: d for d in comp_data["domains"]}
    print(f"Loaded {len(passed)} affordability-passed domains\n")

    # Init clients
    dfs = DFSLabsClient(
        login=settings.dataforseo_login,
        password=settings.dataforseo_password,
    )
    dsn = settings.database_url.replace("postgresql+asyncpg://", "postgresql://").replace("postgres://", "postgresql://")
    pool = await get_asyncpg_pool(dsn, min_size=1, max_size=50)

    # Start Sonnet ramp task
    ramp_task = asyncio.create_task(ramp_sonnet())

    t0    = time.monotonic()
    done  = [0]
    total = len(passed)

    tasks = [
        process_domain(dfs, pool, item, comp_map.get(item["domain"]), done, total, t0)
        for item in passed
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    ramp_task.cancel()

    elapsed = time.monotonic() - t0
    await dfs.close()
    await pool.close()

    # Normalise exceptions
    clean: list[dict] = []
    errors = 0
    for i, r in enumerate(results):
        if isinstance(r, Exception):
            clean.append({
                "domain":   passed[i]["domain"],
                "category": passed[i].get("category", ""),
                "_exception": str(r),
            })
            errors += 1
        else:
            clean.append(r)

    ok = [r for r in clean if not r.get("_exception")]

    # ── STATS ──
    ads_active   = sum(1 for r in ok if r.get("google_ads_active"))
    ads_inactive = sum(1 for r in ok if not r.get("google_ads_active"))
    gmb_found    = sum(1 for r in ok if r.get("gmb_found"))
    gmb_missing  = sum(1 for r in ok if not r.get("gmb_found"))
    gmb_ratings  = [r["gmb_rating"] for r in ok if r.get("gmb_rating") is not None]
    gmb_avg      = round(sum(gmb_ratings) / len(gmb_ratings), 2) if gmb_ratings else 0
    gmb_reviews  = sum(1 for r in ok if r.get("gmb_reviews_text"))

    band_dist = {"NOT_TRYING": 0, "DABBLING": 0, "TRYING": 0, "STRUGGLING": 0}
    for r in ok:
        b = r.get("intent_band", "NOT_TRYING")
        band_dist[b] = band_dist.get(b, 0) + 1

    score_dist = {"0-5": 0, "6-10": 0, "11-14": 0, "15-18": 0}
    for r in ok:
        s = r.get("intent_score", 0)
        if s <= 5:   score_dist["0-5"]   += 1
        elif s <= 10: score_dist["6-10"]  += 1
        elif s <= 14: score_dist["11-14"] += 1
        else:        score_dist["15-18"] += 1

    cat_bands = {}
    for cat in ["Dental", "Construction", "Legal"]:
        cat_ok = [r for r in ok if r.get("category") == cat]
        cat_bands[cat] = {b: sum(1 for r in cat_ok if r.get("intent_band") == b)
                          for b in ["NOT_TRYING", "DABBLING", "TRYING", "STRUGGLING"]}

    total_dfs_cost    = round(len(ok) * (DFS_ADS_COST + DFS_GMB_COST), 2)
    total_sonnet_cost = round(sum(r.get("sonnet_cost_usd", 0) for r in ok), 2)
    total_cost        = round(total_dfs_cost + total_sonnet_cost, 2)

    # ── 5 EXAMPLES ──
    ex_not_trying  = next((r for r in ok if r.get("intent_band") == "NOT_TRYING" and r.get("evidence")), None)
    ex_dabbling    = next((r for r in ok if r.get("intent_band") == "DABBLING"   and r.get("evidence")), None)
    ex_trying      = next((r for r in ok if r.get("intent_band") == "TRYING"     and r.get("evidence")), None)
    ex_struggling  = next((r for r in ok if r.get("intent_band") == "STRUGGLING" and r.get("evidence")), None)
    ex_reviews     = next((r for r in ok if r.get("gmb_reviews_text") and r.get("review_analysis")), None)

    print()
    print("=" * 60)
    print("=== TASK B REPORT ===")
    print()
    print(f"1. TOTAL PROCESSED: {len(clean)} | ERRORS: {errors}")
    print()
    print(f"2. GOOGLE ADS: active={ads_active} | inactive={ads_inactive}")
    print()
    print(f"3. GMB: found={gmb_found} | not found={gmb_missing}")
    print(f"4. GMB AVERAGE RATING (found): {gmb_avg}")
    print(f"5. GMB REVIEWS WITH TEXT: {gmb_reviews}")
    print()
    print("6. INTENT BAND DISTRIBUTION:")
    for band, count in band_dist.items():
        print(f"   {band}: {count}")
    print()
    print("7. INTENT SCORE DISTRIBUTION:")
    for rng, count in score_dist.items():
        print(f"   {rng}: {count}")
    print()
    print("8. PER-CATEGORY INTENT BREAKDOWN:")
    for cat, bands in cat_bands.items():
        parts = " / ".join(f"{b}={bands[b]}" for b in ["NOT_TRYING","DABBLING","TRYING","STRUGGLING"])
        print(f"   {cat}: {parts}")
    print()
    print(f"9.  TOTAL DFS COST:    ${total_dfs_cost:.2f} USD")
    print(f"10. TOTAL SONNET COST: ${total_sonnet_cost:.2f} USD")
    print(f"11. TOTAL STAGE 5:     ${total_cost:.2f} USD")
    print(f"12. WALL-CLOCK TIME:   {elapsed:.1f}s")
    print()
    print("13. FIVE EXAMPLES:")

    def show(label, r):
        if r is None:
            print(f"\n[{label}]: NOT FOUND IN SAMPLE")
            return
        printable = {k: v for k, v in r.items() if not k.startswith("_")}
        print(f"\n[{label}]")
        print(json.dumps(printable, indent=4, default=str))

    show("NOT_TRYING with evidence (rejected)",     ex_not_trying)
    show("DABBLING with evidence",                  ex_dabbling)
    show("TRYING with evidence",                    ex_trying)
    show("STRUGGLING with evidence",                ex_struggling)
    show("GMB reviews → pain themes",               ex_reviews)

    # ── SAVE ──
    summary = {
        "total": len(clean), "ok": len(ok), "errors": errors,
        "google_ads_active": ads_active, "google_ads_inactive": ads_inactive,
        "gmb_found": gmb_found, "gmb_missing": gmb_missing, "gmb_avg_rating": gmb_avg,
        "gmb_reviews_with_text": gmb_reviews,
        "intent_bands": band_dist,
        "score_dist": score_dist,
        "per_category": cat_bands,
        "dfs_cost_usd": total_dfs_cost,
        "sonnet_cost_usd": total_sonnet_cost,
        "total_cost_usd": total_cost,
        "elapsed_seconds": round(elapsed, 1),
    }

    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, "w") as f:
        json.dump({"stage": "300e_intent", "summary": summary, "domains": clean}, f, indent=2, default=str)
    print(f"\nSaved: {OUTPUT_FILE}")


if __name__ == "__main__":
    asyncio.run(main())
