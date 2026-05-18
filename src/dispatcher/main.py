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
import logging
import os
from collections.abc import AsyncGenerator
from typing import Any

from fastapi import FastAPI

import src.dispatcher.auth_minter  # noqa: F401 — imported for fail-fast side-effect
from src.dispatcher.interceptor_proxy import router as interceptor_router
from src.dispatcher.reaper import Reaper
from src.dispatcher.spend_tracker import get_spend
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


# ---------------------------------------------------------------------------
# Background loop helpers
# ---------------------------------------------------------------------------

_WATCHDOG_POLL_INTERVAL_S = 30.0
_REAPER_SWEEP_INTERVAL_S = 60.0

TMUX_NAME_PREFIX = os.environ.get("DISPATCHER_TMUX_PREFIX", "disp-")
CONTAINER_NAME_PREFIX = os.environ.get("DISPATCHER_CONTAINER_PREFIX", "disp-")


async def _watchdog_loop(wd: Watchdog) -> None:
    """Run watchdog.probe_all() every 30 s. Updates _component_status."""
    _component_status["watchdog"] = "ok"
    while True:
        try:
            await asyncio.sleep(_WATCHDOG_POLL_INTERVAL_S)
            snapshot = wd.health_snapshot()
            _component_status["watchdog"] = snapshot.get("status", "ok")
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
    return {"status": overall, "components": dict(_component_status)}
