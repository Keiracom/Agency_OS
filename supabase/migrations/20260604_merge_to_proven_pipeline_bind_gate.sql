-- ============================================================================
-- 20260604_merge_to_proven_pipeline_bind_gate.sql
--
-- The merge_to_proven_pipeline BIND-GATE. Makes the merge->proven rule LIVE.
-- Spec: ceo:merge_to_proven_pipeline_guardrails (dual-concur Aiden+Max).
-- Anchor: #1427 (proven-against-branch, not proven-against-deployed-SHA).
--
-- Exhibit A (Elliot verified): all 14 binding_reviewer proof_runs across the 7
-- proven components have NULL repo_sha — proof-PASSED but not SHA-anchored to
-- deployed code. This gate closes that gap going forward; SHA-backfill of the
-- existing 7 is SEPARATE downstream remediation (NOT this migration).
--
-- FOUR PARTS (= the rule proving itself):
--   R1  gate_proof_runs.repo_sha MANDATORY for binding_reviewer rows. Added
--       NOT VALID so the 14 legacy NULLs are grandfathered (backfill is
--       downstream) while every NEW binding row must carry repo_sha.
--   R2  deployed-state per component: running_sha + deployed_at (+ deploy_trigger
--       for the CI orphan gate). Manual stamp acceptable v1.
--   R3  fn_verify_before_proven Check D — a flip to proven requires deployed_at
--       present AND proof_run.repo_sha (non-null) == component.running_sha
--       (3-way match). Only fires on the OLD->proven transition, so the 7
--       already-proven rows are untouched.
--   (d) CI orphan gate is repo-side (scripts/ci/check_no_orphan_merge.sh) —
--       a migration that binds a proof contract must also wire a deploy_trigger.
--
-- Seeds the merge_to_proven_pipeline gate_roadmap component (status='built',
-- built_by_callsign='atlas') bound to the bind-proof script. status stays
-- 'built' — Aiden+Max dual-attest the flip (atlas is builder, cannot attest).
--
-- INLINE SELF-TESTS (Dave 2026-06-02 precedent): negative assertions that
-- self-rollback via caught exceptions (no persistent test rows). Migration
-- apply ABORTS if R1 or Check D fails to behave. Positive controls live in the
-- bind-proof harness (BEGIN/ROLLBACK), not here.
-- ============================================================================

BEGIN;
SET LOCAL agency_os.callsign = 'atlas';

-- ── R1 — repo_sha mandatory for binding_reviewer (NOT VALID: new rows only) ──
ALTER TABLE public.gate_proof_runs
    DROP CONSTRAINT IF EXISTS gate_proof_runs_repo_sha_binding_check;
ALTER TABLE public.gate_proof_runs
    ADD CONSTRAINT gate_proof_runs_repo_sha_binding_check
        CHECK (
            attestation_kind <> 'binding_reviewer'
            OR (repo_sha IS NOT NULL AND length(repo_sha) >= 7)
        ) NOT VALID;

-- ── R2 — deployed-state record per component ────────────────────────────────
ALTER TABLE public.gate_roadmap ADD COLUMN IF NOT EXISTS running_sha    text;
ALTER TABLE public.gate_roadmap ADD COLUMN IF NOT EXISTS deployed_at    timestamptz;
ALTER TABLE public.gate_roadmap ADD COLUMN IF NOT EXISTS deploy_trigger text;

-- ── R3 — fn_verify_before_proven + Check D (deployed-state + 3-way SHA) ──────
CREATE OR REPLACE FUNCTION public.fn_verify_before_proven()
RETURNS trigger LANGUAGE plpgsql AS $fn$
DECLARE
    v_contract       jsonb;
    v_run_cmd        text;
    v_run_output     text;
    v_attesting_cs   text;
    v_expected_cmd   text;
    v_expected_subs  text[];
    v_builder        text;
    v_substr         text;
    v_repo_sha       text;
