#!/usr/bin/env python3
"""
DIRECTIVE #048 — Process Discovered Leads
Uses Sydney snapshot s_mlrjaadt198xmqen2p (315 records)
"""
import asyncio
import os
import sys
from pathlib import Path
from urllib.parse import urlparse

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

load_dotenv()
load_dotenv(os.path.expanduser("~/.config/agency-os/.env"))

import httpx

# Import ICP filter
from src.services.icp_filter_service import ICPFilterService

SNAPSHOT_ID = "s_mlrjaadt198xmqen2p"
TARGET_LEADS = 10

# Cost tracking
COSTS = {
    "t2_gmb": 0.001,
    "t1_abn": 0.00,
    "t1_5_linkedin": 0.0015,
    "t3_hunter": 0.012,
    "t_dm0_serp": 0.0015,
    "t_dm1_profile": 0.0015,
}

async def main():
    api_key = os.getenv("BRIGHTDATA_API_KEY")
    hunter_key = os.getenv("HUNTER_API_KEY")
    dfs_login = os.getenv("DATAFORSEO_LOGIN")
    dfs_pass = os.getenv("DATAFORSEO_PASSWORD")

    icp_filter = ICPFilterService()

    print("="*60, flush=True)
    print("DIRECTIVE #048 — Processing Sydney Leads", flush=True)
    print(f"Snapshot: {SNAPSHOT_ID}", flush=True)
    print("="*60, flush=True)

    # Fetch Sydney snapshot
    headers = {"Authorization": f"Bearer {api_key}"}

    async with httpx.AsyncClient(timeout=60.0) as client:
        print("\n📥 Fetching Sydney snapshot...", flush=True)
        resp = await client.get(
            f"https://api.brightdata.com/datasets/v3/snapshot/{SNAPSHOT_ID}",
            params={"format": "json"},
            headers=headers,
        )
        all_records = resp.json()
        print(f"   Total records: {len(all_records)}", flush=True)

    # Filter for ICP and select first 10
    print("\n🔍 Running ICP filter...", flush=True)
    qualified_leads = []

    for record in all_records:
        if "error" in record or not record.get("name"):
            continue

        # Check ICP
        qualified, details = icp_filter.is_icp_qualified({
            "company_name": record.get("name"),
            "categories": record.get("all_categories", []),
            "gmb_category": record.get("category"),
        })

        if qualified:
            lead = {
                "company_name": record.get("name"),
                "phone": record.get("phone_number"),
                "website": record.get("open_website"),
                "address": record.get("address"),
                "city": "Sydney",
                "state": "NSW",
                "gmb_category": record.get("category"),
                "gmb_all_categories": record.get("all_categories", []),
                "gmb_rating": record.get("rating"),
                "gmb_review_count": record.get("reviews_count", 0),
                "gmb_place_id": record.get("place_id"),
                "icp_reason": details.get("reason"),
                "cost_gmb": COSTS["t2_gmb"],
            }
            qualified_leads.append(lead)

            if len(qualified_leads) >= TARGET_LEADS:
                break

    print(f"   ICP Qualified: {len(qualified_leads)}/{len(all_records)}", flush=True)

    if len(qualified_leads) < TARGET_LEADS:
        print(f"   ⚠️ Only found {len(qualified_leads)} qualified leads", flush=True)

    # Process each lead through remaining tiers
    results = []
    total_cost = 0.0

    for i, lead in enumerate(qualified_leads, 1):
        print(f"\n{'='*60}", flush=True)
        print(f"LEAD {i}: {lead['company_name']}", flush=True)
        print(f"Category: {lead['gmb_category']}", flush=True)
        print(f"ICP: ✅ {lead['icp_reason']}", flush=True)
        print("="*60, flush=True)

        lead_cost = lead["cost_gmb"]

        # Extract domain from website
        domain = None
        if lead.get("website"):
            try:
                domain = urlparse(lead["website"]).netloc.replace("www.", "")
            except Exception:
                pass

        # T3: Hunter.io email discovery
        print("\n📧 T3: Hunter.io...", flush=True)
        if domain:
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    resp = await client.get(
                        "https://api.hunter.io/v2/domain-search",
                        params={"domain": domain, "api_key": hunter_key, "limit": 5},
                    )
                    data = resp.json().get("data", {})
                    emails = data.get("emails", [])

                    if emails:
                        # Find decision maker
                        priority = ["ceo", "chief executive", "managing director", "founder", "owner", "director"]
                        best = None
                        for em in emails:
                            title = (em.get("position") or "").lower()
                            if any(p in title for p in priority):
                                best = em
                                break
                        if not best:
                            best = emails[0]

                        lead["email"] = best.get("value")
                        lead["dm_first_name"] = best.get("first_name")
                        lead["dm_last_name"] = best.get("last_name")
                        lead["dm_title"] = best.get("position")
                        lead["dm_linkedin"] = best.get("linkedin")
                        lead["email_confidence"] = best.get("confidence")
                        lead_cost += COSTS["t3_hunter"]

                        print(f"   ✅ {lead['email']}", flush=True)
                        print(f"   DM: {lead.get('dm_first_name', '')} {lead.get('dm_last_name', '')} ({lead.get('dm_title', 'Unknown')})", flush=True)
                    else:
                        print("   ⚠️ No emails found", flush=True)
            except Exception as e:
                print(f"   ❌ Error: {e}", flush=True)
        else:
            print("   ⚠️ No domain available", flush=True)

        # T-DM0: DataForSEO SERP for LinkedIn DM profiles
        print("\n🔎 T-DM0: DataForSEO SERP...", flush=True)
        if not lead.get("dm_linkedin"):
            try:
                import base64
                auth = base64.b64encode(f"{dfs_login}:{dfs_pass}".encode()).decode()

                async with httpx.AsyncClient(timeout=60.0) as client:
                    query = f'site:linkedin.com/in "{lead["company_name"]}" CEO OR "Managing Director" OR "Founder"'
                    resp = await client.post(
                        "https://api.dataforseo.com/v3/serp/google/organic/live/advanced",
                        headers={"Authorization": f"Basic {auth}", "Content-Type": "application/json"},
                        json=[{
                            "keyword": query,
                            "location_code": 2036,
                            "language_code": "en",
                            "device": "desktop",
                            "depth": 10,
                        }],
                    )
                    data = resp.json()
                    items = data.get("tasks", [{}])[0].get("result", [{}])[0].get("items", [])

                    profiles = [i for i in items if "linkedin.com/in/" in i.get("url", "")]
                    lead_cost += COSTS["t_dm0_serp"]

                    if profiles:
                        lead["dm_linkedin"] = profiles[0].get("url")
                        lead["dm_serp_title"] = profiles[0].get("title")
                        print(f"   ✅ Found {len(profiles)} profile(s)", flush=True)
                        print(f"   {profiles[0].get('title', 'Unknown')[:60]}", flush=True)
                    else:
                        print("   ⚠️ No LinkedIn profiles found", flush=True)
            except Exception as e:
                print(f"   ❌ Error: {e}", flush=True)
        else:
            print(f"   ✅ Already have LinkedIn: {lead.get('dm_linkedin')}", flush=True)

        # Summary
        lead["total_cost"] = lead_cost
        total_cost += lead_cost
        results.append(lead)

        print(f"\n📊 Lead Cost: ${lead_cost:.4f} AUD", flush=True)

        # Brief pause
        await asyncio.sleep(1)

    # Final Report
    print("\n" + "="*60, flush=True)
    print("DIRECTIVE #048 — FINAL REPORT", flush=True)
    print("="*60, flush=True)

    # Tier table
    print("\n📊 Tier Hit/Miss Table:", flush=True)
    print("-"*80, flush=True)
    print(f"{'#':<3} {'Company':<30} {'ICP':<4} {'Email':<6} {'DM':<4} {'Cost':<8}", flush=True)
    print("-"*80, flush=True)

    email_found = 0
    dm_found = 0

    for i, r in enumerate(results, 1):
        has_email = "✓" if r.get("email") else "✗"
        has_dm = "✓" if r.get("dm_linkedin") or r.get("dm_first_name") else "✗"

        if r.get("email"):
            email_found += 1
        if r.get("dm_linkedin") or r.get("dm_first_name"):
            dm_found += 1

        print(f"{i:<3} {r['company_name'][:29]:<30} ✓    {has_email:<6} {has_dm:<4} ${r['total_cost']:.4f}", flush=True)

    print("-"*80, flush=True)

    # Metrics
    total = len(results)
    print("\n📈 Success Metrics:", flush=True)
    print(f"   ICP Pass Rate: {total}/{total} (100%)", flush=True)
    print(f"   Email Found: {email_found}/{total} ({100*email_found/total:.0f}%) — Target: ≥80%", flush=True)
    print(f"   DM Identified: {dm_found}/{total} ({100*dm_found/total:.0f}%) — Target: ≥70%", flush=True)

    print("\n💰 Cost Analysis:", flush=True)
    print(f"   Total Cost: ${total_cost:.4f} AUD", flush=True)
    print(f"   Cost per Lead: ${total_cost/total:.4f} AUD", flush=True)
    print("   Target: $0.065/lead", flush=True)
    variance = ((total_cost/total) - 0.065) / 0.065 * 100
    print(f"   Variance: {variance:+.1f}%", flush=True)

    # Per-lead summary
    print("\n📋 Per-Lead Summary:", flush=True)
    for i, r in enumerate(results, 1):
        dm_name = f"{r.get('dm_first_name', '')} {r.get('dm_last_name', '')}".strip() or "Not found"
        print(f"\n   Lead {i}: {r['company_name']}", flush=True)
        print(f"   Email: {r.get('email', 'Not found')}", flush=True)
        print(f"   DM: {dm_name} | Title: {r.get('dm_title', 'Unknown')}", flush=True)

    # Assessment
    print(f"\n{'='*60}", flush=True)
    print("🎯 PIPELINE ASSESSMENT", flush=True)
    print("="*60, flush=True)

    ready = email_found/total >= 0.8 and dm_found/total >= 0.7
    if ready:
        print("✅ Pipeline READY for live outreach", flush=True)
    else:
        print("❌ Pipeline NOT READY", flush=True)
        if email_found/total < 0.8:
            print(f"   ⚠️ Email rate {100*email_found/total:.0f}% < 80% target", flush=True)
        if dm_found/total < 0.7:
            print(f"   ⚠️ DM rate {100*dm_found/total:.0f}% < 70% target", flush=True)

if __name__ == "__main__":
    asyncio.run(main())
