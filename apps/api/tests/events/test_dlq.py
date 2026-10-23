"""TC-EVT-003 — retry 5 s / 30 s / 120 s → DLQ; EP-56 lists and replays (10 §8.2 E4)."""

import uuid
from collections.abc import AsyncIterator

import httpx
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.base_model import DEFAULT_TENANT_ID
from app.core.deps import get_db
from app.core.events.bus import ConsumerRegistry
from app.core.events.consumer import MAX_ATTEMPTS, RETRY_BACKOFF_SECONDS, Outcome, consume
from app.core.events.envelope import PROCESSED, EventEnvelope
from app.core.events.outbox import publish_in_tx
from app.core.security import sign_access_token
from app.main import create_app
from app.modules.auth.permission_matrix import ROLE_PERMISSIONS
from app.modules.platform.routes.router import get_platform_service
from app.modules.platform.services.platform_service import PlatformService
from tests.events.conftest import InMemoryTransport

pytestmark = pytest.mark.integration

EVT = "sales.deal_closed_lost"
NAME = "risk.on_deal_closed_lost"


class Flaky:
    def __init__(self, failures: int) -> None:
        self.failures = failures
        self.calls = 0

    async def __call__(self, _s: AsyncSession, _e: EventEnvelope) -> None:
        self.calls += 1
        if self.calls <= self.failures:
            raise RuntimeError(f"boom #{self.calls}")


async def _event(factory: async_sessionmaker[AsyncSession]) -> dict[str, object]:
    async with factory() as s:
        env = await publish_in_tx(
            s,
            event_type=EVT,
            producer="sales",
            aggregate_schema="sales",
            aggregate_table="test_events",
            aggregate_id=uuid.uuid4(),
            payload={"deal_id": str(uuid.uuid4()), "deal_value": 600_000_000},
        )
        await s.commit()
    return env.to_message()


async def _run_until_settled(
    factory: async_sessionmaker[AsyncSession], registry: ConsumerRegistry, msg: dict[str, object]
) -> list[tuple[Outcome, int | None]]:
    """Drive the Celery retry loop by hand: attempt 1, 2, … until not RETRY."""
    trail = []
    attempt = 1
    while True:
        r = await consume(factory, NAME, msg, attempt, registry=registry)
        trail.append((r.outcome, r.retry_in))
        if r.outcome is not Outcome.RETRY:
            return trail
        attempt += 1


async def _processed(factory: async_sessionmaker[AsyncSession], eid: object) -> list[object]:
    async with factory() as s:
        return list((await s.execute(select(PROCESSED).where(PROCESSED.c.event_id == eid))).all())


def test_backoff_schedule() -> None:
    assert RETRY_BACKOFF_SECONDS == (5, 30, 120)
    assert MAX_ATTEMPTS == 4  # first try + 3 retries


async def test_recovers_within_retries(
    factory: async_sessionmaker[AsyncSession], registry: ConsumerRegistry
) -> None:
    handler = Flaky(failures=2)
    registry.register(NAME, (EVT,), handler)
    msg = await _event(factory)
    trail = await _run_until_settled(factory, registry, msg)
    assert trail == [(Outcome.RETRY, 5), (Outcome.RETRY, 30), (Outcome.DONE, None)]
    (row,) = await _processed(factory, uuid.UUID(str(msg["event_id"])))
    assert (row.status, row.attempts) == ("DONE", 3)  # type: ignore[attr-defined]


async def test_persistent_failure_goes_to_dlq(
    factory: async_sessionmaker[AsyncSession], registry: ConsumerRegistry
) -> None:
    handler = Flaky(failures=99)
    registry.register(NAME, (EVT,), handler)
    msg = await _event(factory)
    trail = await _run_until_settled(factory, registry, msg)
    assert trail == [
        (Outcome.RETRY, 5),
        (Outcome.RETRY, 30),
        (Outcome.RETRY, 120),
        (Outcome.DLQ, None),
    ]
    assert handler.calls == 4
    (row,) = await _processed(factory, uuid.UUID(str(msg["event_id"])))
    assert (row.status, row.attempts) == ("DLQ", 4)  # type: ignore[attr-defined]
    assert "boom #4" in row.last_error  # type: ignore[attr-defined]
    # A late duplicate delivery of a DLQ'd event is skipped, not re-run.
    again = await consume(factory, NAME, msg, registry=registry)
    assert again.outcome is Outcome.DUPLICATE
    assert handler.calls == 4


