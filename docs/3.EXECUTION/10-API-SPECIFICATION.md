# 10 — API & Tool Registry Spec (Aureon v3 — AI-EOS)

> **Nguồn chuẩn:** `_reference/SOURCE-BRD-v1.1.md` §11 (AI Platform: §11.1 thành phần, §11.2 Tool Registry + 13 metadata, §11.3 phân loại tool, §11.4 agent, §11.5 luồng + quyền, §11.6 Autonomy, §11.7 chất lượng/grounding), §6.10 (tool IDP, D03), §12 (D27 CEO Assistant, D28 Reporting), §13.1 FR-DATA-04/05 (lineage + event backbone), §16 NFR-INT-01. Bổ sung: `SOURCE-BRD-v1.1-Bổ sung.md` §3.9 (tool/entity/agent), grounding. UI: `SOURCE-UIUX.md`.
> **Phụ thuộc:** 00, 01, 02, 05, 07. **Trạng thái:** ✅ current — Aureon v3 (AI-EOS) CHÍNH THỨC. **Ngày:** 2026-10-23 · **Maintainer:** @CyEyes (tách từ Aureon v2.1 — nay archived ở docs/_archive/v2.1/)
> **Phạm vi:** đặc tả **CHIỀU CONTRACT MỨC KHÁI NIỆM** cho P0 — tool (13 metadata), 4 phân loại + quy tắc quyền/approval, danh mục tool theo domain P0, envelope + danh mục event P0, grounding contract (SourceRef). **Không** sinh EP-*/endpoint path cụ thể, **không** field-level DB, **không** T-*/TC-* — hoãn sang đợt code (R-DEC-09); EP-* cụ thể gán theo domain P0 ở đợt sau (R-DEC-10).

---

## 1. Nguyên tắc API (P02 API First)

Mọi năng lực nghiệp vụ expose qua **API + tool**; UI dùng chính các API này (P02). API **có phiên bản** (`/api/v1/...`) + **webhook cho event** (NFR-INT-01). AI gọi nghiệp vụ **chỉ qua tool đã đăng ký** (AI-R02), **không** truy cập DB trực tiếp (07 §1); mọi tool call được authorize trước khi chạy (AI-R08) và ghi audit (AI-R07).

Bốn ràng buộc nền tảng áp cho toàn bộ contract P0:

- **P06 Traceability:** mọi response ghi `X-Request-Id`; giá trị này đi theo log, audit, và `correlation_id` của event phát ra trong cùng request.
- **P04 Human in the Loop:** tool WRITE/APPROVAL/EXECUTION tuân Autonomy Level (§5) + Approval Matrix (02); AI không vượt quyền người được phục vụ (§4.4).
- **P05 Everything Actionable + grounding:** mọi con số AI trả về phải truy nguyên một `tool_result`/`MetricValue` qua `SourceRef` (§8); không có nguồn → chặn hoặc gắn nhãn "ước tính" (FR-AIQ-01).
- **P08 Security by Design:** default deny; permission `<domain>:<action>`; dữ liệu nhạy cảm (lương, số tài khoản, CCCD, MST) lọc trước khi vào model (06.9 BRD, 02).

> §1.1–§1.3 (envelope, phân trang, header/idempotency) giữ ở dạng quy ước gộp tại **§10**; §1.4 tách riêng vì là bảng được contract test (TC-SYS-003) đọc trực tiếp.

### 1.4. Bảng mã lỗi

**Nguồn sự thật = code** (R-DEC-18): lớp lỗi trong `apps/api/src/app/core/errors.py`, `AI_ERROR_CODES`, và `core/handlers._HTTP_CODES`. Bảng dưới **phản chiếu** code; contract test `tests/contract/test_api_contract.py` đối chiếu hai chiều (mọi mã trong code phải có ở đây với đúng HTTP status, và `AI_*` khớp 1-1). Thêm mã mới = sửa code + bảng này trong cùng commit, qua bước Spec lock (R-DEC-15).

