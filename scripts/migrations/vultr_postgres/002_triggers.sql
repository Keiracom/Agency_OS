-- =============================================================================
-- KEI-241  Vultr Postgres Migration — Governance Triggers
-- Author:  [AIDEN]
-- Date:    2026-05-28
-- Branch:  aiden/vultr-postgres-migration
--
-- DO NOT APPLY until Atlas has provisioned the Vultr Postgres instance AND
-- VULTR_POSTGRES_DSN is set in the environment.
--
-- Apply AFTER 001_schema.sql. All triggers are idempotent:
-- DROP TRIGGER IF EXISTS precedes every CREATE TRIGGER.
-- =============================================================================

-- ---------------------------------------------------------------------------
-- Hard gate: refuse to run on a standby / replica.
-- ---------------------------------------------------------------------------
DO $$
BEGIN
    IF pg_is_in_recovery() THEN
        RAISE EXCEPTION 'KEI-241 gate: pg_is_in_recovery() = true — this is a standby. '
            'Run only against the primary Vultr Postgres instance.';
    END IF;
END;
$$;

-- ===========================================================================
-- Trigger 1: verify-before-done
-- ---------------------------------------------------------------------------
-- Blocks UPDATE tasks SET status='done' when:
--   - acceptance_criteria IS NOT NULL AND acceptance_criteria <> ''
--   - no task_verifications row exists for this task_id
-- BEFORE UPDATE OF status ensures the row is never written on violation.
-- ===========================================================================

CREATE OR REPLACE FUNCTION public.fn_verify_before_done()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    -- Only fires when status is being changed TO 'done'.
    IF NEW.status = 'done' AND OLD.status IS DISTINCT FROM 'done' THEN
        -- Only enforced when acceptance_criteria is present and non-empty.
        IF NEW.acceptance_criteria IS NOT NULL AND NEW.acceptance_criteria <> '' THEN
            IF NOT EXISTS (
                SELECT 1
                FROM public.task_verifications
                WHERE task_id = NEW.id
            ) THEN
                RAISE EXCEPTION
                    'verify-before-done: task % has acceptance_criteria but no '
                    'task_verifications row. Insert a verification row before '
                    'marking done.',
                    NEW.id
                USING ERRCODE = 'check_violation';
            END IF;
        END IF;
    END IF;
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_verify_before_done ON public.tasks;
CREATE TRIGGER trg_verify_before_done
    BEFORE UPDATE OF status ON public.tasks
    FOR EACH ROW
    EXECUTE FUNCTION public.fn_verify_before_done();

COMMENT ON FUNCTION public.fn_verify_before_done() IS
    'KEI-241 — Gate: task cannot be marked done when acceptance_criteria is set '
    'unless a task_verifications row exists. Blocks the UPDATE before it lands.';

-- ===========================================================================
-- Trigger 2: block_parent_claim
-- ---------------------------------------------------------------------------
-- Prevents a callsign from claiming a second active task while one is already
-- active (excluding is_parent=true rows, which are coordination tasks).
-- Belt-and-suspenders alongside the tasks_active_claim UNIQUE partial index —
-- this trigger produces an explicit, actionable error message.
-- ===========================================================================

CREATE OR REPLACE FUNCTION public.fn_block_parent_claim()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
DECLARE
    v_existing_task_id TEXT;
BEGIN
    -- Only fires when a row is being claimed (status -> 'active' + claimed_by set).
    IF NEW.status = 'active'
       AND NEW.claimed_by IS NOT NULL
       AND (OLD.status IS DISTINCT FROM 'active' OR OLD.claimed_by IS DISTINCT FROM NEW.claimed_by)
    THEN
        -- is_parent=true tasks are exempt — they are coordination umbrella tasks
        -- that may legitimately coexist with a worker active task.
        IF NOT COALESCE(NEW.is_parent, FALSE) THEN
            SELECT id INTO v_existing_task_id
            FROM public.tasks
            WHERE claimed_by = NEW.claimed_by
              AND status = 'active'
              AND id <> NEW.id
              AND NOT COALESCE(is_parent, FALSE)
            LIMIT 1;

            IF v_existing_task_id IS NOT NULL THEN
                RAISE EXCEPTION
                    'block_parent_claim: callsign % already has an active task (%). '
                    'Finish or release it before claiming %.',
                    NEW.claimed_by, v_existing_task_id, NEW.id
                USING ERRCODE = 'check_violation';
            END IF;
        END IF;
    END IF;
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_block_parent_claim ON public.tasks;
CREATE TRIGGER trg_block_parent_claim
    BEFORE UPDATE ON public.tasks
    FOR EACH ROW
    EXECUTE FUNCTION public.fn_block_parent_claim();

