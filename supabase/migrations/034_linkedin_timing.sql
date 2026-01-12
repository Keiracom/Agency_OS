-- ============================================
-- Migration: 034_linkedin_timing.sql
-- Purpose: LinkedIn action queue and daily state for timing
-- Phase: Unipile Migration - Timing Randomization
-- ============================================

-- Daily state per LinkedIn account
-- Tracks randomized limits and daily progress
CREATE TABLE IF NOT EXISTS linkedin_account_daily_state (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    account_id TEXT NOT NULL,  -- Unipile account ID
    client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    date DATE NOT NULL DEFAULT CURRENT_DATE,
    daily_limit INT NOT NULL,  -- Randomized limit for this day
    actions_sent INT NOT NULL DEFAULT 0,
    last_action_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- One record per account per day
    UNIQUE(account_id, date)
);

-- Indexes for daily state lookups
CREATE INDEX IF NOT EXISTS idx_linkedin_daily_state_account_date
ON linkedin_account_daily_state(account_id, date DESC);

CREATE INDEX IF NOT EXISTS idx_linkedin_daily_state_client
ON linkedin_account_daily_state(client_id);

-- Trigger to update updated_at
CREATE OR REPLACE FUNCTION update_linkedin_daily_state_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_linkedin_daily_state_updated ON linkedin_account_daily_state;
CREATE TRIGGER trg_linkedin_daily_state_updated
    BEFORE UPDATE ON linkedin_account_daily_state
    FOR EACH ROW
    EXECUTE FUNCTION update_linkedin_daily_state_updated_at();

-- Action queue for scheduled LinkedIn sends
-- Actions are queued with scheduled times and processed by worker
CREATE TABLE IF NOT EXISTS linkedin_action_queue (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    account_id TEXT NOT NULL,  -- Unipile account ID
    client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    lead_id UUID NOT NULL REFERENCES leads(id) ON DELETE CASCADE,
    campaign_id UUID NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE,

    -- Action details
    action_type TEXT NOT NULL CHECK (action_type IN ('connection', 'message')),
    message_content TEXT,
    recipient_linkedin_url TEXT NOT NULL,

    -- Scheduling
    scheduled_at TIMESTAMPTZ NOT NULL,
    priority INT NOT NULL DEFAULT 0,  -- Higher = more urgent

    -- Status tracking
    status TEXT NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'processing', 'sent', 'failed', 'cancelled', 'rate_limited')),
    attempts INT NOT NULL DEFAULT 0,
    max_attempts INT NOT NULL DEFAULT 3,
    last_error TEXT,

    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    processed_at TIMESTAMPTZ,

    -- Result from Unipile
    provider_response JSONB
);

-- Indexes for queue processing
CREATE INDEX IF NOT EXISTS idx_linkedin_queue_scheduled
ON linkedin_action_queue(scheduled_at)
WHERE status = 'pending';

CREATE INDEX IF NOT EXISTS idx_linkedin_queue_account_status
ON linkedin_action_queue(account_id, status);

CREATE INDEX IF NOT EXISTS idx_linkedin_queue_client
ON linkedin_action_queue(client_id);

CREATE INDEX IF NOT EXISTS idx_linkedin_queue_lead
ON linkedin_action_queue(lead_id);

-- Trigger to update updated_at
DROP TRIGGER IF EXISTS trg_linkedin_queue_updated ON linkedin_action_queue;
CREATE TRIGGER trg_linkedin_queue_updated
    BEFORE UPDATE ON linkedin_action_queue
    FOR EACH ROW
    EXECUTE FUNCTION update_linkedin_daily_state_updated_at();

-- ============================================
-- Helper Functions
-- ============================================

-- Get or create daily state for an account
CREATE OR REPLACE FUNCTION get_or_create_linkedin_daily_state(
    p_account_id TEXT,
    p_client_id UUID,
    p_daily_limit INT DEFAULT 17
)
RETURNS linkedin_account_daily_state AS $$
DECLARE
    v_state linkedin_account_daily_state;
BEGIN
    -- Try to get existing state for today
    SELECT * INTO v_state
    FROM linkedin_account_daily_state
    WHERE account_id = p_account_id
    AND date = CURRENT_DATE;

    -- Create if not exists
    IF NOT FOUND THEN
        INSERT INTO linkedin_account_daily_state (
            account_id, client_id, date, daily_limit
        ) VALUES (
            p_account_id, p_client_id, CURRENT_DATE, p_daily_limit
        )
        RETURNING * INTO v_state;
    END IF;

    RETURN v_state;
END;
$$ LANGUAGE plpgsql;

-- Increment action count atomically
CREATE OR REPLACE FUNCTION increment_linkedin_daily_count(
    p_account_id TEXT
)
RETURNS INT AS $$
DECLARE
    v_new_count INT;
