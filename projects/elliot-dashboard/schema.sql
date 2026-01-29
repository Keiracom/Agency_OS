-- Elliot Dashboard Database Schema
-- Run this in Supabase SQL Editor
-- ================================

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";  -- For text search

-- ============================================
-- CORE MEMORY TABLES
-- ============================================

-- Daily memory logs (mirrors memory/daily/*.md)
CREATE TABLE elliot_daily_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    log_date DATE NOT NULL UNIQUE,
    
    -- Structured content
    accomplishments JSONB DEFAULT '[]'::jsonb,      -- Array of accomplishment strings
    interactions JSONB DEFAULT '[]'::jsonb,         -- Array of interaction records
    issues JSONB DEFAULT '[]'::jsonb,               -- Array of issues/problems
    notes TEXT,                                      -- Free-form notes
    
    -- Raw markdown (for full fidelity)
    raw_content TEXT,
    
    -- Sync metadata
    file_checksum VARCHAR(64),                       -- MD5 of source file
    sync_source VARCHAR(20) DEFAULT 'file',          -- 'file' or 'dashboard'
    synced_at TIMESTAMPTZ,
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_daily_logs_date ON elliot_daily_logs(log_date DESC);
CREATE INDEX idx_daily_logs_accomplishments ON elliot_daily_logs USING GIN(accomplishments);

-- Weekly rollups (mirrors memory/weekly/*.md)
CREATE TABLE elliot_weekly_rollups (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    year_week VARCHAR(10) NOT NULL UNIQUE,           -- Format: 2026-W04
    week_start DATE NOT NULL,
    week_end DATE NOT NULL,
    
    -- Synthesized content
    key_accomplishments JSONB DEFAULT '[]'::jsonb,
    decisions_made JSONB DEFAULT '[]'::jsonb,
    patterns_noticed JSONB DEFAULT '[]'::jsonb,
    open_questions JSONB DEFAULT '[]'::jsonb,
    summary TEXT,
    
    -- Raw markdown
    raw_content TEXT,
    
    -- Sync metadata
    file_checksum VARCHAR(64),
    synced_at TIMESTAMPTZ,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_weekly_rollups_week ON elliot_weekly_rollups(week_start DESC);

-- Patterns (mirrors memory/PATTERNS.md)
CREATE TABLE elliot_patterns (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    pattern_key VARCHAR(100) NOT NULL UNIQUE,        -- Slug identifier
    title VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    
    -- Evidence and frequency
    first_observed DATE,
    last_observed DATE,
    occurrence_count INTEGER DEFAULT 1,
    evidence JSONB DEFAULT '[]'::jsonb,              -- Array of {date, source, excerpt}
    
    -- Classification
    category VARCHAR(50),                            -- e.g., 'behavior', 'workflow', 'communication'
    status VARCHAR(20) DEFAULT 'active',             -- 'active', 'resolved', 'archived'
    
    -- Links
    related_learnings UUID[],                        -- References to elliot_learnings
    related_decisions UUID[],                        -- References to elliot_decisions
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_patterns_category ON elliot_patterns(category);
CREATE INDEX idx_patterns_status ON elliot_patterns(status);

-- ============================================
-- KNOWLEDGE BASE TABLES
-- ============================================

-- Operating rules (mirrors knowledge/RULES.md)
CREATE TABLE elliot_rules (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    rule_key VARCHAR(100) NOT NULL UNIQUE,
    category VARCHAR(50) NOT NULL,                   -- e.g., 'communication', 'safety', 'workflow'
    title VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    
    -- Rule properties
    severity VARCHAR(20) DEFAULT 'standard',         -- 'critical', 'standard', 'guideline'
    is_active BOOLEAN DEFAULT true,
    
    -- Source tracking
    source TEXT,                                     -- Why this rule exists
    added_date DATE DEFAULT CURRENT_DATE,
    
    -- Ordering
    sort_order INTEGER DEFAULT 0,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_rules_category ON elliot_rules(category);
CREATE INDEX idx_rules_active ON elliot_rules(is_active);

-- Learnings (mirrors knowledge/LEARNINGS.md)
CREATE TABLE elliot_learnings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    learning_key VARCHAR(100) NOT NULL UNIQUE,
    category VARCHAR(50),
    title VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    
    -- Context
    context TEXT,                                    -- When/why this was learned
    source_type VARCHAR(50),                         -- 'experience', 'feedback', 'observation'
    
    -- Evidence
    learned_date DATE DEFAULT CURRENT_DATE,
    source_daily_logs UUID[],                        -- Reference to daily logs where extracted
    evidence JSONB DEFAULT '[]'::jsonb,
    
    -- Impact
    impact_level VARCHAR(20) DEFAULT 'medium',       -- 'high', 'medium', 'low'
    times_applied INTEGER DEFAULT 0,                 -- How often this has been useful
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_learnings_category ON elliot_learnings(category);
CREATE INDEX idx_learnings_date ON elliot_learnings(learned_date DESC);
CREATE INDEX idx_learnings_impact ON elliot_learnings(impact_level);

-- Decisions (mirrors knowledge/DECISIONS.md)
CREATE TABLE elliot_decisions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    decision_key VARCHAR(100) NOT NULL UNIQUE,
    title VARCHAR(255) NOT NULL,
    
    -- Decision details
    decision_date DATE NOT NULL DEFAULT CURRENT_DATE,
    context TEXT NOT NULL,                           -- Why this came up
    options JSONB DEFAULT '[]'::jsonb,               -- Array of options considered
    chosen_option TEXT NOT NULL,                     -- What was decided
    rationale TEXT NOT NULL,                         -- Why this option
    
    -- Outcome tracking
    expected_outcome TEXT,
    actual_outcome TEXT,
    outcome_date DATE,
    outcome_status VARCHAR(20) DEFAULT 'pending',    -- 'pending', 'success', 'partial', 'failure'
    
    -- Learning extraction
    learning_extracted TEXT,
    linked_learning_id UUID REFERENCES elliot_learnings(id),
    
    -- Classification
    category VARCHAR(50),
    importance VARCHAR(20) DEFAULT 'medium',         -- 'critical', 'high', 'medium', 'low'
    
    -- Who was involved
    stakeholders JSONB DEFAULT '[]'::jsonb,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_decisions_date ON elliot_decisions(decision_date DESC);
CREATE INDEX idx_decisions_status ON elliot_decisions(outcome_status);
CREATE INDEX idx_decisions_category ON elliot_decisions(category);

-- ============================================
-- ACTIVITY & MONITORING TABLES
-- ============================================

-- Real-time activity stream
CREATE TABLE elliot_activity (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- Activity details
    activity_type VARCHAR(50) NOT NULL,              -- 'message', 'file_read', 'file_write', 'api_call', 'thinking', 'decision'
    channel VARCHAR(50),                             -- 'telegram', 'discord', 'heartbeat', 'cron'
    
    -- Content
    summary TEXT NOT NULL,                           -- Brief description
    details JSONB,                                   -- Full details (context-specific)
    
    -- Relationships
    related_files TEXT[],                            -- Files accessed/modified
    related_decision_id UUID REFERENCES elliot_decisions(id),
    session_id VARCHAR(100),                         -- Clawdbot session identifier
    
    -- Metrics
    duration_ms INTEGER,                             -- How long this took
    token_usage JSONB,                               -- {input: X, output: Y}
    
    -- Status
    status VARCHAR(20) DEFAULT 'completed',          -- 'started', 'completed', 'error'
    error_message TEXT,
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_activity_created ON elliot_activity(created_at DESC);
CREATE INDEX idx_activity_type ON elliot_activity(activity_type);
CREATE INDEX idx_activity_channel ON elliot_activity(channel);
CREATE INDEX idx_activity_session ON elliot_activity(session_id);

-- Aggregate activity stats (materialized for performance)
CREATE TABLE elliot_activity_stats (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    stat_date DATE NOT NULL,
    stat_hour INTEGER,                               -- NULL for daily totals, 0-23 for hourly
    
    -- Counts
    total_activities INTEGER DEFAULT 0,
    messages_sent INTEGER DEFAULT 0,
    files_accessed INTEGER DEFAULT 0,
    decisions_made INTEGER DEFAULT 0,
    errors INTEGER DEFAULT 0,
    
    -- Token usage
    total_input_tokens INTEGER DEFAULT 0,
    total_output_tokens INTEGER DEFAULT 0,
    
    -- Channels breakdown
    channel_breakdown JSONB,                         -- {telegram: 10, discord: 5, ...}
    activity_breakdown JSONB,                        -- {message: 15, file_read: 20, ...}
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(stat_date, stat_hour)
);

CREATE INDEX idx_activity_stats_date ON elliot_activity_stats(stat_date DESC);

-- ============================================
-- SYNC & METADATA TABLES
-- ============================================

-- Sync state tracking
CREATE TABLE elliot_sync_state (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    file_path VARCHAR(500) NOT NULL UNIQUE,
    file_type VARCHAR(50) NOT NULL,                  -- 'daily', 'weekly', 'patterns', 'rules', etc.
    
    -- File metadata
    file_checksum VARCHAR(64),
    file_size INTEGER,
    file_modified_at TIMESTAMPTZ,
    
    -- Sync status
    last_sync_at TIMESTAMPTZ,
    last_sync_direction VARCHAR(20),                 -- 'file_to_db', 'db_to_file'
    sync_status VARCHAR(20) DEFAULT 'synced',        -- 'synced', 'pending', 'conflict', 'error'
    sync_error TEXT,
    
    -- Related record
    related_table VARCHAR(100),
    related_id UUID,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_sync_state_path ON elliot_sync_state(file_path);
CREATE INDEX idx_sync_state_status ON elliot_sync_state(sync_status);

-- ============================================
-- SERVICE HEALTH TABLES
-- ============================================

-- Service health status
CREATE TABLE service_health (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    service_name VARCHAR(100) NOT NULL UNIQUE,
    
    -- Current status
    status VARCHAR(20) NOT NULL DEFAULT 'unknown',   -- 'healthy', 'degraded', 'down', 'unknown'
    last_check_at TIMESTAMPTZ,
    response_time_ms INTEGER,
    
    -- Details
    details JSONB,                                   -- Service-specific health info
    error_message TEXT,
    
    -- Config
    check_url VARCHAR(500),
    check_interval_seconds INTEGER DEFAULT 60,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Health check history
CREATE TABLE service_health_history (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    service_id UUID REFERENCES service_health(id),
    
    status VARCHAR(20) NOT NULL,
    response_time_ms INTEGER,
    details JSONB,
    error_message TEXT,
    
    checked_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_health_history_service ON service_health_history(service_id, checked_at DESC);

-- ============================================
-- VIEWS
-- ============================================

-- Recent activity summary
CREATE VIEW elliot_activity_recent AS
SELECT 
    id,
    activity_type,
    channel,
    summary,
    status,
    created_at,
    EXTRACT(EPOCH FROM (NOW() - created_at)) / 60 AS minutes_ago
FROM elliot_activity
WHERE created_at > NOW() - INTERVAL '24 hours'
ORDER BY created_at DESC;

-- Pending decisions (awaiting outcome)
CREATE VIEW elliot_decisions_pending AS
SELECT 
    id,
    title,
    decision_date,
    expected_outcome,
    importance,
    CURRENT_DATE - decision_date AS days_since_decision
FROM elliot_decisions
WHERE outcome_status = 'pending'
ORDER BY importance DESC, decision_date ASC;

-- Pattern insights
CREATE VIEW elliot_pattern_insights AS
SELECT 
    p.id,
    p.title,
    p.category,
    p.occurrence_count,
    p.last_observed,
    CURRENT_DATE - p.last_observed AS days_since_last,
    array_length(p.related_learnings, 1) AS linked_learnings_count
FROM elliot_patterns p
WHERE p.status = 'active'
ORDER BY p.occurrence_count DESC, p.last_observed DESC;

-- ============================================
-- FUNCTIONS & TRIGGERS
-- ============================================

-- Update timestamp trigger
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply to all tables with updated_at
CREATE TRIGGER update_daily_logs_updated_at
    BEFORE UPDATE ON elliot_daily_logs
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER update_weekly_rollups_updated_at
    BEFORE UPDATE ON elliot_weekly_rollups
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER update_patterns_updated_at
    BEFORE UPDATE ON elliot_patterns
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER update_rules_updated_at
    BEFORE UPDATE ON elliot_rules
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER update_learnings_updated_at
    BEFORE UPDATE ON elliot_learnings
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER update_decisions_updated_at
    BEFORE UPDATE ON elliot_decisions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- Function to aggregate activity stats
CREATE OR REPLACE FUNCTION aggregate_activity_stats(target_date DATE)
RETURNS void AS $$
BEGIN
    INSERT INTO elliot_activity_stats (
        stat_date, 
        stat_hour,
        total_activities,
        messages_sent,
        files_accessed,
        decisions_made,
        errors,
        total_input_tokens,
        total_output_tokens,
        channel_breakdown,
        activity_breakdown
    )
    SELECT 
        target_date,
        NULL,  -- Daily aggregate
        COUNT(*),
        COUNT(*) FILTER (WHERE activity_type = 'message'),
        COUNT(*) FILTER (WHERE activity_type IN ('file_read', 'file_write')),
        COUNT(*) FILTER (WHERE activity_type = 'decision'),
        COUNT(*) FILTER (WHERE status = 'error'),
        COALESCE(SUM((token_usage->>'input')::integer), 0),
        COALESCE(SUM((token_usage->>'output')::integer), 0),
        jsonb_object_agg(COALESCE(channel, 'unknown'), channel_count) FILTER (WHERE channel IS NOT NULL),
        jsonb_object_agg(activity_type, type_count)
    FROM (
        SELECT 
            activity_type,
            channel,
            status,
            token_usage,
            COUNT(*) OVER (PARTITION BY channel) as channel_count,
            COUNT(*) OVER (PARTITION BY activity_type) as type_count
        FROM elliot_activity
        WHERE created_at::date = target_date
    ) sub
    ON CONFLICT (stat_date, stat_hour) 
    DO UPDATE SET
        total_activities = EXCLUDED.total_activities,
        messages_sent = EXCLUDED.messages_sent,
        files_accessed = EXCLUDED.files_accessed,
        decisions_made = EXCLUDED.decisions_made,
        errors = EXCLUDED.errors,
        total_input_tokens = EXCLUDED.total_input_tokens,
        total_output_tokens = EXCLUDED.total_output_tokens,
        channel_breakdown = EXCLUDED.channel_breakdown,
        activity_breakdown = EXCLUDED.activity_breakdown,
        updated_at = NOW();
END;
$$ LANGUAGE plpgsql;

-- ============================================
-- ROW LEVEL SECURITY
-- ============================================

-- Enable RLS on all Elliot tables
ALTER TABLE elliot_daily_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE elliot_weekly_rollups ENABLE ROW LEVEL SECURITY;
ALTER TABLE elliot_patterns ENABLE ROW LEVEL SECURITY;
ALTER TABLE elliot_rules ENABLE ROW LEVEL SECURITY;
ALTER TABLE elliot_learnings ENABLE ROW LEVEL SECURITY;
ALTER TABLE elliot_decisions ENABLE ROW LEVEL SECURITY;
ALTER TABLE elliot_activity ENABLE ROW LEVEL SECURITY;
ALTER TABLE elliot_activity_stats ENABLE ROW LEVEL SECURITY;
ALTER TABLE elliot_sync_state ENABLE ROW LEVEL SECURITY;
ALTER TABLE service_health ENABLE ROW LEVEL SECURITY;
ALTER TABLE service_health_history ENABLE ROW LEVEL SECURITY;

-- Admin-only access policies
-- Note: Adjust based on your auth setup. This assumes a 'role' claim in JWT.
CREATE POLICY "Admin access only" ON elliot_daily_logs
    FOR ALL USING (
        auth.jwt() ->> 'email' = 'dave@agency-os.com'
        OR auth.jwt() ->> 'role' = 'admin'
    );

CREATE POLICY "Admin access only" ON elliot_weekly_rollups
    FOR ALL USING (
        auth.jwt() ->> 'email' = 'dave@agency-os.com'
        OR auth.jwt() ->> 'role' = 'admin'
    );

CREATE POLICY "Admin access only" ON elliot_patterns
    FOR ALL USING (
        auth.jwt() ->> 'email' = 'dave@agency-os.com'
        OR auth.jwt() ->> 'role' = 'admin'
    );

CREATE POLICY "Admin access only" ON elliot_rules
    FOR ALL USING (
        auth.jwt() ->> 'email' = 'dave@agency-os.com'
        OR auth.jwt() ->> 'role' = 'admin'
    );

CREATE POLICY "Admin access only" ON elliot_learnings
    FOR ALL USING (
        auth.jwt() ->> 'email' = 'dave@agency-os.com'
        OR auth.jwt() ->> 'role' = 'admin'
    );

CREATE POLICY "Admin access only" ON elliot_decisions
    FOR ALL USING (
        auth.jwt() ->> 'email' = 'dave@agency-os.com'
        OR auth.jwt() ->> 'role' = 'admin'
    );

CREATE POLICY "Admin access only" ON elliot_activity
    FOR ALL USING (
        auth.jwt() ->> 'email' = 'dave@agency-os.com'
        OR auth.jwt() ->> 'role' = 'admin'
    );

CREATE POLICY "Admin access only" ON elliot_activity_stats
    FOR ALL USING (
        auth.jwt() ->> 'email' = 'dave@agency-os.com'
        OR auth.jwt() ->> 'role' = 'admin'
    );

CREATE POLICY "Admin access only" ON elliot_sync_state
    FOR ALL USING (
        auth.jwt() ->> 'email' = 'dave@agency-os.com'
        OR auth.jwt() ->> 'role' = 'admin'
    );

CREATE POLICY "Admin access only" ON service_health
    FOR ALL USING (
        auth.jwt() ->> 'email' = 'dave@agency-os.com'
        OR auth.jwt() ->> 'role' = 'admin'
    );

CREATE POLICY "Admin access only" ON service_health_history
    FOR ALL USING (
        auth.jwt() ->> 'email' = 'dave@agency-os.com'
        OR auth.jwt() ->> 'role' = 'admin'
    );

-- ============================================
-- INITIAL DATA
-- ============================================

-- Initialize service health entries
INSERT INTO service_health (service_name, status, check_url, check_interval_seconds) VALUES
    ('supabase', 'unknown', NULL, 60),
    ('railway-backend', 'unknown', 'https://api.agency-os.com/health', 60),
    ('vercel-frontend', 'unknown', 'https://agency-os.com/api/health', 60),
    ('prefect', 'unknown', 'https://prefect-server-production-f9b1.up.railway.app/api/health', 60),
    ('redis-upstash', 'unknown', NULL, 60),
    ('clawdbot', 'unknown', NULL, 300)
ON CONFLICT (service_name) DO NOTHING;

-- ============================================
-- REALTIME SUBSCRIPTIONS
-- ============================================

-- Enable realtime for activity feed
ALTER PUBLICATION supabase_realtime ADD TABLE elliot_activity;
ALTER PUBLICATION supabase_realtime ADD TABLE elliot_decisions;
ALTER PUBLICATION supabase_realtime ADD TABLE service_health;
