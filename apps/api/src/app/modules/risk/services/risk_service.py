"""Public service interface of `risk` — EP-101 register + EP-102 assessments (T-211).

Every mutation writes `ENT-AuditLog` and its outbox events in the caller's transaction; the
route commits. Scope rules: `services/scope.py`; pure BR-RSK maths: `services/rules.py`.
"""

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import Principal
from app.core.errors import BusinessRuleError, ConflictStateError, NotFoundError
from app.core.pagination import PageParams
from app.modules.risk.models import Risk, RiskAssessment
from app.modules.risk.repositories import AssessmentRepository, RiskRepository
from app.modules.risk.schemas import (
    AssessmentIn,
    AssessmentOut,
    RiskCreate,
    RiskOut,
    RiskUpdate,
)
from app.modules.risk.services import rules, scope
from app.modules.risk.services.common import (
    assessment_out,
    audit,
    now_utc,
    publish,
    publish_identified,
    risk_out,
)


def owner_rule(score: int, status: str, owner_id: uuid.UUID | None) -> None:
    """BR-RSK-02: medium+ risks need an owner unless still `proposed`."""
    if status != "proposed" and owner_id is None and rules.owner_required(score):
        raise BusinessRuleError(
            "owner_id is required for risk_score >= 5 (BR-RSK-02)",
            details={"field": "owner_id", "rule": "BR-RSK-02"},
        )


class RiskService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.risks = RiskRepository(db)
        self.assessments = AssessmentRepository(db)

    async def new_code(self) -> str:
        await self.risks.lock_codes()
        year = now_utc().year
        return rules.format_code(year, rules.next_seq(await self.risks.last_code(year)))

    async def get_row(self, user: Principal, id_: uuid.UUID) -> Risk:
        obj = await self.risks.get(id_)
        if obj is None:
            raise NotFoundError("risk not found")
        scope.check_read(user, obj)
        return obj

    async def get(self, user: Principal, id_: uuid.UUID) -> RiskOut:
        return risk_out(await self.get_row(user, id_))

    async def list_risks(
        self, user: Principal, page: PageParams, *, filters: dict[str, Any]
    ) -> tuple[list[RiskOut], int]:
        items, total = await self.risks.list_page(
            limit=page.limit, offset=page.offset, sort_by=page.sort_by, order=page.order,
            filters={k: v for k, v in filters.items() if v is not None},
            where=scope.read_filter(user),
        )  # fmt: skip
        return [risk_out(r) for r in items], total

    async def create(self, user: Principal, body: RiskCreate) -> RiskOut:
        """Manual entry (FR-RSK-01) → `identified` directly (05 §4.6, DEC-148)."""
        dept = scope.pin_department(user, body.department_id)
        score = rules.risk_score(body.likelihood, body.impact)
        owner_rule(score, "identified", body.owner_id)
        now = now_utc()
        obj = Risk(
            code=await self.new_code(), title=body.title, description=body.description,
            category=body.category, likelihood=body.likelihood, impact=body.impact,
            severity=rules.level_for(score), status="identified", risk_source="manual",
            owner_id=body.owner_id, department_id=dept, review_date=body.review_date,
            linked_entities={k: str(v) for k, v in body.linked_entities.items()},
            identified_at=now, source="MANUAL", created_by=user.user_id,
        )  # fmt: skip
        self.db.add(obj)
        await self.db.flush()
        await self.db.refresh(obj)
        out = risk_out(obj)
        await audit(self.db, "risk.risk_create", "risks", obj, after=out)
        await publish_identified(self.db, obj)
        return out

    async def update(
        self, user: Principal, id_: uuid.UUID, body: RiskUpdate, expected: int
    ) -> RiskOut:
        """Descriptive fields only — score changes go through EP-102 (DEC-216)."""
        obj = await self.get_row(user, id_)
        scope.check_write(user, obj)
        if obj.status in rules.TERMINAL_STATUSES:
            raise ConflictStateError("risk is closed", details={"status": obj.status})
        data = body.model_dump(exclude_unset=True, exclude={"version"})
        if "department_id" in data:
            data["department_id"] = scope.pin_department(user, data["department_id"])
        if "linked_entities" in data:
            data["linked_entities"] = {k: str(v) for k, v in (body.linked_entities or {}).items()}
        owner_rule(obj.likelihood * obj.impact, obj.status, data.get("owner_id", obj.owner_id))
        before = risk_out(obj)
        await self.risks.update(obj, expected_version=expected, updated_by=user.user_id, **data)
        await self.db.refresh(obj)
        out = risk_out(obj)
        await audit(self.db, "risk.risk_update", "risks", obj, before, out)
        return out

    # ---------- EP-102 ----------
    async def list_assessments(self, user: Principal, id_: uuid.UUID) -> list[AssessmentOut]:
        obj = await self.get_row(user, id_)
        return [assessment_out(a) for a in await self.assessments.for_risk(obj.id)]

    async def assess(self, user: Principal, id_: uuid.UUID, body: AssessmentIn) -> AssessmentOut:
        obj = await self.get_row(user, id_)
        scope.check_write(user, obj)
        await self.risks.lock(obj)
        return await self.apply_assessment(obj, body, actor=user.user_id)

    async def apply_assessment(
        self, obj: Risk, body: AssessmentIn, *, actor: uuid.UUID | None
    ) -> AssessmentOut:
        """New likelihood × impact → `ENT-RiskAssessment`; level change → `risk_level_changed`.

        `actor=None` = SYSTEM (event consumer re-assessing an existing risk, BR-RSK-03).
        A `proposed` risk changes level silently (not yet in the register — DEC-148).
        """
        if obj.status in rules.TERMINAL_STATUSES:
            raise ConflictStateError("risk is closed", details={"status": obj.status})
        score = rules.risk_score(body.likelihood, body.impact)
        owner_rule(score, obj.status, obj.owner_id)
        old_level, new_level = obj.severity, rules.level_for(score)
        before = risk_out(obj)
        status = "assessed" if obj.status == "identified" else obj.status
        await self.risks.update(
            obj, likelihood=body.likelihood, impact=body.impact, severity=new_level,
            status=status, updated_by=actor,
        )  # fmt: skip
        row = RiskAssessment(
            risk_id=obj.id, likelihood=body.likelihood, impact=body.impact, risk_score=score,
            severity=new_level, assessed_at=now_utc(), assessed_by=actor, rationale=body.note,
        )  # fmt: skip
        self.db.add(row)
        await self.db.flush()
        await self.db.refresh(obj)
        await self.db.refresh(row)
        out = assessment_out(row)
        await audit(self.db, "risk.assessment_create", "risks", obj, before, risk_out(obj))
        if new_level != old_level and obj.status != "proposed":
            await publish(self.db, "risk.risk_level_changed", obj,
                          {"from_severity": old_level, "to_severity": new_level})  # fmt: skip
        return out
