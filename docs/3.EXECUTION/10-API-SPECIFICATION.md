# 10 — API Specification

> **Contract nguồn duy nhất** cho API của Aureon Demo. Backend FastAPI (`apps/api`) và frontend Next.js (`apps/web`) phải bám đúng file này. Không tự thêm endpoint/field — mọi thay đổi cập nhật file này trước hoặc raise `DEC-xxx` (CLAUDE.md § Cấm tự quyết).
> Nguồn: `02-PERSONAS-PERMISSIONS.md` (quyền, scoping, role switcher), `03-DASHBOARD-SPEC.md` (metric, alert, drill-down), `04-IDP-FEATURE-SPEC.md` (pipeline, FR-DC, US-DC, Action Registry, UC-07), `05-DATA-MODEL.md` (tên bảng/cột/enum), `06-UI-UX-SPEC.md` (SCR-xx), `07-TECH-ARCHITECTURE.md` (JWT, DEMO_MODE, polling, presigned URL).

---

## 1. Quy ước chung

### 1.1. Base path, định dạng, phiên bản

| Hạng mục | Quy ước |
|---|---|
| Base path | `/api/v1` — mọi path trong file này là tương đối với base path (VD `GET /metrics` = `GET /api/v1/metrics`) |
| Định dạng | JSON UTF-8 (`Content-Type: application/json`); riêng upload dùng `multipart/form-data`, tải file dùng presigned URL |
| Tên field JSON | `snake_case`, **trùng tên cột ở 05-DATA-MODEL** (VD `subtotal`, `amount_due`, `period_key`, `computed_at`, `source_location`) |
| ID | UUID dạng chuỗi; mã nghiệp vụ dùng mã chuẩn: `METRIC-FIN-01`, `ALERT-FIN-01`, `ROLE-01` |
| Thời gian | ISO 8601 có timezone (`2026-10-05T08:30:00+07:00`); ngày thuần `YYYY-MM-DD`. **API không format kiểu Việt Nam** — định dạng P04 làm ở frontend (06 §7) |
| Tiền | Số nguyên VND (`bigint`), không chuỗi, không làm tròn |
| Tỷ lệ | Số thập phân (`0.125` = 12,5%) với unit `PERCENT`; metric trả `value` theo `metrics.unit` |
| Chuỗi hiển thị | API trả **mã + i18n key + tham số**, không trả câu tiếng Việt cố định (trừ `error.message` mặc định để debug) |
| Phiên bản | Thay đổi phá vỡ contract → `/api/v2` + DEC; thêm field optional không phá vỡ |

### 1.2. Response envelope

Thành công:

```json
{ "data": { ... } | [ ... ], "meta": { ... } }
```

- `data`: object hoặc mảng; `meta` tùy chọn (phân trang, `request_id`, `generated_at`).

Lỗi:

```json
{ "error": { "code": "FORBIDDEN_SCOPE", "message": "Nguồn thuộc phạm vi khác", "details": { ... } } }
```

- `code`: mã ổn định theo §1.3 (frontend map sang i18n `error.<code>`).
- `details`: tùy chọn — lỗi validation trả `{ "fields": [{ "loc": ["body","field"], "msg": "...", "type": "..." }] }`.
- Mọi response có header `X-Request-Id` (cũng ghi vào `audit_logs.metadata.request_id`).
- Mọi endpoint khai báo `response_model` Pydantic v2; field nhạy cảm không thuộc response model của role không có quyền (§1.8).

### 1.3. Bảng error code

| HTTP | `error.code` | Ý nghĩa | Ví dụ |
|---|---|---|---|
| 400 | `BAD_REQUEST` | Request sai cú pháp/tham số không hợp lệ | `period_key` sai định dạng |
| 401 | `UNAUTHENTICATED` | Thiếu/sai/hết hạn JWT | Header `Authorization` thiếu |
| 401 | `INVALID_CREDENTIALS` | Sai email/mật khẩu (không tiết lộ email tồn tại) | EP-02 |
| 403 | `FORBIDDEN_ROLE` | Role không được phép gọi endpoint (`require_role`) | Sales Director gọi duyệt |
| 403 | `FORBIDDEN_SCOPE` | Tài nguyên thuộc trụ ngoài scope (02 §4.1 mục 4) | CFO mở bản ghi CUS chi tiết |
| 403 | `FORBIDDEN_SALARY` | Tài liệu/field chứa lương cá nhân, role không có quyền (02 §4.3) | CEO mở tài liệu #6 |
| 404 | `NOT_FOUND` | Không tồn tại hoặc đã soft delete; endpoint demo khi `DEMO_MODE=false` | EP-04 khi tắt demo |
| 409 | `CONFLICT_STATE` | Chuyển trạng thái không hợp lệ theo state machine 04 §8.2 | Approve tài liệu `COMMITTED` |
| 409 | `REVIEW_LOCKED` | Tài liệu đang được người khác review (khóa mềm 15 phút) | `details.locked_by`, `locked_until` |
| 409 | `IDEMPOTENCY_CONFLICT` | Cùng `Idempotency-Key` nhưng body khác | §1.6 |
| 409 | `DUPLICATE_DOCUMENT` | Trùng SHA-256 (thông tin, tài liệu vẫn được tạo ở `DUPLICATE`) | EP-20 trả kèm `details.duplicate_of_id` |
| 410 | `UNDO_EXPIRED` | Quá hạn hoàn tác 7 ngày (`undo_deadline`) | EP-33 |
| 413 | `FILE_TOO_LARGE` | > 20 MB hoặc > 50 trang (IDP-E01) | EP-20 |
| 415 | `UNSUPPORTED_MEDIA_TYPE` | Định dạng không hỗ trợ (IDP-E01) | `.zip` khi chưa có DEC |
| 422 | `VALIDATION_ERROR` | Body sai schema / rule nghiệp vụ (MST sai, field đỏ chưa xác nhận) | `details.fields[]` |
| 422 | `ACTION_REJECTED` | Action Registry từ chối (input_schema, conflict XD blocking) — IDP-E10 | `details.action_name`, `details.reason` |
| 423 | `AI_DISABLED` | Kill switch L0 — thao tác cần AI bị chặn | C2 khi AI tắt |
| 429 | `RATE_LIMITED` | Vượt giới hạn tần suất | Upload hàng loạt |
| 500 | `INTERNAL_ERROR` | Lỗi không mong đợi (không lộ stack trace) | — |
| 503 | `DEPENDENCY_UNAVAILABLE` | DB/Redis/MinIO/ModelGateway không sẵn sàng | Health `degraded` |

Mã lỗi IDP nội bộ `IDP-E01..E11` (04 §14) xuất hiện ở `extraction_jobs.error_code` và `details.idp_error_code`, không thay thế `error.code`.

### 1.4. Xác thực (JWT)

| Hạng mục | Quy ước (07 §8.1.2) |
|---|---|
| Header | `Authorization: Bearer <JWT>` cho mọi endpoint trừ EP-01 (health) và EP-02 (login) |
| Định dạng | JWS HS256 ký bằng `JWT_SECRET` (dùng chung NextAuth + FastAPI) |
| Claim bắt buộc | `sub` (user id), `role` (`ROLE-01`..`ROLE-05`), `iat`, `exp`, `iss`, `aud` |
| Hết hạn | `JWT_EXPIRES_IN` (đề xuất 8 giờ); không có refresh token trong demo |
| Verify | Dependency `get_current_user` (chữ ký, `exp`, `iss`, `aud`) → lỗi `UNAUTHENTICATED` |
| Phân quyền | `Depends(require_role(...))` đọc claim `role`; ký hiệu role trong file này là `ROLE-xx` ↔ `roles.key` (`CEO`, `CFO`, `SALES_DIRECTOR`, `HR_MANAGER`, `REVIEWER`) |
| Không tin client | Không endpoint nào nhận role từ body/query để phân quyền |

### 1.5. Phân trang, lọc, sắp xếp

| Tham số | Kiểu | Mặc định | Ghi chú |
|---|---|---|---|
| `page` | int ≥ 1 | 1 | |
| `page_size` | int 1..100 | 20 | |
| `sort` | string | theo endpoint | `field` tăng, `-field` giảm (VD `-uploaded_at`) |
| Bộ lọc | query string | — | Tên tham số trùng tên cột 05 (VD `status`, `doc_type`, `pillar`, `batch_id`) |

`meta` của danh sách: `{ "page": 1, "page_size": 20, "total": 47, "total_pages": 3 }`.

### 1.6. Idempotency

| Hạng mục | Quy ước |
|---|---|
| Header | `Idempotency-Key: <uuid>` **bắt buộc** cho mọi mutation tạo tài nguyên/commit (EP-20..23, EP-30..34, EP-40); khuyến nghị cho mutation khác |
| Lưu | Redis, TTL 24 giờ, khóa `(user_id, method, path, Idempotency-Key)` → response đã trả |
| Gọi lại cùng key + cùng body | Trả lại đúng response cũ (cùng status) — không tạo bản ghi mới |
| Cùng key, body khác | `409 IDEMPOTENCY_CONFLICT` |
| Commit nghiệp vụ | Ngoài header, Action Registry dùng `idempotency_key = hash(document_id, field_set_version, action_name)` lưu ở `business_records.idempotency_key` (04 §10.1, 05 §4.8) — chống trùng cả khi retry Celery |

### 1.7. Audit log cho mutation

- Mọi mutation (POST/PUT/PATCH/DELETE) ghi `ENT-AuditLog` (`audit_logs`) **trong cùng transaction** với thay đổi (05 §4.12): `actor_type`, `actor_user_id`, `actor_role_id`, `action`, `target_type`, `target_id`, `source_document_id`, `before`/`after` (lương mask `••••`), `metadata.request_id`, `metadata.idempotency_key`, `ip_address`.
- Ngoài mutation, ghi thêm: chuyển vai trò (`role.switch`), mở tài liệu gốc có PII (`document.open_pii`), bị từ chối mở tài liệu chứa lương (`document.open_denied`), đăng nhập (`auth.login`).
- Cột "Audit action" của mỗi endpoint ghi tên `action`.

