#!/usr/bin/env python3
"""
Bright Data Google Maps SERP Enrichment Skill
Replaces deprecated DIY GMB scraper (CEO Directive #031)
Usage: python run.py --query "marketing agency Melbourne" [--location "VIC"] [--limit 5]
"""
import argparse
import asyncio
import json
import os
import sys
from pathlib import Path
from urllib.parse import quote_plus

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from dotenv import load_dotenv

load_dotenv()

import httpx

SERP_ZONE = "serp_api1"
SERP_URL = "https://api.brightdata.com/serp/req"


async def main(query: str, location: str = None, limit: int = 5):
    api_key = os.environ.get("BRIGHTDATA_API_KEY")
    if not api_key:
        print("Error: BRIGHTDATA_API_KEY not set")
        sys.exit(1)

    # Build Google Maps search URL
    search_query = query
    if location:
        search_query = f"{query} {location}"

    # Bright Data SERP API for Google Maps
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    payload = {
        "zone": SERP_ZONE,
        "url": f"https://www.google.com/maps/search/{quote_plus(search_query)}",
        "format": "json",
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(SERP_URL, headers=headers, json=payload)

        if response.status_code != 200:
            print(f"Error: {response.status_code} - {response.text[:500]}")
            sys.exit(1)

        data = response.json()

        # Parse results
        results = []
        for item in data.get("organic", [])[:limit]:
            results.append({
                "title": item.get("title"),
                "address": item.get("address"),
                "phone": item.get("phone"),
                "website": item.get("website"),
                "rating": item.get("rating"),
                "reviews_count": item.get("reviews"),
                "category": item.get("category"),
            })

        output = {
            "query": search_query,
            "results": results,
            "total_results": len(results),
            "cost_aud": 0.0015,
        }

        print(json.dumps(output, indent=2))
        return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Bright Data Google Maps SERP")
    parser.add_argument("--query", required=True, help="Search query")
    parser.add_argument("--location", help="Location (city/state)")
    parser.add_argument("--limit", type=int, default=5, help="Max results")
    args = parser.parse_args()

    asyncio.run(main(args.query, args.location, args.limit))
