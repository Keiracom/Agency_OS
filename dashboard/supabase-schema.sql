-- Elliot Dashboard Schema
-- Run this in Supabase SQL Editor

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================
-- ELLIOT DECISIONS
-- Tracks significant decisions with context and outcomes
-- ============================================
CREATE TABLE IF NOT EXISTS elliot_decisions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    decision TEXT NOT NULL,
    context TEXT,
    rationale TEXT,
    outcome TEXT,
    outcome_rating INTEGER CHECK (outcome_rating >= 1 AND outcome_rating <= 5),
    tags TEXT[] DEFAULT '{}',
    session_id TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_decisions_created ON elliot_decisions(created_at DESC);
CREATE INDEX idx_decisions_tags ON elliot_decisions USING GIN(tags);

-- ============================================
-- ELLIOT LEARNINGS
-- Permanent lessons extracted from experience
-- ============================================
CREATE TABLE IF NOT EXISTS elliot_learnings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    lesson TEXT NOT NULL,
    source TEXT,
    category TEXT DEFAULT 'general',
    confidence DECIMAL(3,2) DEFAULT 0.80,
    applications INTEGER DEFAULT 0,
    tags TEXT[] DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_learnings_category ON elliot_learnings(category);
CREATE INDEX idx_learnings_created ON elliot_learnings(created_at DESC);

-- ============================================
-- ELLIOT ACTIVITY
-- Agent activity log (spawned tasks, tool calls, etc)
-- ============================================
CREATE TABLE IF NOT EXISTS elliot_activity (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    action TEXT NOT NULL,
    action_type TEXT DEFAULT 'task', -- task, tool_call, message, heartbeat, sync
    status TEXT DEFAULT 'pending', -- pending, running, completed, failed
    result TEXT,
    tokens_used INTEGER DEFAULT 0,
    cost_usd DECIMAL(10,6) DEFAULT 0,
    duration_ms INTEGER,
    session_id TEXT,
    parent_id UUID REFERENCES elliot_activity(id),
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);

CREATE INDEX idx_activity_created ON elliot_activity(created_at DESC);
CREATE INDEX idx_activity_type ON elliot_activity(action_type);
CREATE INDEX idx_activity_status ON elliot_activity(status);
CREATE INDEX idx_activity_session ON elliot_activity(session_id);

