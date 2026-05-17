"""tests for scripts/cognee_session_start.py — session-start context injection.

All network calls mocked via unittest.mock.patch. No Cognee or network
connectivity required. All tests pass when run offline.

KEI-107: Phase 0.5 test coverage (Aiden re-review requirement).
"""

from __future__ import annotations

import importlib.util
import os
import sys
import urllib.error
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPT_PATH = REPO_ROOT / "scripts" / "cognee_session_start.py"


@pytest.fixture(scope="module")
def css_mod():
    """Load cognee_session_start as a module, isolated from sys.modules."""
    spec = importlib.util.spec_from_file_location("cognee_session_start", SCRIPT_PATH)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["cognee_session_start"] = mod
    spec.loader.exec_module(mod)
    return mod


# ── helpers ──────────────────────────────────────────────────────────────────


def _run(css_mod, argv, env=None):
    """Run main() with given argv list and optional env overrides.

    Temporarily patches os.environ so individual keys can be injected
    without polluting the test environment.
    """
    env_patch = {"GEMINI_API_KEY": "fake-key-for-tests"}
    if env is not None:
        env_patch.update(env)
    with patch.dict(os.environ, env_patch, clear=False):
        css_mod.main(argv)


# ── test 1: Cognee unreachable → fail-open, stub written, exit 0 ─────────────


def test_cognee_unreachable_writes_stub(tmp_path, css_mod):
    """URLError from login → fail-open; output file is written; no exception."""
    out = tmp_path / "context.md"

    def _raise_url_error(req, timeout=None):
        raise urllib.error.URLError("connection refused")

    with patch("urllib.request.urlopen", side_effect=_raise_url_error):
        _run(css_mod, ["--callsign", "elliot", "--output", str(out)])

    assert out.exists(), "output file must be written on URLError (fail-open)"
    content = out.read_text()
    # Should contain the callsign header regardless of failure mode
    assert "elliot" in content.lower() or "cognee" in content.lower()


# ── test 2: HTTP timeout → fail-open ─────────────────────────────────────────


def test_http_timeout_fail_open(tmp_path, css_mod):
    """socket.timeout from urlopen → fail-open; output file written; no exception."""
    out = tmp_path / "context-timeout.md"

    def _raise_timeout(req, timeout=None):
        raise TimeoutError("timed out")

    with patch("urllib.request.urlopen", side_effect=_raise_timeout):
        _run(css_mod, ["--callsign", "aiden", "--output", str(out)])

    assert out.exists(), "output file must be written on timeout (fail-open)"


# ── test 3: callsign interpolated into default output filename ────────────────


def test_callsign_interpolated_in_output_filename(tmp_path, css_mod):
    """Default output path includes the callsign."""

    def _fake_gettempdir():
        return str(tmp_path)

    def _raise_url_error(req, timeout=None):
        raise urllib.error.URLError("offline")

    with (
        patch("tempfile.gettempdir", side_effect=_fake_gettempdir),
        patch("urllib.request.urlopen", side_effect=_raise_url_error),
    ):
        _run(css_mod, ["--callsign", "scout"])

    expected = tmp_path / "cognee-context-scout.md"
    assert expected.exists(), f"expected {expected} to exist; got {list(tmp_path.iterdir())}"


# ── test 4: zero-hits → stub markdown with expected no-results text ───────────


def test_zero_hits_writes_no_results_stub(tmp_path, css_mod):
    """When Cognee returns empty list, output contains the no-results sentinel."""
    out = tmp_path / "context-zero.md"

    # Simulate successful login returning a token, then empty search result.
    login_resp = MagicMock()
    login_resp.read.return_value = b'{"access_token": "tok"}'
    login_resp.__enter__ = lambda s: s
    login_resp.__exit__ = MagicMock(return_value=False)

    search_resp = MagicMock()
    search_resp.read.return_value = b"[]"
    search_resp.__enter__ = lambda s: s
    search_resp.__exit__ = MagicMock(return_value=False)

    responses = [login_resp, search_resp]
    call_count = [0]

    def _urlopen(req, timeout=None):
        resp = responses[call_count[0]]
        call_count[0] += 1
        return resp

    with patch("urllib.request.urlopen", side_effect=_urlopen):
        _run(css_mod, ["--callsign", "elliot", "--output", str(out)])

    assert out.exists()
    content = out.read_text()
    assert "No Cognee results for this callsign" in content, (
        f"Expected no-results sentinel in output; got:\n{content[:400]}"
    )


# ── test 5: happy-path — 2 hits → output contains both hits' text ─────────────


def test_happy_path_two_hits_in_output(tmp_path, css_mod):
    """Successful login + search returning 2 hits → both appear in output file."""
    out = tmp_path / "context-happy.md"

    hit_a = "Decision: use Railway for compute (KEI-107)"
    hit_b = "Open KEI: KEI-136 cognee-session-start Phase 0.5 blocker"

    login_resp = MagicMock()
    login_resp.read.return_value = b'{"access_token": "tok"}'
    login_resp.__enter__ = lambda s: s
    login_resp.__exit__ = MagicMock(return_value=False)

    search_resp = MagicMock()
    # Cognee returns list of strings (or dicts); script does str(hit).strip()
    search_resp.read.return_value = f'["{hit_a}", "{hit_b}"]'.encode()
    search_resp.__enter__ = lambda s: s
    search_resp.__exit__ = MagicMock(return_value=False)

    responses = [login_resp, search_resp]
    call_count = [0]

    def _urlopen(req, timeout=None):
        resp = responses[call_count[0]]
        call_count[0] += 1
        return resp

    with patch("urllib.request.urlopen", side_effect=_urlopen):
        _run(css_mod, ["--callsign", "elliot", "--output", str(out)])

    assert out.exists()
    content = out.read_text()
    assert hit_a in content, f"hit_a missing from output:\n{content[:600]}"
    assert hit_b in content, f"hit_b missing from output:\n{content[:600]}"
