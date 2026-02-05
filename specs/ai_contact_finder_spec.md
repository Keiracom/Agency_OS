# AI Contact Finder - Technical Specification
> **Version:** 1.0 | **Date:** 2025-02-04 | **Status:** Draft  
> **Currency:** All costs in $AUD

## Executive Summary

A fallback lead intelligence system that finds business contacts when primary data sources (Apollo, Prospeo) have gaps. Uses stealth web scraping with AI extraction to discover leadership/team information from company websites and public sources.

**Use Case:** "Apollo returned 0 contacts for `acme-corp.com.au`. Find their decision-makers."

---

## 1. Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                     AI CONTACT FINDER PIPELINE                       │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  INPUT                    SEARCH                   EXTRACT          │
│  ┌─────────┐    ┌───────────────────────┐    ┌──────────────────┐  │
│  │ Company │───▶│  Multi-Source Search  │───▶│  AI Extraction   │  │
│  │ Domain  │    │  • Google (Team/About)│    │  (Claude Haiku)  │  │
│  └─────────┘    │  • Company Website    │    │  • Names/Titles  │  │
│                 │  • LinkedIn Search    │    │  • Confidence    │  │
│                 └───────────────────────┘    └──────────────────┘  │
│                            │                          │             │
│                            ▼                          ▼             │
│                 ┌───────────────────────┐    ┌──────────────────┐  │
│                 │  Stealth Browser      │    │  Profile Finder  │  │
│                 │  (Playwright)         │    │  • LinkedIn URLs │  │
│                 │  + Webshare Proxies   │    │  • Verification  │  │
│                 │  (215k IPs)           │    └──────────────────┘  │
│                 └───────────────────────┘             │             │
│                                                       ▼             │
│                                              ┌──────────────────┐  │
│                                              │  OUTPUT          │  │
│                                              │  Structured JSON │  │
│                                              │  + Confidence    │  │
│                                              └──────────────────┘  │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 2. Pipeline Stages

### Stage 1: Input Normalization
**Purpose:** Clean and validate company input

```python
Input:
  - company_name: str        # "ACME Corporation"
  - domain: str              # "acme.com.au" (optional, derived if missing)
  
Output:
  - normalized_domain: str   # "acme.com.au"
  - normalized_name: str     # "ACME Corporation"
  - search_variants: list    # ["ACME", "ACME Corporation", "ACME Corp"]
```

### Stage 2: Multi-Source Search
**Purpose:** Find pages likely to contain team/leadership info

| Source | Search Pattern | Priority |
|--------|---------------|----------|
| Google | `site:{domain} team OR leadership OR about` | High |
| Google | `"{company}" team page` | Medium |
| Google | `"{company}" CEO OR founder OR director` | Medium |
| LinkedIn | `{company} employees` | High |
| Direct | `{domain}/about`, `{domain}/team`, `{domain}/our-team` | High |

**Implementation:** Use Brave Search API for web search (avoids Google bot detection)

### Stage 3: Stealth Page Fetch
**Purpose:** Retrieve page content without detection

**Tools:**
- `autonomous_browser.py` - Playwright + stealth scripts
- `proxy_manager.py` - 215k Webshare residential proxies
- Burner Protocol - Auto-retry with identity rotation on 403/429

**Process:**
1. Generate stealth identity (UA + viewport + locale + timezone)
2. Route through random Webshare proxy
3. Fetch with Playwright (JS rendering for React/Vue pages)
4. Scroll to trigger lazy-loaded content
5. Extract text + preserve structure

### Stage 4: AI Content Extraction
**Purpose:** Extract structured contact data from raw page text

**Model:** Claude 3.5 Haiku (cost-optimized)

**Prompt Template:**
```
You are a business contact extractor. Analyze this page content and extract all identifiable people with business roles.

RULES:
1. Only extract people who appear to work at or lead the company
2. Exclude testimonials, client quotes, news mentions
3. Infer titles from context if not explicit
4. Rate confidence: HIGH (name + explicit title), MEDIUM (name + inferred role), LOW (name only)

OUTPUT FORMAT (JSON array):
[
  {
    "name": "John Smith",
    "title": "CEO & Founder",
    "confidence": "HIGH",
    "source_context": "Listed under 'Our Leadership Team'"
  }
]

PAGE CONTENT:
{page_text}
```

