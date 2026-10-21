"""HTTP routes for `sales` — EP-70..78 (10 §3.7, §4.7).

Same pattern as finance: one permission per route, `Idem` on create / action POSTs,
`IfMatch` + body `version` on PATCH, `Page` on lists, commit at the end of the request.
"""

import uuid
from datetime import date
from typing import Annotated, Any

from fastapi import Depends, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.concurrency import IfMatch, expected_version
from app.core.deps import Principal, get_db, require_permission
from app.core.envelope import Page
from app.core.idempotency import Idem
from app.core.pagination import PageParams, page_params
from app.core.routing import EnvelopeRouter
from app.modules.sales.schemas import (
    ClientCreate,
    ClientOut,
    ClientUpdate,
    DealCreate,
    DealOut,
    DealStage,
    DealUpdate,
    StageChange,
    StageHistoryOut,
)
from app.modules.sales.services.sales_service import SalesService, client_out, deal_out

router = EnvelopeRouter(tags=["sales"])

Db = Annotated[AsyncSession, Depends(get_db)]
Reader = Annotated[Principal, Depends(require_permission("sales:read"))]
Writer = Annotated[Principal, Depends(require_permission("sales:write"))]
Querier = Annotated[Principal, Depends(require_permission("sales:query"))]


# ---------- EP-71 clients ----------
@router.get("/sales/clients", response_model=list[ClientOut])
async def list_clients(
    db: Db, _: Reader,
    page: Annotated[PageParams, Depends(page_params("name", "updated_at"))],
    q: Annotated[str | None, Query(max_length=200)] = None, industry: str | None = None,
) -> Any:  # fmt: skip
    items, total = await SalesService(db).list_clients(page, q=q, industry=industry)
    return Page(items=items, total=total, limit=page.limit, offset=page.offset)


@router.post("/sales/clients", response_model=ClientOut, status_code=201)
async def create_client(body: ClientCreate, db: Db, user: Writer, idem: Idem) -> Any:
    if (hit := await idem.replay(body)) is not None:
        return ClientOut.model_validate(hit)
    out = await SalesService(db).create_client(user, body)
    await db.commit()
    await idem.remember(out)
    return out


@router.get("/sales/clients/{client_id}", response_model=ClientOut)
async def get_client(client_id: uuid.UUID, db: Db, _: Reader) -> Any:
    return client_out(await SalesService(db).get_client(client_id))


@router.patch("/sales/clients/{client_id}", response_model=ClientOut)
async def update_client(
    client_id: uuid.UUID, body: ClientUpdate, db: Db, user: Writer, if_match: IfMatch = None
) -> Any:
    exp = expected_version(if_match, body.version)
    out = await SalesService(db).update_client(user, client_id, body, exp)
    await db.commit()
    return out


@router.delete("/sales/clients/{client_id}", status_code=204, response_class=Response)
async def delete_client(client_id: uuid.UUID, db: Db, user: Writer) -> Response:
    await SalesService(db).delete_client(user, client_id)
    await db.commit()
    return Response(status_code=204)


# ---------- EP-72 deals ----------
@router.get("/sales/deals", response_model=list[DealOut])
async def list_deals(
    db: Db, user: Reader,
    page: Annotated[PageParams, Depends(
        page_params("deal_value", "expected_close_date", "weighted_value", "updated_at")
    )],
    stage: DealStage | None = None, owner_id: uuid.UUID | None = None,
    client_id: uuid.UUID | None = None, expected_close_from: date | None = None,
    expected_close_to: date | None = None,
) -> Any:  # fmt: skip
    items, total = await SalesService(db).list_deals(
        user, page, stage=stage, owner_id=owner_id, client_id=client_id,
        close_from=expected_close_from, close_to=expected_close_to,
    )  # fmt: skip
    return Page(items=items, total=total, limit=page.limit, offset=page.offset)


@router.post("/sales/deals", response_model=DealOut, status_code=201)
async def create_deal(body: DealCreate, db: Db, user: Writer, idem: Idem) -> Any:
    if (hit := await idem.replay(body)) is not None:
        return DealOut.model_validate(hit)
    out = await SalesService(db).create_deal(user, body)
    await db.commit()
    await idem.remember(out)
    return out


@router.get("/sales/deals/{deal_id}", response_model=DealOut)
async def get_deal(deal_id: uuid.UUID, db: Db, user: Reader) -> Any:
    return deal_out(await SalesService(db).get_deal(user, deal_id))


@router.patch("/sales/deals/{deal_id}", response_model=DealOut)
async def update_deal(
    deal_id: uuid.UUID, body: DealUpdate, db: Db, user: Writer, if_match: IfMatch = None
) -> Any:
    exp = expected_version(if_match, body.version)
    out = await SalesService(db).update_deal(user, deal_id, body, exp)
    await db.commit()
    return out


@router.delete("/sales/deals/{deal_id}", status_code=204, response_class=Response)
async def delete_deal(deal_id: uuid.UUID, db: Db, user: Writer) -> Response:
    await SalesService(db).delete_deal(user, deal_id)
    await db.commit()
    return Response(status_code=204)


# ---------- EP-73 / EP-74 stage ----------
@router.post("/sales/deals/{deal_id}/stage", response_model=DealOut)
async def change_stage(
    deal_id: uuid.UUID, body: StageChange, db: Db, user: Writer, idem: Idem
) -> Any:
    if (hit := await idem.replay(body)) is not None:
        return DealOut.model_validate(hit)
    out = await SalesService(db).change_stage(user, deal_id, body)
    await db.commit()
    await idem.remember(out)
    return out


@router.get("/sales/deals/{deal_id}/stage-history", response_model=list[StageHistoryOut])
async def stage_history(
    deal_id: uuid.UUID, db: Db, user: Reader,
    page: Annotated[PageParams, Depends(page_params("changed_at"))],
) -> Any:  # fmt: skip
    items, total = await SalesService(db).stage_history(user, deal_id, page)
    return Page(items=items, total=total, limit=page.limit, offset=page.offset)
