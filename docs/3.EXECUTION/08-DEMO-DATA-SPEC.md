# 08 — DEMO DATA SPEC

> Hồ sơ Công ty TNHH TM&DV ABC, 5 tài khoản demo ROLE-01..05, 7 tài liệu mẫu với ground truth, seed data cho 18 metric và các alert dùng trong kịch bản demo 15 phút (§11, `01-PROJECT-OVERVIEW.md`).
> Nguồn: `01-PROJECT-OVERVIEW.md` §8; quyền/role theo `02-PERSONAS-PERMISSIONS.md`; metric/alert theo `03-DASHBOARD-SPEC.md`; extraction schema/theo chuẩn IDP theo `04-IDP-FEATURE-SPEC.md`; entity theo `05-DATA-MODEL.md`.
> **Gate A / B / C:** `12-DOC-AUDIT.md` — N/A (Phase 3); `13-DECISION-LOG.md` — chờ OQ-12 human chốt DEC blocking; `14-TEST-TRACEABILITY.md` — mapping task seed ↔ test case sẽ thêm ở Phase 3.

---

## 1. Hồ sơ công ty ABC

| Thuộc tính | Giá trị |
|---|---|
| Tên đầy đủ | Công ty TNHH Thương mại & Dịch vụ ABC |
| Mã số thuế (MST) | `0301234567` (10 số, định dạng VN) |
| Ngành | Phân phối thiết bị văn phòng (giấy, bút, máy in, phụ kiện) |
| Quy mô | **45 nhân sự** đang làm việc (ACTIVE) |
| Doanh thu dự kiến | ~100 tỷ VNĐ/năm → trung bình **~8,3 tỷ/tháng** |
| Trụ sở chính | `Tầng 7, Tòa nhà Bitexco Financial Tower, 2 Hải Triều, Phường Bến Nghé, Quận 1, TP. Hồ Chí Minh` |
| Chi nhánh | `Số 45 đường Lê Duẩn, Phường Bến Thành, Quận 1, TP. Hồ Chí Minh` |
| Người đại diện | Ông **Nguyễn Văn An** — Giám đốc |
| Niên độ tài chính | Năm dương lịch (01/01 – 31/12) |
| Kỳ dữ liệu demo | Tháng 9/2026 (`T9/2026`), Quý 3/2026 (`Q3/2026`) |
| Đơn vị tiền tệ | VNĐ (VND); tiền lưu `bigint` — số nguyên, không thập phân |

**Quy tắc P04 áp dụng cho mọi dữ liệu:**
- Ngày: `dd/mm/yyyy` khi hiển thị; ISO `yyyy-mm-dd` khi lưu.
- Tiền: `1.250.000 đ` / `1,2 tỷ` / `850 tr` — dấu chấm phân cách nghìn, dấu phẩy thập phân.
- MST: 10 số, định dạng `0301234567`.
- Nhân sự: tên giả định, không PII thật; CCCD/số điện thoại dùng giá trị placeholder `0123456789` / `09xxxxxxxx`.

---

## 2. Tài khoản demo — 5 user, 1 role mỗi người

Theo `02-PERSONAS-PERMISSIONS.md` §5.2 R5 và `07-TECH-ARCHITECTURE.md` §8.1.1 (đã chốt): mỗi user tương ứng 1 role cố định; switcher chỉ hoạt động khi `DEMO_MODE=true`; mật khẩu đặt qua `.env.example` — **không ghi cứng**.

| ID tài khoản | Email (demo) | Full name | Role | Ghi chú |
|---|---|---|---|---|
| `acc-ceo` | `ceo@abc.demo` | **Ông Nguyễn Văn An** | **ROLE-01 CEO** | Giám đốc điều hành; xem 4 trụ, xem tất cả alert; **không** có quyền duyệt IDP (§3.4) |
| `acc-cfo` | `cfo@abc.demo` | **Bà Trần Thị Minh** | **ROLE-02 CFO** | Giám đốc tài chính; xem FIN + OPS; duyệt tài liệu FIN; drill-down dừng ở bản ghi tổng hợp với lương cá nhân |
| `acc-sales` | `sales@abc.demo` | **Ông Lê Hoàng Giang** | **ROLE-03 Sales Dir** | Giám đốc kinh doanh; xem CUS + doanh thu FIN; không duyệt IDP |
| `acc-hr` | `hr@abc.demo` | **Cô Phạm Thị Hạnh** | **ROLE-04 HR Manager** | Trưởng phòng nhân sự; xem HR + OPS; duy nhất có quyền mở/tải file #6 lương cá nhân |
| `acc-reviewer` | `reviewer@abc.demo` | **Anh Vũ Đức Thắng** | **ROLE-05 Reviewer** | Nhân viên vận hành dữ liệu; dashboard duy nhất = hàng chờ IDP; duyệt được mọi trụ |

**Quy tắc mật khẩu (chỉ ghi trong `.env.example`, không commit vào repo):**

```env
DEMO_CEO_PASSWORD=<change-me>
DEMO_CFO_PASSWORD=<change-me>
DEMO_SALES_PASSWORD=<change-me>
DEMO_HR_PASSWORD=<change-me>
DEMO_REVIEWER_PASSWORD=<change-me>
```

> ⚠️ Mật khẩu chỉ đặt qua biến `DEMO_*_PASSWORD` trong `.env` (mẫu `.env.example` chỉ chứa `<change-me>`); không ghi giá trị thật trong tài liệu hay repo. Khi chạy seed, hệ thống băm bcrypt và chỉ lưu hash. Không in mật khẩu ra log/console.

**Demo mode flag:** `DEMO_MODE=true` — khi tắt, dropdown switcher ẩn và endpoint role switch trả `404` (theo `07-TECH-ARCHITECTURE.md` §8.1.1; path do `10-API-SPECIFICATION.md` định nghĩa).

---

## 3. Bảy tài liệu mẫu — ground truth chi tiết

### DOC-01 — Báo cáo tài chính Q3/2026

| Thuộc tính | Giá trị |
|---|---|
| Doc type code | `FINANCIAL_REPORT` |
| Định dạng | PDF scan (12 trang), **trang 7 mờ** (ocr_confidence < 0,70) |
| Trụ đích | **Tài chính** |
| Period | `Q3/2026` |
| Ground truth fields | |

