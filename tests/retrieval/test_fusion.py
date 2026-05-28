"""Wave 5 — cross-topology fusion recall (src/retrieval/fusion.py).

Covers:
- fusion_enabled() env parsing (default off).
- _content_key dedup-key stability + whitespace normalisation.
- fused_recall: unions across ALL mapped fleet banks, dedups by content hash
  (higher score wins), ranks by score desc, honours top_k.
- Fail-open at both layers: per-collection swallow inside _gather_ann_pool,
  AND the gather-level isinstance(BaseException) guard.
- Tenant context validated fail-fast before any recall fires.
- agent_query.query() routes through fusion when the flag is on.
"""

from __future__ import annotations

import asyncio

import pytest

from src.retrieval import agent_query, fusion, orchestrator

# ---------------------------------------------------------------------------
# fusion_enabled() — flag parsing
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("val,expected", [("1", True), ("true", True), ("YES", True)])
def test_fusion_enabled_truthy(monkeypatch, val, expected):
    monkeypatch.setenv("RETRIEVAL_FUSION_ENABLED", val)
    assert fusion.fusion_enabled() is expected


@pytest.mark.parametrize("val", ["", "0", "false", "no", "off"])
def test_fusion_enabled_falsy(monkeypatch, val):
    monkeypatch.setenv("RETRIEVAL_FUSION_ENABLED", val)
    assert fusion.fusion_enabled() is False


def test_fusion_disabled_by_default(monkeypatch):
    monkeypatch.delenv("RETRIEVAL_FUSION_ENABLED", raising=False)
    assert fusion.fusion_enabled() is False


# ---------------------------------------------------------------------------
# _content_key — dedup key
# ---------------------------------------------------------------------------


def test_content_key_stable_and_whitespace_normalised():
    assert fusion._content_key("hello") == fusion._content_key("  hello  ")
    assert fusion._content_key("a") != fusion._content_key("b")


# ---------------------------------------------------------------------------
# fused_recall — union / dedup / rank
# ---------------------------------------------------------------------------


def _patch_recall_by_bank(monkeypatch, by_bank):
    """Monkeypatch orchestrator._hindsight_recall to return canned memories per bank."""
    calls: list[str] = []

    def _fake_recall(text, bank_id, *, top_k, tenant_id):
        calls.append(bank_id)
        return list(by_bank.get(bank_id, []))

    monkeypatch.setattr(orchestrator, "_hindsight_recall", _fake_recall)
    return calls


def test_fused_recall_fires_every_mapped_bank(monkeypatch):
    calls = _patch_recall_by_bank(monkeypatch, {})
    asyncio.run(fusion.fused_recall("q", orchestrator.FLEET_TENANT_SLUG, top_k=5))
    assert set(calls) == set(orchestrator.HINDSIGHT_BANK_BY_CLASS.values())


def test_fused_recall_unions_and_ranks_by_score(monkeypatch):
    _patch_recall_by_bank(
        monkeypatch,
        {
            "fleet_decisions": [{"content": "dec", "score": 0.4}],
            "fleet_keis": [{"content": "kei", "score": 0.9}],
            "fleet_agent_memories": [{"content": "mem", "score": 0.6}],
        },
    )
    out = asyncio.run(fusion.fused_recall("q", orchestrator.FLEET_TENANT_SLUG, top_k=10))
    texts = [n.text for n in out]
    assert texts == ["kei", "mem", "dec"]  # ranked by score desc across banks


def test_fused_recall_dedups_by_content_keeping_higher_score(monkeypatch):
    _patch_recall_by_bank(
        monkeypatch,
        {
            "fleet_decisions": [{"content": "shared insight", "score": 0.3}],
            "fleet_keis": [{"content": "shared insight", "score": 0.8}],
        },
    )
    out = asyncio.run(fusion.fused_recall("q", orchestrator.FLEET_TENANT_SLUG, top_k=10))
    shared = [n for n in out if n.text == "shared insight"]
    assert len(shared) == 1
    assert shared[0].score == pytest.approx(0.8)


def test_fused_recall_honours_top_k(monkeypatch):
    _patch_recall_by_bank(
        monkeypatch,
        {
            "fleet_decisions": [{"content": f"d{i}", "score": i / 10} for i in range(5)],
            "fleet_keis": [{"content": f"k{i}", "score": i / 10} for i in range(5)],
        },
    )
    out = asyncio.run(fusion.fused_recall("q", orchestrator.FLEET_TENANT_SLUG, top_k=3))
    assert len(out) == 3


# ---------------------------------------------------------------------------
# Fail-open — both layers
# ---------------------------------------------------------------------------


def test_fused_recall_fail_open_on_per_bank_recall_error(monkeypatch):
    """A bank whose _hindsight_recall raises is swallowed by _gather_ann_pool;
    the surviving banks still contribute to the union."""

    def _flaky_recall(text, bank_id, *, top_k, tenant_id):
        if bank_id == "fleet_decisions":
            raise RuntimeError("simulated bank outage")
        return [{"content": f"ok-{bank_id}", "score": 0.5}]

    monkeypatch.setattr(orchestrator, "_hindsight_recall", _flaky_recall)
    out = asyncio.run(fusion.fused_recall("q", orchestrator.FLEET_TENANT_SLUG, top_k=50))
    texts = {n.text for n in out}
    assert "ok-fleet_keis" in texts
    assert not any("fleet_decisions" in t for t in texts)


