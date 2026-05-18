"""Unit tests for drive_strategic_indexer.py (KEI-208).

No live network — Drive client and Weaviate POST are fully monkeypatched.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "orchestrator"))

import drive_strategic_indexer as mod  # noqa: E402, I001


# ─── Helpers ─────────────────────────────────────────────────────────────────


def _make_config(tmp_path: Path, targets: list[dict] | None = None) -> Path:
    if targets is None:
        targets = [
            {
                "doc_id": "DOC_A",
                "title": "Alpha",
                "ratified_by": "dave",
                "ratified_at": "2026-05-18",
            },
        ]
    cfg = tmp_path / "drive_index_targets.json"
    cfg.write_text(json.dumps({"targets": targets}))
    return cfg


def _fake_doc(content: str = "# H1\nbody\n", modified: str = "2026-05-18T00:00:00Z") -> dict:
    return {"content": content, "modifiedTime": modified}


# ─── Config tests ─────────────────────────────────────────────────────────────


def test_load_config_from_json(tmp_path: Path) -> None:
    cfg = _make_config(tmp_path)
    targets = mod.load_config(cfg)
    assert len(targets) == 1
    assert targets[0].doc_id == "DOC_A"
    assert targets[0].title == "Alpha"
    assert targets[0].ratified_by == "dave"


def test_load_config_rejects_missing_targets_key(tmp_path: Path) -> None:
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps({"docs": []}))
    with pytest.raises(ValueError, match="missing 'targets'"):
        mod.load_config(bad)


# ─── Chunking tests ───────────────────────────────────────────────────────────


def test_chunk_by_heading_h1_h2_h3() -> None:
    md = "# Title\nbody one\n## Sub\nbody two\n### Sub-sub\nbody three\n"
    chunks = mod.chunk_by_heading(md)
    assert len(chunks) == 3


def test_chunk_preserves_section_title() -> None:
    md = "## My Section\ncontent here\n"
    chunks = mod.chunk_by_heading(md)
    assert chunks[0].section_title == "My Section"


def test_chunk_no_headings_returns_single_document_chunk() -> None:
    md = "just plain text\nno headings here\n"
    chunks = mod.chunk_by_heading(md)
    assert len(chunks) == 1
    assert chunks[0].section_title == "(document)"


# ─── UUID tests ───────────────────────────────────────────────────────────────


def test_deterministic_uuid_for_same_doc_section() -> None:
    a = mod.section_uuid("DOC_A", "Introduction")
    b = mod.section_uuid("DOC_A", "Introduction")
    assert a == b


def test_deterministic_uuid_differs_for_different_section() -> None:
    a = mod.section_uuid("DOC_A", "Introduction")
    b = mod.section_uuid("DOC_A", "Conclusion")
    assert a != b


# ─── Full-mode integration tests (mocked Drive + Weaviate) ───────────────────


def test_full_mode_indexes_all_targets(tmp_path: Path) -> None:
    targets_data = [
        {"doc_id": "DOC_A", "title": "Alpha", "ratified_by": "dave", "ratified_at": "2026-05-18"},
        {"doc_id": "DOC_B", "title": "Beta", "ratified_by": "dave", "ratified_at": "2026-05-18"},
    ]
    cfg = _make_config(tmp_path, targets_data)
    posted_ids: list[str] = []

    def fake_fetch(doc_id: str) -> dict:
        return _fake_doc(f"# Section\ncontent for {doc_id}", "2026-05-18T00:00:00Z")

    def fake_post(obj: dict) -> bool:
        posted_ids.append(obj["properties"]["doc_id"])
        return True

    state_file = tmp_path / "state.json"
    with (
        patch.object(mod, "load_config", return_value=mod.load_config(cfg)),
        patch.object(mod, "fetch_drive_doc", side_effect=fake_fetch),
        patch.object(mod, "post_object", side_effect=fake_post),
        patch.object(mod, "_STATE_FILE", state_file),
        patch.object(mod, "ensure_strategic_class"),
        patch.object(mod, "write_ceo_memory"),
    ):
        mod.run("full")

    assert "DOC_A" in posted_ids
    assert "DOC_B" in posted_ids


# ─── Incremental-mode tests ───────────────────────────────────────────────────


def test_incremental_mode_skips_unchanged_modifiedTime(tmp_path: Path) -> None:
    cfg = _make_config(tmp_path)
    state_file = tmp_path / "state.json"
    state_file.write_text(json.dumps({"DOC_A": "2026-05-18T00:00:00Z"}))
    posted_ids: list[str] = []

    def fake_fetch(doc_id: str) -> dict:
        return _fake_doc("# Section\nbody", "2026-05-18T00:00:00Z")

    def fake_post(obj: dict) -> bool:
        posted_ids.append(obj["properties"]["doc_id"])
        return True

    with (
        patch.object(mod, "load_config", return_value=mod.load_config(cfg)),
        patch.object(mod, "fetch_drive_doc", side_effect=fake_fetch),
        patch.object(mod, "post_object", side_effect=fake_post),
        patch.object(mod, "_STATE_FILE", state_file),
        patch.object(mod, "ensure_strategic_class"),
        patch.object(mod, "write_ceo_memory"),
    ):
        mod.run("incremental")

    assert posted_ids == [], "unchanged doc should be skipped"


def test_incremental_mode_reindexes_changed(tmp_path: Path) -> None:
    cfg = _make_config(tmp_path)
    state_file = tmp_path / "state.json"
    state_file.write_text(json.dumps({"DOC_A": "2026-05-17T00:00:00Z"}))
    posted_ids: list[str] = []

    def fake_fetch(doc_id: str) -> dict:
        return _fake_doc("# Section\nnew body", "2026-05-18T00:00:00Z")

    def fake_post(obj: dict) -> bool:
        posted_ids.append(obj["properties"]["doc_id"])
        return True

    with (
        patch.object(mod, "load_config", return_value=mod.load_config(cfg)),
        patch.object(mod, "fetch_drive_doc", side_effect=fake_fetch),
        patch.object(mod, "post_object", side_effect=fake_post),
        patch.object(mod, "_STATE_FILE", state_file),
        patch.object(mod, "ensure_strategic_class"),
        patch.object(mod, "write_ceo_memory"),
    ):
        mod.run("incremental")

    assert "DOC_A" in posted_ids, "changed doc should be re-indexed"


# ─── Upsert idempotency test ──────────────────────────────────────────────────


def test_upsert_overwrites_same_uuid(tmp_path: Path) -> None:
    """Same (doc_id, section) must produce same UUID on second run."""
    doc_id = "DOC_STABLE"
    section = "Stable Section"
    uuid_first = mod.section_uuid(doc_id, section)
    uuid_second = mod.section_uuid(doc_id, section)
    assert uuid_first == uuid_second, "same (doc_id, section) must yield same UUID"


# ─── Error resilience test ────────────────────────────────────────────────────


def test_drive_api_error_logs_and_continues(tmp_path: Path) -> None:
    targets_data = [
        {
            "doc_id": "FAIL_DOC",
            "title": "Will Fail",
            "ratified_by": "dave",
            "ratified_at": "2026-05-18",
        },
        {
            "doc_id": "DOC_OK",
            "title": "Will Succeed",
            "ratified_by": "dave",
            "ratified_at": "2026-05-18",
        },
    ]
    cfg = _make_config(tmp_path, targets_data)
    posted_ids: list[str] = []
    state_file = tmp_path / "state.json"

    def fake_fetch(doc_id: str) -> dict:
        if doc_id == "FAIL_DOC":
            raise RuntimeError("Drive auth error")
        return _fake_doc("# Section\nbody", "2026-05-18T00:00:00Z")

    def fake_post(obj: dict) -> bool:
        posted_ids.append(obj["properties"]["doc_id"])
        return True

    with (
        patch.object(mod, "load_config", return_value=mod.load_config(cfg)),
        patch.object(mod, "fetch_drive_doc", side_effect=fake_fetch),
        patch.object(mod, "post_object", side_effect=fake_post),
        patch.object(mod, "_STATE_FILE", state_file),
        patch.object(mod, "ensure_strategic_class"),
        patch.object(mod, "write_ceo_memory"),
    ):
        mod.run("full")

    assert "DOC_OK" in posted_ids, "healthy doc must still index despite peer failure"
    assert "FAIL_DOC" not in posted_ids


# ─── CEO memory test ──────────────────────────────────────────────────────────


def test_ceo_memory_drive_indexer_key_written(tmp_path: Path) -> None:
    cfg = _make_config(tmp_path)
    state_file = tmp_path / "state.json"
    memory_calls: list[dict] = []

    def fake_fetch(doc_id: str) -> dict:
        return _fake_doc("# Section\nbody", "2026-05-18T00:00:00Z")

    with (
        patch.object(mod, "load_config", return_value=mod.load_config(cfg)),
        patch.object(mod, "fetch_drive_doc", side_effect=fake_fetch),
        patch.object(mod, "post_object", return_value=True),
        patch.object(mod, "_STATE_FILE", state_file),
        patch.object(mod, "ensure_strategic_class"),
        patch.object(mod, "write_ceo_memory", side_effect=memory_calls.append),
    ):
        mod.run("full")

    assert len(memory_calls) == 1
    assert memory_calls[0]["mode"] == "full"
    assert "chunks_ok" in memory_calls[0]


# ─── No-hardcoded-IDs enforcement ────────────────────────────────────────────


def test_no_hardcoded_doc_ids_in_indexer_source() -> None:
    """Gate: indexer Python source must contain zero Drive doc ID literals."""
    drive_doc_ids = [
        "1Br6SsCKizvyNk6dOvm9EQE_8drut1WRId7WJNddilDA",
        "1U5uet-IxJSNhE-iWlVdW3eZpNR8obf-7j3BzvaEWdH4",
        "113Ej0n62uS_qmyMwvase54kFI1eCCwHHwwrMN9GDlCc",
        "1NNoA-6MgXZS6mk35QCeer3mmEnqNVRSD7NBmu0fzfHw",
        "1kf-MVHeHaViwlMuy3ti_pZCS1DJE9ox8vIa3aZdspkY",
    ]
    indexer_src = (ROOT / "scripts" / "orchestrator" / "drive_strategic_indexer.py").read_text()
    for doc_id in drive_doc_ids:
        assert doc_id not in indexer_src, (
            f"hardcoded doc ID {doc_id} found in drive_strategic_indexer.py — "
            "IDs must live in config/drive_index_targets.json only"
        )
