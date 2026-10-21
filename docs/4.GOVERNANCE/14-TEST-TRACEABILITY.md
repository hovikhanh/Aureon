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

Mọi TC dưới đây ở trạng thái **Planned** (2026-10-19), trừ các TC ghi trạng thái ở §2.0.

### 2.0. Trạng thái hiện thực S0a (2026-10-21)

Đợt S0a do human giao (brief "S0a T-001..T-009") đánh số task khác 09; ánh xạ: brief T-001 ↔ 09 T-003 · T-002 ↔ T-002 + T-014 · T-003 ↔ T-005 · T-004 ↔ T-007/T-008 · T-005 ↔ T-006 · T-006 ↔ T-010/T-011 · T-007 ↔ T-012 · T-008 ↔ T-008 (seed) · T-009 ↔ T-017. Cột "Task" ghi mã 09.

| TC | Trạng thái | Test | Task (09) | Commit |
|---|---|---|---|---|
| TC-SYS-001 | Implemented (một phần — scaffold 11 module; test import-boundary ở T-004) | `apps/api/tests/unit/test_scaffold.py` | T-003 | brief T-001 |
| TC-SYS-006 | Implemented (một phần — compose healthcheck postgres/redis/minio/ollama/clamav/worker/beat; `web`/`api` chưa có service) · env v2.1 kiểm bằng `test_env_example.py` | `docker compose ps`, `apps/api/tests/unit/test_env_example.py` | T-002, T-014 | brief T-002 |
| TC-SYS-002 | Passed — `alembic upgrade head` tạo 10 schema; `downgrade base` sạch (0 bảng/enum module, `public` v1 không đổi); `alembic check` không drift. Chuỗi đơn 0001…0005, version table `platform.alembic_version` | `apps/api/tests/integration/test_migrations.py` + CLI round-trip | T-005 | brief T-003a..e |
| TC-SYS-009 | Passed — 79 bảng / 10 schema khớp metadata; nhóm nghiệp vụ/cấu hình có `version` + `data_classification`; append-only không `source`/`version`/`deleted_at` (ngoại lệ ghi trong test: `outbox_events.version` = version payload, `ai.conversations` xóa mềm); FK cùng schema + index (C6), không FK xuyên schema (C7); `audit_logs` chặn UPDATE | `apps/api/tests/integration/test_migrations.py` | T-005, T-018 | brief T-003a..e |
| TC-AUTH-001 | Passed — EP-02 login trả JWT RS256 (`kid`, claim 10 §2.1, access 900 s); verify bằng public key; HS256 / `none` / sai `aud` / payload sửa / chữ ký sửa / hết hạn → `401`; sai mật khẩu / email lạ / user inactive → cùng `401 INVALID_CREDENTIALS`; khóa tạm sau 5 lần sai (02 §4); body không nhận `role` (`extra=forbid`) | `apps/api/tests/unit/test_security.py`, `apps/api/tests/integration/test_auth.py` | T-007 | brief T-004 |
| TC-AUTH-002 | Passed — EP-06 xoay vòng refresh token (chỉ lưu sha256), dùng lại token đã xoay → thu hồi cả chuỗi `family_id`; EP-07 logout `204` idempotent, token bị thu hồi | `apps/api/tests/integration/test_auth.py` | T-007 | brief T-004 |
| TC-AUTH-003 | Implemented (một phần — guard + ma trận) — `require_permission` 10 role × 33 permission (02 §5.3) → `200` hoặc `403 FORBIDDEN_ROLE`; permission lạ bị từ chối lúc import; permission lấy từ token, không từ tên role. Seed role vào DB ở T-008 | `apps/api/tests/unit/test_rbac.py` | T-008 | brief T-004 |
| TC-AUTH-005 | Implemented (một phần) — `POST /auth/register` → `404 NOT_FOUND` (DEC-137); tạo user ở T-009 (09) | `apps/api/tests/integration/test_auth.py` | T-009 | brief T-004 |
| TC-SYS-003 | Passed — `EnvelopeRouter` tự bọc `{data, meta:{request_id, generated_at, pagination}}` (route chỉ trả payload; OpenAPI hiện `Envelope[...]`); lỗi `{error:{code,message,details}}` cho AppError / validation (`details.fields[]`) / 404 / 405 / 500 không lộ stack; `X-Request-Id` echo UUID hợp lệ hoặc sinh mới, có ở cả response lỗi. Contract test đọc bảng 10 §1.4 trực tiếp: mọi class lỗi + `AI_*` khớp mã và HTTP status; chỉ EP-02/EP-06 public | `apps/api/tests/unit/test_envelope.py`, `apps/api/tests/contract/test_api_contract.py` | T-006 | brief T-005 |
| TC-SYS-004 | Passed — `limit` mặc định 20, 1..100; `> 100`, `offset < 0`, `sort_by` ngoài whitelist, `order` sai → **`400 BAD_REQUEST`** theo 10 §1.5 (DEC-175); `has_next` đúng; `BaseRepository.list_page` trả `(items, total)` có filter + soft delete trên PG thật | `apps/api/tests/unit/test_pagination.py`, `apps/api/tests/integration/test_repository_page.py` | T-006 | brief T-005 |
| TC-EVT-001 | Passed — `publish_in_tx` ghi `platform.outbox_events(PENDING)` trong transaction của caller; rollback → không có row; event type phải thuộc registry 28 `EVT-*` (00 §4.5); payload chứa key PII/mức 3–4 bị từ chối; beat `relay_outbox_events` mỗi `OUTBOX_RELAY_INTERVAL_SECONDS`=2 s (07 §3), Celery `acks_late` + `reject_on_worker_lost` | `apps/api/tests/events/test_outbox.py`, `apps/api/tests/events/test_celery_tasks.py` | T-010 | brief T-006 |
| TC-EVT-002 | Passed — relay `FOR UPDATE SKIP LOCKED LIMIT 100` fan-out mỗi consumer 1 message → `PUBLISHED` + `published_at`; 2 relay đồng thời trên 30 event: mỗi event gửi đúng 1 lần, không deadlock; broker lỗi → giữ `PENDING` + `attempts`/`last_error`, quá ngưỡng → `FAILED`; consumer nhận trùng → `DUPLICATE`, handler chạy 1 lần; ghi của handler + `processed_events(DONE)` cùng transaction | `apps/api/tests/events/test_event_bus.py` | T-011 | brief T-006 |
| TC-EVT-003 | Passed — lỗi → retry 5 s / 30 s / 120 s (4 lần chạy) → `processed_events(status=DLQ, attempts=4, last_error)`; delivery muộn của event đã DLQ bị bỏ qua; EP-56 `GET /platform/dead-letters` (`platform:admin`: CEO/ADMIN; role khác `403`) + `POST /platform/dead-letters/{id}/replay` `202` → xóa marker DLQ, gửi lại → xử lý `DONE`; replay lần 2 → `404` | `apps/api/tests/events/test_dlq.py` | T-011 | brief T-006 |
| TC-EVT-004 | Passed — envelope `{event_id, event_type, occurred_at, version, correlation_id, producer, payload}` (10 §8.1), `correlation_id` = `X-Request-Id` | `apps/api/tests/events/test_outbox.py` | T-011 | brief T-006 |
| TC-SYS-007 | Implemented (nền tảng — mutation nghiệp vụ gắn audit theo task domain) — `platform.audit_logs` bất biến 3 lớp: trigger 0001 chặn UPDATE/DELETE SQL thô; ORM guard chặn flush UPDATE/DELETE + bulk `update()/delete()`; migration 0007 role `app_audit_writer` chỉ `INSERT, SELECT` (đã thử `SET ROLE`: INSERT OK, UPDATE `permission denied`; app vẫn dùng role chung — defense in depth). `AuditRepository` chỉ `create`/`list`; `@auditable(action, entity)` ghi cùng transaction, lỗi → không có row, rollback → mất row; before/after/metadata mask mức 3–4 `••••`; `auth.login` / `auth.logout` / `auth.refresh_reuse` được audit với actor USER + role | `apps/api/tests/integration/test_audit.py` | T-012 | brief T-007 |
| TC-SEC-PII (DEC-176) | Passed — quét nội dung: CCCD / SĐT (di động + bàn) / email / số tài khoản bị phát hiện; không bắt nhầm "email hóa đơn", `1.000.000 đ`, `27.500.000.000 đ`, mã hóa đơn, UUID, `EMP-0042`, 9 số; hit không chứa giá trị thô; outbox `PIIDetectedError` ghi path + loại; audit mask (`salary` → `••••`, SĐT → `••••4567`, email → `••••@abc.vn`) cả before/after/metadata | `apps/api/tests/unit/test_pii.py` | T-010, T-012 | DEC-176 |
| TC-SYS-001 (T-004) | Passed — quét AST mọi `import` (kể cả import trong hàm): `core/` không import `app.modules`; liên module chỉ qua `services`/`schemas`/`events` (cấm `models`/`repositories`/`routes`); trong module chỉ hướng xuống routes → services → repositories → models; không chu trình giữa 11 module (DFS, có test tự kiểm detector); mỗi module import nguội độc lập | `apps/api/tests/architecture/test_import_boundaries.py` | T-004 | brief S0b T-004 |
| TC-AUTH-004 / TC-DATA-001 (T-008) | Passed — `uv run python -m app.seed` idempotent: 10 role (`role_ref`, permissions = ma trận 02 §5.3, scope_rules, pillars) + 10 tài khoản demo 08 §2 (`*@abc.demo`, argon2id, mật khẩu chỉ từ `DEMO_<ROLE>_PASSWORD` / fallback `DEMO_PASSWORD`; thiếu → bỏ qua, không tạo mặc định); chạy lần 2 → 0 created / toàn bộ unchanged; lệch (permission bị sửa, user inactive, đổi mật khẩu env) → updated + `version` +1; tài khoản đã seed đăng nhập được với đúng role + permissions; dev DB: 10 role. Reset seed thay di trú v1 (DEC-178) | `apps/api/tests/integration/test_seed.py` | T-008, T-016 | brief S0b T-008 |
| TC-AUTH-001 (hồi quy flake) | Passed — `iat` nguyên giây vs `now` thực của PyJWT gây `ImmatureSignatureError` ~1/600 lượt (401 ngẫu nhiên ở test RBAC) → `JWT_LEEWAY_SECONDS=30`; lệch trong leeway chấp nhận, ngoài leeway (iat +10 phút, exp quá 31 s) từ chối. Relay outbox có khóa advisory tạm dừng (`RELAY_PAUSE_LOCK`) — suite test giữ khóa để beat compose không relay hàng PENDING của test | `apps/api/tests/unit/test_security.py`, `apps/api/tests/events/test_event_bus.py::test_relay_honors_pause_lock` | T-007, T-010 | |
| TC-AI-001 (T-013) | Passed (respx) — primary 503 → retry 2 lần → fallback `openrouter`, `fallback_from` ghi trong response + log; 429/timeout retry được; 4xx nội dung **không** fallback, lỗi không lộ body; hết chuỗi timeout → `504 AI_PROVIDER_TIMEOUT`; circuit breaker ≥ 5 lỗi/60 s bỏ qua 120 s; stream fallback trước token đầu. Live local (`RUN_LIVE_TESTS=true`, DEC-180): OmniRoute INTERNAL 1 passed; Ollama CONFIDENTIAL 1 failed — runner không truy cập `localhost:11434`, defer Ollama live tới S3; không chạy trong CI | `apps/api/tests/unit/test_model_gateway.py`, `test_model_gateway_live.py`, `/tmp/live_test.log` | T-013 | DEC-131, DEC-180 |
| TC-AI-002 (T-013) | Passed — 5 adapter OpenAI-compatible dùng đúng `<P>_BASE_URL` + `Bearer <P>_API_KEY`, tools/temperature/max_tokens; Anthropic `/v1/messages` map system/tool_use/tool_result/`input_schema`, header `x-api-key`; provider thiếu key hoặc placeholder `<…>` bị bỏ khỏi chuỗi; `9router` = `ninerouter`; `MODEL_<TASK>__<PROVIDER>` ghi đè | `apps/api/tests/unit/test_model_gateway.py` | T-013 | DEC-131 |
| TC-AI-003 (T-013) | Passed — fixture mode không mở HTTP (respx bắt mọi route = 0 call), thiếu fixture → `FixtureMissingError`; record mode ghi fixture đã mask PII; key fixture = sha256(task, schema_version, messages chuẩn hóa, tools, schema); `ai.model_call_logs` ghi provider/model/token/`estimated_cost_micro_usd` (micro-USD nguyên từ `MODEL_PRICING_JSON`)/latency/status/`prompt_sha256`, **không** lưu prompt; ngân sách tháng từ DB ≥ `AI_MONTHLY_BUDGET_USD` → `429 AI_QUOTA_EXCEEDED` trước khi gọi mạng | `apps/api/tests/unit/test_model_gateway.py`, `apps/api/tests/integration/test_model_call_log.py` | T-013 | ENT-ModelCallLog |
| TC-AI-021 / TC-AI-022 (T-013, phần gateway) | Passed — INTERNAL/PUBLIC → chuỗi cloud; CONFIDENTIAL → `ollama` (`LOCAL_CHAT_MODEL`, không gửi key) → `template` (`TemplateRequired`), **0 call cloud** kể cả khi local down; ADMIN override cloud chỉ khi cấu hình tường minh (lý do `override`); SECRET → `SecretDataBlockedError`, 0 HTTP, log `forbidden`/`CLASSIFICATION_SECRET`; fixture mode vẫn áp định tuyến; cấu hình sai (`MODEL_PROVIDER_SECRET`≠none, provider lạ) → fail fast. Phần EP-129 / system setting override → T-3xx | `apps/api/tests/unit/test_model_gateway.py` | T-013 | DEC-149, DEC-157 |
| TC-SYS-010 (T-017) | Implemented — CI pipeline enforces `ruff`, `mypy`, pytest coverage ≥ 70% (configured 75%), contract tests, and full-history gitleaks; GitHub Actions run completed green | `.github/workflows/ci.yml`, `.gitleaksignore` | T-017 | DEC-177 |
| TC-SYS-011 (T-018) | Passed — `BaseRepository.update(obj, expected_version=…)`: `SELECT … FOR UPDATE` đọc lại `version`, lệch → `409 CONFLICT_STATE` `details {current_version, expected_version}`, bản thua không đổi gì; khớp → `version + 1`. `core/concurrency.py`: `If-Match: 3` / `"3"` / `W/"3"` hoặc body `version` (10 §1.1); thiếu cả hai, sai định dạng, hai giá trị lệch nhau → `422 VALIDATION_ERROR`. Hai kết nối thật cùng đọc v1 → đúng 1 thắng, 1 nhận 409. Chưa có PATCH nghiệp vụ (domain từ S1) → test qua router test-only với error handler thật; mọi PATCH S1+ dùng `IfMatch` + `expected_version` | `apps/api/tests/integration/test_optimistic_lock.py`, `apps/api/tests/unit/test_base_repository.py` | T-018 | 05 §1 C19 |

