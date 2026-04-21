# P4 Build Spec — Pipeline F Master Flow

## 1. Overview

P4 wraps `cohort_runner.py`'s existing 11-stage logic in Prefect `@flow` and `@task` decorators, making Pipeline F a tracked, deployable, auditable flow without rewriting any stage logic. Stages 1-8 and 11 run inside the master flow as `@task`-decorated wrappers over the existing `_run_stageN` functions; Stages 9-10 are handled by the already-ratified `stage_9_10_pipeline` flow (`src/orchestration/flows/stage_9_10_flow.py`, PR #308), which is called as a sub-flow from the master. The master flow is the P5 gate vehicle: until it produces 10 verified `dm_messages` drafts from 10 fresh AU domains with zero manual intervention, the pipeline does not ship to production cadence.

---

## 2. Master Flow Shape

**Entry point:** A new function `pipeline_f_master_flow` in `src/orchestration/flows/pipeline_f_master_flow.py`. The existing `run_cohort` function in `src/orchestration/cohort_runner.py` is **not** decorated — it stays CLI-callable as-is. `pipeline_f_master_flow` calls `run_cohort` for the Stage 1-8 work, then hands off to `stage_9_10_pipeline`.

**Stage sequencing:**

```
pipeline_f_master_flow(@flow)
  │
  ├─ task: stage_1_discover       (wraps Stage 1 logic inside run_cohort)
  ├─ task: stage_2_verify         (_run_stage2, DFS SERP × 5)
  ├─ task: stage_3_identify       (_run_stage3, Gemini DM extraction)
  ├─ task: stage_4_signal         (_run_stage4, DFS signal bundle)
  ├─ task: stage_5_score          (_run_stage5, viability scoring)
  ├─ task: stage_6_enrich         (_run_stage6, DFS historical rank)
  ├─ task: stage_7_analyse        (_run_stage7, Gemini VR + outreach)
  ├─ task: stage_8_contact        (_run_stage8, email + mobile waterfall)
  │
  ├─ task: persist_stage8_to_db   (DATA HANDOFF — writes BU + BDM rows, returns bdm_ids)
  │
  ├─ sub-flow: stage_9_10_pipeline(bdm_ids=bdm_ids, ...)   [stage_9_10_flow.py]
  │     ├─ task: select_bdms
  │     ├─ task: run_stage_9      (VR + ContactOut)
  │     ├─ task: verify_stage_9
  │     ├─ task: run_stage_10     (4-channel message generation)
  │     └─ task: verify_stage_10
  │
  ├─ task: stage_11_card          (_run_stage11, lead card assembly)
  │
  └─ task: dm_messages_gate       (post-run SQL count + email_scoring_gate sample check)
```

**Within-stage parallelism:** unchanged. `run_parallel()` from `src/intelligence/parallel.py` runs domain batches in parallel within each stage. The Prefect `@task` wrapper fires once per stage (not once per domain) — Prefect tracks the stage, not individual domain calls. Per-domain telemetry is a post-P5 refactor (D2 ratified decision).

**Data handoff note:** Stages 1-8 operate on in-memory `domain_data` dicts. `stage_9_10_pipeline` reads from the `business_decision_makers` table via asyncpg. The `persist_stage8_to_db` task bridges this gap (see Section 4).

---

## 3. Decorator Placement

