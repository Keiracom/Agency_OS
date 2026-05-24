# Hindsight Spike — Item (vi): Viktor's Domain Mapping + Trace/Audit Preservation

**Phase 2.1 Hindsight verification spike** (Aiden gate A, item vi — completes the spike).
Authored 2026-05-24 by Atlas.
Empirical research against `vectorize-io/hindsight@main`. Companion to PR #1126 (item iii — multi-tenancy).

---

## Bottom line (one-paragraph executive)

Viktor's four-way domain mapping (Decision→World, Artifact→Experience, AntiPattern→Opinion, TaskContext→Observation) maps onto Hindsight primitives with **three direct hits and one wrapper-required gap**. Decision/Artifact map onto Hindsight's native `type="world"` / `type="experience"` fact distinction at the `retain()` call site; TaskContext maps onto `observations` with evidence-grounding and freshness signals already built in; AntiPattern → Opinion is the one gap — Hindsight has no native "Opinion" primitive, but observation evolution + bank-level **disposition** traits + the "Anti-Pattern Graveyard as node type" idea from `eleven_agreed_positions` #11 give us the building blocks for a thin domain wrapper. Trace/audit semantics are NATIVELY supported: OTel distributed tracing on every operation, observations preserve "raw facts always" so the supersession history is reconstructible, the `tenant` log field provides per-tenant audit segmentation. **Spike verdict: FAVOURABLE with one domain-wrapper to build (AntiPattern→Opinion) and two citation gaps in the substantive_lock to verify (CARA + position 11 mapping reference).**

---

## Notes — canonical key values (per audit-dispatch checklist `_orchestrator.md`)

`ceo:memory_abstraction_layer_v1` queried 2026-05-24 ahead of authoring (updated 2026-05-24T15:12Z). Verbatim subset pasted so reviewers can cross-check.

### Position 3 — six query primitives

> "Six query primitives: Ingest, Recall, Synthesize, Supersede, Trace, Delete"

### Position 11 (referenced by the dispatch as carrying Viktor's mapping)

> "Surviving design ideas adopted: Semantic Router, git2 vector sync, Anti-Pattern Graveyard as node type, Impact Radius via Temporal Signals"

**Citation gap surfaced.** The dispatch states "Viktor's domain mapping (Decision→World, Artifact→Experience, AntiPattern→Opinion, TaskContext→Observation) … in `ceo:memory_abstraction_layer_v1` eleven_agreed_positions #11". Position 11 as quoted above does not contain that four-way mapping. The mapping IS in the dispatch text (and the spike proceeds from it as the working artefact), but the canonical-key citation needs verification — either position 11 has been updated since this spike or the mapping lives outside the canonical key. Surfaced for Elliot / Viktor reconciliation.

### Substantive_lock — TEMPR/CARA wrapper claim

> "V1 primitives as thin domain wrappers around Hindsight TEMPR + CARA"

**Empirical:** TEMPR is documented (`hindsight-docs/docs/developer/retrieval.md` — "Hindsight solves this with TEMPR — four complementary strategies that run in parallel"). CARA is NOT mentioned in the public developer docs. Either CARA is an internal-only Hindsight concept, a synthesis term Viktor/Aiden coined for the reflect/belief-update path, or a planned-but-not-yet-shipped subsystem. Surfaced for Viktor confirmation.

### Aiden gate A item (vi) — this spike

> "A: Hindsight spike completes favourable with verbatim findings to #ceo BEFORE Phase 2 build starts"

### Five_converged_decisions_locked — Trace primitive

> "trace_primitive: V1 scope (not deferred); regulatory necessity for HIPAA/legal-privilege/audit-trail verticals"

---

## Mapping table — Viktor's four node types onto Hindsight primitives

