# Tenant Isolation — KEI-181

**Phase:** 0.5 (Foundation)
**Priority:** P0
**Author:** MAX
**Date:** 2026-05-17

## Model

Single Supabase project. All tenants share the same schema, same Fleet Supervisor, and same dashboard. Every work-table row carries a `tenant_id INTEGER NOT NULL DEFAULT 1` foreign-keyed to `public.tenants`.

| tenant_id | Who |
|---|---|
| 1 | Dave / Agency_OS internal (default) |
| 2+ | Paying customers |

Row-Level Security on every work table scopes `SELECT / INSERT / UPDATE / DELETE` to the session's declared tenant.

## Tables with tenant_id + RLS

- `public.tasks`
- `public.tool_call_log`
- `public.retrieval_events`
- `public.task_verifications`
- `public.ceo_memory`
- `public.agent_memories`
- `public.completion_sync_queue`
- `public.tenants` (new registry table — no RLS needed, append-only by admins)

## RLS Policy Shape (3-clause)

```sql
USING (
    current_setting('agency_os.tenant_id', true)::integer = tenant_id  -- normal caller
    OR current_setting('role', true) = 'service_role'                   -- backend daemons / Fleet Supervisor
    OR current_setting('agency_os.tenant_id', true) IS NULL             -- daemon hasn't set var yet
)
```

Identical expression in `WITH CHECK`.

**Clause 1** — anon/authenticated callers (customer dashboard via supabase-js anon key) must call `set_tenant_session()` before any query. The session var gates visibility.

**Clause 2** — Supabase service-role key sets `role = service_role` automatically. Fleet Supervisor, `completion_sync_worker`, and every backend daemon use this path. No `set_tenant_session()` call needed.

**Clause 3** — defensive: if a backend daemon connects with service-role and the var happens to be unset, it still passes. Belt-and-braces.

## Helper API

```python
from src.integrations.supabase import set_tenant_session

# Customer dashboard flow (must be called early in request lifecycle):
await set_tenant_session(tenant_id=customer_id, connection=db_session)

# Service-role daemons skip this entirely — RLS clause 2 passes automatically.
```

Source: `src/integrations/supabase.py:set_tenant_session`

### Errors

- `ValueError` — `tenant_id` not a positive integer.
- `IntegrationError` — DB execute failure.

## Migration

`supabase/migrations/20260517_kei181_tenant_id_foundation.sql`

Idempotent. Applied by Dave via Supabase MCP `apply_migration` after PR merges.
Steps: CREATE TABLE tenants → seed Dave row → ADD COLUMN on 7 tables → backfill → indexes → ENABLE RLS → DROP/CREATE policies → COMMENT.

## Out of Scope (KEI-181)

- Per-tenant Paddle billing (KEI-150 / Phase 2)
- Per-tenant dashboard UI
- Per-tenant queue scoping in `fleet_supervisor.py`
- Customer signup flow

## Cross-References

- **KEI-180** — Strangler-fig architecture (single system, tenant isolation strategy decision)
- **KEI-111** — `dispatcher_customers` table (per-tenant outreach config, builds on this foundation)
- `supabase/migrations/20260517_kei181_tenant_id_foundation.sql` — full migration
- `src/integrations/supabase.py` — `set_tenant_session` helper
- `tests/integration/test_tenant_isolation.py` — two-session isolation proof