def test_fused_recall_fail_open_on_gather_level_exception(monkeypatch):
    """If _gather_ann_pool itself raises for one collection, the gather-level
    isinstance(BaseException) guard drops it and keeps the others."""
    good = [orchestrator.RetrievedNode(text="survived", score=0.7, metadata={}, collection="Keis")]

    def _selective_pool(text, collections, k_initial, weaviate_client, *, tenant_id):
        (collection,) = collections
        if collection == "Decisions":
            raise RuntimeError("pool blew up")
        return list(good) if collection == "Keis" else []

    monkeypatch.setattr(orchestrator, "_gather_ann_pool", _selective_pool)
    out = asyncio.run(fusion.fused_recall("q", orchestrator.FLEET_TENANT_SLUG, top_k=10))
    assert [n.text for n in out] == ["survived"]


# ---------------------------------------------------------------------------
# Tenant context — fail-fast
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("bad", [None, "", "   ", "tenant/../escape"])
def test_fused_recall_rejects_bad_tenant_before_any_recall(monkeypatch, bad):
    called = []
    monkeypatch.setattr(orchestrator, "_hindsight_recall", lambda *a, **kw: called.append(1) or [])
    with pytest.raises(orchestrator.MissingTenantContextError):
        asyncio.run(fusion.fused_recall("q", bad, top_k=5))
    assert called == []


# ---------------------------------------------------------------------------
# agent_query.query() integration
# ---------------------------------------------------------------------------


def test_agent_query_routes_through_fusion_when_flag_on(monkeypatch):
    monkeypatch.setenv("RETRIEVAL_FUSION_ENABLED", "1")
    monkeypatch.setattr(agent_query, "_record_event", lambda **kw: None)
    fused = [
        orchestrator.RetrievedNode(
            text="fused-hit", score=0.9, metadata={"source_id": "X1"}, collection="Keis"
        ),
    ]

    async def _fake_fused_recall(text, tenant, top_k=orchestrator.DEFAULT_K_INITIAL):
        return list(fused)

    monkeypatch.setattr(fusion, "fused_recall", _fake_fused_recall)
    # If fusion is wired, retrieve_with_outcome must NOT be called.
    monkeypatch.setattr(
        orchestrator,
        "retrieve_with_outcome",
        lambda **kw: pytest.fail("orchestrator path used while fusion flag on"),
    )
    result = agent_query.query("anything", agent="orion")
    assert result.citations
    assert result.citations[0].source_id == "X1"


def test_agent_query_uses_orchestrator_when_flag_off(monkeypatch):
    monkeypatch.delenv("RETRIEVAL_FUSION_ENABLED", raising=False)
    monkeypatch.setattr(agent_query, "_record_event", lambda **kw: None)
    used = []
    monkeypatch.setattr(
        orchestrator,
        "retrieve_with_outcome",
        lambda **kw: used.append(1) or orchestrator.RetrievalOutcome((), False, "empty_pool", 0),
    )
    monkeypatch.setattr(
        fusion, "fused_recall", lambda *a, **kw: pytest.fail("fusion used while flag off")
    )
    agent_query.query("anything", agent="orion")
    assert used == [1]


# ---------------------------------------------------------------------------
# Async/sync split — running-loop safety (Aiden re-review of PR #1249)
# ---------------------------------------------------------------------------


def _fusion_stub(monkeypatch):
    """Enable fusion + return one canned node; silence the event recorder."""
    monkeypatch.setenv("RETRIEVAL_FUSION_ENABLED", "1")
    monkeypatch.setattr(agent_query, "_record_event", lambda **kw: None)

    async def _fake(text, tenant, top_k=orchestrator.DEFAULT_K_INITIAL):
        return [
            orchestrator.RetrievedNode(
                text="hit", score=0.9, metadata={"source_id": "X1"}, collection="Keis"
            )
        ]

    monkeypatch.setattr(fusion, "fused_recall", _fake)


def test_sync_query_safe_when_called_inside_running_loop(monkeypatch):
    """The landmine: sync query() invoked from within a running event loop
    (FastAPI handler, awaited chain) must NOT raise RuntimeError from
    asyncio.run() — _run_coro_sync falls back to a worker thread."""
    _fusion_stub(monkeypatch)

    async def _driver():
        # Calling the SYNC entry point from inside a running loop.
        return agent_query.query("anything", agent="orion")

    result = asyncio.run(_driver())
    assert result.citations[0].source_id == "X1"


def test_sync_query_works_with_no_running_loop(monkeypatch):
    _fusion_stub(monkeypatch)
    result = agent_query.query("anything", agent="orion")
    assert result.citations[0].source_id == "X1"


def test_query_async_routes_through_fusion(monkeypatch):
    _fusion_stub(monkeypatch)
    monkeypatch.setattr(
        orchestrator,
        "retrieve_with_outcome",
        lambda **kw: pytest.fail("orchestrator path used while fusion flag on"),
    )
    result = asyncio.run(agent_query.query_async("anything", agent="orion"))
    assert result.citations[0].source_id == "X1"


def test_query_async_uses_orchestrator_when_flag_off(monkeypatch):
    monkeypatch.delenv("RETRIEVAL_FUSION_ENABLED", raising=False)
    monkeypatch.setattr(agent_query, "_record_event", lambda **kw: None)
    used = []

    def _spy(**kw):
        used.append(1)
        return orchestrator.RetrievalOutcome((), False, "empty_pool", 0)

    monkeypatch.setattr(orchestrator, "retrieve_with_outcome", _spy)
    monkeypatch.setattr(
        fusion, "fused_recall", lambda *a, **kw: pytest.fail("fusion used while flag off")
    )
    asyncio.run(agent_query.query_async("anything", agent="orion"))
    assert used == [1]
