-- Migration: add_last_rescored_at
-- Purpose: Add last_rescored_at column to business_universe for monthly re-score tracking.
--          Prevents re-scoring the same row more than once every 30 days.

ALTER TABLE business_universe ADD COLUMN IF NOT EXISTS last_rescored_at TIMESTAMPTZ;
CREATE INDEX IF NOT EXISTS idx_bu_last_rescored_at ON business_universe (last_rescored_at);