| HTTP | `error.code` | Ý nghĩa | Ví dụ |
|---|---|---|---|
| 400 | `BAD_REQUEST` | Tham số sai cú pháp; thiếu `Idempotency-Key` ở POST bắt buộc; method không hỗ trợ | `period=2026-13`; `limit > 100` |
| 401 | `UNAUTHENTICATED` | Thiếu/sai/hết hạn access token | Thiếu header `Authorization` |
| 401 | `INVALID_CREDENTIALS` | Sai email/mật khẩu (không tiết lộ email tồn tại) | `POST /auth/login` |
| 401 | `REFRESH_TOKEN_INVALID` | Refresh token sai, hết hạn, đã thu hồi hoặc bị tái sử dụng (thu hồi cả chuỗi) | `POST /auth/refresh` |
| 403 | `FORBIDDEN_ROLE` | Thiếu permission `<domain>:<action>` của endpoint | ROLE-EMP gọi endpoint `finance:write` |
| 403 | `FORBIDDEN_SCOPE` | Tài nguyên ngoài phạm vi dữ liệu (khối `scope_pillars`, đơn vị, chủ sở hữu, tenant) | Finance-DIR ghi bản ghi sales; ROLE-MGR xem team khác |
| 403 | `FORBIDDEN_SALARY` | Field/tài liệu mức 4 (lương, CCCD, số tài khoản…) với role không được phép (02) | ROLE-MGR mở lịch sử lương |
| 404 | `NOT_FOUND` | Không tồn tại, đã soft delete, khác tenant, hoặc endpoint demo khi `DEMO_MODE=false` | role switch demo khi tắt demo |
| 409 | `CONFLICT_STATE` | Chuyển trạng thái không hợp lệ theo state machine | Approve tài liệu đã `COMMITTED` |
| 409 | `DUPLICATE_RESOURCE` | Vi phạm ràng buộc duy nhất nghiệp vụ | Trùng số hóa đơn, trùng mã phòng ban |
| 409 | `IDEMPOTENCY_CONFLICT` | Cùng `Idempotency-Key` nhưng body khác | §10 |
| 409 | `REVIEW_LOCKED` | Tài liệu đang được người khác review (khóa mềm 15 phút) | `details.locked_by`, `details.locked_until` |
| 410 | `UNDO_EXPIRED` | Quá hạn hoàn tác (7 ngày IDP / 24 giờ AI L3 — DEC-134) | Undo commit tài liệu sau 7 ngày |
| 413 | `FILE_TOO_LARGE` | Vượt `IDP_MAX_FILE_SIZE_MB` / số trang / số file mỗi lần tải | Upload 60 MB |
| 415 | `UNSUPPORTED_MEDIA_TYPE` | Định dạng không hỗ trợ (whitelist MIME + magic bytes) | `.zip` (DEC-051) |
| 422 | `VALIDATION_ERROR` | Body sai schema / định dạng | `details.fields[]` |
| 422 | `BUSINESS_RULE_VIOLATION` | Vi phạm quy tắc nghiệp vụ / FR | `deal_value ≤ 0`; audio `context=meeting` ở C2 (R-DEC-22) |
| 422 | `ACTION_REJECTED` | Action Registry / Autonomy Policy từ chối | `details.action_name`, `details.reason` |
| 422 | `AI_CONTEXT_TOO_LARGE` | Vượt context model sau khi đã chunk | Chat với tài liệu quá dài |
| 423 | `AI_DISABLED` | Kill switch chế độ `L0` hoặc AI tắt — thao tác cần AI bị chặn | Trích xuất khi kill switch L0 |
| 429 | `RATE_LIMIT_EXCEEDED` | Vượt giới hạn tần suất (header `Retry-After`) | > 20 request AI/phút/người |
| 429 | `AI_QUOTA_EXCEEDED` | Provider hết hạn mức **hoặc** vượt `AI_MONTHLY_BUDGET_USD` | Chat khi ngân sách tháng đã hết |
| 500 | `INTERNAL_ERROR` | Lỗi không mong đợi (không lộ stack trace) | — |
| 502 | `AI_PROVIDER_ERROR` | Mọi provider trong chuỗi fallback trả lỗi | Chat |
| 502 | `AI_FUNCTION_CALL_FAILED` | Tool nội bộ lỗi và không thể trả lời từng phần | Chat |
| 503 | `DEPENDENCY_UNAVAILABLE` | DB/Redis/MinIO/ClamAV/ModelGateway/Calendar provider không sẵn sàng | Health `degraded` |
| 504 | `AI_PROVIDER_TIMEOUT` | Hết 30 giây/lượt | Chat |

- `AI_NO_DATA_AVAILABLE` **không** phải lỗi HTTP: AI trả 200 kèm `warnings: ["AI_NO_DATA_AVAILABLE"]` — nói rõ thiếu dữ liệu, không bịa số (P05, §8).
- Mã nội bộ không phải `error.code` HTTP: `IDP-E01..E11` (04, ở `extraction_jobs.error_code` / `details.idp_error_code`); `CLASSIFICATION_SECRET` (ModelGateway từ chối gửi dữ liệu Secret tới LLM — ghi ở `ModelCallLog.error_code`).
- `RATE_LIMITED` (v1) đã thay bằng `RATE_LIMIT_EXCEEDED` (DEC-130); `FORBIDDEN` trần không dùng.

