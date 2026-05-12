# Cognee Internals — Phase 0/1 Reference

Source: `topoteretes/cognee` @ main (read 2026-05-12). Citations are file paths + line ranges, raw fetched.

## Q1 — What `cognee.cognify()` actually does

Entry: `cognee/api/v1/cognify/cognify.py::cognify()`. After ontology config it calls `get_default_tasks()` (or `get_temporal_tasks()` if `temporal_cognify=True`), then `run_pipeline(tasks, datasets, user, ...)` via the pipeline executor (background or blocking).

`get_default_tasks()` returns 5 ordered Tasks:

1. **`classify_documents`** — deterministic. Types raw Data records into typed Document subclasses.
2. **`extract_chunks_from_documents`** — deterministic. Uses `TextChunker` (default) or LangchainChunker; chunk-size auto-derived from `min(embedding_max, llm_max // 2)`.
3. **`extract_graph_and_summarize`** — **LLM**. Per-chunk: entity/relationship extraction into `graph_model` (default `KnowledgeGraph`) + hierarchical summary. Batched (`chunks_per_batch`, default 100). Both calls go via `LLMGateway.acreate_structured_output`.
4. **`add_data_points`** — deterministic. Persists nodes + edges to the graph DB and embeddings to the vector DB. Optionally embeds full triplets if `cognify_config.triplet_embedding`.
5. **`extract_dlt_fk_edges`** — deterministic. Pulls foreign-key edges out of ingested structured (DLT) data and writes them as graph edges.

Net LLM calls per ingest: **~`N_chunks × 2`** (extraction + summarization, both via Instructor structured output). Steps 1, 2, 4, 5 are pure compute / DB I/O.

Source: https://github.com/topoteretes/cognee/blob/main/cognee/api/v1/cognify/cognify.py

## Q2 — `cognee.memify()` vs `cognify()`

Entry: `cognee/modules/memify/memify.py::memify()` (router at `cognee/api/v1/memify/routers/get_memify_router.py`).

memify operates on the **existing graph**, not raw data. If `data` is omitted, it pulls a `memory_fragment` via `brute_force_triplet_search.get_memory_fragment(node_type, node_name)` and feeds that fragment into the pipeline.

The pipeline is just `[*extraction_tasks, *enrichment_tasks]` — both lists user-overridable. Defaults come from `cognee/memify_pipelines/memify_default_tasks.py`:

- **Extraction defaults:** `extract_feedback_qas`, `extract_agent_trace_feedbacks` (LLM, deriving Q&A pairs from agent traces).
- **Enrichment defaults:** `apply_frequency_weights`, `persist_sessions_in_knowledge_graph`, `create_triplet_embeddings`, `apply_feedback_weights` (deterministic — re-weighting and re-embedding the subgraph).

Key flags differ from cognify: `use_pipeline_cache=False`, `incremental_loading=False` → memify always re-runs the targeted subgraph.

Source: https://github.com/topoteretes/cognee/blob/main/cognee/modules/memify/memify.py

## Q3 — KuzuDB query syntax

Kuzu uses **openCypher** (with extensions). Python:

```python
import kuzu
db = kuzu.Database("./graph_dir")
conn = kuzu.Connection(db)
df = conn.execute("MATCH (n:Entity) RETURN count(*) AS c").get_as_df()
```

Three validation queries we'll need:

**(a) Count nodes per dataset** — Kuzu requires an explicit node-table label; the dataset is encoded into a property (`dataset_id`):
```cypher
MATCH (n) WHERE n.dataset_id = $did RETURN label(n) AS table, count(*) AS n GROUP BY table;
```

**(b) List edges of one node by name:**
```cypher
MATCH (n {name: $name})-[r]->(m) RETURN type(r) AS rel, m.name AS dst, m.id AS dst_id;
```

**(c) Variable-length path between two named entities:**
```cypher
MATCH p = (a {name: $a})-[*1..6]-(b {name: $b}) RETURN p LIMIT 5;
```

Kuzu-specific: node tables are typed (`CREATE NODE TABLE`); shortestPath uses `*shortest` (e.g. `[*shortest 1..6]`) rather than Neo4j's `shortestPath()` function. Cognee instantiates tables in its Kuzu adapter — read `cognee/infrastructure/databases/graph/kuzu/` before assuming table names.

Sources: https://docs.kuzudb.com/ · https://github.com/kuzudb/kuzu

## Q4 — Dataset/namespace model (validates Aiden's wrapper)

Datasets live in a **relational** store (SQLAlchemy `Dataset` model: `id, name, owner_id, tenant_id`). Graph nodes/edges are scoped to a dataset via runtime context, not by label.

`get_unique_dataset_id(dataset_name, user)` → `uuid5(NAMESPACE_OID, f"{dataset_name}{user.id}{user.tenant_id}")` (modern) or `uuid5(..., f"{dataset_name}{user.id}")` (legacy fallback if a legacy row exists). The pipeline then binds that UUID via `set_database_global_context_variables(dataset.id, dataset.owner_id)` before reads/writes.

**Implication for `dataset_name = f"{org_id}__{app_id}"`:**
- Safe at the *name* level — different `(org, app)` strings always produce different `dataset_id` UUIDs.
- But **isolation comes from `user.id` + `user.tenant_id`, not from the string**. If every Keiracom-side tenant writes as the same Cognee `User`, the namespace string alone won't isolate them — they'll share `owner_id` and `tenant_id`, so an attacker who knows the org_id could pass that `dataset_name` and read the row. The wrapper must mint a distinct Cognee `User` per Keiracom tenant (or set `user.tenant_id = org_id`) for true isolation.
- `resolve_authorized_user_datasets` runs a permission check (`get_authorized_existing_datasets(..., "write", user)`) so cross-user reads are blocked at the auth layer regardless.

Source: https://github.com/topoteretes/cognee/blob/main/cognee/modules/data/methods/get_unique_dataset_id.py

## Q5 — Gemini 2.5 Flash via LiteLLM

Cognee does **NOT** plain-text-parse Gemini output. The Gemini adapter (`cognee/infrastructure/llm/structured_output_framework/litellm_instructor/llm/gemini/adapter.py`) builds the client as:

```python
self.aclient = instructor.from_litellm(
    litellm.acompletion, mode=instructor.Mode(self.instructor_mode)
)
# default_instructor_mode = "json_mode"
```

So all extraction goes through **Instructor `json_mode`** layered on `litellm.acompletion`. For Gemini, json_mode passes a `response_format` / `response_mime_type=application/json` plus a schema derived from the Pydantic `response_model`. This is Gemini's structured-output path — not native function-calling, but schema-enforced JSON with Instructor retrying on validation failures. Quality should be comparable to function-calling for KnowledgeGraph-shaped output.

The framework is switchable: setting `llm_config.structured_output_framework="BAML"` routes through BAML instead (`cognee/infrastructure/llm/structured_output_framework/baml/`), which generates type-safe extraction functions per schema.

Source: https://github.com/topoteretes/cognee/blob/main/cognee/infrastructure/llm/structured_output_framework/litellm_instructor/llm/gemini/adapter.py · https://github.com/topoteretes/cognee/blob/main/cognee/infrastructure/llm/LLMGateway.py

---

**Highest-leverage finding for Phase 0/1:** Q4 — `dataset_name` string alone does NOT isolate tenants. Aiden's wrapper must provision a Cognee `User`-per-Keiracom-tenant (or set `tenant_id = org_id`) or all data shares one owner. Flag this in the wrapper PR before smoke validation.
