# 05 — Data Model & Data Foundation (Aureon v3 — AI-EOS)

> **Nguồn chuẩn:** `_reference/SOURCE-BRD-v1.1.md` §13 (Data Foundation FR-DATA-01..08, entity §13.2, quan hệ §13.3), §5–§12 (entity theo domain).
> **Phụ thuộc:** 00, 01, 02, 04, `TRACEABILITY-SKELETON.md` §11, §4.1. **Trạng thái:** ✅ current — Aureon v3 (AI-EOS) CHÍNH THỨC. **Ngày:** 2026-10-23 · **Maintainer:** @CyEyes
> Tài liệu chính thức v3, tách từ Aureon v2.1 (nay archived ở `docs/_archive/v2.1/`).

---

## 1. Data Foundation (BRD §13.1, P0)

"One Source of Truth" thành hiện thực khi **mỗi entity có nguồn gốc chỉ định, có owner, có điểm chất lượng, truy ngược được đến tài liệu gốc**. Data Foundation là lớp nền của AI-EOS: nó bảo đảm mọi con số AI đưa ra đều kiểm chứng được (BRD-P05 không bịa số, BRD-P01 mọi con số có nguồn), và là điều kiện của mục tiêu kinh doanh BO-07 (bộ nhớ doanh nghiệp ≥90%), BO-09 (Data Quality ≥90/100) trong `TRACEABILITY-SKELETON.md` §3.

Mỗi FR-DATA dưới đây mô tả hành vi + tiêu chí chấp nhận mức sản phẩm (field-level — tên cột/kiểu/constraint — chốt ở đợt code theo **R-DEC-09**):

| Mã | Yêu cầu | Hành vi & tiêu chí chấp nhận (mức sản phẩm, P0) |
|---|---|---|
| FR-DATA-01 | **Master Data Management (MDM)** | 6 master entity — Employee, Customer, Partner, Vendor, Product, Project — mỗi bản ghi có **nguồn gốc chỉ định** (`source` ∈ {manual, document, integration, ai}) và **data owner** (một người/role chịu trách nhiệm). Hệ thống phát hiện bản ghi nghi trùng theo khóa nghiệp vụ (ví dụ MST/email/mã NV) và đề xuất khử trùng/hợp nhất; hợp nhất là hành động có duyệt, ghi lineage. **Tiêu chí:** không có master entity thiếu owner; mọi lần hợp nhất lưu được bản ghi trước/sau và người quyết. Thuật toán khử trùng cụ thể + khóa trùng chi tiết hóa ở đợt code (R-DEC-09). |
| FR-DATA-02 | **Data Quality Score (DQ Score)** | Mỗi domain có điểm chất lượng tổng hợp từ 4 chiều: **đầy đủ** (completeness), **chính xác** (accuracy), **kịp thời** (timeliness), **nhất quán** (consistency). Ngưỡng cảnh báo < 80/100 (chỉ số Dữ liệu, skeleton §10); AI gắn cảnh báo khi một kết luận dựa trên domain có DQ thấp. **Tiêu chí:** DQ Score hiển thị được per-domain; Briefing/insight nêu rõ khi dữ liệu nền có DQ < ngưỡng. Công thức chi tiết 4 chiều → `METRIC-DQ-*` cấp ở 03. |
| FR-DATA-03 | **Data Freshness** | Mọi chỉ số/metric mang **thời điểm cập nhật cuối** (`last_refreshed_at` mức khái niệm). Nếu quá ngưỡng tươi của domain thì đánh dấu "dữ liệu cũ"; UC-01 Morning Briefing **nêu rõ** dữ liệu nào đã cũ. **Tiêu chí:** không có metric thiếu mốc cập nhật; nhãn độ tươi hiển thị ở ô chỉ số (SOURCE-UIUX U3). Ngưỡng tươi per-domain = cấu hình. |
| FR-DATA-04 | **Data Lineage** | Từ một con số trên dashboard/báo cáo truy ngược được: **bản ghi nghiệp vụ → người/agent nhập → các lần sửa (version) → trang tài liệu gốc**. `ENT-DataLineage` nối Business Record ↔ ExtractedField ↔ SourceDocument/DocumentPage. **Tiêu chí (US-CEO-007 P0):** mọi con số click được mở nguồn ≤ 3 bước tới tài liệu gốc; con số ngoài scope role trả `{ restricted: true, reason }` (đồng bộ 02). Khi nguồn mâu thuẫn → hiển thị cả hai, người chọn, ghi vào lineage (SOURCE-UIUX). |
| FR-DATA-05 | **Event backbone** | Mọi thay đổi nghiệp vụ phát một **domain event** (ví dụ `invoice.created`, `kpi.measured`, `task.overdue`, `document.committed`) để AI quan sát real-time và kích hoạt insight/alert. Event phát **cùng transaction** với ghi dữ liệu (nguyên tắc outbox — hiện thực chốt ở 07/10). **Tiêu chí:** không mất event khi rollback; payload **không chứa PII**; mỗi event có `correlation_id` truy được về request/lineage. Danh mục event đầy đủ ở §7 + 10 §8. |
| FR-DATA-06 | **Metric Store / Semantic layer** | Mỗi chỉ số **định nghĩa một lần** (công thức, nguồn, bộ lọc, owner, đơn vị, hướng tốt/xấu) và dùng chung cho dashboard, báo cáo, AI — tránh "mỗi nơi một công thức". KPI tham chiếu công thức trong Metric Store (BRD §8 "Formula (tham chiếu Metric Store)"). **Tiêu chí:** một chỉ số = một định nghĩa; dashboard, Report và AI tool đọc cùng giá trị; mọi metric có `lineage_url`. Xem §6bis. |
| FR-DATA-07 | **Lịch sử & thời điểm hiệu lực (effective-dated)** | Lưu lịch sử thay đổi của entity quan trọng để trả lời "tại thời điểm X thì sao" (ví dụ cơ cấu tổ chức tại quý trước, KPI target đã đổi). P0 tối thiểu áp cho Organization/cơ cấu (bám FR-ORG-04) và KPITarget; mở rộng chốt ở đợt code. **Tiêu chí:** truy vấn được trạng thái entity theo một mốc thời gian quá khứ. Xem §6ter. |
| FR-DATA-08 | **Xuất dữ liệu** | Doanh nghiệp xuất được **toàn bộ dữ liệu của mình** theo định dạng mở (ví dụ CSV/JSON/Excel) bất kỳ lúc nào — chống khóa nhà cung cấp. **Tiêu chí:** phạm vi xuất tôn trọng RBAC/data scope + mask dữ liệu nhạy cảm theo người yêu cầu; bản xuất kèm metadata nguồn khi có. Định dạng/endpoint cụ thể ở 10 (đợt code). |

