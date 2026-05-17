-- KEI-180 Strangler Fig routing layer — per-tenant Model A/B traffic split.
-- Phase 0.5, P0. Author: MAX.
--
-- Adds use_model_b flag to client_customers (the canonical internal CRM table,
-- created in 030_customer_import.sql). Default false = all tenants stay on
-- Model A (the only live outreach path today; Model B dispatcher is standing up
-- per Scout KEI-111 foundation). The flag flips per-tenant as the cut-over
-- progresses:
--   use_model_b=false → POST /api/strangler/outreach proxies to Model A
--   use_model_b=true  → POST /api/strangler/outreach proxies to Model B
--                        dispatcher (DISPATCHER_URL env); fail-open to Model A
--                        on 5xx so no tenant is ever hard-blocked.
--
-- Strangler Fig semantics: this column is the ONLY mechanism that controls
-- which outreach path a tenant hits. Do NOT apply it to dispatcher_customers
-- (Scout KEI-111) — that is the Model B product layer, not the routing flag.

ALTER TABLE public.client_customers
    ADD COLUMN IF NOT EXISTS use_model_b BOOLEAN NOT NULL DEFAULT false;

COMMENT ON COLUMN public.client_customers.use_model_b IS
    'KEI-180 Strangler Fig: when true, outreach requests for this tenant are '
    'proxied to the Model B dispatcher service (DISPATCHER_URL). When false '
    '(default), requests hit the existing Model A internal outreach path. '
    'Flip per-tenant during cut-over; fail-open to Model A on dispatcher 5xx.';
