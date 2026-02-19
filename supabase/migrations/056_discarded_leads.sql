-- Migration: 056_discarded_leads.sql
-- Part C: Discard loop and soft-delete mechanism
-- CEO Directive: Batch Controller & Discard Loop
-- Date: 2026-02-19

-- =============================================================================
-- DISCARDED LEADS TABLE
-- =============================================================================
-- Tracks all discarded leads with reason, gate, ALS score at discard, and hold period

CREATE TABLE IF NOT EXISTS discarded_leads (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    lead_id UUID NOT NULL REFERENCES lead_pool(id) ON DELETE CASCADE,
    client_id UUID REFERENCES clients(id) ON DELETE SET NULL,
    campaign_id UUID REFERENCES campaigns(id) ON DELETE SET NULL,
    
    -- Discard gate (which checkpoint caught this)
    discard_gate INTEGER NOT NULL CHECK (discard_gate IN (1, 2, 3)),
    
    -- Reason for discard
    discard_reason TEXT NOT NULL,
    
    -- ALS score at time of discard (for analytics)
    als_at_discard INTEGER,
    
    -- Soft delete hold mechanism
    discarded_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    held_until TIMESTAMPTZ NOT NULL DEFAULT (NOW() + INTERVAL '48 hours'),
    hard_deleted_at TIMESTAMPTZ,
    
    -- Metadata
    discard_metadata JSONB DEFAULT '{}'::JSONB,
    
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes for efficient querying
CREATE INDEX idx_discarded_leads_lead_id ON discarded_leads(lead_id);
CREATE INDEX idx_discarded_leads_client_id ON discarded_leads(client_id);
CREATE INDEX idx_discarded_leads_gate ON discarded_leads(discard_gate);
CREATE INDEX idx_discarded_leads_held_until ON discarded_leads(held_until) WHERE hard_deleted_at IS NULL;
CREATE INDEX idx_discarded_leads_hard_deleted ON discarded_leads(hard_deleted_at) WHERE hard_deleted_at IS NOT NULL;

-- =============================================================================
-- LEAD POOL STATUS EXTENSION
-- =============================================================================
-- Add discarded_pending status to lead_pool

DO $$ 
BEGIN
    -- Add discarded_pending to pool_status_type if not exists
    IF NOT EXISTS (
        SELECT 1 FROM pg_enum 
        WHERE enumlabel = 'discarded_pending' 
        AND enumtypid = (SELECT oid FROM pg_type WHERE typname = 'pool_status_type')
    ) THEN
        ALTER TYPE pool_status_type ADD VALUE 'discarded_pending';
    END IF;
END $$;

-- =============================================================================
-- ADMIN NOTIFICATIONS TABLE (for angry/complaint alerts)
-- =============================================================================

CREATE TABLE IF NOT EXISTS admin_notifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Notification type
    notification_type TEXT NOT NULL CHECK (notification_type IN (
        'angry_complaint', 'quota_shortfall', 'booking_confirmed', 'lead_converted'
    )),
    
    -- Related entities
    client_id UUID REFERENCES clients(id) ON DELETE CASCADE,
    lead_id UUID,
    campaign_id UUID,
    
    -- Notification content
    title TEXT NOT NULL,
    message TEXT NOT NULL,
    severity TEXT NOT NULL DEFAULT 'medium' CHECK (severity IN ('low', 'medium', 'high', 'critical')),
    
    -- Status tracking
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'sent', 'acknowledged', 'resolved')),
    sent_at TIMESTAMPTZ,
    acknowledged_at TIMESTAMPTZ,
    acknowledged_by UUID REFERENCES users(id),
    resolved_at TIMESTAMPTZ,
    resolved_by UUID REFERENCES users(id),
    
    -- Metadata
    metadata JSONB DEFAULT '{}'::JSONB,
    
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_admin_notifications_type ON admin_notifications(notification_type);
CREATE INDEX idx_admin_notifications_client ON admin_notifications(client_id);
CREATE INDEX idx_admin_notifications_status ON admin_notifications(status);
CREATE INDEX idx_admin_notifications_severity ON admin_notifications(severity) WHERE status = 'pending';

-- =============================================================================
-- QUOTA MONITORING TABLE
-- =============================================================================

CREATE TABLE IF NOT EXISTS campaign_quota_status (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    campaign_id UUID NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE,
    client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    
    -- Quota targets
    target_lead_count INTEGER NOT NULL DEFAULT 100,
    min_als_score INTEGER NOT NULL DEFAULT 35,
    
    -- Current status
    current_qualified_count INTEGER NOT NULL DEFAULT 0,
    current_average_als DECIMAL(5,2),
    
    -- Discovery loop status
    discovery_loops_run INTEGER NOT NULL DEFAULT 0,
    last_discovery_at TIMESTAMPTZ,
    replacement_needed INTEGER NOT NULL DEFAULT 0,
    
    -- Alerts
    quota_shortfall_alert_sent BOOLEAN NOT NULL DEFAULT FALSE,
    quota_shortfall_at TIMESTAMPTZ,
    
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    UNIQUE(campaign_id)
);

