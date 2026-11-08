# Audit kiến trúc Aureon (read-only) — 2026-11-05

Phạm vi: `apps/api` (55k LOC, 11 module, 27 migration (đề bài ghi 28 là tính cả `__pycache__`), 328 route), `apps/web` (30k LOC, 423 file TS/TSX), compose, CI, DB live (catalog). Đối chiếu CLAUDE.md §4–§5 và `docs/3.EXECUTION/07-TECH-ARCHITECTURE.md`.

**Không sửa repo.** Không đọc `.env`, `keys/`, `secrets/`. Không chạy pytest và không chạy `alembic check`. Script tự viết để trong `/tmp/claude-1000/-home-vika-Aureon/2b13532a-4cf7-4113-90e3-1f149a3f8ac1/scratchpad/s/`. Introspect route chạy trên bản copy source ở đó (REPO_ROOT khác nên app không nạp `.env`).

Đánh dấu bằng chứng: **[S]** = script/catalog/lệnh, **[Đ]** = đọc code. Mục chưa kiểm chứng ghi **UNVERIFIED** và gom lại ở §13.

---

## 1. Kết luận chính

Nền kiến trúc tốt hơn mức thường thấy với một monolith 55k LOC: ranh giới module sạch, model khớp DB gần tuyệt đối, outbox/consumer đúng bài, ruff + mypy strict sạch. **Rủi ro lớn không nằm ở cấu trúc code mà ở vận hành và ở vài điểm hở cụ thể:**

1. `uv run pytest` không có chốt chặn DB, và test relay có thể nuốt event thật (§9.1).
2. Backend chưa chạy trên CI từ 21/10; `main` không có branch protection (§8.3).
3. Ghi nhận thanh toán hóa đơn có race mất cập nhật tiền (§5.2).
4. `python -m app.seed` chạy ở mỗi lần API khởi động, không có guard (§8.2).
5. Rate limit theo contract chưa được cài (§7.3).
6. Redis không mật khẩu và app dùng Postgres superuser, publish 0.0.0.0 (§8.1).
7. Tài liệu IDP lỗi ngoài `AIError` kẹt vĩnh viễn ở `UPLOADED` (§6.3).
8. NFR-AV-02 (RPO ≤ 15 phút, backup hằng ngày) không có gì thực thi (§8.4).

**Không nên làm:** tách microservice, đổi tên path API, chuyển sang server component, dọn `# fmt: skip`. Lý do ở §12.

### Những gì đã kiểm tra và ĐẠT

| Mục | Kết quả | Bằng chứng |
|---|---|---|
| Import giữa module | 0 vi phạm: không module nào import `models`/`repositories`/`routes` của module khác | [S] `imports.py` |
| Chu trình module | Không có (DAG) | [S] |
| `core/` import `modules/` | 0 | [S] + test |
| Import tương đối vượt module | 0 | [S] grep |
| SQL raw chéo schema | 0 | [S] grep |
| FK chéo schema | 0/123 FK (đúng C7, soft ref) | [S] catalog |
| FK không có index dẫn đầu | **0/123** | [S] catalog |
| Bảng model ↔ DB | 100/100; chỉ dư `_m13_assignee_backfill` và `alembic_version` (có chủ đích) | [S] |
| Cột, nullable, kiểu, precision | 0 lệch (bytea = `crypto_columns`, đúng thiết kế) | [S] |
| Enum | 99/99 khớp nhãn và thứ tự | [S] |
| Check constraint | 77/77 khớp | [S] |
| Migration | 27/27 có `downgrade()` thật | [S] AST |
| Tiền | BIGINT toàn bộ; `numeric` chỉ ở tỷ lệ/measure; `ai.agent_profiles.monthly_budget_usd` là cấu hình USD | [S] |
| Orphan soft ref (5 mẫu) | 0 | [S] |
| Event | 40 type đăng ký; publish đều qua `publish_in_tx`; chỉ `platform.report_generated` không có publisher | [S] |
| Permission | 318/328 route có `require_*`; 10 route còn lại đúng chủ đích (health, auth, notification của chính mình) | [S] |
| Idempotency-Key bắt buộc | 86/91 POST | [S] |
| `os.environ` | Chỉ `config.py` và `scripts/bootstrap_admin.py` | [S] |
| ruff / format / mypy strict | Sạch (389 file) | [S] |
| Audit | 1 route không với tới audit (`POST /notifications/read-all`, không phải mutation nghiệp vụ). Đây là phân tích reachability, có thể bỏ sót | [S] |

---

## 2. Ranh giới module và phụ thuộc

### 2.1. Đồ thị phụ thuộc [S]

```
ai        → auth, dashboard, execution, hr, idp, platform
dashboard → execution, platform
execution → auth, platform
finance   → platform
hr        → execution, finance, platform
idp       → auth, execution, finance, hr, platform
platform  → auth
product   → platform
risk      → finance, hr, platform, sales
sales     → finance, platform
```

`auth` là lá; `idp` phụ thuộc rộng (33 cạnh sang `execution`, 17 sang `hr`) vì Action Registry — chấp nhận được.

### 2.2. `tests/architecture` chưa phủ gì

`test_import_boundaries.py` tốt nhưng có các lỗ:

| Lỗ hổng | Thực tế hiện nay | Lợi ích nếu vá |
|---|---|---|
| Chỉ quét `modules/`; `workers/`, `seed/`, `scripts/`, `main.py` nằm ngoài | `workers/` sạch; `seed/` import thẳng `models` và `repositories` của 8 module (chấp nhận được nhưng không khai báo) | Chặn worker lấn ranh giới về sau |
| Chỉ cấm `core → app.modules` | `core/events/bus.py:72` import lazy `app.worker` (core → tầng ngoài) | Nhỏ |
| Cho phép bỏ tầng (routes → models) | 1 ca: `platform/routes/workflow.py:19` | Nhỏ |
| Không có test SQL chéo schema / FK chéo | Hiện 0 vi phạm, không có gì giữ nó | Rẻ, thêm 1 test catalog |
| `test_tenant_query_boundary` chỉ xét model `TenantMixin` | **48 `select(` nằm trong `idp/services`** qua test vì bảng `idp.*` đó không có `tenant_id` (`commit_service.py` `_latest_job`, `_schema`...). Tổng 69 ở 6 module | Xem TD-19 |
| File ngoài `LAYER_RANK` (`rules.py`, `tools/`, `permission_matrix.py`) không bị kiểm tầng | Hiện không thấy vi phạm | Nhỏ |

### 2.3. Registry trong `core/` để lách chu trình

`core/client_directory.py`, `directory.py`, `org_scope.py`, `approval_hooks.py`, `capture_share.py`, `ai_activity.py`, `onboarding.py` (khoảng 300 dòng) là dependency inversion có chủ đích, đăng ký qua side effect ở `modules/*/__init__.py`.

Rủi ro duy nhất: tiến trình quên import package thì lookup âm thầm trả rỗng. Ví dụ `workers/idp_pipeline.py:22` phải `importlib.import_module("app.modules.ai")` thủ công; `client_directory.py` ghi rõ "without a provider nothing resolves". Nên fail-fast khi chưa đăng ký. Không cần gỡ pattern này.

### 2.4. Chu trình frontend [S]

- Value import: `features/work/ApprovalDetail ↔ ApprovalsView`, `mocks/work ↔ mocks/workflow`.
- Tính cả type import: `shell/Header ↔ AppShell`, `work/TaskInfoForm ↔ TaskDetail`, onboarding steps, cụm 36 file `mocks/`.
- `components/` import ngược `features/` (12 cạnh, như `LineageChip → capture`, `KillSwitchBanner → admin/ai`). `work`, `ai`, `goals` import `admin` 18 cạnh.

Mức thấp, sửa khi chạm tới.

---

## 3. Trùng lặp, code chết, naming

