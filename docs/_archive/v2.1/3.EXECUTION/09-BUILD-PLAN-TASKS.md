# 09 — BUILD PLAN & TASKS (v2)

> Checklist task atomic để build **Aureon v2** theo 6 mốc S0–S5 (01 §10).
> Task v1 (62 task, S0–S4 cũ) đã **xóa khỏi file này**; bản gốc lưu ở nhánh git `v1`. Số `T-xxx` v2 dùng dải mới (00 §4.7) và không mang nghĩa cũ.
> Nguồn: 00–08, 10–14 v2; DEC-124 → DEC-137. Endpoint ghi theo nhóm dải EP (00 §4.6); số EP chi tiết tra ở 10.
> **Gate:** A — 12; B — 13 (§2 dưới đây); C — 14 (cột Task).

---

## 1. Tổng quan và quy ước

### 1.1. Mốc

| Mốc | Tuần | Mục tiêu | Exit criteria |
|---|---|---|---|
| **S0** | 1–2 | Nền tảng v2 | Module skeleton + schema per module migrate được; login RS256 với 10 role; outbox → Celery → consumer idempotent pass test; ModelGateway gọi được fixture + ≥ 1 provider live |
| **S1** | 3–4 | Domain F, C, O | Finance / Sales / HR / Execution CRUD + BR pass unit test; event publish/consume end-to-end |
| **S2** | 5–6 | Domain U, S + Dashboard F.O.C.U.S | Product / Risk + rủi ro tự sinh; 5 dashboard p95 < 800 ms; FE 5 trụ + drill-down ≤ 3 click |
| **S3** | 7–8 | Trợ lý AI + Autonomy | Chat SSE có `sources`, tool lọc theo role, insight, Action card L2, undo L3, kill switch |
| **S4** | 9–10 | IDP v2 | 9 doc type, C1–C5, review song song, import grid, UC-06/07/08, lineage tới metric |
| **S5** | 11–12 | UX, mobile, phát hành | Design system v2, trang chủ 10 role, PWA, seed ABC ~150 NV, E2E F1–F5, NFR đo được |

Đường găng: T-001 → T-003 → T-010 → T-020 → T-101 → T-201 → T-220 → T-301 → T-310 → T-401 → T-501 → T-540.

### 1.2. Quy ước task

| Trường | Ý nghĩa |
|---|---|
| `T-xxx` | S0 `T-001..099` · S1 `T-101..199` · S2 `T-201..299` · S3 `T-301..399` · S4 `T-401..499` · S5 `T-501..599` |
| Loại | `BE`, `FE`, `DB`, `AI`, `INFRA`, `TEST`, `DOC` |
| Spec | ID nguồn (FR / US / EP-dải / ENT / SCR / METRIC / EVT / TOOL / ACT) — dùng cho Gate C |
| Dep | Task phải xong trước |
| Size | S ≤ 0,5 ngày · M ≤ 1,5 ngày · L ≤ 3 ngày (task > 3 ngày phải tách) |

### 1.3. Definition of Done (mọi task)

- [ ] Gate A/B/C đạt trước khi bắt đầu (11 §4).
- [ ] Tôn trọng module boundary (DEC-125): không import `models`/`repositories` của module khác, không query schema khác; liên module qua service interface hoặc event.
- [ ] Endpoint khớp 10 (path, permission, envelope, mã lỗi); `response_model` khai báo.
- [ ] Migration reversible, đúng schema module; 05 cập nhật trước nếu đổi schema.
- [ ] Mutation ghi audit log; thay đổi nghiệp vụ quan trọng ghi outbox event (05 §event).
- [ ] Test mới map vào 14 (`TC-xxx`); coverage service module ≥ 80%.
- [ ] `pnpm lint && pnpm test && uv run ruff check . && uv run mypy app/ && uv run pytest` exit 0.
- [ ] Không secret trong code/log; LLM chỉ qua ModelGateway; không PII/lương gửi LLM.

---

## 2. Gate B — trạng thái quyết định

Tại 2026-10-19: **0 DEC open + blocking** ảnh hưởng v2. DEC open dải 030–113 của v1 chỉ chặn nếu chạm đúng phạm vi ghi ở cột "Ảnh hưởng" — agent kiểm 13 trước mỗi task. Dependency mới (`cryptography`, `asyncpg`, `respx`, ClamAV, …) phải có DEC resolved trước task đầu tiên dùng chúng → **T-002**.

---

## 3. Checklist task

Ký hiệu: `[ ]` chưa làm · `[~]` đang làm · `[x]` xong (kèm commit).

### S0 — Nền tảng v2 (Tuần 1–2)

