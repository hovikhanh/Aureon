# STATE — Aureon v2.1 auto-pilot

| Field | Value |
|---|---|
| Last updated | 2026-10-22 12:55 (Asia/Saigon) |
| Last commit | `b954f47` test(ai): PII filter tests (T-309) on `main` |
| Sub-sprint | **S3 — AI Core DONE** (T-301→T-310 all complete + verified) |
| Test count | 667 passed, 2 deselected (`-m "not live"`) |
| Coverage | ai module **95%** (S3 exit gate); overall ≥ 95% (`--cov=app`) |
| Gates | A ✅ · B ✅ (0 DEC open+blocking) · C ✅ (TC-AI-001..018 Passed) |
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
- **DEC-230 APPROVED** (human 2026-10-22): F🟢 C🟢 U🟡 O🟡 S🔴 is the official demo layout; DEC-143/152 "demo layout" superseded_by DEC-230 (thresholds unchanged, NFR-19).
- **DEC-231 APPROVED**: alert severity enum = WARNING|CRITICAL only (INFO = log level). "≥10 alerts" = ≥10 alerts **any severity** (met 11W + 2C = 13).
- Gate: ruff ✅ · mypy ✅ (226 files) · pytest 585 ✅.

## S3 AI Core (done 2026-10-22, direct route; 10 commits incl. DEC governance)
- **DEC-230/231 governance** `ad5c598` — demo layout + alert-severity enum approved (gate prelude).
- **T-301** `1212181` Tool Registry: 43 `TOOL-*` with §7.4 metadata (27 QUERY + 13 WRITE + 2 APPROVAL + 1 EXECUTION), `advertisable_for`/`available_for` permission + classification filters.
- **T-302** `9413b9e` Chat orchestration EP-110 + SSE EP-111 (`start→thinking|tool_call→tool_result→token→done`, `X-Accel-Buffering: no`); tool-calling loop (≤ 8 calls, budget warning); prompt_guard classification routing (salary→SECRET no-LLM, PII→CONFIDENTIAL local-only); `<<<DATA … DATA>>>` injection guard.
- **T-303** `c0bf68c` Proactive insights: 9-part grounded `ENT-Insight` from worst-status metric, evidence-gated (≥1 SourceRef), EP-114 list/dismiss with pillar-scope hiding.
- **T-304/305/306** `db9447c` AI action lifecycle (`ENT-AIAction`: propose→L3 auto-exec | L2 confirm card; undo 24h via `TaskService.delete`), Action Registry single write gate, 2-sided approval (finance ≥500M → CEO step1 + CFO step2, distinct approvers), kill switch per-agent/global WRITE_OFF|L0 (L3→L2). Cross-module via `core/approval_hooks.py` (breaks platform↔ai cycle, DEC-125).
- **T-307** `63ecc31` Outcome verification 24h/7d: scores metric status movement (improved/worsened/unchanged/not_measurable) vs baseline captured at propose time, reading current status via platform `MetricQueryService`.
- **T-308** `6a413d4` Cost & usage EP-119 `/ai/usage` (`ai:admin`): aggregates `ENT-ModelCallLog` → budget/used/used_pct + per-key rows (calls/tokens/cost/error_rate/p95_ms) grouped provider|model|task_kind|user; warn 80% / over 100% vs `AI_MONTHLY_BUDGET_USD` (DEC-131).
- **T-309** `ea9866e`+`b954f47` PII filter: `scrub_for_model` drops level-4 PII, tokenises level-3 contacts to stable `EMP-`/`CLI-` codes before every model call (5.5, FR-AI-10).
- **T-310** `0e4d8aa` E2E + coverage: HTTP sweep of EP-110..119 via overridable `get_chat_gateway` dep + service edge branches → **ai coverage 95%** (S3 exit met).
- **Gate:** ruff ✅ · format ✅ · mypy ✅ (242 files) · pytest **667 passed**.

## S3 exit criteria
| Criterion | Result |
|---|---|
| Chat SSE EP-110/111 event order | ✅ |
| Tool Registry 43 tools, permission-filtered | ✅ |
| 9-part grounded insight, no fabricated numbers | ✅ (evidence-gated) |
| Autonomy L0–L3 + undo 24h + kill switch | ✅ |
| 2-sided approval ≥500M (CEO→CFO) | ✅ |
| PII scrub + classification routing | ✅ |
| Cost log + EP-119 usage | ✅ |
| ai coverage ≥ 95%, gates A/B/C | ✅ 95% |

## In progress
- none

## Remaining (in order)
1. S4 IDP v2.1 (T-4xx).
3. S5 FE/UX/Release (Next.js login → dashboard → upload → review); S2 FE tasks T-224..227, T-231/232, T-142/143 still open.
4. `[DEFERRED to S5]` T-223 lineage drill-down (DEC-229).
5. `[DONE in S3]` T-230 approval — built as 2-sided ApprovalService + EP-125 hook (`db9447c`).
6. `[DEFERRED to S5]` T-233 + FE S2 tasks T-224..227, T-231, T-232, T-142/143 (DEC-229).
7. `[DONE]` T-237 seed rebalance 2 green / 2 yellow / 1 red + CPO/RISK_MANAGER users.

## Next task
S4 — read 09 S4 section (T-4xx IDP v2.1), gates A/B/C for IDP (load 00, 01, 04, 05, 10), then start the first S4 task.

## S3 notes / findings
- EP-125 approval executes the AI action with the **approver's** Principal as actor (04 §10.4). A finance approver (CFO, department-scoped for execution) cannot create a cross-department task — the on-behalf-of requester's authority is not reconstructed. Covered at service level by passing a full-scope actor; worth a DEC if finance approvals must create execution writes in prod. Non-blocking for S3.
- `get_chat_gateway` FastAPI dependency added so chat/stream routes are testable without a provider (`app.dependency_overrides`).

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
