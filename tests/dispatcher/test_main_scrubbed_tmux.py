"""Phase-1 scrubbed-tmux spawn (Agency_OS-87ei).

The agent runs under `env -i` so it inherits NO .env — only the Vault bootstrap +
non-secret operational vars + recall/metadata. resolve_into_env (Nova #1289) then
pulls every credential from Vault KV. Gated off by default (rollout phase 1).
"""

from __future__ import annotations

import src.dispatcher.main as main_mod


def test_scrub_exposes_only_bootstrap_and_operational_not_creds(monkeypatch):
    """Scrub must still suppress arbitrary credentials inherited from the env.

    V1-battery carve-out (PR #1358 ANTHROPIC_API_KEY, PR #1359 DATABASE_URL +
    SUPABASE_DB_DSN, Elliot 2026-05-30): those three vars are now in
    _TMUX_OPERATIONAL_PASSTHROUGH and DO appear in the spawn command until
    api_agent_cold_start migrates to vault-resolved creds. The original
    "no DATABASE_URL / no ANTHROPIC_API_KEY" invariant is therefore stale —
    this test now asserts the scrub still suppresses credentials that are
    NOT in the carve-out (using SLACK_BOT_TOKEN as the representative —
    arbitrary non-whitelisted cred), and that the three carve-outs are
    intentionally present.
    """
    monkeypatch.setenv("VAULT_ADDR", "https://v:8200")
    monkeypatch.setenv("VAULT_TOKEN", "tok")
    monkeypatch.setenv("PATH", "/usr/bin")
    # Non-whitelisted credential — MUST remain scrubbed.
    monkeypatch.setenv("SLACK_BOT_TOKEN", "xoxb-should-be-scrubbed")

    out = main_mod._tmux_spawn_kwargs("k9", {"callsign": "atlas", "env": {"PRIOR_CONTEXT": "ctx"}})
    cmd = out["command"]

    assert cmd.startswith("env -i ")  # scrubs all inherited env
    assert "VAULT_ADDR=" in cmd and "VAULT_TOKEN=" in cmd  # bootstrap present
    assert "PATH=" in cmd  # non-secret operational passthrough (so the agent can run)
    assert "AGENT_CALLSIGN=" in cmd  # task metadata
    assert "PRIOR_CONTEXT=" in cmd  # recall block preserved through the scrub
    assert "sh -c" in cmd  # runs the agent command without sourcing a profile
    # THE P10 INVARIANT (narrowed): non-whitelisted credentials remain scrubbed.
    assert "SLACK_BOT_TOKEN" not in cmd
    assert "xoxb-should-be-scrubbed" not in cmd


def test_session_name_and_workdir_default_from_key_and_config():
    out = main_mod._tmux_spawn_kwargs("k9", {})
    assert out["session_name"] == f"{main_mod.TMUX_NAME_PREFIX}k9"
    assert out["working_dir"]  # defaulted from config
    assert main_mod.DEFAULT_AGENT_COMMAND in out["command"]  # cold-start entrypoint invoked


def test_explicit_command_is_wrapped():
    out = main_mod._tmux_spawn_kwargs("k", {"command": "claude -p run"})
    assert "claude -p run" in out["command"]
    assert out["command"].startswith("env -i ")


def test_scrub_v1_battery_carve_outs_pass_through(monkeypatch):
    """Lock the V1-battery carve-out: ANTHROPIC_API_KEY (PR #1358) +
    DATABASE_URL + SUPABASE_DB_DSN (PR #1359) intentionally pass through
    the scrub so api_agent_cold_start can read them at spawn time.

    If these stop passing through, the V1 chain breaks (Anthropic SDK loses
    its key; attribution INSERT loses its DSN). Hence this is a behaviour
    invariant, not a leak — the same env vars that the prior test was
    asserting absent are now asserted present, with a TODO to revisit when
    vault cred resolution lands in api_agent_cold_start.
    """
    monkeypatch.setenv("VAULT_ADDR", "https://v:8200")
    monkeypatch.setenv("VAULT_TOKEN", "tok")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-aud-carve-out")
    monkeypatch.setenv("DATABASE_URL", "postgresql://carve-out-dsn")
    monkeypatch.setenv("SUPABASE_DB_DSN", "postgresql://carve-out-supa")

    out = main_mod._tmux_spawn_kwargs("k", {"callsign": "atlas"})
    cmd = out["command"]
    assert "ANTHROPIC_API_KEY=" in cmd
    assert "DATABASE_URL=" in cmd
    assert "SUPABASE_DB_DSN=" in cmd


def test_scrub_flag_reflects_dispatcher_tmux_scrub_enabled_env(monkeypatch):
    """`tmux_scrub_enabled` is evaluated from `DISPATCHER_TMUX_SCRUB_ENABLED`
    at module import time. The literal default is False (unset env) — and the
    Phase-1 cutover has since flipped the env to `true` in production, so
    this test exercises the parsing logic via a reload rather than asserting
    a fixed value (the original "gated off by default" assertion went stale
    once the cutover landed).
    """
    import importlib

    # Capture the original value so we restore module state after the test.
    original = main_mod.tmux_scrub_enabled

    monkeypatch.delenv("DISPATCHER_TMUX_SCRUB_ENABLED", raising=False)
    importlib.reload(main_mod)
    assert main_mod.tmux_scrub_enabled is False

    monkeypatch.setenv("DISPATCHER_TMUX_SCRUB_ENABLED", "true")
    importlib.reload(main_mod)
    assert main_mod.tmux_scrub_enabled is True

    monkeypatch.setenv("DISPATCHER_TMUX_SCRUB_ENABLED", "garbage")
    importlib.reload(main_mod)
    assert main_mod.tmux_scrub_enabled is False  # only 1/true/yes count

    # Leave the module reflecting the originally-loaded state.
    if original:
        monkeypatch.setenv("DISPATCHER_TMUX_SCRUB_ENABLED", "true")
    else:
        monkeypatch.delenv("DISPATCHER_TMUX_SCRUB_ENABLED", raising=False)
    importlib.reload(main_mod)
