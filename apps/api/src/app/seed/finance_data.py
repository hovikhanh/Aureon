"""Finance seed data for company ABC (08 §3 DOC-01/02, §5, §10.4). Amounts in VND.

Totals are checked by `tests/unit/test_finance_seed_data.py` (08 §9 arithmetic checks).
"""

TY = 1_000_000_000  # 1 tỷ
TR = 1_000_000  # 1 triệu

# Monthly revenue (08 §1: 12 months 10/2025–09/2026 ≈ 294 tỷ; Q3 = 23,4 / 24,6 / 25,5 tỷ).
# 07–09/2025 exist for YoY growth; 10/2026 = 16,5 tỷ recognized 01–20/10 (DOC-03).
MONTHLY_REVENUE_MIL: dict[str, int] = {
    "2025-07": 21_000, "2025-08": 21_800, "2025-09": 22_400,
    "2025-10": 23_000, "2025-11": 23_500, "2025-12": 25_500, "2026-01": 24_000,
    "2026-02": 22_000, "2026-03": 24_500, "2026-04": 25_000, "2026-05": 26_000,
    "2026-06": 27_000, "2026-07": 23_400, "2026-08": 24_600, "2026-09": 25_500,
    "2026-10": 16_500,
}  # fmt: skip
# Product split of T9 (08 §1): SUP 19.125 / CARE 4.080 / ORDER 2.295 → 75 % / 16 % / 9 %.
PRODUCT_SPLIT = (("ABC Supply", "product_sales", 75), ("ABC Care", "service", 16),
                 ("ABC Order", "service", 9))  # fmt: skip
# COGS: Q3 = 60 tỷ (DOC-01, margin 18,4 %); other months 81 % of revenue.
COGS_MIL: dict[str, int] = {"2026-07": 19_080, "2026-08": 20_070, "2026-09": 20_850}
COGS_RATIO_PCT = 81
# Q3 budget vs actual opex by department, triệu. T-603b (08 §5): Kinh doanh overspends by
# 8,0 % (3.618 / 3.350) → METRIC-FIN-06 🟠 warning (catalog warn > 0, crit > 10 — human chose
# ~8 % over 08's "~12 %" to stay amber, 2026-10-23); every other department within budget.
Q3_BUDGET_ACTUAL_MIL: dict[str, tuple[int, int]] = {
    "BOD": (900, 880), "FIN": (1_100, 1_070), "SAL": (3_350, 3_618), "SVC": (3_050, 2_950),
    "HR": (400, 390), "PRD": (800, 770), "ADM": (450, 430),
}  # fmt: skip
Q3_PAYROLL_MIL = 8_000
# Month-end cash, triệu. T-603b (08 §5 — cash runway 🔴 is the demo's main alert): a steady
# ~0,9 tỷ/month decline to 06/2026, then 2,4 tỷ/month over Jul–Sep → BR-FIN-01 net burn 2,4 tỷ,
# runway = 12.600 / 2.400 = 5,25 months (< 6 → critical). 10/2026 = balance on 18/10.
CASH_MIL: dict[str, int] = {
    "2025-07": 30_000, "2025-08": 29_100, "2025-09": 28_100, "2025-10": 27_200,
    "2025-11": 26_300, "2025-12": 25_400, "2026-01": 24_400, "2026-02": 23_500,
    "2026-03": 22_600, "2026-04": 21_700, "2026-05": 20_700, "2026-06": 19_800,
    "2026-07": 17_400, "2026-08": 15_000, "2026-09": 12_600, "2026-10": 11_000,
}  # fmt: skip
# Oct 1–20 expenses — T-237 rebalance: net burn projected ≈ 2,3 tỷ vs forecast 2,5 tỷ →
# METRIC-FIN-07 variance ≈ −7 % (≤ 10 → green). (exp − 16.500) × 31 / 20 ≈ 2.325 → exp ≈ 18.000.
OCT_MTD_EXPENSE_MIL = {"cogs": 13_200, "salary": 2_800, "office": 1_050, "marketing": 950}
# Forecast Q4/2026 (base burn T10 = 2,5 tỷ), triệu: (revenue, expense) per month.
FORECAST_MIL: dict[str, dict[str, tuple[int, int]]] = {
    "base": {"2026-10": (26_000, 28_500), "2026-11": (27_000, 29_000),
             "2026-12": (29_000, 30_000)},
    "optimistic": {"2026-10": (27_500, 28_500), "2026-11": (28_800, 29_000),
                   "2026-12": (31_000, 30_000)},
    "pessimistic": {"2026-10": (24_500, 28_500), "2026-11": (25_000, 29_000),
                    "2026-12": (26_500, 30_000)},
}  # fmt: skip
FORECAST_CONFIDENCE = {"base": 75, "optimistic": 60, "pessimistic": 70}

