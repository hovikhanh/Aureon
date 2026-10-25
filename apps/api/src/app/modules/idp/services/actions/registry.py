"""Action Registry v2 (R-DEC-60, 10 §7.2.4) — the single gate for writes from a document (C1/C3/
C5) or an AI action (L2/L3) into a domain module.

Each `ACT-*` = `ActionDef {name, module, required_permission (any-of), reversible, is_finance,
params_model, validate, run, undo}`. `run` calls the **public service** of the target module with
the caller's `AsyncSession` (DEC-125) — the target service writes its own audit + outbox; `ctx`
carries `source` (`IDP`/`IMPORT`/`MANUAL`/`AI`) + `source_document_id` onto the target rows.

`validate` is a dry-run used for every step before the first `run` (and for EP-DC-05
`planned_actions`); `ctx.planned` lets a later row reference a code an earlier row will create.
"""

from __future__ import annotations

import uuid
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any

from pydantic import BaseModel
from pydantic import ValidationError as PydanticValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import Principal

RowError = dict[str, Any]  # {field, code, message}


@dataclass
class ActionContext:
    """Per-document execution state (one transaction, R-DEC-62)."""

    source: str = "MANUAL"
    source_document_id: uuid.UUID | None = None
    ai_action_id: uuid.UUID | None = None
    # kind → natural key → id of a row created/reused by an earlier ACT of this document
    created: dict[str, dict[str, uuid.UUID]] = field(default_factory=dict)
    # kind → natural keys an earlier step *will* create (validate dry-run)
    planned: dict[str, set[str]] = field(default_factory=dict)
    # second-pass thunks (e.g. #4 manager_id once every employee exists)
    post: list[Callable[[], Awaitable[None]]] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    # validate pass 2 — checks that need every row planned (#4 manager defined later in the file)
    deferred: list[Callable[[], Awaitable[list[RowError]]]] = field(default_factory=list)

    def remember(self, kind: str, key: str, id_: uuid.UUID) -> None:
        self.created.setdefault(kind, {})[key] = id_

    def recall(self, kind: str, key: str | None) -> uuid.UUID | None:
        return None if key is None else self.created.get(kind, {}).get(key)

    def plan(self, kind: str, key: str) -> None:
        self.planned.setdefault(kind, set()).add(key)

    def is_planned(self, kind: str, key: str | None) -> bool:
        return key is not None and key in self.planned.get(kind, set())


@dataclass
class ActionOutcome:
    """`result_refs[{schema, table, id, reused}]` + pre-write `snapshot` (no level-4 values)."""

    result_refs: list[dict[str, Any]]
    snapshot: dict[str, Any] | None = None
    target_version: int | None = None


def ref(schema: str, table: str, id_: uuid.UUID, *, reused: bool = False) -> dict[str, Any]:
    return {"schema": schema, "table": table, "id": str(id_), "reused": reused}


Validate = Callable[[AsyncSession, Principal, Any, ActionContext], Awaitable[list[RowError]]]
Run = Callable[[AsyncSession, Principal, Any, ActionContext], Awaitable[ActionOutcome]]
Undo = Callable[[AsyncSession, Principal, ActionOutcome], Awaitable[None]]


@dataclass(frozen=True)
class ActionDef:
    name: str
    module: str
    required_permission: tuple[str, ...]  # any-of (R-DEC-61)
    reversible: bool
    is_finance: bool
    params_model: type[BaseModel]
    validate: Validate
    run: Run
    undo: Undo
    level4_params: frozenset[str] = frozenset()  # never persisted in `document_actions.params`

    def permitted(self, user: Principal) -> bool:
        return any(user.has(p) for p in self.required_permission)

    def parse(self, params: dict[str, Any]) -> tuple[BaseModel | None, list[RowError]]:
        try:
            return self.params_model.model_validate(params), []
        except PydanticValidationError as exc:
            return None, [
                {"field": ".".join(str(x) for x in e["loc"]), "code": e["type"],
                 "message": e["msg"]}
                for e in exc.errors()
            ]  # fmt: skip


_ACTIONS: dict[str, ActionDef] = {}


def register(act: ActionDef) -> ActionDef:
    _ACTIONS[act.name] = act
    return act


def get_action(name: str) -> ActionDef | None:
    return _ACTIONS.get(name)


def action_names() -> frozenset[str]:
    return frozenset(_ACTIONS)


def is_finance_action(name: str) -> bool:
    act = _ACTIONS.get(name)
    return act.is_finance if act else name.startswith(("ACT-record_", "ACT-create_invoice"))
