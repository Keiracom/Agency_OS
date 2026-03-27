"""
Directive #276 — Endpoint Validation
Test 9 data sources on 5 AU dental domains.
Determines which endpoints make it into production pipeline.
"""

import asyncio
import base64
import json
import os
import re
import time
from datetime import datetime, timezone

import httpx

# ============================================
# CONFIG
# ============================================

DOMAINS = [
    "1300smiles.com.au",
    "affordabledental.com.au",
    "ahpdentalmedical.com.au",
    "adelaidedentist.com.au",
    "addcdental.com.au",
]

BRAND_NAMES = {
    "1300smiles.com.au": "1300 Smiles",
    "affordabledental.com.au": "Affordable Dental",
    "ahpdentalmedical.com.au": "AHP Dental Medical",
    "adelaidedentist.com.au": "Adelaide Dentist",
    "addcdental.com.au": "ADDC Dental",
}

DFS_LOGIN = os.environ.get("DATAFORSEO_LOGIN", "")
DFS_PASSWORD = os.environ.get("DATAFORSEO_PASSWORD", "")
DFS_BASE = "https://api.dataforseo.com"
BD_API_KEY = "2bab0747-ede2-4437-9b6f-6a77e8f0ca3e"

RESULTS: dict = {}
COSTS: dict = {}
TIMINGS: dict = {}
ERRORS: dict = {}


def dfs_auth_header() -> dict:
    creds = base64.b64encode(f"{DFS_LOGIN}:{DFS_PASSWORD}".encode()).decode()
    return {"Authorization": f"Basic {creds}", "Content-Type": "application/json"}


# ============================================
# ENDPOINT 1: Website Scrape (Bright Data)
# ============================================

