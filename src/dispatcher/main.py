"""KEI-213 — Dispatcher wiring entry point.

Assembles the five KEI-209..212 components into a single uvicorn service:

    uvicorn src.dispatcher.main:app --host 127.0.0.1 --port 4001

Startup order (per KEI-213 acceptance criterion):
  1. auth_minter    — validate DISPATCHER_JWT_SECRET env present (fail-fast)
  2. interceptor_proxy — include router, verify LITELLM_URL reachable at runtime
  3. spend_tracker  — validate SUPABASE_DB_DSN env present (fail-fast)
  4. watchdog       — spawn as asyncio background task
  5. reaper         — spawn as asyncio background task

auth_minter and spend_tracker are stateless libraries; "init" for them is
confirming their required env vars are present before accepting traffic.
"""

from __future__ import annotations

import asyncio
import contextlib
import dataclasses
import json
import logging
import os
import shlex
import socket
from collections.abc import AsyncGenerator
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

import src.dispatcher.auth_minter  # noqa: F401 — imported for fail-fast side-effect
from src.dispatcher.bounded_spawn_enforcer import (
    DECISION_VIOLATION,
    BoundedSpawnEnforcer,
)
from src.dispatcher.container_lifecycle import ContainerStartupError, DockerUnavailableError
from src.dispatcher.cost_breaker import BreakerDecision, CostBreaker
from src.dispatcher.idempotency import IdempotencyDecision, IdempotencyGate
from src.dispatcher.interceptor_proxy import router as interceptor_router
from src.dispatcher.physical_ceiling import check_physical_ceiling
from src.dispatcher.reaper import Reaper
from src.dispatcher.session_manager import Backend, SessionManager
from src.dispatcher.spend_tracker import get_spend
from src.dispatcher.tmux_lifecycle import (
    SessionHandle,
    SessionStartupError,
    TmuxUnavailableError,
)
from src.dispatcher.watchdog import Watchdog
from src.keiracom_system.attribution.logger import (
    SOURCE_TYPES,
    TASK_TYPES,
    SpawnAttributionEntry,
    log_spawn_attribution,
)
from src.keiracom_system.work_loop import integration as work_loop
from src.relay.budget_ceiling import (
    PRIORITY_NORMAL,
    SOURCE_DAVE_DM,
    SOURCE_FLEET,
    BudgetCeilingGate,
    BudgetDecision,
)
from src.retrieval import retrieval_orchestrator, spawn_recall
from src.retrieval.workflow_recall import CHARS_PER_TOKEN, WorkflowRecallContext
from src.utils.log_safe import scrub

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Env validation — fail-fast before accepting any traffic
# ---------------------------------------------------------------------------

_REQUIRED_ENVS: dict[str, str] = {
    "DISPATCHER_JWT_SECRET": "auth_minter",
    "SUPABASE_DB_DSN": "spend_tracker",
}


def _validate_envs() -> None:
    """Raise RuntimeError with a clear message for each missing required env."""
    missing = [
        f"{var} (needed by {component})"
        for var, component in _REQUIRED_ENVS.items()
        if not os.environ.get(var, "").strip()
    ]
    if missing:
        raise RuntimeError(
            "Dispatcher cannot start — missing required env vars: " + ", ".join(missing)
        )


# ---------------------------------------------------------------------------
# Shared component-status dict — updated by background tasks
# ---------------------------------------------------------------------------

_component_status: dict[str, str] = {
    "auth_minter": "starting",
    "interceptor_proxy": "starting",
    "spend_tracker": "starting",
    "watchdog": "starting",
    "reaper": "starting",
}

_watchdog: Watchdog | None = None
_reaper: Reaper | None = None

# Pre-spawn idempotency gate (PR #1204 / Cat 21 lever 26 / cutover-blocker 5).
# Set by tests or by a future env-driven config layer; None = no-op (rollout
# phase 1 default — gate is wired but disabled until Valkey config lands).
_idempotency_gate: IdempotencyGate | None = None


def _set_idempotency_gate(gate: IdempotencyGate | None) -> None:
    """Test-only setter for the idempotency gate (DI through module attr)."""
    global _idempotency_gate  # noqa: PLW0603
    _idempotency_gate = gate


# Pre-spawn budget ceiling gate (PR #1203 / Cat 21 lever 28 / cutover-blocker 2).
# Set by tests or by a future env-driven config layer; None = no-op (rollout
# phase 1 default — gate is wired but disabled until DB-cursor config lands).
_budget_gate: BudgetCeilingGate | None = None


def _set_budget_gate(gate: BudgetCeilingGate | None) -> None:
    """Test-only setter for the budget ceiling gate (DI through module attr)."""
    global _budget_gate  # noqa: PLW0603
    _budget_gate = gate


# Fail-SAFE cost circuit breaker (Agency_OS-wdws). OUTER hard stop on fleet LLM
# spend — HALTs new spawns + pings #ceo when a daily/monthly $AUD ceiling is
# crossed. None = no-op until production startup wires one via _set_cost_breaker.
_cost_breaker: CostBreaker | None = None


def _set_cost_breaker(breaker: CostBreaker | None) -> None:
    """Test-only setter for the cost circuit breaker (DI through module attr)."""
    global _cost_breaker  # noqa: PLW0603
    _cost_breaker = breaker


# BudgetDecisions that allow the spawn to proceed (overage logged + Dave bypass).
_BUDGET_PROCEED: frozenset[BudgetDecision] = frozenset(
    {
        BudgetDecision.SPAWN_OK,
        BudgetDecision.OVERAGE_LOG_AND_SPAWN,
        BudgetDecision.DAVE_BYPASS,
        BudgetDecision.FORCE_OVERRIDE,
    }
)


# Bounded-spawn enforcer (Agency_OS-gcpm / Audit fix RED-7). Enforces the
# one-task-per-spawn discipline (per docs/architecture/ephemeral_persistence_boundary.md).
# None = no-op (default until production startup wires a real enforcer via
# _set_bounded_spawn_enforcer with a terminate_cb that calls into _spawned).
_bounded_spawn_enforcer: BoundedSpawnEnforcer | None = None


def _set_bounded_spawn_enforcer(enforcer: BoundedSpawnEnforcer | None) -> None:
    """Test-only setter for the bounded-spawn enforcer (DI through module attr)."""
    global _bounded_spawn_enforcer  # noqa: PLW0603
    _bounded_spawn_enforcer = enforcer


def _bounded_spawn_terminate(key: str) -> bool:
    """Default terminate callback for the enforcer — tears down via _spawned.

    Returns True when the violating spawn was found + terminated; False when
    no live entry exists for ``key`` (already torn down / never registered).
    """
    entry = _spawned.pop(key, None)
    if entry is None:
        return False
    handle = entry["handle"]
    try:
        SessionManager(backend=entry["backend"]).terminate(handle)
    except Exception:  # noqa: BLE001 — fail-open per enforcer contract
        logger.exception("bounded-spawn: SessionManager.terminate raised for key=%s", key)
        return False
    if _watchdog is not None:
        with contextlib.suppress(Exception):
            _watchdog.unregister(key)
    if _reaper is not None:
        try:
            if isinstance(handle, SessionHandle):
                _reaper.unregister_tmux(handle.session_name)
            else:
                _reaper.unregister_container(handle.id)
        except Exception:  # noqa: BLE001
            logger.exception("bounded-spawn: reaper unregister raised for key=%s", key)
    return True


def _bounded_spawn_callsign(spawn_kwargs: dict[str, Any]) -> str:
    """Pull the callsign from spawn_kwargs; default ``dispatcher`` for unlabelled."""
    return str((spawn_kwargs or {}).get("callsign") or "dispatcher")


