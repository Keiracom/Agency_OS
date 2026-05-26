"""Tests for Phase A5 piece 3 — Drive Manual backfill to Hindsight.

Covers:
- chunk_by_section markdown `## ` splitting (with + without preamble + no-headings fallback)
- metadata + external_id shape
- ingest_chunk happy / error / exception paths
- state file roundtrip
- run() dry-run vs execute, refuses on missing input, rc=1 on any failure,
  skip-on-rerun by external_id

bd: Agency_OS-ushm
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts" / "migrations"))

_mod = importlib.import_module("drive_manual_backfill_to_hindsight")


class _SpyWrapper:
    def __init__(self, *, fail_ids: set[str] | None = None) -> None:
        self.calls: list[dict] = []
        self.fail_ids = fail_ids or set()

    def ingest(self, **kwargs):
        self.calls.append(kwargs)
        meta = kwargs.get("metadata") or {}
        if meta.get("external_id", "") in self.fail_ids:
            return {"error": "simulated"}
        return {"id": f"hs-{len(self.calls)}"}


def test_chunk_by_section_splits_on_h2_headings():
    text = "## A\nbody-a\n## B\nbody-b\n## C\nbody-c"
    chunks = _mod.chunk_by_section(text)
    assert len(chunks) == 3
    assert chunks[0]["heading"] == "A"
    assert "body-a" in chunks[0]["body"]
    assert chunks[2]["heading"] == "C"
    assert chunks[2]["index"] == 2


def test_chunk_by_section_carries_preamble_as_chunk_zero():
    text = "intro line\n\n## A\nbody-a\n## B\nbody-b"
    chunks = _mod.chunk_by_section(text)
    assert len(chunks) == 3
    assert chunks[0]["heading"] is None
    assert "intro line" in chunks[0]["body"]
    assert chunks[1]["heading"] == "A"
    assert chunks[1]["index"] == 1


def test_chunk_by_section_no_headings_returns_single_whole_file():
    text = "just one big body with no section headings\n\nstill no headings."
    chunks = _mod.chunk_by_section(text)
    assert len(chunks) == 1
    assert chunks[0]["heading"] is None
    assert "just one big body" in chunks[0]["body"]


def test_build_external_id_combines_path_and_index():
    p = Path("/tmp/manual.md")
    assert _mod.build_external_id(p, 3) == "/tmp/manual.md#3"


def test_build_metadata_carries_routing_fields():
    p = Path("/tmp/manual.md")
    chunk = {"heading": "Section X", "body": "...", "index": 1}
    meta = _mod.build_metadata(p, chunk)
    assert meta["source"] == "a5_piece_3_drive_manual_backfill"
    assert meta["source_file"] == "/tmp/manual.md"
    assert meta["chunk_index"] == 1
    assert meta["chunk_heading"] == "Section X"
    assert meta["external_id"] == "/tmp/manual.md#1"


def test_build_metadata_empty_heading_for_no_heading_chunks():
    p = Path("/tmp/manual.md")
    chunk = {"heading": None, "body": "...", "index": 0}
    meta = _mod.build_metadata(p, chunk)
    assert meta["chunk_heading"] == ""


def test_ingest_chunk_happy_path():
    wrapper = _SpyWrapper()
    chunk = {"heading": "X", "body": "the body", "index": 0}
    ok, info = _mod.ingest_chunk(Path("/tmp/m.md"), chunk, decision_wrapper=wrapper)
    assert ok is True
    assert "hs-1" in info
    call = wrapper.calls[0]
    assert call["tenant_id"] == _mod.FLEET_TENANT_ID
    assert call["content"] == "the body"
    assert call["metadata"]["chunk_heading"] == "X"


def test_ingest_chunk_returns_false_on_dict_error():
    p = Path("/tmp/m.md")
    wrapper = _SpyWrapper(fail_ids={_mod.build_external_id(p, 0)})
    chunk = {"heading": "X", "body": "y", "index": 0}
    ok, info = _mod.ingest_chunk(p, chunk, decision_wrapper=wrapper)
    assert ok is False
    assert "hindsight_error" in info


def test_ingest_chunk_returns_false_on_exception():
    class _Bad:
        def ingest(self, **kwargs):
            raise RuntimeError("boom")

    chunk = {"heading": "X", "body": "y", "index": 0}
    ok, info = _mod.ingest_chunk(Path("/tmp/m.md"), chunk, decision_wrapper=_Bad())
    assert ok is False
    assert "RuntimeError" in info


def test_state_roundtrip(tmp_path: Path):
    state = tmp_path / "s.jsonl"
    _mod.append_state(state, {"external_id": "a#0", "ok": True})
    _mod.append_state(state, {"external_id": "a#1", "ok": False})
    assert _mod.load_state(state) == {"a#0"}


def test_run_aborts_on_missing_input_file(tmp_path: Path):
    rc = _mod.run(
        input_files=[tmp_path / "does-not-exist.md"],
        execute=True,
        state_path=tmp_path / "s.jsonl",
    )
    assert rc == 2


def test_run_aborts_on_empty_input_list(tmp_path: Path):
    rc = _mod.run(input_files=[], execute=True, state_path=tmp_path / "s.jsonl")
    assert rc == 2


def test_run_dry_run_does_not_call_wrapper(tmp_path: Path):
    f = tmp_path / "m.md"
    f.write_text("## A\nbody-a\n## B\nbody-b", encoding="utf-8")
    wrapper = _SpyWrapper()
    rc = _mod.run(
        input_files=[f],
        execute=False,
        state_path=tmp_path / "s.jsonl",
        wrapper_factory=lambda: wrapper,
    )
    assert rc == 0
    assert wrapper.calls == []


def test_run_execute_ingests_all_chunks_and_writes_state(tmp_path: Path):
    f = tmp_path / "m.md"
    f.write_text("## A\nbody-a\n## B\nbody-b\n## C\nbody-c", encoding="utf-8")
    wrapper = _SpyWrapper()
    state = tmp_path / "s.jsonl"
    rc = _mod.run(
        input_files=[f],
        execute=True,
        state_path=state,
        wrapper_factory=lambda: wrapper,
    )
    assert rc == 0
    assert len(wrapper.calls) == 3
    seen = _mod.load_state(state)
    assert len(seen) == 3
    assert all(f"{f}#{i}" in seen for i in range(3))


def test_run_handles_multiple_input_files(tmp_path: Path):
    f1 = tmp_path / "agency_os_manual.md"
    f1.write_text("## A\nbody-a", encoding="utf-8")
    f2 = tmp_path / "keiracom_manual.md"
    f2.write_text("## X\nbody-x\n## Y\nbody-y", encoding="utf-8")
    wrapper = _SpyWrapper()
    rc = _mod.run(
        input_files=[f1, f2],
        execute=True,
        state_path=tmp_path / "s.jsonl",
        wrapper_factory=lambda: wrapper,
    )
    assert rc == 0
    assert len(wrapper.calls) == 3  # 1 from f1 + 2 from f2
    sources = {c["metadata"]["source_file"] for c in wrapper.calls}
    assert sources == {str(f1), str(f2)}


def test_run_returns_one_on_any_failure(tmp_path: Path):
    f = tmp_path / "m.md"
    f.write_text("## A\nbody-a\n## B\nbody-b", encoding="utf-8")
    wrapper = _SpyWrapper(fail_ids={f"{f}#1"})  # chunk index 1 = "B"
    rc = _mod.run(
        input_files=[f],
        execute=True,
        state_path=tmp_path / "s.jsonl",
        wrapper_factory=lambda: wrapper,
    )
    assert rc == 1


def test_run_skips_already_completed_external_ids(tmp_path: Path):
    f = tmp_path / "m.md"
    f.write_text("## A\nbody-a\n## B\nbody-b", encoding="utf-8")
    state = tmp_path / "s.jsonl"
    _mod.append_state(state, {"external_id": f"{f}#0", "ok": True})
    wrapper = _SpyWrapper()
    rc = _mod.run(
        input_files=[f],
        execute=True,
        state_path=state,
        wrapper_factory=lambda: wrapper,
    )
    assert rc == 0
    assert len(wrapper.calls) == 1
    assert wrapper.calls[0]["metadata"]["external_id"] == f"{f}#1"
