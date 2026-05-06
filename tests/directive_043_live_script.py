#!/usr/bin/env python3
"""
Directive #043 — Live Social Tier Validation
Real Bright Data API calls only. No simulation.
"""

import asyncio
import json
import os
from datetime import datetime, timedelta
from pathlib import Path

import httpx

# Load env
from dotenv import load_dotenv

load_dotenv(Path.home() / ".config/agency-os/.env")
load_dotenv(Path(__file__).parent.parent / ".env")

API_KEY = os.environ.get("BRIGHTDATA_API_KEY")
if not API_KEY:
    raise RuntimeError("BRIGHTDATA_API_KEY not set")

# Dataset IDs
LINKEDIN_POSTS_DATASET = "gd_lyy3tktm25m4avu764"
X_POSTS_DATASET = "gd_lwxkxvnf1cynvib9co"

# Test leads
TEST_LEADS = [
    {
        "name": "Wayne Gant",
        "title": "Managing Director",
        "company": "Gant & Sons Pty Ltd",
        "linkedin_url": "https://www.linkedin.com/in/wayne-gant-32b665209",
        "website": "http://www.gantandsons.com.au",
    },
    {
        "name": "Darren Costa",
        "title": "Managing Director",
        "company": "RPR Trades",
        "linkedin_url": "https://www.linkedin.com/in/darrendacosta",
        "website": "http://www.rprtrades.com",
    },
    {
        "name": "Ben L'estrange",
        "title": "Managing Director",
        "company": "RTL Trades",
        "linkedin_url": "https://www.linkedin.com/in/ben-l-estrange-006a2222",
        "website": "http://www.rtltrades.com.au",
    },
]

# 90-day window
END_DATE = datetime.now()
START_DATE = END_DATE - timedelta(days=90)


async def test_linkedin_posts(client: httpx.AsyncClient, lead: dict) -> dict:
    """Task 1: Live T-DM2 test for LinkedIn Posts"""
    print(f"\n{'=' * 60}")
    print(f"T-DM2 TEST: {lead['name']} ({lead['company']})")
    print(f"LinkedIn URL: {lead['linkedin_url']}")
    print(f"Date window: {START_DATE.strftime('%Y-%m-%d')} to {END_DATE.strftime('%Y-%m-%d')}")
    print(f"{'=' * 60}")

    result = {
        "lead": lead["name"],
        "linkedin_url": lead["linkedin_url"],
        "success": False,
        "error": None,
        "posts_returned": 0,
        "posts": [],
        "oldest_post_date": None,
        "newest_post_date": None,
        "raw_response": None,
    }

    try:
        # Step 1: Trigger collection with date filters
        # LinkedIn uses YYYY-MM-DD format per docs
        trigger_payload = [
            {
                "url": lead["linkedin_url"],
                "start_date": START_DATE.strftime("%Y-%m-%d"),
                "end_date": END_DATE.strftime("%Y-%m-%d"),
            }
        ]

        print(f"Triggering with payload: {json.dumps(trigger_payload)}")

        trigger_resp = await client.post(
            "https://api.brightdata.com/datasets/v3/trigger",
            params={
                "dataset_id": LINKEDIN_POSTS_DATASET,
                "include_errors": "true",
            },
            headers={
                "Authorization": f"Bearer {API_KEY}",
                "Content-Type": "application/json",
            },
            json=trigger_payload,
        )

        print(f"Trigger response status: {trigger_resp.status_code}")
        print(f"Trigger response body: {trigger_resp.text[:500]}")

        if trigger_resp.status_code != 200:
            result["error"] = f"Trigger failed: {trigger_resp.status_code} - {trigger_resp.text}"
            return result

        snapshot_id = trigger_resp.json().get("snapshot_id")
        if not snapshot_id:
            result["error"] = f"No snapshot_id returned: {trigger_resp.text}"
            return result

        print(f"Snapshot ID: {snapshot_id}")

        # Step 2: Poll for completion (max 3 minutes)
        print("Polling for completion...")
        for i in range(36):  # 36 x 5s = 180s
            await asyncio.sleep(5)

            status_resp = await client.get(
                f"https://api.brightdata.com/datasets/v3/progress/{snapshot_id}",
                headers={"Authorization": f"Bearer {API_KEY}"},
            )
            status_data = status_resp.json()
            status = status_data.get("status")
            print(f"  Poll {i + 1}: {status}")

            if status == "ready":
                break
            elif status == "failed":
                result["error"] = f"Scrape failed: {status_data}"
                return result
        else:
            result["error"] = "Timeout waiting for results (180s)"
            return result

        # Step 3: Download results
        print("Downloading results...")
        data_resp = await client.get(
            f"https://api.brightdata.com/datasets/v3/snapshot/{snapshot_id}",
            params={"format": "json"},
            headers={"Authorization": f"Bearer {API_KEY}"},
        )

        posts_data = data_resp.json()
        result["raw_response"] = posts_data

        if not posts_data:
            result["error"] = "Empty response - no posts found"
            result["success"] = True  # API worked, just no posts
            return result

        # Step 4: Parse posts
        posts = []
        for post in posts_data:
            if "error" in post:
                print(f"  Post error: {post.get('error')}")
                continue

            posts.append(
                {
                    "post_text": post.get("post_text", "")[:500],  # Truncate for readability
                    "date_posted": post.get("date_posted"),
                    "num_likes": post.get("num_likes", 0),
                    "num_comments": post.get("num_comments", 0),
                    "hashtags": post.get("hashtags", []),
                }
            )

        result["success"] = True
        result["posts_returned"] = len(posts)
        result["posts"] = posts[:5]  # First 5 posts

        # Check date range
        dates = [p.get("date_posted") for p in posts if p.get("date_posted")]
        if dates:
            result["oldest_post_date"] = min(dates)
            result["newest_post_date"] = max(dates)

        print(f"\n✅ SUCCESS: {len(posts)} posts returned")
        for i, p in enumerate(posts[:3]):
            print(f"\n--- Post {i + 1} ---")
            print(f"Date: {p.get('date_posted')}")
            print(f"Likes: {p.get('num_likes')} | Comments: {p.get('num_comments')}")
            print(f"Text: {p.get('post_text', '')[:200]}...")

        return result

    except Exception as e:
        result["error"] = f"Exception: {str(e)}"
        print(f"❌ ERROR: {e}")
        return result