## 2. Trường chung mọi bản ghi nghiệp vụ (BRD §13.3)

`tenant_id` (R-DEC-07: 1 tenant cho MVP nhưng có sẵn ở **mọi** business entity để nâng đa tenant sau) · `created_by` (người hoặc agent) · `source` ∈ {manual, document, integration, ai} · `source_document_id` · `data_classification` ∈ {Công khai, Nội bộ, Mật, Tuyệt mật} · `created_at` · `updated_at` · `version`.

> **`source` vs `*_source` (khác `main`):** `main`/DEC-154 đổi `source` → tên có hậu tố (`risk_source`, `data_source`…) để tránh trùng tên cột. Ở Aureon v3 (AI-EOS) giữ `source` theo BRD §13.3; việc có đổi sang quy ước hậu tố của `main` (khi tái dùng code) là **quyết định ở đợt code (R-DEC-09)**.

### 2.1. Data classification per nhóm entity (mức sản phẩm)

`data_classification` ∈ {Công khai, Nội bộ, Mật, Tuyệt mật} (BRD §13.3) quyết định quyền đọc, mask AI/log, và chính sách LLM (đồng bộ 02/07). Gán mặc định theo nhóm; override per-field chốt ở đợt code (R-DEC-09):

| Nhóm entity | Classification mặc định | Ghi chú nghiệp vụ |
|---|---|---|
| Tổ chức (lương, ngày sinh, địa chỉ, CCCD của Employee) | **Tuyệt mật** (trường nhạy cảm) / Nội bộ (phần còn lại) | Trường mức cao chỉ ROLE-CEO/HR phụ trách; mask trong audit, event payload, prompt LLM |
| Tài chính (Revenue, Expense, Invoice, Payment, CashBalance, Budget) | **Mật** | Số tiền là "trường trọng yếu" IDP — luôn qua người duyệt |
| Kinh doanh (Customer, Lead, Opportunity, Contract) | Mật / Nội bộ | Giá trị hợp đồng, MST là trường trọng yếu |
| Rủi ro & tuân thủ (Risk, Finding, Evidence) | **Mật** | Phát hiện/bằng chứng nhạy cảm |
| KPI / OKR / Hiệu suất | Nội bộ | PerformanceReview có phần Mật |
| Sản phẩm & thực thi, Chiến lược, Họp & quyết định, Tri thức | Nội bộ | MeetingTranscript có thể chứa Mật |
| Data Capture, AI, Workflow | Nội bộ | SourceDocument kế thừa classification của nội dung |

