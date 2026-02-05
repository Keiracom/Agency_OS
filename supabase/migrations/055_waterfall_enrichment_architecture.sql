-- ============================================================
-- FILE: supabase/migrations/055_waterfall_enrichment_architecture.sql
-- PURPOSE: Waterfall Enrichment Architecture - Phase WF-001
-- AUTHOR: Elliot (CTO)
-- DATE: 2026-02-04
-- GOVERNANCE: "Waterfall Reliability Shift" - Moving from Apollo SPOF to 
--             AI Ark + AI Contact Finder + Triple-Check Verification
-- 
-- CHANGES:
--   1. Add enrichment_lineage JSONB for full audit trail
--   2. Add intent signal columns (ad library proxies)
--   3. Add triple-check verification metadata
--   4. Create composite index for ALS engine
--   5. Create BRIN index for time-series queries
--   6. Create partial index for available leads (Australia-wide)
--   7. Create lead_lineage_log table for detailed audit
--   8. Create scraper_health_log table for self-healing
-- ============================================================

-- ============================================================
-- PART 1: ENRICHMENT LINEAGE & INTENT SIGNALS
-- ============================================================

-- Add enrichment_lineage JSONB column for Governance Trace
ALTER TABLE lead_pool 
ADD COLUMN IF NOT EXISTS enrichment_lineage JSONB DEFAULT '[]'::jsonb;

COMMENT ON COLUMN lead_pool.enrichment_lineage IS 
'Full audit trail of enrichment steps. Example:
[
  {"step": 1, "source": "ai_ark", "timestamp": "2026-02-04T10:00:00Z", "cost_aud": 0.015, "data_added": ["email", "title"]},
  {"step": 2, "source": "hunter_io", "timestamp": "2026-02-04T10:00:01Z", "cost_aud": 0.006, "verification": "valid"},
  {"step": 3, "source": "ad_library", "timestamp": "2026-02-04T10:00:02Z", "cost_aud": 0.002, "signal": "high_intent"}
]';

-- Add intent signal columns (Ad Library proxies)
ALTER TABLE lead_pool
ADD COLUMN IF NOT EXISTS intent_ad_volume INT DEFAULT NULL,
ADD COLUMN IF NOT EXISTS intent_ad_longevity_days INT DEFAULT NULL,
ADD COLUMN IF NOT EXISTS intent_ad_first_seen DATE DEFAULT NULL,
ADD COLUMN IF NOT EXISTS intent_ad_last_seen DATE DEFAULT NULL,
ADD COLUMN IF NOT EXISTS intent_ad_platforms TEXT[] DEFAULT NULL,
ADD COLUMN IF NOT EXISTS intent_score INT DEFAULT NULL,
ADD COLUMN IF NOT EXISTS intent_signals JSONB DEFAULT NULL;

COMMENT ON COLUMN lead_pool.intent_ad_volume IS 
'Number of active ads detected. >50 = high intent signal';

COMMENT ON COLUMN lead_pool.intent_ad_longevity_days IS 
'Days ads have been running. >60 = sustained spend signal';

COMMENT ON COLUMN lead_pool.intent_score IS 
'0-100 composite intent score from all signals (ad spend proxy, hiring, funding)';

-- Add triple-check verification metadata
ALTER TABLE lead_pool
ADD COLUMN IF NOT EXISTS verification_method TEXT DEFAULT NULL,
ADD COLUMN IF NOT EXISTS verification_sources TEXT[] DEFAULT NULL,
ADD COLUMN IF NOT EXISTS verification_consensus BOOLEAN DEFAULT NULL,
ADD COLUMN IF NOT EXISTS verification_escalated BOOLEAN DEFAULT FALSE;

COMMENT ON COLUMN lead_pool.verification_method IS 
'Method used: single_source, dual_match, triple_check';

COMMENT ON COLUMN lead_pool.verification_sources IS 
'Array of sources that verified email: ["hunter_io", "zerobounce"]';

COMMENT ON COLUMN lead_pool.verification_consensus IS 
'TRUE if all sources agreed, FALSE if escalation was needed';

-- ============================================================
-- PART 2: PERFORMANCE INDEXES FOR 10M+ SCALE (AUSTRALIA-WIDE)
-- ============================================================

-- Composite index for ALS engine (sub-second queries)
CREATE INDEX IF NOT EXISTS idx_lead_pool_als_engine
ON lead_pool (client_id, pool_status, als_tier)
WHERE deleted_at IS NULL;

COMMENT ON INDEX idx_lead_pool_als_engine IS
'Composite index for ALS engine queries. Covers:
- Client-specific lead lookups
- Status filtering (available, assigned, etc.)
- Tier-based prioritization (hot, warm, cool, cold)';

-- BRIN index for time-series queries (10x more efficient than B-tree for large ordered datasets)
CREATE INDEX IF NOT EXISTS idx_lead_pool_created_brin
ON lead_pool USING BRIN (created_at)
WITH (pages_per_range = 128);

COMMENT ON INDEX idx_lead_pool_created_brin IS
'BRIN index for time-series queries. Efficient for:
- "Leads created in last 7 days"
- Monthly partitioning queries
- Data freshness checks';

