# Deferred Gate Obligations

Dave directive 2026-05-31 — SKIP→ENFORCED ON SHIP rule:
A gate that currently skips (rc=2) because its component doesn't exist yet is TOLERATED ONLY until that component ships. The instant a component is supposedly done but its gate still skips, that is a FAILURE.

## gate_crash_recovery — Agency_OS-jn14
- Skips while: `GATE_CRASH_DISPATCH_CMD` unset (Temporal chain dispatch helper not built)
- Enforced when: Temporal crash recovery ships (V2 Phase 1)
- Close Agency_OS-jn14 with the CI run showing `gate_crash_recovery: pass`

## gate_recall — Agency_OS-rw6r
- Skips while: `HINDSIGHT_URL` unset (recall not proven)
- Enforced when: Hindsight recall ships with populated banks (V2 Phase 5)
- Close Agency_OS-rw6r with the CI run showing `gate_recall: pass`

## gate_atoms — Agency_OS-jjnq
- Skips while: `keiracom_atoms` + `gate_ledger` tables absent from CI DB
- Enforced when: atom store ships (V2 Phase 5)
- Close Agency_OS-jjnq with the CI run showing `gate_atoms: pass`
