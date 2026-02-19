"""
Bright Data Unified Client

Wraps both SERP API and Scrapers API with cost tracking and error handling.
Supports Google/Maps searches via SERP API and LinkedIn scraping via Scrapers API.

Note: All methods are async - use with await.
"""

import httpx
import asyncio
import structlog
import urllib.parse
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

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
    Unified async client for Bright Data SERP API and Scrapers API.
    
    Provides methods for:
    - Google/Maps searches via SERP API
    - LinkedIn scraping via Scrapers API
    - Cost tracking across both services
    
    All methods are async and should be called with await.
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
        self._client: Optional[httpx.AsyncClient] = None
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create async HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=60.0, verify=False)
        return self._client
    
    async def close(self):
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
    
    # SERP API Methods
    
    async def search_google_maps(
        self, 
        query: str, 
        location: str,
        max_results: int = 20
    ) -> List[Dict]:
        """
        Search Google Maps via SERP API.
        
        Args:
            query: Search query (e.g., "restaurants")
            location: Location to search in (e.g., "Melbourne")
            max_results: Maximum results to return (default 20)
        
        Returns:
            List of business results with name, phone, website, address, rating, etc.
        
        Cost: $0.0015 AUD per request
        """
        encoded_query = urllib.parse.quote(f"{query} {location}")
        url = f"https://www.google.com/maps/search/{encoded_query}?brd_json=1"
        
        result = await self._serp_request(url)
        
        # Extract business results (limit to max_results)
        if isinstance(result, list):
            return result[:max_results]
        elif isinstance(result, dict) and "organic" in result:
            return result["organic"][:max_results]
        
        return []
    
    async def search_google(self, query: str) -> Dict:
        """
        Search Google via SERP API.
        
        Args:
            query: Search query (e.g., 'site:linkedin.com/company "business name"')
        
        Returns:
            Search results with organic results list
        
        Cost: $0.0015 AUD per request
        """
        encoded_query = urllib.parse.quote(query)
        url = f"https://www.google.com/search?q={encoded_query}&brd_json=1"
        
        return await self._serp_request(url)
    
    async def _serp_request(self, url: str, max_retries: int = 2) -> Any:
        """Execute SERP API request via proxy with retry and alerting."""
        proxy_url = f"http://brd-customer-hl_4af12f98-zone-{self.serp_zone}:{self.api_key}@brd.superproxy.io:33335"
        
        client = await self._get_client()
        last_error = None
        
        for attempt in range(max_retries + 1):
            try:
                response = await client.get(
                    url,
                    proxy=proxy_url,
                    timeout=30.0
                )
                response.raise_for_status()
                self.costs.serp_requests += 1
                
                logger.debug("serp_request_complete", url=url[:100], status=response.status_code)
                return response.json()
                
            except httpx.HTTPStatusError as e:
                last_error = f"HTTP {e.response.status_code}"
                logger.warning("serp_request_error", attempt=attempt, error=last_error)
            except httpx.RequestError as e:
                last_error = str(e)
                logger.warning("serp_request_error", attempt=attempt, error=last_error)
            except Exception as e:
                last_error = str(e)
                logger.warning("serp_request_error", attempt=attempt, error=last_error)
            
            if attempt < max_retries:
                await asyncio.sleep(2 ** attempt)  # Exponential backoff
        
        # All retries exhausted - fire alert
        await self._fire_bright_data_alert(last_error, max_retries + 1)
        raise BrightDataError(f"SERP request failed after {max_retries + 1} attempts: {last_error}")

    async def _fire_bright_data_alert(self, error_message: str, retry_count: int) -> None:
        """Fire alert for Bright Data failure (Directive 048 Part F)."""
        try:
            from src.integrations.supabase import get_db_session
            from src.services.alert_service import get_alert_service
            
            async with get_db_session() as db:
                alert_service = get_alert_service(db)
                await alert_service.alert_bright_data_error(
                    error_message=error_message,
                    retry_count=retry_count,
                    metadata={"api_type": "serp"},
                )
        except Exception as e:
            logger.error("failed_to_fire_bright_data_alert", error=str(e))
    
    # Scrapers API Methods
    
    async def scrape_linkedin_company(self, linkedin_url: str) -> Dict:
        """
        Scrape LinkedIn Company via Scrapers API.
        
        Args:
            linkedin_url: LinkedIn company URL
        
        Returns:
            Company profile with name, industry, employees[], updates[], etc.
        
        Cost: $0.0015 AUD per record
        """
        results = await self._scraper_request(
            DATASET_IDS["linkedin_company"],
            [{"url": linkedin_url}]
        )
        return results[0] if results else {}
    
    async def scrape_linkedin_profile(self, linkedin_url: str) -> Dict:
        """
        Scrape LinkedIn People Profile via Scrapers API.
        
        Args:
            linkedin_url: LinkedIn profile URL
        
        Returns:
            Person profile with name, experience, education, skills, etc.
        
        Cost: $0.0015 AUD per record
        """
        results = await self._scraper_request(
            DATASET_IDS["linkedin_people"],
            [{"url": linkedin_url}]
        )
        return results[0] if results else {}
    
    async def scrape_linkedin_jobs(
        self, 
        keyword: str, 
        location: str, 
        country: str = "AU"
    ) -> List[Dict]:
        """
        Discover LinkedIn Jobs via keyword search.
        
        Args:
            keyword: Job keyword (e.g., "marketing")
            location: Location (e.g., "Melbourne")
            country: Country code (default: "AU")
        
        Returns:
            List of job postings
        
        Cost: $0.0015 AUD per record
        """
        return await self._scraper_request(
            DATASET_IDS["linkedin_jobs"],
            [{"keyword": keyword, "location": location, "country": country}],
            discover_by="keyword"
        )
    
    async def _scraper_request(
        self, 
        dataset_id: str, 
        inputs: List[Dict], 
        discover_by: str = None
    ) -> List[Dict]:
        """Execute Scraper API: trigger → poll → download."""
        base_url = "https://api.brightdata.com/datasets/v3"
        headers = {
            "Authorization": f"Bearer {self.api_key}", 
            "Content-Type": "application/json"
        }
        
        # Build trigger URL
        trigger_url = f"{base_url}/trigger?dataset_id={dataset_id}&include_errors=true"
        if discover_by:
            trigger_url += f"&type=discover_new&discover_by={discover_by}"
        
        client = await self._get_client()
        
        # Trigger
        try:
            response = await client.post(
                trigger_url, 
                headers=headers, 
                json=inputs, 
                timeout=30.0
            )
            response.raise_for_status()
            snapshot_id = response.json()["snapshot_id"]
            logger.info("scraper_triggered", snapshot_id=snapshot_id, dataset_id=dataset_id)
        except httpx.HTTPStatusError as e:
            raise BrightDataError(f"Scraper trigger failed: HTTP {e.response.status_code}")
        except httpx.RequestError as e:
            raise BrightDataError(f"Scraper trigger failed: {str(e)}")
        
        # Poll until ready (max 5 minutes)
        for _ in range(60):
            try:
                progress = await client.get(
                    f"{base_url}/progress/{snapshot_id}",
                    headers=headers,
                    timeout=10.0
                )
                status_data = progress.json()
                status = status_data.get("status")
                
                if status == "ready":
                    records = status_data.get("records", 0)
                    self.costs.scraper_records += records
                    logger.info("scraper_ready", snapshot_id=snapshot_id, records=records)
                    break
                elif status == "failed":
                    raise BrightDataError(f"Scraper job failed: {status_data}")
                    
            except httpx.RequestError:
                pass  # Retry on network errors
            
            await asyncio.sleep(5)
        else:
            raise BrightDataError(f"Scraper timeout for snapshot {snapshot_id}")
        
        # Download results
        try:
            data = await client.get(
                f"{base_url}/snapshot/{snapshot_id}?format=json",
                headers=headers,
                timeout=60.0
            )
            data.raise_for_status()
            return data.json()
        except httpx.HTTPStatusError as e:
            raise BrightDataError(f"Scraper download failed: HTTP {e.response.status_code}")
        except httpx.RequestError as e:
            raise BrightDataError(f"Scraper download failed: {str(e)}")
    
    # Cost tracking methods
    
    def get_total_cost(self) -> float:
        """Return total AUD spent this session."""
        return self.costs.total_aud
    
    def get_cost_breakdown(self) -> Dict[str, Any]:
        """Return costs by method/tier."""
        return {
            "serp_requests": self.costs.serp_requests,
            "serp_cost_aud": self.costs.serp_requests * COSTS_AUD["serp_request"],
            "scraper_records": self.costs.scraper_records,
            "scraper_cost_aud": self.costs.scraper_records * COSTS_AUD["scraper_record"],
            "total_aud": self.costs.total_aud
        }
