# Scraper Waterfall — Agency OS

**Purpose:** Multi-tier web scraping system with intelligent fallback for ICP extraction and data collection.
**Status:** IMPLEMENTED
**Last Updated:** 2026-01-21

---

## Overview

The Scraper Waterfall is a tiered web scraping architecture designed to maximize success rate while minimizing cost. It progressively escalates from fast/cheap methods to slower/more expensive methods only when needed.

### Why a Tiered Approach?

1. **Cost Efficiency:** Most websites (~60%) can be scraped with static HTML parsing (Cheerio) at minimal cost. Only protected sites require expensive anti-detection tools.

2. **Speed Optimization:** Cheerio processes pages in seconds; Playwright takes 5-10x longer; Camoufox takes 20-45 seconds. Starting simple reduces average scrape time.

3. **Success Rate Maximization:** By trying multiple methods, overall success rate reaches ~95% instead of ~60% with a single method.

4. **Resource Conservation:** Residential proxies and anti-detect browsers are limited resources. Using them only when needed extends their effectiveness.

---

## Code Locations

| Component | File | Purpose |
|-----------|------|---------|
| **URL Validation (Tier 0)** | `src/engines/url_validator.py` | Validates URLs before scraping |
| **URL Validation Model** | `src/models/url_validation.py` | Pydantic model for validation results |
| **Apify Integration (Tier 1-2)** | `src/integrations/apify.py` | Cheerio and Playwright scraping |
| **Camoufox Scraper (Tier 3)** | `src/integrations/camoufox_scraper.py` | Anti-detection browser scraping |
| **ICP Scraper Engine** | `src/engines/icp_scraper.py` | Orchestrates waterfall and combines results |

---

## Tier Architecture

### Tier 0: URL Validation

**File:** `src/engines/url_validator.py`

**Purpose:** Pre-flight validation before any scraping begins.

**Checks Performed:**
1. URL format validation (protocol, domain structure)
2. DNS resolution (does domain exist?)
3. HTTP accessibility (can we reach it?)
4. Redirect following (track www/non-www redirects)
5. Parked domain detection

**Cost:** FREE | **Time:** <2s | **Success Rate:** 100% (validation only)

**Parked Domain Detection:**
- Known parking hosts: `sedoparking.com`, `parking.godaddy.com`, `dan.com`, `afternic.com`, `hugedomains.com`
- Content indicators: "this domain is for sale", "domain parking", "buy this domain", "make an offer"

**Result Model (URLValidationResult):**
```python
class URLValidationResult(BaseModel):
    valid: bool                    # Is URL reachable and valid?
    canonical_url: Optional[str]   # Final URL after redirects
    redirected: bool               # Did URL redirect?
    redirect_chain: list[str]      # All URLs in redirect path
    error: Optional[str]           # Error message if failed
    error_type: Optional[str]      # dns_failure, timeout, ssl_error, parked_domain, invalid_format
    status_code: Optional[int]     # HTTP status code
    is_parked: bool                # Is this a parked/for-sale domain?
    domain: Optional[str]          # Extracted domain
```

---

### Tier 1: Cheerio (Static HTML)

**File:** `src/integrations/apify.py` - `_scrape_cheerio()` method

**Purpose:** Fast parsing of static HTML content.

**When It Works:**
- Simple HTML websites
- Server-rendered pages
- Blogs and content sites
- Older websites

**When It Fails:**
- React/Vue/Angular SPAs
- JavaScript-heavy portfolio pages
- Sites with lazy loading
- Cloudflare-protected sites

**Cost:** ~$0.005/page | **Time:** 2-5s | **Success Rate:** ~60%

**Features:**
- Uses seed URLs to crawl common agency paths (`/case-studies`, `/testimonials`, `/portfolio`)
- Canonicalizes URLs to handle www/non-www redirects
- Saves both HTML and Markdown output

**Seed URL Paths:**
```python
AGENCY_SEED_PATHS = [
    "/about", "/about-us", "/case-studies", "/case-study",
    "/testimonials", "/reviews", "/our-work", "/work",
    "/portfolio", "/clients", "/our-clients", "/services",
]
```

---

### Tier 2: Playwright (JS Rendering)

**File:** `src/integrations/apify.py` - `_scrape_playwright()` method

**Purpose:** Full browser rendering for JavaScript-heavy sites.

**When It Works:**
- Single-page applications (React, Vue, Angular)
- Sites with client-side rendering
- Pages with lazy loading
- Interactive portfolios

