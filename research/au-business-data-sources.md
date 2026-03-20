# Australian Business Revenue & Size Data Source Investigation

**Research Date:** 2026-03-01  
**Purpose:** Identify viable data sources for Australian SME revenue and employee data for Agency OS (targeting Australian marketing agencies)

## Summary Table

| Source | AU Coverage | Employee Data | Revenue Data | Cost/Record AUD | API | Verdict |
|--------|-------------|---------------|--------------|-----------------|-----|---------|
| **Dun & Bradstreet (Global)** | 170M+ global; AU coverage via D&B Direct+ | ✅ Yes (exact count + range) | ✅ Yes (estimated) | ~$0.30-0.50 (UK gov pricing: £0.16/record ≈ $0.30); Enterprise from $37.5K/yr | ✅ D&B Direct+ API | **VIABLE** - Premium but comprehensive |
| **ASIC Company Extract** | 2.9M+ AU companies | ❌ No | ❌ No | Free via data.gov.au; $9-45 per extract via ASIC Connect | ✅ API via data.gov.au | **NOT VIABLE** - No size/revenue data |
| **illion (now Experian)** | AU-specific, merged into Experian Oct 2024 | ✅ Yes | ✅ Yes | Quote required | ✅ Yes (via Experian) | **VIABLE** - AU-native, acquired by Experian |
| **Experian AU Business** | 100K+ AU businesses including SME | ✅ Yes | ✅ Yes | Quote required (~$1-2/record estimated) | ✅ Yes | **VIABLE** - Best AU-native option post-illion merger |
| **LinkedIn Company (T1.5)** | 56M+ companies globally; good AU coverage | ⚠️ Range only: 1, 2-10, 11-50, 51-200, 201-500, 501-1K, 1K-5K, 5K-10K, 10K+ | ❌ Never | Already have | ✅ Via T1.5/scrapers | **MARGINAL** - No revenue; size buckets too coarse |
| **Crunchbase** | ~10K AU companies (funded focus) | ✅ Yes (estimate) | ✅ Yes (estimate) | Pro: $588/yr; Enterprise: quote; API: quote | ✅ API (Enterprise tier) | **NOT VIABLE** - <5% AU SME coverage; startup bias |
| **ASIC Financial Filings** | Only >$50M revenue companies | ✅ If filed | ✅ If filed | Free if available | ❌ No bulk API | **NOT VIABLE** - Threshold excludes all SMEs |
| **SimilarWeb** | Traffic-indexed companies only | ✅ Headcount estimate | ✅ Revenue estimate | Web Intel: from $1,500/yr; API: quote required | ✅ Yes | **MARGINAL** - Traffic-based; misses low-traffic agencies |
| **SEMrush** | SEO data only | ❌ No | ❌ No | N/A | N/A | **NOT VIABLE** - No firmographic data |
| **ATO Data** | Only >$100M (public) or >$200M (private) | ❌ No | ✅ Tax data only | Free | ✅ Data.gov.au | **NOT VIABLE** - Threshold excludes all SMEs |
| **Bright Data Datasets** | Global coverage; 56M+ LinkedIn companies | ✅ Via ZoomInfo/enrichment datasets | ✅ Via ZoomInfo dataset | $250/100K records ($0.0025/record) | ✅ Yes | **VIABLE** - Best price; ZoomInfo dataset includes revenue |

---

## Detailed Analysis by Source

### 1. Dun & Bradstreet (Global)

**What we found:**
- D&B sold AU/NZ operations in 2015 (became illion)
- D&B Direct+ still provides global coverage including AU via DUNS numbers
- 170M+ business records globally
- D&B Hoovers: $529/year for 1,800 credits (~$0.29/credit)
- UK government pricing shows £0.16/record (~$0.30 AUD)
- Median enterprise pricing: $37,500/year

**Data Available:**
- ✅ Employee count (exact + range)
- ✅ Revenue (estimated)
- ✅ Industry classification
- ✅ DUNS linkage

**Verdict: VIABLE** - Premium pricing but comprehensive global data. AU SME coverage uncertain without direct inquiry.

---

### 2. ASIC Company Extract

