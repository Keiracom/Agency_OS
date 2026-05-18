-- KEI-210: interceptor_events — audit log for every model call routed through
-- the Dispatcher interceptor_proxy. Every decision (allow / deny_spend /
-- deny_rate_limit / deny_governance / error) gets a row, including denied
-- requests so the audit trail covers the rejection path too.
--
-- Companion to:
--   - dispatcher_customers (KEI-111) — tenant_id references that table
--   - governance_proxy.py (KEI-165) — emits deny_governance decisions
--   - valkey_pool.py (KEI-117A) — rate-limit + spend checks live on Valkey;
--     this table is the durable audit, Valkey is the hot path.

CREATE TABLE IF NOT EXISTS public.interceptor_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES public.dispatcher_customers(id) ON DELETE CASCADE,
    decision TEXT NOT NULL CHECK (decision IN (
        'allow',
        'deny_spend',
        'deny_rate_limit',
        'deny_governance',
        'error'
    )),
    -- Free-form reason (e.g. governance rule name, error message). Never
    -- contains prompt body — denial logs must not echo customer content
    -- per governance_proxy.py contract.
    reason TEXT,
    model TEXT,
    -- Token counts populated on 'allow' decisions only. NULL on denies.
    input_tokens INT,
    output_tokens INT,
    -- Spend accrued for this call in $AUD cents (LAW II). Integer to dodge
    -- float-rounding bugs at billing time.
    cost_cents_aud INT,
    -- End-to-end latency from interceptor entry to LiteLLM response.
    latency_ms INT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_interceptor_events_tenant_created
    ON public.interceptor_events (tenant_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_interceptor_events_decision
    ON public.interceptor_events (decision)
    WHERE decision <> 'allow';

COMMENT ON TABLE public.interceptor_events IS
    'KEI-210: audit log for every Dispatcher interceptor_proxy decision';
COMMENT ON COLUMN public.interceptor_events.cost_cents_aud IS
    '$AUD cents per LAW II — never USD';
