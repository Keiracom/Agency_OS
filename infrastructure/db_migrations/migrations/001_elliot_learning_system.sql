-- Elliot Persistent Learning System - Phase 1
-- Migration: 001_elliot_learning_system.sql
-- Created: 2025-01-30

-- Enable pgvector extension (required for semantic search)
CREATE EXTENSION IF NOT EXISTS vector;

-- ============================================
-- Table: elliot_knowledge
-- Purpose: Store learned insights with embeddings for semantic retrieval
-- ============================================
CREATE TABLE IF NOT EXISTS elliot_knowledge (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    category TEXT NOT NULL CHECK (category IN (
        'tech_trend', 'market_signal', 'tool_discovery', 
        'pattern_recognition', 'user_preference', 'workflow_optimization',
        'business_insight', 'competitor_intel', 'general'
    )),
    content TEXT NOT NULL,
    summary TEXT, -- One-line summary for quick context injection
    embedding vector(1536), -- OpenAI ada-002 compatible
    source_url TEXT,
    source_type TEXT CHECK (source_type IN ('hackernews', 'producthunt', 'github', 'manual', 'conversation', 'inference')),
    learned_at TIMESTAMPTZ DEFAULT NOW(),
    applied BOOLEAN DEFAULT FALSE,
    applied_at TIMESTAMPTZ,
    confidence_score FLOAT CHECK (confidence_score >= 0 AND confidence_score <= 1) DEFAULT 0.5,
    relevance_decay FLOAT DEFAULT 1.0, -- Decreases over time for time-sensitive info
    tags TEXT[], -- Flexible tagging for filtering
    metadata JSONB DEFAULT '{}'::jsonb,
    
    -- Soft delete
    deleted_at TIMESTAMPTZ
);

-- Indexes for common query patterns
CREATE INDEX IF NOT EXISTS idx_knowledge_category ON elliot_knowledge(category) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_knowledge_learned_at ON elliot_knowledge(learned_at DESC) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_knowledge_applied ON elliot_knowledge(applied) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_knowledge_source_type ON elliot_knowledge(source_type) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_knowledge_tags ON elliot_knowledge USING GIN(tags) WHERE deleted_at IS NULL;

-- Vector similarity search index (IVFFlat for performance)
CREATE INDEX IF NOT EXISTS idx_knowledge_embedding ON elliot_knowledge 
    USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100)
    WHERE deleted_at IS NULL AND embedding IS NOT NULL;

-- ============================================
-- Table: elliot_session_state
-- Purpose: Cross-session state persistence (tasks, context, todos)
-- ============================================
CREATE TABLE IF NOT EXISTS elliot_session_state (
    key TEXT PRIMARY KEY,
    value JSONB NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ, -- Optional TTL
    version INTEGER DEFAULT 1 -- Optimistic locking
);

-- Auto-update timestamp trigger
CREATE OR REPLACE FUNCTION update_session_state_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    NEW.version = OLD.version + 1;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_session_state_timestamp ON elliot_session_state;
CREATE TRIGGER trigger_session_state_timestamp
    BEFORE UPDATE ON elliot_session_state
    FOR EACH ROW
    EXECUTE FUNCTION update_session_state_timestamp();

-- ============================================
-- Function: search_knowledge_by_embedding
-- Purpose: Semantic search with configurable filters
-- ============================================
CREATE OR REPLACE FUNCTION search_knowledge_by_embedding(
    query_embedding vector(1536),
    match_threshold FLOAT DEFAULT 0.7,
    match_count INT DEFAULT 10,
    filter_categories TEXT[] DEFAULT NULL,
    filter_source_types TEXT[] DEFAULT NULL,
    include_applied BOOLEAN DEFAULT TRUE
)
RETURNS TABLE (
    id UUID,
    category TEXT,
    content TEXT,
    summary TEXT,
    source_url TEXT,
    confidence_score FLOAT,
    similarity FLOAT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        k.id,
        k.category,
        k.content,
        k.summary,
        k.source_url,
        k.confidence_score,
        1 - (k.embedding <=> query_embedding) AS similarity
    FROM elliot_knowledge k
    WHERE 
        k.deleted_at IS NULL
        AND k.embedding IS NOT NULL
        AND 1 - (k.embedding <=> query_embedding) > match_threshold
        AND (filter_categories IS NULL OR k.category = ANY(filter_categories))
        AND (filter_source_types IS NULL OR k.source_type = ANY(filter_source_types))
        AND (include_applied OR NOT k.applied)
    ORDER BY k.embedding <=> query_embedding
    LIMIT match_count;
END;
$$ LANGUAGE plpgsql;

-- ============================================
-- Function: get_bootstrap_context
-- Purpose: Retrieve relevant knowledge for session initialization
-- ============================================
CREATE OR REPLACE FUNCTION get_bootstrap_context(
    max_items INT DEFAULT 20,
    max_age_hours INT DEFAULT 168 -- 1 week default
)
RETURNS TABLE (
    category TEXT,
    content TEXT,
    summary TEXT,
    source_type TEXT,
    confidence_score FLOAT,
    learned_at TIMESTAMPTZ
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        k.category,
        k.content,
        k.summary,
        k.source_type,
        k.confidence_score,
        k.learned_at
    FROM elliot_knowledge k
    WHERE 
        k.deleted_at IS NULL
        AND k.learned_at > NOW() - (max_age_hours || ' hours')::INTERVAL
        AND k.confidence_score >= 0.6
    ORDER BY 
        k.confidence_score DESC,
        k.learned_at DESC
    LIMIT max_items;
END;
$$ LANGUAGE plpgsql;

-- ============================================
-- RLS Policies (if needed for API access)
-- ============================================
ALTER TABLE elliot_knowledge ENABLE ROW LEVEL SECURITY;
ALTER TABLE elliot_session_state ENABLE ROW LEVEL SECURITY;

-- Service role bypass (for backend operations)
CREATE POLICY "Service role full access on knowledge" ON elliot_knowledge
    FOR ALL USING (auth.role() = 'service_role');

CREATE POLICY "Service role full access on session_state" ON elliot_session_state
    FOR ALL USING (auth.role() = 'service_role');

-- ============================================
-- Initial seed data for session state
-- ============================================
INSERT INTO elliot_session_state (key, value) VALUES
    ('elliot:current_task', '{"task": null, "started_at": null}'::jsonb),
    ('elliot:last_session', '{"session_id": null, "ended_at": null, "summary": null}'::jsonb),
    ('elliot:pending_todos', '[]'::jsonb),
    ('elliot:learning_stats', '{"total_learned": 0, "last_scrape": null}'::jsonb)
ON CONFLICT (key) DO NOTHING;

COMMENT ON TABLE elliot_knowledge IS 'Persistent knowledge base for Elliot cross-session memory';
COMMENT ON TABLE elliot_session_state IS 'Key-value store for session continuity state';
