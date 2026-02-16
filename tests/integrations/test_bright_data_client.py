"""
Unit tests for BrightDataClient

Tests the unified Bright Data client covering SERP API and Scrapers API.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
import sys
import os

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
        from integrations.bright_data_client import BrightDataClient, COSTS_AUD
        client = BrightDataClient(api_key="test-key")
        
        # Simulate some costs
        client.costs.serp_requests = 10
        client.costs.scraper_records = 5
        
        expected = (10 * COSTS_AUD["serp_request"]) + (5 * COSTS_AUD["scraper_record"])
        assert client.get_total_cost() == expected


class TestSERPAPI:
    """Test SERP API methods"""
    
    @patch('requests.Session.get')
    def test_search_google_maps_url_format(self, mock_get):
        from integrations.bright_data_client import BrightDataClient
        
        mock_response = Mock()
        mock_response.json.return_value = {"results": []}
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        client = BrightDataClient(api_key="test-key")
        client.search_google_maps("restaurants", "Melbourne")
        
        # Verify the URL was constructed correctly
        call_args = mock_get.call_args
        url = call_args[0][0]
        assert "google.com/maps/search" in url
        assert "restaurants" in url
        assert "Melbourne" in url
        assert "brd_json=1" in url
    
    @patch('requests.Session.get')
    def test_search_google_url_format(self, mock_get):
        from integrations.bright_data_client import BrightDataClient
        
        mock_response = Mock()
        mock_response.json.return_value = {"organic": []}
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        client = BrightDataClient(api_key="test-key")
        client.search_google('site:linkedin.com/company "test"')
        
        call_args = mock_get.call_args
        url = call_args[0][0]
        assert "google.com/search" in url
        assert "brd_json=1" in url
    
    @patch('requests.Session.get')
    def test_serp_request_increments_cost(self, mock_get):
        from integrations.bright_data_client import BrightDataClient
        
        mock_response = Mock()
        mock_response.json.return_value = {}
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        client = BrightDataClient(api_key="test-key")
        initial_count = client.costs.serp_requests
        
        client.search_google("test query")
        
        assert client.costs.serp_requests == initial_count + 1


class TestScrapersAPI:
    """Test Scrapers API methods"""
    
    @patch('requests.Session.get')
    @patch('requests.Session.post')
    def test_scrape_linkedin_company_flow(self, mock_post, mock_get):
        from integrations.bright_data_client import BrightDataClient
        
        # Mock trigger response
        mock_trigger = Mock()
        mock_trigger.json.return_value = {"snapshot_id": "sd_test123"}
        mock_trigger.raise_for_status = Mock()
        mock_post.return_value = mock_trigger
        
        # Mock progress and download responses
        def mock_get_side_effect(url, **kwargs):
            mock_resp = Mock()
            mock_resp.raise_for_status = Mock()
            if "progress" in url:
                mock_resp.json.return_value = {"status": "ready", "records": 1}
            else:
                mock_resp.json.return_value = [{"name": "Test Company"}]
            return mock_resp
        
        mock_get.side_effect = mock_get_side_effect
        
        client = BrightDataClient(api_key="test-key")
        result = client.scrape_linkedin_company("https://linkedin.com/company/test")
        
        assert result["name"] == "Test Company"
        assert client.costs.scraper_records == 1
    
    @patch('requests.Session.get')
    @patch('requests.Session.post')
    def test_scrape_linkedin_jobs_uses_discover_mode(self, mock_post, mock_get):
        from integrations.bright_data_client import BrightDataClient
        
        mock_trigger = Mock()
        mock_trigger.json.return_value = {"snapshot_id": "sd_jobs123"}
        mock_trigger.raise_for_status = Mock()
        mock_post.return_value = mock_trigger
        
        def mock_get_side_effect(url, **kwargs):
            mock_resp = Mock()
            mock_resp.raise_for_status = Mock()
            if "progress" in url:
                mock_resp.json.return_value = {"status": "ready", "records": 5}
            else:
                mock_resp.json.return_value = [{"job_title": f"Job {i}"} for i in range(5)]
            return mock_resp
        
        mock_get.side_effect = mock_get_side_effect
        
        client = BrightDataClient(api_key="test-key")
        client.scrape_linkedin_jobs("marketing", "Melbourne", "AU")
        
        # Verify trigger URL includes discover_by parameter
        trigger_call = mock_post.call_args
        url = trigger_call[0][0]
        assert "discover_by=keyword" in url
        assert "type=discover_new" in url


class TestErrorHandling:
    """Test error handling"""
    
    def test_bright_data_error_class_exists(self):
        from integrations.bright_data_client import BrightDataError
        assert issubclass(BrightDataError, Exception)
    
    @patch('requests.Session.get')
    def test_serp_request_raises_on_failure(self, mock_get):
        from integrations.bright_data_client import BrightDataClient, BrightDataError
        import requests
        
        mock_get.side_effect = requests.RequestException("Connection failed")
        
        client = BrightDataClient(api_key="test-key")
        
        with pytest.raises(BrightDataError):
            client.search_google("test")
