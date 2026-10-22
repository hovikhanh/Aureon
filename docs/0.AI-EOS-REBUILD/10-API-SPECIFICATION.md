# 10 — API & Tool Registry Spec (AI-EOS, nhánh `ai-eos`)

> **Nguồn chuẩn:** `_reference/SOURCE-BRD-v1.1.md` §11.2 (Tool Registry + metadata), §11.3 (phân loại tool), §11.4 (agent), §6.10 (tool IDP); §16 NFR-INT-01, §13 FR-DATA-05 (event).
> **Phụ thuộc:** 00, 01, 02, 05, 07. **Trạng thái:** 🟡 draft (Phase R2). **Ngày:** 2026-10-22 · **Maintainer:** @CyEyes

---

## 1. Nguyên tắc API (P02 API First)

Mọi năng lực nghiệp vụ expose qua **API + tool**; UI dùng chính các API này. API **có phiên bản** + webhook cho event (NFR-INT-01). AI gọi nghiệp vụ **chỉ qua tool đã đăng ký** (AI-R02) — không truy cập DB trực tiếp (07 §1).

## 2. Tool Registry (BRD §11.2)

Mọi năng lực expose dưới dạng **tool**. Ví dụ danh mục (BRD §11.2):

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

### 2.1. Metadata bắt buộc mỗi tool (13 thuộc tính)
`name, description, input_schema, output_schema, permission, risk_level, data_scope, data_classification, autonomy_level mặc định, approval_required, reversible, audit_required, cost_estimate, owner`.

## 3. Phân loại tool (BRD §11.3)

| Loại | Ý nghĩa | Ví dụ |
|---|---|---|
| READ | Không thay đổi dữ liệu | get_sales_pipeline, get_kpi_status, extract_document |
| WRITE | Thay đổi dữ liệu nội bộ | create_task, update_task, commit_extraction |
| APPROVAL | Thực hiện quyền phê duyệt | approve_budget, approve_hiring (**AI không được tự gọi**) |
| EXECUTION | Tác động ra ngoài | send_email, send_customer_message, create_calendar_event (khách ngoài) |

Quyền + Autonomy + approval theo Approval Matrix (02 §7). Tool ghi kiểm **cả quyền agent ∩ người** (07 §3).

## 4. Agent (BRD §11.4)

| Agent | Ưu tiên |
|---|---|
| CEO, Data Capture, Performance, Task, Meeting, Reporting | P0 |
| Finance, Sales | P0 Lite / P1 |
| HR, Product, Engineering, Procurement | P1 |
| Strategy, Risk, Governance | P1/P2 |

AI Orchestrator chọn agent theo ý định; agent có Identity/Role/Permission/Scope/Tools/Policies/Budget/Audit (ROLE-AI, 02 §2).

## 5. Tool IDP (D03, BRD §6.10)

`upload_document, classify_document, extract_document, validate_extraction, submit_extraction_for_review, approve_extraction, commit_extraction, import_table, search_documents, get_source_document`. classify/extract/validate = READ; `commit_extraction` = WRITE (kế thừa risk_level tool đích). IDP **không tool calling** (04 §9).

## 6. Endpoint theo domain

API path `/api/v1/<domain>/<resource>`. EP theo 28 domain (D01–D28) — chi tiết hóa theo phase (MVP: Organization, Admin&Security, Data Capture, Strategy/KPI/OKR, Task/Project, Meeting, Calendar, Finance Lite, Sales Lite, CEO Assistant, Reporting, Decision Log).

> **Khác `main`:** `main` có EP-01..119 cố định cho 11 module. AI-EOS đánh EP theo 28 domain; bảng ánh xạ EP `main` ↔ AI-EOS khi quyết Q6. Giữ envelope/phân trang/mã lỗi/Idempotency-Key của `main` làm quy ước triển khai (nhất quán, không mâu thuẫn BRD).

## 7. Convention (giữ nhất quán nền `main`, không mâu thuẫn BRD)
Envelope `{data, meta?}` / `{error:{code,message,details}}`; phân trang `limit/offset/sort_by/order`; `Idempotency-Key` bắt buộc cho POST tạo/hành động + endpoint AI ghi; tiền BIGINT + currency; thời gian ISO 8601 UTC; mọi response `X-Request-Id` → log/audit/event `correlation_id`.

## 8. Event backbone (FR-DATA-05)

Event nghiệp vụ: `invoice.created, kpi.measured, kpi.below_threshold, task.overdue, document.committed, okr.at_risk, risk.detected, meeting.summarized, decision.logged`… Envelope `{event_id, event_type, occurred_at, version, correlation_id, payload}` (không PII). Danh mục đầy đủ + cặp publish/consume chốt khi chi tiết hóa.

## 9. Open questions
- OQ-10-01: Tool naming — snake_case BRD (`get_kpi_status`) vs `TOOL-*` registry `main` (43 tool) → giữ cả hai + ánh xạ? (Q6)
- OQ-10-02: EP numbering AI-EOS vs EP-xx `main` (Q6).
- OQ-10-03: MCP server (FR-INT-04, P1) — trong/ngoài MVP.

## Version
- **Version:** 0.1.0 (draft, Phase R2)
- **Last updated:** 2026-10-22
- **Maintainer:** @CyEyes
- **Change 0.1.0:** Viết lại 10 theo AI-EOS — API First, Tool Registry + 13 metadata + danh mục mẫu, phân loại READ/WRITE/APPROVAL/EXECUTION, agent BRD §11.4, tool IDP, EP theo 28 domain + ánh xạ `main`, convention giữ nền `main`, event backbone.
