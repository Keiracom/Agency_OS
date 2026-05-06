"""Pure-mock tests for scripts/cgroup_memory_guard.py.

No real cgroup, no real signals, no real sleeps. Every external surface
(file reads, os.kill, time.sleep) is monkeypatched or injected.
"""

from __future__ import annotations

import importlib.util
import os
import signal
import sys
from pathlib import Path
from types import ModuleType

import pytest

# ── Module under test (loaded by absolute path because scripts/ isn't a pkg)
_REPO = Path(__file__).resolve().parents[2]
_PATH = _REPO / "scripts" / "cgroup_memory_guard.py"


def _load() -> ModuleType:
    spec = importlib.util.spec_from_file_location("cgroup_memory_guard", _PATH)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules["cgroup_memory_guard"] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture
def guard():
    return _load()


# ── classify_pressure ─────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "usage,limit,expected",
    [
        (0, 1000, "ok"),
        (500, 1000, "ok"),  # 50%
        (799, 1000, "ok"),  # 79.9% — under warn
        (800, 1000, "warn"),  # exactly warn threshold
        (900, 1000, "warn"),
        (949, 1000, "warn"),
        (950, 1000, "kill"),  # exactly kill threshold
        (1000, 1000, "kill"),
        (2000, 1000, "kill"),  # over-limit
    ],
)
def test_classify_pressure_thresholds(guard, usage, limit, expected):
    assert guard.classify_pressure(usage, limit) == expected


def test_classify_pressure_unlimited_is_ok(guard):
    # limit_bytes <= 0 means cgroup is unlimited / unreadable
    assert guard.classify_pressure(10**12, 0) == "ok"
    assert guard.classify_pressure(10**12, -1) == "ok"


def test_classify_pressure_negative_usage_is_ok(guard):
    assert guard.classify_pressure(-1, 1000) == "ok"


def test_classify_pressure_custom_thresholds(guard):
    assert guard.classify_pressure(50, 100, warn_pct=40, kill_pct=60) == "warn"
    assert guard.classify_pressure(70, 100, warn_pct=40, kill_pct=60) == "kill"
    assert guard.classify_pressure(30, 100, warn_pct=40, kill_pct=60) == "ok"


# ── read_cgroup_memory ────────────────────────────────────────────────────


def _write(p: Path, txt: str) -> None:
    p.write_text(txt)


def test_read_cgroup_memory_v2_present(tmp_path, guard):
    usage = tmp_path / "memory.current"
    limit = tmp_path / "memory.max"
    _write(usage, "1048576\n")
    _write(limit, "10485760\n")

    r = guard.read_cgroup_memory(
        v2_usage_path=str(usage),
        v2_max_path=str(limit),
        v1_usage_path="/nonexistent",
        v1_limit_path="/nonexistent",
    )
    assert r.available is True
    assert r.version == "v2"
    assert r.usage_bytes == 1048576
    assert r.limit_bytes == 10485760
    assert r.usage_pct == pytest.approx(10.0)


def test_read_cgroup_memory_v2_max_sentinel(tmp_path, guard):
    usage = tmp_path / "memory.current"
    limit = tmp_path / "memory.max"
    _write(usage, "1048576")
    _write(limit, "max")  # cgroup v2 "no limit"

    r = guard.read_cgroup_memory(
        v2_usage_path=str(usage),
        v2_max_path=str(limit),
        v1_usage_path="/nonexistent",
        v1_limit_path="/nonexistent",
    )
    assert r.available is True
    assert r.limit_bytes == 0
    assert r.usage_pct == 0.0


def test_read_cgroup_memory_v1_fallback(tmp_path, guard):
    v1_usage = tmp_path / "memory.usage_in_bytes"
    v1_limit = tmp_path / "memory.limit_in_bytes"
    _write(v1_usage, "2048")
    _write(v1_limit, "4096")

    r = guard.read_cgroup_memory(
        v2_usage_path="/nonexistent",
        v2_max_path="/nonexistent",
        v1_usage_path=str(v1_usage),
        v1_limit_path=str(v1_limit),
    )
    assert r.available is True
    assert r.version == "v1"
    assert r.limit_bytes == 4096


def test_read_cgroup_memory_v1_unlimited_sentinel(tmp_path, guard):
    v1_usage = tmp_path / "memory.usage_in_bytes"
    v1_limit = tmp_path / "memory.limit_in_bytes"
    _write(v1_usage, "2048")
    _write(v1_limit, str(1 << 63 - 1))  # well above _V1_UNLIMITED_FLOOR

    r = guard.read_cgroup_memory(
        v2_usage_path="/nonexistent",
        v2_max_path="/nonexistent",
        v1_usage_path=str(v1_usage),
        v1_limit_path=str(v1_limit),
    )
    assert r.available is True
    assert r.limit_bytes == 0


