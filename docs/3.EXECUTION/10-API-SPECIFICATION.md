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

### 2.2. Ánh xạ tool BRD ↔ `TOOL-*` (Spec lock M1.6 — đề xuất R-DEC-70, chờ human duyệt)

BRD §11.2 (24 tool) + §6.10 tool IDP (10): quan hệ 1-1 hoặc 1-n; ID `TOOL-<snake>` giữ làm `name` gửi model, `brd_name` truy nguyên tên BRD (R-DEC-70). Danh mục 10 tool mới (43 → 53 `TOOL-*`) và 13 metadata chi tiết ở §7.2.5.

| BRD tool | `TOOL-*` | Ghi chú |
|---|---|---|
| `get_financial_summary` | `get_finance_dashboard` (chính), `get_budget_status`, `get_finance_forecast`, `get_cash_flow_forecast`, `list_expenses`, `list_invoices`, `get_runway_what_if` | 1-n |
| `get_sales_pipeline` | `get_sales_pipeline` (chính), `get_sales_dashboard`, `list_deals` | 1-n |
| `get_employee_workload` | `get_workload` | 1-1 |
| `get_department_performance` | `get_execution_dashboard` (tạm) | thay bằng tool dashboard Department ở M2.1 |
| `get_kpi_status` · `get_okr_status` | `get_kpi_status` · `get_okr_status` (mới), `list_objectives` | 1-1 / 1-n |
| `get_project_status` · `get_overdue_tasks` | mới · mới (`list_tasks` giữ cho lọc tổng quát) | 1-1 |
| `get_customer_health` | — | D18 P1, hoãn |
| `get_health_metrics` | `get_metric`, `list_alerts`, `get_hr_dashboard` | hoàn thiện M2.1 (Metric Store v3) |
| `search_documents` · `get_source_document` | `search_documents` · `get_source_document`, `get_lineage` | 1-1 / 1-n |
| `create_task` · `assign_task` · `update_task` | `create_task` · `assign_task` · `update_task` (mới) | 1-1 |
| `record_kpi_measurement` | `record_kpi_measurement` | 1-1 |
| `create_calendar_event` | `create_meeting` (nội bộ) | lịch ngoài/Google: M3.1 |
| `send_notification` | `send_notification` (EXECUTION) | 1-1 |
| `generate_report` · `request_approval` · `log_decision` | `generate_report` · `request_approval` · `record_decision` | 1-1 |
| `upload_document` | `submit_document` | 1-1 |
| `classify_document`, `extract_document`, `validate_extraction`, `submit_extraction_for_review`, `import_table`, `commit_extraction` | — | **Không** là tool AI: bước pipeline IDP/state machine (04 §9 "IDP không có tool calling"); `commit_extraction` = Action Registry sau review |
| `approve_extraction` | — (EP review người) · `approve_request`/`reject_request` (APPROVAL, không gửi model) | AI không tự gọi APPROVAL |
| (ngoài BRD) | `get_product_dashboard`, `get_product_metrics`, `get_risk_dashboard`, `list_risks`, `run_risk_scenario`, `upsert_risk`, `create_mitigation` | `p1_frozen` (R-DEC-16) |
| (ngoài BRD) | `list_hiring_plans`, `record_expense`, `create_invoice`, `upsert_deal`, `get_org_tree`, `record_kr_checkin`, `upsert_kpi`, `upsert_objective`, `create_department`, `create_team` | tool domain P0 bổ sung |

- Kiểm chéo tự động: test `test_tool_registry_m16.py` đọc `brd_name` của mọi `ToolDef` ⇒ mọi tên BRD P0 có ≥ 1 `TOOL-*` hoặc nằm trong danh sách "không là tool"/"hoãn".

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

> M1.1 (nền build) **không thêm endpoint mới**: mock FE chạy ở BFF Next.js (`API_MODE=mock`), không phải API backend. Endpoint của M1.2 trở đi được thêm vào đây ở bước Spec lock của phase tương ứng (09 §6). M1.2: §7.2.1 · M1.3: §7.2.2 · M1.4: §7.2.3 · M1.5: §7.2.4 · M1.6: §7.2.5.

| EP | Method | Path | Permission | EP v2.1 | Ghi chú |
|---|---|---|---|---|---|
| EP-SYS-01 | GET | `/health` | public | EP-01 | |
| EP-ADM-01 | POST | `/auth/login` | public | EP-02 | Credentials → access RS256 + refresh opaque |
| EP-ADM-02 | POST | `/auth/refresh` | public | EP-06 | Xoay vòng; tái sử dụng → thu hồi chuỗi |
| EP-ADM-03 | POST | `/auth/logout` | (token) | EP-07 | |
| EP-ADM-04 | GET | `/auth/me` | (token) | EP-03 | `UserOut` |

#### 7.2.1. M1.2 — D01 Organization · D02 Admin · D05 Notification (Spec lock M1.2 — đề xuất, chờ human duyệt)

**Quy ước chung M1.2:** envelope/phân trang/mã lỗi theo §10, §1.4 (**không thêm mã lỗi mới**). Mọi `POST` dưới đây bắt buộc `Idempotency-Key` (thiếu → `400 BAD_REQUEST`); `PATCH` nhận `If-Match` hoặc body `version` (lệch → `409 CONFLICT_STATE`, như EP-81/82 v2.1). Mọi mutation ghi `ENT-AuditLog` (`action = <module>.<verb>`) + `ENT-OutboxEvent` (§9.2) **trong cùng transaction**; repository lọc `tenant_id` (R-DEC-21) — bản ghi tenant khác → `404 NOT_FOUND`. Field mức 3/4 trả `{ "masked": true }` theo policy T-615 (05 §2.4). `DELETE` = **archive** (soft delete `deleted_at` + `valid_to`), không xóa cứng (FR-ORG-03) → `204`.

**Prefix (R-DEC-29, đề xuất):** giữ nguyên `/hr/departments`, `/hr/employees` của v2.1 (EP-81/82 — FE SCR-48 + test đang dùng, đổi path = breaking); resource **mới** của D01 dùng `/org/*` theo §7.1. **Quyền cơ cấu (R-DEC-30, đề xuất):** đọc = `hr:read` (có cô lập khối `require_pillar_permission`, như EP-81); ghi cơ cấu = `hr:admin` (CEO, ADM, DIR khối O). POST/PATCH `/hr/departments` đổi `hr:write` → `hr:admin` (tập role là **siêu tập** của trước: DIR-O giữ quyền, thêm CEO/ADM → không breaking với người dùng hiện có).

**Data scope đọc cơ cấu (`hr:read`):** CEO, DIR khối O, ADM (scope mới `s` = **chỉ cơ cấu**, R-DEC-30) → toàn tổ chức; MGR → phòng ban của mình (+ phòng con); EMP, REV → `403 FORBIDDEN_SCOPE` với `/org/tree`, `/org/assignments`; DIR ngoài khối O → `403 FORBIDDEN_ROLE` (pillar, như EP-81). ADM với scope `s` gọi `/hr/employees*`, salary-history, hiring-plans → `403 FORBIDDEN_SCOPE` (02 §2: ADM không đọc bản ghi nghiệp vụ) — chọn nhân viên khi gán dùng `members[]` của EP-ORG-24 (chỉ mã, tên, vị trí). Ghi cơ cấu (`hr:admin`) dùng `require_pillar_permission` (DIR chỉ khối O).

| EP | Method | Path | Permission | EP v2.1 | Ghi chú (request → response) |
|---|---|---|---|---|---|
| EP-ORG-01 | GET | `/org/organizations` | `hr:read` | — | Lọc `q`, `include_archived` (mặc định false); sort `name`/`code` → `OrganizationOut[]` (05 §2.4) + `meta.pagination` |
| EP-ORG-02 | POST | `/org/organizations` | `hr:admin` | — | `{code, name, legal_name?, tax_code?, valid_from?}` → `201 OrganizationOut`. Trùng `code` → `409 DUPLICATE_RESOURCE`. Idempotency-Key. Audit `hr.organization_create`; event `hr.org_structure_changed` |
| EP-ORG-03 | GET | `/org/organizations/{id}` | `hr:read` | — | → `OrganizationOut` |
| EP-ORG-04 | PATCH | `/org/organizations/{id}` | `hr:admin` | — | `{name?, legal_name?, tax_code?, version}` → `OrganizationOut`. Audit `hr.organization_update` |
| EP-ORG-05 | DELETE | `/org/organizations/{id}` | `hr:admin` | — | Archive; còn phòng ban live → `422 BUSINESS_RULE_VIOLATION` (`details.reason=has_live_children`) → `204` |
| EP-ORG-06 | GET | `/hr/departments` | `hr:read` | EP-81 | Giữ path + tham số v2.1 (`parent_id`, sort `name`/`code`); **thêm** lọc `organization_id`, `as_of` (phòng ban hiệu lực tại ngày) → `DepartmentOut[]` (**thêm** `organization_id`, `valid_from`, `valid_to`) |
| EP-ORG-07 | POST | `/hr/departments` | `hr:admin` | EP-81 | Body v2.1 `{name, code, parent_id?, manager_id?}` **+** `organization_id` (bắt buộc), `valid_from?` (mặc định hôm nay) → `201 DepartmentOut`. `parent_id` khác tổ chức / không tồn tại → `422 BUSINESS_RULE_VIOLATION`; trùng `code` → `409 DUPLICATE_RESOURCE`. Permission đổi `hr:write` → `hr:admin` (R-DEC-30). Audit `hr.department_create` |
| EP-ORG-08 | GET | `/hr/departments/{id}` | `hr:read` | EP-81 | → `DepartmentOut` |
| EP-ORG-09 | PATCH | `/hr/departments/{id}` | `hr:admin` | EP-81 | `{name?, code?, parent_id?, manager_id?, version}`; `parent_id` tạo vòng (chính nó/hậu duệ) → `422 BUSINESS_RULE_VIOLATION` (`details.reason=parent_cycle`); `organization_id` không đổi qua PATCH → `DepartmentOut`. Audit `hr.department_update` |
| EP-ORG-10 | DELETE | `/hr/departments/{id}` | `hr:admin` | — | Archive (`deleted_at`, `valid_to = hôm nay`); còn team/phòng con live hoặc phân công hiện hành → `422 BUSINESS_RULE_VIOLATION` → `204`. Audit `hr.department_archive` |
| EP-ORG-11 | GET | `/org/teams` | `hr:read` | — | Lọc `department_id`, `as_of` → `TeamOut[]` |
| EP-ORG-12 | POST | `/org/teams` | `hr:admin` | — | `{department_id, code, name, lead_employee_id?, valid_from?}` → `201 TeamOut`. Idempotency-Key. Audit `hr.team_create` |
| EP-ORG-13 | GET | `/org/teams/{id}` | `hr:read` | — | → `TeamOut` |
| EP-ORG-14 | PATCH | `/org/teams/{id}` | `hr:admin` | — | `{name?, code?, lead_employee_id?, version}` (không đổi `department_id` — tạo team mới) → `TeamOut` |
| EP-ORG-15 | DELETE | `/org/teams/{id}` | `hr:admin` | — | Archive; còn phân công hiện hành → `422` → `204` |
| EP-ORG-16 | GET | `/org/positions` | `hr:read` | — | Lọc `department_id`, `q` → `PositionOut[]` (`headcount_budget`, `filled` = số phân công hiện hành, `vacant`) |
| EP-ORG-17 | POST | `/org/positions` | `hr:admin` | — | `{department_id, code, title, level?, headcount_budget, reports_to_position_id?}` → `201 PositionOut`. Idempotency-Key. Audit `hr.position_create` |
| EP-ORG-18 | GET | `/org/positions/{id}` | `hr:read` | — | → `PositionOut` |
| EP-ORG-19 | PATCH | `/org/positions/{id}` | `hr:admin` | — | `{title?, level?, headcount_budget?, reports_to_position_id?, version}` → `PositionOut` |
| EP-ORG-20 | DELETE | `/org/positions/{id}` | `hr:admin` | — | Archive; còn phân công hiện hành → `422` → `204` |
| EP-ORG-21 | GET | `/org/assignments` | `hr:read` | — | Lọc `employee_id`, `department_id`, `as_of` (hiệu lực tại ngày; bỏ trống = toàn bộ lịch sử); sort `valid_from` → `EmployeeAssignmentOut[]` |
| EP-ORG-22 | POST | `/org/assignments` | `hr:admin` | — | `{employee_id, department_id, team_id?, position_id?, manager_id?, valid_from, reason?}` → `201 EmployeeAssignmentOut`. **Đóng** phân công hiện hành (`valid_to = valid_from` mới) và **mở** bản mới trong một transaction + cập nhật cache `employees.department_id/team_id/position_id/manager_id`. `valid_from` > hôm nay, ≤ `valid_from` của phân công hiện hành, chồng khoảng, `team`/`position` không thuộc `department_id`, `manager_id = employee_id` → `422 BUSINESS_RULE_VIOLATION`. Idempotency-Key. Audit `hr.assignment_create` |
| EP-ORG-23 | PATCH | `/org/assignments/{id}` | `hr:admin` | — | Chỉ sửa `reason`, `manager_id`, `valid_to` (đóng sớm; không tạo chồng/khoảng trống ngược) + `version` → `EmployeeAssignmentOut`. Audit `hr.assignment_update` |
| EP-ORG-24 | GET | `/org/tree` | `hr:read` | — | `as_of=YYYY-MM-DD` (mặc định hôm nay; sai định dạng → `400`), `organization_id?` (mặc định tổ chức đầu tiên). → `OrgTreeOut {as_of, organization, departments[]: {id, code, name, parent_id, manager_id, headcount, teams[]: {id, code, name, lead_employee_id, headcount}, members[]: {employee_id, employee_code, full_name, team_id, position_id, position_title, manager_id}}}` — danh sách phẳng có `parent_id` (FE dựng cây); chỉ phòng ban/team/phân công **hiệu lực tại `as_of`**; `headcount` tính từ phân công. Không chứa field mức 3–4 |
| EP-HR-01 | GET | `/hr/employees` | `hr:read` | EP-82 | Giữ v2.1 (`department_id`, `status`, `q`, scope MGR/EMP/REV như cũ); `EmployeeOut` mask mức 3/4 theo T-615 |
| EP-HR-02 | POST | `/hr/employees` | `hr:write` | EP-82 | Giữ v2.1; **thêm**: tạo phân công đầu tiên `valid_from = hire_date` cùng transaction. Idempotency-Key |
| EP-HR-03 | GET | `/hr/employees/{id}` | `hr:read` | EP-82 | Giữ v2.1 |
| EP-HR-04 | PATCH | `/hr/employees/{id}` | `hr:write` | EP-82 | Giữ v2.1; **thêm** `effective_from?` (mặc định hôm nay): đổi `department_id`/`title`(position)/`manager_id` → đóng + mở phân công như EP-ORG-22 |
| EP-HR-05 | DELETE | `/hr/employees/{id}` | `hr:write` | EP-82 | Giữ v2.1; đóng phân công hiện hành (`valid_to = hôm nay`) |
| EP-ADM-05 | GET | `/platform/users` | `platform:read` | — | Lọc `role_code`, `is_active`, `department_id`, `q` (email/tên); sort `email`/`full_name`/`created_at` → `UserAdminOut[]` `{id, email, full_name, role_id, role_code, scope_pillars[], department_id, employee_id, locale, is_active, is_service_account, last_login_at, locked_until, created_at, updated_at, version}` — **không bao giờ** `password_hash`. Module sở hữu: `auth` (router mount ở `/platform/users`, 07 §1.1) |
| EP-ADM-06 | POST | `/platform/users` | `platform:admin` | — | `{email, full_name, role_code, scope_pillars?, department_id?, employee_id?, locale?, initial_password}` (write-only, argon2id, ≥ 12 ký tự) → `201 UserAdminOut`. `scope_pillars` khác rỗng khi role ≠ DIR, `role_code=AI` không phải service account → `422 BUSINESS_RULE_VIOLATION`; ADM cấp role `CEO` → `403 FORBIDDEN_SCOPE` (R-DEC-36); trùng email/employee_id → `409 DUPLICATE_RESOURCE`. Idempotency-Key. Audit `auth.user_create` (mask `password`); event `auth.user_access_changed` |
| EP-ADM-07 | GET | `/platform/users/{id}` | `platform:read` | — | → `UserAdminOut` |
| EP-ADM-08 | PATCH | `/platform/users/{id}` | `platform:admin` | — | `{full_name?, role_code?, scope_pillars?, department_id?, employee_id?, locale?, version}` → `UserAdminOut`. Đổi `role_code`/`scope_pillars` → **thu hồi mọi refresh token** của user (access token cũ hết hạn ≤ 15 phút); tự đổi role của chính mình → `422`. Không nhận `is_active`/`password` (dùng EP-ADM-09/10). Audit `auth.user_update` |
| EP-ADM-09 | POST | `/platform/users/{id}/deactivate` | `platform:admin` | — | `{reason}` → `200 UserAdminOut` (`is_active=false`); **thu hồi mọi refresh token** (mọi family) → refresh sau đó `401 REFRESH_TOKEN_INVALID`, login `401 INVALID_CREDENTIALS`; tự khóa chính mình → `422 BUSINESS_RULE_VIOLATION`; đã khóa → trả trạng thái hiện tại (idempotent). Idempotency-Key. Audit `auth.user_deactivate` |
| EP-ADM-10 | POST | `/platform/users/{id}/reactivate` | `platform:admin` | — | `{reason}` → `200 UserAdminOut` (`is_active=true`, reset `failed_login_count`, `locked_until`). Idempotency-Key. Audit `auth.user_reactivate`. (Thêm so với 09 T-614 để FE "khóa/mở" — R-DEC-36) |
| EP-ADM-11 | GET | `/platform/roles` | `platform:read` | — | → `RoleOut[]` `{id, code, role_ref, name_vi, name_en, permissions[], scope_rules, pillars[]}` — 7 role, **chỉ đọc** (ma trận = `auth/permission_matrix.py`) |
| EP-ADM-12 | GET | `/platform/audit-logs` | `platform:read` | EP-52 | Giữ path + tham số v2.1 (`action`, `target_type`, `target_id`, `actor_user_id`); **thêm** `from`, `to` (ISO 8601 UTC, lọc `occurred_at`, `from > to` → `400`), `actor_type` ∈ `USER/AI/SYSTEM`; lọc theo tenant; `before`/`after` đã mask → `AuditLogOut[]` |
| EP-NTF-01 | GET | `/notifications` | (token) | — | Chỉ thông báo có `recipient_id = sub` (R-DEC-31). Lọc `unread_only`, `kind`; sort `created_at` desc → `NotificationOut[]` `{id, kind, title, body, link, ref_schema, ref_table, ref_id, read_at, created_at}` + `meta.unread_count` |
| EP-NTF-02 | POST | `/notifications/{id}/read` | (token) | — | → `200 NotificationOut`; đã đọc → giữ `read_at` cũ (idempotent); của người khác / tenant khác → `404 NOT_FOUND`. Idempotency-Key (quy ước POST hành động) |
| EP-NTF-03 | POST | `/notifications/read-all` | (token) | — | `{up_to?}` (mặc định now) → `200 {updated}`; chỉ thông báo của người gọi. Idempotency-Key |
| EP-NTF-04 | GET | `/notifications/preferences` | (token) | — | → `NotificationPreferenceOut[]` `{kind, email_enabled, is_default}` đủ mọi `notification_kind` (dòng chưa lưu = mặc định 05 §2.4) |
| EP-NTF-05 | PATCH | `/notifications/preferences` | (token) | — | `{items: [{kind, email_enabled}]}` → `NotificationPreferenceOut[]`; `kind` lạ → `422 VALIDATION_ERROR`. Upsert theo `(user_id, kind)`. Audit `platform.notification_preference_update` |

