"""Public service interface of `sales` — the only entry point for other modules.

Every mutation writes `ENT-AuditLog` in the caller's transaction (10 §1.8); the route commits.
Scope rules live in `services/scope.py` (02 §6.2); pure BR-SAL math in `calculations.py`.
"""

import re
import unicodedata
import uuid
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import MASK, record_audit
from app.core.base_model import Base
from app.core.deps import Principal
from app.core.errors import (
    BusinessRuleError,
    ConflictStateError,
    DuplicateResourceError,
    NotFoundError,
)
from app.core.events.outbox import publish_in_tx
from app.core.pagination import PageParams
from app.core.pii import mask_text
from app.modules.sales.models import Client, Deal, DealStageHistory, SalesTarget
from app.modules.sales.repositories import (
    ClientRepository,
    ContractRepository,
    DealRepository,
    StageHistoryRepository,
    TargetRepository,
)
from app.modules.sales.schemas import (
    ClientCreate,
    ClientOut,
    ClientUpdate,
    Contact,
    DealCreate,
    DealOut,
    DealUpdate,
    SimilarClient,
    StageChange,
    StageHistoryOut,
    TargetCreate,
    TargetOut,
    TargetUpdate,
)
from app.modules.sales.services import calculations as calc
from app.modules.sales.services import scope

SIMILAR_THRESHOLD = 0.80  # 04 §13.1: SUGGESTED ≥ 0.80


def normalize_name(name: str) -> str:
    """04 §13.1 normalisation: lowercase, strip Vietnamese diacritics, collapse spaces."""
    text = unicodedata.normalize("NFKD", name.replace("đ", "d").replace("Đ", "D"))
    text = "".join(c for c in text if not unicodedata.combining(c)).lower()
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s]", " ", text)).strip()


def now_utc() -> datetime:
    return datetime.now(UTC)


def client_out(c: Client, similar: list[SimilarClient] | None = None) -> ClientOut:
    has_contact = c.contact_person or c.contact_email or c.contact_phone
    contacts = (
        [Contact(name=c.contact_person, email=c.contact_email, phone=c.contact_phone)]
        if has_contact else []
    )  # fmt: skip
    return ClientOut(
        id=c.id, version=c.version, created_at=c.created_at, updated_at=c.updated_at,
        name=c.name, tax_code=c.tax_code, industry=c.industry, size=c.company_size,
        contacts=contacts, status=c.status, address=c.address, website=c.website,
        account_owner_id=c.account_owner_id, merged_into_id=c.merged_into_id, notes=c.notes,
        similar_clients=similar or [],
    )  # fmt: skip


def deal_out(d: Deal) -> DealOut:
    return DealOut(
        id=d.id, version=d.version, created_at=d.created_at, updated_at=d.updated_at,
        name=d.name, client_id=d.client_id, deal_value=d.deal_value, currency=d.currency,
        stage=d.stage, probability_pct=float(d.probability_pct), weighted_value=d.weighted_value,
        expected_close_date=d.expected_close_date, closed_at=d.closed_at,
        lost_reason=d.lost_reason, owner_id=d.assigned_to, department_id=d.department_id,
        product_id=d.product_id, tags=list(d.tags), description=d.description,
    )  # fmt: skip


def target_out(t: SalesTarget) -> TargetOut:
    return TargetOut(
        id=t.id, version=t.version, created_at=t.created_at, updated_at=t.updated_at,
        period_type=t.period_type.lower(), period_key=t.period_key, scope=t.scope,
        owner_id=t.owner_id, target_amount=t.target_amount, currency=t.currency,
    )  # fmt: skip


def _audit_client(out: ClientOut) -> dict[str, Any]:
    """Contacts are PII level 3 → masked in audit snapshots (05 §10, 02 §6.3)."""
    data = out.model_dump(mode="json", exclude={"similar_clients"})
    data["contacts"] = [MASK for _ in data["contacts"]]
    return data


