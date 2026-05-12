"""Tests for scripts/orchestrator/elliot_polling_loop.py — KEI-17.

Each polling source + the dispatcher are mocked at the module level so tests
run without bd, Linear, Prefect, asyncpg, or Slack. The script's contract:
- silent skip when outside peak window AND minute != 0
- silent cycle when zero signals
- one [DISPATCH-PROPOSAL:<callsign>] per (idle agent, bd_ready issue) FIFO pair
- one [PROPOSE:elliot] in #ceo per linear-stale batch
- one [PROPOSE:elliot] in #ceo per prefect-failure batch
"""

from __future__ import annotations

import importlib.util
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import MagicMock

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPT_PATH = REPO_ROOT / "scripts" / "orchestrator" / "elliot_polling_loop.py"


@pytest.fixture(scope="module")
def loop_mod():
    spec = importlib.util.spec_from_file_location("elliot_polling_loop", SCRIPT_PATH)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["elliot_polling_loop"] = mod
    spec.loader.exec_module(mod)
    return mod


# should_run_now ─────────────────────────────────────────────────────────────


def test_should_run_now_peak_hour(loop_mod):
    # 22:30 UTC = 08:30 AEST — peak window, any minute runs
    assert loop_mod.should_run_now(datetime(2026, 5, 12, 22, 30, tzinfo=UTC)) is True


def test_should_run_now_overnight_minute_zero(loop_mod):
    # 15:00 UTC = 01:00 AEST — overnight, minute==0 runs
    assert loop_mod.should_run_now(datetime(2026, 5, 12, 15, 0, tzinfo=UTC)) is True


def test_should_run_now_overnight_other_minute(loop_mod):
    # 15:30 UTC = 01:30 AEST — overnight, minute!=0 skips
    assert loop_mod.should_run_now(datetime(2026, 5, 12, 15, 30, tzinfo=UTC)) is False


# New boundary tests for Dave's KEI-17 schedule amendment ts ~1778584000:
# Peak window AEST 07:00–24:00 (UTC 21:00 prev day → 14:00 today, exclusive).
# Off-peak AEST 00:00–07:00 (UTC 14:00 → 21:00, exclusive).


def test_should_run_now_peak_window_late_boundary(loop_mod):
    # 13:59 UTC = 23:59 AEST — last minute of peak window
    assert loop_mod.should_run_now(datetime(2026, 5, 12, 13, 59, tzinfo=UTC)) is True


def test_should_run_now_off_peak_starts_at_14_utc(loop_mod):
    # 14:00 UTC = 00:00 AEST — first hour of off-peak; minute==0 still fires (hourly)
    assert loop_mod.should_run_now(datetime(2026, 5, 12, 14, 0, tzinfo=UTC)) is True
    # 14:30 UTC = 00:30 AEST — off-peak hour, minute!=0 → skip
    assert loop_mod.should_run_now(datetime(2026, 5, 12, 14, 30, tzinfo=UTC)) is False


def test_should_run_now_off_peak_late_skip(loop_mod):
    # 20:59 UTC = 06:59 AEST — last off-peak hour, minute!=0 → skip
    assert loop_mod.should_run_now(datetime(2026, 5, 12, 20, 59, tzinfo=UTC)) is False


def test_should_run_now_peak_starts_at_21_utc(loop_mod):
    # 21:00 UTC = 07:00 AEST — first hour of peak; any minute runs
    assert loop_mod.should_run_now(datetime(2026, 5, 12, 21, 0, tzinfo=UTC)) is True
    assert loop_mod.should_run_now(datetime(2026, 5, 12, 21, 37, tzinfo=UTC)) is True


# poll_bd_ready ──────────────────────────────────────────────────────────────


def test_poll_bd_ready_success(loop_mod, monkeypatch):
    fake_proc = MagicMock(returncode=0, stdout='[{"id":"X","title":"T","priority":0}]', stderr="")
    monkeypatch.setattr(loop_mod.subprocess, "run", lambda *a, **k: fake_proc)
    out = loop_mod.poll_bd_ready()
    assert out == [{"id": "X", "title": "T", "priority": 0}]


def test_poll_bd_ready_handles_nonzero_exit(loop_mod, monkeypatch):
    fake_proc = MagicMock(returncode=1, stdout="", stderr="bd not initialized")
    monkeypatch.setattr(loop_mod.subprocess, "run", lambda *a, **k: fake_proc)
    assert loop_mod.poll_bd_ready() == []


