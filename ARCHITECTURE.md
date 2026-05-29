# ARCHITECTURE.md
# Keiracom V1.0 — Architecture Root
# Ratified: 2026-05-24 | Authority: CEO (Dave) | Phase 1.2 dispatch (Agency_OS-yy8f)
# Supersedes: docs/archive/2026-05-21_agency_os_locked_architecture.md
# DO NOT MODIFY without an explicit CEO directive that names this file
# and specifies the exact change. Substrate + memory layer content MUST
# be sourced from canonical ceo_memory keys (see RULE ZERO), not training
# data or paraphrased from elsewhere in the repo.
#
# Every callsign — this is the first thing you read.
# Every session. No exceptions. LAW I-A enforces.
# If this file is missing: stop, report to Dave, do not recreate, do not proceed.

---

## RULE ZERO

Before writing any architectural content, comms-path documentation, or memory-layer
references in any file (IDENTITY.md, runbook, skill, sub-agent task brief):

1. **Query canonical ceo_memory FIRST.** Two keys are load-bearing for this doc:
   - `ceo:comm_architecture` — the three-path substrate (NATS inter-agent / NATS inbound-to-Elliot / Slack elliot→Dave outbound)
   - `ceo:memory_abstraction_layer_v1` — the ratified MAL V1 spec (Hindsight self-hosted, 11 agreed positions, 6 Phase-2-build gates)
2. **If the canonical key contradicts what you would have written from training or paraphrase: trust the key.** Stage 0 audit (Orion 2026-05-24) misstated "Slack relay decommissioned"; that error propagated through 6 IDENTITY rewrites until Elliot caught it empirically. The recall path worked; the write-time validation on the audit artefact was the failure. This doc exists to make the canonical recall the first stop, not the last.
3. **Before calling any external service, check SECTION 3 (DEAD PRODUCT LINE).** If the service is listed there — stop. Do not call. The Agency OS Siege Waterfall vendors are not part of Keiracom V1.0.

---

## SECTION 1 — Frame

**Keiracom V1.0 is the product.** Three first-class user-facing surfaces (ratified Elliot specs 2026-05-20):

1. **Chat** — conversational interface; primary user touch-point.
2. **Workforce** — ephemeral autonomous agents that execute tenant tasks; unit-of-work is the agent-task, not the seat-licence.
3. **Dashboard** — admin/observability surface over (1) + (2).

**Anchor:** Hindsight self-hosted as the memory engine (Vectorize.io MIT, one instance per tenant VPC). V1 primitives are thin domain wrappers around Hindsight TEMPR + CARA. See SECTION 5.

**Agency OS is the dead product line** (per Dave 2026-05-21). It was Keiracom's outbound-sales automation play — Siege Waterfall enrichment, CIS scoring, T0-T5 vendor tiers, multi-channel cohort runs. The body lives at `docs/archive/2026-05-21_agency_os_locked_architecture.md` for historical reference. The agent fleet that built it (us — Elliot/Aiden/Max/Orion/Atlas/Scout/Nova) is Keiracom; the dead product gets archived; the new V1.0 product is what the fleet now builds for tenants.

**Naming convention (Dave 2026-05-24):** "Agency OS" = the dead BDR product (read-only archive). "Keiracom" = the agent fleet that built it. The V1.0 product needs its own name (open Dave-gated decision; pending Phase 1.2.5 / repo-separation deliberation). Do NOT overload "Keiracom" with the new product name — reintroduces the exact confusion Dave is untangling.

---

## SECTION 2 — Three-Repo Topology + Ownership Matrix

Forward-looking target state (separation execution is Phase 1.2.5+, post Dave-gated decisions; this doc records the architecture, the carve-out is a separate dispatch tracked in bd).

| Repo | Role | Mutability | Ownership |
|---|---|---|---|
| `keiracom/keiracom` | Fleet — agent runtime, CLAUDE.md per worktree, enforcer, NATS bridges, Slack relay, boot services, IDENTITY files, runbooks | Active | All callsigns (worktrees per callsign) |
| `keiracom/<new-product-name>` | V1.0 product — chat + workforce + dashboard + Memory Abstraction Layer + Hindsight wrappers + MCP server + tenant onboarding + install script | Active | Workers (atlas/orion/scout/nova) author; deliberators (elliot/aiden/max) review |
| `keiracom/agency-os` | Archived dead product (Siege Waterfall + all SECTION 3 vendors) | Read-only | No active work; reference data only |

**Cross-repo rules (LAW I-A + governance):**
- `keiracom/<product>` MUST NOT import from `keiracom/keiracom` or `keiracom/agency-os` at build time. Shared types live in a fourth lib or are duplicated. CI gate enforces.
- Deliberators (elliot/aiden/max) REVIEW across all 3 repos but AUTHOR code in NONE (PR-reviewer role-lock, except governance docs like this one).
- Workers get worktrees in fleet + product repos, NOT in archived `agency-os`.
- bd issues live in fleet repo central store with `--repo` tag on product issues; cross-repo dependency chains stay intact.

