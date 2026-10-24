"""T-626 — StrategicObjective progress rule (05 §2.6) + `goal_scope` skeleton (R-DEC-57)."""

import uuid
from decimal import Decimal

import pytest

from app.core.deps import Principal
from app.core.errors import PermissionDeniedError, ScopeDeniedError
from app.modules.execution.services import goal_scope
from app.modules.execution.services.strategy_service import so_progress


def test_so_progress_rule() -> None:
    assert so_progress([(100, 30), (0, 10)], [50]) == Decimal("75.0000")
    assert so_progress([(40, 0), (80, 0)], []) == Decimal("60.0000")  # weights 0 → plain mean
    assert so_progress([], [Decimal("10"), Decimal("21")]) == Decimal("15.5000")
    assert so_progress([], []) == Decimal(0)
    assert so_progress([(74, 30), (70, 25), (30, 25), (58, 20)], []) == Decimal("58.8000")


def _p(role: str, pillars: tuple[str, ...] = (), dept: uuid.UUID | None = None) -> Principal:
    return Principal(user_id=uuid.uuid4(), role=role, department_id=dept,
                     scope_pillars=frozenset(pillars))  # fmt: skip


def test_strategy_writer_is_ceo_only() -> None:
    goal_scope.require_strategy_writer(_p("CEO"))
    for role in ("DIR", "MGR", "EMP"):
        with pytest.raises(PermissionDeniedError) as e:
            goal_scope.require_strategy_writer(_p(role))
        assert e.value.code == "FORBIDDEN_ROLE"


def test_so_write_by_pillar() -> None:
    goal_scope.check_so_write(_p("CEO"), None)
    goal_scope.check_so_write(_p("DIR", ("F",)), "F")
    goal_scope.check_so_write(_p("DIR"), "C")  # empty scope_pillars → every pillar
    with pytest.raises(ScopeDeniedError):
        goal_scope.check_so_write(_p("DIR", ("F",)), "C")
    with pytest.raises(ScopeDeniedError):
        goal_scope.check_so_write(_p("DIR", ("F",)), None)
    with pytest.raises(PermissionDeniedError) as e:
        goal_scope.check_so_write(_p("MGR"), "F")
    assert e.value.code == "FORBIDDEN_ROLE"


def test_so_readable() -> None:
    dept, other = uuid.uuid4(), uuid.uuid4()
    emp = _p("EMP", dept=dept)
    assert goal_scope.so_readable(emp, dept=None, owner=uuid.uuid4(), pillar="F")  # company
    assert goal_scope.so_readable(emp, dept=other, owner=emp.user_id, pillar=None)  # own
    assert not goal_scope.so_readable(emp, dept=other, owner=uuid.uuid4(), pillar="F")
    assert goal_scope.so_readable(_p("MGR", dept=dept), dept=dept, owner=uuid.uuid4(), pillar=None)
    assert goal_scope.so_readable(_p("DIR", ("F",)), dept=other, owner=uuid.uuid4(), pillar="F")
    assert not goal_scope.so_readable(_p("DIR", ("F",)), dept=other, owner=uuid.uuid4(),
                                      pillar="C")  # fmt: skip
    assert goal_scope.so_predicate(_p("CEO"), dept=None, owner=None, pillar=None) is None
