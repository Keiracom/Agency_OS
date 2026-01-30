-- Migration: 004_signoff_queue.sql
-- Description: Create elliot_signoff_queue table for knowledge sign-off workflow
-- Created: 2025-02-05

-- Create the signoff queue table
CREATE TABLE IF NOT EXISTS elliot_signoff_queue (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    knowledge_id UUID NOT NULL REFERENCES elliot_knowledge(id) ON DELETE CASCADE,
    action_type TEXT NOT NULL CHECK (action_type IN ('evaluate_tool', 'build_poc', 'research')),
    title TEXT NOT NULL,
    summary TEXT NOT NULL CHECK (char_length(summary) <= 200),
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'approved', 'rejected')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    decided_at TIMESTAMPTZ
);

-- Create index for efficient pending queue lookups
CREATE INDEX IF NOT EXISTS idx_signoff_queue_status ON elliot_signoff_queue(status);
CREATE INDEX IF NOT EXISTS idx_signoff_queue_knowledge_id ON elliot_signoff_queue(knowledge_id);
CREATE INDEX IF NOT EXISTS idx_signoff_queue_created_at ON elliot_signoff_queue(created_at DESC);

-- Add RLS policies
ALTER TABLE elliot_signoff_queue ENABLE ROW LEVEL SECURITY;

-- Allow service role full access
CREATE POLICY "Service role has full access to signoff_queue"
    ON elliot_signoff_queue
    FOR ALL
    USING (true)
    WITH CHECK (true);

COMMENT ON TABLE elliot_signoff_queue IS 'Queue for knowledge items requiring human sign-off before action';
COMMENT ON COLUMN elliot_signoff_queue.action_type IS 'Type of action: evaluate_tool, build_poc, or research';
COMMENT ON COLUMN elliot_signoff_queue.summary IS 'Brief summary for notification display (max 200 chars)';
