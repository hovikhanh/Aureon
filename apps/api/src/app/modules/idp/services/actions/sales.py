"""ACT-upsert_deal → `sales` `SalesService` (F-H8; `TOOL-upsert_deal`, AI L2 only).

The tool schema carries `name, stage, amount, currency`. A new deal also needs a client, an owner
and a close date (`DealCreate`, FR-SAL-01), which the tool does not have, so only an existing deal
matched by its exact name can change: value and/or stage. An unknown name is a row error on the
card, never an invented client. Undo restores the value through the version the action left; a
stage move stays in the stage history, so a stage change is not undone silently.
"""

from __future__ import annotations

import uuid
from typing import Any

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import Principal
from app.core.pagination import PageParams
from app.modules.idp.services.actions.registry import (
    ActionContext,
    ActionDef,
    ActionOutcome,
    RowError,
    ref,
    register,
)
from app.modules.sales.schemas import DealStage, DealUpdate, StageChange
from app.modules.sales.services.sales_service import SalesService

_SCAN = PageParams(limit=100, offset=0, sort_by="created_at", order="desc")


class DealParams(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=300)
    stage: DealStage | None = None
    amount: int | None = Field(default=None, gt=0)
    currency: str | None = None


async def _find(db: AsyncSession, user: Principal, name: str) -> Any:
    deals, _ = await SalesService(db).list_deals(
        user, _SCAN, stage=None, owner_id=None, client_id=None, close_from=None, close_to=None
    )
    return next((d for d in deals if d.name.strip().casefold() == name.strip().casefold()), None)


async def _validate(
    db: AsyncSession, user: Principal, p: Any, ctx: ActionContext
) -> list[RowError]:
    if await _find(db, user, p.name) is None:
        return [{"field": "name", "code": "not_found",
                 "message": "only an existing deal can be changed from chat"}]  # fmt: skip
    return []


async def _run(db: AsyncSession, user: Principal, p: Any, ctx: ActionContext) -> ActionOutcome:
    svc = SalesService(db)
    deal = await _find(db, user, p.name)
    snapshot: dict[str, Any] = {"deal_value": deal.deal_value}
    out = deal
    if p.amount is not None and p.amount != deal.deal_value:
        out = await svc.update_deal(user, deal.id, DealUpdate(deal_value=p.amount), deal.version)
    if p.stage and p.stage != deal.stage:
        out = await svc.change_stage(user, deal.id, StageChange(to_stage=p.stage))
    return ActionOutcome([ref("sales", "deals", deal.id)], snapshot=snapshot,
                         target_version=out.version)  # fmt: skip


async def _undo(db: AsyncSession, user: Principal, outcome: ActionOutcome) -> None:
    await SalesService(db).update_deal(
        user, uuid.UUID(outcome.result_refs[0]["id"]),
        DealUpdate(deal_value=(outcome.snapshot or {})["deal_value"]),
        int(outcome.target_version or 0),
    )  # fmt: skip


register(ActionDef(
    name="ACT-upsert_deal", module="sales", required_permission=("sales:write",),
    reversible=True, is_finance=False, params_model=DealParams, validate=_validate, run=_run,
    undo=_undo,
))  # fmt: skip
