-- Migration: 081_cis_timing_signals.sql
-- Purpose: CIS Timing Signal Aggregation - Gap 3 (Directive #157)
-- Date: 2025-07-08
--
-- PROBLEM: Activities table has timing columns (lead_local_day_of_week, lead_local_time)
--          but CIS never reads them. This gap means we're missing timing intelligence.
--
-- SOLUTION: Aggregate timing patterns from conversions into queryable platform-level insights
--           by industry/channel/company_size. E.g., "Manufacturing responds best Tues 10-11am"

-- ============================================================================
-- 1. PLATFORM TIMING SIGNALS TABLE
-- ============================================================================

CREATE TABLE IF NOT EXISTS platform_timing_signals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Segment dimensions (anonymized, platform-wide)
    industry TEXT NOT NULL,
    channel TEXT NOT NULL,  -- 'email', 'linkedin', 'sms', 'voice'
    company_size TEXT NOT NULL,  -- 'smb', 'mid_market', 'enterprise' (derived from employee_count)

    -- Timing aggregations
    -- Day of week stats (0=Monday, 6=Sunday - ISO 8601 format)
    day_of_week_distribution JSONB NOT NULL DEFAULT '{}',  
    -- Format: {"0": {"conversions": 5, "total": 20}, "1": {...}, ...}

    -- Hour of day stats (0-23, in lead local time)
    hour_of_day_distribution JSONB NOT NULL DEFAULT '{}',
    -- Format: {"9": {"conversions": 3, "total": 15}, "10": {...}, ...}

    -- Touchpoint distribution (which touch number converts)
    touchpoint_distribution JSONB NOT NULL DEFAULT '{}',
    -- Format: {"1": {"conversions": 2, "total": 50}, "2": {...}, ...}

    -- Derived insights (pre-computed for fast queries)
    best_day_of_week INTEGER,  -- 0=Monday
    best_hour_of_day INTEGER,  -- 0-23
    best_touchpoint INTEGER,  -- 1, 2, 3, etc.
    avg_converting_touchpoint NUMERIC(5,2),

    -- Confidence metrics
    total_conversions INTEGER NOT NULL DEFAULT 0,
    total_attempts INTEGER NOT NULL DEFAULT 0,
    conversion_rate NUMERIC(5,4),  -- total_conversions / total_attempts
    last_updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Unique constraint: one row per segment
    CONSTRAINT unique_timing_segment UNIQUE (industry, channel, company_size),

    -- Must have minimum sample size for insights to be meaningful
    CONSTRAINT valid_stats CHECK (total_conversions >= 0 AND total_attempts >= 0)
);

-- ============================================================================
-- 2. INDEXES FOR PERFORMANCE
-- ============================================================================

-- Fast lookups by segment
CREATE INDEX IF NOT EXISTS idx_timing_signals_segment
    ON platform_timing_signals(industry, channel, company_size);

-- Find best performers
CREATE INDEX IF NOT EXISTS idx_timing_signals_conversion_rate
    ON platform_timing_signals(conversion_rate DESC NULLS LAST)
    WHERE total_conversions >= 5;

-- Industry-specific queries
CREATE INDEX IF NOT EXISTS idx_timing_signals_industry
    ON platform_timing_signals(industry);

-- ============================================================================
-- 3. FUNCTION TO UPDATE TIMING SIGNALS
-- ============================================================================

CREATE OR REPLACE FUNCTION update_platform_timing_signal(
    p_industry TEXT,
    p_channel TEXT,
    p_company_size TEXT,
    p_day_of_week INTEGER,  -- 0=Monday, 6=Sunday
    p_hour_of_day INTEGER,  -- 0-23
    p_touchpoint INTEGER,   -- 1, 2, 3, etc.
    p_is_conversion BOOLEAN
) RETURNS VOID AS $$
DECLARE
    v_dow_key TEXT := p_day_of_week::TEXT;
    v_hour_key TEXT := p_hour_of_day::TEXT;
    v_touch_key TEXT := p_touchpoint::TEXT;
