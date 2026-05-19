"""KEI Agency_OS-cd36 — tests for governance_freshness_probe.py.

Covers pure-Python logic (no Cognee or NATS network):
  - collect_governance_files globs the right paths
  - probe_snippet extracts heading or first non-empty line
  - classify_file: SYNCED / STALE / MISSING decision tree
  - _pick_marker: long-token preference, fallback to leading chars
  - probe_file: severity ladder (OK < WARN < CRITICAL) based on age + status
  - main exits non-zero on CRITICAL
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "orchestrator" / "governance_freshness_probe.py"


@pytest.fixture(scope="module")
def mod():
    spec = importlib.util.spec_from_file_location("governance_freshness_probe", SCRIPT)
    m = importlib.util.module_from_spec(spec)
    sys.modules["governance_freshness_probe"] = m
    spec.loader.exec_module(m)
    return m


# ---------------------------------------------------------------------------
# probe_snippet.
# ---------------------------------------------------------------------------


def test_probe_snippet_prefers_heading(mod, tmp_path) -> None:
    f = tmp_path / "x.md"
    f.write_text("# This Is The Heading\n\nbody text follows here.\n")
    assert mod.probe_snippet(f) == "This Is The Heading"


def test_probe_snippet_skips_frontmatter(mod, tmp_path) -> None:
    f = tmp_path / "x.md"
    f.write_text("---\nkey: value\n---\n# Real Heading\nbody\n")
    snippet = mod.probe_snippet(f)
    assert "Real Heading" in snippet
    assert "key" not in snippet


def test_probe_snippet_falls_back_to_first_non_empty(mod, tmp_path) -> None:
    f = tmp_path / "x.md"
    f.write_text("\n\nFirst body line without heading.\n")
    assert mod.probe_snippet(f) == "First body line without heading."


def test_probe_snippet_caps_at_120_chars(mod, tmp_path) -> None:
    f = tmp_path / "x.md"
    long_heading = "A" * 200
    f.write_text(f"# {long_heading}\n")
    snippet = mod.probe_snippet(f)
    assert len(snippet) <= 120


def test_probe_snippet_falls_back_to_filename_on_empty(mod, tmp_path) -> None:
    f = tmp_path / "empty.md"
    f.write_text("")
    assert mod.probe_snippet(f) == "empty.md"


# ---------------------------------------------------------------------------
# _pick_marker.
# ---------------------------------------------------------------------------


def test_pick_marker_returns_long_word(mod) -> None:
    text = "the layered_governance_matrix module retires nine modules"
    assert mod._pick_marker(text) == "layered_governance_matrix"


def test_pick_marker_strips_punctuation(mod) -> None:
    text = "Per `layered_governance_matrix_v1`, the retire list is fixed."
    marker = mod._pick_marker(text)
    assert "`" not in marker
    assert "layered_governance_matrix_v1" in marker


def test_pick_marker_falls_back_to_leading_chars(mod) -> None:
    text = "short words and tiny tokens only"
    marker = mod._pick_marker(text)
    assert marker == "short words and tiny tokens only"
    assert len(marker) <= 60


# ---------------------------------------------------------------------------
# classify_file.
# ---------------------------------------------------------------------------


def test_classify_synced_when_marker_in_results(mod) -> None:
    file_text = "Per layered_governance_matrix_v1 ratified Dave 2026-05-19"
    results = ["The layered_governance_matrix_v1 was ratified on 2026-05-19."]
    assert mod.classify_file(file_text, results) == "SYNCED"


def test_classify_stale_when_results_but_marker_absent(mod) -> None:
    file_text = "Per layered_governance_matrix_v1 ratified"
    results = ["completely different content about something else"]
    assert mod.classify_file(file_text, results) == "STALE"


def test_classify_missing_on_empty_results(mod) -> None:
    assert mod.classify_file("any text", []) == "MISSING"


# ---------------------------------------------------------------------------
# probe_file severity ladder.
# ---------------------------------------------------------------------------


def test_probe_file_ok_when_synced(mod, tmp_path) -> None:
    f = tmp_path / "g.md"
    f.write_text("# Distinctive title here\nbody\n")
    with (
        patch.object(mod, "git_commit_age_seconds", return_value=10),
        patch.object(mod, "cognee_top_k", return_value=["Distinctive title here matches"]),
    ):
        result = mod.probe_file(tmp_path, f)
    assert result["severity"] == "OK"
    assert result["cognee_status"] == "SYNCED"


def test_probe_file_warn_when_missing_over_1h(mod, tmp_path) -> None:
    f = tmp_path / "g.md"
    f.write_text("# Distinctive title here\n")
    with (
        patch.object(mod, "git_commit_age_seconds", return_value=3700),
        patch.object(mod, "cognee_top_k", return_value=[]),
    ):
        result = mod.probe_file(tmp_path, f)
    assert result["severity"] == "WARN"
    assert result["cognee_status"] == "MISSING"


def test_probe_file_critical_when_missing_over_6h(mod, tmp_path) -> None:
    f = tmp_path / "g.md"
    f.write_text("# Distinctive title here\n")
    with (
        patch.object(mod, "git_commit_age_seconds", return_value=7 * 3600),
        patch.object(mod, "cognee_top_k", return_value=[]),
    ):
        result = mod.probe_file(tmp_path, f)
    assert result["severity"] == "CRITICAL"


def test_probe_file_untracked_skipped(mod, tmp_path) -> None:
    f = tmp_path / "new.md"
    f.write_text("# brand new\n")
    with patch.object(mod, "git_commit_age_seconds", return_value=None):
        result = mod.probe_file(tmp_path, f)
    assert result["severity"] == "OK"
    assert result["cognee_status"] == "UNTRACKED"


def test_probe_file_ok_within_grace_window(mod, tmp_path) -> None:
    """Status MISSING but age < 1h → still within SLO grace; severity=OK."""
    f = tmp_path / "g.md"
    f.write_text("# fresh content\n")
    with (
        patch.object(mod, "git_commit_age_seconds", return_value=600),
        patch.object(mod, "cognee_top_k", return_value=[]),
    ):
        result = mod.probe_file(tmp_path, f)
    assert result["severity"] == "OK"


# ---------------------------------------------------------------------------
# collect_governance_files.
# ---------------------------------------------------------------------------


def test_collect_governance_files_returns_real_repo_files(mod) -> None:
    """Sanity check against the live repo — we have docs/governance + CLAUDE.md."""
    files = mod.collect_governance_files(REPO_ROOT)
    paths = {str(p.relative_to(REPO_ROOT)) for p in files}
    assert "CLAUDE.md" in paths
    governance_present = any(p.startswith("docs/governance/") for p in paths)
    assert governance_present


# ---------------------------------------------------------------------------
# main exit code.
# ---------------------------------------------------------------------------


def test_main_exits_2_on_critical(mod, monkeypatch) -> None:
    fake_report = [
        {"severity": "CRITICAL", "path": "x", "age_seconds": 99999, "cognee_status": "MISSING"}
    ]
    monkeypatch.setattr(mod, "run_probe", lambda root: fake_report)
    monkeypatch.setattr(mod, "_print_report", lambda r, emit_json: None)
    assert mod.main([]) == 2


def test_main_exits_0_on_no_critical(mod, monkeypatch) -> None:
    fake_report = [
        {"severity": "OK", "path": "a", "age_seconds": 10, "cognee_status": "SYNCED"},
        {"severity": "WARN", "path": "b", "age_seconds": 3700, "cognee_status": "MISSING"},
    ]
    monkeypatch.setattr(mod, "run_probe", lambda root: fake_report)
    monkeypatch.setattr(mod, "_print_report", lambda r, emit_json: None)
    assert mod.main([]) == 0
