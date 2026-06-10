"""
Alembic environment configuration.

Key decisions:
- Uses async engine to match the application's SQLAlchemy setup.
- Imports all ORM models so Alembic can detect schema changes via autogenerate.
- target_metadata points to our shared Base — all tables registered against it
  will be included in migrations.
"""

import asyncio
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

# Import Base and all models so Alembic can see every table.
# noqa: F401 suppresses "imported but unused" warnings — these imports are
# side-effect imports that register the models against Base.metadata.
from app.database import Base
from app.wallet.models import Wallet  # noqa: F401
from app.transfer.models import Transfer  # noqa: F401
from app.ledger.models import LedgerEntry  # noqa: F401
from app.outbox.models import OutboxEvent  # noqa: F401
from app.processed_events.models import ProcessedEvent  # noqa: F401

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# All tables registered against Base will be picked up by autogenerate
target_metadata = Base.metadata


def get_url() -> str:
    """
    Read the database URL from application settings.
    Overrides whatever is set in alembic.ini so we have a single
    source of truth for config.
    """
    from app.config import get_settings
    return get_settings().database_url


def run_migrations_offline() -> None:
    """
    Run migrations without a live DB connection.
    Useful for generating SQL scripts to review before applying.
    """
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """
    Called by run_async_migrations inside run_sync().
    Alembic's context.configure and run_migrations must run
    in a synchronous context even when using an async engine.
    """
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """
    Creates an async engine and runs migrations inside run_sync().
    NullPool is used here because Alembic migrations are one-shot —
    we don't want pooled connections lingering after the migration run.
    """
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = get_url()

    connectable = async_engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Entry point for online migrations — called by Alembic at runtime."""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
