"""IDP data scope (02 §2, §6; 04 §8.2): who sees which source documents.

A reader sees documents of their own department or that they submitted. Company-wide readers
— ROLE-CEO (scope "Toàn doanh nghiệp", 02 §2), `idp:admin`, or a principal without a
department — see every document. The CEO rule matters since seed v3 (T-603b) places the CEO
in the Ban Giám đốc department.
"""

from __future__ import annotations

from app.core.deps import Principal
from app.modules.idp.models import SourceDocument


def sees_all_departments(user: Principal) -> bool:
    return user.role == "CEO" or user.has("idp:admin") or user.department_id is None


def document_visible(user: Principal, doc: SourceDocument) -> bool:
    if sees_all_departments(user) or doc.submitted_by == user.user_id:
        return True
    return doc.department_id is not None and doc.department_id == user.department_id