## 2. Tool Registry (BRD §11.2)

Tool Registry là danh mục trung tâm: mọi năng lực nghiệp vụ (đọc, ghi, phê duyệt, tác động ngoài) đều được expose dưới dạng **tool** có schema, quyền và risk level. AI chỉ "nhìn thấy" và gọi được tool trong registry; không có tool ngoài registry nào được thực thi (AI-R02). Danh mục mẫu từ BRD §11.2:

```text
get_financial_summary()      get_sales_pipeline()        get_employee_workload()
get_department_performance() get_kpi_status()            get_okr_status()
get_project_status()         get_overdue_tasks()         get_customer_health()
get_health_metrics()         search_documents()          get_source_document()
create_task()                assign_task()               update_task()
record_kpi_measurement()     create_calendar_event()     send_notification()
upload_document()            extract_document()          commit_extraction()
generate_report()            request_approval()          log_decision()
```

> **Đặt tên (R-DEC-10):** dùng tên BRD snake_case (vd. `get_kpi_status`) + giữ **bảng ánh xạ** sang `TOOL-*` registry của `main` (43 tool) để truy nguyên. `TOOL-*` cụ thể gán ở đợt code; registry này chốt **tên + mục đích + loại + quyền + autonomy** mức khái niệm.

### 2.1. Metadata bắt buộc mỗi tool (13 thuộc tính)

Mọi tool trong registry phải khai đủ 13 thuộc tính sau (BRD §11.2); thiếu bất kỳ thuộc tính nào → tool không được đăng ký:

| # | Thuộc tính | Ý nghĩa (mức contract) |
|---|---|---|
| 1 | `name` | Định danh snake_case, duy nhất trong registry; AI tham chiếu qua tên này. |
| 2 | `description` | Mô tả ngắn mục đích + khi nào dùng; Orchestrator dựa vào đây để chọn tool theo ý định (§4). |
| 3 | `input_schema` | JSON schema tham số đầu vào; validate trước khi gọi, sai schema → từ chối (không gọi). |
| 4 | `output_schema` | JSON schema kết quả; dùng để validate `tool_result` và nối `SourceRef` (§8). |
| 5 | `permission` | Permission `<domain>:<action>` cần có; kiểm theo quyền **hiệu lực = agent ∩ người** (§4.4). |
| 6 | `risk_level` | Mức rủi ro (thấp/trung bình/cao) — quyết định ngưỡng approval + Autonomy mặc định. |
| 7 | `data_scope` | Phạm vi dữ liệu tool chạm (cá nhân / team / phòng ban / toàn DN); lọc theo scope người gọi. |
| 8 | `data_classification` | Mức phân loại dữ liệu (Public/Internal/Confidential/Mật) → chọn nơi xử lý model (07). |
| 9 | `autonomy_level` mặc định | L0–L3 mặc định cho tool (L4 khóa ở MVP); có thể hạ theo kill switch (§5). |
| 10 | `approval_required` | Có cần phê duyệt trước khi thực thi không, theo Approval Matrix (02). |
| 11 | `reversible` | Hành động có hoàn tác được không → quyết định undo window (≥24h) và được phép L3 hay không. |
| 12 | `audit_required` | Luôn `true` cho WRITE/APPROVAL/EXECUTION; ghi `AIToolCall`/audit trong cùng transaction. |
| 13 | `cost_estimate` | Ước tính chi phí AI/hạ tầng mỗi lần gọi; vào ngân sách AI (FR-AIQ-05) + báo cáo chi phí/quyết định. |
| — | `owner` | (thuộc tính thứ 13 theo BRD — chủ domain chịu trách nhiệm tool; duyệt khi nâng Autonomy §5). |

> BRD liệt kê 13 thuộc tính: `name, description, input_schema, output_schema, permission, risk_level, data_scope, data_classification, autonomy_level, approval_required, reversible, audit_required, cost_estimate, owner` — bảng trên giữ nguyên danh sách này (`owner` là thuộc tính cuối). Kiểu/định dạng từng thuộc tính chi tiết hóa ở đợt code (R-DEC-09).

## 3. Phân loại tool + quy tắc quyền/approval (BRD §11.3)

Mỗi tool thuộc đúng một trong 4 loại; loại quyết định quy tắc quyền, Autonomy mặc định và approval:

