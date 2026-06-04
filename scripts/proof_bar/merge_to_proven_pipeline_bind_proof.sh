#!/usr/bin/env bash
# merge_to_proven_pipeline_bind_proof.sh
#
# BIND-PROOF for gate_roadmap component merge_to_proven_pipeline.
# Spec: ceo:merge_to_proven_pipeline_guardrails. The rule is NOT live until its
# OWN bind-proof passes (GOV-12 — gates-as-code-not-comments).
#
# Proves the four-part rule with TWO planted negatives + TWO positive controls,
# all live (real CI gate script + real fn_verify_before_proven trigger):
#   N1  orphan merge -> CI BLOCKS: a planted migration that binds a component to
#       the proof path with NO deploy_trigger is rejected by
#       scripts/ci/check_no_orphan_merge.sh (exit 1).
#   N2  stale-SHA flip -> TRIGGER REJECTS: a transient component whose pinned
#       proof_run.repo_sha != running_sha cannot flip to proven —
#       fn_verify_before_proven Check D (sha_mismatch) raises. ROLLBACK.
#   P1  matched-SHA flip -> ALLOWED: same shape but repo_sha == running_sha and
#       a valid contract flips to proven (proves Check D is not always-reject).
#       ROLLBACK.
#   P2  wired merge -> CI PASSES: a planted migration that binds AND wires a
#       deploy_trigger passes the orphan gate (exit 0).
#
# Captures repo_sha = git rev-parse HEAD so the attester records a non-null
# repo_sha (R1) for this component's binding rows.
#
# Exit 0 = all four pass. Exit 2 = an assertion failed. Exit 3 = env error.
# ref: atlas-merge-to-proven-pipeline-bind-proof.

set -u

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT" || { echo "ERROR: cannot cd to repo root" >&2; exit 3; }

if [[ -z "${DATABASE_URL:-}" ]]; then
    if [[ -f /home/elliotbot/.config/agency-os/.env ]]; then
        set -a; # shellcheck disable=SC1091
        source /home/elliotbot/.config/agency-os/.env; set +a
    fi
fi
[[ -n "${DATABASE_URL:-}" ]] || { echo "ERROR: DATABASE_URL not set" >&2; exit 3; }
DSN="${DATABASE_URL//postgresql+asyncpg/postgresql}"
fail() { echo "BIND_PROOF: FAIL — $1" >&2; cleanup; exit 2; }

REPO_SHA="$(git rev-parse HEAD 2>/dev/null)"
[[ -n "$REPO_SHA" ]] || { echo "ERROR: git rev-parse HEAD failed" >&2; exit 3; }
echo "BIND_PROOF: repo_sha=$REPO_SHA"

TMPDIR_BP="$(mktemp -d)"
cleanup() { rm -rf "$TMPDIR_BP"; }
trap cleanup EXIT

# ── N1. Orphan merge -> CI orphan gate BLOCKS ───────────────────────────────
ORPHAN="$TMPDIR_BP/orphan_migration.sql"
cat > "$ORPHAN" <<'SQL'
-- planted ORPHAN fixture: binds the proof path but wires no deploy mechanism.
UPDATE public.gate_roadmap
   SET proof_gate_contract = '{"check_id":"planted_orphan","cmd":"bash x.sh","expected_output_contains":["X"],"role_sep":{"builder":"atlas","attester":["aiden","max"]}}'::jsonb
 WHERE component = 'planted_orphan_never_real';
SQL
N1_OUT="$(ORPHAN_CHECK_FILES="$ORPHAN" bash scripts/ci/check_no_orphan_merge.sh 2>&1)"; N1_RC=$?
echo "----- N1 orphan-gate output (rc=$N1_RC) -----"; echo "$N1_OUT"; echo "-----"
[[ "$N1_RC" -ne 0 ]] || fail "N1: orphan gate did NOT block a contract-bind with no deploy_trigger"
echo "$N1_OUT" | grep -qF "ORPHAN MERGE" || fail "N1: orphan gate blocked but without the ORPHAN MERGE diagnostic"
echo "BIND_PROOF: N1 orphan_merge_ci_blocks OK"

# ── P2. Wired merge -> CI orphan gate PASSES ────────────────────────────────
WIRED="$TMPDIR_BP/wired_migration.sql"
cat > "$WIRED" <<'SQL'
-- planted WIRED: binds a component to the proof path AND wires a deploy_trigger.
INSERT INTO public.gate_roadmap (component, deploy_trigger, proof_gate_contract)
VALUES ('planted_wired', 'manual_v1',
        '{"check_id":"planted_wired","cmd":"bash y.sh","expected_output_contains":["Y"],"role_sep":{"builder":"atlas","attester":["aiden","max"]}}'::jsonb);
SQL
P2_OUT="$(ORPHAN_CHECK_FILES="$WIRED" bash scripts/ci/check_no_orphan_merge.sh 2>&1)"; P2_RC=$?
echo "----- P2 orphan-gate output (rc=$P2_RC) -----"; echo "$P2_OUT"; echo "-----"
[[ "$P2_RC" -eq 0 ]] || fail "P2: orphan gate wrongly BLOCKED a properly-wired (deploy_trigger) bind"
echo "BIND_PROOF: P2 wired_merge_ci_passes OK"

