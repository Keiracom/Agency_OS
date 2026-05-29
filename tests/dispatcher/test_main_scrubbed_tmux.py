"""Phase-1 scrubbed-tmux spawn (Agency_OS-87ei).

The agent runs under `env -i` so it inherits NO .env — only the Vault bootstrap +
non-secret operational vars + recall/metadata. resolve_into_env (Nova #1289) then
pulls every credential from Vault KV. Gated off by default (rollout phase 1).
"""

from __future__ import annotations

import src.dispatcher.main as main_mod


def test_scrub_exposes_only_bootstrap_and_operational_not_creds(monkeypatch):
    monkeypatch.setenv("VAULT_ADDR", "https://v:8200")
    monkeypatch.setenv("VAULT_TOKEN", "tok")
    monkeypatch.setenv("PATH", "/usr/bin")
    monkeypatch.setenv("DATABASE_URL", "postgresql://should-be-scrubbed")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-should-be-scrubbed")

    out = main_mod._tmux_spawn_kwargs("k9", {"callsign": "atlas", "env": {"PRIOR_CONTEXT": "ctx"}})
    cmd = out["command"]

    assert cmd.startswith("env -i ")  # scrubs all inherited env
    assert "VAULT_ADDR=" in cmd and "VAULT_TOKEN=" in cmd  # bootstrap present
    assert "PATH=" in cmd  # non-secret operational passthrough (so the agent can run)
    assert "AGENT_CALLSIGN=" in cmd  # task metadata
    assert "PRIOR_CONTEXT=" in cmd  # recall block preserved through the scrub
    assert "sh -c" in cmd  # runs the agent command without sourcing a profile
    # THE P10 INVARIANT: credentials are NOT exposed to the agent process.
    assert "DATABASE_URL" not in cmd
    assert "ANTHROPIC_API_KEY" not in cmd


def test_session_name_and_workdir_default_from_key_and_config():
    out = main_mod._tmux_spawn_kwargs("k9", {})
    assert out["session_name"] == f"{main_mod.TMUX_NAME_PREFIX}k9"
    assert out["working_dir"]  # defaulted from config
    assert main_mod.DEFAULT_AGENT_COMMAND in out["command"]  # cold-start entrypoint invoked


def test_explicit_command_is_wrapped():
    out = main_mod._tmux_spawn_kwargs("k", {"command": "claude -p run"})
    assert "claude -p run" in out["command"]
    assert out["command"].startswith("env -i ")


def test_scrub_gated_off_by_default():
    # Rollout phase 1: tmux spawns are NOT scrubbed unless explicitly enabled, so
    # existing (non-ephemeral) tmux callers are unchanged.
    assert main_mod.tmux_scrub_enabled is False
