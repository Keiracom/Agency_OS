-- KEI-111E: Row-level security on customer-facing Dispatcher tables.
-- Author: ORION (Linear KEI-149 / bd Agency_OS-fd3fsr)
-- Idempotent: safe to re-run.
-- Tables touched: public.dispatcher_customers, public.customer_api_keys
--
-- Rationale:
--   * dispatcher_customers (KEI-111) is the per-customer root row for the
--     customer-facing Dispatcher product. Multiple customers share the table;
--     a customer must not be able to read another customer's row.
--   * customer_api_keys (KEI-116) stores encrypted BYO API keys keyed by
--     customer_id. Same isolation requirement — and the consequence of a
--     leak here is far worse (decryption key compromise → cross-tenant
--     key exposure).
--   * The 3rd "tasks" table named in the KEI-111E spec is already covered
--     by KEI-181's tenant_isolation_tasks policy (PR shipped 2026-05-17).
--     This migration covers the remaining two.
--
-- Policy shape mirrors KEI-181 — session-local var, service-role bypass,
-- null-var bypass for backend daemons that have not yet set the var.
-- The var name here is `agency_os.dispatcher_user_id` (UUID) rather than
-- `agency_os.tenant_id` (integer) because dispatcher_customers is keyed by
-- supabase_user_id (the auth.users UUID), not by the integer tenant_id
-- foundation.

-- ============================================================
-- 1. Enable RLS on both tables (idempotent)
-- ============================================================

ALTER TABLE public.dispatcher_customers ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.customer_api_keys    ENABLE ROW LEVEL SECURITY;

-- ============================================================
-- 2. Policies on public.dispatcher_customers
-- ============================================================
-- A row is visible when ANY of:
--   1. session var agency_os.dispatcher_user_id matches the row's
--      supabase_user_id  (normal customer-authenticated callers)
--   2. current_setting('role') = 'service_role'  (Supabase service-role key)
--   3. agency_os.dispatcher_user_id IS NULL  (backend daemons that
--      have not set the var — same bypass shape as KEI-181 keeps
--      legacy callers working until they switch to set-the-var)

DROP POLICY IF EXISTS tenant_isolation_dispatcher_customers ON public.dispatcher_customers;
CREATE POLICY tenant_isolation_dispatcher_customers ON public.dispatcher_customers
    FOR ALL
    USING (
        current_setting('agency_os.dispatcher_user_id', true)::uuid = supabase_user_id
        OR current_setting('role', true) = 'service_role'
        OR current_setting('agency_os.dispatcher_user_id', true) IS NULL
    )
    WITH CHECK (
        current_setting('agency_os.dispatcher_user_id', true)::uuid = supabase_user_id
        OR current_setting('role', true) = 'service_role'
        OR current_setting('agency_os.dispatcher_user_id', true) IS NULL
    );

-- ============================================================
-- 3. Policies on public.customer_api_keys
-- ============================================================
-- customer_api_keys.customer_id references dispatcher_customers.id (per
-- application-layer convention — there is no FK in the table definition
-- because the table was created before dispatcher_customers existed). The
-- RLS policy resolves the chain: row visible iff customer_id belongs to
-- the dispatcher_customers row matching the session user.

DROP POLICY IF EXISTS tenant_isolation_customer_api_keys ON public.customer_api_keys;
CREATE POLICY tenant_isolation_customer_api_keys ON public.customer_api_keys
    FOR ALL
    USING (
        customer_id IN (
            SELECT id FROM public.dispatcher_customers
            WHERE supabase_user_id = current_setting('agency_os.dispatcher_user_id', true)::uuid
        )
        OR current_setting('role', true) = 'service_role'
        OR current_setting('agency_os.dispatcher_user_id', true) IS NULL
    )
    WITH CHECK (
        customer_id IN (
            SELECT id FROM public.dispatcher_customers
            WHERE supabase_user_id = current_setting('agency_os.dispatcher_user_id', true)::uuid
        )
        OR current_setting('role', true) = 'service_role'
        OR current_setting('agency_os.dispatcher_user_id', true) IS NULL
    );

COMMENT ON POLICY tenant_isolation_dispatcher_customers ON public.dispatcher_customers IS
    'KEI-111E: per-customer isolation via agency_os.dispatcher_user_id session var. Service-role + null-var bypass for backend daemons.';
COMMENT ON POLICY tenant_isolation_customer_api_keys ON public.customer_api_keys IS
    'KEI-111E: chained isolation via dispatcher_customers join on supabase_user_id. Service-role + null-var bypass for backend.';
