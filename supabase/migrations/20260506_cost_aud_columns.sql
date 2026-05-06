-- FILE: supabase/migrations/20260506_cost_aud_columns.sql
-- PURPOSE: Add per-row cost_aud tracking to email_events + campaign_sends.
-- TASK: Track 1 audit Gap 3.3 — cost visibility was missing across all
-- send paths. AUD-only per LAW II. DECIMAL(8,4) gives a $9,999.9999 per-row
-- ceiling with sub-cent precision (Resend ~$0.0001 AUD per email; SmartLead
-- subscription is flat-rate so per-row cost is bookkeeping only).

-- 1. keiracom_admin.email_events — every Resend send writes one row here
ALTER TABLE keiracom_admin.email_events
    ADD COLUMN IF NOT EXISTS cost_aud DECIMAL(8, 4) NOT NULL DEFAULT 0;

COMMENT ON COLUMN keiracom_admin.email_events.cost_aud IS
    'Per-send cost in AUD. Resend at ~$0.0001/send. Backfilled rows pre-2026-05-06 are 0.';

-- 2. public.campaign_sends — every CampaignExecutor send writes one row here
ALTER TABLE public.campaign_sends
    ADD COLUMN IF NOT EXISTS cost_aud DECIMAL(8, 4) NOT NULL DEFAULT 0;

COMMENT ON COLUMN public.campaign_sends.cost_aud IS
    'Per-send cost in AUD. Mirrors email_events.cost_aud for the same message.';

-- 3. Lightweight aggregate index for run-level cost reporting
-- (campaign_name, status) is a sensible partial index; omitted here to keep
-- the migration cheap. Add later if reporting queries get slow.