-- Partial index for available leads - AUSTRALIA-WIDE with state support
CREATE INDEX IF NOT EXISTS idx_lead_pool_available_sourcing
ON lead_pool (company_country, company_state, company_industry, company_employee_count)
WHERE pool_status = 'available' 
  AND deleted_at IS NULL 
  AND is_bounced = FALSE 
  AND is_unsubscribed = FALSE;

COMMENT ON INDEX idx_lead_pool_available_sourcing IS
'Partial index for ICP matching on available leads.
Optimized for Australia-wide queries with state-level filtering.
Supports: NSW (Phase 1), VIC, QLD, WA, SA, TAS, NT, ACT expansion.';

-- Index for intent-based queries
CREATE INDEX IF NOT EXISTS idx_lead_pool_high_intent
ON lead_pool (intent_score DESC, als_score DESC)
WHERE intent_score >= 50 AND deleted_at IS NULL;

COMMENT ON INDEX idx_lead_pool_high_intent IS
'Index for high-intent lead prioritization.
Covers leads with >50 intent score (ad spend proxy signals).';

-- Index for state-level queries (nationwide expansion)
CREATE INDEX IF NOT EXISTS idx_lead_pool_state_industry
ON lead_pool (company_state, company_industry)
WHERE company_country = 'Australia' AND deleted_at IS NULL;

COMMENT ON INDEX idx_lead_pool_state_industry IS
'Index for state-level industry queries. Supports nationwide expansion:
NSW, VIC, QLD, WA, SA, TAS, NT, ACT';

-- ============================================================
-- PART 3: LEAD LINEAGE LOG TABLE (Detailed Audit)
-- ============================================================

CREATE TABLE IF NOT EXISTS lead_lineage_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    lead_id UUID NOT NULL REFERENCES lead_pool(id) ON DELETE CASCADE,
    
    -- Step identification
    step_number INT NOT NULL,
    step_type TEXT NOT NULL, -- 'source', 'enrichment', 'verification', 'intent_signal'
    
    -- Source tracking
    source_name TEXT NOT NULL, -- 'ai_ark', 'gmb_scraper', 'hunter_io', 'ad_library', 'abr'
    source_endpoint TEXT, -- API endpoint or scraper path
    source_raw_response JSONB, -- Full raw response (for debugging)
    
    -- Data changes
    fields_added TEXT[], -- ['email', 'title', 'company_name']
    fields_updated TEXT[], -- ['als_score', 'intent_score']
    data_before JSONB, -- Snapshot before this step
    data_after JSONB, -- Snapshot after this step
    
    -- Verification specifics
    verification_result TEXT, -- 'valid', 'invalid', 'catch_all', 'unknown'
    verification_confidence NUMERIC(3,2), -- 0.00-1.00
    
    -- Cost tracking
    cost_aud NUMERIC(10,6) NOT NULL DEFAULT 0,
    api_credits_used NUMERIC(10,2) DEFAULT 0,
    
    -- Performance metrics
    latency_ms INT,
    retry_count INT DEFAULT 0,
    
    -- Status
    success BOOLEAN NOT NULL DEFAULT TRUE,
    error_message TEXT,
    
    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- Ensure ordered steps per lead
    CONSTRAINT unique_lead_step UNIQUE (lead_id, step_number)
);

-- Index for lead lookup
CREATE INDEX IF NOT EXISTS idx_lineage_lead_id ON lead_lineage_log (lead_id);

-- Index for source analysis
CREATE INDEX IF NOT EXISTS idx_lineage_source ON lead_lineage_log (source_name, created_at DESC);

-- Index for cost tracking
CREATE INDEX IF NOT EXISTS idx_lineage_cost ON lead_lineage_log (created_at, cost_aud) 
WHERE cost_aud > 0;

COMMENT ON TABLE lead_lineage_log IS
'Detailed audit trail for every enrichment step.
Answers: "Why does this lead have a 92 ALS?"
Example query:
  SELECT * FROM lead_lineage_log 
  WHERE lead_id = ? 
  ORDER BY step_number;';

-- ============================================================
-- PART 4: HELPER FUNCTION FOR LINEAGE QUERIES
-- ============================================================

CREATE OR REPLACE FUNCTION get_lead_lineage_summary(p_lead_id UUID)
RETURNS JSONB
LANGUAGE plpgsql
STABLE
AS $$
DECLARE
    result JSONB;
BEGIN
    SELECT jsonb_build_object(
        'lead_id', p_lead_id,
        'total_steps', COUNT(*),
        'total_cost_aud', SUM(cost_aud),
        'sources_used', array_agg(DISTINCT source_name),
        'verification_result', (
            SELECT verification_result 
            FROM lead_lineage_log 
            WHERE lead_id = p_lead_id AND step_type = 'verification'
            ORDER BY step_number DESC LIMIT 1
        ),
        'lineage', jsonb_agg(
            jsonb_build_object(
                'step', step_number,
                'source', source_name,
                'type', step_type,
                'cost', cost_aud,
                'success', success,
                'timestamp', created_at
            ) ORDER BY step_number
        )
    ) INTO result
    FROM lead_lineage_log
    WHERE lead_id = p_lead_id;
    
    RETURN COALESCE(result, '{}'::jsonb);
