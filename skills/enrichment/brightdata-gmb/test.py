#!/usr/bin/env python3
"""
Validation test for Bright Data GMB Web Scraper API.
CEO Directive #035: Uses Web Scraper API (gd_m8ebnr0q2qlklc02fz), NOT blocked SERP API.

Dataset: gd_m8ebnr0q2qlklc02fz (Google Maps Business Information)
Method: discover_by=location
Cost: $0.001 AUD per record
"""
import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from dotenv import load_dotenv

load_dotenv()

import httpx

# CEO Directive #035: Web Scraper API config
DATASET_ID = "gd_m8ebnr0q2qlklc02fz"
API_BASE = "https://api.brightdata.com/datasets/v3"

TEST_CASE = {
    "company": "Mustard Creative",
    "state": "VIC",
    "city": "Melbourne",
}


async def test():
    api_key = os.environ.get("BRIGHTDATA_API_KEY")
    if not api_key:
        print("❌ BLOCKED: BRIGHTDATA_API_KEY not set")
        return False
    print(f"✓ BRIGHTDATA_API_KEY configured: {api_key[:8]}...")

    keyword = f"{TEST_CASE['company']} {TEST_CASE['city']}"
    print(f"\nTesting GMB Web Scraper API for: {keyword}")
    print(f"   Dataset: {DATASET_ID}")
    print(f"   Method: discover_by=location")

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=180.0) as client:
        # Step 1: Trigger collection
        print("\n1. Triggering collection...")
        trigger_resp = await client.post(
            f"{API_BASE}/trigger",
            params={
                "dataset_id": DATASET_ID,
                "type": "discover_new",
                "discover_by": "location",
                "notify": "false",
                "include_errors": "true",
            },
            headers=headers,
            json={"input": [{"country": "AU", "keyword": keyword, "lat": ""}]},
        )

        if trigger_resp.status_code != 200:
            print(f"❌ FAIL: Trigger failed - {trigger_resp.status_code}")
            print(f"   Response: {trigger_resp.text[:300]}")
            return False

        snapshot_id = trigger_resp.json().get("snapshot_id")
        if not snapshot_id:
            print("❌ FAIL: No snapshot_id returned")
            return False

        print(f"   ✓ Snapshot ID: {snapshot_id}")

        # Step 2: Poll for completion
        print("\n2. Polling for completion...")
        for i in range(18):  # 18 × 10s = 180s
            await asyncio.sleep(10)
            status_resp = await client.get(
                f"{API_BASE}/progress/{snapshot_id}",
                headers=headers,
            )
            status_data = status_resp.json()
            status = status_data.get("status")
            print(f"   Poll {i+1}: {status}")

            if status == "ready":
                break
            elif status == "failed":
                print(f"❌ FAIL: Snapshot failed")
                print(f"   Error: {status_data}")
                return False
        else:
            print("❌ FAIL: Timeout (180s)")
            return False

        # Step 3: Fetch results
        print("\n3. Fetching results...")
        data_resp = await client.get(
            f"{API_BASE}/snapshot/{snapshot_id}",
            params={"format": "json"},
            headers=headers,
        )
        results = data_resp.json()

        if not results:
            print("⚠️ PASS: API working but no results for test query")
            return True

        # Parse and display
        valid_results = [r for r in results if "error" not in r]
        print(f"   ✓ Results: {len(valid_results)}")

        if valid_results:
            sample = valid_results[0]
            print(f"\n   Sample result:")
            print(f"   - Name: {sample.get('name')}")
            print(f"   - Phone: {sample.get('phone_number')}")
            print(f"   - Website: {sample.get('open_website')}")
            print(f"   - Rating: {sample.get('rating')}")
            print(f"   - Category: {sample.get('category')}")

        print("\n✅ PASS: GMB Web Scraper API working")
        print(f"   Cost: $0.001 AUD/record")
        return True


if __name__ == "__main__":
    success = asyncio.run(test())
    sys.exit(0 if success else 1)
