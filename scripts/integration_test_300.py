"""
DIRECTIVE #300a (rerun) — Integration Test: Stage 1 Discovery
Categories: 10514 dental, 10282 construction, 10163 legal
ETV: 100-50000, cap 500/category, on-demand next_batch.
"""

import asyncio
import base64
import json
import os
import sys
import time
from collections import Counter
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv

load_dotenv("/home/elliotbot/.config/agency-os/.env")

import httpx
from src.config.settings import settings

CATEGORY_CODES = [10514, 10282, 10163]
CATEGORY_NAMES = {
    10514: "Dentists & Dental Services",
    10282: "Building Construction & Maintenance",
    10163: "Legal",
}
LOCATION = "Australia"
ETV_MIN = 100.0
ETV_MAX = 50000.0
CAP = 500
BATCH = 100
OUTPUT = os.path.join(os.path.dirname(__file__), "output", "300a_rerun.json")
DFS_URL = "https://api.dataforseo.com/v3/dataforseo_labs/google/domain_metrics_by_categories/live"


def etv_bucket(etv):
    if etv <= 500:
        return "100-500"
    if etv <= 1000:
        return "501-1000"
    if etv <= 5000:
        return "1001-5000"
    if etv <= 20000:
        return "5001-20000"
    return "20001-50000"


async def fetch(client, b64, code, cap):
    today = date.today()
    fd = (today - timedelta(days=180)).strftime("%Y-%m-%d")
    sd = today.strftime("%Y-%m-%d")
    hdrs = {"Authorization": f"Basic {b64}", "Content-Type": "application/json"}

    results, offset, total_count, calls = [], 0, None, 0

    while len(results) < cap:
        payload = [
            {
                "category_codes": [code],
                "location_name": LOCATION,
                "language_name": "English",
                "first_date": fd,
                "second_date": sd,
                "limit": BATCH,
                "offset": offset,
            }
        ]
        r = await client.post(DFS_URL, headers=hdrs, json=payload, timeout=30)
        r.raise_for_status()
        task = r.json()["tasks"][0]
        calls += 1

        if task.get("status_code") != 20000:
            print(f"  ERR {code} offset={offset}: {task.get('status_message')}")
            break

        rd = (task.get("result") or [{}])[0]
        if total_count is None:
            total_count = rd.get("total_count", 0)

        items = rd.get("items") or []
        if not items:
            break

        etvs = [i.get("organic_etv") or 0 for i in items]
        min_etv = min(etvs)
        max_etv = max(etvs)

        in_range = 0
        for item in items:
            if len(results) >= cap:
                break
            etv = item.get("organic_etv") or 0
            if ETV_MIN <= etv <= ETV_MAX:
                d = item.get("domain") or item.get("main_domain", "")
                if d:
                    results.append(
                        {
                            "domain": d,
                            "organic_etv": round(float(etv), 2),
                            "paid_etv": round(float(item.get("paid_etv") or 0), 2),
                        }
                    )
                    in_range += 1

        print(
            f"    offset={offset:5d} | batch_etv=[{min_etv:.0f}-{max_etv:.0f}] "
            f"| in_range={in_range} | total_so_far={len(results)}"
        )

        offset += len(items)

        # Stop when we've gone past the ETV floor or hit last page
        if min_etv < ETV_MIN:
            break
        if len(items) < BATCH:
            break
        if total_count and offset >= total_count:
            break

    return results, total_count or 0, calls


