# STATE — Aureon v2.1 auto-pilot

| Field | Value |
|---|---|
| Last updated | 2026-10-22 14:05 (Asia/Saigon) |
| Last commit | `17d26f4` test(idp): S4a pipeline tests + traceability on `main` |
| Sub-sprint | **S4a — IDP pipeline core DONE** (upload + scan → OCR → extract → validate → route); S4b/S4c/S4d pending |
| Test count | 710 passed, 2 deselected (`-m "not live"`) |
| Coverage | `modules/idp/services` **96%** (S4a exit ≥ 90%); ai 95%; overall ≥ 95% |
| Gates | A ✅ · B ✅ (0 DEC open+blocking) · C ✅ (TC-IDP-001/002/003/005/006/012 + EP-20 Passed) |
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

## S4a IDP pipeline core (done 2026-10-22, direct route; 3 commits)
- **T-401** `0ee6214` EP-20 `POST /idp/documents` (1..100 file, 50MB/file, MIME whitelist + magic bytes, stream chunk 1MB), sha256 dedupe → `DUPLICATE` linked to original, `ImportBatch` for multi-file, `ExtractionJob` QUEUED, audit `idp.upload`. New `core/storage.py` (local-FS `ObjectStore`, `quarantine` bucket — prod swaps MinIO/S3 same interface). `schema_registry.py` seeds DocumentType/ExtractionSchema/ValidationRule (INVOICE 04 §5.5 + OTHER) idempotently. `query_service.py` EP-25/26 + dept scoping. Config: `IDP_STORAGE_DIR`, `IDP_MAX_FILE_SIZE_MB/PAGES/FILES`, `OCR_PROVIDER`.
- **T-402..T-405** `cddb33e` pipeline core:
  - malware_scan (T-402): clamd TCP + EICAR local detect; INFECTED→`FAILED` `status_reason=MALWARE` + `quarantine` bucket; `CLAMAV_REQUIRED=false`→`SKIPPED` (DEC-138).
  - preprocess (T-403): text-layer check before OCR; PDF(pypdf)/DOCX/XLSX/CSV/image; `DocumentPage` per page; `OCR_PROVIDER` stub|paddle (paddle lazy-imported, DEC-049).
  - extractor (T-404): ModelGateway `task=extract`, classification by sensitivity (4→SECRET no-LLM, 3→CONFIDENTIAL local, ≤2→cloud), schema-driven prompt, field result `{value, confidence, source_location, confidence_band}`, bands HIGH≥0.90/MEDIUM 0.60/LOW (DEC-133), null not fabricated (P05). Gateway injected (DI, DEC-233).
  - validator (T-405): ValidationRule ops required/gt/lte/in/`date_not_future`/`sum_equals`; VN number/date parsing; errors → `ExtractionJob.xd_results.validation_errors`.
  - pipeline orchestrator: `UPLOADED→PREPROCESSING→CLASSIFYING→EXTRACTING→VALIDATING→NEEDS_REVIEW|AUTO_APPROVED` (MALWARE→FAILED). STP routing (04 §7.3): doc conf ≥0.95 + required fields ≥0.90 + no critical field + no validation error, else REVIEW. Keyword classifier picks INVOICE vs OTHER (full 9-type LLM classify = later sub-sprint). Celery `app.idp.process_document` (idempotent, time_limit).
- **Tests** `17d26f4`: 43 new (`tests/unit/test_idp_*.py` + `tests/integration/idp/`); `sample_docs.py` builds in-memory PDF(text+scan)/DOCX/XLSX/EICAR/PNG from runtime deps only (no reportlab).
- **Gate:** ruff ✅ · format ✅ · mypy ✅ (254 files) · pytest **710 passed**.

## S4a exit criteria
| Criterion | Result |
|---|---|
| EP-20 upload C1/C3/C4 → job created | ✅ |
| malware blocks EICAR (quarantine) | ✅ |
| OCR/text extract (PDF text + scan + DOCX/XLSX) | ✅ |
| LLM extract field results + confidence bands | ✅ |
| validation rejects invalid (neg amount, future date, bad sum) | ✅ |
| pipeline upload→scan→OCR→extract→validate → `NEEDS_REVIEW` | ✅ |
| coverage `modules/idp/services` ≥ 90% | ✅ 96% |
| gates A/B/C | ✅ |