def _bounded_spawn_task_id(spawn_kwargs: dict[str, Any], registry_key: str) -> str:
    """Pull a stable task identifier from spawn_kwargs, falling back to key."""
    explicit = str((spawn_kwargs or {}).get("task_id") or "").strip()
    return explicit or registry_key


# Spawn-attribution emit toggle (PR #1207 / Cat 21 lever 27 / cutover-blocker 6
# + PR #1209 / Cat 21 lever 23 / cutover-blocker 7 — per-task-type extension).
# When True, /dispatcher/spawn emits a SpawnAttributionEntry JSONL after
# successful register. Disabled in rollout phase 1.
_ATTRIBUTION_ENABLED_ENV = "DISPATCHER_ATTRIBUTION_ENABLED"
attribution_enabled: bool = os.environ.get(_ATTRIBUTION_ENABLED_ENV, "").lower() in {
    "1",
    "true",
    "yes",
}
attribution_default_model: str = os.environ.get("DISPATCHER_ATTRIBUTION_MODEL", "claude-sonnet-4-6")

# When True, /dispatcher/spawn fires a structured Hindsight recall before
# spawning and injects the top-3 results into the spawn env as a
# 'Prior context from memory' block (Wave 3 spawn-recall lifecycle hook).
# Disabled by default in rollout phase 1; recall is fail-open regardless.
_SPAWN_RECALL_ENABLED_ENV = "DISPATCHER_SPAWN_RECALL_ENABLED"
spawn_recall_enabled: bool = os.environ.get(_SPAWN_RECALL_ENABLED_ENV, "").lower() in {
    "1",
    "true",
    "yes",
}

# Workflow-scoped recall budget (Wave 3). A multi-step workflow spawns several
# sessions; without this, spawn_recall re-queries Hindsight on every spawn for
# the same workflow. When enabled AND a spawn carries a ``workflow_id``, the
# prior-context block from spawn 1 is cached and reused by spawn 2..N — no
# re-query (the cost + latency win). Layers ON TOP of spawn_recall: only
# engages when spawn_recall is also on; otherwise no effect. Default OFF;
# fail-open; 10-min TTL prevents cross-workflow bleed.
_WORKFLOW_RECALL_ENABLED_ENV = "DISPATCHER_WORKFLOW_RECALL_ENABLED"
workflow_recall_enabled: bool = os.environ.get(_WORKFLOW_RECALL_ENABLED_ENV, "").lower() in {
    "1",
    "true",
    "yes",
}
_workflow_recall = WorkflowRecallContext()

# Work-loop reconcile background task (Agency_OS-innu). OFF by default — matches
# every other dispatcher gate in rollout phase 1, and keeps the loop dormant
# until the budget-gate go-live. CRITICAL: when ON, the lifespan starts a forever
# loop that connects to Valkey via get_consumer(); leaving it unconditionally-on
# made the 8 TestClient dispatcher tests await an absent Valkey in CI (hang →
# 27-min kill), since no pytest timeout is configured (Agency_OS-28ai root cause).
_WORK_LOOP_RECONCILE_ENABLED_ENV = "DISPATCHER_WORK_LOOP_RECONCILE_ENABLED"
work_loop_reconcile_enabled: bool = os.environ.get(
    _WORK_LOOP_RECONCILE_ENABLED_ENV, ""
).lower() in {
    "1",
    "true",
    "yes",
}


def _spawn_kwargs_source_type(sk: dict) -> str:
    """Derive source_type from spawn_kwargs per PR #1207 SOURCE_TYPES taxonomy."""
    explicit = str(sk.get("source_type") or "").strip()
    if explicit in SOURCE_TYPES:
        return explicit
    sender = str(sk.get("from") or "").lower().strip()
    if sender == "dave":
        return "slack"
    if sender in {"cron", "scheduler"}:
        return "cron"
    return "inbox"


def _spawn_kwargs_task_type(sk: dict, registry_key: str) -> str:
    """Derive task_type from spawn_kwargs per PR #1207/#1209 TASK_TYPES taxonomy."""
    explicit = str(sk.get("task_type") or "").lower().strip()
    if explicit in TASK_TYPES:
        return explicit
    key_upper = registry_key.upper()
    if "REVIEW-PR" in key_upper or "PR-REVIEW" in key_upper:
        return "pr_review"
    if "DELIBERATE" in key_upper or "DELIBERATION" in key_upper:
        return "deliberation"
    if key_upper.startswith("DISPATCH"):
        return "dispatch_mgmt"
    if str(sk.get("from") or "").lower().strip() == "dave":
        return "chat"
    return "build"


def _spawn_kwargs_brief(sk: dict) -> str:
    """Pull the task brief from spawn_kwargs for spawn-time recall.

    Reads the canonical `brief` field first (per dispatch JSON contract),
    then common aliases. Empty string when none present.
    """
    for field in ("brief", "task_brief", "summary", "text"):
        value = str(sk.get(field) or "").strip()
        if value:
            return value
    return ""


def _recall_block(
    sk: dict[str, Any], *, task_type: str, task_brief: str
) -> tuple[str, dict[str, Any] | None]:
    """Produce the spawn's prior-context block, caching it per workflow_id.

    Returns ``(block, workflow_recall_result)``. When workflow recall is
    enabled AND a workflow_id is present, the block is cached so spawn 2..N in
    the same workflow reuse spawn 1's Hindsight recall without re-querying.
    Otherwise the block is computed fresh per spawn (Scout's #1240 behaviour)
    and the second element is None. Fail-open throughout (spawn_recall +
    WorkflowRecallContext both swallow errors to an empty block).
    """

    def _fresh_block() -> str:
        # Fail-open: a recall outage must never block a spawn. query_for_spawn
        # is fail-open by contract, but guard here too so a catastrophic raise
        # (matching spawn_recall.inject_prior_context's own outer catch) still
        # yields an empty block rather than a 500.
        try:
            # 4-layer retrieval orchestrator (RETRIEVAL_ORCHESTRATOR_4LAYER_ENABLED,
            # default off): L1 recall → L2 rerank → L3 contradiction filter →
            # L4 compression. Additive — when off, the existing single-layer path
            # below runs unchanged. Both are fail-open by contract.
            if retrieval_orchestrator.four_layer_enabled():
                return retrieval_orchestrator.assemble_hydration_block(task_type, task_brief)
            # build_spawn_context_block = positive recall + (flag-gated) failure
            # recall. Byte-identical to the positive-only block when
            # RETRIEVAL_FAILURE_RECALL_ENABLED is off (Wave 6).
            return spawn_recall.build_spawn_context_block(task_type, task_brief)
        except Exception:  # noqa: BLE001 — recall must never block a spawn
            logger.debug("workflow_recall: fresh block failed — no prior context", exc_info=True)
            return ""

    workflow_id = str(sk.get("workflow_id") or "").strip()
    if not (workflow_recall_enabled and workflow_id):
        return _fresh_block(), None
    outcome = _workflow_recall.get_or_recall(workflow_id, _fresh_block)
    result = {
        "workflow_id": workflow_id,
        "cached": outcome.cached,
        "context_tokens": len(outcome.context) // CHARS_PER_TOKEN,
    }
    return outcome.context, result


def _emit_attribution(
    *,
    registry_key: str,
    spawn_kwargs: dict,
    callsign: str,
) -> SpawnAttributionEntry | None:
    """Emit a SpawnAttributionEntry; fail-open on telemetry exceptions."""
    if not attribution_enabled:
        return None
    source_type = _spawn_kwargs_source_type(spawn_kwargs)
    task_type = _spawn_kwargs_task_type(spawn_kwargs, registry_key)
    try:
        return log_spawn_attribution(
            source_type=source_type,
            source_id=registry_key,
            callsign=callsign,
            model=attribution_default_model,
            task_type=task_type,
        )
    except Exception:  # noqa: BLE001 — telemetry must not block spawn
        logger.exception(
            "KEI-213 spawn attribution emit failed source_type=%s task_type=%s key=%s",
            source_type,
            task_type,
            registry_key,
        )
        return None


