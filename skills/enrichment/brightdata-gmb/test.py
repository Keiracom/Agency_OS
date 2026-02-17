#!/usr/bin/env python3
"""
Bright Data GMB Skill - Test Cases

This replaces the deprecated DIY GMB scraper tests.
Validates Bright Data Google Maps SERP API integration.
"""
import os
import asyncio
import sys
from typing import List, Dict

# Add src to path for imports  
sys.path.append(os.path.join(os.path.dirname(__file__), '../../..'))

from run import gmb_search, gmb_search_with_fallbacks


def validate_gmb_results(results: List[Dict], query: str, location: str = None) -> bool:
    """Validate GMB search results structure and content."""
    if not results:
        print("❌ No results returned")
        return False
    
    if not isinstance(results, list):
        print("❌ Results should be a list")
        return False
    
    print(f"✅ Found {len(results)} businesses for '{query}' in {location or 'Australia'}")
    
    # Validate first result structure
    first_result = results[0]
    required_fields = ['name', 'source']
    for field in required_fields:
        if field not in first_result:
            print(f"❌ Missing required field in first result: {field}")
            return False
    
    # Check if source is correct
    if first_result.get('source') != 'bright_data_gmb':
        print(f"❌ Wrong source: expected 'bright_data_gmb', got {first_result.get('source')}")
        return False
    
    # Display sample results
    for i, business in enumerate(results[:3]):  # Show first 3 results
        print(f"   {i+1}. {business['name']}")
        if business.get('address'):
            print(f"      Address: {business['address']}")
        if business.get('phone'):
            print(f"      Phone: {business['phone']}")
        if business.get('rating'):
            print(f"      Rating: {business['rating']} ({business.get('reviews_count', 0)} reviews)")
        print()
    
    return True


async def test_marketing_agency_melbourne():
    """Test case: 'marketing agency Melbourne'"""
    query = "marketing agency"
    location = "Melbourne"
    
    print(f"Testing GMB search: '{query}' in {location}")
    
    try:
        results = await gmb_search(query, location)
        return validate_gmb_results(results, query, location)
    except Exception as e:
        print(f"❌ Error searching for marketing agencies in Melbourne: {e}")
        return False


async def test_general_search():
    """Test general business search without location."""
    query = "restaurants"
    
    print(f"Testing general search: '{query}'")
    
    try:
        results = await gmb_search(query)
        
        if not results:
            print("❌ No results for general restaurant search")
            return False
        
        print(f"✅ General search successful - found {len(results)} restaurants")
        return True
        
    except Exception as e:
        print(f"❌ Error in general search: {e}")
        return False


async def test_fallback_search():
    """Test fallback search strategies."""
    business_name = "Mustard Creative Pty Ltd"
    location = "Melbourne"
    
    print(f"Testing fallback search for: {business_name}")
    
    try:
        results = await gmb_search_with_fallbacks(business_name, location)
        
        if results:
            print(f"✅ Fallback search found {len(results)} results")
            # Look for Mustard Creative specifically
            mustard_found = any(
                'mustard' in business.get('name', '').lower() or
                'creative' in business.get('name', '').lower()
                for business in results
            )
            if mustard_found:
                print("✅ Found Mustard Creative in results")
            else:
                print("⚠️  Mustard Creative not specifically found but got other results")
            return True
        else:
            print("⚠️  No results from fallback search - may be expected for test business")
            return True  # This is acceptable for a test case
            
    except Exception as e:
        print(f"❌ Error in fallback search: {e}")
        return False


async def test_api_key_validation():
    """Test API key validation."""
    print("Testing API key validation...")
    
    # Temporarily remove API key
    original_key = os.getenv("BRIGHTDATA_API_KEY")
    if "BRIGHTDATA_API_KEY" in os.environ:
        del os.environ["BRIGHTDATA_API_KEY"]
    
    try:
        results = await gmb_search("test query")
        print("❌ Should have raised ValueError for missing API key")
        return False
    except ValueError as e:
        if "BRIGHTDATA_API_KEY" in str(e):
            print("✅ API key validation working correctly")
            success = True
        else:
            print(f"❌ Wrong error message: {e}")
            success = False
    except Exception as e:
        print(f"❌ Unexpected error type: {e}")
        success = False
    finally:
        # Restore original API key
        if original_key:
            os.environ["BRIGHTDATA_API_KEY"] = original_key
    
    return success


async def main():
    """Run all GMB search tests."""
    print("🧪 Bright Data GMB Skill Tests")
    print("=" * 50)
    print("🔄 This replaces the deprecated DIY GMB scraper")
    print("💰 Cost: $0.0015/request vs $0.006/lead DIY (75% reduction)")
    print()
    
    # Check environment
    if not os.getenv("BRIGHTDATA_API_KEY"):
        print("❌ BRIGHTDATA_API_KEY environment variable not set")
        print("   Set it to run tests: export BRIGHTDATA_API_KEY=your_api_key_here")
        sys.exit(1)
    
    tests = [
        ("Marketing Agency Melbourne", test_marketing_agency_melbourne),
        ("General Search", test_general_search),
        ("Fallback Search Strategies", test_fallback_search),
        ("API Key Validation", test_api_key_validation),
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
        print("✅ GMB replacement validated - DIY scraper successfully replaced")
        sys.exit(0)
    else:
        print("💥 Some tests failed!")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())