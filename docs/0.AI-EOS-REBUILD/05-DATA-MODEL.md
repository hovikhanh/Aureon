# 05 — Data Model & Data Foundation (AI-EOS, nhánh `ai-eos`)

> **Nguồn chuẩn:** `_reference/SOURCE-BRD-v1.1.md` §13 (Data Foundation FR-DATA-01..08, entity §13.2, quan hệ §13.3), §5–§12 (entity theo domain).
> **Phụ thuộc:** 00, 01, 02, 04, `TRACEABILITY-SKELETON.md` §11, §4.1. **Trạng thái:** 🟡 draft (Phase R2). **Ngày:** 2026-10-22 · **Maintainer:** @CyEyes

---

## 1. Data Foundation (BRD §13.1, P0)

"One Source of Truth" thành hiện thực khi **mỗi entity có nguồn gốc chỉ định, có owner, có điểm chất lượng, truy ngược được đến tài liệu gốc**.

| Mã | Yêu cầu |
|---|---|
| FR-DATA-01 | **Master Data Management:** Employee, Customer, Partner, Vendor, Product, Project có nguồn gốc chỉ định, data owner, quy tắc khử trùng & hợp nhất bản ghi |
| FR-DATA-02 | **Data Quality Score** theo domain (đầy đủ/chính xác/kịp thời/nhất quán); AI cảnh báo khi kết luận dựa trên dữ liệu chất lượng thấp |
| FR-DATA-03 | **Data Freshness:** mọi chỉ số có thời điểm cập nhật cuối; Briefing nêu dữ liệu đã cũ |
| FR-DATA-04 | **Data Lineage:** từ con số truy ngược bản ghi, người nhập, lần sửa, trang tài liệu gốc |
| FR-DATA-05 | **Event backbone:** mọi thay đổi nghiệp vụ phát event (invoice.created, kpi.measured, task.overdue, document.committed) để AI quan sát real-time |
| FR-DATA-06 | **Metric Store / Semantic layer:** chỉ số định nghĩa một lần (công thức, nguồn, bộ lọc, owner), dùng chung dashboard/báo cáo/AI |
| FR-DATA-07 | **Lịch sử & thời điểm hiệu lực:** lưu lịch sử entity quan trọng để trả lời "tại thời điểm X thì sao" (effective-dated) |
| FR-DATA-08 | **Xuất dữ liệu:** doanh nghiệp xuất toàn bộ dữ liệu theo định dạng mở bất kỳ lúc nào |

## 2. Trường chung mọi bản ghi nghiệp vụ (BRD §13.3)

`tenant_id` (R-DEC-07: 1 tenant cho MVP nhưng có sẵn ở **mọi** business entity để nâng đa tenant sau) · `created_by` (người hoặc agent) · `source` ∈ {manual, document, integration, ai} · `source_document_id` · `data_classification` ∈ {Công khai, Nội bộ, Mật, Tuyệt mật} · `created_at` · `updated_at` · `version`.

> **`source` vs `*_source` (khác `main`):** `main`/DEC-154 đổi `source` → tên có hậu tố (`risk_source`, `data_source`…) để tránh trùng tên cột. Trên `ai-eos` giữ `source` theo BRD §13.3; việc có đổi sang quy ước hậu tố của `main` (khi tái dùng code) là **quyết định ở đợt code (R-DEC-09)**.

## 3. 13 nhóm entity (BRD §13.2)

| Nhóm | Entity |
|---|---|
| Tổ chức | Organization, BusinessUnit, Department, Team, Employee, Position, Role |
| Kinh doanh | Customer, Contact, Lead, Opportunity, Partner, Vendor, Contract, ContractObligation, PurchaseOrder |
| Sản phẩm & thực thi | Product, Feature, Project, Milestone, Task, Workload |
| Chiến lược | Strategy, StrategicPillar, StrategicObjective, Initiative |
| KPI | KPI, KPITarget, KPIMeasurement, KPIEvaluation, Metric |
| OKR | Objective, KeyResult, KRMeasurement |
| Hiệu suất | PerformanceCycle, PerformanceReview, CheckIn |
| Họp & quyết định | Meeting, MeetingTranscript, MeetingSummary, Decision, ActionItem |
| Rủi ro & tuân thủ | Risk, RiskAssessment, Mitigation, Policy, Control, Evidence, Finding |
| Tài chính | Budget, CostCenter, Revenue, Expense, Invoice, Payment, CashBalance |
| Tri thức | Document, Knowledge, Report |
| Data Capture | SourceDocument, DocumentPage, DocumentType, ExtractionSchema, ExtractionJob, ExtractedField, ExtractionReview, ValidationRule, ImportBatch, DataLineage |
| AI | AIAgent, AITool, AIToolCall, AIRecommendation, AIDecision, AIAudit, AIEvaluation, AIBudget |
| Workflow | Workflow, WorkflowStep, ApprovalRequest, Notification |