**When It Fails:**
- Cloudflare Turnstile
- Aggressive bot detection
- Sites requiring CAPTCHA
- IP-reputation-based blocking

**Cost:** ~$0.02/page | **Time:** 10-30s | **Success Rate:** ~80%

**Features:**
- Full JavaScript execution
- Extended page load timeout (45s)
- Retry on failure (2 attempts)
- Uses same seed URLs as Cheerio

**Configuration:**
```python
run_input = {
    "startUrls": seed_urls,
    "maxCrawlPages": max_pages,
    "crawlerType": "playwright",
    "requestTimeoutSecs": 60,
    "saveHtml": True,
    "saveMarkdown": True,
    "pageLoadTimeoutSecs": 45,
    "maxRequestRetries": 2,
}
```

---

### Tier 3: Camoufox (Anti-Detection)

**File:** `src/integrations/camoufox_scraper.py`

**Purpose:** Bypass bot detection using anti-fingerprint browser.

**When It Works:**
- Cloudflare-protected sites
- Sites with browser fingerprinting
- Aggressive bot detection
- Rate-limited APIs

**When It Fails:**
- CAPTCHA (requires human)
- Sites behind login walls
- Geo-restricted content (without proper proxy location)

**Cost:** ~$0.02-0.05/page | **Time:** 20-45s | **Success Rate:** ~95%

**Features:**
- Firefox-based anti-detect browser
- Residential proxy support for IP reputation
- Cloudflare challenge waiting
- Human-like browser fingerprints

**Cloudflare Challenge Detection:**
```python
cloudflare_selectors = [
    "#challenge-running",
    "#challenge-stage",
    ".cf-browser-verification",
    "#cf-challenge-running",
    ".cf-im-under-attack",
    "#trk_jschal_js",
]
```

**Requirements:**
- Package: `pip install camoufox[geoip]`
- Residential proxy for best results (optional but recommended)

**Proxy Configuration:**
```python
CamoufoxScraper(
    proxy_host="proxy.example.com",
    proxy_port=8080,
    proxy_username="user",
    proxy_password="pass",
)
```

---

### Tier 4: Manual Fallback

**Status:** UI PLACEHOLDER

**Purpose:** Human-assisted data entry when all automated methods fail.

When all tiers fail, the system returns:
```python
manual_fallback_url = f"/onboarding/manual-entry?url={url}"
```

The frontend should display a manual entry form where users can:
- Paste text content from the website
- Upload screenshots
- Manually enter company/portfolio information

---

## Fallback Logic

### When to Advance Tiers

```
Tier 0 (URL Validation)
  |
  |-- Invalid format? --> FAIL (bad URL)
  |-- DNS fails? --> FAIL (domain doesn't exist)
  |-- Parked domain? --> FAIL (domain for sale)
  |-- Valid --> Continue
  v
Tier 1 (Cheerio)
  |
  |-- Content < 500 chars? --> Tier 2
  |-- Blocked content detected? --> Tier 2
  |-- No portfolio indicators? --> Tier 2
  |-- Success --> RETURN
  v
Tier 2 (Playwright)
  |
  |-- Content < 500 chars? --> Tier 3
  |-- Blocked content detected? --> Tier 3
  |-- Success --> RETURN
  v
Tier 3 (Camoufox)
  |
  |-- Content < 500 chars? --> Tier 4
  |-- Blocked content detected? --> Tier 4
  |-- Success --> RETURN
  v
Tier 4 (Manual Fallback)
  --> Return manual_fallback_url
```

### Implementation in Code

```python
# In icp_scraper.py - scrape_website()
async def scrape_website(self, url: str, max_pages: int = 15):
    # Tier 0: URL Validation
    validation = await self.url_validator.validate_and_normalize(url)
    if not validation.valid:
        return EngineResult.ok(data=ScrapedWebsite(
            needs_fallback=True,
            failure_reason=validation.error,
        ))

    # Tier 1 & 2: Apify Waterfall
    scrape_result = await self.apify.scrape_website_with_waterfall(url)

    if scrape_result.needs_fallback:
        # Would continue to Tier 3/4 here
        return EngineResult.ok(data=ScrapedWebsite(
            needs_fallback=True,
            manual_fallback_url=f"/onboarding/manual-entry?url={url}",
        ))

    return EngineResult.ok(data=scraped)
```

---

## Blocked Content Detection

