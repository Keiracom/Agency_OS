# P4 Prefect Status Audit — Final Converged

**Date:** 2026-04-21
**Authors:** Elliot (build-2) + Aiden (build-3) — independent drafts merged per peer review consensus
**Source drafts:** `p4_audit_elliot_draft.md` + `p4_audit_aiden_draft.md`
**Methodology:** Desk audit. Evidence cited to file:line, commit SHA, or ceo_memory key. Felt-sufficiency flags inline. No live API calls.

---

## 1. TL;DR

**P4 status: PARTIALLY STARTED.**

`ceo:phase_1_pipeline` describes P4 as "Prefect flow rebuild (automated Stages 1–10)" — status `in_progress` (last updated 2026-04-13). What was actually shipped is Stage 9+10 automation only (PR #308, commits 4fa75dc + 00d6e36, `src/orchestration/flows/stage_9_10_flow.py`, 271 lines).

**P4 as shipped ≠ P4 as described in ceo_memory.** This is a material divergence worth resolving before P5 gate evaluation.

The remaining gap is purely wiring. Pipeline logic is validated (D2.2). Automation infrastructure is running (Prefect: 1 pool, concurrency 10, zero zombies as of 2026-04-03 snapshot). They just haven't been connected. Stages 1–8 and the unified end-to-end flow are missing.

**Recommended approach:** Wrap `cohort_runner.run_cohort()` in a `@flow` decorator and promote `_run_stageN` functions to `@task`. Preserves all ratified logic, adds Prefect scheduling + retry + telemetry. Lowest-risk path to P5.

**Dave action required:** Confirm P4 scope (DONE vs IN_PROGRESS) before any P4 build work proceeds. See §6.

---

## 2. Per-Stage Wiring Table

Classification as of HEAD (git log through 2026-04-21):

| Stage | Name | cohort_runner.py? | Prefect flow? | E2E-automated? |
|-------|------|-------------------|---------------|----------------|
| 1 | Discovery (DFS categories + ETV + blocklist) | YES — else branch lines 728–759; DFS `domain_metrics_by_categories`, ETV window filter, `is_blocked()` check | YES via `pool_population_flow.py` — SEPARATE LINEAGE (POOL-012 era, scout engine, pre-v7) | PARTIAL — not connected to cohort_runner path |
| 2 | VERIFY (5 SERP queries) | YES — `_run_stage2` line 216 | NO | Manual only |
| 3 | IDENTIFY (Gemini + DM extraction) | YES — `_run_stage3` line 232 | NO | Manual only |
| 4 | SIGNAL (DFS signal bundle) | YES — `_run_stage4` line 279 | NO | Manual only |
| 5 | SCORE (viability scoring) | YES — `_run_stage5` line 297 | NO | Manual only |
| 6 | ENRICH (historical rank, composite gate ≥60) | YES — `_run_stage6` line 334 | NO | Manual only |
| 7 | ANALYSE (Gemini VR + outreach draft) | YES — `_run_stage7` line 353 | NO | Manual only |
| 8 | CONTACT (email + phone waterfall) | YES — `_run_stage8` line 384 (updated PR #363 to thread lm + bd clients) | NO | Manual only |
| 9 | SOCIAL (LinkedIn scrape, gated verified URL) | YES — `_run_stage9` line 502 | YES — `stage_9_10_flow.py` imports `Stage9VulnerabilityEnrichment` directly | **AUTOMATED** |
| 10 | VR+MSG (value report + outreach, gated email found) | YES — `_run_stage10` line 535 | YES — `stage_9_10_flow.py` imports `Stage10MessageGenerator` directly | **AUTOMATED** |
| 11 | CARD (lead card assembly) | YES — `_run_stage11` line 562 | NO | Manual only |

**Stage 1 correction note:** Aiden's draft originally marked Stage 1 as "NO" in cohort_runner, reading only the `--domains` bypass comment at line 716. The else branch at lines 728–759 contains full DFS category discovery + ETV window filtering + blocklist gate. Stage 1 classification is therefore: **YES in cohort_runner, NO in any Prefect flow that uses the v7 cohort path.**

**Status legend:**
- AUTOMATED — Prefect flow calls Pipeline F v2.1 module directly
- PARTIAL — Prefect flow exists but is a separate lineage; doesn't hand off to cohort_runner
- Manual only — cohort_runner CLI only; no Prefect entry point

---

## 3. Prefect Flow Inventory

31 flow files in `src/orchestration/flows/`. Categorized by P4-relevance:

**P4-core (automates v7 pipeline stages):**
- `stage_9_10_flow.py` (271 lines) — Stage 9+10 automation; PR #308. Only flow that imports Pipeline F v2.1 modules.

**P4-adjacent (touches pipeline but different lineage or purpose):**
- `pool_population_flow.py` (1,031 lines) — Stage 1 discovery via POOL-012 / scout engine. Pre-v7 lineage; not connected to cohort_runner.
- `lead_enrichment_flow.py` (623 lines) — pre-v7 enrichment path
- `enrichment_flow.py` (772 lines) — pre-v7 enrichment path (possibly duplicate-adjacent to `lead_enrichment_flow.py`)
- `rescore_flow.py` — re-score path (monthly cycle per MANUAL.md §5)
- `stale_lead_refresh_flow.py` — refresh path
- `batch_controller_flow.py` — quota monitoring + ICP filter; calls scout engine, no Pipeline F calls

**Non-P4 (outreach, campaign, infra, listener):**
25 remaining flows: `campaign_flow.py`, `campaign_evolution_flow.py`, `outreach_flow.py`, `onboarding_flow.py`, `post_onboarding_flow.py`, `daily_digest_flow.py`, `daily_pacing_flow.py`, `monthly_replenishment_flow.py`, `persona_buffer_flow.py`, `reply_recovery_flow.py`, `voice_flow.py`, `warmup_monitor_flow.py`, `linkedin_health_flow.py`, `marketing_automation_flow.py`, `pattern_backfill_flow.py`, `pattern_learning_flow.py`, `cis_learning_flow.py`, `fire_scheduled_actions_flow.py`, `credit_reset_flow.py`, `dncr_rewash_flow.py`, `infra_provisioning_flow.py`, `recording_cleanup_flow.py`, `domain_pool_maintenance_flow.py`, `pool_assignment_flow.py`, `intelligence_flow.py`

**Deployments:** Only `cis_learning_deployment.py` exists — CIS learning is the only flow with a ratified Prefect deployment. The remaining 30 flow files are defined but deployment status is unverified (felt-sufficiency flag — not confirmed via `prefect deployment ls`).

---

## 4. Infrastructure State

Per `ceo:prefect_state` snapshot dated 2026-04-03 (**18 days old — felt-sufficiency flag; not recently verified**):

| Component | State | Evidence |
|-----------|-------|----------|
| Work pool | `agency-os-pool`, concurrency=10 | `ceo:prefect_state` |
| Worker | `src/orchestration/worker.py` — Prefect 3.x PrefectAgent, polls SCHEDULED/PENDING | Code inventory |
| Zombie flows | 0 at time of snapshot | `ceo:prefect_state → zombie_count: 0, last_cleanup: 2026-04-03` |
| Telegram alerts | Wired | `ceo:prefect_state → alert_status: telegram_wired` |
| EVO-003 callbacks | Module exists: `src/prefect_utils/callback_writer.py`, `src/evo/callback_poller.py`, `.claude/skills/callback-poller/SKILL.md`. Runtime behavior not verified in this audit. | Code + skill inventory |
| Schedules | `scheduled_jobs.py` defines: enrichment (2AM daily), outreach (hourly 8AM–6PM), reply recovery (15min), CIS learning (weekly), credit reset (monthly), DNCR rewash (quarterly), LinkedIn health (daily), daily pacing, monthly replenishment, recording cleanup | Code inventory |
| Deployment | Target: Railway. Plan tier not verified (see §6 D3). Prior audit (2026-04-03) flagged hobby-tier risk — resolution not confirmed. | `ceo:phase_1_5_operational_autonomy` |
| Prior audit debt | `C2_prefect_reaudit` in `ceo:phase_1_5_operational_autonomy` — P2 priority, still pending. April 3 audit found 8 zombies + no concurrency limits. Both cleared per ceo_memory; not re-verified here. Recommend folding C2_prefect_reaudit into P4 scope. | `ceo:phase_1_5_operational_autonomy` |

Infrastructure is healthy for existing (old-arch) flows. The blocker is not infra — it is the missing wiring from Prefect into Pipeline F Stages 1–8.

---

## 5. Gap List to P5

P5 gate (from `ceo:phase_1_pipeline`): automated E2E run, zero manual intervention, 10 fresh AU domains, `dm_messages` verified.

### 5.1 Automate Stages 1–8 into Prefect flows (biggest gap — ~1–2 sessions)

Currently: `cohort_runner.py` is manual-trigger Python orchestration. No Prefect flow wraps Stages 1–8.

Two approaches:
- **(a) Wrap cohort_runner (recommended by both drafts):** Decorate `run_cohort()` with `@flow` and `_run_stageN` functions with `@task`. Preserves all ratified logic, adds Prefect scheduling + retry + telemetry. Minimal new code, maximal reuse of validated pipeline.
- **(b) Build a new master flow from scratch:** Compose Stages 1–8 tasks fresh, chain with `stage_9_10_flow.py`. Higher effort, larger bug surface area.

Both drafts recommend (a). Stage logic is already in cohort_runner — the work is decorating and wiring, not rewriting.

### 5.2 Discovery path reconciliation (~30 min investigation + scoped fix)

Stage 1 IS in cohort_runner (lines 728–759: DFS `domain_metrics_by_categories` + ETV window + blocklist). This SHRINKS the gap from Aiden's original assessment — the discovery logic is already implemented in the v7 cohort path.

Outstanding question: D2 / D2.2 / 100-domain cohort runs — did they use the Stage 1 else-branch in cohort_runner, or were domains injected via `--domains`? If `--domains` was used throughout validation, the Stage 1 Prefect wiring path needs a verified E2E run to confirm it works. Check run logs before assuming Stage 1 in cohort_runner is production-tested.

`pool_population_flow.py` (POOL-012 era) remains a usable discovery source if its output is reconciled with cohort_runner's domain schema — but using it requires a handoff bridge.

### 5.3 E2E automation wiring — master flow (~1 session)

A master Prefect flow that:
1. Discovery: Stage 1 (Prefect-wrapped cohort_runner else-branch, or pool_population handoff) → N fresh AU domains
2. Stages 2–8: Prefect `@task` wrappers of cohort_runner `_run_stageN` functions
3. Stages 9–10: hand off to existing `stage_9_10_flow.py` → dm_messages
4. Stage 11: CARD assembly task
5. Telemetry: Prefect run logs per stage; Telegram alerts on failure; EVO-003 callback on completion

### 5.4 Deployment and schedule (~15 min)

Build a Prefect Deployment for the master flow following `cis_learning_deployment.py` pattern. Decide: manual-only trigger or cron (daily 03:00 AEST for monthly cycle per MANUAL.md §5).

### 5.5 dm_messages verification query (~30 min)

P5 gate requires dm_messages verified:
- Post-run check: `SELECT COUNT(*) FROM public.dm_messages WHERE run_id = ... AND status = 'draft'` ≥ threshold
- Content gate: Stage 8 email scoring gate exists (`email_scoring_gate.py`, commit 0a5f516d) — confirm it is runtime-enforced (GOV-12)
- Dashboard view or export per F21 audit §7.6

### 5.6 F21 holdovers that block the path AFTER P5 (not P4-scope, but flag now)

From `f21_evidence_audit_2026-04-20.md` (§7.2–§7.5 OPEN):
- **§7.2 Waterfall reconciliation** — Hunter renew/replace, ContactOut credit decision, Leadmagic AU mobile replacement. Provider decisions required before any automated run contacts real prospects.
- **§7.3 N≥50 clean cohort run** — prior validation run at scale before P5 count is credible.
- **§7.4 OUTREACH-GATES-AUDIT** — channel cooldown + tier aggregate cap as runtime-enforced gates (GOV-12 mandatory pre-any-live-send). Automation without these gates is a compliance risk.
- **§7.5 First manual-mode outreach** — prove reply / suppression / compliance stack on real inbound before automated sends.

P5 "automated run" is technically achievable (pipeline fires, cards land in DB) without §7.2–7.5. Shipping anything to customers after P5 requires §7.2–7.5 closed.

---

## 6. Dave-Lane Blockers

| # | Blocker | Why it blocks |
|---|---------|---------------|
| D1 | **P4 scope clarification** — ceo_memory says "Stages 1–10 automated." Shipped code = Stage 9–10 only. Is P4 DONE (shipped state) or IN_PROGRESS (ceo_memory state)? Determines whether P5 gate can be evaluated now. | No P5 gate evaluation until scope is ratified. |
| D2 | **Data handoff contract** — in-memory subflows vs Supabase row-per-stage. cohort_runner currently runs all stages sequentially in one process. Prefect DAG needs this contract pinned before any flow architecture is finalised. | Every stage 1–8 flow design depends on this. |
| D3 | **Old flow coexistence policy** — `pool_population_flow.py` and `enrichment_flow.py` may be in use for live outreach. Replace them, run Pipeline F in parallel, or hard-cutover? | If active campaigns depend on old flows, a hard replace breaks them. Determines whether P4 is a cutover or an addition. |
| D4 | **Railway plan verification** — April 3 audit flagged hobby-tier risk for long-running paid-enrichment flows (Stages 6–8). Not confirmed as resolved in ceo_memory. Railway hobby tier may kill workers mid-run. | P5 automated run fails silently without confirmed plan tier. |
| D5 | **API key audit for Stages 6–8** — DataForSEO (Stage 6), Leadmagic (Stage 8 contact waterfall), Bright Data LinkedIn (Stage 8 DM). Must be set in Railway environment variables before automated run. Status not confirmed in this audit. | Flows fail at runtime without verified env vars. |
| D6 | **Provider decisions (F21 §7.2)** — Hunter, ContactOut, Leadmagic AU mobile. Not P4-blocking for the flow build, but required before any automated run reaches real prospects. | Blocks first live send post-P5. |
| D7 | **Stripe** — First paying customer path. Not P4-blocking. | Product-readiness dependency post-P5. |

---

## 7. Effort Estimate to P5-Ready

Scoped by work items, not calendar time.

| Work item | Size | Notes |
|-----------|------|-------|
| D1 + D2 + D3 decisions (Dave-lane) | 0 build items | Must resolve before any flow is written |
| Wrap Stage 1–8 in Prefect @flow/@task (approach a) | Medium–Large | Decorator wiring + data handoff per D2 decision; logic already exists in cohort_runner |
| Stage 1 discovery reconciliation (5.2) | Small | Confirm cohort_runner Stage 1 is production-tested; add pool_population handoff if needed |
| Master E2E flow (5.3) | Medium | Sequence 1–11 with stage_9_10_flow handoff; EVO-003 telemetry |
| Deployment + schedule (5.4) | Small | Follow cis_learning_deployment.py pattern |
| dm_messages verification query (5.5) | Small | Post-run SQL check + GOV-12 gate confirm |
| Railway plan + env var verification (D4 + D5) | Small (devops) | Verify, not build |
| C2_prefect_reaudit (fold into P4) | Small | Verify current zombie count + concurrency enforcement |
| P5 E2E validation run (10 AU domains) | Validation run | Final gate — not a build item |

**Critical path to P5:** D1 scope decision → D2 data handoff decision → Stage 1–8 Prefect wrapping → master E2E flow → Railway verify → P5 run.

---

## 8. Felt-Sufficiency Appendix

Flags raised during independent drafts and their resolutions:

| Flag | Raised by | Resolution |
|------|-----------|-----------|
| Stage 1 "NO" in cohort_runner | Aiden — read line 716 `--domains` bypass comment without reading the else branch | Elliot corrected: else branch lines 728–759 contains full DFS category discovery + ETV + blocklist. Stage 1 IS in cohort_runner. |
| 31-flow count / only cis_learning_deployment.py is ratified | Aiden — via `ls`; did not verify against live Prefect server | Flag stands. `prefect deployment ls` needed to confirm deployed vs defined. Folded into C2_prefect_reaudit recommendation. |
| ceo:prefect_state is 18 days old | Aiden | Flag stands. Zombie count, concurrency enforcement, and Railway plan tier are unverified. C2_prefect_reaudit should close this. |
| How did D2/D2.2 cohort runs discover domains? | Aiden — known unknown; did not grep run scripts | Flag stands (§5.2). Check run logs before assuming Stage 1 else-branch is production-tested. |
| Deployment count (Elliot's version listed fewer flows) | Elliot draft listed 5 flows; Aiden found 31 | Aiden's count from `ls src/orchestration/flows/` is more complete. Elliot's table covered only actively-used flows. Both counts valid in context. |
