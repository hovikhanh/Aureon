"""IDP data scope (02 §2, §6; 04 §8.2): who sees which source documents.

A reader sees documents of their own department or that they submitted. Company-wide readers
— ROLE-CEO (scope "Toàn doanh nghiệp", 02 §2), `idp:admin`, or a principal without a
department — see every document. The CEO rule matters since seed v3 (T-603b) places the CEO
in the Ban Giám đốc department.
"""

from __future__ import annotations

import uuid

from sqlalchemy import select
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
