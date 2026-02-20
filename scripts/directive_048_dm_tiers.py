#!/usr/bin/env python3
"""
DIRECTIVE #048 Follow-up — T-DM1, T-DM2, T-DM3
Execute remaining DM tiers for all 10 leads.

Datasets (from ceo_memory):
- T-DM1: gd_l1viktl72bvl7bjuj0 (LinkedIn Profile)
- T-DM2: gd_lyy3tktm25m4avu764 (LinkedIn Posts)
- T-DM3: gd_lwxkxvnf1cynvib9co (X Posts)

Law III: Real API calls only.
"""
import asyncio
import base64
import os
import re
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

load_dotenv()
load_dotenv(os.path.expanduser("~/.config/agency-os/.env"))

import httpx

# Dataset IDs
LINKEDIN_PROFILE_DATASET = "gd_l1viktl72bvl7bjuj0"
LINKEDIN_POSTS_DATASET = "gd_lyy3tktm25m4avu764"
X_POSTS_DATASET = "gd_lwxkxvnf1cynvib9co"

# Costs (AUD)
COSTS = {
    "t_dm1_profile": 0.0015,
    "t_dm2_posts": 0.001,
    "t_dm3_x": 0.001,
}

# The 10 leads from #048 with their DM LinkedIn URLs
LEADS = [
    {
        "company_name": "True Sydney",
        "dm_linkedin": "https://www.linkedin.com/in/eric-stephens-true-sydney",  # From SERP
        "website": "http://www.truesyd.com.au/",
    },
    {
        "company_name": "AdVisible",
        "dm_linkedin": "https://www.linkedin.com/in/ivan-teh",
        "dm_name": "Ivan Teh",
        "dm_title": "Co-Founder",
        "email": "ivan@advisible.com.au",
        "website": "https://advisible.com.au",
    },
    {
        "company_name": "Sydney Digital Marketing",
        "dm_linkedin": "https://www.linkedin.com/in/cedricpaq",
        "dm_name": "Cedric Paquotte",
        "dm_title": "Director of Design",
        "email": "cedric@sydneydigitalmarketing.com.au",
        "website": "https://sydneydigitalmarketing.com.au",
    },
    {
        "company_name": "Defiant Digital Marketing Agency",
        "dm_linkedin": "https://www.linkedin.com/in/joel-burrows",
        "dm_name": "Joel Burrows",
        "dm_title": "Creative Director",
        "email": "joel@defiantdigital.com.au",
        "website": "https://defiantdigital.com.au",
    },
    {
        "company_name": "Rocket Agency",
        "dm_linkedin": "https://www.linkedin.com/in/jameslawrenceoz",
        "dm_name": "James Lawrence",
        "dm_title": "Co-Founder",
        "email": "jamesl@rocketagency.com.au",
        "website": "https://rocketagency.com.au",
    },
    {
        "company_name": "XLR8 Media",
        "dm_linkedin": "https://www.linkedin.com/in/jordanps",
        "dm_name": "Jordan Peters",
        "dm_title": "Director of Business Development",
        "email": "jordan@xlr8.media",
        "website": "https://xlr8.media",
    },
    {
        "company_name": "Melotti Content Media",
        "dm_linkedin": "https://www.linkedin.com/in/angela-melotti",
        "dm_name": "Angela Melotti",
        "dm_title": "Managing Director",
        "email": "angela@melottimedia.com.au",
        "website": "https://melottimedia.com.au",
    },
    {
        "company_name": "Nifty Marketing Australia",
        "dm_linkedin": "https://www.linkedin.com/in/tarik-derek-ozen",
        "dm_name": "Derek Ozen",
        "dm_title": "Marketing Director",
        "email": "derek@niftymarketing.com.au",
        "website": "https://niftymarketing.com.au",
    },
    {
        "company_name": "Scale Smart Marketing",
        "dm_linkedin": "https://www.linkedin.com/in/adrienperezbrisbane",
        "dm_name": "Adrien Perez",
        "dm_title": "Digital Marketing Manager",
        "email": "adrien@scalesmartmarketing.com",
        "website": "https://scalesmartmarketing.com",
    },
    {
        "company_name": "The Level Up",
        "dm_linkedin": "https://www.linkedin.com/in/kevin-j-balighot",
        "dm_name": "Kevin Balighot",
        "dm_title": "CEO",
        "email": "kevin@thelevelup.ai",
        "website": "https://thelevelup.ai",
    },
]