### 1.8. Data scoping & dữ liệu nhạy cảm

| # | Quy tắc |
|---|---|
| DS1 | Mọi truy vấn lọc theo role active ở backend trước khi trả (02 §4.1); default deny |
| DS2 | Role `view-agg` với một trụ: chỉ nhận giá trị tổng hợp (`value`, `status_color`, `computed_at`, `formula_display`); **không** có `breakdown` chi tiết theo cá nhân/bản ghi, `source_record_ids`, `source_document_ids`, link tài liệu |
| DS3 | Field lương cá nhân (`business_records.salary`, `extracted_fields` có `sensitivity='SALARY'`) **bị loại khỏi response model** cho mọi role trừ ROLE-04 và ROLE-05 trong ngữ cảnh review (EP-26). Với ROLE-01/02 field xuất hiện dạng `{ "masked": true }` (không có `value`) để UI hiển thị `••••` (06 §7.4); ROLE-03 không nhận field |
| DS4 | Tài liệu `contains_salary=true`: chỉ ROLE-04 mở/tải; ROLE-05 mở trong ngữ cảnh review, không tải; role khác → `403 FORBIDDEN_SALARY` + audit `document.open_denied` |
| DS5 | Lineage ra ngoài scope: không ẩn im lặng — trả mục với `{ "restricted": true, "reason": "OUT_OF_SCOPE" }` (hoặc `SALARY`) để UI hiển thị thông báo (03 §4.4) |
| DS6 | `password_hash` không bao giờ có trong response |

### 1.9. Trạng thái giá trị metric (N/A)

Mọi object metric value trả kèm `value_state` (03 §1.3, 06 §4.1):

| `value_state` | Điều kiện | `value` | `status_color` | Sinh alert |
|---|---|---|---|---|
| `OK` | Tính được | số | `GREEN`/`YELLOW`/`RED` | Theo ngưỡng |
| `NO_DATA` | Không có bản ghi nguồn cho kỳ (`metric_values.value` null / chưa có dòng) | `null` | `null` | Không |
| `NOT_COMPUTABLE` | Mẫu số công thức = 0 hoặc âm / phép tính không xác định (VD CUS-01 chỉ tiêu còn lại ≤ 0; FIN-04 doanh thu kỳ = 0; HR-01/02 headcount = 0; OPS-01/03 không có task/quyết định đến hạn) | `null` | `null` | Không |

Khi `NOT_COMPUTABLE`, response kèm `not_computable_reason` (`DENOMINATOR_ZERO` / `DENOMINATOR_NEGATIVE` / `UNDEFINED`) và `computation_inputs` `{ numerator, denominator }` (nếu role có quyền xem chi tiết) để giữ P01. Giá trị đặc biệt theo 03 (VD METRIC-FIN-03 dòng tiền ròng ≥ 0 → `> 24 tháng`) trả `value_state='OK'`, `value=null`, `display_hint='GT_24_MONTHS'`. Lưu trữ `value_state` là OQ-02.

### 1.10. Danh mục endpoint

> **Đối chiếu code ↔ spec (2026-10-19).** Đã rà các module **Audit (EP-52), Dynamic metric/alert engine (EP-11/EP-31 + recompute nội bộ), UC-07 (EP-40/EP-41)** so với route thực tế trong `apps/api`. Kết quả: **mọi endpoint đã code đều có mặt trong danh mục này — không thiếu endpoint nào cần bổ sung.** Bộ test contract (`uv run pytest -m contract`, **39 pass**) xác nhận `check_documented` không phát hiện route "undocumented" và `missing_endpoints` không liệt kê EP-40/EP-41/EP-52 (đều đã mount). `recompute_metrics` là tác vụ nội bộ sau commit Action Registry (không phải endpoint HTTP công khai — xem §8.3). Spec tiếp tục là **contract nguồn duy nhất**; không có thay đổi contract trong đợt đồng bộ này.

| EP | Method | Path | Nhóm | Role |
|---|---|---|---|---|
| EP-01 | GET | `/health` | Hệ thống | Public |
| EP-02 | POST | `/auth/login` | Auth | Public |
| EP-03 | GET | `/auth/me` | Auth | ROLE-01..05 |
| EP-04 | POST | `/auth/switch-role` | Auth (demo) | ROLE-01..05, chỉ `DEMO_MODE=true` |
| EP-05 | GET | `/auth/demo-users` | Auth (demo) | ROLE-01..05, chỉ `DEMO_MODE=true` |
| EP-10 | GET | `/dashboard` | Dashboard | ROLE-01..04 |
| EP-11 | GET | `/metrics` | Metric | ROLE-01..04 |
| EP-12 | GET | `/metrics/{metric_code}` | Metric detail | ROLE-01..04 |
| EP-13 | GET | `/metrics/{metric_code}/records` | Drill-down click 2 | ROLE-01..04 |
| EP-14 | GET | `/business-records/{id}/lineage` | Drill-down click 3 | ROLE-01..04 |
| EP-15 | GET | `/alerts` | Alert | ROLE-01..04 |
| EP-16 | POST | `/alerts/{id}/acknowledge` | Alert | ROLE-01..04 (theo trụ) |
| EP-17 | POST | `/alerts/{id}/dismiss` | Alert | ROLE-01..04 (theo trụ) |
| EP-20 | POST | `/documents` | IDP upload (C3/C4) | ROLE-01..05 |
| EP-21 | POST | `/documents/manual` | IDP nhập tay (C1) | ROLE-01..05 |
| EP-22 | POST | `/documents/natural-language` | IDP C2 | ROLE-01..05 |
| EP-23 | POST | `/documents/import` | IDP C5 (upload + gợi ý mapping) | ROLE-01..05 |
| EP-36 | POST | `/documents/{id}/import-mapping` | IDP C5 (xác nhận mapping) | Người upload tài liệu đó |
| EP-24 | GET | `/documents` | Tài liệu | ROLE-01..05 |
| EP-25 | GET | `/documents/{id}` | Tài liệu + job status | ROLE-01..05 |
| EP-26 | GET | `/documents/{id}/extraction` | Extraction result | ROLE-01, 02, 04, 05 |
| EP-27 | GET | `/documents/{id}/source` | Tài liệu gốc (presigned URL) | ROLE-01..05 |
| EP-28 | GET | `/review-queue` | Hàng chờ | ROLE-01, 02, 04, 05 |
| EP-29 | POST | `/documents/{id}/review/open` | Mở review (khóa) | ROLE-02, 04, 05 |
| EP-30 | PATCH | `/documents/{id}/fields` | Sửa field | ROLE-02, 04, 05 |
| EP-31 | POST | `/documents/{id}/review/approve` | Duyệt + commit Action Registry | ROLE-02, 04, 05 |
| EP-32 | POST | `/documents/{id}/review/reject` | Từ chối | ROLE-02, 04, 05 |
| EP-33 | POST | `/documents/{id}/rollback` | Hoàn tác | ROLE-02, 04, 05 |
| EP-34 | POST | `/documents/{id}/retry` | Retry FAILED / Vẫn xử lý / Mở lại | ROLE-02, 04, 05 (+ người upload với DUPLICATE) |
| EP-35 | POST | `/documents/{id}/review/release` | Đóng review không lưu | ROLE-02, 04, 05 |
| EP-40 | POST | `/onboarding/batches` | UC-07 tạo batch | ROLE-01, 05 |
| EP-41 | GET | `/onboarding/batches/{batch_id}` | UC-07 tiến độ + tổng hợp + XD | ROLE-01, 05 |
| EP-50 | GET | `/extraction-schemas` | Schema (SCR-11) | ROLE-01..05 (ROLE-01..04 bắt buộc `doc_type`, ẩn SALARY) |
| EP-51 | GET | `/ai-config` | Cấu hình AI chỉ đọc (SCR-15) | ROLE-01, 05 |
| EP-52 | GET | `/audit-logs` | Audit (SCR-14) | ROLE-01 |

Dải số EP để trống (06–09, 18–19, 37–39, 42–49) dành cho mở rộng sau DEC.

---

## 2. Hệ thống & Auth

### EP-01 — Health check

| Thuộc tính | Giá trị |
|---|---|
| Method / Path | `GET /api/v1/health` |
| Role | Public — không `require_role` (CLAUDE.md § API yêu cầu `require_role` cho mọi endpoint trừ health check; EP-02 login cũng bắt buộc public vì chưa có JWT — xem OQ-13) |
| Request | — |
| Response 200 | `data`: `status` (`ok`/`degraded`), `version` (string), `checks` `{ database, redis, storage, model_gateway }` mỗi giá trị `ok`/`fail`, `demo_mode` (bool) |
| Lỗi | `503 DEPENDENCY_UNAVAILABLE` khi DB không sẵn sàng (vẫn trả body `status=degraded`) |
| Audit action | — |
| Liên quan | 07 §10 Observability |

Không trả thông tin nhạy cảm (connection string, model key).

### EP-02 — Đăng nhập

