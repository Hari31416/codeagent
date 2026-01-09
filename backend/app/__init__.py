"""
CodingAgent Backend Application

Main FastAPI application with all routes and middleware.
"""

from contextlib import asynccontextmanager

# Import routers
from app.api.routes import artifacts, models, projects, query, sessions, upload
from app.config import settings
from app.core.cache import CacheService
from app.db.init_db import init_database
from app.db.pool import DatabasePool
from app.shared.logging import get_logger
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.

    Handles startup and shutdown tasks.
    """
    # Startup
    logger.info("Starting CodingAgent backend", version=settings.app_version)

    # Initialize database pool
    await DatabasePool.get_pool()
    logger.info("Database pool initialized")

    # Initialize database tables
    await init_database()
    logger.info("Database tables initialized")

    # Initialize cache
    await CacheService.get_client()
    logger.info("Redis cache initialized")

    yield

    # Shutdown
    logger.info("Shutting down CodingAgent backend")

    # Close database pool
    await DatabasePool.close()

    # Close cache
    await CacheService.close()


# Create FastAPI application
app = FastAPI(
    title="CodingAgent API",
    version=settings.app_version,
    description="AI Coding & Data Analysis Agent Backend",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=settings.cors_allow_credentials,
    allow_methods=settings.cors_allow_methods,
    allow_headers=settings.cors_allow_headers,
)

# Include routers
app.include_router(projects.router)
app.include_router(sessions.router)
app.include_router(artifacts.router)
app.include_router(upload.router)
app.include_router(query.router)
app.include_router(models.router)


@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "status": "ok",
        "service": "CodingAgent API",
        "version": settings.app_version,
    }


@app.get("/health")
async def health():
    """Detailed health check."""
    return {
        "status": "healthy",
        "version": settings.app_version,
        "environment": settings.environment,
    }
