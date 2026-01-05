# Apify Integration

**File:** `src/integrations/apify.py`  
**Purpose:** Web scraping for bulk data collection  
**API Docs:** https://docs.apify.com/api/v2

---

## Capabilities

- LinkedIn profile scraping
- Company website scraping
- Bulk data extraction
- Pre-built actors for common tasks

---

## Usage Pattern

```python
from apify_client import ApifyClient

class ApifyIntegration:
    def __init__(self, api_key: str):
        self.client = ApifyClient(api_key)
    
    async def scrape_linkedin_profiles(
        self,
        linkedin_urls: list[str]
    ) -> list[LinkedInProfile]:
        """Scrape LinkedIn profiles in bulk."""
        run = self.client.actor("apify/linkedin-profile-scraper").call(
            run_input={
                "profileUrls": linkedin_urls,
                "proxy": {"useApifyProxy": True}
            }
        )
        
        results = []
        for item in self.client.dataset(run["defaultDatasetId"]).iterate_items():
            results.append(LinkedInProfile(**item))
        return results
    
    async def scrape_company_website(
        self,
        url: str,
        max_pages: int = 10
    ) -> WebsiteContent:
        """Scrape company website for ICP discovery."""
        run = self.client.actor("apify/website-content-crawler").call(
            run_input={
                "startUrls": [{"url": url}],
                "maxCrawlPages": max_pages,
                "includeUrlGlobs": ["*/about*", "*/team*", "*/services*", "*/clients*"]
            }
        )
        
        pages = []
        for item in self.client.dataset(run["defaultDatasetId"]).iterate_items():
            pages.append(PageContent(**item))
        return WebsiteContent(url=url, pages=pages)
```

---

## Common Actors

| Actor | Purpose | Cost |
|-------|---------|------|
| `apify/linkedin-profile-scraper` | LinkedIn profiles | ~$0.01/profile |
| `apify/website-content-crawler` | Website pages | ~$0.005/page |
| `apify/google-search-scraper` | Search results | ~$0.002/search |

---

## Rate Limits

- **Concurrent runs:** 25 (default)
- **Memory:** 4GB per run (default)

---

## Cost

- **Compute units:** ~$0.01-0.02 per 1000 results
- **Proxy:** Included with Apify proxy
