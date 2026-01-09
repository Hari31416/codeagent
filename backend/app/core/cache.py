"""
Datara Redis Cache Service

Async Redis cache with connection pooling and JSON serialization.
"""

import asyncio
import json
from typing import Any, Awaitable, Callable

import redis.asyncio as redis
from redis.asyncio.connection import ConnectionPool

from app.config import settings
from app.shared.logging import get_logger

logger = get_logger(__name__)


class CacheService:
    """
    Async Redis cache service with connection pooling.

    Features:
    - Async operations with redis-py
    - JSON serialization for complex objects
    - Global TTL configurable via REDIS_DEFAULT_TTL environment variable
    - Graceful degradation on errors
    """

    _pool: ConnectionPool | None = None
    _client: redis.Redis | None = None

    def __init__(self, default_ttl: int | None = None):
        """
        Initialize cache service.

        Args:
            default_ttl: Default TTL in seconds. If None, uses REDIS_DEFAULT_TTL
                        from config (defaults to 300s / 5 minutes).
        """
        self.default_ttl = default_ttl or settings.redis_default_ttl

    @classmethod
    async def get_client(cls) -> redis.Redis:
        """Get or create Redis client with connection pooling."""
        if cls._client is None:
            cls._pool = ConnectionPool.from_url(
                settings.redis_url,
                decode_responses=True,
                max_connections=settings.redis_max_connections,
            )
            cls._client = redis.Redis(connection_pool=cls._pool)
            logger.info("Redis connection pool initialized")
        return cls._client

    @classmethod
    async def close(cls) -> None:
        """Close Redis connection pool."""
        if cls._client:
            await cls._client.aclose()
            cls._client = None
        if cls._pool:
            await cls._pool.disconnect()
            cls._pool = None
            logger.info("Redis connection pool closed")

    async def get(self, key: str) -> str | None:
        """
        Get a value from cache.

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found
        """
        try:
            client = await self.get_client()
            value = await client.get(key)
            if value:
                logger.debug("Cache hit", key=key)
            else:
                logger.debug("Cache miss", key=key)
            return value
        except Exception as e:
            logger.warning("Cache get failed", key=key, error=str(e))
            return None

    async def set(
        self,
        key: str,
        value: str,
        ttl_seconds: int | None = None,
    ) -> bool:
        """
        Set a value in cache.

        Args:
            key: Cache key
            value: Value to cache
            ttl_seconds: TTL in seconds. If None, uses default_ttl.

        Returns:
            True if successful, False otherwise
        """
        ttl = ttl_seconds if ttl_seconds is not None else self.default_ttl
        try:
            client = await self.get_client()
            await client.set(key, value, ex=ttl)
            logger.debug("Cache set", key=key, ttl=ttl)
            return True
        except Exception as e:
            logger.warning("Cache set failed", key=key, error=str(e))
            return False

    async def delete(self, key: str) -> bool:
        """
        Delete a key from cache.

        Args:
            key: Cache key

        Returns:
            True if key was deleted, False otherwise
        """
        try:
            client = await self.get_client()
            result = await client.delete(key)
            logger.debug("Cache delete", key=key, deleted=bool(result))
            return bool(result)
        except Exception as e:
            logger.warning("Cache delete failed", key=key, error=str(e))
            return False

    async def exists(self, key: str) -> bool:
        """
        Check if a key exists in cache.

        Args:
            key: Cache key

        Returns:
            True if key exists, False otherwise
        """
        try:
            client = await self.get_client()
            result = await client.exists(key)
            return bool(result)
        except Exception as e:
            logger.warning("Cache exists check failed", key=key, error=str(e))
            return False

    async def get_json(self, key: str) -> dict[str, Any] | list | None:
        """
        Get a JSON value from cache.

        Args:
            key: Cache key

        Returns:
            Parsed JSON object or None if not found
        """
        value = await self.get(key)
        if value:
            try:
                return json.loads(value)
            except json.JSONDecodeError as e:
                logger.warning("Cache JSON decode failed", key=key, error=str(e))
                return None
        return None

    async def set_json(
        self,
        key: str,
        value: dict[str, Any] | list,
        ttl_seconds: int | None = None,
    ) -> bool:
        """
        Set a JSON value in cache.

        Args:
            key: Cache key
            value: Value to serialize and cache
            ttl_seconds: TTL in seconds. If None, uses default_ttl.

        Returns:
            True if successful, False otherwise
        """
        try:
            json_str = json.dumps(value, default=str)
            return await self.set(key, json_str, ttl_seconds)
        except (TypeError, ValueError) as e:
            logger.warning("Cache JSON encode failed", key=key, error=str(e))
            return False

    async def get_or_set(
        self,
        key: str,
        factory: Callable[[], Awaitable[Any]],
        ttl_seconds: int | None = None,
    ) -> Any:
        """
        Get value from cache or compute and cache it.

        Uses a distributed lock (Redis SETNX) to prevent cache stampede/race conditions.

        Args:
            key: Cache key
            factory: Async callable to compute value if not cached
            ttl_seconds: TTL in seconds. If None, uses default_ttl.

        Returns:
            Cached or computed value
        """
        value = await self.get_json(key)
        if value is not None:
            return value

        lock_key = f"{key}:lock"
        client = await self.get_client()

        # Try to acquire lock
        # nx=True means SET if Not eXists
        # ex=30 means expire after 30 seconds to prevent deadlocks
        if await client.set(lock_key, "1", nx=True, ex=30):
            try:
                # Re-check cache after acquiring lock
                value = await self.get_json(key)
                if value is not None:
                    return value

                computed = await factory()
                await self.set_json(key, computed, ttl_seconds)
                return computed
            finally:
                await client.delete(lock_key)
        else:
            # Wait and retry (exponential backoff could be better, but simple retry is fine for now)
            await asyncio.sleep(0.1)
            return await self.get_or_set(key, factory, ttl_seconds)

    async def clear_pattern(self, pattern: str) -> int:
        """
        Delete all keys matching a pattern.

        Args:
            pattern: Glob-style pattern (e.g., "user:*")

        Returns:
            Number of keys deleted
        """
        try:
            client = await self.get_client()
            keys = []
            async for key in client.scan_iter(match=pattern):
                keys.append(key)

            if keys:
                deleted = await client.delete(*keys)
                logger.info(
                    "Cache cleared by pattern", pattern=pattern, deleted=deleted
                )
                return deleted
            return 0
        except Exception as e:
            logger.warning("Cache clear pattern failed", pattern=pattern, error=str(e))
            return 0


# Default cache instance
cache = CacheService()
