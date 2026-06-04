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