-- ============================================
-- ELLIOT PATTERNS
-- Recurring behavioral/contextual patterns
-- ============================================
CREATE TABLE IF NOT EXISTS elliot_patterns (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    pattern TEXT NOT NULL,
    description TEXT,
    occurrences INTEGER DEFAULT 1,
    category TEXT DEFAULT 'behavioral',
    first_seen TIMESTAMPTZ DEFAULT NOW(),
    last_seen TIMESTAMPTZ DEFAULT NOW(),
    examples TEXT[] DEFAULT '{}',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_patterns_category ON elliot_patterns(category);
CREATE INDEX idx_patterns_occurrences ON elliot_patterns(occurrences DESC);

-- ============================================
-- ELLIOT MEMORY
-- Key-value store for persistent memory items
-- ============================================
CREATE TABLE IF NOT EXISTS elliot_memory (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    key TEXT NOT NULL UNIQUE,
    value TEXT NOT NULL,
    category TEXT DEFAULT 'general',
    importance INTEGER DEFAULT 5 CHECK (importance >= 1 AND importance <= 10),
    access_count INTEGER DEFAULT 0,
    last_accessed TIMESTAMPTZ,
    expires_at TIMESTAMPTZ,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_memory_key ON elliot_memory(key);
CREATE INDEX idx_memory_category ON elliot_memory(category);
CREATE INDEX idx_memory_importance ON elliot_memory(importance DESC);

-- ============================================
-- ELLIOT RULES
-- Non-negotiable constraints and operational rules
-- ============================================
CREATE TABLE IF NOT EXISTS elliot_rules (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    rule TEXT NOT NULL,
    category TEXT DEFAULT 'operational',
    priority INTEGER DEFAULT 5 CHECK (priority >= 1 AND priority <= 10),
    source TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_rules_category ON elliot_rules(category);
CREATE INDEX idx_rules_priority ON elliot_rules(priority DESC);

-- ============================================
-- ELLIOT SESSIONS
-- Track session health and context usage
-- ============================================
CREATE TABLE IF NOT EXISTS elliot_sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id TEXT UNIQUE NOT NULL,
    channel TEXT, -- telegram, discord, etc
    started_at TIMESTAMPTZ DEFAULT NOW(),
    ended_at TIMESTAMPTZ,
    messages_count INTEGER DEFAULT 0,
    tokens_input INTEGER DEFAULT 0,
    tokens_output INTEGER DEFAULT 0,
    context_percentage DECIMAL(5,2) DEFAULT 0,
    total_cost_usd DECIMAL(10,6) DEFAULT 0,
    status TEXT DEFAULT 'active', -- active, ended, crashed
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_sessions_session_id ON elliot_sessions(session_id);
CREATE INDEX idx_sessions_created ON elliot_sessions(created_at DESC);

-- ============================================
-- VIEWS FOR DASHBOARD
-- ============================================

-- Daily activity summary
CREATE OR REPLACE VIEW elliot_daily_stats AS
SELECT 
    DATE(created_at) as date,
    COUNT(*) as total_activities,
    COUNT(*) FILTER (WHERE status = 'completed') as completed,
    COUNT(*) FILTER (WHERE status = 'failed') as failed,
    SUM(tokens_used) as total_tokens,
    SUM(cost_usd) as total_cost,
    AVG(duration_ms) as avg_duration_ms
FROM elliot_activity
GROUP BY DATE(created_at)
ORDER BY date DESC;

-- Recent activity feed (last 50)
CREATE OR REPLACE VIEW elliot_recent_activity AS
SELECT 
    id,
    action,
    action_type,
    status,
    result,
    tokens_used,
    cost_usd,
    duration_ms,
    created_at,
    completed_at
FROM elliot_activity
ORDER BY created_at DESC
LIMIT 50;

-- Memory by category
CREATE OR REPLACE VIEW elliot_memory_by_category AS
SELECT 
    category,
    COUNT(*) as count,
    AVG(importance) as avg_importance
FROM elliot_memory
GROUP BY category
ORDER BY count DESC;

-- ============================================
-- ROW LEVEL SECURITY (RLS)
-- ============================================

-- Enable RLS on all tables
ALTER TABLE elliot_decisions ENABLE ROW LEVEL SECURITY;
ALTER TABLE elliot_learnings ENABLE ROW LEVEL SECURITY;
ALTER TABLE elliot_activity ENABLE ROW LEVEL SECURITY;
ALTER TABLE elliot_patterns ENABLE ROW LEVEL SECURITY;
ALTER TABLE elliot_memory ENABLE ROW LEVEL SECURITY;
ALTER TABLE elliot_rules ENABLE ROW LEVEL SECURITY;
ALTER TABLE elliot_sessions ENABLE ROW LEVEL SECURITY;

-- Create policies for service role (full access)
CREATE POLICY "Service role full access" ON elliot_decisions FOR ALL USING (true);
CREATE POLICY "Service role full access" ON elliot_learnings FOR ALL USING (true);
CREATE POLICY "Service role full access" ON elliot_activity FOR ALL USING (true);
CREATE POLICY "Service role full access" ON elliot_patterns FOR ALL USING (true);
CREATE POLICY "Service role full access" ON elliot_memory FOR ALL USING (true);
CREATE POLICY "Service role full access" ON elliot_rules FOR ALL USING (true);
CREATE POLICY "Service role full access" ON elliot_sessions FOR ALL USING (true);

-- ============================================
-- FUNCTIONS
-- ============================================

-- Update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Add triggers for updated_at
CREATE TRIGGER update_decisions_updated_at BEFORE UPDATE ON elliot_decisions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER update_learnings_updated_at BEFORE UPDATE ON elliot_learnings
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER update_patterns_updated_at BEFORE UPDATE ON elliot_patterns
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER update_memory_updated_at BEFORE UPDATE ON elliot_memory
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER update_rules_updated_at BEFORE UPDATE ON elliot_rules
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER update_sessions_updated_at BEFORE UPDATE ON elliot_sessions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- Function to get dashboard stats
CREATE OR REPLACE FUNCTION get_elliot_stats()
RETURNS JSON AS $$
DECLARE
    result JSON;
BEGIN
    SELECT json_build_object(
        'decisions_count', (SELECT COUNT(*) FROM elliot_decisions),
        'learnings_count', (SELECT COUNT(*) FROM elliot_learnings),
        'patterns_count', (SELECT COUNT(*) FROM elliot_patterns WHERE is_active = true),
        'memory_items', (SELECT COUNT(*) FROM elliot_memory),
        'rules_count', (SELECT COUNT(*) FROM elliot_rules WHERE is_active = true),
        'today_activities', (SELECT COUNT(*) FROM elliot_activity WHERE DATE(created_at) = CURRENT_DATE),
        'today_tokens', (SELECT COALESCE(SUM(tokens_used), 0) FROM elliot_activity WHERE DATE(created_at) = CURRENT_DATE),
        'today_cost', (SELECT COALESCE(SUM(cost_usd), 0) FROM elliot_activity WHERE DATE(created_at) = CURRENT_DATE),
        'active_sessions', (SELECT COUNT(*) FROM elliot_sessions WHERE status = 'active'),
        'last_activity', (SELECT created_at FROM elliot_activity ORDER BY created_at DESC LIMIT 1)
    ) INTO result;
    
    RETURN result;
END;
$$ LANGUAGE plpgsql;

-- Function to log activity
CREATE OR REPLACE FUNCTION log_elliot_activity(
    p_action TEXT,
    p_action_type TEXT DEFAULT 'task',
    p_status TEXT DEFAULT 'completed',
    p_result TEXT DEFAULT NULL,
    p_tokens_used INTEGER DEFAULT 0,
    p_cost_usd DECIMAL DEFAULT 0,
    p_duration_ms INTEGER DEFAULT NULL,
    p_session_id TEXT DEFAULT NULL,
    p_metadata JSONB DEFAULT '{}'
)
RETURNS UUID AS $$
DECLARE
    new_id UUID;
BEGIN
    INSERT INTO elliot_activity (
        action, action_type, status, result, tokens_used, 
        cost_usd, duration_ms, session_id, metadata, completed_at
    ) VALUES (
        p_action, p_action_type, p_status, p_result, p_tokens_used,
        p_cost_usd, p_duration_ms, p_session_id, p_metadata,
        CASE WHEN p_status IN ('completed', 'failed') THEN NOW() ELSE NULL END
    )
    RETURNING id INTO new_id;
    
    RETURN new_id;
END;
$$ LANGUAGE plpgsql;

-- Grant execute on functions
GRANT EXECUTE ON FUNCTION get_elliot_stats() TO authenticated, anon;
GRANT EXECUTE ON FUNCTION log_elliot_activity(TEXT, TEXT, TEXT, TEXT, INTEGER, DECIMAL, INTEGER, TEXT, JSONB) TO authenticated, anon;
