-- Migration 021: campaign_lead_messages table for Stage 7 draft storage
-- Directive #252

CREATE TABLE IF NOT EXISTS campaign_lead_messages (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    campaign_lead_id uuid NOT NULL REFERENCES campaign_leads(id) ON DELETE CASCADE,
    channel text NOT NULL CHECK (channel IN ('email', 'linkedin', 'sms', 'voice')),
    subject text,                          -- email only
    body text NOT NULL,
    tone_notes text,                       -- internal: why this angle was chosen
    generation_model text NOT NULL DEFAULT 'claude-haiku',
    generation_cost_aud numeric(8,4),
    status text NOT NULL DEFAULT 'draft' CHECK (status IN ('draft', 'approved', 'edited', 'sent', 'failed', 'skipped')),
    approved_at timestamptz,
    approved_by text,                      -- 'auto' or user identifier
    sent_at timestamptz,
    created_at timestamptz NOT NULL DEFAULT NOW(),
    updated_at timestamptz NOT NULL DEFAULT NOW(),
    UNIQUE(campaign_lead_id, channel)
);

CREATE INDEX IF NOT EXISTS idx_clm_campaign_lead ON campaign_lead_messages(campaign_lead_id);
CREATE INDEX IF NOT EXISTS idx_clm_status ON campaign_lead_messages(status);
