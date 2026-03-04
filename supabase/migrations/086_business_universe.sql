-- Migration 086: business_universe table
-- Canonical table of every legitimate active Australian business
-- Foundation for all campaign discovery

CREATE TABLE IF NOT EXISTS business_universe (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    abn TEXT UNIQUE NOT NULL,
    acn TEXT,
    legal_name TEXT NOT NULL,
    trading_name TEXT,
    entity_type TEXT NOT NULL,
    entity_type_code TEXT NOT NULL,
    state TEXT,
    postcode TEXT,
    gst_registered BOOLEAN DEFAULT FALSE,
    status TEXT NOT NULL DEFAULT 'active',
    abn_status_code TEXT,
    registration_date DATE,
    last_abr_check TIMESTAMPTZ DEFAULT now(),
    
    -- Enrichment status flags (populated later)
    gmb_enriched_at TIMESTAMPTZ,
    linkedin_enriched_at TIMESTAMPTZ,
    
    -- Record metadata
    abr_last_updated TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- Indexes
CREATE INDEX idx_bu_state ON business_universe(state);
CREATE INDEX idx_bu_entity_type ON business_universe(entity_type_code);
CREATE INDEX idx_bu_status ON business_universe(status);
CREATE INDEX idx_bu_trading_name ON business_universe(trading_name);
CREATE INDEX idx_bu_postcode ON business_universe(postcode);
