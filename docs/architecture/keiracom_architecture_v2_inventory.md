# Keiracom Architecture V2.0 — Phase 1 Inventory

**Directive:** KEI-ARCHITECTURE-V2-UNIFIED-LOCK (Dave 2026-05-25 ts ~1779704000)
**Phase:** 1 (Inventory + Status; 24-48hr deadline)
**Co-leads:** Elliot (impl-feasibility) + Aiden (architecture/governance)
**Contributors:** Viktor (roadmap-architect), Atlas (engineering), Orion (engineering), Max (quality)
**Status:** WORKING DRAFT — populated from Viktor 24-item contribution + Aiden 25-item anchored + Elliot operational status checks; OPEN for additions

---

## Schema (per Aiden §1)

| Column | Meaning |
|---|---|
| `element_id` | Stable slug (e.g. `mem.topology`) |
| `category` | memory \| cost \| persona \| customer-product \| governance \| infra \| commercial |
| `status` | RATIFIED-CEO \| RATIFIED-DM \| PROPOSED \| LOOSE \| DEFERRED \| GAP |
| `source` | ceo_memory_key \| PR# \| repo_path \| dispatch_ts \| `[DM-CLAIMED]` \| `[GAP]` |
| `owner` | Deliberator/worker callsign for Phase 2 |
| `depends_on` | List of element_id this depends on |
| `customer_visible` | install \| dashboard \| chat \| email \| onboarding \| pricing \| nothing |
| `phase_tag` | V1-launch \| V1.1 \| V2 \| Phase-3.x-deferred |

---

## Category 1 — Memory Architecture (owner: Aiden)

| ID | Element | Status | Source | Customer-visible | Phase |
|---|---|---|---|---|---|
| mem.engine | Hindsight self-hosted as engine | RATIFIED-CEO | ceo:memory_abstraction_layer_v1 substantive_lock | nothing | V1-launch |
| mem.topology | Tier-keyed topology: Solo/Pro=schema-per-tenant Topology B; Scale=per-tenant VPC Topology A | RATIFIED-CEO | substantive_lock item 2; PR #1126 | nothing (visible as tier-feature) | V1-launch |
| mem.primitives | Six query primitives: Ingest/Recall/Synthesize/Supersede/Trace/Delete | RATIFIED-CEO | eleven_agreed_positions #3 | nothing | V1-launch |
| mem.tempr_cara | TEMPR (Temporal/Experiential/Mental-Model/Procedural) + CARA (Reflect/belief-update on top) | RATIFIED-CEO | substantive_lock item 4 (Viktor verbatim 2026-05-25); CONFLICT with Aiden's outline expansion to resolve | nothing | V1-launch |
| mem.schema | memory_nodes + memory_edges with HNSW + GIN + B-Tree indexes | RATIFIED-CEO | eleven_agreed_positions #2 | nothing | V1-launch |
| mem.embedding | BGE-small-en-v1.5 via TEI sidecar (Path 3 V1; Path 1 native fastembed deferred upstream) | RATIFIED-CEO | eleven_agreed_positions #1; PR #1127/#1133 | nothing | V1-launch |
| mem.byok | BYOK sovereignty — tenant-bounded only, never cross-tenant inference | RATIFIED-CEO | eleven_agreed_positions #5 | install/onboarding (key field) | V1-launch |
| mem.tenancy_tripwire | schema-per-tenant + 20-30 tripwire + migration runner pre-launch | RATIFIED-CEO | eleven_agreed_positions #6 | nothing | V1-launch |
| mem.whiteboard | Whiteboard flush through Ingest at every task boundary | RATIFIED-CEO | eleven_agreed_positions #8 | nothing | V1-launch |
| mem.mcp_swap | MCP swappability: agents call memory MCP tools, never SQL/Cypher | RATIFIED-CEO | eleven_agreed_positions #9; PR #1136 Gate E proof | nothing | V1-launch |
| mem.reasoning_listener | Reasoning Listener as Temporal workflow activity | RATIFIED-CEO | eleven_agreed_positions #10 | nothing | V1-launch |
| mem.synthesis | Supersession-via-AntiPattern V1; active concept-synthesis V2 | RATIFIED-CEO | eleven_agreed_positions #4 | nothing | V1-launch |
| mem.cognee_retired | Cognee retired (cold-start, snapshot preserved) | RATIFIED-CEO | PR #1143 (2026-05-25) | nothing | V1-launch |
| mem.llamaindex_pinned | LlamaIndex pinned; retire during cutover step 5-B | RATIFIED-CEO | PR #1142 (2026-05-25) | nothing | V1-launch |
| mem.weaviate_coldstart | Weaviate cold-start; 7 pipeline-fed classes re-ingest + 3 hand-migration (Sessions, Global_governance_patterns, Discoveries). **A3 addendum 2026-05-25 (Elliot operational call):** empirically Weaviate live state is byte-identical to snapshot per snapshot README verification chain; the cold-start framing was prescriptive about HOW to reach the destination state, not structural about WHAT state. Cold-start ops skipped — live Weaviate already represents the post-cutover target. Net new A3 work: criterion 1 (re-point indexers to Hindsight) + criterion 4 (LlamaIndex retirement). | RATIFIED-CEO | PR #1141 (Aiden + Max audit 2026-05-25) + A3 empirical-state addendum (Atlas + Elliot 2026-05-25) | nothing | V1-launch |
| mem.snapshot_archive | Pre-Hindsight memory snapshot 2.1GB chmod 444 at /backups/memory_pre_hindsight_migration_20260525/ | RATIFIED-CEO | Orion snapshot complete 2026-05-25 ts 1779687930 | nothing | V1-launch (audit-only) |

## Category 2 — Memory Wrappers (owner: Atlas; Aiden reviews)

| ID | Element | Status | Source | Customer-visible | Phase |
|---|---|---|---|---|---|
| mem.wrap.decision | Decision wrapper → Hindsight World (direct) | RATIFIED-CEO | PR #1134 src/keiracom_system/memory/wrappers/decision_wrapper.py | nothing | V1-launch |
| mem.wrap.artifact | Artifact wrapper → Hindsight Experience (direct) | RATIFIED-CEO | PR #1134 | nothing | V1-launch |
| mem.wrap.taskcontext | TaskContext wrapper → Hindsight Observation (direct) | RATIFIED-CEO | PR #1134 | nothing | V1-launch |
| mem.wrap.antipattern | AntiPattern wrapper → Hindsight Opinion with entity_label + supersession edge | RATIFIED-CEO | PR #1134 | nothing | V1-launch |
| mem.wrap.trace | Trace composition: OTel + tenant log + Reflect citations → audit-trail shape (HIPAA/legal/accounting) | RATIFIED-CEO | PR #1134 trace_composition.py + Aiden Gate D | dashboard (audit view) | V1-launch |
| mem.wrap.bank_id | get_bank_id(tenant_id) → tenant_id (V1 identity mapping) | RATIFIED-CEO | PR #1135 hotfix | nothing | V1-launch |
| mem.wrap.contract | Wrapper interface contract documentation | LOOSE | not yet documented; Phase 2 lock item | nothing | V1-launch |

## Category 3 — Hindsight Engine Integration (joint: Atlas + Aiden)

| ID | Element | Status | Source | Customer-visible | Phase |
|---|---|---|---|---|---|
| hind.spike_verdict | Phase 2.1 spike FAVOURABLE; 6 items closed | RATIFIED-CEO | phase_2_1_spike_verdict | nothing | V1-launch |
| hind.gates_a_to_f | Aiden 6 Phase-2-build gates (A-F); B closes on this V2.0 inventory landing | RATIFIED-CEO | aiden_six_phase_2_build_gates | nothing | V1-launch |
| hind.smoke_engine_fit | Pre-build smoke verdict: ENGINE FIT, methodology gap (G3 rubric refinement deferred to first-customer-checkpoint) | RATIFIED-CEO | PR #1130 | nothing | V1-launch |
| hind.fleet_deploy | Fleet-side Hindsight instance + wired wrappers + fleet tenant in control-plane | LOOSE | step 4a HOLDING until V2.0 publishes per directive constraint | nothing | V1-launch |
| hind.cara_citation | CARA citation reconciliation — closed | RATIFIED-CEO | Viktor verbatim 2026-05-25; substantive_lock item 4 | nothing | V1-launch |

## Category 4 — Cost / Metering / Cache (owner: Elliot + Atlas)