### 3.1. Code chết [S] (heuristic: tên xuất hiện đúng 1 lần trong `src`; đã loại route, task, validator)

| Mục | Vị trí | Ghi chú |
|---|---|---|
| `RateLimitError` | `core/errors.py:106` | Không ai raise — bằng chứng rate limit chưa cài |
| `ExecutionService` | `modules/execution/services/execution_service.py:6` | Docstring nói "public interface" nhưng rỗng và không dùng |
| `department_exists` | `hr/services/hr_service.py:165` | |
| `assumptions_of` | `finance/services/cash_flow_service.py:203` | |
| `agents_for_tool` | `ai/services/agent_catalog.py:103` | |
| `ScenarioRepository` | `risk/repositories/__init__.py:102` | |
| `pillar_card` | `dashboard/services/dashboard_service.py:112` | |
| `as_source_refs` | `idp/services/knowledge_search.py:76` | |
| `delete_summary` | `execution/services/meeting_service.py:466` | |
| Chỉ test dùng | `require_role` (`core/deps.py:131`), `generate_for_pillar`, `sources_as_dict`, `redact_for_log`, `create_summary`, `approver_roles` | `redact_for_log` không được dùng trong prod: kiểm tra có phải bỏ sót che log không |
| `features/dashboard/DashboardView.tsx` | FE | Không có ai import |
| `core/base_service.py` (15 dòng) | | Chỉ 2 tham chiếu |
| Event `platform.report_generated` | `core/events/registry.py` | Không publisher, không consumer |

Bản thân `vulture` không có trong venv.

### 3.2. Trùng lặp có hại thật

- Helper thời gian: `_now` ×7, `today` ×7, `_aware` ×4, `now_utc` ×3, `_audit` ×9, `_uuid` ×3 [S]. `today()` lặp đáng ngại vì `core/clock.business_today()` mới biết demo date: `invoice_service.py:82` gọi `today()`, cần rà từng bản có đi qua clock không. **UNVERIFIED** cho từng bản.
- `_deactivate_assignments` lặp ở `idp/services/commit_service.py` và `review_service.py`; khối kiểm `locked_by/locked_until` lặp ít nhất 4 lần trong `review_service.py` (:425, :620, :647) và `commit_service.py:102`.
- **Mock backend FE**: `apps/web/src/mocks` = 6.266 dòng, là bản cài đặt thứ hai của API. Có giá trị (E2E không cần backend) nhưng phải bảo trì song song; và `app/api/backend/[...path]/route.ts` import tĩnh `@/mocks/router` nên vào cả bundle server production (có guard runtime).
- `/health` (ops) và `/api/v1/health` (EP-01) trùng chức năng, có lý do (contract vs probe). Giữ.

### 3.3. Không phải god service

File lớn nhất: `ai/tools/registry.py` 793, `idp/services/review_service.py` 731, `execution/services/meeting_service.py` 718, `idp/models` 537. FE lớn nhất `RecordCrud.tsx` 350. **Không có file nào cần tách vì kích thước.** Hai module lớn `idp` (10,3k) và `execution` (8,8k) đã chia service theo nghiệp vụ. Không đề xuất.

### 3.4. Naming và drift tài liệu

| Vấn đề | Bằng chứng | Khuyến nghị |
|---|---|---|
| CLAUDE §5.1 `/api/v1/<module>/<resource>`, thực tế 28 prefix cho 11 module: `execution` phủ `/work,/goals,/kpis,/objectives,/key-results,/calendar`; `idp` phủ `/data-capture,/idp,/files,/lineage`; `hr` phủ `/org`; `auth` phủ `/platform/users`; `/reporting` chia `dashboard` + `ai` | [S] `routes.json` | **Không đổi path** (breaking, không lợi ích). Cập nhật doc |
| `/business` chỉ là route FE (`app/(app)/business`), API vẫn `/finance`, `/sales`, `/hr`. Không phải bug | [S] | Giữ |
| EP numbering 2 hệ: CLAUDE §4.1 số thuần (EP-60..69), code và 10 dùng `EP-DC-xx`, `EP-WF-xx`, `EP-AI-xx`, `EP-FIN-xx` | [Đ] | Sửa bảng §4.1 |
| CLAUDE §4 ghi `ai_core`, `routes.py`, `core/rate_limit`, `workers/recompute_metrics...`, EVT 28; thực tế `ai`, `routes/`, không có rate_limit, `workers/jobs.py`, 40 event | [S] | Sửa doc (human) |
| Role v2.1: DB enum `auth.role_code` đã đúng 7 giá trị, `auth.roles` 7 dòng | [S] | Đã sạch ở dữ liệu |
| Dư v2.1 trong code: `LEGACY_ROLE_MAP` (`permission_matrix.py:23`, chỉ seed/test), `require_role`, `ApiClient._LEGACY` (`tests/conftest.py`), tên env `DEMO_CFO_PASSWORD`, `seed.UserSpec.env_key`, comment `ex CFO`, header compose "Aureon v2.1" | [S] | Gỡ `require_role` + `LEGACY_ROLE_MAP` khi chạm; test map có thể giữ |
| `secrets/` vs `keys/`: `docker-compose.yml` mount `./secrets`, `docker-compose.full.yml` mount `./keys`; default config trỏ `secrets/` | [Đ] | Chọn một |

---

## 4. Tầng dữ liệu

### 4.1. Schema `public` còn sót: alembic nào có thẩm quyền

- **Có thẩm quyền: `platform.alembic_version` = `0027_external_event_link_c19`.** `alembic/env.py` đặt `VERSION_SCHEMA = "platform"`.
- `public.alembic_version` = `37728110ccb4`, là revision của chuỗi v1 (có trong lịch sử git, commit `defb4d2`, không nằm trong `alembic/versions/` hiện tại).
- `public` còn 13 bảng + 3 enum (`actor_type`, `pillar`, `role_key`), có dữ liệu thật: `users` 5 dòng **kèm cột `password_hash`**, `audit_logs` 19 (có trigger append-only), `metrics` 18, `metric_values` 36, `alerts` 12, `extracted_fields` 11...
- Không có code nào trong app đụng tới. `env.py:include_name` chủ động bỏ qua.

Hại cụ thể: mọi `pg_dump` kéo theo hash mật khẩu cũ, và dễ nhầm khi điều tra sự cố. Cách xử lý: dump riêng schema `public`, lưu archive, `DROP` từng đối tượng, tách 1 task có quyết định của human (lệnh phá hủy, §6.6 rule 9). Không cần migration Alembic vì ngoài chuỗi.

### 4.2. Drift model ↔ migration (suy luận tĩnh, tương đương output `alembic check`) [S]

| Đối tượng | Model | DB | Hại |
|---|---|---|---|
| `ai.ai_evaluations` | `ix_ai_evaluations_tenant_id`, `ix_ai_evaluations_triggered_by` | Không có (0026 quên) | Bảng duy nhất có `tenant_id` không index dẫn đầu |
| `platform.user_preferences` | `ix_user_preferences_user_id` | Không có | Nhỏ, có UQ `(tenant_id,user_id,key)` |
| `execution.external_event_links` | `ix_..._calendar_event_id` | `ix_..._event_id` (rename cột không rename index) | `alembic check` báo lệch |
| `execution.action_items.task_id`, `meeting_summaries.meeting_id` | `unique=True, index=True` (unique index `ix_*`) | `uq_*` constraint | Lệch tên/kiểu đối tượng |
| `ai.briefings.generated_at`, `ai.ai_evaluations.started_at/finished_at` | không có `server_default` | `now()` | Nhỏ |

`env.py` đã bật `compare_type` + `compare_server_default`, nhưng **CI không chạy `alembic check`**, nên drift lọt được. Sửa: 1 migration vá + thêm bước `alembic check` trong CI (trên DB CI, an toàn).

