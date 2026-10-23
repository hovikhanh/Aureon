"""EP-42 meetings, EP-43 decisions, EP-45 projects (T-131).

Scope (DEC-220): meeting = department + chair/attendees; decision has no `department_id`
(05) → department of its meeting + `owner_id`; project = department + `owner_id`.
"""

import uuid
from datetime import timedelta
from typing import Any

from sqlalchemy import ColumnElement, Date, any_, literal
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import Principal
from app.core.errors import BusinessRuleError, ConflictStateError
from app.core.pagination import PageParams
from app.modules.execution.models import Decision, Meeting, Project, Task
from app.modules.execution.repositories import (
    DecisionRepository,
    MeetingRepository,
    ProjectRepository,
    TaskRepository,
)
from app.modules.execution.schemas.meetings import (
    DecisionCreate,
    DecisionOut,
    DecisionUpdate,
    MeetingCreate,
    MeetingOut,
    MeetingUpdate,
    ProjectCreate,
    ProjectOut,
    ProjectUpdate,
)
from app.modules.execution.services import scope
from app.modules.execution.services.base import ExecBase, not_found, now_utc, today

REVIEW_OFFSETS_DAYS = (30, 60, 90)  # 10 EP-43 default `review_at`


def _c19(o: Any) -> dict[str, Any]:
    return {
        "id": o.id, "version": o.version, "source": o.source,
        "data_classification": o.data_classification,
        "created_at": o.created_at, "updated_at": o.updated_at,
    }  # fmt: skip


def meeting_out(m: Meeting) -> MeetingOut:
    return MeetingOut(
        **_c19(m), title=m.title, held_at=m.held_at, chair_id=m.chair_id,
        attendee_ids=list(m.attendee_ids), department_id=m.department_id, summary=m.summary,
        source_document_id=m.source_document_id, transcript_id=m.transcript_id,
    )  # fmt: skip


def decision_out(d: Decision) -> DecisionOut:
    return DecisionOut(
        **_c19(d), meeting_id=d.meeting_id, content=d.content, rationale=d.rationale,
        alternatives_rejected=d.alternatives_rejected, expected_outcome=d.expected_outcome,
        owner_id=d.owner_id, decided_at=d.decided_at, due_date=d.due_date,
        review_at=list(d.review_at), actual_outcome=d.actual_outcome,
        outcome_verified_at=d.outcome_verified_at, initiative_id=d.initiative_id,
        source_insight_id=d.source_insight_id, status=d.status, done_at=d.done_at,
        source_document_id=d.source_document_id,
    )  # fmt: skip


def project_out(p: Project) -> ProjectOut:
    return ProjectOut(
        **_c19(p), code=p.code, name=p.name, owner_id=p.owner_id, department_id=p.department_id,
        start_date=p.start_date, due_date=p.planned_end_date, actual_end_date=p.actual_end_date,
        status=p.status, budget_amount=p.budget_amount, currency=p.currency,
    )  # fmt: skip


def _page(page: PageParams) -> dict[str, Any]:
    return {"limit": page.limit, "offset": page.offset, "sort_by": page.sort_by,
            "order": page.order}  # fmt: skip


def _clean(filters: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in filters.items() if v is not None}


def _dates(start: Any, end: Any, field: str) -> None:
    if start is not None and end is not None and end < start:
        raise BusinessRuleError(f"{field} must be on/after start_date",
                                details={"field": field, "rule": "FR-TASK-01"})  # fmt: skip


