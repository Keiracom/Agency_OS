"""Unit tests for governance_rules_atomizer.

Covers iter_governance_sources (path enumeration in deterministic order +
globs + skip-on-missing) + atomize_governance_file (success + oversize
reject + atomizer exception) + load/append_state idempotency + run()
orchestration (skip-already-seen + dry-run + execute + rc=0/1).

bd: Agency_OS-blka (Phase Alpha — Governance Rules Atomization)
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

from src.keiracom_system.atomization import governance_rules_atomizer as mod
from src.keiracom_system.atomization.governance_rules_atomizer import (
    GOVERNANCE_SOURCE_KIND,
    MAX_GOVERNANCE_BYTES,
    _build_source_ref,
    append_state,
    atomize_governance_file,
    iter_governance_sources,
    load_state,
    run,
)

# ─── Fixtures ──────────────────────────────────────────────────────────────────


def _make_repo(tmp_path: Path) -> Path:
    """Build a minimal fake repo tree matching the dispatch's source surface."""
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "CLAUDE.md").write_text("# Project CLAUDE.md\nProject-level rules.")
    modules = repo / ".claude" / "modules"
    modules.mkdir(parents=True)
    (modules / "_session_start.md").write_text("# Session Start")
    (modules / "_orchestrator.md").write_text("# Orchestrator")
    (modules / "z_last.md").write_text("# Last module (sort verify)")
    gov = repo / "docs" / "governance"
    gov.mkdir(parents=True)
    (gov / "CONSOLIDATED_RULES.md").write_text("# CONSOLIDATED_RULES\nLAW I-A through LAW XVII.")
    (gov / "_hot_pointer_cache.md").write_text("# Hot pointer cache")
    return repo


# ─── iter_governance_sources ───────────────────────────────────────────────────


def test_iter_governance_sources_yields_in_deterministic_order(tmp_path: Path):
    """global (if present) → project CLAUDE.md → modules sorted → governance sorted."""
    repo = _make_repo(tmp_path)
    sources = list(iter_governance_sources(repo, include_global=False))
    names = [p.name for p in sources]
    assert names == [
        "CLAUDE.md",
        "_orchestrator.md",
        "_session_start.md",
        "z_last.md",
        "CONSOLIDATED_RULES.md",
        "_hot_pointer_cache.md",
    ]


def test_iter_governance_sources_skips_missing_dirs(tmp_path: Path):
    """No .claude/modules + no docs/governance → only CLAUDE.md (if present)."""
    repo = tmp_path / "empty_repo"
    repo.mkdir()
    (repo / "CLAUDE.md").write_text("# minimal")
    sources = list(iter_governance_sources(repo, include_global=False))
    assert [p.name for p in sources] == ["CLAUDE.md"]


def test_iter_governance_sources_skips_when_no_project_claude_md(tmp_path: Path):
    """Repo without CLAUDE.md → still yields modules + governance."""
    repo = tmp_path / "noclaude"
    repo.mkdir()
    (repo / "docs" / "governance").mkdir(parents=True)
    (repo / "docs" / "governance" / "x.md").write_text("# x")
    sources = list(iter_governance_sources(repo, include_global=False))
    assert [p.name for p in sources] == ["x.md"]


def test_iter_governance_sources_excludes_global_when_flag_false(tmp_path: Path):
    """include_global=False MUST skip ~/.claude/CLAUDE.md even if it exists."""
    repo = _make_repo(tmp_path)
    sources = list(iter_governance_sources(repo, include_global=False))
    # No path should match the home-config global CLAUDE.md path
    assert all(s != mod.DEFAULT_GLOBAL_CLAUDE_MD for s in sources)


# ─── _build_source_ref ─────────────────────────────────────────────────────────


def test_build_source_ref_relative_to_repo(tmp_path: Path):
    repo = tmp_path / "r"
    repo.mkdir()
    inside = repo / "CLAUDE.md"
    inside.touch()
    assert _build_source_ref(inside, repo) == "governance/CLAUDE.md"