BEGIN
    IF NEW.status = 'proven' AND (OLD.status IS NULL OR OLD.status IS DISTINCT FROM 'proven') THEN
        IF NEW.proof_run_id IS NULL THEN
            RAISE EXCEPTION
                'gate_roadmap proven-requires-proof-run: status=proven requires proof_run_id to pin which gate_proof_runs row justified the transition.'
                USING ERRCODE = 'check_violation';
        END IF;

        IF NOT EXISTS (
            SELECT 1 FROM public.gate_proof_runs
             WHERE id              = NEW.proof_run_id
               AND gate_roadmap_id = NEW.id
               AND exit_code       = 0
        ) THEN
            RAISE EXCEPTION
                'gate_roadmap proven-requires-proof-run: proof_run_id=% missing, not linked to gate_roadmap_id=%, or failed (exit_code != 0).',
                NEW.proof_run_id, NEW.id
                USING ERRCODE = 'check_violation';
        END IF;

        v_contract := NEW.proof_gate_contract;
        IF v_contract IS NOT NULL THEN
            SELECT run_cmd, run_output, attesting_callsign
              INTO v_run_cmd, v_run_output, v_attesting_cs
              FROM public.gate_proof_runs
             WHERE id = NEW.proof_run_id;

            v_expected_cmd  := v_contract->>'cmd';
            v_expected_subs := ARRAY(
                SELECT jsonb_array_elements_text(v_contract->'expected_output_contains')
            );
            v_builder       := v_contract->'role_sep'->>'builder';

            -- Check A — exact cmd match (superset_cmd vs cmd_mismatch).
            IF v_expected_cmd IS NULL OR v_expected_cmd = '' THEN
                RAISE EXCEPTION
                    'proof_gate_contract Check A (cmd_unset): contract.cmd is missing/empty for gate_roadmap_id=%.',
                    NEW.id USING ERRCODE = 'check_violation';
            END IF;
            IF v_run_cmd IS DISTINCT FROM v_expected_cmd THEN
                IF position(v_expected_cmd IN COALESCE(v_run_cmd, '')) > 0 THEN
                    RAISE EXCEPTION
                        'proof_gate_contract Check A (superset_cmd): gate_proof_runs.run_cmd=% contains but does not equal contract.cmd=% for gate_roadmap_id=%.',
                        v_run_cmd, v_expected_cmd, NEW.id USING ERRCODE = 'check_violation';
                ELSE
                    RAISE EXCEPTION
                        'proof_gate_contract Check A (cmd_mismatch): gate_proof_runs.run_cmd=% does not equal contract.cmd=% for gate_roadmap_id=%.',
                        v_run_cmd, v_expected_cmd, NEW.id USING ERRCODE = 'check_violation';
                END IF;
            END IF;

            -- Check B — every expected substring must appear in run_output.
            IF v_expected_subs IS NULL OR cardinality(v_expected_subs) = 0 THEN
                RAISE EXCEPTION
                    'proof_gate_contract Check B (no_expected_substrings): contract.expected_output_contains is empty for gate_roadmap_id=%.',
                    NEW.id USING ERRCODE = 'check_violation';
            END IF;
            FOREACH v_substr IN ARRAY v_expected_subs LOOP
                IF position(v_substr IN COALESCE(v_run_output, '')) = 0 THEN
                    RAISE EXCEPTION
                        'proof_gate_contract Check B (output_substring_missing): gate_proof_runs.run_output missing required substring "%" for gate_roadmap_id=%.',
                        v_substr, NEW.id USING ERRCODE = 'check_violation';
                END IF;
            END LOOP;

            -- Check C — attester != contract.role_sep.builder.
            IF v_builder IS NULL OR v_builder = '' THEN
                RAISE EXCEPTION
                    'proof_gate_contract Check C (builder_unset): contract.role_sep.builder is missing/empty for gate_roadmap_id=%.',
                    NEW.id USING ERRCODE = 'check_violation';
            END IF;
            IF v_attesting_cs = v_builder THEN
                RAISE EXCEPTION
                    'proof_gate_contract Check C (attester_eq_builder): gate_proof_runs.attesting_callsign=% matches contract.role_sep.builder=% for gate_roadmap_id=%.',
                    v_attesting_cs, v_builder, NEW.id USING ERRCODE = 'check_violation';
            END IF;
        END IF;

        -- Check D — deployed-state + 3-way SHA anchor (merge_to_proven_pipeline
        -- bind-gate). Applies to EVERY proven flip (independent of contract).
        -- Closes #1427: the pinned proof must have run against the deployed SHA.
        SELECT repo_sha INTO v_repo_sha
          FROM public.gate_proof_runs WHERE id = NEW.proof_run_id;

        IF NEW.deployed_at IS NULL THEN
            RAISE EXCEPTION
                'gate_roadmap Check D (deployed_at_unset): status=proven requires deployed_at (a recorded running deployment) for gate_roadmap_id=%.',
                NEW.id USING ERRCODE = 'check_violation';
        END IF;
        IF NEW.running_sha IS NULL OR NEW.running_sha = '' THEN
            RAISE EXCEPTION
                'gate_roadmap Check D (running_sha_unset): status=proven requires running_sha for gate_roadmap_id=%.',
                NEW.id USING ERRCODE = 'check_violation';
        END IF;
        IF v_repo_sha IS NULL OR v_repo_sha = '' THEN
            RAISE EXCEPTION
                'gate_roadmap Check D (proof_repo_sha_null): proof_run_id=% has NULL repo_sha — proof not SHA-anchored to deployed code (gate_roadmap_id=%).',
                NEW.proof_run_id, NEW.id USING ERRCODE = 'check_violation';
        END IF;
        IF v_repo_sha IS DISTINCT FROM NEW.running_sha THEN
            RAISE EXCEPTION
                'gate_roadmap Check D (sha_mismatch): proof_run.repo_sha=% != component.running_sha=% — proof ran against code that is not what is deployed (gate_roadmap_id=%).',
                v_repo_sha, NEW.running_sha, NEW.id USING ERRCODE = 'check_violation';
        END IF;

        SELECT run_at INTO NEW.last_verified
          FROM public.gate_proof_runs WHERE id = NEW.proof_run_id;
    END IF;
    RETURN NEW;
