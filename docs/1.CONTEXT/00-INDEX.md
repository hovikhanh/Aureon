# 00 — INDEX

> File này là **bản đồ tài liệu** và **sổ đăng ký ID** (ID registry) của Aureon v2 cho AI Agent.
> Mục đích: agent biết file nào cần đọc cho task nào, KHÔNG đọc thừa, và dùng đúng một bộ ID xuyên suốt 14 spec.
> Aureon v2 = hợp nhất **A-EMS** (BRD v1.0) + **AI-EOS** (BRD v1.1, D03 Data Capture & IDP) + đề xuất UI/UX AI-EOS, theo DEC-124 → DEC-137. Nguồn gốc chính thức: `_reference/` (DEC-144). Bản 2.1.0: ID registry theo scheme BRD (DEC-146) và scope v2.0 / v2.1 (DEC-147..153, `docs/4.GOVERNANCE/GAP-ANALYSIS-v2.1.md`).

---

## 1. Cấu trúc tài liệu

```
docs/
├── 1.CONTEXT/              ← Đọc đầu mọi session
├── 2.PRODUCT/              ← Đọc khi làm feature
├── 3.EXECUTION/            ← Đọc khi code/build
└── 4.GOVERNANCE/           ← Check trước mọi task
```

Bản v1 (MVP demo 4 trụ, 5 vai trò) được lưu nguyên trạng ở nhánh git `v1` — không dùng cho build v2.

---

## 2. Bản đồ file

### 1.CONTEXT — Tầng ngữ cảnh

| File | Mục đích | Khi nào load |
|---|---|---|
| `00-INDEX.md` | File này — bản đồ tài liệu + ID registry | Đầu mọi session |
| `01-PROJECT-OVERVIEW.md` | Tầm nhìn v2, scope, KPI, nguyên tắc, roadmap S0–S5 | Đầu mọi session |

### 2.PRODUCT — Tầng sản phẩm

| File | Mục đích | Khi nào load |
|---|---|---|
| `02-PERSONAS-PERMISSIONS.md` | 10 vai trò, user stories, ma trận quyền `<domain>:<action>` | Task auth, role, UI theo vai trò, AI tool filter |
| `03-DASHBOARD-SPEC.md` | 5 trụ F.O.C.U.S, metric, alert, drill-down, insight, briefing | Task dashboard, metric, alert, domain module (F/O/C/U/S) |
| `04-IDP-FEATURE-SPEC.md` | D03 — Data Capture & IDP: 5 kênh, pipeline, review, Action Registry | Task IDP, import, review |
| `05-DATA-MODEL.md` | ERD hợp nhất theo schema module, entity, event, outbox | Task DB, migration, schema |
| `06-UI-UX-SPEC.md` | IA, màn hình SCR-xx, design system v2, AI components, luồng F1–F5 | Task UI, component, layout |

### 3.EXECUTION — Tầng triển khai

| File | Mục đích | Khi nào load |
|---|---|---|
| `07-TECH-ARCHITECTURE.md` | Modular Monolith, event bus, RS256, ModelGateway đa provider, deployment | Đầu sprint, setup, quyết định kỹ thuật |
| `08-DEMO-DATA-SPEC.md` | Công ty ABC (~150 NV), dữ liệu 5 trụ, tài liệu mẫu, seed | Task seed data, demo data |
| `09-BUILD-PLAN-TASKS.md` | Checklist task v2, 6 mốc S0–S5, DoD | Plan sprint, nhận task |
| `10-API-SPECIFICATION.md` | **Contract nguồn duy nhất** cho API + event | Mọi task code API hoặc call API |
| `11-AGENT-WORKFLOW.md` | Doc loading matrix, prompt templates, gates, routing model | Đầu session, khi bị block |

### 4.GOVERNANCE — Tầng kiểm soát

| File | Mục đích | Khi nào check |
|---|---|---|
| `12-DOC-AUDIT.md` | Trạng thái tài liệu (current/draft/stale/archived) | **Gate A** — trước mọi task |
| `13-DECISION-LOG.md` | Trạng thái quyết định (open/resolved/superseded/blocking) | **Gate B** — trước mọi task |
| `14-TEST-TRACEABILITY.md` | Ma trận spec ↔ task ↔ test | **Gate C** — trước mọi task |

---

## 3. Quy ước ID

| Prefix | Loại | Ví dụ | File định nghĩa |
|---|---|---|---|
| `ROLE-xx` | Vai trò | ROLE-06 | 02 |
| `US-<AREA>-nnn` | User Story — area BRD (`ORG, DC, FIN, HR, SAL, CUS, PTN, PRC, CTR, PRD, ENG, GOV, STR, KPI, OKR, PERF, TASK, MTG, CAL, AI, CEO, RPT`) + docs-only (`MGR, ADM, ALL`); 001–099 = BRD, 101–199 = docs (DEC-146, §4.11) | US-KPI-006, US-FIN-101 | 00 §4.11, 02, 04 |
| `UC-xx` | Use Case UC-01..08 (BRD §14, §4.10) | UC-02 | 00 §4.10, 01, 04 |
| `F1`…`F5` | Luồng UX chính | F2 | 06 |
| `FR-<AREA>-xx[x]` | Functional Requirement (`AUTH, FIN, SAL, HR, PRD, RSK, AI, DSH, NTF, DC`); FR-DC-01..23 = nghĩa BRD, 101+ = docs-only (§4.12) | FR-FIN-08, FR-DC-14 | 02, 03, 04 |
| `BR-<AREA>-xx` | Business rule / công thức | BR-FIN-02 | 03 |
| `NFR-xx` | Yêu cầu phi chức năng | NFR-07 | 07 |
| `PIL-x` | Trụ F.O.C.U.S (`F, O, C, U, S`) | PIL-S | 03 |
| `METRIC-<FIN\|OPS\|HR\|CUS\|PRD\|RSK\|DQ>-xx` | Metric | METRIC-PRD-02, METRIC-DQ-01 | 03 |
| `ALERT-<FIN\|OPS\|HR\|CUS\|PRD\|RSK\|DQ>-xx` | Alert (1-1 với metric cùng số) | ALERT-RSK-02 | 03 |
| `ENT-<Name>` | Entity | ENT-HiringPlan | 05 |
| `EVT-<domain>.<name>` | Domain event | EVT-hr.hiring_plan_delayed | 05, 10 |
| `TOOL-<name>` | AI tool trong Tool Registry | TOOL-get_finance_dashboard | 10 |
| `ACT-<name>` | Action trong Action Registry (ghi dữ liệu) | ACT-create_invoice | 04 |
| `SCR-xx` | Screen (SCR-01..31) | SCR-10 | 06 |
| `EP-xx` / `EP-1xx` | API Endpoint (2–3 chữ số theo dải §4.6) | EP-110 | 10 |
| `T-xxx` | Build Task v2 (`T-0xx` = S0 … `T-5xx` = S5) | T-204 | 09 |
| `TC-<AREA>-xxx` | Test case | TC-RSK-003 | 14 |
| `DEC-xxx` | Decision | DEC-125 | 13 |

**Tham chiếu nguyên tắc BRD:** `BRD-P01..P11` là **nhãn tham chiếu** tới `_reference/SOURCE-BRD-v1.1.md` §2.2, không phải prefix ID của docs; `P01–P09` (không tiền tố) luôn là nguyên tắc docs 01 §6 (gọi "docs-P" khi cần phân biệt). Bảng đối chiếu §4.9.

**Quy tắc:** Dùng đúng prefix và đúng dải. Không tự tạo ID/prefix mới — raise decision. Nhãn nội bộ được phép trong phạm vi một file: `XD-`, `PI-`, `IDP-E`, `VR-`, `DOC-`, `OQ-`, `K-`, `GAP-`.

---

## 4. ID Registry (nguồn chuẩn cho mọi spec)

Mọi file 02–14 phải dùng đúng các ID dưới đây. Thêm ID mới → sửa bảng này trước (qua DEC).

### 4.1. Vai trò (DEC-128)

