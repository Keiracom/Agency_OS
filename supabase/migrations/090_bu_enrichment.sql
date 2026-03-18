-- business_universe enrichment columns
-- Ratified: March 17 2026
-- Directive #215

ALTER TABLE business_universe
ADD COLUMN IF NOT EXISTS gmb_place_id TEXT,
ADD COLUMN IF NOT EXISTS gmb_cid TEXT,
ADD COLUMN IF NOT EXISTS gmb_category TEXT,
ADD COLUMN IF NOT EXISTS gmb_rating NUMERIC(3,1),
ADD COLUMN IF NOT EXISTS gmb_review_count INTEGER,
ADD COLUMN IF NOT EXISTS gmb_phone TEXT,
ADD COLUMN IF NOT EXISTS gmb_website TEXT,
ADD COLUMN IF NOT EXISTS gmb_domain TEXT,
ADD COLUMN IF NOT EXISTS gmb_address TEXT,
ADD COLUMN IF NOT EXISTS gmb_city TEXT,
ADD COLUMN IF NOT EXISTS gmb_latitude NUMERIC(10,7),
ADD COLUMN IF NOT EXISTS gmb_longitude NUMERIC(10,7),
ADD COLUMN IF NOT EXISTS linkedin_company_url TEXT,
ADD COLUMN IF NOT EXISTS linkedin_employee_count INTEGER,
ADD COLUMN IF NOT EXISTS linkedin_industry TEXT,
ADD COLUMN IF NOT EXISTS linkedin_founded_year INTEGER,
ADD COLUMN IF NOT EXISTS linkedin_specialties TEXT[],
ADD COLUMN IF NOT EXISTS dfs_organic_traffic NUMERIC(10,2),
ADD COLUMN IF NOT EXISTS dfs_organic_keywords INTEGER,
ADD COLUMN IF NOT EXISTS dfs_paid_traffic_cost NUMERIC(10,2),
ADD COLUMN IF NOT EXISTS dfs_domain_rank INTEGER,
ADD COLUMN IF NOT EXISTS dfs_backlinks BIGINT,
ADD COLUMN IF NOT EXISTS dfs_referring_domains INTEGER,
ADD COLUMN IF NOT EXISTS dfs_spam_score INTEGER,
ADD COLUMN IF NOT EXISTS dfs_enriched_at TIMESTAMPTZ,
ADD COLUMN IF NOT EXISTS abr_trading_name TEXT,
ADD COLUMN IF NOT EXISTS abr_gst_status TEXT,
ADD COLUMN IF NOT EXISTS abr_business_names TEXT[],
ADD COLUMN IF NOT EXISTS abr_last_checked TIMESTAMPTZ,
ADD COLUMN IF NOT EXISTS revenue_confidence_score INTEGER DEFAULT 0,
ADD COLUMN IF NOT EXISTS revenue_confidence_updated TIMESTAMPTZ;

CREATE INDEX IF NOT EXISTS idx_bu_gmb_domain ON business_universe(gmb_domain);
CREATE INDEX IF NOT EXISTS idx_bu_confidence ON business_universe(revenue_confidence_score);
