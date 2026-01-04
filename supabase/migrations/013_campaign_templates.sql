-- Migration: 013_campaign_templates.sql
-- Task: CAM-005
-- Phase: 12A (Campaign Generation - Core)
-- Purpose: Store generated campaign templates for reuse
-- Created: December 25, 2025

-- ============================================
-- CAMPAIGN TEMPLATES TABLE
-- ============================================

-- Store generated campaign templates for reuse
CREATE TABLE IF NOT EXISTS campaign_templates (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v7(),
    client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,

    -- Template info
    name TEXT NOT NULL,
    industry TEXT NOT NULL,

    -- Sequence (SequenceBuilderOutput as JSONB)
    -- Contains: sequence_name, total_days, total_touches, touches, adaptive_rules, channel_summary
    sequence JSONB NOT NULL,

    -- Messaging per touch (dict of MessagingGeneratorOutput as JSONB)
    -- Keyed by messaging_key (e.g., "touch_1_email")
    messaging JSONB NOT NULL,

    -- Source ICP (optional reference)
    source_icp_profile JSONB,

    -- Campaign configuration
    lead_allocation INTEGER NOT NULL DEFAULT 0,
    priority INTEGER NOT NULL DEFAULT 1,
    messaging_focus TEXT,

    -- Status
    status TEXT NOT NULL DEFAULT 'draft'
        CHECK (status IN ('draft', 'active', 'paused', 'archived')),

    -- Metadata
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ,  -- Soft delete (Rule 14)

    -- Unique constraint (per client, excluding soft-deleted)
    CONSTRAINT unique_client_template UNIQUE NULLS NOT DISTINCT (client_id, name, deleted_at)
);

-- Add comment for documentation
COMMENT ON TABLE campaign_templates IS 'Generated campaign templates from ICP for reuse';
COMMENT ON COLUMN campaign_templates.sequence IS 'SequenceBuilderOutput: touches with timing, channels, conditions';
COMMENT ON COLUMN campaign_templates.messaging IS 'MessagingGeneratorOutput keyed by touch (touch_1_email, etc.)';

-- ============================================
-- INDEXES
-- ============================================

-- Index for quick lookup by client (excluding soft-deleted)
CREATE INDEX IF NOT EXISTS idx_campaign_templates_client
    ON campaign_templates(client_id)
    WHERE deleted_at IS NULL;

-- Index for status filtering
CREATE INDEX IF NOT EXISTS idx_campaign_templates_status
    ON campaign_templates(status)
    WHERE deleted_at IS NULL;

-- Index for industry filtering
CREATE INDEX IF NOT EXISTS idx_campaign_templates_industry
    ON campaign_templates(industry)
    WHERE deleted_at IS NULL;

-- Combined index for common query pattern
CREATE INDEX IF NOT EXISTS idx_campaign_templates_client_status
    ON campaign_templates(client_id, status)
    WHERE deleted_at IS NULL;

-- ============================================
-- ROW LEVEL SECURITY
-- ============================================

ALTER TABLE campaign_templates ENABLE ROW LEVEL SECURITY;

-- Policy: Clients can view their own templates
CREATE POLICY "Clients can view own templates"
    ON campaign_templates
    FOR SELECT
    USING (
        client_id IN (
            SELECT client_id FROM memberships
            WHERE user_id = auth.uid()
            AND deleted_at IS NULL
        )
    );

-- Policy: Clients can insert their own templates
CREATE POLICY "Clients can insert own templates"
    ON campaign_templates
    FOR INSERT
    WITH CHECK (
        client_id IN (
            SELECT client_id FROM memberships
            WHERE user_id = auth.uid()
            AND deleted_at IS NULL
        )
    );

-- Policy: Clients can update their own templates
CREATE POLICY "Clients can update own templates"
    ON campaign_templates
    FOR UPDATE
    USING (
        client_id IN (
            SELECT client_id FROM memberships
            WHERE user_id = auth.uid()
            AND deleted_at IS NULL
        )
    );

-- Policy: Clients can soft-delete their own templates
CREATE POLICY "Clients can delete own templates"
    ON campaign_templates
    FOR DELETE
    USING (
        client_id IN (
            SELECT client_id FROM memberships
            WHERE user_id = auth.uid()
            AND role IN ('owner', 'admin')
            AND deleted_at IS NULL
        )
    );

-- Policy: Platform admins can view all templates
CREATE POLICY "Platform admins can view all templates"
    ON campaign_templates
    FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM users
            WHERE id = auth.uid()
            AND is_platform_admin = true
        )
    );

-- ============================================
-- TRIGGERS
-- ============================================

-- Trigger to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_campaign_templates_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_campaign_templates_updated_at
    BEFORE UPDATE ON campaign_templates
    FOR EACH ROW
    EXECUTE FUNCTION update_campaign_templates_updated_at();

-- ============================================
-- HELPER FUNCTIONS
-- ============================================