| ID | Mã code | Tên | Trụ dashboard |
|---|---|---|---|
| ROLE-01 | `CEO` | Tổng giám đốc | F O C U S |
| ROLE-02 | `CFO` | Giám đốc tài chính | F, S |
| ROLE-03 | `VP_SALES` | Giám đốc kinh doanh | C |
| ROLE-04 | `HR_MANAGER` | Trưởng phòng nhân sự | O |
| ROLE-05 | `REVIEWER` | Người duyệt dữ liệu | — (hàng chờ review) |
| ROLE-06 | `CPO` | Giám đốc sản phẩm | U |
| ROLE-07 | `RISK_MANAGER` | Quản trị rủi ro | S |
| ROLE-08 | `MANAGER` | Trưởng bộ phận | Đơn vị của mình (không có dashboard điều hành) |
| ROLE-09 | `EMPLOYEE` | Nhân viên | — (việc của tôi) |
| ROLE-10 | `ADMIN` | Quản trị hệ thống | — (AI Control Center) |

### 4.2. Trụ và metric (DEC-127; DQ — DEC-148)

| Trụ | Câu hỏi lãnh đạo | Metric |
|---|---|---|
| **PIL-F** Finance | Có đủ tiền, kiếm/tiêu hiệu quả? | METRIC-FIN-01 Doanh thu vs kế hoạch · 02 Biên LN gộp · 03 Cash runway · 04 DSO · 05 Công nợ quá hạn · 06 Chênh lệch ngân sách · 07 Net burn vs dự báo |
| **PIL-O** Operations & People | Đủ người, vận hành ổn? | METRIC-OPS-01 Task đúng hạn · 02 Dự án trễ · 03 Thực thi quyết định · METRIC-HR-01 Doanh thu/nhân sự · 02 Turnover năm hóa · 03 Quá tải · 04 Kế hoạch tuyển dụng trễ |
| **PIL-C** Customer & Growth | Giành và giữ được khách? | METRIC-CUS-01 Pipeline coverage · 02 Win rate · 03 NRR · 04 Tập trung doanh thu top 5 · 05 NPS · 06 Chu kỳ bán TB |
| **PIL-U** Product & Innovation | Sản phẩm tiến lên, được dùng thật? | METRIC-PRD-01 Adoption/MAU · 02 Churn · 03 Retention 30 ngày · 04 Roadmap đúng tiến độ · 05 Tính năng release trong kỳ |
| **PIL-S** Strategy & Risk | Điều gì làm hỏng kế hoạch, xử lý tới đâu? | METRIC-RSK-01 Rủi ro high/critical đang mở · 02 Rủi ro high chưa có chủ · 03 Rủi ro high > 30 ngày không có mitigation · 04 Điểm rủi ro tổng hợp · 05 Biện pháp quá hạn · 06 Strategy execution index (tính theo Initiative — DEC-147, Phase 3b) |
| *(nền tảng — không thuộc trụ)* | Dữ liệu có đáng tin? | **METRIC-DQ-01 Data Quality Score** (DEC-148; nguồn ENT-MetricValue `data_quality_score` + ENT-ImportBatch `quality_score`; công thức và ngưỡng ở 03, Phase 3b) |

Tổng **32 metric** (31 trụ + METRIC-DQ-01). Mỗi metric có đúng 1 alert cùng số (`ALERT-FIN-03` ↔ `METRIC-FIN-03`, `ALERT-DQ-01` ↔ `METRIC-DQ-01`) → **32 alert**. METRIC-DQ-01 không tham gia quy tắc trạng thái trụ (03 §4); hiển thị ở SCR-07 và SCR-15.

### 4.3. Entity theo schema (DEC-125; bổ sung v2.1 — DEC-147..153)

Mã chuẩn vẫn là **`ENT-<Name>`** (CLAUDE.md §5.9). Cột `#` chỉ để đếm và tra cứu — **không dùng `#` làm ID** trong spec/code. Entity **in đậm** = mới v2.1; số v2.0 (001–064) giữ nguyên, entity mới đánh tiếp 065+.

| # | Entity | Schema | Mới · DEC |
|---|---|---|---|
| 001 | ENT-User | `auth` | — |
| 002 | ENT-Role | `auth` | — |
| 003 | ENT-RefreshToken | `auth` | — |
| 004 | ENT-Revenue | `finance` | — |
| 005 | ENT-Expense | `finance` | — |
| 006 | ENT-Budget | `finance` | — |
| 007 | ENT-Forecast | `finance` | — |
| 008 | ENT-ForecastLine | `finance` | — |
| 009 | ENT-Invoice | `finance` | — |
| 010 | ENT-InvoiceLine | `finance` | — |
| 011 | ENT-CashPosition | `finance` | — |
| 012 | ENT-Client | `sales` | — |
| 013 | ENT-Deal | `sales` | — |
| 014 | ENT-DealStageHistory | `sales` | — |
| 015 | ENT-SalesTarget | `sales` | — |
| 016 | ENT-Contract | `sales` | — |
| 017 | ENT-Department | `hr` | — |
| 018 | ENT-Employee | `hr` | — |
| 019 | ENT-SalaryHistory | `hr` | — |
| 020 | ENT-HiringPlan | `hr` | — |
| 021 | ENT-Product | `product` | — |
| 022 | ENT-Feature | `product` | — |
| 023 | ENT-RoadmapItem | `product` | — |
| 024 | ENT-Release | `product` | — |
| 025 | ENT-ProductMetric | `product` | — |
| 026 | ENT-Risk | `risk` | — |
| 027 | ENT-RiskAssessment | `risk` | — |
| 028 | ENT-Mitigation | `risk` | — |
| 029 | ENT-Scenario | `risk` | — |
| 030 | ENT-Meeting | `execution` | — |
| 031 | ENT-Decision | `execution` | — |
| 032 | ENT-Task | `execution` | — |
| 033 | ENT-Project | `execution` | — |
| 034 | ENT-Objective | `execution` | — |
| 035 | ENT-KeyResult | `execution` | — |
| 036 | ENT-CheckIn | `execution` | — |
| 037 | ENT-KPI | `execution` | — |
| 038 | ENT-KPIMeasurement | `execution` | — |
| 039 | ENT-Conversation | `ai` | — |
| 040 | ENT-Message | `ai` | — |
| 041 | ENT-ToolCallLog | `ai` | — |
| 042 | ENT-Feedback | `ai` | — |
| 043 | ENT-Insight | `ai` | — |
| 044 | ENT-AIAction | `ai` | — |
| 045 | ENT-AutonomyPolicy | `ai` | — |
| 046 | ENT-ModelCallLog | `ai` | — |
| 047 | ENT-SourceDocument | `idp` | — |
| 048 | ENT-DocumentPage | `idp` | — |
| 049 | ENT-DocumentType | `idp` | — |
| 050 | ENT-ExtractionSchema | `idp` | — |
| 051 | ENT-ExtractionJob | `idp` | — |
| 052 | ENT-ExtractedField | `idp` | — |
| 053 | ENT-ExtractionReview | `idp` | — |
| 054 | ENT-ValidationRule | `idp` | — |
| 055 | ENT-ImportBatch | `idp` | — |
| 056 | ENT-Metric | `platform` | — |
| 057 | ENT-MetricValue | `platform` | — |
| 058 | ENT-Alert | `platform` | — |
| 059 | ENT-DataLineage | `platform` | — |
| 060 | ENT-AuditLog | `platform` | — |
| 061 | ENT-Notification | `platform` | — |
| 062 | ENT-OutboxEvent | `platform` | — |
| 063 | ENT-ProcessedEvent | `platform` | — |
| 064 | ENT-SystemSetting | `platform` | — |
| 065 | **ENT-CashFlowForecast** | `finance` | DEC-148 |
| 066 | **ENT-CashFlowForecastLine** | `finance` | DEC-148 |
| 067 | **ENT-Team** | `hr` | DEC-147 |
| 068 | **ENT-Position** | `hr` | DEC-147 |
| 069 | **ENT-EmployeeSkill** | `hr` | DEC-147 (C-12) |
| 070 | **ENT-Leave** | `hr` | DEC-147 (C-12) |
| 071 | **ENT-Initiative** | `execution` | DEC-147 |
| 072 | **ENT-Milestone** | `execution` | DEC-147 |
| 073 | **ENT-KPITarget** | `execution` | DEC-147 |
| 074 | **ENT-MeetingTranscript** | `execution` | DEC-153 |
| 075 | **ENT-AIAgentProfile** | `ai` | DEC-149/150 |
| 076 | **ENT-ReviewAssignment** | `idp` | DEC-151 |
| 077 | **ENT-ApprovalRule** | `platform` | DEC-153 |
| 078 | **ENT-ApprovalRequest** | `platform` | DEC-153, DEC-149 |
| 079 | **ENT-Report** | `platform` | DEC-153 |