> Nguyên tắc classification (đồng bộ CLAUDE.md §2.2): Công khai/Nội bộ → có thể dùng cloud LLM; Mật → LLM local; Tuyệt mật → không đưa vào LLM. Hiện thực chính sách ở 07 (đợt code).

### 2.2. Field-level đợt code — Phase 1 (R-DEC-12, R-DEC-13)

> Chốt ở đợt code (R-DEC-09) khi refactor nền v2.1 → model v3. Áp cho hiện thực SQLAlchemy/Alembic; migration reversible.

**`tenant_id` (R-DEC-13):** `tenant_id UUID NOT NULL`, mặc định một tenant hệ thống cố định ở MVP (single-tenant), có ở **mọi business entity** (thêm qua `TenantMixin`, gộp vào `BusinessModel`); index theo `tenant_id`. Repository lọc `tenant_id` của principal; JWT mang claim `tenant_id`; backfill tenant mặc định cho dữ liệu hiện có khi migrate.

**`auth.role_code` enum (R-DEC-12):** 7 giá trị BRD + AI Agent (thay 10 giá trị F.O.C.U.S của nền v2.1):

| role_code (v3) | ROLE-* | Gộp từ 10 code F.O.C.U.S | Phân biệt scope |
|---|---|---|---|
| `CEO` | ROLE-CEO | CEO | Toàn doanh nghiệp |
| `DIR` | ROLE-DIR | CFO, VP_SALES, HR_MANAGER, CPO, RISK_MANAGER | Theo `department_id` + data scope (ABAC) |
| `MGR` | ROLE-MGR | MANAGER | Team |
| `EMP` | ROLE-EMP | EMPLOYEE | Cá nhân & việc được giao |
| `REV` | ROLE-REV | REVIEWER | Hàng chờ review được phân |
| `ADM` | ROLE-ADM | ADMIN | Cấu hình nền tảng (không mặc định đọc bản ghi nghiệp vụ) |
| `AI` | ROLE-AI | (mới — actor) | Quyền agent ∩ người được phục vụ |

- `DIR.permissions[]` = hợp quyền của 5 C-level cũ (ma trận: `auth/permission_matrix.py`, sinh từ 02 §5.3), **thu hẹp theo khối** bằng `auth.users.scope_pillars PILLAR[]` (R-DEC-12a, chống leo quyền): tập con ⊆ {F,O,C,U,S}; rỗng = không lọc (CEO, non-DIR). Tầng kiểm quyền ánh xạ domain↔pillar (finance↔F, hr↔O, sales↔C, product↔U, risk↔S; execution/idp/ai/dashboard/platform cross-pillar — không lọc) và từ chối domain nếu pillar ∉ `scope_pillars`. Phạm vi **hàng** vẫn thu hẹp bằng `department_id`/ownership (02 §5–§6).
- `scope_pillars` vào claim JWT + `Principal`; effective-dated không áp (thuộc identity).
- Giữ **bảng ánh xạ** 10→7 (R-DEC-08) ở `TRACEABILITY-SKELETON.md` §12 để truy nguyên test/seed nền v2.1.

## 3. 13 nhóm entity (BRD §13.2)

Mỗi nhóm nêu **vai trò nghiệp vụ**, **entity P0 chính** (tập con phục vụ domain P0 trong `TRACEABILITY-SKELETON.md` §12bis), và **liên kết lineage/event** chính. Tham chiếu `ENT-<Name>`. Field/kiểu/ràng buộc chi tiết chốt khi chi tiết hóa per-domain (R-DEC-09; giữ nguyên tắc: UUID id, created_at/updated_at, soft delete nghiệp vụ, index mọi FK — nhất quán `main` §5.7).

