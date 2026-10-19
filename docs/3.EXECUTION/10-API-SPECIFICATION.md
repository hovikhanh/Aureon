# 10 — API Specification

> **Contract nguồn duy nhất** cho API HTTP, SSE và domain event của **Aureon v2**. Backend FastAPI (`apps/api`, Modular Monolith — DEC-125) và frontend Next.js (`apps/web`) phải bám đúng file này. Không tự thêm endpoint/field/event — mọi thay đổi cập nhật file này trước hoặc raise `DEC-xxx` (`CLAUDE.md` § Cấm tự quyết).
> Nguồn: `00-INDEX.md` §4 (ID registry: ROLE, ENT, EVT, SCR, dải EP §4.6), `01-PROJECT-OVERVIEW.md`, DEC-124 → DEC-137 (`13-DECISION-LOG.md` §3.5), A-EMS (`SOURCE-BRD-v1.0` §III), AI-EOS (`SOURCE-BRD-v1.1` §3, §4.2, §4.4). Bản v1 (35 endpoint, 4 trụ, 5 role) lưu ở nhánh git `v1`.
> Spec liên quan: quyền `02`, metric/alert `03`, IDP/Action Registry `04`, bảng/cột/enum `05`, màn hình `06`, kiến trúc/ModelGateway `07`.

---

## 1. Quy ước chung

### 1.1. Base path, định dạng, đặt tên

| Hạng mục | Quy ước |
|---|---|
| Base path | `/api/v1` — mọi path trong file là tương đối (VD `GET /finance/revenues` = `GET /api/v1/finance/revenues`). Riêng `GET /health` cũng nằm dưới base path |
| Prefix module | Segment đầu là **tên module số ít** theo DEC-125: `auth`, `dashboard`, `idp`, `execution`, `platform`, `finance`, `sales`, `hr`, `product`, `risk`, `ai` |
| Resource | Danh từ **số nhiều**, từ ghép **kebab-case** (`/hr/hiring-plans`, `/product/roadmap-items`); hành động không phải CRUD dùng sub-resource động từ (`/invoices/{id}/pay`, `/risks/{id}/accept`) |
| Định dạng | JSON UTF-8; upload `multipart/form-data`; streaming AI `text/event-stream` (§6); tải file qua presigned URL |
| Tên field JSON | `snake_case`, trùng tên cột ở `05-DATA-MODEL.md` |
| ID | UUID v4 dạng chuỗi; mã nghiệp vụ dùng mã chuẩn registry: `METRIC-FIN-01`, `ALERT-RSK-02`, `ROLE-07`, `PIL-S` (trong API trả gọn `pillar: "S"`) |
| Tiền | **Số nguyên (BIGINT) theo đơn vị nhỏ nhất** của `currency` + field `currency` (ISO 4217, mặc định `VND`). VD `{ "amount": 1250000, "currency": "VND" }`. Không chuỗi, không số thực |
| Tỷ lệ | Field có hậu tố `_pct`, số thực **đã nhân 100** (`28.0` = 28%). Metric có `unit = PCT` trả `value` theo cùng thang 0–100 |
| Thời gian | ISO 8601 **UTC** có hậu tố `Z` (`2026-10-05T01:30:00Z`); ngày thuần `YYYY-MM-DD`; kỳ `YYYY-MM`, `YYYY-Qn`, `YYYY`. Frontend hiển thị theo múi giờ người dùng (mặc định `Asia/Ho_Chi_Minh`) và định dạng P04 |
| Chuỗi hiển thị | API trả **mã + i18n key + tham số**, không trả câu cố định (trừ `error.message` debug và nội dung trả lời AI). Ngôn ngữ AI theo `Accept-Language` / ngôn ngữ câu hỏi (DEC-135) |
| Validation chung | Email RFC 5322; điện thoại 10–15 ký tự (số và `+`); `status` thuộc enum của entity (05) |
| Phiên bản | Thay đổi phá vỡ contract → `/api/v2` + DEC; thêm field optional không phá vỡ |

### 1.2. Quy ước đánh số EP

- Dải số theo `00-INDEX.md` §4.6. **Một EP = một resource** (collection + item). Các thao tác của resource ghi bằng ký hiệu: **L** = `GET` collection, **C** = `POST` collection, **R** = `GET /{id}`, **U** = `PATCH /{id}`, **D** = `DELETE /{id}` (soft delete). Khi trích dẫn thao tác cụ thể dùng `EP-61.C`, `EP-81.U`.
- Hành động phi CRUD có EP riêng (VD `EP-68` thanh toán hóa đơn).
- EP-20..41 giữ **số** của v1; path đổi sang prefix `/idp/...` (OQ-01).

### 1.3. Response envelope (DEC-130)

Thành công:

```json
{ "data": { } , "meta": { "request_id": "…", "generated_at": "…", "pagination": { } } }
```

- `data`: object hoặc mảng. `meta` tùy chọn.
- Danh sách: `meta.pagination = { "total": 47, "limit": 20, "offset": 0, "has_next": true }`.
- `201` cho tạo mới, `202` cho tác vụ bất đồng bộ (trả `data.job_id` hoặc tài nguyên ở trạng thái chờ), `204` cho xóa (không body).

Lỗi:

```json
{ "error": { "code": "FORBIDDEN_SCOPE", "message": "debug message", "details": { } } }
```

- `code` ổn định theo §1.4 (frontend map sang i18n `error.<code>`).
- Lỗi validation: `details.fields = [{ "loc": ["body","amount"], "msg": "…", "type": "…" }]`.
- Mọi response có header `X-Request-Id` (§1.9). Mọi endpoint khai báo `response_model` Pydantic v2; field nhạy cảm không thuộc response model của role không có quyền (§2.4).

### 1.4. Bảng mã lỗi

| HTTP | `error.code` | Ý nghĩa | Ví dụ |
|---|---|---|---|
| 400 | `BAD_REQUEST` | Tham số sai cú pháp | `period` sai định dạng |
| 401 | `UNAUTHENTICATED` | Thiếu/sai/hết hạn access token | Thiếu header `Authorization` |
| 401 | `INVALID_CREDENTIALS` | Sai email/mật khẩu (không tiết lộ email tồn tại) | EP-02 |
| 401 | `REFRESH_TOKEN_INVALID` | Refresh token sai, hết hạn hoặc đã thu hồi/xoay vòng | EP-06 |
| 403 | `FORBIDDEN_ROLE` | Thiếu permission `<domain>:<action>` của endpoint | EMPLOYEE gọi `POST /finance/budgets` |
| 403 | `FORBIDDEN_SCOPE` | Tài nguyên ngoài phạm vi dữ liệu (trụ, đơn vị, chủ sở hữu) | MANAGER xem chi phí phòng khác |
| 403 | `FORBIDDEN_SALARY` | Field/tài liệu chứa lương hoặc PII rất nhạy cảm (02) | CFO mở lịch sử lương |
| 404 | `NOT_FOUND` | Không tồn tại, đã soft delete, hoặc endpoint demo khi `DEMO_MODE=false` | EP-04 khi tắt demo |
| 409 | `CONFLICT_STATE` | Chuyển trạng thái không hợp lệ theo state machine | Approve tài liệu `COMMITTED` |
| 409 | `REVIEW_LOCKED` | Tài liệu đang được người khác review (khóa mềm 15 phút) | `details.locked_by`, `locked_until` |
| 409 | `IDEMPOTENCY_CONFLICT` | Cùng `Idempotency-Key` nhưng body khác | §1.6 |
| 409 | `DUPLICATE_DOCUMENT` | Trùng SHA-256 file (thông tin; tài liệu vẫn tạo ở `DUPLICATE`) | EP-20, `details.duplicate_of_id` |
| 409 | `DUPLICATE_RESOURCE` | Vi phạm ràng buộc duy nhất nghiệp vụ | Trùng `product.code`, `release.version`, `cash_position.period` |
| 410 | `UNDO_EXPIRED` | Quá hạn hoàn tác (7 ngày IDP / 24 giờ AI L3 — DEC-134) | EP-33, EP-116 |
| 413 | `FILE_TOO_LARGE` | Vượt `MAX_FILE_SIZE_MB` / `MAX_PAGES` / `MAX_FILES_PER_UPLOAD` | EP-20 |
| 415 | `UNSUPPORTED_MEDIA_TYPE` | Định dạng không hỗ trợ | `.zip` |
| 422 | `VALIDATION_ERROR` | Body sai schema / định dạng | `details.fields[]` |
| 422 | `BUSINESS_RULE_VIOLATION` | Vi phạm quy tắc nghiệp vụ `BR-*`/FR | `deal_value ≤ 0`; xóa sản phẩm còn tính năng `in_progress` (BR-PRD-01) |
| 422 | `ACTION_REJECTED` | Action Registry / Autonomy Policy từ chối | `details.action_name`, `details.reason` |
| 422 | `MALWARE_DETECTED` | File bị ClamAV đánh dấu (FR-DC-08) | EP-20 |
| 422 | `AI_CONTEXT_TOO_LARGE` | Vượt context model sau khi đã chunk | EP-110 |
| 423 | `AI_DISABLED` | Kill switch chế độ mạnh `L0` (04 §9.2) hoặc AI tắt — thao tác cần AI bị chặn | EP-22 khi kill switch L0 |
| 429 | `RATE_LIMIT_EXCEEDED` | Vượt giới hạn tần suất (header `Retry-After`) | > 20 request AI/phút |
| 429 | `AI_QUOTA_EXCEEDED` | Provider hết hạn mức **hoặc** vượt `AI_MONTHLY_BUDGET_USD` | EP-110 |
| 500 | `INTERNAL_ERROR` | Lỗi không mong đợi (không lộ stack trace) | — |
| 502 | `AI_PROVIDER_ERROR` | Mọi provider trong chuỗi fallback trả lỗi | EP-110 |
| 502 | `AI_FUNCTION_CALL_FAILED` | Tool nội bộ lỗi và không thể trả lời từng phần | EP-110 |
| 503 | `DEPENDENCY_UNAVAILABLE` | DB/Redis/MinIO/ClamAV/ModelGateway không sẵn sàng | Health `degraded` |
| 504 | `AI_PROVIDER_TIMEOUT` | Hết 30 giây/lượt | EP-110 |

- `AI_NO_DATA_AVAILABLE` **không** phải lỗi HTTP: AI vẫn trả 200, kèm `warnings: ["AI_NO_DATA_AVAILABLE"]` trong `done` (§6) — AI nói rõ thiếu dữ liệu, không bịa số (P05).
- Mã lỗi IDP nội bộ `IDP-E01..E11` (04) nằm ở `extraction_jobs.error_code` và `details.idp_error_code`, không thay `error.code`.
- Mã `RATE_LIMITED` của v1 được thay bằng `RATE_LIMIT_EXCEEDED` (DEC-130).

### 1.5. Phân trang, lọc, sắp xếp (DEC-130)

| Tham số | Kiểu | Mặc định | Ghi chú |
|---|---|---|---|
| `limit` | int 1..100 | 20 | > 100 → `400 BAD_REQUEST` |
| `offset` | int ≥ 0 | 0 | |
| `sort_by` | string | `created_at` | Chỉ field nằm trong whitelist của endpoint |
| `order` | `asc` / `desc` | `desc` | |
| Bộ lọc | query string | — | Tên trùng cột 05 (`status`, `department_id`, `period`, `pillar`); khoảng thời gian `from`, `to` (ngày, bao gồm hai đầu); tìm kiếm `q` |
| Kỳ | `period` | `current_month` | `current_month` / `current_quarter` / `ytd` / `custom` (`start_date`, `end_date` bắt buộc khi `custom`) hoặc mã kỳ cụ thể `YYYY-MM`, `YYYY-Qn` |

### 1.6. Idempotency

| Hạng mục | Quy ước |
|---|---|
| Header | `Idempotency-Key: <uuid>` **bắt buộc** cho mọi `POST` tạo tài nguyên/commit/hành động (C, hành động phi CRUD) và mọi endpoint AI ghi; khuyến nghị cho `PATCH`. Thiếu khi bắt buộc → `400 BAD_REQUEST` |
| Lưu | Redis, TTL 24 giờ, khóa `(user_id, method, path, Idempotency-Key)` → response đã trả |
| Gọi lại cùng key + cùng body | Trả lại đúng response cũ (cùng status) |
| Cùng key, body khác | `409 IDEMPOTENCY_CONFLICT` |
| Ghi nghiệp vụ | Action Registry dùng thêm `idempotency_key` nghiệp vụ (04, 05) để chống trùng cả khi retry Celery |
| Event | Consumer khử trùng theo `event_id` (`ENT-ProcessedEvent`, §8) |

### 1.7. Rate limit & cache

