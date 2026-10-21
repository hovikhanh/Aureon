"""T-001 — BaseRepository / BaseService behaviour with a fake AsyncSession (no DB needed)."""

import uuid
from typing import Any

import pytest
from sqlalchemy.orm import DeclarativeBase

from app.core.base_model import (
    ActorMixin,
    CommonFieldsMixin,
    IdMixin,
    SoftDeleteMixin,
    TimestampMixin,
)
from app.core.base_repository import MAX_LIMIT, BaseRepository
from app.core.base_service import BaseService


class _IsolatedBase(DeclarativeBase):
    """Separate metadata so this test table never leaks into Alembic's target_metadata."""


class Widget(
    _IsolatedBase, IdMixin, TimestampMixin, SoftDeleteMixin, ActorMixin, CommonFieldsMixin
):
    __tablename__ = "widgets_test"


class _Result:
    def __init__(self, value: Any) -> None:
        self.value = value

    def scalar_one_or_none(self) -> Any:
        return self.value

    def scalar_one(self) -> Any:
        return self.value

    def scalars(self) -> "_Result":
        return self

    def all(self) -> Any:
        return self.value


class FakeSession:
    def __init__(self, result: Any = None) -> None:
        self.added: list[Any] = []
        self.flushes = 0
        self.statements: list[Any] = []
        self.result = result

    def add(self, obj: Any) -> None:
        self.added.append(obj)

    async def flush(self) -> None:
        self.flushes += 1

    async def execute(self, stmt: Any) -> _Result:
        self.statements.append(stmt)
        return _Result(self.result)


def _repo(session: FakeSession) -> BaseRepository[Widget]:
    return BaseRepository(session, Widget)  # type: ignore[arg-type]


async def test_create_adds_and_flushes() -> None:
    s = FakeSession()
    obj = await _repo(s).create(source="SEED")
    assert s.added == [obj] and s.flushes == 1


async def test_update_bumps_version() -> None:
    s = FakeSession()
    obj = Widget(version=1)
    await _repo(s).update(obj, data_classification="SECRET")
    assert obj.version == 2 and obj.data_classification == "SECRET"


async def test_soft_delete_sets_deleted_at() -> None:
    s = FakeSession()
    obj = Widget()
    await _repo(s).soft_delete(obj)
    assert obj.deleted_at is not None


async def test_get_filters_soft_deleted() -> None:
    s = FakeSession(result=None)
    assert await _repo(s).get(uuid.uuid4()) is None
    assert "deleted_at IS NULL" in str(s.statements[0])


async def test_list_clamps_limit() -> None:
    s = FakeSession(result=[])
    await _repo(s).list(limit=10_000, offset=-5)
    compiled = s.statements[0].compile()
    assert compiled.params["param_1"] == MAX_LIMIT


async def test_count() -> None:
    assert await _repo(FakeSession(result=3)).count() == 3


async def test_soft_delete_rejects_append_only() -> None:
    class Plain:
        __name__ = "Plain"

    repo = _repo(FakeSession())
    repo.model = Plain  # type: ignore[assignment]
    with pytest.raises(TypeError):
        await repo.soft_delete(object())  # type: ignore[arg-type]


def test_base_service_holds_session_and_repo() -> None:
    s = FakeSession()
    repo = _repo(s)
    svc = BaseService(s, repo)  # type: ignore[arg-type]
    assert svc.db is s and svc.repo is repo


class Plain(_IsolatedBase, IdMixin, TimestampMixin):
    __tablename__ = "plain_test"


async def test_expected_version_on_unversioned_model_is_rejected() -> None:
    repo = BaseRepository(FakeSession(), Plain)  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="no version column"):
        await repo.update(Plain(), expected_version=1)
