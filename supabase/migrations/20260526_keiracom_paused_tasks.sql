-- ============================================================================
-- 20260526_keiracom_paused_tasks.sql
--
-- Phase A8 ephemeral-agent paused-task persistence (PR #1140 §5 + §7 piece #2).
-- bd: Agency_OS-tjni
--
-- Persists state-snapshots from `paused_pending_decision` envelopes (per my
-- PR #1181 envelope schema, Agency_OS-wmbv) so a future resume-spawn agent
-- can pick up where the paused agent left off. The dispatcher (PR #1188,
-- Agency_OS-8416) is the writer; resume-spawn logic is the reader.
--
-- CANONICAL DESIGN — docs/architecture/ephemeral_agent_system_scoping.md
-- §5 (state-snapshot semantics) + §7 piece #2 (this work).
--
-- Schema decisions:
--   - PRIMARY KEY (task_ref) — opaque correlation key from the envelope;
--     unique by design (one paused row per task at a time).
--   - deadline_at = paused_at + 7 days (§5 line 102: "TTL on the row e.g.
--     7 days → automatic cleanup + dead-letter to Elliot"). The sweep is
--     query-driven via iter_expired() in the accessor — no native PG TTL.
--   - state CHECK ('pending','resumed','dead_lettered') — explicit lifecycle.
--   - Idempotent re-insert via ON CONFLICT semantics (dispatcher handles
--     this via insert_from_envelope() — see src/relay/paused_tasks.py).
--   - No FK to keiracom_tenants — paused-tasks are per-callsign-internal
--     (orchestrator-level dead-letter), not per-tenant. Sibling concept
--     to keiracom_atom_store (per-tenant) but different scope per §5.
--
-- KEI-87 bypass: SET LOCAL agency_os.callsign = 'dave' — same pattern as
-- 20260526_keiracom_tenant_budgets.sql + 20260525_keiracom_tenants.sql.
-- ============================================================================

SET LOCAL agency_os.callsign = 'dave';

CREATE TABLE IF NOT EXISTS public.keiracom_paused_tasks (
    task_ref       TEXT         PRIMARY KEY
        CHECK (length(task_ref) > 0),
    callsign       TEXT         NOT NULL
        CHECK (length(callsign) > 0),
    paused_at      TIMESTAMPTZ  NOT NULL,
    deadline_at    TIMESTAMPTZ  NOT NULL
        CHECK (deadline_at > paused_at),
    interim_state  JSONB        NOT NULL DEFAULT '{}'::jsonb,
    question       TEXT,
    options        JSONB,
    state          TEXT         NOT NULL DEFAULT 'pending'
        CHECK (state IN ('pending','resumed','dead_lettered')),
    created_at     TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at     TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

-- Sweep query: WHERE state = 'pending' AND deadline_at < now() — partial
-- index on the pending-only subset keeps the dead-letter scan cheap.
CREATE INDEX IF NOT EXISTS idx_keiracom_paused_tasks_pending_deadline
    ON public.keiracom_paused_tasks (deadline_at)
    WHERE state = 'pending';

-- Per-callsign listing (operator + ops queries): "what is callsign X
-- waiting on?"
CREATE INDEX IF NOT EXISTS idx_keiracom_paused_tasks_callsign
    ON public.keiracom_paused_tasks (callsign);

-- Trigger to refresh updated_at on every UPDATE so the column tracks the
-- last state change even when the writer forgets to set it explicitly.
CREATE OR REPLACE FUNCTION public.keiracom_paused_tasks_set_updated_at()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_keiracom_paused_tasks_updated_at
    ON public.keiracom_paused_tasks;

CREATE TRIGGER trg_keiracom_paused_tasks_updated_at
    BEFORE UPDATE ON public.keiracom_paused_tasks
    FOR EACH ROW
    EXECUTE FUNCTION public.keiracom_paused_tasks_set_updated_at();
