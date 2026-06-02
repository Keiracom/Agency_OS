# Proof-Gate for `gate_roadmap.status='proven'` — Safety-Lens Design (Atlas)

**KEI:** Agency_OS-xjtn (Dave directive 2026-06-02 via Elliot dispatch)
**Status:** DRAFT — awaiting Aiden architecture-lens sync. No migration to be applied without Dave's approval.
**Lens:** Safety / production-readiness (Atlas). Pairs with Aiden's architecture-lens draft.

---

## 1. Problem statement

`gate_roadmap.status` accepts `'proven'` today with no structural backing. Any agent with `DATABASE_URL` can `UPDATE gate_roadmap SET status='proven' WHERE component=…` and the roadmap will render the green tick. There is no requirement that a re-runnable proof exists, no requirement that the attestation party is independent of the builder, no anti-retroactive-fabrication, no audit trail.

The dispatch's four safety asks:

1. **DB-level non-self-attestation enforcement** (not app-level checks the agent can route around)
2. **Same-callsign creation of proof_run AND attestation must be prevented**
3. **Retroactive proof-run fabrication must be prevented**
4. **Audit trail must exist**

---

## 2. Threat model (what we are defending against)

| # | Threat | Source | Today's defense |
|---|---|---|---|
| T1 | Agent writes `status='proven'` with no proof | Any callsign with DSN | None |
| T2 | Agent writes the proof_run themselves to satisfy a future existence check | Building agent | None (proposed trigger must address) |
| T3 | Agent writes proof_run claiming a peer attested | Building agent forging `attested_by` | None |
| T4 | Agent backdates / rewrites a proof_run after the gate is set | Any writer | None |
| T5 | Agent inserts proof_run referencing CI output it didn't actually run | Building agent | None |
| T6 | Two agents collude — A builds, B attests A's work, then A attests B's work in turn | Two callsigns | Hardest case; partial defense via attestation_kind |
| T7 | An attacker with DB credentials can claim to be CI | Any DSN holder | KEI-87 callsign-write-guard pattern (session var) |

The safety design must close T1–T5 at the trigger layer; T6 is structurally bounded (needs human attestation for high-trust gates); T7 is closed by the existing KEI-87 mechanism extended to this table.

---

## 3. Schema — `public.proof_runs`

```sql
-- DESIGN ONLY — DO NOT APPLY until Dave approves.
SET LOCAL agency_os.callsign = 'dave';

CREATE TABLE public.proof_runs (
    id                    UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    gate_roadmap_id       UUID         NOT NULL REFERENCES public.gate_roadmap(id) ON DELETE RESTRICT,
    gate_ledger_id        UUID         REFERENCES public.gate_ledger(id) ON DELETE RESTRICT,

    -- The four dispatch requirements (a)-(d):
    rerun_command         TEXT         NOT NULL,           -- (a) reproducible command
    captured_output       TEXT         NOT NULL,           -- (b) verbatim stdout+stderr
    exit_code             INTEGER      NOT NULL CHECK (exit_code = 0),  -- (b) exit 0 only
    attested_by           TEXT         NOT NULL,           -- (c) party making the attestation
    attestation_kind      TEXT         NOT NULL
                          CHECK (attestation_kind IN ('ci_runner', 'binding_reviewer')),
    attested_at           TIMESTAMPTZ  NOT NULL DEFAULT NOW(),  -- (d) immutable server-time

    -- Anti-fabrication anchors:
    written_by_callsign   TEXT         NOT NULL,           -- captured from session var by trigger
    output_sha256         TEXT         NOT NULL,           -- SHA-256 of captured_output, write-once
    ci_run_id             TEXT,                            -- required when attestation_kind='ci_runner'
    ci_run_url            TEXT,                            -- audit link

    created_at            TIMESTAMPTZ  NOT NULL DEFAULT NOW(),

    -- One unique proof per (gate_roadmap_id, output content). Resubmitting the
    -- same exact output for the same gate is refused; a re-attestation must
    -- produce a meaningfully different run (different timestamp / metadata / output).
    UNIQUE (gate_roadmap_id, output_sha256)
);

CREATE INDEX idx_proof_runs_gate_roadmap ON public.proof_runs (gate_roadmap_id);
CREATE INDEX idx_proof_runs_gate_ledger  ON public.proof_runs (gate_ledger_id);

-- gate_roadmap gains a column that links to the proof_run that justified
-- its 'proven' transition. NULL while status != 'proven'. Set by trigger.
ALTER TABLE public.gate_roadmap
  ADD COLUMN proof_run_id UUID REFERENCES public.proof_runs(id),
  ADD COLUMN built_by_callsign TEXT;   -- captured at status='built' transition, frozen thereafter
```

