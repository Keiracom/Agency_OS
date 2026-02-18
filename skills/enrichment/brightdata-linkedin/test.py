#!/usr/bin/env python3
"""
Validation test for Bright Data LinkedIn enrichment.
"""
import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from dotenv import load_dotenv
load_dotenv()

import httpx

TEST_CASE = {
    "url": "https://www.linkedin.com/company/mustard-creative-media",
    "expected_name": "Mustard",
}

DATASET_ID = "gd_l1vikfnt1wgvvqz95w"


async def test():
    api_key = os.environ.get("BRIGHTDATA_API_KEY")
    if not api_key:
        print("❌ BLOCKED: BRIGHTDATA_API_KEY not set")
        return False
    print(f"✓ BRIGHTDATA_API_KEY configured: {api_key[:8]}...")
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        # Trigger
        print(f"\nTesting LinkedIn lookup for: {TEST_CASE['url']}")
        params = {"dataset_id": DATASET_ID, "include_errors": "true"}
        payload = [{"url": TEST_CASE["url"]}]
        
        response = await client.post(
            "https://api.brightdata.com/datasets/v3/trigger",
            params=params, headers=headers, json=payload
        )
        
        if response.status_code != 200:
            print(f"❌ FAIL: Trigger failed - {response.status_code}")
            return False
        
        snapshot_id = response.json().get("snapshot_id")
        print(f"   Snapshot: {snapshot_id}")
        
        # Poll (max 15 seconds for test)
        for i in range(5):
            await asyncio.sleep(3)
            snap_response = await client.get(
                f"https://api.brightdata.com/datasets/v3/snapshot/{snapshot_id}",
                headers=headers, params={"format": "json"}
            )
            
            if snap_response.status_code == 200:
                data = snap_response.json()
                if isinstance(data, list) and len(data) > 0:
                    name = data[0].get("name", "")
                    if TEST_CASE["expected_name"].lower() in name.lower():
                        print(f"✅ PASS: LinkedIn enrichment working")
                        print(f"   Company: {name}")
                        print(f"   Industry: {data[0].get('industries', 'N/A')}")
                        return True
        
        print("❌ FAIL: Timeout or no data")
        return False


if __name__ == "__main__":
    success = asyncio.run(test())
    sys.exit(0 if success else 1)
