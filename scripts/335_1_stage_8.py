"""Stage 8: Hunter L1 → DFS SERP L2 → Apify L3 LinkedIn Company enrichment on 57 domains."""

import asyncio
import base64
import json
import os
import re
import sys
import time
from decimal import Decimal
from pathlib import Path

import httpx
from dotenv import load_dotenv

# ── env ───────────────────────────────────────────────────────────────────────
load_dotenv("/home/elliotbot/.config/agency-os/.env")

HUNTER_API_KEY   = os.getenv("HUNTER_API_KEY", "")
APIFY_API_TOKEN  = os.getenv("APIFY_API_TOKEN", "")
DFS_LOGIN        = os.getenv("DATAFORSEO_LOGIN", "")
DFS_PASSWORD     = os.getenv("DATAFORSEO_PASSWORD", "")

if not all([HUNTER_API_KEY, APIFY_API_TOKEN, DFS_LOGIN, DFS_PASSWORD]):
    print("ERROR: Missing API keys. Check .env")
    sys.exit(1)

# ── input paths ───────────────────────────────────────────────────────────────
OUT_DIR = Path("/home/elliotbot/clawd/Agency_OS/scripts/output")
S6_PATH = OUT_DIR / "332_stage_6.json"
S2_PATH = OUT_DIR / "328_stage_2_final.json"
OUT_PATH = OUT_DIR / "335_1_stage_8.json"

# ── constants ─────────────────────────────────────────────────────────────────
HUNTER_SEM = 15
DFS_SEM    = 15
APIFY_ACTOR = "automation-lab~linkedin-company-scraper"
DFS_BASE = "https://api.dataforseo.com"
APIFY_BASE = "https://api.apify.com"

COST_HUNTER_PER_CALL = Decimal("0.0")   # Hunter company find is included in plan
COST_DFS_SERP        = Decimal("0.002") # $0.002 per SERP call
COST_APIFY_RUN       = Decimal("0.0")   # actor cost varies; track separately

# ── load inputs ───────────────────────────────────────────────────────────────
with open(S6_PATH) as f:
    s6 = json.load(f)
with open(S2_PATH) as f:
    s2 = json.load(f)

# Build domain → legal_name map from stage 2
s2_map = {e["domain"]: e for e in s2["domains"]}

# 57 domains from stage 6
domains_data = s6["domains"]  # list of {domain, category, dm_name, ...}
domain_list  = [e["domain"] for e in domains_data]
domain_meta  = {e["domain"]: e for e in domains_data}

print(f"Loaded {len(domain_list)} domains from Stage 6")


# ══════════════════════════════════════════════════════════════════════════════
# L1: Hunter Company Enrichment
# ══════════════════════════════════════════════════════════════════════════════

async def hunter_company(client: httpx.AsyncClient, sem: asyncio.Semaphore,
                          domain: str) -> dict | None:
    """GET Hunter company-find for a domain. Returns data dict or None."""
    async with sem:
        try:
            resp = await client.get(
                "https://api.hunter.io/v2/companies/find",
                params={"domain": domain, "api_key": HUNTER_API_KEY},
                timeout=30.0,
            )
            if resp.status_code == 200:
                data = resp.json().get("data", {})
                print(f"  [L1] {domain}: OK | employees={data.get('metrics', {}).get('employees')} "
                      f"| linkedin={data.get('linkedin', {}).get('handle')}")
                return data
            elif resp.status_code == 404:
                print(f"  [L1] {domain}: 404 not found")
                return None
            else:
                print(f"  [L1] {domain}: HTTP {resp.status_code}")
                return None
        except Exception as e:
            print(f"  [L1] {domain}: ERROR {e}")
            return None


async def run_l1(domain_list: list[str]) -> dict[str, dict | None]:
    """Run Hunter L1 concurrently. Returns domain → data."""
    sem = asyncio.Semaphore(HUNTER_SEM)
    async with httpx.AsyncClient() as client:
        tasks = [hunter_company(client, sem, d) for d in domain_list]
        results = await asyncio.gather(*tasks)
    return dict(zip(domain_list, results))


