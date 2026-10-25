"""D01 Organization structure — EP-ORG-01..05, 11..20, 24 (M1.2 T-613, 10 §7.2.1).

Writes: audit `hr.<entity>_<verb>` + `hr.org_structure_changed` (R-DEC-35) in the request
transaction. Archive = `deleted_at` + `valid_to` (FR-ORG-03), refused while live children exist.
Reads are scoped by `structure_scope` (EMP/REV → 403, MGR → own department subtree).
"""

import uuid
from collections.abc import Iterable, Sequence
from datetime import UTC, date, datetime, timedelta
from typing import Any

from pydantic import BaseModel
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import record_audit
from app.core.deps import Principal
from app.core.errors import BusinessRuleError, DuplicateResourceError, NotFoundError
from app.core.events.outbox import publish_in_tx
from app.core.pagination import PageParams
from app.modules.hr.models import Organization, Position, Team
from app.modules.hr.repositories import EmployeeRepository
from app.modules.hr.repositories.org import (
    DeptRepository,
    OrgRepository,
    PositionsRepository,
    TeamRepository,
    TreeRepository,
)
from app.modules.hr.schemas.org import (
    OrganizationCreate,
    OrganizationOut,
    OrganizationUpdate,
    OrgTreeOut,
    PositionCreate,
    PositionOut,
    PositionUpdate,
    TeamCreate,
    TeamOut,
    TeamUpdate,
    TreeDepartment,
    TreeMember,
    TreeOrganization,
    TreeTeam,
)
from app.modules.hr.services.scope import deny, structure_scope


def today() -> date:
    return datetime.now(UTC).date()


def _rule(message: str, reason: str, field: str | None = None, **extra: Any) -> BusinessRuleError:
    return BusinessRuleError(message, details={"reason": reason, **extra} |
                             ({"field": field} if field else {}))  # fmt: skip


def _json(m: BaseModel | None) -> Any:
    return m.model_dump(mode="json") if m is not None else None


