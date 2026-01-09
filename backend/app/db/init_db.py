"""
Database initialization script.

Creates all required tables for the application.
Run this script manually or as part of deployment.
"""

import asyncio
import sys

from app.db.models import ARTIFACTS_TABLE_SQL, MESSAGES_TABLE_SQL, SESSIONS_TABLE_SQL
from app.db.pool import get_system_db
from app.shared.logging import get_logger

logger = get_logger(__name__)


async def init_database():
    """
    Initialize the database by creating all required tables.
    """
    try:
        logger.info("Starting database initialization")

        async with get_system_db() as conn:
            # Create sessions table
            logger.info("Creating sessions table")
            await conn.execute(SESSIONS_TABLE_SQL)

            # Create messages table (must come before artifacts due to FK)
            logger.info("Creating messages table")
            await conn.execute(MESSAGES_TABLE_SQL)

            # Create artifacts table
            logger.info("Creating artifacts table")
            await conn.execute(ARTIFACTS_TABLE_SQL)

        logger.info("Database initialization completed successfully")
        return True

    except Exception as e:
        logger.error("Database initialization failed", error=str(e), exc_info=True)
        return False


async def main():
    """Main entry point for the script."""
    success = await init_database()

    if success:
        logger.info("Database is ready")
        sys.exit(0)
    else:
        logger.error("Database initialization failed")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
