"""M1.4 T-627: KPI target effective-dated, measurement history, KPIEvaluation, KRMeasurement.

Revision ID: 0017_goals_measure_m14
Revises: 0016_goals_strategy_m14
Create Date: 2026-10-24

05 §2.6 / R-DEC-51..53:
- `kpi_targets.valid_from` (backfill = first day of `period_key`), `valid_to`, `reason`; partial
  UQ `(kpi_id, period_key)` now `WHERE deleted_at IS NULL AND valid_to IS NULL`.
- `kpi_measurements`: `tenant_id`, `measured_by`, `data_source` (default `manual`), `note`,
  `check_in_id` FK; UQ `(kpi_id, period_key)` dropped → index `(kpi_id, period_key, measured_at
  DESC)` (one row per measurement).
- `check_ins.tenant_id` (backfill = system tenant).
- `kpi_evaluations` (business, partial UQ live `(kpi_id, period_key)`) backfilled from the latest
  measurement of each KPI × period (`gap_value` by direction, `measured_on_time` with the default
  grace of 5 days, `previous_band` NULL).
- `kr_measurements` (append-only + tenant) backfilled from KR check-ins (`checked_in_at` order,
  progress from current baseline/target, `previous_progress_pct` = previous row).
- `key_results.at_risk`, `at_risk_since`, `at_risk_reasons`, `last_checked_in_at` (backfill
  `max(checked_in_at)`).

Downgrade drops the new tables/columns. Restoring UQ `kpi_measurements (kpi_id, period_key)`
keeps only the latest measurement of each KPI × period (**measurement history is lost**);
closed target versions (`valid_to` NOT NULL) are deleted after their measurements are re-pointed
to the current version of the period (old partial UQ allows one live target per period).
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0017_goals_measure_m14"
down_revision: str | None = "0016_goals_strategy_m14"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

DEFAULT_TENANT_ID = "00000000-0000-0000-0000-000000000001"
S = "execution"
EV, KRM = "kpi_evaluations", "kr_measurements"


def _enum(name: str, schema: str = "platform") -> postgresql.ENUM:
    return postgresql.ENUM(name=name, schema=schema, create_type=False)


def _ts(name: str, *, nullable: bool = False) -> sa.Column[object]:
    default = None if nullable else sa.text("now()")
    return sa.Column(name, sa.DateTime(timezone=True), server_default=default, nullable=nullable)


def _tenant() -> sa.Column[object]:
    return sa.Column(
        "tenant_id", sa.UUID(), server_default=sa.text(f"'{DEFAULT_TENANT_ID}'"), nullable=False
    )


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


def _fk(table: str, col: str, ref: str) -> sa.ForeignKeyConstraint:
    return sa.ForeignKeyConstraint(
        [col], [f"execution.{ref}.id"], name=op.f(f"fk_{table}_{col}_{ref}"), ondelete="RESTRICT"
    )


def _targets_upgrade() -> None:
    op.add_column("kpi_targets", sa.Column("valid_from", sa.Date(), nullable=True), schema=S)
    op.add_column("kpi_targets", sa.Column("valid_to", sa.Date(), nullable=True), schema=S)
    op.add_column("kpi_targets", sa.Column("reason", sa.Text(), nullable=True), schema=S)
    op.execute(BACKFILL_VALID_FROM)
    op.alter_column("kpi_targets", "valid_from", nullable=False, schema=S)
    op.drop_index("uq_kpi_targets_kpi_id_period_key", table_name="kpi_targets", schema=S)
    op.create_index("uq_kpi_targets_kpi_id_period_key", "kpi_targets", ["kpi_id", "period_key"],
                    unique=True, schema=S,
                    postgresql_where=sa.text("deleted_at IS NULL AND valid_to IS NULL"))  # fmt: skip


def _logs_upgrade() -> None:
    for t in ("check_ins", "kpi_measurements"):
        op.add_column(t, _tenant(), schema=S)
        op.create_index(op.f(f"ix_{t}_tenant_id"), t, ["tenant_id"], schema=S)
    m = "kpi_measurements"
    op.add_column(m, sa.Column("measured_by", sa.UUID(), nullable=True), schema=S)
    op.add_column(m, sa.Column("data_source", _enum("kpi_data_source", S),
                               server_default="manual", nullable=False), schema=S)  # fmt: skip
    op.add_column(m, sa.Column("note", sa.Text(), nullable=True), schema=S)
    op.add_column(m, sa.Column("check_in_id", sa.UUID(), nullable=True), schema=S)
    op.create_foreign_key(op.f(f"fk_{m}_check_in_id_check_ins"), m, "check_ins", ["check_in_id"],
                          ["id"], source_schema=S, referent_schema=S, ondelete="RESTRICT")  # fmt: skip
    op.create_index(op.f(f"ix_{m}_check_in_id"), m, ["check_in_id"], schema=S)
    op.drop_constraint("uq_kpi_measurements_kpi_id_period_key", m, type_="unique", schema=S)
    op.create_index("ix_kpi_measurements_kpi_id_period_key_measured_at", m,
                    ["kpi_id", "period_key", sa.text("measured_at DESC")], schema=S)  # fmt: skip
    k = "key_results"
    op.add_column(k, sa.Column("at_risk", sa.Boolean(), server_default=sa.text("false"),
                               nullable=False), schema=S)  # fmt: skip
    op.add_column(k, sa.Column("at_risk_since", sa.DateTime(timezone=True), nullable=True),
                  schema=S)  # fmt: skip
    op.add_column(k, sa.Column("at_risk_reasons", postgresql.ARRAY(sa.Text()),
                               server_default=sa.text("'{}'"), nullable=False), schema=S)  # fmt: skip
    op.add_column(k, sa.Column("last_checked_in_at", sa.DateTime(timezone=True), nullable=True),
                  schema=S)  # fmt: skip


def _tables_upgrade() -> None:
    op.create_table(
        EV,
        sa.Column("kpi_id", sa.UUID(), nullable=False),
        sa.Column("period_key", sa.Text(), nullable=False),
        sa.Column("kpi_target_id", sa.UUID(), nullable=False),
        sa.Column("measurement_id", sa.UUID(), nullable=False),
        sa.Column("actual_value", sa.Numeric(20, 6), nullable=False),
        sa.Column("target", sa.Numeric(20, 6), nullable=False),
        sa.Column("achievement_pct", sa.Numeric(7, 4), nullable=False),
        sa.Column("band", _enum("kpi_band", S), nullable=False),
        sa.Column("previous_band", _enum("kpi_band", S), nullable=True),
        sa.Column("gap_value", sa.Numeric(20, 6), nullable=False),
        sa.Column("measured_on_time", sa.Boolean(), nullable=False),
        sa.Column("evaluated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("locked_at", sa.DateTime(timezone=True), nullable=True),
        *_business_columns(),
        _fk(EV, "kpi_id", "kpis"),
        _fk(EV, "kpi_target_id", "kpi_targets"),
        _fk(EV, "measurement_id", "kpi_measurements"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_kpi_evaluations")),
        schema=S,
    )
    for col in ("tenant_id", "kpi_id", "kpi_target_id", "measurement_id"):
        op.create_index(op.f(f"ix_kpi_evaluations_{col}"), EV, [col], schema=S)
    op.create_index("uq_kpi_evaluations_kpi_id_period_key", EV, ["kpi_id", "period_key"], unique=True,
                    postgresql_where=sa.text("deleted_at IS NULL"), schema=S)  # fmt: skip
    op.create_table(
        KRM,
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        _ts("created_at"),
        _ts("updated_at"),
        _tenant(),
        sa.Column("key_result_id", sa.UUID(), nullable=False),
        sa.Column("check_in_id", sa.UUID(), nullable=True),
        sa.Column("period_key", sa.Text(), nullable=False),
        sa.Column("value", sa.Numeric(20, 6), nullable=False),
        sa.Column("progress_pct", sa.Numeric(7, 4), nullable=False),
        sa.Column("previous_progress_pct", sa.Numeric(7, 4), nullable=True),
        sa.Column("confidence", _enum("confidence_band"), nullable=False),
        sa.Column("measured_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("measured_by", sa.UUID(), nullable=True),
        _fk(KRM, "key_result_id", "key_results"),
        _fk(KRM, "check_in_id", "check_ins"),
        sa.UniqueConstraint("check_in_id", name=op.f("uq_kr_measurements_check_in_id")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_kr_measurements")),
        schema=S,
    )
    for col in ("tenant_id", "key_result_id"):
        op.create_index(op.f(f"ix_kr_measurements_{col}"), KRM, [col], schema=S)
    op.create_index("ix_kr_measurements_key_result_id_measured_at", KRM,
                    ["key_result_id", sa.text("measured_at DESC")], schema=S)  # fmt: skip


BACKFILL_EVALUATIONS = """
INSERT INTO execution.kpi_evaluations (tenant_id, kpi_id, period_key, kpi_target_id, measurement_id, actual_value,
    target, achievement_pct, band, previous_band, gap_value, measured_on_time, evaluated_at,
    locked_at, source, data_classification)