-- Function to create campaign template from generation result
CREATE OR REPLACE FUNCTION create_campaign_template(
    p_client_id UUID,
    p_name TEXT,
    p_industry TEXT,
    p_sequence JSONB,
    p_messaging JSONB,
    p_source_icp JSONB DEFAULT NULL,
    p_lead_allocation INTEGER DEFAULT 0,
    p_priority INTEGER DEFAULT 1,
    p_messaging_focus TEXT DEFAULT NULL
)
RETURNS UUID AS $$
DECLARE
    v_template_id UUID;
BEGIN
    INSERT INTO campaign_templates (
        client_id,
        name,
        industry,
        sequence,
        messaging,
        source_icp_profile,
        lead_allocation,
        priority,
        messaging_focus,
        status
    ) VALUES (
        p_client_id,
        p_name,
        p_industry,
        p_sequence,
        p_messaging,
        p_source_icp,
        p_lead_allocation,
        p_priority,
        p_messaging_focus,
        'draft'
    )
    RETURNING id INTO v_template_id;

    RETURN v_template_id;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Function to launch campaign from template
CREATE OR REPLACE FUNCTION launch_campaign_from_template(
    p_template_id UUID,
    p_campaign_name TEXT DEFAULT NULL
)
RETURNS UUID AS $$
DECLARE
    v_template RECORD;
    v_campaign_id UUID;
    v_sequence_step JSONB;
    v_step_number INTEGER := 1;
BEGIN
    -- Get template
    SELECT * INTO v_template
    FROM campaign_templates
    WHERE id = p_template_id AND deleted_at IS NULL;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Template not found: %', p_template_id;
    END IF;

    -- Create campaign
    INSERT INTO campaigns (
        client_id,
        name,
        status,
        permission_mode,
        settings
    ) VALUES (
        v_template.client_id,
        COALESCE(p_campaign_name, v_template.name || ' - ' || TO_CHAR(NOW(), 'YYYY-MM-DD')),
        'draft',
        'autopilot',
        jsonb_build_object(
            'source_template_id', p_template_id,
            'industry', v_template.industry,
            'messaging_focus', v_template.messaging_focus
        )
    )
    RETURNING id INTO v_campaign_id;

    -- Create sequence steps from template
    FOR v_sequence_step IN SELECT * FROM jsonb_array_elements(v_template.sequence->'touches')
    LOOP
        INSERT INTO campaign_sequences (
            campaign_id,
            step_number,
            channel,
            delay_days,
            template,
            conditions
        ) VALUES (
            v_campaign_id,
            v_step_number,
            v_sequence_step->>'channel',
            (v_sequence_step->>'day')::INTEGER,
            v_template.messaging->>(v_sequence_step->>'messaging_key'),
            jsonb_build_object(
                'condition', v_sequence_step->>'condition',
                'skip_if', v_sequence_step->>'skip_if',
                'purpose', v_sequence_step->>'purpose'
            )
        );
        v_step_number := v_step_number + 1;
    END LOOP;

    -- Mark template as active (it's being used)
    UPDATE campaign_templates
    SET status = 'active'
    WHERE id = p_template_id;

    RETURN v_campaign_id;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Function to soft delete template
CREATE OR REPLACE FUNCTION soft_delete_campaign_template(
    p_template_id UUID
)
RETURNS BOOLEAN AS $$
BEGIN
    UPDATE campaign_templates
    SET deleted_at = NOW(),
        status = 'archived'
    WHERE id = p_template_id
    AND deleted_at IS NULL;

    RETURN FOUND;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- ============================================
-- GRANTS
-- ============================================

-- Grant access to authenticated users
GRANT SELECT, INSERT, UPDATE ON campaign_templates TO authenticated;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO authenticated;

-- Grant function access
GRANT EXECUTE ON FUNCTION create_campaign_template TO authenticated;
GRANT EXECUTE ON FUNCTION launch_campaign_from_template TO authenticated;
GRANT EXECUTE ON FUNCTION soft_delete_campaign_template TO authenticated;

-- ============================================
-- VERIFICATION
-- ============================================
-- Run these queries to verify the migration:
--
-- SELECT table_name FROM information_schema.tables
-- WHERE table_name = 'campaign_templates';
--
-- SELECT column_name, data_type
-- FROM information_schema.columns
-- WHERE table_name = 'campaign_templates';
--
-- SELECT indexname FROM pg_indexes
-- WHERE tablename = 'campaign_templates';
--
-- SELECT polname FROM pg_policies
-- WHERE tablename = 'campaign_templates';

-- ============================================
-- MIGRATION CHECKLIST
-- ============================================
-- [x] Table created with all required columns
-- [x] UUID primary key with uuid_generate_v7()
-- [x] Foreign key to clients table
-- [x] JSONB columns for sequence and messaging
-- [x] Status check constraint
-- [x] Soft delete support (deleted_at column)
-- [x] Unique constraint respecting soft delete
-- [x] Indexes for common query patterns
-- [x] RLS enabled with appropriate policies
-- [x] Updated_at trigger
-- [x] Helper functions for common operations
-- [x] Grants for authenticated users
-- [x] Comments for documentation
