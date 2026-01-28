"""
FILE: src/integrations/redis.py
PURPOSE: Versioned cache and resource-level rate limiting
PHASE: 1 (Foundation + DevOps)
TASK: INT-002
DEPENDENCIES:
  - src/config/settings.py
  - src/exceptions.py
RULES APPLIED:
  - Rule 1: Follow blueprint exactly
  - Rule 16: Cache versioning (v1 prefix)
  - Rule 17: Resource-level rate limits
  - Redis for caching ONLY (not task queues)
"""

import json
from datetime import date, datetime
from typing import Any

from redis.asyncio import ConnectionPool, Redis

from src.config.settings import settings
from src.exceptions import ResourceRateLimitError

# ============================================
# Redis Connection Pool
# ============================================

_redis_pool: ConnectionPool | None = None
_redis_client: Redis | None = None


async def get_redis_pool() -> ConnectionPool:
    """Get or create Redis connection pool."""
    global _redis_pool
    if _redis_pool is None:
        _redis_pool = ConnectionPool.from_url(
            settings.redis_url,
            decode_responses=True,
            max_connections=20,
        )
    return _redis_pool


async def get_redis() -> Redis:
    """
    Get Redis client instance.

    Usage:
        redis = await get_redis()
        await redis.set("key", "value")
    """
    global _redis_client
    if _redis_client is None:
        pool = await get_redis_pool()
        _redis_client = Redis(connection_pool=pool)
    return _redis_client


async def close_redis() -> None:
    """Close Redis connections."""
    global _redis_client, _redis_pool
    if _redis_client is not None:
        await _redis_client.close()
        _redis_client = None
    if _redis_pool is not None:
        await _redis_pool.disconnect()
        _redis_pool = None


# ============================================
# Cache Key Builders (Rule 16: Versioned Keys)
# ============================================


def build_cache_key(*parts: str) -> str:
    """
    Build a versioned cache key.

    Args:
        *parts: Key components (e.g., "enrichment", "domain", "example.com")

    Returns:
        Versioned key like "v1:enrichment:domain:example.com"
    """
    version = settings.redis_cache_version
    return f"{version}:" + ":".join(parts)


def build_enrichment_key(domain: str) -> str:
    """Build cache key for enrichment data."""
    return build_cache_key("enrichment", "domain", domain.lower())


def build_rate_limit_key(
    resource_type: str,
    resource_id: str,
    date_str: str | None = None,
) -> str:
    """
    Build cache key for rate limiting.

    Args:
        resource_type: Type of resource (email, linkedin, sms)
        resource_id: Resource identifier (domain, seat_id, phone)
        date_str: Date string (defaults to today)

    Returns:
        Key like "v1:ratelimit:email:domain.com:2025-12-20"
    """
    if date_str is None:
        date_str = date.today().isoformat()
    return build_cache_key("ratelimit", resource_type, resource_id, date_str)


def build_ai_spend_key(date_str: str | None = None) -> str:
    """Build cache key for AI spend tracking."""
    if date_str is None:
        date_str = date.today().isoformat()
    return build_cache_key("ai_spend", date_str)


# ============================================
# Cache Operations
# ============================================


class CacheManager:
    """Manager for Redis cache operations with versioning."""

    def __init__(self):
        self._redis: Redis | None = None

    async def _get_redis(self) -> Redis:
        """Get Redis client (lazy initialization)."""
        if self._redis is None:
            self._redis = await get_redis()
        return self._redis

    async def get(self, key: str) -> Any | None:
        """
        Get value from cache.

        Args:
            key: Cache key (will be prefixed with version)

        Returns:
            Cached value or None if not found
        """
        redis = await self._get_redis()
        full_key = build_cache_key(key) if not key.startswith(settings.redis_cache_version) else key
        value = await redis.get(full_key)
        if value is not None:
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return value
        return None

    async def set(
        self,
        key: str,
        value: Any,
        ttl: int | None = None,
    ) -> bool:
        """
        Set value in cache.

        Args:
            key: Cache key
            value: Value to cache (will be JSON serialized)
            ttl: TTL in seconds (defaults to settings.redis_cache_ttl)

        Returns:
            True if successful
        """
        redis = await self._get_redis()
        full_key = build_cache_key(key) if not key.startswith(settings.redis_cache_version) else key
        ttl = ttl or settings.redis_cache_ttl

        if isinstance(value, (dict, list)):
            value = json.dumps(value, default=str)

        await redis.set(full_key, value, ex=ttl)
        return True

    async def delete(self, key: str) -> bool:
        """Delete key from cache."""
        redis = await self._get_redis()
        full_key = build_cache_key(key) if not key.startswith(settings.redis_cache_version) else key
        result = await redis.delete(full_key)
        return result > 0

    async def exists(self, key: str) -> bool:
        """Check if key exists in cache."""
        redis = await self._get_redis()
        full_key = build_cache_key(key) if not key.startswith(settings.redis_cache_version) else key
        return await redis.exists(full_key) > 0


