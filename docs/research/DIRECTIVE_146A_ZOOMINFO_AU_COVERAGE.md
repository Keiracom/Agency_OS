# DIRECTIVE #146 PART A — ZoomInfo AU Coverage Test Results

**Date:** 2026-03-01  
**Dataset:** Bright Data ZoomInfo Companies (`gd_m0ci4a4ivx3j5l6nx`)  
**Scope:** Australian Marketing/Advertising Agencies  

---

## Executive Summary

### ⚠️ CRITICAL LIMITATION DISCOVERED

**ZoomInfo via Bright Data does NOT support discovery/search.** It only works with **exact ZoomInfo company page URLs**. This creates a major operational blocker:

1. **No discover-by-name** — Can't query "Thinkerbell Melbourne"
2. **No discover-by-location** — Can't query "marketing agencies Australia"  
3. **No discover-by-industry** — Search URLs return `dead_page` errors
4. **Must have ZoomInfo company ID** — e.g., `https://www.zoominfo.com/c/clemenger-bbdo/11338759`

### Workaround Required
To use ZoomInfo, we'd need a **two-step process**:
1. Google SERP: `site:zoominfo.com "{company name}"` → Get ZoomInfo URL
2. Bright Data ZoomInfo scraper: Fetch company details from URL

**Cost impact:** +$0.0015/lead for ZoomInfo URL discovery via SERP

---

## Test Results

### Companies Queried: 5
### Companies Found: 1 (20% hit rate on known URLs)

| Company | ZoomInfo ID | Result | Revenue | Employees | Phone |
|---------|-------------|--------|---------|-----------|-------|
| Clemenger BBDO | 11338759 | ✅ SUCCESS | $119M USD | 201-500 | +61 279083008 |
| Clemenger Group Ltd | 1155585405 | ❌ dead_page | — | — | — |
| Ogilvy | 47882 | ❌ dead_page | — | — | — |
| DDB Worldwide | 55648 | ❌ dead_page | — | — | — |
| TBWA Worldwide | 166093 | ❌ dead_page | — | — | — |

**Note:** "dead_page" errors indicate ZoomInfo may have changed company IDs, pages were merged, or content is gated.

---

## Clemenger BBDO Full Record Analysis

### Key Fields Retrieved

| Field | Value | Available in LinkedIn T1.5? |
|-------|-------|---------------------------|
| **Revenue (Exact)** | $119,000,000 USD | ❌ NO |
| **Revenue Text** | "$119 Million" | ❌ NO |
| **Phone Number** | +61 279083008 | ❌ NO |
| **Employee Count** | 201-500 | ✅ Yes (company_size) |
| **C-Level Count** | 5 | ❌ NO |
| **Director Count** | 122 | ❌ NO |
| **Manager Count** | 45 | ❌ NO |
| **Total Contacts** | 237 | ❌ NO |
| **Industry** | Advertising Networks, Business Services | ✅ Yes |
| **Headquarters** | 474 St Kilda Rd L 3, Melbourne, VIC 3004, AU | ✅ Yes (locations) |
| **Website** | clemengerbbdo.com.au | ✅ Yes |
| **LinkedIn URL** | ✅ Included | ✅ Yes (source) |
| **SIC/NAICS Codes** | 73,731 / 54,541 | ❌ NO |
| **Tech Stack** | Gupy, Zingfit, WordPress, Drupal | ❌ NO |
| **Similar Companies** | 6 competitors with revenue estimates | ❌ NO |
| **Recent Scoops** | Executive moves, departures | ❌ NO |
| **News Coverage** | 5 recent articles | ❌ NO |

### Leadership Data

| Name | Title | ZoomInfo Profile |
|------|-------|------------------|
| Lee Leggett | Chief Executive Officer | ✅ |
| Caitlin Burgess | CFO & COO | ✅ |
| Rowan Darling | Chief Financial Officer | ✅ |
| Alisha Vaissiere | Director, Digital Strategy | ✅ |
| Jeff Clark | Director, Strategic Planning | ✅ |
| Ant Phillips | Executive Creative Director | ✅ |
| James Greaney | Chief Data Officer | ✅ |

### Recent Scoops (Executive Intelligence)
1. Simon Wassef, Chief Strategy & Experience Officer → Left to join M&C Saatchi (Jan 2026)
2. Mark Gretton, Chief Technology Officer → Left company
3. Clemenger BBDO + CHEP Network + Traffik merged under Clemenger BBDO banner

### Similar Companies (with Revenue Estimates)

| Company | Employees | Revenue |
|---------|-----------|---------|
| UrsaClemenger | 15,000 | $461.2M |
| Animal Logic | 501-1000 | $175.8M |
| McCANN Australia | 51-200 | $73.6M |
| MCN Holdings | 501-1000 | $67.5M |
| 303 MullenLowe | 51-200 | $34.3M |
| Clemenger Tasmania | 11-50 | $5M |

---

## ZoomInfo Fields NOT in LinkedIn T1.5

### HIGH VALUE Fields (Unique to ZoomInfo)

