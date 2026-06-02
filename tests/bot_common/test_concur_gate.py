"""tests for src/bot_common/concur_gate.py — R1 outbound concur gate (v2, inbox-signal).

v2 (Dave directive 2026-06-02): the gate's signal source is the inbox-watcher
processed/*.json directory, not the dead #execution Slack channel. The gate now
requires ≥2 distinct deliberator [CONCUR] within a lookback window, excludes the
synthesis author (independence rule), and has no CONCUR_GATE_SKIP env-var bypass.

Coverage:
  - should_gate: anchored-regex token detection (unchanged from v1)
  - find_recent_concurrers: parses processed/*.json envelopes, filters by mtime
  - gate_check acceptance criteria (dispatch-prescribed):
      (a) passes with 2 distinct non-author concurrers
      (b) BLOCKS with only 1 concurrer
      (c) BLOCKS when only concurrer is the author
      (d) BLOCKS when CONCUR_GATE_SKIP=1 (env var no longer opens the gate)
  - Independence: synthesis_author excluded; None → 3-deliberator safe default
  - Hold-file persistence under /tmp/<callsign>-pending-concur/
  - No surviving import of env_skip / CONCUR_GATE_SKIP

All filesystem traffic redirected to tmp_path via the processed_dir injection
point on gate_check + the _pending_dir monkeypatch.
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path

import pytest

from src.bot_common import concur_gate

# ─────────────────────────────────────────────────────────────────────────────
# should_gate — anchored-token detection (unchanged from v1 / KEI-38)
# ─────────────────────────────────────────────────────────────────────────────


def test_should_gate_matches_concur_token() -> None:
    assert concur_gate.should_gate("[CONCUR:max] release looks fine")


def test_should_gate_matches_block_token() -> None:
    assert concur_gate.should_gate("[BLOCK:elliot] hold on the rebase")


def test_should_gate_case_insensitive_token() -> None:
    assert concur_gate.should_gate("[concur:scout] verified")
    assert concur_gate.should_gate("[Block:Aiden] stop")


def test_should_gate_does_not_match_prose_concur() -> None:
    """KEI-38 — prose containing 'concur' must NOT trigger the gate."""
    assert not concur_gate.should_gate("we concur on this approach")
    assert not concur_gate.should_gate("shape-concur with hold")
    assert not concur_gate.should_gate("Max FINAL CONCUR on PR #842")


def test_should_gate_does_not_match_final_concur_token() -> None:
    assert not concur_gate.should_gate("[FINAL CONCUR:ELLIOT] merging now")


def test_should_gate_does_not_match_concur_request_stub() -> None:
    """[CONCUR-REQUEST:<callsign>] is the hold-stub itself — breaks recursion."""
    assert not concur_gate.should_gate(
        "[CONCUR-REQUEST:AIDEN] requesting concurrence from peer on: PR merge"
    )


def test_should_gate_does_not_match_escalation_sentinel() -> None:
    """KEI-79: [ESCALATION-INITIATED:<callsign>:<task-id>] is exempt."""
    assert not concur_gate.should_gate("[ESCALATION-INITIATED:orion:KEI-99] direct-post path")


def test_should_gate_no_match_on_completion_prose() -> None:
    assert not concur_gate.should_gate("Just committed the fix.")
    assert not concur_gate.should_gate("PR merged to main.")
    assert not concur_gate.should_gate("Task done, all stores written.")


def test_should_gate_no_match_on_empty_brackets() -> None:
    assert not concur_gate.should_gate("[CONCUR:] missing callsign")


# ─────────────────────────────────────────────────────────────────────────────
# find_recent_concurrers — processed-dir scan
# ─────────────────────────────────────────────────────────────────────────────


def _write_envelope(
    pdir: Path,
    name: str,
    sender: str,
    body: str,
    *,
    mtime: float | None = None,
) -> Path:
    """Materialise an inbox-watcher processed envelope at <pdir>/<name>.json."""
    pdir.mkdir(parents=True, exist_ok=True)
    path = pdir / name
    path.write_text(json.dumps({"from": sender, "body": body}))
    if mtime is not None:
        os.utime(path, (mtime, mtime))
    return path


def test_find_recent_concurrers_picks_up_distinct_senders(tmp_path) -> None:
    """Two distinct deliberators posting [CONCUR:elliot] → set of two callsigns."""
    pdir = tmp_path / "processed"
    _write_envelope(pdir, "aiden_1.json", "aiden", "[CONCUR:elliot] looks good")
    _write_envelope(pdir, "max_1.json", "max", "approved\n[CONCUR:elliot]")
    found = concur_gate.find_recent_concurrers("elliot", processed_dir=pdir)
    assert found == {"aiden", "max"}


def test_find_recent_concurrers_deduplicates_same_sender(tmp_path) -> None:
    """Same sender concurring twice → counted once."""
    pdir = tmp_path / "processed"
    _write_envelope(pdir, "aiden_1.json", "aiden", "[CONCUR:elliot] first")
    _write_envelope(pdir, "aiden_2.json", "aiden", "[CONCUR:elliot] retry")
    assert concur_gate.find_recent_concurrers("elliot", processed_dir=pdir) == {"aiden"}


def test_find_recent_concurrers_skips_stale_envelopes(tmp_path, monkeypatch) -> None:
    """Envelopes older than the lookback window are not counted."""
    monkeypatch.setenv("CONCUR_LOOKBACK_MINUTES", "10")
    pdir = tmp_path / "processed"
    now = 1_780_000_000.0
    _write_envelope(pdir, "fresh.json", "aiden", "[CONCUR:elliot]", mtime=now - 60)
    _write_envelope(pdir, "stale.json", "max", "[CONCUR:elliot]", mtime=now - 60 * 60)
    found = concur_gate.find_recent_concurrers("elliot", now=now, processed_dir=pdir)
    assert found == {"aiden"}


def test_find_recent_concurrers_ignores_envelopes_without_token(tmp_path) -> None:
    """Envelope with no [CONCUR:elliot] body → not counted, even from a deliberator."""
    pdir = tmp_path / "processed"
    _write_envelope(pdir, "aiden.json", "aiden", "status update, nothing to concur")
    assert concur_gate.find_recent_concurrers("elliot", processed_dir=pdir) == set()


def test_find_recent_concurrers_handles_malformed_envelope(tmp_path) -> None:
    """Malformed JSON / missing 'from' / non-dict payload → fail closed (skip)."""
    pdir = tmp_path / "processed"
    pdir.mkdir()
    (pdir / "bad.json").write_text("not json at all {{{")
    (pdir / "no_from.json").write_text(json.dumps({"body": "[CONCUR:elliot]"}))
    (pdir / "non_dict.json").write_text(json.dumps(["a", "list", "payload"]))
    _write_envelope(pdir, "good.json", "aiden", "[CONCUR:elliot]")
    found = concur_gate.find_recent_concurrers("elliot", processed_dir=pdir)
    assert found == {"aiden"}


def test_find_recent_concurrers_missing_processed_dir_returns_empty(tmp_path) -> None:
    """No processed/ dir → empty set (gate then fails closed downstream)."""
    pdir = tmp_path / "nonexistent" / "processed"
    assert concur_gate.find_recent_concurrers("elliot", processed_dir=pdir) == set()


def test_find_recent_concurrers_extracts_token_from_alternate_fields(tmp_path) -> None:
    """Token may live in body/text/subject/brief/message — all are scanned."""
    pdir = tmp_path / "processed"
    pdir.mkdir()
    (pdir / "subject.json").write_text(
        json.dumps({"from": "aiden", "subject": "[CONCUR:elliot] design"})
    )
    (pdir / "text.json").write_text(
        json.dumps({"from": "max", "text": "approval: [CONCUR:elliot]"})
    )
    (pdir / "brief.json").write_text(
        json.dumps({"from": "atlas", "brief": "[CONCUR:elliot] safety lens"})
    )
    found = concur_gate.find_recent_concurrers("elliot", processed_dir=pdir)
    assert found == {"aiden", "max", "atlas"}


def test_find_recent_concurrers_accepts_sender_field_alias(tmp_path) -> None:
    """`sender` is an accepted alias for `from` (Telegram relay envelope shape)."""
    pdir = tmp_path / "processed"
    pdir.mkdir()
    (pdir / "sender.json").write_text(json.dumps({"sender": "aiden", "text": "[CONCUR:elliot] ok"}))
    assert concur_gate.find_recent_concurrers("elliot", processed_dir=pdir) == {"aiden"}


# ─────────────────────────────────────────────────────────────────────────────
# gate_check — acceptance criteria (Dave directive 2026-06-02)
# ─────────────────────────────────────────────────────────────────────────────


@pytest.fixture
def isolated_pending_dir(tmp_path, monkeypatch):
    """Redirect _pending_dir away from real /tmp."""
    monkeypatch.setattr(concur_gate, "_pending_dir", lambda cs: tmp_path / "pending" / cs)
    return tmp_path


def test_gate_check_no_trigger_allows(isolated_pending_dir) -> None:
    """No [CONCUR/BLOCK:...] token → (True, None) without any inbox scan."""
    allow, replacement = concur_gate.gate_check("Standing by, no shipping happening.", "elliot")
    assert allow is True
    assert replacement is None


def test_gate_check_a_passes_with_two_distinct_non_author_concurrers(
    isolated_pending_dir,
) -> None:
    """Acceptance (a): two distinct deliberator [CONCUR:elliot] from non-author → ALLOW."""
    pdir = isolated_pending_dir / "processed"
    _write_envelope(pdir, "aiden.json", "aiden", "[CONCUR:elliot] yes")
    _write_envelope(pdir, "max.json", "max", "[CONCUR:elliot] yes")
    allow, replacement = concur_gate.gate_check(
        "[CONCUR:atlas] release looks fine",
        "elliot",
        synthesis_author="elliot",
        processed_dir=pdir,
    )
    assert allow is True, replacement
    assert replacement is None


def test_gate_check_b_blocks_with_only_one_concurrer(isolated_pending_dir) -> None:
    """Acceptance (b): only 1 deliberator concurrer → BLOCK + replacement + hold file."""
    pdir = isolated_pending_dir / "processed"
    _write_envelope(pdir, "aiden.json", "aiden", "[CONCUR:elliot] yes")
    text = "[CONCUR:atlas] release looks fine"
    allow, replacement = concur_gate.gate_check(
        text,
        "elliot",
        synthesis_author="elliot",
        processed_dir=pdir,
    )
    assert allow is False
    assert replacement is not None
    assert "[CONCUR-REQUEST:ELLIOT]" in replacement
    # Hold file written.
    hold_files = list((isolated_pending_dir / "pending" / "elliot").glob("*.txt"))
    assert len(hold_files) == 1
    assert hold_files[0].read_text() == text


def test_gate_check_c_blocks_when_only_concurrer_is_the_author(
    isolated_pending_dir,
) -> None:
    """Acceptance (c): the lone concurrer is the synthesis author → BLOCK (independence)."""
    pdir = isolated_pending_dir / "processed"
    # Aiden authored the synthesis; aiden self-concurs in the inbox; nobody else has.
    _write_envelope(pdir, "aiden.json", "aiden", "[CONCUR:elliot] approving my own thing")
    allow, replacement = concur_gate.gate_check(
        "[CONCUR:atlas] release", "elliot", synthesis_author="aiden", processed_dir=pdir
    )
    assert allow is False
    assert replacement is not None
    assert "[CONCUR-REQUEST:ELLIOT]" in replacement
    # The replacement should declare that we have no valid concurrers.
    assert "Have: (none)" in replacement


def test_gate_check_d_blocks_even_when_CONCUR_GATE_SKIP_set(
    isolated_pending_dir, monkeypatch
) -> None:
    """Acceptance (d): CONCUR_GATE_SKIP=1 no longer opens the gate (env var removed)."""
    monkeypatch.setenv("CONCUR_GATE_SKIP", "1")
    pdir = isolated_pending_dir / "processed"  # empty — zero concurrers
    pdir.mkdir()
    allow, replacement = concur_gate.gate_check(
        "[CONCUR:atlas] release", "elliot", synthesis_author="elliot", processed_dir=pdir
    )
    assert allow is False
    assert replacement is not None
    assert "[CONCUR-REQUEST:ELLIOT]" in replacement


def test_gate_check_safe_default_requires_both_when_author_unknown(
    isolated_pending_dir,
) -> None:
    """synthesis_author=None → require BOTH deliberators (aiden AND max)."""
    pdir = isolated_pending_dir / "processed"
    # Only 1 of 2 deliberators concur — should BLOCK under safe default.
    _write_envelope(pdir, "aiden.json", "aiden", "[CONCUR:elliot]")
    allow, replacement = concur_gate.gate_check(
        "[CONCUR:atlas] release", "elliot", processed_dir=pdir
    )
    assert allow is False
    assert replacement is not None
    assert "all 2 deliberators" in replacement


def test_gate_check_safe_default_allows_when_both_deliberators_concur(
    isolated_pending_dir,
) -> None:
    """synthesis_author=None + both deliberators concur → ALLOW. Atlas (worker
    clone, not a deliberator post-2026-06-02) does not add to the count."""
    pdir = isolated_pending_dir / "processed"
    _write_envelope(pdir, "aiden.json", "aiden", "[CONCUR:elliot]")
    _write_envelope(pdir, "max.json", "max", "[CONCUR:elliot]")
    _write_envelope(pdir, "atlas.json", "atlas", "[CONCUR:elliot]")  # ignored — not a deliberator
    allow, _ = concur_gate.gate_check("[CONCUR:atlas] release", "elliot", processed_dir=pdir)
    assert allow is True


def test_gate_check_excludes_non_deliberator_concurrers(isolated_pending_dir) -> None:
    """A non-deliberator concur (e.g. nova, orion) does not count toward the threshold."""
    pdir = isolated_pending_dir / "processed"
    _write_envelope(pdir, "aiden.json", "aiden", "[CONCUR:elliot]")
    _write_envelope(pdir, "nova.json", "nova", "[CONCUR:elliot]")  # not a deliberator
    _write_envelope(pdir, "orion.json", "orion", "[CONCUR:elliot]")  # not a deliberator
    allow, _ = concur_gate.gate_check(
        "[CONCUR:atlas] release",
        "elliot",
        synthesis_author="elliot",
        processed_dir=pdir,
    )
    # Only 1 deliberator (aiden); nova + orion don't count → block.
    assert allow is False


def test_gate_check_replacement_lists_deliberators(isolated_pending_dir) -> None:
    """Replacement message names the eligible deliberator set."""
    pdir = isolated_pending_dir / "processed"
    pdir.mkdir()
    _, replacement = concur_gate.gate_check(
        "[CONCUR:atlas] release",
        "elliot",
        synthesis_author="elliot",
        processed_dir=pdir,
    )
    assert "Eligible deliberators:" in replacement
    for callsign in concur_gate.DELIBERATOR_CALLSIGNS:
        assert callsign in replacement


def test_gate_check_excludes_synthesis_author_case_insensitive(
    isolated_pending_dir,
) -> None:
    """synthesis_author='AIDEN' should still be excluded (case-insensitive)."""
    pdir = isolated_pending_dir / "processed"
    _write_envelope(pdir, "aiden.json", "aiden", "[CONCUR:elliot]")
    _write_envelope(pdir, "max.json", "max", "[CONCUR:elliot]")
    allow, _ = concur_gate.gate_check(
        "[CONCUR:atlas] release",
        "elliot",
        synthesis_author="AIDEN",  # uppercase author
        processed_dir=pdir,
    )
    # AIDEN excluded → only max remains → 1 of 2 needed → BLOCK.
    assert allow is False


# ─────────────────────────────────────────────────────────────────────────────
# No surviving env_skip / CONCUR_GATE_SKIP path
# ─────────────────────────────────────────────────────────────────────────────


def test_env_skip_removed_from_module() -> None:
    """v2 removes env_skip(); module must no longer export it."""
    assert not hasattr(concur_gate, "env_skip"), (
        "env_skip must be removed in v2 — no env-var bypass per Dave directive 2026-06-02"
    )


def test_has_peer_concur_removed_from_module() -> None:
    """v2 removes the Slack history scan; gate is inbox-source-only."""
    assert not hasattr(concur_gate, "has_peer_concur"), (
        "has_peer_concur (Slack history scan) is dead — #execution killed 2026-05-27"
    )


# ─────────────────────────────────────────────────────────────────────────────
# _topic_sha — deterministic short hash (unchanged from v1)
# ─────────────────────────────────────────────────────────────────────────────


def test_topic_sha_deterministic() -> None:
    assert concur_gate._topic_sha("hello") == concur_gate._topic_sha("hello")


def test_topic_sha_different_inputs_different_outputs() -> None:
    assert concur_gate._topic_sha("hello") != concur_gate._topic_sha("goodbye")


def test_topic_sha_length() -> None:
    assert len(concur_gate._topic_sha("anything")) == 12


# ─────────────────────────────────────────────────────────────────────────────
# Lookback config
# ─────────────────────────────────────────────────────────────────────────────


def test_lookback_default_is_sixty_minutes(monkeypatch) -> None:
    monkeypatch.delenv("CONCUR_LOOKBACK_MINUTES", raising=False)
    assert concur_gate._lookback_seconds() == 60.0 * 60.0


def test_lookback_env_override(monkeypatch) -> None:
    monkeypatch.setenv("CONCUR_LOOKBACK_MINUTES", "15")
    assert concur_gate._lookback_seconds() == 15.0 * 60.0


def test_lookback_invalid_env_falls_back_to_default(monkeypatch) -> None:
    monkeypatch.setenv("CONCUR_LOOKBACK_MINUTES", "not-a-number")
    assert concur_gate._lookback_seconds() == 60.0 * 60.0


# ─────────────────────────────────────────────────────────────────────────────
# Integration smoke — real now() + real mtime
# ─────────────────────────────────────────────────────────────────────────────


def test_real_now_and_mtime_pick_up_just_written_files(isolated_pending_dir) -> None:
    """No now= injection — gate uses time.time() and fs mtime as written."""
    pdir = isolated_pending_dir / "processed"
    _write_envelope(pdir, "a.json", "aiden", "[CONCUR:elliot]")
    _write_envelope(pdir, "m.json", "max", "[CONCUR:elliot]")
    # No now=, no mtime override — relies on time.time() and current mtime.
    allow, _ = concur_gate.gate_check(
        "[CONCUR:atlas] release",
        "elliot",
        synthesis_author="elliot",
        processed_dir=pdir,
    )
    assert allow is True
    # Sanity: mtime is recent.
    for path in pdir.glob("*.json"):
        assert path.stat().st_mtime > time.time() - 5