| ✓ | Task | Loại | Mô tả | Spec | Dep | Size |
|---|---|---|---|---|---|---|
| [ ] | T-001 | DOC | Human promote 00–14 về `current` 2.0.0; xác nhận Gate A/B/C cho S0 | 12, 13 | — | S |
| [ ] | T-002 | DOC | Raise + resolve DEC cho dependency mới (`cryptography`, `asyncpg`, `respx`, ClamAV, `sse-starlette` nếu dùng) **+ v2.1:** parse `pypdf` (hoặc `PyPDF2`), `pillow-heif` (HEIC), `python-docx`, `openpyxl` (DEC-151); container **Ollama** + pull `bge-m3` (embed, DEC-142) và `qwen2.5:7b-instruct` (chat `CONFIDENTIAL`, DEC-157); `gitleaks` trong CI (07 OQ-08) | 07 OQ-08, OQ-13, 13 DEC-151, DEC-157 | T-001 | S |
| [ ] | T-003 | BE | Tái cấu trúc `apps/api/src/app/modules/` theo 11 module (auth, finance, sales, hr, product, risk, execution, ai_core, idp, dashboard, platform), mỗi module `routes/schemas/models/repositories/services/events` | DEC-125, 07 §4 | T-001 | M |
| [ ] | T-004 | TEST | Kiểm tra import-boundary tự động (vd `import-linter`/test pytest quét import) — cấm import chéo `models`/`repositories` | DEC-125 | T-003 | S |
| [ ] | T-005 | DB | Alembic đa schema: tạo 10 schema PG, `version_table_schema`, base model (UUID, timestamps, soft delete) | 05 §1, DEC-125 | T-003 | M |
| [ ] | T-006 | BE | `core/`: envelope `{data, meta}`, bảng mã lỗi, phân trang `limit/offset/sort_by/order`, `X-Request-Id`, idempotency-key | 10 §1, DEC-130 | T-003 | M |
| [ ] | T-007 | BE | Auth RS256: sinh cặp khóa (script, `secrets/` gitignored), ký/verify, payload `role + permissions[]`, refresh/logout | FR-AUTH-01..03, EP-01..09, DEC-129 | T-005, T-002 | M |
| [ ] | T-008 | BE | RBAC: `require_permission("<domain>:<action>")`, data scoping MANAGER/EMPLOYEE, seed 10 role + permission | 02 §ma trận, DEC-128 | T-007 | M |
| [ ] | T-009 | BE | User admin (ADMIN/CEO tạo user, gán role), đổi mật khẩu, không self-register | FR-AUTH-04..05, DEC-137 | T-008 | S |
| [ ] | T-010 | BE | Transactional Outbox: `platform.outbox_events`, helper `publish_in_tx()`, relay Celery beat | DEC-126, 05 §event | T-005 | M |
| [ ] | T-011 | BE | Consumer framework: `processed_events` idempotency, retry 5s/30s/120s, DLQ, envelope `event_id/event_type/version` | DEC-126, 10 §event | T-010 | M |
| [ ] | T-012 | BE | Audit log middleware cho mọi mutation (`platform.audit_logs`) | ENT-AuditLog | T-006 | S |
| [ ] | T-013 | AI | ModelGateway đa provider: adapter OpenAI-compatible (omniroute, openrouter, 9router, deepseek, openai) + Anthropic; `MODEL_PROVIDER_PRIMARY/FALLBACKS`; fixture mode; log `ENT-ModelCallLog` (token, chi phí) | DEC-131, 07 §ModelGateway | T-003 | L |
| [ ] | T-014 | INFRA | `.env.example` v2 (đủ biến 07 §Cấu hình, chỉ placeholder), `docker-compose.yml` (web, api, worker, beat, postgres, redis, minio, clamav, **ollama** — init pull `bge-m3`, `qwen2.5:7b-instruct`), health check; 9 biến mới 2.1 (07 §7) | 07 §Deployment, §7 | T-013, T-002 | S |
| [ ] | T-015 | FE | NextAuth với JWT RS256 từ API, middleware guard, `apiClient` bóc envelope, `types/api.ts`, next-intl VI/EN khung | DEC-129, DEC-135 | T-007 | M |
| [ ] | T-016 | DB | Script di trú dữ liệu v1 (`business_records` → bảng domain) hoặc quyết định reset seed; ghi vào 05 §migration | DEC-016 superseded | T-005 | S |
| [ ] | T-017 | TEST | CI: ruff, mypy, pytest (fixture mode), vitest, contract test khung; coverage gate; **`gitleaks detect`** chặn merge khi lộ secret | 14 §1, 07 OQ-08 | T-006, T-002 | S |
| [ ] | T-018 | BE | Trường chung C19 (`source`, `data_classification`, `version`) cho bảng nghiệp vụ + optimistic locking `PATCH` (`409 CONFLICT_STATE`); 5 cột đổi tên DEC-154 | 05 §1 C19, 10 §1.1, DEC-147, DEC-154 | T-005, T-006 | M |

### S1 — Domain F, C, O (Tuần 3–4)

