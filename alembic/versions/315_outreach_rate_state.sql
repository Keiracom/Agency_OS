-- outreach_rate_state — tracks per-channel rolling counters and warming state
-- for the outreach rate limiter (PHASE-2.1-2.2 slice 2, Track 2.2-next).

CREATE TABLE IF NOT EXISTS outreach_rate_state (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    channel TEXT NOT NULL,                       -- 'email' | 'linkedin' | 'voice' | 'sms'
    account_id TEXT NOT NULL,                    -- mailbox_id / linkedin_seat_id / phone_id
    window_start TIMESTAMPTZ NOT NULL,           -- start of the rolling window this row counts
    count INTEGER NOT NULL DEFAULT 0,            -- events observed in this window
    warming_day INTEGER,                         -- NULL for non-warming channels; 1..14 for email warming
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (channel, account_id, window_start)
);

CREATE INDEX IF NOT EXISTS idx_ors_channel_account
    ON outreach_rate_state (channel, account_id);

CREATE INDEX IF NOT EXISTS idx_ors_window
    ON outreach_rate_state (window_start);

-- Per-prospect frequency cap: count emails per prospect over rolling 14-day window
CREATE TABLE IF NOT EXISTS outreach_prospect_frequency (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    prospect_id UUID NOT NULL,
    channel TEXT NOT NULL,
    sent_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_opf_prospect_channel_sent
    ON outreach_prospect_frequency (prospect_id, channel, sent_at DESC);
