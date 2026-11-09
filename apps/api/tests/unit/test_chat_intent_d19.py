"""D-19 intent pre-selection (pure): which tools a question needs, which READ tools run first."""

from app.modules.ai.services.intent import select_tools

CEO = [
    "TOOL-get_finance_dashboard", "TOOL-get_sales_dashboard", "TOOL-get_hr_dashboard",
    "TOOL-get_execution_dashboard", "TOOL-get_metric", "TOOL-list_alerts", "TOOL-get_lineage",
    "TOOL-search_documents", "TOOL-get_source_document", "TOOL-get_kpi_status",
    "TOOL-get_org_tree", "TOOL-get_okr_status", "TOOL-get_project_status", "TOOL-create_task",
    "TOOL-execute_recommendation", "TOOL-record_decision",
]  # fmt: skip


def test_revenue_prefetches_the_finance_card_and_advertises_nothing_more() -> None:
    sel = select_tools("Doanh thu Q3?", CEO)
    assert sel.intents == ("finance",)
    assert sel.prefetch == ("TOOL-get_finance_dashboard",)
    assert sel.tools == ()


def test_diacritics_and_case_do_not_matter() -> None:
    assert select_tools("DÒNG TIỀN căng không?", CEO).prefetch == ("TOOL-get_finance_dashboard",)
    assert select_tools("dong tien cang khong", CEO).prefetch == ("TOOL-get_finance_dashboard",)


def test_intent_without_prefetch_keeps_its_tools_in_registry_order() -> None:
    sel = select_tools("OKR và KPI quý này?", CEO)
    assert sel.prefetch == ()
    assert sel.tools == ("TOOL-get_kpi_status", "TOOL-get_okr_status")


def test_write_intent_never_prefetches() -> None:
    sel = select_tools("Giao việc cho NV-0001 kiểm tra doanh thu", CEO)
    assert sel.prefetch == ()
    assert sel.tools is not None and "TOOL-create_task" in sel.tools


def test_overview_is_a_fallback_and_only_within_permitted_tools() -> None:
    assert select_tools("Tình hình công ty?", CEO).prefetch == (
        "TOOL-get_finance_dashboard", "TOOL-get_sales_dashboard", "TOOL-list_alerts")  # fmt: skip
    assert select_tools("Tình hình nhân sự?", CEO).intents == ("hr",)
    only_hr = ["TOOL-get_hr_dashboard", "TOOL-list_alerts"]
    assert select_tools("Tình hình công ty?", only_hr).prefetch == ("TOOL-list_alerts",)


def test_no_match_or_nothing_permitted_keeps_the_full_catalog() -> None:
    assert select_tools("Xin chào", CEO).tools is None
    assert select_tools("Doanh thu?", ["TOOL-get_org_tree"]).tools is None
    assert select_tools("Doanh thu?", ["TOOL-get_org_tree"]).prefetch == ()
