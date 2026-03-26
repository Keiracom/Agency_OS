-- Outreach channel + message storage — Stages 6 + 7
-- Directive #264

ALTER TABLE business_universe
ADD COLUMN IF NOT EXISTS outreach_channels TEXT[],
ADD COLUMN IF NOT EXISTS outreach_messages JSONB;
