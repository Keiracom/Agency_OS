"""KEI-163 — container lifecycle monitor: status poll + reap on exit.

Long-running companion to spawn_container/wait_healthy (KEI-115A). Polls
`docker inspect` on a configurable cadence; when state transitions to
'exited', persists the final state to public.tasks (container_exit_code +
container_ended_at) and best-effort reaps the container via kill_and_remove.

Acceptance (Linear KEI-163): monitor detects exit within 5s; reaps
container; logs final state to tasks table.
"""

from __future__ import annotations

import datetime as dt
import logging
import os
import subprocess
import time
from collections.abc import Callable
from dataclasses import dataclass

from src.dispatcher.container_lifecycle import (
    ContainerHandle,
    DockerUnavailableError,
    kill_and_remove,
)

logger = logging.getLogger(__name__)

DEFAULT_POLL_INTERVAL_S: float = 2.0  # 2s ≤ 5s acceptance budget
DEFAULT_INSPECT_TIMEOUT_S: float = 5.0
DOCKER_CLI = "docker"

_SOURCE_DOC = "KEI-163"


@dataclass(frozen=True)
class MonitorResult:
    status: str  # 'exited' or 'timeout'
    exit_code: int | None
    ended_at: dt.datetime | None


def _inspect_state(handle: ContainerHandle) -> tuple[str, int | None]:
    """Return ('running'|'exited'|'unknown', exit_code_or_None).

    Calls ``docker inspect --format '{{.State.Status}} {{.State.ExitCode}}'``.
    Non-zero return code or FileNotFoundError → ('unknown', None).
    DockerUnavailableError is re-raised so the caller can surface it.
    """
    try:
        result = subprocess.run(  # noqa: S603
            [
                DOCKER_CLI,
                "inspect",
                "--format",
                "{{.State.Status}} {{.State.ExitCode}}",
                handle.id,
            ],
            capture_output=True,
            text=True,
            timeout=DEFAULT_INSPECT_TIMEOUT_S,
            check=False,
        )
    except FileNotFoundError as exc:
        raise DockerUnavailableError(f"{DOCKER_CLI} CLI not found on PATH") from exc

    if result.returncode != 0:
        logger.debug(
            "%s inspect rc=%d stderr=%s",
            _SOURCE_DOC,
            result.returncode,
            result.stderr.strip()[:200],
        )
        return ("unknown", None)

    raw = result.stdout.strip()
    parts = raw.split(maxsplit=1)
    if not parts:
        return ("unknown", None)

    status = parts[0].lower()
    exit_code: int | None = None
    if len(parts) == 2:
        with __import__("contextlib").suppress(ValueError):
            exit_code = int(parts[1])

    return (status, exit_code)


def _default_persist(task_id: str, result: MonitorResult) -> None:
    """UPDATE public.tasks SET container_exit_code, container_ended_at WHERE id.

    psycopg.Error is caught and logged — monitor reports the result
    regardless of DB write success (fail-open by spec).
    """
    dsn = os.environ.get("DATABASE_URL", "")
    if not dsn:
        logger.warning(
            "%s DATABASE_URL not set — skipping task persist for %s", _SOURCE_DOC, task_id
        )
        return

    try:
        import psycopg  # type: ignore[import]

        with psycopg.connect(dsn, prepare_threshold=None) as conn, conn.cursor() as cur:
            cur.execute(
                """
                UPDATE public.tasks
                   SET container_exit_code = %s,
                       container_ended_at  = %s
                 WHERE id = %s
                """,
                (result.exit_code, result.ended_at, task_id),
            )
        logger.info(
            "%s persisted exit_code=%s ended_at=%s for task %s",
            _SOURCE_DOC,
            result.exit_code,
            result.ended_at,
            task_id,
        )
    except Exception as exc:  # noqa: BLE001
        logger.error(
            "%s persist failed for task %s: %s",
            _SOURCE_DOC,
            task_id,
            exc,
        )


def monitor_container(
    handle: ContainerHandle,
    *,
    task_id: str,
    poll_interval_s: float = DEFAULT_POLL_INTERVAL_S,
    overall_timeout_s: float | None = None,
    persist_fn: Callable[[str, MonitorResult], None] | None = None,
    reap_fn: Callable[[ContainerHandle], None] | None = None,
) -> MonitorResult:
    """Block until the container exits, then reap + persist + return.

    Returns MonitorResult(status='exited', exit_code=N, ended_at=now) when
    inspect reports exited. Returns MonitorResult(status='timeout', ...)
    if overall_timeout_s is set and elapsed before exit detected.

    On exit: calls reap_fn(handle) (default = kill_and_remove) and
    persist_fn(task_id, result) (default = _default_persist).
    Persistence failures are logged not raised — caller still gets the
    MonitorResult.

    Raises:
        DockerUnavailableError: if the docker CLI is absent (propagated from
            _inspect_state on the very first poll).
        ValueError: if poll_interval_s > 5.0 (enforcement of acceptance budget).
    """
    if poll_interval_s > 5.0:
        raise ValueError(
            f"poll_interval_s={poll_interval_s} exceeds 5s acceptance budget (KEI-163)"
        )

    _persist = persist_fn if persist_fn is not None else _default_persist
    _reap = reap_fn if reap_fn is not None else kill_and_remove

    start = time.monotonic()
    deadline = (start + overall_timeout_s) if overall_timeout_s is not None else None

    while True:
        status, exit_code = _inspect_state(handle)

        if status == "exited":
            ended_at = dt.datetime.now(tz=dt.UTC)
            result = MonitorResult(status="exited", exit_code=exit_code, ended_at=ended_at)
            logger.info(
                "%s container %s exited (code=%s) after %.1fs",
                _SOURCE_DOC,
                handle.id[:12],
                exit_code,
                time.monotonic() - start,
            )
            try:
                _reap(handle)
            except Exception as exc:  # noqa: BLE001
                logger.warning("%s reap failed for %s: %s", _SOURCE_DOC, handle.id[:12], exc)

            try:
                _persist(task_id, result)
            except Exception as exc:  # noqa: BLE001
                logger.error("%s persist_fn raised for task %s: %s", _SOURCE_DOC, task_id, exc)

            return result

        if deadline is not None and time.monotonic() >= deadline:
            result = MonitorResult(status="timeout", exit_code=None, ended_at=None)
            logger.warning(
                "%s monitor timed out after %.1fs for container %s",
                _SOURCE_DOC,
                overall_timeout_s,
                handle.id[:12],
            )
            try:
                _persist(task_id, result)
            except Exception as exc:  # noqa: BLE001
                logger.error(
                    "%s persist_fn raised on timeout for task %s: %s", _SOURCE_DOC, task_id, exc
                )
            return result

        time.sleep(poll_interval_s)
