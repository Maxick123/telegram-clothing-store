from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncAttrs, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import NullPool

from app.core.config import get_settings


class Base(AsyncAttrs, DeclarativeBase):
    pass


settings = get_settings()
engine_options = {"pool_pre_ping": True}
if settings.app_env == "test":
    engine_options["poolclass"] = NullPool
engine = create_async_engine(settings.database_url, **engine_options)
SessionFactory = async_sessionmaker(engine, expire_on_commit=False)


async def get_session() -> AsyncIterator[AsyncSession]:
    async with SessionFactory() as session:
        yield session
