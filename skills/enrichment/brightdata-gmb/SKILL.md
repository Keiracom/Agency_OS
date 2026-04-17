# SKILL: Bright Data Google Maps (GMB Enrichment)

**Tier:** 1.5a
**Cost:** ~$0.0015 AUD per record
**Source:** Bright Data Web Scraper API (Google Maps Full Information)
**Dataset ID:** `gd_m8ebnr0q2qlklc02fz`
**Credentials Required:** `BRIGHTDATA_API_KEY`
**Status:** ✅ Working (Web Scraper API)

---

## At-a-Glance

**What:** Pull full Google My Business record for an AU SMB — name, address, phone, website, rating, review count, opening hours, photos. T1.5a in the enrichment waterfall.

**When to use:**
- Validating a discovered AU business has live GMB presence (strong signal of "real, operating SMB")
- Capturing phone/website/rating for CIS scoring and outreach routing
- Detecting red flags: 0 reviews, rating <3.0, or "Permanently closed"

**When NOT to use:**
- NOT Apify's GMB scraper (deprecated per CEO Directive #035 — use this skill, Dataset `gd_m8ebnr0q2qlklc02fz`)
- NOT the SERP API for GMB data (different dataset, stale results)
- NOT real-time API during user-facing flows (async dataset fetch, 10-60s)

**Caveats:**
- Dataset runs async — poll with `snapshot_id` until status=ready
- Reviews array can be huge (50-200 items); trim before persistence
- AU-specific: filter for `country == "Australia"` defensively — occasional bleed from `.au` domains that aren't actually AU
- ratings of `null` are legitimately rare-but-real (new listings), distinguish from API error

**Returns:** `{name, address, phone, website, rating: float|null, review_count: int, hours, category, status: enum['Operational','Permanently closed','Temporarily closed'], place_id, lat, lng}`.

## Input Parameter Constraints (poka-yoke)

- `query: str` — required. Business name + locality (e.g. `"Acme Plumbing Sydney NSW"`). Must be ≤200 chars.
- `place_id: str` — optional alternative. Must match Google place_id format `^ChIJ[A-Za-z0-9_\-]+$`. Prefer over `query` when available (deterministic).
- Never pass both `query` and `place_id` — prefer `place_id`.

## Response Trimming

PERSIST: `name, address, phone, website, rating, review_count, category, status, place_id, lat, lng, hours_summary`. DROP: full reviews array (use sentiment-extract skill for that), photos URLs (use only for card render, fetch on-demand), popular_times grid (rarely used).

## Error Handling

| Error | Signal | Category | Action |
|-------|--------|----------|--------|
| Invalid query (too short) | client-side reject | caller_error | Require ≥5 chars including locality. |
| Auth failure | 401 | config_error | Route to devops-6 — `BRIGHTDATA_API_KEY`. |
| Dataset run failed | async status=failed | transient | Retry once. If still failing, escalate. |
| No match | async status=ready, empty result | miss | Persist `{found: false, reason: no_gmb_listing}`. |
| Quota exceeded | 402 | budget | Escalate to Dave. |
| Stuck "running" >120s | timeout | transient | Cancel + retry once; escalate on second failure. |

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
