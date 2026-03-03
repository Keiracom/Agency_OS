-- Migration 085: Add campaign discovery config fields
-- CEO Directive #163: CampaignConfig translation layer
-- Add industry_slug, state, lead_volume for QueryTranslator compatibility

-- Step 1: Add industry_slug column
ALTER TABLE campaigns ADD COLUMN IF NOT EXISTS industry_slug TEXT;

-- Step 2: Add state column (Australian state code: NSW, VIC, QLD, SA, WA, TAS, NT, ACT)
ALTER TABLE campaigns ADD COLUMN IF NOT EXISTS state VARCHAR(10);

-- Step 3: Add lead_volume column with default (Ignition tier = 1250)
ALTER TABLE campaigns ADD COLUMN IF NOT EXISTS lead_volume INTEGER NOT NULL DEFAULT 1250;

-- Step 4: Backfill industry_slug from target_industries[1] where available
UPDATE campaigns 
SET industry_slug = target_industries[1] 
WHERE industry_slug IS NULL 
  AND target_industries IS NOT NULL 
  AND array_length(target_industries, 1) > 0;

-- Step 5: Index on industry_slug for discovery queries
CREATE INDEX IF NOT EXISTS idx_campaigns_industry_slug ON campaigns(industry_slug);
