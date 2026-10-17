"""T-004 — `get_db()` yields one session per request and always closes it."""

from collections.abc import Generator, Iterator

import pytest
from sqlalchemy.orm import Session

from app.db import session as session_module


class _SpySession(Session):
    closed_calls = 0

    def close(self) -> None:
        type(self).closed_calls += 1
        super().close()


@pytest.fixture
def spy(monkeypatch: pytest.MonkeyPatch) -> Iterator[type[_SpySession]]:
    _SpySession.closed_calls = 0
    monkeypatch.setattr(session_module, "SessionLocal", lambda: _SpySession())
    yield _SpySession


def test_get_db_closes_session_after_request(spy: type[_SpySession]) -> None:
    gen: Generator[Session] = session_module.get_db()
    db = next(gen)
    assert isinstance(db, Session)
    assert spy.closed_calls == 0
    with pytest.raises(StopIteration):
        next(gen)
    assert spy.closed_calls == 1


def test_get_db_closes_session_on_error(spy: type[_SpySession]) -> None:
    gen: Generator[Session] = session_module.get_db()
    next(gen)
    with pytest.raises(RuntimeError):
        gen.throw(RuntimeError("handler failed"))
    assert spy.closed_calls == 1


def test_get_db_yields_new_session_per_request(spy: type[_SpySession]) -> None:
    first: Generator[Session] = session_module.get_db()
    second: Generator[Session] = session_module.get_db()
    assert next(first) is not next(second)
    first.close()
    second.close()
    assert spy.closed_calls == 2