| Loại | Ý nghĩa | Ví dụ | Autonomy mặc định | Quy tắc quyền / approval |
|---|---|---|---|---|
| READ | Không thay đổi dữ liệu | `get_sales_pipeline`, `get_kpi_status`, `extract_document` | L0 | Cần `<domain>:read`; không approval; trả theo data_scope + che dữ liệu nhạy cảm; luôn qua quyền người hỏi. |
| WRITE | Thay đổi dữ liệu nội bộ | `create_task`, `update_task`, `commit_extraction`, `record_kpi_measurement` | L2 hoặc L3 theo tool × role × ngưỡng giá trị | Cần `ai:write` **và** `<domain>:write`; `audit_required=true`; L3 chỉ khi `reversible=true` + trong policy, có undo ≥24h; vượt ngưỡng giá trị → L2 + duyệt. |
| APPROVAL | Thực hiện quyền phê duyệt | `approve_budget`, `approve_hiring`, `approve_extraction` | — (**AI không được tự gọi**) | AI **không bao giờ** tự gọi; chỉ con người có quyền phê duyệt gọi; AI chỉ `request_approval` tạo yêu cầu chờ người duyệt. |
| EXECUTION | Tác động ra ngoài tổ chức | `send_email`, `send_customer_message`, `create_calendar_event` (khách mời ngoài) | L2 (Draft & Confirm) | Mặc định cần người xác nhận (L2) do tác động ra ngoài; kill switch tắt toàn bộ WRITE/EXECUTION của AI (FR-ADM-07). |

**Quy tắc chung (BRD §11.3 + §11.5, 07 §3):**

- Tool ghi kiểm **cả quyền agent ∩ quyền người** (§4.4) — giao của hai tập, không phải hợp.
- `commit_extraction` là WRITE nhưng **kế thừa `risk_level` của tool đích** (ghi hóa đơn rủi ro cao hơn ghi task) → quyết định approval/Autonomy theo tool đích.
- Trường trọng yếu (số tiền, số tài khoản, MST, lương, giá trị hợp đồng) → luôn qua người (FR-DC-16), WRITE không tự chạy L3.
- Nội dung tài liệu / email / web là **data**, không phải lệnh — không kích hoạt tool (FR-AIQ-06; "duyệt thanh toán ngay" trong hóa đơn không gọi `approve_budget`).

## 4. Agent & Orchestrator (BRD §11.1, §11.4, §11.5)

### 4.1. Thành phần AI Platform (contract liên quan API/tool)

AI Platform gồm 13 thành phần (BRD §11.1; `AIC-*` gán ở 07). Những thành phần chạm contract tool/API: **AI Gateway** (điểm vào duy nhất — xác thực, rate limit, ngân sách, lọc dữ liệu nhạy cảm), **Orchestrator** (hiểu ý định → chọn agent), **Tool Registry** (§2), **Policy Engine** (đánh giá quyền/scope/Autonomy mỗi tool call — AI-R08), **Approval Engine** (`request_approval`), **Audit Engine** (ghi bất biến mọi tool call — AI-R07), **Event Listener** (nghe event backbone §8 để AI Observe). Chi tiết thành phần ở 07.

### 4.2. Agent P0 (BRD §11.4)

| Agent | Phạm vi | Ưu tiên | Tool chính (mức khái niệm) |
|---|---|---|---|
| CEO Agent | Tổng hợp liên domain, briefing, khuyến nghị chiến lược | P0 | READ liên domain, `generate_report`, `log_decision` |
| Data Capture Agent | Phân loại, trích xuất, kiểm tra, đề xuất ghi (không tự ghi tài chính) | P0 | tool IDP §6 (READ) + `commit_extraction` (đề xuất) |
| Performance Agent | KPI/OKR, check-in, phân tích khoảng cách | P0 | `get_kpi_status`, `get_okr_status`, `record_kpi_measurement` |
| Task Agent | Task, workload, nhắc việc, follow-up | P0 | `create_task`, `assign_task`, `update_task`, `get_overdue_tasks` |
| Meeting Agent | Biên bản, quyết định, action item | P0 | `log_decision`, `create_task`, `send_notification` |
| Reporting Agent | Báo cáo định kỳ / theo yêu cầu | P0 | `generate_report`, READ metric |
| Finance Agent, Sales Agent | Phân tích tài chính, pipeline | P0 Lite / P1 | `get_financial_summary`, `get_sales_pipeline` |

Agent P1/P2 (HR, Product, Engineering, Procurement, Strategy, Risk, Governance) ghi backlog (09). Người dùng chỉ nói chuyện với **một Assistant duy nhất**; Orchestrator quyết định agent nào xử lý.

### 4.3. Luồng thực thi (BRD §11.5)

```text
User / Event → Intent Detection → Context Retrieval → Planning → Tool Selection
→ Authorization (Policy Engine) → Tool Calling → Result Validation → Reasoning
→ Recommendation → Approval (theo Autonomy Level) → Execution → Verification → Audit
```

### 4.4. Quy tắc quyền (BRD §11.5)

