# 14 — Test Traceability (AI-EOS, nhánh `ai-eos`)

> **Vai trò:** Gate C. Ma trận UC/US/FR ↔ test cho bản rebuild AI-EOS.
> **Nguồn chuẩn:** `_reference/SOURCE-BRD-v1.1.md` §14 (UC nghiệm thu), §15 (US), §16 (NFR).
> **Phụ thuộc:** 00–10, `TRACEABILITY-SKELETON.md`. **Trạng thái:** 🟡 draft (Phase R3). **Ngày:** 2026-10-22 · **Maintainer:** @CyEyes

---

## 1. Chiến lược

Mỗi UC/US/FR P0 → ≥1 test case (`TC-*`). Test theo tầng: unit (service/FR), integration (API/event), contract, E2E (UC), AI-eval (fixture). Ngưỡng coverage giữ nguyên CLAUDE.md §6.1 (service ≥80%, bảo mật ≥90%, FE ≥70%).

## 2. Ma trận nghiệm thu UC (BRD §14) — khung TC

| UC | Tên | Tiêu chí nghiệm thu | TC (planned) |
|---|---|---|---|
| UC-01 | CEO Morning Briefing | Đúng giờ, mọi số có nguồn, ≤1 trang | TC-UC01-* |
| UC-02 | Meeting to Execution | ≥90% action item nhận diện; task sau khi duyệt | TC-UC02-* |
| UC-03 | KPI Underperformance | Khuyến nghị có bằng chứng; task gắn KPI | TC-UC03-* |
| UC-04 | OKR At Risk | Cảnh báo trước cuối kỳ ≥3 tuần | TC-UC04-* |
| UC-06 | Biên bản giấy → thực thi | Tải → task ≤10 phút (gồm duyệt) | TC-UC06-* |
| UC-07 | Onboarding 1 ngày | DN 200 NV có dashboard trong 1 ngày | TC-UC07-* |
| UC-05 | CEO Strategic Question (P1) | Trả lời có xác suất/rủi ro/khuyến nghị/nguồn | TC-UC05-* |
| UC-08 | Hóa đơn → dòng tiền (P1) | Không hóa đơn trùng; cảnh báo trong ngày | TC-UC08-* |

## 3. Khung TC theo nhóm FR P0

| Nhóm | FR | TC |
|---|---|---|
| Data Capture | FR-DC-01..23 | TC-DC-* (grounding, confidence routing, trường trọng yếu qua người, anti-injection) |
| KPI/OKR | FR-KPI-01..08, FR-OKR-01..06 | TC-KPI-*, TC-OKR-* (cascade, evaluation rule, alignment, check-in) |
| AI Platform | FR-AIQ-01..06 | TC-AIQ-* (grounding, eval, confidence, budget, injection) |
| Permissions | FR-ADM-02..08 | TC-SEC-* (RBAC+ABAC, field-level, kill switch, Approval Matrix, agent∩user) |
| Data Foundation | FR-DATA-01..08 | TC-DATA-* (MDM, DQ Score, freshness, lineage, event, Metric Store) |
| Reporting/Decision | FR-RPT-01..04, FR-DEC-01..03 | TC-RPT-*, TC-DEC-* (export, 30/60/90 đối chiếu) |

## 4. NFR test (BRD §16)
TC-NFR-* cho PERF (p95/p90 ngưỡng), SEC (RBAC/field-level/injection), AV (fallback model, graceful degradation P10), UX (VI/EN, WCAG 2.1 AA).

## 5. Open questions
- OQ-14-01: TC-* cụ thể chỉ liệt kê sau khi chốt Q1 (scope) + Q5 (có code hay không).
- OQ-14-02: Tái dùng test của `main` (BE 777/FE 18/E2E 30) làm nền nếu tái dùng code? (Q5)

## Version
- **Version:** 0.1.0 (draft, Phase R3)
- **Last updated:** 2026-10-22
- **Maintainer:** @CyEyes
- **Change 0.1.0:** Tạo 14 cho nhánh `ai-eos` — chiến lược test, ma trận UC-01..08 nghiệm thu + khung TC, khung TC theo nhóm FR P0, NFR test; TC-* chi tiết chờ Q1/Q5.
