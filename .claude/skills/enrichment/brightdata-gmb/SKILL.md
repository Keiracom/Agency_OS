# SKILL: Bright Data Google Maps (GMB Enrichment)

**Tier:** 1.5a  
**Cost:** ~$0.0015 AUD per record  
**Source:** Bright Data Web Scraper API (Google Maps Full Information)  
**Dataset ID:** `gd_m8ebnr0q2qlklc02fz`  
**Credentials Required:** `BRIGHTDATA_API_KEY`  
**Status:** ✅ Working (Web Scraper API)

---

## ⚠️ IMPORTANT — CEO Directive #035

**GMB enrichment uses Bright Data Web Scraper API, NOT SERP API.**

Per CEO Directive #035, the correct method is:
- **Dataset:** `gd_m8ebnr0q2qlklc02fz` (Google Maps full information)
- **Endpoint:** `/datasets/v3/trigger`
- **Input:** place_id or business URL

The SERP API endpoint was deprecated due to low success rate.

---

## Quick Test

```bash
cd /home/elliotbot/clawd
source .venv/bin/activate
python skills/enrichment/brightdata-gmb/test.py
```

## Prerequisites

- [x] Credential: `BRIGHTDATA_API_KEY` is set
- [x] Dataset: `gd_m8ebnr0q2qlklc02fz` (Google Maps full information)

## How to Run

```bash
# Enrich by Google Maps URL or place_id
python skills/enrichment/brightdata-gmb/run.py --url "https://maps.google.com/place/..."

# Or by place_id directly
python skills/enrichment/brightdata-gmb/run.py --place_id "ChIJ..."
```

## Input Format

| Field | Required | Description |
|-------|----------|-------------|
| `--url` | One of | Google Maps business URL |
| `--place_id` | One of | Google Place ID |

## API Call Pattern

```python
import httpx

headers = {"Authorization": f"Bearer {BRIGHTDATA_API_KEY}"}
payload = [{"url": "https://maps.google.com/place/..."}]

response = await client.post(
    "https://api.brightdata.com/datasets/v3/trigger",
    params={
        "dataset_id": "gd_m8ebnr0q2qlklc02fz",
        "include_errors": "true"
    },
    headers=headers,
    json=payload
)
snapshot_id = response.json()["snapshot_id"]
# Poll for results...
```

## Output Format

```json
{
  "name": "Agency Name",
  "address": "123 Street, Melbourne VIC 3000",
  "phone": "+61 3 1234 5678",
  "website": "https://example.com",
  "rating": 4.8,
  "reviews_count": 127,
  "category": "Marketing agency",
  "place_id": "ChIJ...",
  "hours": {...},
  "photos": [...],
  "cost_aud": 0.0015
}
```

## Error Handling

| Error | Meaning | Action |
|-------|---------|--------|
| `401 Unauthorized` | Invalid API key | Check BRIGHTDATA_API_KEY |
| `Empty result` | Place not found | Verify URL/place_id |
| `Snapshot timeout` | Processing slow | Retry after 30s |

## Governance

- **LAW II:** All costs in $AUD (~$0.0015/record)
- **Rate limits:** Per account quota
- **CEO Directive #035:** Use Web Scraper API dataset, NOT SERP
- **Source:** docs/integrations/bright-data-inventory.md