- AI **không bao giờ vượt quyền** người được phục vụ: **quyền hiệu lực = giao của quyền agent và quyền người dùng** (P06, AI-R08).
- Ví dụ: CEO AI → Finance READ/WRITE, HR READ, Strategy READ/WRITE; Employee AI → dữ liệu cá nhân READ/WRITE, task team READ, Finance DENY.
- AI chạy theo **event/lịch** (không có người hỏi) dùng **danh tính service của agent** với quyền cấu hình riêng, hẹp nhất có thể (ROLE-AI, 02).
- Lọc tool theo `permissions[]` **trước khi** gửi model; tool chạy in-process qua service layer bằng principal dựng từ danh tính người hỏi — không HTTP loopback, không token hệ thống (07 §3).

## 5. Autonomy & kill switch (BRD §11.6, FR-ADM-07)

Mỗi tool call chịu Autonomy Level cấu hình theo **tool × vai trò × ngưỡng giá trị**:

| Level | Tên | AI được làm gì | Áp cho (contract) |
|---|---|---|---|
| L0 | Inform | Chỉ đọc + trả lời | Mọi tool READ |
| L1 | Suggest | Đề xuất, người tự làm | Phân bổ nguồn lực/nhân sự |
| L2 | Draft & Confirm | AI chuẩn bị, người bấm xác nhận | Ghi dữ liệu tài chính, EXECUTION (giao tiếp ngoài) |
| L3 | Act & Notify | AI tự làm trong policy, báo lại, **undo ≥24h** | Task, lịch, nhắc việc nội bộ (`reversible=true`) |
| L4 | Autonomous | AI tự làm, chỉ audit + báo cáo | **Không bật MVP** (phase 5) |

- Ngưỡng giá trị ví dụ: chi phí < 5 triệu → L3; ≥ 5 triệu → L2 + quản lý duyệt.
- Hành động L3 trở lên có **nút hoàn tác tối thiểu 24 giờ** khi bản chất cho phép (`reversible=true`).
- **Kill switch (FR-ADM-07):** Admin tắt toàn bộ hành động WRITE/EXECUTION của AI (hoặc một agent) bằng một thao tác; khi bật, L3 hạ xuống L2 (buộc người xác nhận), L4 luôn khóa.
- Nâng Autonomy cho một tool cần số liệu chất lượng từ Evaluation Engine + duyệt của Admin và `owner` domain.

## 6. Tool IDP (D03, BRD §6.10 + Bổ sung §3.9)

Domain Data Capture expose 10 tool; IDP **không có tool calling** nội bộ (04 §9) — pipeline gọi tool tuần tự theo state machine `UPLOADED → PROCESSING → EXTRACTED → NEEDS_REVIEW → APPROVED → COMMITTED`.

| Tool | Mục đích (contract) | Loại | Quyền cần |
|---|---|---|---|
| `upload_document` | Nhận file/stream, tạo `SourceDocument`, tiền xử lý (quét mã độc, hash trùng, tách trang) | WRITE | `idp:write` |
| `classify_document` | AI phân loại loại tài liệu (bỏ qua nếu người chọn trước) | READ | `idp:read` |
| `extract_document` | Trích trường/bảng theo Extraction Schema; mỗi field `{value, confidence, source_location}` | READ | `idp:read` |
| `validate_extraction` | Kiểm tra nghiệp vụ (tổng dòng + VAT = tổng; MST; master data; trùng) | READ | `idp:read` |
| `submit_extraction_for_review` | Đẩy vào hàng chờ review (SLA, nhắc việc, escalation) | WRITE | `idp:write` |
| `approve_extraction` | Reviewer duyệt bản trích (quyền phê duyệt) | APPROVAL | `idp:approve` |
| `commit_extraction` | Ghi vào domain đích **qua tool đích** (`create_invoice`, `create_task`...) | WRITE (kế thừa risk tool đích) | `idp:write` + `<domain đích>:write` |
| `import_table` | Import Excel/CSV: map cột, xem trước, ghi dòng hợp lệ, xuất file lỗi | WRITE | `idp:write` |
| `search_documents` | Tìm tài liệu theo quyền (ngữ nghĩa/metadata) | READ | `idp:read` |
| `get_source_document` | Lấy tài liệu gốc + trang nguồn (cho lineage/trích dẫn) | READ | `idp:read` |

- Phân loại: `classify`/`extract`/`validate` = READ; `commit_extraction` = WRITE, **kế thừa `risk_level` tool đích**.
- Ghi vào domain đích **chỉ qua Tool Registry** (FR-DC-17) — áp đủ permission, approval, audit; một transaction / tài liệu; phát `document.committed`.
- Trường trọng yếu + classification < ngưỡng → luôn review (FR-DC-16); undo window IDP cấu hình ở đợt code.