COMMENT ON FUNCTION public.fn_block_parent_claim() IS
    'KEI-241 — Prevents a callsign from holding two simultaneous active tasks. '
    'Complements the tasks_active_claim UNIQUE partial index with a human-readable '
    'exception. is_parent=true tasks are exempt.';

-- ===========================================================================
-- Trigger 3: KEI-87 ceo_memory write-guard (re-applied exactly)
-- ---------------------------------------------------------------------------
-- Only elliot and dave may write rows whose key starts with 'ceo:'.
-- Requires agency_os.callsign session var to be SET LOCAL before the write.
-- ===========================================================================

CREATE OR REPLACE FUNCTION public.ceo_memory_write_guard()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
DECLARE
    caller TEXT;
BEGIN
    IF NEW.key NOT LIKE 'ceo:%' THEN
        RETURN NEW;
    END IF;
    caller := current_setting('agency_os.callsign', true);
    IF caller IS NULL OR caller = '' THEN
        RAISE EXCEPTION
            'KEI-87 ceo_memory write-guard: agency_os.callsign session-var must be '
            'SET LOCAL before writing key %; missing var refused.',
            NEW.key
        USING ERRCODE = 'check_violation';
    END IF;
    IF caller NOT IN ('elliot', 'dave') THEN
        RAISE EXCEPTION
            'KEI-87 ceo_memory write-guard: agency_os.callsign=% is not in '
            '(elliot, dave) — refused write on key %',
            caller, NEW.key
        USING ERRCODE = 'check_violation';
    END IF;
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS ceo_memory_write_guard ON public.ceo_memory;
CREATE TRIGGER ceo_memory_write_guard
    BEFORE INSERT OR UPDATE ON public.ceo_memory
    FOR EACH ROW
    EXECUTE FUNCTION public.ceo_memory_write_guard();

COMMENT ON FUNCTION public.ceo_memory_write_guard() IS
    'KEI-87/KEI-241 — Restricts ceo:* key writes to callsigns elliot and dave. '
    'Session var agency_os.callsign must be SET LOCAL before any ceo:* write.';

-- ===========================================================================
-- Trigger 4: Completion sync fan-out (re-applied from 20260516_completion_sync_queue.sql)
-- ---------------------------------------------------------------------------
-- On tasks.status -> ('done', 'cancelled') OR new task_verifications row,
-- inserts 3 rows into completion_sync_queue (one per sink).
-- ===========================================================================

CREATE OR REPLACE FUNCTION public.fn_enqueue_completion_sync(p_task_id TEXT, p_status TEXT)
RETURNS VOID
LANGUAGE plpgsql
AS $$
BEGIN
    INSERT INTO public.completion_sync_queue (task_id, target_sink, target_status)
    SELECT p_task_id, sink, p_status
    FROM unnest(ARRAY['linear', 'ceo_memory', 'drive_manual']::TEXT[]) AS sink
    ON CONFLICT (task_id, target_sink) WHERE processed = FALSE
    DO UPDATE SET updated_at = NOW();
END;
$$;

CREATE OR REPLACE FUNCTION public.trg_tasks_status_to_sync_queue()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    IF NEW.status IN ('done', 'cancelled') AND NEW.status IS DISTINCT FROM OLD.status THEN
        PERFORM public.fn_enqueue_completion_sync(NEW.id, NEW.status);
    END IF;
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_tasks_completion_sync ON public.tasks;
CREATE TRIGGER trg_tasks_completion_sync
    AFTER UPDATE OF status ON public.tasks
    FOR EACH ROW
    EXECUTE FUNCTION public.trg_tasks_status_to_sync_queue();

