"""EP-AI-14 Tool Registry catalog (10 §7.2.5, T-644): `ToolDef` → `ToolOut` + filters.

`available` = the caller may use the tool (holds every permission) **and** it is advertised to
the model (not APPROVAL / `p1_frozen`) — the v2.1 meaning, kept. Filters: `kind`, `domain`,
`available_only`. No pagination (≤ 60 rows).
"""

from __future__ import annotations

from app.core.deps import Principal
from app.modules.ai.schemas import ToolOut
from app.modules.ai.tools import ToolDef, advertisable_for, all_tools


def tool_out(t: ToolDef, *, available: bool) -> ToolOut:
    return ToolOut(
        name=t.name, kind=t.kind, autonomy_default=t.autonomy_default, available=available,
        data_scope=t.data_scope, classification=t.data_classification,
        reversible=t.reversible_label, cost_estimate=t.cost_estimate,
        tool_id=t.name, brd_name=t.brd_name, description=t.description, domain=t.domain,
        input_schema=t.input_schema or {}, output_schema=t.output_schema or {},
        permission=list(t.required_permissions), risk_level=t.risk_level,
        data_classification=t.data_classification, autonomy_max=t.autonomy_max,
        approval_required=t.approval_required, audit_required=t.audit_required,
        owner=t.owner, compute=t.compute, p1_frozen=t.p1_frozen, action_name=t.action_name,
        endpoint_ref=t.endpoint_ref,
    )  # fmt: skip


def list_tools(
    user: Principal, *, kind: str | None = None, domain: str | None = None,
    available_only: bool = False,
) -> list[ToolOut]:  # fmt: skip
    advertised = {t.name for t in advertisable_for(user.permissions)}
    out: list[ToolOut] = []
    for t in all_tools():
        if (kind and t.kind != kind) or (domain and t.domain != domain):
            continue
        available = t.name in advertised
        if available_only and not available:
            continue
        out.append(tool_out(t, available=available))
    return out
