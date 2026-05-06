"""GOV-PHASE3 — TG alert helper tests."""

from __future__ import annotations

from unittest.mock import patch, MagicMock

from src.governance.tg_alert import alert_on_deny


def _ok_subproc() -> MagicMock:
    proc = MagicMock()
    proc.returncode = 0
    proc.stdout = ""
    proc.stderr = ""
    return proc


def test_alert_returns_true_on_relay_success() -> None:
    with (
        patch("shutil.which", return_value="/usr/bin/tg"),
        patch("subprocess.run", return_value=_ok_subproc()) as run,
    ):
        ok = alert_on_deny(
            callsign="aiden",
            directive_id="SYNTH-3",
            reasons=["G1 fail", "G2 fail"],
            claim_text_sha256_16="abc1234567890def",
        )
    assert ok is True
    args, kwargs = run.call_args
    cmd = args[0]
    assert cmd[0] == "tg"
    assert cmd[1] == "-g"
    msg = cmd[2]
    assert "[GATEKEEPER-DENY:aiden]" in msg
    assert "directive=SYNTH-3" in msg
    assert "claim_hash=abc1234567890def" in msg
    assert "G1 fail" in msg and "G2 fail" in msg


def test_alert_returns_false_when_tg_missing() -> None:
    with patch("shutil.which", return_value=None):
        ok = alert_on_deny(
            callsign="aiden",
            directive_id="X",
            reasons=[],
            claim_text_sha256_16="0" * 16,
        )
    assert ok is False


def test_alert_returns_false_on_subprocess_error() -> None:
    with (
        patch("shutil.which", return_value="/usr/bin/tg"),
        patch("subprocess.run", side_effect=OSError("relay down")),
    ):
        ok = alert_on_deny(
            callsign="aiden",
            directive_id="X",
            reasons=["G3"],
            claim_text_sha256_16="0" * 16,
        )
    assert ok is False


def test_alert_handles_empty_reasons() -> None:
    with (
        patch("shutil.which", return_value="/usr/bin/tg"),
        patch("subprocess.run", return_value=_ok_subproc()) as run,
    ):
        alert_on_deny(
            callsign="aiden",
            directive_id="X",
            reasons=[],
            claim_text_sha256_16="0" * 16,
        )
    msg = run.call_args[0][0][2]
    assert "(no reasons reported)" in msg
