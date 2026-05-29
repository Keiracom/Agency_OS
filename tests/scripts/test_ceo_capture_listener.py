"""Tests for scripts/ceo_capture_listener.py (Agency_OS-yku8, final design).

Final design: Socket Mode → spawn one claude-haiku-4-5 agent per human #ceo
message. No Python content pre-filter, no rate limiter, no buffer. The listener
is a thin bridge; classification + the ceo_memory write are the spawned agent's
job. These tests cover the bridge: event hygiene, the spawn payload (model +
injection-safety), fail-open, and handle_event decisions.

Runs without slack_sdk installed (lazy-imported in main()).

Smoke note: the dispatch smoke ("substantive → write; 'ok' → no write") is an
END-TO-END check of the Haiku agent + classify_and_save (PR #1268) + live Slack
— not runnable hermetically and not the listener's decision. At the listener
level BOTH substantive and 'ok' spawn (no Python filter); the write-vs-exit
distinction is the agent's. test_smoke_* assert the listener-level behaviour.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPT = REPO_ROOT / "scripts" / "ceo_capture_listener.py"


def _load():
    spec = importlib.util.spec_from_file_location("_ceo_capture_listener", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


m = _load()
CEO = m.CEO_CHANNEL


def _event(text, *, bot_id=None, subtype=None, channel=CEO, etype="message"):
    e = {"type": etype, "channel": channel, "text": text}
    if bot_id:
        e["bot_id"] = bot_id
    if subtype:
        e["subtype"] = subtype
    return e


# ─── event hygiene ────────────────────────────────────────────────────────────


def test_human_ceo_message_accepted():
    assert m.is_human_ceo_message(_event("We ratified the multi-tenancy decision.")) is True
    assert m.is_human_ceo_message(_event("ok")) is True  # no content filter — 'ok' still qualifies


def test_bot_subtype_wrongchannel_empty_rejected():
    assert m.is_human_ceo_message(_event("decision", bot_id="B123")) is False
    assert m.is_human_ceo_message(_event("x", subtype="message_changed")) is False
    assert m.is_human_ceo_message(_event("x", channel="C_OTHER")) is False
    assert m.is_human_ceo_message(_event("   ")) is False
    assert m.is_human_ceo_message(_event("x", etype="reaction_added")) is False


# ─── spawn payload ────────────────────────────────────────────────────────────


def test_spawn_request_uses_haiku_model():
    p = m.build_spawn_request("the decision is X")
    assert p["spawn_kwargs"]["model"] == "claude-haiku-4-5"
    assert p["spawn_kwargs"]["env"]["CEO_CAPTURE_MODEL"] == "claude-haiku-4-5"
    assert p["backend"] == m.SPAWN_BACKEND
    assert p["key"].startswith("ceo-capture-")
    assert p["spawn_kwargs"]["callsign"] == "john"


def test_spawn_request_carries_message_in_env_not_command():
    """Injection guard: untrusted message lives in env only; the command references
    it by env-var name and never contains the raw text."""
    nasty = 'ratified"; rm -rf / #'
    p = m.build_spawn_request(nasty)
    sk = p["spawn_kwargs"]
    assert sk["env"]["CEO_CAPTURE_MESSAGE"] == nasty
    assert nasty not in sk["command"]
    assert "rm -rf" not in sk["command"]
    assert "$CEO_CAPTURE_MESSAGE" in sk["command"]  # referenced, not interpolated


# ─── spawn call (fail-open) ───────────────────────────────────────────────────


def test_spawn_true_on_2xx(monkeypatch):
    class _Resp:
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    monkeypatch.setattr(m.urllib.request, "urlopen", lambda *a, **k: _Resp())
    assert m.spawn_capture_agent("decision: X") is True


def test_spawn_fails_open_when_dispatcher_down(monkeypatch):
    def _boom(*a, **k):
        raise m.urllib.error.URLError("connection refused")

    monkeypatch.setattr(m.urllib.request, "urlopen", _boom)
    assert m.spawn_capture_agent("decision: X") is False  # logged, not raised


# ─── handle_event (the deterministic smoke) ───────────────────────────────────


def test_smoke_substantive_message_spawns(monkeypatch):
    captured = {}
    monkeypatch.setattr(m, "spawn_capture_agent", lambda t: captured.update(text=t) or True)
    action = m.handle_event(_event("Decision: we will use Hindsight. Ratified by Dave."))
    assert action == "spawned"
    assert "Hindsight" in captured["text"]


def test_smoke_ok_still_spawns_at_listener_level(monkeypatch):
    """No Python pre-filter: even 'ok' spawns a Haiku agent (which then exits with
    no write — the agent's decision, not the listener's)."""
    calls = []
    monkeypatch.setattr(m, "spawn_capture_agent", lambda t: calls.append(t) or True)
    action = m.handle_event(_event("ok"))
    assert action == "spawned"
    assert calls == ["ok"]


def test_bot_message_does_not_spawn(monkeypatch):
    monkeypatch.setattr(
        m, "spawn_capture_agent", lambda t: (_ for _ in ()).throw(AssertionError("no spawn on bot"))
    )
    assert m.handle_event(_event("Decision: ratified", bot_id="B0B2W7VL7T4")) == "skip"


def test_handle_event_reports_spawn_failure(monkeypatch):
    monkeypatch.setattr(m, "spawn_capture_agent", lambda t: False)
    assert m.handle_event(_event("Decision: real human decision here")) == "spawn_failed"


# ─── direct Slack→task creator (Agency_OS-evbn) ───────────────────────────────


def test_is_task_command_detects_prefix_case_insensitive():
    assert m.is_task_command("TASK: wire the foo") is True
    assert m.is_task_command("  task: lowercase works  ") is True
    assert m.is_task_command("Decision: not a task") is False
    assert m.is_task_command("") is False


def test_extract_task_title_strips_prefix_and_caps():
    assert m.extract_task_title("TASK: fix the typo in README") == "fix the typo in README"
    assert m.extract_task_title("task:   trimmed  ") == "trimmed"
    assert len(m.extract_task_title("TASK: " + "X" * 1000)) == m.TASK_TITLE_MAX_CHARS


def test_task_insert_sql_is_parameterised_and_available():
    # Atlas wire #1283: status MUST be 'available' (fires the kei45 trigger); values bound.
    assert (
        m._TASK_INSERT_SQL
        == "INSERT INTO public.tasks (id, title, status) VALUES (%s, %s, 'available')"
    )


def test_create_task_returns_none_without_dsn(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("RETRIEVAL_EVENTS_DSN", raising=False)
    assert m.create_task_from_message("TASK: do a thing") is None  # fail-open, no crash


def test_create_task_returns_none_on_empty_body(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://x")
    assert m.create_task_from_message("TASK:   ") is None  # no title → no task


def test_handle_event_routes_task_command_to_creator(monkeypatch):
    monkeypatch.setattr(m, "create_task_from_message", lambda t: "ceo-task-123")
    monkeypatch.setattr(
        m,
        "spawn_capture_agent",
        lambda t: (_ for _ in ()).throw(AssertionError("must not spawn a TASK:")),
    )
    assert m.handle_event(_event("TASK: wire the dispatcher health probe")) == "task_created"


def test_handle_event_non_task_still_spawns_capture(monkeypatch):
    monkeypatch.setattr(
        m,
        "create_task_from_message",
        lambda t: (_ for _ in ()).throw(AssertionError("not a TASK:")),
    )
    monkeypatch.setattr(m, "spawn_capture_agent", lambda t: True)
    assert m.handle_event(_event("We have ratified the multi-tenancy decision.")) == "spawned"


def test_handle_event_reports_task_create_failure(monkeypatch):
    monkeypatch.setattr(m, "create_task_from_message", lambda t: None)
    assert m.handle_event(_event("TASK: something")) == "task_create_failed"
