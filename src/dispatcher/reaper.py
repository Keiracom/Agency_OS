"""KEI-211 — Dispatcher Reaper: zombie session detection + cleanup.

Pairs with :mod:`src.dispatcher.watchdog`. The watchdog catches sessions
that are *running but unresponsive*; the reaper catches sessions that
were never properly torn down: tmux sessions / containers that the
dispatcher's registry no longer knows about, or registered handles past
their TTL.

Scope safety — DO NOT misuse:
This module enumerates **live tmux sessions and containers on the host**
and kills anything not in the dispatcher's registry. To avoid reaping
unrelated dev sessions, callers MUST supply a name prefix scope
(``tmux_name_prefix`` / ``container_name_prefix``). Empty prefixes are
rejected at construction time — there is no "reap all" mode.
"""

from __future__ import annotations

import logging
import subprocess
import time
from dataclasses import dataclass

from src.dispatcher.container_lifecycle import (
    DEFAULT_DOCKER_TEARDOWN_TIMEOUT_S,
    DOCKER_CLI,
    ContainerHandle,
    DockerUnavailableError,
    kill_and_remove,
)
from src.dispatcher.tmux_lifecycle import (
    DEFAULT_TMUX_CMD_TIMEOUT_S,
    TMUX_CLI,
    SessionHandle,
    TmuxUnavailableError,
    terminate,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ReapEvent:
    kind: str  # "tmux" | "container"
    name_or_id: str
    reason: str  # "orphan" | "ttl_exceeded"
    success: bool


@dataclass(frozen=True)
class ReapResult:
    scanned_tmux: int
    scanned_containers: int
    reaped: tuple[ReapEvent, ...]

    @property
    def total_reaped(self) -> int:
        return len(self.reaped)


def _list_tmux_sessions() -> list[str] | None:
    """Return live tmux session names, or None when tmux unreachable.

    None is a soft signal: caller MUST NOT treat "no tmux" as "no zombies"
    and proceed to reap; it means "skip the tmux pass this cycle".
    """
    try:
        result = subprocess.run(  # noqa: S603  # controlled args
            [TMUX_CLI, "list-sessions", "-F", "#{session_name}"],
            capture_output=True,
            text=True,
            timeout=DEFAULT_TMUX_CMD_TIMEOUT_S,
            check=False,
        )
    except FileNotFoundError as exc:
        raise TmuxUnavailableError(f"{TMUX_CLI} CLI not found on PATH") from exc
    except subprocess.TimeoutExpired:
        logger.warning("KEI-211 reaper: tmux list-sessions timed out — skipping pass")
        return None
    # tmux returns rc=1 when there are no sessions; that's "empty", not error.
    if result.returncode != 0 and "no server running" not in result.stderr.lower():
        logger.warning(
            "KEI-211 reaper: tmux list-sessions rc=%d stderr=%s",
            result.returncode,
            result.stderr.strip()[:200],
        )
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def _list_containers_by_prefix(prefix: str) -> list[tuple[str, str]] | None:
    """Return [(id, name), ...] for containers whose name starts with prefix.

    None means docker is unreachable for this cycle (skip the container pass).
    """
    try:
        result = subprocess.run(  # noqa: S603  # controlled args
            [
                DOCKER_CLI,
                "ps",
                "-a",
                "--filter",
                f"name=^{prefix}",
                "--format",
                "{{.ID}} {{.Names}}",
            ],
            capture_output=True,
            text=True,
            timeout=DEFAULT_DOCKER_TEARDOWN_TIMEOUT_S,
            check=False,
        )
    except FileNotFoundError as exc:
        raise DockerUnavailableError(f"{DOCKER_CLI} CLI not found on PATH") from exc
    except subprocess.TimeoutExpired:
        logger.warning("KEI-211 reaper: docker ps timed out — skipping pass")
        return None
    if result.returncode != 0:
        logger.warning(
            "KEI-211 reaper: docker ps rc=%d stderr=%s",
            result.returncode,
            result.stderr.strip()[:200],
        )
        return None
    out: list[tuple[str, str]] = []
    for line in result.stdout.splitlines():
        parts = line.split(maxsplit=1)
        if len(parts) == 2:
            out.append((parts[0], parts[1]))
    return out


class Reaper:
    """Kills + cleans dispatcher sessions/containers no longer in registry.

    The dispatcher registers each session it starts; when the session ends
    normally it's unregistered. ``sweep()`` scans the host and kills
    anything matching the name prefix that is not currently registered, OR
    is registered but has exceeded its TTL.
    """

    def __init__(
        self,
        *,
        tmux_name_prefix: str,
        container_name_prefix: str,
        default_ttl_s: float | None = None,
    ) -> None:
        if not tmux_name_prefix or not container_name_prefix:
            raise ValueError(
                "Reaper requires non-empty tmux_name_prefix and container_name_prefix "
                "to avoid reaping unrelated sessions/containers on the host"
            )
        self._tmux_prefix = tmux_name_prefix
        self._container_prefix = container_name_prefix
        self._default_ttl_s = default_ttl_s
        # Registered handles keyed by name (tmux) or id (container).
        self._tmux_registry: dict[str, tuple[SessionHandle, float]] = {}
        self._container_registry: dict[str, tuple[ContainerHandle, float]] = {}
        self._last_result: ReapResult | None = None

    # ------------------------------------------------------------------
    # registry
    # ------------------------------------------------------------------

    def register_tmux(self, handle: SessionHandle, *, ttl_s: float | None = None) -> None:
        if not handle.session_name.startswith(self._tmux_prefix):
            raise ValueError(
                f"tmux session {handle.session_name!r} does not start with "
                f"registered prefix {self._tmux_prefix!r}"
            )
        ttl = ttl_s if ttl_s is not None else self._default_ttl_s
        deadline = time.monotonic() + ttl if ttl is not None else float("inf")
        self._tmux_registry[handle.session_name] = (handle, deadline)

    def register_container(self, handle: ContainerHandle, *, ttl_s: float | None = None) -> None:
        if not handle.name.startswith(self._container_prefix):
            raise ValueError(
                f"container name {handle.name!r} does not start with "
                f"registered prefix {self._container_prefix!r}"
            )
        ttl = ttl_s if ttl_s is not None else self._default_ttl_s
        deadline = time.monotonic() + ttl if ttl is not None else float("inf")
        self._container_registry[handle.id] = (handle, deadline)

    def unregister_tmux(self, session_name: str) -> None:
        self._tmux_registry.pop(session_name, None)

    def unregister_container(self, container_id: str) -> None:
        self._container_registry.pop(container_id, None)

    # ------------------------------------------------------------------
    # sweep
    # ------------------------------------------------------------------

    def _sweep_tmux(self) -> tuple[int, list[ReapEvent]]:
        try:
            live = _list_tmux_sessions()
        except TmuxUnavailableError:
            logger.info("KEI-211 reaper: tmux unavailable, skipping tmux sweep")
            return (0, [])
        if live is None:
            return (0, [])
        scoped = [s for s in live if s.startswith(self._tmux_prefix)]
        events: list[ReapEvent] = []
        now = time.monotonic()

        # Orphans: live in tmux but not in our registry.
        for name in scoped:
            if name not in self._tmux_registry:
                events.append(self._kill_tmux(name, reason="orphan"))

        # TTL-exceeded: registered AND live AND past deadline. Collect first,
        # then pop after the loop so we never mutate the dict mid-iteration.
        ttl_exceeded: list[str] = []
        for name, (_handle, deadline) in self._tmux_registry.items():
            if name in scoped and now >= deadline:
                ttl_exceeded.append(name)
        for name in ttl_exceeded:
            handle = self._tmux_registry[name][0]
            events.append(self._kill_tmux(handle.session_name, reason="ttl_exceeded"))
            self._tmux_registry.pop(name, None)

        return (len(scoped), events)

    def _sweep_containers(self) -> tuple[int, list[ReapEvent]]:
        try:
            live = _list_containers_by_prefix(self._container_prefix)
        except DockerUnavailableError:
            logger.info("KEI-211 reaper: docker unavailable, skipping container sweep")
            return (0, [])
        if live is None:
            return (0, [])
        events: list[ReapEvent] = []
        now = time.monotonic()

        registered_ids = set(self._container_registry)
        # Orphans
        for cid, name in live:
            if cid not in registered_ids:
                events.append(self._kill_container_by_id(cid, name, reason="orphan"))

        # TTL-exceeded — collect first, mutate after.
        live_ids = {cid for cid, _ in live}
        ttl_exceeded: list[str] = []
        for cid, (_handle, deadline) in self._container_registry.items():
            if cid in live_ids and now >= deadline:
                ttl_exceeded.append(cid)
        for cid in ttl_exceeded:
            handle = self._container_registry[cid][0]
            events.append(self._kill_container_by_id(cid, handle.name, reason="ttl_exceeded"))
            self._container_registry.pop(cid, None)

        return (len(live), events)

    def _kill_tmux(self, name: str, *, reason: str) -> ReapEvent:
        try:
            handle = self._tmux_registry.get(name, (None, 0.0))[0]
            target = handle or SessionHandle(session_name=name, working_dir="/", command="")
            terminate(target)
            logger.info("KEI-211 reaper killed tmux %r (%s)", name, reason)
            return ReapEvent(kind="tmux", name_or_id=name, reason=reason, success=True)
        except Exception as exc:  # noqa: BLE001
            logger.warning("KEI-211 reaper failed to kill tmux %r: %s", name, exc)
            return ReapEvent(kind="tmux", name_or_id=name, reason=reason, success=False)

    def _kill_container_by_id(self, cid: str, name: str, *, reason: str) -> ReapEvent:
        try:
            handle = self._container_registry.get(cid, (None, 0.0))[0]
            target = handle or ContainerHandle(id=cid, name=name, image="", port=0)
            kill_and_remove(target)
            logger.info("KEI-211 reaper killed container %s/%s (%s)", cid[:12], name, reason)
            return ReapEvent(kind="container", name_or_id=cid, reason=reason, success=True)
        except Exception as exc:  # noqa: BLE001
            logger.warning("KEI-211 reaper failed to kill container %s: %s", cid[:12], exc)
            return ReapEvent(kind="container", name_or_id=cid, reason=reason, success=False)

    def sweep(self) -> ReapResult:
        """Run one full pass; reap orphans + TTL-exceeded. Best-effort."""
        scanned_tmux, tmux_events = self._sweep_tmux()
        scanned_containers, container_events = self._sweep_containers()
        result = ReapResult(
            scanned_tmux=scanned_tmux,
            scanned_containers=scanned_containers,
            reaped=tuple(tmux_events + container_events),
        )
        self._last_result = result
        return result

    # ------------------------------------------------------------------
    # reporting
    # ------------------------------------------------------------------

    def health_snapshot(self) -> dict[str, object]:
        """Status block for the dispatcher health endpoint.

        ``status`` is "green" when the last sweep had no failed reaps,
        otherwise "degraded". When ``sweep()`` has never run, status is
        "unknown".
        """
        if self._last_result is None:
            return {
                "component": "reaper",
                "status": "unknown",
                "tracked_tmux": len(self._tmux_registry),
                "tracked_containers": len(self._container_registry),
                "last_reaped": 0,
                "last_failed": 0,
            }
        failed = sum(1 for e in self._last_result.reaped if not e.success)
        status = "green" if failed == 0 else "degraded"
        return {
            "component": "reaper",
            "status": status,
            "tracked_tmux": len(self._tmux_registry),
            "tracked_containers": len(self._container_registry),
            "last_reaped": self._last_result.total_reaped,
            "last_failed": failed,
        }
