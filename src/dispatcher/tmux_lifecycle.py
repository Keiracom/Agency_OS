"""KEI-184 — tmux session spawn + startup polling + send/terminate.

Mirrors the ``container_lifecycle`` interface for tmux sessions so the
dispatcher's Strangler Fig router (KEI-185) can route uniformly to either
backend.  This module is spawn + wait_ready + send + terminate only; a
future lifecycle-monitor module (parallel to KEI-163/container_monitor)
handles long-running supervision.

Caller responsibility: the command passed to ``spawn_session`` must emit
``ready_marker`` to its pane when it is ready to accept input.  The
default ``"❯"`` matches Claude CLI's prompt character.
"""

from __future__ import annotations

import logging
import subprocess
import time
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants — mirror DEFAULT_* naming from container_lifecycle for symmetry.
# ---------------------------------------------------------------------------

DEFAULT_SESSION_STARTUP_TIMEOUT_S = 15.0
DEFAULT_SESSION_POLL_INTERVAL_S = 0.5
DEFAULT_TMUX_CMD_TIMEOUT_S = 10.0
TMUX_CLI = "tmux"

# The Claude CLI prompt character used for default ready detection.
_DEFAULT_READY_MARKER = "❯"


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class SessionStartupError(RuntimeError):
    """tmux session failed to start or become responsive within timeout.

    On the ``wait_ready`` timeout path the session has already been
    terminated before this is raised — caller does not need to clean up.
    """


class TmuxUnavailableError(RuntimeError):
    """The tmux CLI is not installed or not on PATH."""


# ---------------------------------------------------------------------------
# Handle
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SessionHandle:
    """Reference to a running tmux session.

    Returned by ``spawn_session``, consumed by ``wait_ready`` / ``send`` /
    ``terminate`` / future lifecycle ops.
    """

    session_name: str  # e.g. "orion:0" or just "orion"
    working_dir: str
    command: str  # e.g. "claude --resume"
    ready_marker: str = field(default=_DEFAULT_READY_MARKER)


# ---------------------------------------------------------------------------
# Internal helper
# ---------------------------------------------------------------------------


def _run_tmux(
    args: list[str],
    timeout_s: float = DEFAULT_TMUX_CMD_TIMEOUT_S,
) -> subprocess.CompletedProcess:
    """Run a tmux sub-command and return the CompletedProcess.

    Wraps FileNotFoundError in TmuxUnavailableError so callers only need
    to handle the domain exception.
    """
    try:
        # controlled args, no shell injection risk
        return subprocess.run(  # noqa: S603
            [TMUX_CLI, *args],
            capture_output=True,
            text=True,
            timeout=timeout_s,
            check=False,
        )
    except FileNotFoundError as exc:
        raise TmuxUnavailableError(f"{TMUX_CLI} CLI not found on PATH") from exc


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def spawn_session(
    *,
    session_name: str,
    working_dir: str,
    command: str,
    env: dict[str, str] | None = None,
    ready_marker: str = _DEFAULT_READY_MARKER,
) -> SessionHandle:
    """Start a detached tmux session running ``command``.

    Returns a ``SessionHandle``.  Does NOT block on readiness — call
    ``wait_ready(handle)`` next.

    Args:
        session_name: tmux session name (must be unique on this host).
        working_dir:  The ``-c`` start directory passed to tmux.
        command:      Shell command string run inside the session.
        env:          Optional extra environment variables injected via
                      ``-e KEY=VAL`` flags.
        ready_marker: Pane text that signals the session is ready (default
                      ``"❯"`` — Claude CLI prompt).

    Raises:
        TmuxUnavailableError: tmux CLI missing from PATH.
        SessionStartupError:  ``tmux new-session`` returned non-zero rc.
    """
    cmd: list[str] = [
        "new-session",
        "-d",
        "-s",
        session_name,
        "-c",
        working_dir,
    ]
    for k, v in (env or {}).items():
        cmd += ["-e", f"{k}={v}"]
    # command is the last positional arg
    cmd.append(command)

    out = _run_tmux(cmd)
    if out.returncode != 0:
        raise SessionStartupError(
            f"tmux new-session failed (rc={out.returncode}): {out.stderr.strip()[:300]}"
        )

    logger.info("tmux session %r started in %s", session_name, working_dir)
    return SessionHandle(
        session_name=session_name,
        working_dir=working_dir,
        command=command,
        ready_marker=ready_marker,
    )


