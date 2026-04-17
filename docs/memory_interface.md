# Semantic Memory Interface Contract — v1

Stable API any agent codes against to store/retrieve memories from the shared semantic memory layer. Ratified 2026-04-17 as part of Wave 2 (memory layer + scout).

## Module
`src.memory`

## Storage backend
Supabase Postgres table `public.agent_memories` with pgvector `vector(1536)` embedding column. Model: OpenAI `text-embedding-3-small`.

---

## Public API

### `store(callsign, source_type, content, metadata=None, tags=None) -> uuid.UUID`

Embed `content` via OpenAI, write row to `agent_memories`.

**Parameters:**
- `callsign: str` — bot writing the memory (`aiden` / `elliot` / `scout` / any future)
- `source_type: str` — must be one of the valid values below
- `content: str` — memory body (gets embedded + stored verbatim)
- `metadata: dict | None` — structured data (stored as `jsonb`)
- `tags: list[str] | None` — flat tags for non-semantic filtering

**Returns:** `uuid.UUID` of the inserted row.

**Raises:**
- `ValueError` — invalid `source_type`
- `RateLimitExceeded` — daily write cap reached
- `RuntimeError` — OpenAI or Supabase failure (wraps underlying exception)

---

### `retrieve(query, n=10, types=None, callsigns=None, min_similarity=0.7) -> list[Memory]`

Embed `query`, cosine search, return top-N above threshold.

**Parameters:**
- `query: str` — natural-language search text
- `n: int` — max results (default 10)
- `types: list[str] | None` — filter to these `source_type` values
- `callsigns: list[str] | None` — filter to these authors
- `min_similarity: float` — reject below this cosine similarity (default 0.7)

**Returns:** `list[Memory]`, sorted by similarity desc.

---

### `retrieve_by_tags(tags, n=10, mode='any') -> list[Memory]`

Tag-based filter, no embedding cost.

**Parameters:**
- `tags: list[str]` — tags to match
- `mode: Literal["any", "all"]` — `any` = match at least one (default); `all` = match every tag
- `n: int` — max results (default 10)

**Returns:** `list[Memory]`, sorted by `created_at` desc. `similarity` field is `None`.

---

## `Memory` dataclass

```python
@dataclass(frozen=True)
class Memory:
    id: uuid.UUID
    callsign: str
    source_type: str
    content: str
    metadata: dict
    tags: list[str]
    created_at: datetime
    similarity: float | None  # None for tag-based retrieval
```

---

## Valid `source_type` values

| value | meaning |
|-------|---------|
| `research` | external knowledge ingested (Reddit, paper, competitor intel, scout finding) |
| `decision` | a call Dave made or the agents formally agreed on |
| `pattern` | a recurring behaviour / design pattern worth remembering |
| `skill` | a reusable technique / helper / procedure |
| `dave_confirmed` | Dave personally verified this fact as current truth |
| `verified_fact` | agents cross-validated via two independent sources |

Invalid values raise `ValueError` at `store()` time.

---

## Rate limits

- **Daily write cap:** 5000 rows / UTC day (overridable via `MEMORY_WRITE_CAP` env var)
- **Embedding calls:** 1 per `store`, 1 per `retrieve`. Simple in-memory cache (~1h TTL) dedupes repeated identical queries.
- **Expected cost:** ~$0.0001 per embed, ~$0.10/day at cap.
- On cap hit, `store()` raises `RateLimitExceeded`; caller chooses retry/drop.

---

## Usage pattern — session-start retrieval (recommended)

```python
from src.memory import retrieve

# At session load, fetch context relevant to current directive:
context = retrieve(
    f"directive: {current_directive_title}. recent work: {recent_prs}",
    n=20,
    min_similarity=0.65,
)
# Surface to operator or prepend to context window.
```

---

## Usage pattern — scout (agent-3) write path

```python
from src.memory import store

# Scout writes each research finding as it lands:
mem_id = store(
    callsign="scout",
    source_type="research",
    content=full_finding_text,
    metadata={
        "source_url": url,
        "published_at": published_iso,
        "relevance_score": score,
    },
    tags=["au_smb", "competitor", competitor_name, "channel_benchmarks"],
)
```

Scout should write one row per distinct finding (not one-row-per-brief). Ingestion cadence is scout's choice; memory layer caps via the daily write limit.

---

## Usage pattern — dave_confirmed

```python
# When Dave confirms something factual in the group chat:
store(
    callsign="<whoever is capturing>",
    source_type="dave_confirmed",
    content="Agency OS target ACV band is $500-2000/mo AUD (Dave confirmed 2026-04-17).",
    tags=["pricing", "acv", "product"],
)
```

`dave_confirmed` memories are treated as high-trust and survive any future schema/pruning policy.

---

## Schema reference (migration lives in `supabase/migrations/NNN_agent_memories.sql`)

```sql
CREATE TABLE public.agent_memories (
  id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  callsign        text NOT NULL,
  source_type     text NOT NULL,
  content         text NOT NULL,
  embedding       vector(1536) NOT NULL,
  metadata        jsonb NOT NULL DEFAULT '{}'::jsonb,
  tags            text[] NOT NULL DEFAULT '{}',
  created_at      timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX agent_memories_embedding_idx
  ON public.agent_memories
  USING ivfflat (embedding vector_cosine_ops)
  WITH (lists = 100);

CREATE INDEX agent_memories_callsign_idx  ON public.agent_memories (callsign);
CREATE INDEX agent_memories_source_type_idx ON public.agent_memories (source_type);
CREATE INDEX agent_memories_tags_idx      ON public.agent_memories USING GIN (tags);
CREATE INDEX agent_memories_created_at_idx ON public.agent_memories (created_at DESC);
```

---

## Versioning

- **Contract version: v1.** Breaking API changes require a v2 module (parallel namespace) + migration plan.
- Schema additions (new columns) that don't break existing callers are NOT breaking; add them in `src.memory` same-version.
- New `source_type` values: NOT breaking (validated at app layer); update this doc + enum simultaneously.

---

## Out of scope for v1 (reference, not promises)

- Automatic session-start retrieval via Claude hook/skill — manual `retrieve()` call only.
- TTL / memory pruning — all memories retained indefinitely in v1.
- Embedding model hot-swap — locked to `text-embedding-3-small`.
- Async batch writes — synchronous embed-then-insert per call.
- Cross-project memory federation — single Supabase project only.
