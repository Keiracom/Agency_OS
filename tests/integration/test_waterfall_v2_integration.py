"""
Integration tests for Waterfall v2

Uses real Bright Data API with Mustard Creative as test fixture.
Run with: pytest -m integration (costs money!)

Fixture data from Directive #020d testing (2026-02-16).
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../src'))

# Test fixture: confirmed data from Directive #020d
MUSTARD_CREATIVE = {
    "linkedin_url": "https://www.linkedin.com/company/mustard-creative-media",
    "business_name": "Mustard Creative Media",
    "location": "Richmond, Victoria",
    "expected": {
        "name": "Mustard | A Creative Agency",
        "country_code": "AU",
        "followers": 10589,
        "employees_in_linkedin": 29,
        "company_size": "11-50 employees",
        "organization_type": "Privately Held",
        "industries": "Advertising Services",
        "website": "https://www.mustardcreative.com.au/",
        "founded": 2002,
        "company_id": "205141",
        "headquarters": "Richmond, Victoria",
        "has_employees": True,
        "has_updates": True,
        "has_similar": True
    }
}

# API key for testing (same as used in Directive #020d)
TEST_API_KEY = os.environ.get(
    "BRIGHT_DATA_API_KEY",
    "2bab0747-ede2-4437-9b6f-6a77e8f0ca3e"
)


@pytest.fixture
def bright_data_client():
    """Create a real BrightDataClient for integration tests"""
    from integrations.bright_data_client import BrightDataClient
    return BrightDataClient(api_key=TEST_API_KEY)


@pytest.mark.integration
class TestBrightDataClientIntegration:
    """
    Integration tests using real Bright Data API.
    These tests cost money - run sparingly!
    
    Run with: pytest -m integration tests/integration/
    """

    def test_scrape_linkedin_company_mustard_creative(self, bright_data_client):
        """
        Test LinkedIn Company scraper with Mustard Creative.
        
        This is the same test that was run in Directive #020d.
        Expected output is known and verified.
        
        Cost: $0.0015 AUD
        """
        result = bright_data_client.scrape_linkedin_company(
            MUSTARD_CREATIVE["linkedin_url"]
        )

        # Core fields
        assert result["name"] == MUSTARD_CREATIVE["expected"]["name"]
        assert result["country_code"] == MUSTARD_CREATIVE["expected"]["country_code"]
        assert result["industries"] == MUSTARD_CREATIVE["expected"]["industries"]
        assert result["founded"] == MUSTARD_CREATIVE["expected"]["founded"]
        assert result["headquarters"] == MUSTARD_CREATIVE["expected"]["headquarters"]

        # Verify rich data is present
        assert "employees" in result
        assert len(result["employees"]) > 0, "Should have employee data"

        assert "updates" in result
        assert len(result["updates"]) > 0, "Should have recent posts"

        assert "similar" in result
        assert len(result["similar"]) > 0, "Should have similar companies"

        # Verify cost tracking
        assert bright_data_client.costs.scraper_records == 1
        assert bright_data_client.get_total_cost() == pytest.approx(0.0015, rel=0.01)

    def test_search_google_linkedin_discovery(self, bright_data_client):
        """
        Test SERP Google search to find LinkedIn URL.
        
        This is Tier 1.5b in the waterfall.
        
        Cost: $0.0015 AUD
        """
        query = f'site:linkedin.com/company "{MUSTARD_CREATIVE["business_name"]}"'
        results = bright_data_client.search_google(query)

        # Should find the LinkedIn URL in organic results
        found_url = False
        for result in results.get("organic", []):
            if "mustard-creative-media" in result.get("url", ""):
                found_url = True
                break

        assert found_url, "Should find Mustard Creative LinkedIn URL via SERP"

        # Verify cost tracking
        assert bright_data_client.costs.serp_requests == 1

    def test_full_tier_1_5b_to_tier_2_flow(self, bright_data_client):
        """
        Test complete enrichment flow:
        1. SERP search to find LinkedIn URL
        2. LinkedIn Company scrape
        
        This tests Tier 1.5b → Tier 2 transition.
        
        Cost: $0.003 AUD (2 requests)
        """
        # Tier 1.5b: Find LinkedIn URL
        query = f'site:linkedin.com/company "{MUSTARD_CREATIVE["business_name"]}"'
        serp_results = bright_data_client.search_google(query)

        # Extract LinkedIn URL from results
        linkedin_url = None
        for result in serp_results.get("organic", []):
            url = result.get("url", "")
            if "linkedin.com/company" in url:
                linkedin_url = url
                break

        assert linkedin_url is not None, "Should find LinkedIn URL"

        # Tier 2: Scrape LinkedIn Company
        company_data = bright_data_client.scrape_linkedin_company(linkedin_url)

        # Verify we got company data
        assert "name" in company_data
        assert "employees" in company_data

        # Verify total cost
        assert bright_data_client.costs.serp_requests == 1
        assert bright_data_client.costs.scraper_records == 1
        assert bright_data_client.get_total_cost() == pytest.approx(0.003, rel=0.01)


@pytest.mark.integration
class TestWaterfallIntegration:
    """
    Full waterfall integration tests.
    
    These are expensive - use sparingly for validation.
    """

    def test_employee_extraction_for_decision_makers(self, bright_data_client):
        """
        Test that LinkedIn Company scrape returns employee data
        suitable for decision maker identification.
        
        This data feeds into Tier 2.5 (LinkedIn Profile enrichment).
        """
        result = bright_data_client.scrape_linkedin_company(
            MUSTARD_CREATIVE["linkedin_url"]
        )

        employees = result.get("employees", [])
        assert len(employees) > 0

        # Each employee should have required fields for Tier 2.5
        for emp in employees:
            assert "title" in emp, "Employee should have title"
            assert "link" in emp, "Employee should have LinkedIn URL"

    def test_hiring_signal_detection(self, bright_data_client):
        """
        Test that LinkedIn Company scrape returns posts
        that can be analyzed for hiring signals.
        
        "#hiring" in posts indicates active growth (Timing score).
        """
        result = bright_data_client.scrape_linkedin_company(
            MUSTARD_CREATIVE["linkedin_url"]
        )

        updates = result.get("updates", [])
        assert len(updates) > 0

        # Check if any posts contain hiring signals
        hiring_signals = []
        for update in updates:
            text = update.get("text", "").lower()
            if "#hiring" in text or "we're hiring" in text or "join us" in text:
                hiring_signals.append(update)

        # Note: Mustard Creative may or may not have hiring posts
        # This test validates the data structure supports detection


# Mark all tests in this module as integration tests
pytestmark = pytest.mark.integration
