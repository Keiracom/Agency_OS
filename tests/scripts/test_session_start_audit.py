"""tests for scripts/session_start_audit.py — Dave System Health Outcome 3.

Mocks Supabase + Slack to test:
  - resolve_callsign from env / IDENTITY.md / fallback
  - write_session_start_audit writes correct payload to agent_memories
  - DB failure → returns None + log warning + Slack alert
  - main() always returns 0 (best-effort, never blocks agent startup)
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
AUDIT_PATH = REPO_ROOT / "scripts" / "session_start_audit.py"


@pytest.fixture(scope="module")
def audit():
    spec = importlib.util.spec_from_file_location("session_start_audit", AUDIT_PATH)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["session_start_audit"] = mod
    spec.loader.exec_module(mod)
    return mod


# ─────────────────────────────────────────────────────────────────────────────
# resolve_callsign
# ─────────────────────────────────────────────────────────────────────────────


def test_resolve_callsign_from_env(audit, monkeypatch) -> None:
    monkeypatch.setenv("CALLSIGN", "aiden")
    assert audit.resolve_callsign() == "aiden"


def test_resolve_callsign_lowercases(audit, monkeypatch) -> None:
    monkeypatch.setenv("CALLSIGN", "AIDEN")
    assert audit.resolve_callsign() == "aiden"


def test_resolve_callsign_from_identity_md(audit, monkeypatch, tmp_path) -> None:
    """CALLSIGN env empty → fallback to IDENTITY.md in cwd."""
    monkeypatch.delenv("CALLSIGN", raising=False)
    (tmp_path / "IDENTITY.md").write_text("# IDENTITY\n\n**CALLSIGN:** aiden\n")
    monkeypatch.chdir(tmp_path)
    assert audit.resolve_callsign() == "aiden"


def test_resolve_callsign_fallback_unknown(audit, monkeypatch, tmp_path) -> None:
    """No env, no IDENTITY.md → 'unknown'."""
    monkeypatch.delenv("CALLSIGN", raising=False)
    monkeypatch.chdir(tmp_path)
    assert audit.resolve_callsign() == "unknown"


# ─────────────────────────────────────────────────────────────────────────────
# write_session_start_audit
# ─────────────────────────────────────────────────────────────────────────────


def test_write_session_start_audit_writes_correct_payload(audit) -> None:
    captured: list[dict] = []

    def fake_sb_post(table: str, payload: dict) -> list:
        captured.append({"table": table, "payload": payload})
        return [{"id": "fake-uuid"}]

    # Patch the import inside the function — write_session_start_audit imports
    # sb_post lazily so we patch on the imported name post-load.
    import src.evo.supabase_client as sb_mod

    with patch.object(sb_mod, "sb_post", side_effect=fake_sb_post):
        row = audit.write_session_start_audit("aiden")
    assert row is not None
    assert len(captured) == 1
    assert captured[0]["table"] == "agent_memories"
    payload = captured[0]["payload"]
    assert payload["callsign"] == "aiden"
    assert payload["source_type"] == "session_start_audit"
    content = json.loads(payload["content"])
    assert content["callsign"] == "aiden"
    assert content["manual_doc_id"] == audit.MANUAL_DOC_ID


def test_write_session_start_audit_handles_db_failure(audit) -> None:
    """sb_post raises → returns None + no exception."""
    import src.evo.supabase_client as sb_mod

    def fake_sb_post(*args, **kwargs):
        raise RuntimeError("supabase down")

    with patch.object(sb_mod, "sb_post", side_effect=fake_sb_post):
        row = audit.write_session_start_audit("aiden")
    assert row is None


# ─────────────────────────────────────────────────────────────────────────────
# post_slack_alert
# ─────────────────────────────────────────────────────────────────────────────


def test_post_slack_alert_no_token_returns_false(audit, monkeypatch) -> None:
    monkeypatch.delenv("SLACK_BOT_TOKEN", raising=False)
    assert audit.post_slack_alert("test") is False


def test_post_slack_alert_ok_returns_true(audit, monkeypatch) -> None:
    monkeypatch.setenv("SLACK_BOT_TOKEN", "xoxb-fake")
    import urllib.request

    class FakeResponse:
        def read(self) -> bytes:
            return json.dumps({"ok": True}).encode("utf-8")

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

    with patch.object(urllib.request, "urlopen", return_value=FakeResponse()):
        assert audit.post_slack_alert("test") is True


# ─────────────────────────────────────────────────────────────────────────────
# main entry — best-effort always returns 0
# ─────────────────────────────────────────────────────────────────────────────


def test_main_succeeds_on_db_success(audit, monkeypatch) -> None:
    monkeypatch.setenv("CALLSIGN", "aiden")
    with patch.object(audit, "write_session_start_audit", return_value={"id": "fake"}):
        assert audit.main() == 0


def test_main_returns_zero_even_on_db_failure(audit, monkeypatch) -> None:
    """Best-effort — agent startup must never be blocked by audit failure."""
    monkeypatch.setenv("CALLSIGN", "aiden")
    with (
        patch.object(audit, "write_session_start_audit", return_value=None),
        patch.object(audit, "post_slack_alert", return_value=True),
    ):
        assert audit.main() == 0


def test_main_attempts_slack_alert_on_db_failure(audit, monkeypatch) -> None:
    """When DB fails, main() must call post_slack_alert."""
    monkeypatch.setenv("CALLSIGN", "aiden")
    alert_calls: list[str] = []
    with (
        patch.object(audit, "write_session_start_audit", return_value=None),
        patch.object(
            audit, "post_slack_alert", side_effect=lambda text: alert_calls.append(text) or True
        ),
    ):
        audit.main()
    assert len(alert_calls) == 1
    assert "SESSION-START-AUDIT" in alert_calls[0]
    assert "aiden" in alert_calls[0]
