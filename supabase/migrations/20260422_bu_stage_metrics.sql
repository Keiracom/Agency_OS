-- Add stage_metrics JSONB column to business_universe for GOV-8 compliance.
-- Stores per-stage enrichment data (DFS bundle, social posts, drop forensics)
-- so intelligence is never lost on domain drop or re-run.
ALTER TABLE business_universe ADD COLUMN IF NOT EXISTS stage_metrics jsonb;

-- Drop redundant duplicate of uq_bu_domain (same predicate, added in error).
-- The pre-existing uq_bu_domain partial index is sufficient for
-- ON CONFLICT (domain) WHERE domain IS NOT NULL AND domain != '' DO UPDATE.
DROP INDEX IF EXISTS business_universe_domain_unique_idx;
