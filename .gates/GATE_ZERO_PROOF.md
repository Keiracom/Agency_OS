# Gate Zero Proof — Verification-Gate Mechanism

Dave directive 2026-05-30: before the mechanism goes live, plant a deliberate
failure and prove CI catches it. This document records that proof.

## Procedure

1. Build the mechanism (gate scripts + manifest + CI workflow + ledger).
2. Add `gate_PLANTED_FAILURE` (always exits 1) to `.gates/manifest.json`
   under a phase active in CI.
3. Push a PR. Wait for GitHub Actions `Verification Gate` job to run.
4. Confirm the job goes **RED** because the planted gate exits 1.
5. Once the red proof is captured, remove `gate_PLANTED_FAILURE` from the
   manifest in a follow-up commit on the same PR.
6. Confirm CI now goes **GREEN** (or YELLOW with skipped gates — never
   fake-PASS).
7. Record both runs below.

## Initial state (this PR's first commit)

`.gates/manifest.json` contains:

```json
{
  "phases": {
    "phase_0_mechanism": ["gate_PLANTED_FAILURE"],
    ...
  }
}
```

The phase_0_mechanism gate fires in CI on every PR to main.

## Run 1 — planted failure (RED) ✓

- PR: https://github.com/Keiracom/Agency_OS/pull/1371
- CI run: https://github.com/Keiracom/Agency_OS/actions/runs/26711089656
- Result: **failure** (job conclusion = failure)
- Raw evidence (verbatim from CI job log):

```
::group::phase=phase_0_mechanism
→ running gate=gate_PLANTED_FAILURE
{"gate":"gate_PLANTED_FAILURE","status":"fail","evidence":{"reason":"this gate is the deliberate-failure proof of the verification-gate mechanism; it must exit 1 unconditionally"},"ts":"2026-05-31T11:16:30Z"}
← gate=gate_PLANTED_FAILURE rc=1
::group::phase=phase_1_recall
→ running gate=gate_recall
← gate=gate_recall rc=2
→ running gate=gate_atoms
← gate=gate_atoms rc=2
::group::phase=phase_2_build
→ running gate=gate_git_commit
← gate=gate_git_commit rc=0
::group::phase=phase_3_resilience
→ running gate=gate_crash_recovery
← gate=gate_crash_recovery rc=2
==== gate_check summary ====
  phase_0_mechanism/gate_PLANTED_FAILURE: FAIL
```

Result confirmed: the planted-failure gate produced `rc=1`, the workflow
recorded it as `FAIL` in the summary, and the overall job exited nonzero
(`conclusion: failure`). The CI mechanism caught the deliberate failure.

Other gates in the same run:
- `gate_recall`, `gate_atoms`, `gate_crash_recovery`: `rc=2` (skipped — no
  HINDSIGHT_URL / DATABASE_URL / GATE_CRASH_DISPATCH_CMD wired in CI yet).
  These are honest skips, not fake passes. Wiring those secrets is a
  separate decision (see "Next steps" below).
- `gate_git_commit`: `rc=0` (passed — the PR added commits, so HEAD has
  advanced versus HEAD~1).

## Run 2 — planted gate removed (must be GREEN or skipped-only)

- Follow-up commit on this same PR removed `gate_PLANTED_FAILURE` from
  `.gates/manifest.json` (`phase_0_mechanism: []`).
- CI run: _filled in by a third commit once Run 2 completes_
- Expected result: success (or success with `rc=2` skips on real gates
  whose config env is not yet wired).

## What this proves

- A gate that exits nonzero **stops** the CI job. The mechanism cannot be
  bypassed by an agent claiming "done" in prose. Verified end-to-end in
  Run 1.
- Adding/removing a gate is a manifest edit — gates are data, not code.
- The PR author does not write the ledger row. GitHub Actions does, via
  `scripts/gates/verify.sh`. The routing-violation check fires if a
  future gate ever emits `evidence.agent == PR_AUTHOR`.

## Next steps (separate dispatches)

1. Wire CI secrets `GATE_LEDGER_DATABASE_URL` + `HINDSIGHT_URL` so the
   real gates produce pass/fail (not skipped) signal.
2. Dave reviews each gate definition for honesty (tests real OUTPUT, not
   mere existence).
3. Add the routing-violation evidence assertion as a positive test once
   any gate emits `evidence.agent`.

## Permanent invariants the mechanism enforces

1. **Done = proven**: a gate that exits 0 with honest JSON evidence is the
   sole acceptable definition of done for any task that has a gate.
2. **Phase advancement is data-driven**: `check_phase_ready.sh <phase>`
   reads `gate_ledger` for the latest status of each gate in that phase.
   No agent prose can flip it.
3. **Rehearsal is locked behind every phase passing**: `rehearsal_ready.sh`
   iterates the manifest's phases and aborts if any gate is fail/pending.

## What this proves

- A gate that exits nonzero **stops** the CI job. The mechanism cannot be
  bypassed by an agent claiming "done" in prose.
- A gate removal from the manifest takes effect on the next CI run — gates
  are data, not code, so they can be added/retired without touching the
  workflow.
- The PR author does not write the ledger row. GitHub Actions does, via
  `scripts/gates/verify.sh`. Routing-violation check fires if a future
  gate ever emits `evidence.agent == PR_AUTHOR`.

## Permanent invariants the mechanism enforces

1. **Done = proven**: a gate that exits 0 with honest JSON evidence is the
   sole acceptable definition of done for any task that has a gate.
2. **Phase advancement is data-driven**: `check_phase_ready.sh <phase>`
   reads `gate_ledger` for the latest status of each gate in that phase.
   No agent prose can flip it.
3. **Rehearsal is locked behind every phase passing**: `rehearsal_ready.sh`
   iterates the manifest's phases and aborts if any gate is fail/pending.