### Stage 5: LinkedIn Profile Discovery
**Purpose:** Find LinkedIn URLs for extracted contacts

**Method 1: Brave Search (Preferred)**
```
"{name}" site:linkedin.com/in "{company}"
```

**Method 2: Constructed URL Guess**
```
https://linkedin.com/in/{firstname}-{lastname}-{random}
```

**Method 3: Google Dorking (Fallback)**
```
"{name}" "{company}" linkedin
```

### Stage 6: Output Structuring
**Purpose:** Produce validated, scored contact records

```json
{
  "company": {
    "name": "ACME Corporation",
    "domain": "acme.com.au"
  },
  "contacts": [
    {
      "name": "John Smith",
      "title": "CEO & Founder",
      "linkedin_url": "https://linkedin.com/in/john-smith-12345",
      "confidence_score": 0.92,
      "confidence_breakdown": {
        "name_extraction": 1.0,
        "title_extraction": 0.95,
        "linkedin_match": 0.85
      },
      "sources": ["acme.com.au/about", "linkedin.com/in/john-smith"]
    }
  ],
  "metadata": {
    "searched_at": "2025-02-04T10:30:00Z",
    "pages_scraped": 4,
    "total_cost_aud": 0.012
  }
}
```

---

## 3. Data Models

### Contact Record
```python
@dataclass
class Contact:
    name: str                           # Full name
    title: Optional[str]                # Job title
    company: str                        # Company name
    linkedin_url: Optional[str]         # LinkedIn profile URL
    email: Optional[str]                # Email if found (bonus)
    phone: Optional[str]                # Phone if found (bonus)
    confidence: float                   # 0.0 - 1.0
    sources: List[str]                  # URLs where found
    extraction_method: str              # "ai" | "pattern" | "structured"
    found_at: datetime
```

### Search Job
```python
@dataclass
class ContactFinderJob:
    job_id: str
    company_name: str
    domain: str
    status: str                         # "pending" | "searching" | "extracting" | "complete" | "failed"
    pages_searched: int
    contacts_found: List[Contact]
    total_cost_aud: float
    started_at: datetime
    completed_at: Optional[datetime]
    error: Optional[str]
```

---

## 4. Cost Analysis

### Per-Request Costs

| Component | Cost (AUD) | Notes |
|-----------|------------|-------|
| **Brave Search API** | $0.007 | ~$9 USD/1000 queries → ~$0.014 AUD each, batch discount |
| **Webshare Proxy** | $0.0001 | $15 USD/month for 215k IPs → negligible per request |
| **Playwright Instance** | $0.00 | Self-hosted, compute only |
| **Claude Haiku** | $0.0015 | ~$0.25 USD/1M input, $1.25/1M output |
| **Supabase Storage** | $0.0001 | Negligible for structured JSON |

### Cost Per Lead Scenarios

| Scenario | Pages | API Calls | Haiku Tokens | **Total AUD** |
|----------|-------|-----------|--------------|---------------|
| **Easy** (company has /team page) | 2 | 1 search | ~2k | **$0.012** |
| **Medium** (Google search needed) | 4 | 3 searches | ~5k | **$0.035** |
| **Hard** (LinkedIn + multiple sources) | 8 | 5 searches | ~10k | **$0.070** |
| **Very Hard** (sparse data, retries) | 15 | 8 searches | ~15k | **$0.120** |

### Monthly Budget Projections

| Volume | Easy (60%) | Medium (30%) | Hard (10%) | **Monthly AUD** |
|--------|-----------|--------------|------------|-----------------|
| 100 leads | $0.72 | $1.05 | $0.70 | **$2.47** |
| 500 leads | $3.60 | $5.25 | $3.50 | **$12.35** |
| 1,000 leads | $7.20 | $10.50 | $7.00 | **$24.70** |
| 5,000 leads | $36.00 | $52.50 | $35.00 | **$123.50** |

---

## 5. Implementation Plan

