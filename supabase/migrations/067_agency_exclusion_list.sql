-- Migration: 067_agency_exclusion_list.sql
-- Phase: CRM Exclusion List
-- Purpose: Track companies to exclude from outreach (existing clients, pipeline deals, lost deals)
-- Date: 2026-02-26

-- ============================================================================
-- AGENCY EXCLUSION LIST
-- ============================================================================
-- Stores companies that should be excluded from outreach for each client.
-- Sources: existing CRM clients, active pipeline deals, lost deals, manual entries.

CREATE TABLE IF NOT EXISTS agency_exclusion_list (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    company_name TEXT NOT NULL,
    domain TEXT,
    abn TEXT,
    source TEXT NOT NULL,  -- 'crm_client', 'crm_pipeline', 'crm_lost_deal', 'manual'
    external_crm_id TEXT,
    added_at TIMESTAMPTZ DEFAULT NOW(),
    notes TEXT,
    
    -- Unique constraints for deduplication
    UNIQUE(client_id, domain),
    UNIQUE(client_id, abn)
);

-- ============================================================================
-- INDEXES
-- ============================================================================

CREATE INDEX IF NOT EXISTS idx_exclusion_client ON agency_exclusion_list(client_id);
CREATE INDEX IF NOT EXISTS idx_exclusion_domain ON agency_exclusion_list(domain);
CREATE INDEX IF NOT EXISTS idx_exclusion_abn ON agency_exclusion_list(abn);

-- ============================================================================
-- ROW LEVEL SECURITY
-- ============================================================================

ALTER TABLE agency_exclusion_list ENABLE ROW LEVEL SECURITY;

-- Clients can view their own exclusion list
CREATE POLICY "Clients can view own exclusion list"
    ON agency_exclusion_list FOR SELECT
    USING (client_id IN (
        SELECT client_id FROM memberships
        WHERE user_id = auth.uid()
    ));

-- Clients can insert to their own exclusion list
CREATE POLICY "Clients can insert own exclusion list"
    ON agency_exclusion_list FOR INSERT
    WITH CHECK (client_id IN (
        SELECT client_id FROM memberships
        WHERE user_id = auth.uid()
    ));

-- Clients can delete from their own exclusion list
CREATE POLICY "Clients can delete own exclusion list"
    ON agency_exclusion_list FOR DELETE
    USING (client_id IN (
        SELECT client_id FROM memberships
        WHERE user_id = auth.uid()
    ));

-- Service role full access
CREATE POLICY "Service role full access to exclusion list"
    ON agency_exclusion_list FOR ALL
    USING (auth.jwt() ->> 'role' = 'service_role');

-- ============================================================================
-- COMMENTS
-- ============================================================================

COMMENT ON TABLE agency_exclusion_list IS 'Companies to exclude from outreach per client';
COMMENT ON COLUMN agency_exclusion_list.source IS 'Origin: crm_client, crm_pipeline, crm_lost_deal, manual';
COMMENT ON COLUMN agency_exclusion_list.external_crm_id IS 'ID in external CRM system for sync tracking';

-- ============================================================================
-- COMPLETE
-- ============================================================================
