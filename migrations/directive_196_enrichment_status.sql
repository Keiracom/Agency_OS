-- Directive #196: Partial enrichment status tracking
-- DO NOT RUN AUTOMATICALLY — apply manually via Dave or migration runner
-- This adds a dedicated enrichment_status column to leads for faster querying.
-- The metadata JSONB field is already being used for full tier tracking
-- (see metadata->'enrichment_tracking'). This column is a queryable summary.

-- Add enrichment_status column to leads table
ALTER TABLE leads
  ADD COLUMN IF NOT EXISTS enrichment_status TEXT
    CHECK (enrichment_status IN ('fully_enriched', 'partially_enriched', 'discovery_only'))
    DEFAULT 'discovery_only';

-- Index for fast filtering by enrichment status
CREATE INDEX IF NOT EXISTS idx_leads_enrichment_status ON leads (enrichment_status)
  WHERE deleted_at IS NULL;

-- Backfill: leads with enriched_at already set are fully_enriched
UPDATE leads
SET enrichment_status = 'fully_enriched'
WHERE enriched_at IS NOT NULL
  AND deleted_at IS NULL
  AND enrichment_status = 'discovery_only';

-- Backfill from existing metadata JSONB (for leads enriched via Directive #196 logic)
UPDATE leads
SET enrichment_status = (metadata->'enrichment_tracking'->>'status')::TEXT
WHERE metadata->'enrichment_tracking'->>'status' IS NOT NULL
  AND deleted_at IS NULL;

-- Verify
SELECT enrichment_status, COUNT(*) FROM leads WHERE deleted_at IS NULL GROUP BY enrichment_status;
