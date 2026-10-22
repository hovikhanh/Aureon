# 08 — Demo / Seed Data Spec (AI-EOS, nhánh `ai-eos`)

> **Nguồn chuẩn:** `_reference/SOURCE-BRD-v1.1.md` §19.1 (MVP), §20.2 (kịch bản CEO), §14 (UC); kế thừa doanh nghiệp giả định `main` (Công ty ABC).
> **Phụ thuộc:** 00, 01, 04, 05. **Trạng thái:** 🟡 draft (Phase R3). **Ngày:** 2026-10-22 · **Maintainer:** @CyEyes

---

## 1. Phạm vi seed

Theo **R-DEC-05: phủ tập P0 MVP** trước — đủ chạy UC-01/02/03/04/06/07 và kịch bản CEO (BRD §20.2), mở rộng P1 theo phase sau (backlog, không seed đợt này).

> **Khác `main`:** `main` seed Công ty ABC ~150 NV, 9 doc type, 5 trụ F.O.C.U.S. AI-EOS giữ **cùng doanh nghiệp giả định** (dữ liệu giả, không PII thật — nhất quán ràng buộc an toàn) nhưng tổ chức dữ liệu theo **28 domain / 7 role + AI Agent**.

## 2. Doanh nghiệp giả định

**Công ty TNHH TM&DV ABC** — phân phối thiết bị văn phòng + bảo trì + nền tảng "ABC Order"; ~150 nhân sự, 7 phòng ban, ~300 tỷ VNĐ/năm; TP.HCM + chi nhánh Hà Nội. `DEMO_REFERENCE_DATE=2026-10-20`.

## 3. Seed theo domain P0

| Domain | Dữ liệu seed |
|---|---|
| D01 Organization | Company ABC, 7 Department, Team, ~150 Employee, Position, reporting line (ma trận) |
| D02 Admin & Security | 7 role + AI Agent actor, user demo mỗi role, data policy, 4 mức phân loại |
| D03 Data Capture | 1 hóa đơn NEEDS_REVIEW, Extraction Schema cho 6 loại P0, 1 biên bản họp mẫu |
| D07/08/09 Strategy/KPI/OKR | Vision/Pillar/Objective; cây KPI+OKR công ty→phòng ban→cá nhân; measurement vài kỳ |
| D10 Performance | 1 PerformanceCycle, vài CheckIn |
| D11 Task/Project | Dự án, Task, Workload (có người quá tải để kích UC F5) |
| D12 Meeting | 1 Meeting + transcript + Decision + ActionItem (UC-02/06) |
| D13 Calendar | Sự kiện lịch CEO (UC-01 "TODAY") |
| D15 Finance Lite | Revenue/Expense/CashBalance → runway < ngưỡng (kích cảnh báo) |
| D17 Sales Lite | Pipeline, Opportunity, win rate (kích pipeline coverage) |
| D25 Risk | Vài Risk (1 critical cho Briefing) |
| D27/D28 | Dữ liệu đủ cho Briefing + Decision Log |

## 4. Kịch bản demo (BRD §20.2 — CEO 7 bước)

Ask ("Tình hình công ty?") → Understand (tổng hợp Finance/Sales/People/KPI/OKR/Projects/Risks có nguồn) → Investigate → Decide → Act (tạo task L3) → Follow-up → Verify. Dữ liệu seed phải làm mỗi bước ra kết quả thật, có nguồn.

## 5. Chỉ số sức khỏe demo (03 §4)
Seed để trạng thái trụ/nhóm chỉ số có cả ok/warning/critical (runway <6 tháng = 🔴, pipeline coverage thấp = 🟠, quá tải >10% = 🟠…) để Briefing nêu ngoại lệ.

## 6. Ràng buộc an toàn
Dữ liệu demo là **dữ liệu giả** — không PII/dữ liệu thật trong seed/fixture/prompt. Seed idempotent. (Nhất quán §6.6 CLAUDE.md.)

## 7. Open questions
- OQ-08-01: Doc type trong seed — ĐÃ CHỐT: R-DEC-05 — dùng tập doc type P0 theo 04 (04 §P0); 14 doc type BRD đầy đủ là backlog phase sau.
- OQ-08-02: Seed đa tenant vs 1 tenant — ĐÃ CHỐT: R-DEC-07 — seed **1 tenant ABC** cho MVP; data model có `tenant_id` sẵn để nâng đa tenant sau.

## Version
- **Version:** 0.2.0 (draft, Phase R3)
- **Last updated:** 2026-10-22
- **Maintainer:** @CyEyes
- **Change 0.2.0:** Chốt Q1–Q6 (R-DEC-05..10) — cập nhật trạng thái quyết định, đóng OQ liên quan; phạm vi docs-first P0.
- **Change 0.1.0:** Viết lại 08 theo AI-EOS — phạm vi seed P0 MVP, Công ty ABC theo 28 domain/7 role+AI Agent, seed theo domain, kịch bản CEO 7 bước, chỉ số sức khỏe demo, ràng buộc an toàn.