| ✓ | Task | Loại | Mô tả | Spec | Dep | Size |
|---|---|---|---|---|---|---|
| [ ] | T-101 | BE | Finance: revenues, expenses, cash-positions CRUD + validate | FR-FIN-01, EP-60..69, ENT-Revenue/Expense/CashPosition | T-008, T-010 | M |
| [ ] | T-102 | BE | Finance: budgets theo phòng ban × quý; phát `EVT-finance.budget_exceeded` | FR-FIN-02, BR-FIN-*, ENT-Budget | T-101 | M |
| [ ] | T-103 | BE | Finance: forecasts 3 kịch bản + lines; `EVT-finance.forecast_updated` | FR-FIN-03..04, ENT-Forecast/ForecastLine | T-101 | M |
| [ ] | T-104 | BE | Finance: invoices + lines, `/pay`, công nợ/DSO; `EVT-finance.invoice_paid` | FR-FIN-05..06, ENT-Invoice/InvoiceLine | T-101 | M |
| [ ] | T-105 | BE | Finance: công thức burn/runway/biên LN (unit test từng BR); cảnh báo burn vượt dự báo `EVT-finance.burn_over_forecast` | BR-FIN-01..06, FR-FIN-08 | T-103 | M |
| [ ] | T-106 | BE | Finance: dòng tiền 13 tuần — EP-128 (GET + `/recompute`), tính từ invoices OUT/IN chưa thanh toán + lương tổng (service `hr`) + chi định kỳ; consumer `invoice_created`/`invoice_paid`; phát `EVT-finance.invoice_created`, `EVT-finance.cash_flow_forecast_updated` | FR-FIN-05, US-FIN-003, UC-08, ENT-CashFlowForecast/Line, DEC-148 | T-104, T-121, T-011 | M |
| [ ] | T-111 | BE | Sales: clients, deals + stage history, `/stage`; `EVT-sales.deal_closed_won/lost` | FR-SAL-01..03, EP-70..79 | T-008, T-010 | M |
| [ ] | T-112 | BE | Sales: targets, pipeline, performance, win rate, coverage, chu kỳ bán | FR-SAL-04..07, BR-SAL-01..04 | T-111 | M |
| [ ] | T-113 | BE | Sales: contracts (giá trị, hiệu lực, liên kết client) | ENT-Contract | T-111 | S |
| [ ] | T-121 | BE | HR: departments, employees, salary history (mask theo quyền, không gửi LLM) | FR-HR-01..03, EP-80..89 | T-008 | M |
| [ ] | T-122 | BE | HR: hiring plans + `/submit` + `/approve` (CFO); job phát hiện trễ > 30 ngày → `EVT-hr.hiring_plan_delayed` | FR-HR-04..05, BR-HR-01 | T-121, T-011 | M |
| [ ] | T-123 | BE | HR: turnover năm hóa, onboard/terminate events | FR-HR-06, METRIC-HR-02 | T-121 | S |
| [ ] | T-131 | BE | Execution: meetings, decisions, tasks, projects; `EVT-execution.task_overdue` | EP-42..49, ENT-Meeting/Decision/Task/Project | T-008 | M |
| [ ] | T-132 | BE | Execution: objectives, key results, check-ins, KPI + measurements; `EVT-execution.kpi_measured` | ENT-Objective/KeyResult/CheckIn/KPI/KPIMeasurement | T-131 | M |
| [ ] | T-133 | BE | Execution v2.1: Initiative + Milestone (EP-45 sub-resource), Task 7 trạng thái + `owner_id/estimate/actual/task_source`, KPI evaluation band 5 mức | EP-44, EP-45, ENT-Initiative/Milestone/Task/KPITarget, DEC-147 | T-131, T-132, T-018 | M |
| [ ] | T-141 | TEST | Integration event: budget_exceeded, hiring_plan_delayed, deal_closed_lost publish → consumer stub nhận đúng 1 lần (retry/dup) | DEC-126 | T-102, T-111, T-122 | S |
| [ ] | T-142 | FE | Workspace Finance / Sales / HR (danh sách + form, react-hook-form + zod) | SCR-22, SCR-23, SCR-24 | T-015, T-101, T-111, T-121 | L |
| [ ] | T-143 | FE | Công việc + workload heatmap; Mục tiêu OKR/KPI + check-in | SCR-19, SCR-20 | T-132 | M |

### S2 — Domain U, S + Dashboard F.O.C.U.S (Tuần 5–6)

