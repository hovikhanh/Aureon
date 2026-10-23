"""Tool metadata model + enums (10 §7.4, DEC-149).

A `ToolDef` is the registry row for one `TOOL-*`. The five §7.4 metadata attributes
(`schema`, `data_scope`, `classification`, `reversible`, `cost_estimate`) plus the §7.1–7.3
columns (`kind`, `risk_level`, `autonomy_default`, `autonomy_max`, `required_permissions`) are
declared here; the executor binding (service call with the asker's `Principal`) is added in T-302.
This module has no DB / service imports — the registry is a pure, importable catalog.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

ToolKind = Literal["READ", "COMPUTE", "WRITE", "APPROVAL", "EXECUTION"]
RiskLevel = Literal["low", "medium", "high"]
Autonomy = Literal["L0", "L1", "L2", "L3"]
CostEstimate = Literal["low", "medium", "high"]
ToolClassification = Literal["INTERNAL", "CONFIDENTIAL", "SECRET"]


@dataclass(frozen=True)
class ToolDef:
    """One registry entry. `name` is the `TOOL-*` id; `domain` is its owning module."""

    name: str
    description: str
    domain: str
    endpoint: str
    kind: ToolKind
    risk_level: RiskLevel
    autonomy_default: Autonomy
    autonomy_max: Autonomy
    required_permissions: tuple[str, ...]
    data_scope: str
    classification: ToolClassification
    reversible: bool | None  # None == "n/a" (QUERY/COMPUTE); True/False for WRITE/APPROVAL
    cost_estimate: CostEstimate
    # `declare_to_model=False` → never advertised to the LLM (APPROVAL layer, §7.3).
    declare_to_model: bool = True
    # R-DEC-16: product (D22) / risk (D25) frozen at P1 — kept runnable server-side, but never
    # advertised to the model at P0 (`advertisable_for`).
    p1_frozen: bool = False
    parameters: dict[str, object] = field(default_factory=dict)

    @property
    def is_write(self) -> bool:
        return self.kind in ("WRITE", "EXECUTION")

    @property
    def reversible_label(self) -> str:
        return "n/a" if self.reversible is None else ("true" if self.reversible else "false")