| Function | File | Current Signature | Decorator | Notes |
|----------|------|-------------------|-----------|-------|
| `pipeline_f_master_flow` | `src/orchestration/flows/pipeline_f_master_flow.py` | NEW | `@flow` | Master entry point. `on_completion=[on_completion_hook]`, `on_failure=[on_failure_hook]` |
| `run_cohort` | `src/orchestration/cohort_runner.py` line 670 | `async def run_cohort(categories, domains_per_category, output_dir, domains, force_replay, dry_run) -> dict` | **None** | CLI entrypoint — must stay undecorated. Master flow calls it as a plain coroutine. |
| `stage_1_discover` | `pipeline_f_master_flow.py` | NEW thin wrapper | `@task` | Extracts `cohort_runner.py` lines 728-759 (DFS category discovery + ETV + blocklist) into a standalone callable. Does NOT call `run_cohort` — `run_cohort` has no stage-disable flag, and calling it would run all 11 stages. The extraction is a ~20-line function that calls `dfs.domain_metrics_by_categories()` with category codes + ETV windows + blocklist filter, returning `list[dict]` of domain items. |
| `stage_2_verify` | `pipeline_f_master_flow.py` | NEW thin wrapper | `@task` | Calls `_run_stage2` via `run_parallel`. Input: `pipeline: list[dict]`, `dfs: DFSLabsClient`. |
| `stage_3_identify` | `pipeline_f_master_flow.py` | NEW thin wrapper | `@task` | Calls `_run_stage3` via `run_parallel`. |
| `stage_4_signal` | `pipeline_f_master_flow.py` | NEW thin wrapper | `@task` | Calls `_run_stage4` via `run_parallel`. |
| `stage_5_score` | `pipeline_f_master_flow.py` | NEW thin wrapper | `@task` | Calls `_run_stage5` via `run_parallel`. No client. |
| `stage_6_enrich` | `pipeline_f_master_flow.py` | NEW thin wrapper | `@task` | Calls `_run_stage6` via `run_parallel`. |
| `stage_7_analyse` | `pipeline_f_master_flow.py` | NEW thin wrapper | `@task` | Calls `_run_stage7` via `run_parallel`. |
| `stage_8_contact` | `pipeline_f_master_flow.py` | NEW thin wrapper | `@task` | Calls `_run_stage8` via `run_parallel`. |
| `persist_stage8_to_db` | `pipeline_f_master_flow.py` | NEW | `@task` | Writes BU + BDM rows; returns `bdm_ids`. See Section 4. |
| `stage_11_card` | `pipeline_f_master_flow.py` | NEW thin wrapper | `@task` | Calls `_run_stage11` via `run_parallel`. Runs after `stage_9_10_pipeline` returns. |
| `dm_messages_gate` | `pipeline_f_master_flow.py` | NEW | `@task` | Post-run SQL + `email_scoring_gate.score_and_suggest()` sample. See Section 7. |
| `select_bdms` | `stage_9_10_flow.py` line 80 | `async def select_bdms(pool, bdm_ids, batch_size) -> list[str]` | `@task` (existing) | Do not modify. |
| `run_stage_9` | `stage_9_10_flow.py` line 94 | `async def run_stage_9(pool, bdm_ids) -> dict` | `@task` (existing) | Do not modify. |
| `verify_stage_9` | `stage_9_10_flow.py` line 101 | `async def verify_stage_9(pool, bdm_ids) -> int` | `@task` (existing) | Do not modify. |
| `run_stage_10` | `stage_9_10_flow.py` line 120 | `async def run_stage_10(pool, bdm_ids, vertical_slug, agency_profile) -> dict` | `@task` (existing) | Do not modify. |
| `verify_stage_10` | `stage_9_10_flow.py` line 135 | `async def verify_stage_10(pool, bdm_ids) -> dict` | `@task` (existing) | Do not modify. |
| `stage_9_10_pipeline` | `stage_9_10_flow.py` line 150 | `async def stage_9_10_pipeline(bdm_ids, batch_size, budget_cap_usd, vertical_slug, agency_profile, dry_run) -> dict` | `@flow` (existing) | Called as sub-flow from master. |

**Prefect task tracking note:** `@task`-decorated functions called inside a `@flow` are automatically tracked by Prefect — their start time, end time, and state appear in the Prefect UI. No additional instrumentation needed to get per-stage visibility. The wrappers are thin; all business logic stays in `cohort_runner.py`.

---

## 4. Data Handoff: In-Memory to DB

**The gap:** `run_cohort` (lines 670-946, `cohort_runner.py`) maintains domain state as a `list[dict]` in memory. Each dict has keys like `domain`, `stage3` (DM data), `stage8_contacts` (email/mobile), `stage7` (VR draft), etc. `stage_9_10_pipeline` reads exclusively from the `business_decision_makers` table via asyncpg — it has no awareness of the in-memory pipeline.

**Handoff contract — what `persist_stage8_to_db` must write:**

After Stage 8 completes and before `stage_9_10_pipeline` is called, `persist_stage8_to_db` iterates the active (non-dropped) pipeline domains and upserts:

