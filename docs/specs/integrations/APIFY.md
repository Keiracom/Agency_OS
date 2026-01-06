# Apify Integration

**File:** `src/integrations/apify.py`  
**Purpose:** Web scraping for ICP discovery and bulk data collection  
**API Docs:** https://docs.apify.com/api/v2  
**Waterfall Spec:** `docs/specs/integrations/SCRAPER_WATERFALL.md`

---

## Role in Scraper Waterfall

Apify provides **Tier 1 and Tier 2** of the scraper waterfall:

| Tier | Crawler | Use Case | Success Rate |
|------|---------|----------|--------------|
| **Tier 1** | Cheerio | Static HTML sites | ~60% |
| **Tier 2** | Playwright | JS-rendered sites | ~80% |

For sites that fail both tiers (Cloudflare-protected), see `SCRAPER_WATERFALL.md` for Tier 3 (Camoufox) fallback.

---

## Capabilities

- Website content scraping (static + JS-rendered)
- LinkedIn profile scraping (via actors)
- Bulk data extraction
- Pre-built actors for common tasks
- Automatic proxy rotation

---

## Primary Method: Website Scraping

```python
from apify_client import ApifyClient

class ApifyIntegration:
    def __init__(self, api_key: str):
        self.client = ApifyClient(api_key)
    
    async def scrape_website_with_waterfall(
        self,
        url: str,
        max_pages: int = 10,
    ) -> ScrapeResult:
        """
        Scrape website with tiered fallback:
        1. Try Cheerio (fast, static HTML)
        2. If empty, try Playwright (JS rendering)
        """
        # Tier 1: Cheerio
        result = await self._scrape_cheerio(url, max_pages)
        if result.page_count > 0 and len(result.raw_html) > 500:
            result.tier_used = 1
            return result
        
        # Tier 2: Playwright
        result = await self._scrape_playwright(url, max_pages)
        if result.page_count > 0 and len(result.raw_html) > 500:
            result.tier_used = 2
            return result
        
        # Both failed
        return ScrapeResult(
            url=url,
            page_count=0,
            raw_html="",
            tier_used=2,
            needs_fallback=True,
            failure_reason="Both Cheerio and Playwright returned empty"
        )

    async def _scrape_cheerio(self, url: str, max_pages: int) -> ScrapeResult:
        """Tier 1: Static HTML scraping."""
        run = self.client.actor("apify/website-content-crawler").call(
            run_input={
                "startUrls": [{"url": url}],
                "maxCrawlPages": max_pages,
                "crawlerType": "cheerio",
                "requestTimeoutSecs": 30,
                "saveHtml": True,
                "includeUrlGlobs": ["*/about*", "*/team*", "*/services*", "*/clients*"]
            }
        )
        return self._process_results(run)

    async def _scrape_playwright(self, url: str, max_pages: int) -> ScrapeResult:
        """Tier 2: JS-rendered scraping."""
        run = self.client.actor("apify/website-content-crawler").call(
            run_input={
                "startUrls": [{"url": url}],
                "maxCrawlPages": max_pages,
                "crawlerType": "playwright",
                "requestTimeoutSecs": 60,
                "saveHtml": True,
                "includeUrlGlobs": ["*/about*", "*/team*", "*/services*", "*/clients*"]
            }
        )
        return self._process_results(run)
    
    def _process_results(self, run: dict) -> ScrapeResult:
        """Process Apify run results into ScrapeResult."""
        pages = []
        raw_html_parts = []
        
        for item in self.client.dataset(run["defaultDatasetId"]).iterate_items():
            pages.append(item)
            if item.get("html"):
                raw_html_parts.append(item["html"])
        
        return ScrapeResult(
            url=pages[0]["url"] if pages else "",
            page_count=len(pages),
            raw_html="\n\n".join(raw_html_parts),
            pages=pages
        )
```

---

## Content Validation

**CRITICAL:** Always validate that content was actually retrieved.

```python
def is_valid_content(result: ScrapeResult) -> bool:
    """Check if scrape returned meaningful content."""
    if result.page_count == 0:
        return False
    if len(result.raw_html) < 500:
        return False
    
    # Check for blocked page indicators
    blocked_indicators = [
        "Access denied",
        "Please enable JavaScript",
        "Checking your browser",
        "Ray ID:"
    ]
    for indicator in blocked_indicators:
        if indicator.lower() in result.raw_html.lower():
            return False
    
    return True
```

---

## Common Actors

| Actor | Purpose | Cost |
|-------|---------|------|
| `apify/website-content-crawler` | Website pages | ~$0.25-0.50/1k pages |
| `apify/linkedin-profile-scraper` | LinkedIn profiles | ~$0.01/profile |
| `apify/google-search-scraper` | Search results | ~$0.002/search |

---

## Crawler Types

| Type | Best For | Speed | JS Support |
|------|----------|-------|------------|
| `cheerio` | Static HTML | Fast (5-10s) | ❌ No |
| `playwright` | Dynamic sites | Medium (15-30s) | ✅ Yes |

**Default strategy:** Start with Cheerio, fall back to Playwright if empty.

---

## Configuration Options

```python
run_input = {
    "startUrls": [{"url": url}],
    "maxCrawlPages": 10,           # Limit pages to scrape
    "crawlerType": "cheerio",      # or "playwright"
    "requestTimeoutSecs": 30,      # Per-request timeout
    "saveHtml": True,              # REQUIRED for ICP extraction
    "includeUrlGlobs": [           # Focus on relevant pages
        "*/about*",
        "*/team*",
        "*/services*",
        "*/clients*",
        "*/work*",
        "*/portfolio*"
    ],
    "excludeUrlGlobs": [           # Skip irrelevant pages
        "*/blog/*",
        "*/news/*",
        "*/careers/*"
    ]
}
```

---

## Rate Limits

- **Concurrent runs:** 25 (default)
- **Memory:** 4GB per run (default)
- **Timeout:** 30-60 seconds recommended

---

## Cost Estimates

| Crawler | Cost per 1k Pages | Typical ICP Scrape |
|---------|-------------------|-------------------|
| Cheerio | ~$0.25 | ~$0.0025 (10 pages) |
| Playwright | ~$0.50 | ~$0.005 (10 pages) |

**For 8,000 agencies:** ~$20-40 for Tier 1+2 combined

---

## Error Handling

```python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(stop=stop_after_attempt(2), wait=wait_exponential(min=1, max=10))
async def scrape_with_retry(self, url: str) -> ScrapeResult:
    """Scrape with automatic retry on transient failures."""
    try:
        return await self.scrape_website_with_waterfall(url)
    except ApifyClientError as e:
        if "rate limit" in str(e).lower():
            raise  # Let retry handle it
        # Log and return failure
        return ScrapeResult(
            url=url,
            needs_fallback=True,
            failure_reason=str(e)
        )
```

---

## Related Documents

- `docs/specs/integrations/SCRAPER_WATERFALL.md` - Full waterfall architecture
- `docs/phases/PHASE_11_ICP.md` - ICP discovery flow
- `src/engines/icp_scraper.py` - Scraper engine implementation
