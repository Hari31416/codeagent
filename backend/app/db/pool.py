"""
Database connection pool for PostgreSQL using asyncpg.

Provides connection management with async context managers.
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

import asyncpg
from app.config import settings
from app.shared.logging import get_logger
from asyncpg import Connection, Pool

logger = get_logger(__name__)


class DatabasePool:
    """Manages PostgreSQL connection pool."""

    _pool: Pool | None = None

    @classmethod
    async def get_pool(cls) -> Pool:
        """Get or create the connection pool."""
        if cls._pool is None:
            cls._pool = await asyncpg.create_pool(
                host=settings.postgres_host,
                port=settings.postgres_port,
                user=settings.postgres_user,
                password=settings.postgres_password,
                database=settings.postgres_db,
                min_size=settings.db_pool_min_size,
                max_size=settings.db_pool_max_size,
                command_timeout=settings.db_command_timeout,
            )
            logger.info(
                "database_pool_created",
                min_size=settings.db_pool_min_size,
                max_size=settings.db_pool_max_size,
            )
        return cls._pool

    @classmethod
    async def close(cls) -> None:
        """Close the connection pool."""
        if cls._pool:
            await cls._pool.close()
            cls._pool = None
            logger.info("database_pool_closed")


@asynccontextmanager
async def get_system_db() -> AsyncGenerator[Connection, None]:
    """
    Get a database connection from the pool.

    Usage:
        async with get_system_db() as conn:
            result = await conn.fetch("SELECT * FROM sessions")
    """
    pool = await DatabasePool.get_pool()
    async with pool.acquire() as conn:
        yield conn
