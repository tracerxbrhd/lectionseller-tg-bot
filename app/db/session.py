from __future__ import annotations

from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from app.config.settings import Settings, get_settings


def create_engine(settings: Settings | None = None) -> AsyncEngine:
    actual_settings = settings or get_settings()
    return create_async_engine(
        actual_settings.database_url,
        echo=actual_settings.database_echo,
        pool_pre_ping=True,
    )


engine = create_engine()
async_session_factory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_session() -> AsyncIterator[AsyncSession]:
    async with async_session_factory() as session:
        yield session
