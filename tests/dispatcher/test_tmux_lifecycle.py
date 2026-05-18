"""Tests for src/dispatcher/tmux_lifecycle.py (KEI-184)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from src.dispatcher.tmux_lifecycle import (
    TMUX_CLI,
    SessionHandle,
    SessionStartupError,
    TmuxUnavailableError,
    send,
    spawn_session,
    terminate,
    wait_ready,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_GOOD_RC = MagicMock(returncode=0, stdout="", stderr="")
_BAD_RC = MagicMock(returncode=1, stdout="", stderr="tmux: session already exists")


def _make_handle(**kwargs) -> SessionHandle:
    # S5443: use a fake non-publicly-writable path; tests mock subprocess so the
    # path is never actually accessed. Avoids the /tmp publicly-writable flag.
    defaults = {
        "session_name": "test-session",
        "working_dir": "/test/wd",
        "command": "claude --resume",
        "ready_marker": "❯",
    }
    defaults.update(kwargs)
    return SessionHandle(**defaults)


# ---------------------------------------------------------------------------
# spawn_session
# ---------------------------------------------------------------------------


class TestSpawnSession:
    def test_spawn_calls_tmux_new_session_with_correct_args(self):
        with patch("subprocess.run", return_value=_GOOD_RC) as mock_run:
            spawn_session(
                session_name="orion",
                working_dir="/home/elliotbot",
                command="claude --resume",
            )
        args_list = mock_run.call_args[0][0]
        assert args_list[0] == TMUX_CLI
        assert "new-session" in args_list
        assert "-d" in args_list
        assert "-s" in args_list
        idx_s = args_list.index("-s")
        assert args_list[idx_s + 1] == "orion"
        assert "-c" in args_list
        idx_c = args_list.index("-c")
        assert args_list[idx_c + 1] == "/home/elliotbot"
        assert args_list[-1] == "claude --resume"

    def test_spawn_includes_env_flags(self, tmp_path):
        with patch("subprocess.run", return_value=_GOOD_RC) as mock_run:
            spawn_session(
                session_name="orion",
                working_dir=str(tmp_path),
                command="bash",
                env={"FOO": "bar", "BAZ": "qux"},
            )
        args_list = mock_run.call_args[0][0]
        # Both env vars should appear as -e KEY=VAL pairs
        flat = " ".join(args_list)
        assert "-e FOO=bar" in flat or ("-e" in args_list and "FOO=bar" in args_list)
        assert "-e BAZ=qux" in flat or ("-e" in args_list and "BAZ=qux" in args_list)

    def test_spawn_returns_handle_with_provided_fields(self):
        with patch("subprocess.run", return_value=_GOOD_RC):
            handle = spawn_session(
                session_name="my-session",
                working_dir="/workspace",
                command="python main.py",
                ready_marker=">>",
            )
        assert handle.session_name == "my-session"
        assert handle.working_dir == "/workspace"
        assert handle.command == "python main.py"
        assert handle.ready_marker == ">>"

    def test_spawn_raises_tmux_unavailable_error_when_tmux_missing(self, tmp_path):
        with (
            patch("subprocess.run", side_effect=FileNotFoundError("tmux not found")),
            pytest.raises(TmuxUnavailableError, match="not found on PATH"),
        ):
            spawn_session(
                session_name="orion",
                working_dir=str(tmp_path),
                command="bash",
            )

    def test_spawn_raises_session_startup_error_on_nonzero_rc(self, tmp_path):
        with (
            patch("subprocess.run", return_value=_BAD_RC),
            pytest.raises(SessionStartupError, match="rc=1"),
        ):
            spawn_session(
                session_name="orion",
                working_dir=str(tmp_path),
                command="bash",
            )


# ---------------------------------------------------------------------------
# wait_ready
# ---------------------------------------------------------------------------


class TestWaitReady:
    def _capture_result(self, pane_text: str) -> MagicMock:
        return MagicMock(returncode=0, stdout=pane_text, stderr="")

    def test_wait_ready_returns_true_when_marker_appears(self):
        handle = _make_handle()
        capture = self._capture_result("some output ❯ ")
        with patch("subprocess.run", return_value=capture):
            result = wait_ready(handle, timeout_s=5.0, interval_s=0.01)
        assert result is True

    def test_wait_ready_polls_until_marker(self):
        handle = _make_handle()
        empty = self._capture_result("")
        found = self._capture_result("❯")
        # First two calls return empty, third has marker
        with (
            patch("subprocess.run", side_effect=[empty, empty, found]),
            patch("time.sleep"),  # avoid real sleep in tests
        ):
            result = wait_ready(handle, timeout_s=5.0, interval_s=0.01)
        assert result is True

    def test_wait_ready_terminates_and_raises_on_timeout(self):
        handle = _make_handle()
        empty = self._capture_result("")
        # Patch time.monotonic to simulate immediate timeout after first poll
        times = iter([0.0, 0.0, 999.0])  # start, loop check, deadline exceeded
        terminate_calls = []

        def fake_terminate(h):
            terminate_calls.append(h)

        with (
            patch("subprocess.run", return_value=empty),
            patch("time.monotonic", side_effect=times),
            patch("time.sleep"),
            patch("src.dispatcher.tmux_lifecycle.terminate", side_effect=fake_terminate),
            pytest.raises(SessionStartupError, match="did not emit ready marker"),
        ):
            wait_ready(handle, timeout_s=0.001, interval_s=0.001)

        assert len(terminate_calls) == 1
        assert terminate_calls[0].session_name == handle.session_name


# ---------------------------------------------------------------------------
# send
# ---------------------------------------------------------------------------


class TestSend:
    def test_send_uses_two_call_literal_then_enter_pattern(self):
        handle = _make_handle()
        with patch("subprocess.run", return_value=_GOOD_RC) as mock_run:
            send(handle, "hello world")

        assert mock_run.call_count == 2
        first_call_args = mock_run.call_args_list[0][0][0]
        second_call_args = mock_run.call_args_list[1][0][0]

        # First call: literal mode with -l flag and the text
        assert "-l" in first_call_args
        assert "hello world" in first_call_args
        assert "send-keys" in first_call_args

        # Second call: Enter key (no -l flag)
        assert "Enter" in second_call_args
        assert "send-keys" in second_call_args
        assert "-l" not in second_call_args


# ---------------------------------------------------------------------------
# terminate
# ---------------------------------------------------------------------------


class TestTerminate:
    def test_terminate_invokes_kill_session_best_effort(self):
        handle = _make_handle()
        bad = MagicMock(returncode=1, stdout="", stderr="no session")
        with patch("subprocess.run", return_value=bad) as mock_run:
            # Should NOT raise even on non-zero rc
            terminate(handle)
        args_list = mock_run.call_args[0][0]
        assert "kill-session" in args_list
        assert handle.session_name in args_list

    def test_terminate_swallows_file_not_found_error(self):
        handle = _make_handle()
        with patch("subprocess.run", side_effect=FileNotFoundError("tmux missing")):
            # Must not raise — tmux missing during teardown is tolerated
            terminate(handle)

    def test_terminate_calls_correct_session_name(self):
        handle = _make_handle(session_name="my-unique-session")
        with patch("subprocess.run", return_value=_GOOD_RC) as mock_run:
            terminate(handle)
        args_list = mock_run.call_args[0][0]
        assert "my-unique-session" in args_list
