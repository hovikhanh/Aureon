"""Alembic environment — one chain, multi-schema (CLAUDE.md §5.7).

URL comes from ConfigService only. `version_table_schema="platform"`; the `platform` schema
is ensured before Alembic writes its version table. Schemas outside the 10 module schemas
(e.g. v1 leftovers in `public`) are ignored by autogenerate/check (05 §12.2).
"""

from logging.config import fileConfig
from typing import Any

from alembic import context
from sqlalchemy import Connection, create_engine, pool, text

from app.core.config import get_config
from app.model_registry import SCHEMAS, metadata

config = context.config

if config.config_file_name is not None and config.attributes.get("configure_logger", True):
    fileConfig(config.config_file_name, disable_existing_loggers=False)

target_metadata = metadata
VERSION_SCHEMA = "platform"


def _database_url() -> str:
    return get_config().database_url.get_secret_value()


def include_name(name: str | None, type_: str, parent_names: dict[str, Any]) -> bool:
    if type_ == "schema":
        return name in SCHEMAS
    return True


def _configure(**kwargs: Any) -> None:
    context.configure(
        target_metadata=target_metadata,
        include_schemas=True,
        include_name=include_name,
        version_table_schema=VERSION_SCHEMA,
        compare_type=True,
        compare_server_default=True,
        **kwargs,
    )


def run_migrations_offline() -> None:
    _configure(url=_database_url(), literal_binds=True, dialect_opts={"paramstyle": "named"})
    with context.begin_transaction():
        context.run_migrations()


def _run_with_connection(connection: Connection) -> None:
    connection.execute(text(f"CREATE SCHEMA IF NOT EXISTS {VERSION_SCHEMA}"))
    connection.commit()
    _configure(connection=connection)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    injected = config.attributes.get("connection")
    if isinstance(injected, Connection):
        _run_with_connection(injected)
        return
    connectable = create_engine(_database_url(), poolclass=pool.NullPool)
    try:
        with connectable.connect() as connection:
            _run_with_connection(connection)
    finally:
        connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
