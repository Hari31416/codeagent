"""
Datara Redis Cache Service

Async Redis cache with connection pooling, compression, and advanced locking.
"""

import asyncio
import gzip
import json
from typing import Any, Awaitable, Callable

import redis.asyncio as redis
from app.config import settings
from app.shared.logging import get_logger
from redis.asyncio.connection import ConnectionPool

logger = get_logger(__name__)


class CacheMetrics:
    """Track cache performance metrics."""

    def __init__(self):
        self.hits = 0
        self.misses = 0
        self.compression_count = 0
        self.total_compressed_bytes = 0
        self.total_original_bytes = 0

    def record_hit(self) -> None:
        self.hits += 1

    def record_miss(self) -> None:
        self.misses += 1

    def record_compression(self, original: int, compressed: int) -> None:
        self.compression_count += 1
        self.total_compressed_bytes += compressed
        self.total_original_bytes += original

    def get_hit_rate(self) -> float:
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0.0

    def get_compression_ratio(self) -> float:
        if self.total_original_bytes == 0:
            return 0.0
        return 1.0 - (self.total_compressed_bytes / self.total_original_bytes)

    def to_dict(self) -> dict[str, Any]:
        return {
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": self.get_hit_rate(),
            "compression_count": self.compression_count,
            "compression_ratio": self.get_compression_ratio(),
            "total_original_bytes": self.total_original_bytes,
            "total_compressed_bytes": self.total_compressed_bytes,
        }