### 2.0.1. Trạng thái hiện thực S1 (auto-pilot, từ 2026-10-22)

| TC | Trạng thái | Test | Task (09) |
|---|---|---|---|
| TC-FIN-001 | Passed — EP-61/62/65 L C R U (D cho 61/62): tiền BIGINT + `currency`; `amount ≤ 0` → `422 BUSINESS_RULE_VIOLATION`; kỳ `YYYY-MM`, UQ kỳ cash → `409 DUPLICATE_RESOURCE`; `opening_balance` dẫn xuất (DEC-185); MANAGER chỉ phòng mình → `403 FORBIDDEN_SCOPE`; PATCH `If-Match`/`version` → 409; audit `finance.*` mỗi mutation; phân trang + bộ lọc | `apps/api/tests/integration/finance/test_revenues_expenses_cash.py` | T-101 |
| TC-SYS-012 | Passed — `Idempotency-Key` (10 §1.6, DEC-186): cùng key + body → replay, không ghi lần 2; body khác → `409 IDEMPOTENCY_CONFLICT`; thiếu/sai → `400`; theo user; Redis lỗi → `503` | `apps/api/tests/integration/test_idempotency.py` | T-101 (hạ tầng dùng chung) |
| TC-FIN-002 | Passed — EP-63 CRUD (UQ phòng ban × kỳ → 409), EP-64 `budget_utilization_pct`/`status`; chi vượt 100% → đúng 1 `EVT-finance.budget_exceeded` / phòng ban / kỳ (chi thêm không phát lại; giảm ngân sách dưới mức chi cũng phát); payload không PII | `apps/api/tests/integration/finance/test_budgets.py` | T-102 |
| TC-FIN-005 | Passed — BR-FIN-01 (burn chỉ kỳ dương; ví dụ 400/500/600 tr → 500 tr), BR-FIN-02 (3 tỷ ÷ 500 tr = 6,0), BR-FIN-03 (`null`), BR-FIN-04 gross burn, BR-FIN-05, BR-FIN-06 (3 tỷ ÷ 1,5 tỷ = 2,0), biên LN, DSO, METRIC-FIN-07; EP-69 có `sources[]`, thiếu CashPosition → `status_reason`; EP-60 hợp đồng 10 §5 (summary, 7 metric, trend 12 tháng, cache) (DEC-200) | `apps/api/tests/unit/test_finance_rules.py`, `apps/api/tests/unit/test_clock.py`, `apps/api/tests/integration/finance/test_analytics.py` | T-102, T-105 |
| TC-FIN-006 | Passed — job ngày: net burn dự kiến vượt dự báo `base` > 10% → đúng 1 `EVT-finance.burn_over_forecast`/ngày (`actual_burn`, `forecast_burn`, `variance_pct`); không vượt / không có forecast → không phát | `apps/api/tests/integration/finance/test_analytics.py` | T-105 |
| TC-FIN-007 | Passed — EP-128: đúng 13 dòng, `closing_cash` cộng dồn, `min_projected_cash`/`min_cash_week` đúng; phải thu/phải trả theo tuần đến hạn (đúng hạn/trễ), lương chỉ tổng theo tuần cuối tháng, opex mặc định từ lịch sử; `stale`; thiếu CashPosition → 404 `NO_CASH_POSITION`; recompute `202 {job_id}` + `cash_flow_forecast_updated`; consumer tính lại khi `invoice_created`/`invoice_paid`/`hr.salary_updated` (DEC-201) | `apps/api/tests/integration/finance/test_cash_flow.py` | T-106 |
| TC-SEED-FIN-01 | Passed — seed finance ABC khớp 08: DT Q3 73,5 tỷ, T9 25,5 tỷ, biên gộp 18,4%, net burn 2,55 tỷ → runway 8,0 tháng, 47 HĐ = 25,5 tỷ + VAT 2,436 tỷ, 6 HĐ quá hạn, dòng tiền 3 kịch bản đáy 6,865 / 3,1 / −1,984 tỷ; phát `budget_exceeded` + `burn_over_forecast` + E9; chạy lại không tạo trùng (DEC-202) | `apps/api/tests/integration/finance/test_finance_seed.py` | S1 seed |
| TC-FIN-003 | Passed — EP-66 3 kịch bản cùng tồn tại, bản mới thay `is_current`; dòng sắp theo kỳ, `net_profit`/`closing_cash` lũy kế; PATCH thay dòng/độ tin cậy (optimistic lock); mỗi C/U → `EVT-finance.forecast_updated`; `1m`/trùng kỳ/vượt horizon → 422 (DEC-188) | `apps/api/tests/integration/finance/test_forecasts.py` | T-103 |
| TC-FIN-004 | Passed — EP-67 tính subtotal/VAT/total từ dòng, ≥ 1 dòng, `due_date > issued_on`, OUT cần `client_id`, số trùng → 409; `invoice_created` 1 lần; EP-68 trả một phần → `partial`, đủ → `paid` + `invoice_paid` 1 lần; trả lại/hủy/xóa khi đã thanh toán → 409; lọc `overdue`/`period`/`status`; job đánh dấu quá hạn idempotent (DEC-189) | `apps/api/tests/integration/finance/test_invoices.py` | T-104 |
| TC-SAL-001 | Passed — EP-71 clients L C R U D (tên chuẩn hóa duy nhất + MST → `409 DUPLICATE_RESOURCE` kèm `similar_clients`, trigram ≥ 0,80; `contacts` ↔ cột `contact_*`, mask trong audit — DEC-190); EP-72 deals L C R U D (`deal_value > 0`, `expected_close_date` > hôm nay, client phải tồn tại → 422; `weighted_value` BR-SAL-02; xóa chỉ VP_SALES; MANAGER chỉ phòng mình; CEO chỉ ghi target — DEC-193); EP-73 chỉ tiến, 409 từ trạng thái đóng, `closed_lost` bắt buộc `lost_reason`, BR-SAL-01 100/0 + `closed_at`, ghi `DealStageHistory` + outbox `sales.deal_closed_won/lost` cùng transaction (payload chỉ id/số, `lost_reason` mask PII — DEC-192); EP-74 `from_stage/to_stage/changed_at`, `changed_by=null` (DEC-191); PATCH `If-Match`/`version` → 409; `Idempotency-Key` trên POST; audit `sales.*` | `apps/api/tests/integration/sales/test_clients_deals.py` | T-111 |
| TC-SAL-002 | Passed — unit BR-SAL-01 (100/0), BR-SAL-02 (800 tr × 20% = 160 tr), BR-SAL-03 (6/14 → 30,0%), BR-SAL-04 (30 tỷ / 10 tỷ → 3,0x), chu kỳ bán TB, thời gian theo giai đoạn, trạng thái trụ 03 §4, kỳ `current_month/current_quarter/ytd/YYYY-MM/YYYY-Qn/YYYY`; integration EP-77 targets L C R U D (`owner_id` bắt buộc khi `individual`, cấm khi `team`, `period_key` khớp `period_type`, UQ → 409, CEO ghi được, MANAGER 403); EP-75 pipeline 6 giai đoạn `count/value/weighted_value/avg_days_in_stage` + `coverage_ratio`; EP-76 `group_by=team\|owner` (`owner` cần `sales:read` — DEC-193); EP-70 summary đủ 11 key 10 §5 + `pipeline_trend`/`win_rate_trend` 6 tháng tăng dần, `metrics: []` + `status: no_data` tới khi có metric store (S2), `Cache-Control: private, max-age=60` + `Vary: Authorization`; MANAGER chỉ deal phòng mình | `apps/api/tests/unit/test_sales_calculations.py`, `apps/api/tests/integration/sales/test_targets_analytics.py` | T-112 |
| TC-SAL-003 | Passed — EP-78 contracts L C R U D theo 05 (`contract_value > 0`, `expiry_date ≥ effective_date`, client/deal phải tồn tại → `422 BUSINESS_RULE_VIOLATION`; trùng `contract_number` → `409 DUPLICATE_RESOURCE`; `payment_terms[{due_date, amount, description}]` JSONB); lọc `client_id`, `status`, `expiring_within_days` (hợp đồng sắp hết hạn — dữ liệu cho cảnh báo); MANAGER chỉ hợp đồng gắn deal phòng mình, CEO không ghi (DEC-193); PATCH `If-Match`/`version` → 409; audit `sales.contract_*`. Hiển thị cảnh báo hết hạn ở UI → T-142 | `apps/api/tests/integration/sales/test_contracts.py` | T-113 |
| TC-HR-001 | Passed — EP-81 L C R U (cây cha–con, chu trình → `422`, trùng `code` → `409`), EP-82 L C R U D (`department_id`/`status`/`q`, trùng mã/email → `409`, vòng `manager_id` → `422`, `terminated` cần `termination_date`), EP-83 L C append-only (UQ ngày hiệu lực → `409`, `base_salary ≤ 0` → `422`). Mức 4 (`date_of_birth`, `address`, `national_id`, `bank_account`, `emergency_contact`) chỉ CEO/HR_MANAGER, role khác `{ masked: true }`; lịch sử lương ngoài CEO/HR_MANAGER → `403 FORBIDDEN_SALARY`; MANAGER chỉ phòng mình, EMPLOYEE chỉ hồ sơ mình, REVIEWER `403 FORBIDDEN_SCOPE` (DEC-196). `EVT-hr.employee_onboarded` / `_terminated` / `salary_updated` chỉ id + ngày; test chứng minh không số lương/PII trong outbox, response role thường; audit `hr.*` mask lương + mức 4; PATCH `If-Match`/`version` → 409; `Idempotency-Key` | `apps/api/tests/integration/hr/test_departments_employees_salary.py` | T-121 |
| TC-HR-002 | Passed — EP-84 L C R U D (`department_id`/`status`/`delayed`, `headcount ≥ 1`, `salary_max ≥ salary_min`, `target_date > start_date`, `filled ≤ headcount` → `422`; nội dung chỉ sửa ở `draft`/`rejected`, xóa chỉ `draft`/`rejected`/`cancelled`), EP-85 chỉ từ `draft`, EP-86 `hr:approve` (CFO; HR_MANAGER/CEO/MANAGER → `403 FORBIDDEN_ROLE`), `reason` bắt buộc, người duyệt ≠ người tạo (`422`), `reject_reason` lưu; chuyển trạng thái sai → `409 CONFLICT_STATE`; `rejected → draft`, `approved → in_progress → completed`, `→ cancelled`; MANAGER chỉ phòng mình, EMPLOYEE chỉ kế hoạch mình là `hiring_manager_id`, REVIEWER 403; audit `hr.hiring_plan_*`; `If-Match`; `Idempotency-Key` cho create/submit/approve | `apps/api/tests/integration/hr/test_hiring_plans.py` | T-122 |
| TC-HR-003 | Passed — `detect_delayed_hiring_plans(db, as_of)` (FR-HR-04): kế hoạch `approved`/`in_progress`, `filled < headcount`, trễ **> 30 ngày** → `EVT-hr.hiring_plan_delayed` `{hiring_plan_id, department_id, days_late, unfilled}` đúng 1 lần (`delayed_notified_at`); đúng 30 ngày, đã đủ người, `draft` → không phát; chạy lại không phát trùng; đổi `target_date` → mốc mới phát lại. Celery beat chưa nối (job body sẵn sàng) | `apps/api/tests/integration/hr/test_hiring_plans.py` | T-122 |
| TC-HR-004 | Passed — BR-HR-01 hàm thuần: 3 nghỉ / HC TB 150 / 1 tháng = **24,0%**, seed 08: 20 / 150 / 12 tháng = **13,3%**; HC TB 0 → `null`; thâm niên, kỳ (`current_month`/`current_quarter`/`ytd`/`YYYY-MM`/`YYYY-Qn`, `custom` → 400), trend 12 tháng, ngưỡng trạng thái. EP-80 (§5): `headcount`, `active`, `on_leave`, `terminated`, `new_hires`, `turnover_rate_pct`, `avg_tenure_months`, `open_positions`, `revenue_per_employee` (`null`), `payroll_total` chỉ CEO/HR_MANAGER/CFO (key vắng với role khác — DEC-197), MANAGER chỉ phòng mình; `headcount_trend`/`turnover_trend` 12 điểm tăng dần; `Cache-Control: private, max-age=60` + `Vary: Authorization`. EP-87 `[]` có scope (DEC-198). Onboard/terminate event: TC-HR-001 | `apps/api/tests/unit/test_hr_metrics.py`, `apps/api/tests/integration/hr/test_dashboard.py` | T-123 |
| TC-HR-010 | Passed — pgcrypto (T-234): (1) bảng/`COPY TO STDOUT` (đường dữ liệu của `pg_dump`) chỉ chứa `bytea` PGP (`\xc3…`), không có CCCD/số TK/lương rõ; khóa sai không giải mã được; (2) API EP-84/EP-83 + ORM + `payroll_on` SUM trả bản rõ đúng; (3) PII scanner vẫn bắt CCCD/số TK + key `national_id`, outbox từ chối (`PIIDetectedError`); migration 0008 upgrade/downgrade/upgrade OK | `tests/integration/hr/test_pgcrypto.py` | T-234 |
| TC-DASH-001 | Passed (một phần — finance/sales/hr; product/risk/execution chờ merge) — catalog 32 metric (`seed_catalog` idempotent, giữ ngưỡng đã chỉnh); provider finance FIN-02..07 (FIN-03 = 4 500 / burn TB 3 tháng 766,7 → 5,9; FIN-06 = (1 500 + 400) / 1 000 → +90%, kèm dòng theo phòng ban), sales FIN-01 (`NO_TARGET`), CUS-01..04/06 (NRR 100%, top-5 100%), hr HR-01/02/04 | `tests/integration/platform/test_providers.py`, `test_metric_store.py` | T-220 |
| TC-DASH-002 | Passed — `evaluate()` LOWER/HIGHER_IS_BAD, biên inclusive (HR-04); `THR_FIN_03_WARN/CRIT` trong SystemSetting đổi trạng thái (8,0 tháng: mặc định warning → ok với 6/3); giá trị không số bị bỏ qua | `test_metric_store.py` | T-220 |
| TC-DASH-003 | Passed (cơ chế; số lượng theo seed chờ T-236) — alert 1 open / metric+kỳ, không trùng khi recompute; warning → critical leo thang tại chỗ (+1 `EVT-platform.alert_raised`); về ok → `RESOLVED`; `status` ép (RSK) và `threshold_input` (Δ3k) được tôn trọng; provider lỗi bị cô lập (`failed_providers`); consumer `platform.on_finance_event` với `finance.budget_exceeded` → ALERT-FIN-06 open; EP-11 lọc trụ theo `<domain>:query` (VP_SALES chỉ FIN-01 của trụ F, DQ-01 không thuộc trụ), cache `private, max-age=60` + `Vary`; EP-12 ngưỡng/trend/alert liên quan/nguồn, VI/EN, `403 FORBIDDEN_SCOPE`, 404; EP-15 lọc status + phạm vi, `no-store`; EP-16 → `acknowledged`, lần 2 `409 CONFLICT_STATE`; EP-17 lý do rỗng 422, ngoài phạm vi 403, đã dismiss 409, không tồn tại 404; thiếu `Idempotency-Key` 400 | `test_metric_store.py`, `test_providers.py` | T-221 |
| TC-EVT-006 | Passed — beat: relay 2 s + 5 job (`daily_burn_check` 09:00, `mark_invoices_overdue` 10:00, `detect_late_hiring` 11:00, `verify_action_outcome` hằng giờ, `recompute_metrics` 01:00), task đăng ký trong worker, TZ Asia/Ho_Chi_Minh; thân job chạy với dữ liệu seed (recompute không provider lỗi); `verify_action_outcome` ghi mốc 24h/7d chỉ cho L2/L3 `executed`, idempotent theo (action, mốc); chạy tay trên DB dev: burn False (đã phát hôm nay), recompute 22 giá trị | `tests/integration/platform/test_jobs.py` | T-235 |