**Tổng 79 entity** (64 v2.0 + 15 mới) / 10 schema: `auth` 3 · `finance` 10 · `sales` 5 · `hr` 8 · `product` 5 · `risk` 4 · `execution` 13 · `ai` 9 · `idp` 10 · `platform` 12. Module `dashboard` không có schema (DEC-125).

Theo DEC (không tạo entity riêng): rủi ro "đề xuất" = trạng thái `proposed` của ENT-Risk (DEC-148); DQ Score = METRIC-DQ-01 lưu ở ENT-MetricValue (DEC-148); `SUPERSEDED` = trạng thái của ENT-SourceDocument (DEC-151); KPI evaluation band = cột của ENT-KPITarget; Task 7 trạng thái = enum của ENT-Task (DEC-147); permission vẫn là ma trận trong ENT-Role (02 §5).

### 4.4. Màn hình

| ID | Màn hình | ID | Màn hình |
|---|---|---|---|
| SCR-01 | Trang chủ theo vai trò (Briefing) | SCR-15 | AI Control Center (autonomy, kill switch, ngân sách, provider) |
| SCR-02 | Trụ F — Finance | SCR-16 | Hỏi AI (trang Chat) + thanh ⌘K + Panel AI |
| SCR-03 | Trụ O — Operations & People | SCR-17 | Feed "AI đã làm" |
| SCR-04 | Trụ C — Customer & Growth | SCR-18 | Họp, biên bản & transcript → việc (UC-02, UC-06) |
| SCR-05 | Trụ U — Product & Innovation | SCR-19 | Công việc & Workload heatmap |
| SCR-06 | Trụ S — Strategy & Risk | SCR-20 | Mục tiêu: Strategy/Initiative, OKR/KPI & check-in |
| SCR-07 | Chi tiết metric + lineage | SCR-21 | Sổ rủi ro & What-if (gồm hàng chờ `proposed`) |
| SCR-08 | Hộp thư dữ liệu (Data Inbox) | SCR-22 | Finance workspace |
| SCR-09 | Gửi dữ liệu (drop zone, chụp C4, nhập lời C2, form C1) | SCR-23 | Sales workspace |
| SCR-10 | Review song song | SCR-24 | HR workspace (gồm Team/Position) |
| SCR-11 | Import grid (C5) | SCR-25 | Product workspace |
| SCR-12 | Nạp doanh nghiệp (UC-07) | SCR-26 | Quản trị người dùng & vai trò |
| SCR-13 | Đăng nhập | SCR-27 | Cấu hình loại tài liệu / schema / ngưỡng |
| SCR-14 | Audit log | SCR-28 | Mobile shell (Briefing, chụp, duyệt, hỏi AI) |
| **SCR-29** | **Phê duyệt** — hàng chờ ApprovalRequest + cấu hình ApprovalRule (DEC-153) | **SCR-31** | **Dòng tiền 13 tuần** (DEC-148) |
| **SCR-30** | **Báo cáo** — weekly/monthly, xuất PDF/Excel (DEC-153) | | |

Tổng **31 màn hình** (28 v2.0 + 3 mới). Đặc tả SCR-29..31 bổ sung vào 06 ở Phase 3c.

### 4.5. Domain event (DEC-126)

**v2.0 (21):** `EVT-hr.employee_onboarded`, `EVT-hr.employee_terminated`, `EVT-hr.salary_updated`, `EVT-hr.hiring_plan_delayed`, `EVT-sales.deal_closed_won`, `EVT-sales.deal_closed_lost`, `EVT-finance.budget_exceeded`, `EVT-finance.invoice_paid`, `EVT-finance.forecast_updated`, `EVT-finance.burn_over_forecast`, `EVT-product.product_launched`, `EVT-product.feature_released`, `EVT-product.metric_anomaly`, `EVT-risk.risk_identified`, `EVT-risk.risk_level_changed`, `EVT-risk.risk_mitigated`, `EVT-execution.task_overdue`, `EVT-execution.kpi_measured`, `EVT-idp.document_committed`, `EVT-idp.document_rolled_back`, `EVT-platform.alert_raised`.

**Mới v2.1 (7):** `EVT-finance.invoice_created` (BRD §13, GAP D-26) · `EVT-finance.cash_flow_forecast_updated` (DEC-148) · `EVT-risk.risk_proposed` (DEC-148; `risk_identified` phát khi owner xác nhận) · `EVT-platform.approval_requested`, `EVT-platform.approval_decided` (DEC-153) · `EVT-platform.report_generated` (DEC-153) · `EVT-idp.review_escalated` (DEC-151).

Tổng **28 event**. Cặp publish/consume và payload bổ sung vào 05 §5.3 và 10 §8.3 (Phase 3a sub-step 2–4 và Phase 3d).

### 4.6. Dải EP

| Dải | Nhóm | Dải | Nhóm |
|---|---|---|---|
| EP-01..09 | System, Auth, User admin | EP-60..69 | Finance |
| EP-10..19 | Dashboard, metric, alert, lineage, briefing | EP-70..79 | Sales |
| EP-20..41 | IDP (giữ số v1) | EP-80..89 | HR |
| EP-42..49 | Execution (họp, quyết định, task, OKR, KPI) | EP-90..99 | Product |
| EP-50..59 | Config, audit, notification | EP-100..109 | Risk |
| EP-120..129 | **Mới v2.1:** Approval, Report, Strategy/Initiative (DEC-153, DEC-147) | EP-110..119 | AI Core |

Số EP cụ thể trong dải cấp ở 10 (Phase 3d); dải đã kín (VD EP-42..49 cho execution) → endpoint mới dùng EP-120..129.

### 4.7. Sprint và task

| Mốc | Dải task | Mục tiêu |
|---|---|---|
| S0 | T-001..T-099 | Nền tảng v2 (module, schema, RS256, outbox, ModelGateway đa provider) |
| S1 | T-101..T-199 | Domain F, C, O (Finance, Sales, HR, Execution) |
| S2 | T-201..T-299 | Domain U, S + Dashboard F.O.C.U.S |
| S3 | T-301..T-399 | Trợ lý AI + Autonomy |
| S4 | T-401..T-499 | IDP v2 |
| S5 | T-501..T-599 | UX, mobile PWA, demo data, phát hành |


### 4.8. AI Tool (Tool Registry — 10 §7)

**35 tool v2.0** (định nghĩa ở 10 §7): `TOOL-create_invoice`, `TOOL-create_meeting`, `TOOL-create_mitigation`, `TOOL-create_task`, `TOOL-get_budget_status`, `TOOL-get_execution_dashboard`, `TOOL-get_finance_dashboard`, `TOOL-get_finance_forecast`, `TOOL-get_hr_dashboard`, `TOOL-get_lineage`, `TOOL-get_metric`, `TOOL-get_product_dashboard`, `TOOL-get_product_metrics`, `TOOL-get_risk_dashboard`, `TOOL-get_runway_what_if`, `TOOL-get_sales_dashboard`, `TOOL-get_sales_pipeline`, `TOOL-get_source_document`, `TOOL-get_workload`, `TOOL-list_alerts`, `TOOL-list_deals`, `TOOL-list_expenses`, `TOOL-list_hiring_plans`, `TOOL-list_invoices`, `TOOL-list_objectives`, `TOOL-list_risks`, `TOOL-list_tasks`, `TOOL-record_decision`, `TOOL-record_expense`, `TOOL-record_kpi_measurement`, `TOOL-run_risk_scenario`, `TOOL-search_documents`, `TOOL-submit_document`, `TOOL-upsert_deal`, `TOOL-upsert_risk`.