def _contact_columns(contacts: list[Contact]) -> dict[str, str | None]:
    c = contacts[0] if contacts else Contact()
    return {"contact_person": c.name, "contact_email": c.email, "contact_phone": c.phone}


def _positive(value: int | None, field: str, rule: str) -> None:
    if value is not None and value <= 0:
        raise BusinessRuleError(f"{field} must be > 0", details={"field": field, "rule": rule})


class SalesService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.clients = ClientRepository(db)
        self.deals = DealRepository(db)
        self.history = StageHistoryRepository(db)
        self.targets = TargetRepository(db)
        self.contracts = ContractRepository(db)

    # ---------- shared ----------
    async def _audit(
        self, action: str, table: str, obj: Base, before: Any = None, after: Any = None
    ) -> None:
        def snap(v: Any) -> Any:
            if v is None or isinstance(v, dict):
                return v
            return _audit_client(v) if isinstance(v, ClientOut) else v.model_dump(mode="json")

        await record_audit(
            self.db, action=action, target_schema="sales", target_table=table,
            target_id=getattr(obj, "id", None), before=snap(before), after=snap(after),
        )  # fmt: skip

    async def _flush_unique(self, what: str) -> None:
        try:
            await self.db.flush()
        except IntegrityError as exc:  # concurrent insert won the partial UQ race
            raise DuplicateResourceError(f"{what} already exists") from exc

    # ---------- EP-71 clients ----------
    async def list_clients(
        self, page: PageParams, *, q: str | None, industry: str | None
    ) -> tuple[list[ClientOut], int]:
        where = []
        if q:
            pattern = "%" + normalize_name(q).replace("%", "").replace("_", "") + "%"
            where.append(Client.normalized_name.like(pattern))
        filters = {"industry": industry} if industry else {}
        items, total = await self.clients.list_page(
            limit=page.limit, offset=page.offset, sort_by=page.sort_by, order=page.order,
            filters=filters, where=where,
        )  # fmt: skip
        return [client_out(c) for c in items], total

    async def get_client(self, id_: uuid.UUID) -> Client:
        obj = await self.clients.get(id_)
        if obj is None:
            raise NotFoundError("client not found")
        return obj

    async def _check_client_unique(
        self, norm: str, tax_code: str | None, exclude: uuid.UUID | None = None
    ) -> list[SimilarClient]:
        same = await self.clients.by_normalized_name(norm)
        if same is not None and same.id != exclude:
            raise DuplicateResourceError(
                "client name already exists",
                details={"field": "name", "similar_clients": [
                    {"id": str(same.id), "name": same.name, "score": 1.0}
                ]},
            )  # fmt: skip
        if tax_code:
            dup = await self.clients.by_tax_code(tax_code)
            if dup is not None and dup.id != exclude:
                raise DuplicateResourceError(
                    "tax_code already exists", details={"field": "tax_code", "id": str(dup.id)}
                )
        rows = await self.clients.similar(norm, threshold=SIMILAR_THRESHOLD, exclude=exclude)
        return [SimilarClient(id=c.id, name=c.name, score=round(s, 2)) for c, s in rows]

    async def create_client(self, user: Principal, body: ClientCreate) -> ClientOut:
        scope.require_record_writer(user)
        norm = normalize_name(body.name)
        similar = await self._check_client_unique(norm, body.tax_code)
        obj = Client(
            name=body.name, normalized_name=norm, tax_code=body.tax_code,
            industry=body.industry, company_size=body.size, status=body.status,
            address=body.address, website=body.website, account_owner_id=body.account_owner_id,
            notes=body.notes, source="MANUAL", created_by=user.user_id,
            **_contact_columns(body.contacts),
        )  # fmt: skip
        self.db.add(obj)
        await self._flush_unique("client tax_code")
        await self.db.refresh(obj)
        out = client_out(obj, similar)
        await self._audit("sales.client_create", "clients", obj, after=out)
        return out

    async def update_client(
        self, user: Principal, id_: uuid.UUID, body: ClientUpdate, expected: int
    ) -> ClientOut:
        scope.require_full_writer(user)
        obj = await self.get_client(id_)
        before = client_out(obj)
        data = body.model_dump(exclude_unset=True, exclude={"version", "contacts"})
        if "name" in data:
            data["normalized_name"] = normalize_name(data["name"])
        similar: list[SimilarClient] = []
        if "name" in data or data.get("tax_code"):
            similar = await self._check_client_unique(
                data.get("normalized_name", obj.normalized_name), data.get("tax_code"), obj.id
            )
        if "size" in data:
            data["company_size"] = data.pop("size")
        if body.contacts is not None:
            data.update(_contact_columns(body.contacts))
        data["updated_by"] = user.user_id
        await self.clients.update(obj, expected_version=expected, **data)
        await self._flush_unique("client tax_code")
        await self.db.refresh(obj)
        out = client_out(obj, similar)
        await self._audit("sales.client_update", "clients", obj, before, out)
        return out

    async def delete_client(self, user: Principal, id_: uuid.UUID) -> None:
        scope.require_full_writer(user)
        obj = await self.get_client(id_)
        if await self.clients.has_live_children(obj.id):
            raise ConflictStateError(
                "client still has deals or contracts", details={"client_id": str(obj.id)}
            )
        before = client_out(obj)
        obj.updated_by = user.user_id
        await self.clients.soft_delete(obj)
        await self._audit("sales.client_delete", "clients", obj, before=before)

    async def _require_client(self, client_id: uuid.UUID) -> None:
        if await self.clients.get(client_id) is None:
            raise BusinessRuleError(
                "client does not exist", details={"field": "client_id", "rule": "FR-SAL-01"}
            )

    # ---------- EP-72 deals ----------
    async def list_deals(
        self, user: Principal, page: PageParams, *, stage: str | None,
        owner_id: uuid.UUID | None, client_id: uuid.UUID | None,
        close_from: date | None, close_to: date | None,
    ) -> tuple[list[DealOut], int]:  # fmt: skip
        filters: dict[str, Any] = {}
        if scope.is_department_scoped(user):
            filters["department_id"] = user.department_id
        if stage:
            filters["stage"] = stage
        if owner_id:
            filters["assigned_to"] = owner_id
        if client_id:
            filters["client_id"] = client_id
        where = []
        if close_from:
            where.append(Deal.expected_close_date >= close_from)
        if close_to:
            where.append(Deal.expected_close_date <= close_to)
        items, total = await self.deals.list_page(
            limit=page.limit, offset=page.offset, sort_by=page.sort_by, order=page.order,
            filters=filters, where=where,
        )  # fmt: skip
        return [deal_out(d) for d in items], total

    async def get_deal(self, user: Principal, id_: uuid.UUID) -> Deal:
        obj = await self.deals.get(id_)
        if obj is None:
            raise NotFoundError("deal not found")
        scope.check_department(user, obj.department_id)
        return obj

    async def create_deal(self, user: Principal, body: DealCreate) -> DealOut:
        scope.require_record_writer(user)
        _positive(body.deal_value, "deal_value", "FR-SAL-01")
        if body.expected_close_date <= now_utc().date():
            raise BusinessRuleError(
                "expected_close_date must be after today",
                details={"field": "expected_close_date", "rule": "FR-SAL-01"},
            )
        dept = body.department_id
        if scope.is_department_scoped(user):
            if dept is not None:
                scope.check_department(user, dept)
            dept = user.department_id
        await self._require_client(body.client_id)
        obj = await self.deals.create(
            name=body.name, client_id=body.client_id, deal_value=body.deal_value,
            currency=body.currency, stage="lead",
            probability_pct=Decimal(str(body.probability_pct)),
            expected_close_date=body.expected_close_date, assigned_to=body.owner_id,
            department_id=dept, product_id=body.product_id, tags=body.tags,
            description=body.description, source="MANUAL", created_by=user.user_id,
        )  # fmt: skip
        await self.history.create(deal_id=obj.id, stage="lead", entered_at=now_utc())
        await self.db.refresh(obj)
        out = deal_out(obj)
        await self._audit("sales.deal_create", "deals", obj, after=out)
        return out

    async def update_deal(
        self, user: Principal, id_: uuid.UUID, body: DealUpdate, expected: int
    ) -> DealOut:
        scope.require_record_writer(user)
        obj = await self.get_deal(user, id_)
        before = deal_out(obj)
        data = body.model_dump(exclude_unset=True, exclude={"version"})
        _positive(data.get("deal_value"), "deal_value", "FR-SAL-01")
        if "department_id" in data:
            scope.check_department(user, data["department_id"])
        if data.get("client_id"):
            await self._require_client(data["client_id"])
        if "probability_pct" in data:
            if obj.stage in calc.CLOSED_STAGES:
                raise ConflictStateError(
                    "probability of a closed deal is fixed (BR-SAL-01)",
                    details={"stage": obj.stage},
                )
            data["probability_pct"] = Decimal(str(data["probability_pct"]))
        if "owner_id" in data:
            data["assigned_to"] = data.pop("owner_id")
        data["updated_by"] = user.user_id
        await self.deals.update(obj, expected_version=expected, **data)
        await self.db.refresh(obj)
        out = deal_out(obj)
        await self._audit("sales.deal_update", "deals", obj, before, out)
        return out

    async def delete_deal(self, user: Principal, id_: uuid.UUID) -> None:
        scope.require_deal_deleter(user)
        obj = await self.get_deal(user, id_)
        before = deal_out(obj)
        obj.updated_by = user.user_id
        await self.deals.soft_delete(obj)
        await self._audit("sales.deal_delete", "deals", obj, before=before)

    # ---------- EP-73 stage ----------
    async def change_stage(self, user: Principal, id_: uuid.UUID, body: StageChange) -> DealOut:
        scope.require_record_writer(user)
        obj = await self.get_deal(user, id_)
        await self.deals.lock(obj)
        reason = calc.transition_error(obj.stage, body.to_stage)
        if reason is not None:
            raise ConflictStateError(
                f"cannot move deal from {obj.stage} to {body.to_stage}",
                details={"from_stage": obj.stage, "to_stage": body.to_stage, "reason": reason},
            )
        if body.to_stage == "closed_lost" and not body.lost_reason:
            raise BusinessRuleError(
                "closed_lost requires lost_reason",
                details={"field": "lost_reason", "rule": "FR-SAL-02"},
            )
        before = deal_out(obj)
        at = now_utc()
        values: dict[str, Any] = {"stage": body.to_stage, "updated_by": user.user_id}
        prob = calc.closing_probability(body.to_stage)
        if prob is not None:
            values.update(probability_pct=prob, closed_at=at)
        if body.to_stage == "closed_lost":
            values["lost_reason"] = body.lost_reason
        await self.history.close_current(obj.id, at)
        await self.history.create(deal_id=obj.id, stage=body.to_stage, entered_at=at)
        await self.deals.update(obj, **values)
        await self.db.refresh(obj)
        out = deal_out(obj)
        await self._audit("sales.deal_stage_change", "deals", obj, before, out)
        if prob is not None:
            await self._publish_closed(obj)
        return out

    async def _publish_closed(self, d: Deal) -> None:
        """05 §8 payload — ids + amounts only; free-text `lost_reason` is PII-masked."""
        payload: dict[str, Any] = {
            "deal_id": str(d.id), "client_id": str(d.client_id), "deal_value": d.deal_value,
            "currency": d.currency,
            "closed_at": d.closed_at.isoformat() if d.closed_at else None,
        }  # fmt: skip
        if d.stage == "closed_won":
            payload["product_id"] = str(d.product_id) if d.product_id else None
        else:
            payload["lost_reason"] = mask_text(d.lost_reason or "")
        await publish_in_tx(
            self.db, event_type=f"sales.deal_{d.stage}", producer="sales",
            aggregate_schema="sales", aggregate_table="deals", aggregate_id=d.id,
            payload=payload,
        )  # fmt: skip

    # ---------- EP-74 stage history ----------
    async def stage_history(
        self, user: Principal, id_: uuid.UUID, page: PageParams
    ) -> tuple[list[StageHistoryOut], int]:
        deal = await self.get_deal(user, id_)
        rows: list[DealStageHistory] = list(await self.history.for_deal(deal.id))
        out = [
            StageHistoryOut(
                from_stage=rows[i - 1].stage if i else None,
                to_stage=r.stage,
                changed_by=None,
                changed_at=r.entered_at,
            )
            for i, r in enumerate(rows)
        ]
        if page.order == "desc":
            out.reverse()
        return out[page.offset : page.offset + page.limit], len(out)

    # ---------- EP-77 targets ----------
    async def list_targets(
        self, page: PageParams, *, period_key: str | None, scope_: str | None
    ) -> tuple[list[TargetOut], int]:
        filters: dict[str, Any] = {}
        if period_key:
            filters["period_key"] = period_key
        if scope_:
            filters["scope"] = scope_
        items, total = await self.targets.list_page(
            limit=page.limit, offset=page.offset, sort_by=page.sort_by, order=page.order,
            filters=filters,
        )  # fmt: skip
        return [target_out(t) for t in items], total

    async def get_target(self, id_: uuid.UUID) -> SalesTarget:
        obj = await self.targets.get(id_)
        if obj is None:
            raise NotFoundError("sales target not found")
        return obj

    async def create_target(self, user: Principal, body: TargetCreate) -> TargetOut:
        scope.require_target_writer(user)
        _positive(body.target_amount, "target_amount", "FR-SAL-06")
        if not calc.target_period_key_ok(body.period_type, body.period_key):
            raise BusinessRuleError(
                "period_key does not match period_type",
                details={"field": "period_key", "rule": "FR-SAL-06"},
            )
        if (body.scope == "individual") != (body.owner_id is not None):
            raise BusinessRuleError(
                "owner_id is required for individual targets and forbidden for team targets",
                details={"field": "owner_id", "rule": "FR-SAL-06"},
            )
        if await self.targets.find(body.period_key, body.scope, body.owner_id) is not None:
            raise DuplicateResourceError(
                "target already exists for this period / scope / owner",
                details={"period_key": body.period_key, "scope": body.scope},
            )
        obj = SalesTarget(
            period_type=body.period_type.upper(), period_key=body.period_key, scope=body.scope,
            owner_id=body.owner_id, target_amount=body.target_amount, currency=body.currency,
            source="MANUAL", created_by=user.user_id,
        )  # fmt: skip
        self.db.add(obj)
        await self._flush_unique("sales target")
        await self.db.refresh(obj)
        out = target_out(obj)
        await self._audit("sales.target_create", "sales_targets", obj, after=out)
        return out

    async def update_target(
        self, user: Principal, id_: uuid.UUID, body: TargetUpdate, expected: int
    ) -> TargetOut:
        scope.require_target_writer(user)
        obj = await self.get_target(id_)
        before = target_out(obj)
        data = body.model_dump(exclude_unset=True, exclude={"version"})
        _positive(data.get("target_amount"), "target_amount", "FR-SAL-06")
        data["updated_by"] = user.user_id
        await self.targets.update(obj, expected_version=expected, **data)
        await self.db.refresh(obj)
        out = target_out(obj)
        await self._audit("sales.target_update", "sales_targets", obj, before, out)
        return out

    async def delete_target(self, user: Principal, id_: uuid.UUID) -> None:
        scope.require_target_writer(user)
        obj = await self.get_target(id_)
        before = target_out(obj)
        obj.updated_by = user.user_id
        await self.targets.soft_delete(obj)
        await self._audit("sales.target_delete", "sales_targets", obj, before=before)
