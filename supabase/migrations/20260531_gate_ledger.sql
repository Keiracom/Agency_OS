-- ============================================================================
-- 20260531_gate_ledger.sql
--
-- Verification-Gate Mechanism (Phase 0) — Dave directive 2026-05-30 via Elliot.
--
-- Machine-readable ledger of gate runs. Every CI gate execution writes a row;
-- phase-ready + rehearsal-ready checks read from this table. The agent that
-- merged the PR does NOT write here — GitHub Actions does.
--
-- Schema rationale:
--   gate_id      — short stable identifier ('gate_recall', 'gate_atoms', etc).
--   phase        — migration plan phase label ('phase_0', 'phase_1', …).
--   ci_run_id    — GitHub Actions run id (TEXT — can be numeric or URL).
--   pr_number    — INTEGER PR number (nullable for cron / manual runs).
--   status       — pass | fail | pending. CHECK enforced.
--   evidence     — JSONB blob the gate script wrote to stdout, captured verbatim.
--   recorded_at  — NOW() default. Used for "since last check" diff queries.
--
-- KEI-87 bypass: SET LOCAL agency_os.callsign = 'dave' required for
-- public-schema DDL.
-- ============================================================================

SET LOCAL agency_os.callsign = 'dave';

CREATE TABLE IF NOT EXISTS public.gate_ledger (
    id            UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    gate_id       TEXT         NOT NULL,
    phase         TEXT         NOT NULL,
    ci_run_id     TEXT,
    pr_number     INTEGER,
    status        TEXT         NOT NULL
                  CHECK (status IN ('pass', 'fail', 'pending')),
    evidence      JSONB,
    recorded_at   TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_gate_ledger_gate_id_recorded_at
    ON public.gate_ledger (gate_id, recorded_at DESC);

CREATE INDEX IF NOT EXISTS idx_gate_ledger_phase_status
    ON public.gate_ledger (phase, status);

COMMENT ON TABLE public.gate_ledger IS
    'Verification-Gate Mechanism — every CI gate run lands here. '
    'check_phase_ready.sh and rehearsal_ready.sh read this table to decide '
    'whether the named phase / rehearsal is unlocked. Writes come from '
    'GitHub Actions (the PR author does NOT write here).';
