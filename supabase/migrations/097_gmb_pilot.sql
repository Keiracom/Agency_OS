-- Directive #225: Sydney GMB Pre-Population Pilot
-- Migration 097: gmb_pilot_results, business_reviews, business_universe new columns

-- gmb_pilot_results table
CREATE TABLE IF NOT EXISTS gmb_pilot_results (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  abn TEXT,
  trading_name TEXT,
  serp_match BOOLEAN,
  gmb_category TEXT,
  gmb_rating NUMERIC,
  gmb_review_count INTEGER,
  gmb_domain TEXT,
  match_confidence TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- business_reviews table
CREATE TABLE IF NOT EXISTS business_reviews (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  abn TEXT NOT NULL,
  gmb_place_id TEXT,
  reviewer_name TEXT,
  review_rating INTEGER,
  review_text TEXT,
  review_date TIMESTAMPTZ,
  owner_response TEXT,
  owner_response_date TIMESTAMPTZ,
  owner_name TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- New columns on business_universe
ALTER TABLE business_universe ADD COLUMN IF NOT EXISTS gmb_owner_name TEXT;
ALTER TABLE business_universe ADD COLUMN IF NOT EXISTS gmb_reviews_fetched_at TIMESTAMPTZ;
ALTER TABLE business_universe ADD COLUMN IF NOT EXISTS gmb_last_review_date TIMESTAMPTZ;
