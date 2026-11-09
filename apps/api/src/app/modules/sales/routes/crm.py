"""CRM routes — EP-SAL-10..13 (R-DEC-176, D-08 defaults, D-21; 10 §7.2.7).

Mounted under the sales router. Same pattern as `router.py`: one permission per route
(`sales:read` / `sales:write`, khối C), `Idem` on create / action POSTs, `IfMatch` + body
`version` on PATCH, `Page` on lists, soft DELETE → 204, commit at the end of the request.
"""

import uuid
from typing import Annotated, Any

from fastapi import Depends, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.concurrency import IfMatch, expected_version
from app.core.deps import Principal, get_db, require_pillar_permission
from app.core.envelope import Page
from app.core.idempotency import Idem
from app.core.pagination import PageParams, page_params
from app.core.routing import EnvelopeRouter
from app.modules.sales.schemas.crm import (
    ActivityCreate,
    ActivityOut,
    ActivityStatus,
    ActivityType,
    ActivityUpdate,
    ContactCreate,
    ContactOut,
    ContactUpdate,
    LeadConvert,
    LeadConvertOut,
    LeadCreate,
    LeadOut,
    LeadStatus,
    LeadUpdate,
)
from app.modules.sales.services import scope as sales_scope
from app.modules.sales.services.crm_service import (
    CrmService,
    activity_out,
    contact_out,
    lead_out,
)

router = EnvelopeRouter(tags=["sales"])

Db = Annotated[AsyncSession, Depends(get_db)]
PillarReader = Annotated[Principal, Depends(require_pillar_permission("sales:read"))]
Writer = Annotated[Principal, Depends(require_pillar_permission("sales:write"))]
Q = Annotated[str | None, Query(max_length=200)]


async def _reader(user: PillarReader) -> Principal:
    sales_scope.require_record_reader(user)  # REV outside a review → 403 FORBIDDEN_SCOPE
    return user


Reader = Annotated[Principal, Depends(_reader)]


# ---------- EP-SAL-10 leads ----------
@router.get("/sales/leads", response_model=list[LeadOut])
async def list_leads(
    db: Db, user: Reader,
    page: Annotated[PageParams, Depends(page_params(
        "code", "full_name", "company_name", "score", "status", "next_action_date", "updated_at",
    ))],
    q: Q = None, status: LeadStatus | None = None, owner_id: uuid.UUID | None = None,
) -> Any:  # fmt: skip
    items, total = await CrmService(db).list_leads(
        user, page, q=q, status=status, owner_id=owner_id
    )
    return Page(items=items, total=total, limit=page.limit, offset=page.offset)


@router.post("/sales/leads", response_model=LeadOut, status_code=201)
async def create_lead(body: LeadCreate, db: Db, user: Writer, idem: Idem) -> Any:
    if (hit := await idem.replay(body)) is not None:
        return LeadOut.model_validate(hit)
    out = await CrmService(db).create_lead(user, body)
    await db.commit()
    await idem.remember(out)
    return out


@router.get("/sales/leads/{lead_id}", response_model=LeadOut)
async def get_lead(lead_id: uuid.UUID, db: Db, user: Reader) -> Any:
    return lead_out(await CrmService(db).get_lead(user, lead_id))


@router.patch("/sales/leads/{lead_id}", response_model=LeadOut)
async def update_lead(
    lead_id: uuid.UUID, body: LeadUpdate, db: Db, user: Writer, if_match: IfMatch = None
) -> Any:
    exp = expected_version(if_match, body.version)
    out = await CrmService(db).update_lead(user, lead_id, body, exp)
    await db.commit()
    return out


@router.delete("/sales/leads/{lead_id}", status_code=204, response_class=Response)
async def delete_lead(lead_id: uuid.UUID, db: Db, user: Writer) -> Response:
    await CrmService(db).delete_lead(user, lead_id)
    await db.commit()
    return Response(status_code=204)


# ---------- EP-SAL-13 lead convert ----------
@router.post("/sales/leads/{lead_id}/convert", response_model=LeadConvertOut)
async def convert_lead(
    lead_id: uuid.UUID, body: LeadConvert, db: Db, user: Writer, idem: Idem
) -> Any:
    if (hit := await idem.replay(body)) is not None:
        return LeadConvertOut.model_validate(hit)
    out = await CrmService(db).convert_lead(user, lead_id, body)
    await db.commit()
    await idem.remember(out)
    return out