def test_poll_bd_ready_handles_bad_json(loop_mod, monkeypatch):
    fake_proc = MagicMock(returncode=0, stdout="not-json", stderr="")
    monkeypatch.setattr(loop_mod.subprocess, "run", lambda *a, **k: fake_proc)
    assert loop_mod.poll_bd_ready() == []


# Agency_OS-yvz fix (a): bd invoked via absolute ~/.local/bin/bd path so
# systemd --user services with restricted PATH don't FileNotFoundError.


def test_poll_bd_ready_uses_absolute_bd_path(loop_mod, monkeypatch):
    captured: list[list[str]] = []

    def _capture(cmd, *a, **k):
        captured.append(cmd)
        return MagicMock(returncode=0, stdout="[]", stderr="")

    monkeypatch.setattr(loop_mod.subprocess, "run", _capture)
    loop_mod.poll_bd_ready()
    assert captured, "subprocess.run was not invoked"
    assert captured[0][0].endswith("/.local/bin/bd"), (
        f"expected absolute bd path, got {captured[0][0]!r}"
    )
    assert captured[0][1:] == ["ready", "--json"]


# poll_linear_stale ──────────────────────────────────────────────────────────


def test_poll_linear_stale_no_api_key(loop_mod, monkeypatch):
    monkeypatch.delenv("LINEAR_API_KEY", raising=False)
    assert loop_mod.poll_linear_stale() == []


def test_poll_linear_stale_swallows_url_error(loop_mod, monkeypatch):
    monkeypatch.setenv("LINEAR_API_KEY", "x")
    import urllib.error

    def fake_open(*a, **k):
        raise urllib.error.URLError("nope")

    monkeypatch.setattr(loop_mod.urllib.request, "urlopen", fake_open)
    assert loop_mod.poll_linear_stale() == []


# poll_idle_agents ───────────────────────────────────────────────────────────


