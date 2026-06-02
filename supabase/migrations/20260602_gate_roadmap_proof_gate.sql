-- ============================================================================
-- 20260602_gate_roadmap_proof_gate.sql
--
-- Proof-Gate for gate_roadmap.status='proven' — Dave directive 2026-06-02.
-- KEI Agency_OS-xjtn. Joint design by Aiden (architecture) + Atlas (safety).
-- Concur trail:
--   /tmp/aiden_proof_gate_design.md                                  (Aiden solo, superseded)
--   docs/architecture/design/proof_gate_design_xjtn_atlas_safety.md  (Atlas safety draft)
--   /tmp/atlas_proof_gate_safety_additions.md                        (Atlas merge table)
--   /tmp/telegram-relay-elliot/processed/aiden_atlas_joint_proof_gate_1780372795.json (joint)
--   /tmp/telegram-relay-elliot/inbox/atlas_concur_joint_proof_gate_1780372915.json   ([CONCUR:atlas])
--
-- CEO calls reflected verbatim:
--   Q1 — Session-independence trigger is SOFT (best-effort). Comment in body.
--        No tool_call_log write-guard in this PR.
--   Q2 — SHA256 computed at APPLICATION layer. Trigger validates output_sha256
--        IS NOT NULL + UNIQUE — does NOT compute or re-verify the hash.
--   Q3 — Bootstrap proof_runs allowed but MUST include comment citing real
--        evidence. Components without real evidence MUST seed as status='built'
--        not 'proven'. No laundering.
--
-- Dave tightening (TAKE IT):
--   * binding_reviewer attestation restricted to ('dave', 'elliot') at trigger
--     layer (fn_gate_proof_no_self_attest).
--   * gate_roadmap.required_attestation_kind='ci_runner' on a row → trigger
--     refuses any binding_reviewer proof_run for that row.
--   * Anti-spoof on built_by_callsign: explicit settings must match session-var
--     caller — closes the backdated-builder-identity surface.
--   * First component seeded: product_landing_site (status='built',
--     required_attestation_kind='ci_runner').
--
-- Dave addendum (2026-06-02):
--   * Inline DO block negative tests — REQUIRED. Migration apply fails if a
--     trigger doesn't block the thing it exists to block. §8 below.
--   * Bootstrap proof_runs for existing 'proven' rows (gate_mechanism /
--     persona_config / temporal_runtime) with verbatim evidence citations. §7.
--   * product_landing_site seeds as 'built' (NOT 'proven') — proven THROUGH
--     the gate, not bootstrapped. First self-validation target. §6.
--
-- KEI-87 bypass: SET LOCAL agency_os.callsign = 'dave' is REQUIRED for the
-- public-schema DDL below AND for parts of the seed/bootstrap. Per-row
-- session-var changes record the correct builder via the capture trigger.
--
-- DESIGN ONLY — do NOT apply to any DB until Dave approves the joint design.
-- This file is the proposed migration the design produces. SHA256 hashes for
-- bootstrap run_output were precomputed at the application layer (Python
-- hashlib); the trigger does not re-verify per Q2.
-- ============================================================================

SET LOCAL agency_os.callsign = 'dave';


-- ============================================================================
-- 1. gate_roadmap — ADDITIVE ONLY (Dave directive 2026-06-02).
--
-- The gate_roadmap table already exists in prod (50 live rows confirmed
-- against jatzvazlbusedwsnqxzr). This migration MUST be additive — it
-- only ADDs columns + a UNIQUE constraint via DO block. No CREATE TABLE
-- gate_roadmap, even with IF NOT EXISTS. A fresh-DB bootstrap is the
-- responsibility of the original gate_roadmap migration (not this one).
-- ============================================================================

ALTER TABLE public.gate_roadmap
    ADD COLUMN IF NOT EXISTS built_by_callsign        TEXT,
    ADD COLUMN IF NOT EXISTS required_attestation_kind TEXT
        CHECK (required_attestation_kind IS NULL
               OR required_attestation_kind IN ('ci_runner', 'binding_reviewer'));

-- UNIQUE (component) so seeds can use ON CONFLICT and the proof_run FK below
-- can identify a roadmap row by its semantic key in audits.
-- PG 17.6 has no ADD CONSTRAINT IF NOT EXISTS; gate via pg_constraint check.
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
         WHERE conname  = 'gate_roadmap_component_unique'
           AND conrelid = 'public.gate_roadmap'::regclass
    ) THEN
        ALTER TABLE public.gate_roadmap
            ADD CONSTRAINT gate_roadmap_component_unique UNIQUE (component);
    END IF;
END $$;


-- ============================================================================
-- 2. gate_proof_runs — append-only evidence records that unlock 'proven'.
-- ============================================================================

CREATE TABLE IF NOT EXISTS public.gate_proof_runs (
    id                    UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    gate_roadmap_id       UUID         NOT NULL
                          REFERENCES public.gate_roadmap(id) ON DELETE RESTRICT,
    attestation_kind      TEXT         NOT NULL
                          CHECK (attestation_kind IN ('ci_runner', 'binding_reviewer')),
    run_cmd               TEXT         NOT NULL
                          CHECK (length(trim(run_cmd)) > 0),
    run_output            TEXT         NOT NULL
                          CHECK (length(run_output) >= 32),
    output_sha256         TEXT         NOT NULL
                          CHECK (length(output_sha256) = 64),  -- hex sha256
    exit_code             INTEGER      NOT NULL CHECK (exit_code = 0),
    attesting_callsign    TEXT         NOT NULL,
    attester_session_uuid TEXT         NOT NULL,
    run_at                TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    ci_run_id             TEXT,
    gate_ledger_id        UUID         REFERENCES public.gate_ledger(id) ON DELETE RESTRICT,
    repo_sha              TEXT,
    UNIQUE (gate_roadmap_id, output_sha256)
);

