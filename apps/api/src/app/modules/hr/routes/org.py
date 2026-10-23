"""HTTP routes for D01 Organization — EP-ORG-01..05, 11..24 (10 §7.2.1, M1.2 T-613).

Departments stay on `/hr/departments` (EP-ORG-06..10, R-DEC-29) in `router.py`. Reads =
`hr:read`, writes = `hr:admin` (R-DEC-30); both with pillar isolation (DIR only khối O).
"""

import uuid
from datetime import date
from typing import Annotated, Any

from fastapi import Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.concurrency import IfMatch, expected_version
from app.core.deps import Principal, get_db, require_pillar_permission
from app.core.envelope import Page
from app.core.errors import BadRequestError
from app.core.idempotency import Idem
from app.core.pagination import PageParams, page_params
from app.core.routing import EnvelopeRouter
from app.modules.hr.schemas.org import (
    AssignmentCreate,
    AssignmentUpdate,
    EmployeeAssignmentOut,
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
)
from app.modules.hr.services.org_service import OrgService, Placement
from app.modules.hr.services.scope import structure_scope
from app.modules.hr.services.structure_service import StructureService, today

router = EnvelopeRouter(tags=["org"])

Db = Annotated[AsyncSession, Depends(get_db)]
Reader = Annotated[Principal, Depends(require_pillar_permission("hr:read"))]
Admin = Annotated[Principal, Depends(require_pillar_permission("hr:admin"))]


def parse_as_of(as_of: str | None) -> date | None:
    """`YYYY-MM-DD` or None; anything else → `400 BAD_REQUEST` (EP-ORG-24)."""
    if as_of is None:
        return None
    try:
        return date.fromisoformat(as_of)
    except ValueError as exc:
        raise BadRequestError("as_of must be YYYY-MM-DD", details={"param": "as_of"}) from exc


async def as_of_dep(as_of: str | None = None) -> date | None:
    return parse_as_of(as_of)


AsOf = Annotated[date | None, Depends(as_of_dep)]


def _page(items: list[Any], total: int, page: PageParams) -> Page[Any]:
    return Page(items=items, total=total, limit=page.limit, offset=page.offset)


# ---------- EP-ORG-01..05 organizations ----------
@router.get("/org/organizations", response_model=list[OrganizationOut])
async def list_organizations(
    db: Db, user: Reader, page: Annotated[PageParams, Depends(page_params("name", "code"))],
    q: str | None = None, include_archived: bool = False,
) -> Any:  # fmt: skip
    svc = StructureService(db)
    items, total = await svc.list_orgs(user, page, q=q, include_archived=include_archived)
    return _page(items, total, page)


@router.post("/org/organizations", response_model=OrganizationOut, status_code=201)
async def create_organization(body: OrganizationCreate, db: Db, user: Admin, idem: Idem) -> Any:
    if (hit := await idem.replay(body)) is not None:
        return OrganizationOut.model_validate(hit)
    out = await StructureService(db).create_org(user, body)
    await db.commit()
    await idem.remember(out)
    return out


@router.get("/org/organizations/{organization_id}", response_model=OrganizationOut)
async def get_organization(organization_id: uuid.UUID, db: Db, user: Reader) -> Any:
    return await StructureService(db).get_org(user, organization_id)


@router.patch("/org/organizations/{organization_id}", response_model=OrganizationOut)
async def update_organization(
    organization_id: uuid.UUID, body: OrganizationUpdate, db: Db, user: Admin,
    if_match: IfMatch = None,
) -> Any:  # fmt: skip
    exp = expected_version(if_match, body.version)
    out = await StructureService(db).update_org(user, organization_id, body, exp)
    await db.commit()
    return out


@router.delete("/org/organizations/{organization_id}", status_code=204, response_class=Response)
async def archive_organization(organization_id: uuid.UUID, db: Db, user: Admin) -> Response:
    await StructureService(db).archive_org(user, organization_id)
    await db.commit()
    return Response(status_code=204)


# ---------- EP-ORG-11..15 teams ----------
@router.get("/org/teams", response_model=list[TeamOut])
async def list_teams(
    db: Db, user: Reader, as_of: AsOf,
    page: Annotated[PageParams, Depends(page_params("name", "code", "valid_from"))],
    department_id: uuid.UUID | None = None,
) -> Any:  # fmt: skip
    items, total = await StructureService(db).list_teams(user, page, department_id=department_id,
                                                         as_of=as_of)  # fmt: skip
    return _page(items, total, page)


@router.post("/org/teams", response_model=TeamOut, status_code=201)
async def create_team(body: TeamCreate, db: Db, user: Admin, idem: Idem) -> Any:
    if (hit := await idem.replay(body)) is not None:
        return TeamOut.model_validate(hit)
    out = await StructureService(db).create_team(user, body)
    await db.commit()
    await idem.remember(out)
    return out