| Field | Giá trị ground truth | Nguồn gốc |
|---|---|---|
| `company_name` | `Công ty TNHH TM&DV ABC` | Tiêu đề BCTC |
| `tax_code` | `0301234567` | Thống nhất MST công ty |
| `period` | `2026-Q3` | Header BCTC |
| `revenue` (cả quý) | `24.500.000.000 đ` | Tổng doanh thu Q3 (trang 3 P&L) |
| `revenue_by_month[]` | Bảng doanh thu tháng trước VAT (trang 4) | Xem bảng bên dưới |
| `cogs` | `20.000.000.000 đ` | Giá vốn hàng bán Q3 (< doanh thu) |
| `gross_profit` | `4.500.000.000 đ` | = `24.500.000.000 − 20.000.000.000` → biên gộp **18,4%** |
| `operating_expenses` | `3.400.000.000 đ` | Chi phí bán hàng + quản lý Q3; **gồm quỹ lương quý 2.565.000.000** (= 855.000.000 × 3, khớp DOC-06) + chi phí khác 835.000.000 |
| `profit_before_tax` | `1.100.000.000 đ` | = `4.500.000.000 − 3.400.000.000` |
| `income_tax` | `220.000.000 đ` | Thuế TNDN 20% × 1.100.000.000 |
| `net_profit` | `880.000.000 đ` | = `1.100.000.000 − 220.000.000` |
| `budget_opex` | `3.150.000.000 đ` | Ngân sách chi phí vận hành Q3 (trang 9) → METRIC-FIN-06 |
| `cash_end_of_period` | `6.800.000.000 đ` | Tiền cuối Q3 (30/09/2026) |
| `net_cash_flow_by_month[]` | T7 `−700.000.000`, T8 `−850.000.000`, T9 `−1.000.000.000` | Dòng tiền ròng âm do tăng tồn kho + phải thu; bình quân 3 tháng `−850.000.000` → METRIC-FIN-03 |
| `receivables` | `13.000.000.000 đ` | Phải thu khách hàng tại 30/09/2026 (gồm VAT) = 47 HĐ T9 chưa thu `9.312.000.000` + HL-001 `242.000.000` + HĐ T8 chưa thu `3.446.000.000` |

**Bảng `revenue_by_month` (bắt buộc theo XD-01 §12.1):**

| Tháng | Doanh thu (trước VAT, VND) |
|---|---|
| T7/2026 (`2026-07`) | `7.800.000.000` |
| T8/2026 (`2026-08`) | `8.200.000.000` |
| T9/2026 (`2026-09`) | `8.500.000.000` |
| **Tổng Q3** | `24.500.000.000` (= SUM 3 tháng ✓) |

> 📌 **Doanh thu T9 = 8.500.000.000 VND** phải khớp `SUM(INVOICE.subtotal)` của 47 hóa đơn trong DOC-02 (xem §4.1). Nếu BCTC không có bảng `revenue_by_month` → `NOT_COMPARABLE` (04 §12.1).

**Doc field mapping:**
- `revenue_by_month[2026-09]` → METRIC-FIN-01 (doanh thu tháng)
- `gross_profit / revenue × 100` → METRIC-FIN-02
- `cash_end_of_period` / bình quân `net_cash_flow_by_month` → METRIC-FIN-03 (cash runway)
- `receivables` / `revenue` × 90 → METRIC-FIN-04 (DSO)
- `operating_expenses` vs `budget_opex` → METRIC-FIN-06

---

### DOC-02 — Danh sách hóa đơn T9/2026

| Thuộc tính | Giá trị |
|---|---|
| Doc type code | `INVOICE` |
| Định dạng | Excel (`.xlsx`), **47 dòng** (header + 47 bản ghi hóa đơn) |
| Trụ đích | **Tài chính** |
| Kỳ | Tháng 9/2026 (`T9/2026`) |
| Tổng subtotal (trước VAT) | **8.500.000.000 đ** (= `revenue_by_month[2026-09]` của DOC-01 ✓ MATCH) |
| Tổng VAT | `812.000.000 đ` (cộng theo từng dòng: 33 dòng 10% + 14 dòng 8%; thuế suất bình quân 9,55%) |
| Tổng thanh toán (subtotal + VAT) | `9.312.000.000 đ` |
| Hạn thanh toán | `issue_date + điều khoản`: 30 ngày (Giáo dục Việt Nam, HĐ-2026-001), 60 ngày (Minh Phát, HĐ-2026-002), 45 ngày (khách còn lại). Luôn `due_date ≥ issue_date` |
| Cột "Đã thu" | Số tiền đã thu **tính đến `DEMO_REFERENCE_DATE` = 20/10/2026**; mọi khoản thu đều phát sinh từ 01/10/2026 (tức tại 30/09/2026 cả 47 hóa đơn đều chưa thu — dùng cho DSO §5.1) |

**Schema Excel (10 cột, chuẩn `business_records` §05 §4.8.1):**

