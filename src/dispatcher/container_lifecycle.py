"""KEI-115A — Container spawn + startup timeout + health check.

Foundational primitive for Part 17 dispatcher product layer. Wraps the
local docker CLI via subprocess (one less dependency than docker-py;
tracks vendor shape verbatim — see `empirical-smoke-catches-paper-review-3`).

Caller responsibility: the container image must expose an HTTP health
endpoint (default ``/healthz``) on the published port. ``wait_healthy``
polls that endpoint and aborts cleanly via ``docker kill`` + ``docker
rm -f`` if it doesn't respond 2xx within the startup timeout. KEI-163
(KEI-115B) handles the longer-running lifecycle monitor; this module is
spawn + wait + clean-abort only.
"""

from __future__ import annotations

import contextlib
import http.client
import logging
import subprocess
import time
from dataclasses import dataclass

logger = logging.getLogger(__name__)

DEFAULT_HEALTH_PATH = "/healthz"
DEFAULT_STARTUP_TIMEOUT_S = 30.0
DEFAULT_POLL_INTERVAL_S = 1.0
DEFAULT_HEALTH_PROBE_TIMEOUT_S = 2.0
DEFAULT_DOCKER_CMD_TIMEOUT_S = 30.0
DEFAULT_DOCKER_TEARDOWN_TIMEOUT_S = 10.0
DOCKER_CLI = "docker"


class ContainerStartupError(RuntimeError):
    """Container failed to start or become healthy within startup timeout.

    On the wait_healthy timeout path, the container has already been
    killed + removed before this is raised — caller does not need to
    clean up.
    """


class DockerUnavailableError(RuntimeError):
    """The docker CLI is not installed or not on PATH."""


@dataclass(frozen=True)
class ContainerHandle:
    """Reference to a running container. Returned by `spawn_container`,
    consumed by `wait_healthy` / `kill_and_remove` / future lifecycle ops.
    """

    id: str
    name: str
    image: str
    port: int
    health_path: str = DEFAULT_HEALTH_PATH


def _run_docker(
    args: list[str], timeout_s: float = DEFAULT_DOCKER_CMD_TIMEOUT_S
) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(  # noqa: S603 — controlled args, no shell
            [DOCKER_CLI, *args],
            capture_output=True,
            text=True,
            timeout=timeout_s,
            check=False,
        )
    except FileNotFoundError as exc:
        raise DockerUnavailableError(f"{DOCKER_CLI} CLI not found on PATH") from exc


def spawn_container(
    *,
    image: str,
    name: str,
    port: int,
    env: dict[str, str] | None = None,
    health_path: str = DEFAULT_HEALTH_PATH,
    extra_args: list[str] | None = None,
) -> ContainerHandle:
    """Start a detached container and return a handle.

    Image-agnostic — caller passes ``image`` so the same primitive serves
    the BYO-key Claude-side container and future per-tier containers.
    Does NOT block on health; call ``wait_healthy(handle)`` next.

    Raises:
        DockerUnavailableError: docker CLI missing from PATH.
        ContainerStartupError: ``docker run`` returned non-zero or empty id.
    """
    cmd: list[str] = ["run", "-d", "--name", name, "-p", f"{port}:{port}"]
    for k, v in (env or {}).items():
        cmd += ["-e", f"{k}={v}"]
    if extra_args:
        cmd += list(extra_args)
    cmd.append(image)

    out = _run_docker(cmd)
    if out.returncode != 0:
        raise ContainerStartupError(
            f"docker run failed (rc={out.returncode}): {out.stderr.strip()[:300]}"
        )
    container_id = out.stdout.strip()
    if not container_id:
        raise ContainerStartupError("docker run returned empty container id")
    return ContainerHandle(
        id=container_id,
        name=name,
        image=image,
        port=port,
        health_path=health_path,
    )


def _probe_health(host: str, port: int, path: str) -> bool:
    """Return True iff GET http://host:port<path> responds 2xx within
    DEFAULT_HEALTH_PROBE_TIMEOUT_S. Any network/protocol error is False
    (caller treats this as 'not yet ready' and retries until timeout).
    """
    conn = None
    try:
        conn = http.client.HTTPConnection(host, port, timeout=DEFAULT_HEALTH_PROBE_TIMEOUT_S)
        conn.request("GET", path)
        resp = conn.getresponse()
        ok = 200 <= resp.status < 300
        resp.read()
        return ok
    except (OSError, http.client.HTTPException):
        return False
    finally:
        if conn is not None:
            with contextlib.suppress(OSError):
                conn.close()


def wait_healthy(
    handle: ContainerHandle,
    *,
    timeout_s: float = DEFAULT_STARTUP_TIMEOUT_S,
    interval_s: float = DEFAULT_POLL_INTERVAL_S,
    host: str = "127.0.0.1",
) -> bool:
    """Poll the container's health endpoint until it returns 2xx or timeout.

    On timeout: kill_and_remove the container, then raise
    ContainerStartupError. The container is gone before the exception
    surfaces — caller does not need to clean up.
    """
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        if _probe_health(host, handle.port, handle.health_path):
            logger.info(
                "container %s healthy on %s:%d%s",
                handle.id[:12],
                host,
                handle.port,
                handle.health_path,
            )
            return True
        time.sleep(interval_s)

    logger.warning(
        "container %s failed health check within %.1fs — aborting",
        handle.id[:12],
        timeout_s,
    )
    kill_and_remove(handle)
    raise ContainerStartupError(
        f"container {handle.id[:12]} ({handle.image}) failed health check within {timeout_s:.1f}s"
    )


def kill_and_remove(handle: ContainerHandle) -> None:
    """Best-effort stop + remove. Logs but does not raise on docker
    errors — the abort path must not mask the original failure for
    callers using this from `wait_healthy`'s timeout branch.
    """
    for op in (["kill", handle.id], ["rm", "-f", handle.id]):
        result = _run_docker(op, timeout_s=DEFAULT_DOCKER_TEARDOWN_TIMEOUT_S)
        if result.returncode != 0:
            logger.warning(
                "docker %s %s failed (rc=%d): %s",
                op[0],
                handle.id[:12],
                result.returncode,
                result.stderr.strip()[:200],
            )
