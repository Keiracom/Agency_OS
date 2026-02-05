# Sydney Digital Marketing Agency Scraper

A comprehensive scraper for collecting digital marketing and SEO agency data from Sydney, Australia.

## Overview

This tool scrapes agency information from multiple directory sources:
- **Yellow Pages Australia** - Australian business directory
- **Clutch.co** - B2B ratings and reviews platform
- **DesignRush** - Agency marketplace
- **GoodFirms** - IT services directory

## Requirements

- Python 3.10+
- Virtual environment with dependencies:
  - `playwright` (with Chromium installed)
  - `fake-useragent`

## Usage

### Activate Environment
```bash
cd /home/elliotbot/clawd
source venv/bin/activate
```

### Basic Commands

```bash
# Scrape all sources
python tools/sydney_agency_scraper.py scrape --source all

# Scrape specific source
python tools/sydney_agency_scraper.py scrape --source clutch
python tools/sydney_agency_scraper.py scrape --source yellowpages
python tools/sydney_agency_scraper.py scrape --source designrush
python tools/sydney_agency_scraper.py scrape --source goodfirms

# Multiple sources
python tools/sydney_agency_scraper.py scrape -s clutch -s yellowpages

# Custom output file
python tools/sydney_agency_scraper.py scrape --source all --output my_agencies.csv
python tools/sydney_agency_scraper.py scrape --source all --output my_agencies.json

# Limit pages per source
python tools/sydney_agency_scraper.py scrape --source all --max-pages 3

# Output format control
python tools/sydney_agency_scraper.py scrape --source all --csv-only
python tools/sydney_agency_scraper.py scrape --source all --json-only

# List available sources
python tools/sydney_agency_scraper.py sources

# Quick test (1 page only)
python tools/sydney_agency_scraper.py test --source clutch
```

## Output

### CSV Format
Output fields:
- `name` - Business name
- `website` - Company website URL
- `phone` - Phone number (Australian format)
- `email` - Email address (if visible)
- `address` - Physical address
- `services` - Comma-separated list of services
- `google_rating` - Rating (0-5 scale)
- `google_reviews_count` - Number of reviews
- `source` - Data source (yellowpages, clutch, etc.)
- `source_url` - URL where data was scraped
- `scraped_at` - ISO timestamp

### JSON Format
```json
{
  "scraped_at": "2024-02-03T10:30:00Z",
  "total_agencies": 150,
  "sources": ["yellowpages", "clutch"],
  "agencies": [
    {
      "name": "Example Agency",
      "website": "https://example.com",
      "phone": "02 1234 5678",
      "services": ["SEO", "PPC", "Content Marketing"],
      ...
    }
  ]
}
```

### Default Output Location
```
data/scraped_agencies/sydney_agencies_YYYYMMDD_HHMMSS.csv
data/scraped_agencies/sydney_agencies_YYYYMMDD_HHMMSS.json
```

## Features

### Stealth Mode
Uses the Autonomous Stealth Browser with:
- **Proxy rotation** - 215,000+ residential proxies (Webshare)
- **User-Agent spoofing** - Randomized browser fingerprints
- **Burner Protocol** - Auto-retry with new identity on blocks (403/429/503)
- **Anti-detection** - webdriver flag spoofing, chrome.runtime injection

### Rate Limiting
- Minimum 2-5 second delay between requests (randomized)
- 3 second delay between pagination
- Respects site rate limits

### Deduplication
- Cross-source deduplication based on name + address
- Merges data from duplicate listings (prefers non-empty values)

## Configuration

Edit constants in `sydney_agency_scraper.py`:

```python
# Rate limiting
MIN_DELAY_SECONDS = 2.0
MAX_DELAY_SECONDS = 5.0
PAGE_DELAY_SECONDS = 3.0

# Pagination limits
MAX_PAGES_PER_SOURCE = 10
MAX_RESULTS_PER_SOURCE = 200
```

## Scraping Hierarchy

Per TOOLS.md guidelines, the scraper follows this priority:
1. **JSON/API endpoints** - Not available for these sources
2. **RSS feeds** - Not available
3. **Lite/mobile versions** - Not available
4. **Full browser automation** - Used with stealth mode ✓

## Troubleshooting

### "Playwright not installed"
```bash
source venv/bin/activate
pip install playwright
playwright install chromium
```

### Too many 403 errors
- The proxy pool may need refreshing:
```bash
python tools/proxy_manager.py sync --force
python tools/proxy_manager.py test --count 5
```

### Slow scraping
- Browser automation is inherently slower than API calls
- Each page may take 10-40 seconds with retries
- Consider reducing `MAX_PAGES_PER_SOURCE`

### Empty results
- Some sources may have enhanced bot protection
- Try again later or reduce request frequency
- Check if site structure has changed

## Extending

### Add New Source

1. Create new scraper class:
```python
class NewSourceScraper(BaseScraper):
    source_name = "newsource"
    base_url = "https://newsource.com"
    
    async def scrape(self, max_pages: int) -> List[Agency]:
        # Implementation
        pass
    
    def _parse_listings(self, content: str, source_url: str) -> int:
        # Parse HTML content
        pass
```

2. Register in orchestrator:
```python
class SydneyAgencyScraper:
    SCRAPERS = {
        # ... existing
        "newsource": NewSourceScraper,
    }
```

## Compliance Notes

- Scraper uses respectful delays and rate limiting
- Follows robots.txt guidelines where practical
- Data is for business research purposes
- No authentication bypass or login scraping
- Consider source Terms of Service before commercial use
