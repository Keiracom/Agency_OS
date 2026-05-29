"""Dispatcher container-defaults injection (Agency_OS-g9xx).

The work-loop bridge sends LOGICAL spawn_kwargs (callsign/task_id/brief/...) that
container_lifecycle.spawn_container's strict signature would TypeError on →
/dispatcher/spawn 400. _container_spawn_kwargs translates them so the call is
signature-valid (image/name/port/env), routing metadata into the container env.
"""

from __future__ import annotations

import inspect

import src.dispatcher.main as main_mod
from src.dispatcher.container_lifecycle import spawn_container

# Bridge-style logical kwargs that would blow up spawn_container as-is.
_BRIDGE_KWARGS = {
    "callsign": "atlas",
    "task_id": "T-1",
    "tenant_id": "fleet-1",
    "title": "do x",
    "brief": "do x",
    "task_type": "build",
    "priority": 2,
    "tags": ["build"],
}


def test_output_keys_are_all_valid_spawn_container_params():
    out = main_mod._container_spawn_kwargs("T-1", _BRIDGE_KWARGS)
    sig = inspect.signature(spawn_container)
    # Every produced key must be an accepted spawn_container param → no TypeError.
    for key in out:
        assert key in sig.parameters, f"{key} is not a spawn_container parameter"
    assert {"image", "name", "port"} <= set(out)  # required params always present


def test_defaults_image_name_port_and_routes_metadata_to_env():
    out = main_mod._container_spawn_kwargs("T-1", _BRIDGE_KWARGS)
    assert out["image"]  # defaulted from config
    assert out["name"] == f"{main_mod.CONTAINER_NAME_PREFIX}T-1"  # name from key
    assert isinstance(out["port"], int) and out["port"] > 0  # allocated
    assert out["env"]["AGENT_CALLSIGN"] == "atlas"  # metadata → env
    assert out["env"]["AGENT_TASK_TYPE"] == "build"
    assert "callsign" not in out  # metadata is no longer a top-level kwarg


def test_preserves_explicit_image_name_port():
    out = main_mod._container_spawn_kwargs("k", {"image": "img:1", "name": "c1", "port": 9000})
    assert out["image"] == "img:1"
    assert out["name"] == "c1"
    assert out["port"] == 9000


def test_preserves_recall_env_and_merges_metadata():
    sk = {"env": {"PRIOR_CONTEXT": "recall block"}, "callsign": "atlas"}
    out = main_mod._container_spawn_kwargs("k", sk)
    assert out["env"]["PRIOR_CONTEXT"] == "recall block"  # recall block survives
    assert out["env"]["AGENT_CALLSIGN"] == "atlas"  # metadata merged alongside


def test_image_overridable_via_env(monkeypatch):
    monkeypatch.setenv("DISPATCHER_CONTAINER_IMAGE", "custom-agent:v9")
    out = main_mod._container_spawn_kwargs("k", {"callsign": "x"})
    assert out["image"] == "custom-agent:v9"


# --- P10 vault bootstrap injection (Agency_OS-8dvl) --------------------


def test_vault_bootstrap_injected_into_container_env(monkeypatch):
    monkeypatch.setenv("VAULT_ADDR", "https://v:8200")
    monkeypatch.setenv("VAULT_TOKEN", "tok")
    out = main_mod._container_spawn_kwargs("k", {"callsign": "atlas"})
    assert out["env"]["VAULT_ADDR"] == "https://v:8200"
    assert out["env"]["VAULT_TOKEN"] == "tok"


def test_only_bootstrap_injected_not_other_dot_env_creds(monkeypatch):
    # The container gets the Vault bootstrap ONLY — not arbitrary .env creds.
    # This is the P10 invariant at the spawn boundary (no .env inheritance).
    monkeypatch.setenv("VAULT_ADDR", "https://v:8200")
    monkeypatch.setenv("VAULT_TOKEN", "tok")
    monkeypatch.setenv("DATABASE_URL", "postgresql://should-not-leak")
    out = main_mod._container_spawn_kwargs("k", {"callsign": "atlas"})
    assert "DATABASE_URL" not in out["env"]  # resolved from Vault in the container, not inherited
