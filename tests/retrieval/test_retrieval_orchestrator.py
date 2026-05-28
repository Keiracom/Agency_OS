"""4-layer retrieval orchestrator wiring tests.

Covers the L3/L4 stubs (identity + budget-clamp, fail-open, IS_STUB marked) and
the orchestrator that chains L1 recall → L2 rerank → L3 contradiction filter →
L4 compression into the spawn-hydration payload. L1+L2 are mocked at the
spawn_recall boundary so no live Hindsight is needed.
"""

from __future__ import annotations

import pytest

from src.retrieval import (
    compression,
    contradiction_filter,
    retrieval_orchestrator,
    spawn_recall,
)

# ── L3 contradiction filter (stub) ───────────────────────────────────────


def test_contradiction_filter_is_marked_stub_and_identity():
    assert contradiction_filter.IS_STUB is True
    assert contradiction_filter.filter_contradictions(["a", "b"]) == ["a", "b"]


def test_contradiction_filter_fail_open_on_bad_input():
    # list(None) raises inside the try → fail-open returns the input unchanged.
    assert contradiction_filter.filter_contradictions(None) is None  # type: ignore[arg-type]


# ── L4 compression (stub) ────────────────────────────────────────────────


def test_compression_is_marked_stub_and_clamps_to_budget():
    assert compression.IS_STUB is True
    out = compression.compress("x" * 100, max_tokens=10)
    assert out == "x" * 40  # 10 tokens * 4 chars/token


def test_compression_leaves_under_budget_block_intact():
    assert compression.compress("short block", max_tokens=500) == "short block"


# ── four_layer_enabled flag ──────────────────────────────────────────────


@pytest.mark.parametrize("val,expected", [("1", True), ("on", True), ("true", True)])
def test_four_layer_enabled_truthy(monkeypatch, val, expected):
    monkeypatch.setenv("RETRIEVAL_ORCHESTRATOR_4LAYER_ENABLED", val)
    assert retrieval_orchestrator.four_layer_enabled() is expected


def test_four_layer_disabled_by_default(monkeypatch):
    monkeypatch.delenv("RETRIEVAL_ORCHESTRATOR_4LAYER_ENABLED", raising=False)
    assert retrieval_orchestrator.four_layer_enabled() is False


# ── assemble_hydration_block runs all 4 layers ───────────────────────────


def test_assemble_runs_all_four_layers(monkeypatch):
    calls: list[str] = []

    monkeypatch.setattr(
        spawn_recall, "query_for_spawn", lambda tt, tb: calls.append("L1L2_pos") or ["pos-hit"]
    )
    monkeypatch.setattr(
        spawn_recall, "query_failures_for_spawn", lambda tt, tb: calls.append("L1L2_neg") or []
    )

    orig_filter = contradiction_filter.filter_contradictions
    monkeypatch.setattr(
        contradiction_filter,
        "filter_contradictions",
        lambda r: calls.append("L3") or orig_filter(r),
    )
    orig_compress = compression.compress
    monkeypatch.setattr(
        compression, "compress", lambda b, **kw: calls.append("L4") or orig_compress(b, **kw)
    )

    block = retrieval_orchestrator.assemble_hydration_block("build", "wire the orchestrator")
    assert "pos-hit" in block
    assert spawn_recall.BLOCK_HEADER in block
    # All four layers were exercised (L1+L2 recall calls, L3 on each set, L4 once).
    assert "L1L2_pos" in calls and "L1L2_neg" in calls
    assert calls.count("L3") == 2 and calls.count("L4") == 1


def test_assemble_fail_open_on_layer_error(monkeypatch):
    def _boom(tt, tb):
        raise RuntimeError("recall down")

    monkeypatch.setattr(spawn_recall, "query_for_spawn", _boom)
    monkeypatch.setattr(spawn_recall, "query_failures_for_spawn", lambda tt, tb: [])
    # query_for_spawn raising propagates into assemble's outer guard → "".
    assert retrieval_orchestrator.assemble_hydration_block("build", "x") == ""


# ── end-to-end: a spawn receives the 4-layer payload ─────────────────────


def test_inject_hydration_places_payload_in_spawn_env(monkeypatch):
    monkeypatch.setattr(spawn_recall, "query_for_spawn", lambda tt, tb: ["canonical approach X"])
    monkeypatch.setattr(spawn_recall, "query_failures_for_spawn", lambda tt, tb: [])
    out = retrieval_orchestrator.inject_hydration({}, task_type="build", task_brief="do X")
    payload = out["env"][spawn_recall.PRIOR_CONTEXT_ENV_KEY]
    assert "canonical approach X" in payload
    assert spawn_recall.BLOCK_HEADER in payload


def test_inject_hydration_no_block_leaves_kwargs_unchanged(monkeypatch):
    monkeypatch.setattr(spawn_recall, "query_for_spawn", lambda tt, tb: [])
    monkeypatch.setattr(spawn_recall, "query_failures_for_spawn", lambda tt, tb: [])
    sk = {"callsign": "test"}
    assert retrieval_orchestrator.inject_hydration(sk, task_type="build", task_brief="x") == sk
