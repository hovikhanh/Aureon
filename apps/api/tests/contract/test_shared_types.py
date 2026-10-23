"""TC-M11-08 (T-605, R-DEC-19) — `packages/shared-types/src/generated.ts` has no drift.

The committed file must equal a fresh render of `create_app().openapi()` by
`scripts/gen_shared_types.py`; on failure regenerate with
`PYTHONPATH=apps/api/src:apps/api .venv/bin/python scripts/gen_shared_types.py`.
"""

import importlib.util
from types import ModuleType

import pytest

from app.core.config import REPO_ROOT
from app.main import create_app

pytestmark = pytest.mark.contract
SCRIPT = REPO_ROOT / "scripts" / "gen_shared_types.py"


def _generator() -> ModuleType:
    spec = importlib.util.spec_from_file_location("gen_shared_types", SCRIPT)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_generated_types_match_openapi() -> None:
    gen = _generator()
    fresh = gen.render(create_app().openapi())
    assert gen.OUT.read_text(encoding="utf-8") == fresh, "generated.ts is stale — regenerate"


def test_generator_covers_every_schema_and_operation() -> None:
    gen = _generator()
    spec = create_app().openapi()
    text = gen.render(spec)
    for name in spec["components"]["schemas"]:
        assert f"export type {gen.ref_name(name)} = " in text
    ops = sum(1 for p in spec["paths"].values() for _ in p)
    assert text.count("    request: ") == ops


def test_ts_mapping_of_json_schema_nodes() -> None:
    ts = _generator().ts
    assert ts({"anyOf": [{"type": "string"}, {"type": "null"}]}) == "string | null"
    assert ts({"enum": ["a", "b"]}) == '"a" | "b"'
    assert ts({"type": "array", "items": {"$ref": "#/components/schemas/X"}}) == "X[]"
    assert ts({"type": "array", "items": {"anyOf": [{"type": "integer"}, {"type": "null"}]}}) == (
        "(number | null)[]"
    )
    assert ts({"type": "object", "additionalProperties": {"type": "number"}}) == (
        "Record<string, number>"
    )
    assert ts({"type": "object", "properties": {"a-b": {"const": 1}}, "required": ["a-b"]}) == (
        '{\n  "a-b": 1;\n}'
    )
    assert ts({"allOf": [{"$ref": "#/x/A"}, {"$ref": "#/x/B"}]}) == "A & B"
    assert ts({"type": ["string", "null"]}) == "string | null"
    assert ts({}) == "unknown" and ts(False) == "never"
    assert ts({"type": "array", "prefixItems": [{"type": "string"}, {"type": "integer"}]}) == (
        "[string, number]"
    )