The system identifies blocked/empty pages using these indicators:

```python
BLOCKED_CONTENT_INDICATORS = [
    "access denied",
    "ray id:",                        # Cloudflare
    "please wait while we verify",    # Challenge page
    "checking your browser",          # Challenge page
    "just a moment...",               # Cloudflare
    "enable javascript and cookies",  # Bot wall
    "cloudflare",                     # Direct mention
    "attention required",             # Cloudflare
    "please complete the security check",
    "bot protection",
    "captcha",
]
```

**Detection Logic:**
- If 2+ indicators found in page content --> Content is BLOCKED
- If content length < 500 chars --> Content is EMPTY/BLOCKED

---

## Cost Comparison

| Tier | Cost per Page | Time | Success Rate | Use Case |
|------|---------------|------|--------------|----------|
| **0: Validation** | FREE | <2s | 100% | Pre-flight checks |
| **1: Cheerio** | ~$0.005 | 2-5s | ~60% | Static HTML sites |
| **2: Playwright** | ~$0.02 | 10-30s | ~80% | JS-rendered sites |
| **3: Camoufox** | ~$0.05 | 20-45s | ~95% | Protected sites |
| **4: Manual** | N/A | Human time | 100% | Last resort |

### Cost Optimization Strategy

Assuming 100 websites to scrape:
- ~60 succeed at Tier 1 (Cheerio): 60 x $0.005 = $0.30
- ~32 need Tier 2 (Playwright): 32 x $0.02 = $0.64
- ~6 need Tier 3 (Camoufox): 6 x $0.05 = $0.30
- ~2 need Tier 4 (Manual): 2 x $0 = $0.00

**Total: ~$1.24 for 100 websites**

vs. using Camoufox for all: 100 x $0.05 = **$5.00**

---

## Key Rules

1. **Always start at Tier 0.** Never skip URL validation - it prevents wasted API calls on bad URLs.

2. **Check for portfolio indicators before declaring success.** Cheerio may return valid HTML that lacks the portfolio data needed for ICP extraction.

3. **Canonicalize URLs before building seed URLs.** Many sites redirect www to non-www or vice versa, causing duplicate crawling.

4. **Track which tier succeeded.** The `tier_used` field helps analyze scraping effectiveness and optimize costs.

5. **Never retry the same tier.** If Cheerio fails, don't retry Cheerio - advance to Playwright.

6. **Camoufox requires residential proxy for best results.** Datacenter IPs have poor reputation with bot detection systems.

7. **Set reasonable timeouts.** Cheerio: 30s, Playwright: 60s, Camoufox: 45s.

8. **Combine scraper output with direct fetch.** The ICP scraper also directly fetches known portfolio paths via httpx to supplement Apify results.

---

## Configuration

### Environment Variables

```bash
# Apify (Tier 1-2)
APIFY_API_KEY=apify_api_xxx

# Residential Proxy (Tier 3 - Optional)
RESIDENTIAL_PROXY_HOST=proxy.example.com
RESIDENTIAL_PROXY_PORT=8080
RESIDENTIAL_PROXY_USERNAME=user
RESIDENTIAL_PROXY_PASSWORD=pass
```

### Settings Integration

```python
# src/config/settings.py
class Settings:
    apify_api_key: str
    residential_proxy_host: Optional[str] = None
    residential_proxy_port: Optional[int] = None
    residential_proxy_username: Optional[str] = None
    residential_proxy_password: Optional[str] = None
```

### Availability Checks

```python
from src.integrations.camoufox_scraper import is_camoufox_available, is_camoufox_configured

# Check if Camoufox package is installed
if is_camoufox_available():
    print("Camoufox installed")

# Check if proxy is configured
if is_camoufox_configured():
    print("Tier 3 fully operational")
```

---

## Cross-References

| Related Doc | Purpose |
|-------------|---------|
| [`../flows/ONBOARDING_FLOW.md`](../flows/ONBOARDING_FLOW.md) | Uses scraper for ICP extraction |
| [`../../specs/engines/ICP_SCRAPER_ENGINE.md`](../../specs/engines/ICP_SCRAPER_ENGINE.md) | Full engine specification |
| [`../../specs/integrations/APIFY.md`](../../specs/integrations/APIFY.md) | Apify integration details |
| [`../TODO.md`](../TODO.md) | Implementation gaps |

---

For gaps and implementation status, see [`../TODO.md`](../TODO.md).
