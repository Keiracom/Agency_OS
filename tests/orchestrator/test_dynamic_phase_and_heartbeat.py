"""Unit tests for Defects 1 + 2 (Dave 2026-05-31).

  Defect 1 — write_compact_state.current_phase: live ceo_memory query for the
  phase header, with a deterministic fallback when the query fails. Replaces
  the previous hardcoded "V2 migration — Phase 0" literal.

  Defect 2 — write_heartbeat.main: Stop-hook entry-point that refreshes
  HEARTBEAT.md with live phase / open-PRs / active-directives data.

Pattern: monkeypatch the network/subprocess seams so no real HTTP / gh
shells out. Smoke wiring (host run, live data) is exercised by
scripts/orchestrator/test_revive_cycle.sh — these tests cover the per-unit
contracts that smoke can't poke (error paths, fallback wording).
"""

from __future__ import annotations

import importlib
import io
import json
from pathlib import Path
from unittest.mock import patch

import pytest


@pytest.fixture
def wcs():
    mod = importlib.import_module("scripts.orchestrator.write_compact_state")
    return importlib.reload(mod)


@pytest.fixture
def whb():
    importlib.import_module("scripts.orchestrator.write_compact_state")
    mod = importlib.import_module("scripts.orchestrator.write_heartbeat")
    return importlib.reload(mod)


def _fake_urlopen(payload: object):
    """Build a urlopen replacement that returns a serialised payload."""
    body = json.dumps(payload).encode()

    class _Resp:
        def __enter__(self):
            return io.BytesIO(body)

        def __exit__(self, *_):
            return False

    return lambda *_a, **_kw: _Resp()


# ---------------------------------------------------------------------------
# Defect 1 — current_phase
# ---------------------------------------------------------------------------