COMMENT ON TABLE public.gate_proof_runs IS
    'Append-only audit table backing gate_roadmap.status=proven. DO NOT add '
    'retention/archival without a Dave directive — loss of these rows '
    'invalidates the gate. Inserts only; UPDATE/DELETE blocked by '
    'fn_gate_proof_runs_immutability. KEI Agency_OS-xjtn, Dave 2026-06-02.';

CREATE INDEX IF NOT EXISTS idx_gate_proof_runs_gate_roadmap_id
    ON public.gate_proof_runs (gate_roadmap_id);
CREATE INDEX IF NOT EXISTS idx_gate_proof_runs_gate_ledger_id
    ON public.gate_proof_runs (gate_ledger_id);


-- ============================================================================
-- 3. gate_roadmap.proof_run_id — added AFTER gate_proof_runs exists.
-- ============================================================================

ALTER TABLE public.gate_roadmap
    ADD COLUMN IF NOT EXISTS proof_run_id UUID REFERENCES public.gate_proof_runs(id);


-- ============================================================================
-- 4. gate_roadmap_history — append-only status-transition audit (Atlas D2).
-- ============================================================================

CREATE TABLE IF NOT EXISTS public.gate_roadmap_history (
    id                  UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    gate_roadmap_id     UUID         NOT NULL REFERENCES public.gate_roadmap(id) ON DELETE RESTRICT,
    old_status          TEXT,
    new_status          TEXT         NOT NULL,
    changed_by_callsign TEXT,
    proof_run_id        UUID         REFERENCES public.gate_proof_runs(id),
    changed_at          TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE public.gate_roadmap_history IS
    'Append-only status-transition audit. UPDATE/DELETE blocked by '
    'fn_gate_roadmap_history_immutability. KEI Agency_OS-xjtn, Dave 2026-06-02.';

CREATE INDEX IF NOT EXISTS idx_gate_roadmap_history_gate_roadmap_id_changed_at
    ON public.gate_roadmap_history (gate_roadmap_id, changed_at DESC);


-- ============================================================================
-- 5. Trigger functions (9 from joint + history immutability = 10 total).
-- ============================================================================

-- ----- trg_01 : fn_verify_before_proven -----------------------------------
CREATE OR REPLACE FUNCTION public.fn_verify_before_proven()
RETURNS trigger LANGUAGE plpgsql AS $fn$
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

        SELECT run_at INTO NEW.last_verified
          FROM public.gate_proof_runs WHERE id = NEW.proof_run_id;
    END IF;
    RETURN NEW;
END;
$fn$;

DROP TRIGGER IF EXISTS trg_01_verify_before_proven ON public.gate_roadmap;
CREATE TRIGGER trg_01_verify_before_proven
    BEFORE UPDATE OF status ON public.gate_roadmap
    FOR EACH ROW EXECUTE FUNCTION public.fn_verify_before_proven();


-- ----- trg_02 : fn_gate_roadmap_status_forward_only -----------------------
CREATE OR REPLACE FUNCTION public.fn_gate_roadmap_status_forward_only()
RETURNS trigger LANGUAGE plpgsql AS $fn$
DECLARE
    status_order CONSTANT TEXT[] := ARRAY['not_started', 'built', 'proven'];
    old_ord INT;
    new_ord INT;
BEGIN
    IF NEW.status IS NOT DISTINCT FROM OLD.status THEN
        RETURN NEW;
    END IF;
    IF OLD.status IN ('skipped', 'deferred') OR NEW.status IN ('skipped', 'deferred') THEN
        RETURN NEW;
    END IF;
    old_ord := array_position(status_order, OLD.status);
    new_ord := array_position(status_order, NEW.status);
    IF old_ord IS NOT NULL AND new_ord IS NOT NULL AND new_ord < old_ord THEN
        RAISE EXCEPTION
            'gate_roadmap status regression blocked: % → % is not allowed.',
            OLD.status, NEW.status
            USING ERRCODE = 'check_violation';
    END IF;
    RETURN NEW;
END;
$fn$;

DROP TRIGGER IF EXISTS trg_02_gate_roadmap_status_forward_only ON public.gate_roadmap;
CREATE TRIGGER trg_02_gate_roadmap_status_forward_only
    BEFORE UPDATE OF status ON public.gate_roadmap
    FOR EACH ROW EXECUTE FUNCTION public.fn_gate_roadmap_status_forward_only();


-- ----- trg_03 : fn_gate_roadmap_capture_builder ---------------------------
-- Auto-captures session-var caller into built_by_callsign at first
-- status='built' transition (INSERT or UPDATE). Anti-spoof: any explicit
-- setting of built_by_callsign must match the session-var caller — closes
-- the backdated-identity surface. Once non-NULL, frozen.
CREATE OR REPLACE FUNCTION public.fn_gate_roadmap_capture_builder()
RETURNS trigger LANGUAGE plpgsql AS $fn$
DECLARE
    caller TEXT := current_setting('agency_os.callsign', true);
BEGIN
    IF TG_OP = 'INSERT' THEN
        -- Auto-capture path: built status with NULL builder → take from session.
        IF NEW.status = 'built' AND NEW.built_by_callsign IS NULL THEN
            IF caller IS NULL OR caller = '' THEN
                RAISE EXCEPTION
                    'gate_roadmap capture-builder: INSERT with status=built requires agency_os.callsign session var.'
                    USING ERRCODE = 'check_violation';
            END IF;
            NEW.built_by_callsign := caller;
        END IF;

        -- Anti-spoof: any explicit builder must match session-var caller.
        IF NEW.built_by_callsign IS NOT NULL
           AND NEW.built_by_callsign IS DISTINCT FROM caller THEN
            RAISE EXCEPTION
                'gate_roadmap capture-builder: explicit built_by_callsign=% must match session-var caller=% — no spoofing.',
                NEW.built_by_callsign, caller
                USING ERRCODE = 'check_violation';
        END IF;
        RETURN NEW;
    END IF;

    -- UPDATE path: first transition to 'built' captures caller.
    IF NEW.status = 'built'
       AND OLD.status IS DISTINCT FROM 'built'
       AND OLD.built_by_callsign IS NULL
       AND NEW.built_by_callsign IS NULL THEN
        IF caller IS NULL OR caller = '' THEN
            RAISE EXCEPTION
                'gate_roadmap capture-builder: UPDATE to status=built requires agency_os.callsign session var.'
                USING ERRCODE = 'check_violation';
        END IF;
        NEW.built_by_callsign := caller;
    END IF;

    -- Immutability: once set, cannot change.
    IF OLD.built_by_callsign IS NOT NULL
       AND NEW.built_by_callsign IS DISTINCT FROM OLD.built_by_callsign THEN
        RAISE EXCEPTION
            'gate_roadmap capture-builder: built_by_callsign is frozen (was %, refused change to %).',
            OLD.built_by_callsign, NEW.built_by_callsign
            USING ERRCODE = 'check_violation';
    END IF;

    -- Anti-spoof on first-time UPDATE settings: NEW must match session-var.
    -- Allows the legitimate bootstrap path where the migration SETs the
    -- session-var per row to the real builder before UPDATE.
    IF OLD.built_by_callsign IS NULL
       AND NEW.built_by_callsign IS NOT NULL
       AND NEW.built_by_callsign IS DISTINCT FROM caller THEN
        RAISE EXCEPTION
            'gate_roadmap capture-builder: explicit built_by_callsign=% must match session-var caller=% — no spoofing.',
            NEW.built_by_callsign, caller
            USING ERRCODE = 'check_violation';
    END IF;

    RETURN NEW;
END;
$fn$;

DROP TRIGGER IF EXISTS trg_03_gate_roadmap_capture_builder ON public.gate_roadmap;
CREATE TRIGGER trg_03_gate_roadmap_capture_builder
    BEFORE INSERT OR UPDATE OF status, built_by_callsign ON public.gate_roadmap
    FOR EACH ROW EXECUTE FUNCTION public.fn_gate_roadmap_capture_builder();


-- ----- trg_04 : fn_gate_proof_no_self_attest ------------------------------
-- Non-self-attestation + binding_reviewer allowlist + per-component policy.
CREATE OR REPLACE FUNCTION public.fn_gate_proof_no_self_attest()
RETURNS trigger LANGUAGE plpgsql AS $fn$
DECLARE
    v_builder         TEXT;
    v_required_kind   TEXT;
    binding_allowlist CONSTANT TEXT[] := ARRAY['dave', 'elliot'];
BEGIN
    SELECT built_by_callsign, required_attestation_kind
      INTO v_builder, v_required_kind
      FROM public.gate_roadmap
     WHERE id = NEW.gate_roadmap_id;

    IF v_builder IS NULL THEN
        RAISE EXCEPTION
            'gate_proof_runs no-self-attest: gate_roadmap.built_by_callsign is NULL for gate_roadmap_id=%; record the build transition first.',
            NEW.gate_roadmap_id
            USING ERRCODE = 'check_violation';
    END IF;

    IF NEW.attesting_callsign = v_builder THEN
        RAISE EXCEPTION
            'gate_proof_runs no-self-attest: attesting_callsign=% matches gate_roadmap.built_by_callsign=% for gate_roadmap_id=%. Building agent cannot attest its own proof.',
            NEW.attesting_callsign, v_builder, NEW.gate_roadmap_id
            USING ERRCODE = 'check_violation';
    END IF;

    -- Dave tightening (TAKE IT): binding_reviewer requires allowlist callsign.
    IF NEW.attestation_kind = 'binding_reviewer'
       AND NOT (NEW.attesting_callsign = ANY (binding_allowlist)) THEN
        RAISE EXCEPTION
            'gate_proof_runs binding-reviewer-allowlist: attestation_kind=binding_reviewer requires attesting_callsign IN % (got: %).',
            binding_allowlist, NEW.attesting_callsign
            USING ERRCODE = 'check_violation';
    END IF;

    -- Per-component policy: ci_runner-required components refuse binding_reviewer.
    IF v_required_kind = 'ci_runner' AND NEW.attestation_kind = 'binding_reviewer' THEN
        RAISE EXCEPTION
            'gate_proof_runs required-attestation-kind: gate_roadmap.required_attestation_kind=ci_runner for gate_roadmap_id=%; binding_reviewer proof_runs refused.',
            NEW.gate_roadmap_id
            USING ERRCODE = 'check_violation';
    END IF;

    RETURN NEW;
END;
$fn$;

DROP TRIGGER IF EXISTS trg_04_gate_proof_no_self_attest ON public.gate_proof_runs;
CREATE TRIGGER trg_04_gate_proof_no_self_attest
    BEFORE INSERT ON public.gate_proof_runs
    FOR EACH ROW EXECUTE FUNCTION public.fn_gate_proof_no_self_attest();


-- ----- trg_05 : fn_gate_proof_ci_hardening --------------------------------
-- ci_runner: bearer-token + ci_run_id + gate_ledger_id chain validation.
CREATE OR REPLACE FUNCTION public.fn_gate_proof_ci_hardening()
RETURNS trigger LANGUAGE plpgsql AS $fn$
DECLARE
    caller         TEXT := current_setting('agency_os.callsign', true);
    v_ledger_match BOOLEAN;
BEGIN
    IF NEW.attestation_kind <> 'ci_runner' THEN
        RETURN NEW;
    END IF;

    IF caller IS DISTINCT FROM 'github_actions' THEN
        RAISE EXCEPTION
            'gate_proof_runs ci-hardening: ci_runner attestation requires agency_os.callsign=github_actions (got: %).',
            caller
            USING ERRCODE = 'check_violation';
    END IF;

    IF NEW.attesting_callsign IS DISTINCT FROM 'github_actions' THEN
        RAISE EXCEPTION
            'gate_proof_runs ci-hardening: ci_runner attestation requires attesting_callsign=github_actions (got: %).',
            NEW.attesting_callsign
            USING ERRCODE = 'check_violation';
    END IF;

    IF NEW.ci_run_id IS NULL OR NEW.ci_run_id = '' THEN
        RAISE EXCEPTION
            'gate_proof_runs ci-hardening: ci_runner attestation requires non-empty ci_run_id.'
            USING ERRCODE = 'check_violation';
    END IF;

    IF NEW.gate_ledger_id IS NULL THEN
        RAISE EXCEPTION
            'gate_proof_runs ci-hardening: ci_runner attestation requires gate_ledger_id.'
            USING ERRCODE = 'check_violation';
    END IF;

    SELECT TRUE INTO v_ledger_match
      FROM public.gate_ledger
     WHERE id        = NEW.gate_ledger_id
       AND status    = 'pass'
       AND ci_run_id = NEW.ci_run_id;

    IF NOT FOUND THEN
        RAISE EXCEPTION
            'gate_proof_runs ci-hardening: gate_ledger_id=% missing, not status=pass, or ci_run_id=% mismatch.',
            NEW.gate_ledger_id, NEW.ci_run_id
            USING ERRCODE = 'check_violation';
    END IF;

    RETURN NEW;
END;
$fn$;

DROP TRIGGER IF EXISTS trg_05_gate_proof_ci_hardening ON public.gate_proof_runs;
CREATE TRIGGER trg_05_gate_proof_ci_hardening
    BEFORE INSERT ON public.gate_proof_runs
    FOR EACH ROW EXECUTE FUNCTION public.fn_gate_proof_ci_hardening();


-- ----- trg_06 : fn_gate_proof_session_independence ------------------------
-- CEO Q1: SOFT control — best-effort signal only. The load-bearing controls
-- are the bearer-token gate (ci_runner, trg_05) and the frozen-builder
-- DB-join (binding_reviewer, trg_04). This trigger adds a defensive
-- secondary signal for binding_reviewer attestations by checking the
-- attester_session_uuid against tool_call_log activity.
--
-- WHY SOFT: tool_call_log does not (yet) have a session-var write guard
-- equivalent to ceo_memory_write_guard (KEI-87). Without that, an agent
-- with DSN access can write fake tool_call_log rows under arbitrary
-- callsigns / session_uuids. This trigger is a bypassable secondary
-- defense — useful pressure against casual fabrication, not a structural
-- floor. Tightening tracked as a follow-up KEI; do NOT elevate this
-- trigger to load-bearing without first hardening tool_call_log.
--
-- DAVE EXEMPTION: when attesting_callsign='dave' the session-independence
-- check is skipped — dave-attested rows are the migration-time bootstrap
-- path; dave's session_uuid is not a meaningful check (no tool_call_log
-- entry for dave's privileged callsign).
CREATE OR REPLACE FUNCTION public.fn_gate_proof_session_independence()
RETURNS trigger LANGUAGE plpgsql AS $fn$
DECLARE
    v_builder           TEXT;
    v_count_in_builder  INTEGER;
    v_count_in_attester INTEGER;
BEGIN
    IF NEW.attestation_kind <> 'binding_reviewer' THEN
        RETURN NEW;
    END IF;

    -- Dave-exemption (bootstrap path).
    IF NEW.attesting_callsign = 'dave' THEN
        RETURN NEW;
    END IF;

    SELECT built_by_callsign INTO v_builder
      FROM public.gate_roadmap WHERE id = NEW.gate_roadmap_id;

    SELECT count(*) INTO v_count_in_builder
      FROM public.tool_call_log
     WHERE callsign     = v_builder
       AND session_uuid = NEW.attester_session_uuid;

    IF v_count_in_builder > 0 THEN
        RAISE EXCEPTION
            'gate_proof_runs session-independence (soft): attester_session_uuid=% appears in builder=% tool_call_log.',
            NEW.attester_session_uuid, v_builder
            USING ERRCODE = 'check_violation';
    END IF;

    SELECT count(*) INTO v_count_in_attester
      FROM public.tool_call_log
     WHERE callsign     = NEW.attesting_callsign
       AND session_uuid = NEW.attester_session_uuid;

    IF v_count_in_attester = 0 THEN
        RAISE EXCEPTION
            'gate_proof_runs session-independence (soft): attester_session_uuid=% has no record in attesting_callsign=% tool_call_log.',
            NEW.attester_session_uuid, NEW.attesting_callsign
            USING ERRCODE = 'check_violation';
    END IF;

    RETURN NEW;
END;
$fn$;

DROP TRIGGER IF EXISTS trg_06_gate_proof_session_independence ON public.gate_proof_runs;
CREATE TRIGGER trg_06_gate_proof_session_independence
    BEFORE INSERT ON public.gate_proof_runs
    FOR EACH ROW EXECUTE FUNCTION public.fn_gate_proof_session_independence();


-- ----- trg_07 : fn_gate_proof_runs_immutability ---------------------------
CREATE OR REPLACE FUNCTION public.fn_gate_proof_runs_immutability()
RETURNS trigger LANGUAGE plpgsql AS $fn$
BEGIN
    RAISE EXCEPTION
        'gate_proof_runs is append-only — UPDATE/DELETE refused.'
        USING ERRCODE = 'check_violation';
END;
$fn$;

DROP TRIGGER IF EXISTS trg_07_gate_proof_runs_immutability ON public.gate_proof_runs;
CREATE TRIGGER trg_07_gate_proof_runs_immutability
    BEFORE UPDATE OR DELETE ON public.gate_proof_runs
    FOR EACH ROW EXECUTE FUNCTION public.fn_gate_proof_runs_immutability();


-- ----- trg_08 : fn_gate_proof_runs_write_guard ----------------------------
-- Session-var must be set + match NEW.attesting_callsign. Mirrors KEI-87.
-- output_sha256 IS NOT NULL + length=64 already enforced by column CHECK;
-- the trigger does NOT compute or re-verify the hash per CEO Q2.
CREATE OR REPLACE FUNCTION public.fn_gate_proof_runs_write_guard()
RETURNS trigger LANGUAGE plpgsql AS $fn$
DECLARE
    caller TEXT := current_setting('agency_os.callsign', true);
BEGIN
    IF caller IS NULL OR caller = '' THEN
        RAISE EXCEPTION
            'gate_proof_runs write-guard: agency_os.callsign session var must be SET LOCAL before writing.'
            USING ERRCODE = 'check_violation';
    END IF;
    IF NEW.attesting_callsign IS DISTINCT FROM caller THEN
        RAISE EXCEPTION
            'gate_proof_runs write-guard: attesting_callsign=% does not match session-var caller=%.',
            NEW.attesting_callsign, caller
            USING ERRCODE = 'check_violation';
    END IF;
    RETURN NEW;
END;
$fn$;

DROP TRIGGER IF EXISTS trg_08_gate_proof_runs_write_guard ON public.gate_proof_runs;
CREATE TRIGGER trg_08_gate_proof_runs_write_guard
    BEFORE INSERT ON public.gate_proof_runs
    FOR EACH ROW EXECUTE FUNCTION public.fn_gate_proof_runs_write_guard();


-- ----- trg_09 : fn_gate_roadmap_audit -------------------------------------
CREATE OR REPLACE FUNCTION public.fn_gate_roadmap_audit()
RETURNS trigger LANGUAGE plpgsql AS $fn$
BEGIN
    IF NEW.status IS DISTINCT FROM OLD.status THEN
        INSERT INTO public.gate_roadmap_history
            (gate_roadmap_id, old_status, new_status, changed_by_callsign, proof_run_id)
        VALUES
            (NEW.id, OLD.status, NEW.status,
             current_setting('agency_os.callsign', true), NEW.proof_run_id);
    END IF;
    RETURN NEW;
END;
$fn$;

DROP TRIGGER IF EXISTS trg_09_gate_roadmap_audit ON public.gate_roadmap;
CREATE TRIGGER trg_09_gate_roadmap_audit
    AFTER UPDATE ON public.gate_roadmap
    FOR EACH ROW EXECUTE FUNCTION public.fn_gate_roadmap_audit();


-- ----- trg_10 : fn_gate_roadmap_history_immutability ----------------------
CREATE OR REPLACE FUNCTION public.fn_gate_roadmap_history_immutability()
RETURNS trigger LANGUAGE plpgsql AS $fn$
BEGIN
    RAISE EXCEPTION
        'gate_roadmap_history is append-only — UPDATE/DELETE refused.'
        USING ERRCODE = 'check_violation';
END;
$fn$;

DROP TRIGGER IF EXISTS trg_10_gate_roadmap_history_immutability ON public.gate_roadmap_history;
CREATE TRIGGER trg_10_gate_roadmap_history_immutability
    BEFORE UPDATE OR DELETE ON public.gate_roadmap_history
    FOR EACH ROW EXECUTE FUNCTION public.fn_gate_roadmap_history_immutability();


-- ============================================================================
-- 6. Seed — product_landing_site (Dave directive 2026-06-02 addendum item 3).
--
-- CEO Q3 verbatim: "Any component without real evidence MUST seed as
-- status='built' not 'proven'. No laundering." product_landing_site has no
-- CI proof_run; seeded as 'built' AND required_attestation_kind='ci_runner'
-- so the only path to 'proven' is THROUGH the gate (first self-validation).
-- ============================================================================

INSERT INTO public.gate_roadmap
    (component, phase, proof_gate, status, required_attestation_kind, owner, notes)
VALUES
    ('product_landing_site',
     'phase_1',
     'pending — awaits CI gate authoring + first ci_runner proof_run',
     'built',
     'ci_runner',
     'dave',
     'KEI Agency_OS-xjtn seed (Dave directive 2026-06-02). status=built reflects current implementation state; transition to proven blocked until a ci_runner proof_run lands per required_attestation_kind policy. First self-validation target for the proof-gate mechanism. built_by_callsign captured as dave by trg_03_gate_roadmap_capture_builder via the SET LOCAL agency_os.callsign=dave at the top of this migration.')
ON CONFLICT (component) DO NOTHING;


-- ============================================================================
-- 7. BOOTSTRAP — existing 'proven' rows backfilled with proof_runs.
--
-- Three pre-existing 'proven' rows on gate_roadmap predate this migration.
-- Each MUST have a backing proof_run with verbatim evidence citation per
-- Dave addendum item 2. Without bootstrap, trigger_1 fires on any future
-- UPDATE OF status on these rows (which would currently have proof_run_id
-- = NULL), making them effectively unmaintainable.
--
-- For each row:
--   (a) SET LOCAL agency_os.callsign to the REAL builder (per gate_roadmap.
--       owner column) → UPDATE built_by_callsign. Anti-spoof passes because
--       NEW.built_by_callsign == caller for each.
--   (b) SET LOCAL agency_os.callsign='dave' → INSERT binding_reviewer
--       proof_run. trigger_4 allowlist passes (dave ∈ allowlist), no-self-
--       attest passes (dave != elliot/aiden builders), trigger_5 skipped
--       (binding_reviewer not ci_runner), trigger_6 skipped (dave-exemption).
--   (c) UPDATE gate_roadmap.proof_run_id ← new proof_run.id. Does NOT touch
--       status column → trg_01 does not fire on this UPDATE.
--
-- SHA256 hashes precomputed via Python hashlib (CEO Q2 — application layer).
-- Trigger validates IS NOT NULL + UNIQUE; does not recompute.
-- ============================================================================

-- 7a. gate_mechanism (builder=elliot) ---------------------------------------
SET LOCAL agency_os.callsign = 'elliot';
UPDATE public.gate_roadmap
   SET built_by_callsign = 'elliot'
 WHERE component = 'gate_mechanism'
   AND built_by_callsign IS NULL;

SET LOCAL agency_os.callsign = 'dave';
WITH proof AS (
    INSERT INTO public.gate_proof_runs
        (gate_roadmap_id, attestation_kind, run_cmd, run_output, output_sha256,
         exit_code, attesting_callsign, attester_session_uuid)
    SELECT id,
           'binding_reviewer',
           'BOOTSTRAP — no re-runnable command; row backs CLOSED-per-Dave-2026-05-31 ratification. Future re-attestation should land via ci_runner once a CI gate is authored for gate_mechanism.',
           E'BOOTSTRAP proof_run — citing real evidence per Dave directive 2026-06-02 (KEI Agency_OS-xjtn).\n\nComponent: gate_mechanism (Phase 0_foundation, owner=elliot)\nStatus pre-migration: proven (last_verified 2026-05-31)\n\nEVIDENCE (verbatim from gate_roadmap.notes):\nCLOSED per Dave 2026-05-31. skip-to-enforced rule ratified.\n\nAnchor migrations:\n  supabase/migrations/20260531_gate_ledger.sql           — verification-gate mechanism Phase 0\n  supabase/migrations/20260601_gate_ledger_add_skipped_status.sql — skip-to-enforced amendment\n\nAttestation: binding_reviewer Dave at migration apply time. The gate_mechanism row is META — it backs the very mechanism this migration extends. Bootstrap is the only honest path (CI gates verify components, not themselves).',
           'c87404e9985d11d3f8afaa98e90b3585da28df5d9b3db6748161800924c7d274',
           0,
           'dave',
           'bootstrap-migration-20260602-gate_mechanism'
      FROM public.gate_roadmap
     WHERE component = 'gate_mechanism'
       AND NOT EXISTS (
            SELECT 1 FROM public.gate_proof_runs
             WHERE gate_roadmap_id = public.gate_roadmap.id
       )
    RETURNING id, gate_roadmap_id
)
UPDATE public.gate_roadmap gr
   SET proof_run_id = proof.id
  FROM proof
 WHERE gr.id = proof.gate_roadmap_id
   AND gr.proof_run_id IS NULL;


-- 7b. persona_config (builder=aiden) ----------------------------------------
SET LOCAL agency_os.callsign = 'aiden';
UPDATE public.gate_roadmap
   SET built_by_callsign = 'aiden'
 WHERE component = 'persona_config'
   AND built_by_callsign IS NULL;

SET LOCAL agency_os.callsign = 'dave';
WITH proof AS (
    INSERT INTO public.gate_proof_runs
        (gate_roadmap_id, attestation_kind, run_cmd, run_output, output_sha256,
         exit_code, attesting_callsign, attester_session_uuid)
    SELECT id,
           'binding_reviewer',
           'BOOTSTRAP — anchor commands: SELECT role, variant, token_count, length(prompt_text) FROM persona_bank WHERE role IN (worker,reviewer) AND variant IN (nova,orion,atlas); — executed 2026-06-01 against jatzvazlbusedwsnqxzr.',
           E'BOOTSTRAP proof_run — citing real evidence per Dave directive 2026-06-02 (KEI Agency_OS-xjtn).\n\nComponent: persona_config (Phase 1_nucleus, owner=aiden)\nStatus pre-migration: proven (last_verified 2026-06-02)\n\nEVIDENCE (verbatim from Dave addendum 2026-06-02):\nverified token counts in persona_bank (supabase migration 20260529_persona_bank_seed_v1_chain.sql).\n\nCompanion evidence: PR #1389 [ATLAS] feat(persona_bank): rebuild Nova/Orion/Atlas to production depth (KEI Agency_OS-xjtn) — back-half rebuild with verified token counts nova 1475 / orion 1778 / atlas 2224 via (char_length+3)/4 ceil; dry-run executed against jatzvazlbusedwsnqxzr 2026-06-01.\n\nCaveat (verbatim from gate_roadmap.notes): persona depth alone does NOT fix theatre; verdict_enforcement still required.\n\nAttestation: binding_reviewer Dave at migration apply time.',
           '9e49def7526ffab1e65a026a7232dbfcbabf18352e565efe03774bbfd14bf4ae',
           0,
           'dave',
           'bootstrap-migration-20260602-persona_config'
      FROM public.gate_roadmap
     WHERE component = 'persona_config'
       AND NOT EXISTS (
            SELECT 1 FROM public.gate_proof_runs
             WHERE gate_roadmap_id = public.gate_roadmap.id
       )
    RETURNING id, gate_roadmap_id
)
UPDATE public.gate_roadmap gr
   SET proof_run_id = proof.id
  FROM proof
 WHERE gr.id = proof.gate_roadmap_id
   AND gr.proof_run_id IS NULL;


-- 7c. temporal_runtime (builder=aiden) --------------------------------------
SET LOCAL agency_os.callsign = 'aiden';
UPDATE public.gate_roadmap
   SET built_by_callsign = 'aiden'
 WHERE component = 'temporal_runtime'
   AND built_by_callsign IS NULL;

SET LOCAL agency_os.callsign = 'dave';
WITH proof AS (
    INSERT INTO public.gate_proof_runs
        (gate_roadmap_id, attestation_kind, run_cmd, run_output, output_sha256,
         exit_code, attesting_callsign, attester_session_uuid)
    SELECT id,
           'binding_reviewer',
           'BOOTSTRAP — anchor: cat /tmp/v1_chain_state.json | jq .runs[] | length; 2026-06-02 5/5-hop v1 chain runs visible there + xjtn-case-a chain artifact. No CI re-run available pre-gate-authoring.',
           E'BOOTSTRAP proof_run — citing real evidence per Dave directive 2026-06-02 (KEI Agency_OS-xjtn).\n\nComponent: temporal_runtime (Phase 0_foundation, owner=aiden)\nStatus pre-migration: proven (last_verified 2026-06-02)\n\nEVIDENCE (verbatim from Dave addendum 2026-06-02):\n2026-06-02 5/5-hop v1 chain runs (chain IDs: xjtn-case-a and completed chains in /tmp/v1_chain_state.json).\n\nScope: durability/crash-recovery proof is separate (temporal_chain, not_started). This bootstrap row backs the runtime-engine-is-live claim only.\n\nAttestation: binding_reviewer Dave at migration apply time. No CI run available pre-gate. Future re-attestation should land via ci_runner with gate_ledger_id once CI gate is authored for temporal_runtime.',
           'c6ab9fbd25f6cfb040ee787583b5072143768f5336610833e025f0e7e873547d',
           0,
           'dave',
           'bootstrap-migration-20260602-temporal_runtime'
      FROM public.gate_roadmap
     WHERE component = 'temporal_runtime'
       AND NOT EXISTS (
            SELECT 1 FROM public.gate_proof_runs
             WHERE gate_roadmap_id = public.gate_roadmap.id
       )
    RETURNING id, gate_roadmap_id
)
UPDATE public.gate_roadmap gr
   SET proof_run_id = proof.id
  FROM proof
 WHERE gr.id = proof.gate_roadmap_id
   AND gr.proof_run_id IS NULL;


-- Restore session-var to 'dave' for downstream operations + tests.
SET LOCAL agency_os.callsign = 'dave';


-- ============================================================================
-- 8. NEGATIVE TESTS — MANDATORY per Dave addendum item 1.
--
-- "The gate is only proven when it BLOCKS the thing it exists to block.
--  Happy-path pass is necessary but not sufficient."
--
-- Inline DO blocks that exercise the trigger refusal paths. If any expected
-- rejection does NOT fire, the entire migration ROLLBACKs via outer
-- RAISE EXCEPTION. Component names are UUID-suffixed to allow re-running
-- the migration in dev without UNIQUE collision.
-- ============================================================================

DO $$
DECLARE
    test_id_1 UUID;
    test_id_2 UUID;
    test_id_3 UUID;
    test_failed_1 BOOLEAN := FALSE;
    test_failed_2 BOOLEAN := FALSE;
    test_failed_3 BOOLEAN := FALSE;
    suffix TEXT := substr(gen_random_uuid()::text, 1, 8);
BEGIN
    -- ─── TEST 1 ──────────────────────────────────────────────────────────
    -- nova builds, nova attempts self-attestation → trigger_4 step 2 raises.
    PERFORM set_config('agency_os.callsign', 'nova', true);
    INSERT INTO public.gate_roadmap
        (component, phase, proof_gate, status, owner, notes)
    VALUES ('__xjtn_test_self_attest_' || suffix || '__',
            'test', 'test-pending', 'built', 'nova',
            'Negative test for trg_04_gate_proof_no_self_attest. Deleted at end of DO block.')
    RETURNING id INTO test_id_1;

    -- Sanity: capture happened.
    IF NOT EXISTS (SELECT 1 FROM public.gate_roadmap
                    WHERE id = test_id_1 AND built_by_callsign = 'nova') THEN
        RAISE EXCEPTION 'NEGATIVE TEST 1 SETUP FAILED: built_by_callsign=nova not captured by trg_03';
    END IF;

    -- Now attempt self-attestation — must raise.
    BEGIN
        INSERT INTO public.gate_proof_runs
            (gate_roadmap_id, attestation_kind, run_cmd, run_output, output_sha256,
             exit_code, attesting_callsign, attester_session_uuid)
        VALUES (test_id_1, 'binding_reviewer', 'echo self-attest test',
                'NEGATIVE TEST OUTPUT — long enough to pass length >= 32 char floor.',
                '0000000000000000000000000000000000000000000000000000000000000000',
                0, 'nova', 'fake-session-test-1');
        test_failed_1 := TRUE;  -- should not reach here
    EXCEPTION WHEN check_violation THEN
        NULL;  -- expected — trigger_4 step 2 raised on nova == nova
    END;

    DELETE FROM public.gate_roadmap WHERE id = test_id_1;
    IF test_failed_1 THEN
        RAISE EXCEPTION 'NEGATIVE TEST 1 FAILED: self-attestation was NOT blocked by trg_04 — proof-gate is INSECURE.';
    END IF;

    -- ─── TEST 2 ──────────────────────────────────────────────────────────
    -- Binding-reviewer allowlist: nova builds, atlas attempts binding_reviewer
    -- attestation. atlas ∉ ['dave','elliot'] → trigger_4 step 3 raises.
    PERFORM set_config('agency_os.callsign', 'nova', true);
    INSERT INTO public.gate_roadmap
        (component, phase, proof_gate, status, owner, notes)
    VALUES ('__xjtn_test_allowlist_' || suffix || '__',
            'test', 'test-pending', 'built', 'nova',
            'Negative test for binding_reviewer allowlist. Deleted at end of DO block.')
    RETURNING id INTO test_id_2;

    PERFORM set_config('agency_os.callsign', 'atlas', true);
    BEGIN
        INSERT INTO public.gate_proof_runs
            (gate_roadmap_id, attestation_kind, run_cmd, run_output, output_sha256,
             exit_code, attesting_callsign, attester_session_uuid)
        VALUES (test_id_2, 'binding_reviewer', 'echo allowlist test',
                'NEGATIVE TEST OUTPUT — long enough to pass length >= 32 char floor.',
                '1111111111111111111111111111111111111111111111111111111111111111',
                0, 'atlas', 'fake-session-test-2');
        test_failed_2 := TRUE;
    EXCEPTION WHEN check_violation THEN
        NULL;  -- expected — trigger_4 step 3 raised on atlas ∉ allowlist
    END;

    PERFORM set_config('agency_os.callsign', 'dave', true);
    DELETE FROM public.gate_roadmap WHERE id = test_id_2;
    IF test_failed_2 THEN
        RAISE EXCEPTION 'NEGATIVE TEST 2 FAILED: binding_reviewer-allowlist did not refuse atlas — Dave tightening broken.';
    END IF;

    -- ─── TEST 3 ──────────────────────────────────────────────────────────
    -- required_attestation_kind=ci_runner refuses binding_reviewer proof_runs.
    -- elliot builds, then dave (allowlist) attempts binding_reviewer → blocked
    -- by trigger_4 final clause (required_attestation_kind mismatch).
    PERFORM set_config('agency_os.callsign', 'elliot', true);
    INSERT INTO public.gate_roadmap
        (component, phase, proof_gate, status, required_attestation_kind, owner, notes)
    VALUES ('__xjtn_test_required_ci_' || suffix || '__',
            'test', 'test-pending', 'built', 'ci_runner', 'elliot',
            'Negative test for required_attestation_kind=ci_runner policy. Deleted at end of DO block.')
    RETURNING id INTO test_id_3;

    PERFORM set_config('agency_os.callsign', 'dave', true);
    BEGIN
        INSERT INTO public.gate_proof_runs
            (gate_roadmap_id, attestation_kind, run_cmd, run_output, output_sha256,
             exit_code, attesting_callsign, attester_session_uuid)
        VALUES (test_id_3, 'binding_reviewer', 'echo required-kind test',
                'NEGATIVE TEST OUTPUT — long enough to pass length >= 32 char floor.',
                '2222222222222222222222222222222222222222222222222222222222222222',
                0, 'dave', 'fake-session-test-3');
        test_failed_3 := TRUE;
    EXCEPTION WHEN check_violation THEN
        NULL;  -- expected — required_attestation_kind=ci_runner refuses binding_reviewer
    END;

    DELETE FROM public.gate_roadmap WHERE id = test_id_3;
    IF test_failed_3 THEN
        RAISE EXCEPTION 'NEGATIVE TEST 3 FAILED: required_attestation_kind=ci_runner did not refuse binding_reviewer — per-component policy broken.';
    END IF;

    RAISE NOTICE 'NEGATIVE TESTS 1+2+3 PASSED: self-attestation blocked, binding_reviewer allowlist enforced, required_attestation_kind=ci_runner refuses binding_reviewer.';
END $$;

-- Restore session-var (the DO block changes are local-to-block; explicit
-- restore is paranoia + intent-marker for downstream operators).
SET LOCAL agency_os.callsign = 'dave';


-- ============================================================================
-- 9. Verification queries (executed post-apply by the operator).
--
--   -- Confirm all 10 triggers landed:
--   SELECT tgname FROM pg_trigger
--    WHERE tgrelid IN ('public.gate_roadmap'::regclass,
--                      'public.gate_proof_runs'::regclass,
--                      'public.gate_roadmap_history'::regclass)
--      AND tgname LIKE 'trg_%' ORDER BY tgname;
--
--   -- Confirm seed + bootstrap rows landed with correct identity capture:
--   SELECT component, status, built_by_callsign, required_attestation_kind,
--          proof_run_id IS NOT NULL AS has_proof_run
--     FROM public.gate_roadmap
--    WHERE component IN ('product_landing_site','gate_mechanism','persona_config','temporal_runtime')
--    ORDER BY component;
--
--   -- Confirm bootstrap proof_runs visible:
--   SELECT gr.component, pr.attesting_callsign, pr.attestation_kind,
--          pr.ci_run_id, length(pr.run_output) AS output_chars
--     FROM public.gate_proof_runs pr
--     JOIN public.gate_roadmap   gr ON gr.id = pr.gate_roadmap_id
--    ORDER BY gr.component;
--
--   -- Confirm no orphan 'proven' rows (every proven row has a backing proof_run):
--   SELECT component FROM public.gate_roadmap
--    WHERE status = 'proven' AND proof_run_id IS NULL;
--   -- ↑ Expected: zero rows. Non-zero = alarm.
-- ============================================================================
