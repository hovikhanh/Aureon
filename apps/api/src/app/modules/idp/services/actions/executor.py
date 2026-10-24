"""Document → ACT plan → validate-all → run-all (10 §7.2.4, R-DEC-61/62/63).

Plan: every field of the published `ExtractionSchema` carries `target {action, param}` (05 §2.7);
fields with `group="row"` make one step per `row_index`, the rest one header step. Steps run in
`action_names` order (#4 department → team → position → employee, #2 objective → key_result →
kpi → kpi_target). Fields without `target` map `param = name` onto a single-action schema
(INVOICE, v2.1 shape).

Atomicity: all `run`s execute in one SAVEPOINT of the caller's transaction — a failing step
rolls back every earlier step (target rows + their audit/outbox), raised as `ACTION_REJECTED`.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import Principal
from app.core.errors import ActionRejectedError, AppError
from app.modules.idp.models import DocumentAction
from app.modules.idp.services.actions.registry import (
    ActionContext,
    ActionDef,
    ActionOutcome,
    get_action,
)


@dataclass
class Step:
    act: ActionDef
    row_index: int | None
    params: dict[str, Any]


def build_plan(
    action_names: list[str],
    schema_fields: list[dict[str, Any]],
    values: list[tuple[str, int | None, Any]],
) -> list[Step]:
    """`values` = (field_name, row_index, effective value) of the reviewed fields."""
    defs = {f["name"]: f for f in schema_fields}
    single = action_names[0] if len(action_names) == 1 else None
    grouped: dict[tuple[str, int | None], dict[str, Any]] = defaultdict(dict)
    for name, row, value in values:
        target = (defs.get(name) or {}).get("target")
        action, param = (target["action"], target["param"]) if target else (single, name)
        if action is None or value is None:
            continue
        grouped[(action, row)][param] = value
    steps: list[Step] = []
    for name in action_names:
        act = get_action(name)
        if act is None:
            raise ActionRejectedError(
                f"unknown action {name}", details={"action_name": name, "reason": "unregistered"}
            )
        rows = sorted((r for (a, r) in grouped if a == name), key=lambda r: (r is not None, r))
        steps += [Step(act, r, grouped[(name, r)]) for r in rows]
    return steps


def missing_permissions(user: Principal, steps: list[Step]) -> list[str]:
    """First `required_permission` of every ACT the caller cannot run (any-of, R-DEC-61)."""
    return sorted({s.act.required_permission[0] for s in steps if not s.act.permitted(user)})


def _reject(step: Step, errors: list[dict[str, Any]], **extra: Any) -> ActionRejectedError:
    return ActionRejectedError(
        f"{step.act.name} rejected",
        details={"action_name": step.act.name, "row_index": step.row_index, "errors": errors,
                 **extra},
    )  # fmt: skip


async def validate_all(
    db: AsyncSession, user: Principal, steps: list[Step], ctx: ActionContext
) -> list[Any]:
    """Dry-run every step before the first write (no row written on failure)."""
    parsed: list[Any] = []
    owners: list[Step] = []  # step that registered each `ctx.deferred` check
    for step in steps:
        params, errors = step.act.parse(step.params)
        if params is not None:
            errors = await step.act.validate(db, user, params, ctx)
        if errors:
            raise _reject(step, errors)
        parsed.append(params)
        owners += [step] * (len(ctx.deferred) - len(owners))
    for step, check in zip(owners, ctx.deferred, strict=True):  # pass 2: every row planned
        if errors := await check():
            raise _reject(step, errors)
    return parsed


def _json(value: Any) -> Any:
    from pydantic_core import to_jsonable_python

    return to_jsonable_python(value)


async def run_all(
    db: AsyncSession, user: Principal, steps: list[Step], ctx: ActionContext
) -> list[tuple[Step, ActionOutcome]]:
    """Validate all, then run all inside one SAVEPOINT; persist `idp.document_actions` rows
    (when `ctx.source_document_id`). Any failure → nothing written, `ACTION_REJECTED`."""
    parsed = await validate_all(db, user, steps, ActionContext(
        source=ctx.source, source_document_id=ctx.source_document_id,
        ai_action_id=ctx.ai_action_id,
    ))  # fmt: skip
    done: list[tuple[Step, ActionOutcome]] = []
    current: Step | None = None
    nested = await db.begin_nested()
    try:
        for step, params in zip(steps, parsed, strict=True):
            current = step
            done.append((step, await step.act.run(db, user, params, ctx)))
        current = None
        for thunk in ctx.post:  # second pass (#4 manager_id)
            await thunk()
        if ctx.source_document_id is not None:
            for seq, (step, outcome) in enumerate(done, start=1):
                db.add(DocumentAction(
                    source_document_id=ctx.source_document_id, seq=seq,
                    action_name=step.act.name, row_index=step.row_index,
                    params=_json({k: v for k, v in step.params.items()
                                  if k not in step.act.level4_params}),
                    result_refs=outcome.result_refs, snapshot=outcome.snapshot,
                    target_version=outcome.target_version, status="applied",
                    executed_by=user.user_id,
                ))  # fmt: skip
            await db.flush()
    except ActionRejectedError:
        await nested.rollback()
        db.expire_all()  # identity map may hold rolled-back versions
        raise
    except AppError as exc:
        await nested.rollback()
        db.expire_all()  # identity map may hold rolled-back versions
        failed = current or (done[-1][0] if done else steps[0])
        raise _reject(failed, [{"code": exc.code, "message": exc.message}],
                      cause_code=exc.code) from exc  # fmt: skip
    await nested.commit()
    return done


def outcome_of(row: DocumentAction) -> ActionOutcome:
    return ActionOutcome(list(row.result_refs or []), row.snapshot, row.target_version)
