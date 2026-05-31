# ROADMAP V2 — Keiracom Workforce

Source of truth for V2 scope, phasing, and current status.
Status block at the bottom is auto-rendered from `public.gate_roadmap` by
`scripts/roadmap_status.py` on every push to `main`. Do not edit the table
inside the markers manually — your edit will be overwritten on the next push.

Working name "Keiracom" is per `ceo:agency_os_keiracom_separation_v1`
(ratified 2026-05-24). Final commercial brand TBD post-launch.

---

## What "done" looks like

The end state is a machine a customer installs that just runs, improves
itself from its own work, and is transparent about what it is doing.
Off Supabase entirely. Chain on Temporal — durable execution, retries,
audit trail. Secrets in Vault — no plaintext keys on disk. All LLM calls
flow through LiteLLM so the customer's BYOK key, the rate caps, the
governance gates, and the cost telemetry sit on a single chokepoint.
Atoms capture every task boundary into Hindsight; recall over those atoms
returns real, scoped signal rather than empty results. Nova commits its
own work inside the activity rather than handing back a string. Stalled
chains surface to Dave (and, post-launch, to the customer) within five
minutes, not silently. The product repo is isolated from the fleet repo,
so a tenant install carries nothing that the tenant should not see.

---

## Phases

### Phase 0 — Gate mechanism (PROVEN, CLOSED 2026-05-31)

- **Proof gate:** Phase 0 CI gates fire pass/fail/skip correctly; the
  mechanism itself exists and is exercised on every push.
- **Components:** `gate_mechanism`.
- **Outcome:** CLOSED per Dave 2026-05-31 (CI run 26711089656 sealed the
  proof). See `ceo:gate_skip_enforced_rule_v1` `phase_0_status`.

### Phase 1 — Temporal chain

- **Proof gate:** Temporal workflow + activities run end-to-end on the
  VPS, and crash recovery is verified by killing the worker mid-chain
  and observing automatic resume.
- **Components:** `temporal_chain`, `dispatcher_retirement`.
- **Sequencing:** Dave's call — riskiest-first. Temporal is both the
  riskiest (durable execution semantics we don't yet operate) and the
  most reversible (Supabase stays live as fallback during the build).
  The custom dispatcher is deleted on Phase 1 pass, not before.

### Phase 2 — Infrastructure migration

- **Proof gate:** Supabase fully retired; Vault holds every secret;
  LiteLLM routes every LLM call; self-hosted Postgres carries the live
  workload.
- **Components:** `vault_secrets`, `litellm_routing`,
  `postgres_self_hosted`, `gate_roadmap_migration` (META — this very
  table moving with the rest of the data), `roadmap_doc_relocation`
  (META — this doc moving to the product repo when it's carved out).
- **Hard gate:** R2 offsite backup must be configured AND a restore must
  be verified end-to-end **before** the first client data row crosses
  into the self-hosted Postgres. Backup that has never been restored is
  not a backup.

### Phase 3 — Memory + atoms

- **Proof gate:** Atoms write at every task boundary, and recall against
  populated Hindsight banks returns real signal (not empty results and
  not boilerplate).
- **Components:** `atom_capture`, `atom_recall`.

### Phase 4 — Nova + reliability

- **Proof gate:** Nova commits its own work inside the workflow activity
  (not a returned string the orchestrator has to commit on its behalf),
  AND a stalled chain surfaces to Dave within 5 minutes.
- **Components:** `nova_commits`, `failure_notification`.

---

## Decisions log

### Dave's three corrections (2026-05-31)

1. **Supabase scope: expanded from "chain state only" to "full platform
   retirement".** Every table moves — `ceo_memory`, CIS, the pipeline
   tables, client data, agent memories, chain state. Nothing stays.
2. **Prefect stays.** The outbound sales pipeline (discovery + enrichment
   + 4-channel outreach) keeps running on Prefect. V2 scope is the
   agent fleet chain only.
3. **Go sidecar stays.** Ratified at V1 launch; not in V2 scope.

### SKIP → ENFORCED ON SHIP rule (Dave ratified 2026-05-31)

A gate that currently skips (rc=2) is tolerated **only while** its
component genuinely does not exist. The instant a component is supposedly
done but its gate still skips, that is a **FAILURE**, not a pass. Applies
to every phase, every gate, every PR. Recorded in
`ceo:gate_skip_enforced_rule_v1`; deferred-gate obligations tracked in
`.gates/deferred_gates.md`.

### Atom capture + recall (RATIFIED)

Hindsight self-hosted as the memory engine; atoms write at every task
boundary via the Ingest primitive; recall must return real results as
DoD for Phase 3. Phase 3 does not start until Phase 3 components are
genuinely built — no early-promotion off paper readiness.

### Dual concur on Temporal workflow definitions

Any change to Temporal workflow definitions requires concur from **two**
deliberators. Topology changes are governance-level, not routine code
review. Standard 2-of-3 deliberator concur still applies to everything
else.

### Phase ordering — riskiest-first

Temporal is Phase 1 because it's both the riskiest (we don't operate it
yet) and the most reversible (Supabase remains live during the build,
so a Phase 1 failure does not strand state). Each phase gates the next;
no parallel phase execution.

---

## Deferred list

- **KEI-198** — crash recovery spec; runs in parallel with Phase 1
  Temporal build (so the spec hardens against what we actually
  observe, not what we predict).
- **`gate_atoms`** — currently SKIPPED (the `keiracom_atoms` table is
  not yet on the CI database). Becomes ENFORCED when the atom store
  ships (`Agency_OS-jjnq`). See `.gates/deferred_gates.md`.
- **`gate_recall`** — currently SKIPPED (no `HINDSIGHT_URL`). Becomes
  ENFORCED when Hindsight recall ships with populated banks
  (`Agency_OS-rw6r`). See `.gates/deferred_gates.md`.
- **`gate_crash_recovery`** — currently SKIPPED (no
  `GATE_CRASH_DISPATCH_CMD`). Becomes ENFORCED when Temporal crash
  recovery ships (`Agency_OS-jn14`). See `.gates/deferred_gates.md`.
- **Product repo name** — `keiracom-core` (Dave confirmed); the actual
  repo creation is deferred until Phase 2.0 carve-out.
- **LiteLLM / claude-CLI base-URL investigation** — required **before**
  Phase 3 coding begins, not during.
- **Build-hop 40 min timeout** — acceptable when paired with a
  heartbeat. A held slot at 40 min surfaces to Dave; it does not get
  silently eaten.

---

## Current status

<!-- STATUS_BLOCK_START -->
<!-- auto-generated by scripts/roadmap_status.py — do not edit manually -->
<!-- run: python3 scripts/roadmap_status.py --render to see current state -->
<!-- STATUS_BLOCK_END -->
