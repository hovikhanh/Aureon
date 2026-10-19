# 00 — INDEX

> File này là **bản đồ tài liệu** và **sổ đăng ký ID** (ID registry) của Aureon v2 cho AI Agent.
> Mục đích: agent biết file nào cần đọc cho task nào, KHÔNG đọc thừa, và dùng đúng một bộ ID xuyên suốt 14 spec.
> Aureon v2 = hợp nhất **A-EMS** (BRD v1.0) + **AI-EOS** (BRD v1.1, Domain 22 IDP) + đề xuất UI/UX AI-EOS, theo DEC-124 → DEC-137.

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
| `04-IDP-FEATURE-SPEC.md` | Domain 22 — Data Capture & IDP: 5 kênh, pipeline, review, Action Registry | Task IDP, import, review |
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
| `US-<AREA>-xx[x]` | User Story (`CEO, CFO, SAL, HR, PRD, RSK, MGR, EMP, ADM, ALL, AI, DC`) | US-RSK-02, US-DC-006 | 02, 04 |
| `UC-xx` | Use Case | UC-07 | 01, 04 |
| `F1`…`F5` | Luồng UX chính | F2 | 06 |
| `FR-<AREA>-xx` | Functional Requirement (`AUTH, FIN, SAL, HR, PRD, RSK, AI, DSH, NTF, DC`) | FR-FIN-08, FR-DC-14 | 02, 03, 04 |
| `BR-<AREA>-xx` | Business rule / công thức | BR-FIN-02 | 03 |
| `NFR-xx` | Yêu cầu phi chức năng | NFR-07 | 07 |
| `PIL-x` | Trụ F.O.C.U.S (`F, O, C, U, S`) | PIL-S | 03 |
| `METRIC-<FIN\|OPS\|HR\|CUS\|PRD\|RSK>-xx` | Metric | METRIC-PRD-02 | 03 |
| `ALERT-<FIN\|OPS\|HR\|CUS\|PRD\|RSK>-xx` | Alert (1-1 với metric cùng số) | ALERT-RSK-02 | 03 |
| `ENT-<Name>` | Entity | ENT-HiringPlan | 05 |
| `EVT-<domain>.<name>` | Domain event | EVT-hr.hiring_plan_delayed | 05, 10 |
| `TOOL-<name>` | AI tool trong Tool Registry | TOOL-get_finance_dashboard | 10 |
| `ACT-<name>` | Action trong Action Registry (ghi dữ liệu) | ACT-create_invoice | 04 |
| `SCR-xx` | Screen | SCR-10 | 06 |
| `EP-xx` / `EP-1xx` | API Endpoint (2–3 chữ số theo dải §4.6) | EP-110 | 10 |
| `T-xxx` | Build Task v2 (`T-0xx` = S0 … `T-5xx` = S5) | T-204 | 09 |
| `TC-<AREA>-xxx` | Test case | TC-RSK-003 | 14 |
| `DEC-xxx` | Decision | DEC-125 | 13 |

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

### 4.2. Trụ và metric (DEC-127)

| Trụ | Câu hỏi lãnh đạo | Metric |
|---|---|---|
| **PIL-F** Finance | Có đủ tiền, kiếm/tiêu hiệu quả? | METRIC-FIN-01 Doanh thu vs kế hoạch · 02 Biên LN gộp · 03 Cash runway · 04 DSO · 05 Công nợ quá hạn · 06 Chênh lệch ngân sách · 07 Net burn vs dự báo |
| **PIL-O** Operations & People | Đủ người, vận hành ổn? | METRIC-OPS-01 Task đúng hạn · 02 Dự án trễ · 03 Thực thi quyết định · METRIC-HR-01 Doanh thu/nhân sự · 02 Turnover năm hóa · 03 Quá tải · 04 Kế hoạch tuyển dụng trễ |
| **PIL-C** Customer & Growth | Giành và giữ được khách? | METRIC-CUS-01 Pipeline coverage · 02 Win rate · 03 NRR · 04 Tập trung doanh thu top 5 · 05 NPS · 06 Chu kỳ bán TB |
| **PIL-U** Product & Innovation | Sản phẩm tiến lên, được dùng thật? | METRIC-PRD-01 Adoption/MAU · 02 Churn · 03 Retention 30 ngày · 04 Roadmap đúng tiến độ · 05 Tính năng release trong kỳ |
| **PIL-S** Strategy & Risk | Điều gì làm hỏng kế hoạch, xử lý tới đâu? | METRIC-RSK-01 Rủi ro high/critical đang mở · 02 Rủi ro high chưa có chủ · 03 Rủi ro high > 30 ngày không có mitigation · 04 Điểm rủi ro tổng hợp · 05 Biện pháp quá hạn · 06 Strategy execution index |

