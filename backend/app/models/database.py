"""Async SQLAlchemy 2.0 engine, session factory, and declarative base."""

from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.config import get_settings


class Base(DeclarativeBase):
    """Canonical SQLAlchemy 2.0 declarative base for all 9 database tables."""


_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def get_async_engine() -> AsyncEngine:
    """Return or lazily initialize the singleton SQLAlchemy AsyncEngine."""
    global _engine
    if _engine is None:
        settings = get_settings()
        _engine = create_async_engine(
            settings.DATABASE_URL,
            pool_pre_ping=True,
            pool_size=5,
            max_overflow=5,
            connect_args={"command_timeout": settings.TOOL_TIMEOUT_SECONDS},
        )
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """Return or lazily initialize the async_sessionmaker bound to the engine."""
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(
            bind=get_async_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
        )
    return _session_factory


async def get_db_session() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency yielding a scoped AsyncSession per request."""
    factory = get_session_factory()
    async with factory() as session:
        yield session


async def dispose_async_engine() -> None:
    """Dispose the global AsyncEngine pool during application shutdown."""
    global _engine, _session_factory
    if _engine is not None:
        await _engine.dispose()
        _engine = None
        _session_factory = None

