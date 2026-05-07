"""
DIRECTIVE #300f — Integration Test: Stage 6
DM Identification

370 non-NOT_TRYING prospects from Stage 5.
DFS SERP LinkedIn lookup per domain.
Cost: ~$3.70 DFS (370 × $0.01/call).
"""

import asyncio
import json
import os
import re
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv

load_dotenv("/home/elliotbot/.config/agency-os/.env")

import asyncpg
from src.config.settings import settings
from src.clients.dfs_labs_client import DFSLabsClient
from src.integrations.bright_data_linkedin_client import DM_TITLE_PRIORITY
from src.utils.asyncpg_connection import get_asyncpg_pool

INPUT_INTENT = os.path.join(os.path.dirname(__file__), "output", "300e_intent.json")
OUTPUT_FILE = os.path.join(os.path.dirname(__file__), "output", "300f_dm.json")

DFS_COST_PER_CALL = 0.01  # search_linkedin_people = $0.01

SEM_DFS = asyncio.Semaphore(28)

# DM title keywords that suggest NOT the decision maker
NON_DM_TITLES = {
    "coordinator",
    "assistant",
    "receptionist",
    "admin",
    "administrator",
    "secretary",
    "clerk",
    "junior",
    "intern",
    "trainee",
    "graduate",
    "marketing coordinator",
    "marketing manager",
    "account manager",
    "social media",
    "content",
    "hr",
    "human resources",
}

HIGH_CONFIDENCE_TITLES = {
    "owner",
    "founder",
    "co-founder",
    "director",
    "principal",
    "managing director",
    "managing partner",
    "ceo",
    "chief executive",
    "proprietor",
    "partner",
    "president",
    "general manager",
}


def _derive_company_name(domain: str, display_name: str | None, legal_name: str | None) -> str:
    """Best available company name for LinkedIn search query."""
    if display_name and len(display_name.strip()) > 3:
        return display_name.strip()
    if legal_name and len(legal_name.strip()) > 3:
        # Strip PTY LTD etc
        name = re.sub(
            r"\s*(PTY\.?\s*LTD\.?|PROPRIETARY\s+LIMITED|PTY\s+LIMITED|LIMITED|LTD\.?|TRUST)\s*$",
            "",
            legal_name.strip(),
            flags=re.IGNORECASE,
        ).strip()
        if len(name) > 3:
            return name
    # Fall back to domain stem
    stem = domain.lstrip("www.").split(".")[0].replace("-", " ").title()
    return stem


def _is_au_profile(snippet: str, linkedin_url: str) -> bool:
    """Check if a LinkedIn profile looks Australian."""
    if "au.linkedin.com" in linkedin_url:
        return True
    AU_SIGNALS = re.compile(
        r"\b(NSW|VIC|QLD|SA|WA|TAS|NT|ACT|Sydney|Melbourne|Brisbane|Perth|"
        r"Adelaide|Hobart|Darwin|Canberra|Australia|Australian)\b",
        re.IGNORECASE,
    )
    return bool(AU_SIGNALS.search(snippet or ""))


def _pick_best_dm(people: list[dict]) -> dict | None:
    """Pick best DM from SERP results using title priority list."""
    if not people:
        return None

    # Filter to AU profiles first
    au_people = [
        p for p in people if _is_au_profile(p.get("snippet", ""), p.get("linkedin_url", ""))
    ]
    candidates = au_people if au_people else people

    best = None
    best_idx = len(DM_TITLE_PRIORITY) + 1

    for p in candidates:
        title_lower = (p.get("title") or "").lower()
        idx = len(DM_TITLE_PRIORITY)  # no match = lowest priority
        for i, kw in enumerate(DM_TITLE_PRIORITY):
            if kw in title_lower:
                idx = i
                break
        if idx < best_idx:
            best_idx = idx
            best = p

    return best