def test_build_source_ref_global_claude_uses_stable_label(tmp_path: Path):
    repo = tmp_path / "r"
    repo.mkdir()
    # Global CLAUDE.md is outside repo → falls into the stable-label branch
    ref = _build_source_ref(mod.DEFAULT_GLOBAL_CLAUDE_MD, repo)
    assert ref == "governance/~/.claude/CLAUDE.md"


def test_build_source_ref_outside_repo_falls_through_to_full_path(tmp_path: Path):
    repo = tmp_path / "r"
    repo.mkdir()
    elsewhere = tmp_path / "elsewhere" / "weird.md"
    elsewhere.parent.mkdir(parents=True)
    elsewhere.touch()
    ref = _build_source_ref(elsewhere, repo)
    assert ref.startswith("governance/")
    assert str(elsewhere) in ref


# ─── load_state / append_state ────────────────────────────────────────────────


def test_load_state_returns_empty_when_file_missing(tmp_path: Path):
    assert load_state(tmp_path / "no.jsonl") == set()


def test_load_state_only_ok_true_rows_count_as_seen(tmp_path: Path):
    state = tmp_path / "state.jsonl"
    state.write_text(
        '{"source_ref":"governance/a","ok":true,"info":"ok"}\n'
        '{"source_ref":"governance/b","ok":false,"info":"err"}\n'
        '{"source_ref":"governance/c","ok":true}\n'
    )
    seen = load_state(state)
    assert seen == {"governance/a", "governance/c"}


def test_load_state_tolerates_malformed_lines(tmp_path: Path):
    state = tmp_path / "state.jsonl"
    state.write_text(
        '{"source_ref":"governance/a","ok":true}\n'
        "not json at all\n"
        '{"source_ref":"governance/b","ok":true}\n'
    )
    assert load_state(state) == {"governance/a", "governance/b"}


def test_append_state_creates_parent_dir(tmp_path: Path):
    state = tmp_path / "deep" / "nested" / "state.jsonl"
    append_state(state, {"source_ref": "governance/x", "ok": True, "info": "ok"})
    assert state.exists()
    assert json.loads(state.read_text().strip())["source_ref"] == "governance/x"


# ─── atomize_governance_file ───────────────────────────────────────────────────


def test_atomize_governance_file_invokes_atomizer_with_correct_kind(tmp_path: Path):
    repo = _make_repo(tmp_path)
    gov = repo / "CLAUDE.md"
    fake_atomizer = MagicMock()
    fake_atomizer.atomize.return_value = MagicMock(job_id="job-1", atoms_produced=3)

    ok, info = atomize_governance_file(
        atomizer=fake_atomizer,
        governance_path=gov,
        repo_root=repo,
    )
    assert ok is True
    assert "job-1" in info
    assert "atoms=3" in info
    call_kwargs = fake_atomizer.atomize.call_args.kwargs
    assert call_kwargs["source_kind"] == GOVERNANCE_SOURCE_KIND
    assert call_kwargs["source_ref"] == "governance/CLAUDE.md"
    assert "Project CLAUDE.md" in call_kwargs["source_text"]


def test_atomize_governance_file_rejects_oversize(tmp_path: Path):
    repo = tmp_path / "r"
    repo.mkdir()
    huge = repo / "huge.md"
    huge.write_text("x" * (MAX_GOVERNANCE_BYTES + 1))
    fake_atomizer = MagicMock()
    ok, info = atomize_governance_file(
        atomizer=fake_atomizer,
        governance_path=huge,
        repo_root=repo,
    )
    assert ok is False
    assert "exceeds" in info
    assert "MAX_GOVERNANCE_BYTES" in info
    # Atomizer MUST NOT have been called — no wasted LLM tokens on oversize
    fake_atomizer.atomize.assert_not_called()


def test_atomize_governance_file_catches_atomizer_exception(tmp_path: Path):
    repo = _make_repo(tmp_path)
    fake_atomizer = MagicMock()
    fake_atomizer.atomize.side_effect = RuntimeError("LLM rate-limited")
    ok, info = atomize_governance_file(
        atomizer=fake_atomizer,
        governance_path=repo / "CLAUDE.md",
        repo_root=repo,
    )
    assert ok is False
    assert "LLM rate-limited" in info


