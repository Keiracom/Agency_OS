-- Add missing GMB columns to leads table
-- Ratified: ARCHITECTURE.md Section 5
-- Directive #218

ALTER TABLE leads
ADD COLUMN IF NOT EXISTS gmb_cid TEXT,
ADD COLUMN IF NOT EXISTS gmb_category TEXT,
ADD COLUMN IF NOT EXISTS gmb_phone TEXT,
ADD COLUMN IF NOT EXISTS gmb_domain TEXT,
ADD COLUMN IF NOT EXISTS gmb_website TEXT,
ADD COLUMN IF NOT EXISTS gmb_address TEXT,
ADD COLUMN IF NOT EXISTS gmb_city TEXT,
ADD COLUMN IF NOT EXISTS gmb_latitude NUMERIC(10,7),
ADD COLUMN IF NOT EXISTS gmb_longitude NUMERIC(10,7);

-- Index for domain lookups
CREATE INDEX IF NOT EXISTS idx_leads_gmb_domain ON leads(gmb_domain);
