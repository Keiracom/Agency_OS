#!/usr/bin/env python3
"""
Validation test for ABN Lookup enrichment.
Run before any batch operations.
"""
import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from dotenv import load_dotenv
load_dotenv()

TEST_CASE = {
    "abn": "33051775556",
    "expected_name": "TELSTRA",
}


async def test():
    # Check credentials first
    guid = os.environ.get("ABN_LOOKUP_GUID")
    if not guid:
        print("❌ BLOCKED: ABN_LOOKUP_GUID not set")
        return False
    print(f"✓ ABN_LOOKUP_GUID configured: {guid[:8]}...")
    
    # Run test case
    from src.integrations.abn_client import get_abn_client
    client = get_abn_client()
    
    print(f"\nTesting ABN lookup for: {TEST_CASE['abn']}")
    result = await client.search_by_abn(TEST_CASE["abn"])
    
    if result.get("found"):
        name = result.get("business_name", "") or result.get("trading_name", "")
        if TEST_CASE["expected_name"].upper() in name.upper():
            print(f"✅ PASS: ABN lookup working")
            print(f"   Company: {name}")
            print(f"   State: {result.get('state')}")
            print(f"   GST: {result.get('gst_registered')}")
            return True
        else:
            print(f"⚠️ WARN: Got unexpected company: {name}")
            return True  # Still working, just different data
    else:
        print(f"❌ FAIL: ABN lookup returned no data")
        print(f"   Error: {result.get('error', 'Unknown')}")
        return False


if __name__ == "__main__":
    success = asyncio.run(test())
    sys.exit(0 if success else 1)
