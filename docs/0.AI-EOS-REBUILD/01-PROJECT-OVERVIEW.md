# 01 — Project Overview (AI-EOS, nhánh `ai-eos`)

> **Nguồn chuẩn (Canonical):** `_reference/SOURCE-BRD-v1.1.md` (AI-EOS BRD v1.1) + `SOURCE-BRD-v1.1-Bổ sung.md` + `SOURCE-UIUX.md`. File này viết lại **đầy đủ theo AI-EOS**, không phải bản distill demo v2.0/v2.1 ở `main`.
> **Trạng thái:** 🟡 draft (Phase R0) — Q1–Q6 **đã chốt** (R-DEC-05..10, 13 §1); phạm vi **docs-first P0** (R-DEC-09).
> **Phụ thuộc:** `TRACEABILITY-SKELETON.md` (ID registry). **Ngày:** 2026-10-22 · **Maintainer:** @CyEyes

---

## 1. Sản phẩm

**AI-EOS — AI-First Enterprise Operating System.** Không phải ERP/CRM/HRM/PM/BI/chatbot, mà là **hệ điều hành doanh nghiệp lấy AI làm trung tâm**, nối liền một vòng lặp:

```text
Capture → Data → Intelligence → Decision → Action → Measurement → Feedback
```

### 1.1. Tầm nhìn

> **One Enterprise. One Source of Truth. One AI Operating Layer.**

AI đóng vai Assistant, Analyst, Advisor, Planner, Orchestrator hoặc Agent tùy mức tự chủ (Autonomy L0–L4) doanh nghiệp cho phép.

### 1.2. Bốn câu hỏi hệ thống phải trả lời liên tục (BRD §1.2)

1. **Chúng ta muốn đạt gì?** — Strategy, KPI, OKR.
2. **Chúng ta đang làm gì để đạt nó?** — Initiative, Project, Task.
3. **Kết quả đang thế nào và tại sao?** — Measurement, Analytics, AI.
4. **Tiếp theo cần làm gì?** — Recommendation, Decision, Action, Follow-up.

### 1.3. Giá trị cốt lõi — 3 hệ thống hợp nhất (BRD §1.4)

- **System of Record** — sự thật về con người, tài chính, khách hàng, dự án, công việc, KPI/OKR, hợp đồng, cuộc họp, tài liệu gốc.
- **System of Intelligence** — phân tích, dự báo, phát hiện rủi ro, khuyến nghị.
- **System of Action** — task, workflow, phê duyệt, lịch, thông báo, API, agent.

Khác ERP: ERP dừng ở "dữ liệu → dashboard → người tự quyết"; AI-EOS đi tiếp "insight → khuyến nghị → quyết định → hành động → **xác minh kết quả**", và bắt đầu từ **tài liệu doanh nghiệp đang có** thay vì bắt nhập lại.

### 1.4. Lời hứa MVP

> **"CEO biết công ty đang đạt mục tiêu đến đâu, vì sao, và giao việc được ngay — với dữ liệu nhập vào dễ như gửi một file."**

---

## 2. Mục tiêu kinh doanh — BO-01…BO-10 (BRD §2.1)

| Mã | Mục tiêu | Chỉ số | Mục tiêu 6 tháng |
|---|---|---|---|
| BO-01 | Quản trị tập trung trên một nền tảng | % quy trình cốt lõi chạy trên AI-EOS | ≥ 80% |
| BO-02 | Minh bạch gần thời gian thực | Độ trễ dữ liệu chỉ số điều hành | ≤ 24h tài chính; ≤ 1h task/sales |
| BO-03 | Liên kết chiến lược ↔ thực thi | % task/dự án gắn KPI/OKR/initiative | ≥ 70% |
| BO-04 | Ra quyết định có AI | % quyết định quan trọng có phân tích AI + bằng chứng | ≥ 50% |
| BO-05 | Thực thi có AI | Số hành động AI xác minh thành công/tháng | Tăng hàng tháng |
| BO-06 | Giảm chi phí quản lý | Giờ/tuần CEO & quản lý cho tổng hợp/báo cáo/follow-up | Giảm ≥ 50% (CEO ≥ 5h/tuần) |
| BO-07 | Bộ nhớ doanh nghiệp | % quyết định/họp/tài liệu quan trọng truy vấn được | ≥ 90% |
| BO-08 | Thu thập dữ liệu không ma sát | Thời gian nhập liệu vs nhập tay | Giảm ≥ 70% |
| BO-09 | Dữ liệu đáng tin cho AI | Data Quality Score domain cốt lõi | ≥ 90/100 |
| BO-10 | Phát hiện rủi ro sớm | Thời gian từ dấu hiệu → hành động | Giảm ≥ 50% |