### 4.3. Migration

- Reversibility: 27/27 có downgrade. Lossy đã khai báo (0016/0017). **Không có round-trip tự động**: `tests/integration/test_migrations.py:3` ghi rõ "Read-only", CI chỉ `upgrade head`.
- `0019_capture_seed_doctypes.py:22` import `app.modules.idp.services.catalog.SEED_TYPES`, trái với chính quy ước "migrations never import app" (0005:19, 0011:31, 0021:35). Sửa catalog thì replay 0019 cho kết quả khác. Chép snapshot vào migration.
- `0008_pgcrypto.py:19` import `encryption_key` nên migrate phụ thuộc env; chấp nhận nếu được ghi rõ.

### 4.4. `tenant_id` (R-DEC-07/13)

22 bảng thật không có `tenant_id` [S]:

| Nhóm | Bảng | Đánh giá |
|---|---|---|
| **Gốc rễ định danh** | `auth.users`, `auth.refresh_tokens` | Chặn multi-tenant: email unique toàn cục |
| **Log chứa dữ liệu nghiệp vụ** | `platform.audit_logs`, `ai.conversations`, `ai.messages`, `ai.feedback` | Lệch "mọi entity"; log mới (R-DEC-51) đã có `tenant_id`, các bảng này chưa |
| **Bảng con** | `hr.salary_history`, `idp.document_pages`, `idp.extraction_jobs`, `idp.extraction_reviews`, `idp.review_assignments`, `product.product_metrics`, `risk.risk_assessments`, `sales.deal_stage_history` | Scope qua cha; đây chính là lý do 48 `select(` trong `idp/services` lọt test |
| **Catalog/config** | `platform.metrics`, `approval_rules`, `system_settings`, `idp.document_types`, `extraction_schemas`, `validation_rules`, `auth.roles` | Có thể toàn cục, cần quyết định riêng |
| Kỹ thuật | `platform.processed_events` | Đúng (05 §2.3) |

`05` nói "mọi business entity" còn R-DEC-07 nói "mọi entity", nên hai tài liệu lệch nhau, cần DEC làm rõ.

Thêm: unique toàn cục không theo tenant: `execution.initiatives/kpis/projects.code`, `hr.employees.employee_code`, `product.products.code`, `risk.risks.code`, `sales.contracts.contract_number`. Chỉ thành vấn đề khi đi multi-tenant (B1 còn mở).

Tầng 2 của tenant guard không che: `insert(AUDIT_LOGS)`, `OUTBOX`, `PROCESSED` (Core table, đúng chủ đích) và `ModelCallLog` dùng `current_tenant() or DEFAULT_TENANT_ID` (`ai_service.py:62`), một fallback ngầm trái nguyên tắc fail-closed.

### 4.5. Soft delete, index

- Thiếu `deleted_at` 35 bảng, phần lớn là log/config đúng nhóm. Hard delete nghiệp vụ: `execution/repositories:370,389,397,420` (calendar event, measurement, check-in), dòng hóa đơn và forecast khi sửa. Đã audit ở service; chấp nhận vì `check_ins`, `kpi_measurements` là append-only theo 05 nhưng vẫn có API xóa → **mâu thuẫn tài liệu nhỏ**.
- Soft ref không index: `ai.insights.trigger_event_id`, `idp.capture_incidents.target_id`, `platform.data_lineage.document_action_id`, `platform.metric_values.scope_id`, `platform.notifications.ref_id`, `platform.outbox_events.aggregate_id`, `platform.reports.scope_id`. Dữ liệu nhỏ, chỉ thêm khi có query thật (`notifications.ref_id` được `already_sent` lọc, ưu tiên nhất).
- **75/530 index là `tenant_id` đơn cột** [S]: gần như vô dụng ở single-tenant (selectivity 1), chỉ tốn ghi. Không cần dọn gấp; khi multi-tenant thì composite mới là thứ cần.
- `platform.approval_requests` không có partial unique `(target_kind, target_id) WHERE status='PENDING'` → xem §5.3.

### 4.6. Quyền DB

App kết nối bằng role `aureon` **`rolsuper = t`** [S]. `app_audit_writer` (0007) được tạo nhưng không dùng; `core/audit.py` tự nhận "the app still connects as the shared role". Trigger immutability vì thế có thể bị vô hiệu bởi chính app. Claim "defense in depth" ở audit chỉ đúng 2/3 lớp.

---

## 5. Transaction và race condition

### 5.1. Đạt

- Service mở session riêng: chỉ `ModelCallLogService` (có chủ đích, ghi log lỗi provider độc lập, `ai_service.py:38,72`).
- Commit trong service: `auth_service` (session), `platform_service.py:67` (có lý do), `idp/.../executor.py:163` (savepoint). Còn lại commit ở route, được `test_route_commit.py` kiểm.
- Publish ngoài `publish_in_tx`: 0. Ngoại lệ không phải domain event: `process_document.delay` (§6.3).
- Khóa đúng: `approval_service.decide` (`_locked` + savepoint + CK `distinct_approvers`), `sales` stage (`FOR UPDATE`), `risk` code (advisory lock), `execution` task/KPI, `hr` assignment, `ai` action, `auth` refresh, `platform` settings. Rất tốt.

### 5.2. HIGH — `POST /finance/invoices/{id}/pay` mất cập nhật [Đ]

`modules/finance/services/invoice_service.py:256-276`:

```python
inv = await self.get(id_)                    # không FOR UPDATE
due = inv.total_amount - inv.paid_amount     # kiểm trên giá trị cũ
paid = inv.paid_amount + body.amount_paid    # read-modify-write
await self.repo.update(inv, paid_amount=paid, ...)   # không expected_version
```

`finance/repositories` không có `with_for_update`, `InvoicePay` không có `version`, không có `version_id_col` trong toàn dự án [S].

Hai khoản thanh toán đồng thời (khác `Idempotency-Key`): cả hai đọc `paid=0`, cả hai ghi `paid=X`. **Một khoản biến mất, `paid_amount` thiếu tiền, không lỗi.** CK `paid_in_range` chỉ chặn vượt tổng, không chặn mất cập nhật. Cũng có thể phát thiếu `finance.invoice_paid`. Không có test đồng thời (chỉ 2 `gather` trong toàn suite: optimistic lock, relay).

Fix: thêm `get_locked()` trong `InvoiceRepository`, 1 test `gather`. Effort S, không đổi schema/API.

### 5.3. MEDIUM — IDP thiếu khóa hàng [S + Đ]

`idp/repositories` là module ghi lớn duy nhất **không có `with_for_update`**.

- `CommitService._guarded` (`commit_service.py:219`) kiểm status/version trong Python; `doc.version += 1` (:117, :144) không có điều kiện. Hai approve đồng thời cùng qua.
- Với tài liệu có ACT, `uq_document_actions_document_seq` chặn **do tình cờ**: giao dịch thứ hai nhận `IntegrityError`. `run_all` không bắt lỗi này nên client nhận 500, không phải 409. Với tài liệu không có ACT: double `idp.document_committed` và double `ExtractionReview`.
- `UndoService.undo` (`undo_service.py:76`) kiểm `COMMITTED` không khóa: hai undo cùng lúc nhân đôi audit/event; `_conflicts` là check-then-act trên target.
- `ReviewService.open` (:239): soft lock check-then-set, hai reviewer có thể cùng nhận khóa.

Fix: 1 `SourceDocumentRepository.lock(id)` dùng ở `_guarded`, `undo`, `open`, `patch_fields`. Effort S.

### 5.4. LOW–MEDIUM — check-then-act khác

