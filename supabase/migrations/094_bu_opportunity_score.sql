-- Add opportunity_score to business_universe
-- Was added to leads in 091 but missed BU
-- Directive #218

ALTER TABLE business_universe
ADD COLUMN IF NOT EXISTS opportunity_score INTEGER DEFAULT 0,
ADD COLUMN IF NOT EXISTS opportunity_reason TEXT,
ADD COLUMN IF NOT EXISTS opportunity_updated TIMESTAMPTZ;
