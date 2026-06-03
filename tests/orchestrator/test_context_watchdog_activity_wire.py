"""Tests for the agent_activity wire-up in context_watchdog
(nova-agent-activity-watchdog-wire).

Covers:
  - Flap-guard window math (load / record / threshold)
  - check_other_agents per-state dispatch (active / idle_with_work_queued /
    idle / no_data) including flap suppression
  - Negative path: idle + no inbox → NO wake (no-thrash invariant)
  - Negative path: flap-tripped agent → NO wake + #ceo slack post

Pattern mirrors test_context_watchdog.py: monkeypatch side-effecting seams
(pane_capture, send_pane, slack_ceo, revive_agent, compute_activity_state) so
no real tmux / DB / Slack is reached.
"""

from __future__ import annotations

import importlib

import pytest


@pytest.fixture
def cw(tmp_path, monkeypatch):
    """Fresh context_watchdog import with flap-state files routed into tmp_path.

    Per-test isolation: each test gets its own tmp dir for flap state files so
    the global /tmp/watchdog-flap-*.json files (production state) are not
    touched. Also prevents flap events bleeding between tests via the file
    system."""
    mod = importlib.import_module("scripts.orchestrator.context_watchdog")
    mod = importlib.reload(mod)
    # Reroute flap state files into tmp_path.
    template = str(tmp_path / "watchdog-flap-{name}.json")
    monkeypatch.setattr(mod, "FLAP_STATE_PATH_TEMPLATE", template)
    return mod


# ---------------------------------------------------------------------------
# Flap-guard primitives
# ---------------------------------------------------------------------------


def test_flap_load_empty_when_no_file(cw):
    assert cw.load_flap_events("ghost", now=1000.0) == []


def test_flap_record_appends_event(cw):
    cw.record_flap_event("nova", now=1000.0)
    cw.record_flap_event("nova", now=1100.0)
    events = cw.load_flap_events("nova", now=1200.0)
    assert events == [1000.0, 1100.0]


def test_flap_load_drops_events_outside_window(cw):
    # Three events: two inside the window (relative to now=10_000), one outside.
    cw.record_flap_event("nova", now=1000.0)  # inside
    cw.record_flap_event("nova", now=2000.0)  # inside
    cw.record_flap_event("nova", now=5000.0)  # outside (5000 + 1800 < 10000)
    now = 10_000.0  # FLAP_WINDOW_SEC default = 1800
    events = cw.load_flap_events("nova", now=now)
    # All events older than 10000 - 1800 = 8200 are dropped → all three drop.
    assert events == []
    # Recent events stay.
    cw.record_flap_event("nova", now=9500.0)
    assert cw.load_flap_events("nova", now=now) == [9500.0]


def test_flap_tripped_at_threshold(cw):
    """Threshold is inclusive (>=): 3 wakes in the window arms the guard;
    the 4th wake attempt is the one suppressed by is_flap_tripped."""
    now = 1000.0
    assert not cw.is_flap_tripped("nova", now)
    cw.record_flap_event("nova", now)
    assert not cw.is_flap_tripped("nova", now)
    cw.record_flap_event("nova", now)
    assert not cw.is_flap_tripped("nova", now)
    cw.record_flap_event("nova", now)
    # Third event in the window → tripped.
    assert cw.is_flap_tripped("nova", now)


def test_flap_state_file_corruption_falls_back_to_empty(cw, tmp_path):
    bad = tmp_path / "watchdog-flap-nova.json"
    bad.write_text("{not json")
    assert cw.load_flap_events("nova", now=1000.0) == []


# ---------------------------------------------------------------------------
# check_other_agents wire-up — per-state dispatch
# ---------------------------------------------------------------------------


