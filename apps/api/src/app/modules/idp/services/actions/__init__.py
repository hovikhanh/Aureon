"""Action Registry v2 (R-DEC-60). Importing the package registers all 12 `ACT-*`."""

from app.modules.idp.services.actions import finance, goals, org, work
from app.modules.idp.services.actions.registry import (
    ActionContext,
    ActionDef,
    ActionOutcome,
    action_names,
    get_action,
    is_finance_action,
)

__all__ = [
    "ActionContext",
    "ActionDef",
    "ActionOutcome",
    "action_names",
    "finance",
    "get_action",
    "goals",
    "is_finance_action",
    "org",
    "work",
]  # finance/goals/org/work: importing the ACT modules registers their `ActionDef`s