def wait_ready(
    handle: SessionHandle,
    *,
    timeout_s: float = DEFAULT_SESSION_STARTUP_TIMEOUT_S,
    interval_s: float = DEFAULT_SESSION_POLL_INTERVAL_S,
) -> bool:
    """Poll the session's pane until ``ready_marker`` appears or timeout.

    On timeout: terminates the session via ``terminate(handle)``, then
    raises ``SessionStartupError``.  The session is gone before the
    exception surfaces — caller does not need to clean up.

    Returns:
        ``True`` when the marker is detected.

    Raises:
        SessionStartupError: marker not seen within ``timeout_s`` seconds.
    """
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        # controlled args, no shell injection risk
        result = subprocess.run(  # noqa: S603
            [TMUX_CLI, "capture-pane", "-t", handle.session_name, "-p"],
            capture_output=True,
            text=True,
            timeout=DEFAULT_TMUX_CMD_TIMEOUT_S,
            check=False,
        )
        if handle.ready_marker in result.stdout:
            logger.info(
                "session %r ready (marker %r found)",
                handle.session_name,
                handle.ready_marker,
            )
            return True
        time.sleep(interval_s)

    logger.warning(
        "session %r did not become ready within %.1fs — terminating",
        handle.session_name,
        timeout_s,
    )
    terminate(handle)
    raise SessionStartupError(
        f"session {handle.session_name!r} (cmd={handle.command!r}) "
        f"did not emit ready marker within {timeout_s:.1f}s"
    )


def send(handle: SessionHandle, text: str) -> None:
    """Send ``text`` to the session pane followed by Enter.

    Uses the two-call literal+Enter pattern from ``fleet_supervisor.py``
    to avoid the embedded-newline soft-break trap (a single
    ``["text", "Enter"]`` call is unreliable when text contains newlines
    because Claude CLI interprets embedded ``\\n`` as a soft-break and may
    eat the trailing Enter).
    """
    # First call: send text in literal mode (-l) so special chars are safe.
    # controlled args, no shell injection risk
    subprocess.run(  # noqa: S603
        [TMUX_CLI, "send-keys", "-t", handle.session_name, "-l", text],
        capture_output=True,
        text=True,
        timeout=DEFAULT_TMUX_CMD_TIMEOUT_S,
        check=True,
    )
    # Second call: send the Enter key separately.
    # controlled args, no shell injection risk
    subprocess.run(  # noqa: S603
        [TMUX_CLI, "send-keys", "-t", handle.session_name, "Enter"],
        capture_output=True,
        text=True,
        timeout=DEFAULT_TMUX_CMD_TIMEOUT_S,
        check=True,
    )


def terminate(handle: SessionHandle) -> None:
    """Best-effort ``tmux kill-session -t <name>``.

    Logs but does not raise on tmux errors — the abort path must not mask
    the original failure for callers using this from ``wait_ready``'s
    timeout branch.
    """
    try:
        # controlled args, no shell injection risk
        result = subprocess.run(  # noqa: S603
            [TMUX_CLI, "kill-session", "-t", handle.session_name],
            capture_output=True,
            text=True,
            timeout=DEFAULT_TMUX_CMD_TIMEOUT_S,
            check=False,
        )
        if result.returncode != 0:
            logger.warning(
                "tmux kill-session %r failed (rc=%d): %s",
                handle.session_name,
                result.returncode,
                result.stderr.strip()[:200],
            )
    except FileNotFoundError:
        logger.warning(
            "tmux CLI not found during terminate(%r) — session may linger",
            handle.session_name,
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("terminate(%r) raised unexpectedly: %s", handle.session_name, exc)