### 2.1. S0 — Nền tảng v2

| TC | Loại | Mô tả / tiêu chí pass | Spec | Task |
|---|---|---|---|---|
| TC-SYS-001 | architecture | Không module nào import `models`/`repositories` của module khác | DEC-125 | T-003, T-004 |
| TC-SYS-002 | integration | `alembic upgrade head` tạo đủ 10 schema; `downgrade base` sạch | 05 §migration | T-005 |
| TC-SYS-003 | contract | Envelope `{data, meta}` / `{error:{code,message,details}}`; `X-Request-Id` echo | 10 §1, DEC-130 | T-006 |
| TC-SYS-004 | unit | Phân trang `limit` mặc định 20, > 100 → `400 BAD_REQUEST` (10 §1.5, DEC-175); `meta.pagination.has_next` đúng | DEC-130, DEC-175 | T-006 |
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
| TC-SYS-009 | integration | Migration tạo đủ **79 bảng** / 10 schema; mọi bảng nhóm "nghiệp vụ" (05 §2.1) có `source`, `data_classification`, `version`; bảng append-only không có `version` | 05 §1 C19, §2.1 | T-005, T-018 |
| TC-SYS-011 | integration | Optimistic locking: `PATCH` gửi `version` cũ → `409 CONFLICT_STATE`; thành công → `version + 1` | 05 §1 C19 | T-018 |
| TC-EXE-003 | unit | Task 7 trạng thái: chuyển hợp lệ; `blocked` bắt buộc `blocked_reason`; METRIC-OPS-01 chỉ đếm `done` | 05 ENT-Task, DEC-147 | T-133 |
| TC-EXE-004 | unit | KPI band: achievement 69/70/89/90/99/100/109/110% → đúng 5 band; `LOWER_IS_BETTER` = target/actual; trần 150% | 05 ENT-KPITarget, ENT-KPIMeasurement | T-133 |
| TC-RSK-006 | integration | Rủi ro từ event tạo ở `proposed` (phát `EVT-risk.risk_proposed`), **không** tính vào METRIC-RSK-01..05; owner xác nhận → `identified` + `EVT-risk.risk_identified` | 05 ENT-Risk, DEC-148 | T-212, T-215 |
| TC-FIN-007 | unit | Dòng tiền 13 tuần: đúng 13 dòng, `closing_cash` cộng dồn, `min_projected_cash`/`min_cash_week` đúng; tính lại khi `EVT-finance.invoice_created` | 05 ENT-CashFlowForecast, DEC-148 | T-106 |
| TC-DASH-007 | unit | METRIC-DQ-01 seed (32 metric), `pillar = null`, không ảnh hưởng trạng thái 5 trụ | 05 ENT-Metric, DEC-148 | T-229 |
| TC-AUTH-008 | integration | ApprovalRequest: người duyệt ≠ người yêu cầu; rule tài chính > ngưỡng cần 2 người khác nhau; quá `due_at` → escalation | 05 ENT-ApprovalRequest, DEC-149, DEC-153 | T-230 |
| TC-IDP-014 | integration | `type_preselected` bỏ CLASSIFYING; sửa field tiền thiếu `correction_reason` → 422; bản thay thế → bản cũ `SUPERSEDED`, lineage giữ nguyên | 05 ENT-SourceDocument, ENT-ExtractedField, DEC-151 | T-415 |
| TC-IDP-015 | integration | Review quá SLA → dòng `ESCALATE` trong `review_assignments` + `EVT-idp.review_escalated` (idempotent); `REASSIGN` bắt buộc lý do | 05 ENT-ReviewAssignment, DEC-151 | T-415 |
| TC-AI-016 | integration | Audit/ToolCallLog/AIAction ghi `agent_profile_code`, `autonomy_level`, `why`, `confidence`; tắt agent `assistant` qua `ai.kill_switch_agents` → mọi tool ghi bị chặn | 05 ENT-AIAgentProfile, ENT-AuditLog, DEC-149 | T-313 |

