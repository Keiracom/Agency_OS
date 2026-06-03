-- reasoning_records — capture deliberation reasoning per chain hop.
-- Per [DESIGN-AMENDMENT-v2] (Aiden+Max concur, PR #1420 comment 4611481694).
-- Gap 1: trg_08 write-guard mirrors fn_gate_proof_runs_write_guard byte-pattern.
-- Gap 2: retry policy lives in Python (shares V1_VERDICT_MAX_RETRIES) — NOT here.
-- Gap 3: gate_roadmap blocker_text wires reasoning_capture → persona_bank_amendment.

SET LOCAL agency_os.callsign = 'orion';


-- ============================================================================
-- 1. reasoning_records — append-only deliberation capture.
-- ============================================================================

CREATE TABLE IF NOT EXISTS public.reasoning_records (
    id              UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    chain_id        TEXT         NOT NULL,
    hop_name        TEXT         NOT NULL,
    callsign        TEXT         NOT NULL,
    source          TEXT         NOT NULL
                    CHECK (source = 'temporal_activity'),
    decision        TEXT         NOT NULL CHECK (length(trim(decision)) > 0),
    challenge       TEXT         NOT NULL CHECK (length(trim(challenge)) > 0),
    tradeoffs       TEXT         NOT NULL CHECK (length(trim(tradeoffs)) > 0),
    rejected_options TEXT        NOT NULL CHECK (length(trim(rejected_options)) > 0),
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE public.reasoning_records IS
    'Per-hop deliberation reasoning captured by capture_hop_reasoning Temporal '
    'activity BEFORE advance_step. Append-only; write-guarded by trg_08. '
    'Reference: [DESIGN-AMENDMENT-v2] in PR #1420 comment 4611481694.';

CREATE INDEX IF NOT EXISTS idx_reasoning_records_chain
    ON public.reasoning_records (chain_id, created_at);


-- ============================================================================
-- 2. trg_08_reasoning_write_guard — byte-identical to fn_gate_proof_runs_write_guard.
-- Max carry-forward: covers ALL connection paths (service_role, anon,
-- authenticated, internal). BEFORE INSERT triggers fire regardless of role —
-- the negative-path DO block §6 below proves the trigger refuses without the
-- session var, independent of connection role.
-- ============================================================================

CREATE OR REPLACE FUNCTION public.fn_reasoning_records_write_guard()
RETURNS trigger LANGUAGE plpgsql AS $fn$
BEGIN
    IF current_setting('agency_os.callsign', TRUE) IS NULL
       OR current_setting('agency_os.callsign', TRUE) = ''
    THEN
        RAISE EXCEPTION
            'reasoning_records write-guard: agency_os.callsign session var must be SET LOCAL before writing.'
            USING ERRCODE = 'check_violation';
    END IF;
    RETURN NEW;
END;
$fn$;

DROP TRIGGER IF EXISTS trg_08_reasoning_write_guard ON public.reasoning_records;
CREATE TRIGGER trg_08_reasoning_write_guard
    BEFORE INSERT ON public.reasoning_records
    FOR EACH ROW EXECUTE FUNCTION public.fn_reasoning_records_write_guard();


-- ============================================================================
-- 3. gate_roadmap row — persona_bank_amendment (prerequisite of reasoning_capture).
-- Per Gap 3: converts the follow-up note into a hard DB dependency.
-- ============================================================================

INSERT INTO public.gate_roadmap
    (component, phase, proof_gate, status, owner, notes)
VALUES (
    'persona_bank_amendment',
    '1_nucleus',
    'persona_bank migration applied + smoke test passes',
    'not_started',
    'atlas',
    'Prerequisite for reasoning_capture per [DESIGN-AMENDMENT-v2] '
    '(Aiden+Max concur, PR #1420 comment 4611481694). Without persona_bank_amendment '
    'proven, all captured reasoning_records have null/empty source_persona — the '
    'capture table exists but its analytical value (which persona produced which '
    'reasoning trace) is lost.'
)
ON CONFLICT (component) DO NOTHING;


-- ============================================================================
-- 4. gate_roadmap update — reasoning_capture.blocker_text references persona_bank_amendment.
-- proof_gate text already encodes the dispatch's amendment spec (Dave 2026-06-03);
-- this UPDATE wires the blocker so proven-flip on reasoning_capture is hard-blocked
-- until persona_bank_amendment is proven.
-- ============================================================================

DO $$
DECLARE
    persona_bank_id UUID;
BEGIN
    SELECT id INTO persona_bank_id
      FROM public.gate_roadmap
     WHERE component = 'persona_bank_amendment'
     LIMIT 1;
    IF persona_bank_id IS NULL THEN
        RAISE EXCEPTION 'reasoning_capture blocker_text wire: persona_bank_amendment row missing — §3 INSERT failed.';
    END IF;
    UPDATE public.gate_roadmap
       SET blocker_text =
           'BLOCKED BY persona_bank_amendment (gate_roadmap_id ' || persona_bank_id::text
           || '). Per [DESIGN-AMENDMENT-v2] Gap 3 — proven-flip refused until persona_bank_amendment proven.'
     WHERE component = 'reasoning_capture';
END $$;


-- ============================================================================
-- 5. gate_roadmap NoOp — atom_capture proof_gate already tightened.
-- Dave directive 2026-06-03 added the SUBSTANCE addendum: persisted atoms must
-- contain decision/challenge/tradeoffs/rejected_options + agent attribution.
-- This block asserts the text is present so the migration fails loudly if a
-- future change drops the substance language.
-- ============================================================================

DO $$
BEGIN
    PERFORM 1 FROM public.gate_roadmap
     WHERE component = 'atom_capture'
       AND proof_gate ILIKE '%deliberation reasoning%'
       AND proof_gate ILIKE '%rejected options%';
    IF NOT FOUND THEN
        RAISE EXCEPTION 'atom_capture proof_gate missing SUBSTANCE addendum (decision/challenge/tradeoffs/rejected — Dave 2026-06-03). [DESIGN-AMENDMENT-v2] requires this guarantee.';
    END IF;
END $$;


-- ============================================================================
-- 6. NEGATIVE-PATH TEST — trigger refuses INSERT without session var (Dave precedent).
-- Migration apply ROLLBACKs if the expected rejection does not fire.
-- ============================================================================

DO $$
DECLARE
    test_failed BOOLEAN := FALSE;
BEGIN
    -- Stash + clear the session var so the trigger sees NULL/empty.
    PERFORM set_config('agency_os.callsign', '', TRUE);

    BEGIN
        INSERT INTO public.reasoning_records
            (chain_id, hop_name, callsign, source,
             decision, challenge, tradeoffs, rejected_options)
        VALUES ('__neg_test__', 'hop', 'nova', 'temporal_activity',
                'd', 'c', 't', 'r');
        test_failed := TRUE;
    EXCEPTION WHEN check_violation THEN
        NULL;  -- expected — trg_08 refused on empty session var
    END;

    -- Restore session var for the migration's downstream operations.
    PERFORM set_config('agency_os.callsign', 'orion', TRUE);

    IF test_failed THEN
        RAISE EXCEPTION 'NEGATIVE TEST FAILED: trg_08_reasoning_write_guard did NOT refuse INSERT with empty session var.';
    END IF;
    RAISE NOTICE 'NEGATIVE TEST PASSED: trg_08_reasoning_write_guard correctly refused INSERT without agency_os.callsign session var.';
END $$;


-- ============================================================================
-- 7. Verification queries (operator runs post-apply).
--
--   SELECT tgname FROM pg_trigger
--    WHERE tgrelid = 'public.reasoning_records'::regclass
--      AND tgname = 'trg_08_reasoning_write_guard';
--
--   SELECT component, status, blocker_text
--     FROM public.gate_roadmap
--    WHERE component IN ('reasoning_capture', 'persona_bank_amendment', 'atom_capture')
--    ORDER BY component;
-- ============================================================================
