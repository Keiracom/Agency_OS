# Siege Waterfall Implementation Plan

**Created:** 2026-02-05
**Status:** PLANNING
**Priority:** CRITICAL — Core business logic overhaul

---

## Overview

Replace Apollo-centric enrichment with 5-tier Siege Waterfall:

| Tier | Source | Cost (AUD) | Status |
|------|--------|------------|--------|
| 1 | ABN Bulk (data.gov.au) | FREE | ❌ Not built |
| 2 | GMB/Ads Signals | ~$0.006 | ❌ Not built |
| 3 | Hunter.io Email | ~$0.012 | ✅ MCP ready |
| 4 | LinkedIn Pulse (Proxycurl) | ~$0.024 | ❌ Not built |
| 5 | Identity Gold (Kaspr/Lusha) | ~$0.45 | ❌ Not built |

---

## Phase 1: Data Layer (Database Schema)

### New Tables Required
```sql
-- ABN seed data
CREATE TABLE abn_businesses (
    abn VARCHAR(11) PRIMARY KEY,
    acn VARCHAR(9),
    legal_name TEXT,
    trading_names TEXT[],
    state VARCHAR(3),
    postcode VARCHAR(4),
    gst_registered BOOLEAN,
    abn_status VARCHAR(20),
    entity_type VARCHAR(50),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- GMB enrichment
CREATE TABLE gmb_enrichment (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    abn VARCHAR(11) REFERENCES abn_businesses(abn),
    place_id VARCHAR(255),
    gmb_name TEXT,
    phone VARCHAR(20),
    website TEXT,
    address TEXT,
    rating DECIMAL(2,1),
    review_count INTEGER,
    match_confidence DECIMAL(3,2),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Ads signals (Meta/Google)
CREATE TABLE ads_signals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    lead_id UUID REFERENCES leads(id),
    platform VARCHAR(20), -- 'meta' | 'google'
    ad_count INTEGER,
    first_seen DATE,
    last_seen DATE,
    ad_longevity_days INTEGER,
    intent_score INTEGER, -- 0-100
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Waterfall tracking
CREATE TABLE waterfall_enrichment (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    lead_id UUID REFERENCES leads(id),
    tier INTEGER,
    source VARCHAR(50),
    data JSONB,
    cost_aud DECIMAL(10,4),
    success BOOLEAN,
    error_message TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

### Modify Existing Tables
```sql
-- Add to leads table
ALTER TABLE leads ADD COLUMN IF NOT EXISTS abn VARCHAR(11);
ALTER TABLE leads ADD COLUMN IF NOT EXISTS waterfall_tier INTEGER DEFAULT 0;
ALTER TABLE leads ADD COLUMN IF NOT EXISTS total_enrichment_cost DECIMAL(10,4) DEFAULT 0;
```

**Deliverable:** Migration file `056_siege_waterfall_schema.sql`

---

## Phase 2: Tier 1 — ABN Bulk Ingestion

### Components
1. `src/integrations/abn.py` — ABN Bulk Extract parser
2. `src/engines/abn_ingestion_worker.py` — Prefect flow for bulk import
3. Cron job: Weekly ABN sync

### Data Source
- URL: https://data.gov.au/data/dataset/abn-bulk-extract
- Format: ZIP containing pipe-delimited text files
- Size: ~500MB compressed, 3.5M+ records
- Filter: Active ABNs only, specific ANZSIC codes for marketing agencies

### Flow
```
Download ABN Bulk ZIP
    ↓
Extract & Parse (streaming)
    ↓
Filter by ANZSIC codes (7310: Advertising, 6940: Marketing)
    ↓
Upsert to abn_businesses table
    ↓
Queue for GMB matching
```

**Deliverable:** Working ABN ingestion with 3.5M records loaded

---

## Phase 3: Tier 2 — GMB/Ads Signals

### Components
1. `src/integrations/gmb_scraper.py` — Google Maps scraper (DIY, replaces Apify)
2. `src/integrations/meta_ads_library.py` — Meta Ad Library scraper
3. `src/engines/gmb_enrichment_worker.py` — Prefect flow

### GMB Matching Logic
```python
def match_abn_to_gmb(abn_record):
    # Search GMB by: trading_name + postcode
    # Fuzzy match: Levenshtein distance ≥ 70%
    # Return: place_id, phone, website, rating, reviews
```

### Ads Intent Signals
| Signal | Score Impact |
|--------|--------------|
| >50 active ads | +20 |
| Ad longevity >60 days | +15 |
| Multi-platform ads | +10 |
| Recent ad activity (<7 days) | +10 |

**Deliverable:** GMB enrichment for all ABN-matched businesses

---

## Phase 4: Tier 3 — Hunter.io Email

### Components
- ✅ `hunter-mcp` — Already built
- `src/engines/email_enrichment_worker.py` — Prefect flow

### Flow
```
Lead with website but no email
    ↓
