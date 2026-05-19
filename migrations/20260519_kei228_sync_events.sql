-- KEI-228 (Linear) / Agency_OS-tfsl (bd) — K2 sync_events audit table + emit paths.
--
-- Builds on K1 (KEI-227 — bd_id column). Every cross-store change publishes
-- a single sync_events row tagged with origin. The K3 sync_orchestrator
-- (next PR) drains the table and writes to the OTHER two stores, with the
-- origin tag preventing echo-back loops.
--
-- Three emit paths (planned for K2):
--   1. Postgres → trigger on public.tasks INSERT/UPDATE (covered here)
--   2. Linear webhook → src/api/webhooks/linear.py insert (Python side)
--   3. bd-Dolt → DEFERRED to K2.5 (no clean post-bd hook; most bd ops
--      propagate to Postgres via tasks_cli.py and so are caught by trigger #1)

CREATE TABLE IF NOT EXISTS public.sync_events (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    origin          TEXT NOT NULL CHECK (origin IN ('bd', 'postgres', 'linear')),
    event_type      TEXT NOT NULL CHECK (event_type IN (
                        'create', 'update', 'close', 'reopen',
                        'priority_change', 'title_change'
                    )),
    task_id         TEXT NOT NULL,
    bd_id           TEXT,
    payload         JSONB NOT NULL,
    payload_hash    TEXT GENERATED ALWAYS AS (
                        encode(extensions.digest(payload::text, 'sha256'), 'hex')
                    ) STORED,
    processed       BOOLEAN NOT NULL DEFAULT FALSE,
    attempts        INT NOT NULL DEFAULT 0,
    last_attempt_at TIMESTAMPTZ,
    error_message   TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Drain index — K3 worker reads via this path.
CREATE INDEX IF NOT EXISTS idx_sync_events_unprocessed
    ON public.sync_events (created_at)
    WHERE processed = FALSE;

-- Dedupe partial index — at most one unprocessed event per (task, hash).
-- Same task can re-emit after processing; identical payloads collapse.
CREATE UNIQUE INDEX IF NOT EXISTS uq_sync_events_pending_dedupe
    ON public.sync_events (task_id, payload_hash)
    WHERE processed = FALSE;

COMMENT ON TABLE public.sync_events IS
    'KEI-228 — cross-store change events. Three origins (bd/postgres/linear); '
    'K3 sync_orchestrator drains and dispatches to the OTHER two stores with '
    'origin-tag loop prevention. Idempotency via (task_id, payload_hash) '
    'partial unique index.';

-- ---------------------------------------------------------------------------
-- Emit path 1: Postgres trigger on public.tasks.
-- ---------------------------------------------------------------------------
--
-- Fires on INSERT (event_type='create') and UPDATE (event_type='update' or
-- 'close' if NEW.status transitions to a done-shape state). Payload carries
-- the full row snapshot so K3 can replay without a re-select.
--
-- Coexists with the existing trg_tasks_completion_sync (KEI-74) — that one
-- writes to completion_sync_queue (legacy fan-out, to be removed in K3).
-- During the transition both fire; K3 will drop the old trigger.

CREATE OR REPLACE FUNCTION public.fn_emit_sync_event_postgres()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
DECLARE
    v_event_type TEXT;
    v_payload    JSONB;
BEGIN
    IF TG_OP = 'INSERT' THEN
        v_event_type := 'create';
    ELSIF TG_OP = 'UPDATE' THEN
        -- Closing transitions (status in done/cancelled) emit 'close';
        -- everything else is 'update'.
        IF NEW.status IN ('done', 'cancelled') AND NEW.status IS DISTINCT FROM OLD.status THEN
            v_event_type := 'close';
        ELSIF OLD.status IN ('done', 'cancelled') AND NEW.status NOT IN ('done', 'cancelled') THEN
            v_event_type := 'reopen';
        ELSIF NEW.priority IS DISTINCT FROM OLD.priority THEN
            v_event_type := 'priority_change';
        ELSIF NEW.title IS DISTINCT FROM OLD.title THEN
            v_event_type := 'title_change';
        ELSE
            v_event_type := 'update';
        END IF;
    ELSE
        RETURN NULL;
    END IF;

    v_payload := jsonb_build_object(
        'id', NEW.id,
        'bd_id', NEW.bd_id,
        'title', NEW.title,
        'status', NEW.status,
        'priority', NEW.priority,
        'linear_url', NEW.linear_url,
        'claimed_by', NEW.claimed_by,
        'tg_op', TG_OP
    );

    INSERT INTO public.sync_events (origin, event_type, task_id, bd_id, payload)
    VALUES ('postgres', v_event_type, NEW.id, NEW.bd_id, v_payload)
    ON CONFLICT (task_id, payload_hash) WHERE processed = FALSE DO NOTHING;

    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_tasks_emit_sync_events ON public.tasks;
CREATE TRIGGER trg_tasks_emit_sync_events
    AFTER INSERT OR UPDATE ON public.tasks
    FOR EACH ROW EXECUTE FUNCTION public.fn_emit_sync_event_postgres();

-- ---------------------------------------------------------------------------
-- Helper: emit from application code (used by Linear webhook + future bd path).
-- ---------------------------------------------------------------------------

CREATE OR REPLACE FUNCTION public.fn_emit_sync_event(
    p_origin TEXT,
    p_event_type TEXT,
    p_task_id TEXT,
    p_bd_id TEXT,
    p_payload JSONB
) RETURNS UUID LANGUAGE plpgsql AS $$
DECLARE
    v_id UUID;
BEGIN
    INSERT INTO public.sync_events (origin, event_type, task_id, bd_id, payload)
    VALUES (p_origin, p_event_type, p_task_id, p_bd_id, p_payload)
    ON CONFLICT (task_id, payload_hash) WHERE processed = FALSE DO NOTHING
    RETURNING id INTO v_id;
    RETURN v_id;
END;
$$;

COMMENT ON FUNCTION public.fn_emit_sync_event IS
    'KEI-228 — application-side helper to insert into sync_events with '
    'dedupe-on-pending semantics. Returns event id, or NULL if a duplicate '
    'pending event already exists for this (task_id, payload_hash).';