- `HiringService.submit` (`hiring_service.py:238`): không khóa, không có partial unique cho approval PENDING → double submit tạo 2 request. Fix: partial unique, cần DEC schema.
- `invoice_service.pay`-style khác: `race.py` lọc còn `import_service.submit` (có `_writable` + version, cần soi), `manual_service._commit_or_queue`, `mitigation_service._sync_risk`. **UNVERIFIED** từng ca.
- `InvoiceService.create` xử lý tốt: bắt `IntegrityError` trên UQ nghiệp vụ.
- Sinh mã: chỉ `risk.code` là sequence kiểu `max+1` và đã khóa advisory. Không thấy generator khác.

### 5.5. Audit cùng transaction

Đạt theo reachability (§1). `record_audit` ghi cùng session. Điểm yếu: `meta.request_id` luôn `None` trong worker (§7.1).

---

## 6. Idempotency, Celery, event

### 6.1. MEDIUM–HIGH — Idempotency có race và 15 route chỉ đòi key [S + Đ]

**Race:** `core/idempotency.py:59-82` là get → xử lý → set, không có reservation (`SET NX`). Hai request cùng key đến gần nhau (double click, retry của proxy) cùng miss, cùng thực thi. Thêm nữa `remember` chạy sau commit: Redis lỗi lúc đó thì client nhận 503 dù đã ghi, retry sẽ ghi đôi.

**Route khai `idem: Idem` nhưng không gọi `replay`/`remember` (15/88)** [S `idem.py`]:

`ai/routes/admin.py:80 create_policy`, `ai/routes/router.py:90 chat`, `:107 chat_stream`, `:212 dismiss_insight`, `:236 confirm_action`, `:245 reject_action`, `:254 undo_action`, `:281 open_briefing`, `:319 set_kill_switch`, `idp/routes/router.py:83 upload_documents`, `:201 review_open`, `:232 review_approve`, `:260 review_reject`, `:285 review_reassign`, `:304 review_merge`.

Phần lớn được state machine chặn và trả 409 thay vì replay kết quả (retry sau mạng rớt thành lỗi giả). `chat` thì không: retry tính phí LLM và tạo message trùng. `create_policy` tùy unique. `upload_documents` được dedupe qua sha256.

POST không có key: `/platform/dead-letters/{id}/replay`, `/idp/documents/{id}/review/release`, ngoài 3 route auth (được miễn). Hai route đầu trái CLAUDE §5.2 hoặc cần ghi miễn trừ.

Fix: `Idem` thành context manager với `SET key PENDING NX`, trả `409` khi đang xử lý; AST test bắt buộc `replay`. Effort M, không đổi API (409 đã có).

### 6.2. Celery

Tốt: `task_acks_late`, time limit toàn cục và từng task, `result_expires=3600`, NullPool theo task, consumer dedupe + unique `(event_id, consumer)`, retry 5/30/120 s, DLQ, beat 1 instance, job gom theo tenant.

| Vấn đề | Bằng chứng | Hại |
|---|---|---|
| Poison message | `worker.py:40,46` `acks_late` + `reject_on_worker_lost` toàn cục; `process_document` nặng RAM | OOM khi OCR → task quay lại queue vô hạn. **UNVERIFIED**, chưa tái hiện |
| 1 worker chung 3 queue | `docker-compose.full.yml:135` `-Q default,idp,events`, không `-O fair`/`prefetch=1`/`max_tasks_per_child` | OCR 240 s chiếm slot, event và relay consumer trễ; paddle rò RAM không được thu hồi |
| Hard time limit làm mất event | `consume_event` hard limit 60 s: Celery ack khi timeout, không có dòng `processed_events` | Mất event, không vào DLQ (hiếm) |
| Re-enqueue thất bại | `workers/events.py:71` `apply_async` lỗi khi broker down → event mất | Hiếm |
| DLQ replay mất event | `platform_service.py:57-67` commit xóa marker **rồi** mới `transport.send`; broker lỗi → marker mất, outbox đã `PUBLISHED`, không ai biết | Trực tiếp trái mục đích của DLQ |
| Outbox `FAILED` không có đường replay | `relay.py` set `FAILED` sau 5 lần; EP replay chỉ đọc `processed_events` | Mất event sau sự cố broker dài |
| Không có UI DLQ | FE không gọi `/platform/dead-letters` [S] | Vận hành chỉ biết qua API |
| Job dài trong 1 transaction | `_run_tenant` commit cuối; `generate_briefings`, `calendar_sync` gọi HTTP/LLM trong transaction | Giữ connection + 1 lỗi rollback cả loạt. Calendar interval 300 s = time limit 300 s → có thể chồng |
| Engine cache xuyên event loop | `ai_service.py:38` `get_sessionmaker()` (lru_cache, QueuePool) chạy trong worker dùng `asyncio.run` mỗi task, trái docstring `workers/events.py` | Log lỗi provider có thể mất âm thầm. **UNVERIFIED** |

### 6.3. HIGH — IDP pipeline nuốt lỗi [Đ]

- `pipeline.py:157` chỉ bắt `AIError`. PDF hỏng, `FileNotFoundError`, paddle crash, `SoftTimeLimitExceeded` (240 s) đều thoát ra, rollback **cả pipeline** vì `workers/idp_pipeline.py` chỉ commit một lần. Tài liệu ở lại `UPLOADED`, không lý do, không retry (`process_document` không `autoretry_for`).
- `enqueue_pipeline` (`pipeline.py:385-395`) `except Exception: return`, không log. Broker down → tài liệu không bao giờ chạy. Comment M6 trong chính file mô tả đúng triệu chứng này, nhưng chỉ vá cho `AIError`.
- `grep '"UPLOADED"'` không thấy sweeper nào; `check_review_sla` chỉ xét review.
- Toàn pipeline là 1 transaction (tới 300 s, giữ connection), nên các trạng thái `PREPROCESSING`/`EXTRACTING` **không hề nhìn thấy được** từ UI, dù inbox map chúng thành "processing".
- `store.read()` (`pipeline.py:104`) nạp cả file vào RAM (tới 50 MB), trái tinh thần CLAUDE §5.6.

Fix: `try/except Exception` → `_fail()` trong session mới; commit theo chặng; beat job sweep tài liệu `UPLOADED > N phút` để re-enqueue; log ở enqueue. Effort M, không đổi schema/API.

### 6.4. Beat job idempotent

Đã kiểm: `mark_overdue` (lọc trạng thái), `detect_overdue_tasks`, `detect_delayed_hiring_plans` (`skip_locked`), `checkin_reminder`, `remind_due_reviews` (`already_sent`), `generate_briefings` (CK). `check_burn_over_forecast`, `verify_action_outcomes`: **UNVERIFIED**.

---

## 7. Hiệu năng, lỗi, log, cấu hình, storage

### 7.1. MEDIUM — Log và truy vết [S + Đ]

- **`correlation_id` bị rơi**: `outbox.py:72` đưa vào envelope nhưng `insert(OUTBOX)` không có cột đó (bảng cũng không có, xác nhận trên catalog); `relay.py:38-47 _envelope` không set; DLQ replay cũng vậy. Mọi consumer nhận `None`. Trái CLAUDE §5.2 ("giá trị đi theo ... event `correlation_id`"). Fix cần thêm cột: schema change.
- Consumer không set `_request_id` nên audit từ worker có `request_id=null`.
- **Không có cấu hình logging**: `basicConfig/dictConfig` chỉ ở `seed/__init__.py:110`. `log_level` (`config.py:32`) không được đọc ở đâu. Hệ quả trong process API: logger `app.*` rơi về root mặc định WARNING, nên `log.info("model_call ...")` (`ai_service.py:42`) không xuất hiện. Chưa có JSON; `extra={"request_id"}` ở `request_context.py:60` không có formatter hiển thị.
- `/metrics` tự viết chỉ có counter theo method/status, không có latency, không có queue depth, outbox lag, DLQ count.

### 7.2. MEDIUM — Blocking trên event loop [S]