| STT | Số HĐ | Ngày | Khách hàng | MST khách | Subtotal (VND) | VAT % | Đã thu (VND) | Hạn TT | Trạng thái |
|---|---|---|---|---|---|---|---|---|---|
| 1 | HV-001 | 02/09/2026 | Công ty Cổ phần Giáo dục Việt Nam | 0309876543 | 260.000.000 | 10% | 0 | 02/10/2026 | UNPAID |
| 2 | HV-002 | 03/09/2026 | Công ty TNHH TechSoft | 0305551234 | 250.000.000 | 10% | 275.000.000 | 18/10/2026 | PAID |
| 3 | HV-003 | 04/09/2026 | Công ty TNHH Giải pháp Số | 0304445678 | 150.000.000 | 8% | 0 | 19/10/2026 | UNPAID |
| 4 | HV-004 | 05/09/2026 | Công ty Cổ phần Văn phòng Phẩm | 0301112223 | 95.000.000 | 10% | 104.500.000 | 20/10/2026 | PAID |
| 5 | HV-005 | 06/09/2026 | Công ty TNHH Minh Phát | 0306667778 | 320.000.000 | 10% | 0 | 05/11/2026 | UNPAID |
| 6 | HV-006 | 07/09/2026 | Công ty Cổ phần ABC Retail | 0302223334 | 165.000.000 | 8% | 178.200.000 | 22/10/2026 | PAID |
| 7 | HV-007 | 08/09/2026 | Công ty TNHH Đại Lợi | 0307778889 | 240.000.000 | 10% | 0 | 23/10/2026 | UNPAID |
| 8 | HV-008 | 09/09/2026 | Công ty Cổ phần Giáo dục Việt Nam | 0309876543 | 140.000.000 | 10% | 0 | 09/10/2026 | UNPAID |
| 9 | HV-009 | 10/09/2026 | Công ty TNHH An Khang | 0308889990 | 85.000.000 | 8% | 91.800.000 | 25/10/2026 | PAID |
| 10 | HV-010 | 11/09/2026 | Công ty Cổ phần Văn phòng Phẩm | 0301112223 | 195.000.000 | 10% | 0 | 26/10/2026 | UNPAID |
| 11 | HV-011 | 12/09/2026 | Công ty TNHH FPT Trading | 0303334445 | 290.000.000 | 10% | 319.000.000 | 27/10/2026 | PAID |
| 12 | HV-012 | 13/09/2026 | Công ty TNHH Giải pháp Số | 0304445678 | 140.000.000 | 8% | 0 | 28/10/2026 | UNPAID |
| 13 | HV-013 | 14/09/2026 | Công ty Cổ phần Thương mại Quốc tế | 0305556677 | 200.000.000 | 10% | 220.000.000 | 29/10/2026 | PAID |
| 14 | HV-014 | 15/09/2026 | Công ty TNHH Minh Phát | 0306667778 | 175.000.000 | 10% | 0 | 14/11/2026 | UNPAID |
| 15 | HV-015 | 16/09/2026 | Công ty Cổ phần TechVN | 0301119988 | 185.000.000 | 10% | 203.500.000 | 31/10/2026 | PAID |
| 16 | HV-016 | 17/09/2026 | Công ty TNHH Đầu tư Đại Cường | 0302228877 | 270.000.000 | 10% | 0 | 01/11/2026 | UNPAID |
| 17 | HV-017 | 18/09/2026 | Công ty Cổ phần Giáo dục Việt Nam | 0309876543 | 130.000.000 | 8% | 140.400.000 | 18/10/2026 | PAID |
| 18 | HV-018 | 19/09/2026 | Công ty TNHH Thương mại Lộc Phát | 0303332211 | 190.000.000 | 10% | 0 | 03/11/2026 | UNPAID |
| 19 | HV-019 | 20/09/2026 | Công ty Cổ phần Bút Tre VN | 0304443322 | 100.000.000 | 8% | 108.000.000 | 04/11/2026 | PAID |
| 20 | HV-020 | 21/09/2026 | Công ty TNHH An Khang | 0308889990 | 145.000.000 | 10% | 0 | 05/11/2026 | UNPAID |
| 21 | HV-021 | 22/09/2026 | Công ty Cổ phần Văn phòng Phẩm | 0301112223 | 240.000.000 | 10% | 264.000.000 | 06/11/2026 | PAID |
| 22 | HV-022 | 23/09/2026 | Công ty TNHH FPT Trading | 0303334445 | 190.000.000 | 10% | 0 | 07/11/2026 | UNPAID |
| 23 | HV-023 | 24/09/2026 | Công ty Cổ phần ABC Retail | 0302223334 | 160.000.000 | 8% | 172.800.000 | 08/11/2026 | PAID |
| 24 | HV-024 | 25/09/2026 | Công ty TNHH Giải pháp Số | 0304445678 | 230.000.000 | 10% | 0 | 09/11/2026 | UNPAID |
| 25 | HV-025 | 26/09/2026 | Công ty Cổ phần Giáo dục Việt Nam | 0309876543 | 175.000.000 | 10% | 192.500.000 | 26/10/2026 | PAID |
| 26 | HV-026 | 27/09/2026 | Công ty TNHH Minh Phát | 0306667778 | 120.000.000 | 8% | 0 | 26/11/2026 | UNPAID |
| 27 | HV-027 | 28/09/2026 | Công ty Cổ phần Văn phòng Phẩm | 0301112223 | 195.000.000 | 10% | 214.500.000 | 12/11/2026 | PAID |
| 28 | HV-028 | 29/09/2026 | Công ty TNHH Đầu tư Đại Cường | 0302228877 | 185.000.000 | 10% | 0 | 13/11/2026 | UNPAID |
| 29 | HV-029 | 30/09/2026 | Công ty Cổ phần TechVN | 0301119988 | 140.000.000 | 8% | 151.200.000 | 14/11/2026 | PAID |
| 30 | HV-030 | 01/09/2026 | Công ty TNHH An Khang | 0308889990 | 220.000.000 | 10% | 0 | 16/10/2026 | UNPAID |
| 31 | HV-031 | 02/09/2026 | Công ty Cổ phần Bút Tre VN | 0304443322 | 130.000.000 | 10% | 143.000.000 | 17/10/2026 | PAID |
| 32 | HV-032 | 03/09/2026 | Công ty TNHH Thương mại Lộc Phát | 0303332211 | 200.000.000 | 10% | 0 | 18/10/2026 | UNPAID |
| 33 | HV-033 | 04/09/2026 | Công ty Cổ phần Giáo dục Việt Nam | 0309876543 | 155.000.000 | 8% | 167.400.000 | 04/10/2026 | PAID |
| 34 | HV-034 | 05/09/2026 | Công ty TNHH FPT Trading | 0303334445 | 230.000.000 | 10% | 0 | 20/10/2026 | UNPAID |
| 35 | HV-035 | 06/09/2026 | Công ty Cổ phần ABC Retail | 0302223334 | 110.000.000 | 8% | 118.800.000 | 21/10/2026 | PAID |
| 36 | HV-036 | 07/09/2026 | Công ty TNHH Minh Phát | 0306667778 | 210.000.000 | 10% | 0 | 06/11/2026 | UNPAID |
| 37 | HV-037 | 08/09/2026 | Công ty Cổ phần Văn phòng Phẩm | 0301112223 | 145.000.000 | 10% | 159.500.000 | 23/10/2026 | PAID |
| 38 | HV-038 | 09/09/2026 | Công ty TNHH Giải pháp Số | 0304445678 | 195.000.000 | 10% | 0 | 24/10/2026 | UNPAID |
| 39 | HV-039 | 10/09/2026 | Công ty Cổ phần TechVN | 0301119988 | 160.000.000 | 8% | 172.800.000 | 25/10/2026 | PAID |
| 40 | HV-040 | 11/09/2026 | Công ty TNHH Đầu tư Đại Cường | 0302228877 | 225.000.000 | 10% | 0 | 26/10/2026 | UNPAID |
| 41 | HV-041 | 12/09/2026 | Công ty Cổ phần Giáo dục Việt Nam | 0309876543 | 135.000.000 | 10% | 148.500.000 | 12/10/2026 | PAID |
| 42 | HV-042 | 13/09/2026 | Công ty TNHH An Khang | 0308889990 | 205.000.000 | 10% | 0 | 28/10/2026 | UNPAID |
| 43 | HV-043 | 14/09/2026 | Công ty Cổ phần Bút Tre VN | 0304443322 | 125.000.000 | 8% | 135.000.000 | 29/10/2026 | PAID |
| 44 | HV-044 | 15/09/2026 | Công ty TNHH Thương mại Lộc Phát | 0303332211 | 170.000.000 | 10% | 0 | 30/10/2026 | UNPAID |
| 45 | HV-045 | 16/09/2026 | Công ty Cổ phần Văn phòng Phẩm | 0301112223 | 195.000.000 | 10% | 214.500.000 | 31/10/2026 | PAID |
| 46 | HV-046 | 17/09/2026 | Công ty TNHH FPT Trading | 0303334445 | 160.000.000 | 8% | 100.000.000 | 01/11/2026 | PARTIAL |
| 47 | HV-047 | 18/09/2026 | Công ty Cổ phần ABC Retail | 0302223334 | 170.000.000 | 10% | 100.000.000 | 02/11/2026 | PARTIAL |

> ✅ **Xác nhận XD-01:** `Σ(INVOICE.subtotal) = 8.500.000.000 đ` khớp với `revenue_by_month[2026-09]` của DOC-01 — kết quả **MATCH ✓**, dung sai ±0,5%.

**Phân bổ trạng thái tại `DEMO_REFERENCE_DATE` = 20/10/2026:**
- `PAID`: 22 hóa đơn (`paid_amount = total_amount`)
- `PARTIAL`: 2 hóa đơn có chủ đích — HV-046 (đã thu 100.000.000 / 172.800.000, còn 72.800.000) và HV-047 (đã thu 100.000.000 / 187.000.000, còn 87.000.000); cả hai chưa đến hạn
- `UNPAID`: 23 hóa đơn (`paid_amount = 0`)
  - Quá hạn (1–30 ngày): 5 hóa đơn — HV-001 (18 ngày, 286.000.000), HV-008 (11 ngày, 154.000.000), HV-030 (4 ngày, 242.000.000), HV-032 (2 ngày, 220.000.000), HV-003 (1 ngày, 162.000.000) → tổng **1.064.000.000 đ**
  - Chưa đến hạn: 18 hóa đơn
- Không có hóa đơn T9 nào quá hạn > 30 ngày. Khoản quá hạn > 90 ngày đến từ **seed lịch sử** HL-001 (bên dưới), không phải từ DOC-02.