class MeetingService(ExecBase):
    def __init__(self, db: AsyncSession) -> None:
        super().__init__(db)
        self.meetings = MeetingRepository(db)
        self.decisions = DecisionRepository(db)
        self.tasks = TaskRepository(db)

    @staticmethod
    def _own(user: Principal) -> list[ColumnElement[bool]]:
        return [
            Meeting.chair_id == user.user_id,
            literal(user.user_id, UUID(as_uuid=True)) == any_(Meeting.attendee_ids),
        ]

    async def list_meetings(
        self, user: Principal, page: PageParams, *, held_from: Any, held_to: Any,
        department_id: uuid.UUID | None,
    ) -> tuple[list[MeetingOut], int]:  # fmt: skip
        where: list[ColumnElement[bool]] = []
        pred = scope.predicate(user, "read", dept=Meeting.department_id, own=self._own(user))
        if pred is not None:
            where.append(pred)
        if held_from is not None:
            where.append(Meeting.held_at >= held_from)
        if held_to is not None:
            where.append(Meeting.held_at <= held_to)
        items, total = await self.meetings.list_page(
            **_page(page), filters=_clean({"department_id": department_id}), where=where
        )
        return [meeting_out(m) for m in items], total

    async def get_meeting(self, user: Principal, id_: uuid.UUID, action: str = "read") -> Meeting:
        m = await self.meetings.get(id_)
        if m is None:
            raise not_found("meeting")
        scope.check(user, action, dept=m.department_id, owners=(m.chair_id, *m.attendee_ids),
                    what="meeting")  # fmt: skip
        return m

    async def create_meeting(self, user: Principal, body: MeetingCreate) -> MeetingOut:
        data = body.model_dump()
        data["department_id"] = scope.pin_department(user, data["department_id"])
        if scope.level(user, "write") == "o" and user.user_id not in data["attendee_ids"]:
            data["chair_id"] = data["chair_id"] or user.user_id
            scope.require_self(user, data["chair_id"], field="chair_id")
        await self._check_transcript(data.get("transcript_id"))
        m = await self.meetings.create(**data, source="MANUAL", created_by=user.user_id)
        await self.db.refresh(m)
        out = meeting_out(m)
        await self.audit("meeting_create", "meetings", m.id, after=out)
        return out

    async def _check_transcript(self, transcript_id: uuid.UUID | None) -> None:
        if transcript_id is not None:
            raise BusinessRuleError(
                "transcript_id is set by the transcript upload flow (EP-20)",
                details={"field": "transcript_id", "rule": "DEC-153"},
            )

    async def update_meeting(
        self, user: Principal, id_: uuid.UUID, body: MeetingUpdate, expected: int
    ) -> MeetingOut:
        m = await self.get_meeting(user, id_, "write")
        before = meeting_out(m)
        data = body.model_dump(exclude_unset=True, exclude={"version"})
        if "department_id" in data:
            data["department_id"] = scope.pin_department(user, data["department_id"])
        if "transcript_id" in data and data["transcript_id"] != m.transcript_id:
            await self._check_transcript(data["transcript_id"])
        for k in ("title", "held_at", "attendee_ids"):
            if k in data and data[k] is None:
                del data[k]
        await self.meetings.update(m, expected_version=expected, updated_by=user.user_id, **data)
        await self.db.refresh(m)
        out = meeting_out(m)
        await self.audit("meeting_update", "meetings", m.id, before, out)
        return out

    async def delete_meeting(self, user: Principal, id_: uuid.UUID) -> None:
        m = await self.get_meeting(user, id_, "write")
        if await self.decisions.where(Decision.meeting_id == m.id) or await self.tasks.where(
            Task.meeting_id == m.id
        ):
            raise ConflictStateError("meeting still has decisions or tasks",
                                     details={"meeting_id": str(m.id)})  # fmt: skip
        before = meeting_out(m)
        m.updated_by = user.user_id
        await self.meetings.soft_delete(m)
        await self.audit("meeting_delete", "meetings", m.id, before=before)

    # ---------- EP-43 decisions ----------
    def _decision_pred(self, user: Principal) -> ColumnElement[bool] | None:
        """Decisions have no `department_id` (05) → department of their meeting."""
        own: list[ColumnElement[bool]] = [Decision.owner_id == user.user_id]
        if scope.level(user) == "d" and user.department_id is not None:
            dept_meetings = MeetingRepository.ids_where(Meeting.department_id == user.department_id)
            own.append(Decision.meeting_id.in_(dept_meetings))
        return scope.predicate(user, "read", own=own)

    async def list_decisions(
        self, user: Principal, page: PageParams, *, status: str | None,
        meeting_id: uuid.UUID | None, initiative_id: uuid.UUID | None, review_due: bool | None,
    ) -> tuple[list[DecisionOut], int]:  # fmt: skip
        where: list[ColumnElement[bool]] = []
        pred = self._decision_pred(user)
        if pred is not None:
            where.append(pred)
        if review_due is not None:
            # a review date has been reached and the outcome is not verified yet
            reached = literal(today(), Date) >= any_(Decision.review_at)
            due = Decision.outcome_verified_at.is_(None) & reached
            where.append(due if review_due else ~due)
        filters = _clean({"status": status, "meeting_id": meeting_id,
                          "initiative_id": initiative_id})  # fmt: skip
        items, total = await self.decisions.list_page(**_page(page), filters=filters, where=where)
        return [decision_out(d) for d in items], total

    async def get_decision(self, user: Principal, id_: uuid.UUID, action: str = "read") -> Decision:
        d = await self.decisions.get(id_)
        if d is None:
            raise not_found("decision")
        dept = None
        if d.meeting_id is not None:
            meeting = await self.meetings.get(d.meeting_id)
            dept = meeting.department_id if meeting is not None else None
        scope.check(user, action, dept=dept, owners=(d.owner_id,), what="decision")
        return d

    async def create_decision(self, user: Principal, body: DecisionCreate) -> DecisionOut:
        data = body.model_dump()
        if scope.level(user, "write") == "o":
            data["owner_id"] = data["owner_id"] or user.user_id
        scope.require_self(user, data["owner_id"], field="owner_id")
        await self.require_refs(data, "FR-DC-11")
        if data["meeting_id"] is not None:
            await self.get_meeting(user, data["meeting_id"], "write")
        if data["review_at"] is None:
            day = data["decided_at"].date()
            data["review_at"] = [day + timedelta(days=n) for n in REVIEW_OFFSETS_DAYS]
        data["done_at"] = now_utc() if data["status"] == "done" else None
        d = await self.decisions.create(**data, source="MANUAL", created_by=user.user_id)
        await self.db.refresh(d)
        out = decision_out(d)
        await self.audit("decision_create", "decisions", d.id, after=out)
        return out

    async def update_decision(
        self, user: Principal, id_: uuid.UUID, body: DecisionUpdate, expected: int
    ) -> DecisionOut:
        d = await self.get_decision(user, id_, "write")
        before = decision_out(d)
        data = body.model_dump(exclude_unset=True, exclude={"version"})
        scope.require_self(user, data.get("owner_id"), field="owner_id")
        await self.require_refs(data, "FR-DC-11")
        for k in ("content", "status", "review_at"):
            if k in data and data[k] is None:
                del data[k]
        if "status" in data and data["status"] != d.status:
            data["done_at"] = now_utc() if data["status"] == "done" else None
        await self.decisions.update(d, expected_version=expected, updated_by=user.user_id, **data)
        await self.db.refresh(d)
        out = decision_out(d)
        await self.audit("decision_update", "decisions", d.id, before, out)
        return out