**Why `gate_roadmap.built_by_callsign`?** Non-self-attestation requires knowing who built. `gate_roadmap.owner` is aspirational (set by orchestrator at row creation, may be stale). The builder is the agent that actually flipped `status` to `'built'`. We capture this at-the-moment of that transition into an immutable column. See §4 trigger 5.

---

## 4. Triggers — five layers of defense

### 4.1 `proof_runs_write_guard` (BEFORE INSERT on `proof_runs`)

Captures the writer's session-var callsign, validates writer-role consistency, blocks impersonation.

```plpgsql
CREATE OR REPLACE FUNCTION public.proof_runs_write_guard()
RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE
    caller text := current_setting('agency_os.callsign', true);
    expected_writer_set text[];
BEGIN
    IF caller IS NULL OR caller = '' THEN
        RAISE EXCEPTION 'proof_runs write-guard: agency_os.callsign session var missing — refused'
            USING ERRCODE = 'check_violation';
    END IF;

    -- The row's written_by_callsign MUST be the session-var caller. No proxy claims.
    NEW.written_by_callsign := caller;

    -- Role validation: who is allowed to write each attestation_kind?
    IF NEW.attestation_kind = 'ci_runner' THEN
        -- Only the GitHub Actions service callsign may write CI-runner attestations.
        -- (The exact string is implementation-defined; mirror gate_ledger's writer.)
        expected_writer_set := ARRAY['github_actions'];
    ELSIF NEW.attestation_kind = 'binding_reviewer' THEN
        -- Only the human-binding callsigns. Agents NEVER write this kind.
        expected_writer_set := ARRAY['dave', 'elliot'];
    END IF;

    IF NOT (caller = ANY (expected_writer_set)) THEN
        RAISE EXCEPTION 'proof_runs write-guard: callsign=% may not write attestation_kind=%; allowed: %',
                        caller, NEW.attestation_kind, expected_writer_set
            USING ERRCODE = 'check_violation';
    END IF;

    -- attested_by MUST equal the actual writer. Prevents an agent claiming
    -- "Dave attested" while writing under its own callsign.
    IF NEW.attested_by IS DISTINCT FROM caller THEN
        RAISE EXCEPTION 'proof_runs write-guard: attested_by=% does not match writer callsign=% — refused',
                        NEW.attested_by, caller
            USING ERRCODE = 'check_violation';
    END IF;

    -- output_sha256 must match the hash of captured_output (computed in trigger).
    IF NEW.output_sha256 IS DISTINCT FROM encode(digest(NEW.captured_output, 'sha256'), 'hex') THEN
        RAISE EXCEPTION 'proof_runs write-guard: output_sha256 mismatch with captured_output content'
            USING ERRCODE = 'check_violation';
    END IF;

    -- ci_run_id is required when attestation is from CI.
    IF NEW.attestation_kind = 'ci_runner' AND (NEW.ci_run_id IS NULL OR NEW.ci_run_id = '') THEN
        RAISE EXCEPTION 'proof_runs write-guard: ci_run_id required for ci_runner attestation'
            USING ERRCODE = 'check_violation';
    END IF;

    RETURN NEW;
END;
$$;

CREATE TRIGGER proof_runs_write_guard
    BEFORE INSERT ON public.proof_runs
    FOR EACH ROW EXECUTE FUNCTION public.proof_runs_write_guard();
```

**What this closes:** T3 (`attested_by` forging), T5 (writer impersonating CI), T7 (privileged-callsign theft mitigated by session-var capture).
**Requires:** `pgcrypto` extension for `digest()` (already present per existing migrations).

### 4.2 `proof_runs_immutability` (BEFORE UPDATE OR DELETE on `proof_runs`)

Append-only enforcement. Once written, the row is frozen.

```plpgsql
CREATE OR REPLACE FUNCTION public.proof_runs_immutability()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    RAISE EXCEPTION 'proof_runs is append-only — UPDATE/DELETE refused. Use a new INSERT for a new attestation.'
        USING ERRCODE = 'check_violation';
END;
$$;

CREATE TRIGGER proof_runs_immutability_block
    BEFORE UPDATE OR DELETE ON public.proof_runs
    FOR EACH ROW EXECUTE FUNCTION public.proof_runs_immutability();
```

