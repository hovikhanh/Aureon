"""rename extraction_schemas.version to schema_version (DEC-162); feedback CK = 1 (DEC-165)

Revision ID: 0006_extraction_schema_version
Revises: 0005_ai_idp_baseline
Create Date: 2026-10-21

`version` on `idp.extraction_schemas` carried the business schema version (05 §4.9). It is
renamed to `schema_version` (data preserved) and a fresh C19 `version` (optimistic lock,
default 1) is added, so the table matches the other config tables (05 §2.1).

Every migration must be reversible (05 §12.1 G3): implement both upgrade() and downgrade().
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0006_extraction_schema_version"
down_revision: str | Sequence[str] | None = "0005_ai_idp_baseline"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

T = "extraction_schemas"
S = "idp"
OLD_UQ = "uq_extraction_schemas_document_type_id_version"
NEW_UQ = "uq_extraction_schemas_document_type_id_schema_version"


def upgrade() -> None:
    op.drop_index(OLD_UQ, table_name=T, schema=S)
    # Business version has no default (set explicitly on publish); drop the C19 default it carried.
    op.alter_column(T, "version", new_column_name="schema_version", server_default=None, schema=S)
    op.add_column(
        T,
        sa.Column("version", sa.Integer(), server_default=sa.text("1"), nullable=False),
        schema=S,
    )
    op.create_index(NEW_UQ, T, ["document_type_id", "schema_version"], unique=True, schema=S)

    op.drop_constraint(op.f("ck_feedback_has_target"), "feedback", schema="ai", type_="check")
    op.create_check_constraint(
        op.f("ck_feedback_one_target"),
        "feedback",
        "num_nonnulls(message_id, insight_id) = 1",
        schema="ai",
    )


def downgrade() -> None:
    op.drop_constraint(op.f("ck_feedback_one_target"), "feedback", schema="ai", type_="check")
    op.create_check_constraint(
        op.f("ck_feedback_has_target"),
        "feedback",
        "num_nonnulls(message_id, insight_id) >= 1",
        schema="ai",
    )

    op.drop_index(NEW_UQ, table_name=T, schema=S)
    op.drop_column(T, "version", schema=S)
    op.alter_column(
        T, "schema_version", new_column_name="version", server_default=sa.text("1"), schema=S
    )
    op.create_index(OLD_UQ, T, ["document_type_id", "version"], unique=True, schema=S)
