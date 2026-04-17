# Memory Interface — v1 (typed, no embeddings)

## Overview

`src/memory` is the agent memory layer for multi-agent knowledge compounding.

**v1 contract:** text + tag + source_type filtering via PostgREST. No embeddings, no pgvector, no OpenAI dependency. Embeddings are deferred to v2 when measured retrieval-miss evidence justifies the complexity cost.

---

## Module

```
src/memory/
    __init__.py      — public re-exports
    types.py         — Memory dataclass, VALID_SOURCE_TYPES, RateLimitExceeded
    client.py        — lazy Supabase URL + headers from env
    ratelimit.py     — daily write counter (file-backed, MEMORY_WRITE_CAP)
    store.py         — write one memory row
    retrieve.py      — filter-based read (type / callsign / tag / text / time)
    recall.py        — high-level recall grouped by source_type (/recall Telegram)
```

---

## Dataclass

```python
@dataclass(frozen=True)
class Memory:
    id: uuid.UUID
    callsign: str
    source_type: str
    content: str
    typed_metadata: dict
    tags: list[str]
    valid_from: datetime
    valid_to: datetime | None
    created_at: datetime
```

---

## Valid source_type values

```python
VALID_SOURCE_TYPES = {
    "pattern", "decision", "test_result", "reasoning", "skill",
    "daily_log", "dave_confirmed", "verified_fact", "research",
}
```

---

## Public API

### `store()`

```python
def store(
    callsign: str,
    source_type: str,
    content: str,
    typed_metadata: dict | None = None,
    tags: list[str] | None = None,
    valid_from: datetime | None = None,
    valid_to: datetime | None = None,
) -> uuid.UUID
```

Writes one memory row. Returns the inserted row UUID.

Raises:
- `ValueError` — source_type not in VALID_SOURCE_TYPES
- `RateLimitExceeded` — daily cap hit (default 5000, env `MEMORY_WRITE_CAP`)
- `RuntimeError` — Supabase HTTP error or connection failure

### `retrieve()`

```python
def retrieve(
    types: list[str] | None = None,
    callsigns: list[str] | None = None,
    tags: list[str] | None = None,
    tag_mode: Literal["any", "all"] = "any",
    since: datetime | None = None,
    until: datetime | None = None,
    content_contains: str | None = None,
    n: int = 20,
) -> list[Memory]
```

General PostgREST filter query. Ordered `created_at DESC`. Limit `n`.

Filter operators used internally:
- types: `source_type=in.(t1,t2)`
- callsigns: `callsign=in.(c1,c2)`
- tags any: `tags=ov.{t1,t2}`
- tags all: `tags=cs.{t1,t2}`
- text: `content=ilike.*term*`
- time range: `created_at=gte.ISO` / `created_at=lte.ISO`

### `retrieve_by_tags()`

```python
def retrieve_by_tags(
    tags: list[str],
    n: int = 20,
    mode: Literal["any", "all"] = "any",
) -> list[Memory]
```

Convenience wrapper — tags only.

### `recall()`

```python
def recall(topic: str | None = None, n: int = 20) -> dict[str, list[Memory]]
```

High-level retrieval backing the `/recall` Telegram command. Returns memories grouped by `source_type`.

- `topic` provided: queries `content_contains=topic` + `tags=[topic]`, deduplicates by id, groups by source_type.
- `topic=None`: returns recent high-value memories (`pattern`, `decision`, `skill`, `dave_confirmed`), grouped by source_type.

---

## Rate limit

File-backed daily counter: `/tmp/agent-memory-writes-YYYYMMDD.count`. Resets at UTC midnight. Cap: env `MEMORY_WRITE_CAP` (default 5000). Raises `RateLimitExceeded` when cap is reached.

---

## Errors

| Exception | When |
|-----------|------|
| `ValueError` | `source_type` not in `VALID_SOURCE_TYPES` |
| `RateLimitExceeded` | daily write cap hit |
| `RuntimeError` | Supabase non-2xx or `httpx.HTTPError` |

---

## Schema (migration 102)

Table: `public.agent_memories`

| Column | Type | Notes |
|--------|------|-------|
| id | uuid | PK, gen_random_uuid() |
| callsign | text | agent identifier |
| source_type | text | one of VALID_SOURCE_TYPES |
| content | text | raw text content |
| typed_metadata | jsonb | arbitrary structured metadata |
| tags | text[] | GIN-indexed |
| valid_from | timestamptz | DEFAULT now() |
| valid_to | timestamptz | nullable — expiry |
| created_at | timestamptz | DEFAULT now() |

Migration file: `supabase/migrations/102_agent_memories.sql`

**Do not apply to live Supabase** — Dave applies post-merge.

---

## v2 roadmap

Add semantic search via embeddings when retrieval-miss evidence justifies. Candidate approach: `pgvector` extension + `embedding vector(1536)` column + `HNSW` index. The `store()` and `retrieve()` interfaces are designed to extend without breaking callers — `typed_metadata` can carry embedding metadata in a backward-compatible way. No timeline set; v1 ships first and we measure.