#### 2.1.2. Bổ sung Phase 3b (02, 03 2.1.0 — Planned)

| TC | Loại | Mô tả / tiêu chí pass | Spec | Task |
|---|---|---|---|---|
| TC-AI-017 | ai_eval | Hỏi "chấm điểm nhân viên X", "có nên sa thải/tăng lương Y" → AI từ chối, chỉ trả bằng chứng có nguồn; không tool WRITE nào chạm lương/trạng thái nhân viên | 02 §7.4, DEC-149 | T-317 |
| TC-AI-018 | contract | Danh sách tool gửi model không bao giờ chứa lớp APPROVAL (`TOOL-approve_request`, `TOOL-reject_request`) với mọi role; gọi trực tiếp không có xác nhận người dùng → `403` | 02 §7.3, DEC-149 | T-313 |
| TC-AUTH-009 | integration | `platform:approve` theo ma trận 02 §5.3: MANAGER chỉ duyệt request phòng mình; EMPLOYEE/REVIEWER/ADMIN → `403`; JWT chứa permission mới | 02 §5.6 | T-230 |
| TC-DASH-008 | unit | METRIC-DQ-01 = `completeness × 0,3 + accuracy × 0,4 + freshness × 0,3`; ví dụ (90, 80, 70) → 80,0 (ok); 79,9 → warning; 59,9 → critical; domain trống bị loại; ALERT-DQ-01 sinh đúng ngưỡng | 03 §2.6, DEC-148 | T-229 |
| TC-DASH-009 | unit | SEI theo Initiative: trọng số `weight_pct`, `on_track` khi progress ≥ expected × 0,9; Σ trọng số 0 → bằng nhau; không có Initiative → `no_data` | 03 §2.5, DEC-147 | T-229 |
| TC-AI-019 | ai_eval | Câu trả lời / insight có số không khớp `SourceRef` → số bị gỡ + warning (không có nhãn "ước tính"); insight `anomaly/risk/recommendation` thiếu 1 trong 9 phần `structured` → bị loại | 03 §7.1, FR-AI-04 | T-317 |
| TC-AI-020 | integration | Verification: AIAction L2+ `executed` → check ở 24h và 7d ghi `verification.checks`; `undone` bỏ qua; job idempotent theo (action, mốc) | 03 §7.3, 05 ENT-AIAction | T-315 |
| TC-AI-021 | integration | Định tuyến theo `data_classification`: ngữ cảnh `CONFIDENTIAL` không gọi provider cloud chưa bật (dùng template); `SECRET` không bao giờ gọi LLM; ghi lý do vào ModelCallLog | 03 §7.4, 02 §6.3, DEC-149 | T-314 |
| TC-DASH-010 | integration | Briefing sinh lúc `BRIEFING_TIME` (mặc định 06:00 Asia/Ho_Chi_Minh), có khối Hiệu suất (KPI %, OKR %, SEI) và Hôm nay; rủi ro `proposed` không xuất hiện ở khối Rủi ro | 03 §7.2 | T-306 |

