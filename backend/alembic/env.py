import sys
from logging.config import fileConfig
from pathlib import Path

from sqlalchemy import pool
from sqlalchemy import create_engine

from alembic import context

# Make backend/ importable (so `app.*` resolves) regardless of CWD.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import Config
from app.db.base import Base
import app.models  # noqa: F401 — register models on Base.metadata

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Single source of truth: repo-root .env via Config (never hardcode here).
# NOTE: ConfigParser interpolation requires literal % to be escaped as %%.
config.set_main_option("sqlalchemy.url", Config.DATABASE_URL.replace("%", "%%"))

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=Config.DATABASE_URL,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = create_engine(Config.DATABASE_URL, poolclass=pool.NullPool)
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
