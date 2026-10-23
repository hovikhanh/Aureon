"""TC-M11-06 (T-603b, 08 §2.1) — pure checks on the v3 org / execution seed data (no DB)."""

from collections import Counter

from app.seed import exec_data as X
from app.seed.auth_seed import DEMO_USERS
from app.seed.org_data import BY_NAME, DEPARTMENTS, PEOPLE, build_people, synthetic_name


def test_org_is_deterministic_and_sized_per_08() -> None:
    assert build_people() == PEOPLE
    assert [d.code for d in DEPARTMENTS] == ["BOD", "SAL", "SVC", "FIN", "HR", "PRD", "ADM"]
    current = Counter(p.dept for p in PEOPLE if p.status != "terminated")
    assert current == {d.code: d.size for d in DEPARTMENTS}
    assert sum(current.values()) == 148 and len(PEOPLE) == 154
    assert len({p.code for p in PEOPLE}) == len(PEOPLE) == len(BY_NAME)  # unique codes + names


def test_reporting_line_is_a_tree_rooted_at_the_ceo() -> None:
    by_code = {p.code: p for p in PEOPLE}
    roots = [p for p in PEOPLE if p.manager is None]
    assert [r.name for r in roots] == ["Nguyễn Văn An"]
    for p in PEOPLE:
        seen, cur = set(), p
        while cur.manager is not None:  # no cycles, every chain ends at the CEO
            assert cur.code not in seen
            seen.add(cur.code)
            cur = by_code[cur.manager]
        assert cur is roots[0]
    heads = {p.dept: p.name for p in PEOPLE if p.lead and p.team is None}
    assert heads == {d.code: d.head for d in DEPARTMENTS}


def test_demo_users_map_to_employees_in_their_department() -> None:
    for u in DEMO_USERS:
        assert BY_NAME[u.full_name].dept == u.dept, u.email


def test_execution_figures_match_08_section_5() -> None:
    window = [t for t in X.tasks() if t.due.month == 10 and t.due.day <= 20]
    on_time = [t for t in window if t.done is not None and t.done.date() <= t.due]
    assert (len(on_time), len(window)) == (17, 20)  # OPS-01 85 %
    meeting = [t for t in window if t.meeting]
    assert (sum(t.status == "done" for t in meeting), len(meeting)) == (6, 8)  # OPS-03 75 %
    assert len(X.ASSIGNEES) == 25 and len(X.OVERLOADED) == 3  # HR-03 12 %
    assert sum(len(krs) for *_, krs in X.OKRS) == 15 and len(X.KPIS) == 12
    assert synthetic_name(1) != synthetic_name(2)
