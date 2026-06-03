-- ============================================================================
-- 20260603_litellm_routing_proof_contract.sql
--
-- Bind the LIVE proof_gate_contract for gate_roadmap component litellm_routing
-- (id cb31edd9-3186-4685-a98f-56475d9e20ce, phase 4_infra) and stamp
-- built_by_callsign='atlas' so the attester!=builder gate is ARMED.
--
-- KEI: litellm_routing built->proven (Elliot dispatch 2026-06-03).
-- Decision A (Aiden, confirmed): proof target is RUNTIME-SRC governance-tier
--   routing — NOT the Claude-Code worker model. Opus workers run on Claude
--   Max OAuth and are never in the LiteLLM path (Dave 2026-05-20).
-- Decision B (Aiden AMEND (b), Tier-2; Max binding-attest): retrieval
--   DEFAULT_MODEL 'claude-haiku-4-5' -> 'governance_tier_fast' (this PR);
--   documented direct-API paths allowlisted (drevon_port_2026-05-11 +
--   Agency_OS-l6i2).
--
-- contract.cmd is the LIVE proof script. trg_01 Check A pins gate_proof_runs
-- .run_cmd to EXACTLY this string, so a pytest/mock run_cmd is refused
-- (the script's own C5 clause demonstrates that rejection against the live
-- trigger). expected_output_contains are the per-clause LITELLM_PROOF tokens
-- the script emits only after each assertion passes (Check B).
--
-- This migration does NOT flip status to 'proven'. status stays 'built';
-- Aiden+Max each run the script live and INSERT a binding_reviewer
-- gate_proof_runs row (exit_code=0, attesting_callsign in {aiden,max} != the
-- atlas builder), then the flip is performed against a pinned proof_run_id.
--
-- Inline post-condition self-test (Dave 2026-06-02 standing precedent):
-- migration apply ABORTS if the contract / built_by_callsign did not land.
-- ============================================================================

BEGIN;

-- Anti-spoof: explicit built_by_callsign must match the session-var caller.
SET LOCAL agency_os.callsign = 'atlas';

UPDATE public.gate_roadmap
   SET proof_gate_contract = '{
        "check_id": "litellm_routing_live_v1",
        "cmd": "bash scripts/proof_bar/litellm_routing_live_proof.sh",
        "expected_output_contains": [
            "LITELLM_PROOF: C1 live_governance_tier_call_traverses_proxy OK",
            "LITELLM_PROOF: C2 fail_closed_no_gateway OK",
            "LITELLM_PROOF: C3 governed_retrieval_http200_not_400 OK",
            "LITELLM_PROOF: C4 direct_anthropic_allowlist_only OK",
            "LITELLM_PROOF: C5 gov12_gate_teeth_live_rejection OK",
            "LITELLM_PROOF: COST cost_tracking_live OK",
            "LITELLM_PROOF: ALL PASS"
        ],
        "role_sep": {
            "builder": "atlas",
            "attester": ["aiden", "max"]
        },
        "negative_test_required": true
   }'::jsonb,
       built_by_callsign = 'atlas',
       notes = COALESCE(notes, '') || E'\n\n[atlas-litellm-routing-live-proof 2026-06-03] '
            || 'proof_gate_contract bound to scripts/proof_bar/'
            || 'litellm_routing_live_proof.sh (check_id litellm_routing_live_v1). '
            || 'Proof target corrected to runtime-src governance-tier routing '
            || '(Opus workers are on Claude Max OAuth, never in the proxy — Dave '
            || '2026-05-20). C3: retrieval DEFAULT_MODEL claude-haiku-4-5 -> '
            || 'governance_tier_fast. C4 allowlist = keyword_expander, vault '
            || 'cold_start, anthropic_batch, Stage7/10 AnthropicClient, plus '
            || 'intelligence.py + anthropic_rate_limit.py (discovered direct '
            || 'paths — flagged for binding ratification). COST proven at the '
            || 'proxy layer (x-litellm-response-cost); downstream '
            || 'infra_spend_metrics (KEI-212) not deployed here. built_by_'
            || 'callsign=atlas — attester must be aiden|max (!= builder).'
 WHERE id = 'cb31edd9-3186-4685-a98f-56475d9e20ce'::uuid;

-- ── Inline post-condition self-test — abort apply if the bind did not land ──
DO $self_test$
DECLARE
    v_cmd      text;
    v_builder  text;
    v_n_subs   int;
    v_status   text;
BEGIN
    SELECT proof_gate_contract->>'cmd',
           built_by_callsign,
           jsonb_array_length(proof_gate_contract->'expected_output_contains'),
           status
      INTO v_cmd, v_builder, v_n_subs, v_status
      FROM public.gate_roadmap
     WHERE id = 'cb31edd9-3186-4685-a98f-56475d9e20ce'::uuid;

    IF v_cmd IS DISTINCT FROM 'bash scripts/proof_bar/litellm_routing_live_proof.sh' THEN
        RAISE EXCEPTION 'self-test: contract.cmd did not bind (got %)', v_cmd
            USING ERRCODE = 'check_violation';
    END IF;
    IF v_builder IS DISTINCT FROM 'atlas' THEN
        RAISE EXCEPTION 'self-test: built_by_callsign not atlas (got %)', v_builder
            USING ERRCODE = 'check_violation';
    END IF;
    IF v_n_subs < 7 THEN
        RAISE EXCEPTION 'self-test: expected_output_contains has % substrings (<7)', v_n_subs
            USING ERRCODE = 'check_violation';
    END IF;
    -- Must remain 'built' — proven is the attesters' transition, not this PR's.
    IF v_status <> 'built' THEN
        RAISE EXCEPTION 'self-test: status is % (expected built — no laundering)', v_status
            USING ERRCODE = 'check_violation';
    END IF;
    RAISE NOTICE 'self-test OK: litellm_routing contract bound, built_by_callsign=atlas, status=built';
END
$self_test$;

COMMIT;