| MAL V1 node type | Viktor's Hindsight primitive | Empirical fit | Trace/audit shape | Verdict |
| --- | --- | --- | --- | --- |
| **Decision** | World | DIRECT — `retain()` exposes explicit `type="world"` for facts about people/places/things. "Alice works at Google" is a world fact. Decisions about external state (who chose what, what was concluded about whom) map cleanly. | Decision-as-world-fact gets the standard observation evolution: supersession when contradicted, full raw-fact history retained, OTel trace on every retain call. | ✅ DIRECT |
| **Artifact** | Experience | DIRECT — `retain()` exposes `type="experience"` for "conversations and events" (e.g. "I recommended Python to Alice"). Artifacts ARE events with provenance (who produced what, in which session). | Experience-fact carries actor + temporal context natively. Reflect-time citations pull from these. | ✅ DIRECT |
| **AntiPattern** | Opinion | **GAP — no native Opinion primitive.** Closest Hindsight analogs: (a) bank-level **disposition traits** (Skepticism/Literalism/Empathy, scale 1-5) that shape `reflect()` reasoning, (b) **observation refinement** when contradictory evidence arrives, (c) the "Anti-Pattern Graveyard as node type" idea already adopted in `eleven_agreed_positions` #11. | Disposition is per-bank not per-node. Observation refinement preserves history but treats supersession as evolution, not as a separate "anti-pattern" surface. | ⚠️ WRAPPER REQUIRED |
| **TaskContext** | Observation | DIRECT — Hindsight `observations` are "consolidated knowledge built from multiple facts" with evidence-grounding, proof count, freshness signals (stable/strengthening/weakening/new/stale), and **history preserved when refined**. TaskContext is exactly an observation about agent-task interaction. | Each observation tracks supporting source memories with exact quotes; proof count; freshness trend. Raw facts always preserved per docs: "you can trace back to see what was originally stated and when it was corrected." | ✅ DIRECT |

---

## Trace / audit semantics — per-node-type evidence

### Per-operation audit (all four node types)

`hindsight-docs/docs/developer/monitoring.md` documents OpenTelemetry distributed tracing on every `retain` / `recall` / `reflect` call, plus Prometheus metrics:

| Metric | Type | Labels |
| --- | --- | --- |
| `hindsight.operation.duration` | Histogram | `operation`, `bank_id`, `source`, `budget`, `max_tokens`, `success` |
| `hindsight.operation.total` | Counter | `operation`, `bank_id`, `source`, `budget`, `max_tokens`, `success` |

Plus the JSON-log `tenant` field (Finding 5 in `hindsight_spike_item_3_multitenancy.md`) — per-tenant audit segmentation is first-class.

**Trace primitive (MAL V1 five_converged_decisions_locked) → covered.** HIPAA / legal-privilege / accounting audit-trail requirements need: timestamp, actor, change-diff, provenance chain. Hindsight delivers timestamp + actor (via OTel span attributes) + tenant (via log field) + provenance (via observation source-memory references with exact quotes). Change-diff for observation evolution is reconstructible from the preserved raw facts.

### Per-node-type audit specifics

**Decision (world facts):** `retain()` extraction captures the why/how/what-it-means alongside the fact. Quoted from `retain.md`: "Hindsight doesn't just store what was said — it captures **why**, **how**, and **what it means**." Causation chains are preserved at the extraction layer, queryable at recall.

**Artifact (experience facts):** Experiences are events with actor + temporal binding. Reflect citations identify which memory was used. Provenance is queryable per-experience.

**AntiPattern (opinion — wrapper):** This is the gap. The wrapper would need to:
- Store the AntiPattern as a domain-tagged observation (via the `entity_labels` mechanism per `configuration.md`: "Entity labels are configured per bank via the bank config API, not as global environment variables — each bank can have its own controlled vocabulary")
- Maintain a supersession edge to the world/experience fact it contradicts
- Surface "Anti-Pattern Graveyard" as a queryable view (observations tagged `entity_label="anti-pattern"`)
- Honour the "supersession-via-AntiPattern V1" approach from `eleven_agreed_positions` #4

This is buildable today on top of Hindsight's existing primitives. ~50-100 LoC of domain wrapper + tests, sequenced at Phase 2 build (not blocking the spike).

**TaskContext (observation):** Native. Each observation already tracks supporting source memories with exact quotes, proof count, freshness signal, and history preservation across refinement. The MAL V1 Trace primitive can read observation evolution directly — no wrapper needed.

