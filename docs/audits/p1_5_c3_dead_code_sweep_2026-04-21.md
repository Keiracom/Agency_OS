# P1.5-C3 Dead Code Sweep — 2026-04-21

**Directive:** P1.5-C3-DEAD-CODE-SWEEP
**Auditor:** Aiden (read-only, no fixes)
**Worktree:** /home/elliotbot/clawd/Agency_OS-aiden/
**Branch:** aiden/scaffold
**Base commit:** 539cd931 (origin/main HEAD at audit start)
**Companion to:** C1 System Audit (docs/audits/p1_5_system_audit_2026-04-21.md)

---

## 1. Why this audit exists

C1's deprecated-provider grep (`proxycurl|kaspr|apollo|hunterio|HunterIO`) came back clean. C3 widens the net to include **deprecated integrations by engine name** (`siege_waterfall`) and **versioned modules where a newer version exists** (`waterfall_v[012]`). The wider grep finds substantial dead-code surface that C1 missed.

**Scope gap fix:** C1's blind spot was literal provider-name grep. C3's wider grep catches engine-level dead code that wraps the same providers. Recommend future dead-reference checklists include the integration-wrapper names, not just the vendor names.

## 2. Headline numbers

- **~6,334 lines** of suspected-dead enrichment code across 3 files (`siege_waterfall.py` 2,796 + `scout.py` 2,127 + `icp_scraper.py` 1,411).
- **~1,096 lines** of superseded code in `waterfall_v2.py` (v3 is active per `CLAUDE.md` dead-references table).
- **~623 lines** in the orphan `lead_enrichment_flow.py` (not in `prefect.yaml`, still imports scout).
- **~543 lines** in `campaign_trigger.py` (imports `waterfall_v2`, may or may not be called).
- **3 registered Prefect deployments** (`enrichment-flow`, `intelligence-flow`, `pool-population-flow`) depend on the dead chain.
- **3 engine files** marked as deprecated patterns but still imported somewhere in the live tree.

## 3. Methodology

```
grep -rln -iE "proxycurl|kaspr|apollo|hunterio|hunter_io|abnfirstdiscovery|siege_waterfall|waterfall_v[012]" src/
```

Narrow to actual imports:

```
grep -rn -iE "^import.*apollo|^from.*apollo|proxycurl|kaspr|^import.*siege_waterfall|^from.*siege_waterfall|waterfall_v[012]|abnfirstdiscovery" src/
```

Cross-reference dead modules against the Prefect flow tree:

```
grep -rn "from src.engines.scout|from src.engines.icp_scraper|from src.enrichment.waterfall_v2|from src.integrations.siege_waterfall" src/
```

## 4. Findings by severity

### CRITICAL

**C3-C-01. Dead-chain flows are REGISTERED and READY in Prefect.**

`src/integrations/siege_waterfall.py` is marked dead in `CLAUDE.md`'s dead-references table. `src/engines/scout.py` imports from it at line 67 (`from src.integrations.siege_waterfall import EnrichmentTier, SiegeWaterfall, get_siege_waterfall`). `src/engines/icp_scraper.py` imports from it at line 62. These two engines are imported by:

- `src/orchestration/flows/enrichment_flow.py:37` (`daily_enrichment_flow` — registered as `enrichment-flow`)
- `src/orchestration/flows/intelligence_flow.py:27` (registered as `intelligence-flow` + `trigger-lead-research`)
- `src/orchestration/flows/pool_population_flow.py:36` (registered as `pool-population-flow`)
- `src/orchestration/flows/lead_enrichment_flow.py:37` (orphan — not in `prefect.yaml`)
- `src/orchestration/flows/onboarding_flow.py:129` (registered as `onboarding-flow` + `icp-reextract-flow`)
- `src/orchestration/tasks/enrichment_tasks.py:28` (task-level use)

Live call sites include `scout_engine.enrich_batch()` (`enrichment_flow.py:168`), `scout_engine.perform_deep_research()` (`intelligence_flow.py:156`), `scout.enrich_linkedin_for_assignment()` (`lead_enrichment_flow.py:209`).

