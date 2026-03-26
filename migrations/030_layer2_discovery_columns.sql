-- Migration 030: Layer 2 discovery columns
-- Directive #272
ALTER TABLE business_universe
  ADD COLUMN IF NOT EXISTS discovery_batch_id uuid,
  ADD COLUMN IF NOT EXISTS no_domain boolean NOT NULL DEFAULT false,
  ADD COLUMN IF NOT EXISTS dfs_discovery_category text,
  ADD COLUMN IF NOT EXISTS dfs_discovery_keyword text;

CREATE INDEX IF NOT EXISTS idx_bu_discovery_batch ON business_universe(discovery_batch_id)
  WHERE discovery_batch_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_bu_no_domain ON business_universe(no_domain)
  WHERE no_domain = true;
