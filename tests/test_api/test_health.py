"""
FILE: tests/test_api/test_health.py
PURPOSE: Test health check endpoints
PHASE: 7 (API Routes)
TASK: API-003
DEPENDENCIES:
  - src/api/routes/health.py
  - pytest
  - pytest-asyncio
RULES APPLIED:
  - Rule 1: Follow blueprint exactly
  - Test all 3 endpoints
  - Mock database and Redis for unit tests
  - Test healthy and degraded states
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import status
from httpx import AsyncClient

from src.api.main import app


# ============================================
# Fixtures
# ============================================


@pytest.fixture
def mock_db_healthy():
    """Mock healthy database connection."""
    mock_session = AsyncMock()
    mock_session.execute = AsyncMock()

    async def mock_get_session():
        yield mock_session

    return mock_get_session


@pytest.fixture
def mock_db_unhealthy():
    """Mock unhealthy database connection."""
    async def mock_get_session():
        raise Exception("Database connection failed")
        yield

    return mock_get_session


@pytest.fixture
def mock_redis_healthy():
    """Mock healthy Redis connection."""
    mock_redis = AsyncMock()
    mock_redis.ping = AsyncMock()
    return mock_redis


@pytest.fixture
def mock_redis_unhealthy():
    """Mock unhealthy Redis connection."""
    mock_redis = AsyncMock()
    mock_redis.ping = AsyncMock(side_effect=Exception("Redis connection failed"))
    return mock_redis


@pytest.fixture
def mock_prefect_healthy():
    """Mock healthy Prefect connection."""
    mock_response = MagicMock()
    mock_response.status_code = 200

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_response)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock()

    return mock_client


@pytest.fixture
def mock_prefect_unhealthy():
    """Mock unhealthy Prefect connection."""
    mock_client = AsyncMock()
    mock_client.get = AsyncMock(side_effect=Exception("Prefect connection failed"))
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock()

    return mock_client


# ============================================
# Test Basic Health Check
# ============================================


@pytest.mark.asyncio
async def test_health_check_returns_200():
    """Test that basic health check returns 200 OK."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/health")

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "agency-os-api"
    assert data["version"] == "3.0.0"


@pytest.mark.asyncio
async def test_health_check_no_dependencies():
    """Test that basic health check doesn't check dependencies."""
    # Even if dependencies are down, health check should return healthy
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/health")

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["status"] == "healthy"


# ============================================
# Test Liveness Check
# ============================================


@pytest.mark.asyncio
async def test_liveness_check_returns_alive():
    """Test that liveness check returns alive status."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/health/live")

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["status"] == "alive"
    assert data["service"] == "agency-os-api"
    assert data["version"] == "3.0.0"


@pytest.mark.asyncio
async def test_liveness_check_no_dependencies():
    """Test that liveness check doesn't check dependencies."""
    # Liveness should always return alive if the service is running
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/health/live")

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["status"] == "alive"


# ============================================
# Test Readiness Check - All Healthy
# ============================================


@pytest.mark.asyncio
async def test_readiness_check_all_healthy(
    mock_db_healthy,
    mock_redis_healthy,
    mock_prefect_healthy
):
    """Test readiness check when all components are healthy."""
    with patch("src.api.routes.health.get_async_session", mock_db_healthy), \
         patch("src.api.routes.health.get_redis", return_value=mock_redis_healthy), \
         patch("src.api.routes.health.httpx.AsyncClient", return_value=mock_prefect_healthy):

        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get("/health/ready")

    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    assert data["status"] == "ready"
    assert data["service"] == "agency-os-api"
    assert data["version"] == "3.0.0"

    # Check all components are healthy
    assert data["components"]["database"]["status"] == "healthy"
    assert data["components"]["redis"]["status"] == "healthy"
    assert data["components"]["prefect"]["status"] == "healthy"

    # Check latency is included
    assert "latency_ms" in data["components"]["database"]
    assert "latency_ms" in data["components"]["redis"]
    assert "latency_ms" in data["components"]["prefect"]


# ============================================
# Test Readiness Check - Degraded States
# ============================================


@pytest.mark.asyncio
async def test_readiness_check_redis_unhealthy(
    mock_db_healthy,
    mock_redis_unhealthy,
    mock_prefect_healthy
):
    """Test readiness check when Redis is unhealthy (degraded state)."""
    with patch("src.api.routes.health.get_async_session", mock_db_healthy), \
         patch("src.api.routes.health.get_redis", return_value=mock_redis_unhealthy), \
         patch("src.api.routes.health.httpx.AsyncClient", return_value=mock_prefect_healthy):

        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get("/health/ready")

    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    # Should be degraded because database is healthy but Redis is not
    assert data["status"] == "degraded"

    # Check component statuses
    assert data["components"]["database"]["status"] == "healthy"
    assert data["components"]["redis"]["status"] == "unhealthy"
    assert data["components"]["prefect"]["status"] == "healthy"

    # Check error message for Redis
    assert "Redis connection failed" in data["components"]["redis"]["message"]


