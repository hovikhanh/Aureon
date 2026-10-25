"""Metric catalog — 32 METRIC-* / ALERT-* from 03 §2–§3 (T-220, DEC-205).

Seeded into `platform.metrics` (thresholds there are the live, configurable values — NFR-19).
`direction`: LOWER_IS_BAD → breach when the compared number is below the threshold;
HIGHER_IS_BAD → above. `inclusive` → `≥` / `≤` instead of `>` / `<` (03 wording).
For "change vs 3-period average" metrics the provider sends `threshold_input` = the change
(points or %), so the catalog thresholds are expressed on that change.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class MetricDef:
    code: str
    pillar: str | None
    name_vi: str
    name_en: str
    unit: str
    direction: str
    warning: float
    critical: float
    source_module: str
    refresh_events: tuple[str, ...] = ()
    inclusive: bool = False

    @property
    def alert_code(self) -> str:
        return self.code.replace("METRIC-", "ALERT-")


LO, HI = "LOWER_IS_BAD", "HIGHER_IS_BAD"

CATALOG: tuple[MetricDef, ...] = (
    MetricDef("METRIC-FIN-01", "F", "Doanh thu vs kế hoạch", "Revenue vs target", "PERCENT", LO,
              90, 80, "finance", ("finance.invoice_paid",)),
    MetricDef("METRIC-FIN-02", "F", "Biên lợi nhuận gộp", "Gross margin", "PERCENT", HI, 3, 5,
              "finance"),
    MetricDef("METRIC-FIN-03", "F", "Cash runway", "Cash runway", "MONTHS", LO, 12, 6,
              "finance"),
    MetricDef("METRIC-FIN-04", "F", "DSO", "Days sales outstanding", "DAYS", HI, 15, 30,
              "finance", ("finance.invoice_paid",)),
    MetricDef("METRIC-FIN-05", "F", "Công nợ quá hạn", "Overdue receivables", "PERCENT", HI, 15,
              25, "finance"),
    MetricDef("METRIC-FIN-06", "F", "Chênh lệch ngân sách", "Budget variance", "PERCENT", HI, 0,
              10, "finance", ("finance.budget_exceeded",)),
    MetricDef("METRIC-FIN-07", "F", "Net burn vs dự báo", "Net burn vs forecast", "PERCENT", HI,
              10, 25, "finance", ("finance.burn_over_forecast", "finance.forecast_updated")),
    MetricDef("METRIC-OPS-01", "O", "Task đúng hạn", "On-time tasks", "PERCENT", LO, 80, 65,
              "execution", ("execution.task_overdue",)),
    MetricDef("METRIC-OPS-02", "O", "Dự án trễ", "Late projects", "PERCENT", HI, 20, 35,
              "execution"),
    MetricDef("METRIC-OPS-03", "O", "Thực thi quyết định", "Decision execution", "PERCENT", LO,
              70, 50, "execution", ("idp.document_committed",)),
    MetricDef("METRIC-HR-01", "O", "Doanh thu / nhân sự", "Revenue per employee",
              "VND_PER_PERSON", HI, 15, 25, "hr", ("hr.employee_onboarded",)),
    MetricDef("METRIC-HR-02", "O", "Turnover năm hóa", "Annualized turnover", "PERCENT", HI, 15,
              20, "hr", ("hr.employee_terminated",), inclusive=True),
    MetricDef("METRIC-HR-03", "O", "Quá tải", "Overload", "PERCENT", HI, 10, 20, "execution"),
    MetricDef("METRIC-HR-04", "O", "Kế hoạch tuyển dụng trễ", "Late hiring plans", "COUNT", HI,
              1, 45, "hr", ("hr.hiring_plan_delayed",), inclusive=True),
    MetricDef("METRIC-CUS-01", "C", "Pipeline coverage", "Pipeline coverage", "RATIO", LO, 2.8,
              2.5, "sales"),
    MetricDef("METRIC-CUS-02", "C", "Win rate", "Win rate", "PERCENT", HI, 10, 20, "sales",
              ("sales.deal_closed_won", "sales.deal_closed_lost")),
    MetricDef("METRIC-CUS-03", "C", "NRR", "Net revenue retention", "PERCENT", LO, 100, 90,
              "sales", ("finance.invoice_paid",)),
    MetricDef("METRIC-CUS-04", "C", "Tập trung doanh thu top 5", "Top-5 revenue concentration",
              "PERCENT", HI, 50, 65, "sales"),
    MetricDef("METRIC-CUS-05", "C", "NPS", "NPS", "SCORE", LO, 30, 0, "sales"),
    MetricDef("METRIC-CUS-06", "C", "Chu kỳ bán TB", "Average sales cycle", "DAYS", HI, 20, 40,
              "sales", ("sales.deal_closed_won",)),
    MetricDef("METRIC-PRD-01", "U", "Adoption / MAU", "Adoption / MAU", "COUNT", HI, 10, 20,
              "product"),
    MetricDef("METRIC-PRD-02", "U", "Churn", "Churn", "PERCENT", HI, 25, 50, "product",
              ("product.metric_anomaly",)),
    MetricDef("METRIC-PRD-03", "U", "Retention 30 ngày", "30-day retention", "PERCENT", LO, 40,
              25, "product"),
    MetricDef("METRIC-PRD-04", "U", "Roadmap đúng tiến độ", "Roadmap on track", "PERCENT", LO,
              70, 50, "product"),
    MetricDef("METRIC-PRD-05", "U", "Tính năng release trong kỳ", "Features released",
              "PERCENT", LO, 70, 40, "product", ("product.feature_released",)),
    MetricDef("METRIC-RSK-01", "S", "Rủi ro high/critical đang mở", "Open high/critical risks",
              "COUNT", HI, 1, 1, "risk", ("risk.risk_identified", "risk.risk_level_changed"),
              inclusive=True),
    MetricDef("METRIC-RSK-02", "S", "Rủi ro high chưa có chủ", "Unowned high risks", "COUNT",
              HI, 1, 1, "risk", ("risk.risk_identified",), inclusive=True),
    MetricDef("METRIC-RSK-03", "S", "Rủi ro high > 30 ngày không có mitigation",
              "High risks without mitigation > 30 days", "COUNT", HI, 1, 1, "risk",
              inclusive=True),
    MetricDef("METRIC-RSK-04", "S", "Điểm rủi ro tổng hợp", "Aggregate risk score", "SCORE", HI,
              10, 15, "risk", ("risk.risk_level_changed",), inclusive=True),
    MetricDef("METRIC-RSK-05", "S", "Biện pháp quá hạn", "Overdue mitigations", "COUNT", HI, 1,
              5, "risk", ("risk.risk_mitigated",), inclusive=True),
    MetricDef("METRIC-RSK-06", "S", "Strategy execution index (SEI)",
              "Strategy execution index", "PERCENT", LO, 70, 50, "execution",
              ("execution.kpi_measured",)),
    # M1.4 G2 (R-DEC-54, 03 §4): KPI/OKR updated on time
    MetricDef("METRIC-STR-01", "S", "KPI/OKR cập nhật đúng kỳ", "KPI/OKR updated on time",
              "PERCENT", LO, 80, 60, "execution",
              ("execution.kpi_measured", "execution.okr_checked_in")),
    MetricDef("METRIC-DQ-01", None, "Data Quality Score", "Data quality score", "SCORE", LO, 80,
              60, "platform", ("idp.document_committed", "idp.document_rolled_back")),
    MetricDef("METRIC-DQ-02", None, "Bản ghi mới vào qua tài liệu/NL",
              "New records captured from documents/NL", "PERCENT", LO, 60, 40, "capture",
              ("idp.document_committed", "idp.document_rolled_back")),
)  # fmt: skip

BY_CODE = {m.code: m for m in CATALOG}
PILLARS = ("F", "O", "C", "U", "S")


def evaluate(direction: str, x: float, warning: float, critical: float, inclusive: bool) -> str:
    """Status of number `x` against catalog thresholds → ok / warning / critical."""
    if direction == HI:
        crit = x >= critical if inclusive else x > critical
        warn = x >= warning if inclusive else x > warning
    else:
        crit = x <= critical if inclusive else x < critical
        warn = x <= warning if inclusive else x < warning
    return "critical" if crit else "warning" if warn else "ok"