async def lookup_dm(
    dfs: DFSLabsClient,
    domain: str,
    company_name: str,
    pool: asyncpg.Pool,
    done: list,
    total: int,
    t0: float,
) -> dict:
    search_query = f"{company_name} owner OR director OR founder site:linkedin.com"
    t_start = time.monotonic()

    async with SEM_DFS:
        try:
            people = await dfs.search_linkedin_people(company_name)
        except Exception as exc:
            people = []
            error = str(exc)
        else:
            error = None

    elapsed_ms = round((time.monotonic() - t_start) * 1000)

    dm = _pick_best_dm(people) if people else None

    # Check if the title suggests NOT the decision maker
    title_lower = (dm.get("title") or "").lower() if dm else ""
    is_non_dm = any(t in title_lower for t in NON_DM_TITLES) and not any(
        t in title_lower for t in HIGH_CONFIDENCE_TITLES
    )

    result = {
        "domain": domain,
        "dm_found": dm is not None,
        "dm_name": dm["name"] if dm else None,
        "dm_title": dm["title"] if dm else None,
        "dm_linkedin_url": dm["linkedin_url"] if dm else None,
        "dm_search_query": search_query,
        "dm_source": "serp_linkedin",
        "dm_is_non_dm": is_non_dm,  # title suggests not a decision maker
        "candidates_found": len(people),
        "dfs_cost_usd": DFS_COST_PER_CALL,
        "response_time_ms": elapsed_ms,
        "_error": error,
    }

    # Upsert to BU
    if dm:
        try:
            async with pool.acquire() as conn:
                await conn.execute(
                    """
                    UPDATE business_universe SET
                        dm_name        = $2,
                        dm_title       = $3,
                        dm_linkedin_url = $4,
                        dm_source      = $5,
                        dm_found_at    = NOW(),
                        pipeline_stage = GREATEST(pipeline_stage, 6)
                    WHERE domain = $1
                    """,
                    domain,
                    dm["name"],
                    dm["title"],
                    dm["linkedin_url"],
                    "serp_linkedin",
                )
        except Exception:
            pass

    done[0] += 1
    if done[0] % 25 == 0:
        elapsed = time.monotonic() - t0
        rate = done[0] / elapsed
        eta = (total - done[0]) / rate if rate > 0 else 0
        found = sum(1 for _ in range(done[0]))  # just progress
        print(f"  {done[0]}/{total} | {elapsed:.0f}s elapsed | ETA {eta:.0f}s")

    return result


