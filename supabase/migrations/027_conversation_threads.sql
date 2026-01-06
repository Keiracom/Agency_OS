-- Migration: 027_conversation_threads.sql
-- Phase: 24D (Conversation Threading)
-- Purpose: Track conversation threads and analyze reply patterns for CIS learning
-- Date: 2026-01-06

-- ============================================================================
-- 1. CREATE CONVERSATION THREADS TABLE
-- ============================================================================

CREATE TABLE IF NOT EXISTS conversation_threads (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    lead_id UUID NOT NULL REFERENCES leads(id) ON DELETE CASCADE,
    campaign_id UUID REFERENCES campaigns(id) ON DELETE SET NULL,

    -- Thread status
    status TEXT DEFAULT 'active',  -- 'active', 'resolved', 'stale', 'converted'
    channel channel_type NOT NULL,

    -- Thread metrics
    message_count INTEGER DEFAULT 0,
    our_message_count INTEGER DEFAULT 0,
    their_message_count INTEGER DEFAULT 0,

    -- Timing
    started_at TIMESTAMPTZ DEFAULT NOW(),
    last_message_at TIMESTAMPTZ,
    last_our_message_at TIMESTAMPTZ,
    last_their_message_at TIMESTAMPTZ,

    -- Response timing stats
    avg_our_response_minutes INTEGER,  -- How fast we respond
    avg_their_response_minutes INTEGER,  -- How fast they respond

    -- Outcome
    outcome TEXT,  -- 'converted', 'rejected', 'no_response', 'ongoing', 'meeting_booked'
    outcome_at TIMESTAMPTZ,
    outcome_reason TEXT,  -- Details about the outcome

    -- Escalation
    escalated_to_human BOOLEAN DEFAULT FALSE,
    escalated_at TIMESTAMPTZ,
    escalation_reason TEXT,

    -- Audit
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    CONSTRAINT valid_thread_status CHECK (status IN ('active', 'resolved', 'stale', 'converted', 'dead')),
    CONSTRAINT valid_thread_outcome CHECK (outcome IS NULL OR outcome IN (
        'converted', 'rejected', 'no_response', 'ongoing', 'meeting_booked', 'referral', 'future_interest'
    ))
);

-- ============================================================================
-- 2. CREATE THREAD MESSAGES TABLE
-- ============================================================================

CREATE TABLE IF NOT EXISTS thread_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    thread_id UUID NOT NULL REFERENCES conversation_threads(id) ON DELETE CASCADE,
    activity_id UUID REFERENCES activities(id) ON DELETE SET NULL,  -- Our outbound message
    reply_id UUID REFERENCES replies(id) ON DELETE SET NULL,  -- Their inbound message

    -- Direction
    direction TEXT NOT NULL,  -- 'outbound' (us) or 'inbound' (them)

    -- Content
    content TEXT NOT NULL,
    content_preview TEXT,  -- First 200 chars

    -- Analysis (populated by AI)
    sentiment TEXT,  -- 'positive', 'neutral', 'negative', 'mixed'
    sentiment_score FLOAT,  -- -1 to 1
    intent TEXT,  -- 'interested', 'question', 'objection', 'not_interested', 'meeting_request', etc.
    objection_type TEXT,  -- 'timing', 'budget', 'authority', 'need', 'competitor', 'trust'
    question_extracted TEXT,  -- The actual question they asked
    topics_mentioned TEXT[],  -- Key topics in this message

    -- Timing
    sent_at TIMESTAMPTZ NOT NULL,
    response_time_minutes INTEGER,  -- Time since previous message in thread

    -- Position
    position INTEGER NOT NULL,  -- 1, 2, 3... in thread

    created_at TIMESTAMPTZ DEFAULT NOW(),

    CONSTRAINT valid_direction CHECK (direction IN ('outbound', 'inbound')),
    CONSTRAINT valid_sentiment CHECK (sentiment IS NULL OR sentiment IN ('positive', 'neutral', 'negative', 'mixed')),
    CONSTRAINT valid_objection_type CHECK (objection_type IS NULL OR objection_type IN (
        'timing', 'budget', 'authority', 'need', 'competitor', 'trust', 'other'
    ))
);

