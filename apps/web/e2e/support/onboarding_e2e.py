"""E2E support (T-650): UC-07 onboarding on the real stack — `onboarding.spec.ts` (`@real-only`).

Sub-commands (dev DB only, fake demo data — CLAUDE §6.6 #8/#9; audit log / outbox kept):
  --expect     print the sample-file figures computed by `scripts/gen_demo_docs.py`
               (`uc07_expectations()` + per-department headcount) — the spec never hard-codes them.
  --chat EMAIL record the model-gateway fixtures of the /ask turn "create a task for me" for
               EMAIL (kill switch off → TOOL-create_task → L2 card; kill switch L0 → refused):
               `ChatService` runs with a scripted gateway in a rolled-back transaction, so the
               fixture keys are the exact `prompt_sha256` the API will compute. Files are marked
               `model = "e2e-onboarding"` under the runtime fixture dir (removed by --cleanup).
  --report     print the payload of the latest `platform.onboarding_completed` outbox event.
  --cleanup    kill switch off; E2E users (`@abc-e2e.demo`) deleted; E2E tasks retired; UC-07 /
               DOC-07 C5 imports undone (UndoService as the seeded CEO) then retired; e-mails of
               the undone employees cleared (global unique index); org `ABC-E2E` retired;
               `onboarding.state` restored to the seed `completed` state; fixtures removed.
               Idempotent; prints counts.

Run: PYTHONPATH=apps/api/src:apps/api .venv/bin/python \
       apps/web/e2e/support/onboarding_e2e.py --cleanup
"""

from __future__ import annotations

import asyncio
import json
import sys
import uuid
from pathlib import Path
from types import ModuleType
from typing import Any

from sqlalchemy import text

from app.core.base_model import DEFAULT_TENANT_ID
from app.core.config import get_config
from app.core.db import get_sessionmaker
from app.core.deps import Principal
from app.core.model_gateway.fixtures import DEFAULT_DIR, FixtureStore
from app.core.model_gateway.types import ChatRequest, ChatResponse, ToolCall
from app.core.tenant import tenant_scope
from app.modules.auth.permission_matrix import ROLE_PERMISSIONS
from app.modules.auth.repositories import UserRepository
from app.modules.idp.schemas.capture import UndoIn
from app.modules.idp.services.undo_service import UndoService
from app.modules.platform.services.settings_service import SystemSettingService
from app.seed.onboarding_seed import completed_state

ROOT = Path(__file__).resolve().parents[4]
MARK = "e2e-onboarding"
ASK = "Tạo việc cho tôi: gọi lại khách hàng ABC trước cuối tháng"
TASK_TITLE = "E2E onboarding gọi lại khách hàng ABC"
FILES = ("ABC_DanhSachNhanSu_Onboarding.xlsx", "DOC-07-kpi-okr-q4-2026.xlsx")

# literal SQL (no string building)
DOCS = text("""
    SELECT id, status FROM idp.source_documents
    WHERE deleted_at IS NULL AND channel = 'C5' AND original_filename = ANY(:files)
    ORDER BY submitted_at DESC""")
RETIRE_DOCS = text("UPDATE idp.source_documents SET deleted_at = now() WHERE id = ANY(:ids)")
USERS = text("SELECT id FROM auth.users WHERE email LIKE '%@abc-e2e.demo'")
DEL_TOKENS = text("DELETE FROM auth.refresh_tokens WHERE user_id = ANY(:ids)")
DEL_USERS = text("DELETE FROM auth.users WHERE id = ANY(:ids)")
TASKS = text("""
    UPDATE execution.tasks SET deleted_at = now()
    WHERE deleted_at IS NULL AND title LIKE 'E2E onboarding %'""")
EMAILS = text("""
    UPDATE hr.employees SET email = NULL
    WHERE deleted_at IS NOT NULL AND email LIKE '%@abc-e2e.demo'""")
ORG = text("""
    UPDATE hr.organizations SET deleted_at = now()
    WHERE deleted_at IS NULL AND code = 'ABC-E2E'""")
ADMIN = text("SELECT id FROM auth.users WHERE email = 'admin@abc.demo'")
COMPLETED = text("""
    SELECT payload FROM platform.outbox_events WHERE event_type = 'platform.onboarding_completed'
    ORDER BY occurred_at DESC LIMIT 1""")


def _generator() -> ModuleType:
    """`uc07_expectations()` without the demo dependency group (only the UC-07 slice)."""
    src = (ROOT / "scripts" / "gen_demo_docs.py").read_text(encoding="utf-8")
    mod = ModuleType("uc07")
    body = src[src.index("# UC-07 — onboarding roster") : src.index("def gen_uc07")]
    exec("from typing import Final\n" + body, mod.__dict__)  # noqa: S102 — repo file, not input
    return mod


def expect() -> dict[str, Any]:
    gen = _generator()
    return gen.uc07_expectations() | {  # type: ignore[no-any-return]
        "file": gen.UC07_FILE,
        "departments_list": [{"code": c, "name": n, "headcount": k} for c, n, k in gen.UC07_DEPTS],
    }


async def _ceo(db: Any) -> Principal:
    ceo = await UserRepository(db).by_email("ceo@abc.demo")
    if ceo is None:
        raise SystemExit("seeded ceo@abc.demo missing")
    return Principal(user_id=ceo.id, role="CEO", permissions=frozenset(ROLE_PERMISSIONS["CEO"]),
                     department_id=ceo.department_id, tenant_id=DEFAULT_TENANT_ID)  # fmt: skip