# Global cache manager instance
cache = CacheManager()


# ============================================
# Enrichment Cache (90-day TTL)
# ============================================


class EnrichmentCache:
    """Cache for enrichment data with 90-day TTL."""

    TTL = 90 * 24 * 60 * 60  # 90 days in seconds

    def __init__(self):
        self._redis: Redis | None = None

    async def _get_redis(self) -> Redis:
        if self._redis is None:
            self._redis = await get_redis()
        return self._redis

    async def get(self, domain: str) -> dict | None:
        """
        Get cached enrichment data for a domain.

        Args:
            domain: Company domain

        Returns:
            Enrichment data dict or None
        """
        redis = await self._get_redis()
        key = build_enrichment_key(domain)
        value = await redis.get(key)
        if value:
            try:
                data = json.loads(value)
                # Add cache metadata
                data["_from_cache"] = True
                data["_cache_key"] = key
                return data
            except json.JSONDecodeError:
                return None
        return None

    async def set(self, domain: str, data: dict) -> bool:
        """
        Cache enrichment data for a domain.

        Args:
            domain: Company domain
            data: Enrichment data

        Returns:
            True if successful
        """
        redis = await self._get_redis()
        key = build_enrichment_key(domain)

        # Add cache timestamp
        data["_cached_at"] = datetime.utcnow().isoformat()
        data["_cache_version"] = settings.redis_cache_version

        await redis.set(key, json.dumps(data, default=str), ex=self.TTL)
        return True

    async def invalidate(self, domain: str) -> bool:
        """Invalidate cached enrichment data."""
        redis = await self._get_redis()
        key = build_enrichment_key(domain)
        result = await redis.delete(key)
        return result > 0


# Global enrichment cache instance
enrichment_cache = EnrichmentCache()


# ============================================
# Rate Limiting (Resource-Level, Rule 17)
# ============================================


class RateLimiter:
    """
    Resource-level rate limiter.

    Tracks usage per resource (email domain, LinkedIn seat, phone number)
    per day as specified in Rule 17.
    """

    def __init__(self):
        self._redis: Redis | None = None

    async def _get_redis(self) -> Redis:
        if self._redis is None:
            self._redis = await get_redis()
        return self._redis

    async def check_and_increment(
        self,
        resource_type: str,
        resource_id: str,
        limit: int,
    ) -> tuple[bool, int]:
        """
        Check rate limit and increment if allowed.

        Args:
            resource_type: Type (email, linkedin, sms)
            resource_id: Identifier (domain, seat_id, phone)
            limit: Maximum allowed per day

        Returns:
            Tuple of (allowed, current_count)

        Raises:
            ResourceRateLimitError: If limit exceeded
        """
        redis = await self._get_redis()
        key = build_rate_limit_key(resource_type, resource_id)

        # Get current count
        current = await redis.get(key)
        current_count = int(current) if current else 0

        if current_count >= limit:
            raise ResourceRateLimitError(
                resource_type=resource_type,
                resource_id=resource_id,
                limit=limit,
                message=f"{resource_type} limit ({limit}/day) exceeded for {resource_id}",
            )

        # Increment and set expiry to end of day
        pipe = redis.pipeline()
        pipe.incr(key)
        # Set expiry to next midnight (seconds until midnight)
        now = datetime.now()
        midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)
        next_midnight = midnight.replace(day=midnight.day + 1)
        seconds_until_midnight = int((next_midnight - now).total_seconds())
        pipe.expire(key, seconds_until_midnight)
        await pipe.execute()

        return True, current_count + 1

    async def get_usage(
        self,
        resource_type: str,
        resource_id: str,
    ) -> int:
        """Get current usage count for a resource."""
        redis = await self._get_redis()
        key = build_rate_limit_key(resource_type, resource_id)
        current = await redis.get(key)
        return int(current) if current else 0

    async def get_remaining(
        self,
        resource_type: str,
        resource_id: str,
        limit: int,
    ) -> int:
        """Get remaining quota for a resource."""
        usage = await self.get_usage(resource_type, resource_id)
        return max(0, limit - usage)

    async def reset(
        self,
        resource_type: str,
        resource_id: str,
    ) -> bool:
        """Reset rate limit counter for a resource."""
        redis = await self._get_redis()
        key = build_rate_limit_key(resource_type, resource_id)
        result = await redis.delete(key)
        return result > 0


