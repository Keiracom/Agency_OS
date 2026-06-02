"""
Contract: tests/integrations/test_agent_os_advisory.py
Purpose: Verify the ADVISORY_ONLY flag at the Agent OS integration boundary.
Layer: test
Directive: agent-os-advisory-flag (GOV-12)
"""

from __future__ import annotations

import importlib
import logging

import pytest


def _reload_with_flag(monkeypatch: pytest.MonkeyPatch, value: str | None):
    if value is None:
        monkeypatch.delenv("AGENT_OS_ADVISORY_ONLY", raising=False)
    else:
        monkeypatch.setenv("AGENT_OS_ADVISORY_ONLY", value)
    import src.integrations.agent_os as agent_os

    return importlib.reload(agent_os)


def test_default_is_advisory_only(monkeypatch: pytest.MonkeyPatch) -> None:
    """Unset env defaults to advisory (safe — never blocks)."""
    mod = _reload_with_flag(monkeypatch, None)
    assert mod.ADVISORY_ONLY is True


def test_advisory_evaluate_does_not_block(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """ADVISORY_ONLY=True: evaluate() logs + returns, never raises."""
    mod = _reload_with_flag(monkeypatch, "true")
    with caplog.at_level(logging.INFO, logger="src.integrations.agent_os"):
        verdict = mod.evaluate("tool.bash.exec", {"callsign": "nova"})
    assert verdict.allowed is True
    assert verdict.surfaced is True
    assert any("agent_os.advisory" in r.message for r in caplog.records)


def test_non_advisory_evaluate_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    """ADVISORY_ONLY=False: fail loud — enforcement belongs to Sidecar."""
    mod = _reload_with_flag(monkeypatch, "false")
    assert mod.ADVISORY_ONLY is False
    with pytest.raises(RuntimeError, match="Sidecar"):
        mod.evaluate("tool.bash.exec")
