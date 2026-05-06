-- FILE: supabase/migrations/20260506_campaign_sends.sql
-- PURPOSE: Track per-step campaign sends to prevent duplicate outreach
-- TASK: Per-step send tracking for CampaignExecutor

CREATE TABLE IF NOT EXISTS public.campaign_sends (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    prospect_id UUID NOT NULL,
    dm_email TEXT NOT NULL,
    campaign_name TEXT NOT NULL,
    step_number INTEGER NOT NULL,
    message_id TEXT,
    status TEXT NOT NULL DEFAULT 'sent',
    sent_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Unique constraint: one send per prospect per campaign per step
    CONSTRAINT unique_campaign_step_prospect UNIQUE (campaign_name, step_number, dm_email)
);

CREATE INDEX idx_campaign_sends_lookup
    ON public.campaign_sends (campaign_name, step_number, dm_email);

CREATE INDEX idx_campaign_sends_prospect
    ON public.campaign_sends (prospect_id);