| ✓ | Task | Loại | Mô tả | Spec | Dep | Size |
|---|---|---|---|---|---|---|
| [ ] | T-201 | BE | Product: products, features, roadmap items, releases; `EVT-product.product_launched/feature_released` | FR-PRD-01..05, EP-90..99 | T-008, T-010 | M |
| [ ] | T-202 | BE | Product: metric snapshots (append-only) + phát hiện churn bất thường `EVT-product.metric_anomaly` | FR-PRD-06..07, BR-PRD-01 | T-201 | M |
| [ ] | T-211 | BE | Risk: sổ rủi ro, score = L × I, level, assessments, accept (CEO, kèm lý do) | FR-RSK-01..03, BR-RSK-01..02, EP-100..109 | T-008 | M |
| [ ] | T-212 | BE | Risk: consumer tự sinh rủi ro từ event (`hiring_plan_delayed`, `budget_exceeded`, `deal_closed_lost`, `metric_anomaly`, `forecast_updated`) → `EVT-risk.risk_proposed` (trạng thái `proposed`, `risk_source`) | FR-RSK-04, BR-RSK-03, DEC-148 | T-211, T-011 | M |
| [ ] | T-213 | BE | Risk: mitigations, risk alerts acknowledge, heatmap | FR-RSK-05..06 | T-211 | S |
| [ ] | T-214 | BE | Risk: what-if scenario (gọi service Finance/HR/Product qua interface, không query chéo schema) | FR-RSK-07, US-CEO-06 | T-211, T-105 | M |
| [ ] | T-215 | BE | Risk v2.1: 13 danh mục, vòng đời `proposed → identified/rejected` (EP-106), RSK metric bỏ qua `proposed`, hàng chờ "Rủi ro đề xuất" | EP-101, EP-106, ENT-Risk, DEC-148 | T-212 | S |
| [ ] | T-220 | BE | Metric store: `platform.metrics/metric_values`, job tính 31 metric trụ từ service domain, ngưỡng cấu hình | METRIC-*, 03 §2 | T-105, T-112, T-123, T-132, T-202, T-211 | L |
| [ ] | T-221 | BE | Alert engine 31 alert 1-1 metric; acknowledge/dismiss; `EVT-platform.alert_raised` | ALERT-*, EP-10..19 | T-220 | M |
| [ ] | T-222 | BE | 5 endpoint dashboard trụ (`summary` + `*_trend`, status ok/warning/critical), cache 60s `Vary: Authorization` | FR-DSH-01..07, EP-10..19 | T-220 | M |
| [ ] | T-223 | BE | Lineage API: metric value → bản ghi domain → (field/trang tài liệu nếu có) | ENT-DataLineage, P01 | T-220 | M |
| [ ] | T-224 | FE | SCR-01 khung + 5 thẻ trụ tải song song, cô lập lỗi từng widget | FR-DSH-01, FR-DSH-07, SCR-01 | T-222, T-015 | M |
| [ ] | T-225 | FE | SCR-02..06 trang trụ (Recharts, bộ lọc kỳ, alert list) | SCR-02..06 | T-224 | L |
| [ ] | T-226 | FE | SCR-07 chi tiết metric + lineage popover (≤ 3 click) | SCR-07, P01 | T-223, T-225 | M |
| [ ] | T-227 | FE | SCR-21 sổ rủi ro + what-if; SCR-25 Product workspace | SCR-21, SCR-25 | T-213, T-214, T-201 | M |
| [ ] | T-228 | TEST | Perf: dashboard p95 < 800 ms, 5 trụ < 3 s với seed tối thiểu | NFR dashboard | T-222 | S |
| [ ] | T-229 | BE | METRIC-DQ-01 Data Quality Score (completeness/accuracy/freshness, `DQ_WEIGHT_*`, SLA freshness theo domain) + ALERT-DQ-01; SEI theo Initiative (METRIC-RSK-06) | 03 §2.5, §2.6, 08 §10.3, DEC-147, DEC-148 | T-220, T-133 | M |
| [ ] | T-230 | BE | Approval: `ENT-ApprovalRule/Request`, EP-123..125, khớp rule trong Action Registry, 2 người cho tài chính ≥ `APPROVAL_FINANCE_THRESHOLD_VND`, SLA + escalation, `EVT-platform.approval_requested/approval_decided`, permission `platform:approve` | FR-DSH-10, US-CEO-006, 02 §5.6, DEC-149, DEC-153, DEC-155 | T-008, T-011, T-018 | L |
| [ ] | T-231 | FE | SCR-29 Phê duyệt: hộp chờ/đã gửi/đã xử lý, chi tiết diff, duyệt/từ chối (lý do), bước 2, badge sidebar, mobile | SCR-29, EP-123..125 | T-230, T-224 | M |
| [ ] | T-232 | FE | SCR-31 Dòng tiền 13 tuần: summary, chart + bảng thay thế, giả định → recompute, stale | SCR-31, EP-128 | T-106, T-224 | M |
| [ ] | T-233 | BE | Classification override: EP-129 (`ai:admin`, lý do bắt buộc, `SECRET` → 422), `ai.classification_overrides`, audit + thông báo CEO; FE dòng "Phân loại → provider" + băng vàng SCR-15 | EP-129, 07 §6.5, 06 §4.7, DEC-157 | T-012, T-013 | S |
| [ ] | T-234 | BE | HR: mã hóa pgcrypto trường nhạy cảm (`national_id`, `bank_account`, `salary_history` số tiền) — migration `0008_pgcrypto`, `DB_ENCRYPTION_KEY`, TypeDecorator trong suốt với service; test round-trip, dump thấy ciphertext, service đọc plaintext (DEC-203) | 05 §4 hr, NĐ 13/2023, 02 §7 | T-121 | M |
| [ ] | T-235 | BE | Celery beat: `daily_burn_check` 09:00, `mark_invoices_overdue` 10:00, `detect_late_hiring` 11:00, `verify_action_outcome` mỗi giờ, `relay_outbox_events` (DEC-203) | FR-FIN-08, METRIC-FIN-05, EVT-hr.hiring_plan_delayed | T-105, T-104, T-122 | S |
| [ ] | T-236 | SEED | Seed Sales/HR công ty ABC (client, deal đủ giai đoạn, target Q4; phòng ban, nhân sự, kế hoạch tuyển trễ, lịch sử lương mã hóa) (DEC-203) | 08 §3, §5 | T-111, T-121, T-234 | M |

