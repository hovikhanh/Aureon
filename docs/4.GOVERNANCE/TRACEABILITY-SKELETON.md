# AI-EOS Traceability Skeleton — ID Registry (Aureon v3 — AI-EOS)

> **Mục đích:** bộ **ID registry xương sống** cho toàn bộ tài liệu AI-EOS (00–14). Mọi spec chỉ dùng ID trong file này; đây là nguồn traceability duy nhất cho Aureon v3 — AI-EOS.
> **Nguồn:** `_reference/SOURCE-BRD-v1.1.md` (1.264 dòng), `_reference/SOURCE-BRD-v1.1-Bổ sung.md`, `_reference/SOURCE-UIUX.md`. Tách từ Aureon v2.1 (nay archived ở `docs/_archive/v2.1/`).
> **Khác v2.1:** v2.1 dùng 5 trụ F.O.C.U.S + 10 role + 6 module. Registry này bám **BRD đầy đủ**: 28 domain, 7 role + AI Agent, FR theo domain. Bảng ánh xạ sang v2.1 ở §12.
> **Trạng thái:** ✅ current — Aureon v3 (AI-EOS) CHÍNH THỨC — khung ID; định nghĩa chi tiết (entity field, metric formula, EP contract) viết ở các file 00–14 theo `docs/4.GOVERNANCE/REBUILD-PLAN.md` §7.
> **Ngày:** 2026-10-23 · **Maintainer:** @CyEyes

---

## 1. Nguyên tắc sản phẩm — `P01`–`P11` (BRD §2.2)

| ID | Nguyên tắc | ID | Nguyên tắc |
|---|---|---|---|
| P01 | AI First | P07 | Explainable AI |
| P02 | API First | P08 | Security by Design |
| P03 | Data First | P09 | Capture Once, Use Everywhere |
| P04 | Human in the Loop | P10 | Graceful Degradation |
| P05 | Everything Actionable | P11 | Measure Outcomes |
| P06 | Traceability | | |

## 2. Yêu cầu AI-first — `AI-R01`–`AI-R12` (BRD §2.3)

AI-R01 đọc dữ liệu theo quyền · AI-R02 truy vấn qua tool (không DB trực tiếp) · AI-R03 khuyến nghị chuẩn · AI-R04 tạo task từ insight/tài liệu · AI-R05 kích hoạt workflow · AI-R06 thực hiện hành động theo Autonomy · AI-R07 log mọi tool call · AI-R08 kiểm authorization trước tool call · AI-R09 bằng chứng + trích dẫn · AI-R10 verify kết quả · AI-R11 có Extraction Schema · AI-R12 phát event nghiệp vụ.

## 3. Mục tiêu kinh doanh — `BO-01`–`BO-10` (BRD §2.1)

BO-01 quản trị tập trung ≥80% · BO-02 minh bạch gần real-time (≤24h tài chính, ≤1h task/sales) · BO-03 liên kết chiến lược↔thực thi ≥70% · BO-04 quyết định có AI ≥50% · BO-05 thực thi có AI (tăng/tháng) · BO-06 giảm chi phí quản lý ≥50% · BO-07 bộ nhớ doanh nghiệp ≥90% · BO-08 nhập liệu không ma sát (−70%) · BO-09 Data Quality ≥90/100 · BO-10 phát hiện rủi ro sớm (−50%).

## 4. Domain — `D01`–`D28`, 5 lớp (BRD §4–§12)