**8 tool mới v2.1** (DEC-149 — D-03; tool metadata `schema, data_scope, classification, reversible, cost` áp dụng cho mọi tool). Đặc tả input/output, lớp và mức autonomy bổ sung vào 10 §7 ở Phase 3d; tool liên quan tiền **trần L2** (DEC-150).

| Tool | Mục đích |
|---|---|
| **TOOL-assign_task** | Giao/đổi người thực hiện task (L2) |
| **TOOL-get_kpi_status** | Đọc trạng thái KPI + evaluation band |
| **TOOL-get_cash_flow_forecast** | Đọc dự báo dòng tiền 13 tuần (DEC-148) |
| **TOOL-send_notification** | Gửi thông báo in-app/email |
| **TOOL-generate_report** | Tạo báo cáo weekly/monthly PDF/Excel (DEC-153) |
| **TOOL-request_approval** | Tạo ApprovalRequest theo ApprovalRule |
| **TOOL-approve_request** | Duyệt request — lớp APPROVAL, chỉ chạy khi người dùng bấm xác nhận |
| **TOOL-reject_request** | Từ chối request (bắt buộc lý do) — lớp APPROVAL |

Tổng **43 tool**.

### 4.9. Nguyên tắc sản phẩm — `P` (docs) ↔ `BRD-P` (DEC-146)

`P01–P09` là nguyên tắc **docs** (01 §6), dùng trong CLAUDE.md, code review và test — giữ nguyên. Khi trích nguyên tắc BRD dùng nhãn tham chiếu **`BRD-P01..P11`** (không phải prefix ID mới). Viết tắt "docs-P" chỉ dùng khi cần phân biệt trong văn bản.

| docs | Nguyên tắc docs (01 §6) | BRD tương ứng | BRD | Nguyên tắc BRD (§2.2, canonical) |
|---|---|---|---|---|
| P01 | Every number traceable | BRD-P06 | BRD-P01 | AI First |
| P02 | AI shows state (L1/L2/L3) | BRD-P04, BRD-P07 | BRD-P02 | API First |
| P03 | Capture once, use everywhere | BRD-P09 | BRD-P03 | Data First |
| P04 | Vietnamese-first | — | BRD-P04 | Human in the Loop |
| P05 | AI never fabricates numbers | BRD-P07 | BRD-P05 | Everything Actionable |
| P06 | AI within user's permission | BRD-P08 | BRD-P06 | Traceability |
| P07 | Exceptions first | BRD-P05 (một phần) | BRD-P07 | Explainable AI |
| P08 | Graceful degradation | BRD-P10 | BRD-P08 | Security by Design |
| P09 | Event-driven, vendor-agnostic | BRD-P02 (một phần) | BRD-P09 | Capture Once, Use Everywhere |
| — | — | — | BRD-P10 | Graceful Degradation |
| — | — | — | BRD-P11 | Measure Outcomes |

BRD-P01, BRD-P03, BRD-P11 chưa có nguyên tắc docs tương ứng — bổ sung vào 01 §6 ở Phase 3b (không đổi số P01–P09).

### 4.10. Use case (DEC-146 — mã BRD §14)

| ID | Tên (BRD) | BRD | v2 (DEC-153) | Ghi chú v2.0 |
|---|---|---|---|---|
| UC-01 | CEO Morning Briefing | P0 · MVP | v2.0 | Giờ briefing cấu hình được (GAP D-17, Phase 3b); không có nguồn Calendar |
| UC-02 | Meeting to Execution | P0 (transcript) · MVP | v2.0 lite | Transcript **mock upload thủ công**; không Calendar, không bot họp |
| UC-03 | KPI Underperformance | P0 · MVP | v2.0 | Insight 9 phần → Manager duyệt → task (DEC-149) |
| UC-04 | OKR At Risk | P0 | v2.0 | |
| UC-05 | CEO Strategic Question | P1 | v2.0 lite | Qua trợ lý AI + tool đọc; không agent orchestration (DEC-150) |
| UC-06 | Biên bản giấy đến thực thi | P0 · MVP | v2.0 | Giữ như v2.0.0 |
| UC-07 | Onboarding doanh nghiệp trong 1 ngày | P0 · MVP | v2.0 | Giữ như v2.0.0 (SCR-12) |
| UC-08 | Hóa đơn đến cảnh báo dòng tiền | P1 | v2.0 (bản demo) | Không email/XML (C6, C8 OUT); cập nhật dòng tiền 13 tuần (DEC-148) |

### 4.11. User Story (DEC-146 — mã BRD §15 canonical)

Mã `US-<AREA>-nnn`: **001–099 = mã BRD** (nội dung theo `_reference/SOURCE-BRD-v1.1.md` §15) · **101–199 = story chỉ có ở docs** (DEC-146, giữ area BRD; area docs-only `MGR`, `ADM`, `ALL` chỉ dùng dải 101+). Cột "v2" = phạm vi theo DEC-153: `v2.0` · `v2.0 lite` · `v2.1` (hoãn) · `OUT`. Tiêu chí nghiệm thu chi tiết ở 02 (và 04 cho `US-DC`).

#### 4.11.1. Story BRD (US-xxx-001..099)