Tổng **31 metric**; mỗi metric có đúng 1 alert cùng số (`ALERT-FIN-03` ↔ `METRIC-FIN-03`).

### 4.3. Entity theo schema (DEC-125)

| Schema | Entity |
|---|---|
| `auth` | ENT-User, ENT-Role, ENT-RefreshToken |
| `finance` | ENT-Revenue, ENT-Expense, ENT-Budget, ENT-Forecast, ENT-ForecastLine, ENT-Invoice, ENT-InvoiceLine, ENT-CashPosition |
| `sales` | ENT-Client, ENT-Deal, ENT-DealStageHistory, ENT-SalesTarget, ENT-Contract |
| `hr` | ENT-Department, ENT-Employee, ENT-SalaryHistory, ENT-HiringPlan |
| `product` | ENT-Product, ENT-Feature, ENT-RoadmapItem, ENT-Release, ENT-ProductMetric |
| `risk` | ENT-Risk, ENT-RiskAssessment, ENT-Mitigation, ENT-Scenario |
| `execution` | ENT-Meeting, ENT-Decision, ENT-Task, ENT-Project, ENT-Objective, ENT-KeyResult, ENT-CheckIn, ENT-KPI, ENT-KPIMeasurement |
| `ai` | ENT-Conversation, ENT-Message, ENT-ToolCallLog, ENT-Feedback, ENT-Insight, ENT-AIAction, ENT-AutonomyPolicy, ENT-ModelCallLog |
| `idp` | ENT-SourceDocument, ENT-DocumentPage, ENT-DocumentType, ENT-ExtractionSchema, ENT-ExtractionJob, ENT-ExtractedField, ENT-ExtractionReview, ENT-ValidationRule, ENT-ImportBatch |
| `platform` | ENT-Metric, ENT-MetricValue, ENT-Alert, ENT-DataLineage, ENT-AuditLog, ENT-Notification, ENT-OutboxEvent, ENT-ProcessedEvent, ENT-SystemSetting |

### 4.4. Màn hình

| ID | Màn hình | ID | Màn hình |
|---|---|---|---|
| SCR-01 | Trang chủ theo vai trò (Briefing) | SCR-15 | AI Control Center (autonomy, kill switch, ngân sách, provider) |
| SCR-02 | Trụ F — Finance | SCR-16 | Hỏi AI (trang Chat) + thanh ⌘K + Panel AI |
| SCR-03 | Trụ O — Operations & People | SCR-17 | Feed "AI đã làm" |
| SCR-04 | Trụ C — Customer & Growth | SCR-18 | Họp & biên bản → việc (UC-06) |
| SCR-05 | Trụ U — Product & Innovation | SCR-19 | Công việc & Workload heatmap |
| SCR-06 | Trụ S — Strategy & Risk | SCR-20 | Mục tiêu: OKR/KPI & check-in |
| SCR-07 | Chi tiết metric + lineage | SCR-21 | Sổ rủi ro & What-if |
| SCR-08 | Hộp thư dữ liệu (Data Inbox) | SCR-22 | Finance workspace |
| SCR-09 | Gửi dữ liệu (drop zone, chụp C4, nhập lời C2, form C1) | SCR-23 | Sales workspace |
| SCR-10 | Review song song | SCR-24 | HR workspace |
| SCR-11 | Import grid (C5) | SCR-25 | Product workspace |
| SCR-12 | Nạp doanh nghiệp (UC-07) | SCR-26 | Quản trị người dùng & vai trò |
| SCR-13 | Đăng nhập | SCR-27 | Cấu hình loại tài liệu / schema / ngưỡng |
| SCR-14 | Audit log | SCR-28 | Mobile shell (Briefing, chụp, duyệt, hỏi AI) |

