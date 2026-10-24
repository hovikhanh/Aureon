"""`python -m app.seed.snapshot` — export `seed_snapshot.json` for the mock FE (T-603b → T-604).

Deterministic view of the v3 seed: org chart, demo accounts (no passwords), the JWT
permission matrix of the 7 roles (mock login claims), projects, tasks, KPIs, OKRs, the
October meeting and the current company metric values (read through the platform's public
`MetricQueryService` after a seed + recompute). No level-4 data (salary, PII) and no
timestamps that change between runs, so the committed file only changes when the seed
changes (drift-checked by `tests/integration/test_seed_v3.py`).
"""

import asyncio
import json
from pathlib import Path
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.base_model import DEFAULT_TENANT_ID
from app.core.config import REPO_ROOT
from app.core.db import get_engine, get_sessionmaker
from app.core.tenant import tenant_scope
from app.modules.auth.permission_matrix import ROLE_PERMISSIONS, ROLE_REFS, ROLE_SCOPES
from app.modules.platform.services.metric_query import MetricQueryService
from app.seed import exec_data as X
from app.seed.auth_seed import AI_AGENT, DEMO_USERS, ROLES
from app.seed.hr_seed import ORG_CODE, ORG_NAME, ORG_VALID_FROM, TRANSFERS
from app.seed.org_data import BY_NAME, DEPARTMENTS, PEOPLE, REFERENCE

SNAPSHOT_PATH = REPO_ROOT / "apps" / "web" / "src" / "mocks" / "seed_snapshot.json"


def _assignments() -> list[dict[str, Any]]:
    """T-617: effective-dated placements (05 §2.4) — hire → now, split at the seeded moves."""
    moved = {code: (dept, team, mgr, at) for code, dept, team, mgr, at in TRANSFERS}
    out: list[dict[str, Any]] = []
    for p in PEOPLE:
        start, end = p.hired.isoformat(), p.left.isoformat() if p.left else None
        if p.code in moved and p.left is None:  # a terminated person is never moved
            dept, team, mgr, at = moved[p.code]
            out.append(
                {
                    "employee": p.code,
                    "department": dept,
                    "team": team,
                    "manager": mgr,
                    "valid_from": start,
                    "valid_to": at.isoformat(),
                }
            )
            start = at.isoformat()
        out.append(
            {
                "employee": p.code,
                "department": p.dept,
                "team": p.team,
                "manager": p.manager,
                "valid_from": start,
                "valid_to": end,
            }
        )
    return out  # fmt: skip


def _org() -> dict[str, Any]:
    return {
        "organization": {"code": ORG_CODE, "name": ORG_NAME,
                         "valid_from": ORG_VALID_FROM.isoformat()},
        "assignments": _assignments(),
        "departments": [
            {"code": d.code, "name": d.name, "head": BY_NAME[d.head].code,
             "teams": [{"code": c, "name": n} for c, n in d.teams]}
            for d in DEPARTMENTS
        ],
        "employees": [
            {"code": p.code, "full_name": p.name, "department": p.dept, "team": p.team,
             "manager": p.manager, "status": p.status, "hire_date": p.hired.isoformat()}
            for p in PEOPLE
        ],
    }  # fmt: skip


def _users() -> list[dict[str, Any]]:
    return [
        {"email": u.email, "role": u.role, "full_name": u.full_name, "department": u.dept,
         "scope_pillars": list(u.scope_pillars),
         "employee": None if u.role == "AI" else BY_NAME[u.full_name].code,
         "is_service_account": u.role == "AI"}
        for u in (*DEMO_USERS, AI_AGENT)
    ]  # fmt: skip


