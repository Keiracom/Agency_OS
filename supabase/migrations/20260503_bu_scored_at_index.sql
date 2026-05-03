-- Gap #4 signal decay: index scored_at for rescore picker WHERE clause
-- Partial index: only rows with scored_at populated need fast lookup
CREATE INDEX IF NOT EXISTS idx_bu_scored_at
    ON business_universe (scored_at)
    WHERE scored_at IS NOT NULL;
