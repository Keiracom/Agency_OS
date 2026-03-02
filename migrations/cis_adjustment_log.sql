-- CIS Learning Engine: Weight Adjustment Log
-- Directive #147: Full audit trail for all weight changes

CREATE TABLE IF NOT EXISTS cis_adjustment_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id UUID REFERENCES customers(id),
    run_timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    signal_name TEXT NOT NULL,
    weight_before INTEGER NOT NULL,
    delta_applied INTEGER NOT NULL,
    weight_after INTEGER NOT NULL,
    confidence_score NUMERIC(3,2) NOT NULL,  -- 0.00 to 1.00
    outcome_sample_size INTEGER NOT NULL,
    skipped BOOLEAN NOT NULL DEFAULT FALSE,
    skip_reason TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Index for querying by customer and time
CREATE INDEX idx_cis_adjustment_customer_time ON cis_adjustment_log(customer_id, run_timestamp DESC);

-- Index for signal analysis
CREATE INDEX idx_cis_adjustment_signal ON cis_adjustment_log(signal_name);

COMMENT ON TABLE cis_adjustment_log IS 'Directive #147: Audit trail for CIS weight adjustments. Never destructive.';
