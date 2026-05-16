"""KEI-79 — behavioural tests for bd escalate + direct_post + concur_gate carve-out."""

from __future__ import annotations

import sys
import types
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from scripts import bd_escalate  # noqa: E402
from src.bot_common import concur_gate  # noqa: E402
from src.slack_bot import direct_post  # noqa: E402


def test_format_options_csv_strips():
    assert bd_escalate._format_options(" A, B ,C") == ["A", "B", "C"]
    assert bd_escalate._format_options(None) is None
    assert bd_escalate._format_options("") is None


def test_build_text_no_options_free_form():
    out = bd_escalate._build_text("aiden", "KEI-58", "kuzu cap stuck", None, False)
    assert "[ESCALATION:aiden] KEI-58" in out
    assert "kuzu cap stuck" in out
    assert "Reply with decision text" in out


def test_build_text_with_options_labels_letters():
    out = bd_escalate._build_text("aiden", "KEI-58", "pick path", ["foo", "bar", "baz"], False)
    assert "A) foo" in out and "B) bar" in out and "C) baz" in out


def test_build_text_rate_limit_prefix():
    out = bd_escalate._build_text("max", "KEI-9", "x", None, True)
    assert out.startswith("[RATE-LIMIT-EXCEEDED] [ESCALATION:max]")


def test_concur_gate_carve_out_for_escalation_sentinel():
    sentinel = "[ESCALATION-INITIATED:aiden:KEI-58]"
    assert concur_gate.should_gate(sentinel) is False
    plain_concur = "[CONCUR:aiden] looks good"
    assert concur_gate.should_gate(plain_concur) is True


def test_concur_gate_still_blocks_plain_concur_without_sentinel():
    body = "Posting [CONCUR:elliot] on the schema slice"
    assert concur_gate.should_gate(body) is True


def test_direct_post_returns_queued_retry_on_slack_failure(monkeypatch):
    def boom(*a, **k):
        raise RuntimeError("slack 503")

    monkeypatch.setattr(direct_post, "_post_via_urllib", boom)
    monkeypatch.setattr(direct_post, "_enqueue_retry", lambda *a, **k: None)
    out = direct_post.post_to_ceo("hi", ceo_decision_id="abc")
    assert out["ok"] is False
    assert out["status"] == "queued_retry"


def test_direct_post_returns_posted_on_success(monkeypatch):
    monkeypatch.setattr(
        direct_post, "_post_via_urllib", lambda *a, **k: {"ok": True, "ts": "1.000"}
    )
    out = direct_post.post_to_ceo("hi", ceo_decision_id="abc")
    assert out["ok"] is True
    assert out["status"] == "posted"
    assert out["ts"] == "1.000"


def test_post_via_urllib_missing_token_raises(monkeypatch):
    monkeypatch.delenv("SLACK_BOT_TOKEN", raising=False)
    with pytest.raises(RuntimeError):
        direct_post._post_via_urllib("hi", None)


def test_callsign_falls_through_env_chain(monkeypatch):
    monkeypatch.delenv("CALLSIGN", raising=False)
    monkeypatch.delenv("TASKS_CALLSIGN", raising=False)
    assert bd_escalate._callsign() == "unknown"
    monkeypatch.setenv("TASKS_CALLSIGN", "scout")
    assert bd_escalate._callsign() == "scout"
    monkeypatch.setenv("CALLSIGN", "aiden")
    assert bd_escalate._callsign() == "aiden"


def test_rate_limit_check_force_skips(monkeypatch):
    cur = types.SimpleNamespace(execute=lambda *a, **k: None, fetchone=lambda: (99,))
    assert bd_escalate._rate_limit_check(cur, "aiden", force=True) is False


def test_rate_limit_check_triggers_at_threshold(monkeypatch):
    class FakeCur:
        def execute(self, *a, **k):
            self._called = True

        def fetchone(self):
            return (bd_escalate.RATE_LIMIT_PER_24H,)

    assert bd_escalate._rate_limit_check(FakeCur(), "aiden", force=False) is True


def test_rate_limit_check_under_threshold_passes():
    class FakeCur:
        def execute(self, *a, **k):
            pass

        def fetchone(self):
            return (bd_escalate.RATE_LIMIT_PER_24H - 1,)

    assert bd_escalate._rate_limit_check(FakeCur(), "aiden", force=False) is False


def test_resolve_task_returns_explicit_when_set():
    cur = types.SimpleNamespace(execute=lambda *a, **k: None, fetchall=lambda: [])
    assert bd_escalate._resolve_task(cur, "KEI-58", "aiden") == "KEI-58"


def test_resolve_task_errors_on_zero_active_claims():
    class FakeCur:
        def execute(self, *a, **k):
            pass

        def fetchall(self):
            return []

    with pytest.raises(SystemExit):
        bd_escalate._resolve_task(FakeCur(), None, "aiden")


def test_resolve_task_returns_id_on_single_active_claim():
    class FakeCur:
        def execute(self, *a, **k):
            pass

        def fetchall(self):
            return [("KEI-79",)]

    assert bd_escalate._resolve_task(FakeCur(), None, "aiden") == "KEI-79"
