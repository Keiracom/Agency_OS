# SKILL: Bright Data Google Maps SERP (GMB Replacement)

**Tier:** 2  
**Cost:** $0.0015 AUD per request  
**Source:** Bright Data SERP API (Google Maps)  
**Zone:** `serp_api1`  
**Credentials Required:** `BRIGHTDATA_API_KEY`  
**Status:** ✅ Working (validated Directive #020a, 2026-02-16)

---

## ⚠️ IMPORTANT

**This replaces the deprecated DIY GMB scraper.**

The original `src/integrations/gmb_scraper.py` has been deprecated as of CEO Directive #031. See Directive #020a for validation testing.

**Cost comparison:**
- DIY scraper: $0.006/lead (proxy + browser automation)
- Bright Data SERP: $0.0015/request = **75% cost reduction**

**Quality improvement:**
- Bright Data returns: email, phone, website, social media, reviews
- DIY scraper: phone, website, hours only

---

## Quick Test

```bash
cd /home/elliotbot/clawd
source .venv/bin/activate
python skills/enrichment/brightdata-gmb/test.py
```

## Prerequisites

- [x] Credential: `BRIGHTDATA_API_KEY` is set
- [x] SERP zone: `serp_api1` configured

## How to Run

```bash
# Search Google Maps for businesses
python skills/enrichment/brightdata-gmb/run.py --query "marketing agency Melbourne"

# With location specificity
python skills/enrichment/brightdata-gmb/run.py --query "plumber" --location "Sydney NSW"
```

## Input Format

| Field | Required | Description |
|-------|----------|-------------|
| `--query` | Yes | Business type/name to search |
| `--location` | No | Location (city, state, or postcode) |
| `--limit` | No | Max results (default: 5) |

## Output Format

```json
{
  "results": [
    {
      "title": "Agency Name",
      "address": "123 Street, Melbourne VIC",
      "phone": "+61 3 1234 5678",
      "website": "https://example.com",
      "rating": 4.8,
      "reviews_count": 127,
      "category": "Marketing agency",
      "email": "info@example.com",
      "social_media": {
        "facebook": "...",
        "instagram": "..."
      }
    }
  ],
  "total_results": 20,
  "cost_aud": 0.0015
}
```

## Error Handling

| Error | Meaning | Action |
|-------|---------|--------|
| `401 Unauthorized` | Invalid API key | Check BRIGHTDATA_API_KEY |
| `No results` | Query too specific | Broaden search terms |
| `Rate limited` | Too many requests | Wait and retry |

## Governance

- **LAW II:** All costs in $AUD ($0.0015/request)
- **Rate limits:** Per account quota
- **Directive chain:** #020 → #020a → #031
- **Source:** docs/integrations/bright-data-inventory.md