| Lớp | ID | Domain | Ưu tiên | FR prefix |
|---|---|---|---|---|
| Nền tảng | D01 | Organization | P0 | FR-ORG-01..06 |
| Nền tảng | D02 | Administration & Security | P0 | FR-ADM-01..08 |
| Nền tảng | D03 | Data Capture & IDP | P0 | FR-DC-01..23 |
| Nền tảng | D04 | Workflow & Approval Engine | P0 cơ bản / P1 | FR-WF-01..06 |
| Nền tảng | D05 | Notification | P0 | FR-NTF-01..04 |
| Nền tảng | D06 | Integration Hub | P0 (Google/MS) / P1 | FR-INT-01..04 |
| Điều hành | D07 | Strategy Management | P0 cơ bản / P1 | FR-STR-01..06 |
| Điều hành | D08 | KPI Management | P0 | FR-KPI-01..08 |
| Điều hành | D09 | OKR Management | P0 | FR-OKR-01..06 |
| Điều hành | D10 | Performance Management | P0 check-in / P1 | FR-PERF-01..05 |
| Thực thi | D11 | Project / Task / Workload | P0 | FR-TASK-01..05, FR-WL-01..03 |
| Thực thi | D12 | Meeting Intelligence | P0 / P1 | FR-MTG-01..07 |
| Thực thi | D13 | Calendar | P0 | FR-CAL-01..04 |
| Thực thi | D14 | Knowledge / Documents | P0 | FR-KNW-01..04 |
| Vận hành KD | D15 | Finance | P0 Lite / P1 | FR-FIN-01..04 |
| Vận hành KD | D16 | Human Resources | P0 cơ bản / P1 | FR-HR-01..04 |
| Vận hành KD | D17 | Sales / Business | P0 Lite / P1 | FR-SAL-01..04 |
| Vận hành KD | D18 | Customer | P1 | FR-CUS-01..03 |
| Vận hành KD | D19 | Partner | P1 | (FR-PTN, §9.5) |
| Vận hành KD | D20 | Procurement / Vendor | P1 | FR-PRC-01..03 |
| Vận hành KD | D21 | Contract Lifecycle | P1 | FR-CTR-01..03 |
| Vận hành KD | D22 | Product | P1 | (FR-PRD, §9.8) |
| Vận hành KD | D23 | Technical / Engineering | P1 | (FR-ENG, §9.9) |
| Governance & Trí tuệ | D24 | Governance & Compliance | P2 | FR-GOV-01..04 |
| Governance & Trí tuệ | D25 | Risk Management | P1 | FR-RSK-01..05 |
| Governance & Trí tuệ | D26 | AI Platform | P0 | FR-AIQ-01..06 |
| Governance & Trí tuệ | D27 | CEO AI Assistant | P0 | (§12.1–12.3) |
| Governance & Trí tuệ | D28 | Reporting & Analytics | P0 cơ bản | FR-RPT-01..04, FR-DEC-01..03 |

### 4.1. FR Data Foundation — `FR-DATA-01`–`08` (BRD §13.1)

MDM · Data Quality Score · Data Freshness · Data Lineage · Event backbone · Metric Store/Semantic layer · Lịch sử & effective-dated · Data export.

## 5. Vai trò — 7 chuẩn + AI Agent actor (BRD §3.2)

| ID | Vai trò | Scope | AI Assistant |
|---|---|---|---|
| ROLE-CEO | CEO | Toàn DN | CEO Assistant |
| ROLE-DIR | Executive / Director | Khối / phòng ban phụ trách | Department Copilot |
| ROLE-MGR | Manager | Team | Team Copilot |
| ROLE-EMP | Employee | Cá nhân | Personal Assistant |
| ROLE-REV | Reviewer | Hàng chờ được phân | Review Assistant |
| ROLE-ADM | Admin | Cấu hình nền tảng (không mặc định xem nghiệp vụ) | Admin Assistant |
| ROLE-AI | AI Agent | Giao quyền agent ∩ người | — |

- Doanh nghiệp tạo thêm **vai trò tùy biến** (BRD §3).
- RBAC + **ABAC** + field-level security (NFR-SEC-02); AI access scope theo phòng ban/role/agent/tool (FR-ADM-03).
- RACI cho 7 quy trình cốt lõi: BRD §3.3 (AI Agent không bao giờ là A).

## 6. Use case — `UC-01`–`UC-08` (BRD §14)

| ID | Tên | Ưu tiên |
|---|---|---|
| UC-01 | CEO Morning Briefing | P0 |
| UC-02 | Meeting to Execution | P0 (transcript) / P1 (AI dự họp) |
| UC-03 | KPI Underperformance | P0 |
| UC-04 | OKR At Risk | P0 |
| UC-05 | CEO Strategic Question | P1 |
| UC-06 | Biên bản giấy → thực thi | P0 |
| UC-07 | Onboarding doanh nghiệp 1 ngày | P0 |
| UC-08 | Hóa đơn → cảnh báo dòng tiền | P1 |