| ID | Story (rút gọn BRD) | BRD | v2 | Ghi chú | Mã cũ docs |
|---|---|---|---|---|---|
| US-ORG-001 | CEO, tôi muốn định nghĩa cơ cấu tổ chức (công ty, phòng ban, team, quản lý, nhân viên, reporting line) | P0 | v2.0 lite | Team/Position; không ma trận, không effective-dated — DEC-147 | — |
| US-ORG-002 | Admin, tôi muốn cấu hình vai trò và quyền | P0 | v2.0 lite | gán 10 role cố định; role tùy biến v2.1 — DEC-150 | — |
| US-ORG-003 | Admin, tôi muốn định nghĩa phạm vi truy cập của AI theo phòng ban và vai trò | P0 | v2.1 | quyền agent ∩ người — DEC-150 | — |
| US-ORG-004 | Admin, tôi muốn dựng cơ cấu từ sơ đồ tổ chức và danh sách nhân sự có sẵn | P0 | v2.0 | UC-07 | — |
| US-DC-001 | Employee, tôi muốn nhập dữ liệu qua form có kiểm tra tức thì | P0 | v2.0 |  | — |
| US-DC-002 | Manager, tôi muốn nói hoặc gõ một câu để AI tạo bản ghi, chỉ ghi sau khi tôi xác nhận | P0 | v2.0 lite | gõ v2.0; nói (C2) v2.1 — DEC-153 | — |
| US-DC-003 | User, tôi muốn tải PDF, Word, ảnh để AI tự trích xuất dữ liệu | P0 | v2.0 |  | — |
| US-DC-004 | Manager, tôi muốn tải biên bản họp để AI tạo task, giao người và đặt hạn | P0 | v2.0 |  | — |
| US-DC-005 | Manager, tôi muốn tải file kế hoạch KPI/OKR hiện có thay vì nhập lại | P0 | v2.0 |  | — |
| US-DC-006 | Reviewer, tôi muốn xem tài liệu gốc cạnh dữ liệu AI trích để duyệt nhanh | P0 | v2.0 |  | — |
| US-DC-007 | Admin, tôi muốn import danh sách từ Excel với AI tự map cột | P0 | v2.0 |  | — |
| US-DC-008 | Admin, tôi muốn cấu hình loại tài liệu, schema và ngưỡng tự ghi không cần code | P0 | v2.0 |  | — |
| US-DC-009 | Employee, tôi muốn chụp ảnh chứng từ trên điện thoại để gửi vào hệ thống | P0 | v2.0 |  | US-EMP-02 |
| US-DC-010 | Finance, tôi muốn tải hoặc chuyển tiếp hóa đơn để AI ghi chi phí và công nợ | P1 | v2.0 | UC-08 bản demo | US-DC-009 |
| US-DC-011 | Legal/Sales, tôi muốn tải hợp đồng để AI trích giá trị, mốc thanh toán, hạn gia hạn | P1 | v2.0 |  | US-DC-010 |
| US-DC-012 | bộ phận, tôi muốn chuyển tiếp email có đính kèm vào hệ thống | P1 | OUT | C6 email — 01 §3 | — |
| US-FIN-001 | Finance Manager, tôi muốn quản lý doanh thu và chi phí | P0 Lite | v2.0 |  | US-CFO-01 |
| US-FIN-002 | Finance Manager, tôi muốn quản lý ngân sách | P0 Lite | v2.0 |  | US-CFO-02 |
| US-FIN-003 | CFO, tôi muốn theo dõi dòng tiền và runway | P0 | v2.0 | gồm dòng tiền 13 tuần — DEC-148 | — |
| US-FIN-004 | CEO, tôi muốn AI phân tích hiệu quả tài chính | P1 | v2.1 |  | — |
| US-FIN-005 | CEO, tôi muốn AI phát hiện rủi ro tài chính | P1 | v2.1 |  | — |
| US-HR-001 | HR, tôi muốn quản lý vòng đời nhân sự | P1 | v2.0 lite | hồ sơ + lịch sử lương; vòng đời đầy đủ v2.1 | — |
| US-HR-002 | HR, tôi muốn quản lý vị trí trong tổ chức | P0 | v2.0 | DEC-147 | — |
| US-HR-003 | Manager, tôi muốn xem workload của nhân viên | P0 | v2.0 |  | — |
| US-HR-004 | CEO, tôi muốn AI nhận diện rủi ro nhân lực | P1 | v2.1 |  | — |
| US-HR-005 | HR, tôi muốn xác định thiếu hụt kỹ năng | P1 | v2.1 | dữ liệu kỹ năng có ở v2.0 (ENT-EmployeeSkill) | — |
| US-SAL-001 | Sales, tôi muốn quản lý lead | P1 | v2.1 |  | — |
| US-SAL-002 | Sales, tôi muốn quản lý cơ hội | P0 | v2.0 |  | US-SAL-01 |
| US-SAL-003 | Sales Manager, tôi muốn theo dõi pipeline | P0 | v2.0 |  | US-SAL-03 |
| US-SAL-004 | CEO, tôi muốn AI dự báo doanh thu | P1 | v2.1 |  | — |
| US-SAL-005 | Sales Manager, tôi muốn AI gợi ý next-best-action | P1 | v2.1 |  | — |
| US-CUS-001 | CEO, tôi muốn biết khách nào có nguy cơ churn hoặc cần tôi follow-up | P1 | v2.1 |  | — |
| US-PTN-001 | Partner Manager, tôi muốn theo dõi hiệu quả và hoa hồng đối tác | P1 | OUT | Partner — GAP C-24 | — |
| US-PRC-001 | Trưởng phòng, tôi muốn tạo đề nghị mua sắm và theo dõi phê duyệt | P1 | OUT | Procurement — 01 §3 | — |
| US-CTR-001 | CFO, tôi muốn được nhắc trước hạn thanh toán và gia hạn hợp đồng | P1 | v2.1 | contract xuyên domain — DEC-148 | — |
| US-PRD-001 | Product Manager, tôi muốn quản lý roadmap | P1 | v2.0 | Must — DEC-153 | US-PRD-01 |
| US-PRD-002 | Product Manager, tôi muốn quản lý yêu cầu | P1 | v2.1 |  | — |
| US-PRD-003 | Product Manager, tôi muốn AI phân tích phản hồi khách hàng | P1 | v2.1 |  | — |
| US-PRD-004 | CPO, tôi muốn AI nhận diện rủi ro sản phẩm | P1 | v2.1 |  | — |
| US-ENG-001 | Engineering Manager, tôi muốn quản lý dự án kỹ thuật | P1 | OUT | Technical domain — GAP C-24 | — |
| US-ENG-002 | Engineering Manager, tôi muốn theo dõi delivery | P1 | OUT | Technical domain | — |
| US-ENG-003 | CTO, tôi muốn theo dõi technical debt | P1 | OUT | Technical domain | — |
| US-ENG-004 | CTO, tôi muốn AI phát hiện rủi ro delivery | P1 | OUT | Technical domain | — |
| US-GOV-001 | Governance Manager, tôi muốn quản lý chính sách và control | P2 | OUT | P2 | — |
| US-GOV-002 | Compliance Manager, tôi muốn theo dõi bằng chứng | P2 | OUT | P2 | — |
| US-GOV-003 | Risk Manager, tôi muốn quản lý rủi ro doanh nghiệp | P1 | v2.0 | Must — DEC-153 | US-RSK-01 |
| US-GOV-004 | CEO, tôi muốn AI tóm tắt rủi ro quản trị | P1 | v2.1 |  | — |
| US-STR-001 | CEO, tôi muốn định nghĩa mục tiêu chiến lược | P0 | v2.0 | DEC-147 | — |
| US-STR-002 | CEO, tôi muốn định nghĩa initiative chiến lược | P0 | v2.0 | ENT-Initiative — DEC-147 | — |
| US-STR-003 | CEO, tôi muốn theo dõi thực thi chiến lược | P0 | v2.0 |  | — |
| US-STR-004 | CEO, tôi muốn AI đánh giá thực thi chiến lược và chạy mô phỏng what-if | P1 | v2.1 | what-if runway/rủi ro đã có (US-CEO-104) | — |
| US-KPI-001 | CEO/Manager, tôi muốn định nghĩa KPI | P0 | v2.0 |  | — |
| US-KPI-002 | Manager, tôi muốn cấu hình target KPI | P0 | v2.0 | ENT-KPITarget | — |
| US-KPI-003 | Manager, tôi muốn cấu hình trọng số KPI | P0 | v2.0 |  | — |
| US-KPI-004 | Manager, tôi muốn cấu hình phương pháp đo và nguồn dữ liệu KPI | P0 | v2.0 |  | — |
| US-KPI-005 | Manager, tôi muốn theo dõi giá trị thực tế KPI | P0 | v2.0 |  | — |
| US-KPI-006 | Manager, tôi muốn đánh giá KPI theo rule | P0 | v2.0 | evaluation bands — DEC-147 | — |
| US-KPI-007 | CEO, tôi muốn so sánh KPI giữa phòng ban | P0 | v2.0 |  | — |
| US-KPI-008 | AI, tôi muốn phát hiện bất thường KPI | P0 | v2.0 | insight | — |
| US-KPI-009 | AI, tôi muốn xác định nguyên nhân gốc của KPI yếu | P0 | v2.0 | insight 9 phần — DEC-149 | — |
| US-KPI-010 | AI, tôi muốn khuyến nghị hành động khắc phục | P0 | v2.0 |  | — |
| US-OKR-001 | CEO, tôi muốn định nghĩa Objective công ty | P0 | v2.0 |  | — |
| US-OKR-002 | Manager, tôi muốn định nghĩa Objective phòng ban | P0 | v2.0 |  | — |
| US-OKR-003 | Manager, tôi muốn định nghĩa Key Result | P0 | v2.0 |  | — |
| US-OKR-004 | Manager, tôi muốn theo dõi tiến độ KR | P0 | v2.0 |  | — |
| US-OKR-005 | CEO, tôi muốn xem sơ đồ alignment OKR | P0 | v2.0 |  | — |
| US-OKR-006 | Employee, tôi muốn cập nhật tiến độ OKR (kể cả bằng lời nói) | P0 | v2.0 lite | bằng lời nói v2.1 | US-EMP-03 |
| US-OKR-007 | Manager, tôi muốn thực hiện check-in OKR | P0 | v2.0 |  | — |
| US-OKR-008 | AI, tôi muốn phát hiện OKR có rủi ro | P0 | v2.0 |  | — |
| US-OKR-009 | AI, tôi muốn khuyến nghị hành động khắc phục | P0 | v2.0 |  | — |
| US-PERF-001 | CEO/HR, tôi muốn chọn khung KPI, OKR hoặc hybrid cho từng phòng ban | P0 | v2.1 | khung KPI/OKR theo phòng ban (GAP C-06) | — |
| US-PERF-002 | HR, tôi muốn định nghĩa chu kỳ đánh giá | P1 | v2.1 |  | — |
| US-PERF-003 | Employee, tôi muốn tự đánh giá | P1 | v2.1 |  | — |
| US-PERF-004 | Manager, tôi muốn đánh giá nhân viên với bằng chứng do AI tổng hợp | P1 | v2.1 |  | — |
| US-PERF-005 | HR, tôi muốn thực hiện calibration | P1 | v2.1 |  | — |
| US-PERF-006 | CEO, tôi muốn AI phân tích hiệu suất toàn tổ chức | P0 | v2.1 | AI không chấm điểm cá nhân — DEC-149 | — |
| US-TASK-001 | Manager, tôi muốn tạo và giao task | P0 | v2.0 |  | — |
| US-TASK-002 | Employee, tôi muốn quản lý task của mình | P0 | v2.0 |  | US-EMP-01 |
| US-TASK-003 | Manager, tôi muốn xem workload và người quá tải | P0 | v2.0 |  | US-MGR-02 |
| US-TASK-004 | AI, tôi muốn đề xuất phân bổ lại task | P0 | v2.0 | gợi ý L1 | — |
| US-TASK-005 | AI, tôi muốn phát hiện task quá hạn và nhắc việc | P0 | v2.0 |  | — |
| US-TASK-006 | CEO, tôi muốn xem tình trạng thực thi toàn doanh nghiệp | P0 | v2.0 |  | — |
| US-MTG-001 | User, tôi muốn AI tóm tắt cuộc họp từ transcript hoặc biên bản | P0 | v2.0 | transcript mock upload — DEC-153 | — |
| US-MTG-002 | Manager, tôi muốn AI trích quyết định và action item rồi giao việc | P0 | v2.0 |  | — |
| US-MTG-003 | User, tôi muốn AI tham gia Google Meet để ghi và tóm tắt | P1 | OUT | Meet bot | — |
| US-CAL-001 | User, tôi muốn đồng bộ Google/Outlook Calendar và thấy deadline trên lịch | P0 | v2.1 | DEC-153 | — |
| US-CAL-002 | User, tôi muốn AI phát hiện trùng lịch và nhắc sự kiện quan trọng | P0 | v2.1 | DEC-153 | — |
| US-AI-001 | AI Agent, tôi muốn khám phá các tool khả dụng | P0 | v2.0 |  | — |
| US-AI-002 | AI Agent, tôi muốn truy xuất dữ liệu doanh nghiệp được phép | P0 | v2.0 |  | — |
| US-AI-003 | AI Agent, tôi muốn thực hiện hành động được phép | P0 | v2.0 |  | — |
| US-AI-004 | Admin, tôi muốn kiểm soát agent nào dùng tool nào ở Autonomy Level nào | P0 | v2.0 lite | tool × role; theo agent v2.1 — DEC-150 | US-ADM-02 |
| US-AI-005 | Admin, tôi muốn cấu hình phê duyệt cho tool tác động cao | P0 | v2.0 | 2 người duyệt cho finance > ngưỡng — DEC-149 | — |
| US-AI-006 | Admin, tôi muốn audit mọi tool call của AI | P0 | v2.0 |  | — |
| US-AI-007 | Admin, tôi muốn tắt toàn bộ hành động của AI bằng một thao tác | P0 | v2.0 | thêm kill switch per-agent — DEC-149 | US-ADM-03 |
| US-AI-008 | Admin, tôi muốn theo dõi chất lượng và chi phí AI theo agent | P0 | v2.0 lite | 1 agent profile — DEC-150 | — |
| US-CEO-001 | CEO, tôi muốn hỏi bằng ngôn ngữ tự nhiên và nhận câu trả lời có nguồn | P0 | v2.0 |  | US-CEO-03 |
| US-CEO-002 | CEO, tôi muốn nhận briefing hằng ngày | P0 | v2.0 |  | US-CEO-02 |
| US-CEO-003 | CEO, tôi muốn AI tóm tắt hiệu suất công ty và rủi ro | P0 | v2.0 |  | — |
| US-CEO-004 | CEO, tôi muốn AI khuyến nghị hành động chiến lược | P0 | v2.0 |  | — |
| US-CEO-005 | CEO, tôi muốn AI tạo task và nhắc cam kết | P0 | v2.0 |  | — |
| US-CEO-006 | CEO, tôi muốn biết quyết định nào đang chờ mình | P0 | v2.0 | hàng chờ phê duyệt — DEC-153 | — |
| US-CEO-007 | CEO, tôi muốn mọi con số AI báo cáo đều truy được nguồn gốc | P0 | v2.0 |  | US-DC-011 |
| US-CEO-008 | CEO, tôi muốn xem lại quyết định cũ và kết quả thực tế | P0 | v2.0 lite | Decision review_at | — |
| US-RPT-001 | CEO, tôi muốn tạo báo cáo điều hành và HĐQT | P0 | v2.0 lite | weekly/monthly PDF + Excel — DEC-153 | — |
| US-RPT-002 | Manager, tôi muốn tạo báo cáo phòng ban | P0 | v2.0 lite |  | — |
| US-RPT-003 | HR, tôi muốn báo cáo hiệu suất | P1 | v2.1 |  | — |
| US-RPT-004 | CFO, tôi muốn báo cáo tài chính quản trị | P1 | v2.1 |  | — |
| US-RPT-005 | AI, tôi muốn tự tạo báo cáo định kỳ | P0 | v2.0 | báo cáo định kỳ tự động | — |

