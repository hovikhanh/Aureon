"""Execution seed data v3 (T-603b, 08 §3 D07–D12, §4, §5) — pure, deterministic (no DB).

Targets of 08 §5 (checked by `tests/integration/test_seed_v3.py` through the real providers):
OPS-01 🟢 85 % (20 tasks due 1–20/10, 17 done on time) · OPS-03 🟢 75 % (8 meeting tasks, 6
done) · HR-03 🟠 12 % (3 of 25 assignees > 110 % two weeks running) · OPS-02 🟢 10 % (1 of 10
projects > 10 pts behind plan) · SEI 🟢 75 % (3 of 4 weighted initiatives on track).
"""

from dataclasses import dataclass
from datetime import UTC, date, datetime

from app.seed.org_data import PEOPLE, Person

CREATED = datetime(2026, 9, 25, 2, tzinfo=UTC)
MEETING_AT = datetime(2026, 9, 30, 2, tzinfo=UTC)  # giao ban tháng 10 (UC-02/06 source)


def _assignees() -> tuple[Person, ...]:
    """25 active staff (not leads) spread over the operating departments; the EMP demo account
    (Ngô Thị Lan) is one of them so ROLE-EMP sees own tasks."""
    pool = [p for p in PEOPLE if p.status == "active" and not p.lead and p.dept != "BOD"]
    per = {"SVC": 8, "SAL": 7, "PRD": 5, "FIN": 2, "ADM": 2, "HR": 1}
    out: list[Person] = [p for p in pool if p.name == "Ngô Thị Lan"]
    for dept, n in per.items():
        out += [p for p in pool if p.dept == dept and p not in out][: n - (dept == "SVC")]
    return tuple(out)


ASSIGNEES = _assignees()
OVERLOADED = ASSIGNEES[21:24]  # 46 h open in both weeks → > 110 % of 40 h


@dataclass(frozen=True)
class TaskRow:
    key: str
    who: Person
    due: date
    status: str
    done: datetime | None
    meeting: bool
    hours: int


def tasks() -> tuple[TaskRow, ...]:
    out: list[TaskRow] = []
    for i in range(20):  # due window 1–20/10
        due = date(2026, 10, i + 1)
        status = {15: "blocked", 17: "in_progress"}.get(i, "done")
        done_day = due.day + 2 if i == 4 else max(due.day - 1, 1)  # i=4 done late
        done = datetime(2026, 10, done_day, 9, tzinfo=UTC) if status == "done" else None
        out.append(TaskRow(f"T-{i + 1:02d}", ASSIGNEES[i], due, status, done, i % 5 in (0, 2), 6))
    for i, p in enumerate(ASSIGNEES):  # open load after the window
        hours = (24, 22) if p in OVERLOADED else (8,)
        for j, h in enumerate(hours):
            out.append(TaskRow(f"T-L{i:02d}{j}", p, date(2026, 10, 25 + j * 3), "todo", None,
                               False, h))  # fmt: skip
    return tuple(out)


# code, name, dept, start, planned end, tasks done / total. Planned % at 20/10 is linear; actual =
# done / total. Only PRJ-ERP lags > 10 pts (planned 73 %, actual 3/6 = 50 %) → OPS-02 = 10 %.
PROJECTS: tuple[tuple[str, str, str, date, date, int, int], ...] = (
    ("PRJ-ERP", "Triển khai ERP kho", "FIN", date(2026, 7, 1), date(2026, 11, 30), 3, 6),
    ("PRJ-HN", "Mở rộng chi nhánh Hà Nội", "SAL", date(2026, 9, 1), date(2027, 3, 31), 1, 4),
    ("PRJ-ORD4", "ABC Order 4.0", "PRD", date(2026, 10, 1), date(2027, 6, 30), 0, 4),
    ("PRJ-CRM", "Chuẩn hóa CRM khách hàng lớn", "SAL", date(2026, 6, 1), date(2026, 12, 31),
     4, 6),
    ("PRJ-CARE", "Gói bảo trì ABC Care 2027", "SVC", date(2026, 8, 1), date(2027, 1, 31), 2, 5),
    ("PRJ-WMS", "Tối ưu kho Bình Dương", "SVC", date(2026, 5, 1), date(2026, 12, 15), 5, 7),
    ("PRJ-DATA", "Kho dữ liệu điều hành", "PRD", date(2026, 9, 15), date(2027, 2, 28), 1, 5),
    ("PRJ-HRIS", "Số hóa hồ sơ nhân sự", "HR", date(2026, 8, 15), date(2026, 12, 31), 2, 4),
    ("PRJ-OFFICE", "Chuyển văn phòng Hà Nội", "ADM", date(2026, 9, 1), date(2026, 11, 30),
     3, 6),
    ("PRJ-KA", "Chương trình khách hàng chiến lược", "SAL", date(2026, 7, 15),
     date(2026, 12, 31), 3, 5),
)  # fmt: skip

