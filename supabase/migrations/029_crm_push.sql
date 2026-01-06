-- Migration: 029_crm_push.sql
-- Phase: 24E - CRM Push (Meeting Booked)
-- Purpose: Push meetings to client's CRM (HubSpot, Pipedrive, Close)

-- ============================================================================
-- CLIENT CRM CONFIGURATIONS
-- ============================================================================

-- Client CRM configuration (one CRM per client)
CREATE TABLE IF NOT EXISTS client_crm_configs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,

    -- CRM type
    crm_type TEXT NOT NULL CHECK (crm_type IN ('hubspot', 'pipedrive', 'close')),

    -- Authentication (encrypted at rest via Supabase)
    -- For Pipedrive, Close: API key only
    api_key TEXT,

    -- For HubSpot: OAuth tokens
    oauth_access_token TEXT,
    oauth_refresh_token TEXT,
    oauth_expires_at TIMESTAMPTZ,

    -- HubSpot OAuth metadata
    hubspot_portal_id TEXT,
    hubspot_app_id TEXT,

    -- Configuration - which pipeline/stage to use
    pipeline_id TEXT,          -- CRM pipeline ID
    pipeline_name TEXT,        -- Display name
    stage_id TEXT,             -- Stage for new meetings
    stage_name TEXT,           -- Display name
    owner_id TEXT,             -- Default deal owner
    owner_name TEXT,           -- Display name
    owner_email TEXT,          -- For reference

    -- Status
    is_active BOOLEAN DEFAULT true,
    connection_status TEXT DEFAULT 'pending' CHECK (connection_status IN ('pending', 'connected', 'error', 'disconnected')),
    last_successful_push_at TIMESTAMPTZ,
    last_error TEXT,
    last_error_at TIMESTAMPTZ,

    -- Metadata
    connected_at TIMESTAMPTZ,
    connected_by UUID REFERENCES auth.users(id),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    -- One CRM config per client
    UNIQUE (client_id)
);

-- CRM push log (audit trail for all push operations)
CREATE TABLE IF NOT EXISTS crm_push_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    crm_config_id UUID REFERENCES client_crm_configs(id) ON DELETE SET NULL,

    -- Operation details
    operation TEXT NOT NULL CHECK (operation IN (
        'find_contact',
        'create_contact',
        'create_deal',
        'associate_deal_contact',
        'update_deal',
        'test_connection',
        'fetch_pipelines',
        'fetch_stages',
        'fetch_users',
        'oauth_token_refresh'
    )),

    -- Our references
    lead_id UUID REFERENCES leads(id) ON DELETE SET NULL,
    meeting_id UUID REFERENCES meetings(id) ON DELETE SET NULL,

    -- Their references
    crm_contact_id TEXT,
    crm_deal_id TEXT,
    crm_org_id TEXT,  -- For Pipedrive organization

    -- Request/Response for debugging
    request_payload JSONB,
    response_payload JSONB,

    -- Status
    status TEXT NOT NULL CHECK (status IN ('success', 'failed', 'skipped')),
    error_code TEXT,
    error_message TEXT,

    -- Timing
    duration_ms INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================================
-- INDEXES
-- ============================================================================

CREATE INDEX IF NOT EXISTS idx_crm_configs_client ON client_crm_configs(client_id);
CREATE INDEX IF NOT EXISTS idx_crm_configs_active ON client_crm_configs(is_active) WHERE is_active = true;

CREATE INDEX IF NOT EXISTS idx_crm_push_log_client ON crm_push_log(client_id);
CREATE INDEX IF NOT EXISTS idx_crm_push_log_lead ON crm_push_log(lead_id) WHERE lead_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_crm_push_log_meeting ON crm_push_log(meeting_id) WHERE meeting_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_crm_push_log_status ON crm_push_log(status);
CREATE INDEX IF NOT EXISTS idx_crm_push_log_created ON crm_push_log(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_crm_push_log_operation ON crm_push_log(operation, created_at DESC);

-- ============================================================================
-- ROW LEVEL SECURITY
-- ============================================================================

ALTER TABLE client_crm_configs ENABLE ROW LEVEL SECURITY;
ALTER TABLE crm_push_log ENABLE ROW LEVEL SECURITY;

-- Clients can view their own CRM config
CREATE POLICY "Clients can view own CRM config"
    ON client_crm_configs FOR SELECT
    USING (client_id IN (
        SELECT id FROM clients WHERE user_id = auth.uid()
    ));

-- Clients can update their own CRM config
CREATE POLICY "Clients can update own CRM config"
    ON client_crm_configs FOR UPDATE
    USING (client_id IN (
        SELECT id FROM clients WHERE user_id = auth.uid()
    ));

-- Clients can insert their own CRM config
CREATE POLICY "Clients can insert own CRM config"
    ON client_crm_configs FOR INSERT
    WITH CHECK (client_id IN (
        SELECT id FROM clients WHERE user_id = auth.uid()
    ));

-- Clients can delete their own CRM config (disconnect)
CREATE POLICY "Clients can delete own CRM config"
    ON client_crm_configs FOR DELETE
    USING (client_id IN (
        SELECT id FROM clients WHERE user_id = auth.uid()
    ));

-- Clients can view their own push logs
CREATE POLICY "Clients can view own CRM push logs"
    ON crm_push_log FOR SELECT
    USING (client_id IN (
        SELECT id FROM clients WHERE user_id = auth.uid()
    ));

-- Service role can do everything (for backend operations)
CREATE POLICY "Service role full access to CRM configs"
    ON client_crm_configs FOR ALL
    USING (auth.jwt() ->> 'role' = 'service_role');

CREATE POLICY "Service role full access to CRM push logs"
    ON crm_push_log FOR ALL
    USING (auth.jwt() ->> 'role' = 'service_role');

-- Platform admins can view all CRM configs
CREATE POLICY "Platform admins can view all CRM configs"
    ON client_crm_configs FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM users
            WHERE users.id = auth.uid()
            AND users.is_platform_admin = true
        )
    );