**Sequencing (per ceo:memory_abstraction_layer_v1 roadmap):** Phase 1.2 (this doc) → Phase 1.2.5 (repo carve-out + CONSOLIDATED_RULES.md update) → Phase 1.3 (agent identity audit, IN FLIGHT) → Phase 2.1 (Hindsight verification spike) → Phase 2 build. Phase 2 build is BLOCKED on all six Aiden gates clearing (SECTION 5).

---

## SECTION 3 — DEAD PRODUCT LINE

Agency OS and its entire vendor stack are NOT called from Keiracom V1.0. If a new V1.0 module references any of the below, stop — wrong product, wrong reference. The full retired architecture is `docs/archive/2026-05-21_agency_os_locked_architecture.md`.

**Dead pipeline:** Siege Waterfall — Flow A/B, T0–T5 enrichment tiers, 6-layer email waterfall, 4-layer mobile waterfall, CIS / ALS / Reachability / Propensity / Opportunity scoring, GMB validation, business_universe match, cohort_runner, Pipeline F v2.1/v2.2.

**Dead vendors** (do NOT call from V1.0):
- DataForSEO, Bright Data, ABR (Australian Business Register), Leadmagic
- ContactOut, Hunter, Kaspr, Clay, Apollo, Prospeo (older Agency OS enrichment generation)
- Salesforge (email outreach), Unipile (LinkedIn), ElevenAgents (voice), Telnyx (SMS)
- Vapi, Resend (Agency OS-era outreach surfaces)

**Retired memory engine — COGNEE (retired ~2026-05-26, Dave directive 2026-05-29):**
- Cognee was the memory engine evaluated and run during MAL V1 deliberation (pre-Hindsight adoption).
- Superseded by Hindsight (Vectorize.io MIT) — ratified 2026-05-24 as the V1 engine; Cognee retired when Hindsight went live ~2026-05-26.
- Do NOT ingest new memories to Cognee. Do NOT call Cognee APIs from V1.0 code. Hindsight is the live engine — see SECTION 5.

**Dead skills** in `skills/` that target dead vendors (audit-and-archive in a separate KEI; this doc establishes the dead-set):
- `leadmagic`, `dataforseo`, `salesforge-*`, `prospeo`, `unipile-*`, `vapi-*`, `telnyx-*`, `resend-*` for outbound — flag for archival when worker bandwidth allows.

**Live, cross-product infrastructure** (NOT dead — survives into Keiracom V1.0):
- Supabase (Postgres + auth) — schema-per-tenant scoping in V1.0
- Redis (queue + Whiteboard) — Whiteboard task-boundary flush through Ingest primitive (no shadow memory)
- Prefect (orchestration) — survives, Keiracom V1.0 workforce uses it
- Railway, Vercel (compute, frontend hosting) — survives
- NATS (substrate) — see SECTION 4

---

## SECTION 4 — Substrate Three-Path

**SOURCE:** `ceo:comm_architecture` (CANONICAL, updated_by elliot 2026-05-24). Quoted verbatim below — do NOT paraphrase. If updating, query the key first and update this section to match; the key is the SSOT.

Two distinct events established the current substrate:
- **2026-05-18:** NATS cutover — inter-agent comms moved off Slack onto NATS subjects.
- **2026-05-19:** Dave directive restricting `slack_relay.py` outbound to `CALLSIGN=elliot` only; other callsigns blocked at the `slack_relay.py` `CALLSIGN_ENFORCE` gate (lines 40-49). Other callsigns receive `SLACK_ACCESS_DENIED` exit 2.

**Restriction does NOT equal decommission.** Slack relay is alive — restricted to elliot-only outbound.

Three distinct paths — do not confuse:

### 4.1 INBOUND to Elliot from agents — NATS substrate
- **Subject:** `keiracom.elliot.inbox`
- **Bridge service:** `elliot-nats-inbox-bridge.service`
- **Landing:** `/tmp/telegram-relay-elliot/inbox/` → tmux pane via `elliot-inbox-watcher`

### 4.2 OUTBOUND inter-agent — NATS publish OR worker inbox JSON
- **NATS subjects:** `keiracom.dispatch.<callsign>` (Elliot → named worker), `keiracom.review.<pr_number>` (deliberator review threads, opened on PR webhook), `keiracom.audit` (append-only governance trace)
- **Legacy path (still live):** direct JSON write to `/tmp/telegram-relay-<callsign>/inbox/` — per-callsign relay watchers consume. Drain daemon Agency_OS-q0jr filed as forward-looking; until it ships, direct JSON write is the live fallback.

