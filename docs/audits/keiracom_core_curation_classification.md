# keiracom-core Import-Closure Curation — Classification for HoO Confirm

**Author:** orion · **Date:** 2026-06-04 · **Branch:** `orion/keiracom-core-curation`
**Status:** AWAITING Head-of-Ops confirm — NO removal applied. Atlas re-validates (gate 2) after confirm.
**Tool:** `scripts/repo_split/import_closure.py` · **Manifest:** `scripts/repo_split/closure_manifest.json`

## Decision needed (1 binary + 1 list)
keiracom-core = **FLEET + V1.0 PRODUCT** (per `ceo:agency_os_keiracom_separation_v1` + `ceo:decision:repo_split_light_keiracom_core_2026-06-04`); archive = dead BDR lead-gen only.
1. **Confirm the DORMANT-FLEET-RISK set is KEPT** (see §3) — the systemd-seeded dep-graph cannot see fleet code invoked via Claude Code hooks / inline governance, so it wrongly lands them in ARCHIVE. Recommend KEEP per §4.8 F/P.
2. **Confirm the dead-BDR ARCHIVE set** (see §2).

## Method (per `ceo:rule:repo_split_classification_and_guarantees`)
PRIMARY = deterministic AST dependency graph from KeiraCom's live entrypoints (56 systemd ExecStart targets incl base+drop-in vault-envwrap forms) **+ V1.0 product subsystem seeds** (MAL `src/memory`, `keiracom_system/{mcp,memory,tenant,metering,cache,chat,atomization}`, BYOK/Paddle) — product ships but is dormant (not systemd-wired). SECONDARY = carveout-doc §4.8 dir labels as CROSS-CHECK only (labels go stale; dep-graph wins). Result: **src/ 623 → KEEP 379 / ARCHIVE 244.** All 4 known live-edges land in KEEP.

## §1 PRODUCT-KEEP (379) — by subdir, with §4.8 citation
- `keiracom_system` 89 (FLEET+PRODUCT core: chain/work_loop/vault/temporal/backup=fleet; mcp/memory/tenant/metering/cache/chat/atomization=PRODUCT per MAL+SaaS)
- `services` 43 (KEEP = live-edge sdk_usage_service + deps; §4.8 A label is coarse — dep-graph keeps only the live ones)
- `agents` 28 (F), `models` 27 (SPLIT, kept = fleet/product-reached), `dispatcher` 17 (P, MCP dispatcher), `retrieval` 15 (live-edge ← dispatcher.main, overrides §4.8 A), `integrations` 18 (kept = live-reached), `memory` 10 (P — MAL), `pipeline` 10 (kept = live-reached helpers), `intelligence` 6 (gemini_client live-edge + deps), `api` 24 (linear/paddle/customer_api_keys + deps), `evo` 8, `detectors` 8, others.
- **4 live-edge sanity-asserts all KEEP:** retrieval←dispatcher.main, intelligence/gemini_client, services/sdk_usage_service, api/webhooks/linear.

## §2 ARCHIVE — dead-BDR (recommend ARCHIVE; see /tmp/bdr_archive.txt for full list)
Matches §4.8 'A' (discovery/enrichment/outreach/scoring) + the BDR Prefect flows mislabeled F in `orchestration`:
- `pipeline` 39 (Siege Waterfall T0-T5 — §4.8 A), `outreach` 17 (Salesforge/Unipile/Telnyx — A), `integrations` 15 (dead vendors — A), `intelligence` 14 (CIS/ALS scoring — A), `services` 14 (campaign/lead services — A), `engines` 6 (A), `voice` 4 (A), `scraper`/`data` (A), `api` 17 (dead BDR routes — A).
- `orchestration` BDR portion: flows (bu_closed_loop, daily_warming/pacing, free_enrichment, linkedin_health, marketing_automation, dncr_rewash, recording_cleanup, rescore, monthly_*) + tasks (enrichment/outreach/reply/scoring/voice) + deployments + cohort_runner. (§4.8 labeled `orchestration=F` but these are BDR cohort flows — dep-graph correctly archives; **confirm**.)
- `agents/campaign_evolution/*` (BDR campaign agents).