Hunter.io domain search
    ↓
If confidence ≥ 70% → Store email
If confidence < 70% → Flag for ZeroBounce verification
```

**Deliverable:** Email enrichment integrated into waterfall

---

## Phase 5: Tier 4 — LinkedIn Pulse

### Components
1. `src/integrations/proxycurl.py` — Proxycurl API client
2. `src/engines/linkedin_enrichment_worker.py` — Prefect flow

### Data Points
- LinkedIn company URL
- Decision maker profiles (CEO, CMO, MD)
- Employee count
- Recent posts/activity
- Company specialties

**Deliverable:** LinkedIn enrichment for Tier 3+ leads

---

## Phase 6: Tier 5 — Identity Gold

### Components
1. `src/integrations/kaspr.py` — Kaspr API client
2. `src/integrations/lusha.py` — Lusha API client (fallback)
3. `src/engines/identity_escalation.py` — Already partially built

### Gate
**ONLY triggers when ALS ≥ 85**

### Flow
```
Lead with ALS ≥ 85 AND no mobile
    ↓
Kaspr lookup (primary)
    ↓
If fail → Lusha fallback
    ↓
Store verified mobile
```

**Deliverable:** Mobile enrichment for high-value leads only

---

## Phase 7: Waterfall Orchestrator

### Components
1. `src/engines/waterfall_orchestrator.py` — Master flow coordinator
2. Update `src/engines/scout_engine.py` — Remove Apollo dependency

### Orchestration Logic
```python
async def run_waterfall(lead_id: str):
    lead = await get_lead(lead_id)
    
    # Tier 1: ABN already seeded
    
    # Tier 2: GMB/Ads
    if not lead.phone or not lead.website:
        await enrich_gmb(lead)
        await enrich_ads_signals(lead)
    
    # Tier 3: Email
    if not lead.email and lead.website:
        await enrich_email_hunter(lead)
    
    # Tier 4: LinkedIn
    if lead.als_score >= 60:
        await enrich_linkedin(lead)
    
    # Tier 5: Mobile (GATED)
    if lead.als_score >= 85 and not lead.mobile:
        await enrich_identity_gold(lead)
    
    # Recalculate ALS
    await recalculate_als(lead)
```

**Deliverable:** Fully orchestrated waterfall replacing Apollo

---

## Phase 8: ALS Enhancement

Update ALS scoring to use Siege Waterfall signals:

| Signal | Weight |
|--------|--------|
| ABN verified | +10 |
| GMB matched (high confidence) | +15 |
| Active advertiser (>50 ads) | +20 |
| Ad longevity >60 days | +15 |
| Verified email | +10 |
| LinkedIn company found | +10 |
| Decision maker identified | +10 |
| Mobile verified | +10 |

**Deliverable:** Updated ALS algorithm in `src/scoring/als.py`

---

## Execution Order

| Phase | Description | Est. Lines | Agent Task |
|-------|-------------|------------|------------|
| 1 | Database Schema | ~100 | Migration file |
| 2 | ABN Ingestion | ~300 | Sub-agent |
| 3 | GMB/Ads Signals | ~400 | Sub-agent |
| 4 | Hunter Integration | ~100 | Sub-agent |
| 5 | LinkedIn Pulse | ~200 | Sub-agent |
| 6 | Identity Gold | ~150 | Sub-agent |
| 7 | Orchestrator | ~200 | Sub-agent |
| 8 | ALS Enhancement | ~100 | Sub-agent |

**Total estimated:** ~1,550 lines across 8 phases

---

## Dependencies

### API Keys Required
- ✅ HUNTER_API_KEY — Need to add
- ❌ PROXYCURL_API_KEY — Need to obtain
- ❌ KASPR_API_KEY — Need to obtain
- ❌ LUSHA_API_KEY — Need to obtain

### Infrastructure
- ✅ Prefect server running
- ✅ Supabase database accessible
- ❌ ABN Bulk data downloaded

---

## Success Criteria

1. ABN Bulk ingested (3.5M+ records)
2. GMB matching >60% of marketing agencies
3. Email enrichment via Hunter working
4. LinkedIn enrichment for ALS ≥60 leads
5. Mobile enrichment gated to ALS ≥85
6. Total enrichment cost <$0.10 AUD per lead (vs Apollo $0.16)
7. Apollo dependency removed from scout engine

---

*Plan created: 2026-02-05 | Ready for phased execution*