# code, title, pillar, dept, start, end, progress %, weight %. On track = progress ≥ 90 % of the
# linear plan: INI-01 (72,2 needed) 74 ✔ · INI-02 (66,4) 70 ✔ · INI-03 (41,9) 30 ✘ ·
# INI-04 (54,6) 58 ✔ → SEI = (30 + 25 + 20) / 100 = 75 %.
INITIATIVES = (
    ("INI-01", "Tăng trưởng doanh thu 15%", "C", "SAL", date(2026, 1, 1), date(2026, 12, 31),
     74, 30),
    ("INI-02", "Giảm DSO xuống 45 ngày", "F", "FIN", date(2026, 4, 1), date(2026, 12, 31), 70,
     25),
    ("INI-03", "Ra mắt ABC Insight", "U", "PRD", date(2026, 6, 1), date(2027, 3, 31), 30, 25),
    ("INI-04", "Chuẩn hóa quy trình bảo trì", "O", "SVC", date(2026, 7, 1), date(2026, 12, 31),
     58, 20),
)  # fmt: skip

# D08 KPI tree (company → department), monthly, 3 periods (Jul–Sep). (code, name, dept, unit,
# direction, target, actuals Jul/Aug/Sep, parent). UC-03: KPI-SAL-01 drops below 70 % in Sep.
KPIS: tuple[tuple[str, str, str | None, str, str, float, tuple[float, float, float], str | None],
            ...] = (
    ("KPI-CO-01", "Doanh thu thuần (tỷ)", None, "tỷ VND", "HIGHER_IS_BETTER", 27.0,
     (23.4, 24.6, 25.5), None),
    ("KPI-CO-02", "Biên lợi nhuận gộp (%)", None, "%", "HIGHER_IS_BETTER", 20.0,
     (18.5, 18.4, 18.2), None),
    ("KPI-SAL-01", "Doanh số mới khách hàng lớn (tỷ)", "SAL", "tỷ VND", "HIGHER_IS_BETTER", 6.0,
     (5.4, 4.6, 3.9), "KPI-CO-01"),
    ("KPI-SAL-02", "Số cơ hội mới", "SAL", "cơ hội", "HIGHER_IS_BETTER", 12, (12, 11, 10),
     "KPI-CO-01"),
    ("KPI-SVC-01", "Tỷ lệ bảo trì đúng SLA (%)", "SVC", "%", "HIGHER_IS_BETTER", 95,
     (94, 95, 96), None),
    ("KPI-SVC-02", "Thời gian giao hàng TB (ngày)", "SVC", "ngày", "LOWER_IS_BETTER", 2.0,
     (2.1, 2.0, 1.9), None),
    ("KPI-FIN-01", "DSO (ngày)", "FIN", "ngày", "LOWER_IS_BETTER", 45, (48, 46, 45),
     "KPI-CO-02"),
    ("KPI-FIN-02", "Chi phí vận hành / doanh thu (%)", "FIN", "%", "LOWER_IS_BETTER", 12,
     (12.5, 12.2, 12.0), "KPI-CO-02"),
    ("KPI-HR-01", "Thời gian tuyển dụng TB (ngày)", "HR", "ngày", "LOWER_IS_BETTER", 30,
     (34, 32, 31), None),
    ("KPI-PRD-01", "Đơn hàng qua ABC Order (%)", "PRD", "%", "HIGHER_IS_BETTER", 35,
     (30, 31, 33), None),
    ("KPI-PRD-02", "Sự cố nghiêm trọng / tháng", "PRD", "sự cố", "LOWER_IS_BETTER", 2,
     (2, 2, 1), None),
    ("KPI-ADM-01", "Hồ sơ số hóa đúng hạn (%)", "ADM", "%", "HIGHER_IS_BETTER", 90, (88, 90, 92),
     None),
)  # fmt: skip
KPI_PERIODS = ("2026-07", "2026-08", "2026-09")

