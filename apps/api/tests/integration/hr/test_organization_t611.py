"""T-611 — ENT-Organization + effective-dated departments/teams (05 §2.4, R-DEC-24).

TC-M12-01 (T-611 part): migration `0011` backfill — one live Organization per tenant, every
department linked to it, `valid_from` set, `code` unique per tenant among live rows only.
TC-M12-16 (T-611 part): another tenant may reuse a department code and never sees tenant A's
organization / departments.
"""

import uuid
from datetime import date

import pytest
from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.tenant import tenant_scope
from app.modules.hr.models import Department, Organization
from app.modules.hr.repositories import DepartmentRepository, OrganizationRepository
from app.seed.ids import seed_uuid
from tests.conftest import ApiClient
from tests.integration.hr.helpers import make_department, uniq

pytestmark = pytest.mark.integration

TENANT_B = uuid.UUID("00000000-0000-0000-0000-0000000000b2")
ABC = seed_uuid("organization", "ABC")


async def test_every_department_belongs_to_a_live_organization(db_session: AsyncSession) -> None:
    orgs = await OrganizationRepository(db_session).live()
    assert [o.id for o in orgs] == [ABC]
    orphans = await db_session.scalar(
        select(func.count()).select_from(Department).where(Department.organization_id.is_(None))
    )
    assert orphans == 0
    for sql in ("SELECT count(*) FROM hr.departments WHERE valid_from IS NULL",
                "SELECT count(*) FROM hr.teams WHERE valid_from IS NULL"):  # fmt: skip
        assert await db_session.scalar(text(sql)) == 0, sql


async def test_post_department_attaches_tenant_organization(api: ApiClient) -> None:
    d = await make_department(api)
    r = await api.call("GET", f"/hr/departments/{d['id']}", "CEO")
    assert r.status_code == 200, r.text


async def test_department_validity_range_is_checked(db_session: AsyncSession) -> None:
    bad = Department(
        organization_id=ABC, code=uniq("D"), name="x", aliases=[], source="MANUAL",
        valid_from=date(2026, 1, 2), valid_to=date(2026, 1, 1),
    )  # fmt: skip
    db_session.add(bad)
    with pytest.raises(IntegrityError, match="valid_to_after_valid_from"):
        await db_session.flush()
    await db_session.rollback()


async def test_code_unique_among_live_rows_only(db_session: AsyncSession) -> None:
    code = uniq("D")
    first = Department(organization_id=ABC, code=code, name="a", aliases=[], source="MANUAL",
                       valid_from=date(2026, 1, 1))  # fmt: skip
    db_session.add(first)
    await db_session.flush()
    first.deleted_at = func.now()
    first.valid_to = date(2026, 6, 1)
    await db_session.flush()
    again = Department(organization_id=ABC, code=code, name="b", aliases=[], source="MANUAL",
                       valid_from=date(2026, 6, 1))  # fmt: skip
    db_session.add(again)
    await db_session.flush()  # archived code is reusable
    live = await DepartmentRepository(db_session).by_code(code)
    assert live is not None and live.id == again.id


async def test_other_tenant_reuses_code_and_sees_nothing(db_session: AsyncSession) -> None:
    with tenant_scope(TENANT_B):
        assert await OrganizationRepository(db_session).live() == []
        assert await DepartmentRepository(db_session).get(seed_uuid("department", "SAL")) is None
        assert await DepartmentRepository(db_session).by_code("SAL") is None
        org = await OrganizationRepository(db_session).create(
            code="ABC", name="B corp", source="MANUAL", valid_from=date(2026, 1, 1)
        )
        dept = await DepartmentRepository(db_session).create(
            organization_id=org.id, code="SAL", name="B sales", aliases=[], source="MANUAL",
            valid_from=date(2026, 1, 1),
        )  # fmt: skip
        mine = await DepartmentRepository(db_session).by_code("SAL")
        assert mine is not None and mine.id == dept.id
    ours = await DepartmentRepository(db_session).by_code("SAL")
    assert ours is not None and ours.id == seed_uuid("department", "SAL")
    assert isinstance(await db_session.get(Organization, ABC), Organization)