# ─── run() orchestration ───────────────────────────────────────────────────────


def test_run_dry_run_does_not_call_atomizer(tmp_path: Path):
    repo = _make_repo(tmp_path)
    fake_atomizer = MagicMock()
    rc = run(
        atomizer=fake_atomizer,
        repo_root=repo,
        state_path=tmp_path / "state.jsonl",
        execute=False,
        include_global=False,
    )
    assert rc == 0
    fake_atomizer.atomize.assert_not_called()


def test_run_execute_atomizes_all_sources_and_returns_zero(tmp_path: Path):
    repo = _make_repo(tmp_path)
    fake_atomizer = MagicMock()
    fake_atomizer.atomize.return_value = MagicMock(job_id="j", atoms_produced=1)
    state = tmp_path / "state.jsonl"
    rc = run(
        atomizer=fake_atomizer,
        repo_root=repo,
        state_path=state,
        execute=True,
        include_global=False,
    )
    assert rc == 0
    # 6 sources: CLAUDE.md + 3 modules + 2 governance docs
    assert fake_atomizer.atomize.call_count == 6
    # State file MUST carry all 6 ok=true rows
    seen = load_state(state)
    assert len(seen) == 6


def test_run_skips_already_seen_sources(tmp_path: Path):
    repo = _make_repo(tmp_path)
    fake_atomizer = MagicMock()
    fake_atomizer.atomize.return_value = MagicMock(job_id="j", atoms_produced=1)
    state = tmp_path / "state.jsonl"
    # Pre-seed state to mark CLAUDE.md as already-atomized
    append_state(state, {"source_ref": "governance/CLAUDE.md", "ok": True, "info": "prior"})
    rc = run(
        atomizer=fake_atomizer,
        repo_root=repo,
        state_path=state,
        execute=True,
        include_global=False,
    )
    assert rc == 0
    # 5 sources atomized (skipped CLAUDE.md)
    assert fake_atomizer.atomize.call_count == 5
    called_refs = {c.kwargs["source_ref"] for c in fake_atomizer.atomize.call_args_list}
    assert "governance/CLAUDE.md" not in called_refs


def test_run_returns_one_on_any_atomizer_failure(tmp_path: Path):
    repo = _make_repo(tmp_path)
    fake_atomizer = MagicMock()
    # First call succeeds, second raises
    call_count = {"n": 0}

    def _side_effect(**_kwargs: Any) -> Any:
        call_count["n"] += 1
        if call_count["n"] == 2:
            raise RuntimeError("LLM 500")
        return MagicMock(job_id="j", atoms_produced=1)

    fake_atomizer.atomize.side_effect = _side_effect
    rc = run(
        atomizer=fake_atomizer,
        repo_root=repo,
        state_path=tmp_path / "state.jsonl",
        execute=True,
        include_global=False,
    )
    assert rc == 1


def test_run_returns_two_when_repo_root_missing(tmp_path: Path):
    fake_atomizer = MagicMock()
    rc = run(
        atomizer=fake_atomizer,
        repo_root=tmp_path / "does-not-exist",
        state_path=tmp_path / "state.jsonl",
        execute=True,
    )
    assert rc == 2


# ─── CLI smoke ─────────────────────────────────────────────────────────────────


def test_cli_dry_run_lists_source_refs(tmp_path: Path, capsys):
    repo = _make_repo(tmp_path)
    rc = mod.main(argv=["--repo-root", str(repo), "--no-global", "--log-level", "ERROR"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "governance/CLAUDE.md" in out
    assert "governance/.claude/modules/_orchestrator.md" in out
    assert "governance/docs/governance/CONSOLIDATED_RULES.md" in out


def test_cli_execute_rejects_without_wired_factory(tmp_path: Path, capsys):
    """--execute on standalone CLI MUST fail loudly — no LLM/DB wired."""
    repo = _make_repo(tmp_path)
    rc = mod.main(
        argv=["--repo-root", str(repo), "--no-global", "--execute", "--log-level", "ERROR"]
    )
    assert rc == 2


def test_cli_requires_repo_root():
    with pytest.raises(SystemExit):
        mod.main(argv=[])
