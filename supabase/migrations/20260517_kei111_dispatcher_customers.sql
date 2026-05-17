-- KEI-111: dispatcher_customers — root table for the customer-facing
-- Dispatcher product (Part 17). Maps 1:1 to Supabase auth.users; carries
-- the tenant tier + lifecycle metadata that downstream tables key off.
--
-- Why a separate table (not just auth.users):
--   - auth.users is Supabase-managed; we can't add columns there.
--   - Dispatcher needs tier + lifecycle state alongside auth identity.
--   - RLS policies (KEI-111E / KEI-149) need a tenant-scoped column to
--     filter against; a per-customer row provides the join target.
--
-- Namespaced `dispatcher_*` to avoid collision with:
--   - existing public.client_customers (internal CRM customers)
--   - existing public.customer_api_keys (Orion's KEI-116 BYO keys)

CREATE TABLE IF NOT EXISTS public.dispatcher_customers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    -- 1:1 link to Supabase Auth — populated when a user completes signup.
    supabase_user_id UUID UNIQUE NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    email TEXT NOT NULL,
    -- Tier name matches the DispatcherTier enum in the frontend
    -- (free | starter | growth | scale | enterprise). Stored as TEXT to
    -- keep the migration cheap; tighten to an enum in a sub-KEI when
    -- KEI-117C tier-limits-from-database lands.
    tier TEXT NOT NULL DEFAULT 'free',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    -- Soft delete so the BYO key + task history audit trail survives
    -- a customer leaving.
    deleted_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS dispatcher_customers_supabase_user_id_idx
    ON public.dispatcher_customers (supabase_user_id)
    WHERE deleted_at IS NULL;

CREATE INDEX IF NOT EXISTS dispatcher_customers_email_idx
    ON public.dispatcher_customers (email)
    WHERE deleted_at IS NULL;

COMMENT ON TABLE public.dispatcher_customers IS
    'KEI-111: Customer-facing Dispatcher product tenants. 1:1 with auth.users; carries tier + lifecycle state. Sub-KEI KEI-111E adds RLS policies.';
COMMENT ON COLUMN public.dispatcher_customers.tier IS
    'KEI-111: matches frontend DispatcherTier enum. Sub-KEI KEI-117C ties this to a tier_limits table.';
COMMENT ON COLUMN public.dispatcher_customers.deleted_at IS
    'KEI-111: soft delete; BYO key + task audit history survives the customer leaving.';
