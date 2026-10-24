"""TC-SYS-002 / TC-SYS-009 — Alembic baseline against the compose Postgres.

Read-only against a DB already at `alembic upgrade head` (the round-trip itself is a CLI step,
CLAUDE.md §6.6 rule 9). Skips cleanly only via marker selection, never `pytest.skip`.
"""

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import DBAPIError

from app.core.config import get_config
from app.model_registry import SCHEMAS, metadata

pytestmark = pytest.mark.integration

APPEND_ONLY = {
    "auth.refresh_tokens", "platform.audit_logs", "platform.data_lineage",
    "platform.outbox_events", "platform.processed_events", "platform.notifications",
    "ai.conversations", "ai.messages", "ai.tool_call_logs", "ai.model_call_logs", "ai.feedback",
    "idp.document_pages", "idp.extraction_jobs", "idp.extraction_reviews", "idp.import_batches",
    "idp.review_assignments", "hr.salary_history", "sales.deal_stage_history",
    "risk.risk_assessments", "execution.kpi_measurements", "product.product_metrics",
    "execution.check_ins", "execution.kr_measurements",
    "idp.import_rows", "idp.document_actions",  # M1.5 log tables (05 §2.7)
}  # fmt: skip


@pytest.fixture(scope="module")
def engine() -> Engine:
    eng = create_engine(get_config().database_url.get_secret_value())
    yield eng  # type: ignore[misc]
    eng.dispose()


def _tables(engine: Engine) -> set[str]:
    sql = text(
        "SELECT table_schema || '.' || table_name FROM information_schema.tables "
        "WHERE table_schema = ANY(:s) AND table_type = 'BASE TABLE' "
        "AND table_name <> 'alembic_version' "
        # migration bookkeeping (e.g. `execution._m13_assignee_backfill`, 05 §2.5) is not a model
        "AND table_name NOT LIKE '\\_%'"
    )
    with engine.connect() as c:
        return set(c.execute(sql, {"s": list(SCHEMAS)}).scalars())


def test_all_module_schemas_exist(engine: Engine) -> None:
    with engine.connect() as c:
        found = set(c.execute(text("SELECT nspname FROM pg_namespace")).scalars())
    assert set(SCHEMAS) <= found
    assert "dashboard" not in found  # DEC-125: dashboard has no schema


def test_db_tables_match_metadata(engine: Engine) -> None:
    assert _tables(engine) == set(metadata.tables)


# Columns named like C19 but with a different meaning in 05 (not optimistic locking).
NON_C19_VERSION = {"platform.outbox_events"}  # 05 §5.1: payload schema version
# Log tables with an optimistic-lock `version` but no other C19 (05 §2.7: EP-DC-19/22 lock).
LOG_WITH_VERSION = {"idp.import_batches"}
# Log tables that 05 explicitly soft-deletes (05 §4.8: "xóa hội thoại = xóa mềm ở conversations").
SOFT_DELETED_LOGS = {"ai.conversations"}


def test_c19_columns_by_group() -> None:
    for name, table in metadata.tables.items():
        cols = set(table.c.keys())
        if name in APPEND_ONLY:
            forbidden = {"source"} | (set() if name in SOFT_DELETED_LOGS else {"deleted_at"})
            if name not in NON_C19_VERSION | LOG_WITH_VERSION:
                forbidden.add("version")
            assert not forbidden & cols, name
        else:
            assert {"version", "data_classification"} <= cols, name


def test_audit_logs_reject_update(engine: Engine) -> None:
    with engine.connect() as c:
        tx = c.begin()
        try:
            c.execute(
                text(
                    "INSERT INTO platform.audit_logs (actor_type, action) "
                    "VALUES ('SYSTEM', 'test.probe')"
                )
            )
            with pytest.raises(DBAPIError, match="append-only"):
                c.execute(text("UPDATE platform.audit_logs SET action = 'x'"))
        finally:
            tx.rollback()


def test_no_cross_schema_foreign_keys() -> None:
    """05 §1 C7 — cross-schema references are soft (uuid + index), never FK constraints."""
    for name, table in metadata.tables.items():
        for fk in table.foreign_keys:
            assert fk.column.table.schema == table.schema, f"{name} -> {fk.target_fullname}"


def test_foreign_keys_are_indexed() -> None:
    """05 §1 C6 — every FK column has an index."""
    for name, table in metadata.tables.items():
        indexed = {idx.columns.keys()[0] for idx in table.indexes if idx.columns.keys()}
        unique = {c.name for c in table.columns if c.unique}
        for fk in table.foreign_keys:
            col = fk.parent.name
            assert col in indexed or col in unique, f"{name}.{col}"
