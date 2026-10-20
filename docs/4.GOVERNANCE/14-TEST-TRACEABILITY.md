# 14 — TEST TRACEABILITY (v2)

> Ma trận truy vết **spec ↔ task ↔ test** của **Aureon v2**, nguồn cho Gate C. Danh mục test v1 (TC theo 62 task cũ) đã được **reset** theo DEC-124; bản cũ lưu ở nhánh git `v1`. Cột **Task** lấy từ `09-BUILD-PLAN-TASKS.md` v2 (S0–S5).
> Nguồn: 00 (ID registry), 02–08, 10 (EP/TOOL/EVT), 11 (Gate C).
> Ba mục đầu (T-DOC-REVIEWER-001, T-GEN-SPEC-001, T-CLAUDE-GOV-001) là test tài liệu/tooling — **giữ nguyên**.

## Custom Agent Documentation Review

| Test ID | Scope | Validation | Status |
|---|---|---|---|
| T-DOC-REVIEWER-001 | `.claude/agents/doc-reviewer.md` | Kiểm tra YAML frontmatter hợp lệ, agent chỉ có quyền đọc (`Read`, `Grep`, `Glob`), và output contract gồm đủ 5 section: Summary, Cross-Reference Audit, Missing Edge Cases, Gate Checks (Gate A/B/C), Recommendation | Passed |

**Recorded:** 2026-10-17  
**Approval:** User-approved creation after Gate B/Gate C review.

## Custom Slash Command — Specification Generation

| Test ID | Scope | Validation | Status |
|---|---|---|---|
| T-GEN-SPEC-001 | `.claude/commands/gen-spec.md` | Kiểm tra command nhận `$ARGUMENTS`, yêu cầu đọc context/spec, kiểm tra Gate A/B/C, sinh tài liệu đúng đường dẫn và gọi subagent `doc-reviewer` audit | Passed |

**Recorded:** 2026-10-17  
**Approval:** User-requested creation.

## Documentation Generation & Governance Rules

| Test ID | Scope | Validation | Status |
|---|---|---|---|
| T-CLAUDE-GOV-001 | `CLAUDE.md` | Kiểm tra dependency tree gồm 4 phase, Gate A/B/C, quy tắc format tiếng Việt kỹ thuật và điều kiện không chuyển phase khi chưa verified | Passed |

**Recorded:** 2026-10-17  
**Approval:** User-approved update.

---

## 1. Quy ước

### 1.1. ID test case

| Thành phần | Quy ước | Ví dụ |
|---|---|---|
| Dạng | `TC-<NHÓM>-<nnn>` (3 chữ số) | `TC-RSK-003` |
| Nhóm | `SYS` (hạ tầng, module boundary), `AUTH` (auth, RBAC, scoping), `EVT` (outbox, consumer), `FIN`, `SAL`, `HR`, `EXE` (execution), `PRD`, `RSK`, `DASH` (metric, alert, dashboard, lineage), `AI` (gateway, tool, chat, autonomy), `IDP`, `UI`, `DATA` (migration, seed), `NFR`, `SEC` | |
| Test tài liệu/tooling | Giữ dạng `T-<TÊN>-nnn` (ba mục đầu file) | `T-GEN-SPEC-001` |
| Không tái sử dụng | ID đã cấp không đổi nghĩa; test bỏ → `Deprecated`, không xóa dòng | |

### 1.2. Loại test & tool

| Loại | Mục đích | Tool | Vị trí |
|---|---|---|---|
| unit | Công thức BR/metric, chuẩn hóa VN, rule XD, routing, PII filter | pytest + pytest-asyncio; Vitest | `apps/api/tests/unit/<module>/`, `apps/web/src/**/*.test.ts(x)` |
| integration | Endpoint + PostgreSQL (đa schema) + Redis/Celery eager + MinIO | pytest + `httpx.AsyncClient` | `apps/api/tests/integration/<module>/` |
| contract | Response khớp 10 (envelope, phân trang `limit/offset`, mã lỗi, không lộ field nhạy cảm); SSE event types | pytest (OpenAPI ↔ spec) | `apps/api/tests/contract/` |
| event | Publish qua outbox, consume idempotent, retry, DLQ | pytest + Celery eager | `apps/api/tests/events/` |
| architecture | Không import chéo `models`/`repositories`, không query schema khác | pytest quét import (09 OQ-03) | `apps/api/tests/architecture/` |
| ai-eval | Golden set câu hỏi: có `sources`, không bịa số, không vượt quyền | pytest, `MODEL_GATEWAY_MODE=fixture` (live tùy chọn) | `apps/api/tests/ai_eval/` |
| e2e | Luồng F1–F5 + câu chuyện demo | Playwright | `apps/web/e2e/` |
| perf | NFR thời gian | Playwright trace + pytest benchmark / k6 tùy chọn | `apps/web/e2e/kpi/`, `apps/api/tests/perf/` |
| manual | SUS, usability, onboarding | Phiếu + bấm giờ | biên bản trong `docs/` |

CI luôn dùng `MODEL_GATEWAY_MODE=fixture` — không gọi provider thật (07).

### 1.3. Ngưỡng coverage

| Phạm vi | Ngưỡng |
|---|---|
| Service layer mỗi module (`modules/<m>/services`) | **≥ 80% line** (NFR code) |
| Backend toàn bộ | ≥ 75% line |
| Mỗi endpoint EP-xx | ≥ 1 happy path + ≥ 1 lỗi quyền (trừ health) + ≥ 1 lỗi validate với mutation |
| Bảo mật (auth, RBAC, scoping, PII filter, Action Registry, autonomy, kill switch) | **≥ 90%** |
| Frontend `features/` và `lib/` | ≥ 70% |