async def endpoint_1_website_scrape(client: httpx.AsyncClient, domain: str) -> dict:
    """Scrape homepage via Bright Data Web Unlocker, then check /sitemap.xml and /robots.txt."""
    url = f"https://www.{domain}"

    # Use BD Web Unlocker
    bd_url = "https://api.brightdata.com/request"
    headers = {"Authorization": f"Bearer {BD_API_KEY}", "Content-Type": "application/json"}

    # Try direct fetch first (free), fall back to BD if blocked
    result = {"domain": domain, "source": "direct"}

    try:
        resp = await client.get(url, follow_redirects=True, timeout=30)
        html = resp.text
        result["source"] = "direct"
        result["status_code"] = resp.status_code
    except Exception as e:
        # Try BD Web Unlocker
        try:
            bd_payload = {"zone": "unblocker", "url": url, "format": "raw"}
            resp = await client.post(bd_url, json=bd_payload, headers=headers, timeout=60)
            html = resp.text
            result["source"] = "bright_data"
            result["status_code"] = resp.status_code
        except Exception as e2:
            return {"domain": domain, "error": f"direct: {e}, bd: {e2}"}

    result["raw_size_bytes"] = len(html)
    html_lower = html.lower()

    # TECH detection
    result["cms"] = (
        "WordPress" if "wp-content" in html_lower or "wordpress" in html_lower else
        "Wix" if "wix.com" in html_lower else
        "Squarespace" if "squarespace" in html_lower else
        "Shopify" if "shopify" in html_lower else
        "Unknown"
    )
    result["ga4"] = bool(re.search(r'gtag|G-[A-Z0-9]+', html))
    result["ga4_id"] = (re.findall(r'G-[A-Z0-9]+', html) or [None])[0]
    result["gtm"] = bool(re.search(r'GTM-[A-Z0-9]+', html))
    result["gtm_id"] = (re.findall(r'GTM-[A-Z0-9]+', html) or [None])[0]
    result["google_ads"] = bool(re.search(r'AW-[0-9]+', html))
    result["google_ads_id"] = (re.findall(r'AW-[0-9]+', html) or [None])[0]
    result["fb_pixel"] = bool(re.search(r'fbq|fb.*pixel', html_lower))
    result["fb_pixel_id"] = (re.findall(r"fbq\('init',\s*'(\d+)'\)", html) or [None])[0]

    # CRM
    result["hubspot"] = "hbspt" in html_lower or "hubspot" in html_lower
    result["activecampaign"] = "activecampaign" in html_lower
    result["mailchimp"] = "mailchimp" in html_lower
    result["salesforce"] = "salesforce" in html_lower
    result["crm"] = next((c for c in ["hubspot", "activecampaign", "mailchimp", "salesforce"] if result.get(c)), "None")

    # Chat
    result["intercom"] = "intercom" in html_lower
    result["drift"] = "drift" in html_lower
    result["livechat"] = "livechat" in html_lower
    result["tidio"] = "tidio" in html_lower
    result["chat"] = next((c for c in ["intercom", "drift", "livechat", "tidio"] if result.get(c)), "None")

    # Booking
    result["hotdoc"] = "hotdoc" in html_lower
    result["calendly"] = "calendly" in html_lower
    result["booking_system"] = "hotdoc" if result["hotdoc"] else "calendly" if result["calendly"] else ("detected" if re.search(r'book.*(online|now|appointment)', html_lower) else "None")

    result["ssl"] = url.startswith("https") or "https" in str(resp.url)

    # CONTENT
    result["blog_exists"] = bool(re.search(r'href=["\'][^"\']*(/blog|/news|/articles)', html_lower))
    services = re.findall(r'<li[^>]*>([^<]{5,60})</li>', html)
    result["services_listed"] = services[:20] if services else []
    result["locations_mentioned"] = len(re.findall(r'location|clinic|branch|practice', html_lower))
    result["team_page"] = bool(re.search(r'href=["\'][^"\']*(/team|/about|/our-team|/dentist)', html_lower))
    copyright_match = re.findall(r'©\s*(\d{4})|copyright\s*(\d{4})', html_lower)
    result["copyright_year"] = (copyright_match[0][0] or copyright_match[0][1]) if copyright_match else None

    # CONVERSION
    result["contact_form"] = bool(re.search(r'<form|contact.*form|enqui?r', html_lower))
    phones = re.findall(r'(?:\+61|0[2-9])\s*\d[\d\s\-]{6,12}\d', html)
    result["phone_numbers"] = list(set(phones))[:5]
    result["cta_button"] = bool(re.search(r'book\s*(now|online|appointment)|get\s*started|contact\s*us|request.*quote', html_lower))

    # SEO
    title_match = re.search(r'<title[^>]*>([^<]+)</title>', html, re.IGNORECASE)
    result["meta_title"] = title_match.group(1).strip() if title_match else None
    desc_match = re.search(r'<meta[^>]*name=["\']description["\'][^>]*content=["\']([^"\']+)', html, re.IGNORECASE)
    if not desc_match:
        desc_match = re.search(r'<meta[^>]*content=["\']([^"\']+)["\'][^>]*name=["\']description["\']', html, re.IGNORECASE)
    result["meta_description"] = desc_match.group(1).strip() if desc_match else None
    h1_match = re.search(r'<h1[^>]*>([^<]+)</h1>', html, re.IGNORECASE)
    result["h1"] = h1_match.group(1).strip() if h1_match else None
    result["schema_markup"] = bool(re.search(r'application/ld\+json|LocalBusiness|Dentist', html))

    # Check sitemap and robots
    for path in ["/sitemap.xml", "/robots.txt"]:
        try:
            r = await client.get(f"https://www.{domain}{path}", follow_redirects=True, timeout=10)
            result[path.strip("/").replace(".", "_")] = r.status_code == 200
        except:
            result[path.strip("/").replace(".", "_")] = False

    return result


# ============================================
# ENDPOINT 2: GMB Lookup (Bright Data)
# ============================================

