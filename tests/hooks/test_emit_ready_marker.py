"""Tests for scripts/hooks/emit_ready_marker.sh (Stop-hook auto-[READY:] marker).

Verifies the five behaviours Scout's design at docs/wave2/stop_hook_design.md
calls out as must-pass:

  1. Empty / missing payload -> exit 0, no emit (fail-open).
  2. Body already contains [READY:<callsign>] -> skip emit (de-dup).
  3. Body missing [READY:<callsign>] -> emit fires.
  4. Sub-agent (CLAUDE_AGENT_ID set) -> skip emit.
  5. Tg-cli unavailable -> exit 0 cleanly (fail-open).

Each test spawns the hook script in a subprocess with a stubbed PATH so the
'tg' / slack_relay invocation is observable but does not actually hit Slack.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
HOOK = REPO_ROOT / "scripts" / "hooks" / "emit_ready_marker.sh"


def _run_hook(
    payload: str | None,
    callsign: str = "aiden",
    agent_id: str | None = None,
    tg_available: bool = True,
    tmp_path: Path | None = None,
) -> tuple[int, str, str]:
    """Run the hook with a fake tg shim. Return (exit, stdout, tg_log)."""
    assert tmp_path is not None
    shim_dir = tmp_path / "bin"
    shim_dir.mkdir(parents=True, exist_ok=True)
    tg_log = tmp_path / "tg_invocations.log"

    if tg_available:
        tg_shim = shim_dir / "tg"
        tg_shim.write_text(f'#!/usr/bin/env bash\necho "$@" >> "{tg_log}"\nexit 0\n')
        tg_shim.chmod(0o755)

    env = os.environ.copy()
    env["CALLSIGN"] = callsign
    env["PATH"] = f"{shim_dir}:/usr/bin:/bin"
    # Isolate from any real /tmp/.stop_event_payload.json on the host so tests
    # don't see leaked state from prior Stop events.
    env["STOP_EVENT_PAYLOAD_TEMP_PATH"] = str(tmp_path / "stop_payload.json")
    if agent_id:
        env["CLAUDE_AGENT_ID"] = agent_id
    else:
        env.pop("CLAUDE_AGENT_ID", None)

    proc = subprocess.run(  # noqa: S603 — controlled args, no shell
        ["/bin/bash", str(HOOK)],
        input=payload if payload is not None else "",
        text=True,
        capture_output=True,
        env=env,
        timeout=10,
    )
    log_contents = tg_log.read_text() if tg_log.exists() else ""
    return proc.returncode, proc.stdout, log_contents


def test_empty_payload_fail_open(tmp_path: Path) -> None:
    rc, _stdout, tg_log = _run_hook("", tmp_path=tmp_path)
    assert rc == 0
    assert tg_log == ""


def test_body_already_has_ready_marker_skips_emit(tmp_path: Path) -> None:
    payload = json.dumps(
        {"last_assistant_message": "Standing.\n\n[READY:aiden]"}
    )
    rc, _stdout, tg_log = _run_hook(payload, tmp_path=tmp_path)
    assert rc == 0
    assert tg_log == ""


def test_body_missing_marker_emits(tmp_path: Path) -> None:
    payload = json.dumps(
        {"last_assistant_message": "Holding for confirm — no marker here."}
    )
    rc, _stdout, tg_log = _run_hook(payload, tmp_path=tmp_path)
    assert rc == 0
    assert "[READY:aiden]" in tg_log


def test_subagent_skips_emit(tmp_path: Path) -> None:
    payload = json.dumps({"last_assistant_message": "Done. No marker."})
    rc, _stdout, tg_log = _run_hook(
        payload, agent_id="sub_abc123", tmp_path=tmp_path
    )
    assert rc == 0
    assert tg_log == ""


def test_tg_missing_fail_open(tmp_path: Path) -> None:
    payload = json.dumps({"last_assistant_message": "Body without marker."})
    rc, _stdout, _tg_log = _run_hook(
        payload, tg_available=False, tmp_path=tmp_path
    )
    assert rc == 0


def test_case_insensitive_dedup(tmp_path: Path) -> None:
    payload = json.dumps({"last_assistant_message": "Wrap. [READY:AIDEN]"})
    rc, _stdout, tg_log = _run_hook(payload, tmp_path=tmp_path)
    assert rc == 0
    assert tg_log == ""


def test_alt_body_key_message_content(tmp_path: Path) -> None:
    payload = json.dumps(
        {"message": {"content": "Reply via alt key. [READY:aiden]"}}
    )
    rc, _stdout, tg_log = _run_hook(payload, tmp_path=tmp_path)
    assert rc == 0
    assert tg_log == ""


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