MVP: UC-01, UC-02, UC-03, UC-06, UC-07 (+ UC-04 P0).

## 7. User stories — ~110 US, 19 epic A–S (BRD §15)

| Epic | Prefix | Dải | Ưu tiên nổi bật |
|---|---|---|---|
| A. Organization | US-ORG | 001–004 | P0 |
| B. Data Capture | US-DC | 001–012 | P0 (001–009), P1 (010–012) |
| C. Finance | US-FIN | 001–005 | P0 Lite (001–003), P1 (004–005) |
| D. HR | US-HR | 001–005 | P0 (002–003), P1 (còn lại) |
| E. Sales | US-SAL | 001–005 | P0 (002–003), P1 (còn lại) |
| F. Customer & Partner | US-CUS, US-PTN | CUS-001, PTN-001 | P1 |
| G. Procurement & Contract | US-PRC, US-CTR | PRC-001, CTR-001 | P1 |
| H. Product | US-PRD | 001–004 | P1 |
| I. Engineering | US-ENG | 001–004 | P1 |
| J. Governance & Risk | US-GOV | 001–004 | P2 (GOV), P1 (RSK via GOV-003/004) |
| K. Strategy | US-STR | 001–004 | P0 (001–003), P1 (004) |
| L. KPI | US-KPI | 001–010 | P0 |
| M. OKR | US-OKR | 001–009 | P0 |
| N. Performance | US-PERF | 001–006 | P0 (001, 006), P1 (còn lại) |
| O. Task & Workload | US-TASK | 001–006 | P0 |
| P. Meeting & Calendar | US-MTG, US-CAL | MTG-001..003, CAL-001..002 | P0 (trừ MTG-003 P1) |
| Q. AI Platform | US-AI | 001–008 | P0 |
| R. CEO Assistant | US-CEO | 001–008 | P0 |
| S. Reporting | US-RPT | 001–005 | P0 (001, 002, 005), P1 (003, 004) |

> ⚠️ `US-CEO-0xx` của BRD **khác nghĩa** với mã `US-CEO-*` từng dùng ở `main` v1 — khi ánh xạ phải dùng bảng §12.

## 8. Kênh nhập liệu — `C1`–`C10` (BRD §6.1)

| ID | Kênh | Ưu tiên | ID | Kênh | Ưu tiên |
|---|---|---|---|---|---|
| C1 | Form thủ công | P0 | C6 | Email forwarding | P1 |
| C2 | Ngôn ngữ tự nhiên (text/voice) | P0 | C7 | Chat (Zalo/Slack/Teams) | P1 |
| C3 | Tải file | P0 | C8 | Hóa đơn điện tử XML (NĐ 123) | P1 |
| C4 | Chụp ảnh mobile | P0 | C9 | Thư mục đồng bộ (Drive/SharePoint) | P1 |
| C5 | Import hàng loạt (Excel/CSV) | P0 | C10 | API / Webhook | P1 |

- Vòng đời tài liệu: `UPLOADED → PROCESSING → EXTRACTED → NEEDS_REVIEW → APPROVED → COMMITTED` (+ `FAILED`, `REJECTED`, `SUPERSEDED`) — BRD §6.7.
- 14 loại tài liệu + Extraction Schema cấu hình (BRD §6.3).

## 9. AI Platform (BRD §11)

- **13 thành phần** (`AIC-*` đề xuất): AI Gateway, Orchestrator, Agent Runtime, Model Gateway, Prompt & Instruction Mgmt, Tool Registry, Knowledge Retrieval, Memory, Document AI Engine, Policy Engine, Approval Engine, Audit Engine, Evaluation Engine, Event Listener.
- **Autonomy Levels** `L0`–`L4` (BRD §11.6): L0 Inform · L1 Suggest · L2 Draft & Confirm · L3 Act & Notify (undo ≥24h) · L4 Autonomous (chưa bật MVP).
- **Phân loại tool:** READ · WRITE · APPROVAL (AI không tự gọi) · EXECUTION (BRD §11.3).
- **Agent** (`AGT-*` đề xuất, BRD §11.4): CEO, Data Capture, Performance, Task, Meeting, Reporting (P0); Finance/Sales (P0 Lite/P1); HR/Product/Engineering/Procurement (P1); Strategy/Risk/Governance (P1/P2).
- **Tool Registry metadata** (BRD §11.2, 13 thuộc tính): name, description, input_schema, output_schema, permission, risk_level, data_scope, data_classification, autonomy_level mặc định, approval_required, reversible, audit_required, cost_estimate, owner.
- **Insight 9 phần** (BRD §11.8): Observation → Evidence → Impact → Root Cause → Risk → Recommendation → Expected Outcome → Confidence → Action.
- **AI Operating Loop** (BRD §17.5): OBSERVE → UNDERSTAND → REASON → RECOMMEND → APPROVE → ACT → VERIFY → LEARN.

