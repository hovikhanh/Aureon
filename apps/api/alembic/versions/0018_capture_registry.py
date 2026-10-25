"""M1.5 T-636: Action Registry v2 + capture bookkeeping (idp + platform.data_lineage).

Revision ID: 0018_capture_registry
Revises: 0017_goals_measure_m14
Create Date: 2026-10-24

05 §2.7 / R-DEC-60..64, 69:
- `idp.source_documents`: `committed_by`, `rolled_back_at`, `rolled_back_by`,
  `rollback_reason_code` (CHECK), `row_count` (CHECK ≥ 0) + inbox indexes.
- `idp.import_batches`: `tenant_id` (backfill = system tenant), `source_document_id` (FK),
  `document_type_id` (FK), `sheet_name`, `header_row` (CHECK 1..50), `rows_total/valid/invalid`,
  `version`.
- `idp.document_types.classifier_keywords text[]` (R-DEC-65).
- new `idp.import_rows`, `idp.document_actions`, `idp.capture_incidents`.
- `platform.data_lineage`: `tenant_id` (backfill), `document_action_id`, `row_index` + indexes.

Downgrade drops the new tables/columns (document action log, import preview rows and incidents
are lost).
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0018_capture_registry"
down_revision: str | None = "0017_goals_measure_m14"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

DEFAULT_TENANT_ID = "00000000-0000-0000-0000-000000000001"
S = "idp"
JSONB = postgresql.JSONB(astext_type=sa.Text())


def _enum(name: str) -> postgresql.ENUM:
    return postgresql.ENUM(name=name, schema="platform", create_type=False)


def _ts(name: str, *, nullable: bool = False) -> sa.Column[object]:
    default = None if nullable else sa.text("now()")
    return sa.Column(name, sa.DateTime(timezone=True), server_default=default, nullable=nullable)


def _tenant() -> sa.Column[object]:
    return sa.Column(
        "tenant_id", sa.UUID(), server_default=sa.text(f"'{DEFAULT_TENANT_ID}'"), nullable=False
    )


def _log_columns() -> list[sa.Column[object]]:
    return [
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        _ts("created_at"),
        _ts("updated_at"),
        _tenant(),
    ]


def _business_columns() -> list[sa.Column[object]]:
    return [
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        _tenant(),
        _ts("created_at"),
        _ts("updated_at"),
        _ts("deleted_at", nullable=True),
        sa.Column("created_by", sa.UUID(), nullable=True),
        sa.Column("updated_by", sa.UUID(), nullable=True),
        sa.Column("source", _enum("record_source"), nullable=False),
        sa.Column("data_classification", _enum("data_classification"),
                  server_default="INTERNAL", nullable=False),
        sa.Column("version", sa.Integer(), server_default=sa.text("1"), nullable=False),
    ]  # fmt: skip


def _fk(table: str, col: str, ref: str, ondelete: str = "RESTRICT") -> sa.ForeignKeyConstraint:
    return sa.ForeignKeyConstraint(
        [col], [f"{S}.{ref}.id"], name=op.f(f"fk_{table}_{col}_{ref}"), ondelete=ondelete
    )


def _ck(table: str, name: str, sql: str) -> None:
    op.create_check_constraint(op.f(f"ck_{table}_{name}"), table, sql, schema=S)


def _columns_upgrade() -> None:
    d = "source_documents"
    for col in ("committed_by", "rolled_back_by"):
        op.add_column(d, sa.Column(col, sa.UUID(), nullable=True), schema=S)
    op.add_column(d, _ts("rolled_back_at", nullable=True), schema=S)
    op.add_column(d, sa.Column("rollback_reason_code", sa.Text(), nullable=True), schema=S)
    op.add_column(d, sa.Column("row_count", sa.Integer(), nullable=True), schema=S)
    _ck(d, "rollback_reason_code_values",
        "rollback_reason_code IN ('mistake', 'critical_field_wrong', 'duplicate', 'other')")  # fmt: skip
    _ck(d, "row_count_non_negative", "row_count >= 0")
    op.create_index("ix_source_documents_submitted_by_status", d, ["submitted_by", "status"],
                    schema=S)  # fmt: skip
    op.create_index("ix_source_documents_department_id_status", d, ["department_id", "status"],
                    schema=S)  # fmt: skip

    b = "import_batches"
    op.add_column(b, _tenant(), schema=S)
    for col in ("source_document_id", "document_type_id"):
        op.add_column(b, sa.Column(col, sa.UUID(), nullable=True), schema=S)
    op.add_column(b, sa.Column("sheet_name", sa.Text(), nullable=True), schema=S)
    op.add_column(b, sa.Column("header_row", sa.SmallInteger(), nullable=True), schema=S)
    for col in ("rows_total", "rows_valid", "rows_invalid"):
        op.add_column(b, sa.Column(col, sa.Integer(), server_default=sa.text("0"),
                                   nullable=False), schema=S)  # fmt: skip
    op.add_column(b, sa.Column("version", sa.Integer(), server_default=sa.text("1"),
                               nullable=False), schema=S)  # fmt: skip
    _ck(b, "header_row_1_50", "header_row BETWEEN 1 AND 50")
    _ck(b, "rows_non_negative", "rows_total >= 0 AND rows_valid >= 0 AND rows_invalid >= 0")
    for col, ref in (("source_document_id", "source_documents"),
                     ("document_type_id", "document_types")):  # fmt: skip
        op.create_foreign_key(op.f(f"fk_{b}_{col}_{ref}"), b, ref, [col], ["id"],
                              source_schema=S, referent_schema=S, ondelete="RESTRICT")  # fmt: skip
    for col in ("tenant_id", "source_document_id", "document_type_id"):
        op.create_index(op.f(f"ix_{b}_{col}"), b, [col], schema=S)

    op.add_column("document_types", sa.Column("classifier_keywords", sa.ARRAY(sa.Text()),
                  server_default=sa.text("'{}'"), nullable=False), schema=S)  # fmt: skip

    lin = "data_lineage"
    op.add_column(lin, _tenant(), schema="platform")
    op.add_column(lin, sa.Column("document_action_id", sa.UUID(), nullable=True), schema="platform")
    op.add_column(lin, sa.Column("row_index", sa.Integer(), nullable=True), schema="platform")
    op.create_index(op.f("ix_data_lineage_tenant_id"), lin, ["tenant_id"], schema="platform")
    op.create_index("ix_data_lineage_target_live", lin,
                    ["target_schema", "target_table", "target_id"], schema="platform",
                    postgresql_where=sa.text("revoked_at IS NULL"))  # fmt: skip
    # `ix_data_lineage_source_document_id` already exists (sr() index since 0001).


def _tables_upgrade() -> None:
    r = "import_rows"
    op.create_table(
        r,
        *_log_columns(),
        sa.Column("import_batch_id", sa.UUID(), nullable=False),
        sa.Column("row_number", sa.Integer(), nullable=False),
        sa.Column("raw", JSONB, nullable=False),
        sa.Column("values", JSONB, nullable=True),
        sa.Column("errors", JSONB, server_default=sa.text("'[]'"), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.CheckConstraint("status IN ('valid', 'invalid')", name=op.f(f"ck_{r}_status_values")),
        _fk(r, "import_batch_id", "import_batches", "CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f(f"pk_{r}")),
        schema=S,
    )
    op.create_index(op.f(f"ix_{r}_tenant_id"), r, ["tenant_id"], schema=S)
    op.create_index("uq_import_rows_batch_row", r, ["import_batch_id", "row_number"], unique=True,
                    schema=S)  # fmt: skip
    op.create_index("ix_import_rows_import_batch_id_status", r, ["import_batch_id", "status"],
                    schema=S)  # fmt: skip

    a = "document_actions"
    op.create_table(
        a,
        *_log_columns(),
        sa.Column("source_document_id", sa.UUID(), nullable=False),
        sa.Column("seq", sa.Integer(), nullable=False),
        sa.Column("action_name", sa.Text(), nullable=False),
        sa.Column("row_index", sa.Integer(), nullable=True),
        sa.Column("params", JSONB, nullable=False),
        sa.Column("result_refs", JSONB, nullable=False),
        sa.Column("snapshot", JSONB, nullable=True),
        sa.Column("target_version", sa.Integer(), nullable=True),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("executed_by", sa.UUID(), nullable=False),
        _ts("executed_at"),
        _ts("reverted_at", nullable=True),
        sa.Column("reverted_by", sa.UUID(), nullable=True),
        sa.CheckConstraint("status IN ('applied', 'reverted')", name=op.f(f"ck_{a}_status_values")),
        _fk(a, "source_document_id", "source_documents"),
        sa.PrimaryKeyConstraint("id", name=op.f(f"pk_{a}")),
        schema=S,
    )
    for col in ("tenant_id", "source_document_id"):
        op.create_index(op.f(f"ix_{a}_{col}"), a, [col], schema=S)
    op.create_index("uq_document_actions_document_seq", a, ["source_document_id", "seq"],
                    unique=True, schema=S)  # fmt: skip

    c = "capture_incidents"
    op.create_table(
        c,
        sa.Column("source_document_id", sa.UUID(), nullable=False),
        sa.Column("extracted_field_id", sa.UUID(), nullable=True),
        sa.Column("field_name", sa.Text(), nullable=False),
        sa.Column("is_critical", sa.Boolean(), nullable=False),
        sa.Column("detected_by", sa.Text(), nullable=False),
        sa.Column("undetected", sa.Boolean(), nullable=False),
        sa.Column("target_table", sa.Text(), nullable=True),
        sa.Column("target_id", sa.UUID(), nullable=True),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("reported_by", sa.UUID(), nullable=False),
        _ts("reported_at"),
        *_business_columns(),
        sa.CheckConstraint(
            "detected_by IN ('review', 'post_commit', 'undo')",
            name=op.f(f"ck_{c}_detected_by_values"),
        ),
        sa.CheckConstraint(
            "char_length(description) <= 2000", name=op.f(f"ck_{c}_description_max_2000")
        ),
        _fk(c, "source_document_id", "source_documents"),
        _fk(c, "extracted_field_id", "extracted_fields"),
        sa.PrimaryKeyConstraint("id", name=op.f(f"pk_{c}")),
        schema=S,
    )
    for col in ("tenant_id", "source_document_id", "extracted_field_id"):
        op.create_index(op.f(f"ix_{c}_{col}"), c, [col], schema=S)
    op.create_index("ix_capture_incidents_undetected_reported_at", c,
                    ["undetected", "reported_at"], schema=S)  # fmt: skip


def upgrade() -> None:
    _columns_upgrade()
    _tables_upgrade()


def downgrade() -> None:
    for t in ("capture_incidents", "document_actions", "import_rows"):
        op.drop_table(t, schema=S)
    lin = "data_lineage"
    op.drop_index("ix_data_lineage_target_live", table_name=lin, schema="platform")
    op.drop_index(op.f("ix_data_lineage_tenant_id"), table_name=lin, schema="platform")
    for col in ("row_index", "document_action_id", "tenant_id"):
        op.drop_column(lin, col, schema="platform")
    op.drop_column("document_types", "classifier_keywords", schema=S)
    b = "import_batches"
    for col in ("tenant_id", "source_document_id", "document_type_id"):
        op.drop_index(op.f(f"ix_{b}_{col}"), table_name=b, schema=S)
    for col, ref in (("source_document_id", "source_documents"),
                     ("document_type_id", "document_types")):  # fmt: skip
        op.drop_constraint(op.f(f"fk_{b}_{col}_{ref}"), b, type_="foreignkey", schema=S)
    op.drop_constraint(op.f(f"ck_{b}_rows_non_negative"), b, type_="check", schema=S)
    op.drop_constraint(op.f(f"ck_{b}_header_row_1_50"), b, type_="check", schema=S)
    for col in ("version", "rows_invalid", "rows_valid", "rows_total", "header_row", "sheet_name",
                "document_type_id", "source_document_id", "tenant_id"):  # fmt: skip
        op.drop_column(b, col, schema=S)
    d = "source_documents"
    op.drop_index("ix_source_documents_department_id_status", table_name=d, schema=S)
    op.drop_index("ix_source_documents_submitted_by_status", table_name=d, schema=S)
    op.drop_constraint(op.f(f"ck_{d}_row_count_non_negative"), d, type_="check", schema=S)
    op.drop_constraint(op.f(f"ck_{d}_rollback_reason_code_values"), d, type_="check", schema=S)
    for col in ("row_count", "rollback_reason_code", "rolled_back_at", "rolled_back_by",
                "committed_by"):  # fmt: skip
        op.drop_column(d, col, schema=S)
