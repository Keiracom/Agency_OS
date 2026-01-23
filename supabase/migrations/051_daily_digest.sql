-- Migration: 051_daily_digest.sql
-- Purpose: Add digest preferences to clients table for Phase H Item 44
-- Date: 2026-01-23

-- Add digest preference fields to clients table
ALTER TABLE clients
ADD COLUMN IF NOT EXISTS digest_enabled BOOLEAN DEFAULT true,
ADD COLUMN IF NOT EXISTS digest_frequency TEXT DEFAULT 'daily' CHECK (digest_frequency IN ('daily', 'weekly', 'none')),
ADD COLUMN IF NOT EXISTS digest_send_hour INTEGER DEFAULT 7 CHECK (digest_send_hour >= 0 AND digest_send_hour <= 23),
ADD COLUMN IF NOT EXISTS digest_timezone TEXT DEFAULT 'Australia/Sydney',
ADD COLUMN IF NOT EXISTS digest_recipients JSONB DEFAULT '[]'::jsonb,
ADD COLUMN IF NOT EXISTS last_digest_sent_at TIMESTAMPTZ;

-- Create digest_logs table to track sent digests
CREATE TABLE IF NOT EXISTS digest_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,

    -- Digest metadata
    digest_date DATE NOT NULL,
    digest_type TEXT NOT NULL DEFAULT 'daily' CHECK (digest_type IN ('daily', 'weekly')),

    -- Recipients
    recipients JSONB NOT NULL DEFAULT '[]'::jsonb,

    -- Content snapshot
    metrics_snapshot JSONB NOT NULL DEFAULT '{}'::jsonb,
    content_summary JSONB NOT NULL DEFAULT '{}'::jsonb,

    -- Delivery status
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'sent', 'failed', 'skipped')),
    sent_at TIMESTAMPTZ,
    error_message TEXT,

    -- Engagement tracking
    opened_at TIMESTAMPTZ,
    clicked_at TIMESTAMPTZ,

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT now(),

    UNIQUE(client_id, digest_date, digest_type)
);

-- Create index for efficient digest queries
CREATE INDEX IF NOT EXISTS idx_digest_logs_client_date ON digest_logs(client_id, digest_date DESC);
CREATE INDEX IF NOT EXISTS idx_digest_logs_status ON digest_logs(status) WHERE status = 'pending';

-- RLS policies for digest_logs
ALTER TABLE digest_logs ENABLE ROW LEVEL SECURITY;

-- Users can view their client's digest logs
CREATE POLICY digest_logs_select_policy ON digest_logs
    FOR SELECT
    USING (client_id IN (
        SELECT client_id FROM memberships WHERE user_id = auth.uid()
    ));

-- Service role can insert/update
CREATE POLICY digest_logs_service_insert ON digest_logs
    FOR INSERT
    WITH CHECK (true);

CREATE POLICY digest_logs_service_update ON digest_logs
    FOR UPDATE
    USING (true);

-- Function to get digest data for a client
CREATE OR REPLACE FUNCTION get_digest_data(
    p_client_id UUID,
    p_date DATE DEFAULT CURRENT_DATE - INTERVAL '1 day'
)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    v_result JSONB;
    v_activities_sent INTEGER;
    v_emails_opened INTEGER;
    v_emails_clicked INTEGER;
    v_replies_received INTEGER;
    v_meetings_booked INTEGER;
    v_top_campaigns JSONB;
    v_recent_content JSONB;