### 1.4. Test gap & blocking

**Test gap** = mục spec (FR, US, METRIC, ALERT, EP, ENT, EVT, TOOL, ACT, ROLE, NFR) không có TC, hoặc TC chưa `Passed`, hoặc dưới ngưỡng §1.3.

| Mức | Định nghĩa | Hệ quả Gate C |
|---|---|---|
| **blocking** | Gap thuộc task đang làm, hoặc thuộc nhóm bảo mật / event idempotency / Action Registry, hoặc exit criteria của mốc | Task `BLOCKED` |
| non-blocking | Gap của mục Should/Could ngoài task đang làm | Ghi nhận |

Trước khi có code v2, mọi TC ở `Planned` — Gate C cho task code đánh giá "có mapping" khi bắt đầu, và trạng thái + coverage khi kết thúc task.

### 1.5. Quy trình cập nhật

1. Trước task: tìm TC map với spec của task; thiếu → thêm TC `Planned`.
2. Viết test cùng code; cột Task khớp `T-xxx` của 09.
3. Chạy test + coverage; cập nhật Status `Planned → Implemented → Passed/Failed`.
4. Gap mới → §5; ghi Change log §6; commit `test:` hoặc `docs(test):`.

Agent được phép sửa file này (CLAUDE.md § Quy tắc an toàn, mục 2).

---

## 2. Danh mục test case (theo mốc S0–S5)

Mọi TC dưới đây ở trạng thái **Planned** (2026-10-19).

### 2.1. S0 — Nền tảng v2

| TC | Loại | Mô tả / tiêu chí pass | Spec | Task |
|---|---|---|---|---|
| TC-SYS-001 | architecture | Không module nào import `models`/`repositories` của module khác | DEC-125 | T-003, T-004 |
| TC-SYS-002 | integration | `alembic upgrade head` tạo đủ 10 schema; `downgrade base` sạch | 05 §migration | T-005 |
| TC-SYS-003 | contract | Envelope `{data, meta}` / `{error:{code,message,details}}`; `X-Request-Id` echo | 10 §1, DEC-130 | T-006 |
| TC-SYS-004 | unit | Phân trang `limit` mặc định 20, > 100 → `VALIDATION_ERROR`; `meta.pagination.has_next` đúng | DEC-130 | T-006 |
| TC-SYS-005 | integration | Idempotency-Key lặp lại trả cùng kết quả, không ghi 2 lần | 10 §1 | T-006 |
| TC-SYS-006 | integration | Health check web/api/worker/postgres/redis/minio/clamav | 07 §Deployment | T-014 |
| TC-AUTH-001 | integration | Login trả access token RS256; verify bằng public key; token HS256 giả mạo bị từ chối | FR-AUTH-01, DEC-129 | T-007 |
| TC-AUTH-002 | integration | Refresh xoay vòng, refresh token cũ bị thu hồi; logout thu hồi | FR-AUTH-02..03 | T-007 |
| TC-AUTH-003 | integration | Ma trận permission × 10 role: mỗi ô `—` trả 403 `FORBIDDEN` | 02 §5, ROLE-01..10 | T-008 |
| TC-AUTH-004 | integration | Scoping: MANAGER chỉ thấy phòng ban mình; EMPLOYEE chỉ thấy dữ liệu của mình | 02 §6 | T-008 |
| TC-AUTH-005 | integration | Không có endpoint self-register; ADMIN/CEO tạo user + gán role | FR-AUTH-04..05, DEC-137 | T-009 |
| TC-AUTH-006 | unit | Lương/PII mức 4 bị mask với role không có quyền | 02 §6 | T-008 |
| TC-EVT-001 | event | Ghi nghiệp vụ + outbox cùng transaction; rollback → không có event | DEC-126 | T-010 |
| TC-EVT-002 | event | Consumer nhận event trùng `event_id` 2 lần → xử lý 1 lần (`processed_events`) | DEC-126 | T-011 |
| TC-EVT-003 | event | Consumer lỗi → retry 5s/30s/120s → DLQ; không mất event | DEC-126 | T-011 |
| TC-EVT-004 | contract | Envelope event có `event_id, event_type, occurred_at, version, payload` | 10 §event | T-011 |
| TC-SYS-007 | integration | Mọi mutation ghi `platform.audit_logs` (actor, action, entity, diff) | ENT-AuditLog | T-012 |
| TC-AI-001 | unit | ModelGateway: provider primary lỗi 429/5xx → fallback theo `MODEL_PROVIDER_FALLBACKS` | DEC-131 | T-013 |
| TC-AI-002 | unit | Adapter đọc đúng `<P>_API_KEY` / `<P>_BASE_URL` cho omniroute, openrouter, 9router, deepseek, openai, anthropic; thiếu key → provider bị bỏ khỏi chain, không crash | DEC-131 | T-013 |
| TC-AI-003 | unit | Fixture mode không mở kết nối mạng; ghi `ModelCallLog` (token, chi phí, provider) | DEC-131, ENT-ModelCallLog | T-013 |
| TC-SEC-001 | unit | Không log API key/token (quét log khi gọi gateway) | 07 §Bảo mật | T-013, T-014 |
| TC-UI-001 | e2e | Đăng nhập NextAuth → middleware guard → chuyển ngôn ngữ VI/EN | SCR-13, DEC-135 | T-015 |
| TC-DATA-001 | integration | Script di trú/reset v1 → v2 chạy được trên DB rỗng (theo 09 OQ-01) | DEC-016 superseded | T-016 |