async def endpoint_2_gmb_lookup(client: httpx.AsyncClient, domain: str) -> dict:
    """Search GMB via Bright Data Datasets API."""
    business_name = BRAND_NAMES[domain]

    headers = {
        "Authorization": f"Bearer {BD_API_KEY}",
        "Content-Type": "application/json",
    }

    # Trigger collection
    trigger_url = "https://api.brightdata.com/datasets/v3/trigger?dataset_id=gd_m8ebnr0q2qlklc02fz&include_errors=true&type=discover_new&discover_by=keyword"
    payload = [{"keyword": business_name, "country": "Australia"}]

    try:
        resp = await client.post(trigger_url, json=payload, headers=headers, timeout=30)
        trigger_data = resp.json()
        snapshot_id = trigger_data.get("snapshot_id")
        if not snapshot_id:
            return {"domain": domain, "error": f"No snapshot_id: {trigger_data}"}

        # Poll for results
        poll_url = f"https://api.brightdata.com/datasets/v3/snapshot/{snapshot_id}?format=json"
        for attempt in range(60):
            await asyncio.sleep(5)
            poll_resp = await client.get(poll_url, headers=headers, timeout=30)
            if poll_resp.status_code == 200:
                data = poll_resp.json()
                if isinstance(data, list) and len(data) > 0:
                    gmb = data[0]
                    return {
                        "domain": domain,
                        "business_name": business_name,
                        "gmb_name": gmb.get("title") or gmb.get("name"),
                        "rating": gmb.get("rating"),
                        "review_count": gmb.get("reviews") or gmb.get("review_count"),
                        "categories": gmb.get("category") or gmb.get("categories"),
                        "address": gmb.get("address") or gmb.get("full_address"),
                        "phone": gmb.get("phone"),
                        "hours_listed": gmb.get("work_hours") is not None,
                        "photos_count": gmb.get("photos_count"),
                        "website": gmb.get("website") or gmb.get("site"),
                        "place_id": gmb.get("place_id"),
                        "claimed": gmb.get("claimed"),
                        "raw_keys": list(gmb.keys())[:30],
                        "total_results": len(data),
                    }
                elif poll_resp.status_code == 202:
                    continue
            elif poll_resp.status_code == 202:
                continue
            else:
                if attempt > 24:  # 2 min timeout
                    return {"domain": domain, "error": f"GMB poll timeout after {attempt * 5}s, last status: {poll_resp.status_code}"}

        return {"domain": domain, "error": "GMB poll exhausted 60 attempts"}
    except Exception as e:
        return {"domain": domain, "error": str(e)}


# ============================================
# ENDPOINT 3: Competitors Domain (DFS)
# ============================================

async def endpoint_3_competitors(client: httpx.AsyncClient, domain: str) -> dict:
    """DFS Labs competitors_domain/live."""
    url = f"{DFS_BASE}/v3/dataforseo_labs/google/competitors_domain/live"
    payload = [{"target": domain, "location_code": 2036, "language_code": "en", "limit": 5}]

    try:
        resp = await client.post(url, json=payload, headers=dfs_auth_header(), timeout=30)
        data = resp.json()

        if data.get("status_code") == 20000:
            items = []
            try:
                items = data["tasks"][0]["result"][0]["items"] or []
            except (IndexError, KeyError, TypeError):
                pass

            competitors = []
            for item in items[:5]:
                competitors.append({
                    "domain": item.get("domain"),
                    "avg_position": item.get("avg_position"),
                    "common_keywords": item.get("se_keywords") or item.get("intersections"),
                    "organic_etv": item.get("etv") or item.get("estimated_paid_traffic_cost"),
                    "visibility": item.get("visibility"),
                })

            return {
                "domain": domain,
                "competitors_found": len(competitors),
                "competitors": competitors,
                "raw_task_cost": data["tasks"][0].get("cost"),
            }
        else:
            return {"domain": domain, "error": f"DFS status {data.get('status_code')}: {data.get('status_message')}"}
    except Exception as e:
        return {"domain": domain, "error": str(e)}


# ============================================
# ENDPOINT 4: Backlinks Summary (DFS)
# ============================================

