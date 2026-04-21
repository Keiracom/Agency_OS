# P4 Prefect Status Audit — Elliot Draft

**Date:** 2026-04-20
**Auditor:** Elliot (Build Agent 2, claude-sonnet-4-6)
**Methodology:** Desk audit from ceo_memory keys (`ceo:phase_1_pipeline`, `ceo:prefect_state`, `ceo:phase_1_5_operational_autonomy`, `ceo:roadmap_master`), flow file inventory in `src/orchestration/flows/`, and pipeline module inventory in `src/pipeline/` + `src/orchestration/`. No live API calls. Evidence cited inline.

---

## 1. TL;DR

Pipeline F v2.1 (the validated, ratified enrichment pipeline) and the Prefect automation layer are two completely separate systems that have never been connected.

- **Pipeline F v2.1** lives in `src/pipeline/pipeline_orchestrator.py` (9-stage streaming), wrapped by `src/orchestration/cohort_runner.py` (CLI). It has been validated through D2/D2.2 with real API calls and contains all ratified logic: blocklist, affordability gate, intent scoring, DM identification, and contact waterfall.
- **Prefect flows** in `src/orchestration/flows/` use a different, older architecture: `scout.enrich_batch()` via `src/engines/scout.py` and `siege_waterfall`. None of them import `PipelineOrchestrator` or call `cohort_runner`.
- The single exception is `stage_9_10_flow.py`, which imports Stage 9 and Stage 10 modules from `src/pipeline/` — making it the only Prefect flow that touches Pipeline F code at all.

**P4's core work — rebuilding Prefect flows 1–8 to call Pipeline F stages — has not started.**

ceo_memory confirms: `ceo:phase_1_pipeline → P4: Prefect flow rebuild (automated Stages 1-10) — in_progress`. The `in_progress` status is aspirational; no flow rebuild code has landed.

---

## 2. Per-Stage Wiring Table

| Stage | Pipeline F v2.1 Module | Prefect Flow | Status |
|-------|------------------------|--------------|--------|
| 1 — Discovery | `src/pipeline/stage_1_discovery.py` (inferred from orchestrator) | `pool_population_flow.py` exists BUT calls `siege_waterfall` via `src/engines/scout.py` — NOT Pipeline F | **STALE PARALLEL** |
| 2 — Spider scrape | `src/pipeline/pipeline_orchestrator.py` (stage 2 internal) | None | **NOT WIRED** |
| 3 — DNS + ABN + DM pre-screen | `src/pipeline/pipeline_orchestrator.py` (stage 3 internal) | None | **NOT WIRED** |
| 4 — Affordability gate | `src/pipeline/pipeline_orchestrator.py` (stage 4 internal) | None | **NOT WIRED** |
| 5 — Intent free gate | `src/pipeline/pipeline_orchestrator.py` (stage 5 internal) | None | **NOT WIRED** |
| 6 — Paid enrichment (DFS) | `src/pipeline/pipeline_orchestrator.py` (stage 6 internal) | None | **NOT WIRED** |
| 7 — Intent full score | `src/pipeline/pipeline_orchestrator.py` (stage 7 internal) | None | **NOT WIRED** |
| 8 — DM identification + contact waterfall | `src/pipeline/pipeline_orchestrator.py` + `src/orchestration/cohort_runner.py` | None | **COHORT-RUNNER-ONLY** |
| 9 — VR enrichment | `src/pipeline/stage_9_vulnerability_enrichment.py` | `stage_9_10_flow.py` ✓ | **WIRED** |
| 10 — Message generation | `src/pipeline/stage_10_message_generator.py` | `stage_9_10_flow.py` ✓ | **WIRED** |

**Status key:**
- WIRED — Prefect flow calls Pipeline F module directly
- STALE PARALLEL — Prefect flow exists but calls old scout/siege architecture, not Pipeline F
- COHORT-RUNNER-ONLY — Runnable manually via CLI cohort_runner.py, no Prefect trigger
- NOT WIRED — Pipeline F module exists, no Prefect entry point of any kind

---

## 3. Prefect Flow Inventory

