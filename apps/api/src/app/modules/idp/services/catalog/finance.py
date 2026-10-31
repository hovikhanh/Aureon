"""#6 FINANCE_REPORT "BC tài chính / sao kê số dư" (04 §5 #6; M2.2, R-DEC-92).

One statement row carries a `period` context and feeds whichever of the three finance-record
ACTs its targeted fields are present for: revenue → `ACT-record_revenue`, expense →
`ACT-record_expense`, closing balance → `ACT-record_cash_balance`. Money fields are critical
(R-DEC-69) → always reviewed before commit (04 §7.3).
"""

from typing import Any

from app.modules.idp.services.catalog.base import doc_type, f

_REV, _EXP, _CASH = (
    "ACT-record_revenue",
    "ACT-record_expense",
    "ACT-record_cash_balance",
)


def _ctx(name: str, value_type: str, *aliases: str, required: bool = False) -> dict[str, Any]:
    return {"name": name, "label_key": f"idp.field.{name}", "value_type": value_type,
            "required": required, "is_critical": False, "sensitivity_level": 2, "group": "row",
            "header_aliases": list(aliases)}  # fmt: skip


FINANCE_REPORT = doc_type(
    "FINANCE_REPORT", "BC tài chính / sao kê số dư", "Financial report / bank statement",
    ["F"], 2,
    ["báo cáo tài chính", "sao kê", "số dư", "dòng tiền", "doanh thu", "chi phí",
     "bank statement", "cash balance"],
    [_REV, _EXP, _CASH],
    [
        _ctx("period", "period", "kỳ", "period", "tháng", required=True),
        # revenue → ACT-record_revenue
        f("revenue_amount", "money", _REV, "amount", aliases=("doanh thu", "revenue")),
        f("revenue_category", "text", _REV, "category", aliases=("loại doanh thu",)),
        # expense → ACT-record_expense
        f("expense_title", "text", _EXP, "title", aliases=("khoản chi", "nội dung chi")),
        f("expense_amount", "money", _EXP, "amount", aliases=("chi phí", "expense")),
        f("expense_category", "text", _EXP, "category", aliases=("loại chi phí",)),
        f("expense_vendor", "text", _EXP, "vendor", aliases=("nhà cung cấp", "vendor")),
        # closing cash balance → ACT-record_cash_balance
        f("closing_balance", "money", _CASH, "balance",
          aliases=("số dư cuối kỳ", "số dư", "closing balance")),
    ],
    [],
)  # fmt: skip
