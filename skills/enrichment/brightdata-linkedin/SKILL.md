# SKILL: Bright Data LinkedIn Enrichment

**Tier:** 1.5 - 2
**Cost:** ~$0.0015 AUD per record
**Source:** Bright Data Web Scraper API (LinkedIn Datasets)
**Credentials Required:** `BRIGHTDATA_API_KEY`
**Status:** ✅ Working (verified 2026-02-17)

---

## At-a-Glance

**What:** Pull LinkedIn company or profile data via Bright Data's async dataset API. Replaces Proxycurl (dead reference per CLAUDE.md).

**When to use:**
- T2 Company enrichment: employee count, industry, headquarters, founded-year, follower count (CIS scoring signals)
- T2.5 People enrichment: decision-maker title, tenure, profile URL verification (F5 DM identification support)
- Profile validation: confirm a DM candidate's LinkedIn URL actually exists and matches the expected person

**When NOT to use:**
- NOT Proxycurl (dead per CLAUDE.md dead-references table)
- NOT for real-time scraping during user-facing requests (async dataset fetch, 10-60s typical)
- NOT for bulk >1000 profile sweeps without explicit budget approval
- NOT when a cheaper tier has already produced sufficient signal (GOV-8 maximum extraction — reuse upstream if available)

**Caveats:**
- Async dataset runs — poll `snapshot_id` until status=ready
- Rate-limit headroom unclear; assume 100 req/min soft
- AU-specific: profile data is global; filter downstream for AU relevance
- Profile URLs occasionally carry regional prefixes (`au.linkedin.com/in/...`) — normalise before dedup

**Returns:** dataset-specific. Company: `{name, industry, size, headquarters, founded, followers, linkedin_url}`. Profile: `{name, title, current_company, location, tenure, url}`.

## Input Parameter Constraints (poka-yoke)

- `dataset_id: enum` — must be one of the documented Dataset IDs below; reject free-text.
- `url: str` — must match LinkedIn URL regex: `^https://(www\.|au\.|)linkedin\.com/(company|in)/[a-zA-Z0-9\-_%]+/?$`. Strip query strings before submission.
- `timeout_s: int` — default 60. Do not exceed 120 (dataset stalls beyond are almost always failures).

## Response Trimming

Company: PERSIST `name, industry, size, headquarters_country, founded_year, followers_count, linkedin_url`. DROP: `description, specialties, affiliated_companies, similar_companies` (rarely used).

Profile: PERSIST `name, current_title, current_company, current_tenure_months, location, profile_url`. DROP: `skills, endorsements, recommendations, connections_count, about_section` (context bloat; fetch on demand if needed).

## Error Handling

| Error | Signal | Category | Action |
|-------|--------|----------|--------|
| Malformed URL | client-side reject | caller_error | Regex-check before API call. |
| Dataset run failed | async status=failed | transient | Retry once with same URL. |
| No match | async status=ready, empty | miss | Persist `{found: false}`. Not an error. |
| Auth failure | 401 | config_error | Route to devops-6 — `BRIGHTDATA_API_KEY`. |
| Quota exceeded | 402 | budget | Escalate to Dave. |
| Stuck ≥120s | timeout | transient | Cancel + retry once; escalate on second. |

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