## 10. Bộ chỉ số sức khỏe doanh nghiệp (BRD §12.4)

Nhóm Tài chính / Khách hàng / Vận hành / Con người / Chiến lược / Dữ liệu. P0: tăng trưởng DT & %kế hoạch, cash runway (<6 tháng), chênh lệch ngân sách (>10%), pipeline coverage (<3x), win rate & chu kỳ bán hàng, hoàn thành đúng hạn (<80%), dự án trễ (>20%), thực thi quyết định (<70%), quá tải (>10%), **Strategy Execution Index** (<70%), **Data Quality Score** (<80/100). P1: biên lợi nhuận, DSO/DPO, công nợ quá hạn, NRR/churn, tập trung DT, CAC/LTV/NPS, nghỉ việc, DT/nhân sự.

> Mã `METRIC-*` cụ thể sẽ cấp ở file 00/03 khi viết; registry này chốt **danh sách chỉ số nguồn** từ BRD, chưa gán số.

## 11. Entity cốt lõi (BRD §13.2) — 13 nhóm

Tổ chức (Organization, BusinessUnit, Department, Team, Employee, Position, Role) · Kinh doanh (Customer, Contact, Lead, Opportunity, Partner, Vendor, Contract, ContractObligation, PurchaseOrder) · Sản phẩm & thực thi (Product, Feature, Project, Milestone, Task, Workload) · Chiến lược (Strategy, StrategicPillar, StrategicObjective, Initiative) · KPI (KPI, KPITarget, KPIMeasurement, KPIEvaluation, Metric) · OKR (Objective, KeyResult, KRMeasurement) · Hiệu suất (PerformanceCycle, PerformanceReview, CheckIn) · Họp & quyết định (Meeting, MeetingTranscript, MeetingSummary, Decision, ActionItem) · Rủi ro & tuân thủ (Risk, RiskAssessment, Mitigation, Policy, Control, Evidence, Finding) · Tài chính (Budget, CostCenter, Revenue, Expense, Invoice, Payment, CashBalance) · Tri thức (Document, Knowledge, Report) · Data Capture (SourceDocument, DocumentPage, DocumentType, ExtractionSchema, ExtractionJob, ExtractedField, ExtractionReview, ValidationRule, ImportBatch, DataLineage) · AI (AIAgent, AITool, AIToolCall, AIRecommendation, AIDecision, AIAudit, AIEvaluation, AIBudget) · Workflow (Workflow, WorkflowStep, ApprovalRequest, Notification).

→ Dùng `ENT-<Name>` khi viết 05; field, kiểu, quan hệ chốt ở 05-DATA-MODEL.

## 12. Ánh xạ Aureon v2.1 ↔ Aureon v3 (AI-EOS) — để giữ traceability

| Khía cạnh | Aureon v2.1 | Aureon v3 (AI-EOS) |
|---|---|---|
| Trụ F (Finance) | 5 trụ F.O.C.U.S | D15 Finance + chỉ số Tài chính §12.4 |
| Trụ O (Operations & People) | trụ O | D11 Task/Workload + D16 HR + chỉ số Vận hành/Con người |
| Trụ C (Customer & Growth) | trụ C | D17 Sales + D18 Customer + chỉ số Khách hàng |
| Trụ U (Product & Innovation) | trụ U | D22 Product + D23 Engineering |
| Trụ S (Strategy & Risk) | trụ S | D07 Strategy + D25 Risk + D24 Governance |
| 10 role F.O.C.U.S | CEO/CFO/VP_SALES/HR_MANAGER/CPO/RISK_MANAGER/MANAGER/EMPLOYEE/REVIEWER/ADMIN | 7 role: C-level → ROLE-DIR (scope); MANAGER→ROLE-MGR; EMPLOYEE→ROLE-EMP; REVIEWER→ROLE-REV; ADMIN→ROLE-ADM; CEO→ROLE-CEO; **+ ROLE-AI mới** |
| Autonomy | L0–L3 (L4 khóa) | L0–L4 (L4 ở phase 5) |
| Kênh | C1–C5 | C1–C10 |
| Kiến trúc | Modular Monolith 11 module | 28 domain / 5 lớp (kiến trúc chốt theo Q2 trong REBUILD-PLAN) |

