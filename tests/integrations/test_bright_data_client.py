"""
Unit tests for BrightDataClient

Tests the unified Bright Data client covering SERP API and Scrapers API.
"""
import os
import sys
from unittest.mock import AsyncMock, Mock, patch

import pytest

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../src'))


class TestDatasetIDs:
    """Verify dataset IDs match the SSOT in bright-data-inventory.md"""

    def test_linkedin_company_id(self):
        from integrations.bright_data_client import DATASET_IDS
        assert DATASET_IDS["linkedin_company"] == "gd_l1vikfnt1wgvvqz95w"

    def test_linkedin_people_id(self):
        from integrations.bright_data_client import DATASET_IDS
        assert DATASET_IDS["linkedin_people"] == "gd_l1viktl72bvl7bjuj0"

    def test_linkedin_jobs_id(self):
        from integrations.bright_data_client import DATASET_IDS
        assert DATASET_IDS["linkedin_jobs"] == "gd_lpfll7v5hcqtkxl6l"


class TestCosts:
    """Verify cost constants match the SSOT"""

    def test_serp_cost(self):
        from integrations.bright_data_client import COSTS_AUD
        assert COSTS_AUD["serp_request"] == 0.0015

    def test_scraper_cost(self):
        from integrations.bright_data_client import COSTS_AUD
        assert COSTS_AUD["scraper_record"] == 0.0015


class TestBrightDataClientInit:
    """Test client initialization"""

    def test_init_with_api_key(self):
        from integrations.bright_data_client import BrightDataClient
        client = BrightDataClient(api_key="test-key-123")
        assert client.api_key == "test-key-123"

    def test_default_serp_zone(self):
        from integrations.bright_data_client import BrightDataClient
        client = BrightDataClient(api_key="test-key")
        assert client.serp_zone == "serp_api1"

    def test_custom_serp_zone(self):
        from integrations.bright_data_client import BrightDataClient
        client = BrightDataClient(api_key="test-key", serp_zone="custom_zone")
        assert client.serp_zone == "custom_zone"

    def test_cost_tracker_initialized(self):
        from integrations.bright_data_client import BrightDataClient
        client = BrightDataClient(api_key="test-key")
        assert client.get_total_cost() == 0.0


class TestCostTracking:
    """Test cost accumulation"""

    def test_cost_breakdown_structure(self):
        from integrations.bright_data_client import BrightDataClient
        client = BrightDataClient(api_key="test-key")
        breakdown = client.get_cost_breakdown()

        assert "serp_requests" in breakdown
        assert "serp_cost_aud" in breakdown
        assert "scraper_records" in breakdown
        assert "scraper_cost_aud" in breakdown
        assert "total_aud" in breakdown

    def test_cost_calculation(self):
        from integrations.bright_data_client import COSTS_AUD, BrightDataClient
        client = BrightDataClient(api_key="test-key")

        # Simulate some costs
        client.costs.serp_requests = 10
        client.costs.scraper_records = 5

        expected = (10 * COSTS_AUD["serp_request"]) + (5 * COSTS_AUD["scraper_record"])
        assert client.get_total_cost() == expected


class TestSERPAPI:
    """Test SERP API methods"""

    @pytest.mark.asyncio
    async def test_search_google_maps_url_format(self):
        from integrations.bright_data_client import BrightDataClient

        client = BrightDataClient(api_key="test-key")

        # Mock the httpx client - uses POST to Direct API with URL in body
        mock_response = Mock()
        mock_response.json.return_value = {"organic": []}
        mock_response.raise_for_status = Mock()
        mock_response.status_code = 200

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response

        with patch.object(client, '_get_client', return_value=mock_client):
            await client.search_google_maps("restaurants", "Melbourne")

        # Verify the URL was constructed correctly in the request body
        call_args = mock_client.post.call_args
        json_body = call_args.kwargs.get("json", {})
        url = json_body.get("url", "")
        assert "google.com/maps/search" in url
        assert "restaurants" in url
        assert "Melbourne" in url
        assert "brd_json=1" in url

    @pytest.mark.asyncio
    async def test_search_google_url_format(self):
        from integrations.bright_data_client import BrightDataClient

        client = BrightDataClient(api_key="test-key")

        mock_response = Mock()
        mock_response.json.return_value = {"organic": []}
        mock_response.raise_for_status = Mock()
        mock_response.status_code = 200

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response

        with patch.object(client, '_get_client', return_value=mock_client):
            await client.search_google('site:linkedin.com/company "test"')

        call_args = mock_client.post.call_args
        json_body = call_args.kwargs.get("json", {})
        url = json_body.get("url", "")
        assert "google.com/search" in url
        assert "brd_json=1" in url

    @pytest.mark.asyncio
    async def test_serp_request_increments_cost(self):
        from integrations.bright_data_client import BrightDataClient

        client = BrightDataClient(api_key="test-key")
        initial_count = client.costs.serp_requests

        mock_response = Mock()
        mock_response.json.return_value = {}
        mock_response.raise_for_status = Mock()
        mock_response.status_code = 200

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response

        with patch.object(client, '_get_client', return_value=mock_client):
            await client.search_google("test query")

        assert client.costs.serp_requests == initial_count + 1