class StructureService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.orgs = OrgRepository(db)
        self.depts = DeptRepository(db)
        self.teams = TeamRepository(db)
        self.positions = PositionsRepository(db)
        self.employees = EmployeeRepository(db)

    # ---------- public: department subtree (R-DEC-57, `core/org_scope`) ----------
    async def subtree_ids(self, root_ids: Iterable[uuid.UUID]) -> set[uuid.UUID]:
        """Every root + its live descendant departments (goal scope DIR / MGR, T-632)."""
        out: set[uuid.UUID] = set()
        for root in set(root_ids):
            if root not in out:
                out |= await self.depts.subtree_ids(root)
        return out

    # ---------- public: lookups for the Action Registry v2 (T-636) ----------
    async def team_id_by_code(self, department_id: uuid.UUID, code: str) -> uuid.UUID | None:
        team = await self.teams.by_department_code(department_id, code)
        return team.id if team is not None else None

    # ---------- shared ----------
    async def _record(
        self, entity: str, table: str, obj: Any, change: str, verb: str,
        before: BaseModel | None = None, after: BaseModel | None = None, **ref: Any,
    ) -> None:  # fmt: skip
        await record_audit(self.db, action=f"hr.{entity}_{verb}", target_schema="hr",
                           target_table=table, target_id=obj.id, before=_json(before),
                           after=_json(after))  # fmt: skip
        payload = {"entity": entity, "entity_id": str(obj.id), "change": change} | {
            k: str(v) for k, v in ref.items() if v is not None
        }
        await publish_in_tx(self.db, event_type="hr.org_structure_changed", producer="hr",
                            aggregate_schema="hr", aggregate_table=table, aggregate_id=obj.id,
                            payload=payload)  # fmt: skip

    async def _flush(self, what: str) -> None:
        try:
            async with self.db.begin_nested():
                await self.db.flush()
        except IntegrityError as exc:
            raise DuplicateResourceError(f"{what} code exists") from exc

    @staticmethod
    def _end(valid_from: date) -> date:
        return max(today(), valid_from + timedelta(days=1))

    async def _department(self, id_: uuid.UUID, field: str = "department_id") -> Any:
        dept = await self.depts.get(id_)
        if dept is None:
            raise _rule("department not found", "not_found", field)
        return dept

    async def _employee(self, id_: uuid.UUID | None, field: str) -> None:
        if id_ is not None and await self.employees.get(id_) is None:
            raise _rule("employee not found", "not_found", field)

    async def _visible_departments(self, user: Principal) -> set[uuid.UUID] | None:
        root = structure_scope(user)
        return None if root is None else await self.depts.subtree_ids(root)

    async def _check_visible(self, user: Principal, department_id: uuid.UUID) -> None:
        seen = await self._visible_departments(user)
        if seen is not None and department_id not in seen:
            raise deny("department", department_id=department_id)

    async def get_department_visible(self, user: Principal, id_: uuid.UUID) -> Any:
        """Scoped single-department read (lineage EP-DC-26): 404 / 403 like EP-ORG reads."""
        dept = await self.depts.get(id_)
        if dept is None:
            raise NotFoundError("department not found")
        await self._check_visible(user, dept.id)
        return dept

    # ---------- organizations (EP-ORG-01..05) ----------
    async def list_orgs(
        self, user: Principal, page: PageParams, *, q: str | None, include_archived: bool
    ) -> tuple[list[OrganizationOut], int]:
        structure_scope(user)
        rows, total = await self.orgs.page(q=q, include_archived=include_archived,
                                           limit=page.limit, offset=page.offset,
                                           sort_by=page.sort_by, order=page.order)  # fmt: skip
        return [OrganizationOut.model_validate(o) for o in rows], total

    async def get_org(self, user: Principal, id_: uuid.UUID) -> OrganizationOut:
        structure_scope(user)
        return OrganizationOut.model_validate(await self._org(id_))

    async def _org(self, id_: uuid.UUID) -> Organization:
        org = await self.orgs.get(id_)
        if org is None:
            raise NotFoundError("organization not found")
        return org

    async def create_org(self, user: Principal, body: OrganizationCreate) -> OrganizationOut:
        if await self.orgs.by_code_live(body.code):
            raise DuplicateResourceError("organization code exists", details={"code": body.code})
        org = Organization(code=body.code, name=body.name, legal_name=body.legal_name,
                           tax_code=body.tax_code, valid_from=body.valid_from or today(),
                           source="MANUAL", created_by=user.user_id)  # fmt: skip
        self.db.add(org)
        await self._flush("organization")
        await self.db.refresh(org)
        out = OrganizationOut.model_validate(org)
        await self._record("organization", "organizations", org, "created", "create", after=out,
                           valid_from=org.valid_from)  # fmt: skip
        return out

    async def update_org(
        self, user: Principal, id_: uuid.UUID, body: OrganizationUpdate, expected: int
    ) -> OrganizationOut:
        org = await self._org(id_)
        before = OrganizationOut.model_validate(org)
        data = body.model_dump(exclude_unset=True, exclude={"version"})
        await self.orgs.update(org, expected_version=expected, updated_by=user.user_id, **data)
        await self.db.refresh(org)
        out = OrganizationOut.model_validate(org)
        await self._record("organization", "organizations", org, "updated", "update", before, out)
        return out

    async def archive_org(self, user: Principal, id_: uuid.UUID) -> None:
        org = await self._org(id_)
        if n := await self.orgs.live_departments(org.id):
            raise _rule("organization still has live departments", "has_live_children",
                        departments=n)  # fmt: skip
        before = OrganizationOut.model_validate(org)
        await self.orgs.update(org, valid_to=self._end(org.valid_from),
                               deleted_at=datetime.now(UTC), updated_by=user.user_id)  # fmt: skip
        await self._record("organization", "organizations", org, "archived", "archive", before)

    # ---------- teams (EP-ORG-11..15) ----------
    async def list_teams(
        self, user: Principal, page: PageParams, *, department_id: uuid.UUID | None,
        as_of: date | None,
    ) -> tuple[list[TeamOut], int]:  # fmt: skip
        seen = await self._visible_departments(user)
        if department_id is not None and seen is not None and department_id not in seen:
            raise deny("department", department_id=department_id)
        where = []
        if department_id is not None:
            where.append(Team.department_id == department_id)
        elif seen is not None:
            where.append(Team.department_id.in_(seen))
        if as_of is not None:
            where.append(Team.valid_from <= as_of)
        rows, total = await self.teams.list_page(limit=page.limit, offset=page.offset,
                                                 sort_by=page.sort_by, order=page.order,
                                                 where=where)  # fmt: skip
        if as_of is not None:  # live rows are open (`valid_to` NULL) or ended in the future
            rows = [t for t in rows if t.valid_to is None or t.valid_to > as_of]
        return [TeamOut.model_validate(t) for t in rows], total

    async def _team(self, id_: uuid.UUID) -> Team:
        team = await self.teams.get(id_)
        if team is None:
            raise NotFoundError("team not found")
        return team

    async def get_team(self, user: Principal, id_: uuid.UUID) -> TeamOut:
        team = await self._team(id_)
        await self._check_visible(user, team.department_id)
        return TeamOut.model_validate(team)

    async def create_team(
        self, user: Principal, body: TeamCreate, *, source: str = "MANUAL"
    ) -> TeamOut:
        dept = await self._department(body.department_id)
        await self._employee(body.lead_employee_id, "lead_employee_id")
        if await self.teams.by_code_live(body.code):
            raise DuplicateResourceError("team code exists", details={"code": body.code})
        start = body.valid_from or today()
        if start < dept.valid_from:
            raise _rule("valid_from before the department", "before_parent", "valid_from")
        team = Team(department_id=dept.id, code=body.code, name=body.name,
                    lead_employee_id=body.lead_employee_id, valid_from=start, source=source,
                    created_by=user.user_id)  # fmt: skip
        self.db.add(team)
        await self._flush("team")
        await self.db.refresh(team)
        out = TeamOut.model_validate(team)
        await self._record("team", "teams", team, "created", "create", after=out,
                           department_id=dept.id, valid_from=start)  # fmt: skip
        return out

    async def update_team(
        self, user: Principal, id_: uuid.UUID, body: TeamUpdate, expected: int
    ) -> TeamOut:
        team = await self._team(id_)
        data = body.model_dump(exclude_unset=True, exclude={"version"})
        if "code" in data and await self.teams.by_code_live(data["code"], exclude=team.id):
            raise DuplicateResourceError("team code exists", details={"code": data["code"]})
        await self._employee(data.get("lead_employee_id"), "lead_employee_id")
        before = TeamOut.model_validate(team)
        await self.teams.update(team, expected_version=expected, updated_by=user.user_id, **data)
        await self._flush("team")
        await self.db.refresh(team)
        out = TeamOut.model_validate(team)
        await self._record("team", "teams", team, "updated", "update", before, out,
                           department_id=team.department_id)  # fmt: skip
        return out

    async def archive_team(self, user: Principal, id_: uuid.UUID) -> None:
        team = await self._team(id_)
        if n := await self.teams.current_assignments(team.id):
            raise _rule("team still has current assignments", "has_live_children", assignments=n)
        before = TeamOut.model_validate(team)
        await self.teams.update(team, valid_to=self._end(team.valid_from),
                                deleted_at=datetime.now(UTC), updated_by=user.user_id)  # fmt: skip
        await self._record("team", "teams", team, "archived", "archive", before,
                           department_id=team.department_id)  # fmt: skip

    # ---------- positions (EP-ORG-16..20) ----------
    async def _position_out(self, rows: Sequence[Position]) -> list[PositionOut]:
        filled = await self.positions.filled([p.id for p in rows])
        out = []
        for p in rows:
            n = filled.get(p.id, 0)
            out.append(PositionOut(
                id=p.id, version=p.version, created_at=p.created_at, updated_at=p.updated_at,
                department_id=p.department_id, code=p.code, title=p.title, level=p.level,
                headcount_budget=p.headcount_budget,
                reports_to_position_id=p.reports_to_position_id, filled=n,
                vacant=max(p.headcount_budget - n, 0),
            ))  # fmt: skip
        return out

    async def list_positions(
        self, user: Principal, page: PageParams, *, department_id: uuid.UUID | None,
        q: str | None,
    ) -> tuple[list[PositionOut], int]:  # fmt: skip
        seen = await self._visible_departments(user)
        if department_id is not None and seen is not None and department_id not in seen:
            raise deny("department", department_id=department_id)
        where = []
        if department_id is not None:
            where.append(Position.department_id == department_id)
        elif seen is not None:
            where.append(Position.department_id.in_(seen))
        if q:
            where.append(Position.title.ilike(f"%{q}%"))
        rows, total = await self.positions.list_page(limit=page.limit, offset=page.offset,
                                                     sort_by=page.sort_by, order=page.order,
                                                     where=where)  # fmt: skip
        return await self._position_out(rows), total

    async def _position(self, id_: uuid.UUID) -> Position:
        pos = await self.positions.get(id_)
        if pos is None:
            raise NotFoundError("position not found")
        return pos

    async def get_position(self, user: Principal, id_: uuid.UUID) -> PositionOut:
        pos = await self._position(id_)
        await self._check_visible(user, pos.department_id)
        return (await self._position_out([pos]))[0]

    async def _reports_to(self, id_: uuid.UUID | None, own: uuid.UUID | None = None) -> None:
        if id_ is None:
            return
        if id_ == own:
            raise _rule("position cannot report to itself", "parent_cycle",
                        "reports_to_position_id")  # fmt: skip
        if await self.positions.get(id_) is None:
            raise _rule("position not found", "not_found", "reports_to_position_id")

    async def create_position(
        self, user: Principal, body: PositionCreate, *, source: str = "MANUAL"
    ) -> PositionOut:
        await self._department(body.department_id)
        await self._reports_to(body.reports_to_position_id)
        if await self.positions.code_taken(body.code):
            raise DuplicateResourceError("position code exists", details={"code": body.code})
        pos = Position(department_id=body.department_id, code=body.code, title=body.title,
                       level=body.level, headcount_budget=body.headcount_budget,
                       reports_to_position_id=body.reports_to_position_id, source=source,
                       created_by=user.user_id)  # fmt: skip
        self.db.add(pos)
        await self._flush("position")
        await self.db.refresh(pos)
        out = (await self._position_out([pos]))[0]
        await self._record("position", "positions", pos, "created", "create", after=out,
                           department_id=pos.department_id)  # fmt: skip
        return out

    async def update_position(
        self, user: Principal, id_: uuid.UUID, body: PositionUpdate, expected: int
    ) -> PositionOut:
        pos = await self._position(id_)
        data = body.model_dump(exclude_unset=True, exclude={"version"})
        await self._reports_to(data.get("reports_to_position_id"), pos.id)
        before = (await self._position_out([pos]))[0]
        await self.positions.update(pos, expected_version=expected, updated_by=user.user_id,
                                    **data)  # fmt: skip
        await self.db.refresh(pos)
        out = (await self._position_out([pos]))[0]
        await self._record("position", "positions", pos, "updated", "update", before, out,
                           department_id=pos.department_id)  # fmt: skip
        return out

    async def archive_position(self, user: Principal, id_: uuid.UUID) -> None:
        pos = await self._position(id_)
        if n := (await self.positions.filled([pos.id])).get(pos.id, 0):
            raise _rule("position still has current assignments", "has_live_children",
                        assignments=n)  # fmt: skip
        before = (await self._position_out([pos]))[0]
        await self.positions.update(pos, deleted_at=datetime.now(UTC), updated_by=user.user_id)
        await self._record("position", "positions", pos, "archived", "archive", before,
                           department_id=pos.department_id)  # fmt: skip

    # ---------- tree (EP-ORG-24) ----------
    async def tree(
        self, user: Principal, as_of: date, organization_id: uuid.UUID | None
    ) -> OrgTreeOut:
        seen = await self._visible_departments(user)
        if organization_id is not None:
            org = await self.orgs.get_any(organization_id)
            if org is None:
                raise NotFoundError("organization not found")
        else:
            found = await self.orgs.first_at(as_of)
            if found is None:
                live = await self.orgs.live()
                found = live[0] if live else None
            if found is None:
                raise NotFoundError("organization not found")
            org = found
        depts = [d for d in await self.depts.at(as_of, organization_id=org.id)
                 if seen is None or d.id in seen]  # fmt: skip
        ids = [d.id for d in depts]
        teams = [t for t in await self.teams.at(as_of) if t.department_id in set(ids)]
        members = await TreeRepository(self.db).members_at(as_of, ids)
        by_dept: dict[uuid.UUID, list[TreeMember]] = {i: [] for i in ids}
        team_count: dict[uuid.UUID, int] = {}
        for a, code, name, title in members:
            by_dept[a.department_id].append(TreeMember(
                employee_id=a.employee_id, employee_code=code, full_name=name, team_id=a.team_id,
                position_id=a.position_id, position_title=title, manager_id=a.manager_id,
            ))  # fmt: skip
            if a.team_id is not None:
                team_count[a.team_id] = team_count.get(a.team_id, 0) + 1
        return OrgTreeOut(
            as_of=as_of,
            organization=TreeOrganization(id=org.id, code=org.code, name=org.name),
            departments=[
                TreeDepartment(
                    id=d.id, code=d.code, name=d.name, parent_id=d.parent_id,
                    manager_id=d.head_employee_id, headcount=len(by_dept[d.id]),
                    teams=[TreeTeam(id=t.id, code=t.code, name=t.name,
                                    lead_employee_id=t.lead_employee_id,
                                    headcount=team_count.get(t.id, 0))
                           for t in teams if t.department_id == d.id],
                    members=by_dept[d.id],
                )
                for d in depts
            ],
        )  # fmt: skip


async def department_subtree(db: AsyncSession, roots: Iterable[uuid.UUID]) -> set[uuid.UUID]:
    """`core.org_scope` provider (registered by `app.modules.hr`)."""
    return await StructureService(db).subtree_ids(roots)
