-- Migration: 026_email_engagement.sql
-- Phase: 24C (Email Engagement Tracking)
-- Purpose: Track email opens, clicks, and engagement timing for CIS WHEN/HOW Detectors
-- Date: 2026-01-06

-- ============================================================================
-- 1. CREATE EMAIL ENGAGEMENT EVENTS TABLE
-- ============================================================================

CREATE TABLE IF NOT EXISTS email_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    activity_id UUID NOT NULL REFERENCES activities(id) ON DELETE CASCADE,
    lead_id UUID NOT NULL REFERENCES leads(id) ON DELETE CASCADE,
    client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,

    -- Event type
    event_type TEXT NOT NULL,  -- 'sent', 'delivered', 'opened', 'clicked', 'bounced', 'complained', 'unsubscribed'
    event_at TIMESTAMPTZ NOT NULL,

    -- Open tracking
    open_count INTEGER DEFAULT 0,
    first_opened_at TIMESTAMPTZ,
    last_opened_at TIMESTAMPTZ,

    -- Click tracking
    clicked_url TEXT,
    click_count INTEGER DEFAULT 0,
    first_clicked_at TIMESTAMPTZ,

    -- Device info (from email client detection)
    device_type TEXT,  -- 'desktop', 'mobile', 'tablet'
    email_client TEXT,  -- 'gmail', 'outlook', 'apple_mail', 'yahoo', etc.
    os_type TEXT,  -- 'windows', 'macos', 'ios', 'android', 'linux'

    -- Geo info (from IP if available)
    open_ip TEXT,
    open_city TEXT,
    open_region TEXT,
    open_country TEXT,

    -- Provider metadata
    provider TEXT,  -- 'salesforge', 'smartlead', 'resend'
    provider_event_id TEXT,  -- External event ID for dedup
    raw_payload JSONB,  -- Store full webhook payload

    created_at TIMESTAMPTZ DEFAULT NOW(),

    CONSTRAINT valid_event_type CHECK (event_type IN (
        'sent', 'delivered', 'opened', 'clicked',
        'bounced', 'complained', 'unsubscribed', 'dropped'
    ))
);

-- ============================================================================
-- 2. ADD ENGAGEMENT SUMMARY FIELDS TO ACTIVITIES
-- ============================================================================

-- Open tracking on activities (summary for quick access)
ALTER TABLE activities ADD COLUMN IF NOT EXISTS email_opened BOOLEAN DEFAULT FALSE;
ALTER TABLE activities ADD COLUMN IF NOT EXISTS email_opened_at TIMESTAMPTZ;
ALTER TABLE activities ADD COLUMN IF NOT EXISTS email_open_count INTEGER DEFAULT 0;

-- Click tracking on activities
ALTER TABLE activities ADD COLUMN IF NOT EXISTS email_clicked BOOLEAN DEFAULT FALSE;
ALTER TABLE activities ADD COLUMN IF NOT EXISTS email_clicked_at TIMESTAMPTZ;
ALTER TABLE activities ADD COLUMN IF NOT EXISTS email_click_count INTEGER DEFAULT 0;

-- Calculated timing fields
ALTER TABLE activities ADD COLUMN IF NOT EXISTS time_to_open_minutes INTEGER;  -- Minutes from send to first open
ALTER TABLE activities ADD COLUMN IF NOT EXISTS time_to_click_minutes INTEGER;  -- Minutes from send to first click
ALTER TABLE activities ADD COLUMN IF NOT EXISTS time_to_reply_minutes INTEGER;  -- Minutes from send to reply

-- ============================================================================
-- 3. ADD TOUCH METADATA TO ACTIVITIES
-- ============================================================================

-- Touch sequence tracking
ALTER TABLE activities ADD COLUMN IF NOT EXISTS touch_number INTEGER;  -- 1st, 2nd, 3rd touch to this lead
ALTER TABLE activities ADD COLUMN IF NOT EXISTS days_since_last_touch INTEGER;  -- Days since previous touch
ALTER TABLE activities ADD COLUMN IF NOT EXISTS sequence_position INTEGER;  -- Position in sequence (1, 2, 3...)