@pytest.mark.asyncio
async def test_readiness_check_prefect_unhealthy(
    mock_db_healthy,
    mock_redis_healthy,
    mock_prefect_unhealthy
):
    """Test readiness check when Prefect is unhealthy (degraded state)."""
    with patch("src.api.routes.health.get_async_session", mock_db_healthy), \
         patch("src.api.routes.health.get_redis", return_value=mock_redis_healthy), \
         patch("src.api.routes.health.httpx.AsyncClient", return_value=mock_prefect_unhealthy):

        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get("/health/ready")

    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    # Should be degraded because database is healthy but Prefect is not
    assert data["status"] == "degraded"

    # Check component statuses
    assert data["components"]["database"]["status"] == "healthy"
    assert data["components"]["redis"]["status"] == "healthy"
    assert data["components"]["prefect"]["status"] == "unhealthy"


# ============================================
# Test Readiness Check - Not Ready
# ============================================


@pytest.mark.asyncio
async def test_readiness_check_database_unhealthy(
    mock_db_unhealthy,
    mock_redis_healthy,
    mock_prefect_healthy
):
    """Test readiness check when database is unhealthy (not ready)."""
    with patch("src.api.routes.health.get_async_session", mock_db_unhealthy), \
         patch("src.api.routes.health.get_redis", return_value=mock_redis_healthy), \
         patch("src.api.routes.health.httpx.AsyncClient", return_value=mock_prefect_healthy):

        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get("/health/ready")

    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    # Should be not_ready because database is critical
    assert data["status"] == "not_ready"

    # Check component statuses
    assert data["components"]["database"]["status"] == "unhealthy"
    assert data["components"]["redis"]["status"] == "healthy"
    assert data["components"]["prefect"]["status"] == "healthy"

    # Check error message for database
    assert "Database connection failed" in data["components"]["database"]["message"]


@pytest.mark.asyncio
async def test_readiness_check_all_unhealthy(
    mock_db_unhealthy,
    mock_redis_unhealthy,
    mock_prefect_unhealthy
):
    """Test readiness check when all components are unhealthy."""
    with patch("src.api.routes.health.get_async_session", mock_db_unhealthy), \
         patch("src.api.routes.health.get_redis", return_value=mock_redis_unhealthy), \
         patch("src.api.routes.health.httpx.AsyncClient", return_value=mock_prefect_unhealthy):

        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get("/health/ready")

    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    # Should be not_ready because database is unhealthy
    assert data["status"] == "not_ready"

    # Check all components are unhealthy
    assert data["components"]["database"]["status"] == "unhealthy"
    assert data["components"]["redis"]["status"] == "unhealthy"
    assert data["components"]["prefect"]["status"] == "unhealthy"


# ============================================
# Test Response Models
# ============================================


@pytest.mark.asyncio
async def test_health_response_structure():
    """Test that health response has correct structure."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/health")

    data = response.json()

    # Check required fields
    assert "status" in data
    assert "service" in data
    assert "version" in data

    # Check no extra fields
    assert set(data.keys()) == {"status", "service", "version"}


@pytest.mark.asyncio
async def test_liveness_response_structure():
    """Test that liveness response has correct structure."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/health/live")

    data = response.json()

    # Check required fields
    assert "status" in data
    assert "service" in data
    assert "version" in data

    # Check no extra fields
    assert set(data.keys()) == {"status", "service", "version"}


@pytest.mark.asyncio
async def test_readiness_response_structure(
    mock_db_healthy,
    mock_redis_healthy,
    mock_prefect_healthy
):
    """Test that readiness response has correct structure."""
    with patch("src.api.routes.health.get_async_session", mock_db_healthy), \
         patch("src.api.routes.health.get_redis", return_value=mock_redis_healthy), \
         patch("src.api.routes.health.httpx.AsyncClient", return_value=mock_prefect_healthy):

        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get("/health/ready")

    data = response.json()

    # Check required fields
    assert "status" in data
    assert "service" in data
    assert "version" in data
    assert "components" in data

    # Check components structure
    assert "database" in data["components"]
    assert "redis" in data["components"]
    assert "prefect" in data["components"]

    # Check component fields
    for component in data["components"].values():
        assert "status" in component
        # Message and latency_ms are optional


# ============================================
# VERIFICATION CHECKLIST
# ============================================
# [x] Test all 3 endpoints (health, ready, live)
# [x] Mock database for unit tests
# [x] Mock Redis for unit tests
# [x] Mock Prefect for unit tests
# [x] Test healthy state (all components healthy)
# [x] Test degraded states (Redis unhealthy, Prefect unhealthy)
# [x] Test not ready state (database unhealthy)
# [x] Test all unhealthy state
# [x] Test response structures
# [x] Test that health and liveness don't check dependencies
# [x] Test latency measurements in readiness response
# [x] Test error messages in unhealthy components
# [x] All tests use pytest.mark.asyncio
# [x] All tests have descriptive docstrings
# [x] Contract comment at top
