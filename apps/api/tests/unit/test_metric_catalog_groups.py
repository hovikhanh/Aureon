"""TC-M21-01/02 — catalog nhóm v3 (R-DEC-82) + SEI đổi mã (R-DEC-83).

Nhóm v3 suy từ (pillar, source_module): FIN←F, CUS←C, OPS←O∩execution, PPL←O∩hr,
STR←S∩execution, DQ←pillar None. Risk nghiệp vụ (S∩risk) + Product (U) = p1_frozen.
"""

from app.modules.platform.services.catalog import (
    BY_CODE,
    CATALOG,
    FROZEN_CODES,
    GROUP_OF,
    GROUPS,
)

EXPECTED_GROUP = {
    "METRIC-FIN-01": "FIN", "METRIC-FIN-07": "FIN",
    "METRIC-CUS-01": "CUS", "METRIC-CUS-06": "CUS",
    "METRIC-OPS-01": "OPS", "METRIC-OPS-03": "OPS",
    "METRIC-HR-01": "PPL", "METRIC-HR-04": "PPL",
    "METRIC-STR-01": "STR", "METRIC-STR-02": "STR",
    "METRIC-DQ-01": "DQ", "METRIC-DQ-02": "DQ",
}  # fmt: skip


def test_group_mapping_matches_pillar_and_module() -> None:
    for code, group in EXPECTED_GROUP.items():
        assert BY_CODE[code].group == group, code
        assert GROUP_OF[code] == group


def test_every_metric_has_a_valid_group_or_is_frozen() -> None:
    for m in CATALOG:
        if m.p1_frozen:
            assert m.group is None, m.code
        else:
            assert m.group in GROUPS, m.code


def test_risk_business_and_product_are_frozen() -> None:
    # Risk nghiệp vụ (pillar S, module risk) + Product (pillar U) không nhóm v3.
    for code in ("METRIC-RSK-01", "METRIC-RSK-05", "METRIC-PRD-01", "METRIC-PRD-05"):
        assert BY_CODE[code].p1_frozen, code
        assert BY_CODE[code].group is None
        assert code in FROZEN_CODES


def test_sei_renamed_to_str02_not_rsk06() -> None:
    assert "METRIC-RSK-06" not in BY_CODE
    sei = BY_CODE["METRIC-STR-02"]
    assert sei.group == "STR"
    assert sei.pillar == "S"
    assert sei.source_module == "execution"
    assert sei.alert_code == "ALERT-STR-02"
    assert "execution.kpi_measured" in sei.refresh_events
    assert not sei.p1_frozen


def test_catalog_codes_unique() -> None:
    # FIN 7 + CUS 6 + OPS 3 + HR 4 + PRD 5 + RSK 5 + STR 2 + DQ 2 = 34 mã.
    codes = [m.code for m in CATALOG]
    assert len(codes) == len(set(codes)) == 34
