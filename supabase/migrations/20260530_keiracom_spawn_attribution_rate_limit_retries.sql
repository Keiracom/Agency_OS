-- ============================================================================
-- 20260530_keiracom_spawn_attribution_rate_limit_retries.sql
--
-- V1-battery hard-gate (Agency_OS-v1-battery-hard-gates — Elliot dispatch
-- 2026-05-30 ~11:35 AEST). Adds rate_limit_retries to keiracom_spawn_attribution
-- so v1_battery_harness can aggregate 429/529 retry counts per chain_id.
--
-- Source: src/keiracom_system/vault/api_agent_cold_start.py — the retry wrapper
-- around anthropic.messages.create returns retry_count; insert_attribution
-- threads it into this column. Default 0 covers the no-retry happy path so the
-- existing INSERT call sites that don't pass retry_count keep working.
--
-- KEI-87 bypass: SET LOCAL agency_os.callsign = 'dave' required for
-- public-schema DDL.
-- ============================================================================

ALTER TABLE public.keiracom_spawn_attribution
  ADD COLUMN IF NOT EXISTS rate_limit_retries INTEGER NOT NULL DEFAULT 0;

COMMENT ON COLUMN public.keiracom_spawn_attribution.rate_limit_retries IS
  '429/529 retry attempts performed by api_agent_cold_start for this hop. 0 = first call succeeded. >0 means rate-limit pressure observed.';
