"""
Test Leadmagic Mock Mode (CEO Directive #059)

Verifies that LEADMAGIC_MOCK=true returns realistic fake data
WITHOUT making any API calls.
"""

import asyncio
import os
import sys

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Set mock mode BEFORE importing
os.environ["LEADMAGIC_MOCK"] = "true"
# Set a dummy API key so client initializes
os.environ["LEADMAGIC_API_KEY"] = "mock-test-key-not-real"


async def test_mock_mode():
    """Test that mock mode returns data without API calls."""
    from src.integrations.leadmagic import LeadmagicClient

    print("=" * 60)
    print("LEADMAGIC MOCK MODE TEST")
    print("=" * 60)
    print(f"LEADMAGIC_MOCK={os.environ.get('LEADMAGIC_MOCK')}")
    print()

    async with LeadmagicClient() as client:
        # Test find_email
        print("Testing find_email()...")
        email_result = await client.find_email(
            first_name="Jane",
            last_name="Doe",
            domain="acme.com",
            company="Acme Corp",
        )
        print(f"  found: {email_result.found}")
        print(f"  email: {email_result.email}")
        print(f"  confidence: {email_result.confidence}")
        print(f"  status: {email_result.status}")
        print(f"  cost_aud: ${email_result.cost_aud:.2f}")
        print(f"  source: {email_result.source}")
        print()

        # Verify expectations
        assert email_result.found is True, "Expected found=True"
        assert email_result.email == "jane.doe@acme.com", (
            f"Expected jane.doe@acme.com, got {email_result.email}"
        )
        assert email_result.cost_aud == 0.0, f"Expected cost_aud=0.0, got {email_result.cost_aud}"
        assert email_result.source == "leadmagic-mock", (
            f"Expected source=leadmagic-mock, got {email_result.source}"
        )
        assert 85 <= email_result.confidence <= 98, (
            f"Expected confidence 85-98, got {email_result.confidence}"
        )
        print("  ✅ find_email() PASSED")
        print()

        # Test find_mobile
        print("Testing find_mobile()...")
        mobile_result = await client.find_mobile(
            linkedin_url="https://www.linkedin.com/in/john-smith-12345",
        )
        print(f"  found: {mobile_result.found}")
        print(f"  mobile_number: {mobile_result.mobile_number}")
        print(f"  mobile_confidence: {mobile_result.mobile_confidence}")
        print(f"  status: {mobile_result.status}")
        print(f"  full_name: {mobile_result.full_name}")
        print(f"  cost_aud: ${mobile_result.cost_aud:.2f}")
        print(f"  source: {mobile_result.source}")
        print()

        # Verify expectations
        assert mobile_result.found is True, "Expected found=True"
        assert mobile_result.mobile_number is not None, "Expected mobile_number"
        assert mobile_result.mobile_number.startswith("+61 4"), (
            f"Expected AU mobile starting +61 4, got {mobile_result.mobile_number}"
        )
        assert mobile_result.cost_aud == 0.0, f"Expected cost_aud=0.0, got {mobile_result.cost_aud}"
        assert mobile_result.source == "leadmagic-mock", (
            f"Expected source=leadmagic-mock, got {mobile_result.source}"
        )
        assert 80 <= mobile_result.mobile_confidence <= 95, (
            f"Expected confidence 80-95, got {mobile_result.mobile_confidence}"
        )
        print("  ✅ find_mobile() PASSED")
        print()

        # Verify no cost tracked (no real API calls)
        print(f"Session total cost: ${client.get_session_cost():.2f} AUD")
        assert client.get_session_cost() == 0.0, "Expected no cost in mock mode"
        print("  ✅ No costs incurred (mock mode)")
        print()

    print("=" * 60)
    print("ALL TESTS PASSED ✅")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_mock_mode())