class CacheService:
    """
    Async Redis cache service with multiple connection pools, compression, and metrics.

    Features:
    - Separate connection pools for different use cases
    - GZIP compression for large values (>2KB)
    - JSON serialization with compression support
    - Distributed locks with lease renewal
    - Cache metrics tracking
    - Graceful degradation on errors
    """

    _pools: dict[str, ConnectionPool | None] = {
        "default": None,
        "state": None,
        "presigned": None,
    }
    _clients: dict[str, redis.Redis | None] = {
        "default": None,
        "state": None,
        "presigned": None,
    }
    _metrics: CacheMetrics = CacheMetrics()

    def __init__(self, default_ttl: int | None = None, pool_type: str = "default"):
        """
        Initialize cache service.

        Args:
            default_ttl: Default TTL in seconds. If None, uses REDIS_DEFAULT_TTL
            pool_type: Which connection pool to use (default|state|presigned)
        """
        self.default_ttl = default_ttl or settings.redis_default_ttl
        self.pool_type = pool_type

    @classmethod
    async def get_client(cls, pool_type: str = "default") -> redis.Redis:
        """Get or create Redis client for specified pool type."""
        if cls._clients[pool_type] is None:
            pool_config = {
                "default": settings.redis_max_connections,
                "state": settings.redis_pool_size_state,
                "presigned": settings.redis_pool_size_presigned,
            }

            cls._pools[pool_type] = ConnectionPool.from_url(
                settings.redis_url,
                decode_responses=True,
                max_connections=pool_config[pool_type],
            )
            cls._clients[pool_type] = redis.Redis(connection_pool=cls._pools[pool_type])
            logger.info(
                "redis_pool_initialized",
                pool_type=pool_type,
                max_connections=pool_config[pool_type],
            )
        return cls._clients[pool_type]

    @classmethod
    async def close(cls) -> None:
        """Close all Redis connection pools."""
        for pool_type in cls._clients:
            if cls._clients[pool_type]:
                await cls._clients[pool_type].aclose()
                cls._clients[pool_type] = None
            if cls._pools[pool_type]:
                await cls._pools[pool_type].disconnect()
                cls._pools[pool_type] = None
        logger.info("all_redis_pools_closed")

    @classmethod
    def get_metrics(cls) -> dict[str, Any]:
        """Get current cache metrics."""
        return cls._metrics.to_dict()

    def _compress_if_needed(self, data: str) -> tuple[str, bool]:
        """
        Compress data if it exceeds threshold.

        Returns:
            tuple: (compressed/base64_encoded_data, is_compressed)
        """
        data_bytes = data.encode("utf-8")

        if len(data_bytes) > settings.redis_compression_threshold:
            compressed = gzip.compress(data_bytes)
            import base64

            encoded = base64.b64encode(compressed).decode("utf-8")
            CacheService._metrics.record_compression(len(data_bytes), len(compressed))
            return encoded, True

        return data, False

    def _decompress_if_needed(self, data: str, is_compressed: bool) -> str:
        """Decompress data if it was compressed."""
        if not is_compressed:
            return data

        try:
            import base64

            compressed = base64.b64decode(data.encode("utf-8"))
            decompressed = gzip.decompress(compressed)
            return decompressed.decode("utf-8")
        except Exception as e:
            logger.warning("cache_decompression_failed", error=str(e))
            return data

    async def get(self, key: str) -> str | None:
        """
        Get a value from cache.

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found
        """
        try:
            client = await self.get_client(self.pool_type)
            value = await client.get(key)

            if value:
                CacheService._metrics.record_hit()
                logger.debug("cache_hit", key=key)
            else:
                CacheService._metrics.record_miss()
                logger.debug("cache_miss", key=key)

            return value
        except Exception as e:
            logger.warning("cache_get_failed", key=key, error=str(e))
            return None

    async def set(
        self,
        key: str,
        value: str,
        ttl_seconds: int | None = None,
    ) -> bool:
        """
        Set a value in cache with optional compression.

        Args:
            key: Cache key
            value: Value to cache
            ttl_seconds: TTL in seconds. If None, uses default_ttl.

        Returns:
            True if successful, False otherwise
        """
        ttl = ttl_seconds if ttl_seconds is not None else self.default_ttl

        try:
            client = await self.get_client(self.pool_type)
            processed_value, is_compressed = self._compress_if_needed(value)

            await client.set(key, processed_value, ex=ttl)

            if is_compressed:
                await client.set(f"{key}:compressed", "1", ex=ttl)

            logger.debug("cache_set", key=key, ttl=ttl, compressed=is_compressed)
            return True
        except Exception as e:
            logger.warning("cache_set_failed", key=key, error=str(e))
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
            client = await self.get_client(self.pool_type)
            result = await client.delete(key, f"{key}:compressed")
            logger.debug("cache_delete", key=key, deleted=bool(result))
            return bool(result)
        except Exception as e:
            logger.warning("cache_delete_failed", key=key, error=str(e))
            return False

    async def delete_pattern(self, pattern: str) -> int:
        """
        Delete all keys matching a pattern.

        Args:
            pattern: Glob-style pattern (e.g., "user:*")

        Returns:
            Number of keys deleted
        """
        try:
            client = await self.get_client(self.pool_type)
            keys = []
            async for key in client.scan_iter(match=pattern):
                keys.append(key)

            if keys:
                deleted = await client.delete(*keys)
                logger.info(
                    "cache_cleared_by_pattern", pattern=pattern, deleted=deleted
                )
                return deleted
            return 0
        except Exception as e:
            logger.warning("cache_clear_pattern_failed", pattern=pattern, error=str(e))
            return 0

    async def exists(self, key: str) -> bool:
        """
        Check if a key exists in cache.

        Args:
            key: Cache key

        Returns:
            True if key exists, False otherwise
        """
        try:
            client = await self.get_client(self.pool_type)
            result = await client.exists(key)
            return bool(result)
        except Exception as e:
            logger.warning("cache_exists_check_failed", key=key, error=str(e))
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
            is_compressed = await self.exists(f"{key}:compressed")
            decompressed = self._decompress_if_needed(value, is_compressed)

            try:
                return json.loads(decompressed)
            except json.JSONDecodeError as e:
                logger.warning("cache_json_decode_failed", key=key, error=str(e))
                return None
        return None

    async def set_json(
        self,
        key: str,
        value: dict[str, Any] | list,
        ttl_seconds: int | None = None,
    ) -> bool:
        """
        Set a JSON value in cache with compression.

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
            logger.warning("cache_json_encode_failed", key=key, error=str(e))
            return False

    async def ttl(self, key: str) -> int:
        """Get remaining TTL in seconds for a key."""
        try:
            client = await self.get_client(self.pool_type)
            return await client.ttl(key) or 0
        except Exception as e:
            logger.warning("cache_ttl_check_failed", key=key, error=str(e))
            return 0

    async def renew_lock(
        self,
        lock_key: str,
        lock_timeout: int = 30,
        renew_interval: int = 10,
    ) -> None:
        """
        Periodically renew a distributed lock.

        Args:
            lock_key: The lock key to renew
            lock_timeout: Lock expiration time in seconds
            renew_interval: Interval between renewals in seconds
        """
        try:
            client = await self.get_client(self.pool_type)
            while True:
                await asyncio.sleep(renew_interval)
                await client.pexpire(lock_key, lock_timeout * 1000)
                logger.debug("lock_renewed", lock_key=lock_key)
        except asyncio.CancelledError:
            logger.debug("lock_renewal_cancelled", lock_key=lock_key)
        except Exception as e:
            logger.warning("lock_renewal_failed", lock_key=lock_key, error=str(e))

    async def get_or_set(
        self,
        key: str,
        factory: Callable[[], Awaitable[Any]],
        ttl_seconds: int | None = None,
        lock_timeout: int = 30,
    ) -> Any:
        """
        Get value from cache or compute and cache it.

        Uses a distributed lock (Redis SETNX) to prevent cache stampede/race conditions.
        Lock is renewed in background for long-running operations.

        Args:
            key: Cache key
            factory: Async callable to compute value if not cached
            ttl_seconds: TTL in seconds. If None, uses default_ttl.
            lock_timeout: Lock expiration time in seconds

        Returns:
            Cached or computed value
        """
        value = await self.get_json(key)
        if value is not None:
            return value

        lock_key = f"{key}:lock"
        client = await self.get_client(self.pool_type)

        if await client.set(lock_key, "1", nx=True, ex=lock_timeout):
            renew_task = None
            try:
                value = await self.get_json(key)
                if value is not None:
                    return value

                computed = await factory()
                await self.set_json(key, computed, ttl_seconds)
                return computed
            finally:
                if renew_task:
                    renew_task.cancel()
                    try:
                        await renew_task
                    except asyncio.CancelledError:
                        pass
                await client.delete(lock_key)
        else:
            await asyncio.sleep(0.1)
            return await self.get_or_set(key, factory, ttl_seconds, lock_timeout)

    async def get_presigned_url(
        self, object_key: str, expires_seconds: int
    ) -> str | None:
        """
        Get or generate a cached presigned URL.

        Args:
            object_key: MinIO object key
            expires_seconds: URL expiration time in seconds

        Returns:
            Cached or newly generated presigned URL
        """
        cache_key = f"presigned:url:{object_key}:{expires_seconds}"
        cached_url = await self.get(cache_key)

        if cached_url:
            logger.debug("presigned_url_cache_hit", object_key=object_key)
            return cached_url

        return None

    async def set_presigned_url(
        self, object_key: str, expires_seconds: int, url: str
    ) -> bool:
        """
        Cache a presigned URL for partial expiration time.

        Args:
            object_key: MinIO object key
            expires_seconds: Original URL expiration time
            url: Presigned URL to cache
        """
        cache_key = f"presigned:url:{object_key}:{expires_seconds}"
        cache_ttl = int(expires_seconds * settings.presigned_url_cache_ttl_pct)

        return await self.set(cache_key, url, ttl_seconds=cache_ttl)

    async def get_many(self, keys: list[str]) -> list[str | None]:
        """
        Get multiple values from cache (MGET).

        Args:
            keys: List of cache keys

        Returns:
            List of values (None for missing keys)
        """
        if not keys:
            return []

        try:
            client = await self.get_client(self.pool_type)

            compressed_flags = await client.mget(f"{k}:compressed" for k in keys)
            raw_values = await client.mget(keys)

            result = []
            for i, val in enumerate(raw_values):
                if val is None:
                    CacheService._metrics.record_miss()
                    result.append(None)
                else:
                    CacheService._metrics.record_hit()
                    is_compressed = bool(compressed_flags[i])
                    result.append(self._decompress_if_needed(val, is_compressed))

            return result
        except Exception as e:
            logger.warning("cache_get_many_failed", error=str(e))
            return [None] * len(keys)

    async def set_many(
        self, mapping: dict[str, str], ttl_seconds: int | None = None
    ) -> int:
        """
        Set multiple values in cache (MSET).

        Args:
            mapping: Dictionary of key-value pairs
            ttl_seconds: TTL in seconds

        Returns:
            Number of keys set
        """
        if not mapping:
            return 0

        ttl = ttl_seconds if ttl_seconds is not None else self.default_ttl

        try:
            client = await self.get_client(self.pool_type)
            pipe = client.pipeline()

            for key, value in mapping.items():
                processed_value, is_compressed = self._compress_if_needed(value)
                pipe.set(key, processed_value, ex=ttl)
                if is_compressed:
                    pipe.set(f"{key}:compressed", "1", ex=ttl)

            results = await pipe.execute()
            logger.info("cache_set_many", keys=len(mapping), success=sum(results))
            return sum(results)
        except Exception as e:
            logger.warning("cache_set_many_failed", error=str(e))
            return 0


# Default cache instance
cache = CacheService()
cache_state = CacheService(pool_type="state")
cache_presigned = CacheService(pool_type="presigned")
