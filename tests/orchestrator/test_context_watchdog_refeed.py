"""Unit tests for the watchdog re-feed (watchdog_reaper) — the 'keep a healthy
agent fed' half. Covers _next_queued_work (inbox brief / bd fallback / none) and
refeed_agent (injects the task, NEVER /clear, returns False when nothing to feed).

The live end-to-end proof (real tmux + real tool_call_log row) lives in
scripts/proof_bar/context_watchdog_refeed_live.sh — these are the fast units.
"""
from __future__ import annotations

import importlib
import json

import pytest

cw = importlib.import_module("scripts.orchestrator.context_watchdog")


@pytest.fixture
def inbox(tmp_path, monkeypatch):
    template = str(tmp_path / "telegram-relay-{callsign}" / "inbox")
    monkeypatch.setattr(cw, "REFEED_INBOX_TEMPLATE", template)
    return template


def _write_dispatch(inbox_template, callsign, payload):
    from pathlib import Path
    d = Path(inbox_template.format(callsign=callsign))
    d.mkdir(parents=True, exist_ok=True)
    f = d / "dispatch_1.json"
    f.write_text(json.dumps(payload))
    return f


def test_next_queued_work_reads_inbox_brief(inbox):
    _write_dispatch(inbox, "wdtest", {"brief": "Resume KEI-9 build", "task_ref": "KEI-9"})
    work = cw._next_queued_work("wdtest")
    assert work is not None
    text, source = work
    assert "Resume KEI-9 build" in text
    assert source.startswith("inbox:")


def test_next_queued_work_bd_fallback_when_inbox_unparseable(inbox, monkeypatch):
    from pathlib import Path
    d = Path(inbox.format(callsign="wdtest"))
    d.mkdir(parents=True, exist_ok=True)
    (d / "broken.json").write_text("{not json")
    monkeypatch.setattr(cw, "_bd_ready_top", lambda c: {"id": "KEI-42", "title": "Do thing"})
    work = cw._next_queued_work("wdtest")
    assert work is not None
    text, source = work
    assert "KEI-42" in text and source == "bd:KEI-42"


def test_next_queued_work_none_when_empty(inbox, monkeypatch):
    monkeypatch.setattr(cw, "_bd_ready_top", lambda c: None)
    assert cw._next_queued_work("wdtest") is None


def test_refeed_agent_injects_task_and_never_clears(inbox, monkeypatch):
    monkeypatch.setattr(cw, "_next_queued_work", lambda c: ("DO THE THING", "inbox:x"))
    monkeypatch.setattr(cw, "wait_for_prompt", lambda *a, **k: True)
    monkeypatch.setattr(cw, "slack_ceo", lambda *a, **k: None)
    sent = []
    monkeypatch.setattr(cw, "safe_send", lambda target, text, **k: sent.append(text) or True)

    assert cw.refeed_agent("nova", "nova:0.0", "nova") is True
    assert len(sent) == 1
    assert "DO THE THING" in sent[0]
    assert cw.REFEED_GUARD.strip()[:20] in sent[0]  # no-spend guard present
    # The whole point: a cleanly-idle agent is RE-FED, never tab-cleared.
    assert "/clear" not in sent[0]


def test_refeed_agent_returns_false_when_no_work(inbox, monkeypatch):
    monkeypatch.setattr(cw, "_next_queued_work", lambda c: None)
    sent = []
    monkeypatch.setattr(cw, "safe_send", lambda *a, **k: sent.append(a) or True)
    assert cw.refeed_agent("nova", "nova:0.0", "nova") is False
    assert sent == []  # nothing injected → no thrash


def test_refeed_agent_returns_false_when_no_prompt(inbox, monkeypatch):
    monkeypatch.setattr(cw, "_next_queued_work", lambda c: ("X", "inbox:x"))
    monkeypatch.setattr(cw, "wait_for_prompt", lambda *a, **k: False)
    sent = []
    monkeypatch.setattr(cw, "safe_send", lambda *a, **k: sent.append(a) or True)
    assert cw.refeed_agent("nova", "nova:0.0", "nova") is False
    assert sent == []  # never force-send to a pane not at ❯
