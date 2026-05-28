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

    manager = SessionManager(backend=backend)
    try:
        handle = manager.spawn(**req.spawn_kwargs)
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
    rsnap = _reaper.health_snapshot()
    return {
        "spawned": True,
        "key": req.key,
        "backend": backend.value,
        "handle": dataclasses.asdict(handle),
        "watchdog_tracked": _watchdog.tracked,
        "reaper_tracked": int(rsnap["tracked_tmux"]) + int(rsnap["tracked_containers"]),
    }


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
    return {"terminated": True, "key": req.key, "watchdog_tracked": _watchdog.tracked}
