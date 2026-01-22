-- Migration: 048_crm_sync_fields.sql
-- Phase: Two-way CRM Sync (Item 20)
-- Purpose: Add fields for blind meeting tracking, CRM sync, and CRM credentials
-- Date: 2026-01-22

-- ============================================================================
-- 1. ADD CRM INTEGRATION FIELDS TO CLIENTS TABLE
-- ============================================================================
-- These fields store CRM credentials for two-way sync polling

ALTER TABLE clients ADD COLUMN IF NOT EXISTS crm_type TEXT;  -- 'hubspot', 'pipedrive', 'close', 'salesforce'
ALTER TABLE clients ADD COLUMN IF NOT EXISTS hubspot_access_token TEXT;  -- HubSpot OAuth access token
ALTER TABLE clients ADD COLUMN IF NOT EXISTS pipedrive_api_token TEXT;  -- Pipedrive API token
ALTER TABLE clients ADD COLUMN IF NOT EXISTS close_api_key TEXT;  -- Close CRM API key
ALTER TABLE clients ADD COLUMN IF NOT EXISTS crm_webhook_secret TEXT;  -- Shared secret for webhook verification
ALTER TABLE clients ADD COLUMN IF NOT EXISTS crm_last_synced_at TIMESTAMPTZ;  -- Last successful CRM sync

-- Index for clients with CRM integrations
CREATE INDEX IF NOT EXISTS idx_clients_crm_type ON clients(crm_type)
    WHERE crm_type IS NOT NULL;

COMMENT ON COLUMN clients.crm_type IS 'Primary CRM integration type (hubspot, pipedrive, close, salesforce)';
COMMENT ON COLUMN clients.hubspot_access_token IS 'HubSpot OAuth access token for API calls';
COMMENT ON COLUMN clients.pipedrive_api_token IS 'Pipedrive API token for API calls';
COMMENT ON COLUMN clients.close_api_key IS 'Close CRM API key for API calls';

-- ============================================================================
-- 2. ALLOW NULLABLE LEAD_ID FOR BLIND MEETINGS
-- ============================================================================
-- Blind conversions may not have a linked lead (deal created directly in CRM)
-- We need to allow NULL lead_id for these cases

ALTER TABLE meetings ALTER COLUMN lead_id DROP NOT NULL;

-- ============================================================================
-- 3. ADD BLIND MEETING FIELDS TO MEETINGS TABLE
-- ============================================================================
-- Track meetings that were created directly in external CRM without going
-- through Agency OS ("blind conversions")

-- is_blind: TRUE if meeting was captured from CRM sync, not booked through Agency OS
ALTER TABLE meetings ADD COLUMN IF NOT EXISTS is_blind BOOLEAN DEFAULT FALSE;

-- external_deal_id: For deduplication when syncing from CRM
-- Maps to the deal ID in the external CRM system
ALTER TABLE meetings ADD COLUMN IF NOT EXISTS external_deal_id TEXT;

-- external_crm: Which CRM the meeting was synced from
ALTER TABLE meetings ADD COLUMN IF NOT EXISTS external_crm TEXT;

-- external_synced_at: When the meeting was last synced from external CRM
ALTER TABLE meetings ADD COLUMN IF NOT EXISTS external_synced_at TIMESTAMPTZ;

-- ============================================================================
-- 4. CREATE INDEXES FOR CRM SYNC LOOKUPS
-- ============================================================================

-- Index for external deal ID lookups (deduplication)
CREATE INDEX IF NOT EXISTS idx_meetings_external_deal ON meetings(external_deal_id)
    WHERE external_deal_id IS NOT NULL;

-- Index for finding blind meetings
CREATE INDEX IF NOT EXISTS idx_meetings_is_blind ON meetings(is_blind)
    WHERE is_blind = TRUE;

-- Composite index for CRM sync queries
CREATE INDEX IF NOT EXISTS idx_meetings_external_crm ON meetings(external_crm, external_deal_id)
    WHERE external_crm IS NOT NULL;

-- ============================================================================
-- 5. CREATE CRM SYNC LOG TABLE
-- ============================================================================
-- Track all incoming CRM sync events for debugging and audit

CREATE TABLE IF NOT EXISTS crm_sync_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,

    -- Source info
    crm_source TEXT NOT NULL,  -- 'hubspot', 'pipedrive', 'close'
    sync_type TEXT NOT NULL,   -- 'webhook', 'poll', 'manual'
    event_type TEXT NOT NULL,  -- 'deal_created', 'deal_updated', 'meeting_created'

    -- External identifiers
    external_deal_id TEXT,
    external_contact_id TEXT,

    -- Payload
    raw_payload JSONB,

    -- Matching results
    matched_lead_id UUID REFERENCES leads(id),
    matched_deal_id UUID REFERENCES deals(id),
    matched_meeting_id UUID REFERENCES meetings(id),

    -- Outcome
    sync_status TEXT NOT NULL DEFAULT 'pending',  -- 'pending', 'success', 'partial', 'failed', 'skipped'
    sync_notes TEXT,
    error_message TEXT,

    -- Flags
    created_blind_meeting BOOLEAN DEFAULT FALSE,
    created_deal BOOLEAN DEFAULT FALSE,
    updated_lead BOOLEAN DEFAULT FALSE,

    -- Audit
    created_at TIMESTAMPTZ DEFAULT NOW(),
    processed_at TIMESTAMPTZ
);

-- Indexes for sync log queries
CREATE INDEX IF NOT EXISTS idx_crm_sync_log_client ON crm_sync_log(client_id);
CREATE INDEX IF NOT EXISTS idx_crm_sync_log_source ON crm_sync_log(crm_source);
CREATE INDEX IF NOT EXISTS idx_crm_sync_log_status ON crm_sync_log(sync_status);
CREATE INDEX IF NOT EXISTS idx_crm_sync_log_created ON crm_sync_log(created_at);
CREATE INDEX IF NOT EXISTS idx_crm_sync_log_external ON crm_sync_log(external_deal_id);

-- ============================================================================
-- 6. ROW LEVEL SECURITY FOR SYNC LOG
-- ============================================================================

ALTER TABLE crm_sync_log ENABLE ROW LEVEL SECURITY;

CREATE POLICY crm_sync_log_client_isolation ON crm_sync_log
    FOR ALL
    USING (
        client_id IN (
            SELECT client_id FROM memberships
            WHERE user_id = auth.uid()
        )
    );

-- ============================================================================
-- 7. ADD COMMENTS FOR DOCUMENTATION
-- ============================================================================

COMMENT ON COLUMN meetings.is_blind IS 'TRUE if meeting was captured from external CRM sync, not booked through Agency OS';
COMMENT ON COLUMN meetings.external_deal_id IS 'External CRM deal ID for deduplication during sync';
COMMENT ON COLUMN meetings.external_crm IS 'Source CRM system (hubspot, pipedrive, close)';
COMMENT ON TABLE crm_sync_log IS 'Audit log for all incoming CRM sync events (webhooks and polling)';

-- ============================================================================
-- COMPLETE
-- ============================================================================