## §3 DORMANT-FLEET-RISK — recommend KEEP, NOT archive (CONFIRM) — /tmp/fleet_risk.txt
These are §4.8 **F/P** (fleet/product) but the dep-graph archived them because they are invoked via **Claude Code hooks / inline governance / bridges — NOT systemd entrypoints**, so the systemd-seeded closure is structurally blind to them. Archiving them would break fleet governance/session/relay behaviour (not boot, but features):
- `governance/*` (gatekeeper, router, coordinator, contracts/*, restate_service, claim_injection, freeze, loader, rules_client, tg_alert, discovery_validation) — fleet governance enforcement (§4.8 F).
- `session_store/userpromptsubmit_handler.py`, `session_resumption/*` — Claude Code session hooks (§4.8 F).
- `bot_common/{concur_gate,session_end_gate,verify_gate,state_store}.py` — fleet bot gates (§4.8 F).
- `relay/{spawn_composer,relay_consumer,redis_relay,envelope_schema,paused_tasks}.py` — inter-agent relay (§4.8 F).
- `skill_gen/*`, `cognee/*`, `dispatcher/{heartbeat_*,container_*,ratified_hash}.py`, `slack_bot/direct_post.py` (§4.8 F/P).

**RECOMMENDATION:** KEEP all of §3 (wholesale per §4.8 F/P). To make the dep-graph *prove* it, add their non-systemd entrypoints as seeds (Claude Code hook configs in `.claude/hooks`, governance hook wiring). Until then, §4.8 F/P + this flag is the basis to KEEP them — do not archive on the systemd-only dep-graph alone.

## §4 NEG-TEST status
NOT YET RUN (no removal applied — holding for confirm). On confirm: apply removal of the confirmed ARCHIVE set on this branch, then neg-test (every kept .py compiles; each live entrypoint imports against curated tree; grep curated tree = 0 refs to removed). Hand validated branch to Atlas (gate 2).

## §5 Findings
- Dangling systemd entrypoints (units reference absent files): `scripts/coo_bot_service.py`, `src/telegram_bot/{chat_bot,enforcer_bot}.py`.
- Closure bug fixed pre-handoff: ancestor `__init__.py` imports were not followed (would under-keep package submodules → boot break); fix raised KEEP 118→187 (fleet-only) before product seeds.

---

## §6 EXECUTED + VALIDATED (HoO confirmed 2026-06-04 — keep-42 / archive-202)
**Closure (complete trigger set):** 56 systemd + 5 hooks + 68 product + 36 HoO-confirmed-keep = 165 entrypoint seeds. **src/ KEEP 422 / ARCHIVE 201.** All 4 live-edges + all 42 fleet-risk in KEEP.
**Removed on branch `orion/keiracom-core-curation` (Agency_OS untouched; reversible):**
- 201 dead-BDR `src/` files (pipeline/outreach/integrations/intelligence-CIS/services-BDR/engines/voice/api-BDR + BDR Prefect flows).
- 10 dead top-level dirs (agency-os-html/-prototype, builds, campaigns, canvas, competitive, frontend, landing-page-analysis, maya-concepts, research).
- 30 dead-BDR `scripts/` (BDR test/run/readiness/ingest/voice — provably dead: import only removed BDR modules, none are live entrypoints). Full list in `closure_manifest.json:dead_scripts`.

**NEG-TEST over the COMPLETE entrypoint set (HoO standard, not services-only) — PASS, exit 0:**
```
(a) COMPILE: 422 kept src/*.py compiled, 0 failures
(b) RESOLVE: 165 entrypoints, walked 266 files, 0 imports pointing at a MISSING (removed) module
(c) ZERO-REF: removed modules referenced in curated tree = 0
NEG-TEST PASS (compile+resolve+zero-ref over 165 entrypoints, 422 kept, 201 removed)
```
Reproduce: `python3 scripts/repo_split/neg_test.py`. Hand-off for Atlas gate-2 (independent re-run over the same set). Dangling units (coo_bot_service.py, telegram_bot/*) = separate cleanup, not closure.

---

## §7 GATE-2 C3 FIX — dead-BDR bleed eliminated (2026-06-04)
Atlas gate-2 C3 (founder-eyeball / fresh-clone zero-dead-BDR) caught ~121 dead-BDR
files still KEPT after §6 — neg-test passed (tree was *consistent*) but a kept-but-dead
subgraph slipped through (C3 checks *completeness*, neg-test only *consistency*).

**Root cause (two layers):**
1. **Aggregator `__init__` re-export bleed.** `src/api/routes/__init__.py`, `src/services/`,
   `src/models/`, `src/integrations/` `__init__`s imported *all* submodules, so one
   reached product/fleet submodule dragged the whole dead-BDR package into KEEP. FIX:
   slimmed each aggregator `__init__` to only genuinely-used submodules. Result:
   `orchestration`/`pipeline`/`engines` → 0 KEEP; dead BDR `src/api` routes archived
   (live `webhooks/linear` + product `customer_api_keys`/`paddle` retained).
2. **`TYPE_CHECKING` model-relationship re-bleed.** The `Client` tenant model + `SDKUsageLog`
   carried stale BDR SQLAlchemy relationships (campaigns, leads, linkedin_*, pool_leads,
   resources, personas, campaign_suggestions, digest_logs, lead) — `TYPE_CHECKING`-only
   imports + `relationship("…")` string forward-refs. These are NOT runtime deps of the
   SaaS tenant (the product does not own lead-gen/outreach entities). FIX: decoupled —
   removed the 9 BDR relationships from `client.py` + the `lead` relationship from
   `sdk_usage_log.py` + their type-imports. `lead_id`/`campaign_id` remain as plain FK
   columns (string table-refs) for the product migration phase.

**Model classification (all 11 archived = BDR; only sdk_usage_log = PRODUCT):**
campaign, campaign_suggestion, client_persona (sender identities/outreach), digest_log
(daily campaign digest), lead, lead_pool, lead_social_post, linkedin_{connection,
credential,seat}, resource_pool (email distribution). KEPT models: base, client,
membership, user, sdk_usage_log (SDK metering — product).

**New neg-test check (d) MAPPER** added — imports every kept ORM model + `configure_mappers()`.
A relationship referencing an archived class by string forward-ref compiles + imports fine
but fails at mapper configuration; (a)/(b)/(c) are blind to it. Check (d) caught
`SDKUsageLog.lead -> 'Lead'` after the type-import was removed — proving the gap is real.

**FINAL state — branch `orion/keiracom-core-curation` (Agency_OS untouched; reversible):**
src/ KEEP **238**, zero dead-BDR path signals across the entire KEEP set.
```
(a) COMPILE: 238 kept src/*.py compiled, 0 failures
(b) RESOLVE: 165 entrypoints, walked 255 files, 0 imports pointing at a MISSING (removed) module
(c) ZERO-REF: removed modules referenced in curated tree = 0
(d) MAPPER: kept ORM models import + configure_mappers() = OK
NEG-TEST PASS (compile+resolve+zero-ref+mapper over 165 entrypoints, 238 kept, 11 removed)
```
Reproduce: `python3 scripts/repo_split/import_closure.py --include-product --confirmed-keep-file scripts/repo_split/confirmed_keep_hoo_2026-06-04.txt --json scripts/repo_split/closure_manifest.json && python3 scripts/repo_split/neg_test.py`
**READY for Atlas gate-2 RE-PASS** (independent neg_test.py re-run over the 165-set + C3 fresh-clone zero-dead-BDR assert).

---

## §8 GATE-2 ROUND-2 — scripts/ dead-BDR archival (2026-06-04)
Atlas's stronger **full-absent-set zero-ref** caught a second bleed one level over:
dead-BDR **scripts/** are entrypoint-class — not import-reached, so the import-closure
+ 165-entrypoint neg-test are structurally blind to them. §4.6 classification:
a script is KEEP only if it is a LIVE entrypoint (systemd/hook/cron/timer seed) OR a
current fleet-ops tool; else, if dead-BDR (GMB/ABN/business-universe/campaign/lead-gen/
enrichment/Pipeline-F/old-BDR-directive-tests), ARCHIVE. Traced each (no mass-remove).

**ARCHIVED — 44 dead-BDR scripts** (none a live seed; verified):
GMB pilots (gmb_pilot2/2_resume/2_retry/3/3_resume/4/_sydney, gmb_process_snapshot(_v2)),
GMB enrich (t2_gmb_enrich(_v2), test_gmb_match_live, test_gmb_match_with_scraper),
ABN/BU (abn_match_sweep, load_business_universe, load_abr_names, backfill_300_to_bu,
backfill_test_data_to_bu, backfill_t5_log, migrate_leads_to_pool), campaign_sender,
enrichment vendor tests (301_email_discovery, 302_contactout_validation,
fm_stage2_contactout_search, zoominfo_actual_company_test, zoominfo_au_coverage_test,
test_keyword_discovery, test_t125_efficient_media, rescore_113_drafts_2026_05_08),
pipeline-stage tests (335_1_stage_8, 335_bd_company_test, 336_v2_pipeline, 338_1_stage_9,
integration_test_300, seed_demo_tenant [seeds BDR campaigns], preflight_check [Pipeline F v2.1]),
old-BDR directive tests (directive_048_dm_tiers/validation/validation_part2,
directive_144_live_waterfall_test [imports archived bright_data_client],
directive_144_waterfall_test_mock, directive_243_part2, directive_243_serp_research,
directive_244_qual_gate).

**EXCLUDED — kept (live entrypoint OR fleet-ops, NOT dead-BDR):**
- `orchestrator/ceo_decision_sweeper.py` (Atlas false-positive; fleet/CEO governance).
- `classifier/discovery_log_classifier.py`, `fix_dead_refs_listener_seed_v1.py`,
  `seed_claude_md_facts.py`, `alerts/pipeline_failure_alert.py` (fleet-ops).
- `session_store/userpromptsubmit_handler.py` (fleet Claude Code hook; "serp" is a
  substring false-positive inside "u·serp·rompt").

**TWO RESIDUALS FLAGGED — NOT dead-BDR-archival (need a ruling, out of my scope):**
1. `scripts/alerts/lead_quality_anomaly.py` — BDR-flavored (24h propensity pass-rate),
   BUT its `agency-os-alert-lead-quality.timer` is **enabled + active** → a LIVE scheduled
   entrypoint right now. Per the KEEP rule (live timer seed) it stays. Its retirement is a
   **host-side systemd decision** (disable the timer first), not a repo archival —
   archiving the script would break an enabled timer. (Sibling `daily-digest.timer` is
   *disabled*; `budget-threshold`/`pipeline-failure` enabled.)
2. `scripts/spawn_nova.py` — FLEET tool (spawns Nova) importing `src.fleet.session_manager`,
   which **never existed in this repo** (no git history). Pre-existing dangling fleet
   forward-ref, NOT BDR, NOT produced by this curation. Flagged for fleet-owner triage.

**VERIFICATION (verbatim):**
```
closure: src/ 238 KEEP / 0 REMOVE; EDGE CHECK PASS (4 live-edges in KEEP)
(a) COMPILE: 238 kept src/*.py compiled, 0 failures
(b) RESOLVE: 165 entrypoints, walked 255 files, 0 imports pointing at a MISSING module
(c) ZERO-REF: removed modules referenced in curated tree = 0
(d) MAPPER: kept ORM models import + configure_mappers() = OK
NEG-TEST PASS
C3 BDR-name sweep (scripts/+src/): 2 hits, both KEEP — lead_quality (live timer, flagged) +
  userpromptsubmit_handler (serp-substring false-positive)
FULL-ABSENT-SET zero-ref (scripts/+src/): 1 residual — spawn_nova->src.fleet.session_manager
  (flagged pre-existing fleet dangling; import_closure doc-examples neutralized)
```
**READY for Atlas gate-2 round 3** with the two flagged residuals for ruling.

---

## §9 GATE-2 ROUND-3 — EXHAUSTIVE TOP-LEVEL CLASSIFICATION (2026-06-04, convergent last pass)
Atlas C3 round-3 caught the 4th completeness bleed: ROOT-level loose files + dirs were
never curated (closure is src/-only). Per elliot's convergent directive, EVERY top-level
entry is now classified KEEP/ARCHIVE — nothing left uncovered.

### KEEP — fleet/product runtime, governance, infra (dirs)
`src` `scripts` `tests` `supabase` (206 canonical migrations) `keiracom_system` (fleet
Hindsight/MAL infra) `memory` `personas` `skills` `governance` `infra` `systemd` `config`
`docs` `hooks` `mcp-servers` (fleet servers) `agents` `projects` `app-data` `mcp-servers`
+ fleet dotdirs `.beads .claude .clawdbot .clawdhub .openclaw .gates .githooks .github .cache`

### KEEP — files
14 fleet docs: AGENTS, ARCHITECTURE, BOOTSTRAP, CLAUDE, CLAUDE_DESKTOP, CONTRIBUTING,
DEFINITION_OF_DONE, DEPLOYMENT, ENFORCE, HEARTBEAT, README, SOUL, TOOLS, USER .md (+IDENTITY).
Infra/config: docker-compose.yml, Dockerfile{,.dispatcher,.prefect,.worker}, ecosystem.config.cjs,
package{,-lock}.json, prefect.yaml, pytest.ini, railway{,.prefect,.worker}.toml, ruff.toml,
conftest.py, requirements.txt, .gitignore, .mcp.json, .pre-commit-config.yaml, .railway_deploy,
.railwayignore.

### ARCHIVED — dead-BDR / obvious-dead (this pass): 69 loose files + 6 dirs
- **Dirs (6):** `frontend/` (residual tsbuildinfo; BDR Next.js dashboard — keiracom.com product
  site is a separate Dave decision), `data/` (founding_20_prospects.csv, gmb_pilot_results.jsonl),
  `migrations/` (40 BDR sales_pipeline/founding/demo — supabase/migrations is canonical; NO
  alembic.ini/Docker/prefect reference), `alembic/` (10 BDR outreach/domain migrations, unreferenced),
  `SKILLS/` (uppercase stray dup; canonical is `skills/`), `prompts/` (historical CC ICP/phase/UI/
  outreach build prompts + landing copy — all dead Agency-OS build artifacts).
- **Loose files (69):** 21 dashboard/landing/prototype `.html` + 9 dashboard `.png` +
  agency-os-prototype.zip + original-*.mp4 + 4 strays (_test_token.txt, test_triage_output.txt,
  test_icp_extraction.py, prefect-snapshot-2026-04-04.txt) + **vercel.json** (deploys the archived
  frontend; product-site deploy is a separate decision) + 32 dead `.md` (audits: AUDIT_GAPS/
  AUDIT_REPORT/CODE_AUDIT_COMPLETE/CODEBASE_AUDIT/DOCS_AUDIT/FINANCE_AUDIT/GAP_AUDIT/INFRA_AUDIT/
  CLAUDE_CODE_AUDIT; plans: AUTONOMOUS/MASTER/INTEGRATION_MASTER/PHASE_2_REMEDIATION/PHASE_21/
  PROJECT_BLUEPRINT{,_FULL_ARCHIVE}/SYNC_ALIGNMENT; BDR: ABN_FIELD_VERIFICATION/AGENCY_OS_STRATEGY/
  CLAUDE_CODE_PROMPT_CIS_DATA_GAPS/GAP_ANALYSIS/unipile; strays: CEO_QUESTIONS/DAVE_INPUT_FORM/
  DEPLOYMENT_ISSUES/INFRA_FIX_REPORT/FILE_TREE/«C:\AI…FILE_TREE»/HANDOFF[deprecated]/PROGRESS/
  progress_backup/progress_18b_append).

### FLAGGED — dead-BDR but LIVE-config-referenced (rulings needed; NOT unilaterally actioned)
1. `mcp-servers/{dataforseo,prospeo,salesforge,telnyx,unipile,vapi}-mcp` — BDR enrichment/
   distribution vendors, but **`.mcp.json` still wires all 6**. Archiving them requires editing the
   central live MCP config; recommend a COUPLED archival + `.mcp.json` cleanup (parallel to
   frontend↔vercel.json) as a ruling, to avoid broken refs. Fleet MCPs kept: gmail, keiradrive,
   memory, prefect, railway, resend, vercel, telegram (+ supabase/redis).
2. `scripts/alerts/lead_quality_anomaly.py` — BDR-flavored but timer ENABLED+ACTIVE (host-side retire).
3. `scripts/spawn_nova.py` — fleet tool, pre-existing `src.fleet.session_manager` dangling ref (never in repo).

### VERIFICATION (verbatim, hardened sweep over src + scripts + ROOT)
```
closure: src/ 238 KEEP / 0 REMOVE; EDGE CHECK PASS (4 live-edges)
(a) COMPILE 238 0-fail  (b) RESOLVE 165 entrypoints 0-broken  (c) ZERO-REF 0  (d) MAPPER OK  -> NEG-TEST PASS
ROOT dead-BDR-signal sweep: ZERO dead-BDR-signal root files
FULL-ABSENT zero-ref (src+scripts): 1 residual = spawn_nova->src.fleet.session_manager (flagged)
kept-file -> archived-entry references: 0 real (2 matches both false-positive: import_closure DEAD_DIRS
  config + a prose comment in vault_secrets_migrate.py)
```
**READY for Atlas gate-2 round-4** (final fresh-clone eyeball + hardened sweep). Modulo the 3 flagged
live-referenced residuals (each with rationale + a ruling), the repo top-level is zero-actionable-dead-BDR.

---

## §10 GATE-2 ROUND-4 — MCP cleanup + WHOLE-TREE all-files dead-BDR asset sweep (2026-06-04)
Two coupled completeness classes closed in one converging pass.

### (A) Dead-vendor MCP servers + coupled config cleanup (elliot+Atlas ruling)
Archived 8 dead-BDR MCP server dirs: dataforseo, prospeo, salesforge, telnyx, unipile, vapi
(lead-gen enrichment/distribution vendors) + vercel-mcp (orphaned — deploys the archived
frontend) + resend-mcp (BDR email; no live fleet alert sends via it — only cold_auth_proof
credential-checks the key). SAFETY-FIRST verified: zero python import / subprocess / mcp-bridge
call to any of the 8 in the kept tree. Coupled config cleanup (no broken refs): removed the 8
entries from BOTH `.mcp.json` AND `.claude/settings.json`. Kept (fleet/product): supabase, redis,
prefect, railway, memory, keiramail (gmail-mcp backed), keiradrive. Also tidied stale dead-BDR
`__all__` in `src/integrations/__init__.py` (ABN/Vapi/ElevenLabs/Leadmagic exports → []).

### (B) WHOLE-TREE all-files dead-BDR asset sweep (closure is .py-only — blind to data/assets)
Enumerated EVERY tracked file (all types, all depths). Archived 369 dead-BDR data/asset files:
- `scripts/output/` (33 BDR pipeline dumps: 300a-k/301/302/304/317/335/336/338 + fm_prospects csv).
- `scripts/` data blobs: fm_raw_profiles.json (4.7M), t2_gmb_results.jsonl, zoominfo_*.json.
- `src/data/au_suburbs.csv` (885K geo — verified unused by kept code).
- `docs/marketing/` (entire: landing_page_examples_v0/{v1,v2,v3} v0.dev mockups + headshly pngs +
  MARKETING_*/LANDING_PAGE_*/FOUNDING_20_CAMPAIGN_SIM/EXPERT_PANEL + assets).
