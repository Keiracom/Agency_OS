"""
FILE: src/integrations/supabase.py
PURPOSE: Async Supabase client with connection pool limits
PHASE: 1 (Foundation + DevOps)
TASK: INT-001
DEPENDENCIES:
  - src/config/settings.py
  - src/exceptions.py
RULES APPLIED:
  - Rule 1: Follow blueprint exactly
  - Rule 11: Session passed as argument (for engines)
  - Rule 19: Connection pool limits (pool_size=5, max_overflow=10)
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from src.config.settings import settings
from src.exceptions import IntegrationError
from supabase import Client, create_client

# ============================================
# SQLAlchemy Async Engine (for ORM operations)
# ============================================


def create_database_engine() -> AsyncEngine:
    """
    Create async SQLAlchemy engine with pool configuration.

    Uses Transaction Pooler (Port 6543) for application connections.
    Pool limits: pool_size=5, max_overflow=10 (Rule 19)

    Note: Supabase Supavisor (transaction pooler) doesn't support prepared
    statements, so we disable statement caching.
    """
    return create_async_engine(
        settings.database_url,
        echo=settings.debug,
        connect_args={
            "statement_cache_size": 0,
            "prepared_statement_cache_size": 0,
        },
        **settings.database_pool_config,
    )


def create_database_engine_no_pool() -> AsyncEngine:
    """
    Create async SQLAlchemy engine without pooling.

    Used for one-off operations or testing.
    """
    return create_async_engine(
        settings.database_url,
        echo=settings.debug,
        poolclass=NullPool,
    )


# Global engine instance
_engine: AsyncEngine | None = None


def get_engine() -> AsyncEngine:
    """Get or create the global database engine."""
    global _engine
    if _engine is None:
        _engine = create_database_engine()
    return _engine


async def dispose_engine() -> None:
    """Dispose of the global engine (for cleanup)."""
    global _engine
    if _engine is not None:
        await _engine.dispose()
        _engine = None


# ============================================
# Async Session Factory
# ============================================


def create_session_factory(engine: AsyncEngine | None = None) -> async_sessionmaker[AsyncSession]:
    """
    Create async session factory.

    Args:
        engine: SQLAlchemy async engine. Uses global engine if not provided.

    Returns:
        Async session maker for creating database sessions.
    """
    if engine is None:
        engine = get_engine()

    return async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )


# Global session factory
_session_factory: async_sessionmaker[AsyncSession] | None = None


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """Get or create the global session factory."""
    global _session_factory
    if _session_factory is None:
        _session_factory = create_session_factory()
    return _session_factory


@asynccontextmanager
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Context manager for database sessions.

    Usage:
        async with get_db_session() as session:
            result = await session.execute(query)

    Automatically handles commit on success and rollback on error.
    """
    factory = get_session_factory()
    session = factory()
    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency for FastAPI routes.

    Usage in FastAPI:
        @app.get("/items")
        async def get_items(db: AsyncSession = Depends(get_db)):
            ...
    """
    async with get_db_session() as session:
        yield session


# ============================================
# Supabase Client (for Auth & Realtime)
# ============================================

_supabase_client: Client | None = None
_supabase_service_client: Client | None = None


def get_supabase_client() -> Client:
    """
    Get Supabase client for auth and public operations.

    Uses the anon/public key for RLS-enforced operations.
    """
    global _supabase_client

    if _supabase_client is None:
        if not settings.supabase_url or not settings.supabase_key:
            raise IntegrationError(
                service="supabase",
                message="Supabase URL and key are required",
            )
        _supabase_client = create_client(
            settings.supabase_url,
            settings.supabase_key,
        )

    return _supabase_client


def get_supabase_service_client() -> Client:
    """
    Get Supabase client with service role (bypasses RLS).

    Used for backend operations that need full access.
    WARNING: Only use in trusted backend code.
    """
    global _supabase_service_client

    if _supabase_service_client is None:
        if not settings.supabase_url or not settings.supabase_service_key:
            raise IntegrationError(
                service="supabase",
                message="Supabase URL and service key are required",
            )
        _supabase_service_client = create_client(
            settings.supabase_url,
            settings.supabase_service_key,
        )

    return _supabase_service_client


# ============================================
# Health Check
# ============================================


async def check_database_health() -> dict:
    """
    Check database connection health.

    Returns:
        Dict with status and connection info.
    """
    try:
        async with get_db_session() as session:
            result = await session.execute(text("SELECT 1"))
            result.scalar()
            return {
                "status": "healthy",
                "database": "connected",
                "pool_size": settings.db_pool_size,
                "max_overflow": settings.db_max_overflow,
            }
    except Exception as e:
        return {
            "status": "unhealthy",
            "database": "disconnected",
            "error": str(e),
        }


# ============================================
# Cleanup
# ============================================


async def cleanup() -> None:
    """Cleanup all database connections."""
    await dispose_engine()


# ============================================
# VERIFICATION CHECKLIST
# ============================================
# [x] Contract comment at top
# [x] No hardcoded credentials
# [x] Pool config: pool_size=5, max_overflow=10 (Rule 19)
# [x] Transaction Pooler (Port 6543) for app connections
# [x] Async SQLAlchemy engine
# [x] Async session factory
# [x] get_db_session() context manager
# [x] get_db() dependency for FastAPI
# [x] Supabase client (anon key, for auth)
# [x] Supabase service client (service key, bypasses RLS)
# [x] Health check function
# [x] Cleanup function
# [x] All functions have type hints
# [x] All functions have docstrings