def _install_seams(cw, monkeypatch, *, activity_state: str, pane: str = "idle ❯") -> dict:
    """Stub the pane + activity-state seams. Returns a dict where the test
    can observe whether revive_agent was called and the args it received."""
    calls: dict = {"revives": [], "slack": []}

    monkeypatch.setattr(cw, "pane_capture", lambda _t: pane)
    monkeypatch.setattr(cw, "_try_classify_activity", lambda _name: activity_state)
    monkeypatch.setattr(cw, "is_context_full", lambda _p: False)
    monkeypatch.setattr(cw, "is_genuinely_stuck", lambda _p: False)
    monkeypatch.setattr(cw, "is_permission_prompt", lambda _p: False)

    def _record_revive(name, target, reason, last_task=""):  # noqa: ANN001
        calls["revives"].append({"name": name, "reason": reason, "last_task": last_task})

    monkeypatch.setattr(cw, "revive_agent", _record_revive)
    monkeypatch.setattr(cw, "slack_ceo", lambda msg: calls["slack"].append(msg))
    # Restrict the agent set so one assertion = one agent.
    monkeypatch.setattr(cw, "AGENTS", {"nova": "nova:0.0"})
    return calls


def test_idle_with_work_queued_triggers_revive(cw, monkeypatch):
    calls = _install_seams(cw, monkeypatch, activity_state="idle_with_work_queued")
    cw.check_other_agents({})
    assert len(calls["revives"]) == 1
    assert calls["revives"][0]["name"] == "nova"
    assert calls["revives"][0]["reason"] == "idle_with_work_queued"


def test_idle_no_inbox_does_NOT_revive(cw, monkeypatch):
    """No-thrash invariant: pure idle (no inbox) MUST be left untouched. This
    is the negative path the dispatch's proof gate requires."""
    calls = _install_seams(cw, monkeypatch, activity_state="idle")
    cw.check_other_agents({})
    assert calls["revives"] == []


def test_active_does_NOT_revive(cw, monkeypatch):
    calls = _install_seams(cw, monkeypatch, activity_state="active")
    cw.check_other_agents({})
    assert calls["revives"] == []


def test_no_data_does_NOT_revive(cw, monkeypatch):
    """no_data is the pane-based safety-net fall-through. With genuine_stuck=
    False and context_full=False (set by _install_seams), no_data → no action
    here. The existing pane branches (tested in test_context_watchdog.py) own
    the no_data failure modes."""
    calls = _install_seams(cw, monkeypatch, activity_state="no_data")
    cw.check_other_agents({})
    assert calls["revives"] == []


def test_flap_tripped_suppresses_revive_and_posts_slack(cw, monkeypatch):
    """3 prior wake events in the window → next idle_with_work_queued call
    must NOT revive AND must post a single #ceo flap alert."""
    # Seed three flap events at a known time within the window.
    now = 5000.0
    monkeypatch.setattr("time.time", lambda: now)
    cw.record_flap_event("nova", now - 100)
    cw.record_flap_event("nova", now - 200)
    cw.record_flap_event("nova", now - 300)
    assert cw.is_flap_tripped("nova", now)

    calls = _install_seams(cw, monkeypatch, activity_state="idle_with_work_queued")
    state = cw.check_other_agents({})

    assert calls["revives"] == []
    assert len(calls["slack"]) == 1
    assert "FLAP" in calls["slack"][0]
    assert "nova" in calls["slack"][0]
    # Cooldown timestamp recorded for slack-spam suppression.
    assert state.get("nova_flap_alerted_at") == now


def test_flap_slack_alert_obeys_escalation_cooldown(cw, monkeypatch):
    """Two flap-tripped cycles inside ESCALATION_COOLDOWN_SEC → only one
    slack_ceo post (the second cycle silently suppresses)."""
    now = 5000.0
    monkeypatch.setattr("time.time", lambda: now)
    cw.record_flap_event("nova", now - 100)
    cw.record_flap_event("nova", now - 200)
    cw.record_flap_event("nova", now - 300)

    calls = _install_seams(cw, monkeypatch, activity_state="idle_with_work_queued")
    # First cycle — slack posted, cooldown stamped.
    state = cw.check_other_agents({})
    assert len(calls["slack"]) == 1
    # Second cycle immediately after — slack NOT posted (cooldown active).
    cw.check_other_agents(state)
    assert len(calls["slack"]) == 1  # unchanged


