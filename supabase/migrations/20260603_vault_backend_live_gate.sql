-- 20260603_vault_backend_live_gate.sql
--
-- NOVA — vault_secrets SPLIT (Elliot ratify 2026-06-03).
--
-- The vault_secrets gate (id 00770e74) demands "zero env-var carve-outs; all
-- secrets Vault-resolved at spawn; git grep no hardcoded DSN/key in src/".
-- That is a security claim NOT yet true: 75 secret-shaped carve-outs still
-- resolve from .env. vault_secrets therefore stays not_started, and the
-- env-carve-out elimination is filed as a separate follow-up.
--
-- This migration seeds a NARROWER, honestly-provable gate: vault_backend_live
-- — the HashiCorp Vault is reachable, unsealed, and durably stores+retrieves a
-- secret asserted from the live server (real store/retrieve, not mock). Bound
-- to scripts/proof_bar/vault_secrets_live_roundtrip.sh. Does NOT flip status:
-- flip awaits Aiden + Max binding_reviewer proof_runs (attester != builder=nova).
--
-- Vault is EXISTING infra (VPS keiracom-vault-v1, unsealed/initialized) —
-- non-billable. No provisioning performed.

BEGIN;

SET LOCAL agency_os.callsign = 'nova';

INSERT INTO public.gate_roadmap (
    component, phase, gate_id, proof_gate, status,
    owner, built_by_callsign, required_attestation_kind, proof_gate_contract, notes
) VALUES (
    'vault_backend_live',
    '4_infra',
    'gate_vault_backend_live',
    'Live HashiCorp Vault is reachable, unsealed, and initialized, and durably '
      || 'stores then retrieves a secret asserted from the live server (real '
      || 'store/retrieve via KV v2, not a mock). NARROWER than vault_secrets '
      || '(zero env-var carve-outs), which remains not_started and is tracked '
      || 'separately — do NOT read this gate as "no secrets in env".',
    'built',
    'nova',
    'nova',
    'binding_reviewer',
    '{
        "check_id": "vault_backend_live_roundtrip_v1",
        "cmd": "bash scripts/proof_bar/vault_secrets_live_roundtrip.sh",
        "expected_output_contains": [
            "VAULT_LIVE_CONFIRMED=",
            "secret_readback_match=true",
            "NEG_SELFTEST_REJECTED_MISMATCH",
            "VAULT_ROUNDTRIP_OK"
        ],
        "role_sep": {"builder": "nova", "attester": ["aiden", "max"]},
        "negative_test_required": true
    }'::jsonb,
    'Split from vault_secrets (00770e74) per Elliot 2026-06-03. Proves the Vault '
      || 'secret backend is live; env-carve-out elimination is the remaining '
      || 'vault_secrets scope (75 carve-outs in .env) — separate follow-up KEI.'
)
ON CONFLICT (component) DO NOTHING;

COMMIT;

-- Flip (post dual-attest): Aiden + Max each run
--   bash scripts/proof_bar/vault_secrets_live_roundtrip.sh
-- in independent sessions -> binding_reviewer proof_runs, then
--   UPDATE public.gate_roadmap SET status='proven', proof_run_id=<run>
--     WHERE component='vault_backend_live';
-- fires trg_01 (A/B/C) + trg_11 (aiden+max) + trg_02 + trg_04 (attester != nova).