# Sessions spawned via /dispatcher/spawn, keyed by supervisor registry key.
# Lets /dispatcher/terminate find the handle + backend for clean teardown.
_spawned: dict[str, dict[str, Any]] = {}


# ---------------------------------------------------------------------------
# Background loop helpers
# ---------------------------------------------------------------------------

_WATCHDOG_POLL_INTERVAL_S = 30.0
_REAPER_SWEEP_INTERVAL_S = 60.0

TMUX_NAME_PREFIX = os.environ.get("DISPATCHER_TMUX_PREFIX", "disp-")
CONTAINER_NAME_PREFIX = os.environ.get("DISPATCHER_CONTAINER_PREFIX", "disp-")

# Container spawn defaults (Agency_OS-g9xx). The work-loop bridge sends LOGICAL
# spawn_kwargs (callsign/task_id/brief/...) that container_lifecycle.spawn_container's
# strict signature (image/name/port/env) would TypeError on → /dispatcher/spawn 400.
# _container_spawn_kwargs translates: image from config, name from key, port
# allocated, all other metadata → container env (AGENT_*), alongside any recall
# block spawn_recall.inject_block already placed in env.
#
# NOTE: DISPATCHER_CONTAINER_IMAGE must point at an image present on the spawn
# host. No Claude-agent container image was found in-repo (Dockerfile.worker is a
# Prefect worker, not an agent), and docker wasn't available to verify a built
# tag — so the default below is a placeholder the operator MUST override/build
# before a real container spawn succeeds (else docker run → ContainerStartupError).
_CONTAINER_IMAGE_ENV = "DISPATCHER_CONTAINER_IMAGE"
DEFAULT_CONTAINER_IMAGE = "keiracom-agent:latest"
_CONTAINER_PASSTHROUGH = frozenset({"image", "name", "port", "env", "health_path", "extra_args"})


def _container_image() -> str:
    return os.environ.get(_CONTAINER_IMAGE_ENV) or DEFAULT_CONTAINER_IMAGE


