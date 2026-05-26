-- ============================================================================
-- 20260526_keiracom_tenant_budgets.sql
--
-- Phase A7 sub-task 2 — per-tenant LLM token budget policy data.
-- bd: Agency_OS-rw8e
--
-- Sibling to keiracom_tenant_metering (PR #1137). Stores the per-tenant tier
-- + per-call cap + daily/monthly pool sizes + model-cost calibration weights
-- that the LLM-call workflow #2 token_gate enforces against.
--
-- CANONICAL DESIGN — docs/architecture/design/a7_cache_architecture.md §6 +
-- §13 CB-3 (point-in-time schema, no effective_from/until per build clarification)
-- + CB-9 (tier CHECK constraint).
--
-- Schema decisions (per CB-3):
--   - PRIMARY KEY (tenant_id) — one current policy per tenant
--   - NO effective_from/until columns (point-in-time only)
--   - updated_at tracks last write via app-layer UPSERT
--   - Historical "what was Pro's cap in March?" reconstruction via
--     keiracom_tenant_metering rollup + future budget-change audit log
--     (separate follow-up if needed; not required for V1 pre-revenue)
--
-- CHECK (tier IN (...)) per CB-9 prevents typos at INSERT/UPDATE time;
-- mirrors VALID_TIERS in src/keiracom_system/cache/token_budget_policy.py.
--
-- Seed rows: 5 tier-default placeholders (Dave's tenant assigned 'team' tier
-- per design §5 "team-equivalent for capacity allocation"). Operator inserts
-- per-tenant override row at onboarding for Enterprise (custom caps).
--
-- KEI-87 bypass: SET LOCAL agency_os.callsign = 'dave' required because this
-- migration creates a public-schema table — same pattern as the metering
-- migration (PR #1137) and 20260524_0scg_ceo_memory_context_not_null.sql.
-- ============================================================================

SET LOCAL agency_os.callsign = 'dave';

CREATE TABLE IF NOT EXISTS public.keiracom_tenant_budgets (
    tenant_id              UUID         NOT NULL,
    tier                   TEXT         NOT NULL
        CHECK (tier IN ('sandbox','solo','pro','team','enterprise')),
    per_call_cap_tokens    BIGINT       NOT NULL CHECK (per_call_cap_tokens > 0),
    daily_pool_tokens      BIGINT       NOT NULL CHECK (daily_pool_tokens > 0),
    monthly_pool_tokens    BIGINT       NOT NULL CHECK (monthly_pool_tokens > 0),
    model_cost_calibration JSONB        NOT NULL DEFAULT '{}'::jsonb,
    updated_at             TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    PRIMARY KEY (tenant_id),
    FOREIGN KEY (tenant_id) REFERENCES public.keiracom_tenants(tenant_id) ON DELETE CASCADE
);

-- "All Pro tenants" / "all Team tenants" queries — per CB-3 index decision.
CREATE INDEX IF NOT EXISTS idx_keiracom_tenant_budgets_tier
    ON public.keiracom_tenant_budgets (tier);

-- Trigger: refresh updated_at on any UPDATE so the column tracks the last
-- policy change accurately even if the writer forgets to set it explicitly.
CREATE OR REPLACE FUNCTION public.keiracom_tenant_budgets_set_updated_at()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_keiracom_tenant_budgets_updated_at
    ON public.keiracom_tenant_budgets;

CREATE TRIGGER trg_keiracom_tenant_budgets_updated_at
    BEFORE UPDATE ON public.keiracom_tenant_budgets
    FOR EACH ROW
    EXECUTE FUNCTION public.keiracom_tenant_budgets_set_updated_at();

-- ----------------------------------------------------------------------------
-- Seed: Dave's tenant gets 'team' tier defaults (design §5 + metadata tier).
-- Dave is tenant_id 00000000-0000-0000-0000-000000000001 per
-- ceo:keiracom_architecture_v2 tenant.single_supabase amendment (PR #1168).
-- Other tenants seeded at their per-customer onboarding (Phase C5).
-- ----------------------------------------------------------------------------

INSERT INTO public.keiracom_tenant_budgets (
    tenant_id,
    tier,
    per_call_cap_tokens,
    daily_pool_tokens,
    monthly_pool_tokens,
    model_cost_calibration
)
SELECT
    '00000000-0000-0000-0000-000000000001'::uuid AS tenant_id,
    'team'::text                                  AS tier,
    200000::bigint                                AS per_call_cap_tokens,
    20000000::bigint                              AS daily_pool_tokens,
    600000000::bigint                             AS monthly_pool_tokens,
    jsonb_build_object(
        'anthropic/claude-3-5-sonnet', 3.0,
        'anthropic/claude-3-5-haiku',  1.0,
        'openai/gpt-4o',               2.5,
        'openai/gpt-4o-mini',          0.8,
        'google/gemini-2.5-flash',     0.5
    )                                              AS model_cost_calibration
WHERE EXISTS (
    SELECT 1 FROM public.keiracom_tenants
    WHERE tenant_id = '00000000-0000-0000-0000-000000000001'::uuid
)
ON CONFLICT (tenant_id) DO NOTHING;
