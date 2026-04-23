-- approvals table + approval_status enum.
-- Part of ORION phase-2-slice-8 (Track A) — ORM model migration.
--
-- Defensive: table may already exist from PR #389 backfill.
-- Uses IF NOT EXISTS + ADD COLUMN IF NOT EXISTS throughout.

-- Enum type (idempotent via DO block)
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'approval_status') THEN
        CREATE TYPE approval_status AS ENUM (
            'pending',
            'approved',
            'rejected',
            'deferred',
            'edit_applied'
        );
    END IF;
END$$;

-- Table (idempotent)
CREATE TABLE IF NOT EXISTS approvals (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id   UUID NOT NULL,
    prospect_id UUID,
    channel     VARCHAR(32) NOT NULL DEFAULT 'email',
    draft_subject VARCHAR(512),
    draft_body  TEXT,
    status      approval_status NOT NULL DEFAULT 'pending',
    approved_at TIMESTAMPTZ,
    approved_by UUID,
    notes       TEXT,
    payload     JSONB,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Add any columns that may be missing on a pre-existing table
ALTER TABLE approvals
    ADD COLUMN IF NOT EXISTS prospect_id   UUID,
    ADD COLUMN IF NOT EXISTS channel       VARCHAR(32) NOT NULL DEFAULT 'email',
    ADD COLUMN IF NOT EXISTS draft_subject VARCHAR(512),
    ADD COLUMN IF NOT EXISTS draft_body    TEXT,
    ADD COLUMN IF NOT EXISTS approved_at   TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS approved_by   UUID,
    ADD COLUMN IF NOT EXISTS notes         TEXT,
    ADD COLUMN IF NOT EXISTS payload       JSONB;

-- Indexes (idempotent)
CREATE INDEX IF NOT EXISTS idx_approvals_client_status
    ON approvals (client_id, status);

CREATE INDEX IF NOT EXISTS idx_approvals_prospect
    ON approvals (prospect_id);
