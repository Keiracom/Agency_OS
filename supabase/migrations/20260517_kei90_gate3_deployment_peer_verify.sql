-- KEI-90 — Gate 3: peer-verify on deployment-class KEIs (KEI-128 Phase 0.5).
--
-- Adds public.tasks.deployment (boolean default false). When true, bd
-- complete additionally requires --verifier <callsign> with verifier ≠
-- builder AND verifier's session_uuid ≠ builder's session_uuid. The
-- session_uuid independence check uses Gate 2's evidence schema (already
-- enforces verifier_session_uuid as a required field via KEI-89).
--
-- Backfill: mark the known operational-deployment KEIs (install systemd
-- unit / set env / restart service shape) as deployment=true. List is
-- derived from today's audit sweeps (KEI-108 + KEI-32) — install
-- references for systemd units + Railway env-set work + webhook router
-- registration. Going forward, deployment=true is set explicitly on
-- KEIs filed under the operational-deployment label.

ALTER TABLE public.tasks
  ADD COLUMN IF NOT EXISTS deployment boolean DEFAULT false NOT NULL;

-- Backfill known operational KEIs (Phase 0 + 0.5 remediation set).
-- Memory + observability install: KEI-45/66 (false-complete remediations)
-- + KEI-86 (phase-lock) + KEI-91 (Gate 4 heartbeat) + KEI-92 (self-claim)
-- + KEI-93 (reset handler) + KEI-100 (LiteLLM gateway) + KEI-101 (Valkey).
-- KEI-87 (cross-cutting write-guard) DOES involve a migration but ships
-- the trigger; the actual deploy-step is the apply_migration follow-up,
-- which is a deployment-class task.
UPDATE public.tasks SET deployment = true
 WHERE id IN (
   'KEI-45', 'KEI-66', 'KEI-86', 'KEI-87', 'KEI-91', 'KEI-92', 'KEI-93',
   'KEI-100', 'KEI-101'
 );

COMMENT ON COLUMN public.tasks.deployment IS
  'KEI-90 Gate 3 flag — true means bd complete requires --verifier ≠ builder with session_uuid independence (KEI-89 evidence schema cross-check). Dave-solo-ops 2-of-3 path applies when builder.callsign=dave.';
