"""capture: seed P0 doc types #2 PLAN_KPI_OKR, #3 PERIOD_REPORT, #4 HR_ROSTER (T-634)

Revision ID: 0019_capture_seed_doctypes
Revises: 0018_capture_registry

Config rows (05 §2.7, R-DEC-65): one `document_types` row + `extraction_schemas` v1
`published` + its validation rules per type. The catalog dicts in
`app.modules.idp.services.catalog` are the seed only — Admin edits the DB copy afterwards
(EP-DC-27..35). INVOICE keeps its v1 schema; its `action_names` gets `ACT-create_invoice` when
the row exists (fresh DBs create it lazily via `schema_registry`). Idempotent; downgrade
removes exactly the seeded rows (by code)
that no captured document references.
"""

import json
import uuid
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

from app.modules.idp.services.catalog import SEED_TYPES

revision: str = "0019_capture_seed_doctypes"
down_revision: str | None = "0018_capture_registry"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_CODES = tuple(t["code"] for t in SEED_TYPES)


def upgrade() -> None:
    conn = op.get_bind()
    for t in SEED_TYPES:
        if conn.execute(sa.text("SELECT 1 FROM idp.document_types WHERE code = :c"),
                        {"c": t["code"]}).first():  # fmt: skip
            continue
        dt_id, schema_id = uuid.uuid4(), uuid.uuid4()
        conn.execute(sa.text(
            "INSERT INTO idp.document_types (id, code, name_vi, name_en, pillars, "
            "sensitivity_level, retention_years, is_active, classifier_keywords, "
            "data_classification) VALUES (:id, :code, :vi, :en, "
            "CAST(:pillars AS platform.pillar[]), :lvl, :ret, true, :kw, 'INTERNAL')"
        ), {"id": dt_id, "code": t["code"], "vi": t["name_vi"], "en": t["name_en"],
            "pillars": "{" + ",".join(t["pillars"]) + "}", "lvl": t["sensitivity_level"],
            "ret": t["retention_years"], "kw": t["classifier_keywords"]})  # fmt: skip
        conn.execute(sa.text(
            "INSERT INTO idp.extraction_schemas (id, document_type_id, schema_version, fields, "
            "thresholds, action_names, status, published_at, data_classification) VALUES "
            "(:id, :dt, 1, CAST(:fields AS jsonb), CAST(:th AS jsonb), :acts, 'published', "
            "now(), 'INTERNAL')"
        ), {"id": schema_id, "dt": dt_id, "fields": json.dumps(t["fields"], ensure_ascii=False),
            "th": json.dumps(t["thresholds"]), "acts": t["action_names"]})  # fmt: skip
        conn.execute(sa.text("UPDATE idp.document_types SET current_schema_id = :s WHERE id = :d"),
                     {"s": schema_id, "d": dt_id})  # fmt: skip
        for r in t["rules"]:
            conn.execute(sa.text(
                "INSERT INTO idp.validation_rules (id, extraction_schema_id, code, kind, "
                "expression, severity, is_active, data_classification) VALUES (:id, :s, :code, "
                "CAST(:kind AS idp.rule_kind), CAST(:ex AS jsonb), "
                "CAST(:sev AS idp.rule_severity), true, 'INTERNAL')"
            ), {"id": uuid.uuid4(), "s": schema_id, "code": r["code"], "kind": r["kind"],
                "ex": json.dumps(r["expression"]), "sev": r["severity"]})  # fmt: skip
    conn.execute(sa.text(
        "UPDATE idp.extraction_schemas s SET action_names = ARRAY['ACT-create_invoice'] "
        "FROM idp.document_types d WHERE s.document_type_id = d.id AND d.code = 'INVOICE' "
        "AND cardinality(s.action_names) = 0"
    ))  # fmt: skip


# Types still referenced by captured documents/jobs/batches are kept (deleting them would
# delete user data); the upgrade skips an existing code, so down → up stays consistent.
_IN_USE = (
    "SELECT d.code FROM idp.document_types d WHERE d.code = ANY(:codes) AND ("
    "EXISTS (SELECT 1 FROM idp.source_documents x WHERE x.document_type_id = d.id) OR "
    "EXISTS (SELECT 1 FROM idp.import_batches x WHERE x.document_type_id = d.id) OR "
    "EXISTS (SELECT 1 FROM idp.extraction_jobs j JOIN idp.extraction_schemas s "
    "ON j.extraction_schema_id = s.id WHERE s.document_type_id = d.id))"
)
_DOWN = (
    "UPDATE idp.document_types SET current_schema_id = NULL WHERE code = ANY(:codes)",
    "DELETE FROM idp.validation_rules r USING idp.extraction_schemas s, idp.document_types d "
    "WHERE r.extraction_schema_id = s.id AND s.document_type_id = d.id AND d.code = ANY(:codes)",
    "DELETE FROM idp.extraction_schemas s USING idp.document_types d "
    "WHERE s.document_type_id = d.id AND d.code = ANY(:codes)",
    "DELETE FROM idp.document_types WHERE code = ANY(:codes)",
)


def downgrade() -> None:
    conn = op.get_bind()
    in_use = {r[0] for r in conn.execute(sa.text(_IN_USE), {"codes": list(_CODES)})}
    codes = [c for c in _CODES if c not in in_use]
    for stmt in _DOWN:  # constant SQL; codes are bound parameters
        conn.execute(sa.text(stmt), {"codes": codes})