- **Mỗi endpoint đúng một permission** trừ EP-NTF-* (`(token)` — dữ liệu của chính người gọi, cùng tiền lệ EP-ADM-03/04; R-DEC-31). Ma trận cần thêm `hr:admin` (CEO, ADM, DIR) và `hr:read` scope `s` cho ADM (R-DEC-30) — sửa `auth/permission_matrix.py` ở bước B.
- **Email (T-616b, R-DEC-20/33):** không có endpoint — job beat `notifications.dispatch_email` quét `email_status=PENDING`, Celery task gửi qua `smtplib`, idempotent theo `notification.id`; nội dung = template theo `kind` + locale + link, **không** chèn `title`/`body`.
- Route path tĩnh (`/notifications/read-all`, `/notifications/preferences`) khai báo trước route có `{id}`.

#### 7.2.2. M1.3 — D11 Project/Task/Workload · D04 Approval cơ bản (Spec lock M1.3 — đề xuất, chờ human duyệt)

**Quy ước chung M1.3:** như §7.2.1 — envelope/phân trang/mã lỗi §10, §1.4 (**không thêm mã lỗi**); mọi `POST` bắt buộc `Idempotency-Key` (thiếu → `400 BAD_REQUEST`); `PATCH` nhận `If-Match` hoặc body `version` (lệch → `409 CONFLICT_STATE`); mọi mutation ghi `ENT-AuditLog` (`execution.<verb>` / `platform.<verb>`) + `ENT-OutboxEvent` (§9.2) **cùng transaction**; repository lọc `tenant_id` (R-DEC-21) — bản ghi tenant khác / ngoài scope đọc → `404 NOT_FOUND` (đọc theo id) hoặc `403 FORBIDDEN_SCOPE` (ghi, như v2.1 `scope.check`). `DELETE` = soft delete (`deleted_at`) → `204`. Ngày `due_date` so theo ngày nghiệp vụ `Asia/Ho_Chi_Minh` (`business_today()`).

**Prefix (R-DEC-39 đã chốt, R-DEC-40 chi tiết):** `/execution/tasks*`, `/execution/projects*` → `/work/*`; milestone theo **project** mở mới ở `/work/projects/{id}/milestones` (route milestone theo initiative `/execution/initiatives/{id}/milestones` **giữ nguyên tới M1.4** — chuyển cùng initiative sang `/goals/*`). `/platform/approvals/{id}/decide` → `/workflow/approval-requests/{id}/decide`. **Không giữ alias path cũ** (không có client ngoài: FE v2.1 không gọi `/execution/tasks`; chỉ test BE + `shared-types` sinh lại). Giữ nguyên ở `/execution/*` tới M2.3: meetings, decisions (EP-42/43); `/execution/dashboard` (EP-49) tới M2.1; objectives/key-results/kpis/check-ins/initiatives tới M1.4.

**Quyền:** không thêm permission/cặp mới. Task/project/milestone đọc = `execution:read`, ghi = `execution:write`; workload = `execution:query` (CEO, DIR, MGR — EMP không có → `403 FORBIDDEN_ROLE`, EMP xem tải của mình qua "Task của tôi"); approval inbox/decide = `platform:approve` (CEO, DIR scope `p`, MGR scope `d`). Project với EMP: thấy dự án mình là `owner_id` hoặc có task `assignee_id` = mình (không có bảng thành viên dự án ở P0). Data scope giữ `execution/services/scope.py` (DEC-220): CEO `●`; DIR/MGR `d` (phòng ban mình + task mình là owner/assignee); EMP `o` (owner/assignee = chính mình, `require_self` khi tạo/giao). "Chính mình" = `employee_id` của người gọi **hoặc** `user_id` (tương thích bản ghi cũ) — R-DEC-41.

| EP | Method | Path | Permission | EP v2.1 | Ghi chú (request → response) |
|---|---|---|---|---|---|
| EP-TASK-01 | GET | `/work/tasks` | `execution:read` | EP-44.L | Giữ lọc v2.1 (`assignee_id`, `owner_id`, `status`, `overdue`, `department_id`, `initiative_id`, `project_id`; sort `due_date/priority/status/updated_at/title`). **Thêm:** `mine=true` (assignee = người gọi — R-DEC-41), `status` lặp nhiều giá trị (kanban), `due_from`/`due_to` (date, `due_from > due_to` → `400`), `parent_task_id`, `source_kind` → `TaskOut[]` |
| EP-TASK-02 | POST | `/work/tasks` | `execution:write` | EP-44.C | `TaskCreate` v2.1 + `parent_task_id?`, `source_ref?` (05 §2.5) → `201 TaskOut`. Giữ luật v2.1 (EMP chỉ giao cho mình; `due_date ≥ start_date`; `blocked` cần `blocked_reason`). `parent_task_id` = chính nó/hậu duệ hoặc cha đã là sub-task → `422 BUSINESS_RULE_VIOLATION` (R-DEC-42). Idempotency-Key. Audit `execution.task_create`; event `execution.task_created`; assignee ≠ người gọi → notification `task_assigned` (R-DEC-46) |
| EP-TASK-03 | GET | `/work/tasks/{id}` | `execution:read` | EP-44.R | → `TaskOut` (+ `parent_task_id`, `source_ref`, `subtask_count`, `depends_on_open: int`) |
| EP-TASK-04 | PATCH | `/work/tasks/{id}` | `execution:write` | EP-44.U | `TaskUpdate` v2.1 + `parent_task_id?`, `source_ref?` + `version` → `TaskOut`. Chuyển trạng thái theo DEC-147 (sai → `409 CONFLICT_STATE`). Sang `done` khi còn dependency chưa `done/cancelled` → `422 BUSINESS_RULE_VIOLATION` `details.rule=FR-TASK-02` (R-DEC-43). Đổi `assignee_id` → notification `task_assigned` cho người mới; sang `done` → event `execution.task_completed`. Đổi `due_date` → re-arm overdue (giữ v2.1). Audit `execution.task_update` |
| EP-TASK-05 | DELETE | `/work/tasks/{id}` | `execution:write` | EP-44.D | Giữ v2.1 (soft delete, recompute initiative progress); xóa kèm dependency của task (soft) → `204`. Task còn sub-task sống → `422` |
| EP-TASK-06 | GET | `/work/tasks/{id}/dependencies` | `execution:read` | — | → `TaskDependenciesOut {depends_on: TaskBriefOut[], blocks: TaskBriefOut[]}`; `TaskBriefOut {dependency_id, task_id, title, status, due_date, overdue, assignee_id}` — task ngoài scope đọc trả `{task_id, restricted: true}` |
| EP-TASK-07 | POST | `/work/tasks/{id}/dependencies` | `execution:write` | — | `{depends_on_task_id, dependency_type?="finish_to_start"}` → `201 TaskDependencyOut`. Tự phụ thuộc / tạo vòng (BFS trong tx, khóa dòng task) → `422 BUSINESS_RULE_VIOLATION` `details.cycle=[ids]`; trùng cặp → `409 DUPLICATE_RESOURCE`; task đích không tồn tại/tenant khác → `404`. Cần quyền ghi task `{id}` + đọc task đích. Idempotency-Key. Audit `execution.task_dependency_create` |
| EP-TASK-08 | DELETE | `/work/tasks/{id}/dependencies/{dependency_id}` | `execution:write` | — | → `204`. Audit `execution.task_dependency_delete` |
| EP-TASK-09 | GET | `/work/projects` | `execution:read` | EP-45.L | Giữ lọc v2.1 (`status`, `department_id`, `owner_id`); **thêm** `late=true`, `initiative_id` → `ProjectOut[]` (+ `initiative_id`) + `progress_pct` (task `done` / tổng task không `cancelled`), `planned_pct` (tuyến tính `start_date→due_date` tại hôm nay), `late` (= `planned_pct − progress_pct > 10` điểm — cùng công thức METRIC-OPS-02, ngưỡng 03 §4 giữ nguyên), `open_tasks`, `overdue_tasks` |
| EP-TASK-10 | POST | `/work/projects` | `execution:write` | EP-45.C | Giữ v2.1 `ProjectCreate` + `initiative_id?` (nullable FK `execution.initiatives`, 05 §2.5; initiative không tồn tại/tenant khác → `422 BUSINESS_RULE_VIOLATION`) → `201 ProjectOut`; trùng `code` → `409 DUPLICATE_RESOURCE`. Idempotency-Key. Audit `execution.project_create` |
| EP-TASK-11 | GET | `/work/projects/{id}` | `execution:read` | EP-45.R | → `ProjectDetailOut` = `ProjectOut` + `milestones: MilestoneOut[]` (sắp `due_date`) + `task_counts {by_status}` |
| EP-TASK-12 | PATCH | `/work/projects/{id}` | `execution:write` | EP-45.U | Giữ v2.1 + `initiative_id?` (gán/bỏ liên kết Initiative → Project, dùng ở EP-STR-22 M1.4) + `version` → `ProjectOut`. Audit `execution.project_update` |
| EP-TASK-13 | DELETE | `/work/projects/{id}` | `execution:write` | EP-45.D | Giữ v2.1 → `204` |
| EP-TASK-14 | GET | `/work/projects/{id}/milestones` | `execution:read` | — (cùng hành vi EP-45 sub-resource theo initiative) | → `MilestoneOut[]` (+ `project_id`, `late` = `status=planned AND due_date < hôm nay`) |
| EP-TASK-15 | POST | `/work/projects/{id}/milestones` | `execution:write` | — | `MilestoneCreate` v2.1 `{title, due_date, status?}` → `201 MilestoneOut` (`project_id` từ path; CK `one_parent` giữ). Idempotency-Key. Audit `execution.milestone_create` |
| EP-TASK-16 | PATCH | `/work/projects/{id}/milestones/{milestone_id}` | `execution:write` | — | `MilestoneUpdate` + `version` → `MilestoneOut`; milestone không thuộc project → `404`. `status=done` set `done_at`. Audit `execution.milestone_update` |
| EP-TASK-17 | DELETE | `/work/projects/{id}/milestones/{milestone_id}` | `execution:write` | — | → `204`; task còn trỏ `milestone_id` → set NULL cùng tx (audit) |
| EP-TASK-18 | GET | `/work/workload` | `execution:query` | (EP-87 dùng cùng service) | `week=YYYY-Www` (ISO; mặc định tuần chứa hôm nay; sai định dạng → `400`), `weeks=1..8` (mặc định 4, lùi từ `week`), `department_id?` (MGR bị ghim phòng mình, khác → `403 FORBIDDEN_SCOPE`) → `WorkloadOut {weeks: ["2026-W40",…], threshold_pct: 110, overload_weeks: 2, capacity_hours: 40, rows: [{employee_id, department_id, cells: [{week, load_pct, hours, open_tasks}], overloaded}], summary: {people, overloaded_count, overloaded_pct}}` — `overloaded` = `load_pct > 110` ở **tuần cuối và tuần liền trước** (giữ `rows_from`, DEC-226); `overloaded_pct` khớp METRIC-HR-03. **Không** trả tên: `hr` đã import `execution` (EP-87) nên `execution → hr` tạo vòng module (test import-boundary) — FE ghép tên/mã từ `members[]` của EP-ORG-24 (`hr:read`, mức 2) (R-DEC-44). `Cache-Control: private, max-age=60` + `Vary: Authorization` |
| EP-WF-01 | GET | `/workflow/approval-requests` | `platform:approve` | EP-123.L | `assigned_to=me` (mặc định; request `PENDING` mà role người gọi nằm trong người duyệt **bước hiện tại** của rule và trong data scope — R-DEC-45), `status?` (mặc định `PENDING`), `rule_code?`, `target_kind?`; sort `due_at`/`created_at` → `ApprovalRequestOut[]` + `meta.pending_count`. Thêm field `title_key`, `params` (i18n, không câu cứng), `requested_by_name`, `overdue` (`due_at < now`). Người yêu cầu không thấy request của chính mình trong `assigned_to=me` |
| EP-WF-02 | GET | `/workflow/approval-requests/{id}` | `platform:approve` | EP-124 | → `ApprovalDetailOut` (có sẵn: `payload_diff`, `timeline`); ngoài scope → `404` |
| EP-WF-03 | POST | `/workflow/approval-requests/{id}/decide` | `platform:approve` | **EP-125** (gán ID) | `DecideIn {decision: approve\|reject, reason?}` → `ApprovalRequestOut`. Giữ nguyên hành vi v2.1: không `PENDING`/hết hạn → `409 CONFLICT_STATE`; người duyệt = người yêu cầu, bước 2 trùng bước 1, `reject` thiếu `reason` → `422 BUSINESS_RULE_VIOLATION`; role không thuộc bước → `403 FORBIDDEN_ROLE`; ngoài scope → `403 FORBIDDEN_SCOPE`. Duyệt cuối → hook theo `target_kind` (`ai_action` v2.1, `task_reassign` mới — R-DEC-45) cùng tx. Idempotency-Key. Audit `platform.approval_decided`; event `platform.approval_decided`; notification `approval_decided` cho người yêu cầu |

