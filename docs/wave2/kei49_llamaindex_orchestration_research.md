# KEI-49 — LlamaIndex OSS retrieval orchestration: research + design

**Author:** scout (Sonnet 4.6, research clone)
**Date:** 2026-05-14
**Status:** research-phase deliverable; build is Orion's after KEI-46 (Weaviate install) ships.
**Linear:** [KEI-49](https://linear.app/keiracom/issue/KEI-49)
**Depends on:** KEI-46 (Weaviate install on Vultr Sydney) — currently not shipped.

This document is the design spec that lets Orion lift KEI-49 into a PR
without having to re-derive the architecture. It captures the questions
that don't fit in the Linear KEI body — concrete file layout, query
interface signatures, Cognee coexistence rules, observability hooks,
and the smoke-test plan that will gate "shipped" vs "needs rework".

---

## 1. Problem framing

Without an orchestration layer, agents talking to Weaviate hit raw
nearest-neighbour search. That gives back chunks, not answers — no
re-ranking, no citation, no awareness of which collection to query, no
hierarchical fall-through (chunk → parent doc → section). Three years
of internal discoveries from agents will be eroded by precision loss.

LlamaIndex sits between the agent and Weaviate. It owns the IR
pipeline: chunking strategy, multi-collection routing, re-ranking,
citation, and the agent-facing query API.

---

## 2. Where LlamaIndex sits in the stack

```
┌─────────────────────────────────────────────────────────┐
│ Agent (Claude Opus / Sonnet via Anthropic API)          │
│   • bd claim KEI-N                                       │
│   • injects last 500 tokens of prior knowledge           │
└───────────────┬─────────────────────────────────────────┘
                │  query("how was Cognee memory cap solved?",
                │         agent="max", collections=[...])
                ▼
┌─────────────────────────────────────────────────────────┐
│ LlamaIndex orchestration (NEW — KEI-49)                  │
│   ┌───────────────────────────────────────────────────┐ │
│   │ CitationQueryEngine                                │ │
│   │   ├─ Router: pick collections by agent + query    │ │
│   │   ├─ HierarchicalNodeParser: chunks ↔ parents     │ │
│   │   ├─ Re-ranker (FlashRank or CrossEncoder)        │ │
│   │   └─ Response synth w/ inline citations            │ │
│   └───────────────────────────────────────────────────┘ │
│   ┌───────────────────────────────────────────────────┐ │
│   │ Index writers (one per collection)                 │ │
│   │   • discoveries — written by tasks_cli complete    │ │
│   │   • decisions — written by webhook (KEI ratified)  │ │
│   │   • code — written by repo-walker cron             │ │
│   └───────────────────────────────────────────────────┘ │
└───────────────┬─────────────────────────────────────────┘
                │  WeaviateVectorStore client (gRPC)
                ▼
┌─────────────────────────────────────────────────────────┐
│ Weaviate (KEI-46, Vultr Sydney) — storage + ANN          │
│   • discoveries collection (per KEI-55 tier rules)       │
│   • decisions collection                                 │
│   • code collection (chunked source)                     │
│   • keis collection (Linear KEI bodies)                  │
└─────────────────────────────────────────────────────────┘

                ┌──────────────────────────────────────────┐
                │ Cognee (parallel — graph reasoning only) │
                │   • multi-hop relationship traversal     │
                │   • NOT primary retrieval                │
                └──────────────────────────────────────────┘
```

Cognee is retained ONLY for multi-hop relationship traversal queries
("which KEIs are blocked by KEI-X?"). All precision retrieval flows
through LlamaIndex.

---

## 3. File layout (proposed)

```
src/retrieval/
  __init__.py
  llama_orchestrator.py     # CitationQueryEngine + router
  weaviate_store.py         # WeaviateVectorStore wrapper + auth
  chunkers.py               # HierarchicalNodeParser per content-type
  rerankers.py              # FlashRank / cross-encoder pipeline
  writers/
    __init__.py
    discoveries.py          # called by tasks_cli complete (KEI-22)
    decisions.py            # called by Linear webhook on ratified KEI
    code.py                 # called by repo-walker cron
  queries/
    agent_query.py          # the public agent-facing query() entry
    fixtures.py             # canonical smoke-test queries

tests/retrieval/
  test_llama_orchestrator.py
  test_weaviate_store.py
  test_chunkers.py
  test_writers_*.py
  test_smoke_queries.py     # acceptance-criteria smoke

scripts/
  retrieval_smoke.py        # one-shot CLI: runs all canonical queries
                            # against current Weaviate + dumps a report
```

Rationale for the `src/retrieval/` namespace (vs putting it under
`src/memory/`): retrieval is read-side; memory/* in this repo currently
houses write-side modules (sanitise, environment_hash, organise, store).
Splitting keeps the read/write boundary clean and avoids accidental
co-import that pulls write deps into agent query paths.

---

## 4. Dependency pins

```
llama-index==0.10.*                       # core
llama-index-llms-anthropic==0.1.*         # Claude Opus 4.7 backend
llama-index-vector-stores-weaviate==0.1.* # Weaviate adapter
llama-index-embeddings-huggingface==0.2.* # local embedding (no API cost)
flashrank>=0.2.7                          # CPU re-ranker, ~30ms / query
weaviate-client>=4.5,<5                   # already in scope via KEI-46
```

Why pin minor versions: the LlamaIndex 0.10 API is the stable line as
of 2026-05; the 0.11 line (released 2026-04) changed the
`VectorStoreIndex.from_documents` signature in a way that breaks the
HierarchicalNodeParser integration. Pin tight until Orion has bandwidth
to migrate.

Embedding model decision: prefer `BAAI/bge-small-en-v1.5` (local CPU,
no API cost, 384-dim) over OpenAI's `text-embedding-3-small`. Saves
~$15-30/mo at projected query volume and avoids cross-vendor data
exfiltration. Cost note: re-indexing the full corpus on first ship is
a one-time ~$0 instead of ~$8-12 if we'd used OpenAI.

---

## 5. Chunking strategy by content-type

Different content needs different chunkers. HierarchicalNodeParser
gives us "chunk → parent → grandparent" linkage so a precise match on
a small chunk still surfaces the surrounding context block.

| Collection  | Parser                                | Chunk size | Parent levels |
|-------------|---------------------------------------|------------|---------------|
| discoveries | SentenceWindowNodeParser              | 3 sents    | window=10     |
| decisions   | MarkdownNodeParser (heading-aware)    | section    | h1 → h2 → h3  |
| code        | CodeSplitter (tree-sitter, language=py)| 200 lines  | function → module |
| keis        | SemanticSplitter (paragraph)          | ~400 tok   | KEI → section |

Hierarchical fall-through: if a small chunk matches but the
re-ranker confidence is < 0.6, automatically widen to the parent
node. This avoids the "great match, useless without context" failure
mode that plain ANN exhibits.

---

## 6. Re-ranker pipeline

The retrieval response is a two-stage pipeline:

1. **First pass (Weaviate ANN, k=20)** — pure vector similarity.
2. **Re-rank (FlashRank, ms-marco-MiniLM-L-12-v2)** — CPU cross-encoder
   that scores each of the 20 chunks against the original query. Keep
   top 5 by re-rank score.

Why FlashRank not Cohere/Voyage Rerank: $0 marginal cost, runs in
~30ms on a 4 vCPU box, comparable NDCG@5 to Cohere on our internal
evals (per Anthropic's 2026-03 retrieval study cited in
research/listener_v3_techniques.md).

Fallback path: if FlashRank latency exceeds 200ms (cold-start or
container OOM), bypass the re-rank and use raw Weaviate scores. Log
the bypass to `audit_logs.retrieval_events` so we can spot if it
becomes common.

---

## 7. Public query API (agent-facing)

```python
# src/retrieval/queries/agent_query.py

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class Citation:
    source_id: str        # discovery_id | decision_id | file_path:line
    collection: Literal["discoveries", "decisions", "code", "keis"]
    score: float          # re-rank score, 0..1
    excerpt: str          # 80-char snippet
    parent_path: str      # hierarchical context path


@dataclass(frozen=True)
class QueryResult:
    answer: str                          # synthesised response
    citations: tuple[Citation, ...]      # always non-empty if answer!=""
    elapsed_ms: int
    bypass_rerank: bool                  # FlashRank fallback fired


def query(
    text: str,
    *,
    agent: str,
    collections: tuple[str, ...] = ("discoveries", "decisions", "keis"),
    max_tokens: int = 500,
    citation_required: bool = True,
) -> QueryResult: ...
```

Design notes:
- `citation_required=True` is the default. If no citation passes the
  0.6 re-rank threshold, return `answer=""` rather than fabricate.
  This is the anti-hallucination guard the discovery-validation KEI
  (KEI-55) requires.
- `max_tokens=500` matches the bd-claim-injection ceiling from
  KEI-57 (already shipped). LlamaIndex's response synthesis is
  configured to fit within that envelope.
- `agent` is recorded in `audit_logs.retrieval_events` so we can
  see retrieval patterns per-agent (e.g. "Aiden queries 'cgroup'
  N times/day, Orion queries 'tmux' M times/day").

---

## 8. Cognee coexistence

Two retrieval surfaces live side-by-side. Decision tree for agents:

```
agent has a query
    │
    ├─ "Find facts about X"           → LlamaIndex (precision)
    ├─ "List discoveries by Y agent"  → LlamaIndex (filter + retrieve)
    ├─ "Which KEIs depend on KEI-N?"  → Cognee (multi-hop graph)
    ├─ "Show me how A and B relate"   → Cognee (relationship traversal)
    └─ "Summarise recent activity"    → LlamaIndex (with date filter)
```

Both share Weaviate's underlying vectors — LlamaIndex via
WeaviateVectorStore, Cognee via its existing Weaviate adapter. The
two clients use distinct gRPC channels; no concurrency conflict on
Weaviate's side (it serialises writes anyway).

Cognee's role narrows from "primary memory layer" to "graph
reasoning sidecar". The migration off Cognee for precision retrieval
is what KEI-49 unblocks; Cognee's graph layer is retained per
ratified decision (research/cognee_internals_decision.md from
earlier in this session).

---

## 9. Observability

Every `query()` call records to `public.audit_logs.retrieval_events`:

```sql
CREATE TABLE IF NOT EXISTS public.retrieval_events (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  occurred_at TIMESTAMPTZ DEFAULT NOW(),
  agent       TEXT NOT NULL,
  query_text  TEXT NOT NULL,                 -- truncated to 200 chars
  collections TEXT[] NOT NULL,
  k_initial   INT  NOT NULL,                 -- 20 default
  k_returned  INT  NOT NULL,                 -- after re-rank
  elapsed_ms  INT  NOT NULL,
  bypass_rerank BOOL DEFAULT FALSE,
  top_citation_id TEXT,                       -- discovery_id / file_path:line
  top_score   NUMERIC(4,3)
);
CREATE INDEX ON public.retrieval_events (agent, occurred_at DESC);
CREATE INDEX ON public.retrieval_events (occurred_at DESC) WHERE bypass_rerank = TRUE;
```

Dashboards (Grafana, later KEI): queries/agent/day, p50/p95 latency,
bypass-rerank rate, top-5 unmatched queries (citation_required=True
returning empty answers — flags where the corpus is thin).

---

## 10. Smoke-test plan (the acceptance criteria)

`scripts/retrieval_smoke.py` runs eight canonical queries against
the current Weaviate corpus and asserts the response shape. Orion's
PR ships when all eight pass against a freshly indexed corpus.

| # | Query                                                          | Expected top-citation collection | Min top-score |
|---|----------------------------------------------------------------|----------------------------------|---------------|
| 1 | "where is the Slack relay implemented?"                        | code                             | 0.65          |
| 2 | "how was the Cognee memory cap solved?"                        | discoveries OR decisions         | 0.60          |
| 3 | "what does KEI-22 deliver?"                                    | keis                             | 0.70          |
| 4 | "which file owns the concur-gate regex?"                       | code                             | 0.65          |
| 5 | "Australia-first dollar currency rule"                         | decisions                        | 0.55          |
| 6 | "scout governance rule for self-merge"                         | decisions OR discoveries         | 0.55          |
| 7 | "how should agents handle Vercel rate-limit failures?"         | discoveries                      | 0.50          |
| 8 | "give me a wrong query that has no answer in the corpus"       | empty answer expected            | n/a           |

Query 8 verifies the anti-hallucination path — `citation_required=True`
returns `answer=""` rather than synthesising something unsupported.

---

## 11. Build sequence (when KEI-46 ships)

Recommended order for Orion's PR(s) to keep each step verifiable:

1. **PR 1** — scaffolding: `src/retrieval/__init__.py`, dependency pins
   in `pyproject.toml`, empty `weaviate_store.py` with one-shot
   `health_check()` that pings Weaviate and returns version.
   Smoke: `python -c "from src.retrieval.weaviate_store import health_check; print(health_check())"`.

2. **PR 2** — chunkers + writers (discoveries collection only).
   `tasks_cli complete` is wired to call `writers.discoveries.write()`.
   Smoke: complete a fake task, query Weaviate directly, see the doc.

3. **PR 3** — agent query API (`queries/agent_query.py`) with the 8
   smoke queries. CitationQueryEngine + FlashRank. This is the visible
   deliverable.

4. **PR 4** — code-collection writer + repo-walker cron. Higher risk
   (large index, embedding cost) so isolated last.

Each PR ships independently with the smoke harness. KEI-49 closes when
PR 3 lands; PR 1/2/4 can land in any order before that.

---

## 12. Risks + mitigations

| Risk                                                          | Likelihood | Mitigation                                                                                       |
|---------------------------------------------------------------|------------|--------------------------------------------------------------------------------------------------|
| Weaviate v4 client breaks vs LlamaIndex's expected v3 shape   | medium     | Pin `llama-index-vector-stores-weaviate==0.1.*` and `weaviate-client>=4.5,<5`; smoke PR 1 first. |
| FlashRank cold-start latency >200ms                            | high       | Bypass path returns raw ANN; warm-pool the reranker via systemd `Type=notify` worker.            |
| Re-index of full corpus blocks agents                          | medium     | Repo-walker writes to a `code_staging` collection; atomic swap to `code` on completion.          |
| Cognee + LlamaIndex compete for Weaviate writes                | low        | Both serialise on the gRPC channel; cap concurrent writers to 2 in `weaviate_store.py`.          |
| Empty corpus on first query (PR 3 before PR 2 ships)           | low        | Query 8 fixture exercises the empty-corpus path; the rest assume `tasks_cli` has run ≥1×.        |

---

## 13. Open questions for Orion

These are the decisions I can't make from research alone — they need
Orion's runtime context when KEI-46 lands:

1. Embedding model: `BAAI/bge-small-en-v1.5` (proposed) vs
   `text-embedding-3-small` (cost trade). Pick after first cost
   measurement against a sample corpus.
2. FlashRank vs `BAAI/bge-reranker-base` (heavier, more accurate).
   Bench both on the 8 smoke queries and pick by NDCG@5 — keep the
   loser as a fallback module.
3. Cron cadence for the code-collection re-indexer (PR 4): hourly
   (cheap, often stale) vs on-merge webhook (always fresh, more
   plumbing).
4. Whether to gate `query()` behind a feature flag during PR 3 so
   agents can be cut over one-by-one rather than all at once.

---

## 14. Scout handoff note

This is a research-phase deliverable. Per IDENTITY.md, scout's lane is
research + diagnosis; the build is Orion's after KEI-46 (Weaviate
install) ships. Marking the tasks-table row KEI-49 as `done` with the
understanding that "done" here means *research-phase done* — the
build phase is a separate dispatched task to Orion.

If Orion wants the design changed before lifting it, comment on this
doc or post in #execution; scout is on-call for design clarifications.
