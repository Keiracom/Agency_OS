-- Wave 5 — Customer memory override interface: public.memory_overrides.
--
-- Authored by Atlas 2026-05-28 (Elliot dispatch — Wave 5 customer override API).
-- Backs src/retrieval/overrides.py. A customer (or operator on their behalf)
-- records an intent to either SUPPRESS a specific memory from recall ('ignore')
-- or PROMOTE it ('prefer') — optionally scoped to a single task_type and/or
-- given an expiry. The retrieval read-path (agent_query.query) consults active
-- rows and filters/boosts citations accordingly, behind the
-- RETRIEVAL_OVERRIDES_ENABLED feature flag (default off).
--
-- Scope note: the override model intentionally carries no tenant_id column —
-- it follows the dispatch spec verbatim ({memory_id, override_type, task_type,
-- expires_at}). Tenant scoping is a deliberate follow-up if/when overrides go
-- multi-tenant (cf. the YELLOW-4 Hindsight recall tenant work, Agency_OS-7sj6).

BEGIN;

CREATE TYPE public.memory_override_type AS ENUM ('ignore', 'prefer');

CREATE TABLE IF NOT EXISTS public.memory_overrides (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    memory_id     TEXT NOT NULL,
    override_type public.memory_override_type NOT NULL,
    task_type     TEXT,
    expires_at    TIMESTAMPTZ,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT memory_overrides_memory_id_not_blank CHECK (length(memory_id) > 0)
);

-- Apply-path join key: agent_query matches a citation's source_id to memory_id.
CREATE INDEX IF NOT EXISTS idx_memory_overrides_memory_id
    ON public.memory_overrides (memory_id);

-- Load-path filter: scope by task_type + range-scan the expiry. NOW() is
-- non-immutable so it can't sit in an index predicate — a plain composite
-- index serves the `task_type` filter and the `expires_at > NOW()` range.
CREATE INDEX IF NOT EXISTS idx_memory_overrides_task_expiry
    ON public.memory_overrides (task_type, expires_at);

COMMENT ON TABLE public.memory_overrides IS
    'Customer-facing recall overrides. ignore=suppress memory_id from recall; prefer=boost it. Optional task_type scope + expiry. Consumed by src/retrieval/overrides.py behind RETRIEVAL_OVERRIDES_ENABLED.';
COMMENT ON COLUMN public.memory_overrides.memory_id IS
    'Matches the citation source_id surfaced by agent_query (Hindsight memory / chunk / doc identifier).';
COMMENT ON COLUMN public.memory_overrides.task_type IS
    'NULL = applies to all queries; a value = applies only when the query declares the same task_type.';
COMMENT ON COLUMN public.memory_overrides.expires_at IS
    'NULL = never expires; otherwise the override is inert once NOW() passes this timestamp.';

COMMIT;