END;
$fn$;

-- ── Seed the merge_to_proven_pipeline component (built; attesters flip) ──────
-- Idempotent: skip if the component already exists (re-apply over already-
-- present prod, or a fresh-DB rebuild from migration history). Never seeds a
-- duplicate; never resets an already-proven row back to 'built'.
INSERT INTO public.gate_roadmap
    (id, component, phase, subphase, proof_gate, proof_gate_contract,
     status, required_attestation_kind, owner, built_by_callsign, deploy_trigger)
SELECT
    gen_random_uuid(),
    'merge_to_proven_pipeline', '4_infra', 'gates',
    'repo_sha mandatory for binding proofs; deployed-state (running_sha+deployed_at) recorded; fn_verify_before_proven enforces deployed_at + proof.repo_sha==running_sha (3-way); CI blocks orphan merges (component bound to proof path without a deploy_trigger). Both negatives proven live.',
    '{
        "check_id": "merge_to_proven_pipeline_bind_v1",
        "cmd": "bash scripts/proof_bar/merge_to_proven_pipeline_bind_proof.sh",
        "expected_output_contains": [
            "BIND_PROOF: N1 orphan_merge_ci_blocks OK",
            "BIND_PROOF: N2 stale_sha_flip_trigger_rejects OK",
            "BIND_PROOF: P1 matched_sha_flip_allowed OK",
            "BIND_PROOF: P2 wired_merge_ci_passes OK",
            "BIND_PROOF: ALL PASS"
        ],
        "role_sep": {"builder": "atlas", "attester": ["aiden", "max"]},
        "negative_test_required": true
    }'::jsonb,
    'built', 'binding_reviewer', 'elliot', 'atlas',
    'migration:20260604_merge_to_proven_pipeline_bind_gate.sql + ci:check_no_orphan_merge + proof_bar:merge_to_proven_pipeline_bind_proof.sh'
WHERE NOT EXISTS (
    SELECT 1 FROM public.gate_roadmap WHERE component = 'merge_to_proven_pipeline'
);

