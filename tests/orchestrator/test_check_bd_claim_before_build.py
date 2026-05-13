"""Tests for KEI-22 D5 — Beads hard-block on no-claim-execution.

scripts/orchestrator/check_bd_claim_before_build.py — PreToolUse hook gate.

Pure decision function `decide(...)` is injectable; tests don't shell out
to real `bd`. CLI `main()` is also tested with stdin injection.
"""

from __future__ import annotations

import importlib.util
import io
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPT = REPO_ROOT / "scripts" / "orchestrator" / "check_bd_claim_before_build.py"
_spec = importlib.util.spec_from_file_location("check_bd_claim_before_build", SCRIPT)
mod = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
sys.modules["check_bd_claim_before_build"] = mod
_spec.loader.exec_module(mod)


def _valid_claim(callsign: str = "orion", id_: str = "Agency_OS-khf3an") -> dict:
    return {
        "id": id_,
        "title": "KEI-22 — Linear ↔ Beads bidirectional sync",
        "status": "in_progress",
        "assignee": callsign,
        "external": "https://linear.app/keiracom/issue/KEI-22/sync",
    }


# ─── Read-only tools always pass ───────────────────────────────────────


def test_read_tool_always_allowed_even_without_claim():
    result = mod.decide(
        tool="Read",
        tool_input={"file_path": "/tmp/foo"},
        callsign="orion",
        bd_fn=lambda: [],  # no claims at all
        bd_available=True,
    )
    assert result["decision"] == "allow"
    assert result["reason"] == "read_only_tool"
    assert result["exit_code"] == 0


def test_grep_tool_always_allowed():
    result = mod.decide(
        tool="Grep",
        tool_input={"pattern": "x"},
        callsign="orion",
        bd_fn=lambda: [],
        bd_available=True,
    )
    assert result["decision"] == "allow"


def test_bash_readonly_command_passes():
    """Bash 'git status' / 'git log' / 'git diff' / 'cat' / 'ls' must pass."""
    for cmd in ("git status", "git log -1", "git diff origin/main", "ls scripts/", "cat README.md"):
        result = mod.decide(
            tool="Bash",
            tool_input={"command": cmd},
            callsign="orion",
            bd_fn=lambda: [],
            bd_available=True,
        )
        assert result["decision"] == "allow", f"read-only bash should pass: {cmd!r}"


# ─── Write tools — valid claim allows ──────────────────────────────────


def test_write_tool_with_valid_claim_allowed():
    result = mod.decide(
        tool="Write",
        tool_input={"file_path": "/x"},
        callsign="orion",
        bd_fn=lambda: [_valid_claim("orion")],
        bd_available=True,
    )
    assert result["decision"] == "allow"
    assert result["reason"] == "claim_valid"
    assert result["claim"]["id"] == "Agency_OS-khf3an"


def test_edit_tool_with_valid_claim_allowed():
    result = mod.decide(
        tool="Edit",
        tool_input={"file_path": "/x", "old_string": "a", "new_string": "b"},
        callsign="orion",
        bd_fn=lambda: [_valid_claim("orion")],
        bd_available=True,
    )
    assert result["decision"] == "allow"


def test_bash_git_commit_with_valid_claim_allowed():
    result = mod.decide(
        tool="Bash",
        tool_input={"command": "git commit -m 'feat: x'"},
        callsign="orion",
        bd_fn=lambda: [_valid_claim("orion")],
        bd_available=True,
    )
    assert result["decision"] == "allow"


# ─── Write tools — NO claim hard-blocks ────────────────────────────────


def test_write_tool_with_no_claim_hard_blocks():
    result = mod.decide(
        tool="Write",
        tool_input={"file_path": "/x"},
        callsign="orion",
        bd_fn=lambda: [],  # no claims
        bd_available=True,
    )
    assert result["decision"] == "block"
    assert result["reason"] == "no_claim_hard_block"
    assert result["exit_code"] == 1


def test_bash_git_push_with_no_claim_blocks():
    result = mod.decide(
        tool="Bash",
        tool_input={"command": "git push -u origin orion/foo"},
        callsign="orion",
        bd_fn=lambda: [],
        bd_available=True,
    )
    assert result["decision"] == "block"
    assert result["exit_code"] == 1


def test_gh_pr_create_with_no_claim_blocks():
    result = mod.decide(
        tool="Bash",
        tool_input={"command": "gh pr create --title x --body y"},
        callsign="orion",
        bd_fn=lambda: [],
        bd_available=True,
    )
    assert result["decision"] == "block"


# ─── Peer's claim is NOT mine (Pattern A: no poach) ────────────────────


def test_peer_claim_does_not_satisfy_my_callsign():
    """Issue assigned to atlas does NOT let orion write. Same Pattern A
    semantics as the self-assign hook PR #817."""
    result = mod.decide(
        tool="Write",
        tool_input={"file_path": "/x"},
        callsign="orion",
        bd_fn=lambda: [_valid_claim("atlas")],  # atlas's claim, not orion's
        bd_available=True,
    )
    assert result["decision"] == "block"


