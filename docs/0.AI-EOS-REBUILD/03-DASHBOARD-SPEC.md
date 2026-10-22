# 03 — Dashboard & Executive Intelligence Spec (AI-EOS, nhánh `ai-eos`)

> **Nguồn chuẩn:** `_reference/SOURCE-BRD-v1.1.md` §12 (D27 CEO Assistant, Daily Briefing, Management Loop, bộ chỉ số sức khỏe, D28 Reporting, Decision Log), §11.8 (insight 9 phần); `SOURCE-BRD-v1.1-Bổ sung.md` §4.3; `SOURCE-UIUX.md` §6.1.
> **Phụ thuộc:** 00, 01, 02, `TRACEABILITY-SKELETON.md` §10. **Trạng thái:** 🟡 draft (Phase R1). **Ngày:** 2026-10-22 · **Maintainer:** @CyEyes

---

## 1. Ba cấp dashboard (FR-RPT-03)

| Dashboard | Người dùng | Nội dung |
|---|---|---|
| **Executive** | CEO, Director | Doanh thu, tiền, pipeline, con người, KPI, OKR, rủi ro, dự án, **tiến độ chiến lược** |
| **Department** | Director, Manager | Hiệu suất, workload, KPI, OKR, dự án, rủi ro của đơn vị |
| **Employee** | Employee | Task, mục tiêu, KPI/OKR cá nhân, workload, lịch |

- **FR-RPT-04:** mọi chỉ số hiển thị **thời điểm cập nhật (data freshness)** + **drill-down** tới bản ghi và **tài liệu gốc** (P06 Traceability).
- Mỗi widget lỗi chỉ báo tại chỗ, không sập cả trang.

> **Khác `main`:** `main` dùng 5 trụ F.O.C.U.S cố định. AI-EOS dùng 3 cấp dashboard theo vai trò + bộ chỉ số sức khỏe chuẩn §4. Ánh xạ 5 trụ ↔ nhóm chỉ số: `TRACEABILITY-SKELETON.md` §12.

## 2. CEO AI Assistant — D27 (BRD §12.1)

Giao diện AI chính, dùng trên **web, mobile, chat, giọng nói**. 12 năng lực:

Hỏi · Phân tích · So sánh · Dự báo · Mô phỏng (what-if) · Rủi ro · Khuyến nghị · Thực thi · Nhập liệu (text/ảnh/file) · Báo cáo · Nhắc việc · Quyết định chờ.

- Mọi con số **có nguồn** (P01/P07, FR-AIQ-01 grounding).
- Tool lọc theo quyền người hỏi (AI dùng quyền agent ∩ người — ROLE-AI).

## 3. CEO Daily Briefing (BRD §12.2, UC-01)

AI tổng hợp lúc **07:00** (cấu hình được), gửi qua kênh CEO chọn. Chỉ nêu **ngoại lệ & thay đổi đáng kể**; mọi dòng bấm được để xem chi tiết + nguồn.

Khối nội dung: `COMPANY STATUS · DATA FRESHNESS · RISKS · PERFORMANCE · TODAY · DECISIONS WAITING · RECOMMENDATIONS`. Mục tiêu ≤ 1 trang (UC-01).

### 3.1. CEO Management Loop (BRD §12.3)

```text
Observe → Company Status → Performance → Risk → Opportunity → Recommendation
→ Decision → Delegation → Execution → Follow-up → Result
```

## 4. Bộ chỉ số sức khỏe doanh nghiệp chuẩn (BRD §12.4)

Cố định, có công thức + ngưỡng cảnh báo, dùng chung cho Dashboard / Briefing / AI / Risk Engine. Tinh chỉnh được; MVP **bắt buộc các chỉ số P0**.