### Phase 1: Core Pipeline (Week 1)
**Deliverables:**
- [ ] `tools/contact_finder.py` - Main orchestrator
- [ ] `ContactFinder` class with async pipeline
- [ ] Integration with `autonomous_browser.py`
- [ ] Basic AI extraction prompt

**Files:**
```
tools/
├── contact_finder.py        # Main tool (NEW)
├── autonomous_browser.py    # Existing - stealth fetch
├── proxy_manager.py         # Existing - proxy rotation
└── enrichment_master.py     # Existing - Apollo fallback
```

### Phase 2: AI Extraction (Week 2)
**Deliverables:**
- [ ] Claude Haiku integration for content parsing
- [ ] Prompt optimization for accuracy
- [ ] Confidence scoring algorithm
- [ ] Edge case handling (non-English, heavy JS, etc.)

### Phase 3: LinkedIn Discovery (Week 2-3)
**Deliverables:**
- [ ] Brave Search integration for LinkedIn lookup
- [ ] Profile URL validation
- [ ] Rate limiting to avoid LinkedIn blocks
- [ ] Fallback to Unipile API if available

### Phase 4: Database Integration (Week 3)
**Deliverables:**
- [ ] Supabase schema for contact storage
- [ ] Deduplication logic
- [ ] Search job tracking
- [ ] Cost logging per request

---

## 6. Supabase Schema

```sql
-- Contact Finder Results
CREATE TABLE contact_finder_contacts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_domain TEXT NOT NULL,
    company_name TEXT,
    contact_name TEXT NOT NULL,
    contact_title TEXT,
    linkedin_url TEXT,
    email TEXT,
    phone TEXT,
    confidence_score FLOAT,
    sources JSONB,           -- Array of source URLs
    raw_extraction JSONB,    -- Full AI extraction response
    found_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Deduplication
    UNIQUE(company_domain, contact_name)
);

-- Search Job Tracking
CREATE TABLE contact_finder_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_domain TEXT NOT NULL,
    company_name TEXT,
    status TEXT DEFAULT 'pending',
    pages_searched INT DEFAULT 0,
    contacts_found INT DEFAULT 0,
    cost_aud DECIMAL(10,4) DEFAULT 0,
    error TEXT,
    started_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);

-- Cost Tracking
CREATE TABLE contact_finder_costs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_id UUID REFERENCES contact_finder_jobs(id),
    component TEXT,          -- 'brave_search', 'claude_haiku', 'proxy'
    cost_aud DECIMAL(10,6),
    tokens_used INT,
    recorded_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_contacts_domain ON contact_finder_contacts(company_domain);
CREATE INDEX idx_contacts_confidence ON contact_finder_contacts(confidence_score DESC);
CREATE INDEX idx_jobs_status ON contact_finder_jobs(status);
```

---

## 7. API Interface

### CLI Usage
```bash
# Single company lookup
python tools/contact_finder.py find --domain "acme.com.au"
python tools/contact_finder.py find --company "ACME Corporation"

# Batch processing
python tools/contact_finder.py batch --input companies.csv --output contacts.json

# With options
python tools/contact_finder.py find --domain "acme.com.au" \
    --max-pages 10 \
    --include-linkedin \
    --confidence-threshold 0.7 \
    --output-format json
```

### Python API
```python
from tools.contact_finder import ContactFinder

finder = ContactFinder()

# Async usage
contacts = await finder.find_contacts(
    domain="acme.com.au",
    max_pages=5,
    include_linkedin=True,
    confidence_threshold=0.7
)

# Sync wrapper
contacts = finder.find_sync(domain="acme.com.au")

# Batch
results = await finder.batch_find(
    domains=["acme.com.au", "example.com.au"],
    concurrency=3
)
```

---

## 8. Risk Mitigation

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| LinkedIn blocks IP | Medium | High | Use Webshare residential proxies, rate limit to 1 req/5s |
| Google CAPTCHA | Medium | Medium | Brave Search API instead of scraping Google directly |
| AI hallucination | Low | Medium | Require source_context in extraction, manual review for high-value leads |
| Cost overrun | Low | Medium | Hard limit per job ($0.50 AUD), alert at 80% budget |
| Cloudflare blocks | Medium | Low | Burner Protocol auto-rotates identity |

