-- Migration: 005_task_tracking.sql
-- Description: Create elliot_tasks table for spawned agent task tracking
-- Created: 2025-02-05

-- Create the task tracking table
CREATE TABLE IF NOT EXISTS elliot_tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    label TEXT NOT NULL,
    session_key TEXT NOT NULL UNIQUE,
    task_description TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'running' CHECK (status IN ('running', 'completed', 'failed', 'retry')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at TIMESTAMPTZ,
    retry_count INT NOT NULL DEFAULT 0,
    max_retries INT NOT NULL DEFAULT 2,
    output_summary TEXT,
    parent_session_key TEXT,
    last_checked_at TIMESTAMPTZ
);

-- Indexes for efficient lookups
CREATE INDEX IF NOT EXISTS idx_tasks_status ON elliot_tasks(status);
CREATE INDEX IF NOT EXISTS idx_tasks_session_key ON elliot_tasks(session_key);
CREATE INDEX IF NOT EXISTS idx_tasks_label ON elliot_tasks(label);
CREATE INDEX IF NOT EXISTS idx_tasks_created_at ON elliot_tasks(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_tasks_running ON elliot_tasks(status, created_at) WHERE status = 'running';

-- Enable RLS
ALTER TABLE elliot_tasks ENABLE ROW LEVEL SECURITY;

-- Allow service role full access
CREATE POLICY "Service role has full access to tasks"
    ON elliot_tasks
    FOR ALL
    USING (true)
    WITH CHECK (true);

-- Comments
COMMENT ON TABLE elliot_tasks IS 'Tracks spawned agent tasks for monitoring, retry, and alerting';
COMMENT ON COLUMN elliot_tasks.label IS 'Human-readable task label (e.g., research-apollo, build-poc)';
COMMENT ON COLUMN elliot_tasks.session_key IS 'Clawdbot session key for the spawned agent';
COMMENT ON COLUMN elliot_tasks.task_description IS 'Full description of what was requested';
COMMENT ON COLUMN elliot_tasks.status IS 'running, completed, failed, or retry';
COMMENT ON COLUMN elliot_tasks.retry_count IS 'Number of times this task has been retried';
COMMENT ON COLUMN elliot_tasks.max_retries IS 'Maximum retry attempts before marking permanently failed';
COMMENT ON COLUMN elliot_tasks.output_summary IS 'Summary of task output/result';
COMMENT ON COLUMN elliot_tasks.parent_session_key IS 'Session key of the agent that spawned this task';
COMMENT ON COLUMN elliot_tasks.last_checked_at IS 'Last time heartbeat checked this task';
