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
