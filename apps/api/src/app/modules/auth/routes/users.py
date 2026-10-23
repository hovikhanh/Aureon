"""EP-ADM-05..11 — user & role administration (M1.2 T-614, 10 §7.2.1).

Owned by module `auth` (identity data), mounted at `/platform/users` + `/platform/roles`
(07 §1.1). Reads = `platform:read`, writes = `platform:admin` — one permission each.
"""

import uuid
from typing import Annotated, Any

from fastapi import Depends

from app.core.concurrency import IfMatch, expected_version
from app.core.deps import DbSession, Principal, require_permission
from app.core.envelope import Page
from app.core.idempotency import Idem
from app.core.pagination import PageParams, page_params
from app.core.routing import EnvelopeRouter
from app.modules.auth.schemas import ReasonIn, RoleOut, UserAdminOut, UserCreate, UserUpdate
from app.modules.auth.services.user_admin_service import UserAdminService

router = EnvelopeRouter(prefix="/platform", tags=["admin"])

Reader = Annotated[Principal, Depends(require_permission("platform:read"))]
Admin = Annotated[Principal, Depends(require_permission("platform:admin"))]
UserPage = Annotated[PageParams, Depends(page_params("email", "full_name", "created_at"))]


@router.get("/users", response_model=list[UserAdminOut], summary="EP-ADM-05 List users")
async def list_users(
    db: DbSession, _: Reader, page: UserPage, role_code: str | None = None,
    is_active: bool | None = None, department_id: uuid.UUID | None = None, q: str | None = None,
) -> Any:  # fmt: skip
    items, total = await UserAdminService(db).list_users(
        page, role_code=role_code, is_active=is_active, department_id=department_id, q=q
    )
    return Page(items=items, total=total, limit=page.limit, offset=page.offset)


@router.post("/users", response_model=UserAdminOut, status_code=201, summary="EP-ADM-06")
async def create_user(body: UserCreate, db: DbSession, user: Admin, idem: Idem) -> Any:
    if (hit := await idem.replay(body)) is not None:
        return UserAdminOut.model_validate(hit)
    out = await UserAdminService(db).create(user, body)
    await db.commit()
    await idem.remember(out)
    return out


@router.get("/users/{user_id}", response_model=UserAdminOut, summary="EP-ADM-07")
async def get_user(user_id: uuid.UUID, db: DbSession, _: Reader) -> Any:
    return await UserAdminService(db).get(user_id)


@router.patch("/users/{user_id}", response_model=UserAdminOut, summary="EP-ADM-08")
async def update_user(
    user_id: uuid.UUID, body: UserUpdate, db: DbSession, user: Admin, if_match: IfMatch = None
) -> Any:
    exp = expected_version(if_match, body.version)
    out = await UserAdminService(db).update(user, user_id, body, exp)
    await db.commit()
    return out


async def _set_active(
    db: DbSession, user: Principal, idem: Any, user_id: uuid.UUID, body: ReasonIn, active: bool
) -> Any:
    if (hit := await idem.replay(body)) is not None:
        return UserAdminOut.model_validate(hit)
    out = await UserAdminService(db).set_active(user, user_id, active, body.reason)
    await db.commit()
    await idem.remember(out)
    return out


@router.post("/users/{user_id}/deactivate", response_model=UserAdminOut, summary="EP-ADM-09")
async def deactivate_user(
    user_id: uuid.UUID, body: ReasonIn, db: DbSession, user: Admin, idem: Idem
) -> Any:
    return await _set_active(db, user, idem, user_id, body, False)


@router.post("/users/{user_id}/reactivate", response_model=UserAdminOut, summary="EP-ADM-10")
async def reactivate_user(
    user_id: uuid.UUID, body: ReasonIn, db: DbSession, user: Admin, idem: Idem
) -> Any:
    return await _set_active(db, user, idem, user_id, body, True)


@router.get("/roles", response_model=list[RoleOut], summary="EP-ADM-11 Roles (read-only)")
async def list_roles(db: DbSession, _: Reader) -> Any:
    return await UserAdminService(db).roles_list()