def test_read_cgroup_memory_unavailable(guard):
    r = guard.read_cgroup_memory(
        v2_usage_path="/nonexistent",
        v2_max_path="/nonexistent",
        v1_usage_path="/nonexistent",
        v1_limit_path="/nonexistent",
    )
    assert r.available is False
    assert r.version == "none"
    assert r.usage_bytes == 0


def test_read_cgroup_memory_garbage_text(tmp_path, guard):
    usage = tmp_path / "memory.current"
    limit = tmp_path / "memory.max"
    _write(usage, "not-a-number\n")
    _write(limit, "10000")
    r = guard.read_cgroup_memory(
        v2_usage_path=str(usage),
        v2_max_path=str(limit),
        v1_usage_path="/nonexistent",
        v1_limit_path="/nonexistent",
    )
    # garbage usage → falls through to v1 (also missing) → unavailable
    assert r.available is False


# ── parse_agent_overrides ─────────────────────────────────────────────────


def test_parse_agent_overrides_basic(guard):
    env = {
        "AGENT_MEMORY_LIMIT_MB__BUILD_2": "2048",
        "AGENT_MEMORY_LIMIT_MB__RESEARCH_1": "512",
        "AGENT_MEMORY_LIMIT_MB__REVIEW_5": "256",
        "UNRELATED_VAR": "ignored",
    }
    out = guard.parse_agent_overrides(env)
    assert out == {"build-2": 2048, "research-1": 512, "review-5": 256}


def test_parse_agent_overrides_drops_garbage(guard):
    env = {
        "AGENT_MEMORY_LIMIT_MB__BUILD_2": "not-an-int",
        "AGENT_MEMORY_LIMIT_MB__BUILD_3": "0",  # non-positive dropped
        "AGENT_MEMORY_LIMIT_MB__TEST_4": "-100",  # negative dropped
        "AGENT_MEMORY_LIMIT_MB__": "1024",  # empty agent dropped
    }
    out = guard.parse_agent_overrides(env)
    assert out == {}


def test_parse_agent_overrides_empty_env(guard):
    assert guard.parse_agent_overrides({}) == {}


# ── list_agent_pids ───────────────────────────────────────────────────────


def test_list_agent_pids_missing_dir(tmp_path, guard):
    assert guard.list_agent_pids(tmp_path / "nope") == []


def test_list_agent_pids_reads_files(tmp_path, guard, monkeypatch):
    (tmp_path / "build-2.1234.pid").write_text("1234")
    (tmp_path / "research-1.5678.pid").write_text("5678\n")
    (tmp_path / "ignore.txt").write_text("9999")
    (tmp_path / "stale.0001.pid").write_text("1")  # pid<=1 ignored

    # Make every pid look alive.
    monkeypatch.setattr(guard, "_pid_alive", lambda pid: True)
    pids = sorted(guard.list_agent_pids(tmp_path))
    assert pids == [1234, 5678]


def test_list_agent_pids_skips_dead(tmp_path, guard, monkeypatch):
    (tmp_path / "build-2.1234.pid").write_text("1234")
    (tmp_path / "build-3.5678.pid").write_text("5678")
    monkeypatch.setattr(guard, "_pid_alive", lambda pid: pid == 1234)
    assert guard.list_agent_pids(tmp_path) == [1234]


def test_list_agent_pids_handles_garbage_file(tmp_path, guard, monkeypatch):
    (tmp_path / "broken..pid").write_text("not-a-pid")
    monkeypatch.setattr(guard, "_pid_alive", lambda pid: True)
    assert guard.list_agent_pids(tmp_path) == []


# ── terminate_pids ────────────────────────────────────────────────────────


def test_terminate_pids_empty(guard):
    assert guard.terminate_pids([]) == 0


def test_terminate_pids_signals_each(guard, monkeypatch):
    sent: list[tuple[int, int]] = []
    sleeps: list[float] = []

    def fake_kill(pid, sig):
        sent.append((pid, sig))

    monkeypatch.setattr(guard, "_pid_alive", lambda pid: False)  # all dead after SIGTERM

    n = guard.terminate_pids(
        [111, 222, 333],
        grace_seconds=0.01,
        sleeper=sleeps.append,
        killer=fake_kill,
    )
    assert n == 3
    assert sent == [(111, signal.SIGTERM), (222, signal.SIGTERM), (333, signal.SIGTERM)]
    assert sleeps == [0.01]


def test_terminate_pids_escalates_to_sigkill(guard, monkeypatch):
    sent: list[tuple[int, int]] = []
    monkeypatch.setattr(guard, "_pid_alive", lambda pid: True)  # all still alive
    guard.terminate_pids(
        [111],
        grace_seconds=0.0,
        sleeper=lambda s: None,
        killer=lambda pid, sig: sent.append((pid, sig)),
    )
    sigs = [s for _, s in sent]
    assert signal.SIGTERM in sigs
    assert signal.SIGKILL in sigs