# ─── status != in_progress fails ───────────────────────────────────────


def test_claim_with_wrong_status_fails():
    item = _valid_claim("orion")
    item["status"] = "open"  # not yet started
    result = mod.decide(
        tool="Write",
        tool_input={"file_path": "/x"},
        callsign="orion",
        bd_fn=lambda: [item],
        bd_available=True,
    )
    assert result["decision"] == "block"


def test_closed_claim_does_not_count():
    item = _valid_claim("orion")
    item["status"] = "closed"
    result = mod.decide(
        tool="Edit",
        tool_input={"file_path": "/x", "old_string": "a", "new_string": "b"},
        callsign="orion",
        bd_fn=lambda: [item],
        bd_available=True,
    )
    assert result["decision"] == "block"


# ─── Linear-sourced check (external must contain linear.app) ───────────


def test_non_linear_sourced_claim_does_not_satisfy():
    """Dave standing rule: 'Linear is the only source of work.' A bd-only
    task (no Linear external-ref) does NOT satisfy the claim check."""
    item = _valid_claim("orion")
    item["external"] = ""  # bd-only, not Linear-sourced
    result = mod.decide(
        tool="Write",
        tool_input={"file_path": "/x"},
        callsign="orion",
        bd_fn=lambda: [item],
        bd_available=True,
    )
    assert result["decision"] == "block"


def test_github_external_ref_does_not_count():
    """An external-ref pointing at a GitHub issue (not Linear) should not
    satisfy — Dave rule is Linear-only."""
    item = _valid_claim("orion")
    item["external"] = "https://github.com/Keiracom/Agency_OS/issues/42"
    result = mod.decide(
        tool="Write",
        tool_input={"file_path": "/x"},
        callsign="orion",
        bd_fn=lambda: [item],
        bd_available=True,
    )
    assert result["decision"] == "block"


# ─── Pattern A: bd-down soft-allows ────────────────────────────────────


def test_bd_unavailable_soft_allows_write():
    """If bd binary is missing or unreachable, the gate degrades-soft:
    allow with reason='bd_unavailable_soft_allow'. Pattern A teaching —
    do NOT cascade an infra outage into a build outage."""
    result = mod.decide(
        tool="Write",
        tool_input={"file_path": "/x"},
        callsign="orion",
        bd_fn=lambda: [],
        bd_available=False,
    )
    assert result["decision"] == "allow"
    assert result["reason"] == "bd_unavailable_soft_allow"


# ─── Block payload structure ───────────────────────────────────────────


def test_block_payload_includes_chain_and_fix():
    payload = mod.block_payload("orion", "Write")
    assert payload["decision"] == "block"
    assert "KEI-22 D5" in payload["rule"]
    assert "callsign='orion'" in payload["reason"]
    assert payload["tool_blocked"] == "Write"
    assert isinstance(payload["chain_required"], list)
    assert any("bd update" in step for step in payload["chain_required"])
    assert "bd update" in payload["fix"]


# ─── CLI main() with stdin ─────────────────────────────────────────────


def test_main_allow_on_read_op(monkeypatch, capsys):
    """Read op → exit 0, no stderr."""
    monkeypatch.setattr(
        "sys.stdin",
        io.StringIO(json.dumps({"tool": "Read", "tool_input": {"file_path": "/x"}})),
    )
    rc = mod.main(["--callsign", "orion"])
    assert rc == 0
    err = capsys.readouterr().err
    assert err == ""


def test_main_blocks_write_with_no_claim(monkeypatch, capsys):
    monkeypatch.setattr(
        "sys.stdin",
        io.StringIO(json.dumps({"tool": "Write", "tool_input": {"file_path": "/x"}})),
    )
    # Force bd_unavailable=False by injecting an empty bd response.
    monkeypatch.setattr(mod, "_bd_list", lambda _bd: [])
    monkeypatch.setattr(mod.shutil, "which", lambda _bin: "/usr/bin/bd")  # bd exists
    rc = mod.main(["--callsign", "orion"])
    assert rc == 1
    err_payload = json.loads(capsys.readouterr().err)
    assert err_payload["decision"] == "block"
    assert err_payload["tool_blocked"] == "Write"


def test_main_malformed_stdin_soft_allows(monkeypatch):
    monkeypatch.setattr("sys.stdin", io.StringIO("{not json"))
    rc = mod.main(["--callsign", "orion"])
    assert rc == 0  # never crash the hook chain


def test_main_empty_stdin_soft_allows(monkeypatch):
    monkeypatch.setattr("sys.stdin", io.StringIO(""))
    # isatty defaults False under StringIO; empty body parsed as {} → tool="" → read_only path
    rc = mod.main(["--callsign", "orion"])
    assert rc == 0