### S3 — Trợ lý AI + Autonomy (Tuần 7–8)

| ✓ | Task | Loại | Mô tả | Spec | Dep | Size |
|---|---|---|---|---|---|---|
| [ ] | T-301 | AI | Tool Registry: khai báo `TOOL-*` (endpoint, permission, `risk_level`, autonomy mặc định, metadata `schema/data_scope/classification/reversible/cost_estimate` — 10 §7.4); lọc theo role trước khi gửi model | 10 §Tool Registry, P06 | T-013, T-222 | M |
| [ ] | T-302 | AI | Tool executor: gọi tool song song bằng JWT người hỏi, ≤ 8 call, 5 s/call, 30 s/lượt, trả `truncated` | DEC-131, FR-AI-02 | T-301 | M |
| [ ] | T-303 | AI | PII filter trước khi gửi LLM (lương, ngày sinh, địa chỉ, SĐT, email); prompt injection guard (delimiter, data ≠ lệnh) | FR-AI-10, 07 §Bảo mật | T-302 | M |
| [ ] | T-304 | BE | `POST /ai/chat` + SSE stream (`start/thinking/tool_call/tool_result/token/done/error`), `sources`, P05 không bịa số | FR-AI-01..04, EP-110..119 | T-302, T-303 | L |
| [ ] | T-305 | BE | Conversations, messages, feedback 👍/👎; rate limit 20 req/phút/người | FR-AI-05..06, ENT-Conversation/Message/Feedback | T-304 | S |
| [ ] | T-306 | AI | Insight chủ động: consumer mọi event → làm mới `ENT-Insight` (Observation → Evidence → Impact → Recommendation → Confidence); Briefing theo role | FR-AI-07, 03 §insight | T-304, T-221 | M |
| [ ] | T-307 | AI | What-if runway "không có doanh thu mới" qua tool Finance | FR-AI-09, US-CEO-04 | T-304, T-105 | S |
| [ ] | T-310 | BE | AutonomyPolicy (tool × role × ngưỡng giá trị → L0–L3), `ENT-AIAction`, undo L3 trong 24 h, kill switch (L3 → L2, chặn WRITE) | DEC-134, 04 §autonomy, ENT-AutonomyPolicy | T-301 | M |
| [ ] | T-311 | AI | Ngân sách AI: đếm chi phí theo `ModelCallLog`, cảnh báo 80%, chặn 100% (fallback rẻ hơn hoặc từ chối có thông báo) | DEC-131, NFR AI cost | T-013 | S |
| [ ] | T-312 | TEST | Bộ AI evaluation (golden set câu hỏi CEO/CFO, kiểm `sources`, không vượt quyền, không bịa số) chạy fixture + live tùy chọn | 07 §AI eval | T-304 | M |
| [ ] | T-313 | AI | 8 tool v2.1 (10 §7.3: `assign_task`, `get_kpi_status`, `get_cash_flow_forecast`, `send_notification`, `generate_report`, `request_approval`, `approve_request`, `reject_request`) — lớp APPROVAL không bao giờ gửi model; `ENT-AIAgentProfile` + kill switch theo agent (EP-118 `agents`) | 10 §7.3, 02 §7.3, DEC-149, DEC-150 | T-301, T-310, T-230, T-106 | M |
| [ ] | T-314 | AI | Định tuyến provider theo `data_classification` (07 §6.5): `INTERNAL` cloud · `CONFIDENTIAL` Ollama `LOCAL_CHAT_MODEL` → template · `SECRET` không LLM; đọc override EP-129; fail fast `MODEL_PROVIDER_SECRET`, Σ `DQ_WEIGHT_*` | 07 §6.5, 03 §7.4, DEC-149, DEC-157 | T-013, T-303, T-233 | M |
| [ ] | T-315 | AI | `verify_action_outcome`: job beat kiểm kết quả AIAction L2+ ở mốc 24h / 7d, quét bù khi worker restart, không gọi LLM, `not_met` → notification | 03 §7.3, 07 §5.6, ENT-AIAction | T-310, T-011 | S |
| [ ] | T-316 | BE | Report: EP-120..122, worker sinh PDF + XLSX (`kind` WEEKLY/MONTHLY, mẫu `BOARD`), lọc scope người yêu cầu, MinIO + presigned, job định kỳ, `EVT-platform.report_generated` | FR-DSH-09, US-RPT-001/002/005, DEC-153 | T-220, T-011, T-002 | M |
| [ ] | T-317 | AI | Grounding insight 9 phần + gỡ số không khớp `SourceRef`; từ chối chấm điểm / quyết định nhân sự (chỉ trả bằng chứng) | 03 §7.1, 02 §7.4, FR-AI-04, DEC-149 | T-306 | S |
| [ ] | T-320 | FE | Thanh AI ⌘K toàn cục + Panel ngữ cảnh (biết màn hình/đối tượng đang xem) | SCR-16, 06 §AI components | T-304 | L |
| [ ] | T-321 | FE | Trang Chat: streaming, trạng thái "đang tra cứu" theo bước thật, source chip, feedback | SCR-16 | T-320 | M |
| [ ] | T-322 | FE | Insight card L0, Suggestion chip L1, Action card L2, Undo toast 10 s + feed "AI đã làm" L3, kill-switch banner | SCR-17, 06 §autonomy UI | T-310, T-320 | M |
| [ ] | T-323 | FE | AI Control Center: autonomy matrix, kill switch, ngân sách, trạng thái provider | SCR-15 | T-310, T-311 | M |
| [ ] | T-324 | FE | SCR-30 Báo cáo: chọn mẫu/kỳ/phạm vi/định dạng, lịch sử + trạng thái + tải; ẩn với ROLE-09 | SCR-30, EP-120..122 | T-316, T-224 | M |

