# Portfolio Enrichment Waterfall

**FILE:** `src/engines/icp_scraper.py`
**METHOD:** `enrich_portfolio_company()`
**PURPOSE:** Enrich portfolio company data with industry, size, and contact info

---

## Overview

When a client's portfolio companies are discovered (from case studies, testimonials, etc.), they need to be enriched with firmographic data (industry, employee count, domain) so they can be used for lookalike lead targeting.

The enrichment uses a **Claude-first waterfall** approach: Claude AI analyzes every company name first to establish a baseline, then API sources attempt to confirm/enrich that baseline.

---

## Waterfall Tiers

| Tier | Source | Purpose | Cost |
|------|--------|---------|------|
| **0** | Claude AI | Infer industry from company name (ALWAYS RUNS FIRST) | ~$0.002 |
| **1a** | Apollo Name Search | Search Apollo by company name | 1 credit |
| **1b** | Apollo Domain Lookup | Enrich via domain if available | 1 credit |
| **1.5** | LinkedIn Scrape | Fill gaps if Apollo found company but missing data | Apify credits |
| **1.6** | Clay | Multi-provider enrichment (Clearbit, ZoomInfo, etc.) | 1 Clay credit |
| **2** | LinkedIn via Google | Google search for LinkedIn URL, then scrape | Apify credits |
| **3** | Google Business | Search Google Business listings (excellent for local AU) | Apify credits |
| **4** | General Google | Find company website, infer industry from description | Apify credits |
| **Final** | Keyword Matching | Simple pattern matching (rarely needed) | Free |

---

## Tier Details

### Tier 0: Claude Inference (NEW - Always First)

**Why Claude First:**
- Australian SMBs often aren't in Apollo/LinkedIn databases
- Claude can intelligently infer industry from company names like:
  - "Kenner Electrics" → trades/electrical
  - "Rod's Kitchens" → construction/renovation
  - "First Aid HQ" → healthcare/training
- Ensures EVERY company gets at least a baseline industry

**Method:** `_infer_industry_with_claude()`

**Prompt:**
```
Analyze this company name and infer its likely industry and size.
Company Name: {company_name}
Domain: {domain if available}

Respond in JSON: {"industry": "...", "employee_range": "...", "confidence": "..."}
```

**Industries Used:**
- automotive, retail, construction, manufacturing
- healthcare, hospitality, technology, professional_services
- food_beverage, real_estate, education, fitness
- trades, environmental, recruitment

---

### Tier 1a: Apollo Name Search

**When:** No domain available
**API:** `POST /mixed_companies/search`
**Data Retrieved:** domain, industry, employee_count, founded_year, linkedin_url

### Tier 1b: Apollo Domain Lookup

**When:** Domain is known (from Tier 1a or provided)
**API:** `POST /organizations/enrich`
**Data Retrieved:** Same as 1a but more accurate with exact domain match

### Tier 1.5: LinkedIn Scrape (Fill Gaps)

**When:** Apollo found company but missing industry/employee_count
**API:** Apify LinkedIn Company Scraper
**Data Retrieved:** employee_count, employee_range, industry, headquarters

### Tier 1.6: Clay Enrichment

**When:** Domain known but still missing data
**API:** Clay Company Enrichment (aggregates Clearbit, ZoomInfo, etc.)
**Data Retrieved:** industry, employee_count, location, country

### Tier 2: LinkedIn via Google

**When:** Company not found in Apollo
**Process:**
1. Google search: `"{company_name}" site:linkedin.com/company`
2. Extract LinkedIn company URL
3. Scrape LinkedIn page via Apify
**Data Retrieved:** employee_range, industry, headquarters

### Tier 3: Google Business

**When:** Still no data (great for local AU businesses)
**API:** Apify Google Business Scraper
**Search:** `{company_name}` in Australia
**Data Retrieved:** address, category (used as industry), website

### Tier 4: General Google Search

**When:** Last resort before keyword fallback
**Process:**
1. Google search: `"{company_name}" Australia company`
2. Find company website
3. Infer industry from page title/description
**Data Retrieved:** domain, country, inferred industry

### Final Fallback: Keyword Matching

**When:** Claude failed AND all APIs failed (rare)
**Method:** `_infer_industry_from_name()`
**Pattern Matching:**
```python
"kitchen" → construction
"electric" → trades
"medical" → healthcare
"hotel" → hospitality
```

---

## Usage in Lead Sourcing

Once portfolio companies have enriched data, the **pool population waterfall** uses them:

1. **Tier 1:** Search Apollo for people at portfolio company domains
2. **Tier 2:** Search Apollo by portfolio industries (lookalike targeting)
3. **Tier 3:** Fall back to generic ICP criteria

See: `src/orchestration/flows/pool_population_flow.py`

---

## Cost Estimation

For 10 portfolio companies:
- Claude inference: ~$0.02
- Apollo searches: ~10 credits
- Apify (if needed): ~$0.50
- Clay (if needed): ~10 credits

**Total:** ~$1-2 per client onboarding

---

## Implementation Notes

**File:** `src/engines/icp_scraper.py`

**Key Methods:**
- `enrich_portfolio_company()` - Main waterfall orchestrator
- `_infer_industry_with_claude()` - Claude inference (Tier 0)
- `enrich_portfolio_batch()` - Batch processing for multiple companies

**Dependencies:**
- `src/integrations/anthropic.py` - Claude API
- `src/integrations/apollo.py` - Apollo API
- `src/integrations/apify.py` - LinkedIn/Google scrapers
- `src/integrations/clay.py` - Clay enrichment

---

## Changelog

| Date | Change |
|------|--------|
| 2026-01-09 | Added Claude-first tier (Tier 0) to ensure all companies get baseline industry |
| 2026-01-08 | Original waterfall: Apollo → LinkedIn → Clay → Google → Keyword fallback |
