"""tests for slack_relay.py CALLSIGN resolution + ALLOWED_CHANNELS guard.

Per Dave directive #6 (callsign bug fix 2026-05-11): slack_relay must
refuse to run without explicit CALLSIGN env or ./IDENTITY.md, and must
refuse to post to channels not in the per-callsign allowlist.

Deliberation-layer #ceo grant (2026-05-18, PR #1027): Elliot/Aiden/Max
may post to #ceo. Clones (atlas/orion/scout/nova) post to #execution
only. Nova was added explicitly as a fourth clone.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
RELAY = REPO_ROOT / "scripts" / "slack_relay.py"

CHANNEL_CEO = "C0B2PM3TV0B"
CHANNEL_EXECUTION = "C0B3QB0K1GQ"
CHANNEL_ALERTS = "C0B2EJU53EK"

# R11 CEO_FORMAT_GATE-compliant body: bold header + bullet, no banned tokens.
# Required for any #ceo positive-path test that exercises the in-repo relay.
CEO_COMPLIANT_BODY = "**Test**\n- positive path"


def _run(
    env: dict[str, str], args: list[str], cwd: Path | None = None
) -> subprocess.CompletedProcess:
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


def _build_fake_repo(tmp_path: Path, callsign: str) -> Path:
    """Stand up a minimal repo containing a copy of slack_relay.py + IDENTITY.md.

    Running the copy isolates the test from the real REPO_ROOT/IDENTITY.md
    (which is gitignored and not present in CI checkouts), and from
    src.bot_common gates (they fail to import from the fake repo and the
    relay falls through ungated). This keeps the assertion focused on
    allowlist behaviour.
    """
    fake_repo = tmp_path / "fakerepo"
    (fake_repo / "scripts").mkdir(parents=True)
    relay_copy = fake_repo / "scripts" / "slack_relay.py"
    relay_copy.write_bytes(RELAY.read_bytes())
    (fake_repo / "IDENTITY.md").write_text(f"**CALLSIGN:** {callsign}\n")
    return relay_copy


def test_callsign_resolves_from_identity_md(tmp_path: Path) -> None:
    """No CALLSIGN env + IDENTITY.md present → resolves callsign from file.

    Uses fake_repo with **CALLSIGN:** orion. Posting to #ceo from orion
    (clone, execution-only allowlist) must produce the allowlist refusal
    message tagged with the resolved callsign.
    """
    relay_copy = _build_fake_repo(tmp_path, "orion")
    result = subprocess.run(
        [sys.executable, str(relay_copy), "-c", CHANNEL_CEO, "test"],
        env={"PATH": os.environ.get("PATH", ""), "SLACK_BOT_TOKEN": "fake-token"},
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 2
    assert f"orion-relay refuses post to {CHANNEL_CEO}" in result.stderr


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


def test_aiden_can_post_ceo_after_deliberation_grant() -> None:
    """PR #1027 — aiden (deliberator/governance lens) gains #ceo access.

    Posting to #ceo from aiden worktree must NOT trip the allowlist refusal.
    The HTTP call itself will fail under fake-token (invalid_auth or URLError),
    but the specific allowlist-refusal signal must be absent.
    """
    result = _run(
        env={
            "SLACK_BOT_TOKEN": "fake-token",
            "R_VERIFY_SKIP": "1",
            "R_LAW_XV_SKIP": "1",
            "CONCUR_GATE_SKIP": "1",
            "CALLSIGN": "aiden",
        },
        args=["-c", CHANNEL_CEO, CEO_COMPLIANT_BODY],
    )
    assert f"aiden-relay refuses post to {CHANNEL_CEO}" not in result.stderr


def test_max_can_post_ceo_after_deliberation_grant() -> None:
    """PR #1027 — max (deliberator/quality lens) gains #ceo access."""
    result = _run(
        env={
            "SLACK_BOT_TOKEN": "fake-token",
            "R_VERIFY_SKIP": "1",
            "R_LAW_XV_SKIP": "1",
            "CONCUR_GATE_SKIP": "1",
            "CALLSIGN": "max",
        },
        args=["-c", CHANNEL_CEO, CEO_COMPLIANT_BODY],
    )
    assert f"max-relay refuses post to {CHANNEL_CEO}" not in result.stderr


def test_nova_can_post_execution() -> None:
    """PR #1027 — nova is now an explicit allowlist entry (execution only)."""
    result = _run(
        env={
            "SLACK_BOT_TOKEN": "fake-token",
            "R_VERIFY_SKIP": "1",
            "R_LAW_XV_SKIP": "1",
            "CONCUR_GATE_SKIP": "1",
            "CALLSIGN": "nova",
        },
        args=["-c", CHANNEL_EXECUTION, "nova execution post"],
    )
    assert f"nova-relay refuses post to {CHANNEL_EXECUTION}" not in result.stderr


def test_nova_blocked_from_ceo() -> None:
    """PR #1027 — nova is a clone; #ceo remains forbidden for clones."""
    result = _run(
        env={
            "SLACK_BOT_TOKEN": "fake-token",
            "R_VERIFY_SKIP": "1",
            "R_LAW_XV_SKIP": "1",
            "CONCUR_GATE_SKIP": "1",
            "CALLSIGN": "nova",
        },
        args=["-c", CHANNEL_CEO, CEO_COMPLIANT_BODY],
    )
    assert result.returncode == 2
    assert f"nova-relay refuses post to {CHANNEL_CEO}" in result.stderr


def test_env_callsign_overrides_identity(tmp_path: Path) -> None:
    """CALLSIGN env wins over IDENTITY.md."""
    result = _run(
        env={
            "SLACK_BOT_TOKEN": "fake-token",
            "R_VERIFY_SKIP": "1",
            "R_LAW_XV_SKIP": "1",
            "CONCUR_GATE_SKIP": "1",
            "CALLSIGN": "elliot",
        },
        args=["-c", CHANNEL_ALERTS, "alerts-block-for-elliot"],
    )
    # elliot allowlist = execution + ceo + ops + completed_directives. #alerts blocked.
    assert result.returncode == 2
    assert f"elliot-relay refuses post to {CHANNEL_ALERTS}" in result.stderr
