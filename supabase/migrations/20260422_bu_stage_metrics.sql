-- Add stage_metrics JSONB column to business_universe for GOV-8 compliance.
-- Stores per-stage enrichment data (DFS bundle, social posts, drop forensics)
-- so intelligence is never lost on domain drop or re-run.
ALTER TABLE business_universe ADD COLUMN IF NOT EXISTS stage_metrics jsonb;
