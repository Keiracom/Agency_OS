"""Tests for Phase A5 piece 1b — ceo_memory Hindsight HTTP executor.

Covers the pure-logic surface (filtering, state file roundtrip, dry-run vs
execute control, refuses-to-run on empty MEMORY set) + the DecisionWrapper
call shape via a stub wrapper. End-to-end HTTP path is exercised by
operator dry-run before --execute, not re-mocked here.

bd: Agency_OS-oq3c
"""

from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts" / "migrations"))

_mod = importlib.import_module("ceo_memory_hindsight_executor")


class _SpyWrapper:
    """Stub DecisionWrapper that records ingest calls + returns a fake resp."""

    def __init__(self, *, fail_keys: set[str] | None = None) -> None:
        self.calls: list[dict] = []
        self.fail_keys = fail_keys or set()

    def ingest(self, *, tenant_id: str, content: str, metadata: dict) -> dict:
        self.calls.append({"tenant_id": tenant_id, "content": content, "metadata": metadata})
        for key in self.fail_keys:
            if key in content:
                return {"error": "simulated-failure"}
        return {"id": f"hindsight-{len(self.calls)}"}


def _write_jsonl(tmp_path: Path, name: str, rows: list[dict]) -> Path:
    path = tmp_path / name
    path.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
    return path


def test_filter_memory_rows_drops_policy_rows():
    rows = [
        {"key": "ceo:boundary_matrix_v1", "_carve": "POLICY"},
        {"key": "ceo:dave_x", "_carve": "MEMORY"},
        {"key": "ceo:memory_abstraction_v1", "_carve": "POLICY"},
        {"key": "ceo:dave_y", "_carve": "MEMORY"},
    ]
    out = _mod.filter_memory_rows(rows)
    assert len(out) == 2
    assert {r["key"] for r in out} == {"ceo:dave_x", "ceo:dave_y"}


def test_serialize_content_handles_string_and_dict():
    assert _mod.serialize_content("k", "v") == "k: v"
    out = _mod.serialize_content("k", {"a": 1, "b": [2, 3]})
    assert out.startswith("k: ")
    assert '"a": 1' in out
    assert '"b": [2, 3]' in out


def test_build_metadata_carries_key_source_carve_and_updated_at():
    row = {"key": "ceo:dave_x", "value": "v", "updated_at": "2026-05-26T10:00:00Z"}
    meta = _mod.build_metadata(row)
    assert meta["ceo_memory_key"] == "ceo:dave_x"
    assert meta["source"] == "a5_piece_1b_backfill"
    assert meta["carve"] == "MEMORY"
    assert meta["original_updated_at"] == "2026-05-26T10:00:00Z"


def test_state_roundtrip_skips_seen_keys(tmp_path: Path):
    state = tmp_path / "state.jsonl"
    assert _mod.load_state(state) == set()
    _mod.append_state(state, {"key": "ceo:dave_x", "ok": True, "info": "ok"})
    _mod.append_state(state, {"key": "ceo:dave_y", "ok": False, "info": "rc=500"})
    _mod.append_state(state, {"key": "ceo:dave_z", "ok": True, "info": "ok"})
    assert _mod.load_state(state) == {"ceo:dave_x", "ceo:dave_z"}


def test_execute_one_ok_path_returns_true():
    wrapper = _SpyWrapper()
    row = {"key": "ceo:dave_x", "value": "test", "updated_at": "2026-05-26T10:00:00Z"}
    ok, info = _mod.execute_one(row, decision_wrapper=wrapper)
    assert ok is True
    assert "hindsight-1" in info
    assert len(wrapper.calls) == 1
    call = wrapper.calls[0]
    assert call["tenant_id"] == _mod.FLEET_TENANT_ID
    assert "ceo:dave_x" in call["content"]
    assert call["metadata"]["ceo_memory_key"] == "ceo:dave_x"


def test_execute_one_error_response_returns_false():
    wrapper = _SpyWrapper(fail_keys={"ceo:dave_x"})
    row = {"key": "ceo:dave_x", "value": "test"}
    ok, info = _mod.execute_one(row, decision_wrapper=wrapper)
    assert ok is False
    assert "hindsight_error" in info


