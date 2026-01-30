-- Elliot Persistent Learning System - Phase 1.5
-- Migration: 002_application_tracking.sql
-- Purpose: Add application enforcement and knowledge decay
-- Created: 2025-01-30

-- ============================================
-- Schema Updates: Add application context column
-- ============================================

-- Add applied_context column if it doesn't exist
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'elliot_knowledge' AND column_name = 'applied_context'
    ) THEN
        ALTER TABLE elliot_knowledge ADD COLUMN applied_context TEXT;
        COMMENT ON COLUMN elliot_knowledge.applied_context IS 'How this knowledge was applied (user-provided context)';
    END IF;
END $$;

-- Rename relevance_decay to decay_score for clarity (if not already renamed)
-- Note: We'll use relevance_decay as-is since it already exists with same semantics
COMMENT ON COLUMN elliot_knowledge.relevance_decay IS 'Decay score: starts at 1.0, decreases by 0.1 daily if not applied. Pruned below 0.3.';

-- Index for efficient decay queries
CREATE INDEX IF NOT EXISTS idx_knowledge_decay_score 
    ON elliot_knowledge(relevance_decay) 
    WHERE deleted_at IS NULL AND applied = FALSE;

-- Index for unapplied knowledge queries
CREATE INDEX IF NOT EXISTS idx_knowledge_unapplied 
    ON elliot_knowledge(learned_at DESC) 
    WHERE deleted_at IS NULL AND applied = FALSE;

-- ============================================
-- Function: decay_unused_knowledge
-- Purpose: Reduce decay_score by 0.1 for all unapplied knowledge
-- Returns: Number of rows affected
-- ============================================
CREATE OR REPLACE FUNCTION decay_unused_knowledge()
RETURNS TABLE (
    decayed_count INTEGER,
    min_score_after FLOAT,
    max_age_days INTEGER
) AS $$
DECLARE
    affected INTEGER;
    min_score FLOAT;
    max_age INTEGER;
BEGIN
    -- Decay all unapplied knowledge by 0.1
    WITH updated AS (
        UPDATE elliot_knowledge
        SET relevance_decay = GREATEST(0, relevance_decay - 0.1)
        WHERE deleted_at IS NULL
          AND applied = FALSE
          AND relevance_decay > 0
        RETURNING relevance_decay, learned_at
    )
    SELECT 
        COUNT(*)::INTEGER,
        MIN(relevance_decay),
        MAX(EXTRACT(DAY FROM NOW() - learned_at))::INTEGER
    INTO affected, min_score, max_age
    FROM updated;

    RETURN QUERY SELECT 
        COALESCE(affected, 0),
        COALESCE(min_score, 0.0)::FLOAT,
        COALESCE(max_age, 0);
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION decay_unused_knowledge() IS 
    'Daily job: reduces decay score by 0.1 for all unapplied knowledge. Call daily after learning scrape.';

-- ============================================
-- Function: mark_knowledge_applied
-- Purpose: Mark knowledge as applied with context, reset decay
-- Returns: The updated knowledge record
-- ============================================
CREATE OR REPLACE FUNCTION mark_knowledge_applied(
    knowledge_id UUID,
    context TEXT
)
RETURNS TABLE (
    id UUID,
    content TEXT,
    applied_at TIMESTAMPTZ,
    applied_context TEXT,
    relevance_decay FLOAT
) AS $$
BEGIN
    RETURN QUERY
    UPDATE elliot_knowledge
    SET 
        applied = TRUE,
        applied_at = NOW(),
        applied_context = context,
        relevance_decay = 1.0  -- Reset decay on application
    WHERE elliot_knowledge.id = knowledge_id
      AND deleted_at IS NULL
    RETURNING 
        elliot_knowledge.id,
        elliot_knowledge.content,
        elliot_knowledge.applied_at,
        elliot_knowledge.applied_context,
        elliot_knowledge.relevance_decay;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION mark_knowledge_applied(UUID, TEXT) IS 
    'Mark knowledge as applied with context. Resets decay score to 1.0.';

