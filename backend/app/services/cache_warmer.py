"""
Cache Warmer Service

Background task to warm cache with frequently accessed data.
"""

import asyncio
from uuid import UUID

from app.core.cache import CacheService, cache
from app.shared.logging import get_logger

logger = get_logger(__name__)


class CacheWarmer:
    """
    Background cache warming service.

    Warms frequently accessed data in the background after application startup.
    """

    def __init__(self):
        self._warming_task: asyncio.Task | None = None
        self._stop_event = asyncio.Event()

    async def start_warming(self) -> None:
        """Start background cache warming."""
        if self._warming_task and not self._warming_task.done():
            logger.warning("cache_warmer_already_running")
            return

        self._warming_task = asyncio.create_task(self._warm_cache_loop())
        logger.info("cache_warmer_started")

    async def stop_warming(self) -> None:
        """Stop background cache warming."""
        self._stop_event.set()
        if self._warming_task:
            self._warming_task.cancel()
            try:
                await self._warming_task
            except asyncio.CancelledError:
                pass
        logger.info("cache_warmer_stopped")

    async def _warm_cache_loop(self) -> None:
        """Main cache warming loop."""
        logger.info("cache_warming_initial")

        try:
            await self._warm_initial_data()

            refresh_interval = 300

            while not self._stop_event.is_set():
                try:
                    # Wait for the refresh interval before checking cache
                    await asyncio.wait_for(
                        self._stop_event.wait(),
                        timeout=refresh_interval,
                    )
                    # If we get here, stop_event was set
                    break
                except asyncio.TimeoutError:
                    # Timeout means we should refresh
                    await self._refresh_stale_cache()
        except asyncio.CancelledError:
            logger.info("cache_warming_cancelled")
        except Exception as e:
            logger.error("cache_warming_error", error=str(e), exc_info=True)

    async def _warm_initial_data(self) -> None:
        """Warm initial frequently accessed data."""
        try:
            test_keys = [
                ("test_key_1", {"data": "test1"}),
                ("test_key_2", {"data": "test2"}),
                ("test_key_3", {"data": "test3"}),
            ]

            for key, value in test_keys:
                await cache.set_json(key, value, ttl_seconds=600)

            logger.info(
                "initial_cache_warming_complete",
                keys_warmed=len(test_keys),
            )
        except Exception as e:
            logger.warning("initial_cache_warming_failed", error=str(e))

    async def _refresh_stale_cache(self) -> None:
        """Refresh stale cache entries based on hit rate."""
        try:
            metrics = CacheService.get_metrics()
            hit_rate = metrics.get("hit_rate", 0)

            if hit_rate < 0.5:
                logger.info("refreshing_cache_low_hit_rate", hit_rate=hit_rate)
                await self._warm_initial_data()
        except Exception as e:
            logger.warning("cache_refresh_failed", error=str(e))


_cache_warmer: CacheWarmer | None = None


def get_cache_warmer() -> CacheWarmer:
    """Get singleton CacheWarmer instance."""
    global _cache_warmer
    if _cache_warmer is None:
        _cache_warmer = CacheWarmer()
    return _cache_warmer


async def start_background_warming() -> None:
    """Start background cache warming."""
    warmer = get_cache_warmer()
    await warmer.start_warming()


async def stop_background_warming() -> None:
    """Stop background cache warming."""
    warmer = get_cache_warmer()
    await warmer.stop_warming()
