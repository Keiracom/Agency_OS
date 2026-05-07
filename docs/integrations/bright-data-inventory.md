# Bright Data Platform Inventory — Agency OS SSOT

**Last Updated:** 2026-02-16T05:05 UTC  
**API Key:** 2bab0747-ede2-4437-9b6f-6a77e8f0ca3e  
**Account Status:** ✅ Active  

---

## Executive Summary

Bright Data provides 234 datasets. 35 are relevant to Agency OS B2B operations. Key discovery:

**Discovery modes ARE supported** — accessed via query parameters on trigger endpoint, NOT visible in `/datasets/list` API. The list API only returns dataset names; discovery modes are sub-endpoints accessed with `&type=discover_new&discover_by=keyword|url`.

---

## Verified Dataset IDs (Tested 2026-02-16)

| Dataset | ID | Collection Modes | Status |
|---------|-----|------------------|--------|
| LinkedIn Company | `gd_l1vikfnt1wgvvqz95w` | collect-by-URL | ✅ Tested |
| LinkedIn People Profiles | `gd_l1viktl72bvl7bjuj0` | collect-by-URL | ✅ Verified |
| LinkedIn Jobs | `gd_lpfll7v5hcqtkxl6l` | collect-by-URL, **discover-by-keyword** | ✅ Tested |

---

## Discovery Modes (Per Dave's Dashboard)

Some datasets support discovery modes beyond URL collection. These are accessed via query params:

```
POST /datasets/v3/trigger?dataset_id=XXX&type=discover_new&discover_by=keyword
```

### LinkedIn Jobs (`gd_lpfll7v5hcqtkxl6l`)
- **discover by keyword**: ✅ Tested & Working
  - Input: `{"keyword": "marketing", "location": "Melbourne", "country": "AU"}`
  - Additional filters: `time_range`, `job_type`, `experience_level`, `remote`, `company`, `location_radius`
- **discover by URL**: Standard URL collection

### LinkedIn Posts (`gd_lyy3tktm25m4avu764`)
- discover by company URL
- discover by profile URL  
- discover by URL

---

## Field Reports

### LinkedIn Company Enrichment

**Test:** `https://www.linkedin.com/company/mustard-creative-media`  
**Snapshot:** `sd_mlopftkkz9n6k9twp`  
**Records:** 1 | **Duration:** 3.97s  

**All Fields Returned:**
| Field | Type | Example |
|-------|------|---------|
| `id` | string | `mustard-creative-media` |
| `name` | string | `Mustard \| A Creative Agency` |
| `country_code` | string | `AU` |
| `locations` | array | `["61 Stephenson Street Richmond..."]` |
| `followers` | number | `10589` |
| `employees_in_linkedin` | number | `29` |
| `about` | string | Full company description |
| `specialties` | string | Comma-separated list |
| `company_size` | string | `11-50 employees` |
| `organization_type` | string | `Privately Held` |
| `industries` | string | `Advertising Services` |
| `website` | string | `https://www.mustardcreative.com.au/` |
| `founded` | number | `2002` |
| `company_id` | string | `205141` |
| `employees` | array | `[{img, link, title}]` — sample employee profiles |
| `headquarters` | string | `Richmond, Victoria` |
| `image` | string | Cover image URL |
| `logo` | string | Logo URL |
| `similar` | array | Similar companies with links |
| `url` | string | LinkedIn URL |
| `updates` | array | Recent posts with text, likes, images, videos |
| `slogan` | string | Company tagline |
| `formatted_locations` | array | Clean address strings |
| `get_directions_url` | array | Bing Maps links |
| `description` | string | Full LinkedIn description |
| `country_codes_array` | array | `["AU"]` |
| `website_simplified` | string | `mustardcreative.com.au` |
| `timestamp` | string | Collection timestamp |
| `input` | object | Original input URL |

---

### LinkedIn Jobs Discovery (by Keyword)

**Test:** keyword=`marketing`, location=`Melbourne`, country=`AU`  
**Snapshot:** `sd_mloox7r18mop2i7vt`  
**Records:** 2,879 successful | **Errors:** 104 (cancelled crawls)  

**All Fields Returned:**
| Field | Type | Example |
|-------|------|---------|
| `url` | string | Full job posting URL |
| `job_posting_id` | string | `4370375393` |
| `job_title` | string | `Digital Marketing Co-ordinator` |
| `company_name` | string | `Apartments.com.au` |
| `company_id` | string | `18436850` |
| `job_location` | string | `Abbotsford, Victoria, Australia` |
| `job_summary` | string | Full job description text |
| `job_seniority_level` | string | `Associate` |
| `job_function` | string | `Marketing` |
| `job_employment_type` | string | `Full-time` |
| `job_industries` | string | `Technology, Information and Internet...` |
| `company_url` | string | Company LinkedIn URL |
| `job_posted_time` | string | `1 week ago` |
| `job_num_applicants` | number | `177` |
| `discovery_input` | object | Original search params |
| `apply_link` | string/null | External application URL |
| `country_code` | string/null | Country code |
| `title_id` | string | Job title ID |
| `company_logo` | string | Logo URL |
| `job_posted_date` | string | ISO timestamp |
| `job_poster` | object/null | Recruiter info if available |
| `application_availability` | boolean | `true` |
| `job_description_formatted` | string | HTML formatted description |
| `base_salary` | object/null | Salary info if available |
| `salary_standards` | object/null | Salary standards |
| `is_easy_apply` | boolean | `true` |
| `timestamp` | string | Collection timestamp |

