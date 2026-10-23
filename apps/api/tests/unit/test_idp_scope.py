"""IDP document scope (02 §2/§6, 04 §8.2): department-scoped readers vs company-wide readers."""

from __future__ import annotations

import uuid
from types import SimpleNamespace
from typing import Any

from app.core.deps import Principal
from app.modules.auth.permission_matrix import ROLE_PERMISSIONS
from app.modules.idp.services.scope import document_visible, sees_all_departments

DEPT_A, DEPT_B = uuid.uuid4(), uuid.uuid4()


def _p(role: str, dept: uuid.UUID | None, uid: uuid.UUID | None = None) -> Principal:
    perms = frozenset(ROLE_PERMISSIONS[role])
    return Principal(user_id=uid or uuid.uuid4(), role=role, permissions=perms, department_id=dept)


def _doc(dept: uuid.UUID | None, submitted_by: uuid.UUID | None = None) -> Any:
    return SimpleNamespace(department_id=dept, submitted_by=submitted_by or uuid.uuid4())


def test_company_wide_readers() -> None:
    assert sees_all_departments(_p("CEO", DEPT_A))  # CEO in BGĐ still sees all (seed v3)
    assert sees_all_departments(_p("ADM", DEPT_A))  # idp:admin
    assert sees_all_departments(_p("DIR", None))  # no department
    assert not sees_all_departments(_p("DIR", DEPT_A))
    assert not sees_all_departments(_p("REV", DEPT_A))


def test_department_scope_and_own_submissions() -> None:
    uid = uuid.uuid4()
    rev = _p("REV", DEPT_A, uid)
    assert document_visible(rev, _doc(DEPT_A))
    assert not document_visible(rev, _doc(DEPT_B))
    assert not document_visible(rev, _doc(None))
    assert document_visible(rev, _doc(DEPT_B, submitted_by=uid))
    assert document_visible(_p("CEO", DEPT_A), _doc(DEPT_B))
