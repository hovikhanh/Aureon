# AI-EOS Rebuild Plan — nhánh `ai-eos`

> **Mục đích:** viết lại bộ tài liệu 00–14 cho **đúng AI-EOS đầy đủ** (`_reference/SOURCE-BRD-v1.1.md` + `SOURCE-BRD-v1.1-Bổ sung.md` + `SOURCE-UIUX.md`), thay vì bản distill demo-ready v2.0/v2.1 đang nằm trên `main`.
> **Nhánh:** `ai-eos` (tách từ `main` @ `e394668` — bản demo-ready v2.1, giữ nguyên code + docs để làm baseline/fallback).
> **Trạng thái:** 🟡 Planning — chưa viết lại nội dung spec cho tới khi human duyệt kế hoạch này.
> **Ngày:** 2026-10-22 · **Maintainer:** @CyEyes

---

## 1. Vì sao rebuild

`main` (v2.1) là bản **distill có chủ đích thu hẹp** để demo trong 12 tuần: 5 trụ F.O.C.U.S, 10 role cố định, Modular Monolith, Autonomy L0–L3, 5 kênh C1–C5, ~9 doc type. BRD AI-EOS gốc rộng hơn nhiều. Nhánh `ai-eos` lấy **BRD làm khung chính** (không phải distill), bám sát:

- **28 domain / 5 lớp** (BRD §4) thay vì 6 domain module.
- **7 vai trò chuẩn + AI Agent là actor có identity riêng** (BRD §3.2), RBAC **+ ABAC**, field-level security.
- **Autonomy L0–L4** (BRD §11.6) — có L4 (bật cho tool đã chứng minh độ tin cậy ở phase 5).
- **AI Platform đầy đủ** (BRD §11.1): Orchestrator + Agent Runtime + nhiều agent chuyên trách + Memory + Prompt Management + Evaluation Engine + Policy/Approval/Audit Engine.
- **Data Capture C1–C10** (BRD §6.1) — gồm email, chat, XML hóa đơn, Drive sync, API/webhook.
- **Data Foundation** (BRD §13): Master Data Management, Metric Store/Semantic layer, lineage, freshness, event backbone, effective-dated history, data export.
- **Executive Intelligence** (BRD §12): CEO Assistant đa kênh (web/mobile/chat/voice), Daily Briefing, Management Loop, bộ chỉ số sức khỏe chuẩn, **Reporting D28** (PDF/Word/Excel/Google Docs), **Decision Log** + đối chiếu 30/60/90 ngày.
- **Governance & tuân thủ pháp lý VN** (BRD §17): NĐ 13/2023 (BVDLCN), DPIA, Luật ANM, Approval Matrix, audit trail bất biến.
- **11 nguyên tắc P01–P11** (BRD §2.2), **12 yêu cầu AI-R01–R12** (BRD §2.3), **10 mục tiêu BO-01–BO-10** (BRD §2.1).

---

## 2. Bản đồ 28 domain / 5 lớp (BRD §4–§12)

| Lớp | Domain | Ưu tiên BRD |
|---|---|---|
| **Nền tảng** | D01 Organization · D02 Administration & Security · D03 Data Capture & IDP · D04 Workflow & Approval Engine · D05 Notification · D06 Integration Hub | P0 (D04 nâng cao P1, D06 ngoài Google/MS P1) |
| **Điều hành** | D07 Strategy · D08 KPI · D09 OKR · D10 Performance | P0 (Performance cycle đầy đủ P1) |
| **Thực thi** | D11 Project/Task/Workload · D12 Meeting Intelligence · D13 Calendar · D14 Knowledge/Documents | P0 (AI dự họp P1) |
| **Vận hành KD** | D15 Finance · D16 HR · D17 Sales/Business · D18 Customer · D19 Partner · D20 Procurement/Vendor · D21 Contract Lifecycle · D22 Product · D23 Technical/Engineering | D15/D16/D17 P0 Lite; D18–D23 P1 |
| **Governance & Trí tuệ** | D24 Governance & Compliance · D25 Risk · **D26 AI Platform** · D27 CEO AI Assistant · D28 Reporting & Analytics | D26/D27/D28 P0; D25 P1; D24 P2 |

## 3. Vai trò (BRD §3.2) — khác `main` (10 role F.O.C.U.S)

7 vai trò chuẩn + AI Agent actor; doanh nghiệp tạo thêm vai trò tùy biến:

| Vai trò | Scope | AI Assistant | Ghi chú so với `main` |
|---|---|---|---|
| CEO | Toàn DN | CEO Assistant | Giữ |
| Executive / Director | Khối / phòng ban | Department Copilot | `main` tách CFO/VP_SALES/HR_MANAGER/CPO/RISK_MANAGER → gộp lại thành Director có scope |
| Manager | Team | Team Copilot | Giữ |
| Employee | Cá nhân | Personal Assistant | Giữ |
| Reviewer | Hàng chờ được phân | Review Assistant | Giữ |
| Admin | Cấu hình nền tảng | Admin Assistant | Giữ |
| **AI Agent** | Giao quyền agent ∩ người | — | **Mới** — actor độc lập có Identity/Role/Permission/Scope/Tools/Policies/Budget/Audit |

