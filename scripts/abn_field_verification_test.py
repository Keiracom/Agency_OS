#!/usr/bin/env python3
"""
ABN Field Verification Test
CEO Directive #009 Research Task 2

Quick test to verify actual ABN bulk extract field structure.
"""

import asyncio
import sys
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.integrations.abn_client import ABNClient


async def verify_abn_fields():
    """Test actual ABN field structure with a known ABN."""

    # Use a well-known Australian company ABN (Woolworths Group)
    # ABN: 88 000 014 675
    test_abn = "88 000 014 675"

    print("=" * 60)
    print("ABN FIELD VERIFICATION TEST")
    print("=" * 60)
    print(f"Testing ABN: {test_abn}")
    print()

    try:
        client = ABNClient()
        result = await client.search_by_abn(test_abn)

        if result and result.get("found"):
            print("✓ ABN lookup successful!")
            print()
            print("FIELD STRUCTURE:")
            print("-" * 40)

            # Check the specific fields we're interested in
            business_name = result.get("business_name")
            trading_name = result.get("trading_name")
            business_names = result.get("business_names")

            print(f"business_name: {business_name!r}")
            print(f"trading_name: {trading_name!r}")
            print(f"business_names: {business_names!r}")
            print()

            print("ALL AVAILABLE FIELDS:")
            print("-" * 40)
            for key, value in sorted(result.items()):
                print(f"{key}: {value!r}")

        else:
            print("✗ ABN lookup failed or returned no data")
            print(f"Result: {result}")

    except Exception as e:
        print(f"✗ Error during test: {e}")
        import traceback

        traceback.print_exc()

    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(verify_abn_fields())
