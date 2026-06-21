"""Async database session management.

Provides:
  - Async SQLAlchemy engine with connection pooling
  - Per-request session dependency (FastAPI Depends)
  - Automatic commit/rollback lifecycle

Connection pool configuration:
  - pool_size: 20 (persistent connections)
  - max_overflow: 10 (burst capacity)
  - pool_timeout: 30s (wait for available connection)
  - pool_recycle: 3600s (recycle connections after 1 hour)
"""

from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from patchbay_gateway.core.config import get_settings

settings = get_settings()

engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
    pool_size=20,
    max_overflow=10,
    pool_timeout=30,
    pool_recycle=3600,
    pool_pre_ping=True,
)

async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that provides an async database session.

    Lifecycle:
      1. Create session
      2. Yield to endpoint
      3. On success: commit
      4. On exception: rollback
      5. Always: close session
    """
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