→ Quyết định cần human: giữ 7 role BRD **hay** 7 role + role tùy biến; quan hệ với 10 role F.O.C.U.S của `main` (ánh xạ Director → CFO/VP_SALES/…).

## 4. Cấu trúc tài liệu đích (00–14 theo AI-EOS)

Giữ khung 15 file + chuỗi phụ thuộc (CLAUDE.md §10.1), nhưng nội dung mở theo BRD:

| # | File | Thay đổi lớn so với `main` |
|---|---|---|
| 00 | INDEX | ID registry mở rộng: 28 domain (D01–D28), ~141 US BRD, FR theo domain (FR-ORG/ADM/WF/NTF/INT/DC/STR/KPI/OKR/…), 79+ entity BRD §13.2, metric theo §12.4, SCR UIUX |
| 01 | PROJECT-OVERVIEW | Tầm nhìn "One Enterprise, One Source of Truth, One AI Operating Layer"; 28 domain; BO-01..10; P01–P11; AI-R01–R12; MVP 90 ngày (3 giai đoạn) + 5 phase; North Star |
| 02 | PERSONAS-PERMISSIONS | 7 role + AI Agent; RBAC **+ ABAC** + field-level; RACI §3.3; 4 mức phân loại quyết định model; AI access scope theo phòng ban/role/agent/tool |
| 03 | DASHBOARD-SPEC | Executive/Department/Employee dashboard (§12.3 FR-RPT-03); bộ chỉ số sức khỏe chuẩn §12.4; insight 9 phần §11.8; Daily Briefing §12.2; Management Loop |
| 04 | IDP-FEATURE-SPEC | D03 đầy đủ: C1–C10, pipeline, 13+ doc type §6.3, FR-DC-01..23, review song song, Extraction Schema cấu hình, lineage, học từ chỉnh sửa §6.8 |
| 05 | DATA-MODEL | Toàn bộ entity §13.2 (Organization→AI→Workflow), Data Foundation §13.1 (MDM, Metric Store, lineage, freshness, event backbone, effective-dated, export), quan hệ §13.3 |
| 06 | UI-UX-SPEC | Theo `SOURCE-UIUX.md`: 5 persona, IA theo vai trò, F1–F5, wireframe CEO/Review/Mobile, mẫu tương tác AI theo Autonomy, design system, WCAG 2.1 AA, i18n |
| 07 | TECH-ARCHITECTURE | AI Platform §11.1 (13 thành phần), Model Gateway đa provider + on-prem, Agent Runtime, Orchestrator, Policy/Approval/Audit/Evaluation Engine, event backbone, NFR §16 |
| 08 | DEMO-DATA-SPEC | Dữ liệu mẫu phủ 28 domain (hoặc tập P0 MVP) — cần quyết phạm vi seed |
| 09 | BUILD-PLAN-TASKS | Theo MVP 90 ngày §19.1 (Nền móng / Trí tuệ / Hành động) + 5 phase §19.2 thay vì S0–S5 |
| 10 | API-SPECIFICATION | Tool Registry §11.2 (danh mục tool đầy đủ + 13 metadata §11.2), phân loại READ/WRITE/APPROVAL/EXECUTION, EP theo 28 domain, event backbone §13 FR-DATA-05 |
| 11 | AGENT-WORKFLOW | Loading matrix cho 28 domain; gates; EPCC |
| 12 | DOC-AUDIT | Reset trạng thái cho bộ tài liệu AI-EOS mới |
| 13 | DECISION-LOG | DEC mới cho các quyết định mở §21.1 (SaaS multi-tenant vs nội bộ, ngưỡng L3, AI cloud/on-prem, …) |
| 14 | TEST-TRACEABILITY | Ma trận test theo US/UC/FR BRD |

## 5. Khoảng cách chính `main` (v2.1) → `ai-eos` (AI-EOS đầy đủ)

