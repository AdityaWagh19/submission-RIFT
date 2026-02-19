"""
Database engine and session management for the Creator Sticker Platform.

Uses SQLAlchemy async engine with aiosqlite for non-blocking DB operations
inside FastAPI. Tables are auto-created on server startup via init_db().
"""
import logging
import os

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

from config import settings

logger = logging.getLogger(__name__)


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""
    pass


# ── Engine ──────────────────────────────────────────────────────────

# Convert sqlite:///... → sqlite+aiosqlite:///... for async driver
_raw_url = settings.database_url
if _raw_url.startswith("sqlite:///"):
    _async_url = _raw_url.replace("sqlite:///", "sqlite+aiosqlite:///", 1)
else:
    _async_url = _raw_url

engine = create_async_engine(
    _async_url,
    echo=(settings.environment == "development"),
    future=True,
)

async_session = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)


# ── Helpers ─────────────────────────────────────────────────────────

async def init_db() -> None:
    """Create all tables. Called once on server startup."""
    # Import models so Base.metadata knows about them
    import db_models  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    logger.info("Database tables created (or already exist)")


async def get_db() -> AsyncSession:
    """FastAPI dependency — yields an async session."""
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()
