"""Unit tests for src.governance.loader — Agency_OS-ngw2.

Covers the three-tier loader's HOT/POINTER/REFERENCE behaviours and
fail-loud budget enforcement. No external dependencies — tests build a
synthetic repo root inside tmp_path + inject a fake recall_fn for the
POINTER tier so cognee_recall isn't required.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from src.governance.loader import (
    BUDGET_HOT_TOKENS,
    BUDGET_SESSION_RECALL_TOKENS,
    GovernanceBudgetExceeded,
    GovernanceConfigError,
    GovernanceLoader,
    estimate_tokens,
)

# ---------------------------------------------------------------------------
# Fixtures: synthetic repo root with the three HOT-tier required files
# ---------------------------------------------------------------------------


def _build_repo(tmp_path: Path, *, claude_md_chars: int = 2000, cache_chars: int = 2000) -> Path:
    """Return tmp_path with IDENTITY.md, CLAUDE.md, _hot_pointer_cache.md."""
    (tmp_path / "IDENTITY.md").write_text("callsign: orion\n")
    (tmp_path / "CLAUDE.md").write_text("c" * claude_md_chars)
    gov_dir = tmp_path / "docs" / "governance"
    gov_dir.mkdir(parents=True)
    (gov_dir / "_hot_pointer_cache.md").write_text("h" * cache_chars)
    return tmp_path


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    return _build_repo(tmp_path)


@pytest.fixture
def loader(repo: Path) -> GovernanceLoader:
    return GovernanceLoader(repo_root=repo, callsign="orion", recall_fn=lambda k: "x" * 100)


# ---------------------------------------------------------------------------
# estimate_tokens — sanity
# ---------------------------------------------------------------------------


def test_estimate_tokens_matches_4_chars_per_token() -> None:
    assert estimate_tokens("x" * 400) == 100
    assert estimate_tokens("") == 0


# ---------------------------------------------------------------------------
# HOT tier
# ---------------------------------------------------------------------------


def test_load_hot_succeeds_under_budget(loader: GovernanceLoader) -> None:
    text = loader.load_hot()
    assert "callsign: orion" in text
    assert "HOT TIER 1/3" in text and "HOT TIER 2/3" in text and "HOT TIER 3/3" in text
    assert estimate_tokens(text) <= BUDGET_HOT_TOKENS


def test_load_hot_fails_loud_over_budget(tmp_path: Path) -> None:
    # Hot budget is 8000 tokens = ~32000 chars. Make CLAUDE.md big enough
    # to push the combined past that.
    repo = _build_repo(tmp_path, claude_md_chars=34000, cache_chars=100)
    loader = GovernanceLoader(repo_root=repo, callsign="orion")
    with pytest.raises(GovernanceBudgetExceeded, match="HOT tier"):
        loader.load_hot()


def test_load_hot_fails_loud_when_identity_missing(tmp_path: Path) -> None:
    repo = _build_repo(tmp_path)
    (repo / "IDENTITY.md").unlink()
    loader = GovernanceLoader(repo_root=repo, callsign="orion")
    with pytest.raises(GovernanceConfigError, match="IDENTITY.md"):
        loader.load_hot()


def test_load_hot_fails_loud_when_pointer_cache_missing(tmp_path: Path) -> None:
    repo = _build_repo(tmp_path)
    (repo / "docs" / "governance" / "_hot_pointer_cache.md").unlink()
    loader = GovernanceLoader(repo_root=repo, callsign="orion")
    with pytest.raises(GovernanceConfigError, match="_hot_pointer_cache.md"):
        loader.load_hot()


def test_load_hot_fails_loud_when_claude_md_missing(tmp_path: Path) -> None:
    repo = _build_repo(tmp_path)
    (repo / "CLAUDE.md").unlink()
    loader = GovernanceLoader(repo_root=repo, callsign="orion")
    with pytest.raises(GovernanceConfigError, match="CLAUDE.md"):
        loader.load_hot()


# ---------------------------------------------------------------------------
# POINTER tier
# ---------------------------------------------------------------------------


def test_load_pointer_returns_recall_result_under_budget(loader: GovernanceLoader) -> None:
    out = loader.load_pointer("law-i-a-architecture-first")
    assert out == "x" * 100
    # ~25 tokens charged; session budget mostly untouched
    assert loader.session_recall_used == estimate_tokens("x" * 100)


def test_load_pointer_fails_loud_when_recall_exceeds_per_call_budget(repo: Path) -> None:
    # Per-call budget is 500 tokens = ~2000 chars. Return 2500 chars → fail.
    big_recall = lambda k: "y" * 2500  # noqa: E731
    loader = GovernanceLoader(repo_root=repo, callsign="orion", recall_fn=big_recall)
    with pytest.raises(GovernanceBudgetExceeded, match="POINTER recall_key"):
        loader.load_pointer("rule-1-verify")


def test_load_pointer_passes_recall_key_to_backend(repo: Path) -> None:
    captured: dict[str, str] = {}

    def fake_recall(k: str) -> str:
        captured["key"] = k
        return "ok"

    loader = GovernanceLoader(repo_root=repo, callsign="orion", recall_fn=fake_recall)
    loader.load_pointer("persona-orion")
    assert captured["key"] == "persona-orion"


# ---------------------------------------------------------------------------
# REFERENCE tier
# ---------------------------------------------------------------------------


def test_load_reference_returns_file_text(loader: GovernanceLoader, repo: Path) -> None:
    (repo / "ARCHITECTURE.md").write_text("# arch\nstuff\n")
    text = loader.load_reference("ARCHITECTURE.md")
    assert text == "# arch\nstuff\n"


def test_load_reference_fails_loud_when_missing(loader: GovernanceLoader) -> None:
    with pytest.raises(GovernanceConfigError, match="REFERENCE file missing"):
        loader.load_reference("does/not/exist.md")


def test_load_reference_charges_session_recall_budget(loader: GovernanceLoader, repo: Path) -> None:
    (repo / "big.md").write_text("z" * 4000)  # ~1000 tokens
    loader.load_reference("big.md")
    assert loader.session_recall_used == 1000


# ---------------------------------------------------------------------------
# Cumulative session-recall budget
# ---------------------------------------------------------------------------


def test_session_recall_cumulative_pointer_charges(repo: Path) -> None:
    # Each pointer call returns 400 chars = 100 tokens; do 10 calls → 1000 tokens used
    loader = GovernanceLoader(repo_root=repo, callsign="orion", recall_fn=lambda k: "x" * 400)
    for _ in range(10):
        loader.load_pointer("rule-1-verify")
    assert loader.session_recall_used == 1000
    assert loader.session_recall_remaining == BUDGET_SESSION_RECALL_TOKENS - 1000


def test_session_recall_fails_loud_when_cumulative_exceeded(repo: Path) -> None:
    # 11 pointer calls × 500 tokens each = 5500 tokens > 5000-token session budget
    loader = GovernanceLoader(repo_root=repo, callsign="orion", recall_fn=lambda k: "x" * 2000)
    # 10 calls cleanly consume 5000 (10 * 500)
    for _ in range(10):
        loader.load_pointer("rule-1-verify")
    assert loader.session_recall_used == 5000
    # 11th call charges 500 more → trips cumulative budget
    with pytest.raises(GovernanceBudgetExceeded, match="session-recall total"):
        loader.load_pointer("rule-2-coordinate")


def test_session_recall_mixed_pointer_and_reference_share_budget(
    loader: GovernanceLoader, repo: Path
) -> None:
    # Load a 1000-token reference, then 100-token pointers; total stays in budget
    (repo / "big.md").write_text("z" * 4000)
    loader.load_reference("big.md")  # +1000 tokens
    assert loader.session_recall_used == 1000
    loader.load_pointer("rule-1-verify")  # +25 tokens
    assert loader.session_recall_used == 1025


# ---------------------------------------------------------------------------
# FAIL-LOUD stderr marker
# ---------------------------------------------------------------------------


def test_fail_loud_emits_stderr_marker(repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    loader = GovernanceLoader(repo_root=repo, callsign="orion", recall_fn=lambda k: "y" * 2500)
    with pytest.raises(GovernanceBudgetExceeded):
        loader.load_pointer("law-xv-d-step-0-restate")
    err = capsys.readouterr().err
    assert "FAIL-LOUD:" in err
    assert "POINTER recall_key" in err