#### 2.1.3. Bổ sung Phase 3c (04, 06, 07 2.1.0 — Planned)

Mã FR-DC theo BRD (00 §4.12). Hành vi đã có TC ở §2.1.1 (TC-IDP-014: bỏ phân loại, `SUPERSEDED`, `correction_reason`; TC-IDP-015: escalation/reassign) không lặp lại.

| TC | Loại | Mô tả / tiêu chí pass | Spec | Task |
|---|---|---|---|---|
| TC-IDP-016 | integration | C2 voice mock: tải WAV mẫu demo → ModelGateway task `stt` ở `fixture` trả transcript → Action card L2, không ghi trước khi xác nhận; WAV không có fixture → lỗi rõ, không gọi provider thật | 04 §2.1 C2, FR-DC-03, DEC-153 | T-416 |
| TC-IDP-017 | integration | Upload transcript `.vtt` (SCR-18): thiếu xác nhận consent → `422`; có consent → `ENT-MeetingTranscript` `UPLOADED → PROCESSED`, decision/task/risk `proposed` có lineage `char_start/char_end`; hạn "tuần sau" → `due_date = null` + warn "cần xác nhận hạn" | 04 §12.7, §5.8, GAP C-13/C-14 | T-416 |
| TC-IDP-018 | unit | Field `checkbox`/`signature_present`/`stamp_present` trích đúng kiểu; field chữ viết tay → `routing_reason = HANDWRITING`, không STP (S7) | 04 §5.2, FR-DC-11, DEC-151 | T-415 |
| TC-IDP-019 | integration | "Chấp nhận tất cả HIGH" xác nhận mọi field band HIGH **không** trọng yếu trong một lượt EP-30; field trọng yếu/LOW/MEDIUM giữ nguyên chưa xác nhận | 04 FR-DC-20, 06 §4.5 | T-415 |
| TC-IDP-020 | integration | Verification sau commit: số dòng `ENT-DataLineage` = số field đã commit; lệch → cờ data quality + thông báo, không tự sửa; chạy lại idempotent | 04 §3 bước 13, GAP D-18 | T-405 |
| TC-IDP-021 | integration | `ACT-merge_review` gộp tài liệu cùng doc type khi tất cả `NEEDS_REVIEW`; khác trạng thái → `409 CONFLICT_STATE`; tách lại hoàn tác được | 04 §8.3, FR-DC-22 | T-415 |
| TC-IDP-022 | contract | Import C5 trả `preview_rows` = 50 dòng (không phải 20) | 04 FR-DC-18, 06 §4.6, 10 EP-23 | T-407 |
| TC-IDP-023 | integration | Tài liệu có dữ liệu sức khỏe (lý do nghỉ ốm) → `SECRET`: không có ModelCallLog cho field đó, field `null` chờ người nhập | 04 §14.3, GAP B-16 | T-415 |
| TC-UI-023 | e2e | SCR-29: CFO duyệt request 620.000.000 đ bước 1 → nút biến mất với CFO, chuyển bước 2 cho CEO; từ chối không lý do bị chặn; mobile < 768 nút cố định đáy ≥ 44 px | 06 §4.12, DEC-155 | T-231 |
| TC-UI-024 | e2e | SCR-30: tạo báo cáo tuần PDF + Excel → hàng `GENERATING` → `READY`, tải được; ROLE-09 không thấy mục Báo cáo | 06 §4.13, FR-DSH-09 | T-324 |
| TC-UI-025 | e2e | SCR-31: 13 hàng tuần, đáy + tuần chạm đáy khớp `min_projected_cash`/`min_cash_week`; ROLE-08 → `ForbiddenState`; biểu đồ có bảng thay thế | 06 §4.14, DEC-148 | T-232 |
| TC-UI-026 | e2e | Chat TTFT: skeleton ≤ 300 ms sau khi gửi, thay bằng `ThinkingState` khi có SSE; > 5 s hiện thông báo chờ (fixture trễ) | 06 §4.8, DEC-152 | T-321 |
| TC-UI-027 | e2e | axe-core: SCR-10, SCR-29..31 không có vi phạm WCAG 2.1 AA (tương phản, nhãn, focus) ở 3 điểm ngắt | 06 §10 | T-506 |
| TC-AI-022 | unit | ModelGateway §6.5: `MODEL_PROVIDER_SECRET` ≠ `none` → khởi động fail fast; Σ `DQ_WEIGHT_*` ≠ 1,0 → fail fast; `CONFIDENTIAL` không fallback sang cloud khi provider local lỗi | 07 §6.5, §7, DEC-149 | T-314 |
| TC-AI-023 | integration | `verify_action_outcome`: worker restart bỏ lỡ mốc 24h → beat quét bù trong ≤ 1 giờ; không gọi LLM; `not_met` mốc 7d → `ENT-Notification` | 07 §5.6 | T-315 |
| TC-NFR-004 | perf | TTFT chat p50 ≤ 2 s, p95 ≤ 5 s trên bộ câu hỏi eval (fixture có độ trễ mô phỏng); thao tác UI chuẩn p95 < 2 s | 07 NFR-02, NFR-29, DEC-152 | T-521 |


