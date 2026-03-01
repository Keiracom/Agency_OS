-- Siege Waterfall V3 Schema Updates (Directive #144)
-- CIS Outcome Tracking + Dual Scoring Fields

-- ============================================
-- LEAD_POOL TABLE UPDATES
-- ============================================

-- Add dual scoring fields to lead_pool
ALTER TABLE lead_pool
ADD COLUMN IF NOT EXISTS reachability_score INTEGER,
ADD COLUMN IF NOT EXISTS propensity_score INTEGER,
ADD COLUMN IF NOT EXISTS priority_rank INTEGER,
ADD COLUMN IF NOT EXISTS priority_reason TEXT,
ADD COLUMN IF NOT EXISTS dual_scored_at TIMESTAMPTZ;

-- Add indexes for dual scoring
CREATE INDEX IF NOT EXISTS idx_lead_pool_reachability ON lead_pool(reachability_score);
CREATE INDEX IF NOT EXISTS idx_lead_pool_propensity ON lead_pool(propensity_score);
CREATE INDEX IF NOT EXISTS idx_lead_pool_priority_rank ON lead_pool(priority_rank);

-- ============================================
-- CIS OUTCOME TRACKING TABLE
-- ============================================

CREATE TABLE IF NOT EXISTS cis_outcomes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Lead reference
    lead_pool_id UUID NOT NULL REFERENCES lead_pool(id),
    campaign_id UUID REFERENCES campaigns(id),
    client_id UUID REFERENCES clients(id),
    
    -- Outcome data
    outcome_type TEXT NOT NULL,  -- 'positive_reply', 'meeting_booked', 'deal_closed', 'unsubscribe', 'bounce', 'no_response'
    channel_converted TEXT,  -- 'email', 'linkedin', 'sms', 'voice', 'mail'
    sequence_position INTEGER,  -- Which step in sequence led to conversion
    hook_source TEXT,  -- 'dm_linkedin_posts', 'company_linkedin_posts', 'gmb_reviews', 'x_posts', 'none'
    
    -- Scores at time of send (for learning)
    reachability_at_send INTEGER,
    propensity_at_send INTEGER,
    
    -- Active signals at time of send (for learning)
    signals_active JSONB,  -- {"hiring": true, "recent_funding": true, "dm_posts": 3, ...}
    
    -- Metadata
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- Soft delete
    deleted_at TIMESTAMPTZ
);

-- Indexes for CIS outcome analysis
CREATE INDEX IF NOT EXISTS idx_cis_outcomes_lead_pool ON cis_outcomes(lead_pool_id);
CREATE INDEX IF NOT EXISTS idx_cis_outcomes_campaign ON cis_outcomes(campaign_id);
CREATE INDEX IF NOT EXISTS idx_cis_outcomes_outcome_type ON cis_outcomes(outcome_type);
CREATE INDEX IF NOT EXISTS idx_cis_outcomes_channel ON cis_outcomes(channel_converted);
CREATE INDEX IF NOT EXISTS idx_cis_outcomes_hook_source ON cis_outcomes(hook_source);
CREATE INDEX IF NOT EXISTS idx_cis_outcomes_created ON cis_outcomes(created_at);

-- ============================================
-- CEO MEMORY: PROPENSITY WEIGHTS V3
-- ============================================

-- Insert default weights (DO NOT hardcode in code!)
INSERT INTO ceo_memory (key, value, created_at, updated_at)
VALUES (
    'ceo:propensity_weights_v3',
    '{
        "reachability": {
            "verified_email": 35,
            "dm_confirmed": 30,
            "direct_mobile": 25,
            "linkedin_url": 10
        },
        "propensity": {
            "industry_match": 15,
            "company_size_fit": 10,
            "authority_level": 20,
            "timing_signals": 15,
            "engagement_signals": 25,
            "buyer_history": 15
        }
    }'::jsonb,
    NOW(),
    NOW()
)
ON CONFLICT (key) DO UPDATE
SET value = EXCLUDED.value,
    updated_at = NOW();

-- ============================================
-- COMMENTS
-- ============================================

COMMENT ON TABLE cis_outcomes IS 'CIS (Conversion Intelligence System) outcome tracking for Siege Waterfall v3';
COMMENT ON COLUMN cis_outcomes.outcome_type IS 'Type of outcome: positive_reply, meeting_booked, deal_closed, unsubscribe, bounce, no_response';
COMMENT ON COLUMN cis_outcomes.channel_converted IS 'Which channel led to conversion: email, linkedin, sms, voice, mail';
COMMENT ON COLUMN cis_outcomes.hook_source IS 'Which data source provided the hook: dm_linkedin_posts, company_linkedin_posts, gmb_reviews, x_posts, none';
COMMENT ON COLUMN cis_outcomes.signals_active IS 'JSON of active signals at send time for learning';
COMMENT ON COLUMN lead_pool.reachability_score IS 'Reachability score 0-100: Can we reach them?';
COMMENT ON COLUMN lead_pool.propensity_score IS 'Propensity score 0-100+: Will they buy?';
COMMENT ON COLUMN lead_pool.priority_rank IS 'Priority rank within batch (1 = highest priority)';
COMMENT ON COLUMN lead_pool.priority_reason IS 'Plain-English reason for priority (no raw scores exposed)';
