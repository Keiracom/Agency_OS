-- scripts/insert_system_pipeline_client.sql
--
-- E1 cost instrumentation prerequisite (per PHASE_1_KICKOFF 2026-05-08).
--
-- Inserts the SystemPipelineClient sentinel row that pipeline cost-logging
-- (`src/pipeline/intelligence.py:_log_anthropic_call_to_sdk_usage`) writes
-- against. Required because `sdk_usage_log.client_id` is NOT NULL with a
-- FK constraint to `clients.id`, but pipeline runs against business_universe
-- domains (pre-customer) — no natural client_id at AI call sites.
--
-- IDEMPOTENT: ON CONFLICT DO NOTHING. Safe to re-run.
--
-- CASCADE FOOTGUN: sdk_usage_log.client_id FK is ON DELETE CASCADE. If
-- anyone DELETEs this row, every sdk_usage_log row referencing it goes
-- too. Helper has a pre-write existence guard that refuses to write if
-- this row is missing rather than 500 on FK violation. Operationally:
-- never delete this row unless you're truncating sdk_usage_log first.
--
-- Run once before any pipeline AI call:
--   psql $DATABASE_URL -f scripts/insert_system_pipeline_client.sql
--
-- Or via supabase MCP execute_sql tool with the body below.

INSERT INTO public.clients (id, name, deposit_paid, created_at, updated_at)
VALUES (
    '00000000-0000-0000-0000-000000000001'::uuid,
    'SystemPipelineClient (E1 sentinel)',
    false,
    NOW(),
    NOW()
)
ON CONFLICT (id) DO NOTHING;

-- Verify insert landed (or pre-existed):
SELECT id, name, created_at FROM public.clients
WHERE id = '00000000-0000-0000-0000-000000000001'::uuid;
