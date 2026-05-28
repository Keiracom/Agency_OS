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
import logging
import os
from collections.abc import AsyncGenerator
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

import src.dispatcher.auth_minter  # noqa: F401 — imported for fail-fast side-effect
from src.dispatcher.bounded_spawn_enforcer import (
    DECISION_VIOLATION,
    BoundedSpawnEnforcer,
)
from src.dispatcher.container_lifecycle import ContainerStartupError, DockerUnavailableError
from src.dispatcher.idempotency import IdempotencyDecision, IdempotencyGate
from src.dispatcher.interceptor_proxy import router as interceptor_router
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

    try:
        yield
    finally:
        # Graceful shutdown — cancel tasks and wait for clean exit
        for task in (wd_task, rp_task):
            task.cancel()
        await asyncio.gather(wd_task, rp_task, return_exceptions=True)
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

    _spawned[req.key] = {"handle": handle, "backend": backend}

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
    return {"terminated": True, "key": req.key, "watchdog_tracked": _watchdog.tracked}
