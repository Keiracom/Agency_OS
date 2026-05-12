"""Tests for scripts/smoke_test_skill_gen.py — parser + matcher + evaluator only.

NO e2e: tests never invoke src.skill_gen.generator.generate() or any real
subprocess. Per Elliot dispatch 2026-05-11, real-data run is deferred until
~2-3 directive cycles have accumulated in turn_logs.
"""

from __future__ import annotations

import importlib.util
import sys
from importlib.machinery import SourceFileLoader
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_SCRIPT = _REPO_ROOT / "scripts" / "smoke_test_skill_gen.py"
_REFERENCE = Path("/tmp/max_session_skill_notes_c322aa37.md")


def _load_harness():
    """Load scripts/smoke_test_skill_gen.py as a module.

    Registers the module in sys.modules before exec_module — required because
    @dataclass(frozen=True) with PEP-604 unions (`str | None`) calls
    `sys.modules.get(cls.__module__).__dict__` during field type resolution,
    which crashes if the module isn't registered first.
    """
    name = "smoke_test_skill_gen_harness"
    loader = SourceFileLoader(name, str(_SCRIPT))
    spec = importlib.util.spec_from_loader(name, loader)
    assert spec is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    try:
        loader.exec_module(mod)
    except BaseException:
        sys.modules.pop(name, None)
        raise
    return mod


# ---------- Parser tests against Max's real reference ----------


@pytest.mark.skipif(not _REFERENCE.exists(), reason="Max's reference file not on this host")
def test_parser_returns_14_patterns():
    h = _load_harness()
    patterns = h.parse_reference(_REFERENCE)
    assert len(patterns) == 14


@pytest.mark.skipif(not _REFERENCE.exists(), reason="Max's reference file not on this host")
def test_parser_categorises_how_avoid_correctly():
    h = _load_harness()
    patterns = h.parse_reference(_REFERENCE)
    how = [p for p in patterns if p.kind == "HOW"]
    avoid = [p for p in patterns if p.kind == "AVOID"]
    assert len(how) == 8
    assert len(avoid) == 6


@pytest.mark.skipif(not _REFERENCE.exists(), reason="Max's reference file not on this host")
def test_parser_covers_all_5_hard_req_categories():
    h = _load_harness()
    patterns = h.parse_reference(_REFERENCE)
    labels = {p.hard_req_label for p in patterns if p.is_hard_req}
    labels.discard(None)
    assert len(labels) == 5, f"expected 5 hard-req categories, got {labels}"


# ---------- Synthetic-input parser tests ----------


def test_parser_handles_synthetic_input(tmp_path: Path):
    h = _load_harness()
    p = tmp_path / "synthetic.md"
    p.write_text(
        "# header\n"
        "## WHAT\n"
        "- skipped (not HOW/AVOID)\n"
        "## HOW\n"
        "- Run verify_pr.sh for sanity\n"
        "- Use git cat-file -t to confirm hashes\n"
        "## AVOID\n"
        "- Do NOT fabricate completion claims\n"
    )
    patterns = h.parse_reference(p)
    assert len(patterns) == 3
    assert [pp.kind for pp in patterns] == ["HOW", "HOW", "AVOID"]
    assert all(pp.is_hard_req for pp in patterns)


def test_parser_skips_blank_bullets(tmp_path: Path):
    h = _load_harness()
    p = tmp_path / "blank.md"
    p.write_text("## HOW\n- \n- Real pattern here\n")
    patterns = h.parse_reference(p)
    assert len(patterns) == 1
    assert patterns[0].text == "Real pattern here"


# ---------- match_patterns tests ----------


def test_match_patterns_finds_all_when_skillmd_quotes_each(tmp_path: Path):
    h = _load_harness()
    ref_md = tmp_path / "ref.md"
    ref_md.write_text(
        "## HOW\n"
        "- Run verify_pr.sh before each merge\n"
        "- Use git cat-file -t to check hashes\n"
        "## AVOID\n"
        "- Do NOT fabricate PR numbers\n"
    )
    reference = h.parse_reference(ref_md)
    generated = "Steps: run verify_pr.sh first, then git cat-file -t. Never fabricate PR numbers."
    report = h.match_patterns(generated, reference)
    assert report.matched_count == 3
    assert report.missed == []


def test_match_patterns_sparse_skillmd_reports_missed(tmp_path: Path):
    h = _load_harness()
    ref_md = tmp_path / "ref.md"
    ref_md.write_text(
        "## HOW\n"
        "- Run verify_pr.sh first\n"
        "- Read SonarCloud bot output\n"
        "- Source env before tg -g\n"
    )
    reference = h.parse_reference(ref_md)
    generated = "Just run verify_pr.sh. Nothing else."
    report = h.match_patterns(generated, reference)
    assert report.matched_count == 1
    assert len(report.missed) == 2
    assert "SonarCloud bot comment retrieval" in report.hard_req_missing
    assert "tg -g env sourcing pattern" in report.hard_req_missing


# ---------- evaluate tests ----------


def test_evaluate_pass_requires_10_total_and_all_hard_reqs():
    h = _load_harness()
    matched = [
        h.Pattern("HOW", "x", True, label)
        for _, label in h._HARD_REQ_KEYWORDS  # all 5 hard-reqs hit
    ] + [h.Pattern("HOW", f"p{i}", False, None) for i in range(5)]  # +5 non-hard = 10 total matched
    missed = [h.Pattern("AVOID", f"m{i}", False, None) for i in range(4)]  # 4 missed -> 14 ref
    report = h.MatchReport(matched=matched, missed=missed, hard_req_matched=[], hard_req_missing=[])
    passed, summary = h.evaluate(report)
    assert passed is True
    assert "matched=10/14" in summary


def test_evaluate_fail_when_hard_req_missing():
    h = _load_harness()
    matched = [h.Pattern("HOW", f"p{i}", False, None) for i in range(12)]
    missed = [h.Pattern("AVOID", "m", False, None)]
    report = h.MatchReport(
        matched=matched,
        missed=missed,
        hard_req_matched=["verify_pr.sh usage pattern"],
        hard_req_missing=["git cat-file commit verification"],
    )
    passed, summary = h.evaluate(report)
    assert passed is False
    assert "git cat-file" in summary


def test_evaluate_fail_when_below_10_matches():
    h = _load_harness()
    matched = [h.Pattern("HOW", f"p{i}", False, None) for i in range(9)]
    missed = [h.Pattern("AVOID", "m", False, None) for _ in range(5)]
    report = h.MatchReport(matched=matched, missed=missed, hard_req_matched=[], hard_req_missing=[])
    passed, _ = h.evaluate(report)
    assert passed is False


# ---------- CLI tests (parse-only mode, no e2e) ----------


def test_cli_parse_only_returns_zero_when_reference_present():
    h = _load_harness()
    if not _REFERENCE.exists():
        pytest.skip("Max's reference file not on this host")
    rc = h.main([])  # no --run -> parse-only
    assert rc == 0


def test_cli_returns_two_when_reference_missing(tmp_path: Path):
    h = _load_harness()
    fake = tmp_path / "does-not-exist.md"
    rc = h.main(["--reference", str(fake)])
    assert rc == 2


def test_cli_run_without_session_id_returns_two():
    h = _load_harness()
    if not _REFERENCE.exists():
        pytest.skip("Max's reference file not on this host")
    rc = h.main(["--run"])  # --run without --session-id
    assert rc == 2
