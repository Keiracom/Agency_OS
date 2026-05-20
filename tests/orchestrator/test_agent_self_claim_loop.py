"""Tests for scripts/orchestrator/agent_self_claim_loop.sh — KEI-92.

Strategy:
  - Provide a stub `self_assign_on_ready.py` that returns canned JSON.
  - Stub `tg` via a temp PATH dir (logs to a file we can read).
  - Redirect bash stdout to a file before kill so buffered lines survive.
  - Run the loop with --poll-seconds=1, kill after a few seconds, inspect.

Covers:
  - reason=claimed → logs `claimed <id>` line + resets READY_POSTED
  - reason=no_eligible_work → posts [READY:<callsign>] ONCE per idle streak
  - missing CALLSIGN → exits 2 with diagnostic
"""

from __future__ import annotations

import os
import signal
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
LOOP = REPO_ROOT / "scripts" / "orchestrator" / "agent_self_claim_loop.sh"


def _make_stub(tmp: Path, json_out: str) -> Path:
    stub_dir = tmp / "scripts" / "orchestrator"
    stub_dir.mkdir(parents=True, exist_ok=True)
    target = stub_dir / "self_assign_on_ready.py"
    target.write_text(f"#!/usr/bin/env python3\nprint({json_out!r})\n")
    target.chmod(0o755)
    return target


def test_missing_callsign_exits_2():
    env = {**os.environ, "CALLSIGN": ""}
    proc = subprocess.run(
        ["bash", str(LOOP)], env=env, capture_output=True, text=True, timeout=3, check=False
    )
    assert proc.returncode == 2
    assert "CALLSIGN not set" in proc.stderr


def _run_loop(tmp: Path, stub_json: str, callsign: str = "scout", seconds: float = 3.0) -> str:
    _make_stub(tmp, stub_json)
    fake_tg = tmp / "tg"
    tg_log = tmp / "tg.log"
    fake_tg.write_text(f'#!/usr/bin/env bash\necho "TG: $*" >> {tg_log}\n')
    fake_tg.chmod(0o755)
    stub_path = tmp / "scripts" / "orchestrator" / "self_assign_on_ready.py"
    env = {
        **os.environ,
        "CALLSIGN": callsign,
        "PATH": f"{tmp}:{os.environ.get('PATH', '')}",
        "POLL_SECONDS": "1",
        "ASSIGN_PATH": str(stub_path),
    }
    # Force the Slack (tg) fallback path by clearing the v2 routing flag.
    # KEI-221 (c) introduced AGENT_ROUTING_<CS>=v2 to opt into NATS; if it's
    # set in the host env, the loop would publish to NATS and never call tg.
    env.pop(f"AGENT_ROUTING_{callsign.upper()}", None)
    out_path = tmp / "loop.out"
    with out_path.open("w") as out_f:
        proc = subprocess.Popen(
            ["bash", str(LOOP), "--callsign", callsign, "--poll-seconds", "1"],
            env=env,
            cwd=str(tmp),
            stdout=out_f,
            stderr=subprocess.STDOUT,
            preexec_fn=os.setsid,
        )
        try:
            proc.wait(timeout=seconds)
        except subprocess.TimeoutExpired:
            os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
            try:
                proc.wait(timeout=2)
            except subprocess.TimeoutExpired:
                os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
    return out_path.read_text()


def test_claimed_path_logs_issue_id(tmp_path):
    out = _run_loop(tmp_path, '{"claimed": true, "reason": "claimed", "issue_id": "KEI-XYZ"}')
    assert "[self-claim-loop:scout] claimed KEI-XYZ" in out


def test_no_eligible_posts_ready_once(tmp_path):
    _run_loop(
        tmp_path,
        '{"claimed": false, "reason": "no_eligible_work", "issue_id": null}',
        seconds=4.0,
    )
    log = (tmp_path / "tg.log").read_text() if (tmp_path / "tg.log").exists() else ""
    assert log.count("[READY:scout]") == 1, f"expected 1 READY, got: {log!r}"


def test_no_eligible_routes_to_nats_when_v2_flag_set(tmp_path):
    """KEI-221 (c): with AGENT_ROUTING_SCOUT=v2, the loop must publish to NATS
    via agent_ready_emit.sh and NOT post to Slack tg."""
    _make_stub(
        tmp_path,
        '{"claimed": false, "reason": "no_eligible_work", "issue_id": null}',
    )
    fake_tg = tmp_path / "tg"
    fake_nats = tmp_path / "nats"
    tg_log = tmp_path / "tg.log"
    nats_log = tmp_path / "nats.log"
    fake_tg.write_text(f'#!/usr/bin/env bash\necho "TG: $*" >> {tg_log}\n')
    fake_nats.write_text(f'#!/usr/bin/env bash\necho "NATS: $*" >> {nats_log}\n')
    fake_tg.chmod(0o755)
    fake_nats.chmod(0o755)
    stub_path = tmp_path / "scripts" / "orchestrator" / "self_assign_on_ready.py"
    env = {
        **os.environ,
        "CALLSIGN": "scout",
        "PATH": f"{tmp_path}:{os.environ.get('PATH', '')}",
        "POLL_SECONDS": "1",
        "ASSIGN_PATH": str(stub_path),
        "AGENT_ROUTING_SCOUT": "v2",
    }
    proc = subprocess.Popen(
        ["bash", str(LOOP), "--callsign", "scout", "--poll-seconds", "1"],
        env=env,
        cwd=str(tmp_path),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        preexec_fn=os.setsid,
    )
    try:
        proc.wait(timeout=4.0)
    except subprocess.TimeoutExpired:
        os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
        try:
            proc.wait(timeout=2)
        except subprocess.TimeoutExpired:
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
    nats_text = nats_log.read_text() if nats_log.exists() else ""
    assert "pub keiracom.agent.status.scout" in nats_text, f"expected NATS pub, got: {nats_text!r}"
    assert not tg_log.exists(), "tg must NOT be called when AGENT_ROUTING_SCOUT=v2"