| ID | Element | Status | Source | Customer-visible | Phase |
|---|---|---|---|---|---|
| cost.metering_pipeline | Log-based per-tenant LLM metering pipeline (V1 captures token-counts only; cost $AUD translation deferred to P3) | RATIFIED-CEO | PR #1137 | dashboard (token-counts only V1; $AUD when P3 ships) | V1-launch |
| cost.metering.production_wiring | psycopg-backed PostgresDBAdapter + from_env() factory + Prefect daily rollup deployment | LOOSE (P1 Orion follow-up) | PR #1137 §follow-ups | nothing | V1-launch |
| cost.metering.log_shipper_config | Vector or Filebeat tailing Hindsight container logs → metering service stdin | LOOSE (P2 Orion follow-up) | PR #1137 §follow-ups | nothing | V1-launch |
| cost.metering.provider_billing_api | Per-model-per-tenant $AUD cost translation via OpenAI/Anthropic billing API — upgrades dashboard from token-counts to true $AUD | DEFERRED (P3 post-first-paying-customer per Dave ratify on PR #1128 §5) | PR #1128 §5 + PR #1137 §follow-ups | dashboard ($AUD activation) | V1.1 or V2 |
| cost.attribution_wrappers | Cost-attribution wrappers around 6 MAL primitives | LOOSE | #1139 scoping; pending build | nothing | V1-launch |
| cost.governance_attribution | Governance-decision cost-attribution (PR-review + canonical-key query + audit-dispatch) | LOOSE | #1139 scoping | dashboard | V1-launch |
| cost.cache_discipline | Cache-pattern enforcement (triple-option A discipline-doc + B runtime-warn + C PR-linter) — SHIFTING to Temporal interception layer per ratify 2026-05-25 | RATIFIED-CEO (placement); LOOSE (implementation) | #1139 + temporal_interception_layer | nothing | V1-launch |
| cost.dashboard | Cost dashboard (admin-dashboard panel, not standalone) per-tenant + per-callsign + per-agent-role | LOOSE | #1139 scoping | dashboard | V1-launch |
| cost.semantic_cache_valkey | Semantic caching via Valkey vector-similarity (not standard KV) | RATIFIED-DM | Viktor verbatim 2026-05-25; V1.0 spec ts 1779500195; Valkey running today | nothing | V1-launch |
| cost.token_budget | Token budget mechanism — per-call cap + tier-scaled pool + dispatcher-enforced + model-cost-calibrated | LOOSE | Viktor 4-component proposal; sub-deliberation per directive | onboarding (tier limits) | V1-launch |

**Depends-on edges added per Orion review:**
- `cost.metering_pipeline` → `tenant.control_plane` (FK keiracom_tenant_metering.tenant_id REFERENCES keiracom_tenants ON DELETE CASCADE; Atlas PR #1131)
- `cost.metering_pipeline` → `mem.engine` (Hindsight emits the JSON log lines metering reads; log_reader.py DEFAULT_FIELD_MAP matches documented Hindsight schema)

## Category 5 — Temporal Interception Layer + Governance (owner: Elliot)

| ID | Element | Status | Source | Customer-visible | Phase |
|---|---|---|---|---|---|
| temp.middleware | Temporal middleware between chat input and LLM token call (single chokepoint) | RATIFIED-CEO | temporal_interception_layer 2026-05-25 (Elliot+Aiden concur) | nothing | V1-launch |
| temp.inline.listener | Reasoning Listener (capture why behind decisions) — INLINE | RATIFIED-CEO | temporal_interception_layer | nothing | V1-launch |
| temp.inline.token_gate | Token spend gates — INLINE | RATIFIED-CEO | temporal_interception_layer | nothing | V1-launch |
| temp.inline.cache_check | Cache discipline checks — INLINE | RATIFIED-CEO | temporal_interception_layer | nothing | V1-launch |
| temp.inline.tier_gate | Tier feature gating — INLINE | RATIFIED-CEO | temporal_interception_layer | nothing | V1-launch |
| temp.inline.audit | Audit trail emission — INLINE | RATIFIED-CEO | temporal_interception_layer | dashboard | V1-launch |
| temp.inline.content_check | Pre-call content checks (privacy/regulated) — INLINE | RATIFIED-CEO | temporal_interception_layer | nothing | V1-launch |
| temp.async.post_validation | Post-call validation (response shape + citation validity) — ASYNC continuation | RATIFIED-CEO | temporal_interception_layer (Aiden refinement) | nothing | V1-launch |
| temp.contract_doc | One-page contract definition (emit guarantees + enforce-vs-warn semantics per gate) — ELLIOT OWES BEFORE BUILD | LOOSE | temporal_interception_layer open_action_elliot_owns | nothing | V1-launch (BLOCKER for build) |
| temp.dispatcher | Temporal as workflow execution engine for dispatcher (replaces NATS-loop/tmux-pane-injection) | RATIFIED-CEO | v1_completion_criteria criterion 1; ephemeral scoping PR #1140 | nothing | V1-launch |

## Category 6 — NATS Substrate + Comms (owner: Elliot)

| ID | Element | Status | Source | Customer-visible | Phase |
|---|---|---|---|---|---|
| nats.fleet_inter_agent | NATS JetStream subjects for fleet inter-agent (inbox/review/audit) — running today | RATIFIED-CEO | ceo:comm_architecture | nothing | running |
| nats.viktor_position | NATS retained as inter-agent messaging fabric (Viktor pushed against V1.0-spec removal; Temporal + NATS coexist with different roles) | RATIFIED-CEO | Viktor verbatim 2026-05-25; viktor_nats_position_verbatim in canonical | nothing | V1-launch |
| nats.customer_topology | Per-tenant isolated NATS deployment vs shared (Viktor's position: isolated — subject leakage + noisy-neighbour + retention) | LOOSE | Viktor proposal; Phase 2 sub-deliberation | nothing | V1-launch |
| nats.cross_tenant_aggregation | Cross-tenant aggregation for governance audit-trail roll-up via separate layer (not cross-tenant NATS access) | LOOSE | Viktor proposal | dashboard (admin support view) | V1-launch |
| comms.slack_relay | Slack relay restricted to elliot-only outbound (2026-05-19 directive) | RATIFIED-CEO | ceo:comm_architecture | nothing | running |

## Category 7 — Ephemeral Agent System (owner: Aiden)

| ID | Element | Status | Source | Customer-visible | Phase |
|---|---|---|---|---|---|
| eph.scoping | 8 tmux-coupled subsystems enumerated; 5-stage migration; spawn-with-context pattern | RATIFIED-CEO | PR #1140 | nothing | V1-launch |
| eph.paused_tasks | paused_tasks Postgres table with 7-day TTL + dead-letter to Elliot | RATIFIED-CEO | PR #1140 | nothing | V1-launch |
| eph.docker_container | Isolated Docker container per tenant per task (Vultr-hosted) | RATIFIED-DM | Aiden DM provenance | nothing | V1-launch |
| eph.implementation_keis | 7 engineer-tier implementation KEIs from PR #1140 §7 | LOOSE | PR #1140 §7 | nothing | V1-launch |

## Category 8 — Three-Repo Topology (owner: Aiden + Elliot)

| ID | Element | Status | Source | Customer-visible | Phase |
|---|---|---|---|---|---|
| repo.fleet | keiracom-fleet repo (internal agent runtime) | RATIFIED-CEO | ceo:agency_os_keiracom_separation_v1 | nothing | V1-launch |
| repo.product | keiracom-system repo (V1.0 customer product; name locked 2026-05-24) | RATIFIED-CEO | product_name_lock in canonical | nothing | V1-launch |
| repo.archive | agency-os repo (read-only archive; URL preserved) | RATIFIED-CEO | separation directive (Dave 2026-05-25) | nothing | V1-launch |
| repo.carveout_doc | Three-repo carve-out execution plan with file-by-file ownership matrix | RATIFIED-CEO | PR #1122 docs/architecture/three_repo_carveout_execution.md | nothing | V1-launch |
| repo.cross_import_gate | No platform→fleet imports CI gate | LOOSE | repo.carveout_doc; Phase 2.0 build item | nothing | V1-launch |
| repo.fair_source | Fair-Source license at launch (LICENSE + README header + CLA + commit hygiene) — currently 0 of 4 implemented | GAP | none in repo today | install (legal/compliance) | V1-launch |

## Category 9 — Multi-Tenancy + Tenant Isolation (owner: Atlas + Aiden)

| ID | Element | Status | Source | Customer-visible | Phase |
|---|---|---|---|---|---|
| tenant.table | Control-plane tenants Postgres table + provisioning + deprovisioning | RATIFIED-CEO | PR #1131 | dashboard (admin) | V1-launch |
| tenant.extension | KeiracomTenantExtension (per-request config lookup + field-level permission gate) | RATIFIED-CEO | PR #1132 | nothing | V1-launch |
| tenant.mcp_tier_router | Tier-aware MCP server (Gate E proof) | RATIFIED-CEO | PR #1136 | chat/dashboard (tier limits) | V1-launch |
| tenant.routing_implementation | Connection routing for schema-per-tenant (Solo/Pro) vs per-VPC (Scale) — implementation detail | LOOSE | Phase 2 build item; Viktor noted | nothing | V1-launch |
| tenant.single_supabase | One Supabase + one dashboard; Dave is tenant_id=1; customers are tenant_id=2+ | RATIFIED-DM | Aiden Phase 1 §3.A item 21 + 23 + Atlas PR #1126 | dashboard | V1-launch |

## Category 10 — MCP Tool Access (owner: Atlas + Orion)

| ID | Element | Status | Source | Customer-visible | Phase |
|---|---|---|---|---|---|
| mcp.abstraction | All tools exposed via MCP servers; tools/list resolves per-tenant allowed set | RATIFIED-CEO | PR #1136 + canonical | chat (tool-driven UX) | V1-launch |
| mcp.composio | Composio as integration library beneath MCP (implementation choice; not architectural constraint) | RATIFIED-DM | Viktor verbatim 2026-05-25 + Aiden anchor MAL §11 (git2 sync) | nothing | V1-launch |
| mcp.go_sidecar | Go sidecar — security interceptor + tool-call validator; static config not knowledge graph; mechanical enforcement | RATIFIED-DM | Viktor verbatim 2026-05-25 + Aiden Phase 1 §3.A item 7 | nothing | V1-launch (BUILD pending) |
| mcp.tei_sidecar | TEI sidecar (embedding service alongside Hindsight) — running; same model lineage as fastembed default (BAAI/bge-small-en-v1.5, 384-dim, MIT) | RATIFIED-CEO | PR #1133 | nothing | running |
| mcp.tei_path1_upstream | Upstream Hindsight PR adding native FastembedEmbeddings provider (~150-200 LoC); long-term canonical fix; Path 3 ships V1, transition is config-only swap | LOOSE (P2 Orion follow-up) | PR #1127 §6 + PR #1133 §follow-ups | nothing | V1.1 |

**Depends-on edge added per Orion review:**
- `mcp.tei_sidecar` ← `mem.engine` (Hindsight reads embeddings via HINDSIGHT_API_EMBEDDINGS_TEI_URL; TEI is the embedding provider)

## Category 11 — Governance Router (LiteLLM) + BYOK (owner: Elliot + Atlas)

| ID | Element | Status | Source | Customer-visible | Phase |
|---|---|---|---|---|---|
| gov.litellm_router | LiteLLM as governance router with BYOK key resolution — RATIFIED AND RUNNING (T0.2 audit) | RATIFIED-CEO | litellm_governance_router in canonical (Viktor 2026-05-25 surfaced) | nothing | running |
| gov.internal_gemini | Internal fleet hardcoded Gemini 2.5 Flash | RATIFIED-CEO | reference_model_routing.md | nothing | running |
| gov.customer_byok | Customer product BYOK key per tier (Anthropic Haiku, OpenAI gpt-4o-mini, Gemini Flash, Azure) | RATIFIED-DM | Viktor verbatim + Aiden Phase 1 §3.A | onboarding (key field), dashboard | V1-launch |
| gov.composio_per_customer_segregation | Composio per-customer segregation: ONE Composio account per customer (NOT shared account). Cleaner isolation, more cost, worth it. Aligned with sovereignty positioning. Resolves Aiden's HARD-GATE-WITHIN-HARD-GATE concern from Cat 16 item 2 review. HARD GATE before V1 launch | RATIFIED-CEO | Dave directive 2026-05-25 decision #3 + Aiden Cat 16 escalation | nothing | V1-launch (HARD GATE) |

## Category 12 — V1 Completion Criteria (joint: Aiden + Elliot)

| ID | Element | Status | Source | Customer-visible | Phase |
|---|---|---|---|---|---|
| crit1.ephemeral | Ephemeral agent system replaces tmux | RATIFIED-CEO | v1_completion_criteria criterion 1 | nothing | V1-launch |
| crit2.whole_system | Whole system modelled + built + wired (with Viktor coherence check) | RATIFIED-CEO | criterion 2 + viktor coherence | chat/dashboard/install (FULL customer journey) | V1-launch |
| crit3.identities | Ideal candidate identities — purpose-built not generic | RATIFIED-CEO (scope); LOOSE (definitions) | criterion 3 + Viktor framing | chat (chat agent identity) | V1-launch (BLOCKER) |
| crit4.cost_aware | Memory + governance on API token spend + cache | RATIFIED-CEO (placement); LOOSE (implementation) | criterion 4 + temporal_interception_layer | dashboard (cost panel) | V1-launch |

## Category 13 — Customer Product Surface (owner: NEEDS DECISION — likely Elliot per Dave DM-context)

| ID | Element | Status | Source | Customer-visible | Phase |
|---|---|---|---|---|---|
| cust.chat_prompt_v3 | Chat agent system prompt v3 — name=Keira; wires Viktor's 8 resolved answers + handoff transparency rule + Viktor's 6 worked examples + Dave's factual-correction example. Canonical location: /home/elliotbot/clawd/Agency_OS/keiracom_system/personas/keira/system_prompt_v3.md. Pending Dave final review before ship (LOOSE moves to RATIFIED-CEO on Dave sign-off of the assembled prompt). | LOOSE (pending Dave final review of assembled v3) | Dave authorisation 2026-05-25 ~1779742100 + Viktor 3-part + persona.chat_agent_identity ratified | chat | V1-launch |
| cust.icp_segmentation | ICP segmentation — V1.0 spec named 5 segments; Viktor recommends narrow-to-1 (technical founders/solo builders) | LOOSE (Dave CEO decision) | Viktor verbatim | onboarding/email/pricing | V1-launch |
| cust.dashboard_spec | Dashboard spec — docs/specs/AGENT_DASHBOARD_SPEC.md exists but stale (Agency OS calibration; refers to Maya/Researcher/Builder/Auditor not current fleet) | LOOSE | spec file exists; needs refresh | dashboard | V1-launch |
| cust.pricing_locked | RATIFIED pricing: Solo $79 + Pro $249 + Team $649 + Enterprise custom ($1,500+ floor) + Distributor $775 base + $15/thread wholesale. Solo locked at $79 (decision #6 — competitive positioning preserved; accepted margin compression vs $99 alternative; volume play). Enterprise rename per decision #5 | RATIFIED-CEO | Dave directive 2026-05-25 decisions #5 + #6 | pricing | V1-launch |
| cust.multi_channel_communication | Slack + WhatsApp via Composio as customer communication channels (NEW strategic direction per Dave decision #2). Customers interact with Keiracom from where they already are. Tenant isolation cross-channel (Slack workspace → tenant identity mapping). BYOK preserved (customer's Anthropic key powers LLM). Pro tier feature (matches tier-gating). Reframes product: "Keiracom is the brain; you reach it from wherever you already are." Competitive differentiator vs Viktor.com (Slack-native but managed-cloud, no BYOK) | RATIFIED-CEO | Dave directive 2026-05-25 decision #2 | chat/onboarding/dashboard (Pro tier surface) | V1-launch |
| cust.solo_governance_locked | Solo tier governance: 3 deliberators (NOT 2) — CONCUR integrity > tier pricing optimisation. Customers buy CONCUR; compromising at Solo means selling a different product at Solo. Accepted margin compression from ~70% to ~50% (decision #4) | RATIFIED-CEO | Dave directive 2026-05-25 decision #4 | nothing | V1-launch |
| cust.enterprise_tier_naming | "Enterprise" replaces "Scale" per V1.0-spec rename (decision #5). Custom pricing, requirements-based. Internal floor $1,500/mo. Range $1,500-$50,000+/mo | RATIFIED-CEO | Dave directive 2026-05-25 decision #5 | onboarding/pricing | V1-launch |
| cust.terminology_failure_informed | "Failure-informed memory" internal canonical; customer-facing language separate | LOOSE | Viktor verbatim | chat/email/pricing | V1-launch |
| cust.cognitive_software_refinery | "Cognitive Software Refinery" framing — DM-discussed but never deliberated | LOOSE | Viktor verbatim | nothing (internal only) | DEFERRED (positioning round) |
| cust.acquisition_strategy | Customer acquisition strategy + first-3-paying-customer ownership | DEFERRED-with-re-introduction-before-V2.0 | Viktor flagged absent from all roadmaps | install (acquisition surface) | V1-launch (BLOCKER) |
| cust.dispatcher_customer_side | Customer-product dispatcher (presumably ephemeral spawn-with-context same as fleet but not crisply ratified for multi-tenant) | LOOSE | Viktor flagged | nothing | V1-launch |

## Category 14 — Persona / Identity (DEFERRED Phase 3.x per Dave; Phase 1 inventory only)

| ID | Element | Status | Source | Customer-visible | Phase |
|---|---|---|---|---|---|
| persona.deliberator_complementary | Deliberators (Elliot/Aiden/Max) need COMPLIMENTARY not overlapping lenses | DEFERRED-Phase-3.x | Viktor framing 2026-05-25 + Dave operating model | nothing | Phase-3.x-deferred |
| persona.behavioral_design | Design identity that CHANGES behaviour, not "write description" | DEFERRED-Phase-3.x | Viktor framing | nothing | Phase-3.x-deferred |
| persona.chat_agent_identity | Customer-facing chat agent identity: **NAME = KEIRA**. Voice: direct + smart + helpful + curious-that-opens-conversation. Action-verb-first for task confirms ("Dispatching now" / "On it"); "I" for conversation. Praise: brief acknowledgment + redirect. Hostility: own if she erred, pivot to action; no performative apology. Humor: dry-wry only, customer sets tone first. No cultural variants V1. Per-customer adaptation: one Keira, different volumes. Voice across surfaces: same core, formality varies (chat full, dashboard terse, push verb-first). Handoff rule: "This needs X. Routing to Y. Back to you in N." Factual-correction rule: correct gently with reasoning; don't patronize; don't capitulate; pivot to underlying problem. | RATIFIED-CEO | Dave sign-off 2026-05-25 ~1779742100 + Viktor 3-part deliberation 2026-05-25 + Aiden "competent-peer" concern resolved via worked examples | chat (primary surface) | V1-launch |
| persona.runbook_refresh | Phase 1.3 identity runbooks for atlas/elliot/max/nova | LOOSE | Agency_OS-e02v (open) | nothing | V1-launch |

## Category 16 — Operability + Infrastructure Layers (owner: Aiden review/governance + engineer-tier TBD implementation)

Added per Dave directive 2026-05-25 ts ~1779708000. Items 2 and 5 explicitly tagged LOOSE-BLOCKER per Viktor's verbatim "hard gates" framing.

**Owner-attribution correction (Aiden review 2026-05-25):** Aiden's role per IDENTITY.md is deliberator/governance lens — NOT infra implementation owner. Original draft attributed implementation to "Aiden infra" without Dave-verbatim role-expansion. Corrected: each row owner is `Aiden (review/governance) + <engineer-tier TBD> (implementation)`. Implementation owner assigned in Phase 2 dispatch (likely Atlas or Orion per current engineering charters).

| ID | Element | Status | Source | Customer-visible | Phase |
|---|---|---|---|---|---|
| infra.observability | Observability + monitoring layer — Better Stack (already in fleet env vars) + per-layer /health checks. V1 scoped. Owner: Aiden (review/governance) + engineer-tier TBD (implementation). Depends on: temp.middleware (audit events flow here per inline_at_chokepoint item 5) + nats.fleet_inter_agent (NATS health observed) + mem.engine (Hindsight health observed). | LOOSE V1-required | Dave directive + Viktor 2026-05-25 + Aiden delta 2026-05-25 | dashboard (admin health view) | V1-launch |
| infra.secrets_management | Secrets management — HashiCorp Vault self-hosted on Vultr (single node V1) with Transit engine for BYOK envelope encryption. Three categories: customer BYOK keys (envelope-encrypted in Postgres, KMS-managed), internal service credentials (Vault store), Composio OAuth tokens (managed by Composio's credential store). Vault chosen over Cloud KMS for dynamic-secrets-with-rotation. Owner: Aiden (review/governance) + engineer-tier TBD (implementation) + Elliot (policy). Integration: agents call Vault at spawn; Go Sidecar validates no raw secret leaks into LLM context. Depends on: mcp.go_sidecar + tenant.table + mem.byok. Cross-cite: gov.customer_byok (BYOK key resolution sits above this substrate). **Phase 2 sub-deliberation items:** (a) Vault unseal posture (Cloud-KMS auto-unseal vs shamir-shares-on-disk vs manual); (b) Single-node SPOF mitigation (degraded-mode read from envelope-encrypted Postgres cache when Vault unreachable); (c) Vault HA tripwire (3-node cluster at what threshold — probably mem.tenancy_tripwire 20-30 tenants); (d) **HARD-GATE-WITHIN-HARD-GATE: Composio OAuth per-tenant segregation** — does Composio support per-tenant OAuth segregation, or does Keiracom share one Composio account across tenants? If shared, cross-tenant data leakage risk via Composio. V1 needs the choice named before launch. | LOOSE-BLOCKER | Dave directive + Viktor 2026-05-25 verbatim + Aiden Viktor-7 delta review 2026-05-25 | onboarding (key field), nothing else | V1-launch (HARD GATE) |
| infra.rate_limiting | Rate limiting + abuse prevention. V1 scoped: request throttling at LiteLLM governance router (per-tenant req/sec + req/day per virtual key — config task, LiteLLM native) + token spend hard-stop via Temporal middleware (already proposed). Deferred to V1.1: anomaly detection on per-tenant traffic (needs 30+ days baseline). Owner: Aiden (review/governance) + engineer-tier TBD (LiteLLM config task) + Elliot (policy). Depends on: gov.litellm_router (throttle integration) + temp.inline.token_gate (hard-stop integration) + tenant.table (per-tenant routing). | LOOSE V1-required | Dave directive + Viktor 2026-05-25 verbatim + Aiden delta 2026-05-25 | nothing | V1-launch |
| infra.cdn | CDN for customer dashboard — Cloudflare free tier. DEFERRED until ICP includes non-local customers (V1.0 builds for Australian-only or similar). Re-introduction: ICP geography expansion. Two-hour task when needed. | DEFERRED | Dave directive + Viktor 2026-05-25 deferral | dashboard (latency-felt) | V1.1 or V2 |
| infra.backup_dr | Backup + disaster recovery per tenant. **MOVED FROM V1 HARD GATE TO V1.x FEATURE per Dave directive 2026-05-25 ~1779738300:** "everything is in the backend. We can build hindsight and add backup afterwards". V1 ships with Supabase PITR Pro tier (7-day point-in-time recovery; ~$39 AUD/mo) at the database layer + multi-region cloud infrastructure failover. Per-tenant export/restore is V1.x feature, gated on upstream Hindsight pull request (M2 mitigation per Orion il34 spike). Regulated verticals (legal/health/accounting) naturally self-select to V1.x since they legally need DR. Standard V1 answer to "what happens if your servers die": "multi-region cloud + Supabase PITR; per-customer export/restore is V1.x". Owner: Aiden (review/governance) + engineer-tier TBD (implementation) for V1.x. | LOOSE (V1.x feature) | Dave directive 2026-05-25 re-frame; Viktor + Aiden HARD-GATE label SUPERSEDED | install/dashboard (V1.x onboarding will include backup step) | V1.x (post upstream PR merge) |
| infra.cicd | CI/CD pipeline — GitHub Actions (partially exists today; gap audit needed for what's missing: tests yes, deploys via Railway, rollouts via Vercel, rollbacks UNKNOWN — Phase 2 sub-item). V1 minimum: automated tests + deploys + rollouts + rollbacks. Owner: Aiden (review/governance) + engineer-tier TBD (implementation) + Elliot (release-policy). | LOOSE V1-required | Dave directive + Viktor 2026-05-25 + Aiden delta 2026-05-25 | nothing | V1-launch |
| infra.iac | Infrastructure as Code — Pulumi (Python SDK) over Terraform for V1 (keep team in single language). V1 narrow scope: tenant provisioning automation triggered by Temporal workflow (schema creation + Hindsight namespace + LiteLLM virtual key + NATS instance if per-tenant ratified). DEFERRED: Vultr VPC provisioning per tenant (Scale-tier only, re-introduce on first Scale-tier customer). Pulumi state stored in Vultr object storage. Owner: Aiden (review/governance) + engineer-tier TBD (implementation). Depends on: tenant.table (provisioning trigger) + mem.tenancy_tripwire (topology shift trigger) + eph.scoping (Temporal workflow is provisioning runner). | LOOSE V1-required | Dave directive + Viktor 2026-05-25 verbatim + Aiden delta 2026-05-25 | nothing | V1-launch |

## Category 17 — Tier Capacity Allocation (owner: Elliot impl-feasibility + Aiden architecture-fit + Viktor roadmap/pricing alignment)

Added per Dave directive 2026-05-25 ts ~1779710800. Concurrent agent thread allocation per tier. Capacity floor (all tiers): 1 chat + 2 deliberators.

| ID | Element | Status | Source | Customer-visible | Phase |
|---|---|---|---|---|---|
| tier.sandbox | Sandbox free managed: 1 chat + 2 deliberators + 1 worker = 4 concurrent; 10 tasks/day rate limit; trial/evaluation purpose | LOOSE | Dave directive 2026-05-25 | onboarding/pricing | V1-launch |
| tier.solo | Solo $79: 1 chat + 3 deliberators + 2 workers = 6 concurrent (BUMPED from 2→3 deliberators per Dave 2026-05-25 decision #4 "no governance compromise" — CONCUR integrity > tier pricing optimisation; Solo margin compresses ~70% to ~50%; accepted). Solo founder, single active project, light parallelism. Curve becomes 4-6-8-14 | RATIFIED-CEO | Dave directive 2026-05-25 decisions #4 + #6 | onboarding/pricing | V1-launch |
| tier.pro | Pro $249: 1 chat + 3 deliberators + 4 workers = 8 concurrent; dev shop, 2-3 active projects, moderate parallelism. Multi-chat unlocks here | LOOSE | Dave directive 2026-05-25 | onboarding/pricing/dashboard | V1-launch |
| tier.team | Team $649: 2 chats + 4 deliberators + 8 workers = 14 concurrent; small team 3-5 people, multiple projects, multi-user | LOOSE | Dave directive 2026-05-25 | onboarding/pricing/dashboard | V1-launch |
| tier.distributor | Distributor $775 base + $15/thread wholesale; floor 14 baseline (2 chats + 4 deliberators + 8 workers); wholesale-mode | LOOSE | Dave directive 2026-05-25 | onboarding/pricing | V1-launch |
| tier.enterprise | Enterprise tier (replaces Scale per V1.0 spec rename — Dave 2026-05-25 decision #5): per-tenant VPC topology A, custom pricing requirements-based, $1,500/mo internal floor (Aiden arch-fit cost minimum), realistic range $1,500-$50,000+/mo. Public messaging: "Enterprise — custom pricing based on requirements". Value drivers: per-tenant VPC, custom SLAs, custom integrations, compliance certifications (SOC 2/HIPAA), custom pack development, dedicated support, white-labeling | RATIFIED-CEO | Dave directive 2026-05-25 decision #5 + Aiden Cat 17 arch-fit floor | onboarding/pricing | V1-launch |
| tier.self_hosted | Self-Hosted free; unlimited concurrent (their infrastructure, their cost); no capacity gate | LOOSE | Dave directive 2026-05-25 | install/pricing | V1-launch |
| tier.baseline_rule | Baseline rule: PAID tiers minimum 1 chat + 3 deliberators (preserves dual-concur under KEI-206 author-exclusion). Sandbox eval-tier carve-out: 2 deliberators with sole-deliberator review (relaxed governance for free eval only). Per Dave decision #4: no governance compromise at paid tiers — CONCUR integrity > tier pricing optimisation | RATIFIED-CEO | Dave directive 2026-05-25 decision #4 + Aiden arch-fit | nothing | V1-launch |
| tier.capacity_behaviour | When tier-capped: tasks queue with visible "waiting for capacity" indicator in workflow diagram. NOT rejected. 5-min timeout to upgrade prompt with context ("5 of 5 slots in use — upgrade to Pro for 3 more parallel tasks") | LOOSE | Dave directive 2026-05-25 | dashboard | V1-launch |
| tier.burst_capacity | Burst capacity — V2 consideration. Each tier could allow brief bursts above limit for short tasks. Adds UX complexity; defer | DEFERRED | Dave directive 2026-05-25 | dashboard | V2 |
| tier.multi_user_chat_slot | Multi-user Team tier: does each user get own chat slot, or shared chat pool? CEO lean: per-user (clean isolation, predictable concurrency) | LOOSE (open question #2) | Dave directive 2026-05-25 | dashboard | V1-launch |
| tier.team_distributor_gap | Gap from Team $649 to Distributor $775 feels small for meaningful capacity jump. Suggests missing Scale tier OR Distributor pricing needs review | LOOSE (open question #3) | Dave directive 2026-05-25 | pricing | V1-launch |
| tier.infra_cost_curve | Infrastructure cost driver (BYOK covers token cost): Sandbox ~$2/mo, Solo ~$5-10/mo, Pro ~$15-25/mo, Team ~$40-60/mo, Distributor variable per thread | LOOSE | Dave directive 2026-05-25 | nothing | V1-launch |
| tier.parallelism_curve | Each tier ~60-75% parallelism increase from previous. Workers scale faster than chats/deliberators (execution is high-throughput need; reasoning is bottleneck most cases don't hit) | LOOSE | Dave directive 2026-05-25 | nothing | V1-launch |
| tier.calibration_caveat | Pre-revenue; no customer use patterns to calibrate against. First 10 customers' actual concurrency will tell us whether 5/8/14 are right shapes or need adjustment | LOOSE (acknowledged) | Dave directive 2026-05-25 honest caveat | nothing | V1-launch |

**Fleet deliberation request (per Dave):**
1. Pressure-test capacity numbers — are 4/5/8/14 right shapes, or should curve be steeper/flatter?
2. Resolve 3 open questions (Team-vs-Scale reconciliation; per-user chat slots in Team; Team-to-Distributor gap)
3. Validate infra-cost estimates against actual per-tenant burden at each tier
4. Flag architectural reasons certain numbers don't work (Temporal worker pool limits, NATS subject scaling, Postgres connection limits, Hindsight tenant-extension overhead)

**Aiden architecture-fit response 2026-05-25 (NATS ts 1779712149):**

**Curve verdict:** 4/5/8/14 architecturally defensible. 2 pre-revenue calibration risks acknowledged: Pro $/concurrent steepens 2× ($15.80 Solo → $31.13 Pro); Sandbox single-worker means zero parallel exec (intentional limitation; name explicitly in pricing copy). LOOSE tag correct.

**Primary architectural bottleneck — Postgres connection pool:**
- Supabase Pro = 200 conns/instance. Per-tenant load: Solo 10, Pro 16, Team 28
- All-Pro cohort saturates at 12.5 tenants/instance (NOT 20-30 as mem.tenancy_tripwire assumes); 70/30 Solo/Pro mix saturates at ~17 tenants
- Phase 2 sub-items: (a) PgBouncer transaction-mode pooling (~10× multiplexer; requires prepare_threshold=None in psycopg3 per reference_psycopg_supabase_pgbouncer); (b) per-tier connection pool sizing in TenantExtension; (c) Pro-weighted tripwire variant (trip at 12 Pro OR 20 Solo, whichever first)

**Secondary bottleneck — TEI sidecar throughput:**
- BGE-small-en-v1.5 single instance ~100-500 embeddings/sec; 10 Team-tier tenants × 140 emb/sec = 1,400 emb/sec saturates one TEI
- mem.tei_topology now load-bearing for tier capacity (not just memory arch nit)
- Aiden recommends hybrid: shared TEI pool for Solo/Pro + dedicated sidecar for Team+ (mirrors mem.topology Topology A/B split)

**Other layers verdict (NATS, Temporal, TenantExtension):** NOT bottlenecks at 4/5/8/14 concurrencies. Comfortable headroom.

**Critical governance gap — author-exclusion blocks dual-concur in 2-deliberator tiers (Sandbox + Solo):**
KEI-206 author-exclusion: when 1 deliberator authors, only OTHER deliberators can concur. In 2-deliberator tier, 1 authors + 1 reviews = sole-deliberator review, not dual-concur. **Resolution options:**
- (a) Sandbox-only carve-out: "no author-exclusion in Sandbox eval-tier; sole-deliberator review sufficient" — Solo stays at 2 deliberators + same carve-out applies (Aiden flags this as ARCH RISK since Solo is paid-tier and customers expect dual-concur)
- (b) Bump Solo deliberator floor to 3 (curve becomes 4/6/8/14) + Sandbox stays at 2 with carve-out only at eval-tier
- (c) Sandbox deliberators review-only-cannot-author (restrictive; forces all proposals from workers)
- **Aiden recommends (b)** — preserves governance at paid tiers; cleanest tier progression

**Scale tier — CONCUR with CEO lean to insert above Team:**
- Architectural rationale: Team is Topology B ceiling (200 Postgres conns / 28 Team-tier-tenant-conns ≈ 7 Team tenants/instance — even tighter than Pro); Scale is Topology A (per-tenant VPC) floor — unlimited concurrent within dedicated infra
- Aiden arch-fit cost floor: ~$140-190 AUD/mo per-tenant infra (dedicated Postgres $50-100 + NATS $20 + TEI $30 + Hindsight $40) + margin + BYOK token cost passthrough
- Aiden suggests price floor ~$1,500+ AUD/mo (anything lower = loss-leader). Final price = Viktor pricing-fit lens
- This resolves Dave's open question #3: Team→Distributor gap is small because Distributor is wholesale-upgrade-mechanism not capacity-jump; Scale tier is the actual capacity jump

**3 CEO-lean concurrences:**
- Q1 (Separate Scale tier above Team): CONCUR
- Q2 (Per-user chat slot in Team — not shared pool): CONCUR (per-user matches mem.byok sovereignty + Hindsight TenantExtension nested-user-scoping)
- Q3 (Team→Distributor gap small because Scale missing, not because Distributor mispriced): CONCUR

**6 cross-cat depends_on edges surfaced (apply to inventory):**
- `tier.*` ← `mem.tenancy_tripwire` (cohort-mix shapes tripwire)
- `tier.team`, `tier.distributor`, `tier.scale_per_vpc` ← `mem.tei_topology`
- `tier.solo`, `tier.sandbox` ← `op.orchestrator_merge` KEI-206 author-exclusion
- `tier.scale_per_vpc` ← `mem.topology` Topology A
- `tier.capacity_behaviour` ← `temp.middleware` (queue + upgrade prompt fires from chokepoint)
- `tier.infra_cost_curve` ← `cost.metering_pipeline` (real cost capture validates estimates)

**Phase 2 deliberation locks final numbers as RATIFIED. Until then, LOOSE.**

Pending: Viktor pricing-fit response on Pro $/concurrent steepening + Scale tier price + Distributor $126 premium justification + Atlas/Max spot-check tomorrow when API limits clear.

## Category 19 — UX / Product Surface (owner: Aiden design/customer-context lens + Elliot impl-feasibility lens)

Added per Dave directive KEI-UX-LIVING-DOC 2026-05-25 ts ~1779712500. Captures all CEO-side UX discussion this session. To become Keiracom UX Living Document in Drive (same pattern as architecture doc) once Phase 2 stabilises.

**Customer-facing positioning (locked principles):**

| ID | Element | Status | Source | Customer-visible | Phase |
|---|---|---|---|---|---|
| ux.positioning_chat_dash_byok | Customer sees: chat + dashboard. BYOK. Everything else provided | RATIFIED-CEO | Dave directive 2026-05-25 | chat/dashboard | V1-launch |
| ux.no_agent_language | No agent/fleet/governance language exposed customer-side | RATIFIED-CEO | Dave directive | chat/dashboard/onboarding | V1-launch |
| ux.generalist_execution | Generalist task execution system (not domain-bounded; "like asking what Claude is for") | RATIFIED-CEO | Dave directive | onboarding/pricing | V1-launch |
| ux.apple_grade_simplicity | Apple-grade simplicity over sophisticated engineering substrate | RATIFIED-CEO | Dave directive | chat/dashboard | V1-launch |
| ux.platform_mobile_primary | Mobile-primary, desktop-parity | RATIFIED-CEO | Dave directive | install (app stores) | V1-launch |
| ux.tech_stack_rn_next | React Native + Next.js (shared via React Native Web); iOS + Android + Web one codebase; ~70% code reuse | RATIFIED-CEO | Dave directive | nothing | V1-launch |

**App-of-apps architecture (mobile bottom nav V1):**

| ID | Element | Status | Source | Customer-visible | Phase |
|---|---|---|---|---|---|
| ux.nav.home | Home (Command Center) — overview, current state, alerts, recent activity, quick actions | RATIFIED-CEO | Dave directive | dashboard | V1-launch |
| ux.nav.chat | Chat — project-organized conversations | RATIFIED-CEO | Dave directive | chat | V1-launch |
| ux.nav.projects | Projects — workspace view, project list, details | RATIFIED-CEO | Dave directive | dashboard | V1-launch |
| ux.nav.workflows | Workflows — live execution view + history | RATIFIED-CEO | Dave directive | dashboard | V1-launch |
| ux.nav.more | More — hub for secondary surfaces | RATIFIED-CEO | Dave directive | dashboard | V1-launch |
| ux.nav.5tab_user_test | 5-tab bottom nav labels — user-test with 5-10 prospective customers before locking? | LOOSE (open question 1) | Dave directive | dashboard | V1-launch |
| ux.nav.notifications_primary | Notifications as first-class primary surface (not buried under More) | LOOSE (CEO add 6) | Dave directive | dashboard | V1-launch |

**Secondary surfaces (under More):**

| ID | Element | Status | Source | Customer-visible | Phase |
|---|---|---|---|---|---|
| ux.surface.files | Files (customer file system) | RATIFIED-CEO | Dave directive | dashboard | V1-launch |
| ux.surface.memory_inspector | Memory Inspector — show what system knows about customer's business (DIFFERENTIATOR; moat candidate) | RATIFIED-CEO | Dave directive | dashboard | V1 or V2 |
| ux.surface.integrations_hub | Integrations Hub | RATIFIED-CEO | Dave directive | dashboard | V2 |
| ux.surface.settings | Settings (BYOK, tier, billing) | RATIFIED-CEO | Dave directive | onboarding/dashboard | V1-launch |
| ux.surface.approval_queue | Approval Queue | RATIFIED-CEO | Dave directive | dashboard | V3 |
| ux.surface.notifications | Notifications | RATIFIED-CEO | Dave directive | dashboard | V1-launch |
| ux.surface.audit_log | Audit Log (compliance, regulated verticals) | RATIFIED-CEO | Dave directive | dashboard | V1 or V2 |

**Chat architecture:**

| ID | Element | Status | Source | Customer-visible | Phase |
|---|---|---|---|---|---|
| ux.chat.project_primary | Project = primary organisational unit (own context, memory scope, workflow state, file folder) | RATIFIED-CEO | Dave directive | chat | V1-launch |
| ux.chat.one_primary_default | One primary chat per project (default) | RATIFIED-CEO | Dave directive | chat | V1-launch |
| ux.chat.topic_branches | Topic chats branch when needed | RATIFIED-CEO | Dave directive | chat | V1-launch (Pro tier feature) |
| ux.chat.multi_thread_tier_gating | Multi-thread chats — tier-gated to Pro vs all tiers? | LOOSE (open question 2) | Dave directive | chat/pricing | V1-launch |
| ux.chat.cross_project_mention | Cross-project context via explicit @-mention gesture | RATIFIED-CEO | Dave directive | chat | V1-launch |

**Workflow visualisation:**

| ID | Element | Status | Source | Customer-visible | Phase |
|---|---|---|---|---|---|
| ux.workflow.live_execution | Live execution view, real-time, nodes light up as work happens | RATIFIED-CEO | Dave directive | dashboard | V2 |
| ux.workflow.decision_traces | Decision points highlighted with reasoning trace expandable | RATIFIED-CEO | Dave directive | dashboard | V2 |
| ux.workflow.concur_visible | CONCUR moments visible to customer (architectural transparency) | RATIFIED-CEO | Dave directive | dashboard | V2 |
| ux.workflow.memory_hits | Memory hits surfaced (what fleet pulled from memory) | RATIFIED-CEO | Dave directive | dashboard | V2 |
| ux.workflow.replay_deferred | Replay capability DEFERRED to V2 | DEFERRED | Dave directive | dashboard | V2 |
| ux.workflow.not_static_designer | NOT a static workflow designer (different problem than Relevance AI) | RATIFIED-CEO | Dave directive | dashboard | V2 |
| ux.workflow.v1_scope | Workflow diagram V1 scope — live status only vs interactive node tree? | LOOSE (open question 3) | Dave directive | dashboard | V1-launch |

**Artifacts (inline in chat):**

| ID | Element | Status | Source | Customer-visible | Phase |
|---|---|---|---|---|---|
| ux.artifacts.file_types_v1 | V1 file types: code (Monaco), markdown, PDF preview, images, CSV tables, Word/Excel (Mammoth.js), JSON/YAML | RATIFIED-CEO | Dave directive | chat | V1-launch |
| ux.artifacts.version_history | Version history per artifact | RATIFIED-CEO | Dave directive | chat | V1-launch |
| ux.artifacts.preview_edit_dl | Preview + edit + download | RATIFIED-CEO | Dave directive | chat | V1-launch |

**Customer file system:**

| ID | Element | Status | Source | Customer-visible | Phase |
|---|---|---|---|---|---|
| ux.files.storage | Vultr Object Storage + Postgres hierarchy table | RATIFIED-CEO | Dave directive | dashboard | V1-launch |
| ux.files.tenant_prefix_isolation | Tenant ID prefix for mechanical isolation at storage API layer (NOT UI layer) | RATIFIED-CEO | Dave directive | nothing | V1-launch |
| ux.files.system_files_hidden | System files (reasoning traces, system prompts, governance configs, Temporal state) NEVER queryable by customer file system | RATIFIED-CEO | Dave directive | nothing | V1-launch |
| ux.files.search | Full-text + semantic search (Hindsight powers semantic side) | RATIFIED-CEO | Dave directive | dashboard | V1-launch |
| ux.files.organisation | Folder organisation, version history, file sharing, tags, "Pin to chat" | RATIFIED-CEO | Dave directive | dashboard | V1-launch |
| ux.files.tier_storage_differentiator | Storage tier as differentiator: Solo limited GB / Pro more / Scale substantial | RATIFIED-CEO | Dave directive | pricing/onboarding | V1-launch |

**V1/V2/V3 scope (proposed):**

| ID | Element | Status | Source | Customer-visible | Phase |
|---|---|---|---|---|---|
| ux.scope.v1_essentials | V1 essentials (~3-4mo fleet-built): Home, Chat single-thread default, Projects basic, Files, Settings, Notifications, Onboarding wizard, Artifacts inline, Token Budget Visualisation, Task progress/live status | RATIFIED-CEO | Dave directive | all customer surfaces | V1-launch |
| ux.scope.v2_additions | V2: Workflows visualisation, Memory Inspector, multi-thread chats (Pro), Integrations Hub, basic analytics | RATIFIED-CEO | Dave directive | dashboard/chat | V2 |
| ux.scope.v3_polish | V3: Approval Queue, Templates/Marketplace, Cross-device handoff, Voice input, Inline approvals from push notifications | RATIFIED-CEO | Dave directive | all | V3 |

**CEO adds (beyond standard surfaces):**

| ID | Element | Status | Source | Customer-visible | Phase |
|---|---|---|---|---|---|
| ux.add.onboarding_wizard | Onboarding wizard — V1 MANDATORY (BYOK setup, OAuth via Composio, first project, first chat); drop-off highest at first-run | RATIFIED-CEO | Dave directive CEO add 1 | onboarding | V1-launch (BLOCKER) |
| ux.add.quick_actions_home | Quick Actions on Home — common starting points, removes blank-canvas paralysis | RATIFIED-CEO | Dave directive CEO add 2 | dashboard | V1-launch |
| ux.add.cross_device_handoff | Cross-device handoff — start mobile, continue desktop, state syncs (Apple-grade) | RATIFIED-CEO | Dave directive CEO add 3 | dashboard | V3 (open question 8) |
| ux.add.voice_input | Voice input on mobile — Whisper or native speech-to-text | RATIFIED-CEO | Dave directive CEO add 4 | chat | V3 (open question 7) |
| ux.add.inline_push_approvals | Inline approvals from push notifications — tap to approve without opening app | RATIFIED-CEO | Dave directive CEO add 5 | dashboard | V3 |

**Differentiators (land V1 if possible):**

| ID | Element | Status | Source | Customer-visible | Phase |
|---|---|---|---|---|---|
| ux.diff.memory_inspector | Memory Inspector — show what system knows about customer's business; most AI products do not surface their memory; real moat | RATIFIED-CEO | Dave directive | dashboard | V1 or V2 |
| ux.diff.reasoning_trace_viewer | Reasoning Trace Viewer — for any output show why; Reasoning Listener customer-facing surface | RATIFIED-CEO | Dave directive | chat/dashboard | V1 or V2 |
| ux.diff.audit_trail_viewer | Compliance / Audit Trail Viewer — gate-opener for regulated verticals (legal, health, accounting) | RATIFIED-CEO | Dave directive | dashboard | V1 or V2 |

**Hard problems (cross-cutting; engineering complexity):**

| ID | Element | Status | Source | Customer-visible | Phase |
|---|---|---|---|---|---|
| ux.hard.realtime_sync | Real-time updates across devices (WebSocket + careful state management) | LOOSE | Dave directive | nothing | V2 |
| ux.hard.offline_mode | Offline mode + reconnect sync | LOOSE | Dave directive | chat/dashboard | V3 |
| ux.hard.file_rendering | File rendering for many types (extends artifacts work) | LOOSE | Dave directive | chat | V1-launch |
| ux.hard.mobile_desktop_sync | Mobile-desktop state synchronisation | LOOSE | Dave directive | dashboard | V2 |
| ux.hard.push_notifications | Push notifications (iOS APNs + Android FCM) | LOOSE | Dave directive | dashboard | V1-launch |
| ux.hard.tenant_isolation_ui | Multi-tenant isolation enforcement at UI layer (decoration only — real enforcement at API) | LOOSE | Dave directive | nothing | V1-launch |
| ux.hard.large_file_perf | Performance with large file systems (virtualised lists, lazy loading) | LOOSE | Dave directive | dashboard | V1-launch |
| ux.hard.wcag | WCAG accessibility compliance (enterprise requirement) | LOOSE | Dave directive | all | V1 or V2 |

**Engineering complexity estimates (Dave's framing):**
- Solid V1 with fleet acceleration: 3-4 months from "backend ready"
- Polished V1 with differentiator features: 6-8 months
- True mobile + desktop parity with offline mode: 9-12 months
(Per `feedback_no_time_estimates` — these are Dave's framing; I'll surface scope-by-work-items in deliberation response)

**8 open questions for fleet deliberation:**
1. 5-tab bottom nav labels — user-test with 5-10 prospective customers before locking? (LOOSE; captured in ux.nav.5tab_user_test)
2. Multi-thread chats — tier-gated to Pro vs all tiers? (LOOSE; captured in ux.chat.multi_thread_tier_gating)
3. Workflow diagram V1 scope — live status only vs interactive node tree? (LOOSE; captured in ux.workflow.v1_scope)
4. ICP segmentation — V1.0 spec 5 segments; chat agent v3 calibrated for technical builders only. Narrow ICP or build persona variants? (Viktor recommends narrow-to-1; cross-cite cust.icp_segmentation)
5. Onboarding wizard flow — right BYOK + OAuth + first-project sequence? (LOOSE; design needed)
6. Tier capacity allocation interaction with UX — does Pro multi-chat unlock require visual differentiation from Solo? (LOOSE; cross-cite Cat 17)
7. Voice input — V2 or V3 priority? (Dave proposes V3; LOOSE for fleet)
8. Cross-device handoff — V2 or V3 priority? (Dave proposes V3; LOOSE for fleet)

**Reference designs (inspiration; NOT verbatim copy):**
- Field Toolkit (NBN field ops app) — categorised resources, bottom nav, icon grids
- Relevance AI — workflow visualisation (different problem: static designer vs dynamic execution)
- OneDrive — file system browser pattern
- Claude.ai — artifacts pattern (inline preview + edit + version history)
- Cursor — code/chat integration

**Fleet deliberation request (per Dave):**
1. Pressure-test bottom nav structure — 5 tabs right? Workflows primary or in More? Notifications primary?
2. Resolve the 8 open questions above
3. Validate engineering complexity estimate against actual fleet capacity
4. Flag missing UX surfaces/patterns that should be in V1 or V2 scope
5. Identify dependencies on un-ratified architecture (which UX features block on which architecture items)
6. Pressure-test "no agent/fleet language" principle — any places where we must surface internal architecture for customer trust?

**Aiden Cat 19 deliberation 2026-05-25 (NATS ts 1779712658):**

**Nav verdict:** 5-tab structure HOLDS. Workflows stays primary with V1-scoped content (task progress + token budget + node-light-up — not full live-execution). **Notifications becomes header-icon with badge NOT 5th tab** (matches Slack/Discord/Apple pattern; resolves ux.nav.notifications_primary).

**8 open questions resolved:**
1. 5-tab user-test: YES — 5-10 prospective customers, label-test only, ~1 week, $0-$500
2. Multi-thread chats: Pro+ only (Sandbox = capacity abuse; Solo matches single-founder persona)
3. Workflow V1: live status only (no interactive node tree until V2)
4. ICP: narrow-to-1 (technical builders/solo founders) — CONCUR Viktor
5. Onboarding: 6-step sequence (Welcome → BYOK [non-skippable] → OAuth-deferrable → First project [templated] → First chat [pre-filled suggestion] → Capacity reminder). Inline "How to get a Claude/OpenAI key" guide critical
6. Pro multi-chat visual differentiation: YES (Solo no "+" button; Pro "+" + tab bar)
7. Voice input V3: CONCUR Dave
8. Cross-device handoff V3: CONCUR Dave

**HARD GOVERNANCE FLAG — mobile-primary scope vs fleet capacity:**
- Current fleet (Atlas/Orion/Scout/Nova) has ZERO React Native specialisation
- Aiden's 4 options: (a) hire mobile FTE; (b) Expo + fleet skills up in parallel; (c) phase: V1 web-only + V1.1 mobile; (d) outsource RN scaffolding
- **Aiden strong recommendation: (b)+(c) hybrid — V1 ships web-only (Next.js) with Expo scaffolding stood up in parallel (no critical path); V1.1 mobile when fleet has RN fluency. Sells "web product, mobile in [N] weeks" rather than over-promising mobile-at-launch**
- DECISION DAVE OWNS (not implementation choice — commercial framing implication)

**2 HARD UX BLOCKERS — V1 LAUNCH BLOCKED:**
- `ux.add.onboarding_wizard` ← `infra.secrets_management` (Vault) currently LOOSE-BLOCKER — onboarding cannot ship without BYOK key storage
- `ux.files.system_files_hidden` ← `mcp.go_sidecar` currently GAP/pending — customer file system could leak system files without Go Sidecar enforcement

Vault is on TWO V1 critical paths (this UX one + Aiden's backup-DR critical path) — **HIGHEST-PRIORITY UNBLOCK across V2 inventory**.

**10 missing UX surfaces (apply to inventory):**

| ID | Element | Status | Source | Customer-visible | Phase |
|---|---|---|---|---|---|
| ux.surface.error_states | Error states / recovery UX (Vault sealed, memory unavailable, LLM rate-limit, payment failure) | LOOSE V1-required | Aiden Cat 19 deliberation §4A.1 | chat/dashboard | V1-launch |
| ux.pattern.loading_states | Loading / skeleton screens (Apple-grade polish) | LOOSE V1-required | Aiden Cat 19 §4A.2 | all surfaces | V1-launch |
| ux.pattern.empty_states | Empty states (first project, no notifications, no files) — drop-off prevention | LOOSE V1-required | Aiden Cat 19 §4A.3 | onboarding/dashboard | V1-launch |
| ux.flow.byok_rotation | BYOK rotation flow (swap key without losing state) | LOOSE V1-required | Aiden Cat 19 §4A.4 | onboarding/settings | V1-launch |
| ux.flow.budget_alerts | Spending caps / budget alerts UX (80% alert + 100% hard-stop) | LOOSE V1-required | Aiden Cat 19 §4A.5 | dashboard | V1-launch |
| ux.flow.account_management | Account management / billing UX (upgrade/downgrade/cancel/refund) | LOOSE V1-required | Aiden Cat 19 §4A.6 | settings/pricing | V1-launch |
| ux.surface.conversation_search | Conversation search across all chats (different from files search) | LOOSE | Aiden Cat 19 §4B.7 | chat | V2 |
| ux.flow.project_lifecycle | Project archive / delete UX | LOOSE | Aiden Cat 19 §4B.8 | dashboard | V2 |
| ux.surface.help_docs | Help / docs surface (web-docs link V1, in-app V2) | LOOSE V1-required | Aiden Cat 19 §4B.9 | dashboard | V1-launch (V1=link; V2=in-app) |
| ux.surface.customer_support | Customer support contact path (expected for paying tiers) | LOOSE V1-required | Aiden Cat 19 §4B.10 | settings/dashboard | V1-launch |

**Mobile strategy decision row:**

| ID | Element | Status | Source | Customer-visible | Phase |
|---|---|---|---|---|---|
| ux.mobile_strategy | RATIFIED: V1 ships web-only (Next.js); native mobile follows V1.1 once fleet has ingested React Native knowledge + completed practice phase. Customer messaging: "web product at launch, native mobile in [N weeks]". Decision #1 — fleet research + memory ingestion path chosen over hire-specialist | RATIFIED-CEO | Dave directive 2026-05-25 decision #1 + Aiden Cat 19 §3C | install (app stores), pricing | V1-launch (web) / V1.1 (native mobile) |
| ux.react_native_ingestion_programme | 2-week intensive Hindsight ingestion phase + practice phase building 3-5 small mobile prototypes. Sources: React Native official docs + Expo + RN Web docs + open-source RN codebases (Discord, Skype, Facebook RN apps) + post-mortems + engineering blogs + conference talks + expert writings (Evan Bacon, Ram Krishnan, etc). Configure "Mobile Engineer" agent identity with that knowledge. Quality compounds via failure-informed memory routing around what doesn't work. Strategic bonus: R&D for future vertical pack business — document what works, what doesn't, ingestion timing, quality at week 1 vs week 4 — becomes case study for external pack model (accounting, legal, etc) | RATIFIED-CEO | Dave directive 2026-05-25 decision #1 | nothing (engineering capability build) | V1-launch (pre-mobile-V1.1) |

**Trust-theatre opportunity (V2):**

| ID | Element | Status | Source | Customer-visible | Phase |
|---|---|---|---|---|---|
| ux.diff.trust_indicator_badge | "Reviewed by 2 specialists" badge on outputs (paid-tier differentiator; "Pro outputs are dual-checked") | LOOSE | Aiden Cat 19 §6C | chat/dashboard | V2 |

**5 honest exceptions to "no agent/fleet language" principle:**
1. Regulated verticals audit trail: "reviewed twice before output" (NOT "Aiden + Max concurred")
2. Pricing tier rationale: "parallel reasoning slots" / "concurrent capacity" (NOT "3 agents")
3. Error messages: "Memory service unavailable" (NOT "Hindsight down")
4. BYOK setup: "your key, your control" (NOT "we use LiteLLM")
5. System status page: "Memory service / Chat service / File storage" (NOT "Hindsight / NATS / Vultr")

**Chat agent v3 persona V1-LAUNCH BLOCKER critical path:** per `persona.chat_agent_identity` + Viktor coherence-check + criterion 3 (LOOSE definitions). The persona shapes first-chat experience. "What are you trying to ship? Let's break it down." (competent-peer) vs "Hi! I'm your AI assistant..." (generic AI). Persona work is NOT Phase 3.x deferred — V1 critical path. Cross-cite `crit3.identities`.

**Customer-journey coherence pass-test (Viktor pattern):**
- Test 1: onboarding → first project → first chat → output: "feels like one capable thing"
- Test 2: tier wall → upgrade → resume task: "felt continuous"
- Test 3: device switch → same project visible: "same machine remembered" — FAILS V1 (cross-device sync V2; document the limitation in onboarding "mobile-first; web sync coming Q[N]")

**Once stabilised:** Elliot creates Keiracom UX Living Document in Drive (same pattern as architecture doc + manual). Three-store fires on creation.

Memory cutover steps 4 and 5 remain on hold per V2.0 directive. UX work runs in parallel — does not block on architecture lock.

## Category 19.1 — Chat UX Pattern Additions (Phase B chat UX scope per Dave directive 2026-05-26)

Added per Dave directive 2026-05-26 ~00:25 UTC. Four V1 must-have patterns identified from chat UX research + Dave review. Design philosophy: Apple-grade restraint (Linear / Arc Browser / Apple Intelligence reference); avoid ChatGPT / Cursor / Material Design.

**V1 critical-path additions (4 items):**

| ID | Element | Status | Source | Customer-visible | Phase |
|---|---|---|---|---|---|
| ux.chat.artifacts_side_panel | Artifacts side panel (chat as engine, document as dashboard). Substantive outputs (proposals, roadmaps, drafts, tables, code) open in side panel (desktop) or full-screen overlay (mobile). Customer iterates on artifact while chat continues. Reference: Claude Artifacts + ChatGPT Canvas + Cursor side pane. Architectural ask: chat message types beyond plain text — render structured artifact blocks that open in side panel on tap | LOOSE V1 HARD GATE | Dave directive 2026-05-26 #1 | chat | V1-launch |
| ux.chat.streaming_text | Streaming text token-by-token reveal. Anthropic SDK supports natively; server-sent events from chat agent → client renders progressively. Absence feels broken to power users | LOOSE V1 HARD GATE | Dave directive 2026-05-26 #2 | chat | V1-launch |
| ux.chat.stage_indicators | Stage indicators (system activity visibility). During Keira's processing, customer sees progress: "Routing to deliberators → Workers researching providers → Synthesizing proposal → Done". Implementation: stage events emitted from Temporal workflow → SSE channel to client → render as collapsible status block above response. Without this, customer experiences silence during multi-minute deliberations and assumes system froze | LOOSE V1 HARD GATE | Dave directive 2026-05-26 #3 | chat | V1-launch |
| ux.chat.memory_chips | Memory chips (compounding memory made visible). Compact context display at top of chat: "Context: AI BDR project · Solo tier · 5 days in · 3 prior decisions". Tappable to expand into Memory Inspector. Implementation: chat agent computes context summary from Hindsight queries → renders as chip block above conversation. Makes the differentiator tangible | LOOSE V1 HARD GATE | Dave directive 2026-05-26 #4 | chat | V1-launch |

**Foundational UI hygiene (no separate scope — lands during B6 build):**
- Action buttons (already in B11)
- Typing indicator ("Keira is thinking...")
- Skeleton loaders instead of spinners
- Inline OAuth (with Composio white-label B11)
- Subtle spring animations (iOS-style, not Material)

**V1.x deferred (within 3 months post-launch):**
- Slash commands (/research, /draft, /summarize)
- Reasoning expansion ("show thinking")
- Confidence indicators on outputs
- Diff views for content changes
- Voice input
- Image upload

**V2+ (after first 10 customers):**
- Carousel cards
- Command palette (Cmd+K)
- @-mentions for subsystems
- Live preview (v0-style)
- Camera input

**Design philosophy LOCKED:**
- Apple-grade restraint — animation reinforces state change, never decorates
- Reference: Linear, Arc Browser, Apple Intelligence
- Avoid: ChatGPT (too plain), Cursor (too dense), Material Design (too bouncy)
- Reduce-motion respected (accessibility)
- No celebration confetti (feels infantile in B2B)

**Deliberation request (per Dave):**
1. Aiden: architecture-fit lens on each of the 4 items (SSE infrastructure, message type schema, Temporal stage emission)
2. Atlas: implementation-feasibility on each + effort estimate
3. Viktor: cross-check against the 29-item customer-lens gap list (Cat 22) — any overlap or conflict
4. Cross-reference Phase B6 scope to identify what's already implicit vs needs explicit addition

## Category 20 — System Deep-Dive Per-Layer Audit (owner: Elliot orchestrates; each layer has named owner)

Added per Dave directive KEI-SYSTEM-DEEP-DIVE 2026-05-25 ~1779746500. Twelve layers each owner produces a one-page deep-dive at `docs/architecture/deep_dives/layer_NN_name.md` answering six questions: Designed / Built / Measured / Token+Cost / Cache strategy / LOOSE items, plus per-tier variation + per-agent-type variation where applicable.

| ID | Element | Status | Source | Customer-visible | Phase |
|---|---|---|---|---|---|
| deepdive.layer1_customer_surface | Customer surface (chat + dashboard + BYOK) — Aiden | LOOSE (deep-dive pending) | Dave directive 2026-05-25 | chat/dashboard | V1-launch |
| deepdive.layer2_chat_agent_keira | Chat agent Keira (Tier 1 ephemeral) — Viktor + Aiden | LOOSE (deep-dive pending) | Dave directive | chat | V1-launch |
| deepdive.layer3_deliberators | Deliberators (Tier 2 CONCUR-gated) — Aiden | LOOSE (deep-dive pending) | Dave directive | nothing | V1-launch |
| deepdive.layer4_worker_agents | Worker agents (domain execution) — Atlas | LOOSE (deep-dive pending) | Dave directive | nothing | V1-launch |
| deepdive.layer5_orchestration | Orchestration (Temporal workflow engine — designed, NEVER deployed) — Orion | LOOSE (deep-dive pending; HARD GAP) | Dave directive | nothing | V1-launch |
| deepdive.layer6_memory | Memory (Hindsight + Weaviate transition + TEI sidecar) — Atlas + Aiden | LOOSE (deep-dive pending) | Dave directive | nothing | V1-launch |
| deepdive.layer7_governance | Governance (CONCUR + Go Sidecar + versioned config) — Aiden | LOOSE (deep-dive pending) | Dave directive | dashboard (audit view) | V1-launch |
| deepdive.layer8_integration | Integration (MCP + Composio + LiteLLM) — Orion + Atlas | LOOSE (deep-dive pending) | Dave directive | chat (tool calls) | V1-launch |
| deepdive.layer9_state_persistence | State / persistence (Postgres + Valkey + Supabase) — Atlas | LOOSE (deep-dive pending) | Dave directive | nothing | V1-launch |
| deepdive.layer10_infrastructure | Infrastructure (Vultr + Docker + Vault + Cloudflare) — Orion | LOOSE (deep-dive pending) | Dave directive | nothing | V1-launch |
| deepdive.layer11_cost_optimization | Cost optimization (caching + token budgets + routing) — Atlas + Orion | LOOSE (deep-dive pending) | Dave directive | dashboard (token budget) | V1-launch |
| deepdive.layer12_observability | Observability (Better Stack + metrics + audit trails) — Scout + Atlas | LOOSE (deep-dive pending) | Dave directive | dashboard (admin) | V1-launch |
| deepdive.cross_cutting_aggregation | Cross-layer dependency graph aggregated by Elliot after Phase 1 deep-dives stabilise. Cross-cutting concerns each owner addresses where their layer touches: multi-tenancy enforcement, security (BYOK custody + secret mgmt + per-customer segregation), CI/CD + rollback, backup/DR (V1.x), customer file system, reasoning trace + audit trail, compliance gates | LOOSE (waits on Phase 1) | Dave directive | nothing | V1-launch |

**Cache framework registered canonical (per Dave directive):**
- Layer 1 (Anthropic prompt cache, 0.10× input cost): structurally stable per-domain content
- Layer 2 (uncached, 1.0×): per-call dynamic content
- Valkey semantic cache layered on top: repetitive query hits
- Conversation history beyond active window: stored in Hindsight for queryable recall, not held in active context
- Per-tier multipliers (proposal — refine in Phase 2): Sandbox 0.5× / Solo 1.0× / Pro 1.5× / Team 2.0× / Enterprise custom

This canonical registration sits in `cost.cache_discipline` (Cat 4) RATIFIED-CEO placement + LOOSE implementation; deep-dive Layer 11 produces the implementation spec.

## Category 22 — Customer-Lens Gaps (owner: Aiden arch-fit + Atlas impl-feasibility on V1 hard gates + Viktor pricing-roadmap)

Added per Dave directive KEI-CUSTOMER-LENS-GAPS 2026-05-25 ~1779749200. Twenty-nine gaps across 8 themes per CEO priority tags. Items #21/#22/#23 LOCKED IN Dave V1 migration scope.

**Theme 1 — Cost Control + Visibility**
- gap.cost_prediction_pre_exec — Cost prediction before execution ("This task will cost $0.50. Proceed?") | LOOSE V1.x strong
- gap.cost_visibility_per_task — Per-task cost visibility (live + retrospective) | LOOSE V1 HARD GATE (BYOK transparency depends on this)
- gap.spend_caps_per_project — Spend caps per project / per task type | LOOSE V2
- gap.cache_hit_rate_visibility — Cache hit rate visibility per customer | LOOSE V2
- gap.cost_comparison_reports — Cost comparison reports (vs Claude Max + Cursor Pro + ChatGPT Pro) | LOOSE V2

**Theme 2 — Trust + Safety**
- gap.sandbox_dry_run — Sandbox / dry-run mode for irreversible actions | LOOSE V1.x strong
- gap.approval_gate_irreversible — Explicit approval gate for irreversible actions (mobile push) | LOOSE V1 HARD GATE (trust mechanism)
- gap.confidence_scoring — Confidence scoring on outputs | LOOSE V2
- gap.action_rollback_undo — Action rollback / undo | LOOSE V2

**Theme 3 — Workflow + Productivity**
- gap.recurring_scheduled_tasks — Recurring / scheduled tasks (cron pattern) | LOOSE V1.x strong
- gap.webhook_triggers_inbound — Webhook triggers inbound (Stripe→invoice, GitHub PR→review) | LOOSE V1.x strong
- gap.task_templates_workflows — Task templates / saved workflows | LOOSE V1.x strong
- gap.multi_step_dag — Multi-step chained tasks with conditions (DAG) | LOOSE V2

**Theme 4 — Memory + Learning**
- gap.memory_editing_ui — Memory editing UI (Memory Inspector becomes editable) | LOOSE V1 HARD GATE (Memory Inspector differentiator)
- gap.selective_forgetting_archival — Selective forgetting / project lifecycle archival | LOOSE V2
- gap.memory_export_gdpr — Memory export (data portability, GDPR) | LOOSE V1.x strong
- gap.privacy_zones_memory — Privacy zones within memory | LOOSE V2

**Theme 5 — Collaboration (Team+)**
- gap.multi_user_rbac — Multi-user same project with permission levels (RBAC) | LOOSE V2
- gap.comments_annotations — Comments / annotations on agent work | LOOSE V2
- gap.approval_workflows_rbac — Approval workflows (marketer drafts, admin publishes) | LOOSE V2

**Theme 6 — Output Quality (Dave V1 migration scope per directive)**
- gap.self_correction_loop — Self-correction loop (agent reviews own output before delivery) | LOOSE V1 HARD GATE (Dave V1 migration)
- gap.style_learning — Style learning (matches customer's writing tone/vocabulary) | LOOSE V1 HARD GATE (Dave V1 migration)
- gap.output_format_flexibility — Output format flexibility (same content as email/Slack/PDF/Notion) | LOOSE V1 HARD GATE (Dave V1 migration)

**Theme 7 — Onboarding + Migration**
- gap.migration_tools_competitors — Migration tools from competitors (ChatGPT history, Claude projects, Cursor chats) | LOOSE V2
- gap.use_case_wizard — Use case wizard at onboarding | LOOSE V2
- gap.push_notifications_async — Push notifications for async completion. V1: WEB-PUSH (browser permission API + service worker; reuses Slack-alert notification routing substrate). V1.1: APNs + FCM with native mobile per ux.mobile_strategy_web_v1 | RATIFIED-CEO V1 web-push + V1.1 native (Dave 2026-05-25 ~1779750900)

**Theme 8 — Developer / Power User**
- gap.cli_api_access — CLI / API access (script Keiracom from terminal) | LOOSE V2
- gap.webhooks_outbound — Webhooks outbound (task events to customer's endpoint) | LOOSE V2
- gap.custom_agent_definitions — Custom agent definitions | LOOSE V2

**V1 Hard Gates Summary (7 items per Dave priority):**
1. gap.cost_visibility_per_task (BYOK transparency)
2. gap.approval_gate_irreversible (trust mechanism)
3. gap.memory_editing_ui (Memory Inspector differentiator)
4. gap.self_correction_loop (Dave V1 migration)
5. gap.style_learning (Dave V1 migration)
6. gap.output_format_flexibility (Dave V1 migration)
7. gap.push_notifications_async (async value prop)

**Deliberation request (per Dave):**
1. Aiden: architecture-fit lens on each gap — what changes architecturally?
2. Atlas: implementation-feasibility lens on the 7 V1 hard gates
3. Viktor: pricing/roadmap lens — differentiators vs hygiene
4. Cross-reference against existing LOOSE items (Memory Inspector design already in flight)
5. Surface any gaps NOT in this list

**Pattern observation (Dave):** Biggest cluster = trust + visibility (foundation for autonomous work customers trust). Second = workflow patterns beyond chat. Third = memory as customer-managed.

## Category 15 — Operational + Process (owner: Elliot)

| ID | Element | Status | Source | Customer-visible | Phase |
|---|---|---|---|---|---|
| op.worker_idling | Worker idling fix (yvz P1 in_progress; KEI-17 regression) | LOOSE | Agency_OS-yvz tracked but assignee unclear | nothing | V1-launch |
| op.probe_daemon | memory-core-fact-probe.service in FAILED state | LOOSE | Elliot status check 2026-05-25; paused per Viktor | nothing | DEFERRED (reconfigure against V2.0) |
| op.nova_state | Nova: missing self-claim loop (i9vrrt P0), Cognee silent drops (cjeo P1), identity runbook (e02v P2), keepalive sd_notify (x4jl P2) | LOOSE | bd open issues | nothing | V1-launch |
| op.orchestrator_merge | orchestrator-merge-after-NATS-concur pattern + KEI-206 author-exclusion | RATIFIED-CEO | _orchestrator.md PR #1116 | nothing | running |
| op.discovery_log | Discovery log + bd + Beads/Linear integration | RATIFIED-CEO | bd routing policy PR #1120 | nothing | running |
| op.audit_dispatch_checklist | Canonical-key-query gate + query-and-paste + deliberator cross-check | RATIFIED-CEO | _orchestrator.md audit-dispatch checklist | nothing | running |
| op.codeql_migration | SonarCloud → CodeQL migration | RATIFIED-CEO | PR #1138 | nothing | running |
| op.safe_resolve_consolidation | _safe_resolve rule-of-three → scripts/common/safe_paths.py | LOOSE | tracked KEI per Aiden Phase 1 §3.C | nothing | V1-launch |

---

## Items Pending Dave Pull-From-Context (per Aiden §3.B)

These items have either no canonical-key source OR no Aiden-retrievable source. Dave is the only person who has the full context. Surface as a single escalation:

- `mcp.go_sidecar` — broader Go sidecar role beyond Viktor verbatim (Dave DM context?)
- `cust.cognitive_software_refinery` — substantive framing-text Dave posted 2026-05-23 (Slack #ceo 2026-05-23 — Dave has channel access, team does not)
- `persona.depth_dm_content` — broader persona depth Dave DM content beyond Viktor's 2026-05-25 relayed framing
- `temp.contract_doc` — Elliot owes; not Dave-pull but flagged for completeness

## Items Aiden Flagged from §3.C (additional inventory rows)

- `cost.tier_router_attribution` — how does tier-router decide Solo/Pro/Scale topology routing (#1139 follow-up nit)
- `cost.cache_post_ephemeral_validity` — semantic cache validity in ephemeral-agent world (each spawn loses cache locality) (#1139 follow-up nit)
- `mem.tei_topology` — TEI sidecar per-tenant vs shared (depends on Topology A vs B per tier)
- `op.codeql_calibration_period` — verify dual-validation against SonarCloud for 3-5 PRs before admin-disabling Sonar (PR #1138 follow-up)

---

## Phase 2 Deliberation Order (per Aiden §5 step 8)

Leaf elements deliberate first, dependent ones second. Initial topology:

1. **Leaf level** (no depends_on): mem.engine, mem.byok, mem.tenancy_tripwire, repo.fair_source, nats.fleet_inter_agent
2. **L2**: mem.topology (depends on tenancy_tripwire), mem.primitives, mem.schema
3. **L3**: mem.wrap.*, tenant.extension, tenant.mcp_tier_router
4. **L4**: temp.*, cost.*
5. **L5**: cust.*, op.*

Full dep graph to lock in Phase 1 finalisation.

---

## Phase 1 Completion Criteria (per Aiden §5 step 7)

- [ ] Every row has a non-`[GAP]` `source`
- [ ] Every `depends_on` edge has both ends defined
- [ ] Viktor's coherence-check customer-journey view pullable via `customer_visible` column
- [ ] Section owners confirmed
- [ ] Atlas + Max review pass

---

**Status:** WORKING DRAFT v1. Open for Aiden + Viktor + Atlas + Max additions/corrections. Phase 2 deliberation begins after this stabilises.
