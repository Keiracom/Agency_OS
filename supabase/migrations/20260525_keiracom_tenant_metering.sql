-- ============================================================================
-- 20260525_keiracom_tenant_metering.sql
--
-- Phase 2 build wave 2 item 3 — log-based per-tenant LLM metering pipeline.
-- bd: Agency_OS-3k8g
--
-- Stores per-tenant per-day per-model aggregate counts rolled up from
-- Hindsight log streams (see src/keiracom_system/metering/).
--
-- Idempotent on (tenant_id, date_utc, model). The metering sink does
-- ON CONFLICT UPDATE with cumulative ADD so re-running the pipeline over
-- the same log range (e.g. log replay) produces the same totals — assuming
-- the log shipper provides exactly-once delivery.
--
-- CANONICAL KEY ANCHOR — ceo:memory_abstraction_layer_v1 position 5:
--   "Collective scope: tenant-bounded only, never cross-tenant inference
--    (BYOK sovereignty)"
--
-- This table is for Keiracom-side observability + future overage billing
-- ONLY. Tenants pay LLM providers DIRECTLY via their own BYOK key — we
-- never bill tenants for the inference itself (provider already did),
-- only for tier overage if their volume exceeds plan limits.
--
-- Cost columns (cost_aud_sum, etc.) are intentionally DEFERRED to P3 —
-- they require provider-billing-API integration to translate token counts
-- to per-model-per-tenant dollar amounts, which is the post-first-paying-
-- customer follow-up per PR #1128 §5 recommendation.
--
-- KEI-87 bypass: SET LOCAL agency_os.callsign = 'dave' is required because
-- this migration creates a public-schema table and the write-guard trigger
-- otherwise blocks. Same pattern as 20260524_0scg_ceo_memory_context_not_null.sql.
-- ============================================================================

SET LOCAL agency_os.callsign = 'dave';

CREATE TABLE IF NOT EXISTS public.keiracom_tenant_metering (
    tenant_id           UUID         NOT NULL,
    date_utc            DATE         NOT NULL,
    model               TEXT         NOT NULL,
    request_count       BIGINT       NOT NULL DEFAULT 0,
    input_tokens_sum    BIGINT       NOT NULL DEFAULT 0,
    output_tokens_sum   BIGINT       NOT NULL DEFAULT 0,
    created_at          TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    PRIMARY KEY (tenant_id, date_utc, model),
    FOREIGN KEY (tenant_id) REFERENCES public.keiracom_tenants(tenant_id) ON DELETE CASCADE
);

-- Date-range scans for daily rollup reports + per-tenant trend dashboards.
CREATE INDEX IF NOT EXISTS idx_keiracom_tenant_metering_date_utc
    ON public.keiracom_tenant_metering (date_utc);

CREATE INDEX IF NOT EXISTS idx_keiracom_tenant_metering_tenant_date
    ON public.keiracom_tenant_metering (tenant_id, date_utc DESC);

COMMENT ON TABLE public.keiracom_tenant_metering IS
    'V1 log-based LLM metering aggregates per tenant/day/model. '
    'Phase 2 wave 2 item 3 per PR #1128 §7 P2. Cost columns deferred to P3.';

COMMENT ON COLUMN public.keiracom_tenant_metering.request_count IS
    'Number of LLM-call events observed in the log for this bucket.';
COMMENT ON COLUMN public.keiracom_tenant_metering.input_tokens_sum IS
    'Cumulative input/prompt tokens. Used for tier-overage detection.';
COMMENT ON COLUMN public.keiracom_tenant_metering.output_tokens_sum IS
    'Cumulative output/completion tokens. Used for tier-overage detection.';
