-- Scoring output columns for Stage 4
-- Directive #262

ALTER TABLE business_universe
ADD COLUMN IF NOT EXISTS score_reason TEXT,
ADD COLUMN IF NOT EXISTS best_match_service TEXT,
ADD COLUMN IF NOT EXISTS linkedin_company_url TEXT,
ADD COLUMN IF NOT EXISTS scored_at TIMESTAMPTZ;
