"""Tests for scripts/dispatcher/dispatcher_main.py.

End-to-end smoke: main() with stop_after=1, real fs (tmp_path), injected
db_factory, in noop mode — processes 3 inbox files (one of each routable
type) and verifies the file lifecycle + routing decisions.

bd: Agency_OS-8416
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from scripts.dispatcher.dispatcher_main import main


class _FakeDB:
    """5-query script: 3 canonical keys + Part D + Part E (per spawn)."""

    def __init__(self) -> None:
        self._cursor = 0
        # Each compose call burns 5 queries; allow 3 compose calls.
        self._script: list[tuple[Any, list[Any]]] = []
        for _ in range(3):
            self._script.extend(
                [
                    (("comm_v1",), []),
                    (("mal_v1",), []),
                    (("sep_v1",), []),
                    (None, []),
                    (None, []),
                ]
            )
        self._next_one: Any = None
        self._next_all: list[Any] = []

    def execute(self, _query: str, *_params: Any) -> Any:
        if self._cursor < len(self._script):
            self._next_one, self._next_all = self._script[self._cursor]
            self._cursor += 1
        return self

    def fetchone(self) -> Any:
        return self._next_one

    def fetchall(self) -> Any:
        return self._next_all


def _seed_inbox(tmp_path: Path, callsign: str) -> Path:
    inbox = tmp_path / f"telegram-relay-{callsign}" / "inbox"
    inbox.mkdir(parents=True)
    (inbox / "01_task.json").write_text('{"type":"task_dispatch","id":"t1","brief":"do thing"}')
    (inbox / "02_decision.json").write_text(
        '{"type":"decision_response","id":"r1","decision":"push_fixup",'
        '"original_task_ref":"review-pr-X"}'
    )
    (inbox / "03_unknown.json").write_text('{"type":"alien_envelope","id":"u1"}')
    return inbox


def test_main_processes_three_envelopes_in_noop_mode(tmp_path: Path, monkeypatch):
    callsign = "nova"
    inbox_dir = _seed_inbox(tmp_path, callsign)
    (tmp_path / "IDENTITY.md").write_text("ROLE_BRIEF")
    monkeypatch.setenv("DISPATCHER_MODE", "noop")
    rc = main(
        argv=[
            "--callsign",
            callsign,
            "--inbox-root",
            str(tmp_path),
            "--repo-root",
            str(tmp_path),
            "--stop-after",
            "1",
            "--log-level",
            "WARNING",
        ],
        db_factory=lambda: _FakeDB(),
    )
    assert rc == 0
    # task + decision envelopes should be in processing/; unknown in quarantine/
    callsign_root = tmp_path / f"telegram-relay-{callsign}"
    assert (callsign_root / "processing" / "01_task.json").exists()
    assert (callsign_root / "processing" / "02_decision.json").exists()
    assert (callsign_root / "quarantine" / "03_unknown.json").exists()
    assert (callsign_root / "quarantine" / "03_unknown.json.reason").exists()
    # All 3 files should have left the inbox dir.
    assert sorted(p.name for p in inbox_dir.glob("*.json")) == []


def test_main_requires_callsign_arg():
    with pytest.raises(SystemExit):
        main(argv=[])


def test_main_with_empty_inbox_completes_cleanly(tmp_path: Path, monkeypatch):
    """No inbox dir at all → loop runs one iteration, no envelopes yielded, rc=0."""
    monkeypatch.setenv("DISPATCHER_MODE", "noop")
    rc = main(
        argv=[
            "--callsign",
            "nova",
            "--inbox-root",
            str(tmp_path),
            "--repo-root",
            str(tmp_path),
            "--stop-after",
            "1",
            "--log-level",
            "WARNING",
        ],
        db_factory=lambda: _FakeDB(),
    )
    assert rc == 0


def test_main_uses_dispatcher_poll_seconds_env(tmp_path: Path, monkeypatch):
    """Env var DISPATCHER_POLL_SECONDS must be readable; test exercises the
    float-parse path (we don't actually wait — stop_after=1 short-circuits)."""
    monkeypatch.setenv("DISPATCHER_POLL_SECONDS", "0.001")
    monkeypatch.setenv("DISPATCHER_MODE", "noop")
    (tmp_path / "IDENTITY.md").write_text("ROLE")
    rc = main(
        argv=[
            "--callsign",
            "nova",
            "--inbox-root",
            str(tmp_path),
            "--repo-root",
            str(tmp_path),
            "--stop-after",
            "1",
            "--log-level",
            "WARNING",
        ],
        db_factory=lambda: _FakeDB(),
    )
    assert rc == 0
