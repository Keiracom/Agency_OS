-- linkedin_connection_state — per (account, prospect) connect-request lifecycle.
-- Backs src/outreach/safety/linkedin_account_state.py (PHASE-2-SLICE-5 Track C).
--
-- State FSM:
--   (none) -> connect_sent -> accepted  (allows DMs, terminal)
--                          -> rejected  (skip LinkedIn for prospect, terminal)
--                          -> stale_skipped (pending > 7d, auto-routed past LinkedIn)
--
-- The dispatcher records connect_sent; webhooks from Unipile flip accepted/rejected;
-- the hourly flow calls auto_skip_stale_connects() to advance long-pending rows.

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'linkedin_conn_state') THEN
        CREATE TYPE linkedin_conn_state AS ENUM (
            'connect_sent', 'accepted', 'rejected', 'stale_skipped'
        );
    END IF;
END$$;

CREATE TABLE IF NOT EXISTS linkedin_connection_state (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    account_id TEXT NOT NULL,
    prospect_id UUID NOT NULL,
    state linkedin_conn_state NOT NULL DEFAULT 'connect_sent',
    sent_at TIMESTAMPTZ,
    accepted_at TIMESTAMPTZ,
    days_pending INTEGER NOT NULL DEFAULT 0,
    extra JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (account_id, prospect_id)
);

-- Dispatcher lookup: "has this (account, prospect) pair got an active connect?"
CREATE INDEX IF NOT EXISTS idx_lcs_account_prospect
    ON linkedin_connection_state (account_id, prospect_id);

-- Stale-connect scan: cheap partial index for pending rows ordered by sent_at
CREATE INDEX IF NOT EXISTS idx_lcs_pending_sent_at
    ON linkedin_connection_state (sent_at)
    WHERE state = 'connect_sent';

-- State rollups for health dashboards
CREATE INDEX IF NOT EXISTS idx_lcs_state ON linkedin_connection_state (state);
