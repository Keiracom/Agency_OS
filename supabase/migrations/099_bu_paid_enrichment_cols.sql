-- Sprint 3 paid enrichment columns
ALTER TABLE business_universe
  ADD COLUMN IF NOT EXISTS paid_enrichment_completed_at  TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS paid_enrichment_skipped_reason TEXT;