# D09 OKR Q4/2026 (ends 31/12 — ≥ 3 weeks after 20/10, UC-04). (code, title, dept, KRs) with
# KR = (title, unit, baseline, target, current, confidence). OKR-SAL's 2nd KR is at risk
# (progress 20 % at ~22 % of the quarter, confidence LOW) → UC-04.
OKRS: tuple[tuple[str, str, str | None, tuple[tuple[str, str, float, float, float, str], ...]],
            ...] = (
    ("OKR-CO", "Tăng trưởng có lãi, giữ dòng tiền an toàn", None, (
        ("Doanh thu Q4 đạt 85 tỷ", "tỷ VND", 0, 85, 16.5, "MEDIUM"),
        ("Runway ≥ 6 tháng cuối quý", "tháng", 5.25, 6, 5.25, "LOW"),
        ("Biên lợi nhuận gộp ≥ 20%", "%", 18.2, 20, 18.4, "MEDIUM"))),
    ("OKR-SAL", "Mở rộng khách hàng lớn", "SAL", (
        ("Ký 6 hợp đồng khách hàng lớn", "hợp đồng", 0, 6, 2, "MEDIUM"),
        ("Pipeline trọng số ≥ 3x chỉ tiêu", "x", 2.4, 3.0, 2.52, "LOW"),
        ("Tỷ lệ thắng ≥ 65%", "%", 60, 65, 63, "HIGH"))),
    ("OKR-SVC", "Dịch vụ đúng hẹn", "SVC", (
        ("Bảo trì đúng SLA ≥ 97%", "%", 94, 97, 96, "HIGH"),
        ("Giao hàng TB ≤ 1,8 ngày", "ngày", 2.1, 1.8, 1.9, "MEDIUM"))),
    ("OKR-FIN", "Kỷ luật dòng tiền", "FIN", (
        ("DSO ≤ 42 ngày", "ngày", 48, 42, 45, "MEDIUM"),
        ("Chi phí vận hành ≤ 11,5% doanh thu", "%", 12.5, 11.5, 12.0, "MEDIUM"))),
    ("OKR-HR", "Đủ người cho tăng trưởng", "HR", (
        ("Tuyển đủ 14 vị trí kế hoạch", "người", 0, 14, 3, "MEDIUM"),
        ("Thời gian tuyển TB ≤ 28 ngày", "ngày", 34, 28, 31, "MEDIUM"))),
    ("OKR-PRD", "ABC Order thành kênh chính", "PRD", (
        ("35% đơn hàng qua ABC Order", "%", 30, 35, 33, "HIGH"),
        ("≤ 1 sự cố nghiêm trọng / tháng", "sự cố", 2, 1, 1, "HIGH"),
        ("Ra mắt ABC Insight beta", "mốc", 0, 1, 0, "LOW"))),
)  # fmt: skip

# D12 — giao ban tháng 10 (UC-02/06): ≥ 3 decisions, ≥ 5 action items (= meeting tasks T-01,
# T-03, T-06, T-08, T-11, T-13, T-16, T-18 — `exec_data.tasks()` with meeting=True).
MEETING_TITLE = "Họp giao ban tháng 10/2026"
DECISIONS = (
    (
        "Ưu tiên thu hồi công nợ quá hạn > 30 ngày trong tháng 10",
        "FIN",
        "Runway về ≥ 6 tháng vào cuối Q4",
    ),
    ("Tạm dừng tuyển mới khối hỗ trợ tới hết Q4", "HR", "Tiết kiệm ~0,4 tỷ/tháng"),
    ("Tập trung đội Sales vào 5 cơ hội lớn nhất Q4", "SAL", "Coverage ≥ 3x trước 15/11"),
)
