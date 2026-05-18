"""KEI-125 — tests for scripts/agent_failover_notify.sh.

Tests via subprocess. Three branches:
  1. NRestarts=0 (first boot)  → silent exit 0, no Slack call
  2. NRestarts=N (failover)    → Slack POST issued + log emitted
  3. SLACK_BOT_TOKEN missing   → silent exit 0 with warning, no Slack call

We mock systemctl by PATH-prefixing a fake binary that returns canned
NRestarts. curl is similarly stubbed so we don't hit live Slack.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "agent_failover_notify.sh"


def _make_fake_bin(tmp_path: Path, *, n_restarts: str, slack_response: str) -> Path:
    """Build a tmp bin/ dir with fake `systemctl` + `curl` so PATH override
    intercepts both binaries the script invokes."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir(exist_ok=True)

    # Fake systemctl: respond to `show <unit> --property=NRestarts --value` with
    # canned value; everything else exits 1.
    systemctl = bin_dir / "systemctl"
    systemctl.write_text(
        f"""#!/usr/bin/env bash
for arg in "$@"; do
    if [[ "$arg" == "--property=NRestarts" ]]; then
        echo '{n_restarts}'
        exit 0
    fi
done
exit 1
"""
    )
    systemctl.chmod(0o755)

    # Fake curl: log the body to a file then echo the canned slack response.
    curl = bin_dir / "curl"
    curl.write_text(
        f"""#!/usr/bin/env bash
# Capture the JSON body to /tmp for assertion if -d came in.
for ((i=1; i<=$#; i++)); do
    if [[ "${{!i}}" == "-d" ]]; then
        next=$((i+1))
        echo "${{!next}}" > "{tmp_path}/curl_body"
    fi
done
echo '{slack_response}'
exit 0
"""
    )
    curl.chmod(0o755)
    return bin_dir


def _run(
    tmp_path: Path,
    *,
    n_restarts: str,
    callsign: str = "ATLAS",
    delay: str = "0",
    slack_token: str | None = "xoxb-test-token",
    slack_response: str = '{"ok":true,"channel":"C09M2HE8XXX"}',
) -> subprocess.CompletedProcess:
    bin_dir = _make_fake_bin(tmp_path, n_restarts=n_restarts, slack_response=slack_response)
    env = {k: v for k, v in os.environ.items() if k not in {"SLACK_BOT_TOKEN", "PATH"}}
    env["PATH"] = f"{bin_dir}:/usr/bin:/bin"
    if slack_token:
        env["SLACK_BOT_TOKEN"] = slack_token
    return subprocess.run(
        ["bash", str(SCRIPT), callsign, delay],
        env=env,
        capture_output=True,
        text=True,
    )


# ─── branch 1: first boot — NRestarts=0 ────────────────────────────────────


def test_silent_on_first_boot(tmp_path):
    """NRestarts=0 → no #ceo post, no curl call, exit 0."""
    result = _run(tmp_path, n_restarts="0")
    assert result.returncode == 0
    # No curl body captured = curl never invoked.
    assert not (tmp_path / "curl_body").exists(), (
        f"curl should not run on first boot; stderr={result.stderr!r}"
    )


# ─── branch 2: failover — NRestarts>0 → post to #ceo ──────────────────────


def test_posts_to_ceo_on_failover(tmp_path):
    result = _run(tmp_path, n_restarts="3", callsign="ATLAS")
    assert result.returncode == 0, result.stderr
    body_file = tmp_path / "curl_body"
    assert body_file.exists(), (
        f"curl should have run on failover; stdout={result.stdout!r} stderr={result.stderr!r}"
    )
    body = body_file.read_text()
    assert "ATLAS" in body
    assert "restart #3" in body
    assert "C09M2HE8XXX" in body  # default ceo channel


def test_failover_log_emitted_on_success(tmp_path):
    """stdout includes a success line per the script logger."""
    result = _run(tmp_path, n_restarts="2")
    assert "posted #ceo failover notice" in result.stdout
    assert "ATLAS" in result.stdout
    assert "restart #2" in result.stdout


# ─── branch 3: missing SLACK_BOT_TOKEN ─────────────────────────────────────


def test_silent_when_slack_token_missing(tmp_path):
    """SLACK_BOT_TOKEN unset → warn + skip, no Slack call, fail-open exit 0."""
    result = _run(tmp_path, n_restarts="5", slack_token=None)
    assert result.returncode == 0
    assert not (tmp_path / "curl_body").exists()
    assert "SLACK_BOT_TOKEN unset" in result.stderr


# ─── branch 4: Slack POST returned non-ok JSON ─────────────────────────────


def test_warns_on_slack_failure(tmp_path):
    """Slack response without ok:true → warning logged, fail-open exit 0.
    The agent service should NOT be blocked by Slack outages."""
    result = _run(
        tmp_path,
        n_restarts="1",
        slack_response='{"ok":false,"error":"channel_not_found"}',
    )
    assert result.returncode == 0
    assert (tmp_path / "curl_body").exists()
    assert "Slack post failed" in result.stderr


# ─── branch 5: empty callsign / missing arg ────────────────────────────────


def test_fails_when_callsign_missing(tmp_path):
    """Empty positional arg → script exits non-zero with usage hint."""
    bin_dir = _make_fake_bin(tmp_path, n_restarts="0", slack_response="{}")
    env = {k: v for k, v in os.environ.items() if k not in {"PATH"}}
    env["PATH"] = f"{bin_dir}:/usr/bin:/bin"
    result = subprocess.run(
        ["bash", str(SCRIPT)],
        env=env,
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    assert "usage" in result.stderr.lower()


# ─── branch 6: NRestarts read from systemctl that returns empty ────────────


def test_treats_empty_nrestarts_as_zero(tmp_path):
    """systemctl returns empty string (e.g. unit not loaded yet) → treat
    as NRestarts=0 → silent. This is the fail-open boot-race shape."""
    result = _run(tmp_path, n_restarts="")
    assert result.returncode == 0
    assert not (tmp_path / "curl_body").exists()
