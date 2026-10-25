"""#2 PLAN_KPI_OKR and #3 PERIOD_REPORT (04 §5 #2/#3; ACT order 10 §7.2.4).

Fields without `target` are row context: every ACT step of the row reads them by name
(`period_key`, `owner_code`, `unit`, `baseline`, `target` — executor.build_plan); a targeted
field also feeds same-named params (`objective_title` → KR, `kpi_code` → KPI target).
"""

from typing import Any

from app.modules.idp.services.catalog.base import doc_type, f

_O, _KR, _K, _KT = ("ACT-upsert_objective", "ACT-upsert_key_result", "ACT-upsert_kpi",
                    "ACT-upsert_kpi_target")  # fmt: skip
_M, _C = "ACT-record_kpi_measurement", "ACT-record_kr_checkin"
_T = "ACT-create_task"


def ctx(name: str, value_type: str, *aliases: str, required: bool = False) -> dict[str, Any]:
    return {"name": name, "label_key": f"idp.field.{name}", "value_type": value_type,
            "required": required, "is_critical": False, "sensitivity_level": 2, "group": "row",
            "header_aliases": list(aliases)}  # fmt: skip


PLAN_KPI_OKR = doc_type(
    "PLAN_KPI_OKR", "Kế hoạch / OKR / KPI", "Plan / OKR / KPI", ["F", "O", "C", "U", "S"], 2,
    ["okr", "kpi", "mục tiêu", "key result", "kết quả then chốt", "kế hoạch"],
    [_O, _KR, _K, _KT, _T],
    [
        ctx("period_key", "period", "kỳ", "period", required=True),
        ctx("owner_code", "text", "mã owner", "người phụ trách", "owner", required=True),
        ctx("unit", "text", "đơn vị", "unit"),
        ctx("baseline", "number", "baseline", "giá trị nền"),
        ctx("target", "number", "target", "mục tiêu số", "chỉ tiêu"),
        f("objective_title", "text", _O, "title", aliases=("mục tiêu", "objective")),
        f("kr_title", "text", _KR, "title", aliases=("kết quả then chốt", "key result", "kr")),
        f("kpi_code", "text", _K, "code", aliases=("mã kpi", "kpi code"),
          master_ref="execution.kpi_code"),
        f("kpi_name", "text", _K, "name", aliases=("tên kpi", "kpi")),
        f("kpi_period_target", "number", _KT, "target",
          aliases=("chỉ tiêu kỳ", "target kỳ", "period target")),
        # #2 action items (10 §7.2.4 ACT-create_task "#1, #2"; TC-M15-04 EMP creates own task):
        # a row with `task_title` adds one task (blank assignee = the caller, TaskService scope).
        f("task_title", "text", _T, "title", aliases=("việc cần làm", "công việc", "task")),
        f("assignee_code", "text", _T, aliases=("người thực hiện", "assignee"),
          master_ref="hr.employee_code"),
        f("task_due_date", "date", _T, "due_date", aliases=("hạn", "hạn chót", "due date")),
    ],
    [],
)  # fmt: skip

PERIOD_REPORT = doc_type(
    "PERIOD_REPORT", "Báo cáo kết quả định kỳ", "Periodic results report",
    ["F", "O", "C", "U", "S"], 2,
    ["báo cáo kết quả", "báo cáo tháng", "báo cáo quý", "thực hiện", "kết quả kỳ"],
    [_M, _C],
    [
        f("kpi_code", "text", _M, aliases=("mã kpi", "kpi code"), master_ref="execution.kpi_code"),
        f("period_key", "period", _M, aliases=("kỳ", "kỳ báo cáo", "period")),
        f("actual_value", "number", _M, critical=False, aliases=("thực tế", "actual")),
        f("kr_ref", "text", _C, aliases=("mã kr", "kr id")),
        f("value", "number", _C, aliases=("giá trị kr", "kr value")),
        f("confidence", "enum", _C, aliases=("độ tự tin", "confidence"),
          enum=["HIGH", "MEDIUM", "LOW"]),
        f("note", "text", _C, aliases=("ghi chú", "note")),
    ],
    [],
)  # fmt: skip