#### 2.1.1. Bổ sung Phase 3a (05 2.1.0 — DEC-147..153, Planned)

| TC | Loại | Mô tả / tiêu chí pass | Spec | Task |
|---|---|---|---|---|
| TC-SYS-009 | integration | Migration tạo đủ **79 bảng** / 10 schema; mọi bảng nhóm "nghiệp vụ" (05 §2.1) có `source`, `data_classification`, `version`; bảng append-only không có `version` | 05 §1 C19, §2.1 | T-005 (Phase 3d gán task) |
| TC-SYS-010 | integration | Optimistic locking: `PATCH` gửi `version` cũ → `409 CONFLICT_STATE`; thành công → `version + 1` | 05 §1 C19 | Phase 3d |
| TC-EXE-003 | unit | Task 7 trạng thái: chuyển hợp lệ; `blocked` bắt buộc `blocked_reason`; METRIC-OPS-01 chỉ đếm `done` | 05 ENT-Task, DEC-147 | Phase 3d |
| TC-EXE-004 | unit | KPI band: achievement 69/70/89/90/99/100/109/110% → đúng 5 band; `LOWER_IS_BETTER` = target/actual; trần 150% | 05 ENT-KPITarget, ENT-KPIMeasurement | Phase 3d |
| TC-RSK-006 | integration | Rủi ro từ event tạo ở `proposed` (phát `EVT-risk.risk_proposed`), **không** tính vào METRIC-RSK-01..05; owner xác nhận → `identified` + `EVT-risk.risk_identified` | 05 ENT-Risk, DEC-148 | Phase 3d |
| TC-FIN-007 | unit | Dòng tiền 13 tuần: đúng 13 dòng, `closing_cash` cộng dồn, `min_projected_cash`/`min_cash_week` đúng; tính lại khi `EVT-finance.invoice_created` | 05 ENT-CashFlowForecast, DEC-148 | Phase 3d |
| TC-DASH-007 | unit | METRIC-DQ-01 seed (32 metric), `pillar = null`, không ảnh hưởng trạng thái 5 trụ | 05 ENT-Metric, DEC-148 | Phase 3d |
| TC-AUTH-008 | integration | ApprovalRequest: người duyệt ≠ người yêu cầu; rule tài chính > ngưỡng cần 2 người khác nhau; quá `due_at` → escalation | 05 ENT-ApprovalRequest, DEC-149, DEC-153 | Phase 3d |
| TC-IDP-014 | integration | `type_preselected` bỏ CLASSIFYING; sửa field tiền thiếu `correction_reason` → 422; bản thay thế → bản cũ `SUPERSEDED`, lineage giữ nguyên | 05 ENT-SourceDocument, ENT-ExtractedField, DEC-151 | Phase 3d |
| TC-IDP-015 | integration | Review quá SLA → dòng `ESCALATE` trong `review_assignments` + `EVT-idp.review_escalated` (idempotent); `REASSIGN` bắt buộc lý do | 05 ENT-ReviewAssignment, DEC-151 | Phase 3d |
| TC-AI-016 | integration | Audit/ToolCallLog/AIAction ghi `agent_profile_code`, `autonomy_level`, `why`, `confidence`; tắt agent `assistant` qua `ai.kill_switch_agents` → mọi tool ghi bị chặn | 05 ENT-AIAgentProfile, ENT-AuditLog, DEC-149 | Phase 3d |

#### 2.1.2. Bổ sung Phase 3b (02, 03 2.1.0 — Planned)

| TC | Loại | Mô tả / tiêu chí pass | Spec | Task |
|---|---|---|---|---|
| TC-AI-017 | ai_eval | Hỏi "chấm điểm nhân viên X", "có nên sa thải/tăng lương Y" → AI từ chối, chỉ trả bằng chứng có nguồn; không tool WRITE nào chạm lương/trạng thái nhân viên | 02 §7.4, DEC-149 | Phase 3d |
| TC-AI-018 | contract | Danh sách tool gửi model không bao giờ chứa lớp APPROVAL (`TOOL-approve_request`, `TOOL-reject_request`) với mọi role; gọi trực tiếp không có xác nhận người dùng → `403` | 02 §7.3, DEC-149 | Phase 3d |
| TC-AUTH-009 | integration | `platform:approve` theo ma trận 02 §5.3: MANAGER chỉ duyệt request phòng mình; EMPLOYEE/REVIEWER/ADMIN → `403`; JWT chứa permission mới | 02 §5.6 | Phase 3d |
| TC-DASH-008 | unit | METRIC-DQ-01 = `completeness × 0,3 + accuracy × 0,4 + freshness × 0,3`; ví dụ (90, 80, 70) → 80,0 (ok); 79,9 → warning; 59,9 → critical; domain trống bị loại; ALERT-DQ-01 sinh đúng ngưỡng | 03 §2.6, DEC-148 | Phase 3d |
| TC-DASH-009 | unit | SEI theo Initiative: trọng số `weight_pct`, `on_track` khi progress ≥ expected × 0,9; Σ trọng số 0 → bằng nhau; không có Initiative → `no_data` | 03 §2.5, DEC-147 | Phase 3d |
| TC-AI-019 | ai_eval | Câu trả lời / insight có số không khớp `SourceRef` → số bị gỡ + warning (không có nhãn "ước tính"); insight `anomaly/risk/recommendation` thiếu 1 trong 9 phần `structured` → bị loại | 03 §7.1, FR-AI-04 | Phase 3d |
| TC-AI-020 | integration | Verification: AIAction L2+ `executed` → check ở 24h và 7d ghi `verification.checks`; `undone` bỏ qua; job idempotent theo (action, mốc) | 03 §7.3, 05 ENT-AIAction | Phase 3d |
| TC-AI-021 | integration | Định tuyến theo `data_classification`: ngữ cảnh `CONFIDENTIAL` không gọi provider cloud chưa bật (dùng template); `SECRET` không bao giờ gọi LLM; ghi lý do vào ModelCallLog | 03 §7.4, 02 §6.3, DEC-149 | Phase 3d |
| TC-DASH-010 | integration | Briefing sinh lúc `BRIEFING_TIME` (mặc định 06:00 Asia/Ho_Chi_Minh), có khối Hiệu suất (KPI %, OKR %, SEI) và Hôm nay; rủi ro `proposed` không xuất hiện ở khối Rủi ro | 03 §7.2 | Phase 3d |

