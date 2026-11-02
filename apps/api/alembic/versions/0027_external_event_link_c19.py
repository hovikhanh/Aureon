"""M3.1 fix — ExternalEventLink / SyncState are BusinessModel (05 §2.10), not LogModel.

Revision ID: 0027_external_event_link_c19
Revises: 0026_ai_evaluation_m34
Create Date: 2026-11-02

05 §2.10 declares `execution.external_event_links` AND `platform.calendar_sync_states` as
`BusinessModel` (C19: `version` + `data_classification` + `source`, soft-delete, actor).
Migration `0024_calendar_m31` built both with the `LogModel` column set, so
`test_c19_columns_by_group` fails and the models/migration disagreed. This adds the missing
group-1 columns to each. Both tables are empty in every environment, so the one-off
`server_default` on `source` only guards legacy rows; it is dropped immediately so the column
matches `SourceMixin` (no Python/SQL default — the repository sets it explicitly).

Reversible: downgrade drops the 6 added columns from each table.
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0027_external_event_link_c19"
down_revision: str | Sequence[str] | None = "0026_ai_evaluation_m34"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

PLAT = "platform"
# (schema, table) pairs that migration 0024 built as LogModel but 05 §2.10 marks BusinessModel.
TABLES = (("execution", "external_event_links"), ("platform", "calendar_sync_states"))


def _add_c19(schema: str, table: str) -> None:
    fq = f"{schema}.{table}"
    # Idempotent `ADD COLUMN IF NOT EXISTS` so a partially-applied run heals on re-upgrade.
    op.execute(f"ALTER TABLE {fq} ADD COLUMN IF NOT EXISTS deleted_at timestamptz NULL")
    op.execute(f"ALTER TABLE {fq} ADD COLUMN IF NOT EXISTS created_by uuid NULL")
    op.execute(f"ALTER TABLE {fq} ADD COLUMN IF NOT EXISTS updated_by uuid NULL")
    op.execute(f"ALTER TABLE {fq} ADD COLUMN IF NOT EXISTS version integer NOT NULL DEFAULT 1")
    op.execute(
        f"ALTER TABLE {fq} ADD COLUMN IF NOT EXISTS data_classification "
        f"{PLAT}.data_classification NOT NULL DEFAULT 'INTERNAL'"
    )
    # `source`: transient default to satisfy NOT NULL on any legacy row, then drop the default so
    # the column matches `SourceMixin` (the repository passes `source=` on every insert).
    op.execute(
        f"ALTER TABLE {fq} ADD COLUMN IF NOT EXISTS source "
        f"{PLAT}.record_source NOT NULL DEFAULT 'EVENT'"
    )
    op.execute(f"ALTER TABLE {fq} ALTER COLUMN source DROP DEFAULT")


def upgrade() -> None:
    for schema, table in TABLES:
        _add_c19(schema, table)


def downgrade() -> None:
    for schema, table in TABLES:
        fq = f"{schema}.{table}"
        for col in ("source", "data_classification", "version", "updated_by", "created_by",
                    "deleted_at"):  # fmt: skip
            op.execute(f"ALTER TABLE {fq} DROP COLUMN IF EXISTS {col}")