| Thuộc tính | Giá trị |
|---|---|
| Method / Path | `POST /api/v1/auth/login` |
| Role | Public — endpoint đăng nhập bắt buộc không `require_role` vì client chưa có JWT để gửi (07 §8.1.2); gọi từ NextAuth Credentials provider phía server, không gọi trực tiếp từ browser |
| Request | Bảng dưới |
| Response 200 | `data`: `access_token`, `token_type`=`Bearer`, `expires_at`, `user` (UserOut) |
| Lỗi | `401 INVALID_CREDENTIALS`, `422 VALIDATION_ERROR`, `429 RATE_LIMITED` |
| Biện pháp bảo vệ | (1) Rate limit 429 per IP/email (§1.3); (2) Audit `auth.login` cả thành công và thất bại, không ghi mật khẩu; (3) `INVALID_CREDENTIALS` không tiết lộ email tồn tại hay không (thông báo chung); (4) Mật khẩu demo lấy từ seed data (`08-DEMO-DATA-SPEC.md`) / biến môi trường, **không hard-code** trong code |
| Audit action | `auth.login` (cả thành công và thất bại, không ghi mật khẩu) |
| Liên quan | SCR-13; 07 §8.1.2; OQ-13 |

| Field request | Kiểu | Bắt buộc | Ghi chú |
|---|---|---|---|
| email | string (email) | ✅ | lowercase (`users.email`) |
| password | string | ✅ | Không log; demo: hash lấy từ `users.password_hash` (seed, argon2/bcrypt) |

**UserOut** (dùng lại ở EP-03, EP-04, EP-05):

| Field | Kiểu | Nguồn 05 |
|---|---|---|
| id | uuid | `users.id` |
| email | string | `users.email` |
| full_name | string | `users.full_name` |
| salutation | `anh`/`chị`/null | `users.salutation` |
| role | object `{ code, key, name_i18n_key, pillar_scope[], pillar_agg_scope[], review_pillars[], can_view_salary, home_route }` | `roles.*` |
| is_demo_account | bool | `users.is_demo_account` |

### EP-03 — Thông tin phiên hiện tại

| Thuộc tính | Giá trị |
|---|---|
| Method / Path | `GET /api/v1/auth/me` |
| Role | `require_role(ROLE-01..05)` |
| Response 200 | `data`: UserOut + `permissions` (object danh sách capability tính từ ma trận 02 §3, VD `{ "alerts.ack_pillars": ["FIN"], "review.pillars": ["FIN"], "onboarding": false, "audit.read": false }`) + `demo_mode` (bool) |
| Lỗi | `401 UNAUTHENTICATED` |
| Audit action | — |
| Liên quan | SCR-01..05 (render theo role), SCR-12 |

`permissions` chỉ để UI ẩn/hiện; backend vẫn kiểm từng endpoint.

### EP-04 — Chuyển vai trò demo

| Thuộc tính | Giá trị |
|---|---|
| Method / Path | `POST /api/v1/auth/switch-role` |
| Role | `require_role(ROLE-01..05)` **và** `DEMO_MODE=true`; khi `DEMO_MODE=false` router không đăng ký → `404 NOT_FOUND` (07 §8.1.1) |
| Request | `target_role_code` (string `ROLE-01`..`ROLE-05`, bắt buộc) |
| Xử lý | Tìm user seed có `is_demo_account=true` và `roles.code = target_role_code` → cấp **JWT mới** cho user đích (cùng thuật toán/secret/claim §1.4); cập nhật `users.last_login_at`; ghi audit |
| Response 200 | `data`: `access_token`, `token_type`, `expires_at`, `user` (UserOut của user đích), `home_route` |
| Lỗi | `401 UNAUTHENTICATED`; `404 NOT_FOUND` (demo tắt hoặc không có user seed cho role); `422 VALIDATION_ERROR` (mã role sai) |
| Audit action | `role.switch` — `metadata { from_role, to_role, from_user_id, to_user_id }` |
| Hiệu năng | p95 ≤ 300 ms ở server để toàn luồng ≤ 2 giây (02 §5.2 R1) |
| Liên quan | SCR-12; 02 §5; 07 §8.1.1 |

Client: thay JWT trong session NextAuth, `queryClient.clear()`, điều hướng `home_route`. Gọi lại với role đang active → 200 trả token mới (không lỗi). JWT cũ không bị thu hồi (chấp nhận ở demo).

### EP-05 — Danh sách user demo

| Thuộc tính | Giá trị |
|---|---|
| Method / Path | `GET /api/v1/auth/demo-users` |
| Role | `require_role(ROLE-01..05)` + `DEMO_MODE=true` (tắt → 404) |
| Response 200 | `data`: mảng `{ role_code, role_name_i18n_key, full_name, user_id }` — đúng 5 phần tử theo thứ tự ROLE-01..05 |
| Lỗi | `401`, `404` |
| Liên quan | SCR-12 (dropdown), SCR-13 (chọn nhanh — gọi sau đăng nhập) |

---

## 3. Dashboard, Metric, Drill-down, Alert

**MetricValueOut** (dùng ở EP-10..EP-12):