**What we found:**
- Contains ONLY: Company Name, ACN, Type, Class, Sub Class, Status, Date of Registration, Date of Deregistration, ABN
- **NO employee count**
- **NO financial data** (even for large companies - that's separate filings)
- API available via data.gov.au (free bulk download)
- Individual extracts: $9-45 via ASIC Connect

**Data Available:**
- ❌ Employee count
- ❌ Revenue
- ✅ Company registration details
- ✅ Directors (separate extract)

**Verdict: NOT VIABLE** - No sizing or financial data whatsoever.

---

### 3. illion (formerly D&B Australia)

**What we found:**
- Was D&B Australia until 2015 divestiture
- **Acquired by Experian Australia October 2024**
- Now merged into Experian AU business data
- Previously AU's most comprehensive business database
- Quote-based pricing

**Data Available:**
- ✅ Employee count
- ✅ Revenue estimates
- ✅ Credit risk data
- ✅ AU-native coverage

**Verdict: VIABLE** - Contact Experian AU for pricing. Now part of Experian.

---

### 4. Experian AU Business Marketing

**What we found:**
- Now includes illion data post-acquisition
- Claims 100,000+ Australian businesses
- Explicit mention of: "revenue, employee count, location, industry"
- Quote required - no public pricing
- API available

**Data Available:**
- ✅ Employee count
- ✅ Revenue
- ✅ Industry
- ✅ Location
- ✅ Director/executive profiles

**Verdict: VIABLE** - Best AU-native option. Request quote. Post-illion acquisition means largest AU dataset.

---

### 5. LinkedIn Company Data (already have via T1.5)

**What we found - EXACT BUCKETS:**
```
A = 1 (Self-employed)
B = 2-10
C = 11-50
D = 51-200
E = 201-500
F = 501-1000
G = 1001-5000
H = 5001-10000
I = 10001+
```

**Data Available:**
- ⚠️ Employee count RANGE (not exact)
- ❌ Revenue - NEVER available via LinkedIn
- ✅ Industry
- ✅ Location
- ✅ Follower count

**Verdict: MARGINAL** - Already have. Useful for coarse size segmentation but revenue gap is critical. Cannot distinguish $500K agency from $5M agency in same bucket.

---

### 6. Crunchbase

**What we found:**
- AU "Top 10K" companies hub suggests ~10,000 AU companies
- AU total businesses: 2.4M+ active
- **Coverage: <0.5% of AU businesses**
- Heavy bias toward funded startups
- Marketing agencies rarely appear (unfunded service businesses)

**Pricing:**
- Pro: $49/month ($588/year)
- Enterprise: Custom quote
- API: Enterprise tier only

**Data Available:**
- ✅ Employee count (estimate)
- ✅ Revenue (estimate)
- ✅ Funding history
- But only for funded companies

**Verdict: NOT VIABLE** - Marketing agencies (~3,300 in AU) are service businesses rarely appearing in Crunchbase unless they've raised VC. Coverage estimate: <5% of target segment.

---

### 7. ASIC Financial Filings

**What we found - THRESHOLDS:**
- Large proprietary company must file if 2+ of:
  - Revenue ≥ $50 million
  - Gross assets ≥ $25 million  
  - Employees ≥ 100

- **Small proprietary companies (most SME/agencies): EXEMPT from filing**

**Data Available:**
- Only for large companies above threshold
- ~3,000 entities file (vs 2.4M businesses)

**Verdict: NOT VIABLE** - Threshold is $50M+ revenue. Typical marketing agency: $500K-$10M revenue. Zero overlap.

---

### 8. SimilarWeb / SEMrush

**SimilarWeb:**
- ✅ Does estimate company revenue (via their methodology)
- ✅ Estimates employee count
- Based on traffic correlation and multiple sources
- Starts $199/month (Web Intelligence Starter)
- API: Custom quote required

**SEMrush:**
- ❌ SEO/SEM data only
- ❌ No company firmographic data
- Not relevant for this use case

**DataForSEO (already have):**
- ❌ SEO data only
- ❌ No company revenue/size data

**Verdict: MARGINAL** - SimilarWeb has revenue estimates but coverage depends on web traffic. Low-traffic agencies may be missing or have poor estimates.

---

### 9. ATO Data

**What we found - THRESHOLDS:**
- Corporate Tax Transparency Report covers:
  - Public/foreign-owned: $100M+ income
  - Australian-owned private: $200M+ income
  
- **No publicly accessible data below these thresholds**
- ABN Lookup: No revenue data
- Large business register: $250M+ only

**Verdict: NOT VIABLE** - Zero coverage of SME segment. Thresholds 20-400x higher than typical agency revenue.

---

### 10. Bright Data Datasets

**What we found:**
- LinkedIn Company dataset: 56M+ records, $250/100K records ($0.0025/record)
  - ✅ Employee count (range)
  - ❌ No revenue
  
- **ZoomInfo dataset available on Bright Data:**
  - ✅ Revenue
  - ✅ Employee count
  - ✅ Industry
  - $250/100K records

- Business Intelligence dataset:
  - ✅ CompanyID, Revenue, EmployeeCount, Founded, Country

**Verdict: VIABLE** - Best price point at $0.0025/record. ZoomInfo dataset through Bright Data includes revenue + employee count. Need to verify AU coverage.

---

## Recommendations for Agency OS

### Tier 1: Primary Sources (Recommended)
1. **Experian AU** (includes illion) - Request quote. Best AU-native coverage with revenue + employee data.
2. **Bright Data ZoomInfo dataset** - $250/100K. Verify AU coverage and accuracy first.

### Tier 2: Supplementary Sources
3. **LinkedIn (already have)** - For employee range buckets. No revenue.
4. **SimilarWeb** - For revenue estimates on web-active agencies. Quote required.

### Tier 3: Not Recommended
5. **ASIC** - No size/revenue data
6. **Crunchbase** - Wrong market segment
7. **ATO** - Threshold too high
8. **D&B Global** - Pricing may be prohibitive for SME focus

### Key Gap
**Revenue data for Australian SMEs is scarce.** Most free/low-cost sources only have employee data. Revenue requires premium data providers (Experian/illion, ZoomInfo, D&B) or inference models.

### Suggested Action
1. Request Experian AU quote for marketing/advertising industry segment
2. Test Bright Data ZoomInfo dataset with sample of 1,000 AU marketing agencies
3. Build revenue inference model using employee count + industry as proxy
