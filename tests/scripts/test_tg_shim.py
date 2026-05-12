"""Tests for scripts/tg — Slack relay shim (callsign-fix Phase 2).

Verifies:
    - CLI flag translation (-g, -d prime, -d clone reject, -c, no-flag default)
    - stdin pipe pass-through
    - exit code propagation from slack_relay.py
    - callsign attribution preserved (via slack_relay.py, not re-prepended in tg)
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from importlib.machinery import SourceFileLoader
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_TG = _REPO_ROOT / "scripts" / "tg"


def _load_tg():
    # tg has no .py suffix; bypass extension-based loader detection.
    loader = SourceFileLoader("tg_shim", str(_TG))
    spec = importlib.util.spec_from_loader("tg_shim", loader)
    assert spec is not None
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


def test_translate_group_flag():
    tg = _load_tg()
    assert tg.translate(["-g", "hello"], "elliot") == ["-g", "hello"]


def test_translate_dm_prime_routes_to_ceo():
    tg = _load_tg()
    for callsign in ("elliot", "aiden", "enforcer", "max"):
        assert tg.translate(["-d", "msg"], callsign) == ["-c", "ceo", "msg"], callsign


def test_translate_dm_clone_rejects_with_exit_2(capsys):
    """Clones (atlas/orion/scout) have no DM privileges — -d must reject.

    Falling back to #execution silently was the original PR #712 behaviour;
    today's contract (Elliot dispatch 2026-05-12, concurred ts 1778544356.893729)
    is explicit rejection so the operator sees the intent mismatch.
    """
    tg = _load_tg()
    for callsign in ("atlas", "orion", "scout"):
        with pytest.raises(SystemExit) as exc:
            tg.translate(["-d", "msg"], callsign)
        assert exc.value.code == 2, callsign
        err = capsys.readouterr().err
        assert "not supported for clone callsign" in err, callsign
        assert callsign in err, callsign


def test_translate_channel_flag_named_and_id():
    tg = _load_tg()
    assert tg.translate(["-c", "alerts", "msg"], "elliot") == ["-c", "alerts", "msg"]
    assert tg.translate(["-c", "C0B3QB0K1GQ", "msg"], "elliot") == ["-c", "C0B3QB0K1GQ", "msg"]


def test_translate_default_passes_message_through():
    tg = _load_tg()
    assert tg.translate(["hello", "world"], "elliot") == ["hello", "world"]


def test_translate_channel_flag_requires_argument(capsys):
    tg = _load_tg()
    with pytest.raises(SystemExit) as exc:
        tg.translate(["-c"], "elliot")
    assert exc.value.code == 2
    err = capsys.readouterr().err
    assert "-c requires" in err


def test_subprocess_propagates_relay_exit_code(tmp_path):
    """End-to-end: tg invokes slack_relay.py via subprocess; exit codes flow back.

    Uses a temporary fake slack_relay.py adjacent to a temp tg copy so we never
    touch the real Slack API. Confirms tg returns whatever the relay returns.
    """
    fake_relay = tmp_path / "slack_relay.py"
    fake_relay.write_text("import sys\nsys.stderr.write(' '.join(sys.argv[1:]))\nsys.exit(42)\n")
    tg_copy = tmp_path / "tg"
    tg_copy.write_text(_TG.read_text())
    tg_copy.chmod(0o755)
    result = subprocess.run(
        [sys.executable, str(tg_copy), "-g", "hi"],
        capture_output=True,
        text=True,
        env={"CALLSIGN": "atlas", "PATH": "/usr/bin:/bin"},
    )
    assert result.returncode == 42, result.stderr
    assert "-g hi" in result.stderr


def test_subprocess_stdin_passthrough(tmp_path):
    """`echo msg | tg` should reach slack_relay.py stdin unchanged."""
    fake_relay = tmp_path / "slack_relay.py"
    fake_relay.write_text(
        "import sys\n"
        "data = sys.stdin.read()\n"
        "sys.stderr.write(f'STDIN={data!r}')\n"
        "sys.exit(0 if data.strip() else 7)\n"
    )
    tg_copy = tmp_path / "tg"
    tg_copy.write_text(_TG.read_text())
    tg_copy.chmod(0o755)
    result = subprocess.run(
        [sys.executable, str(tg_copy)],
        input="piped message\n",
        capture_output=True,
        text=True,
        env={"CALLSIGN": "elliot", "PATH": "/usr/bin:/bin"},
    )
    assert result.returncode == 0, result.stderr
    assert "piped message" in result.stderr