async def trigger_and_poll(client, headers, dataset_id, inputs, timeout_min=10, discover_by=None):
    """Trigger Bright Data dataset and poll until ready."""
    # Trigger
    params = {
        "dataset_id": dataset_id,
        "include_errors": "true",
    }
    if discover_by:
        params["type"] = "discover_new"
        params["discover_by"] = discover_by

    resp = await client.post(
        "https://api.brightdata.com/datasets/v3/trigger",
        params=params,
        headers=headers,
        json=inputs,
    )
    resp.raise_for_status()
    snapshot_id = resp.json().get("snapshot_id")

    # Poll
    max_polls = timeout_min * 12
    for _ in range(max_polls):
        await asyncio.sleep(5)
        status_resp = await client.get(
            f"https://api.brightdata.com/datasets/v3/progress/{snapshot_id}",
            headers=headers,
        )
        data = status_resp.json()
        if data.get("status") == "ready":
            # Fetch results
            result_resp = await client.get(
                f"https://api.brightdata.com/datasets/v3/snapshot/{snapshot_id}",
                params={"format": "json"},
                headers=headers,
            )
            return result_resp.json()
        elif data.get("status") == "failed":
            return None
    return None


async def find_x_handle(client, website, company_name, dfs_auth):
    """Find X/Twitter handle from website or SERP."""
    handle = None

    # Method 1: Check website HTML for Twitter/X links
    if website:
        try:
            resp = await client.get(website, timeout=10.0, follow_redirects=True)
            html = resp.text.lower()

            # Look for twitter.com or x.com links
            patterns = [
                r'(?:twitter\.com|x\.com)/([a-zA-Z0-9_]+)',
            ]
            for pattern in patterns:
                match = re.search(pattern, html, re.IGNORECASE)
                if match:
                    handle = match.group(1)
                    if handle not in ['share', 'intent', 'search', 'home']:
                        return handle
        except Exception:
            pass

    # Method 2: DataForSEO SERP fallback
    if not handle:
        try:
            query = f'site:twitter.com OR site:x.com "{company_name}"'
            resp = await client.post(
                "https://api.dataforseo.com/v3/serp/google/organic/live/advanced",
                headers={"Authorization": f"Basic {dfs_auth}", "Content-Type": "application/json"},
                json=[{
                    "keyword": query,
                    "location_code": 2036,
                    "language_code": "en",
                    "depth": 5,
                }],
                timeout=30.0,
            )
            data = resp.json()
            items = data.get("tasks", [{}])[0].get("result", [{}])[0].get("items", [])

            for item in items:
                url = item.get("url", "")
                match = re.search(r'(?:twitter\.com|x\.com)/([a-zA-Z0-9_]+)', url)
                if match:
                    handle = match.group(1)
                    if handle not in ['share', 'intent', 'search', 'home', 'hashtag']:
                        return handle
        except Exception:
            pass

    return None


