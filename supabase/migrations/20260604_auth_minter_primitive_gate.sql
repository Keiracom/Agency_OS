-- 20260604_auth_minter_primitive_gate.sql
--
-- NOVA — parallel provable item during the reboot pause (Elliot dispatch).
-- Honest split (mirrors vault_backend_live): seed a NARROW, cleanly-provable gate
-- for the auth_minter PRIMITIVE and leave the broad auth_minter gate unproven.
--
-- WHY A SPLIT: the broad gate auth_minter requires "JWT minted per agent session,
-- validated on EVERY dispatcher call". That integration is UNWIRED — dispatcher
-- main.py imports auth_minter only for a boot-time DISPATCHER_JWT_SECRET env-check
-- (L35 "imported for fail-fast side-effect"); verify_token/mint_token have ZERO
-- call sites on the request path. So the broad gate is NOT met and stays as-is.
--
-- This narrow gate proves what auth_minter actually OWNS and what works live:
-- mint a short-lived HS256 session JWT + verify + REJECT expired/tampered/
-- wrong-secret/blank, with the real DISPATCHER_JWT_SECRET against a live agent
-- session. Clear of exclusions (no DB/Valkey/NATS/model-routing, no reboot dep).
--
-- built_by_callsign='nova' = proof-stager (for attest role-separation; the KEI-209
-- component code predates nova). Does NOT flip status — flip awaits Aiden+Max
-- binding_reviewer proof_runs (attester != nova).

BEGIN;

SET LOCAL agency_os.callsign = 'nova';

INSERT INTO public.gate_roadmap (
    component, phase, gate_id, proof_gate, status,
    owner, built_by_callsign, required_attestation_kind, proof_gate_contract,
    deploy_trigger, notes
) VALUES (
    'auth_minter_primitive',
    '1_nucleus',
    'gate_auth_minter_primitive',
    'auth_minter mints a short-lived (15-min TTL) HS256 agent-session JWT '
      || '(tenant+callsign+session) and verify_token accepts it, and REJECTS '
      || 'expired / tampered / wrong-secret / blank-field tokens — proven LIVE '
      || 'with the real DISPATCHER_JWT_SECRET against a live agent session. '
      || 'NARROWER than auth_minter: the "validated on every dispatcher call" '
      || 'integration is UNWIRED (verify_token has no request-path call site) and '
      || 'remains not_started — do NOT read this as "dispatcher enforces auth".',
    'built',
    'nova',
    'nova',
    'binding_reviewer',
    '{
        "check_id": "auth_minter_primitive_live_v1",
        "cmd": "bash scripts/proof_bar/auth_minter_live.sh",
        "expected_output_contains": [
            "AUTH_MINT_VERIFY_OK",
            "EXPIRED_REJECTED",
            "TAMPERED_REJECTED",
            "WRONGSECRET_REJECTED",
            "BLANK_REJECTED",
            "AUTH_MINTER_PRIMITIVE_PROOF_OK"
        ],
        "role_sep": {"builder": "nova", "attester": ["aiden", "max"]},
        "negative_test_required": true
    }'::jsonb,
    'migration:supabase/migrations/20260604_auth_minter_primitive_gate.sql'
      || ' + ci:check_no_orphan_merge + proof_bar:scripts/proof_bar/auth_minter_live.sh',
    'SCOPE (attesters check THIS, not full integration): proven=auth_minter '
      || 'PRIMITIVE; dispatcher-integration clause ("validated on every dispatcher '
      || 'call") DEFERRED to post-reboot/launcher-live — broad auth_minter gate '
      || 'stays not_started. built_by=nova (proof-stager; KEI-209 code predates '
      || 'nova). Broad auth_minter owner=atlas is UNCONTESTED (atlas is '
      || 'reboot-driver/validator, not working auth_minter) — no collision. '
      || 'RELATED FINDING (same class): spend_tracker gate says "over-budget '
      || 'rejected end-to-end" but record() is WARN-ONLY (KEI-212 spec). Both '
      || 'nucleus components have correct primitives, unwired enforcement.'
)
ON CONFLICT (component) DO UPDATE SET
    deploy_trigger = EXCLUDED.deploy_trigger,
    proof_gate_contract = EXCLUDED.proof_gate_contract,
    notes = EXCLUDED.notes;

COMMIT;
