"""KEI-115A — tests for src/dispatcher/container_lifecycle.

All docker CLI calls are mocked at the subprocess.run boundary; no live
docker daemon required for CI. Health probes are stubbed at the
_probe_health helper boundary so tests don't open real sockets.
"""

from __future__ import annotations

import subprocess
from types import SimpleNamespace

import pytest

from src.dispatcher.container_lifecycle import (
    ContainerHandle,
    ContainerStartupError,
    DockerUnavailableError,
    kill_and_remove,
    spawn_container,
    wait_healthy,
)


def _docker_ok(stdout: str = "abc123\n", stderr: str = "", returncode: int = 0):
    """Build a fake subprocess.run return value."""
    return SimpleNamespace(stdout=stdout, stderr=stderr, returncode=returncode)


def _handle(**overrides) -> ContainerHandle:
    defaults = {"id": "abc123def456", "name": "task-1", "image": "img:latest", "port": 8080}
    defaults.update(overrides)
    return ContainerHandle(**defaults)


# ─── spawn_container ───────────────────────────────────────────────────────


def test_spawn_container_runs_docker_with_expected_args(monkeypatch):
    """Verify the docker CLI invocation shape: `docker run -d --name <n>
    -p <port>:<port> <image>`."""
    captured: dict = {}

    def fake_run(cmd, **kwargs):
        captured["cmd"] = list(cmd)
        return _docker_ok(stdout="abc123def456\n")

    monkeypatch.setattr(subprocess, "run", fake_run)
    h = spawn_container(image="python:3.12-slim", name="task-1", port=8080)
    assert h.id == "abc123def456"
    assert h.name == "task-1"
    assert h.image == "python:3.12-slim"
    assert h.port == 8080
    assert h.health_path == "/healthz"
    cmd = captured["cmd"]
    assert cmd[:6] == ["docker", "run", "-d", "--name", "task-1", "-p"]
    assert "8080:8080" in cmd
    assert cmd[-1] == "python:3.12-slim"


def test_spawn_container_passes_env_vars(monkeypatch):
    """Each env entry becomes a separate `-e K=V` pair in argv order."""
    captured: dict = {}

    def fake_run(cmd, **kwargs):
        captured["cmd"] = list(cmd)
        return _docker_ok()

    monkeypatch.setattr(subprocess, "run", fake_run)
    spawn_container(image="img", name="n", port=1, env={"FOO": "bar", "BAZ": "qux"})
    cmd = captured["cmd"]
    # -e flag appears for each entry
    e_indices = [i for i, tok in enumerate(cmd) if tok == "-e"]
    assert len(e_indices) == 2
    e_values = {cmd[i + 1] for i in e_indices}
    assert e_values == {"FOO=bar", "BAZ=qux"}


def test_spawn_container_appends_extra_args(monkeypatch):
    """extra_args are inserted before the image name (after env)."""
    captured: dict = {}

    def fake_run(cmd, **kwargs):
        captured["cmd"] = list(cmd)
        return _docker_ok()

    monkeypatch.setattr(subprocess, "run", fake_run)
    spawn_container(
        image="img",
        name="n",
        port=1,
        extra_args=["--read-only", "--memory=512m"],
    )
    cmd = captured["cmd"]
    assert "--read-only" in cmd
    assert "--memory=512m" in cmd
    # image is the last token
    assert cmd[-1] == "img"
    # extras appear before the image
    assert cmd.index("--read-only") < cmd.index("img")


def test_spawn_container_raises_clean_error_when_docker_missing(monkeypatch):
    """FileNotFoundError from subprocess maps to DockerUnavailableError."""

    def fake_run(*args, **kwargs):
        raise FileNotFoundError(2, "No such file or directory: 'docker'")

    monkeypatch.setattr(subprocess, "run", fake_run)
    with pytest.raises(DockerUnavailableError, match="docker"):
        spawn_container(image="img", name="n", port=1)


def test_spawn_container_raises_on_nonzero_rc(monkeypatch):
    """Non-zero docker run exit (e.g. port-in-use rc=125) raises
    ContainerStartupError with the stderr preserved."""
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *a, **kw: _docker_ok(stdout="", stderr="port already in use", returncode=125),
    )
    with pytest.raises(ContainerStartupError, match="rc=125") as exc_info:
        spawn_container(image="img", name="n", port=1)
    assert "port already in use" in str(exc_info.value)


def test_spawn_container_raises_on_empty_stdout(monkeypatch):
    """rc=0 but no container id is still a failure — defensive."""
    monkeypatch.setattr(subprocess, "run", lambda *a, **kw: _docker_ok(stdout="   \n"))
    with pytest.raises(ContainerStartupError, match="empty container id"):
        spawn_container(image="img", name="n", port=1)


# ─── wait_healthy ──────────────────────────────────────────────────────────


