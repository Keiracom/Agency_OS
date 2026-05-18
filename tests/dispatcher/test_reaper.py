"""Tests for KEI-211 reaper — zombie session detection + cleanup."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from src.dispatcher.container_lifecycle import ContainerHandle
from src.dispatcher.reaper import Reaper
from src.dispatcher.tmux_lifecycle import SessionHandle


def _proc(stdout: str = "", returncode: int = 0, stderr: str = "") -> MagicMock:
    p = MagicMock()
    p.stdout = stdout
    p.stderr = stderr
    p.returncode = returncode
    return p


def _tmux_handle(name: str, working_dir: str) -> SessionHandle:
    """Build a SessionHandle. ``working_dir`` MUST come from pytest's
    ``tmp_path`` fixture (per-test isolated dir) — never the shared /tmp,
    which Sonar S5443 flags as a path-traversal vector in tests.
    """
    return SessionHandle(session_name=name, working_dir=working_dir, command="bash")


def _container_handle(cid: str, name: str) -> ContainerHandle:
    return ContainerHandle(id=cid, name=name, image="img:latest", port=8080)


class TestReaperConstruction:
    def test_empty_prefix_rejected(self) -> None:
        with pytest.raises(ValueError, match="non-empty"):
            Reaper(tmux_name_prefix="", container_name_prefix="kei211-")
        with pytest.raises(ValueError, match="non-empty"):
            Reaper(tmux_name_prefix="kei211-", container_name_prefix="")

    def test_registry_rejects_mismatched_prefix_tmux(self, tmp_path) -> None:
        r = Reaper(tmux_name_prefix="kei211-", container_name_prefix="kei211-c-")
        with pytest.raises(ValueError, match="does not start with"):
            r.register_tmux(_tmux_handle("other-session", str(tmp_path)))

    def test_registry_rejects_mismatched_prefix_container(self) -> None:
        r = Reaper(tmux_name_prefix="kei211-", container_name_prefix="kei211-c-")
        with pytest.raises(ValueError, match="does not start with"):
            r.register_container(_container_handle("abc", "other-container"))


class TestReaperTmuxSweep:
    def test_orphan_tmux_session_reaped(self, tmp_path) -> None:
        r = Reaper(tmux_name_prefix="kei211-", container_name_prefix="kei211-c-")
        # Listed: kei211-orphan + kei211-known; only kei211-known is registered.
        r.register_tmux(_tmux_handle("kei211-known", str(tmp_path)))
        list_proc = _proc("kei211-orphan\nkei211-known\nunrelated-thing\n")
        kill_calls: list[list[str]] = []

        def fake_run(argv: list[str], **_kw: object) -> MagicMock:
            kill_calls.append(argv)
            if argv[1] == "list-sessions":
                return list_proc
            return _proc()

        with (
            patch("src.dispatcher.reaper.subprocess.run", side_effect=fake_run),
            patch(
                "src.dispatcher.reaper._list_containers_by_prefix",
                return_value=[],
            ),
        ):
            result = r.sweep()
        # Orphan reaped, known left alone, unrelated never touched.
        reaped_names = [e.name_or_id for e in result.reaped]
        assert "kei211-orphan" in reaped_names
        assert "kei211-known" not in reaped_names
        assert "unrelated-thing" not in reaped_names
        assert all(e.reason == "orphan" for e in result.reaped)

    def test_ttl_exceeded_tmux_session_reaped(self, tmp_path) -> None:
        r = Reaper(
            tmux_name_prefix="kei211-",
            container_name_prefix="kei211-c-",
            default_ttl_s=10.0,
        )
        with patch("src.dispatcher.reaper.time.monotonic", return_value=100.0):
            r.register_tmux(_tmux_handle("kei211-old", str(tmp_path)))
        list_proc = _proc("kei211-old\n")
        with (
            patch("src.dispatcher.reaper.subprocess.run", return_value=list_proc),
            patch("src.dispatcher.reaper.time.monotonic", return_value=200.0),
            patch("src.dispatcher.reaper._list_containers_by_prefix", return_value=[]),
            patch("src.dispatcher.reaper.terminate") as mock_terminate,
        ):
            result = r.sweep()
        assert len(result.reaped) == 1
        assert result.reaped[0].reason == "ttl_exceeded"
        mock_terminate.assert_called_once()

    def test_no_zombies_no_reap(self, tmp_path) -> None:
        r = Reaper(tmux_name_prefix="kei211-", container_name_prefix="kei211-c-")
        r.register_tmux(_tmux_handle("kei211-alive", str(tmp_path)))
        with (
            patch(
                "src.dispatcher.reaper.subprocess.run",
                return_value=_proc("kei211-alive\n"),
            ),
            patch("src.dispatcher.reaper._list_containers_by_prefix", return_value=[]),
            patch("src.dispatcher.reaper.terminate") as mock_terminate,
        ):
            result = r.sweep()
        assert result.total_reaped == 0
        mock_terminate.assert_not_called()

    def test_tmux_unavailable_skips_pass_no_crash(self) -> None:
        r = Reaper(tmux_name_prefix="kei211-", container_name_prefix="kei211-c-")
        with (
            patch(
                "src.dispatcher.reaper.subprocess.run",
                side_effect=FileNotFoundError("no tmux"),
            ),
            patch("src.dispatcher.reaper._list_containers_by_prefix", return_value=[]),
        ):
            result = r.sweep()
        assert result.total_reaped == 0
        assert result.scanned_tmux == 0


class TestReaperContainerSweep:
    def test_orphan_container_reaped(self) -> None:
        r = Reaper(tmux_name_prefix="kei211-", container_name_prefix="kei211-c-")
        r.register_container(_container_handle("known-id", "kei211-c-known"))
        with (
            patch("src.dispatcher.reaper._list_tmux_sessions", return_value=[]),
            patch(
                "src.dispatcher.reaper._list_containers_by_prefix",
                return_value=[
                    ("orphan-id", "kei211-c-orphan"),
                    ("known-id", "kei211-c-known"),
                ],
            ),
            patch("src.dispatcher.reaper.kill_and_remove") as mock_kar,
        ):
            result = r.sweep()
        assert mock_kar.call_count == 1
        reaped_ids = [e.name_or_id for e in result.reaped]
        assert reaped_ids == ["orphan-id"]
        assert result.reaped[0].kind == "container"
        assert result.reaped[0].reason == "orphan"

    def test_ttl_exceeded_container_reaped(self) -> None:
        r = Reaper(
            tmux_name_prefix="kei211-",
            container_name_prefix="kei211-c-",
            default_ttl_s=10.0,
        )
        with patch("src.dispatcher.reaper.time.monotonic", return_value=100.0):
            r.register_container(_container_handle("old-id", "kei211-c-old"))
        with (
            patch("src.dispatcher.reaper._list_tmux_sessions", return_value=[]),
            patch(
                "src.dispatcher.reaper._list_containers_by_prefix",
                return_value=[("old-id", "kei211-c-old")],
            ),
            patch("src.dispatcher.reaper.time.monotonic", return_value=200.0),
            patch("src.dispatcher.reaper.kill_and_remove") as mock_kar,
        ):
            result = r.sweep()
        assert result.total_reaped == 1
        assert result.reaped[0].reason == "ttl_exceeded"
        mock_kar.assert_called_once()


class TestReaperSnapshot:
    def test_unknown_before_first_sweep(self) -> None:
        r = Reaper(tmux_name_prefix="kei211-", container_name_prefix="kei211-c-")
        snap = r.health_snapshot()
        assert snap["status"] == "unknown"

    def test_green_after_clean_sweep(self) -> None:
        r = Reaper(tmux_name_prefix="kei211-", container_name_prefix="kei211-c-")
        with (
            patch("src.dispatcher.reaper._list_tmux_sessions", return_value=[]),
            patch("src.dispatcher.reaper._list_containers_by_prefix", return_value=[]),
        ):
            r.sweep()
        snap = r.health_snapshot()
        assert snap["status"] == "green"
        assert snap["last_reaped"] == 0
        assert snap["last_failed"] == 0

    def test_degraded_on_kill_failure(self) -> None:
        r = Reaper(tmux_name_prefix="kei211-", container_name_prefix="kei211-c-")
        with (
            patch(
                "src.dispatcher.reaper._list_tmux_sessions",
                return_value=["kei211-orphan"],
            ),
            patch("src.dispatcher.reaper._list_containers_by_prefix", return_value=[]),
            patch("src.dispatcher.reaper.terminate", side_effect=RuntimeError("kaboom")),
        ):
            r.sweep()
        snap = r.health_snapshot()
        assert snap["status"] == "degraded"
        assert snap["last_failed"] == 1


class TestReaperRegistry:
    def test_unregister_tmux_removes(self, tmp_path) -> None:
        r = Reaper(tmux_name_prefix="kei211-", container_name_prefix="kei211-c-")
        r.register_tmux(_tmux_handle("kei211-a", str(tmp_path)))
        assert r.health_snapshot()["tracked_tmux"] == 1
        r.unregister_tmux("kei211-a")
        assert r.health_snapshot()["tracked_tmux"] == 0

    def test_unregister_container_removes(self) -> None:
        r = Reaper(tmux_name_prefix="kei211-", container_name_prefix="kei211-c-")
        r.register_container(_container_handle("cid", "kei211-c-x"))
        assert r.health_snapshot()["tracked_containers"] == 1
        r.unregister_container("cid")
        assert r.health_snapshot()["tracked_containers"] == 0