Toàn bộ `to_thread` chỉ có 1 chỗ (`core/health.py:55`). Chạy thẳng trên loop:

- `verify_password` argon2 (`auth_service.py:130`).
- `put_stream` ghi đĩa (`upload_service.py:78`), tới 100 file 50 MB.
- `parse()` openpyxl (`import_service.py:258,515`), 5.000 dòng.
- `Workbook` export (`dashboard/services/report_service.py:120`).
- `iter_file_chunks` file sync trong `StreamingResponse`: **UNVERIFIED** vì Starlette chạy sync iterator qua threadpool.

Compose chạy `uvicorn` **1 process, không `--workers`** (`docker-compose.full.yml:124`), nên một import lớn làm đứng mọi request.

### 7.3. HIGH — Rate limit chưa cài [S]

CLAUDE §5.3 ("middleware verify token + rate limit"), §5.5 (20 request/phút/người), `10` §1.4 dòng 48, `07` NFR-SEC-05 và AIC-01. Thực tế: không có middleware, không có Redis counter, `RateLimitError` không được raise, `core/rate_limit` không tồn tại. Có sẵn: lockout đăng nhập (`auth_max_failed_logins`), budget AI tháng (`gateway.py:216`).

Hại: `/ai/chat` không có trần theo người (chi phí và pool DB), `/auth/refresh` và upload không có trần; lockout có thể bị lợi dụng khóa tài khoản người khác. Effort S–M.

### 7.4. MEDIUM — LLM giữ connection DB [Đ]

`chat_service.py:112-113` ghi message (mở transaction, giữ connection) rồi `:151 gateway.chat` chờ tới `chat_timeout_seconds=90`; route commit sau cùng. `core/db.py:21` dùng pool mặc định (5+10), không `statement_timeout`/`lock_timeout`/`idle_in_transaction_session_timeout`.

15 chat đồng thời là cạn pool toàn API. Với 150 nhân sự dùng nội bộ thì chưa nổ ngay, nhưng đây là điểm nghẽn đầu tiên.

Cùng hàm: `/ai/chat/stream` `await svc.chat()` **xong rồi mới yield** (`router.py:123`), nên SSE không stream thật; không có `request.is_disconnected()` (0 kết quả grep), trái CLAUDE §6.5.

### 7.5. N+1 và phân trang [S]

134 điểm `await` trong vòng lặp, đã lọc tay. Đáng sửa (đường đọc thường xuyên, `limit` tới 100):

| Vị trí | Query mỗi item | Ghi chú |
|---|---|---|
| `idp/review_service.py:137 queue` → `_queue_item` (:141,:144,:149) | 3+ | Tệ nhất: tới ~300 query mỗi trang |
| `finance/invoice_service.py:149 list_invoices` → `out` (:81) | 1 | |
| `finance/forecast_service.py:144`, `finance_service.py:277` | 1 | |
| `finance/budget_service.py:159 statuses` | 1+ | Không phân trang |
| `idp/lineage.py:153-155` | 2 | |
| `execution/kpi_target_service.py:215 evaluate` | 1 | |
| `ai/tool_catalog.py:61` | 1 × số tool | |

24 GET trả `list[...]` không phân trang [S]. Phần lớn là danh mục nhỏ (roles, providers, tools). **Cần xem lại:** `/ai/conversations`, `/ai/conversations/{id}/messages`, `/ai/insights`, `/ai/actions`, `/calendar/events`, `/data-capture/documents/{id}/actions`. Thêm `limit` là đổi API (nhẹ).

Tính nặng trong request: `finance/analytics_service.py:218 dashboard` lặp `burn_and_runway`; `POST /finance/cash-flow-forecast/recompute` tính đồng bộ. Metric đã tính sẵn đúng thiết kế.

Dashboard fan-out là **chủ đích** (CLAUDE §5.8, FR-DSH-07), không phải lỗi. `Vary: Authorization` đã có.

### 7.6. Frontend [S]

- 51 `page.tsx` đều là Server Component mỏng, 183/423 file `use client`, dữ liệu fetch qua BFF. **Không có page client-only sai chỗ**; đúng với §5.8.
- First-load JS (raw, trước gzip): 344 KB tới 1.078 KB (`/goals/kpis/[id]`). `next/dynamic` dùng 0 lần; recharts nằm chung. Dynamic import biểu đồ là việc rẻ.
- `layout.tsx:27-31` đẩy **toàn bộ** messages (97–110 KB) vào RSC payload mỗi trang. Tách namespace nếu LCP là vấn đề.
- Query key: 41/133 chỗ dùng `queryKey` viết tay ngoài `qk`. Soi tự động không thấy key thiếu tham số thật: các ca regex báo là tham số cố định hoặc đã nằm trong `spec.path`. Các key `["work"]`, `["capture"]` invalidation thô, chấp nhận được.
- `use-capture.ts:84` invalidate 7 namespace mỗi lần, nhỏ.
- Logout: `signOut` mặc định reload trang nên cache mất; role switch demo: **UNVERIFIED**.

### 7.7. MEDIUM — Cấu hình không an toàn cho prod [Đ]

`app_env` **không có ai đọc** ngoài `config.py` [S]; không có validator production. Default fail-open:

| Biến | Default | Hại ở prod nếu quên |
|---|---|---|
| `MODEL_GATEWAY_MODE` | `fixture` | AI trả dữ liệu fixture, không báo lỗi. Hoặc lỗi thiếu fixture. |
| `CLAMAV_REQUIRED` | `False` (`.env.example` cũng false) | Scanner chết → tài liệu qua `SKIPPED`, chỉ chặn STP |
| `OCR_PROVIDER` | `stub` | OCR giả |
| `JWT_KEY_ID` | hard-code | Xoay khóa 90 ngày không có quy trình |
| `NEXT_PUBLIC_DEMO_MODE` | `true` (`Dockerfile` ARG, compose default) | Mode demo FE mặc định bật ở image |
| `/docs`, `/openapi.json`, `/metrics` | Công khai | Lộ toàn bộ contract và tình trạng dependency trên cổng 4000 |

`web` nhận `env_file: .env` (`docker-compose.full.yml:182`): Next.js có đủ `DATABASE_URL`, API key provider, `DB_ENCRYPTION_KEY`. Nên whitelist.

`scripts/bootstrap_admin.py:38` đọc `os.environ` (được ghi chú, là script). Chấp nhận.

Fix: `model_validator` khi `APP_ENV=production` bắt buộc `live`, `CLAMAV_REQUIRED=true`, `OCR=paddle`, `DEMO_MODE=false`. Effort S.

### 7.8. Storage: MinIO không được dùng [S]

- Không có `boto`/`minio`/`s3` trong code. `S3_ENDPOINT`, `S3_BUCKET` không có trong `ConfigService`; compose vẫn yêu cầu `S3_ACCESS_KEY` bắt buộc và chạy MinIO (150 MB RAM, cổng 9000/9001 mở) mà không phục vụ gì.
- Lưu thật ở `LocalObjectStore`, `var/idp-storage` (bind mount ở `full`). `docker-compose.yml` **không mount**, nên worker từ file đó không thấy file upload.
- `ObjectStore.open()` trả `Path`: protocol rò khái niệm filesystem; S3 adapter sẽ phải sửa `files.py`, `import_service.py`, `pipeline`.
- Retention: `sweep_orphan_storage` chỉ báo cáo mặc định; `purge_import_rows` có. **Không có retention** cho file gốc, `outbox_events`, `processed_events`, `audit_logs`, `model_call_logs`, `tool_call_logs`, `data_lineage`, `document_pages.text_content` (nội dung tài liệu dạng rõ).
- Không có backup cho `var/idp-storage`.

Quyết định: hoặc cài S3 adapter hoặc gỡ MinIO khỏi compose. Đừng giữ cả hai.

---

## 8. Hạ tầng và CI

