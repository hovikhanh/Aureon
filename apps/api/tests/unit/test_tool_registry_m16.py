"""TC-M16-01 / TC-M16-02 (T-644, R-DEC-70) — Tool Registry 13 metadata + 4 kinds + BRD map.

* every `ToolDef` declares the 13 metadata of 10 §2.1; a missing one → `ToolRegistryError`
  at construction (the module never finishes importing);
* `kind ∈ READ/WRITE/APPROVAL/EXECUTION` (v2.1 COMPUTE → READ + `compute`);
* kind invariants (APPROVAL never declared to the model, `audit_required`, reversible/max);
* `input_schema`/`output_schema` minimal structure (hand-rolled check, no `jsonschema`);
* `brd_name` covers every BRD §11.2 tool of 10 §2.2 (or it is listed as "not a tool / deferred").
"""

import re
from dataclasses import asdict, replace
from pathlib import Path
from typing import Any

import pytest

from app.core.config import REPO_ROOT
from app.modules.ai.tools import (
    TOOLS,
    ToolDef,
    ToolRegistryError,
    advertisable_for,
    get_tool,
    tool_for_action,
    tool_kind,
)
from app.modules.ai.tools.spec import REQUIRED, check_object_schema

SPEC = Path(REPO_ROOT) / "docs" / "3.EXECUTION" / "10-API-SPECIFICATION.md"
KINDS = {"READ", "WRITE", "APPROVAL", "EXECUTION"}


def _base() -> dict[str, Any]:
    t = get_tool("TOOL-create_task")
    assert t is not None
    return {k: v for k, v in asdict(t).items() if k != "extra"}


def test_every_tool_declares_13_metadata() -> None:
    for t in TOOLS:
        for attr in REQUIRED:
            assert getattr(t, attr) not in (None, "", ()), f"{t.name} missing {attr}"
        assert t.kind in KINDS
        assert check_object_schema(t.input_schema) is None, t.name
        assert check_object_schema(t.output_schema) is None, t.name


@pytest.mark.parametrize("attr", ["input_schema", "output_schema", "approval_required",
                                  "audit_required", "owner", "description"])  # fmt: skip
def test_missing_metadata_is_not_registered(attr: str) -> None:
    kwargs = _base() | {attr: None}
    with pytest.raises(ToolRegistryError, match=attr):
        ToolDef(**kwargs)


@pytest.mark.parametrize(
    ("patch", "why"),
    [
        ({"kind": "COMPUTE"}, "kind"),
        ({"kind": "APPROVAL", "declare_to_model": True}, "never declared"),
        ({"audit_required": False}, "audit_required"),
        ({"reversible": False, "autonomy_max": "L3"}, "irreversible"),
        ({"kind": "EXECUTION", "autonomy_max": "L3", "name": "TOOL-send_email"}, "EXECUTION"),
        ({"action_name": None}, "action_name"),
        ({"autonomy_default": "L3", "autonomy_max": "L2"}, "above autonomy_max"),
        ({"data_scope": "execution:rows"}, "data_scope"),
        ({"owner": "ROLE-EMP"}, "owner"),
        ({"approval_required": "maybe"}, "approval_required"),
        ({"input_schema": {"type": "object", "properties": {}}}, "additionalProperties"),
        ({"input_schema": {"type": "array"}}, "type must be"),
        (
            {
                "output_schema": {
                    "type": "object",
                    "properties": {"x": {}},
                    "additionalProperties": False,
                }
            },
            "no type",
        ),
        (
            {
                "input_schema": {
                    "type": "object",
                    "properties": {},
                    "required": ["x"],
                    "additionalProperties": False,
                }
            },
            "required",
        ),
        ({"compute": True}, "compute"),
        ({"name": "create_task"}, "TOOL-"),
        ({"risk_level": "extreme"}, "risk_level"),
        ({"data_classification": "TOP"}, "classification"),
        ({"autonomy_max": "L4"}, "L4"),
    ],
)
def test_invariants_rejected_at_construction(patch: dict[str, Any], why: str) -> None:
    with pytest.raises(ToolRegistryError, match=why):
        ToolDef(**(_base() | patch))