| Nhóm | Chỉ số | Công thức tóm tắt | Ngưỡng cảnh báo | Ưu tiên |
|---|---|---|---|---|
| Tài chính | Tăng trưởng DT, % đạt kế hoạch | (DT kỳ − DT cùng kỳ)/DT cùng kỳ | < kế hoạch > 10% | P0 |
| Tài chính | Cash runway | Tiền mặt / Burn ròng tháng | < 6 tháng | P0 |
| Tài chính | Chênh lệch ngân sách | (Thực chi − NS)/NS | > 10% | P0 |
| Tài chính | Biên LN gộp/EBITDA | LN/DT | giảm > 3đ% vs TB 3 kỳ | P1 |
| Tài chính | DSO/DPO/vòng quay tiền | DSO+DIO−DPO | DSO tăng > 15% | P1 |
| Tài chính | Công nợ quá hạn | Phải thu quá hạn/Tổng | > 15% | P1 |
| Khách hàng | Pipeline coverage | Pipeline trọng số/Chỉ tiêu còn lại | < 3x | P0 |
| Khách hàng | Win rate, chu kỳ bán | Won/Cơ hội đóng | giảm > 20% | P0 |
| Khách hàng | NRR, churn | DT khách cũ kỳ/kỳ trước | NRR < 100% | P1 |
| Khách hàng | Tập trung DT | DT top5/Tổng | > 50% | P1 |
| Khách hàng | CAC, LTV/CAC, NPS | chuẩn | LTV/CAC < 3 | P1 |
| Vận hành | Hoàn thành đúng hạn | Task đúng hạn/đến hạn | < 80% | P0 |
| Vận hành | Dự án trễ | Dự án trễ>10%/Tổng | > 20% | P0 |
| Vận hành | Thực thi quyết định | Action item xong/đến hạn | < 70% | P0 |
| Con người | Quá tải | Người >110% workload 2 tuần/Tổng | > 10% | P0 |
| Con người | Nghỉ việc | Nghỉ/NS bình quân (năm hóa) | > 15%/năm | P1 |
| Con người | DT/nhân sự; CP nhân sự/DT | theo kỳ | lệch > 15% kế hoạch | P1 |
| Chiến lược | **Strategy Execution Index** | % initiative đúng tiến độ (trọng số) | < 70% | P0 |
| Dữ liệu | **Data Quality Score** | Đầy đủ/chính xác/kịp thời/nhất quán | < 80/100 | P0 |

> `METRIC-*` cụ thể + alert 1-1 cấp khi chi tiết hóa (00/14). Ngưỡng là **cấu hình** (không hard-code).

## 5. Insight & khuyến nghị — cấu trúc 9 phần (BRD §11.8)

`Observation → Evidence → Impact → Root Cause → Risk → Recommendation → Expected Outcome → Confidence → Action`.
Grounding bắt buộc (FR-AIQ-01); confidence thang Cao/Trung bình/Thấp kèm lý do khi chưa hiệu chỉnh đủ (FR-AIQ-03).

## 6. D28 — Reporting & Analytics (BRD §12.5)

- **FR-RPT-01:** báo cáo ngày/tuần/tháng/HĐQT/phòng ban/KPI/OKR/dự án/rủi ro/tài chính; theo lịch hoặc yêu cầu.
- **FR-RPT-02:** số liệu từ **Metric Store**, có trích dẫn; xuất **PDF/Word/Excel/Google Docs**; sửa được trước khi gửi.

## 7. Decision Log (BRD §12.6)

- **FR-DEC-01:** ghi quyết định: nội dung, lý do, phương án đã loại, người quyết, ngày, kết quả kỳ vọng đo được, nguồn (họp/khuyến nghị AI/phê duyệt).
- **FR-DEC-02:** sau **30/60/90 ngày** AI đối chiếu thực tế vs kỳ vọng, đánh dấu quyết định cần xem lại.
- **FR-DEC-03:** Decision Log là nguồn chính đo **North Star** (01 §2).

## 8. Use case liên quan
UC-01 Briefing · UC-03 KPI Underperformance · UC-04 OKR At Risk · UC-05 CEO Strategic Question (dashboard + Assistant + Decision Log).

## 9. Open questions
- OQ-03-01: Giữ "view 5 trụ F.O.C.U.S" của `main` — ĐÃ CHỐT: R-DEC-10 giữ bảng ánh xạ sang `main`; "view 5 trụ" là bố cục Executive tùy chọn (optional), không phải view chuẩn — view chuẩn là 3 cấp dashboard BRD.
- OQ-03-02: METRIC-* numbering — ĐÃ CHỐT: R-DEC-10 — đánh số theo nhóm BRD + giữ bảng ánh xạ sang METRIC-<DOMAIN>-xx của `main`; METRIC-* cụ thể gán khi 03 được chi tiết hóa ở đợt code (R-DEC-09).

## Version
- **Version:** 0.2.0 (draft, Phase R1)
- **Last updated:** 2026-10-22
- **Maintainer:** @CyEyes
- **Change 0.2.0:** Chốt Q1–Q6 (R-DEC-05..10) — cập nhật trạng thái quyết định, đóng OQ liên quan; phạm vi docs-first P0.
- **Change 0.1.0:** Viết lại 03 theo AI-EOS — 3 cấp dashboard (Executive/Department/Employee), CEO Assistant 12 năng lực đa kênh, Daily Briefing + Management Loop, bộ chỉ số sức khỏe chuẩn đầy đủ (P0/P1), insight 9 phần, D28 Reporting (PDF/Word/Excel/Google Docs), Decision Log 30/60/90 ngày.
