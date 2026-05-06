"""Tests for scripts/check_claim.py — CLI verification gate."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_SCRIPT = str(_REPO_ROOT / "scripts" / "check_claim.py")

# Common required flags used across tests
_REQUIRED_FLAGS = [
    "--callsign",
    "testcallsign",
    "--directive-id",
    "TEST-001",
    "--claim-text",
    "Test claim text",
    "--evidence",
    "$ pytest -q\n3 passed",
    "--target-files",
    "src/foo.py",
    "--store-writes",
    '[{"directive_id":"TEST-001","store":"manual"}]',
]


def test_help_exits_zero():
    result = subprocess.run(
        [sys.executable, _SCRIPT, "--help"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"Expected exit 0, got {result.returncode}\n{result.stdout}\n{result.stderr}"
    )
    assert "check_claim" in result.stdout.lower() or "gatekeeper" in result.stdout.lower()


def test_missing_required_flags_exits_two():
    result = subprocess.run(
        [sys.executable, _SCRIPT],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 2, (
        f"Expected exit 2 (missing flags), got {result.returncode}\n{result.stderr}"
    )


def test_dry_run_exits_zero():
    result = subprocess.run(
        [sys.executable, _SCRIPT, "--dry-run"] + _REQUIRED_FLAGS,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"Expected exit 0 on dry-run, got {result.returncode}\n{result.stderr}"
    )
    assert "DRY" in result.stdout.upper(), f"Expected 'DRY RUN' in stdout, got: {result.stdout!r}"


def test_allow_path_exits_zero():
    """mock check_completion_claim returning allow=True → exit 0."""
    if str(_REPO_ROOT) not in sys.path:
        sys.path.insert(0, str(_REPO_ROOT))

    import importlib
    import scripts.check_claim as check_claim_mod

    mock_result = SimpleNamespace(allow=True, reasons=[])

    with patch("scripts.check_claim.sys.argv", ["check_claim.py"] + _REQUIRED_FLAGS):
        with patch.dict(
            "sys.modules",
            {
                "src.governance.gatekeeper": MagicMock(
                    check_completion_claim=MagicMock(return_value=mock_result),
                ),
            },
        ):
            exit_code = check_claim_mod.main()

    assert exit_code == 0, f"Expected exit 0 on ALLOW, got {exit_code}"


def test_deny_path_exits_one():
    """mock check_completion_claim returning allow=False with reasons → exit 1."""
    if str(_REPO_ROOT) not in sys.path:
        sys.path.insert(0, str(_REPO_ROOT))

    import scripts.check_claim as check_claim_mod

    mock_result = SimpleNamespace(allow=False, reasons=["missing store write: ceo_memory"])

    with patch("scripts.check_claim.sys.argv", ["check_claim.py"] + _REQUIRED_FLAGS):
        with patch.dict(
            "sys.modules",
            {
                "src.governance.gatekeeper": MagicMock(
                    check_completion_claim=MagicMock(return_value=mock_result),
                ),
                "src.governance.tg_alert": MagicMock(
                    alert_on_deny=MagicMock(return_value=False),
                ),
            },
        ):
            exit_code = check_claim_mod.main()

    assert exit_code == 1, f"Expected exit 1 on DENY, got {exit_code}"