def _free_port() -> int:
    """Allocate an OS-assigned free localhost port for the container's published port."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _container_spawn_kwargs(key: str, sk: dict[str, Any]) -> dict[str, Any]:
    """Translate logical spawn_kwargs → container_lifecycle.spawn_container kwargs.

    image/name/port are defaulted (config / key / allocated) unless the caller
    supplied them; every other key (task metadata) is routed into the container
    env as an AGENT_* var, merged with any env already present (e.g. the recall
    block from spawn_recall.inject_block). A caller that already passes a valid
    {image, name, port[, env]} set passes through unchanged.
    """
    sk = dict(sk or {})
    env = dict(sk.pop("env", None) or {})
    image = sk.pop("image", None) or _container_image()
    name = sk.pop("name", None) or f"{CONTAINER_NAME_PREFIX}{key}"
    port = int(sk.pop("port", None) or _free_port())
    health_path = sk.pop("health_path", None)
    extra_args = sk.pop("extra_args", None)
    for meta_key, meta_val in sk.items():
        if meta_val is not None:
            env.setdefault(f"AGENT_{meta_key.upper()}", str(meta_val))
    # P10 cold-start bootstrap (Agency_OS-8dvl): pass ONLY the Vault bootstrap into
    # the container — the ephemeral agent resolves every other credential from
    # Vault KV (kv_resolver.resolve_into_env, Nova #1289), with NO .env inheritance. Docker isolation
    # means the container sees only this env dict, so these two are the entire
    # inherited-credential surface.
    for boot in ("VAULT_ADDR", "VAULT_TOKEN"):
        boot_val = os.environ.get(boot)
        if boot_val:
            env.setdefault(boot, boot_val)
    out: dict[str, Any] = {"image": image, "name": name, "port": port, "env": env}
    if health_path is not None:
        out["health_path"] = health_path
    if extra_args is not None:
        out["extra_args"] = extra_args
    return out


# Phase-1 spawn backend is scrubbed-tmux (Agency_OS-87ei): reuse the working tmux
# spawn but run the agent under `env -i` so it inherits NO .env — only the Vault
# bootstrap + non-secret operational vars + recall/metadata. resolve_into_env then
# pulls every credential from Vault KV. (Container is the pre-multi-tenant
# fast-follow; #1282/#1288 already wire its bootstrap.)
#
# env -i clears PATH/HOME too, so the agent command couldn't even start — these
# NON-SECRET operational vars are re-added. Credentials (DATABASE_URL, *_API_KEY,
# …) are deliberately NOT whitelisted → scrubbed.
# Carve-out (Elliot 2026-05-30, V1-battery unblock): ANTHROPIC_API_KEY is in
# the passthrough until api_agent_cold_start migrates to vault-resolved creds;
# the Anthropic SDK reads it from os.environ at spawn time.
_TMUX_OPERATIONAL_PASSTHROUGH = (
    "PATH",
    "HOME",
    "LANG",
    "LC_ALL",
    "TERM",
    "USER",
    "ANTHROPIC_API_KEY",
)
DEFAULT_AGENT_WORKDIR = os.environ.get(
    "DISPATCHER_AGENT_WORKDIR", "/home/elliotbot/clawd/Agency_OS"
)
# The command run AFTER cold-start cred resolution. Defaults to the cold-start
# entrypoint (resolve_into_env → exec the agent); referenced by string so this
# module needs no import of Nova's kv_resolver (the entrypoint lands on #1289).
DEFAULT_AGENT_COMMAND = os.environ.get(
    "DISPATCHER_AGENT_COMMAND", "python3 -m src.keiracom_system.vault.agent_cold_start"
)
# OFF by default (rollout phase 1, matches every other dispatcher gate). When ON,
# every tmux spawn is env-i-scrubbed. Goes live at the Phase-1 cutover; off keeps
# existing (non-ephemeral) tmux spawns unchanged.
_TMUX_SCRUB_ENABLED_ENV = "DISPATCHER_TMUX_SCRUB_ENABLED"
tmux_scrub_enabled: bool = os.environ.get(_TMUX_SCRUB_ENABLED_ENV, "").lower() in {
    "1",
    "true",
    "yes",
}


def _tmux_scrubbed_command(agent_command: str, env: dict[str, str]) -> str:
    """Wrap a command so it runs with a SCRUBBED env (P10).

    ``env -i`` clears all inherited env; only ``env`` (Vault bootstrap +
    operational passthrough + recall/metadata) is set; ``sh -c`` runs the command
    without sourcing a profile that could re-introduce env. Credentials not in
    ``env`` are gone — that is the no-.env-inheritance guarantee.
    """
    assignments = " ".join(f"{k}={shlex.quote(str(v))}" for k, v in env.items())
    return f"env -i {assignments} sh -c {shlex.quote(agent_command)}"


def _tmux_spawn_kwargs(key: str, sk: dict[str, Any]) -> dict[str, Any]:
    """Translate logical spawn_kwargs → scrubbed-tmux spawn_session kwargs (87ei).

    The agent process sees ONLY the Vault bootstrap, the operational passthrough,
    and any recall/metadata — never the dispatcher's .env credentials.
    """
    sk = dict(sk or {})
    session_name = sk.pop("session_name", None) or f"{TMUX_NAME_PREFIX}{key}"
    working_dir = sk.pop("working_dir", None) or DEFAULT_AGENT_WORKDIR
    agent_command = sk.pop("command", None) or DEFAULT_AGENT_COMMAND
    env = dict(sk.pop("env", None) or {})  # carries the recall PRIOR_CONTEXT if injected
    for meta_key, meta_val in sk.items():
        if meta_val is not None:
            env.setdefault(f"AGENT_{meta_key.upper()}", str(meta_val))
    # Vault bootstrap (the only inherited credential surface) + non-secret operational env.
    for passthrough in ("VAULT_ADDR", "VAULT_TOKEN", *_TMUX_OPERATIONAL_PASSTHROUGH):
        val = os.environ.get(passthrough)
        if val:
            env.setdefault(passthrough, val)
    return {
        "session_name": session_name,
        "working_dir": working_dir,
        "command": _tmux_scrubbed_command(agent_command, env),
    }


def _norm_status(raw: str) -> str:
    """Map a watchdog/reaper status into the {'ok','degraded'} vocabulary.

    watchdog.health_snapshot() reports "green"/"degraded"; _component_status
    and the /dispatcher/health aggregator speak "ok"/"degraded". Without this
    map a healthy watchdog ("green") never equals "ok" and falsely drags the
    whole service to "degraded" forever.
    """
    return "ok" if raw in ("ok", "green") else "degraded"


async def _watchdog_loop(wd: Watchdog) -> None:
    """Run watchdog.probe_all() every 30 s. Updates _component_status."""
    _component_status["watchdog"] = "ok"
    while True:
        try:
            await asyncio.sleep(_WATCHDOG_POLL_INTERVAL_S)
            snapshot = wd.health_snapshot()
            _component_status["watchdog"] = _norm_status(snapshot.get("status", "ok"))
        except asyncio.CancelledError:
            _component_status["watchdog"] = "stopped"
            raise
        except Exception:  # noqa: BLE001 — best-effort; must not crash loop
            logger.exception("KEI-213 watchdog loop error")
            _component_status["watchdog"] = "degraded"


async def _reaper_loop(rp: Reaper) -> None:
    """Run reaper.sweep() every 60 s. Updates _component_status."""
    _component_status["reaper"] = "ok"
    while True:
        try:
            await asyncio.sleep(_REAPER_SWEEP_INTERVAL_S)
            result = rp.sweep()
            if result.total_reaped:
                logger.info("KEI-213 reaper reaped %d sessions", result.total_reaped)
            _component_status["reaper"] = "ok"
        except asyncio.CancelledError:
            _component_status["reaper"] = "stopped"
            raise
        except Exception:  # noqa: BLE001
            logger.exception("KEI-213 reaper loop error")
            _component_status["reaper"] = "degraded"


# ---------------------------------------------------------------------------
# Lifespan — startup + shutdown
# ---------------------------------------------------------------------------


@contextlib.asynccontextmanager
async def _lifespan(_app: FastAPI) -> AsyncGenerator[None, None]:
    global _watchdog, _reaper  # noqa: PLW0603

    # Step 1 — auth_minter (env validation)
    _validate_envs()
    _component_status["auth_minter"] = "ok"
    logger.info("KEI-213 auth_minter: DISPATCHER_JWT_SECRET present")

    # Step 2 — interceptor_proxy (router already included; mark ready)
    _component_status["interceptor_proxy"] = "ok"
    logger.info("KEI-213 interceptor_proxy: router mounted")

    # Step 3 — spend_tracker (env confirmed by _validate_envs above)
    _component_status["spend_tracker"] = "ok"
    logger.info("KEI-213 spend_tracker: SUPABASE_DB_DSN present")

    # Step 4 — watchdog background task
    _watchdog = Watchdog()
    wd_task = asyncio.create_task(_watchdog_loop(_watchdog), name="dispatcher-watchdog")
    logger.info("KEI-213 watchdog: background task started")

    # Step 5 — reaper background task
    _reaper = Reaper(
        tmux_name_prefix=TMUX_NAME_PREFIX,
        container_name_prefix=CONTAINER_NAME_PREFIX,
    )
    rp_task = asyncio.create_task(_reaper_loop(_reaper), name="dispatcher-reaper")
    logger.info("KEI-213 reaper: background task started")

    # Step 6 — work-loop reconcile (Agency_OS-innu): reclaim crashed-agent slots
    # whose lease TTL lapsed (the exit hook only covers clean terminations).
    # Gated OFF by default — only runs once the loop goes live (post budget-gate);
    # otherwise it would connect to an absent Valkey (e.g. CI) and hang (28ai).
    background_tasks = [wd_task, rp_task]
    if work_loop_reconcile_enabled:
        rc_task = asyncio.create_task(work_loop.reconcile_loop(), name="work-loop-reconcile")
        background_tasks.append(rc_task)
        logger.info("work-loop: reconcile background task started")

    # Step 7 — v1_chain consumer (Agency_OS-oevr): subscribes keiracom.agent.handoff
    # and advances the chain via _advance_step_async on each message. Fail-open;
    # cancellable. Lazy import keeps dispatcher startup free of chain-module load
    # errors if the package is absent.
    from src.keiracom_system.chain.v1_chain_orchestrator import (  # noqa: PLC0415
        run_consumer as _v1_chain_run_consumer,
    )

    v1c_task = asyncio.create_task(_v1_chain_run_consumer(), name="v1-chain-consumer")
    background_tasks.append(v1c_task)
    logger.info("v1_chain consumer: background task started")

    try:
        yield
    finally:
        # Graceful shutdown — cancel tasks and wait for clean exit
        for task in background_tasks:
            task.cancel()
        await asyncio.gather(*background_tasks, return_exceptions=True)
        logger.info("KEI-213 dispatcher: background tasks cancelled cleanly")


# ---------------------------------------------------------------------------
# FastAPI app — extend interceptor_proxy's router
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Dispatcher",
    description="KEI-213 Dispatcher wiring: auth_minter + interceptor_proxy + spend_tracker + watchdog + reaper",
    version="1.0.0",
    lifespan=_lifespan,
)
app.include_router(interceptor_router)


# ---------------------------------------------------------------------------
# /dispatcher/health — aggregate health across all five components
# ---------------------------------------------------------------------------


@app.get("/dispatcher/health")
async def dispatcher_health() -> dict[str, Any]:
    """Aggregated liveness + readiness probe for the full dispatcher service.

    Returns HTTP 200 with ``status: ok`` when all components report green,
    ``status: degraded`` when any component is non-ok.
    """
    # interceptor_proxy: re-use its own health check logic
    _component_status["interceptor_proxy"] = "ok"

    # spend_tracker: no-op probe via get_spend; any exception = degraded
    try:
        await get_spend(tenant_id=0, period="daily")
        _component_status["spend_tracker"] = "ok"
    except Exception:  # noqa: BLE001
        _component_status["spend_tracker"] = "degraded"
        logger.warning("KEI-213 health probe: spend_tracker unreachable")

    overall = "ok" if all(v == "ok" for v in _component_status.values()) else "degraded"
    result: dict[str, Any] = {"status": overall, "components": dict(_component_status)}
    # Raw supervisor snapshots — surfaces watchdog/reaper tracked counts so a
    # caller can see whether the supervisor loops track live work.
    if _watchdog is not None and _reaper is not None:
        result["supervisor"] = {
            "watchdog": _watchdog.health_snapshot(),
            "reaper": _reaper.health_snapshot(),
        }
    return result


# ---------------------------------------------------------------------------
# /dispatcher/spawn + /dispatcher/terminate — session lifecycle
#
# Wires session_manager into the running service and registers every
# spawned session with the KEI-211 watchdog + reaper. Before this route
# existed the supervisor loops swept an empty registry — they supervised
# nothing, because no code path ever called .register().
# ---------------------------------------------------------------------------


class SpawnRequest(BaseModel):
    """Spawn a tmux/container session and place it under supervision."""

    backend: str  # "tmux" | "container"
    key: str  # supervisor registry key — unique per session
    spawn_kwargs: dict[str, Any]  # forwarded verbatim to SessionManager.spawn
    hung_threshold_s: float | None = None  # watchdog hang-window override
    ttl_s: float | None = None  # reaper TTL override


class TerminateRequest(BaseModel):
    """Terminate a previously spawned session by its registry key."""

    key: str


def _register_session(
    key: str,
    handle: Any,
    *,
    hung_threshold_s: float | None,
    ttl_s: float | None,
) -> None:
    """Register a spawned handle with watchdog + reaper.

    This is the wiring the audit found missing: without it the KEI-211
    supervisor loops sweep an empty registry.
    """
    if hung_threshold_s is not None:
        _watchdog.register(key, handle, hung_threshold_s=hung_threshold_s)  # type: ignore[union-attr]
    else:
        _watchdog.register(key, handle)  # type: ignore[union-attr]
    if isinstance(handle, SessionHandle):
        _reaper.register_tmux(handle, ttl_s=ttl_s)  # type: ignore[union-attr]
    else:
        _reaper.register_container(handle, ttl_s=ttl_s)  # type: ignore[union-attr]


@app.post(
    "/dispatcher/spawn",
    responses={
        400: {"description": "Unknown backend, bad spawn args, or registration rejected"},
        503: {"description": "Supervisors not started, or backend CLI (tmux/docker) unavailable"},
    },
)
async def dispatcher_spawn(req: SpawnRequest) -> dict[str, Any]:
    """Spawn a session via session_manager and put it under supervision.

    Returns the handle plus post-registration supervisor counts so the
    caller can confirm the session is actually being tracked.
    """
    if _watchdog is None or _reaper is None:
        raise HTTPException(status_code=503, detail="dispatcher supervisors not started")
    try:
        backend = Backend(req.backend)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"unknown backend: {req.backend!r}") from exc

    # Pre-spawn idempotency gate (Cat 21 lever 26 / cutover-blocker 5).
    # Dedup duplicate spawn requests within a 60-second window via Valkey
    # SET NX EX. source = "dispatcher-spawn-<backend>"; content = req.key.
    # Fail-open: no-gate-wired / Valkey error → PROCEED (PR #1204 contract).
    if _idempotency_gate is not None:
        idem_result = await _idempotency_gate.check_and_claim(
            source=f"dispatcher-spawn-{backend.value}",
            content=req.key,
        )
        if idem_result.decision == IdempotencyDecision.DROP_DUPLICATE:
            logger.info(
                "KEI-213 idempotency gate dropped duplicate spawn key=%s backend=%s",
                req.key,
                backend.value,
            )
            return {
                "spawned": False,
                "key": req.key,
                "backend": backend.value,
                "decision": "drop_duplicate",
                "reason": idem_result.reason,
                "idempotency_key": idem_result.key,
            }

    # Pre-spawn cost circuit breaker (Agency_OS-wdws) — OUTER fail-SAFE hard stop.
    # Runs BEFORE the (fail-open) budget policy gate: a HALT refuses the spawn
    # outright. Dave-DM / force_override bypass HALT (CEO never blocked) but alert.
    if _cost_breaker is not None:
        cb_sk = req.spawn_kwargs or {}
        cb_source = (
            SOURCE_DAVE_DM
            if (
                str(cb_sk.get("source") or "").strip() == SOURCE_DAVE_DM
                or str(cb_sk.get("from") or "").lower().strip() == "dave"
            )
            else SOURCE_FLEET
        )
        cb_force = bool(cb_sk.get("force_override") or cb_sk.get("force_spawn"))
        breaker_result = await _cost_breaker.check(source=cb_source, force_override=cb_force)
        if breaker_result.decision == BreakerDecision.HALT:
            logger.warning(
                "cost breaker HALT key=%s daily_aud=%.2f monthly_aud=%.2f reason=%s",
                req.key,
                breaker_result.daily_spend_aud,
                breaker_result.monthly_spend_aud,
                breaker_result.reason,
            )
            return {
                "spawned": False,
                "key": req.key,
                "backend": backend.value,
                "decision": "cost_halt",
                "daily_spend_aud": breaker_result.daily_spend_aud,
                "monthly_spend_aud": breaker_result.monthly_spend_aud,
                "reason": breaker_result.reason,
            }

    # Pre-spawn budget ceiling gate (Cat 21 lever 28 / cutover-blocker 2).
    # Per-spawn check before manager.spawn(); BudgetCeilingGate fail-opens
    # internally on DB / alerts errors per PR #1203 contract.
    if _budget_gate is not None:
        # Priority + source derived from spawn_kwargs ("priority" / "source" hints).
        sk = req.spawn_kwargs or {}
        priority_hint = str(sk.get("priority") or PRIORITY_NORMAL).lower().strip()
        priority = priority_hint if priority_hint in {"high", "normal", "low"} else PRIORITY_NORMAL
        source_hint = str(sk.get("source") or "").strip()
        if source_hint in {SOURCE_DAVE_DM, SOURCE_FLEET}:
            source = source_hint
        else:
            sender = str(sk.get("from") or "").lower().strip()
            source = SOURCE_DAVE_DM if sender == "dave" else SOURCE_FLEET
        budget_result = _budget_gate.check_budget(task_priority=priority, source=source)
        if budget_result.decision not in _BUDGET_PROCEED:
            logger.info(
                "KEI-213 budget gate skipped spawn key=%s decision=%s spend_aud=%.2f budget_aud=%.2f",
                req.key,
                budget_result.decision.value,
                budget_result.current_day_spend_aud,
                budget_result.daily_budget_aud,
            )
            return {
                "spawned": False,
                "key": req.key,
                "backend": backend.value,
                "decision": budget_result.decision.value,
                "current_day_spend_aud": budget_result.current_day_spend_aud,
                "daily_budget_aud": budget_result.daily_budget_aud,
                "reason": budget_result.reason,
            }

    # Spawn-time recall lifecycle hook (Wave 3).
    # Fire a structured Hindsight recall ("what failed before + canonical
    # approach + superseded decisions") and inject the top-3 results into the
    # spawn env as a 'Prior context from memory' block. Fail-open: recall
    # errors never block the spawn (spawn_recall swallows internally), and the
    # block only lands in `env` — the one context-bearing field forwarded
    # verbatim to the backend spawn. When workflow recall is on + the spawn
    # carries a workflow_id, the block is cached so sibling spawns reuse it
    # without re-querying (see _recall_block).
    spawn_kwargs_effective = req.spawn_kwargs
    workflow_recall_result: dict[str, Any] | None = None
    if spawn_recall_enabled:
        sk = req.spawn_kwargs or {}
        block, workflow_recall_result = _recall_block(
            sk,
            task_type=_spawn_kwargs_task_type(sk, req.key),
            task_brief=_spawn_kwargs_brief(sk),
        )
        spawn_kwargs_effective = spawn_recall.inject_block(sk, block)

    # Container-defaults injection (Agency_OS-g9xx): translate logical task
    # metadata → spawn_container's strict image/name/port/env signature so the
    # work-loop bridge's spawn_kwargs no longer TypeError → 400.
    if backend is Backend.CONTAINER:
        spawn_kwargs_effective = _container_spawn_kwargs(req.key, spawn_kwargs_effective)
    elif backend is Backend.TMUX and tmux_scrub_enabled:
        # Phase-1 scrubbed-tmux (Agency_OS-87ei): run the agent under env -i so it
        # inherits no .env — only the Vault bootstrap; resolve_into_env does the rest.
        spawn_kwargs_effective = _tmux_spawn_kwargs(req.key, spawn_kwargs_effective)

    # Physical RAM ceiling (Agency_OS-cuit): hard box-level guard separate from the
    # tenant tier ceiling. Applies even to the uncapped operator — the box can OOM
    # regardless of tenant policy. Re-reads available RAM on every call so it adapts
    # to live memory pressure. Fail-safe: if RAM is unreadable, falls back to the
    # conservative DEFAULT_PHYSICAL_CEILING (never fails open to "unlimited").
    can_spawn, ceiling_reason = check_physical_ceiling(len(_spawned))
    if not can_spawn:
        logger.warning("physical ceiling: refusing spawn key=%s — %s", req.key, ceiling_reason)
        raise HTTPException(status_code=503, detail=ceiling_reason)

    manager = SessionManager(backend=backend)
    try:
        handle = manager.spawn(**spawn_kwargs_effective)
    except (TmuxUnavailableError, DockerUnavailableError) as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except (SessionStartupError, ContainerStartupError, TypeError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    try:
        _register_session(req.key, handle, hung_threshold_s=req.hung_threshold_s, ttl_s=req.ttl_s)
    except ValueError as exc:
        # Registration rejected (e.g. session name does not match the
        # reaper prefix). Tear the session down so it is not left orphaned.
        manager.terminate(handle)
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    _spawned[req.key] = {
        "handle": handle,
        "backend": backend,
        # Retained for the work-loop exit hook (Agency_OS-innu): release the
        # tenant slot + pop overflow on terminate. None when not a work-loop spawn.
        "tenant_id": (req.spawn_kwargs or {}).get("tenant_id"),
    }

    # Bounded-spawn enforcement (Agency_OS-gcpm / Audit RED-7).
    # Runs AFTER register so the active-slot record reflects what's actually
    # under supervision. On violation, the prior spawn is killed in-flight;
    # the new spawn proceeds and is recorded as the canonical active slot.
    bounded_spawn_result: dict[str, Any] | None = None
    if _bounded_spawn_enforcer is not None:
        callsign = _bounded_spawn_callsign(req.spawn_kwargs or {})
        task_id = _bounded_spawn_task_id(req.spawn_kwargs or {}, req.key)
        enforcement = _bounded_spawn_enforcer.record_spawn(
            key=req.key,
            callsign=callsign,
            task_id=task_id,
            backend=backend.value,
        )
        bounded_spawn_result = {
            "decision": enforcement.decision,
            "killed_prior": enforcement.killed,
        }
        if enforcement.decision == DECISION_VIOLATION:
            logger.error(
                "bounded-spawn violation: callsign=%s new_task=%s prior_task=%s killed=%s",
                scrub(callsign),
                scrub(task_id),
                enforcement.prior.task_id if enforcement.prior else None,
                enforcement.killed,
            )

    # Spawn attribution emit (Cat 21 levers 27 + 23 / cutover-blockers 6 + 7).
    # Fires AFTER successful register so attribution only records sessions that
    # actually entered supervision.
    callsign_hint = str((req.spawn_kwargs or {}).get("callsign") or "dispatcher")
    _emit_attribution(
        registry_key=req.key,
        spawn_kwargs=req.spawn_kwargs or {},
        callsign=callsign_hint,
    )

    rsnap = _reaper.health_snapshot()
    response: dict[str, Any] = {
        "spawned": True,
        "key": req.key,
        "backend": backend.value,
        "handle": dataclasses.asdict(handle),
        "watchdog_tracked": _watchdog.tracked,
        "reaper_tracked": int(rsnap["tracked_tmux"]) + int(rsnap["tracked_containers"]),
    }
    if bounded_spawn_result is not None:
        response["bounded_spawn"] = bounded_spawn_result
    if workflow_recall_result is not None:
        response["workflow_recall"] = workflow_recall_result
    return response


@app.post(
    "/dispatcher/terminate",
    responses={
        404: {"description": "No spawned session for the given key"},
        503: {"description": "Supervisors not started"},
    },
)
async def dispatcher_terminate(req: TerminateRequest) -> dict[str, Any]:
    """Terminate a spawned session and remove it from supervision."""
    if _watchdog is None or _reaper is None:
        raise HTTPException(status_code=503, detail="dispatcher supervisors not started")
    entry = _spawned.pop(req.key, None)
    if entry is None:
        raise HTTPException(status_code=404, detail=f"no spawned session for key {req.key!r}")

    handle = entry["handle"]
    SessionManager(backend=entry["backend"]).terminate(handle)
    _watchdog.unregister(req.key)
    if isinstance(handle, SessionHandle):
        _reaper.unregister_tmux(handle.session_name)
    else:
        _reaper.unregister_container(handle.id)
    # Release the bounded-spawn slot so the next legitimate spawn for this
    # callsign is treated as the first task on a fresh slot, not a violation.
    if _bounded_spawn_enforcer is not None:
        _bounded_spawn_enforcer.release_spawn(req.key)
    # Work-loop exit hook (Agency_OS-innu): free the tenant slot → pop overflow →
    # spawn next. Fail-open inside release_on_exit; never breaks teardown.
    tenant_id = entry.get("tenant_id")
    if tenant_id:
        await work_loop.release_on_exit(str(tenant_id), req.key)
    return {"terminated": True, "key": req.key, "watchdog_tracked": _watchdog.tracked}


# ---------------------------------------------------------------------------
# /dispatcher/task_complete — result-back-to-Slack hook
#
# Called by agent_cold_start after finalize_task(). The dispatcher runs in
# the host env (has SLACK_BOT_TOKEN from .env); spawned agents run in a
# scrubbed env and cannot post to Slack directly. This endpoint bridges the
# gap: the agent makes a loopback HTTP call here; the dispatcher posts the
# result to #ceo via slack_relay.py with CALLSIGN=elliot.
#
# Fail-open: Slack errors are logged but never propagate to the caller —
# a notification failure must never block the task lifecycle.
# ---------------------------------------------------------------------------


class TaskCompleteRequest(BaseModel):
    """Result-back-to-Slack payload from agent_cold_start."""

    task_id: str
    callsign: str = "worker"
    title: str = ""
    status: str  # "done" | "blocked"
    rc: int = 0


_SLACK_RELAY_SCRIPT = os.path.join(
    os.environ.get("DISPATCHER_AGENT_WORKDIR", "/home/elliotbot/clawd/Agency_OS"),
    "scripts",
    "slack_relay.py",
)


@app.post("/dispatcher/task_complete")
async def dispatcher_task_complete(req: TaskCompleteRequest) -> dict[str, Any]:
    """Post a task-completion notice to #ceo via slack_relay (Elliot's relay).

    Spawned agents cannot post to Slack directly (SLACK_ACCESS_DENIED for
    non-Elliot callsigns; scrubbed env has no SLACK_BOT_TOKEN). This endpoint
    runs in the dispatcher process which has the token in its env.
    """
    icon = "✅" if req.status == "done" else "🔴"
    title_part = f" '{req.title}'" if req.title else ""
    msg = (
        f"{icon} [{req.callsign.upper()}] Task{title_part} {req.status} "
        f"(rc={req.rc}) — ID: {req.task_id}"
    )
    try:
        import subprocess as _sp
        import sys as _sys

        result = _sp.run(
            [_sys.executable, _SLACK_RELAY_SCRIPT, "-c", "ceo", msg],
            capture_output=True,
            text=True,
            timeout=15,
            env={**os.environ, "CALLSIGN": "elliot"},
        )
        if result.returncode != 0:
            logger.warning(
                "task_complete: slack_relay rc=%d stderr=%r",
                result.returncode,
                result.stderr[:200],
            )
            return {"notified": False, "reason": f"slack_relay rc={result.returncode}"}
    except Exception:  # noqa: BLE001 — notification must never break the lifecycle
        logger.exception("task_complete: slack_relay raised for task=%s", req.task_id)
        return {"notified": False, "reason": "exception"}
    logger.info("task_complete: notified #ceo task=%s callsign=%s", req.task_id, req.callsign)
    return {"notified": True}


# ---------------------------------------------------------------------------
# /dispatcher/chain_complete — V1 chain final-result hook (Agency_OS-zqni)
#
# Called by v1_chain_orchestrator.advance_step when the chain reaches the
# 'complete' state. Separate from /task_complete so nd3b's intermediate-step
# suppression rule (CHAIN_STEP != 'complete' → skip) stays clean: per-step
# notifies are gated at the worker, the single chain-result line fires here.
# Cost is summed best-effort from keiracom_spawn_attribution (last 24h entries
# whose source_id equals the chain's task_id), converted USD→AUD at 1.55,
# omitted from the message if unavailable. Fail-open end to end.
# ---------------------------------------------------------------------------


class ChainCompleteRequest(BaseModel):
    """V1 chain completion payload from v1_chain_orchestrator."""

    task_id: str
    chain_id: str
    brief: str = ""
    steps: list[str] = []


def _lookup_chain_cost_aud(task_id: str) -> float | None:
    """Sum cost_usd for attribution rows where source_id == task_id, ×1.55. None on miss/error.

    Fail-closed: any exception or zero-sum returns None so the cost line is
    omitted from the message rather than presenting a misleading A$0.0000.
    """
    try:
        from src.keiracom_system.attribution.logger import load_attribution_last_24h

        entries = load_attribution_last_24h()
        matching = [e for e in entries if e.get("source_id") == task_id]
        if not matching:
            return None
        cost_usd = sum(float(e.get("cost_usd", 0.0)) for e in matching)
        if cost_usd <= 0:
            return None
        return cost_usd * 1.55  # USD→AUD per CLAUDE.md ratified rate
    except Exception:  # noqa: BLE001 — cost lookup must never break notification
        logger.warning("chain_complete: cost lookup failed for task=%s", task_id, exc_info=True)
        return None


@app.post("/dispatcher/chain_complete")
async def dispatcher_chain_complete(req: ChainCompleteRequest) -> dict[str, Any]:
    """Post the V1-chain completion summary to #ceo via slack_relay (Elliot's relay).

    Fail-open: any error (slack_relay, cost-lookup, formatting) is logged and
    swallowed — a notification failure must never block the chain lifecycle.
    """
    steps_str = (
        " → ".join(req.steps)
        if req.steps
        else "aiden_plan → max_challenge → nova_build → orion_spec + atlas_safety"
    )
    lines = [
        f"✅ Chain complete — {req.task_id}",
        f"**Brief:** {req.brief or '(no brief)'}",
        f"**Steps:** {steps_str}",
    ]
    cost_aud = _lookup_chain_cost_aud(req.task_id)
    if cost_aud is not None:
        lines.append(f"**Cost:** A${cost_aud:.4f}")
    lines.append(f"**chain_id:** {req.chain_id}")
    msg = "\n".join(lines)
    try:
        import subprocess as _sp
        import sys as _sys

        result = _sp.run(
            [_sys.executable, _SLACK_RELAY_SCRIPT, "-c", "ceo", msg],
            capture_output=True,
            text=True,
            timeout=15,
            env={**os.environ, "CALLSIGN": "elliot"},
        )
        if result.returncode != 0:
            logger.warning(
                "chain_complete: slack_relay rc=%d stderr=%r",
                result.returncode,
                result.stderr[:200],
            )
            return {"notified": False, "reason": f"slack_relay rc={result.returncode}"}
    except Exception:  # noqa: BLE001 — notification must never break the lifecycle
        logger.exception("chain_complete: slack_relay raised for chain=%s", req.chain_id)
        return {"notified": False, "reason": "exception"}
    logger.info("chain_complete: notified #ceo task=%s chain=%s", req.task_id, req.chain_id)
    return {"notified": True}


# ---------------------------------------------------------------------------
# /dispatcher/persona — role system-prompt lookup (persona_bank_v1)
#
# V1 chain roles (face/deliberator/worker/reviewer) fetch their system prompt
# at spawn time via this endpoint instead of reading a file. Internal only —
# no auth (the dispatcher is not exposed outside the host).
# ---------------------------------------------------------------------------

_PERSONA_DSN_ENV = "SUPABASE_DB_DSN"
# asyncpg rejects the SQLAlchemy-style "+asyncpg" suffix; strip it before
# connect (matches spend_tracker / reference_psycopg_supabase_pgbouncer.md).
_ASYNCPG_DSN_SUFFIX = "+asyncpg"


async def _fetch_persona(role: str, tier: str, variant: str | None) -> dict[str, Any] | None:
    """Fetch one persona row from public.persona_bank.

    variant=None resolves the default row (variant IS NULL). Returns
    ``{prompt_text, token_count}`` or None on a real miss. Raises on DB
    connectivity failure so the caller can distinguish 503 from 404.
    """
    dsn = os.environ.get(_PERSONA_DSN_ENV)
    if not dsn:
        raise RuntimeError(f"{_PERSONA_DSN_ENV} unset")
    import asyncpg  # noqa: PLC0415 — deferred (optional in some test envs)

    conn = await asyncpg.connect(dsn.replace(_ASYNCPG_DSN_SUFFIX, ""))
    try:
        if variant is None:
            row = await conn.fetchrow(
                "SELECT prompt_text, token_count FROM public.persona_bank "
                "WHERE role = $1 AND tier = $2 AND variant IS NULL",
                role,
                tier,
            )
        else:
            row = await conn.fetchrow(
                "SELECT prompt_text, token_count FROM public.persona_bank "
                "WHERE role = $1 AND tier = $2 AND variant = $3",
                role,
                tier,
                variant,
            )
    finally:
        await conn.close()
    if row is None:
        return None
    return {"prompt_text": row["prompt_text"], "token_count": row["token_count"]}


@app.get("/dispatcher/persona")
async def dispatcher_persona(
    role: str, tier: str = "standard", variant: str | None = None
) -> dict[str, Any]:
    """Look up a role's system prompt at spawn time (persona_bank_v1).

    ``variant`` omitted resolves the default persona for the role+tier. Returns
    404 when no persona matches and 503 when persona_bank is unreachable.
    """
    try:
        persona = await _fetch_persona(role, tier, variant)
    except Exception as exc:  # noqa: BLE001 — DB failure is 503, not a 404 miss
        logger.warning("persona lookup failed role=%s tier=%s: %s", role, tier, exc)
        raise HTTPException(status_code=503, detail="persona_bank unavailable") from exc
    if persona is None:
        raise HTTPException(
            status_code=404,
            detail=f"no persona for role={role} tier={tier} variant={variant}",
        )
    return persona


# ---------------------------------------------------------------------------
# /dispatcher/task_dead_letter + /dispatcher/task_crash_retry
# Crash-recovery DB callbacks (Agency_OS-avii). Fail-open — never 5xx.
# ---------------------------------------------------------------------------


class TaskDeadLetterRequest(BaseModel):
    task_id: str


class TaskCrashRetryRequest(BaseModel):
    task_id: str


def _db_dsn() -> str:
    """Return a psycopg-compatible DSN from DATABASE_URL or SUPABASE_DB_URL."""
    raw = os.environ.get("DATABASE_URL") or os.environ.get("SUPABASE_DB_URL", "")
    return raw.replace("+asyncpg", "").replace("postgresql+asyncpg://", "postgresql://", 1)


@app.post("/dispatcher/task_dead_letter")
async def dispatcher_task_dead_letter(req: TaskDeadLetterRequest) -> dict[str, Any]:
    """Mark a task as dead-lettered in Postgres after exhausting crash retries.

    Fail-open: DB errors are logged but never returned as 5xx.
    """
    import asyncio as _aio  # noqa: PLC0415  # isort:skip
    import psycopg  # noqa: PLC0415  # isort:skip

    dsn = _db_dsn()
    if not dsn:
        logger.warning(
            "task_dead_letter: no DATABASE_URL — skipping DB update task=%s", req.task_id
        )
        return {"updated": False, "reason": "no_dsn"}
    try:

        def _update() -> int:
            with psycopg.connect(dsn, prepare_threshold=None) as conn, conn.cursor() as cur:
                cur.execute(
                    "UPDATE public.tasks SET dead_lettered_at = NOW(), "
                    "retry_count = retry_count + 1 "
                    "WHERE id = %s AND dead_lettered_at IS NULL",
                    (req.task_id,),
                )
                conn.commit()
                return cur.rowcount

        rowcount = await _aio.get_running_loop().run_in_executor(None, _update)
        logger.info("task_dead_letter: updated %d row(s) for task=%s", rowcount, req.task_id)
        return {"updated": rowcount > 0}
    except Exception:  # noqa: BLE001
        logger.exception("task_dead_letter: DB error for task=%s", req.task_id)
        return {"updated": False, "reason": "exception"}


@app.post("/dispatcher/task_crash_retry")
async def dispatcher_task_crash_retry(req: TaskCrashRetryRequest) -> dict[str, Any]:
    """Increment retry_count on a crashed task row. Returns new count.

    Fail-open: never 5xx.
    """
    import asyncio as _aio  # noqa: PLC0415

    import psycopg  # noqa: PLC0415

    dsn = _db_dsn()
    if not dsn:
        return {"retry_count": -1, "reason": "no_dsn"}
    try:

        def _update() -> int:
            with psycopg.connect(dsn, prepare_threshold=None) as conn, conn.cursor() as cur:
                cur.execute(
                    "UPDATE public.tasks SET retry_count = retry_count + 1 "
                    "WHERE id = %s RETURNING retry_count",
                    (req.task_id,),
                )
                row = cur.fetchone()
                conn.commit()
                return row[0] if row else 0

        count = await _aio.get_running_loop().run_in_executor(None, _update)
        return {"retry_count": count}
    except Exception:  # noqa: BLE001
        logger.exception("task_crash_retry: DB error for task=%s", req.task_id)
        return {"retry_count": -1, "reason": "exception"}


# ---------------------------------------------------------------------------
# /dispatcher/chain_status — live V1 chain run status + per-hop cost view
#
# Reads chain state from v1_chain_orchestrator's STATE_FILE (V1_CHAIN_STATE_FILE
# env override; default /tmp/v1_chain_state.json — same path the orchestrator
# writes to) and sums cost_usd × USD_TO_AUD per chain from
# keiracom_spawn_attribution. Lets Dave see a chain run in progress: which
# steps are done, what step is current, $AUD spent so far per chain.
#
# KNOWN SCHEMA GAP (TODO follow-up KEI):
# keiracom_spawn_attribution has no chain_id column yet — cost is summed via
# a source_id heuristic (matches `chain_id` or `task_id`). This will return
# 0.0 until the attribution writer starts logging chain_id/task_id as the
# source_id for chain spawns, OR a dedicated chain_id column lands. Similarly
# there is no latency_ms column, so latency_ms_so_far is 0.0 for V1.
# ---------------------------------------------------------------------------

_CHAIN_STATE_FILE_ENV = "V1_CHAIN_STATE_FILE"
_DEFAULT_CHAIN_STATE_FILE = "/tmp/v1_chain_state.json"
# LAW II — Australia First. 1 USD = 1.55 AUD per CLAUDE.md.
_USD_TO_AUD_RATE = 1.55


def _load_chain_state() -> dict[str, Any]:
    """Load v1_chain_orchestrator state from STATE_FILE.

    Fail-open: returns {} on missing file, malformed JSON, or any read error —
    the endpoint serves {"chains": []} rather than 500. State path is the
    SAME path the orchestrator writes to (V1_CHAIN_STATE_FILE env override or
    /tmp/v1_chain_state.json default), so this is a read of authoritative state.
    """
    path = Path(os.environ.get(_CHAIN_STATE_FILE_ENV, _DEFAULT_CHAIN_STATE_FILE))
    try:
        if not path.is_file():
            return {}
        loaded = json.loads(path.read_text())
        return loaded if isinstance(loaded, dict) else {}
    except Exception as exc:  # noqa: BLE001 — fail-open
        logger.warning("chain_status: failed to load %s: %s", path, exc)
        return {}


async def _chain_cost_aud(chain_id: str, task_id: str) -> float:
    """Best-effort SUM(cost_usd) × 1.55 from keiracom_spawn_attribution for one chain.

    No chain_id column exists yet, so this matches via source_id ∈ {chain_id,
    task_id}. Fail-open: returns 0.0 on DSN absent, asyncpg unavailable, DB
    error, or no matching rows. LAW II currency: USD → AUD via USD_TO_AUD_RATE.
    """
    dsn = os.environ.get(_PERSONA_DSN_ENV)
    if not dsn:
        return 0.0
    try:
        import asyncpg  # noqa: PLC0415 — deferred (optional in test envs)

        conn = await asyncpg.connect(dsn.replace(_ASYNCPG_DSN_SUFFIX, ""))
        try:
            row = await conn.fetchrow(
                "SELECT COALESCE(SUM(cost_usd), 0)::float8 AS s "
                "FROM public.keiracom_spawn_attribution "
                "WHERE source_id = ANY($1::text[])",
                [chain_id, task_id],
            )
        finally:
            await conn.close()
        return float(row["s"]) * _USD_TO_AUD_RATE if row else 0.0
    except Exception as exc:  # noqa: BLE001 — fail-open: never 500 the status endpoint
        logger.warning("chain_status: cost sum failed for chain=%s: %s", chain_id, exc)
        return 0.0


@app.get("/dispatcher/chain_status")
async def dispatcher_chain_status() -> dict[str, Any]:
    """Live V1 chain run status: per-chain state + per-hop cost accumulation.

    Returns ``{"chains": [...]}`` — one row per active chain in STATE_FILE,
    each carrying chain_id, current_step, steps_done, started_ts,
    cost_aud_so_far, latency_ms_so_far. Empty list when no chains active.
    Fail-open at every leg: state-file missing → []; DB unreachable → cost 0.0.
    """
    state = _load_chain_state()
    chains: list[dict[str, Any]] = []
    for chain_id, chain in state.items():
        if not isinstance(chain, dict):
            continue
        task_id = str(chain.get("task_id") or chain_id)
        cost_aud = await _chain_cost_aud(chain_id, task_id)
        chains.append(
            {
                "chain_id": chain_id,
                "current_step": chain.get("current_step", ""),
                "steps_done": chain.get("steps_done", []),
                "started_ts": float(chain.get("started_ts") or 0.0),
                "cost_aud_so_far": cost_aud,
                # TODO: keiracom_spawn_attribution has no latency_ms column yet.
                "latency_ms_so_far": 0.0,
            }
        )
    return {"chains": chains}