BEGIN
    -- Count activities sent on the date
    SELECT COUNT(*) INTO v_activities_sent
    FROM activities a
    JOIN campaigns c ON a.campaign_id = c.id
    WHERE c.client_id = p_client_id
    AND DATE(a.created_at AT TIME ZONE 'Australia/Sydney') = p_date
    AND a.action = 'sent';

    -- Count email opens
    SELECT COUNT(*) INTO v_emails_opened
    FROM activities a
    JOIN campaigns c ON a.campaign_id = c.id
    WHERE c.client_id = p_client_id
    AND DATE(a.created_at AT TIME ZONE 'Australia/Sydney') = p_date
    AND a.action = 'opened';

    -- Count email clicks
    SELECT COUNT(*) INTO v_emails_clicked
    FROM activities a
    JOIN campaigns c ON a.campaign_id = c.id
    WHERE c.client_id = p_client_id
    AND DATE(a.created_at AT TIME ZONE 'Australia/Sydney') = p_date
    AND a.action = 'clicked';

    -- Count replies received
    SELECT COUNT(*) INTO v_replies_received
    FROM activities a
    JOIN campaigns c ON a.campaign_id = c.id
    WHERE c.client_id = p_client_id
    AND DATE(a.created_at AT TIME ZONE 'Australia/Sydney') = p_date
    AND a.action = 'replied';

    -- Count meetings booked
    SELECT COUNT(*) INTO v_meetings_booked
    FROM meetings m
    WHERE m.client_id = p_client_id
    AND DATE(m.created_at AT TIME ZONE 'Australia/Sydney') = p_date;

    -- Get top performing campaigns
    SELECT COALESCE(jsonb_agg(campaign_data), '[]'::jsonb) INTO v_top_campaigns
    FROM (
        SELECT jsonb_build_object(
            'campaign_id', c.id,
            'campaign_name', c.name,
            'sent', COUNT(*) FILTER (WHERE a.action = 'sent'),
            'opened', COUNT(*) FILTER (WHERE a.action = 'opened'),
            'replied', COUNT(*) FILTER (WHERE a.action = 'replied')
        ) as campaign_data
        FROM activities a
        JOIN campaigns c ON a.campaign_id = c.id
        WHERE c.client_id = p_client_id
        AND DATE(a.created_at AT TIME ZONE 'Australia/Sydney') = p_date
        GROUP BY c.id, c.name
        ORDER BY COUNT(*) FILTER (WHERE a.action = 'replied') DESC,
                 COUNT(*) FILTER (WHERE a.action = 'opened') DESC
        LIMIT 5
    ) sub;

    -- Get recent content samples (last 5 emails sent)
    SELECT COALESCE(jsonb_agg(content_data), '[]'::jsonb) INTO v_recent_content
    FROM (
        SELECT jsonb_build_object(
            'activity_id', a.id,
            'channel', a.channel,
            'lead_name', l.first_name || ' ' || l.last_name,
            'company', l.company,
            'subject', a.subject_line,
            'preview', LEFT(a.content_snapshot, 150),
            'sent_at', a.created_at
        ) as content_data
        FROM activities a
        JOIN leads l ON a.lead_id = l.id
        JOIN campaigns c ON a.campaign_id = c.id
        WHERE c.client_id = p_client_id
        AND DATE(a.created_at AT TIME ZONE 'Australia/Sydney') = p_date
        AND a.action = 'sent'
        AND a.channel = 'email'
        ORDER BY a.created_at DESC
        LIMIT 5
    ) sub;

    -- Build result
    v_result := jsonb_build_object(
        'date', p_date,
        'metrics', jsonb_build_object(
            'activities_sent', v_activities_sent,
            'emails_opened', v_emails_opened,
            'emails_clicked', v_emails_clicked,
            'replies_received', v_replies_received,
            'meetings_booked', v_meetings_booked,
            'open_rate', CASE WHEN v_activities_sent > 0
                THEN ROUND((v_emails_opened::NUMERIC / v_activities_sent) * 100, 1)
                ELSE 0 END,
            'reply_rate', CASE WHEN v_activities_sent > 0
                THEN ROUND((v_replies_received::NUMERIC / v_activities_sent) * 100, 1)
                ELSE 0 END
        ),
        'top_campaigns', v_top_campaigns,
        'recent_content', v_recent_content
    );

    RETURN v_result;
END;
$$;

-- Grant execute permission
GRANT EXECUTE ON FUNCTION get_digest_data(UUID, DATE) TO authenticated;
GRANT EXECUTE ON FUNCTION get_digest_data(UUID, DATE) TO service_role;

COMMENT ON TABLE digest_logs IS 'Phase H Item 44: Tracks daily/weekly digest emails sent to clients';
COMMENT ON COLUMN clients.digest_enabled IS 'Phase H Item 44: Whether client receives digest emails';
COMMENT ON COLUMN clients.digest_frequency IS 'Phase H Item 44: How often digest is sent (daily/weekly/none)';
COMMENT ON COLUMN clients.digest_send_hour IS 'Phase H Item 44: Hour of day to send digest (0-23 in client timezone)';
