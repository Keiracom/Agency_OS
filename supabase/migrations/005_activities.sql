-- FILE: supabase/migrations/005_activities.sql
-- PURPOSE: Activity log with message ID for email threading
-- PHASE: 1 (Foundation + DevOps)
-- TASK: DB-006
-- DEPENDENCIES: 004_leads_suppression.sql
-- RULES APPLIED:
--   - Rule 1: Follow blueprint exactly
--   - Rule 18: Email threading via In-Reply-To headers

-- ============================================
-- ACTIVITIES (Outreach & Engagement Log)
-- ============================================

CREATE TABLE activities (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id UUID NOT NULL REFERENCES clients(id),
    campaign_id UUID NOT NULL REFERENCES campaigns(id),
    lead_id UUID NOT NULL REFERENCES leads(id),

    -- Channel and action
    channel channel_type NOT NULL,
    action TEXT NOT NULL,   -- sent, delivered, opened, clicked, replied, bounced, unsubscribed, converted

    -- === Email Threading (Rule 18) ===
    provider_message_id TEXT,   -- For In-Reply-To headers
    thread_id TEXT,             -- Conversation thread ID
    in_reply_to TEXT,           -- Parent message ID (for replies)

    -- === Content Reference ===
    sequence_step INTEGER,      -- Which step in the sequence
    subject TEXT,               -- Email subject (for reference)
    content_preview TEXT,       -- First 200 chars of content

    -- === Provider Details ===
    provider TEXT,              -- resend, postmark, twilio, heyreach, etc.
    provider_status TEXT,       -- Provider-specific status
    provider_response JSONB,    -- Full provider response (for debugging)

    -- === Engagement Metadata ===
    metadata JSONB DEFAULT '{}',

    -- Link tracking
    link_clicked TEXT,          -- Which link was clicked
    device_type TEXT,           -- desktop, mobile, tablet
    user_agent TEXT,
    ip_address INET,
    geo_country TEXT,
    geo_city TEXT,

    -- === Intent (for replies) ===
    intent intent_type,         -- Classified intent for replies
    intent_confidence FLOAT,    -- Confidence of intent classification

    -- === Timestamps ===
    created_at TIMESTAMPTZ DEFAULT NOW(),
    processed_at TIMESTAMPTZ    -- When the action was processed
);

-- ============================================
-- INDEXES (Performance Critical)
-- ============================================

-- Primary lookups
CREATE INDEX idx_activities_client_created ON activities(client_id, created_at DESC);
CREATE INDEX idx_activities_lead_created ON activities(lead_id, created_at DESC);
CREATE INDEX idx_activities_campaign_channel ON activities(campaign_id, channel, action);

-- Email threading (Rule 18)
CREATE INDEX idx_activities_thread ON activities(lead_id, channel, provider_message_id)
    WHERE provider_message_id IS NOT NULL;
CREATE INDEX idx_activities_thread_id ON activities(thread_id)
    WHERE thread_id IS NOT NULL;

-- Reply lookup for threading
CREATE INDEX idx_activities_replies ON activities(lead_id, channel)
    WHERE action = 'replied';

-- Provider message ID lookup
CREATE INDEX idx_activities_provider_msg ON activities(provider_message_id)
    WHERE provider_message_id IS NOT NULL;

-- Recent activity lookup
CREATE INDEX idx_activities_recent ON activities(created_at DESC);

-- ============================================
-- ACTIVITY STATS (Materialized for Performance)
-- ============================================

-- This table is updated by triggers on activities
CREATE TABLE activity_stats (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id UUID NOT NULL REFERENCES clients(id),
    campaign_id UUID REFERENCES campaigns(id),
    lead_id UUID REFERENCES leads(id),
    date DATE NOT NULL DEFAULT CURRENT_DATE,

    -- Counts by channel
    email_sent INTEGER DEFAULT 0,
    email_delivered INTEGER DEFAULT 0,
    email_opened INTEGER DEFAULT 0,
    email_clicked INTEGER DEFAULT 0,
    email_replied INTEGER DEFAULT 0,
    email_bounced INTEGER DEFAULT 0,

    sms_sent INTEGER DEFAULT 0,
    sms_delivered INTEGER DEFAULT 0,
    sms_replied INTEGER DEFAULT 0,

    linkedin_sent INTEGER DEFAULT 0,
    linkedin_accepted INTEGER DEFAULT 0,
    linkedin_replied INTEGER DEFAULT 0,

    voice_called INTEGER DEFAULT 0,
    voice_answered INTEGER DEFAULT 0,
    voice_voicemail INTEGER DEFAULT 0,

    mail_sent INTEGER DEFAULT 0,
    mail_delivered INTEGER DEFAULT 0,

    -- Aggregates
    total_sent INTEGER DEFAULT 0,
    total_replied INTEGER DEFAULT 0,
    total_converted INTEGER DEFAULT 0,

    -- Timestamps
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    -- Unique constraint for upsert
    CONSTRAINT unique_activity_stats UNIQUE (client_id, campaign_id, lead_id, date)
);

-- Index for stats lookup
CREATE INDEX idx_activity_stats_client ON activity_stats(client_id, date DESC);
CREATE INDEX idx_activity_stats_campaign ON activity_stats(campaign_id, date DESC)
    WHERE campaign_id IS NOT NULL;

