-- Migration: 057_alert_system.sql
-- Part F: Silent Failure Alerts
-- Part G: Email Deliverability Monitoring
-- Date: 2026-02-19

-- =============================================================================
-- HUMAN REVIEW QUEUE
-- =============================================================================
-- For low-confidence reply classifications and other items needing human review

CREATE TABLE IF NOT EXISTS human_review_queue (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Related entities
    lead_id UUID REFERENCES leads(id) ON DELETE CASCADE,
    client_id UUID REFERENCES clients(id) ON DELETE CASCADE,
    campaign_id UUID REFERENCES campaigns(id) ON DELETE CASCADE,
    
    -- Review type and priority
    review_type TEXT NOT NULL CHECK (review_type IN (
        'reply_classification', 'content_qa', 'lead_data', 'referral_extraction'
    )),
    priority TEXT NOT NULL DEFAULT 'medium' CHECK (priority IN ('low', 'medium', 'high', 'urgent')),
    
    -- Status tracking
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN (
        'pending', 'in_progress', 'completed', 'skipped'
    )),
    
    -- Review data
    data JSONB NOT NULL DEFAULT '{}'::JSONB,
    
    -- Resolution
    resolved_by UUID REFERENCES users(id),
    resolution TEXT,
    resolution_data JSONB,
    resolved_at TIMESTAMPTZ,
    
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_human_review_queue_status ON human_review_queue(status) WHERE status = 'pending';
CREATE INDEX idx_human_review_queue_priority ON human_review_queue(priority, created_at);
CREATE INDEX idx_human_review_queue_lead ON human_review_queue(lead_id);
CREATE INDEX idx_human_review_queue_client ON human_review_queue(client_id);

-- =============================================================================
-- CLIENT DASHBOARD FLAGS
-- =============================================================================
-- Quick-check flags for dashboard alerts and indicators

CREATE TABLE IF NOT EXISTS client_dashboard_flags (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    
    -- Flag type (e.g., alert_bright_data_error, alert_warmup_health_low)
    flag_type TEXT NOT NULL,
    flag_value BOOLEAN NOT NULL DEFAULT FALSE,
    
    -- Link to related alert
    alert_id UUID REFERENCES admin_notifications(id) ON DELETE SET NULL,
    
    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    UNIQUE(client_id, flag_type)
);

CREATE INDEX idx_dashboard_flags_client ON client_dashboard_flags(client_id);
CREATE INDEX idx_dashboard_flags_active ON client_dashboard_flags(client_id) WHERE flag_value = TRUE;

-- =============================================================================
-- DOMAIN WARMUP STATUS
-- =============================================================================
-- Track warmup progress and health per email domain

CREATE TABLE IF NOT EXISTS domain_warmup_status (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    
    -- Domain info
    domain TEXT NOT NULL,
    provider TEXT NOT NULL DEFAULT 'warmforge',  -- warmforge, mailforge, manual
    
    -- Warmup status
    warmup_started_at TIMESTAMPTZ,
    warmup_completed_at TIMESTAMPTZ,
    warmup_stage TEXT,  -- e.g., 'ramping', 'stable', 'paused'
    
    -- Limits and scores
    daily_send_limit INTEGER NOT NULL DEFAULT 10,
    current_send_count INTEGER NOT NULL DEFAULT 0,
    health_score DECIMAL(5,2),
    reputation_score DECIMAL(5,2),
    
    -- Deliverability metrics
    bounce_rate DECIMAL(5,2),
    spam_rate DECIMAL(5,2),
    open_rate DECIMAL(5,2),
    
    -- Provider data
    provider_account_id TEXT,
    provider_data JSONB DEFAULT '{}'::JSONB,
    
    -- Tracking
    last_checked_at TIMESTAMPTZ,
    last_send_at TIMESTAMPTZ,
    
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    UNIQUE(client_id, domain)
);

CREATE INDEX idx_domain_warmup_client ON domain_warmup_status(client_id);
CREATE INDEX idx_domain_warmup_health ON domain_warmup_status(health_score) WHERE health_score < 70;

-- =============================================================================
-- API RATE LIMIT TRACKING
-- =============================================================================
-- Track rate limits for external APIs to enable alerts

CREATE TABLE IF NOT EXISTS api_rate_limits (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- API identification
    api_name TEXT NOT NULL,  -- hunter, bright_data, linkedin, prospeo
    resource_id TEXT,  -- seat_id, account_id, etc.
    client_id UUID REFERENCES clients(id) ON DELETE SET NULL,
    
    -- Rate limit info
    limit_type TEXT NOT NULL DEFAULT 'daily',  -- daily, hourly, per_minute
    max_requests INTEGER NOT NULL,
    requests_used INTEGER NOT NULL DEFAULT 0,
    requests_remaining INTEGER NOT NULL,
    
    -- Reset timing
    reset_at TIMESTAMPTZ,
    
    -- Status
    is_limited BOOLEAN NOT NULL DEFAULT FALSE,
    limited_at TIMESTAMPTZ,
    
    -- Tracking
    last_request_at TIMESTAMPTZ,
    
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    UNIQUE(api_name, resource_id, limit_type)
);