async def main():
    print("=" * 60)
    print("DIRECTIVE #300f — Stage 6: DM Identification")
    print("370 non-NOT_TRYING domains: DFS SERP LinkedIn")
    print("=" * 60)

    with open(INPUT_INTENT) as f:
        intent_data = json.load(f)

    prospects = [d for d in intent_data["domains"] if d.get("intent_band") != "NOT_TRYING"]
    print(f"Loaded {len(prospects)} non-NOT_TRYING domains\n")

    # Init clients
    dfs = DFSLabsClient(
        login=settings.dataforseo_login,
        password=settings.dataforseo_password,
    )
    dsn = settings.database_url.replace("postgresql+asyncpg://", "postgresql://").replace(
        "postgres://", "postgresql://"
    )
    pool = await get_asyncpg_pool(dsn, min_size=1, max_size=20)

    # Get display_name + legal_name from BU for all 370 domains
    domains_list = [p["domain"] for p in prospects]
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT domain, display_name, legal_name FROM business_universe WHERE domain = ANY($1::text[])",
            domains_list,
        )
    bu_names = {r["domain"]: (r["display_name"], r["legal_name"]) for r in rows}

    # Build per-domain company names and category/band context
    enriched = []
    for p in prospects:
        domain = p["domain"]
        display, legal = bu_names.get(domain, (None, None))
        company_name = _derive_company_name(domain, display, legal)
        enriched.append(
            {
                **p,
                "company_name": company_name,
            }
        )

    t0 = time.monotonic()
    done = [0]
    total = len(enriched)

    tasks = [
        lookup_dm(dfs, item["domain"], item["company_name"], pool, done, total, t0)
        for item in enriched
    ]
    raw_results = await asyncio.gather(*tasks, return_exceptions=True)

    elapsed = time.monotonic() - t0
    await dfs.close()
    await pool.close()

    # Normalise + merge category/band back in
    enrich_map = {item["domain"]: item for item in enriched}
    results: list[dict] = []
    errors = 0
    for i, r in enumerate(raw_results):
        domain = enriched[i]["domain"]
        ctx = enrich_map[domain]
        if isinstance(r, Exception):
            results.append(
                {
                    "domain": domain,
                    "category": ctx.get("category", ""),
                    "intent_band": ctx.get("intent_band", ""),
                    "intent_score": ctx.get("intent_score", 0),
                    "_exception": str(r),
                }
            )
            errors += 1
        else:
            results.append(
                {
                    "domain": r["domain"],
                    "category": ctx.get("category", ""),
                    "intent_band": ctx.get("intent_band", ""),
                    "intent_score": ctx.get("intent_score", 0),
                    "dm_found": r["dm_found"],
                    "dm_name": r["dm_name"],
                    "dm_title": r["dm_title"],
                    "dm_linkedin_url": r["dm_linkedin_url"],
                    "dm_search_query": r["dm_search_query"],
                    "dm_source": r["dm_source"],
                    "dm_is_non_dm": r.get("dm_is_non_dm", False),
                    "candidates_found": r.get("candidates_found", 0),
                    "dfs_cost_usd": r["dfs_cost_usd"],
                    "response_time_ms": r["response_time_ms"],
                    "_error": r.get("_error"),
                }
            )

    ok = [r for r in results if not r.get("_exception")]

    # ── STATS ──
    found_results = [r for r in ok if r.get("dm_found")]
    not_found = [r for r in ok if not r.get("dm_found")]
    hit_rate = round(len(found_results) / len(ok) * 100, 1) if ok else 0

    cat_stats = {}
    for cat in ["Dental", "Construction", "Legal"]:
        cat_ok = [r for r in ok if r.get("category") == cat]
        cat_found = sum(1 for r in cat_ok if r.get("dm_found"))
        cat_stats[cat] = {
            "found": cat_found,
            "not_found": len(cat_ok) - cat_found,
            "hit_rate": round(cat_found / len(cat_ok) * 100, 1) if cat_ok else 0,
        }

    band_stats = {}
    for band in ["STRUGGLING", "TRYING", "DABBLING"]:
        band_ok = [r for r in ok if r.get("intent_band") == band]
        band_found = sum(1 for r in band_ok if r.get("dm_found"))
        band_stats[band] = {
            "found": band_found,
            "not_found": len(band_ok) - band_found,
        }

    total_dfs_cost = round(len(ok) * DFS_COST_PER_CALL, 2)

    # Non-DM titles
    non_dm_examples = [r for r in found_results if r.get("dm_is_non_dm")]

    # ── 5 EXAMPLES ──
    ex_dental_high = next(
        (
            r
            for r in found_results
            if r.get("category") == "Dental" and r.get("intent_band") in ("STRUGGLING", "TRYING")
        ),
        None,
    )
    ex_construction = next((r for r in found_results if r.get("category") == "Construction"), None)
    ex_legal = next((r for r in found_results if r.get("category") == "Legal"), None)
    ex_not_found = next((r for r in not_found), None)
    ex_non_dm = non_dm_examples[0] if non_dm_examples else None

    print()
    print("=" * 60)
    print("=== TASK B REPORT ===")
    print()
    print(f"1. TOTAL PROCESSED: {len(results)} | ERRORS: {errors}")
    print()
    print(f"2. DM FOUND: {len(found_results)} | NOT FOUND: {len(not_found)}")
    print(f"3. HIT RATE: {hit_rate}%")
    print()
    print("4. PER-CATEGORY:")
    for cat, s in cat_stats.items():
        print(
            f"   {cat}: found={s['found']} / not_found={s['not_found']} / hit_rate={s['hit_rate']}%"
        )
    print()
    print("5. PER INTENT BAND:")
    for band, s in band_stats.items():
        print(f"   {band}: found={s['found']} / not_found={s['not_found']}")
    print()
    print(f"6. DFS COST: ${total_dfs_cost:.2f} USD ({len(ok)} × ${DFS_COST_PER_CALL})")
    print(f"7. WALL-CLOCK: {elapsed:.1f}s")
    print()
    print("8. FIVE EXAMPLES:")

    def show(label, r):
        if r is None:
            print(f"\n[{label}]: NOT FOUND IN SAMPLE")
            return
        printable = {k: v for k, v in r.items() if not k.startswith("_")}
        print(f"\n[{label}]")
        print(json.dumps(printable, indent=4, default=str))

    show("DENTAL DM FOUND (STRUGGLING/TRYING)", ex_dental_high)
    show("CONSTRUCTION DM FOUND", ex_construction)
    show("LEGAL DM FOUND", ex_legal)
    show("DM NOT FOUND (search query + reason)", ex_not_found)
    show("NON-DM TITLE (not decision maker)", ex_non_dm)

    # ── SAVE ──
    summary = {
        "total": len(results),
        "ok": len(ok),
        "errors": errors,
        "dm_found": len(found_results),
        "dm_not_found": len(not_found),
        "hit_rate_pct": hit_rate,
        "per_category": cat_stats,
        "per_band": band_stats,
        "non_dm_title_count": len(non_dm_examples),
        "dfs_cost_usd": total_dfs_cost,
        "elapsed_seconds": round(elapsed, 1),
    }

    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, "w") as f:
        json.dump(
            {"stage": "300f_dm", "summary": summary, "domains": results}, f, indent=2, default=str
        )
    print(f"\nSaved: {OUTPUT_FILE}")


if __name__ == "__main__":
    asyncio.run(main())