- **Không có endpoint tạo approval riêng ở M1.3:** request sinh bởi service (AI action L2 tài chính v2.1; `TOOL-assign_task` chuyển task giữa người do AI đề xuất → rule `RULE-task_reassign` — R-DEC-45). `POST /workflow/approval-requests` (EP-123.C) **hoãn M3.2** (Workflow cấu hình).
- **AI tool registry** (`ai/tools/registry.py`, chỉ đổi chuỗi `endpoint`, không thêm tool): `TOOL-list_tasks` → `EP-TASK-01`, `TOOL-create_task` → `EP-TASK-02 / ACT-create_task`, `TOOL-assign_task` → `EP-TASK-04`, `TOOL-approve_request`/`TOOL-reject_request` → `EP-WF-03`, `TOOL-request_approval` giữ `EP-123.C` (hoãn). `TOOL-get_workload` giữ EP-87 (`hr:query`) — không đổi quyền tool ở M1.3.
- **Route tĩnh trước route `{id}`**: `/work/workload` tách router; `/work/tasks/{id}/dependencies` khai báo trước catch-all.
- **File phải sửa do đổi path (R-DEC-40):** BE `modules/execution/routes/router.py` (tách `routes/work.py` mount `/work`), `modules/platform/routes/router.py` (bỏ `/platform/approvals/{id}/decide`, thêm `routes/workflow.py` mount `/workflow`), `ai/tools/registry.py`, `ai/services/action_service.py:146` (docstring EP-125→EP-WF-03); test `tests/integration/execution/{helpers.py,test_tasks.py,test_meetings_projects.py,test_dashboard.py,test_initiatives.py,test_metrics_provider.py,test_okr_kpi.py,test_workload.py}` (URL `/execution/tasks|projects` → `/work/*`), `tests/integration/ai/test_ai_e2e.py:468`, `tests/integration/ai/test_action_service.py` (nếu gọi HTTP), contract snapshot `tests/contract/*`; `packages/shared-types/src/generated.ts` (sinh lại). FE: `apps/web/src/mocks/router.ts` (+ file mới `mocks/work.ts`, `mocks/workflow.ts`), `src/mocks/admin.ts:164-165` (link giữ `/work`, `/work/approvals`), `src/lib/permissions.ts` (+ route con `/work/projects`, `/work/workload`), `src/lib/permissions.test.ts`, `src/lib/query-keys.ts`, `src/app/(app)/work/**`, `e2e/roles.spec.ts:113-135` (SCR-43 không còn `coming-soon`), `e2e/navigation.spec.ts` (giữ redirect `/approvals → /work/approvals`). `legacy-routes.ts`/`middleware.ts` không đổi.
- **EP-TASK-19 (mới, R-DEC-45) — `POST /work/tasks/{id}/reassign-requests` · `execution:write` · EP v2.1 —:** `{to_assignee_id, reason}` (reason 1..500) → `201 ApprovalRequestOut` (rule `RULE-task_reassign`, `target_kind=task_reassign`, `department_id` = phòng của task). Dùng khi người gọi **không** được tự giao lại (EMP với task của mình — 02 §7 "Chuyển task giữa người → Manager"); MGR/DIR/CEO trong scope PATCH trực tiếp EP-TASK-04 (gọi endpoint này → `422 BUSINESS_RULE_VIOLATION` `details.reason=direct_reassign_allowed`). Đã có request `PENDING` cho task → `409 CONFLICT_STATE`. Task `done/cancelled` → `409`. Idempotency-Key. Audit `platform.approval_requested`; event `platform.approval_requested`; notification `approval_requested` cho MGR phòng ban (fallback DIR theo `escalate_to_role_code`).
- **Hook duyệt** `task_reassign` (đăng ký từ `execution` vào `core/approval_hooks.py`, như `ai_action`): APPROVED → `TaskService.reassign(approver, task_id, to_assignee_id, expected_version=payload.version)` cùng tx; task đã đổi version từ lúc yêu cầu → `409 CONFLICT_STATE` (request giữ `PENDING`, rollback); thành công → notification `task_assigned` cho người nhận + `approval_decided` cho người yêu cầu.
#### 7.2.3. M1.4 — D07 Strategy · D08 KPI · D09 OKR · D10 Performance (Spec lock M1.4 — đề xuất, chờ human duyệt)

**Quy ước chung M1.4:** như §7.2.1 (envelope/phân trang/mã lỗi §1.4 — **không thêm mã lỗi**). Mọi `POST` bắt buộc `Idempotency-Key` (thiếu → `400 BAD_REQUEST`; trùng key khác body → `409 IDEMPOTENCY_CONFLICT`); `PATCH` nhận `If-Match` hoặc body `version` (lệch → `409 CONFLICT_STATE`). Mọi mutation ghi `ENT-AuditLog` (`action = execution.<verb>`) + outbox (§9.2) trong **cùng transaction**; repository lọc `tenant_id` (bản ghi tenant khác → `404`). `DELETE` = soft delete (`deleted_at`) → `204`. Module code `execution` (schema `execution`), tách router thành `routes/goals.py` (STR), `routes/kpis.py` (KPI + PRF KPI), `routes/okr.py` (OKR + PRF KR). Số đo `numeric(20,6)` trả `float`; tỷ lệ `_pct` 0–100.

**Path (R-DEC-39 + R-DEC-58):** gỡ hẳn `/execution/{kpis,objectives,key-results,check-ins,initiatives}` (kể cả `/execution/initiatives/{id}/milestones`) — không alias. KR phẳng hóa: `/execution/objectives/{oid}/key-results/{kr}` → `/key-results/{kr}` (tạo/list vẫn lồng dưới objective). Check-in tách theo đích: KR `/key-results/{id}/check-ins`, KPI `/kpis/{id}/check-ins`; feed tổng hợp `/goals/check-ins`.

**Quyền & data scope (R-DEC-57):** permission giữ `execution:read` (GET) / `execution:write` (ghi) — **không** cấp permission mới. Scope mục tiêu tách thành `execution/services/goal_scope.py` (không đổi `scope.py` mà task M1.3 đang dùng):

| Role | Đọc (STR/KPI/OKR/PRF) | Ghi Strategy / StrategicObjective | Ghi KPI / Objective / KR / Initiative | Check-in (EP-PRF-02/04) |
|---|---|---|---|---|
| CEO | toàn bộ | có | toàn bộ | mọi KR/KPI |
| DIR | **khối** = cây phòng ban của mình (phòng + phòng con, qua `core/org_scope.py` `department_subtree()` — `hr` đăng ký provider từ `StructureService.subtree_ids` public, tránh vòng `execution → hr`) ∪ bản ghi có `pillar ∈ scope_pillars` ∪ bản ghi mình sở hữu ∪ cấp công ty (`department_id IS NULL`, chỉ đọc); `scope_pillars` rỗng → toàn bộ | chỉ StrategicObjective có `pillar ∈ scope_pillars` (Strategy: không) → `403 FORBIDDEN_SCOPE`/`FORBIDDEN_ROLE` | trong khối (`pin_department` theo cây con) | KR/KPI trong khối (ghi hộ, `user_id` = người gọi) |
| MGR | **team** = phòng ban của mình + phòng con ∪ của mình ∪ cấp công ty (chỉ đọc) | không → `403 FORBIDDEN_ROLE` | trong phòng ban | KR/KPI trong phòng ban |
| EMP | của mình (`owner_id = Principal.user_id` — `owner_id` KPI/OKR giữ ngữ nghĩa `auth.users.id`, R-DEC-41) + **tổ tiên** của chúng trong cây (node rút gọn `restricted: true`, chỉ `id`, `code`/`title`) | không → `403 FORBIDDEN_ROLE` | không tạo Objective/KPI/Initiative (→ `403 FORBIDDEN_ROLE`); không sửa | **chỉ** KR/KPI có `owner_id = Principal.user_id`; khác → `403 FORBIDDEN_SCOPE` |
| REV, ADM | không có `execution:*` → `403 FORBIDDEN_ROLE` (như v2.1) | — | — | — |
| AI | chỉ qua tool, quyền = người được phục vụ (P06); M1.4 không thêm tool | — | — | — |

Bản ghi ngoài scope ở GET chi tiết → `403 FORBIDDEN_SCOPE` (giữ v2.1); ở list/tree → loại khỏi kết quả.

| EP | Method | Path | Permission | EP v2.1 | Ghi chú (request → response) |
|---|---|---|---|---|---|
| EP-STR-01 | GET | `/goals/tree` | `execution:read` | — | Mới. Query `strategy_id?`, `period_key?` (kỳ OKR, mặc định quý hiện tại theo `business_today`), `department_id?` (trong scope). → `GoalTreeOut {strategies:[StrategyNode{…, strategic_objectives:[SONode{id, code, title, pillar, owner_id, department_id, progress_pct, status, kpis:[KpiNode{id, code, name, unit, direction, owner_id, department_id, latest_evaluation: KpiEvaluationBrief\|null, children:[KpiNode]}], objectives:[ObjNode{id, title, period_key, level, status, progress_pct, owner_id, department_id, at_risk_kr_count, key_results:[KrNode{id, title, unit, baseline, target, current_value, progress_pct, confidence, at_risk, last_checked_in_at, owner_id}], children:[ObjNode]}], initiatives:[IniNode{id, code, title, status, progress_pct, start_date, planned_end_date, on_track, projects:[{id, code, name, status}]}]}]}], unaligned:{kpis:[KpiNode], objectives:[ObjNode]}}`. Node tổ tiên ngoài scope: `{id, code?, title?, restricted:true}`. Chỉ đọc cột tính sẵn (không tính metric lúc request); `on_track` = cùng quy tắc SEI (05 §2.6). Không phân trang; độ sâu KPI/Objective tối đa 5 |
| EP-STR-02 | GET | `/goals/strategies` | `execution:read` | — | Lọc `status?`; sort `code`/`period_start` → `StrategyOut[]` + `meta.pagination` |
| EP-STR-03 | POST | `/goals/strategies` | `execution:write` (CEO) | — | `{code, name, vision?, mission?, period_start, period_end, owner_id, status?=draft}` → `201 StrategyOut`. Trùng `code` → `409 DUPLICATE_RESOURCE`; `period_end ≤ period_start` → `422 VALIDATION_ERROR`. Audit `execution.strategy_create` |
| EP-STR-04 | GET | `/goals/strategies/{id}` | `execution:read` | — | → `StrategyOut` |
| EP-STR-05 | PATCH | `/goals/strategies/{id}` | `execution:write` (CEO) | — | `{name?, vision?, mission?, period_start?, period_end?, owner_id?, status?, version}` → `StrategyOut`. Hai Strategy `active` chồng kỳ → `422 BUSINESS_RULE_VIOLATION` (`details.reason=overlapping_active_strategy`). Audit `execution.strategy_update` |
| EP-STR-06 | DELETE | `/goals/strategies/{id}` | `execution:write` (CEO) | — | Còn StrategicObjective live → `422 BUSINESS_RULE_VIOLATION` (`reason=has_live_children`) → `204`. Audit `execution.strategy_delete` |
| EP-STR-07 | GET | `/goals/strategic-objectives` | `execution:read` | — | Lọc `strategy_id?`, `pillar?`, `department_id?`; sort `sort_order`/`code` → `StrategicObjectiveOut[]` |
| EP-STR-08 | POST | `/goals/strategic-objectives` | `execution:write` (CEO; DIR trong `scope_pillars`) | — | `{strategy_id, code, title, description?, pillar?, owner_id, department_id?, weight_pct?=0, sort_order?}` → `201`. Trùng `code` → `409 DUPLICATE_RESOURCE`. Audit `execution.strategic_objective_create` |
| EP-STR-09 | GET | `/goals/strategic-objectives/{id}` | `execution:read` | — | → `StrategicObjectiveOut` (+ `kpi_count`, `objective_count`, `initiative_count`) |
| EP-STR-10 | PATCH | `/goals/strategic-objectives/{id}` | `execution:write` (như 08) | — | Mọi field của 08 trừ `strategy_id` + `status`, `version`. Audit `execution.strategic_objective_update` |
| EP-STR-11 | DELETE | `/goals/strategic-objectives/{id}` | `execution:write` (như 08) | — | Còn KPI/Objective/Initiative live liên kết → `422 BUSINESS_RULE_VIOLATION` (`reason=has_live_links`) → `204` |
| EP-STR-12 | GET | `/goals/initiatives` | `execution:read` | `GET /execution/initiatives` (EP-45) | Giữ lọc `objective_id`, `status`, `pillar`, sort v2.1; **thêm** lọc `strategic_objective_id` → `InitiativeOut[]` (**thêm** `strategic_objective_id`, `objective_id` thành nullable) |
| EP-STR-13 | POST | `/goals/initiatives` | `execution:write` | `POST /execution/initiatives` | Body v2.1 + **`strategic_objective_id` bắt buộc**, `objective_id` tùy chọn (OKR đóng góp). SO/Objective không tồn tại/ngoài scope → `422 BUSINESS_RULE_VIOLATION` (`details.field`). Audit `execution.initiative_create` (giữ) |
| EP-STR-14 | GET | `/goals/initiatives/{id}` | `execution:read` | `GET /execution/initiatives/{id}` | → `InitiativeOut` |
| EP-STR-15 | PATCH | `/goals/initiatives/{id}` | `execution:write` | `PATCH /execution/initiatives/{id}` | Giữ hành vi v2.1 (`progress_pct` không sửa tay) + field mới. Đổi `progress_pct` → recompute `strategic_objectives.progress_pct` cùng transaction |
| EP-STR-16 | DELETE | `/goals/initiatives/{id}` | `execution:write` | `DELETE /execution/initiatives/{id}` | Giữ v2.1 (còn task/milestone/decision → `409 CONFLICT_STATE`); **thêm**: còn Project liên kết → `409 CONFLICT_STATE` |
| EP-STR-17..21 | GET/POST/GET/PATCH/DELETE | `/goals/initiatives/{id}/milestones[/{milestone_id}]` | read / write | `/execution/initiatives/{id}/milestones*` | Giữ nguyên body/hành vi v2.1 (milestone `done` → `done_at`, recompute progress); chỉ đổi path. Milestone của **Project** thuộc M1.3 (`/work/*`) |
| EP-STR-22 | GET | `/goals/initiatives/{id}/projects` | `execution:read` | — | Mới. Project có `initiative_id = id` trong scope → `[{id, code, name, status, start_date, planned_end_date, owner_id}]` (gọi service Project M1.3, không query chéo). Gán/bỏ liên kết = field `initiative_id` trên EP-TASK-10/12 (cột `projects.initiative_id` thuộc M1.3, migration `0014`, 05 §2.5) |
| EP-KPI-01 | GET | `/kpis` | `execution:read` | `GET /execution/kpis` (EP-47) | Giữ lọc `owner_id`, `metric_code`, sort v2.1; **thêm** lọc `strategic_objective_id`, `department_id`, `parent_kpi_id`, `band` (band của evaluation kỳ gần nhất) → `KpiOut[]` (**thêm** `strategic_objective_id`, `pillar`, `latest_evaluation`) |
| EP-KPI-02 | POST | `/kpis` | `execution:write` (không EMP) | `POST /execution/kpis` | Body v2.1 + `strategic_objective_id?` (chỉ KPI gốc `parent_kpi_id IS NULL`; KPI con có SO → `422 BUSINESS_RULE_VIOLATION`), `pillar?`. Trùng `code` → `409 DUPLICATE_RESOURCE`. Audit `execution.kpi_create` |
| EP-KPI-03 | GET | `/kpis/{id}` | `execution:read` | `GET /execution/kpis/{id}` | → `KpiOut` |
| EP-KPI-04 | PATCH | `/kpis/{id}` | `execution:write` (không EMP) | `PATCH /execution/kpis/{id}` | Giữ v2.1. Đổi `target` (`kpis.target_value`) **chỉ** là mặc định cho kỳ chưa có KPITarget; đổi target một kỳ dùng EP-KPI-09 |
| EP-KPI-05 | DELETE | `/kpis/{id}` | `execution:write` (không EMP) | `DELETE /execution/kpis/{id}` | Giữ v2.1 (còn KPI con/task → `409 CONFLICT_STATE`) |
| EP-KPI-06 | GET | `/kpis/{id}/measurements` | `execution:read` | `GET /execution/kpis/{id}/measurements` | Lọc **thêm** `period_key?`; sort `measured_at`/`period_key` → `MeasurementOut[]` (**thêm** `measured_by`, `data_source`, `note`, `check_in_id`) — mỗi lần đo là một dòng (R-DEC-51) |
| EP-KPI-07 | POST | `/kpis/{id}/measurements` | `execution:write` (EMP: chỉ KPI của mình) | `POST /execution/kpis/{id}/measurements` | `{period_key, actual_value, source_document_id?, data_source?=manual, note?}` → `201 MeasurementOut`. `period_key` lệch `period_type` → `422 BUSINESS_RULE_VIOLATION`; kỳ/target đã khóa → `409 CONFLICT_STATE` (giữ). **Đổi:** INSERT dòng mới (không UPDATE); upsert `KPIEvaluation` kỳ đó; target = KPITarget hiệu lực tại ngày đo (R-DEC-52). Audit `execution.kpi_measure`; event `execution.kpi_measured` (+ `execution.kpi_below_threshold` khi chuyển band) |
| EP-KPI-08 | GET | `/kpis/{id}/targets` | `execution:read` | — | Mới. Lọc `period_key?`, `as_of?` → `KpiTargetOut[]` (cả bản đã đóng `valid_to`), sort `period_key`,`valid_from` |
| EP-KPI-09 | POST | `/kpis/{id}/targets` | `execution:write` (không EMP) | — | Mới. `{period_key, target, baseline?, minimum?, stretch?, band_thresholds?, score_cap_pct?, valid_from?=hôm nay, reason?}` → `201 KpiTargetOut`. Đóng target hiện hành cùng kỳ (`valid_to = valid_from` mới) + mở bản mới trong **một** transaction (khóa dòng). `valid_from` ≤ `valid_from` hiện hành, ngoài `[period_start, period_end)`, kỳ đã khóa → `422 BUSINESS_RULE_VIOLATION`/`409 CONFLICT_STATE`. Đánh giá lại `KPIEvaluation` kỳ đó. Audit `execution.kpi_target_set` |
| EP-KPI-10 | GET | `/kpis/{id}/evaluations` | `execution:read` | — | Mới. Lọc `from_period?`, `to_period?` (mặc định 12 kỳ gần nhất) → `KpiEvaluationOut[]` sort `period_key` asc (dữ liệu đồ thị SCR-58) |
| EP-OKR-01 | GET | `/objectives` | `execution:read` | `GET /execution/objectives` (EP-46) | Giữ lọc `period_key`, `owner_id`; **thêm** `strategic_objective_id`, `department_id`, `parent_id`, `at_risk?` → `ObjectiveOut[]` (**thêm** `strategic_objective_id`, `at_risk_kr_count`) |
| EP-OKR-02 | POST | `/objectives` | `execution:write` (không EMP) | `POST /execution/objectives` | Body v2.1 + `strategic_objective_id?` (chỉ Objective gốc; có `parent_id` + SO → `422`). Giữ quy tắc kích hoạt 2..5 KR |
| EP-OKR-03 | GET | `/objectives/{id}` | `execution:read` | `GET /execution/objectives/{id}` | → `ObjectiveOut` |
| EP-OKR-04 | PATCH | `/objectives/{id}` | `execution:write` (không EMP) | `PATCH /execution/objectives/{id}` | Giữ v2.1 |
| EP-OKR-05 | DELETE | `/objectives/{id}` | `execution:write` (không EMP) | `DELETE /execution/objectives/{id}` | Giữ v2.1 |
| EP-OKR-06 | GET | `/objectives/{id}/key-results` | `execution:read` | `GET /execution/objectives/{id}/key-results` | → `KeyResultOut[]` (**thêm** `at_risk`, `at_risk_since`, `at_risk_reasons`, `last_checked_in_at`) |
| EP-OKR-07 | POST | `/objectives/{id}/key-results` | `execution:write` (không EMP) | `POST /execution/objectives/{id}/key-results` | Giữ v2.1 (> 5 KR → `422`) |
| EP-OKR-08 | GET | `/key-results/{id}` | `execution:read` | `GET /execution/objectives/{oid}/key-results/{id}` | Phẳng hóa path → `KeyResultOut` |
| EP-OKR-09 | PATCH | `/key-results/{id}` | `execution:write` (không EMP) | `PATCH …/key-results/{id}` | Giữ v2.1; `current_value`/`confidence` **không** sửa qua PATCH (chỉ qua check-in) |
| EP-OKR-10 | DELETE | `/key-results/{id}` | `execution:write` (không EMP) | `DELETE …/key-results/{id}` | Giữ v2.1 |
| EP-OKR-11 | GET | `/key-results/{id}/measurements` | `execution:read` | — | Mới. → `KrMeasurementOut[]` sort `measured_at` desc (lịch sử giá trị + confidence, SCR-59) |
| EP-PRF-01 | GET | `/key-results/{id}/check-ins` | `execution:read` | `GET /execution/check-ins?key_result_id=` | → `CheckInOut[]` (kèm `kr_measurement: {value, progress_pct, previous_progress_pct}`) sort `checked_in_at` desc |
| EP-PRF-02 | POST | `/key-results/{id}/check-ins` | `execution:write` | `POST /execution/check-ins` (`key_result_id`) | `{value, confidence, note?, blocker?, support_needed?, next_action?}` (≤ 5000 ký tự/field) → `201 CheckInOut`. Objective không `active` → `409 CONFLICT_STATE` (`reason=objective_not_active`). Một transaction: `CheckIn` + `KRMeasurement` + cập nhật KR (`current_value`, `confidence`, `last_checked_in_at`, cờ at-risk) + recompute progress Objective. Audit `execution.check_in_create`; event `execution.okr_checked_in` (+ `execution.okr_at_risk` khi chuyển trạng thái, R-DEC-55) |
| EP-PRF-03 | GET | `/kpis/{id}/check-ins` | `execution:read` | `GET /execution/check-ins?kpi_id=` | → `CheckInOut[]` |
| EP-PRF-04 | POST | `/kpis/{id}/check-ins` | `execution:write` | `POST /execution/check-ins` (`kpi_id`) | Body như 02 → `CheckIn` + `KPIMeasurement` kỳ hiện tại (`check_in_id`) như v2.1. Audit `execution.check_in_create`; event `execution.kpi_measured`, `execution.okr_checked_in` (`target_type=kpi`) |
| EP-PRF-05 | GET | `/goals/check-ins` | `execution:read` | `GET /execution/check-ins` | Feed tổng hợp team (F4 bước 4). Giữ lọc `owner_id` (= `user_id`), `period_key`, `kpi_id`, `key_result_id`; **thêm** `department_id`, `from`, `to`, `confidence` → `CheckInOut[]` (**thêm** `target_type`, `target_title`, `department_id`) |
| EP-PRF-06 | GET | `/goals/check-ins/due` | `execution:read` | — | Mới. Thẻ F4 của **người gọi**: KR (Objective `active`, kỳ chứa hôm nay) + KPI `active` có `owner_id = Principal.user_id` → `[{target_type, target_id, title, unit, current_value, target, confidence, last_checked_in_at, due: bool, prefill: null}]`; `due` = chưa check-in trong `GOALS_KR_CHECKIN_MAX_AGE_DAYS` (KR) / kỳ đến hạn chưa đo (KPI). `prefill` luôn `null` ở M1.4 (chỗ cho "AI điền sẵn" M2.4) |

