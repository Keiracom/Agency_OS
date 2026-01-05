# Database: Leads & Suppression

**Migration:** `004_leads_suppression.sql`

---

## Leads Table

```sql
CREATE TABLE leads (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id UUID NOT NULL REFERENCES clients(id),
    campaign_id UUID NOT NULL REFERENCES campaigns(id),
    email TEXT NOT NULL,
    phone TEXT,
    first_name TEXT,
    last_name TEXT,
    title TEXT,
    company TEXT,
    linkedin_url TEXT,
    domain TEXT,
    
    -- ALS Score components
    als_score INTEGER,
    als_tier TEXT,
    als_data_quality INTEGER,
    als_authority INTEGER,
    als_company_fit INTEGER,
    als_timing INTEGER,
    als_risk INTEGER,
    als_components JSONB,           -- Full breakdown (Phase 16)
    als_weights_used JSONB,         -- Weights used for scoring (Phase 16)
    scored_at TIMESTAMPTZ,          -- When last scored (Phase 16)
    
    -- Organization data
    organization_industry TEXT,
    organization_employee_count INTEGER,
    organization_country TEXT,
    organization_founded_year INTEGER,
    organization_is_hiring BOOLEAN,
    organization_latest_funding_date DATE,
    employment_start_date DATE,
    
    -- DataForSEO enrichment (Phase 17)
    dataforseo_domain_rank INTEGER,
    dataforseo_organic_traffic INTEGER,
    dataforseo_top10_keywords INTEGER,
    dataforseo_spam_score FLOAT,
    dataforseo_enriched_at TIMESTAMPTZ,
    
    -- Status
    status lead_status DEFAULT 'new',
    dncr_checked BOOLEAN DEFAULT FALSE,
    enrichment_source TEXT,
    enrichment_confidence FLOAT,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    deleted_at TIMESTAMPTZ,
    
    -- CRITICAL: Compound uniqueness per client
    CONSTRAINT unique_lead_per_client UNIQUE (client_id, email)
);

-- Indexes
CREATE INDEX idx_leads_client_email ON leads(client_id, email);
CREATE INDEX idx_leads_campaign ON leads(campaign_id);
CREATE INDEX idx_leads_status ON leads(status);
CREATE INDEX idx_leads_als ON leads(als_score DESC);
CREATE INDEX idx_leads_domain ON leads(domain);
```

---

## ALS Tiers (CRITICAL)

| Tier | Score Range | Channels Available |
|------|-------------|-------------------|
| **Hot** | 85-100 | Email, SMS, LinkedIn, Voice, Direct Mail |
| **Warm** | 60-84 | Email, LinkedIn, Voice |
| **Cool** | 35-59 | Email, LinkedIn |
| **Cold** | 20-34 | Email only |
| **Dead** | <20 | None (suppress) |

**IMPORTANT:** Hot starts at 85, NOT 80.

---

## Global Suppression Table

```sql
CREATE TABLE global_suppression (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email TEXT NOT NULL UNIQUE,
    reason TEXT NOT NULL,
    added_by TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_suppression_email ON global_suppression(email);
```

---

## ALS Score Components

| Component | Max Points | Description |
|-----------|------------|-------------|
| Data Quality | 20 | Email verified (8), phone (6), LinkedIn (4), personal email (2) |
| Authority | 25 | Owner/CEO (25), C-suite (22), VP (18), Director (15), Manager (7-10) |
| Company Fit | 25 | Industry (10), employee 5-50 (5), Australia (5), DataForSEO (5) |
| Timing | 15 | New role <6mo (6), hiring (5), funded <12mo (4) |
| Risk | 15 | Deductions for bounced, unsubscribed, competitor, bad title, no web presence |

See `docs/specs/engines/SCORER_ENGINE.md` for full formula.