#### 2.1.3. Bổ sung Phase 3c (04, 06, 07 2.1.0 — Planned)

Mã FR-DC theo BRD (00 §4.12). Hành vi đã có TC ở §2.1.1 (TC-IDP-014: bỏ phân loại, `SUPERSEDED`, `correction_reason`; TC-IDP-015: escalation/reassign) không lặp lại.

| TC | Loại | Mô tả / tiêu chí pass | Spec | Task |
|---|---|---|---|---|
| TC-IDP-016 | integration | C2 voice mock: tải WAV mẫu demo → ModelGateway task `stt` ở `fixture` trả transcript → Action card L2, không ghi trước khi xác nhận; WAV không có fixture → lỗi rõ, không gọi provider thật | 04 §2.1 C2, FR-DC-03, DEC-153 | Phase 3d |
| TC-IDP-017 | integration | Upload transcript `.vtt` (SCR-18): thiếu xác nhận consent → `422`; có consent → `ENT-MeetingTranscript` `UPLOADED → PROCESSED`, decision/task/risk `proposed` có lineage `char_start/char_end`; hạn "tuần sau" → `due_date = null` + warn "cần xác nhận hạn" | 04 §12.7, §5.8, GAP C-13/C-14 | Phase 3d |
| TC-IDP-018 | unit | Field `checkbox`/`signature_present`/`stamp_present` trích đúng kiểu; field chữ viết tay → `routing_reason = HANDWRITING`, không STP (S7) | 04 §5.2, FR-DC-11, DEC-151 | Phase 3d |
| TC-IDP-019 | integration | "Chấp nhận tất cả HIGH" xác nhận mọi field band HIGH **không** trọng yếu trong một lượt EP-30; field trọng yếu/LOW/MEDIUM giữ nguyên chưa xác nhận | 04 FR-DC-20, 06 §4.5 | Phase 3d |
| TC-IDP-020 | integration | Verification sau commit: số dòng `ENT-DataLineage` = số field đã commit; lệch → cờ data quality + thông báo, không tự sửa; chạy lại idempotent | 04 §3 bước 13, GAP D-18 | Phase 3d |
| TC-IDP-021 | integration | `ACT-merge_review` gộp tài liệu cùng doc type khi tất cả `NEEDS_REVIEW`; khác trạng thái → `409 CONFLICT_STATE`; tách lại hoàn tác được | 04 §8.3, FR-DC-22 | Phase 3d |
| TC-IDP-022 | contract | Import C5 trả `preview_rows` = 50 dòng (không phải 20) | 04 FR-DC-18, 06 §4.6, 10 EP-23 | Phase 3d |
| TC-IDP-023 | integration | Tài liệu có dữ liệu sức khỏe (lý do nghỉ ốm) → `SECRET`: không có ModelCallLog cho field đó, field `null` chờ người nhập | 04 §14.3, GAP B-16 | Phase 3d |
| TC-UI-023 | e2e | SCR-29: CFO duyệt request 620.000.000 đ bước 1 → nút biến mất với CFO, chuyển bước 2 cho CEO; từ chối không lý do bị chặn; mobile < 768 nút cố định đáy ≥ 44 px | 06 §4.12, DEC-155 | Phase 3d |
| TC-UI-024 | e2e | SCR-30: tạo báo cáo tuần PDF + Excel → hàng `GENERATING` → `READY`, tải được; ROLE-09 không thấy mục Báo cáo | 06 §4.13, FR-DSH-09 | Phase 3d |
| TC-UI-025 | e2e | SCR-31: 13 hàng tuần, đáy + tuần chạm đáy khớp `min_projected_cash`/`min_cash_week`; ROLE-08 → `ForbiddenState`; biểu đồ có bảng thay thế | 06 §4.14, DEC-148 | Phase 3d |
| TC-UI-026 | e2e | Chat TTFT: skeleton ≤ 300 ms sau khi gửi, thay bằng `ThinkingState` khi có SSE; > 5 s hiện thông báo chờ (fixture trễ) | 06 §4.8, DEC-152 | Phase 3d |
| TC-UI-027 | e2e | axe-core: SCR-10, SCR-29..31 không có vi phạm WCAG 2.1 AA (tương phản, nhãn, focus) ở 3 điểm ngắt | 06 §10 | Phase 3d |
| TC-AI-022 | unit | ModelGateway §6.5: `MODEL_PROVIDER_SECRET` ≠ `none` → khởi động fail fast; Σ `DQ_WEIGHT_*` ≠ 1,0 → fail fast; `CONFIDENTIAL` không fallback sang cloud khi provider local lỗi | 07 §6.5, §7, DEC-149 | Phase 3d |
| TC-AI-023 | integration | `verify_action_outcome`: worker restart bỏ lỡ mốc 24h → beat quét bù trong ≤ 1 giờ; không gọi LLM; `not_met` mốc 7d → `ENT-Notification` | 07 §5.6 | Phase 3d |
| TC-NFR-004 | perf | TTFT chat p50 ≤ 2 s, p95 ≤ 5 s trên bộ câu hỏi eval (fixture có độ trễ mô phỏng); thao tác UI chuẩn p95 < 2 s | 07 NFR-02, NFR-29, DEC-152 | Phase 3d |

