import os
from typing import AsyncGenerator
from sqlalchemy.orm import declarative_base

# Base MUST be defined before any engine/session machinery so models can
# import it without triggering a driver dependency at module-load time.
Base = declarative_base()

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://user:pass@db/ttc")

# Engine and session factory are created lazily on first use so that
# ``from app.database import Base`` works even when asyncpg isn't installed
# (e.g. during local linting / testing without a full venv).
_engine = None
_async_session_factory = None


def _get_engine():
    global _engine
    if _engine is None:
        from sqlalchemy.ext.asyncio import create_async_engine
        _engine = create_async_engine(DATABASE_URL, echo=False)
    return _engine


def _get_session_factory():
    global _async_session_factory
    if _async_session_factory is None:
        from sqlalchemy.ext.asyncio import AsyncSession
        from sqlalchemy.orm import sessionmaker
        _async_session_factory = sessionmaker(
            _get_engine(), class_=AsyncSession, expire_on_commit=False
        )
    return _async_session_factory


async def get_async_session() -> AsyncGenerator:
    """FastAPI dependency that yields an async database session."""
    factory = _get_session_factory()
    async with factory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
