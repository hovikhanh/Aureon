"""Shared helpers of the M1.5 capture channels C1 (manual) and C5 (import) — 10 §7.2.4.

* `normalize` — VN value normalisation per `value_type` (FR-DC-13): dates `dd/mm/yyyy` →
  ISO, `1.250.000` → 1250000, enum case-folded; returns a row error instead of guessing.
* `published_schema` — the active doc type + its published `ExtractionSchema` (404 otherwise).
* `assign_initial_review` — first `ReviewAssignment` (04 §8.2), shared with the pipeline.
* `document_out` — `DocumentOut` with the doc-type code and `can_undo` filled in.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundError
from app.modules.idp.models import (
    DocumentType,
    ExtractionSchema,
    SourceDocument,
    ValidationRule,
)
from app.modules.idp.schemas import DocumentOut

RowError = dict[str, Any]
_DATE_FORMATS = ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y")
_NUMERIC = frozenset({"money", "number", "percent"})
_CLASSIFICATION = {1: "PUBLIC", 2: "INTERNAL", 3: "CONFIDENTIAL", 4: "SECRET"}


def row_error(field: str | None, rule_code: str, **params: Any) -> RowError:
    key = rule_code.lower().replace("-", "_")
    return {"field": field, "rule_code": rule_code, "message_key": f"idp.import.error.{key}",
            "params": params}  # fmt: skip


def classification_of(level: int) -> str:
    return _CLASSIFICATION.get(level, "INTERNAL")


def _blank(value: Any) -> bool:
    return value is None or (isinstance(value, str) and not value.strip())


def _date(value: Any) -> str | None:
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    text = str(value).strip()
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(text, fmt).date().isoformat()
        except ValueError:
            continue
    return None


def _number(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip().replace(" ", "").replace("\u00a0", "")
    for unit in ("VND", "vnd", "đ", "₫", "%"):
        text = text.replace(unit, "")
    if "." in text and "," in text:  # 1.250.000,5 (VN)
        text = text.replace(".", "").replace(",", ".")
    elif "," in text:  # 12,5 (VN decimal comma)
        text = text.replace(",", ".")
    elif text.count(".") > 1 or (text.count(".") == 1 and len(text.split(".")[1]) == 3):
        text = text.replace(".", "")  # 1.250.000 / 25.000 (VN thousands)
    try:
        return float(text)
    except ValueError:
        return None


def normalize(spec: dict[str, Any], value: Any) -> tuple[Any, RowError | None]:
    """`(normalised value, None)` or `(None, row error)`; blank → `(None, None)`."""
    name, kind = spec["name"], spec.get("value_type", "text")
    if _blank(value):
        return None, None
    if kind == "date":
        iso = _date(value)
        return (iso, None) if iso else (None, row_error(name, "DATE_FORMAT", value=str(value)))
    if kind in _NUMERIC:
        num = _number(value)
        if num is None:
            return None, row_error(name, "NUMBER_FORMAT", value=str(value))
        if kind == "money":  # BIGINT smallest unit (VND)
            return round(num), None
        return (int(num) if num.is_integer() else num), None
    text = str(value).strip()
    if kind == "enum" and spec.get("enum"):
        match = next((e for e in spec["enum"] if e.lower() == text.lower()), None)
        if match is None:
            return None, row_error(name, "ENUM", value=text, allowed=spec["enum"])
        return match, None
    if kind == "period" and isinstance(value, (datetime, date)):
        return value.strftime("%Y-%m"), None
    if isinstance(value, float) and value.is_integer():
        return str(int(value)), None  # Excel numeric codes ("101.0" → "101")
    return text, None


def required_errors(
    fields: list[dict[str, Any]],
    values: dict[str, Any],
    errors: list[RowError] = (),  # type: ignore[assignment]
) -> list[RowError]:
    """`REQUIRED` for each missing required field without a format error already."""
    flagged = {e.get("field") for e in errors}
    return [row_error(f["name"], "REQUIRED") for f in fields
            if f.get("required") and values.get(f["name"]) is None
            and f["name"] not in flagged]  # fmt: skip


@dataclass
class Published:
    doc_type: DocumentType
    schema: ExtractionSchema
    rules: list[dict[str, Any]] = field(default_factory=list)

    @property
    def fields(self) -> list[dict[str, Any]]:
        return list(self.schema.fields or [])


async def published_schema(db: AsyncSession, code: str) -> Published:
    """Active doc type `code` with a published schema, else `404 NOT_FOUND`."""
    row = (await db.execute(
        select(DocumentType, ExtractionSchema)
        .join(ExtractionSchema, ExtractionSchema.id == DocumentType.current_schema_id)
        .where(DocumentType.code == code, DocumentType.is_active.is_(True),
               ExtractionSchema.status == "published")
    )).first()  # fmt: skip
    if row is None:
        raise NotFoundError("document type not found", details={"document_type": code})
    return Published(row[0], row[1], await schema_rules(db, row[1].id))


async def schema_rules(db: AsyncSession, schema_id: Any) -> list[dict[str, Any]]:
    rows = (await db.execute(select(ValidationRule).where(
        ValidationRule.extraction_schema_id == schema_id, ValidationRule.is_active.is_(True)
    ))).scalars()  # fmt: skip
    return [{"code": r.code, "kind": r.kind, "expression": r.expression, "severity": r.severity}
            for r in rows]  # fmt: skip


async def type_code(db: AsyncSession, type_id: Any) -> str | None:
    if type_id is None:
        return None
    stmt = select(DocumentType.code).where(DocumentType.id == type_id)
    return (await db.execute(stmt)).scalar_one_or_none()


async def assign_initial_review(db: AsyncSession, doc: SourceDocument) -> None:
    """Initial ASSIGN row (04 §8.2): role pool `REV`, `due_at = now + REVIEW_SLA_HOURS`."""
    from app.core.config import get_config
    from app.modules.idp.models import ReviewAssignment

    stmt = select(ReviewAssignment.id).where(
        ReviewAssignment.source_document_id == doc.id, ReviewAssignment.is_current.is_(True)
    )
    if (await db.execute(stmt)).first() is not None:
        return
    due_at = datetime.now(UTC) + timedelta(hours=get_config().review_sla_hours)
    db.add(ReviewAssignment(source_document_id=doc.id, kind="ASSIGN", to_role_code="REV",
                            due_at=due_at, is_current=True))  # fmt: skip
    await db.flush()


def can_undo(doc: SourceDocument, now: datetime | None = None) -> bool:
    if doc.status != "COMMITTED" or doc.undo_deadline is None:
        return False
    deadline = doc.undo_deadline
    deadline = deadline if deadline.tzinfo else deadline.replace(tzinfo=UTC)
    return deadline > (now or datetime.now(UTC))


def document_out(doc: SourceDocument, code: str | None) -> DocumentOut:
    out = DocumentOut.model_validate(doc)
    return out.model_copy(update={"document_type": code, "can_undo": can_undo(doc)})