| Flow File | Purpose | Architecture Used | Status |
|-----------|---------|------------------|--------|
| `pool_population_flow.py` | Discovers new companies, fills pool | Old: `siege_waterfall` via `src/engines/scout.py` | Active/Stale (old arch) |
| `enrichment_flow.py` | Enriches a batch of leads | Old: `scout.enrich_batch()` | Active/Stale (old arch) |
| `intelligence_flow.py` | Hot lead deep research | Old: scout engine | Active/Stale (old arch) |
| `batch_controller_flow.py` | Quota monitoring + ICP filter, triggers discovery | Old: scout engine; no Pipeline F calls | Active/Stale (old arch) |
| `stage_9_10_flow.py` | VR enrichment + message generation | **Pipeline F v2.1** — imports `Stage9VulnerabilityEnrichment`, `Stage10MessageGenerator` | Active, wired |

All flows reference `src/orchestration/flows/`. No flow in this directory imports `PipelineOrchestrator` from `src/pipeline/pipeline_orchestrator.py` except `stage_9_10_flow.py` (stages 9–10 only).

---

## 4. Infrastructure Health

| Component | State | Evidence |
|-----------|-------|----------|
| Work pool | `agency-os-pool`, concurrency=10 | `ceo:prefect_state` |
| Worker | `src/orchestration/worker.py` — Prefect 3.x PrefectAgent, polls SCHEDULED/PENDING | Code inventory |
| Zombie flows | 0 | `ceo:prefect_state → zombie_count: 0, last_cleanup: 2026-04-03` |
| Callback system (EVO-003) | `evo_flow_callbacks` table exists; `src/prefect_utils/completion_hook.py` writes rows on completion/failure; most flows wired via `@flow(on_completion=[on_completion_hook])` | Code inventory |
| Schedules | `scheduled_jobs.py` defines: enrichment (2AM daily), outreach (hourly 8AM–6PM), reply recovery (15min), CIS learning (weekly), credit reset (monthly), DNCR rewash (quarterly), LinkedIn health (daily), daily pacing, monthly replenishment, recording cleanup | Code inventory |
| Railway deployment | Target platform confirmed; plan/tier not verified in this audit | `ceo:phase_1_5_operational_autonomy` note |
| Telegram alerts | Wired | `ceo:prefect_state → alert_status: telegram_wired` |
| Prior audit debt | April 3 audit found 8 zombies + no concurrency limits + Railway hobby tier risk — zombies cleared, concurrency now set | `ceo:phase_1_5_operational_autonomy → C2_prefect_reaudit: pending (P2)` |

Infrastructure is healthy for the existing (old-arch) flows. The blocker is not infra — it is the missing wiring from Prefect into Pipeline F stages 1–8.

---

## 5. Gap Analysis: What Remains Before P5

P5 definition (from `ceo:phase_1_pipeline`): automated E2E run, zero manual intervention, 10 fresh AU domains, `dm_messages` verified.

### 5.1 Required Prefect flow work (Stages 1–8)

Each item below is a distinct build task. None has started.

1. **Stage 1 flow** — Replace or extend `pool_population_flow.py` to call Pipeline F `stage_1_discovery.py` instead of `siege_waterfall`. Decision needed: replace or create a new `pipeline_f_discovery_flow.py` alongside the old flow.
2. **Stage 2 flow** — New Prefect flow wrapping the spider/scrape stage from `pipeline_orchestrator.py`. No existing flow to repurpose.
3. **Stage 3 flow** — New flow: DNS + ABN + pre-screen DM pass.
4. **Stage 4 flow** — New flow: affordability gate. Must enforce GOV-12 (gate as runtime code, not comment).
5. **Stage 5 flow** — New flow: intent free-tier gate.
6. **Stage 6 flow** — New flow: paid enrichment (DataForSEO). Requires API key in Railway env vars.
7. **Stage 7 flow** — New flow: intent full-score pass.
8. **Stage 8 flow** — New flow: DM identification + contact waterfall (currently cohort_runner.py CLI only).
9. **Orchestration DAG** — A top-level `pipeline_f_full_flow.py` or scheduler that sequences flows 1–10 with inter-stage data handoff (currently `pipeline_orchestrator.py` handles this in-process; Prefect needs a DAG equivalent or subflow chain).
10. **Data handoff contract** — Decide and implement: does each Prefect stage flow write to Supabase and the next stage reads from it, or do they pass in-memory via subflow returns? `cohort_runner.py` currently runs all stages sequentially in one process — this contract must be pinned before any flow is built.