#### 4.11.2. Story chỉ có ở docs (US-xxx-101..199)

| ID | Story | v2 | Mã cũ docs |
|---|---|---|---|
| US-CEO-101 | Toàn cảnh 5 trụ F.O.C.U.S | v2.0 | US-CEO-01 |
| US-CEO-102 | Hỏi runway nếu không có doanh thu mới | v2.0 | US-CEO-04 |
| US-CEO-103 | Drill-down ≤ 3 click tới tài liệu gốc | v2.0 | US-CEO-05 |
| US-CEO-104 | What-if rủi ro liên miền | v2.0 | US-CEO-06 |
| US-CEO-105 | Chấp nhận rủi ro kèm lý do | v2.0 | US-CEO-07 |
| US-CEO-106 | Đặt mục tiêu doanh thu theo kỳ | v2.0 | US-CEO-08 |
| US-FIN-101 | Dự báo theo horizon × 3 kịch bản | v2.0 | US-CFO-03 |
| US-FIN-102 | Cảnh báo Net Burn vượt dự báo | v2.0 | US-CFO-04 |
| US-FIN-103 | Hóa đơn & trạng thái thanh toán | v2.0 | US-CFO-05 |
| US-FIN-104 | Duyệt kế hoạch tuyển dụng | v2.0 | US-CFO-06 |
| US-SAL-101 | Danh sách khách hàng | v2.0 | US-SAL-02 |
| US-SAL-102 | Cảnh báo pipeline coverage / win rate | v2.0 | US-SAL-04 |
| US-HR-101 | Hồ sơ nhân viên + lịch sử lương | v2.0 | US-HR-01 |
| US-HR-102 | Kế hoạch tuyển dụng vs định biên | v2.0 | US-HR-02 |
| US-HR-103 | Cảnh báo tuyển dụng trễ | v2.0 | US-HR-03 |
| US-HR-104 | Turnover năm hóa + cảnh báo | v2.0 | US-HR-04 |
| US-PRD-101 | Chỉ số sản phẩm theo kỳ | v2.0 | US-PRD-02 |
| US-PRD-102 | Cảnh báo churn bất thường | v2.0 | US-PRD-03 |
| US-GOV-101 | Rủi ro tự sinh từ event (trạng thái proposed — DEC-148) | v2.0 | US-RSK-02 |
| US-GOV-102 | Mitigation & xác nhận cảnh báo | v2.0 | US-RSK-03 |
| US-MGR-101 | Nhập dữ liệu của bộ phận | v2.0 | US-MGR-01 |
| US-MGR-102 | Duyệt dữ liệu/check-in của đơn vị | v2.0 | US-MGR-03 |
| US-ADM-101 | Tạo user, gán role (không self-register) | v2.0 | US-ADM-01 |
| US-ADM-102 | Audit log + preview quyền | v2.0 | US-ADM-04 |
| US-ALL-101 | Chỉ thấy dữ liệu trong phạm vi, kể cả qua AI | v2.0 | US-ALL-01 |
| US-ALL-102 | Xem / xóa hội thoại AI | v2.0 | US-ALL-02 |
| US-ALL-103 | Đánh giá câu trả lời AI | v2.0 | US-ALL-03 |
| US-ALL-104 | Dashboard vẫn chạy khi AI/module lỗi | v2.0 | US-ALL-04 |
| US-AI-101 | ⌘K hiểu ngữ cảnh | v2.0 | US-AI-01 |
| US-AI-102 | Thấy AI đang làm gì, dừng được | v2.0 | US-AI-02 |
| US-AI-103 | Phân biệt L1 / L2 / L3 | v2.0 | US-AI-03 |
| US-AI-104 | Hoàn tác L3 trong 24 giờ | v2.0 | US-AI-04 |
| US-AI-105 | Trả lời đúng ngôn ngữ, báo thiếu dữ liệu | v2.0 | US-AI-05 |