**Seed lịch sử phải thu (không thuộc 7 tài liệu mẫu; seed thẳng `business_records`, `computation='SEED'`):**

| STT | Số HĐ | Ngày | Khách hàng | MST khách | Subtotal (VND) | VAT % | Đã thu (VND) | Hạn TT | Trạng thái |
|---|---|---|---|---|---|---|---|---|---|
| L1 | HL-001 | 01/06/2026 | Công ty TNHH Thương mại Lộc Phát | 0303332211 | 220.000.000 | 10% | 0 | 16/07/2026 | UNPAID |

- HL-001: tổng 242.000.000 đ, quá hạn **96 ngày** tại 20/10/2026 → điều kiện đỏ "có khoản quá hạn > 90 ngày" của METRIC-FIN-05.
- Hóa đơn T7, T8 (seed lịch sử, chỉ ở mức tổng): đã thu đủ trước 20/10/2026, trừ HL-001.

> 📌 Mục đích demo: ALERT-FIN-01 (Warning) và ALERT-FIN-05 (Critical) hiển thị trên dashboard CEO/CFO ở bước 1–2 kịch bản (§6). Phép tính ở §4.4.

**Mapping cột Excel → `business_records` (§05 §4.8.1):**

| Cột Excel | Cột `business_records` | Ghi chú |
|---|---|---|
| Số HĐ | `code` | Mã nghiệp vụ, UQ `(record_type, series, code)` (nếu có series) |
| Ngày | `issue_date` | `date` |
| Khách hàng | `customer_id` → bản ghi `CUSTOMER.name` | XT-02 so khớp với #3, #4 |
| MST khách | `tax_code` + `attributes.customer_name_raw` | MST 10 số |
| Subtotal (VND) | `subtotal` | Trước VAT, `bigint` VND — đối chiếu XD-01 |
| VAT % | `vat_rate` | `0.10` / `0.08` (numeric) |
| Đã thu (VND) | `paid_amount` | 0 = `UNPAID`; 0 < x < total = `PARTIAL`; = total = `PAID` |
| Hạn TT | `due_date` | `date` |
| Trạng thái | `status` | `PAID`/`UNPAID`/`PARTIAL` (05 §4.8.2) |

---

### DOC-03 — Báo cáo sales T9/2026

| Thuộc tính | Giá trị |
|---|---|
| Doc type code | `SALES_REPORT` |
| Định dạng | PDF (6 trang) |
| Trụ đích | **Khách hàng** |
| Period | `T9/2026` |
| Trụ đích metrics | METRIC-CUS-01 (pipeline coverage), METRIC-CUS-02 (tỷ lệ chuyển đổi), METRIC-CUS-03 (NRR), METRIC-CUS-04 (tập trung doanh thu) |

**Ground truth fields:**

| Field | Giá trị | Ghi chú |
|---|---|---|
| `period` | `T9/2026` | |
| `pipeline_value_by_stage[]` | Bảng pipeline theo giai đoạn | Xem bên dưới |
| `deals_won_count` | 12 | Cơ hội `WON` có ngày đóng trong T9 |
| `deals_won_value` | `3.200.000.000 đ` | Tổng giá trị deal won (deal mới; doanh thu T9 còn gồm khách cũ mua lặp lại) |
| `deals_lost_count` | 38 | Cơ hội `LOST` có ngày đóng trong T9 |
| `deals_lost_value` | `6.840.000.000 đ` | Bình quân 180.000.000 đ/deal (deal nhỏ, chủ yếu mất ở giai đoạn đầu) |
| `revenue_by_customer[]` | Bảng doanh thu theo khách | 14 khách, group-by từ 47 HĐ DOC-02 |
| `nps_score` | `+32` | Điểm NPS kỳ này |
| `sales_target` | `9.600.000.000 đ` | Kế hoạch tháng T9 → METRIC-FIN-01 %KH = 8.500.000.000 / 9.600.000.000 = **88,5%** (< 90% → Warning) |
| `q4_revenue_recognized_to_date` | `5.500.000.000 đ` | Doanh thu T10 đã xuất hóa đơn 01–20/10/2026 (seed `business_records`, không thuộc DOC-02) |

**Bảng pipeline (trạng thái tại `DEMO_REFERENCE_DATE` = 20/10/2026, các deal mở đều có `close_date` ∈ Q4/2026):**

| Stage | Trạng thái | Deal count | Value (VND) | Probability | Weighted value |
|---|---|---|---|---|---|
| Prospecting | Mở | 15 | `12.000.000.000` | 0,10 | `1.200.000.000` |
| Qualification | Mở | 10 | `10.000.000.000` | 0,25 | `2.500.000.000` |
| Proposal | Mở | 8 | `12.000.000.000` | 0,40 | `4.800.000.000` |
| Negotiation | Mở | 6 | `13.500.000.000` | 0,60 | `8.100.000.000` |
| **Cộng stage mở** | — | **39** | `47.500.000.000` | — | **`16.600.000.000`** |
| Closed Won (T9) | Đóng — không tính coverage | 12 | `3.200.000.000` | — | — |
| Closed Lost (T9) | Đóng — không tính coverage | 38 | `6.840.000.000` | — | — |

> **METRIC-CUS-01** (công thức 03): `Σ(value × probability)` stage mở, `close_date ∈ Q4` / (`chỉ tiêu Q4` − `doanh thu Q4 đã ghi nhận`) = `16.600.000.000 / (27.000.000.000 − 5.500.000.000)` = `16.600.000.000 / 21.500.000.000` = **0,77x** → Đỏ (< 2,0x) → **ALERT-CUS-01 Critical**. Chỉ tiêu Q4 lấy từ DOC-07.
> **Mẫu số ≤ 0** (doanh thu đã ghi nhận ≥ chỉ tiêu quý): hiển thị `—` + nhãn "Đã đạt chỉ tiêu quý", không sinh alert. Không xảy ra với seed này.
> **METRIC-CUS-02** = `12 / (12 + 38)` = **24,0%** → Vàng (< 25%, ≥ 15%) → **ALERT-CUS-02 Warning**.

**Bảng `revenue_by_customer` T9 (group-by trực tiếp 47 hóa đơn DOC-02, sắp xếp giảm dần):**

| # | Khách hàng | MST | Doanh thu T9 (VND, trước VAT) | Số HĐ | Tỷ trọng T9 |
|---|---|---|---|---|---|
| 1 | Công ty Cổ phần Văn phòng Phẩm | 0301112223 | `1.065.000.000` | 6 | 12,5% |
| 2 | Công ty Cổ phần Giáo dục Việt Nam | 0309876543 | `995.000.000` | 6 | 11,7% |
| 3 | Công ty TNHH FPT Trading | 0303334445 | `870.000.000` | 4 | 10,2% |
| 4 | Công ty TNHH Minh Phát | 0306667778 | `825.000.000` | 4 | 9,7% |
| 5 | Công ty TNHH Giải pháp Số | 0304445678 | `715.000.000` | 4 | 8,4% |
| 6 | Công ty TNHH Đầu tư Đại Cường | 0302228877 | `680.000.000` | 3 | 8,0% |
| 7 | Công ty TNHH An Khang | 0308889990 | `655.000.000` | 4 | 7,7% |
| 8 | Công ty Cổ phần ABC Retail | 0302223334 | `605.000.000` | 4 | 7,1% |
| 9 | Công ty TNHH Thương mại Lộc Phát | 0303332211 | `560.000.000` | 3 | 6,6% |
| 10 | Công ty Cổ phần TechVN | 0301119988 | `485.000.000` | 3 | 5,7% |
| 11 | Công ty Cổ phần Bút Tre VN | 0304443322 | `355.000.000` | 3 | 4,2% |
| 12 | Công ty TNHH TechSoft | 0305551234 | `250.000.000` | 1 | 2,9% |
| 13 | Công ty TNHH Đại Lợi | 0307778889 | `240.000.000` | 1 | 2,8% |
| 14 | Công ty Cổ phần Thương mại Quốc tế | 0305556677 | `200.000.000` | 1 | 2,4% |
| — | **Tổng** | — | **`8.500.000.000`** | **47** | 100% |

