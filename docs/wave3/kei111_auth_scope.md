# KEI-111 — Dispatcher Auth Layer: Scope + Scaffold

**Status:** Scaffold landed (this PR — `dispatcher_customers` table only). Sub-KEIs (KEI-111A/C/D/E) implement provisioning, magic-link flow, sessions, and RLS.
**Parent:** [KEI-110](https://linear.app/keiracom/issue/KEI-110) — Dispatcher Product Layer (Part 17).
**Authored by:** Scout · 2026-05-17.

## What this PR delivers

Foundational `public.dispatcher_customers` table that all downstream auth-keyed work hangs off:
- 1:1 link to `auth.users` (Supabase Auth-managed)
- `tier` (matches frontend `DispatcherTier` enum)
- Soft-delete lifecycle columns
- Two partial indexes (on `supabase_user_id` + `email`, scoped to non-deleted rows)

No auth flow code, no RLS policies, no API endpoints — those land in the sub-KEIs below.

## Why a separate table (not auth.users)

Supabase manages `auth.users` directly; we cannot add columns there. Dispatcher needs:
- Tier alongside identity (free/starter/growth/scale/enterprise)
- Soft-delete state so BYO key + task audit history survives a customer leaving
- A tenant-scoped column for RLS policies to filter against (`customer_id = current_dispatcher_customer_id()` shape)

The `dispatcher_customers` row is the join target between Supabase Auth identity and the dispatcher domain tables.

## Why `dispatcher_*` namespace

Avoids collision with:
- `public.client_customers` — internal Agency_OS CRM customers (existing)
- `public.customer_api_keys` — Orion's KEI-116 BYO API keys (PR #954)
- `public.tasks` — internal Agency_OS agent task queue (the one bd-claim uses)

The dispatcher product is customer-facing and isolated. Same reason `frontend/app/dispatcher/*` (PR #953) uses a path prefix instead of mixing with internal Agency_OS routes.

## Sub-KEI dependency graph

```
KEI-111A (KEI-145) Provision Supabase Auth tenant project + email templates
   │
   │  (manual ops: Supabase dashboard config — no code dep)
   ↓
KEI-111B (TBD)     Supabase client wrapper for dispatcher frontend
   │
   ├─→ KEI-111C (KEI-147) Magic link auth flow (no-password)
   │     │
   │     ↓
   │  KEI-111D (KEI-148) Session tokens + refresh + revoke cycle
   │     │
   │     ↓
   │  KEI-111E (KEI-149) RLS policies on customers + api_keys + tasks
   │
   └─→ KEI-113A (KEI-154) Signup UI (Part 17.3 — implements row INSERT)
```

**Build order** (so each sub-KEI claimer is unblocked):

1. **KEI-111A** ops setup — Supabase project, email templates. Manual + no code.
2. **dispatcher_customers** table (this PR) — gates everything keyed on tenant identity.
3. **KEI-111B** Supabase client wrapper at `frontend/lib/dispatcher/supabase.ts` — sub-KEI sketch:
   ```ts
   import { createBrowserClient } from "@supabase/ssr";
   export const dispatcherClient = () => createBrowserClient(
     process.env.NEXT_PUBLIC_DISPATCHER_SUPABASE_URL!,
     process.env.NEXT_PUBLIC_DISPATCHER_SUPABASE_ANON_KEY!,
   );
   ```
4. **KEI-111C** magic-link `auth.signInWithOtp({email, emailRedirectTo})` flow + verify-email page wiring (composes with PR #953 stub pages).
5. **KEI-111D** session middleware in `frontend/middleware.ts` — refresh on every request, revoke on `/api/dispatcher/auth/logout`.
6. **KEI-111E** RLS policies on three tables:
   - `dispatcher_customers` — `id = current_dispatcher_customer_id()` (own row only)
   - `customer_api_keys` (Orion's table — KEI-116) — `customer_id = current_dispatcher_customer_id()`
   - `public.tasks` — needs decision: namespace separately as `dispatcher_tasks`, or filter by a new `dispatcher_customer_id` column on `public.tasks`? Sub-KEI claimer makes the call after reading PR #953 scope doc.

## RLS pattern (target shape for KEI-111E)

```sql
-- Helper: returns the dispatcher_customers.id for the current session.
CREATE OR REPLACE FUNCTION public.current_dispatcher_customer_id()
RETURNS UUID LANGUAGE sql STABLE AS $$
  SELECT id FROM public.dispatcher_customers
   WHERE supabase_user_id = auth.uid()
     AND deleted_at IS NULL
$$;

ALTER TABLE public.dispatcher_customers ENABLE ROW LEVEL SECURITY;
CREATE POLICY dispatcher_customers_own_row ON public.dispatcher_customers
  USING (id = public.current_dispatcher_customer_id());

-- Sibling pattern for customer_api_keys + the dispatcher task table.
```

Acceptance test for KEI-111E (per Linear spec): "RLS enabled on customers + api_keys + tasks; integration test verifies user A can't read user B rows."

## Out of scope for this PR

- Any code — this PR is migration + scope doc only
- RLS policies (KEI-111E)
- Helper function `current_dispatcher_customer_id()` (lands with RLS)
- Tier enum tightening (waits for KEI-117C tier-limits table)
- The dispatcher tasks namespace decision

## Acceptance for this scaffold

- [x] `public.dispatcher_customers` table created with RLS-ready columns
- [x] FK to `auth.users` with `ON DELETE CASCADE` (auth user delete cascades to dispatcher row)
- [x] Soft-delete column + two partial indexes
- [x] Scope doc captures dep graph + RLS pattern target shape
- [x] All 4 named sub-KEIs (KEI-145/147/148/149) have a clear next-step from this foundation
- [x] No collision with existing `public.client_customers` / `public.customer_api_keys` / `public.tasks`

## Reference

- Parent: KEI-110 Dispatcher Product Layer (Linear)
- Sub-KEIs: KEI-145 (provision), KEI-147 (magic link), KEI-148 (session), KEI-149 (RLS)
- Sibling scaffolds: KEI-113 onboarding (PR #953), KEI-114 dashboard (Aiden), KEI-116 BYO keys (Orion PR #954)
- Frontend tier enum: `frontend/components/dispatcher/thread-usage-gauge.tsx#DispatcherTier`