| Nhóm | Entity (đầy đủ BRD §13.2) | Vai trò nghiệp vụ | Entity P0 chính | Lineage / Event chính |
|---|---|---|---|---|
| Tổ chức | Organization, BusinessUnit, Department, Team, Employee, Position, Role | Khung tổ chức & con người — nền của scope RBAC và data ownership (D01) | Organization, Department, Team, Employee, Position, Role | effective-dated cho cơ cấu (FR-ORG-04); Employee là đích khớp tên trong UC-02/UC-06 |
| Kinh doanh | Customer, Contact, Lead, Opportunity, Partner, Vendor, Contract, ContractObligation, PurchaseOrder | Quan hệ khách hàng/đối tác & pipeline bán hàng (D17 Sales Lite P0; D18–D21 P1) | Lead, Opportunity (Sales Lite); Customer cơ bản | `opportunity.*` → Metric Store (pipeline coverage, win rate); phần lớn P1 |
| Sản phẩm & thực thi | Product, Feature, Project, Milestone, Task, Workload | Chuyển chiến lược thành việc thực thi được đo (D11 P0) | Project, Milestone, Task, Workload | `task.overdue`, `task.created`; Task là đích của Decision→ActionItem và của IDP commit |
| Chiến lược | Strategy, StrategicPillar, StrategicObjective, Initiative | Cây mục tiêu chiến lược, liên kết chiến lược↔thực thi (D07 cơ bản P0) | Strategy, StrategicObjective, Initiative | Strategy Execution Index (chỉ số, skeleton §10); liên kết tới KPI/OKR |
| KPI | KPI, KPITarget, KPIMeasurement, KPIEvaluation, Metric | Đo lường hiệu quả theo mục tiêu (D08 P0) | KPI, KPITarget, KPIMeasurement, KPIEvaluation, Metric | `kpi.measured`, `kpi.below_threshold`; KPIMeasurement là SourceRef cho grounding AI |
| OKR | Objective, KeyResult, KRMeasurement | Mục tiêu & kết quả then chốt theo chu kỳ (D09 P0) | Objective, KeyResult, KRMeasurement | `okr.at_risk` (UC-04); KRMeasurement là nguồn grounding |
| Hiệu suất | PerformanceCycle, PerformanceReview, CheckIn | Theo dõi hiệu suất qua check-in (D10 check-in P0, review P1) | CheckIn (P0); PerformanceCycle | CheckIn phát event feed hiệu suất; PerformanceReview chứa trường Mật |
| Họp & quyết định | Meeting, MeetingTranscript, MeetingSummary, Decision, ActionItem | Biến họp/transcript thành quyết định & việc (D12 từ transcript P0) | Meeting, MeetingTranscript, MeetingSummary, Decision, ActionItem | UC-02/UC-06: Transcript → Summary → Decision → ActionItem → Task; `document.committed` |
| Rủi ro & tuân thủ | Risk, RiskAssessment, Mitigation, Policy, Control, Evidence, Finding | Nhận diện & giảm thiểu rủi ro, lưu bằng chứng (D25 Risk P1, D24 Governance P2) | (P1 — ghi backlog 09) | `risk.detected` (observe từ event khác); Evidence nối lineage tới SourceDocument |
| Tài chính | Budget, CostCenter, Revenue, Expense, Invoice, Payment, CashBalance | Dòng tiền, công nợ, ngân sách (D15 Finance Lite P0) | Invoice, Payment, Revenue, Expense, CashBalance, Budget (Lite) | `invoice.created`; Invoice là đích IDP commit (UC-08 P1); số tiền = trường trọng yếu |
| Tri thức | Document, Knowledge, Report | Bộ nhớ doanh nghiệp & báo cáo (D14 Knowledge, D28 Reporting cơ bản P0) | Document, Report (Knowledge/RAG tối thiểu) | Report dùng số từ Metric Store + trích dẫn lineage (FR-RPT-02) |
| Data Capture | SourceDocument, DocumentPage, DocumentType, ExtractionSchema, ExtractionJob, ExtractedField, ExtractionReview, ValidationRule, ImportBatch, DataLineage | Nhập liệu không ma sát → trích xuất → review → ghi (D03 P0, chi tiết ở 04) | Toàn bộ (lõi IDP P0) | **Nguồn gốc của mọi lineage**: SourceDocument→ExtractionJob→ExtractedField→Review→Business Record; `document.committed` |
| AI | AIAgent, AITool, AIToolCall, AIRecommendation, AIDecision, AIAudit, AIEvaluation, AIBudget | Hạ tầng AI có thể audit & kiểm chi phí (D26 P0, chi tiết 02 §9/07) | AIAgent, AITool, AIToolCall, AIRecommendation, AIDecision, AIAudit, AIEvaluation, AIBudget | AIToolCall.result là SourceRef cho grounding (FR-AIQ-01); AIDecision/AIAudit cho autonomy L0–L3 |
| Workflow | Workflow, WorkflowStep, ApprovalRequest, Notification | Duyệt & thông báo (D04 cơ bản + D05 P0) | ApprovalRequest, Notification (Workflow cơ bản) | ApprovalRequest gắn autonomy L2 (chờ xác nhận); Notification là đích của alert/event |