def test_execute_one_exception_returns_false():
    class _ThrowingWrapper:
        def ingest(self, **kwargs):
            raise ConnectionError("boom")

    row = {"key": "ceo:dave_x", "value": "test"}
    ok, info = _mod.execute_one(row, decision_wrapper=_ThrowingWrapper())
    assert ok is False
    assert "ConnectionError" in info


def test_run_aborts_when_input_file_missing(tmp_path: Path):
    rc = _mod.run(
        input_path=tmp_path / "no-such.jsonl",
        execute=True,
        state_path=tmp_path / "s.jsonl",
    )
    assert rc == 2


def test_run_aborts_when_no_memory_rows(tmp_path: Path):
    src = _write_jsonl(
        tmp_path,
        "in.jsonl",
        [{"key": "ceo:boundary_matrix_v1", "_carve": "POLICY"}],
    )
    rc = _mod.run(input_path=src, execute=True, state_path=tmp_path / "s.jsonl")
    assert rc == 2


def test_run_dry_run_does_not_call_wrapper(tmp_path: Path):
    src = _write_jsonl(
        tmp_path,
        "in.jsonl",
        [
            {"key": "ceo:dave_x", "value": "v", "_carve": "MEMORY"},
            {"key": "ceo:boundary_matrix_v1", "_carve": "POLICY"},
        ],
    )
    wrapper = _SpyWrapper()
    rc = _mod.run(
        input_path=src,
        execute=False,
        state_path=tmp_path / "s.jsonl",
        wrapper_factory=lambda: wrapper,
    )
    assert rc == 0
    assert wrapper.calls == []  # dry-run skips ingest


def test_run_execute_ingests_each_memory_row_and_writes_state(tmp_path: Path):
    src = _write_jsonl(
        tmp_path,
        "in.jsonl",
        [
            {"key": "ceo:dave_x", "value": "vx", "_carve": "MEMORY"},
            {"key": "ceo:boundary_matrix_v1", "_carve": "POLICY"},
            {"key": "ceo:dave_y", "value": "vy", "_carve": "MEMORY"},
        ],
    )
    wrapper = _SpyWrapper()
    state = tmp_path / "s.jsonl"
    rc = _mod.run(
        input_path=src,
        execute=True,
        state_path=state,
        wrapper_factory=lambda: wrapper,
    )
    assert rc == 0
    assert len(wrapper.calls) == 2
    assert {c["metadata"]["ceo_memory_key"] for c in wrapper.calls} == {"ceo:dave_x", "ceo:dave_y"}
    assert _mod.load_state(state) == {"ceo:dave_x", "ceo:dave_y"}


def test_run_execute_returns_one_on_any_failure(tmp_path: Path):
    src = _write_jsonl(
        tmp_path,
        "in.jsonl",
        [
            {"key": "ceo:dave_x", "value": "vx", "_carve": "MEMORY"},
            {"key": "ceo:dave_y", "value": "vy", "_carve": "MEMORY"},
        ],
    )
    wrapper = _SpyWrapper(fail_keys={"ceo:dave_y"})
    rc = _mod.run(
        input_path=src,
        execute=True,
        state_path=tmp_path / "s.jsonl",
        wrapper_factory=lambda: wrapper,
    )
    assert rc == 1


def test_run_skips_already_completed_keys_on_rerun(tmp_path: Path):
    src = _write_jsonl(
        tmp_path,
        "in.jsonl",
        [
            {"key": "ceo:dave_x", "value": "vx", "_carve": "MEMORY"},
            {"key": "ceo:dave_y", "value": "vy", "_carve": "MEMORY"},
        ],
    )
    state = tmp_path / "s.jsonl"
    _mod.append_state(state, {"key": "ceo:dave_x", "ok": True, "info": "prev"})
    wrapper = _SpyWrapper()
    rc = _mod.run(
        input_path=src,
        execute=True,
        state_path=state,
        wrapper_factory=lambda: wrapper,
    )
    assert rc == 0
    assert len(wrapper.calls) == 1  # only dave_y; dave_x already in state
    assert wrapper.calls[0]["metadata"]["ceo_memory_key"] == "ceo:dave_y"
