-- Migration 080: Add dual-score columns
-- CEO Directive #153 Phase 6
-- Add reachability_score and propensity_score as proper columns

-- Step 1: Add columns to lead_pool
ALTER TABLE lead_pool ADD COLUMN IF NOT EXISTS reachability_score INTEGER;
ALTER TABLE lead_pool ADD COLUMN IF NOT EXISTS propensity_score INTEGER;

-- Step 2: Backfill from als_score
UPDATE lead_pool SET reachability_score = als_score, propensity_score = als_score WHERE als_score IS NOT NULL AND (reachability_score IS NULL OR propensity_score IS NULL);

-- Step 3: Add columns to leads table
ALTER TABLE leads ADD COLUMN IF NOT EXISTS reachability_score INTEGER;
ALTER TABLE leads ADD COLUMN IF NOT EXISTS propensity_score INTEGER;

-- Step 4: Backfill leads table
UPDATE leads SET reachability_score = als_score, propensity_score = als_score WHERE als_score IS NOT NULL AND (reachability_score IS NULL OR propensity_score IS NULL);

-- Step 5: Indexes
CREATE INDEX IF NOT EXISTS idx_lead_pool_reachability ON lead_pool(reachability_score DESC);
CREATE INDEX IF NOT EXISTS idx_lead_pool_propensity ON lead_pool(propensity_score DESC);
CREATE INDEX IF NOT EXISTS idx_leads_reachability ON leads(reachability_score DESC);
CREATE INDEX IF NOT EXISTS idx_leads_propensity ON leads(propensity_score DESC);
