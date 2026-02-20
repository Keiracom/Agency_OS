#!/usr/bin/env python3
"""
Hunter.io Email Discovery & Verification Skill
Usage: python run.py --domain "example.com" [--first "John" --last "Smith"]
       python run.py --verify "email@example.com"
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

BASE_URL = "https://api.hunter.io/v2"


async def domain_search(domain: str, first: str = None, last: str = None, limit: int = 5):
    api_key = os.environ.get("HUNTER_API_KEY")
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        if first and last:
            # Email finder
            params = {
                "api_key": api_key,
                "domain": domain,
                "first_name": first,
                "last_name": last,
            }
            response = await client.get(f"{BASE_URL}/email-finder", params=params)
        else:
            # Domain search
            params = {
                "api_key": api_key,
                "domain": domain,
                "limit": limit,
            }
            response = await client.get(f"{BASE_URL}/domain-search", params=params)
        
        if response.status_code != 200:
            print(f"Error: {response.status_code} - {response.text}")
            sys.exit(1)
        
        data = response.json().get("data", {})
        
        output = {
            "domain": domain,
            "organization": data.get("organization"),
            "emails": [
                {
                    "value": e.get("value"),
                    "first_name": e.get("first_name"),
                    "last_name": e.get("last_name"),
                    "position": e.get("position"),
                    "seniority": e.get("seniority"),
                    "confidence": e.get("confidence"),
                }
                for e in data.get("emails", [])
            ],
            "total_found": len(data.get("emails", [])),
            "cost_aud": 0.15,
        }
        
        print(json.dumps(output, indent=2))
        return output


async def verify_email(email: str):
    api_key = os.environ.get("HUNTER_API_KEY")
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        params = {"api_key": api_key, "email": email}
        response = await client.get(f"{BASE_URL}/email-verifier", params=params)
        
        if response.status_code != 200:
            print(f"Error: {response.status_code} - {response.text}")
            sys.exit(1)
        
        data = response.json().get("data", {})
        
        output = {
            "email": email,
            "status": data.get("status"),
            "score": data.get("score"),
            "deliverable": data.get("status") == "valid",
            "cost_aud": 0.08,
        }
        
        print(json.dumps(output, indent=2))
        return output


async def main(domain: str = None, verify: str = None, first: str = None, last: str = None, limit: int = 5):
    api_key = os.environ.get("HUNTER_API_KEY")
    if not api_key:
        print("Error: HUNTER_API_KEY not set")
        sys.exit(1)
    
    if verify:
        return await verify_email(verify)
    elif domain:
        return await domain_search(domain, first, last, limit)
    else:
        print("Error: Must provide --domain or --verify")
        sys.exit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Hunter.io Email Discovery & Verification")
    parser.add_argument("--domain", help="Domain to search")
    parser.add_argument("--verify", help="Email to verify")
    parser.add_argument("--first", help="First name (with domain)")
    parser.add_argument("--last", help="Last name (with domain)")
    parser.add_argument("--limit", type=int, default=5, help="Max results")
    args = parser.parse_args()
    
    if not args.domain and not args.verify:
        parser.error("Must provide either --domain or --verify")
    
    asyncio.run(main(args.domain, args.verify, args.first, args.last, args.limit))