async def cleanup() -> dict[str, int]:
    get_config()
    out: dict[str, int] = {}
    async with get_sessionmaker()() as db:
        admin = (await db.execute(ADMIN)).scalar_one()
        settings = SystemSettingService(db)
        ks = await settings.get("ai.kill_switch")
        if ks is not None and ks.value.get("enabled"):
            off = {"enabled": False, "mode": "WRITE_OFF", "agents": []}
            await settings.set("ai.kill_switch", off, reason="E2E cleanup", updated_by=admin)
        ids = list((await db.execute(USERS)).scalars())
        if ids:
            await db.execute(DEL_TOKENS, {"ids": ids})
            await db.execute(DEL_USERS, {"ids": ids})
        out["users"] = len(ids)
        out["tasks"] = (await db.execute(TASKS)).rowcount  # type: ignore[attr-defined]
        ceo, undone = await _ceo(db), 0
        rows = (await db.execute(DOCS, {"files": list(FILES)})).all()
        for doc_id, status in rows:  # newest first
            if status == "COMMITTED":
                body = UndoIn(reason="E2E cleanup", reason_code="mistake")
                await UndoService(db).undo(ceo, uuid.UUID(str(doc_id)), body)
                undone += 1
        if rows:
            await db.execute(RETIRE_DOCS, {"ids": [r[0] for r in rows]})
        out |= {"undone": undone, "retired": len(rows)}
        out["emails"] = (await db.execute(EMAILS)).rowcount  # type: ignore[attr-defined]
        out["orgs"] = (await db.execute(ORG)).rowcount  # type: ignore[attr-defined]
        await settings.set("onboarding.state", completed_state(str(admin)), reason="E2E cleanup",
                           updated_by=admin)  # fmt: skip
        await db.commit()
    out["fixtures"] = _drop_fixtures()
    return out


def _drop_fixtures() -> int:
    n = 0
    for p in (DEFAULT_DIR / "chat").glob("*.json"):
        if json.loads(p.read_text(encoding="utf-8")).get("model") == MARK:
            p.unlink()
            n += 1
    return n


class _Scripted:
    """Gateway stand-in: replies in order and stores each (request → reply) as a fixture."""

    def __init__(self, replies: list[ChatResponse]) -> None:
        self.replies, self.store = replies, FixtureStore(DEFAULT_DIR)

    async def chat(self, req: ChatRequest) -> ChatResponse:
        resp = self.replies.pop(0)
        self.store.save(req, resp)
        return resp


def _reply(content: str, *calls: ToolCall) -> ChatResponse:
    return ChatResponse(content=content, provider="fixture", model=MARK, tool_calls=calls)


async def record_chat(email: str) -> dict[str, Any]:
    from app.modules.ai.services.chat_service import ChatService

    get_config()
    async with get_sessionmaker()() as db:
        u = await UserRepository(db).by_email(email)
        if u is None or u.employee_id is None:
            raise SystemExit(f"{email} missing / not linked to an employee")
        code = (await db.execute(text("SELECT employee_code FROM hr.employees WHERE id = :i"),
                                 {"i": u.employee_id})).scalar_one()  # fmt: skip
        user = Principal(user_id=u.id, role="EMP", permissions=frozenset(ROLE_PERMISSIONS["EMP"]),
                         department_id=u.department_id, tenant_id=DEFAULT_TENANT_ID,
                         employee_id=u.employee_id, email=email)  # fmt: skip
        args = {"title": TASK_TITLE, "assignee_code": code, "priority": "high"}
        call = ToolCall("call_1", "TOOL-create_task", args)
        ok = await ChatService(db, _Scripted([
            _reply("", call), _reply("Đã soạn thẻ giao việc — chờ bạn xác nhận."),
        ])).chat(user, ASK)  # fmt: skip
        await db.rollback()
        await SystemSettingService(db).set(
            "ai.kill_switch", {"enabled": True, "mode": "L0", "agents": []}, reason="E2E record",
            updated_by=user.user_id,
        )  # fmt: skip
        off = await ChatService(db, _Scripted([
            _reply("", call), _reply("AI đang tạm dừng soạn thao tác — bạn tự tạo việc nhé."),
        ])).chat(user, ASK)  # fmt: skip
        await db.rollback()
    return {"card": ok.suggested_actions[0]["autonomy_level"] if ok.suggested_actions else None,
            "killed": off.warnings, "ask": ASK}  # fmt: skip


async def report() -> dict[str, Any]:
    get_config()
    async with get_sessionmaker()() as db:
        return dict((await db.execute(COMPLETED)).scalar_one_or_none() or {})


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "--expect":
        print(json.dumps(expect(), ensure_ascii=False))
        raise SystemExit(0)
    jobs = {"--cleanup": cleanup, "--report": report}
    if cmd not in (*jobs, "--chat"):
        raise SystemExit("usage: onboarding_e2e.py --expect | --chat EMAIL | --report | --cleanup")
    with tenant_scope(DEFAULT_TENANT_ID):
        coro = record_chat(sys.argv[2]) if cmd == "--chat" else jobs[cmd]()
        print(json.dumps(asyncio.run(coro), ensure_ascii=False, default=str))