| Table | Columns written | Source in domain_data |
|-------|-----------------|-----------------------|
| `business_universe` | `domain`, `pipeline_stage = 8`, `propensity_score`, `vulnerability_report` (if stage7 produced it), `organic_etv`, `category` | `domain`, `stage5["viability_score"]`, `stage7["vr_draft"]` |
| `business_decision_makers` | `name`, `title`, `linkedin_url`, `email`, `mobile`, `is_current = TRUE`, `business_universe_id` | `stage3["dm_name"]`, `stage3["dm_title"]`, `stage3["linkedin_url"]`, `stage8_contacts["email"]`, `stage8_contacts["mobile"]` |

**Return value:** `list[str]` of UUIDs — the `business_decision_makers.id` values just written. These are passed directly as `bdm_ids` to `stage_9_10_pipeline`, bypassing its auto-select SQL (`_DEDUP_SQL`).

**Why explicit IDs, not auto-select:** Passing explicit BDM IDs ensures Stage 9-10 processes exactly the domains that passed Stages 1-8 in this run. Auto-select (`_DEDUP_SQL`) would pull from the full `pipeline_stage = 9` pool, mixing prior-run residuals.

**After stage_9_10_pipeline returns:** `stage_9_10_pipeline` updates `business_universe.pipeline_stage` to 10 for processed BDMs and writes `dm_messages` rows. `stage_11_card` then reads the still-live in-memory pipeline (which was not flushed) to assemble lead cards. The in-memory dict and the DB row coexist for Stage 11 — no re-fetch required.

---

## 5. Deployment Config

File: `src/orchestration/deployments/pipeline_f_deployment.py`

Following `cis_learning_deployment.py` pattern (`src/orchestration/deployments/cis_learning_deployment.py`).

**Manual deployment (P5 validation):**

```python
pipeline_f_manual = Deployment.build_from_flow(
    flow=pipeline_f_master_flow,
    name="pipeline-f-manual",
    version="1.0.0",
    tags=["p4", "pipeline-f", "master-flow", "manual"],
    description="P4 master flow — manual trigger for P5 validation runs.",
    schedule=None,
    parameters={
        "categories": ["dental", "plumbing", "legal", "accounting", "fitness"],
        "domains_per_category": 2,
        "dry_run": False,
        "budget_cap_aud": 15.0,
    },
    work_queue_name="default",
)
```

**Production deployment (cron placeholder):**

```python
pipeline_f_production = Deployment.build_from_flow(
    flow=pipeline_f_master_flow,
    name="pipeline-f-production",
    version="1.0.0",
    tags=["p4", "pipeline-f", "master-flow", "production"],
    description="P4 master flow — production cadence. Schedule TBD post-P5.",
    schedule=CronSchedule(cron="0 2 * * 1", timezone="Australia/Sydney"),  # PLACEHOLDER
    parameters={
        "categories": ["dental", "plumbing", "legal", "accounting", "fitness"],
        "domains_per_category": 4,
        "dry_run": False,
        "budget_cap_aud": 50.0,
    },
    work_queue_name="default",
)
```

**Parameters exposed to Prefect UI:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `categories` | `list[str]` | `["dental","plumbing","legal","accounting","fitness"]` | Stage 1 discovery categories |
| `domains_per_category` | `int` | `4` | Domains to discover per category |
| `dry_run` | `bool` | `False` | If True: wires @flow/@task, zero API spend |
| `budget_cap_aud` | `float` | `15.0` | Hard spend ceiling in AUD |

`budget_cap_aud` is converted to USD inside the master flow: `budget_cap_usd = budget_cap_aud / 1.55`.

---

## 6. Telemetry

**Prefect run logs:** Each `@task` wrapper logs on entry and exit:
- Stage name (e.g. `"Stage 2 VERIFY"`)
- Domain count going in (active, non-dropped)
- Domain count surviving (non-dropped after stage)
- Incremental cost USD for the stage
- Wall time seconds

These are standard `flow_logger.info()` calls using `_logger()` from `stage_9_10_flow.py` (which falls back to `logging.getLogger` outside a flow context). Same pattern works in all wrappers.

