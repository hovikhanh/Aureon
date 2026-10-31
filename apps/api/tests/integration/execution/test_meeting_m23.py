"""M2.3 (T-720..724) — MeetingSummary/ActionItem, fuzzy owner match (R-DEC-103),
2 ACTs + chair-approval gate (R-DEC-101), ids-only events (R-DEC-102), lineage whitelist.

Service-level tests on `db_session` (rolled back). TC-M23-05/06/07/08/09.
"""

import uuid
from datetime import date, datetime

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.base_model import DEFAULT_TENANT_ID
from app.core.deps import Principal
from app.modules.auth.permission_matrix import ROLE_PERMISSIONS
from app.modules.execution.models import ActionItem, Meeting, MeetingSummary
from app.modules.execution.services.meeting_service import MeetingService
from app.modules.hr.models import Department, Employee, Organization
from app.modules.hr.services import hr_service as _hr  # noqa: F401 — registers name matcher
from tests.integration.execution.helpers import outbox_for

pytestmark = pytest.mark.integration
HELD = datetime(2026, 10, 20, 9, 0, 0)


def _ceo() -> Principal:
    return Principal(
        user_id=uuid.uuid4(), role="CEO", role_id="CEO",
        permissions=frozenset(ROLE_PERMISSIONS["CEO"]), tenant_id=DEFAULT_TENANT_ID,
    )  # fmt: skip


async def _department(db: AsyncSession) -> Department:
    org = Organization(code=f"ORG-{uuid.uuid4().hex[:6]}", name="ABC", valid_from=date(2020, 1, 1),
                       source="SEED")  # fmt: skip
    db.add(org)
    await db.flush()
    dept = Department(organization_id=org.id, code=f"D-{uuid.uuid4().hex[:6]}", name="Phòng",
                      aliases=[], valid_from=date(2020, 1, 1), source="SEED")  # fmt: skip
    db.add(dept)
    await db.flush()
    return dept


async def _employee(db: AsyncSession, name: str, norm: str, dept: Department) -> Employee:
    emp = Employee(
        employee_code=f"M23-{uuid.uuid4().hex[:8]}", full_name=name, normalized_name=norm,
        department_id=dept.id, status="active", hire_date=date(2025, 1, 1), source="MANUAL",
    )  # fmt: skip
    db.add(emp)
    await db.flush()
    return emp


async def _meeting(db: AsyncSession, chair: uuid.UUID) -> Meeting:
    m = Meeting(title="Giao ban", held_at=HELD, chair_id=chair, attendee_ids=[chair],
                source="MANUAL")  # fmt: skip
    db.add(m)
    await db.flush()
    return m


async def test_fuzzy_owner_match_bands(db_session: AsyncSession) -> None:
    """R-DEC-103: exact-ish ≥0.90 → matched; faint → unmatched/ambiguous."""
    dept = await _department(db_session)
    await _employee(db_session, "Nguyễn Văn Minh", "nguyen van minh", dept)
    svc = MeetingService(db_session)
    ceo = _ceo()
    matched = await svc.create_action_item(ceo, title="Báo cáo", owner_name="Nguyen Van Minh")
    assert matched.match_status == "matched" and matched.owner_id is not None
    unmatched = await svc.create_action_item(ceo, title="Việc khác", owner_name="Zzz Qqq Www")
    assert unmatched.match_status in {"unmatched", "ambiguous"} and unmatched.owner_id is None
    no_name = await svc.create_action_item(ceo, title="Không người", owner_name=None)
    assert no_name.match_status == "unmatched" and no_name.owner_id is None


async def test_action_item_event_ids_only(db_session: AsyncSession) -> None:
    """R-DEC-102: execution.action_item_created payload has no title/owner_name_raw."""
    svc = MeetingService(db_session)
    ai = await svc.create_action_item(
        _ceo(), title="Bí mật nội dung", owner_name="Trần Thị Thu", due_date=date(2026, 11, 15)
    )
    events = await outbox_for(db_session, str(ai.id))
    created = [p for t, p in events if t == "execution.action_item_created"]
    assert len(created) == 1
    payload = created[0]
    assert payload["action_item_id"] == str(ai.id)
    assert payload["match_status"] in {"matched", "ambiguous", "unmatched"}
    assert "title" not in payload and "owner_name_raw" not in payload
    assert payload["due_date"] == "2026-11-15"


