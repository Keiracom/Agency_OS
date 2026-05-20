"""tests for scripts/cognee_auto_ingest.py — Agency_OS-zbvs watch-set fix.

Regression lock: the --watch set must cover the same root-level core-truth
docs as the --once set. Before the fix watch_loop watched only sub-dirs, so
ARCHITECTURE.md edits never propagated to Cognee after the watcher started.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPT = REPO_ROOT / "scripts" / "cognee_auto_ingest.py"
sys.path.insert(0, str(REPO_ROOT / "scripts"))


@pytest.fixture(scope="module")
def mod():
    spec = importlib.util.spec_from_file_location("cognee_auto_ingest", SCRIPT)
    m = importlib.util.module_from_spec(spec)
    sys.modules["cognee_auto_ingest"] = m
    spec.loader.exec_module(m)
    return m


def test_root_core_files_includes_architecture(mod):
    """ARCHITECTURE.md MUST be a tracked core-truth file — its absence from
    the watch set was the root cause of the memory-content drift."""
    assert "ARCHITECTURE.md" in mod._ROOT_CORE_FILES
    assert "CLAUDE.md" in mod._ROOT_CORE_FILES
    assert "DEFINITION_OF_DONE.md" in mod._ROOT_CORE_FILES


def test_files_in_uses_the_shared_root_core_constant(mod):
    """_files_in must include every _ROOT_CORE_FILES entry — so the --once
    set and the --watch set share one source of truth and cannot drift."""
    files = mod._files_in(REPO_ROOT)
    names = {p.name for p in files}
    for core in mod._ROOT_CORE_FILES:
        assert core in names, f"{core} missing from _files_in — watch/once drift risk"