def _execution() -> dict[str, Any]:
    return {
        "projects": [
            {"code": c, "name": n, "department": d, "start_date": s.isoformat(),
             "planned_end_date": e.isoformat(), "tasks_done": done, "tasks_total": total}
            for c, n, d, s, e, done, total in X.PROJECTS
        ],
        "tasks": [
            {"key": t.key, "assignee": t.who.code, "due_date": t.due.isoformat(),
             "status": t.status, "estimate_hours": t.hours, "from_meeting": t.meeting}
            for t in X.tasks()
        ],
        "kpis": [
            {"code": c, "name": n, "department": d, "unit": u, "direction": dr, "target": tg,
             "measurements": dict(zip(X.KPI_PERIODS, a, strict=True))}
            for c, n, d, u, dr, tg, a, _ in X.KPIS
        ],
        "okrs": [
            {"code": c, "title": t, "department": d, "period_key": "2026-Q4",
             "key_results": [{"title": k, "unit": u, "baseline": b, "target": tg,
                              "current": cur, "confidence": conf}
                             for k, u, b, tg, cur, conf in krs]}
            for c, t, d, krs in X.OKRS
        ],
        "strategy": {"code": X.STRATEGY[0], "name": X.STRATEGY[1],
                     "period_start": X.STRATEGY[2].isoformat(),
                     "period_end": X.STRATEGY[3].isoformat(),
                     "strategic_objectives": [
                         {"code": c, "title": t, "pillar": p, "department": d, "owner": o,
                          "weight_pct": w, "kpis": list(k), "objectives": list(ob),
                          "initiative": i, "projects": list(pr)}
                         for c, t, p, d, o, w, k, ob, i, pr in X.STRATEGIC_OBJECTIVES]},
        "check_ins": [{"okr": o, "key_result": i, "value": v, "confidence": c,
                       "date": d.isoformat(), "by": by or "ceo@abc.demo", "note": n}
                      for o, i, v, c, d, by, n in X.CHECK_INS],
        "meeting": {"title": X.MEETING_TITLE, "held_at": X.MEETING_AT.isoformat(),
                    "decisions": [c for c, _, _ in X.DECISIONS]},
        "dependencies": [{"task": a, "depends_on": b} for a, b in X.DEPENDENCIES],
        "subtasks": [{"task": c, "parent": p} for c, p in X.SUBTASKS],
        "document_tasks": [{"task": k, "document": d, "page": pg}
                           for k, d, pg in X.DOCUMENT_TASKS],
        "milestones": [{"project": c, "title": t, "due_date": d.isoformat(), "status": st}
                       for c, t, d, st, _ in X.MILESTONES],
        "reassign_request": {"task": X.REASSIGN[0], "from": X.ASSIGNEES[0].code,
                             "to": X.REASSIGN[1].code, "department": X.ASSIGNEES[0].dept,
                             "status": "PENDING"},
    }  # fmt: skip


async def metrics(db: AsyncSession) -> list[dict[str, Any]]:
    rows = await MetricQueryService(db).current_values()
    return sorted(
        ({"code": v.metric_code, "pillar": v.pillar, "value": v.value, "unit": v.unit,
          "status": v.status, "period_key": v.period_key} for v in rows),
        key=lambda r: str(r["code"]),
    )  # fmt: skip


def build(metric_rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {"reference_date": REFERENCE.isoformat(), "company": "Công ty TNHH TM&DV ABC",
            "users": _users(), **_org(), **_execution(), "metrics": metric_rows,
            "role_permissions": {r: sorted(p) for r, p in ROLE_PERMISSIONS.items()},
            "roles": _roles()}  # fmt: skip


def _roles() -> list[dict[str, Any]]:
    """EP-ADM-11 catalog (T-617F mock SCR-54) — names, khối and scope notes per role."""
    return [{"code": r.code, "role_ref": ROLE_REFS[r.code], "name_vi": r.name_vi,
             "name_en": r.name_en, "pillars": list(r.pillars),
             "scope_rules": dict(sorted(ROLE_SCOPES.get(r.code, {}).items()))}
            for r in ROLES]  # fmt: skip


def render(data: dict[str, Any]) -> str:
    return json.dumps(data, ensure_ascii=False, indent=1, sort_keys=True) + "\n"


async def _collect() -> list[dict[str, Any]]:
    async with get_sessionmaker()() as session:
        rows = await metrics(session)
    await get_engine().dispose()
    return rows


def export(path: Path = SNAPSHOT_PATH) -> None:
    with tenant_scope(DEFAULT_TENANT_ID):
        rows = asyncio.run(_collect())
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render(build(rows)), encoding="utf-8")
    print(f"wrote {path.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    export()
