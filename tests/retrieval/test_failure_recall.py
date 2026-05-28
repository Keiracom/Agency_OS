"""Wave 6 — negative-example recall as a first-class query type.

Covers `agent_query.query_failures` (flag gate, negative framing, top-3 cap,
fail-open) and the `spawn_recall` wiring (a separate 'Past failures to avoid'
block combined with positive recall, and byte-identical positive-only output
when RETRIEVAL_FAILURE_RECALL_ENABLED is off — no regression on the Wave 3
path). All mocked; no Hindsight / network.
"""

from __future__ import annotations

from unittest.mock import patch

from src.retrieval import agent_query, spawn_recall


def _result(*triples: tuple[str, str, str]) -> agent_query.QueryResult:
    """Build a QueryResult from (source_id, collection, excerpt) triples."""
    cits = tuple(
        agent_query.Citation(source_id=s, collection=c, score=0.8, excerpt=e)
        for (s, c, e) in triples
    )
    return agent_query.QueryResult(answer="x", citations=cits, elapsed_ms=1, bypass_rerank=True)


# ─── failure_recall_enabled ───────────────────────────────────────────────────


def test_failure_recall_disabled_by_default(monkeypatch):
    monkeypatch.delenv(agent_query.FAILURE_RECALL_ENABLED_ENV, raising=False)
    assert agent_query.failure_recall_enabled() is False


def test_failure_recall_enabled_truthy_values(monkeypatch):
    for val in ("1", "true", "TRUE", "yes", "on"):
        monkeypatch.setenv(agent_query.FAILURE_RECALL_ENABLED_ENV, val)
        assert agent_query.failure_recall_enabled() is True
    monkeypatch.setenv(agent_query.FAILURE_RECALL_ENABLED_ENV, "no")
    assert agent_query.failure_recall_enabled() is False


# ─── _build_failure_query ─────────────────────────────────────────────────────


def test_build_failure_query_has_framing_terms_and_task_type():
    q = agent_query._build_failure_query("pr_review", "Review PR #1252 atom gate")
    assert "pr_review" in q
    assert "Review PR #1252" in q
    for term in agent_query.FAILURE_FRAMING_TERMS:
        assert term in q


def test_build_failure_query_truncates_brief():
    q = agent_query._build_failure_query("build", "A" * 500)
    assert "A" * agent_query.FAILURE_BRIEF_PREFIX_CHARS in q
    assert "A" * (agent_query.FAILURE_BRIEF_PREFIX_CHARS + 1) not in q


def test_build_failure_query_defaults_blank_task_type():
    assert "build" in agent_query._build_failure_query("", "do thing")


# ─── query_failures ───────────────────────────────────────────────────────────


def test_query_failures_returns_empty_when_disabled(monkeypatch):
    monkeypatch.delenv(agent_query.FAILURE_RECALL_ENABLED_ENV, raising=False)
    # query() must not even be reached when the flag is off.
    with patch.object(agent_query, "query", side_effect=AssertionError("queried while disabled")):
        assert agent_query.query_failures("build", "brief") == []


def test_query_failures_formats_top_3_when_enabled(monkeypatch):
    monkeypatch.setenv(agent_query.FAILURE_RECALL_ENABLED_ENV, "1")
    res = _result(
        ("F-1", "Discoveries", "ulimit -v false-OOM; use cgroup MemoryMax"),
        ("F-2", "Decisions", "Slack relay restricted not decommissioned"),
        ("F-3", "Keis", "min_score hard filter dropped all citations"),
        ("F-4", "Discoveries", "fourth result beyond top-3"),
    )
    with patch.object(agent_query, "query", return_value=res) as mq:
        out = agent_query.query_failures("build", "brief")
    assert out == [
        "[F-1 · Discoveries] ulimit -v false-OOM; use cgroup MemoryMax",
        "[F-2 · Decisions] Slack relay restricted not decommissioned",
        "[F-3 · Keis] min_score hard filter dropped all citations",
    ]
    # Negative-framed text reached the retrieval path.
    search_text = mq.call_args.args[0]
    assert "failed" in search_text and "failure" in search_text


def test_query_failures_caps_at_custom_top_k(monkeypatch):
    monkeypatch.setenv(agent_query.FAILURE_RECALL_ENABLED_ENV, "1")
    res = _result(*[(f"F-{i}", "Discoveries", f"failure {i}") for i in range(10)])
    with patch.object(agent_query, "query", return_value=res):
        out = agent_query.query_failures("build", "brief", top_k=2)
    assert len(out) == 2


