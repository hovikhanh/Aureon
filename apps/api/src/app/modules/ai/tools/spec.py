"""Tool metadata model — 13 metadata of 10 §2.1 (T-644, R-DEC-70, 10 §7.2.5 table).

A `ToolDef` is the registry row for one `TOOL-*`. Every metadata attribute must be declared:
a missing one (left `None`), an unknown enum value or a broken invariant raises
`ToolRegistryError` while the registry module is imported — the tool "is not registered"
(10 §2.1). Invariants (10 §7.2.5 "Kiểm tra lúc import"):

* `kind ∈ READ/WRITE/APPROVAL/EXECUTION` (v2.1 `COMPUTE` → `READ` + `compute=True`);
* READ: `reversible=None`, autonomy `L0/L0`, `audit_required=False`;
* WRITE/APPROVAL/EXECUTION: `audit_required=True`; WRITE/EXECUTION carry an `action_name`;
* APPROVAL ⇒ `declare_to_model=False` (AI never calls it);
* WRITE with `reversible=False` ⇒ `autonomy_max ≤ L2`; EXECUTION ⇒ `autonomy_max ≤ L2` except
  `TOOL-send_notification` (in-app channel, capped by the M1 ceiling anyway);
* `input_schema`/`output_schema`: `type=object`, `properties` dict, `additionalProperties=false`
  (checked by hand — no `jsonschema` dependency).

This module has no DB / service imports — the registry is a pure, importable catalog.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

ToolKind = Literal["READ", "WRITE", "APPROVAL", "EXECUTION"]
RiskLevel = Literal["low", "medium", "high"]
Autonomy = Literal["L0", "L1", "L2", "L3"]
CostEstimate = Literal["low", "medium", "high"]
ToolClassification = Literal["PUBLIC", "INTERNAL", "CONFIDENTIAL", "SECRET"]
ApprovalRequired = Literal["never", "threshold", "always"]

KINDS = frozenset({"READ", "WRITE", "APPROVAL", "EXECUTION"})
LEVEL_ORDER = {"L0": 0, "L1": 1, "L2": 2, "L3": 3}
GRAINS = frozenset({"aggregate", "record", "document", "structure", "self"})
OWNERS = frozenset({"ROLE-CEO", "ROLE-ADM", "ROLE-DIR:F", "ROLE-DIR:C", "ROLE-DIR:O",
                    "ROLE-DIR:U", "ROLE-DIR:S"})  # fmt: skip
EXECUTION_L3_EXCEPTION = frozenset({"TOOL-send_notification"})
# Attributes that must be declared (not `None`/empty) on every tool — 10 §2.1 rows 1..14.
REQUIRED = ("name", "description", "input_schema", "output_schema", "required_permissions",
            "risk_level", "data_scope", "data_classification", "autonomy_default",
            "approval_required", "audit_required", "cost_estimate", "owner", "kind",
            "domain", "endpoint_ref", "autonomy_max")  # fmt: skip


class ToolRegistryError(RuntimeError):
    """A `ToolDef` misses a metadata attribute or breaks an invariant (raised at import)."""


@dataclass(frozen=True)
class ToolDef:
    """One registry entry. `name` is the `TOOL-*` id (also sent to the model, R-DEC-70)."""

    name: str
    description: str
    domain: str
    endpoint_ref: str
    kind: ToolKind
    risk_level: RiskLevel
    autonomy_default: Autonomy
    autonomy_max: Autonomy
    required_permissions: tuple[str, ...]
    data_scope: str
    data_classification: ToolClassification
    reversible: bool | None  # None == READ ("n/a")
    cost_estimate: CostEstimate
    input_schema: dict[str, Any] | None = None
    output_schema: dict[str, Any] | None = None
    approval_required: ApprovalRequired | None = None
    audit_required: bool | None = None
    owner: str | None = None
    brd_name: str | None = None
    action_name: str | None = None
    compute: bool = False
    # `declare_to_model=False` → never advertised to the LLM (APPROVAL layer, §7.3).
    declare_to_model: bool = True
    # R-DEC-16: product (D22) / risk (D25) frozen at P1 — runnable server-side, never advertised.
    p1_frozen: bool = False
    extra: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        validate_tool(self)

    # ---- v2.1 read aliases (callers / fixtures keep working) ----
    @property
    def classification(self) -> str:
        return self.data_classification

    @property
    def parameters(self) -> dict[str, Any]:
        return dict(self.input_schema or {})

    @property
    def endpoint(self) -> str:
        return self.endpoint_ref

    @property
    def is_write(self) -> bool:
        return self.kind in ("WRITE", "EXECUTION")

    @property
    def reversible_label(self) -> str:
        return "n/a" if self.reversible is None else ("true" if self.reversible else "false")


def _fail(t: ToolDef, why: str) -> None:
    raise ToolRegistryError(f"{getattr(t, 'name', '?')}: {why}")


def check_object_schema(schema: object) -> str | None:
    """Minimal structural check of a JSON Schema object node; returns the problem or None."""
    if not isinstance(schema, dict):
        return "schema is not an object"
    if schema.get("type") != "object":
        return "type must be 'object'"
    props = schema.get("properties")
    if not isinstance(props, dict):
        return "properties must be a dict"
    if schema.get("additionalProperties") is not False:
        return "additionalProperties must be false"
    req = schema.get("required", [])
    if not isinstance(req, list) or not set(req) <= set(props):
        return "required must list declared properties"
    for key, sub in props.items():
        if not isinstance(sub, dict) or not ({"type", "$ref", "anyOf", "enum"} & set(sub)):
            return f"property {key!r} has no type"
    return None


def validate_tool(t: ToolDef) -> None:
    for attr in REQUIRED:
        value = getattr(t, attr)
        if value is None or value == "" or value == ():
            _fail(t, f"missing metadata {attr!r}")
    if not t.name.startswith("TOOL-"):
        _fail(t, "name must start with TOOL-")
    if t.kind not in KINDS:
        _fail(t, f"kind {t.kind!r} not in {sorted(KINDS)}")
    if {t.risk_level, t.cost_estimate} - {"low", "medium", "high"}:
        _fail(t, "risk_level/cost_estimate must be low|medium|high")
    if t.data_classification not in ("PUBLIC", "INTERNAL", "CONFIDENTIAL", "SECRET"):
        _fail(t, "bad data_classification")
    if t.approval_required not in ("never", "threshold", "always"):
        _fail(t, "bad approval_required")
    if t.owner not in OWNERS:
        _fail(t, f"bad owner {t.owner!r}")
    if t.autonomy_default not in LEVEL_ORDER or t.autonomy_max not in LEVEL_ORDER:
        _fail(t, "autonomy must be L0..L3 (L4 locked)")
    if LEVEL_ORDER[t.autonomy_default] > LEVEL_ORDER[t.autonomy_max]:
        _fail(t, "autonomy_default above autonomy_max")
    domain, _, grain = t.data_scope.partition(":")
    if not domain or grain not in GRAINS:
        _fail(t, f"data_scope {t.data_scope!r} must be <domain>:<grain>")
    for label, schema in (("input_schema", t.input_schema), ("output_schema", t.output_schema)):
        problem = check_object_schema(schema)
        if problem:
            _fail(t, f"{label}: {problem}")
    _check_kind_rules(t)


def _check_kind_rules(t: ToolDef) -> None:
    if t.kind == "READ":
        if t.reversible is not None or t.audit_required:
            _fail(t, "READ: reversible must be None and audit_required False")
        if t.autonomy_max != "L0":
            _fail(t, "READ: autonomy must be L0")
        return
    if not t.audit_required:
        _fail(t, f"{t.kind}: audit_required must be True")
    if not isinstance(t.reversible, bool):
        _fail(t, f"{t.kind}: reversible must be a bool")
    if t.compute:
        _fail(t, "compute flag is READ-only")
    if t.kind == "APPROVAL" and t.declare_to_model:
        _fail(t, "APPROVAL tools are never declared to the model")
    if t.kind in ("WRITE", "EXECUTION") and not (t.action_name or "").startswith("ACT-"):
        _fail(t, f"{t.kind}: action_name ACT-* required")
    if t.kind == "WRITE" and t.reversible is False and LEVEL_ORDER[t.autonomy_max] > 2:
        _fail(t, "irreversible WRITE: autonomy_max must be <= L2")
    if (t.kind == "EXECUTION" and t.name not in EXECUTION_L3_EXCEPTION
            and LEVEL_ORDER[t.autonomy_max] > 2):  # fmt: skip
        _fail(t, "EXECUTION: autonomy_max must be <= L2")
