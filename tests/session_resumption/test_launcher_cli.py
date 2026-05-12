"""Smoke tests for scripts/agent_session_launcher.sh — Drevon PR-C.

Verifies the launcher script's resolution + flag-selection path end-to-end via
SESSION_LAUNCHER_DRY mode (no actual `claude` exec). Does not hit Supabase —
the launcher's resolver path falls through to a fresh UUID when sb_get cannot
contact the DB, which is what we exercise here.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
LAUNCHER = REPO_ROOT / "scripts" / "agent_session_launcher.sh"
UUID_RE = re.compile(r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b")


def _run(args, env_extra=None):
    env = {**os.environ, "SESSION_LAUNCHER_DRY": "1"}
    if env_extra:
        env.update(env_extra)
    # Strip Supabase creds so resolver falls through to fresh path without
    # accidentally writing to a real DB during tests.
    for k in ("SUPABASE_URL", "SUPABASE_SERVICE_KEY"):
        env.pop(k, None)
    return subprocess.run(
        ["bash", str(LAUNCHER), *args],
        capture_output=True,
        text=True,
        env=env,
        cwd=REPO_ROOT,
    )


def test_launcher_exits_2_without_callsign():
    result = _run([])
    assert result.returncode == 2 or "usage" in result.stderr.lower()


@pytest.mark.parametrize("callsign", ["elliot", "aiden", "max", "atlas", "orion", "scout"])
def test_launcher_resolves_to_fresh_uuid_when_db_unreachable(callsign):
    """All 6 callsigns must produce a launchable command even with DB down."""
    result = _run([callsign])
    assert result.returncode == 0, f"stderr={result.stderr}"
    assert "[launcher] mode=" in result.stdout
    assert f"callsign={callsign}" in result.stdout
    # Without a DB the resolver returns None → mode=fresh + a generated UUID.
    assert "mode=fresh" in result.stdout
    assert UUID_RE.search(result.stdout), f"no uuid in output:\n{result.stdout}"


def test_launcher_emits_session_id_flag_for_fresh_path():
    result = _run(["orion"])
    assert "would exec: claude --session-id" in result.stdout


def test_launcher_forwards_extra_args():
    result = _run(["orion", "--model", "claude-opus-4-7", "extra"])
    assert "--model claude-opus-4-7 extra" in result.stdout


@pytest.mark.skipif(sys.platform.startswith("win"), reason="bash launcher is POSIX-only")
def test_launcher_script_is_executable():
    assert os.access(LAUNCHER, os.X_OK), f"{LAUNCHER} is not executable"