-- Lead timezone tracking for send time optimization
ALTER TABLE activities ADD COLUMN IF NOT EXISTS lead_local_time TIME;  -- What time was it for the lead?
ALTER TABLE activities ADD COLUMN IF NOT EXISTS lead_timezone TEXT;  -- Lead's timezone (from location)
ALTER TABLE activities ADD COLUMN IF NOT EXISTS lead_local_day_of_week INTEGER;  -- 0=Sunday, 6=Saturday

-- ============================================================================
-- 4. ADD TIMEZONE TO LEADS (from location data)
-- ============================================================================

ALTER TABLE leads ADD COLUMN IF NOT EXISTS timezone TEXT;
ALTER TABLE leads ADD COLUMN IF NOT EXISTS timezone_offset INTEGER;  -- Offset from UTC in minutes

-- ============================================================================
-- 5. CREATE INDEXES FOR PERFORMANCE
-- ============================================================================

-- Email events indexes
CREATE INDEX IF NOT EXISTS idx_email_events_activity ON email_events(activity_id);
CREATE INDEX IF NOT EXISTS idx_email_events_lead ON email_events(lead_id);
CREATE INDEX IF NOT EXISTS idx_email_events_client ON email_events(client_id);
CREATE INDEX IF NOT EXISTS idx_email_events_type ON email_events(event_type);
CREATE INDEX IF NOT EXISTS idx_email_events_time ON email_events(event_at);
CREATE INDEX IF NOT EXISTS idx_email_events_provider_event ON email_events(provider, provider_event_id);

-- Activity engagement indexes
CREATE INDEX IF NOT EXISTS idx_activities_opened ON activities(email_opened) WHERE email_opened = TRUE;
CREATE INDEX IF NOT EXISTS idx_activities_clicked ON activities(email_clicked) WHERE email_clicked = TRUE;
CREATE INDEX IF NOT EXISTS idx_activities_touch_number ON activities(touch_number);
CREATE INDEX IF NOT EXISTS idx_activities_lead_timezone ON activities(lead_timezone);

-- Lead timezone index
CREATE INDEX IF NOT EXISTS idx_leads_timezone ON leads(timezone) WHERE timezone IS NOT NULL;

-- ============================================================================
-- 6. TRIGGER TO UPDATE ACTIVITY STATS ON EMAIL EVENT
-- ============================================================================

CREATE OR REPLACE FUNCTION update_activity_email_stats()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.event_type = 'opened' THEN
        UPDATE activities SET
            email_opened = TRUE,
            email_opened_at = COALESCE(email_opened_at, NEW.event_at),
            email_open_count = COALESCE(email_open_count, 0) + 1,
            time_to_open_minutes = CASE
                WHEN time_to_open_minutes IS NULL
                THEN EXTRACT(EPOCH FROM (NEW.event_at - created_at)) / 60
                ELSE time_to_open_minutes
            END
        WHERE id = NEW.activity_id;

    ELSIF NEW.event_type = 'clicked' THEN
        UPDATE activities SET
            email_clicked = TRUE,
            email_clicked_at = COALESCE(email_clicked_at, NEW.event_at),
            email_click_count = COALESCE(email_click_count, 0) + 1,
            time_to_click_minutes = CASE
                WHEN time_to_click_minutes IS NULL
                THEN EXTRACT(EPOCH FROM (NEW.event_at - created_at)) / 60
                ELSE time_to_click_minutes
            END
        WHERE id = NEW.activity_id;

    ELSIF NEW.event_type = 'bounced' THEN
        -- Mark the activity as bounced
        UPDATE activities SET
            provider_status = 'bounced'
        WHERE id = NEW.activity_id;

        -- Update lead status if hard bounce
        UPDATE leads SET
            email_status = 'invalid',
            is_bounced = TRUE
        WHERE id = NEW.lead_id;

    ELSIF NEW.event_type = 'unsubscribed' THEN
        -- Mark lead as unsubscribed
        UPDATE leads SET
            is_unsubscribed = TRUE
        WHERE id = NEW.lead_id;

    ELSIF NEW.event_type = 'complained' THEN
        -- Mark lead as complained (spam report)
        UPDATE leads SET
            is_unsubscribed = TRUE,
            do_not_contact = TRUE
        WHERE id = NEW.lead_id;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Drop existing trigger if exists, then create