**North Star (BRD §20.1):** *Tỷ lệ quyết định & hành động quan trọng được AI hỗ trợ và có kết quả được xác minh.* Phễu: Insights → Recommendations → Accepted → Executed → Verified → Successful Outcomes (nguồn: Decision Log + AIRecommendation).

---

## 3. Nguyên tắc sản phẩm — P01…P11 (BRD §2.2)

P01 AI First · P02 API First · P03 Data First · P04 Human in the Loop · P05 Everything Actionable · P06 Traceability · P07 Explainable AI · P08 Security by Design · P09 Capture Once Use Everywhere · P10 Graceful Degradation · P11 Measure Outcomes.

12 yêu cầu AI-first **AI-R01…AI-R12** áp cho mọi module (BRD §2.3) — chi tiết ở `TRACEABILITY-SKELETON.md` §2.

---

## 4. Bản đồ 28 domain / 5 lớp (BRD §4)

Lớp **Nền tảng** và lớp **Trí tuệ** phục vụ mọi domain; **D03 Data Capture là cửa vào dữ liệu duy nhất**.

| Lớp | Domain |
|---|---|
| Nền tảng | D01 Organization · D02 Admin & Security · D03 Data Capture & IDP · D04 Workflow & Approval · D05 Notification · D06 Integration Hub |
| Điều hành | D07 Strategy · D08 KPI · D09 OKR · D10 Performance |
| Thực thi | D11 Project/Task/Workload · D12 Meeting Intelligence · D13 Calendar · D14 Knowledge |
| Vận hành KD | D15 Finance · D16 HR · D17 Sales · D18 Customer · D19 Partner · D20 Procurement · D21 Contract · D22 Product · D23 Engineering |
| Governance & Trí tuệ | D24 Governance & Compliance · D25 Risk · D26 AI Platform · D27 CEO AI Assistant · D28 Reporting & Analytics |

Ưu tiên chi tiết: `TRACEABILITY-SKELETON.md` §4 / BRD §19.3.

---

## 5. Vai trò (BRD §3.2)

7 vai trò chuẩn + **AI Agent là actor độc lập** (có Identity/Role/Permission/Scope/Tools/Policies/Budget/Audit); doanh nghiệp tạo thêm vai trò tùy biến:

ROLE-CEO · ROLE-DIR (Executive/Director) · ROLE-MGR · ROLE-EMP · ROLE-REV (Reviewer) · ROLE-ADM · **ROLE-AI**. RACI 7 quy trình cốt lõi ở BRD §3.3 (AI Agent không bao giờ là A). Chi tiết quyền/scope: 02.

---

## 6. Phạm vi MVP & lộ trình (BRD §19)

### 6.1. MVP 90 ngày (BRD §19.1)

| Giai đoạn | Nội dung |
|---|---|
| **Ngày 1–30 — Nền móng** | Organization, Employee, Project/Task, KPI/OKR cơ bản; Admin & Security; nhập tay + import Excel + Word/PDF (UC-07); Tool Registry, audit, Autonomy L0–L2, kill switch |
| **Ngày 31–60 — Trí tuệ** | CEO Assistant hỏi đáp có trích nguồn; Finance Lite, Sales Pipeline Lite; biên bản/transcript → task (UC-02, UC-06); chụp ảnh mobile, nhập bằng lời; chỉ số sức khỏe P0 + cảnh báo ngưỡng; Metric Store |
| **Ngày 61–90 — Hành động** | CEO Daily Briefing; khuyến nghị → phê duyệt → task (L3); Google/Outlook Calendar 2 chiều; Decision Log; Evaluation Engine; thí điểm 1 DN 50–200 NV |

