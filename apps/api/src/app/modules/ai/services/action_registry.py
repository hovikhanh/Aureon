"""Re-export of the Action Registry v2 (R-DEC-60): the registry lives in
`modules/idp/services/actions/`; AI L2/L3 actions share the same `ACT-*` definitions
(`get_action`, `ActionDef`). `idp` no longer imports `ai` (gateway split), so `ai → idp` is
acyclic."""

from app.modules.idp.services.actions import (
    ActionContext,
    ActionDef,
    ActionOutcome,
    get_action,
    is_finance_action,
)

__all__ = ["ActionContext", "ActionDef", "ActionOutcome", "get_action", "is_finance_action"]
