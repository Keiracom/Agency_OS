-- Migration: 20260511_drevon_session_store.sql
-- Purpose: Drevon PR-A — session store foundation (Dave directive 2026-05-11,
--          Elliot dispatch ts 1778540XXX). 5-table audit + replay store for
--          every agent action. Unblocks PR-B (skill-gen), PR-C (UUID resume),
--          PR-D (dynamic CLAUDE.md).
--
-- Tables:
--   sessions    — one row per Claude Code process lifetime (includes session_uuid
--                 for PR-C resumption)
--   messages    — user/assistant messages within a session
--   turns       — atomic assistant turn (one user msg → tool calls → response)
--   turn_logs   — individual tool invocations within a turn
--   turn_files  — files created/modified/read during a turn_log
--
-- Conventions follow vendor_usage_log precedent (PR #649):
--   - UUID primary keys, gen_random_uuid()
--   - TIMESTAMPTZ for all timestamps
--   - Soft-delete via deleted_at
--   - Partial indexes filtering deleted_at IS NULL
--   - RLS enabled; platform admin (CRUD) + client member (read) policies
--
-- No retroactive backfill (Elliot explicit). New sessions only.
-- Created: 2026-05-11

-- ─────────────────────────────────────────────────────────────────────────────
-- Table 1: sessions — Claude Code process lifetime
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Identity
    callsign TEXT NOT NULL,                                  -- 'elliot'|'aiden'|'max'|'atlas'|'orion'|'scout'
    session_uuid TEXT,                                       -- Claude Code's --session-id (PR-C resumption key)

    -- Context
    working_directory TEXT NOT NULL,                         -- worktree path
    tmux_session TEXT,                                       -- e.g. 'aiden', 'orion' — nullable for non-tmux sessions

    -- Lifecycle
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    ended_at TIMESTAMPTZ,                                    -- NULL = active session
    status TEXT NOT NULL DEFAULT 'active',                   -- 'active'|'closed'|'stuck' (text enum, no PG enum coupling)

    -- Metadata
    model_id TEXT,                                           -- e.g. 'claude-opus-4-7' captured at session start
    extra JSONB NOT NULL DEFAULT '{}'::jsonb,                -- agent-specific context

    -- Soft delete
    deleted_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_sessions_callsign_started
    ON sessions(callsign, started_at DESC) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_sessions_session_uuid
    ON sessions(session_uuid) WHERE session_uuid IS NOT NULL AND deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_sessions_active
    ON sessions(callsign) WHERE ended_at IS NULL AND deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_sessions_status
    ON sessions(status) WHERE deleted_at IS NULL;

ALTER TABLE sessions ENABLE ROW LEVEL SECURITY;

CREATE POLICY sessions_platform_admin ON sessions
    FOR ALL TO authenticated
    USING (EXISTS (SELECT 1 FROM users u WHERE u.id = auth.uid() AND u.is_platform_admin = true));

-- ─────────────────────────────────────────────────────────────────────────────
-- Table 2: messages — user/assistant messages within a session
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    session_id UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,

    -- Role + ordering
    role TEXT NOT NULL,                                      -- 'user'|'assistant'|'system'
    message_index INTEGER NOT NULL,                          -- 0-based ordering within session
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Content (text optional — large transcripts may store hash only)
    content_hash TEXT,                                       -- sha256 of full content
    content_text TEXT,                                       -- truncated or full body — caller's choice
    content_bytes INTEGER,                                   -- byte count of full content

    -- Soft delete
    deleted_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_messages_session_idx
    ON messages(session_id, message_index) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_messages_session_ts
    ON messages(session_id, timestamp) WHERE deleted_at IS NULL;

ALTER TABLE messages ENABLE ROW LEVEL SECURITY;

CREATE POLICY messages_platform_admin ON messages
    FOR ALL TO authenticated
    USING (EXISTS (SELECT 1 FROM users u WHERE u.id = auth.uid() AND u.is_platform_admin = true));

-- ─────────────────────────────────────────────────────────────────────────────
-- Table 3: turns — atomic assistant turn (one user msg → tool calls → response)
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS turns (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    session_id UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    trigger_message_id UUID REFERENCES messages(id) ON DELETE SET NULL,

    -- Ordering
    turn_index INTEGER NOT NULL,                             -- 0-based within session

    -- Lifecycle
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    status TEXT NOT NULL DEFAULT 'in_progress',              -- 'in_progress'|'completed'|'error'

    -- Cost (per-turn rollup written by Stop hook)
    input_tokens INTEGER,
    output_tokens INTEGER,
    cost_aud DECIMAL(10, 6),

    -- Soft delete
    deleted_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_turns_session_idx
    ON turns(session_id, turn_index) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_turns_session_started
    ON turns(session_id, started_at DESC) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_turns_status
    ON turns(status) WHERE deleted_at IS NULL;

ALTER TABLE turns ENABLE ROW LEVEL SECURITY;

CREATE POLICY turns_platform_admin ON turns
    FOR ALL TO authenticated
    USING (EXISTS (SELECT 1 FROM users u WHERE u.id = auth.uid() AND u.is_platform_admin = true));

-- ─────────────────────────────────────────────────────────────────────────────
-- Table 4: turn_logs — individual tool invocations within a turn
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS turn_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    turn_id UUID NOT NULL REFERENCES turns(id) ON DELETE CASCADE,

    -- Tool invocation
    tool_name TEXT NOT NULL,                                 -- 'Bash'|'Read'|'Edit'|'Write'|...|'Agent'|'mcp__...'
    tool_args_json JSONB NOT NULL DEFAULT '{}'::jsonb,       -- captured args (may be redacted/truncated)
    tool_args_bytes INTEGER,                                 -- original arg-payload byte count

    -- Result
    tool_result_summary TEXT,                                -- first N chars or hash for evidence
    tool_result_bytes INTEGER,                               -- result-payload byte count
    exit_status TEXT NOT NULL DEFAULT 'success',             -- 'success'|'error'|'denied'|'timeout'
    error_message TEXT,                                      -- non-null when exit_status != 'success'

    -- Lifecycle
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    duration_ms INTEGER,

    -- Soft delete
    deleted_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_turn_logs_turn_started
    ON turn_logs(turn_id, started_at) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_turn_logs_tool_name
    ON turn_logs(tool_name) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_turn_logs_exit_status
    ON turn_logs(exit_status) WHERE deleted_at IS NULL;

ALTER TABLE turn_logs ENABLE ROW LEVEL SECURITY;

CREATE POLICY turn_logs_platform_admin ON turn_logs
    FOR ALL TO authenticated
    USING (EXISTS (SELECT 1 FROM users u WHERE u.id = auth.uid() AND u.is_platform_admin = true));

-- ─────────────────────────────────────────────────────────────────────────────
-- Table 5: turn_files — files created/modified/read during a turn_log
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS turn_files (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    turn_log_id UUID NOT NULL REFERENCES turn_logs(id) ON DELETE CASCADE,

    -- File identity
    file_path TEXT NOT NULL,                                 -- absolute path
    operation TEXT NOT NULL,                                 -- 'read'|'write'|'edit'|'delete'|'create'

    -- Change tracking
    bytes_written INTEGER,                                   -- write/edit/create only
    bytes_read INTEGER,                                      -- read only
    content_hash TEXT,                                       -- sha256 of post-operation content (write/edit)
    lines_added INTEGER,                                     -- edit/write only
    lines_removed INTEGER,                                   -- edit only

    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Soft delete
    deleted_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_turn_files_turn_log
    ON turn_files(turn_log_id) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_turn_files_path
    ON turn_files(file_path) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_turn_files_operation
    ON turn_files(operation) WHERE deleted_at IS NULL;

ALTER TABLE turn_files ENABLE ROW LEVEL SECURITY;

CREATE POLICY turn_files_platform_admin ON turn_files
    FOR ALL TO authenticated
    USING (EXISTS (SELECT 1 FROM users u WHERE u.id = auth.uid() AND u.is_platform_admin = true));

-- ─────────────────────────────────────────────────────────────────────────────
-- Updated-at trigger (mirrors the agency-wide pattern)
-- ─────────────────────────────────────────────────────────────────────────────
-- Not adding updated_at columns by default — these tables are append-mostly.
-- If a future migration adds updated_at, follow the trigger pattern from
-- ceo_memory / agent_memories.

COMMENT ON TABLE sessions IS 'Drevon PR-A — one row per Claude Code process lifetime';
COMMENT ON TABLE messages IS 'Drevon PR-A — user/assistant messages within a session';
COMMENT ON TABLE turns IS 'Drevon PR-A — atomic assistant turn (one user msg → tool calls → response)';
COMMENT ON TABLE turn_logs IS 'Drevon PR-A — individual tool invocations within a turn';
COMMENT ON TABLE turn_files IS 'Drevon PR-A — files created/modified/read during a turn_log';
