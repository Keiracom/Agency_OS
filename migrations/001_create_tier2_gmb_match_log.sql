-- Migration: Create tier2_gmb_match_log table for CEO Directive #014
-- Purpose: Track GMB waterfall search attempts for production monitoring
-- Created: 2025-02-12

-- Create tier2_gmb_match_log table
CREATE TABLE IF NOT EXISTS tier2_gmb_match_log (
    id BIGSERIAL PRIMARY KEY,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- ABN identification
    abn VARCHAR(11) NOT NULL,
    abn_name TEXT NOT NULL,
    
    -- Waterfall search details
    search_name_used TEXT NOT NULL,
    waterfall_step VARCHAR(10) NOT NULL, -- a/b/c/d (with potential suffixes like a1, a2)
    
    -- Search results
    gmb_result VARCHAR(20) NOT NULL, -- found/not_found
    match_score DECIMAL(3,2), -- 0.00 to 1.00
    pass_fail VARCHAR(10) NOT NULL, -- pass/fail
    
    -- Metadata
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT valid_gmb_result CHECK (gmb_result IN ('found', 'not_found')),
    CONSTRAINT valid_pass_fail CHECK (pass_fail IN ('pass', 'fail')),
    CONSTRAINT valid_match_score CHECK (match_score >= 0.0 AND match_score <= 1.0),
    CONSTRAINT valid_abn_length CHECK (LENGTH(abn) = 11)
);

-- Create indexes for performance
CREATE INDEX idx_tier2_gmb_match_log_abn ON tier2_gmb_match_log(abn);
CREATE INDEX idx_tier2_gmb_match_log_timestamp ON tier2_gmb_match_log(timestamp DESC);
CREATE INDEX idx_tier2_gmb_match_log_waterfall_step ON tier2_gmb_match_log(waterfall_step);
CREATE INDEX idx_tier2_gmb_match_log_gmb_result ON tier2_gmb_match_log(gmb_result);
CREATE INDEX idx_tier2_gmb_match_log_pass_fail ON tier2_gmb_match_log(pass_fail);

-- Create composite index for analysis queries
CREATE INDEX idx_tier2_gmb_match_log_analysis 
ON tier2_gmb_match_log(waterfall_step, gmb_result, timestamp DESC);

-- Enable Row Level Security (RLS)
ALTER TABLE tier2_gmb_match_log ENABLE ROW LEVEL SECURITY;

-- Create RLS policy for service role access
CREATE POLICY "Allow service role full access" ON tier2_gmb_match_log
    FOR ALL USING (true);

-- Add table comment
COMMENT ON TABLE tier2_gmb_match_log IS 'CEO Directive #014: Tracks GMB waterfall search attempts for match rate monitoring and optimization';

-- Add column comments
COMMENT ON COLUMN tier2_gmb_match_log.abn IS 'Australian Business Number (11 digits)';
COMMENT ON COLUMN tier2_gmb_match_log.abn_name IS 'Original business name from ABN record';
COMMENT ON COLUMN tier2_gmb_match_log.search_name_used IS 'Actual search term used in this waterfall step';
COMMENT ON COLUMN tier2_gmb_match_log.waterfall_step IS 'Waterfall step identifier: a=ASIC names, b=trading name, c=stripped legal name, d=location search';
COMMENT ON COLUMN tier2_gmb_match_log.gmb_result IS 'Whether GMB search found a result';
COMMENT ON COLUMN tier2_gmb_match_log.match_score IS 'Quality score of the match (0.0-1.0)';
COMMENT ON COLUMN tier2_gmb_match_log.pass_fail IS 'Overall success/failure of this search attempt';

-- Grant permissions to authenticated users (adjust as needed for your auth setup)
GRANT SELECT ON tier2_gmb_match_log TO authenticated;
GRANT INSERT ON tier2_gmb_match_log TO authenticated;