# ══════════════════════════════════════════════════════════════════════════════
# L2: DFS SERP LinkedIn URL recovery
# ══════════════════════════════════════════════════════════════════════════════

def _dfs_auth_header() -> str:
    creds = f"{DFS_LOGIN}:{DFS_PASSWORD}"
    return "Basic " + base64.b64encode(creds.encode()).decode()


def _extract_linkedin_company_url(items: list) -> str | None:
    """Parse SERP items for first /company/ URL."""
    for item in items:
        url = item.get("url", "")
        if "/company/" in url and "linkedin.com" in url:
            # normalise to https://www.linkedin.com/company/SLUG/
            m = re.search(r"linkedin\.com/company/([^/?#]+)", url)
            if m:
                slug = m.group(1)
                return f"https://www.linkedin.com/company/{slug}/"
        # recurse into sub-items if present
        sub_items = item.get("items") or []
        found = _extract_linkedin_company_url(sub_items)
        if found:
            return found
    return None


async def dfs_linkedin_serp(client: httpx.AsyncClient, sem: asyncio.Semaphore,
                             domain: str, legal_name: str) -> str | None:
    """POST DFS SERP for LinkedIn company URL. Returns URL or None."""
    query = f'"{legal_name}" site:linkedin.com/company/'
    payload = [{
        "keyword": query,
        "location_code": 2036,
        "language_code": "en",
        "depth": 10,
        "se_domain": "google.com.au",
    }]
    async with sem:
        try:
            resp = await client.post(
                f"{DFS_BASE}/v3/serp/google/organic/live/advanced",
                json=payload,
                headers={"Authorization": _dfs_auth_header()},
                timeout=30.0,
            )
            resp.raise_for_status()
            data = resp.json()
            tasks = data.get("tasks", [])
            if not tasks:
                print(f"  [L2] {domain}: no tasks in response")
                return None
            result = (tasks[0].get("result") or [{}])[0]
            items  = result.get("items") or []
            url = _extract_linkedin_company_url(items)
            if url:
                print(f"  [L2] {domain}: RECOVERED {url}")
            else:
                print(f"  [L2] {domain}: no LinkedIn URL found in {len(items)} items")
            return url
        except Exception as e:
            print(f"  [L2] {domain}: ERROR {e}")
            return None


async def run_l2(domains_needing_recovery: list[str],
                 domain_names: dict[str, str]) -> dict[str, str | None]:
    """Run DFS SERP L2 for domains missing LinkedIn handle. Returns domain → url."""
    if not domains_needing_recovery:
        return {}
    sem = asyncio.Semaphore(DFS_SEM)
    auth = _dfs_auth_header()
    async with httpx.AsyncClient(headers={"Authorization": auth}) as client:
        tasks = [
            dfs_linkedin_serp(client, sem, d, domain_names.get(d, d))
            for d in domains_needing_recovery
        ]
        results = await asyncio.gather(*tasks)
    return dict(zip(domains_needing_recovery, results))


# ══════════════════════════════════════════════════════════════════════════════
# L3: Apify batch scrape
# ══════════════════════════════════════════════════════════════════════════════

