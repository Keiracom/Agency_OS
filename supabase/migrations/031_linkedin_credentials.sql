-- Migration: 031_linkedin_credentials.sql
-- Phase: 24H - LinkedIn Credential Connection
-- Purpose: Enable clients to connect LinkedIn accounts for HeyReach automation

-- ============================================================================
-- CLIENT LINKEDIN CREDENTIALS TABLE
-- ============================================================================

CREATE TABLE IF NOT EXISTS client_linkedin_credentials (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,

    -- Encrypted credentials (Fernet AES-256)
    linkedin_email_encrypted TEXT NOT NULL,
    linkedin_password_encrypted TEXT NOT NULL,

    -- Connection status: pending, connecting, awaiting_2fa, connected, failed, disconnected
    connection_status TEXT NOT NULL DEFAULT 'pending'
        CHECK (connection_status IN ('pending', 'connecting', 'awaiting_2fa', 'connected', 'failed', 'disconnected')),

    -- HeyReach integration
    heyreach_sender_id TEXT,
    heyreach_account_id TEXT,

    -- LinkedIn profile info (populated after connection)
    linkedin_profile_url TEXT,
    linkedin_profile_name TEXT,
    linkedin_headline TEXT,
    linkedin_connection_count INTEGER,

    -- 2FA handling
    two_fa_method TEXT,  -- 'sms', 'email', 'authenticator'
    two_fa_requested_at TIMESTAMPTZ,

    -- Error tracking
    last_error TEXT,
    error_count INTEGER DEFAULT 0,
    last_error_at TIMESTAMPTZ,

    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    connected_at TIMESTAMPTZ,
    disconnected_at TIMESTAMPTZ,

    -- One LinkedIn per client
    UNIQUE(client_id)
);

-- ============================================================================
-- INDEXES
-- ============================================================================

CREATE INDEX IF NOT EXISTS idx_linkedin_creds_client ON client_linkedin_credentials(client_id);
CREATE INDEX IF NOT EXISTS idx_linkedin_creds_status ON client_linkedin_credentials(connection_status);
CREATE INDEX IF NOT EXISTS idx_linkedin_creds_connected ON client_linkedin_credentials(connection_status)
    WHERE connection_status = 'connected';
CREATE INDEX IF NOT EXISTS idx_linkedin_creds_heyreach ON client_linkedin_credentials(heyreach_sender_id)
    WHERE heyreach_sender_id IS NOT NULL;

-- ============================================================================
-- ROW LEVEL SECURITY
-- ============================================================================

ALTER TABLE client_linkedin_credentials ENABLE ROW LEVEL SECURITY;

-- Clients can view their own LinkedIn credentials
DROP POLICY IF EXISTS "Clients can view own LinkedIn credentials" ON client_linkedin_credentials;
CREATE POLICY "Clients can view own LinkedIn credentials"
    ON client_linkedin_credentials FOR SELECT
    USING (client_id IN (
        SELECT client_id FROM memberships WHERE user_id = auth.uid()
    ));

-- Clients can insert their own LinkedIn credentials
DROP POLICY IF EXISTS "Clients can insert own LinkedIn credentials" ON client_linkedin_credentials;
CREATE POLICY "Clients can insert own LinkedIn credentials"
    ON client_linkedin_credentials FOR INSERT
    WITH CHECK (client_id IN (
        SELECT client_id FROM memberships WHERE user_id = auth.uid()
    ));

-- Clients can update their own LinkedIn credentials
DROP POLICY IF EXISTS "Clients can update own LinkedIn credentials" ON client_linkedin_credentials;
CREATE POLICY "Clients can update own LinkedIn credentials"
    ON client_linkedin_credentials FOR UPDATE
    USING (client_id IN (
        SELECT client_id FROM memberships WHERE user_id = auth.uid()
    ));

-- Clients can delete their own LinkedIn credentials
DROP POLICY IF EXISTS "Clients can delete own LinkedIn credentials" ON client_linkedin_credentials;
CREATE POLICY "Clients can delete own LinkedIn credentials"
    ON client_linkedin_credentials FOR DELETE
    USING (client_id IN (
        SELECT client_id FROM memberships WHERE user_id = auth.uid()
    ));

-- Service role full access
DROP POLICY IF EXISTS "Service role full access to LinkedIn credentials" ON client_linkedin_credentials;
CREATE POLICY "Service role full access to LinkedIn credentials"
    ON client_linkedin_credentials FOR ALL
    USING (auth.jwt() ->> 'role' = 'service_role');

-- Platform admins can view all
DROP POLICY IF EXISTS "Platform admins can view all LinkedIn credentials" ON client_linkedin_credentials;
CREATE POLICY "Platform admins can view all LinkedIn credentials"
    ON client_linkedin_credentials FOR SELECT
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
DROP TRIGGER IF EXISTS update_linkedin_credentials_updated_at ON client_linkedin_credentials;
CREATE TRIGGER update_linkedin_credentials_updated_at
    BEFORE UPDATE ON client_linkedin_credentials
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- HELPER FUNCTIONS
-- ============================================================================

-- Get LinkedIn connection status for a client
CREATE OR REPLACE FUNCTION get_linkedin_connection_status(p_client_id UUID)
RETURNS TABLE (
    status TEXT,
    profile_url TEXT,
    profile_name TEXT,
    headline TEXT,
    connection_count INTEGER,
    connected_at TIMESTAMPTZ,
    error TEXT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        lc.connection_status,
        lc.linkedin_profile_url,
        lc.linkedin_profile_name,
        lc.linkedin_headline,
        lc.linkedin_connection_count,
        lc.connected_at,
        CASE WHEN lc.connection_status = 'failed' THEN lc.last_error ELSE NULL END
    FROM client_linkedin_credentials lc
    WHERE lc.client_id = p_client_id;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Check if client has connected LinkedIn
CREATE OR REPLACE FUNCTION has_linkedin_connected(p_client_id UUID)
RETURNS BOOLEAN AS $$
BEGIN
    RETURN EXISTS (
        SELECT 1 FROM client_linkedin_credentials
        WHERE client_id = p_client_id
        AND connection_status = 'connected'
        AND heyreach_sender_id IS NOT NULL
    );
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- ============================================================================
-- COMMENTS
-- ============================================================================

COMMENT ON TABLE client_linkedin_credentials IS 'Stores encrypted LinkedIn credentials for HeyReach automation';
COMMENT ON COLUMN client_linkedin_credentials.linkedin_email_encrypted IS 'AES-256 encrypted LinkedIn email';
COMMENT ON COLUMN client_linkedin_credentials.linkedin_password_encrypted IS 'AES-256 encrypted LinkedIn password';
COMMENT ON COLUMN client_linkedin_credentials.connection_status IS 'Current connection state: pending, connecting, awaiting_2fa, connected, failed, disconnected';
COMMENT ON COLUMN client_linkedin_credentials.heyreach_sender_id IS 'HeyReach sender ID after successful connection';
COMMENT ON COLUMN client_linkedin_credentials.two_fa_method IS 'Method used for 2FA: sms, email, authenticator';
