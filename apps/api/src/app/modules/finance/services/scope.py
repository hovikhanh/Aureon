"""Finance data scope (`02` §5.3 marks in `auth/permission_matrix.py`, D-07) for REST.

- REV (`finance:read ◑r`): only inside an assigned review session. Records reach the reviewer
  through the IDP review, never through a general finance read → `403 FORBIDDEN_SCOPE`.
- MGR (`finance:* ◑d`): own department, for read and write. Budgets and expenses carry
  `department_id`; revenues, invoices, cash positions and forecasts are company records with no
  department, so nothing there is in a manager's scope (default deny, as DEC-212 for writes).
- Everyone else holding the permission: whole company (DIR already isolated by khối at the route).
- D-20 / R-DEC-199: invoices are company records, but a MGR reads (list + detail) the invoices
  they created themselves — `Invoice.created_by`, which is also the committer of an invoice
  written through the IDP review (the Action Registry runs `InvoiceService.create` as the
  reviewer). Invoices created by others stay `FORBIDDEN_SCOPE`; MGR writes stay denied.

Enforced where the REST caller is known. The IDP Action Registry calls the record services with
the reviewer as actor, under its own `idp:approve` scope, so those services stay scope-free.
"""

import uuid

from app.core.deps import Principal
from app.core.errors import ScopeDeniedError

DEPARTMENT_SCOPED_ROLES = frozenset({"MGR"})
REVIEW_SCOPED_ROLES = frozenset({"REV"})


def deny(what: str, **details: object) -> ScopeDeniedError:
    return ScopeDeniedError(
        f"{what} outside your scope", details={k: str(v) for k, v in details.items()}
    )


def require_reader(user: Principal) -> None:
    """Records that a scoped role may read (department-filtered for MGR by the service)."""
    if user.role in REVIEW_SCOPED_ROLES:
        raise ScopeDeniedError("finance records are readable only inside an assigned review")


def require_company_reader(user: Principal) -> None:
    """Company records (no `department_id`): out of reach of `◑r` and `◑d`."""
    require_reader(user)
    if user.role in DEPARTMENT_SCOPED_ROLES:
        raise deny("company finance records", role=user.role)


def invoice_creator_filter(user: Principal) -> uuid.UUID | None:
    """D-20: `created_by` filter of the invoice list — a MGR sees only their own invoices."""
    return user.user_id if user.role in DEPARTMENT_SCOPED_ROLES else None


def check_invoice_reader(user: Principal, created_by: uuid.UUID | None) -> None:
    """D-20: one invoice — a MGR reads it only when they created it."""
    if user.role in DEPARTMENT_SCOPED_ROLES and (created_by is None or created_by != user.user_id):
        raise deny("company invoice", role=user.role)


def require_company_writer(user: Principal) -> None:
    if user.role in DEPARTMENT_SCOPED_ROLES:
        raise deny("company finance records", role=user.role)


def department_filter(user: Principal, requested: uuid.UUID | None) -> uuid.UUID | None:
    """Effective `department_id` filter of a list; MGR is pinned to their department."""
    if user.role not in DEPARTMENT_SCOPED_ROLES:
        return requested
    if user.department_id is None or requested not in (None, user.department_id):
        raise deny("department", department_id=requested)
    return user.department_id


def check_department(user: Principal, department_id: uuid.UUID | None) -> None:
    """Single record / write target (MGR: own department only, no department = not theirs)."""
    if user.role in DEPARTMENT_SCOPED_ROLES and (
        user.department_id is None or department_id != user.department_id
    ):
        raise deny("department", department_id=department_id)
