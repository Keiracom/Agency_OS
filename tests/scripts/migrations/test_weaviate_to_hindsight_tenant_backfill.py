"""Tests for Phase A5 piece 2 — generic Weaviate-class → Hindsight tenant backfill.

Covers wrapper dispatch (4 types), idempotency state-file roundtrip, dry-run
vs execute control, and the per-wrapper ingest signature builders.

bd: Agency_OS-inhl
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts" / "migrations"))

_mod = importlib.import_module("weaviate_to_hindsight_tenant_backfill")


class _SpyWrapper:
    """Records ingest calls; mimics wrapper return shape."""

    def __init__(self, *, fail_ids: set[str] | None = None) -> None:
        self.calls: list[dict] = []
        self.fail_ids = fail_ids or set()

    def ingest(self, **kwargs):
        self.calls.append(kwargs)
        meta = kwargs.get("metadata") or {}
        ext_id = meta.get("external_id", "")
        if ext_id in self.fail_ids:
            return {"error": "simulated"}
        return {"id": f"hs-{len(self.calls)}"}


def _obj(external_id: str, props: dict | None = None) -> dict:
    return {
        "id": external_id,
        "class": "X",
        "properties": props or {"raw_text": f"text-{external_id}"},
    }


def test_content_from_props_prefers_raw_text():
    assert _mod._content_from_props({"raw_text": "rt", "content": "c"}) == "rt"
    assert _mod._content_from_props({"content": "c"}) == "c"
    out = _mod._content_from_props({"x": 1, "y": "z"})
    assert '"x": 1' in out


def test_metadata_excludes_raw_text_and_carries_routing():
    obj = _obj("ext-1", {"raw_text": "rt", "agent": "atlas", "kei": "KEI-1"})
    meta = _mod._metadata_from_obj(obj, "Decisions", "decision")
    assert meta["source"] == "a5_piece_2_snapshot_backfill"
    assert meta["weaviate_class"] == "Decisions"
    assert meta["wrapper"] == "decision"
    assert meta["external_id"] == "ext-1"
    assert meta["agent"] == "atlas"
    assert meta["kei"] == "KEI-1"
    assert "raw_text" not in meta


def test_ingest_decision_calls_wrapper_with_tenant_content_metadata():
    wrapper = _SpyWrapper()
    obj = _obj("d-1", {"raw_text": "decision text", "agent": "atlas"})
    out = _mod.ingest_decision(wrapper, obj, "Decisions")
    assert out["id"] == "hs-1"
    call = wrapper.calls[0]
    assert call["tenant_id"] == _mod.FLEET_TENANT_ID
    assert call["content"] == "decision text"
    assert call["metadata"]["weaviate_class"] == "Decisions"
    assert call["metadata"]["wrapper"] == "decision"


def test_ingest_taskcontext_calls_wrapper_with_tenant_content_metadata():
    wrapper = _SpyWrapper()
    obj = _obj("tc-1", {"raw_text": "task context"})
    _mod.ingest_taskcontext(wrapper, obj, "Sessions")
    call = wrapper.calls[0]
    assert call["tenant_id"] == _mod.FLEET_TENANT_ID
    assert call["content"] == "task context"
    assert call["metadata"]["wrapper"] == "taskcontext"


def test_ingest_artifact_passes_author_and_artifact_ref():
    wrapper = _SpyWrapper()
    obj = _obj("a-1", {"raw_text": "artifact body", "agent": "scout"})
    _mod.ingest_artifact(wrapper, obj, "Codebase")
    call = wrapper.calls[0]
    assert call["author"] == "scout"
    assert call["artifact_ref"] == "Codebase/a-1"
    assert call["metadata"]["wrapper"] == "artifact"


def test_ingest_artifact_defaults_author_to_unknown():
    wrapper = _SpyWrapper()
    obj = _obj("a-2", {"raw_text": "artifact body"})  # no `agent`
    _mod.ingest_artifact(wrapper, obj, "Codebase")
    assert wrapper.calls[0]["author"] == "unknown"


def test_ingest_antipattern_pulls_context_failed_verified_paths():
    wrapper = _SpyWrapper()
    obj = _obj(
        "ap-1",
        {"context": "ctx", "failed_path": "fp", "verified_path": "vp"},
    )
    _mod.ingest_antipattern(wrapper, obj, "Discoveries")
    call = wrapper.calls[0]
    assert call["context"] == "ctx"
    assert call["failed_path"] == "fp"
    assert call["verified_path"] == "vp"
    assert call["metadata"]["wrapper"] == "antipattern"


def test_ingest_antipattern_falls_back_to_class_name_for_context():
    wrapper = _SpyWrapper()
    obj = _obj("ap-2", {"raw_text": "rt only"})
    _mod.ingest_antipattern(wrapper, obj, "Discoveries")
    call = wrapper.calls[0]
    assert call["context"] == "Discoveries"
    assert call["failed_path"] == "rt only"
    assert call["verified_path"] == ""


def test_ingest_one_returns_false_on_dict_error():
    wrapper = _SpyWrapper(fail_ids={"x"})
    ok, info = _mod.ingest_one(
        _obj("x"),
        class_name="Decisions",
        wrapper_name="decision",
        wrapper=wrapper,
    )
    assert ok is False
    assert "hindsight_error" in info


def test_ingest_one_returns_false_on_exception():
    class _Bad:
        def ingest(self, **kwargs):
            raise RuntimeError("kaboom")

    ok, info = _mod.ingest_one(
        _obj("y"),
        class_name="Decisions",
        wrapper_name="decision",
        wrapper=_Bad(),
    )
    assert ok is False
    assert "RuntimeError" in info


def test_state_roundtrip(tmp_path: Path):
    state = tmp_path / "s.jsonl"
    _mod.append_state(state, {"external_id": "a", "ok": True})
    _mod.append_state(state, {"external_id": "b", "ok": False})
    assert _mod.load_state(state) == {"a"}


def test_run_unknown_wrapper_returns_two():
    rc = _mod.run(
        class_name="Decisions",
        wrapper_name="nonesuch",
        execute=True,
        state_path=Path("/tmp/never.jsonl"),
    )
    assert rc == 2


def test_run_dry_run_does_not_call_wrapper(tmp_path: Path):
    wrapper = _SpyWrapper()
    objs = [_obj(f"d-{i}") for i in range(3)]
    rc = _mod.run(
        class_name="Decisions",
        wrapper_name="decision",
        execute=False,
        state_path=tmp_path / "s.jsonl",
        obj_iter=iter(objs),
        wrapper_factory=lambda: wrapper,
    )
    assert rc == 0
    assert wrapper.calls == []


def test_run_execute_ingests_each_object_and_writes_state(tmp_path: Path):
    wrapper = _SpyWrapper()
    objs = [_obj("a"), _obj("b")]
    state = tmp_path / "s.jsonl"
    rc = _mod.run(
        class_name="Decisions",
        wrapper_name="decision",
        execute=True,
        state_path=state,
        obj_iter=iter(objs),
        wrapper_factory=lambda: wrapper,
    )
    assert rc == 0
    assert len(wrapper.calls) == 2
    assert _mod.load_state(state) == {"a", "b"}


def test_run_returns_one_on_any_failure(tmp_path: Path):
    wrapper = _SpyWrapper(fail_ids={"b"})
    objs = [_obj("a"), _obj("b")]
    rc = _mod.run(
        class_name="Decisions",
        wrapper_name="decision",
        execute=True,
        state_path=tmp_path / "s.jsonl",
        obj_iter=iter(objs),
        wrapper_factory=lambda: wrapper,
    )
    assert rc == 1


def test_run_skips_already_completed_external_ids(tmp_path: Path):
    state = tmp_path / "s.jsonl"
    _mod.append_state(state, {"external_id": "a", "ok": True})
    wrapper = _SpyWrapper()
    objs = [_obj("a"), _obj("b")]
    rc = _mod.run(
        class_name="Decisions",
        wrapper_name="decision",
        execute=True,
        state_path=state,
        obj_iter=iter(objs),
        wrapper_factory=lambda: wrapper,
    )
    assert rc == 0
    assert len(wrapper.calls) == 1
    assert wrapper.calls[0]["metadata"]["external_id"] == "b"


def test_ingesters_registry_covers_all_four_wrapper_names():
    assert set(_mod.INGESTERS) == set(_mod.WRAPPER_NAMES)
    for _name, (cls, fn) in _mod.INGESTERS.items():
        assert cls is not None
        assert callable(fn)
