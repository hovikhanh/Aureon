"""Shared helpers for execution services: audit, reference checks, today, out-mapping."""

import uuid
from datetime import UTC, date, datetime
from typing import Any

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import record_audit
from app.core.base_model import BusinessModel
from app.core.clock import business_today
from app.core.errors import BusinessRuleError, DuplicateResourceError, NotFoundError
from app.modules.execution.models import (
    Decision,
    Initiative,
    KeyResult,
    Kpi,
    Meeting,
    Milestone,
    Objective,
    Project,
    StrategicObjective,
    Task,
)

# body field → model it must point to (live row), checked before INSERT/UPDATE → 422 not 500.
REFS: dict[str, type[BusinessModel]] = {
    "project_id": Project,
    "meeting_id": Meeting,
    "decision_id": Decision,
    "key_result_id": KeyResult,
    "initiative_id": Initiative,
    "milestone_id": Milestone,
    "kpi_id": Kpi,
    "objective_id": Objective,
    "strategic_objective_id": StrategicObjective,
}


def now_utc() -> datetime:
    return datetime.now(UTC)


def today() -> date:
    return business_today()


def num(value: Any) -> float | None:
    return None if value is None else float(value)


class ExecBase:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def audit(
        self, action: str, table: str, target: uuid.UUID, before: Any = None, after: Any = None
    ) -> None:
        def snap(v: Any) -> Any:
            return v.model_dump(mode="json") if isinstance(v, BaseModel) else v

        await record_audit(
            self.db, action=f"execution.{action}", target_schema="execution",
            target_table=table, target_id=target, before=snap(before), after=snap(after),
        )  # fmt: skip

    async def require_refs(
        self, data: dict[str, Any], rule: str, **extra: type[BusinessModel]
    ) -> None:
        refs = {**REFS, **extra}
        for field, value in data.items():
            model = refs.get(field)
            if model is None or value is None:
                continue
            stmt = select(model.id).where(model.id == value, model.deleted_at.is_(None))
            if (await self.db.execute(stmt)).first() is None:
                raise BusinessRuleError(
                    f"{field} does not exist", details={"field": field, "rule": rule}
                )

    @staticmethod
    def require_root_link(data: dict[str, Any], parent_field: str, rule: str) -> None:
        """05 §2.6 CHECK: only a root (no parent) links to a StrategicObjective → 422 not 500."""
        if data.get(parent_field) is not None and data.get("strategic_objective_id") is not None:
            raise BusinessRuleError(
                "only a root record links to a strategic objective",
                details={"field": "strategic_objective_id", "rule": rule},
            )

    async def require_unique(
        self, model: type[BusinessModel], column: str, value: Any, exclude: Any
    ) -> None:
        stmt = select(model.id).where(getattr(model, column) == value)
        if exclude is not None:
            stmt = stmt.where(model.id != exclude)
        if (await self.db.execute(stmt)).first() is not None:
            raise DuplicateResourceError(f"{column} already exists", details={"field": column})


def not_found(what: str) -> NotFoundError:
    return NotFoundError(f"{what} not found")


__all__ = ["ExecBase", "Task", "not_found", "now_utc", "num", "today"]