### 8.1. HIGH — Cổng và quyền [S]

Publish `0.0.0.0` thực tế (`docker ps`): 5432, 6379, 9000-9001, 11434, 3310, 1025, 8025, 3000, 4000.

- **Redis `requirepass` rỗng** [S], kiêm broker: ai tới được 6379 có thể đẩy task `app.events.consume` với event và `tenant_id` tự chọn, vượt qua mọi RBAC; hoặc xóa idempotency/queue.
- Postgres dùng superuser (§4.6).
- Ollama, ClamAV không có auth.
- Không có `mem_limit`/`cpus` ở service nào.

Fix: bind `127.0.0.1:` mặc định qua biến, `requirepass`, role app thường. Khả năng truy cập từ LAN: **UNVERIFIED** (WSL2 NAT che một phần, Docker publish không qua iptables WSL).

### 8.2. HIGH — Seed chạy ở mỗi lần start [Đ]

`docker-compose.full.yml:124`: `alembic upgrade head && python -m app.seed && uvicorn ...`. `seed/__init__.py` không kiểm `DEMO_MODE`/`APP_ENV`.

Với deploy thật: dữ liệu công ty ABC và 10 tài khoản `@abc.demo` được tạo ở production nếu env có mật khẩu demo; `seed_auth` đặt lại hash khi env đổi; `seed_goals` upsert theo id cố định ở mọi lần seed (`goals_seed.py:3,154` `setattr`) nên **ghi đè chỉnh sửa thật** trên các bản ghi đó; `MetricStore.recompute` chạy ở mỗi restart. Migration trong command cũng sẽ race khi có >1 replica và không có đường dry-run.

Fix: job one-shot riêng `migrate`, seed chỉ khi `DEMO_MODE=true`. Effort S.

### 8.3. CRITICAL — CI không bảo vệ gì (đã biết nhưng chưa sửa) [S]

- `.github/workflows/ci.yml:83` `needs: secrets`; gitleaks đỏ liên tục từ 21/10 → **job `api` bị skip**: ruff, mypy, migrate, seed, pytest, contract backend không chạy trên CI suốt 15 ngày. Chỉ `web` chạy.
- `gh api .../branches/main/protection` → `404 Branch not protected` [S]. PR #6 merge khi đỏ. 8/8 run gần nhất failure [S].
- `deliverables/GITLEAKS-AUDIT.md` (03/11) đã có phương án đã thử (0 leak), nhưng `.gitleaks.toml` **vẫn chưa tồn tại** [S]. Đây là việc rẻ nhất có giá trị lớn nhất trong báo cáo này. Repo public, nên càng cần.

Thiếu khác: `on: push` chỉ `main` (nhánh `v3/*` chỉ chạy khi có PR), không E2E, không build image, không `alembic check`, không round-trip migration, không `pip-audit`/`pnpm audit`, action pin bằng tag, Node 22 (CI) khác Node 24 (Dockerfile).

### 8.4. HIGH — Backup và rollback

| Yêu cầu | Thực tế |
|---|---|
| NFR-AV-02 (`07:179`): RPO ≤ 15 phút, RTO ≤ 4 giờ, backup hằng ngày, giữ 30 ngày, diễn tập hằng quý | Chỉ `pg_dump` thủ công khi deploy (`var/backup/aureon_prem8_*.dump`, cùng máy, cùng đĩa). Không cron, không WAL, không offsite, không diễn tập |
| Rollback | Checklist tay `deliverables/M8-CRM-PLAN.md` §9: `docker tag :pre-m8 → :local`, recreate. Có rủi ro dữ liệu đã được ghi rõ (approval hiring). **Khá tốt cho quy mô hiện tại**, nhưng không có registry, tag không gắn git SHA, không đường lùi schema đã diễn tập |
| Secret/key | Bản sao khóa JWT, `DB_ENCRYPTION_KEY` ngoài máy: **UNVERIFIED**. Mất key pgcrypto = mất dữ liệu mức 4 |

### 8.5. Hai file compose

| Khác biệt | `docker-compose.yml` | `docker-compose.full.yml` |
|---|---|---|
| Service | Hạ tầng + worker + beat | Thêm `api`, `web` |
| Khóa | `./secrets` | `./keys` |
| Storage | **Không mount** | `./var/idp-storage` |
| `S3_ENDPOINT` | Không | Có nhưng vô dụng |
| Network | default | `aureon-net` |

Cùng `name: aureon`, chia volume; header vẫn "v2.1". Nên hợp nhất bằng `profiles` (S).

`latest`: minio, ollama, clamav, mailpit (máy đã có `clamav/clamav:1.5.4`). Pin digest. `deploy.replicas: 1` của beat **không** chặn `--scale`, chỉ là chú thích; relay vẫn an toàn nhờ `SKIP LOCKED`.

Healthcheck: đủ cho postgres, redis, minio, ollama, clamav, api, web, worker, beat (beat chỉ kiểm mtime). Tốt.

### 8.6. Image 5,25 GB: nguyên nhân [S]

| Thành phần | Dung lượng |
|---|---|
| **`/root/.cache` (uv cache, không xóa sau `uv sync`)** | **1,7 GB — lãng phí thuần** |
| `/opt/venv` | 1,7 GB, gồm `paddle` 702 MB |
| Ba bản OpenCV (`opencv_python`, `opencv_contrib_python`, `opencv_python_headless`) | ~400 MB kèm `.libs` |
| apt `libgomp1 libgl1 libglib2.0-0` | 217 MB |
| Base python + binary `uv` | ~235 MB |

Layer `uv sync` = 3,56 GB (= venv + cache). Hai bước `uv sync` đều giữ cache.

Sửa: `UV_NO_CACHE=1` hoặc `rm -rf /root/.cache/uv` cùng `RUN` → **giảm 1,7 GB, 1 dòng**. Tách image OCR: `api`/`beat` chạy `UV_EXTRAS=none` (~0,5 GB, ước tính), chỉ `worker-idp` mang paddle.

`aureon-web` 1,63 GB: `COPY /repo /repo` kéo cả devDependencies, source, có thể `.next/cache`. `output: "standalone"` trong `next.config.mjs` → ~200–300 MB (ước tính).

---

## 9. Kiến trúc test

### 9.1. CRITICAL — `uv run pytest` chọn DB thế nào [Đ]

**Trả lời trực tiếp:** test dùng đúng `DATABASE_URL` của `ConfigService`, tức `.env`. Không có DB test riêng, không có `TEST_DATABASE_URL`, **không có guard** kiểm tên DB hay `APP_ENV` (`tests/conftest.py` `db_session`, `events/conftest.py`). `.env.example` trỏ `localhost:5432/aureon`, chính là cổng Postgres stack đang publish. Team đã từng tránh bằng tay: `STATE.md:37` ghi "DB `aureon_m4` tạo lại sạch". Docstring thừa nhận "shared dev DB" (`events/conftest.py:3`, `test_seed.py:3`).

Giá trị thật của `.env` trên máy này: **UNVERIFIED** (không được đọc).

Nếu trỏ vào DB đang chạy, thứ thực sự xảy ra:

