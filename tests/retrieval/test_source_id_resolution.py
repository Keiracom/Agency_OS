"""KEI-75 source_id resolution regression tests.

Locks the citation source_id precedence order: explicit source_id > chunk_id >
source_path > file_path > doc_id > umbrella kei > collection fallback. Atlas's
audit found the old ordering produced 'KEI-73' (the umbrella tag) on every
Wave 3 citation; the new ordering points at the chunk that actually matched.
"""

from __future__ import annotations

from unittest.mock import patch

from src.retrieval import agent_query, orchestrator


def _mk_node(text: str, score: float, metadata: dict) -> orchestrator.RetrievedNode:
    return orchestrator.RetrievedNode(
        text=text,
        score=score,
        metadata=metadata,
        collection="Discoveries",
    )


def _outcome(nodes: tuple[orchestrator.RetrievedNode, ...]) -> orchestrator.RetrievalOutcome:
    return orchestrator.RetrievalOutcome(
        nodes=nodes, bypass_rerank=True, rerank_reason="test", rerank_elapsed_ms=0
    )


def _query_top_source(metadata: dict) -> str:
    nodes = (_mk_node("hit", 0.95, metadata),)
    with patch(
        "src.retrieval.agent_query.orchestrator.retrieve_with_outcome",
        return_value=_outcome(nodes),
    ):
        result = agent_query.query("anything?", agent="test", min_score=0.50)
    return result.citations[0].source_id


def test_explicit_source_id_wins_over_chunk_id():
    md = {"source_id": "explicit-1", "chunk_id": "chunk-2", "kei": "KEI-73"}
    assert _query_top_source(md) == "explicit-1"


def test_chunk_id_preferred_over_source_path():
    md = {"chunk_id": "abc-123", "source_path": "docs/audits/x.md", "kei": "KEI-73"}
    assert _query_top_source(md) == "abc-123"


def test_source_path_preferred_over_kei_umbrella():
    md = {"source_path": "docs/audits/sonar_audit.md", "kei": "KEI-73"}
    assert _query_top_source(md) == "docs/audits/sonar_audit.md"


def test_file_path_preferred_over_kei_umbrella():
    md = {"file_path": "src/retrieval/agent_query.py", "kei": "KEI-73"}
    assert _query_top_source(md) == "src/retrieval/agent_query.py"


def test_kei_used_when_no_specific_identifier_present():
    md = {"kei": "KEI-73"}
    assert _query_top_source(md) == "KEI-73"


def test_collection_fallback_when_metadata_empty():
    md = {}
    assert _query_top_source(md) == "discoveries:unknown"


def test_parent_path_falls_back_to_section_when_missing():
    md = {"chunk_id": "c-1", "section": "Anti-hallucination guard"}
    nodes = (_mk_node("hit", 0.95, md),)
    with patch(
        "src.retrieval.agent_query.orchestrator.retrieve_with_outcome",
        return_value=_outcome(nodes),
    ):
        result = agent_query.query("q?", agent="test", min_score=0.50)
    assert result.citations[0].parent_path == "Anti-hallucination guard"