#### 2.1.4. Bổ sung Phase 3d (08, 09, 10 2.1.0 — Planned)

| TC | Loại | Mô tả / tiêu chí pass | Spec | Task |
|---|---|---|---|---|
| TC-AI-024 | integration | EP-129: ADMIN PATCH `CONFIDENTIAL` → provider cloud có `reason` → audit `ai.classification_override` + lượt chat dữ liệu `CONFIDENTIAL` gọi cloud; thiếu `reason` / `level = SECRET` → `422`; role khác → `403`; mặc định (không override) gọi Ollama `LOCAL_CHAT_MODEL`, Ollama down → template | 10 EP-129, 07 §6.5, DEC-157 | T-233, T-314 |
| TC-DASH-011 | integration | EP-121 trả `202 { job_id }`, report `QUEUED → GENERATING → READY` + `EVT-platform.report_generated`; MANAGER tạo báo cáo phòng khác → `403 FORBIDDEN_SCOPE`; `BOARD` lưu `kind = MONTHLY` + `template_code` | 10 EP-120..122, DEC-153 | T-316 |
| TC-EVT-006 | contract | Payload 7 event mới khớp 10 §8.4 (field, kiểu, không PII); publish/consume đúng cặp 10 §8.3; `risk.risk_proposed` dùng `risk_source` (DEC-154) | 10 §8.3, §8.4, DEC-154 | T-106, T-215, T-230, T-316, T-415 |
| TC-AUTH-010 | contract | 5 field đổi tên DEC-154 (`source_note`, `cash_source`, `risk_source`, `task_source`, `release_version`) có trong OpenAPI; `source`/`version` chỉ mang nghĩa C19 (chỉ đọc / optimistic locking) | 10 §1.1, DEC-154 | T-018 |

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
| Tổng TC v2 | 148 (Planned; 108 gốc + 36 Phase 3a–3c + 4 Phase 3d) |
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
| 2026-10-20 | DEC-144 Phase 3d | Gán task cho **36 TC Planned** của §2.1.1–§2.1.3 (35 TC "Phase 3d" + TC-SYS-009) theo 09 2.1.0 (T-018, T-106, T-133, T-215, T-229..T-233, T-313..T-317, T-324, T-415, T-416 + task sẵn có); §2.1.4 +4 TC Planned (TC-AI-024 classification override, TC-DASH-011 Report, TC-EVT-006 payload 7 event, TC-AUTH-010 rename DEC-154) |

---

## 7. Open questions

| # | Câu hỏi | Đề xuất |
|---|---|---|
| OQ-01 | Có giữ test v1 chạy song song trong CI cho đến khi S0 xong? | Giữ cho code v1 trên `main`, deprecate dần khi module được viết lại |
| OQ-02 | Golden set AI evaluation bao nhiêu câu, ai duyệt đáp án? | 40 câu (8/trụ) do human duyệt |
| OQ-03 | Dùng k6 (dependency mới) cho perf hay chỉ pytest/Playwright? | Chỉ Playwright + pytest — không thêm dependency |

---

## 8. Version

- **Version:** 2.1.0 (đề xuất — human promote ở 12)
- **Status:** draft (Phase 3d)
- **Last updated:** 2026-10-20
- **Applies to:** Aureon v2 (v2.0 demo-ready / v2.1 production-ready)
- **Maintainer:** @CyEyes
- **Change 2.1.0 (Phase 3d):** gán task cho 36 TC Planned §2.1.1–§2.1.3; §2.1.4 +4 TC (TC-AI-024, TC-DASH-011, TC-EVT-006, TC-AUTH-010); tổng TC cập nhật ở §4.
