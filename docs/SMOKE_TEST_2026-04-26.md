# Smoke Test — main branch — 2026-04-26 (Step 1 cleanup)

Run after merging P1 governance hooks, OC1 memory consolidation, P4
batch API, P5 rate limits, P9 context fork, P10 REM backfill, P6
sandbox isolation (+ wire-up), P11 cgroup memory + sidecar, and demo
auth seeding.

## Command

```
pytest --tb=short -q --ignore=tests/test_dncr_client.py
```

`tests/test_dncr_client.py` collects cleanly in isolation but errors
during full-suite collection (pre-existing import-order side-effect on
main; not introduced by this branch). Running it standalone passes
both of its 2 tests.

## Results

| Bucket   | Count |
|----------|------:|
| **passed**   | **2,880** |
| **failed**   | **53**    |
| skipped  | 28    |
| warnings | 141   |
| wall     | 3 min 19 s |

`tests/scripts/` + `tests/config/` (the namespace touched by Step 1):
**264 passed, 0 failed in 2.38 s.**

## Failing groups (all pre-existing on main — none touched by this branch)

| Group | Files | Failures |
|-------|-------|---------:|
| Pipeline orchestrator wiring | `tests/test_pipeline/test_orchestrator_*` | 8 |
| Pipeline parallel orchestrator | `tests/test_pipeline/test_parallel_orchestrator.py` | 3 |
| Pipeline pipeline_orchestrator | `tests/test_pipeline/test_pipeline_orchestrator.py` | 4 |
| Pipeline stage_parallel | `tests/test_pipeline/test_stage_parallel.py` | 7 |
| Stage 9/10 flow | `tests/test_stage_9_10_flow.py` | 4 |
| Card streaming | `tests/unit/test_card_streaming.py` | 3 |
| Other (orchestrator gates etc.) | misc | 24 |

These failures pre-date the Step 1 cleanup branch (`P11 sidecar`,
`demo auth user`). The branch does not modify
`src/pipeline/orchestrator*`, `src/flows/stage_9_10_flow.py`, or any
card-streaming module.

## Verdict

GREEN for the surface this branch touches (264/264 in the affected
namespace). The 53 pipeline/stage failures are existing main-branch
debt that should be triaged separately — flagging in next session
end report.
