"""E2E support (T-633): undo the D07–D10 writes of `goals.spec.ts` on the dev DB.

The real-stack spec writes KR check-ins whose note starts with `E2E goals ` (EMP on its own KR,
DIR Sales on OKR-SAL #0 → at risk → `alert` through the Celery consumer). Check-ins are
append-only in the API, so cleanup works at the DB level — dev DB only, fake demo data
(CLAUDE §6.6 #8/#9); the audit log and outbox/processed events are append-only and kept:
  * `alert` notifications about the touched KRs: deleted (per-user inbox rows, not audit);
  * KR measurements + check-ins of the E2E notes: deleted;
  * KR columns / at-risk flags / objective progress: restored by re-running the idempotent
    `seed_goals` (same values as `python -m app.seed`).
Idempotent; prints `{"notifications": n, "kr_measurements": m, "check_ins": k}`.

Run: PYTHONPATH=apps/api/src:apps/api .venv/bin/python apps/web/e2e/support/goals_e2e.py --cleanup
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
from app.seed.goals_seed import seed_goals

# literal SQL (no string building): E2E check-ins = note `E2E goals %`
E2E_KRS = "SELECT key_result_id FROM execution.check_ins WHERE note LIKE 'E2E goals %'"
STEPS = (
    ("notifications", text(f"""
        DELETE FROM platform.notifications
        WHERE kind = 'alert' AND ref_table = 'key_results' AND ref_id IN ({E2E_KRS})""")),
    ("kr_measurements", text("""
        DELETE FROM execution.kr_measurements
        WHERE check_in_id IN (SELECT id FROM execution.check_ins
                              WHERE note LIKE 'E2E goals %')""")),
    ("check_ins", text("DELETE FROM execution.check_ins WHERE note LIKE 'E2E goals %'")),
)  # fmt: skip
CEO = text("SELECT id FROM auth.users WHERE email = 'ceo@abc.demo'")


async def cleanup() -> dict[str, int]:
    get_config()
    out: dict[str, int] = {}
    async with get_sessionmaker()() as db:
        for name, stmt in STEPS:
            out[name] = (await db.execute(stmt)).rowcount  # type: ignore[attr-defined]
        await seed_goals(db, (await db.execute(CEO)).scalar_one())
        await db.commit()
    return out


if __name__ == "__main__":
    if "--cleanup" not in sys.argv:
        raise SystemExit("usage: goals_e2e.py --cleanup")
    with tenant_scope(DEFAULT_TENANT_ID):
        print(json.dumps(asyncio.run(cleanup())))