DROP TRIGGER IF EXISTS on_email_event ON email_events;
CREATE TRIGGER on_email_event
    AFTER INSERT ON email_events
    FOR EACH ROW
    EXECUTE FUNCTION update_activity_email_stats();

-- ============================================================================
-- 7. TRIGGER TO CALCULATE TOUCH METADATA ON ACTIVITY INSERT
-- ============================================================================

CREATE OR REPLACE FUNCTION calculate_touch_metadata()
RETURNS TRIGGER AS $$
DECLARE
    last_touch RECORD;
    touch_count INTEGER;
    lead_tz TEXT;
BEGIN
    -- Only for outbound activities (sent messages)
    IF NEW.action NOT IN ('sent', 'email_sent', 'sms_sent', 'linkedin_sent', 'connection_sent', 'message_sent') THEN
        RETURN NEW;
    END IF;

    -- Count previous touches to this lead from this client
    SELECT COUNT(*) INTO touch_count
    FROM activities
    WHERE lead_id = NEW.lead_id
    AND client_id = NEW.client_id
    AND action IN ('sent', 'email_sent', 'sms_sent', 'linkedin_sent', 'connection_sent', 'message_sent')
    AND id != NEW.id;

    NEW.touch_number := touch_count + 1;

    -- Find last touch to calculate days_since_last_touch
    SELECT created_at INTO last_touch
    FROM activities
    WHERE lead_id = NEW.lead_id
    AND client_id = NEW.client_id
    AND action IN ('sent', 'email_sent', 'sms_sent', 'linkedin_sent', 'connection_sent', 'message_sent')
    AND id != NEW.id
    ORDER BY created_at DESC
    LIMIT 1;

    IF last_touch IS NOT NULL THEN
        NEW.days_since_last_touch := EXTRACT(DAY FROM (NEW.created_at - last_touch.created_at));
    END IF;

    -- Get lead timezone and calculate local time
    SELECT timezone INTO lead_tz FROM leads WHERE id = NEW.lead_id;

    IF lead_tz IS NOT NULL THEN
        NEW.lead_timezone := lead_tz;
        NEW.lead_local_time := (NEW.created_at AT TIME ZONE lead_tz)::TIME;
        NEW.lead_local_day_of_week := EXTRACT(DOW FROM (NEW.created_at AT TIME ZONE lead_tz));
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Drop existing trigger if exists, then create
DROP TRIGGER IF EXISTS on_activity_touch_metadata ON activities;
CREATE TRIGGER on_activity_touch_metadata
    BEFORE INSERT ON activities
    FOR EACH ROW
    EXECUTE FUNCTION calculate_touch_metadata();

-- ============================================================================
-- 8. HELPER FUNCTION TO GET ENGAGEMENT STATS
-- ============================================================================

