# SKILL: Bright Data LinkedIn Enrichment

**Tier:** 1.5 - 2  
**Cost:** ~$0.0015 AUD per record  
**Source:** Bright Data Web Scraper API (LinkedIn Datasets)  
**Credentials Required:** `BRIGHTDATA_API_KEY`  
**Status:** ✅ Working (verified 2026-02-17)

---

## Dataset IDs

| Dataset | ID | Use Case | Tier |
|---------|-----|----------|------|
| LinkedIn Company | `gd_l1vikfnt1wgvvqz95w` | Company enrichment | T2 |
| LinkedIn People | `gd_l1viktl72bvl7bjuj0` | Decision maker profiles | T2.5 |
| LinkedIn Posts | `gd_lyy3tktm25m4avu764` | Social posts (T-DM2/T-DM3) | T-DM |

---

## CEO Directives Compliance

- **#040:** T-DM0 LinkedIn discovery via DataForSEO + Bright Data
- **#041:** T-DM2/T-DM3 social posts via Bright Data (dataset: `gd_lyy3tktm25m4avu764`)
- **#043:** Use `discover_by=profile_url` for LinkedIn/X posts

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

### Company Enrichment (T2)
```bash
python skills/enrichment/brightdata-linkedin/run.py --url "https://www.linkedin.com/company/mustard-creative-media"
```

### People Profile Enrichment (T2.5)
```bash
python skills/enrichment/brightdata-linkedin/run.py --profile "https://www.linkedin.com/in/johndoe"
```

### Social Posts Discovery (T-DM2/T-DM3) — CEO Directive #041, #043
```bash
# By profile URL (discover_by=profile_url per Directive #043)
python skills/enrichment/brightdata-linkedin/run.py --posts --profile-url "https://www.linkedin.com/in/johndoe"

# By company URL
python skills/enrichment/brightdata-linkedin/run.py --posts --company-url "https://www.linkedin.com/company/example"
```

## Input Format

| Field | Required | Description |
|-------|----------|-------------|
| `--url` | One of | LinkedIn company URL (company enrichment) |
| `--profile` | One of | LinkedIn profile URL (people enrichment) |
| `--posts` | Flag | Enable posts discovery mode |
| `--profile-url` | With posts | Profile URL for posts discovery |
| `--company-url` | With posts | Company URL for posts discovery |

## API Call Pattern

### Company/Profile Enrichment
```python
payload = [{"url": linkedin_url}]
response = await client.post(
    "https://api.brightdata.com/datasets/v3/trigger",
    params={"dataset_id": "gd_l1vikfnt1wgvvqz95w", "include_errors": "true"},
    headers=headers,
    json=payload
)
```

### Posts Discovery (Directive #043)
```python
# discover_by=profile_url for individual posts
payload = [{"url": profile_url}]
response = await client.post(
    "https://api.brightdata.com/datasets/v3/trigger",
    params={
        "dataset_id": "gd_lyy3tktm25m4avu764",
        "type": "discover_new",
        "discover_by": "profile_url",  # CEO Directive #043
        "include_errors": "true"
    },
    headers=headers,
    json=payload
)
```

## Output Format

### Company Enrichment
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
  "specialties": "Branding, Digital, Content...",
  "updates": [...],  // Recent company posts
  "employees": [...]  // Sample employee profiles
}
```

### Posts Discovery (T-DM2/T-DM3)
```json
{
  "posts": [
    {
      "post_url": "https://linkedin.com/posts/...",
      "text": "Post content...",
      "likes": 45,
      "comments": 12,
      "posted_date": "2026-02-15",
      "author": {...}
    }
  ]
}
```

## How It Works

1. Submit LinkedIn URL to Bright Data trigger endpoint
2. For posts: add `type=discover_new&discover_by=profile_url`
3. Receive snapshot_id (async processing)
4. Poll snapshot endpoint until ready (~3-10 seconds)
5. Return enriched data

## Error Handling

| Error | Meaning | Action |
|-------|---------|--------|
| `401 Unauthorized` | Invalid API key | Check BRIGHTDATA_API_KEY |
| `snapshot_id timeout` | Processing slow | Retry after 30s |
| `Empty result` | Profile/company not found | Verify LinkedIn URL |

## Governance

- **LAW II:** All costs in $AUD (~$0.0015/record)
- **CEO Directive #040:** T-DM0 LinkedIn discovery
- **CEO Directive #041:** T-DM2/T-DM3 social posts via Bright Data
- **CEO Directive #043:** Use `discover_by=profile_url` for posts
- **Rate limits:** Per account quota
- **Source:** docs/integrations/bright-data-inventory.md
