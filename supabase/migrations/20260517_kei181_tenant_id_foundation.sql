-- KEI-181: Tenant ID + RLS Foundation (Phase 0.5 P0)
-- Author: MAX
-- Idempotent: safe to re-run.
-- Tables touched: public.tenants (new), public.tasks, public.tool_call_log,
--   public.retrieval_events, public.task_verifications, public.ceo_memory,
--   public.agent_memories, public.completion_sync_queue

-- ============================================================
-- 1. tenants table
-- ============================================================
CREATE TABLE IF NOT EXISTS public.tenants (
    id          integer     PRIMARY KEY,
    name        text        NOT NULL,
    created_at  timestamptz NOT NULL DEFAULT now(),
    deleted_at  timestamptz
);

COMMENT ON TABLE public.tenants IS 'KEI-181: one row per tenant. Dave=1, customers=2+.';

-- Seed Dave's tenant row
INSERT INTO public.tenants (id, name)
VALUES (1, 'Dave / Agency_OS internal')
ON CONFLICT (id) DO NOTHING;

-- ============================================================
-- 2. Add tenant_id column to each work table (idempotent)
-- ============================================================

ALTER TABLE public.tasks
    ADD COLUMN IF NOT EXISTS tenant_id integer NOT NULL DEFAULT 1
    REFERENCES public.tenants(id);

ALTER TABLE public.tool_call_log
    ADD COLUMN IF NOT EXISTS tenant_id integer NOT NULL DEFAULT 1
    REFERENCES public.tenants(id);

ALTER TABLE public.retrieval_events
    ADD COLUMN IF NOT EXISTS tenant_id integer NOT NULL DEFAULT 1
    REFERENCES public.tenants(id);

ALTER TABLE public.task_verifications
    ADD COLUMN IF NOT EXISTS tenant_id integer NOT NULL DEFAULT 1
    REFERENCES public.tenants(id);

ALTER TABLE public.ceo_memory
    ADD COLUMN IF NOT EXISTS tenant_id integer NOT NULL DEFAULT 1
    REFERENCES public.tenants(id);

ALTER TABLE public.agent_memories
    ADD COLUMN IF NOT EXISTS tenant_id integer NOT NULL DEFAULT 1
    REFERENCES public.tenants(id);

ALTER TABLE public.completion_sync_queue
    ADD COLUMN IF NOT EXISTS tenant_id integer NOT NULL DEFAULT 1
    REFERENCES public.tenants(id);

-- ============================================================
-- 3. Backfill (belt + braces — DEFAULT 1 already covers inserts)
-- ============================================================

UPDATE public.tasks             SET tenant_id = 1 WHERE tenant_id IS NULL;
UPDATE public.tool_call_log     SET tenant_id = 1 WHERE tenant_id IS NULL;
UPDATE public.retrieval_events  SET tenant_id = 1 WHERE tenant_id IS NULL;
UPDATE public.task_verifications SET tenant_id = 1 WHERE tenant_id IS NULL;
UPDATE public.ceo_memory        SET tenant_id = 1 WHERE tenant_id IS NULL;
UPDATE public.agent_memories    SET tenant_id = 1 WHERE tenant_id IS NULL;
UPDATE public.completion_sync_queue SET tenant_id = 1 WHERE tenant_id IS NULL;

-- ============================================================
-- 4. Indexes
-- ============================================================

CREATE INDEX IF NOT EXISTS tasks_tenant_id_idx
    ON public.tasks (tenant_id);

CREATE INDEX IF NOT EXISTS tool_call_log_tenant_id_idx
    ON public.tool_call_log (tenant_id);

CREATE INDEX IF NOT EXISTS retrieval_events_tenant_id_idx
    ON public.retrieval_events (tenant_id);

CREATE INDEX IF NOT EXISTS task_verifications_tenant_id_idx
    ON public.task_verifications (tenant_id);

CREATE INDEX IF NOT EXISTS ceo_memory_tenant_id_idx
    ON public.ceo_memory (tenant_id);

CREATE INDEX IF NOT EXISTS agent_memories_tenant_id_idx
    ON public.agent_memories (tenant_id);

CREATE INDEX IF NOT EXISTS completion_sync_queue_tenant_id_idx
    ON public.completion_sync_queue (tenant_id);

-- ============================================================
-- 5. Enable RLS
-- ============================================================

ALTER TABLE public.tasks               ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.tool_call_log       ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.retrieval_events    ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.task_verifications  ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.ceo_memory          ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.agent_memories      ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.completion_sync_queue ENABLE ROW LEVEL SECURITY;

