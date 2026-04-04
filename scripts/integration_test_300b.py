"""
DIRECTIVE #300b — Integration Test: Stage 2 Website Scraping
Load 1,500 domains from 300a_rerun.json, scrape with httpx (Spider fallback),
apply AU country filter. Zero API cost.
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

from src.integrations.httpx_scraper import HttpxScraper
from src.config.settings import settings

INPUT_FILE  = os.path.join(os.path.dirname(__file__), "output", "300a_rerun.json")
OUTPUT_FILE = os.path.join(os.path.dirname(__file__), "output", "300b_scrape.json")

CATEGORY_MAP = {10514: "Dental", 10282: "Construction", 10163: "Legal"}

SEM_SCRAPE  = asyncio.Semaphore(80)
SPIDER_URL  = "https://api.spider.cloud/scrape"
SPIDER_KEY  = settings.spider_api_key if hasattr(settings, "spider_api_key") else os.environ.get("SPIDER_API_KEY", "")

# AU detection regexes (from free_enrichment.py)
_AU_PHONE_RE    = re.compile(r"\b(0[2347]|0[45]\d|\+61)\d{8}\b")
_AU_STATE_RE    = re.compile(r"\b(NSW|VIC|QLD|SA|WA|TAS|NT|ACT)\b")
_AU_POSTCODE_RE = re.compile(r"\b[2-9]\d{3}\b")


def is_au_domain(domain: str, html: str) -> tuple[bool, str]:
    """Returns (is_au, reason)."""
    if domain.endswith(".au"):
        return True, "tld"
    html = html or ""
    if _AU_PHONE_RE.search(html):
        return True, "phone"
    if _AU_STATE_RE.search(html):
        return True, "state"
    if _AU_POSTCODE_RE.search(html):
        return True, "postcode"
    return False, "non_au"


async def scrape_httpx(scraper: HttpxScraper, domain: str) -> dict | None:
    t0 = time.monotonic()
    try:
        result = await scraper.scrape(domain, timeout=10.0)
        elapsed_ms = (time.monotonic() - t0) * 1000
        if result:
            result["response_time_ms"] = round(elapsed_ms)
        return result
    except Exception:
        return None


async def scrape_spider(domain: str) -> dict | None:
    import httpx as _httpx
    t0 = time.monotonic()
    try:
        payload = {"url": f"https://{domain}", "return_format": "raw",
                   "metadata": True, "limit": 1, "max_credits_per_page": 50}
        async with _httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                SPIDER_URL, json=payload,
                headers={"Authorization": f"Bearer {SPIDER_KEY}"}
            )
        elapsed_ms = (time.monotonic() - t0) * 1000
        if resp.status_code != 200:
            return None
        data = resp.json()
        if not data or not isinstance(data, list):
            return None
        item = data[0]
        content = item.get("content") or ""
        meta = item.get("metadata") or {}
        return {
            "html": content,
            "title": meta.get("title", ""),
            "status_code": 200,
            "content_length": len(content),
            "response_time_ms": round(elapsed_ms),
        }
    except Exception:
        return None


async def process_domain(scraper: HttpxScraper, domain: str, category_code: int) -> dict:
    base = {
        "domain": domain,
        "category": CATEGORY_MAP.get(category_code, str(category_code)),
        "category_code": category_code,
        "scraper_used": "failed",
        "status_code": None,
        "content_length": 0,
        "response_time_ms": 0,
        "au_filter": "fail",
        "au_filter_reason": "non_au",
        "title": "",
    }

    async with SEM_SCRAPE:
        # Try httpx first
        result = await scrape_httpx(scraper, domain)
        if result and result.get("html") and len(result["html"]) >= 1000:
            base["scraper_used"] = "httpx"
            base["status_code"] = result.get("status_code", 200)
            base["content_length"] = len(result.get("html", ""))
            base["response_time_ms"] = result.get("response_time_ms", 0)
            base["title"] = result.get("title") or ""
            html = result.get("html", "")
        elif SPIDER_KEY:
            # Spider fallback
            spider = await scrape_spider(domain)
            if spider and spider.get("html") and len(spider["html"]) >= 500:
                base["scraper_used"] = "spider"
                base["status_code"] = 200
                base["content_length"] = len(spider.get("html", ""))
                base["response_time_ms"] = spider.get("response_time_ms", 0)
                base["title"] = spider.get("title") or ""
                html = spider.get("html", "")
            else:
                html = ""
        else:
            html = ""

    # AU filter
    if base["scraper_used"] != "failed" or html:
        au_pass, reason = is_au_domain(domain, html)
        base["au_filter"] = "pass" if au_pass else "fail"
        base["au_filter_reason"] = reason
    else:
        base["au_filter"] = "fail"
        base["au_filter_reason"] = "scrape_failed"

    return base


async def main():
    print("=" * 60)
    print("DIRECTIVE #300b — Stage 2: Website Scraping")
    print(f"Input: {INPUT_FILE}")
    print("Concurrency: 80 (GLOBAL_SEM_SCRAPE)")
    print("=" * 60)

    with open(INPUT_FILE) as f:
        data = json.load(f)
    domains = data["all_domains"]
    print(f"Loaded {len(domains)} domains\n")

    scraper = HttpxScraper()
    t0 = time.monotonic()
    results = []
    done = 0

    tasks = [process_domain(scraper, d["domain"], d.get("category_code", 0)) for d in domains]

    async def wrap(coro, idx):
        nonlocal done
        r = await coro
        done += 1
        if done % 100 == 0:
            elapsed = time.monotonic() - t0
            print(f"  Progress: {done}/{len(domains)} ({elapsed:.0f}s elapsed)")
        return r

    results = await asyncio.gather(*[wrap(t, i) for i, t in enumerate(tasks)])

    elapsed = time.monotonic() - t0

    # Compute stats
    scraped       = [r for r in results if r["scraper_used"] != "failed"]
    httpx_ok      = [r for r in results if r["scraper_used"] == "httpx"]
    spider_ok     = [r for r in results if r["scraper_used"] == "spider"]
    failed        = [r for r in results if r["scraper_used"] == "failed"]
    au_pass       = [r for r in results if r["au_filter"] == "pass"]
    au_fail       = [r for r in results if r["au_filter"] != "pass"]
    scrape_failed = [r for r in results if r["au_filter_reason"] == "scrape_failed"]

    cat_stats = {}
    for cat in ["Dental", "Construction", "Legal"]:
        cat_r = [r for r in results if r["category"] == cat]
        cat_stats[cat] = {
            "total": len(cat_r),
            "scraped": len([r for r in cat_r if r["scraper_used"] != "failed"]),
            "au_pass": len([r for r in cat_r if r["au_filter"] == "pass"]),
            "au_fail": len([r for r in cat_r if r["au_filter"] != "pass"]),
        }

    httpx_times = [r["response_time_ms"] for r in httpx_ok if r["response_time_ms"]]
    spider_times = [r["response_time_ms"] for r in spider_ok if r["response_time_ms"]]
    avg_httpx = round(sum(httpx_times) / len(httpx_times)) if httpx_times else 0
    avg_spider = round(sum(spider_times) / len(spider_times)) if spider_times else 0

    content_buckets = {"<1000": 0, "1000-10000": 0, "10001-50000": 0, "50001+": 0}
    for r in results:
        cl = r["content_length"]
        if cl < 1000:          content_buckets["<1000"] += 1
        elif cl <= 10000:      content_buckets["1000-10000"] += 1
        elif cl <= 50000:      content_buckets["10001-50000"] += 1
        else:                  content_buckets["50001+"] += 1

    fail_reasons = {}
    for r in au_fail:
        reason = r["au_filter_reason"]
        fail_reasons[reason] = fail_reasons.get(reason, 0) + 1

    first_au_fails = [r for r in results if r["au_filter"] != "pass"][:5]

    print("\n" + "=" * 60)
    print("=== TASK B REPORT ===")
    print()
    print(f"1. TOTAL SCRAPED SUCCESSFULLY: {len(scraped)}")
    print(f"2. httpx SUCCESS: {len(httpx_ok)} | Spider FALLBACK: {len(spider_ok)}")
    print(f"3. TOTAL FAILED (neither): {len(failed)}")
    print(f"4. AU FILTER PASS: {len(au_pass)} | FAIL: {len(au_fail)}")
    print()
    print("5. FAIL REASONS BREAKDOWN:")
    for reason, count in sorted(fail_reasons.items(), key=lambda x: -x[1]):
        print(f"   {reason}: {count}")
    print()
    print("6. PER-CATEGORY BREAKDOWN:")
    for cat, s in cat_stats.items():
        print(f"   {cat}: scraped={s['scraped']} | AU pass={s['au_pass']} | AU fail={s['au_fail']}")
    print()
    print(f"7. AVG RESPONSE TIME: httpx={avg_httpx}ms | Spider={avg_spider}ms")
    print()
    print("8. CONTENT LENGTH DISTRIBUTION:")
    for bucket, count in content_buckets.items():
        print(f"   {bucket}: {count}")
    print()
    print(f"9. WALL-CLOCK TIME: {elapsed:.2f}s")
    print()
    print("10. FIRST 5 AU-FAILED DOMAINS:")
    for r in first_au_fails:
        print(f"   {r['domain']} | reason={r['au_filter_reason']} | scraper={r['scraper_used']} | len={r['content_length']}")

    # Save
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    output = {
        "stage": "300b_scrape",
        "summary": {
            "total": len(results),
            "scraped_ok": len(scraped),
            "httpx_ok": len(httpx_ok),
            "spider_ok": len(spider_ok),
            "failed": len(failed),
            "au_pass": len(au_pass),
            "au_fail": len(au_fail),
            "elapsed_seconds": round(elapsed, 2),
            "avg_httpx_ms": avg_httpx,
            "avg_spider_ms": avg_spider,
            "content_buckets": content_buckets,
            "fail_reasons": fail_reasons,
            "per_category": cat_stats,
        },
        "domains": results,
    }
    with open(OUTPUT_FILE, "w") as f:
        json.dump(output, f, indent=2)
    print(f"\nSaved: {OUTPUT_FILE}")


if __name__ == "__main__":
    asyncio.run(main())