**Tool / ACT:** M1.4 **không thêm** `TOOL-*`/`ACT-*`. Chỉ sửa nhãn endpoint trong `modules/ai/tools/registry.py`: `TOOL-get_kpi_status` → `EP-KPI-01`, `TOOL-list_objectives` → `EP-OKR-01`, `TOOL-record_kpi_measurement` → `EP-KPI-07 / ACT-record_kpi_measurement`. Tool org/KPI/OKR mới ở M1.6.
#### 7.2.4. M1.5 — D03 Data Capture C1/C3/C5 · Action Registry v2 · lineage (Spec lock M1.5 — đề xuất, chờ human duyệt)

**Quy ước chung M1.5** (kế thừa §7.2.1):
- Envelope `{data, meta?}`, phân trang `limit/offset/sort_by/order`, mã lỗi §1.4 (**không thêm mã**). Mọi `POST` tạo/commit/hành động bắt buộc `Idempotency-Key` (thiếu → `400 BAD_REQUEST`; replay cùng key + cùng body → cùng response; khác body → `409 IDEMPOTENCY_CONFLICT`). `PATCH` nhận body `version` (lệch → `409 CONFLICT_STATE`).
- Mọi mutation: `ENT-AuditLog` (`action = idp.<verb>`) + `ENT-OutboxEvent` (§9.2) + `ENT-DataLineage` (khi ghi domain) **cùng một transaction**; lỗi giữa chừng → rollback toàn bộ (bản ghi đích, document_actions, lineage, audit, outbox).
- Prefix (R-DEC-39): resource **mới** của D03 dùng `/data-capture/*`; `/idp/*` v2.1 **giữ nguyên path** (FE SCR-18a/b + test đang dùng). Lineage dùng `/lineage/*` (R-DEC-64).
- Tenant: repository lọc `tenant_id` (R-DEC-21); bản ghi tenant khác → `404 NOT_FOUND`.
- Field mức 3/4 trong preview/review/lineage: trả `{ "masked": true }` khi caller không có quyền đọc mức đó ở domain đích (policy T-615, 05 §2.4). Riêng phiên review được phân (REV) xem mức 4 của tài liệu đó (CLAUDE.md §5.3).
- Giới hạn (04 FR-DC-07, `core/config.py`, **giữ**): 50 MB/file, 100 file/lần (C3), 300 trang/PDF. **Mới cho C5** (cấu hình, không phải ngưỡng khóa — R-DEC-62): `idp_import_max_rows = 5000` dòng dữ liệu/file, `idp_import_max_sheets = 20`, `idp_import_max_columns = 60`; vượt → `413 FILE_TOO_LARGE` (`details.limit = rows|sheets|columns`). Upload stream chunk 1 MB (`_UPLOAD_CHUNK`, **giữ**) vào object store rồi parse bằng `openpyxl.load_workbook(read_only=True, data_only=True)` từ file tạm (SpooledTemporaryFile ≤ 8 MB RAM), không đọc cả file vào RAM. CSV: `csv` stdlib, UTF-8/UTF-8-BOM; mã hóa khác → `422 VALIDATION_ERROR`. `.xls` (BIFF) → `415 UNSUPPORTED_MEDIA_TYPE` (openpyxl không đọc).
- **Quyền 2 lớp khi ghi domain (R-DEC-61):** endpoint giữ **đúng một** permission `idp:*`; bên trong, Action Registry v2 kiểm `required_permission` của **từng** ACT (`<domain>:write` hoặc `hr:admin`) bằng `Principal` của người gọi (`user.has()`, có pillar). Thiếu → không ghi; xử lý theo EP (xem ghi chú EP-DC-08/16/23).

**Bảng EP** (D03 — module `idp`; path `/idp/*` giữ, `/data-capture/*` mới):

