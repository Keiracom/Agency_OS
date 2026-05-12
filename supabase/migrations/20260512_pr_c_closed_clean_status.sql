-- Migration: 20260512_pr_c_closed_clean_status.sql
-- Purpose: PR-C clean-close fix — formalise sessions.status='closed_clean'.
--          'closed_clean' = planned tmux kill / graceful restart, UUID
--          preserved so the next launcher call can `claude --resume <uuid>`.
--          'closed' is now reserved for callers that explicitly want NO
--          resume (no current caller); 'stuck' continues to mean unresponsive
--          (set by watchdog).
--
-- Schema note: sessions.status is TEXT with no CHECK constraint, so the new
-- value requires no DDL — this migration is documentation-only via COMMENT.
-- Re-runnable: COMMENT ON is idempotent.
--
-- Companions:
--   - .claude/hooks/session_store_stop.sh writes status='closed_clean'
--   - src/session_resumption/resolver.py filters status IN ('active', 'closed_clean')
--   - src/session_resumption/watchdog.py only touches status='active' rows
--
-- Created: 2026-05-12

COMMENT ON COLUMN sessions.status IS
    'active = open process; closed_clean = planned restart, UUID resumable; '
    'closed = explicit no-resume close; stuck = watchdog-reaped unresponsive';
