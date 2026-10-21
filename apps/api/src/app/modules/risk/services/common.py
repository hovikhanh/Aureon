"""Shared helpers of the risk services: DTO mapping, audit, outbox (10 §1.8, §8)."""

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import record_audit
from app.core.base_model import Base
from app.core.events.outbox import publish_in_tx
from app.modules.risk.models import Risk, RiskAssessment
from app.modules.risk.schemas import AssessmentOut, RiskOut


def now_utc() -> datetime:
    return datetime.now(UTC)


def risk_out(r: Risk) -> RiskOut:
    return RiskOut(
        id=r.id, version=r.version, created_at=r.created_at, updated_at=r.updated_at,
        code=r.code, title=r.title, description=r.description, category=r.category,
        likelihood=r.likelihood, impact=r.impact, risk_score=r.likelihood * r.impact,
        level=r.severity, status=r.status, risk_source=r.risk_source, owner_id=r.owner_id,
        department_id=r.department_id, linked_entities=dict(r.linked_entities or {}),
        review_date=r.review_date, identified_at=r.identified_at, proposed_at=r.proposed_at,
        confirmed_by=r.confirmed_by, confirmed_at=r.confirmed_at, accepted_by=r.accepted_by,
        accepted_reason=r.accepted_reason, accepted_at=r.accepted_at,
        source_event_id=r.source_event_id, source_document_id=r.source_document_id,
    )  # fmt: skip


def assessment_out(a: RiskAssessment) -> AssessmentOut:
    return AssessmentOut(
        id=a.id, risk_id=a.risk_id, likelihood=a.likelihood, impact=a.impact,
        risk_score=a.risk_score, level=a.severity, note=a.rationale,
        assessed_at=a.assessed_at, assessed_by=a.assessed_by,
    )  # fmt: skip


def links_payload(r: Risk) -> dict[str, str]:
    return {k: str(v) for k, v in (r.linked_entities or {}).items()}


async def audit(
    db: AsyncSession, action: str, table: str, obj: Base,
    before: BaseModel | None = None, after: BaseModel | None = None, why: str | None = None,
) -> None:  # fmt: skip
    await record_audit(
        db, action=action, target_schema="risk", target_table=table,
        target_id=getattr(obj, "id", None),
        before=before.model_dump(mode="json") if before is not None else None,
        after=after.model_dump(mode="json") if after is not None else None, why=why,
    )  # fmt: skip


async def publish(db: AsyncSession, event_type: str, r: Risk, payload: dict[str, Any]) -> None:
    await publish_in_tx(
        db, event_type=event_type, producer="risk", aggregate_schema="risk",
        aggregate_table="risks", aggregate_id=r.id, payload={"risk_id": str(r.id), **payload},
    )  # fmt: skip


async def publish_identified(db: AsyncSession, r: Risk) -> None:
    """`risk.risk_identified` only for severity ≥ high (03 BR-RSK-02 table, 05 §5.3)."""
    if r.severity in ("high", "critical"):
        await publish(db, "risk.risk_identified", r, {
            "category": r.category, "severity": r.severity, "risk_source": r.risk_source,
            "linked_entities": links_payload(r),
        })  # fmt: skip


async def publish_proposed(db: AsyncSession, r: Risk) -> None:
    await publish(db, "risk.risk_proposed", r, {
        "category": r.category, "severity": r.severity, "risk_source": r.risk_source,
        "linked_entities": links_payload(r),
    })  # fmt: skip
