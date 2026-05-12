"""test_upload.py — pytest suite for slack-file-upload skill.

All tests are 100% mocked — no real Slack API calls.
"""

from __future__ import annotations

import importlib
import sys
import types
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

SKILL_DIR = Path(__file__).parent


def _load_upload(monkeypatch, token: str = "xoxb-test") -> types.ModuleType:
    """Import upload.py with SLACK_BOT_TOKEN set and slack_sdk mocked."""
    monkeypatch.setenv("SLACK_BOT_TOKEN", token)
    monkeypatch.setenv("CALLSIGN", "elliot")

    # Provide a minimal slack_sdk stub so import doesn't require the real package
    sdk_stub = types.ModuleType("slack_sdk")
    web_stub = types.ModuleType("slack_sdk.web")
    errors_stub = types.ModuleType("slack_sdk.errors")

    class _SlackApiError(Exception):
        def __init__(self, message: str, response: dict):
            super().__init__(message)
            self.response = response

    errors_stub.SlackApiError = _SlackApiError
    web_stub.WebClient = MagicMock()
    sdk_stub.web = web_stub
    sdk_stub.errors = errors_stub

    sys.modules.setdefault("slack_sdk", sdk_stub)
    sys.modules.setdefault("slack_sdk.web", web_stub)
    sys.modules.setdefault("slack_sdk.errors", errors_stub)

    if "upload" in sys.modules:
        del sys.modules["upload"]

    spec = importlib.util.spec_from_file_location("upload", SKILL_DIR / "upload.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ---------------------------------------------------------------------------
# Test 1: missing channel/path args → exit 3
# ---------------------------------------------------------------------------


def test_missing_args_exits_3(monkeypatch, capsys):
    mod = _load_upload(monkeypatch)
    with pytest.raises(SystemExit) as exc:
        mod.main([])
    assert exc.value.code == 3
    captured = capsys.readouterr()
    assert "usage" in captured.err.lower()


# ---------------------------------------------------------------------------
# Test 2: channel name "ceo" resolves to correct ID
# ---------------------------------------------------------------------------


def test_channel_name_resolution(monkeypatch):
    mod = _load_upload(monkeypatch)
    assert mod._resolve_channel("ceo") == "C0B2PM3TV0B"
    assert mod._resolve_channel("#execution") == "C0B3QB0K1GQ"
    # raw ID passthrough
    assert mod._resolve_channel("C0B2EJU53EK") == "C0B2EJU53EK"


# ---------------------------------------------------------------------------
# Test 3: missing SLACK_BOT_TOKEN → exit 2
# ---------------------------------------------------------------------------


def test_missing_token_exits_2(monkeypatch, tmp_path, capsys):
    monkeypatch.delenv("SLACK_BOT_TOKEN", raising=False)
    monkeypatch.setenv("CALLSIGN", "elliot")

    if "upload" in sys.modules:
        del sys.modules["upload"]

    spec = importlib.util.spec_from_file_location("upload", SKILL_DIR / "upload.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    dummy = tmp_path / "f.md"
    dummy.write_text("hello")

    with pytest.raises(SystemExit) as exc:
        mod.main(["ceo", str(dummy)])
    assert exc.value.code == 2
    captured = capsys.readouterr()
    assert "SLACK_BOT_TOKEN" in captured.err


# ---------------------------------------------------------------------------
# Test 4: files_upload_v2 called with correct kwargs
# ---------------------------------------------------------------------------


def test_sdk_called_with_correct_kwargs(monkeypatch, tmp_path):
    mod = _load_upload(monkeypatch)

    dummy = tmp_path / "report.md"
    dummy.write_text("# Report")

    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.get.return_value = {"id": "F123"}
    mock_client.files_upload_v2.return_value = mock_response

    with patch.object(
        mod, "WebClient" if hasattr(mod, "WebClient") else "__builtins__", create=True
    ):
        # Patch the WebClient inside the module's imported namespace
        import slack_sdk.web as _web

        original = _web.WebClient
        _web.WebClient = MagicMock(return_value=mock_client)
        try:
            mod.main(["ceo", str(dummy), "--title=My Report", "--comment=[ELLIOT] done"])
        finally:
            _web.WebClient = original

    mock_client.files_upload_v2.assert_called_once()
    kwargs = mock_client.files_upload_v2.call_args.kwargs
    assert kwargs["channel"] == "C0B2PM3TV0B"
    assert kwargs["title"] == "My Report"
    assert kwargs["filename"] == "report.md"
    assert kwargs["initial_comment"] == "[ELLIOT] done"


# ---------------------------------------------------------------------------
# Test 5: callsign prefix auto-applied to comment when missing
# ---------------------------------------------------------------------------


def test_callsign_prefix_applied(monkeypatch):
    mod = _load_upload(monkeypatch)
    # comment without prefix
    result = mod._prefix_comment("Phase 1 done", "[ELLIOT]")
    assert result == "[ELLIOT] Phase 1 done"
    # comment already prefixed — no double-tag
    result2 = mod._prefix_comment("[ELLIOT] Phase 1 done", "[ELLIOT]")
    assert result2 == "[ELLIOT] Phase 1 done"
    # None comment → just the tag
    result3 = mod._prefix_comment(None, "[ELLIOT]")
    assert result3 == "[ELLIOT]"


# ---------------------------------------------------------------------------
# Test 6: file not found → exit 3
# ---------------------------------------------------------------------------


def test_file_not_found_exits_3(monkeypatch, tmp_path, capsys):
    mod = _load_upload(monkeypatch)
    missing = tmp_path / "does_not_exist.md"

    with pytest.raises(SystemExit) as exc:
        mod.main(["ceo", str(missing)])
    assert exc.value.code == 3
    captured = capsys.readouterr()
    assert "not found" in captured.err.lower()
