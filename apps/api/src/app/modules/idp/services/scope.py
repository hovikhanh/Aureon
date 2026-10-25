"""IDP data scope (02 §2, §6; 04 §8.2): who sees which source documents.

A reader sees documents of their own department or that they submitted. Company-wide readers
— ROLE-CEO (scope "Toàn doanh nghiệp", 02 §2), `idp:admin`, or a principal without a
department — see every document. The CEO rule matters since seed v3 (T-603b) places the CEO
in the Ban Giám đốc department.
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import ARRAY, ColumnElement, Select, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import Principal
from app.core.errors import ScopeDeniedError
from app.core.field_policy import STRUCTURE_ONLY_ROLES
from app.modules.idp.models import DocumentType, SourceDocument


def sees_all_departments(user: Principal) -> bool:
    return user.role == "CEO" or user.has("idp:admin") or user.department_id is None


def document_visible(user: Principal, doc: SourceDocument) -> bool:
    if sees_all_departments(user) or doc.submitted_by == user.user_id:
        return True
    return doc.department_id is not None and doc.department_id == user.department_id


# R-DEC-76: ADM holds `idp:read`/`idp:write` with scope `s` — only the org-structure doc type
# (#4 HR_ROSTER). `STRUCTURE_ONLY_ROLES` is the same `s` mark that limits `hr:read` (R-DEC-30).
STRUCTURE_DOC_TYPES = frozenset({"HR_ROSTER"})


def ensure_doc_type_scope(user: Principal, code: str | None) -> None:
    """403 FORBIDDEN_SCOPE when a structure-only role captures/commits another doc type.

    `code=None` (C3 upload left for the classifier) is refused too: such a role must preselect
    #4, otherwise classification could route the file to a type outside its scope.
    """
    if user.role in STRUCTURE_ONLY_ROLES and code not in STRUCTURE_DOC_TYPES:
        raise ScopeDeniedError(
            "document type outside idp scope `s`",
            details={"document_type": code, "allowed": sorted(STRUCTURE_DOC_TYPES)},
        )


async def structure_type_ids(db: AsyncSession) -> list[uuid.UUID]:
    rows = await db.execute(
        select(DocumentType.id).where(DocumentType.code.in_(STRUCTURE_DOC_TYPES))
    )
    return list(rows.scalars())


async def type_in_scope(db: AsyncSession, user: Principal, doc: SourceDocument) -> bool:
    """Read side of R-DEC-76: a structure-only role sees only #4 documents."""
    if user.role not in STRUCTURE_ONLY_ROLES:
        return True
    return doc.document_type_id in await structure_type_ids(db)


async def inbox_filter(db: AsyncSession, user: Principal) -> ColumnElement[bool] | None:
    """EP-DC-13 scope by role (10 §7.2.4 scope table; ADM per R-DEC-76). `None` = no filter.

    CEO: whole company · DIR: own submissions, documents they reviewed, or documents whose
    `pillars` meet their `scope_pillars` (empty scope = every pillar) · MGR: department +
    sub-departments + own · REV: current assignment + own · EMP: own · ADM (scope `s`): own
    #4 HR_ROSTER documents only. Unknown roles fall back to own documents (default deny).
    """
    from app.core.org_scope import department_subtree
    from app.modules.idp.models import ExtractionReview

    own = SourceDocument.submitted_by == user.user_id
    if user.role == "CEO":
        return None
    if user.role in STRUCTURE_ONLY_ROLES:
        return own & SourceDocument.document_type_id.in_(await structure_type_ids(db))
    if user.role == "DIR":
        if not user.scope_pillars:
            return None
        reviewed = select(ExtractionReview.source_document_id).where(
            ExtractionReview.reviewer_id == user.user_id
        )
        from sqlalchemy import cast, literal

        from app.core.enums import PILLAR

        wanted = cast(literal(sorted(user.scope_pillars), ARRAY(PILLAR)), ARRAY(PILLAR))
        pillars = SourceDocument.pillars.op("&&")(wanted)
        return or_(own, SourceDocument.id.in_(reviewed), pillars)
    if user.role == "MGR" and user.department_id is not None:
        depts = await department_subtree(db, [user.department_id])
        return or_(own, SourceDocument.department_id.in_(depts))
    if user.role == "REV":
        return or_(own, SourceDocument.id.in_(assigned_to(user)))
    return own


def assigned_to(user: Principal) -> Select[Any]:
    """Documents whose current review assignment names the caller or the caller's role pool
    (`assign_initial_review` → `to_role_code="REV"`, 04 §8.2 "hàng chờ theo vai trò")."""
    from app.modules.idp.models import ReviewAssignment

    return select(ReviewAssignment.source_document_id).where(
        ReviewAssignment.is_current.is_(True),
        (ReviewAssignment.to_user_id == user.user_id)
        | (ReviewAssignment.to_user_id.is_(None) & (ReviewAssignment.to_role_code == user.role)),
    )


async def in_review_session(db: AsyncSession, user: Principal, doc: SourceDocument) -> bool:
    """REV inside an assigned review session of `doc` (10 §7.2.4 scope table: REV reviews the
    queue it is assigned; CLAUDE.md §5.3: level 4 readable in that session)."""
    if user.role != "REV":
        return False
    from app.modules.idp.models import ReviewAssignment

    stmt = assigned_to(user).where(ReviewAssignment.source_document_id == doc.id).limit(1)
    return (await db.execute(stmt)).first() is not None


async def review_visible(db: AsyncSession, user: Principal, doc: SourceDocument) -> bool:
    """Review/approve side (EP-DC-05..10, 08): own department/submissions, or an assigned
    review session (REV role pool)."""
    return document_visible(user, doc) or await in_review_session(db, user, doc)


async def capture_visible(db: AsyncSession, user: Principal, doc: SourceDocument) -> bool:
    """GET-by-id side of the `/data-capture/*` endpoints (EP-DC-14, 18..21, 24, 25): the same
    row scope as the inbox (10 §7.2.4 scope table — EMP own only, MGR department subtree, DIR
    khối, REV assigned + own, ADM own #4) plus the caller's own submissions and current review
    sessions. Wider v2.1 `document_visible` (same department) is not used here."""
    if not await type_in_scope(db, user, doc):
        return False
    if doc.submitted_by == user.user_id or await in_review_session(db, user, doc):
        return True
    from app.modules.idp.repositories import SourceDocumentRepository

    scope = await inbox_filter(db, user)
    return scope is None or await SourceDocumentRepository(db).matches(doc.id, scope)


async def lineage_visible(db: AsyncSession, user: Principal, doc: SourceDocument) -> bool:
    """Source side of EP-DC-26 (R-DEC-64): the document is in the caller's capture scope — the
    same row filter as the inbox (REV: only assigned review sessions; EMP: own submissions)."""
    from app.modules.idp.repositories import SourceDocumentRepository

    if not await type_in_scope(db, user, doc):
        return False
    scope = await inbox_filter(db, user)
    return scope is None or await SourceDocumentRepository(db).matches(doc.id, scope)
