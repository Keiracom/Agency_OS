-- =============================================================================
-- KEI-241  Vultr Postgres Migration — Schema (DDL only, no data)
-- Author:  [AIDEN]
-- Date:    2026-05-28
-- Branch:  aiden/vultr-postgres-migration
--
-- DO NOT APPLY until Atlas has provisioned the Vultr Postgres instance AND
-- VULTR_POSTGRES_DSN is set in the environment.
--
-- Supabase remains the primary fallback store until KEI-242 (Hindsight
-- backup/restore) completes. This file is idempotent; all objects use
-- IF NOT EXISTS / CREATE OR REPLACE where applicable.
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

-- ---------------------------------------------------------------------------
-- Extensions
-- ---------------------------------------------------------------------------
CREATE EXTENSION IF NOT EXISTS "pgcrypto";   -- gen_random_uuid()

-- ---------------------------------------------------------------------------
-- Enums (keiracom_tenants control-plane)
-- ---------------------------------------------------------------------------

DO $$ BEGIN
    CREATE TYPE public.keiracom_tier AS ENUM ('solo', 'pro', 'scale');
EXCEPTION WHEN duplicate_object THEN NULL; END; $$;

DO $$ BEGIN
    CREATE TYPE public.keiracom_topology AS ENUM ('A_per_vpc', 'B_shared_schema');
EXCEPTION WHEN duplicate_object THEN NULL; END; $$;

DO $$ BEGIN
    CREATE TYPE public.keiracom_tenant_status AS ENUM (
        'provisioning',
        'active',
        'suspended',
        'deprovisioning',
        'deleted'
    );
EXCEPTION WHEN duplicate_object THEN NULL; END; $$;

-- ---------------------------------------------------------------------------
-- Table: public.tasks
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.tasks (
    id                        TEXT        PRIMARY KEY NOT NULL,
    title                     TEXT        NOT NULL,
    status                    TEXT        DEFAULT 'available',
    priority                  INTEGER     DEFAULT 2,
    claimed_by                TEXT,
    claimed_at                TIMESTAMPTZ,
    dependencies              TEXT[],
    tags                      TEXT[],
    linear_url                TEXT,
    created_at                TIMESTAMPTZ DEFAULT NOW(),
    updated_at                TIMESTAMPTZ DEFAULT NOW(),
    acceptance_criteria       TEXT,
    required_persona          VARCHAR     DEFAULT 'worker',
    active_thread_id          UUID,
    context_ceiling_tokens    INTEGER     DEFAULT 40000,
    tenant_id                 TEXT        DEFAULT 'internal',
    phase                     NUMERIC     NOT NULL DEFAULT 0,
    claim_source              TEXT        NOT NULL DEFAULT 'manual',
    deployment                BOOLEAN     NOT NULL DEFAULT FALSE,
    heartbeat_at              TIMESTAMPTZ,
    is_parent                 BOOLEAN     DEFAULT FALSE,
    description               TEXT,
    persona                   TEXT,
    bd_id                     TEXT,
    linear_synced_status      TEXT,
    linear_create_pending     BOOLEAN     DEFAULT FALSE
);

-- Indexes on tasks
CREATE INDEX IF NOT EXISTS tasks_available
    ON public.tasks (priority, created_at)
    WHERE status = 'available';

-- Unique partial: one active claim per callsign (belt-and-suspenders with the
-- block_parent_claim trigger defined in 002_triggers.sql).
CREATE UNIQUE INDEX IF NOT EXISTS tasks_active_claim
    ON public.tasks (claimed_by)
    WHERE status = 'active';

CREATE INDEX IF NOT EXISTS idx_tasks_bd_id
    ON public.tasks (bd_id)
    WHERE bd_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_tasks_persona
    ON public.tasks (persona)
    WHERE status = 'available';

CREATE UNIQUE INDEX IF NOT EXISTS uq_tasks_bd_id
    ON public.tasks (bd_id)
    WHERE bd_id IS NOT NULL;

COMMENT ON TABLE public.tasks IS
    'KEI-241 — Operational task queue migrated from Supabase. '
    'Primary store post-KEI-242; Supabase is fallback until then.';