class ProjectService(ExecBase):
    def __init__(self, db: AsyncSession) -> None:
        super().__init__(db)
        self.projects = ProjectRepository(db)
        self.tasks = TaskRepository(db)

    async def list_projects(
        self, user: Principal, page: PageParams, *, status: str | None,
        department_id: uuid.UUID | None,
    ) -> tuple[list[ProjectOut], int]:  # fmt: skip
        pred = scope.predicate(user, "read", dept=Project.department_id,
                               own=[Project.owner_id == user.user_id])  # fmt: skip
        items, total = await self.projects.list_page(
            **_page(page), filters=_clean({"status": status, "department_id": department_id}),
            where=[pred] if pred is not None else [],
        )  # fmt: skip
        return [project_out(p) for p in items], total

    async def get_project(self, user: Principal, id_: uuid.UUID, action: str = "read") -> Project:
        p = await self.projects.get(id_)
        if p is None:
            raise not_found("project")
        scope.check(user, action, dept=p.department_id, owners=(p.owner_id,), what="project")
        return p

    async def create_project(self, user: Principal, body: ProjectCreate) -> ProjectOut:
        data = body.model_dump()
        data["planned_end_date"] = data.pop("due_date")
        scope.require_self(user, data["owner_id"], field="owner_id")
        data["department_id"] = scope.pin_department(user, data["department_id"])
        _dates(data["start_date"], data["planned_end_date"], "due_date")
        await self.require_unique(Project, "code", data["code"], None)
        p = await self.projects.create(**data, source="MANUAL", created_by=user.user_id)
        await self.db.refresh(p)
        out = project_out(p)
        await self.audit("project_create", "projects", p.id, after=out)
        return out

    async def update_project(
        self, user: Principal, id_: uuid.UUID, body: ProjectUpdate, expected: int
    ) -> ProjectOut:
        p = await self.get_project(user, id_, "write")
        before = project_out(p)
        data = body.model_dump(exclude_unset=True, exclude={"version"})
        if "due_date" in data:
            data["planned_end_date"] = data.pop("due_date")
        scope.require_self(user, data.get("owner_id"), field="owner_id")
        if "department_id" in data:
            data["department_id"] = scope.pin_department(user, data["department_id"])
        for k in ("code", "name", "owner_id", "status"):
            if k in data and data[k] is None:
                del data[k]
        _dates(data.get("start_date", p.start_date),
               data.get("planned_end_date", p.planned_end_date), "due_date")  # fmt: skip
        if "code" in data:
            await self.require_unique(Project, "code", data["code"], p.id)
        await self.projects.update(p, expected_version=expected, updated_by=user.user_id, **data)
        await self.db.refresh(p)
        out = project_out(p)
        await self.audit("project_update", "projects", p.id, before, out)
        return out

    async def delete_project(self, user: Principal, id_: uuid.UUID) -> None:
        p = await self.get_project(user, id_, "write")
        if await self.tasks.where(Task.project_id == p.id):
            raise ConflictStateError("project still has tasks", details={"project_id": str(p.id)})
        before = project_out(p)
        p.updated_by = user.user_id
        await self.projects.soft_delete(p)
        await self.audit("project_delete", "projects", p.id, before=before)