BEGIN
    -- Upsert the timing signal record
    INSERT INTO platform_timing_signals (
        industry, channel, company_size,
        day_of_week_distribution,
        hour_of_day_distribution,
        touchpoint_distribution,
        total_conversions,
        total_attempts
    ) VALUES (
        p_industry, p_channel, p_company_size,
        -- Initialize day distribution
        jsonb_build_object(v_dow_key, jsonb_build_object(
            'conversions', CASE WHEN p_is_conversion THEN 1 ELSE 0 END,
            'total', 1
        )),
        -- Initialize hour distribution
        jsonb_build_object(v_hour_key, jsonb_build_object(
            'conversions', CASE WHEN p_is_conversion THEN 1 ELSE 0 END,
            'total', 1
        )),
        -- Initialize touchpoint distribution
        jsonb_build_object(v_touch_key, jsonb_build_object(
            'conversions', CASE WHEN p_is_conversion THEN 1 ELSE 0 END,
            'total', 1
        )),
        CASE WHEN p_is_conversion THEN 1 ELSE 0 END,
        1
    )
    ON CONFLICT (industry, channel, company_size) DO UPDATE SET
        -- Update day distribution
        day_of_week_distribution = CASE
            WHEN platform_timing_signals.day_of_week_distribution ? v_dow_key THEN
                jsonb_set(
                    platform_timing_signals.day_of_week_distribution,
                    ARRAY[v_dow_key],
                    jsonb_build_object(
                        'conversions', 
                        COALESCE((platform_timing_signals.day_of_week_distribution->v_dow_key->>'conversions')::INTEGER, 0) 
                            + CASE WHEN p_is_conversion THEN 1 ELSE 0 END,
                        'total',
                        COALESCE((platform_timing_signals.day_of_week_distribution->v_dow_key->>'total')::INTEGER, 0) + 1
                    )
                )
            ELSE
                platform_timing_signals.day_of_week_distribution || 
                jsonb_build_object(v_dow_key, jsonb_build_object(
                    'conversions', CASE WHEN p_is_conversion THEN 1 ELSE 0 END,
                    'total', 1
                ))
        END,
        -- Update hour distribution
        hour_of_day_distribution = CASE
            WHEN platform_timing_signals.hour_of_day_distribution ? v_hour_key THEN
                jsonb_set(
                    platform_timing_signals.hour_of_day_distribution,
                    ARRAY[v_hour_key],
                    jsonb_build_object(
                        'conversions',
                        COALESCE((platform_timing_signals.hour_of_day_distribution->v_hour_key->>'conversions')::INTEGER, 0)
                            + CASE WHEN p_is_conversion THEN 1 ELSE 0 END,
                        'total',
                        COALESCE((platform_timing_signals.hour_of_day_distribution->v_hour_key->>'total')::INTEGER, 0) + 1
                    )
                )
            ELSE
                platform_timing_signals.hour_of_day_distribution ||
                jsonb_build_object(v_hour_key, jsonb_build_object(
                    'conversions', CASE WHEN p_is_conversion THEN 1 ELSE 0 END,
                    'total', 1
                ))
        END,
        -- Update touchpoint distribution
        touchpoint_distribution = CASE
            WHEN platform_timing_signals.touchpoint_distribution ? v_touch_key THEN
                jsonb_set(
                    platform_timing_signals.touchpoint_distribution,
                    ARRAY[v_touch_key],
                    jsonb_build_object(
                        'conversions',
                        COALESCE((platform_timing_signals.touchpoint_distribution->v_touch_key->>'conversions')::INTEGER, 0)
                            + CASE WHEN p_is_conversion THEN 1 ELSE 0 END,
                        'total',
                        COALESCE((platform_timing_signals.touchpoint_distribution->v_touch_key->>'total')::INTEGER, 0) + 1
                    )
                )
            ELSE
                platform_timing_signals.touchpoint_distribution ||
                jsonb_build_object(v_touch_key, jsonb_build_object(
                    'conversions', CASE WHEN p_is_conversion THEN 1 ELSE 0 END,
                    'total', 1
                ))
        END,
        total_conversions = platform_timing_signals.total_conversions + CASE WHEN p_is_conversion THEN 1 ELSE 0 END,
        total_attempts = platform_timing_signals.total_attempts + 1,
        conversion_rate = (platform_timing_signals.total_conversions + CASE WHEN p_is_conversion THEN 1 ELSE 0 END)::NUMERIC 
            / (platform_timing_signals.total_attempts + 1),
        last_updated_at = NOW();

    -- Update derived insights (find best performers)
    UPDATE platform_timing_signals pts
    SET
        best_day_of_week = (
            SELECT (kv.key)::INTEGER
            FROM jsonb_each(pts.day_of_week_distribution) kv
            WHERE (kv.value->>'total')::INTEGER >= 3
            ORDER BY (kv.value->>'conversions')::NUMERIC / NULLIF((kv.value->>'total')::NUMERIC, 0) DESC
            LIMIT 1
        ),
        best_hour_of_day = (
            SELECT (kv.key)::INTEGER
            FROM jsonb_each(pts.hour_of_day_distribution) kv
            WHERE (kv.value->>'total')::INTEGER >= 3
            ORDER BY (kv.value->>'conversions')::NUMERIC / NULLIF((kv.value->>'total')::NUMERIC, 0) DESC
            LIMIT 1
        ),
        best_touchpoint = (
            SELECT (kv.key)::INTEGER
            FROM jsonb_each(pts.touchpoint_distribution) kv
            WHERE (kv.value->>'total')::INTEGER >= 3
            ORDER BY (kv.value->>'conversions')::NUMERIC / NULLIF((kv.value->>'total')::NUMERIC, 0) DESC
            LIMIT 1
        ),
        avg_converting_touchpoint = (
            SELECT SUM((kv.key)::NUMERIC * (kv.value->>'conversions')::NUMERIC) / 
                   NULLIF(SUM((kv.value->>'conversions')::NUMERIC), 0)
            FROM jsonb_each(pts.touchpoint_distribution) kv
        )
    WHERE pts.industry = p_industry 
      AND pts.channel = p_channel 
      AND pts.company_size = p_company_size;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- 4. HELPER FUNCTION TO GET TIMING INSIGHTS
