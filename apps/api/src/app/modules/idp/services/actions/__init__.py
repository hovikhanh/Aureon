"""Action Registry v2 (R-DEC-60). Importing the package registers every `ACT-*`
(+ `recommendation` M3.2, R-DEC-127)."""

from app.modules.idp.services.actions import (
    finance,
    goals,
    meeting,
    org,
    recommendation,
    work,
)
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
    "meeting",
    "org",
    "recommendation",
    "work",
]  # importing the ACT modules registers their `ActionDef`s
