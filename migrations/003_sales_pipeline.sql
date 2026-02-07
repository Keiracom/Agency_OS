-- Migration: Sales Pipeline Schema
-- Created: 2026-02-07
-- Purpose: Track leads through sales funnel stages

-- Create enum for pipeline stages
CREATE TYPE sales_stage AS ENUM (
    'prospect',
    'contacted', 
    'demo_booked',
    'demo_done',
    'proposal_sent',
    'negotiation',
    'closed_won',
    'closed_lost'
);

-- Main sales pipeline table
CREATE TABLE IF NOT EXISTS sales_pipeline (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    lead_id UUID NOT NULL REFERENCES leads(id) ON DELETE CASCADE,
    stage sales_stage NOT NULL DEFAULT 'prospect',
    next_action TEXT,
    next_action_date TIMESTAMPTZ,
    assigned_to TEXT, -- User email or ID
    deal_value_aud DECIMAL(12, 2),
    probability INTEGER CHECK (probability >= 0 AND probability <= 100),
    loss_reason TEXT,
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    closed_at TIMESTAMPTZ,
    
    CONSTRAINT valid_loss_reason CHECK (
        (stage = 'closed_lost' AND loss_reason IS NOT NULL) OR
        (stage != 'closed_lost')
    )
);

-- Stage history for tracking progression
CREATE TABLE IF NOT EXISTS sales_pipeline_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pipeline_id UUID NOT NULL REFERENCES sales_pipeline(id) ON DELETE CASCADE,
    from_stage sales_stage,
    to_stage sales_stage NOT NULL,
    changed_by TEXT,
    changed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    notes TEXT
);

-- Indexes for common queries
CREATE INDEX idx_sales_pipeline_lead_id ON sales_pipeline(lead_id);
CREATE INDEX idx_sales_pipeline_stage ON sales_pipeline(stage);
CREATE INDEX idx_sales_pipeline_assigned ON sales_pipeline(assigned_to);
CREATE INDEX idx_sales_pipeline_next_action ON sales_pipeline(next_action_date) WHERE next_action_date IS NOT NULL;
CREATE INDEX idx_pipeline_history_pipeline ON sales_pipeline_history(pipeline_id);

-- Auto-update updated_at trigger
CREATE OR REPLACE FUNCTION update_sales_pipeline_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    IF NEW.stage IN ('closed_won', 'closed_lost') AND OLD.stage NOT IN ('closed_won', 'closed_lost') THEN
        NEW.closed_at = NOW();
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_sales_pipeline_updated
    BEFORE UPDATE ON sales_pipeline
    FOR EACH ROW
    EXECUTE FUNCTION update_sales_pipeline_timestamp();

-- Stage change history trigger
CREATE OR REPLACE FUNCTION log_stage_change()
RETURNS TRIGGER AS $$
BEGIN
    IF OLD.stage IS DISTINCT FROM NEW.stage THEN
        INSERT INTO sales_pipeline_history (pipeline_id, from_stage, to_stage, changed_by)
        VALUES (NEW.id, OLD.stage, NEW.stage, NEW.assigned_to);
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_log_stage_change
    AFTER UPDATE ON sales_pipeline
    FOR EACH ROW
    EXECUTE FUNCTION log_stage_change();

-- RLS Policies
ALTER TABLE sales_pipeline ENABLE ROW LEVEL SECURITY;
ALTER TABLE sales_pipeline_history ENABLE ROW LEVEL SECURITY;

-- View: Pipeline Summary Stats
CREATE OR REPLACE VIEW sales_pipeline_summary AS
SELECT 
    stage,
    COUNT(*) as count,
    COALESCE(SUM(deal_value_aud), 0) as total_value,
    COALESCE(AVG(deal_value_aud), 0) as avg_value,
    AVG(probability) as avg_probability
FROM sales_pipeline
WHERE stage NOT IN ('closed_won', 'closed_lost')
GROUP BY stage
ORDER BY 
    CASE stage
        WHEN 'prospect' THEN 1
        WHEN 'contacted' THEN 2
        WHEN 'demo_booked' THEN 3
        WHEN 'demo_done' THEN 4
        WHEN 'proposal_sent' THEN 5
        WHEN 'negotiation' THEN 6
    END;

-- Comments
COMMENT ON TABLE sales_pipeline IS 'Tracks leads through sales stages from prospect to close';
COMMENT ON TABLE sales_pipeline_history IS 'Audit log of stage transitions';
COMMENT ON COLUMN sales_pipeline.deal_value_aud IS 'Expected deal value in AUD (Australia First)';
