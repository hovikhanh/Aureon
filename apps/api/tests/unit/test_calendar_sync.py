"""TC-M31-02 (T-804/T-805/T-810) — CalendarSyncService pull/push logic with in-memory fakes.

No DB, no network: the execution sync engine is exercised against a fake repositories + a fake
platform Integration-Hub, so the orchestration (LWW by etag, idempotent ExternalEventLink,
internal-only push, soft-delete on remote cancel) is covered on its own. Provider HTTP is
covered by TC-M31-01 (respx); the real-stack wiring by the integration tests.
"""

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

import pytest

from app.modules.execution.services.calendar_sync import CalendarSyncService
from app.modules.platform.services.calendar.types import PullResult, RemoteEvent
from app.modules.platform.services.calendar_integration import AccountRef

NOW = datetime(2026, 10, 20, 9, 0, tzinfo=UTC)


@dataclass
class FakeEvent:
    id: uuid.UUID
    owner_id: uuid.UUID
    title: str
    starts_at: datetime
    ends_at: datetime | None = None
    description: str | None = None
    location: str | None = None
    event_source: str = "internal"
    deleted_at: datetime | None = None
    task_id: uuid.UUID | None = None


@dataclass
class FakeLink:
    id: uuid.UUID
    calendar_event_id: uuid.UUID
    account_id: uuid.UUID
    external_id: str
    etag: str | None = None
    last_pushed_at: datetime | None = None
    deleted_at: datetime | None = None


class FakeEventRepo:
    def __init__(self) -> None:
        self.rows: dict[uuid.UUID, FakeEvent] = {}

    async def get(self, id_: uuid.UUID) -> FakeEvent | None:
        e = self.rows.get(id_)
        return e if e and e.deleted_at is None else None

    async def create(self, **values: Any) -> FakeEvent:
        values.pop("tenant_id", None)
        values.pop("source", None)
        values.pop("data_classification", None)
        values.pop("created_by", None)
        values.pop("visibility", None)
        e = FakeEvent(id=uuid.uuid4(), **values)
        self.rows[e.id] = e
        return e

    async def update(self, obj: FakeEvent, **values: Any) -> FakeEvent:
        for k, v in values.items():
            setattr(obj, k, v)
        return obj

    async def soft_delete(self, obj: FakeEvent) -> None:
        obj.deleted_at = NOW


class FakeLinkRepo:
    def __init__(self) -> None:
        self.rows: dict[uuid.UUID, FakeLink] = {}

    async def by_account_external(self, account_id: uuid.UUID, external_id: str) -> FakeLink | None:
        for link in self.rows.values():
            if (
                link.account_id == account_id
                and link.external_id == external_id
                and link.deleted_at is None
            ):
                return link
        return None

    async def for_event(self, calendar_event_id: uuid.UUID) -> list[FakeLink]:
        return [
            link
            for link in self.rows.values()
            if link.calendar_event_id == calendar_event_id and link.deleted_at is None
        ]

    async def create(self, **values: Any) -> FakeLink:
        values.pop("tenant_id", None)
        link = FakeLink(id=uuid.uuid4(), **values)
        self.rows[link.id] = link
        return link

    async def update(self, obj: FakeLink, **values: Any) -> FakeLink:
        for k, v in values.items():
            setattr(obj, k, v)
        return obj

    async def soft_delete(self, obj: FakeLink) -> None:
        obj.deleted_at = NOW


@dataclass
class FakeHub:
    """Stand-in for platform's public CalendarIntegrationService."""

    accounts: list[AccountRef] = field(default_factory=list)
    pull_result: PullResult | None = None
    pushed: list[tuple[uuid.UUID, RemoteEvent, str | None]] = field(default_factory=list)
    deleted: list[tuple[uuid.UUID, str]] = field(default_factory=list)
    push_returns: RemoteEvent | None = None

    async def connected_accounts(self) -> list[AccountRef]:
        return self.accounts

    async def connected_for_user(self, user_id: uuid.UUID) -> list[AccountRef]:
        return [a for a in self.accounts if a.user_id == user_id]

    async def pull(self, ref: AccountRef) -> PullResult | None:
        return self.pull_result

    async def push_remote(
        self, account_id: uuid.UUID, remote: RemoteEvent, *, external_id: str | None
    ) -> RemoteEvent | None:
        self.pushed.append((account_id, remote, external_id))
        return self.push_returns or RemoteEvent(
            external_id=external_id or "ext-new", title=remote.title,
            starts_at=remote.starts_at, ends_at=remote.ends_at, etag="etag-after",
        )  # fmt: skip

    async def delete_remote(self, account_id: uuid.UUID, external_id: str) -> bool:
        self.deleted.append((account_id, external_id))
        return True


class FakeSession:
    async def flush(self) -> None:  # engine calls db.flush() after create
        return None


def _svc() -> tuple[CalendarSyncService, FakeHub, FakeEventRepo, FakeLinkRepo]:
    svc = CalendarSyncService.__new__(CalendarSyncService)
    svc.db = FakeSession()  # type: ignore[assignment]
    svc.events = FakeEventRepo()  # type: ignore[assignment]
    svc.links = FakeLinkRepo()  # type: ignore[assignment]
    svc.hub = FakeHub()  # type: ignore[assignment]
    return svc, svc.hub, svc.events, svc.links  # type: ignore[return-value]