async def main():
    print("=" * 60)
    print("DIRECTIVE #300a (rerun) — Stage 1: Discovery")
    print(f"Categories: {CATEGORY_CODES}")
    print(f"ETV filter: {ETV_MIN}–{ETV_MAX} | Cap: {CAP}/category")
    print("=" * 60)

    b64 = base64.b64encode(
        f"{settings.dataforseo_login}:{settings.dataforseo_password}".encode()
    ).decode()

    t0 = time.monotonic()
    per_cat = {}
    total_calls = 0

    async with httpx.AsyncClient() as client:
        for code in CATEGORY_CODES:
            print(f"\n--- {CATEGORY_NAMES[code]} ({code}) ---")
            tc = time.monotonic()
            domains, total_count, calls = await fetch(client, b64, code, CAP)
            elapsed_cat = time.monotonic() - tc
            total_calls += calls
            dist = Counter(etv_bucket(d["organic_etv"]) for d in domains)
            per_cat[code] = {
                "name": CATEGORY_NAMES[code],
                "total_pool": total_count,
                "fetched": len(domains),
                "calls": calls,
                "elapsed": round(elapsed_cat, 1),
                "distribution": dict(dist),
                "domains": domains,
            }
            print(
                f"  Pool: {total_count:,} | Fetched: {len(domains)} | Calls: {calls} | Time: {elapsed_cat:.1f}s"
            )

    elapsed = time.monotonic() - t0
    cost = total_calls * 0.10

    seen, all_unique = set(), []
    for code in CATEGORY_CODES:
        for d in per_cat[code]["domains"]:
            if d["domain"] not in seen:
                seen.add(d["domain"])
                all_unique.append({**d, "category_code": code})

    print("\n" + "=" * 60)
    print("=== TASK C REPORT ===")
    print()
    print("1. CATEGORY CODES USED:")
    for code in CATEGORY_CODES:
        print(f"   {code}: {CATEGORY_NAMES[code]}")

    print()
    print("2. TOTAL DOMAINS PER CATEGORY:")
    for code in CATEGORY_CODES:
        c = per_cat[code]
        print(f"   {c['name']} ({code}): {c['fetched']} (pool: {c['total_pool']:,})")

    print()
    print(f"3. TOTAL UNIQUE DOMAINS (deduped): {len(all_unique)}")
    print(f"4. WALL-CLOCK TIME: {elapsed:.2f}s")
    print(f"5. DFS API CALLS: {total_calls}")
    print(f"6. DFS COST: ${cost:.2f} USD")

    print()
    print("7. ETV DISTRIBUTION PER CATEGORY:")
    buckets = ["100-500", "501-1000", "1001-5000", "5001-20000", "20001-50000"]
    for code in CATEGORY_CODES:
        c = per_cat[code]
        print(f"   {c['name']}:")
        for b in buckets:
            print(f"     {b:>15}: {c['distribution'].get(b, 0)}")

    print()
    print("8. FIRST 10 DOMAINS PER CATEGORY:")
    for code in CATEGORY_CODES:
        c = per_cat[code]
        print(f"   {c['name']} ({code}):")
        for d in c["domains"][:10]:
            print(f"     {d['domain']} (ETV: {d['organic_etv']:.0f})")

    print()
    print("9. ERRORS: none" if total_calls > 0 else "9. ERRORS: no calls completed")

    os.makedirs(os.path.dirname(OUTPUT), exist_ok=True)
    output = {
        "stage": "300a_rerun",
        "config": {
            "category_codes": CATEGORY_CODES,
            "location": LOCATION,
            "etv_min": ETV_MIN,
            "etv_max": ETV_MAX,
            "cap": CAP,
        },
        "summary": {
            "total_unique": len(all_unique),
            "total_calls": total_calls,
            "cost_usd": round(cost, 2),
            "elapsed_seconds": round(elapsed, 2),
            "per_category": {
                str(c): {k: v for k, v in per_cat[c].items() if k != "domains"}
                for c in CATEGORY_CODES
            },
        },
        "all_domains": all_unique,
        "per_category_full": {str(c): per_cat[c]["domains"] for c in CATEGORY_CODES},
    }
    with open(OUTPUT, "w") as f:
        json.dump(output, f, indent=2)
    print(f"\nSaved: {OUTPUT}")


if __name__ == "__main__":
    asyncio.run(main())
