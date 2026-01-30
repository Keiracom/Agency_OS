-- Migration: Add scoring infrastructure to elliot_knowledge table
-- Version: 002
-- Date: 2025-02-02

-- Add scoring columns to elliot_knowledge
ALTER TABLE elliot_knowledge
ADD COLUMN IF NOT EXISTS scored BOOLEAN DEFAULT false,
ADD COLUMN IF NOT EXISTS business_score INTEGER CHECK (business_score >= 0 AND business_score <= 100),
ADD COLUMN IF NOT EXISTS learning_score INTEGER CHECK (learning_score >= 0 AND learning_score <= 100),
ADD COLUMN IF NOT EXISTS final_score INTEGER CHECK (final_score >= 0 AND final_score <= 100),
ADD COLUMN IF NOT EXISTS score_reasoning TEXT,
ADD COLUMN IF NOT EXISTS action_type TEXT,
ADD COLUMN IF NOT EXISTS scored_at TIMESTAMPTZ;

-- Create partial index on unscored rows for fast queries
CREATE INDEX IF NOT EXISTS idx_elliot_knowledge_unscored 
ON elliot_knowledge (scored) 
WHERE scored = false;

-- Create index on final_score for sorting/filtering scored content
CREATE INDEX IF NOT EXISTS idx_elliot_knowledge_final_score 
ON elliot_knowledge (final_score DESC) 
WHERE scored = true;

COMMENT ON COLUMN elliot_knowledge.scored IS 'Whether this knowledge entry has been scored';
COMMENT ON COLUMN elliot_knowledge.business_score IS 'Business relevance score (0-100)';
COMMENT ON COLUMN elliot_knowledge.learning_score IS 'Learning/insight value score (0-100)';
COMMENT ON COLUMN elliot_knowledge.final_score IS 'Combined final score (0-100)';
COMMENT ON COLUMN elliot_knowledge.score_reasoning IS 'LLM reasoning for the assigned scores';
COMMENT ON COLUMN elliot_knowledge.action_type IS 'Recommended action (archive, summarize, keep, etc.)';
COMMENT ON COLUMN elliot_knowledge.scored_at IS 'When this entry was scored';