| Field | Description | Value for Sales |
|-------|-------------|-----------------|
| `revenue` | Exact dollar figure | **CRITICAL** for ICP sizing |
| `revenue_text` | Human-readable | Quick qualification |
| `phone_number` | Direct company line | Cold calling |
| `c_level_employees` | Count of C-suite | Org mapping |
| `director_level_employees` | Director count | Buyer population |
| `manager_level_employees` | Manager count | Champion population |
| `total_contacts` | Contacts in DB | Coverage indicator |
| `tech_stack` | Technologies used | Tech-based triggers |
| `business_classification_codes` | SIC/NAICS | Industry precision |
| `recent_scoops` | Executive moves | Timing signals |
| `news_and_media` | Press coverage | Context for outreach |
| `similar_companies` | Competitors | Comp intel |
| `org_chart` | Leadership hierarchy | Decision maker map |

### MEDIUM VALUE Fields

| Field | Description |
|-------|-------------|
| `ceo_rating` | CEO performance score (when available) |
| `enps_score` | Employee NPS (when available) |
| `funding_rounds` | Investment history |
| `email_formats` | Email pattern |

---

## Coverage Assessment (50 AU Agencies)

### Unable to Test Full Pool

Due to the **URL-only limitation**, we could not query 50 agencies by name. 

**To achieve 50-agency coverage, we would need:**
1. Pre-existing list of ZoomInfo URLs for AU agencies, OR
2. SERP discovery step: `site:zoominfo.com "{agency name}"` for each agency

### Estimated AU Marketing Agency Coverage

Based on web search results, ZoomInfo appears to have profiles for:
- ✅ Clemenger BBDO (verified)
- ✅ Clemenger Group (URL found, page dead)
- ⚠️ Major global networks likely have AU subsidiary pages
- ❓ Smaller Australian-only agencies: **Unknown coverage**

### Cost Projection for ZoomInfo-Enriched Waterfall

| Tier | Action | Cost |
|------|--------|------|
| T1.5 | LinkedIn Company | $0.025 |
| T1.6 | SERP ZoomInfo URL lookup | $0.0015 |
| T1.7 | ZoomInfo Company scrape | ~$0.025 (est) |
| **Total** | | **$0.0515/lead** |

---

## Recommendations

### 1. ❌ DO NOT integrate ZoomInfo as standalone enrichment
The URL-only limitation makes it impractical for discovery workflows.

### 2. ✅ CONSIDER ZoomInfo for HIGH-VALUE leads only
For HOT leads (ALS ≥ 85), the $0.05/lead cost is justified by:
- Exact revenue figures for proposal sizing
- Direct phone numbers for calling
- Executive move signals for timing
- Tech stack for tech-based positioning

### 3. ✅ Add ZoomInfo URL to T1.5b SERP query
Modify existing SERP query to also check ZoomInfo:
```
site:linkedin.com/company "{name}" OR site:zoominfo.com/c/ "{name}"
```

### 4. 🔄 Consider Alternative: Hunter.io Tech Domain Lookup
Hunter.io includes some tech stack data at $0.012/lookup — may be cheaper alternative.

---

## All ZoomInfo Fields Returned

```python
ZOOMINFO_FIELDS = [
    'url',                    # ZoomInfo page URL
    'id',                     # ZoomInfo company ID
    'name',                   # Company name
    'description',            # Company description
    'revenue',                # Revenue in USD (integer)
    'revenue_currency',       # Currency code
    'revenue_text',           # Human-readable revenue
    'stock_symbol',           # Ticker symbol (if public)
    'website',                # Company website
    'employees',              # Employee count (encoded)
    'employees_text',         # Employee range text
    'industry',               # Industry list
    'headquarters',           # Full HQ address
    'phone_number',           # Company phone
    'total_funding_amount',   # Total funding raised
    'most_recent_funding_amount',
    'funding_currency',
    'funding_rounds',
    'leadership',             # Key executives list
    'popular_searches',       # Related search terms
    'business_classification_codes',  # SIC/NAICS
    'ceo',                    # CEO info
    'total_employees',
    'c_level_employees',      # C-suite count
    'vp_level_employees',     # VP count
    'director_level_employees',
    'manager_level_employees',
    'non_manager_employees',
    'top_contacts',           # Total contacts available
    'org_chart',              # Leadership hierarchy
    'social_media',           # Social links
    'ceo_rating',             # CEO performance
    'enps_score',             # Employee NPS
    'similar_companies',      # Competitors
    'email_formats',          # Email patterns
    'products_owned',         # Products/services
    'tech_stack',             # Technologies used
    'recent_scoops',          # News/executive moves
    'news_and_media',         # Press coverage
    'timestamp',              # Data freshness
    'input',                  # Original query
]
```

---

## Conclusion

**ZoomInfo offers significantly richer data than LinkedIn T1.5**, particularly:
- **Exact revenue** (vs. no revenue in LinkedIn)
- **Phone numbers** (vs. none in LinkedIn)
- **Org chart/leadership breakdown** (vs. sample employees)
- **Tech stack** (vs. none)
- **Executive move signals** (vs. post-based inference only)

**However**, the **URL-only access model** makes it impractical for bulk discovery. Integration would require:
1. SERP-based URL discovery (+$0.0015/lead)
2. Selective application to HIGH-VALUE leads only

**RECOMMENDED:** Add ZoomInfo as T2.5 enrichment tier for HOT leads (ALS ≥ 85) only.

---

**Document Status:** Complete  
**Tested By:** research-1 (subagent)  
**Directive:** #146 PART A