### 4.5. Domain event (DEC-126)

`EVT-hr.employee_onboarded`, `EVT-hr.employee_terminated`, `EVT-hr.salary_updated`, `EVT-hr.hiring_plan_delayed`, `EVT-sales.deal_closed_won`, `EVT-sales.deal_closed_lost`, `EVT-finance.budget_exceeded`, `EVT-finance.invoice_paid`, `EVT-finance.forecast_updated`, `EVT-finance.burn_over_forecast`, `EVT-product.product_launched`, `EVT-product.feature_released`, `EVT-product.metric_anomaly`, `EVT-risk.risk_identified`, `EVT-risk.risk_level_changed`, `EVT-risk.risk_mitigated`, `EVT-execution.task_overdue`, `EVT-execution.kpi_measured`, `EVT-idp.document_committed`, `EVT-idp.document_rolled_back`, `EVT-platform.alert_raised`.

### 4.6. Dải EP

| Dải | Nhóm | Dải | Nhóm |
|---|---|---|---|
| EP-01..09 | System, Auth, User admin | EP-60..69 | Finance |
| EP-10..19 | Dashboard, metric, alert, lineage, briefing | EP-70..79 | Sales |
| EP-20..41 | IDP (giữ số v1) | EP-80..89 | HR |
| EP-42..49 | Execution (họp, quyết định, task, OKR, KPI) | EP-90..99 | Product |
| EP-50..59 | Config, audit, notification | EP-100..109 | Risk |
| | | EP-110..119 | AI Core |

### 4.7. Sprint và task

| Mốc | Dải task | Mục tiêu |
|---|---|---|
| S0 | T-001..T-099 | Nền tảng v2 (module, schema, RS256, outbox, ModelGateway đa provider) |
| S1 | T-101..T-199 | Domain F, C, O (Finance, Sales, HR, Execution) |
| S2 | T-201..T-299 | Domain U, S + Dashboard F.O.C.U.S |
| S3 | T-301..T-399 | Trợ lý AI + Autonomy |
| S4 | T-401..T-499 | IDP v2 |
| S5 | T-501..T-599 | UX, mobile PWA, demo data, phát hành |

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
| `_reference/SOURCE-*.md` | Đã hợp nhất vào v2 (DEC-124); ngoại lệ đọc đã hết hiệu lực |
| Bất kỳ file status `archived` | Đã thay thế |

Nếu cần thông tin không có trong `docs/` → raise vào `13-DECISION-LOG.md`.

---

## 8. Trạng thái hiện tại

| Mục | Trạng thái |
|---|---|
| Documentation | 🟢 Bộ spec v2 (2.0.0) — viết lại 2026-10-19 theo DEC-124..137 |
| Sprint hiện tại | **S0 — Nền tảng v2** (chưa bắt đầu) |
| Code | ⚠️ Code trên `main` là v1 (4 trụ, 5 role, monolith phẳng) — **lệch spec v2** (drift được human chấp nhận); build lại theo 09 |
| Backup v1 | Nhánh `v1` (commit `a5161f6`) |
| Blocking decisions | 0 open+blocking — xem `13-DECISION-LOG.md` |
| Doc audit status | Xem `12-DOC-AUDIT.md` |

---

## 9. Version

- **Version:** 2.0.0
- **Last updated:** 2026-10-19
- **Applies to:** Aureon v2
- **Maintainer:** @CyEyes
