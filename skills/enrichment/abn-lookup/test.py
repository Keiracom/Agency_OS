#!/usr/bin/env python3
"""
ABN Lookup Skill - Test Cases
"""
import os
import asyncio
import sys
from typing import Dict

# Add src to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '../../..'))

from run import abn_lookup, abn_search_by_name


def validate_abn_result(result: Dict, expected_abn: str) -> bool:
    """Validate ABN lookup result structure and content."""
    if not result:
        print("❌ No result returned")
        return False
    
    required_fields = ['abn', 'entity_name', 'entity_type', 'status']
    for field in required_fields:
        if field not in result:
            print(f"❌ Missing required field: {field}")
            return False
    
    if result['abn'] != expected_abn:
        print(f"❌ ABN mismatch: expected {expected_abn}, got {result['abn']}")
        return False
    
    print(f"✅ ABN lookup successful for {expected_abn}")
    print(f"   Entity: {result['entity_name']}")
    print(f"   Type: {result.get('entity_type_name', result['entity_type'])}")
    print(f"   Status: {result['status']}")
    
    return True


async def test_telstra_abn():
    """Test case: Telstra ABN 33051775556"""
    print("Testing Telstra ABN lookup...")
    
    try:
        result = await abn_lookup("33051775556")
        return validate_abn_result(result, "33051775556")
    except Exception as e:
        print(f"❌ Error looking up Telstra ABN: {e}")
        return False


async def test_name_search():
    """Test business name search functionality."""
    print("Testing name search...")
    
    try:
        results = await abn_search_by_name("Telstra", state="VIC")
        
        if not results:
            print("❌ No results from name search")
            return False
        
        if len(results) == 0:
            print("❌ Empty results list")
            return False
        
        # Check if Telstra is in the results
        telstra_found = any(
            result.get('abn') == '33051775556' or 
            'telstra' in result.get('entity_name', '').lower()
            for result in results
        )
        
        if telstra_found:
            print(f"✅ Name search successful - found {len(results)} results including Telstra")
            return True
        else:
            print(f"⚠️  Name search returned {len(results)} results but Telstra not found")
            return False
            
    except Exception as e:
        print(f"❌ Error in name search: {e}")
        return False


async def test_invalid_abn():
    """Test invalid ABN handling."""
    print("Testing invalid ABN handling...")
    
    try:
        result = await abn_lookup("00000000000")
        
        if result is None:
            print("✅ Invalid ABN correctly returned None")
            return True
        else:
            print(f"⚠️  Invalid ABN returned unexpected result: {result}")
            return False
            
    except Exception as e:
        print(f"❌ Error testing invalid ABN: {e}")
        return False


async def main():
    """Run all ABN lookup tests."""
    print("🧪 ABN Lookup Skill Tests")
    print("=" * 40)
    
    # Check environment
    if not os.getenv("ABN_LOOKUP_GUID"):
        print("❌ ABN_LOOKUP_GUID environment variable not set")
        print("   Set it to run tests: export ABN_LOOKUP_GUID=your_guid_here")
        sys.exit(1)
    
    tests = [
        ("Telstra ABN Lookup", test_telstra_abn),
        ("Name Search", test_name_search),
        ("Invalid ABN Handling", test_invalid_abn),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n🔍 {test_name}")
        if await test_func():
            passed += 1
    
    print(f"\n📊 Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed!")
        sys.exit(0)
    else:
        print("💥 Some tests failed!")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())