### 5.2 Verification gaps

- No Prefect deployment YAML exists for any Pipeline F stage flow (stages 1–8).
- `scheduled_jobs.py` has no schedule entry for a Pipeline F end-to-end run.
- `stage_9_10_flow.py` is wired but its trigger path assumes upstream stages have already populated the data — there is no automated upstream that feeds it via Pipeline F today.

### 5.3 Prerequisite decisions (not builds)

- **Data handoff contract** (see 5.1 item 10) — blocks all flow design.
- **Old vs new flow coexistence** — `pool_population_flow.py` and `enrichment_flow.py` may still be in use for live outreach. Replacing them without a cutover plan risks disrupting active campaigns. Dave must decide: parallel tracks or hard cutover.

---

## 6. Dave-Lane Blockers

| # | Blocker | Why it blocks |
|---|---------|--------------|
| D1 | **Data handoff contract decision** — in-memory subflows vs Supabase row-per-stage | No flow architecture can be finalized without this. Affects every stage 1–8 flow design. |
| D2 | **Old flow coexistence policy** — replace `pool_population_flow.py` / `enrichment_flow.py` or run Pipeline F flows in parallel | Determines whether P4 is a cutover or an addition. If active outreach depends on old flows, a hard replace could break live campaigns mid-run. |
| D3 | **Railway plan verification** — `ceo:phase_1_5_operational_autonomy` flagged hobby-tier risk on April 3. Not verified as resolved. If Railway is still on hobby tier, long-running Pipeline F flows (stages 6–8, paid enrichment) may be killed mid-run. | P5 automated run fails silently if Railway kills the worker. |
| D4 | **API key audit for stages 6–8** — DataForSEO (Stage 6), Leadmagic (Stage 8 contact waterfall), Bright Data LinkedIn (Stage 8 DM). These must be set in Railway environment variables before any automated run. Status not confirmed in this audit. | Flows will fail at runtime without verified env vars. |

---

## 7. Effort Estimate to P5-Ready

Scoped by work items, not calendar time.

| Work item | Size | Notes |
|-----------|------|-------|
| D1 + D2 decisions (Dave-lane) | 0 build items | Must resolve before any flow is written |
| Stage 1 flow (replace/extend pool_population_flow) | Medium | Existing flow to repurpose; architecture change needed |
| Stage 2 flow (spider/scrape) | Small–Medium | New flow; stage logic already exists in orchestrator |
| Stage 3 flow (DNS/ABN/DM pre-screen) | Small–Medium | New flow |
| Stage 4 flow (affordability gate, GOV-12) | Small | Gate logic already in orchestrator; runtime enforcement required |
| Stage 5 flow (intent free gate, GOV-12) | Small | Same pattern as Stage 4 |
| Stage 6 flow (paid DFS enrichment) | Medium | API calls; Railway env var dependency (D4) |
| Stage 7 flow (intent full score) | Small | Scoring logic already in orchestrator |
| Stage 8 flow (DM + contact waterfall) | Large | Most complex stage; cohort_runner already has this logic but Prefect wiring + error recovery needed |
| Top-level DAG / subflow chain (stages 1–10) | Medium | Requires data handoff contract finalized (D1) |
| `scheduled_jobs.py` entry for Pipeline F E2E | Small | Add schedule once DAG exists |
| Railway plan + env var verification (D3 + D4) | Small (devops) | Verify, don't build |
| P5 E2E validation run (10 AU domains) | Validation run | Final gate; not a build item |

**Minimum critical path to P5:** D1 decision → Stage 1–8 flows → DAG → Railway verify → P5 run.

The `C2_prefect_reaudit` task in `ceo:phase_1_5_operational_autonomy` (P2 priority, still pending) should be folded into P4 scope — it covers the same ground and its findings may affect flow design choices.