## 12bis. Tập P0 đã khóa (R-DEC-05 — P0 MVP first)

Q1–Q6 đã chốt (13 §1). Tập **P0** cho đợt tài liệu này được khóa như sau; mọi file 00–14 chỉ đặc tả đầy đủ tập P0, P1/P2 ghi backlog (09).

**Domain P0 (12):** D01 Organization · D02 Admin & Security · D03 Data Capture & IDP · D04 Workflow (cơ bản) · D05 Notification · D06 Integration Hub (Google/MS) · D07 Strategy (cơ bản) · D08 KPI · D09 OKR · D10 Performance (check-in) · D11 Task/Workload · D12 Meeting (từ transcript) · D13 Calendar · D14 Knowledge · D15 Finance Lite · D16 HR cơ bản · D17 Sales Lite · D26 AI Platform · D27 CEO Assistant · D28 Reporting cơ bản.
**Domain P1 (backlog):** D18 Customer · D19 Partner · D20 Procurement · D21 Contract · D22 Product · D23 Engineering · D25 Risk · D04/D06/D10/D12 phần nâng cao.
**Domain P2 (backlog):** D24 Governance & Compliance.

**Kênh P0:** C1–C5. **Kênh P1 (backlog):** C6–C10.
**Autonomy P0:** L0–L3 (undo ≥24h). **L4:** phase 5 (backlog, không bật MVP).
**UC P0:** UC-01, UC-02 (transcript), UC-03, UC-04, UC-06, UC-07. **UC P1:** UC-05, UC-08, UC-02 (AI dự họp).
**Agent P0 (`AGT-*`):** CEO, Data Capture, Performance, Task, Meeting, Reporting (+ Finance/Sales Lite). **Agent P1/P2:** HR/Product/Engineering/Procurement/Strategy/Risk/Governance.

