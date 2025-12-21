-- FILE: supabase/migrations/010_platform_admin.sql
-- PURPOSE: Add platform admin flag to users table
-- PHASE: Admin Dashboard
-- TASK: Admin Dashboard Foundation

-- ============================================================================
-- Add is_platform_admin column to users table
-- ============================================================================

ALTER TABLE users
ADD COLUMN IF NOT EXISTS is_platform_admin BOOLEAN DEFAULT FALSE;

-- Add index for admin lookups
CREATE INDEX IF NOT EXISTS idx_users_platform_admin
ON users(is_platform_admin)
WHERE is_platform_admin = TRUE;

-- ============================================================================
-- Platform Settings Table (for admin configuration)
-- ============================================================================

CREATE TABLE IF NOT EXISTS platform_settings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    key TEXT NOT NULL UNIQUE,
    value JSONB NOT NULL DEFAULT '{}',
    description TEXT,
    updated_by UUID REFERENCES users(id),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Insert default platform settings
INSERT INTO platform_settings (key, value, description) VALUES
    ('ai_daily_spend_limit_aud', '{"value": 500}', 'Daily AI spend limit in AUD'),
    ('clay_fallback_percentage', '{"value": 15}', 'Percentage of leads to send to Clay'),
    ('maintenance_mode', '{"enabled": false}', 'Platform maintenance mode flag'),
    ('feature_flags', '{"voice_enabled": true, "mail_enabled": true}', 'Feature toggles')
ON CONFLICT (key) DO NOTHING;

-- ============================================================================
-- Global Suppression List Table (platform-wide)
-- ============================================================================

CREATE TABLE IF NOT EXISTS global_suppression_list (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email TEXT NOT NULL,
    reason TEXT NOT NULL CHECK (reason IN ('unsubscribe', 'bounce', 'spam', 'manual')),
    source TEXT, -- Which client/campaign triggered this
    added_by UUID REFERENCES users(id),
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),

    CONSTRAINT unique_global_suppression_email UNIQUE (email)
);

-- Index for email lookups
CREATE INDEX IF NOT EXISTS idx_global_suppression_email
ON global_suppression_list(email);

CREATE INDEX IF NOT EXISTS idx_global_suppression_reason
ON global_suppression_list(reason);

-- ============================================================================
-- AI Spend Tracking Table (for historical tracking)
-- ============================================================================

CREATE TABLE IF NOT EXISTS ai_spend_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id UUID REFERENCES clients(id),
    agent_type TEXT NOT NULL CHECK (agent_type IN ('cmo', 'content', 'reply')),
    model TEXT NOT NULL,
    input_tokens INTEGER NOT NULL DEFAULT 0,
    output_tokens INTEGER NOT NULL DEFAULT 0,
    cost_aud DECIMAL(10, 4) NOT NULL DEFAULT 0,
    request_metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for AI spend reporting
CREATE INDEX IF NOT EXISTS idx_ai_spend_client
ON ai_spend_log(client_id, created_at);

CREATE INDEX IF NOT EXISTS idx_ai_spend_agent
ON ai_spend_log(agent_type, created_at);

CREATE INDEX IF NOT EXISTS idx_ai_spend_date
ON ai_spend_log(created_at);

-- ============================================================================
-- Admin Activity Log
-- ============================================================================

CREATE TABLE IF NOT EXISTS admin_activity_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    admin_user_id UUID NOT NULL REFERENCES users(id),
    action TEXT NOT NULL,
    resource_type TEXT,
    resource_id UUID,
    details JSONB DEFAULT '{}',
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_admin_activity_user
ON admin_activity_log(admin_user_id, created_at);

CREATE INDEX IF NOT EXISTS idx_admin_activity_action
ON admin_activity_log(action, created_at);

-- ============================================================================
-- RLS Policies for Admin Tables
-- ============================================================================

-- Platform settings: Only platform admins can read/write
ALTER TABLE platform_settings ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Platform admins can read settings"
ON platform_settings FOR SELECT
TO authenticated
USING (
    EXISTS (
        SELECT 1 FROM users
        WHERE id = auth.uid()
        AND is_platform_admin = TRUE
    )
);

