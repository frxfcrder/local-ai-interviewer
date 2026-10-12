from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Config

from .base import Base

__all__ = ["Base", "engine", "SessionLocal", "get_db"]

# Sync psycopg3 engine. (An async engine was tried first, but Uvicorn forces
# the Proactor event loop on Windows after app import, and psycopg async
# cannot run on Proactor — so every DB call failed at runtime. Sync is
# correct for a local-first service with millisecond queries.)
engine = create_engine(Config.DATABASE_URL, echo=Config.DEBUG, future=True)

SessionLocal = sessionmaker(bind=engine, class_=Session, expire_on_commit=False)


def get_db() -> Generator[Session, None, None]:
    with SessionLocal() as session:
        yield session