If any of these deployments is triggered manually or on schedule, the flow crashes at import time (siege_waterfall's Apollo/Proxycurl clients are absent) or at runtime (first call to the dead provider). This is a latent CRITICAL — unused today, failure-as-soon-as-scheduled tomorrow.

### HIGH

**C3-H-01. Superseded `waterfall_v2.py` still imported.**

`CLAUDE.md` active path is `T0 GMB → T1 ABN → T1.5a SERP → ... → T5 Leadmagic Mobile` — that's Waterfall v3 / MapsFirstDiscovery. `src/enrichment/waterfall_v2.py` (1,096 lines) is superseded but still imported by `src/enrichment/campaign_trigger.py:16`. `src/enrichment/__init__.py:34` re-exports the v2 symbols publicly. Either v2 is secretly still in the path (in which case the MANUAL is wrong) or this is dead import surface.

**C3-H-02. Orphan flow file still in the tree.**

`src/orchestration/flows/lead_enrichment_flow.py` (623 lines) has no `prefect.yaml` entry (confirmed in C1 §3). It imports scout (which imports dead siege_waterfall). Safe to delete once no consumer is found. Recommend one `grep -rn "lead_enrichment_flow" src/` confirms zero imports before removal.

**C3-H-03. `src/integrations/__init__.py` publicly re-exports dead modules.**

`from src.integrations.siege_waterfall import SiegeWaterfall, get_siege_waterfall` at `src/integrations/__init__.py:24`. Anyone doing `from src.integrations import SiegeWaterfall` gets the dead class. Encourages misuse by IDE autocomplete.

### MEDIUM

**C3-M-01. `src/enrichment/__init__.py` re-exports from `waterfall_v2`.**

Similar to C3-H-03 but for the superseded (not-quite-dead) v2. Line 34 re-exports v2 symbols. Once v2 is removed, this breaks — cleanup coupled to C3-H-01.

**C3-M-02. `campaign_trigger.py` imports superseded v2.**

543 lines. If v2 is truly dead in production, this file is also dead. If v2 is still used for legacy campaigns (onboarding-flow?), waterfall_v2 promotion path needs documenting before any removal.

**C3-M-03. `src/engines/scout.py` and `icp_scraper.py` are the blast radius of C3-C-01.**

Cannot remove `siege_waterfall.py` without removing scout/icp_scraper. Cannot remove those without rewiring 5 flows (enrichment, intelligence, pool_population, lead_enrichment, onboarding). Scope of cleanup is large; staging it as 3-4 PRs is safer than one big sweep.

**C3-M-04. `agents/icp_discovery_agent.py:56` imports `icp_scraper`.**

Another dead-chain consumer in the agents layer. Same cleanup blast radius as C3-M-03.

### LOW

**C3-L-01. `src/engines/deprecated/voice_vapi.py` exists as a self-quarantined dead file.**

This is the GOOD pattern — file moved to `deprecated/` subfolder, signalling its status without still being imported. Apply this pattern to siege_waterfall/scout/icp_scraper/waterfall_v2 when cleanup PRs land.

**C3-L-02. `src/enrichment/campaign_trigger.py` may itself be orphaned.**

Need `grep -rn "from src.enrichment.campaign_trigger\|from src.enrichment import campaign_trigger"` to verify. If nothing imports it, it's a leaf dead branch.

### INFO (positive findings + context)

**C3-I-01. Existing `deprecated/` subfolder is the correct quarantine pattern.** Use it for future cleanup staging.

**C3-I-02. Pipeline F master flow does NOT depend on any dead-chain module.** Stage 1-11 live in `cohort_runner.py` + its stage_N functions, which call current APIs directly. Tonight's P5 run is unaffected by anything in this audit.

**C3-I-03. All dead-chain files last modified 2026-04-16 11:08.** That's a merge date (likely PR #340 — the AIDEN-SCAFFOLD commit sweep), not an active-edit date. The code hasn't been meaningfully touched in 5 days; safe to treat as cold.

**C3-I-04. Last directive before this audit that touched enrichment was F-CONTAMINATION-01** — narrow-scoped contamination fix, not a general refactor. No recent active work on the dead chain. Confirms it's safe to cleanup without surprising an in-flight change.

## 5. Explicit Phase 2 Dashboard blockers

**None direct.** The dashboard reads Supabase tables (`business_universe`, `dm_messages`, `ceo_memory`, `lead_tags`, etc.) that are written by the ACTIVE pipeline_f_master_flow chain, not by the dead scout/siege chain.

**Indirect risks worth flagging before Dashboard starts:**
- If a dashboard trigger accidentally fires a dead-chain flow (e.g., onboarding-flow during a Phase 2 demo), it crashes. Cleanup of C3-C-01 before Dashboard removes that class of demo risk.
- If Dashboard wants to surface enrichment progress, it must read from pipeline_f_master_flow outputs (`evo_flow_callbacks`, `business_universe.pipeline_stage`), not from scout-layer telemetry which is dead.

## 6. Recommended cleanup sequencing

Not in this directive's scope (C3 is report-only), but for follow-up directives:

1. **C3-CLEANUP-1** — pause the 4 registered Prefect deployments depending on scout (`enrichment-flow`, `intelligence-flow`, `trigger-lead-research`, `pool-population-flow`, `onboarding-flow`, `icp-reextract-flow`). Verify no scheduled fires. One Prefect config change.
2. **C3-CLEANUP-2** — remove the dead imports + re-exports from `__init__.py` files. Small PR, flushes out any hidden consumers (if tests break, we find the live consumer).
3. **C3-CLEANUP-3** — move `siege_waterfall.py`, `scout.py`, `icp_scraper.py`, `waterfall_v2.py`, `campaign_trigger.py`, `lead_enrichment_flow.py` to `src/engines/deprecated/` (or equivalent quarantine). Do NOT delete yet; 30-day observation period to catch unexpected consumers.
4. **C3-CLEANUP-4** — after 30-day quarantine with no consumer surfacing, delete. Total dead-surface removed: ~8,500 lines.

## 7. Dead-reference table additions

Recommend `CLAUDE.md`'s dead-references table expand from vendor-names-only to include **wrapper-module names**:

| Dead (additions) | Replacement |
|------------------|-------------|
| siege_waterfall | MapsFirstDiscovery / Waterfall v3 (already in table) |
| waterfall_v2 | Waterfall v3 / active T0→T5 path |
| ScoutEngine / get_scout_engine | cohort_runner stage functions |
| IcpScraperEngine / get_icp_scraper_engine | Smart Prompts + sdk_brain (per CLAUDE.md) |

Without the wrapper names in the table, future grep-for-dead-refs misses these.

---

**Auditor's meta-note:** this audit is read-only. No code was modified. Findings list locations, symptoms, and cleanup sequencing; actual removal is separate directive work. The one line this audit adds to the repo is this audit file itself.
