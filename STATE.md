# STATE — Aureon v2.1 auto-pilot

| Field | Value |
|---|---|
| Last updated | 2026-10-22 11:18 (Asia/Saigon) |
| Last commit | `3bdee1f` feat(platform): SEED_PASSWORD_* aliases (T-237 Step 3) on `main` |
| Sub-sprint | S2 — CHECKPOINT #2 done + **T-237 seed rebalance done** (2 green / 2 yellow / 1 red) |
| Test count | 585 passed, 2 deselected (`-m "not live"`) |
| Coverage | 98% overall (`--cov=app`) |
| Gates | A ✅ · B ✅ (0 DEC open+blocking) · C ✅ (TC-DASH-*, TC-EXE-007, TC-DQ-001, TC-SEED-002/003, TC-EVT-007 Passed) |
| Open blocking DECs | none |

## Done
- S0, S0b, S1 (Finance/Sales/HR) — see git history (`ed1836a`).
- S2 (`a0fd762`):
  - T-220 metric store (`platform.services.metric_store.MetricStore.recompute`, providers `@metric_provider` per module), METRIC-DQ-01 (`core/data_quality.py` + `register_dq` per domain, DEC-209).
  - T-221 alert engine; budget_exceeded → alert < 60 s test.
  - T-222 pillar dashboards EP-60/70/80/90/100 + EP-49 from store (`pillar_snapshot`), partial-failure isolation.
  - T-131..133 execution, T-201/202 product, T-211..216 risk (merged worktrees `/home/vika/aureon-wt/{exec,prdrisk,risk}`).
  - T-234 pgcrypto level-4 PII, migration `0008_pgcrypto`; T-235 Celery beat (7 entries incl. outbox relay, detect-overdue-tasks 08:30).
  - T-236 seed: auth + finance + hr + sales + product + risk + execution (reduced, DEC-208). Dev DB: 32/32 metrics valued, 25 OPEN alerts, all dashboards 200.
- Shared: `core/periods.py` (period resolution, breaks hr↔execution cycle); metric provider registry tolerates re-import of same function.

## S2 exit criteria
| Criterion | Result |
|---|---|
| 5 pillar endpoints 200 | ✅ (+EP-49) |
| ≥ 10 alerts from seed | ✅ 25 OPEN |
| revenue → budget_exceeded → alert ≤ 60 s | ✅ `tests/events/test_alert_sla.py` |
| beat jobs registered | ✅ 7 entries |
| 3 pgcrypto tests | ✅ |
| Sales/HR dashboards non-zero | ✅ |
| 32 metrics populated | ✅ |
| Coverage ≥ 95 %, gates A/B/C | ✅ 98 % |

## T-237 seed rebalance (done 2026-10-22, direct route cc/claude-sonnet-5; 3 commits)
- **Step 1** (analysis, no edits): identified per-pillar levers vs DEC-143.
- **Step 2** `b0cefa4` feat(s2): seed data → **F,C green · U,O yellow · S red**. Edited `finance_data.py` (cash flatter→runway 13.6, Q3 budget ≤ alloc, Oct MTD trimmed, 8 carried-forward open invoices `HISTORICAL_OPEN_INVOICES` + `HV_PAID_IN_FULL`), `sales_seed.py` (Sep target 26.0tỷ, Q4 18.0tỷ, `attribute_revenue` splits big row over 5 anchor clients + frozen window for NRR), `product_seed.py` (Sep churn 1.79, retention 43, NPS lift), `hr_seed.py` (1 plan 40d late). Updated 3 finance_seed assertions.
- **Step 3** `3bdee1f` feat(platform): `SEED_PASSWORD_CPO`/`SEED_PASSWORD_RISK_MANAGER` aliases on config + `.env.example`. Dev `.env` got CPO/RISK/MANAGER/EMPLOYEE/ADMIN passwords → seed creates all 10 users; product owner=CPO, risk owner=RISK_MANAGER.
- **Verified** (clean-DB `python -m app.seed` + in-process API as CEO): F green · C green · O yellow · U yellow · S red; 13 OPEN alerts (11 WARNING + 2 CRITICAL). `probe3.py` harness truncates domain schemas in a rolled-back tx.
- **Divergence logged:** DEC-230 (proposed, agent) in 13-DECISION-LOG — T-237 overrides DEC-143/152 pillar layout; brief "2 info" infeasible (enum has only WARNING/CRITICAL). **Human to assign DEC number + resolve.**
- Gate: ruff ✅ · mypy ✅ (226 files) · pytest 585 ✅.

## In progress
- none

## Remaining (in order)
1. S3 AI Core (T-3xx per 09): ModelGateway already exists from S0 — check 09 for T-301.. (chat SSE EP-110.., Tool Registry, insight, autonomy L0–L3, kill switch, cost log).
2. S4 IDP v2.1 (T-4xx).
3. S5 FE/UX/Release (Next.js login → dashboard → upload → review); S2 FE tasks T-224..227, T-231/232, T-142/143 still open.
4. `[DEFERRED to S5]` T-223 lineage drill-down (DEC-229).
5. `[DEFERRED to S3]` T-230 approval — after AI actions exist (DEC-229).
6. `[DEFERRED to S5]` T-233 + FE S2 tasks T-224..227, T-231, T-232, T-142/143 (DEC-229).
7. `[DONE]` T-237 seed rebalance 2 green / 2 yellow / 1 red + CPO/RISK_MANAGER users.

## Next task
S3 — read 09 S3 section (T-3xx), gates A/B/C for AI Core (load 00, 01, 02, 07, 10), then start T-301.

## Key files
- `apps/api/src/app/modules/platform/services/{metric_store,pillar_snapshot,metrics}.py`, `core/{metrics,data_quality,periods}.py`
- `apps/api/src/app/seed/{__init__,finance_seed,hr_seed,sales_seed,product_seed,risk_seed,execution_seed,ids}.py`
- `apps/api/src/app/workers/{consumers,jobs}.py`, `apps/api/src/app/worker.py`
- Env: `export PYTHONPATH=$PWD/apps/api/src:$PWD/apps/api PATH=$PWD/.venv/bin:$PATH` (never `uv sync`).

## Human decisions (2026-10-22)
- DEC-227 (human "DEC-210"): DQ-01 = 87.0 accepted; 77.1 aspirational; calibration S4.
- DEC-228 (human "DEC-211"): sub-agents = single code tasks only; seed / cross-file / orchestration by DSH.
- DEC-229: deferrals above. (Numbers 210/211 were already taken by Product DECs → renumbered.)

## Known issues / gaps
- EP-74 `changed_by` null (DEC-191); MANAGER quota null; no log-redaction filter yet.
- ~~Dev DB only 5 users~~ **fixed by T-237**: dev `.env` now has all 10 demo passwords; product owner=CPO, risk owner=RISK_MANAGER.
- Risk: EP-104 doesn't create ENT-Decision; what-if product unavailable; `hr.employee_terminated` not consumed.
- Product BR-PRD-01 thresholds constants; execution constants not in config (DEC-226).
- METRIC-DQ-01 accuracy = validation proxy; IDP-correction component comes with S4.
- 09 task checkboxes not ticked (docs edit outside 14).
- Celery worker/beat restarted after S2 merge (2026-10-22 06:25).