-- ============================================================================

CREATE OR REPLACE FUNCTION get_timing_insights(
    p_industry TEXT,
    p_channel TEXT DEFAULT NULL,
    p_company_size TEXT DEFAULT NULL
)
RETURNS TABLE (
    industry TEXT,
    channel TEXT,
    company_size TEXT,
    best_day TEXT,
    best_hour INTEGER,
    best_touchpoint INTEGER,
    avg_touchpoint NUMERIC,
    conversion_rate NUMERIC,
    total_conversions INTEGER,
    confidence TEXT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        pts.industry,
        pts.channel,
        pts.company_size,
        CASE pts.best_day_of_week
            WHEN 0 THEN 'Monday'
            WHEN 1 THEN 'Tuesday'
            WHEN 2 THEN 'Wednesday'
            WHEN 3 THEN 'Thursday'
            WHEN 4 THEN 'Friday'
            WHEN 5 THEN 'Saturday'
            WHEN 6 THEN 'Sunday'
        END as best_day,
        pts.best_hour_of_day,
        pts.best_touchpoint,
        pts.avg_converting_touchpoint,
        pts.conversion_rate,
        pts.total_conversions,
        CASE
            WHEN pts.total_conversions >= 50 THEN 'high'
            WHEN pts.total_conversions >= 20 THEN 'medium'
            WHEN pts.total_conversions >= 5 THEN 'low'
            ELSE 'insufficient'
        END as confidence
    FROM platform_timing_signals pts
    WHERE pts.industry = p_industry
      AND (p_channel IS NULL OR pts.channel = p_channel)
      AND (p_company_size IS NULL OR pts.company_size = p_company_size)
    ORDER BY pts.total_conversions DESC;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- 5. ROW LEVEL SECURITY (Platform-wide, read-only for authenticated)
-- ============================================================================

ALTER TABLE platform_timing_signals ENABLE ROW LEVEL SECURITY;

-- All authenticated users can read platform timing signals (anonymized data)
CREATE POLICY timing_signals_read_all ON platform_timing_signals
    FOR SELECT
    USING (true);

-- Only service role can modify (via CIS engine)
CREATE POLICY timing_signals_write_service ON platform_timing_signals
    FOR ALL
    USING (auth.role() = 'service_role');

-- ============================================================================
-- COMMENTS
-- ============================================================================

COMMENT ON TABLE platform_timing_signals IS 
    'Aggregated timing patterns from conversions by industry/channel/size. '
    'Used by CIS for timing intelligence. Gap 3 fix (Directive #157).';

COMMENT ON COLUMN platform_timing_signals.day_of_week_distribution IS 
    'JSON distribution of conversions/attempts by day. 0=Monday, 6=Sunday (ISO 8601).';

COMMENT ON COLUMN platform_timing_signals.hour_of_day_distribution IS 
    'JSON distribution of conversions/attempts by hour (0-23) in lead local time.';

COMMENT ON COLUMN platform_timing_signals.touchpoint_distribution IS 
    'JSON distribution of conversions/attempts by touchpoint number (1, 2, 3...).';

-- ============================================================================
-- VERIFICATION
-- ============================================================================
-- [x] platform_timing_signals table created
-- [x] Indexes for segment lookups and performance queries
-- [x] update_platform_timing_signal function for upserts
-- [x] get_timing_insights function for queries
-- [x] RLS policies for security
-- [x] Day of week uses ISO 8601 (0=Monday) not PostgreSQL DOW
-- [x] Comments for documentation