SELECT k.tenant_id, m.kpi_id, m.period_key, m.kpi_target_id, m.id, m.actual_value, t.target,
    m.achievement_pct, m.evaluation_band, NULL,
    CASE k.direction
        WHEN 'LOWER_IS_BETTER' THEN m.actual_value - t.target
        WHEN 'WITHIN_RANGE' THEN CASE
            WHEN m.actual_value < coalesce(t.minimum, t.target)
                THEN coalesce(t.minimum, t.target) - m.actual_value
            WHEN m.actual_value > t.target THEN m.actual_value - t.target
            ELSE 0 END
        ELSE t.target - m.actual_value END,
    (m.measured_at AT TIME ZONE 'Asia/Ho_Chi_Minh')::date
        < CASE
              WHEN m.period_key ~ '^[0-9]{4}$' THEN make_date(m.period_key::int + 1, 1, 1)
              WHEN m.period_key ~ '^[0-9]{4}-Q[1-4]$'
                  THEN (make_date(left(m.period_key, 4)::int, 3 * right(m.period_key, 1)::int - 2, 1)
                        + interval '3 months')::date
              ELSE (make_date(left(m.period_key, 4)::int, substr(m.period_key, 6, 2)::int, 1)
                    + interval '1 month')::date END + 5,
    m.measured_at, m.locked_at, k.source, k.data_classification