async def endpoint_4_backlinks(client: httpx.AsyncClient, domain: str) -> dict:
    """DFS Backlinks summary/live."""
    url = f"{DFS_BASE}/v3/backlinks/summary/live"
    payload = [{"target": domain, "limit": 1}]

    try:
        resp = await client.post(url, json=payload, headers=dfs_auth_header(), timeout=30)
        data = resp.json()

        if data.get("status_code") == 20000:
            try:
                item = data["tasks"][0]["result"][0]
            except (IndexError, KeyError, TypeError):
                return {"domain": domain, "error": "No result items", "raw": data}

            return {
                "domain": domain,
                "total_backlinks": item.get("total_backlinks"),
                "referring_domains": item.get("referring_domains"),
                "broken_backlinks": item.get("broken_backlinks"),
                "referring_domains_nofollow": item.get("referring_domains_nofollow"),
                "rank": item.get("rank"),
                "raw_task_cost": data["tasks"][0].get("cost"),
            }
        else:
            return {"domain": domain, "error": f"DFS status {data.get('status_code')}: {data.get('status_message')}"}
    except Exception as e:
        return {"domain": domain, "error": str(e)}


# ============================================
# ENDPOINT 5: On-Page Summary (DFS)
# ============================================

async def endpoint_5_onpage(client: httpx.AsyncClient, domain: str) -> dict:
    """DFS On-Page — requires task_post then task_get. May take minutes."""
    # Step 1: Post task
    post_url = f"{DFS_BASE}/v3/on_page/task_post"
    payload = [{"target": f"https://www.{domain}", "max_crawl_pages": 10}]

    try:
        resp = await client.post(post_url, json=payload, headers=dfs_auth_header(), timeout=30)
        data = resp.json()

        if data.get("status_code") != 20000:
            return {"domain": domain, "error": f"task_post failed: {data.get('status_code')}: {data.get('status_message')}"}

        task_id = data["tasks"][0]["id"]

        # Step 2: Poll for completion
        summary_url = f"{DFS_BASE}/v3/on_page/summary/{task_id}"
        for attempt in range(12):  # 60s max
            await asyncio.sleep(5)
            resp2 = await client.get(summary_url, headers=dfs_auth_header(), timeout=30)
            data2 = resp2.json()

            if data2.get("status_code") == 20000:
                try:
                    result = data2["tasks"][0]["result"][0]
                    crawl_status = result.get("crawl_progress", "")
                    if crawl_status == "finished" or result.get("pages_crawled", 0) > 0:
                        return {
                            "domain": domain,
                            "pages_crawled": result.get("pages_crawled"),
                            "pages_with_issues": result.get("pages_with_issues"),
                            "duplicate_title": result.get("duplicate_title"),
                            "duplicate_description": result.get("duplicate_description"),
                            "broken_resources": result.get("broken_resources"),
                            "pages_without_h1": None,  # Extract from detailed results if available
                            "crawl_progress": crawl_status,
                            "raw_task_cost": data["tasks"][0].get("cost"),
                        }
                except (IndexError, KeyError, TypeError):
                    continue

            if attempt == 11:
                return {"domain": domain, "error": f"on_page poll timeout after 60s, crawl not finished", "task_id": task_id}

        return {"domain": domain, "error": "on_page poll exhausted"}
    except Exception as e:
        return {"domain": domain, "error": str(e)}


# ============================================
# ENDPOINT 6: SERP Brand Name (DFS)
# ============================================