def test_query_failures_fails_open_on_exception(monkeypatch):
    monkeypatch.setenv(agent_query.FAILURE_RECALL_ENABLED_ENV, "1")
    with patch.object(agent_query, "query", side_effect=RuntimeError("hindsight down")):
        assert agent_query.query_failures("build", "brief") == []


def test_query_failures_passes_agent_label_and_k_returned(monkeypatch):
    monkeypatch.setenv(agent_query.FAILURE_RECALL_ENABLED_ENV, "1")
    with patch.object(agent_query, "query", return_value=_result(("F", "D", "e"))) as mq:
        agent_query.query_failures("deliberation", "decide arch")
    kwargs = mq.call_args.kwargs
    assert kwargs["agent"] == agent_query.FAILURE_RECALL_AGENT
    assert kwargs["k_returned"] == 3


# ─── spawn_recall failure-block builders ──────────────────────────────────────


def test_build_failure_context_block_empty_for_no_results():
    assert spawn_recall.build_failure_context_block([]) == ""


def test_build_failure_context_block_has_header_and_bullets():
    block = spawn_recall.build_failure_context_block(["[F-1 · Discoveries] x", "[F-2 · Keis] y"])
    assert block.startswith(spawn_recall.FAILURE_BLOCK_HEADER)
    assert "- [F-1 · Discoveries] x" in block
    assert "- [F-2 · Keis] y" in block


def test_build_failure_context_block_clamped_to_max_chars():
    assert (
        len(spawn_recall.build_failure_context_block(["X" * 5000])) <= spawn_recall.MAX_BLOCK_CHARS
    )


def test_query_failures_for_spawn_fails_open():
    with patch("src.retrieval.agent_query.query_failures", side_effect=RuntimeError("boom")):
        assert spawn_recall.query_failures_for_spawn("build", "brief") == []


# ─── build_spawn_context_block (combined) ─────────────────────────────────────


def test_spawn_context_block_positive_only_when_failures_empty():
    """No-regression: failures off → byte-identical to the positive-only block."""
    with (
        patch.object(spawn_recall, "query_for_spawn", return_value=["[D-1 · Decisions] canonical"]),
        patch.object(spawn_recall, "query_failures_for_spawn", return_value=[]),
    ):
        combined = spawn_recall.build_spawn_context_block("build", "brief")
        positive_only = spawn_recall.build_prior_context_block(["[D-1 · Decisions] canonical"])
    assert combined == positive_only
    assert spawn_recall.FAILURE_BLOCK_HEADER not in combined


def test_spawn_context_block_combines_positive_then_failures():
    with (
        patch.object(spawn_recall, "query_for_spawn", return_value=["[D-1 · Decisions] canonical"]),
        patch.object(
            spawn_recall, "query_failures_for_spawn", return_value=["[F-1 · Discoveries] failed X"]
        ),
    ):
        block = spawn_recall.build_spawn_context_block("build", "brief")
    assert spawn_recall.BLOCK_HEADER in block
    assert spawn_recall.FAILURE_BLOCK_HEADER in block
    assert block.index(spawn_recall.BLOCK_HEADER) < block.index(spawn_recall.FAILURE_BLOCK_HEADER)


def test_spawn_context_block_failures_only_when_positive_empty():
    with (
        patch.object(spawn_recall, "query_for_spawn", return_value=[]),
        patch.object(
            spawn_recall, "query_failures_for_spawn", return_value=["[F-1 · Discoveries] failed X"]
        ),
    ):
        block = spawn_recall.build_spawn_context_block("build", "brief")
    assert block.startswith(spawn_recall.FAILURE_BLOCK_HEADER)


def test_inject_prior_context_carries_failure_block_into_env():
    with (
        patch.object(spawn_recall, "query_for_spawn", return_value=["[D-1 · Decisions] canonical"]),
        patch.object(
            spawn_recall, "query_failures_for_spawn", return_value=["[F-1 · Discoveries] failed X"]
        ),
    ):
        out = spawn_recall.inject_prior_context({}, task_type="build", task_brief="b")
    injected = out["env"][spawn_recall.PRIOR_CONTEXT_ENV_KEY]
    assert spawn_recall.FAILURE_BLOCK_HEADER in injected
    assert "[F-1 · Discoveries] failed X" in injected
