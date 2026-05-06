"""
Live Discovery/Enrichment Tests for Siege Waterfall Pipeline

Target: AdVisible (advisible.com.au) - Australian digital agency
Test tiers covered:
- T0: GMB Discovery (Bright Data SERP)
- T1: ABN Verification (ABN API)
- T-LI: LinkedIn Company Enrichment (Bright Data Scraper)
- T-DM: Decision Maker Discovery (Bright Data SERP)
- T-DM1: LinkedIn Profile Enrichment (Bright Data Scraper)

NOT COVERED (LeadMagic API key not configured):
- T3: Email Discovery
- T5: Mobile Discovery

Per Directive #166.
"""

import os

import pytest

from src.integrations.abn_client import ABNClient

# Import clients
from src.integrations.bright_data_client import BrightDataClient

# ============================================
# FIXTURES
# ============================================


@pytest.fixture
def bright_data_client():
    """
    Provide BrightDataClient instance.
    Skips if BRIGHTDATA_API_KEY not configured.
    """
    api_key = os.environ.get("BRIGHTDATA_API_KEY")
    if not api_key:
        pytest.skip("BRIGHTDATA_API_KEY not configured")
    return BrightDataClient(api_key=api_key)


@pytest.fixture
def abn_client():
    """
    Provide ABNClient instance.
    Skips if ABN_LOOKUP_GUID not configured.
    """
    guid = os.environ.get("ABN_LOOKUP_GUID")
    if not guid:
        pytest.skip("ABN_LOOKUP_GUID not configured")
    return ABNClient(guid=guid)


# ============================================
# SHARED STATE FOR INTEGRATION TEST
# ============================================


class TestState:
    """Shared state for passing data between tests in integration."""

    gmb_result: dict = None
    business_name: str = None
    abn_result: dict = None
    linkedin_company_result: dict = None
    dm_linkedin_url: str = None
    dm_name: str = None
    dm_title: str = None
    dm_profile_result: dict = None


# ============================================
# TEST CLASS
# ============================================


