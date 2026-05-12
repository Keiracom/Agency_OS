# src/cognee — Agency OS Cognee Wrapper

**Sole call surface** for the [Cognee](https://github.com/topoteretes/cognee) knowledge-graph + memory layer. All Cognee usage in the Agency OS codebase MUST import from `src.cognee.client`. Direct `import cognee` outside this module is forbidden (LAW XII Skills-First; keeps tenant naming + agent provenance consistent).

## When to use

Reach for this wrapper when you need:

- **Knowledge graph storage** with semantic search over agent activity / domain facts
- **Cross-agent memory** scoped to a tenant (org+app) with per-agent provenance
- **LLM-extracted entity / relationship retrieval** (Gemini 2.5 Flash via Cognee's LiteLLM bridge as of 2026-05-12)

Don't use it for: raw key-value caching (Redis), structured business data (Supabase tables), or short-term session state (`public.agent_memories`).

## API

All functions are `async`. Import:

```python
from src.cognee.client import add, search, cognify, memify
```

### Tenant + agent encoding

Every call is scoped by three IDs:

- `org_id` — top-level tenant (e.g. `keiracom_platform`)
- `app_id` — sub-tenant within an org (e.g. `agency_os`)
- `agent_id` — writing agent (e.g. `aiden`, `max`, `orion`)

Internally encoded as:

```
dataset_name = f"{org_id}__{app_id}"          # "keiracom_platform__agency_os"
node_set     = [f"agent:{agent_id}", ...extras]  # ["agent:aiden", "test"]
```

Every chunk you `add()` carries the writing agent's tag automatically. `search()` can optionally filter to a specific agent.

### Calls

```python
# Add content with caller-supplied extra tags
await add(
    "Some fact about the codebase.",
    org_id="keiracom_platform", app_id="agency_os",
    agent_id="aiden", node_set=["audit", "phase0"],
)

# Process pending adds into the knowledge graph + embeddings
await cognify()

# Optional second-pass memory enrichment over the cognified graph
await memify()

# Semantic search across all agents in this org+app
results = await search(
    "What discovery endpoint do we use?",
    org_id="keiracom_platform", app_id="agency_os",
)

# Or scope to a single agent's writes
results = await search(
    "What did aiden touch in Phase 0?",
    org_id="keiracom_platform", app_id="agency_os", agent_id="aiden",
)
```

`add()` requires `agent_id` (provenance is mandatory on writes). `search()` makes it optional (defaults to all-agents).

## Configuration

Wrapper is **provider-agnostic**. Backing stores + LLM are read from `/home/elliotbot/.config/agency-os/.env`:

| Concern    | Env var(s)                                | Value (2026-05-12)              |
|------------|-------------------------------------------|---------------------------------|
| LLM        | `LLM_PROVIDER`, `LLM_MODEL`, `GEMINI_API_KEY` | gemini / gemini-2.5-flash    |
| Embedding  | `EMBEDDING_PROVIDER`, `EMBEDDING_MODEL`   | gemini / text-embedding-004     |
| Vector DB  | `VECTOR_DB_PROVIDER`, `VECTOR_DB_URL`     | pgvector on `$SUPABASE_DB_URL`  |
| Relational | `DB_PROVIDER`, `DB_URL`                   | sqlalchemy on `$SUPABASE_DB_URL`|
| Graph DB   | `GRAPH_DB_PROVIDER`, `GRAPH_DB_PATH`      | kuzu / `~/clawd/cognee_graph/`  |

Cognee's own HTTP API server runs as `systemd --user cognee.service` on `127.0.0.1:8000` (separate from this wrapper — wrapper calls the SDK in-process).

## Smoke test

```bash
python3 scripts/cognee_smoke.py
```

Drives the directive's `add → cognify → search` sequence + asserts the two Phase 0 conditions. Exit code 0 (pass) / 2 (fail). See the script docstring for override flags.

## Extending

Add new methods to `src/cognee/client.py` only — never bypass with a direct `import cognee` elsewhere. Patterns for Phase 2+:

- `delete(node_set, *, org_id, app_id)` — soft-delete chunks matching a tag
- `update(content, *, chunk_id)` — replace a specific chunk's content
- `prune(*, org_id, app_id, older_than)` — bulk-clean stale chunks per tenant

Each extension MUST:

1. Accept `org_id` + `app_id` (tenant scoping) — no global ops
2. Encode through the same `_dataset_name` + `_agent_node_set` helpers if it touches writes
3. Add unit tests with mocked Cognee SDK to `tests/cognee/test_client.py`

## See also

- `scripts/cognee_smoke.py` — Phase 0 verify runner
- `scripts/cognee_ingest.py` — batch ingestion (Max, Phase 1)
- `continuous_ingest.py` — continuous hook ingestion (Orion, Phase 1)
- `/home/elliotbot/.config/systemd/user/cognee.service` — API server unit