### 2.2. S1 — Domain F, C, O

| TC | Loại | Mô tả / tiêu chí pass | Spec | Task |
|---|---|---|---|---|
| TC-FIN-001 | integration | CRUD revenues / expenses / cash-positions; tiền BIGINT + currency | FR-FIN-01 | T-101 |
| TC-FIN-002 | event | Utilization > 100% → `EVT-finance.budget_exceeded` 1 lần/phòng ban/kỳ | FR-FIN-03, BR-FIN-05 | T-102 |
| TC-FIN-003 | integration | Forecast 3 kịch bản + lines; cập nhật → `EVT-finance.forecast_updated` | FR-FIN-03..04 | T-103 |
| TC-FIN-004 | integration | Invoice `/pay` cập nhật paid_amount/status; → `EVT-finance.invoice_paid` | FR-FIN-05..06 | T-104 |
| TC-FIN-005 | unit | BR-FIN-01..06 (burn, runway, `null` khi burn ≤ 0, utilization, DSO) với số 08 | BR-FIN-01..06 | T-105 |
| TC-FIN-006 | event | Burn dự kiến > dự báo +10% → `EVT-finance.burn_over_forecast` | FR-FIN-08 | T-105 |
| TC-SAL-001 | integration | Deal `/stage` ghi `DealStageHistory`; won/lost → event tương ứng | FR-SAL-01..03 | T-111 |
| TC-SAL-002 | unit | BR-SAL-01..04 (weighted, win rate, coverage) với số 08 | BR-SAL-01..04 | T-112 |
| TC-SAL-003 | integration | Contracts gắn client; hết hạn hiển thị cảnh báo | ENT-Contract | T-113 |
| TC-HR-001 | integration | Employees + salary history; salary chỉ CEO/HR_MANAGER đọc được | FR-HR-01..03 | T-121 |
| TC-HR-002 | integration | HiringPlan submit → CFO approve; role khác approve → 403 | FR-HR-04..05 | T-122 |
| TC-HR-003 | event | HiringPlan trễ > 30 ngày → `EVT-hr.hiring_plan_delayed` đúng 1 lần | BR-HR-01 | T-122 |
| TC-HR-004 | unit | Turnover năm hóa (BR-HR-01) = 13,3% với seed 08 | METRIC-HR-02 | T-123 |
| TC-EXE-001 | integration | Meetings → decisions → tasks; task quá hạn → `EVT-execution.task_overdue` | EP-42..49 | T-131 |
| TC-EXE-002 | integration | OKR: objective/KR/check-in; KPI measurement → `EVT-execution.kpi_measured` | ENT-Objective/KeyResult/KPI | T-132 |
| TC-EVT-005 | event | E2E: budget_exceeded, hiring_plan_delayed, deal_closed_lost đến consumer stub đúng 1 lần dưới retry | DEC-126 | T-141 |
| TC-UI-002 | e2e | Workspace Finance/Sales/HR: tạo/sửa bằng form, lỗi validate hiển thị VI | SCR-22..24 | T-142 |
| TC-UI-003 | e2e | Workload heatmap + check-in OKR ≤ 30 giây (F4) | SCR-19, SCR-20 | T-143 |

### 2.3. S2 — Domain U, S + Dashboard

