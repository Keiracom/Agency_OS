"""
DIRECTIVE #304 — Keyword Discovery Test
Track B validation: DFS keyword suggestions + SERP domain matrix

Tests whether keyword-based SERP discovery finds AU SMBs that
category-based discovery (Track A) misses.

Estimated cost: ~$0.25 USD
Output: scripts/output/304_keywords.json
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv

load_dotenv("/home/elliotbot/.config/agency-os/.env")

import httpx

DATAFORSEO_LOGIN = os.getenv("DATAFORSEO_LOGIN")
DATAFORSEO_PASSWORD = os.getenv("DATAFORSEO_PASSWORD")

import base64

_AUTH = "Basic " + base64.b64encode(f"{DATAFORSEO_LOGIN}:{DATAFORSEO_PASSWORD}".encode()).decode()
HEADERS = {"Authorization": _AUTH, "Content-Type": "application/json"}
DFS_BASE = "https://api.dataforseo.com"

OUT_DIR = os.path.join(os.path.dirname(__file__), "output")
OUTPUT = os.path.join(OUT_DIR, "304_keywords.json")

SEED_KEYWORDS = [
    "dentist sydney",
    "plumber emergency",
    "family lawyer",
    "personal trainer near me",
    "accountant small business",
]

# ── Helpers ───────────────────────────────────────────────────────────────────


def _is_au_domain(domain: str) -> bool:
    return (
        domain.endswith(".com.au")
        or domain.endswith(".net.au")
        or domain.endswith(".org.au")
        or domain.endswith(".edu.au")
        or domain.endswith(".gov.au")
        or ".au/" in domain
    )


async def dfs_post(client: httpx.AsyncClient, endpoint: str, payload: list) -> dict:
    resp = await client.post(
        f"{DFS_BASE}{endpoint}",
        headers=HEADERS,
        json=payload,
        timeout=60,
    )
    resp.raise_for_status()
    data = resp.json()
    tasks = data.get("tasks") or []
    if not tasks:
        return {}
    task = tasks[0]
    result = (task.get("result") or [{}])[0]
    return result


# ── Task A: Keyword Suggestions ───────────────────────────────────────────────


async def task_a(client: httpx.AsyncClient) -> dict:
    """
    Call DFS keywords_for_keywords for 5 seed keywords.
    Endpoint: /v3/keywords_data/google_ads/keywords_for_keywords/live
    """
    print("\n" + "=" * 60)
    print("TASK A — Keyword Suggestions")
    print("=" * 60)

    results = {}
    total_cost = 0.0
    COST_PER_CALL = 0.01  # keywords_for_keywords: $0.01/task

    for seed in SEED_KEYWORDS:
        print(f"\n  Seed: '{seed}'", flush=True)
        try:
            # DFS Labs keyword_suggestions (not google_ads keywords_for_keywords)
            payload = [
                {
                    "keyword": seed,
                    "location_code": 2036,
                    "language_code": "en",
                    "limit": 50,
                }
            ]
            result = await dfs_post(
                client,
                "/v3/dataforseo_labs/google/keyword_suggestions/live",
                payload,
            )
            items = result.get("items") or []
            total_cost += COST_PER_CALL

            # Sort by search_volume descending
            items_sorted = sorted(
                items,
                key=lambda x: (x.get("keyword_info") or {}).get("search_volume") or 0,
                reverse=True,
            )
            top10 = []
            for item in items_sorted[:10]:
                ki = item.get("keyword_info") or {}
                top10.append(
                    {
                        "keyword": item.get("keyword"),
                        "search_volume": ki.get("search_volume"),
                        "cpc": ki.get("cpc"),
                        "competition": ki.get("competition"),
                    }
                )

            results[seed] = {
                "total_returned": len(items),
                "top10": top10,
                "all_keywords": [
                    {
                        "keyword": i.get("keyword"),
                        "search_volume": (i.get("keyword_info") or {}).get("search_volume") or 0,
                    }
                    for i in items_sorted
                ],
            }

            print(f"    Returned: {len(items)} keywords", flush=True)
            if top10:
                print(f"    Top 3: {[t['keyword'] for t in top10[:3]]}", flush=True)
            else:
                print(f"    ⚠️  ZERO results returned", flush=True)

        except Exception as e:
            print(f"    ERROR: {e}", flush=True)
            results[seed] = {"error": str(e), "total_returned": 0, "top10": [], "all_keywords": []}

        await asyncio.sleep(0.5)

    return {"seeds": results, "cost_usd": total_cost}


# ── Task B: SERP Scraping ─────────────────────────────────────────────────────


async def task_b(client: httpx.AsyncClient, task_a_results: dict) -> dict:
    """
    Pick top 20 keywords by volume from Task A, run SERP for each.
    Endpoint: /v3/serp/google/organic/live/advanced
    """
    print("\n" + "=" * 60)
    print("TASK B — SERP Scraping (top 20 keywords)")
    print("=" * 60)

    # Collect all keywords across seeds, deduplicate
    all_kw: dict[str, int] = {}
    for seed_data in task_a_results["seeds"].values():
        for kw in seed_data.get("all_keywords", []):
            kw_text = kw.get("keyword", "")
            vol = kw.get("search_volume") or 0
            if kw_text and vol > 0:
                if kw_text not in all_kw or vol > all_kw[kw_text]:
                    all_kw[kw_text] = vol

    # Sort and take top 20
    top20 = sorted(all_kw.items(), key=lambda x: -x[1])[:20]
    print(f"\n  Selected {len(top20)} keywords for SERP test", flush=True)
    for kw, vol in top20:
        print(f"    '{kw}' — vol {vol}", flush=True)

    COST_PER_CALL = 0.01  # SERP advanced depth=50
    total_cost = 0.0
    serp_results = {}

    for kw, vol in top20:
        print(f"\n  SERP: '{kw}' (vol {vol})", flush=True)
        try:
            payload = [
                {
                    "keyword": kw,
                    "location_code": 2036,
                    "language_code": "en",
                    "depth": 50,
                    "se_domain": "google.com.au",
                }
            ]
            result = await dfs_post(
                client,
                "/v3/serp/google/organic/live/advanced",
                payload,
            )
            items = result.get("items") or []
            total_cost += COST_PER_CALL

            # Extract organic results
            organic = [i for i in items if i.get("type") == "organic"]
            top10_domains = []
            for item in organic[:10]:
                domain = item.get("domain", "")
                top10_domains.append(
                    {
                        "position": item.get("rank_absolute"),
                        "domain": domain,
                        "url": item.get("url"),
                        "title": item.get("title", "")[:80],
                        "is_au": _is_au_domain(domain),
                    }
                )

            au_count = sum(1 for i in organic if _is_au_domain(i.get("domain", "")))

            serp_results[kw] = {
                "volume": vol,
                "total_items": len(items),
                "organic_count": len(organic),
                "au_domain_count": au_count,
                "top10": top10_domains,
                "all_organic": [
                    {
                        "position": i.get("rank_absolute"),
                        "domain": i.get("domain", ""),
                        "is_au": _is_au_domain(i.get("domain", "")),
                    }
                    for i in organic
                ],
            }

            print(f"    Organic results: {len(organic)} | AU domains: {au_count}", flush=True)

        except Exception as e:
            print(f"    ERROR: {e}", flush=True)
            serp_results[kw] = {"error": str(e), "volume": vol}

        await asyncio.sleep(0.3)

    return {"keywords": serp_results, "cost_usd": total_cost}


# ── Task C: Domain-Keyword Matrix ─────────────────────────────────────────────


def task_c(task_b_results: dict) -> dict:
    """Build domain → keyword count matrix from SERP results."""
    print("\n" + "=" * 60)
    print("TASK C — Domain-Keyword Matrix")
    print("=" * 60)

    domain_data: dict[str, dict] = {}

    for kw, kw_data in task_b_results["keywords"].items():
        if "error" in kw_data:
            continue
        for item in kw_data.get("all_organic", []):
            domain = item.get("domain", "")
            pos = item.get("position") or 99
            if not domain:
                continue
            if domain not in domain_data:
                domain_data[domain] = {
                    "domain": domain,
                    "is_au": item.get("is_au", False),
                    "keywords": [],
                    "positions": [],
                    "best_keyword": None,
                    "best_position": 99,
                }
            domain_data[domain]["keywords"].append(kw)
            domain_data[domain]["positions"].append(pos)
            if pos < domain_data[domain]["best_position"]:
                domain_data[domain]["best_position"] = pos
                domain_data[domain]["best_keyword"] = kw

    # Compute averages
    for d in domain_data.values():
        d["keyword_count"] = len(d["keywords"])
        d["avg_position"] = (
            round(sum(d["positions"]) / len(d["positions"]), 1) if d["positions"] else 99
        )

    # Sort by keyword count desc
    sorted_domains = sorted(domain_data.values(), key=lambda x: -x["keyword_count"])
    top20 = sorted_domains[:20]
    au_domains = [d for d in sorted_domains if d["is_au"]]

    print(f"\n  Total unique domains: {len(domain_data)}")
    print(f"  AU domains: {len(au_domains)}")
    print(f"\n  Top 20 by keyword count:")
    for d in top20:
        au_flag = "🇦🇺" if d["is_au"] else "  "
        print(
            f"    {au_flag} {d['domain'][:45]:<45} kws={d['keyword_count']} avg_pos={d['avg_position']} best='{d['best_keyword']}'@{d['best_position']}"
        )

    return {
        "total_unique_domains": len(domain_data),
        "au_domain_count": len(au_domains),
        "all_domains": sorted_domains,
        "top20": top20,
    }


# ── Task D: Overlap Analysis ──────────────────────────────────────────────────


async def task_d(client: httpx.AsyncClient, matrix_domains: list[dict]) -> dict:
    """
    Pull a small category discovery batch and compare overlap.
    Fetches 100 AU dental domains via domain_metrics_by_categories.
    """
    print("\n" + "=" * 60)
    print("TASK D — Overlap Analysis")
    print("=" * 60)

    keyword_domains = {d["domain"] for d in matrix_domains}
    category_domains: set[str] = set()

    # Pull a batch of category domains (dental AU) for comparison
    COST_PER_CALL = 0.10  # $0.001/domain × 100
    try:
        # Use category code 10514 (dental)
        today = __import__("datetime").date.today()
        first_date = str(today - __import__("datetime").timedelta(days=180))
        second_date = str(today)

        payload = [
            {
                "category_codes": [10514],
                "location_code": 2036,
                "language_code": "en",
                "first_date": first_date,
                "second_date": second_date,
                "filters": [
                    ["metrics.organic.etv", ">", 0],
                ],
                "order_by": ["metrics.organic.etv,desc"],
                "limit": 100,
            }
        ]
        result = await dfs_post(
            client,
            "/v3/dataforseo_labs/google/domain_metrics_by_categories/live",
            payload,
        )
        items = result.get("items") or []
        for item in items:
            domain = item.get("domain", "")
            if domain:
                category_domains.add(domain)
        print(
            f"\n  Category discovery (dental, top 100): {len(category_domains)} domains", flush=True
        )
    except Exception as e:
        print(f"  Category pull failed: {e}", flush=True)

    overlap = keyword_domains & category_domains
    keyword_only = keyword_domains - category_domains
    au_keyword_only = {d for d in keyword_only if _is_au_domain(d)}

    print(f"  Keyword discovery unique domains: {len(keyword_domains)}")
    print(f"  Overlap with category: {len(overlap)}")
    print(f"  Keyword-only (new): {len(keyword_only)}")
    print(f"  Keyword-only AU (.com.au etc): {len(au_keyword_only)}")

    return {
        "keyword_domain_count": len(keyword_domains),
        "category_domain_count": len(category_domains),
        "overlap_count": len(overlap),
        "overlap_domains": list(overlap),
        "keyword_only_count": len(keyword_only),
        "keyword_only_au_count": len(au_keyword_only),
        "keyword_only_au_domains": sorted(au_keyword_only),
        "cost_usd": COST_PER_CALL if category_domains else 0,
    }


# ── Main ──────────────────────────────────────────────────────────────────────


async def main():
    print("=" * 60)
    print("DIRECTIVE #304 — Keyword Discovery Test")
    print("Track B validation: DFS keyword SERP vs category discovery")
    print("=" * 60)
    print(f"Login: {DATAFORSEO_LOGIN}")

    t0 = time.monotonic()

    async with httpx.AsyncClient(timeout=60) as client:
        # Task A
        a_results = await task_a(client)

        # Task B
        b_results = await task_b(client, a_results)

        # Task C (sync)
        c_results = task_c(b_results)

        # Task D
        d_results = await task_d(client, c_results["all_domains"])

    elapsed = time.monotonic() - t0
    total_cost = a_results["cost_usd"] + b_results["cost_usd"] + d_results.get("cost_usd", 0)

    # ── Task E: Summary Report ────────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("TASK E — SUMMARY REPORT")
    print("=" * 60)

    # Seeds summary
    print(f"\n1. Total DFS cost: ${total_cost:.4f} USD")
    print(f"2. Wall-clock time: {elapsed:.1f}s")
    print(f"\n3. Seeds → suggestions:")
    for seed, sd in a_results["seeds"].items():
        err = sd.get("error", "")
        print(f"   '{seed}': {sd['total_returned']} suggestions{' ❌ ' + err if err else ''}")

    # SERP keywords summary
    serp_kws = [k for k, v in b_results["keywords"].items() if "error" not in v]
    avg_organic = (
        sum(b_results["keywords"][k]["organic_count"] for k in serp_kws) / len(serp_kws)
        if serp_kws
        else 0
    )
    print(f"\n4. {len(serp_kws)} SERP keywords → avg {avg_organic:.1f} organic results/keyword")

    print(f"\n5. Total unique domains from keyword discovery: {c_results['total_unique_domains']}")
    print(
        f"6. AU domain percentage: {c_results['au_domain_count']}/{c_results['total_unique_domains']} "
        f"= {100 * c_results['au_domain_count'] // max(c_results['total_unique_domains'], 1)}%"
    )
    print(f"\n7. Overlap with category discovery:")
    print(f"   Category domains pulled: {d_results['category_domain_count']}")
    print(f"   Overlap: {d_results['overlap_count']}")
    print(f"   Keyword-only (new): {d_results['keyword_only_count']}")
    print(f"   Keyword-only AU: {d_results['keyword_only_au_count']}")

    # Top 5 interesting AU SMBs
    print(f"\n8. Top 5 most interesting AU SMB domains found:")
    au_smbs = [
        d
        for d in c_results["all_domains"]
        if d["is_au"]
        and not any(
            x in d["domain"]
            for x in [
                "healthdirect",
                "medicare",
                "health.gov",
                "betterhealth",
                "yellowpages",
                "truelocal",
                "hotfrog",
                "localsearch",
                "yelp",
                "google",
                "facebook",
                "instagram",
                "linkedin",
                "wikipedia",
                "reddit",
                "finder.com",
                "canstar",
                "nib.com",
                "bupa",
                "medibank",
                "ahm",
                "lawpath",
                "legalvision",
                "armstronglegal",
            ]
        )
        and d["keyword_count"] >= 2
    ][:5]
    for d in au_smbs:
        print(
            f"   {d['domain']} — {d['keyword_count']} kws, avg pos {d['avg_position']}, best '{d['best_keyword']}'@{d['best_position']}"
        )

    # Save full output
    os.makedirs(OUT_DIR, exist_ok=True)
    full_output = {
        "directive": 304,
        "summary": {
            "total_cost_usd": round(total_cost, 4),
            "elapsed_seconds": round(elapsed, 1),
            "seeds_returned": {k: v["total_returned"] for k, v in a_results["seeds"].items()},
            "serp_keywords_tested": len(serp_kws),
            "avg_organic_per_keyword": round(avg_organic, 1),
            "total_unique_domains": c_results["total_unique_domains"],
            "au_domain_count": c_results["au_domain_count"],
            "au_domain_pct": round(
                100 * c_results["au_domain_count"] / max(c_results["total_unique_domains"], 1), 1
            ),
            "category_overlap": d_results["overlap_count"],
            "keyword_only_new": d_results["keyword_only_count"],
            "keyword_only_au": d_results["keyword_only_au_count"],
        },
        "task_a": a_results,
        "task_b": b_results,
        "task_c": {
            "total_unique_domains": c_results["total_unique_domains"],
            "au_domain_count": c_results["au_domain_count"],
            "top20": c_results["top20"],
        },
        "task_d": d_results,
    }
    with open(OUTPUT, "w") as f:
        json.dump(full_output, f, indent=2, default=str)
    print(f"\nSaved: {OUTPUT}")


if __name__ == "__main__":
    asyncio.run(main())