### 4.12. FR-DC — Data Capture (DEC-146 — mã BRD §6.4–6.6 canonical)

**FR-DC-01..23 mang nghĩa BRD.** Story/FR chỉ có ở docs dùng dải **FR-DC-101+**. Cột "Mã cũ" = số trong 04 v2.0.0. Cho tới khi Phase 3c/3d cập nhật xong, 04, 09, 14 và DEC-123/138 **còn dùng mã cũ** — đọc qua bảng này.

| ID | Nội dung (BRD) | v2 | Mã cũ 04 v2.0.0 |
|---|---|---|---|
| FR-DC-01 | Form sinh từ schema, validate tại chỗ | v2.0 | 04 |
| FR-DC-02 | AI gợi ý giá trị, cảnh báo bản ghi có thể trùng | v2.0 | — (mới) |
| FR-DC-03 | Nhập ngôn ngữ tự nhiên qua AI, xác nhận trước khi ghi | v2.0 lite (gõ; nói v2.1) | 03 |
| FR-DC-04 | Lưu nháp; sửa hàng loạt dạng lưới | v2.0 lite (nháp; lưới OUT — DEC-151) | — (mới) |
| FR-DC-05 | Audit mọi thay đổi; lý do bắt buộc với trường tài chính | v2.0 (DEC-151) | 22 (phần audit) |
| FR-DC-06 | Nhập trên mobile cho tác vụ thường xuyên | v2.0 (PWA) | — (mới) |
| FR-DC-07 | Định dạng PDF/DOC/ảnh/XLSX/CSV; 50 MB · 100 file · 300 trang | v2.0 | 01, 07 |
| FR-DC-08 | Tiền xử lý: mã độc, trùng hash, xoay/khử nghiêng, tách trang | v2.0 | 02, 05, 06 |
| FR-DC-09 | AI phân loại; chọn trước loại thì bỏ qua bước này | v2.0 (DEC-151) | 08 |
| FR-DC-10 | Tách một file nhiều tài liệu; gộp nhiều ảnh | v2.0 | 09 |
| FR-DC-11 | Trích trường, bảng, checkbox, chữ ký/con dấu; viết tay luôn review | v2.0 (DEC-151) | 10, 11 |
| FR-DC-12 | Mỗi trường: giá trị, confidence, vị trí nguồn, đoạn gốc | v2.0 | — (đã có trong 10 cũ) |
| FR-DC-13 | Chuẩn hóa ngữ cảnh Việt Nam | v2.0 (địa chỉ hành chính OUT — GAP B-11) | 12 |
| FR-DC-14 | Kiểm tra nghiệp vụ, so khớp master data, trùng hóa đơn | v2.0 | 13, 14 |
| FR-DC-15 | Định tuyến theo ngưỡng confidence × loại × trường | v2.0 | 15 |
| FR-DC-16 | Trường trọng yếu luôn qua người | v2.0 | 16 |
| FR-DC-17 | Ghi domain chỉ qua Tool/Action Registry | v2.0 | 21 |
| FR-DC-18 | Import Excel/CSV: map cột, xem trước, lỗi theo dòng | v2.0 | 18 |
| FR-DC-19 | Review song song, tô sáng vùng nguồn | v2.0 | 19 |
| FR-DC-20 | Màu theo confidence; "Chấp nhận tất cả trường tin cậy cao"; bàn phím | v2.0 | — (một phần 19) |
| FR-DC-21 | Hàng chờ theo phòng ban/vai trò, SLA, nhắc việc, escalation | v2.0 (DEC-151) | 17 |
| FR-DC-22 | Sửa, từ chối, đổi loại, tách/gộp, chuyển người khác | v2.0 (DEC-151) | 20 |
| FR-DC-23 | Link "Xem tài liệu gốc"; AI trích đúng trang | v2.0 | — (US-DC cũ 011) |
| FR-DC-101 | Hoàn tác commit ≤ 7 ngày (DEC-134) | v2.0 | 22 (phần hoàn tác) |
| FR-DC-102 | Cấu hình doc type/schema/ngưỡng; học từ chỉnh sửa | v2.0 (không học theo vendor — DEC-151) | 23 |

Không có mã cũ nào được tái dùng với nghĩa khác: mọi FR-DC-01..23 cũ phải đổi qua bảng này (DEC-146).

### 4.13. Bảng ánh xạ mã cũ → mã mới (DEC-146)

Áp dụng cho mọi tham chiếu trong 01–14, DEC cũ và CLAUDE.md. Khi một file được cập nhật ở Phase 3b–3d, mã cũ được thay bằng mã mới; tới lúc đó đọc mã cũ qua bảng này. **UC-06/07/08, ENT-*, METRIC-*, SCR-01..28, EVT, EP, TOOL không đổi mã.**

#### 4.13.1. User Story (50 mã)

| Mã cũ (v2.0.0) | Mã mới | Story |
|---|---|---|
| US-CEO-01 | US-CEO-101 | Toàn cảnh 5 trụ F.O.C.U.S |
| US-CEO-02 | US-CEO-002 | Insight/briefing đầu dashboard |
| US-CEO-03 | US-CEO-001 | Hỏi AI liên phòng ban kèm nguồn |
| US-CEO-04 | US-CEO-102 | Hỏi runway nếu không có doanh thu mới |
| US-CEO-05 | US-CEO-103 | Drill-down ≤ 3 click tới tài liệu gốc |
| US-CEO-06 | US-CEO-104 | What-if rủi ro liên miền |
| US-CEO-07 | US-CEO-105 | Chấp nhận rủi ro kèm lý do |
| US-CEO-08 | US-CEO-106 | Đặt mục tiêu doanh thu theo kỳ |
| US-CFO-01 | US-FIN-001 | Ghi doanh thu, chi phí, tiền mặt |
| US-CFO-02 | US-FIN-002 | Ngân sách theo phòng ban + cảnh báo |
| US-CFO-03 | US-FIN-101 | Dự báo theo horizon × 3 kịch bản |
| US-CFO-04 | US-FIN-102 | Cảnh báo Net Burn vượt dự báo |
| US-CFO-05 | US-FIN-103 | Hóa đơn & trạng thái thanh toán |
| US-CFO-06 | US-FIN-104 | Duyệt kế hoạch tuyển dụng |
| US-SAL-01 | US-SAL-002 | Quản lý deal & giai đoạn |
| US-SAL-02 | US-SAL-101 | Danh sách khách hàng |
| US-SAL-03 | US-SAL-003 | Pipeline, win rate, hiệu suất |
| US-SAL-04 | US-SAL-102 | Cảnh báo pipeline coverage / win rate |
| US-HR-01 | US-HR-101 | Hồ sơ nhân viên + lịch sử lương |
| US-HR-02 | US-HR-102 | Kế hoạch tuyển dụng vs định biên |
| US-HR-03 | US-HR-103 | Cảnh báo tuyển dụng trễ |
| US-HR-04 | US-HR-104 | Turnover năm hóa + cảnh báo |
| US-PRD-01 | US-PRD-001 | Sản phẩm, tính năng, roadmap, release |
| US-PRD-02 | US-PRD-101 | Chỉ số sản phẩm theo kỳ |
| US-PRD-03 | US-PRD-102 | Cảnh báo churn bất thường |
| US-RSK-01 | US-GOV-003 | Ghi rủi ro, tự chấm điểm |
| US-RSK-02 | US-GOV-101 | Rủi ro tự sinh từ event (trạng thái proposed — DEC-148) |
| US-RSK-03 | US-GOV-102 | Mitigation & xác nhận cảnh báo |
| US-MGR-01 | US-MGR-101 | Nhập dữ liệu của bộ phận |
| US-MGR-02 | US-TASK-003 | Heatmap workload + gợi ý chuyển task |
| US-MGR-03 | US-MGR-102 | Duyệt dữ liệu/check-in của đơn vị |
| US-EMP-01 | US-TASK-002 | "Việc hôm nay" của tôi |
| US-EMP-02 | US-DC-009 | Gửi chứng từ ≤ 3 chạm |
| US-EMP-03 | US-OKR-006 | Check-in KR / cập nhật task ≤ 30 giây |
| US-ADM-01 | US-ADM-101 | Tạo user, gán role (không self-register) |
| US-ADM-02 | US-AI-004 | Cấu hình autonomy tool × role × ngưỡng |
| US-ADM-03 | US-AI-007 | Kill switch |
| US-ADM-04 | US-ADM-102 | Audit log + preview quyền |
| US-ALL-01 | US-ALL-101 | Chỉ thấy dữ liệu trong phạm vi, kể cả qua AI |
| US-ALL-02 | US-ALL-102 | Xem / xóa hội thoại AI |
| US-ALL-03 | US-ALL-103 | Đánh giá câu trả lời AI |
| US-ALL-04 | US-ALL-104 | Dashboard vẫn chạy khi AI/module lỗi |
| US-AI-01 | US-AI-101 | ⌘K hiểu ngữ cảnh |
| US-AI-02 | US-AI-102 | Thấy AI đang làm gì, dừng được |
| US-AI-03 | US-AI-103 | Phân biệt L1 / L2 / L3 |
| US-AI-04 | US-AI-104 | Hoàn tác L3 trong 24 giờ |
| US-AI-05 | US-AI-105 | Trả lời đúng ngôn ngữ, báo thiếu dữ liệu |
| US-DC-009 | US-DC-010 | Hóa đơn → chi phí & công nợ (CFO) |
| US-DC-010 | US-DC-011 | Hợp đồng → giá trị, mốc, gia hạn |
| US-DC-011 | US-CEO-007 | Mọi con số AI truy được nguồn |