**Telegram progress:** `_tg()` in `cohort_runner.py` already fires after each stage (lines 785, 802, 819, 836, etc.). These calls live inside `run_cohort` and fire regardless of Prefect wrapping — keep them. No duplication needed in the `@task` wrappers.

**EVO-003 hooks:**

```python
from src.prefect_utils.completion_hook import on_completion_hook
from src.prefect_utils.hooks import on_failure_hook

@flow(
    name="pipeline-f-master-flow",
    on_completion=[on_completion_hook],
    on_failure=[on_failure_hook],
    timeout_seconds=3600,
)
async def pipeline_f_master_flow(...) -> dict:
```

`on_completion_hook` (`src/prefect_utils/completion_hook.py` line 6) writes to `evo_flow_callbacks` via `write_flow_callback`. The summary dict returned by the master flow is captured as `result_summary` in that row.

`on_failure_hook` (`src/prefect_utils/hooks.py` line 7) sends a Telegram alert and writes a failed callback row.

**Summary dict shape returned by master flow** (captured by `on_completion_hook`):

```python
{
    "run_ts": str,           # ISO timestamp
    "domains_discovered": int,
    "domains_carded": int,
    "bdms_processed": int,
    "dm_messages_written": int,
    "cost_usd": float,
    "cost_aud": float,
    "wall_clock_s": float,
    "stage_9_10_result": dict,   # passthrough from stage_9_10_pipeline
    "dm_gate_passed": bool,
    "dry_run": bool,
}
```

---

## 7. dm_messages Verification Gate

`dm_messages_gate` is a `@task` at the end of `pipeline_f_master_flow`, after `stage_11_card` completes. It must pass before the flow returns success. If it fails, the flow raises `RuntimeError` (triggering `on_failure_hook`).

**Step 1 — count gate (SQL):**

```sql
SELECT COUNT(*) FROM dm_messages
WHERE status = 'draft'
  AND created_at > :run_start_ts
```

Expected: `COUNT >= bdms_processed`. If `COUNT < bdms_processed`, gate fails with log of the shortfall.

**Step 2 — content gate (sampling):**

Pull 3 random `dm_messages` rows where `channel = 'email'` and `created_at > run_start_ts`. For each, call:

```python
from src.pipeline.email_scoring_gate import score_and_suggest

result = score_and_suggest(
    subject=row["subject"],
    body=row["body"],
    recipient_company=row["recipient_company"],
)
# result["score"] must be >= PASS_THRESHOLD (70)
# result["flags"] logged regardless
```

`score_and_suggest` is in `src/pipeline/email_scoring_gate.py`. `PASS_THRESHOLD = 70` is defined at line 19. If any of the 3 samples scores below 70, gate logs the flags and raises `RuntimeError("dm_messages content gate failed")`.

**Gate is runtime enforcement (GOV-12 compliant):** the raise path is an executable conditional, not a comment.

---

## 8. Railway Env Var Checklist

| Var | Service | Required For | Status |
|-----|---------|-------------|--------|
| `DATAFORSEO_LOGIN` | DFSLabsClient | Stages 1, 2, 4, 6 | CONFIRMED (used in cohort_runner line 688) |
| `DATAFORSEO_PASSWORD` | DFSLabsClient | Stages 1, 2, 4, 6 | CONFIRMED (used in cohort_runner line 689) |
| `GEMINI_API_KEY` | GeminiClient | Stages 3, 7 | CONFIRMED (used in cohort_runner line 691) |
| `BRIGHTDATA_API_KEY` | BrightDataClient | Stages 8, 9 (social) | CONFIRMED (used in cohort_runner line 692) |
| `LEADMAGIC_API_KEY` | LeadmagicClient | Stage 8 (mobile waterfall) | CONFIRMED (LeadmagicClient reads from settings) |
| `TELEGRAM_TOKEN` | _tg() progress alerts | All stages | CONFIRMED (cohort_runner uses it) |
| `DATABASE_URL` | asyncpg pool | `persist_stage8_to_db`, `stage_9_10_pipeline` | VERIFY — stage_9_10_flow.py line 177 reads `os.environ["DATABASE_URL"]`. Must be `postgresql://` not `postgresql+asyncpg://` (line 177 does the strip). Confirm Railway injects this. |
| `SUPABASE_URL` | Supabase async client | `_persist_drop_reason`, Stage 8 lead upserts | VERIFY — cohort_runner uses `get_async_supabase_service_client`. Confirm env var name matches Railway secret. |
| `SUPABASE_SERVICE_KEY` | Supabase async client | `_persist_drop_reason`, Stage 8 lead upserts | VERIFY — same as above. |
| `ANTHROPIC_API_KEY` | Stage 10 (AsyncAnthropic) | Stage 10 message generation | VERIFY — `stage_9_10_flow.py` line 129: `_anthropic.AsyncAnthropic()` reads `ANTHROPIC_API_KEY` from env. |
| `CONTACTOUT_API_KEY` | ContactOut enricher | Stage 9 VR enrichment | VERIFY — `Stage9VulnerabilityEnrichment` pulls ContactOut. Confirm key name in Railway. |
| `PREFECT_API_URL` | Prefect agent | Deployment registration | VERIFY — Railway service running the worker must have this set. |
| `PREFECT_API_KEY` | Prefect agent | Deployment registration | VERIFY — same as above. |