| Hạng mục | `main` v2.1 | `ai-eos` AI-EOS | Loại |
|---|---|---|---|
| Domain | 6 module + dashboard | 28 domain / 5 lớp | Mở rộng lớn |
| Role | 10 role F.O.C.U.S cố định | 7 role chuẩn + AI Agent actor + role tùy biến | Thay cấu trúc |
| RBAC | RBAC permission `<domain>:<action>` | RBAC + **ABAC** + field-level security | Mở rộng |
| Autonomy | L0–L3 (L4 khóa) | L0–L4 (L4 bật ở phase 5) | Mở rộng |
| Kênh nhập | C1–C5 | C1–C10 (email, chat, XML, Drive, API/webhook) | Mở rộng |
| AI | 1 assistant + Tool Registry | Orchestrator + nhiều agent + Memory + Prompt Mgmt + Evaluation | Mở rộng lớn |
| Integration | Không integration thật | Integration Hub (Google/MS P0; MISA/Fast/CRM/bank/… P1) | Mới |
| Reporting | PDF + Excel tối thiểu | D28 đầy đủ (PDF/Word/Excel/Google Docs, theo lịch) | Mở rộng |
| Knowledge | Lineage, RAG hoãn | D14 Knowledge P0 + RAG | Nâng P0 |
| Calendar | OUT | D13 Calendar 2 chiều P0 | Mới |
| Workflow | Approval rule cơ bản | D04 Workflow Engine (kéo thả / NL, SLA, chữ ký số P1) | Mở rộng |
| Compliance | — | D24 + NĐ 13/2023, DPIA, Luật ANM | Mới |
| Multi-tenant | OUT (single-tenant) | Tenant isolation P0 (BRD FR-ADM-06) | Cần quyết |
| Kiến trúc | Modular Monolith (DEC-125) | BRD không chốt — monolith hay microservice? | Cần quyết |

## 6. Câu hỏi cần human quyết trước khi viết (BRD §21.1 + delta)

| # | Câu hỏi | Mặc định đề xuất |
|---|---|---|
| Q1 | Mục tiêu nhánh: tài liệu **toàn bộ 28 domain** hay chỉ **tập P0 MVP 90 ngày** (Org, Employee, Task/Project, KPI/OKR, Admin&Security, Data Capture, Finance Lite, Sales Lite, CEO Assistant, Briefing, Decision Log)? | **Tập P0 MVP trước**, mở rộng P1/P2 sau — tránh phình, bám BRD §19.1 |
| Q2 | Giữ Modular Monolith (DEC-125) hay mở sang kiến trúc hướng microservice/agent runtime như AI Platform §11.1 gợi ý? | Giữ Modular Monolith cho P0; AI Platform là module logic bên trong |
| Q3 | SaaS đa tenant hay nội bộ 1 tenant (BRD §21.1 OQ)? | Thiết kế data model có `tenant_id` nhưng chạy 1 tenant cho MVP |
| Q4 | 7 role BRD thuần hay giữ ánh xạ sang 10 role F.O.C.U.S của `main`? | 7 role BRD chuẩn; Director có data scope thay cho 5 C-level |
| Q5 | Có tái dùng code trên `main` không, hay chỉ rebuild tài liệu? | Rebuild **tài liệu** trước; code quyết sau khi docs ổn |
| Q6 | Giữ mã ID của `main` (METRIC-*, EP-*, ENT-*) hay đánh lại theo BRD? | Đánh theo BRD (FR-ORG/DC/…, D01–D28) + bảng ánh xạ sang `main` |

## 7. Lộ trình viết lại (Q1–Q6 đã chốt — R-DEC-05..10, 13 §1)

**Phase R0 — Khung & registry** (file 00, 01): bản đồ 28 domain, ID registry, scope MVP/phase, nguyên tắc P/BO/AI-R.
**Phase R1 — Core product** (02, 03, 04): role+RBAC/ABAC, dashboard+chỉ số sức khỏe, Data Capture C1–C10.
**Phase R2 — Technical & data** (05, 06, 07, 10): data model + Data Foundation, UI/UX, AI Platform, Tool Registry + API.
**Phase R3 — Execution & governance** (08, 09, 11, 12, 13, 14): seed, build plan MVP 90 ngày + 5 phase, workflow, audit/decision/traceability.

Mỗi phase: viết → `doc-reviewer` (nếu dùng) → human duyệt → promote; bám chuỗi phụ thuộc CLAUDE.md §10.1.

## 8. Ràng buộc
- **`main` bất khả xâm phạm** trong nhánh này — mọi thay đổi chỉ trên `ai-eos`.
- `_reference/` là Canonical Source; gitignored (không commit nội dung nguồn), nhưng là khung chính của nhánh.
- Agent chỉ đề xuất version/status; human promote (CLAUDE.md §10.3).
- Không thêm dependency / đổi stack / build code trong phase tài liệu.

## Version
- **Version:** 0.2.0 (plan)
- **Last updated:** 2026-10-22
- **Maintainer:** @CyEyes
- **Change 0.2.0:** Q1–Q6 đã được human chốt → R-DEC-05..10 (13 §1); vòng này là **docs-first P0** (R-DEC-09). §6 bảng Q giữ làm lịch sử đề xuất; §7 heading cập nhật "đã chốt". Code/app/migration/merge `main` là đợt sau.
- **Change 0.1.0:** Tạo nhánh `ai-eos` + kế hoạch rebuild tài liệu theo AI-EOS đầy đủ (28 domain, 7 role + AI Agent, Autonomy L0–L4, C1–C10, Data Foundation, AI Platform, D28 Reporting, governance VN). Chờ human quyết Q1–Q6.
