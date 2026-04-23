-- BU lifecycle — outreach_status enum + last_outreach_at jsonb + signal snapshot fields.
-- Part of PHASE-2-SLICE-4 (Track B) — supports Phase 2.1 dashboard hooks that
-- query outreach_status for hot-prospect + funnel + stats.
--
-- last_outreach_at JSONB shape:
-- {
--   "email":    "2026-04-23T10:00:00Z",
--   "linkedin": "2026-04-22T14:30:00Z",
--   "voice":    null,
--   "sms":      null
-- }

-- Enum type (idempotent via DO block)
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'bu_outreach_status') THEN
        CREATE TYPE bu_outreach_status AS ENUM (
            'pending', 'active', 'replied', 'converted', 'suppressed'
        );
    END IF;
END$$;

ALTER TABLE business_universe
    ADD COLUMN IF NOT EXISTS outreach_status bu_outreach_status NOT NULL DEFAULT 'pending',
    ADD COLUMN IF NOT EXISTS last_outreach_at JSONB NOT NULL DEFAULT '{}'::jsonb,
    ADD COLUMN IF NOT EXISTS signal_snapshot_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS signal_delta JSONB NOT NULL DEFAULT '{}'::jsonb,
    ADD COLUMN IF NOT EXISTS agency_notes TEXT;

-- Backfill existing rows: DEFAULT 'pending' handles new rows; explicit UPDATE
-- catches any row that might have been backfilled with NULL prior to the
-- NOT NULL constraint (defensive — idempotent no-op if column just added).
UPDATE business_universe
SET outreach_status = 'pending'
WHERE outreach_status IS NULL;

CREATE INDEX IF NOT EXISTS idx_bu_outreach_status
    ON business_universe (outreach_status);

-- Partial index for hot-prospect attention card: pending + high score
CREATE INDEX IF NOT EXISTS idx_bu_pending_for_release
    ON business_universe (outreach_status, created_at DESC)
    WHERE outreach_status = 'pending';
