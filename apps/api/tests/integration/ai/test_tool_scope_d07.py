"""AI record tools apply the REST data scope (D-07 R-DEC-183, D-20 R-DEC-199, P06).

TC-V4-24: through `TOOL-list_invoices` a MGR sees only the invoices they created (like
`GET /finance/invoices`), a REV is refused with `FORBIDDEN_SCOPE` and no data reaches the model;
the expense / budget / deal tools refuse a REV the same way.
"""

import uuid

import pytest
from sqlalchemy import select, update

from app.core.deps import Principal
from app.modules.ai.services.tool_executor import ToolExecutor
from app.modules.auth.permission_matrix import ROLE_PERMISSIONS
from app.modules.finance.models import Invoice

pytestmark = pytest.mark.integration


def _who(role: str, uid: uuid.UUID | None = None) -> Principal:
    return Principal(user_id=uid or uuid.uuid4(), role=role, department_id=uuid.uuid4(),
                     permissions=frozenset(ROLE_PERMISSIONS[role]))  # fmt: skip


async def test_manager_lists_only_own_invoices_through_the_tool(db_session) -> None:
    uid = uuid.uuid4()
    own = (await db_session.execute(select(Invoice.id).limit(1))).scalar_one()
    await db_session.execute(update(Invoice).where(Invoice.id == own).values(created_by=uid))
    await db_session.flush()
    result = await ToolExecutor(db_session, _who("MGR", uid)).run("TOOL-list_invoices",
                                                                   {"limit": 50})  # fmt: skip
    assert result.status == "ok", result.error_code
    assert result.data["total"] == 1
    assert [s.id for s in result.sources] == [str(own)]
    ceo = await ToolExecutor(db_session, _who("CEO")).run("TOOL-list_invoices", {"limit": 50})
    assert ceo.data["total"] > 1  # the company view is unchanged for the CEO


@pytest.mark.parametrize(
    ("tool", "code"),
    [("TOOL-list_invoices", "FORBIDDEN_SCOPE"), ("TOOL-list_expenses", "FORBIDDEN_SCOPE"),
     ("TOOL-list_deals", "FORBIDDEN_SCOPE"),
     ("TOOL-get_budget_status", "FORBIDDEN_ROLE")],  # needs finance:query, which REV lacks
)  # fmt: skip
async def test_reviewer_is_refused_without_data(db_session, tool: str, code: str) -> None:
    rev = _who("REV")
    assert {"finance:read", "sales:read"} <= rev.permissions  # the permission alone is not scope
    result = await ToolExecutor(db_session, rev).run(tool, {})
    assert (result.status, result.error_code) == ("forbidden", code)
    assert result.data == {} and result.sources == []