async def endpoint_6_serp_brand(client: httpx.AsyncClient, domain: str) -> dict:
    """DFS SERP organic/live for brand name search."""
    brand = BRAND_NAMES[domain]
    url = f"{DFS_BASE}/v3/serp/google/organic/live/advanced"
    payload = [{"keyword": brand, "location_code": 2036, "language_code": "en", "depth": 10}]

    try:
        resp = await client.post(url, json=payload, headers=dfs_auth_header(), timeout=30)
        data = resp.json()

        if data.get("status_code") == 20000:
            items = []
            try:
                items = data["tasks"][0]["result"][0]["items"] or []
            except (IndexError, KeyError, TypeError):
                pass

            serp_results = []
            own_rank = None
            gmb_showing = False

            for item in items:
                item_type = item.get("type", "")
                if item_type == "organic":
                    rank = item.get("rank_absolute")
                    item_domain = item.get("domain", "")
                    serp_results.append({
                        "rank": rank,
                        "domain": item_domain,
                        "title": item.get("title"),
                        "url": item.get("url"),
                    })
                    if domain in item_domain:
                        own_rank = rank
                elif item_type in ("maps", "local_pack"):
                    gmb_showing = True

            return {
                "domain": domain,
                "brand_query": brand,
                "own_rank": own_rank,
                "gmb_showing": gmb_showing,
                "top_results": serp_results[:10],
                "total_items": len(items),
                "raw_task_cost": data["tasks"][0].get("cost"),
            }
        else:
            return {"domain": domain, "error": f"DFS status {data.get('status_code')}: {data.get('status_message')}"}
    except Exception as e:
        return {"domain": domain, "error": str(e)}


# ============================================
# ENDPOINT 7: PageSpeed Insights (FREE)
# ============================================

async def endpoint_7_pagespeed(client: httpx.AsyncClient, domain: str) -> dict:
    """Google PageSpeed Insights — free, no auth."""
    url = f"https://www.googleapis.com/pagespeedonline/v5/runPagespeed?url=https://www.{domain}&strategy=mobile"

    try:
        resp = await client.get(url, timeout=60)
        data = resp.json()

        lh = data.get("lighthouseResult", {})
        categories = lh.get("categories", {})
        audits = lh.get("audits", {})

        perf = categories.get("performance", {})

        return {
            "domain": domain,
            "performance_score": int(perf.get("score", 0) * 100) if perf.get("score") else None,
            "lcp_ms": audits.get("largest-contentful-paint", {}).get("numericValue"),
            "inp_ms": audits.get("interaction-to-next-paint", {}).get("numericValue"),
            "cls": audits.get("cumulative-layout-shift", {}).get("numericValue"),
            "fcp_ms": audits.get("first-contentful-paint", {}).get("numericValue"),
            "speed_index_ms": audits.get("speed-index", {}).get("numericValue"),
            "tbt_ms": audits.get("total-blocking-time", {}).get("numericValue"),
        }
    except Exception as e:
        return {"domain": domain, "error": str(e)}


# ============================================
# ENDPOINT 8: Social Presence Check
# ============================================

async def endpoint_8_social(client: httpx.AsyncClient, domain: str) -> dict:
    """Check for social presence from website HTML, then verify links."""
    # First get the homepage HTML (reuse from EP1 or fetch fresh)
    url = f"https://www.{domain}"
    result = {"domain": domain, "facebook": None, "instagram": None}

    try:
        resp = await client.get(url, follow_redirects=True, timeout=20)
        html = resp.text
    except:
        html = ""

    # Extract social links
    fb_links = re.findall(r'href=["\']([^"\']*facebook\.com/[^"\']+)', html, re.IGNORECASE)
    ig_links = re.findall(r'href=["\']([^"\']*instagram\.com/[^"\']+)', html, re.IGNORECASE)

    result["fb_link_on_site"] = fb_links[0] if fb_links else None
    result["ig_link_on_site"] = ig_links[0] if ig_links else None

    # Check if FB page exists
    fb_url = fb_links[0] if fb_links else f"https://www.facebook.com/{BRAND_NAMES[domain].replace(' ', '')}"
    try:
        fb_resp = await client.get(fb_url, follow_redirects=True, timeout=15)
        result["fb_exists"] = fb_resp.status_code == 200 and "page not found" not in fb_resp.text.lower()
        result["fb_url_checked"] = fb_url
    except:
        result["fb_exists"] = "check_failed"

    # Check if IG page exists
    ig_url = ig_links[0] if ig_links else f"https://www.instagram.com/{BRAND_NAMES[domain].replace(' ', '').lower()}"
    try:
        ig_resp = await client.get(ig_url, follow_redirects=True, timeout=15)
        result["ig_exists"] = ig_resp.status_code == 200 and "page isn't available" not in ig_resp.text.lower()
        result["ig_url_checked"] = ig_url
    except:
        result["ig_exists"] = "check_failed"

    return result