### End-to-end sample (invoice.pdf, in-process pipeline)
upload → `UPLOADED` + QUEUED job → scan `SKIPPED/CLEAN` → text-layer extracted (1 page, pypdf) → classify `INVOICE` (0.99) → extract 8 fields (subtotal/vat/total HIGH, critical) → validate (VR-INV-02/03/SUB/05 pass) → route `REVIEW` (reason `CRITICAL_FIELD`) → **`NEEDS_REVIEW`**.

## In progress
- none

## Remaining (in order)
1. **S4b** — IDP review workflow (EP-29..35 open/fields/approve/reject/release, soft-lock 15min, parallel review, reassign/merge T-415). **Do NOT start without a new RESUME brief.**
2. **S4c** — commit + lineage + Action Registry v2 (ACT-* write to domain services, undo 7d, `EVT-idp.document_committed/rolled_back`, `ENT-DataLineage` field→record→metric, TC-IDP-007/008/009/020).
3. **S4d** (optional) — C2 voice/transcript (T-416), C5 Excel import (T-407), UC-06/07/08 (T-408), full 9-type LLM classification + accuracy harness (T-403/T-414).
4. S5 FE/UX/Release; S2 FE tasks T-224..227, T-231/232, T-142/143 still open.
5. `[DEFERRED to S5]` T-223 lineage drill-down, T-233 + FE S2 (DEC-229).

## Next task
**S4b review workflow** — on next RESUME: read 09 §S4 (T-411/T-415), 04 §8 (review state machine, soft-lock, parallel review), 10 EP-29..35, gates A/B/C. Build review open/fields/approve/reject/release on top of the S4a documents sitting in `NEEDS_REVIEW`.

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
- METRIC-DQ-01 accuracy = validation proxy; IDP-correction component comes with S4c (commit/lineage).
- 09 task checkboxes not ticked (docs edit outside 14).

## S4a notes / deferred (for S4b/S4c)
- **EP path:** spec 10 §3.3 canonical is `POST /idp/documents` (brief said `/idp/documents/upload`); followed the spec. `channel` defaults to C3 (file); C1 manual form = EP-21, C2 = EP-22, C5 = EP-23 (not built in S4a).
- **Storage:** `core/storage.py` is a **local-filesystem** demo store (`var/idp-storage/`, gitignored) behind an `ObjectStore` Protocol — prod swaps MinIO/S3 without touching callers. No MinIO client dependency added (none in config; non-blocking demo infra).
- **OCR:** `OCR_PROVIDER=stub` default (deterministic empty text + 0.0 conf for image/scan pages) so CI needs no PaddleOCR. `paddle` path is lazy-imported and only runs if the package is present (DEC-049 fixture/replay demo still `open`, non-blocking). Scan-PDF/image → `ocr_used=True, text_layer_exists=False`.
- **Classification:** S4a uses a keyword classifier (INVOICE vs OTHER) to pick the schema. Full LLM 9-type classification + accuracy harness (TC-IDP-004/013) is S4d.
- **Schema catalog:** only INVOICE (full 8 fields + 4 VR) and OTHER seeded. Remaining 7 doc-type schemas + ADMIN CRUD (TC-IDP-001 full, T-413) deferred.
- **Extractor DI:** `Pipeline(db, gateway)` / `Extractor(gateway)` take an injected gateway (like chat, DEC-233) → testable with a fake returning `ChatResponse.data`; prod uses `pipeline_gateway(db)` = `AiService(db).gateway()`.
- **mypy:** added `[[tool.mypy.overrides]]` for `clamd`/`openpyxl`/`paddleocr` (no stubs; approved deps DEC-138/DEC-120).
- **Status mapping:** brief's `READY_FOR_REVIEW` = real enum `NEEDS_REVIEW` (05 §6 `document_status`). STP path → `AUTO_APPROVED` (commit itself is S4c).
- Celery worker/beat restarted after S2 merge (2026-10-22 06:25).