def test_read_invariants() -> None:
    read = get_tool("TOOL-get_metric")
    assert read is not None
    with pytest.raises(ToolRegistryError, match="READ"):
        replace(read, reversible=True)
    with pytest.raises(ToolRegistryError, match="READ"):
        replace(read, autonomy_max="L2")
    for t in TOOLS:
        if t.kind == "READ":
            assert (t.autonomy_default, t.autonomy_max, t.audit_required) == ("L0", "L0", False)
            assert t.reversible is None and t.action_name is None
            assert set(t.output_schema["required"]) == {"data", "sources"}  # type: ignore[index]
        else:
            assert t.audit_required is True and isinstance(t.reversible, bool)


def test_kind_invariants_across_registry() -> None:
    order = {"L0": 0, "L1": 1, "L2": 2, "L3": 3}
    for t in TOOLS:
        if t.kind == "APPROVAL":
            assert not t.declare_to_model
        if t.kind == "WRITE" and t.reversible is False:
            assert order[t.autonomy_max] <= 2, t.name
        if t.kind == "EXECUTION" and t.name != "TOOL-send_notification":
            assert order[t.autonomy_max] <= 2, t.name
        if t.kind in ("WRITE", "EXECUTION"):
            assert t.action_name and t.action_name.startswith("ACT-")
            assert tool_for_action(t.action_name) is t


def test_compute_tools_are_read() -> None:
    compute = {t.name for t in TOOLS if t.compute}
    assert compute == {"TOOL-get_runway_what_if", "TOOL-run_risk_scenario"}
    assert all(get_tool(n).kind == "READ" for n in compute)  # type: ignore[union-attr]


def test_tool_kind_lookup_defaults_to_read() -> None:
    assert tool_kind("TOOL-create_task") == "WRITE"
    assert tool_kind("TOOL-send_notification") == "EXECUTION"
    assert tool_kind("TOOL-approve_request") == "APPROVAL"
    assert tool_kind("TOOL-nope") == "READ"


def test_owner_follows_domain() -> None:
    owners = {"finance": "ROLE-DIR:F", "sales": "ROLE-DIR:C", "hr": "ROLE-DIR:O",
              "execution": "ROLE-CEO", "idp": "ROLE-ADM"}  # fmt: skip
    for t in TOOLS:
        if t.domain in owners:
            assert t.owner == owners[t.domain], t.name


def test_agent_allow_list_filters_advertised() -> None:
    perms = frozenset({"execution:read", "dashboard:read"})
    only = advertisable_for(perms, allowed=frozenset({"TOOL-list_tasks"}))
    assert [t.name for t in only] == ["TOOL-list_tasks"]


def _brd_rows() -> list[tuple[str, str]]:
    text = SPEC.read_text(encoding="utf-8")
    sec = text[text.index("### 2.2.") : text.index("## 3. Phân loại tool")]
    rows = re.findall(r"^\| ([^|]+) \| ([^|]+) \| [^|]+ \|$", sec, re.M)
    return [(b, t) for b, t in rows if "`" in b]


def test_brd_tools_mapped_or_excluded() -> None:
    """TC-M16-02: each BRD tool name of 10 §2.2 is either a `brd_name` of some registry tool
    or its row has no `TOOL-*` ("—", not-a-tool / deferred) — no silent gaps."""
    brd_names = {t.brd_name for t in TOOLS if t.brd_name}
    rows = _brd_rows()
    assert len(rows) >= 15
    for brd_cell, tool_cell in rows:
        names = re.findall(r"`([a-z_]+)`", brd_cell)
        if tool_cell.strip().startswith("—"):
            continue  # documented "không là tool / hoãn"
        for name in names:
            assert name in brd_names, f"BRD tool {name} has no TOOL-* with brd_name"
