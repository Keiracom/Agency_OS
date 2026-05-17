"""KEI-49 — LlamaIndex OSS retrieval orchestration over Weaviate.

Read-side of the Keiracom Collective Intelligence layer. Agents query this
module; writes flow through `src/memory/` and the dedicated indexers in
`scripts/orchestrator/`. The boundary is deliberate per Scout's design
(docs/wave2/kei49_llamaindex_orchestration_research.md §3) — co-locating
read and write modules pulled write deps into agent hot paths.

Public entry point:
    from src.retrieval import query
    result = query("how was the Cognee memory cap solved?", agent="max")

Returns a `QueryResult` carrying the synthesised answer plus cited
sources. `citation_required=True` is the default — empty results return
`answer=""` rather than synthesising unsupported text (anti-hallucination
guard per KEI-55).
"""

from src.retrieval.agent_query import Citation, QueryResult, query

__all__ = ["Citation", "QueryResult", "query"]
