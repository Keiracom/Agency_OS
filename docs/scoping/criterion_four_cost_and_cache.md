# Scoping — V1 Criterion 4: Memory + Governance on API Token Spend + Cache

**Author:** Atlas, 2026-05-25.
**Purpose:** Scoping doc for the gaps between Phase 2 build wave 2 (metering substrate landed in PR #1137) and full criterion-four satisfaction. Plain English for Dave.

---

## Notes — canonical key value (per audit-dispatch checklist)

`ceo:memory_abstraction_layer_v1.v1_completion_criteria[3]` queried 2026-05-25 ahead of authoring.

> **Title:** Memory and governance on API token spend + cache
>
> **Description:** Every memory read/write and every governance decision tracked against real API cost. Caching built in so we are not burning tokens on repeat work. System cost-aware by design. Phase 2 build metering pipeline (PR #1137) is one component of this.

Phase 2 alignment note from the same key: Phase 2 build "covers partially" criterion 4 — "memory uses substrate with token-spend tracking via metering pipeline." Cache-awareness in governance and full attribution coverage are **not yet covered** and are the scope of this doc.

---

## The four scope items

### Item 1 — Cost-attribution wrappers around the six MAL primitives

**What it does.** Each call to Ingest / Recall / Synthesize / Supersede / Trace / Delete emits a cost-tagged log entry. The metering pipeline (PR #1137) reads those entries and produces per-tenant + per-callsign + per-primitive spend rollups. Today the wrappers (PR #1134) and the MCP server (PR #1136) pass through the operation but emit nothing the metering pipeline can attribute.

**Work pieces.**
1. Add a `CostAttribution` dataclass to `src/keiracom_system/memory/wrappers/_base.py` with fields: `tenant_id`, `callsign`, `primitive`, `model`, `input_tokens`, `output_tokens`, `cached_input_tokens`, `wall_seconds`, `timestamp`. Small — one file, ~30 LoC.
2. Wrap each of the six MCP tools (`src/keiracom_system/mcp/tools/*.py`) to capture the Hindsight response's token-count fields (Hindsight emits these in OTel spans per the smoke spike) and emit a `CostAttribution` to the metering pipeline. Six files, ~10 LoC each = ~60 LoC.
3. Plumb the callsign through. Today the MCP server takes `tenant_id` but not `callsign`. Add `callsign: str` as a required kwarg to `MCPServer.invoke()` so the attribution is unambiguous. One file edit + test additions ~20 LoC.
4. Tests — one positive + one negative per primitive (6 × 2 = 12 tests) plus 2 integration tests that round-trip an attribution event through a mock metering sink.

**Effort.** ~2 hours code + ~1 hour tests = ~3 hours, single PR.

**Dependencies.** PR #1137 metering pipeline landed (the substrate to write to). #1134 wrappers + #1136 MCP server (which I authored). No external blockers.

---

### Item 2 — Governance-decision cost-attribution

**What it does.** Every deliberator concur, every canonical-key query, every audit-dispatch review costs tokens. Right now we see only the eventual artefact (the PR review comment, the canonical-key paste) — never the token cost of the deliberation. Per-decision attribution lets the metering pipeline answer "did this PR's review consume more tokens than the build itself?"

**Work pieces.**
1. Define the governance-decision event taxonomy. Five categories: `deliberator_concur` (Aiden/Max/Elliot PR reviews), `canonical_key_query` (the audit-dispatch checklist queries), `audit_dispatch_review` (the doc-author's pre-write canonical paste), `dispatch_authoring` (Elliot writing a dispatch brief), `tier_router_decision` (per-MCP-call tier gate — see Item 1, may share substrate). One markdown spec + a `GovernanceDecisionType` enum in `src/keiracom_system/governance/cost_events.py`. ~50 LoC.
2. Instrumentation hooks at the four obvious decision-emit sites:
   - PR review comment posting (Aiden/Max/Elliot via `gh pr comment`) — wrap the call so the comment emit also writes a `governance_decision` row to the metering sink.
   - Canonical-key query — already centralised through `mcp-bridge` to Supabase; add cost-attribution emit at the bridge call site.
   - Audit-dispatch checklist — when a worker pastes verbatim into a Notes section, emit a `audit_dispatch_review` event keyed off the canonical-key name.
   - Dispatch authoring — Elliot's dispatch composition (Slack post + per-clone inbox file write). Out of process today; instrumentation is a small wrapper on the dispatch tool.
3. Aggregation table on the metering side. A `governance_decision_costs` view over the raw rows, with columns: timestamp, decision_type, actor (callsign or human), target (PR number, KEI id, canonical-key name), input_tokens, output_tokens, model.
4. Tests — same shape as Item 1 (positive + negative per decision-type, plus integration through mock metering sink).

**Effort.** ~3 hours code + ~1.5 hours tests = ~4-5 hours, single PR. Larger than Item 1 because the emit sites are spread across the codebase (PR-comment tooling, mcp-bridge, dispatch composer) rather than concentrated.

**Dependencies.** Item 1 (shares the metering sink contract). PR #1137 metering pipeline landed.

---

### Item 3 — Cache-pattern enforcement

**The constraint.** Claude prompt cache has a 5-minute TTL. Cache hits dramatically reduce input-token cost (~90% discount on cached tokens). Hits require the system-prompt prefix to match byte-for-byte AND a call within the 5-minute window. Today agents hit the cache incidentally — a long system prompt happens to repeat — but there is no design discipline that says "shape this batch of related calls so they all hit one warm cache window".

**Three options surfaced for Dave.**

| Option | What | Effort | Strength | Weakness |
| --- | --- | --- | --- | --- |
| **A. Discipline doc only** | Add a CLAUDE.md section "Cache discipline": consistent system prompt prefix per role; batch related calls within 5min windows; never re-order tool definitions within a session. | ~2h to write, ongoing read-discipline | Cheap, no infra | Voluntary — discipline drift over time |
| **B. Runtime warn-on-cache-bust** | A wrapper around the Claude API call inspects the request; if it differs from the prior request in this session by a cache-busting pattern (tool-definition reorder, system prompt mid-string change, >5min gap) it logs a `cache_bust` event the metering pipeline counts. | ~6-8h | Catches drift in production, attributable per agent | Detection lag — bad cache habits cost tokens before the warning fires |
| **C. PR-review linter** | A bd-style check at PR review time that scans agent prompt templates for cache-busting patterns (e.g. `{timestamp}` interpolated into system prompt, or tool definitions inside a loop). Flags PRs that introduce them. | ~4-6h | Catches at PR time before tokens burn | Only catches what the linter knows about; can't see runtime-dynamic prompts |

**Recommendation: ALL THREE, sequenced.** A (discipline doc) first because cheap. B (runtime warn) second because it gives the metering pipeline visible data. C (linter) third when the pattern set is well-enough understood to encode rules.

**Work pieces.**
1. **Item 3a (discipline doc)** — Write `docs/governance/cache_discipline.md`. Cover: consistent system prompt prefix per role (Atlas vs Orion etc), batching related calls, never-reorder tool definitions, log-the-prefix-hash so deviations are auditable. ~2 hours, one PR.
2. **Item 3b (runtime warn)** — Wrap the Claude API client used by the worker callsigns. Compute the system-prompt-prefix hash + tool-definition-set hash per call; on hash drift OR >5min gap, emit `cache_bust` event to metering. ~6-8 hours, one PR. Depends on item 3a (the linter rule set comes from the discipline doc).
3. **Item 3c (linter)** — PR-review linter. Scope: scan `src/`, `scripts/`, `prompts/` (wherever prompt templates live) for the patterns the discipline doc names as cache-busting. Run in CI as `Cache Discipline Lint` check; non-blocking warning at first, blocking after 30 days of tuning. ~4-6 hours, one PR. Depends on 3a (the rules) + 3b (the runtime data feeding the tuning).

**Effort total.** ~12-16 hours, three sequenced PRs.

**Dependencies.** PR #1137 metering pipeline (for the cache_bust event sink). Items 1-2 ship independently — cache discipline is orthogonal to attribution.

---

### Item 4 — Cost dashboard

**What it does.** Reads from the metering pipeline output. Per-tenant + per-callsign + per-agent-role spend over time. Answers questions like "did Aiden's deliberation last week cost more than Atlas's build?" and "is the Solo-tier customer cost-positive?".

**Where it lives.** Two options:

| Option | What | Pros | Cons |
| --- | --- | --- | --- |
| **A. New dashboard surface** | A standalone Next.js page under `frontend/app/(dashboard)/cost/` reading from the metering pipeline view. | Clean separation; can be product-customer-facing later (per-tenant view they can self-serve). | Yet-another surface to build + maintain. |
| **B. Part of criterion-two whole-system admin dashboard** | The whole-system admin dashboard from criterion 2 already exists as a surface. Cost becomes one panel among several (fleet health, KEI throughput, deliberation queue). | Wires into the criterion-2 surface that's already getting built; no new layout overhead. | Crowds the admin dashboard; couples cost dashboard release schedule to criterion 2's. |

**Recommendation: B (panel in criterion-2 admin dashboard) for V1, with the option to spin out a customer-facing per-tenant view later** when product enters general availability. V1 is internal-only; customers don't see their cost yet. Crowding the criterion-2 dashboard is fine for the V1 audience.

**Work pieces.**
1. SQL view on top of the metering pipeline data: `cost_attribution_rollup_daily` with columns `(day, tenant_id, callsign, primitive, governance_decision_type, model, input_tokens, output_tokens, cached_input_tokens, estimated_cost_usd, estimated_cost_aud)`. Lives in `supabase/migrations/`. Reads from PR #1137 substrate. ~80 LoC SQL + ~30 LoC unit tests. ~3 hours.
2. Dashboard panel — one new component `frontend/components/cost-panel/` rendering a stacked-area chart (spend over time, segmented by callsign or tenant). Reads the SQL view via the existing `frontend/lib/supabase-client.ts` pattern. ~6 hours including layout + tests.
3. Drilldown surface — a route `frontend/app/(dashboard)/cost/` that takes a callsign or tenant filter and shows the cohort: top primitives, top governance-decision types, top recent expensive calls (>$0.10 per call). ~6-8 hours.

**Effort.** ~15-17 hours total, two-three PRs (SQL view + dashboard panel + drilldown).

**Dependencies.** Items 1 + 2 (attribution emit must be live so the data is present). PR #1137 substrate. Criterion 2 admin dashboard scaffolding (sequenced ahead of this; if not yet wired the dashboard panel ships standalone first per Option A's fallback).

---

## Summary table — work / effort / dependencies

| Item | What | Effort | Sequenced behind | PR count |
| --- | --- | --- | --- | --- |
| 1 | MAL primitive cost attribution | ~3h | #1137 substrate | 1 |
| 2 | Governance-decision cost attribution | ~4-5h | Item 1 | 1 |
| 3a | Cache discipline doc | ~2h | — | 1 |
| 3b | Cache-bust runtime warn | ~6-8h | Item 3a + #1137 | 1 |
| 3c | Cache discipline linter | ~4-6h | Item 3b | 1 |
| 4 | Cost dashboard (SQL view + panel + drilldown) | ~15-17h | Items 1 + 2 + criterion-2 dashboard | 2-3 |

**Total effort for criterion 4 completion: ~35-42 hours.**
**Total PR count: 7-8.**

The critical path is Item 1 → Item 2 → Item 4 (attribution must exist before the dashboard reads it). Item 3 (cache) is parallelisable with the attribution items; 3a in particular ships in the time it takes to write it (no code).

---

## Out of scope for this doc (surfaced for downstream prioritisation)

1. **Tenant-facing billing/invoicing.** Cost-attribution data drives an internal dashboard for V1. Whether the customer sees per-tenant spend in their own UI (and at what tier) is a separate product decision, not engineering scope here.
2. **Cost alerting / threshold breaches.** A "Solo tenant exceeded 50k tokens this week — notify" path. Pre-revenue; ship after the dashboard makes the data visible.
3. **Per-customer LLM-budget enforcement (hard cap).** The MCP server could deny calls past a tenant's allocated budget. V2-grade product feature; the V1 metering substrate makes it possible, but enforcement is a separate gate.
4. **Cost regression CI gate.** "Did this PR raise cost-per-recall by >10%?" type checks. Useful but post-V1; requires a stable baseline that needs ~3 months of attribution data to compute.

These four belong on the post-V1 follow-up roadmap, not in the criterion-four completion scope.
