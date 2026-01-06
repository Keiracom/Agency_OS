# Scraper Waterfall Architecture

**Created:** January 5, 2026  
**Status:** APPROVED  
**Purpose:** Multi-tier scraping strategy with graceful degradation for protected websites

---

## Problem Statement

During E2E testing, we discovered that Cloudflare-protected websites (and similar bot detection systems) cause Apify scrapers to timeout or return empty content. This affects an estimated 30-50% of Australian agency websites.

**Example failure:**
- URL: `dilatedigital.com.au` (incorrect — actual domain is `dilate.com.au`)
- Apify returned: 0 pages, empty HTML
- Root cause: Cloudflare bot protection + 30s timeout

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     URL SUBMITTED                               │
└─────────────────────────┬───────────────────────────────────────┘
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│  TIER 0: URL Validation & Normalization                         │
│  ─────────────────────────────────────────────────────────────  │
│  • Follow redirects to get canonical URL                        │
│  • Check if domain resolves (DNS lookup)                        │
│  • Detect parked/for-sale domains                               │
│  • Validate URL format                                          │
│  • Cost: FREE | Time: <2s | Success: 100%                       │
└─────────────────────────┬───────────────────────────────────────┘
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│  TIER 1: Apify Cheerio (Static HTML)                            │
│  ─────────────────────────────────────────────────────────────  │
│  • Fast, cheap, handles ~60% of sites                           │
│  • Fails on: JS-rendered content, Cloudflare, bot detection     │
│  • Actor: apify/website-content-crawler (crawlerType: cheerio)  │
│  • Cost: ~$0.25/1k pages | Time: 5-10s | Success: ~60%          │
│  • SUCCESS (content.length > 500) → ICP extraction              │
│  • FAIL (empty/blocked/timeout) → Tier 2                        │
└─────────────────────────┬───────────────────────────────────────┘
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│  TIER 2: Apify Playwright (JS Rendering)                        │
│  ─────────────────────────────────────────────────────────────  │
│  • Handles JS-heavy sites (React, Vue, Angular, etc.)           │
│  • Fails on: Cloudflare Turnstile, aggressive bot detection     │
│  • Actor: apify/website-content-crawler (crawlerType: playwright)│
│  • Cost: ~$0.50/1k pages | Time: 15-30s | Success: ~80%         │
│  • SUCCESS → ICP extraction                                     │
│  • FAIL → Tier 3                                                │
└─────────────────────────┬───────────────────────────────────────┘
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│  TIER 3: Camoufox + Residential Proxy (Anti-Detection)          │
│  ─────────────────────────────────────────────────────────────  │
│  • Handles Cloudflare, Turnstile, most bot detection            │
│  • Uses Camoufox (Firefox-based anti-detect browser)            │
│  • Requires residential proxy for clean IP reputation           │
│  • Runs locally in Railway backend container                    │
│  • Cost: ~$0.02-0.05/page (proxy) | Time: 20-45s | Success: ~95%│
│  • SUCCESS → ICP extraction                                     │
│  • FAIL → Tier 4                                                │
└─────────────────────────┬───────────────────────────────────────┘
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│  TIER 4: Manual Fallback                                        │
│  ─────────────────────────────────────────────────────────────  │
│  • Flag for user intervention                                   │
│  • Options presented to user:                                   │
│    a) Paste website content directly (textarea)                 │
│    b) Provide LinkedIn company URL instead                      │
│    c) Skip ICP extraction, use basic company info               │
│    d) Try a different URL                                       │
│  • Cost: FREE | Time: User-dependent | Success: 100%            │
└─────────────────────────────────────────────────────────────────┘
```

---

## Implementation Details

### Tier 0: URL Validation

**File:** `src/engines/url_validator.py` (NEW)

```python
import httpx
from urllib.parse import urlparse

