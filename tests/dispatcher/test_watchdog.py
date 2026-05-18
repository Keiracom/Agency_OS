"""Tests for KEI-211 watchdog — liveness probe + hang detection."""

from __future__ import annotations

import math
from unittest.mock import MagicMock, patch

import pytest

from src.dispatcher.container_lifecycle import ContainerHandle
from src.dispatcher.tmux_lifecycle import SessionHandle
from src.dispatcher.watchdog import Watchdog


def _proc(stdout: str = "", returncode: int = 0) -> MagicMock:
    p = MagicMock()
    p.stdout = stdout
    p.stderr = ""
    p.returncode = returncode
    return p


class _Clock:
    """Mutable fake clock so individual test points can advance time freely.

    Avoids the ``iter(...)`` exhaustion trap where ``_format_reason`` consumes
    an extra ``time.monotonic()`` call on every HUNG transition.
    """

    def __init__(self, t: float = 0.0) -> None:
        self.t = t

    def now(self) -> float:
        return self.t

    def set(self, t: float) -> None:
        self.t = t


CONTAINER = ContainerHandle(
    id="abc123def456", name="kei211-container", image="img:latest", port=8080
)


@pytest.fixture
def tmux_handle(tmp_path) -> SessionHandle:
    """SessionHandle rooted in the per-test ``tmp_path`` dir.

    The shared ``/tmp`` is rejected by Sonar S5443 (path-traversal vector
    in tests); ``tmp_path`` is the per-test isolated dir pytest creates.
    """
    return SessionHandle(session_name="kei211-test", working_dir=str(tmp_path), command="bash")


class TestWatchdogTmux:
    def test_changing_pane_marks_alive(self, tmux_handle) -> None:
        wd = Watchdog()
        wd.register("s1", tmux_handle, hung_threshold_s=10.0)
        with patch("subprocess.run", side_effect=[_proc("hello\n"), _proc("hello world\n")]):
            assert wd.probe_one("s1") == "alive"
            assert wd.probe_one("s1") == "alive"

    def test_static_pane_past_threshold_is_hung(self, tmux_handle) -> None:
        clock = _Clock(100.0)
        with patch("src.dispatcher.watchdog.time.monotonic", side_effect=clock.now):
            wd = Watchdog()
            wd.register("s1", tmux_handle, hung_threshold_s=10.0)
            with patch("subprocess.run", return_value=_proc("frozen\n")):
                assert wd.probe_one("s1") == "alive"
                clock.set(200.0)
                assert wd.probe_one("s1") == "hung"

    def test_static_pane_under_threshold_stays_alive(self, tmux_handle) -> None:
        clock = _Clock(100.0)
        with patch("src.dispatcher.watchdog.time.monotonic", side_effect=clock.now):
            wd = Watchdog()
            wd.register("s1", tmux_handle, hung_threshold_s=300.0)
            with patch("subprocess.run", return_value=_proc("frozen\n")):
                assert wd.probe_one("s1") == "alive"
                clock.set(200.0)
                assert wd.probe_one("s1") == "alive"

    def test_missing_session_is_dead(self, tmux_handle) -> None:
        wd = Watchdog()
        wd.register("s1", tmux_handle)
        with patch("subprocess.run", return_value=_proc("", returncode=1)):
            assert wd.probe_one("s1") == "dead"

    def test_tmux_missing_is_dead(self, tmux_handle) -> None:
        wd = Watchdog()
        wd.register("s1", tmux_handle)
        with patch("subprocess.run", side_effect=FileNotFoundError("no tmux")):
            assert wd.probe_one("s1") == "dead"

    def test_alert_fires_once_on_hung_transition(self, tmux_handle) -> None:
        alerts: list[tuple[str, str]] = []
        clock = _Clock(100.0)
        with patch("src.dispatcher.watchdog.time.monotonic", side_effect=clock.now):
            wd = Watchdog(alert_fn=lambda k, _e, r: alerts.append((k, r)))
            wd.register("s1", tmux_handle, hung_threshold_s=10.0)
            with patch("subprocess.run", return_value=_proc("frozen\n")):
                wd.probe_one("s1")  # alive
                clock.set(200.0)
                wd.probe_one("s1")  # hung -> alert
                clock.set(300.0)
                wd.probe_one("s1")  # still hung -> no new alert
        assert len(alerts) == 1
        assert alerts[0][0] == "s1"
        assert "tmux" in alerts[0][1]


