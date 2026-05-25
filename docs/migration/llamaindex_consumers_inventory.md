# LlamaIndex Consumers Inventory — Pre-Hindsight-Cutover

**Authored 2026-05-25 by Atlas** as input to the Hindsight cutover work (step 5-B in Aiden PR #1141's sequence). When each consumer below is redirected to the MAL primitives via Hindsight, LlamaIndex's pin in `requirements.txt` can be lifted and the package fully removed.

---

## Why this doc exists (correcting the canonical analysis)

The Aiden + Elliot + Viktor concur in the Phase 2.1 / wave-2 LlamaIndex deliberation concluded that LlamaIndex was **"orchestration-only with no data store; safe to remove."** Elliot dispatched a retirement task to Atlas on that basis.

**Atlas HOLD 2026-05-25** found the analysis was wrong about production usage. Empirical evidence: `bd claim` (the hot-path agent context-injection flow) reaches LlamaIndex via lazy imports. The dispatch was paused, the direction switched to **option (c) — pin + freeze short-term + redirect during Hindsight cutover long-term**, and this doc was written so the deliberation's canonical analysis is corrected.

The lazy-import pattern (`from llama_index.* import X` placed inside function bodies rather than at module top) is what masked the production dependency in the original analysis — a `grep "^from llama_index"` would show nothing at module level. The real surface is reached at *call time*, not *import time*.

**Discipline lesson** (worth capturing in a feedback memory): lazy-import patterns hide dependency analysis. The next "is X safe to remove?" deliberation should grep both top-level AND function-body imports to avoid the same trap.

---

## The five LlamaIndex import sites

All five are in `src/retrieval/` and all use lazy imports (inside functions, not module-top).

| File:line | What is imported | What it does |
| --- | --- | --- |
| `src/retrieval/orchestrator.py:46` | `from llama_index.core import VectorStoreIndex` | Used in `_build_index()` to construct a LlamaIndex `VectorStoreIndex` over a Weaviate collection. Backbone of the retrieval pipeline. |
| `src/retrieval/orchestrator.py:47` | `from llama_index.core.storage.storage_context import StorageContext` | Wraps the `WeaviateVectorStore` so `VectorStoreIndex.from_vector_store()` can attach. Required by the LlamaIndex API. |
| `src/retrieval/orchestrator.py:73` | `from llama_index.core import Document` | Used in `index_document()` to wrap raw text into a LlamaIndex `Document` for embedding + indexing. |
| `src/retrieval/weaviate_store.py:109` | `from llama_index.vector_stores.weaviate import WeaviateVectorStore` | The LlamaIndex adapter that talks to Weaviate. The whole reason LlamaIndex is in the dependency tree — direct `weaviate-client` calls would replace this. |
| `src/retrieval/embeddings.py:37` | `from llama_index.embeddings.huggingface import HuggingFaceEmbedding` | The LlamaIndex wrapper around HuggingFace BGE embeddings. Used by `get_embed_model()`. Direct `sentence-transformers` (or the upcoming TEI sidecar from Orion PR #1127 Path 3) would replace this. |

---

## The production call chain (proves the consumers are live)

```
scripts/tasks_cli.py:581                         # cmd_claim — the bd claim flow
  └─> src.retrieval.agent_query.query()          # agent_query.py:22 imports orchestrator
        └─> src.retrieval.orchestrator.retrieve_with_outcome()
              ├─> _build_index()                 # orchestrator.py:46-47 — VectorStoreIndex + StorageContext
              ├─> weaviate_store.get_vector_store()
              │     └─> weaviate_store.py:109    # WeaviateVectorStore
              └─> embeddings.get_embed_model()
                    └─> embeddings.py:37          # HuggingFaceEmbedding

scripts/orchestrator/claim_context_injector.py:95  # same agent_query.query() pattern
  └─> src.retrieval.agent_query.query()          # same downstream chain as above
```

Both `cmd_claim` and `claim_context_injector` fire on every `bd claim` invocation (one is the CLI command, the other is the lazy-injection helper that runs alongside). LlamaIndex is loaded by every bd-claim that has retrieval context to inject — not orchestration-only, not data-store-absent. It is the live retrieval backend.

---

## Per-consumer redirect plan (Hindsight cutover step 5-B)

Each row maps a current LlamaIndex call site to the Hindsight equivalent that should replace it. Owner = the agent who should claim that piece of the cutover; the existing Atlas wrappers (PR #1134) + MCP tools (PR #1136) provide most of the surface.

| Site | Current | Replace with | Owner | Notes |
| --- | --- | --- | --- | --- |
| `orchestrator.py:46-47` `_build_index()` | `VectorStoreIndex.from_vector_store(StorageContext(...))` over Weaviate | Direct `HindsightClient.recall(bank_id=...)` calls; the bank-scoped index lives inside Hindsight already. No per-call "build index" step needed because Hindsight maintains the bank. | TBD (Atlas/Orion) | Net code simplification — `_build_index` goes away entirely. |
| `orchestrator.py:73` `index_document()` | `Document(text=...)` then `index.insert(doc)` | `HindsightClient.retain(bank_id, items=[{content, tags, metadata}])` — what the wrappers in PR #1134 already do. | TBD | The wrapper-layer surface IS the replacement; agents call wrappers instead of orchestrator directly. |
| `weaviate_store.py:109` `WeaviateVectorStore` | LlamaIndex's Weaviate adapter | The Hindsight server already owns its Weaviate-equivalent storage (Postgres + pgvector + HNSW per `eleven_agreed_positions` #2). Direct Weaviate access via this adapter goes away when consumers cut over to Hindsight. | TBD | If anything still needs RAW Weaviate access post-cutover (e.g. legacy data not yet migrated), use direct `weaviate-client` calls — the indexer-base pattern in `scripts/orchestrator/indexer_base.py` shows the shape. |
| `embeddings.py:37` `HuggingFaceEmbedding` | LlamaIndex wrapper over HF | TEI sidecar serving BGE-small-en-v1.5 per Orion PR #1127 Path 3 — the embedding layer is moved out of process and accessed via the sidecar HTTP API. Hindsight talks to the sidecar; consumers don't need a local embedder at all. | Orion (already in flight) | Removes both LlamaIndex AND in-process sentence-transformers from the retrieval path. |

---

## Sequencing within the Hindsight cutover

1. **Now (this PR):** pin LlamaIndex to `0.14.22` + `1.6.0` + `0.7.0` in `requirements.txt`. No upgrade risk while the cutover designs.
2. **Hindsight cutover step 5-A (Aiden PR #1141 sequence):** the hand-migration scripts for the 5 classes in PR #1141 land. This brings the Hindsight-side data store online for production use.
3. **Hindsight cutover step 5-B:** consumer redirect — each row in the table above gets a small PR replacing the LlamaIndex call with the Hindsight equivalent. Wrapper layer (PR #1134) + MCP tools (PR #1136) are the surface.
4. **Hindsight cutover step 5-C:** after all 5 consumers are redirected + integration tests confirm no LlamaIndex import fires in production, the pins in `requirements.txt` get removed, the `src/retrieval/` files get either deleted or trimmed to a thin shim that proxies to Hindsight, and `llama_index` leaves the dependency tree.

Total cutover effort estimate for the LlamaIndex piece alone: **~2-3 days** spread across the 4 consumer redirects (each is small but each needs its own test parity check). Cannot be done in the 1-2h dispatch box that the original retirement task was scoped for — exactly why option (c) is the right short-term move.

---

## Out of scope for this inventory

1. **Cognee retirement** — separate retirement (step 1 of the three-retirement plan per Aiden PR #1141). Cognee + LlamaIndex are sibling retirements but on different tracks.
2. **Weaviate retirement** — also separate. Weaviate stays as the storage backend behind Hindsight (LlamaIndex was just the adapter ABOVE Weaviate, not the store itself). Per `eleven_agreed_positions` #2 the storage substrate is Postgres + pgvector; the Weaviate-to-Postgres data migration is its own PR sequence.
3. **The `flashrank` package** in `requirements.txt` — reranker, used by `orchestrator.retrieve_nodes`. Not LlamaIndex-dependent but currently colocated with the LlamaIndex pin block. Stays for now; its replacement is the Hindsight built-in `ms-marco-MiniLM-L-6-v2` reranker (per PR #1130 smoke spike) once the consumer cutover is done.

These three belong on the Hindsight-cutover roadmap, not in this inventory.
