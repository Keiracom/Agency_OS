"""Unit tests for git_commits_indexer (KEI-85 phase C).

No network / no live git. Tests cover the parse + UUID + ABC contract.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "orchestrator"))

import git_commits_indexer as mod  # noqa: E402


def _commit(sha: str = "abc123", iso: str = "2026-05-17T10:00:00+00:00") -> mod.GitCommit:
    return mod.GitCommit(
        sha=sha,
        author="atlas",
        committed_iso=iso,
        subject="[ATLAS] feat(kei85): phase C — git commits → Codebase",
        body="Body text mentioning KEI-99 and KEI-85.",
    )


def test_deterministic_uuid_per_sha():
    a = mod.build_codebase_doc(_commit(sha="abc123"))["id"]
    b = mod.build_codebase_doc(_commit(sha="abc123"))["id"]
    assert a == b


def test_uuid_differs_per_sha():
    a = mod.build_codebase_doc(_commit(sha="abc123"))["id"]
    b = mod.build_codebase_doc(_commit(sha="def456"))["id"]
    assert a != b


def test_build_codebase_doc_basic_shape():
    doc = mod.build_codebase_doc(_commit())
    assert doc["class"] == "Codebase"
    props = doc["properties"]
    assert props["agent"] == "system"
    assert props["created_at"] == "2026-05-17T10:00:00+00:00"
    assert "phase C" in props["raw_text"]
    assert len(props["environment_hash"]) == 16
    int(props["environment_hash"], 16)


def test_kei_extracted_from_subject():
    """`_extract_kei` walks the subject + body and pulls the first KEI-N hit."""
    doc = mod.build_codebase_doc(_commit())
    # Subject has kei85 in `feat(kei85)`. _extract_kei normalises to KEI-85.
    assert doc["properties"]["kei"] == "KEI-85"


def test_kei_empty_when_no_match():
    commit = mod.GitCommit(
        sha="aaaaaa",
        author="x",
        committed_iso="2026-05-17T00:00:00+00:00",
        subject="initial commit",
        body="",
    )
    assert mod.build_codebase_doc(commit)["properties"]["kei"] == ""


def test_empty_iso_falls_back_to_epoch():
    commit = mod.GitCommit(sha="x", author="x", committed_iso="", subject="s", body="")
    assert mod.build_codebase_doc(commit)["properties"]["created_at"] == mod.EPOCH_ISO


def test_indexer_satisfies_base_indexer_abc():
    import indexer_base

    assert issubclass(mod.GitCommitsIndexer, indexer_base.BaseIndexer)
    assert mod.GitCommitsIndexer.source_name == "git"
    assert mod.GitCommitsIndexer.target_class == "Codebase"
    assert mod.GitCommitsIndexer.class_schema["class"] == "Codebase"
    assert mod.GitCommitsIndexer.__abstractmethods__ == frozenset()


def test_cursor_write_then_read(tmp_path, monkeypatch):
    cursor = tmp_path / "git.cursor"
    monkeypatch.setattr(mod, "CURSOR_PATH", cursor)
    indexer = mod.GitCommitsIndexer()
    indexer._last_max_committed_iso = "2026-05-17T10:00:00+00:00"
    indexer.advance_cursor()
    assert mod._read_cursor() == "2026-05-17T10:00:00+00:00"


def test_cursor_missing_returns_epoch(tmp_path, monkeypatch):
    monkeypatch.setattr(mod, "CURSOR_PATH", tmp_path / "no-such")
    assert mod._read_cursor() == mod.EPOCH_ISO


def test_cursor_corrupt_returns_epoch(tmp_path, monkeypatch):
    bad = tmp_path / "bad.cursor"
    bad.write_text("not-json")
    monkeypatch.setattr(mod, "CURSOR_PATH", bad)
    assert mod._read_cursor() == mod.EPOCH_ISO


def test_git_log_since_drops_boundary_commit(monkeypatch):
    """Aiden HOLD #1: `git log --since` is inclusive at the boundary second.
    The fetch path must drop any commit whose committed_iso matches the cursor
    exactly — otherwise it gets re-POSTed every poll.
    """
    cursor = "2026-05-17T10:00:00+00:00"
    boundary_sha = "boundary123"
    newer_sha = "newer456"

    fake_stdout = (
        f"{boundary_sha}\x1fatlas\x1f{cursor}\x1fboundary commit\x1f\x1e"
        f"{newer_sha}\x1fatlas\x1f2026-05-17T11:00:00+00:00\x1fnewer commit\x1f\x1e"
    )

    class _Proc:
        returncode = 0
        stdout = fake_stdout
        stderr = ""

    monkeypatch.setattr(mod.subprocess, "run", lambda *a, **kw: _Proc())

    out = mod._git_log_since(cursor, 50)
    shas = [c.sha for c in out]
    assert boundary_sha not in shas
    assert newer_sha in shas


def test_git_log_since_preserves_body_with_embedded_field_separator(monkeypatch):
    """Aiden HOLD #2: rec.split(_FIELD_SEP, 4) must keep body intact even
    when the body contains a \\x1f byte.
    """
    sha = "withbody789"
    embedded_body = "line one\x1fembedded sep should not split"
    fake_stdout = f"{sha}\x1fatlas\x1f2026-05-17T12:00:00+00:00\x1fsubj\x1f{embedded_body}\x1e"

    class _Proc:
        returncode = 0
        stdout = fake_stdout
        stderr = ""

    monkeypatch.setattr(mod.subprocess, "run", lambda *a, **kw: _Proc())

    out = mod._git_log_since("1970-01-01T00:00:00Z", 10)
    assert len(out) == 1
    assert out[0].sha == sha
    # The embedded sep + everything after must be preserved in `body`.
    assert "embedded sep should not split" in out[0].body
