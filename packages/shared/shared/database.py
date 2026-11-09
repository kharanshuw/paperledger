"""Asynchronous database engine, session factory, and base declarative class.

Utilizes SQLAlchemy 2.0 AsyncEngine backed by asyncpg for high-throughput I/O.
"""

import os
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

from sqlalchemy.ext.asyncio import (
    AsyncAttrs,
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

DEFAULT_DATABASE_URL = (
    "postgresql+asyncpg://postgres:postgres@localhost:5432/expense_tracker"
)


def get_database_url() -> str:
    """Retrieve and normalize database URL for asyncpg."""
    url = os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL)
    # Ensure async driver scheme
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
    elif url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql+asyncpg://", 1)
    return url 


class Base(AsyncAttrs, DeclarativeBase):
    """Base declarative class for all SQLAlchemy 2.0 models."""

    pass 


# Global engine cache
_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def get_engine() -> AsyncEngine:
    """Get or create singleton AsyncEngine with connection pool tuning."""
    global _engine
    if _engine is None:
        _engine = create_async_engine(
            get_database_url(),
            echo=os.getenv("SQL_ECHO", "false").lower() in ("true", "1"),
            pool_size=10,
            max_overflow=5,
            pool_pre_ping=True,
            pool_recycle=300,
        )
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """Get or create singleton async session factory."""
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(
            bind=get_engine(),
            expire_on_commit=False,
            class_=AsyncSession,
        )
    return _session_factory


@asynccontextmanager
async def get_db_session() -> AsyncGenerator[AsyncSession, Any]:
    """Context manager yielding an isolated async database session with automatic rollback."""
    factory = get_session_factory()
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
