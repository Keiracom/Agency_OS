-- Agency_OS-j8eu — GAP-A: one-way push KEI-creation opt-in flag.
--
-- Adds public.tasks.linear_create_pending — the OPT-IN marker the one-way
-- push (scripts/orchestrator/linear_oneway_push.py) uses to decide which
-- title-less rows should get a Linear issue created.
--
-- Why opt-in (not "any row with no linear_url"): public.tasks holds
-- non-KEI operational rows (REVIEW-PR-* queue tasks, smoke tests) that
-- have no linear_url and must NEVER be mirrored to Linear. A blanket
-- "no linear_url -> issueCreate" would pollute Linear with junk. Only a
-- row explicitly flagged linear_create_pending = TRUE is a create
-- candidate. DEFAULT FALSE -> every existing row is a non-candidate, so
-- the create path is dormant until the redirect sites (separate PR) set
-- the flag for genuine KEIs.
--
-- The emit trigger fn_emit_sync_event_postgres is re-defined to also skip
-- emission when an UPDATE touches only the push's bookkeeping columns
-- (linear_synced_status / linear_url / linear_create_pending) — so the
-- push's writes never echo back as Supabase sync_events.

ALTER TABLE public.tasks
    ADD COLUMN IF NOT EXISTS linear_create_pending BOOLEAN DEFAULT FALSE;

COMMENT ON COLUMN public.tasks.linear_create_pending IS
    'Agency_OS-j8eu — one-way push create opt-in. TRUE = this task should '
    'get a Linear issue created by linear_oneway_push.py. The push consumes '
    'the flag (sets it FALSE) before issueCreate. DEFAULT FALSE — only the '
    'KEI-create redirect sites set it TRUE.';

-- Re-definition of the emit trigger. Identical to the Agency_OS-1x3x
-- (Part 4) version except the watermark guard now also covers linear_url
-- and linear_create_pending.
CREATE OR REPLACE FUNCTION public.fn_emit_sync_event_postgres()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
DECLARE
    v_event_type TEXT;
    v_payload    JSONB;
    -- Terminal statuses — single source of truth (avoids repeating the
    -- 'done'/'cancelled' literals across the close/reopen branches).
    v_terminal   CONSTANT TEXT[] := ARRAY['done', 'cancelled'];
BEGIN
    IF TG_OP = 'INSERT' THEN
        v_event_type := 'create';
    ELSIF TG_OP = 'UPDATE' THEN
        -- Watermark guard: an UPDATE that changes ONLY the one-way push's
        -- bookkeeping columns (status/title/priority all unchanged) is the
        -- push recording its own progress. Emit nothing — otherwise the
        -- push's write echoes back as a Supabase sync_event.
        IF NEW.status IS NOT DISTINCT FROM OLD.status
           AND NEW.title IS NOT DISTINCT FROM OLD.title
           AND NEW.priority IS NOT DISTINCT FROM OLD.priority
           AND (NEW.linear_synced_status IS DISTINCT FROM OLD.linear_synced_status
                OR NEW.linear_url IS DISTINCT FROM OLD.linear_url
                OR NEW.linear_create_pending IS DISTINCT FROM OLD.linear_create_pending) THEN
            RETURN NEW;
        END IF;
        -- Closing transitions (status in a terminal state) emit 'close';
        -- everything else is 'update'.
        IF NEW.status = ANY(v_terminal) AND NEW.status IS DISTINCT FROM OLD.status THEN
            v_event_type := 'close';
        ELSIF OLD.status = ANY(v_terminal) AND NEW.status <> ALL(v_terminal) THEN
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
