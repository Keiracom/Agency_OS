"""
FILE: src/api/routes/health.py
PURPOSE: Health check endpoints for Railway/Docker deployment
PHASE: 7 (API Routes)
TASK: API-003
DEPENDENCIES:
  - src/integrations/supabase.py
  - src/integrations/redis.py
  - src/config/settings.py
RULES APPLIED:
  - Rule 1: Follow blueprint exactly
  - Health checks for database, Redis, and Prefect connectivity
  - Readiness vs liveness separation for Kubernetes-style orchestration
"""

from typing import Literal

import httpx
from fastapi import APIRouter, status
from pydantic import BaseModel
from sqlalchemy import text

from src.config.settings import settings
from src.integrations.redis import get_redis
from src.integrations.supabase import get_db_session as get_async_session

# ============================================
# Response Models
# ============================================


class ComponentStatus(BaseModel):
    """Status of a single component."""

    status: Literal["healthy", "unhealthy", "unknown"]
    message: str | None = None
    latency_ms: float | None = None


class HealthResponse(BaseModel):
    """Basic health check response."""

    status: Literal["healthy", "unhealthy"]
    service: str
    version: str


class ReadinessResponse(BaseModel):
    """Readiness check response with all component statuses."""

    status: Literal["ready", "not_ready", "degraded"]
    service: str
    version: str
    components: dict[str, ComponentStatus]


class LivenessResponse(BaseModel):
    """Liveness check response (simple alive check)."""

    status: Literal["alive"]
    service: str
    version: str


# ============================================
# Router
# ============================================


router = APIRouter(
    prefix="/health",
    tags=["health"],
)


# ============================================
# Helper Functions
# ============================================


async def check_database() -> ComponentStatus:
    """
    Check database connectivity and measure latency.

    Returns:
        ComponentStatus with database health information.
    """
    import time

    try:
        start = time.perf_counter()

        async with get_async_session() as session:
            await session.execute(text("SELECT 1"))

        latency = (time.perf_counter() - start) * 1000  # Convert to ms

        return ComponentStatus(
            status="healthy",
            message="Connected",
            latency_ms=round(latency, 2)
        )
    except Exception as e:
        return ComponentStatus(
            status="unhealthy",
            message=f"Connection failed: {str(e)[:100]}"
        )


async def check_redis() -> ComponentStatus:
    """
    Check Redis connectivity and measure latency.

    Returns:
        ComponentStatus with Redis health information.
    """
    import time

    try:
        start = time.perf_counter()

        redis = await get_redis()
        await redis.ping()

        latency = (time.perf_counter() - start) * 1000  # Convert to ms

        return ComponentStatus(
            status="healthy",
            message="Connected",
            latency_ms=round(latency, 2)
        )
    except Exception as e:
        return ComponentStatus(
            status="unhealthy",
            message=f"Connection failed: {str(e)[:100]}"
        )


async def check_prefect() -> ComponentStatus:
    """
    Check Prefect server connectivity.

    Returns:
        ComponentStatus with Prefect health information.
    """
    import time

    try:
        start = time.perf_counter()

        # Try to reach Prefect API health endpoint
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{settings.prefect_api_url}/health")

        latency = (time.perf_counter() - start) * 1000  # Convert to ms

        if response.status_code == 200:
            return ComponentStatus(
                status="healthy",
                message="Connected",
                latency_ms=round(latency, 2)
            )
        else:
            return ComponentStatus(
                status="unhealthy",
                message=f"HTTP {response.status_code}"
            )
    except Exception as e:
        return ComponentStatus(
            status="unhealthy",
            message=f"Connection failed: {str(e)[:100]}"
        )


# ============================================
# Endpoints
# ============================================


@router.get(
    "",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Basic health check",
    description="Simple health check that returns 200 if the service is running. Used by load balancers."
)
async def health_check() -> HealthResponse:
    """
    Basic health check endpoint.

    Returns service status without checking dependencies.
    Useful for load balancer health checks.

    Returns:
        HealthResponse with basic service information.
    """
    return HealthResponse(
        status="healthy",
        service="agency-os-api",
        version="3.0.0"
    )


@router.get(
    "/ready",
    response_model=ReadinessResponse,
    summary="Readiness check",
    description="Check if all components (database, Redis, Prefect) are ready. Used by Kubernetes readiness probes."
)
async def readiness_check() -> ReadinessResponse:
    """
    Readiness check endpoint.

    Checks all critical components:
    - Database (PostgreSQL via Supabase)
    - Redis (cache)
    - Prefect (workflow orchestration)

    Status logic:
    - ready: All components healthy
    - degraded: Some components unhealthy but service can operate
    - not_ready: Critical components unhealthy

    Returns:
        ReadinessResponse with component status details.
    """
    # Check all components in parallel
    import asyncio

    db_status, redis_status, prefect_status = await asyncio.gather(
        check_database(),
        check_redis(),
        check_prefect(),
        return_exceptions=True
    )

    # Handle any exceptions from gather
    if isinstance(db_status, Exception):
        db_status = ComponentStatus(status="unhealthy", message=str(db_status))
    if isinstance(redis_status, Exception):
        redis_status = ComponentStatus(status="unhealthy", message=str(redis_status))
    if isinstance(prefect_status, Exception):
        prefect_status = ComponentStatus(status="unhealthy", message=str(prefect_status))

    components = {
        "database": db_status,
        "redis": redis_status,
        "prefect": prefect_status
    }

    # Determine overall status
    healthy_count = sum(1 for c in components.values() if c.status == "healthy")

    if healthy_count == len(components):
        overall_status = "ready"
    elif db_status.status == "healthy":
        # Database is critical, if it's healthy we're degraded but operational
        overall_status = "degraded"
    else:
        # Database unhealthy = not ready
        overall_status = "not_ready"

    return ReadinessResponse(
        status=overall_status,
        service="agency-os-api",
        version="3.0.0",
        components=components
    )


@router.get(
    "/live",
    response_model=LivenessResponse,
    status_code=status.HTTP_200_OK,
    summary="Liveness check",
    description="Simple liveness check that confirms the service is alive. Used by Kubernetes liveness probes."
)
async def liveness_check() -> LivenessResponse:
    """
    Liveness check endpoint.

    Confirms the service is alive and responding.
    Does not check dependencies - just confirms the process is running.

    Used by Kubernetes liveness probes to detect deadlocked processes.

    Returns:
        LivenessResponse confirming service is alive.
    """
    return LivenessResponse(
        status="alive",
        service="agency-os-api",
        version="3.0.0"
    )


# ============================================
# VERIFICATION CHECKLIST
# ============================================
# [x] Contract comment at top
# [x] FastAPI router with health endpoints
# [x] GET /health - Basic health check (returns 200)
# [x] GET /health/ready - Readiness check (all components)
# [x] GET /health/live - Liveness check (just alive)
# [x] Check database connectivity with latency
# [x] Check Redis connectivity with latency
# [x] Check Prefect connectivity with latency
# [x] Return component status in response
# [x] Response models with Pydantic
# [x] Status logic: ready/degraded/not_ready
# [x] All functions have type hints
# [x] All functions have docstrings
# [x] No hardcoded credentials
# [x] Async operations with asyncio.gather for parallel checks
# [x] Exception handling for component checks
# [x] Latency measurement in milliseconds