FROM (SELECT DISTINCT ON (kpi_id, period_key) * FROM execution.kpi_measurements
      ORDER BY kpi_id, period_key, measured_at DESC, id DESC) m
JOIN execution.kpis k ON k.id = m.kpi_id
JOIN execution.kpi_targets t ON t.id = m.kpi_target_id
"""
BACKFILL_KR_MEASUREMENTS = """
INSERT INTO execution.kr_measurements (tenant_id, key_result_id, check_in_id, period_key, value, progress_pct,
    previous_progress_pct, confidence, measured_at, measured_by)
SELECT tenant_id, key_result_id, id, period_key, value, p,
       lag(p) OVER (PARTITION BY key_result_id ORDER BY checked_in_at, id),
       confidence, checked_in_at, user_id
FROM (SELECT c.*, o.period_key, round(LEAST(GREATEST(CASE
          WHEN kr.target = kr.baseline THEN CASE WHEN c.value = kr.target THEN 100 ELSE 0 END
          ELSE (c.value - kr.baseline) / (kr.target - kr.baseline) * 100 END, 0), 100), 4) AS p
      FROM execution.check_ins c
      JOIN execution.key_results kr ON kr.id = c.key_result_id
      JOIN execution.objectives o ON o.id = kr.objective_id) src
"""
BACKFILL_LAST_CHECKIN = """
UPDATE execution.key_results kr SET last_checked_in_at = agg.at
FROM (SELECT key_result_id, max(checked_in_at) AS at FROM execution.check_ins
      WHERE key_result_id IS NOT NULL GROUP BY key_result_id) agg