**What this closes:** T4 (retroactive fabrication / output rewriting). The `attested_at` timestamp captured by `DEFAULT NOW()` cannot be modified after the fact. The `captured_output` cannot be rewritten to retroactively match a later-discovered correct output. If the proof was wrong, you write a NEW proof_run — the old one stays as audit evidence of the bad claim.

### 4.3 `proof_runs_no_self_attestation` (BEFORE INSERT on `proof_runs`, FIRES AFTER write_guard)

The dispatch's core ask. Enforces that the attester is not the builder.

```plpgsql
CREATE OR REPLACE FUNCTION public.proof_runs_no_self_attestation()
RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE
    builder_callsign text;
BEGIN
    SELECT built_by_callsign INTO builder_callsign
      FROM public.gate_roadmap
     WHERE id = NEW.gate_roadmap_id;

    IF builder_callsign IS NULL THEN
        -- The roadmap row was never transitioned to 'built' under the new
        -- regime — refuse proof_run to force the build-transition to be
        -- recorded first (and to prevent a proof_run being inserted for a
        -- row whose builder we cannot identify).
        RAISE EXCEPTION 'proof_runs no-self-attestation: gate_roadmap.built_by_callsign unset for gate_roadmap_id=%; record build transition first',
                        NEW.gate_roadmap_id
            USING ERRCODE = 'check_violation';
    END IF;

    -- Hard rule: the attester is NOT the builder.
    IF NEW.attested_by = builder_callsign THEN
        RAISE EXCEPTION 'proof_runs no-self-attestation: attested_by=% matches gate_roadmap.built_by_callsign=% for gate_roadmap_id=% — building agent cannot attest its own proof',
                        NEW.attested_by, builder_callsign, NEW.gate_roadmap_id
            USING ERRCODE = 'check_violation';
    END IF;

    RETURN NEW;
END;
$$;

CREATE TRIGGER proof_runs_no_self_attestation
    BEFORE INSERT ON public.proof_runs
    FOR EACH ROW EXECUTE FUNCTION public.proof_runs_no_self_attestation();
```

**What this closes:** T2 (building agent self-attestation). The trigger compares against the immutable `built_by_callsign`, not against any field the inserter controls. Combined with §4.5 (build transition captures builder from session-var), this is structurally tight.

### 4.4 `gate_roadmap_proven_requires_proof_run` (BEFORE UPDATE on `gate_roadmap`)

The actual gate. Blocks `status='proven'` without a valid proof_run.

```plpgsql
CREATE OR REPLACE FUNCTION public.gate_roadmap_proven_requires_proof_run()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    -- Only fire when transitioning TO 'proven' (not on idempotent re-writes).
    IF NEW.status = 'proven' AND (OLD.status IS NULL OR OLD.status != 'proven') THEN
        -- The transition must specify which proof_run justifies it.
        IF NEW.proof_run_id IS NULL THEN
            RAISE EXCEPTION 'gate_roadmap proven-requires-proof-run: status=proven requires proof_run_id; set NEW.proof_run_id to an existing proof_runs.id'
                USING ERRCODE = 'check_violation';
        END IF;

        -- That proof_run must exist, link to THIS gate_roadmap row, and pass.
        IF NOT EXISTS (
            SELECT 1 FROM public.proof_runs
             WHERE id = NEW.proof_run_id
               AND gate_roadmap_id = NEW.id
               AND exit_code = 0
        ) THEN
            RAISE EXCEPTION 'gate_roadmap proven-requires-proof-run: proof_run_id=% does not exist, is not linked to gate_roadmap_id=%, or did not pass (exit_code != 0)',
                            NEW.proof_run_id, NEW.id
                USING ERRCODE = 'check_violation';
        END IF;

        -- last_verified is stamped from the proof_run's attested_at — not from
        -- the agent's clock; the agent doesn't pick the timestamp.
        SELECT attested_at INTO NEW.last_verified
          FROM public.proof_runs WHERE id = NEW.proof_run_id;
    END IF;

    RETURN NEW;
END;
$$;

CREATE TRIGGER gate_roadmap_proven_requires_proof_run
    BEFORE UPDATE ON public.gate_roadmap
    FOR EACH ROW EXECUTE FUNCTION public.gate_roadmap_proven_requires_proof_run();
```

**What this closes:** T1 (claiming `'proven'` with no proof). The `last_verified` server-stamp closes T4 from a second angle — the agent cannot lie about WHEN the proof happened.

