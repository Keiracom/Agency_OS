-- Add stage_metrics JSONB column to business_universe for GOV-8 compliance.
-- Stores per-stage enrichment data (DFS bundle, social posts, drop forensics)
-- so intelligence is never lost on domain drop or re-run.
ALTER TABLE business_universe ADD COLUMN IF NOT EXISTS stage_metrics jsonb;

-- Add unique constraint on domain for ON CONFLICT (domain) DO UPDATE support.
-- Required by H1/H3/H7 persistence fixes. No duplicates confirmed pre-creation.
CREATE UNIQUE INDEX IF NOT EXISTS business_universe_domain_unique_idx
    ON business_universe (domain) WHERE domain IS NOT NULL AND domain != '';
