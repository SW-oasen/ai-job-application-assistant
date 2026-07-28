from functools import lru_cache

from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine

from app.core.config import get_settings


@lru_cache
def get_engine() -> AsyncEngine | None:
    database_url = get_settings().database_url
    if not database_url:
        return None
    return create_async_engine(database_url, pool_pre_ping=True)


@lru_cache
def get_session_factory() -> async_sessionmaker | None:
    engine = get_engine()
    if engine is None:
        return None
    return async_sessionmaker(engine, expire_on_commit=False)