CREATE INDEX idx_campaign_quota_campaign ON campaign_quota_status(campaign_id);
CREATE INDEX idx_campaign_quota_client ON campaign_quota_status(client_id);

-- =============================================================================
-- HELPER FUNCTION: Create admin notification
-- =============================================================================

CREATE OR REPLACE FUNCTION create_admin_notification(
    p_notification_type TEXT,
    p_client_id UUID,
    p_title TEXT,
    p_message TEXT,
    p_severity TEXT DEFAULT 'medium',
    p_lead_id UUID DEFAULT NULL,
    p_campaign_id UUID DEFAULT NULL,
    p_metadata JSONB DEFAULT '{}'::JSONB
) RETURNS UUID AS $$
DECLARE
    v_notification_id UUID;
BEGIN
    INSERT INTO admin_notifications (
        notification_type, client_id, lead_id, campaign_id,
        title, message, severity, metadata
    ) VALUES (
        p_notification_type, p_client_id, p_lead_id, p_campaign_id,
        p_title, p_message, p_severity, p_metadata
    )
    RETURNING id INTO v_notification_id;
    
    RETURN v_notification_id;
END;
$$ LANGUAGE plpgsql;

-- =============================================================================
-- HELPER FUNCTION: Soft discard a lead
-- =============================================================================

CREATE OR REPLACE FUNCTION soft_discard_lead(
    p_lead_id UUID,
    p_discard_gate INTEGER,
    p_discard_reason TEXT,
    p_client_id UUID DEFAULT NULL,
    p_campaign_id UUID DEFAULT NULL,
    p_metadata JSONB DEFAULT '{}'::JSONB
) RETURNS UUID AS $$
DECLARE
    v_discard_id UUID;
    v_als_score INTEGER;
BEGIN
    -- Get current ALS score
    SELECT als_score INTO v_als_score
    FROM lead_pool
    WHERE id = p_lead_id;
    
    -- Create discard record
    INSERT INTO discarded_leads (
        lead_id, client_id, campaign_id,
        discard_gate, discard_reason, als_at_discard,
        discard_metadata
    ) VALUES (
        p_lead_id, p_client_id, p_campaign_id,
        p_discard_gate, p_discard_reason, v_als_score,
        p_metadata
    )
    RETURNING id INTO v_discard_id;
    
    -- Update lead_pool status to discarded_pending
    UPDATE lead_pool
    SET pool_status = 'discarded_pending',
        updated_at = NOW()
    WHERE id = p_lead_id;
    
    RETURN v_discard_id;
END;
$$ LANGUAGE plpgsql;

-- =============================================================================
-- HELPER FUNCTION: Hard delete expired discards
-- =============================================================================

CREATE OR REPLACE FUNCTION hard_delete_expired_discards() RETURNS INTEGER AS $$
DECLARE
    v_count INTEGER;
BEGIN
    -- Update discarded_leads records past their hold period
    WITH expired AS (
        UPDATE discarded_leads
        SET hard_deleted_at = NOW(),
            updated_at = NOW()
        WHERE held_until < NOW()
        AND hard_deleted_at IS NULL
        RETURNING lead_id
    )
    SELECT COUNT(*) INTO v_count FROM expired;
    
    -- Delete from lead_pool where hard deleted
    DELETE FROM lead_pool
    WHERE id IN (
        SELECT lead_id FROM discarded_leads
        WHERE hard_deleted_at IS NOT NULL
        AND hard_deleted_at > NOW() - INTERVAL '1 hour'
    );
    
    RETURN v_count;
END;
$$ LANGUAGE plpgsql;

-- =============================================================================
-- TRIGGER: Update updated_at
-- =============================================================================

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER discarded_leads_updated_at
    BEFORE UPDATE ON discarded_leads
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER admin_notifications_updated_at
    BEFORE UPDATE ON admin_notifications
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER campaign_quota_status_updated_at
    BEFORE UPDATE ON campaign_quota_status
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- =============================================================================
-- VERIFICATION
-- =============================================================================
-- [x] discarded_leads table with gate, reason, als_at_discard
-- [x] Soft delete hold mechanism (held_until + 48hrs)
-- [x] admin_notifications table for alerts
-- [x] campaign_quota_status for quota monitoring
-- [x] soft_discard_lead() function
-- [x] hard_delete_expired_discards() function
-- [x] create_admin_notification() function