def test_wait_healthy_returns_true_on_first_probe(monkeypatch):
    """Healthy on the first probe — no retries, no kill."""
    monkeypatch.setattr(
        "src.dispatcher.container_lifecycle._probe_health",
        lambda host, port, path: True,
    )
    # If wait_healthy called docker, the test would fail because no fake_run
    # is wired here — confirms healthy path doesn't touch docker.
    assert wait_healthy(_handle(), timeout_s=5.0, interval_s=0.01) is True


def test_wait_healthy_returns_true_after_retries(monkeypatch):
    """Probe returns False twice then True — wait_healthy retries through
    the failures and reports healthy on the third probe."""
    counter = {"n": 0}

    def probe(host, port, path):
        counter["n"] += 1
        return counter["n"] >= 3

    monkeypatch.setattr("src.dispatcher.container_lifecycle._probe_health", probe)
    assert wait_healthy(_handle(), timeout_s=5.0, interval_s=0.01) is True
    assert counter["n"] >= 3


def test_wait_healthy_aborts_and_kills_on_timeout(monkeypatch):
    """Health probe never succeeds — wait_healthy must:
    1. raise ContainerStartupError
    2. call `docker kill` + `docker rm -f` BEFORE raising."""
    kill_cmds: list[list[str]] = []

    monkeypatch.setattr(
        "src.dispatcher.container_lifecycle._probe_health",
        lambda *args, **kwargs: False,
    )

    def fake_run(cmd, **kwargs):
        kill_cmds.append(list(cmd))
        return _docker_ok()

    monkeypatch.setattr(subprocess, "run", fake_run)
    with pytest.raises(ContainerStartupError, match="failed health check"):
        wait_healthy(_handle(), timeout_s=0.05, interval_s=0.01)
    ops = [cmd[1] for cmd in kill_cmds]
    assert "kill" in ops
    assert "rm" in ops
    # rm runs after kill
    assert ops.index("kill") < ops.index("rm")


def test_wait_healthy_respects_custom_host(monkeypatch):
    """Non-default host is passed through to _probe_health."""
    captured: dict = {}

    def probe(host, port, path):
        captured["host"] = host
        captured["port"] = port
        captured["path"] = path
        return True

    monkeypatch.setattr("src.dispatcher.container_lifecycle._probe_health", probe)
    assert wait_healthy(_handle(port=9000), timeout_s=1.0, interval_s=0.01, host="container-host")
    assert captured == {"host": "container-host", "port": 9000, "path": "/healthz"}


def test_wait_healthy_uses_handle_health_path(monkeypatch):
    """Custom health_path on the handle is honoured by the probe."""
    captured: dict = {}

    def probe(host, port, path):
        captured["path"] = path
        return True

    monkeypatch.setattr("src.dispatcher.container_lifecycle._probe_health", probe)
    wait_healthy(_handle(), timeout_s=1.0, interval_s=0.01)
    # default
    assert captured["path"] == "/healthz"

    captured.clear()
    custom = ContainerHandle(id="x", name="y", image="z", port=1, health_path="/api/health")
    wait_healthy(custom, timeout_s=1.0, interval_s=0.01)
    assert captured["path"] == "/api/health"


# ─── kill_and_remove ───────────────────────────────────────────────────────


def test_kill_and_remove_runs_kill_then_rm(monkeypatch):
    """Two docker invocations in order: kill then rm -f."""
    calls: list[list[str]] = []

    def fake_run(cmd, **kwargs):
        calls.append(list(cmd))
        return _docker_ok()

    monkeypatch.setattr(subprocess, "run", fake_run)
    kill_and_remove(_handle())
    assert len(calls) == 2
    assert calls[0][1] == "kill"
    assert calls[1][1:3] == ["rm", "-f"]
    # both target the container id
    assert calls[0][-1] == "abc123def456"
    assert calls[1][-1] == "abc123def456"


def test_kill_and_remove_logs_but_does_not_raise_on_docker_error(monkeypatch, caplog):
    """Stale containers, already-removed containers etc. produce non-zero
    rcs. kill_and_remove must NOT raise — it's an abort path that runs
    inside wait_healthy's exception branch and must not mask the
    original ContainerStartupError."""

    def fake_run(cmd, **kwargs):
        return _docker_ok(returncode=1, stderr=f"Error: No such container: {cmd[-1]}")

    monkeypatch.setattr(subprocess, "run", fake_run)
    with caplog.at_level("WARNING"):
        kill_and_remove(_handle())
    assert any("No such container" in r.message for r in caplog.records)


def test_kill_and_remove_propagates_docker_unavailable(monkeypatch):
    """If docker disappears between spawn and teardown (impossible but
    defensive), DockerUnavailableError must surface — not be swallowed —
    so the operator sees the environment is broken."""

    def fake_run(*args, **kwargs):
        raise FileNotFoundError("docker")

    monkeypatch.setattr(subprocess, "run", fake_run)
    with pytest.raises(DockerUnavailableError):
        kill_and_remove(_handle())
