#!/usr/bin/env python3
"""
Bright Data LinkedIn Skill - Test Cases
"""
import os
import asyncio
import sys
from typing import Dict

# Add src to path for imports  
sys.path.append(os.path.join(os.path.dirname(__file__), '../../..'))

from run import linkedin_profile_lookup


def validate_linkedin_result(result: Dict, expected_url: str) -> bool:
    """Validate LinkedIn profile lookup result structure and content."""
    if not result:
        print("❌ No result returned")
        return False
    
    if result.get("status") == "not_found":
        print("❌ Profile not found")
        return False
    
    required_fields = ['profile_url', 'status', 'name']
    for field in required_fields:
        if field not in result:
            print(f"❌ Missing required field: {field}")
            return False
    
    if result['profile_url'] != expected_url:
        print(f"❌ URL mismatch: expected {expected_url}, got {result['profile_url']}")
        return False
    
    print(f"✅ LinkedIn lookup successful for {expected_url}")
    print(f"   Name: {result['name']}")
    print(f"   Headline: {result.get('headline', 'N/A')}")
    print(f"   Location: {result.get('location', 'N/A')}")
    print(f"   Industry: {result.get('industry', 'N/A')}")
    
    # Check for company-specific fields
    if result.get('company_size'):
        print(f"   Company Size: {result['company_size']}")
    if result.get('website'):
        print(f"   Website: {result['website']}")
    
    return True


async def test_mustard_creative():
    """Test case: Mustard Creative LinkedIn URL"""
    mustard_url = "https://www.linkedin.com/company/mustard-creative/"
    print(f"Testing Mustard Creative LinkedIn lookup: {mustard_url}")
    
    try:
        result = await linkedin_profile_lookup(mustard_url)
        return validate_linkedin_result(result, mustard_url)
    except Exception as e:
        print(f"❌ Error looking up Mustard Creative LinkedIn: {e}")
        return False


async def test_invalid_url():
    """Test invalid LinkedIn URL handling."""
    invalid_url = "https://www.linkedin.com/company/this-does-not-exist-test-123456/"
    print(f"Testing invalid URL handling: {invalid_url}")
    
    try:
        result = await linkedin_profile_lookup(invalid_url)
        
        if result and result.get("status") == "not_found":
            print("✅ Invalid URL correctly handled")
            return True
        elif result is None:
            print("✅ Invalid URL correctly returned None")
            return True
        else:
            print(f"⚠️  Invalid URL returned unexpected result: {result}")
            return False
            
    except Exception as e:
        print(f"❌ Error testing invalid URL: {e}")
        return False


async def test_api_key_validation():
    """Test API key validation."""
    print("Testing API key validation...")
    
    # Temporarily remove API key
    original_key = os.getenv("BRIGHTDATA_API_KEY")
    if "BRIGHTDATA_API_KEY" in os.environ:
        del os.environ["BRIGHTDATA_API_KEY"]
    
    try:
        result = await linkedin_profile_lookup("https://www.linkedin.com/company/test/")
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
    """Run all LinkedIn lookup tests."""
    print("🧪 Bright Data LinkedIn Skill Tests")
    print("=" * 50)
    
    # Check environment
    if not os.getenv("BRIGHTDATA_API_KEY"):
        print("❌ BRIGHTDATA_API_KEY environment variable not set")
        print("   Set it to run tests: export BRIGHTDATA_API_KEY=your_api_key_here")
        sys.exit(1)
    
    tests = [
        ("Mustard Creative LinkedIn", test_mustard_creative),
        ("Invalid URL Handling", test_invalid_url),
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
        sys.exit(0)
    else:
        print("💥 Some tests failed!")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())