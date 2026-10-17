"""Reusable metadata checker for TC-DATA-002 (05 §1 C3–C6; CLAUDE.md § Database).

Later tasks (T-101, T-102, T-201, T-301) get coverage for free: the test runs the checker
over the real ``Base.metadata`` once entity models are registered on it.
"""

from collections.abc import Iterable

from sqlalchemy import DateTime, MetaData, Table, Uuid

# audit_logs is append-only and has no deleted_at (05 §1 C5, §4.12).
DEFAULT_SOFT_DELETE_EXEMPT: frozenset[str] = frozenset({"audit_logs"})


def _check_timestamp(table: Table, name: str, *, nullable: bool) -> list[str]:
    col = table.columns.get(name)
    if col is None:
        return [f"{table.name}: missing column '{name}'"]
    problems: list[str] = []
    if not (isinstance(col.type, DateTime) and col.type.timezone):
        problems.append(f"{table.name}.{name}: must be timestamptz (DateTime(timezone=True))")
    if col.nullable != nullable:
        problems.append(f"{table.name}.{name}: nullable must be {nullable}")
    return problems


def _indexed_leading_columns(table: Table) -> set[str]:
    """Column names that lead an index/PK/unique constraint (usable for FK lookups)."""
    leading: set[str] = set()
    for index in table.indexes:
        cols = list(index.columns)
        if cols:
            leading.add(cols[0].name)
    for column in table.columns:
        if column.index or column.unique:
            leading.add(column.name)
    pk_cols = list(table.primary_key.columns)
    if pk_cols:
        leading.add(pk_cols[0].name)
    return leading


def check_table(table: Table, *, soft_delete_exempt: Iterable[str] = ()) -> list[str]:
    problems: list[str] = []

    id_col = table.columns.get("id")
    if id_col is None:
        problems.append(f"{table.name}: missing column 'id'")
    else:
        if not isinstance(id_col.type, Uuid):
            problems.append(f"{table.name}.id: must be uuid")
        if not id_col.primary_key:
            problems.append(f"{table.name}.id: must be the primary key")

    problems += _check_timestamp(table, "created_at", nullable=False)
    problems += _check_timestamp(table, "updated_at", nullable=False)
    if table.name not in set(soft_delete_exempt):
        problems += _check_timestamp(table, "deleted_at", nullable=True)

    indexed = _indexed_leading_columns(table)
    for fk in table.foreign_keys:
        if fk.parent.name not in indexed:
            problems.append(f"{table.name}.{fk.parent.name}: foreign key column has no index")
    return problems


def check_metadata(
    metadata: MetaData,
    *,
    soft_delete_exempt: Iterable[str] = DEFAULT_SOFT_DELETE_EXEMPT,
) -> list[str]:
    """Return human-readable violations for every table in ``metadata`` (empty = OK)."""
    exempt = frozenset(soft_delete_exempt)
    problems: list[str] = []
    for table in metadata.sorted_tables:
        problems += check_table(table, soft_delete_exempt=exempt)
    return problems
