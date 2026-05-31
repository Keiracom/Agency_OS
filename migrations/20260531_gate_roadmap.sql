-- gate_roadmap: V2 roadmap proof-gate component registry
-- Dave directive 2026-05-31 — schema approved verbatim by Elliot dispatch
-- Renamed from gate_ledger 2026-05-31 (Aiden architecture decision) to avoid
-- collision with Atlas PR #1371 gate_ledger (CI execution log, different schema).
-- Write contract: CI gates UPDATE status='proven', last_verified=now() WHERE gate_id='<id>'.
-- Status moves forward only; a gate cannot un-prove a row.

CREATE TABLE IF NOT EXISTS public.gate_roadmap (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    component     TEXT NOT NULL,
    phase         TEXT NOT NULL,
    subphase      TEXT,
    proof_gate    TEXT NOT NULL,
    gate_id       TEXT,
    status        TEXT NOT NULL DEFAULT 'not_started'
                  CHECK (status IN ('not_started','built','proven','skipped','deferred')),
    owner         TEXT,
    kei_link      TEXT,
    blocker_text  TEXT,
    notes         TEXT,
    last_verified TIMESTAMPTZ,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS gate_roadmap_gate_id_idx
    ON public.gate_roadmap (gate_id) WHERE gate_id IS NOT NULL;

CREATE OR REPLACE FUNCTION public.touch_gate_roadmap()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS gate_roadmap_updated_at ON public.gate_roadmap;
CREATE TRIGGER gate_roadmap_updated_at
    BEFORE UPDATE ON public.gate_roadmap
    FOR EACH ROW EXECUTE FUNCTION public.touch_gate_roadmap();

-- Seed data: 12 rows covering Phase 0 (closed) + Phase 1-4 (open)

-- Phase 0 — proven 2026-05-31
INSERT INTO public.gate_roadmap (component, phase, gate_id, proof_gate, status, owner, notes, last_verified)
VALUES (
    'gate_mechanism', 'phase_0', 'gate_phase0_mechanism',
    'Gate mechanism exists; Phase 0 gates fire pass/fail in CI; rc=0 pass, rc=1 fail, rc=2 skip-tolerated-if-component-absent',
    'proven', 'elliot',
    'CLOSED per Dave 2026-05-31. skip-to-enforced rule ratified.',
    now()
);

-- Phase 1
INSERT INTO public.gate_roadmap (component, phase, gate_id, proof_gate, status, owner, notes) VALUES
('temporal_chain', 'phase_1', 'gate_temporal_chain_e2e',
 'Temporal workflow + activities run end-to-end on VPS; crash recovery verified; chain restarts from last completed activity after kill -9',
 'not_started', 'aiden',
 'Riskiest-first per Dave. Custom dispatcher deleted on pass.'),
('dispatcher_retirement', 'phase_1', 'gate_dispatcher_retired',
 'src/dispatcher/, v1_chain_orchestrator, reconcile/lease/dead-letter code deleted; CI passes with no imports or references remaining',
 'not_started', 'aiden', NULL);

-- Phase 2
INSERT INTO public.gate_roadmap (component, phase, gate_id, proof_gate, status, owner, notes, blocker_text) VALUES
('vault_secrets', 'phase_2', 'gate_vault_secrets',
 'Zero env-var carve-outs remain; all secrets Vault-resolved at spawn; git grep confirms no hardcoded DSN or API key in src/',
 'not_started', 'max', NULL, NULL),
('litellm_routing', 'phase_2', 'gate_litellm_routing',
 'All LLM API calls route via LiteLLM proxy; no direct anthropic SDK imports in runtime src/; cost tracking live',
 'not_started', 'max', NULL, NULL),
('postgres_self_hosted', 'phase_2', 'gate_postgres_self_hosted',
 'Supabase fully retired; all platform tables (ceo_memory, CIS, pipeline, client data, agent memories, chain state) in self-hosted Postgres on existing VPS; backup + restore proven before first client data row moves',
 'not_started', 'aiden',
 'R2 offsite backup required hard gate before client data migrates. Dual-write during transition.',
 NULL),
('gate_roadmap_migration', 'phase_2', 'gate_roadmap_self_hosted',
 'gate_roadmap table migrated to self-hosted Postgres; CI gates still write status=proven correctly after migration',
 'not_started', 'elliot',
 'META: the registry tracks its own migration. Cannot be the one thing forgotten during the Supabase cutover.',
 'Blocked on postgres_self_hosted completing first'),
('roadmap_doc_relocation', 'phase_2', 'gate_roadmap_doc_relocated',
 'docs/ROADMAP_V2.md moved to the isolated product repo; fleet repo contains a pointer only',
 'not_started', 'elliot',
 'META: SSOT must live with what it describes. Dave call 2026-05-31.',
 'Blocked on isolated repo creation (Phase 2.0)');

-- Phase 3
INSERT INTO public.gate_roadmap (component, phase, gate_id, proof_gate, status, owner) VALUES
('atom_capture', 'phase_3', 'gate_atom_capture',
 'Atoms write correctly across all chain hops; zero dropped atoms in validation run; keiracom_atoms rows verifiable per hop',
 'not_started', 'nova'),
('atom_recall', 'phase_3', 'gate_atom_recall',
 'Recall returns real signal (relevance_score > 0.0) from Hindsight banks populated with V2 session data; live chain hit confirmed in attribution log',
 'not_started', 'nova');

-- Phase 4
INSERT INTO public.gate_roadmap (component, phase, gate_id, proof_gate, status, owner) VALUES
('nova_commits', 'phase_4', 'gate_nova_commits',
 'Nova pushes a passing commit (all tests green) within a chain activity; git credentials Vault-resolved; commit appears on correct branch',
 'not_started', 'nova'),
('failure_notification', 'phase_4', 'gate_failure_notification',
 'Stalled or failed chain surfaces to Dave within 5 minutes via Slack #ceo; no silent hangs in a 30-minute soak test',
 'not_started', 'elliot');
