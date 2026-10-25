"""E2E support (T-625): undo the D11/D04 writes of `work.spec.ts` on the dev DB.

The spec creates tasks titled `E2E work *` (MGR assigns, EMP asks to reassign, MGR approves).
Cleanup works at the DB level — dev DB only, fake demo data (CLAUDE §6.6 #8/#9); the audit log is
append-only (and `audit_logs` references `approval_requests`), so nothing there is deleted:
  * approval requests on those tasks: PENDING → CANCELLED, then soft-deleted;
  * notifications about those tasks / requests: deleted (per-user inbox rows, not audit);
  * dependencies + the tasks themselves: soft-deleted (workload / lists ignore them).
Idempotent; prints `{"tasks": n, "approvals": m, "notifications": k}`.

Run: PYTHONPATH=apps/api/src:apps/api .venv/bin/python apps/web/e2e/support/work_e2e.py --cleanup
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

# literal SQL (no string building): E2E tasks = title `E2E work %`, live rows only
STEPS = (
    ("notifications", text("""
        DELETE FROM platform.notifications
        WHERE ref_id IN (SELECT id FROM execution.tasks WHERE title LIKE 'E2E work %')
           OR ref_id IN (SELECT r.id FROM platform.approval_requests r
                         JOIN execution.tasks t ON t.id = r.target_id
                         WHERE r.target_kind = 'task_reassign' AND t.title LIKE 'E2E work %')""")),
    ("approvals", text("""
        UPDATE platform.approval_requests r SET deleted_at = now(),
               status = CASE WHEN r.status = 'PENDING' THEN 'CANCELLED' ELSE r.status END
        FROM execution.tasks t
        WHERE t.id = r.target_id AND r.target_kind = 'task_reassign'
          AND r.deleted_at IS NULL AND t.title LIKE 'E2E work %'""")),
    ("dependencies", text("""
        UPDATE execution.task_dependencies d SET deleted_at = now()
        FROM execution.tasks t
        WHERE d.deleted_at IS NULL AND t.title LIKE 'E2E work %'
          AND t.id IN (d.task_id, d.depends_on_task_id)""")),
    ("tasks", text("""
        UPDATE execution.tasks SET deleted_at = now()
        WHERE title LIKE 'E2E work %' AND deleted_at IS NULL""")),
)  # fmt: skip


async def cleanup() -> dict[str, int]:
    get_config()
    out: dict[str, int] = {}
    async with get_sessionmaker()() as db:
        for name, stmt in STEPS:
            out[name] = (await db.execute(stmt)).rowcount  # type: ignore[attr-defined]
        await db.commit()
    return out


if __name__ == "__main__":
    if "--cleanup" not in sys.argv:
        raise SystemExit("usage: work_e2e.py --cleanup")
    with tenant_scope(DEFAULT_TENANT_ID):
        print(json.dumps(asyncio.run(cleanup())))
