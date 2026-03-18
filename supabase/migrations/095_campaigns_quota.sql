-- Add monthly_quota to campaigns table
-- daily_limit exists but quota loop needs monthly target
-- Directive #218

ALTER TABLE campaigns
ADD COLUMN IF NOT EXISTS monthly_quota INTEGER DEFAULT 1250,
ADD COLUMN IF NOT EXISTS quota_filled_at TIMESTAMPTZ;

-- market_exhausted_at and final_enriched_count already added by #217
-- monthly_quota DEFAULT 1250 covers all existing campaigns