| EP-<DOMAIN>-NN | Method | Path | Permission | Request/Response | Idempotency | EP v2.1 |
|---|---|---|---|---|---|---|
| EP-DC-01 | POST | `/idp/documents` | `idp:write` | **sửa:** multipart `files[]` 1..100 + **mới** form field `document_type?` (code doc type active, chọn trước → `type_preselected=true`, bỏ bước classify — FR-DC-09) → `202 UploadResultOut` (giữ shape). `document_type` lạ/inactive → `422 VALIDATION_ERROR`. Audit `idp.upload` (giữ) | bắt buộc | EP-20 `/idp/documents` |
| EP-DC-02 | GET | `/idp/documents/{id}` | `idp:read` | giữ → `DocumentOut` (**thêm** `document_type`, `committed_at`, `undo_deadline`, `can_undo`, `rolled_back_at`) | — | EP-25 |
| EP-DC-03 | GET | `/idp/documents/{id}/extraction` | `idp:read` | giữ → `ExtractionResultOut` | — | EP-26 |
| EP-DC-04 | GET | `/idp/review-queue` | `idp:approve` | giữ (lọc `status`, `document_type`, `assigned_to`, `date_from/to`); **sửa:** mặc định gồm cả `APPROVED` chờ ghi khi caller có quyền đích (R-DEC-61) | — | EP-28 |
| EP-DC-05 | GET | `/idp/documents/{id}/review` | `idp:approve` | **sửa:** `ReviewDetailOut` + `rows[]` (nhóm field theo `row_index` cho doc dạng bảng), `planned_actions[] {action_name, count, required_permission, permitted}` (dry-run validate, không ghi), `can_commit` | — | (detail, không số) |
| EP-DC-06 | POST | `/idp/documents/{id}/review/open` | `idp:approve` | giữ (soft lock 15 phút, `409 REVIEW_LOCKED`) | bắt buộc | EP-29 |
| EP-DC-07 | PATCH | `/idp/documents/{id}/fields` | `idp:approve` | giữ + cho phép `field_id` của field có `row_index`; `accept_all_high` **không** áp trường trọng yếu (giữ) | khuyến nghị | EP-30 |
| EP-DC-08 | POST | `/idp/documents/{id}/review/approve` | `idp:approve` | **sửa:** `{comment?, version}` → `ApproveOut {document, actions[], undo_deadline}`. Chạy ACT theo `ExtractionSchema.action_names` qua Registry v2. Caller có **đủ** `required_permission` → `COMMITTED`; thiếu ≥ 1 → `APPROVED` (chờ người có quyền ghi, EP-DC-23), `actions=[]`, `meta.pending_permissions[]`. Trường trọng yếu chưa xác nhận → `422 ACTION_REJECTED` (`details.reason=critical_unconfirmed`, `fields[]`). Validate ACT fail → `422 ACTION_REJECTED` (`details.action_name, row_index, errors[]`), không ghi gì. Audit `idp.document.committed` (giữ chuỗi) hoặc `idp.document_approve` | bắt buộc | EP-31 |
| EP-DC-09 | POST | `/idp/documents/{id}/review/reject` | `idp:approve` | giữ `{reason}` | bắt buộc | EP-32 |
| EP-DC-10 | POST | `/idp/documents/{id}/review/release` | `idp:approve` | giữ | bắt buộc | EP-35 |
| EP-DC-11 | POST | `/idp/documents/{id}/review/reassign` | `idp:approve` | giữ (ACT-reassign_review); **sửa:** cho phép `to_role_code` = role có quyền đích (vd `DIR`) | bắt buộc | EP-126 |
| EP-DC-12 | POST | `/idp/review-queue/merge` | `idp:approve` | giữ (ACT-merge_review) | bắt buộc | EP-127 |
| EP-DC-13 | GET | `/data-capture/inbox` | `idp:read` | **mới** Hộp thư dữ liệu SCR-45: lọc `group` ∈ `processing` (UPLOADED…VALIDATING) / `needs_review` (NEEDS_REVIEW, IN_REVIEW) / `approved` / `committed` (AUTO_APPROVED, COMMITTED) / `rejected` / `failed` (FAILED, DUPLICATE) / `rolled_back`; `channel`, `document_type`, `mine`, `q` (tên file), `date_from/to`; sort `submitted_at`/`committed_at` → `InboxItemOut[] {document, document_type, channel, submitted_by_name, record_count, undo_deadline, can_undo, batch_id}` + `meta.pagination` + `meta.counts{group: n}` | — | — |
| EP-DC-14 | GET | `/data-capture/documents/{id}/source` | `idp:read` | **mới** "Xem tài liệu gốc": `?page=` → `{url (presigned GET 5 phút), mime_type, page_count, page}`; doc `kind=MANUAL` → `422 BUSINESS_RULE_VIOLATION` (`reason=no_file`). Audit `idp.source_view` khi `sensitivity_level ≥ 3` | — | — |
| EP-DC-15 | GET | `/data-capture/forms/{document_type}` | `idp:write` | **mới** C1: form sinh từ schema published → `FormOut {document_type, schema_version, fields[] {name, label_key, value_type, required, is_critical, sensitivity_level, enum?, master_ref?, repeatable_group?}, required_permissions[], permitted}` | — | — |
| EP-DC-16 | POST | `/data-capture/manual` | `idp:write` | **mới** C1: `{document_type, schema_version, values{field: v}, rows?[{field: v}], department_id?}` → `201 ManualSubmitOut {document, status, actions[], validation_errors[], undo_deadline}`. Tạo `SourceDocument(kind=MANUAL, channel=C1, manual_payload)`, field confidence = 1.0, `source=MANUAL`. Validate lỗi `fail/blocking` → `422 VALIDATION_ERROR` (`details.fields[]`), không tạo bản ghi. Caller đủ quyền đích → commit ngay (`COMMITTED`); thiếu → `NEEDS_REVIEW` (R-DEC-65). Audit `idp.manual_submit` | bắt buộc | — |
| EP-DC-17 | POST | `/data-capture/imports` | `idp:write` | **mới** C5 bước 1: multipart `file` (1 file `.xlsx`/`.csv`) + `document_type?` → `201 ImportPreviewOut {batch_id, document_id, sheets[] {name, row_count, header_row, columns[]}, suggested_document_type {code, confidence}, column_mapping {column → field\|null, confidence}, preview_rows[≤20], summary{rows_total, rows_valid, rows_invalid}, version}`. `ImportBatch(kind=excel_import)` + `SourceDocument(channel=C5, status=VALIDATING)`; trùng SHA-256 → doc `DUPLICATE`, `409 DUPLICATE_RESOURCE` (`details.duplicate_of_id`). Audit `idp.import_upload` | bắt buộc | — |
| EP-DC-18 | GET | `/data-capture/imports/{batch_id}` | `idp:read` | **mới** → `ImportPreviewOut` hiện tại | — | — |
| EP-DC-19 | PATCH | `/data-capture/imports/{batch_id}/mapping` | `idp:write` | **mới** `{document_type, sheet, header_row, mapping{column: field\|null}, version}` → validate lại **toàn bộ** dòng → `ImportPreviewOut`. Field `required` chưa map → `422 VALIDATION_ERROR` (`details.unmapped_required[]`); batch không ở `VALIDATING` → `409 CONFLICT_STATE`. Chỉ submitter. Audit `idp.import_mapping_update` | khuyến nghị | — |
| EP-DC-20 | GET | `/data-capture/imports/{batch_id}/rows` | `idp:read` | **mới** `?status=valid\|invalid\|all` → `ImportRowOut[] {row_number, values{field: v\|{masked}}, errors[] {field, rule_code, message_key, params}}` + pagination | — | — |
| EP-DC-21 | GET | `/data-capture/imports/{batch_id}/error-file` | `idp:read` | **mới** tải `.xlsx` dòng lỗi (cột gốc + cột `Lỗi`), sinh bằng openpyxl `write_only`; không có dòng lỗi → `404 NOT_FOUND`. Cột mức 4 bị bỏ nếu caller không có quyền | — | — |
| EP-DC-22 | POST | `/data-capture/imports/{batch_id}/submit` | `idp:write` | **mới** C5 xác nhận: `{version}` → ghi `ExtractedField` (`row_index` = số dòng Excel) cho **dòng hợp lệ**, dòng lỗi loại khỏi tài liệu → doc `NEEDS_REVIEW` + `ReviewAssignment` (R-DEC-62) → `200 {document, rows_submitted, rows_excluded}`. 0 dòng hợp lệ → `422 BUSINESS_RULE_VIOLATION` (`reason=no_valid_rows`). Audit `idp.import_submit` | bắt buộc | — |
| EP-DC-23 | POST | `/data-capture/documents/{id}/commit` | `idp:write` | **mới** ghi tài liệu `APPROVED` (bước 2 khi người duyệt thiếu quyền đích): `{version}` → `ApproveOut`. Thiếu quyền đích → `403 FORBIDDEN_ROLE` (`details.missing[]`); trạng thái ≠ `APPROVED` → `409 CONFLICT_STATE`. Audit `idp.document.committed` | bắt buộc | — |
| EP-DC-24 | POST | `/data-capture/documents/{id}/undo` | `idp:write` | **mới** `{reason, reason_code: mistake\|critical_field_wrong\|duplicate\|other}` → `200 {document (ROLLED_BACK), reverted_actions[]}`. Quá `undo_deadline` → `410 UNDO_EXPIRED`; trạng thái ≠ `COMMITTED` → `409 CONFLICT_STATE`; bản ghi đích đã bị sửa sau commit → `409 CONFLICT_STATE` (`details.conflicts[] {table, id}`), không đảo gì. Audit `idp.document_rollback`; event `idp.document_rolled_back` | bắt buộc | EP-33 (v2.1 chưa build, S4c) |
| EP-DC-25 | GET | `/data-capture/documents/{id}/actions` | `idp:read` | **mới** → `DocumentActionOut[] {seq, action_name, result_refs[], status: applied\|reverted, reverted_at}` | — | — |
| EP-DC-26 | GET | `/lineage/{entity}/{id}` | `idp:read` | **mới** FR-DATA-04: `entity` ∈ whitelist (R-DEC-64) → `LineageOut {entity, id, links[] {target_column, source_document_id, document_type, original_filename, page_number, sheet_name, row_index, field_name, raw_text\|{masked}, confidence, action_name, committed_at, revoked_at}}`; ngoài scope → `200 {restricted: true, reason: target_out_of_scope\|source_out_of_scope}`; `entity` lạ → `422 VALIDATION_ERROR`; không có lineage → `links=[]` | — | — |
| EP-DC-27 | GET | `/data-capture/document-types` | `idp:read` | **mới** → `DocumentTypeOut[] {id, code, name_vi, name_en, pillars, is_active, current_schema_version, channels_supported}`; `include_inactive=true` chỉ có hiệu lực với `idp:admin` | — | — |
| EP-DC-28 | PATCH | `/data-capture/document-types/{id}` | `idp:admin` | **mới** `{name_vi?, name_en?, is_active?, classifier_keywords?, version}` → `DocumentTypeOut`. Audit `idp.doctype_update` | khuyến nghị | — |
| EP-DC-29 | GET | `/data-capture/extraction-schemas` | `idp:admin` | **mới** lọc `document_type`, `status` → `ExtractionSchemaOut[]` (05 §2.7) | — | — |
| EP-DC-30 | POST | `/data-capture/extraction-schemas` | `idp:admin` | **mới** `{document_type, clone_from_id?, fields[], thresholds, action_names[]}` → `201` bản `draft`, `schema_version = max+1`. Audit `idp.schema_create` | bắt buộc | — |
| EP-DC-31 | PATCH | `/data-capture/extraction-schemas/{id}` | `idp:admin` | **mới** chỉ `draft` (khác → `409 CONFLICT_STATE`, DEC-162 bất biến sau publish). Ràng buộc cứng → `422 VALIDATION_ERROR`: ngưỡng thấp hơn DEC-133 (`classification_confidence_min < 0.95`, `required_field_min < 0.90`); bỏ `is_critical` của field `value_type ∈ {money, tax_code}` hoặc tên thuộc `CRITICAL_FIELD_NAMES` (FR-DC-16); `action_names` không có trong Registry; `fields[].target` trỏ tham số ACT không tồn tại. Audit `idp.schema_update` | khuyến nghị | — |
| EP-DC-32 | POST | `/data-capture/extraction-schemas/{id}/publish` | `idp:admin` | **mới** `{version}` → `published`, bản published cũ → `retired`, `document_types.current_schema_id` trỏ bản mới. Job đang chạy giữ schema cũ. Audit `idp.schema_publish` | bắt buộc | — |
| EP-DC-33 | GET | `/data-capture/validation-rules` | `idp:admin` | **mới** lọc `extraction_schema_id`, `kind` → `ValidationRuleOut[]` | — | — |
| EP-DC-34 | POST | `/data-capture/validation-rules` | `idp:admin` | **mới** `{extraction_schema_id?, code, kind, expression{op,…}, severity, tolerance?}`; `op` ngoài tập Validator → `422`; trùng `(schema, code)` → `409 DUPLICATE_RESOURCE`; schema không `draft` → `409 CONFLICT_STATE`. Audit `idp.rule_create` | bắt buộc | — |
| EP-DC-35 | PATCH | `/data-capture/validation-rules/{id}` | `idp:admin` | **mới** `{expression?, severity?, tolerance?, is_active?, version}`; rule thuộc schema published → `409 CONFLICT_STATE`. Audit `idp.rule_update` | khuyến nghị | — |
| EP-DC-36 | POST | `/data-capture/incidents` | `idp:approve` | **mới** G4: `{source_document_id, extracted_field_id?, field_name, target_table?, target_id?, description}` → `201 IncidentOut`. Audit `idp.incident_report` | bắt buộc | — |
| EP-DC-37 | GET | `/data-capture/incidents` | `idp:approve` | **mới** lọc `period`, `undetected_only` → `IncidentOut[]` | — | — |

- Route tĩnh (`/data-capture/imports`, `/inbox`) khai báo trước route có `{id}`. Router mới `modules/idp/routes/data_capture.py` (prefix `/data-capture`) + `modules/idp/routes/lineage.py` (prefix `/lineage`), include trong `main.py`.
- Metric G3/DQ không thêm EP: đọc qua `GET /dashboard/metrics/{code}` hiện có; **sửa** `breakdown[]` của `METRIC-DQ-01` lấy per-domain từ `platform.dq_domain_scores` (R-DEC-68).

**Data scope theo role** (`idp/services/scope.py` **sửa**: thêm `inbox_filter`, `lineage_visible`):

| Role | Gửi C1/C3/C5 | Hộp thư EP-DC-13 | Review/approve | Ghi đích (ACT) | Undo EP-DC-24 | Lineage EP-DC-26 | Admin schema/rule |
|---|---|---|---|---|---|---|---|
| CEO | có (`idp:write`) | toàn công ty | không (thiếu `idp:approve`) | có quyền đích của CEO (`hr:admin`, `execution:write`…) | tài liệu mình gửi | mọi entity | không |
| DIR | có | tài liệu thuộc phòng ban trong khối (`scope_pillars` ∩ `pillars` tài liệu) | có (khối) | theo khối (`require_pillar`) | mình gửi **hoặc** đã duyệt; hoặc mọi tài liệu trong khối | entity trong khối | không |
| MGR | có | phòng ban mình (+ phòng con) | có (phòng ban) | `execution:write` (d), `finance:write` (d); **không** `hr:admin`/`hr:write` → HR list dừng ở `APPROVED` | mình gửi/đã duyệt | entity trong phòng ban | không |
| EMP | có | chỉ tài liệu mình gửi | không | `execution:write` (o) — C1 task/check-in của mình | mình gửi | entity mình đọc được; còn lại `restricted` | không |
| REV | có | hàng chờ được phân + mình gửi | có (phân công) | không có quyền đích nào → luôn dừng `APPROVED`, chuyển người ghi (EP-DC-11/23) | không (trừ tài liệu mình gửi) | chỉ tài liệu trong phiên review được phân | không |
| ADM | không (không có `idp:write`) | — `403 FORBIDDEN_ROLE` | không | không | không | không (`hr:read` scope `s` không gồm bản ghi) | có (`idp:admin`) |
| AI | không (chỉ `ai:*`; C2 hoãn M1.7 T-717) | — | — | qua `ai/services/action_service` (L2/L3) dùng cùng Registry v2 | AI undo 24 h (giữ) | — | — |

- Ngoài scope ở GET theo id → `404 NOT_FOUND` (không lộ tồn tại, như v2.1 `document_visible`); ở lineage → `{restricted:true, reason}` (CLAUDE.md §5.3).
- Undo: `idp:write` + (submitter **hoặc** người duyệt **hoặc** `sees_all_departments`) **và** caller có `required_permission` của **mọi** ACT cần đảo (R-DEC-66); thiếu → `403 FORBIDDEN_ROLE`.

**Bảng ACT — Action Registry v2** (`modules/idp/services/actions/` **mới**; `ai/services/action_registry.py` **sửa** thành re-export, R-DEC-60). Mỗi ACT: `ActionDef {name, module, required_permission, reversible, is_finance, params_model (Pydantic), validate(db, user, params) → errors[], run(db, user, params, ctx) → ActionOutcome {result_refs[{schema, table, id}], snapshot}, undo(db, user, outcome) }`. `run` gọi **service public** của module đích bằng `AsyncSession` của request (DEC-125), service đích tự ghi audit + outbox của nó; `ctx = {source_document_id, source="IDP"|"IMPORT"|"MANUAL"}` gán `source`, `source_document_id` cho bản ghi đích.

| ACT | Module / service đích | required_permission | Tham số chính (← field schema) | Khóa upsert / trùng | Undo | Doc type |
|---|---|---|---|---|---|---|
| ACT-create_department | hr `HrService.create_department` | `hr:admin` | code, name, parent_code? | `code` live tồn tại → **dùng lại** (không tạo, `result_refs.reused=true`) | `archive_department` (soft) nếu do ACT tạo | #4 |
| ACT-create_team | hr `StructureService.create_team` | `hr:admin` | code, name, department_code | `(department, code)` → dùng lại | `archive_team` | #4 |
| ACT-create_position | hr `StructureService.create_position` | `hr:admin` | title (→ code slug), department_code | `(department, title)` → dùng lại | `archive_position` | #4 |
| ACT-create_employee | hr `HrService.create_employee` (+ `OrgService.assign`) | `hr:write` **hoặc** `hr:admin` (any-of — R-DEC-61; CEO/ADM không có `hr:write`; `hr:write` cùng quyền EP-HR-02 `POST /hr/employees` — hồ sơ NV là dữ liệu nhân sự, không phải cơ cấu; phân công đầu tiên đi kèm theo hành vi EP-HR-02) | employee_code, full_name, title, department_code, manager_code?, hire_date, status, salary? (mức 4, trọng yếu → `add_salary`) | `employee_code` live trùng → lỗi dòng `DUPLICATE` (không cập nhật — upsert NV hoãn M2.x) | `delete_employee` (soft) + đóng assignment | #4 |
| ACT-upsert_kpi | execution `KpiService.create_kpi/update_kpi` | `execution:write` | code, name, unit, period_type, direction, owner_code, department_code? | `code` → update, snapshot giá trị cũ | update về snapshot / delete nếu tạo mới | #2 |
| ACT-upsert_kpi_target | execution `kpi` (M1.4) `KpiTargetService.upsert` | `execution:write` | kpi_code, period_key, baseline?, target, stretch? | `(kpi, period_key)`; `locked_at` ≠ null → lỗi `BUSINESS_RULE_VIOLATION` | snapshot / delete | #2 |
| ACT-record_kpi_measurement | execution `KpiService.measure` | `execution:write` | kpi_code, period_key, actual_value | `(kpi, period_key)` đã có & `locked_at` → lỗi dòng | xóa measurement do ACT tạo (service `delete_measurement`, M1.4) | #3 |
| ACT-upsert_objective | execution `goals` (M1.4) `OkrService.create/update_objective` | `execution:write` | title, period_key, level, owner_code, parent_title? | `(period_key, title, owner)` | snapshot / delete | #2 |
| ACT-upsert_key_result | execution `OkrService.create_kr/update_kr` | `execution:write` | objective_title, title, unit, baseline, target, owner_code | `(objective, title)` | snapshot / delete | #2 |
| ACT-record_kr_checkin | execution `KpiService.check_in` → `apply_check_in` | `execution:write` | kr_ref, value, confidence, note? | — (append) | xóa check-in + `recompute_progress` | #3 |
| ACT-create_task | execution `TaskService.create` (giữ, **sửa** truyền `source_ref`, `parent_task_id` M1.3) | `execution:write` | title, assignee_code, due_date, kr_ref?/kpi_code? | — | `TaskService.delete` (giữ) | #1, #2 |
| ACT-create_invoice | finance `InvoiceService.create` (giữ, chuyển từ `commit_service._commit_invoice`) | `finance:write` | như v2.1 | `number_taken` → `DUPLICATE_RESOURCE` | `InvoiceService` void/delete (soft) | #7 (P1, giữ code) |

- Tham chiếu `*_code` giải bằng service đọc của module đích trong **cùng transaction**, ưu tiên bản ghi do ACT trước của cùng tài liệu vừa tạo (`ctx.created_refs`) → thứ tự chạy #4: department → team → position → employee (2 lượt: tạo NV, rồi gán `manager_id`), #2: objective → key_result → kpi → kpi_target.
- `validate` chạy cho **mọi** dòng trước khi `run` dòng đầu (dry-run, cũng dùng cho `planned_actions` EP-DC-05); có lỗi → `ACTION_REJECTED`, không ghi gì. Trong `run`, lỗi service đích (`DUPLICATE_RESOURCE`, `BUSINESS_RULE_VIOLATION`) → rollback cả tài liệu, response `422 ACTION_REJECTED` (`details.cause_code`, `row_index`).
- Tool: **giữ** `TOOL-commit_extraction` (kế thừa risk của ACT, cần `idp:write` + `<domain đích>:write`), `TOOL-import_table` (`idp:write`), `TOOL-get_source_document` — không thêm tool mới; AI chỉ đề xuất, ghi C5/C1 do người bấm (hoãn tool chat C2 sang M1.7).
- Ngoài phase: ACT cho #1 Meeting/Decision (hoãn M2.3), #5 SOP → Knowledge (hoãn M3.4; M1.6 UC-07 chỉ lưu `COMMITTED` metadata-only như OTHER), #6 Finance Lite (hoãn M2.1), upsert NV/đổi phòng ban qua import (hoãn M2.x).
#### 7.2.5. M1.6 — D26 AI Platform nền · UC-07 Onboarding (Spec lock M1.6 — đề xuất, chờ human duyệt)

