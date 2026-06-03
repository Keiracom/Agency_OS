-- 20260603_postgres_self_hosted_proof_gate.sql
--
-- NOVA — postgres_self_hosted built->proven prep (gate id 5cb0d0de).
--
-- Sets the proof_gate_contract + stamps built_by_callsign='nova' on the live
-- gate_roadmap row for component=postgres_self_hosted. Does NOT flip status:
-- the flip happens only after the LIVE proof runs against the self-hosted
-- (Vultr) Postgres and Aiden + Max each record a binding_reviewer proof_run.
--
-- Scope (ratified Dave/Elliot 2026-06-03): this gate proves the self-hosted
-- instance is REAL, reachable, and durably writable (live connect + write +
-- read-back + assert). It does NOT cover Supabase decommission or
-- backup/restore — that is the separate R2 offsite-backup hard gate (KEI-242),
-- tracked independently. proof_gate wording is narrowed here to match.
--
-- The contract.cmd binds to scripts/proof_bar/postgres_self_hosted_live_roundtrip.sh.
-- expected_output_contains are substrings that ONLY a live roundtrip against a
-- non-Supabase host can produce (LIVE_HOST_CONFIRMED + sentinel_readback_match
-- + LIVE_ROUNDTRIP_OK) — a mock / pytest-only run cannot satisfy them.

BEGIN;

-- Stamp the builder (idempotent — only if not already set).
SET LOCAL agency_os.callsign = 'nova';
UPDATE public.gate_roadmap
   SET built_by_callsign = 'nova'
 WHERE id = '5cb0d0de-6aae-4e85-92e0-8fadddc1d7f3'
   AND component = 'postgres_self_hosted'
   AND built_by_callsign IS NULL;

-- Set the proof contract + narrow the proof_gate to the live-roundtrip scope.
UPDATE public.gate_roadmap
   SET proof_gate = 'Self-hosted Postgres on the Vultr VPS is real, reachable, '
                 || 'and durably writable: a live connection performs a real '
                 || 'write + read-back + assert against the live server (not a '
                 || 'mock). Supabase decommission + backup/restore are the '
                 || 'separate R2 offsite-backup hard gate (KEI-242).',
       proof_gate_contract = '{
            "check_id": "postgres_self_hosted_live_roundtrip_v1",
            "cmd": "bash scripts/proof_bar/postgres_self_hosted_live_roundtrip.sh",
            "expected_output_contains": [
                "LIVE_HOST_CONFIRMED=",
                "sentinel_readback_match=true",
                "LIVE_ROUNDTRIP_OK"
            ],
            "role_sep": {"builder": "nova", "attester": ["aiden", "max"]},
            "negative_test_required": true
        }'::jsonb,
       required_attestation_kind = 'binding_reviewer'
 WHERE id = '5cb0d0de-6aae-4e85-92e0-8fadddc1d7f3'
   AND component = 'postgres_self_hosted';

COMMIT;

-- NOTE: status flip is performed AFTER the live proof + dual attestation:
--   1. Aiden runs `bash scripts/proof_bar/postgres_self_hosted_live_roundtrip.sh`
--      in his own session against VULTR_POSTGRES_DSN -> binding_reviewer proof_run.
--   2. Max does likewise (independent session).
--   3. UPDATE public.gate_roadmap SET status='proven', proof_run_id=<run>
--        WHERE id='5cb0d0de-6aae-4e85-92e0-8fadddc1d7f3';
--      fires trg_01 (Checks A/B/C) + trg_11 (aiden+max dual-attest) +
--      trg_02 (forward-only) + trg_04 (attester != builder=nova). All must pass.
