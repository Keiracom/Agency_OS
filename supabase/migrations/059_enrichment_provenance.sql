-- Migration: 059_enrichment_provenance.sql
-- Purpose: Add enrichment provenance fields for Spam Act compliance
-- CEO Directive #057: Store source URL and capture timestamp for "conspicuous publication" defence
-- Created: 2025-02-19

-- ============================================
-- ENRICHMENT PROVENANCE FIELDS
-- ============================================
-- These fields support the "conspicuous publication" defence under the
-- Australian Spam Act 2003. By storing where and when an email address
-- was captured, we can prove the email was publicly listed at the time
-- of collection.
--
-- Examples of source URLs:
-- - LinkedIn profile: https://www.linkedin.com/in/john-smith-12345/
-- - Company website: https://acme.com.au/about/team/
-- - Google Business: https://business.google.com/...
-- - ABN register: https://abr.business.gov.au/...

-- Add enrichment_source_url - where the email/data was found
ALTER TABLE lead_pool 
ADD COLUMN IF NOT EXISTS enrichment_source_url TEXT;

COMMENT ON COLUMN lead_pool.enrichment_source_url IS 
    'URL where email was publicly listed (LinkedIn, company site, GMB, etc.) - supports Spam Act conspicuous publication defence';

-- Add enrichment_captured_at - when the data was captured
ALTER TABLE lead_pool 
ADD COLUMN IF NOT EXISTS enrichment_captured_at TIMESTAMPTZ;

COMMENT ON COLUMN lead_pool.enrichment_captured_at IS 
    'Timestamp when enrichment data was captured - proves email was publicly listed at this time';

-- Create index for compliance auditing
CREATE INDEX IF NOT EXISTS idx_lead_pool_enrichment_source_url 
    ON lead_pool(enrichment_source_url) 
    WHERE enrichment_source_url IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_lead_pool_enrichment_captured_at 
    ON lead_pool(enrichment_captured_at DESC NULLS LAST);

-- ============================================
-- VERIFICATION CHECKLIST
-- ============================================
-- [x] enrichment_source_url (TEXT) added to lead_pool
-- [x] enrichment_captured_at (TIMESTAMPTZ) added to lead_pool
-- [x] Comments explaining Spam Act compliance purpose
-- [x] Indexes for compliance auditing queries