# ============================================
# ENDPOINT 9: Jina AI Reader (1 domain only)
# ============================================

async def endpoint_9_jina(client: httpx.AsyncClient, domain: str) -> dict:
    """Jina AI Reader — free, markdown extraction. Run on 1 domain only."""
    url = f"https://r.jina.ai/https://www.{domain}"

    try:
        resp = await client.get(url, timeout=30, headers={"Accept": "application/json"})
        data = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {"content": resp.text}

        content = data.get("data", {}).get("content", "") if "data" in data else data.get("content", resp.text)

        return {
            "domain": domain,
            "status_code": resp.status_code,
            "content_length": len(content),
            "content_preview": content[:2000],
            "title": data.get("data", {}).get("title") if "data" in data else None,
        }
    except Exception as e:
        return {"domain": domain, "error": str(e)}


# ============================================
# RUNNER
# ============================================

async def run_endpoint(name: str, func, client: httpx.AsyncClient, domains: list[str]) -> list[dict]:
    """Run an endpoint function across domains, tracking time and errors."""
    results = []
    for domain in domains:
        start = time.time()
        try:
            result = await func(client, domain)
        except Exception as e:
            result = {"domain": domain, "error": str(e)}
        elapsed = round(time.time() - start, 2)
        result["_time_seconds"] = elapsed
        results.append(result)
        print(f"  [{name}] {domain}: {elapsed}s {'ERROR: ' + result.get('error', '')[:80] if 'error' in result else 'OK'}")
    return results