WHERE kr.id = agg.key_result_id
"""


BACKFILL_VALID_FROM = """
UPDATE execution.kpi_targets SET valid_from = CASE
    WHEN period_key ~ '^[0-9]{4}$' THEN make_date(period_key::int, 1, 1)
    WHEN period_key ~ '^[0-9]{4}-Q[1-4]$'
        THEN make_date(left(period_key, 4)::int, 3 * right(period_key, 1)::int - 2, 1)
    ELSE make_date(left(period_key, 4)::int, substr(period_key, 6, 2)::int, 1) END
"""


def upgrade() -> None:
    _targets_upgrade()
    _logs_upgrade()
    _tables_upgrade()
    for sql in (BACKFILL_EVALUATIONS, BACKFILL_KR_MEASUREMENTS, BACKFILL_LAST_CHECKIN):
        op.execute(sql)


# downgrade: keep the latest measurement per KPI × period, one target version per period
DOWN_REPOINT = """
UPDATE execution.kpi_measurements m SET kpi_target_id = cur.id
FROM execution.kpi_targets old
JOIN execution.kpi_targets cur ON cur.kpi_id = old.kpi_id AND cur.period_key = old.period_key
    AND cur.valid_to IS NULL AND cur.deleted_at IS NULL
WHERE m.kpi_target_id = old.id AND old.valid_to IS NOT NULL
"""
DOWN_DROP_HISTORY = """
DELETE FROM execution.kpi_measurements m USING (
    SELECT id, row_number() OVER (PARTITION BY kpi_id, period_key
                                  ORDER BY measured_at DESC, id DESC) AS n
    FROM execution.kpi_measurements) r
WHERE m.id = r.id AND r.n > 1
"""
DOWN_DROP_CLOSED_TARGETS = """
DELETE FROM execution.kpi_targets t WHERE t.valid_to IS NOT NULL
  AND NOT EXISTS (SELECT 1 FROM execution.kpi_measurements m WHERE m.kpi_target_id = t.id)
"""


def downgrade() -> None:
    op.drop_table(KRM, schema=S)
    op.drop_table(EV, schema=S)
    for col in ("last_checked_in_at", "at_risk_reasons", "at_risk_since", "at_risk"):
        op.drop_column("key_results", col, schema=S)
    m = "kpi_measurements"
    for sql in (DOWN_REPOINT, DOWN_DROP_HISTORY, DOWN_DROP_CLOSED_TARGETS):
        op.execute(sql)
    op.drop_index("ix_kpi_measurements_kpi_id_period_key_measured_at", table_name=m, schema=S)
    op.create_unique_constraint("uq_kpi_measurements_kpi_id_period_key", m,
                                ["kpi_id", "period_key"], schema=S)  # fmt: skip
    op.drop_index(op.f(f"ix_{m}_check_in_id"), table_name=m, schema=S)
    op.drop_constraint(op.f(f"fk_{m}_check_in_id_check_ins"), m, type_="foreignkey", schema=S)
    for col in ("check_in_id", "note", "data_source", "measured_by"):
        op.drop_column(m, col, schema=S)
    for t in ("check_ins", "kpi_measurements"):
        op.drop_index(op.f(f"ix_{t}_tenant_id"), table_name=t, schema=S)
        op.drop_column(t, "tenant_id", schema=S)
    op.drop_index("uq_kpi_targets_kpi_id_period_key", table_name="kpi_targets", schema=S)
    op.create_index("uq_kpi_targets_kpi_id_period_key", "kpi_targets", ["kpi_id", "period_key"],
                    unique=True, schema=S, postgresql_where=sa.text("deleted_at IS NULL"))  # fmt: skip
    for col in ("reason", "valid_to", "valid_from"):
        op.drop_column("kpi_targets", col, schema=S)
