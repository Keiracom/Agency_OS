#!/usr/bin/env python3
"""
Bright Data GMB Enrichment - Web Scraper API (gd_m8ebnr0q2qlklc02fz)
CEO Directive #035: Migrated from blocked SERP API (serp_api1) to Web Scraper API

Usage: python run.py --company "Mustard Creative" --state VIC
"""
import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from dotenv import load_dotenv

load_dotenv()

import httpx

# CEO Directive #035: Web Scraper API (NOT SERP)
DATASET_ID = "gd_m8ebnr0q2qlklc02fz"
API_BASE = "https://api.brightdata.com/datasets/v3"

# State to city mapping for keyword search
STATE_CITY_MAP = {
    "NSW": "Sydney",
    "VIC": "Melbourne",
    "QLD": "Brisbane",
    "WA": "Perth",
    "SA": "Adelaide",
    "TAS": "Hobart",
    "ACT": "Canberra",
    "NT": "Darwin",
}


async def main(company: str, state: str, timeout_seconds: int = 180):
    api_key = os.environ.get("BRIGHTDATA_API_KEY")
    if not api_key:
        print("Error: BRIGHTDATA_API_KEY not set")
        sys.exit(1)

    city = STATE_CITY_MAP.get(state.upper(), state)
    keyword = f"{company} {city}"

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=float(timeout_seconds)) as client:
        # Step 1: Trigger collection (discover_by=location)
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
            print(f"Error: Trigger failed - {trigger_resp.status_code}")
            print(trigger_resp.text[:500])
            sys.exit(1)

        snapshot_id = trigger_resp.json().get("snapshot_id")
        if not snapshot_id:
            print("Error: No snapshot_id returned")
            sys.exit(1)

        print(f"Triggered snapshot: {snapshot_id}", file=sys.stderr)

        # Step 2: Poll for completion (max 3 minutes)
        for i in range(18):  # 18 × 10s = 180s
            await asyncio.sleep(10)
            status_resp = await client.get(
                f"{API_BASE}/progress/{snapshot_id}",
                headers=headers,
            )
            status_data = status_resp.json()
            status = status_data.get("status")
            print(f"  Poll {i+1}: {status}", file=sys.stderr)

            if status == "ready":
                break
            elif status == "failed":
                print(f"Error: Snapshot failed - {status_data}")
                sys.exit(1)
        else:
            print("Error: Timeout waiting for snapshot")
            sys.exit(1)

        # Step 3: Fetch results
        data_resp = await client.get(
            f"{API_BASE}/snapshot/{snapshot_id}",
            params={"format": "json"},
            headers=headers,
        )
        results = data_resp.json()

        if not results:
            output = {
                "company": company,
                "state": state,
                "results": [],
                "total_results": 0,
                "cost_aud": 0.001,
            }
            print(json.dumps(output, indent=2))
            return output

        # Step 4: Parse and output results
        parsed = []
        for r in results:
            if "error" in r:
                continue
            parsed.append({
                "name": r.get("name"),
                "phone": r.get("phone_number"),
                "website": r.get("open_website"),
                "address": r.get("address"),
                "rating": r.get("rating"),
                "reviews_count": r.get("reviews_count"),
                "category": r.get("category"),
                "all_categories": r.get("all_categories", []),
                "place_id": r.get("place_id"),
            })

        output = {
            "company": company,
            "state": state,
            "keyword": keyword,
            "results": parsed,
            "total_results": len(parsed),
            "cost_aud": 0.001,
        }

        print(json.dumps(output, indent=2))
        return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Bright Data GMB Web Scraper API")
    parser.add_argument("--company", required=True, help="Company name to search")
    parser.add_argument("--state", required=True, help="Australian state (NSW, VIC, etc.)")
    parser.add_argument("--timeout", type=int, default=180, help="Timeout in seconds")
    args = parser.parse_args()

    asyncio.run(main(args.company, args.state, args.timeout))
