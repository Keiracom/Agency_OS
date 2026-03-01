-- ============================================================================
-- Migration: 076_cis_learning_engine.sql
-- Directive #147: CIS Learning Engine tables
-- Purpose: Store weight adjustments and run logs for continuous improvement
-- ============================================================================

-- CIS Adjustment Log: Audit trail of all weight changes
CREATE TABLE IF NOT EXISTS cis_adjustment_log (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    customer_id UUID REFERENCES customers(id) ON DELETE CASCADE,  -- NULL = global weights
    signal_name TEXT NOT NULL,
    weight_before INTEGER NOT NULL,
    delta_applied INTEGER NOT NULL,
    weight_after INTEGER NOT NULL,
    confidence_score NUMERIC(4,3) NOT NULL,  -- 0.000 to 1.000
    outcome_sample_size INTEGER NOT NULL,
    skipped BOOLEAN DEFAULT FALSE,
    skip_reason TEXT,
    run_id UUID,  -- Links to cis_run_log
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- CIS Run Log: Track each CIS execution
CREATE TABLE IF NOT EXISTS cis_run_log (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    run_type TEXT NOT NULL DEFAULT 'weekly',  -- weekly, manual, triggered
    customer_id UUID REFERENCES customers(id) ON DELETE CASCADE,  -- NULL = global
    status TEXT NOT NULL DEFAULT 'pending',  -- pending, running, complete, failed
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    outcomes_analyzed INTEGER DEFAULT 0,
    adjustments_applied INTEGER DEFAULT 0,
    summary TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Add foreign key from adjustment_log to run_log
ALTER TABLE cis_adjustment_log
    ADD CONSTRAINT fk_cis_adjustment_run
    FOREIGN KEY (run_id) REFERENCES cis_run_log(id) ON DELETE SET NULL;

-- Indexes for efficient queries
CREATE INDEX IF NOT EXISTS idx_cis_adjustment_log_signal
    ON cis_adjustment_log(signal_name);

CREATE INDEX IF NOT EXISTS idx_cis_adjustment_log_created
    ON cis_adjustment_log(created_at DESC);

CREATE INDEX IF NOT EXISTS idx_cis_adjustment_log_run
    ON cis_adjustment_log(run_id);

CREATE INDEX IF NOT EXISTS idx_cis_adjustment_log_customer
    ON cis_adjustment_log(customer_id)
    WHERE customer_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_cis_run_log_status
    ON cis_run_log(status);

CREATE INDEX IF NOT EXISTS idx_cis_run_log_completed
    ON cis_run_log(completed_at DESC);

CREATE INDEX IF NOT EXISTS idx_cis_run_log_customer
    ON cis_run_log(customer_id)
    WHERE customer_id IS NOT NULL;

-- Add signals_active column to leads table if not exists
-- This stores the active buyer signals for propensity calculation
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'leads' AND column_name = 'signals_active'
    ) THEN
        ALTER TABLE leads ADD COLUMN signals_active JSONB DEFAULT '[]'::JSONB;
    END IF;
END $$;

-- Create index on signals_active for CIS queries
CREATE INDEX IF NOT EXISTS idx_leads_signals_active
    ON leads USING GIN (signals_active);

-- Ensure ceo_memory table exists for propensity weights storage
CREATE TABLE IF NOT EXISTS ceo_memory (
    key TEXT PRIMARY KEY,
    value JSONB NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Insert default propensity weights if not exists
INSERT INTO ceo_memory (key, value)
VALUES (
    'ceo:propensity_weights_v3',
    '{
        "weights": {
            "no_seo": 10,
            "new_dm_6mo": 15,
            "low_gmb_rating": 10,
            "active_ad_spend": 15,
            "growing_signals": 10,
            "pain_point_post": 20,
            "hiring_marketing": 10,
            "outdated_website": 10,
            "poor_digital_presence": 20,
            "negative_marketing_review": 10
        },
        "negative": {
            "competitor": -25,
            "enterprise_200plus": -15,
            "large_internal_team": -20,
            "recently_signed_agency": -15
        }
    }'::JSONB
)
ON CONFLICT (key) DO NOTHING;

-- Comments for documentation
COMMENT ON TABLE cis_adjustment_log IS 'Directive #147: Audit trail of CIS weight adjustments';
COMMENT ON TABLE cis_run_log IS 'Directive #147: CIS Learning Engine execution history';
COMMENT ON COLUMN cis_adjustment_log.confidence_score IS 'Claude analysis confidence (0.0-1.0), adjustments < 0.7 are skipped';
COMMENT ON COLUMN cis_adjustment_log.skip_reason IS 'Reason for skipping adjustment (low confidence, etc.)';
COMMENT ON COLUMN cis_run_log.run_type IS 'weekly (scheduled), manual (on-demand), triggered (event-based)';