async def test_create_task_from_action_item_idempotent_and_undo(db_session: AsyncSession) -> None:
    """R-DEC-101: task from item (chair approval upstream); idempotent; undo detaches."""
    ceo = _ceo()
    svc = MeetingService(db_session)
    m = await _meeting(db_session, ceo.user_id)
    ai = await svc.create_action_item(ceo, title="Soạn hợp đồng", meeting_id=m.id)
    task1 = await svc.create_task_from_action_item(ceo, ai.id)
    await db_session.refresh(ai)
    assert ai.task_id == task1.id and ai.status == "task_created"
    task2 = await svc.create_task_from_action_item(ceo, ai.id)  # idempotent
    assert task2.id == task1.id
    await svc.detach_task(ceo, task1.id)  # ACT undo
    await db_session.refresh(ai)
    assert ai.task_id is None and ai.status == "open"


async def test_meeting_summary_upsert_and_event(db_session: AsyncSession) -> None:
    """R-DEC-100/102: 1-1 MeetingSummary upsert + execution.meeting_summarized event."""
    ceo = _ceo()
    svc = MeetingService(db_session)
    m = await _meeting(db_session, ceo.user_id)
    s1 = await svc.create_summary(ceo, meeting_id=m.id, summary_text="Tóm tắt 1")
    s2 = await svc.create_summary(ceo, meeting_id=m.id, summary_text="Tóm tắt 2")
    assert s1.id == s2.id  # 1-1 upsert
    rows = (
        (await db_session.execute(select(MeetingSummary).where(MeetingSummary.meeting_id == m.id)))
        .scalars()
        .all()
    )
    assert len(rows) == 1 and rows[0].summary_text == "Tóm tắt 2"
    events = await outbox_for(db_session, str(s2.id))
    assert any(t == "execution.meeting_summarized" and p["meeting_id"] == str(m.id)
               for t, p in events)  # fmt: skip


async def test_action_item_soft_delete_undo(db_session: AsyncSession) -> None:
    ceo = _ceo()
    svc = MeetingService(db_session)
    ai = await svc.create_action_item(ceo, title="Xoá thử")
    await svc.delete_action_item(ceo, ai.id)
    row = await db_session.get(ActionItem, ai.id)
    assert row is not None and row.deleted_at is not None


async def test_action_item_in_lineage_whitelist_and_scoped(db_session: AsyncSession) -> None:
    """R-DEC-104: execution.action_items is an EP-DC-26 lineage target, scoped via meeting."""
    from app.modules.platform.services.lineage_service import LINEAGE_ENTITIES

    assert "execution.action_items" in LINEAGE_ENTITIES
    ceo = _ceo()
    svc = MeetingService(db_session)
    m = await _meeting(db_session, ceo.user_id)
    ai = await svc.create_action_item(ceo, title="Việc có lineage", meeting_id=m.id)
    fetched = await svc.get_action_item(ceo, ai.id)  # CEO sees all meetings
    assert fetched.id == ai.id


async def test_both_acts_through_registry_validate_run_undo(db_session: AsyncSession) -> None:
    """R-DEC-101: both meeting ACTs via the Action Registry executor (validate → run → undo).
    Covers the ActionDef wrappers + params models + the create_task undo (detach)."""
    from app.modules.idp.services.actions import ActionContext, get_action
    from app.modules.idp.services.actions.executor import Step, run_all

    ceo = _ceo()
    # ACT-create_action_item: empty title → validate error; valid → writes an ActionItem.
    act_ai = get_action("ACT-create_action_item")
    assert act_ai is not None
    bad = await act_ai.validate(db_session, ceo, act_ai.params_model(title=""),
                                ActionContext(source="IDP"))  # fmt: skip
    assert bad and bad[0]["field"] == "title"
    step_ai = Step(act_ai, 0, {"title": "Giao việc A", "owner_name": "Nguyễn Văn An",
                               "due_date": "2026-11-05"})  # fmt: skip
    ((_, outcome_ai),) = await run_all(db_session, ceo, [step_ai], ActionContext(source="IDP"))
    ai_id = uuid.UUID(outcome_ai.result_refs[0]["id"])
    assert await db_session.get(ActionItem, ai_id) is not None

    # ACT-create_task_from_action_item: bad ref → validate error; valid → Task; undo detaches.
    act_task = get_action("ACT-create_task_from_action_item")
    assert act_task is not None
    bad_t = await act_task.validate(db_session, ceo, act_task.params_model(action_item_ref="x"),
                                    ActionContext())  # fmt: skip
    assert bad_t and bad_t[0]["code"] == "invalid_uuid"
    step_t = Step(act_task, 0, {"action_item_ref": str(ai_id)})
    ((_, outcome_t),) = await run_all(db_session, ceo, [step_t], ActionContext())
    task_id = uuid.UUID(outcome_t.result_refs[0]["id"])
    refreshed = await MeetingService(db_session).get_action_item(ceo, ai_id)
    assert refreshed.task_id == task_id
    await act_task.undo(db_session, ceo, outcome_t)  # detach + delete task
    detached = await MeetingService(db_session).get_action_item(ceo, ai_id)
    assert detached.task_id is None