- BDR docs: docs/architecture/{business,frontend}/CAMPAIGNS+LEADS, flows/OUTREACH, e2e J2_CAMPAIGN,
  phases/PHASE_12_CAMPAIGN_EXEC, research/ZOOMINFO_AU_COVERAGE, specs/{CAMPAIGN_SKILLS,LEAD_POOL*,
  database/CAMPAIGNS+LEADS,integrations/GMB_SCRAPER}, audits/OUTREACH_AUDIT.
- BDR skills: skills/campaign/, skills/leadmagic/. BDR memory: memory/leadmagic-trial/, decisions/031-gmb-replacement.
Each traced to genuinely dead-BDR (not fleet/product-used) before removal.

### KEEP-GUARDRAILS honoured (NOT archived)
`.beads/` (11, fleet issue tracker), `supabase/migrations` (206, canonical), `.claude/` (80, hooks/
config/settings), `.git`, 14 fleet docs, kept MCP/skills, all fleet/product code + config.

### FLAGGED — BDR content under `.claude/` (kept per elliot's "KEEP .claude/" guardrail; ruling)
`.claude/agents/fix-p2/fix-{10-campaign-fk,11-campaign-performance}.md`, `.claude/skills/
{enrichment/brightdata-gmb,leadmagic}/SKILL.md` — dead-BDR content but under the guarded `.claude/`
tree; left in place this pass, surfaced for a ruling (archive BDR skill/agent docs within .claude?).
Prior standing KEEP flags: lead_quality_anomaly (live timer), spawn_nova (pre-existing fleet dangling).

