-- Migration 087: business_decision_makers table
-- DM contact data with confidence scoring and freshness timestamps
-- Mobile is NEVER stored here — live lookup only

CREATE TABLE IF NOT EXISTS business_decision_makers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    business_universe_id UUID NOT NULL REFERENCES business_universe(id) ON DELETE CASCADE,
    
    -- Identity anchor (permanent)
    linkedin_url TEXT,
    
    -- Profile fields (90 day confidence window)
    name TEXT,
    title TEXT,
    seniority TEXT,
    dm_enriched_at TIMESTAMPTZ,
    
    -- Contact fields
    email TEXT,
    email_confidence FLOAT,
    email_verified_at TIMESTAMPTZ,
    -- mobile is NEVER stored here — live lookup only
    -- at campaign time for ALS >= 85
    
    -- Status
    is_current BOOLEAN DEFAULT TRUE,
    last_verified_at TIMESTAMPTZ,
    
    -- CIS outcome history (populated by campaign activity)
    last_outreach_at TIMESTAMPTZ,
    last_outcome TEXT,
    total_outreach_count INTEGER DEFAULT 0,
    
    -- Metadata
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- Indexes
CREATE INDEX idx_bdm_business_id ON business_decision_makers(business_universe_id);
CREATE INDEX idx_bdm_linkedin_url ON business_decision_makers(linkedin_url);
CREATE INDEX idx_bdm_is_current ON business_decision_makers(is_current);

-- Comments
COMMENT ON COLUMN business_decision_makers.linkedin_url IS 'Permanent anchor — persists even when person changes jobs. Primary join key for re-verification.';
COMMENT ON TABLE business_decision_makers IS 'Mobile numbers are NEVER stored here. Always live Leadmagic lookup at campaign time for ALS >= 85 only. Too perishable to cache.';
