"""Helpers to declare a seed doc type compactly (05 §2.7 field JSON shape)."""

from typing import Any

THRESHOLDS = {"classification_confidence_min": 0.95, "required_field_min": 0.90}


def f(
    name: str, value_type: str, action: str, param: str | None = None, *,
    required: bool = False, critical: bool = False, level: int = 2,
    aliases: tuple[str, ...] = (), master_ref: str | None = None, enum: list[str] | None = None,
) -> dict[str, Any]:  # fmt: skip
    """One row-group field targeting `action.param` (param defaults to the field name)."""
    out: dict[str, Any] = {
        "name": name, "label_key": f"idp.field.{name}", "value_type": value_type,
        "required": required, "is_critical": critical, "sensitivity_level": level,
        "group": "row", "target": {"action": action, "param": param or name},
        "header_aliases": list(aliases),
    }  # fmt: skip
    if master_ref:
        out["master_ref"] = master_ref
    if enum:
        out["enum"] = enum
    return out


def doc_type(
    code: str, name_vi: str, name_en: str, pillars: list[str], sensitivity: int,
    keywords: list[str], actions: list[str], fields: list[dict[str, Any]],
    rules: list[dict[str, Any]],
) -> dict[str, Any]:  # fmt: skip
    return {
        "code": code, "name_vi": name_vi, "name_en": name_en, "pillars": pillars,
        "sensitivity_level": sensitivity, "retention_years": 10, "classifier_keywords": keywords,
        "action_names": actions, "fields": fields, "thresholds": THRESHOLDS, "rules": rules,
    }  # fmt: skip
