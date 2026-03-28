-- Sprint 2 free intelligence columns for business_universe
ALTER TABLE business_universe
  -- Domain growth signal
  ADD COLUMN IF NOT EXISTS trajectory                  NUMERIC(5,3),
  -- Website intelligence (from website scraping)
  ADD COLUMN IF NOT EXISTS website_tech_stack          JSONB,
  ADD COLUMN IF NOT EXISTS website_cms                 TEXT,
  ADD COLUMN IF NOT EXISTS website_tracking_codes      JSONB,
  ADD COLUMN IF NOT EXISTS website_team_names          JSONB,
  ADD COLUMN IF NOT EXISTS website_contact_emails      JSONB,
  -- Google Ads transparency intelligence
  ADD COLUMN IF NOT EXISTS google_ads_active           BOOLEAN,
  ADD COLUMN IF NOT EXISTS google_ads_count            INTEGER,
  ADD COLUMN IF NOT EXISTS google_ads_last_seen        TIMESTAMPTZ,
  -- DNS intelligence
  ADD COLUMN IF NOT EXISTS dns_mx_provider             TEXT,
  ADD COLUMN IF NOT EXISTS dns_has_spf                 BOOLEAN,
  ADD COLUMN IF NOT EXISTS dns_has_dkim                BOOLEAN,
  -- ABN enrichment flags
  ADD COLUMN IF NOT EXISTS abn_matched                 BOOLEAN,
  -- GMB mobile detection
  ADD COLUMN IF NOT EXISTS gmb_phone_is_mobile         BOOLEAN,
  -- Sprint 2 completion marker
  ADD COLUMN IF NOT EXISTS free_enrichment_completed_at TIMESTAMPTZ;
