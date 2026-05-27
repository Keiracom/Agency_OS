"""Tests for scripts/dispatcher/_inbox_loop.py.

Covers atomic-claim race-safety + decode failure handling + missing-dir +
sorted iteration order.

bd: Agency_OS-8416
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from scripts.dispatcher._inbox_loop import (
    _decode_envelope,
    _scan_inbox,
    _try_claim,
    iter_claimed_envelopes,
)


class _FakeClock:
    """Records sleep() calls; never actually sleeps."""

    def __init__(self) -> None:
        self.sleeps: list[float] = []

    def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)


def test_scan_inbox_returns_sorted_json_files(tmp_path: Path):
    (tmp_path / "b.json").write_text("{}")
    (tmp_path / "a.json").write_text("{}")
    (tmp_path / "c.txt").write_text("not json — should be skipped")
    out = _scan_inbox(tmp_path)
    assert [p.name for p in out] == ["a.json", "b.json"]


def test_scan_inbox_missing_dir_returns_empty(tmp_path: Path):
    assert _scan_inbox(tmp_path / "does-not-exist") == []


def test_try_claim_atomic_rename_succeeds(tmp_path: Path):
    src = tmp_path / "in.json"
    src.write_text("{}")
    processing = tmp_path / "processing"
    processing.mkdir()
    claimed = _try_claim(src, processing)
    assert claimed is not None
    assert claimed == processing / "in.json"
    assert claimed.exists()
    assert not src.exists()


def test_try_claim_race_loss_returns_none(tmp_path: Path):
    """If the file is already gone (another consumer won the race), return None."""
    src = tmp_path / "ghost.json"  # not created
    processing = tmp_path / "processing"
    processing.mkdir()
    assert _try_claim(src, processing) is None


def test_decode_envelope_returns_dict_on_valid_json(tmp_path: Path):
    fp = tmp_path / "x.json"
    fp.write_text('{"type":"task_dispatch","id":"x"}')
    out = _decode_envelope(fp)
    assert out == {"type": "task_dispatch", "id": "x"}


def test_decode_envelope_returns_none_on_garbage(tmp_path: Path):
    fp = tmp_path / "garbage.json"
    fp.write_text("this is not json")
    assert _decode_envelope(fp) is None


def test_iter_claimed_envelopes_yields_in_sorted_order(tmp_path: Path):
    inbox = tmp_path / "inbox"
    inbox.mkdir()
    (inbox / "task_b.json").write_text('{"type":"task_dispatch","id":"b"}')
    (inbox / "task_a.json").write_text('{"type":"task_dispatch","id":"a"}')
    processing = tmp_path / "processing"
    clock = _FakeClock()
    yielded: list[tuple[Path, dict[str, Any]]] = list(
        iter_claimed_envelopes(
            inbox,
            processing_dir=processing,
            poll_seconds=0.01,
            stop_after=1,
            clock=clock,
        )
    )
    assert [p.name for (p, _) in yielded] == ["task_a.json", "task_b.json"]
    assert [env["id"] for (_, env) in yielded] == ["a", "b"]
    # All claimed files should now live under processing/.
    assert (processing / "task_a.json").exists()
    assert (processing / "task_b.json").exists()
    # inbox dir should be empty of the original files.
    assert sorted(p.name for p in inbox.glob("*.json")) == []


def test_iter_claimed_envelopes_skips_garbage_json(tmp_path: Path):
    inbox = tmp_path / "inbox"
    inbox.mkdir()
    (inbox / "good.json").write_text('{"type":"task_dispatch","id":"g"}')
    (inbox / "bad.json").write_text("not json")
    processing = tmp_path / "processing"
    clock = _FakeClock()
    yielded = list(
        iter_claimed_envelopes(
            inbox,
            processing_dir=processing,
            poll_seconds=0.01,
            stop_after=1,
            clock=clock,
        )
    )
    # Only the good envelope is yielded — bad is claimed but not yielded.
    assert [env["id"] for (_, env) in yielded] == ["g"]
    # Both files are now in processing/ (atomic-claim ran on both).
    assert (processing / "good.json").exists()
    assert (processing / "bad.json").exists()


def test_iter_claimed_envelopes_respects_stop_after_bound(tmp_path: Path):
    """stop_after=2 → exactly 2 iterations of the outer poll loop."""
    inbox = tmp_path / "inbox"
    inbox.mkdir()
    processing = tmp_path / "processing"
    clock = _FakeClock()
    list(
        iter_claimed_envelopes(
            inbox,
            processing_dir=processing,
            poll_seconds=0.5,
            stop_after=2,
            clock=clock,
        )
    )
    # One sleep between iter 1 → iter 2; no sleep after iter 2 (we exit).
    assert clock.sleeps == [0.5]
