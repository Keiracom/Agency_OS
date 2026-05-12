# Phase 1 Validation Queries — Pre-built `search()` Calls

Pre-built calls for Dave's directive Queries 1–4 against Aiden's wrapper:
`search(query, *, org_id, app_id, agent_id=None, node_set=None)`.

Each query lists: (a) wrapper call, (b) what the wrapper must translate to under-the-hood, (c) `SearchType` choice, (d) expected result shape, (e) pass/fail criterion.

`SearchType` source: `cognee/modules/search/types/SearchType.py`.
`cognee.search()` signature source: `cognee/api/v1/search/search.py`.

---

## Query 1 — Architecture recall

```python
result = await keira_memory.search(
    "What is the active enrichment waterfall in Agency OS?",
    org_id="keiracom",
    app_id="agency_os",
)
```

**Wrapper translation:**
```python
await cognee.search(
    query_text="What is the active enrichment waterfall in Agency OS?",
    query_type=SearchType.GRAPH_COMPLETION,
    user=user_for("keiracom"),          # per-tenant User (fixes Q4 isolation gap)
    datasets=["keiracom__agency_os"],
    top_k=10,
)
```

**Result shape:** `List[SearchResult]` with one or more conversational AI strings. With `GRAPH_COMPLETION`, each item is a generated answer string grounded in retrieved graph context (not raw nodes). The first string is the LLM completion.

**Pass criterion:** Returned string mentions at minimum 2 of: `GMB`, `ABN`, `SERP`, `LinkedIn`, `Leadmagic`. (Anchored to Active Enrichment Path in `CLAUDE.md`.) `len(result) >= 1` and `len(result[0]) > 50`.

**Fail signals:** Empty list (ingest didn't land in this dataset), "I don't have information about that" (retriever found no relevant chunks → embeddings broken), wrong product names (cross-namespace leakage → see Query 4).

---

## Query 2 — Temporal reasoning

```python
result = await keira_memory.search(
    "What changed in the Agency OS enrichment stack between April 2026 and now?",
    org_id="keiracom",
    app_id="agency_os",
)
```

**Wrapper translation:**
```python
await cognee.search(
    query_text="What changed in the Agency OS enrichment stack between April 2026 and now?",
    query_type=SearchType.TEMPORAL,
    user=user_for("keiracom"),
    datasets=["keiracom__agency_os"],
    top_k=10,
)
```

**Requires:** `cognify(..., temporal_cognify=True)` at ingest time so the temporal task pipeline runs (`extract_events_and_timestamps` + `extract_knowledge_graph_from_events`). If the data was ingested with the default (non-temporal) pipeline, `TEMPORAL` will return nothing useful — fall back to `GRAPH_COMPLETION` for narrative answers and note the gap.

**Result shape:** `List[SearchResult]` of strings. Temporal mode grounds answers in event-typed nodes with `valid_from`/`valid_to` timestamps.

**Pass criterion:** Returned string references at least one dated transition (e.g., "Apify replaced by Bright Data", "Pipeline F v2.1 introduced"). `len(result[0]) > 50` and contains a date-like token (regex `\b20(2[5-9]|3\d)\b`).

**Fail signals:** "No events found" → temporal pipeline wasn't run at ingest. Generic non-temporal answer → wrapper passed wrong `query_type`.

---

## Query 3 — Agent-scoped memory

```python
result = await keira_memory.search(
    "What feedback has scout received from CEO Dave?",
    org_id="keiracom",
    app_id="agency_os",
    agent_id="scout",
)
```

**Wrapper translation:**
```python
await cognee.search(
    query_text="What feedback has scout received from CEO Dave?",
    query_type=SearchType.GRAPH_COMPLETION,
    user=user_for("keiracom"),
    datasets=["keiracom__agency_os"],
    node_name=["scout"],                # wrapper sets this from agent_id
    node_name_filter_operator="OR",
    top_k=10,
)
```

**Wrapper contract:** `agent_id` MUST map to a `node_name` filter (or a `node_set` matching how memify persisted agent-scoped subgraphs — see `cognee.modules.engine.models.node_set.NodeSet`). Without this filter, results include other agents' feedback and the query is meaningless.

**Result shape:** `List[SearchResult]` of strings. Graph completion is restricted to traversals seeded from nodes matching `node_name=["scout"]`.

**Pass criterion:** Returned string references at least one piece of feedback tagged to scout (e.g., callsign mention, "research-only", "no Step 0"). NO mentions of other agent callsigns (atlas/orion/elliot/aiden/max) as the *subject* of feedback.

**Fail signals:** Mentions another agent as subject → filter not applied. Empty result → wrapper didn't set `node_name` or wrong seed node.

---

## Query 4 — Cross-namespace isolation (the gate)

```python
result = await keira_memory.search(
    "Agency OS enrichment stack",
    org_id="keiracom",
    app_id="hardhats",                  # different app — must NOT see agency_os data
)
```

**Wrapper translation (correct, with tenant-isolation fix):**
```python
await cognee.search(
    query_text="Agency OS enrichment stack",
    query_type=SearchType.CHUNKS,       # raw retrieval — no LLM hallucination
    user=user_for("keiracom__hardhats"), # OR same user but with tenant_id=org_id
    datasets=["keiracom__hardhats"],
    top_k=10,
)
```

**Why `CHUNKS` not `GRAPH_COMPLETION`:** completion endpoints invoke an LLM which may *hallucinate* a plausible answer even when no relevant chunks are retrieved — masking a leak. `CHUNKS` returns raw vector hits with metadata so we can verify zero matches deterministically.

**Result shape:** `List[SearchResult]` of chunk objects with `text`, `score`, `metadata.dataset_id`, `metadata.document_id`.

**Pass criterion:** `len(result) == 0`, OR every returned chunk's `metadata.dataset_id == uuid_for("keiracom__hardhats")`. Zero chunks from `keiracom__agency_os` dataset.

**Fail signals:** Any chunk with `metadata.dataset_id` matching the agency_os dataset UUID → tenant isolation broken → confirms Q4 gap in internals doc → wrapper must mint per-tenant `User` or set `user.tenant_id = org_id`.

**Why this is the load-bearing gate:** it's the only one of the four that empirically proves the wrapper's namespace encoding actually isolates data at the storage layer rather than just at the query layer. The other three queries can pass even with a broken isolation model.

---

## Common assertions across all four

```python
assert isinstance(result, list)
assert all(isinstance(r, (str, dict)) for r in result)   # SearchResult is a Pydantic model; serializes either way
```

Capture each query's raw return into `phase1_validation.json` keyed by query number for later diffing across runs. Run all four in sequence and only declare Phase 1 PASS when 1, 2, 3 return non-empty grounded answers AND 4 returns empty (or in-namespace only).