### S4 — IDP v2 (Tuần 9–10)

| ✓ | Task | Loại | Mô tả | Spec | Dep | Size |
|---|---|---|---|---|---|---|
| [ ] | T-401 | BE | Chuyển module IDP v1 vào schema `idp`; DocumentType / ExtractionSchema / ValidationRule cấu hình được | 04 §5, ENT-DocumentType/ExtractionSchema/ValidationRule | T-005 | M |
| [ ] | T-402 | AI | Pipeline Celery: ingest → malware scan (ClamAV) → hash dedupe → text-layer → OCR → phân loại → tách/gộp → trích xuất → chuẩn hóa VN → validate | FR-DC-07..14 (mã BRD — DEC-146) | T-401, T-013, T-002 | L |
| [ ] | T-403 | AI | Extraction schema 9 doc type (thêm `PRODUCT_REPORT`, `RISK_REGISTER`), field `{value, confidence, source_location}`, `null` khi không thấy | 04 §5 | T-402 | L |
| [ ] | T-404 | BE | Confidence 3 mức (≥ 0,90 / 0,60–< 0,90 / < 0,60), STP routing, trường trọng yếu luôn review | DEC-133, 04 §7 | T-403 | S |
| [ ] | T-405 | BE | Action Registry v2: `ACT-*` ghi vào service domain mới (finance/sales/hr/product/risk/execution), idempotent, undo 7 ngày, `EVT-idp.document_committed/rolled_back` | 04 §10, DEC-134 | T-404, S1, S2 | L |
| [ ] | T-406 | BE | Lineage: `ENT-DataLineage` field → bản ghi domain → metric value | 05 §lineage, P01 | T-405, T-223 | M |
| [ ] | T-407 | BE | C1 form, C2 nhập bằng lời (LLM → bản nháp có cấu trúc), C5 import Excel + map cột + preview | FR-DC (C1/C2/C5), EP-20..41 | T-405 | M |
| [ ] | T-408 | BE | UC-06 biên bản họp → decisions + tasks; UC-08 hóa đơn → cảnh báo dòng tiền; UC-07 batch | UC-06, UC-07, UC-08 | T-405, T-131 | M |
| [ ] | T-410 | FE | Hộp thư dữ liệu + drop zone toàn cục (thả file ở bất kỳ màn hình) | SCR-08, SCR-09 | T-402 | M |
| [ ] | T-411 | FE | Review song song: tài liệu trái / field phải, highlight vùng nguồn, phím tắt, confidence badge 3 mức | SCR-10 | T-404 | L |
| [ ] | T-412 | FE | Import grid C5; Nạp doanh nghiệp UC-07; Họp → việc UC-06 | SCR-11, SCR-12, SCR-18 | T-407, T-408 | M |
| [ ] | T-413 | FE | Cấu hình loại tài liệu / schema / ngưỡng (ADMIN) | SCR-27 | T-401 | S |
| [ ] | T-414 | TEST | Accuracy harness với ground truth 9 tài liệu (08): field accuracy ≥ 90%, error leakage trường trọng yếu = 0 trên bộ mẫu | 04 §KPI, 08 | T-403 | M |
| [ ] | T-415 | BE | IDP DEC-151: `SUPERSEDED`, `type_preselected`, `correction_reason` cho field tiền, field `checkbox/signature/stamp`, "chấp nhận tất cả HIGH", `ENT-ReviewAssignment` + SLA escalation (`EVT-idp.review_escalated`), EP-126 reassign, EP-127 merge; dữ liệu sức khỏe → `SECRET` | 04 §8.3, §14.3, FR-DC-19..22, DEC-151 | T-404, T-405 | L |
| [ ] | T-416 | BE | C2 voice mock STT (WAV mẫu + fixture `stt`) và upload transcript họp SCR-18 (consent bắt buộc, `ENT-MeetingTranscript`) | FR-DC-03, UC-02, DEC-050, DEC-153 | T-407, T-408 | M |