### VERIFICATION (verbatim, whole-tree)
```
closure src/ 238 KEEP/0 REMOVE, EDGE PASS; neg-test (a)238-compile (b)165-resolve (c)zero-ref (d)MAPPER -> PASS
WHOLE-TREE dead-BDR-asset residual (excl .py/.claude-flagged/guardrails): 0
.mcp.json + .claude/settings.json: both = [keiradrive,keiramail,memory,prefect,railway,redis,supabase], zero dead-vendor
full-absent zero-ref (src+scripts): 1 = spawn_nova (flagged); kept->archived live refs: 0
guardrails intact: .beads 11, supabase/migrations 206, .claude 80
```
**READY for Atlas WHOLE-TREE gate-2 round-4** (browse-into-ANY-dir = zero dead-BDR + neg-test 4).

---

## §11 METHOD SWITCH — allowlist-KEEP / archive-REST (terminal) — DRAFT, application HELD
Atlas+elliot: the category/denylist sweep is structurally non-converging (always a next
uncovered category — docs/specs, skills, frontend-docs, even a non-import-reached BDR .py
survived). INVERTED to allowlist: KEEP-SET = curated .py (src closure 238 + scripts seeds/
fleet-ops + tests-of-kept + tooling) UNION explicit fleet/product non-.py allowlist;
ARCHIVE = everything not in keep-set. Inverse risk (wrongly archiving fleet) mitigated:
uncertain → FLAG bucket (kept, surfaced), never silently archived.

Tool: `scripts/repo_split/allowlist_classify.py` (deterministic, non-destructive — writes
`allowlist_archive.txt` + `allowlist_flag.txt`). First-cut over 2851 tracked files:
- **KEEP 2056** (all curated .py + fleet dirs + fleet-doc allowlist + fleet skills).
- **ARCHIVE 298** (high-confidence dead-BDR): 143 tests importing removed modules, 111
  BDR-signal paths (distribution/dashboard/CIS/smartlead/icp docs), 35 BDR tests, 6
  non-allowlist skills (pipedrive/smartlead/hubspot/crm/seek/conversion), 3 dead .claude skills.
- **FLAG 497** (kept pending ruling): 276 docs/ uncertain, 220 memory/+other uncertain, 1 src-py.

APPLICATION HELD pending HoO confirmation of the method switch. Next on confirm: refine the
fleet-doc + memory allowlist to shrink FLAG to genuinely-uncertain, then apply archive-rest +
neg-test (kept .py boot) + a NOT-ARCHIVED-FLEET/PRODUCT inverse check + Atlas terminal gate-2
(BOTH directions: zero dead-BDR AND zero fleet/product wrongly archived).