class TestWatchdogContainer:
    def test_healthy_container_is_alive(self) -> None:
        wd = Watchdog()
        wd.register("c1", CONTAINER, hung_threshold_s=10.0)
        with patch("src.dispatcher.watchdog._probe_http_health", return_value=True):
            assert wd.probe_one("c1") == "alive"

    def test_unhealthy_under_threshold_stays_alive(self) -> None:
        clock = _Clock(100.0)
        with patch("src.dispatcher.watchdog.time.monotonic", side_effect=clock.now):
            wd = Watchdog()
            wd.register("c1", CONTAINER, hung_threshold_s=60.0)
            with patch("src.dispatcher.watchdog._probe_http_health", return_value=False):
                assert wd.probe_one("c1") == "alive"
                clock.set(110.0)
                assert wd.probe_one("c1") == "alive"

    def test_unhealthy_past_threshold_is_hung(self) -> None:
        clock = _Clock(100.0)
        with patch("src.dispatcher.watchdog.time.monotonic", side_effect=clock.now):
            wd = Watchdog()
            wd.register("c1", CONTAINER, hung_threshold_s=10.0)
            with patch("src.dispatcher.watchdog._probe_http_health", return_value=False):
                assert wd.probe_one("c1") == "alive"
                clock.set(200.0)
                assert wd.probe_one("c1") == "hung"

    def test_recovery_resets_unhealthy_window(self) -> None:
        clock = _Clock(100.0)
        probes = iter([False, True, False])
        with patch("src.dispatcher.watchdog.time.monotonic", side_effect=clock.now):
            wd = Watchdog()
            wd.register("c1", CONTAINER, hung_threshold_s=10.0)
            with patch(
                "src.dispatcher.watchdog._probe_http_health",
                side_effect=lambda *_a, **_k: next(probes),
            ):
                assert wd.probe_one("c1") == "alive"  # unhealthy starts window
                clock.set(105.0)
                assert wd.probe_one("c1") == "alive"  # healthy resets
                clock.set(200.0)
                # Without reset this would be HUNG (Δ100 > 10); recovery should keep alive.
                assert wd.probe_one("c1") == "alive"


class TestWatchdogSnapshot:
    def test_empty_is_green(self) -> None:
        wd = Watchdog()
        snap = wd.health_snapshot()
        assert snap["status"] == "green"
        assert snap["tracked"] == 0

    def test_all_alive_is_green(self, tmux_handle) -> None:
        wd = Watchdog()
        wd.register("s1", tmux_handle)
        with patch("subprocess.run", return_value=_proc("ok\n")):
            wd.probe_all()
        assert wd.health_snapshot()["status"] == "green"

    def test_any_hung_is_degraded(self, tmux_handle) -> None:
        clock = _Clock(100.0)
        with patch("src.dispatcher.watchdog.time.monotonic", side_effect=clock.now):
            wd = Watchdog()
            wd.register("s1", tmux_handle, hung_threshold_s=10.0)
            with patch("subprocess.run", return_value=_proc("frozen\n")):
                wd.probe_all()
                clock.set(200.0)
                wd.probe_all()
        snap = wd.health_snapshot()
        assert snap["status"] == "degraded"
        assert snap["hung"] == 1

    def test_probe_all_swallows_exception(self, tmux_handle) -> None:
        wd = Watchdog()
        wd.register("s1", tmux_handle)
        with patch.object(wd, "probe_one", side_effect=RuntimeError("boom")):
            results = wd.probe_all()
        assert results == {"s1": "dead"}


class TestWatchdogRegistry:
    def test_unregister_removes_entry(self, tmux_handle) -> None:
        wd = Watchdog()
        wd.register("s1", tmux_handle)
        assert wd.tracked == 1
        wd.unregister("s1")
        assert wd.tracked == 0

    def test_probe_unknown_key_is_dead(self) -> None:
        assert Watchdog().probe_one("nope") == "dead"

    def test_re_register_resets_progress(self, tmux_handle) -> None:
        wd = Watchdog()
        wd.register("s1", tmux_handle, hung_threshold_s=10.0)
        entry_before = wd._entries["s1"]
        wd.register("s1", tmux_handle, hung_threshold_s=20.0)
        entry_after = wd._entries["s1"]
        # Sonar S1244: avoid float == — use math.isclose for tolerance-safe compare.
        assert math.isclose(entry_after.hung_threshold_s, 20.0, rel_tol=1e-9)
        assert entry_after is not entry_before


@pytest.mark.parametrize("returncode", [1, 2])
def test_tmux_capture_nonzero_returns_none(returncode: int) -> None:
    """Direct unit test on the capture helper."""
    from src.dispatcher.watchdog import _capture_tmux_pane

    with patch("subprocess.run", return_value=_proc("", returncode=returncode)):
        assert _capture_tmux_pane("s") is None


class TestSupervisorSnapshot:
    """KEI-211 composing helper for the dispatcher health endpoint."""

    def test_empty_is_green(self) -> None:
        from src.dispatcher import supervisor_health_snapshot

        snap = supervisor_health_snapshot()
        assert snap == {"status": "green", "components": []}

    def test_both_green(self) -> None:
        from src.dispatcher import supervisor_health_snapshot
        from src.dispatcher.reaper import Reaper

        wd = Watchdog()
        r = Reaper(tmux_name_prefix="kei211-", container_name_prefix="kei211-c-")
        with (
            patch("src.dispatcher.reaper._list_tmux_sessions", return_value=[]),
            patch("src.dispatcher.reaper._list_containers_by_prefix", return_value=[]),
        ):
            r.sweep()
        snap = supervisor_health_snapshot(wd, r)
        assert snap["status"] == "green"
        assert len(snap["components"]) == 2

    def test_one_degraded_marks_overall_degraded(self) -> None:
        from src.dispatcher import supervisor_health_snapshot
        from src.dispatcher.reaper import Reaper

        wd = Watchdog()
        r = Reaper(tmux_name_prefix="kei211-", container_name_prefix="kei211-c-")
        # reaper never swept -> "unknown" -> overall != green
        snap = supervisor_health_snapshot(wd, r)
        assert snap["status"] == "degraded"