-- ============================================
-- TRIGGER: Update activity stats
-- ============================================

CREATE OR REPLACE FUNCTION update_activity_stats()
RETURNS TRIGGER AS $$
BEGIN
    -- Upsert stats row
    INSERT INTO activity_stats (client_id, campaign_id, lead_id, date)
    VALUES (NEW.client_id, NEW.campaign_id, NEW.lead_id, CURRENT_DATE)
    ON CONFLICT (client_id, campaign_id, lead_id, date)
    DO UPDATE SET updated_at = NOW();

    -- Update specific counter based on channel and action
    IF NEW.channel = 'email' THEN
        CASE NEW.action
            WHEN 'sent' THEN
                UPDATE activity_stats
                SET email_sent = email_sent + 1, total_sent = total_sent + 1
                WHERE client_id = NEW.client_id
                AND campaign_id = NEW.campaign_id
                AND lead_id = NEW.lead_id
                AND date = CURRENT_DATE;
            WHEN 'delivered' THEN
                UPDATE activity_stats
                SET email_delivered = email_delivered + 1
                WHERE client_id = NEW.client_id
                AND campaign_id = NEW.campaign_id
                AND lead_id = NEW.lead_id
                AND date = CURRENT_DATE;
            WHEN 'opened' THEN
                UPDATE activity_stats
                SET email_opened = email_opened + 1
                WHERE client_id = NEW.client_id
                AND campaign_id = NEW.campaign_id
                AND lead_id = NEW.lead_id
                AND date = CURRENT_DATE;
            WHEN 'clicked' THEN
                UPDATE activity_stats
                SET email_clicked = email_clicked + 1
                WHERE client_id = NEW.client_id
                AND campaign_id = NEW.campaign_id
                AND lead_id = NEW.lead_id
                AND date = CURRENT_DATE;
            WHEN 'replied' THEN
                UPDATE activity_stats
                SET email_replied = email_replied + 1, total_replied = total_replied + 1
                WHERE client_id = NEW.client_id
                AND campaign_id = NEW.campaign_id
                AND lead_id = NEW.lead_id
                AND date = CURRENT_DATE;
            WHEN 'bounced' THEN
                UPDATE activity_stats
                SET email_bounced = email_bounced + 1
                WHERE client_id = NEW.client_id
                AND campaign_id = NEW.campaign_id
                AND lead_id = NEW.lead_id
                AND date = CURRENT_DATE;
            ELSE NULL;
        END CASE;
    ELSIF NEW.channel = 'sms' THEN
        CASE NEW.action
            WHEN 'sent' THEN
                UPDATE activity_stats
                SET sms_sent = sms_sent + 1, total_sent = total_sent + 1
                WHERE client_id = NEW.client_id
                AND campaign_id = NEW.campaign_id
                AND lead_id = NEW.lead_id
                AND date = CURRENT_DATE;
            WHEN 'delivered' THEN
                UPDATE activity_stats
                SET sms_delivered = sms_delivered + 1
                WHERE client_id = NEW.client_id
                AND campaign_id = NEW.campaign_id
                AND lead_id = NEW.lead_id
                AND date = CURRENT_DATE;
            WHEN 'replied' THEN
                UPDATE activity_stats
                SET sms_replied = sms_replied + 1, total_replied = total_replied + 1
                WHERE client_id = NEW.client_id
                AND campaign_id = NEW.campaign_id
                AND lead_id = NEW.lead_id
                AND date = CURRENT_DATE;
            ELSE NULL;
        END CASE;
    END IF;

    -- Handle conversions
    IF NEW.action = 'converted' THEN
        UPDATE activity_stats
        SET total_converted = total_converted + 1
        WHERE client_id = NEW.client_id
        AND campaign_id = NEW.campaign_id
        AND lead_id = NEW.lead_id
        AND date = CURRENT_DATE;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER activities_update_stats
    AFTER INSERT ON activities
    FOR EACH ROW
    EXECUTE FUNCTION update_activity_stats();

-- ============================================
-- HELPER: Get thread for email reply
-- ============================================

CREATE OR REPLACE FUNCTION get_email_thread(p_lead_id UUID)
RETURNS TABLE (
    message_id TEXT,
    subject TEXT,
    action TEXT,
    created_at TIMESTAMPTZ
) AS $$
    SELECT
        provider_message_id,
        subject,
        action,
        created_at
    FROM activities
    WHERE lead_id = p_lead_id
    AND channel = 'email'
    AND provider_message_id IS NOT NULL
    ORDER BY created_at DESC;
$$ LANGUAGE sql STABLE;

-- ============================================
-- VERIFICATION CHECKLIST
-- ============================================
-- [x] activities table with all fields from PART 5
-- [x] provider_message_id for email threading (Rule 18)
-- [x] thread_id and in_reply_to for conversation tracking
-- [x] Intent classification fields
-- [x] Composite indexes for performance
-- [x] idx_activities_thread for email threading
-- [x] activity_stats table for aggregated metrics
-- [x] Trigger to update stats on insert
-- [x] get_email_thread() function for reply context