END;
$$;

COMMENT ON FUNCTION get_lead_lineage_summary IS
'Returns a complete lineage summary for a lead.
Usage: SELECT get_lead_lineage_summary(lead_id);
Returns: {"lead_id": "...", "total_cost_aud": 0.036, "sources_used": [...], "lineage": [...]}';

-- ============================================================
-- PART 5: SCRAPER HEALTH MONITORING TABLE (Self-Healing)
-- ============================================================

CREATE TABLE IF NOT EXISTS scraper_health_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    scraper_name TEXT NOT NULL, -- 'gmb_scraper', 'ad_library_google', 'linkedin_ads', 'abr_scraper'
    
    -- Health metrics
    consecutive_failures INT NOT NULL DEFAULT 0,
    last_success_at TIMESTAMPTZ,
    last_failure_at TIMESTAMPTZ,
    last_error_message TEXT,
    
    -- Auto-healing tracking
    healing_triggered_at TIMESTAMPTZ,
    healing_session_key TEXT, -- Clawdbot session that's fixing it
    healing_status TEXT, -- 'pending', 'in_progress', 'success', 'failed'
    
    -- Statistics
    total_runs INT NOT NULL DEFAULT 0,
    total_successes INT NOT NULL DEFAULT 0,
    total_failures INT NOT NULL DEFAULT 0,
    avg_latency_ms INT,
    
    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    CONSTRAINT unique_scraper UNIQUE (scraper_name)
);

COMMENT ON TABLE scraper_health_log IS
'Monitors scraper health for self-healing triggers.
If consecutive_failures >= 3, triggers auto-healing via sessions_spawn.
Scrapers: gmb_scraper (AU-wide), ad_library_google, ad_library_linkedin, abr_scraper';

-- Function to check and trigger self-healing
CREATE OR REPLACE FUNCTION check_scraper_health()
RETURNS TABLE (
    scraper_name TEXT,
    needs_healing BOOLEAN,
    consecutive_failures INT
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT 
        s.scraper_name,
        s.consecutive_failures >= 3 AS needs_healing,
        s.consecutive_failures
    FROM scraper_health_log s
    WHERE s.consecutive_failures >= 3
      AND (s.healing_triggered_at IS NULL 
           OR s.healing_triggered_at < NOW() - INTERVAL '1 hour');
END;
$$;

-- ============================================================
-- PART 6: AUDIT LOG ENTRY
-- ============================================================

-- Insert governance audit entry for this migration
INSERT INTO audit_logs (
    id,
    action,
    entity_type,
    entity_id,
    changes,
    performed_by,
    created_at
) VALUES (
    gen_random_uuid(),
    'SCHEMA_MIGRATION',
    'database',
    '055_waterfall_enrichment_architecture',
    jsonb_build_object(
        'migration', '055_waterfall_enrichment_architecture.sql',
        'governance_event', 'Waterfall Reliability Shift',
        'description', 'Moving from Apollo SPOF to AI Ark + AI Contact Finder + Triple-Check Verification',
        'changes', ARRAY[
            'Added enrichment_lineage JSONB column',
            'Added intent signal columns (ad_volume, ad_longevity, intent_score)',
            'Added triple-check verification fields',
            'Created lead_lineage_log table',
            'Created scraper_health_log table',
            'Added composite + BRIN + partial indexes for 10M+ scale',
            'Added Australia-wide state-level index support'
        ],
        'cost_impact', 'Estimated 50-60% reduction in enrichment costs',
        'reliability_impact', 'Estimated 95%+ coverage vs 70-85% with Apollo'
    ),
    'elliot_cto',
    NOW()
) ON CONFLICT DO NOTHING;

-- ============================================================
-- VERIFICATION
-- ============================================================

DO $$
BEGIN
    -- Verify new columns exist
    ASSERT (SELECT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'lead_pool' AND column_name = 'enrichment_lineage'
    )), 'enrichment_lineage column not created';
    
    ASSERT (SELECT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'lead_pool' AND column_name = 'intent_ad_volume'
    )), 'intent_ad_volume column not created';
    
    ASSERT (SELECT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'lead_pool' AND column_name = 'verification_method'
    )), 'verification_method column not created';
    
    -- Verify tables exist
    ASSERT (SELECT EXISTS (
        SELECT 1 FROM information_schema.tables 
        WHERE table_name = 'lead_lineage_log'
    )), 'lead_lineage_log table not created';
    
    ASSERT (SELECT EXISTS (
        SELECT 1 FROM information_schema.tables 
        WHERE table_name = 'scraper_health_log'
    )), 'scraper_health_log table not created';
    
    RAISE NOTICE '✅ Migration 055_waterfall_enrichment_architecture completed successfully';
    RAISE NOTICE '✅ Governance Event: Waterfall Reliability Shift logged to audit_logs';
END;
$$;
