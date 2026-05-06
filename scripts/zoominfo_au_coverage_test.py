#!/usr/bin/env python3
"""
DIRECTIVE #146 PART A - ZoomInfo AU Coverage Test
Test Bright Data ZoomInfo dataset coverage for Australian marketing agencies.
"""

import asyncio
import json
import httpx
import os
from datetime import datetime

# ZoomInfo dataset ID from inventory
ZOOMINFO_DATASET_ID = "gd_m0ci4a4ivx3j5l6nx"

# API Key from inventory
API_KEY = "2bab0747-ede2-4437-9b6f-6a77e8f0ca3e"

# Test agencies (known AU agencies to check coverage)
TEST_AGENCIES = [
    "Marketingmix Sydney",
    "Hogarth Australia",
    "VMLY&R Melbourne",
    "BWM Dentsu Sydney",
    "Special Group Australia",
    "The Monkeys Sydney",
    "Thinkerbell Melbourne",
    "Akcelo Sydney",
    "Paper Moose Sydney",
    "Kaimera Sydney",
    # Additional agencies to reach 50
    "Clemenger BBDO Melbourne",
    "DDB Sydney",
    "M&C Saatchi Sydney",
    "Ogilvy Australia",
    "TBWA Sydney",
    "Leo Burnett Sydney",
    "Wunderman Thompson Sydney",
    "Grey Australia",
    "Publicis Sydney",
    "Havas Australia",
    "CHE Proximity Melbourne",
    "Cummins&Partners Melbourne",
    "72andSunny Sydney",
    "The Brand Agency Perth",
    "Marketforce Perth",
    "BMF Sydney",
    "AJF Partnership Melbourne",
    "Bohemia Sydney",
    "Initiative Australia",
    "Mediacom Australia",
    "OMD Australia",
    "Zenith Australia",
    "PHD Australia",
    "Wavemaker Australia",
    "GroupM Australia",
    "IPG Mediabrands Australia",
    "Dentsu Australia",
    "Carat Australia",
    "iProspect Australia",
    "McCann Melbourne",
    "AKQA Sydney",
    "Digitas Australia",
    "Merkle Australia",
    "R/GA Sydney",
    "Interbrand Sydney",
    "Landor Sydney",
    "FutureBrand Australia",
    "Principals Sydney",
    "Re Sydney",
    "Hulsbosch Sydney",
]


async def test_zoominfo_discovery():
    """Test ZoomInfo discovery by search URL."""
    print("=" * 60)
    print("ZOOMINFO DISCOVERY TEST - AUSTRALIAN MARKETING AGENCIES")
    print("=" * 60)

    # Try search URL format for AU advertising/marketing industry
    search_inputs = [
        {
            "url": "https://www.zoominfo.com/companies-search/location-australia-industry-advertising-services"
        },
        {
            "url": "https://www.zoominfo.com/companies-search/location-australia-industry-marketing-services"
        },
    ]

    headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}

    trigger_url = f"https://api.brightdata.com/datasets/v3/trigger?dataset_id={ZOOMINFO_DATASET_ID}&include_errors=true"

    async with httpx.AsyncClient(timeout=120.0, verify=False) as client:
        print(f"\n[1] Triggering ZoomInfo discovery...")
        print(f"    Dataset ID: {ZOOMINFO_DATASET_ID}")
        print(f"    Inputs: {json.dumps(search_inputs, indent=2)}")

        try:
            response = await client.post(trigger_url, headers=headers, json=search_inputs)

            print(f"\n    Response Status: {response.status_code}")
            print(f"    Response: {response.text[:1000]}")

            if response.status_code == 200:
                data = response.json()
                snapshot_id = data.get("snapshot_id")
                print(f"\n[2] Snapshot created: {snapshot_id}")

                # Poll for completion (max 5 minutes)
                for i in range(60):
                    await asyncio.sleep(5)
                    progress = await client.get(
                        f"https://api.brightdata.com/datasets/v3/progress/{snapshot_id}",
                        headers=headers,
                    )
                    status_data = progress.json()
                    status = status_data.get("status")
                    print(
                        f"    Poll {i + 1}: Status={status}, Records={status_data.get('records', 0)}"
                    )

                    if status == "ready":
                        print("\n[3] Downloading results...")
                        results = await client.get(
                            f"https://api.brightdata.com/datasets/v3/snapshot/{snapshot_id}?format=json",
                            headers=headers,
                        )

                        if results.status_code == 200:
                            records = results.json()
                            print(f"    Retrieved {len(records)} records")

                            # Save raw results
                            with open(
                                "/home/elliotbot/clawd-build-2/scripts/zoominfo_au_raw_results.json",
                                "w",
                            ) as f:
                                json.dump(records, f, indent=2)

                            return records
                    elif status == "failed":
                        print(f"\n    JOB FAILED: {status_data}")
                        return None

        except Exception as e:
            print(f"\n    ERROR: {e}")
            import traceback

            traceback.print_exc()
            return None

    return None


async def test_specific_company_lookups():
    """Test looking up specific known companies by ZoomInfo URL or name."""
    print("\n" + "=" * 60)
    print("TESTING SPECIFIC COMPANY LOOKUPS VIA NAME SEARCH")
    print("=" * 60)

    # First, let's see what input formats ZoomInfo supports
    # Try company name search format
    test_inputs = []

    for agency in TEST_AGENCIES[:10]:  # Test first 10
        # Try constructing ZoomInfo search URLs
        search_term = agency.replace(" ", "-").lower()
        test_inputs.append(
            {"url": f"https://www.zoominfo.com/c/search?q={agency.replace(' ', '+')}"}
        )

    headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}

    trigger_url = f"https://api.brightdata.com/datasets/v3/trigger?dataset_id={ZOOMINFO_DATASET_ID}&include_errors=true"

    async with httpx.AsyncClient(timeout=120.0, verify=False) as client:
        print(f"\n[1] Testing name-based search inputs...")
        print(f"    Sample input: {test_inputs[0]}")

        try:
            response = await client.post(
                trigger_url,
                headers=headers,
                json=test_inputs[:5],  # Test 5 first
            )

            print(f"\n    Response Status: {response.status_code}")
            print(f"    Response: {response.text[:1000]}")

            if response.status_code == 200:
                return response.json()

        except Exception as e:
            print(f"    ERROR: {e}")

    return None


async def check_dataset_info():
    """Get dataset info to understand supported input formats."""
    print("\n" + "=" * 60)
    print("CHECKING ZOOMINFO DATASET INFO")
    print("=" * 60)

    headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}

    async with httpx.AsyncClient(timeout=30.0, verify=False) as client:
        # Get dataset details
        response = await client.get(
            f"https://api.brightdata.com/datasets/v3/dataset/{ZOOMINFO_DATASET_ID}", headers=headers
        )

        print(f"Status: {response.status_code}")
        print(f"Response: {response.text[:2000]}")

        return response.json() if response.status_code == 200 else None


async def main():
    print(f"Starting ZoomInfo AU Coverage Test at {datetime.now()}")
    print(f"Using API Key: {API_KEY[:8]}...")

    # First check what inputs the dataset supports
    dataset_info = await check_dataset_info()

    # Try discovery search
    discovery_results = await test_zoominfo_discovery()

    # If discovery fails, try specific lookups
    if not discovery_results:
        await test_specific_company_lookups()


if __name__ == "__main__":
    asyncio.run(main())