CREATE POLICY "Platform admins can update settings"
ON platform_settings FOR UPDATE
TO authenticated
USING (
    EXISTS (
        SELECT 1 FROM users
        WHERE id = auth.uid()
        AND is_platform_admin = TRUE
    )
);

-- Global suppression: Platform admins only
ALTER TABLE global_suppression_list ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Platform admins can manage suppression list"
ON global_suppression_list FOR ALL
TO authenticated
USING (
    EXISTS (
        SELECT 1 FROM users
        WHERE id = auth.uid()
        AND is_platform_admin = TRUE
    )
);

-- AI spend log: Platform admins can read all
ALTER TABLE ai_spend_log ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Platform admins can read AI spend"
ON ai_spend_log FOR SELECT
TO authenticated
USING (
    EXISTS (
        SELECT 1 FROM users
        WHERE id = auth.uid()
        AND is_platform_admin = TRUE
    )
);

-- Admin activity log: Platform admins only
ALTER TABLE admin_activity_log ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Platform admins can read admin activity"
ON admin_activity_log FOR SELECT
TO authenticated
USING (
    EXISTS (
        SELECT 1 FROM users
        WHERE id = auth.uid()
        AND is_platform_admin = TRUE
    )
);

CREATE POLICY "Platform admins can log actions"
ON admin_activity_log FOR INSERT
TO authenticated
WITH CHECK (
    EXISTS (
        SELECT 1 FROM users
        WHERE id = auth.uid()
        AND is_platform_admin = TRUE
    )
);

-- ============================================================================
-- Helper Functions
-- ============================================================================

-- Function to check if current user is platform admin
CREATE OR REPLACE FUNCTION is_platform_admin()
RETURNS BOOLEAN AS $$
    SELECT EXISTS (
        SELECT 1 FROM users
        WHERE id = auth.uid()
        AND is_platform_admin = TRUE
    );
$$ LANGUAGE sql SECURITY DEFINER STABLE;

-- Function to calculate client health score
CREATE OR REPLACE FUNCTION calculate_client_health_score(p_client_id UUID)
RETURNS INTEGER AS $$
DECLARE
    score INTEGER := 0;
    has_active_campaigns BOOLEAN;
    last_activity_at TIMESTAMPTZ;
    bounce_rate DECIMAL;
    subscription_status TEXT;
BEGIN
    -- Get client subscription status
    SELECT c.subscription_status INTO subscription_status
    FROM clients c WHERE c.id = p_client_id;

    -- Check for active campaigns (+20)
    SELECT EXISTS (
        SELECT 1 FROM campaigns
        WHERE client_id = p_client_id
        AND status = 'active'
        AND deleted_at IS NULL
    ) INTO has_active_campaigns;

    IF has_active_campaigns THEN
        score := score + 20;
    END IF;

    -- Check last activity
    SELECT MAX(created_at) INTO last_activity_at
    FROM activities a
    JOIN leads l ON a.lead_id = l.id
    WHERE l.client_id = p_client_id;

    IF last_activity_at > NOW() - INTERVAL '24 hours' THEN
        score := score + 30;  -- Activity in last 24h
    ELSIF last_activity_at > NOW() - INTERVAL '48 hours' THEN
        score := score + 20;  -- Activity in last 48h
    ELSIF last_activity_at < NOW() - INTERVAL '48 hours' OR last_activity_at IS NULL THEN
        score := score - 30;  -- No activity 48h+
    END IF;

    -- Check bounce rate (simplified - would need actual bounce tracking)
    -- For now, assume good: +15
    score := score + 15;

    -- Check payment status
    IF subscription_status IN ('active', 'trialing') THEN
        score := score + 15;
    ELSIF subscription_status = 'past_due' THEN
        score := score - 30;
    END IF;

    -- Ensure score is between 0 and 100
    RETURN GREATEST(0, LEAST(100, score));
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- ============================================================================
-- Verification
-- ============================================================================
-- [x] is_platform_admin column added
-- [x] platform_settings table created
-- [x] global_suppression_list table created
-- [x] ai_spend_log table created
-- [x] admin_activity_log table created
-- [x] RLS policies applied
-- [x] Helper functions created
