"""M1.4 T-626: Strategy + StrategicObjective (05 §2.6, R-DEC-50).

Revision ID: 0016_goals_strategy_m14
Revises: 0015_workflow_approvals_m13
Create Date: 2026-10-24

- enum `execution.strategy_status` (`draft, active, closed`);
- `execution.strategies` (BusinessModel, partial UQ live `code`, CHECK `period_end > period_start`);
- `execution.strategic_objectives` (BusinessModel, FK `strategy_id`, partial UQ live `code`,
  index `(strategy_id, sort_order)`, CHECK `weight_pct` 0..100);
- `strategic_objective_id` FK NULL on `objectives`, `kpis`, `initiatives` (+ index); CHECK root
  only on objectives (`parent_id`) and kpis (`parent_kpi_id`); `kpis.pillar` (`platform.pillar`);
  `initiatives.objective_id` DROP NOT NULL.
- Backfill: per tenant and year of a live root `level=company` Objective with a yearly
  `period_key` (`YYYY`) → one Strategy `STR-<year>` (`active`, `[YYYY-01-01, YYYY+1-01-01)`,
  owner = earliest such objective's owner) + one StrategicObjective per such Objective
  (`SO-<year>-<nn>` in `created_at` order, title/pillar/owner/department/weight/status copied);
  the Objective gets `strategic_objective_id`; its Initiatives get the same SO; SO
  `progress_pct` = weighted mean of the linked live initiatives (all weights 0 → plain mean),
  else the Objective's `progress_pct` (05 §2.6 rule).

Reversible: downgrade drops columns/tables/enum (backfilled rows go with them). Restoring
`initiatives.objective_id NOT NULL` raises when an initiative without objective exists.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0016_goals_strategy_m14"
down_revision: str | None = "0015_workflow_approvals_m13"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

DEFAULT_TENANT_ID = "00000000-0000-0000-0000-000000000001"
S = "execution"
STR, SO = "strategies", "strategic_objectives"
LINKED = ("objectives", "kpis", "initiatives")


def _enum(name: str, schema: str = "platform") -> postgresql.ENUM:
    return postgresql.ENUM(name=name, create_type=False, schema=schema)


def _ts(name: str, *, nullable: bool = False) -> sa.Column[sa.DateTime]:
    default = None if nullable else sa.text("now()")
    return sa.Column(name, sa.DateTime(timezone=True), server_default=default, nullable=nullable)


def _business_columns() -> list[sa.Column[object]]:
    """C3/C4/C19 + tenant + soft delete + actor (05 §2.1 group 1)."""
    return [
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column(
            "tenant_id", sa.UUID(), server_default=sa.text(f"'{DEFAULT_TENANT_ID}'"), nullable=False
        ),
        _ts("created_at"),
        _ts("updated_at"),
        _ts("deleted_at", nullable=True),
        sa.Column("created_by", sa.UUID(), nullable=True),
        sa.Column("updated_by", sa.UUID(), nullable=True),
        sa.Column("source", _enum("record_source"), nullable=False),
        sa.Column(
            "data_classification",
            _enum("data_classification"),
            server_default="INTERNAL",
            nullable=False,
        ),
        sa.Column("version", sa.Integer(), server_default=sa.text("1"), nullable=False),
    ]


def _tables_upgrade() -> None:
    postgresql.ENUM("draft", "active", "closed", name="strategy_status", schema=S).create(
        op.get_bind(), checkfirst=True
    )
    op.create_table(
        STR,
        sa.Column("code", sa.Text(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("vision", sa.Text(), nullable=True),
        sa.Column("mission", sa.Text(), nullable=True),
        sa.Column("period_start", sa.Date(), nullable=False),
        sa.Column("period_end", sa.Date(), nullable=False),
        sa.Column("owner_id", sa.UUID(), nullable=False),
        sa.Column("status", _enum("strategy_status", S), nullable=False),
        *_business_columns(),
        sa.CheckConstraint("period_end > period_start", name=op.f(f"ck_{STR}_period_end_after_start")),
        sa.PrimaryKeyConstraint("id", name=op.f(f"pk_{STR}")),
        schema=S,
    )  # fmt: skip
    for col in ("tenant_id", "owner_id"):
        op.create_index(op.f(f"ix_{STR}_{col}"), STR, [col], schema=S)
    op.create_index(f"uq_{STR}_code_live", STR, ["code"], unique=True,
                    postgresql_where=sa.text("deleted_at IS NULL"), schema=S)  # fmt: skip
    op.create_table(
        SO,
        sa.Column("strategy_id", sa.UUID(), nullable=False),
        sa.Column("code", sa.Text(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("pillar", _enum("pillar"), nullable=True),
        sa.Column("owner_id", sa.UUID(), nullable=False),
        sa.Column("department_id", sa.UUID(), nullable=True),
        sa.Column("weight_pct", sa.Numeric(7, 4), nullable=False),
        sa.Column("sort_order", sa.Integer(), server_default="0", nullable=False),
        sa.Column("status", _enum("okr_status", S), nullable=False),
        sa.Column("progress_pct", sa.Numeric(7, 4), nullable=False),
        *_business_columns(),
        sa.CheckConstraint("weight_pct BETWEEN 0 AND 100", name=op.f(f"ck_{SO}_weight_pct_0_100")),
        sa.ForeignKeyConstraint(["strategy_id"], [f"{S}.{STR}.id"],
                                name=op.f(f"fk_{SO}_strategy_id_{STR}"), ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id", name=op.f(f"pk_{SO}")),
        schema=S,
    )  # fmt: skip
    for col in ("tenant_id", "strategy_id", "owner_id", "department_id"):
        op.create_index(op.f(f"ix_{SO}_{col}"), SO, [col], schema=S)
    op.create_index(f"ix_{SO}_strategy_id_sort_order", SO, ["strategy_id", "sort_order"], schema=S)
    op.create_index(f"uq_{SO}_code_live", SO, ["code"], unique=True,
                    postgresql_where=sa.text("deleted_at IS NULL"), schema=S)  # fmt: skip


def _links_upgrade() -> None:
    for t in LINKED:
        op.add_column(t, sa.Column("strategic_objective_id", sa.UUID(), nullable=True), schema=S)
        op.create_foreign_key(
            op.f(f"fk_{t}_strategic_objective_id_{SO}"), t, SO, ["strategic_objective_id"],
            ["id"], source_schema=S, referent_schema=S, ondelete="RESTRICT",
        )  # fmt: skip
        op.create_index(op.f(f"ix_{t}_strategic_objective_id"), t, ["strategic_objective_id"],
                        schema=S)  # fmt: skip
    op.create_check_constraint(
        op.f("ck_objectives_so_root_only"), "objectives",
        "parent_id IS NULL OR strategic_objective_id IS NULL", schema=S,
    )  # fmt: skip
    op.create_check_constraint(
        op.f("ck_kpis_so_root_only"), "kpis",
        "parent_kpi_id IS NULL OR strategic_objective_id IS NULL", schema=S,
    )  # fmt: skip
    op.add_column("kpis", sa.Column("pillar", _enum("pillar"), nullable=True), schema=S)
    op.alter_column("initiatives", "objective_id", nullable=True, schema=S)


# Roots = live root yearly `level=company` objectives — the strategic layer of v2.1 data.
BACKFILL_STRATEGIES = """
INSERT INTO execution.strategies (tenant_id, code, name, period_start, period_end, owner_id,
    status, source, data_classification)