@router.get("/org/teams/{team_id}", response_model=TeamOut)
async def get_team(team_id: uuid.UUID, db: Db, user: Reader) -> Any:
    return await StructureService(db).get_team(user, team_id)


@router.patch("/org/teams/{team_id}", response_model=TeamOut)
async def update_team(
    team_id: uuid.UUID, body: TeamUpdate, db: Db, user: Admin, if_match: IfMatch = None
) -> Any:
    exp = expected_version(if_match, body.version)
    out = await StructureService(db).update_team(user, team_id, body, exp)
    await db.commit()
    return out


@router.delete("/org/teams/{team_id}", status_code=204, response_class=Response)
async def archive_team(team_id: uuid.UUID, db: Db, user: Admin) -> Response:
    await StructureService(db).archive_team(user, team_id)
    await db.commit()
    return Response(status_code=204)


# ---------- EP-ORG-16..20 positions ----------
@router.get("/org/positions", response_model=list[PositionOut])
async def list_positions(
    db: Db, user: Reader,
    page: Annotated[PageParams, Depends(page_params("title", "code"))],
    department_id: uuid.UUID | None = None, q: str | None = None,
) -> Any:  # fmt: skip
    svc = StructureService(db)
    items, total = await svc.list_positions(user, page, department_id=department_id, q=q)
    return _page(items, total, page)


@router.post("/org/positions", response_model=PositionOut, status_code=201)
async def create_position(body: PositionCreate, db: Db, user: Admin, idem: Idem) -> Any:
    if (hit := await idem.replay(body)) is not None:
        return PositionOut.model_validate(hit)
    out = await StructureService(db).create_position(user, body)
    await db.commit()
    await idem.remember(out)
    return out


@router.get("/org/positions/{position_id}", response_model=PositionOut)
async def get_position(position_id: uuid.UUID, db: Db, user: Reader) -> Any:
    return await StructureService(db).get_position(user, position_id)


@router.patch("/org/positions/{position_id}", response_model=PositionOut)
async def update_position(
    position_id: uuid.UUID, body: PositionUpdate, db: Db, user: Admin, if_match: IfMatch = None
) -> Any:
    exp = expected_version(if_match, body.version)
    out = await StructureService(db).update_position(user, position_id, body, exp)
    await db.commit()
    return out


@router.delete("/org/positions/{position_id}", status_code=204, response_class=Response)
async def archive_position(position_id: uuid.UUID, db: Db, user: Admin) -> Response:
    await StructureService(db).archive_position(user, position_id)
    await db.commit()
    return Response(status_code=204)


# ---------- EP-ORG-21..23 assignments ----------
@router.get("/org/assignments", response_model=list[EmployeeAssignmentOut])
async def list_assignments(
    db: Db, user: Reader, as_of: AsOf,
    page: Annotated[PageParams, Depends(page_params("valid_from"))],
    employee_id: uuid.UUID | None = None, department_id: uuid.UUID | None = None,
) -> Any:  # fmt: skip
    rows, total = await OrgService(db).list_scoped(
        structure_scope(user), employee_id=employee_id, department_id=department_id,
        as_of=as_of, limit=page.limit, offset=page.offset,
    )  # fmt: skip
    return _page([EmployeeAssignmentOut.model_validate(a) for a in rows], total, page)


@router.post("/org/assignments", response_model=EmployeeAssignmentOut, status_code=201)
async def create_assignment(body: AssignmentCreate, db: Db, user: Admin, idem: Idem) -> Any:
    if (hit := await idem.replay(body)) is not None:
        return EmployeeAssignmentOut.model_validate(hit)
    placement = Placement(body.department_id, body.team_id, body.position_id, body.manager_id)
    a = await OrgService(db).assign(body.employee_id, placement, body.valid_from,
                                    actor=user.user_id, reason=body.reason)  # fmt: skip
    await db.refresh(a)
    out = EmployeeAssignmentOut.model_validate(a)
    await db.commit()
    await idem.remember(out)
    return out


@router.patch("/org/assignments/{assignment_id}", response_model=EmployeeAssignmentOut)
async def update_assignment(
    assignment_id: uuid.UUID, body: AssignmentUpdate, db: Db, user: Admin,
    if_match: IfMatch = None,
) -> Any:  # fmt: skip
    exp = expected_version(if_match, body.version)
    data = body.model_dump(exclude_unset=True, exclude={"version"})
    a = await OrgService(db).update(assignment_id, data, exp, actor=user.user_id)
    await db.refresh(a)
    out = EmployeeAssignmentOut.model_validate(a)
    await db.commit()
    return out


# ---------- EP-ORG-24 tree ----------
@router.get("/org/tree", response_model=OrgTreeOut)
async def org_tree(
    db: Db, user: Reader, as_of: AsOf, organization_id: uuid.UUID | None = None
) -> Any:
    return await StructureService(db).tree(user, as_of or today(), organization_id)
