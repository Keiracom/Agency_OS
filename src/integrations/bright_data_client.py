"""
Bright Data Unified Client

Wraps both SERP API and Scrapers API with cost tracking and error handling.
Supports Google/Maps searches via SERP API and LinkedIn scraping via Scrapers API.
"""

import requests
import time
import structlog
import urllib.parse
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field

logger = structlog.get_logger()

# Verified dataset IDs from Directive #020d
DATASET_IDS = {
    "linkedin_company": "gd_l1vikfnt1wgvvqz95w",
    "linkedin_people": "gd_l1viktl72bvl7bjuj0",
    "linkedin_jobs": "gd_lpfll7v5hcqtkxl6l"
}

COSTS_AUD = {
    "serp_request": 0.0015,
    "scraper_record": 0.0015
}


class BrightDataError(Exception):
    """Bright Data API error"""
    pass


@dataclass
class CostTracker:
    """Tracks API usage costs for the session"""
    serp_requests: int = 0
    scraper_records: int = 0
    
    @property
    def total_aud(self) -> float:
        """Calculate total cost in AUD for this session"""
        return (self.serp_requests * COSTS_AUD["serp_request"] + 
                self.scraper_records * COSTS_AUD["scraper_record"])


class BrightDataClient:
    """
    Unified client for Bright Data SERP API and Scrapers API.
    
    Provides methods for:
    - Google/Maps searches via SERP API
    - LinkedIn scraping via Scrapers API
    - Cost tracking across both services
    """
    
    def __init__(self, api_key: str, serp_zone: str = "serp_api1"):
        """
        Initialize the Bright Data client.
        
        Args:
            api_key: Your Bright Data API key
            serp_zone: Zone for SERP API proxy (default: "serp_api1")
        """
        self.api_key = api_key
        self.serp_zone = serp_zone
        self.costs = CostTracker()
        self._session = requests.Session()
    
    # SERP API Methods
    
    def search_google_maps(self, query: str, location: str) -> List[Dict]:
        """
        Search Google Maps via SERP API.
        
        Args:
            query: Search query (e.g., "restaurants")
            location: Location to search in (e.g., "Melbourne")
            
        Returns:
            List of business results from Google Maps
            
        Raises:
            BrightDataError: If the SERP request fails
            
        Cost: $0.0015 AUD per request
        """
        url = f"https://www.google.com/maps/search/{query}+{location}?brd_json=1"
        return self._serp_request(url)
    
    def search_google(self, query: str) -> List[Dict]:
        """
        Search Google via SERP API.
        
        Args:
            query: Search query string
            
        Returns:
            List of organic search results from Google
            
        Raises:
            BrightDataError: If the SERP request fails
            
        Cost: $0.0015 AUD per request
        """
        encoded_query = urllib.parse.quote(query)
        url = f"https://www.google.com/search?q={encoded_query}&brd_json=1"
        return self._serp_request(url)
    
    def _serp_request(self, url: str) -> Any:
        """
        Execute SERP API request via proxy.
        
        Args:
            url: Target URL to scrape
            
        Returns:
            JSON response from the target URL
            
        Raises:
            BrightDataError: If the request fails
        """
        proxy_url = f"http://brd-customer-hl_4af12f98-zone-{self.serp_zone}:{self.api_key}@brd.superproxy.io:33335"
        
        try:
            response = self._session.get(
                url,
                proxies={"http": proxy_url, "https": proxy_url},
                verify=False,
                timeout=30
            )
            response.raise_for_status()
            self.costs.serp_requests += 1
            logger.info("serp_request_success", url=url, cost_aud=COSTS_AUD["serp_request"])
            return response.json()
        except requests.RequestException as e:
            logger.error("serp_request_failed", url=url, error=str(e))
            raise BrightDataError(f"SERP request failed: {e}")
    
    # Scrapers API Methods
    
    def scrape_linkedin_company(self, linkedin_url: str) -> Dict:
        """
        Scrape LinkedIn Company profile via Scrapers API.
        
        Args:
            linkedin_url: Full LinkedIn company URL
            
        Returns:
            Company profile data including name, employees, about, etc.
            
        Raises:
            BrightDataError: If scraping fails
            
        Dataset: gd_l1vikfnt1wgvvqz95w
        Cost: $0.0015 AUD per record
        """
        results = self._scraper_request(
            DATASET_IDS["linkedin_company"],
            [{"url": linkedin_url}]
        )
        return results[0] if results else {}
    
    def scrape_linkedin_profile(self, linkedin_url: str) -> Dict:
        """
        Scrape LinkedIn People Profile via Scrapers API.
        
        Args:
            linkedin_url: Full LinkedIn profile URL
            
        Returns:
            Profile data including name, title, experience, etc.
            
        Raises:
            BrightDataError: If scraping fails
            
        Dataset: gd_l1viktl72bvl7bjuj0
        Cost: $0.0015 AUD per record
        """
        results = self._scraper_request(
            DATASET_IDS["linkedin_people"],
            [{"url": linkedin_url}]
        )
        return results[0] if results else {}
    
    def scrape_linkedin_jobs(self, keyword: str, location: str, country: str = "AU") -> List[Dict]:
        """
        Discover LinkedIn Jobs via keyword search.
        
        Args:
            keyword: Job search keyword (e.g., "marketing")
            location: Location to search in (e.g., "Melbourne") 
            country: Country code (default: "AU")
            
        Returns:
            List of job postings matching the criteria
            
        Raises:
            BrightDataError: If scraping fails
            
        Dataset: gd_lpfll7v5hcqtkxl6l
        Discovery mode: keyword
        Cost: $0.0015 AUD per record
        """
        return self._scraper_request(
            DATASET_IDS["linkedin_jobs"],
            [{"keyword": keyword, "location": location, "country": country}],
            discover_by="keyword"
        )
    
    def _scraper_request(self, dataset_id: str, inputs: List[Dict], discover_by: str = None) -> List[Dict]:
        """
        Execute Scraper API request: trigger → poll → download.
        
        Args:
            dataset_id: Bright Data dataset ID
            inputs: List of input parameters for the dataset
            discover_by: Discovery mode ("keyword" for jobs)
            
        Returns:
            List of scraped records
            
        Raises:
            BrightDataError: If any step of the process fails
        """
        base_url = "https://api.brightdata.com/datasets/v3"
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        
        # Build trigger URL
        trigger_url = f"{base_url}/trigger?dataset_id={dataset_id}&include_errors=true"
        if discover_by:
            trigger_url += f"&type=discover_new&discover_by={discover_by}"
        
        # Trigger collection
        try:
            response = self._session.post(trigger_url, headers=headers, json=inputs, timeout=30)
            response.raise_for_status()
            snapshot_id = response.json()["snapshot_id"]
            logger.info("scraper_triggered", snapshot_id=snapshot_id, dataset_id=dataset_id, discover_by=discover_by)
        except requests.RequestException as e:
            logger.error("scraper_trigger_failed", dataset_id=dataset_id, error=str(e))
            raise BrightDataError(f"Scraper trigger failed: {e}")
        
        # Poll until ready (max 5 minutes)
        for attempt in range(60):
            try:
                progress = self._session.get(
                    f"{base_url}/progress/{snapshot_id}",
                    headers=headers,
                    timeout=10
                )
                progress_data = progress.json()
                status = progress_data.get("status")
                
                if status == "ready":
                    records = progress_data.get("records", 0)
                    self.costs.scraper_records += records
                    logger.info("scraper_ready", snapshot_id=snapshot_id, records=records, 
                              cost_aud=records * COSTS_AUD["scraper_record"])
                    break
                elif status == "failed":
                    logger.error("scraper_failed", snapshot_id=snapshot_id, progress_data=progress_data)
                    raise BrightDataError(f"Scraper job failed: {progress_data}")
                else:
                    logger.debug("scraper_polling", snapshot_id=snapshot_id, status=status, attempt=attempt + 1)
            except requests.RequestException as e:
                logger.warning("scraper_poll_error", snapshot_id=snapshot_id, attempt=attempt + 1, error=str(e))
                pass
            
            time.sleep(5)
        else:
            logger.error("scraper_timeout", snapshot_id=snapshot_id)
            raise BrightDataError(f"Scraper timeout for snapshot {snapshot_id}")
        
        # Download results
        try:
            data = self._session.get(
                f"{base_url}/snapshot/{snapshot_id}?format=json",
                headers=headers,
                timeout=60
            )
            data.raise_for_status()
            results = data.json()
            logger.info("scraper_download_success", snapshot_id=snapshot_id, records=len(results))
            return results
        except requests.RequestException as e:
            logger.error("scraper_download_failed", snapshot_id=snapshot_id, error=str(e))
            raise BrightDataError(f"Scraper download failed: {e}")
    
    # Cost tracking methods
    
    def get_total_cost(self) -> float:
        """
        Get total AUD spent this session.
        
        Returns:
            Total cost in AUD
        """
        return self.costs.total_aud
    
    def get_cost_breakdown(self) -> Dict[str, Any]:
        """
        Get detailed cost breakdown by service type.
        
        Returns:
            Dictionary with cost breakdown including:
            - serp_requests: Number of SERP API requests
            - serp_cost_aud: Cost of SERP requests in AUD
            - scraper_records: Number of scraper records
            - scraper_cost_aud: Cost of scraper records in AUD
            - total_aud: Total cost in AUD
        """
        return {
            "serp_requests": self.costs.serp_requests,
            "serp_cost_aud": self.costs.serp_requests * COSTS_AUD["serp_request"],
            "scraper_records": self.costs.scraper_records,
            "scraper_cost_aud": self.costs.scraper_records * COSTS_AUD["scraper_record"],
            "total_aud": self.costs.total_aud
        }