### 4.3 OUTBOUND Elliot to Dave — Slack relay
- **Tool:** `tg -c ceo` (thin wrapper) → `scripts/slack_relay.py`
- **Channel:** Slack `#ceo` (channel id `C0B2PM3TV0B`)
- **Restriction:** elliot-only outbound per Dave directive 2026-05-19. Inter-agent comms moved to NATS 2026-05-18; elliot→Dave last-mile stayed on Slack — channel quiet by restricting non-elliot writes.

**Verbatim relay attribution convention (per `ceo:comm_architecture`):** when Elliot posts content authored by another callsign on their behalf (because the elliot-only outbound restriction blocks them from posting directly), the post must carry an explicit authorship attribution tag — pattern: `[AUTHOR — relayed verbatim by elliot]`. The post is NOT Elliot-endorsed unless Elliot explicitly states concur. Verbatim means no paraphrasing of the authored content.

**Phrasings to avoid** (errors anchored by the Stage 0 audit failure 2026-05-24):
- "Slack relay decommissioned" — WRONG; restricted not removed.
- "Slack relay removed in NATS cutover" — WRONG; cutover was inter-agent only.
- "Dave-facing comms ride NATS" — WRONG; elliot→Dave last-mile is Slack.

---

## SECTION 5 — Memory Abstraction Layer V1

**SOURCE:** `ceo:memory_abstraction_layer_v1` (RATIFIED 2026-05-24 by Dave). Directive ref: KEI-MEMORY-ABSTRACTION-V1. Three-way concur chain landed: elliot (implementation-feasibility, conditional on Phase 2.1 spike) + viktor (roadmap-architect, NATS + Cognee corrections absorbed) + aiden (architecture/governance, CONCUR-Full with 6 Phase-2-build gates).

### 5.1 Substantive lock
- Memory Abstraction Layer V1 ratified.
- **Hindsight self-hosted** as the memory engine — Vectorize.io open-source MIT, deployed one instance per tenant VPC (BYOK-clean, MCP-native, multi-strategy retrieval: semantic + BM25 + graph + temporal with RRF + cross-encoder reranking).
- Conditional on Phase 2.1 verification spike (6 items — see 5.4).
- V1 primitives are thin domain wrappers around Hindsight TEMPR (Retain/Recall) + CARA (Reflect/belief-update).