ACCT = AccountRef(account_id=uuid.uuid4(), user_id=uuid.uuid4(), provider="google")


async def test_pull_creates_internal_event_and_link() -> None:
    svc, hub, events, links = _svc()
    hub.accounts = [ACCT]
    hub.pull_result = PullResult(
        events=[
            RemoteEvent(external_id="e1", title="Demo", starts_at=NOW, ends_at=None, etag="t1")
        ],
        next_sync_token="s2",
    )
    applied = await svc.pull_all()
    assert applied == 1
    assert len(events.rows) == 1
    (ev,) = events.rows.values()
    assert ev.owner_id == ACCT.user_id and ev.event_source == "google" and ev.title == "Demo"
    (link,) = links.rows.values()
    assert link.external_id == "e1" and link.etag == "t1"


async def test_pull_lww_skips_unchanged_etag() -> None:
    svc, hub, events, _links = _svc()
    hub.accounts = [ACCT]
    hub.pull_result = PullResult(
        events=[RemoteEvent(external_id="e1", title="A", starts_at=NOW, ends_at=None, etag="t1")]
    )
    await svc.pull_all()
    # second pull with same etag → no change applied
    hub.pull_result = PullResult(
        events=[RemoteEvent(external_id="e1", title="A2", starts_at=NOW, ends_at=None, etag="t1")]
    )
    applied = await svc.pull_all()
    assert applied == 0
    (ev,) = events.rows.values()
    assert ev.title == "A"  # unchanged


async def test_pull_updates_on_new_etag() -> None:
    svc, hub, events, _links = _svc()
    hub.accounts = [ACCT]
    hub.pull_result = PullResult(
        events=[RemoteEvent(external_id="e1", title="A", starts_at=NOW, ends_at=None, etag="t1")]
    )
    await svc.pull_all()
    hub.pull_result = PullResult(
        events=[RemoteEvent(external_id="e1", title="B", starts_at=NOW, ends_at=None, etag="t2")]
    )
    applied = await svc.pull_all()
    assert applied == 1
    (ev,) = events.rows.values()
    assert ev.title == "B"


async def test_pull_soft_deletes_on_remote_cancel() -> None:
    svc, hub, events, links = _svc()
    hub.accounts = [ACCT]
    hub.pull_result = PullResult(
        events=[RemoteEvent(external_id="e1", title="A", starts_at=NOW, ends_at=None, etag="t1")]
    )
    await svc.pull_all()
    hub.pull_result = PullResult(
        events=[RemoteEvent(external_id="e1", title="A", starts_at=NOW, ends_at=None, deleted=True)]
    )
    applied = await svc.pull_all()
    assert applied == 1
    (ev,) = events.rows.values()
    assert ev.deleted_at is not None
    assert all(link.deleted_at is not None for link in links.rows.values())


async def test_push_internal_event_creates_remote_and_link() -> None:
    svc, hub, events, links = _svc()
    hub.accounts = [ACCT]
    ev = await events.create(
        owner_id=ACCT.user_id, title="Mine", starts_at=NOW, event_source="internal"
    )
    pushed = await svc.push_event(ACCT.user_id, ev.id, "created")
    assert pushed == 1
    assert len(hub.pushed) == 1 and hub.pushed[0][2] is None  # no external_id yet
    (link,) = links.rows.values()
    assert link.external_id == "ext-new" and link.etag == "etag-after"


async def test_push_skips_provider_sourced_event() -> None:
    svc, hub, events, _links = _svc()
    hub.accounts = [ACCT]
    ev = await events.create(
        owner_id=ACCT.user_id, title="FromGoogle", starts_at=NOW, event_source="google"
    )
    pushed = await svc.push_event(ACCT.user_id, ev.id, "updated")
    assert pushed == 0 and hub.pushed == []


async def test_push_delete_removes_remote_and_link() -> None:
    svc, hub, events, links = _svc()
    hub.accounts = [ACCT]
    ev = await events.create(
        owner_id=ACCT.user_id, title="Mine", starts_at=NOW, event_source="internal"
    )
    await links.create(
        calendar_event_id=ev.id, account_id=ACCT.account_id, external_id="ext-1", etag="t1"
    )
    pushed = await svc.push_event(ACCT.user_id, ev.id, "deleted")
    assert pushed == 1
    assert hub.deleted == [(ACCT.account_id, "ext-1")]
    assert all(link.deleted_at is not None for link in links.rows.values())


async def test_push_no_accounts_is_noop() -> None:
    svc, _hub, events, _links = _svc()
    ev = await events.create(
        owner_id=ACCT.user_id, title="Mine", starts_at=NOW, event_source="internal"
    )
    assert await svc.push_event(ACCT.user_id, ev.id, "created") == 0


@pytest.mark.parametrize("change", ["created", "updated"])
async def test_push_existing_link_updates_remote(change: str) -> None:
    svc, hub, events, links = _svc()
    hub.accounts = [ACCT]
    ev = await events.create(
        owner_id=ACCT.user_id, title="Mine", starts_at=NOW, event_source="internal"
    )
    await links.create(
        calendar_event_id=ev.id, account_id=ACCT.account_id, external_id="ext-1", etag="old"
    )
    pushed = await svc.push_event(ACCT.user_id, ev.id, change)
    assert pushed == 1
    assert hub.pushed[0][2] == "ext-1"  # reuses external_id
    (link,) = links.rows.values()
    assert link.etag == "etag-after"