CREATE OR REPLACE FUNCTION public.trg_verifications_to_sync_queue()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
DECLARE
    v_status TEXT;
BEGIN
    SELECT status INTO v_status FROM public.tasks WHERE id = NEW.task_id;
    IF v_status IN ('done', 'cancelled') THEN
        PERFORM public.fn_enqueue_completion_sync(NEW.task_id, v_status);
    END IF;
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_verifications_completion_sync ON public.task_verifications;
CREATE TRIGGER trg_verifications_completion_sync
    AFTER INSERT ON public.task_verifications
    FOR EACH ROW
    EXECUTE FUNCTION public.trg_verifications_to_sync_queue();

COMMENT ON FUNCTION public.fn_enqueue_completion_sync(TEXT, TEXT) IS
    'KEI-74/KEI-241 — Fan-out helper: upserts 3 completion_sync_queue rows per terminal status.';

-- ===========================================================================
-- Trigger 5: Dependency auto-unblock (re-applied from 20260516_kei78_dependency_unblock.sql)
-- ---------------------------------------------------------------------------
-- When task X → status='done', any task Y with X in dependencies[] AND all
-- other deps also done gets auto-flipped from blocked → available.
-- ===========================================================================

CREATE OR REPLACE FUNCTION public.fn_unblock_dependents(p_task_id TEXT)
RETURNS INT
LANGUAGE plpgsql
AS $$
DECLARE
    v_unblocked INT := 0;
BEGIN
    WITH candidate AS (
        SELECT id, dependencies
        FROM public.tasks
        WHERE status = 'blocked'
          AND dependencies IS NOT NULL
          AND p_task_id = ANY(dependencies)
    ),
    satisfied AS (
        SELECT c.id
        FROM candidate c
        WHERE NOT EXISTS (
            SELECT 1
            FROM unnest(c.dependencies) AS dep_id
            LEFT JOIN public.tasks t ON t.id = dep_id
            WHERE t.status IS DISTINCT FROM 'done'
        )
    )
    UPDATE public.tasks
       SET status = 'available', updated_at = NOW()
     WHERE id IN (SELECT id FROM satisfied);
    GET DIAGNOSTICS v_unblocked = ROW_COUNT;
    RETURN v_unblocked;
END;
$$;

CREATE OR REPLACE FUNCTION public.trg_tasks_dependency_unblock()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    IF NEW.status = 'done' AND NEW.status IS DISTINCT FROM OLD.status THEN
        PERFORM public.fn_unblock_dependents(NEW.id);
    END IF;
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_tasks_unblock_dependents ON public.tasks;
CREATE TRIGGER trg_tasks_unblock_dependents
    AFTER UPDATE OF status ON public.tasks
    FOR EACH ROW
    EXECUTE FUNCTION public.trg_tasks_dependency_unblock();

COMMENT ON FUNCTION public.fn_unblock_dependents(TEXT) IS
    'KEI-78/KEI-241 — Scan tasks whose dependencies[] contain p_task_id and '
    'status=blocked; flip to available when all deps are done. Returns count.';

-- ===========================================================================
-- Trigger 6: keiracom_tenants updated_at touch (re-applied from 20260525_keiracom_tenants.sql)
-- ===========================================================================

CREATE OR REPLACE FUNCTION public.keiracom_tenants_touch_updated_at()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS keiracom_tenants_touch_updated_at_tg ON public.keiracom_tenants;
CREATE TRIGGER keiracom_tenants_touch_updated_at_tg
    BEFORE UPDATE ON public.keiracom_tenants
    FOR EACH ROW
    EXECUTE FUNCTION public.keiracom_tenants_touch_updated_at();

COMMENT ON FUNCTION public.keiracom_tenants_touch_updated_at() IS
    'KEI-241 — Auto-sets updated_at on any UPDATE to keiracom_tenants.';
