-- KEI-78 — Dependency auto-unblock trigger.
--
-- When task X transitions to status='done', any task Y where X = ANY(Y.dependencies)
-- AND Y.status='blocked' AND every element of Y.dependencies is now 'done' gets
-- auto-flipped to status='available'. KEI-45 Supabase Realtime fans out the
-- change; idle agents claim from the queue without manual dispatch.
--
-- Same trigger pattern as KEI-74 completion_sync. Per Dave directive
-- 2026-05-16T11:55Z. Plus: governance rule ratified ts ~11:52Z — dependencies[]
-- is mandatory at task creation when the work depends on another agent.

CREATE OR REPLACE FUNCTION public.fn_unblock_dependents(p_task_id TEXT)
RETURNS INT LANGUAGE plpgsql AS $$
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
RETURNS TRIGGER LANGUAGE plpgsql AS $$
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
    FOR EACH ROW EXECUTE FUNCTION public.trg_tasks_dependency_unblock();

COMMENT ON FUNCTION public.fn_unblock_dependents(TEXT) IS
    'KEI-78 — scan tasks whose dependencies[] contain p_task_id and status=blocked; '
    'flip to status=available when all deps are done. Idempotent: returns count.';