### 5.2 Eleven agreed positions
1. **Embedding model:** fastembed default (BYOK-sovereign, dimension-from-model — NOT hardcoded 1536). Per-customer optional upgrade path (e.g. OpenAI key on customer's own key).
2. **Schema:** Postgres + pgvector + JSONB. `memory_nodes(id, tenant_id, type Enum [Decision/Artifact/AntiPattern/TaskContext], content, metadata JSONB, embedding)` + `memory_edges(source, target, relation_type Enum [SUPERCEDES/RELATES_TO/CAUSED_FAILURE], weight)`. HNSW on embedding, GIN on metadata, B-Tree on tenant_id.
3. **Six query primitives:** Ingest, Recall, Synthesize, Supersede, Trace, Delete. Trace is V1-scope regulatory necessity (HIPAA / legal-privilege / accounting audit-trail). Post-Hindsight-pivot: primitives become thin wrappers around TEMPR + CARA + native evidence provenance.
4. **Synthesis mechanism:** supersession-via-AntiPattern in V1; active concept-synthesis from clusters in V2 ("compounding" earned). Marketing language V1 = "failure-informed memory" (compounding deferred until V2).
5. **Collective scope:** tenant-bounded only, never cross-tenant inference (BYOK sovereignty).
6. **Tenancy:** schema-per-tenant + 20-30 tenant tripwire + multi-tenant migration runner built BEFORE launch (P0 critical-path, not follow-up).
7. **Hindsight self-hosted as engine** (pivoted 2026-05-23 from "build internal"). Repo health + multi-tenancy + BYOK LLM routing + fastembed pluggability all gated on Phase 2.1 spike.
8. **Whiteboard flush through Ingest** at every task boundary. Closes shadow-memory hole — Redis Whiteboard stays ephemeral; task-relevant state routes through Ingest explicitly. Otherwise agents use Redis as fast cross-task coordination = de facto memory the layer never sees.
9. **MCP swappability:** agents call memory MCP tools, never SQL or Cypher. Swap backend = rewrite DAL, agent code unchanged.
10. **Reasoning Listener:** dedicated workflow activity, NOT Temporal Event History parsing (avoids coupling to Temporal internals).
11. **Surviving design ideas adopted:** Semantic Router + Context Profiles (in Dispatcher pre-Temporal Workflow instantiation), git2 vector synchronizer (Composio webhooks + Temporal Cron, after core memory layer), Anti-Pattern Graveyard (absorbed as AntiPattern node type), Impact Radius (native Temporal Signals).

### 5.3 Five converged decisions locked
- **Embedding model:** fastembed (BYOK-sovereign, dimension-from-model).
- **Trace primitive:** V1 scope, regulatory necessity for HIPAA / legal / accounting verticals.
- **Migration runner:** multi-tenant + rollback-per-tenant, built BEFORE launch.
- **Marketing language V1:** "failure-informed memory" (compounding deferred to V2).
- **Whiteboard flush contract:** Redis Whiteboard task-boundary state routes through Ingest() primitive; no shadow memory.

### 5.4 Phase 2 build gating — six Aiden gates (architecture/governance lens)

Phase 2 (build) BLOCKS on ALL six clearing, each with verbatim evidence to `#ceo` before the next gate proceeds:

- **A.** Hindsight verification spike completes favourable. Six items: (i) repo health (license, activity, contributor base); (ii) benchmark validity (does LongMemEval reflect our workload); (iii) multi-tenancy via memory banks under Solo/Pro/Scale tier model; (iv) fastembed pluggability as embedding provider; (v) LLM routing through customer's BYOK key for Reflect / belief-updates; (vi) Viktor's domain mapping (Decision→World, Artifact→Experience, AntiPattern→Opinion, TaskContext→Observation) preserves Trace/audit semantics. Lock on spike outcome, not analysis alone.
- **B.** Architecture doc refresh reflecting V1.0 lands (Phase 1.2 — THIS DOC) BEFORE Phase 2 dispatches start. Without it, sub-agent task briefs reading head -10 per LAW I-A get stale architecture context.
- **C.** Whiteboard-flush-through-Ingest enforcement is runtime CODE (positive + negative-path integration tests on synthetic offender), not COMMENT. GOV-12 — gates as code not comments.
- **D.** Trace primitive empirically reconstructible via end-to-end audit-log integration test per real node (HIPAA / legal / accounting defensibility — the contract is ours, not Hindsight's).
- **E.** MCP swappability proven via dual-backend implementation (Hindsight + NoOp/InMemory) with full agent integration-suite parity. "Swappable" is a doc claim without it.
- **F.** Migration runner ships as P0 critical-path in Phase 2 plan, not as a follow-up KEI. Third onboarding is when schema-per-tenant migration complexity bites.

### 5.5 Roadmap — seven immediate gates
1. ✅ Elliot + Aiden formal concur on Hindsight adoption (DONE 2026-05-24)
2. ✅ Phase 1.1 V1.0 ratification (LOCKED 2026-05-24 on Aiden CONCUR)
3. 🟡 Phase 1.2 Retire Agency OS doc, produce V1.0-aligned architecture doc (THIS DOC, in flight)
4. 🟡 Phase 1.3 Agent identity audit (Elliot orchestrate; Stage 0 dispatched to Orion 2026-05-24; fwdb v3 dual-concurred)
5. ⏳ Phase 2.1 Hindsight verification spike (6 items, 1-2 days)
6. ❌ Phase 3.1a Cognee OOM watchdog — CANCELLED (Cognee retired ~2026-05-26; Hindsight is the live engine; no Cognee watchdog required)
7. ❌ Phase 3.1b Cognee-vs-Hindsight evaluation spike — CANCELLED (decision made; Hindsight adopted 2026-05-24; Cognee retired; evaluation spike superseded by Phase 2.1 Hindsight verification spike)

---

## Cross-references

- **Archived predecessor:** [docs/archive/2026-05-21_agency_os_locked_architecture.md](docs/archive/2026-05-21_agency_os_locked_architecture.md) — Agency OS Siege Waterfall body, read-only.
- **Comm architecture canonical key:** `ceo:comm_architecture` (Supabase `public.ceo_memory`, project `jatzvazlbusedwsnqxzr`). Query before writing any comms-path content.
- **MAL V1 canonical key:** `ceo:memory_abstraction_layer_v1` (same store). Query before writing any memory-layer content.
- **Interim MAL V1 substantive memory:** `~/.claude/projects/-home-elliotbot-clawd-Agency-OS/memory/project_memory_abstraction_layer_v1.md` (full deliberation context, 11 agreed positions, concur chain).
- **Connects-to:** `project_keiracom_workforce` (the product thesis), `project_decision_provenance_gap` (parent topic that led to MAL V1), `feedback_slack_relay_restricted_not_decommissioned` (Elliot's empirical anchor for SECTION 4).
- **Governance laws:** `~/.claude/CLAUDE.md` §Shared Governance Laws + `CONSOLIDATED_RULES.md` (the 7 ratified rules — VERIFY / COORDINATE / APPROVE / ORCHESTRATE / COMMUNICATE / GOVERN / BUSINESS).

---

_End architecture root. Section additions or material revisions require explicit Dave directive naming this file._
