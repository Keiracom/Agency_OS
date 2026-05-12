"""tests for slack_relay.py CALLSIGN resolution + ALLOWED_CHANNELS guard.

Per Dave directive #6 (callsign bug fix 2026-05-11): slack_relay must
refuse to run without explicit CALLSIGN env or ./IDENTITY.md, and must
refuse to post to channels not in the per-callsign allowlist.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
RELAY = REPO_ROOT / "scripts" / "slack_relay.py"


def _worktree_callsign() -> str:
    """Read callsign from IDENTITY.md so tests work in any worktree."""
    identity = REPO_ROOT / "IDENTITY.md"
    if identity.exists():
        for line in identity.read_text().splitlines():
            if line.startswith("**CALLSIGN:**"):
                return line.split("**CALLSIGN:**")[1].strip()
    return "unknown"


def _run(env: dict[str, str], args: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess:
    base_env = {"PATH": os.environ.get("PATH", "")}
    base_env.update(env)
    return subprocess.run(
        [sys.executable, str(RELAY), *args],
        env=base_env,
        cwd=str(cwd) if cwd else None,
        capture_output=True,
        text=True,
        timeout=10,
    )


def test_callsign_resolves_from_identity_md(tmp_path: Path) -> None:
    """No CALLSIGN env + IDENTITY.md present → resolves callsign from file."""
    callsign = _worktree_callsign()
    result = _run(
        env={
            "SLACK_BOT_TOKEN": "fake-token",
            "R_VERIFY_SKIP": "1",
            "CONCUR_GATE_SKIP": "1",
        },
        args=["-c", "C0B2PM3TV0B", "test"],
    )
    assert result.returncode == 2
    assert f"{callsign}-relay refuses post" in result.stderr
    assert "not in worktree allowlist" in result.stderr


def test_callsign_unresolved_exits_2(tmp_path: Path) -> None:
    """No env, no IDENTITY.md → exit 2 with clear error."""
    fake_repo = tmp_path / "fakerepo"
    (fake_repo / "scripts").mkdir(parents=True)
    relay_copy = fake_repo / "scripts" / "slack_relay.py"
    relay_copy.write_bytes(RELAY.read_bytes())
    result = subprocess.run(
        [sys.executable, str(relay_copy), "-g", "test"],
        env={"PATH": os.environ.get("PATH", "")},
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 2
    assert "CALLSIGN unresolved" in result.stderr


def test_forbidden_channel_blocks() -> None:
    """Posting to #ceo from aiden worktree → exit 2 with allowlist message."""
    result = _run(
        env={
            "SLACK_BOT_TOKEN": "fake-token",
            "R_VERIFY_SKIP": "1",
            "CONCUR_GATE_SKIP": "1",
            "CALLSIGN": "aiden",
        },
        args=["-c", "C0B2PM3TV0B", "ceo-block"],
    )
    assert result.returncode == 2
    assert "aiden-relay refuses post to C0B2PM3TV0B" in result.stderr


def test_env_callsign_overrides_identity(tmp_path: Path) -> None:
    """CALLSIGN env wins over IDENTITY.md."""
    result = _run(
        env={
            "SLACK_BOT_TOKEN": "fake-token",
            "R_VERIFY_SKIP": "1",
            "CONCUR_GATE_SKIP": "1",
            "CALLSIGN": "elliot",
        },
        args=["-c", "C0B2EJU53EK", "alerts-block-for-elliot"],
    )
    # elliot allowlist = execution + ceo + completed_directives. #alerts blocked.
    assert result.returncode == 2
    assert "elliot-relay refuses post to C0B2EJU53EK" in result.stderr