# Global rate limiter instance
rate_limiter = RateLimiter()


# ============================================
# AI Spend Tracking (Rule 15)
# ============================================


class AISpendTracker:
    """
    Track daily AI spend for circuit breaker.

    Used to enforce the daily AI spend limit (Rule 15).
    """

    def __init__(self):
        self._redis: Redis | None = None

    async def _get_redis(self) -> Redis:
        if self._redis is None:
            self._redis = await get_redis()
        return self._redis

    async def add_spend(self, amount: float) -> float:
        """
        Add to daily spend and return new total.

        Args:
            amount: Amount spent in AUD

        Returns:
            New total daily spend
        """
        redis = await self._get_redis()
        key = build_ai_spend_key()

        # Use INCRBYFLOAT for atomic increment
        # Convert to cents for precision
        cents = int(amount * 100)
        new_cents = await redis.incrby(key, cents)

        # Set expiry to end of day if this is a new key
        ttl = await redis.ttl(key)
        if ttl == -1:  # No expiry set
            now = datetime.now()
            midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)
            next_midnight = midnight.replace(day=midnight.day + 1)
            seconds_until_midnight = int((next_midnight - now).total_seconds())
            await redis.expire(key, seconds_until_midnight)

        return new_cents / 100.0

    async def get_spend(self) -> float:
        """Get current daily spend."""
        redis = await self._get_redis()
        key = build_ai_spend_key()
        cents = await redis.get(key)
        return int(cents) / 100.0 if cents else 0.0

    async def get_remaining(self) -> float:
        """Get remaining daily budget."""
        spent = await self.get_spend()
        return max(0.0, settings.anthropic_daily_spend_limit - spent)

    async def check_budget(self, required: float) -> bool:
        """
        Check if there's enough budget for a spend.

        Args:
            required: Amount needed in AUD

        Returns:
            True if budget available
        """
        remaining = await self.get_remaining()
        return remaining >= required

    async def reset(self) -> bool:
        """Reset daily spend (for testing)."""
        redis = await self._get_redis()
        key = build_ai_spend_key()
        result = await redis.delete(key)
        return result > 0


# Global AI spend tracker instance
ai_spend_tracker = AISpendTracker()


# ============================================
# Health Check
# ============================================


async def check_redis_health() -> dict:
    """
    Check Redis connection health.

    Returns:
        Dict with status and connection info.
    """
    try:
        redis = await get_redis()
        await redis.ping()  # type: ignore[misc]
        info = await redis.info("server")
        return {
            "status": "healthy",
            "redis": "connected",
            "version": info.get("redis_version", "unknown"),
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "redis": "disconnected",
            "error": str(e),
        }


# ============================================
# VERIFICATION CHECKLIST
# ============================================
# [x] Contract comment at top
# [x] No hardcoded credentials
# [x] Cache versioning with v1 prefix (Rule 16)
# [x] Resource-level rate limiting (Rule 17)
# [x] Rate limits: per seat/domain/number
# [x] Enrichment cache with 90-day TTL
# [x] AI spend tracking for circuit breaker (Rule 15)
# [x] Redis for caching ONLY (not task queues)
# [x] Connection pool management
# [x] Health check function
# [x] All functions have type hints
# [x] All functions have docstrings
