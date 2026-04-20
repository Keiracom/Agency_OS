# Directive #323 — V7 Pipeline Forensic Audit
## Tasks A, B, C — Research Agent Findings
### Date: 2026-04-07 | Agent: research-1 (Sonnet 4.6)

---

## TASK A — Architecture Provenance

### A1. Ratification Commit Evidence

| Architecture | Commit | Date | Message |
|---|---|---|---|
| v6 ratified | `c0db7ad` | 2026-03-27 | `Directive #269: Architecture v6 ratification — Section 3 rewrite (10-layer engine), Section 2 + 12 updated` |
| v7 ratified | `74ac09a` | 2026-03-28 | `docs: Directive #278 — v7 architecture alignment. Ratify v7 pipeline. v6 superseded.` |
| v7 current | `07ecaa1` | Apr 2026 | `docs(manual): Directive #302 — full rewrite sections 2-8, current state Apr 2026` |

SOURCE: `git log --oneline --all --grep="#269\|#278"`

### A2. What v6 Promised vs What v7 Promised vs What Exists Today

#### v6 (commit `c0db7ad`, #269, ratified 2026-03-27)
- **Title:** Architecture v6 — 10-layer engine. "Discovery by SPEND + GAPS + FIT"
- **Structure:** 10 layers (Layer 1=Discovery, Layer 2=5-source parallel discovery, Layer 3=cheap filter, Layer 4=DFS tech/rank/historical, Layer 5=fit scoring, Layer 6=competitive intel, Layer 7=GMB, Layer 8=DM, Layer 9=Haiku message gen, Layer 10=scheduling)
- **Cost model:** ~$0.27/prospect total
- **Key claim:** Multi-source Layer 2 (Categories + Ads Search + HTML Terms + Jobs + Competitors). DFS Google Jobs, HTML Terms, and competitor network expansion central to discovery.
- **Build plan:** #270–#281 queued to build the 10 layers

