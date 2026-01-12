-- ============================================
-- Migration: 033_unipile_migration.sql
-- Purpose: Add Unipile support for LinkedIn automation
-- Phase: Unipile Migration (replacing HeyReach)
-- ============================================

-- Add Unipile columns to linkedin_credentials table
ALTER TABLE client_linkedin_credentials
ADD COLUMN IF NOT EXISTS unipile_account_id TEXT,
ADD COLUMN IF NOT EXISTS auth_method TEXT DEFAULT 'heyreach';

-- Create index for Unipile account lookup
CREATE INDEX IF NOT EXISTS idx_linkedin_creds_unipile
ON client_linkedin_credentials(unipile_account_id)
WHERE unipile_account_id IS NOT NULL;

-- Add comment explaining the transition
COMMENT ON COLUMN client_linkedin_credentials.unipile_account_id IS
'Unipile account ID for LinkedIn automation (replacing HeyReach)';

COMMENT ON COLUMN client_linkedin_credentials.auth_method IS
'Authentication method: heyreach (legacy), hosted (Unipile hosted auth)';

-- Update connection_status to include Unipile states
-- Note: Unipile uses simpler states since hosted auth handles complexity
ALTER TABLE client_linkedin_credentials
DROP CONSTRAINT IF EXISTS client_linkedin_credentials_connection_status_check;

ALTER TABLE client_linkedin_credentials
ADD CONSTRAINT client_linkedin_credentials_connection_status_check
CHECK (connection_status IN (
    'pending',           -- Initial state
    'connecting',        -- HeyReach: attempting connection
    'awaiting_2fa',      -- HeyReach: waiting for 2FA
    'connected',         -- Successfully connected
    'failed',            -- Connection failed
    'disconnected',      -- User disconnected
    'credentials_required' -- Unipile: needs re-authentication
));

-- ============================================
-- Note: Keep HeyReach columns for transition period
-- These will be dropped in a future migration:
-- - linkedin_email_encrypted
-- - linkedin_password_encrypted
-- - heyreach_sender_id
-- - heyreach_account_id
-- - two_fa_method
-- - two_fa_requested_at
-- ============================================
