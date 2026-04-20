-- F5: dm_messages table for Stage 10 message generation output
-- Per #339 audit recommendation: normalised storage, one row per channel per DM

BEGIN;

CREATE TABLE IF NOT EXISTS dm_messages (
    id                          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    business_universe_id        UUID NOT NULL REFERENCES business_universe(id) ON DELETE CASCADE,
    business_decision_makers_id UUID NOT NULL REFERENCES business_decision_makers(id) ON DELETE CASCADE,
    channel                     TEXT NOT NULL CHECK (channel IN ('email', 'linkedin', 'sms', 'voice')),
    subject                     TEXT,
    body                        TEXT NOT NULL,
    model                       TEXT,  -- sonnet-4-5 | haiku-4-5
    cost_usd                    NUMERIC(10, 6),
    status                      TEXT NOT NULL DEFAULT 'draft' CHECK (status IN ('draft', 'approved', 'sent', 'bounced', 'replied')),
    generated_at                TIMESTAMPTZ NOT NULL DEFAULT now(),
    approved_at                 TIMESTAMPTZ,
    approved_by                 UUID,
    sent_at                     TIMESTAMPTZ,
    created_at                  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at                  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Indexes for common query patterns
CREATE INDEX IF NOT EXISTS idx_dm_messages_bdm_channel
    ON dm_messages(business_decision_makers_id, channel);

CREATE INDEX IF NOT EXISTS idx_dm_messages_bu_status
    ON dm_messages(business_universe_id, status);

CREATE INDEX IF NOT EXISTS idx_dm_messages_status
    ON dm_messages(status);

CREATE INDEX IF NOT EXISTS idx_dm_messages_channel_status
    ON dm_messages(channel, status);

-- Enable RLS from creation (coordinated with F3)
ALTER TABLE dm_messages ENABLE ROW LEVEL SECURITY;

-- Service role has full access (pipeline writes)
CREATE POLICY dm_messages_service_all ON dm_messages
    FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

-- Authenticated users: read-only via BU tenant chain
-- Full tenant-scoped policy added in F3 after tenancy model ratified
-- For now: authenticated can read own messages (placeholder)
CREATE POLICY dm_messages_auth_select ON dm_messages
    FOR SELECT
    TO authenticated
    USING (true);

COMMENT ON TABLE dm_messages IS 'Stage 10 message generation output. One row per channel per DM. Status tracks lifecycle: draft→approved→sent→bounced/replied.';

COMMIT;
