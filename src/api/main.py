"""
FILE: src/api/main.py
PURPOSE: FastAPI application entrypoint with middleware and routers
PHASE: 7 (API Routes)
TASK: API-001
DEPENDENCIES:
  - src/config/settings.py
  - src/integrations/supabase.py
  - src/integrations/redis.py
  - src/exceptions.py
RULES APPLIED:
  - Rule 1: Follow blueprint exactly
  - Rule 19: Connection pool limits (pool_size=5, max_overflow=10)
  - Health check for Railway/Docker deployment
"""

import logging
import time
from contextlib import asynccontextmanager
from typing import Any
from uuid import UUID

from fastapi import FastAPI, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from src.config.settings import settings
from src.exceptions import (
    AgencyOSError,
    AISpendLimitError,
    AuthenticationError,
    AuthorizationError,
    ResourceNotFoundError,
    RateLimitError,
    ValidationError,
)
from src.integrations.redis import close_redis, get_redis
from src.integrations.supabase import cleanup as close_db, get_db_session as get_async_session

# Configure logging
logging.basicConfig(
    level=logging.INFO if settings.ENV != "development" else logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("agency_os.api")


# ============================================
# Lifespan Context Manager
# ============================================


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.

    Handles startup and shutdown events:
    - Startup: Verify database and Redis connections
    - Shutdown: Close all connections gracefully
    """
    # Startup
    logger.info("Starting Agency OS API...")

    # Verify database connection
    try:
        async with get_async_session() as session:
            await session.execute("SELECT 1")
        logger.info("Database connection verified")
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        # Don't raise - let Railway health check detect issues

    # Verify Redis connection
    try:
        redis = await get_redis()
        await redis.ping()
        logger.info("Redis connection verified")
    except Exception as e:
        logger.error(f"Redis connection failed: {e}")

    logger.info("Agency OS API started successfully")

    yield

    # Shutdown
    logger.info("Shutting down Agency OS API...")
    await close_db()
    await close_redis()
    logger.info("Agency OS API shutdown complete")


# ============================================
# Application Instance
# ============================================


app = FastAPI(
    title="Agency OS API",
    description="Automated acquisition engine for marketing agencies",
    version="3.0.0",
    docs_url="/docs" if settings.ENV != "production" else None,
    redoc_url="/redoc" if settings.ENV != "production" else None,
    lifespan=lifespan,
)


# ============================================
# Middleware
# ============================================


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Log all incoming requests with timing."""

    async def dispatch(self, request: Request, call_next):
        start_time = time.time()

        # Get request ID from header or generate
        request_id = request.headers.get("X-Request-ID", "")

        # Add request ID to state for use in handlers
        request.state.request_id = request_id

        # Process request
        response = await call_next(request)

        # Calculate duration
        duration = time.time() - start_time

        # Log request (skip health checks to reduce noise)
        if request.url.path not in ["/health", "/", "/favicon.ico"]:
            logger.info(
                f"{request.method} {request.url.path} - {response.status_code} - {duration:.3f}s"
            )

        # Add timing header
        response.headers["X-Response-Time"] = f"{duration:.3f}s"
        if request_id:
            response.headers["X-Request-ID"] = request_id

        return response


class ClientContextMiddleware(BaseHTTPMiddleware):
    """Extract client context from JWT for multi-tenancy."""

    async def dispatch(self, request: Request, call_next):
        # Initialize context (will be populated by auth dependency)
        request.state.client_id = None
        request.state.user_id = None
        request.state.membership_role = None

        return await call_next(request)


# Add middleware in order (first added = outermost)
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(ClientContextMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.ENV == "development" else settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================
# Exception Handlers
# ============================================


@app.exception_handler(ValidationError)
async def validation_error_handler(request: Request, exc: ValidationError):
    """Handle validation errors."""
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "error": "validation_error",
            "message": str(exc),
            "field": exc.field if hasattr(exc, "field") else None,
        },
    )


@app.exception_handler(RequestValidationError)
async def request_validation_error_handler(
    request: Request, exc: RequestValidationError
):
    """Handle FastAPI request validation errors."""
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": "validation_error",
            "message": "Request validation failed",
            "details": jsonable_encoder(exc.errors()),
        },
    )


@app.exception_handler(AuthenticationError)
async def authentication_error_handler(request: Request, exc: AuthenticationError):
    """Handle authentication errors."""
    return JSONResponse(
        status_code=status.HTTP_401_UNAUTHORIZED,
        content={
            "error": "authentication_error",
            "message": str(exc),
        },
    )


@app.exception_handler(AuthorizationError)
async def authorization_error_handler(request: Request, exc: AuthorizationError):
    """Handle authorization errors."""
    return JSONResponse(
        status_code=status.HTTP_403_FORBIDDEN,
        content={
            "error": "authorization_error",
            "message": str(exc),
        },
    )