## 4. Quan hệ cốt lõi (BRD §13.3)

Sơ đồ khái niệm dưới đây mô tả 5 chuỗi quan hệ cốt lõi với **cardinality mức khái niệm** (`1` = một, `N`/`*` = nhiều); cardinality & khóa chi tiết chốt ở đợt code (R-DEC-09):

```text
[1] Cây tổ chức (effective-dated — FR-DATA-07/FR-ORG-04)
Organization 1─N Department 1─N Team 1─N Employee
                                   Employee N─1 Position
                                   Employee N─1 Role

[2] Chiến lược → thực thi (liên kết chiến lược↔thực thi — BO-03)
Strategy 1─N StrategicObjective 1─N {KPI | OKR}
StrategicObjective 1─N Initiative 1─N Project 1─N Task N─1 Employee
KPI 1─N KPITarget ; KPI 1─N KPIMeasurement ; Objective 1─N KeyResult 1─N KRMeasurement

[3] Họp → quyết định → việc (UC-02 / UC-06)
Meeting 1─1 MeetingTranscript 1─1 MeetingSummary
Meeting 1─N Decision 1─N ActionItem 1─1 Task ──► Deadline ──► Calendar

[4] Data Capture → bản ghi nghiệp vụ (lineage — FR-DATA-04)
SourceDocument 1─N DocumentPage
SourceDocument 1─N ExtractionJob 1─N ExtractedField N─1 ExtractionReview
ExtractedField ──► (qua Review, 1 txn/tài liệu) ──► BusinessRecord {Invoice | Task | KPIMeasurement | ...}
DataLineage N─1 BusinessRecord ; DataLineage N─1 ExtractedField ; DataLineage N─1 DocumentPage

[5] Vòng lặp AI (AI Operating Loop — BRD §17.5)
Data ──► AI(Insight) ──► Recommendation ──► Decision ──► Action ──► Measurement ──► Feedback
AIToolCall 1─1 (result = SourceRef) ──► {Metric | KPIMeasurement}   # grounding FR-AIQ-01
```

**Giải thích chuỗi lineage (trọng tâm P0):** một con số trên dashboard (ví dụ Doanh thu T9) trỏ tới một `Metric`/`KPIMeasurement`; giá trị đó lần ngược qua `DataLineage` về `BusinessRecord` (Invoice/Revenue) → `ExtractedField` (nếu nhập từ tài liệu) → `DocumentPage` của `SourceDocument`, kèm người/agent nhập và lịch sử `version`. Đây là hiện thực của FR-DATA-04 + BRD-P01/P05 và tiêu chí US-CEO-007.

## 5. Phân vùng lưu trữ theo domain (ánh xạ sang schema)

AI-EOS 28 domain / 5 lớp, hiện thực hóa theo **R-DEC-06 (Modular Monolith)** + **R-DEC-10** (ID theo BRD + ánh xạ `main`): nhóm entity ánh xạ sang schema PostgreSQL theo domain. Bảng ánh xạ 13 nhóm → schema (đề xuất): org/admin → `platform`+`auth`; data capture → `idp`; AI → `ai`; workflow → `platform`; finance → `finance`; sales/customer/partner → `sales`; hr → `hr`; product/engineering → `product`; risk/governance → `risk`; strategy/kpi/okr/performance/meeting/task → `execution`; knowledge/report → `platform`/`dashboard`. Chi tiết schema chốt ở đợt code (R-DEC-09).

## 6. AI entity & grounding