> ✅ Tên khách hàng và MST khớp 100% với DOC-02 — XD-02 **PASS**. Tổng = `8.500.000.000` / 47 HĐ = `Σ subtotal` DOC-02.
> Top 5 T9 = `4.470.000.000` / `8.500.000.000` = **52,6%** (chỉ để tham khảo; METRIC-CUS-04 dùng rolling 12 tháng, xem bên dưới).

**METRIC-CUS-04 — số liệu seed rolling 12 tháng (10/2025 → 09/2026):**

| Thành phần | Giá trị (VND) | Nguồn |
|---|---|---|
| Tổng doanh thu 12 tháng | `98.000.000.000` | 9 tháng 10/2025–06/2026 = `73.500.000.000` (seed `metric_values`, `computation='SEED'`) + Q3/2026 `24.500.000.000` (DOC-01) |
| Top 5 khách 12 tháng (cùng 5 khách đứng đầu bảng T9) | `49.980.000.000` | Seed lịch sử theo khách + T9 |
| Khách lớn nhất 12 tháng (Văn phòng Phẩm) | `13.720.000.000` (14,0%) | < 15% |
| **METRIC-CUS-04** | `49.980.000.000 / 98.000.000.000` = **51,0%** | Đỏ (Top 5 > 50%) → **ALERT-CUS-04 Critical** |

---

### DOC-04 — Hợp đồng mẫu (2 file PDF scan)

| Thuộc tính | Giá trị |
|---|---|
| Doc type code | `CONTRACT` |
| Định dạng | PDF scan (2 file) |
| Trụ đích | **Khách hàng** |
| Đích entity | `ENT-Contract` |

**File 1 — Hợp đồng với Công ty Cổ phần Giáo dục Việt Nam:**

| Field | Giá trị |
|---|---|
| `contract_number` | `HD-2026-001` |
| `party_a_name` | `Công ty TNHH TM&DV ABC` |
| `party_a_tax_code` | `0301234567` |
| `party_b_name` | `Công ty Cổ phần Giáo dục Việt Nam` |
| `party_b_tax_code` | `0309876543` |
| `contract_value` | `5.000.000.000 đ` |
| `sign_date` | `15/01/2026` |
| `effective_date` | `01/02/2026` |
| `expiry_date` | `31/01/2027` |
| `payment_terms` | `30 ngày` |

**File 2 — Hợp đồng với Công ty TNHH Minh Phát:**

| Field | Giá trị |
|---|---|
| `contract_number` | `HD-2026-002` |
| `party_a_name` | `Công ty TNHH TM&DV ABC` |
| `party_a_tax_code` | `0301234567` |
| `party_b_name` | `Công ty TNHH Minh Phát` |
| `party_b_tax_code` | `0306667778` |
| `contract_value` | `3.000.000.000 đ` |
| `sign_date` | `20/03/2026` |
| `effective_date` | `01/04/2026` |
| `expiry_date` | `30/09/2026` |
| `payment_terms` | `60 ngày` |

> ✅ Tên khách hàng và MST khớp với DOC-02 và DOC-03 — XD-02 **PASS**.

---

### DOC-05 — Biên bản họp giao ban (3 file Word)

| Thuộc tính | Giá trị |
|---|---|
| Doc type code | `MEETING_MINUTES` |
| Định dạng | Word (.docx, 3 file) |
| Trụ đích | **Vận hành** |
| Kỳ | T9/2026 |
| Đích entity | `ENT-Task`, `ENT-Decision` |

**File 1 — Họp giao ban tuần 1 (05/09/2026):**

| Field | Giá trị |
|---|---|
| `meeting_date` | `05/09/2026` |
| `meeting_title` | `Giao ban tuần 1 T9` |
| `chairperson` | **Ông Nguyễn Văn An** (CEO) |
| `attendees[]` | Ông Lê Hoàng Giang (Sales Dir), Cô Phạm Thị Hạnh (HR Mgr), Bà Trần Thị Minh (CFO) |
| `decisions[]` | 2 quyết định |
| `action_items[]` | 5 action items |

**File 2 — Họp giao ban tuần 2 (12/09/2026):**

| Field | Giá trị |
|---|---|
| `meeting_date` | `12/09/2026` |
| `meeting_title` | `Giao ban tuần 2 T9` |
| `chairperson` | **Ông Nguyễn Văn An** |
| `attendees[]` | Ông Lê Hoàng Giang, Cô Phạm Thị Hạnh, Ông Vũ Đức Thắng |
| `decisions[]` | 1 quyết định |
| `action_items[]` | 4 action items |

**File 3 — Họp giao ban tuần 3 (19/09/2026):**

| Field | Giá trị |
|---|---|
| `meeting_date` | `19/09/2026` |
| `meeting_title` | `Giao ban tuần 3 T9` |
| `chairperson` | **Ông Nguyễn Văn An** |
| `attendees[]` | Bà Trần Thị Minh, Cô Phạm Thị Hạnh, Ông Vũ Đức Thắng |
| `decisions[]` | 2 quyết định |
| `action_items[]` | 6 action items |

**Tổng action items từ 3 file:** 15 tasks. Trong đó:
- `DONE` đúng hạn: 9 tasks → **METRIC-OPS-01 = 60%** (chạm đỏ ALERT-OPS-01)
- `DONE` trễ hạn: 2 tasks
- `OPEN` quá hạn: 4 tasks
- Người phụ trách: các nhân sự trong danh sách nhân sự #6 (XD-03 **PASS**)
- Quyết định: 5 quyết định (2 + 1 + 2); 3 quyết định có hạn ≤ 20/10/2026, trong đó 2 làm xong đúng hạn → **METRIC-OPS-03 = 2 / 3 = 66,7%** (Vàng)

> 📌 Seed đủ để METRIC-OPS-01 = 60% < 70% → kích **ALERT-OPS-01 Critical** ở demo.

---

### DOC-06 — Danh sách nhân sự (Excel)

| Thuộc tính | Giá trị |
|---|---|
| Doc type code | `EMPLOYEE_LIST` |
| Định dạng | Excel (`.xlsx`) |
| Trụ đích | **Con người** |
| Period | `T9/2026` |
| Tổng ACTIVE | **45 nhân sự** (khớp 01 §8) |
| Nhạy cảm | **salary** (`sensitivity=SALARY`, 02 §4.3) |

**Schema (8 cột):**

