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

## Run 1 — planted failure (must be RED)

- PR URL: _to be filled in once opened_
- CI run URL: _to be filled in once run completes_
- Result: _to be filled in_
- Job step `Run gates from manifest`: expected to log
  `phase_0_mechanism/gate_PLANTED_FAILURE: FAIL` and exit nonzero.

## Run 2 — planted gate removed (must be GREEN or skipped-only)

- Follow-up commit removing `gate_PLANTED_FAILURE` from `.gates/manifest.json`.
- CI run URL: _to be filled in_
- Result: _to be filled in_
- All remaining gates either pass against live infra or emit `skipped`
  because their config env is not yet wired in CI secrets.

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