SELECT DISTINCT ON (r.tenant_id, r.period_key) r.tenant_id, 'STR-' || r.period_key, r.title,
    make_date(r.period_key::int, 1, 1), make_date(r.period_key::int + 1, 1, 1), r.owner_id,
    'active'::execution.strategy_status, r.source, r.data_classification
FROM (SELECT o.* FROM execution.objectives o WHERE o.deleted_at IS NULL AND o.parent_id IS NULL
      AND o.level = 'company' AND o.period_key ~ '^[0-9]{4}$') r
WHERE NOT EXISTS (SELECT 1 FROM execution.strategies s
                  WHERE s.code = 'STR-' || r.period_key AND s.deleted_at IS NULL)
ORDER BY r.tenant_id, r.period_key, r.created_at, r.id
"""
BACKFILL_SOS = """
WITH src AS (
    SELECT r.*, s.id AS strategy_id, gen_random_uuid() AS so_id,
           row_number() OVER (PARTITION BY r.tenant_id, r.period_key
                              ORDER BY r.created_at, r.id) AS n
    FROM (SELECT o.* FROM execution.objectives o WHERE o.deleted_at IS NULL AND o.parent_id IS NULL
      AND o.level = 'company' AND o.period_key ~ '^[0-9]{4}$') r
    JOIN execution.strategies s
      ON s.tenant_id = r.tenant_id AND s.code = 'STR-' || r.period_key AND s.deleted_at IS NULL
    WHERE r.strategic_objective_id IS NULL
), ins AS (
    INSERT INTO execution.strategic_objectives (id, tenant_id, strategy_id, code, title,
        pillar, owner_id, department_id, weight_pct, sort_order, status, progress_pct, source,
        data_classification)
    SELECT so_id, tenant_id, strategy_id, 'SO-' || period_key || '-' || lpad(n::text, 2, '0'),
           title, pillar, owner_id, department_id, weight_pct, n - 1, status, progress_pct,
           source, data_classification
    FROM src
    RETURNING id
)
UPDATE execution.objectives o SET strategic_objective_id = src.so_id
FROM src WHERE o.id = src.id
"""
# Initiatives inherit the SO of the root of their objective's tree.
BACKFILL_INITIATIVES = """
WITH RECURSIVE up AS (
    SELECT o.id AS objective_id, o.id AS cur, o.parent_id, o.strategic_objective_id
    FROM execution.objectives o
    UNION ALL
    SELECT up.objective_id, p.id, p.parent_id, p.strategic_objective_id
    FROM up JOIN execution.objectives p ON p.id = up.parent_id
    WHERE up.strategic_objective_id IS NULL
)
UPDATE execution.initiatives i SET strategic_objective_id = up.strategic_objective_id
FROM up
WHERE up.objective_id = i.objective_id AND up.strategic_objective_id IS NOT NULL
  AND i.strategic_objective_id IS NULL