class URLValidator:
    """Validate and normalize URLs before scraping."""
    
    async def validate_and_normalize(self, url: str) -> URLValidationResult:
        """
        1. Parse and validate URL format
        2. Follow redirects to get canonical URL
        3. Check if domain resolves
        4. Detect parked/placeholder pages
        """
        # Normalize URL
        if not url.startswith(('http://', 'https://')):
            url = f'https://{url}'
        
        parsed = urlparse(url)
        if not parsed.netloc:
            return URLValidationResult(
                valid=False,
                error="Invalid URL format"
            )
        
        # Follow redirects
        async with httpx.AsyncClient(follow_redirects=True, timeout=10) as client:
            try:
                response = await client.head(url)
                canonical_url = str(response.url)
                
                # Check for parked domain indicators
                if self._is_parked_domain(response):
                    return URLValidationResult(
                        valid=False,
                        error="Domain appears to be parked or for sale"
                    )
                
                return URLValidationResult(
                    valid=True,
                    canonical_url=canonical_url,
                    redirected=canonical_url != url
                )
            except httpx.ConnectError:
                return URLValidationResult(
                    valid=False,
                    error="Domain does not resolve"
                )
            except httpx.TimeoutException:
                return URLValidationResult(
                    valid=False,
                    error="Connection timeout"
                )
    
    def _is_parked_domain(self, response: httpx.Response) -> bool:
        """Detect parked domain indicators."""
        parked_indicators = [
            'godaddy.com/parking',
            'sedoparking.com',
            'dan.com',
            'This domain is for sale'
        ]
        # Check response headers or do quick content check
        return False  # Implement based on response analysis
