"""FastAPI application factory, lifespan context, and middleware for PaperLedger."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
import logging
from typing import Any

from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from redis.asyncio import from_url as redis_from_url
from sqlalchemy import text

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.errors import setup_exception_handlers
from shared.database import get_engine

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("paperledger.core-api")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, Any]:
    """Manage lifecycle resources: verify DB/Redis at startup, dispose at shutdown."""
    settings = get_settings()
    logger.info("Starting up %s (env: %s)...", settings.PROJECT_NAME, settings.ENVIRONMENT)

    # 1. Ensure statement upload storage directories exist
    settings.init_storage_dirs()

    # 2. Warm up & test PostgreSQL connection
    engine = get_engine()
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        logger.info("✔ PostgreSQL connection verified successfully")
    except Exception as exc:
        logger.error("❌ Failed to connect to PostgreSQL during startup: %s", exc)
        raise

    # 3. Test Redis connection
    try:
        r = redis_from_url(settings.REDIS_URL)
        await r.ping()
        await r.aclose()
        logger.info("✔ Redis connection verified successfully")
    except Exception as exc:
        logger.error("❌ Failed to connect to Redis during startup: %s", exc)
        raise

    yield

    # Shutdown: Cleanly dispose connection pool
    logger.info("Shutting down %s, disposing database connection pool...", settings.PROJECT_NAME)
    await engine.dispose()
    logger.info("✔ Database pool disposed cleanly")


def create_app() -> FastAPI:
    """FastAPI application factory."""
    settings = get_settings()

    app = FastAPI(
        title=settings.PROJECT_NAME,
        version="0.1.0",
        description="Self-hosted, audit-grade personal expense engine with automated PDF bank statement ingestion.",
        lifespan=lifespan,
    )

    # CORS Middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Setup standardized RFC 7807 error responses
    setup_exception_handlers(app)

    # Health check endpoint
    @app.get("/health", tags=["Health"], status_code=status.HTTP_200_OK)
    async def health_check() -> dict[str, Any]:
        """System health and readiness probe."""
        db_status = "connected"
        redis_status = "connected"

        # Check DB
        try:
            async with get_engine().connect() as conn:
                await conn.execute(text("SELECT 1"))
        except Exception:
            db_status = "unhealthy"

        # Check Redis
        try:
            r = redis_from_url(settings.REDIS_URL)
            await r.ping()
            await r.aclose()
        except Exception:
            redis_status = "unhealthy"

        overall_ok = db_status == "connected" and redis_status == "connected"
        return {
            "status": "healthy" if overall_ok else "degraded",
            "version": "0.1.0",
            "database": db_status,
            "redis": redis_status,
        }

    # Mount central API v1 routes
    app.include_router(api_router, prefix=settings.API_V1_PREFIX)

    return app


app = create_app()