def test_current_phase_returns_live_value_when_ceo_memory_reachable(wcs, monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_KEY", "fake-key")
    payload = [{"value": {"phase_1_status": "OPEN — Temporal chain build starting"}}]
    with patch("urllib.request.urlopen", _fake_urlopen(payload)):
        result = wcs.current_phase()
    assert result == "Phase 1 — OPEN — Temporal chain build starting"


def test_current_phase_falls_back_when_env_missing(wcs, monkeypatch):
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_SERVICE_KEY", raising=False)
    assert wcs.current_phase() == wcs.PHASE_FALLBACK
    assert "phase unknown" in wcs.PHASE_FALLBACK


def test_current_phase_falls_back_on_http_error(wcs, monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_KEY", "fake-key")

    def boom(*_a, **_kw):
        raise RuntimeError("network down")

    with patch("urllib.request.urlopen", boom):
        assert wcs.current_phase() == wcs.PHASE_FALLBACK


def test_current_phase_falls_back_when_row_missing(wcs, monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_KEY", "fake-key")
    with patch("urllib.request.urlopen", _fake_urlopen([])):
        assert wcs.current_phase() == wcs.PHASE_FALLBACK


def test_current_phase_falls_back_when_jsonb_field_missing(wcs, monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_KEY", "fake-key")
    payload = [{"value": {"some_other_field": "irrelevant"}}]
    with patch("urllib.request.urlopen", _fake_urlopen(payload)):
        assert wcs.current_phase() == wcs.PHASE_FALLBACK


# ---------------------------------------------------------------------------
# Defect 2 — write_heartbeat
# ---------------------------------------------------------------------------


def test_write_heartbeat_writes_file_with_live_phase(whb, monkeypatch, tmp_path, capsys):
    out = tmp_path / "HEARTBEAT.md"
    monkeypatch.setenv("HEARTBEAT_PATH", str(out))
    monkeypatch.setattr(whb, "current_phase", lambda: "Phase 1 — building")
    monkeypatch.setattr(
        whb,
        "_open_prs",
        lambda: [
            {"number": 1373, "title": "watchdog fix", "author": {"login": "orion"}},
        ],
    )
    monkeypatch.setattr(
        whb,
        "_active_directives",
        lambda: [
            {
                "key": "ceo:directive_321",
                "value": {"title": "ship recovery infra", "status": "active"},
            },
        ],
    )

    rc = whb.main()
    assert rc == 0
    text = out.read_text()
    assert "## Current Phase: Phase 1 — building" in text
    assert "#1373 watchdog fix (@orion)" in text
    assert "ceo:directive_321: ship recovery infra" in text
    assert "## Last update:" in text
    captured = capsys.readouterr()
    assert "HEARTBEAT written:" in captured.out


def test_write_heartbeat_uses_fallback_sections_when_io_returns_empty(whb, monkeypatch, tmp_path):
    out = tmp_path / "HEARTBEAT.md"
    monkeypatch.setenv("HEARTBEAT_PATH", str(out))
    monkeypatch.setattr(whb, "current_phase", lambda: whb.PHASE_FALLBACK)
    monkeypatch.setattr(whb, "_open_prs", lambda: [])
    monkeypatch.setattr(whb, "_active_directives", lambda: [])

    rc = whb.main()
    assert rc == 0
    text = out.read_text()
    assert "## Open PRs:\n- none open" in text
    assert "## Active directives:\n- none active" in text
    assert whb.PHASE_FALLBACK in text


def test_write_heartbeat_returns_1_on_write_failure(whb, monkeypatch, capsys):
    monkeypatch.setattr(whb, "current_phase", lambda: "Phase 1")
    monkeypatch.setattr(whb, "_open_prs", lambda: [])
    monkeypatch.setattr(whb, "_active_directives", lambda: [])
    # Direct the writer at a path inside a file (not a dir) to force OSError.
    bad = Path("/tmp/test_revive_does_not_exist/not/a/dir/HEARTBEAT.md")
    monkeypatch.setenv("HEARTBEAT_PATH", str(bad))

    def boom(*_a, **_kw):
        raise OSError("cannot write")

    monkeypatch.setattr(Path, "write_text", boom)
    monkeypatch.setattr(Path, "mkdir", lambda *a, **kw: None)
    rc = whb.main()
    assert rc == 1
    err = capsys.readouterr().err
    assert "write_heartbeat: write failed" in err


def test_open_prs_returns_empty_when_gh_fails(whb, monkeypatch):
    class _R:
        returncode = 1
        stdout = ""

    monkeypatch.setattr(whb.subprocess, "run", lambda *a, **kw: _R())
    assert whb._open_prs() == []


def test_active_directives_returns_empty_when_env_missing(whb, monkeypatch):
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_SERVICE_KEY", raising=False)
    assert whb._active_directives() == []


def test_active_directives_parses_postgrest_rows(whb, monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_KEY", "fake-key")
    payload = [
        {"key": "ceo:directive_42", "value": {"title": "do the thing", "status": "active"}},
        {"key": "ceo:directive_43", "value": {"summary": "also this", "status": "active"}},
    ]
    with patch("urllib.request.urlopen", _fake_urlopen(payload)):
        rows = whb._active_directives()
    assert len(rows) == 2
    assert rows[0]["key"] == "ceo:directive_42"


# ---------------------------------------------------------------------------
# Defect 3 — end-to-end smoke (bash) runs in CI under pytest
# ---------------------------------------------------------------------------


def test_revive_cycle_smoke_passes_under_pytest(monkeypatch, tmp_path):
    """Invoke scripts/orchestrator/test_revive_cycle.sh as the dispatch
    mandates. Routes both writes to tmpdir so the host's real HEARTBEAT.md
    is never touched. In CI Supabase is unreachable, so the smoke validates
    the structural fix via the 'phase unknown' fallback path; on the host
    with live reach it validates the live 'Phase 1' query."""
    import os
    import subprocess

    repo_root = Path(__file__).resolve().parents[2]
    script = repo_root / "scripts" / "orchestrator" / "test_revive_cycle.sh"
    env = {**os.environ, "PYTHON": os.environ.get("PYTHON", "python3")}
    proc = subprocess.run(
        ["bash", str(script)],
        cwd=str(repo_root),
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert proc.returncode == 0, (
        f"smoke exited {proc.returncode}\n--- stdout ---\n{proc.stdout}"
        f"\n--- stderr ---\n{proc.stderr}"
    )
    assert "PASS — write_heartbeat.py" in proc.stdout
    assert "Result: 2 pass, 0 fail" in proc.stdout
