-- CIS Learning Engine: Canonical Outcomes Table
-- Directive #147: cis_outcome_schema_v3

-- Outcome type enum
DO $$ BEGIN
    CREATE TYPE outcome_type AS ENUM (
        'booked',
        'replied_positive',
        'replied_neutral', 
        'replied_negative',
        'unsubscribed',
        'bounced',
        'no_response'
    );
EXCEPTION
    WHEN duplicate_object THEN NULL;
END $$;

-- Channel converted enum
DO $$ BEGIN
    CREATE TYPE channel_converted_type AS ENUM (
        'email',
        'linkedin',
        'sms',
        'voice'
    );
EXCEPTION
    WHEN duplicate_object THEN NULL;
END $$;

-- Hook source enum
DO $$ BEGIN
    CREATE TYPE hook_source_type AS ENUM (
        'dm_linkedin_posts',
        'company_linkedin_posts',
        'gmb_reviews',
        'x_posts',
        'none'
    );
EXCEPTION
    WHEN duplicate_object THEN NULL;
END $$;

CREATE TABLE IF NOT EXISTS outcomes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id UUID REFERENCES customers(id),
    lead_id UUID NOT NULL,
    campaign_id UUID,
    
    -- Outcome classification
    outcome_type outcome_type NOT NULL,
    channel_converted channel_converted_type,
    sequence_position INTEGER,
    hook_source hook_source_type,
    
    -- Scores at time of send (for CIS learning)
    reachability_at_send INTEGER,
    propensity_at_send INTEGER,
    
    -- Active signals at time of send (for CIS learning)
    signals_active JSONB,  -- {"hiring": true, "recent_funding": true, "dm_posts": 3, ...}
    
    -- Metadata
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes for CIS analysis
CREATE INDEX IF NOT EXISTS idx_outcomes_customer_created ON outcomes(customer_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_outcomes_type ON outcomes(outcome_type);
CREATE INDEX IF NOT EXISTS idx_outcomes_signals ON outcomes USING GIN(signals_active);

COMMENT ON TABLE outcomes IS 'Directive #147: Canonical outcomes table for CIS Learning Engine (schema v3)';
