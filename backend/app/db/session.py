import asyncio
import sys
import warnings
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import Config

from .base import Base

__all__ = ["Base", "engine", "AsyncSessionLocal", "get_db"]

# psycopg async requires a selector loop on Windows (default Proactor is
# incompatible). Deprecated in 3.14, removal slated 3.16 — revisit then
# (likely switch to sync engine or run Postgres access in threads).
if sys.platform == "win32":
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        try:
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        except AttributeError:
            pass

# Single source of truth: repo-root .env via Config (psycopg3 scheme works
# with create_async_engine). No hardcoded secrets here.
engine = create_async_engine(Config.DATABASE_URL, echo=Config.DEBUG, future=True)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session