#### 4.13.2. FR-DC (23 mã cũ)

| Mã cũ (04 v2.0.0) | Mã mới | Số cũ đổi nghĩa? |
|---|---|---|
| FR-DC-01 | FR-DC-07 | **có** |
| FR-DC-02 | FR-DC-08 | **có** |
| FR-DC-03 | FR-DC-03 | không |
| FR-DC-04 | FR-DC-01 | **có** |
| FR-DC-05 | FR-DC-08 | **có** |
| FR-DC-06 | FR-DC-08 | **có** |
| FR-DC-07 | FR-DC-07 | không |
| FR-DC-08 | FR-DC-09 | **có** |
| FR-DC-09 | FR-DC-10 | **có** |
| FR-DC-10 | FR-DC-11, FR-DC-12 | **có** |
| FR-DC-11 | FR-DC-11 | không |
| FR-DC-12 | FR-DC-13 | **có** |
| FR-DC-13 | FR-DC-14 | **có** |
| FR-DC-14 | FR-DC-14 | không |
| FR-DC-15 | FR-DC-15 | không |
| FR-DC-16 | FR-DC-16 | không |
| FR-DC-17 | FR-DC-21 | **có** |
| FR-DC-18 | FR-DC-18 | không |
| FR-DC-19 | FR-DC-19, FR-DC-20 | không |
| FR-DC-20 | FR-DC-22 | **có** |
| FR-DC-21 | FR-DC-17 | **có** |
| FR-DC-22 | FR-DC-05, FR-DC-101 | **có** |
| FR-DC-23 | FR-DC-102 | **có** |

FR-DC-22 cũ tách làm hai: phần audit → FR-DC-05, phần hoàn tác → FR-DC-101. FR-DC-02/05/06 cũ (malware, chống trùng, text-layer/OCR) gộp vào FR-DC-08 (tiền xử lý); FR-DC-13/14 cũ gộp vào FR-DC-14.



---

## 5. Doc Loading Matrix (tóm tắt)

Chi tiết đầy đủ ở `11-AGENT-WORKFLOW.md` §3.

| Task type | Bắt buộc load | Từ chối nếu thiếu |
|---|---|---|
| Plan sprint | 00, 01, 09, 13 | 13 |
| Scaffold / hạ tầng | 00, 01, 07, 10 | 07 |
| Code domain module (F/O/C/U/S) | 00, 01, 03, 05, 10 | 03, 10 |
| Code dashboard | 00, 01, 03, 06, 10 | 03, 10 |
| Code IDP | 00, 01, 04, 05, 10 | 04, 10 |
| Code AI Core | 00, 01, 02, 07, 10 | 07, 10 |
| Code auth | 00, 01, 02, 10 | 02, 10 |
| Code UI | 00, 06, 10 | 06 |
| Seed data | 00, 01, 08 | 08 |
| Test | 10, 14 | 10, 14 |
| Audit doc | 12 | 12 |
| Review PR | 10, 14 + PR diff | 10, 14 |

---

## 6. 3 Gate bắt buộc

- **Gate A** — `12-DOC-AUDIT.md`: mọi file load phải `current`
- **Gate B** — `13-DECISION-LOG.md`: không có `open + blocking` ảnh hưởng task
- **Gate C** — `14-TEST-TRACEABILITY.md`: task có test mapping

Fail bất kỳ gate nào → task `BLOCKED`, không code. Chi tiết ở `CLAUDE.md` § Gotchas.

---

## 7. ⛔ Không load

| Đường dẫn | Lý do |
|---|---|
| Bất kỳ file status `archived` | Đã thay thế |

`_reference/` **được đọc** — là Canonical Source (DEC-144, DEC-145). Mâu thuẫn `docs/` ↔ `_reference/` → ưu tiên `_reference/` trừ khi có DEC mới hơn DEC-144 nói ngược lại (12 §X). Nếu cần thông tin không có trong `docs/` lẫn `_reference/` → raise vào `13-DECISION-LOG.md`.

---

## 8. Trạng thái hiện tại

| Mục | Trạng thái |
|---|---|
| Documentation | 🟡 Phase 3 cập nhật 2.1.0 theo DEC-146..153 (3a: 00, 05 → 3b → 3c → 3d); file chưa cập nhật còn dùng mã cũ — đọc qua §4.13 |
| Sprint hiện tại | **S0 — Nền tảng v2** (chưa bắt đầu) |
| Code | ⚠️ Code trên `main` là v1 (4 trụ, 5 role, monolith phẳng) — **lệch spec v2** (drift được human chấp nhận); build lại theo 09 |
| Backup v1 | Nhánh `v1` (commit `a5161f6`) |
| Blocking decisions | 0 open+blocking — xem `13-DECISION-LOG.md` |
| Doc audit status | Xem `12-DOC-AUDIT.md` |

---

## 9. Version

- **Version:** 2.1.0 (đề xuất — human bump status ở 12)
- **Last updated:** 2026-10-20
- **Applies to:** Aureon v2 (v2.0 demo-ready / v2.1 production-ready)
- **Maintainer:** @CyEyes
- **Change 2.1.0 (Phase 3a, DEC-146..153):** ID registry theo scheme BRD canonical — §4.9 P ↔ BRD-P, §4.10 UC-01..08, §4.11 US 108 mã BRD + 33 mã docs (101+), §4.12 FR-DC-01..23 nghĩa BRD + FR-DC-101/102, §4.13 bảng ánh xạ cũ → mới (50 US, 23 FR-DC); §4.3 79 entity (15 mới, cột `#` chỉ để tra cứu, giữ `ENT-<Name>`); §4.2 32 metric (METRIC-DQ-01); §4.4 SCR-29..31; §4.5 28 event; §4.6 dải EP-120..129; §4.8 43 tool. "Domain 22" → D03 (GAP A-02); §7 bỏ "Không load `_reference/`" (GAP A-04).
- **Change 2.0.0:** viết lại cho Aureon v2 (DEC-124..137).
