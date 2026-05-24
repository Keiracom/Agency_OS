-- Phase 2 build (item 2) — Keiracom System control-plane: tenants table.
--
-- Authored by Atlas 2026-05-24 (Dave-ratified Phase 2 build commit + product
-- name lock same day). Lands in fleet repo for now; migrates to product repo
-- when Phase 2.0 carve completes.
--
-- ---------------------------------------------------------------------------
-- Canonical key citations (per audit-dispatch checklist `_orchestrator.md`):
--
-- ceo:agency_os_keiracom_separation_v1 (updated 2026-05-24T11:04Z+):
--   product_name_lock: "Keiracom System — locked by Dave 2026-05-24.
--     Encapsulates the entire build: memory, agents, UI/UX, governance.
--     Product repo name follows from this lock; repo creation proceeds as
--     Phase 2.0 carve-out."
--
-- ceo:memory_abstraction_layer_v1 — substantive_lock item 2:
--   "Hindsight self-hosted as engine (Vectorize.io open-source MIT).
--     Deployment topology is tier-keyed: Solo/Pro tiers use shared-instance
--     schema-per-tenant via TenantExtension + SupabaseTenantExtension
--     (Topology B); Scale tier and regulated verticals use per-tenant VPC
--     (Topology A). Same MAL primitives across both topologies via MCP
--     swappability. (Phase 2.1 spike item iii — Atlas PR #1126.)"
--
-- ceo:memory_abstraction_layer_v1 — eleven_agreed_positions tenancy line:
--   "Tenancy: schema-per-tenant + 20-30 tripwire + migration runner pre-launch"
-- ---------------------------------------------------------------------------

BEGIN;

-- Three enums encode the contracts above:
-- - tier        — Dave's product-name lock day defined Solo/Pro/Scale
-- - topology    — A vs B from substantive_lock; tier→topology default in
--   provisioning.py but recorded per-row so audit can replay
-- - status      — provisioning lifecycle (FSM enforced by app + this CHECK)

CREATE TYPE public.keiracom_tier AS ENUM ('solo', 'pro', 'scale');

CREATE TYPE public.keiracom_topology AS ENUM ('A_per_vpc', 'B_shared_schema');

CREATE TYPE public.keiracom_tenant_status AS ENUM (
    'provisioning',
    'active',
    'suspended',
    'deprovisioning',
    'deleted'
);

CREATE TABLE IF NOT EXISTS public.keiracom_tenants (
    tenant_id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tier                   public.keiracom_tier NOT NULL,
    topology               public.keiracom_topology NOT NULL,
    llm_api_key_encrypted  TEXT NOT NULL,
    llm_model              TEXT NOT NULL,
    embedding_dim          INT  NOT NULL DEFAULT 384,
    schema_name            TEXT,
    vpc_id                 TEXT,
    signup_date            TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    status                 public.keiracom_tenant_status NOT NULL DEFAULT 'provisioning',
    created_at             TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at             TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    -- Topology consistency: B requires schema_name (not null), A requires vpc_id
    CONSTRAINT keiracom_tenants_topology_consistency CHECK (
        (topology = 'B_shared_schema' AND schema_name IS NOT NULL AND vpc_id IS NULL)
        OR (topology = 'A_per_vpc'    AND vpc_id IS NOT NULL    AND schema_name IS NULL)
    ),
    CONSTRAINT keiracom_tenants_embedding_dim_positive CHECK (embedding_dim > 0),
    CONSTRAINT keiracom_tenants_llm_api_key_not_blank  CHECK (length(llm_api_key_encrypted) > 0),
    CONSTRAINT keiracom_tenants_llm_model_not_blank    CHECK (length(llm_model) > 0)
);

CREATE INDEX IF NOT EXISTS idx_keiracom_tenants_tier
    ON public.keiracom_tenants (tier);

CREATE INDEX IF NOT EXISTS idx_keiracom_tenants_status
    ON public.keiracom_tenants (status)
    WHERE status != 'deleted';

CREATE INDEX IF NOT EXISTS idx_keiracom_tenants_signup_date
    ON public.keiracom_tenants (signup_date DESC);

-- updated_at auto-update trigger
CREATE OR REPLACE FUNCTION public.keiracom_tenants_touch_updated_at()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $func$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END
$func$;

DROP TRIGGER IF EXISTS keiracom_tenants_touch_updated_at_tg ON public.keiracom_tenants;

CREATE TRIGGER keiracom_tenants_touch_updated_at_tg
    BEFORE UPDATE ON public.keiracom_tenants
    FOR EACH ROW
    EXECUTE FUNCTION public.keiracom_tenants_touch_updated_at();

-- Comments — schema documentation lands in pg_catalog for tooling discovery.
COMMENT ON TABLE public.keiracom_tenants IS
    'Keiracom System control-plane tenants table. Tier-keyed topology per ceo:memory_abstraction_layer_v1 substantive_lock.';
COMMENT ON COLUMN public.keiracom_tenants.llm_api_key_encrypted IS
    'BYOK-sovereign tenant LLM API key, encrypted at application layer before insert.';
COMMENT ON COLUMN public.keiracom_tenants.embedding_dim IS
    'Embedding vector dimension; default 384 matches BGE-small-en-v1.5 per eleven_agreed_positions #1.';
COMMENT ON COLUMN public.keiracom_tenants.schema_name IS
    'Topology B (shared-instance) Hindsight schema name. NULL for Topology A.';
COMMENT ON COLUMN public.keiracom_tenants.vpc_id IS
    'Topology A (per-tenant VPC) VPC reference. NULL for Topology B.';

COMMIT;