Mọi con số AI đưa ra phải khớp một `AIToolCall` result hoặc `Metric`/`KPIMeasurement` (SourceRef) — **grounding** (FR-AIQ-01, BRD-P05 "không bịa số"). Không khớp → gỡ số + warning; thiếu dữ liệu → trả rõ "chưa có dữ liệu" (SOURCE-UIUX §208) thay vì bịa. `AIToolCall`, `AIAudit`, `AIDecision`, `AIRecommendation`, `AIEvaluation`, `AIBudget` ghi đủ cho audit AI (02 §9):
- `AIToolCall` — mỗi lượt gọi tool: tool, input (đã lọc PII), result, nguồn; là bằng chứng của mọi số AI đưa ra.
- `AIRecommendation` / `AIDecision` — khuyến nghị 9 phần (Observation→…→Action, skeleton §9) và quyết định (người hoặc AI theo autonomy L0–L3); gắn undo ≥24h cho hành động L3.
- `AIAudit` — vết audit đầy đủ chuỗi OBSERVE→…→VERIFY→LEARN; `AIEvaluation` — đánh giá chất lượng/độ chính xác; `AIBudget` — chi phí AI theo kỳ (chặn khi vượt ngân sách).

`ENT-DataLineage` nối Business Record → ExtractedField → SourceDocument/trang; khi AI trích dẫn một con số, source chip trỏ qua cùng lineage này (một đường truy nguồn duy nhất cho cả người và AI).

## 6bis. Metric Store / Semantic layer (FR-DATA-06)

Metric Store là **nơi định nghĩa chỉ số một lần**, chia sẻ cho dashboard, Report và AI tool — chống tình trạng "mỗi nơi một công thức". Mỗi định nghĩa (mức khái niệm) gồm: tên, mô tả, **công thức**, **nguồn dữ liệu**, **bộ lọc**, **owner**, đơn vị, hướng tốt/xấu, tần suất/kỳ, ngưỡng cảnh báo. Giá trị tính sẵn (precompute qua consumer của event backbone) lưu vào `Metric`/`KPIMeasurement`, không tính lúc request.

- **Semantic layer:** KPI tham chiếu công thức trong Metric Store (BRD §8: "Formula (tham chiếu Metric Store)") — một KPI không tự định nghĩa lại công thức.
- **Dùng chung:** dashboard (03), Report (FR-RPT-02 "dùng số liệu từ Metric Store, có trích dẫn"), và AI tool đọc **cùng** giá trị → mọi kênh nhất quán.
- **Lineage bắt buộc:** mỗi metric có `lineage_url` để click ra nguồn (FR-DATA-04, BRD-P01).
- Mã `METRIC-<NHÓM>-NN` (NHÓM ∈ FIN/CUS/OPS/PPL/STR/DQ) + công thức cụ thể **cấp ở 03** theo nhóm chỉ số (skeleton §10); 05 chỉ chốt vai trò entity `Metric` trong semantic layer. Field-level của `Metric` chốt ở đợt code (R-DEC-09).

## 6ter. Lịch sử & effective-dated (FR-DATA-07) — scope P0

Để trả lời "tại thời điểm X thì sao", entity quan trọng lưu lịch sử thay đổi theo thời điểm hiệu lực (effective-dated). **Phạm vi P0 (tối thiểu):**
- **Cơ cấu tổ chức** (Organization/Department/Team/Employee–Position–Role) — bám FR-ORG-04: truy được sơ đồ tổ chức tại một mốc quá khứ; phục vụ UC-07 onboarding và báo cáo lịch sử.
- **KPITarget** — target có thể đổi giữa kỳ; cần biết target "đang hiệu lực" tại thời điểm đo để KPIEvaluation đúng.

Entity còn lại (ngoài P0) dùng `version` + audit để truy vết thay đổi; mở rộng effective-dated sang entity khác và **mô hình lưu lịch sử cụ thể** (bitemporal, bảng history hay cột valid_from/valid_to) chốt ở đợt code (R-DEC-09). Giữ nguyên tắc: không ghi field-level DB ở vòng docs này.

## 7. Event backbone (FR-DATA-05)

Event backbone biến mọi thay đổi nghiệp vụ thành dòng sự kiện để AI **quan sát real-time** (bước OBSERVE của AI Operating Loop) và để metric tính sẵn. Event mẫu: `invoice.created`, `kpi.measured`, `task.overdue`, `document.committed`, `kpi.below_threshold`, `okr.at_risk`, `risk.detected`.

**Envelope (mức khái niệm):** `event_id, event_type, occurred_at, version, correlation_id, payload` — payload **không chứa PII** (đồng bộ chính sách classification §2.1). `correlation_id` nối event về request/lineage để truy nguồn.