# 08 §10.4 base scenario, triệu: (inflow_receivables, inflow_other, payables, payroll, opex,
# other_out). Start 19/10/2026, opening 11.000 (= 18/10 balance). Receivables = M1.0 weekly
# collections × 1,25 (T-603b: lower opening cash; the base scenario stays positive).
_CF_M10: tuple[tuple[int, int, int, int, int, int], ...] = (
    (4_200, 300, 2_100, 2_925, 800, 900), (5_200, 100, 6_200, 0, 800, 660),
    (4_800, 100, 5_400, 0, 800, 0), (5_000, 150, 5_200, 0, 800, 0),
    (4_600, 100, 4_300, 2_925, 800, 900), (4_400, 100, 5_900, 0, 800, 0),
    (3_800, 100, 5_240, 0, 800, 0), (7_600, 200, 4_300, 0, 800, 0),
    (6_800, 100, 4_600, 2_925, 800, 900), (7_400, 150, 4_100, 0, 800, 0),
    (6_900, 100, 4_500, 0, 800, 0), (7_200, 100, 4_400, 0, 800, 0),
    (4_725, 150, 4_200, 0, 800, 0),
)  # fmt: skip
CASH_FLOW_BASE_MIL = tuple((r * 5 // 4, *rest) for r, *rest in _CF_M10)
CASH_FLOW_START = "2026-10-19"
CASH_FLOW_OPENING_MIL = 11_000
COLLECTION_PCT = {"optimistic": 95, "base": 85, "pessimistic": 75}

# T-237 rebalance — open receivables carried across the trailing quarters so METRIC-FIN-04 DSO
# stays flat (~45 days) quarter over quarter (change ≈ 0 → OK) instead of jumping from ~0 (no
# prior open AR) at 2025-Q4 to ~60 at Q3. `receivables(end)` counts invoices by CURRENT status, so
# these carry a future due date (2027) to remain `sent` today → counted at every quarter end ≥
# their issue date, never overdue (they do NOT inflate METRIC-FIN-05). One invoice per quarter;
# its `total` (subtotal + 10 % VAT) brings cumulative open AR at that quarter end to ≈ 45 × (quarter
# revenue) / (days in quarter). Clients rotate over 8 accounts so top-5 concentration stays ≤ 50 %.
# A flat block of open AR established at 2025-Q4 and carried forward (future due date → always
# `sent`, never overdue). Spread over 8 clients (≈ 5,0 tỷ each) so top-5 concentration stays low.
# ≈ 40 tỷ keeps DSO ≈ 50 days each quarter; the small Sep HV open AR (see HV_PAID_IN_FULL) then
# perturbs 2026-Q3 by < 15 % → METRIC-FIN-04 OK. Clients reuse DOC-02 tax codes.
_HIST_CLIENTS: tuple[tuple[str, str], ...] = (
    ("Công ty TNHH FPT Trading", "0303334445"),
    ("Công ty Cổ phần Giáo dục Việt Nam", "0309876543"),
    ("Công ty TNHH Minh Phát", "0306667778"),
    ("Công ty Cổ phần Văn phòng Phẩm", "0301112223"),
    ("Công ty TNHH Giải pháp Số", "0304445678"),
    ("Công ty Cổ phần ABC Retail", "0302223334"),
    ("Công ty TNHH Đầu tư Đại Cường", "0302228877"),
    ("Công ty Cổ phần TechVN", "0301119988"),
)
# HV invoices (Sep batch) whose paid_amount is forced to full in seed_invoices → they close, so the
# Sep open AR shrinks to a realistic ≈ 4,2 tỷ (HV-001/008/030/032 + HL-001 remain overdue for the
# FIN-05 story). Keeps the 2026-Q3 DSO spike small (FIN-04 green) without rewriting DOC-02 numbers.
HV_PAID_IN_FULL: frozenset[str] = frozenset(
    f"HV-{n:03d}" for n in range(1, 48) if n not in (1, 8, 30, 32)
)


def _build_historical_open_invoices() -> tuple[tuple[str, str, str, str, int, int, int, str], ...]:
    """Eight ≈ 5,0 tỷ open invoices issued in 2025-Q4 (≈ 40 tỷ total), one per client."""
    rows: list[tuple[str, str, str, str, int, int, int, str]] = []
    for idx, (name, tax) in enumerate(_HIST_CLIENTS):
        subtotal = 4_545_000_000  # + 10 % VAT ≈ 5,0 tỷ total
        issued = f"2025-1{idx % 3}-15" if idx % 3 else "2025-10-15"
        rows.append((f"HC-{idx + 1:02d}", issued, name, tax, subtotal, 10, 0, "2027-12-31"))
    return tuple(rows)


HISTORICAL_OPEN_INVOICES = _build_historical_open_invoices()

# Generated from 08 §3 DOC-02 + HL-001 (number, issued, client, tax_code, subtotal, vat, paid, due)
INVOICES: tuple[tuple[str, str, str, str, int, int, int, str], ...] = (
    (
        "HV-001",
        "2026-09-02",
        "Công ty Cổ phần Giáo dục Việt Nam",
        "0309876543",
        780000000,
        10,
        0,
        "2026-10-02",
    ),
    (
        "HV-002",
        "2026-09-03",
        "Công ty TNHH TechSoft",
        "0305551234",
        750000000,
        10,
        825000000,
        "2026-10-18",
    ),
    (
        "HV-003",
        "2026-09-04",
        "Công ty TNHH Giải pháp Số",
        "0304445678",
        450000000,
        8,
        0,
        "2026-10-19",
    ),
    (
        "HV-004",
        "2026-09-05",
        "Công ty Cổ phần Văn phòng Phẩm",
        "0301112223",
        285000000,
        10,
        313500000,
        "2026-10-20",
    ),
    (
        "HV-005",
        "2026-09-06",
        "Công ty TNHH Minh Phát",
        "0306667778",
        960000000,
        10,
        0,
        "2026-11-05",
    ),
    (
        "HV-006",
        "2026-09-07",
        "Công ty Cổ phần ABC Retail",
        "0302223334",
        495000000,
        8,
        534600000,
        "2026-10-22",
    ),
    ("HV-007", "2026-09-08", "Công ty TNHH Đại Lợi", "0307778889", 720000000, 10, 0, "2026-10-23"),
    (
        "HV-008",
        "2026-09-09",
        "Công ty Cổ phần Giáo dục Việt Nam",
        "0309876543",
        420000000,
        10,
        0,
        "2026-10-09",
    ),
    (
        "HV-009",
        "2026-09-10",
        "Công ty TNHH An Khang",
        "0308889990",
        255000000,
        8,
        275400000,
        "2026-10-25",
    ),
    (
        "HV-010",
        "2026-09-11",
        "Công ty Cổ phần Văn phòng Phẩm",
        "0301112223",
        585000000,
        10,
        0,
        "2026-10-26",
    ),
    (
        "HV-011",
        "2026-09-12",
        "Công ty TNHH FPT Trading",
        "0303334445",
        870000000,
        10,
        957000000,
        "2026-10-27",
    ),
    (
        "HV-012",
        "2026-09-13",
        "Công ty TNHH Giải pháp Số",
        "0304445678",
        420000000,
        8,
        0,
        "2026-10-28",
    ),
    (
        "HV-013",
        "2026-09-14",
        "Công ty Cổ phần Thương mại Quốc tế",
        "0305556677",
        600000000,
        10,
        660000000,
        "2026-10-29",
    ),
    (
        "HV-014",
        "2026-09-15",
        "Công ty TNHH Minh Phát",
        "0306667778",
        525000000,
        10,
        0,
        "2026-11-14",
    ),
    (
        "HV-015",
        "2026-09-16",
        "Công ty Cổ phần TechVN",
        "0301119988",
        555000000,
        10,
        610500000,
        "2026-10-31",
    ),
    (
        "HV-016",
        "2026-09-17",
        "Công ty TNHH Đầu tư Đại Cường",
        "0302228877",
        810000000,
        10,
        0,
        "2026-11-01",
    ),
    (
        "HV-017",
        "2026-09-18",
        "Công ty Cổ phần Giáo dục Việt Nam",
        "0309876543",
        390000000,
        8,
        421200000,
        "2026-10-18",
    ),
    (
        "HV-018",
        "2026-09-19",
        "Công ty TNHH Thương mại Lộc Phát",
        "0303332211",
        570000000,
        10,
        0,
        "2026-11-03",
    ),
    (
        "HV-019",
        "2026-09-20",
        "Công ty Cổ phần Bút Tre VN",
        "0304443322",
        300000000,
        8,
        324000000,
        "2026-11-04",
    ),
    ("HV-020", "2026-09-21", "Công ty TNHH An Khang", "0308889990", 435000000, 10, 0, "2026-11-05"),
    (
        "HV-021",
        "2026-09-22",
        "Công ty Cổ phần Văn phòng Phẩm",
        "0301112223",
        720000000,
        10,
        792000000,
        "2026-11-06",
    ),
    (
        "HV-022",
        "2026-09-23",
        "Công ty TNHH FPT Trading",
        "0303334445",
        570000000,
        10,
        0,
        "2026-11-07",
    ),
    (
        "HV-023",
        "2026-09-24",
        "Công ty Cổ phần ABC Retail",
        "0302223334",
        480000000,
        8,
        518400000,
        "2026-11-08",
    ),
    (
        "HV-024",
        "2026-09-25",
        "Công ty TNHH Giải pháp Số",
        "0304445678",
        690000000,
        10,
        0,
        "2026-11-09",
    ),
    (
        "HV-025",
        "2026-09-26",
        "Công ty Cổ phần Giáo dục Việt Nam",
        "0309876543",
        525000000,
        10,
        577500000,
        "2026-10-26",
    ),
    ("HV-026", "2026-09-27", "Công ty TNHH Minh Phát", "0306667778", 360000000, 8, 0, "2026-11-26"),
    (
        "HV-027",
        "2026-09-28",
        "Công ty Cổ phần Văn phòng Phẩm",
        "0301112223",
        585000000,
        10,
        643500000,
        "2026-11-12",
    ),
    (
        "HV-028",
        "2026-09-29",
        "Công ty TNHH Đầu tư Đại Cường",
        "0302228877",
        555000000,
        10,
        0,
        "2026-11-13",
    ),
    (
        "HV-029",
        "2026-09-30",
        "Công ty Cổ phần TechVN",
        "0301119988",
        420000000,
        8,
        453600000,
        "2026-11-14",
    ),
    ("HV-030", "2026-09-01", "Công ty TNHH An Khang", "0308889990", 660000000, 10, 0, "2026-10-16"),
    (
        "HV-031",
        "2026-09-02",
        "Công ty Cổ phần Bút Tre VN",
        "0304443322",
        390000000,
        10,
        429000000,
        "2026-10-17",
    ),
    (
        "HV-032",
        "2026-09-03",
        "Công ty TNHH Thương mại Lộc Phát",
        "0303332211",
        600000000,
        10,
        0,
        "2026-10-18",
    ),
    (
        "HV-033",
        "2026-09-04",
        "Công ty Cổ phần Giáo dục Việt Nam",
        "0309876543",
        465000000,
        8,
        502200000,
        "2026-10-04",
    ),
    (
        "HV-034",
        "2026-09-05",
        "Công ty TNHH FPT Trading",
        "0303334445",
        690000000,
        10,
        0,
        "2026-10-20",
    ),
    (
        "HV-035",
        "2026-09-06",
        "Công ty Cổ phần ABC Retail",
        "0302223334",
        330000000,
        8,
        356400000,
        "2026-10-21",
    ),
    (
        "HV-036",
        "2026-09-07",
        "Công ty TNHH Minh Phát",
        "0306667778",
        630000000,
        10,
        0,
        "2026-11-06",
    ),
    (
        "HV-037",
        "2026-09-08",
        "Công ty Cổ phần Văn phòng Phẩm",
        "0301112223",
        435000000,
        10,
        478500000,
        "2026-10-23",
    ),
    (
        "HV-038",
        "2026-09-09",
        "Công ty TNHH Giải pháp Số",
        "0304445678",
        585000000,
        10,
        0,
        "2026-10-24",
    ),
    (
        "HV-039",
        "2026-09-10",
        "Công ty Cổ phần TechVN",
        "0301119988",
        480000000,
        8,
        518400000,
        "2026-10-25",
    ),
    (
        "HV-040",
        "2026-09-11",
        "Công ty TNHH Đầu tư Đại Cường",
        "0302228877",
        675000000,
        10,
        0,
        "2026-10-26",
    ),
    (
        "HV-041",
        "2026-09-12",
        "Công ty Cổ phần Giáo dục Việt Nam",
        "0309876543",
        405000000,
        10,
        445500000,
        "2026-10-12",
    ),
    ("HV-042", "2026-09-13", "Công ty TNHH An Khang", "0308889990", 615000000, 10, 0, "2026-10-28"),
    (
        "HV-043",
        "2026-09-14",
        "Công ty Cổ phần Bút Tre VN",
        "0304443322",
        375000000,
        8,
        405000000,
        "2026-10-29",
    ),
    (
        "HV-044",
        "2026-09-15",
        "Công ty TNHH Thương mại Lộc Phát",
        "0303332211",
        510000000,
        10,
        0,
        "2026-10-30",
    ),
    (
        "HV-045",
        "2026-09-16",
        "Công ty Cổ phần Văn phòng Phẩm",
        "0301112223",
        585000000,
        10,
        643500000,
        "2026-10-31",
    ),
    (
        "HV-046",
        "2026-09-17",
        "Công ty TNHH FPT Trading",
        "0303334445",
        480000000,
        8,
        300000000,
        "2026-11-01",
    ),
    (
        "HV-047",
        "2026-09-18",
        "Công ty Cổ phần ABC Retail",
        "0302223334",
        510000000,
        10,
        300000000,
        "2026-11-02",
    ),
    (
        "HL-001",
        "2026-06-01",
        "Công ty TNHH Thương mại Lộc Phát",
        "0303332211",
        660000000,
        10,
        0,
        "2026-07-16",
    ),
)