-- ============================================================
-- 6. RLS Policies  (DROP IF EXISTS first for idempotency)
-- ============================================================
-- 3-clause USING/WITH CHECK:
--   clause 1: session var matches row's tenant_id  (normal anon/authenticated callers)
--   clause 2: current_setting('role') = 'service_role'  (Supabase service-role key)
--   clause 3: agency_os.tenant_id IS NULL  (backend daemons that haven't set the var)

DROP POLICY IF EXISTS tenant_isolation_tasks ON public.tasks;
CREATE POLICY tenant_isolation_tasks ON public.tasks
    FOR ALL
    USING (
        current_setting('agency_os.tenant_id', true)::integer = tenant_id
        OR current_setting('role', true) = 'service_role'
        OR current_setting('agency_os.tenant_id', true) IS NULL
    )
    WITH CHECK (
        current_setting('agency_os.tenant_id', true)::integer = tenant_id
        OR current_setting('role', true) = 'service_role'
        OR current_setting('agency_os.tenant_id', true) IS NULL
    );

DROP POLICY IF EXISTS tenant_isolation_tool_call_log ON public.tool_call_log;
CREATE POLICY tenant_isolation_tool_call_log ON public.tool_call_log
    FOR ALL
    USING (
        current_setting('agency_os.tenant_id', true)::integer = tenant_id
        OR current_setting('role', true) = 'service_role'
        OR current_setting('agency_os.tenant_id', true) IS NULL
    )
    WITH CHECK (
        current_setting('agency_os.tenant_id', true)::integer = tenant_id
        OR current_setting('role', true) = 'service_role'
        OR current_setting('agency_os.tenant_id', true) IS NULL
    );

DROP POLICY IF EXISTS tenant_isolation_retrieval_events ON public.retrieval_events;
CREATE POLICY tenant_isolation_retrieval_events ON public.retrieval_events
    FOR ALL
    USING (
        current_setting('agency_os.tenant_id', true)::integer = tenant_id
        OR current_setting('role', true) = 'service_role'
        OR current_setting('agency_os.tenant_id', true) IS NULL
    )
    WITH CHECK (
        current_setting('agency_os.tenant_id', true)::integer = tenant_id
        OR current_setting('role', true) = 'service_role'
        OR current_setting('agency_os.tenant_id', true) IS NULL
    );

DROP POLICY IF EXISTS tenant_isolation_task_verifications ON public.task_verifications;
CREATE POLICY tenant_isolation_task_verifications ON public.task_verifications
    FOR ALL
    USING (
        current_setting('agency_os.tenant_id', true)::integer = tenant_id
        OR current_setting('role', true) = 'service_role'
        OR current_setting('agency_os.tenant_id', true) IS NULL
    )
    WITH CHECK (
        current_setting('agency_os.tenant_id', true)::integer = tenant_id
        OR current_setting('role', true) = 'service_role'
        OR current_setting('agency_os.tenant_id', true) IS NULL
    );

DROP POLICY IF EXISTS tenant_isolation_ceo_memory ON public.ceo_memory;
CREATE POLICY tenant_isolation_ceo_memory ON public.ceo_memory
    FOR ALL
    USING (
        current_setting('agency_os.tenant_id', true)::integer = tenant_id
        OR current_setting('role', true) = 'service_role'
        OR current_setting('agency_os.tenant_id', true) IS NULL
    )
    WITH CHECK (
        current_setting('agency_os.tenant_id', true)::integer = tenant_id
        OR current_setting('role', true) = 'service_role'
        OR current_setting('agency_os.tenant_id', true) IS NULL
    );

DROP POLICY IF EXISTS tenant_isolation_agent_memories ON public.agent_memories;
CREATE POLICY tenant_isolation_agent_memories ON public.agent_memories
    FOR ALL
    USING (
        current_setting('agency_os.tenant_id', true)::integer = tenant_id
        OR current_setting('role', true) = 'service_role'
        OR current_setting('agency_os.tenant_id', true) IS NULL
    )
    WITH CHECK (
        current_setting('agency_os.tenant_id', true)::integer = tenant_id
        OR current_setting('role', true) = 'service_role'
        OR current_setting('agency_os.tenant_id', true) IS NULL
    );

DROP POLICY IF EXISTS tenant_isolation_completion_sync_queue ON public.completion_sync_queue;
CREATE POLICY tenant_isolation_completion_sync_queue ON public.completion_sync_queue
    FOR ALL
    USING (
        current_setting('agency_os.tenant_id', true)::integer = tenant_id
        OR current_setting('role', true) = 'service_role'
        OR current_setting('agency_os.tenant_id', true) IS NULL
    )
    WITH CHECK (
        current_setting('agency_os.tenant_id', true)::integer = tenant_id
        OR current_setting('role', true) = 'service_role'
        OR current_setting('agency_os.tenant_id', true) IS NULL
    );

-- ============================================================
-- 7. Column comments
-- ============================================================

COMMENT ON COLUMN public.tasks.tenant_id             IS 'KEI-181: tenant isolation. FK to public.tenants(id). Dave=1, customers=2+.';
COMMENT ON COLUMN public.tool_call_log.tenant_id     IS 'KEI-181: tenant isolation. FK to public.tenants(id). Dave=1, customers=2+.';
COMMENT ON COLUMN public.retrieval_events.tenant_id  IS 'KEI-181: tenant isolation. FK to public.tenants(id). Dave=1, customers=2+.';
COMMENT ON COLUMN public.task_verifications.tenant_id IS 'KEI-181: tenant isolation. FK to public.tenants(id). Dave=1, customers=2+.';
COMMENT ON COLUMN public.ceo_memory.tenant_id        IS 'KEI-181: tenant isolation. FK to public.tenants(id). Dave=1, customers=2+.';
COMMENT ON COLUMN public.agent_memories.tenant_id    IS 'KEI-181: tenant isolation. FK to public.tenants(id). Dave=1, customers=2+.';
COMMENT ON COLUMN public.completion_sync_queue.tenant_id IS 'KEI-181: tenant isolation. FK to public.tenants(id). Dave=1, customers=2+.';