**Quy ước chung M1.6:** envelope/phân trang/mã lỗi theo §10, §1.4 (**không thêm mã lỗi mới**; `AI_WRITE_VIA_ACTION`, `AI_UNKNOWN_TOOL`, `AI_TOOL_NOT_AVAILABLE` hiện chỉ là `error_code` nội bộ của `ToolCallLog`, không phải `error.code` HTTP — giữ nguyên). Endpoint **giữ từ v2.1 giữ path + hành vi** (gán ID mới, cột `EP v2.1`); endpoint list **mới** dùng `limit/offset/sort_by/order` + `meta.pagination`; endpoint list v2.1 (`/ai/conversations`, `/ai/insights`, `/ai/actions`) giữ trả mảng không phân trang (không breaking). Mọi `POST`/`PUT` bắt buộc `Idempotency-Key`; `PATCH` nhận body `version` (lệch → `409 CONFLICT_STATE`). Mọi mutation cấu hình AI ghi `ENT-AuditLog` (`action = ai.<verb>`, `why = reason` bắt buộc) + outbox `ai.policy_changed` (§9.2) **trong cùng transaction**. Log (`tool_call_logs`, `model_call_logs`) lọc theo `tenant_id` (R-DEC-74).

**Quyền (không thêm permission):** `ai:query` = đọc cho người dùng AI (mọi role người + AI actor); `ai:write` = xác nhận/từ chối/hoàn tác action (kèm `<domain>:write` của action — như EP-115 v2.1); `ai:admin` = **AI Control Center** (CEO scope `k`, ADM). DIR/MGR/EMP/REV không có `ai:admin` → `403 FORBIDDEN_ROLE`. Log tool/model chỉ `ai:admin`; `arguments` trong log đã qua PII filter (mức 4 bỏ, mức 3 → `EMP-xxxx`/`CLI-xxxx`) nên ADM xem được mà không vi phạm 02 §2 (ADM không đọc bản ghi nghiệp vụ). Trạng thái onboarding: đọc `platform:read` (CEO, ADM), ghi `platform:admin` (CEO, ADM).

| EP | Method | Path | Permission | EP v2.1 | Ghi chú (request → response) |
|---|---|---|---|---|---|
| EP-AI-01 | POST | `/ai/chat` | `ai:query` | EP-110 | Giữ. **Sửa (T-645b):** tool WRITE/EXECUTION model gọi → `ActionService.propose()` (không còn `AI_WRITE_VIA_ACTION`); `suggested_actions[]` = `AIActionOut` (L2, `status=proposed`) hoặc `{action_name, tool_name, autonomy_level:"L1", input_preview}` (L1, không tạo `ai_actions`); kill switch `mode=L0` áp cho agent → tool ghi trả `ToolCallLog.status=forbidden`, `error_code=AI_DISABLED`, câu trả lời có warning `ai.warn.kill_switch`. Idempotency-Key |
| EP-AI-02 | POST | `/ai/chat/stream` | `ai:query` | EP-111 | Giữ thứ tự SSE 10 §6; `done` mang `suggested_actions[]` như EP-AI-01 (**không** thêm loại event SSE) |
| EP-AI-03 | GET | `/ai/conversations` | `ai:query` | EP-112 | Giữ (chỉ của người gọi) |
| EP-AI-04 | GET | `/ai/conversations/{id}/messages` | `ai:query` | EP-112 | Giữ |
| EP-AI-05 | GET | `/ai/insights` | `ai:query` | EP-114 | Giữ (M2.4 mở rộng 9 phần) |
| EP-AI-06 | POST | `/ai/insights/{id}/dismiss` | `ai:query` | EP-114 | Giữ |
| EP-AI-07 | GET | `/ai/actions` | `ai:query` | EP-115 | Giữ lọc `status`, `autonomy_level`; **thêm** lọc `agent_profile_code`. Scope: người thường → `on_behalf_of = sub`; `ai:admin` → toàn tenant (hàng chờ ở SCR-64) |
| EP-AI-08 | GET | `/ai/actions/{id}` | `ai:query` | EP-115 | Giữ; `AIActionOut` **thêm** `agent_profile_code`, `request_id`, `created_at` |
| EP-AI-09 | POST | `/ai/actions/{id}/confirm` | `ai:write` | EP-115 | Giữ (cần thêm `<domain>:write` của ACT; kill switch **không** chặn người xác nhận thẻ L2). `edited_input?`. Idempotency-Key. Audit `ai.action_confirm` |
| EP-AI-10 | POST | `/ai/actions/{id}/reject` | `ai:write` | EP-115 | Giữ `{reason}`. Audit `ai.action_reject` |
| EP-AI-11 | POST | `/ai/actions/{id}/undo` | `ai:write` | EP-116 | Giữ 24h (`410 UNDO_EXPIRED`, `409 CONFLICT_STATE`) |
| EP-AI-12 | GET | `/ai/kill-switch` | `ai:query` | EP-118 | Giữ `KillSwitchOut`; **thêm** `autonomy_ceiling` (`"L2"` ở M1 — R-DEC-72, chỉ đọc) và `reason` (lý do lần đổi gần nhất). FE `KillSwitchBanner` poll mỗi 60 s + khi focus |
| EP-AI-13 | PUT | `/ai/kill-switch` | `ai:admin` | EP-118 | Giữ `{enabled, mode ∈ WRITE_OFF/L0, agents[], reason}`; **thêm** validate `agents[]` ⊆ `agent_profiles.code` (khác → `422 VALIDATION_ERROR`); `reason` rỗng → `422`. Audit `ai.kill_switch` (giữ) + event `ai.policy_changed` (`change=kill_switch`). Idempotency-Key |
| EP-AI-14 | GET | `/ai/tools` | `ai:query` | EP-119 | Giữ path; `ToolOut` **mở rộng đủ 13 metadata** (05 §2.8 "Tool Registry") + `tool_id`, `brd_name`, `kind ∈ READ/WRITE/APPROVAL/EXECUTION`, `compute`, `autonomy_max`, `agents[]` (agent có tool), `effective_level` (sau policy mặc định + ceiling + kill switch cho role người gọi), `available`, `p1_frozen`, `action_name`, `endpoint_ref`. Lọc `kind`, `domain`, `agent`, `available_only` (mặc định false). Không phân trang (≤ 60 dòng) |
| EP-AI-15 | GET | `/ai/usage` | `ai:admin` | EP-119 | Giữ `CostSummaryOut`; `group_by` **thêm** `agent` (cột mới `model_call_logs.agent_profile_code`); **thêm** `period=YYYY-MM` (mặc định tháng hiện tại; sai định dạng → `400`) |
| EP-AI-16 | GET | `/ai/agents` | `ai:query` | — | → `AIAgentOut[]` `{code, agent_ref, name_vi, name_en, description_vi, description_en, allowed_tools[], max_autonomy_level, effective_max_level, model_task, prompt_version, monthly_budget_usd, month_spend_usd, is_enabled, kill_switched, version, updated_at}`; `month_spend_usd` chỉ trả cho `ai:admin` (khác → không có key). 6 agent P0 (R-DEC-71) |
| EP-AI-17 | PATCH | `/ai/agents/{code}` | `ai:admin` | — | `{is_enabled?, max_autonomy_level?, monthly_budget_usd?, allowed_tools?, reason, version}` → `AIAgentOut`. `max_autonomy_level` > `autonomy_ceiling` → `422 BUSINESS_RULE_VIOLATION` (`details.reason=above_ceiling`); `allowed_tools` chứa tool không có trong registry / tool APPROVAL / `p1_frozen` → `422 BUSINESS_RULE_VIOLATION` (`details.reason=invalid_tool`); `code` lạ → `404`. Không tạo/xóa agent qua API (catalog cố định P0). Audit `ai.agent_update`; event `ai.policy_changed` (`change=agent`) |
| EP-AI-18 | GET | `/ai/autonomy-policies` | `ai:admin` | — | Lọc `tool_name`, `agent_profile_code`, `role_code`, `is_active`, `include_deleted` (mặc định false); sort `tool_name`/`updated_at` → `AutonomyPolicyOut[]` (05 §2.8) + `meta.pagination` + `meta.defaults[]` = `{tool_name, action_name, default_level, max_level}` từ registry/seed 04 §9.1 (sau ceiling) để FE hiện "mặc định" cạnh dòng ghi đè |
| EP-AI-19 | POST | `/ai/autonomy-policies` | `ai:admin` | — | `{tool_name, agent_profile_code?, role_code?, max_amount?, currency?, level, max_level, is_active?, reason}` → `201 AutonomyPolicyOut`. Server suy `action_name` từ tool (`ToolDef.action_name`). Quy tắc: tool READ hoặc APPROVAL → `422 BUSINESS_RULE_VIOLATION` (`not_configurable`); `level` > `max_level` hoặc `max_level` > `ToolDef.autonomy_max` → `422` (`above_tool_max`); `level`/`max_level` > ceiling → `422` (`above_ceiling`); tool EXECUTION `max_level` > `L2` → `422` (`execution_max_l2`, 02 §6); trường trọng yếu (ACT tài chính) `level` > `L2` → `422` (`critical_field`); `max_amount` cần `currency`; trùng khóa `(action_name, agent, role, max_amount)` live → `409 DUPLICATE_RESOURCE`. Idempotency-Key. Audit `ai.autonomy_policy_create`; event `ai.policy_changed` (`change=autonomy_policy`) |
| EP-AI-20 | PATCH | `/ai/autonomy-policies/{id}` | `ai:admin` | — | `{level?, max_level?, max_amount?, currency?, is_active?, reason, version}` (không đổi `tool_name/agent/role` — tạo dòng mới) → `AutonomyPolicyOut`. Cùng quy tắc EP-AI-19. Audit `ai.autonomy_policy_update` |
| EP-AI-21 | DELETE | `/ai/autonomy-policies/{id}` | `ai:admin` | — | Query `reason` bắt buộc; soft delete (`deleted_at`) → quay về mặc định → `204`. Audit `ai.autonomy_policy_delete` |
| EP-AI-22 | GET | `/ai/tool-calls` | `ai:admin` | — | Lọc `from`/`to` (ISO 8601 UTC, `from > to` → `400`; mặc định 7 ngày gần nhất), `tool_name`, `tool_kind`, `agent_profile_code`, `status`, `user_id`, `request_id`, `ai_action_id`; sort `created_at` (mặc định desc) → `ToolCallLogOut[]` `{id, created_at, request_id, user_id, agent_profile_code, tool_name, tool_kind, status, error_code, latency_ms, autonomy_level, ai_action_id, message_id, arguments, result_refs}` + `meta.pagination`. Chỉ đọc (append-only) |
| EP-AI-23 | GET | `/ai/model-calls` | `ai:admin` | — | Lọc `from`/`to`, `provider`, `model`, `task_kind`, `caller_module`, `agent_profile_code`, `status`, `request_id`; sort `created_at`/`estimated_cost_micro_usd`/`latency_ms` → `ModelCallLogOut[]` `{id, created_at, request_id, caller_module, task_kind, provider, model, fallback_from, agent_profile_code, user_id, tokens_in, tokens_out, cost_usd, latency_ms, status, error_code, prompt_sha256}` + `meta.pagination`. **Không** có prompt thô (không lưu) |
| EP-ADM-13 | GET | `/platform/onboarding` | `platform:read` | — | → `OnboardingStateOut` (05 §2.8, `platform.system_settings` key `onboarding.state` — R-DEC-75) + `progress` **suy ra từ dữ liệu** (không tin trạng thái client): `{organization_ready: có ≥1 org + `name`, departments, employees, employees_without_user, users_by_role{}, kpis, objectives}` đếm qua service public `hr`/`auth`/`execution`. Chưa có dòng setting → `{status:"not_started", steps:{...all "pending"}}` |
| EP-ADM-14 | PATCH | `/platform/onboarding` | `platform:admin` | — | `{action ∈ start/complete_step/skip_step/reopen_step/finish/reset, step?, refs?, reason?}` → `OnboardingStateOut`. Máy trạng thái 06 §3.4 (SCR-66); `start` khi đã `in_progress` → trả hiện tại (idempotent); `finish` khi bước bắt buộc (`company`, `org_import`, `users`) chưa `done` → `422 BUSINESS_RULE_VIOLATION` (`details.missing_steps[]`); `reset` cần `reason`, chỉ khi `DEMO_MODE=true` hoặc trạng thái chưa `completed` (khác → `422`). `refs` chỉ nhận mã (`import_id`, `document_id`, đếm) — không PII. Audit `platform.onboarding_<action>`; `finish` → event `platform.onboarding_completed`. Body `version` bắt buộc cho mọi action trừ `start` |