-- ============================================================================
-- 3. ADD THREAD REFERENCE TO ACTIVITIES AND REPLIES
-- ============================================================================

ALTER TABLE activities ADD COLUMN IF NOT EXISTS conversation_thread_id UUID REFERENCES conversation_threads(id) ON DELETE SET NULL;
ALTER TABLE replies ADD COLUMN IF NOT EXISTS conversation_thread_id UUID REFERENCES conversation_threads(id) ON DELETE SET NULL;

-- Add analysis fields to replies
ALTER TABLE replies ADD COLUMN IF NOT EXISTS objection_type TEXT;
ALTER TABLE replies ADD COLUMN IF NOT EXISTS question_extracted TEXT;
ALTER TABLE replies ADD COLUMN IF NOT EXISTS sentiment TEXT;
ALTER TABLE replies ADD COLUMN IF NOT EXISTS sentiment_score FLOAT;
ALTER TABLE replies ADD COLUMN IF NOT EXISTS topics_mentioned TEXT[];
ALTER TABLE replies ADD COLUMN IF NOT EXISTS ai_analysis_at TIMESTAMPTZ;

-- ============================================================================
-- 4. CREATE REJECTION REASONS ENUM AND FIELDS
-- ============================================================================

-- Create enum type if it doesn't exist
DO $$ BEGIN
    CREATE TYPE rejection_reason_type AS ENUM (
        'timing_not_now',
        'budget_constraints',
        'using_competitor',
        'not_decision_maker',
        'no_need',
        'bad_experience',
        'too_busy',
        'not_interested_generic',
        'do_not_contact',
        'wrong_contact',
        'company_policy',
        'other'
    );
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- Add rejection tracking to leads
ALTER TABLE leads ADD COLUMN IF NOT EXISTS rejection_reason rejection_reason_type;
ALTER TABLE leads ADD COLUMN IF NOT EXISTS rejection_notes TEXT;
ALTER TABLE leads ADD COLUMN IF NOT EXISTS rejection_at TIMESTAMPTZ;
ALTER TABLE leads ADD COLUMN IF NOT EXISTS objections_raised TEXT[];  -- History of objections

-- ============================================================================
-- 5. CREATE INDEXES FOR PERFORMANCE
-- ============================================================================

-- Conversation threads indexes
CREATE INDEX IF NOT EXISTS idx_threads_client ON conversation_threads(client_id);
CREATE INDEX IF NOT EXISTS idx_threads_lead ON conversation_threads(lead_id);
CREATE INDEX IF NOT EXISTS idx_threads_campaign ON conversation_threads(campaign_id);
CREATE INDEX IF NOT EXISTS idx_threads_status ON conversation_threads(status);
CREATE INDEX IF NOT EXISTS idx_threads_outcome ON conversation_threads(outcome);
CREATE INDEX IF NOT EXISTS idx_threads_last_message ON conversation_threads(last_message_at);

-- Thread messages indexes
CREATE INDEX IF NOT EXISTS idx_thread_messages_thread ON thread_messages(thread_id);
CREATE INDEX IF NOT EXISTS idx_thread_messages_direction ON thread_messages(direction);
CREATE INDEX IF NOT EXISTS idx_thread_messages_sentiment ON thread_messages(sentiment);
CREATE INDEX IF NOT EXISTS idx_thread_messages_objection ON thread_messages(objection_type);
CREATE INDEX IF NOT EXISTS idx_thread_messages_intent ON thread_messages(intent);
CREATE INDEX IF NOT EXISTS idx_thread_messages_position ON thread_messages(thread_id, position);

-- Activity/Reply thread links
CREATE INDEX IF NOT EXISTS idx_activities_thread ON activities(conversation_thread_id) WHERE conversation_thread_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_replies_thread ON replies(conversation_thread_id) WHERE conversation_thread_id IS NOT NULL;

-- Lead rejection
CREATE INDEX IF NOT EXISTS idx_leads_rejection ON leads(rejection_reason) WHERE rejection_reason IS NOT NULL;