CREATE OR REPLACE FUNCTION get_email_engagement_stats(
    p_client_id UUID,
    p_days INTEGER DEFAULT 30
)
RETURNS TABLE (
    total_sent BIGINT,
    total_delivered BIGINT,
    total_opened BIGINT,
    total_clicked BIGINT,
    total_bounced BIGINT,
    total_unsubscribed BIGINT,
    open_rate NUMERIC,
    click_rate NUMERIC,
    click_to_open_rate NUMERIC,
    bounce_rate NUMERIC,
    avg_time_to_open_minutes NUMERIC,
    avg_time_to_click_minutes NUMERIC
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        COUNT(DISTINCT a.id) FILTER (WHERE a.action IN ('sent', 'email_sent'))::BIGINT as total_sent,
        COUNT(DISTINCT e.activity_id) FILTER (WHERE e.event_type = 'delivered')::BIGINT as total_delivered,
        COUNT(DISTINCT a.id) FILTER (WHERE a.email_opened = TRUE)::BIGINT as total_opened,
        COUNT(DISTINCT a.id) FILTER (WHERE a.email_clicked = TRUE)::BIGINT as total_clicked,
        COUNT(DISTINCT e.activity_id) FILTER (WHERE e.event_type = 'bounced')::BIGINT as total_bounced,
        COUNT(DISTINCT e.activity_id) FILTER (WHERE e.event_type = 'unsubscribed')::BIGINT as total_unsubscribed,
        ROUND(
            COUNT(DISTINCT a.id) FILTER (WHERE a.email_opened = TRUE)::NUMERIC /
            NULLIF(COUNT(DISTINCT a.id) FILTER (WHERE a.action IN ('sent', 'email_sent')), 0) * 100,
            2
        ) as open_rate,
        ROUND(
            COUNT(DISTINCT a.id) FILTER (WHERE a.email_clicked = TRUE)::NUMERIC /
            NULLIF(COUNT(DISTINCT a.id) FILTER (WHERE a.action IN ('sent', 'email_sent')), 0) * 100,
            2
        ) as click_rate,
        ROUND(
            COUNT(DISTINCT a.id) FILTER (WHERE a.email_clicked = TRUE)::NUMERIC /
            NULLIF(COUNT(DISTINCT a.id) FILTER (WHERE a.email_opened = TRUE), 0) * 100,
            2
        ) as click_to_open_rate,
        ROUND(
            COUNT(DISTINCT e.activity_id) FILTER (WHERE e.event_type = 'bounced')::NUMERIC /
            NULLIF(COUNT(DISTINCT a.id) FILTER (WHERE a.action IN ('sent', 'email_sent')), 0) * 100,
            2
        ) as bounce_rate,
        ROUND(AVG(a.time_to_open_minutes) FILTER (WHERE a.time_to_open_minutes IS NOT NULL), 2) as avg_time_to_open_minutes,
        ROUND(AVG(a.time_to_click_minutes) FILTER (WHERE a.time_to_click_minutes IS NOT NULL), 2) as avg_time_to_click_minutes
    FROM activities a
    LEFT JOIN email_events e ON e.activity_id = a.id
    WHERE a.client_id = p_client_id
    AND a.created_at >= NOW() - (p_days || ' days')::INTERVAL
    AND a.channel = 'email';
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- 9. HELPER FUNCTION TO GET OPTIMAL SEND TIMES
-- ============================================================================

CREATE OR REPLACE FUNCTION get_optimal_send_times(
    p_client_id UUID,
    p_days INTEGER DEFAULT 90
)
RETURNS TABLE (
    day_of_week INTEGER,
    hour_of_day INTEGER,
    total_sent BIGINT,
    total_opened BIGINT,
    open_rate NUMERIC,
    avg_time_to_open NUMERIC
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        COALESCE(a.lead_local_day_of_week, EXTRACT(DOW FROM a.created_at)::INTEGER) as day_of_week,
        EXTRACT(HOUR FROM COALESCE(a.lead_local_time, a.created_at::TIME))::INTEGER as hour_of_day,
        COUNT(*)::BIGINT as total_sent,
        COUNT(*) FILTER (WHERE a.email_opened = TRUE)::BIGINT as total_opened,
        ROUND(
            COUNT(*) FILTER (WHERE a.email_opened = TRUE)::NUMERIC /
            NULLIF(COUNT(*), 0) * 100,
            2
        ) as open_rate,
        ROUND(AVG(a.time_to_open_minutes) FILTER (WHERE a.time_to_open_minutes IS NOT NULL), 2) as avg_time_to_open
    FROM activities a
    WHERE a.client_id = p_client_id
    AND a.created_at >= NOW() - (p_days || ' days')::INTERVAL
    AND a.channel = 'email'
    AND a.action IN ('sent', 'email_sent')
    GROUP BY 1, 2
    HAVING COUNT(*) >= 5  -- Minimum sample size
    ORDER BY open_rate DESC NULLS LAST;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- 10. ROW LEVEL SECURITY FOR EMAIL_EVENTS
-- ============================================================================

ALTER TABLE email_events ENABLE ROW LEVEL SECURITY;

-- Users can only see email events for their clients
CREATE POLICY email_events_client_isolation ON email_events
    FOR ALL
    USING (
        client_id IN (
            SELECT client_id FROM memberships
            WHERE user_id = auth.uid()
        )
    );

-- ============================================================================
-- COMPLETE
-- ============================================================================
