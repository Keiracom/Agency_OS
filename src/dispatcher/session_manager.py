"""KEI-184 — SessionManager: unified dispatcher interface for tmux + container backends.

Routes ``spawn`` / ``wait_ready`` / ``send`` / ``terminate`` to either
``tmux_lifecycle`` or ``container_lifecycle`` based on the configured
``Backend``.  This is the abstraction layer for the Strangler Fig router
(KEI-185); it is intentionally wire-free — no callers are touched here.

Design notes:
- Backend is chosen at construction time; one ``SessionManager`` instance
  maps to one backend for the lifetime of a spawned session.
- No ``SessionManager``-level exception class is added.  Callers handle
  the backend-native exception types (``SessionStartupError`` /
  ``ContainerStartupError``) so the same try/except covers each backend
  uniformly.
- ``send()`` for the CONTAINER backend raises ``NotImplementedError``:
  containers expose an HTTP API, not a pane; LiteLLM router / dispatcher's
  HTTP-forward path owns request forwarding for that backend.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from src.dispatcher import container_lifecycle, tmux_lifecycle


class Backend(StrEnum):
    """Supported session backends."""

    TMUX = "tmux"
    CONTAINER = "container"


class SessionManager:
    """Routes spawn / wait_ready / send / terminate to the configured backend.

    Construction::

        sm = SessionManager(backend=Backend.TMUX)
        sm = SessionManager(backend=Backend.CONTAINER)

    The backend is fixed at construction time — a single ``SessionManager``
    instance is a stable choice for the lifetime of one spawned session.
    The dispatcher's Strangler Fig router (KEI-185) picks the backend per
    route and constructs accordingly.

    All four methods raise the backend-native exception type so callers
    handle once per backend and don't need a ``SessionManager``-level
    wrapper exception.
    """

    def __init__(self, backend: Backend) -> None:
        self._backend = backend

    @property
    def backend(self) -> Backend:
        """The backend this manager is configured for."""
        return self._backend

    # ------------------------------------------------------------------
    # spawn
    # ------------------------------------------------------------------

    def spawn(self, **kwargs: Any) -> Any:
        """Spawn a session on the configured backend.

        For ``TMUX``: forwards to ``tmux_lifecycle.spawn_session(**kwargs)``.
        Returns a ``SessionHandle``.

        For ``CONTAINER``: forwards to
        ``container_lifecycle.spawn_container(**kwargs)``.
        Returns a ``ContainerHandle``.

        Raises:
            tmux_lifecycle.TmuxUnavailableError:       TMUX, tmux missing.
            tmux_lifecycle.SessionStartupError:        TMUX, non-zero rc.
            container_lifecycle.DockerUnavailableError: CONTAINER, docker missing.
            container_lifecycle.ContainerStartupError:  CONTAINER, non-zero rc.
        """
        if self._backend is Backend.TMUX:
            return tmux_lifecycle.spawn_session(**kwargs)
        return container_lifecycle.spawn_container(**kwargs)

    # ------------------------------------------------------------------
    # wait_ready
    # ------------------------------------------------------------------

    def wait_ready(self, handle: Any, **kwargs: Any) -> bool:
        """Wait for the spawned session/container to become ready.

        For ``TMUX``: ``tmux_lifecycle.wait_ready(handle, **kwargs)``.
        For ``CONTAINER``: ``container_lifecycle.wait_healthy(handle, **kwargs)``.

        Note the intentional name asymmetry in the underlying modules
        (``wait_ready`` vs ``wait_healthy``); ``SessionManager`` normalises
        both behind a single ``wait_ready`` call so callers need not know
        which backend is active.

        Returns:
            ``True`` when ready/healthy.

        Raises:
            tmux_lifecycle.SessionStartupError:       TMUX timeout.
            container_lifecycle.ContainerStartupError: CONTAINER timeout.
        """
        if self._backend is Backend.TMUX:
            return tmux_lifecycle.wait_ready(handle, **kwargs)
        return container_lifecycle.wait_healthy(handle, **kwargs)

    # ------------------------------------------------------------------
    # send
    # ------------------------------------------------------------------

    def send(self, handle: Any, text: str) -> None:
        """Send free-form text to the session.

        For ``TMUX``: ``tmux_lifecycle.send(handle, text)`` — uses the
        two-call literal+Enter pattern from ``fleet_supervisor.py``.

        For ``CONTAINER``: raises ``NotImplementedError``.  Containers
        expose an HTTP API rather than a pane; the dispatcher's HTTP-forward
        path (LiteLLM router) owns request forwarding for this backend.
        Callers must route via the HTTP forward path instead of ``send``.

        Raises:
            NotImplementedError: when backend is ``CONTAINER``.
        """
        if self._backend is Backend.TMUX:
            tmux_lifecycle.send(handle, text)
            return
        raise NotImplementedError(
            "SessionManager.send() is not supported for the CONTAINER backend. "
            "Route requests via the dispatcher's HTTP forward path (LiteLLM router)."
        )

    # ------------------------------------------------------------------
    # terminate
    # ------------------------------------------------------------------

    def terminate(self, handle: Any) -> None:
        """Terminate the session/container.

        For ``TMUX``: ``tmux_lifecycle.terminate(handle)`` — best-effort,
        logs but does not raise on tmux errors.

        For ``CONTAINER``: ``container_lifecycle.kill_and_remove(handle)``
        — best-effort, logs but does not raise on docker errors.

        Note the intentional name asymmetry in the underlying modules
        (``terminate`` vs ``kill_and_remove``); ``SessionManager`` normalises
        both behind a single ``terminate`` call.
        """
        if self._backend is Backend.TMUX:
            tmux_lifecycle.terminate(handle)
            return
        container_lifecycle.kill_and_remove(handle)