**Cổng qua MVP:** CEO dùng Briefing ≥ 4 ngày/tuần × 4 tuần; ≥ 80% KPI/OKR cập nhật đúng kỳ; ≥ 60% dữ liệu mới vào qua tài liệu/ngôn ngữ tự nhiên; không có AI ghi sai trường trọng yếu mà không bị phát hiện.

### 6.2. 5 phase sau (BRD §19.2)

1. AI Executive & Work Core (MVP) · 2. Business Operations · 3. Product & Technical · 4. Governance & Strategy · 5. Autonomous Enterprise (mở L4 cho tool đã chứng minh độ tin cậy).

### 6.3. Kịch bản nghiệm thu CEO (BRD §20.2) — 7 bước

Ask → Understand → Investigate → Decide → Act → Follow-up → Verify.

---

## 7. Use case nghiệm thu (BRD §14)

UC-01 CEO Morning Briefing · UC-02 Meeting to Execution · UC-03 KPI Underperformance · UC-04 OKR At Risk · UC-05 CEO Strategic Question · UC-06 Biên bản giấy → thực thi · UC-07 Onboarding 1 ngày · UC-08 Hóa đơn → cảnh báo dòng tiền. MVP: UC-01/02/03/04/06/07.

---

## 8. Quyết định nền (Q1–Q6 đã chốt) + quyết định mở CEO (BRD §21.1)

> ✅ Q1–Q6 **đã chốt** (R-DEC-05..10, 13 §1). Các mục dưới ghi quyết định chính thức; BRD-OQ (B1–B7) còn chờ CEO nhưng không blocking docs P0.

| # | Quyết định | Đã chốt |
|---|---|---|
| Q1 | Toàn bộ 28 domain vs tập P0 MVP | **R-DEC-05:** P0 MVP trước; khung 28 domain giữ đủ ở 00; P1/P2 là backlog (09) |
| Q2 | Kiến trúc | **R-DEC-06:** Modular Monolith; AI Platform là cụm module logic bên trong |
| Q3 | Tenant | **R-DEC-07:** 1 tenant cho MVP; data model có `tenant_id` sẵn ở mọi entity |
| Q4 | Role | **R-DEC-08:** 7 role BRD + AI Agent; Director có data scope thay 5 C-level; giữ bảng ánh xạ 10 role F.O.C.U.S của `main` |
| Q5 | Phạm vi nhánh | **R-DEC-09:** Docs-first — hoàn thiện 00–14 đợt này; code/app/migration/merge main là đợt sau |
| Q6 | ID scheme | **R-DEC-10:** Theo BRD + bảng ánh xạ sang METRIC-/EP-/ENT-/SCR-/TOOL- của `main` |
| BRD-OQ | SaaS đa tenant / AI cloud / ngưỡng L3 / phần mềm kế toán / kênh chat / giá | Chờ CEO (B1–B7, BRD §21.1) — không blocking docs P0 |

---

## Version
- **Version:** 0.2.0 (draft, Phase R0)
- **Last updated:** 2026-10-22
- **Maintainer:** @CyEyes
- **Change 0.2.0:** Chốt Q1–Q6 (R-DEC-05..10) — cập nhật trạng thái quyết định, đóng OQ liên quan; phạm vi docs-first P0.
- **Change 0.1.0:** Viết lại 01 theo AI-EOS đầy đủ — tầm nhìn/4 câu hỏi/3 hệ thống, BO-01..10 + North Star, P01..P11 + AI-R, bản đồ 28 domain/5 lớp, 7 role + AI Agent, MVP 90 ngày + 5 phase, kịch bản CEO 7 bước, UC-01..08, quyết định mở + mặc định tạm Q1–Q6.
