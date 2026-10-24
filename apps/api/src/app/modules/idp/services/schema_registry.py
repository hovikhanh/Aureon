"""Extraction-schema registry (04 §5, ENT-DocumentType / ExtractionSchema / ValidationRule).

The DB is the source of truth (T-634): `schema_for_code` returns the doc type's
`current_schema_id` (the published schema Admin last published, EP-DC-32). The hard-coded
INVOICE / OTHER dicts below and `catalog.SEED_TYPES` (#2/#3/#4, migration 0019) are only seed
data — `_ensure` creates a missing seed type idempotently so the pipeline runs on a fresh DB.

`FIELD_DEFS` encode the 04 §5 field result contract: `name`, `value_type`, `required`,
`is_critical` (trường trọng yếu — always reviewed, §7.3), `sensitivity_level`. `RULE_DEFS`
encode the §5.3 validation rules the validator evaluates (T-405).
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.idp.models import DocumentType, ExtractionSchema, ValidationRule
from app.modules.idp.services.catalog import SEED_TYPES

# ---- INVOICE (04 §5.5) — the pipeline's reference doc type -------------------------------
INVOICE_FIELDS: list[dict[str, Any]] = [
    {"name": "invoice_number", "value_type": "text", "required": True, "is_critical": False,
     "sensitivity_level": 2},
    {"name": "issue_date", "value_type": "date", "required": True, "is_critical": False,
     "sensitivity_level": 2},
    {"name": "seller_name", "value_type": "org_name", "required": True, "is_critical": False,
     "sensitivity_level": 2},
    {"name": "seller_tax_code", "value_type": "tax_code", "required": True, "is_critical": False,
     "sensitivity_level": 2},
    {"name": "subtotal", "value_type": "money", "required": True, "is_critical": True,
     "sensitivity_level": 2},
    {"name": "vat_rate_pct", "value_type": "percent", "required": True, "is_critical": False,
     "sensitivity_level": 2},
    {"name": "vat_amount", "value_type": "money", "required": True, "is_critical": True,
     "sensitivity_level": 2},
    {"name": "total_amount", "value_type": "money", "required": True, "is_critical": True,
     "sensitivity_level": 2},
]  # fmt: skip

# §5.3 validation rules — evaluated by the validator (T-405).
INVOICE_RULES: list[dict[str, Any]] = [
    {"code": "VR-INV-02", "kind": "field", "severity": "fail",
     "expression": {"field": "issue_date", "op": "date_not_future"}},
    {"code": "VR-INV-03", "kind": "field", "severity": "fail",
     "expression": {"field": "vat_rate_pct", "op": "in", "values": [0, 5, 8, 10]}},
    {"code": "VR-INV-SUB", "kind": "field", "severity": "fail",
     "expression": {"field": "subtotal", "op": "gt", "value": 0}},
    {"code": "VR-INV-05", "kind": "cross_field", "severity": "fail",
     "expression": {"op": "sum_equals", "target": "total_amount",
                    "addends": ["subtotal", "vat_amount"], "tolerance": 1000}},
]  # fmt: skip

_OTHER_FIELDS: list[dict[str, Any]] = [
    {"name": "title", "value_type": "text", "required": False, "is_critical": False,
     "sensitivity_level": 2},
]  # fmt: skip

_THRESHOLDS = {"classification_confidence_min": 0.95, "required_field_min": 0.90}


async def _ensure(
    db: AsyncSession,
    *,
    code: str,
    name_vi: str,
    name_en: str,
    pillars: list[str],
    sensitivity: int,
    fields: list[dict[str, Any]],
    rules: list[dict[str, Any]],
    action_names: list[str] | None = None,
    keywords: list[str] | None = None,
) -> uuid.UUID:
    action_names = action_names or []
    dt = (
        await db.execute(select(DocumentType).where(DocumentType.code == code))
    ).scalar_one_or_none()
    if dt is None:
        dt = DocumentType(
            code=code,
            name_vi=name_vi,
            name_en=name_en,
            pillars=pillars,
            sensitivity_level=sensitivity,
            retention_years=10,
            is_active=True,
            classifier_keywords=keywords or [],
            data_classification="INTERNAL",
        )
        db.add(dt)
        await db.flush()

    schema = (
        await db.execute(
            select(ExtractionSchema).where(
                ExtractionSchema.document_type_id == dt.id,
                ExtractionSchema.schema_version == 1,
            )
        )
    ).scalar_one_or_none()
    if dt.current_schema_id is not None:  # Admin-managed from here on (DB = source of truth)
        return dt.current_schema_id
    if schema is None:
        schema = ExtractionSchema(
            document_type_id=dt.id,
            schema_version=1,
            fields=fields,
            thresholds=_THRESHOLDS,
            action_names=action_names,
            status="published",
            data_classification="INTERNAL",
        )
        db.add(schema)
        await db.flush()
        dt.current_schema_id = schema.id
        for r in rules:
            db.add(
                ValidationRule(
                    extraction_schema_id=schema.id,
                    code=r["code"],
                    kind=r["kind"],
                    expression=r["expression"],
                    severity=r["severity"],
                    data_classification="INTERNAL",
                )
            )
        await db.flush()
    return schema.id


async def ensure_invoice_schema(db: AsyncSession) -> uuid.UUID:
    return await _ensure(
        db,
        code="INVOICE",
        name_vi="Hóa đơn GTGT",
        name_en="Invoice",
        pillars=["F"],
        sensitivity=2,
        fields=INVOICE_FIELDS,
        rules=INVOICE_RULES,
        action_names=["ACT-create_invoice"],
    )


async def ensure_other_schema(db: AsyncSession) -> uuid.UUID:
    return await _ensure(
        db,
        code="OTHER",
        name_vi="Khác",
        name_en="Other",
        pillars=[],
        sensitivity=2,
        fields=_OTHER_FIELDS,
        rules=[],
    )


async def default_schema_id(db: AsyncSession) -> uuid.UUID:
    """Schema assigned to a freshly uploaded document before classification picks the real one."""
    return await ensure_other_schema(db)


async def ensure_seed_type(db: AsyncSession, code: str) -> uuid.UUID | None:
    seed = next((t for t in SEED_TYPES if t["code"] == code), None)
    if seed is None:
        return None
    return await _ensure(
        db, code=code, name_vi=seed["name_vi"], name_en=seed["name_en"], pillars=seed["pillars"],
        sensitivity=seed["sensitivity_level"], fields=seed["fields"], rules=seed["rules"],
        action_names=seed["action_names"], keywords=seed["classifier_keywords"],
    )  # fmt: skip


async def schema_for_code(db: AsyncSession, code: str) -> uuid.UUID:
    """Current published schema of doc type `code` (DB); unknown/unpublished → OTHER."""
    current = (
        await db.execute(
            select(DocumentType.current_schema_id).where(
                DocumentType.code == code, DocumentType.is_active.is_(True)
            )
        )
    ).scalar_one_or_none()
    if current is not None:
        return current
    if code == "INVOICE":
        return await ensure_invoice_schema(db)
    return await ensure_seed_type(db, code) or await ensure_other_schema(db)