def test_poll_idle_agents_no_dsn(loop_mod, monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("DATABASE_URL_MIGRATIONS", raising=False)
    assert loop_mod.poll_idle_agents() == []


# Agency_OS-yvz fix (b): asyncpg.connect must pass statement_cache_size=0 so
# Supabase's pgbouncer (transaction pool) doesn't error on prepared-statement
# re-use across pool checkouts.


def test_poll_idle_agents_passes_statement_cache_size_zero(loop_mod, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@h:5432/d")
    captured_kwargs: list[dict] = []

    pytest.importorskip("asyncpg")  # skip if asyncpg isn't installed on this host

    class _FakeConn:
        async def fetch(self, *a, **k):
            return []

        async def close(self):
            return None

    async def _fake_connect(*args, **kwargs):
        captured_kwargs.append(kwargs)
        return _FakeConn()

    import asyncpg

    monkeypatch.setattr(asyncpg, "connect", _fake_connect)
    out = loop_mod.poll_idle_agents()
    assert out == []
    assert captured_kwargs, "asyncpg.connect was not invoked"
    assert captured_kwargs[0].get("statement_cache_size") == 0, (
        f"expected statement_cache_size=0 for pgbouncer compat, got {captured_kwargs[0]!r}"
    )


# poll_prefect_failures ──────────────────────────────────────────────────────


def test_poll_prefect_failures_no_api_url(loop_mod, monkeypatch):
    monkeypatch.delenv("PREFECT_API_URL", raising=False)
    assert loop_mod.poll_prefect_failures() == []


# compose_dispatches ─────────────────────────────────────────────────────────


def test_compose_dispatches_silent_when_no_signals(loop_mod):
    sig = loop_mod.CycleSignals(bd_ready=[], linear_stale=[], idle_agents=[], prefect_failures=[])
    assert loop_mod.compose_dispatches(sig) == []


def test_compose_dispatches_pairs_idle_with_bd_ready_fifo(loop_mod):
    sig = loop_mod.CycleSignals(
        bd_ready=[
            {"id": "Agency_OS-a", "title": "First", "priority": 0},
            {"id": "Agency_OS-b", "title": "Second", "priority": 1},
        ],
        linear_stale=[],
        idle_agents=["aiden", "max"],
        prefect_failures=[],
    )
    dispatches = loop_mod.compose_dispatches(sig)
    assert len(dispatches) == 2
    chan0, msg0 = dispatches[0]
    chan1, msg1 = dispatches[1]
    assert chan0 == "#execution"
    assert chan1 == "#execution"
    assert "[DISPATCH-PROPOSAL:aiden]" in msg0 and "Agency_OS-a" in msg0 and "First" in msg0
    assert "[DISPATCH-PROPOSAL:max]" in msg1 and "Agency_OS-b" in msg1 and "Second" in msg1


def test_compose_dispatches_pairing_truncates_to_shorter_list(loop_mod):
    sig = loop_mod.CycleSignals(
        bd_ready=[{"id": "Z", "title": "T", "priority": 0}],
        linear_stale=[],
        idle_agents=["aiden", "max"],
        prefect_failures=[],
    )
    dispatches = loop_mod.compose_dispatches(sig)
    # one bd item + two idle agents → one dispatch (FIFO)
    assert len(dispatches) == 1
    assert "[DISPATCH-PROPOSAL:aiden]" in dispatches[0][1]


def test_compose_dispatches_linear_stale_escalates_to_ceo(loop_mod):
    sig = loop_mod.CycleSignals(
        bd_ready=[],
        linear_stale=[
            {
                "identifier": "KEI-99",
                "title": "Stuck",
                "updatedAt": "2026-05-11T00:00:00Z",
                "assignee": {"name": "aiden"},
            },
        ],
        idle_agents=[],
        prefect_failures=[],
    )
    dispatches = loop_mod.compose_dispatches(sig)
    assert len(dispatches) == 1
    chan, msg = dispatches[0]
    assert chan == "#ceo"
    assert "[PROPOSE:elliot]" in msg
    assert "KEI-99" in msg


# Agency_OS-3gy: Linear returns assignee=null on unassigned issues (key
# present, value None). Empirical crash on next polling cycle post the bd
# subprocess + asyncpg fixes (PR #792). Trace: AttributeError 'NoneType'
# object has no attribute 'get' in compose_dispatches.


def test_compose_dispatches_linear_stale_handles_null_assignee(loop_mod):
    """Linear-stale issue with assignee=None (unassigned) must not crash."""
    sig = loop_mod.CycleSignals(
        bd_ready=[],
        linear_stale=[
            {
                "identifier": "KEI-100",
                "title": "Unassigned stuck",
                "updatedAt": "2026-05-11T00:00:00Z",
                "assignee": None,  # ← the empirical Linear shape
            },
        ],
        idle_agents=[],
        prefect_failures=[],
    )
    dispatches = loop_mod.compose_dispatches(sig)
    assert len(dispatches) == 1
    chan, msg = dispatches[0]
    assert chan == "#ceo"
    assert "KEI-100" in msg
    assert "assignee ?" in msg  # default '?' when assignee dict has no name


def test_compose_dispatches_linear_stale_handles_missing_assignee_key(loop_mod):
    """Linear-stale issue with no assignee key at all also must not crash."""
    sig = loop_mod.CycleSignals(
        bd_ready=[],
        linear_stale=[
            {"identifier": "KEI-101", "title": "No assignee key", "updatedAt": "x"},
        ],
        idle_agents=[],
        prefect_failures=[],
    )
    dispatches = loop_mod.compose_dispatches(sig)
    assert len(dispatches) == 1
    assert "KEI-101" in dispatches[0][1]


def test_compose_dispatches_prefect_failures_escalate_to_ceo(loop_mod):
    sig = loop_mod.CycleSignals(
        bd_ready=[],
        linear_stale=[],
        idle_agents=[],
        prefect_failures=[
            {
                "id": "abc12345-deadbeef",
                "state": {"type": "CRASHED"},
                "end_time": "2026-05-12T07:00:00Z",
            },
        ],
    )
    dispatches = loop_mod.compose_dispatches(sig)
    assert len(dispatches) == 1
    chan, msg = dispatches[0]
    assert chan == "#ceo"
    assert "[PROPOSE:elliot]" in msg
    assert "CRASHED" in msg


# run_cycle ──────────────────────────────────────────────────────────────────


def test_run_cycle_silent_skip_outside_peak_minute_nonzero(loop_mod, monkeypatch):
    sent: list = []
    monkeypatch.setattr(loop_mod, "send_dispatch", lambda c, t: sent.append((c, t)))
    monkeypatch.setattr(
        loop_mod,
        "collect_signals",
        lambda now=None: pytest.fail(
            "collect_signals must NOT be called outside peak when minute != 0"
        ),
    )
    n = loop_mod.run_cycle(datetime(2026, 5, 12, 15, 30, tzinfo=UTC))
    assert n == 0
    assert sent == []


def test_run_cycle_silent_when_no_signals(loop_mod, monkeypatch):
    sent: list = []
    monkeypatch.setattr(loop_mod, "send_dispatch", lambda c, t: sent.append((c, t)))
    monkeypatch.setattr(
        loop_mod,
        "collect_signals",
        lambda now=None: loop_mod.CycleSignals(
            bd_ready=[], linear_stale=[], idle_agents=[], prefect_failures=[]
        ),
    )
    n = loop_mod.run_cycle(datetime(2026, 5, 12, 22, 30, tzinfo=UTC))
    assert n == 0
    assert sent == []


def test_run_cycle_dispatches_when_signals_present(loop_mod, monkeypatch):
    sent: list = []
    monkeypatch.setattr(loop_mod, "send_dispatch", lambda c, t: sent.append((c, t)))
    monkeypatch.setattr(
        loop_mod,
        "collect_signals",
        lambda now=None: loop_mod.CycleSignals(
            bd_ready=[{"id": "Z", "title": "T", "priority": 0}],
            linear_stale=[],
            idle_agents=["aiden"],
            prefect_failures=[],
        ),
    )
    n = loop_mod.run_cycle(datetime(2026, 5, 12, 22, 30, tzinfo=UTC))
    assert n == 1
    assert len(sent) == 1
    assert sent[0][0] == "#execution"
    assert "[DISPATCH-PROPOSAL:aiden]" in sent[0][1]


# Polling hole A (Dave directive ts ~1778584800) — clone inbox dispatch ─────


def test_compose_dispatches_clone_targets_inbox_not_execution(loop_mod):
    """Clone callsigns (atlas/orion/scout) get inbox:<cs> target, not #execution.
    Primes (aiden/max) still get #execution."""
    sig = loop_mod.CycleSignals(
        bd_ready=[
            {"id": "A1", "title": "T1", "priority": 0},
            {"id": "A2", "title": "T2", "priority": 0},
            {"id": "A3", "title": "T3", "priority": 0},
        ],
        linear_stale=[],
        idle_agents=["atlas", "aiden", "orion"],
        prefect_failures=[],
    )
    dispatches = loop_mod.compose_dispatches(sig)
    assert len(dispatches) == 3
    targets = [d[0] for d in dispatches]
    assert "inbox:atlas" in targets
    assert "#execution" in targets
    assert "inbox:orion" in targets


def test_send_dispatch_inbox_writes_json_file(loop_mod, monkeypatch, tmp_path):
    """send_dispatch('inbox:atlas', text) writes a JSON dispatch file to the
    monkeypatched inbox path."""
    inbox = tmp_path / "telegram-relay-atlas" / "inbox"
    inbox.mkdir(parents=True)
    monkeypatch.setitem(loop_mod.INBOX_PATHS, "atlas", str(inbox))

    loop_mod.send_dispatch("inbox:atlas", "[DISPATCH-PROPOSAL:atlas] do thing")
    files = list(inbox.iterdir())
    assert len(files) == 1
    import json as _json

    payload = _json.loads(files[0].read_text())
    assert payload["type"] == "task_dispatch"
    assert payload["from"] == "elliot_polling_loop"
    assert "[DISPATCH-PROPOSAL:atlas]" in payload["brief"]


def test_send_dispatch_inbox_missing_dir_drops_quietly(loop_mod, monkeypatch, tmp_path):
    """If the clone's inbox dir doesn't exist (clone offline / pre-watcher),
    drop the dispatch instead of crashing."""
    monkeypatch.setitem(loop_mod.INBOX_PATHS, "atlas", str(tmp_path / "nonexistent"))
    # Should not raise.
    loop_mod.send_dispatch("inbox:atlas", "text")


def test_send_dispatch_unknown_inbox_callsign_drops(loop_mod):
    """inbox:<unmapped> drops quietly (best-effort)."""
    loop_mod.send_dispatch("inbox:unknown_callsign", "text")  # no raise


# Rate-limit detection (Dave P1 directive ts ~1778619750) ────────────────────


def _stub_capture_pane(loop_mod, monkeypatch, output_per_session: dict[str, str]):
    """Patch _capture_pane_tail to return scripted output per session-name."""
    def _fake(session, lines=10):
        return output_per_session.get(session, "")
    monkeypatch.setattr(loop_mod, "_capture_pane_tail", _fake)


def test_poll_rate_limited_clean_to_clean_no_transition(loop_mod, monkeypatch, tmp_path):
    monkeypatch.setenv("AGENCY_OS_THROTTLE_STATE_PATH", str(tmp_path / "state.json"))
    _stub_capture_pane(loop_mod, monkeypatch, {})  # all empty (clean)
    assert loop_mod.poll_rate_limited_agents() == []


def test_poll_rate_limited_clean_to_throttled_emits(loop_mod, monkeypatch, tmp_path):
    state_path = tmp_path / "state.json"
    monkeypatch.setenv("AGENCY_OS_THROTTLE_STATE_PATH", str(state_path))
    _stub_capture_pane(
        loop_mod,
        monkeypatch,
        {"aiden": "Working on PR...\nrate limit reached. retry-after 60\n"},
    )
    out = loop_mod.poll_rate_limited_agents(now=datetime(2026, 5, 12, 22, 0, tzinfo=UTC))
    assert ("aiden", "throttled", 0) in out
    assert state_path.exists()
    state = json.loads(state_path.read_text())
    assert "aiden" in state


def test_poll_rate_limited_throttled_to_throttled_no_emit(loop_mod, monkeypatch, tmp_path):
    state_path = tmp_path / "state.json"
    monkeypatch.setenv("AGENCY_OS_THROTTLE_STATE_PATH", str(state_path))
    state_path.write_text(json.dumps({"aiden": "2026-05-12T22:00:00+00:00"}))
    _stub_capture_pane(
        loop_mod,
        monkeypatch,
        {"aiden": "still rate limit-ed, brewed for 30 more seconds"},
    )
    out = loop_mod.poll_rate_limited_agents(now=datetime(2026, 5, 12, 22, 5, tzinfo=UTC))
    assert out == []


def test_poll_rate_limited_throttled_to_clean_emits_resumed(loop_mod, monkeypatch, tmp_path):
    state_path = tmp_path / "state.json"
    monkeypatch.setenv("AGENCY_OS_THROTTLE_STATE_PATH", str(state_path))
    state_path.write_text(json.dumps({"aiden": "2026-05-12T22:00:00+00:00"}))
    _stub_capture_pane(loop_mod, monkeypatch, {})  # clean now
    out = loop_mod.poll_rate_limited_agents(now=datetime(2026, 5, 12, 22, 15, tzinfo=UTC))
    # Resumed event for aiden with 15-min duration
    assert any(t for t in out if t[0] == "aiden" and t[1] == "resumed" and t[2] == 15)
    state = json.loads(state_path.read_text())
    assert "aiden" not in state


def test_poll_rate_limited_pattern_429_matches(loop_mod, monkeypatch, tmp_path):
    monkeypatch.setenv("AGENCY_OS_THROTTLE_STATE_PATH", str(tmp_path / "state.json"))
    _stub_capture_pane(loop_mod, monkeypatch, {"orion": "HTTP 429 Too Many Requests"})
    out = loop_mod.poll_rate_limited_agents()
    assert any(t[0] == "orion" and t[1] == "throttled" for t in out)


def test_compose_dispatches_throttle_transitions_to_ceo(loop_mod):
    sig = loop_mod.CycleSignals(
        bd_ready=[],
        linear_stale=[],
        idle_agents=[],
        prefect_failures=[],
        rate_limit_transitions=[
            ("aiden", "throttled", 0),
            ("orion", "resumed", 12),
        ],
    )
    dispatches = loop_mod.compose_dispatches(sig)
    # Two #ceo dispatches: one throttled-list, one resumed-list.
    ceo_msgs = [m for chan, m in dispatches if chan == "#ceo"]
    assert len(ceo_msgs) == 2
    throttled_msg = next(m for m in ceo_msgs if "throttle detected" in m)
    assert "aiden" in throttled_msg
    resumed_msg = next(m for m in ceo_msgs if "throttle cleared" in m)
    assert "orion resumed after 12m" in resumed_msg