**Discovery Input Parameters:**
```json
{
  "keyword": "marketing",
  "location": "Melbourne", 
  "country": "AU",
  "time_range": "Past month",
  "job_type": "",
  "experience_level": "",
  "remote": "",
  "company": "",
  "location_radius": ""
}
```

---

## Full B2B Inventory

### LinkedIn (Core)
| Dataset ID | Name | Records | Modes |
|------------|------|---------|-------|
| `gd_l1vikfnt1wgvvqz95w` | LinkedIn company information | 55M | URL |
| `gd_l1viktl72bvl7bjuj0` | LinkedIn people profiles | 115M | URL |
| `gd_lpfll7v5hcqtkxl6l` | LinkedIn job listings | — | URL, **keyword** |
| `gd_lyy3tktm25m4avu764` | LinkedIn posts | — | URL, company, profile |
| `gd_m487ihp32jtc4ujg45` | LinkedIn profiles Jobs Listings | — | URL |

### Company Intelligence
| Dataset ID | Name | Records |
|------------|------|---------|
| `gd_l1vijqt9jfj7olije` | Crunchbase companies | 2.3M |
| `gd_m0ci4a4ivx3j5l6nx` | ZoomInfo companies | — |
| `gd_l1vilsfd1xpsndbtpr` | VentureRadar company | 325K |
| `gd_l1vilaxi10wutoage7` | Owler companies | 6.1M |
| `gd_l1vilg5a1decoahvgq` | Slintel/6sense company | 10.9M |
| `gd_m4ijiqfp2n9oe3oluj` | PitchBook companies | — |

### Business Directories
| Dataset ID | Name | Records |
|------------|------|---------|
| `gd_m8ebnr0q2qlklc02fz` | Google Maps full information | — |
| `gd_luzfs1dn2oa0teb81` | Google Maps reviews | — |
| `gd_lgugwl0519h1p14rwk` | Yelp businesses overview | — |
| `gd_lgzhlu9323u3k24jkv` | Yelp businesses reviews | — |
| `gd_l1vil1d81g0u8763b2` | Manta businesses | 5.6M |

### Job Sites
| Dataset ID | Name | Records |
|------------|------|---------|
| `gd_l4dx9j9sscpvs7no2` | Indeed job listings | 7.4M |
| `gd_l7qekxkv2i7ve6hx1s` | Indeed companies info | — |
| `gd_lpfbbndm1xnopbrcr0` | Glassdoor job listings | — |
| `gd_l7j1po0921hbu0ri1z` | Glassdoor companies reviews | 2.5M |
| `gd_l7j0bx501ockwldaqf` | Glassdoor companies overview | 2.5M |

### Professional Networks
| Dataset ID | Name | Records |
|------------|------|---------|
| `gd_l3lh4ev31oqrvvblv6` | Xing social network | 8M |
| `gd_lwxkxvnf1cynvib9co` | X (Twitter) Posts | — |
| `gd_lwxmeb2u1cniijd7t4` | X (Twitter) Profiles | — |

### SaaS/Tech
| Dataset ID | Name | Records |
|------------|------|---------|
| `gd_l88xvdka1uao86xvlb` | G2 software reviews | 132K |
| `gd_l88xp4k01qnhvyqlvw` | G2 software overview | 132K |
| `gd_lztojazw1389985ops` | TrustRadius product reviews | — |

---

## API Reference

### Trigger Collection (by URL)
```bash
curl -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '[{"url": "https://linkedin.com/company/..."}]' \
  "https://api.brightdata.com/datasets/v3/trigger?dataset_id=XXX&include_errors=true"
```

### Trigger Discovery (by keyword)
```bash
curl -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '[{"keyword": "...", "location": "...", "country": "XX"}]' \
  "https://api.brightdata.com/datasets/v3/trigger?dataset_id=XXX&type=discover_new&discover_by=keyword&include_errors=true"
```

### Check Progress
```bash
curl -H "Authorization: Bearer $API_KEY" \
  "https://api.brightdata.com/datasets/v3/progress/$SNAPSHOT_ID"
```

### Download Results
```bash
curl -H "Authorization: Bearer $API_KEY" \
  "https://api.brightdata.com/datasets/v3/snapshot/$SNAPSHOT_ID?format=json"
```

---

## Contradictions Resolved (Directive #020d)

| Issue | Resolution |
|-------|------------|
| "All datasets URL-only" | **WRONG.** Discovery modes exist but are accessed via query params, not visible in `/datasets/list` |
| "Account not active" | **Transient error.** Account IS active. Triggers work. |
| "Jobs requires URLs" | **WRONG.** Jobs supports `discover_by=keyword` with keyword/location/country inputs |

---

## Siege Waterfall v2 Architecture (Directive #023)

### Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           PHASE 1: DISCOVERY                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   Mode A (ABN-First)          Mode B (Maps-First)       Mode C (Parallel)   │
│   ─────────────────           ─────────────────         ────────────────    │
│   Campaign Config             Campaign Config           Both modes          │
│         ↓                           ↓                   run together        │
│   ABN API Search              SERP Google Maps          Deduplicate on      │
│   (FREE)                      ($0.0015/req)             ABN + fuzzy name    │
│         ↓                           ↓                                       │
│   Hard Filters:               ABN Lookup                                    │
│   - Active only               (reverse verify)                              │
│   - No trusts/funds                                                         │
│   - GST registered                                                          │
│         ↓                           ↓                                       │
│   Qualified ABN Records       GMB Data + ABN                                │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                          PHASE 2: ENRICHMENT                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   Tier 1: ABN API ──────────────────────────────────────────── FREE         │
│   └── Entity data, ASIC names, GST, state                                   │
│                              │                                              │
│   Tier 1.5a: SERP Maps ─────┼───────────────────────────── $0.0015/req      │
│   └── Phone, website, address, rating, reviews                              │
│                              │                                              │
│   Tier 1.5b: SERP LinkedIn ─┼───────────────────────────── $0.0015/req      │
│   └── site:linkedin.com/company "{name}" {location}                         │
│   └── Returns LinkedIn company URL                                          │
│                              │                                              │
│   Tier 2: LinkedIn Company ─┼───────────────────────────── $0.0015/rec      │
│   └── Dataset: gd_l1vikfnt1wgvvqz95w                                        │
│   └── Returns: employees[], updates[], industry, size                       │
│                              │                                              │
│                     ════════════════════════════                            │
│                     ║  PRE-ALS GATE: Score ≥ 30 ║                           │
│                     ════════════════════════════                            │
│                              │                                              │
│   Tier 2.5: LinkedIn Profile ┼──────────────────────────── $0.0015/rec      │
│   └── Dataset: gd_l1viktl72bvl7bjuj0                                        │
│   └── Decision maker enrichment from Tier 2 employees[]                     │
│                              │                                              │
│   Tier 3: Hunter.io ────────┼───────────────────────────── $0.012/rec       │
│   └── Domain → verified email                                               │
│                              │                                              │
│                     ════════════════════════════                            │
│                     ║  HOT GATE: ALS ≥ 85        ║                          │
│                     ════════════════════════════                            │
│                              │                                              │
│   Tier 5: Kaspr ────────────┴───────────────────────────── $0.45/rec        │
│   └── Direct mobile + personal email (HOT leads only)                       │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           PHASE 3: SCORING (ALS)                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   Component        Points    New Data Source            Signal              │
│   ─────────────────────────────────────────────────────────────────────     │
│   Company Fit        25      LinkedIn industries,       Industry match,     │
│                              company_size, specialties  employee count      │
│                                                                             │
│   Authority          25      LinkedIn employees[]       Owner/CEO/Director  │
│                              → title matching           identification      │
│                                                                             │
│   Timing             15      LinkedIn updates[]         "#hiring" in posts  │
│                              → hiring posts             = active growth     │
│                                                                             │
│   Data Quality       20      Multiple verified sources  More tiers = higher │
│                                                                             │
│   Engagement         15      Email opens, replies       Existing signals    │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Cost Model (AUD per lead)

| Tier | Hot (≥85) | Warm (60-84) | Cool (35-59) | Cold (30-34) |
|------|-----------|--------------|--------------|--------------|
| ABN API | $0.000 | $0.000 | $0.000 | $0.000 |
| SERP Maps | $0.0015 | $0.0015 | $0.0015 | $0.0015 |
| SERP LinkedIn | $0.0015 | $0.0015 | $0.0015 | $0.0015 |
| LinkedIn Company | $0.0015 | $0.0015 | $0.0015 | $0.0015 |
| LinkedIn Profile | $0.0015 | $0.0015 | $0.0015 | $0.0015 |
| Hunter.io | $0.012 | $0.012 | $0.012 | $0.012 |
| Kaspr | $0.45 | — | — | — |
| **Total** | **$0.468** | **$0.018** | **$0.018** | **$0.018** |

### Key Constants

```python
DATASET_IDS = {
    "linkedin_company": "gd_l1vikfnt1wgvvqz95w",
    "linkedin_people": "gd_l1viktl72bvl7bjuj0", 
    "linkedin_jobs": "gd_lpfll7v5hcqtkxl6l"
}

SERP_ZONE = "serp_api1"
PRE_ALS_GATE = 30
HOT_THRESHOLD = 85
```

### Files

| File | Purpose |
|------|---------|
| `src/integrations/bright_data_client.py` | Unified SERP + Scrapers API client |
| `src/pipeline/discovery_modes.py` | Mode A/B/C discovery logic |
| `src/pipeline/waterfall_v2.py` | Full Phase 1→2→3 pipeline |

---

**Document Status:** SSOT Verified  
**Last Test:** 2026-02-16T05:05 UTC  
**Architecture:** Directive #023 (2026-02-16)
