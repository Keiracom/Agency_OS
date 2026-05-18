"""env_schema_validate.sh — fail-fast critical-5 env vars (Agency_OS-9erxio).

Dispatch (Elliot 2026-05-18): "Identify the 5 most critical env vars and add
hook script that exits non-zero if any missing — registered in session-start
hook chain. Acceptance: missing var blocks session start with clear error."

Critical-5:
  - DATABASE_URL or SUPABASE_DB_URL
  - SLACK_BOT_TOKEN
  - ANTHROPIC_API_KEY
  - OPENAI_API_KEY
  - CALLSIGN
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT = REPO_ROOT / "scripts" / "hooks" / "env_schema_validate.sh"

FULL_ENV = {
    "DATABASE_URL": "postgresql://u:p@h:5432/db",
    "SLACK_BOT_TOKEN": "xoxb-fake",
    "ANTHROPIC_API_KEY": "sk-ant-fake",
    "OPENAI_API_KEY": "sk-openai-fake",
    "CALLSIGN": "orion",
    "ENV_VALIDATE_SKIP_SOURCE": "1",  # tests must not depend on real .env
    "PATH": "/usr/bin:/bin",
}


def _run(env_overrides: dict[str, str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", str(SCRIPT)],
        env=env_overrides,
        capture_output=True,
        text=True,
        timeout=10,
    )


# ---------------------------------------------------------------------------
# Happy path: all 5 present
# ---------------------------------------------------------------------------


def test_all_five_present_exits_zero() -> None:
    result = _run(FULL_ENV)
    assert result.returncode == 0, (
        f"exit={result.returncode}, stderr={result.stderr!r}, stdout={result.stdout!r}"
    )
    assert result.stderr == ""


def test_supabase_db_url_substitutes_for_database_url() -> None:
    env = dict(FULL_ENV)
    del env["DATABASE_URL"]
    env["SUPABASE_DB_URL"] = "postgresql://u:p@h:5432/db"
    result = _run(env)
    assert result.returncode == 0, result.stderr


# ---------------------------------------------------------------------------
# Negative path: each missing var blocks
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "drop_keys,expected_in_stderr",
    [
        (["DATABASE_URL"], "DATABASE_URL"),
        (["SLACK_BOT_TOKEN"], "SLACK_BOT_TOKEN"),
        (["ANTHROPIC_API_KEY"], "ANTHROPIC_API_KEY"),
        (["OPENAI_API_KEY"], "OPENAI_API_KEY"),
        (["CALLSIGN"], "CALLSIGN"),
    ],
)
def test_single_missing_var_blocks(drop_keys: list[str], expected_in_stderr: str) -> None:
    env = {k: v for k, v in FULL_ENV.items() if k not in drop_keys}
    result = _run(env)
    assert result.returncode == 1, (
        f"expected exit 1 with {drop_keys} missing; got {result.returncode}"
    )
    assert expected_in_stderr in result.stderr, (
        f"stderr should name the missing var: {result.stderr!r}"
    )
    assert "critical env var" in result.stderr


def test_db_url_either_name_required() -> None:
    # Drop both DB names — should fail with DATABASE_URL in the list.
    env = {k: v for k, v in FULL_ENV.items() if k not in ("DATABASE_URL", "SUPABASE_DB_URL")}
    result = _run(env)
    assert result.returncode == 1
    assert "DATABASE_URL" in result.stderr or "SUPABASE_DB_URL" in result.stderr


def test_all_five_missing_lists_all_five() -> None:
    env = {"PATH": "/usr/bin:/bin", "ENV_VALIDATE_SKIP_SOURCE": "1"}
    result = _run(env)
    assert result.returncode == 1
    # Each critical var (or its acceptable alternative) should be named.
    for token in (
        "DATABASE_URL",
        "SLACK_BOT_TOKEN",
        "ANTHROPIC_API_KEY",
        "OPENAI_API_KEY",
        "CALLSIGN",
    ):
        assert token in result.stderr, f"stderr should name '{token}'; got {result.stderr!r}"


def test_empty_string_treated_as_missing() -> None:
    # Empty-string env vars are common after a botched secret rotation and
    # should be rejected just like unset ones.
    env = dict(FULL_ENV)
    env["SLACK_BOT_TOKEN"] = ""
    result = _run(env)
    assert result.returncode == 1
    assert "SLACK_BOT_TOKEN" in result.stderr


# ---------------------------------------------------------------------------
# Auto-source from .env fallback
# ---------------------------------------------------------------------------


def test_auto_sources_env_file_when_vars_missing(tmp_path: Path) -> None:
    env_file = tmp_path / "agency-os.env"
    env_file.write_text(
        "DATABASE_URL=postgresql://from-envfile@h/db\n"
        "SLACK_BOT_TOKEN=xoxb-from-envfile\n"
        "ANTHROPIC_API_KEY=sk-ant-from-envfile\n"
        "OPENAI_API_KEY=sk-openai-from-envfile\n"
        "CALLSIGN=fromenvfile\n"
    )
    # Calling shell has NONE of the critical vars; helper should source the file.
    env = {"PATH": "/usr/bin:/bin", "AGENCY_OS_ENV": str(env_file)}
    result = _run(env)
    assert result.returncode == 0, f"stderr={result.stderr!r}"


# ---------------------------------------------------------------------------
# DRY mode + script syntax
# ---------------------------------------------------------------------------


def test_dry_mode_lists_critical_five_and_exits_zero() -> None:
    env = {"PATH": "/usr/bin:/bin", "ENV_VALIDATE_DRY": "1"}
    result = _run(env)
    assert result.returncode == 0
    body = result.stdout
    for token in (
        "DATABASE_URL",
        "SUPABASE_DB_URL",
        "SLACK_BOT_TOKEN",
        "ANTHROPIC_API_KEY",
        "OPENAI_API_KEY",
        "CALLSIGN",
    ):
        assert token in body, f"DRY mode should list '{token}'; got {body!r}"


def test_script_syntax_valid() -> None:
    result = subprocess.run(["bash", "-n", str(SCRIPT)], capture_output=True, text=True, timeout=5)
    assert result.returncode == 0, result.stderr


# ---------------------------------------------------------------------------
# Hook is registered FIRST in the SessionStart chain
# ---------------------------------------------------------------------------


def test_hook_registered_first_in_session_start_chain() -> None:
    settings = json.loads((REPO_ROOT / ".claude" / "settings.json").read_text())
    session_start = settings["hooks"]["SessionStart"]
    # Find the "*" matcher block — the primary chain.
    primary = next(b for b in session_start if b.get("matcher") == "*")
    first_cmd = primary["hooks"][0]["command"]
    assert "env_schema_validate.sh" in first_cmd, (
        f"env_schema_validate.sh must be FIRST in the SessionStart * chain so "
        f"misconfigured env fails fast; got {first_cmd!r}"
    )
