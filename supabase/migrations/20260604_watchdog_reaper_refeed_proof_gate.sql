-- 20260604_watchdog_reaper_refeed_proof_gate.sql
--
-- NOVA — context_watchdog RE-FEED (action-on-idle recovery net) built->proven prep.
-- Gate: watchdog_reaper (66d0879e). Owner-ratified redefinition (Elliot 2026-06-04):
-- this gate now covers the idle->RE-FEED recovery net (the watchdog re-feeds a
-- cleanly-idle agent that has queued work instead of only tab-clearing — the
-- "keep a healthy agent fed" half of continuous_operation_hooks; #1427).
--
-- ⚠ SCOPE FLAG: the gate's PRIOR proof_gate ("zombie/stuck session detected via
-- heartbeat then reaped") described the heartbeat zombie-session reaper
-- (src/dispatcher/heartbeat_reaper.py, KEI-211) — a SEPARATE component that
-- remains built-but-unwired and is NOT proven by this work. Recorded in notes so
-- it is not lost. If reviewers prefer the zombie-reaper keep this gate id, split
-- the re-feed into its own gate instead (HOLD at attest and ping NOVA).
--
-- Does NOT flip status — flip awaits Aiden + Max binding_reviewer proof_runs
-- (attester != builder=nova) via the fixed gate.

BEGIN;

SET LOCAL agency_os.callsign = 'nova';
UPDATE public.gate_roadmap
   SET built_by_callsign = 'nova'
 WHERE id = '66d0879e-b8c8-49ba-af38-88a0f96c9199'
   AND built_by_callsign IS NULL;

UPDATE public.gate_roadmap
   SET proof_gate = 'Action-on-idle recovery net: when an agent is cleanly idle '
                 || '(activity-signal idle) AND has queued inbox work or a due '
                 || 'fleet-task, the context_watchdog RE-FEEDS it — injects the '
                 || 'actual next task so it RESUMES real work (emits a fresh '
                 || 'tool_call_log row), NOT just a tab-clear. Negative: idle with '
                 || 'no queued work is left untouched (no thrash). Never '
                 || 'auto-authorises spend/risky-exec.',
       proof_gate_contract = '{
            "check_id": "context_watchdog_refeed_live_v1",
            "cmd": "bash scripts/proof_bar/context_watchdog_refeed_live.sh",
            "expected_output_contains": [
                "REFED_TASK_INJECTED=true",
                "REFED_FRESH_TOOL_CALL=true",
                "NEG_IDLE_NO_WORK_LEFT=true",
                "REFEED_PROOF_OK"
            ],
            "role_sep": {"builder": "nova", "attester": ["aiden", "max"]},
            "negative_test_required": true
        }'::jsonb,
       required_attestation_kind = 'binding_reviewer',
       notes = 'RE-FED gate (idle->resume real work) wired into '
            || 'scripts/orchestrator/context_watchdog.py refeed_agent (#1427). '
            || 'SEPARATE still-unwired component: heartbeat zombie-session reaper '
            || '(src/dispatcher/heartbeat_reaper.py, KEI-211) — NOT covered here; '
            || 'needs its own gate/proof.'
 WHERE id = '66d0879e-b8c8-49ba-af38-88a0f96c9199';

COMMIT;

-- Flip (post dual-attest): Aiden + Max each run
--   bash scripts/proof_bar/context_watchdog_refeed_live.sh
-- in independent sessions -> binding_reviewer proof_runs, then
--   UPDATE public.gate_roadmap SET status='proven', proof_run_id=<run>
--     WHERE id='66d0879e-b8c8-49ba-af38-88a0f96c9199';
-- fires trg_01 (A/B/C) + trg_11 (aiden+max) + trg_02 + trg_04 (attester != nova).
