#!/usr/bin/env python3
"""
Bright Data LinkedIn Company Enrichment Skill
Usage: python run.py --url "https://www.linkedin.com/company/company-name"
"""
import asyncio
import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from dotenv import load_dotenv
load_dotenv()

import httpx

DATASET_ID = "gd_l1vikfnt1wgvvqz95w"
TRIGGER_URL = "https://api.brightdata.com/datasets/v3/trigger"
SNAPSHOT_URL = "https://api.brightdata.com/datasets/v3/snapshot"


async def main(url: str):
    api_key = os.environ.get("BRIGHTDATA_API_KEY")
    if not api_key:
        print("Error: BRIGHTDATA_API_KEY not set")
        sys.exit(1)
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        # Trigger collection
        params = {"dataset_id": DATASET_ID, "include_errors": "true"}
        payload = [{"url": url}]
        
        response = await client.post(TRIGGER_URL, params=params, headers=headers, json=payload)
        
        if response.status_code != 200:
            print(f"Error triggering: {response.status_code} - {response.text}")
            sys.exit(1)
        
        snapshot_id = response.json().get("snapshot_id")
        print(f"Snapshot ID: {snapshot_id}")
        print("Waiting for processing...")
        
        # Poll for results (max 30 seconds)
        for _ in range(10):
            await asyncio.sleep(3)
            
            snapshot_response = await client.get(
                f"{SNAPSHOT_URL}/{snapshot_id}",
                headers=headers,
                params={"format": "json"}
            )
            
            if snapshot_response.status_code == 200:
                data = snapshot_response.json()
                if isinstance(data, list) and len(data) > 0:
                    print(json.dumps(data[0], indent=2))
                    return data[0]
        
        print("Timeout waiting for results")
        sys.exit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Bright Data LinkedIn Company Enrichment")
    parser.add_argument("--url", required=True, help="LinkedIn company URL")
    args = parser.parse_args()
    
    asyncio.run(main(args.url))