#### v7 (commit `74ac09a`, #278, ratified 2026-03-28 — ONE DAY LATER)
- **Title:** Architecture v7 — "Signal-first organic discovery"
- **Critical revision from v6:** 5-source Layer 2 REPLACED with single endpoint: `domain_metrics_by_categories`. Rationale documented: "DFS Google Jobs broken (40402 Invalid Path), HTML Terms unreliable for AU, competitor expansion better as enrichment step."
- **Confirmed live:** domain_metrics_by_categories returns 22,592 AU dental domains at $0.001/domain
- **Renamed structure:** Still calls them "Layers" in documentation but v7 Sprint Plan (#279 onward) shows build sequence diverging from layer numbering
- **Dead endpoints declared:** DFS Google Jobs, Layer 3 Bulk Traffic Estimation

#### Current State (Manual Section 3, commit `07ecaa1`, `ed82d15`)
- **Title:** "SECTION 3 — PIPELINE ARCHITECTURE (v7, proven Apr 2026)"
- **Structure language shift:** Manual no longer uses "Layer N" terminology. Uses stage-named sections: DISCOVERY, SCRAPING, INTELLIGENCE LAYER, SCORING, INTELLIGENCE ENDPOINTS, DM IDENTIFICATION, EMAIL WATERFALL.
- **Stage numbers in code:** `pipeline_orchestrator.py` docstring documents 9 stages (1=Discovery, 2=Spider, 3=DNS+ABN, 4=Affordability gate, 5=Intent free gate, 6=Paid enrichment, 7=Intent full score, 8=DM identification, 9=Reachability+card build). Stage 7c=Vulnerability Report, Stage 11=Haiku refine.
- **NO layer numbering exists in current code.** The term "Layer" in current code only appears in `layer_2_discovery.py` and `layer_3_bulk_filter.py` — both orphaned v6-era files (see Task C).

### A3. Architecture Terminology Drift

FINDING: The v6 architecture used "Layer N" (1–10). v7 documentation retained "Layer" terminology at ratification. By the time of #293 (stage-parallel refactor, PR #255), the orchestrator's internal docstring switched to "Stage N" (1–9). The Manual's current Section 3 uses neither numbers consistently — it uses section headers (DISCOVERY, SCRAPING, etc.). This creates three incompatible numbering systems across the codebase and documentation.

FLAGS:
- `layer_2_discovery.py` and `layer_3_bulk_filter.py` are v6-era artifacts. They are NOT called by `pipeline_orchestrator.py`. They exist in the repo but are orphaned from production execution (see Task C).
- Manual Section 3 line 202 states: "These fields feed the Vulnerability Report (designed, not yet built — see Section 9)." This is STALE — `generate_vulnerability_report()` WAS built (#306, PR #269). The note was not updated.

SOURCE: `docs/MANUAL.md` line 121–240; `src/pipeline/pipeline_orchestrator.py` lines 1–20 (docstring); commits `c0db7ad`, `74ac09a`, `07ecaa1`

---

## TASK B — Sprint Completion Audit (Directives #280–#316)

### B1. Matrix (boundary-matched grep, pattern: `Directive #N\b|#N —|#N:`)

| Directive | Git Status | Commit | Notes |
|---|---|---|---|
| #280 | FOUND | `1bc7b3c` | Discovery Engine v7, PR #242 |
| #281 | FOUND | `c840a5f` | Layer2 coverage gap tests, PR #244 |
| #282 | FOUND | `f16d95f` | Sprint 2 free intelligence sweep, PR #245 |
| #283 | FOUND | `2d7f607` | Section 21 segment testing strategy |
| #284 | FOUND | `e1677e3` | DFS date params + DiscoverySource enum |
| #285 | FOUND | `bbf52f2` | Free enrichment quality fixes, PR #248 |
| #286 | FOUND | `39351c0` | DM identification layer docs |
| #287 | FOUND | `e18418f` | SERP-first DM waterfall docs |
| #288 | FOUND | `f0a2cff` | Affordability scorer + orchestrator docs |
| #289 | FOUND | `57af3ef` | ABN multi-strategy matching, PR #252 |
| #290 | FOUND* | `4ae144f` / `f0670dd` | Orchestrator wiring. NOTE: boundary grep returned `2af3f6d` (a #317.3 fix) as false positive — the actual #290 commits are `f0670dd` + `4ae144f` |
| #291 | FOUND | `5fec3da` | Two-dimension scorer + ads detection, PR #254 |
| #292 | FOUND | `6b4b870` | Architecture alignment + ABN Settings fix |
| #293 | FOUND | `7618618` / `4ae9629` | Stage-parallel orchestrator, PR #255 |
| #294 | FOUND | `4ced9e7` | Multi-category rotation + claimed_by, PR #256 |
| #295 | FOUND | `7fbf9be` | httpx primary scraper, PR #257 |
| #296 | FOUND | `3de9621` | Sonnet/Haiku intelligence layer, PR #258 |
| #297 | FOUND | `ffb2a3a` | ABN audit, PR #259 |
| #298 | FOUND | `c1a2434` | Multi-category discovery, PR #260 |
| #299 | FOUND | `77962f9` | Email waterfall, PR #261 |
| #300 | FOUND | `48fc446` | Integration test + FIX series |
| #301 | FOUND | `e9b7740` | SMTP email verifier + LAW XVI |
| #302 | FOUND | `07ecaa1` | Manual full rewrite sections 2–8 |
| #303 | FOUND | `74917e9` | Wire four intelligence endpoints, PR #266 |
| #304 | NOT IN GIT | — | Manual says "COMPLETE — test only" (keyword discovery test, 382 domains). No code commit. PR #267 is the `#304-FIX` for dynamic date, not #304 itself. |
| #305 | FOUND | `8625f64` | Card quality waterfalls, PR #268 |
| #306 | FOUND | `ed82d15` | Vulnerability Report docs header fix |
| #307 | FOUND | `3cbddc6` | ABN matcher single-keyword fix, PR #275 |
| #308 | NOT IN GIT | — | Not found in git log. Not referenced in Manual. |
| #309 | FOUND | `00d4a58` | 4 new onboarding pages |
| #310 | FOUND | `1657b72` | Billing lifecycle wiring |
| #311 | FOUND | `d82eff0` | Outreach execution layer, PR #285 |
| #312 | FOUND | `97db20a` | Salesforge domain pool architecture |
| #313 | NOT IN GIT | — | Not found in git log. Not referenced in Manual. |
| #314 | FOUND | `e10a1da` | Customer-facing flow + dashboard, PR #288 |
| #315 | FOUND | `c178179` | crm-sync-flow permanently deleted |
| #316 | FOUND | `d587e11` | Salesforge Stack audit + Megaforge evaluation |

### B2. Missing Directives

**3 directives not found in git:**
- `#304` — Manual classifies as "test only" (no code shipped). Exploratory keyword discovery run.
- `#308` — No record in git or Manual. Gap between #307 and #309.
- `#313` — No record in git or Manual. Gap between #312 and #314.

FLAGS:
- `#308` and `#313` are unexplained gaps. Neither appears in `docs/MANUAL.md` at all. These may be directives that were scoped/planned but superseded, or executed informally without a git commit.
- Manual Section 2 states "Last directive: #306" but git shows #307–#317 all have commits. The Manual is stale by 11 directives at minimum.

SOURCE: `git log --oneline --all`; `docs/MANUAL.md` lines 619–623, line 26

---

## TASK C — Codebase Reality Audit

### C1. Pipeline Files Summary (24 files, 8,096 total lines)

| File | Lines | Status | Evidence |
|---|---|---|---|
| `pipeline_orchestrator.py` | 1,207 | **CANONICAL v7** | Imports: `ProspectScorer`, `intelligence`, `email_waterfall`, `discovery` (MultiCategoryDiscovery). 9-stage docstring. Called by: API campaigns route + integration test scripts. |
| `intelligence.py` | 646 | **CANONICAL v7** | 113 callers (grep counts all field/method name matches). Contains comprehend, afford, classify, reviews, vulnerability report, refine_evidence. |
| `free_enrichment.py` | 915 | **CANONICAL v7** | 8 callers. httpx scraper, DNS/MX, ABN lookup. Used by orchestrator Stage 2+3. |
| `discovery.py` | 340 | **CANONICAL v7** | `MultiCategoryDiscovery` class. Called only from within `layer_2_discovery.py` usage note (docstring) — but `pipeline_orchestrator.py` uses it directly via `src.config.category_registry`. `discovery.py` line 313: "Compatible with PipelineOrchestrator.run_parallel() worker interface." |
| `email_waterfall.py` | 535 | **CANONICAL v7** | Imported directly by `pipeline_orchestrator.py` line 34. 4-layer waterfall. |
| `dm_identification.py` | 284 | **CANONICAL v7** | 4 callers. DM waterfall T-DM1 through T-DM4. |
| `prospect_scorer.py` | 342 | **CANONICAL v7** | Imported by `pipeline_orchestrator.py` line 30. Two-dimension scorer (#291). |
| `paid_enrichment.py` | 342 | **CANONICAL v7** | 3 callers. DFS Ads Search + GMB. |
| `rescore_engine.py` | 192 | ACTIVE (special) | 5 callers. Imports `stage_4_scoring._calc_budget_score` and `_calc_pain_score`. Bridge between v5 scoring helpers and v7 rescore path. |
| `layer_2_discovery.py` | 459 | **ORPHANED (v6 artifact)** | 0 prod callers in src/. Has tests (test_layer_2_discovery.py, test_layer2_pull_batch.py, test_layer2_discovery.py). The class `Layer2Discovery` is NOT imported by `pipeline_orchestrator.py`. It documents itself as "Used by PipelineOrchestrator.run()" but the orchestrator was refactored and no longer imports it. |
| `layer_3_bulk_filter.py` | 205 | **ORPHANED (v6 artifact)** | 0 prod callers. 0 test callers. Pure dead code. Manual notes "Layer 3 bulk filter (now superseded by v7)" at line 640. |
| `stage_1_discovery.py` | 199 | **ORPHANED (v5 artifact)** | 1 caller: `src/pipeline/__init__.py` exports `Stage1Discovery`. The `__init__.py` contains only this one line. No other src code imports it. Has test coverage (test_stage_1_discovery.py). |
| `stage_2_gmb_lookup.py` | 210 | **ORPHANED (v5 artifact)** | 0 prod callers in src/. Has test coverage (test_stage_2_gmb_lookup.py). |
| `stage_3_dfs_profile.py` | 201 | **ORPHANED (v5 artifact)** | 0 prod callers. Has test coverage (test_stage_3_dfs_profile.py). |
| `stage_4_scoring.py` | 438 | **PARTIALLY ALIVE (v5)** | 3 callers: `rescore_engine.py` imports `_calc_budget_score` + `_calc_pain_score`; `signal_config.py` docstring references it. Has test coverage. |
| `stage_5_dm_waterfall.py` | 390 | **ORPHANED (v5 artifact)** | 0 prod callers. Has test coverage (test_stage_5_dm_waterfall.py). |
| `stage_6_reachability.py` | 160 | **ORPHANED (v5 artifact)** | 0 prod callers. Has test coverage (test_stage_6_reachability.py). |
| `stage_7_haiku.py` | 246 | **ORPHANED (v5 artifact)** | 0 prod callers. Has test coverage (test_stage_7_haiku.py). |
| `affordability_scoring.py` | 210 | **ORPHANED** | 0 prod callers. Prospect_scorer.py docstring says "Replaces AffordabilityScorer as the primary scorer." This is the replaced module. |
| `social_enrichment.py` | 228 | **ORPHANED** | 0 prod callers. Built for Stage 9+10 (BD LinkedIn scrape) but NOT imported by `pipeline_orchestrator.py`. The orchestrator handles LinkedIn URL storage but does not call `scrape_linkedin_company` or `scrape_linkedin_dm`. |
| `mobile_waterfall.py` | 138 | **ORPHANED** | 0 prod callers. `run_mobile_waterfall()` function exists but is not imported anywhere in src/. |
| `campaign_claimer.py` | 110 | **ORPHANED (from src/)** | 0 prod callers in src/. Has test coverage (test_campaign_claimer.py). `pipeline_orchestrator.py` handles `exclude_domains` / claimed-domain exclusion inline, not via this class. |
| `category_rotation.py` | 98 | **ORPHANED (from src/)** | 0 prod callers in src/. Has test coverage (test_category_rotation.py). `pipeline_orchestrator.py` uses `src.config.category_registry` instead. |
| `__init__.py` | 1 | Stale re-export | Exports `Stage1Discovery` — a v5 class no longer used in production. |

### C2. Canonical Entry Points

The production execution path is:
```
pipeline_orchestrator.PipelineOrchestrator.run_parallel()
  └── MultiCategoryDiscovery (discovery.py) — on-demand batch pull
  └── free_enrichment.py — Stage 2+3 (httpx, DNS, ABN)
  └── intelligence.py — Stages 4,5,5b,7c,11
  └── paid_enrichment.py — Stage 6 (DFS ads, GMB)
  └── dm_identification.py — Stage 8
  └── email_waterfall.py — Stage 9
  └── prospect_scorer.py — scoring gates
```

There is **no external caller** of `PipelineOrchestrator` in `src/` outside of the pipeline module itself and a single integration test script (`scripts/integration_test_300d.py` imports `GLOBAL_SEM_ABN` only). The SSE streaming entry point (`SSECardStreamer`) is defined inside `pipeline_orchestrator.py` and consumed by tests only — no API route currently wires it.

### C3. Orphaned File Classification

**v5-era (7 files, built #257–#264, superseded by v7 sprint starting #279):**
`stage_1_discovery.py`, `stage_2_gmb_lookup.py`, `stage_3_dfs_profile.py`, `stage_4_scoring.py` (partially alive via rescore_engine), `stage_5_dm_waterfall.py`, `stage_6_reachability.py`, `stage_7_haiku.py`

**v6-era (2 files, built #271–#274, superseded by v7 at #278):**
`layer_2_discovery.py`, `layer_3_bulk_filter.py`
Manual explicitly marks these: "Layer 2 discovery engine (5-source — now superseded by v7)" and "Layer 3 bulk filter (now superseded by v7)" at lines 638+640.

**Post-v7, unintegrated (3 files):**
`social_enrichment.py` — built #300-FIX Issues 13–14 but never wired into `pipeline_orchestrator.py`
`mobile_waterfall.py` — built for Stage 9 but not called
`affordability_scoring.py` — replaced by `prospect_scorer.py` (#291)

**Utility/support (2 files, orphaned from production path):**
`campaign_claimer.py` — claiming logic inlined in orchestrator
`category_rotation.py` — superseded by `src/config/category_registry.py`

### C4. Stale Manual Reference

SOURCE: `docs/MANUAL.md` line 202
> "These fields feed the Vulnerability Report (designed, not yet built — see Section 9)."

This is contradicted by:
- Directive #306 commit `ed82d15` — Vulnerability Report built and wired
- Manual line 623: `#306 | Marketing Vulnerability Report: generate_vulnerability_report() Sonnet Stage 7c, 6 sections... | PR #269 open`
- Manual Section 3 line 155 fully documents Stage 7c as implemented

The "not yet built" note at line 202 was not cleaned up after #306 shipped.

---

## Summary of Flags

| Flag | Severity | Detail |
|---|---|---|
| Manual stale by 11 directives | HIGH | Manual says "Last directive: #306" — git shows #307–#317 shipped |
| `layer_2_discovery.py` orphaned but has tests | MEDIUM | v6 artifact. Docstring claims "Used by PipelineOrchestrator.run()" — false |
| `layer_3_bulk_filter.py` dead code | LOW | v6 artifact. 0 callers anywhere. Manual explicitly supersedes it. |
| `social_enrichment.py` built but unwired | HIGH | Stage 9+10 LinkedIn scrape module exists but is never called in production |
| `mobile_waterfall.py` built but unwired | MEDIUM | Mobile number discovery exists but is not in the pipeline execution path |
| `stage_[1-7]_*.py` orphaned v5 files | MEDIUM | 7 files, ~1,844 lines of dead production code. Tests still run against them. |
| `#308`, `#313` unexplained gaps | LOW | Two directive numbers have no git or Manual record |
| Manual Section 3 line 202 stale | LOW | "Vulnerability Report not yet built" — contradicted by #306 delivery |
| `__init__.py` exports dead v5 class | LOW | Exports `Stage1Discovery` which has no prod callers |