---

## 9. Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| **Contact Discovery Rate** | >60% | Companies where ≥1 contact found |
| **Title Accuracy** | >85% | Spot-check validation against LinkedIn |
| **LinkedIn Match Rate** | >50% | Contacts with verified LinkedIn URL |
| **Cost Per Lead** | <$0.05 AUD | Average across all difficulty levels |
| **Pipeline Latency** | <30s | Time from input to structured output |

---

## 10. Dependencies

### Existing (No Changes)
- `tools/autonomous_browser.py` - Stealth Playwright wrapper
- `tools/proxy_manager.py` - Webshare 215k proxy pool
- `tools/enrichment_master.py` - Apollo fallback

### New Requirements
```bash
# Already installed
playwright
aiohttp
fake-useragent

# May need
anthropic           # Claude API client (if not using raw HTTP)
```

### API Keys Required
- [x] `ANTHROPIC_API_KEY` - ✅ Available
- [x] `BRAVE_API_KEY` - ⚠️ Need to verify/add
- [x] `WEBSHARE_PROXY_URL` - ✅ Available (215k proxies)

---

## 11. Example Output

**Input:** `domain=digitalagency.com.au`

**Output:**
```json
{
  "job_id": "cf_a1b2c3d4",
  "company": {
    "name": "Digital Agency Co",
    "domain": "digitalagency.com.au"
  },
  "contacts": [
    {
      "name": "Sarah Mitchell",
      "title": "Managing Director",
      "linkedin_url": "https://linkedin.com/in/sarah-mitchell-digital",
      "confidence_score": 0.94,
      "sources": [
        "digitalagency.com.au/about",
        "linkedin.com/company/digitalagency"
      ]
    },
    {
      "name": "James Chen",
      "title": "Head of Strategy",
      "linkedin_url": "https://linkedin.com/in/jameschen-strategy",
      "confidence_score": 0.87,
      "sources": [
        "digitalagency.com.au/team"
      ]
    }
  ],
  "metadata": {
    "pages_scraped": 3,
    "search_queries": 2,
    "total_cost_aud": 0.028,
    "duration_seconds": 12.4,
    "status": "complete"
  }
}
```

---

## Appendix A: Competitive Comparison

| Feature | AI Contact Finder | Apollo | Hunter.io | Clearbit |
|---------|------------------|--------|-----------|----------|
| Cost per lead | $0.02-0.07 AUD | $0.15-0.50 AUD | $0.10-0.30 AUD | $0.20-0.80 AUD |
| Works on small AU companies | ✅ | ❌ Limited | ❌ Limited | ❌ Limited |
| LinkedIn profiles | ✅ | ✅ | ❌ | ✅ |
| Real-time scraping | ✅ | ❌ Cached | ❌ Cached | ❌ Cached |
| No API limits | ✅ | ❌ | ❌ | ❌ |

---

## Appendix B: Prompt Library

### Main Extraction Prompt
```
You are a business intelligence analyst extracting contact information from web pages.

TASK: Identify all people who work at {company_name} from this page content.

EXTRACTION RULES:
1. Only include people with clear employment/leadership roles at this specific company
2. EXCLUDE: testimonial authors, quoted clients, news article subjects, event speakers (unless they work here)
3. INCLUDE: founders, executives, team members, employees listed on team pages
4. Infer titles from context clues: "leads our development team" → "Development Lead"
5. Assign confidence: HIGH (explicit name + title), MEDIUM (inferred), LOW (name only)

OUTPUT (JSON only, no markdown):
[
  {"name": "...", "title": "...", "confidence": "HIGH|MEDIUM|LOW", "context": "..."}
]

If no contacts found, return: []

PAGE CONTENT:
---
{content}
---
```

### LinkedIn Search Prompt
```
Generate 3 search queries to find this person's LinkedIn profile:

Name: {name}
Company: {company}
Title: {title}

Output as JSON array of query strings.
```

---

*Specification authored by Elliot (CTO) | Keiracom 2025*
