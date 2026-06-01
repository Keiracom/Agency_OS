-- ============================================================================
-- 20260601_gate_ledger_add_skipped_status.sql
--
-- Follow-up to 20260531_gate_ledger.sql — adds 'skipped' to the status CHECK
-- constraint. verify.sh maps exit code 2 (gate-config-missing) to
-- status='skipped' when writing the ledger row, but the original migration's
-- CHECK clause only allowed ('pass','fail','pending'). Inserts on skipped
-- gates were therefore failing silently (verify.sh logs the failure on
-- stderr and proceeds) and check_phase_ready.sh saw no row → forever pending.
--
-- Max review HOLD 2 on PR #1371 surfaced this; original migration was already
-- applied to production so editing it in place would leave drift, and a
-- follow-up migration is the safe path.
--
-- KEI-87 bypass: SET LOCAL agency_os.callsign = 'dave' required for
-- public-schema DDL.
-- ============================================================================

SET LOCAL agency_os.callsign = 'dave';

ALTER TABLE public.gate_ledger
    DROP CONSTRAINT IF EXISTS gate_ledger_status_check,
    ADD  CONSTRAINT gate_ledger_status_check
         CHECK (status IN ('pass', 'fail', 'pending', 'skipped'));
