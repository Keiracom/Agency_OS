-- Migration 078: als_score dual-score stub
-- CEO Directive #153 Phase 1
-- als_score becomes computed column from reachability_score

-- Step 1: Add dual-score columns if not exist (from migration 077)
ALTER TABLE lead_pool 
ADD COLUMN IF NOT EXISTS reachability_score INTEGER DEFAULT 0,
ADD COLUMN IF NOT EXISTS propensity_score INTEGER DEFAULT 0;

-- Step 2: Backfill reachability_score from existing als_score
UPDATE lead_pool 
SET reachability_score = COALESCE(als_score, 0)
WHERE reachability_score IS NULL OR reachability_score = 0;

-- Step 3: Rename existing als_score to legacy
ALTER TABLE lead_pool RENAME COLUMN als_score TO als_score_legacy;

-- Step 4: Add computed stub column
ALTER TABLE lead_pool 
ADD COLUMN als_score INTEGER GENERATED ALWAYS AS (reachability_score) STORED;

-- Step 5: Repeat for leads table if als_score exists there
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'leads' AND column_name = 'als_score') THEN
        ALTER TABLE leads ADD COLUMN IF NOT EXISTS reachability_score INTEGER DEFAULT 0;
        ALTER TABLE leads ADD COLUMN IF NOT EXISTS propensity_score INTEGER DEFAULT 0;
        UPDATE leads SET reachability_score = COALESCE(als_score, 0) WHERE reachability_score IS NULL OR reachability_score = 0;
        ALTER TABLE leads RENAME COLUMN als_score TO als_score_legacy;
        ALTER TABLE leads ADD COLUMN als_score INTEGER GENERATED ALWAYS AS (reachability_score) STORED;
    END IF;
END $$;

-- Indexes on new columns
CREATE INDEX IF NOT EXISTS idx_lead_pool_reachability ON lead_pool(reachability_score DESC);
CREATE INDEX IF NOT EXISTS idx_lead_pool_propensity ON lead_pool(propensity_score DESC);