async def discover_x_handle(client: httpx.AsyncClient, lead: dict) -> str | None:
    """Discover X handle from website or SERP"""
    import re

    # Method 1: Scrape website for X/Twitter links
    if lead.get("website"):
        try:
            print(f"  Checking website for X handle: {lead['website']}")
            resp = await client.get(lead["website"], follow_redirects=True, timeout=15.0)
            html = resp.text

            patterns = [
                r"https?://(?:www\.)?(?:twitter|x)\.com/([a-zA-Z0-9_]+)",
            ]

            for pattern in patterns:
                matches = re.findall(pattern, html, re.IGNORECASE)
                valid = [
                    m
                    for m in matches
                    if m.lower() not in ("share", "intent", "home", "search", "i")
                ]
                if valid:
                    handle = valid[0]
                    print(f"  ✅ Found X handle from website: @{handle}")
                    return f"@{handle}"
        except Exception as e:
            print(f"  Website scrape failed: {e}")

    # Method 2: SERP fallback (would use DataForSEO, skipping for this test)
    print("  No X handle found from website")
    return None


async def test_x_posts(client: httpx.AsyncClient, lead: dict) -> dict:
    """Task 2: Live T-DM3 test for X Posts"""
    print(f"\n{'=' * 60}")
    print(f"T-DM3 TEST: {lead['name']} ({lead['company']})")
    print(f"{'=' * 60}")

    result = {
        "lead": lead["name"],
        "x_handle": None,
        "x_handle_source": None,
        "success": False,
        "error": None,
        "posts_returned": 0,
        "posts": [],
        "raw_response": None,
    }

    # Step 1: Discover X handle
    x_handle = await discover_x_handle(client, lead)

    if not x_handle:
        result["error"] = "No X handle found"
        result["success"] = True  # Not a failure, just no handle
        result["x_handle_source"] = "not_found"
        return result

    result["x_handle"] = x_handle
    result["x_handle_source"] = "website"

    try:
        # Step 2: Trigger X Posts collection
        # X uses MM-DD-YYYY format per docs
        handle = x_handle.lstrip("@")
        profile_url = f"https://x.com/{handle}"

        trigger_payload = [
            {
                "url": profile_url,
                "start_date": START_DATE.strftime("%m-%d-%Y"),
                "end_date": END_DATE.strftime("%m-%d-%Y"),
            }
        ]

        print(f"Triggering X Posts for {profile_url}")
        print(f"Payload: {json.dumps(trigger_payload)}")

        trigger_resp = await client.post(
            "https://api.brightdata.com/datasets/v3/trigger",
            params={
                "dataset_id": X_POSTS_DATASET,
                "include_errors": "true",
            },
            headers={
                "Authorization": f"Bearer {API_KEY}",
                "Content-Type": "application/json",
            },
            json=trigger_payload,
        )

        print(f"Trigger response status: {trigger_resp.status_code}")
        print(f"Trigger response body: {trigger_resp.text[:500]}")

        if trigger_resp.status_code != 200:
            result["error"] = f"Trigger failed: {trigger_resp.status_code} - {trigger_resp.text}"
            return result

        snapshot_id = trigger_resp.json().get("snapshot_id")
        if not snapshot_id:
            result["error"] = f"No snapshot_id returned: {trigger_resp.text}"
            return result

        print(f"Snapshot ID: {snapshot_id}")

        # Step 3: Poll for completion
        print("Polling for completion...")
        for i in range(36):
            await asyncio.sleep(5)

            status_resp = await client.get(
                f"https://api.brightdata.com/datasets/v3/progress/{snapshot_id}",
                headers={"Authorization": f"Bearer {API_KEY}"},
            )
            status_data = status_resp.json()
            status = status_data.get("status")
            print(f"  Poll {i + 1}: {status}")

            if status == "ready":
                break
            elif status == "failed":
                result["error"] = f"Scrape failed: {status_data}"
                return result
        else:
            result["error"] = "Timeout waiting for results"
            return result

        # Step 4: Download results
        print("Downloading results...")
        data_resp = await client.get(
            f"https://api.brightdata.com/datasets/v3/snapshot/{snapshot_id}",
            params={"format": "json"},
            headers={"Authorization": f"Bearer {API_KEY}"},
        )

        posts_data = data_resp.json()
        result["raw_response"] = posts_data

        if not posts_data:
            result["error"] = "Empty response - no posts found"
            result["success"] = True
            return result

        # Parse posts
        posts = []
        for post in posts_data:
            if "error" in post:
                continue
            posts.append(
                {
                    "content": post.get("description", "")[:500],
                    "date_posted": post.get("date_posted"),
                    "likes": post.get("likes", 0),
                    "reposts": post.get("reposts", 0),
                    "views": post.get("views", 0),
                }
            )

        result["success"] = True
        result["posts_returned"] = len(posts)
        result["posts"] = posts[:5]

        print(f"\n✅ SUCCESS: {len(posts)} X posts returned")
        for i, p in enumerate(posts[:3]):
            print(f"\n--- Post {i + 1} ---")
            print(f"Date: {p.get('date_posted')}")
            print(
                f"Likes: {p.get('likes')} | Reposts: {p.get('reposts')} | Views: {p.get('views')}"
            )
            print(f"Content: {p.get('content', '')[:200]}...")

        return result

    except Exception as e:
        result["error"] = f"Exception: {str(e)}"
        print(f"❌ ERROR: {e}")
        return result