- **Route tĩnh trước route `{id}`** (`/ai/autonomy-policies` trước `/{id}`); `/ai/tools` không có `{name}` riêng (13 metadata đã ở list).
- **Không thêm endpoint onboarding orchestration** (R-DEC-75): wizard gọi tuần tự EP sẵn có — EP-ORG-01/02/04 (thông tin DN), import C5 M1.5 (EP-DC-17 upload → EP-DC-18..21 preview/mapping/dòng lỗi → EP-DC-22 submit → duyệt EP-DC-08 hoặc EP-DC-23 commit; undo EP-DC-24; doc type #4 / #2), EP-ORG-24 (xem cây), EP-HR-01 + EP-ADM-05/06 (tạo user + role), KPI/OKR qua import C5 doc type #2 (ghi bằng ACT M1.5), EP-ADM-13/14 chỉ lưu tiến độ + đồng hồ.
- `AIActionOut`, `KillSwitchOut`, `ToolOut`, `CostSummaryOut` **chỉ thêm field** (không đổi/bỏ) → `packages/shared-types` sinh lại; FE v2.1 không vỡ.
- Ma trận quyền: **không đổi** cho AI Control Center. Onboarding cần ADM ghi import doc type #4 → R-DEC-76 (cấp ADM `idp:write` scope `s`).

**Tool Registry — 13 metadata chi tiết (T-644, đóng OQ-10-05).** `ToolDef` (`modules/ai/tools/spec.py`) sửa thành:

| # | Metadata (10 §2.1) | Trường `ToolDef` | Kiểu / giá trị | Hiện trạng → M1.6 |
|---|---|---|---|---|
| 1 | `name` | `name` | `TOOL-<snake_case>` (ID registry, cũng là tên gửi model) + `brd_name: str \| None` (tên BRD §11.2/§6 nếu khác) | giữ `name` (fixture AI không đổi — R-DEC-70); **mới** `brd_name` |
| 2 | `description` | `description` | text EN ≤ 300 ký tự (gửi model) | giữ |
| 3 | `input_schema` | `input_schema` (đổi tên từ `parameters`, giữ alias đọc) | JSON Schema draft 2020-12, `type=object`, `additionalProperties=false`; tool không tham số = `{"type":"object","properties":{}}` | sửa — mọi tool phải khai đủ (hiện nhiều `{}`) |
| 4 | `output_schema` | `output_schema` | JSON Schema của `ToolResult.data` + `sources: SourceRef[]` (§8) bắt buộc với READ | **mới** |
| 5 | `permission` | `required_permissions` | tuple `<domain>:<action>`; READ = 1 quyền; WRITE/EXECUTION = `ai:write` + `<domain>:write` (hoặc `hr:admin` cho cơ cấu) | giữ |
| 6 | `risk_level` | `risk_level` | `low/medium/high` | giữ |
| 7 | `data_scope` | `data_scope` | `<domain>:<grain>`, grain ∈ `aggregate/record/document/structure/self` | giữ, chuẩn hóa grain |
| 8 | `data_classification` | `data_classification` (đổi tên từ `classification`, giữ property cũ) | `PUBLIC/INTERNAL/CONFIDENTIAL/SECRET` (02 §5) | sửa tên |
| 9 | `autonomy_level` mặc định | `autonomy_default` (+ `autonomy_max`) | `L0..L3`; READ = `L0`; L4 không có trong enum | giữ |
| 10 | `approval_required` | `approval_required` | `never` / `threshold` (vượt ngưỡng → ApprovalRequest, như ACT tài chính DEC-155) / `always` | **mới** |
| 11 | `reversible` | `reversible` | `bool \| None` (READ = None) | giữ |
| 12 | `audit_required` | `audit_required` | `bool`; **bất biến:** `True` với WRITE/APPROVAL/EXECUTION (`ENT-AuditLog`); READ = `False` (vẫn ghi `ToolCallLog`) | **mới** |
| 13 | `cost_estimate` | `cost_estimate` | `low/medium/high` | giữ |
| 14 | `owner` | `owner` | role chủ domain duyệt nâng autonomy: `ROLE-DIR:F` (finance), `ROLE-DIR:C` (sales), `ROLE-DIR:O` (hr), `ROLE-DIR:U`/`ROLE-DIR:S` (product/risk, frozen), `ROLE-CEO` (execution, dashboard, platform), `ROLE-ADM` (idp, ai) | **mới** |

- **Phân loại 4 loại (BRD §11.3):** `kind ∈ READ/WRITE/APPROVAL/EXECUTION`; `COMPUTE` v2.1 (`TOOL-get_runway_what_if`, `TOOL-run_risk_scenario`) → `kind=READ` + cờ `compute=True` (R-DEC-70). Thêm `action_name: str \| None` (ACT-* đích, bắt buộc với WRITE/EXECUTION có ghi) và `endpoint_ref` (EP v3 tương ứng — thay chuỗi `"EP-44.C / ACT-create_task"`).
- **Kiểm tra lúc import (test kiến trúc):** thiếu bất kỳ metadata → `ToolRegistryError` khi nạp module (tool "không được đăng ký" — 10 §2.1); APPROVAL ⇒ `declare_to_model=False`; WRITE `reversible=False` ⇒ `autonomy_max ≤ L2`; EXECUTION ⇒ `autonomy_max ≤ L2` trừ `TOOL-send_notification` kênh in-app (giữ `L3`, bị ceiling M1 hạ L2).

**Tool mới (T-645 — đề xuất R-DEC-70, cập nhật 10 §7 + 00 §4.8 + skeleton trước khi code):** 43 → **53** `TOOL-*`.

| TOOL | brd_name | Loại | Permission | ACT / nguồn | data_scope | Class. | Default / Max | approval | Agent |
|---|---|---|---|---|---|---|---|---|---|
| `TOOL-get_org_tree` | — (FR-ORG) | READ | `hr:read` | EP-ORG-24 | `hr:structure` | INTERNAL | L0/L0 | never | ceo, task |
| `TOOL-get_okr_status` | `get_okr_status` | READ | `execution:read` | EP-OKR-01/03/06 (M1.4) | `execution:record` | INTERNAL | L0/L0 | never | performance, ceo |
| `TOOL-get_overdue_tasks` | `get_overdue_tasks` | READ | `execution:read` | EP-TASK-01 `overdue=true` (M1.3) | `execution:record` | INTERNAL | L0/L0 | never | task |
| `TOOL-get_project_status` | `get_project_status` | READ | `execution:read` | EP-TASK-11 (M1.3) | `execution:record` | INTERNAL | L0/L0 | never | task, ceo |
| `TOOL-update_task` | `update_task` | WRITE | `ai:write`+`execution:write` | `ACT-update_task` (**thêm ở M1.6** T-645 — không thuộc 12 ACT M1.5; snapshot undo) | `execution:record` | CONFIDENTIAL | L2/L3 | never | task |
| `TOOL-record_kr_checkin` | — (D10) | WRITE | `ai:write`+`execution:write` | `ACT-record_kr_checkin` (M1.5) | `execution:self` | CONFIDENTIAL | L2/L3 | never | performance |
| `TOOL-upsert_kpi` | — (D08) | WRITE | `ai:write`+`execution:write` | `ACT-upsert_kpi` (M1.5) | `execution:record` | CONFIDENTIAL | L2/L2 | never | performance |
| `TOOL-upsert_objective` | — (D09) | WRITE | `ai:write`+`execution:write` | `ACT-upsert_objective` (M1.5) | `execution:record` | CONFIDENTIAL | L2/L2 | never | performance |
| `TOOL-create_department` | — (FR-ORG-02) | WRITE | `ai:write`+`hr:admin` | `ACT-create_department` (M1.5) | `hr:structure` | INTERNAL | L2/L2 | never | data_capture |
| `TOOL-create_team` | — (FR-ORG-02) | WRITE | `ai:write`+`hr:admin` | `ACT-create_team` (M1.5) | `hr:structure` | INTERNAL | L2/L2 | never | data_capture |

- **Không** thêm tool ghi nhân sự (`upsert_employee`, lương, phân công) — chạm mức 3/4 + Approval Matrix "thay đổi nhân sự: không cho phép" → hoãn (OQ-M16-02). Hồ sơ NV vào hệ thống chỉ qua import C5 người duyệt (UC-07).
- `TOOL-get_kpi_status` (giữ) đổi `endpoint_ref` sang EP-KPI-01 (M1.4); `TOOL-list_tasks`/`TOOL-list_objectives`/`TOOL-create_task`/`TOOL-assign_task`/`TOOL-record_kpi_measurement` đổi `endpoint_ref` sang EP-TASK/EP-OKR/EP-KPI (R-DEC-39). `TOOL-request_approval` giữ `ai:write`+`dashboard:read` và `endpoint_ref` EP-123.C (M1.3 hoãn `POST /workflow/approval-requests` tới M3.2; `TOOL-approve_request`/`reject_request` → EP-WF-03); chuẩn hóa permission theo domain workflow ghi OQ-M16-03.

**Bảng ánh xạ BRD ↔ `TOOL-*`:** xem §2.2 (đóng OQ-10-06).


**Autonomy M1 — ceiling L2 + kill switch (T-646/T-647, R-DEC-72).** `resolve_level()` (`services/autonomy.py`) sửa thứ tự: (1) mặc định seed `AUTONOMY_DEFAULTS[action]` → (2) dòng `AutonomyPolicy` khớp nhất (agent > role > amount, chọn level thấp nhất nếu nhiều dòng cùng độ cụ thể) → (3) `min(level, agent.max_autonomy_level)` → (4) `min(level, AI_AUTONOMY_CEILING)` (config `ConfigService`, mặc định `L2` ở M1; M3.2 đổi `L3`) → (5) kill switch áp agent: `WRITE_OFF` → `min(level, L2)`; `L0` → `L0` (tool ghi không soạn thẻ). Agent `is_enabled=false` → mọi tool của agent coi như không có (không quảng bá cho model). Kết quả L3 ở M1 **không thể xảy ra** (test bất biến).

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
| `invoice.created` (mã code `finance.invoice_created`) | Ghi hóa đơn (qua `commit_extraction`/Finance) | D15 Finance | Cảnh báo dòng tiền, cập nhật metric tài chính |
| `kpi.measured` (mã code `execution.kpi_measured`) | Ghi `record_kpi_measurement` | D08 KPI | Cập nhật achievement, trend |
| `kpi.below_threshold` (mã code `execution.kpi_below_threshold`) | KPI dưới ngưỡng cảnh báo | D08 KPI | UC-03 KPI underperformance |
| `okr.at_risk` (mã code `execution.okr_at_risk`) | KR/OKR có rủi ro không đạt | D09 OKR | UC-04 OKR at risk |
| `task.overdue` (mã code `execution.task_overdue`) | Task quá hạn | D11 Task | Nhắc việc, escalation, metric thực thi |
| `document.committed` (mã code `idp.document_committed`) | `commit_extraction` ghi thành công | D03 IDP | Cập nhật domain đích, lineage |
| `meeting.summarized` | Biên bản họp được tóm tắt | D12 Meeting | UC-02/UC-06 meeting → execution |
| `decision.logged` | Ghi Decision Log (`log_decision`) | D28 Decision Log | Đo North Star, đối chiếu 30/60/90 ngày (FR-DEC-02) |
| `risk.detected` | Rủi ro tự sinh từ event/ngưỡng | D25 Risk (P1) | BO-10 phát hiện rủi ro sớm (backlog phần nâng cao) |
| `hr.org_structure_changed` *(M1.2, đề xuất R-DEC-35)* | Tạo/sửa/archive Organization, Department, Team, Position, EmployeeAssignment (EP-ORG-02..23, EP-HR-02/04/05) | D01 Organization | Payload `{entity, entity_id, change ∈ created/updated/archived, department_id?, employee_id?, valid_from?}` — chỉ mã tham chiếu. Consumer M1.2: chưa có (relay + webhook NFR-INT-01); dự kiến consumer metric headcount/cache phạm vi (M2.1) |
| `auth.user_access_changed` *(M1.2, đề xuất R-DEC-35)* | Tạo user, đổi role/`scope_pillars`, khóa/mở (EP-ADM-06/08/09/10) | D02 Admin & Security | Payload `{user_id, change ∈ created/role_changed/deactivated/reactivated, role_code}` — không email/tên. Consumer M1.2: chưa có (audit bảo mật/AI Observe sau) |
| `execution.task_created` *(M1.3, đề xuất R-DEC-47; BRD `task.created`)* | Tạo task (EP-TASK-02, `ACT-create_task`, seed không phát) | D11 Task | Payload `{task_id, assignee_id?, department_id?, project_id?, parent_task_id?, due_date?, task_source, source_ref_kind?}` — chỉ mã tham chiếu, không `title`. Consumer M1.3: `platform.on_execution_event` (thêm vào `AFFECTS` → recompute `execution`: METRIC-OPS-01/HR-03). Notification **không** qua consumer (ghi in-tx, R-DEC-46) |
| `execution.task_overdue` *(đã có; M1.3 xác minh; BRD `task.overdue`)* | Job beat `app.jobs.detect_overdue_tasks` **08:30 `Asia/Ho_Chi_Minh`** (đã xác minh `worker.py`), một lần/task tới khi đổi `due_date` (`overdue_notified_at`) | D11 Task | Payload giữ v2.1 `{task_id, assignee_id, department_id, due_date}` + **thêm** `days_late` (thêm field không phá consumer — không cần `_v2`). Consumer giữ `platform.on_execution_event`. M1.3: job tạo notification `reminder` cùng tx (R-DEC-46) |
| `execution.task_completed` *(M1.3, đề xuất R-DEC-47; BRD `task.completed`)* | Task chuyển sang `done` (EP-TASK-04, hook, AI); reopen `done → in_progress` **không** phát event riêng (audit đủ) | D11 Task | Payload `{task_id, assignee_id?, department_id?, project_id?, due_date?, done_at, on_time: bool}`. Consumer: `platform.on_execution_event` (OPS-01/OPS-02). Re-done sau reopen phát lại (consumer metric idempotent theo `event_id`, recompute toàn kỳ nên không nhân đôi) |
| `platform.approval_requested` *(M1.3 — phát outbox; đã có trong registry; BRD `approval.requested`)* | `ApprovalService.create_*` (AI action L2 tài chính, EP-TASK-19) | D04 Workflow | Payload `{approval_request_id, rule_code, target_kind, target_id?, department_id?, step, due_at}`. Consumer M1.3: chưa có (notification in-tx); dự kiến AI Observe/escalation SLA M3.2 |
| `platform.approval_decided` *(M1.3 — phát outbox; đã có trong registry; BRD `approval.decided`)* | EP-WF-03 mỗi bước | D04 Workflow | Payload `{approval_request_id, rule_code, target_kind, decision, step, status}`. Consumer M1.3: chưa có |
| `execution.kpi_measured` *(M1.4, đề xuất R-DEC-56; BRD `kpi.measured`; **đã có**, mở rộng payload)* | `execution` — EP-KPI-07, EP-PRF-04, `ACT-record_kpi_measurement`; seed không phát | D08 KPI / D09 OKR / D10 | Payload `{kpi_id, kpi_code, period_key, measurement_id, actual_value, target, achievement_pct, band, previous_band, department_id, data_source}`. Consumer: `platform.on_goal_event` → recompute provider `execution` (metric G2 + SEI, 05 §2.6). Payload v2.1 giữ nguyên field cũ, thêm field mới (R-DEC-56) |
| `execution.kpi_below_threshold` *(M1.4, đề xuất R-DEC-56; BRD `kpi.below_threshold`)* | `execution` — khi `KPIEvaluation.band` của kỳ **chuyển vào** `BELOW`/`CRITICAL` từ band tốt hơn hoặc lần đầu (không phát lại nếu vẫn ở band dưới; đo lại lên `NEAR+` rồi xuống → phát lại) | D08 KPI / D09 OKR / D10 | Payload `{kpi_id, kpi_code, period_key, evaluation_id, achievement_pct, band, previous_band, gap_value, owner_id, department_id}`. Consumer: `execution.on_goal_alert` → Notification kind `alert` (R-DEC-59) cho owner KPI + MGR/DIR phụ trách phòng ban (`AuthService.find_user_by_role`), `link=/goals/kpis/{id}`, `ref=execution.kpis/{id}`; dedupe theo `(kpi_id, period_key, band)`. Nguồn UC-03 (insight + ApprovalRequest nối M2.4/M3.x, không làm ở M1.4) |
| `execution.okr_checked_in` *(M1.4, đề xuất R-DEC-56; BRD `okr.checked_in`)* | `execution` — EP-PRF-02 (KR) và EP-PRF-04 (KPI) | D08 KPI / D09 OKR / D10 | Payload `{check_in_id, target_type: kr\|kpi, target_id, objective_id?, period_key, value, confidence, progress_pct?, previous_progress_pct?, user_id, department_id, on_time: bool}`. Consumer: `platform.on_goal_event` → recompute metric G2 (`METRIC-STR-01`). `user_id` là UUID (không PII); `on_time` theo quy tắc 05 §2.6 |
| `execution.okr_at_risk` *(M1.4, đề xuất R-DEC-56; BRD `okr.at_risk`)* | `execution` — sau check-in KR (hoặc job hằng ngày 07:00, 05 §2.6) khi KR **chuyển** `at_risk=false→true` | D08 KPI / D09 OKR / D10 | Payload `{key_result_id, objective_id, period_key, progress_pct, previous_progress_pct, expected_progress_pct, confidence, reasons: [declining\|low_confidence\|behind_plan], days_to_period_end, owner_id, department_id}`. Consumer: `execution.on_goal_alert` → Notification kind `alert` cho owner KR + owner Objective + MGR phòng ban, `link=/goals/objectives/{oid}?kr={id}`; dedupe theo `(key_result_id, period_key, ISO week)`. Điều kiện: lý do ∧ `days_to_period_end ≥ 21` (R-DEC-55). Sang `at_risk=false` không phát event (chỉ cập nhật cột). Nguồn UC-04; widget Executive ở M2.1 |
| `idp.document_committed` *(M1.5, R-DEC-67 — **sửa** payload)* | Tài liệu C1/C3/C5 chuyển `COMMITTED` (STP, EP-DC-08/16/23) — cùng transaction với ghi đích | D03 | Biết dữ liệu mới vào qua tài liệu (G3), DQ, gắn nguồn cho insight |
| `idp.document_rolled_back` *(M1.5, R-DEC-67 — **mới publish**, đã có registry)* | Undo EP-DC-24 thành công — sau khi đảo mọi ACT, cùng transaction | D03 | Gỡ insight/alert dựa trên bản ghi đã đảo; tính lại metric |
| `ai.policy_changed` *(M1.6, đề xuất R-DEC-77)* | Bật/tắt/sửa kill switch (EP-AI-13), sửa agent (EP-AI-17), tạo/sửa/xóa autonomy policy (EP-AI-19..21) | D26 AI Platform | Payload `{change ∈ kill_switch/agent/autonomy_policy, ref_id?, agent_code?, tool_name?, enabled?, mode?, level?}` — không PII, không `reason` tự do. Consumer M1.6: chưa có (relay + webhook NFR-INT-01); dự kiến M3.4 Evaluation Engine/AIAudit. Cache resolve_level **không** dựa event (đọc DB mỗi lượt) |
| `platform.onboarding_completed` *(M1.6, đề xuất R-DEC-77)* | EP-ADM-14 `action=finish` | D02 Admin | Payload `{started_at, completed_at, duration_minutes, within_one_day: bool, counts{departments, employees, users, kpis, objectives}}`. Consumer M1.6: chưa có; M2.1 dùng để bật Executive dashboard đầu tiên + metric time-to-value |

> Danh mục đầy đủ + cặp **publish/consume** chốt khi chi tiết hóa (R-DEC-09); `risk.detected` thuộc D25 (P1) nên chỉ liệt kê, chi tiết ở đợt sau. Tên event giữ convention BRD (`<entity>.<verb>`), ánh xạ sang `EVT-*` của `main` ở đợt code. Các dòng M1.2–M1.6 ghi **mã code** (`event_type` phát thật); ánh xạ tên BRD ↔ mã code ở bảng ngay dưới.

**Ánh xạ tên BRD/05 §7 ↔ mã event trong code (Spec lock M1.3–M1.6, R-DEC-47/56/77).** Code phát **duy nhất** mã registry `core/events/registry.py` dạng `<module>.<entity>_<verb>`; tên BRD `<entity>.<verb>` chỉ là nhãn khái niệm để truy nguyên — không phát song song hai tên.

| Tên BRD / khái niệm | Mã code (`event_type`) | Trạng thái registry |
|---|---|---|
| `invoice.created` | `finance.invoice_created` | `EVENT_TYPES` (có) |
| `task.created` · `task.completed` | `execution.task_created` · `execution.task_completed` | `EXTENSION_EVENT_TYPES` (thêm M1.3, R-DEC-47) |
| `task.overdue` | `execution.task_overdue` | `EVENT_TYPES` (có; M1.3 thêm `days_late`) |
| `approval.requested` · `approval.decided` | `platform.approval_requested` · `platform.approval_decided` | `EVENT_TYPES` (có; M1.3 bắt đầu publish) |
| `kpi.measured` | `execution.kpi_measured` | `EVENT_TYPES` (có; M1.4 mở rộng payload, R-DEC-56) |
| `kpi.below_threshold` | `execution.kpi_below_threshold` | `EXTENSION_EVENT_TYPES` (thêm M1.4) |
| `okr.checked_in` · `okr.at_risk` | `execution.okr_checked_in` · `execution.okr_at_risk` | `EXTENSION_EVENT_TYPES` (thêm M1.4) |
| `document.committed` · (undo) | `idp.document_committed` · `idp.document_rolled_back` | `EVENT_TYPES` (có; M1.5 sửa payload / bắt đầu publish, R-DEC-67) |
| `org.structure_changed` · `user.access_changed` | `hr.org_structure_changed` · `auth.user_access_changed` | `EXTENSION_EVENT_TYPES` (M1.2, R-DEC-35) |
| `policy.changed` · `onboarding.completed` | `ai.policy_changed` · `platform.onboarding_completed` | `EXTENSION_EVENT_TYPES` (thêm M1.6, R-DEC-77) |
| `meeting.summarized` · `decision.logged` · `risk.detected` | (chưa cấp — M2.3 / M2.x / P1) | — |

**Ghi chú publish/consume M1.3–M1.6:**
- **M1.3 — đặt tên (R-DEC-47):** 10 §9.2 giữ tên BRD `<entity>.<verb>` (`task.created`); mã trong code theo registry `core/events/registry.py` dạng `<module>.<entity>_<verb>` như `execution.task_overdue` có sẵn. `execution.task_created`, `execution.task_completed` thêm vào `EXTENSION_EVENT_TYPES` (cùng cơ chế R-DEC-35). `platform.approval_*` đã có trong `EVENT_TYPES` nhưng v2.1 chỉ audit — M1.3 bổ sung `publish_in_tx`.
- **M1.3 — không có tool/ACT mới.** `TOOL-assign_task` giữ L2 → action card (AI không tự giao lại người khác); chuyển task theo F5 do Manager bấm "Áp dụng" = EP-TASK-04 (người là actor).
- **M1.4 — quy ước tên (R-DEC-56, theo registry code `<module>.<entity>_<verb>` như R-DEC-47):** **tái dùng** `execution.kpi_measured` (đã có trong `EVENT_TYPES`, consumer `platform.on_execution_event` + catalog `refresh_on` đang dựa vào) với payload **mở rộng** (thêm field, không `_v2`); thêm mới `execution.kpi_below_threshold`, `execution.okr_checked_in`, `execution.okr_at_risk` vào `EXTENSION_EVENT_TYPES` (cùng cơ chế R-DEC-35). Tên BRD/05 §7 (`execution.kpi_measured`, `kpi.below_threshold`, `okr.checked_in`, `okr.at_risk`) chỉ dùng làm cột ánh xạ ở 10 §9.2 — **không** phát hai tên song song. Payload không PII (chỉ id/mã/số/band); `tenant_id` trong envelope; mọi event phát qua `publish_in_tx` cùng transaction với ghi dữ liệu; consumer dedupe `processed_events(event_id, consumer)`.
- **M1.4 — không thêm** event cho Strategy/StrategicObjective/KPITarget CRUD (chỉ audit). Consumer mới: `platform.on_goal_event` (mở rộng AFFECTS `execution.kpi_measured`/`execution.okr_checked_in` → `{"execution"}`) và `execution.on_goal_alert` (module `execution/events/consumers.py`, gọi public `NotificationService.create` trong transaction consumer). **Nhắc check-in tuần** (F4 bước 1) = beat job `execution.checkin_reminder` thứ Sáu 08:00 `Asia/Ho_Chi_Minh`, idempotent theo `(user_id, ISO week)`, Notification kind `reminder` "Check-in tuần: N KR của bạn" — không phát event.
- **M1.5:** payload `idp.document_committed` v1 (không PII, có `tenant_id` ở envelope): `{document_id, document_type, channel, kind, row_count, actions: [{action_name, count}], target_tables: ["hr.employees", …], committed_by, stp: bool, critical_field_count}`. Giữ tên field cũ (`document_id`, `document_type`, `actions`) → không cần `_v2`.
- Payload `idp.document_rolled_back`: `{document_id, document_type, channel, reverted_actions: [{action_name, count}], target_tables[], rolled_back_by, reason_code}` (không gửi `reason` tự do — có thể chứa PII).
- Event domain đích **do service đích phát** khi ACT chạy (không phát lại ở idp): `hr.org_structure_changed` (ACT-create_department/team/position/employee — 1 event/thực thể theo M1.2), `execution.kpi_measured` (ACT-record_kpi_measurement, payload mở rộng M1.4), `execution.okr_checked_in` (ACT-record_kr_checkin, T-629), `execution.task_created` (ACT-create_task, M1.3 T-621), `finance.invoice_created`. Undo đảo qua service đích → service đích phát event tương ứng (vd `hr.org_structure_changed` với `change=archived`).
- **Consumer mới** (Celery `acks_late`, dedupe `processed_events`):
  - `platform.capture_share` ← `idp.document_committed`, `idp.document_rolled_back`: upsert lại `METRIC-DQ-02` kỳ tháng (R-DEC-68).
  - `platform.dq_recompute` ← `idp.document_committed` (đã khai ở catalog METRIC-DQ-01, **giữ**) + **thêm** `idp.document_rolled_back`.
- Không consumer nào phát lại `idp.*`.
- **M1.6:** thêm `ai.policy_changed`, `platform.onboarding_completed` vào `core/events/registry.py` + 00 §4.5/skeleton (giống R-DEC-35). Tool call **không** phát event (khối lượng lớn; `ToolCallLog` là bằng chứng); AIAction executed/undone dùng event domain đích (`execution.task_created`…) do ACT phát.

## 10. Convention (giữ nhất quán nền `main`, không mâu thuẫn BRD)

Envelope `{data, meta?}` / `{error:{code,message,details}}`; phân trang `limit/offset/sort_by/order` (`meta.pagination = {total, limit, offset, has_next}`); `Idempotency-Key` **bắt buộc** cho POST tạo/hành động + mọi endpoint AI ghi; tiền **BIGINT + currency** (mặc định VND); tỷ lệ hậu tố `_pct` thang 0–100; thời gian ISO 8601 UTC có `Z`; mọi response `X-Request-Id` → log/audit/event `correlation_id` (P06). Mã lỗi: bảng **§1.4** (nguồn sự thật = `core/errors.py`, R-DEC-18).

## Open questions

- OQ-10-01: Tool naming — **ĐÃ CHỐT** (R-DEC-10): tên theo BRD snake_case (vd. `get_kpi_status`) + bảng ánh xạ sang `TOOL-*` registry `main` (43 tool) để truy nguyên.
- OQ-10-02: EP numbering — **ĐÃ CHỐT** (R-DEC-10): đánh số theo BRD (`EP-<DOMAIN>-NN`) + bảng ánh xạ sang EP-xx của `main`; path cụ thể gán ở đợt code (R-DEC-09).
- OQ-10-03: MCP server (FR-INT-04, P1) — ngoài MVP (P1 backlog, R-DEC-05); xác nhận phạm vi khi chi tiết hóa.
- OQ-10-04: Cặp publish/consume đầy đủ cho từng event P0 + ánh xạ `EVT-*` của `main` — hoãn sang đợt code (R-DEC-09); registry §9.2 chốt danh mục + domain nguồn.
- OQ-10-05: Kiểu/định dạng chi tiết 13 metadata tool (vd. enum `risk_level`, đơn vị `cost_estimate`) + danh sách mã lỗi `AI_*` đầy đủ — hoãn sang đợt code (R-DEC-09).
- OQ-10-06: Bảng ánh xạ 24 tool mẫu BRD ↔ 43 `TOOL-*` của `main` (1-1 hay 1-nhiều) — lập ở đợt code cùng Tool Registry chi tiết. **Đề xuất đóng (Spec lock M1.6):** §2.2 (R-DEC-70).
- *(Spec lock M1.3–M1.6)* OQ-10-04 **đề xuất đóng một phần:** publish/consume + ánh xạ tên BRD ↔ mã code cho event M1.2–M1.6 ở §9.2; còn `meeting.summarized`, `decision.logged`, `risk.detected` (M2.3/P1). OQ-10-05 **đề xuất đóng:** 13 metadata chi tiết ở §7.2.5 (R-DEC-70).
- OQ-10-07 (M1.3): Thêm claim JWT `employee_id` (R-DEC-41) — **phương án đề xuất — chọn nếu human duyệt: có**; token cũ thiếu claim rơi về so `user_id` (hẹp hơn, an toàn).
- OQ-10-08 (M1.3/M1.4): Không giữ alias path cũ `/execution/{tasks,projects,kpis,objectives,key-results,check-ins,initiatives}`, `/platform/approvals/{id}/decide` (R-DEC-40/58) — **phương án đề xuất — chọn nếu human duyệt: không alias** (chỉ test BE + `shared-types` dùng).
- OQ-10-09 (M1.5): Prefix `/lineage/*` (EP-DC-26) ngoài bảng §7.1 — **phương án đề xuất — chọn nếu human duyệt:** chấp nhận như prefix xuyên domain, route đặt ở module `idp` (`platform` không được import `idp`).
- OQ-10-10 (M1.6): Chuẩn hóa permission `TOOL-request_approval`/`TOOL-generate_report` (`dashboard:read` v2.1) sang domain workflow/reporting — **phương án đề xuất — chọn nếu human duyệt:** giữ ở M1, xử lý ở M2.4/M3.3 khi có EP-RPT.
- OQ-10-11 (M1.6): Tool ghi nhân sự (`upsert_employee`, phân công) cho AI — **phương án đề xuất — chọn nếu human duyệt: không ở P0** (Approval Matrix "thay đổi nhân sự: không cho phép"); hồ sơ NV chỉ qua import C5 có người duyệt.

## Version

- **Version:** 1.1.0 (current)
- **Last updated:** 2026-10-23
- **Maintainer:** @CyEyes
- **Change 1.3.0 (đề xuất — Spec lock M1.3–M1.6, chờ human duyệt):** §2.2 mới — ánh xạ tool BRD ↔ `TOOL-*` (R-DEC-70). §7.2 thêm §7.2.2 M1.3 (EP-TASK-01..19, EP-WF-01..03; path `/work/*`, `/workflow/*` — R-DEC-40..49; `projects.initiative_id` ở EP-TASK-09..12), §7.2.3 M1.4 (EP-STR-01..22, EP-KPI-01..10, EP-OKR-01..11, EP-PRF-01..06; path `/goals/*`, `/kpis/*`, `/objectives/*`, `/key-results/*` — R-DEC-50..59), §7.2.4 M1.5 (EP-DC-01..37, Action Registry v2 12 ACT — R-DEC-60..69; `ACT-create_employee` = `hr:write`), §7.2.5 M1.6 (EP-AI-01..23, EP-ADM-13/14, 13 metadata tool, 10 tool mới 43 → 53, `ACT-update_task`/`ACT-assign_task`, trần L2 — R-DEC-70..79). §9.2 thêm event theo mã registry code (`execution.task_created/_completed`, `execution.kpi_measured` mở rộng payload, `execution.kpi_below_threshold`, `execution.okr_checked_in`, `execution.okr_at_risk`, `idp.document_committed/_rolled_back`, `platform.approval_*`, `ai.policy_changed`, `platform.onboarding_completed`) + bảng ánh xạ tên BRD ↔ mã code (không phát song song). Open questions: đề xuất đóng OQ-10-05/06, đóng một phần OQ-10-04; thêm OQ-10-07..11.
- **Change 1.2.0 (đề xuất — Spec lock M1.2, R-DEC-29..36, chờ human duyệt bước S):** §7.2.1 bảng EP M1.2: EP-ORG-01..24 (organization/department/team/position/assignment CRUD + `GET /org/tree?as_of=`; giữ `/hr/departments` EP-81 — R-DEC-29; ghi cơ cấu `hr:admin` — R-DEC-30), EP-HR-01..05 (giữ `/hr/employees` EP-82 + nối phân công effective-dated), EP-ADM-05..12 (user admin `/platform/users` + deactivate/reactivate thu hồi refresh token, `/platform/roles`, audit-logs EP-52 thêm `from`/`to`/`actor_type`), EP-NTF-01..05 (inbox `(token)` của chính mình — R-DEC-31, read/read-all, preferences email — R-DEC-32). §9.2 thêm `hr.org_structure_changed`, `auth.user_access_changed` (R-DEC-35). Không thêm mã lỗi (§1.4 giữ nguyên).
- **Change 1.1.0 (human duyệt 2026-10-23 — Spec lock M1.1, R-DEC-15/18/19/21):** thêm §1.4 bảng mã lỗi phản chiếu `core/errors.py` (R-DEC-18; sửa 4 contract test hỏng); thêm `tenant_id` vào envelope event §9.1 + quy tắc tenant context (R-DEC-21); thêm §7.1 quy ước domain code/prefix path `EP-<DOMAIN>-NN` và §7.2 danh mục EP đã chốt (bắt đầu với EP-SYS-01, EP-ADM-01..04 ↔ EP-01/02/06/07/03 v2.1); §10 trỏ mã lỗi về §1.4.
- **Change 1.0.0 (promote):** Promote tài liệu AI-EOS lên CHÍNH THỨC Aureon v3; di chuyển vào vị trí docs chuẩn; v2.1 archived (docs/_archive/v2.1/).
- **Change 0.3.0:** Mở rộng lên **spec-level P0** — giải thích đầy đủ 13 metadata tool (bảng ý nghĩa mức contract); 4 phân loại tool kèm **quy tắc quyền/Autonomy/approval mỗi loại** (§3); thêm Agent & Orchestrator (thành phần AI Platform liên quan contract, agent P0 + tool chính, luồng §11.5, quyền agent ∩ người §4.4); **Autonomy & kill switch** (§5); danh mục **tool IDP** đầy đủ (tên + mục đích + loại + quyền, §6); **grounding contract SourceRef** (§8); **envelope event + danh mục event P0** kèm domain nguồn và mục đích Observe (§9); bổ sung OQ-10-04..06. Giữ R-DEC-09 (không EP-*/field DB/T-*/TC-* chi tiết).
- **Change 0.2.0:** Chốt Q1–Q6 (R-DEC-05..10) — cập nhật trạng thái quyết định, đóng OQ liên quan; phạm vi docs-first P0.
- **Change 0.1.0:** Viết lại 10 theo AI-EOS — API First, Tool Registry + 13 metadata + danh mục mẫu, phân loại READ/WRITE/APPROVAL/EXECUTION, agent BRD §11.4, tool IDP, EP theo 28 domain + ánh xạ `main`, convention giữ nền `main`, event backbone.
