"""`auth` source of the onboarding `progress` (EP-ADM-13, `core/onboarding`) — counts/ids only."""

from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.models import Role, User


async def auth_progress(db: AsyncSession) -> dict[str, Any]:
    live = (User.deleted_at.is_(None), User.is_service_account.is_(False))
    by_role = await db.execute(
        select(Role.code, func.count(User.id)).join(Role, Role.id == User.role_id)
        .where(*live, User.is_active.is_(True)).group_by(Role.code)
    )  # fmt: skip
    linked = await db.execute(select(User.employee_id).where(*live, User.employee_id.is_not(None)))
    return {
        "users_by_role": {code: int(n) for code, n in by_role.all()},
        "user_employee_ids": set(linked.scalars()),
    }
