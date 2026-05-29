-- 20260529_keiracom_spawn_attribution_chain_fields.sql
-- Adds the 4 columns Atlas's api_agent_cold_start.py writes:
--   cost_aud, latency_ms, chain_id, task_id
-- (`role` maps to the existing `callsign` column — no new column needed.)
--
-- Already applied LIVE via Supabase MCP 2026-05-29 to unblock Atlas's build for
-- the V1 dress rehearsal — this migration is the persisted record so future
-- deploys + branch builds match the live schema.
--
-- Idempotent (ADD COLUMN IF NOT EXISTS). Non-blocking. KEI-87 write guard:
-- SET LOCAL agency_os.callsign = 'dave' required for public-schema ALTER.

SET LOCAL agency_os.callsign = 'dave';

ALTER TABLE public.keiracom_spawn_attribution
  ADD COLUMN IF NOT EXISTS cost_aud   NUMERIC(10,6) NOT NULL DEFAULT 0,
  ADD COLUMN IF NOT EXISTS latency_ms NUMERIC(10,2),
  ADD COLUMN IF NOT EXISTS chain_id   TEXT,
  ADD COLUMN IF NOT EXISTS task_id    TEXT;