| Field | Kiểu | Nguồn 05 / ghi chú |
|---|---|---|
| metric_code | string | `metrics.code` (`METRIC-FIN-01`) |
| pillar | `FIN`/`CUS`/`OPS`/`HR` | `metrics.pillar` |
| name_i18n_key | string | `metric.<code>.name` (06 §7.2) |
| unit | enum | `metrics.unit` |
| chart_type | string | `metrics.chart_type` |
| access_level | `FULL` / `AGG` | Theo 02 §3.2 với role active |
| period_key | string | `metric_values.period_key` |
| value | number/null | `metric_values.value` |
| value_state | `OK`/`NO_DATA`/`NOT_COMPUTABLE` | §1.9 |
| not_computable_reason | enum/null | §1.9 |
| display_hint | string/null | VD `GT_24_MONTHS` |
| target_value | number/null | `metric_values` `value_kind=TARGET` cùng kỳ |
| status_color | `GREEN`/`YELLOW`/`RED`/null | `metric_values.status_color` |
| warning_threshold, critical_threshold | number | `metrics.*` |
| sparkline | mảng `{ period_key, value }` (≤ 12 điểm) | `metric_values` lịch sử `is_current=true` |
| computed_at | datetime | `metric_values.computed_at` (FreshnessLabel, P01 #3) |
| open_alert | `{ id, alert_code, severity }` / null | `alerts` đang `OPEN`/`ACKNOWLEDGED` |

### EP-10 — Dashboard theo role

| Thuộc tính | Giá trị |
|---|---|
| Method / Path | `GET /api/v1/dashboard` |
| Role | `require_role(ROLE-01, ROLE-02, ROLE-03, ROLE-04)` — ROLE-05 → `403 FORBIDDEN_ROLE` (không có dashboard, 03 §5.1) |
| Query | `period_key` (tùy chọn, mặc định kỳ hiện hành) |
| Response 200 | `data`: `role_code`, `greeting` `{ full_name, salutation }`, `summary` `{ i18n_key, params, suggestion_level: "L1" }` (câu tóm tắt AI, số trong `params` kèm `metric_code`), `pillars[]` `{ pillar, access_level, health_color, open_alert_count, headline_metric: MetricValueOut, metrics: MetricValueOut[] }`, `alerts_top[]` (≤ 5, AlertOut, Critical trước) |
| Scoping | Chỉ trụ/metric trong scope (03 §5.1): ROLE-03 nhận FIN chỉ `METRIC-FIN-01`; ROLE-04 nhận FIN chỉ doanh thu tổng (`access_level=AGG`, phục vụ METRIC-HR-01). Metric ngoài scope **không có trong response**. `alerts_top[]` chỉ chứa alert thuộc trụ role có quyền nhận theo 02 §3.3 (ROLE-04 chỉ `ALERT-HR-*`, không trả `ALERT-FIN-*` dù có view-agg FIN; ROLE-02 chỉ `ALERT-FIN-*`+`ALERT-OPS-*`, không trả `ALERT-CUS-*`/`ALERT-HR-*` dù có view-agg) |
| Lỗi | `401`, `403 FORBIDDEN_ROLE` |
| Hiệu năng | Đọc giá trị tính sẵn (`is_current=true`), p95 ≤ 500 ms (insight ≤ 10 giây, chuyển role ≤ 2 giây) |
| Liên quan | SCR-01..04; METRIC-FIN-01..06, METRIC-CUS-01..05, METRIC-OPS-01..04, METRIC-HR-01..03 |

### EP-11 — Danh sách metric

| Thuộc tính | Giá trị |
|---|---|
| Method / Path | `GET /api/v1/metrics` |
| Role | `require_role(ROLE-01..04)` |
| Query | `pillar` (tùy chọn), `period_key` (tùy chọn) |
| Response 200 | `data`: MetricValueOut[] trong scope |
| Lỗi | `401`, `403 FORBIDDEN_ROLE`, `400 BAD_REQUEST` (`pillar` sai) |
| Liên quan | SCR-01..04 (lưới MetricCard, refetch polling 07 §3.5) |

### EP-12 — Metric detail (drill-down click 1, P01)

| Thuộc tính | Giá trị |
|---|---|
| Method / Path | `GET /api/v1/metrics/{metric_code}` |
| Role | `require_role(ROLE-01..04)` + metric trong scope (ngoài scope → `403 FORBIDDEN_SCOPE`) |
| Query | `period_key`, `history` (int 1..24, mặc định 12) |
| Response 200 | Bảng dưới |
| Lỗi | `401`, `403 FORBIDDEN_ROLE`/`FORBIDDEN_SCOPE`, `404 NOT_FOUND` (mã metric không tồn tại) |
| Liên quan | SCR-09; 03 §4.1–4.2; 05 §7.2 |

| Field `data` | Kiểu | Ghi chú |
|---|---|---|
| metric | MetricValueOut | |
| lineage_panel.formula_display | string | `metrics.formula_display` (P01 #1) |
| lineage_panel.formula_expr | string | `metrics.formula_expr` |
| lineage_panel.source_record_types | string[] | `metrics.source_record_types` (P01 #2) |
| lineage_panel.computed_at | datetime | P01 #3 |
| lineage_panel.computation | `COMPUTED`/`EXTRACTED` | `metric_values.computation` |
| lineage_panel.source_record_count | int | Số bản ghi gốc (P01 #4) — chỉ `FULL` |
| lineage_panel.source_documents | `[{ id, original_filename, doc_type, restricted, reason }]` | P01 #5 — chỉ `FULL`; tài liệu chứa lương với CEO/CFO → `restricted=true, reason=SALARY` |
| computation_inputs | `{ numerator, denominator }` / null | Chỉ khi `FULL`; bắt buộc khi `NOT_COMPUTABLE` |
| history | `[{ period_key, value, target_value, value_state, status_color }]` | TrendChart |
| breakdown | `{ dimension, rows: [{ key, label, value, share, record_filter }] }` / null | `metric_values.breakdown`; `null` khi `AGG` (DS2); `record_filter` dùng gọi EP-13 |
| alert | AlertOut / null | Alert của metric (1-1) |

### EP-13 — Bản ghi gốc của metric (drill-down click 2)

| Thuộc tính | Giá trị |
|---|---|
| Method / Path | `GET /api/v1/metrics/{metric_code}/records` |
| Role | `require_role(ROLE-01..04)` + `access_level=FULL` với trụ của metric (AGG → `403 FORBIDDEN_SCOPE`) |
| Query | `period_key`, `record_filter` (chuỗi lấy từ EP-12 `breakdown`), phân trang §1.5, `sort` (mặc định `-total_amount`) |
| Response 200 | `data`: BusinessRecordOut[] (chỉ bản ghi trong `metric_values.source_record_ids`); `meta`: phân trang + `sum_check` `{ expected, actual }` (tổng khớp metric, 05 §7.3) |
| Lỗi | `401`, `403`, `404` |
| Liên quan | SCR-09 (RecordPanel); 03 §4.1 click 2 |

**BusinessRecordOut** (tên trùng cột `business_records`, 05 §4.8):

| Field | Kiểu | Ghi chú |
|---|---|---|
| id, record_type, pillar, code, series, name, tax_code | | |
| customer_id, employee_id, parent_id | uuid/null | |
| period_key, issue_date, start_date, end_date, due_date, done_at, signed_at | | |
| subtotal, vat_rate, vat_amount, total_amount, paid_amount, amount_due | | Tiền VND số nguyên; `amount_due` generated |
| probability, score, status, department, title, is_critical | | |
| salary | bigint / `{ "masked": true }` / (vắng mặt) | DS3: ROLE-04 có giá trị; ROLE-01/02 `masked`; ROLE-03 không có field |
| attributes | object | |
| source_document_id | uuid/null | Link click 3 (EP-14/EP-27) |
| source_document_restricted | `null` / `OUT_OF_SCOPE` / `SALARY` | DS4/DS5 |
| created_by_action, created_at, updated_at | | |

### EP-14 — Lineage của một bản ghi (drill-down click 3)

| Thuộc tính | Giá trị |
|---|---|
| Method / Path | `GET /api/v1/business-records/{id}/lineage` |
| Role | `require_role(ROLE-01..04)` + bản ghi thuộc trụ có `FULL` |
| Response 200 | `data`: `record` (BusinessRecordOut), `fields[]` `{ field_key, final_value, confidence, source_location, document_page_id, corrected }` (từ `extracted_fields` có `business_record_id = id`; field SALARY theo DS3), `source_document` `{ id, original_filename, doc_type, channel, kind, restricted, reason }`, `review` `{ reviewer_full_name, decided_at, decision }` / null (STP → `actor: "ai:idp"`) |
| Lỗi | `401`, `403 FORBIDDEN_SCOPE`, `404` |
| Liên quan | SCR-09 → SCR-10; 05 §7.1 |

Mở file gốc dùng EP-27 với `page` + `highlight` lấy từ `source_location`.

**AlertOut**:

| Field | Kiểu | Nguồn 05 |
|---|---|---|
| id | uuid | `alerts.id` |
| alert_code | string | `metrics.alert_code` (`ALERT-FIN-01`) |
| metric_code | string | `metrics.code` |
| pillar | enum | |
| severity | `WARNING`/`CRITICAL` | `alerts.severity` |
| status | `OPEN`/`ACKNOWLEDGED`/`RESOLVED`/`DISMISSED` | `alerts.status` |
| period_key | string | |
| title_i18n_key | string | `alert.<code>.title` |
| message_params | object | `alerts.message_params` |
| suggestion_level | `L1` | `alerts.suggestion_level` |
| suggested_action_i18n_key | string | Hành động đề xuất (03 §3.2) |
| triggered_at, acknowledged_at, resolved_at, dismissed_at | datetime/null | |
| can_acknowledge | bool | Theo 02 §3.3 với role active |

### EP-15 — Danh sách alert

| Thuộc tính | Giá trị |
|---|---|
| Method / Path | `GET /api/v1/alerts` |
| Role | `require_role(ROLE-01..04)`; lọc theo 02 §3.3: ROLE-01 mọi `ALERT-*`; ROLE-02 `ALERT-FIN-*`, `ALERT-OPS-*`; ROLE-03 `ALERT-CUS-*`; ROLE-04 `ALERT-HR-*` |
| Query | `status` (mặc định `OPEN,ACKNOWLEDGED`), `severity`, `pillar`, phân trang; `sort` mặc định Critical trước rồi `-triggered_at` |
| Response 200 | `data`: AlertOut[]; `meta` phân trang |
| Lỗi | `401`, `403 FORBIDDEN_ROLE` |
| Liên quan | SCR-01..04 vùng "Cần anh/chị quyết"; ALERT-FIN-01..06, ALERT-CUS-01..05, ALERT-OPS-01..04, ALERT-HR-01..03 |

### EP-16 — Acknowledge alert

| Thuộc tính | Giá trị |
|---|---|
| Method / Path | `POST /api/v1/alerts/{id}/acknowledge` |
| Role | `require_role(ROLE-01..04)` + quyền E theo 02 §3.3: ROLE-01 mọi alert; ROLE-02 `ALERT-FIN-*`; ROLE-03 `ALERT-CUS-*`; ROLE-04 `ALERT-HR-*` (ROLE-02 xem nhưng **không** ack `ALERT-OPS-*`) |
| Request | `note` (string ≤ 500, tùy chọn) |
| Response 200 | `data`: AlertOut (`status=ACKNOWLEDGED`) |
| Lỗi | `401`, `403 FORBIDDEN_SCOPE`, `404`, `409 CONFLICT_STATE` (không ở `OPEN`) |
| Audit action | `alert.acknowledge` |
| Liên quan | SCR-01..04 AlertCard |

### EP-17 — Dismiss alert

| Thuộc tính | Giá trị |
|---|---|
| Method / Path | `POST /api/v1/alerts/{id}/dismiss` |
| Role | Như EP-16 |
| Request | `reason` (string ≤ 500, bắt buộc) |
| Response 200 | `data`: AlertOut (`status=DISMISSED`) |
| Lỗi | `401`, `403`, `404`, `409 CONFLICT_STATE` (đã `RESOLVED`/`DISMISSED`), `422` |
| Audit action | `alert.dismiss` |

Alert engine tự tạo/nâng cấp/đóng alert (`RESOLVED`) — không có endpoint tạo alert thủ công.

---

## 4. IDP — Nhập liệu

**DocumentOut** (dùng ở EP-20..25, EP-28..35; tên trùng cột `source_documents`, 05 §4.3):

| Field | Kiểu | Ghi chú |
|---|---|---|
| id | uuid | |
| batch_id | uuid/null | UC-07 |
| channel | `C1`..`C5` | |
| kind | `FILE`/`MANUAL`/`TRANSCRIPT` | |
| original_filename, mime_type, size_bytes, page_count | | null với tài liệu ảo |
| doc_type | enum 7 loại + `OTHER` / null | |
| pillars | pillar[] | |
| status | `document_status` (14 trạng thái 04 §8.1) | |
| status_reason | string/null | |
| ai_state | `L0`/`L1`/`L2`/`L3`/null | Nhãn AIStateBadge (06 §6.3), suy từ `autonomy_level` + `status` |
| autonomy_level | enum/null | |
| contains_salary, contains_pii | bool | |
| duplicate_of_id | uuid/null | |
| uploaded_by | `{ id, full_name }` | |
| uploaded_at, committed_at, undo_deadline | datetime/null | |
| locked_by | `{ id, full_name }`/null; `locked_until` | Khóa mềm Review |
| retry_count | int | |
| latest_job | JobOut/null | |
| can | `{ review, approve, reject, rollback, retry, open_source, download_source }` | Capability theo role active (UI ẩn/hiện) |

**JobOut** (`extraction_jobs`, 05 §4.5): `id`, `attempt_no`, `status` (`QUEUED`/`RUNNING`/`SUCCEEDED`/`FAILED`), `doc_type`, `classification_confidence`, `avg_confidence`, `routing_decision` (`STP`/`REVIEW`), `routing_reason`, `error_code` (`IDP-E01..E11`), `validation_summary`, `cross_doc_results`, `started_at`, `finished_at`. Không trả `model_route`, `token_cost_usd` cho role khác ROLE-05.

### EP-20 — Upload file (C3/C4, stream)

| Thuộc tính | Giá trị |
|---|---|
| Method / Path | `POST /api/v1/documents` (`multipart/form-data`) |
| Role | `require_role(ROLE-01..05)` (02 §3.4 upload = E mọi role) |
| Header | `Idempotency-Key` bắt buộc |
| Request | Bảng dưới |
| Xử lý | `UploadFile` + **đọc chunked** (không đọc toàn bộ vào RAM) → stream lên MinIO, tính SHA-256 trong lúc stream; kiểm giới hạn sớm; tạo `source_documents` `UPLOADED`; enqueue Celery `process_document` (task id xác định); trùng hash → tạo bản ghi `DUPLICATE` + `duplicate_of_id`, không enqueue |
| Response 201 | `data`: DocumentOut (`status=UPLOADED` hoặc `DUPLICATE`) — trả trong ≤ 2 giây, không chờ xử lý (FR-DC-01) |
| Lỗi | `413 FILE_TOO_LARGE`, `415 UNSUPPORTED_MEDIA_TYPE` (IDP-E01, không tạo document), `422 VALIDATION_ERROR`, `409 IDEMPOTENCY_CONFLICT`. Kill switch L0 không chặn upload: tài liệu được nhận và chờ nhập tay (C1) |
| Audit action | `document.upload` (DUPLICATE: `document.upload_duplicate`) |
| Liên quan | FR-DC-01, FR-DC-04, FR-DC-06, FR-DC-07; US-DC-001, US-DC-004; SCR-08 |

| Field request | Kiểu | Bắt buộc | Ghi chú |
|---|---|---|---|
| file | binary | ✅ | PDF/DOCX/XLSX/CSV/JPG/PNG/HEIC; ≤ `MAX_FILE_SIZE_MB` (20) và ≤ `MAX_PAGES` (50) |
| files | binary[] | — | C4 nhiều ảnh → gộp thành 1 tài liệu nhiều trang (thay cho `file`) |
| channel | `C3`/`C4` | ✅ | |
| doc_type_hint | doc_type | — | Gợi ý của người dùng; AI vẫn phân loại |
| batch_id | uuid | — | Chỉ khi thuộc batch UC-07 (EP-40) |

Khi `DUPLICATE`, response 201 kèm `meta.warning = { code: "DUPLICATE_DOCUMENT", duplicate_of_id }`.

### EP-21 — Nhập tay qua form (C1)

| Thuộc tính | Giá trị |
|---|---|
| Method / Path | `POST /api/v1/documents/manual` |
| Role | `require_role(ROLE-01..05)` |
| Header | `Idempotency-Key` bắt buộc |
| Request | `doc_type` (bắt buộc), `fields` (object theo Extraction Schema của doc type, key = `field_key`), `batch_id` (tùy chọn) |
| Xử lý | Validate server theo schema (zod phía client tương ứng); tạo `source_documents` `kind=MANUAL`, `channel=C1`, `manual_payload`; tạo `extracted_fields` với `confidence=1.0`, `source_location.kind=manual`; chạy validation + XD → định tuyến (C1 vẫn qua Action Registry) |
| Response 201 | `data`: DocumentOut |
| Lỗi | `422 VALIDATION_ERROR` (VD MST sai — `details.fields`), `403 FORBIDDEN_ROLE`, `409 IDEMPOTENCY_CONFLICT` |
| Audit action | `document.manual_create` |
| Liên quan | FR-DC-02, FR-DC-12, FR-DC-13; US-DC-002; SCR-08 |

### EP-22 — Nhập ngôn ngữ tự nhiên (C2)

| Thuộc tính | Giá trị |
|---|---|
| Method / Path | `POST /api/v1/documents/natural-language` (`multipart/form-data` khi có audio) |
| Role | `require_role(ROLE-01..05)` |
| Header | `Idempotency-Key` bắt buộc |
| Request | `text` (string ≤ 2.000) **hoặc** `audio` (binary ≤ 60 giây); `batch_id` (tùy chọn) |
| Xử lý | Tạo `source_documents` `kind=TRANSCRIPT`, `channel=C2`; STT (nếu audio) qua ModelGateway; luôn `NEEDS_REVIEW` mức L2 (không STP, S6) |
| Response 201 | `data`: DocumentOut |
| Lỗi | `422`, `423 AI_DISABLED` (kill switch L0), `415` (audio sai định dạng) |
| Audit action | `document.nl_create` |
| Liên quan | FR-DC-03; US-DC-003; SCR-08 (P1) |

### EP-23 — Import Excel/CSV hàng loạt (C5) — bước 1

| Thuộc tính | Giá trị |
|---|---|
| Method / Path | `POST /api/v1/documents/import` (`multipart/form-data`) |
| Role | `require_role(ROLE-01..05)` |
| Header | `Idempotency-Key` bắt buộc |
| Request | `file` (XLSX/CSV, ≤ 5.000 dòng), `doc_type` (tùy chọn), `batch_id` (tùy chọn) |
| Response 201 | `data`: DocumentOut + `mapping_suggestion` `{ sheet_name, header_row, columns: [{ column, header, suggested_field_key, confidence }] }` (AI gợi ý, L1) |
| Lỗi | `413`, `415`, `422` (vượt 5.000 dòng), `423 AI_DISABLED` (không gợi ý được — trả `mapping_suggestion` rỗng, không lỗi) |
| Audit action | `document.import_upload` |
| Liên quan | FR-DC-05, FR-DC-11; US-DC-005; SCR-08 |

### EP-36 — Import C5 — bước 2: xác nhận mapping

| Thuộc tính | Giá trị |
|---|---|
| Method / Path | `POST /api/v1/documents/{id}/import-mapping` |
| Role | `require_role(ROLE-01..05)` + phải là người upload tài liệu (`uploaded_by_id`) |
| Header | `Idempotency-Key` bắt buộc |
| Request | `doc_type`, `columns: [{ column, field_key }]` (người xác nhận) |
| Xử lý | Mỗi dòng → nhóm `extracted_fields` (`record_group` = dòng, `source_location.kind=cell` với sheet/row/col) → validation → định tuyến |
| Response 200 | `data`: DocumentOut + `row_errors: [{ row_index, field_key, code }]` (dòng lỗi không chặn dòng hợp lệ, IDP-E11) |
| Lỗi | `403 FORBIDDEN_SCOPE` (không phải người upload), `409 CONFLICT_STATE` (đã xác nhận), `422` |
| Audit action | `document.import_mapping_confirm` |
| Liên quan | FR-DC-05; US-DC-005 |

### EP-24 — Danh sách tài liệu

| Thuộc tính | Giá trị |
|---|---|
| Method / Path | `GET /api/v1/documents` |
| Role | `require_role(ROLE-01..05)`; scope 02 §3.4: ROLE-01 & ROLE-05 tất cả; ROLE-02 trụ FIN + của mình; ROLE-03 của mình; ROLE-04 trụ HR + của mình |
| Query | `status`, `doc_type`, `pillar`, `channel`, `batch_id`, `uploaded_by_id`, `q` (tên file), phân trang; `sort` mặc định `-uploaded_at` |
| Response 200 | `data`: DocumentOut[]; `meta` phân trang |
| Lỗi | `401`, `400` |
| Liên quan | SCR-07; polling tiến độ (07 §3.3) |

### EP-25 — Chi tiết tài liệu + trạng thái job

| Thuộc tính | Giá trị |
|---|---|
| Method / Path | `GET /api/v1/documents/{id}` |
| Role | `require_role(ROLE-01..05)` + tài liệu trong scope EP-24 (ngoài → `403 FORBIDDEN_SCOPE`) |
| Response 200 | `data`: DocumentOut + `jobs` (JobOut[] theo `attempt_no`), `status_timeline` `[{ status, at, actor_type }]` (từ `audit_logs`), `affected` `{ business_record_ids, metric_codes }` (sau commit, theo scope), `reviews` `[{ reviewer_full_name, decision, reject_reason_code, decided_at }]` |
| Lỗi | `401`, `403`, `404` |
| Polling | Frontend `refetchInterval` 2–5 giây khi `status` ∈ {`UPLOADED`,`PREPROCESSING`,`CLASSIFYING`,`EXTRACTING`,`VALIDATING`,`AUTO_APPROVED`,`APPROVED`} |
| Liên quan | FR-DC-15, FR-DC-22; US-DC-017, US-DC-019; SCR-07, SCR-08 (progress) |

### EP-26 — Kết quả trích xuất

| Thuộc tính | Giá trị |
|---|---|
| Method / Path | `GET /api/v1/documents/{id}/extraction` |
| Role | `require_role(ROLE-01, ROLE-02, ROLE-04, ROLE-05)` — ROLE-03 → `403 FORBIDDEN_ROLE` (02 §3.4 không xem hàng chờ); ROLE-02 chỉ trụ FIN; ROLE-04 chỉ trụ HR |
| Response 200 | `data`: `document` (DocumentOut), `job` (JobOut), `fields` (ExtractedFieldOut[]), `cross_doc_results`, `validation_summary`, `suspicious_content` (bool, PI) |
| Dữ liệu lương | ROLE-04: đầy đủ. ROLE-05: đầy đủ **chỉ khi** tài liệu đang `IN_REVIEW` do chính user khóa (ngữ cảnh review). ROLE-01: field `sensitivity=SALARY` trả `{ field_key, masked: true }` (không `value`, `raw_text`, `source_location`); với tài liệu `contains_salary` CEO chỉ nhận metadata (02 §3.4 ghi chú) |
| Lỗi | `401`, `403 FORBIDDEN_ROLE`/`FORBIDDEN_SCOPE`, `404`, `409 CONFLICT_STATE` (chưa có job `SUCCEEDED`) |
| Liên quan | FR-DC-08, FR-DC-10, FR-DC-11, FR-DC-13, FR-DC-14; US-DC-006..010; SCR-06 |

**ExtractedFieldOut** (`extracted_fields`, 05 §4.6):

| Field | Kiểu | Ghi chú |
|---|---|---|
| id | uuid | |
| field_key, table_key, row_index, record_group | | |
| value | any/null | Giá trị AI đã chuẩn hóa — `null` nếu không tìm thấy |
| raw_text | string/null | |
| value_type | enum | |
| confidence | number 0–1 | Bắt buộc mọi field |
| confidence_band | `HIGH`/`MEDIUM`/`LOW` | ≥ 0,90 / 0,70–< 0,90 / < 0,70 (04 §7.2) |
| source_location | object `{ kind, page, bbox, sheet, row, col, paragraph }` | Bắt buộc mọi field |
| document_page_id | uuid/null | |
| validation | `[{ rule, status }]` | |
| sensitivity | `NONE`/`PII`/`SALARY` | |
| corrected, corrected_value, final_value | | |
| required | bool | Từ Extraction Schema |
| masked | bool | `true` khi DS3 áp dụng (khi đó vắng `value`, `raw_text`, `corrected_value`, `final_value`, `source_location`) |

### EP-27 — Tài liệu gốc (presigned URL)

| Thuộc tính | Giá trị |
|---|---|
| Method / Path | `GET /api/v1/documents/{id}/source` |
| Role | `require_role(ROLE-01..05)` + scope EP-24 + DS4 |
| Query | `page` (int, tùy chọn), `disposition` (`inline` mặc định / `attachment` = tải xuống) |
| Response 200 | `data`: `url` (presigned MinIO/S3, hết hạn ≤ 15 phút), `expires_at`, `mime_type`, `page_count`, `pages` `[{ page_number, image_url, width_px, height_px, ocr_used, ocr_confidence }]` (cho SourceViewer + HighlightOverlay), `manual_info` `{ created_by_full_name, created_at }` với tài liệu ảo C1/C2 (không có `url`) |
| Quy tắc lương | `contains_salary=true`: ROLE-04 mở + tải; ROLE-05 chỉ khi đang review tài liệu đó và `disposition=inline` (attachment → `403 FORBIDDEN_SALARY`); role khác → `403 FORBIDDEN_SALARY` |
| Lỗi | `401`, `403 FORBIDDEN_SCOPE`/`FORBIDDEN_SALARY`, `404` |
| Audit action | `document.open_pii` khi `contains_pii`; `document.open_denied` khi bị từ chối do lương; `document.download` khi `attachment` |
| Liên quan | FR-DC-18, FR-DC-20; SCR-10, SCR-06; 03 §4.1 click 3 |

---

## 5. IDP — Review, Commit, Hoàn tác

Quy tắc chung nhóm này:
- Quyền duyệt theo `roles.review_pillars` (02 §3.4): ROLE-05 mọi trụ; ROLE-02 chỉ tài liệu có `pillars ⊆ {FIN}`; ROLE-04 chỉ `{HR}`. Tài liệu CUS, OPS và #7 (KPI/OKR đa trụ) chỉ ROLE-05. ROLE-01, ROLE-03 → `403 FORBIDDEN_ROLE`.
- Chuyển trạng thái phải hợp lệ theo 04 §8.2, nếu không → `409 CONFLICT_STATE` với `details { from, to }`.
- Mọi ghi dữ liệu nghiệp vụ **chỉ qua Action Registry** (FR-DC-17, CLAUDE.md § IDP Worker); endpoint không ghi ORM nghiệp vụ trực tiếp.

### EP-28 — Hàng chờ review

| Thuộc tính | Giá trị |
|---|---|
| Method / Path | `GET /api/v1/review-queue` |
| Role | `require_role(ROLE-01, ROLE-02, ROLE-04, ROLE-05)`; ROLE-01 chỉ xem (02 §3.4), tài liệu `contains_salary` chỉ trả metadata |
| Query | `status` (mặc định `NEEDS_REVIEW,IN_REVIEW,FAILED`), `doc_type`, `pillar`, `batch_id`, `confidence_band`, phân trang |
| Sắp xếp | Mặc định: có conflict XD blocking → confidence thấp → `uploaded_at` cũ nhất (FR-DC-16) |
| Response 200 | `data`: `[{ document: DocumentOut, routing_reason, avg_confidence, fields_to_check (int), has_conflict (bool), locked_by, locked_until }]`; `meta` phân trang + `counts { needs_review, in_review, failed }` |
| Lỗi | `401`, `403 FORBIDDEN_ROLE` (ROLE-03) |
| Liên quan | FR-DC-15, FR-DC-16; US-DC-011; SCR-05 |

### EP-29 — Mở review (khóa mềm)

| Thuộc tính | Giá trị |
|---|---|
| Method / Path | `POST /api/v1/documents/{id}/review/open` |
| Role | `require_role(ROLE-02, ROLE-04, ROLE-05)` + `review_pillars` |
| Xử lý | `NEEDS_REVIEW` → `IN_REVIEW`; set `locked_by_id`, `locked_until = now + 15 phút`; tạo `extraction_reviews` với `opened_at` (đo KPI ≤ 60 giây). Cùng user gọi lại → gia hạn khóa |
| Response 200 | `data`: DocumentOut + `review_id` + `extraction` (như EP-26) |
| Lỗi | `403`, `404`, `409 REVIEW_LOCKED` (`details.locked_by`, `locked_until`), `409 CONFLICT_STATE` |
| Audit action | `review.open` |
| Liên quan | FR-DC-18; US-DC-012; SCR-06 |

### EP-35 — Đóng review không lưu

| Thuộc tính | Giá trị |
|---|---|
| Method / Path | `POST /api/v1/documents/{id}/review/release` |
| Role | `require_role(ROLE-02, ROLE-04, ROLE-05)` + đang giữ khóa (`locked_by_id` = current user) |
| Xử lý | `IN_REVIEW` → `NEEDS_REVIEW`; xóa khóa; `extraction_reviews.decision = ABANDONED`. Hết hạn khóa → hệ thống tự làm tương tự |
| Response 200 | `data`: DocumentOut |
| Lỗi | `403` (không giữ khóa), `409 CONFLICT_STATE` |
| Audit action | `review.release` |

### EP-30 — Sửa field (và đổi doc type)

| Thuộc tính | Giá trị |
|---|---|
| Method / Path | `PATCH /api/v1/documents/{id}/fields` |
| Role | `require_role(ROLE-02, ROLE-04, ROLE-05)` + `review_pillars` + đang giữ khóa (`IN_REVIEW`) |
| Header | `Idempotency-Key` bắt buộc |
| Request | Bảng dưới |
| Xử lý | Ghi `corrected=true`, `corrected_value`, `corrected_by_id`; giữ `value` của AI; chạy lại validation field + XD liên quan. Đổi `doc_type` (khi classification < 0,80, FR-DC-08) → enqueue extract lại, tài liệu về `EXTRACTING` |
| Response 200 | `data`: `fields` (ExtractedFieldOut[] đã cập nhật), `validation_summary`, `cross_doc_results` |
| Lỗi | `403`, `409 CONFLICT_STATE` (không `IN_REVIEW`/không giữ khóa), `422 VALIDATION_ERROR` (giá trị sai kiểu/định dạng) |
| Audit action | `field.correct` (before/after; lương mask `••••`), `document.change_doc_type` |
| Liên quan | FR-DC-12, FR-DC-13, FR-DC-19; US-DC-013; SCR-06 |

| Field request | Kiểu | Bắt buộc | Ghi chú |
|---|---|---|---|
| fields | `[{ id, corrected_value }]` | — | `corrected_value` theo `value_type`; `null` = xác nhận không có |
| confirmed_field_ids | uuid[] | — | Xác nhận field vàng/đỏ không đổi giá trị |
| doc_type | doc_type | — | Đổi loại tài liệu |
| split_ranges | `[{ from_page, to_page }]` | — | Chỉnh ranh giới tài liệu ghép (FR-DC-09, P1) |

### EP-31 — Duyệt + commit qua Action Registry

| Thuộc tính | Giá trị |
|---|---|
| Method / Path | `POST /api/v1/documents/{id}/review/approve` |
| Role | `require_role(ROLE-02, ROLE-04, ROLE-05)` + `review_pillars` + giữ khóa |
| Header | `Idempotency-Key` bắt buộc |
| Request | `review_id` (uuid, bắt buộc), `field_ids` (uuid[], tùy chọn — duyệt từng phần; mặc định toàn bộ), `accepted_conflicts` `[{ rule, note }]` (chấp nhận chênh lệch XD, bắt buộc ghi chú) |
| Điều kiện | Mọi field `required` có `confidence_band=LOW` hoặc `value=null` phải đã được sửa/xác nhận (EP-30) → nếu không `422 VALIDATION_ERROR` với `details.fields`; XD `MISMATCH` blocking chưa chấp nhận → `422 ACTION_REJECTED` |
| Xử lý | `IN_REVIEW` → `APPROVED` → gọi Action Registry theo doc type (04 §10.2: `invoice.create`, `contract.create`, `task.create_from_minutes`, `employee.upsert`, `metric_value.upsert`, `metric_target.upsert`) với `idempotency_key = hash(document_id, field_set_version, action_name)` → một transaction (business_records/metric_values + lineage `extracted_fields.business_record_id`/`committed_metric_value_id` + audit) → `COMMITTED`, `committed_at`, `undo_deadline = +7 ngày` → enqueue `recompute_metrics(affected_metric_ids)` |
| Response 200 | `data`: DocumentOut (`COMMITTED`), `review` `{ id, decision: "APPROVED", decided_at, duration_ms, fields_corrected }`, `commit` `{ actions: [{ action_name, business_record_ids, metric_value_ids }], affected_metric_codes, recompute_job_id }` |
| Lỗi | `403`, `409 CONFLICT_STATE`/`REVIEW_LOCKED`, `422 VALIDATION_ERROR`/`ACTION_REJECTED` (IDP-E10: rollback, tài liệu về `NEEDS_REVIEW`, `details.reason`) |
| Audit action | `review.approve` + mỗi action `<action_name>` (actor = user) |
| Liên quan | FR-DC-17, FR-DC-19, FR-DC-20; US-DC-012, US-DC-014; SCR-06 → SCR-09; METRIC-* bị ảnh hưởng theo 05 §9.1 |

Commit STP (L3, `AUTO_APPROVED`) do worker gọi Action Registry nội bộ, **không** qua endpoint; audit actor `ai:idp`.

### EP-32 — Từ chối

| Thuộc tính | Giá trị |
|---|---|
| Method / Path | `POST /api/v1/documents/{id}/review/reject` |
| Role | Như EP-31 |
| Header | `Idempotency-Key` bắt buộc |
| Request | `review_id` (bắt buộc), `reject_reason_code` (bắt buộc: `WRONG_DOC_TYPE`, `UNREADABLE`, `DUPLICATE_BUSINESS`, `WRONG_DATA`, `SUSPICIOUS_CONTENT`, `OTHER`), `reject_note` (bắt buộc khi `OTHER`, ≤ 1.000) |
| Xử lý | Action `document.reject`: `IN_REVIEW` → `REJECTED`; `extraction_reviews.decision=REJECTED` |
| Response 200 | `data`: DocumentOut (`REJECTED`) |
| Lỗi | `403`, `409`, `422` (thiếu lý do) |
| Audit action | `review.reject` |
| Liên quan | FR-DC-19; US-DC-013; SCR-06 |

Danh mục `reject_reason_code` là đề xuất (OQ-05).

### EP-33 — Hoàn tác commit

| Thuộc tính | Giá trị |
|---|---|
| Method / Path | `POST /api/v1/documents/{id}/rollback` |
| Role | `require_role(ROLE-02, ROLE-04, ROLE-05)` + `review_pillars` (04 §8.2: CEO **không** hoàn tác) |
| Header | `Idempotency-Key` bắt buộc |
| Request | `reason` (string ≤ 500, bắt buộc) |
| Điều kiện | `status=COMMITTED` và `now ≤ undo_deadline` |
| Xử lý | Action `document.rollback`: hoàn tác các action đã ghi (soft delete bản ghi, khôi phục `previous_snapshot`, `metric_values` `superseded_by_id`) trong một transaction → `ROLLED_BACK` → recompute metric + alert |
| Response 200 | `data`: DocumentOut (`ROLLED_BACK`), `affected_metric_codes` |
| Lỗi | `403`, `409 CONFLICT_STATE`, `410 UNDO_EXPIRED` |
| Audit action | `document.rollback` |
| Liên quan | FR-DC-21, FR-DC-22; US-DC-015; SCR-07; nút "Hoàn tác" L3 (06 §6.3) |

### EP-34 — Thử lại / Vẫn xử lý / Mở lại

| Thuộc tính | Giá trị |
|---|---|
| Method / Path | `POST /api/v1/documents/{id}/retry` |
| Role | `FAILED` → `PREPROCESSING`: ROLE-02 (FIN), ROLE-04 (HR), ROLE-05 (mọi trụ). `REJECTED` → `NEEDS_REVIEW` (mở lại): như trên. `DUPLICATE` → `PREPROCESSING` ("Vẫn xử lý"): người upload hoặc ROLE-05 |
| Header | `Idempotency-Key` bắt buộc |
| Request | `mode` (`RETRY` / `REOPEN` / `FORCE_DUPLICATE`, bắt buộc), `note` (tùy chọn) |
| Xử lý | `RETRY`: tạo `extraction_jobs` mới (`attempt_no+1`), enqueue; `REOPEN`: undo `document.reject`; `FORCE_DUPLICATE`: xử lý như tài liệu mới |
| Response 202 | `data`: DocumentOut |
| Lỗi | `403`, `409 CONFLICT_STATE` (mode không khớp trạng thái), `422` |
| Audit action | `document.retry` / `document.reopen` / `document.force_duplicate` |
| Liên quan | FR-DC-06, FR-DC-22; US-DC-019; SCR-05, SCR-07 |

---

## 6. UC-07 — Nạp doanh nghiệp (batch)

Batch là thuộc tính `batch_id` trên `source_documents` (05 M3), không phải entity. Upload từng file trong batch dùng lại EP-20/EP-23 kèm `batch_id`.

### EP-40 — Tạo batch onboarding

| Thuộc tính | Giá trị |
|---|---|
| Method / Path | `POST /api/v1/onboarding/batches` |
| Role | `require_role(ROLE-01, ROLE-05)` (02 §3.4 UC-07 = E chỉ CEO, Reviewer) |
| Header | `Idempotency-Key` bắt buộc |
| Request | `expected_doc_types` (doc_type[], tùy chọn — mặc định 7 loại checklist), `label` (string ≤ 100, tùy chọn) |
| Xử lý | Sinh `batch_id` (uuid); lưu checklist trong audit `metadata` (không có bảng batch) |
| Response 201 | `data`: `batch_id`, `checklist` `[{ doc_type, required: true }]` (7 loại), `upload_endpoint` = `/api/v1/documents` |
| Lỗi | `401`, `403 FORBIDDEN_ROLE` (ROLE-02/03/04), `409 IDEMPOTENCY_CONFLICT` |
| Audit action | `onboarding.batch_create` |
| Liên quan | FR-DC-23; US-DC-016; SCR-08 (chế độ UC-07, bước 1–2); UC-07 |

EP-20/EP-23 với `batch_id` chỉ chấp nhận khi người gọi có quyền UC-07 (ROLE-01/05), nếu không → `403 FORBIDDEN_ROLE`.

### EP-41 — Tiến độ + tổng hợp + đối chiếu chéo batch

| Thuộc tính | Giá trị |
|---|---|
| Method / Path | `GET /api/v1/onboarding/batches/{batch_id}` |
| Role | `require_role(ROLE-01, ROLE-05)` |
| Polling | 2 giây khi còn tài liệu đang xử lý (07 §3.3) |
| Response 200 | Bảng dưới |
| Lỗi | `401`, `403`, `404` (batch không tồn tại / không có tài liệu) |
| Liên quan | FR-DC-14, FR-DC-23; US-DC-016; SCR-08 (bước 3–5) → SCR-05 (lọc `batch_id`) → SCR-01 |

| Field `data` | Kiểu | Ghi chú |
|---|---|---|
| batch_id | uuid | |
| documents | `[{ document: DocumentOut, progress_step }]` | Tiến độ từng file theo `status` (bước 3) |
| summary | `{ total, processing, stp_committed, needs_review, failed, duplicate, other, avg_confidence, high_confidence_ratio }` | Bước 4 |
| checklist | `[{ doc_type, present: bool, document_ids[] }]` | 7 loại, đánh dấu đủ/thiếu (UC07-E1) |
| cross_checks | `[{ rule: "XD-01".."XD-05", result: "MATCH"/"MISMATCH"/"NOT_COMPARABLE", severity, params, document_ids[] }]` | Bước 5; XD-01 theo 04 §12.1 (doanh thu tháng 09/2026 trong BCTC vs SUM(`subtotal`) hóa đơn T9, ±0,5%) |
| is_complete | bool | Không còn tài liệu ở trạng thái xử lý |
| next | `{ review_queue_filter: { batch_id }, dashboard_route }` | Bước 6–7 |

Với CEO, tài liệu `contains_salary` trong batch chỉ trả metadata (02 §3.4).

---

## 7. Cấu hình & tra cứu (chỉ đọc)

### EP-50 — Extraction Schema

| Thuộc tính | Giá trị |
|---|---|
| Method / Path | `GET /api/v1/extraction-schemas` |
| Role | `require_role(ROLE-01, ROLE-02, ROLE-03, ROLE-04, ROLE-05)` — ROLE-05 đọc tất cả doc type; ROLE-01..04 **bắt buộc** tham số `doc_type` và chỉ trả field không `SALARY` (OQ-06) |
| Query | `doc_type` (bắt buộc với ROLE-01..04; tùy chọn với ROLE-05) |
| Response 200 | `data`: `[{ doc_type, field_set_version, fields: [{ field_key, table_key, value_type, required, sensitivity, validation_rules[] }] }]` (04 §5) — ROLE-01..04: field `sensitivity='SALARY'` bị loại khỏi response |
| Lỗi | `401`, `403` |
| Liên quan | SCR-11; FR-DC-02, FR-DC-10 |

Ghi chú: form C1 (SCR-08) cần schema cho mọi role → ROLE-01..04 gọi EP-50 với `doc_type` bắt buộc; field `sensitivity='SALARY'` bị ẩn (DS3). ROLE-05 đọc tất cả doc type không restrictions. Không có endpoint sửa schema (02 §3.4). Quyền đọc EP-50 cho ROLE-01..04 chưa có dòng tương ứng trong 02 §3.6 (OQ-06).

### EP-51 — Cấu hình AI (chỉ đọc)

| Thuộc tính | Giá trị |
|---|---|
| Method / Path | `GET /api/v1/ai-config` |
| Role | `require_role(ROLE-01, ROLE-05)` — **chỉ đọc** |
| Response 200 | `data`: `kill_switch` `{ enabled: bool, mode: "L0"/"L2"/null }`, `doc_types` `[{ doc_type, autonomy_level, max_autonomy_level }]`, `thresholds` `{ field_high: 0.90, field_low: 0.70, classification_min: 0.80, stp_classification: 0.95 }`, `source: "SEED"` |
| Lỗi | `401`, `403` |
| Liên quan | FR-DC-21; US-DC-017; SCR-15 |

Không có endpoint ghi cấu hình AI/kill switch trong MVP (02 §3.6). Quyền đọc này của ROLE-01/05 chưa có dòng tương ứng trong 02 §3.6 (OQ-01).

### EP-52 — Audit log

| Thuộc tính | Giá trị |
|---|---|
| Method / Path | `GET /api/v1/audit-logs` |
| Role | `require_role(ROLE-01)` (02 §3.6) |
| Query | `from`, `to` (datetime), `actor_type`, `actor_user_id`, `action`, `target_type`, `source_document_id`, phân trang; `sort` mặc định `-occurred_at` |
| Response 200 | `data`: `[{ id, occurred_at, actor_type, actor { id, full_name } / "ai:idp", actor_role_code, action, target_type, target_id, source_document_id, before, after, metadata }]` — lương luôn mask `••••` |
| Lỗi | `401`, `403`, `400` |
| Liên quan | FR-DC-22; SCR-14 |

Audit log chỉ append — không có PUT/PATCH/DELETE.

---

## 8. Ma trận truy vết

### 8.1. Endpoint ↔ SCR

| SCR | Endpoint |
|---|---|
| SCR-01..04 Dashboard | EP-10, EP-11, EP-15, EP-16, EP-17 |
| SCR-05 Hàng chờ | EP-28, EP-34 |
| SCR-06 Review | EP-26, EP-27, EP-29, EP-30, EP-31, EP-32, EP-35 |
| SCR-07 Tài liệu | EP-24, EP-25, EP-33, EP-34 |
| SCR-08 Upload / UC-07 | EP-20, EP-21, EP-22, EP-23, EP-36, EP-40, EP-41, EP-50 |
| SCR-09 Metric Detail | EP-12, EP-13, EP-14 |
| SCR-10 Source Viewer | EP-27 |
| SCR-11 Schema | EP-50 |
| SCR-12 Role Switcher | EP-04, EP-05 |
| SCR-13 Đăng nhập | EP-02, EP-03 |
| SCR-14 Audit | EP-52 |
| SCR-15 Cấu hình AI | EP-51 |

### 8.2. FR-DC ↔ Endpoint

| FR-DC | Endpoint | FR-DC | Endpoint |
|---|---|---|---|
| FR-DC-01 | EP-20 | FR-DC-13 | EP-21, EP-26, EP-30 |
| FR-DC-02 | EP-21, EP-50 | FR-DC-14 | EP-26, EP-30, EP-41 |
| FR-DC-03 | EP-22 | FR-DC-15 | EP-25, EP-28 |
| FR-DC-04 | EP-20 | FR-DC-16 | EP-28 |
| FR-DC-05 | EP-23, EP-36 | FR-DC-17 | EP-31, EP-32, EP-33 |
| FR-DC-06 | EP-20, EP-34 | FR-DC-18 | EP-26, EP-27, EP-29 |
| FR-DC-07 | EP-20, EP-27 (pages) | FR-DC-19 | EP-30, EP-31, EP-32 |
| FR-DC-08 | EP-26, EP-30 | FR-DC-20 | EP-31, EP-14 |
| FR-DC-09 | EP-30 (`split_ranges`) | FR-DC-21 | EP-51, EP-33 |
| FR-DC-10 | EP-26 | FR-DC-22 | EP-25, EP-33, EP-34, EP-52 |
| FR-DC-11 | EP-23, EP-26 | FR-DC-23 | EP-40, EP-41 |
| FR-DC-12 | EP-21, EP-30 | | |

FR-DC-07..15 thực thi chủ yếu trong worker (Celery); endpoint chỉ phơi kết quả.

### 8.3. Metric / Alert ↔ Endpoint

| Nhóm | Endpoint đọc | Endpoint ghi gián tiếp |
|---|---|---|
| METRIC-FIN-01..06, METRIC-CUS-01..05, METRIC-OPS-01..04, METRIC-HR-01..03 | EP-10, EP-11, EP-12, EP-13, EP-14 | EP-31, EP-33 (qua Action Registry + `recompute_metrics`) |
| ALERT-FIN-01..06, ALERT-CUS-01..05, ALERT-OPS-01..04, ALERT-HR-01..03 | EP-10 (`alerts_top`), EP-12, EP-15 | EP-16, EP-17; alert engine sau recompute |

### 8.4. Endpoint ↔ quyền role (tóm tắt)

| Endpoint | ROLE-01 CEO | ROLE-02 CFO | ROLE-03 Sales Dir | ROLE-04 HR Mgr | ROLE-05 Reviewer |
|---|---|---|---|---|---|
| EP-10..14 | ✅ 4 trụ | ✅ FIN, OPS (CUS/HR agg) | ✅ CUS + FIN-01 (OPS agg) | ✅ HR, OPS (FIN agg) | — |
| EP-15 xem / EP-16, 17 | ✅ / ✅ mọi | ✅ FIN+OPS / FIN | ✅ CUS / CUS | ✅ HR / HR | — |
| EP-20..23, 36 upload | ✅ | ✅ | ✅ | ✅ | ✅ |
| EP-24, 25, 27 | ✅ tất cả (lương chặn) | FIN + của mình | của mình | HR + của mình | ✅ tất cả |
| EP-26, 28 | ✅ chỉ xem (lương mask) | FIN | — | HR | ✅ |
| EP-29..35 review/commit/undo | — | FIN | — | HR | ✅ |
| EP-40, 41 UC-07 | ✅ | — | — | — | ✅ |
| EP-50 | ✅ (doc_type, ẩn SALARY) | ✅ (doc_type, ẩn SALARY) | ✅ (doc_type, ẩn SALARY) | ✅ (doc_type, ẩn SALARY) | ✅ tất cả |
| EP-51 | ✅ đọc | — | — | — | ✅ đọc |
| EP-52 | ✅ | — | — | — | — |
| EP-04, 05 (demo) | ✅ | ✅ | ✅ | ✅ | ✅ |

---

## 9. Open questions

| ID | Câu hỏi | Ảnh hưởng | Đề xuất tạm |
|---|---|---|---|
| OQ-01 | EP-51 (đọc cấu hình AI, SCR-15) cho ROLE-01/ROLE-05: quyền này **chưa có dòng** trong 02 §3.6; cũng chưa có endpoint ghi autonomy/kill switch (04 OQ-04) | 02, 06 | Giữ chỉ đọc; captain raise DEC bổ sung dòng vào 02 §3.6 |
| OQ-02 | `value_state` / `not_computable_reason` (§1.9) không có cột trong `metric_values` (05 §4.10) — tính khi đọc hay thêm cột? | 05 | Tính khi đọc từ `breakdown`/`computation`; nếu cần lưu → cập nhật 05 trước |
| OQ-03 | Thông tin batch UC-07 (checklist, `label`) không có bảng (05 M3) — EP-40 lưu tạm trong `audit_logs.metadata` | 05 | Giữ; nếu cần truy vấn nhiều → DEC thêm entity |
| OQ-04 | Lưu trữ Idempotency-Key ở Redis (TTL 24h) — đủ cho demo hay cần bảng DB | 07 | Redis |
| OQ-05 | Danh mục `reject_reason_code` (EP-32) là đề xuất, 04 chỉ nói "bắt buộc chọn lý do" | 04, 06 | Dùng 6 mã §5 EP-32 |
| OQ-06 | EP-50: 02/06 chỉ cấp SCR-11 cho ROLE-05, nhưng form C1 (SCR-08) cần schema cho mọi role. File này chốt: `require_role(ROLE-01..05)`, ROLE-01..04 bắt buộc `doc_type` + ẩn field SALARY. Cần DEC xác nhận trong 02 §3.6 | 02, 06 | Chốt ROLE-01..05 đọc, ROLE-01..04 ẩn SALARY; chờ DEC |
| OQ-07 | Phím tắt Review lệch giữa 04 FR-DC-18 (Enter/E/R) và 06 §4.3 (Ctrl+Enter/Ctrl+Backspace) — API không phụ thuộc, cần chốt ở 06/04 | 04, 06 | Ngoài phạm vi 10 |
| OQ-08 | Polling vs SSE (07 OQ-06) — file này giả định polling (EP-25, EP-41, EP-11) | 07 | Polling |
| OQ-09 | Tóm tắt AI trên dashboard (EP-10 `summary`) và Panel AI hỏi đáp (06 §5) — Panel AI chưa có endpoint vì 07 OQ-13 chưa chốt Panel AI có trong MVP | 06, 07 | Không định nghĩa endpoint Panel AI cho tới khi có DEC; `summary` sinh bằng template từ alert (không gọi LLM) |
| OQ-10 | ZIP upload trong UC-07 (04 OQ-09) — EP-20 hiện trả `415` với `.zip` | 04 | Không hỗ trợ ZIP trong MVP |
| OQ-11 | Endpoint `switch-role` dùng `target_role_code`; 07 OQ-14 (cơ chế chuyển vai) chưa resolved | 07 | Theo mặc định 07 §8.1.1 |
| OQ-12 | `ai_state` trong DocumentOut suy từ `autonomy_level` + `status` (không có cột) | 05 | Tính khi đọc |
| OQ-13 | CLAUDE.md § API yêu cầu `require_role` cho mọi endpoint trừ health check, nhưng EP-02 (login) cũng bắt buộc public vì client chưa có JWT. Xác nhận tập public endpoint = {EP-01 health, EP-02 login} là đủ, không mở rộng thêm (VD refresh-token, forgot-password) | CLAUDE.md, 02, 07 | Giữ {health, login}; captain raise DEC xác nhận ngoại lệ so với CLAUDE.md § API |

---

## 10. Liên kết

| Chủ đề | File |
|---|---|
| Quyền, scoping, role switcher | `02-PERSONAS-PERMISSIONS.md` |
| Metric, alert, drill-down | `03-DASHBOARD-SPEC.md` |
| IDP, FR-DC, US-DC, Action Registry, UC-07 | `04-IDP-FEATURE-SPEC.md` |
| Bảng, cột, enum, lineage | `05-DATA-MODEL.md` |
| Màn hình SCR-xx | `06-UI-UX-SPEC.md` |
| JWT, DEMO_MODE, polling, presigned URL | `07-TECH-ARCHITECTURE.md` |
| Test mapping endpoint | `14-TEST-TRACEABILITY.md` |

---

## 11. Version

- **Version:** 1.0.0
- **Last updated:** 2026-10-17
- **Applies to:** Aureon Demo v1.0
- **Maintainer:** @CyEyes
