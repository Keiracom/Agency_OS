# SKILL: Bright Data LinkedIn Company Enrichment

**Tier:** 1.5  
**Cost:** ~$0.01 AUD per lookup  
**Source:** Bright Data LinkedIn Company Dataset  
**Dataset ID:** `gd_l1vikfnt1wgvvqz95w`  
**Credentials Required:** `BRIGHTDATA_API_KEY`  
**Status:** ✅ Working (verified 2026-02-17)

---

## Quick Test

```bash
cd /home/elliotbot/clawd
source .venv/bin/activate
python skills/enrichment/brightdata-linkedin/test.py
```

## Prerequisites

- [x] Credential: `BRIGHTDATA_API_KEY` is set
- [x] API endpoint: https://api.brightdata.com/datasets/v3/trigger

## How to Run

```bash
# Enrich by LinkedIn company URL
python skills/enrichment/brightdata-linkedin/run.py --url "https://www.linkedin.com/company/mustard-creative-media"
```

## Input Format

| Field | Required | Description |
|-------|----------|-------------|
| `--url` | Yes | LinkedIn company URL |

## Output Format

```json
{
  "name": "Mustard | A Creative Agency",
  "industries": "Advertising Services",
  "website": "https://www.mustardcreative.com.au/",
  "employees_in_linkedin": 29,
  "headquarters": "Richmond, Victoria",
  "company_size": "11-50 employees",
  "founded": 2002,
  "about": "Full company description...",
  "specialties": "Branding, Digital, Content..."
}
```

## How It Works

1. Submit LinkedIn URL to Bright Data trigger endpoint
2. Receive snapshot_id (async processing)
3. Poll snapshot endpoint until ready (~3-10 seconds)
4. Return enriched company data

## Error Handling

| Error | Meaning | Action |
|-------|---------|--------|
| `401 Unauthorized` | Invalid API key | Check BRIGHTDATA_API_KEY |
| `snapshot_id timeout` | Processing slow | Retry after 30s |
| `Empty result` | Company not found | Verify LinkedIn URL |

## Governance

- **LAW II:** All costs in $AUD (~$0.01/lookup)
- **Rate limits:** Per account quota
- **Source:** https://brightdata.com/products/datasets
- **Dataset docs:** See docs/integrations/bright-data-inventory.md