| Hành vi | Bằng chứng | Hậu quả |
|---|---|---|
| **Test relay quét toàn bộ `PENDING` của outbox thật** với `honor_pause=False` và transport/registry giả | `relay.py:66-71` không lọc; `test_celery_tasks.py:80` `relay_outbox_events.run(honor_pause=False)`; `test_alert_sla.py:63`; `test_task_events.py:125`; `test_event_bus.py:48` | Event thật của người dùng bị đánh dấu `PUBLISHED` và gửi vào bộ nhớ: **mất vĩnh viễn, không lỗi** (metric không tính lại, alert không phát, không notification) |
| Pause relay live cả phiên | `events/conftest.py:34-47` | Event thật tắc trong lúc chạy test; vì bị test relay ở dòng trên ăn mất nên không tự phục hồi |
| `TRUNCATE ... CASCADE` ~100 bảng | `test_seed_v3.py:47-52,77`, `test_seed_onboarding_t649.py:87`, `test_work_m13.py:43` | Nằm trong transaction nên **rollback, dữ liệu an toàn**; nhưng giữ `ACCESS EXCLUSIVE` tới hết test → API, worker treo, nguy cơ deadlock |
| Ghi thật rồi tự dọn | `events/*` (9 file có `commit()` thật), `test_alert_sla.py:50-60` (Budget, Expense, Alert năm 2041), `test_optimistic_lock.py:149,174` (`auth.users`, hard delete), `test_model_call_log_failures_m5.py:43` | Pytest bị kill giữa chừng → rác trong DB thật. Dòng `test_events` PENDING bị beat thật relay |
| Redis thật | `core/idempotency.py:_redis()` không mock | Key `idem:v1:*` trên Redis stack (TTL 24 h), vô hại |
| Storage | `integration/idp/conftest.py` patch `tmp_path` | An toàn cho test IDP |
| Alembic | `test_migrations.py` chỉ đọc | An toàn |

Đánh giá: test rollback-based (phần lớn) không hủy dữ liệu, kể cả `TRUNCATE`. **Lỗi thật là nuốt event và khóa bảng.** Vì cùng máy với deploy "production" M8, xếp Critical.

Fix (S):

```python
# tests/conftest.py, chạy trước mọi thứ, session scope
assert make_url(cfg.database_url).database.endswith("_test"), "refuse non-test DB"
assert cfg.app_env != "production"
```

kèm `TEST_DATABASE_URL`, tạo DB `aureon_test` từ `alembic upgrade head` + seed. CI đổi tên DB tương ứng.

### 9.2. Kiến trúc test: khác

- Tốt: outer transaction + savepoint; fixture gateway mặc định; event test dùng commit thật có chủ đích; contract test; test kiến trúc tĩnh; `.coverage` (03/11) báo 90% branch cho services + core [S], STATE ghi 94% toàn bộ.
- Kết quả test phụ thuộc `.env`: `DEMO_MODE` đổi `business_today()`, seed sẵn có hay không, nên chạy trên máy khác nhau cho kết quả khác.
- `pytest.skip` trong `integration/ai/test_ai_e2e.py:547,581,635`: trái CLAUDE §6.6 rule 4 (điều kiện seed).
- **Gap đồng thời**: chỉ 2 test dùng `gather`; không có test race cho pay, IDP approve, idempotency, undo. Mock session dùng chung (`api` fixture) còn che lỗi quên commit, đã được `test_route_commit` bù.
- Không có test cho nhánh lỗi pipeline ngoài `AIError`.
- E2E: 33 spec, 2 project (`mock`/`real`), `workers: 1` nên ổn định, nhưng **không chạy trong CI**. Tỉ lệ flaky: **UNVERIFIED**.
- `tests/events/test_tasks_end_to_end` monkeypatch `CeleryTransport.send`, nên không có test nào đi qua Redis thật.

---

## 10. Sổ nợ kỹ thuật

Effort: S ≤ 1 ngày, M ≤ 1 tuần, L > 1 tuần. Cột **S/A**: S = đổi schema, A = đổi API.

| ID | Sev | Vị trí | Tác động | Fix | Eff | S/A |
|---|---|---|---|---|---|---|
| TD-01 | **Critical** | `tests/conftest.py`, `tests/events/*`, `relay.py:66` | Pytest trên DB live nuốt event thật, khóa ~100 bảng | Guard tên DB + `aureon_test`, bắt relay test lọc theo `aggregate_table` | S | Không |
| TD-02 | **Critical** | `ci.yml:83`, thiếu `.gitleaks.toml`, không branch protection | Backend không có CI từ 21/10; merge khi đỏ | Áp GITLEAKS-AUDIT; bỏ `needs` hoặc giữ sau khi xanh; bật protection | S | Không |
| TD-03 | High | `invoice_service.py:256` | Mất khoản thanh toán khi đồng thời | `get_locked` + test `gather` | S | Không |
| TD-04 | High | `docker-compose.full.yml:124`, `seed/__init__.py` | Seed demo mỗi lần start, có thể ghi đè dữ liệu thật | Job migrate riêng, seed chỉ khi `DEMO_MODE` | S | Không |
| TD-05 | High | Thiếu `core/rate_limit` | Không có trần AI/auth/upload; trái contract | Middleware Redis + `RateLimitError` | M | Không (đã có trong 10) |
| TD-06 | High | Compose ports, Redis, role `aureon` | Tiêm task qua broker; superuser | Bind localhost, `requirepass`, role app, `mem_limit` | S | Không (migration quyền) |
| TD-07 | High | `pipeline.py:157,394`, `idp_pipeline.py` | Tài liệu kẹt `UPLOADED` im lặng; 1 transaction 300 s | Bắt mọi lỗi → `_fail`, commit theo chặng, sweeper, log | M | Không |
| TD-08 | High | NFR-AV-02 | Không backup tự động, không diễn tập | Cron `pg_dump` + WAL/offsite + `var/idp-storage` + drill | M | Không |
| TD-09 | High | `core/idempotency.py`, 15 route | Double-submit thực thi 2 lần; chat tính phí lại | `SET NX` reservation; AST test | M | Không |
| TD-10 | Medium | `idp/repositories`, `commit_service`, `undo_service`, `review_service` | Race trả 500, double event | `lock()` hàng tài liệu | S | Không |
| TD-11 | Medium | `outbox.py:72`, `relay.py:38`, consumer | Mất correlation event → worker | Cột `correlation_id` + set contextvar | S | **S** |
| TD-12 | Medium | `config.py:32`, thiếu logging config | INFO mất ở API, không JSON, không request_id | `dictConfig` + formatter JSON (stdlib) | S | Không |
| TD-13 | Medium | `config.py`, thiếu validator prod | Quên env → AI/OCR giả, scanner fail-open | `model_validator` theo `app_env` | S | Không |
| TD-14 | Medium | `chat_service.py:113,151`, `router.py:123` | LLM giữ connection; SSE giả; không kiểm disconnect | Tách transaction quanh LLM, stream thật | M | Không |
| TD-15 | Medium | Auth, upload, import, export | Blocking loop, 1 uvicorn process | `to_thread`, `--workers 2-4` | S | Không |
| TD-16 | Medium | `worker.py`, compose | OCR starve event; poison loop; OOM | Worker riêng `idp` + `prefetch=1` + `max_tasks_per_child`; `reject_on_worker_lost` chỉ cho event | S | Không |
| TD-17 | Medium | `platform_service.py:57`, relay `FAILED`, FE | DLQ replay mất event; FAILED không replay; không UI | Send trước, xóa marker sau; EP replay outbox | M | **A** (nếu thêm EP) |
| TD-18 | Medium | Image API/web | 5,25 GB / 1,63 GB, pull và recreate chậm | Xóa uv cache (1 dòng), tách image OCR, `standalone` | S–M | Không |
| TD-19 | Medium | 22 bảng thiếu `tenant_id`, 48 `select(` trong `idp/services` | Chặn multi-tenant, lệch R-DEC-07 | Chốt DEC; thêm cột theo đợt; chuyển SQL vào repository | L | **S** |
| TD-20 | Medium | Schema `public` | Hash cũ trong mọi dump; gây nhầm | Archive rồi DROP (human duyệt) | S | **S** (ngoài Alembic) |
| TD-21 | Medium | Local FS + MinIO chết, `ObjectStore.open→Path` | Không HA, chạy dịch vụ thừa | Quyết: S3 adapter hoặc gỡ MinIO | M | Không |
| TD-22 | Medium | Không retention | outbox, processed, log, text tài liệu tăng vô hạn | Beat job + TTL theo classification | M | Không |
| TD-23 | Medium | `core/db.py:21` | Không timeout DB; query treo giữ pool | `connect_args` `statement_timeout`, `lock_timeout` | S | Không |
| TD-24 | Medium | `/docs`, `/metrics`, `web env_file` | Lộ contract; web giữ mọi secret | Tắt theo env; whitelist env cho `web` | S | Không |
| TD-25 | Medium | `review_service.py:137`, N+1 khác | ~300 query/trang review queue | Batch load | S–M | Không |
| TD-26 | Low | Drift §4.2 | `alembic check` đỏ | 1 migration + bước CI | S | **S** (index) |
| TD-27 | Low | `0019` import app | Replay migration không ổn định | Snapshot trong file | S | Không |
| TD-28 | Low | CI: thiếu E2E, round-trip, audit deps | Lỗi lọt muộn | Thêm job | M | Không |
| TD-29 | Low | `latest`, 2 file compose, `secrets`/`keys` | Không tái lập | Pin digest, `profiles` | S | Không |
| TD-30 | Low | 6 GET list không phân trang | Tải lớn dần | Thêm `limit/offset` | S | **A** |
| TD-31 | Low | `hiring_service.py:238`, approval PENDING | 2 request trùng | Partial unique | S | **S** |
| TD-32 | Low | Code chết §3.1, helper trùng | Nhiễu | Gỡ dần | S | Không |
| TD-33 | Low | Doc drift §3.4 | Agent đọc sai cấu trúc | Human cập nhật CLAUDE §4 | S | Không |
| TD-34 | Low | `recharts`, i18n payload | First-load 1 MB | `next/dynamic`, tách namespace | S | Không |
| TD-35 | Low | 3 `pytest.skip`, gap test đồng thời | Che lỗi | Sửa thành seed deterministic | S | Không |