-- ============================================
-- Function: get_unapplied_knowledge
-- Purpose: Get knowledge that hasn't been applied yet (for session prompts)
-- ============================================
CREATE OR REPLACE FUNCTION get_unapplied_knowledge(
    max_items INT DEFAULT 5,
    min_decay_score FLOAT DEFAULT 0.3
)
RETURNS TABLE (
    id UUID,
    category TEXT,
    content TEXT,
    summary TEXT,
    source_type TEXT,
    learned_at TIMESTAMPTZ,
    relevance_decay FLOAT,
    days_old INTEGER
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        k.id,
        k.category,
        k.content,
        k.summary,
        k.source_type,
        k.learned_at,
        k.relevance_decay,
        EXTRACT(DAY FROM NOW() - k.learned_at)::INTEGER AS days_old
    FROM elliot_knowledge k
    WHERE 
        k.deleted_at IS NULL
        AND k.applied = FALSE
        AND k.relevance_decay >= min_decay_score
    ORDER BY 
        k.relevance_decay DESC,  -- Prioritize higher decay scores (newer/more relevant)
        k.confidence_score DESC,
        k.learned_at DESC
    LIMIT max_items;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION get_unapplied_knowledge(INT, FLOAT) IS 
    'Get unapplied knowledge items for session prompts. Prioritizes by decay score and confidence.';

-- ============================================
-- Function: prune_stale_knowledge
-- Purpose: Soft-delete knowledge with decay below threshold
-- ============================================
CREATE OR REPLACE FUNCTION prune_stale_knowledge(
    min_score FLOAT DEFAULT 0.3
)
RETURNS TABLE (
    pruned_count INTEGER,
    pruned_ids UUID[]
) AS $$
DECLARE
    affected INTEGER;
    deleted_ids UUID[];
BEGIN
    -- Soft delete stale unapplied knowledge
    WITH deleted AS (
        UPDATE elliot_knowledge
        SET deleted_at = NOW()
        WHERE deleted_at IS NULL
          AND applied = FALSE
          AND relevance_decay < min_score
        RETURNING id
    )
    SELECT COUNT(*)::INTEGER, ARRAY_AGG(id)
    INTO affected, deleted_ids
    FROM deleted;

    RETURN QUERY SELECT 
        COALESCE(affected, 0),
        COALESCE(deleted_ids, ARRAY[]::UUID[]);
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION prune_stale_knowledge(FLOAT) IS 
    'Soft-delete unapplied knowledge with decay score below threshold (default 0.3).';

-- ============================================
-- Function: get_session_learning_stats
-- Purpose: Get summary stats for session reports
-- ============================================
CREATE OR REPLACE FUNCTION get_session_learning_stats(
    hours_back INT DEFAULT 24
)
RETURNS TABLE (
    total_knowledge INTEGER,
    applied_count INTEGER,
    unapplied_count INTEGER,
    recently_added INTEGER,
    recently_applied INTEGER,
    avg_decay_score FLOAT,
    at_risk_count INTEGER  -- Below 0.5 decay, not yet applied
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        COUNT(*)::INTEGER AS total_knowledge,
        COUNT(*) FILTER (WHERE applied = TRUE)::INTEGER AS applied_count,
        COUNT(*) FILTER (WHERE applied = FALSE)::INTEGER AS unapplied_count,
        COUNT(*) FILTER (WHERE learned_at > NOW() - (hours_back || ' hours')::INTERVAL)::INTEGER AS recently_added,
        COUNT(*) FILTER (WHERE applied_at > NOW() - (hours_back || ' hours')::INTERVAL)::INTEGER AS recently_applied,
        COALESCE(AVG(relevance_decay) FILTER (WHERE applied = FALSE), 0)::FLOAT AS avg_decay_score,
        COUNT(*) FILTER (WHERE applied = FALSE AND relevance_decay < 0.5)::INTEGER AS at_risk_count
    FROM elliot_knowledge
    WHERE deleted_at IS NULL;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION get_session_learning_stats(INT) IS 
    'Get learning statistics for session reports.';
