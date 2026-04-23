-- Migration 320: nurture_drip_state table
-- Idempotent — safe to re-run.

CREATE TABLE IF NOT EXISTS nurture_drip_state (
    prospect_id       UUID        PRIMARY KEY,
    client_id         UUID        NOT NULL,
    next_channel      TEXT        CHECK (next_channel IN ('email', 'linkedin')),
    next_scheduled_at TIMESTAMPTZ,
    touches_sent      INT         NOT NULL DEFAULT 0,
    status            TEXT        NOT NULL DEFAULT 'active'
                                  CHECK (status IN ('active', 'exhausted', 'paused')),
    started_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at        TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS nurture_drip_state_client_status_idx
    ON nurture_drip_state (client_id, status);