| Cột Excel | Cột `business_records` | Ghi chú |
|---|---|---|
| Mã NV | `code` | Duy nhất |
| Họ tên | `name` | — |
| Chức danh | `title` | — |
| Phòng ban | `department` | FIN / CUS / OPS / HR / ADMIN |
| Ngày vào | `start_date` | `date` |
| Ngày nghỉ | `end_date` | `date` (null nếu còn làm) |
| Trạng thái | `status` | `ACTIVE`/`ON_LEAVE`/`TERMINATED` |
| Lương (VND) | `salary` | **SALARY** — ẩn với role không có quyền |

**Phân bố nhân sự (seed):**

| Phòng ban | Số lượng | Ghi chú |
|---|---|---|
| FIN (Tài chính) | 8 | Bao gồm CFO |
| CUS (Kinh doanh) | 12 | Bao gồm Sales Director |
| OPS (Vận hành) | 10 | Bao gồm trưởng phòng OPS |
| HR (Nhân sự) | 5 | Bao gồm HR Manager |
| ADMIN (Quản trị) | 10 | Bao gồm CEO, IT, bảo vệ |
| **Tổng ACTIVE** | **45** | — |

**Seed lịch sử nghỉ việc:**
- 6 nhân sự TERMINATED trong 12 tháng gần nhất (đã thay người, headcount bình quân 12 tháng = 45) → **METRIC-HR-02 = 6 / 45 = 13,3%** (Xanh, ngưỡng vàng > 15%)
- 2 nhân sự có > 8 task mở + 2 nhân sự khác có ≥ 3 task trễ → **METRIC-HR-03 = 4 / 45 = 8,9%** (Xanh, ngưỡng vàng > 10%)

**Lương cá nhân (dữ liệu nhạy cảm):**
- Tổng quỹ lương tháng T9: **855.000.000 đ** (45 người × bình quân 19.000.000 đ); quỹ lương Q3 = 855.000.000 × 3 = **2.565.000.000 đ**, nằm trong `operating_expenses` DOC-01
- Trung bình: **19.000.000 đ/người**
- Range: 9.000.000 – 60.000.000 đ

> 📌 CEO/CFO **không** được xem lương cá nhân (02 §4.3): field `salary` hiển thị `••••`, API không trả giá trị.
> Drill-down của CEO dừng ở bản ghi tổng hợp. HR Manager và Reviewer (trong ngữ cảnh review) được xem đầy đủ.

---

### DOC-07 — Bảng KPI/OKR Q4/2026

| Thuộc tính | Giá trị |
|---|---|
| Doc type code | `KPI_OKR` |
| Định dạng | Word/Excel (1 file) |
| Trụ đích | **Cả 4 trụ** (FIN, CUS, OPS, HR) |
| Period | `Q4/2026` |
| Đích | `ENT-MetricValue` (TARGET) |

**Ground truth — kế hoạch Q4/2026 (18 chỉ số):**

| Metric code | Mục tiêu Q4 | Đơn vị |Owner | Ghi chú |
|---|---|---|---|---|
| METRIC-FIN-01 | `27.000.000.000` (Quý) | VND | CFO | Plan T10+T11+T12 |
| METRIC-FIN-02 | `≥ 18,0%` | % | CFO | Biên LN gộp |
| METRIC-FIN-03 | `≥ 9,0` | tháng | CFO | Cash runway |
| METRIC-FIN-04 | `≤ 40 ngày` | days | CFO | DSO |
| METRIC-FIN-05 | `≤ 10%` | % | CFO | Công nợ quá hạn |
| METRIC-FIN-06 | `≤ 5%` | % | CFO | Chênh ngân sách |
| METRIC-CUS-01 | `≥ 3,0x` | ratio | Sales Dir | Pipeline coverage |
| METRIC-CUS-02 | `≥ 25%` | % | Sales Dir | Tỷ lệ chuyển đổi |
| METRIC-CUS-03 | `≥ 100%` | % | Sales Dir | NRR |
| METRIC-CUS-04 | `≤ 40%` | % | Sales Dir | Tập trung doanh thu |
| METRIC-CUS-05 | `≥ 30` | score | Sales Dir | NPS |
| METRIC-OPS-01 | `≥ 85%` | % | Ops Mgr | Task đúng hạn |
| METRIC-OPS-02 | `≤ 1` | count | Ops Mgr | Dự án trễ |
| METRIC-OPS-03 | `≥ 80%` | % | Ops Mgr | Thực thi quyết định |
| METRIC-OPS-04 | `≤ 6` | tasks/person | Ops Mgr | Workload |
| METRIC-HR-01 | `≥ 2,0 tỷ` | VND/person | HR Mgr | Doanh thu/nhân sự |
| METRIC-HR-02 | `≤ 15%` | % | HR Mgr | Tỷ lệ nghỉ việc |
| METRIC-HR-03 | `≤ 10%` | % | HR Mgr | Nhân sự quá tải |

> ✅ Tất cả `metric_code` tồn tại trong 18 metric `ENT-Metric` — XD-04 **PASS**.
> DOC-07 là kế hoạch **Q4/2026** (dùng cho kỳ sau và mẫu số METRIC-CUS-01). Kế hoạch T9 của METRIC-FIN-01 (9,6 tỷ) lấy từ DOC-03 `sales_target`.

---

## 4. Quy tắc nhất quán liên tài liệu

### 4.1. XD-01 — Doanh thu BCTC vs Hóa đơn

Theo 04 §12.1:

| Bên so sánh | Nguồn | Giá trị ground truth |
|---|---|---|
| BCTC Q3 — doanh thu tháng T9 | DOC-01 `revenue_by_month[2026-09]` | `8.500.000.000 đ` |
| SUM hóa đơn T9 | DOC-02 `Σ(subtotal)` | `8.500.000.000 đ` |
| Chênh lệch | — | **0 đ (0,0%)** → **MATCH ✓** |

> 📌 **Open question OQ-12:** 01 §8 yêu cầu so #1 (Q3) với #2 (T9) — hai bên khác kỳ. Quy tắc kỳ đã được 04 §12.1 định nghĩa (so tháng M trong BCTC với SUM hóa đơn tháng M). Cần human chốt DEC blocking ở Phase 3.

### 4.2. XD-02 — Tên khách hàng

| Nguồn | Trường | Giá trị ground truth |
|---|---|---|
| DOC-02 | `customer_name` (14 khách) | Tên + MST như bảng §3 DOC-02 |
| DOC-03 | `revenue_by_customer[].customer_name` | Cùng 14 tên + MST |
| DOC-04 | `party_b_name` + `party_b_tax_code` | 2 khách trong #4 có trong #2 |

> ✅ Tên khách hàng khớp 100% — XD-02 **PASS** (fuzzy ≥ 0,90, ưu tiên MST).

### 4.3. XD-03 — Người trong biên bản vs danh sách nhân sự

| Nguồn | Trường | Giá trị ground truth |
|---|---|---|
| DOC-05 | `chairperson`, `attendees[]`, `action_items.assignee` | 8 tên riêng |
| DOC-06 | `EMPLOYEE.name` (45 ACTIVE) | Tất cả 8 tên đều có trong DS nhân sự |

> ✅ Người trong biên bản khớp với danh sách nhân sự — XD-03 **PASS**.

