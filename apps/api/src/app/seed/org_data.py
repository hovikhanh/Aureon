"""Company ABC org chart v3 (08 §2.1, R-DEC-23/27) — pure, deterministic data (no DB).

7 departments, ~150 people. Each department: a head (reports to the CEO), team leads (report
to the head) and staff (report to their team lead). A few people are on probation and a few
left in the last 12 months (turnover). Names are synthetic (DEC-136): a fixed pool combined by
index, so the same code always gets the same name. Key people carry the names of the demo
accounts (`auth_seed.DEMO_USERS`) so a demo login maps to an employee record.
"""

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any


@dataclass(frozen=True)
class Dept:
    code: str
    name: str
    size: int  # active + probation headcount (08 §2.1 "quy mô gợi ý")
    teams: tuple[tuple[str, str], ...]  # (team code, team name)
    head: str  # name of the department head


# 08 §2.1 — order = employee code order. BOD has no team (the head is the CEO).
DEPARTMENTS: tuple[Dept, ...] = (
    Dept("BOD", "Ban Giám đốc", 3, (), "Nguyễn Văn An"),
    Dept("SAL", "Kinh doanh", 35, (("SAL-HCM", "Sales TP.HCM"), ("SAL-HN", "Sales Hà Nội"),
                                   ("SAL-KA", "Khách hàng lớn")), "Lê Hoàng Giang"),
    Dept("SVC", "Vận hành & Dịch vụ", 45, (("SVC-LOG", "Kho vận & giao nhận"),
                                           ("SVC-CARE", "Bảo trì ABC Care"),
                                           ("SVC-CS", "Chăm sóc khách hàng")), "Hoàng Minh Tuấn"),
    Dept("FIN", "Tài chính — Kế toán", 12, (("FIN-ACC", "Kế toán"),), "Trần Thị Minh"),
    Dept("HR", "Nhân sự", 8, (("HR-OPS", "Tuyển dụng & C&B"),), "Phạm Thị Hạnh"),
    Dept("PRD", "Sản phẩm/Công nghệ (ABC Order)", 30, (("PRD-BE", "Backend ABC Order"),
                                                       ("PRD-APP", "Ứng dụng & dữ liệu")),
         "Đỗ Quang Huy"),
    Dept("ADM", "Hành chính — Trợ lý", 15, (("ADM-OFF", "Hành chính văn phòng"),),
         "Lương Thị Mai"),
)  # fmt: skip

# Named staff (demo accounts) — (dept, team index, name).
NAMED_STAFF: tuple[tuple[str, int, str], ...] = (
    ("SVC", 1, "Ngô Thị Lan"),  # employee@ (ROLE-EMP)
    ("ADM", 0, "Vũ Đức Thắng"),  # reviewer@ (ROLE-REV)
    ("PRD", 1, "Trịnh Văn Khoa"),  # admin@ (ROLE-ADM — IT admin)
)

_FAMILY = ("Nguyễn", "Trần", "Lê", "Phạm", "Hoàng", "Huỳnh", "Phan", "Vũ", "Võ", "Đặng", "Bùi",
           "Đỗ", "Hồ", "Ngô", "Dương", "Lý")  # fmt: skip
_MIDDLE = ("Văn", "Thị", "Minh", "Thanh", "Quốc", "Ngọc", "Hữu", "Thu", "Đức", "Kim")
_GIVEN = ("Anh", "Bảo", "Châu", "Dũng", "Duy", "Giang", "Hà", "Hải", "Hiếu", "Hòa", "Hùng",
          "Khánh", "Linh", "Long", "Mai", "Nam", "Nga", "Nhung", "Phong", "Phúc", "Quân",
          "Quyên", "Sơn", "Tâm", "Thảo", "Thắng", "Trang", "Trí", "Tú", "Vy", "Yến")  # fmt: skip


def synthetic_name(n: int) -> str:
    """Deterministic fake full name for sequence `n` (strides co-prime with pool sizes)."""
    return f"{_FAMILY[n * 7 % 16]} {_MIDDLE[n * 3 % 10]} {_GIVEN[n * 11 % 31]}"


@dataclass(frozen=True)
class Person:
    code: str  # NV-0001…
    name: str
    dept: str
    team: str | None
    manager: str | None  # employee code of the direct manager (reporting line)
    status: str  # active | probation | terminated
    hired: date
    left: date | None
    salary_mil: int  # monthly base salary, triệu VND (fake, level 4)
    lead: bool = False  # department head or team lead


# Per department: probation hires (count) and leavers in the last 12 months (count, extra to
# `size`). Leavers ≈ 6 / 150 → HR-02 turnover stays ok; probation feeds UC-07 onboarding.
PROBATION = {"SAL": 2, "SVC": 2, "PRD": 1, "ADM": 1}
LEAVERS = {"SAL": 2, "SVC": 2, "PRD": 1, "ADM": 1}
REFERENCE = date(2026, 10, 20)


def _hire(n: int) -> date:
    return date(2015, 1, 5) + timedelta(days=n * 37 % 4000)


def build_people() -> tuple[Person, ...]:
    out: list[Person] = []
    named = {(d, t): name for d, t, name in NAMED_STAFF}
    seq = 0

    def add(**kw: Any) -> Person:
        nonlocal seq
        seq += 1
        p = Person(code=f"NV-{seq:04d}", **kw)
        out.append(p)
        return p

    ceo = add(name=DEPARTMENTS[0].head, dept="BOD", team=None, manager=None, status="active",
              hired=date(2012, 3, 1), left=None, salary_mil=120, lead=True)  # fmt: skip
    for d in DEPARTMENTS:
        head = ceo if d.code == "BOD" else add(
            name=d.head, dept=d.code, team=None, manager=ceo.code, status="active",
            hired=_hire(seq), left=None, salary_mil=70, lead=True)  # fmt: skip
        leads = [add(name=synthetic_name(seq), dept=d.code, team=tc, manager=head.code,
                     status="active", hired=_hire(seq), left=None, salary_mil=38, lead=True)
                 for tc, _ in d.teams]  # fmt: skip
        staff = d.size - 1 - len(leads)
        probation, leavers = PROBATION.get(d.code, 0), LEAVERS.get(d.code, 0)
        for i in range(staff + leavers):
            ti = i % len(leads) if leads else 0
            team, boss = (leads[ti].team, leads[ti].code) if leads else (None, head.code)
            name = named.pop((d.code, ti), None) if i < len(leads) else None
            if i >= staff:  # leavers: left within the last 12 months
                status, hired, left = (
                    "terminated",
                    _hire(seq),
                    REFERENCE - timedelta(days=20 + 45 * (i - staff) + 7 * len(out) % 30),
                )
            elif i >= staff - probation:  # newest hires on probation (Aug–Oct 2026)
                status, hired, left = (
                    "probation",
                    REFERENCE - timedelta(days=15 + 20 * (staff - 1 - i)),
                    None,
                )
            else:
                status, hired, left = "active", _hire(seq), None
            add(
                name=name or synthetic_name(seq),
                dept=d.code,
                team=team,
                manager=boss,
                status=status,
                hired=hired,
                left=left,
                salary_mil=14 + seq * 13 % 17,
            )
    return tuple(out)


PEOPLE: tuple[Person, ...] = build_people()
BY_NAME = {p.name: p for p in PEOPLE}
