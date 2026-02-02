-- ============================================
-- MIGRATION: 001_elliot_brain.sql
-- PURPOSE: Create isolated schema for Elliot's persistent memory
-- DATE: 2026-02-01
-- STATUS: PENDING REVIEW
-- ============================================

-- ============================================
-- 1. ENABLE EXTENSIONS (if not already enabled)
-- ============================================

-- pgvector for semantic search
CREATE EXTENSION IF NOT EXISTS vector;

-- pgcrypto for gen_random_uuid() (usually already enabled in Supabase)
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- ============================================
-- 2. CREATE ISOLATED SCHEMA
-- ============================================

CREATE SCHEMA IF NOT EXISTS elliot_internal;

-- Set search path for this migration
SET search_path TO elliot_internal, public;

-- ============================================
-- 3. MEMORIES TABLE (Vector-enabled knowledge store)
-- ============================================

CREATE TABLE IF NOT EXISTS elliot_internal.memories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Content
    content TEXT NOT NULL,
    content_hash TEXT GENERATED ALWAYS AS (md5(content)) STORED,
    
    -- Classification
    type TEXT NOT NULL DEFAULT 'general',
    -- Types: 'core_fact', 'decision', 'learning', 'pattern', 'daily_log', 'legacy_import'
    
    -- Vector embedding for semantic search
    embedding vector(1536),  -- OpenAI ada-002 dimensions
    
    -- Metadata (flexible JSON)
    metadata JSONB DEFAULT '{}',
    -- Expected keys: source_file, section, importance, related_ids, tags
    
    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ,  -- NULL = never expires
    
    -- Soft delete
    deleted_at TIMESTAMPTZ
);