async def main():
    print("=" * 70)
    print("DIRECTIVE #043 — LIVE SOCIAL TIER VALIDATION")
    print("Real Bright Data API calls. No simulation.")
    print("=" * 70)
    print(f"API Key: {API_KEY[:8]}...{API_KEY[-4:]}")
    print(f"Date Range: {START_DATE.strftime('%Y-%m-%d')} to {END_DATE.strftime('%Y-%m-%d')}")
    print(f"Test Leads: {len(TEST_LEADS)}")

    all_results = {
        "linkedin_posts": [],
        "x_posts": [],
    }

    async with httpx.AsyncClient(timeout=120.0) as client:
        # Task 1: LinkedIn Posts
        print("\n" + "=" * 70)
        print("TASK 1: T-DM2 LINKEDIN POSTS")
        print("=" * 70)

        for lead in TEST_LEADS:
            result = await test_linkedin_posts(client, lead)
            all_results["linkedin_posts"].append(result)

        # Task 2: X Posts
        print("\n" + "=" * 70)
        print("TASK 2: T-DM3 X POSTS")
        print("=" * 70)

        for lead in TEST_LEADS:
            result = await test_x_posts(client, lead)
            all_results["x_posts"].append(result)

    # Save results
    output_path = Path(__file__).parent / "directive_043_results.json"
    with open(output_path, "w") as f:
        # Exclude raw_response for cleaner output
        clean_results = {
            "linkedin_posts": [
                {k: v for k, v in r.items() if k != "raw_response"}
                for r in all_results["linkedin_posts"]
            ],
            "x_posts": [
                {k: v for k, v in r.items() if k != "raw_response"} for r in all_results["x_posts"]
            ],
            "timestamp": datetime.now().isoformat(),
            "date_range": {
                "start": START_DATE.strftime("%Y-%m-%d"),
                "end": END_DATE.strftime("%Y-%m-%d"),
            },
        }
        json.dump(clean_results, f, indent=2)

    print(f"\n\nResults saved to: {output_path}")

    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)

    li_posts = all_results["linkedin_posts"]
    li_success = sum(1 for r in li_posts if r["success"])
    li_total_posts = sum(r["posts_returned"] for r in li_posts)

    print("\nT-DM2 LinkedIn Posts:")
    print(f"  Successful API calls: {li_success}/{len(li_posts)}")
    print(f"  Total posts returned: {li_total_posts}")
    if li_success > 0:
        counts = [r["posts_returned"] for r in li_posts if r["success"]]
        print(
            f"  Posts per person: min={min(counts)}, max={max(counts)}, avg={sum(counts) / len(counts):.1f}"
        )

    x_posts = all_results["x_posts"]
    x_handles_found = sum(1 for r in x_posts if r["x_handle"])
    x_success = sum(1 for r in x_posts if r["success"] and r.get("posts_returned", 0) > 0)
    x_total_posts = sum(r["posts_returned"] for r in x_posts)

    print("\nT-DM3 X Posts:")
    print(f"  X handles found: {x_handles_found}/{len(x_posts)}")
    print(
        f"  Successful post retrievals: {x_success}/{x_handles_found if x_handles_found else len(x_posts)}"
    )
    print(f"  Total posts returned: {x_total_posts}")

    for r in li_posts:
        if r.get("error"):
            print(f"\n⚠️ LinkedIn error for {r['lead']}: {r['error']}")

    for r in x_posts:
        if r.get("error"):
            print(f"\n⚠️ X error for {r['lead']}: {r['error']}")


if __name__ == "__main__":
    asyncio.run(main())