@pytest.fixture
async def admin_client(
    factory: async_sessionmaker[AsyncSession], transport: InMemoryTransport
) -> AsyncIterator[httpx.AsyncClient]:
    app = create_app()

    async def _db() -> AsyncIterator[AsyncSession]:
        async with factory() as s:
            yield s

    app.dependency_overrides[get_db] = _db

    async def _svc() -> AsyncIterator[PlatformService]:
        async with factory() as s:
            yield PlatformService(s, transport)

    app.dependency_overrides[get_platform_service] = _svc
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test/api/v1"
    ) as c:
        yield c


# ex 10-role F.O.C.U.S → 7-role v3 (R-DEC-12). DLQ là platform (cross-pillar), không cần khối.
_LEGACY = {"CEO": "CEO", "CFO": "DIR", "VP_SALES": "DIR", "HR_MANAGER": "DIR", "CPO": "DIR",
           "RISK_MANAGER": "DIR", "MANAGER": "MGR", "EMPLOYEE": "EMP", "REVIEWER": "REV",
           "ADMIN": "ADM"}  # fmt: skip


def _auth(role: str) -> dict[str, str]:
    v3 = _LEGACY.get(role, role)
    token, _ = sign_access_token(
        user_id=uuid.uuid4(),
        email=f"{v3.lower()}@abc.test",
        role=v3,
        role_id=str(uuid.uuid4()),
        permissions=ROLE_PERMISSIONS[v3],
        department_id=None,
        tenant_id=DEFAULT_TENANT_ID,
    )
    return {"Authorization": f"Bearer {token}"}


async def test_ep56_list_and_replay_reprocesses(
    factory: async_sessionmaker[AsyncSession],
    registry: ConsumerRegistry,
    transport: InMemoryTransport,
    admin_client: httpx.AsyncClient,
) -> None:
    handler = Flaky(failures=4)  # fails all 4 attempts, succeeds on replay
    registry.register(NAME, (EVT,), handler)
    msg = await _event(factory)
    eid = str(msg["event_id"])
    await _run_until_settled(factory, registry, msg)

    r = await admin_client.get(
        "/platform/dead-letters", params={"event_type": EVT}, headers=_auth("ADMIN")
    )
    assert r.status_code == 200, r.text
    mine = [d for d in r.json()["data"] if d["event_id"] == eid]
    assert len(mine) == 1
    assert mine[0]["consumer"] == NAME
    assert mine[0]["attempts"] == 4
    assert r.json()["meta"]["pagination"]["total"] >= 1

    r = await admin_client.post(
        f"/platform/dead-letters/{mine[0]['id']}/replay", headers=_auth("ADMIN")
    )
    assert r.status_code == 202, r.text
    replay = r.json()["data"]
    assert replay["id"] == mine[0]["id"]  # EP-56 replay request identifier
    assert replay["event_id"] == eid
    assert replay["replay_status"] == "queued"
    assert replay["queued_at"].endswith("Z")
    assert "status" not in replay
    assert await _processed(factory, uuid.UUID(eid)) == []  # DLQ marker cleared
    (name, replayed, _) = next(x for x in transport.sent if x[1]["event_id"] == eid)
    assert name == NAME

    # Worker picks the replayed message up → processed once, DONE.
    result = await consume(factory, name, replayed, registry=registry)
    assert result.outcome is Outcome.DONE
    assert handler.calls == 5
    (row,) = await _processed(factory, uuid.UUID(eid))
    assert row.status == "DONE"  # type: ignore[attr-defined]

    # Replaying again: no DLQ row any more → 404.
    r = await admin_client.post(
        f"/platform/dead-letters/{mine[0]['id']}/replay", headers=_auth("ADMIN")
    )
    assert r.status_code == 404


async def test_ep56_requires_platform_admin(admin_client: httpx.AsyncClient) -> None:
    for role in ("CFO", "EMPLOYEE", "REVIEWER"):
        r = await admin_client.get("/platform/dead-letters", headers=_auth(role))
        assert r.status_code == 403, role
        assert r.json()["error"]["code"] == "FORBIDDEN_ROLE"
    assert (
        await admin_client.get("/platform/dead-letters", headers=_auth("CEO"))
    ).status_code == 200
    assert (await admin_client.get("/platform/dead-letters")).status_code == 401
