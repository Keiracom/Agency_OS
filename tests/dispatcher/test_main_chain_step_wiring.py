"""qjl7 — CHAIN_STEP env injection at dispatcher spawn (chain envelope -> agent env).

v1_chain_orchestrator emits envelopes with ``chain_step`` (e.g. "aiden_plan").
The consumer hands that through as a top-level spawn_kwargs key; the dispatcher
must promote it to ``env['CHAIN_STEP']`` so agent_cold_start's nd3b
notify-suppression gate reads the right name. Without this wiring the generic
metadata loop would land it under ``AGENT_CHAIN_STEP`` instead.
"""

from __future__ import annotations

from src.dispatcher import main as dm

# ---------------------------------------------------------------------------
# Helper — _apply_chain_step_env
# ---------------------------------------------------------------------------


def test_apply_chain_step_env_sets_unprefixed_when_present():
    """chain_step in sk → env['CHAIN_STEP']; chain_step popped from sk so it
    won't also surface as AGENT_CHAIN_STEP downstream."""
    sk = {"chain_step": "aiden_plan", "task_id": "t-1"}
    env: dict[str, str] = {}
    dm._apply_chain_step_env(sk, env)
    assert env == {"CHAIN_STEP": "aiden_plan"}
    assert "chain_step" not in sk  # popped
    assert sk == {"task_id": "t-1"}  # other metadata intact


def test_apply_chain_step_env_no_op_when_absent():
    """No chain_step → env unchanged. Fail-open: legacy spawns must work."""
    sk = {"task_id": "t-2"}
    env = {"PRIOR_CONTEXT": "block"}
    dm._apply_chain_step_env(sk, env)
    assert env == {"PRIOR_CONTEXT": "block"}
    assert sk == {"task_id": "t-2"}


def test_apply_chain_step_env_caller_override_preserved():
    """An explicit env['CHAIN_STEP'] wins over the spawn_kwargs key (setdefault)."""
    sk = {"chain_step": "max_challenge"}
    env = {"CHAIN_STEP": "explicit_override"}
    dm._apply_chain_step_env(sk, env)
    assert env["CHAIN_STEP"] == "explicit_override"


def test_apply_chain_step_env_stringifies_non_string_value():
    """A non-string chain_step (defensive) gets str()'d so env stays text-only."""
    sk = {"chain_step": 7}
    env: dict[str, str] = {}
    dm._apply_chain_step_env(sk, env)
    assert env["CHAIN_STEP"] == "7"


# ---------------------------------------------------------------------------
# Container backend — _container_spawn_kwargs
# ---------------------------------------------------------------------------


def test_container_spawn_kwargs_promotes_chain_step_to_env():
    """chain_step in spawn_kwargs → container env['CHAIN_STEP'] (un-prefixed),
    and the generic loop does NOT also set AGENT_CHAIN_STEP."""
    out = dm._container_spawn_kwargs(
        "k-1",
        {"chain_step": "aiden_plan", "callsign": "aiden", "task_id": "t-1"},
    )
    env = out["env"]
    assert env.get("CHAIN_STEP") == "aiden_plan"
    assert "AGENT_CHAIN_STEP" not in env  # not double-set under the AGENT_* prefix
    # Other metadata still flows through with the AGENT_ prefix.
    assert env.get("AGENT_CALLSIGN") == "aiden"
    assert env.get("AGENT_TASK_ID") == "t-1"


def test_container_spawn_kwargs_no_chain_step_no_env_var():
    """Legacy spawn (no chain_step) leaves env CHAIN_STEP unset — fail-open."""
    out = dm._container_spawn_kwargs("k-2", {"callsign": "worker", "task_id": "t-2"})
    assert "CHAIN_STEP" not in out["env"]


# ---------------------------------------------------------------------------
# Tmux backend — _tmux_spawn_kwargs
# ---------------------------------------------------------------------------


def test_tmux_spawn_kwargs_promotes_chain_step_into_scrubbed_command():
    """The scrubbed-tmux command embeds env -i assignments; CHAIN_STEP=<value>
    must be in the assignment list when chain_step is supplied."""
    out = dm._tmux_spawn_kwargs(
        "k-3",
        {"chain_step": "atlas_safety", "callsign": "atlas", "task_id": "t-3"},
    )
    cmd = out["command"]
    # The env -i prefix carries quoted assignments; CHAIN_STEP must land there
    # un-prefixed (NOT as AGENT_CHAIN_STEP).
    assert "CHAIN_STEP=atlas_safety" in cmd
    assert "AGENT_CHAIN_STEP" not in cmd


def test_tmux_spawn_kwargs_no_chain_step_no_env_var_in_command():
    """Legacy tmux spawn: no chain_step → no CHAIN_STEP assignment in the command."""
    out = dm._tmux_spawn_kwargs("k-4", {"callsign": "worker", "task_id": "t-4"})
    assert "CHAIN_STEP=" not in out["command"]