### 4.5 `gate_roadmap_capture_builder` (BEFORE UPDATE on `gate_roadmap`)

Captures the builder callsign at the `status='built'` transition; freezes it thereafter.

```plpgsql
CREATE OR REPLACE FUNCTION public.gate_roadmap_capture_builder()
RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE
    caller text := current_setting('agency_os.callsign', true);
BEGIN
    -- On first transition to 'built', capture the writer's callsign.
    IF NEW.status = 'built' AND (OLD.status IS NULL OR OLD.status != 'built')
       AND OLD.built_by_callsign IS NULL THEN
        IF caller IS NULL OR caller = '' THEN
            RAISE EXCEPTION 'gate_roadmap capture-builder: agency_os.callsign session var required to record build transition'
                USING ERRCODE = 'check_violation';
        END IF;
        NEW.built_by_callsign := caller;
    END IF;

    -- Once set, built_by_callsign is immutable. Any UPDATE attempting to
    -- change it refuses — even back to NULL, even to a different callsign.
    IF OLD.built_by_callsign IS NOT NULL
       AND NEW.built_by_callsign IS DISTINCT FROM OLD.built_by_callsign THEN
        RAISE EXCEPTION 'gate_roadmap capture-builder: built_by_callsign is frozen (was %, refused change to %)',
                        OLD.built_by_callsign, NEW.built_by_callsign
            USING ERRCODE = 'check_violation';
    END IF;

    RETURN NEW;
END;
$$;

CREATE TRIGGER gate_roadmap_capture_builder
    BEFORE UPDATE ON public.gate_roadmap
    FOR EACH ROW EXECUTE FUNCTION public.gate_roadmap_capture_builder();
```

**Trigger order matters.** PostgreSQL fires `BEFORE` triggers alphabetically on the same table per row. Names chosen so `capture_builder` (CB) fires before `proven_requires_proof_run` (PR), so `built_by_callsign` is set during the same UPDATE that subsequently transitions to `built`. For the `built -> proven` transition, capture is a no-op (already set), then `proven_requires_proof_run` validates.

---

## 5. Audit trail — `public.gate_roadmap_history`

Every status transition writes an immutable history row.

```sql
CREATE TABLE public.gate_roadmap_history (
    id                  UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    gate_roadmap_id     UUID         NOT NULL REFERENCES public.gate_roadmap(id) ON DELETE RESTRICT,
    old_status          TEXT,
    new_status          TEXT         NOT NULL,
    changed_by_callsign TEXT         NOT NULL,                 -- captured by trigger from session var
    proof_run_id        UUID         REFERENCES public.proof_runs(id),
    changed_at          TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE OR REPLACE FUNCTION public.gate_roadmap_log_history()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF NEW.status IS DISTINCT FROM OLD.status THEN
        INSERT INTO public.gate_roadmap_history
            (gate_roadmap_id, old_status, new_status, changed_by_callsign, proof_run_id)
        VALUES
            (NEW.id, OLD.status, NEW.status, current_setting('agency_os.callsign', true), NEW.proof_run_id);
    END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER gate_roadmap_history_log
    AFTER UPDATE ON public.gate_roadmap
    FOR EACH ROW EXECUTE FUNCTION public.gate_roadmap_log_history();

-- Audit table is append-only — same pattern as proof_runs_immutability.
CREATE OR REPLACE FUNCTION public.gate_roadmap_history_immutability()
RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN
    RAISE EXCEPTION 'gate_roadmap_history is append-only — UPDATE/DELETE refused'
        USING ERRCODE = 'check_violation';
END; $$;

CREATE TRIGGER gate_roadmap_history_immutability_block
    BEFORE UPDATE OR DELETE ON public.gate_roadmap_history
    FOR EACH ROW EXECUTE FUNCTION public.gate_roadmap_history_immutability();
```

**Audit queries:**

```sql
-- Full lineage for a component, newest first.
SELECT old_status, new_status, changed_by_callsign, proof_run_id, changed_at
  FROM public.gate_roadmap_history
 WHERE gate_roadmap_id = (SELECT id FROM public.gate_roadmap WHERE component = $1)
 ORDER BY changed_at DESC;

-- Who attested a given component's 'proven'?
SELECT pr.attested_by, pr.attestation_kind, pr.ci_run_url, pr.attested_at,
       gr.built_by_callsign
  FROM public.gate_roadmap gr
  JOIN public.proof_runs pr ON pr.id = gr.proof_run_id
 WHERE gr.component = $1;

-- Components in 'proven' WITHOUT a backing proof_run (should always be empty
-- after migration; if not, raise alarm).
SELECT component FROM public.gate_roadmap
 WHERE status = 'proven' AND proof_run_id IS NULL;
```

