"""Tests for scripts/dead_letter_notifier.py (Agency_OS-gl3v).

Covers the pure notification logic — row→DeadLetterTask mapping (incl. graceful
degradation when the consumer hasn't captured retry/error yet), the #ceo message
format, post fail-open, and the dedup (each dead-letter fires exactly once). The
live DB poll is injected, so these run without psycopg / a database.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPT = REPO_ROOT / "scripts" / "dead_letter_notifier.py"


def _load():
    spec = importlib.util.spec_from_file_location("_dead_letter_notifier", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    import sys

    sys.modules[spec.name] = mod  # @dataclass annotation resolution
    spec.loader.exec_module(mod)
    return mod


m = _load()


# ─── poll cadence (< 60s SLA) ─────────────────────────────────────────────────


def test_poll_under_60s():
    assert m.POLL_SECONDS < 60  # the dispatch's "within 60s" guarantee


# ─── row → DeadLetterTask ─────────────────────────────────────────────────────


def test_row_to_dead_letter_full_row():
    dlt = m.row_to_dead_letter(
        {"id": "ceo-task-7", "title": "wire the health probe", m.RETRY_COL: 3, m.ERROR_COL: "boom"}
    )
    assert dlt.task_id == "ceo-task-7"
    assert dlt.description == "wire the health probe"
    assert dlt.retry_count == 3
    assert dlt.final_error == "boom"


def test_row_to_dead_letter_degrades_when_retry_error_absent():
    # confirmed #1283 schema has no retry_count/last_error yet → absent → None/empty
    dlt = m.row_to_dead_letter({"id": "t1", "title": "do thing"})
    assert dlt.retry_count is None
    assert dlt.final_error == ""


# ─── message format ───────────────────────────────────────────────────────────


def test_format_contains_all_required_fields():
    dlt = m.DeadLetterTask(
        task_id="t9", description="build X", retry_count=3, final_error="timeout"
    )
    msg = m.format_dead_letter_message(dlt)
    assert "t9" in msg and "build X" in msg and "3" in msg and "timeout" in msg
    assert "not deleted" in msg  # row retained for audit
    assert "[DEAD-LETTER]" in msg  # plain-text marker (Aiden flag)
    assert "🔴" not in msg  # no emoji — renders identically in every Slack client


def test_format_degrades_gracefully_on_unknowns():
    dlt = m.DeadLetterTask(task_id="t0", description="", retry_count=None, final_error="")
    msg = m.format_dead_letter_message(dlt)
    assert "unknown" in msg  # retry count unknown
    assert "not captured" in msg  # final error not captured
    assert "(no title)" in msg


# ─── post fail-open ───────────────────────────────────────────────────────────


def test_post_returns_false_without_token(monkeypatch):
    monkeypatch.delenv("SLACK_BOT_TOKEN", raising=False)
    dlt = m.DeadLetterTask(task_id="t", description="d", retry_count=3, final_error="e")
    assert m.post_dead_letter(dlt) is False  # logged locally, not raised


def test_post_true_on_2xx(monkeypatch):
    class _Resp:
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    monkeypatch.setattr(m.urllib.request, "urlopen", lambda *a, **k: _Resp())
    dlt = m.DeadLetterTask(task_id="t", description="d", retry_count=3, final_error="e")
    assert m.post_dead_letter(dlt, token="xoxb-test") is True


# ─── dedup (fire exactly once) ────────────────────────────────────────────────


def test_notify_new_fires_once_per_task():
    posted = []
    rows = [{"id": "a", "title": "A"}, {"id": "b", "title": "B"}]
    notified: set = set()
    n1 = m.notify_new_dead_letters(
        rows, notified, post=lambda d, token=None: posted.append(d.task_id) or True
    )
    assert n1 == 2 and notified == {"a", "b"}
    # same rows next poll → no re-fire
    n2 = m.notify_new_dead_letters(
        rows, notified, post=lambda d, token=None: posted.append(d.task_id) or True
    )
    assert n2 == 0
    assert posted == ["a", "b"]


def test_notify_new_records_even_on_post_failure_to_avoid_spam():
    notified: set = set()
    m.notify_new_dead_letters(
        [{"id": "x", "title": "X"}], notified, post=lambda d, token=None: False
    )
    assert "x" in notified  # recorded despite failure (failure is logged; no infinite re-spam)


def test_notify_new_skips_rows_without_id():
    posted = []
    m.notify_new_dead_letters(
        [{"title": "no id"}], set(), post=lambda d, token=None: posted.append(d) or True
    )
    assert posted == []