-- Indexes for memories
CREATE INDEX IF NOT EXISTS idx_memories_type ON elliot_internal.memories(type);
CREATE INDEX IF NOT EXISTS idx_memories_created ON elliot_internal.memories(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_memories_metadata ON elliot_internal.memories USING GIN(metadata);
CREATE INDEX IF NOT EXISTS idx_memories_embedding ON elliot_internal.memories 
    USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
CREATE INDEX IF NOT EXISTS idx_memories_content_hash ON elliot_internal.memories(content_hash);

-- ============================================
-- 4. STATE TABLE (Session & context persistence)
-- ============================================

CREATE TABLE IF NOT EXISTS elliot_internal.state (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- State identification
    key TEXT UNIQUE NOT NULL,
    -- Keys: 'current_session', 'active_tasks', 'context_snapshot', 'delegation_queue'
    
    -- State data
    value JSONB NOT NULL DEFAULT '{}',
    
    -- Versioning
    version INTEGER NOT NULL DEFAULT 1,
    
    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes for state
CREATE INDEX IF NOT EXISTS idx_state_key ON elliot_internal.state(key);
CREATE INDEX IF NOT EXISTS idx_state_updated ON elliot_internal.state(updated_at DESC);

-- ============================================
-- 5. PREFECT_LOGS TABLE (Workflow execution history)
-- ============================================

CREATE TABLE IF NOT EXISTS elliot_internal.prefect_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Prefect identifiers
    flow_run_id UUID,
    flow_name TEXT,
    deployment_name TEXT,
    
    -- Execution details
    state TEXT NOT NULL,
    -- States: 'SCHEDULED', 'PENDING', 'RUNNING', 'COMPLETED', 'FAILED', 'CANCELLED', 'CRASHED'
    
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    duration_seconds NUMERIC(10,2),
    
    -- Parameters & results
    parameters JSONB DEFAULT '{}',
    result JSONB,
    error_message TEXT,
    
    -- Metadata
    tags TEXT[] DEFAULT '{}',
    metadata JSONB DEFAULT '{}',
    
    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes for prefect_logs
CREATE INDEX IF NOT EXISTS idx_prefect_logs_flow_run ON elliot_internal.prefect_logs(flow_run_id);
CREATE INDEX IF NOT EXISTS idx_prefect_logs_flow_name ON elliot_internal.prefect_logs(flow_name);
CREATE INDEX IF NOT EXISTS idx_prefect_logs_state ON elliot_internal.prefect_logs(state);
CREATE INDEX IF NOT EXISTS idx_prefect_logs_started ON elliot_internal.prefect_logs(started_at DESC);
CREATE INDEX IF NOT EXISTS idx_prefect_logs_tags ON elliot_internal.prefect_logs USING GIN(tags);

-- ============================================
-- 6. HELPER FUNCTIONS
-- ============================================

-- Function: Semantic search on memories
CREATE OR REPLACE FUNCTION elliot_internal.search_memories(
    query_embedding vector(1536),
    match_threshold FLOAT DEFAULT 0.7,
    match_count INT DEFAULT 10,
    filter_type TEXT DEFAULT NULL
)
RETURNS TABLE (
    id UUID,
    content TEXT,
    type TEXT,
    metadata JSONB,
    similarity FLOAT
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT 
        m.id,
        m.content,
        m.type,
        m.metadata,
        1 - (m.embedding <=> query_embedding) AS similarity
    FROM elliot_internal.memories m
    WHERE 
        m.deleted_at IS NULL
        AND m.embedding IS NOT NULL
        AND (filter_type IS NULL OR m.type = filter_type)
        AND 1 - (m.embedding <=> query_embedding) > match_threshold
    ORDER BY m.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;

-- Function: Upsert state
CREATE OR REPLACE FUNCTION elliot_internal.upsert_state(
    p_key TEXT,
    p_value JSONB
)
RETURNS elliot_internal.state
LANGUAGE plpgsql
AS $$
DECLARE
    result elliot_internal.state;
BEGIN
    INSERT INTO elliot_internal.state (key, value, version)
    VALUES (p_key, p_value, 1)
    ON CONFLICT (key) DO UPDATE SET
        value = p_value,
        version = elliot_internal.state.version + 1,
        updated_at = NOW()
    RETURNING * INTO result;
    
    RETURN result;
END;
$$;

-- Function: Auto-update updated_at timestamp
CREATE OR REPLACE FUNCTION elliot_internal.update_timestamp()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$;

-- Triggers for updated_at
CREATE TRIGGER memories_updated_at
    BEFORE UPDATE ON elliot_internal.memories
    FOR EACH ROW EXECUTE FUNCTION elliot_internal.update_timestamp();

CREATE TRIGGER state_updated_at
    BEFORE UPDATE ON elliot_internal.state
    FOR EACH ROW EXECUTE FUNCTION elliot_internal.update_timestamp();

-- ============================================
-- 7. ROW LEVEL SECURITY (Optional - for future multi-agent)
-- ============================================

-- Enable RLS on tables (policies can be added later)
ALTER TABLE elliot_internal.memories ENABLE ROW LEVEL SECURITY;
ALTER TABLE elliot_internal.state ENABLE ROW LEVEL SECURITY;
ALTER TABLE elliot_internal.prefect_logs ENABLE ROW LEVEL SECURITY;

-- Allow service role full access
CREATE POLICY "Service role has full access to memories"
    ON elliot_internal.memories FOR ALL
    USING (true)
    WITH CHECK (true);

CREATE POLICY "Service role has full access to state"
    ON elliot_internal.state FOR ALL
    USING (true)
    WITH CHECK (true);

CREATE POLICY "Service role has full access to prefect_logs"
    ON elliot_internal.prefect_logs FOR ALL
    USING (true)
    WITH CHECK (true);

-- ============================================
-- 8. COMMENTS (Documentation)
-- ============================================

COMMENT ON SCHEMA elliot_internal IS 'Isolated schema for Elliot AI agent persistent memory and state';
COMMENT ON TABLE elliot_internal.memories IS 'Vector-enabled knowledge store for semantic search';
COMMENT ON TABLE elliot_internal.state IS 'Session and context persistence (key-value store)';
COMMENT ON TABLE elliot_internal.prefect_logs IS 'Workflow execution history mirror from Prefect';

-- ============================================
-- ROLLBACK (if needed)
-- ============================================
-- DROP SCHEMA elliot_internal CASCADE;

-- ============================================
-- VERIFICATION CHECKLIST
-- ============================================
-- [ ] Review table structures
-- [ ] Confirm vector dimensions (1536 for ada-002)
-- [ ] Check index strategy
-- [ ] Verify RLS policies
-- [ ] Test search_memories function
-- [ ] Run in Supabase SQL Editor
