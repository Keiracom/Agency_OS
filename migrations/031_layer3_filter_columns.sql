-- Migration 031: Layer 3 filter columns
-- Directive #274
ALTER TABLE business_universe
  ADD COLUMN IF NOT EXISTS filter_reason text,
  ADD COLUMN IF NOT EXISTS backlinks_count integer,
  ADD COLUMN IF NOT EXISTS domain_rank integer;

CREATE INDEX IF NOT EXISTS idx_bu_pipeline_stage ON business_universe(pipeline_stage)
  WHERE pipeline_stage IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_bu_filtered ON business_universe(pipeline_stage)
  WHERE pipeline_stage = -1;