---

## 6. Anti-fabrication measures — combined picture

| Threat | Layer of defense |
|---|---|
| T1 — `'proven'` without proof | §4.4 `proven_requires_proof_run` (UPDATE blocked) |
| T2 — agent self-attests | §4.5 `capture_builder` (freezes builder) + §4.3 `no_self_attestation` (compares against frozen builder) |
| T3 — forged `attested_by` | §4.1 `write_guard` (`attested_by` MUST equal session-var callsign) |
| T4 — retroactive rewrite of proof_run | §4.2 `proof_runs_immutability` (no UPDATE / DELETE) + server-side `attested_at = NOW()` + `output_sha256` validation + §4.4 setting `last_verified` from proof_run server-stamp |
| T5 — agent claiming a CI run it didn't perform | §4.1 `write_guard` (CI-runner attestation requires `callsign='github_actions'`, which is a service-account-only callsign) + `ci_run_id` non-null requirement enables out-of-band verification against GitHub Actions API |
| T6 — two-agent collusion (A builds X, B attests X; B builds Y, A attests Y) | Partial defense: triggers prevent A from attesting A's own build, but two distinct agents can cross-attest. **Mitigation:** for high-trust components, the roadmap row's metadata can require `attestation_kind='ci_runner'` (excluding all agent attestations); this is enforced by an OPTIONAL `gate_roadmap.required_attestation_kind` column the trigger consults. For lower-trust components, agent cross-attestation is acceptable BECAUSE the attesting agent is also at reputational risk if the proof is bad. |
| T7 — DB credential leak | KEI-87 mechanism (session-var required) + `ceo_memory_write_guard` precedent. The `github_actions` callsign is set only by the CI runner's wrapper script; no agent has access to the secret that produces this session-var. |

---

## 7. Open questions for Aiden (architecture lens)

1. **Where does `github_actions` get its session-var set?** Proposed: a wrapper script in `.github/workflows/` that runs every gate, runs the proof, and inserts the `proof_runs` row with `SET LOCAL agency_os.callsign = 'github_actions'`. Needs a secret (e.g., `CI_DB_CALLSIGN_TOKEN`) that only the CI runner has. Aiden — is this the right shape for the runner-trust boundary?

2. **`gate_roadmap.required_attestation_kind`** (T6 mitigation) — should this be a new column on `gate_roadmap` (per-component policy) or a global default (e.g., all `phase_2+` components require `ci_runner` attestation)? I lean per-component for flexibility.

3. **`gate_ledger_id` nullable?** I left it nullable to allow `binding_reviewer` attestations that aren't backed by a CI run (e.g., Dave manually verifies a documentation gate). Aiden — is this acceptable, or should every proof_run trace back to a `gate_ledger` row?

4. **Builder identity for already-existing 'built' rows** — at migration time, gate_roadmap rows in `'built'` state have `built_by_callsign = NULL`. Triggers in §4.3 will refuse any proof_run for them. Aiden — backfill plan: query `gate_roadmap_history` (which won't exist yet) or accept that pre-migration `'built'` rows cannot transition to `'proven'` without a Dave-attested override path?

5. **`pgcrypto` for `digest()`** — verify it's enabled on the prod project (`jatzvazlbusedwsnqxzr`). If not, the §4.1 `output_sha256` validation needs an alternative (e.g., the writer computes the hash client-side and the trigger only validates equality).

---

## 8. What was deliberately NOT included

- **No new CHECK on `gate_roadmap.status`** — the existing CHECK already constrains values; the new gate is in the transition trigger.
- **No row-level security policies** — RLS on `proof_runs` would be defense-in-depth, but Supabase's RLS evaluates AFTER triggers; the session-var trigger is the load-bearing layer. RLS can be added as a follow-up if the threat model expands.
- **No migration applied.** This document is design only per dispatch. Migration filename will be `20260603_proof_run_gate.sql` (or whatever date Dave approves), to be authored as a follow-up PR after joint design CONCUR.

---

## 9. Hand-off

- Aiden — please post your architecture-lens draft + cross-check this safety-lens for: enforcement layering, missing threats, scope creep into runtime/perf concerns. Open questions in §7 are the explicit asks.
- Joint document to Elliot inbox once we CONCUR.
- No migration PR until Dave reviews the joint design.
