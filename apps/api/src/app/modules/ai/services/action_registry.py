"""Action Registry (04 §10) — the single gate for AI-confirmed writes into domain modules.

Each `ACT-*` wraps one domain use case: it validates input, calls the **public service** of the
target module with the acting `Principal` (never importing another module's models — DEC-125), and
returns `result_refs` plus an `undo` thunk. A write runs in the caller's transaction so the
`ENT-AIAction` + domain row + audit commit together (04 §10.4). Undo is soft-delete / snapshot
restore and is blocked if the target row changed after commit (conflict → `CONFLICT_STATE`).

v2.0 wires the internal, fully-reversible actions needed by the AI assistant; the full catalogue
(04 §10.2) is completed alongside IDP S4. `TOOL-*` write tools map onto the same `ACT-*`.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import Principal

# an executor: (db, user, input) -> (result_refs, undo_thunk)
UndoThunk = Callable[[], Awaitable[None]]


@dataclass(frozen=True)
class ActionOutcome:
    result_refs: list[dict[str, Any]]
    undo: UndoThunk


@dataclass(frozen=True)
class ActionDef:
    name: str
    module: str
    reversible: bool
    is_finance: bool
    run: Callable[[AsyncSession, Principal, dict[str, Any]], Awaitable[ActionOutcome]]


async def _run_create_task(
    db: AsyncSession, user: Principal, data: dict[str, Any]
) -> ActionOutcome:
    """ACT-create_task → execution.tasks (reversible: soft delete)."""
    from app.modules.execution.schemas.tasks import TaskCreate
    from app.modules.execution.services.task_service import TaskService

    svc = TaskService(db)
    body = TaskCreate.model_validate(data)
    created = await svc.create(user, body)
    task_id = created.id

    async def undo() -> None:
        # reverse via the execution public service (DEC-125) — soft delete + audit
        from app.core.errors import NotFoundError

        try:
            await TaskService(db).delete(user, task_id)
        except NotFoundError:
            return  # already gone

    return ActionOutcome(
        result_refs=[{"type": "record", "id": str(task_id), "table": "execution.tasks"}],
        undo=undo,
    )


_ACTIONS: dict[str, ActionDef] = {
    "ACT-create_task": ActionDef(
        name="ACT-create_task",
        module="execution",
        reversible=True,
        is_finance=False,
        run=_run_create_task,
    ),
}


def get_action(name: str) -> ActionDef | None:
    return _ACTIONS.get(name)


def is_finance_action(name: str) -> bool:
    act = _ACTIONS.get(name)
    return act.is_finance if act else name.startswith(("ACT-record_", "ACT-create_invoice"))
