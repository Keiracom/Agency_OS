"""Unit tests for src/retrieval/spawn_recall — Wave 3 spawn-time recall hook.

Mocks agent_query.query so tests run without Hindsight / Weaviate. Locks
the contract: structured query build, top-3 truncation, fail-open on any
error, block formatting + KEI-55 char clamp, and env injection semantics.
"""

from __future__ import annotations

from unittest.mock import patch

from src.retrieval import agent_query, spawn_recall


def _mk_result(*citations: agent_query.Citation) -> agent_query.QueryResult:
    return agent_query.QueryResult(
        answer="x",
        citations=tuple(citations),
        elapsed_ms=1,
        bypass_rerank=True,
    )


def _cit(
    source_id: str, *, collection: str = "Decisions", excerpt: str = "ex"
) -> agent_query.Citation:
    return agent_query.Citation(
        source_id=source_id,
        collection=collection,
        score=0.9,
        excerpt=excerpt,
    )


# ─── _build_query ──────────────────────────────────────────────────────────


def test_build_query_includes_task_type_and_brief_head():
    q = spawn_recall._build_query("pr_review", "Review PR #1238 for hook compliance")
    assert "pr_review" in q
    assert "Review PR #1238" in q
    assert "failed" in q and "canonical" in q and "superseded" in q


def test_build_query_truncates_brief_to_100_chars():
    long_brief = "A" * 250
    q = spawn_recall._build_query("build", long_brief)
    assert "A" * 100 in q
    assert "A" * 101 not in q


def test_build_query_defaults_blank_task_type_to_build():
    assert "For a build task" in spawn_recall._build_query("", "do thing")


# ─── query_for_spawn ─────────────────────────────────────────────────────────


def test_query_for_spawn_returns_formatted_citations():
    res = _mk_result(_cit("D-1", collection="Decisions", excerpt="canonical X"))
    with patch("src.retrieval.agent_query.query", return_value=res):
        out = spawn_recall.query_for_spawn("build", "ship feature")
    assert out == ["[D-1 · Decisions] canonical X"]


def test_query_for_spawn_caps_at_top_k():
    cits = [_cit(f"D-{i}") for i in range(10)]
    with patch("src.retrieval.agent_query.query", return_value=_mk_result(*cits)):
        out = spawn_recall.query_for_spawn("build", "brief")
    assert len(out) == spawn_recall.TOP_K == 3


def test_query_for_spawn_empty_citations_returns_empty():
    with patch("src.retrieval.agent_query.query", return_value=_mk_result()):
        assert spawn_recall.query_for_spawn("build", "brief") == []


def test_query_for_spawn_fails_open_on_exception():
    with patch("src.retrieval.agent_query.query", side_effect=RuntimeError("hindsight down")):
        assert spawn_recall.query_for_spawn("build", "brief") == []


def test_query_for_spawn_passes_budget_and_agent_label():
    res = _mk_result(_cit("D-1"))
    with patch("src.retrieval.agent_query.query", return_value=res) as mq:
        spawn_recall.query_for_spawn("deliberation", "decide arch")
    _, kwargs = mq.call_args
    assert kwargs["agent"] == spawn_recall.SPAWN_RECALL_AGENT
    assert kwargs["max_tokens"] == spawn_recall.MAX_TOKENS == 500
    assert kwargs["k_returned"] == spawn_recall.TOP_K


# ─── build_prior_context_block ───────────────────────────────────────────────


def test_block_empty_for_no_results():
    assert spawn_recall.build_prior_context_block([]) == ""


def test_block_has_header_and_bullets():
    block = spawn_recall.build_prior_context_block(["[D-1 · Decisions] a", "[D-2 · Keis] b"])
    assert block.startswith(spawn_recall.BLOCK_HEADER)
    assert "- [D-1 · Decisions] a" in block
    assert "- [D-2 · Keis] b" in block


def test_block_clamped_to_max_chars():
    big = ["X" * 5000]
    block = spawn_recall.build_prior_context_block(big)
    assert len(block) <= spawn_recall.MAX_BLOCK_CHARS


# ─── inject_prior_context ────────────────────────────────────────────────────


def test_inject_adds_env_key_when_results_present():
    with patch.object(spawn_recall, "query_for_spawn", return_value=["[D-1 · Decisions] x"]):
        out = spawn_recall.inject_prior_context({}, task_type="build", task_brief="b")
    assert spawn_recall.PRIOR_CONTEXT_ENV_KEY in out["env"]
    assert "[D-1 · Decisions] x" in out["env"][spawn_recall.PRIOR_CONTEXT_ENV_KEY]


def test_inject_preserves_existing_env_and_other_kwargs():
    base = {"command": "claude", "env": {"EXISTING": "1"}}
    with patch.object(spawn_recall, "query_for_spawn", return_value=["[D-1 · Decisions] x"]):
        out = spawn_recall.inject_prior_context(base, task_type="build", task_brief="b")
    assert out["command"] == "claude"
    assert out["env"]["EXISTING"] == "1"
    assert spawn_recall.PRIOR_CONTEXT_ENV_KEY in out["env"]
    # original dict not mutated (copy semantics)
    assert spawn_recall.PRIOR_CONTEXT_ENV_KEY not in base["env"]


def test_inject_unchanged_when_no_results():
    base = {"command": "claude"}
    with patch.object(spawn_recall, "query_for_spawn", return_value=[]):
        out = spawn_recall.inject_prior_context(base, task_type="build", task_brief="b")
    assert out == base


def test_inject_fails_open_on_exception():
    base = {"command": "claude"}
    with patch.object(spawn_recall, "query_for_spawn", side_effect=RuntimeError("boom")):
        out = spawn_recall.inject_prior_context(base, task_type="build", task_brief="b")
    assert out == base
