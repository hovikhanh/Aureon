"""E2E support (T-643): undo / retire the D03 captures of `capture.spec.ts` on the dev DB.

The real-stack spec imports `DOC-06-danh-sach-nhan-su.xlsx` (C5, HR_ROSTER) and enters C1
PLAN_KPI_OKR rows whose `task_title` starts with `E2E capture `. Cleanup goes through the
product's own undo (R-DEC-66, `UndoService` as the seeded CEO) so targets, lineage and the
outbox follow the normal path; every touched document is then soft-deleted so the inbox /
review queue of later runs (and backend tests) start clean. Dev DB only, fake demo data
(CLAUDE §6.6 #8/#9); the audit log and outbox are append-only and kept. Idempotent; prints
`{"undone": n, "retired": m}`.

Run: PYTHONPATH=apps/api/src:apps/api .venv/bin/python apps/web/e2e/support/capture_e2e.py --cleanup
"""

from __future__ import annotations

import asyncio
import json
import sys
import uuid

from sqlalchemy import text

from app.core.base_model import DEFAULT_TENANT_ID
from app.core.config import get_config
from app.core.db import get_sessionmaker
from app.core.deps import Principal
from app.core.tenant import tenant_scope
from app.modules.auth.permission_matrix import ROLE_PERMISSIONS
from app.modules.auth.repositories import UserRepository
from app.modules.idp.schemas.capture import UndoIn
from app.modules.idp.services.undo_service import UndoService

# literal SQL (no string building): the E2E captures = DOC-06 imports + C1 rows `E2E capture %`
E2E_DOCS = text("""
    SELECT id, status FROM idp.source_documents
    WHERE deleted_at IS NULL
      AND ((channel = 'C5' AND original_filename = 'DOC-06-danh-sach-nhan-su.xlsx')
           OR (channel = 'C1' AND manual_payload::text LIKE '%E2E capture %'))
    ORDER BY submitted_at DESC""")
RETIRE = text("""
    UPDATE idp.source_documents SET deleted_at = now()
    WHERE id = ANY(:ids) AND deleted_at IS NULL""")


async def cleanup() -> dict[str, int]:
    get_config()
    async with get_sessionmaker()() as db:
        ceo = await UserRepository(db).by_email("ceo@abc.demo")
        assert ceo is not None, "seeded ceo@abc.demo missing"
        user = Principal(user_id=ceo.id, role="CEO", permissions=frozenset(ROLE_PERMISSIONS["CEO"]),
                         department_id=ceo.department_id, tenant_id=DEFAULT_TENANT_ID)  # fmt: skip
        rows = (await db.execute(E2E_DOCS)).all()
        undone = 0
        for doc_id, status in rows:  # newest first: later imports never block older undos
            if status == "COMMITTED":
                body = UndoIn(reason="E2E cleanup", reason_code="mistake")
                await UndoService(db).undo(user, uuid.UUID(str(doc_id)), body)
                undone += 1
        ids = [r[0] for r in rows]
        retired = (await db.execute(RETIRE, {"ids": ids})).rowcount if ids else 0  # type: ignore[attr-defined]
        await db.commit()
    return {"undone": undone, "retired": retired}


if __name__ == "__main__":
    if "--cleanup" not in sys.argv:
        raise SystemExit("usage: capture_e2e.py --cleanup")
    with tenant_scope(DEFAULT_TENANT_ID):
        print(json.dumps(asyncio.run(cleanup())))
