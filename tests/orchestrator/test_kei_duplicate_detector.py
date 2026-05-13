"""Tests for scripts/kei_duplicate_detector.py — KEI-30.

bd find-duplicates + Linear commentCreate are injected via bd_fn /
comment_fn. No real bd, no real Linear network.

Covers:
  - duplicate above threshold → flagged + Linear comment posted
  - duplicate below threshold → not flagged, no comment
  - no pairs returned → clean no-dupe
  - candidate not present in bd output → no_pairs fallthrough
  - candidate ID malformed → candidate_not_in_bd
  - bd output parsing tolerates malformed json (returns {})
  - linear_comment=False → linear_comment field reads 'disabled'
  - Linear comment failure → linear_comment='failed', but duplicate_found stays true
  - multiple matches sorted by similarity desc; best_match is the top one
  - candidate appears in either side ('a' or 'b') of the pair
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPT = REPO_ROOT / "scripts" / "kei_duplicate_detector.py"
_spec = importlib.util.spec_from_file_location("kei_duplicate_detector", SCRIPT)
mod = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
sys.modules["kei_duplicate_detector"] = mod
_spec.loader.exec_module(mod)


def _bd_response(pairs: list[dict]) -> dict:
    return {
        "count": len(pairs),
        "method": "mechanical",
        "pairs": pairs,
        "schema_version": 1,
        "threshold": 0.5,
    }


def _pair(a_id: str, b_id: str, similarity: float, *, a_title="A", b_title="B") -> dict:
    return {
        "a": {"id": a_id, "title": a_title},
        "b": {"id": b_id, "title": b_title},
        "similarity": similarity,
    }


# ─── 1. Duplicate above threshold → flagged + comment posted ────────────


def test_duplicate_above_threshold_flags_and_posts_comment():
    pairs = [_pair("Agency_OS-cand", "Agency_OS-exist", 0.92, b_title="Existing KEI")]
    comments: list[tuple[str, str]] = []

    result = mod.run(
        candidate_bd_id="Agency_OS-cand",
        threshold=0.85,
        linear_comment=True,
        linear_issue_id="KEI-99",
        bd_fn=lambda: _bd_response(pairs),
        comment_fn=lambda iid, body: comments.append((iid, body)) or True,
    )

    assert result["duplicate_found"] is True
    assert result["reason"] == "above_threshold"
    assert result["best_match"]["bd_id"] == "Agency_OS-exist"
    assert result["best_match"]["similarity"] == 0.92
    assert result["linear_comment"] == "posted"
    assert len(comments) == 1
    assert comments[0][0] == "KEI-99"
    assert "0.92" in comments[0][1]
    assert "Existing KEI" in comments[0][1]


# ─── 2. Duplicate below threshold → not flagged ─────────────────────────


def test_duplicate_below_threshold_does_not_flag():
    pairs = [_pair("Agency_OS-cand", "Agency_OS-exist", 0.40)]
    comments: list = []

    result = mod.run(
        candidate_bd_id="Agency_OS-cand",
        threshold=0.85,
        linear_comment=True,
        linear_issue_id="KEI-99",
        bd_fn=lambda: _bd_response(pairs),
        comment_fn=lambda i, b: comments.append((i, b)) or True,
    )

    assert result["duplicate_found"] is False
    assert result["reason"] == "below_threshold"
    assert result["best_match"]["similarity"] == 0.40
    assert comments == []


# ─── 3. No pairs returned → no_pairs ────────────────────────────────────


def test_no_pairs_returns_clean_no_dupe():
    result = mod.run(
        candidate_bd_id="Agency_OS-cand",
        threshold=0.85,
        bd_fn=lambda: _bd_response([]),
    )
    assert result["duplicate_found"] is False
    assert result["reason"] == "no_pairs"
    assert result["best_match"] is None


# ─── 4. Candidate absent from bd output → no_pairs ──────────────────────


def test_candidate_absent_from_pairs_returns_no_pairs():
    """Bd returned pairs but none involve the candidate id — same shape as
    'no pairs' from the candidate's perspective."""
    pairs = [_pair("Agency_OS-x", "Agency_OS-y", 0.90)]
    result = mod.run(
        candidate_bd_id="Agency_OS-cand",
        threshold=0.85,
        bd_fn=lambda: _bd_response(pairs),
    )
    assert result["duplicate_found"] is False
    assert result["reason"] == "no_pairs"
    assert result["all_matches"] == []


