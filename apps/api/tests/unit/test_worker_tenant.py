"""TC-M11-03 (T-603, R-DEC-21) — workers set the tenant: beat jobs loop over the active tenants,
the IDP pipeline task runs as the enqueuer's tenant and refuses a task without one."""

import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

import pytest

from app.core.base_model import DEFAULT_TENANT_ID
from app.core.tenant import TenantContextMissingError, current_tenant
from app.workers import idp_pipeline, jobs

T1, T2 = uuid.UUID(int=0xA1), uuid.UUID(int=0xB2)


class FakeSession:
    commits = 0

    def __init__(self, *_a: Any, **_k: Any) -> None: ...

    async def __aenter__(self) -> "FakeSession":
        return self

    async def __aexit__(self, *_a: Any) -> None: ...

    async def commit(self) -> None:
        FakeSession.commits += 1


@asynccontextmanager
async def fake_engine() -> AsyncIterator[object]:
    yield object()


@pytest.fixture(autouse=True)
def _no_db(monkeypatch: pytest.MonkeyPatch) -> None:
    FakeSession.commits = 0
    for mod in (jobs, idp_pipeline):
        monkeypatch.setattr(mod, "_engine", fake_engine)
        monkeypatch.setattr(mod, "AsyncSession", FakeSession)


async def test_job_runs_once_per_active_tenant_and_merges(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(jobs, "active_tenant_ids", lambda: (T1, T2))
    seen: list[uuid.UUID | None] = []

    async def job(_db: Any) -> dict[str, int]:
        seen.append(current_tenant())
        return {"written": 2, str(current_tenant())[-1]: 1}

    assert await jobs._run(job) == {"written": 4, "1": 1, "2": 1}
    assert seen == [T1, T2] and FakeSession.commits == 2  # one transaction per tenant
    assert current_tenant() == DEFAULT_TENANT_ID  # scope restored


def test_merge_shapes() -> None:
    assert jobs._merge(None, 3) == 3
    assert jobs._merge(3, 4) == 7
    assert jobs._merge(False, True) is True and jobs._merge(False, False) is False


async def test_default_tenant_list_is_the_system_tenant() -> None:
    seen: list[uuid.UUID | None] = []

    async def job(_db: Any) -> int:
        seen.append(current_tenant())
        return 1

    assert await jobs._run(job) == 1 and seen == [DEFAULT_TENANT_ID]


def test_pipeline_task_refuses_missing_tenant() -> None:
    with pytest.raises(TenantContextMissingError):
        idp_pipeline.process_document.run(str(uuid.uuid4()))


async def test_pipeline_task_runs_as_given_tenant(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: list[uuid.UUID | None] = []

    class FakePipeline:
        def __init__(self, *_a: Any) -> None: ...

        async def run(self, _doc: uuid.UUID) -> Any:
            seen.append(current_tenant())
            return type("O", (), {"status": "SUCCEEDED"})()

    monkeypatch.setattr(idp_pipeline, "Pipeline", FakePipeline)
    monkeypatch.setattr(idp_pipeline, "pipeline_gateway", lambda _s: None)
    assert await idp_pipeline._run(str(uuid.uuid4()), str(T2)) == "SUCCEEDED"
    assert seen == [T2] and FakeSession.commits == 1
