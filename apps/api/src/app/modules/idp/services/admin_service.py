"""Capture catalog admin — EP-DC-27..35 (10 §7.2.4, US-DC-008, DEC-162, T-634).

Doc types are config (no delete). Extraction schemas: `draft` → `published` (old published →
`retired`, `document_types.current_schema_id` → new) and immutable afterwards. Hard rules on a
draft (422 VALIDATION_ERROR): thresholds below DEC-133, a critical field (money / tax code /
CRITICAL_FIELD_NAMES / level 4) not `is_critical`, unknown `action_names`, or a field `target`
pointing at an ACT param that does not exist. Every write is audited `idp.*` in the caller's
transaction; the route commits.
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import record_audit
from app.core.deps import Principal
from app.core.errors import (
    ConflictStateError,
    DuplicateResourceError,
    NotFoundError,
    ValidationError,
)
from app.modules.idp.models import (
    FIELD_VALUE_TYPE,
    DocumentType,
    ExtractionSchema,
    ValidationRule,
)
from app.modules.idp.schemas.capture import (
    DocumentTypeOut,
    DocumentTypePatch,
    ExtractionSchemaCreate,
    ExtractionSchemaOut,
    ExtractionSchemaPatch,
    ValidationRuleCreate,
    ValidationRuleOut,
    ValidationRulePatch,
)
from app.modules.idp.services.actions import get_action

MIN_CLASSIFICATION, MIN_REQUIRED_FIELD = 0.95, 0.90  # DEC-133 — may only be raised
CRITICAL_VALUE_TYPES = frozenset({"money", "tax_code"})
# FR-DC-16 trường trọng yếu: số tiền, số tài khoản, MST, lương, giá trị hợp đồng (+ CCCD).
CRITICAL_FIELD_NAMES = frozenset({
    "amount", "subtotal", "vat_amount", "total_amount", "bank_account", "tax_code",
    "seller_tax_code", "buyer_tax_code", "salary", "contract_value", "national_id",
})  # fmt: skip
VALUE_TYPES = frozenset(FIELD_VALUE_TYPE.enums)  # idp.field_value_type (05 §2.7)
# Validator ops (validator.py) — anything else is rejected on EP-DC-34.
VALIDATOR_OPS = frozenset({"required", "date_not_future", "in", "gt", "gte", "lt", "lte",
                           "sum_equals"})  # fmt: skip


def _bad(message: str, **details: Any) -> ValidationError:
    return ValidationError(message, details=details)


def check_schema_body(fields: list[dict[str, Any]], thresholds: dict[str, Any],
                      action_names: list[str]) -> None:  # fmt: skip
    """The EP-DC-31 hard rules (also applied on create / publish)."""
    if thresholds.get("classification_confidence_min", 0) < MIN_CLASSIFICATION:
        raise _bad("threshold below DEC-133", field="thresholds.classification_confidence_min")
    if thresholds.get("required_field_min", 0) < MIN_REQUIRED_FIELD:
        raise _bad("threshold below DEC-133", field="thresholds.required_field_min")
    unknown = [n for n in action_names if get_action(n) is None]
    if unknown:
        raise _bad("unknown action", field="action_names", unknown=unknown)
    for f in fields:
        if f["value_type"] not in VALUE_TYPES:
            raise _bad("unknown value_type", field=f["name"], value_type=f["value_type"])
        level4_money = f.get("sensitivity_level") == 4 and f["value_type"] == "money"
        critical = (f["value_type"] in CRITICAL_VALUE_TYPES
                    or f["name"] in CRITICAL_FIELD_NAMES or level4_money)  # fmt: skip
        if critical and not f.get("is_critical"):
            raise _bad("critical field must stay is_critical", field=f["name"], reason="FR-DC-16")
        target = f.get("target")
        if target:
            act = get_action(target["action"])
            if act is None or target["action"] not in action_names:
                raise _bad("target action not in action_names", field=f["name"])
            if target["param"] not in act.params_model.model_fields:
                raise _bad("target param does not exist", field=f["name"],
                           action=target["action"], param=target["param"])  # fmt: skip


def schema_out(s: ExtractionSchema, code: str) -> ExtractionSchemaOut:
    return ExtractionSchemaOut(
        id=s.id, document_type=code, schema_version=s.schema_version, status=s.status,
        fields=s.fields, thresholds=s.thresholds, action_names=list(s.action_names),
        published_at=s.published_at, version=s.version,
    )  # fmt: skip


def rule_out(r: ValidationRule) -> ValidationRuleOut:
    return ValidationRuleOut(
        id=r.id, extraction_schema_id=r.extraction_schema_id, code=r.code, kind=r.kind,
        expression=r.expression, severity=r.severity,
        tolerance=float(r.tolerance) if r.tolerance is not None else None,
        is_active=r.is_active, version=r.version,
    )  # fmt: skip


def _check_version(obj: Any, expected: int, what: str) -> None:
    if obj.version != expected:
        details = {"version": obj.version, "expected": expected}
        raise ConflictStateError(f"{what} was modified", details=details)


class CaptureAdminService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ---------- EP-DC-27/28 ----------
    async def list_types(self, user: Principal, *, include_inactive: bool) -> list[DocumentTypeOut]:
        stmt = select(DocumentType, ExtractionSchema.schema_version).outerjoin(
            ExtractionSchema, ExtractionSchema.id == DocumentType.current_schema_id
        ).order_by(DocumentType.code)  # fmt: skip
        if not (include_inactive and user.has("idp:admin")):
            stmt = stmt.where(DocumentType.is_active.is_(True))
        rows = (await self.db.execute(stmt)).all()
        return [self._type_out(dt, v) for dt, v in rows]

    async def patch_type(self, user: Principal, id_: uuid.UUID,
                         body: DocumentTypePatch) -> DocumentTypeOut:  # fmt: skip
        dt = await self._get(DocumentType, id_, "document type")
        _check_version(dt, body.version, "document type")
        before = self._type_out(dt, None).model_dump(mode="json")
        for k, v in body.model_dump(exclude_unset=True, exclude={"version"}).items():
            setattr(dt, k, v)
        dt.version += 1
        dt.updated_by = user.user_id
        await self.db.flush()
        ver = await self._schema_version(dt.current_schema_id)
        out = self._type_out(dt, ver)
        await record_audit(self.db, action="idp.doctype_update", target_schema="idp",
                           target_table="document_types", target_id=dt.id, before=before,
                           after=out.model_dump(mode="json"))  # fmt: skip
        return out

    # ---------- EP-DC-29..32 ----------
    async def list_schemas(self, *, document_type: str | None,
                           status: str | None) -> list[ExtractionSchemaOut]:  # fmt: skip
        stmt = select(ExtractionSchema, DocumentType.code).join(
            DocumentType, DocumentType.id == ExtractionSchema.document_type_id
        ).order_by(DocumentType.code, ExtractionSchema.schema_version)  # fmt: skip
        if document_type:
            stmt = stmt.where(DocumentType.code == document_type)
        if status:
            stmt = stmt.where(ExtractionSchema.status == status)
        return [schema_out(s, c) for s, c in (await self.db.execute(stmt)).all()]

    async def create_schema(self, user: Principal,
                            body: ExtractionSchemaCreate) -> ExtractionSchemaOut:  # fmt: skip
        dt = (await self.db.execute(select(DocumentType).where(
            DocumentType.code == body.document_type))).scalar_one_or_none()  # fmt: skip
        if dt is None:
            raise NotFoundError("document type not found", details={"field": "document_type"})
        fields = [f.model_dump(exclude_none=True) for f in body.fields]
        thresholds = body.thresholds.model_dump() if body.thresholds else None
        actions = list(body.action_names)
        if body.clone_from_id is not None:
            src = await self._get(ExtractionSchema, body.clone_from_id, "schema")
            if src.document_type_id != dt.id:
                raise _bad("clone source belongs to another document type",
                           field="clone_from_id")  # fmt: skip
            fields, thresholds = fields or list(src.fields), thresholds or dict(src.thresholds)
            actions = actions or list(src.action_names)
        thresholds = thresholds or {"classification_confidence_min": MIN_CLASSIFICATION,
                                    "required_field_min": MIN_REQUIRED_FIELD}  # fmt: skip
        check_schema_body(fields, thresholds, actions)
        top = (await self.db.execute(select(func.max(ExtractionSchema.schema_version)).where(
            ExtractionSchema.document_type_id == dt.id))).scalar_one()  # fmt: skip
        s = ExtractionSchema(
            document_type_id=dt.id, schema_version=(top or 0) + 1, fields=fields,
            thresholds=thresholds, action_names=actions, status="draft",
            data_classification="INTERNAL", created_by=user.user_id,
        )  # fmt: skip
        self.db.add(s)
        await self.db.flush()
        await self.db.refresh(s)
        out = schema_out(s, dt.code)
        await record_audit(self.db, action="idp.schema_create", target_schema="idp",
                           target_table="extraction_schemas", target_id=s.id,
                           after=out.model_dump(mode="json"))  # fmt: skip
        return out

    async def patch_schema(self, user: Principal, id_: uuid.UUID,
                           body: ExtractionSchemaPatch) -> ExtractionSchemaOut:  # fmt: skip
        s, code = await self._draft(id_, body.version)
        before = schema_out(s, code).model_dump(mode="json")
        fields = ([f.model_dump(exclude_none=True) for f in body.fields]
                  if body.fields is not None else list(s.fields))  # fmt: skip
        thresholds = body.thresholds.model_dump() if body.thresholds else dict(s.thresholds)
        actions = list(body.action_names) if body.action_names is not None else list(s.action_names)
        check_schema_body(fields, thresholds, actions)
        s.fields, s.thresholds, s.action_names = fields, thresholds, actions
        return await self._bump(user, s, code, "idp.schema_update", before)

    async def publish_schema(self, user: Principal, id_: uuid.UUID,
                             version: int) -> ExtractionSchemaOut:  # fmt: skip
        s, code = await self._draft(id_, version)
        check_schema_body(list(s.fields), dict(s.thresholds), list(s.action_names))
        before = schema_out(s, code).model_dump(mode="json")
        old = (await self.db.execute(select(ExtractionSchema).where(
            ExtractionSchema.document_type_id == s.document_type_id,
            ExtractionSchema.status == "published"))).scalars().all()  # fmt: skip
        for o in old:  # running jobs keep their schema id (immutable row)
            o.status, o.version = "retired", o.version + 1
        s.status, s.published_at = "published", func.now()
        dt = await self._get(DocumentType, s.document_type_id, "document type")
        dt.current_schema_id, dt.version = s.id, dt.version + 1
        return await self._bump(user, s, code, "idp.schema_publish", before)

    # ---------- EP-DC-33..35 ----------
    async def list_rules(self, *, schema_id: uuid.UUID | None,
                         kind: str | None) -> list[ValidationRuleOut]:  # fmt: skip
        stmt = select(ValidationRule).order_by(ValidationRule.code)
        if schema_id:
            stmt = stmt.where(ValidationRule.extraction_schema_id == schema_id)
        if kind:
            stmt = stmt.where(ValidationRule.kind == kind)
        return [rule_out(r) for r in (await self.db.execute(stmt)).scalars()]

    async def create_rule(self, user: Principal, body: ValidationRuleCreate) -> ValidationRuleOut:
        _check_expression(body.expression)
        if body.extraction_schema_id is not None:
            await self._draft(body.extraction_schema_id, None)
        dup = (await self.db.execute(select(ValidationRule.id).where(
            ValidationRule.extraction_schema_id.is_(None) if body.extraction_schema_id is None
            else ValidationRule.extraction_schema_id == body.extraction_schema_id,
            ValidationRule.code == body.code))).first()  # fmt: skip
        if dup:
            raise DuplicateResourceError("rule code exists", details={"code": body.code})
        r = ValidationRule(**body.model_dump(), data_classification="INTERNAL",
                           created_by=user.user_id)  # fmt: skip
        self.db.add(r)
        await self.db.flush()
        await self.db.refresh(r)
        out = rule_out(r)
        await record_audit(self.db, action="idp.rule_create", target_schema="idp",
                           target_table="validation_rules", target_id=r.id,
                           after=out.model_dump(mode="json"))  # fmt: skip
        return out

    async def patch_rule(self, user: Principal, id_: uuid.UUID,
                         body: ValidationRulePatch) -> ValidationRuleOut:  # fmt: skip
        r = await self._get(ValidationRule, id_, "rule")
        if r.extraction_schema_id is not None:
            s = await self._get(ExtractionSchema, r.extraction_schema_id, "schema")
            if s.status != "draft":
                raise ConflictStateError("rule of a published schema is immutable",
                                         details={"status": s.status})  # fmt: skip
        _check_version(r, body.version, "rule")
        before = rule_out(r).model_dump(mode="json")
        changes = body.model_dump(exclude_unset=True, exclude={"version"})
        if "expression" in changes:
            _check_expression(changes["expression"])
        for k, v in changes.items():
            setattr(r, k, v)
        r.version += 1
        r.updated_by = user.user_id
        await self.db.flush()
        await self.db.refresh(r)
        out = rule_out(r)
        await record_audit(self.db, action="idp.rule_update", target_schema="idp",
                           target_table="validation_rules", target_id=r.id, before=before,
                           after=out.model_dump(mode="json"))  # fmt: skip
        return out

    # ---------- helpers ----------
    async def _get(self, model: Any, id_: uuid.UUID, what: str) -> Any:
        obj = (await self.db.execute(select(model).where(model.id == id_))).scalar_one_or_none()
        if obj is None:
            raise NotFoundError(f"{what} not found")
        return obj

    async def _draft(self, id_: uuid.UUID, version: int | None) -> tuple[ExtractionSchema, str]:
        s = await self._get(ExtractionSchema, id_, "schema")
        if s.status != "draft":  # DEC-162: immutable after publish
            raise ConflictStateError("schema is not a draft", details={"status": s.status})
        if version is not None:
            _check_version(s, version, "schema")
        code = (await self.db.execute(select(DocumentType.code).where(
            DocumentType.id == s.document_type_id))).scalar_one()  # fmt: skip
        return s, code

    async def _bump(self, user: Principal, s: ExtractionSchema, code: str, action: str,
                    before: dict[str, Any]) -> ExtractionSchemaOut:  # fmt: skip
        s.version += 1
        s.updated_by = user.user_id
        await self.db.flush()
        await self.db.refresh(s)
        out = schema_out(s, code)
        await record_audit(self.db, action=action, target_schema="idp",
                           target_table="extraction_schemas", target_id=s.id, before=before,
                           after=out.model_dump(mode="json"))  # fmt: skip
        return out

    async def _schema_version(self, schema_id: uuid.UUID | None) -> int | None:
        if schema_id is None:
            return None
        return (await self.db.execute(select(ExtractionSchema.schema_version).where(
            ExtractionSchema.id == schema_id))).scalar_one_or_none()  # fmt: skip

    @staticmethod
    def _type_out(dt: DocumentType, schema_version: int | None) -> DocumentTypeOut:
        return DocumentTypeOut(
            id=dt.id, code=dt.code, name_vi=dt.name_vi, name_en=dt.name_en,
            pillars=list(dt.pillars), is_active=dt.is_active,
            current_schema_version=schema_version, channels_supported=channels_for(dt.code),
            version=dt.version,
        )  # fmt: skip


# C1 = manual form, C3 = file upload, C5 = spreadsheet import (04 §2; P0 types, R-DEC-62/65).
_CHANNELS = {
    "HR_ROSTER": ["C1", "C3", "C5"], "PLAN_KPI_OKR": ["C1", "C3", "C5"],
    "PERIOD_REPORT": ["C1", "C3", "C5"], "INVOICE": ["C1", "C3"], "OTHER": ["C3"],
}  # fmt: skip


def channels_for(code: str) -> list[str]:
    return list(_CHANNELS.get(code, ["C3"]))


def _check_expression(expression: dict[str, Any]) -> None:
    if expression.get("op") not in VALIDATOR_OPS:
        raise _bad("unknown validator op", field="expression.op", op=expression.get("op"),
                   allowed=sorted(VALIDATOR_OPS))  # fmt: skip