Tham chiếu `ENT-<Name>`. Field/kiểu/ràng buộc chi tiết chốt khi chi tiết hóa per-domain (giữ nguyên tắc: UUID id, created_at/updated_at, soft delete nghiệp vụ, index mọi FK — nhất quán `main` §5.7).

## 4. Quan hệ cốt lõi (BRD §13.3)

```text
Organization → Department → Team → Employee
Strategy → Strategic Objective → KPI/OKR → Initiative → Project → Task → Employee
Meeting → Decision → Action Item → Task → Deadline → Calendar
SourceDocument → ExtractionJob → ExtractedField → Review → Business Record (Invoice, Task, KPIMeasurement…)
Data → AI → Insight → Recommendation → Decision → Action → Measurement → Feedback
```

## 5. Phân vùng lưu trữ theo domain (ánh xạ sang schema)

AI-EOS 28 domain / 5 lớp, hiện thực hóa theo **R-DEC-06 (Modular Monolith)** + **R-DEC-10** (ID theo BRD + ánh xạ `main`): nhóm entity ánh xạ sang schema PostgreSQL theo domain. Bảng ánh xạ 13 nhóm → schema (đề xuất): org/admin → `platform`+`auth`; data capture → `idp`; AI → `ai`; workflow → `platform`; finance → `finance`; sales/customer/partner → `sales`; hr → `hr`; product/engineering → `product`; risk/governance → `risk`; strategy/kpi/okr/performance/meeting/task → `execution`; knowledge/report → `platform`/`dashboard`. Chi tiết schema chốt ở đợt code (R-DEC-09).

## 6. AI entity & grounding

Mọi con số AI đưa ra phải khớp một `AIToolCall` result hoặc `Metric`/`KPIMeasurement` (SourceRef) — grounding (FR-AIQ-01). `AIToolCall`, `AIAudit`, `AIDecision`, `AIRecommendation`, `AIEvaluation`, `AIBudget` ghi đủ cho audit AI (02 §9). `DataLineage` nối Business Record → ExtractedField → SourceDocument/trang.

## 7. Event backbone (FR-DATA-05)

Event mẫu: `invoice.created`, `kpi.measured`, `task.overdue`, `document.committed`, `kpi.below_threshold`, `okr.at_risk`, `risk.detected`. Envelope: `event_id, event_type, occurred_at, version, correlation_id, payload` (không PII). Danh mục event đầy đủ chốt ở 10 §8.

## 8. Open questions
- OQ-05-01: Quy ước `source` (BRD) vs hậu tố `*_source` (DEC-154 `main`) — giữ `source` theo BRD ở docs; chốt quy ước cột khi tái dùng code ở đợt code (R-DEC-09).
- OQ-05-02: Tập entity chính xác cho MVP P0 (tập con của §13.2) — theo R-DEC-05 (phủ tập P0); danh sách entity cụ thể chi tiết hóa ở đợt code (R-DEC-09).
- OQ-05-03: effective-dated (FR-DATA-07) cho entity nào ở MVP (ít nhất Organization theo FR-ORG-04) — phạm vi cụ thể chốt ở đợt code (R-DEC-09).

## Version
- **Version:** 0.2.0 (draft, Phase R2)
- **Last updated:** 2026-10-22
- **Maintainer:** @CyEyes
- **Change 0.2.0:** Chốt Q1–Q6 (R-DEC-05..10) — cập nhật trạng thái quyết định, đóng OQ liên quan; phạm vi docs-first P0.
- **Change 0.1.0:** Viết lại 05 theo AI-EOS — Data Foundation FR-DATA-01..08, trường chung, 13 nhóm entity BRD §13.2, quan hệ cốt lõi, ánh xạ nhóm→schema, AI entity/grounding, event backbone.
