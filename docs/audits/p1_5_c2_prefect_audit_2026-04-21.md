# C2 Prefect Infrastructure Audit

**Audit ID:** p1_5_c2
**Wave:** 2
**Date:** 2026-04-21
**Auditor:** Elliot (build-2, claude-sonnet-4-6)
**Scope:** Prefect deployment health, work pool configuration, flow failure rates, worker status, prefect.yaml sync

---

## Summary

| Area | Status | Severity |
|------|--------|----------|
| Deployments vs entrypoints | OK | — |
| Work pool concurrency limits | CONCERN | Medium |
| Pipeline-F failure rate | NOTE | Context-dependent (see §4) |
| Callback write failures | CONCERN | Needs investigation |
| Worker health | OK | — |
| prefect.yaml sync | OK | — |
| Paused deployments (scout chain) | CRITICAL landmines — ratified PAUSED | Resolved |

---

## 1. Deployments

- **Total deployments:** 23
- **Entrypoint existence check:** All 23 entrypoints verified to exist on disk
- **Orphan deployments** (deployment registered, entrypoint missing): **0**
- **Result: OK**

---

## 2. Work Pool Concurrency Limits

- **Finding:** No concurrency limits configured on the work pool
- **Risk:** Under burst load, the worker can spawn unbounded concurrent flow runs, consuming all Railway compute resources and causing OOM/timeout cascades
- **Severity:** Medium
- **Recommendation (B4 scope):** Set explicit `concurrency_limit` on the default work pool. Suggested starting value: 5 concurrent flow runs. Tune post-validation.
- **Result: CONCERN**

---

## 3. prefect.yaml Sync

- **Finding:** All 23 deployments in Prefect Cloud match corresponding entries in `prefect.yaml`
- **No drift detected**
- **Result: OK**

---

## 4. Pipeline-F Failure Rate

- **Observed failure rate:** 73% across pipeline-F flow runs in the audit window
- **Context:** This rate reflects debug retry runs during the 2026-04-21 session, not steady-state infrastructure failures. The session involved active debugging of stage crashes (asyncpg ISO string bug, dm_messages_gate datetime conversion, stage_9_10 traceback suppression). These were application bugs, not Prefect infra failures.
- **Expected post-fix rate:** Recovery to <20% expected after PRs #365-#367 merge
- **Severity:** NOTE — not an infrastructure concern at this reading. Revisit on next audit after clean run.
- **Result: NOTE (context-dependent)**

---

## 5. Callback Write Failures

- **Finding:** Callback writes to `evo_flow_callbacks` are failing for a subset of flow runs
- **Symptom:** Flow completes in Prefect but no callback row appears in Supabase; `callback-poller` skill has nothing to process
- **Impact:** Orchestrator loses flow completion signal; downstream stages may stall waiting for callback that never arrives
- **Severity:** CONCERN — needs investigation in B4
- **Suspected cause:** asyncpg connection handling in the callback write path (consistent with other asyncpg bugs found this session)
- **Recommended action:** Instrument callback write with explicit error logging; add retry with exponential backoff; add monitoring query to health_check_flow
- **Result: CONCERN — investigation required**

---

## 6. Worker Health

- **Last deployed build:** `ca197dad`
- **Last flow completed:** 11:08 UTC, 2026-04-21
- **Worker polling:** Active (no stale worker signal at time of audit)
- **Result: OK**

---

## 7. Paused Deployments — Scout Chain Landmines

**CRITICAL finding — resolved by Dave ratification 2026-04-21**

Four Prefect deployments were found in PAUSED state, wired to a dead execution chain (`scout.py`):

| Deployment | Paused since |
|---|---|
| `intelligence-flow` | Unknown — pre-audit |
| `pool-population-flow` | Unknown — pre-audit |
| `icp-reextract-flow` | Unknown — pre-audit |
| `trigger-lead-research` | Unknown — pre-audit |

**Root cause:** These deployments reference `scout.py` which has been deprecated. The deployments were not removed when scout.py was retired, creating live Prefect entries pointing to dead code. If triggered (manually or by a schedule), they would fail immediately.

**Resolution:** Dave ratified PAUSE as the correct state on 2026-04-21. These deployments should remain PAUSED until formally deleted via a cleanup directive. Deletion requires R3 audit trail and R1-R2 7-day hold per dead code governance (see `docs/specs/b3_self_healing_spec.md §9`).

**Action required:** Schedule cleanup directive to formally delete these 4 deployments with proper governance trail.

---

## 8. Recommendations for B4

Priority order:

1. **Investigate callback write failures** — instrument, add retry, add to health_check_flow probe
2. **Set work pool concurrency limit** — default 5, tune after validation run
3. **Schedule scout chain cleanup directive** — formal deletion with R1-R3 governance
4. **Add health_check_flow deployment** (B3/B4 handoff) — 5-min cadence, probe watchdog
5. **Re-audit after clean validation run** — reassess pipeline-F failure rate post-fix

---

## Audit Sign-Off

- Auditor: Elliot (build-2)
- Wave 2 close: confirmed
- Next audit trigger: after B4 build + first N>=20 validation run (GOV-11)