"""
BACKFILL_PROGRESS = """
UPDATE execution.strategic_objectives so SET progress_pct = round(agg.p, 4)
FROM (
    SELECT i.strategic_objective_id AS so_id,
           CASE WHEN sum(i.weight_pct) > 0
                THEN sum(i.progress_pct * i.weight_pct) / sum(i.weight_pct)
                ELSE avg(i.progress_pct) END AS p
    FROM execution.initiatives i
    WHERE i.deleted_at IS NULL AND i.strategic_objective_id IS NOT NULL
    GROUP BY i.strategic_objective_id
) agg
WHERE so.id = agg.so_id
"""


def upgrade() -> None:
    _tables_upgrade()
    _links_upgrade()
    for sql in (BACKFILL_STRATEGIES, BACKFILL_SOS, BACKFILL_INITIATIVES, BACKFILL_PROGRESS):
        op.execute(sql)


def downgrade() -> None:
    orphan = op.get_bind().execute(
        sa.text("SELECT count(*) FROM execution.initiatives WHERE objective_id IS NULL")
    )
    if orphan.scalar_one():
        raise RuntimeError(
            "0016 downgrade: initiatives without objective_id exist — link them to an Objective "
            "(or delete them) before restoring NOT NULL"
        )
    op.alter_column("initiatives", "objective_id", nullable=False, schema=S)
    op.drop_column("kpis", "pillar", schema=S)
    op.drop_constraint(op.f("ck_kpis_so_root_only"), "kpis", type_="check", schema=S)
    op.drop_constraint(op.f("ck_objectives_so_root_only"), "objectives", type_="check", schema=S)
    for t in LINKED:
        op.drop_index(op.f(f"ix_{t}_strategic_objective_id"), table_name=t, schema=S)
        op.drop_constraint(
            op.f(f"fk_{t}_strategic_objective_id_{SO}"), t, type_="foreignkey", schema=S
        )
        op.drop_column(t, "strategic_objective_id", schema=S)
    op.drop_table(SO, schema=S)
    op.drop_table(STR, schema=S)
    postgresql.ENUM(name="strategy_status", schema=S).drop(op.get_bind(), checkfirst=True)
