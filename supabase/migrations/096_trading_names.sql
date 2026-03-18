-- Trading names and business names register
-- Source: ABR bulk extract, data.gov.au
-- Ratified: March 18 2026 | Directive #222
-- Purpose: match GMB trading names to ABN
-- for GST status and entity verification

CREATE TABLE IF NOT EXISTS trading_names (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    abn TEXT NOT NULL,
    name TEXT NOT NULL,
    name_type TEXT NOT NULL,
    -- 'TRD' = trading name
    -- 'BN' = registered business name
    state TEXT,
    postcode TEXT,
    is_active BOOLEAN DEFAULT true,
    registration_date DATE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Trigram index for fuzzy name matching
-- This is what makes GMB→ABN matching work
CREATE EXTENSION IF NOT EXISTS pg_trgm;

CREATE INDEX IF NOT EXISTS idx_trading_names_trgm
    ON trading_names USING gin(name gin_trgm_ops);

CREATE INDEX IF NOT EXISTS idx_trading_names_abn
    ON trading_names(abn);

CREATE INDEX IF NOT EXISTS idx_trading_names_state
    ON trading_names(name, state);

-- Resume-safe: reruns are idempotent
ALTER TABLE trading_names ADD CONSTRAINT trading_names_unique
    UNIQUE (abn, name, name_type);

-- USAGE: Use % operator (not similarity() function) to activate GIN index
-- SET pg_trgm.similarity_threshold = 0.4;
-- SELECT * FROM trading_names WHERE name % 'search term' LIMIT 10;
-- For matching with score: WHERE lower(name) % lower('search term')
-- The similarity() function without % does NOT use the GIN index and will seq-scan.
