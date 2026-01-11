"""
Database initialization script.

Creates all required tables for the application.
Run this script manually or as part of deployment.
"""

import asyncio
import sys
from datetime import datetime, timezone

from app.config import settings
from app.db.models import (
    ARTIFACTS_TABLE_SQL,
    MESSAGES_TABLE_SQL,
    PROJECTS_TABLE_SQL,
    SESSIONS_TABLE_SQL,
    USERS_TABLE_SQL,
)
from app.db.pool import get_system_db
from app.shared.logging import get_logger

logger = get_logger(__name__)


async def create_admin_user(conn) -> None:
    """
    Create the admin user if it doesn't exist.

    Uses credentials from settings (env vars).
    """
    from app.core.auth import get_password_hash

    # Check if admin user already exists
    existing = await conn.fetchrow(
        "SELECT user_id FROM users WHERE email = $1",
        settings.admin_email,
    )

    if existing:
        logger.info("Admin user already exists", email=settings.admin_email)
        return

    # Create admin user
    password_hash = get_password_hash(settings.admin_password)
    now = datetime.now(timezone.utc)

    await conn.execute(
        """
        INSERT INTO users (email, password_hash, full_name, role, is_active, created_at, updated_at)
        VALUES ($1, $2, $3, 'admin', TRUE, $4, $4)
        """,
        settings.admin_email,
        password_hash,
        settings.admin_full_name,
        now,
    )

    logger.info("Admin user created", email=settings.admin_email)


async def init_database():
    """
    Initialize the database by creating all required tables.
    """
    try:
        logger.info("Starting database initialization")

        async with get_system_db() as conn:
            # Create users table
            logger.info("Creating users table")
            await conn.execute(USERS_TABLE_SQL)

            # Create projects table (must come before sessions due to FK)
            logger.info("Creating projects table")
            await conn.execute(PROJECTS_TABLE_SQL)

            # Create sessions table
            logger.info("Creating sessions table")
            await conn.execute(SESSIONS_TABLE_SQL)

            # Create messages table (must come before artifacts due to FK)
            logger.info("Creating messages table")
            await conn.execute(MESSAGES_TABLE_SQL)

            # Create artifacts table
            logger.info("Creating artifacts table")
            await conn.execute(ARTIFACTS_TABLE_SQL)

            # Create admin user
            logger.info("Creating admin user if not exists")
            await create_admin_user(conn)

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
