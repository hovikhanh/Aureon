"""R-DEC-176 (D-08 defaults, D-21) — CRM Lead / Contact / Activity in schema `sales`.

Revision ID: 0028_crm_leads_contacts_activity
Revises: 0027_external_event_link_c19
Create Date: 2026-11-09

Additive only (05 §2.13): 3 new tables `sales.leads`, `sales.contacts`, `sales.activities`
(`BusinessModel`: id / tenant_id / created_at / updated_at / deleted_at / created_by /
updated_by / version / data_classification / source), 4 new enums, 3 code sequences
(`LD-` / `CT-` / `SA-` + 6 digits, unique). FKs stay inside `sales` (C7), every FK indexed (C6).
No existing column or table is changed — the flat contact columns of `sales.clients` stay.

Reversible: downgrade drops the 3 tables, the 3 sequences and the 4 enums.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0028_crm_leads_contacts_activity"  # ≤ 32 chars (alembic_version)
down_revision: str | Sequence[str] | None = "0027_external_event_link_c19"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

DEFAULT_TENANT_ID = "00000000-0000-0000-0000-000000000001"
S = "sales"
ENUMS: dict[str, tuple[str, ...]] = {
    "lead_status": (
        "new", "contacted", "engaged", "qualified", "nurturing", "converted", "disqualified",
    ),
    "influence_level": ("low", "medium", "high"),
    "activity_type": (
        "call", "email", "meeting", "demo", "workshop", "poc", "proposal", "follow_up", "other",
    ),
    "activity_status": ("planned", "completed", "cancelled"),
}  # fmt: skip
SEQUENCES = {"leads": ("LD", "lead_code_seq"), "contacts": ("CT", "contact_code_seq"),
             "activities": ("SA", "activity_code_seq")}  # fmt: skip


def _enum(name: str) -> postgresql.ENUM:
    return postgresql.ENUM(name=name, schema=S, create_type=False)


def _ts(name: str) -> sa.Column[sa.DateTime]:
    return sa.Column(
        name, sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
    )


def _common(table: str) -> list[sa.Column]:
    prefix, seq = SEQUENCES[table]
    code = f"'{prefix}-' || lpad(nextval('{S}.{seq}')::text, 6, '0')"
    return [
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column(
            "tenant_id",
            sa.UUID(),
            server_default=sa.text(f"'{DEFAULT_TENANT_ID}'"),
            nullable=False,
        ),
        _ts("created_at"),
        _ts("updated_at"),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", sa.UUID(), nullable=True),
        sa.Column("updated_by", sa.UUID(), nullable=True),
        sa.Column("version", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.Column(
            "data_classification",
            postgresql.ENUM(name="data_classification", schema="platform", create_type=False),
            server_default="INTERNAL",
            nullable=False,
        ),
        sa.Column(
            "source",
            postgresql.ENUM(name="record_source", schema="platform", create_type=False),
            nullable=False,
        ),
        sa.Column("code", sa.Text(), server_default=sa.text(code), nullable=False),
    ]


def _fk(table: str, col: str, ref: str) -> sa.ForeignKeyConstraint:
    return sa.ForeignKeyConstraint(
        [col], [f"{S}.{ref}.id"], name=f"fk_{table}_{col}_{ref}", ondelete="RESTRICT"
    )


def _indexes(table: str, *cols: str) -> None:
    for col in ("tenant_id", *cols):
        op.create_index(f"ix_{table}_{col}", table, [col], schema=S)


def upgrade() -> None:
    bind = op.get_bind()
    for name, values in ENUMS.items():
        postgresql.ENUM(*values, name=name, schema=S).create(bind, checkfirst=True)
    for _prefix, seq in SEQUENCES.values():
        op.execute(f"CREATE SEQUENCE IF NOT EXISTS {S}.{seq}")

    op.create_table(
        "contacts",
        *_common("contacts"),
        sa.Column("client_id", sa.UUID(), nullable=False),
        sa.Column("first_name", sa.Text(), nullable=False),
        sa.Column("last_name", sa.Text(), nullable=True),
        sa.Column("job_title", sa.Text(), nullable=True),
        sa.Column("department", sa.Text(), nullable=True),
        sa.Column("email", sa.Text(), nullable=True),
        sa.Column("phone", sa.Text(), nullable=True),
        sa.Column(
            "roles", postgresql.ARRAY(sa.Text()), server_default=sa.text("'{}'"), nullable=False
        ),
        sa.Column("decision_authority", sa.Text(), nullable=True),
        sa.Column("influence_level", _enum("influence_level"), nullable=True),
        sa.Column("owner_id", sa.UUID(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_contacts"),
        sa.UniqueConstraint("code", name="uq_contacts_code"),
        _fk("contacts", "client_id", "clients"),
        schema=S,
    )
    _indexes("contacts", "client_id", "owner_id")

    op.create_table(
        "leads",
        *_common("leads"),
        sa.Column("company_name", sa.Text(), nullable=True),
        sa.Column("full_name", sa.Text(), nullable=False),
        sa.Column("job_title", sa.Text(), nullable=True),
        sa.Column("email", sa.Text(), nullable=True),
        sa.Column("phone", sa.Text(), nullable=True),
        sa.Column("industry", sa.Text(), nullable=True),
        sa.Column("lead_source", sa.Text(), nullable=True),
        sa.Column("need", sa.Text(), nullable=True),
        sa.Column("budget", sa.BigInteger(), nullable=True),
        sa.Column("currency", sa.CHAR(3), server_default=sa.text("'VND'"), nullable=False),
        sa.Column("score", sa.SmallInteger(), server_default=sa.text("0"), nullable=False),
        sa.Column("status", _enum("lead_status"), server_default=sa.text("'new'"), nullable=False),
        sa.Column("owner_id", sa.UUID(), nullable=False),
        sa.Column("department_id", sa.UUID(), nullable=True),
        sa.Column("next_action", sa.Text(), nullable=True),
        sa.Column("next_action_date", sa.Date(), nullable=True),
        sa.Column("converted_client_id", sa.UUID(), nullable=True),
        sa.Column("converted_contact_id", sa.UUID(), nullable=True),
        sa.Column("converted_deal_id", sa.UUID(), nullable=True),
        sa.Column("converted_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_leads"),
        sa.UniqueConstraint("code", name="uq_leads_code"),
        sa.CheckConstraint(
            "email IS NOT NULL OR phone IS NOT NULL", name="ck_leads_contact_channel_required"
        ),
        sa.CheckConstraint("score >= 0 AND score <= 100", name="ck_leads_score_range"),
        sa.CheckConstraint("budget IS NULL OR budget >= 0", name="ck_leads_budget_non_negative"),
        _fk("leads", "converted_client_id", "clients"),
        _fk("leads", "converted_contact_id", "contacts"),
        _fk("leads", "converted_deal_id", "deals"),
        schema=S,
    )
    _indexes(
        "leads", "owner_id", "department_id", "converted_client_id", "converted_contact_id",
        "converted_deal_id",
    )  # fmt: skip
    op.create_index(
        "ix_leads_status_next_action_date", "leads", ["status", "next_action_date"], schema=S
    )

    op.create_table(
        "activities",
        *_common("activities"),
        sa.Column("type", _enum("activity_type"), nullable=False),
        sa.Column("subject", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("lead_id", sa.UUID(), nullable=True),
        sa.Column("client_id", sa.UUID(), nullable=True),
        sa.Column("contact_id", sa.UUID(), nullable=True),
        sa.Column("deal_id", sa.UUID(), nullable=True),
        sa.Column("owner_id", sa.UUID(), nullable=False),
        sa.Column("department_id", sa.UUID(), nullable=True),
        sa.Column("start_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "status",
            _enum("activity_status"),
            server_default=sa.text("'planned'"),
            nullable=False,
        ),
        sa.Column("outcome", sa.Text(), nullable=True),
        sa.Column("next_action", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_activities"),
        sa.UniqueConstraint("code", name="uq_activities_code"),
        sa.CheckConstraint(
            "lead_id IS NOT NULL OR client_id IS NOT NULL OR contact_id IS NOT NULL "
            "OR deal_id IS NOT NULL",
            name="ck_activities_link_required",
        ),
        sa.CheckConstraint(
            "end_at IS NULL OR end_at >= start_at", name="ck_activities_end_after_start"
        ),
        _fk("activities", "lead_id", "leads"),
        _fk("activities", "client_id", "clients"),
        _fk("activities", "contact_id", "contacts"),
        _fk("activities", "deal_id", "deals"),
        schema=S,
    )
    _indexes(
        "activities", "lead_id", "client_id", "contact_id", "deal_id", "owner_id", "department_id"
    )
    op.create_index("ix_activities_status_start_at", "activities", ["status", "start_at"], schema=S)


def downgrade() -> None:
    op.drop_table("activities", schema=S)
    op.drop_table("leads", schema=S)
    op.drop_table("contacts", schema=S)
    for _prefix, seq in SEQUENCES.values():
        op.execute(f"DROP SEQUENCE IF EXISTS {S}.{seq}")
    for name in ENUMS:
        postgresql.ENUM(name=name, schema=S).drop(op.get_bind(), checkfirst=True)