---

## 11. Thứ tự đề xuất trước v4 (2 tuần đầu)

1. **Ngày 1:** TD-01, TD-02 (đặt lại lưới an toàn trước khi sửa gì khác).
2. **Tuần 1:** TD-03, TD-04, TD-06, TD-10, TD-12, TD-13, TD-15, TD-16, TD-18, TD-23, TD-24.
3. **Tuần 2:** TD-05, TD-07, TD-08, TD-09, TD-11.

---

## 12. Tái cấu trúc cho v4

### MUST (chặn production hoặc chặn mở rộng)

1. **Tách môi trường và đặt lại gate:** DB test riêng, CI xanh bắt buộc, branch protection, `migrate` job riêng khỏi `app.seed`. Lợi ích: mọi thứ dưới đây mới kiểm chứng được.
2. **Tách worker theo tải:** `worker-events` (nhẹ, nhiều slot) và `worker-idp` (concurrency 1–2, image OCR); `api`/`beat` dùng image lean. Lợi ích: event không bị OCR chặn, image API giảm từ 5,25 GB xuống cỡ 0,5 GB (ước tính).
3. **Độ tin cậy IDP và idempotency:** pipeline commit theo chặng, sweeper, reservation `SET NX`, row lock cho tài liệu và hóa đơn.
4. **Sự sống hạ tầng:** backup tự động + drill, role DB thường, Redis có auth, cổng nội bộ, validator production, rate limit.
5. **Quan sát:** `correlation_id` xuyên worker, log JSON, metric outbox lag/DLQ/queue.
6. **Quyết định lưu trữ:** S3 adapter thật (đổi `ObjectStore` sang stream, không `Path`) hoặc gỡ MinIO; kèm retention.

### WORTH IT (lợi rõ, không gấp)

7. **Hoàn tất `tenant_id` — chỉ khi B1 chốt SaaS.** Nếu vẫn 1 doanh nghiệp, giữ nguyên.
8. Chuyển 48 `select(` trong `idp/services` vào repository khi thêm `tenant_id` (làm chung để không đụng 2 lần) và mở rộng test tenant sang bảng con.
9. Mở rộng `tests/architecture`: `workers/`, kiểm catalog FK chéo schema, bắt buộc `Idem.replay`, cấm `select(` trong services.
10. Stream SSE thật, giải phóng connection trong lúc gọi LLM.
11. `alembic check` và round-trip trong CI.
12. Batch load N+1 cho review queue, hóa đơn; dynamic import biểu đồ; web `standalone`.
13. Hợp nhất helper thời gian vào `core/clock` (giảm nguy cơ sai ngày demo/thật).
14. Dọn schema `public`, gỡ `require_role`, `LEGACY_ROLE_MAP`, code chết.
15. Tách mock FE khỏi bundle production (dynamic import sau `isMockMode`).

### NOT WORTH IT

- **Tách microservice hoặc tách deployable `ai`/`idp`:** ranh giới đã sạch; tách theo process (worker) đạt lợi ích thực mà không mất transaction chéo module của Action Registry.
- **Đổi 28 prefix API về `/<module>/...`:** breaking cho FE, mock, AI tool, test; không có lợi ích vận hành. Sửa tài liệu.
- **Đồng bộ EP numbering trong code.** Chỉ sửa bảng doc.
- **Chuyển trang sang Server Component fetch:** 51 page đã đúng mô hình BFF + TanStack theo §5.8; đổi sẽ phá "mỗi widget một query", được rất ít cho app nội bộ.
- **Tách file lớn:** không có god service thật.
- **Bỏ `core/*_directory` registry:** pattern đúng, chỉ cần fail-fast.
- **Thêm FK chéo schema:** trái C7, soft ref hiện 0 orphan trên mẫu.
- **Dọn 1.380 `# fmt: skip`**, **viết lại 75 index `tenant_id`**, **bỏ mock FE**: tốn nhiều, lợi nhỏ (mock vẫn có giá trị cho E2E).
- **Đổi Redis/Celery sang broker khác:** chưa có áp lực tải.
- **Đổi tên module `ai` về `ai_core`:** chỉ cần sửa doc.

---

## 13. UNVERIFIED

| Mục | Vì sao |
|---|---|
| `.env` host có trỏ đúng DB stack không | Không đọc `.env`; suy từ `.env.example` và cổng publish |
| Compose này có đúng là production không | Suy từ `deliverables/M8-CRM-PLAN.md` ("production deployment" trên cùng compose) |
| Các race §5.2–5.4, §6.1 | Phân tích tĩnh, không chạy test |
| Poison loop OOM, engine xuyên event loop | Suy luận, chưa tái hiện |
| Truy cập cổng từ LAN | Không thử mạng |
| Endpoint không dùng | FE gọi động qua `RecordCrud` (`spec.path`). Đã xác nhận bằng grep **không** có FE: `/finance/forecasts*`, `/finance/cash-flow-forecast*`, `/hr/.../salary-history`, `/hr/dashboard`, `/hr/workload`, `/execution/dashboard`, `/goals/strategic-objectives*`, `/reporting/preferences/executive-tiles`, `/platform/dead-letters*`, `/idp/.../review/reassign`, `/idp/review-queue/merge`, `POST /ai/chat`, `/auth/me`, toàn bộ `/product/*` (22) và `/risk/*` (14, đóng băng theo R-DEC-16). Có thể được AI tool, script hoặc khách API dùng. **Không tự ý xóa**: phần lớn là EP trong contract 10 |
| Coverage | Từ `.coverage` ngày 03/11, không chạy lại |
| Flaky E2E, số liệu tải thực | Không chạy |
| `today()` từng bản, 3 ca check-then-act §5.4, `check_burn_over_forecast` | Chưa đọc hết |
| Kích thước image sau tối ưu | Ước tính |

Ghi chú: `docker stats` lúc audit thấy thêm container `v4audit-pg`, `v4audit-redis` không có trong danh sách ban đầu; không phải do audit này tạo. `git status` không phát sinh thay đổi do audit này.
