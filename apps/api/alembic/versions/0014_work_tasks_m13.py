"""M1.3 T-619: tasks sub-task / source_ref / dependencies, projects.initiative_id (05 §2.5).

Revision ID: 0014_work_tasks_m13
Revises: 0013_notifications_m12
Create Date: 2026-10-24

- `execution.tasks.parent_id` → `parent_task_id` (R-DEC-42; FK + index renamed with it).
- `execution.tasks.source_ref` JSONB + CHECK `kind`/`id`; backfill decision > meeting > document.
- `execution.tasks.assignee_id` = `hr.employees.id` (R-DEC-41): values equal to an `auth.users.id`
  with an `employee_id` are rewritten; the mapping is kept in `execution._m13_assignee_backfill`
  so downgrade can restore the old values.
- index `(tenant_id, assignee_id, due_date) WHERE deleted_at IS NULL` ("Task của tôi", workload).
- `execution.task_dependency_type` enum + `execution.task_dependencies` (BusinessModel, CASCADE FKs,
  CHECK not self, partial unique live `(tenant_id, task_id, depends_on_task_id)`).
- `execution.projects.initiative_id` (FK SET NULL) + index `(tenant_id, initiative_id)`.

Reversible: downgrade restores assignees, drops the new table/enum/columns, renames back.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0014_work_tasks_m13"
down_revision: str | None = "0013_notifications_m12"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

DEFAULT_TENANT_ID = "00000000-0000-0000-0000-000000000001"
S = "execution"
D = "task_dependencies"
SOURCE_REF_CK = "source_ref IS NULL OR (source_ref ? 'kind' AND source_ref ? 'id')"
SOURCE_REF_BACKFILL = (
    "UPDATE execution.tasks SET source_ref = CASE "
    "WHEN decision_id IS NOT NULL THEN jsonb_build_object('kind', 'decision', 'id', decision_id) "
    "WHEN meeting_id IS NOT NULL THEN jsonb_build_object('kind', 'meeting', 'id', meeting_id) "
    "ELSE jsonb_build_object('kind', 'document', 'id', source_document_id) END "
    "WHERE source_ref IS NULL AND (decision_id IS NOT NULL OR meeting_id IS NOT NULL "
    "OR source_document_id IS NOT NULL)"
)


def _enum(name: str, *values: str) -> postgresql.ENUM:
    return postgresql.ENUM(*values, name=name, create_type=False, schema="platform")


def _ts(name: str, *, nullable: bool = False) -> sa.Column[sa.DateTime]:
    default = None if nullable else sa.text("now()")
    return sa.Column(name, sa.DateTime(timezone=True), server_default=default, nullable=nullable)


def _tasks_upgrade() -> None:
    op.alter_column("tasks", "parent_id", new_column_name="parent_task_id", schema=S)
    op.execute(
        "ALTER TABLE execution.tasks RENAME CONSTRAINT fk_tasks_parent_id_tasks "
        "TO fk_tasks_parent_task_id_tasks"
    )
    op.execute("ALTER INDEX execution.ix_tasks_parent_id RENAME TO ix_tasks_parent_task_id")
    op.add_column("tasks", sa.Column("source_ref", postgresql.JSONB(), nullable=True), schema=S)
    op.create_check_constraint(
        op.f("ck_tasks_source_ref_kind_id"), "tasks", SOURCE_REF_CK, schema=S
    )
    op.execute(SOURCE_REF_BACKFILL)
    op.create_index(
        "ix_tasks_tenant_id_assignee_id_due_date", "tasks", ["tenant_id", "assignee_id", "due_date"],
        postgresql_where=sa.text("deleted_at IS NULL"), schema=S,
    )  # fmt: skip
    # R-DEC-41 backfill: assignee user id → employee id (keep the mapping for downgrade).
    op.execute(
        "CREATE TABLE execution._m13_assignee_backfill (task_id uuid PRIMARY KEY, user_id uuid NOT NULL)"
    )
    op.execute(
        "INSERT INTO execution._m13_assignee_backfill (task_id, user_id) SELECT t.id, t.assignee_id "
        "FROM execution.tasks t JOIN auth.users u ON u.id = t.assignee_id "
        "WHERE u.employee_id IS NOT NULL"
    )
    op.execute(
        "UPDATE execution.tasks t SET assignee_id = u.employee_id FROM execution._m13_assignee_backfill b "
        "JOIN auth.users u ON u.id = b.user_id WHERE t.id = b.task_id"
    )


def _dependencies_upgrade() -> None:
    dep_type = postgresql.ENUM("finish_to_start", name="task_dependency_type", schema=S)
    dep_type.create(op.get_bind(), checkfirst=True)
    op.create_table(
        D,
        sa.Column("task_id", sa.UUID(), nullable=False),
        sa.Column("depends_on_task_id", sa.UUID(), nullable=False),
        sa.Column(
            "dependency_type",
            postgresql.ENUM(name="task_dependency_type", schema=S, create_type=False),
            server_default=sa.text("'finish_to_start'"),
            nullable=False,
        ),
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column(
            "tenant_id", sa.UUID(), server_default=sa.text(f"'{DEFAULT_TENANT_ID}'"), nullable=False
        ),
        _ts("created_at"),
        _ts("updated_at"),
        _ts("deleted_at", nullable=True),
        sa.Column("created_by", sa.UUID(), nullable=True),
        sa.Column("updated_by", sa.UUID(), nullable=True),
        sa.Column(
            "source",
            _enum("record_source", "MANUAL", "IDP", "IMPORT", "AI", "EVENT", "SEED"),
            nullable=False,
        ),
        sa.Column(
            "data_classification",
            _enum("data_classification", "PUBLIC", "INTERNAL", "CONFIDENTIAL", "SECRET"),
            server_default="INTERNAL",
            nullable=False,
        ),
        sa.Column("version", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.CheckConstraint("task_id <> depends_on_task_id", name=op.f(f"ck_{D}_not_self")),
        *(
            sa.ForeignKeyConstraint(
                [col], [f"{S}.tasks.id"], name=op.f(f"fk_{D}_{col}_tasks"), ondelete="CASCADE"
            )
            for col in ("task_id", "depends_on_task_id")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f(f"pk_{D}")),
        schema=S,
    )
    for col in ("tenant_id", "task_id", "depends_on_task_id"):
        op.create_index(op.f(f"ix_{D}_{col}"), D, [col], schema=S)
    op.create_index(
        f"uq_{D}_tenant_id_task_id_depends_on_task_id_live", D,
        ["tenant_id", "task_id", "depends_on_task_id"], unique=True,
        postgresql_where=sa.text("deleted_at IS NULL"), schema=S,
    )  # fmt: skip


def _projects_upgrade() -> None:
    op.add_column("projects", sa.Column("initiative_id", sa.UUID(), nullable=True), schema=S)
    op.create_foreign_key(
        op.f("fk_projects_initiative_id_initiatives"), "projects", "initiatives",
        ["initiative_id"], ["id"], source_schema=S, referent_schema=S, ondelete="SET NULL",
    )  # fmt: skip
    op.create_index(op.f("ix_projects_initiative_id"), "projects", ["initiative_id"], schema=S)
    op.create_index(
        "ix_projects_tenant_id_initiative_id", "projects", ["tenant_id", "initiative_id"], schema=S
    )


def upgrade() -> None:
    _tasks_upgrade()
    _dependencies_upgrade()
    _projects_upgrade()


def downgrade() -> None:
    op.drop_index("ix_projects_tenant_id_initiative_id", table_name="projects", schema=S)
    op.drop_index(op.f("ix_projects_initiative_id"), table_name="projects", schema=S)
    op.drop_constraint(
        op.f("fk_projects_initiative_id_initiatives"), "projects", type_="foreignkey", schema=S
    )
    op.drop_column("projects", "initiative_id", schema=S)

    op.drop_index(f"uq_{D}_tenant_id_task_id_depends_on_task_id_live", table_name=D, schema=S)
    for col in ("tenant_id", "task_id", "depends_on_task_id"):
        op.drop_index(op.f(f"ix_{D}_{col}"), table_name=D, schema=S)
    op.drop_table(D, schema=S)
    postgresql.ENUM(name="task_dependency_type", schema=S).drop(op.get_bind(), checkfirst=True)

    op.execute(
        "UPDATE execution.tasks t SET assignee_id = b.user_id FROM execution._m13_assignee_backfill b "
        "WHERE t.id = b.task_id"
    )
    op.execute("DROP TABLE execution._m13_assignee_backfill")
    op.drop_index("ix_tasks_tenant_id_assignee_id_due_date", table_name="tasks", schema=S)
    op.drop_constraint(op.f("ck_tasks_source_ref_kind_id"), "tasks", type_="check", schema=S)
    op.drop_column("tasks", "source_ref", schema=S)
    op.execute("ALTER INDEX execution.ix_tasks_parent_task_id RENAME TO ix_tasks_parent_id")
    op.execute(
        "ALTER TABLE execution.tasks RENAME CONSTRAINT fk_tasks_parent_task_id_tasks "
        "TO fk_tasks_parent_id_tasks"
    )
    op.alter_column("tasks", "parent_task_id", new_column_name="parent_id", schema=S)
