"""Tests for KEI-163 container_monitor module.

All docker interactions are mocked at the subprocess.run boundary so no live
docker daemon is required.
"""

from __future__ import annotations

import logging
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from src.dispatcher.container_lifecycle import ContainerHandle, DockerUnavailableError
from src.dispatcher.container_monitor import (
    DEFAULT_POLL_INTERVAL_S,
    MonitorResult,
    _inspect_state,
    monitor_container,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

HANDLE = ContainerHandle(
    id="abc123def456",
    name="test-container",
    image="test-image:latest",
    port=8080,
)

TASK_ID = "task-uuid-1234"


def _make_completed_proc(stdout: str, returncode: int = 0) -> MagicMock:
    proc = MagicMock()
    proc.stdout = stdout
    proc.stderr = ""
    proc.returncode = returncode
    return proc


# ---------------------------------------------------------------------------
# _inspect_state unit tests
# ---------------------------------------------------------------------------


class TestInspectState:
    def test_running_status_returns_running(self) -> None:
        proc = _make_completed_proc("running 0\n")
        with patch("subprocess.run", return_value=proc) as mock_run:
            status, code = _inspect_state(HANDLE)
        assert status == "running"
        assert code == 0
        mock_run.assert_called_once()

    def test_exited_137_parsed_correctly(self) -> None:
        proc = _make_completed_proc("exited 137\n")
        with patch("subprocess.run", return_value=proc):
            status, code = _inspect_state(HANDLE)
        assert status == "exited"
        assert code == 137

    def test_nonzero_rc_returns_unknown(self) -> None:
        proc = _make_completed_proc("", returncode=1)
        with patch("subprocess.run", return_value=proc):
            status, code = _inspect_state(HANDLE)
        assert status == "unknown"
        assert code is None

    def test_file_not_found_raises_docker_unavailable(self) -> None:
        with (
            patch("subprocess.run", side_effect=FileNotFoundError("docker not found")),
            pytest.raises(DockerUnavailableError),
        ):
            _inspect_state(HANDLE)

    def test_exited_zero_code(self) -> None:
        proc = _make_completed_proc("exited 0\n")
        with patch("subprocess.run", return_value=proc):
            status, code = _inspect_state(HANDLE)
        assert status == "exited"
        assert code == 0


# ---------------------------------------------------------------------------
# monitor_container integration tests
# ---------------------------------------------------------------------------


class TestMonitorContainer:
    def test_detect_exit_calls_reap_and_persist(self) -> None:
        """Monitor detects 'exited 0' on first poll, calls reap + persist."""
        inspect_proc = _make_completed_proc("exited 0\n")
        reap_fn = MagicMock()
        persist_fn = MagicMock()

        with patch("subprocess.run", return_value=inspect_proc):
            result = monitor_container(
                HANDLE,
                task_id=TASK_ID,
                poll_interval_s=0.01,
                reap_fn=reap_fn,
                persist_fn=persist_fn,
            )

        assert result.status == "exited"
        assert result.exit_code == 0
        assert isinstance(result.ended_at, datetime)
        reap_fn.assert_called_once_with(HANDLE)
        persist_fn.assert_called_once()

    def test_persist_called_with_task_id_and_result(self) -> None:
        """persist_fn receives (task_id, MonitorResult) with correct values."""
        inspect_proc = _make_completed_proc("exited 137\n")
        persist_fn = MagicMock()

        with patch("subprocess.run", return_value=inspect_proc):
            result = monitor_container(
                HANDLE,
                task_id=TASK_ID,
                poll_interval_s=0.01,
                reap_fn=MagicMock(),
                persist_fn=persist_fn,
            )

        persist_fn.assert_called_once_with(TASK_ID, result)
        assert result.exit_code == 137

    def test_monitor_loops_until_exit(self) -> None:
        """Monitor polls 'running' multiple times before detecting 'exited'."""
        running_proc = _make_completed_proc("running 0\n")
        exited_proc = _make_completed_proc("exited 0\n")
        side_effects = [running_proc, running_proc, exited_proc]

        reap_fn = MagicMock()
        persist_fn = MagicMock()

        with patch("subprocess.run", side_effect=side_effects):
            result = monitor_container(
                HANDLE,
                task_id=TASK_ID,
                poll_interval_s=0.01,
                reap_fn=reap_fn,
                persist_fn=persist_fn,
            )

        assert result.status == "exited"
        reap_fn.assert_called_once_with(HANDLE)

    def test_timeout_returns_timeout_status(self) -> None:
        """overall_timeout_s exceeded → status='timeout', reap not called."""
        running_proc = _make_completed_proc("running 0\n")
        persist_fn = MagicMock()
        reap_fn = MagicMock()

        with patch("subprocess.run", return_value=running_proc):
            result = monitor_container(
                HANDLE,
                task_id=TASK_ID,
                poll_interval_s=0.01,
                overall_timeout_s=0.05,
                reap_fn=reap_fn,
                persist_fn=persist_fn,
            )

        assert result.status == "timeout"
        assert result.exit_code is None
        assert result.ended_at is None
        persist_fn.assert_called_once_with(TASK_ID, result)
        reap_fn.assert_not_called()

    def test_persist_error_logged_not_raised(self, caplog: pytest.LogCaptureFixture) -> None:
        """persist_fn raising does not propagate — caller still gets MonitorResult."""
        inspect_proc = _make_completed_proc("exited 1\n")

        def bad_persist(task_id: str, result: MonitorResult) -> None:
            raise RuntimeError("DB down")

        with (
            caplog.at_level(logging.ERROR, logger="src.dispatcher.container_monitor"),
            patch("subprocess.run", return_value=inspect_proc),
        ):
            result = monitor_container(
                HANDLE,
                task_id=TASK_ID,
                poll_interval_s=0.01,
                reap_fn=MagicMock(),
                persist_fn=bad_persist,
            )

        assert result.status == "exited"
        assert any("persist_fn raised" in r.message for r in caplog.records)

    def test_unknown_inspect_status_not_treated_as_exit(self) -> None:
        """'unknown' status (non-zero rc) keeps looping, doesn't trigger reap."""
        unknown_proc = _make_completed_proc("", returncode=1)
        exited_proc = _make_completed_proc("exited 0\n")
        side_effects = [unknown_proc, exited_proc]

        reap_fn = MagicMock()
        persist_fn = MagicMock()

        with patch("subprocess.run", side_effect=side_effects):
            result = monitor_container(
                HANDLE,
                task_id=TASK_ID,
                poll_interval_s=0.01,
                reap_fn=reap_fn,
                persist_fn=persist_fn,
            )

        assert result.status == "exited"
        reap_fn.assert_called_once()

    def test_docker_unavailable_propagates(self) -> None:
        """DockerUnavailableError from _inspect_state propagates to caller."""
        with (
            patch("subprocess.run", side_effect=FileNotFoundError("no docker")),
            pytest.raises(DockerUnavailableError),
        ):
            monitor_container(
                HANDLE,
                task_id=TASK_ID,
                poll_interval_s=0.01,
                reap_fn=MagicMock(),
                persist_fn=MagicMock(),
            )

    def test_poll_interval_over_5s_raises(self) -> None:
        """poll_interval_s > 5.0 violates acceptance budget → ValueError."""
        with pytest.raises(ValueError, match="5s acceptance budget"):
            monitor_container(
                HANDLE,
                task_id=TASK_ID,
                poll_interval_s=5.1,
                reap_fn=MagicMock(),
                persist_fn=MagicMock(),
            )

    def test_default_poll_interval_within_budget(self) -> None:
        """DEFAULT_POLL_INTERVAL_S satisfies the ≤5s acceptance budget."""
        assert DEFAULT_POLL_INTERVAL_S <= 5.0

    def test_reap_fn_called_with_handle_on_exit(self) -> None:
        """reap_fn receives the exact ContainerHandle that was passed in."""
        inspect_proc = _make_completed_proc("exited 0\n")
        reap_fn = MagicMock()

        with patch("subprocess.run", return_value=inspect_proc):
            monitor_container(
                HANDLE,
                task_id=TASK_ID,
                poll_interval_s=0.01,
                reap_fn=reap_fn,
                persist_fn=MagicMock(),
            )

        reap_fn.assert_called_once_with(HANDLE)