---

### 4.4. Kiểm tra số học (chạy lại bằng script trước khi seed)

Mọi số dưới đây được tính lại từ bảng trong file này (script kiểm tra cộng từng dòng DOC-02, `DEMO_REFERENCE_DATE` = 20/10/2026).

| # | Phép kiểm tra | Phép tính | Kết quả | Khớp |
|---|---|---|---|---|
| K1 | Σ subtotal 47 HĐ DOC-02 | cộng 47 dòng | `8.500.000.000` = DOC-01 `revenue_by_month[2026-09]` | ✓ |
| K2 | Σ VAT 47 HĐ | Σ(subtotal × VAT%) theo dòng | `812.000.000` | ✓ |
| K3 | Σ tổng thanh toán | `8.500.000.000 + 812.000.000` | `9.312.000.000` | ✓ |
| K4 | PAID ⇒ `paid_amount = total_amount` | 22 HĐ `PAID` | Không lệch dòng nào | ✓ |
| K5 | `due_date ≥ issue_date` | 47 HĐ + HL-001 | Không vi phạm | ✓ |
| K6 | Σ `revenue_by_customer` | 14 khách | `8.500.000.000` / 47 HĐ = K1 | ✓ |
| K7 | Doanh thu Q3 | `7.800.000.000 + 8.200.000.000 + 8.500.000.000` | `24.500.000.000` = `revenue` | ✓ |
| K8 | LN gộp | `24.500.000.000 − 20.000.000.000` | `4.500.000.000` (18,4%) | ✓ |
| K9 | LN ròng | `(4.500.000.000 − 3.400.000.000) × (1 − 20%)` | `880.000.000` | ✓ |
| K10 | Quỹ lương ⊂ opex | `855.000.000 × 3 = 2.565.000.000 ≤ 3.400.000.000` | ✓ | ✓ |
| K11 | Tổng phải thu tại 20/10/2026 | còn nợ 47 HĐ `5.217.100.000` (23 UNPAID + 2 PARTIAL) + HL-001 `242.000.000` | `5.459.100.000` | ✓ |
| K12 | Quá hạn tại 20/10/2026 | 5 HĐ T9 `1.064.000.000` (1–30 ngày) + HL-001 `242.000.000` (96 ngày, > 90) | `1.306.000.000` | ✓ |
| K13 | METRIC-FIN-05 | `1.306.000.000 / 5.459.100.000 × 100` | `23,9%` → Đỏ | ✓ |
| K14 | DSO (phải thu 30/09/2026) | `9.312.000.000 + 242.000.000 + 3.446.000.000` | `13.000.000.000`; `13.000.000.000 / 24.500.000.000 × 90 = 47,8` ngày | ✓ |
| K15 | Pipeline coverage | `1.200 + 2.500 + 4.800 + 8.100` (triệu) / `(27.000 − 5.500)` | `16.600.000.000 / 21.500.000.000 = 0,77x` | ✓ |
| K16 | NRR | `23.300.000.000 / 22.300.000.000` | `104,5%`; `23.300 + 1.200 = 24.500` (triệu) | ✓ |

---

## 5. Seed dữ liệu cho 18 metric và alert demo

### 5.1. Giá trị metric (ACTUAL) tại `DEMO_REFERENCE_DATE` = 20/10/2026

Ngưỡng lấy nguyên văn từ `03-DASHBOARD-SPEC.md` §2 (đánh giá Đỏ trước, Vàng sau). Không chỉnh ngưỡng; chỉ chọn số liệu gốc.

| Metric | Phép tính từ seed | Giá trị | Ngưỡng 03 | Trạng thái | Alert |
|---|---|---|---|---|---|
| METRIC-FIN-01 Doanh thu tháng | `8.500.000.000 / 9.600.000.000` (KH T9, DOC-03) | `8,5 tỷ` · **88,5% KH** | V < 90%; Đ < 80% | Vàng | **ALERT-FIN-01 Warning** |
| METRIC-FIN-02 Biên LN gộp | `4.500.000.000 / 24.500.000.000` | `18,4%` | V < 15%; Đ < 10% | Xanh | — |
| METRIC-FIN-03 Cash runway | `6.800.000.000 / 850.000.000` (dòng tiền ra ròng bình quân 3 tháng) | `8,0 tháng` | V < 9; Đ < 6 | Vàng | **ALERT-FIN-03 Warning** |
| METRIC-FIN-04 DSO | `13.000.000.000 / 24.500.000.000 × 90` | `47,8 ngày` | V > 45; Đ > 60 | Vàng | **ALERT-FIN-04 Warning** |
| METRIC-FIN-05 Công nợ quá hạn | `1.306.000.000 / 5.459.100.000` (§4.4) | `23,9%` · `1,3 tỷ` | V > 10%; Đ > 20% hoặc khoản > 90 ngày | Đỏ (cả 2 điều kiện) | **ALERT-FIN-05 Critical** |
| METRIC-FIN-06 Chênh ngân sách | `(3.400.000.000 − 3.150.000.000) / 3.150.000.000` | `+7,9%` | V > 5%; Đ > 10% | Vàng | **ALERT-FIN-06 Warning** |
| METRIC-CUS-01 Pipeline coverage | `16.600.000.000 / (27.000.000.000 − 5.500.000.000)` | `0,77x` | V < 3,0x; Đ < 2,0x | Đỏ | **ALERT-CUS-01 Critical** |
| METRIC-CUS-02 Tỷ lệ chuyển đổi | `12 / (12 + 38)` | `24,0%` | V < 25%; Đ < 15% | Vàng | **ALERT-CUS-02 Warning** |
| METRIC-CUS-03 NRR | `23.300.000.000 / 22.300.000.000` (§5.2) | `104,5%` | V < 100%; Đ < 90% | Xanh | — |
| METRIC-CUS-04 Tập trung DT | `49.980.000.000 / 98.000.000.000` (rolling 12 tháng) | `51,0%` | V Top5 > 40%; Đ Top5 > 50% | Đỏ | **ALERT-CUS-04 Critical** |
| METRIC-CUS-05 NPS | DOC-03 `nps_score` | `+32` | V < 30; Đ < 0 | Xanh | — |
| METRIC-OPS-01 Task đúng hạn | `9 / 15` (DOC-05) | `60,0%` | V < 85%; Đ < 70% | Đỏ | **ALERT-OPS-01 Critical** |
| METRIC-OPS-02 Dự án trễ | 2 dự án trễ ≤ 30 ngày (seed `PROJECT`) | `2` | V ≥ 1; Đ ≥ 3 hoặc trễ > 30 ngày | Vàng | **ALERT-OPS-02 Warning** |
| METRIC-OPS-03 Thực thi quyết định | `2 / 3` quyết định đến hạn làm đúng hạn (trong 5 quyết định DOC-05) | `66,7%` | V < 80%; Đ < 60% | Vàng | **ALERT-OPS-03 Warning** |
| METRIC-OPS-04 Workload | `81` task mở / `15` assignee; 2 người > 8 task | `5,4 task/người` | V > 6 hoặc ≥ 1 người > 8; Đ > 8 hoặc ≥ 3 người > 8 | Vàng (2 người > 8) | **ALERT-OPS-04 Warning** |
| METRIC-HR-01 Doanh thu/nhân sự | `98.000.000.000 / 45` | `2,18 tỷ/người` | V < 2,0; Đ < 1,7 | Xanh | — |
| METRIC-HR-02 Tỷ lệ nghỉ việc | `6 / 45` (headcount bình quân 12 tháng) | `13,3%` | V > 15%; Đ > 25% | Xanh | — |
| METRIC-HR-03 Nhân sự quá tải | `(2 người > 8 task mở + 2 người ≥ 3 task trễ) / 45` | `8,9%` | V > 10%; Đ > 20% | Xanh | — |

