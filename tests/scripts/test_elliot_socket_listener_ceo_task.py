"""Tests for the #ceo TASK: wiring in scripts/elliot_socket_listener.py (evbn).

A human 'TASK:'-prefixed message in #ceo must call
ceo_capture_listener.create_task_from_message() (insert a public.tasks row) and
must NOT also be inboxed (it is a command, not a message for Elliot). Everything
else must keep its existing inbox behavior. Bot posts and non-#ceo channels must
NOT create tasks.

create_task_from_message + write_inbox are monkeypatched — no live DB/Slack.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPT = REPO_ROOT / "scripts" / "elliot_socket_listener.py"
EXEC_CHANNEL = "C0B3QB0K1GQ"  # #execution (in the allowlist, not #ceo)


def _boom(*_a, **_k):
    raise AssertionError("must not be called")


@pytest.fixture(scope="module")
def E():
    spec = importlib.util.spec_from_file_location("_elliot_socket_listener", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _event(text, *, channel, bot_id=None):
    e = {"type": "message", "channel": channel, "text": text}
    if bot_id:
        e["bot_id"] = bot_id
    return e


def test_human_ceo_task_creates_task_and_is_not_inboxed(E, monkeypatch):
    created = []
    monkeypatch.setattr(E.ceo_capture_listener, "create_task_from_message", lambda t: created.append(t) or "ceo-task-1")
    monkeypatch.setattr(E, "write_inbox", _boom)
    E.process_event(_event("TASK: wire the dispatcher probe", channel=E.ceo_capture_listener.CEO_CHANNEL))
    assert created == ["TASK: wire the dispatcher probe"]


def test_ceo_non_task_still_inboxed_and_no_task(E, monkeypatch):
    inboxed = []
    monkeypatch.setattr(E, "write_inbox", lambda text, sender: inboxed.append(text))
    monkeypatch.setattr(E.ceo_capture_listener, "create_task_from_message", _boom)
    E.process_event(_event("elliot please review the plan", channel=E.ceo_capture_listener.CEO_CHANNEL))
    assert inboxed == ["elliot please review the plan"]


def test_task_prefix_in_non_ceo_channel_does_not_create_task(E, monkeypatch):
    monkeypatch.setattr(E.ceo_capture_listener, "create_task_from_message", _boom)
    inboxed = []
    monkeypatch.setattr(E, "write_inbox", lambda text, sender: inboxed.append(text))
    E.process_event(_event("TASK: do x outside ceo", channel=EXEC_CHANNEL))
    assert inboxed == ["TASK: do x outside ceo"]  # treated as a normal message


def test_bot_task_in_ceo_does_not_create_task(E, monkeypatch):
    monkeypatch.setattr(E.ceo_capture_listener, "create_task_from_message", _boom)
    monkeypatch.setattr(E, "write_inbox", _boom)  # bot non-trigger msg is dropped by should_keep
    E.process_event(_event("TASK: from a fleet bot", channel=E.ceo_capture_listener.CEO_CHANNEL, bot_id="B123"))


def test_ceo_task_create_failure_is_non_fatal_and_not_inboxed(E, monkeypatch):
    monkeypatch.setattr(E.ceo_capture_listener, "create_task_from_message", lambda t: None)
    monkeypatch.setattr(E, "write_inbox", _boom)
    E.process_event(_event("TASK: db is down", channel=E.ceo_capture_listener.CEO_CHANNEL))  # no raise