## 7. Endpoint theo domain

API path `/api/v1/<domain>/<resource>`. EP theo domain P0 (D01–D28, phần P0 khóa ở skeleton §12bis): Organization, Admin & Security, Data Capture, Workflow (cơ bản), Notification, Integration Hub (Google/MS), Strategy (cơ bản), KPI, OKR, Performance (check-in), Task/Workload, Meeting (transcript), Calendar, Knowledge, Finance Lite, HR cơ bản, Sales Lite, AI Platform, CEO Assistant, Reporting cơ bản.

> **Khác `main`:** `main` có EP-01..119 cố định cho 11 module. Theo **R-DEC-10**, AI-EOS đánh EP theo BRD (domain P0) format `EP-<DOMAIN>-NN` + giữ **bảng ánh xạ** EP `main` ↔ AI-EOS để truy nguyên; **EP-*/endpoint path cụ thể gán ở đợt code (R-DEC-09)**. Giữ envelope/phân trang/mã lỗi/Idempotency-Key của `main` làm quy ước triển khai (nhất quán, không mâu thuẫn BRD).

### 7.1. Quy ước gán EP đợt code (R-DEC-15, R-DEC-19)

| Domain code | Domain | Module code | Prefix path đề xuất |
|---|---|---|---|
| `ORG` | D01 Organization | `hr` | `/org/*` |
| `ADM` | D02 Admin & Security | `auth`, `platform` | `/auth/*`, `/platform/*` |
| `DC` | D03 Data Capture & IDP | `idp` | `/idp/*`, `/data-capture/*` |
| `WF` | D04 Workflow & Approval (cơ bản) | `platform` | `/workflow/*` |
| `NTF` | D05 Notification | `platform` | `/notifications/*` |
| `INT` | D06 Integration Hub | `platform` | `/integrations/*` |
| `STR` · `KPI` · `OKR` · `PRF` | D07 · D08 · D09 · D10 | `execution` | `/goals/*`, `/kpis/*`, `/objectives/*`, `/key-results/*` |
| `TASK` | D11 Project/Task/Workload | `execution` | `/execution/*`, `/work/*` |
| `MTG` · `CAL` | D12 Meeting · D13 Calendar | `execution` | `/meetings/*`, `/calendar/*` |
| `KNW` | D14 Knowledge | `idp` | `/knowledge/*` |
| `FIN` · `HR` · `SAL` | D15 · D16 · D17 | `finance` · `hr` · `sales` | `/finance/*` · `/hr/*` · `/sales/*` |
| `AI` · `CEO` | D26 AI Platform · D27 CEO Assistant | `ai` | `/ai/*` |
| `RPT` | D28 Reporting | `dashboard`, `platform` | `/reporting/*`, `/dashboard/*` |
| `SYS` | Hệ thống (health, ops) | `core` | `/health` |

- **Mỗi phase**, bước Spec lock thêm một bảng `EP-<DOMAIN>-NN | Method | Path | Permission | Request/Response | Idempotency | EP v2.1` vào §7.2 cho endpoint phase đó chạm tới (mới hoặc giữ từ v2.1). Endpoint chưa có trong §7.2 → không được code.
- **Endpoint v2.1 giữ nguyên path** nếu hành vi khớp; chỉ gán ID mới và ghi cột `EP v2.1`. Đổi path = breaking change → phải ghi lý do ở bảng và sửa FE cùng phase.
- Public chỉ: `GET /health`, `POST /auth/login`, `POST /auth/refresh` (giữ DEC-137, không có `/auth/register`).

### 7.2. Danh mục EP đã chốt (cập nhật theo phase)

> M1.1 (nền build) **không thêm endpoint mới**: mock FE chạy ở BFF Next.js (`API_MODE=mock`), không phải API backend. Endpoint của M1.2 trở đi được thêm vào đây ở bước Spec lock của phase tương ứng (09 §6).

| EP | Method | Path | Permission | EP v2.1 | Ghi chú |
|---|---|---|---|---|---|
| EP-SYS-01 | GET | `/health` | public | EP-01 | |
| EP-ADM-01 | POST | `/auth/login` | public | EP-02 | Credentials → access RS256 + refresh opaque |
| EP-ADM-02 | POST | `/auth/refresh` | public | EP-06 | Xoay vòng; tái sử dụng → thu hồi chuỗi |
| EP-ADM-03 | POST | `/auth/logout` | (token) | EP-07 | |
| EP-ADM-04 | GET | `/auth/me` | (token) | EP-03 | `UserOut` |

