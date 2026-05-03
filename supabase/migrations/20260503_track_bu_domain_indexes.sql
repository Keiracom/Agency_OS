-- Track pre-existing business_universe domain indexes into migration set.
-- These exist on live DB (created outside migrations) but were untracked,
-- causing the DROP in 20260422_bu_stage_metrics.sql to reference an index
-- that wasn't in the migration chain. Idempotent — IF NOT EXISTS.

-- Primary btree index for JOIN lookups (e.g. conversion_feedback.py)
CREATE INDEX IF NOT EXISTS idx_bu_domain
    ON business_universe (domain);

-- Unique partial index for ON CONFLICT upserts
-- Predicate matches the standard upsert pattern used across enrichment flows:
-- ON CONFLICT (domain) WHERE domain IS NOT NULL AND domain != '' DO UPDATE
CREATE UNIQUE INDEX IF NOT EXISTS uq_bu_domain
    ON business_universe (domain)
    WHERE domain IS NOT NULL AND domain != '';
