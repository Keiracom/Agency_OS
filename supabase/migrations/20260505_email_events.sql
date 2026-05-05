-- 20260505_email_events.sql
-- Task #20 — Email Integration Backend (aiden/email-backend)
-- Stores per-message Resend send + webhook event history.

CREATE SCHEMA IF NOT EXISTS keiracom_admin;

CREATE TABLE IF NOT EXISTS keiracom_admin.email_events (
    id              BIGSERIAL PRIMARY KEY,
    message_id      TEXT UNIQUE,
    to_email        TEXT NOT NULL,
    from_email      TEXT NOT NULL,
    subject         TEXT,
    status          TEXT NOT NULL DEFAULT 'queued',
    events          JSONB NOT NULL DEFAULT '[]'::jsonb,
    sent_at         TIMESTAMPTZ,
    last_event_at   TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS email_events_status_idx
    ON keiracom_admin.email_events (status);
CREATE INDEX IF NOT EXISTS email_events_to_email_idx
    ON keiracom_admin.email_events (to_email);
CREATE INDEX IF NOT EXISTS email_events_created_at_idx
    ON keiracom_admin.email_events (created_at DESC);

ALTER TABLE keiracom_admin.email_events ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS email_events_anon_select
    ON keiracom_admin.email_events;
CREATE POLICY email_events_anon_select
    ON keiracom_admin.email_events
    FOR SELECT
    TO anon
    USING (TRUE);
