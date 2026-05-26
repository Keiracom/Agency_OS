-- ============================================================================
-- 20260526_keiracom_paused_tasks.sql
--
-- Phase A8 §7 piece 2 — paused_tasks Postgres table + migration.
-- bd: Agency_OS-70hb
--
-- Per PR #1140 §5 (state-snapshot semantics) + §7 piece 2:
--   "paused_tasks Postgres table + migration — see §5 state-snapshot.
--    ~50 LoC SQL + ~100 LoC accessor. P1."
--
-- Closes the Scout #1171 audit finding: canonical citation referenced this
-- table at PR #1140 line 102 + 124 + 154 but the migration was never filed
-- post-merge. Verdict (c): deferred-to-Phase-A8 build.
--
-- Schema purpose: durable wait-state for ephemeral agents that pause mid-task
-- awaiting a `decision_response` envelope. Agent writes a row before
-- terminating; dispatcher reads on `decision_response` arrival + spawns a
-- resume agent with the persisted state_snapshot. Empty <1KB JSON state per
-- §5 carries (a) original task_ref, (b) the question asked, (c) interim
-- artifact paths so resume reconstructs the pre-pause context.
--
-- Tenant scoping: FK to keiracom_tenants(tenant_id) ON DELETE CASCADE.
-- Matches the PR #1137 metering + PR #1173 budgets + PR #1185 atomization
-- per-tenant pattern.
--
-- TTL: per §5 "Decision never lands: TTL on the paused_tasks row (e.g. 7
-- days) → automatic cleanup + dead-letter to Elliot." Caller sets
-- expires_at; the accessor's expire_old() method marks paused rows past
-- expiry as `expired` for downstream dispatcher cleanup.
--
-- KEI-87 bypass: SET LOCAL agency_os.callsign = 'dave' required because
-- this migration creates a public-schema table — same pattern as
-- 20260525_keiracom_tenant_metering.sql + 20260526_keiracom_tenant_budgets.sql.
-- ============================================================================

SET LOCAL agency_os.callsign = 'dave';

CREATE TABLE IF NOT EXISTS public.keiracom_paused_tasks (
    paused_task_id         UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id              UUID         NOT NULL
        REFERENCES public.keiracom_tenants(tenant_id) ON DELETE CASCADE,
    callsign               TEXT         NOT NULL,
    task_ref               TEXT         NOT NULL,
    question               TEXT         NOT NULL,
    state_snapshot         JSONB        NOT NULL DEFAULT '{}'::jsonb,
    paused_at              TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    expires_at             TIMESTAMPTZ  NOT NULL,
    status                 TEXT         NOT NULL DEFAULT 'paused'
        CHECK (status IN ('paused', 'resolved', 'aborted', 'expired')),
    resolved_at            TIMESTAMPTZ,
    decision_response_ref  TEXT,
    updated_at             TIMESTAMPTZ  NOT NULL DEFAULT NOW(),

    CHECK (expires_at > paused_at),
    CHECK ((status = 'resolved') = (resolved_at IS NOT NULL))
);

-- TTL sweep index: dispatcher scans for paused rows past expires_at to mark
-- them 'expired' + dead-letter. Partial index keeps the working set small.
CREATE INDEX idx_keiracom_paused_tasks_tenant_expires
    ON public.keiracom_paused_tasks (tenant_id, expires_at)
    WHERE status = 'paused';

-- task_ref lookup index: dispatcher matches incoming decision_response
-- envelopes to a paused row by (tenant_id, task_ref).
CREATE INDEX idx_keiracom_paused_tasks_task_ref
    ON public.keiracom_paused_tasks (tenant_id, task_ref);

-- Per-callsign paused-set query: orchestrator surfaces "agent X has Y paused
-- tasks awaiting decision" inventories.
CREATE INDEX idx_keiracom_paused_tasks_callsign
    ON public.keiracom_paused_tasks (tenant_id, callsign, paused_at)
    WHERE status = 'paused';

-- updated_at maintenance trigger (mirrors PR #1185 atomization pilot pattern).
CREATE OR REPLACE FUNCTION public.keiracom_paused_tasks_updated_at()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END
$$;

DROP TRIGGER IF EXISTS trg_keiracom_paused_tasks_updated_at
    ON public.keiracom_paused_tasks;
CREATE TRIGGER trg_keiracom_paused_tasks_updated_at
    BEFORE UPDATE ON public.keiracom_paused_tasks
    FOR EACH ROW EXECUTE FUNCTION public.keiracom_paused_tasks_updated_at();
