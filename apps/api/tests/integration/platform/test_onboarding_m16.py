"""T-648 — EP-ADM-13/14 onboarding (TC-M16-13, TC-M16-17 onboarding part; 10 §7.2.5, 05 §2.8).

State machine on `platform.system_settings` key `onboarding.state` with optimistic `version`;
`progress` derived from hr/auth/execution data; audit `platform.onboarding_<action>`; `finish`
→ outbox `platform.onboarding_completed` (registered, tenant + correlation id, no PII/`reason`).
"""

import uuid
from typing import Any

import pytest
from sqlalchemy import select

from app.core.audit import AUDIT_LOGS
from app.core.events.envelope import OUTBOX
from app.core.events.registry import is_registered
from app.modules.platform.services import onboarding_service
from tests.conftest import ApiClient

pytestmark = pytest.mark.integration
URL = "/platform/onboarding"


async def _patch(api: ApiClient, role: str = "ADM", **body: Any) -> Any:
    return await api.call("PATCH", URL, role=role, json=body)


async def _state(api: ApiClient) -> dict[str, Any]:
    r = await api.call("GET", URL, role="ADM")
    assert r.status_code == 200, r.text
    return r.json()["data"]


async def _step(api: ApiClient, action: str, step: str, **kw: Any) -> dict[str, Any]:
    v = (await _state(api))["version"]
    r = await _patch(api, action=action, step=step, version=v, **kw)
    assert r.status_code == 200, r.text
    return r.json()["data"]


async def test_get_without_row_is_not_started_with_progress(api: ApiClient) -> None:
    s = await _state(api)
    assert (s["status"], s["version"]) == ("not_started", 0)
    assert {v["status"] for v in s["steps"].values()} == {"pending"}
    assert len(s["steps"]) == 6
    p = s["progress"]
    assert p["organization_ready"] is True and p["departments"] >= 7 and p["employees"] >= 100
    assert p["users_by_role"].get("CEO", 0) >= 1 and p["kpis"] > 0 and p["objectives"] > 0
    assert 0 <= p["employees_without_user"] <= p["employees"]


async def test_start_is_idempotent_and_needs_no_version(api: ApiClient) -> None:
    a = (await _patch(api, action="start")).json()["data"]
    assert a["status"] == "in_progress" and a["started_at"] and a["version"] == 1
    b = (await _patch(api, action="start")).json()["data"]
    assert (b["started_at"], b["version"]) == (a["started_at"], a["version"])


async def test_rbac_reader_and_admin(api: ApiClient) -> None:
    for role in ("DIR", "MGR", "EMP", "REV"):
        assert (await api.call("GET", URL, role=role)).status_code == 403
        assert (await _patch(api, role=role, action="start")).status_code == 403
    assert (await _patch(api, role="CEO", action="start")).status_code == 200


async def test_steps_finish_event_and_audit(api: ApiClient, db_session, monkeypatch) -> None:
    sent: list[Any] = []
    real = onboarding_service.publish_in_tx

    async def spy(*a: Any, **kw: Any) -> Any:
        sent.append(env := await real(*a, **kw))
        return env

    monkeypatch.setattr(onboarding_service, "publish_in_tx", spy)
    await _patch(api, action="start")
    org = str(uuid.uuid4())
    s = await _step(api, "complete_step", "company", refs={"organization_id": org})
    assert s["steps"]["company"]["status"] == "done" and s["refs"]["organization_id"] == org
    v = s["version"]
    early = await _patch(api, action="finish", version=v)
    assert early.status_code == 422
    assert early.json()["error"]["details"]["missing_steps"] == ["org_import", "users"]
    await _step(api, "complete_step", "org_import", refs={"org_import_id": str(uuid.uuid4())})
    await _step(api, "reopen_step", "org_import")
    await _step(api, "complete_step", "org_import")
    await _step(api, "complete_step", "users", refs={"users_created": 3})
    assert (await _step(api, "skip_step", "goals_import"))["steps"]["goals_import"]["status"] == (
        "skipped")  # fmt: skip
    v = (await _state(api))["version"]
    done = await _patch(api, action="finish", version=v, reason="xong")
    assert done.status_code == 200 and done.json()["data"]["status"] == "completed"
    assert done.json()["data"]["completed_at"]

    (env,) = sent
    assert is_registered(env.event_type) and env.event_type == "platform.onboarding_completed"
    assert env.tenant_id is not None and env.correlation_id
    p = env.payload
    assert set(p) == {"started_at", "completed_at", "duration_minutes", "within_one_day", "counts"}
    assert p["within_one_day"] is True and p["duration_minutes"] >= 0
    assert set(p["counts"]) == {"departments", "employees", "users", "kpis", "objectives"}
    assert "xong" not in str(p)
    stored = (await db_session.execute(select(OUTBOX.c.payload).where(
        OUTBOX.c.id == env.event_id))).scalar_one()  # fmt: skip
    assert stored["counts"] == p["counts"]
    acts = set((await db_session.execute(select(AUDIT_LOGS.c.action).where(
        AUDIT_LOGS.c.action.like("platform.onboarding_%")))).scalars())  # fmt: skip
    assert {"platform.onboarding_start", "platform.onboarding_complete_step",
            "platform.onboarding_reopen_step", "platform.onboarding_skip_step",
            "platform.onboarding_finish"} <= acts  # fmt: skip


