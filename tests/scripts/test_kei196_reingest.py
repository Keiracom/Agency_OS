"""Tests for kei196_reingest_with_vectorizer — KEI-196 backup/restore/validate logic.

Parser-only tests; no live Weaviate dependency. Covers:
  - Module-level constants (target collections + new vectorizer config)
  - CLI argparse (step + --execute gating + --class filter)
  - Backup path construction
  - validate_scores returns the expected shape

Live integration (live Weaviate + inference container) is the operator-gated
acceptance path documented in docs/wave3/kei196_reingest_plan.md.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPT = REPO_ROOT / "scripts" / "orchestrator" / "kei196_reingest_with_vectorizer.py"


@pytest.fixture(scope="module")
def mod():
    spec = importlib.util.spec_from_file_location("kei196_reingest", SCRIPT)
    m = importlib.util.module_from_spec(spec)
    sys.modules["kei196_reingest"] = m
    spec.loader.exec_module(m)
    return m


def test_target_collections_five(mod):
    """KEI-192 audit identified 5 retrieval-path collections."""
    assert set(mod.TARGET_COLLECTIONS) == {
        "Discoveries",
        "Keis",
        "AgentMemories",
        "Decisions",
        "Codebase",
    }


def test_new_vectorizer_is_text2vec_transformers(mod):
    """Per ratification: text2vec-transformers (sentence-transformers) is the choice."""
    assert mod.NEW_VECTORIZER == "text2vec-transformers"
    assert "text2vec-transformers" in mod.NEW_MODULE_CONFIG


def test_destructive_step_requires_execute_flag(mod, capsys):
    """recreate/restore/all without --execute returns rc=1 + explanatory log."""
    rc = mod.main(["--step", "recreate"])
    assert rc == 1


def test_backup_step_safe_without_execute(mod, monkeypatch, tmp_path):
    """--step backup is read-only; runs without --execute. Mocks the HTTP call."""

    def _fake_get(path):
        # Return one page of 2 objects then an empty page (end of cursor).
        if "after=" in path:
            return {"objects": []}
        return {
            "objects": [
                {"id": "obj-1", "properties": {"agent": "scout"}},
                {"id": "obj-2", "properties": {"agent": "scout"}},
            ]
        }

    monkeypatch.setattr(mod, "_http_get", _fake_get)
    rc = mod.main(["--step", "backup", "--class", "AgentMemories", "--backup-dir", str(tmp_path)])
    assert rc == 0
    out_path = tmp_path / "AgentMemories.jsonl"
    assert out_path.exists()
    assert sum(1 for _ in out_path.read_text().splitlines()) == 2


def test_class_filter_restricts_to_one(mod, monkeypatch, tmp_path):
    """--class restricts the iteration to one target collection."""
    seen: list[str] = []

    def _fake_backup(class_name, backup_dir):
        seen.append(class_name)
        return 0

    monkeypatch.setattr(mod, "backup_class", _fake_backup)
    rc = mod.main(["--step", "backup", "--class", "AgentMemories", "--backup-dir", str(tmp_path)])
    assert rc == 0
    assert seen == ["AgentMemories"]


def test_default_step_is_safe_backup(mod, monkeypatch, tmp_path):
    """Default step is backup (read-only) — operator can't accidentally destruct."""
    monkeypatch.setattr(mod, "backup_class", lambda _c, _d: 0)
    # No --step + no --execute should still succeed (backup default).
    rc = mod.main(["--backup-dir", str(tmp_path)])
    assert rc == 0


def test_validate_scores_returns_pass_when_certainty_positive(mod, monkeypatch):
    """validate_scores returns (True, score) when nearText probe gets back a hit."""

    def _fake_request(_method, _path, _body=None):
        return {
            "data": {
                "Get": {
                    "AgentMemories": [
                        {"_additional": {"id": "x", "certainty": 0.78, "distance": 0.4}}
                    ]
                }
            }
        }

    monkeypatch.setattr(mod, "_http_request", _fake_request)
    passed, score = mod.validate_scores("AgentMemories", "test probe")
    assert passed is True
    assert score == pytest.approx(0.78)


def test_validate_scores_returns_fail_when_certainty_zero(mod, monkeypatch):
    """validate_scores returns (False, 0.0) when certainty is 0 (vectorizer not working)."""

    def _fake_request(_method, _path, _body=None):
        return {
            "data": {
                "Get": {
                    "AgentMemories": [
                        {"_additional": {"id": "x", "certainty": 0.0, "distance": 1.0}}
                    ]
                }
            }
        }

    monkeypatch.setattr(mod, "_http_request", _fake_request)
    passed, score = mod.validate_scores("AgentMemories", "test probe")
    assert passed is False
    assert score == 0.0


def test_validate_scores_returns_fail_when_no_results(mod, monkeypatch):
    """validate_scores returns (False, 0.0) when the probe returns no rows."""

    def _fake_request(_method, _path, _body=None):
        return {"data": {"Get": {"AgentMemories": []}}}

    monkeypatch.setattr(mod, "_http_request", _fake_request)
    passed, score = mod.validate_scores("AgentMemories", "test probe")
    assert passed is False
    assert score == 0.0