### S5 — UX, mobile, demo, phát hành (Tuần 11–12)

| ✓ | Task | Loại | Mô tả | Spec | Dep | Size |
|---|---|---|---|---|---|---|
| [ ] | T-501 | FE | Design system v2: token (primary / ai / semantic / neutral / stale), sáng-tối, 2 mật độ, Be Vietnam Pro, tabular nums | 06 §Design system | T-015 | M |
| [ ] | T-502 | FE | Trang chủ theo 10 role (CEO briefing, Manager, Employee, Reviewer, Admin, …) | SCR-01, 02 §persona | T-306, T-501 | L |
| [ ] | T-503 | FE | PWA mobile 4 việc: Briefing, hỏi AI, chụp/gửi chứng từ (C4), duyệt | SCR-28 | T-502, T-410 | M |
| [ ] | T-504 | FE | Audit log + quản trị user/role | SCR-14, SCR-26 | T-012, T-009 | S |
| [ ] | T-505 | FE | i18n đủ VI/EN, định dạng VN (tiền, ngày, số), không hard-code chuỗi | DEC-135, P04 | T-501 | S |
| [ ] | T-506 | FE | Accessibility WCAG 2.1 AA (focus, contrast, trạng thái không chỉ bằng màu) | 06 §a11y | T-501 | S |
| [ ] | T-510 | DB | Seed ABC ~150 NV: 10 tài khoản demo (mật khẩu qua env), dữ liệu 6 kỳ cho 31 metric, rủi ro, sản phẩm | 08, DEC-136 | T-220, T-211, T-201 | L |
| [ ] | T-511 | DB | 9 tài liệu mẫu (PDF/DOCX/XLSX/ảnh) khớp ground truth 08 + quy tắc XD | 08 §tài liệu | T-510 | M |
| [ ] | T-512 | BE | Chuyển vai trò demo (`DEMO_MODE`) cho 10 role | 02 §demo | T-008 | S |
| [ ] | T-513 | DB | Seed v2.1 (08 §10): 5 Initiative / 13 Milestone / 15 Task, 3 rủi ro `proposed`, DQ 6 domain, dòng tiền 13 tuần × 3 kịch bản, 4 rule / 8 approval request, 5 report | 08 §10, DEC-147, DEC-148, DEC-153 | T-510, T-106, T-133, T-229, T-230, T-316 | M |
| [ ] | T-520 | TEST | E2E Playwright F1–F5 + câu chuyện demo 20 phút (01 §11) | 06 §F1–F5 | T-502, T-411, T-322 | L |
| [ ] | T-521 | TEST | Đo NFR: dashboard p95, AI first token ≤ 5 s, IDP p95 ≤ 60 s (≤ 5 trang), thông lượng | 07 §NFR | T-520 | M |
| [ ] | T-522 | TEST | Bảo mật: test vượt quyền 10 role × domain, PII không ra LLM (assert payload), prompt injection fixture | 02, 07 §Bảo mật | T-303, T-008 | M |
| [ ] | T-530 | DOC | Đồng bộ 14 (status TC, coverage), 00 §8 trạng thái, 12 audit | 12, 14 | T-520 | S |
| [ ] | T-540 | INFRA | Release: `docker compose up --wait` sạch từ zero, seed, checklist demo, tag `v2.0.0` | 07 §Deployment | T-530 | S |

---

## 4. Ma trận coverage spec → task (Gate C)

