"""Tests for src/dispatcher/session_manager.py (KEI-184)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from src.dispatcher.session_manager import Backend, SessionManager

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _tmux_sm() -> SessionManager:
    return SessionManager(backend=Backend.TMUX)


def _container_sm() -> SessionManager:
    return SessionManager(backend=Backend.CONTAINER)


_FAKE_TMUX_HANDLE = MagicMock(name="SessionHandle")
_FAKE_CONTAINER_HANDLE = MagicMock(name="ContainerHandle")


# ---------------------------------------------------------------------------
# backend property
# ---------------------------------------------------------------------------


class TestBackendProperty:
    def test_backend_property_returns_configured_backend_tmux(self):
        sm = SessionManager(backend=Backend.TMUX)
        assert sm.backend is Backend.TMUX

    def test_backend_property_returns_configured_backend_container(self):
        sm = SessionManager(backend=Backend.CONTAINER)
        assert sm.backend is Backend.CONTAINER


# ---------------------------------------------------------------------------
# spawn
# ---------------------------------------------------------------------------


class TestSpawn:
    def test_backend_tmux_spawn_routes_to_tmux_lifecycle(self, tmp_path):
        sm = _tmux_sm()
        wd = str(tmp_path)
        with patch(
            "src.dispatcher.session_manager.tmux_lifecycle.spawn_session",
            return_value=_FAKE_TMUX_HANDLE,
        ) as mock_spawn:
            result = sm.spawn(
                session_name="orion",
                working_dir=wd,
                command="claude --resume",
            )
        mock_spawn.assert_called_once_with(
            session_name="orion",
            working_dir=wd,
            command="claude --resume",
        )
        assert result is _FAKE_TMUX_HANDLE

    def test_backend_container_spawn_routes_to_container_lifecycle(self):
        sm = _container_sm()
        with patch(
            "src.dispatcher.session_manager.container_lifecycle.spawn_container",
            return_value=_FAKE_CONTAINER_HANDLE,
        ) as mock_spawn:
            result = sm.spawn(image="myimg", name="mycontainer", port=8080)
        mock_spawn.assert_called_once_with(image="myimg", name="mycontainer", port=8080)
        assert result is _FAKE_CONTAINER_HANDLE


# ---------------------------------------------------------------------------
# wait_ready
# ---------------------------------------------------------------------------


class TestWaitReady:
    def test_backend_tmux_wait_ready_routes_correctly(self):
        sm = _tmux_sm()
        with patch(
            "src.dispatcher.session_manager.tmux_lifecycle.wait_ready",
            return_value=True,
        ) as mock_wait:
            result = sm.wait_ready(_FAKE_TMUX_HANDLE, timeout_s=5.0)
        mock_wait.assert_called_once_with(_FAKE_TMUX_HANDLE, timeout_s=5.0)
        assert result is True

    def test_backend_container_wait_ready_routes_to_wait_healthy(self):
        """The CONTAINER backend normalises wait_ready → container_lifecycle.wait_healthy."""
        sm = _container_sm()
        with patch(
            "src.dispatcher.session_manager.container_lifecycle.wait_healthy",
            return_value=True,
        ) as mock_healthy:
            result = sm.wait_ready(_FAKE_CONTAINER_HANDLE, timeout_s=30.0)
        mock_healthy.assert_called_once_with(_FAKE_CONTAINER_HANDLE, timeout_s=30.0)
        assert result is True


# ---------------------------------------------------------------------------
# send
# ---------------------------------------------------------------------------


class TestSend:
    def test_backend_tmux_send_routes_correctly(self):
        sm = _tmux_sm()
        with patch(
            "src.dispatcher.session_manager.tmux_lifecycle.send",
        ) as mock_send:
            sm.send(_FAKE_TMUX_HANDLE, "hello")
        mock_send.assert_called_once_with(_FAKE_TMUX_HANDLE, "hello")

    def test_backend_container_send_raises_not_implemented_error(self):
        sm = _container_sm()
        with pytest.raises(NotImplementedError, match="HTTP forward path"):
            sm.send(_FAKE_CONTAINER_HANDLE, "hello")


# ---------------------------------------------------------------------------
# terminate
# ---------------------------------------------------------------------------


class TestTerminate:
    def test_backend_tmux_terminate_routes_correctly(self):
        sm = _tmux_sm()
        with patch(
            "src.dispatcher.session_manager.tmux_lifecycle.terminate",
        ) as mock_terminate:
            sm.terminate(_FAKE_TMUX_HANDLE)
        mock_terminate.assert_called_once_with(_FAKE_TMUX_HANDLE)

    def test_backend_container_terminate_routes_to_kill_and_remove(self):
        """terminate() normalises to container_lifecycle.kill_and_remove — name mismatch is intentional."""
        sm = _container_sm()
        with patch(
            "src.dispatcher.session_manager.container_lifecycle.kill_and_remove",
        ) as mock_kill:
            sm.terminate(_FAKE_CONTAINER_HANDLE)
        mock_kill.assert_called_once_with(_FAKE_CONTAINER_HANDLE)
