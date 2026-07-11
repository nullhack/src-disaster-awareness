"""Alembic environment.

Wires Alembic's autogenerate and online/offline runners to the operational
schema's ``MetaData`` declared in ``disaster_report.store.base``. The
database URL is resolved from (in order) the ``sqlalchemy.url`` ini key, the
``DATABASE_URL`` environment variable, or an in-memory SQLite fallback so the
Alembic CLI is usable without secrets on disk.
"""

from __future__ import annotations

import os
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool

from alembic import context
from disaster_report.store.base import _metadata as target_metadata

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

_configured_url = config.get_main_option("sqlalchemy.url")
_env_url = os.environ.get("DATABASE_URL")
if _env_url:
    config.set_main_option("sqlalchemy.url", _env_url)
elif not _configured_url or _configured_url.startswith("driver://"):
    config.set_main_option("sqlalchemy.url", "sqlite:///:memory:")


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=url.startswith("sqlite"),
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    url = config.get_main_option("sqlalchemy.url")
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=url.startswith("sqlite"),
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