-- Platform admins can view all push logs
CREATE POLICY "Platform admins can view all CRM push logs"
    ON crm_push_log FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM users
            WHERE users.id = auth.uid()
            AND users.is_platform_admin = true
        )
    );

-- ============================================================================
-- TRIGGERS
-- ============================================================================

-- Update updated_at timestamp
CREATE TRIGGER update_client_crm_configs_updated_at
    BEFORE UPDATE ON client_crm_configs
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- HELPER FUNCTIONS
-- ============================================================================

-- Get CRM push stats for a client
CREATE OR REPLACE FUNCTION get_crm_push_stats(p_client_id UUID)
RETURNS TABLE (
    total_pushes BIGINT,
    successful_pushes BIGINT,
    failed_pushes BIGINT,
    success_rate NUMERIC,
    last_push_at TIMESTAMPTZ,
    contacts_created BIGINT,
    deals_created BIGINT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        COUNT(*)::BIGINT as total_pushes,
        COUNT(*) FILTER (WHERE status = 'success')::BIGINT as successful_pushes,
        COUNT(*) FILTER (WHERE status = 'failed')::BIGINT as failed_pushes,
        CASE
            WHEN COUNT(*) > 0 THEN
                ROUND((COUNT(*) FILTER (WHERE status = 'success')::NUMERIC / COUNT(*)::NUMERIC) * 100, 2)
            ELSE 0
        END as success_rate,
        MAX(created_at) as last_push_at,
        COUNT(*) FILTER (WHERE operation = 'create_contact' AND status = 'success')::BIGINT as contacts_created,
        COUNT(*) FILTER (WHERE operation = 'create_deal' AND status = 'success')::BIGINT as deals_created
    FROM crm_push_log
    WHERE client_id = p_client_id;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Get recent CRM push failures for alerting
CREATE OR REPLACE FUNCTION get_recent_crm_failures(p_client_id UUID, p_hours INTEGER DEFAULT 24)
RETURNS TABLE (
    id UUID,
    operation TEXT,
    error_message TEXT,
    created_at TIMESTAMPTZ,
    lead_id UUID,
    meeting_id UUID
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        l.id,
        l.operation,
        l.error_message,
        l.created_at,
        l.lead_id,
        l.meeting_id
    FROM crm_push_log l
    WHERE l.client_id = p_client_id
      AND l.status = 'failed'
      AND l.created_at > NOW() - (p_hours || ' hours')::INTERVAL
    ORDER BY l.created_at DESC
    LIMIT 50;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- ============================================================================
-- COMMENTS
-- ============================================================================

COMMENT ON TABLE client_crm_configs IS 'CRM connection configuration per client (one CRM per client)';
COMMENT ON TABLE crm_push_log IS 'Audit log of all CRM push operations';

COMMENT ON COLUMN client_crm_configs.crm_type IS 'Type of CRM: hubspot, pipedrive, or close';
COMMENT ON COLUMN client_crm_configs.api_key IS 'API key for Pipedrive and Close';
COMMENT ON COLUMN client_crm_configs.oauth_access_token IS 'OAuth access token for HubSpot';
COMMENT ON COLUMN client_crm_configs.oauth_refresh_token IS 'OAuth refresh token for HubSpot';
COMMENT ON COLUMN client_crm_configs.pipeline_id IS 'ID of the pipeline in the CRM to create deals in';
COMMENT ON COLUMN client_crm_configs.stage_id IS 'ID of the stage for newly created deals';
COMMENT ON COLUMN client_crm_configs.owner_id IS 'ID of the user in CRM who will own new deals';

COMMENT ON COLUMN crm_push_log.operation IS 'Type of CRM operation performed';
COMMENT ON COLUMN crm_push_log.crm_contact_id IS 'ID of the contact in the external CRM';
COMMENT ON COLUMN crm_push_log.crm_deal_id IS 'ID of the deal in the external CRM';