**Explicitly excluded:** `HUNTER_API_KEY` — Hunter is L2 of email waterfall but currently 401-dead (FM-PRE-FLIGHT 2026-04-20). The waterfall skips L2 gracefully when `dm_verified=False` or key is absent (email_waterfall.py:565 runtime gate). Re-add to this table if Hunter is renewed (F21 §7.2 holdover).

**Dave-lane items from this table:** `DATABASE_URL`, `ANTHROPIC_API_KEY`, `CONTACTOUT_API_KEY`, `PREFECT_API_URL`, `PREFECT_API_KEY` — all need Railway confirmation before P5 run (see Section 12).

---

## 9. Test Plan

**Step 1 — Dry-run, 1 domain (zero spend):**

```bash
prefect deployment run 'pipeline-f-master-flow/pipeline-f-manual' \
  -p domains=["testdomain.com.au"] \
  -p dry_run=True
```

Pass criteria:
- Prefect UI shows flow run with all `@task` nodes firing and completing
- `on_completion_hook` fires → row appears in `evo_flow_callbacks`
- No API calls made (DFS, Gemini, BD, Leadmagic, ContactOut all return empty)
- Zero spend

Rollback: deployment already stopped at dry_run; old flows unaffected.

**Step 2 — Live, 1 domain:**

```bash
prefect deployment run 'pipeline-f-master-flow/pipeline-f-manual' \
  -p domains=["targetdomain.com.au"] \
  -p dry_run=False \
  -p budget_cap_aud=5.0
```

Pass criteria:
- Stage 11 card produced (`cards.json` has 1 entry) OR drop reason logged to BU
- At least 1 `dm_messages` row with `status='draft'` for this domain's BDM
- `dm_messages_gate` passes (count >= 1, sample score >= 70)
- `evo_flow_callbacks` row shows `status='completed'` with correct `result_summary`

Rollback: kill deployment, investigate. Old `stage_9_10_pipeline` deployment continues serving.

**Step 3 — Live, 5 domains:**

```bash
prefect deployment run 'pipeline-f-master-flow/pipeline-f-manual' \
  -p categories=["dental","plumbing"] \
  -p domains_per_category=3 \
  -p dry_run=False \
  -p budget_cap_aud=10.0
```

Pass criteria:
- Budget gate fires correctly if spend approaches cap
- Per-stage task timing visible in Prefect UI
- `_tg_progress` messages arriving in Telegram after each stage
- Cost per card within $0.50 AUD of P4 economics estimate

Rollback: same as Step 2.

**Step 4 — P5 gate run, 10 fresh AU domains:**

```bash
prefect deployment run 'pipeline-f-master-flow/pipeline-f-manual' \
  -p categories=["dental","plumbing","legal","accounting","fitness"] \
  -p domains_per_category=2 \
  -p dry_run=False \
  -p budget_cap_aud=25.0
```

Pass criteria (all must be true for P5 to pass):
- Zero manual intervention during the run
- `dm_messages` gate passes: `COUNT(*) >= 5` (assuming ~50% funnel yield), all sampled emails score >= 70
- `on_completion_hook` fires with full summary dict
- Telegram completion alert received
- No `on_failure_hook` fires

