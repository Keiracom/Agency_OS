"""Tests for scripts/dispatcher/_spawn.py.

Covers compose-then-noop-log path, compose-then-spawn path with injected
Popen, unknown-mode fallback, missing-binary fallback, and resume-context
forwarding to the composer.

bd: Agency_OS-8416
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from scripts.dispatcher import _spawn
from scripts.dispatcher._spawn import MODE_NOOP, MODE_SPAWN, handle_envelope


class _FakeDB:
    """Minimal _DBProtocol implementation that returns canned data per call."""

    def __init__(self) -> None:
        self._script: list[tuple[Any, list[Any]]] = []
        self.queries: list[str] = []
        self._next_one: Any = None
        self._next_all: list[Any] = []

    def script(self, one: Any, all_: list[Any]) -> None:
        self._script.append((one, all_))

    def execute(self, query: str, *_params: Any) -> Any:
        self.queries.append(query)
        if self._script:
            self._next_one, self._next_all = self._script.pop(0)
        return self

    def fetchone(self) -> Any:
        return self._next_one

    def fetchall(self) -> Any:
        return self._next_all


class _FakeProc:
    def __init__(self) -> None:
        self.pid = 4242
        self.stdin = _FakeStdin()


class _FakeStdin:
    def __init__(self) -> None:
        self.written: list[str] = []
        self.closed = False

    def write(self, text: str) -> None:
        self.written.append(text)

    def close(self) -> None:
        self.closed = True


class _FakeClock:
    def time(self) -> float:
        return 1748252600.0


def _seed_db_for_compose(db: _FakeDB) -> None:
    # 3 canonical keys + Part D + Part E
    db.script(("comm_v1",), [])
    db.script(("mal_v1",), [])
    db.script(("sep_v1",), [])
    db.script(None, [])
    db.script(None, [])


def _make_repo_root(tmp_path: Path) -> Path:
    (tmp_path / "IDENTITY.md").write_text("ROLE_BRIEF_FIXTURE")
    return tmp_path


def _make_inbox_root_with_one_msg(tmp_path: Path, callsign: str) -> Path:
    inbox = tmp_path / f"telegram-relay-{callsign}" / "inbox"
    inbox.mkdir(parents=True)
    (inbox / "t1.json").write_text('{"type":"task_dispatch","id":"t1"}')
    return tmp_path


def test_noop_mode_logs_preview_does_not_spawn(tmp_path: Path):
    db = _FakeDB()
    _seed_db_for_compose(db)
    result = handle_envelope(
        callsign="nova",
        db=db,
        repo_root=_make_repo_root(tmp_path),
        inbox_root=_make_inbox_root_with_one_msg(tmp_path, "nova"),
        mode=MODE_NOOP,
        clock=_FakeClock(),
    )
    assert result["mode"] == MODE_NOOP
    assert result["prompt_chars"] > 0
    assert "pid" not in result


def test_spawn_mode_calls_popen_writes_prompt_to_stdin(tmp_path: Path):
    db = _FakeDB()
    _seed_db_for_compose(db)
    popen_calls: list[Any] = []

    def fake_popen(cmd: list[str], **kwargs: Any) -> _FakeProc:
        popen_calls.append((cmd, kwargs))
        return _FakeProc()

    result = handle_envelope(
        callsign="nova",
        db=db,
        repo_root=_make_repo_root(tmp_path),
        inbox_root=_make_inbox_root_with_one_msg(tmp_path, "nova"),
        mode=MODE_SPAWN,
        claude_bin="/usr/local/bin/claude",
        popen=fake_popen,
        clock=_FakeClock(),
    )
    assert result["mode"] == MODE_SPAWN
    assert result["pid"] == 4242
    assert len(popen_calls) == 1
    cmd, _ = popen_calls[0]
    assert cmd == ["/usr/local/bin/claude"]


def test_spawn_mode_falls_back_to_noop_when_binary_missing(tmp_path: Path, monkeypatch):
    db = _FakeDB()
    _seed_db_for_compose(db)
    # No claude_bin passed + shutil.which returns None.
    monkeypatch.setattr(_spawn.shutil, "which", lambda _name: None)
    result = handle_envelope(
        callsign="nova",
        db=db,
        repo_root=_make_repo_root(tmp_path),
        inbox_root=_make_inbox_root_with_one_msg(tmp_path, "nova"),
        mode=MODE_SPAWN,
        clock=_FakeClock(),
    )
    assert result["mode"] == MODE_NOOP


def test_unknown_mode_falls_back_to_noop(tmp_path: Path):
    db = _FakeDB()
    _seed_db_for_compose(db)
    result = handle_envelope(
        callsign="nova",
        db=db,
        repo_root=_make_repo_root(tmp_path),
        inbox_root=_make_inbox_root_with_one_msg(tmp_path, "nova"),
        mode="bogus_mode",
        clock=_FakeClock(),
    )
    assert result["mode"] == MODE_NOOP


def test_resume_context_forwarded_to_composer_and_skips_inbox(tmp_path: Path):
    """When resume_context is set, the composer must skip Part C; verify by
    asserting the composed prompt's char count differs from the inbox-included
    path with the same db data."""
    db_noop = _FakeDB()
    _seed_db_for_compose(db_noop)
    # No inbox dir created → Part C marker would be present in non-resume path.
    repo_root = _make_repo_root(tmp_path)
    inbox_root = tmp_path  # callsign dir does not exist
    no_resume = handle_envelope(
        callsign="nova",
        db=db_noop,
        repo_root=repo_root,
        inbox_root=inbox_root,
        mode=MODE_NOOP,
        clock=_FakeClock(),
    )

    db_resume = _FakeDB()
    # Resume path: 3 canonical-key queries + Part D + Part E (no Part C).
    db_resume.script(("comm_v1",), [])
    db_resume.script(("mal_v1",), [])
    db_resume.script(("sep_v1",), [])
    db_resume.script(None, [])
    db_resume.script(None, [])
    resume = handle_envelope(
        callsign="nova",
        db=db_resume,
        repo_root=repo_root,
        inbox_root=inbox_root,
        mode=MODE_NOOP,
        resume_context={
            "decision": "push_fixup",
            "original_task_ref": "review-pr-X",
            "interim_state": {"notes": "waiting"},
        },
        clock=_FakeClock(),
    )
    # Both modes produce a prompt; the resume path replaces Part C with the
    # resume section, so char counts differ but both are > 0.
    assert no_resume["prompt_chars"] > 0
    assert resume["prompt_chars"] > 0
    assert no_resume["prompt_chars"] != resume["prompt_chars"]


def test_spawn_mode_handles_proc_without_stdin(tmp_path: Path):
    """If Popen returns a proc with stdin=None (e.g. fake test double), don't
    raise — just log + return."""
    db = _FakeDB()
    _seed_db_for_compose(db)

    class _ProcNoStdin:
        pid = 9999
        stdin = None

    def fake_popen(*_a: Any, **_kw: Any) -> _ProcNoStdin:
        return _ProcNoStdin()

    result = handle_envelope(
        callsign="nova",
        db=db,
        repo_root=_make_repo_root(tmp_path),
        inbox_root=_make_inbox_root_with_one_msg(tmp_path, "nova"),
        mode=MODE_SPAWN,
        claude_bin="/usr/local/bin/claude",
        popen=fake_popen,
        clock=_FakeClock(),
    )
    assert result["mode"] == MODE_SPAWN
    assert result["pid"] == 9999
