# 09 — Build Plan & Tasks (AI-EOS, nhánh `ai-eos`)

> **Nguồn chuẩn:** `_reference/SOURCE-BRD-v1.1.md` §19 (MVP 90 ngày + 5 phase + ma trận ưu tiên).
> **Phụ thuộc:** toàn bộ 00–08, 10, 11. **Trạng thái:** 🟡 draft (Phase R3) — sinh cuối theo CLAUDE.md §10.1 Phase 4. **Ngày:** 2026-10-22 · **Maintainer:** @CyEyes

---

## 1. Lộ trình theo BRD (khác S0–S5 của `main`)

> **Khác `main`:** `main` dùng sprint S0–S5d (đã xong, demo-ready). AI-EOS bám **MVP 90 ngày (3 giai đoạn) + 5 phase** của BRD §19 — là lộ trình **sản phẩm**, không phải lộ trình đã-hoàn-thành.

## 2. MVP 90 ngày (BRD §19.1)

| Giai đoạn | Nội dung chính | UC |
|---|---|---|
| **M1 Ngày 1–30 — Nền móng** | D01 Organization, Employee, D11 Project/Task, D08/D09 KPI/OKR cơ bản; D02 Admin & Security; C1 nhập tay + C5 Excel + C3 Word/PDF; Tool Registry, audit, Autonomy L0–L2, kill switch | UC-07 |
| **M2 Ngày 31–60 — Trí tuệ** | CEO Assistant hỏi đáp có trích nguồn; D15 Finance Lite, D17 Sales Lite; biên bản/transcript → task; C4 chụp ảnh, C2 nhập bằng lời; chỉ số sức khỏe P0 + cảnh báo ngưỡng; Metric Store | UC-02, UC-06, UC-03 |
| **M3 Ngày 61–90 — Hành động** | CEO Daily Briefing; khuyến nghị → phê duyệt → task (L3); Calendar 2 chiều; Decision Log; Evaluation Engine; thí điểm 1 DN 50–200 NV | UC-01, UC-04 |

**Cổng qua MVP (BRD §19.1):** CEO dùng Briefing ≥4 ngày/tuần ×4 tuần · ≥80% KPI/OKR cập nhật đúng kỳ · ≥60% dữ liệu mới vào qua tài liệu/ngôn ngữ tự nhiên · không AI ghi sai trường trọng yếu mà không bị phát hiện.

## 3. 5 phase sau MVP (BRD §19.2)

| Phase | Tên | Nội dung |
|---|---|---|
| 1 | AI Executive & Work Core (MVP) | §2 |
| 2 | Business Operations | Finance đầy đủ, CRM, Customer, Partner, HR nâng cao, Procurement, Contract Lifecycle, hóa đơn/hợp đồng/email capture, XML hóa đơn, Workflow Engine, KPI tự động, AI dự Google Meet, Performance Cycle đầy đủ |
| 3 | Product & Technical | Product, Engineering, Git, CI/CD, Infrastructure, technical debt, product analytics |
| 4 | Governance & Strategy | Governance & Compliance, Risk Intelligence nâng cao, Strategy nâng cao, scenario planning |
| 5 | Autonomous Enterprise | Assistant → Copilot → Agent → Multi-Agent → Enterprise Orchestrator; mở **L4** cho tool đã chứng minh độ tin cậy |

## 4. Ma trận ưu tiên (BRD §19.3) — trích P0

P0: Organization/Employee/Admin&Security · Data Capture & IDP (mới) · Data Foundation (mới) · Task/Project/Workload · KPI/OKR/check-in · Calendar · Meeting từ biên bản/transcript · Knowledge · AI Assistant/Tool Registry/Autonomy L0–L3/Evaluation · CEO Dashboard/Daily Briefing/chỉ số sức khỏe/Decision Log · Finance Lite, Sales Pipeline Lite.
P1: Performance Cycle đầy đủ · AI dự Google Meet · Finance đầy đủ/CRM/Customer/HR nâng cao · Procurement/Contract/Workflow nâng cao · Product/Engineering · Risk Intelligence.
P2: Governance & Compliance · Autonomous Agent (L4).

## 5. Thứ tự sinh tài liệu (CLAUDE.md §10.1)
Phase 1 (02,03,04) → Phase 2 (05,06,07,08,10,11) → Phase 3 (12,13,14) → Phase 4 (09). Q1–Q6 đã chốt (13 §1); file này là **product roadmap** của đợt docs-first. Task chi tiết T-* được sinh ở **đợt code** (R-DEC-09), sau khi docs 00–14 được human promote `current`.

## 6. Open questions
- OQ-09-01: Task breakdown T-* chi tiết — được sinh ở **đợt code** (R-DEC-09); doc 09 giữ vai trò product roadmap P0/P1/P2 (R-DEC-05).
- OQ-09-02: Tái dùng code `main` (S0–S5d) làm nền M1–M3 — quyết định cụ thể ở đợt code (R-DEC-09), gồm cả merge main.

## Version
- **Version:** 0.2.0 (draft, Phase R3)
- **Last updated:** 2026-10-22
- **Maintainer:** @CyEyes
- **Change 0.2.0:** Chốt Q1–Q6 (R-DEC-05..10) — cập nhật trạng thái quyết định, đóng OQ liên quan; phạm vi docs-first P0.
- **Change 0.1.0:** Viết lại 09 theo AI-EOS — MVP 90 ngày (M1–M3) + cổng MVP, 5 phase sau, ma trận ưu tiên P0/P1/P2, thứ tự sinh tài liệu; T-* chờ Q1/Q5.