**Nguyên tắc nghiệp vụ (hiện thực chốt ở 07/10, R-DEC-09):**
- Event phát **cùng transaction** với ghi dữ liệu (nguyên tắc outbox) → không mất/không phát nhầm event khi rollback.
- Consumer xử lý **idempotent** (một event xử lý một lần cho mỗi consumer) → không nhân đôi metric/alert khi retry.
- Breaking change schema event → tạo phiên bản mới (ví dụ `_v2`), không phá consumer cũ.

**Event → tác động (mẫu P0):** `kpi.below_threshold`/`okr.at_risk` → insight + ApprovalRequest (UC-03/UC-04); `task.overdue` → Notification + feed CEO; `document.committed` → cập nhật Business Record + metric liên quan; `invoice.created` → cập nhật công nợ/dòng tiền (chuẩn bị cho UC-08 P1).

Danh mục event đầy đủ (mã `EVT-*`) + cặp publish/consume chốt ở **10 §8** (đợt code).

## 8. Open questions
- OQ-05-01: Quy ước `source` (BRD) vs hậu tố `*_source` (DEC-154 `main`) — giữ `source` theo BRD ở docs; chốt quy ước cột khi tái dùng code ở đợt code (R-DEC-09).
- OQ-05-02: Tập entity chính xác cho MVP P0 (tập con của §13.2) — theo R-DEC-05 (phủ tập P0); §3 đã nêu entity P0 chính per nhóm, danh sách field-level cụ thể chi tiết hóa ở đợt code (R-DEC-09).
- OQ-05-03: effective-dated (FR-DATA-07) cho entity nào ở MVP — §6ter chốt tối thiểu cơ cấu tổ chức (FR-ORG-04) + KPITarget; mở rộng & mô hình lưu lịch sử (bitemporal / valid_from-to) chốt ở đợt code (R-DEC-09).
- OQ-05-04: DQ Score (FR-DATA-02) — công thức tổng hợp 4 chiều (đầy đủ/chính xác/kịp thời/nhất quán) per-domain + ngưỡng tươi dữ liệu per-domain (FR-DATA-03) chốt ở 03 (`METRIC-DQ-*`); chưa gán số ở vòng này.
- OQ-05-05: Data classification mặc định per nhóm (§2.1) là đề xuất mức khái niệm; override per-field + chính sách LLM theo mức chốt ở 07/đợt code (R-DEC-09).

## Version
- **Version:** 1.0.0 (current)
- **Last updated:** 2026-10-23
- **Maintainer:** @CyEyes
- **Change 1.1.0 (code round — human ủy quyền R-DEC-14, 2026-10-23):** Thêm §2.2 field-level đợt code Phase 1: `tenant_id UUID NOT NULL` + `TenantMixin` (R-DEC-13); `auth.role_code` enum 7 giá trị v3 (`CEO/DIR/MGR/EMP/REV/ADM/AI`) + bảng gộp 10→7 (R-DEC-12). Chi tiết schema/migration ở code; mọi thay đổi reversible.
- **Change 1.0.0 (promote):** Promote tài liệu AI-EOS lên CHÍNH THỨC Aureon v3; di chuyển vào vị trí docs chuẩn; v2.1 archived (docs/_archive/v2.1/).
- **Change 0.3.0:** Mở rộng lên spec-level P0 (docs-first R-DEC-09 — không field-level DB): mỗi FR-DATA-01..08 thêm mô tả hành vi + tiêu chí chấp nhận; §2.1 data classification per nhóm entity; §3 bổ sung vai trò nghiệp vụ + entity P0 chính + liên kết lineage/event cho 13 nhóm; §4 sơ đồ quan hệ cốt lõi với cardinality mức khái niệm + giải thích chuỗi lineage; §6 mở rộng AI entity/grounding; §6bis Metric Store/Semantic layer; §6ter effective-dated scope P0; §7 event backbone (envelope, nguyên tắc outbox/idempotent, event→tác động); thêm OQ-05-04/05.
- **Change 0.2.0:** Chốt Q1–Q6 (R-DEC-05..10) — cập nhật trạng thái quyết định, đóng OQ liên quan; phạm vi docs-first P0.
- **Change 0.1.0:** Viết lại 05 theo AI-EOS — Data Foundation FR-DATA-01..08, trường chung, 13 nhóm entity BRD §13.2, quan hệ cốt lõi, ánh xạ nhóm→schema, AI entity/grounding, event backbone.
