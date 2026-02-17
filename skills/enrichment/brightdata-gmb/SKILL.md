# Bright Data GMB Skill

**Purpose:** Google Maps business search via Bright Data Google Maps SERP API

## Overview

This skill provides automated Google Maps business searches using Bright Data's Google Maps SERP API. It extracts comprehensive business information including contact details, reviews, ratings, and location data for local business searches.

**This replaces the deprecated DIY GMB scraper. See Directive #020a for validation.**

## Usage

```python
from skills.enrichment.brightdata_gmb.run import gmb_search

# Search for businesses
results = await gmb_search("marketing agency Melbourne")

# Search with location specificity
results = await gmb_search("plumbers", location="Sydney NSW")
```

## Features

- **Local Business Search:** Comprehensive Google Maps business directory search
- **Location-based Queries:** Support for location-specific searches
- **Structured Data:** Normalized business information extraction
- **Review Data:** Ratings, review counts, and review snippets
- **Contact Information:** Phone, website, address details
- **Business Hours:** Operating hours and availability

## Cost

- **Rate:** $0.0015 per request (AUD)
- **Comparison:** Replaces DIY scraper at $0.006/lead - 75% cost reduction

## Output Format

```json
[
  {
    "name": "Mustard Creative",
    "title": "Digital Marketing Agency",
    "address": "123 Collins St, Melbourne VIC 3000",
    "phone": "+61 3 1234 5678",
    "website": "https://www.mustardcreative.com.au",
    "rating": 4.8,
    "reviews_count": 42,
    "category": "Marketing Agency",
    "place_id": "ChIJ...",
    "hours": "Open ⋅ Closes 5:30 PM",
    "description": "Full-service digital marketing agency specializing in..."
  }
]
```

## Environment Variables

- `BRIGHTDATA_API_KEY` - Bright Data API key (required)

## API Integration

Uses Bright Data Google Maps SERP API directly for business searches.

## Test Case

**Target:** "marketing agency Melbourne"  
**Expected:** List of marketing agencies in Melbourne with complete business details

## Replacement History

- **Replaces:** src/integrations/gmb_scraper.py (deprecated)
- **Validation:** CEO Directive #020a
- **Cost Improvement:** $0.006/lead → $0.0015/request (75% reduction)
- **Data Quality:** Improved reliability and completeness
- **Directive Chain:** #020 → #020a → #031

## Migration Notes

The tools/ directory (autonomous_browser.py, proxy_manager.py) is no longer needed for GMB searches. All Google Maps business data should now use this Bright Data integration.