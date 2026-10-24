"""Event type registry — 00 §4.5 (28 `EVT-*`), names without the `EVT-` prefix (10 §8.1).

Only these types may be published (CLAUDE.md §5.4). S0a publishes none; the registry exists so
`publish_in_tx` rejects unknown names from day one.
"""

EVENT_TYPES: frozenset[str] = frozenset(
    {
        "execution.kpi_measured",
        "execution.task_overdue",
        "finance.budget_exceeded",
        "finance.burn_over_forecast",
        "finance.cash_flow_forecast_updated",
        "finance.forecast_updated",
        "finance.invoice_created",
        "finance.invoice_paid",
        "hr.employee_onboarded",
        "hr.employee_terminated",
        "hr.hiring_plan_delayed",
        "hr.salary_updated",
        "idp.document_committed",
        "idp.document_rolled_back",
        "idp.review_escalated",
        "platform.alert_raised",
        "platform.approval_decided",
        "platform.approval_requested",
        "platform.report_generated",
        "product.feature_released",
        "product.metric_anomaly",
        "product.product_launched",
        "risk.risk_identified",
        "risk.risk_level_changed",
        "risk.risk_mitigated",
        "risk.risk_proposed",
        "sales.deal_closed_lost",
        "sales.deal_closed_won",
    }
)


# M1.2 extension (R-DEC-35, 10 §9.2) — IDs allocated in 10, not in 00 §4.5 (human 2026-10-23).
EXTENSION_EVENT_TYPES: frozenset[str] = frozenset(
    {
        "auth.user_access_changed",
        "hr.org_structure_changed",
        "execution.task_created",  # M1.3 R-DEC-47 (BRD `task.created`)
        "execution.task_completed",  # M1.3 R-DEC-47 (BRD `task.completed`)
        "execution.kpi_below_threshold",  # M1.4 R-DEC-56 (BRD `kpi.below_threshold`)
        "execution.okr_checked_in",  # M1.4 R-DEC-56 (BRD `okr.checked_in`)
        "execution.okr_at_risk",  # M1.4 R-DEC-56 (BRD `okr.at_risk`)
    }
)


def is_registered(event_type: str) -> bool:
    return event_type in EVENT_TYPES or event_type in EXTENSION_EVENT_TYPES
