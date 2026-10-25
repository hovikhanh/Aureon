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


def _active_schemas() -> tuple[str, ...]:
    """`alembic revision --autogenerate -x schemas=finance,sales` scopes a revision to those
    schemas (module-by-module baselines). Default: all 10 module schemas."""
    raw = context.get_x_argument(as_dictionary=True).get("schemas")
    if not raw:
        return SCHEMAS
    picked = tuple(s.strip() for s in raw.split(",") if s.strip())
    unknown = set(picked) - set(SCHEMAS)
    if unknown:
        raise ValueError(f"unknown schemas: {sorted(unknown)}")
    return picked


# Migration bookkeeping tables that live in a module schema but have no model (05 §12.2):
# `execution._m13_assignee_backfill` keeps the 0014 assignee mapping for its downgrade.
MIGRATION_ONLY_TABLES = frozenset({("execution", "_m13_assignee_backfill")})


def include_name(name: str | None, type_: str, parent_names: dict[str, Any]) -> bool:
    """Reflection side: only module schemas (v1 leftovers in `public` are ignored), minus the
    migration-only bookkeeping tables (autogenerate must not propose dropping them)."""
    if type_ == "schema":
        return name in _active_schemas()
    if type_ == "table":
        return (parent_names.get("schema_name"), name) not in MIGRATION_ONLY_TABLES
    return True


def include_object(
    obj: Any, name: str | None, type_: str, reflected: bool, compare_to: Any
) -> bool:
    """Metadata side: keep only tables (and their children) in the active schemas."""
    table = obj if type_ == "table" else getattr(obj, "table", None)
    schema = getattr(table, "schema", None)
    if (schema, getattr(table, "name", None)) in MIGRATION_ONLY_TABLES:
        return False
    return schema is None or schema in _active_schemas()


def _configure(**kwargs: Any) -> None:
    context.configure(
        target_metadata=target_metadata,
        include_schemas=True,
        include_name=include_name,
        include_object=include_object,
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