def test_revive_records_flap_event(cw, monkeypatch):
    """A successful idle_with_work_queued revive must record a flap event so
    the threshold can be reached on subsequent cycles."""
    now = 5000.0
    monkeypatch.setattr("time.time", lambda: now)
    calls = _install_seams(cw, monkeypatch, activity_state="idle_with_work_queued")
    cw.check_other_agents({})
    assert len(calls["revives"]) == 1
    events = cw.load_flap_events("nova", now)
    assert len(events) == 1
    assert events[0] == pytest.approx(now)


# ---------------------------------------------------------------------------
# Existing pane-based branches still win over activity-state
# ---------------------------------------------------------------------------


def test_context_full_still_takes_precedence(cw, monkeypatch):
    """is_context_full=True must trigger revive(context-full) regardless of
    activity_state — the structural pane signal is authoritative for the
    'dead agent needs /clear' case (per check_other_agents header comment)."""
    calls = {"revives": []}
    monkeypatch.setattr(cw, "pane_capture", lambda _t: "100% context used")
    monkeypatch.setattr(cw, "is_context_full", lambda _p: True)
    monkeypatch.setattr(cw, "is_permission_prompt", lambda _p: False)
    monkeypatch.setattr(cw, "is_genuinely_stuck", lambda _p: False)
    monkeypatch.setattr(
        cw,
        "_try_classify_activity",
        lambda _n: "active",  # would normally skip
    )
    monkeypatch.setattr(
        cw,
        "revive_agent",
        lambda name, target, reason, last_task="": calls["revives"].append(
            {"name": name, "reason": reason}
        ),
    )
    monkeypatch.setattr(cw, "AGENTS", {"nova": "nova:0.0"})

    cw.check_other_agents({})
    assert len(calls["revives"]) == 1
    assert calls["revives"][0]["reason"] == "context-full"


# ---------------------------------------------------------------------------
# _try_classify_activity fail-open
# ---------------------------------------------------------------------------


def test_try_classify_returns_no_data_on_import_error(cw, monkeypatch):
    """If the helper module / function cannot be reached, the wrapper must
    return 'no_data' so the watchdog falls through to its pane-based safety
    net rather than crashing the cycle."""
    import builtins

    real_import = builtins.__import__

    def _blow_up_on_agent_activity(name, *args, **kwargs):
        if name == "scripts.orchestrator.agent_activity":
            raise ImportError("simulated missing helper")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", _blow_up_on_agent_activity)
    assert cw._try_classify_activity("nova") == "no_data"


def test_try_classify_returns_no_data_on_helper_exception(cw, monkeypatch):
    import scripts.orchestrator.agent_activity as aa

    def _boom(_callsign):
        raise RuntimeError("DB exploded")

    monkeypatch.setattr(aa, "compute_activity_state", _boom)
    assert cw._try_classify_activity("nova") == "no_data"


# ---------------------------------------------------------------------------
# Pane-name → DB-callsign mapping (Max-specific; caught by live proof run)
# ---------------------------------------------------------------------------


def test_db_callsign_maps_maxbot_to_max(cw):
    """tmux session name 'maxbot' must map to DB callsign 'max'. Verified live
    against tool_call_log: 2824 rows under 'max', 0 under 'maxbot'. Without
    this mapping Max would silently skip auto-wake forever."""
    assert cw._db_callsign("maxbot") == "max"


def test_db_callsign_passes_through_other_agents(cw):
    for name in ("atlas", "orion", "aiden", "scout", "nova", "elliot"):
        assert cw._db_callsign(name) == name


def test_try_classify_uses_mapped_callsign(cw, monkeypatch):
    """compute_activity_state must be called with the mapped DB callsign, not
    the raw pane name."""
    import scripts.orchestrator.agent_activity as aa

    seen: list[str] = []

    def _spy(callsign):
        seen.append(callsign)
        return "active"

    monkeypatch.setattr(aa, "compute_activity_state", _spy)
    cw._try_classify_activity("maxbot")
    assert seen == ["max"]
