-- CEO Directive #014: Tier 2 GMB Match Rate Logging
-- Purpose: Production monitoring of ABN→GMB waterfall match rates
-- LAW II: All costs in AUD

CREATE TABLE IF NOT EXISTS public.tier2_gmb_match_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- Lead identification
    abn VARCHAR(20),
    lead_id UUID,
    
    -- Search parameters
    abn_name TEXT,                    -- Original name from ABN
    search_name_used TEXT NOT NULL,   -- Name actually searched
    waterfall_step CHAR(1) NOT NULL,  -- a=business_names, b=trading_name, c=legal_name, d=location_pinned
    location_query TEXT,              -- Location string used in search
    
    -- Results
    gmb_result VARCHAR(20) NOT NULL,  -- found/not_found/skipped
    gmb_name TEXT,                    -- Name returned from GMB (if found)
    match_score INTEGER,              -- Fuzzy match score (0-100)
    pass BOOLEAN NOT NULL,            -- Whether this step passed threshold
    
    -- Skip tracking
    skip_reason TEXT,                 -- If skipped, why (e.g., 'generic_name')
    
    -- Metadata
    names_tried INTEGER,              -- Total name variants tried before match/fail
    processing_ms INTEGER,            -- Time taken for this search
    
    CONSTRAINT valid_waterfall_step CHECK (waterfall_step IN ('a', 'b', 'c', 'd')),
    CONSTRAINT valid_gmb_result CHECK (gmb_result IN ('found', 'not_found', 'skipped'))
);

-- Indexes for production monitoring queries
CREATE INDEX IF NOT EXISTS idx_tier2_gmb_match_log_created_at 
    ON public.tier2_gmb_match_log(created_at DESC);

CREATE INDEX IF NOT EXISTS idx_tier2_gmb_match_log_waterfall_step 
    ON public.tier2_gmb_match_log(waterfall_step);

CREATE INDEX IF NOT EXISTS idx_tier2_gmb_match_log_gmb_result 
    ON public.tier2_gmb_match_log(gmb_result);

CREATE INDEX IF NOT EXISTS idx_tier2_gmb_match_log_pass 
    ON public.tier2_gmb_match_log(pass);

CREATE INDEX IF NOT EXISTS idx_tier2_gmb_match_log_abn 
    ON public.tier2_gmb_match_log(abn);

-- Composite index for match rate analysis
CREATE INDEX IF NOT EXISTS idx_tier2_gmb_match_log_analysis 
    ON public.tier2_gmb_match_log(created_at DESC, waterfall_step, pass);

-- RLS policies
ALTER TABLE public.tier2_gmb_match_log ENABLE ROW LEVEL SECURITY;

-- Service role can do everything
CREATE POLICY tier2_gmb_match_log_service_all ON public.tier2_gmb_match_log
    FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

-- Authenticated users can read for monitoring dashboards
CREATE POLICY tier2_gmb_match_log_auth_read ON public.tier2_gmb_match_log
    FOR SELECT
    TO authenticated
    USING (true);

COMMENT ON TABLE public.tier2_gmb_match_log IS 'CEO Directive #014: Tier 2 GMB match rate logging for production monitoring';
COMMENT ON COLUMN public.tier2_gmb_match_log.waterfall_step IS 'a=ASIC business_names, b=trading_name, c=legal_name stripped, d=location_pinned';
