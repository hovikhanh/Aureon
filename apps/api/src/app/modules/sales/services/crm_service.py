"""CRM service — Lead / Contact / Activity + lead convert (R-DEC-176, D-08 defaults, D-21).

Same rules as `SalesService`: every mutation writes `ENT-AuditLog` in the caller's transaction
(the route commits), scope from `services/scope.py` (02 §6.2):
- leads / activities carry `department_id` → MANAGER limited to (and pinned to) their department;
- contacts follow their client (no department) → MANAGER may read and create, not update/delete;
- REV is refused at the route (`require_record_reader`), CEO has full access (D-21).
Duplicates (exact e-mail or phone) warn with `409 DUPLICATE_RESOURCE` + `details.similar` unless
the body says `confirm_duplicate: true` (then audited as `sales.<entity>_duplicate_confirmed`).
No outbox event: the registry (10 §9.2) has none for these entities (CLAUDE.md §5.4).
"""

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import ColumnElement
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import record_audit
from app.core.deps import Principal
from app.core.errors import (
    BusinessRuleError,
    ConflictStateError,
    DuplicateResourceError,
    NotFoundError,
)
from app.core.pagination import PageParams
from app.modules.sales.models import Lead, SalesActivity, SalesContact
from app.modules.sales.repositories import (
    ActivityRepository,
    ContactRepository,
    LeadRepository,
    digits,
    search_clause,
)
from app.modules.sales.schemas import ClientCreate, Contact, DealCreate
from app.modules.sales.schemas.crm import (
    ActivityCreate,
    ActivityOut,
    ActivityUpdate,
    ContactCreate,
    ContactOut,
    ContactUpdate,
    LeadConvert,
    LeadConvertOut,
    LeadCreate,
    LeadOut,
    LeadUpdate,
    SimilarRecord,
)
from app.modules.sales.services import scope
from app.modules.sales.services.sales_service import SalesService, client_out

RULE = "R-DEC-176"
CLOSED_LEAD = frozenset({"converted", "disqualified"})
LINKS = ("lead_id", "client_id", "contact_id", "deal_id")


def lead_out(x: Lead) -> LeadOut:
    return LeadOut.model_validate(x)


def contact_out(x: SalesContact) -> ContactOut:
    full = " ".join(p for p in (x.last_name, x.first_name) if p)
    return ContactOut(
        id=x.id, version=x.version, created_at=x.created_at, updated_at=x.updated_at,
        code=x.code, client_id=x.client_id, first_name=x.first_name, last_name=x.last_name,
        full_name=full, job_title=x.job_title, department=x.department, email=x.email,
        phone=x.phone, roles=list(x.roles), decision_authority=x.decision_authority,
        influence_level=x.influence_level, owner_id=x.owner_id, notes=x.notes,
    )  # fmt: skip


def activity_out(x: SalesActivity) -> ActivityOut:
    return ActivityOut.model_validate(x)


def split_name(full_name: str) -> tuple[str, str | None]:
    """Vietnamese order "Họ Đệm Tên" → (first_name = Tên, last_name = Họ Đệm)."""
    parts = full_name.split()
    if len(parts) <= 1:
        return full_name.strip(), None
    return parts[-1], " ".join(parts[:-1])


def _without_nulls(data: dict[str, Any], *not_null: str) -> dict[str, Any]:
    """PATCH: an explicit `null` on a NOT NULL column means "leave as is"."""
    return {k: v for k, v in data.items() if v is not None or k not in not_null}


def _rule(msg: str, field: str) -> BusinessRuleError:
    return BusinessRuleError(msg, details={"field": field, "rule": RULE})


def _similar(rows: Any, email: str | None, phone: str | None, name: Any) -> list[SimilarRecord]:
    out = []
    for r in rows:
        match: list[Any] = []
        if email and r.email and r.email.lower() == email.strip().lower():
            match.append("email")
        if phone and r.phone and digits(r.phone) == digits(phone):
            match.append("phone")
        out.append(SimilarRecord(id=r.id, code=r.code, name=name(r), match=match))
    return out


