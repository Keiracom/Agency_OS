# P1.5 System Audit — 2026-04-21

**Directive:** P1.5-C1-SYSTEM-AUDIT
**Auditor:** Aiden (read-only)
**Worktree:** /home/elliotbot/clawd/Agency_OS-aiden/
**Branch:** aiden/scaffold
**Base commit:** 539cd931 (origin/main HEAD at audit start)
**Scope:** Read-only system-wide audit of codebase state post AGENCY-PROFILE-TRUTH-AUDIT. Report only, no fixes.

---

## 1. Git state confirmation

Current `origin/main` HEAD: `539cd931 docs: add verbatim card bodies + Railway/Stripe/P1 gate status to MANUAL`

Last 20 commits reviewed — all are this session's work (writer/critic architecture, truth audit, MANUAL update, P5 live-fire). No unresolved merge conflicts, clean linear history except the one merge-commit (`cf620f3a` for PR #372).

## 2. Pipeline stage modules

**Standalone stage modules present in `src/pipeline/`:**

| Stage | File | Status |
|-------|------|--------|
| 1 Discovery | `stage_1_discovery.py` | Present |
| 2 GMB Lookup | `stage_2_gmb_lookup.py` | Present |
| 3 DFS Profile | `stage_3_dfs_profile.py` | Present |
| 4 Scoring | `stage_4_scoring.py` | Present |
| 5 DM Waterfall | `stage_5_dm_waterfall.py` | Present |
| 6 Reachability | `stage_6_reachability.py` | Present |
| 7 Haiku | `stage_7_haiku.py` | Present |
| 8 Email | **absent as standalone** — lives inside `src/orchestration/cohort_runner.py::_run_stage8` |
| 9 Vulnerability | `stage_9_vulnerability_enrichment.py` | Present |
| 10 Critic | `stage_10_critic.py` | Present (new this session) |
| 10 Writer | `stage_10_message_generator.py` | Present |
| 11 Card | **absent as standalone** — lives inside `src/orchestration/cohort_runner.py::_run_stage11` |

**Deprecated provider references** — `grep -i "proxycurl\|kaspr\|apollo\|hunterio\|HunterIO" src/` returned **zero matches**. Clean relative to the dead-reference table in `CLAUDE.md`.

**Orphan-module sweep** — see §3 for the flow-level orphan list. At the stage-module level all imports resolve; no dangling references found.

## 3. Prefect flows

- **34 `.py` files** in `src/orchestration/flows/` (excluding `__init__.py`).
- **23 deployment entries** in `prefect.yaml`.
- **Elliot B1 report (companion directive) confirms 19 deployments are actually registered on the Prefect server** — so 4 entries in `prefect.yaml` are stale or never registered.

**16 flows exist in source but are NOT declared in `prefect.yaml`:**

```
batch_controller_flow       cis_learning_flow           daily_digest_flow
daily_pacing_flow           dncr_rewash_flow            domain_pool_maintenance_flow
fire_scheduled_actions_flow infra_provisioning_flow     lead_enrichment_flow
linkedin_health_flow        marketing_automation_flow   post_onboarding_flow
recording_cleanup_flow      rescore_flow                stage_9_10_flow
stale_lead_refresh_flow
```

Some are legitimate internal sub-flows invoked by master flows (`stage_9_10_flow` is called from `pipeline_f_master_flow`). Others look like dead code or work-in-progress flows that never shipped. Requires triage — marked MEDIUM.

