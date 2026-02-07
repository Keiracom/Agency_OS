-- ============================================
-- Migration: 006_unipile_accounts.sql
-- Purpose: Multi-tenant Unipile accounts for BYOA (Bring Your Own Account)
-- Created: 2026-02-07
-- Phase: Unipile BYOA Multi-Tenancy
-- ============================================

-- Multi-tenant Unipile accounts table
-- Each user can connect their own LinkedIn account via Unipile hosted auth
CREATE TABLE IF NOT EXISTS unipile_accounts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    client_id UUID REFERENCES clients(id) ON DELETE SET NULL,
    unipile_account_id TEXT NOT NULL UNIQUE,
    provider TEXT NOT NULL DEFAULT 'LINKEDIN',
    status TEXT NOT NULL DEFAULT 'OK' CHECK (status IN ('OK', 'EXPIRED', 'PENDING', 'ERROR')),
    display_name TEXT,
    email TEXT,
    profile_url TEXT,
    connected_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ,
    last_used_at TIMESTAMPTZ,
    last_checked_at TIMESTAMPTZ,
    error_message TEXT,
    error_count INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Performance indexes
CREATE INDEX idx_unipile_accounts_user_id ON unipile_accounts(user_id);
CREATE INDEX idx_unipile_accounts_client_id ON unipile_accounts(client_id);
CREATE INDEX idx_unipile_accounts_status ON unipile_accounts(status);
CREATE INDEX idx_unipile_accounts_provider ON unipile_accounts(provider);
CREATE INDEX idx_unipile_accounts_expires_at ON unipile_accounts(expires_at) 
    WHERE expires_at IS NOT NULL;

-- Auto-update timestamp trigger
CREATE OR REPLACE FUNCTION update_unipile_accounts_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_unipile_accounts_updated
    BEFORE UPDATE ON unipile_accounts
    FOR EACH ROW
    EXECUTE FUNCTION update_unipile_accounts_timestamp();

-- RLS (Row Level Security)
ALTER TABLE unipile_accounts ENABLE ROW LEVEL SECURITY;

-- Users can only see their own accounts
CREATE POLICY unipile_accounts_select_own ON unipile_accounts
    FOR SELECT
    USING (auth.uid() = user_id);

-- Users can only insert their own accounts
CREATE POLICY unipile_accounts_insert_own ON unipile_accounts
    FOR INSERT
    WITH CHECK (auth.uid() = user_id);

-- Users can only update their own accounts
CREATE POLICY unipile_accounts_update_own ON unipile_accounts
    FOR UPDATE
    USING (auth.uid() = user_id);

-- Users can only delete their own accounts
CREATE POLICY unipile_accounts_delete_own ON unipile_accounts
    FOR DELETE
    USING (auth.uid() = user_id);

-- Service role can do everything (for webhooks)
CREATE POLICY unipile_accounts_service_all ON unipile_accounts
    FOR ALL
    USING (auth.jwt() ->> 'role' = 'service_role');

-- View: Active Unipile accounts with user info
CREATE OR REPLACE VIEW active_unipile_accounts AS
SELECT 
    ua.id,
    ua.user_id,
    ua.client_id,
    ua.unipile_account_id,
    ua.provider,
    ua.status,
    ua.display_name,
    ua.email,
    ua.profile_url,
    ua.connected_at,
    ua.last_used_at,
    c.name AS client_name,
    u.email AS user_email
FROM unipile_accounts ua
LEFT JOIN clients c ON ua.client_id = c.id AND c.deleted_at IS NULL
LEFT JOIN auth.users u ON ua.user_id = u.id
WHERE ua.status = 'OK';

COMMENT ON TABLE unipile_accounts IS 'Multi-tenant Unipile LinkedIn accounts (BYOA model)';
COMMENT ON COLUMN unipile_accounts.unipile_account_id IS 'Unipile account ID from hosted auth';
COMMENT ON COLUMN unipile_accounts.status IS 'Account status: OK=connected, EXPIRED=needs reauth, PENDING=connecting, ERROR=failed';
COMMENT ON COLUMN unipile_accounts.provider IS 'Provider type (currently only LINKEDIN supported)';
