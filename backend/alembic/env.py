"""Alembic migration environment configuration for H.I.R.E.

Configures Alembic to:
- Use H.I.R.E.'s Base.metadata including all registered models (User, Profile, Resume)
- Connect using `settings.DATABASE_URL` with fallback to alembic.ini
- Support both programmatic test runs via connection injection and standard CLI migrations
"""

from __future__ import annotations

import os
import sys
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool

from alembic import context

# Ensure the backend directory is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Ensure SECRET_KEY is set for migration commands if not already exported
os.environ.setdefault(
    "SECRET_KEY", "hire_temporary_migration_secret_key_minimum_32_characters_long"
)

# Import Base and models so Alembic's target_metadata is fully populated
import app.models  # Ensures User, Profile, Resume are registered with Base.metadata
from app.core.config import settings
from app.database.base import Base

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# target_metadata for autogenerate and migrations
target_metadata = Base.metadata


def get_database_url() -> str:
    """Return configured DATABASE_URL from settings, or fallback to alembic.ini."""
    if settings.DATABASE_URL:
        return settings.DATABASE_URL
    return config.get_main_option(
        "sqlalchemy.url", "postgresql://username:password@localhost:5432/hire_db"
    )


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    Configures the context with just a URL and emits SQL statements to stdout or script output.
    """
    url = get_database_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    Creates an Engine and associates a connection with the context, or reuses
    a connection supplied via config.attributes (e.g. In pytest).
    """
    # 1. Check if a connection was provided programmatically (e.g., in test suites)
    connection = config.attributes.get("connection", None)
    if connection is not None:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )
        with context.begin_transaction():
            context.run_migrations()
        return

    # 2. Standard CLI / production migration flow
    configuration = config.get_section(config.config_ini_section, {})
    url = get_database_url()
    configuration["sqlalchemy.url"] = url

    connect_args = {}
    if url.startswith("sqlite"):
        connect_args["check_same_thread"] = False

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
        connect_args=connect_args,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
