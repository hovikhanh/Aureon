# STATE — Aureon v2.1 auto-pilot

| Field | Value |
|---|---|
| Last updated | 2026-10-22 03:10 (Asia/Saigon) |
| Last commit | `ed1836a` Merge branch 's1/hr' into s1/finance (on `main`, pushed) |
| Sub-sprint | S1 — CHECKPOINT #1 done (S1a Finance · S1b Sales · S1c HR) |
| Test count | 423 passed, 2 deselected (`-m "not live"`) |
| Coverage | 98% overall (`--cov=app`); finance 94–99%, sales 99%, hr 99% |
| Gates | A ✅ (docs current) · B ✅ (0 DEC open+blocking) · C ✅ (TC-FIN-001..007, TC-SEED-FIN-01, TC-SAL-001..003, TC-HR-001..004 Passed) |
| Open blocking DECs | none |

## Done
- S0, S0b (`8fe22a6`).
- S1a Finance T-101..T-106 + ABC seed: EP-60..69, EP-128, events `budget_exceeded`, `forecast_updated`, `invoice_created`, `invoice_paid`, `burn_over_forecast`, `cash_flow_forecast_updated`; consumers `finance.on_invoice_created/on_invoice_paid/on_salary_updated`. DEC-185..189, DEC-200..202.
- S1b Sales T-111..T-113 (EP-70..78), DEC-190..193.
- S1c HR T-121..T-123 (EP-80..87), DEC-195..198.
- Seed `uv run python -m app.seed`: roles/users + finance ABC (48 revenues, expenses for 7 departments, 16 cash positions, 7 Q3 budgets, 48 invoices, 3 forecasts, 3×13-week cash flows). Idempotent. Emits budget_exceeded ×6, burn_over_forecast, cash_flow_forecast_updated.

## In progress
- none

## Remaining (in order)
1. S1 leftovers in 09: T-131..133 Execution, T-141 event integration test, T-142/143 FE workspaces.
2. S2: T-201/202 Product, T-211..215 Risk, T-220 metric store (replaces live calculation in EP-60/70/80, DEC-200/197), T-221 alerts, T-222 pillar dashboards, T-223 lineage, T-229 DQ, T-230 approval, T-233; FE T-224..227, T-231, T-232.
3. S3 AI Core (T-3xx), S4 IDP v2.1 (T-4xx), S5 FE/UX/Release (Next.js login → dashboard → upload → review).
4. Sales/HR seeds (client ids = `seed_uuid("client", MST)`, dept = `seed_uuid("department", code)` in `app/seed/ids.py`).

## Next task
T-131 Execution (meetings, decisions, tasks, projects; `EVT-execution.task_overdue`) — or jump to T-220 metric store if S2 is prioritised.

## Key files
- `apps/api/src/app/modules/{finance,sales,hr}/` (routes/schemas/services/repositories)
- `apps/api/src/app/core/{idempotency,clock}.py`, `core/base_repository.py`
- `apps/api/src/app/seed/{finance_seed,finance_data,ids}.py`
- `apps/api/src/app/workers/consumers.py` (consumer modules list)
- `apps/api/tests/conftest.py` (`api` fixture / `ApiClient`)
- Worktrees: `/home/vika/aureon-wt/{fin,sales,hr}` (merged; may be removed)

## Known issues / gaps
- Dashboards EP-60/70/80: `metrics[]` computed live or empty, `open_alerts=0` until T-220/221.
- Celery beat has no daily jobs yet (FR-FIN-08 `check_burn_over_forecast`, invoice `mark_overdue`, HR `detect_delayed_hiring_plans`).
- `hr.employees.national_id/bank_account` stored as plain text (05 asks for pgcrypto) — needs DEC on key management.
- EP-74 `changed_by` null (DEC-191, schema gap).
- EP-87 workload returns [] until execution tasks exist.
- 09 task checkboxes not ticked (docs edit outside 14).
- Worktree `uv sync` fails on pillow-heif → use main `.venv` with `PYTHONPATH`.
