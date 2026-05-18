"""Tests for KEI-95 — Relay reconnection on reboot.

Acceptance gate: every per-callsign agent systemd unit must list both
`Requires=openclaw.service` and `After=openclaw.service` so the agent does
not start before the OpenClaw relay is up. Together with
`loginctl enable-linger elliotbot` (already-applied operator step,
documented in docs/operations/agent-systemd-recovery.md) this closes the
broken-relay-on-reboot loop.

These tests fail if any agent unit drops either directive — runtime regression
gate, not docstring promise.
"""

from __future__ import annotations

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SYSTEMD_DIR = REPO_ROOT / "infra" / "systemd" / "agents"

CALLSIGNS = ("atlas", "aiden", "elliot", "max", "nova", "orion", "scout")


@pytest.mark.parametrize("callsign", CALLSIGNS)
def test_unit_has_requires_openclaw(callsign: str) -> None:
    unit = SYSTEMD_DIR / f"{callsign}-agent.service"
    assert unit.exists(), f"{unit} missing"
    text = unit.read_text()
    assert "Requires=openclaw.service" in text, (
        f"{unit.name}: missing 'Requires=openclaw.service' (KEI-95 relay reboot gate)"
    )


@pytest.mark.parametrize("callsign", CALLSIGNS)
def test_unit_has_after_openclaw(callsign: str) -> None:
    unit = SYSTEMD_DIR / f"{callsign}-agent.service"
    text = unit.read_text()
    after_lines = [line for line in text.splitlines() if line.startswith("After=")]
    assert any("openclaw.service" in line for line in after_lines), (
        f"{unit.name}: no 'After=' line lists openclaw.service "
        f"(KEI-95 start-ordering gate). Found After= lines: {after_lines}"
    )


@pytest.mark.parametrize("callsign", CALLSIGNS)
def test_unit_orders_network_before_openclaw(callsign: str) -> None:
    """Verify network-online.target is listed before openclaw on the After= line.
    OpenClaw makes Slack API calls on startup, so it needs the network up first.
    """
    unit = SYSTEMD_DIR / f"{callsign}-agent.service"
    text = unit.read_text()
    after_line = next(
        (
            line
            for line in text.splitlines()
            if line.startswith("After=") and "openclaw.service" in line
        ),
        None,
    )
    assert after_line is not None, f"{unit.name}: no After= line containing openclaw.service"
    targets = after_line.removeprefix("After=").split()
    assert "network-online.target" in targets, (
        f"{unit.name}: After= line missing network-online.target: {after_line}"
    )
    assert targets.index("network-online.target") < targets.index("openclaw.service"), (
        f"{unit.name}: After= must order network-online.target before openclaw.service: {after_line}"
    )


def test_linger_runbook_references_loginctl() -> None:
    """KEI-95 step 3: docs must instruct operators to enable linger.
    Belt + braces — the runbook check that the operator runs
    `loginctl enable-linger elliotbot` on a new host.
    """
    doc = REPO_ROOT / "docs" / "operations" / "agent-systemd-recovery.md"
    assert doc.exists(), f"{doc} missing — recovery runbook must exist"
    text = doc.read_text()
    assert "loginctl enable-linger elliotbot" in text, (
        "agent-systemd-recovery.md must document `loginctl enable-linger elliotbot` (KEI-95 step 3)"
    )