```

### Tier 1 & 2: Apify Integration Update

**File:** `src/integrations/apify.py`

```python
async def scrape_website_with_waterfall(
    self,
    url: str,
    max_pages: int = 10,
) -> ScrapeResult:
    """
    Scrape website with tiered fallback:
    1. Try Cheerio (fast, static HTML)
    2. If empty, try Playwright (JS rendering)
    3. Return result with tier indicator
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
    
    # Both failed - return empty with failure flag
    return ScrapeResult(
        url=url,
        page_count=0,
        raw_html="",
        tier_used=2,
        needs_fallback=True,
        failure_reason="Both Cheerio and Playwright returned empty content"
    )

async def _scrape_cheerio(self, url: str, max_pages: int) -> ScrapeResult:
    """Tier 1: Static HTML scraping with Cheerio."""
    actor = self.client.actor("apify/website-content-crawler")
    run = await actor.call(
        run_input={
            "startUrls": [{"url": url}],
            "maxCrawlPages": max_pages,
            "crawlerType": "cheerio",
            "requestTimeoutSecs": 30,
            "saveHtml": True,
        }
    )
    return self._process_results(run)

async def _scrape_playwright(self, url: str, max_pages: int) -> ScrapeResult:
    """Tier 2: JS-rendered scraping with Playwright."""
    actor = self.client.actor("apify/website-content-crawler")
    run = await actor.call(
        run_input={
            "startUrls": [{"url": url}],
            "maxCrawlPages": max_pages,
            "crawlerType": "playwright",
            "requestTimeoutSecs": 60,
            "saveHtml": True,
        }
    )
    return self._process_results(run)
```

### Tier 3: Camoufox Integration

**File:** `src/integrations/camoufox_scraper.py` (NEW)

```python
"""
Camoufox-based scraper for Cloudflare-protected sites.
Runs in Railway backend container with residential proxy.
"""
from camoufox.async_api import AsyncCamoufox
from typing import Optional

class CamoufoxScraper:
    """Anti-detection browser scraper using Camoufox."""
    
    def __init__(self, proxy_config: Optional[dict] = None):
        """
        Initialize with optional proxy configuration.
        
        proxy_config example:
        {
            "server": "http://proxy.webshare.io:80",
            "username": "user",
            "password": "pass"
        }
        """
        self.proxy_config = proxy_config
    
    async def scrape(
        self,
        url: str,
        wait_for_cloudflare: bool = True,
        timeout_ms: int = 45000
    ) -> ScrapeResult:
        """
        Scrape a protected website using Camoufox.
        
        1. Launch anti-detect Firefox browser
        2. Navigate to URL
        3. Wait for Cloudflare challenge if detected
        4. Extract page content
        """
        async with AsyncCamoufox(
            headless=True,
            proxy=self.proxy_config
        ) as browser:
            page = await browser.new_page()
            
            try:
                # Navigate with extended timeout for challenges
                await page.goto(url, wait_until="networkidle", timeout=timeout_ms)
                
                # Wait for potential Cloudflare challenge
                if wait_for_cloudflare:
                    await self._wait_for_cloudflare(page)
                
                # Extract content
                html = await page.content()
                title = await page.title()
                
                # Validate we got real content
                if len(html) < 500 or self._is_blocked_page(html):
                    return ScrapeResult(
                        url=url,
                        page_count=0,
                        raw_html="",
                        tier_used=3,
                        needs_fallback=True,
                        failure_reason="Blocked or empty content"
                    )
                
                return ScrapeResult(
                    url=url,
                    page_count=1,
                    raw_html=html,
                    title=title,
                    tier_used=3,
                    needs_fallback=False
                )
                
            except Exception as e:
                return ScrapeResult(
                    url=url,
                    page_count=0,
                    raw_html="",
                    tier_used=3,
                    needs_fallback=True,
                    failure_reason=str(e)
                )
    
    async def _wait_for_cloudflare(self, page, max_wait_ms: int = 10000):
        """Wait for Cloudflare challenge to complete."""
        # Check for Cloudflare challenge indicators
        cloudflare_selectors = [
            "#challenge-running",
            "#challenge-stage",
            ".cf-browser-verification"
        ]
        
        for selector in cloudflare_selectors:
            try:
                element = await page.query_selector(selector)
                if element:
                    # Wait for challenge to disappear
                    await page.wait_for_selector(
                        selector,
                        state="hidden",
                        timeout=max_wait_ms
                    )
                    # Extra wait for page load after challenge
                    await page.wait_for_timeout(2000)
                    break
            except:
                pass
    
    def _is_blocked_page(self, html: str) -> bool:
        """Detect if we received a blocked/error page."""
        blocked_indicators = [
            "Access denied",
            "Ray ID:",
            "Please wait while we verify",
            "Checking your browser",
            "Just a moment...",
            "Enable JavaScript and cookies"
        ]
        html_lower = html.lower()
        return any(ind.lower() in html_lower for ind in blocked_indicators)
```

### Tier 4: Manual Fallback UI

**File:** `frontend/app/onboarding/manual-entry/page.tsx` (NEW)

```typescript
/**
 * Manual ICP entry fallback when automated scraping fails.
 * User can:
 * 1. Paste website content directly
 * 2. Provide LinkedIn URL
 * 3. Skip and use basic info
 */
export default function ManualEntryPage() {
  const [entryMethod, setEntryMethod] = useState<'paste' | 'linkedin' | 'skip'>('paste');
  
  return (
    <div className="max-w-2xl mx-auto p-8">
      <h1>We couldn't automatically read your website</h1>
      <p className="text-muted-foreground">
        Your website has protection that prevents automated reading.
        Choose how you'd like to proceed:
      </p>
      
      <Tabs value={entryMethod} onValueChange={setEntryMethod}>
        <TabsList>
          <TabsTrigger value="paste">Paste Content</TabsTrigger>
          <TabsTrigger value="linkedin">Use LinkedIn</TabsTrigger>
          <TabsTrigger value="skip">Skip for Now</TabsTrigger>
        </TabsList>
        
        <TabsContent value="paste">
          <PasteContentForm />
        </TabsContent>
        
        <TabsContent value="linkedin">
          <LinkedInURLForm />
        </TabsContent>
        
        <TabsContent value="skip">
          <SkipICPForm />
        </TabsContent>
      </Tabs>
    </div>
  );
}
```

---

## Orchestrator Integration

**File:** `src/engines/icp_scraper.py`

```python
async def scrape_website(self, url: str, max_pages: int = 10) -> ScrapeResult:
    """
    Main entry point for website scraping with full waterfall.
    """
    # Tier 0: Validate and normalize URL
    validation = await self.url_validator.validate_and_normalize(url)
    if not validation.valid:
        return ScrapeResult(
            url=url,
            page_count=0,
            tier_used=0,
            needs_fallback=True,
            failure_reason=validation.error
        )
    
    url = validation.canonical_url
    
    # Tier 1 & 2: Apify waterfall
    result = await self.apify.scrape_website_with_waterfall(url, max_pages)
    if not result.needs_fallback:
        return result
    
    # Tier 3: Camoufox with residential proxy
    if self.camoufox_enabled:
        result = await self.camoufox.scrape(url)
        if not result.needs_fallback:
            return result
    
    # Tier 4: Return with manual fallback flag
    return ScrapeResult(
        url=url,
        page_count=0,
        tier_used=3 if self.camoufox_enabled else 2,
        needs_fallback=True,
        failure_reason="All automated methods failed",
        manual_fallback_url=f"/onboarding/manual-entry?url={url}"
    )
```

---

## Cost Analysis

### Per-Scrape Costs

| Tier | Cost | Time | Success Rate |
|------|------|------|--------------|
| 0: Validation | FREE | <2s | 100% (validation only) |
| 1: Cheerio | ~$0.00025 | 5-10s | ~60% |
| 2: Playwright | ~$0.0005 | 15-30s | ~80% |
| 3: Camoufox | ~$0.02-0.05 | 20-45s | ~95% |
| 4: Manual | FREE | User-dependent | 100% |

### Projected Costs for 8,000 Agencies

| Scenario | Distribution | Total Cost |
|----------|--------------|------------|
| **Optimistic** | 65% T1, 25% T2, 8% T3, 2% T4 | ~$20-30 |
| **Realistic** | 50% T1, 30% T2, 15% T3, 5% T4 | ~$40-60 |
| **Pessimistic** | 35% T1, 30% T2, 30% T3, 5% T4 | ~$80-120 |

**Conclusion:** Even worst-case is under $150 for entire target market.

---

## Infrastructure Requirements

### Railway Container Updates

```dockerfile
# Add to Dockerfile for Tier 3 support
RUN pip install camoufox[geoip] playwright
RUN python -m camoufox fetch
# Note: Adds ~300MB for Firefox binary
```

### Environment Variables

```bash
# Tier 3 Proxy Configuration
RESIDENTIAL_PROXY_HOST=proxy.webshare.io
RESIDENTIAL_PROXY_PORT=80
RESIDENTIAL_PROXY_USERNAME=xxx
RESIDENTIAL_PROXY_PASSWORD=xxx

# Feature flags
CAMOUFOX_ENABLED=true
SCRAPER_TIMEOUT_MS=45000
```

### Proxy Providers (Recommended)

| Provider | Cost | Notes |
|----------|------|-------|
| **WebShare** | $2.99/month for 10 IPs | Cheapest, good for low volume |
| **IPRoyal** | ~$1.75/GB | Pay-as-you-go, good quality |
| **Bright Data** | ~$0.10/request | Enterprise, overkill for now |

**Recommendation:** Start with WebShare ($2.99/month), upgrade if needed.

---

## Monitoring & Metrics

### Track per-tier performance

```python
# Log scrape attempts with tier info
logger.info(
    "scrape_complete",
    url=url,
    tier_used=result.tier_used,
    success=not result.needs_fallback,
    duration_ms=duration,
    content_length=len(result.raw_html)
)
```

### Dashboard Metrics

- Tier 1 success rate
- Tier 2 success rate  
- Tier 3 success rate
- Manual fallback rate
- Average scrape duration by tier
- Cost per successful scrape

---

## Implementation Phases

| Phase | Tasks | Effort | Priority |
|-------|-------|--------|----------|
| **Phase A** | Tier 0 (URL validation) + better empty detection | 2-3 hrs | P0 |
| **Phase B** | Fix Apify Tier 1/2 waterfall | 1-2 hrs | P0 |
| **Phase C** | Tier 4 manual fallback UI | 2-3 hrs | P0 |
| **Phase D** | Tier 3 Camoufox integration | 4-6 hrs | P1 |
| **Phase E** | Monitoring & metrics | 2 hrs | P2 |

**Recommended order:** A → B → C → D → E

Phases A-C give 100% coverage (with manual fallback). Phase D adds automation for protected sites.

---

## Testing

### Unit Tests

```python
# tests/test_engines/test_scraper_waterfall.py

async def test_tier0_invalid_url():
    """Tier 0 catches invalid URLs."""
    result = await scraper.scrape_website("not-a-url")
    assert result.tier_used == 0
    assert result.needs_fallback
    assert "Invalid URL" in result.failure_reason

async def test_tier1_success():
    """Tier 1 works for simple static sites."""
    result = await scraper.scrape_website("https://example.com")
    assert result.tier_used == 1
    assert not result.needs_fallback
    assert len(result.raw_html) > 500

async def test_waterfall_to_tier2():
    """Falls back to Tier 2 when Tier 1 returns empty."""
    # Mock Tier 1 to return empty
    result = await scraper.scrape_website("https://react-heavy-site.com")
    assert result.tier_used == 2
```

### E2E Test Sites

| Site | Expected Tier | Notes |
|------|---------------|-------|
| `example.com` | Tier 1 | Simple static |
| `dilate.com.au` | Tier 1 | WordPress |
| `spa-heavy-agency.com` | Tier 2 | React/Vue |
| `cloudflare-protected.com` | Tier 3 | Cloudflare |

---

## Related Documents

- `docs/specs/integrations/APIFY.md` - Apify integration details
- `docs/phases/PHASE_11_ICP.md` - ICP discovery flow
- `PROGRESS.md` - Implementation tracking
