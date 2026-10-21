"""TC-EXE-003 (T-133) — task 7-status machine + execution scope helpers (pure)."""

import uuid
from datetime import date

import pytest
from sqlalchemy import false

from app.core.deps import Principal
from app.core.errors import ScopeDeniedError
from app.modules.execution.models import Task
from app.modules.execution.services import scope
from app.modules.execution.services.task_rules import TRANSITIONS, can_transition, is_overdue


def test_seven_statuses_and_transitions() -> None:
    assert set(TRANSITIONS) == {
        "backlog", "todo", "in_progress", "blocked", "in_review", "done", "cancelled"
    }  # fmt: skip
    assert can_transition("todo", "todo")
    assert can_transition("in_review", "done")
    assert can_transition("done", "in_progress")
    assert not can_transition("blocked", "done")
    assert not can_transition("cancelled", "done")
    assert not can_transition("nope", "done")


def test_overdue() -> None:
    d = date(2037, 1, 10)
    assert is_overdue("todo", d, date(2037, 1, 11))
    assert not is_overdue("todo", d, d)
    assert not is_overdue("done", d, date(2037, 2, 1))
    assert not is_overdue("todo", None, date(2037, 2, 1))


def _p(role: str, dept: uuid.UUID | None = None) -> Principal:
    return Principal(user_id=uuid.uuid4(), role=role, department_id=dept)


def test_scope_levels() -> None:
    assert scope.level(_p("CEO")) == "all"
    assert scope.level(_p("HR_MANAGER"), "query") == "all"
    assert scope.level(_p("HR_MANAGER"), "read") == "d"
    assert scope.level(_p("EMPLOYEE"), "query") == "o"
    assert scope.predicate(_p("CEO"), "read", dept=Task.department_id) is None
    none = scope.predicate(_p("MANAGER"), "read", dept=Task.department_id)
    assert none is not None and str(none) == str(false())
    dept = uuid.uuid4()
    mgr = _p("MANAGER", dept)
    assert scope.allowed(mgr, "read", dept=dept, owners=())
    assert not scope.allowed(mgr, "read", dept=uuid.uuid4(), owners=())
    assert scope.allowed(mgr, "read", dept=None, owners=(mgr.user_id,))
    with pytest.raises(ScopeDeniedError):
        scope.check(_p("EMPLOYEE", dept), "read", dept=dept, owners=())


def test_pin_department() -> None:
    dept = uuid.uuid4()
    assert scope.pin_department(_p("CEO"), dept) == dept
    assert scope.pin_department(_p("MANAGER", dept), None) == dept
    assert scope.pin_department(_p("EMPLOYEE", dept), None) == dept
    with pytest.raises(ScopeDeniedError):
        scope.pin_department(_p("EMPLOYEE", dept), uuid.uuid4())
    with pytest.raises(ScopeDeniedError):
        scope.pin_department(_p("MANAGER"), None)
    emp = _p("EMPLOYEE")
    scope.require_self(emp, emp.user_id, None, field="owner_id")
    scope.require_self(_p("CEO"), uuid.uuid4(), field="owner_id")
    with pytest.raises(ScopeDeniedError):
        scope.require_self(emp, uuid.uuid4(), field="owner_id")
