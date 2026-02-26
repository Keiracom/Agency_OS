-- Migration 075: Create discovery_queries table
-- Bug #22 fix: QueryTranslator logs queries to this table for debugging/audit
-- CEO Directive #110

-- =====================================================
-- CREATE TABLE
-- =====================================================

CREATE TABLE IF NOT EXISTS discovery_queries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    campaign_id UUID NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE,
    mode TEXT NOT NULL,
    query_type TEXT NOT NULL,
    query_params JSONB NOT NULL DEFAULT '{}'::jsonb,
    results_count INTEGER NOT NULL DEFAULT 0,
    cost_aud NUMERIC(10, 4) NOT NULL DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for analysis
CREATE INDEX IF NOT EXISTS idx_discovery_queries_campaign ON discovery_queries(campaign_id);
CREATE INDEX IF NOT EXISTS idx_discovery_queries_created ON discovery_queries(created_at);
CREATE INDEX IF NOT EXISTS idx_discovery_queries_mode ON discovery_queries(mode);

-- =====================================================
-- COMMENTS
-- =====================================================

COMMENT ON TABLE discovery_queries IS 'Audit log of discovery queries executed by QueryTranslator';
COMMENT ON COLUMN discovery_queries.campaign_id IS 'Campaign that triggered the query';
COMMENT ON COLUMN discovery_queries.mode IS 'Discovery mode: abn, maps, or parallel';
COMMENT ON COLUMN discovery_queries.query_type IS 'Query type: abn_search or maps_serp';
COMMENT ON COLUMN discovery_queries.query_params IS 'Query parameters (keyword, location, etc.)';
COMMENT ON COLUMN discovery_queries.results_count IS 'Number of results returned by the query';
COMMENT ON COLUMN discovery_queries.cost_aud IS 'Cost of the query in AUD';

-- =====================================================
-- VERIFICATION
-- =====================================================
-- [x] Table created with correct schema for QueryTranslator._log_query()
-- [x] Foreign key to campaigns with CASCADE delete
-- [x] Indexes for query analysis
-- [x] Cost tracking for budget monitoring