| Nhóm spec | Task chính |
|---|---|
| FR-AUTH-01..05, ROLE-01..10 | T-007, T-008, T-009, T-512 |
| FR-FIN-01..08, BR-FIN-01..06, METRIC/ALERT-FIN-01..07 | T-101..T-106, T-220, T-221 |
| FR-SAL-01..07, BR-SAL-01..04, METRIC/ALERT-CUS-01..06 | T-111..T-113, T-220 |
| FR-HR-01..07, BR-HR-01, METRIC/ALERT-HR-01..04 | T-121..T-123, T-220 |
| METRIC/ALERT-OPS-01..03, Execution, Initiative | T-131..T-133, T-220 |
| FR-PRD-01..07, BR-PRD-01, METRIC/ALERT-PRD-01..05 | T-201, T-202, T-220 |
| FR-RSK-01..07, BR-RSK-01..03, METRIC/ALERT-RSK-01..06 | T-211..T-215, T-220, T-229 |
| METRIC/ALERT-DQ-01 | T-229 |
| FR-DSH-01..08 | T-222, T-224..T-226 |
| FR-DSH-09 (Report), FR-DSH-10 (Approval) | T-316, T-324, T-230, T-231 |
| FR-AI-01..10, TOOL-* (43) | T-301..T-307, T-312..T-317, T-320, T-321 |
| Autonomy L0–L3, kill switch (per-agent), classification override | T-310, T-313, T-322, T-323, T-233 |
| FR-DC-01..23, FR-DC-101..102, US-DC-001..011, ACT-* | T-401..T-416 |
| UC-02 / UC-06 / UC-07 / UC-08 | T-408, T-412, T-416, T-106 |
| EVT-* (00 §4.5, 28) | T-010, T-011, T-141, T-212, T-306, T-405; v2.1: T-106, T-215, T-230, T-316, T-415 |
| SCR-01..31 | T-231, T-232, T-324, T-142, T-143, T-224..T-227, T-320..T-323, T-410..T-413, T-502..T-504 |
| ENT-* (00 §4.3, 79) | T-005, T-018 + task domain tương ứng |
| EP-120..129 | T-316 (120..122), T-230 (123..125), T-415 (126, 127), T-106 (128), T-233 (129) |
| NFR | T-228, T-311, T-312, T-521, T-522 |

Ánh xạ chi tiết từng ID → TC ở `14-TEST-TRACEABILITY.md` §3. 36 TC Planned của Phase 3a–3c (14 §2.1.1–§2.1.3) đã gán task ở Phase 3d.

---

## 5. Rủi ro build

| # | Rủi ro | Giảm thiểu |
|---|---|---|
| R1 | Tái cấu trúc module phá code v1 đang chạy | Làm trên nhánh `v2/s0`; v1 giữ ở nhánh `v1`; T-004 chặn import chéo sớm |
| R2 | Event idempotency sai → dữ liệu trùng | T-011 test retry/dup bắt buộc trước S1 |
| R3 | Provider LLM 429/quota | Fallback chain DEC-131; fixture mode cho CI |
| R4 | AI vượt quyền / lộ PII | T-303, T-522 là blocking cho S3 exit |
| R5 | Phạm vi S1–S2 rộng (6 domain) | Ưu tiên Must; Could (FR-HR-07, FR-NTF-02) dời S5 hoặc Phase 2 |
| R6 | Dữ liệu demo không nhất quán giữa 9 tài liệu | Sinh số bằng script (DEC-022), test XD ở T-511 |

---

## 6. Open questions

| # | Câu hỏi | Đề xuất |
|---|---|---|
| OQ-01 | Có di trú dữ liệu v1 hay reset seed toàn bộ ở v2 (T-016)? | Reset seed — dữ liệu v1 chỉ là demo |
| OQ-02 | Code v2 phát triển trực tiếp trên `main` hay nhánh `v2/*` rồi merge? | Nhánh `v2/sN` theo mốc, PR vào `main` |
| OQ-03 | Có cần công cụ `import-linter` (dependency mới) cho T-004 hay test pytest tự viết là đủ? | Test pytest tự viết — tránh dependency mới |
| OQ-04 | 18 task mới v2.1 (Phase 3d) dồn vào S1–S4 làm mỗi mốc tăng 3–5 task (S2 +6) | Giữ 6 mốc; nếu trễ, dời T-324 (SCR-30) và T-316 phần `BOARD` sang S5 — Report là Must tối thiểu (DEC-153) |
| OQ-05 | Máy demo không đủ RAM cho `qwen2.5:7b-instruct` (~5 GB) | ADMIN override `CONFIDENTIAL` → cloud qua EP-129 (DEC-157), ghi audit |

---

## 7. Version

- **Version:** 2.1.0
- **Status:** current
- **Last updated:** 2026-10-21
- **Applies to:** Aureon v2 (v2.0 demo-ready / v2.1 production-ready)
- **Maintainer:** @CyEyes
- **Change:** Xóa 62 task v1; thay bằng checklist v2 S0–S5 (DEC-124..137).
- **Change 2.1.0 (Phase 3d — DEC-146..157):** +18 task: T-018 (C19 + optimistic locking), T-106 (dòng tiền 13 tuần EP-128), T-133 (Initiative/Task 7 trạng thái/KPI band), T-215 (risk `proposed`), T-229 (DQ Score + SEI), T-230/T-231 (Approval EP-123..125 + SCR-29), T-232 (SCR-31), T-233 (classification override EP-129), T-313 (8 tool v2.1 + agent profile), T-314 (định tuyến provider theo phân loại), T-315 (`verify_action_outcome`), T-316/T-324 (Report EP-120..122 + SCR-30), T-317 (grounding + từ chối HR), T-415 (IDP DEC-151, EP-126/127), T-416 (voice mock + transcript), T-513 (seed v2.1); T-002 thêm parse libs + Ollama + gitleaks; T-014 Ollama; T-017 gitleaks; FR-DC mã BRD; coverage SCR-01..31, EP-120..129; OQ-04, OQ-05.