async def main():
    print(f"=" * 70)
    print(f"DIRECTIVE #276 — ENDPOINT VALIDATION")
    print(f"Started: {datetime.now(timezone.utc).isoformat()}")
    print(f"Domains: {len(DOMAINS)}")
    print(f"DFS Login: {DFS_LOGIN}")
    print(f"BD Key: {BD_API_KEY[:8]}...")
    print(f"=" * 70)

    all_results = {}
    total_cost = 0.0

    async with httpx.AsyncClient(
        timeout=60,
        follow_redirects=True,
        headers={"User-Agent": "Mozilla/5.0 (compatible; AgencyOS/1.0)"},
    ) as client:

        # EP1: Website Scrape
        print(f"\n--- ENDPOINT 1: Website Scrape ---")
        start = time.time()
        all_results["ep1_website"] = await run_endpoint("EP1", endpoint_1_website_scrape, client, DOMAINS)
        print(f"  Total: {round(time.time() - start, 2)}s | Cost: ~$0.00 (direct scrape)")

        # EP7: PageSpeed (free, slow — run early)
        print(f"\n--- ENDPOINT 7: PageSpeed Insights ---")
        start = time.time()
        all_results["ep7_pagespeed"] = await run_endpoint("EP7", endpoint_7_pagespeed, client, DOMAINS)
        print(f"  Total: {round(time.time() - start, 2)}s | Cost: $0.00")

        # EP3: DFS Competitors
        print(f"\n--- ENDPOINT 3: Competitors Domain (DFS) ---")
        start = time.time()
        all_results["ep3_competitors"] = await run_endpoint("EP3", endpoint_3_competitors, client, DOMAINS)
        ep3_cost = sum(r.get("raw_task_cost", 0) or 0 for r in all_results["ep3_competitors"])
        total_cost += ep3_cost
        print(f"  Total: {round(time.time() - start, 2)}s | Cost: ${ep3_cost:.4f}")

        # EP4: DFS Backlinks
        print(f"\n--- ENDPOINT 4: Backlinks Summary (DFS) ---")
        start = time.time()
        all_results["ep4_backlinks"] = await run_endpoint("EP4", endpoint_4_backlinks, client, DOMAINS)
        ep4_cost = sum(r.get("raw_task_cost", 0) or 0 for r in all_results["ep4_backlinks"])
        total_cost += ep4_cost
        print(f"  Total: {round(time.time() - start, 2)}s | Cost: ${ep4_cost:.4f}")

        # EP6: DFS SERP Brand
        print(f"\n--- ENDPOINT 6: SERP Brand Name (DFS) ---")
        start = time.time()
        all_results["ep6_serp"] = await run_endpoint("EP6", endpoint_6_serp_brand, client, DOMAINS)
        ep6_cost = sum(r.get("raw_task_cost", 0) or 0 for r in all_results["ep6_serp"])
        total_cost += ep6_cost
        print(f"  Total: {round(time.time() - start, 2)}s | Cost: ${ep6_cost:.4f}")

        # EP5: DFS On-Page (slow — crawl required)
        print(f"\n--- ENDPOINT 5: On-Page Summary (DFS) ---")
        print(f"  NOTE: Requires crawl — may take 60s+ per domain")
        start = time.time()
        all_results["ep5_onpage"] = await run_endpoint("EP5", endpoint_5_onpage, client, DOMAINS)
        ep5_cost = sum(r.get("raw_task_cost", 0) or 0 for r in all_results["ep5_onpage"])
        total_cost += ep5_cost
        print(f"  Total: {round(time.time() - start, 2)}s | Cost: ${ep5_cost:.4f}")

        # EP8: Social Presence
        print(f"\n--- ENDPOINT 8: Social Presence ---")
        start = time.time()
        all_results["ep8_social"] = await run_endpoint("EP8", endpoint_8_social, client, DOMAINS)
        print(f"  Total: {round(time.time() - start, 2)}s | Cost: ~$0.00")

        # EP9: Jina (1 domain only)
        print(f"\n--- ENDPOINT 9: Jina AI Reader (1300smiles.com.au only) ---")
        start = time.time()
        all_results["ep9_jina"] = await run_endpoint("EP9", endpoint_9_jina, client, [DOMAINS[0]])
        print(f"  Total: {round(time.time() - start, 2)}s | Cost: $0.00")

        # EP2: GMB Lookup (slow — polling required, run last)
        print(f"\n--- ENDPOINT 2: GMB Lookup (Bright Data) ---")
        print(f"  NOTE: Requires polling — may take 30-120s per domain")
        start = time.time()
        all_results["ep2_gmb"] = await run_endpoint("EP2", endpoint_2_gmb_lookup, client, DOMAINS)
        ep2_cost = len([r for r in all_results["ep2_gmb"] if "error" not in r]) * 0.002
        total_cost += ep2_cost
        print(f"  Total: {round(time.time() - start, 2)}s | Cost: ~${ep2_cost:.4f}")

    # ============================================
    # OUTPUT
    # ============================================

    print(f"\n{'=' * 70}")
    print(f"RESULTS — VERBATIM")
    print(f"{'=' * 70}")

    for ep_name, ep_results in all_results.items():
        print(f"\n### {ep_name.upper()}")
        for r in ep_results:
            print(json.dumps(r, indent=2, default=str))

    print(f"\n{'=' * 70}")
    print(f"TOTAL COST: ${total_cost:.4f} USD")
    print(f"Completed: {datetime.now(timezone.utc).isoformat()}")
    print(f"{'=' * 70}")

    # Write JSON results to file
    output = {
        "directive": 276,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "total_cost_usd": round(total_cost, 4),
        "domains_tested": DOMAINS,
        "results": all_results,
    }

    with open("scripts/endpoint_validation_results.json", "w") as f:
        json.dump(output, f, indent=2, default=str)

    print(f"\nResults written to scripts/endpoint_validation_results.json")


if __name__ == "__main__":
    asyncio.run(main())
