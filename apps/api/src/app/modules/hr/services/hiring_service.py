"""Hiring plans — EP-84..86 + delay detection (T-122; FR-HR-03/04/07, 02 §8).

State machine (02 §8):
    draft → submitted (EP-85, `hr:write`)
    submitted → approved | rejected (EP-86, `hr:approve`, reason required, approver ≠ creator)
    rejected → draft (PATCH `status`) · approved → in_progress → completed (PATCH)
    draft | approved | in_progress → cancelled (PATCH)
Any other transition → `409 CONFLICT_STATE`. Content (department, position, headcount, salary
range, dates, budget) is editable only in `draft` / `rejected`; progress fields (`filled`,
`budget_spent`) while the plan is live.

`detect_delayed_hiring_plans(as_of)` is the daily job body (FR-HR-04): open plans
(`approved`, `in_progress`) late > 30 days with `filled < headcount` publish
`EVT-hr.hiring_plan_delayed` once — `delayed_notified_at` marks the plan; moving
`target_date` re-arms it.
"""

import uuid
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from typing import Any, cast

from sqlalchemy import ColumnElement
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import Actor, record_audit
from app.core.deps import Principal
from app.core.errors import BusinessRuleError, ConflictStateError, NotFoundError
from app.core.events.outbox import publish_in_tx
from app.core.pagination import PageParams
from app.modules.hr.models import HiringPlan
from app.modules.hr.repositories import (
    OPEN_PLAN_STATUSES,
    DepartmentRepository,
    HiringPlanRepository,
)
from app.modules.hr.schemas import (
    ApprovalIn,
    HiringPlanCreate,
    HiringPlanOut,
    HiringPlanUpdate,
    HiringPriority,
    HiringStatus,
)
from app.modules.hr.services.scope import SELF_ROLES, check_department, deny, department_scope

DELAY_THRESHOLD_DAYS = 30  # FR-HR-04 / 02 §8 (event); alert bands are METRIC-HR-04 config
EDITABLE_STATES = frozenset({"draft", "rejected"})
LIVE_STATES = frozenset({"draft", "rejected", "submitted", "approved", "in_progress"})
DELETABLE_STATES = frozenset({"draft", "rejected", "cancelled"})
PATCH_TRANSITIONS: dict[str, frozenset[str]] = {
    "draft": frozenset({"cancelled"}),
    "rejected": frozenset({"draft"}),
    "approved": frozenset({"in_progress", "cancelled"}),
    "in_progress": frozenset({"completed", "cancelled"}),
}
CONTENT_FIELDS = frozenset({
    "title", "department_id", "position", "headcount", "priority", "salary_min", "salary_max",
    "start_date", "target_date", "budget_amount", "hiring_manager_id", "requirements",
})  # fmt: skip
API_TO_DB = {
    "salary_min": "salary_range_min", "salary_max": "salary_range_max",
    "target_date": "target_fill_date", "budget_amount": "budget_allocated",
}  # fmt: skip


def plan_out(p: HiringPlan) -> HiringPlanOut:
    return HiringPlanOut(
        id=p.id, version=p.version, created_at=p.created_at, updated_at=p.updated_at,
        title=p.title, department_id=p.department_id, position=p.position,
        headcount=p.headcount, filled=p.filled, priority=cast(HiringPriority, p.priority),
        status=cast(HiringStatus, p.status), salary_min=p.salary_range_min,
        salary_max=p.salary_range_max, currency=p.currency, start_date=p.start_date,
        target_date=p.target_fill_date, budget_amount=p.budget_allocated,
        budget_spent=p.budget_spent, hiring_manager_id=p.hiring_manager_id,
        approved_by=p.approved_by, approved_at=p.approved_at, reject_reason=p.reject_reason,
        requirements=p.requirements,
    )  # fmt: skip


@dataclass(frozen=True)
class DelayedPlan:
    hiring_plan_id: uuid.UUID
    department_id: uuid.UUID
    days_late: int
    unfilled: int


