"""M1.1 T-603: `platform.outbox_events.tenant_id` (R-DEC-21, 05 §2.3).

Revision ID: 0010_tenant_outbox
Revises: 0009_v3_roles_tenant
Create Date: 2026-10-23

Reversible: add `tenant_id UUID NOT NULL` (server_default = MVP system tenant → backfills
existing rows) + index `ix_outbox_events_tenant_id`; downgrade drops both.
`processed_events` unchanged (DLQ tenant comes from the join with `outbox_events`).
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0010_tenant_outbox"
down_revision: str | None = "0009_v3_roles_tenant"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

DEFAULT_TENANT_ID = "00000000-0000-0000-0000-000000000001"


def upgrade() -> None:
    op.add_column(
        "outbox_events",
        sa.Column(
            "tenant_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            nullable=False,
            server_default=sa.text(f"'{DEFAULT_TENANT_ID}'"),
        ),
        schema="platform",
    )
    op.create_index("ix_outbox_events_tenant_id", "outbox_events", ["tenant_id"], schema="platform")


def downgrade() -> None:
    op.drop_index("ix_outbox_events_tenant_id", table_name="outbox_events", schema="platform")
    op.drop_column("outbox_events", "tenant_id", schema="platform")
