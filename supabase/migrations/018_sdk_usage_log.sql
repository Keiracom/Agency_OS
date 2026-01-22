-- Migration: 018_sdk_usage_log.sql
-- Purpose: Track SDK Brain usage for cost control and analytics
-- Created: 2026-01-18

-- SDK usage log table - tracks every SDK agent execution
CREATE TABLE IF NOT EXISTS sdk_usage_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Context
    client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    lead_id UUID REFERENCES leads(id) ON DELETE SET NULL,
    campaign_id UUID REFERENCES campaigns(id) ON DELETE SET NULL,
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,

    -- Agent info
    agent_type VARCHAR(50) NOT NULL,  -- icp_extraction, enrichment, email, voice_kb, objection
    model_used VARCHAR(100) NOT NULL,  -- claude-sonnet-4-20250514, etc.

    -- Cost tracking (AUD)
    input_tokens INT NOT NULL DEFAULT 0,
    output_tokens INT NOT NULL DEFAULT 0,
    cached_tokens INT NOT NULL DEFAULT 0,
    cost_aud DECIMAL(10, 6) NOT NULL DEFAULT 0,

    -- Execution metrics
    turns_used INT NOT NULL DEFAULT 1,
    duration_ms INT NOT NULL DEFAULT 0,
    tool_calls JSONB DEFAULT '[]'::jsonb,

    -- Status
    success BOOLEAN NOT NULL DEFAULT true,
    error_message TEXT,

    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Soft delete
    deleted_at TIMESTAMPTZ
);

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_sdk_usage_client ON sdk_usage_log(client_id) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_sdk_usage_lead ON sdk_usage_log(lead_id) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_sdk_usage_agent ON sdk_usage_log(agent_type) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_sdk_usage_created ON sdk_usage_log(created_at) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_sdk_usage_date ON sdk_usage_log(DATE(created_at)) WHERE deleted_at IS NULL;

-- Daily spend tracking view
CREATE OR REPLACE VIEW sdk_daily_spend AS
SELECT
    client_id,
    DATE(created_at) AS spend_date,
    agent_type,
    COUNT(*) AS execution_count,
    SUM(input_tokens) AS total_input_tokens,
    SUM(output_tokens) AS total_output_tokens,
    SUM(cached_tokens) AS total_cached_tokens,
    SUM(cost_aud) AS total_cost_aud,
    AVG(turns_used) AS avg_turns,
    AVG(duration_ms) AS avg_duration_ms,
    COUNT(*) FILTER (WHERE success = true) AS success_count,
    COUNT(*) FILTER (WHERE success = false) AS failure_count
FROM sdk_usage_log
WHERE deleted_at IS NULL
GROUP BY client_id, DATE(created_at), agent_type;

-- RLS Policies
ALTER TABLE sdk_usage_log ENABLE ROW LEVEL SECURITY;

-- Platform admins can see all usage
CREATE POLICY sdk_usage_platform_admin ON sdk_usage_log
    FOR ALL
    TO authenticated
    USING (
        EXISTS (
            SELECT 1 FROM users u
            WHERE u.id = auth.uid()
            AND u.is_platform_admin = true
        )
    );

-- Client members can see their client's usage
CREATE POLICY sdk_usage_client_member ON sdk_usage_log
    FOR SELECT
    TO authenticated
    USING (
        EXISTS (
            SELECT 1 FROM client_memberships cm
            WHERE cm.user_id = auth.uid()
            AND cm.client_id = sdk_usage_log.client_id
            AND cm.deleted_at IS NULL
        )
    );

-- Comment
COMMENT ON TABLE sdk_usage_log IS 'Tracks Claude Agent SDK usage for cost control and analytics';
COMMENT ON COLUMN sdk_usage_log.agent_type IS 'Type of SDK agent: icp_extraction, enrichment, email, voice_kb, objection';
COMMENT ON COLUMN sdk_usage_log.cost_aud IS 'Total cost in Australian dollars';
COMMENT ON COLUMN sdk_usage_log.tool_calls IS 'Array of tool calls made during execution';