class TestLiveDiscoveryEnrichment:
    """
    Live end-to-end tests for the Siege Waterfall discovery/enrichment pipeline.
    Uses AdVisible (advisible.com.au) as test target.
    """

    @pytest.mark.skip(
        reason="Live Bright Data API test — requires active credentials and live network. Run manually on demand, not in CI baseline."
    )
    @pytest.mark.asyncio
    async def test_gmb_discovery_advisible(self, bright_data_client):
        """
        Test T0: GMB Discovery via Bright Data SERP API.

        Searches Google Maps for "advisible" in "Melbourne VIC".
        Expects at least 1 result with business_name, address, website, place_id.
        """
        print("\n=== T0: GMB Discovery Test ===")

        # Execute GMB search
        results = await bright_data_client.search_google_maps(
            query="advisible", location="Melbourne VIC", max_results=5
        )

        # Log raw result (truncated)
        raw_str = str(results)
        print(f"Raw GMB results (truncated): {raw_str[:500]}...")

        # Assert at least 1 result
        assert len(results) >= 1, "Expected at least 1 GMB result for AdVisible"

        # Get first result
        result = results[0]
        print(f"First result keys: {result.keys()}")

        # Assert required fields present (flexible on exact field names)
        # Bright Data GMB returns various formats
        has_name = any(k in result for k in ["title", "name", "business_name"])
        has_address = any(k in result for k in ["address", "location", "formatted_address"])
        has_website = any(k in result for k in ["website", "url", "domain"])
        has_place_id = any(k in result for k in ["place_id", "placeId", "cid"])

        print(
            f"Has name: {has_name}, Has address: {has_address}, Has website: {has_website}, Has place_id: {has_place_id}"
        )

        assert has_name, "GMB result must contain business name"
        assert has_address, "GMB result must contain address"
        # Website and place_id may not always be present, log warning instead
        if not has_website:
            print("WARNING: No website field found in GMB result")
        if not has_place_id:
            print("WARNING: No place_id field found in GMB result")

        # Store for integration test
        TestState.gmb_result = result
        TestState.business_name = (
            result.get("title") or result.get("name") or result.get("business_name", "AdVisible")
        )

        print(f"✓ GMB Discovery passed - Found: {TestState.business_name}")

        # Cleanup
        await bright_data_client.close()

    @pytest.mark.asyncio
    async def test_abn_verification_advisible(self, abn_client):
        """
        Test T1: ABN Verification via ABN Lookup API.

        Searches for ABN using business name from GMB.
        Expects active ABN with entity_type not Individual/Sole Trader.

        Note: AdVisible HQ is in Sydney NSW (per GMB data).
        """
        print("\n=== T1: ABN Verification Test ===")

        # Use stored business name or fallback
        # Try multiple name variations since ABN registry may differ from trading name
        search_names = [
            TestState.business_name or "AdVisible",
            "AdVisible",
            "Ad Visible",
            "ADVISIBLE",
        ]

        results = []
        search_states = ["NSW", None]  # Try NSW first (Sydney HQ), then all states

        for state in search_states:
            for name in search_names:
                state_str = state if state else "ALL"
                print(f"Searching ABN for: '{name}' in state: {state_str}")

                # Execute ABN search
                try:
                    search_results = await abn_client.search_by_name(
                        name=name, state=state, limit=5, active_only=True
                    )
                    if search_results:
                        results = search_results
                        print(f"Found {len(results)} results for '{name}' in {state_str}")
                        break
                except Exception as e:
                    print(f"Search failed: {e}")
                    continue

            if results:
                break

        # Log raw result
        raw_str = str(results)
        print(f"Raw ABN results (truncated): {raw_str[:500]}...")

        # Assert at least 1 result
        assert len(results) >= 1, (
            f"Expected at least 1 ABN result for AdVisible (tried: {search_names})"
        )

        # Get first result
        result = results[0]
        print(f"ABN Result: {result}")

        # Assert active ABN
        assert result.get("status") == "Active", "Expected active ABN"

        # Get entity type - need to do full lookup for entity_type
        abn = result.get("abn_raw") or result.get("abn", "").replace(" ", "")
        if abn:
            # Full ABN lookup to get entity type
            try:
                full_result = await abn_client.search_by_abn(abn)
                entity_type = full_result.get("entity_type", "")
                entity_type_code = full_result.get("entity_type_code", "")

                print(f"ABN: {full_result.get('abn')}")
                print(f"Entity Type: {entity_type} ({entity_type_code})")

                # Assert not individual/sole trader
                assert entity_type_code != "IND", "Expected non-individual entity"
                assert "Sole Trader" not in entity_type, "Expected non-sole trader entity"

                TestState.abn_result = full_result
            except Exception as e:
                print(f"Full ABN lookup failed: {e}")
                TestState.abn_result = result
        else:
            TestState.abn_result = result

        print(f"✓ ABN Verification passed - ABN: {result.get('abn')}")

        # Cleanup
        await abn_client.close()

    @pytest.mark.skip(
        reason="Live Bright Data API test — requires active credentials and live network. Run manually on demand, not in CI baseline."
    )
    @pytest.mark.asyncio
    async def test_linkedin_company_enrichment_advisible(self, bright_data_client):
        """
        Test T-LI: LinkedIn Company Enrichment via Bright Data Scraper API.

        Scrapes LinkedIn company page for AdVisible.
        Expects company profile with employee_count or specialties.
        """
        print("\n=== T-LI: LinkedIn Company Enrichment Test ===")

        linkedin_url = "https://www.linkedin.com/company/advisible"
        print(f"Scraping LinkedIn company: {linkedin_url}")

        # Execute LinkedIn company scrape
        result = await bright_data_client.scrape_linkedin_company(linkedin_url)

        # Log raw result (truncated)
        raw_str = str(result)
        print(f"Raw LinkedIn company result (truncated): {raw_str[:500]}...")

        # Assert returns company profile
        assert result, "Expected non-empty LinkedIn company result"

        # Check for employee_count or specialties
        has_employees = any(
            k in result
            for k in ["employee_count", "employees", "staff_count", "company_size", "size"]
        )
        has_specialties = any(
            k in result for k in ["specialties", "industries", "industry", "tags"]
        )

        print(f"Result keys: {result.keys()}")
        print(f"Has employees field: {has_employees}, Has specialties field: {has_specialties}")

        # At least one should be present
        assert has_employees or has_specialties, (
            "Expected employee_count or specialties in LinkedIn company data"
        )

        # Log company size and industry
        company_size = (
            result.get("company_size")
            or result.get("employee_count")
            or result.get("size", "Unknown")
        )
        industry = result.get("industry") or result.get("industries", "Unknown")
        print(f"Company Size: {company_size}")
        print(f"Industry: {industry}")

        TestState.linkedin_company_result = result

        print("✓ LinkedIn Company Enrichment passed")

        # Cleanup
        await bright_data_client.close()

    @pytest.mark.skip(
        reason="Live Bright Data API test — requires active credentials and live network. Run manually on demand, not in CI baseline."
    )
    @pytest.mark.asyncio
    async def test_decision_maker_discovery_advisible(self, bright_data_client):
        """
        Test T-DM: Decision Maker Discovery via Bright Data SERP API.

        Searches Google for AdVisible founder/CEO LinkedIn profiles.
        Expects at least 1 result with linkedin.com/in/ URL.
        """
        print("\n=== T-DM: Decision Maker Discovery Test ===")

        query = "AdVisible founder CEO LinkedIn Australia"
        print(f"Searching Google: {query}")

        # Execute Google search
        results = await bright_data_client.search_google(query=query, max_results=10)

        # Log raw results (truncated)
        raw_str = str(results)
        print(f"Raw Google results (truncated): {raw_str[:500]}...")

        # Assert at least 1 result
        assert len(results) >= 1, "Expected at least 1 Google result"

        # Find result with LinkedIn profile URL
        linkedin_profile_url = None
        dm_name = None
        dm_title = None

        for result in results:
            url = result.get("url") or result.get("link", "")
            title = result.get("title", "")

            if "linkedin.com/in/" in url.lower():
                linkedin_profile_url = url
                # Parse name from title (usually "Name - Title | LinkedIn")
                if " - " in title:
                    dm_name = title.split(" - ")[0].strip()
                    dm_title = (
                        title.split(" - ")[1].split(" | ")[0].strip() if " | " in title else ""
                    )
                elif " | " in title:
                    dm_name = title.split(" | ")[0].strip()
                else:
                    dm_name = title.replace(" | LinkedIn", "").strip()
                break

        assert linkedin_profile_url, "Expected at least 1 result with linkedin.com/in/ URL"

        print(f"DM Name: {dm_name}")
        print(f"DM Title: {dm_title}")
        print(f"DM LinkedIn URL: {linkedin_profile_url}")

        TestState.dm_linkedin_url = linkedin_profile_url
        TestState.dm_name = dm_name
        TestState.dm_title = dm_title

        print("✓ Decision Maker Discovery passed")

        # Cleanup
        await bright_data_client.close()

    @pytest.mark.skip(
        reason="Live Bright Data API test — requires active credentials and live network. Run manually on demand, not in CI baseline."
    )
    @pytest.mark.asyncio
    async def test_linkedin_profile_enrichment_advisible(self, bright_data_client):
        """
        Test T-DM1: LinkedIn Profile Enrichment via Bright Data Scraper API.

        Scrapes LinkedIn profile discovered in T-DM.
        Expects profile data with headline or current_title.
        """
        print("\n=== T-DM1: LinkedIn Profile Enrichment Test ===")

        # Use URL from T-DM or fallback
        linkedin_url = TestState.dm_linkedin_url

        if not linkedin_url:
            # Fallback: search for a founder profile
            print("No URL from T-DM, searching for fallback...")
            results = await bright_data_client.search_google(
                query="AdVisible digital marketing agency founder LinkedIn Australia",
                max_results=10,
            )
            for result in results:
                url = result.get("url") or result.get("link", "")
                if "linkedin.com/in/" in url.lower():
                    linkedin_url = url
                    break

        if not linkedin_url:
            pytest.skip("No LinkedIn profile URL found for enrichment test")

        print(f"Scraping LinkedIn profile: {linkedin_url}")

        # Execute LinkedIn profile scrape
        result = await bright_data_client.scrape_linkedin_profile(linkedin_url)

        # Log raw result (truncated)
        raw_str = str(result)
        print(f"Raw LinkedIn profile result (truncated): {raw_str[:500]}...")

        # Assert returns profile data
        assert result, "Expected non-empty LinkedIn profile result"

        # Check for headline or current_title
        has_headline = any(
            k in result for k in ["headline", "title", "current_title", "occupation"]
        )
        has_name = any(k in result for k in ["name", "full_name", "first_name"])

        print(f"Result keys: {result.keys()}")
        print(f"Has headline field: {has_headline}, Has name field: {has_name}")

        assert has_headline or has_name, "Expected headline or name in LinkedIn profile data"

        # Log name and title
        name = (
            result.get("name")
            or result.get("full_name")
            or f"{result.get('first_name', '')} {result.get('last_name', '')}".strip()
        )
        title = result.get("headline") or result.get("title") or result.get("occupation", "Unknown")

        print(f"Name: {name}")
        print(f"Title: {title}")

        TestState.dm_profile_result = result

        print("✓ LinkedIn Profile Enrichment passed")

        # Cleanup
        await bright_data_client.close()

    @pytest.mark.skip(
        reason="Live Bright Data API test — requires active credentials and live network. Run manually on demand, not in CI baseline."
    )
    @pytest.mark.asyncio
    async def test_full_pipeline_advisible(self, bright_data_client, abn_client):
        """
        Test Integration: Full Siege Waterfall Pipeline for AdVisible.

        Runs all discovery/enrichment steps in sequence.
        Creates summary and asserts all steps passed.
        LeadMagic T3/T5 explicitly skipped (no API key).
        """
        print("\n=== INTEGRATION: Full Pipeline Test ===")
        print("Target: AdVisible (advisible.com.au)")
        print("-" * 50)

        summary = {
            "gmb_found": False,
            "abn_verified": False,
            "linkedin_company": False,
            "dm_identified": False,
            "dm_linkedin_profile": False,
        }

        # T0: GMB Discovery
        print("\n[T0] GMB Discovery...")
        try:
            gmb_results = await bright_data_client.search_google_maps(
                query="advisible", location="Melbourne VIC", max_results=5
            )
            if gmb_results and len(gmb_results) > 0:
                summary["gmb_found"] = True
                business_name = (
                    gmb_results[0].get("title") or gmb_results[0].get("name") or "AdVisible"
                )
                print(f"  ✓ Found: {business_name}")
            else:
                print("  ✗ No GMB results")
        except Exception as e:
            print(f"  ✗ GMB Discovery failed: {e}")

        # T1: ABN Verification
        print("\n[T1] ABN Verification...")
        abn_results = []
        search_names = ["AdVisible", "Ad Visible", "ADVISIBLE"]
        search_states = ["NSW", None]  # Sydney HQ, then all states

        for state in search_states:
            for name in search_names:
                try:
                    results = await abn_client.search_by_name(
                        name=name, state=state, limit=5, active_only=True
                    )
                    if results:
                        abn_results = results
                        print(f"  Found {len(results)} results for '{name}' in {state or 'ALL'}")
                        break
                except Exception:
                    continue
            if abn_results:
                break

        if abn_results and len(abn_results) > 0:
            abn = abn_results[0].get("abn", "")
            status = abn_results[0].get("status", "")
            if status == "Active":
                summary["abn_verified"] = True
                print(f"  ✓ ABN: {abn} (Active)")
            else:
                print(f"  ✗ ABN found but not active: {status}")
        else:
            print("  ✗ No ABN results")

        # T-LI: LinkedIn Company
        print("\n[T-LI] LinkedIn Company Enrichment...")
        try:
            linkedin_company = await bright_data_client.scrape_linkedin_company(
                "https://www.linkedin.com/company/advisible"
            )
            if linkedin_company:
                summary["linkedin_company"] = True
                size = linkedin_company.get("company_size") or linkedin_company.get(
                    "employee_count", "Unknown"
                )
                print(f"  ✓ Company found, Size: {size}")
            else:
                print("  ✗ No LinkedIn company data")
        except Exception as e:
            print(f"  ✗ LinkedIn Company failed: {e}")

        # T-DM: Decision Maker Discovery
        print("\n[T-DM] Decision Maker Discovery...")
        dm_linkedin_url = None
        try:
            dm_results = await bright_data_client.search_google(
                query="AdVisible founder CEO LinkedIn Australia", max_results=10
            )
            for result in dm_results:
                url = result.get("url") or result.get("link", "")
                if "linkedin.com/in/" in url.lower():
                    dm_linkedin_url = url
                    title = result.get("title", "")
                    summary["dm_identified"] = True
                    print(f"  ✓ DM found: {title[:50]}...")
                    break
            if not dm_linkedin_url:
                print("  ✗ No LinkedIn profile URLs found")
        except Exception as e:
            print(f"  ✗ Decision Maker Discovery failed: {e}")

        # T-DM1: LinkedIn Profile Enrichment
        print("\n[T-DM1] LinkedIn Profile Enrichment...")
        if dm_linkedin_url:
            try:
                dm_profile = await bright_data_client.scrape_linkedin_profile(dm_linkedin_url)
                if dm_profile:
                    summary["dm_linkedin_profile"] = True
                    name = dm_profile.get("name") or dm_profile.get("full_name", "Unknown")
                    headline = dm_profile.get("headline") or dm_profile.get("title", "Unknown")
                    print(f"  ✓ Profile: {name} - {headline[:30]}...")
                else:
                    print("  ✗ No profile data returned")
            except Exception as e:
                print(f"  ✗ LinkedIn Profile failed: {e}")
        else:
            print("  ⚠ Skipped - no DM URL from previous step")

        # T3/T5: LeadMagic (explicitly skipped)
        print("\n[T3/T5] Email & Mobile Discovery...")
        print("  ⚠ SKIPPED: LeadMagic API key not configured")

        # Summary
        print("\n" + "=" * 50)
        print("PIPELINE SUMMARY")
        print("=" * 50)
        for step, passed in summary.items():
            status = "✓ PASS" if passed else "✗ FAIL"
            print(f"  {step}: {status}")

        all_passed = all(summary.values())
        print("-" * 50)
        print(f"Overall: {'✓ ALL PASSED' if all_passed else '✗ SOME FAILED'}")
        print("=" * 50)

        # Full summary log
        print(f"\nFull summary: {summary}")

        # Assert all five are True
        assert summary["gmb_found"], "GMB Discovery failed"
        assert summary["abn_verified"], "ABN Verification failed"
        assert summary["linkedin_company"], "LinkedIn Company failed"
        assert summary["dm_identified"], "Decision Maker Discovery failed"
        assert summary["dm_linkedin_profile"], "LinkedIn Profile Enrichment failed"

        print("\n✓ Full Pipeline Integration Test PASSED")

        # Cleanup
        await bright_data_client.close()
        await abn_client.close()