async def test_version_mismatch_is_409_and_missing_version_422(api: ApiClient) -> None:
    v = (await _patch(api, action="start")).json()["data"]["version"]
    stale = await _patch(api, action="complete_step", step="company", version=v + 5)
    assert stale.status_code == 409 and stale.json()["error"]["code"] == "CONFLICT_STATE"
    assert (await _patch(api, action="complete_step", step="company")).status_code == 422


@pytest.mark.parametrize("refs", [
    {"email": "a@b.vn"}, {"organization_id": "Công ty ABC"}, {"count": "3"},
    {"document_ids": "x"}, {"full_name": "Nguyễn Văn A"},
])  # fmt: skip
async def test_refs_unknown_key_or_pii_is_422(api: ApiClient, refs: dict[str, Any]) -> None:
    v = (await _patch(api, action="start")).json()["data"]["version"]
    r = await _patch(api, action="complete_step", step="company", version=v, refs=refs)
    assert r.status_code == 422 and r.json()["error"]["code"] == "VALIDATION_ERROR"


async def test_invalid_transitions(api: ApiClient) -> None:
    before = await _patch(api, action="complete_step", step="company", version=0)
    assert before.status_code == 422  # not started yet
    v = (await _patch(api, action="start")).json()["data"]["version"]
    assert (await _patch(api, action="skip_step", step="users", version=v)).status_code == 422
    assert (await _patch(api, action="complete_step", version=v)).status_code == 422
    assert (await _patch(api, action="complete_step", step="finish", version=v)).status_code == 422
    assert (await _patch(api, action="reset", version=v)).status_code == 422  # no reason


async def _complete(api: ApiClient) -> int:
    await _patch(api, action="start")
    for step in ("company", "org_import", "users"):
        await _step(api, "complete_step", step)
    v = (await _state(api))["version"]
    r = await _patch(api, action="finish", version=v)
    assert r.status_code == 200
    return int(r.json()["data"]["version"])


async def test_reset_completed_only_in_demo_mode(api: ApiClient, monkeypatch) -> None:
    from app.core.config import ConfigService

    v = await _complete(api)
    monkeypatch.setattr(onboarding_service, "get_config",
                        lambda: ConfigService(demo_mode=False))  # fmt: skip
    r = await _patch(api, action="reset", version=v, reason="làm lại")
    assert r.status_code == 422 and r.json()["error"]["code"] == "BUSINESS_RULE_VIOLATION"
    monkeypatch.setattr(onboarding_service, "get_config", lambda: ConfigService(demo_mode=True))
    ok = (await _patch(api, action="reset", version=v, reason="làm lại")).json()["data"]
    assert ok["status"] == "not_started" and ok["started_at"] is None
    assert ok["version"] == v + 1


async def test_reset_in_progress_outside_demo(api: ApiClient, monkeypatch) -> None:
    from app.core.config import ConfigService

    monkeypatch.setattr(onboarding_service, "get_config",
                        lambda: ConfigService(demo_mode=False))  # fmt: skip
    v = (await _patch(api, action="start")).json()["data"]["version"]
    r = await _patch(api, action="reset", version=v, reason="sai")
    assert r.status_code == 200 and r.json()["data"]["status"] == "not_started"


async def test_review_is_derived_done_when_org_import_commits(api: ApiClient, db_session) -> None:
    """05 §2.8: `review` auto-`done` once the `org_import` C5 document is COMMITTED (derived on
    read — follows undo; an explicit `reopen_step review` is stored and wins)."""
    from datetime import UTC, datetime

    from app.modules.idp.models import ImportBatch
    from tests.integration.idp.test_inbox_t635 import _doc

    owner = uuid.uuid4()
    doc = await _doc(db_session, owner, "NEEDS_REVIEW", kind="FILE", name="DOC-06.xlsx")
    batch = ImportBatch(kind="excel_import", submitted_by=owner, status="open",
                        source_document_id=doc.id)  # fmt: skip
    db_session.add(batch)
    await db_session.flush()
    await _patch(api, action="start")
    s = await _step(api, "complete_step", "org_import",
                    refs={"org_import_id": str(batch.id), "rows": 12})  # fmt: skip
    assert s["steps"]["review"]["status"] == "pending"
    at = datetime(2026, 10, 20, 3, 0, tzinfo=UTC)
    doc.status, doc.committed_at = "COMMITTED", at
    await db_session.flush()
    s = await _state(api)
    assert s["steps"]["review"]["status"] == "done"
    assert s["steps"]["review"]["updated_at"].startswith("2026-10-20T03:00")
    doc.status = "ROLLED_BACK"  # undo → back to pending (not stored)
    await db_session.flush()
    assert (await _state(api))["steps"]["review"]["status"] == "pending"
    doc.status = "COMMITTED"
    await db_session.flush()
    # finish only needs company/org_import/users; the derived review shows done meanwhile
    s = await _step(api, "reopen_step", "review")
    assert s["steps"]["review"]["status"] == "in_progress"  # explicit state wins