class CrmService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.leads = LeadRepository(db)
        self.contacts = ContactRepository(db)
        self.activities = ActivityRepository(db)
        self.sales = SalesService(db)

    async def _audit(
        self, action: str, table: str, obj: Any, before: Any = None, after: Any = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:  # fmt: skip
        def snap(v: Any) -> Any:  # email / phone keys are masked by `record_audit` (level 3)
            return v.model_dump(mode="json") if v is not None else None

        await record_audit(
            self.db, action=action, target_schema="sales", target_table=table,
            target_id=getattr(obj, "id", None), before=snap(before), after=snap(after),
            metadata=metadata,
        )  # fmt: skip

    async def _check_duplicates(
        self, kind: str, similar: list[SimilarRecord], confirmed: bool
    ) -> dict[str, Any] | None:
        """R-DEC-176 d: warn (409) unless confirmed; returns the audit metadata when confirmed."""
        if not similar:
            return None
        if not confirmed:
            field = "email" if any("email" in s.match for s in similar) else "phone"
            raise DuplicateResourceError(
                f"possible duplicate {kind} (same e-mail or phone)",
                details={
                    "field": field, "confirm_with": "confirm_duplicate",
                    "similar": [s.model_dump(mode="json") for s in similar],
                },
            )  # fmt: skip
        return {"similar_ids": [str(s.id) for s in similar]}

    # ---------- EP-SAL-10 leads ----------
    def _lead_scope(self, user: Principal) -> list[ColumnElement[bool]]:
        if scope.is_department_scoped(user):
            return [Lead.department_id == user.department_id]
        return []

    async def list_leads(
        self, user: Principal, page: PageParams, *, q: str | None, status: str | None,
        owner_id: uuid.UUID | None,
    ) -> tuple[list[LeadOut], int]:  # fmt: skip
        where = self._lead_scope(user)
        if q:
            where.append(search_clause(
                q, Lead.code, Lead.full_name, Lead.company_name, Lead.email, Lead.phone
            ))  # fmt: skip
        filters: dict[str, Any] = {}
        if status:
            filters["status"] = status
        if owner_id:
            filters["owner_id"] = owner_id
        items, total = await self.leads.list_page(
            limit=page.limit, offset=page.offset, sort_by=page.sort_by, order=page.order,
            filters=filters, where=where,
        )  # fmt: skip
        return [lead_out(x) for x in items], total

    async def get_lead(self, user: Principal, id_: uuid.UUID) -> Lead:
        obj = await self.leads.get(id_)
        if obj is None:
            raise NotFoundError("lead not found")
        scope.check_department(user, obj.department_id)
        return obj

    def _department(self, user: Principal, requested: uuid.UUID | None) -> uuid.UUID | None:
        """MANAGER: always their own department (a different one → 403 FORBIDDEN_SCOPE)."""
        if scope.is_department_scoped(user):
            if requested is not None:
                scope.check_department(user, requested)
            return user.department_id
        return requested

    async def create_lead(self, user: Principal, body: LeadCreate) -> LeadOut:
        scope.require_record_writer(user)
        if not (body.email or body.phone):
            raise _rule("a lead needs an e-mail or a phone", "email")
        rows = await self.leads.same_channel(body.email, body.phone, *self._lead_scope(user))
        similar = _similar(rows, body.email, body.phone, lambda r: r.full_name)
        meta = await self._check_duplicates("lead", similar, body.confirm_duplicate)
        data = body.model_dump(exclude={"confirm_duplicate", "owner_id", "department_id"})
        obj = await self.leads.create(
            **data, owner_id=body.owner_id or user.user_id,
            department_id=self._department(user, body.department_id),
            source="MANUAL", created_by=user.user_id,
        )  # fmt: skip
        await self.db.refresh(obj)
        out = lead_out(obj)
        await self._audit("sales.lead_create", "leads", obj, after=out)
        if meta:
            await self._audit("sales.lead_duplicate_confirmed", "leads", obj, metadata=meta)
        return out

    async def update_lead(
        self, user: Principal, id_: uuid.UUID, body: LeadUpdate, expected: int
    ) -> LeadOut:
        scope.require_record_writer(user)
        obj = await self.get_lead(user, id_)
        if obj.status == "converted":
            raise ConflictStateError(
                "a converted lead is read-only", details={"status": "converted"}
            )
        before = lead_out(obj)
        data = _without_nulls(
            body.model_dump(exclude_unset=True, exclude={"version"}),
            "full_name",
            "owner_id",
            "currency",
            "score",
            "status",
        )
        if "department_id" in data:
            data["department_id"] = self._department(user, data["department_id"])
        email = data.get("email", obj.email)
        phone = data.get("phone", obj.phone)
        if not (email or phone):
            raise _rule("a lead needs an e-mail or a phone", "email")
        data["updated_by"] = user.user_id
        await self.leads.update(obj, expected_version=expected, **data)
        await self.db.refresh(obj)
        out = lead_out(obj)
        await self._audit("sales.lead_update", "leads", obj, before, out)
        return out

    async def delete_lead(self, user: Principal, id_: uuid.UUID) -> None:
        scope.require_record_writer(user)
        obj = await self.get_lead(user, id_)
        before = lead_out(obj)
        obj.updated_by = user.user_id
        await self.leads.soft_delete(obj)
        await self._audit("sales.lead_delete", "leads", obj, before=before)

    # ---------- EP-SAL-13 convert ----------
    async def convert_lead(
        self, user: Principal, id_: uuid.UUID, body: LeadConvert
    ) -> LeadConvertOut:
        """Lead → Client (new or linked) + Contact (+ Deal) in the request transaction."""
        scope.require_record_writer(user)
        lead = await self.get_lead(user, id_)
        await self.leads.lock(lead)
        if lead.status in CLOSED_LEAD:
            raise ConflictStateError(
                f"lead is {lead.status}", details={"status": lead.status, "rule": RULE}
            )
        if body.create_deal and body.expected_close_date is None:
            raise _rule("expected_close_date is required to create a deal", "expected_close_date")
        if body.create_deal and not (body.deal_value or lead.budget):
            raise _rule("deal_value is required (the lead has no budget)", "deal_value")
        before = lead_out(lead)
        if body.client_id is not None:
            existing = await self.sales.clients.get(body.client_id)
            if existing is None:
                raise _rule("client does not exist", "client_id")
            client, created = client_out(existing), False
        else:
            client = await self.sales.create_client(user, ClientCreate(
                name=lead.company_name or lead.full_name, industry=lead.industry,
                status="prospect", account_owner_id=lead.owner_id,
                contacts=[Contact(name=lead.full_name, email=lead.email, phone=lead.phone)],
            ))  # fmt: skip
            created = True
        first, last = split_name(lead.full_name)
        contact = await self._insert_contact(user, {
            "client_id": client.id, "first_name": first, "last_name": last,
            "job_title": lead.job_title, "email": lead.email, "phone": lead.phone,
            "roles": [], "owner_id": lead.owner_id,
        })  # fmt: skip
        deal = None
        if body.create_deal:
            if body.expected_close_date is None:  # checked above, narrowed for mypy
                raise _rule("expected_close_date is required", "expected_close_date")
            deal = await self.sales.create_deal(user, DealCreate(
                name=body.deal_name or f"{client.name} — {lead.code}", client_id=client.id,
                deal_value=body.deal_value or lead.budget or 0, currency=lead.currency,
                probability_pct=body.probability_pct,
                expected_close_date=body.expected_close_date,
                owner_id=lead.owner_id, department_id=lead.department_id,
            ))  # fmt: skip
        await self.leads.update(
            lead, status="converted", converted_client_id=client.id,
            converted_contact_id=contact.id, converted_deal_id=deal.id if deal else None,
            converted_at=datetime.now(UTC), updated_by=user.user_id,
        )  # fmt: skip
        # the lead's activity history follows it to the account (timeline of the new client)
        await self.activities.move_lead_history(lead.id, client.id, contact.id, user.user_id)
        await self.db.refresh(lead)
        out = lead_out(lead)
        await self._audit("sales.lead_convert", "leads", lead, before, out, metadata={
            "client_created": created, "client_id": str(client.id),
            "contact_id": str(contact.id), "deal_id": str(deal.id) if deal else None,
        })  # fmt: skip
        return LeadConvertOut(
            lead=out, client=client, client_created=created, contact=contact, deal=deal
        )

    # ---------- EP-SAL-11 contacts ----------
    async def list_contacts(
        self, page: PageParams, *, q: str | None, client_id: uuid.UUID | None
    ) -> tuple[list[ContactOut], int]:
        where: list[ColumnElement[bool]] = []
        if q:
            where.append(search_clause(
                q, SalesContact.code, SalesContact.first_name, SalesContact.last_name,
                SalesContact.email, SalesContact.phone, SalesContact.job_title,
            ))  # fmt: skip
        filters = {"client_id": client_id} if client_id else {}
        items, total = await self.contacts.list_page(
            limit=page.limit, offset=page.offset, sort_by=page.sort_by, order=page.order,
            filters=filters, where=where,
        )  # fmt: skip
        return [contact_out(x) for x in items], total

    async def get_contact(self, id_: uuid.UUID) -> SalesContact:
        obj = await self.contacts.get(id_)
        if obj is None:
            raise NotFoundError("contact not found")
        return obj

    async def _require_client(self, client_id: uuid.UUID) -> None:
        if await self.sales.clients.get(client_id) is None:
            raise _rule("client does not exist", "client_id")

    async def _insert_contact(self, user: Principal, data: dict[str, Any]) -> ContactOut:
        obj = await self.contacts.create(**data, source="MANUAL", created_by=user.user_id)
        await self.db.refresh(obj)
        out = contact_out(obj)
        await self._audit("sales.contact_create", "contacts", obj, after=out)
        return out

    async def create_contact(self, user: Principal, body: ContactCreate) -> ContactOut:
        scope.require_record_writer(user)  # MANAGER may create (needed with a new client)
        await self._require_client(body.client_id)
        rows = await self.contacts.same_channel(body.email, body.phone)
        similar = _similar(rows, body.email, body.phone, lambda r: contact_out(r).full_name)
        meta = await self._check_duplicates("contact", similar, body.confirm_duplicate)
        data = body.model_dump(exclude={"confirm_duplicate", "owner_id"})
        data["roles"] = list(dict.fromkeys(body.roles))
        out = await self._insert_contact(user, {**data, "owner_id": body.owner_id or user.user_id})
        if meta:
            await self._audit("sales.contact_duplicate_confirmed", "contacts", out, metadata=meta)
        return out

    async def update_contact(
        self, user: Principal, id_: uuid.UUID, body: ContactUpdate, expected: int
    ) -> ContactOut:
        scope.require_full_writer(user)  # no department → MANAGER excluded (DEC-193)
        obj = await self.get_contact(id_)
        before = contact_out(obj)
        data = _without_nulls(
            body.model_dump(exclude_unset=True, exclude={"version"}),
            "client_id",
            "first_name",
            "roles",
        )
        if "client_id" in data:
            await self._require_client(data["client_id"])
        if "roles" in data:
            data["roles"] = list(dict.fromkeys(data["roles"]))
        data["updated_by"] = user.user_id
        await self.contacts.update(obj, expected_version=expected, **data)
        await self.db.refresh(obj)
        out = contact_out(obj)
        await self._audit("sales.contact_update", "contacts", obj, before, out)
        return out

    async def delete_contact(self, user: Principal, id_: uuid.UUID) -> None:
        scope.require_full_writer(user)
        obj = await self.get_contact(id_)
        before = contact_out(obj)
        obj.updated_by = user.user_id
        await self.contacts.soft_delete(obj)
        await self._audit("sales.contact_delete", "contacts", obj, before=before)

    # ---------- EP-SAL-12 activities ----------
    async def list_activities(
        self, user: Principal, page: PageParams, *, filters: dict[str, Any], q: str | None
    ) -> tuple[list[ActivityOut], int]:
        where: list[ColumnElement[bool]] = []
        if scope.is_department_scoped(user):
            where.append(SalesActivity.department_id == user.department_id)
        if q:
            where.append(search_clause(q, SalesActivity.code, SalesActivity.subject))
        clean = {k: v for k, v in filters.items() if v is not None}
        items, total = await self.activities.list_page(
            limit=page.limit, offset=page.offset, sort_by=page.sort_by, order=page.order,
            filters=clean, where=where,
        )  # fmt: skip
        return [activity_out(x) for x in items], total

    async def get_activity(self, user: Principal, id_: uuid.UUID) -> SalesActivity:
        obj = await self.activities.get(id_)
        if obj is None:
            raise NotFoundError("activity not found")
        scope.check_department(user, obj.department_id)
        return obj

    async def _links(self, user: Principal, data: dict[str, Any]) -> uuid.UUID | None:
        """Validate linked records (in scope) and fill `client_id` from the contact / deal.

        Returns the department inherited from the linked deal or lead (non-MANAGER callers).
        """
        dept: uuid.UUID | None = None
        if data.get("deal_id"):
            deal = await self.sales.deals.get(data["deal_id"])
            if deal is None:
                raise _rule("deal does not exist", "deal_id")
            scope.check_department(user, deal.department_id)
            data["client_id"] = data.get("client_id") or deal.client_id
            dept = deal.department_id
        if data.get("lead_id"):
            lead = await self.leads.get(data["lead_id"])
            if lead is None:
                raise _rule("lead does not exist", "lead_id")
            scope.check_department(user, lead.department_id)
            dept = dept or lead.department_id
        if data.get("contact_id"):
            contact = await self.contacts.get(data["contact_id"])
            if contact is None:
                raise _rule("contact does not exist", "contact_id")
            data["client_id"] = data.get("client_id") or contact.client_id
        if data.get("client_id"):
            await self._require_client(data["client_id"])
        return dept

    @staticmethod
    def _times(start: datetime, end: datetime | None) -> None:
        if end is not None and end < start:
            raise _rule("end_at must be >= start_at", "end_at")

    async def create_activity(self, user: Principal, body: ActivityCreate) -> ActivityOut:
        scope.require_record_writer(user)
        data = body.model_dump(exclude={"owner_id", "department_id"})
        if not any(data[k] for k in LINKS):
            raise _rule("link the activity to a lead, client, contact or deal", "client_id")
        self._times(body.start_at, body.end_at)
        inherited = await self._links(user, data)
        obj = await self.activities.create(
            **data, owner_id=body.owner_id or user.user_id,
            department_id=self._department(user, body.department_id or inherited),
            source="MANUAL", created_by=user.user_id,
        )  # fmt: skip
        await self.db.refresh(obj)
        out = activity_out(obj)
        await self._audit("sales.activity_create", "activities", obj, after=out)
        return out

    async def update_activity(
        self, user: Principal, id_: uuid.UUID, body: ActivityUpdate, expected: int
    ) -> ActivityOut:
        scope.require_record_writer(user)
        obj = await self.get_activity(user, id_)
        before = activity_out(obj)
        data = _without_nulls(
            body.model_dump(exclude_unset=True, exclude={"version"}),
            "type",
            "subject",
            "owner_id",
            "start_at",
            "status",
        )
        if "department_id" in data:
            data["department_id"] = self._department(user, data["department_id"])
        if any(k in data for k in LINKS):
            links = {k: data.get(k, getattr(obj, k)) for k in LINKS}
            if not any(links.values()):
                raise _rule("link the activity to a lead, client, contact or deal", "client_id")
            await self._links(user, links)  # re-checks scope, may fill client_id
            data.update(links)
        self._times(data.get("start_at", obj.start_at), data.get("end_at", obj.end_at))
        data["updated_by"] = user.user_id
        await self.activities.update(obj, expected_version=expected, **data)
        await self.db.refresh(obj)
        out = activity_out(obj)
        await self._audit("sales.activity_update", "activities", obj, before, out)
        return out

    async def delete_activity(self, user: Principal, id_: uuid.UUID) -> None:
        scope.require_record_writer(user)
        obj = await self.get_activity(user, id_)
        before = activity_out(obj)
        obj.updated_by = user.user_id
        await self.activities.soft_delete(obj)
        await self._audit("sales.activity_delete", "activities", obj, before=before)