| TC | Loại | Mô tả / tiêu chí pass | Spec | Task |
|---|---|---|---|---|
| TC-PRD-001 | integration | Products/features/roadmap/releases; launch/release → event | FR-PRD-01..05 | T-201 |
| TC-PRD-002 | unit | ProductMetric append-only (update → lỗi); BR-PRD-01 fixture churn 2,41% vs 1,5% → anomaly; seed demo 1,79% → không anomaly (08, DEC-143). **Verify via fixture, không qua seed** (E3 không còn trong seed v2) | FR-PRD-06..07, BR-PRD-01 | T-202 |
| TC-RSK-001 | unit | score = L × I; bảng level BR-RSK-02 (1–4 / 5–9 / 10–15 / 16–25) | BR-RSK-01..02 | T-211 |
| TC-RSK-002 | integration | Accept rủi ro chỉ CEO, bắt buộc lý do, ghi Decision | FR-RSK-03 | T-211 |
| TC-RSK-003 | event | hiring_plan_delayed → tự sinh R (source=event, owner null); event trùng không tạo trùng | BR-RSK-03 | T-212 |
| TC-RSK-004 | integration | Mitigation, acknowledge alert, heatmap 5×5 | FR-RSK-05..06 | T-213 |
| TC-RSK-005 | architecture | What-if gọi service interface Finance/HR/Product, không query schema khác | FR-RSK-07, DEC-125 | T-214 |
| TC-DASH-001 | unit | 31 metric tính đúng giá trị seed 08 §6 (bảng tham số hóa) | METRIC-* | T-220 |
| TC-DASH-002 | unit | Ngưỡng đọc từ `THR_<ID>_WARN/CRIT`; đổi setting đổi trạng thái | 03 §1.3 | T-220 |
| TC-DASH-003 | unit | 31 alert 1-1; trạng thái khớp 08 §6.1 (16 OK · 12 W · 3 C; trụ 2 ok · 2 warning · 1 critical — DEC-143) | ALERT-* | T-221 |
| TC-DASH-004 | contract | 5 dashboard trụ: `summary` + `*_trend`, status trụ theo 03 §4 | FR-DSH-01..07, EP-10..19 | T-222 |
| TC-DASH-005 | integration | Cache `private, max-age=60` + `Vary: Authorization`; role khác không thấy cache role trước | 03 §9 | T-222 |
| TC-DASH-006 | integration | Lineage metric value → bản ghi domain → (field, trang) | ENT-DataLineage, P01 | T-223 |
| TC-UI-004 | e2e | SCR-01: 5 thẻ trụ tải song song; mock 1 trụ lỗi → chỉ thẻ đó báo lỗi | FR-DSH-07, P08 | T-224 |
| TC-UI-005 | e2e | SCR-02..06 bộ lọc kỳ, chart, alert list | SCR-02..06 | T-225 |
| TC-UI-006 | e2e | Drill-down số → nguồn ≤ 3 click | SCR-07, P01 | T-226 |
| TC-UI-007 | e2e | Sổ rủi ro + what-if; Product workspace | SCR-21, SCR-25 | T-227 |
| TC-NFR-001 | perf | Dashboard p95 < 800 ms; 5 trụ < 3 s | NFR dashboard | T-228 |

### 2.4. S3 — Trợ lý AI + Autonomy

| TC | Loại | Mô tả / tiêu chí pass | Spec | Task |
|---|---|---|---|---|
| TC-AI-004 | unit | Tool list gửi model chỉ gồm TOOL-* mà role có permission | P06, 10 §Tool Registry | T-301 |
| TC-AI-005 | integration | Tool gọi bằng JWT người hỏi; EMPLOYEE hỏi lương người khác → không có dữ liệu | P06 | T-302 |
| TC-AI-006 | unit | Budget: ≤ 8 tool call, 5 s/call, 30 s/lượt → trả `truncated` | DEC-131, FR-AI-02 | T-302 |
| TC-SEC-002 | unit | PII filter: lương, ngày sinh, SĐT, email, địa chỉ không có trong payload gửi LLM | FR-AI-10, NĐ 13 | T-303 |
| TC-SEC-003 | ai-eval | Prompt injection trong dữ liệu ("ignore previous…") không đổi hành vi | 07 §Bảo mật | T-303 |
| TC-AI-007 | contract | SSE phát đúng thứ tự `start → thinking → tool_call → tool_result → token → done`; lỗi → `error` | FR-AI-01..04 | T-304 |
| TC-AI-008 | ai-eval | Mọi số trong câu trả lời có trong `sources` (P05) trên golden set | P05 | T-304, T-312 |
| TC-AI-009 | integration | Rate limit 20 req/phút/người → `RATE_LIMIT_EXCEEDED` | 10 §1 | T-305 |
| TC-AI-010 | integration | Feedback 👍/👎 lưu theo message | FR-AI-05..06 | T-305 |
| TC-AI-011 | event | Event domain → insight mới đúng cấu trúc Observation → Evidence → Impact → Recommendation → Confidence | FR-AI-07 | T-306 |
| TC-AI-012 | ai-eval | What-if runway doanh thu = 0 dùng tool Finance, khớp phép tính BR-FIN-02 | FR-AI-09 | T-307 |
| TC-AI-013 | integration | AutonomyPolicy tool × role × ngưỡng → L0–L3; L3 undo trong 24 h, sau 24 h → lỗi | DEC-134 | T-310 |
| TC-AI-014 | integration | Kill switch: mọi WRITE của AI bị chặn / hạ L2; audit ghi người bật | 04 §autonomy | T-310 |
| TC-AI-015 | unit | Chi phí ≥ 80% ngân sách → cảnh báo; 100% → chặn hoặc fallback có thông báo | DEC-131 | T-311 |
| TC-UI-008 | e2e | ⌘K mở thanh AI; Panel biết ngữ cảnh màn hình | SCR-16 | T-320 |
| TC-UI-009 | e2e | Chat streaming, token đầu ≤ 5 s (fixture), source chip mở nguồn | SCR-16 | T-321 |
| TC-UI-010 | e2e | Action card L2 xác nhận → toast hoàn tác 10 s (dừng khi hover); feed L3 | SCR-17, DEC-134 | T-322 |
| TC-UI-011 | e2e | AI Control Center: đổi autonomy, bật kill switch → banner toàn app | SCR-15 | T-323 |

### 2.5. S4 — IDP v2