async def run_l3(linkedin_urls: list[str]) -> dict[str, dict]:
    """
    Trigger Apify actor for all URLs, poll to SUCCEEDED, fetch dataset.
    Returns a dict keyed by the normalised LinkedIn URL.
    """
    if not linkedin_urls:
        print("  [L3] No URLs to scrape")
        return {}

    async with httpx.AsyncClient(timeout=60.0) as client:
        # Trigger run
        print(f"  [L3] Triggering Apify run for {len(linkedin_urls)} URLs ...")
        resp = await client.post(
            f"{APIFY_BASE}/v2/acts/{APIFY_ACTOR}/runs",
            params={"token": APIFY_API_TOKEN},
            json={"companyUrls": linkedin_urls},
        )
        resp.raise_for_status()
        run_data  = resp.json()["data"]
        run_id    = run_data["id"]
        dataset_id = run_data["defaultDatasetId"]
        print(f"  [L3] Run ID: {run_id} | Dataset: {dataset_id}")

        # Poll every 10s
        deadline = time.monotonic() + 600  # 10 min cap
        while time.monotonic() < deadline:
            await asyncio.sleep(10)
            poll = await client.get(
                f"{APIFY_BASE}/v2/actor-runs/{run_id}",
                params={"token": APIFY_API_TOKEN},
            )
            poll.raise_for_status()
            status = poll.json()["data"]["status"]
            print(f"  [L3] Poll: {status}")
            if status == "SUCCEEDED":
                break
            if status in ("FAILED", "ABORTED", "TIMED-OUT"):
                print(f"  [L3] Run {status} — partial data may be available")
                break

        # Fetch dataset items
        items_resp = await client.get(
            f"{APIFY_BASE}/v2/datasets/{dataset_id}/items",
            params={"token": APIFY_API_TOKEN, "format": "json"},
        )
        items_resp.raise_for_status()
        items = items_resp.json()
        print(f"  [L3] Fetched {len(items)} items from dataset")

    # Key by normalised slug (no trailing slash) for robust matching
    result_map: dict[str, dict] = {}
    for item in items:
        url = item.get("linkedinUrl") or item.get("linkedInUrl") or item.get("url") or item.get("companyUrl") or ""
        if url:
            m = re.search(r"linkedin\.com/company/([^/?#]+)", url)
            if m:
                slug = m.group(1).lower()
                result_map[slug] = item
    return result_map


# ══════════════════════════════════════════════════════════════════════════════
# Main
# ══════════════════════════════════════════════════════════════════════════════