CREATE INDEX idx_api_rate_limits_name ON api_rate_limits(api_name);
CREATE INDEX idx_api_rate_limits_limited ON api_rate_limits(api_name) WHERE is_limited = TRUE;

-- =============================================================================
-- HELPER FUNCTIONS
-- =============================================================================

-- Check and update rate limit
CREATE OR REPLACE FUNCTION check_api_rate_limit(
    p_api_name TEXT,
    p_resource_id TEXT DEFAULT NULL,
    p_client_id UUID DEFAULT NULL
) RETURNS TABLE (
    is_limited BOOLEAN,
    requests_remaining INTEGER,
    reset_at TIMESTAMPTZ
) AS $$
DECLARE
    v_record api_rate_limits%ROWTYPE;
BEGIN
    SELECT * INTO v_record
    FROM api_rate_limits
    WHERE api_name = p_api_name
    AND (resource_id = p_resource_id OR (resource_id IS NULL AND p_resource_id IS NULL))
    AND (client_id = p_client_id OR client_id IS NULL);
    
    IF v_record IS NULL THEN
        RETURN QUERY SELECT FALSE, 1000, NULL::TIMESTAMPTZ;
        RETURN;
    END IF;
    
    -- Check if limit has reset
    IF v_record.reset_at IS NOT NULL AND v_record.reset_at < NOW() THEN
        UPDATE api_rate_limits
        SET is_limited = FALSE,
            requests_used = 0,
            requests_remaining = max_requests,
            updated_at = NOW()
        WHERE id = v_record.id;
        
        RETURN QUERY SELECT FALSE, v_record.max_requests, v_record.reset_at;
        RETURN;
    END IF;
    
    RETURN QUERY SELECT v_record.is_limited, v_record.requests_remaining, v_record.reset_at;
END;
$$ LANGUAGE plpgsql;

-- Get warmup status for all domains
CREATE OR REPLACE FUNCTION get_warmup_status_report(p_client_id UUID DEFAULT NULL)
RETURNS TABLE (
    client_id UUID,
    domain TEXT,
    provider TEXT,
    warmup_started_at TIMESTAMPTZ,
    warmup_completed_at TIMESTAMPTZ,
    warmup_stage TEXT,
    daily_send_limit INTEGER,
    health_score DECIMAL,
    is_healthy BOOLEAN
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        dws.client_id,
        dws.domain,
        dws.provider,
        dws.warmup_started_at,
        dws.warmup_completed_at,
        dws.warmup_stage,
        dws.daily_send_limit,
        dws.health_score,
        (dws.health_score >= 70) as is_healthy
    FROM domain_warmup_status dws
    WHERE (p_client_id IS NULL OR dws.client_id = p_client_id)
    ORDER BY dws.health_score ASC NULLS LAST;
END;
$$ LANGUAGE plpgsql;

-- =============================================================================
-- TRIGGERS
-- =============================================================================

CREATE TRIGGER human_review_queue_updated_at
    BEFORE UPDATE ON human_review_queue
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER client_dashboard_flags_updated_at
    BEFORE UPDATE ON client_dashboard_flags
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER domain_warmup_status_updated_at
    BEFORE UPDATE ON domain_warmup_status
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER api_rate_limits_updated_at
    BEFORE UPDATE ON api_rate_limits
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- =============================================================================
-- ADD campaign_halt TO NOTIFICATION TYPES
-- =============================================================================

DO $$
BEGIN
    -- Add campaign_halt if not exists (modify check constraint)
    ALTER TABLE admin_notifications 
    DROP CONSTRAINT IF EXISTS admin_notifications_notification_type_check;
    
    ALTER TABLE admin_notifications
    ADD CONSTRAINT admin_notifications_notification_type_check
    CHECK (notification_type IN (
        'angry_complaint', 'quota_shortfall', 'booking_confirmed', 'lead_converted',
        'campaign_halt', 'bright_data_error', 'hunter_rate_limit', 'linkedin_rate_limit',
        'warmup_health_low', 'hot_warm_ratio_low', 'enrichment_failure', 'webhook_failure'
    ));
EXCEPTION WHEN OTHERS THEN
    -- Constraint might not exist or be named differently
    NULL;
END $$;

-- =============================================================================
-- VERIFICATION
-- =============================================================================
-- [x] human_review_queue table for low-confidence classifications
-- [x] client_dashboard_flags for dashboard alerts
-- [x] domain_warmup_status for warmup monitoring
-- [x] api_rate_limits for tracking external API limits
-- [x] check_api_rate_limit() function
-- [x] get_warmup_status_report() function
-- [x] Updated notification types for new alert categories
