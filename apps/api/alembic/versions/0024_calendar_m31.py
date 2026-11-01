"""M3.1 D06 Integration Hub + D13 Calendar: calendar_events / calendar_accounts /
calendar_sync_states / external_event_links (05 §2.10, R-DEC-117).

Revision ID: 0024_calendar_m31
Revises: 0023_meeting_m23
Create Date: 2026-11-01

- T-801: ENT-CalendarEvent (`execution.calendar_events`) + ENT-ExternalEventLink
  (`execution.external_event_links`) + ENT-CalendarAccount (`platform.calendar_accounts`,
  token `EncryptedText` = bytea/pgcrypto) + ENT-SyncState (`platform.calendar_sync_states`).
  Enum mới: `execution.calendar_source`, `platform.calendar_provider`,
  `platform.calendar_account_status`. Lịch mức 3 Confidential (R-DEC-123). Soft ref owner_id/
  account_id không FK chéo schema (C7); FK cùng schema (tasks, calendar_events, calendar_accounts).

Reversible: downgrade drop 4 bảng + 3 enum.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0024_calendar_m31"
down_revision: str | Sequence[str] | None = "0023_meeting_m23"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

DEFAULT_TENANT_ID = "00000000-0000-0000-0000-000000000001"
EXEC = "execution"
PLAT = "platform"


def _tenant() -> sa.Column[sa.Uuid]:
    return sa.Column(
        "tenant_id", sa.UUID(), server_default=sa.text(f"'{DEFAULT_TENANT_ID}'"), nullable=False
    )


def _ts(name: str, *, nullable: bool = False) -> sa.Column[sa.DateTime]:
    default = sa.text("now()") if not nullable else None
    return sa.Column(name, sa.DateTime(timezone=True), server_default=default, nullable=nullable)


def _business(schema: str) -> list[sa.Column]:
    """BusinessModel common columns (05 §2.1 group 1): id/tenant/ts/soft-delete/actor/C19."""
    return [
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        _tenant(),
        _ts("created_at"),
        _ts("updated_at"),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", sa.UUID(), nullable=True),
        sa.Column("updated_by", sa.UUID(), nullable=True),
        sa.Column("version", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.Column(
            "data_classification",
            postgresql.ENUM(name="data_classification", schema=PLAT, create_type=False),
            server_default="INTERNAL",
            nullable=False,
        ),
        sa.Column(
            "source",
            postgresql.ENUM(name="record_source", schema=PLAT, create_type=False),
            nullable=False,
        ),
    ]


def _log(schema: str) -> list[sa.Column]:
    """LogModel + TenantMixin (05 §2.1 group 3): id/created/updated/tenant, no C19/soft-delete."""
    return [
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        _ts("created_at"),
        _ts("updated_at"),
        _tenant(),
    ]


def upgrade() -> None:
    cal_source = postgresql.ENUM(
        "internal", "google", "outlook", name="calendar_source", schema=EXEC
    )
    cal_provider = postgresql.ENUM("google", "outlook", name="calendar_provider", schema=PLAT)
    cal_acct_status = postgresql.ENUM(
        "connected", "expired", "revoked", name="calendar_account_status", schema=PLAT
    )
    for e in (cal_source, cal_provider, cal_acct_status):
        e.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "calendar_events",
        *_business(EXEC),
        sa.Column("owner_id", sa.UUID(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("location", sa.Text(), nullable=True),
        sa.Column(
            "event_source",
            postgresql.ENUM(name="calendar_source", schema=EXEC, create_type=False),
            server_default=sa.text("'internal'"),
            nullable=False,
        ),
        sa.Column("visibility", sa.Text(), server_default=sa.text("'private'"), nullable=False),
        sa.Column("task_id", sa.UUID(), nullable=True),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_calendar_events")),
        sa.ForeignKeyConstraint(
            ["task_id"], [f"{EXEC}.tasks.id"],
            name=op.f("fk_calendar_events_task_id_tasks"), ondelete="SET NULL",
        ),
        schema=EXEC,
    )  # fmt: skip
    op.create_index("ix_calendar_events_tenant_id", "calendar_events", ["tenant_id"], schema=EXEC)
    op.create_index("ix_calendar_events_owner_id", "calendar_events", ["owner_id"], schema=EXEC)
    op.create_index("ix_calendar_events_task_id", "calendar_events", ["task_id"], schema=EXEC)

    op.create_table(
        "calendar_accounts",
        *_business(PLAT),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column(
            "provider",
            postgresql.ENUM(name="calendar_provider", schema=PLAT, create_type=False),
            nullable=False,
        ),
        sa.Column("access_token", sa.LargeBinary(), nullable=True),
        sa.Column("refresh_token", sa.LargeBinary(), nullable=True),
        sa.Column("scope", sa.Text(), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "status",
            postgresql.ENUM(name="calendar_account_status", schema=PLAT, create_type=False),
            server_default=sa.text("'connected'"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_calendar_accounts")),
        sa.UniqueConstraint(
            "tenant_id", "user_id", "provider", name="uq_calendar_accounts_user_provider"
        ),
        schema=PLAT,
    )
    op.create_index(
        "ix_calendar_accounts_tenant_id", "calendar_accounts", ["tenant_id"], schema=PLAT
    )
    op.create_index("ix_calendar_accounts_user_id", "calendar_accounts", ["user_id"], schema=PLAT)

    op.create_table(
        "calendar_sync_states",
        *_log(PLAT),
        sa.Column("account_id", sa.UUID(), nullable=False),
        sa.Column("sync_token", sa.Text(), nullable=True),
        sa.Column("delta_link", sa.Text(), nullable=True),
        sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cursor", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_calendar_sync_states")),
        sa.ForeignKeyConstraint(
            ["account_id"], [f"{PLAT}.calendar_accounts.id"],
            name=op.f("fk_calendar_sync_states_account_id_accounts"), ondelete="CASCADE",
        ),
        schema=PLAT,
    )  # fmt: skip
    op.create_index(
        "ix_calendar_sync_states_tenant_id", "calendar_sync_states", ["tenant_id"], schema=PLAT
    )
    op.create_index(
        "ix_calendar_sync_states_account_id", "calendar_sync_states", ["account_id"], schema=PLAT
    )

    op.create_table(
        "external_event_links",
        *_log(EXEC),
        sa.Column("calendar_event_id", sa.UUID(), nullable=False),
        sa.Column("account_id", sa.UUID(), nullable=False),
        sa.Column("external_id", sa.Text(), nullable=False),
        sa.Column("etag", sa.Text(), nullable=True),
        sa.Column("last_pushed_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_external_event_links")),
        sa.ForeignKeyConstraint(
            ["calendar_event_id"], [f"{EXEC}.calendar_events.id"],
            name=op.f("fk_external_event_links_event_id"), ondelete="CASCADE",
        ),
        schema=EXEC,
    )  # fmt: skip
    op.create_index(
        "ix_external_event_links_tenant_id", "external_event_links", ["tenant_id"], schema=EXEC
    )
    op.create_index(
        "ix_external_event_links_event_id",
        "external_event_links", ["calendar_event_id"], schema=EXEC,
    )  # fmt: skip
    op.create_index(
        "ix_external_event_links_account_id", "external_event_links", ["account_id"], schema=EXEC
    )
    op.create_index(
        "uq_external_event_links_acct_ext",
        "external_event_links", ["account_id", "external_id"], unique=True, schema=EXEC,
    )  # fmt: skip


def downgrade() -> None:
    op.drop_table("external_event_links", schema=EXEC)
    op.drop_table("calendar_sync_states", schema=PLAT)
    op.drop_table("calendar_accounts", schema=PLAT)
    op.drop_table("calendar_events", schema=EXEC)
    postgresql.ENUM(name="calendar_account_status", schema=PLAT).drop(
        op.get_bind(), checkfirst=True
    )
    postgresql.ENUM(name="calendar_provider", schema=PLAT).drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name="calendar_source", schema=EXEC).drop(op.get_bind(), checkfirst=True)