-- ============================================================================
-- INLINE SELF-TESTS (negative; self-rollback via caught exceptions)
-- ============================================================================

-- ST1 — binding_reviewer proof_run with NULL repo_sha must be REJECTED (R1).
DO $st1$
DECLARE v_gate uuid := gen_random_uuid(); v_session uuid := gen_random_uuid();
BEGIN
    BEGIN
        SET LOCAL agency_os.callsign = 'atlas';
        INSERT INTO public.gate_roadmap
            (id, component, phase, subphase, proof_gate, status,
             required_attestation_kind, owner)
        VALUES (v_gate, 'ST1_repo_sha_' || replace(v_gate::text,'-',''),
                '0_foundation','gates','ST1 transient','built','binding_reviewer','atlas');
        INSERT INTO public.tool_call_log (callsign, session_uuid, tool_name, started_at)
        VALUES ('aiden', v_session, 'st1_probe', now());
        SET LOCAL agency_os.callsign = 'aiden';
        INSERT INTO public.gate_proof_runs
            (gate_roadmap_id, attestation_kind, run_cmd, run_output, output_sha256,
             exit_code, attesting_callsign, attester_session_uuid, repo_sha)
        VALUES (v_gate,'binding_reviewer','x','padded output to satisfy the >=32 length check here ok',
                encode(sha256(v_gate::text::bytea),'hex'),0,'aiden',v_session::text, NULL);
        RAISE EXCEPTION 'ST1 FAIL: NULL repo_sha binding_reviewer row was accepted';
    EXCEPTION WHEN check_violation THEN
        IF SQLERRM LIKE '%ST1 FAIL%' THEN RAISE; END IF;
        RAISE NOTICE 'ST1 OK: NULL repo_sha binding row rejected (%)', left(SQLERRM, 60);
    END;
END $st1$;

-- ST2 — stale-SHA flip must be REJECTED by Check D (sha_mismatch).
DO $st2$
DECLARE v_gate uuid := gen_random_uuid(); v_session uuid := gen_random_uuid(); v_run uuid;
BEGIN
    BEGIN
        SET LOCAL agency_os.callsign = 'atlas';
        INSERT INTO public.gate_roadmap
            (id, component, phase, subphase, proof_gate, status,
             required_attestation_kind, owner, running_sha, deployed_at)
        VALUES (v_gate, 'ST2_staleSHA_' || replace(v_gate::text,'-',''),
                '0_foundation','gates','ST2 transient','built','binding_reviewer','atlas',
                'aaaaaaa_running', now());
        INSERT INTO public.tool_call_log (callsign, session_uuid, tool_name, started_at)
        VALUES ('aiden', v_session, 'st2_probe', now());
        SET LOCAL agency_os.callsign = 'aiden';
        INSERT INTO public.gate_proof_runs
            (gate_roadmap_id, attestation_kind, run_cmd, run_output, output_sha256,
             exit_code, attesting_callsign, attester_session_uuid, repo_sha)
        VALUES (v_gate,'binding_reviewer','x','padded output to satisfy the >=32 length check here ok',
                encode(sha256(v_gate::text::bytea),'hex'),0,'aiden',v_session::text, 'bbbbbbb_proof')
        RETURNING id INTO v_run;
        SET LOCAL agency_os.callsign = 'dave';
        UPDATE public.gate_roadmap SET status='proven', proof_run_id=v_run WHERE id=v_gate;
        RAISE EXCEPTION 'ST2 FAIL: stale-SHA flip was accepted';
    EXCEPTION WHEN check_violation THEN
        IF SQLERRM LIKE '%ST2 FAIL%' THEN RAISE; END IF;
        IF SQLERRM NOT LIKE '%Check D (sha_mismatch)%' THEN
            RAISE EXCEPTION 'ST2 FAIL: wrong rejection reason: %', SQLERRM;
        END IF;
        RAISE NOTICE 'ST2 OK: stale-SHA flip rejected by Check D';
    END;
END $st2$;

COMMIT;