## 8. Grounding contract — SourceRef (FR-AIQ-01, AI-R09, FR-DATA-04)

Mọi con số AI đưa ra phải truy nguyên nguồn (P05, P06). Contract mức khái niệm:

- Mỗi `tool_result` số liệu mang một **`SourceRef`** mô tả nguồn: loại nguồn (`tool_call` | `metric` | `document`), định danh (tool name + call id, `Metric` id, hoặc `SourceDocument` + trang/vùng tọa độ), và thời điểm cập nhật (Data Freshness, FR-DATA-03).
- AI chỉ được đưa số khi số đó **khớp** một `tool_result`/`MetricValue` qua `SourceRef`; không khớp → gỡ số + cảnh báo hoặc gắn nhãn "ước tính"; thiếu dữ liệu → trả trạng thái "không có dữ liệu" (không bịa, FR-AIQ-01, AI-R10).
- Tài liệu → lineage: `get_source_document` trả liên kết "Xem tài liệu gốc" + trang nguồn; AI trích dẫn đúng trang (FR-DC-23, FR-DATA-04).
- Confidence: khi chưa đủ dữ liệu hiệu chỉnh, dùng thang **Cao/Trung bình/Thấp** kèm lý do thay vì % (FR-AIQ-03).
- Insight theo cấu trúc 9 phần (BRD §11.8): Observation → Evidence → Impact → Root Cause → Risk → Recommendation → Expected Outcome → Confidence → Action; "Evidence" chính là tập `SourceRef`.

## 9. Event backbone (FR-DATA-05, FR-DATA-04, NFR-INT-01)

Mọi thay đổi nghiệp vụ **phát event** để AI Observe theo thời gian thực (FR-DATA-05, AI-R12); webhook cho event (NFR-INT-01). Event nghiệp vụ phát **trong cùng transaction** với bản ghi (outbox) để không mất khi rollback (quy ước triển khai `main`).

### 9.1. Envelope event

```text
{
  event_id        # định danh duy nhất (dedupe consumer)
  event_type      # vd. invoice.created
  occurred_at     # ISO 8601 UTC
  version         # breaking change → event_type _v2
  correlation_id  # = X-Request-Id của request gốc (P06)
  tenant_id       # tenant phát event (R-DEC-21) — consumer set tenant context từ trường này
  payload         # dữ liệu nghiệp vụ, KHÔNG chứa PII / dữ liệu nhạy cảm
}
```

- **Tenant context (R-DEC-21):** publisher ghi `tenant_id` từ tenant context của request; consumer Celery set `current_tenant` từ envelope trước khi xử lý; event thiếu `tenant_id` → chuyển DLQ (fail closed). Event phát trước R-DEC-21 (không có trường) được coi là tenant mặc định khi relay.

- Consumer dedupe theo `event_id`; không giả định thứ tự; payload không chứa PII (số tài khoản, lương, CCCD) — chỉ mã tham chiếu.
- Metric tính sẵn từ consumer (không tính lúc request); mọi `MetricValue` có `SourceRef`/lineage (§8).

### 9.2. Danh mục event P0 (mức khái niệm)

| Event | Phát khi | Domain nguồn | AI dùng để (Observe) |
|---|---|---|---|
| `invoice.created` | Ghi hóa đơn (qua `commit_extraction`/Finance) | D15 Finance | Cảnh báo dòng tiền, cập nhật metric tài chính |
| `kpi.measured` | Ghi `record_kpi_measurement` | D08 KPI | Cập nhật achievement, trend |
| `kpi.below_threshold` | KPI dưới ngưỡng cảnh báo | D08 KPI | UC-03 KPI underperformance |
| `okr.at_risk` | KR/OKR có rủi ro không đạt | D09 OKR | UC-04 OKR at risk |
| `task.overdue` | Task quá hạn | D11 Task | Nhắc việc, escalation, metric thực thi |
| `document.committed` | `commit_extraction` ghi thành công | D03 IDP | Cập nhật domain đích, lineage |
| `meeting.summarized` | Biên bản họp được tóm tắt | D12 Meeting | UC-02/UC-06 meeting → execution |
| `decision.logged` | Ghi Decision Log (`log_decision`) | D28 Decision Log | Đo North Star, đối chiếu 30/60/90 ngày (FR-DEC-02) |
| `risk.detected` | Rủi ro tự sinh từ event/ngưỡng | D25 Risk (P1) | BO-10 phát hiện rủi ro sớm (backlog phần nâng cao) |

> Danh mục đầy đủ + cặp **publish/consume** chốt khi chi tiết hóa (R-DEC-09); `risk.detected` thuộc D25 (P1) nên chỉ liệt kê, chi tiết ở đợt sau. Tên event giữ convention BRD (`<entity>.<verb>`), ánh xạ sang `EVT-*` của `main` ở đợt code.