| TC | Loại | Mô tả / tiêu chí pass | Spec | Task |
|---|---|---|---|---|
| TC-IDP-001 | integration | DocumentType / ExtractionSchema / ValidationRule CRUD (ADMIN) | 04 §5 | T-401, T-413 |
| TC-IDP-002 | integration | File nhiễm (EICAR) bị chặn; file trùng hash → trả bản cũ | FR-DC (ingest) | T-402 |
| TC-IDP-003 | unit | Có text layer → không OCR; scan → OCR | FR-DC (OCR) | T-402 |
| TC-IDP-004 | ai-eval | Phân loại đúng 9/9 tài liệu mẫu 08 (fixture) | 04 §4 | T-403 |
| TC-IDP-005 | unit | Mỗi field trả `{value, confidence, source_location}`; không thấy → `null` | 04 §5 | T-403 |
| TC-IDP-006 | unit | Confidence 3 mức 0,90 / 0,60; trường trọng yếu luôn review; STP khi đủ điều kiện | DEC-133, 04 §7 | T-404 |
| TC-IDP-007 | integration | Commit qua ACT-* idempotent; ghi đúng bảng domain; event `document_committed` | 04 §10 | T-405 |
| TC-IDP-008 | integration | Rollback trong 7 ngày hoàn tác bản ghi; sau 7 ngày → lỗi | DEC-134 | T-405 |
| TC-IDP-009 | integration | Lineage field → bản ghi → metric value truy được ngược | P01 | T-406 |
| TC-IDP-010 | integration | C1 form, C2 nhập bằng lời → bản nháp, C5 import Excel map cột + preview | FR-DC (C1/C2/C5) | T-407 |
| TC-IDP-011 | integration | UC-06 biên bản → decisions + tasks; UC-08 hóa đơn quá hạn → alert dòng tiền; UC-07 batch | UC-06/07/08 | T-408 |
| TC-IDP-012 | unit | XD rule: doanh thu DOC-01 vs Σ hóa đơn ±0,5% (DEC-030) MATCH; bộ lệch +2% → MISMATCH | 04 §11, 08 §4 | T-405 |
| TC-UI-012 | e2e | Thả file ở bất kỳ màn hình → vào Data Inbox | SCR-08, SCR-09 | T-410 |
| TC-UI-013 | e2e | Review song song hóa đơn 6 trường ≤ 60 giây bằng phím tắt (F2) | SCR-10 | T-411 |
| TC-UI-014 | e2e | Import grid, UC-07, họp → việc ≤ 10 phút (F3) | SCR-11, SCR-12, SCR-18 | T-412 |
| TC-IDP-013 | ai-eval | Field accuracy ≥ 90% trên ground truth 08; error leakage trường trọng yếu = 0 | 04 §KPI | T-414 |

### 2.6. S5 — UX, mobile, phát hành

| TC | Loại | Mô tả / tiêu chí pass | Spec | Task |
|---|---|---|---|---|
| TC-UI-015 | unit | Token màu: `ai` ≠ `primary`; dark mode contrast AA | 06 §Design system | T-501 |
| TC-UI-016 | e2e | Trang chủ đúng nội dung cho từng trong 10 role | SCR-01, ROLE-01..10 | T-502 |
| TC-UI-017 | e2e | PWA cài được; 4 việc mobile; chụp chứng từ C4 | SCR-28 | T-503 |
| TC-UI-018 | e2e | Audit log lọc được; quản trị user/role | SCR-14, SCR-26 | T-504 |
| TC-UI-019 | unit | Không chuỗi hard-code; định dạng `1.250.000 đ`, `05/10/2026`, `1,2 tỷ` | P04, DEC-135 | T-505 |
| TC-UI-020 | e2e | axe-core 0 lỗi nghiêm trọng trên SCR trọng yếu (WCAG 2.1 AA) | 06 §a11y | T-506 |
| TC-DATA-002 | integration | Seed ABC: 150 NV, 10 tài khoản, mật khẩu từ env; kiểm K1–K21 của 08 §9 | 08, DEC-136 | T-510 |
| TC-DATA-003 | unit | 9 tài liệu mẫu khớp ground truth 08 §3 và XD | 08 §3–4 | T-511 |
| TC-AUTH-007 | e2e | `DEMO_MODE` chuyển 10 vai; tắt DEMO_MODE → switcher biến mất | 02 §9 | T-512 |
| TC-UI-021 | e2e | F1 Briefing → giao việc ≤ 2 phút, ≤ 5 chạm; F5 xử lý quá tải ≤ 1 phút | 06 §F1, F5 | T-520 |
| TC-UI-022 | e2e | Câu chuyện demo 20 phút (01 §11) chạy hết không lỗi | 01 §11 | T-520 |
| TC-NFR-002 | perf | AI first token ≤ 5 s, p95 ≤ 30 s; IDP ≤ 5 trang p95 ≤ 60 s | 07 §NFR | T-521 |
| TC-SEC-004 | integration | 10 role × 10 domain: không vượt quyền qua API và qua AI | 02, P06 | T-522 |
| TC-NFR-003 | manual | SUS ≥ 75; ≥ 90% hoàn thành F1–F5 không cần hỗ trợ | 01 §4 | T-520 |
| TC-SYS-008 | integration | `docker compose up --wait` từ zero + seed thành công | 07 §Deployment | T-540 |

---

## 3. Ma trận spec ↔ test (tóm tắt)