P5 failure = halt new deployment, revert to old flows, investigate.

---

## 10. Rollback Plan

P4 is deployed in **PARALLEL** posture (ratified design decision D3). The existing `stage_9_10_pipeline` deployment and all API route handlers remain live throughout P4 and P5.

**If master flow fails at any step:**
1. Stop the `pipeline-f-master-flow` Prefect deployment (pause via Prefect UI or `prefect deployment pause`)
2. Old flows (`stage_9_10_pipeline` and any `cohort_runner` CLI invocations) continue serving
3. `dm_messages_gate` prevents bad data reaching outreach — if gate fails, `on_failure_hook` fires Telegram alert and writes a failed `evo_flow_callbacks` row; no `dm_messages` rows with `status='ready'` are created from this run
4. Investigate via Prefect run logs and `evo_flow_callbacks` table
5. No DB migrations are required for P4, so no DB rollback needed
6. **Orphan-row note:** `persist_stage8_to_db` writes BU + BDM rows before subsequent stages can fail. On flow failure, those rows persist in the database. At P5 scale (10 domains) this is trivial — one cleanup query (`DELETE FROM business_decision_makers WHERE run_id = '<failed_run>'`). At production scale, add a `cleanup_failed_run` task that fires in the `on_failure_hook` path. Tracked as post-P5 cleanup item, not ship-blocking.

**Nothing to cut over:** the master flow is additive. P5 validation determines whether the production cron deployment replaces manual CLI runs. Until P5 passes, the production cron schedule is `None` (manual deployment only).

---

## 11. Scope Exclusions

| Excluded | Rationale | When |
|----------|-----------|------|
| Row-per-stage Supabase telemetry | D2 ratified: post-P5 refactor. In-memory wrap is sufficient for P5 validation. | Post-P5 |
| Old flow migration / cutover | D3: PARALLEL posture. Migration only after new flow validates at P5. | Post-P5 |
| Provider decisions (Hunter / ContactOut alternatives) | Separate capital decision, separate directive. | TBD |
| Outreach gates audit | `dm_messages` gate covers the email quality surface; full outreach gate audit is a separate directive. | TBD |
| Per-domain `@task` wrapping | D2 ratified: one `@task` per stage, not per domain. Per-domain Prefect tracking is post-P5. | Post-P5 |
| Frontend lead pool display changes | No UI changes in P4. | TBD |

---

## 12. Dave-Lane Items

**Before P5 run — Dave must confirm:**

1. **Railway env vars (VERIFY items from Section 8):**
   - `DATABASE_URL` — is it set in the Railway service that will run the Prefect worker? Must be PostgreSQL direct URL (not SQLAlchemy `+asyncpg` variant — `stage_9_10_flow.py` strips the prefix at line 177, but the raw var must exist).
   - `ANTHROPIC_API_KEY` — required for Stage 10 (`AsyncAnthropic()` at `stage_9_10_flow.py` line 129).
   - `CONTACTOUT_API_KEY` — required for Stage 9 ContactOut enrichment in `Stage9VulnerabilityEnrichment`. Confirm key name matches what Railway has.
   - `PREFECT_API_URL` + `PREFECT_API_KEY` — required for the Railway worker to register and poll the Prefect work queue.

2. **Railway plan capacity:** The master flow runs DFS (concurrent HTTP), Gemini (concurrent LLM), Bright Data (webhook-style scrapes), and asyncpg (DB pool) across potentially 10+ domains. Confirm the Railway service plan can sustain concurrent outbound connections without hitting memory or CPU limits during a 10-domain run.

3. **Budget ceiling for P5:** Section 9 Step 4 sets `budget_cap_aud=25.0`. Confirm this is acceptable for the P5 gate run. At $0.50 AUD/domain fully loaded, 10 domains = ~$5 AUD — the cap is intentionally 5x for safety. Dave can tighten.

4. **Telegram group notification channel:** `_tg()` in `cohort_runner.py` and `on_failure_hook` both send Telegram messages. Confirm they are both pointing to the correct group (chat_id `-1003926592540`) and not to a personal DM.