# ---------- EP-SAL-11 contacts ----------
@router.get("/sales/contacts", response_model=list[ContactOut])
async def list_contacts(
    db: Db, _: Reader,
    page: Annotated[PageParams, Depends(
        page_params("code", "first_name", "last_name", "updated_at")
    )],
    q: Q = None, client_id: uuid.UUID | None = None,
) -> Any:  # fmt: skip
    items, total = await CrmService(db).list_contacts(page, q=q, client_id=client_id)
    return Page(items=items, total=total, limit=page.limit, offset=page.offset)


@router.post("/sales/contacts", response_model=ContactOut, status_code=201)
async def create_contact(body: ContactCreate, db: Db, user: Writer, idem: Idem) -> Any:
    if (hit := await idem.replay(body)) is not None:
        return ContactOut.model_validate(hit)
    out = await CrmService(db).create_contact(user, body)
    await db.commit()
    await idem.remember(out)
    return out


@router.get("/sales/contacts/{contact_id}", response_model=ContactOut)
async def get_contact(contact_id: uuid.UUID, db: Db, _: Reader) -> Any:
    return contact_out(await CrmService(db).get_contact(contact_id))


@router.patch("/sales/contacts/{contact_id}", response_model=ContactOut)
async def update_contact(
    contact_id: uuid.UUID, body: ContactUpdate, db: Db, user: Writer, if_match: IfMatch = None
) -> Any:
    exp = expected_version(if_match, body.version)
    out = await CrmService(db).update_contact(user, contact_id, body, exp)
    await db.commit()
    return out


@router.delete("/sales/contacts/{contact_id}", status_code=204, response_class=Response)
async def delete_contact(contact_id: uuid.UUID, db: Db, user: Writer) -> Response:
    await CrmService(db).delete_contact(user, contact_id)
    await db.commit()
    return Response(status_code=204)


# ---------- EP-SAL-12 activities ----------
@router.get("/sales/activities", response_model=list[ActivityOut])
async def list_activities(
    db: Db, user: Reader,
    page: Annotated[PageParams, Depends(
        page_params("code", "start_at", "status", "type", "updated_at")
    )],
    q: Q = None, type_: Annotated[ActivityType | None, Query(alias="type")] = None,
    status: ActivityStatus | None = None,
    lead_id: uuid.UUID | None = None, client_id: uuid.UUID | None = None,
    contact_id: uuid.UUID | None = None, deal_id: uuid.UUID | None = None,
    owner_id: uuid.UUID | None = None,
) -> Any:  # fmt: skip
    filters = {
        "type": type_, "status": status, "lead_id": lead_id, "client_id": client_id,
        "contact_id": contact_id, "deal_id": deal_id, "owner_id": owner_id,
    }  # fmt: skip
    items, total = await CrmService(db).list_activities(user, page, filters=filters, q=q)
    return Page(items=items, total=total, limit=page.limit, offset=page.offset)


@router.post("/sales/activities", response_model=ActivityOut, status_code=201)
async def create_activity(body: ActivityCreate, db: Db, user: Writer, idem: Idem) -> Any:
    if (hit := await idem.replay(body)) is not None:
        return ActivityOut.model_validate(hit)
    out = await CrmService(db).create_activity(user, body)
    await db.commit()
    await idem.remember(out)
    return out


@router.get("/sales/activities/{activity_id}", response_model=ActivityOut)
async def get_activity(activity_id: uuid.UUID, db: Db, user: Reader) -> Any:
    return activity_out(await CrmService(db).get_activity(user, activity_id))


@router.patch("/sales/activities/{activity_id}", response_model=ActivityOut)
async def update_activity(
    activity_id: uuid.UUID, body: ActivityUpdate, db: Db, user: Writer, if_match: IfMatch = None
) -> Any:
    exp = expected_version(if_match, body.version)
    out = await CrmService(db).update_activity(user, activity_id, body, exp)
    await db.commit()
    return out


@router.delete("/sales/activities/{activity_id}", status_code=204, response_class=Response)
async def delete_activity(activity_id: uuid.UUID, db: Db, user: Writer) -> Response:
    await CrmService(db).delete_activity(user, activity_id)
    await db.commit()
    return Response(status_code=204)
