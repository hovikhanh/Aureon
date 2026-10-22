"""Business validation (04 §3 step 8, §5.3, FR-DC-14, T-405). Evaluates `ENT-ValidationRule`
expressions against the extracted field map and returns per-field `validation[]` entries plus
the aggregate error list (written to `ExtractionJob.xd_results.validation_errors`).

Rule kinds (`expression.op`):
- `date_not_future` — a date field must be ≤ today.
- `in`              — value ∈ a fixed set.
- `gt` / `gte` / `lt` / `lte` — numeric comparison against `value`.
- `required`        — value must be present (non-null).
- `sum_equals`      — cross-field: ``target ≈ Σ addends`` within `tolerance`.

`severity`: `fail`/`blocking` entries become errors (route to review / reject); `warn` is a
soft flag. Missing required fields are also errors.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Any

from app.core.clock import business_today


@dataclass
class ValidationEntry:
    rule: str
    status: str  # pass | warn | fail
    message: str
    field_name: str | None = None


@dataclass
class ValidationOutput:
    entries: list[ValidationEntry]

    @property
    def errors(self) -> list[dict[str, Any]]:
        return [
            {"rule": e.rule, "field": e.field_name, "message": e.message, "status": e.status}
            for e in self.entries
            if e.status == "fail"
        ]

    @property
    def ok(self) -> bool:
        return not self.errors

    def for_field(self, name: str) -> list[dict[str, Any]]:
        return [
            {"rule": e.rule, "status": e.status, "message": e.message}
            for e in self.entries
            if e.field_name == name
        ]


def _to_date(value: Any) -> date | None:
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, str):
        for fmt in ("%Y-%m-%d", "%d/%m/%Y"):
            try:
                return datetime.strptime(value, fmt).date()
            except ValueError:
                continue
    return None


def _to_number(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        cleaned = value.replace(".", "").replace(",", ".").replace(" ", "")
        try:
            return float(cleaned)
        except ValueError:
            return None
    return None


class Validator:
    def __init__(self, rules: list[dict[str, Any]], *, today: date | None = None) -> None:
        self.rules = rules
        self.today = today or business_today()

    def validate(
        self, values: dict[str, Any], *, required: set[str] | None = None
    ) -> ValidationOutput:
        entries: list[ValidationEntry] = []
        for name in sorted(required or set()):
            if values.get(name) is None:
                entries.append(
                    ValidationEntry("REQUIRED", "fail", f"trường bắt buộc thiếu: {name}", name)
                )
        for rule in self.rules:
            entries.append(self._eval(rule, values))
        return ValidationOutput([e for e in entries if e is not None])

    def _eval(self, rule: dict[str, Any], values: dict[str, Any]) -> ValidationEntry:
        expr = rule["expression"]
        op = expr["op"]
        code = rule["code"]
        severity = rule.get("severity", "fail")
        fail_status = "warn" if severity == "warn" else "fail"
        field_name = expr.get("field")

        if op == "required":
            ok = values.get(field_name) is not None
            return self._entry(code, ok, fail_status, field_name, f"{field_name} bắt buộc")

        if op == "date_not_future":
            d = _to_date(values.get(field_name))
            ok = d is None or d <= self.today
            return self._entry(code, ok, fail_status, field_name, f"{field_name} không ở tương lai")

        if op == "in":
            v = values.get(field_name)
            allowed = expr["values"]
            num = _to_number(v)
            ok = v is None or v in allowed or (num is not None and num in allowed)
            return self._entry(code, ok, fail_status, field_name, f"{field_name} ∈ {allowed}")

        if op in ("gt", "gte", "lt", "lte"):
            v = _to_number(values.get(field_name))
            threshold = float(expr["value"])
            ok = (
                v is None
                or {
                    "gt": v > threshold,
                    "gte": v >= threshold,
                    "lt": v < threshold,
                    "lte": v <= threshold,
                }[op]
            )
            return self._entry(code, ok, fail_status, field_name, f"{field_name} {op} {threshold}")

        if op == "sum_equals":
            target = _to_number(values.get(expr["target"]))
            addends = [_to_number(values.get(a)) for a in expr["addends"]]
            tolerance = float(expr.get("tolerance", 0))
            if target is None or any(a is None for a in addends):
                ok = True  # not measurable (a field is missing) — covered by REQUIRED
            else:
                ok = abs(target - sum(a for a in addends if a is not None)) <= tolerance
            return self._entry(
                code,
                ok,
                fail_status,
                expr["target"],
                f"{expr['target']} = Σ{expr['addends']} (±{tolerance})",
            )

        return ValidationEntry(code, "warn", f"quy tắc không hỗ trợ: {op}", field_name)

    @staticmethod
    def _entry(
        code: str, ok: bool, fail_status: str, field_name: str | None, message: str
    ) -> ValidationEntry:
        return ValidationEntry(code, "pass" if ok else fail_status, message, field_name)
