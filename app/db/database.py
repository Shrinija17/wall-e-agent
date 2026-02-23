from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db.models import Base

_engine = None
_session_factory = None


def _get_engine():
    global _engine
    if _engine is None:
        from app.config import settings
        _engine = create_async_engine(settings.async_database_url, echo=False)
    return _engine


def _get_session_factory() -> async_sessionmaker[AsyncSession]:
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(
            _get_engine(), class_=AsyncSession, expire_on_commit=False
        )
    return _session_factory


def async_session() -> AsyncSession:
    """Return a new async session. Use as: async with async_session() as session:"""
    return _get_session_factory()()


async def init_db() -> None:
    engine = _get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
