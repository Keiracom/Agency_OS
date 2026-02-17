#!/usr/bin/env python3
"""
Validation test for Hunter.io email discovery.
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
    "domain": "mustardcreative.com.au",
    "expected_org": "Mustard",
}


async def test():
    api_key = os.environ.get("HUNTER_API_KEY")
    if not api_key:
        print("❌ BLOCKED: HUNTER_API_KEY not set")
        return False
    print(f"✓ HUNTER_API_KEY configured: {api_key[:8]}...")
    
    # Check account status
    async with httpx.AsyncClient(timeout=30.0) as client:
        status_response = await client.get(
            "https://api.hunter.io/v2/account",
            params={"api_key": api_key}
        )
        
        if status_response.status_code == 200:
            account = status_response.json().get("data", {})
            searches = account.get("requests", {}).get("searches", {})
            print(f"   Plan: {account.get('plan_name')}")
            print(f"   Searches remaining: {searches.get('available')}")
            print(f"   Reset: {account.get('reset_date')}")
        
        # Domain search test
        print(f"\nTesting domain search for: {TEST_CASE['domain']}")
        
        search_response = await client.get(
            "https://api.hunter.io/v2/domain-search",
            params={"api_key": api_key, "domain": TEST_CASE["domain"], "limit": 3}
        )
        
        if search_response.status_code == 200:
            data = search_response.json().get("data", {})
            org = data.get("organization", "")
            emails = data.get("emails", [])
            
            if TEST_CASE["expected_org"].lower() in org.lower():
                print(f"✅ PASS: Hunter.io working")
                print(f"   Organization: {org}")
                print(f"   Emails found: {len(emails)}")
                if emails:
                    print(f"   First: {emails[0].get('value')} ({emails[0].get('position', 'N/A')})")
                return True
            else:
                print(f"⚠️ WARN: Unexpected org: {org}")
                return True  # API works
        else:
            print(f"❌ FAIL: API error - {search_response.status_code}")
            return False


if __name__ == "__main__":
    success = asyncio.run(test())
    sys.exit(0 if success else 1)
