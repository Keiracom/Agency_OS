-- Migration: 044_domain_health.sql
-- Purpose: Add domain health tracking fields to resource_pool table
-- Spec: docs/architecture/distribution/EMAIL_DISTRIBUTION.md
-- Phase: D (Email Distribution)

-- ============================================
-- ADD HEALTH TRACKING FIELDS TO RESOURCE_POOL
-- ============================================

-- Health metrics (30-day rolling window)
ALTER TABLE resource_pool
ADD COLUMN IF NOT EXISTS sends_30d INTEGER NOT NULL DEFAULT 0;

ALTER TABLE resource_pool
ADD COLUMN IF NOT EXISTS bounces_30d INTEGER NOT NULL DEFAULT 0;

ALTER TABLE resource_pool
ADD COLUMN IF NOT EXISTS complaints_30d INTEGER NOT NULL DEFAULT 0;

-- Calculated rates (updated by service)
ALTER TABLE resource_pool
ADD COLUMN IF NOT EXISTS bounce_rate NUMERIC(5,4) DEFAULT 0;

ALTER TABLE resource_pool
ADD COLUMN IF NOT EXISTS complaint_rate NUMERIC(6,5) DEFAULT 0;

-- Health status: good, warning, critical
ALTER TABLE resource_pool
ADD COLUMN IF NOT EXISTS health_status TEXT NOT NULL DEFAULT 'good'
CHECK (health_status IN ('good', 'warning', 'critical'));

-- Daily limit override (for health-based reduction)
-- NULL = use default warmup-based limit
-- Set to 35 for warning, 0 for critical
ALTER TABLE resource_pool
ADD COLUMN IF NOT EXISTS daily_limit_override INTEGER;

-- Last health check timestamp
ALTER TABLE resource_pool
ADD COLUMN IF NOT EXISTS health_checked_at TIMESTAMPTZ;

-- ============================================
-- ADD SENDER DOMAIN TO ACTIVITIES
-- ============================================
-- Needed to track which domain sent the email for health calculation

ALTER TABLE activities
ADD COLUMN IF NOT EXISTS sender_domain TEXT;

-- Index for domain health queries
CREATE INDEX IF NOT EXISTS idx_activities_sender_domain
ON activities(sender_domain)
WHERE sender_domain IS NOT NULL;

-- Index for bounce/complaint queries by domain
CREATE INDEX IF NOT EXISTS idx_activities_domain_bounces
ON activities(sender_domain, action, created_at)
WHERE action IN ('bounced', 'complained');

-- ============================================
-- HELPER FUNCTION: Get domain health metrics
-- ============================================

CREATE OR REPLACE FUNCTION get_domain_health_metrics(domain_value TEXT)
RETURNS TABLE (
    sends_30d BIGINT,
    bounces_30d BIGINT,
    complaints_30d BIGINT,
    bounce_rate NUMERIC,
    complaint_rate NUMERIC
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        COUNT(*) FILTER (WHERE action = 'sent')::BIGINT as sends_30d,
        COUNT(*) FILTER (WHERE action = 'bounced')::BIGINT as bounces_30d,
        COUNT(*) FILTER (WHERE action = 'complained')::BIGINT as complaints_30d,
        CASE
            WHEN COUNT(*) FILTER (WHERE action = 'sent') > 0
            THEN (COUNT(*) FILTER (WHERE action = 'bounced')::NUMERIC /
                  COUNT(*) FILTER (WHERE action = 'sent')::NUMERIC)
            ELSE 0
        END as bounce_rate,
        CASE
            WHEN COUNT(*) FILTER (WHERE action = 'sent') > 0
            THEN (COUNT(*) FILTER (WHERE action = 'complained')::NUMERIC /
                  COUNT(*) FILTER (WHERE action = 'sent')::NUMERIC)
            ELSE 0
        END as complaint_rate
    FROM activities
    WHERE sender_domain = domain_value
      AND created_at >= NOW() - INTERVAL '30 days'
      AND channel = 'email';
END;
$$ LANGUAGE plpgsql STABLE;

-- ============================================
-- HELPER FUNCTION: Determine health status
-- ============================================

CREATE OR REPLACE FUNCTION determine_health_status(
    bounce_rate NUMERIC,
    complaint_rate NUMERIC
) RETURNS TEXT AS $$
BEGIN
    -- Critical: >5% bounce OR >0.1% complaint
    IF bounce_rate > 0.05 OR complaint_rate > 0.001 THEN
        RETURN 'critical';
    -- Warning: 2-5% bounce OR 0.05-0.1% complaint
    ELSIF bounce_rate > 0.02 OR complaint_rate > 0.0005 THEN
        RETURN 'warning';
    -- Good: <2% bounce AND <0.05% complaint
    ELSE
        RETURN 'good';
    END IF;
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- ============================================
-- HELPER FUNCTION: Get daily limit for health status
-- ============================================

CREATE OR REPLACE FUNCTION get_health_daily_limit(health_status TEXT)
RETURNS INTEGER AS $$
BEGIN
    CASE health_status
        WHEN 'good' THEN RETURN 50;
        WHEN 'warning' THEN RETURN 35;
        WHEN 'critical' THEN RETURN 0;
        ELSE RETURN 50;
    END CASE;
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- ============================================
-- COMMENTS
-- ============================================

COMMENT ON COLUMN resource_pool.sends_30d IS 'Total emails sent in last 30 days';
COMMENT ON COLUMN resource_pool.bounces_30d IS 'Total bounces in last 30 days';
COMMENT ON COLUMN resource_pool.complaints_30d IS 'Total spam complaints in last 30 days';
COMMENT ON COLUMN resource_pool.bounce_rate IS 'Calculated bounce rate (bounces_30d / sends_30d)';
COMMENT ON COLUMN resource_pool.complaint_rate IS 'Calculated complaint rate (complaints_30d / sends_30d)';
COMMENT ON COLUMN resource_pool.health_status IS 'Domain health: good (<2% bounce, <0.05% complaint), warning (2-5%, 0.05-0.1%), critical (>5%, >0.1%)';
COMMENT ON COLUMN resource_pool.daily_limit_override IS 'Override daily limit based on health (NULL=use default, 35=warning, 0=critical)';
COMMENT ON COLUMN resource_pool.health_checked_at IS 'Last time health metrics were calculated';
COMMENT ON COLUMN activities.sender_domain IS 'Domain used to send email (for health tracking)';

COMMENT ON FUNCTION get_domain_health_metrics IS 'Calculate 30-day health metrics for a domain from activities';
COMMENT ON FUNCTION determine_health_status IS 'Determine health status from bounce/complaint rates';
COMMENT ON FUNCTION get_health_daily_limit IS 'Get daily send limit based on health status';

-- ============================================
-- VERIFICATION
-- ============================================
-- Run this after migration to verify:
-- SELECT column_name, data_type FROM information_schema.columns
-- WHERE table_name = 'resource_pool' AND column_name LIKE '%health%' OR column_name LIKE '%30d%';
