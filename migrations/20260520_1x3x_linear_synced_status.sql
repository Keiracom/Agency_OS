-- Agency_OS-1x3x — Part 4: one-way Supabase→Linear push watermark.
--
-- Adds public.tasks.linear_synced_status — the watermark the controlled
-- one-way push (scripts/orchestrator/linear_oneway_push.py) uses to record
-- which status value it last successfully propagated to Linear. The push
-- reads (status, linear_synced_status); a terminal transition is pending
-- when they diverge and either side is a terminal status. After a
-- successful Linear write the push sets linear_synced_status = status.
-- This makes the push idempotent: a re-run sees them equal and skips.
--
-- The emit trigger fn_emit_sync_event_postgres is re-defined to SKIP
-- emission when an UPDATE touches ONLY linear_synced_status. The push's
-- watermark write is bookkeeping, not a cross-store change — emitting a
-- sync_event for it would echo the push back into the sync pipeline as a
-- Supabase change (the exact loop requirement c forbids).

ALTER TABLE public.tasks
    ADD COLUMN IF NOT EXISTS linear_synced_status TEXT;

COMMENT ON COLUMN public.tasks.linear_synced_status IS
    'Agency_OS-1x3x — one-way push watermark. Last task status value the '
    'controlled Supabase→Linear push successfully propagated to Linear. '
    'NULL = never pushed. Written ONLY by linear_oneway_push.py.';

-- Re-definition of the KEI-228 emit trigger with the watermark guard.
-- Body is identical to migrations/20260519_kei228_sync_events.sql except
-- for the bookkeeping-skip guard at the top of the UPDATE branch.
CREATE OR REPLACE FUNCTION public.fn_emit_sync_event_postgres()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
DECLARE
    v_event_type TEXT;
    v_payload    JSONB;
BEGIN
    IF TG_OP = 'INSERT' THEN
        v_event_type := 'create';
    ELSIF TG_OP = 'UPDATE' THEN
        -- Agency_OS-1x3x watermark guard: an UPDATE that changes ONLY
        -- linear_synced_status (status/title/priority all unchanged) is the
        -- one-way push recording its own progress. Emit nothing — otherwise
        -- the push's watermark write echoes back as a Supabase sync_event.
        IF NEW.status IS NOT DISTINCT FROM OLD.status
           AND NEW.title IS NOT DISTINCT FROM OLD.title
           AND NEW.priority IS NOT DISTINCT FROM OLD.priority
           AND NEW.linear_synced_status IS DISTINCT FROM OLD.linear_synced_status THEN
            RETURN NEW;
        END IF;
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

-- Baseline backfill: declare every existing row's current status as
-- already-synced, so the push starts from a clean baseline and acts only
-- on FUTURE terminal transitions (not a one-time burst of redundant
-- re-pushes of already-completed KEIs). The watermark guard above absorbs
-- this UPDATE — no sync_events emitted.
UPDATE public.tasks
   SET linear_synced_status = status
 WHERE status IS NOT NULL;