**`crm_sync_flow`** — grep in `src/orchestration/flows/` returns zero hits. The only `crm_sync` reference in the tree is a string literal `source: str = "crm_sync"` in `src/services/meeting_service.py:254` — that is a data-column value, not a flow import. Ghost-kill (PR #366) is clean.

**Prefect worker health (from Elliot's B1 companion report):** worker polled 2026-04-21 11:45:48 UTC (minutes before this audit). `pipeline-f-master-flow` READY, last run COMPLETED 11:08 UTC ✓.

## 4. Test baseline

```
$ python3 -m pytest --co -q | tail -5
[...]
2206 tests collected in 14.83s
```

**Reconciliation required:**
- This audit: **2206 tests collected** (via `--co -q`, counts everything importable).
- Manual baseline cited in directive: **1505 passed / 1 failed / 28 skipped** (April 15 snapshot).
- Dave's new-session briefing today reported: **986 passed / 0 failed / 28 skipped**.

Three different numbers, three different methodologies. The 2206 figure is _collection count_ including tests not reached in a run. The 1505 and 986 figures are _run results_ and must have been produced on different branches or with different skip-markers active. I did not run a full `pytest` (scope was read-only collect-count check). Recommend Elliot run a full `pytest --tb=no -q` in his worktree and commit the result to the Manual so all three numbers get one authoritative reconciliation.

## 5. DEFAULT_AGENCY residue

```
$ grep -rn "DEFAULT_AGENCY" src/ --include="*.py"
(no output)
```

**Zero production references.** The test fixture at `tests/fixtures/agency_profile_fixture.py` (`TEST_AGENCY_PROFILE`) is the only remaining home of the pattern. Truth audit is clean at the repo level.

## 6. Env-var / ledger cross-reference

Ledger (`elliot_internal.api_keys_ledger`) contains 42 rows. Code-level `os.environ` / `os.getenv` references in `src/` yielded ~45 distinct env var names.

### 6a. Dead/deprecated ledger entries still referenced in source code

| Var | Ledger status | Still referenced in | Severity |
|-----|---------------|---------------------|----------|
| `HUNTER_API_KEY` | dead_401 | `src/pipeline/email_waterfall.py:563-605` (LIVE L2, ratified), `src/intelligence/contact_waterfall.py:243` (legacy path, not in Prefect chain) | **MEDIUM** (downgraded from HIGH) — see correction note below |
| `ZEROBOUNCE_API_KEY` | deprecated | `src/intelligence/contact_waterfall.py:244,298`; `src/engines/waterfall_verification_worker.py:59,85,715,749,750` | **MEDIUM** — Tier 4 escalation path references a deprecated provider |
| `CONTACTOUT_API_KEY` | locked_403 | referenced in the email-waterfall integration | **MEDIUM** — credit-exhausted provider still wired; will 403 under load |

**Correction note on HUNTER_API_KEY (added 2026-04-21 per P1.5-WATERFALL-ALIGNMENT-AUDIT, Elliot's companion directive).** The original audit wording implied the Hunter wiring should be removed. That was a misframe. Per `CLAUDE.md`:

> EXCEPTION: Hunter email-finder active in Pipeline F v2.1 as L2 email fallback (score >= 70).

Elliot's authoritative audit traced the Prefect call chain (`pipeline_f_master_flow` → `cohort_runner._run_stage8` → `discover_email` → `email_waterfall.py`) and confirmed:

- `src/pipeline/email_waterfall.py:563-605` is the **live** Hunter integration. Layer 2 of the 6-layer waterfall. Gated correctly (GOV-12: `dm_verified=True` + `score >= 70`). Ratified by directive history; D2.2-RUN validation showed Hunter at 5/5 on fresh domains (the only provider that delivered).
- `src/intelligence/contact_waterfall.py:243` is a **legacy** path from pre-v2.1 flows, not reached by the Prefect master flow.
- Key status `dead_401` means the HUNTER_API_KEY **needs renewal** — Dave-lane credential action. Code path is correct and should stay.
- Until renewal: line 572's empty-string check silently skips the Hunter block, L3 (Leadmagic, $0.015/email) picks up the slack.

**Revised recommendation:** renew HUNTER_API_KEY. Do NOT remove the wiring. Severity downgraded HIGH→MEDIUM because the architectural state is correct and only a credential refresh is needed.

**RESOLVED 2026-04-21 12:27 UTC.** Key was never dead — it lived in `~/.config/agency-os/.env` but had never been propagated to Railway. Empty env var on Railway → empty auth header → 401 response → ledger misrecorded as `dead_401`. Elliot pushed the key to Railway `prefect-worker` via GraphQL `variableUpsert`, ledger updated (`status=live`, `storage_locations.railway_prefect_worker=true`, `last_verified=2026-04-21T12:27:11Z`). Verified via `SELECT FROM elliot_internal.api_keys_ledger` after update. Hunter L2 is active on the next pipeline run. Severity further downgraded MEDIUM→INFO (resolved).

### 6b. Ledger entries no longer referenced in source code (candidates for ledger cleanup)

`APOLLO_API_KEY` (deprecated, zero src/ matches), `PROSPEO_API_KEY` (deprecated, zero src/ matches). Delete from ledger or mark retired to keep the ledger honest.

### 6c. Source-code env vars missing from ledger

| Var | Why it matters |
|-----|----------------|
| `DEEPGRAM_API_KEY` | Secret, should be tracked |
| `SPIDER_API_KEY` | In ledger as unknown, referenced in src — status should be re-verified |
| `SUPABASE_KEY` | Ambiguous between `SUPABASE_ANON_KEY` and `SUPABASE_SERVICE_KEY` (both in ledger) — the generic `SUPABASE_KEY` literal in code may mask a bug |
| `CAL_WEBHOOK_SECRET`, `CALENDLY_WEBHOOK_SECRET` | Secrets for webhook verification, not tracked in ledger |

Config-only vars (e.g. `CAL_BOOKING_URL`, `HEYGEN_AVATAR_ID`, `ENRICHMENT_CONCURRENCY`, `DRY_RUN`, `MEMORY_WRITE_CAP`) don't need ledger tracking — they're not secrets.

## 7. Findings summary by severity

### CRITICAL
*(none)* — nothing in the audit blocks Phase 2 Dashboard outright.

### HIGH
1. ~~`HUNTER_API_KEY` dead but still wired into email waterfall.~~ **CORRECTED 2026-04-21 — downgraded to MEDIUM.** See §6a correction note: Hunter wiring at `email_waterfall.py:563-605` is ratified L2 integration, correct and should remain. Only the credential is dead. Fix is `HUNTER_API_KEY` renewal (Dave-lane), not code removal. Companion audit P1.5-WATERFALL-ALIGNMENT-AUDIT (Elliot) provides the authoritative provider-order + verdict: ALIGNED with F2.1 architecture.
2. **16 flows in `src/orchestration/flows/` have no declaration in `prefect.yaml`.** Mixture of legitimate internal sub-flows (e.g. `stage_9_10_flow`) and likely-dead code. Triage list needed; unused ones should be deleted.
3. **Test baseline is three different numbers from three sources.** 2206 collected vs 1505 Manual vs 986 fresh-session. Cannot make a credible "tests are green" claim until one authoritative run reconciles these.

### MEDIUM
4. **`ZEROBOUNCE_API_KEY` (deprecated)** still wired in `contact_waterfall.py` and `waterfall_verification_worker.py` (Tier 4). Dead provider integration.
5. **`CONTACTOUT_API_KEY` locked_403** — credit exhaustion known; src/ path still calls the provider, will return 403 on every call under load.
6. **`APOLLO_API_KEY`, `PROSPEO_API_KEY`** in ledger as deprecated but have zero src/ references. Ledger cleanup candidates (not code issues).
7. **`stage_8` and `stage_11` not standalone modules** — live inside `cohort_runner.py::_run_stage8` / `_run_stage11`. Inconsistent with stages 1-7/9/10 which each have their own module. Hurts discoverability but does not affect runtime correctness.
8. **8 Prefect deployments PAUSED** (per Elliot B1). Some may be intentional off-hours, some may be silently abandoned. Review needed.

### LOW
9. **`agent_comms` table: 20 unread, no polling** — Elliot's B2 directive is fixing this.
10. **`DEEPGRAM_API_KEY`, `CAL_WEBHOOK_SECRET`, `CALENDLY_WEBHOOK_SECRET`** referenced in src/ but not tracked in api_keys_ledger. Ledger completeness gap.
11. **`SUPABASE_KEY` literal** in code — ambiguous between anon and service keys. May be a bug or may be deliberate; needs a read.

### INFO (positive findings)
12. `DEFAULT_AGENCY` fully eliminated from production — truth audit clean.
13. Zero references in src/ to Proxycurl, Kaspr, Apollo, HunterIO (legacy names) — dead-reference table in `CLAUDE.md` is honoured.
14. `_KEIRACOM_PROFILE` contains no `case_study` field — pre-revenue discipline holds structurally.
15. `pipeline_f_master_flow` is READY in Prefect and last-ran successfully (flow 1176392a, 11:08 UTC).
16. `crm_sync_flow` ghost-kill (PR #366) is clean — no deployment refs, no import refs, only a benign string literal remains.
17. Critic new file `stage_10_critic.py` includes both `no_hallucination` and `social_proof_sourced` HARD-FAIL gates — pre-revenue rule is enforced in code, not just docs.

## 8. Explicit Phase 2 Dashboard blockers

**None of the findings above block Phase 2 Dashboard work.** The dashboard reads from Supabase tables (`business_universe`, `dm_messages`, `ceo_memory`, etc.) that are independent of the Hunter/Zerobounce/ContactOut provider paths. Dashboard work can proceed while the deprecated-provider cleanup (HIGH #1, MEDIUM #4-5) happens in parallel.

**Recommended ordering before Phase 2 starts:**
1. Elliot B2 PR (`agent_comms` polling) — unblocks async CEO→agent loop, useful for dashboard directive dispatch.
2. Reconcile test baseline number (HIGH #3) — dashboard work needs a known-good test surface.
3. Triage the 16 orphan flows (HIGH #2) — at minimum remove any that reference deprecated providers or dead endpoints.

Everything else is cleanup-class debt, not a gate.

---

**Auditor's meta-note:** this audit is read-only. No code was modified. Findings above list locations and symptoms; no fixes were applied. Separate directives should own each remediation.
