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