-- ============================================================================
-- 6. TRIGGER TO UPDATE THREAD STATS ON NEW MESSAGE
-- ============================================================================

CREATE OR REPLACE FUNCTION update_thread_stats()
RETURNS TRIGGER AS $$
DECLARE
    prev_message RECORD;
    response_minutes INTEGER;
BEGIN
    -- Calculate response time from previous message
    SELECT sent_at, direction INTO prev_message
    FROM thread_messages
    WHERE thread_id = NEW.thread_id
    AND position = NEW.position - 1;

    IF prev_message IS NOT NULL THEN
        response_minutes := EXTRACT(EPOCH FROM (NEW.sent_at - prev_message.sent_at)) / 60;
        NEW.response_time_minutes := response_minutes;
    END IF;

    -- Update thread stats
    UPDATE conversation_threads SET
        message_count = message_count + 1,
        our_message_count = our_message_count + CASE WHEN NEW.direction = 'outbound' THEN 1 ELSE 0 END,
        their_message_count = their_message_count + CASE WHEN NEW.direction = 'inbound' THEN 1 ELSE 0 END,
        last_message_at = NEW.sent_at,
        last_our_message_at = CASE WHEN NEW.direction = 'outbound' THEN NEW.sent_at ELSE last_our_message_at END,
        last_their_message_at = CASE WHEN NEW.direction = 'inbound' THEN NEW.sent_at ELSE last_their_message_at END,
        updated_at = NOW()
    WHERE id = NEW.thread_id;

    -- Update average response times
    IF NEW.direction = 'outbound' AND NEW.response_time_minutes IS NOT NULL THEN
        UPDATE conversation_threads SET
            avg_our_response_minutes = (
                SELECT AVG(response_time_minutes)::INTEGER
                FROM thread_messages
                WHERE thread_id = NEW.thread_id
                AND direction = 'outbound'
                AND response_time_minutes IS NOT NULL
            )
        WHERE id = NEW.thread_id;
    ELSIF NEW.direction = 'inbound' AND NEW.response_time_minutes IS NOT NULL THEN
        UPDATE conversation_threads SET
            avg_their_response_minutes = (
                SELECT AVG(response_time_minutes)::INTEGER
                FROM thread_messages
                WHERE thread_id = NEW.thread_id
                AND direction = 'inbound'
                AND response_time_minutes IS NOT NULL
            )
        WHERE id = NEW.thread_id;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS on_thread_message ON thread_messages;
CREATE TRIGGER on_thread_message
    BEFORE INSERT ON thread_messages
    FOR EACH ROW
    EXECUTE FUNCTION update_thread_stats();

-- ============================================================================
-- 7. TRIGGER TO MARK STALE THREADS
-- ============================================================================

CREATE OR REPLACE FUNCTION mark_stale_threads()
RETURNS void AS $$
BEGIN
    -- Mark threads as stale if no activity for 14 days
    UPDATE conversation_threads
    SET status = 'stale',
        updated_at = NOW()
    WHERE status = 'active'
    AND last_message_at < NOW() - INTERVAL '14 days';

    -- Mark threads as dead if no activity for 30 days
    UPDATE conversation_threads
    SET status = 'dead',
        outcome = COALESCE(outcome, 'no_response'),
        outcome_at = COALESCE(outcome_at, NOW()),
        updated_at = NOW()
    WHERE status IN ('active', 'stale')
    AND last_message_at < NOW() - INTERVAL '30 days';
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- 8. HELPER FUNCTION TO GET CONVERSATION ANALYTICS
-- ============================================================================