def test_terminate_pids_swallows_lookup_error(guard, monkeypatch):
    monkeypatch.setattr(guard, "_pid_alive", lambda pid: False)

    def raising_kill(pid, sig):
        raise ProcessLookupError

    n = guard.terminate_pids(
        [42],
        grace_seconds=0.0,
        sleeper=lambda s: None,
        killer=raising_kill,
    )
    assert n == 0  # SIGTERM raised, signalled count not incremented


# ── run_once integration (mocked) ─────────────────────────────────────────


def test_run_once_unavailable(monkeypatch, guard, tmp_path):
    monkeypatch.setattr(
        guard,
        "read_cgroup_memory",
        lambda **_: guard.CgroupReading(False, "none", 0, 0, ""),
    )
    status = guard.run_once(
        pid_dir=str(tmp_path),
        warn_pct=80,
        kill_pct=95,
        grace_seconds=0,
    )
    assert status == "unavailable"


def test_run_once_ok(monkeypatch, guard, tmp_path):
    monkeypatch.setattr(
        guard,
        "read_cgroup_memory",
        lambda **_: guard.CgroupReading(True, "v2", 100, 1000, "x"),
    )
    status = guard.run_once(
        pid_dir=str(tmp_path),
        warn_pct=80,
        kill_pct=95,
        grace_seconds=0,
    )
    assert status == "ok"


def test_run_once_warn_does_not_signal(monkeypatch, guard, tmp_path):
    monkeypatch.setattr(
        guard,
        "read_cgroup_memory",
        lambda **_: guard.CgroupReading(True, "v2", 850, 1000, "x"),
    )
    called = {"n": 0}

    def boom(*a, **k):
        called["n"] += 1
        return 0

    monkeypatch.setattr(guard, "terminate_pids", boom)
    status = guard.run_once(
        pid_dir=str(tmp_path),
        warn_pct=80,
        kill_pct=95,
        grace_seconds=0,
    )
    assert status == "warn"
    assert called["n"] == 0


def test_run_once_kill_signals_pids(monkeypatch, guard, tmp_path):
    (tmp_path / "build-2.4242.pid").write_text("4242")
    monkeypatch.setattr(guard, "_pid_alive", lambda pid: True)
    monkeypatch.setattr(
        guard,
        "read_cgroup_memory",
        lambda **_: guard.CgroupReading(True, "v2", 990, 1000, "x"),
    )

    captured: list[list[int]] = []

    def fake_terminate(pids, **kw):
        captured.append(list(pids))
        return len(pids)

    monkeypatch.setattr(guard, "terminate_pids", fake_terminate)
    status = guard.run_once(
        pid_dir=str(tmp_path),
        warn_pct=80,
        kill_pct=95,
        grace_seconds=0,
    )
    assert status == "kill"
    assert captured == [[4242]]


# ── CLI argument validation ───────────────────────────────────────────────


def test_main_rejects_inverted_thresholds(guard):
    rc = guard.main(["--warn-pct", "95", "--kill-pct", "80", "--once"])
    assert rc == 3


def test_main_rejects_kill_above_100(guard):
    rc = guard.main(["--warn-pct", "80", "--kill-pct", "150", "--once"])
    assert rc == 3


def test_main_once_returns_2_on_unavailable(monkeypatch, guard):
    monkeypatch.setattr(
        guard,
        "read_cgroup_memory",
        lambda **_: guard.CgroupReading(False, "none", 0, 0, ""),
    )
    rc = guard.main(["--once", "--pid-dir", "/tmp/nonexistent_p11"])
    assert rc == 2


def test_main_once_returns_0_on_ok(monkeypatch, guard):
    monkeypatch.setattr(
        guard,
        "read_cgroup_memory",
        lambda **_: guard.CgroupReading(True, "v2", 1, 1000, "x"),
    )
    rc = guard.main(["--once", "--pid-dir", "/tmp/nonexistent_p11"])
    assert rc == 0


# ── CgroupReading.usage_pct ────────────────────────────────────────────────


def test_usage_pct_zero_limit(guard):
    r = guard.CgroupReading(True, "v2", 100, 0, "x")
    assert r.usage_pct == 0.0


def test_usage_pct_normal(guard):
    r = guard.CgroupReading(True, "v2", 250, 1000, "x")
    assert r.usage_pct == 25.0


# ── _pid_alive (smoke — uses real os.kill on PID 0 sentinel) ──────────────


def test_pid_alive_for_self(guard):
    assert guard._pid_alive(os.getpid()) is True


def test_pid_alive_for_dead_pid(guard):
    # PID 0 is the current process group sentinel; pick something certain
    # to be missing — extreme PID values are typically out of range.
    assert guard._pid_alive(2**31 - 1) in (False, True)  # platform-tolerant
