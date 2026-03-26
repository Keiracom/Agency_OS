-- DM waterfall output columns — Stage 5
-- Directive #263

ALTER TABLE business_universe
ADD COLUMN IF NOT EXISTS dm_phone TEXT,
ADD COLUMN IF NOT EXISTS dm_found_at TIMESTAMPTZ;