---

## Verify native evidence-provenance per-node + per-Decision-causation-chain

### Per-node provenance (queryable today)

From `observations.mdx`:

> "Every observation references the specific memories (with quotes) that support it"

The Reflect agent's response includes citations: "Returns which memories and observations were used" + "Validates citations — only IDs that were actually retrieved can be cited". This means **every Reflect output is citation-grounded** at the engine level, not a post-hoc LLM convention.

### Per-Decision causation-chain (queryable today)

`retain.md` advertises this explicitly:

> "**Enables: 'Why did this happen?' → trace reasoning chains**"

Combined with the rich extraction (facts + emotions + reasoning), Decision-as-world-fact carries the causation context inline. A `recall("Why did Alice join Google?")` returns the reasoning, not just the fact.

### Cross-Decision causation chain

For multi-step causation ("Decision A led to Decision B led to Decision C") the natural Hindsight pattern is the **observation graph** — observations connect via shared entities; the Reflect agent's `expand` tool walks these connections. The graph-search strategy in TEMPR is one of the four parallel retrievals. So multi-hop causation is supported, but is operationally a recall pattern rather than an explicit causation-edge type.

If MAL V1 wants explicit Decision→Decision causation edges (rather than entity-shared inferred edges), that's a Phase 2 wrapper-extension item. Surfaced.

---

## Gap analysis — imperfect mappings

### Gap 1 — AntiPattern → Opinion (wrapper required)

Documented above. **Remediation:** thin domain wrapper using `entity_labels` + observation supersession. ~50-100 LoC at Phase 2 build. Does NOT change MAL V1 primitives; does NOT require Hindsight changes; does NOT block Phase 2.

### Gap 2 — Explicit Decision→Decision causation edges (operational pattern, not native edge type)

Hindsight infers causation via entity-graph traversal + the recall reasoning chain. If MAL V1 needs explicit causation edges (vs inferred), that's a Phase 2 wrapper-extension item.