class TestScrapersAPI:
    """Test Scrapers API methods"""

    @pytest.mark.asyncio
    async def test_scrape_linkedin_company_flow(self):
        from integrations.bright_data_client import BrightDataClient

        client = BrightDataClient(api_key="test-key")

        # Mock responses - use Mock() since .json() is synchronous in httpx
        mock_trigger_resp = Mock()
        mock_trigger_resp.json.return_value = {"snapshot_id": "sd_test123"}
        mock_trigger_resp.raise_for_status = Mock()

        mock_progress_resp = Mock()
        mock_progress_resp.json.return_value = {"status": "ready", "records": 1}
        mock_progress_resp.raise_for_status = Mock()

        mock_download_resp = Mock()
        mock_download_resp.json.return_value = [{"name": "Test Company"}]
        mock_download_resp.raise_for_status = Mock()

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_trigger_resp

        # Return different responses based on URL
        async def mock_get(url, **kwargs):
            if "progress" in url:
                return mock_progress_resp
            return mock_download_resp

        mock_client.get = mock_get
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None

        with patch.object(client, '_get_client', return_value=mock_client):
            result = await client.scrape_linkedin_company("https://linkedin.com/company/test")

        assert result["name"] == "Test Company"
        assert client.costs.scraper_records == 1

    @pytest.mark.asyncio
    async def test_scrape_linkedin_jobs_uses_discover_mode(self):
        from integrations.bright_data_client import BrightDataClient

        client = BrightDataClient(api_key="test-key")

        # Mock responses - use Mock() since .json() is synchronous in httpx
        mock_trigger_resp = Mock()
        mock_trigger_resp.json.return_value = {"snapshot_id": "sd_jobs123"}
        mock_trigger_resp.raise_for_status = Mock()

        mock_progress_resp = Mock()
        mock_progress_resp.json.return_value = {"status": "ready", "records": 5}
        mock_progress_resp.raise_for_status = Mock()

        mock_download_resp = Mock()
        mock_download_resp.json.return_value = [{"job_title": f"Job {i}"} for i in range(5)]
        mock_download_resp.raise_for_status = Mock()

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_trigger_resp

        async def mock_get(url, **kwargs):
            if "progress" in url:
                return mock_progress_resp
            return mock_download_resp

        mock_client.get = mock_get
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None

        with patch.object(client, '_get_client', return_value=mock_client):
            await client.scrape_linkedin_jobs("marketing", "Melbourne", "AU")

        # Verify trigger URL includes discover_by parameter
        trigger_call = mock_client.post.call_args
        url = trigger_call[0][0]
        assert "discover_by=keyword" in url
        assert "type=discover_new" in url


class TestErrorHandling:
    """Test error handling"""

    def test_bright_data_error_class_exists(self):
        from integrations.bright_data_client import BrightDataError
        assert issubclass(BrightDataError, Exception)

    @pytest.mark.asyncio
    async def test_serp_request_raises_on_failure(self):
        import httpx

        from integrations.bright_data_client import BrightDataClient, BrightDataError

        client = BrightDataClient(api_key="test-key")

        mock_client = AsyncMock()
        mock_client.post.side_effect = httpx.RequestError("Connection failed")

        with patch.object(client, '_get_client', return_value=mock_client):
            with pytest.raises(BrightDataError):
                await client.search_google("test")