# ─── 5. Malformed candidate ID → candidate_not_in_bd ────────────────────


def test_malformed_candidate_id_rejected():
    for bad in ("", "no-prefix-or-suffix", "spaces in id", "../etc/passwd"):
        result = mod.run(
            candidate_bd_id=bad,
            threshold=0.85,
            bd_fn=lambda: _bd_response([]),
        )
        assert result["reason"] == "candidate_not_in_bd", f"failed: {bad!r}"


# ─── 6. linear_comment=False → comment field reads 'disabled' ───────────


def test_linear_comment_disabled_when_flag_off():
    pairs = [_pair("Agency_OS-cand", "Agency_OS-exist", 0.95)]
    result = mod.run(
        candidate_bd_id="Agency_OS-cand",
        threshold=0.85,
        linear_comment=False,
        bd_fn=lambda: _bd_response(pairs),
    )
    assert result["duplicate_found"] is True
    assert result["linear_comment"] == "disabled"


# ─── 7. Linear comment failure → marked failed, duplicate_found stays ──


def test_linear_comment_failure_marks_failed_but_keeps_duplicate_found():
    """Comment posting is best-effort; a Linear API outage must NOT
    swallow the duplicate signal from the caller's perspective."""
    pairs = [_pair("Agency_OS-cand", "Agency_OS-exist", 0.95)]
    result = mod.run(
        candidate_bd_id="Agency_OS-cand",
        threshold=0.85,
        linear_comment=True,
        linear_issue_id="KEI-99",
        bd_fn=lambda: _bd_response(pairs),
        comment_fn=lambda i, b: False,  # Linear API error
    )
    assert result["duplicate_found"] is True
    assert result["linear_comment"] == "failed"


# ─── 8. Multiple matches sorted by similarity desc ──────────────────────


def test_multiple_matches_sorted_best_first():
    pairs = [
        _pair("Agency_OS-cand", "Agency_OS-mid", 0.72, b_title="Mid"),
        _pair("Agency_OS-cand", "Agency_OS-top", 0.93, b_title="Top"),
        _pair("Agency_OS-cand", "Agency_OS-low", 0.51, b_title="Low"),
    ]
    result = mod.run(
        candidate_bd_id="Agency_OS-cand",
        threshold=0.85,
        bd_fn=lambda: _bd_response(pairs),
    )
    assert result["best_match"]["bd_id"] == "Agency_OS-top"
    assert [m["bd_id"] for m in result["all_matches"]] == [
        "Agency_OS-top",
        "Agency_OS-mid",
        "Agency_OS-low",
    ]


# ─── 9. Candidate appears as 'b' side of pair ───────────────────────────


def test_candidate_on_b_side_of_pair_still_matches():
    pairs = [_pair("Agency_OS-exist", "Agency_OS-cand", 0.91, a_title="Existing")]
    result = mod.run(
        candidate_bd_id="Agency_OS-cand",
        threshold=0.85,
        bd_fn=lambda: _bd_response(pairs),
    )
    assert result["duplicate_found"] is True
    assert result["best_match"]["bd_id"] == "Agency_OS-exist"
    assert result["best_match"]["title"] == "Existing"


# ─── 10. bd_fn returns empty dict (parse failure) → no_pairs ────────────


def test_bd_parse_failure_falls_through_to_no_pairs():
    result = mod.run(
        candidate_bd_id="Agency_OS-cand",
        threshold=0.85,
        bd_fn=lambda: {},  # simulates bd unavailable / malformed JSON
    )
    assert result["duplicate_found"] is False
    assert result["reason"] == "no_pairs"


# ─── 11. CLI main exits 0 + prints JSON ─────────────────────────────────


def test_cli_main_prints_json_exit_zero(capsys, monkeypatch):
    import json as _json

    monkeypatch.setattr(mod, "_bd_find_duplicates", lambda *a, **kw: _bd_response([]))
    rc = mod.main(["--candidate-bd-id", "Agency_OS-test"])
    out = capsys.readouterr().out
    assert rc == 0
    payload = _json.loads(out)
    assert payload["candidate_bd_id"] == "Agency_OS-test"
    assert payload["duplicate_found"] is False