### Quy ước gán số ID (R-DEC-10 — BRD + ánh xạ Aureon v2.1)
- **FR-*:** đã cố định theo §4 (FR-ORG-01..06, FR-DC-01..23, …). Agent **không** tạo FR ngoài dải này; cần thêm → cập nhật §4 trước.
- **METRIC-*:** cấp ở **03** theo nhóm §10, định dạng `METRIC-<NHÓM>-NN` (NHÓM ∈ FIN/CUS/OPS/PPL/STR/DQ). Danh sách nguồn ở §10; 03 chốt số + công thức.
- **ENT-*:** cấp ở **05**, định dạng `ENT-<Name>` theo 13 nhóm §11. 05 chốt field/kiểu/quan hệ; mọi entity nghiệp vụ có `tenant_id` (R-DEC-07).
- **EP-*:** cấp ở **10** theo domain P0, định dạng `EP-<DOMAIN>-NN`. Phân loại tool READ/WRITE/APPROVAL/EXECUTION (§9).
- **SCR-*:** cấp ở **06** theo SOURCE-UIUX, định dạng `SCR-NN`. Đợt code (R-DEC-25): giữ số v2.1 cho màn hình dùng tiếp (SCR-03/13/14/16/18a/18b), màn hình mới từ `SCR-40` (06 §3.4).
- **EP domain code** (đợt code, R-DEC-19, 10 §7.1): `SYS, ORG, ADM, DC, WF, NTF, INT, STR, KPI, OKR, PRF, TASK, MTG, CAL, KNW, FIN, HR, SAL, AI, CEO, RPT`.
- **T-*** (task đợt code, R-DEC-19, cấp ở **09 §6**): `T-6xx` M1 · `T-7xx` M2 · `T-8xx` M3 · `T-9xx` nghiệm thu; hậu tố chữ (`T-601b`) cho task chèn thêm. Không dùng lại T-1xx..T-5xx (nền v2.1).
- **TC-*** (nhóm test đợt code, cấp ở **14**): `TC-M<mốc><phase>-NN` (VD `TC-M11-03` = M1.1 case 3), cạnh các nhóm UC `TC-UC0x-*` và `TC-SYS-*` sẵn có.
- **Phase đợt code:** `M1.0`–`M3.5` (09 §6) — nhãn lộ trình, khác "Phase 1–5" BRD §19.2.
- **TOOL-*:** cấp ở **10** (Tool Registry §9, 13 metadata). **AIC-*** (13 thành phần AI Platform) cấp ở **07**. **AGT-*** (agent, §9/§12bis) tham chiếu ở **07**/**10**.
- **Nhãn nội bộ một file** (CLAUDE.md §10.3 — chỉ dùng trong đúng file, không phải ID liên-file): `OQ-` (open question, mọi file); `DD-` (nguyên tắc dữ liệu demo — 08); `G1..G4` (cổng nghiệm thu MVP — 09); `GR-`/`INJ-`/`AUT-` (nhóm test grounding / anti-injection / autonomy — 14). Thêm nhãn nội bộ mới → ghi tại file dùng + liệt kê ở đây.
- Mọi ID **liên-file** mới phải được thêm vào skeleton (file này) **trước** khi dùng trong 00–14.

## 13. Quyết định mở cần human (BRD §21.1 + REBUILD-PLAN Q1–Q6)

Q1–Q6: **đã chốt** (13 §1 — R-DEC-05..10). Còn mở (CEO, không blocking docs P0): SaaS đa tenant dài hạn · khách hàng mục tiêu đầu · chính sách AI cloud (dữ liệu tài chính/nhân sự) · vai trò với phần mềm kế toán · ngưỡng L3 mặc định · kênh chat chính · mô hình giá. Theo dõi ở 13-DECISION-LOG §3 (B1–B7).

## Version
- **Version:** 1.1.0 (current)
- **Last updated:** 2026-10-23
- **Maintainer:** @CyEyes
- **Change 1.1.0 (human duyệt 2026-10-23 — đợt code, R-DEC-19/25):** quy ước ID đợt code: SCR giữ số v2.1 + mới từ SCR-40; EP domain code; `T-6xx..9xx`; `TC-M<x><y>-NN`; nhãn phase `M1.0`–`M3.5`.
- **Change 1.0.0 (promote):** Promote tài liệu AI-EOS lên CHÍNH THỨC Aureon v3; di chuyển vào vị trí docs chuẩn; v2.1 archived (docs/_archive/v2.1/).
- **Change 0.3.0:** Vòng mở rộng spec-level P0 — ghi nhận nhãn nội bộ một file (`DD-`/`G1..G4`/`GR-`/`INJ-`/`AUT-`) dùng trong 08/09/14; bổ sung `AGT-*` vào quy ước ID; phân biệt "ID liên-file" (cập nhật skeleton trước) vs "nhãn nội bộ một file". Không đổi tập P0 hay quyết định Q1–Q6.
- **Change 0.2.0:** Khóa tập P0 (§12bis) sau khi human chốt Q1–Q6: 20 domain P0 / 6 P1 / 1 P2, kênh C1–C5 P0, Autonomy L0–L3 P0 (L4 phase 5), UC P0, agent P0; thêm quy ước gán số METRIC/ENT/EP/SCR/TOOL/AIC + ràng buộc "ID mới cập nhật skeleton trước"; cập nhật §13 (Q1–Q6 đã chốt).
- **Change 0.1.0:** Tạo ID registry xương sống từ BRD AI-EOS đầy đủ: P01–P11, AI-R01–R12, BO-01–BO-10, 28 domain + FR prefix, 7 role + AI Agent, UC-01–08, ~110 US (19 epic), C1–C10, AI Platform (13 thành phần, L0–L4, agent, tool metadata, insight 9 phần), bộ chỉ số sức khỏe, 13 nhóm entity, ánh xạ main↔ai-eos, quyết định mở.