Tổng: **12 alert** (4 Critical: FIN-05, CUS-01, CUS-04, OPS-01; 8 Warning: FIN-01, FIN-03, FIN-04, FIN-06, CUS-02, OPS-02, OPS-03, OPS-04); 6 metric xanh (FIN-02, CUS-03, CUS-05, HR-01, HR-02, HR-03). Task mở OPS-04 gồm 15 action item DOC-05 và 66 task seed thẳng `business_records` (`record_type='TASK'`).

> 📌 **Alert dùng trong kịch bản demo (02 §5.3, 01 §11):**
> - Bước 1 (CEO): ALERT-FIN-05 Critical, ALERT-CUS-04 Critical, ALERT-OPS-01 Critical nổi bật đầu danh sách
> - Bước 2 (CEO): click **ALERT-FIN-01 Warning** (doanh thu 88,5% KH) → drill-down DOC-02, DOC-01
> - Bước 3 (CFO): ALERT-FIN-06 Warning (chênh ngân sách +7,9%), ALERT-FIN-03 Warning (runway 8,0 tháng)

### 5.2. Seed lịch sử cho NRR (METRIC-CUS-03)

Định nghĩa 03: `doanh thu kỳ này từ nhóm khách đã có ở kỳ gốc / doanh thu kỳ gốc của chính nhóm đó × 100`, kỳ gốc = Q3/2025.

| Thành phần | Giá trị (VND) | Ghi chú |
|---|---|---|
| Nhóm khách kỳ gốc | 12 khách | 14 khách T9 trừ TechSoft và Thương mại Quốc tế (khách mới 2026) |
| Doanh thu Q3/2025 của nhóm 12 khách | `22.300.000.000` | Seed `metric_values.breakdown`, `computation='SEED'` |
| Doanh thu Q3/2026 của cùng nhóm 12 khách | `23.300.000.000` | Từ seed T7, T8 + DOC-02 T9 |
| Doanh thu Q3/2026 từ khách mới | `1.200.000.000` | Không tính vào NRR |
| Tổng Q3/2026 | `24.500.000.000` | = 23.300.000.000 + 1.200.000.000 = DOC-01 `revenue` ✓ |
| **NRR** | `23.300.000.000 / 22.300.000.000 × 100` = **104,5%** | Xanh |

---

## 6. Quy tắc demo và kịch bản 15 phút

### 6.1. Kịch bản theo 02 §5.3

| Bước | Role | Hành động | Alert/metric liên quan |
|---|---|---|---|
| 1 | ROLE-01 CEO | Mở app → xem dashboard 4 trụ | ALERT-FIN-05, ALERT-CUS-04, ALERT-OPS-01 (Critical) nổi bật |
| 2 | ROLE-01 CEO | Click ALERT-FIN-01 (88,5% KH) → drill-down | → DOC-02, DOC-01 |
| 3 | ROLE-02 CFO | Chuyển vai → xem ngân sách | ALERT-FIN-06 (+7,9%), ALERT-FIN-03 (8,0 tháng) |
| 4 | ROLE-01 CEO | "Nạp doanh nghiệp" UC-07 | Upload 7 tài liệu |
| 5 | ROLE-05 Reviewer | Duyệt 1 tài liệu FIN | → commit, metric cập nhật |
| 6 | ROLE-01 CEO | Quay lại dashboard | → drill-down đến tài liệu vừa duyệt |

### 6.2. Demo mode flag

- `DEMO_MODE=true` bật dropdown switcher (02 §5.2 R5, 07 §8.1.1)
- Khi tắt: dropdown ẩn, endpoint role switch trả `404` (07 §8.1.1)

---

## 7. Open questions

| # | Câu hỏi | Đề xuất | Ảnh hưởng |
|---|---|---|---|
| OQ-01 | Kỳ đối chiếu Q3 vs T9 trong 01 §8: nên đổi thành so tháng trong tháng, hay mở rộng #2 thành hóa đơn cả Q3? | Giữ mặc định 04 §12.1 (so tháng trong tháng); human chốt DEC blocking | 01, 04, 13 |
| OQ-02 | Script seed: dùng `pnpm` hay `uv`? (`07-TECH-ARCHITECTURE.md` OQ-03 chưa chốt) | Chưa chốt — theo quyết định của 07 OQ-03; 09 map task tương ứng | 07, 09 |
| OQ-03 | NRR (METRIC-CUS-03) cần seed dữ liệu 12 tháng trước — có cần tạo thêm file lịch sử không? | Seed trực tiếp vào `business_records` + `metric_values` với `computation='SEED'` | 03, 05 |
| OQ-04 | NPS chưa có tài liệu nguồn rõ ràng — có đưa vào #7 KPI/OKR không? | Đưa `nps_score` vào DOC-03 và DOC-07 | 03, 07 |
| OQ-05 | Ngưỡng vàng/đỏ của 18 metric là đề xuất từ writer — cần business xác nhận? | Dùng làm seed demo; chỉnh trong 08 nếu có DEC mới | 03 |
| OQ-06 | Có cần seed dữ liệu quá khứ 12 tháng cho METRIC-HR-01, HR-02, CUS-04 (rolling)? | Seed `metric_values` với `period_type='ROLLING_12M'`, `computation='SEED'` | 03, 05 |
| OQ-07 | Phân phối ALERT-OPS: ROLE-04 (HR) chỉ nhận ALERT-HR-* theo 02 §3.3 — đúng hay cần mở rộng? | Giữ đúng 02 §3.3 | 02, 03 |
| OQ-08 | `DEMO_REFERENCE_DATE` = 20/10/2026 là hằng số "hôm nay" cho mọi metric phụ thuộc ngày (FIN-05, OPS-01..03). Đặt bằng biến cấu hình nào? | Đề xuất env `DEMO_REFERENCE_DATE`; 07/10 chốt | 07, 10 |
| OQ-09 | Seed ngoài 7 tài liệu (HL-001, doanh thu T7/T8 + 12 tháng theo khách, 66 task, 5 dự án, doanh thu T10 5,5 tỷ, KH T9 9,6 tỷ) chưa có tài liệu gốc → drill-down P01 dừng ở bản ghi seed. Có cần tạo tài liệu nguồn cho phần này không? | Gắn nhãn "Dữ liệu seed lịch sử" trong panel nguồn | 03 §4, 05 |
| OQ-10 | Chưa liệt kê đủ 45 nhân viên, chi tiết 15 action item / 5 quyết định DOC-05 và bộ tài liệu "lệch số" để demo MISMATCH | Bổ sung ở vòng sau hoặc khi viết script seed | 04, 09 |

---

## 8. Version

- **Version:** 1.0.0
- **Last updated:** 2026-10-17
- **Applies to:** Aureon Demo v1.0
- **Maintainer:** @CyEyes

