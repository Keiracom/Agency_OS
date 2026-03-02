-- Migration: 076_enrichment_raw_responses.sql
-- Purpose: Store raw API responses from enrichment providers for debugging and reprocessing

CREATE TABLE IF NOT EXISTS enrichment_raw_responses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    lead_id UUID NOT NULL REFERENCES lead_pool(id) ON DELETE CASCADE,
    tier TEXT NOT NULL,           -- e.g. "T1.5_linkedin", "T2_apollo"
    provider TEXT NOT NULL,       -- e.g. "bright_data", "apollo", "hunter"
    raw_json JSONB NOT NULL,      -- full API response payload
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Index for efficient lead lookups
CREATE INDEX IF NOT EXISTS idx_enrichment_raw_responses_lead_id 
    ON enrichment_raw_responses(lead_id);

-- Comment for documentation
COMMENT ON TABLE enrichment_raw_responses IS 'Stores raw API responses from enrichment providers for audit trail and reprocessing';
