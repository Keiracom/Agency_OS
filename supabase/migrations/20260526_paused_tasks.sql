-- ============================================================================
-- 20260526_paused_tasks.sql
--
-- Ephemeral agent system §7 piece 2 — durable-wait state for the
-- decision_request/decision_response handshake. Filed under Agency_OS-70hb.
--
-- CANONICAL DESIGN — docs/architecture/ephemeral_agent_system_scoping.md
-- (PR #1140, MERGED 2026-05-25T05:19:04Z), §5 state-snapshot + §7 piece 2.
--
-- ROLE in the protocol (per §5):
--   1. Agent reaches decision-needed → writes decision_request envelope to
--      the deciding-party's inbox.
--   2. Agent emits paused_pending_decision event → dispatcher writes a row
--      HERE with task_ref + question + state_snapshot. Agent terminates.
--   3. Decision-giver answers via decision_response envelope; dispatcher
--      reads the row + spawns resume agent with state_snapshot.
--   4. Dispatcher marks the row resumed.
--   5. If no decision_response within TTL (7 days), TTL sweep marks row
--      expired + dead-letters to Elliot inbox.
--
-- COMPLEMENTS — Nova PR #1181 envelope_schema.py (decision_request +
-- decision_response + paused_pending_decision envelope types) + Nova
-- PR #1184 spawn_composer.py (resume-context branch consuming this state).
--
-- KEI-87 bypass: SET LOCAL agency_os.callsign = 'dave' required for
-- public-schema table creation (same pattern as 20260525_keiracom_*.sql).
-- ============================================================================

SET LOCAL agency_os.callsign = 'dave';

CREATE TABLE IF NOT EXISTS public.paused_tasks (
    -- Primary key + linkage
    task_ref           TEXT         NOT NULL PRIMARY KEY,
        -- bd ID, NATS subject, OR any caller-chosen unique identifier that
        -- the dispatcher uses to match decision_response → paused_tasks row

    -- Identity + routing
    callsign           TEXT         NOT NULL,
        -- The agent that paused (e.g. 'orion', 'atlas')
    decision_target    TEXT         NOT NULL,
        -- Who needs to decide (e.g. 'elliot', 'aiden', 'dave')

    -- Payload — typically <1KB per §5
    question           TEXT         NOT NULL,
        -- Human-readable decision question
    state_snapshot     JSONB        NOT NULL DEFAULT '{}'::jsonb,
        -- Interim state needed to resume: task_ref linkage + intermediate
        -- artifact file paths + per-§5 "whatever interim work it had
        -- completed"

    -- Lifecycle
    status             TEXT         NOT NULL DEFAULT 'active'
        CHECK (status IN ('active', 'resumed', 'expired', 'aborted')),
    created_at         TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    expires_at         TIMESTAMPTZ  NOT NULL,
        -- TTL boundary; 7-day default per §5 set by accessor at insert-time.
        -- TTL sweep job marks expired status + dead-letters to Elliot inbox.
    resumed_at         TIMESTAMPTZ,
        -- Set when dispatcher spawns resume agent on decision_response
    expired_at         TIMESTAMPTZ
        -- Set by the TTL sweep when status flips to expired
);

-- Lookup by task_ref is the dispatcher's hot path (resolve decision_response
-- target). Primary key already provides this, but add named index for clarity.

-- TTL sweep query: WHERE expires_at <= NOW() AND status = 'active'.
-- Partial index on active rows keeps the sweep cheap.
CREATE INDEX IF NOT EXISTS idx_paused_tasks_active_expires
    ON public.paused_tasks (expires_at)
    WHERE status = 'active';

-- "Show me orion's paused tasks" + "show me elliot's pending decisions" —
-- composite index for callsign + status + decision_target queries.
CREATE INDEX IF NOT EXISTS idx_paused_tasks_callsign_status
    ON public.paused_tasks (callsign, status);

CREATE INDEX IF NOT EXISTS idx_paused_tasks_decision_target_status
    ON public.paused_tasks (decision_target, status);
