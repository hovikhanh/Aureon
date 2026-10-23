"""E2E support (T-618): undo the org-structure changes of `admin-org.spec.ts` on the dev DB.

The spec creates departments with code `E2E-*` and assigns one employee there "from today".
EP-ORG-22 cannot move the employee back on the same day (`not_after_current`), so cleanup
works at the DB level — dev DB only, fake demo data (CLAUDE §6.6 #8/#9):
  * delete the assignments into `E2E-*` departments, re-open the assignment they closed and
    restore the employee's cached placement from it;
  * delete teams / positions / departments `E2E-*`.
Idempotent; prints `{"departments": n, "assignments": m}`.

Run: PYTHONPATH=apps/api/src:apps/api .venv/bin/python apps/web/e2e/support/org_e2e.py --cleanup
"""

from __future__ import annotations

import asyncio
import json
import sys

from sqlalchemy import text

from app.core.base_model import DEFAULT_TENANT_ID
from app.core.config import get_config
from app.core.db import get_sessionmaker
from app.core.tenant import tenant_scope

FIND = text(
    "SELECT id, employee_id, valid_from FROM hr.employee_assignments "
    "WHERE department_id IN (SELECT id FROM hr.departments WHERE code LIKE 'E2E-%')"
)
DROP_ASSIGNMENT = text("DELETE FROM hr.employee_assignments WHERE id = :id")
REOPEN = text(
    "UPDATE hr.employee_assignments SET valid_to = NULL "
    "WHERE employee_id = :e AND valid_to = :d AND deleted_at IS NULL "
    "RETURNING department_id, team_id, position_id, manager_id"
)
RESTORE_CACHE = text(
    "UPDATE hr.employees SET department_id = :department_id, team_id = :team_id, "
    "position_id = :position_id, manager_id = :manager_id WHERE id = :e"
)
DROP_CHILDREN = (
    text(
        "DELETE FROM hr.positions WHERE department_id IN "
        "(SELECT id FROM hr.departments WHERE code LIKE 'E2E-%')"
    ),
    text(
        "DELETE FROM hr.teams WHERE department_id IN "
        "(SELECT id FROM hr.departments WHERE code LIKE 'E2E-%')"
    ),
)
DROP_DEPTS = text("DELETE FROM hr.departments WHERE code LIKE 'E2E-%'")


async def cleanup() -> dict[str, int]:
    get_config()
    async with get_sessionmaker()() as db:
        rows = (await db.execute(FIND)).all()
        for a_id, emp_id, start in rows:
            await db.execute(DROP_ASSIGNMENT, {"id": a_id})
            prev = (await db.execute(REOPEN, {"e": emp_id, "d": start})).mappings().first()
            if prev is not None:
                await db.execute(RESTORE_CACHE, {"e": emp_id, **prev})
        for stmt in DROP_CHILDREN:
            await db.execute(stmt)
        res = await db.execute(DROP_DEPTS)
        await db.commit()
    return {"departments": res.rowcount, "assignments": len(rows)}  # type: ignore[attr-defined]


if __name__ == "__main__":
    if "--cleanup" not in sys.argv:
        raise SystemExit("usage: org_e2e.py --cleanup")
    with tenant_scope(DEFAULT_TENANT_ID):
        print(json.dumps(asyncio.run(cleanup())))
