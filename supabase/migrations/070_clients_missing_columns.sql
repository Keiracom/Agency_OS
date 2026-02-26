-- Migration: 070_clients_missing_columns.sql
-- Bug #11: Add missing columns to clients table
-- Full model audit per LAW I-A

-- Emergency pause columns (Phase H, Item 43 - kill switch feature)
ALTER TABLE clients ADD COLUMN IF NOT EXISTS paused_at TIMESTAMPTZ NULL;
ALTER TABLE clients ADD COLUMN IF NOT EXISTS pause_reason TEXT NULL;
ALTER TABLE clients ADD COLUMN IF NOT EXISTS paused_by_user_id UUID NULL REFERENCES users(id);

-- Digest preferences columns (Phase H, Item 44)
ALTER TABLE clients ADD COLUMN IF NOT EXISTS digest_enabled BOOLEAN NOT NULL DEFAULT TRUE;
ALTER TABLE clients ADD COLUMN IF NOT EXISTS digest_frequency TEXT NOT NULL DEFAULT 'daily';
ALTER TABLE clients ADD COLUMN IF NOT EXISTS digest_send_hour INTEGER NOT NULL DEFAULT 7;
ALTER TABLE clients ADD COLUMN IF NOT EXISTS digest_timezone TEXT NOT NULL DEFAULT 'Australia/Sydney';
ALTER TABLE clients ADD COLUMN IF NOT EXISTS digest_recipients JSONB NULL;
ALTER TABLE clients ADD COLUMN IF NOT EXISTS last_digest_sent_at TIMESTAMPTZ NULL;

-- Founding member billing fields (Step 8/8)
ALTER TABLE clients ADD COLUMN IF NOT EXISTS deposit_paid BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE clients ADD COLUMN IF NOT EXISTS subscription_activated_at TIMESTAMPTZ NULL;

-- Add index for pause queries (find all paused clients quickly)
CREATE INDEX IF NOT EXISTS idx_clients_paused_at ON clients(paused_at) WHERE paused_at IS NOT NULL;

-- Add index for digest scheduling queries
CREATE INDEX IF NOT EXISTS idx_clients_digest_schedule ON clients(digest_enabled, digest_send_hour) WHERE digest_enabled = TRUE;