| Hạng mục | Quy ước |
|---|---|
| Rate limit chung | 120 request/phút/người dùng (`API_RATE_LIMIT_PER_MIN`) — middleware Redis token bucket |
| Rate limit AI | **20 request/phút/người dùng** cho EP-110, EP-111 (`AI_RATE_LIMIT_PER_MIN`, NFR-14) |
| Rate limit login | 10 lần sai/15 phút/(email, IP) → `429 RATE_LIMIT_EXCEEDED` |
| Header trả về | `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `Retry-After` (khi 429) |
| Cache dashboard | EP-10, EP-11, EP-12, EP-18, EP-49, EP-60, EP-70, EP-80, EP-90, EP-100: `Cache-Control: private, max-age=60` + **bắt buộc** `Vary: Authorization` (hai tài khoản cùng trình duyệt không đọc chung cache) |
| Cache khác | Mặc định `Cache-Control: no-store` |
| ETag | Tùy chọn cho EP-12, EP-14; `If-None-Match` → `304` |

### 1.8. Audit log cho mutation

- Mọi mutation (POST/PUT/PATCH/DELETE) ghi `ENT-AuditLog` **trong cùng transaction** với thay đổi: `actor_type` (`user` / `ai` / `system`), `actor_user_id`, `actor_role`, `action`, `target_type`, `target_id`, `before`/`after` (lương mask `••••`), `metadata.request_id`, `metadata.idempotency_key`, `metadata.ai_action_id` (nếu do AI), `ip_address`.
- Ghi thêm: đăng nhập/đăng xuất (`auth.login`, `auth.logout`), chuyển vai trò (`role.switch`), mở tài liệu có PII (`document.open_pii`), bị từ chối dữ liệu lương (`document.open_denied`), bật/tắt kill switch (`ai.kill_switch`).
- Tên `action` = `<module>.<verb>` (VD `finance.invoice_pay`, `ai.action_undo`).

### 1.9. Correlation ID & quan sát

- Client có thể gửi `X-Request-Id` (UUID); nếu thiếu, middleware sinh mới. Giá trị được trả về ở header, ghi vào log JSON, `ENT-AuditLog.metadata`, envelope event (`correlation_id`), `ENT-ToolCallLog` và `ENT-ModelCallLog`.
- AI gọi tool nội bộ giữ nguyên `X-Request-Id` của lượt chat.

---

## 2. Xác thực & phân quyền

### 2.1. Token (DEC-129, DEC-137)

| Hạng mục | Quy ước |
|---|---|
| Access token | JWT ký **RS256**, header `Authorization: Bearer <token>`; TTL `JWT_ACCESS_TTL_SECONDS` (mặc định 900 = 15 phút) |
| Refresh token | Chuỗi ngẫu nhiên opaque (không phải JWT), lưu hash ở `ENT-RefreshToken`; TTL `JWT_REFRESH_TTL_SECONDS` (mặc định 7 ngày); **xoay vòng** mỗi lần dùng; dùng lại token đã xoay → thu hồi cả chuỗi |
| Ký / verify | Khóa private chỉ module `auth` đọc (`JWT_PRIVATE_KEY_PATH`); middleware các module verify bằng khóa public (`JWT_PUBLIC_KEY_PATH`); có `kid` để xoay khóa |
| Claim | `sub` (user id), `email`, `role` (mã code `CEO`…`ADMIN`), `role_id` (`ROLE-01`…`ROLE-10`), `permissions[]`, `department_id` (nullable), `iat`, `exp`, `iss` (`JWT_ISSUER`), `aud` (`JWT_AUDIENCE`), `jti` |
| Endpoint public | **Chỉ** EP-01 `GET /health`, EP-02 `POST /auth/login`, EP-06 `POST /auth/refresh` (xác thực bằng refresh token). **Không có** `POST /auth/register` (DEC-137) |
| Lưu phía client | NextAuth giữ token trong session cookie `httpOnly`, `Secure`, `SameSite=Lax`; không lưu `localStorage` |
| Không tin client | Không endpoint nào nhận role/permission từ body/query để phân quyền |

### 2.2. Permission `<domain>:<action>`

Mỗi endpoint khai báo đúng **một** permission bắt buộc qua `Depends(require_permission("<domain>:<action>"))` (bao bọc `require_role` của `CLAUDE.md` — OQ-03). Danh mục permission và ma trận role × permission là nguồn chuẩn ở **`02-PERSONAS-PERMISSIONS.md` §5.2–5.3**; file này chỉ gắn permission vào endpoint. Tóm tắt:

| Action | Ý nghĩa (02 §5.1) |
|---|---|
| `read` | Bản ghi chi tiết (danh sách, chi tiết, lịch sử) |
| `write` | Tạo / sửa / xóa mềm |
| `query` | Dữ liệu tổng hợp: dashboard domain, KPI, trend, what-if — không trả bản ghi cá nhân |
| `approve` | Duyệt trong workflow (`hr:approve` kế hoạch tuyển dụng, `risk:approve` chấp nhận rủi ro, `idp:approve` duyệt/commit/hoàn tác extraction) |
| `admin` | Cấu hình domain (`idp:admin`, `ai:admin`, `dashboard:admin`, `platform:admin`) |

Domain ∈ `finance, sales, hr, product, risk, execution, idp, ai, dashboard, platform` (`ai` = module `ai_core`). Auth của chính mình (EP-03, EP-07, EP-08, EP-53) chỉ cần token hợp lệ (ký hiệu **`authenticated`**); quản trị user = `platform:admin`.

Quy tắc:

1. **RBAC hai lớp:** (a) middleware verify JWT RS256 + rate limit; (b) dependency permission ở từng endpoint + data scoping ở service (§2.3). Thiếu permission → `403 FORBIDDEN_ROLE`.
2. Một số endpoint chấp nhận **một trong hai** permission (VD dashboard domain: `<domain>:query`); khi đó cột Permission ghi `A \| B` và response cắt theo permission thực có (`query` không kèm `read` → chỉ số tổng hợp, không bản ghi/link tài liệu — 02 §6.1 #5).
3. Khi AI gọi tool, permission kiểm bằng **JWT của người hỏi** (P06) — không có token hệ thống để AI đọc dữ liệu nghiệp vụ. Hành động ghi của AI cần **cả** `ai:write` **và** `<domain>:write` (02 §7.1 #5).
4. Worker nội bộ (Celery) chạy với principal `system` hoặc `ai:<agent>` (VD `ai:idp`), chỉ ghi qua Action Registry; không gọi HTTP nội bộ.

### 2.3. Data scoping

| # | Quy tắc |
|---|---|
| DS1 | Mọi truy vấn lọc theo phạm vi của role ở backend trước khi trả; **default deny** |
| DS2 | Trụ ngoài phạm vi role không có trong response dashboard (không trả `null`) |
| DS3 | Scope theo role đúng 02 §6.2: `d` (phòng ban — MANAGER), `o` (của mình/được giao — EMPLOYEE), `p` (trụ của mình), `r` (được phân review — REVIEWER); ADMIN không đọc bản ghi nghiệp vụ |
| DS4 | Lineage/drill-down ra ngoài scope: trả mục `{ "restricted": true, "reason": "OUT_OF_SCOPE" \| "SALARY" }` thay vì ẩn im lặng |
| DS5 | Hội thoại AI chỉ chủ sở hữu đọc/xóa (NFR-12) |

### 2.4. Dữ liệu nhạy cảm

| Mức (05) | Dữ liệu | API |
|---|---|---|
| Rất nhạy cảm | Lương, lịch sử lương, ngày sinh, địa chỉ, liên hệ khẩn cấp, CCCD, số tài khoản cá nhân | Chỉ ROLE-01, ROLE-04 (ROLE-05 trong phiên review được phân); role khác nhận `{ "masked": true }`; **không bao giờ** có trong kết quả tool gửi LLM |
| Nhạy cảm | Họ tên, email, điện thoại nhân viên và người liên hệ khách hàng | Theo RBAC; lọc PII (thay bằng mã tham chiếu `EMP-xxxx`) trước khi gửi LLM |
| Bí mật kinh doanh | Số liệu tài chính, deal, dự báo, rủi ro | Theo RBAC; HTTPS |
| Bảo mật hệ thống | `password_hash`, khóa JWT, API key provider | Không bao giờ có trong response hoặc log |

---

## 3. Danh mục endpoint (tổng)

Ký hiệu thao tác theo §1.2. Cột **Permission**: một permission bắt buộc (§2.2); `authenticated` = chỉ cần token; `public` = không cần token; `A | B` = một trong hai. Thao tác ghi của một resource dùng `<domain>:write` trừ khi ghi chú khác. Số EP còn trống (Sales EP-79, HR EP-88..89, Product EP-96..99, Risk EP-107..109) dành cho mở rộng sau DEC.

### 3.1. System, Auth, User admin — EP-01..09 (module `auth`, `platform`)

| EP | Method | Path | Mô tả | Permission |
|---|---|---|---|---|
| EP-01 | GET | `/health` | Health tổng + từng dependency | public |
| EP-02 | POST | `/auth/login` | Đăng nhập email + mật khẩu | public |
| EP-03 | GET, PATCH | `/auth/me` | Phiên hiện tại / cập nhật hồ sơ | authenticated |
| EP-04 | POST | `/auth/switch-role` | Chuyển vai trò demo (chỉ `DEMO_MODE=true`) | authenticated |
| EP-05 | GET | `/auth/demo-users` | Danh sách user demo (chỉ `DEMO_MODE=true`) | authenticated |
| EP-06 | POST | `/auth/refresh` | Làm mới access token (xoay vòng refresh token) | public (refresh token) |
| EP-07 | POST | `/auth/logout` | Thu hồi refresh token | authenticated |
| EP-08 | POST | `/auth/me/password` | Đổi mật khẩu | authenticated |
| EP-09 | L C R U D | `/platform/users` | Quản trị user, gán/đổi role (FR-AUTH-05) | `platform:admin` |

### 3.2. Dashboard, metric, alert, lineage, briefing — EP-10..19 (module `dashboard`)

Không có endpoint tổng hợp 5 trụ (03 §9 — cô lập lỗi): thẻ trụ lấy từ 5 dashboard domain (EP-60, EP-70, EP-80 + EP-49 cho PIL-O, EP-90, EP-100; §5). Số EP-10..17 giữ nghĩa v1.

| EP | Method | Path | Mô tả | Permission |
|---|---|---|---|---|
| EP-10 | GET | `/dashboard/briefing` | Briefing / trang chủ theo role (F1, 03 §7.2, §10) — tính sẵn 06:00, không gọi LLM đồng bộ; khối hiển thị cắt theo permission thực có (MANAGER/EMPLOYEE không có `dashboard:read` vẫn nhận khối việc/đơn vị) | authenticated |
| EP-11 | GET | `/dashboard/metrics` | Danh sách metric + giá trị hiện tại (lọc `pillar`, `status`) | `dashboard:read` |
| EP-12 | GET | `/dashboard/metrics/{metric_code}` | Metric detail — Panel P01, SCR-07 (drill click 1) | `dashboard:read` |
| EP-13 | GET | `/dashboard/metrics/{metric_code}/records` | Bản ghi thành phần của metric (drill click 2) | `dashboard:read` + `<domain>:read` của metric |
| EP-14 | GET | `/dashboard/lineage` | Lineage bản ghi → field → trang tài liệu (drill click 3) | `dashboard:read` |
| EP-15 | GET | `/dashboard/alerts` | Danh sách alert | `dashboard:read` |
| EP-16 | POST | `/dashboard/alerts/{id}/acknowledge` | Xác nhận đã tiếp nhận alert | `dashboard:write` |
| EP-17 | POST | `/dashboard/alerts/{id}/dismiss` | Bỏ qua alert (bắt buộc lý do) | `dashboard:write` |
| EP-18 | GET | `/dashboard/pillar-history` | Dải trạng thái trụ 30 ngày (03 §4) | `dashboard:read` |
| EP-19 | PUT | `/dashboard/briefing/pinned-metrics` | Chọn 4 chỉ số ghim của Briefing | `dashboard:write` |

### 3.3. IDP — EP-20..41 (module `idp`; giữ số v1, prefix mới `/idp`)

| EP | Method | Path | Mô tả | Permission |
|---|---|---|---|---|
| EP-20 | POST | `/idp/documents` | Upload file C3/C4 (1..100 file, stream) | `idp:write` |
| EP-21 | POST | `/idp/documents/manual` | Nhập tay qua form C1 (kể cả lưu nháp) | `idp:write` |
| EP-22 | POST | `/idp/documents/natural-language` | Nhập ngôn ngữ tự nhiên C2 (text/voice) | `idp:write` |
| EP-23 | POST | `/idp/documents/import` | Import Excel/CSV C5 — bước 1: upload + gợi ý mapping | `idp:write` |
| EP-24 | GET | `/idp/documents` | Danh sách / tìm kiếm tài liệu (Data Inbox) | `idp:read` |
| EP-25 | GET | `/idp/documents/{id}` | Chi tiết tài liệu + job + timeline | `idp:read` |
| EP-26 | GET | `/idp/documents/{id}/extraction` | Kết quả trích xuất (field result) | `idp:read` |
| EP-27 | GET | `/idp/documents/{id}/source` | Tài liệu gốc (presigned URL + trang) | `idp:read` |
| EP-28 | GET | `/idp/review-queue` | Hàng chờ review theo ưu tiên + SLA | `idp:approve` |
| EP-29 | POST | `/idp/documents/{id}/review/open` | Mở review (khóa mềm 15 phút) | `idp:approve` |
| EP-30 | PATCH | `/idp/documents/{id}/fields` | Sửa/xác nhận field, đổi doc type | `idp:approve` |
| EP-31 | POST | `/idp/documents/{id}/review/approve` | Duyệt + commit qua Action Registry | `idp:approve` |
| EP-32 | POST | `/idp/documents/{id}/review/reject` | Từ chối (bắt buộc lý do) | `idp:approve` |
| EP-33 | POST | `/idp/documents/{id}/rollback` | Hoàn tác commit (≤ 7 ngày) | `idp:approve` |
| EP-34 | POST | `/idp/documents/{id}/retry` | `RETRY` / `REOPEN` / `FORCE_DUPLICATE` | `idp:write \| idp:approve` |
| EP-35 | POST | `/idp/documents/{id}/review/release` | Đóng review không lưu | `idp:approve` |
| EP-36 | POST | `/idp/documents/{id}/import-mapping` | Import C5 — bước 2: xác nhận mapping | `idp:write` |
| EP-37 | POST | `/idp/documents/{id}/split` | Tách / chỉnh ranh giới tài liệu ghép (FR-DC-09) | `idp:write \| idp:approve` |
| EP-38 | GET | `/idp/documents/{id}/row-errors` | Xuất file dòng lỗi C5 (FR-DC-18) | `idp:read` |
| EP-39 | GET | `/idp/stats` | Accuracy / STP / thời gian review theo doc type × field (FR-DC-23) | `idp:admin` |
| EP-40 | L C | `/idp/batches` | Tạo / liệt kê batch (UC-07, upload nhiều file) | `idp:write` |
| EP-41 | GET | `/idp/batches/{id}` | Tiến độ + tổng hợp + đối chiếu chéo batch | `idp:read` |

### 3.4. Execution — EP-42..49 (module `execution`)

| EP | Method | Path | Mô tả | Permission |
|---|---|---|---|---|
| EP-42 | L C R U D | `/execution/meetings` | Cuộc họp (UC-06) | `execution:read` / `write` |
| EP-43 | L C R U | `/execution/decisions` | Decision log (lý do, phương án loại, kết quả kỳ vọng) | `execution:read` / `write` |
| EP-44 | L C R U D | `/execution/tasks` | Task (giao việc, hạn, trạng thái) | `execution:read` / `write` |
| EP-45 | L C R U D | `/execution/projects` | Dự án | `execution:read` / `write` |
| EP-46 | L C R U D | `/execution/objectives` (+ `/{id}/key-results`) | OKR: Objective + Key Result | `execution:read` / `write` |
| EP-47 | L C R U D | `/execution/kpis` (+ `/{id}/measurements`) | KPI + đo lường kỳ | `execution:read` / `write` |
| EP-48 | L C | `/execution/check-ins` | Check-in KR/KPI (F4) | `execution:read` / `write` |
| EP-49 | GET | `/execution/dashboard` | Tổng hợp thực thi + workload heatmap | `execution:query` |

### 3.5. Config, audit, notification — EP-50..59 (module `idp`, `dashboard`, `platform`)

| EP | Method | Path | Mô tả | Permission |
|---|---|---|---|---|
| EP-50 | L C R U | `/idp/document-types` (+ `/{id}/schemas`) | Doc type, Extraction Schema (version), ngưỡng confidence/STP | `idp:read` (ghi: `idp:admin`) |
| EP-51 | L C U D | `/idp/validation-rules` | Validation rule theo doc type | `idp:admin` |
| EP-52 | GET | `/platform/audit-logs` | Audit log (SCR-14) | `platform:read` |
| EP-53 | L U | `/platform/notifications` | Thông báo in-app của tôi; đánh dấu đã đọc | authenticated |
| EP-54 | GET, PATCH | `/platform/settings` | System setting (retention, SLA review, ngưỡng chung) | `platform:admin` |
| EP-55 | L U | `/dashboard/metric-configs` | Ngưỡng warning/critical metric/alert (NFR-19) | `dashboard:admin` |
| EP-56 | L + POST replay | `/platform/dead-letters` | Event trong DLQ; phát lại | `platform:admin` |
| EP-57 | GET | `/platform/system-status` | Tình trạng hệ thống (trang chủ ADMIN) | `platform:admin` |
| EP-58 | GET | `/platform/permission-preview` | "Xem như người dùng" — preview quyền chỉ đọc (US-ADM-04) | `platform:admin` |
| EP-59 | GET | `/platform/roles` | Danh mục 10 role + permission | `platform:admin` |

### 3.6. Finance — EP-60..69 (module `finance`, PIL-F)

| EP | Method | Path | Mô tả | Permission |
|---|---|---|---|---|
| EP-60 | GET | `/finance/dashboard` | Finance dashboard (`summary` + `*_trend`) | `finance:query` |
| EP-61 | L C R U D | `/finance/revenues` | Doanh thu (FR-FIN-01) | `finance:read` / `write` |
| EP-62 | L C R U D | `/finance/expenses` | Chi phí, định kỳ (FR-FIN-02) | `finance:read` / `write` |
| EP-63 | L C R U D | `/finance/budgets` | Ngân sách phòng ban × quý × hạng mục (FR-FIN-03) | `finance:read` / `write` |
| EP-64 | GET | `/finance/budgets/status` | Mức sử dụng ngân sách theo phòng ban (`budget_utilization_pct`) | `finance:query` |
| EP-65 | L C R U | `/finance/cash-positions` | Số dư tiền mặt theo kỳ (FR-FIN-04) | `finance:read` / `write` |
| EP-66 | L C R U | `/finance/forecasts` (+ lines) | Dự báo 3 kịch bản × horizon (FR-FIN-05) | `finance:read` / `write` |
| EP-67 | L C R U D | `/finance/invoices` (+ lines) | Hóa đơn (FR-FIN-06) | `finance:read` / `write` |
| EP-68 | POST | `/finance/invoices/{id}/pay` | Ghi nhận thanh toán → `EVT-finance.invoice_paid` | `finance:write` |
| EP-69 | GET | `/finance/what-if/runway` | Runway kịch bản "không có doanh thu mới" (BR-FIN-06) | `finance:query` |

### 3.7. Sales — EP-70..79 (module `sales`, PIL-C)

| EP | Method | Path | Mô tả | Permission |
|---|---|---|---|---|
| EP-70 | GET | `/sales/dashboard` | Sales dashboard | `sales:query` |
| EP-71 | L C R U D | `/sales/clients` | Khách hàng (FR-SAL-03) | `sales:read` / `write` |
| EP-72 | L C R U D | `/sales/deals` | Deal (FR-SAL-01) | `sales:read` / `write` |
| EP-73 | POST | `/sales/deals/{id}/stage` | Chuyển giai đoạn → `EVT-sales.deal_closed_*` (FR-SAL-02) | `sales:write` |
| EP-74 | GET | `/sales/deals/{id}/stage-history` | Lịch sử giai đoạn | `sales:read` |
| EP-75 | GET | `/sales/pipeline` | Pipeline theo giai đoạn (FR-SAL-04) | `sales:query` |
| EP-76 | GET | `/sales/performance` | Hiệu suất theo đội / cá nhân (FR-SAL-05) | `sales:query` |
| EP-77 | L C R U D | `/sales/targets` | Mục tiêu doanh thu (FR-SAL-06) | `sales:read` / `write` |
| EP-78 | L C R U D | `/sales/contracts` | Hợp đồng khách hàng | `sales:read` / `write` |

### 3.8. HR — EP-80..89 (module `hr`, PIL-O)

| EP | Method | Path | Mô tả | Permission |
|---|---|---|---|---|
| EP-80 | GET | `/hr/dashboard` | HR dashboard (FR-HR-06) | `hr:query` |
| EP-81 | L C R U | `/hr/departments` | Phòng ban (FR-HR-05) | `hr:read` / `write` |
| EP-82 | L C R U D | `/hr/employees` | Nhân viên (FR-HR-01) | `hr:read` / `write` |
| EP-83 | L C | `/hr/employees/{id}/salary-history` | Lịch sử lương (FR-HR-02; mức rất nhạy cảm) | `hr:read` + quy tắc lương / `hr:write` |
| EP-84 | L C R U D | `/hr/hiring-plans` | Kế hoạch tuyển dụng (FR-HR-03) | `hr:read` / `write` |
| EP-85 | POST | `/hr/hiring-plans/{id}/submit` | Gửi duyệt kế hoạch tuyển dụng | `hr:write` |
| EP-86 | POST | `/hr/hiring-plans/{id}/approve` | CFO duyệt/từ chối (bắt buộc lý do; FR-HR-07) | `hr:approve` |
| EP-87 | GET | `/hr/workload` | Workload / quá tải theo người, phòng ban (METRIC-HR-03) | `hr:query` |

### 3.9. Product — EP-90..99 (module `product`, PIL-U)

| EP | Method | Path | Mô tả | Permission |
|---|---|---|---|---|
| EP-90 | GET | `/product/dashboard` | Product dashboard (FR-PRD-07) | `product:query` |
| EP-91 | L C R U D | `/product/products` | Danh mục sản phẩm (FR-PRD-01) | `product:read` / `write` |
| EP-92 | L C R U D | `/product/features` | Tính năng (FR-PRD-02) | `product:read` / `write` |
| EP-93 | L C R U D | `/product/roadmap-items` | Roadmap theo quý (FR-PRD-03) | `product:read` / `write` |
| EP-94 | L C R U | `/product/releases` | Release (FR-PRD-04) | `product:read` / `write` |
| EP-95 | L C | `/product/products/{id}/metrics` | Chỉ số sản phẩm append-only (FR-PRD-05) | `product:query` / `write` |

### 3.10. Risk — EP-100..109 (module `risk`, PIL-S)

| EP | Method | Path | Mô tả | Permission |
|---|---|---|---|---|
| EP-100 | GET | `/risk/dashboard` | Risk dashboard + heatmap (FR-RSK-07) | `risk:query` |
| EP-101 | L C R U | `/risk/risks` | Sổ rủi ro (FR-RSK-01) | `risk:read` / `write` |
| EP-102 | L C | `/risk/risks/{id}/assessments` | Đánh giá lại likelihood × impact (FR-RSK-03) | `risk:read` / `write` |
| EP-103 | L C R U | `/risk/mitigations` | Biện pháp giảm thiểu (FR-RSK-04) | `risk:read` / `write` |
| EP-104 | POST | `/risk/risks/{id}/accept` | CEO chấp nhận rủi ro (bắt buộc lý do) | `risk:approve` |
| EP-105 | POST | `/risk/scenarios` | What-if 1–10 rủi ro × 1–24 tháng (FR-RSK-06) | `risk:query` |
| EP-106 | POST | `/risk/risks/{id}/status` | Chuyển trạng thái theo BR-RSK-01 | `risk:write` |

### 3.11. AI Core — EP-110..119 (module `ai_core`, prefix `/ai`)

| EP | Method | Path | Mô tả | Permission |
|---|---|---|---|---|
| EP-110 | POST | `/ai/chat` | Hỏi AI (non-streaming) | `ai:query` |
| EP-111 | POST | `/ai/chat/stream` | Hỏi AI streaming SSE (§6) | `ai:query` |
| EP-112 | L R D | `/ai/conversations` (+ `/{id}/messages`) | Hội thoại của tôi (FR-AI-05) | `ai:query` |
| EP-113 | POST | `/ai/feedback` | Feedback câu trả lời / insight (FR-AI-06) | `ai:query` |
| EP-114 | L + POST dismiss | `/ai/insights` | Insight chủ động theo trụ (FR-AI-07) | `ai:query` |
| EP-115 | L R + POST confirm/reject | `/ai/actions` | Action card L2 và feed "AI đã làm" (SCR-17) | `ai:query` (confirm: `ai:write`) |
| EP-116 | POST | `/ai/actions/{id}/undo` | Hoàn tác hành động AI L3 (≤ 24 giờ) | `ai:write` |
| EP-117 | L C U D | `/ai/policies` | Autonomy policy tool × role × ngưỡng | `ai:admin` |
| EP-118 | GET, PUT | `/ai/kill-switch` | Trạng thái / bật tắt kill switch | `ai:query` (PUT: `ai:admin`) |
| EP-119 | GET | `/ai/tools` (+ `/ai/usage`) | Tool khả dụng cho tôi / chi phí & provider (SCR-15) | `ai:query` (`/ai/usage`: `ai:admin`) |

---

## 4. Chi tiết endpoint

Quy ước chung cho mọi endpoint: lỗi `401 UNAUTHENTICATED`, `403 FORBIDDEN_ROLE`, `429 RATE_LIMIT_EXCEEDED`, `500 INTERNAL_ERROR` **luôn** có thể xảy ra và không lặp lại trong cột Lỗi. CRUD chuẩn: L → `200` + phân trang; C → `201` (header `Idempotency-Key`); R → `200` / `404`; U → `200` / `409 CONFLICT_STATE` / `422`; D → `204` (soft delete) / `409`/`422 BUSINESS_RULE_VIOLATION` khi bị chặn.

### 4.1. System & Auth

| EP | Request | Response `data` | Lỗi | Audit / ghi chú |
|---|---|---|---|---|
| EP-01 | — | `{ status: ok\|degraded\|down, version, checks: { db, redis, minio, clamav, model_gateway: { mode, primary, reachable } } }` | `503` khi `down` | Health AI kèm trạng thái provider (A-EMS §III.6) |
| EP-02 | `{ email, password }` | `{ access_token, token_type: "Bearer", expires_in, refresh_token, user: UserOut }` | `401 INVALID_CREDENTIALS`, `422`, `429` (10 lần sai/15 phút) | `auth.login` (cả thất bại); FR-AUTH-01 |
| EP-03 | PATCH `{ full_name?, locale?: vi\|en, timezone? }` | `UserOut` | `422` | `auth.profile_update`; FR-AUTH-03 |
| EP-04 | `{ target_role_code }` | như EP-02 (token của user demo có role đích) | `404 NOT_FOUND` khi `DEMO_MODE=false`; `422` role không có user demo | `role.switch`; DEC-073 (giữ cơ chế), DEC-129 |
| EP-05 | — | `[{ user_id, full_name, role_code, role_id }]` (10 phần tử, theo ROLE-01..10) | `404` khi tắt demo | — |
| EP-06 | `{ refresh_token }` | như EP-02 (refresh token mới) | `401 REFRESH_TOKEN_INVALID` | Dùng lại token đã xoay → thu hồi chuỗi + `auth.refresh_reuse`; FR-AUTH-02 |
| EP-07 | `{ refresh_token }` | `204` | — | `auth.logout` |
| EP-08 | `{ current_password, new_password }` | `204` | `401 INVALID_CREDENTIALS`, `422 VALIDATION_ERROR` (≥ 8 ký tự, đủ hoa/thường/số/đặc biệt) | `auth.password_change`; thu hồi mọi refresh token khác |
| EP-09 | C `{ email, full_name, role_code, department_id?, initial_password? }`; U `{ role_code?, department_id?, is_active? }` | `UserOut` | `409 DUPLICATE_RESOURCE` (email), `422 BUSINESS_RULE_VIOLATION` (tự đổi role của chính mình) | `user.create`, `user.role_change`; FR-AUTH-05, US-ADM-01, DEC-137. CEO chỉ được gán role ≠ ADMIN (OQ-04) |

**UserOut:** `id`, `email`, `full_name`, `role_code`, `role_id`, `permissions[]`, `department_id`, `locale`, `is_active`, `last_login_at`. Không bao giờ có `password_hash`.

**Không có** endpoint đăng ký (`POST /auth/register` → `404`), DEC-137.

### 4.2. Dashboard, metric, alert, lineage

| EP | Query / Request | Response `data` | Lỗi |
|---|---|---|---|
| EP-10 | `period?` | `{ generated_at, summary_line: { key, params }, pillars: [PillarCard], needs_decision: [ActionRef ≤5], notable_changes: [InsightOut ≤5], risks: [RiskRef ≤3], ai_done: [AIActionOut ≤3], pinned_metrics: [MetricValueOut ×4], stale_metrics: [metric_code] }` — khối không áp dụng cho role bị bỏ (03 §10) | — (ROLE-05 nhận khối hàng chờ review; ROLE-10 nhận khối tình trạng hệ thống — 03 §10) |
| EP-11 | `pillar?`, `status?`, `period?` | `[MetricValueOut]` | `400` |
| EP-12 | `period?`, `breakdown_by?` (`department_id` / `product_id` / `client_id`) | `MetricDetail` = `MetricValueOut` + `{ formula_display, unit, direction, thresholds: { warning, critical }, trend: [{ period_key, value }], breakdown: [{ key, label, value, record_count }], related_alerts: [AlertOut], source: { module, entities[] } }` | `404`, `403 FORBIDDEN_SCOPE` (trụ ngoài phạm vi) |
| EP-13 | `period?`, `breakdown_key?`, phân trang | `[RecordRef]` = `{ entity: "ENT-Invoice", schema, table, id, label, amount?, currency?, entered_by, channel: C1..C5, source_document_id?, restricted? }` | `403 FORBIDDEN_SCOPE` |
| EP-14 | `entity` (VD `ENT-Invoice`), `id` | `{ nodes: [{ kind: metric_value\|record\|extracted_field\|document_page, id, label, restricted?, reason? }], edges: [{ from, to }], document?: { source_document_id, page_no, bbox } }` | `404`; nút ngoài quyền trả `restricted:true` (DS4) |
| EP-15 | `status?` (`open\|acknowledged\|resolved\|dismissed`), `severity?`, `pillar?`, phân trang | `[AlertOut]` | — |
| EP-16 | `{ note? }` | `AlertOut` | `409 CONFLICT_STATE` |
| EP-17 | `{ reason }` (bắt buộc) | `AlertOut` | `409`, `422` |
| EP-18 | `pillar?`, `days?` (≤ 90, mặc định 30) | `[{ date, pillar, status }]` | — |
| EP-19 | `{ metric_codes: [4 mã METRIC-*] }` | `{ metric_codes }` | `422` (≠ 4 mã hoặc metric ngoài phạm vi) |

**MetricValueOut:** `metric_code` (VD `METRIC-FIN-03`), `pillar` (`F\|O\|C\|U\|S`), `value` (number\|null), `unit` (`VND\|PCT\|MONTHS\|DAYS\|COUNT\|RATIO\|SCORE`), `currency?`, `status` (`ok\|warning\|critical\|no_data`), `status_reason?` (VD `NOT_APPLICABLE_PROFITABLE` — BR-FIN-03, `SMALL_SAMPLE` — CUS-02), `period_key`, `computed_at`, `freshness` (`fresh\|stale`), `data_quality_pct`, `lineage_url`.

**AlertOut:** `id`, `alert_code` (VD `ALERT-FIN-03`, cùng số metric), `metric_code`, `pillar`, `severity` (`warning\|critical`), `status`, `scope` (`{ department_id? \| product_id? \| risk_id? }`), `value`, `threshold`, `period_key`, `raised_at`, `acknowledged_by?`, `message_key`, `message_params`.

### 4.3. IDP

| EP | Request | Response `data` | Lỗi | Ghi chú |
|---|---|---|---|---|
| EP-20 | `multipart`: `files[]` (1..100), `doc_type_hint?`, `batch_id?`, `pillar_hint?` | `202` `[DocumentOut]` (status `UPLOADED`), trong ≤ 2 giây | `413 FILE_TOO_LARGE` (> 50 MB), `415`, `422` (> 100 file), `409 DUPLICATE_DOCUMENT` (thông tin: document vẫn tạo `DUPLICATE`) | Stream lên MinIO, SHA-256; ClamAV chạy ở worker (`MALWARE_DETECTED` → `FAILED`); FR-DC-01, 02, 05, 07 |
| EP-21 | `{ doc_type, fields: {…}, draft: bool }` | `201` `DocumentOut` (draft → không vào pipeline) | `422 VALIDATION_ERROR`, `422 BUSINESS_RULE_VIOLATION` | C1; vẫn đi validation + Action Registry; FR-DC-04 |
| EP-22 | `{ text? (≤ 2000), audio? (multipart ≤ 60 s), context?: { screen, entity_ref } }` | `202` `{ document: DocumentOut, ai_action_id }` — luôn L2 | `422`, `423 AI_DISABLED` | C2; FR-DC-03 |
| EP-23 | `multipart file` (xlsx/csv, ≤ 5000 dòng/sheet), `doc_type?` | `202` `{ document, sheets: [{ name, rows, columns[] }], mapping_suggestion: [{ column, field, confidence }], preview_rows: [20] }` | `413`, `415`, `422` | C5 bước 1; FR-DC-18 |
| EP-24 | `status?`, `doc_type?`, `channel?`, `pillar?`, `batch_id?`, `q?`, `from?`, `to?`, phân trang | `[DocumentOut]` | — | Scope `p/d/o/r` |
| EP-25 | — | `DocumentOut` + `{ jobs: [JobOut], status_timeline: [{ status, at, actor }], affected_records: [RecordRef], reviews: [ReviewOut], children?: [DocumentOut] }` | `404`, `403 FORBIDDEN_SCOPE` | |
| EP-26 | `job_id?` | `{ schema_version, doc_type, classification_confidence, fields: [FieldResult], tables: [{ name, rows: [[FieldResult]] }], validations: [{ rule, result: pass\|warn\|fail, field_paths, message_key }], conflicts: [{ xd_code, ref }], master_matches: [...] }` | `403 FORBIDDEN_SALARY` (giá trị mask khi `contains_salary` — chỉ metadata) | FR-DC-10..14 |
| EP-27 | `page?` | `{ url (presigned ≤ 15 phút), mime, page_count, pages: [{ page_no, width, height, ocr_used, ocr_confidence }] }` | `403 FORBIDDEN_SALARY`, `404`; `422` khi file `INFECTED` | Audit `document.open_pii` / `document.open_denied` |
| EP-28 | `doc_type?`, `pillar?`, `batch_id?`, `channel?`, phân trang (sort mặc định theo ưu tiên FR-DC-17) | `[DocumentOut + { priority_reason, sla_due_at, critical_field_count, low_conf_count }]` | — | FR-DC-17, SCR-08 |
| EP-29 | — | `{ locked_until, document: DocumentOut }` | `409 REVIEW_LOCKED`, `409 CONFLICT_STATE` | Khóa mềm 15 phút; gia hạn khi PATCH |
| EP-30 | `{ doc_type?, fields: [{ path, value, action: confirm\|correct\|clear }] }` | `{ fields: [FieldResult], validations }` | `409 REVIEW_LOCKED`, `422` | Lưu cả `ai_value` và `corrected_value` |
| EP-31 | `{ field_paths?: [...] (null = toàn bộ), comment? }` | `{ document: DocumentOut (COMMITTED), actions: [{ action_name, ids[] }], undo_deadline }` | `409`, `422 ACTION_REJECTED`, `422 BUSINESS_RULE_VIOLATION` (về `NEEDS_REVIEW` + `details.idp_error_code=IDP-E11`) | Four-eyes trường trọng yếu; FR-DC-20, 21 |
| EP-32 | `{ reason }` | `DocumentOut` (`REJECTED`) | `409`, `422` | `ACT-reject_document` |
| EP-33 | `{ reason }` | `DocumentOut` (`ROLLED_BACK`) | `410 UNDO_EXPIRED`, `409 CONFLICT_STATE` (bản ghi đích đã sửa — `details.diff`) | `ACT-rollback_document`; FR-DC-22 |
| EP-34 | `{ mode: RETRY\|REOPEN\|FORCE_DUPLICATE }` | `202 DocumentOut` | `409 CONFLICT_STATE` | `FORCE_DUPLICATE` ghi audit |
| EP-35 | — | `204` | `409` | |
| EP-36 | `{ sheet, mapping: [{ column, field }], save_template: bool }` | `202 { document, valid_rows, error_rows: [{ row_no, errors[] }] }` | `422` | Ghi dòng hợp lệ, không chặn bởi dòng lỗi |
| EP-37 | `{ segments: [{ page_from, page_to, doc_type? }] }` | `[DocumentOut]` (tài liệu con; cha → `SPLIT`) | `409`, `422` | FR-DC-09 |
| EP-38 | `format=xlsx\|csv` | `{ url (presigned) }` | `404` | |
| EP-39 | `doc_type?`, `from?`, `to?` | `[{ doc_type, field_path, docs, accuracy_pct, stp_pct, avg_review_seconds, suggest_relax: bool }]` | — | §7.4 04 (≥ 98% / 200 tài liệu) |
| EP-40 | C `{ name, purpose: ONBOARDING\|BULK }`; L phân trang | `ImportBatchOut` | — | UC-07 |
| EP-41 | — | `ImportBatchOut + { documents: [DocumentOut], progress: { total, committed, needs_review, failed }, cross_checks: [{ xd_code, docs[], status }] }` | `404` | |

**DocumentOut:** `id`, `batch_id`, `parent_id`, `channel` (`C1..C5`), `filename`, `mime`, `size_bytes`, `page_count`, `doc_type`, `pillars[]`, `status` (04 §8.1: `UPLOADED, PREPROCESSING, CLASSIFYING, EXTRACTING, VALIDATING, NEEDS_REVIEW, IN_REVIEW, AUTO_APPROVED, APPROVED, COMMITTED, REJECTED, FAILED, DUPLICATE, ROLLED_BACK, SPLIT`), `status_reason?`, `ai_state` (i18n key nhãn AI — P02), `autonomy_level` (`L0..L3`), `routing_decision?` (`STP\|REVIEW`), `routing_reason?`, `contains_salary`, `contains_pii`, `scan_status`, `duplicate_of_id?`, `uploaded_by`, `created_at`, `committed_at?`, `undo_deadline?`, `locked_by?`, `locked_until?`, `retry_count`, `latest_job?: JobOut`, `can: { review, approve, rollback, retry, open_source }`.

**FieldResult:** `path`, `label_key`, `value`, `raw_text`, `confidence` (0..1), `band` (`HIGH ≥ 0,90 \| MEDIUM 0,60–<0,90 \| LOW < 0,60` — DEC-133), `is_critical`, `source_location: { kind: page\|cell\|transcript\|form, page_no?, bbox?, sheet?, cell?, char_range? }`, `validation: pass\|warn\|fail`, `corrected_value?`, `corrected_by?`.

**JobOut:** `id`, `attempt_no`, `status`, `classification_confidence`, `routing_decision`, `error_code?` (`IDP-Exx`), `model_calls`, `started_at`, `finished_at`.

### 4.4. Execution (EP-42..49)

| EP | Field chính (request C/U) | Bộ lọc L | Quy tắc / lỗi | Event |
|---|---|---|---|---|
| EP-42 | `title`, `held_at`, `participants[]` (employee_id), `source_document_id?`, `recording_consent` | `from`, `to`, `department_id` | — | — |
| EP-43 | `meeting_id?`, `title`, `rationale`, `rejected_options[]`, `decided_by`, `expected_outcome`, `review_at[]` (30/60/90 ngày) | `status`, `meeting_id` | Rủi ro `accepted` tạo Decision (BR-RSK-02) | — |
| EP-44 | `title`, `assignee_id`, `due_date`, `priority`, `status` (`todo, in_progress, done, cancelled`), `project_id?`, `decision_id?`, `key_result_id?`, `source_location?` | `assignee_id`, `status`, `overdue`, `department_id` | EMPLOYEE chỉ cập nhật task của mình (scope `o`) | `EVT-execution.task_overdue` (scheduler) |
| EP-45 | `name`, `owner_id`, `department_id`, `start_date`, `due_date`, `status` | `status`, `department_id` | — | — |
| EP-46 | Objective: `title`, `owner_id`, `period_key`, `parent_id?`; KR (`/{id}/key-results`): `title`, `baseline`, `target`, `unit`, `owner_id` | `period_key`, `owner_id` | Kích hoạt chỉ sau duyệt (US-DC-005) | — |
| EP-47 | KPI: `code`, `name`, `unit`, `target`, `owner_id`, `metric_code?`; measurement: `period_key`, `actual_value` | `owner_id`, `metric_code` | — | `EVT-execution.kpi_measured` |
| EP-48 | `key_result_id \| kpi_id`, `value`, `confidence`, `note` | `owner_id`, `period_key` | ≤ 30 giây UX (US-EMP-03) | `EVT-execution.kpi_measured` (khi là KPI) |
| EP-49 | `period?`, `department_id?` | — | `summary`: `tasks_on_time_pct`, `projects_late`, `decision_execution_pct`, `overloaded_count`; `workload_heatmap: [{ employee_ref, week, load_pct }]`; `ontime_trend` | — |

### 4.5. Config, audit, notification (EP-50..59)

| EP | Request / Query | Response `data` | Ghi chú |
|---|---|---|---|
| EP-50 | C/U `{ code, name_key, pillars[], target_actions[], fields: [{ path, type, is_critical, threshold_auto }], classify_threshold, stp_enabled }` | `DocumentTypeOut` + `schemas: [{ version, status }]` | Sửa schema = version mới (FR-DC-23); `idp:admin` |
| EP-51 | `{ doc_type, rule_code, expression, severity: warn\|fail, message_key }` | `ValidationRuleOut` | |
| EP-52 | `actor_user_id?`, `actor_type?`, `action?`, `target_type?`, `target_id?`, `from`, `to`, phân trang | `[AuditLogOut]` (before/after đã mask) | Append-only; không có C/U/D |
| EP-53 | L `unread?`; U `{ read: true }` hoặc `POST /platform/notifications/read-all` | `[NotificationOut { id, kind, title_key, params, link, severity?, read_at }]` | FR-NTF-01; chỉ của tôi |
| EP-54 | PATCH `{ key, value }` (whitelist: retention, `REVIEW_SLA_HOURS`, `NOTIFY_EMAIL_ENABLED`, …) | `[{ key, value, updated_by, updated_at }]` | `ai.kill_switch` **không** sửa ở đây (EP-118) |
| EP-55 | U `{ warning, critical, enabled }` theo `metric_code` | `[MetricConfigOut]` | Đổi ngưỡng → tính lại status; NFR-19 |
| EP-56 | L `consumer?`, `event_type?`; `POST /platform/dead-letters/{id}/replay` | `[{ event_id, event_type, consumer, attempts, last_error }]` | Replay idempotent theo `(event_id, consumer)` |
| EP-57 | — | `{ services: [{ name, status }], outbox_pending, dlq_count, ai: { mode, primary, budget_used_pct, kill_switch } }` | Trang chủ ADMIN (03 §10) |
| EP-58 | `role_code` | `{ permissions[], pillars: [{ pillar, access: full\|aggregate\|none }], tools: [TOOL-*] }` | Không trả dữ liệu nghiệp vụ (US-ADM-04) |
| EP-59 | — | `[{ role_id, role_code, name_key, permissions[] }]` | Nguồn: 02 §5.3 |

### 4.6. Finance (EP-60..69)

| EP | Field chính (C/U) | Bộ lọc L | Quy tắc / lỗi | Event |
|---|---|---|---|---|
| EP-61 | `amount` (> 0), `currency`, `category` (`product_sales, service, consulting, other`), `recognized_on`, `client_id?`, `product_id?`, `department_id?` | `period`, `category`, `client_id` | `422 BUSINESS_RULE_VIOLATION` khi `amount ≤ 0` | `EVT-finance.forecast_updated` (gián tiếp) |
| EP-62 | `amount`, `category` (`cogs, salary, infrastructure, marketing, office, travel, other`), `department_id`, `spent_on`, `is_recurring`, `vendor?` | `period`, `department_id`, `category` | MANAGER chỉ phòng mình (`403 FORBIDDEN_SCOPE`) | `EVT-finance.budget_exceeded` (BR-FIN-05) |
| EP-63 | `department_id`, `fiscal_year`, `quarter`, `category`, `allocated_amount` | `fiscal_year`, `quarter`, `department_id` | UQ (phòng ban, năm, quý, hạng mục) → `409 DUPLICATE_RESOURCE` | — |
| EP-64 | `period?`, `department_id?` | — | `[{ department_id, allocated_amount, spent_amount, budget_utilization_pct, status }]` | — |
| EP-65 | `period` (`YYYY-MM`), `opening_balance`, `closing_balance` (≥ 0), `source` (`bank_statement, manual, imported`) | `from`, `to` | UQ kỳ → `409 DUPLICATE_RESOURCE` | — |
| EP-66 | `scenario` (`optimistic, base, pessimistic`), `horizon` (`1m, 3m, 6m, 1y`), `lines: [{ period_key, revenue, expense }]`, `confidence_pct` | `scenario`, `horizon` | — | `EVT-finance.forecast_updated` |
| EP-67 | `client_id`, `number`, `issued_on`, `due_date` (> `issued_on`), `lines: [{ description, quantity, unit_price, vat_pct = 10 }]`, `status` | `status`, `client_id`, `overdue`, `period` | ≥ 1 dòng; `409 DUPLICATE_RESOURCE` trùng `number` | — |
| EP-68 | `{ amount_paid, paid_at, method? }` | — | `409 CONFLICT_STATE` (`void`/`paid`); thanh toán một phần → `partially_paid` | `EVT-finance.invoice_paid` khi đủ |
| EP-69 | `as_of?` | — | `{ runway_months_no_new_revenue, closing_balance, avg_expense_3m, sources[] }` (BR-FIN-06); `null` + `status_reason` khi thiếu CashPosition | — |

### 4.7. Sales (EP-70..78)

| EP | Field chính (C/U) | Bộ lọc L | Quy tắc / lỗi | Event |
|---|---|---|---|---|
| EP-71 | `name` (duy nhất), `tax_code?`, `industry`, `size`, `contacts: [{ name, email, phone }]` (PII mức 3) | `q`, `industry` | `409 DUPLICATE_RESOURCE`; trả `similar_clients[]` khi tên gần trùng | — |
| EP-72 | `name`, `client_id`, `deal_value` (> 0), `currency`, `probability_pct`, `expected_close_date` (> hôm nay khi tạo), `owner_id`, `product_id?` | `stage`, `owner_id`, `client_id`, `expected_close_from/to` | D chỉ ROLE-03 | — |
| EP-73 | `{ to_stage, lost_reason? }` | — | Chuyển theo thứ tự 03 §5.2; `closed_lost` bắt buộc `lost_reason`; `probability_pct` tự đặt 100/0 (BR-SAL-01); `409 CONFLICT_STATE` từ trạng thái đóng | `EVT-sales.deal_closed_won` / `_lost` |
| EP-74 | — | — | `[{ from_stage, to_stage, changed_by, changed_at }]` | — |
| EP-75 | `period?`, `owner_id?` | — | `[{ stage, count, value, weighted_value, avg_days_in_stage }]` + `coverage_ratio` (BR-SAL-04) | — |
| EP-76 | `period?`, `group_by=team\|owner` | — | `[{ owner_ref, closed_value, quota, attainment_pct, win_rate_pct }]` | — |
| EP-77 | `period_type` (`month, quarter, year`), `period_key`, `scope` (`team, individual`), `owner_id?`, `target_amount` | `period_key`, `scope` | `owner_id` bắt buộc khi `individual`; CEO chỉ ghi target (`sales:write ◑t`) | — |
| EP-78 | `client_id`, `deal_id?`, `value`, `start_date`, `end_date`, `renewal_date?`, `milestones[]` | `client_id`, `expiring_within_days` | — | — |

### 4.8. HR (EP-80..87)

| EP | Field chính (C/U) | Bộ lọc L | Quy tắc / lỗi | Event |
|---|---|---|---|---|
| EP-81 | `name`, `code`, `parent_id?`, `manager_id?` | `parent_id` | Không tạo chu trình (`422`) | — |
| EP-82 | `employee_code`, `full_name`, `email`, `department_id`, `title`, `contract_type` (`full_time, part_time, contract, intern`), `status` (`probation, active, on_leave, terminated`), `hire_date`, `termination_date?`; mức 4 (`date_of_birth`, `address`, …) chỉ ROLE-01/04 | `department_id`, `status`, `q` | Role không có quyền lương nhận `{ masked: true }`; EMPLOYEE chỉ hồ sơ mình | `EVT-hr.employee_onboarded` / `_terminated` |
| EP-83 | C `{ effective_date, base_salary, currency, reason }` | — | Đọc ngoài ROLE-01/04 → `403 FORBIDDEN_SALARY`; append-only | `EVT-hr.salary_updated` (không có số lương) |
| EP-84 | `department_id`, `position`, `headcount` (≥ 1), `salary_min`, `salary_max` (≥ min), `start_date`, `target_date`, `priority`, `budget_amount`, `filled` | `department_id`, `status`, `delayed` | Trạng thái `draft → submitted → approved/rejected` | `EVT-hr.hiring_plan_delayed` (job) |
| EP-85 | — | — | Chỉ từ `draft`; `409 CONFLICT_STATE` | — |
| EP-86 | `{ decision: approve\|reject, reason }` | — | `reason` bắt buộc; duyệt → chi phí lương dự kiến vào Forecast (FR-HR-07) | `EVT-finance.forecast_updated` (do finance) |
| EP-87 | `period?`, `department_id?` | — | `[{ employee_ref, open_tasks, load_pct, overloaded }]` (METRIC-HR-03) | — |
| EP-80 | `period?` | — | §5 | — |

### 4.9. Product & Risk (EP-90..106)

| EP | Field chính (C/U) | Quy tắc / lỗi | Event |
|---|---|---|---|
| EP-91 | `code` (duy nhất), `name`, `status` (`ideation, in_development, beta, launched, sunset`), `lifecycle_stage`, `owner_id` | D bị chặn khi còn Feature `in_progress` / Release `planned, in_progress` → `422 BUSINESS_RULE_VIOLATION` | — |
| EP-92 | `product_id`, `name`, `status` (`backlog, in_progress, released, …`), `release_id?` | — | `EVT-product.feature_released` |
| EP-93 | `product_id`, `title`, `quarter`, `target_date`, `status` (`planned, in_progress, done, dropped`) | — | — |
| EP-94 | `product_id`, `version` (UQ theo sản phẩm), `status` (`planned, in_progress, released, rolled_back`), `released_at?` | `409 DUPLICATE_RESOURCE` | `EVT-product.product_launched` (release đầu) |
| EP-95 | C `{ period_key, mau, adoption_pct, churn_rate_pct, retention_30d_pct, nps, arpu }` | Append-only; trùng kỳ → bản mới đánh dấu `superseded` bản cũ | `EVT-product.metric_anomaly` (BR-PRD-01) |
| EP-101 | `title`, `category` (`financial, operational, market, people, compliance, technology, strategic`), `likelihood` (1..5), `impact` (1..5), `owner_id?`, `linked_entities[]` | `risk_score`, `level`, `code RSK-YYYY-NNN` do hệ thống sinh; `medium`+ nhập tay bắt buộc owner (BR-RSK-02) | `EVT-risk.risk_identified` (≥ high) |
| EP-102 | `{ likelihood, impact, note }` | Level đổi → assessment mới | `EVT-risk.risk_level_changed` |
| EP-103 | `risk_id`, `title`, `owner_id`, `due_date`, `progress_pct`, `status` (`planned, in_progress, done, cancelled`) | — | `EVT-risk.risk_mitigated` (khi risk → `monitoring`) |
| EP-104 | `{ reason }` | Chỉ CEO; tạo `ENT-Decision`; `409 CONFLICT_STATE` từ `closed` | — |
| EP-105 | `{ risk_ids: [1..10], horizon_months: 1..24, assumptions? }` | `{ scenario_id, impacts: { finance: { status: ok\|unavailable, revenue_delta, expense_delta, runway_delta_months }, sales: {…pipeline_delta}, hr: {…headcount_delta}, product: {…roadmap_items_at_risk} }, sources[] }`; mỗi miền timeout 5 s → `unavailable` | — (lưu `ENT-Scenario`) |
| EP-106 | `{ to_status, reason? }` | Vòng đời BR-RSK-02; không đóng khi còn mitigation `in_progress` (`422`); owner bắt buộc trước `mitigating`/`closed` | `EVT-risk.risk_mitigated` (`monitoring`/`closed`) |

### 4.10. AI Core (EP-110..119)

| EP | Request | Response `data` | Lỗi | Ghi chú |
|---|---|---|---|---|
| EP-110 | `{ message (≤ 4000 ký tự), conversation_id?, context?: { screen: SCR-xx, entity_ref?, metric_code?, period? }, locale? }` | `{ conversation_id, message_id, answer, sources: [SourceRef], function_calls: [{ tool, status, latency_ms }], suggested_actions: [AIActionOut], truncated, warnings[] }` | `422 AI_CONTEXT_TOO_LARGE`, `429 AI_QUOTA_EXCEEDED`, `502 AI_PROVIDER_ERROR`, `502 AI_FUNCTION_CALL_FAILED`, `504 AI_PROVIDER_TIMEOUT` | Ngữ cảnh 10 cặp tin nhắn gần nhất (FR-AI-05); `Idempotency-Key` bắt buộc |
| EP-111 | như EP-110 | `text/event-stream` (§6) | Lỗi trước khi stream → JSON như EP-110; sau khi stream → event `error` | Client hủy (nút Dừng) → server dừng tool + lưu lượt `truncated:true` |
| EP-112 | L phân trang; R `/{id}/messages`; D | `[ConversationOut { id, title, last_message_at }]`; messages `[MessageOut { id, sender, content, sources, function_calls, truncated, created_at }]` | `404` (hội thoại người khác → `404`, không lộ tồn tại) | DS5; D = xóa mềm |
| EP-113 | `{ message_id? \| insight_id?, rating: up\|down, reason?: inaccurate_number\|missing_context\|too_verbose\|not_relevant\|other, comment? }` | `201 FeedbackOut` | `422` (thiếu cả hai id) | US-ALL-03 |
| EP-114 | L `pillar?`, `kind?`, `severity?`; `POST /ai/insights/{id}/dismiss` | `[InsightOut { id, kind, pillar, severity, observation, evidence: [SourceRef], impact?, recommendations: [{ text, action?: AIActionOut }], confidence: { band, reason }, created_at, expires_at }]` | — | Lọc theo `audience_roles` + scope; insight không nguồn không trả |
| EP-115 | L `status?` (`proposed, executed, undone, …`), `autonomy_level?`, `from`; R; `POST /ai/actions/{id}/confirm` `{ edited_input? }`; `POST /ai/actions/{id}/reject` `{ reason }` | `AIActionOut { id, action_name (ACT-*), tool_name (TOOL-*), autonomy_level, status, input_preview, result_refs, on_behalf_of, executed_at, undo_deadline, can_undo }` | `409 CONFLICT_STATE`, `422 ACTION_REJECTED`, `403` thiếu `<domain>:write` | Confirm cần `ai:write` **và** `<domain>:write` đích; kill switch không chặn confirm L2 (người xác nhận) |
| EP-116 | `{ reason? }` | `AIActionOut` (`undone`) | `410 UNDO_EXPIRED` (> 24 giờ), `409 CONFLICT_STATE` (bản ghi đã sửa) | DEC-134; hành động do IDP STP hoàn tác qua EP-33 (7 ngày) |
| EP-117 | `{ action_name (ACT-* \| *), role_code?, max_amount?, currency?, level: L0..L3, max_level }` | `[AutonomyPolicyOut]` | `422` (L4 hoặc `level > max_level`) | Hạ level hiệu lực ngay; nâng chỉ cho tài liệu mới (04 §9.1) |
| EP-118 | PUT `{ enabled: bool, mode: WRITE_OFF\|L0, reason }` | `{ enabled, mode, changed_by, changed_at }` | `422` (thiếu lý do) | CEO chỉ bật/tắt (`ai:admin ◑k`); audit `ai.kill_switch` + `EVT-platform.alert_raised` |
| EP-119 | `/ai/tools` —; `/ai/usage` `from`, `to`, `group_by=provider\|model\|task_kind\|user` | Tools: `[{ name: TOOL-*, kind: READ\|WRITE\|COMPUTE, autonomy_default, available: bool }]`; Usage: `{ budget_usd, used_usd, used_pct, rows: [{ key, calls, tokens_in, tokens_out, cost_usd, error_rate, p95_ms }] }` | — | Cảnh báo 80% ngân sách (DEC-131) |

**SourceRef (source chip):** `{ type: metric_value\|record\|document_page\|tool_result, id, label, metric_code?, period_key?, value?, lineage_url }`. Mọi con số trong `answer` phải có ≥ 1 SourceRef (P01, P05); không có dữ liệu → `warnings: ["AI_NO_DATA_AVAILABLE"]`.

---

## 5. Hợp đồng dashboard domain (`/{domain}/dashboard`)

Áp cho EP-49 (execution, dùng cùng HR cho PIL-O), EP-60, EP-70, EP-80, EP-90, EP-100 (03 §9).

```json
{
  "data": {
    "pillar": "F",
    "status": "warning",
    "period": { "key": "2026-10", "type": "current_month", "start_date": "2026-10-01", "end_date": "2026-10-31" },
    "summary": {
      "total_revenue": 8250000000, "total_expense": 7900000000, "net_profit": 350000000,
      "gross_margin_pct": 28.0, "runway_months": 6.4, "budget_utilization_pct": 93.5, "currency": "VND"
    },
    "metrics": [ { "metric_code": "METRIC-FIN-03", "value": 6.4, "unit": "MONTHS", "status": "warning", "computed_at": "…", "freshness": "fresh", "data_quality_pct": 92.0, "lineage_url": "/dashboard/metrics/METRIC-FIN-03" } ],
    "revenue_trend": [ { "period_key": "2025-11", "revenue": 7100000000, "expense": 6900000000 } ],
    "runway_trend": [ { "period_key": "2025-11", "runway_months": 8.9 } ],
    "open_alerts": 2
  },
  "meta": { "generated_at": "…", "cache": { "max_age": 60 } }
}
```

| Quy tắc | Mô tả |
|---|---|
| `status` trụ | `ok` / `warning` / `critical` theo metric xấu nhất (03 §4); thêm `no_data` (≥ 50% metric `no_data`). `unavailable` **không** do endpoint trả — frontend tự gán khi endpoint lỗi/timeout (FR-DSH-07) |
| `summary` | Object phẳng, chỉ số và tiền BIGINT + `currency`; không lồng |
| `*_trend` | ≥ 1 mảng, key ổn định, sắp tăng dần theo `period_key`, vẽ trực tiếp bằng Recharts |
| `metrics[]` | `MetricValueOut` (§4.2) cho mọi metric của trụ |
| `query` không kèm `read` | Chỉ trả tổng hợp; `lineage_url` vẫn có nhưng EP-13 trả `403 FORBIDDEN_SCOPE` |
| Kỳ | `period` (§1.5); `custom` chỉ cho EP-60 |
| Cache | `private, max-age=60` + `Vary: Authorization`; server cache theo (scope, period), xóa khi metric tính lại |

`summary` tối thiểu theo domain:

| EP | Trụ | `summary` | `*_trend` |
|---|---|---|---|
| EP-60 | F | `total_revenue`, `total_expense`, `net_profit`, `gross_margin_pct`, `gross_burn` (BR-FIN-04), `net_burn`, `runway_months`, `revenue_growth_pct`, `budget_utilization_pct`, `overdue_ar`, `dso_days` | `revenue_trend` (12 tháng), `runway_trend` |
| EP-70 | C | `pipeline_value`, `weighted_pipeline`, `deals_open`, `deals_won`, `deals_lost`, `win_rate_pct`, `avg_deal_value`, `closed_revenue`, `quota_attainment_pct`, `avg_sales_cycle_days`, `pipeline_coverage` | `pipeline_trend`, `win_rate_trend` |
| EP-80 | O (con người) | `headcount`, `active`, `on_leave`, `terminated`, `new_hires`, `turnover_rate_pct`, `avg_tenure_months`, `payroll_total` (tổng hợp), `open_positions`, `revenue_per_employee` | `headcount_trend`, `turnover_trend` |
| EP-49 | O (thực thi) | `tasks_on_time_pct`, `projects_late`, `decision_execution_pct`, `overloaded_count` | `ontime_trend` |
| EP-90 | U | `products_total`, `products_active`, `products_in_dev`, `mau`, `adoption_pct`, `churn_rate_pct`, `retention_30d_pct`, `nps`, `arpu`, `features_released`, `roadmap_on_time_pct` | `mau_trend`, `churn_trend` |
| EP-100 | S | `open_risks`, `critical_count`, `high_count`, `aggregate_risk_score`, `opened_in_period`, `closed_in_period`, `mitigations_active`, `mitigations_overdue`, `unacknowledged_alerts`, `strategy_execution_index`; `heatmap: [{ likelihood, impact, count }]` | `risk_score_trend` |

PIL-O được ghép ở frontend từ EP-80 + EP-49; trạng thái trụ O = mức xấu nhất của hai phần (OQ-06).

---

## 6. SSE — `POST /ai/chat/stream` (EP-111)

Header response: `Content-Type: text/event-stream`, `Cache-Control: no-store`, `X-Accel-Buffering: no`, `X-Request-Id`. Mỗi event có `event:` + `data:` (JSON một dòng) + `id:` tăng dần. Heartbeat comment `: ping` mỗi 15 giây.

| Event | Thời điểm | `data` |
|---|---|---|
| `start` | Ngay khi nhận request hợp lệ | `{ conversation_id, message_id, request_id, model_route: { task: chat } }` |
| `thinking` | Mỗi bước suy luận hiển thị cho người dùng (bước thật, P02) | `{ step_key, params }` — VD `{ "step_key": "ai.step.reading_finance_dashboard" }` |
| `tool_call` | Trước khi gọi một tool | `{ call_id, tool: "TOOL-get_finance_dashboard", arguments_preview }` (đã mask) |
| `tool_result` | Tool trả kết quả | `{ call_id, tool, status: ok\|error\|forbidden\|timeout, latency_ms, sources: [SourceRef] }` — **không** trả dữ liệu thô |
| `token` | Từng đoạn văn bản trả lời | `{ delta }` |
| `done` | Kết thúc thành công (sau khi đã lưu lượt vào DB) | `{ message_id, answer, sources: [SourceRef], function_calls: [{ tool, status, latency_ms }], suggested_actions: [AIActionOut], truncated, warnings[], usage: { tokens_in, tokens_out } }` |
| `error` | Lỗi sau khi đã bắt đầu stream (kết thúc stream) | `{ code: AI_PROVIDER_ERROR\|AI_PROVIDER_TIMEOUT\|AI_QUOTA_EXCEEDED\|AI_FUNCTION_CALL_FAILED\|AI_CONTEXT_TOO_LARGE\|INTERNAL_ERROR, message, partial_message_id? }` |

Quy tắc:

1. Thứ tự: `start` → (`thinking` \| `tool_call` → `tool_result`)* → `token`* → `done` \| `error`. Đúng **một** event kết thúc.
2. Giới hạn lượt (DEC-131): ≤ 8 tool call/lượt, 5 giây/tool, 30 giây/lượt, ≤ 2048 output token, temperature 0,2. Chạm giới hạn → trả lời từng phần, `truncated: true` trong `done` (không phải `error`).
3. Tool bị từ chối quyền (`forbidden`) → AI nói rõ người dùng không có quyền với dữ liệu đó (FR-AI-02), không thử vòng.
4. Lượt (kể cả bị cắt hoặc bị hủy) được lưu `ENT-Message` trước khi gửi `done` (FR-AI-04, FR-AI-05); hủy giữa chừng → lưu `truncated: true`.
5. Retry provider: tối đa 2 lần với 5xx/timeout rồi chuyển provider fallback (DEC-131); event `thinking` có thể báo `ai.step.switching_provider`.

---

## 7. Tool Registry (`TOOL-<name>`)

AI Core chỉ gọi tool trong registry dưới đây; tool khả dụng của một lượt = tool có **permission** người hỏi đang có (02 §7.2). Tool đọc gọi service nội bộ tương đương endpoint, với **JWT của người hỏi**; tool ghi tạo `ENT-AIAction` rồi thực thi `ACT-*` qua Action Registry (04 §10) theo `ENT-AutonomyPolicy`. `risk_level`: `low` (đọc tổng hợp), `medium` (đọc chi tiết / tính toán / ghi nội bộ hoàn tác được), `high` (ghi tài chính, nhân sự, hợp đồng). Autonomy mặc định: READ/COMPUTE = **L0**; WRITE theo 04 §9.1.

### 7.1. Tool đọc / tính toán

| Tool | Endpoint gọi | Permission | Kind | risk_level | Autonomy mặc định |
|---|---|---|---|---|---|
| TOOL-get_finance_dashboard | EP-60 | `finance:query` | READ | low | L0 |
| TOOL-get_finance_forecast | EP-66.L | `finance:read` | READ | medium | L0 |
| TOOL-list_expenses | EP-62.L | `finance:read` | READ | medium | L0 |
| TOOL-get_budget_status | EP-64 | `finance:query` | READ | low | L0 |
| TOOL-list_invoices | EP-67.L | `finance:read` | READ | medium | L0 |
| TOOL-get_runway_what_if | EP-69 | `finance:query` | COMPUTE | low | L0 |
| TOOL-get_sales_dashboard | EP-70 | `sales:query` | READ | low | L0 |
| TOOL-list_deals | EP-72.L | `sales:read` | READ | medium | L0 |
| TOOL-get_sales_pipeline | EP-75 | `sales:query` | READ | low | L0 |
| TOOL-get_hr_dashboard | EP-80 | `hr:query` | READ | low | L0 |
| TOOL-list_hiring_plans | EP-84.L | `hr:read` | READ | medium | L0 |
| TOOL-get_workload | EP-87 | `hr:query` | READ | low | L0 |
| TOOL-get_product_dashboard | EP-90 | `product:query` | READ | low | L0 |
| TOOL-get_product_metrics | EP-95.L | `product:query` | READ | low | L0 |
| TOOL-get_risk_dashboard | EP-100 | `risk:query` | READ | low | L0 |
| TOOL-list_risks | EP-101.L | `risk:read` | READ | medium | L0 |
| TOOL-run_risk_scenario | EP-105 | `risk:query` | COMPUTE | medium | L0 (lưu `ENT-Scenario`, không đổi dữ liệu nghiệp vụ) |
| TOOL-get_execution_dashboard | EP-49 | `execution:query` | READ | low | L0 |
| TOOL-list_tasks | EP-44.L | `execution:read` | READ | medium | L0 |
| TOOL-list_objectives | EP-46.L | `execution:read` | READ | medium | L0 |
| TOOL-get_metric | EP-12 | `dashboard:read` | READ | low | L0 |
| TOOL-list_alerts | EP-15 | `dashboard:read` | READ | low | L0 |
| TOOL-get_lineage | EP-14 | `dashboard:read` | READ | medium | L0 |
| TOOL-search_documents | EP-24 (+ RAG pgvector SOP/chính sách) | `idp:read` | READ | medium | L0 |
| TOOL-get_source_document | EP-25, EP-27 (trang + bbox, không URL thô cho LLM) | `idp:read` | READ | medium | L0 |

### 7.2. Tool ghi (qua `ACT-*`)

| Tool | Endpoint / Action | Permission (cả hai) | risk_level | Autonomy mặc định / tối đa |
|---|---|---|---|---|
| TOOL-create_task | EP-44.C / ACT-create_task | `ai:write` + `execution:write` | medium | L3 / L3 |
| TOOL-record_decision | EP-43.C / ACT-record_decision | `ai:write` + `execution:write` | medium | L3 / L3 |
| TOOL-create_meeting | EP-42.C / ACT-create_meeting | `ai:write` + `execution:write` | medium | L3 / L3 |
| TOOL-record_kpi_measurement | EP-47 / ACT-record_kpi_measurement | `ai:write` + `execution:write` | medium | L2 / L3 |
| TOOL-record_expense | EP-62.C / ACT-record_expense | `ai:write` + `finance:write` | high | L2 / L3 (< 5.000.000 đ sau §7.4 của 04) |
| TOOL-create_invoice | EP-67.C / ACT-create_invoice | `ai:write` + `finance:write` | high | L2 / L3 |
| TOOL-upsert_deal | EP-72 / ACT-upsert_deal | `ai:write` + `sales:write` | high | L2 / L2 |
| TOOL-upsert_risk | EP-101 / ACT-upsert_risk | `ai:write` + `risk:write` | medium | L2 / L2 |
| TOOL-create_mitigation | EP-103.C / ACT-create_mitigation | `ai:write` + `risk:write` | medium | L2 / L2 |
| TOOL-submit_document | EP-22 (C2 nhập lời) | `ai:write` + `idp:write` | medium | L2 / L2 (luôn action card) |

Quy tắc:

1. Kết quả tool gửi LLM đã lọc PII/lương (§2.4), bọc trong delimiter "dữ liệu" (prompt injection — 07 §Bảo mật).
2. Kill switch `WRITE_OFF` → mọi tool ghi chỉ tạo action card L2; `L0` → tool ghi bị gỡ khỏi danh sách.
3. Mỗi tool call ghi `ENT-ToolCallLog` (`tool_name`, `arguments` mask, `status`, `http_status`, `latency_ms`).
4. Thêm tool = đổi contract → cập nhật bảng này + 02 §7.2 trước.

---

## 8. Event contract (DEC-126)

### 8.1. Envelope

```json
{
  "event_id": "1b6c2f0e-…",
  "event_type": "finance.invoice_paid",
  "occurred_at": "2026-10-19T03:15:00Z",
  "version": 1,
  "correlation_id": "<X-Request-Id gốc>",
  "producer": "finance",
  "payload": { "invoice_id": "…", "client_id": "…", "amount_paid": 27500000, "currency": "VND", "paid_at": "…" }
}
```

| Field | Quy tắc |
|---|---|
| `event_id` | UUID = `platform.outbox_events.id`; khóa khử trùng của consumer |
| `event_type` | `<domain>.<name>` (mã registry bỏ tiền tố `EVT-`). Breaking change → tên `_v2` mới, chạy song song |
| `version` | Phiên bản payload (bắt đầu 1); thêm field optional không tăng |
| `correlation_id`, `producer` | Bổ sung cho quan sát (OQ-07) — không bắt buộc consumer đọc |
| `payload` | Chỉ id + số tổng hợp; **không** chứa dữ liệu mức 3–4 (PII, lương) |

### 8.2. Vận chuyển & xử lý

| # | Quy tắc |
|---|---|
| E1 | Publisher ghi `ENT-OutboxEvent` **trong cùng transaction** với thay đổi nghiệp vụ; không publish trước commit |
| E2 | Relay (Celery beat — **một** instance) đọc `PENDING` bằng `FOR UPDATE SKIP LOCKED`, gửi lên broker Redis, đánh dấu `PUBLISHED` |
| E3 | Consumer là Celery task `acks_late=True` (manual ack); trước khi xử lý kiểm tra `ENT-ProcessedEvent (event_id, consumer)`; đã có → bỏ qua |
| E4 | Lỗi → retry 3 lần backoff **5 s / 30 s / 120 s**; vẫn lỗi → `processed_events.status = DLQ` + alert ADMIN; phát lại qua EP-56 |
| E5 | Không giả định thứ tự giữa các loại event; consumer dựa `occurred_at` và đọc trạng thái hiện tại qua service interface khi cần |
| E6 | AI Core consume **mọi** event (làm mới insight, debounce 5 phút/trụ) nhưng **không** phát event nghiệp vụ |
| E7 | Tên consumer: `<module>.on_<event_name>` (VD `risk.on_hiring_plan_delayed`) |

### 8.3. Bảng publish / consume

| Event | Publisher (EP/job) | Consumer | Hành động của consumer |
|---|---|---|---|
| EVT-hr.employee_onboarded | hr (EP-82, ACT-upsert_employee) | finance, platform, ai | finance: cập nhật dự báo chi phí lương; platform: tính lại METRIC-HR-01..03 |
| EVT-hr.employee_terminated | hr (EP-82) | finance, risk, platform, ai | finance: dự báo; risk: đánh giá rủi ro nhân sự chủ chốt; platform: METRIC-HR-02 |
| EVT-hr.salary_updated | hr (EP-83) | finance, ai | finance: đọc tổng quỹ lương qua `hr` service, cập nhật dự báo |
| EVT-hr.hiring_plan_delayed | hr (job hằng ngày, FR-HR-04) | risk, finance, platform | risk: tạo Risk `source=event` (BR-RSK-03); finance: điều chỉnh dự báo; platform: ALERT-HR-04 |
| EVT-sales.deal_closed_won | sales (EP-73) | finance, product, platform | finance: doanh thu dự kiến; product: gắn adoption; platform: METRIC-CUS-* |
| EVT-sales.deal_closed_lost | sales (EP-73) | finance, risk, platform | risk: tạo Risk khi deal ≥ `RISK_LOST_DEAL_MIN_VALUE` |
| EVT-finance.budget_exceeded | finance (EP-62, BR-FIN-05) | hr, risk, platform | hr: cảnh báo tuyển dụng phòng ban; risk: Risk `financial`; platform: ALERT-FIN-06 |
| EVT-finance.invoice_paid | finance (EP-68) | sales, product, platform | sales: NRR/doanh thu thực thu; platform: METRIC-FIN-04/05 |
| EVT-finance.forecast_updated | finance (EP-66, EP-86 gián tiếp) | risk, platform, ai | risk: đánh giá lại rủi ro tài chính |
| EVT-finance.burn_over_forecast | finance (job FR-FIN-08) | risk, platform | risk: Risk `financial`; platform: ALERT-FIN-07 |
| EVT-product.product_launched | product (EP-94) | sales, finance | sales: cập nhật danh mục bán; finance: dự báo doanh thu |
| EVT-product.feature_released | product (EP-92) | sales | Thông báo đội sales |
| EVT-product.metric_anomaly | product (EP-95, BR-PRD-01) | risk, platform, ai | risk: Risk `market`; platform: ALERT-PRD-02 |
| EVT-risk.risk_identified | risk (EP-101, consumer) | finance, hr, product, platform | Gắn cờ rủi ro vào bản ghi liên kết; platform: ALERT-RSK-01 |
| EVT-risk.risk_level_changed | risk (EP-102) | finance, hr, platform | Cập nhật cờ; tính lại METRIC-RSK-* |
| EVT-risk.risk_mitigated | risk (EP-103, EP-106) | finance, hr, platform | Gỡ cờ; METRIC-RSK-* |
| EVT-execution.task_overdue | execution (job hằng ngày) | platform, ai | platform: METRIC-OPS-01, thông báo assignee |
| EVT-execution.kpi_measured | execution (EP-47, EP-48) | platform, ai | platform: metric có target, METRIC-RSK-06 |
| EVT-idp.document_committed | idp (EP-31, STP) | platform, ai, risk | platform: tính lại metric (≤ 10 s), quality score; risk: rủi ro từ `RISK_REGISTER` |
| EVT-idp.document_rolled_back | idp (EP-33) | platform, ai, mọi module có bản ghi | Tính lại metric, gỡ bản ghi bị hoàn tác |
| EVT-platform.alert_raised | platform (metric engine, EP-118) | ai, platform (notification) | ai: insight/briefing; notification: FR-NTF-01/02 |

Payload chi tiết từng event: `05-DATA-MODEL.md` §5.3 (nguồn chuẩn cột). Thêm event = cập nhật 00 §4.5, 05 §5.3 và bảng này trước.

---

## 9. Ma trận truy vết EP ↔ FR / US ↔ SCR

| EP | FR | US | SCR |
|---|---|---|---|
| EP-01 | NFR (07) | US-ALL-04 | SCR-15 |
| EP-02, EP-06, EP-07 | FR-AUTH-01, FR-AUTH-02 | — | SCR-13 |
| EP-03, EP-08 | FR-AUTH-03 | — | SCR-26 |
| EP-04, EP-05 | (demo, DEC-073) | — | SCR-13 |
| EP-09, EP-59 | FR-AUTH-04, FR-AUTH-05 | US-ADM-01 | SCR-26 |
| EP-10, EP-19 | FR-DSH-01, FR-DSH-04 | US-CEO-01, US-CEO-02, US-EMP-01 | SCR-01, SCR-28 |
| EP-11, EP-12, EP-18 | FR-DSH-02, FR-DSH-03, FR-DSH-05 | US-CEO-05 | SCR-02..07 |
| EP-13, EP-14 | FR-DSH-03, FR-DC-21 | US-CEO-05, US-DC-011 | SCR-07 |
| EP-15..17 | FR-RSK-05, FR-NTF-01 | US-SAL-04, US-RSK-03 | SCR-01..06 |
| EP-20 | FR-DC-01, 02, 05..08 | US-DC-003, US-EMP-02 | SCR-08, SCR-09, SCR-28 |
| EP-21 | FR-DC-04 | US-DC-001 | SCR-09 |
| EP-22 | FR-DC-03 | US-DC-002 | SCR-09, SCR-16 |
| EP-23, EP-36, EP-38 | FR-DC-18 | US-DC-007 | SCR-11 |
| EP-24, EP-25, EP-28 | FR-DC-17 | US-MGR-03 | SCR-08 |
| EP-26, EP-27, EP-29..32, EP-35 | FR-DC-10..16, 19, 20 | US-DC-006, US-DC-009, US-DC-010 | SCR-10 |
| EP-31, EP-33 | FR-DC-21, FR-DC-22 | US-DC-006 | SCR-10, SCR-08 |
| EP-34, EP-37 | FR-DC-05, FR-DC-09 | US-DC-003 | SCR-08, SCR-10 |
| EP-39, EP-50, EP-51 | FR-DC-23 | US-DC-008 | SCR-27 |
| EP-40, EP-41 | FR-DC-01, FR-DC-14 (UC-07) | US-DC-007 | SCR-12 |
| EP-42, EP-43, EP-44 | FR-DC-11 (UC-06) | US-DC-004, US-MGR-02 | SCR-18, SCR-19 |
| EP-45, EP-49 | (execution — OQ-08) | US-MGR-02 | SCR-19, SCR-03 |
| EP-46, EP-47, EP-48 | (execution — OQ-08) | US-DC-005, US-EMP-03 | SCR-20 |
| EP-52 | FR-DC-22 | US-ADM-04 | SCR-14 |
| EP-53 | FR-NTF-01, FR-NTF-02 | — | (header toàn cục) |
| EP-54..58 | FR-DSH-02 (ngưỡng cấu hình) | US-ADM-04 | SCR-15, SCR-26, SCR-27 |
| EP-60 | FR-FIN-07 | US-CFO-01 | SCR-02, SCR-22 |
| EP-61, EP-62, EP-65 | FR-FIN-01, FR-FIN-02, FR-FIN-04 | US-CFO-01, US-MGR-01 | SCR-22 |
| EP-63, EP-64 | FR-FIN-03 | US-CFO-02 | SCR-22 |
| EP-66 | FR-FIN-05, FR-FIN-08 | US-CFO-03, US-CFO-04 | SCR-22 |
| EP-67, EP-68 | FR-FIN-06 | US-CFO-05 | SCR-22 |
| EP-69 | FR-FIN-07 (BR-FIN-06), FR-AI-09 | US-CEO-04 | SCR-16 |
| EP-70, EP-75, EP-76 | FR-SAL-04, FR-SAL-05, FR-SAL-07 | US-SAL-03, US-SAL-04 | SCR-04, SCR-23 |
| EP-71 | FR-SAL-03 | US-SAL-02 | SCR-23 |
| EP-72..74 | FR-SAL-01, FR-SAL-02 | US-SAL-01, US-MGR-01 | SCR-23 |
| EP-77 | FR-SAL-06 | US-CEO-08 | SCR-23 |
| EP-78 | (03 §6.2 ghi chú Contract) | US-DC-010 | SCR-23 |
| EP-80, EP-87 | FR-HR-06 | US-HR-04, US-MGR-02 | SCR-03, SCR-24, SCR-19 |
| EP-81, EP-82, EP-83 | FR-HR-01, FR-HR-02, FR-HR-05 | US-HR-01 | SCR-24 |
| EP-84..86 | FR-HR-03, FR-HR-04, FR-HR-07 | US-HR-02, US-HR-03, US-CFO-06 | SCR-24 |
| EP-90 | FR-PRD-07 | US-PRD-01 | SCR-05, SCR-25 |
| EP-91..94 | FR-PRD-01..04 | US-PRD-01 | SCR-25 |
| EP-95 | FR-PRD-05, FR-PRD-06 | US-PRD-02, US-PRD-03 | SCR-25 |
| EP-100 | FR-RSK-07 | US-RSK-01 | SCR-06, SCR-21 |
| EP-101, EP-102, EP-106 | FR-RSK-01..03 | US-RSK-01, US-RSK-02 | SCR-21 |
| EP-103 | FR-RSK-04 | US-RSK-03 | SCR-21 |
| EP-104 | FR-RSK-01 (BR-RSK-02) | US-CEO-07 | SCR-21 |
| EP-105 | FR-RSK-06 | US-CEO-06 | SCR-21 |
| EP-110, EP-111 | FR-AI-01..04, FR-AI-08, FR-AI-10, FR-DSH-08 | US-CEO-03, US-AI-01, US-AI-02, US-AI-05 | SCR-16 |
| EP-112 | FR-AI-05 | US-ALL-02 | SCR-16 |
| EP-113 | FR-AI-06 | US-ALL-03 | SCR-16, SCR-01 |
| EP-114 | FR-AI-07, FR-DSH-04 | US-CEO-02 | SCR-01..06 |
| EP-115, EP-116 | FR-AI-08 (ghi qua `ACT-*`, OQ-15) | US-AI-03, US-AI-04 | SCR-17, SCR-16 |
| EP-117, EP-118, EP-119 | FR-DC-23 (autonomy) | US-ADM-02, US-ADM-03 | SCR-15 |

Test case `TC-<AREA>-xxx` cho từng EP do `14-TEST-TRACEABILITY.md` sở hữu (Gate C).

---

## 10. Open questions

| # | Câu hỏi | Đề xuất mặc định | Ảnh hưởng |
|---|---|---|---|
| OQ-01 | EP-20..41 giữ số v1 nhưng path đổi sang prefix module `/idp/...`; EP-10..17 đổi `/metrics`, `/alerts` → `/dashboard/...`. Có cần alias path v1 không? | Không alias (v2 viết lại, DEC-124); cập nhật test 14 theo path mới | 14, frontend |
| OQ-02 | `NFR-12`, `NFR-14`, `NFR-19` được trích từ A-EMS; số NFR chính thức do 07 cấp | 07 giữ đúng số A-EMS (NFR-01..20) để khớp | 07 |
| OQ-03 | `CLAUDE.md` yêu cầu `Depends(require_role(...))` và HS256/"NextAuth + JWT"; v2 dùng `require_permission` + RS256 (DEC-129, DEC-128) | Implement `require_permission`, giữ `require_role` làm alias; human cập nhật `CLAUDE.md` | CLAUDE.md, T-008 |
| OQ-04 | CEO tạo user (FR-AUTH-05, `platform:admin ◑u`) có được gán role ADMIN không? | Không — chỉ ADMIN gán ADMIN | 02 §5.3 |
| OQ-05 | Endpoint Briefing (EP-10) cho MANAGER/EMPLOYEE (không có `dashboard:read`) — permission `authenticated` + cắt khối theo permission | Giữ như §3.2 | 02, 03 §10 |
| OQ-06 | PIL-O gồm HR (EP-80) + Execution (EP-49): hai endpoint cho một trụ; trạng thái trụ ghép ở frontend | Giữ hai endpoint (cô lập lỗi) | 03 §9, 06 |
| OQ-07 | Envelope event thêm `correlation_id`, `producer` ngoài 5 field DEC-126 | Optional, consumer không phụ thuộc; xác nhận bằng DEC | 05 §5.3, 07 |
| OQ-08 | Module `execution` (meeting, decision, task, project, OKR, KPI, check-in) chưa có `FR-EXE-*` trong 00 §4 (FR area chỉ gồm `AUTH, FIN, SAL, HR, PRD, RSK, AI, DSH, NTF, DC`) | Truy vết qua US-DC-004/005, US-MGR-02, US-EMP-03, UC-06; đề xuất thêm area `EXE` | 00, 03, 14 |
| OQ-09 | Danh mục `TOOL-*` (§7) — tên tool mới ngoài 13 function A-EMS (VD `TOOL-create_task`, `TOOL-search_documents`, `TOOL-get_runway_what_if`) | File này là owner `TOOL-*` (00 §4); xác nhận ở review Phase 3 | 02 §7.2, 14 |
| OQ-10 | Upload limit `MAX_FILE_SIZE_MB` v1 = 20, v2 = 50 MB / 300 trang / 100 file (04 §15.1) | Theo 04; cập nhật `.env.example` (T-014) | 07, `.env.example` |
| OQ-11 | Thêm mã lỗi `REFRESH_TOKEN_INVALID`, `MALWARE_DETECTED`, `BAD_REQUEST`, `INVALID_CREDENTIALS` ngoài danh sách nhiệm vụ | Giữ (cần cho FR-AUTH-02, FR-DC-02) | 14 |
| OQ-12 | 04 §15.2 dùng `CONFLICT` cho xung đột commit; file này dùng `CONFLICT_STATE` | Dùng `CONFLICT_STATE`; human sửa 04 | 04 |
| OQ-13 | Thư viện SSE (`sse-starlette` hay `StreamingResponse` thuần) | `StreamingResponse` thuần — không thêm dependency; nếu cần `sse-starlette` → DEC (T-002) | 07 |
| OQ-14 | Email notification (FR-NTF-02) cần SMTP provider | Tắt mặc định (`NOTIFY_EMAIL_ENABLED=false`); log thay gửi | 07 |
| OQ-15 | ~~`FR-AI-01..10` được 09/14 trích dẫn nhưng **chưa có bảng định nghĩa** ở 02/03 (00 §4 có area `AI`). File này dùng nghĩa suy từ 09: 01..04 chat/SSE/tool executor/nguồn, 05..06 hội thoại + feedback, 07 insight, 08 hành động AI (giả định), 09 what-if runway, 10 PII filter~~ **Đã xử lý 2026-10-19:** FR-AI-01..10 được định nghĩa ở 03 §6.8, khớp nghĩa dùng trong file này (FR-AI-08 = hành động AI L1–L3) | Human/owner 02 bổ sung bảng FR-AI; xác nhận FR-AI-08 | 02, 09, 14 |

---

## 11. Liên kết

| Nội dung | File |
|---|---|
| Role, permission, scope, tool filter | `02-PERSONAS-PERMISSIONS.md` §5–§7 |
| Metric, alert, trạng thái trụ, BR, FR domain | `03-DASHBOARD-SPEC.md` |
| Pipeline IDP, state machine, Action Registry `ACT-*`, autonomy | `04-IDP-FEATURE-SPEC.md` |
| Bảng/cột/enum, outbox, payload event | `05-DATA-MODEL.md` |
| Màn hình `SCR-*`, component AI | `06-UI-UX-SPEC.md` |
| Kiến trúc, ModelGateway, cấu hình, NFR | `07-TECH-ARCHITECTURE.md` |
| Test case `TC-*` | `14-TEST-TRACEABILITY.md` |

---

## Version

- **Version:** 2.0.0
- **Last updated:** 2026-10-19
- **Applies to:** Aureon v2
- **Maintainer:** @CyEyes
- **Change:** Viết lại toàn bộ theo DEC-124..137: prefix module (DEC-125), envelope + `limit/offset` (DEC-130), RS256 + permission `<domain>:<action>` (DEC-129), 10 role (DEC-128), domain Finance/Sales/HR/Product/Risk/Execution, AI Core (chat SSE, action, policy, kill switch — DEC-131/132/134), Tool Registry, event contract (DEC-126). Bản 1.x (35 endpoint) lưu ở nhánh `v1`.
