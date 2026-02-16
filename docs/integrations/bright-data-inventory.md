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

**Document Status:** SSOT Verified  
**Last Test:** 2026-02-16T05:05 UTC