## 10. Convention (giữ nhất quán nền `main`, không mâu thuẫn BRD)

Envelope `{data, meta?}` / `{error:{code,message,details}}`; phân trang `limit/offset/sort_by/order` (`meta.pagination = {total, limit, offset, has_next}`); `Idempotency-Key` **bắt buộc** cho POST tạo/hành động + mọi endpoint AI ghi; tiền **BIGINT + currency** (mặc định VND); tỷ lệ hậu tố `_pct` thang 0–100; thời gian ISO 8601 UTC có `Z`; mọi response `X-Request-Id` → log/audit/event `correlation_id` (P06). Mã lỗi: bảng **§1.4** (nguồn sự thật = `core/errors.py`, R-DEC-18).

## Open questions

- OQ-10-01: Tool naming — **ĐÃ CHỐT** (R-DEC-10): tên theo BRD snake_case (vd. `get_kpi_status`) + bảng ánh xạ sang `TOOL-*` registry `main` (43 tool) để truy nguyên.
- OQ-10-02: EP numbering — **ĐÃ CHỐT** (R-DEC-10): đánh số theo BRD (`EP-<DOMAIN>-NN`) + bảng ánh xạ sang EP-xx của `main`; path cụ thể gán ở đợt code (R-DEC-09).
- OQ-10-03: MCP server (FR-INT-04, P1) — ngoài MVP (P1 backlog, R-DEC-05); xác nhận phạm vi khi chi tiết hóa.
- OQ-10-04: Cặp publish/consume đầy đủ cho từng event P0 + ánh xạ `EVT-*` của `main` — hoãn sang đợt code (R-DEC-09); registry §9.2 chốt danh mục + domain nguồn.
- OQ-10-05: Kiểu/định dạng chi tiết 13 metadata tool (vd. enum `risk_level`, đơn vị `cost_estimate`) + danh sách mã lỗi `AI_*` đầy đủ — hoãn sang đợt code (R-DEC-09).
- OQ-10-06: Bảng ánh xạ 24 tool mẫu BRD ↔ 43 `TOOL-*` của `main` (1-1 hay 1-nhiều) — lập ở đợt code cùng Tool Registry chi tiết.

## Version

- **Version:** 1.1.0 (current)
- **Last updated:** 2026-10-23
- **Maintainer:** @CyEyes
- **Change 1.1.0 (human duyệt 2026-10-23 — Spec lock M1.1, R-DEC-15/18/19/21):** thêm §1.4 bảng mã lỗi phản chiếu `core/errors.py` (R-DEC-18; sửa 4 contract test hỏng); thêm `tenant_id` vào envelope event §9.1 + quy tắc tenant context (R-DEC-21); thêm §7.1 quy ước domain code/prefix path `EP-<DOMAIN>-NN` và §7.2 danh mục EP đã chốt (bắt đầu với EP-SYS-01, EP-ADM-01..04 ↔ EP-01/02/06/07/03 v2.1); §10 trỏ mã lỗi về §1.4.
- **Change 1.0.0 (promote):** Promote tài liệu AI-EOS lên CHÍNH THỨC Aureon v3; di chuyển vào vị trí docs chuẩn; v2.1 archived (docs/_archive/v2.1/).
- **Change 0.3.0:** Mở rộng lên **spec-level P0** — giải thích đầy đủ 13 metadata tool (bảng ý nghĩa mức contract); 4 phân loại tool kèm **quy tắc quyền/Autonomy/approval mỗi loại** (§3); thêm Agent & Orchestrator (thành phần AI Platform liên quan contract, agent P0 + tool chính, luồng §11.5, quyền agent ∩ người §4.4); **Autonomy & kill switch** (§5); danh mục **tool IDP** đầy đủ (tên + mục đích + loại + quyền, §6); **grounding contract SourceRef** (§8); **envelope event + danh mục event P0** kèm domain nguồn và mục đích Observe (§9); bổ sung OQ-10-04..06. Giữ R-DEC-09 (không EP-*/field DB/T-*/TC-* chi tiết).
- **Change 0.2.0:** Chốt Q1–Q6 (R-DEC-05..10) — cập nhật trạng thái quyết định, đóng OQ liên quan; phạm vi docs-first P0.
- **Change 0.1.0:** Viết lại 10 theo AI-EOS — API First, Tool Registry + 13 metadata + danh mục mẫu, phân loại READ/WRITE/APPROVAL/EXECUTION, agent BRD §11.4, tool IDP, EP theo 28 domain + ánh xạ `main`, convention giữ nền `main`, event backbone.
