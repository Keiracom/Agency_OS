-- Migration: 006_action_engine_updates.sql
-- Description: Extend signoff_queue for action engine (new action types, statuses, columns)
-- Created: 2025-02-05

-- 1. Drop and recreate the action_type constraint to add new types
ALTER TABLE elliot_signoff_queue DROP CONSTRAINT IF EXISTS elliot_signoff_queue_action_type_check;
ALTER TABLE elliot_signoff_queue ADD CONSTRAINT elliot_signoff_queue_action_type_check 
    CHECK (action_type IN ('evaluate_tool', 'build_poc', 'research', 'audit', 'analyze'));

-- 2. Drop and recreate the status constraint to add new statuses
ALTER TABLE elliot_signoff_queue DROP CONSTRAINT IF EXISTS elliot_signoff_queue_status_check;
ALTER TABLE elliot_signoff_queue ADD CONSTRAINT elliot_signoff_queue_status_check 
    CHECK (status IN ('pending', 'approved', 'rejected', 'executing', 'completed', 'failed'));

-- 3. Drop the summary length constraint (we need longer summaries for rich context)
ALTER TABLE elliot_signoff_queue DROP CONSTRAINT IF EXISTS elliot_signoff_queue_summary_check;
ALTER TABLE elliot_signoff_queue ADD CONSTRAINT elliot_signoff_queue_summary_check
    CHECK (char_length(summary) <= 2000);

-- 4. Add updated_at column if not exists
ALTER TABLE elliot_signoff_queue 
    ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ;

-- 5. Add task_id column to track spawned agent
ALTER TABLE elliot_signoff_queue 
    ADD COLUMN IF NOT EXISTS task_id UUID REFERENCES elliot_tasks(id) ON DELETE SET NULL;

-- 6. Add session_key column for direct agent reference
ALTER TABLE elliot_signoff_queue 
    ADD COLUMN IF NOT EXISTS session_key TEXT;

-- 7. Add rejection_reason column
ALTER TABLE elliot_signoff_queue 
    ADD COLUMN IF NOT EXISTS rejection_reason TEXT;

-- 8. Create index on status for efficient queue lookups
CREATE INDEX IF NOT EXISTS idx_signoff_queue_status_created 
    ON elliot_signoff_queue(status, created_at DESC);

-- 9. Add applied_at column to elliot_knowledge if not exists
ALTER TABLE elliot_knowledge
    ADD COLUMN IF NOT EXISTS applied_at TIMESTAMPTZ;

-- Update comments
COMMENT ON COLUMN elliot_signoff_queue.action_type IS 'Type of action: evaluate_tool, build_poc, research, audit, analyze';
COMMENT ON COLUMN elliot_signoff_queue.status IS 'Status: pending, approved, rejected, executing, completed, failed';
COMMENT ON COLUMN elliot_signoff_queue.task_id IS 'Reference to spawned agent task in elliot_tasks';
COMMENT ON COLUMN elliot_signoff_queue.session_key IS 'Clawdbot session key of spawned agent';
COMMENT ON COLUMN elliot_signoff_queue.rejection_reason IS 'Reason for rejection if declined';
COMMENT ON COLUMN elliot_knowledge.applied_at IS 'When this knowledge was applied via action engine';
