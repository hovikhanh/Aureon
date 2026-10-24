"""JSON Schema builders for `ToolDef.input_schema` / `output_schema` (10 §2.1 rows 3–4, T-644).

Hand-rolled draft 2020-12 subset (no `jsonschema` dependency): every object node has
`type=object`, `properties`, `additionalProperties=false`. READ output = `{data, sources}` where
`sources` are `SourceRef` (10 §8); WRITE/EXECUTION output = the AI action card summary.
"""

from __future__ import annotations

from typing import Any

S: dict[str, Any] = {"type": "string"}
INT: dict[str, Any] = {"type": "integer"}
NUM: dict[str, Any] = {"type": "number"}
DATE: dict[str, Any] = {"type": "string", "format": "date"}
DATETIME: dict[str, Any] = {"type": "string", "format": "date-time"}
UUID: dict[str, Any] = {"type": "string", "format": "uuid"}
PERIOD: dict[str, Any] = {"type": "string", "description": "YYYY-MM | YYYY-Qn | YYYY"}
LIMIT: dict[str, Any] = {"type": "integer", "minimum": 1, "maximum": 50}


def enum(*values: str) -> dict[str, Any]:
    return {"type": "string", "enum": list(values)}


def obj(required: tuple[str, ...] = (), **props: dict[str, Any]) -> dict[str, Any]:
    """`obj(("title",), title=S, due_date=DATE)` → closed object schema."""
    out: dict[str, Any] = {"type": "object", "properties": dict(props),
                           "additionalProperties": False}  # fmt: skip
    if required:
        out["required"] = list(required)
    return out


SOURCE_REF = obj(
    ("type", "id", "label"),
    type=enum("metric_value", "record", "document_page", "tool_result"),
    id=S, label=S, period_key=S, value={"type": ["number", "integer", "null"]}, lineage_url=S,
)  # fmt: skip
READ_OUT = obj(("data", "sources"), data={"type": "object"},
               sources={"type": "array", "items": SOURCE_REF})  # fmt: skip
WRITE_OUT = obj(
    ("action_id", "status", "autonomy_level"),
    action_id=UUID,
    status=enum("proposed", "confirmed", "executed", "rejected", "undone", "failed"),
    autonomy_level=enum("L0", "L1", "L2", "L3"),
    result_refs={"type": "array", "items": {"type": "object"}},
)
APPROVAL_OUT = obj(("request_id", "status"), request_id=UUID, status=S)
NO_ARGS = obj()
