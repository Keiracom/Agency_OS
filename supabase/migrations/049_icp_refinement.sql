-- Migration: 049_icp_refinement.sql
-- Purpose: Add WHO pattern ICP refinement tracking
-- Phase: 19 (ICP Refinement from CIS)
-- Task: Item 19
--
-- This migration adds:
-- 1. targeting_locked_fields column to clients (customer override control)
-- 2. icp_refinement_log table (transparency/audit trail for dashboard)

-- ============================================
-- 1. Add locked fields column to clients
-- ============================================
-- Allows customers to lock specific ICP fields from auto-refinement
-- e.g., ['titles', 'industries'] means those won't be auto-adjusted

ALTER TABLE clients
ADD COLUMN IF NOT EXISTS targeting_locked_fields TEXT[] DEFAULT '{}';

COMMENT ON COLUMN clients.targeting_locked_fields IS
    'ICP fields locked from WHO auto-refinement. Customer can lock: titles, industries, employee_min, employee_max';


-- ============================================
-- 2. Create ICP refinement log table
-- ============================================
-- Tracks all WHO refinements applied for transparency
-- Used by Phase H dashboard "Targeting Insights" panel

CREATE TABLE IF NOT EXISTS icp_refinement_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Foreign keys
    client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    pattern_id UUID NOT NULL REFERENCES conversion_patterns(id) ON DELETE CASCADE,

    -- What was refined
    base_criteria JSONB NOT NULL,      -- Original ICP criteria
    refined_criteria JSONB NOT NULL,   -- Final refined criteria
    refinements_applied JSONB NOT NULL, -- Array of refinement actions

    -- Pattern confidence at time of refinement
    confidence FLOAT NOT NULL,

    -- Timestamps
    applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Soft delete
    deleted_at TIMESTAMPTZ DEFAULT NULL
);

-- Indexes for efficient queries
CREATE INDEX IF NOT EXISTS idx_icp_refinement_log_client_id
    ON icp_refinement_log(client_id);

CREATE INDEX IF NOT EXISTS idx_icp_refinement_log_applied_at
    ON icp_refinement_log(applied_at DESC);

CREATE INDEX IF NOT EXISTS idx_icp_refinement_log_client_recent
    ON icp_refinement_log(client_id, applied_at DESC)
    WHERE deleted_at IS NULL;

COMMENT ON TABLE icp_refinement_log IS
    'Audit log of WHO pattern refinements applied to ICP searches. Used for transparency dashboard.';

COMMENT ON COLUMN icp_refinement_log.base_criteria IS
    'Original ICP criteria before WHO refinement';

COMMENT ON COLUMN icp_refinement_log.refined_criteria IS
    'Final criteria after WHO refinement applied';

COMMENT ON COLUMN icp_refinement_log.refinements_applied IS
    'Array of refinement actions: [{field, action, reason, ...}]';


-- ============================================
-- 3. RLS Policies
-- ============================================
-- Enable RLS on the new table
ALTER TABLE icp_refinement_log ENABLE ROW LEVEL SECURITY;

-- Policy: Users can view refinement logs for their clients
CREATE POLICY "Users can view refinement logs for their clients"
    ON icp_refinement_log
    FOR SELECT
    USING (
        client_id IN (
            SELECT client_id FROM memberships
            WHERE user_id = auth.uid()
            AND deleted_at IS NULL
        )
    );

-- Policy: Platform admins can view all refinement logs
CREATE POLICY "Platform admins can view all refinement logs"
    ON icp_refinement_log
    FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM users
            WHERE id = auth.uid()
            AND is_platform_admin = TRUE
            AND deleted_at IS NULL
        )
    );

-- Policy: Service role can insert refinement logs
CREATE POLICY "Service role can insert refinement logs"
    ON icp_refinement_log
    FOR INSERT
    WITH CHECK (TRUE);


-- ============================================
-- 4. Helper view for dashboard
-- ============================================
-- Aggregated view for "Targeting Insights" panel

CREATE OR REPLACE VIEW v_client_refinement_summary AS
SELECT
    client_id,
    COUNT(*) as total_refinements,
    COUNT(*) FILTER (WHERE applied_at > NOW() - INTERVAL '30 days') as refinements_last_30d,
    AVG(confidence) as avg_confidence,
    MAX(applied_at) as last_refinement_at,
    (
        SELECT jsonb_agg(DISTINCT field)
        FROM icp_refinement_log irl,
        LATERAL jsonb_array_elements(refinements_applied) as r(elem),
        LATERAL (SELECT r.elem->>'field' as field) f
        WHERE irl.client_id = icp_refinement_log.client_id
        AND irl.applied_at > NOW() - INTERVAL '30 days'
        AND irl.deleted_at IS NULL
    ) as fields_refined_last_30d
FROM icp_refinement_log
WHERE deleted_at IS NULL
GROUP BY client_id;

COMMENT ON VIEW v_client_refinement_summary IS
    'Aggregated refinement stats per client for dashboard display';


-- ============================================
-- VERIFICATION
-- ============================================
-- Verify migration applied correctly
DO $$
BEGIN
    -- Check column exists
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'clients'
        AND column_name = 'targeting_locked_fields'
    ) THEN
        RAISE EXCEPTION 'Migration failed: targeting_locked_fields column not created';
    END IF;

    -- Check table exists
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.tables
        WHERE table_name = 'icp_refinement_log'
    ) THEN
        RAISE EXCEPTION 'Migration failed: icp_refinement_log table not created';
    END IF;

    RAISE NOTICE 'Migration 049_icp_refinement.sql completed successfully';
END $$;