async def main():
    api_key = os.getenv("BRIGHTDATA_API_KEY")
    dfs_login = os.getenv("DATAFORSEO_LOGIN")
    dfs_pass = os.getenv("DATAFORSEO_PASSWORD")
    dfs_auth = base64.b64encode(f"{dfs_login}:{dfs_pass}".encode()).decode()

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    print("="*70, flush=True)
    print("DIRECTIVE #048 Follow-up — T-DM1, T-DM2, T-DM3", flush=True)
    print("="*70, flush=True)
    print(f"T-DM1 Dataset: {LINKEDIN_PROFILE_DATASET}", flush=True)
    print(f"T-DM2 Dataset: {LINKEDIN_POSTS_DATASET}", flush=True)
    print(f"T-DM3 Dataset: {X_POSTS_DATASET}", flush=True)
    print("="*70, flush=True)

    results = []
    total_cost = 0.0
    cutoff_date = datetime.now(UTC) - timedelta(days=90)

    async with httpx.AsyncClient(timeout=120.0) as client:
        for i, lead in enumerate(LEADS, 1):
            print(f"\n{'='*70}", flush=True)
            print(f"LEAD {i}: {lead['company_name']}", flush=True)
            print(f"DM LinkedIn: {lead.get('dm_linkedin', 'None')}", flush=True)
            print("="*70, flush=True)

            lead_result = {
                "company": lead["company_name"],
                "dm_name": lead.get("dm_name"),
                "dm_title": lead.get("dm_title"),
                "dm_linkedin": lead.get("dm_linkedin"),
                "profile": None,
                "linkedin_posts": [],
                "linkedin_posts_90d": 0,
                "x_handle": None,
                "x_posts": [],
                "x_posts_90d": 0,
                "cost": 0.0,
            }

            # T-DM1: LinkedIn Profile
            if lead.get("dm_linkedin"):
                print("\n👤 T-DM1: LinkedIn Profile Scrape...", flush=True)
                try:
                    profile_data = await trigger_and_poll(
                        client, headers,
                        LINKEDIN_PROFILE_DATASET,
                        [{"url": lead["dm_linkedin"]}],
                        timeout_min=5,
                    )

                    if profile_data and len(profile_data) > 0:
                        p = profile_data[0] if isinstance(profile_data, list) else profile_data
                        lead_result["profile"] = {
                            "name": p.get("name") or p.get("full_name"),
                            "headline": p.get("headline"),
                            "about": (p.get("about") or p.get("summary") or "")[:300],
                            "location": p.get("location"),
                            "experience": [],
                        }

                        # Extract experience
                        exp = p.get("experience") or p.get("positions") or []
                        for e in exp[:3]:
                            if isinstance(e, dict):
                                lead_result["profile"]["experience"].append({
                                    "title": e.get("title"),
                                    "company": e.get("company") or e.get("company_name"),
                                })

                        lead_result["cost"] += COSTS["t_dm1_profile"]
                        print(f"   ✅ {lead_result['profile']['name']}", flush=True)
                        print(f"   {lead_result['profile']['headline'][:60] if lead_result['profile']['headline'] else 'No headline'}...", flush=True)
                    else:
                        print("   ⚠️ No profile data returned", flush=True)
                except Exception as e:
                    print(f"   ❌ Error: {e}", flush=True)

            # T-DM2: LinkedIn Posts 90d
            if lead.get("dm_linkedin"):
                print("\n📝 T-DM2: LinkedIn Posts (90d)...", flush=True)
                try:
                    posts_data = await trigger_and_poll(
                        client, headers,
                        LINKEDIN_POSTS_DATASET,
                        [{"url": lead["dm_linkedin"]}],
                        timeout_min=5,
                        discover_by="profile_url",
                    )

                    if posts_data:
                        posts_list = posts_data if isinstance(posts_data, list) else [posts_data]

                        for post in posts_list:
                            if isinstance(post, dict) and not post.get("error"):
                                # Get posts from the response
                                post_items = post.get("posts") or post.get("activities") or []
                                if not post_items and post.get("text"):
                                    post_items = [post]

                                for p in post_items:
                                    if isinstance(p, dict):
                                        post_date_str = p.get("date") or p.get("posted_at") or p.get("timestamp")
                                        post_text = p.get("text") or p.get("content") or ""

                                        # Filter to 90 days (if date available)
                                        include = True
                                        if post_date_str:
                                            try:
                                                # Try parsing date
                                                if isinstance(post_date_str, str):
                                                    for _fmt in ["%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%d %b %Y"]:
                                                        try:
                                                            post_date = datetime.strptime(post_date_str[:10], "%Y-%m-%d")
                                                            post_date = post_date.replace(tzinfo=UTC)
                                                            if post_date < cutoff_date:
                                                                include = False
                                                            break
                                                        except ValueError:
                                                            continue
                                            except Exception:
                                                pass

                                        if include and post_text:
                                            lead_result["linkedin_posts"].append({
                                                "text": post_text[:200],
                                                "date": post_date_str,
                                            })

                        lead_result["linkedin_posts_90d"] = len(lead_result["linkedin_posts"])
                        lead_result["cost"] += COSTS["t_dm2_posts"]

                        if lead_result["linkedin_posts"]:
                            print(f"   ✅ {lead_result['linkedin_posts_90d']} posts found", flush=True)
                            for j, p in enumerate(lead_result["linkedin_posts"][:2]):
                                print(f"   [{j+1}] \"{p['text'][:80]}...\"", flush=True)
                        else:
                            print("   ⚠️ No posts in last 90d", flush=True)
                    else:
                        print("   ⚠️ No posts data returned", flush=True)
                        lead_result["cost"] += COSTS["t_dm2_posts"]
                except Exception as e:
                    print(f"   ❌ Error: {e}", flush=True)

            # T-DM3: X Posts 90d
            print("\n🐦 T-DM3: X/Twitter Posts (90d)...", flush=True)

            # First find X handle
            x_handle = await find_x_handle(client, lead.get("website"), lead["company_name"], dfs_auth)
            lead_result["x_handle"] = x_handle

            if x_handle:
                print(f"   Found handle: @{x_handle}", flush=True)
                try:
                    x_data = await trigger_and_poll(
                        client, headers,
                        X_POSTS_DATASET,
                        [{"url": f"https://x.com/{x_handle}"}],
                        timeout_min=5,
                        discover_by="profile_url",
                    )

                    if x_data:
                        x_list = x_data if isinstance(x_data, list) else [x_data]

                        for item in x_list:
                            if isinstance(item, dict) and not item.get("error"):
                                tweets = item.get("tweets") or item.get("posts") or []
                                if not tweets and item.get("text"):
                                    tweets = [item]

                                for t in tweets:
                                    if isinstance(t, dict):
                                        tweet_text = t.get("text") or t.get("full_text") or ""
                                        tweet_date = t.get("date") or t.get("created_at")

                                        if tweet_text:
                                            lead_result["x_posts"].append({
                                                "text": tweet_text[:200],
                                                "date": tweet_date,
                                            })

                        lead_result["x_posts_90d"] = len(lead_result["x_posts"])
                        lead_result["cost"] += COSTS["t_dm3_x"]

                        if lead_result["x_posts"]:
                            print(f"   ✅ {lead_result['x_posts_90d']} tweets found", flush=True)
                            for j, t in enumerate(lead_result["x_posts"][:2]):
                                print(f"   [{j+1}] \"{t['text'][:80]}...\"", flush=True)
                        else:
                            print("   ⚠️ No tweets in last 90d", flush=True)
                    else:
                        print("   ⚠️ No X data returned", flush=True)
                except Exception as e:
                    print(f"   ❌ Error: {e}", flush=True)
            else:
                print("   ⚠️ No X handle found (skipped gracefully)", flush=True)

            total_cost += lead_result["cost"]
            results.append(lead_result)

            print(f"\n📊 Lead T-DM Cost: ${lead_result['cost']:.4f} AUD", flush=True)

            await asyncio.sleep(1)

    # Final Report
    print("\n" + "="*70, flush=True)
    print("DIRECTIVE #048 — T-DM TIERS REPORT", flush=True)
    print("="*70, flush=True)

    # Summary table
    print("\n📊 T-DM Tier Results:", flush=True)
    print("-"*90, flush=True)
    print(f"{'#':<3} {'Company':<25} {'Profile':<8} {'LI Posts':<10} {'X Handle':<12} {'X Posts':<8}", flush=True)
    print("-"*90, flush=True)

    profile_found = 0
    li_posts_found = 0
    x_handle_found = 0
    x_posts_found = 0

    for i, r in enumerate(results, 1):
        has_profile = "✓" if r["profile"] else "✗"
        li_posts = str(r["linkedin_posts_90d"]) if r["linkedin_posts_90d"] > 0 else "0"
        x_handle = f"@{r['x_handle'][:10]}" if r["x_handle"] else "✗"
        x_posts = str(r["x_posts_90d"]) if r["x_posts_90d"] > 0 else "0"

        if r["profile"]:
            profile_found += 1
        if r["linkedin_posts_90d"] > 0:
            li_posts_found += 1
        if r["x_handle"]:
            x_handle_found += 1
        if r["x_posts_90d"] > 0:
            x_posts_found += 1

        print(f"{i:<3} {r['company'][:24]:<25} {has_profile:<8} {li_posts:<10} {x_handle:<12} {x_posts:<8}", flush=True)

    print("-"*90, flush=True)

    # Metrics
    total = len(results)
    print("\n📈 T-DM Completion Rates:", flush=True)
    print(f"   T-DM1 Profile Retrieved: {profile_found}/{total} ({100*profile_found/total:.0f}%) — Target: ≥70%", flush=True)
    print(f"   T-DM2 LinkedIn Posts Found: {li_posts_found}/{total} ({100*li_posts_found/total:.0f}%) — Target: ≥60%", flush=True)
    print(f"   T-DM3 X Handle Found: {x_handle_found}/{total} ({100*x_handle_found/total:.0f}%)", flush=True)
    print(f"   T-DM3 X Posts Found: {x_posts_found}/{total} ({100*x_posts_found/total:.0f}%)", flush=True)

    # Cost
    print("\n💰 T-DM Cost Analysis:", flush=True)
    print(f"   Total T-DM Cost: ${total_cost:.4f} AUD", flush=True)
    print(f"   T-DM Cost per Lead: ${total_cost/total:.4f} AUD", flush=True)

    # Per-lead detail
    print("\n📋 Per-Lead Detail:", flush=True)
    print("="*70, flush=True)

    for i, r in enumerate(results, 1):
        print(f"\n🏢 Lead {i}: {r['company']}", flush=True)

        if r["profile"]:
            print(f"   DM: {r['profile']['name']}", flush=True)
            print(f"   Title: {r['profile']['headline'] or 'Unknown'}", flush=True)
            if r["profile"]["about"]:
                print(f"   About: \"{r['profile']['about'][:150]}...\"", flush=True)
            if r["profile"]["experience"]:
                print("   Experience:", flush=True)
                for exp in r["profile"]["experience"][:2]:
                    print(f"      - {exp.get('title')} at {exp.get('company')}", flush=True)
        else:
            print(f"   DM: {r.get('dm_name', 'Unknown')}", flush=True)

        print(f"\n   LinkedIn Posts (90d): {r['linkedin_posts_90d']}", flush=True)
        if r["linkedin_posts"]:
            for j, p in enumerate(r["linkedin_posts"][:3]):
                print(f"      [{j+1}] \"{p['text'][:100]}...\"", flush=True)
        else:
            print("      (No posts found)", flush=True)

        print(f"\n   X/Twitter: {'@' + r['x_handle'] if r['x_handle'] else 'Not found'}", flush=True)
        if r["x_posts"]:
            print(f"   X Posts (90d): {r['x_posts_90d']}", flush=True)
            for j, t in enumerate(r["x_posts"][:3]):
                print(f"      [{j+1}] \"{t['text'][:100]}...\"", flush=True)
        elif r["x_handle"]:
            print("   X Posts (90d): 0", flush=True)

        # Personalisation assessment
        has_li_posts = r["linkedin_posts_90d"] > 0
        has_x_posts = r["x_posts_90d"] > 0
        has_about = r["profile"] and r["profile"].get("about")

        if has_li_posts or has_x_posts:
            print("\n   ✅ PERSONALISATION SIGNAL: Posts available", flush=True)
        elif has_about:
            print("\n   ⚠️ PARTIAL SIGNAL: About section only", flush=True)
        else:
            print("\n   ❌ NO PERSONALISATION SIGNAL", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
