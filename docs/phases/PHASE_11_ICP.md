# Phase 11: ICP Discovery System

**Status:** ✅ Complete  
**Tasks:** 18  
**Dependencies:** Phase 10 complete (Production deployed)

---

## Overview

Automatically discover client ICP from their digital footprint using modular skills.

When a marketing agency signs up, they provide their website URL. The system:
1. Scrapes their website and digital presence
2. Uses modular skills to extract structured ICP data
3. Analyzes their existing clients to derive patterns
4. Auto-configures ALS weights for their specific ICP
5. User confirms or adjusts

---

## Tasks

| Task ID | Task Name | Description | Files | Complexity |
|---------|-----------|-------------|-------|------------|
| ICP-001 | Database migration | Add ICP fields to clients | `supabase/migrations/012_client_icp_profile.sql` | M |
| ICP-002 | Skill base class | Base skill + registry | `src/agents/skills/base_skill.py` | M |
| ICP-003 | Website Parser Skill | Parse HTML → structured pages | `src/agents/skills/website_parser.py` | M |
| ICP-004 | Service Extractor Skill | Find agency services | `src/agents/skills/service_extractor.py` | M |
| ICP-005 | Value Prop Extractor Skill | Find value proposition | `src/agents/skills/value_prop_extractor.py` | M |
| ICP-006 | Portfolio Extractor Skill | Find client logos/cases | `src/agents/skills/portfolio_extractor.py` | M |
| ICP-007 | Industry Classifier Skill | Classify industries | `src/agents/skills/industry_classifier.py` | M |
| ICP-008 | Company Size Estimator Skill | Estimate team size | `src/agents/skills/company_size_estimator.py` | S |
| ICP-009 | ICP Deriver Skill | Derive ICP from portfolio | `src/agents/skills/icp_deriver.py` | L |
| ICP-010 | ALS Weight Suggester Skill | Suggest scoring weights | `src/agents/skills/als_weight_suggester.py` | M |
| ICP-011 | ICP Scraper Engine | Multi-source scraping | `src/engines/icp_scraper.py` | L |
| ICP-012 | ICP Discovery Agent | Orchestrate skills | `src/agents/icp_discovery_agent.py` | L |
| ICP-013 | Onboarding API routes | Extraction endpoints | `src/api/routes/onboarding.py` | M |
| ICP-014 | Onboarding flow | Prefect async flow | `src/orchestration/flows/onboarding_flow.py` | M |
| ICP-015 | Onboarding UI | Website input + confirm | `frontend/app/onboarding/page.tsx` | M |
| ICP-016 | ICP Settings page | View/edit ICP | `frontend/app/dashboard/settings/icp/page.tsx` | M |
| ICP-017 | Update Create Campaign | Simplified form | `frontend/app/dashboard/campaigns/new/page.tsx` | S |
| ICP-018 | Skill unit tests | Test each skill | `tests/test_skills/*.py` | M |

---

## Skills Architecture

```
src/agents/skills/
├── base_skill.py           # Skill base class + registry
├── website_parser.py       # Parse raw HTML → structured pages
├── service_extractor.py    # Find services offered
├── value_prop_extractor.py # Find value proposition
├── portfolio_extractor.py  # Find client logos/case studies
├── industry_classifier.py  # Classify target industries
├── company_size_estimator.py # Estimate team size
├── icp_deriver.py          # Derive ICP from portfolio
└── als_weight_suggester.py # Suggest custom ALS weights
```

---

## ICP Discovery Flow

```
Website URL
    │
    ▼
┌─────────────────┐
│ ICP Scraper     │ ──► Raw HTML, LinkedIn data
│ Engine          │
└─────────────────┘
    │
    ▼
┌─────────────────┐
│ Website Parser  │ ──► Structured pages
│ Skill           │
└─────────────────┘
    │
    ├──► Service Extractor ──► Services list
    ├──► Value Prop Extractor ──► Value proposition
    └──► Portfolio Extractor ──► Client companies
             │
             ▼
        ┌─────────────────┐
        │ Enrich via      │ ──► Company sizes, industries
        │ Apollo          │
        └─────────────────┘
             │
             ▼
        ┌─────────────────┐
        │ ICP Deriver     │ ──► ICP profile
        │ Skill           │
        └─────────────────┘
             │
             ▼
        ┌─────────────────┐
        │ ALS Weight      │ ──► Custom weights
        │ Suggester       │
        └─────────────────┘
```

---

## Database Fields Added

```sql
ALTER TABLE clients ADD COLUMN website_url TEXT;
ALTER TABLE clients ADD COLUMN icp_industries TEXT[];
ALTER TABLE clients ADD COLUMN icp_company_sizes TEXT[];
ALTER TABLE clients ADD COLUMN icp_locations TEXT[];
ALTER TABLE clients ADD COLUMN als_weights JSONB DEFAULT '{}';
ALTER TABLE clients ADD COLUMN icp_extracted_at TIMESTAMPTZ;
ALTER TABLE clients ADD COLUMN icp_confirmed_at TIMESTAMPTZ;
```

---

## Checkpoint 7 Criteria

- [ ] All 8 skills implemented and tested
- [ ] ICP Scraper Engine fetches from website + LinkedIn
- [ ] ICP Discovery Agent orchestrates skills correctly
- [ ] Onboarding API endpoints work
- [ ] Prefect flow runs end-to-end
- [ ] Onboarding UI shows extraction progress
- [ ] User can confirm/edit ICP
- [ ] Create Campaign inherits ICP from client
- [ ] Custom ALS weights applied to scoring