**Remediation options:**
- (a) Accept inferred causation (operational, no wrapper) — Reflect's `expand` tool walks the entity graph at query time
- (b) Add explicit Decision→Decision edges in the MAL V1 wrapper layer (small JSONB column extension on the wrapper's bookkeeping table; no Hindsight schema change)
- (c) Use the "Impact Radius via Temporal Signals" approach from `eleven_agreed_positions` #11 — already adopted

Recommendation: (a) ship V1, evaluate at first production review whether (b) or (c) is needed. The reflect-time recall already meets the regulatory audit-trail requirement; explicit edges would be an optimisation, not a correctness gate.

### Gap 3 — "CARA" citation in substantive_lock

CARA is referenced in `substantive_lock` ("thin domain wrappers around Hindsight TEMPR + CARA") but is not in the public Hindsight developer docs. TEMPR is solidly documented; CARA needs Viktor confirmation — is it an internal Hindsight module name, a synthesis term for the reflect/disposition path, or a planned subsystem? Surfaced for ratification reconciliation.

### Gap 4 — Citation in dispatch ("position 11 carries Viktor's mapping")

Position 11 of `eleven_agreed_positions` does not contain the four-way mapping the dispatch cites. Working hypothesis: the mapping lives outside the canonical key (in a Viktor deliberation transcript or a separate `project_*.md` memory file) and the dispatch summarised it. The mapping itself is sensible and this spike validates it empirically; the citation should be corrected to point at the actual source.

---

## What the MAL V1 wrapper layer must do (consolidated)

After this spike + spike item (iii):

1. **Decision wrapper** — calls `retain(type="world", ...)`; passes through extraction; no domain logic needed.
2. **Artifact wrapper** — calls `retain(type="experience", ...)`; passes through; no domain logic needed.
3. **TaskContext wrapper** — reads `observations` (via `recall` → observation filter); no wrapper logic needed beyond filter shape.
4. **AntiPattern wrapper** — `retain()` with `entity_label="anti-pattern"` + a supersession edge to the contradicted fact; queryable via `recall(entity_label="anti-pattern")` for the Anti-Pattern Graveyard view. ~50-100 LoC.
5. **Trace primitive** — reads OTel spans + observation source-citations + `tenant` log field. Composition not new infrastructure. Honours the Aiden gate D requirement ("Trace primitive empirically reconstructible via end-to-end audit-log integration test per real node").
6. **MCP swappability** — Honoured (Aiden gate E). The wrapper sits above the TenantExtension; agents call MCP tools that hit the wrapper layer.

Total wrapper-code surface estimate for V1: **300-500 LoC** spread across 4 thin wrappers + the Trace composition. None of these block the spike clearance.

---

## Sequencing implication for Phase 2 build

With items (iii) (this PR's companion) + (vi) (this PR) both FAVOURABLE:

- The substantive_lock survives both spikes with **two recommended amendments**:
  - Item 2 (deployment topology — from item iii): tier-keyed Topology B/A/Hybrid
  - Item 4 (TEMPR + CARA): verify CARA citation; if internal-only, replace with the reflect/disposition path name
- The eleven_agreed_positions survive unchanged.
- Aiden's six Phase-2 build gates remain achievable: Hindsight provides A, native multi-tenancy support feeds the architecture doc B, the `entity_labels` mechanism enables C/D, MCP swappability is the existing extension boundary (E), the migration_runner aligns with the schema-per-tenant mechanism (F).
- One new follow-up: build the AntiPattern→Opinion domain wrapper (50-100 LoC) at Phase 2 build start.

---

## Evidence trail

All findings sourced from `vectorize-io/hindsight@main` as of 2026-05-24.

| File | Finding | Quote anchor |
| --- | --- | --- |
| `hindsight-docs/docs/developer/retain.md` | `type="world"` / `type="experience"` fact distinction | "Hindsight distinguishes between **world** facts (about others) and **experience** (conversations and events)" |
| `hindsight-docs/docs/developer/retain.md` | Causation extraction at retain time | "captures **why**, **how**, and **what it means**" + "Enables: 'Why did this happen?' → trace reasoning chains" |
| `hindsight-docs/docs/developer/observations.mdx` | Native observation primitive with evidence-grounding | "Each observation tracks its supporting evidence (with exact quotes), a proof count, and a computed freshness trend, and is refined rather than overwritten" |
| `hindsight-docs/docs/developer/observations.mdx` | History preservation = audit trail | "raw facts are always preserved, so you can trace back to see what was originally stated and when it was corrected" |
| `hindsight-docs/docs/developer/reflect.mdx` | Bank-level disposition traits | "Skepticism / Literalism / Empathy (scale 1-5)" + "Shapes reasoning based on the bank's personality traits" |
| `hindsight-docs/docs/developer/reflect.mdx` | Citation-grounded reasoning | "Validates citations — only IDs that were actually retrieved can be cited" |
| `hindsight-docs/docs/developer/retrieval.md` | TEMPR — 4-strategy parallel retrieval | "Hindsight solves this with **TEMPR** — four complementary strategies that run in parallel" |
| `hindsight-docs/docs/developer/monitoring.md` | OTel distributed tracing | "OpenTelemetry distributed tracing" + `hindsight.operation.duration` Histogram |
| `hindsight-docs/docs/developer/configuration.md` | Per-bank `entity_labels` vocabulary | "Entity labels are configured per bank via the bank config API, not as global environment variables — each bank can have its own controlled vocabulary" |
| `hindsight-docs/docs/developer/configuration.md` | Per-tenant log segmentation | `tenant` in JSON log field allow-list |

---

## Spike status

- Item (vi) — Viktor's domain mapping + Trace/audit preservation: **FAVOURABLE** with one domain wrapper (AntiPattern→Opinion) sequenced at Phase 2 build start + two citation gaps surfaced (CARA + position 11).
- Aiden gate A item (vi): **CLEARED** pending Aiden + Max concur on this finding.
- Combined with item (iii) PR #1126: 2 of 6 spike items now have FAVOURABLE write-ups (i/ii/iv/v are other agents' or pending).

When all 6 land, Elliot will batch the Phase 2.1 findings into the Dave-surfacing for canonical-key amendments + Gate A go/no-go.