async def main() -> None:
    t_start = time.monotonic()

    # ── build name lookup ────────────────────────────────────────────────────
    # Prefer legal_name from stage 2; fall back to domain as-is
    domain_names: dict[str, str] = {}
    for d in domain_list:
        s2e = s2_map.get(d, {})
        name = s2e.get("legal_name") or d.replace(".com.au", "").replace(".", " ").title()
        domain_names[d] = name

    # ── L1 Hunter ────────────────────────────────────────────────────────────
    print("\n=== L1 Hunter Company Enrichment ===")
    l1_results = await run_l1(domain_list)

    l1_success = sum(1 for v in l1_results.values() if v is not None)
    l1_linkedin_found = 0
    linkedin_urls: dict[str, str] = {}   # domain → URL
    url_source:   dict[str, str] = {}    # domain → "hunter"|"serp"|"none"

    for domain, data in l1_results.items():
        if data and data.get("linkedin", {}).get("handle"):
            handle = data["linkedin"]["handle"]
            # handle may be "company/slug" or just "slug" — normalise to just slug
            slug = handle.replace("company/", "").strip("/")
            url = f"https://www.linkedin.com/company/{slug}/"
            linkedin_urls[domain] = url
            url_source[domain]    = "hunter"
            l1_linkedin_found += 1

    print(f"\nL1 summary: {l1_success}/{len(domain_list)} API success | "
          f"{l1_linkedin_found} LinkedIn URLs found")

    # ── L2 DFS SERP ──────────────────────────────────────────────────────────
    domains_for_l2 = [d for d in domain_list if d not in linkedin_urls]
    print(f"\n=== L2 DFS SERP ({len(domains_for_l2)} domains need recovery) ===")

    l2_results = await run_l2(domains_for_l2, domain_names)
    l2_recovered = 0
    for domain, url in l2_results.items():
        if url:
            linkedin_urls[domain] = url
            url_source[domain]    = "serp"
            l2_recovered += 1

    # Domains still without LinkedIn URL
    for d in domain_list:
        if d not in url_source:
            url_source[d] = "none"

    print(f"\nL2 summary: {len(domains_for_l2)} attempted | {l2_recovered} recovered")

    # ── L3 Apify ─────────────────────────────────────────────────────────────
    all_urls = list(set(linkedin_urls.values()))
    print(f"\n=== L3 Apify batch scrape ({len(all_urls)} unique LinkedIn URLs) ===")

    try:
        apify_map = await run_l3(all_urls)
        l3_success = len(apify_map)
    except Exception as e:
        print(f"  [L3] FAILED: {e}")
        apify_map  = {}
        l3_success = 0

    # ── Assemble per-domain output ────────────────────────────────────────────
    combined_enriched = 0
    domains_out: dict[str, dict] = {}

    for domain in domain_list:
        hunter_data = l1_results.get(domain) or {}
        li_url      = linkedin_urls.get(domain)
        apify_data  = {}
        if li_url:
            # Try exact match first, then slug-normalised
            m_slug = re.search(r"linkedin\.com/company/([^/?#]+)", li_url or "")
            apify_data = apify_map.get(m_slug.group(1).lower(), {}) if m_slug else {}

        if hunter_data or apify_data:
            combined_enriched += 1

        domains_out[domain] = {
            "hunter": hunter_data,
            "apify": apify_data,
            "linkedin_url": li_url,
            "url_source": url_source.get(domain, "none"),
        }

    # ── Cost ─────────────────────────────────────────────────────────────────
    cost_serp  = float(COST_DFS_SERP * len(domains_for_l2))
    cost_total = cost_serp  # Hunter included in plan; Apify billed separately

    # ── Output JSON ──────────────────────────────────────────────────────────
    wall_time = time.monotonic() - t_start
    output = {
        "directive": "#335.1 Stage 8",
        "l1_hunter_success": l1_success,
        "l1_linkedin_url_found": l1_linkedin_found,
        "l2_serp_attempted": len(domains_for_l2),
        "l2_serp_recovered": l2_recovered,
        "l3_apify_input": len(all_urls),
        "l3_apify_success": l3_success,
        "combined_enriched": combined_enriched,
        "cost": {
            "hunter_usd": 0.0,
            "serp_usd": round(cost_serp, 4),
            "apify_usd": "billed_separately",
            "total_usd": round(cost_total, 4),
            "total_aud": round(cost_total * 1.55, 4),
        },
        "wall_time_s": round(wall_time, 1),
        "domains": domains_out,
    }

    OUT_PATH.write_text(json.dumps(output, indent=2, default=str))
    print(f"\nOutput written to {OUT_PATH}")

    # ── Report ────────────────────────────────────────────────────────────────
    print("\n" + "="*60)
    print("STAGE 8 REPORT")
    print("="*60)
    print(f"L1 Hunter success:        {l1_success}/{len(domain_list)}")
    print(f"L1 LinkedIn URLs found:   {l1_linkedin_found}")
    print(f"L2 SERP attempted:        {len(domains_for_l2)}")
    print(f"L2 SERP recovered:        {l2_recovered}")
    print(f"L3 Apify input URLs:      {len(all_urls)}")
    print(f"L3 Apify results:         {l3_success}")
    print(f"Combined enriched:        {combined_enriched}/{len(domain_list)}")
    print(f"Cost (SERP only):         ${cost_serp:.4f} USD / ${cost_serp*1.55:.4f} AUD")
    print(f"Wall time:                {wall_time:.1f}s")

    # URL source breakdown
    src_count = {"hunter": 0, "serp": 0, "none": 0}
    for s in url_source.values():
        src_count[s] = src_count.get(s, 0) + 1
    print(f"\nURL source breakdown:")
    print(f"  hunter: {src_count['hunter']}")
    print(f"  serp:   {src_count['serp']}")
    print(f"  none:   {src_count['none']}")

    # 5 sample records
    print("\nSample records (5):")
    for domain in domain_list[:5]:
        entry = domains_out[domain]
        h = entry["hunter"]
        a = entry["apify"]
        print(f"\n  {domain}")
        print(f"    url_source:   {entry['url_source']}")
        print(f"    linkedin_url: {entry['linkedin_url']}")
        if h:
            print(f"    hunter.name:        {h.get('name')}")
            print(f"    hunter.employees:   {h.get('metrics', {}).get('employees')}")
            print(f"    hunter.founded:     {h.get('foundedYear')}")
        if a:
            print(f"    apify.name:         {a.get('name') or a.get('companyName')}")
            print(f"    apify.followers:    {a.get('followersCount') or a.get('followers')}")
            print(f"    apify.industry:     {a.get('industry')}")


if __name__ == "__main__":
    asyncio.run(main())