class HiringPlanService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.plans = HiringPlanRepository(db)
        self.departments = DepartmentRepository(db)

    async def _audit(
        self, action: str, obj: HiringPlan, before: Any = None, after: Any = None,
        why: str | None = None, actor: Actor | None = None,
    ) -> None:  # fmt: skip
        await record_audit(
            self.db, action=action, target_schema="hr", target_table="hiring_plans",
            target_id=obj.id, before=before.model_dump(mode="json") if before else None,
            after=after.model_dump(mode="json") if after else None, why=why, actor=actor,
        )  # fmt: skip

    def _scope(self, user: Principal, p: HiringPlan) -> None:
        if user.role in SELF_ROLES:
            if p.hiring_manager_id != user.user_id:
                raise deny("hiring plan", hiring_plan_id=p.id)
            return
        check_department(user, p.department_id)

    async def get(self, user: Principal, id_: uuid.UUID) -> HiringPlan:
        obj = await self.plans.get(id_)
        if obj is None:
            raise NotFoundError("hiring plan not found")
        self._scope(user, obj)
        return obj

    async def list_plans(
        self, user: Principal, page: PageParams, *, department_id: uuid.UUID | None,
        status: str | None, delayed: bool | None, today: date,
    ) -> tuple[list[HiringPlanOut], int]:  # fmt: skip
        where: list[ColumnElement[bool]] = []
        if user.role in SELF_ROLES:
            where.append(HiringPlan.hiring_manager_id == user.user_id)
        else:
            department_id = department_scope(user, department_id)
        if department_id is not None:
            where.append(HiringPlan.department_id == department_id)
        if status:
            where.append(HiringPlan.status == status)
        if delayed is not None:
            late = (
                HiringPlan.status.in_(OPEN_PLAN_STATUSES)
                & (HiringPlan.target_fill_date < today)
                & (HiringPlan.filled < HiringPlan.headcount)
            )
            where.append(late if delayed else ~late)
        sort = API_TO_DB.get(page.sort_by, page.sort_by)
        items, total = await self.plans.list_page(
            limit=page.limit, offset=page.offset, sort_by=sort, order=page.order, where=where
        )
        return [plan_out(p) for p in items], total

    async def _check_department(self, user: Principal, department_id: uuid.UUID) -> None:
        check_department(user, department_id)
        if await self.departments.get(department_id) is None:
            raise BusinessRuleError("department not found", details={"field": "department_id"})

    async def create(self, user: Principal, body: HiringPlanCreate) -> HiringPlanOut:
        await self._check_department(user, body.department_id)
        if body.filled > body.headcount:
            raise BusinessRuleError("filled must be <= headcount", details={"field": "filled"})
        obj = await self.plans.create(
            title=body.title or body.position, department_id=body.department_id,
            position=body.position, headcount=body.headcount, filled=body.filled,
            priority=body.priority, status="draft", salary_range_min=body.salary_min,
            salary_range_max=body.salary_max, currency=body.currency,
            start_date=body.start_date, target_fill_date=body.target_date,
            hiring_manager_id=body.hiring_manager_id or user.user_id,
            requirements=body.requirements, budget_allocated=body.budget_amount,
            budget_spent=0, source="MANUAL", created_by=user.user_id,
        )  # fmt: skip
        await self.db.refresh(obj)
        out = plan_out(obj)
        await self._audit("hr.hiring_plan_create", obj, after=out)
        return out

    async def update(
        self, user: Principal, id_: uuid.UUID, body: HiringPlanUpdate, expected: int
    ) -> HiringPlanOut:
        obj = await self.get(user, id_)
        before = plan_out(obj)
        data = body.model_dump(exclude_unset=True, exclude={"version"})
        if obj.status not in LIVE_STATES:
            raise ConflictStateError(f"plan is {obj.status}", details={"status": obj.status})
        content = sorted(CONTENT_FIELDS & data.keys())
        if content and obj.status not in EDITABLE_STATES:
            raise ConflictStateError(
                "plan content is editable only in draft/rejected",
                details={"status": obj.status, "fields": content},
            )
        new_status = data.pop("status", None)
        if new_status is not None and new_status != obj.status:
            if new_status not in PATCH_TRANSITIONS.get(obj.status, frozenset()):
                raise ConflictStateError(
                    f"illegal transition {obj.status} → {new_status}",
                    details={"from": obj.status, "to": new_status},
                )
            data["status"] = new_status
            if new_status == "draft":
                data["reject_reason"] = None
        if "department_id" in data:
            await self._check_department(user, data["department_id"])
        merged = {**before.model_dump(), **data}
        if (
            merged["salary_min"]
            and merged["salary_max"]
            and merged["salary_max"] < merged["salary_min"]
        ):
            raise BusinessRuleError(
                "salary_max must be >= salary_min", details={"field": "salary_max"}
            )
        if merged["target_date"] <= merged["start_date"]:
            raise BusinessRuleError("target_date must be after start_date",
                                    details={"field": "target_date"})  # fmt: skip
        if merged["filled"] > merged["headcount"]:
            raise BusinessRuleError("filled must be <= headcount", details={"field": "filled"})
        if "target_date" in data and data["target_date"] != obj.target_fill_date:
            data["delayed_notified_at"] = None  # new milestone → may notify again (FR-HR-04)
        values = {API_TO_DB.get(k, k): v for k, v in data.items()}
        values["updated_by"] = user.user_id
        await self.plans.update(obj, expected_version=expected, **values)
        await self.db.refresh(obj)
        out = plan_out(obj)
        await self._audit("hr.hiring_plan_update", obj, before, out)
        return out

    async def delete(self, user: Principal, id_: uuid.UUID) -> None:
        obj = await self.get(user, id_)
        if obj.status not in DELETABLE_STATES:
            raise ConflictStateError(
                f"cannot delete a {obj.status} plan (cancel it first)",
                details={"status": obj.status},
            )
        before = plan_out(obj)
        obj.updated_by = user.user_id
        await self.plans.soft_delete(obj)
        await self._audit("hr.hiring_plan_delete", obj, before=before)

    # ---------- EP-85 ----------
    async def submit(self, user: Principal, id_: uuid.UUID) -> HiringPlanOut:
        obj = await self.get(user, id_)
        if obj.status != "draft":
            raise ConflictStateError(
                "only draft plans can be submitted", details={"from": obj.status, "to": "submitted"}
            )
        before = plan_out(obj)
        await self.plans.update(obj, status="submitted", updated_by=user.user_id)
        await self.db.refresh(obj)
        out = plan_out(obj)
        await self._audit("hr.hiring_plan_submit", obj, before, out)
        return out

    # ---------- EP-86 ----------
    async def decide(self, user: Principal, id_: uuid.UUID, body: ApprovalIn) -> HiringPlanOut:
        """CFO approve / reject (FR-HR-07). Forecast cost is finance's job via
        `EVT-finance.forecast_updated` (10 §4.8) — hr publishes nothing here."""
        obj = await self.plans.get(id_)
        if obj is None:
            raise NotFoundError("hiring plan not found")
        target = "approved" if body.decision == "approve" else "rejected"
        if obj.status != "submitted":
            raise ConflictStateError(
                "only submitted plans can be decided", details={"from": obj.status, "to": target}
            )
        reason = body.reason.strip()
        if not reason:
            raise BusinessRuleError("reason is required", details={"field": "reason"})
        if obj.created_by == user.user_id:
            raise BusinessRuleError(
                "approver must differ from the plan creator", details={"rule": "02 §8"}
            )
        before = plan_out(obj)
        await self.plans.update(
            obj, status=target, approved_by=user.user_id, approved_at=datetime.now(UTC),
            reject_reason=reason if target == "rejected" else None, updated_by=user.user_id,
        )  # fmt: skip
        await self.db.refresh(obj)
        out = plan_out(obj)
        await self._audit(f"hr.hiring_plan_{body.decision}", obj, before, out, why=reason)
        return out

    # ---------- FR-HR-04 job ----------
    async def detect_delayed(self, as_of: date) -> list[DelayedPlan]:
        """Publish `EVT-hr.hiring_plan_delayed` once per plan late > 30 days (idempotent)."""
        cutoff = as_of - timedelta(days=DELAY_THRESHOLD_DAYS)
        found: list[DelayedPlan] = []
        now = datetime.now(UTC)
        for p in await self.plans.delayed_candidates(cutoff):
            item = DelayedPlan(
                hiring_plan_id=p.id, department_id=p.department_id,
                days_late=(as_of - p.target_fill_date).days, unfilled=p.headcount - p.filled,
            )  # fmt: skip
            p.delayed_notified_at = now
            await publish_in_tx(
                self.db, event_type="hr.hiring_plan_delayed", producer="hr",
                aggregate_schema="hr", aggregate_table="hiring_plans", aggregate_id=p.id,
                payload={"hiring_plan_id": str(p.id), "department_id": str(p.department_id),
                         "days_late": item.days_late, "unfilled": item.unfilled},
            )  # fmt: skip
            await record_audit(
                self.db, action="hr.hiring_plan_delayed", target_schema="hr",
                target_table="hiring_plans", target_id=p.id,
                after={"days_late": item.days_late, "unfilled": item.unfilled},
                actor=Actor(type="SYSTEM"),
            )  # fmt: skip
            found.append(item)
        await self.db.flush()
        return found


async def detect_delayed_hiring_plans(db: AsyncSession, as_of: date) -> list[DelayedPlan]:
    """Public job entry (FR-HR-04, BR-HR-01 §8): caller commits. Safe to rerun the same day."""
    return await HiringPlanService(db).detect_delayed(as_of)
