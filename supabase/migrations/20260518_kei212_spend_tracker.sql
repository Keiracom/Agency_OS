-- KEI-212: spend_tracker — per-tenant API spend metrics + budget enforcement column.
-- Author: MAX
-- Idempotent: safe to re-run.
-- Tables touched: public.infra_spend_metrics (new), public.tenants (add daily_budget_aud_cents).
-- Currency: ALL monetary fields are integer $AUD cents (LAW II — Australia First, 1 USD = 1.55 AUD).
-- Foundation: depends on KEI-181 tenants table.

-- ============================================================
-- 1. infra_spend_metrics — one row per model-call completion
-- ============================================================
CREATE TABLE IF NOT EXISTS public.infra_spend_metrics (
    id              bigserial   PRIMARY KEY,
    tenant_id       integer     NOT NULL REFERENCES public.tenants(id),
    callsign        text        NOT NULL,
    model           text        NOT NULL,
    tokens_in       integer     NOT NULL CHECK (tokens_in >= 0),
    tokens_out      integer     NOT NULL CHECK (tokens_out >= 0),
    cost_aud_cents  bigint      NOT NULL CHECK (cost_aud_cents >= 0),
    metadata        jsonb       NOT NULL DEFAULT '{}'::jsonb,
    created_at      timestamptz NOT NULL DEFAULT now()
);

COMMENT ON TABLE public.infra_spend_metrics IS
    'KEI-212: one row per model-call completion emitted by interceptor_proxy. spend_tracker.record() inserts here. cost_aud_cents is integer $AUD cents per LAW II.';

CREATE INDEX IF NOT EXISTS infra_spend_metrics_tenant_id_idx
    ON public.infra_spend_metrics (tenant_id);

CREATE INDEX IF NOT EXISTS infra_spend_metrics_created_at_idx
    ON public.infra_spend_metrics (created_at DESC);

CREATE INDEX IF NOT EXISTS infra_spend_metrics_tenant_day_idx
    ON public.infra_spend_metrics (tenant_id, (created_at::date));

-- ============================================================
-- 2. tenants.daily_budget_aud_cents — NULL = no budget set (no warn)
-- ============================================================
ALTER TABLE public.tenants
    ADD COLUMN IF NOT EXISTS daily_budget_aud_cents bigint;

COMMENT ON COLUMN public.tenants.daily_budget_aud_cents IS
    'KEI-212: daily $AUD-cents spend ceiling. NULL = unbounded (no warn). spend_tracker compares Valkey daily total against this and publishes a NATS warn when exceeded. LAW II.';

-- ============================================================
-- 3. budget_warn_audit — audit row when spend warn fires
-- ============================================================
CREATE TABLE IF NOT EXISTS public.budget_warn_audit (
    id                      bigserial   PRIMARY KEY,
    tenant_id               integer     NOT NULL REFERENCES public.tenants(id),
    daily_spend_aud_cents   bigint      NOT NULL,
    budget_aud_cents        bigint      NOT NULL,
    nats_published          boolean     NOT NULL DEFAULT false,
    created_at              timestamptz NOT NULL DEFAULT now()
);

COMMENT ON TABLE public.budget_warn_audit IS
    'KEI-212: audit trail for budget threshold breaches. One row per warn event. Warn-only stage — does not kill session. LAW II currency.';

CREATE INDEX IF NOT EXISTS budget_warn_audit_tenant_id_idx
    ON public.budget_warn_audit (tenant_id, created_at DESC);