BEGIN
    UPDATE linkedin_account_daily_state
    SET
        actions_sent = actions_sent + 1,
        last_action_at = NOW()
    WHERE account_id = p_account_id
    AND date = CURRENT_DATE
    RETURNING actions_sent INTO v_new_count;

    RETURN COALESCE(v_new_count, 0);
END;
$$ LANGUAGE plpgsql;

-- Check if account can send (under daily limit)
CREATE OR REPLACE FUNCTION can_linkedin_account_send(
    p_account_id TEXT
)
RETURNS BOOLEAN AS $$
DECLARE
    v_state linkedin_account_daily_state;
BEGIN
    SELECT * INTO v_state
    FROM linkedin_account_daily_state
    WHERE account_id = p_account_id
    AND date = CURRENT_DATE;

    IF NOT FOUND THEN
        RETURN TRUE;  -- No state = no actions yet today
    END IF;

    RETURN v_state.actions_sent < v_state.daily_limit;
END;
$$ LANGUAGE plpgsql;

-- Get next pending action from queue
CREATE OR REPLACE FUNCTION get_next_linkedin_action(
    p_account_id TEXT DEFAULT NULL
)
RETURNS linkedin_action_queue AS $$
DECLARE
    v_action linkedin_action_queue;
BEGIN
    -- Lock and fetch next pending action
    IF p_account_id IS NULL THEN
        SELECT * INTO v_action
        FROM linkedin_action_queue
        WHERE status = 'pending'
        AND scheduled_at <= NOW()
        AND attempts < max_attempts
        ORDER BY priority DESC, scheduled_at ASC
        LIMIT 1
        FOR UPDATE SKIP LOCKED;
    ELSE
        SELECT * INTO v_action
        FROM linkedin_action_queue
        WHERE account_id = p_account_id
        AND status = 'pending'
        AND scheduled_at <= NOW()
        AND attempts < max_attempts
        ORDER BY priority DESC, scheduled_at ASC
        LIMIT 1
        FOR UPDATE SKIP LOCKED;
    END IF;

    -- Mark as processing if found
    IF FOUND THEN
        UPDATE linkedin_action_queue
        SET status = 'processing', attempts = attempts + 1
        WHERE id = v_action.id;
    END IF;

    RETURN v_action;
END;
$$ LANGUAGE plpgsql;

-- ============================================
-- Row Level Security
-- ============================================

ALTER TABLE linkedin_account_daily_state ENABLE ROW LEVEL SECURITY;
ALTER TABLE linkedin_action_queue ENABLE ROW LEVEL SECURITY;

-- Daily state policies
CREATE POLICY "Service role can manage daily state"
ON linkedin_account_daily_state FOR ALL
USING (auth.role() = 'service_role');

-- Note: User-level RLS will be added when client_memberships table exists
-- For now, only service role has access (backend operations)
-- CREATE POLICY "Users can view own client daily state"
-- ON linkedin_account_daily_state FOR SELECT
-- USING (
--     client_id IN (
--         SELECT client_id FROM client_memberships
--         WHERE user_id = auth.uid()
--     )
-- );

-- Action queue policies
CREATE POLICY "Service role can manage queue"
ON linkedin_action_queue FOR ALL
USING (auth.role() = 'service_role');

-- Note: User-level RLS will be added when client_memberships table exists
-- CREATE POLICY "Users can view own client queue"
-- ON linkedin_action_queue FOR SELECT
-- USING (
--     client_id IN (
--         SELECT client_id FROM client_memberships
--         WHERE user_id = auth.uid()
--     )
-- );

-- CREATE POLICY "Users can cancel own queue items"
-- ON linkedin_action_queue FOR UPDATE
-- USING (
--     client_id IN (
--         SELECT client_id FROM client_memberships
--         WHERE user_id = auth.uid()
--     )
-- )
-- WITH CHECK (status = 'cancelled');

-- ============================================
-- Comments
-- ============================================

COMMENT ON TABLE linkedin_account_daily_state IS
'Tracks daily LinkedIn action limits and counts per account';

COMMENT ON TABLE linkedin_action_queue IS
'Queue for scheduled LinkedIn actions with humanized timing';

COMMENT ON FUNCTION get_or_create_linkedin_daily_state IS
'Gets or creates daily state record for a LinkedIn account';

COMMENT ON FUNCTION increment_linkedin_daily_count IS
'Atomically increments the daily action count for an account';

COMMENT ON FUNCTION can_linkedin_account_send IS
'Checks if an account is under its daily limit';

COMMENT ON FUNCTION get_next_linkedin_action IS
'Gets and locks the next pending action from the queue';