@app.exception_handler(ResourceNotFoundError)
async def not_found_error_handler(request: Request, exc: ResourceNotFoundError):
    """Handle not found errors."""
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={
            "error": "not_found",
            "message": str(exc),
            "resource": exc.details.get("resource_type") if exc.details else None,
            "resource_id": exc.details.get("resource_id") if exc.details else None,
        },
    )


@app.exception_handler(RateLimitError)
async def rate_limit_error_handler(request: Request, exc: RateLimitError):
    """Handle rate limit errors."""
    return JSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        content={
            "error": "rate_limit_exceeded",
            "message": str(exc),
        },
        headers={"Retry-After": "60"},
    )


@app.exception_handler(AISpendLimitError)
async def ai_spend_limit_error_handler(request: Request, exc: AISpendLimitError):
    """Handle AI spend limit errors."""
    return JSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        content={
            "error": "ai_spend_limit_exceeded",
            "message": str(exc),
            "spent": exc.spent if hasattr(exc, "spent") else None,
            "limit": exc.limit if hasattr(exc, "limit") else None,
        },
    )


@app.exception_handler(AgencyOSError)
async def agency_os_error_handler(request: Request, exc: AgencyOSError):
    """Handle all other AgencyOS errors."""
    logger.error(f"AgencyOSError: {exc}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "internal_error",
            "message": str(exc) if settings.ENV != "production" else "An error occurred",
        },
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle unexpected exceptions."""
    logger.exception(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "internal_error",
            "message": str(exc) if settings.ENV != "production" else "An error occurred",
        },
    )


# ============================================
# Core Routes
# ============================================


@app.get("/health")
async def health_check() -> dict[str, Any]:
    """
    Health check endpoint for Railway/Docker.

    Returns service status and optional component health.
    """
    health_status = {
        "status": "healthy",
        "service": "agency-os-api",
        "version": "3.0.0",
    }

    # Check database health
    try:
        async with get_async_session() as session:
            await session.execute("SELECT 1")
        health_status["database"] = "healthy"
    except Exception:
        health_status["database"] = "unhealthy"
        health_status["status"] = "degraded"

    # Check Redis health
    try:
        redis = await get_redis()
        await redis.ping()
        health_status["redis"] = "healthy"
    except Exception:
        health_status["redis"] = "unhealthy"
        health_status["status"] = "degraded"

    return health_status


@app.get("/")
async def root() -> dict[str, Any]:
    """Root endpoint with API information."""
    return {
        "service": "Agency OS API",
        "version": "3.0.0",
        "status": "running",
        "docs": "/docs" if settings.ENV != "production" else None,
        "environment": settings.ENV,
    }


# ============================================
# Router Includes
# ============================================

from src.api.routes.admin import router as admin_router
from src.api.routes.campaign_generation import router as campaign_generation_router
from src.api.routes.campaigns import router as campaigns_router
from src.api.routes.health import router as health_router
from src.api.routes.leads import router as leads_router
from src.api.routes.meetings import router as meetings_router
from src.api.routes.patterns import router as patterns_router
from src.api.routes.replies import router as replies_router
from src.api.routes.reports import router as reports_router
from src.api.routes.webhooks import router as webhooks_router
from src.api.routes.webhooks_outbound import router as webhooks_outbound_router

app.include_router(health_router, prefix="/api/v1")
app.include_router(campaigns_router, prefix="/api/v1")
app.include_router(campaign_generation_router, prefix="/api/v1")
app.include_router(leads_router, prefix="/api/v1")
app.include_router(webhooks_router, prefix="/api/v1/webhooks")
app.include_router(webhooks_outbound_router, prefix="/api/v1/webhooks-outbound")
app.include_router(reports_router, prefix="/api/v1")
app.include_router(admin_router, prefix="/api/v1")
app.include_router(replies_router, prefix="/api/v1")
app.include_router(meetings_router, prefix="/api/v1")
# Phase 16: Conversion Intelligence
app.include_router(patterns_router, prefix="/api/v1/patterns")


# ============================================
# VERIFICATION CHECKLIST
# ============================================
# [x] Contract comment at top
# [x] Lifespan context manager for startup/shutdown
# [x] Database connection verification on startup
# [x] Redis connection verification on startup
# [x] Graceful shutdown with connection cleanup
# [x] Request logging middleware with timing
# [x] Client context middleware for multi-tenancy
# [x] CORS middleware with environment-aware origins
# [x] Exception handlers for all custom exceptions
# [x] Health check with component status
# [x] Root endpoint with API info
# [x] No hardcoded credentials
# [x] Environment-aware logging level
# [x] Docs disabled in production
# [x] Router include placeholders ready