-- ---------------------------------------------------------------------------
-- Table: public.task_verifications
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.task_verifications (
    id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id         TEXT        NOT NULL REFERENCES public.tasks(id) ON DELETE CASCADE,
    verified_by     TEXT        NOT NULL,
    behavioral_test TEXT        NOT NULL,
    test_output     TEXT        NOT NULL,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

COMMENT ON TABLE public.task_verifications IS
    'KEI-241 — Stores evidence rows required by the verify-before-done governance trigger.';

-- ---------------------------------------------------------------------------
-- Table: public.ceo_memory
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.ceo_memory (
    key        TEXT        PRIMARY KEY NOT NULL,
    value      JSONB       NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    version    INTEGER     DEFAULT 1,
    context    TEXT        NOT NULL
);

CREATE INDEX IF NOT EXISTS ceo_memory_context_idx
    ON public.ceo_memory (context);

COMMENT ON TABLE public.ceo_memory IS
    'KEI-241 — CEO SSOT key-value store. Write-guard trigger (KEI-87) enforced '
    'in 002_triggers.sql; only elliot/dave callsigns may write ceo:* keys.';

-- ---------------------------------------------------------------------------
-- Table: public.keiracom_tenants
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.keiracom_tenants (
    tenant_id             UUID                          PRIMARY KEY DEFAULT gen_random_uuid(),
    tier                  public.keiracom_tier          NOT NULL,
    topology              public.keiracom_topology      NOT NULL,
    llm_api_key_encrypted TEXT                          NOT NULL,
    llm_model             TEXT                          NOT NULL,
    embedding_dim         INTEGER                       NOT NULL DEFAULT 384,
    schema_name           TEXT,
    vpc_id                TEXT,
    signup_date           TIMESTAMPTZ                   NOT NULL DEFAULT NOW(),
    status                public.keiracom_tenant_status NOT NULL DEFAULT 'provisioning',
    created_at            TIMESTAMPTZ                   NOT NULL DEFAULT NOW(),
    updated_at            TIMESTAMPTZ                   NOT NULL DEFAULT NOW(),

    -- Topology consistency: Topology B needs schema_name (not null) + vpc_id NULL;
    -- Topology A needs vpc_id (not null) + schema_name NULL.
    CONSTRAINT keiracom_tenants_topology_consistency CHECK (
        (topology = 'B_shared_schema' AND schema_name IS NOT NULL AND vpc_id IS NULL)
        OR (topology = 'A_per_vpc'    AND vpc_id IS NOT NULL    AND schema_name IS NULL)
    ),
    CONSTRAINT keiracom_tenants_embedding_dim_positive
        CHECK (embedding_dim > 0),
    CONSTRAINT keiracom_tenants_llm_api_key_not_blank
        CHECK (length(llm_api_key_encrypted) > 0),
    CONSTRAINT keiracom_tenants_llm_model_not_blank
        CHECK (length(llm_model) > 0)
);

CREATE INDEX IF NOT EXISTS idx_keiracom_tenants_tier
    ON public.keiracom_tenants (tier);

-- Partial index excludes soft-deleted rows from the hot access path.
CREATE INDEX IF NOT EXISTS idx_keiracom_tenants_status
    ON public.keiracom_tenants (status)
    WHERE status != 'deleted';

CREATE INDEX IF NOT EXISTS idx_keiracom_tenants_signup_date
    ON public.keiracom_tenants (signup_date DESC);

COMMENT ON TABLE public.keiracom_tenants IS
    'Keiracom System control-plane tenants table. '
    'Tier-keyed topology per ceo:memory_abstraction_layer_v1 substantive_lock. '
    'max_concurrent_tasks column added in 003_add_max_concurrent_tasks.sql (KEI-241).';

COMMENT ON COLUMN public.keiracom_tenants.llm_api_key_encrypted IS
    'BYOK-sovereign tenant LLM API key, encrypted at application layer before insert.';
COMMENT ON COLUMN public.keiracom_tenants.embedding_dim IS
    'Embedding vector dimension; default 384 matches BGE-small-en-v1.5.';
COMMENT ON COLUMN public.keiracom_tenants.schema_name IS
    'Topology B (shared-instance) Hindsight schema name. NULL for Topology A.';
COMMENT ON COLUMN public.keiracom_tenants.vpc_id IS
    'Topology A (per-tenant VPC) VPC reference. NULL for Topology B.';

-- ---------------------------------------------------------------------------
-- Table: public.keiracom_spawn_attribution
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.keiracom_spawn_attribution (
    spawn_id            UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    ts                  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    source_type         TEXT        NOT NULL
                            CHECK (source_type IN ('slack', 'pr', 'cron', 'inbox', 'unknown')),
    source_id           TEXT        NOT NULL,
    task_type           TEXT        NOT NULL DEFAULT 'unknown'
                            CHECK (task_type IN (
                                'pr_review', 'deliberation', 'build', 'chat',
                                'dispatch_mgmt', 'unknown'
                            )),
    callsign            TEXT        NOT NULL,
    model               TEXT        NOT NULL,
    input_tokens        BIGINT      NOT NULL DEFAULT 0,
    output_tokens       BIGINT      NOT NULL DEFAULT 0,
    cache_read_tokens   BIGINT      NOT NULL DEFAULT 0,
    cache_write_tokens  BIGINT      NOT NULL DEFAULT 0,
    cost_usd            NUMERIC(12, 6) NOT NULL DEFAULT 0,
    completion_status   TEXT        NOT NULL DEFAULT 'unknown'
);

CREATE INDEX IF NOT EXISTS idx_keiracom_spawn_attribution_source_type_ts
    ON public.keiracom_spawn_attribution (source_type, ts DESC);

CREATE INDEX IF NOT EXISTS idx_keiracom_spawn_attribution_task_type_ts
    ON public.keiracom_spawn_attribution (task_type, ts DESC);

CREATE INDEX IF NOT EXISTS idx_keiracom_spawn_attribution_callsign_ts
    ON public.keiracom_spawn_attribution (callsign, ts DESC);

CREATE INDEX IF NOT EXISTS idx_keiracom_spawn_attribution_ts
    ON public.keiracom_spawn_attribution (ts DESC);

COMMENT ON TABLE public.keiracom_spawn_attribution IS
    'KEI-241 — Per-spawn token + cost attribution. Source of truth for billing rollups.';

-- ---------------------------------------------------------------------------
-- Table: public.keiracom_paused_tasks
-- ---------------------------------------------------------------------------
-- Note: no surrogate PK in the Supabase live schema; (task_ref, callsign) is
-- the natural compound key. A surrogate PK is NOT added here — exact schema
-- match is required for the data dump/restore path.
CREATE TABLE IF NOT EXISTS public.keiracom_paused_tasks (
    task_ref      TEXT        NOT NULL,
    callsign      TEXT        NOT NULL,
    paused_at     TIMESTAMPTZ NOT NULL,
    deadline_at   TIMESTAMPTZ NOT NULL,
    interim_state JSONB       NOT NULL DEFAULT '{}',
    question      TEXT,
    options       JSONB,
    state         TEXT        NOT NULL DEFAULT 'pending',
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE public.keiracom_paused_tasks IS
    'KEI-241 — Tracks tasks paused mid-execution awaiting a decision or deadline.';

-- ---------------------------------------------------------------------------
-- Table: public.completion_sync_queue
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.completion_sync_queue (
    id              UUID    PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id         TEXT    NOT NULL REFERENCES public.tasks(id) ON DELETE CASCADE,
    target_sink     TEXT    NOT NULL
                        CHECK (target_sink IN ('linear', 'ceo_memory', 'drive_manual')),
    target_status   TEXT    NOT NULL,
    attempts        INTEGER NOT NULL DEFAULT 0,
    last_attempt_at TIMESTAMPTZ,
    processed       BOOLEAN NOT NULL DEFAULT FALSE,
    error_message   TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Worker SELECT path: unprocessed rows only, ordered by age.
CREATE INDEX IF NOT EXISTS idx_completion_sync_queue_unprocessed
    ON public.completion_sync_queue (created_at)
    WHERE processed = FALSE;

-- Dedupe partial index: at most one unprocessed row per (task_id, target_sink).
CREATE UNIQUE INDEX IF NOT EXISTS uq_completion_sync_queue_pending
    ON public.completion_sync_queue (task_id, target_sink)
    WHERE processed = FALSE;

COMMENT ON TABLE public.completion_sync_queue IS
    'KEI-74/KEI-241 three-store completion fan-out queue. Triggers defined in '
    '002_triggers.sql. Worker drains via SELECT FOR UPDATE SKIP LOCKED.';