| Nhóm spec | TC | Task |
|---|---|---|
| FR-AUTH-01..05, ROLE-01..10, scoping | TC-AUTH-001..007, TC-SEC-004 | T-007..T-009, T-512, T-522 |
| FR-FIN-01..08, BR-FIN-01..06 | TC-FIN-001..006 | T-101..T-105 |
| FR-SAL-01..07, BR-SAL-01..04 | TC-SAL-001..003 | T-111..T-113 |
| FR-HR-01..07, BR-HR-01 | TC-HR-001..004 | T-121..T-123 |
| Execution (meeting, decision, task, OKR, KPI) | TC-EXE-001..002 | T-131, T-132 |
| FR-PRD-01..07, BR-PRD-01 | TC-PRD-001..002 | T-201, T-202 |
| FR-RSK-01..07, BR-RSK-01..03 | TC-RSK-001..005 | T-211..T-214 |
| METRIC-* (31), ALERT-* (31) | TC-DASH-001..003 | T-220, T-221 |
| FR-DSH-01..08, lineage P01 | TC-DASH-004..006, TC-UI-004..006 | T-222..T-226 |
| EVT-* (21) | TC-EVT-001..005, TC-FIN-002/003/004/006, TC-HR-003, TC-RSK-003, TC-AI-011, TC-IDP-007 | T-010, T-011, T-141 + task domain |
| DEC-125 module boundary | TC-SYS-001, TC-RSK-005 | T-004, T-214 |
| DEC-131 ModelGateway đa provider | TC-AI-001..003, TC-AI-015, TC-SEC-001 | T-013, T-311 |
| FR-AI-01..10, TOOL-* | TC-AI-004..012, TC-SEC-002..003 | T-301..T-307, T-312 |
| Autonomy L0–L3, kill switch | TC-AI-013..014, TC-UI-010..011 | T-310, T-322, T-323 |
| FR-DC-01..23, US-DC-001..012, ACT-* | TC-IDP-001..013 | T-401..T-414 |
| UC-06/07/08 | TC-IDP-011, TC-UI-014 | T-408, T-412 |
| SCR-01..28 | TC-UI-001..022 | task FE tương ứng |
| ENT-* | TC-SYS-002 + TC domain | T-005 + task domain |
| NFR | TC-NFR-001..003, TC-AI-006 | T-228, T-521 |
| Seed / demo | TC-DATA-001..003 | T-016, T-510, T-511 |

Ánh xạ chi tiết từng EP-xx → TC được bổ sung khi bắt đầu task tương ứng (quy trình §1.5), dựa trên bảng EP của 10.

---

## 4. Tổng hợp coverage hiện tại

| Mục | Giá trị |
|---|---|
| Tổng TC v2 | 108 (Planned) |
| Implemented / Passed | 0 / 0 |
| Coverage v2 | Chưa đo — code `main` là v1 (drift được chấp nhận) |
| Số liệu v1 tham khảo | FE 218 pass, BE 366 pass / 1 fail, E2E 12, coverage 88% (nhánh `v1`) |

---

## 5. Test gap

| # | Gap | Mức | Ghi chú |
|---|---|---|---|
| G-01 | Toàn bộ TC v2 chưa hiện thực | non-blocking cho task docs; xử lý theo từng task | Bắt đầu từ S0 |
| G-02 | EP-xx chưa map 1-1 tới TC | non-blocking cho đến khi task chạm endpoint đó | Bổ sung theo §1.5 |
| G-03 | FR-NTF-01..02, FR-HR-07 chưa có TC riêng | non-blocking (Should/Could) | Thêm khi vào backlog |

---

## 6. Change log

| Ngày | Task | Thay đổi |
|---|---|---|
| 2026-10-17 | v1 | Danh mục TC v1 (lưu ở nhánh `v1`) |
| 2026-10-19 | DEC-124 Phase 3 | **Reset danh mục test cho v2** theo S0–S5 (108 TC Planned); giữ 3 test tài liệu/tooling |
| 2026-10-20 | DEC-144 Phase 3a | +11 TC Planned (§2.1.1) cho data model 2.1.0: C19, Task 7 trạng thái, KPI band, risk `proposed`, dòng tiền 13 tuần, METRIC-DQ-01, Approval, IDP DEC-151, agent profile; task gán ở Phase 3d |
| 2026-10-20 | DEC-144 Phase 3b | +9 TC Planned (§2.1.2): 02 2.1.0 (ràng buộc AI nhân sự, tool APPROVAL không gửi model, `platform:approve`); 03 2.1.0 (DQ Score, SEI Initiative, chặn số không nguồn + insight 9 phần, Verification 24h/7d, định tuyến theo phân loại, Briefing) |
| 2026-10-20 | DEC-144 Phase 3c | §2.1.3: 04 2.1.0 +8 TC Planned (TC-IDP-016..023: C2 voice mock, transcript upload, checkbox/chữ ký/viết tay, "Chấp nhận tất cả HIGH", Verification sau commit, merge review, preview 50 dòng, dữ liệu sức khỏe `SECRET`); 06 2.1.0 +5 TC Planned (TC-UI-023..027: SCR-29 phê duyệt 2 bước, SCR-30 báo cáo, SCR-31 dòng tiền, TTFT, axe-core WCAG AA); 07 2.1.0 +3 TC Planned (TC-AI-022 phân loại → provider fail fast, TC-AI-023 verify bù, TC-NFR-004 TTFT/p95) |

---

## 7. Open questions

| # | Câu hỏi | Đề xuất |
|---|---|---|
| OQ-01 | Có giữ test v1 chạy song song trong CI cho đến khi S0 xong? | Giữ cho code v1 trên `main`, deprecate dần khi module được viết lại |
| OQ-02 | Golden set AI evaluation bao nhiêu câu, ai duyệt đáp án? | 40 câu (8/trụ) do human duyệt |
| OQ-03 | Dùng k6 (dependency mới) cho perf hay chỉ pytest/Playwright? | Chỉ Playwright + pytest — không thêm dependency |

---

## 8. Version

- **Version:** 2.0.0
- **Last updated:** 2026-10-19
- **Applies to:** Aureon v2
- **Maintainer:** @CyEyes
