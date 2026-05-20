"""Tests for scripts/agent_ready_emit.sh — KEI-221 (b)+(c).

Verifies the route-decision: AGENT_ROUTING_<CALLSIGN_UPPER>=v2 -> NATS publish,
anything else -> Slack tg. Tests use fake NATS_BIN / TG_BIN stubs so no real
network or Slack call happens.
"""

from __future__ import annotations

import stat
import subprocess
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "agent_ready_emit.sh"


def _write_capture_stub(tmp_path: Path, name: str, exit_code: int = 0) -> Path:
    """Write a bash stub that appends its $@ to <name>.log and exits exit_code."""
    stub = tmp_path / name
    log = tmp_path / f"{name}.log"
    stub.write_text(f'#!/usr/bin/env bash\nprintf "%s\\n" "$*" >> "{log}"\nexit {exit_code}\n')
    stub.chmod(stub.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return stub


def _run(env_overrides: dict[str, str], *args: str) -> subprocess.CompletedProcess:
    base = {
        "PATH": "/usr/bin:/bin",
        "AGENT_ROUTING_ATLAS": "",
        "NATS_BIN": "",
        "TG_BIN": "",
    }
    base.update(env_overrides)
    return subprocess.run(
        ["bash", str(SCRIPT), *args],
        env=base,
        capture_output=True,
        text=True,
        check=False,
    )


def test_routes_to_nats_when_flag_v2(tmp_path):
    nats = _write_capture_stub(tmp_path, "nats")
    tg = _write_capture_stub(tmp_path, "tg")
    res = _run({"AGENT_ROUTING_ATLAS": "v2", "NATS_BIN": str(nats), "TG_BIN": str(tg)}, "atlas")
    assert res.returncode == 0, res.stderr
    nats_log = (tmp_path / "nats.log").read_text()
    assert "pub keiracom.agent.status.atlas" in nats_log
    assert '"state":"ready"' in nats_log
    assert '"callsign":"atlas"' in nats_log
    assert not (tmp_path / "tg.log").exists(), "tg must NOT be called when routing=v2"


def test_routes_to_slack_when_flag_unset(tmp_path):
    nats = _write_capture_stub(tmp_path, "nats")
    tg = _write_capture_stub(tmp_path, "tg")
    res = _run({"AGENT_ROUTING_ATLAS": "", "NATS_BIN": str(nats), "TG_BIN": str(tg)}, "atlas")
    assert res.returncode == 0, res.stderr
    tg_log = (tmp_path / "tg.log").read_text()
    assert "[READY:atlas]" in tg_log
    assert not (tmp_path / "nats.log").exists(), "nats must NOT be called when routing unset"


def test_routes_to_slack_when_flag_not_v2(tmp_path):
    nats = _write_capture_stub(tmp_path, "nats")
    tg = _write_capture_stub(tmp_path, "tg")
    res = _run({"AGENT_ROUTING_ATLAS": "v1", "NATS_BIN": str(nats), "TG_BIN": str(tg)}, "atlas")
    assert res.returncode == 0, res.stderr
    assert (tmp_path / "tg.log").exists()
    assert not (tmp_path / "nats.log").exists()


def test_callsign_case_normalised_to_lower(tmp_path):
    nats = _write_capture_stub(tmp_path, "nats")
    tg = _write_capture_stub(tmp_path, "tg")
    res = _run({"AGENT_ROUTING_ATLAS": "v2", "NATS_BIN": str(nats), "TG_BIN": str(tg)}, "ATLAS")
    assert res.returncode == 0, res.stderr
    nats_log = (tmp_path / "nats.log").read_text()
    assert "pub keiracom.agent.status.atlas" in nats_log


def test_fails_when_callsign_missing(tmp_path):
    res = _run(
        {},
    )
    assert res.returncode == 2
    assert "usage" in res.stderr.lower()


def test_nats_failure_propagates_exit_code(tmp_path):
    nats = _write_capture_stub(tmp_path, "nats", exit_code=7)
    tg = _write_capture_stub(tmp_path, "tg")
    res = _run({"AGENT_ROUTING_ATLAS": "v2", "NATS_BIN": str(nats), "TG_BIN": str(tg)}, "atlas")
    assert res.returncode == 7


def test_slack_failure_is_swallowed_fail_open(tmp_path):
    """Legacy Slack path is fail-open — must NOT propagate tg's non-zero exit."""
    nats = _write_capture_stub(tmp_path, "nats")
    tg = _write_capture_stub(tmp_path, "tg", exit_code=9)
    res = _run({"AGENT_ROUTING_ATLAS": "", "NATS_BIN": str(nats), "TG_BIN": str(tg)}, "atlas")
    assert res.returncode == 0


def test_flag_only_affects_matching_callsign(tmp_path):
    """AGENT_ROUTING_ATLAS=v2 must NOT route ORION via NATS."""
    nats = _write_capture_stub(tmp_path, "nats")
    tg = _write_capture_stub(tmp_path, "tg")
    res = _run({"AGENT_ROUTING_ATLAS": "v2", "NATS_BIN": str(nats), "TG_BIN": str(tg)}, "orion")
    assert res.returncode == 0
    assert not (tmp_path / "nats.log").exists()
    assert (tmp_path / "tg.log").exists()
