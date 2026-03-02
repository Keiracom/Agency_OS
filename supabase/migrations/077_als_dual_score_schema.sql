-- Migration 077: ALS Dual-Score Schema
-- Directive: #151
-- Decision: Waterfall v3 Decision #3 (2026-03-01)
-- 
-- Replaces single ALS score with dual-score model:
-- - reachability_score (0-100): Contact data quality (can we reach them?)
-- - propensity_score (0-100): Likelihood to convert (should we reach them?)
--
-- als_score column is DEPRECATED but retained for backward compatibility.
-- New code should use reachability_score + propensity_score.
-- Migration path: als_score will be removed in a future migration after
-- all code references are updated.

BEGIN;

-- Add reachability_score to lead_pool
ALTER TABLE lead_pool
ADD COLUMN IF NOT EXISTS reachability_score INTEGER;

-- Add propensity_score to lead_pool
ALTER TABLE lead_pool
ADD COLUMN IF NOT EXISTS propensity_score INTEGER;

-- Add constraints for new columns
ALTER TABLE lead_pool
ADD CONSTRAINT IF NOT EXISTS valid_reachability_score
CHECK (reachability_score IS NULL OR (reachability_score >= 0 AND reachability_score <= 100));

ALTER TABLE lead_pool
ADD CONSTRAINT IF NOT EXISTS valid_propensity_score
CHECK (propensity_score IS NULL OR (propensity_score >= 0 AND propensity_score <= 100));

-- Mark als_score as deprecated via column comment
COMMENT ON COLUMN lead_pool.als_score IS 
'DEPRECATED (Directive #151): Use reachability_score + propensity_score instead. Will be removed in future migration.';

-- Add indexes for new score columns
CREATE INDEX IF NOT EXISTS idx_lead_pool_reachability_score 
ON lead_pool (client_id, reachability_score DESC) 
WHERE reachability_score IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_lead_pool_propensity_score 
ON lead_pool (client_id, propensity_score DESC) 
WHERE propensity_score IS NOT NULL;

-- Add combined score index for dual-score queries
CREATE INDEX IF NOT EXISTS idx_lead_pool_dual_score 
ON lead_pool (client_id, propensity_score DESC, reachability_score DESC) 
WHERE propensity_score IS NOT NULL AND reachability_score IS NOT NULL;

-- Same changes for leads table (if it exists with als_score)
ALTER TABLE leads
ADD COLUMN IF NOT EXISTS reachability_score INTEGER;

ALTER TABLE leads
ADD COLUMN IF NOT EXISTS propensity_score INTEGER;

ALTER TABLE leads
ADD CONSTRAINT IF NOT EXISTS valid_reachability_score
CHECK (reachability_score IS NULL OR (reachability_score >= 0 AND reachability_score <= 100));

ALTER TABLE leads
ADD CONSTRAINT IF NOT EXISTS valid_propensity_score
CHECK (propensity_score IS NULL OR (propensity_score >= 0 AND propensity_score <= 100));

COMMENT ON COLUMN leads.als_score IS 
'DEPRECATED (Directive #151): Use reachability_score + propensity_score instead. Will be removed in future migration.';

COMMIT;

-- Note: als_score NOT dropped to maintain backward compatibility.
-- All 200+ code references must be migrated before removal.
-- See: memory/decisions/waterfall_v3_decisions.md Decision #3