CREATE OR REPLACE FUNCTION get_conversation_analytics(
    p_client_id UUID,
    p_days INTEGER DEFAULT 30
)
RETURNS TABLE (
    total_threads BIGINT,
    active_threads BIGINT,
    converted_threads BIGINT,
    rejected_threads BIGINT,
    avg_messages_per_thread NUMERIC,
    avg_our_response_minutes NUMERIC,
    avg_their_response_minutes NUMERIC,
    conversion_rate NUMERIC,
    top_objections JSONB,
    sentiment_distribution JSONB
) AS $$
BEGIN
    RETURN QUERY
    WITH thread_stats AS (
        SELECT
            COUNT(*) as total,
            COUNT(*) FILTER (WHERE status = 'active') as active,
            COUNT(*) FILTER (WHERE outcome = 'converted' OR outcome = 'meeting_booked') as converted,
            COUNT(*) FILTER (WHERE outcome = 'rejected') as rejected,
            AVG(message_count) as avg_messages,
            AVG(avg_our_response_minutes) as avg_our_resp,
            AVG(avg_their_response_minutes) as avg_their_resp
        FROM conversation_threads
        WHERE client_id = p_client_id
        AND created_at >= NOW() - (p_days || ' days')::INTERVAL
    ),
    objection_counts AS (
        SELECT objection_type, COUNT(*) as cnt
        FROM thread_messages tm
        JOIN conversation_threads ct ON ct.id = tm.thread_id
        WHERE ct.client_id = p_client_id
        AND tm.objection_type IS NOT NULL
        AND ct.created_at >= NOW() - (p_days || ' days')::INTERVAL
        GROUP BY objection_type
        ORDER BY cnt DESC
        LIMIT 5
    ),
    sentiment_counts AS (
        SELECT sentiment, COUNT(*) as cnt
        FROM thread_messages tm
        JOIN conversation_threads ct ON ct.id = tm.thread_id
        WHERE ct.client_id = p_client_id
        AND tm.direction = 'inbound'
        AND tm.sentiment IS NOT NULL
        AND ct.created_at >= NOW() - (p_days || ' days')::INTERVAL
        GROUP BY sentiment
    )
    SELECT
        ts.total::BIGINT,
        ts.active::BIGINT,
        ts.converted::BIGINT,
        ts.rejected::BIGINT,
        ROUND(ts.avg_messages, 2),
        ROUND(ts.avg_our_resp, 2),
        ROUND(ts.avg_their_resp, 2),
        ROUND(ts.converted::NUMERIC / NULLIF(ts.total, 0) * 100, 2),
        (SELECT jsonb_object_agg(objection_type, cnt) FROM objection_counts),
        (SELECT jsonb_object_agg(sentiment, cnt) FROM sentiment_counts)
    FROM thread_stats ts;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- 9. HELPER FUNCTION TO GET COMMON QUESTIONS
-- ============================================================================

CREATE OR REPLACE FUNCTION get_common_questions(
    p_client_id UUID,
    p_days INTEGER DEFAULT 90,
    p_limit INTEGER DEFAULT 10
)
RETURNS TABLE (
    question TEXT,
    frequency BIGINT,
    avg_sentiment_score NUMERIC
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        tm.question_extracted as question,
        COUNT(*) as frequency,
        ROUND(AVG(tm.sentiment_score), 2) as avg_sentiment_score
    FROM thread_messages tm
    JOIN conversation_threads ct ON ct.id = tm.thread_id
    WHERE ct.client_id = p_client_id
    AND tm.question_extracted IS NOT NULL
    AND tm.question_extracted != ''
    AND ct.created_at >= NOW() - (p_days || ' days')::INTERVAL
    GROUP BY tm.question_extracted
    ORDER BY frequency DESC
    LIMIT p_limit;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- 10. ROW LEVEL SECURITY
-- ============================================================================

ALTER TABLE conversation_threads ENABLE ROW LEVEL SECURITY;
ALTER TABLE thread_messages ENABLE ROW LEVEL SECURITY;

-- Users can only see threads for their clients
CREATE POLICY conversation_threads_client_isolation ON conversation_threads
    FOR ALL
    USING (
        client_id IN (
            SELECT client_id FROM memberships
            WHERE user_id = auth.uid()
        )
    );

CREATE POLICY thread_messages_client_isolation ON thread_messages
    FOR ALL
    USING (
        thread_id IN (
            SELECT id FROM conversation_threads WHERE client_id IN (
                SELECT client_id FROM memberships
                WHERE user_id = auth.uid()
            )
        )
    );

-- ============================================================================
-- COMPLETE
-- ============================================================================