# ── N2. Stale-SHA flip -> fn_verify_before_proven Check D REJECTS ────────────
N2_OUT="$(psql "$DSN" -v ON_ERROR_STOP=0 -X -P pager=off 2>&1 <<'SQL'
BEGIN;
DO $$
DECLARE v_gate uuid := gen_random_uuid(); v_session uuid := gen_random_uuid(); v_run uuid;
BEGIN
    SET LOCAL agency_os.callsign = 'atlas';
    INSERT INTO public.gate_roadmap
        (id, component, phase, subphase, proof_gate, status,
         required_attestation_kind, owner, running_sha, deployed_at)
    VALUES (v_gate, 'bindproof_N2_' || replace(v_gate::text,'-',''),
            '4_infra','gates','N2 transient','built','binding_reviewer','atlas',
            'RUNNING_SHA_AAA', now());
    INSERT INTO public.tool_call_log (callsign, session_uuid, tool_name, started_at)
    VALUES ('aiden', v_session, 'bindproof_n2', now());
    SET LOCAL agency_os.callsign = 'aiden';
    INSERT INTO public.gate_proof_runs
        (gate_roadmap_id, attestation_kind, run_cmd, run_output, output_sha256,
         exit_code, attesting_callsign, attester_session_uuid, repo_sha)
    VALUES (v_gate,'binding_reviewer','x','padded output to satisfy the >=32 length check ok',
            encode(sha256(v_gate::text::bytea),'hex'),0,'aiden',v_session::text,'PROOF_SHA_BBB')
    RETURNING id INTO v_run;
    SET LOCAL agency_os.callsign = 'dave';
    UPDATE public.gate_roadmap SET status='proven', proof_run_id=v_run WHERE id=v_gate;
    RAISE EXCEPTION 'N2 INTERNAL: stale-SHA flip was NOT blocked';
END $$;
ROLLBACK;
SQL
)"
echo "----- N2 trigger output -----"; echo "$N2_OUT"; echo "-----"
echo "$N2_OUT" | grep -qF "Check D (sha_mismatch)" || fail "N2: stale-SHA flip not rejected by Check D"
echo "BIND_PROOF: N2 stale_sha_flip_trigger_rejects OK"

# ── P1. Matched-SHA flip -> ALLOWED (Check D not always-reject) ──────────────
P1_OUT="$(psql "$DSN" -v ON_ERROR_STOP=0 -X -P pager=off 2>&1 <<'SQL'
BEGIN;
DO $$
DECLARE
    v_gate uuid := gen_random_uuid();
    v_sa uuid := gen_random_uuid();  -- aiden session
    v_sm uuid := gen_random_uuid();  -- max session
    v_run uuid; v_status text;
BEGIN
    SET LOCAL agency_os.callsign = 'atlas';
    INSERT INTO public.gate_roadmap
        (id, component, phase, subphase, proof_gate, proof_gate_contract, status,
         required_attestation_kind, owner, built_by_callsign, running_sha, deployed_at, deploy_trigger)
    VALUES (v_gate, 'bindproof_P1_' || replace(v_gate::text,'-',''),
            '4_infra','gates','P1 transient',
            '{"check_id":"p1","cmd":"echo bindproof-p1","expected_output_contains":["P1_SENTINEL"],"role_sep":{"builder":"atlas","attester":["aiden","max"]}}'::jsonb,
            'built','binding_reviewer','atlas','atlas','MATCH_SHA_ZZZ', now(), 'manual_v1');
    INSERT INTO public.tool_call_log (callsign, session_uuid, tool_name, started_at)
    VALUES ('aiden', v_sa, 'bindproof_p1_aiden', now()), ('max', v_sm, 'bindproof_p1_max', now());
    -- Both attesters (dual-attest) record a binding run against the MATCHED sha.
    SET LOCAL agency_os.callsign = 'aiden';
    INSERT INTO public.gate_proof_runs
        (gate_roadmap_id, attestation_kind, run_cmd, run_output, output_sha256,
         exit_code, attesting_callsign, attester_session_uuid, repo_sha)
    VALUES (v_gate,'binding_reviewer','echo bindproof-p1','output with P1_SENTINEL padded to >=32 chars ok',
            encode(sha256((v_gate::text||'aiden')::bytea),'hex'),0,'aiden',v_sa::text,'MATCH_SHA_ZZZ')
    RETURNING id INTO v_run;
    SET LOCAL agency_os.callsign = 'max';
    INSERT INTO public.gate_proof_runs
        (gate_roadmap_id, attestation_kind, run_cmd, run_output, output_sha256,
         exit_code, attesting_callsign, attester_session_uuid, repo_sha)
    VALUES (v_gate,'binding_reviewer','echo bindproof-p1','output with P1_SENTINEL padded to >=32 chars ok',
            encode(sha256((v_gate::text||'max')::bytea),'hex'),0,'max',v_sm::text,'MATCH_SHA_ZZZ');
    SET LOCAL agency_os.callsign = 'dave';
    UPDATE public.gate_roadmap SET status='proven', proof_run_id=v_run WHERE id=v_gate;
    SELECT status INTO v_status FROM public.gate_roadmap WHERE id=v_gate;
    IF v_status = 'proven' THEN
        RAISE NOTICE 'P1_FLIP_OK matched-SHA dual-attested flip reached proven';
    ELSE
        RAISE EXCEPTION 'P1 FAIL: status is % after matched-SHA flip', v_status;
    END IF;
END $$;
ROLLBACK;
SQL
)"
echo "----- P1 trigger output -----"; echo "$P1_OUT"; echo "-----"
echo "$P1_OUT" | grep -qF "P1_FLIP_OK" || fail "P1: matched-SHA flip did NOT reach proven (Check D over-blocking?)"
echo "BIND_PROOF: P1 matched_sha_flip_allowed OK"

echo "BIND_PROOF: run_nonce=$(date -u +%Y%m%dT%H%M%S.%N)"
echo "BIND_PROOF: ALL PASS"
exit 0
