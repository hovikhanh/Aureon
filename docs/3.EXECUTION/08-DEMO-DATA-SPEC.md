# 08 — DEMO DATA SPEC (v2)

> Dữ liệu demo của **Aureon v2**: hồ sơ Công ty TNHH TM&DV ABC mở rộng (~150 nhân sự, DEC-136), 10 tài khoản demo (ROLE-01..10, DEC-128), ground truth 9 tài liệu mẫu, quy tắc nhất quán XD, seed cho 31 metric của 5 trụ F.O.C.U.S (00 §4.2), seed sự kiện (00 §4.5) và kịch bản demo 20 phút (01 §11).
> Nguồn: 00 §4, 01 §8/§11, 02 (quyền), 03 (metric — xem lưu ý §0), 04 (doc type, schema), 05 (entity). Bản v1 (45 NV, 7 tài liệu, 18 metric) lưu ở nhánh `v1`.
> **Mọi số trong file được tính bằng script** (DEC-022); kết quả kiểm tra ở §9.

---

## 0. Lưu ý về công thức và ngưỡng

§6 đã **đối chiếu với `03-DASHBOARD-SPEC.md` 2.0.0** (2026-10-19): công thức, đơn vị, ngưỡng mặc định và bảng level rủi ro (BR-RSK-02) lấy từ 03; 03 thắng khi lệch. "Δ3k" = so với trung bình 3 kỳ gần nhất. Quy ước đánh giá: kiểm điều kiện **Critical trước, Warning sau**; còn lại OK.

---

## 1. Hồ sơ công ty ABC

| Thuộc tính | Giá trị |
|---|---|
| Tên đầy đủ | Công ty TNHH Thương mại & Dịch vụ ABC |
| Mã số thuế (MST) | `0301234567` |
| Ngành | Phân phối thiết bị văn phòng + dịch vụ bảo trì + nền tảng đặt hàng B2B |
| Quy mô | **150 nhân sự ACTIVE**, 7 phòng ban (§1.1) |
| Doanh thu | ~**294 tỷ VNĐ** 12 tháng gần nhất (10/2025–09/2026); Q3/2026 = **73,5 tỷ** |
| Trụ sở | Tầng 7, Tòa nhà Bitexco Financial Tower, 2 Hải Triều, Phường Sài Gòn, TP. Hồ Chí Minh |
| Chi nhánh | Số 12 Trần Hưng Đạo, Phường Cửa Nam, TP. Hà Nội |
| Người đại diện | Ông **Nguyễn Văn An** — Tổng giám đốc |
| Niên độ | Năm dương lịch |
| Kỳ demo | T9/2026, Q3/2026; kế hoạch Q4/2026 |
| `DEMO_REFERENCE_DATE` | **2026-10-20** — "hôm nay" cho mọi metric phụ thuộc ngày |
| Tiền tệ | VND, lưu `BIGINT` số nguyên (05 §1) |

**Sản phẩm / dịch vụ (trụ U):**

| Mã | Tên | Mô tả | Doanh thu T9/2026 (trước VAT) |
|---|---|---|---|
| `PRD-SUP` | ABC Supply | Phân phối giấy, mực, máy in, thiết bị | `19.125.000.000` |
| `PRD-CARE` | ABC Care | Gói bảo trì máy văn phòng theo hợp đồng | `4.080.000.000` |
| `PRD-ORDER` | ABC Order | Nền tảng đặt hàng B2B (phí thuê bao + phí giao dịch) | `2.295.000.000` |
| | **Tổng** | | **`25.500.000.000`** (= doanh thu T9 DOC-01) |

**Quy tắc P04:** ngày `dd/mm/yyyy` khi hiển thị, ISO khi lưu; tiền `1.250.000 đ` / `1,2 tỷ`; MST 10 số; tên người giả định, CCCD/SĐT placeholder `0123456789` / `09xxxxxxxx`; địa chỉ theo đơn vị hành chính mới (2 cấp).

### 1.1. Phòng ban (`ENT-Department`)

| Mã | Phòng ban | Trưởng bộ phận | Headcount ACTIVE | Trụ liên quan |
|---|---|---|---|---|
| `BOD` | Ban Giám đốc | Nguyễn Văn An (CEO) | 6 | Toàn bộ |
| `FIN` | Tài chính – Kế toán | Trần Thị Minh (CFO) | 14 | F |
| `SAL` | Kinh doanh | Lê Hoàng Giang (VP Sales) | 42 | C |
| `LOG` | Kho vận & Giao hàng | Hoàng Minh Tuấn (Manager) | 38 | O |
| `SVC` | Kỹ thuật & Dịch vụ (ABC Care) | Đặng Văn Khải | 24 | O, U |
| `PRD` | Sản phẩm & Công nghệ (ABC Order) | Đỗ Quang Huy (CPO) | 18 | U |
| `HRA` | Nhân sự – Hành chính | Phạm Thị Hạnh (HR Manager) | 8 | O |
| | **Tổng** | | **150** | |

BOD gồm: CEO, CFO, VP Sales, CPO, Risk Manager (Bùi Thu Trang), Trợ lý TGĐ. CFO/VP Sales/CPO được tính ở BOD, đồng thời là trưởng bộ phận FIN/SAL/PRD (`head_employee_id`).

---

## 2. Tài khoản demo — 10 user, 1 role mỗi người

Mỗi user một role cố định (02); switcher chỉ bật khi `DEMO_MODE=true`. **Mật khẩu chỉ qua env**, seed băm (bcrypt/argon2) và chỉ lưu hash; không ghi giá trị trong tài liệu, repo hay log.

| Role | Email | Họ tên | Phòng ban | Env mật khẩu | Trang chủ (06) |
|---|---|---|---|---|---|
| ROLE-01 `CEO` | `ceo@abc.demo` | Ông Nguyễn Văn An | BOD | `DEMO_CEO_PASSWORD` | SCR-01 Briefing công ty |
| ROLE-02 `CFO` | `cfo@abc.demo` | Bà Trần Thị Minh | BOD/FIN | `DEMO_CFO_PASSWORD` | SCR-01 (F + S) |
| ROLE-03 `VP_SALES` | `sales@abc.demo` | Ông Lê Hoàng Giang | BOD/SAL | `DEMO_VP_SALES_PASSWORD` | SCR-01 (C) |
| ROLE-04 `HR_MANAGER` | `hr@abc.demo` | Bà Phạm Thị Hạnh | HRA | `DEMO_HR_MANAGER_PASSWORD` | SCR-01 (O) |
| ROLE-05 `REVIEWER` | `reviewer@abc.demo` | Anh Vũ Đức Thắng | FIN | `DEMO_REVIEWER_PASSWORD` | SCR-08 / SCR-10 |
| ROLE-06 `CPO` | `cpo@abc.demo` | Ông Đỗ Quang Huy | BOD/PRD | `DEMO_CPO_PASSWORD` | SCR-01 (U) |
| ROLE-07 `RISK_MANAGER` | `risk@abc.demo` | Bà Bùi Thu Trang | BOD | `DEMO_RISK_MANAGER_PASSWORD` | SCR-01 (S) |
| ROLE-08 `MANAGER` | `manager@abc.demo` | Ông Hoàng Minh Tuấn | LOG | `DEMO_MANAGER_PASSWORD` | SCR-01 đơn vị LOG |
| ROLE-09 `EMPLOYEE` | `employee@abc.demo` | Chị Ngô Thị Lan | SAL | `DEMO_EMPLOYEE_PASSWORD` | SCR-01 việc hôm nay |
| ROLE-10 `ADMIN` | `admin@abc.demo` | Anh Trịnh Văn Khoa | HRA (IT) | `DEMO_ADMIN_PASSWORD` | SCR-15 |

```env
# .env.example — chỉ placeholder
DEMO_MODE=true
DEMO_REFERENCE_DATE=2026-10-20
DEMO_CEO_PASSWORD=<change-me>
DEMO_CFO_PASSWORD=<change-me>
DEMO_VP_SALES_PASSWORD=<change-me>
DEMO_HR_MANAGER_PASSWORD=<change-me>
DEMO_REVIEWER_PASSWORD=<change-me>
DEMO_CPO_PASSWORD=<change-me>
DEMO_RISK_MANAGER_PASSWORD=<change-me>
DEMO_MANAGER_PASSWORD=<change-me>
DEMO_EMPLOYEE_PASSWORD=<change-me>
DEMO_ADMIN_PASSWORD=<change-me>
```

Thiếu biến nào → seed **bỏ qua** tài khoản đó và báo lỗi rõ ràng (không tạo mật khẩu mặc định). Tên biến v1 `DEMO_SALES_PASSWORD`, `DEMO_HR_PASSWORD` đổi theo mã role (OQ-02).

---

## 3. Chín tài liệu mẫu — ground truth

| DOC | Doc type | Định dạng | Kỳ | Entity đích (05) | Trụ |
|---|---|---|---|---|---|
| DOC-01 | `FINANCIAL_REPORT` | PDF scan 12 trang (trang 7 mờ) | Q3/2026 | ENT-Revenue, ENT-Expense, ENT-CashPosition, ENT-Budget | F |
| DOC-02 | `INVOICE` | Excel 47 dòng | T9/2026 | ENT-Invoice, ENT-InvoiceLine, ENT-Client | F, C |
| DOC-03 | `SALES_REPORT` | PDF 6 trang | T9/2026 | ENT-Deal, ENT-SalesTarget | C |
| DOC-04 | `CONTRACT` | 2 PDF scan | 2026 | ENT-Contract | C, F |
| DOC-05 | `MEETING_MINUTES` | 3 Word | T9/2026 | ENT-Meeting, ENT-Decision, ENT-Task | O, S |
| DOC-06 | `EMPLOYEE_LIST` | Excel 150 dòng | T9/2026 | ENT-Employee, ENT-Department, ENT-SalaryHistory | O |
| DOC-07 | `KPI_OKR` | Excel 1 file | Q4/2026 | ENT-Objective, ENT-KeyResult, ENT-KPI | cả 5 |
| DOC-08 | `PRODUCT_REPORT` | PDF 8 trang | T9/2026 | ENT-ProductMetric, ENT-Release, ENT-RoadmapItem | U |
| DOC-09 | `RISK_REGISTER` | Excel 11 dòng | Q3/2026 | ENT-Risk, ENT-RiskAssessment, ENT-Mitigation | S |

### DOC-01 — Báo cáo tài chính Q3/2026 (`FINANCIAL_REPORT`)

PDF scan 12 trang; **trang 7 mờ** (`ocr_confidence < 0,60` → Thấp, buộc review — DEC-133).

| Field | Ground truth | Ghi chú |
|---|---|---|
| `company_name` / `tax_code` | `Công ty TNHH TM&DV ABC` / `0301234567` | |
| `period` | `2026-Q3` | |
| `revenue` | `73.500.000.000` | Trang 3 P&L |
| `revenue_by_month[]` | T7 `23.400.000.000` · T8 `24.600.000.000` · T9 `25.500.000.000` | Trang 4; Σ = 73.500.000.000 |
| `cogs` | `60.000.000.000` | |
| `gross_profit` | `13.500.000.000` | Biên gộp **18,4%** |
| `operating_expenses` | `10.200.000.000` | Gồm quỹ lương Q3 `8.775.000.000` (khớp DOC-06) + chi phí khác `1.425.000.000` |
| `budget_opex` | `9.450.000.000` | Trang 9, chi tiết theo phòng ban ở bảng dưới |
| `profit_before_tax` | `3.300.000.000` | = 13.500.000.000 − 10.200.000.000 |
| `income_tax` | `660.000.000` | 20% |
| `net_profit` | `2.640.000.000` | |
| `cash_end_of_period` | `20.400.000.000` | 30/09/2026 |
| `net_cash_flow_by_month[]` | T7 `−2.100.000.000` · T8 `−2.550.000.000` · T9 `−3.000.000.000` | Net burn bình quân 3 tháng `2.550.000.000` |
| `forecast_net_burn_t9` | `2.500.000.000` | Kịch bản cơ sở (ENT-Forecast `BASE`) → METRIC-FIN-07 |
| `receivables` | `39.000.000.000` | Tại 30/09/2026 (gồm VAT) = 47 HĐ T9 `27.936.000.000` + HL-001 `726.000.000` + HĐ T8 chưa thu `10.338.000.000` |

**Ngân sách vs thực chi Q3 theo phòng ban (`ENT-Budget`, triệu đồng):**

| Phòng ban | Ngân sách | Thực chi | Chênh lệch |
|---|---|---|---|
| BOD | 900 | 930 | +3,3% |
| FIN | 1.100 | 1.120 | +1,8% |
| SAL | 3.200 | 3.650 | **+14,1%** → `EVT-finance.budget_exceeded` |
| LOG | 1.850 | 1.980 | +7,0% |
| SVC | 1.200 | 1.270 | +5,8% |
| PRD | 800 | 850 | +6,2% |
| HRA | 400 | 400 | 0,0% |
| **Tổng** | **9.450** | **10.200** | **+7,9%** |

Ngân sách / thực chi theo phòng ban ở đây là **chi phí vận hành phân bổ** (gồm lương phân bổ). `budget_exceeded` phát khi chênh của một phòng ban > 10% (giả định, OQ-01).

---

### DOC-02 — Danh sách hóa đơn T9/2026 (`INVOICE`)

| Thuộc tính | Giá trị |
|---|---|
| Định dạng | Excel, 47 dòng |
| Σ subtotal (trước VAT) | **`25.500.000.000`** = DOC-01 `revenue_by_month[2026-09]` → XD-01 MATCH |
| Σ VAT | `2.436.000.000` (33 dòng 10%, 14 dòng 8%; tính theo từng dòng) |
| Σ thanh toán | `27.936.000.000` |
| Điều khoản | 30 ngày (Giáo dục Việt Nam), 60 ngày (Minh Phát), 45 ngày (khách còn lại); `due_date ≥ issue_date` |
| Cột "Đã thu" | Tính đến 20/10/2026; mọi khoản thu phát sinh từ 01/10/2026 (tại 30/09 cả 47 HĐ chưa thu) |

| STT | Số HĐ | Ngày | Khách hàng | MST khách | Subtotal (VND) | VAT % | Đã thu (VND) | Hạn TT | Trạng thái |
|---|---|---|---|---|---|---|---|---|---|
| 1 | HV-001 | 02/09/2026 | Công ty Cổ phần Giáo dục Việt Nam | 0309876543 | 780.000.000 | 10% | 0 | 02/10/2026 | UNPAID |
| 2 | HV-002 | 03/09/2026 | Công ty TNHH TechSoft | 0305551234 | 750.000.000 | 10% | 825.000.000 | 18/10/2026 | PAID |
| 3 | HV-003 | 04/09/2026 | Công ty TNHH Giải pháp Số | 0304445678 | 450.000.000 | 8% | 0 | 19/10/2026 | UNPAID |
| 4 | HV-004 | 05/09/2026 | Công ty Cổ phần Văn phòng Phẩm | 0301112223 | 285.000.000 | 10% | 313.500.000 | 20/10/2026 | PAID |
| 5 | HV-005 | 06/09/2026 | Công ty TNHH Minh Phát | 0306667778 | 960.000.000 | 10% | 0 | 05/11/2026 | UNPAID |
| 6 | HV-006 | 07/09/2026 | Công ty Cổ phần ABC Retail | 0302223334 | 495.000.000 | 8% | 534.600.000 | 22/10/2026 | PAID |
| 7 | HV-007 | 08/09/2026 | Công ty TNHH Đại Lợi | 0307778889 | 720.000.000 | 10% | 0 | 23/10/2026 | UNPAID |
| 8 | HV-008 | 09/09/2026 | Công ty Cổ phần Giáo dục Việt Nam | 0309876543 | 420.000.000 | 10% | 0 | 09/10/2026 | UNPAID |
| 9 | HV-009 | 10/09/2026 | Công ty TNHH An Khang | 0308889990 | 255.000.000 | 8% | 275.400.000 | 25/10/2026 | PAID |
| 10 | HV-010 | 11/09/2026 | Công ty Cổ phần Văn phòng Phẩm | 0301112223 | 585.000.000 | 10% | 0 | 26/10/2026 | UNPAID |
| 11 | HV-011 | 12/09/2026 | Công ty TNHH FPT Trading | 0303334445 | 870.000.000 | 10% | 957.000.000 | 27/10/2026 | PAID |
| 12 | HV-012 | 13/09/2026 | Công ty TNHH Giải pháp Số | 0304445678 | 420.000.000 | 8% | 0 | 28/10/2026 | UNPAID |
| 13 | HV-013 | 14/09/2026 | Công ty Cổ phần Thương mại Quốc tế | 0305556677 | 600.000.000 | 10% | 660.000.000 | 29/10/2026 | PAID |
| 14 | HV-014 | 15/09/2026 | Công ty TNHH Minh Phát | 0306667778 | 525.000.000 | 10% | 0 | 14/11/2026 | UNPAID |
| 15 | HV-015 | 16/09/2026 | Công ty Cổ phần TechVN | 0301119988 | 555.000.000 | 10% | 610.500.000 | 31/10/2026 | PAID |
| 16 | HV-016 | 17/09/2026 | Công ty TNHH Đầu tư Đại Cường | 0302228877 | 810.000.000 | 10% | 0 | 01/11/2026 | UNPAID |
| 17 | HV-017 | 18/09/2026 | Công ty Cổ phần Giáo dục Việt Nam | 0309876543 | 390.000.000 | 8% | 421.200.000 | 18/10/2026 | PAID |
| 18 | HV-018 | 19/09/2026 | Công ty TNHH Thương mại Lộc Phát | 0303332211 | 570.000.000 | 10% | 0 | 03/11/2026 | UNPAID |
| 19 | HV-019 | 20/09/2026 | Công ty Cổ phần Bút Tre VN | 0304443322 | 300.000.000 | 8% | 324.000.000 | 04/11/2026 | PAID |
| 20 | HV-020 | 21/09/2026 | Công ty TNHH An Khang | 0308889990 | 435.000.000 | 10% | 0 | 05/11/2026 | UNPAID |
| 21 | HV-021 | 22/09/2026 | Công ty Cổ phần Văn phòng Phẩm | 0301112223 | 720.000.000 | 10% | 792.000.000 | 06/11/2026 | PAID |
| 22 | HV-022 | 23/09/2026 | Công ty TNHH FPT Trading | 0303334445 | 570.000.000 | 10% | 0 | 07/11/2026 | UNPAID |
| 23 | HV-023 | 24/09/2026 | Công ty Cổ phần ABC Retail | 0302223334 | 480.000.000 | 8% | 518.400.000 | 08/11/2026 | PAID |
| 24 | HV-024 | 25/09/2026 | Công ty TNHH Giải pháp Số | 0304445678 | 690.000.000 | 10% | 0 | 09/11/2026 | UNPAID |
| 25 | HV-025 | 26/09/2026 | Công ty Cổ phần Giáo dục Việt Nam | 0309876543 | 525.000.000 | 10% | 577.500.000 | 26/10/2026 | PAID |
| 26 | HV-026 | 27/09/2026 | Công ty TNHH Minh Phát | 0306667778 | 360.000.000 | 8% | 0 | 26/11/2026 | UNPAID |
| 27 | HV-027 | 28/09/2026 | Công ty Cổ phần Văn phòng Phẩm | 0301112223 | 585.000.000 | 10% | 643.500.000 | 12/11/2026 | PAID |
| 28 | HV-028 | 29/09/2026 | Công ty TNHH Đầu tư Đại Cường | 0302228877 | 555.000.000 | 10% | 0 | 13/11/2026 | UNPAID |
| 29 | HV-029 | 30/09/2026 | Công ty Cổ phần TechVN | 0301119988 | 420.000.000 | 8% | 453.600.000 | 14/11/2026 | PAID |
| 30 | HV-030 | 01/09/2026 | Công ty TNHH An Khang | 0308889990 | 660.000.000 | 10% | 0 | 16/10/2026 | UNPAID |
| 31 | HV-031 | 02/09/2026 | Công ty Cổ phần Bút Tre VN | 0304443322 | 390.000.000 | 10% | 429.000.000 | 17/10/2026 | PAID |
| 32 | HV-032 | 03/09/2026 | Công ty TNHH Thương mại Lộc Phát | 0303332211 | 600.000.000 | 10% | 0 | 18/10/2026 | UNPAID |
| 33 | HV-033 | 04/09/2026 | Công ty Cổ phần Giáo dục Việt Nam | 0309876543 | 465.000.000 | 8% | 502.200.000 | 04/10/2026 | PAID |
| 34 | HV-034 | 05/09/2026 | Công ty TNHH FPT Trading | 0303334445 | 690.000.000 | 10% | 0 | 20/10/2026 | UNPAID |
| 35 | HV-035 | 06/09/2026 | Công ty Cổ phần ABC Retail | 0302223334 | 330.000.000 | 8% | 356.400.000 | 21/10/2026 | PAID |
| 36 | HV-036 | 07/09/2026 | Công ty TNHH Minh Phát | 0306667778 | 630.000.000 | 10% | 0 | 06/11/2026 | UNPAID |
| 37 | HV-037 | 08/09/2026 | Công ty Cổ phần Văn phòng Phẩm | 0301112223 | 435.000.000 | 10% | 478.500.000 | 23/10/2026 | PAID |
| 38 | HV-038 | 09/09/2026 | Công ty TNHH Giải pháp Số | 0304445678 | 585.000.000 | 10% | 0 | 24/10/2026 | UNPAID |
| 39 | HV-039 | 10/09/2026 | Công ty Cổ phần TechVN | 0301119988 | 480.000.000 | 8% | 518.400.000 | 25/10/2026 | PAID |
| 40 | HV-040 | 11/09/2026 | Công ty TNHH Đầu tư Đại Cường | 0302228877 | 675.000.000 | 10% | 0 | 26/10/2026 | UNPAID |
| 41 | HV-041 | 12/09/2026 | Công ty Cổ phần Giáo dục Việt Nam | 0309876543 | 405.000.000 | 10% | 445.500.000 | 12/10/2026 | PAID |
| 42 | HV-042 | 13/09/2026 | Công ty TNHH An Khang | 0308889990 | 615.000.000 | 10% | 0 | 28/10/2026 | UNPAID |
| 43 | HV-043 | 14/09/2026 | Công ty Cổ phần Bút Tre VN | 0304443322 | 375.000.000 | 8% | 405.000.000 | 29/10/2026 | PAID |
| 44 | HV-044 | 15/09/2026 | Công ty TNHH Thương mại Lộc Phát | 0303332211 | 510.000.000 | 10% | 0 | 30/10/2026 | UNPAID |
| 45 | HV-045 | 16/09/2026 | Công ty Cổ phần Văn phòng Phẩm | 0301112223 | 585.000.000 | 10% | 643.500.000 | 31/10/2026 | PAID |
| 46 | HV-046 | 17/09/2026 | Công ty TNHH FPT Trading | 0303334445 | 480.000.000 | 8% | 300.000.000 | 01/11/2026 | PARTIAL |
| 47 | HV-047 | 18/09/2026 | Công ty Cổ phần ABC Retail | 0302223334 | 510.000.000 | 10% | 300.000.000 | 02/11/2026 | PARTIAL |

**Trạng thái tại 20/10/2026:** 22 `PAID` · 2 `PARTIAL` (HV-046 đã thu 300.000.000 / 518.400.000, còn 218.400.000; HV-047 đã thu 300.000.000 / 561.000.000, còn 261.000.000 — chưa đến hạn) · 23 `UNPAID`, trong đó **5 quá hạn 1–30 ngày**: HV-001 (18 ngày, 858.000.000), HV-008 (11 ngày, 462.000.000), HV-030 (4 ngày, 726.000.000), HV-032 (2 ngày, 660.000.000), HV-003 (1 ngày, 486.000.000) → **3.192.000.000**.

**Seed lịch sử (không thuộc 9 tài liệu; `ENT-Invoice` với `source='SEED'`):**

| STT | Số HĐ | Ngày | Khách hàng | MST | Subtotal | VAT | Đã thu | Hạn TT | Trạng thái |
|---|---|---|---|---|---|---|---|---|---|
| L1 | HL-001 | 01/06/2026 | Công ty TNHH Thương mại Lộc Phát | 0303332211 | 660.000.000 | 10% | 0 | 16/07/2026 | UNPAID |

HL-001 tổng `726.000.000`, quá hạn **96 ngày** → hiện trong aging "> 90 ngày" của METRIC-FIN-05. HĐ T7/T8 chỉ seed ở mức tổng, đã thu đủ trước 20/10/2026 (trừ HL-001).

**Mapping cột → `finance.invoices`:** Số HĐ → `invoice_number` · Ngày → `issue_date` · Khách hàng/MST → `client_id` (master data `sales.clients`, khớp MST trước, tên fuzzy ≥ 0,90) · Subtotal → `subtotal_amount` · VAT % → `vat_rate` · Đã thu → `paid_amount` · Hạn TT → `due_date` · Trạng thái → `status` (`PAID`/`UNPAID`/`PARTIAL`; `OVERDUE` là trạng thái tính, không lưu).

---

### DOC-03 — Báo cáo sales T9/2026 (`SALES_REPORT`)

| Field | Ground truth | Ghi chú |
|---|---|---|
| `period` | `2026-09` | |
| `deals_won_count` / `deals_won_value` | 12 / `9.600.000.000` | Deal mới đóng T9 |
| `deals_lost_count` / `deals_lost_value` | 38 / `20.520.000.000` | 22 deal lost với lý do "giá" |
| `avg_sales_cycle_days` | `68` | Deal won T9; Q2/2026 = 54 ngày |
| `nps_score` | `+32` | Khảo sát 214 phản hồi |
| `sales_target` (T9) | `28.800.000.000` | → METRIC-FIN-01 = 25,5 / 28,8 = **88,5%** |
| `q4_revenue_recognized_to_date` | `16.500.000.000` | HĐ xuất 01–20/10/2026 (seed) |
| `revenue_by_customer[]` | 14 khách, group-by 47 HĐ DOC-02 | Bảng dưới |

**Pipeline mở tại 20/10/2026** (mọi deal mở có `expected_close_date` ∈ Q4/2026):

| Stage | Deal | Giá trị (VND) | Xác suất | Weighted |
|---|---|---|---|---|
| `PROSPECTING` | 15 | `36.000.000.000` | 0,10 | `3.600.000.000` |
| `QUALIFICATION` | 10 | `30.000.000.000` | 0,25 | `7.500.000.000` |
| `PROPOSAL` | 8 | `36.000.000.000` | 0,40 | `14.400.000.000` |
| `NEGOTIATION` | 6 | `40.500.000.000` | 0,60 | `24.300.000.000` |
| **Cộng mở** | **39** | **`142.500.000.000`** | — | **`49.800.000.000`** |

Deal `NEGOTIATION` lớn nhất: **Tập đoàn Giáo dục Hoàng Gia** (khách mới, MST `0316543210`) `12.000.000.000` — cơ hội trong câu chuyện demo.

**Doanh thu T9 theo khách:**


| # | Khách hàng | MST | Doanh thu T9 (VND, trước VAT) | Số HĐ | Tỷ trọng T9 |
|---|---|---|---|---|---|
| 1 | Công ty Cổ phần Văn phòng Phẩm | 0301112223 | `3.195.000.000` | 6 | 12,5% |
| 2 | Công ty Cổ phần Giáo dục Việt Nam | 0309876543 | `2.985.000.000` | 6 | 11,7% |
| 3 | Công ty TNHH FPT Trading | 0303334445 | `2.610.000.000` | 4 | 10,2% |
| 4 | Công ty TNHH Minh Phát | 0306667778 | `2.475.000.000` | 4 | 9,7% |
| 5 | Công ty TNHH Giải pháp Số | 0304445678 | `2.145.000.000` | 4 | 8,4% |
| 6 | Công ty TNHH Đầu tư Đại Cường | 0302228877 | `2.040.000.000` | 3 | 8,0% |
| 7 | Công ty TNHH An Khang | 0308889990 | `1.965.000.000` | 4 | 7,7% |
| 8 | Công ty Cổ phần ABC Retail | 0302223334 | `1.815.000.000` | 4 | 7,1% |
| 9 | Công ty TNHH Thương mại Lộc Phát | 0303332211 | `1.680.000.000` | 3 | 6,6% |
| 10 | Công ty Cổ phần TechVN | 0301119988 | `1.455.000.000` | 3 | 5,7% |
| 11 | Công ty Cổ phần Bút Tre VN | 0304443322 | `1.065.000.000` | 3 | 4,2% |
| 12 | Công ty TNHH TechSoft | 0305551234 | `750.000.000` | 1 | 2,9% |
| 13 | Công ty TNHH Đại Lợi | 0307778889 | `720.000.000` | 1 | 2,8% |
| 14 | Công ty Cổ phần Thương mại Quốc tế | 0305556677 | `600.000.000` | 1 | 2,4% |
| — | **Tổng** | — | **`25.500.000.000`** | **47** | 100% |

Top 5 T9 = `13.410.000.000` / `25.500.000.000` = 52,6% (tham khảo). METRIC-CUS-04 dùng rolling 12 tháng: tổng `294.000.000.000` (9 tháng 10/2025–06/2026 seed `220.500.000.000` + Q3 `73.500.000.000`), Top 5 `149.940.000.000` → **51,0%**; khách lớn nhất (Văn phòng Phẩm) `41.160.000.000` = 14,0%.

---

### DOC-04 — Hợp đồng khách hàng (`CONTRACT`, 2 PDF scan)

| Field | File 1 | File 2 |
|---|---|---|
| `contract_number` | `HD-2026-001` | `HD-2026-002` |
| `party_a_name` / `party_a_tax_code` | Công ty TNHH TM&DV ABC / `0301234567` | như File 1 |
| `party_b_name` | Công ty Cổ phần Giáo dục Việt Nam | Công ty TNHH Minh Phát |
| `party_b_tax_code` | `0309876543` | `0306667778` |
| `contract_value` | `15.000.000.000` | `9.000.000.000` |
| `product_code` | `PRD-SUP` + `PRD-CARE` | `PRD-SUP` |
| `sign_date` | 15/01/2026 | 20/03/2026 |
| `effective_date` | 01/02/2026 | 01/04/2026 |
| `expiry_date` | 31/01/2027 | **30/09/2026** (đã hết hạn, chưa gia hạn) |
| `payment_terms` | 30 ngày | 60 ngày |

HD-2026-002 hết hạn 30/09/2026 nhưng Minh Phát vẫn có HĐ T9 (HV-005, -014, -026, -036) → nguồn của rủi ro R-04 (DOC-09) và insight "hợp đồng hết hạn nhưng vẫn giao hàng". `contract_value` là trường **trọng yếu** → luôn review.

---

### DOC-05 — Biên bản họp giao ban (`MEETING_MINUTES`, 3 Word)

| File | Ngày | Tiêu đề | Chủ trì | Thành phần | Quyết định | Action item |
|---|---|---|---|---|---|---|
| 1 | 05/09/2026 | Giao ban tuần 1 T9 | Nguyễn Văn An | Trần Thị Minh, Lê Hoàng Giang, Phạm Thị Hạnh, Bùi Thu Trang | 2 | 5 |
| 2 | 12/09/2026 | Giao ban tuần 2 T9 | Nguyễn Văn An | Lê Hoàng Giang, Phạm Thị Hạnh, Đỗ Quang Huy, Hoàng Minh Tuấn | 1 | 4 |
| 3 | 19/09/2026 | Giao ban tuần 3 T9 | Nguyễn Văn An | Trần Thị Minh, Bùi Thu Trang, Đỗ Quang Huy, Vũ Đức Thắng | 2 | 6 |
| | | | | **Tổng** | **5** | **15** |

**5 quyết định (`ENT-Decision`):**

| Mã | Nội dung | Người chịu trách nhiệm | Hạn | Trạng thái 20/10 |
|---|---|---|---|---|
| QD-01 | Tuyển gấp 6 nhân viên kinh doanh khu vực Hà Nội (HiringPlan HP-2026-07) | Phạm Thị Hạnh | 30/09/2026 | Trễ — chưa xong |
| QD-02 | Siết hạn mức công nợ khách quá hạn > 60 ngày | Trần Thị Minh | 15/10/2026 | Xong đúng hạn |
| QD-03 | Gia hạn hợp đồng Minh Phát trước 30/09 | Lê Hoàng Giang | 30/09/2026 | Xong đúng hạn *(đàm phán xong, chờ ký — phụ lục chưa scan)* |
| QD-04 | Ra mắt tính năng "Đặt hàng định kỳ" ABC Order | Đỗ Quang Huy | 31/10/2026 | Chưa đến hạn |
| QD-05 | Lập kế hoạch dự phòng nhà cung cấp mực in | Bùi Thu Trang | 15/11/2026 | Chưa đến hạn |

3 quyết định đến hạn (QD-01..03), 2 xong đúng hạn → **METRIC-OPS-03 = 66,7%**.

**15 action item → `ENT-Task`:** 9 xong đúng hạn, 2 xong trễ, 4 mở quá hạn (gồm "Đăng tuyển 6 vị trí sales HN" của Phạm Thị Hạnh, trễ 20 ngày). Người phụ trách đều có trong DOC-06 (XD-03).

---

### DOC-06 — Danh sách nhân sự (`EMPLOYEE_LIST`, Excel 150 dòng)

Cột: Mã NV · Họ tên · Chức danh · Phòng ban · Ngày vào · Ngày nghỉ · Trạng thái (`ACTIVE`/`ON_LEAVE`/`TERMINATED`) · Lương (VND). **Lương = "rất nhạy cảm"** (02, 05 §dữ liệu nhạy cảm): chỉ CEO và HR_MANAGER xem; REVIEWER chỉ thấy trong ngữ cảnh review DOC-06 được giao; **không bao giờ gửi LLM** (AI chỉ nhận tổng hợp theo phòng ban).

| Phòng ban | ACTIVE | Quỹ lương T9 (VND) | Bình quân |
|---|---|---|---|
| BOD | 6 | `305.000.000` | ~50,8 tr |
| FIN | 14 | `294.000.000` | 21,0 tr |
| SAL | 42 | `777.000.000` | 18,5 tr |
| LOG | 38 | `513.000.000` | 13,5 tr |
| SVC | 24 | `408.000.000` | 17,0 tr |
| PRD | 18 | `504.000.000` | 28,0 tr |
| HRA | 8 | `124.000.000` | 15,5 tr |
| **Tổng** | **150** | **`2.925.000.000`** | **19,5 tr** |

Quỹ lương Q3 = 2.925.000.000 × 3 = `8.775.000.000` ⊂ `operating_expenses` DOC-01 (XD-05). Khoảng lương 9–85 triệu.

**Seed lịch sử nhân sự:** 20 nhân sự `TERMINATED` trong 12 tháng (10/2025–09/2026), headcount bình quân 12 tháng = 150 → METRIC-HR-02 = **13,3%**. 13 nhân sự quá tải (> 8 task mở hoặc ≥ 3 task trễ) → METRIC-HR-03 = **8,7%**.

**Kế hoạch tuyển dụng (`ENT-HiringPlan`):**

| Mã | Phòng ban | Số lượng | Hạn tuyển | Trạng thái | Ngày trễ tại 20/10 |
|---|---|---|---|---|---|
| HP-2026-05 | PRD | 2 (Backend dev) | 31/10/2026 | `APPROVED` (CFO duyệt) | — |
| HP-2026-06 | SVC | 3 (Kỹ thuật viên) | 30/09/2026 | `IN_PROGRESS` | 20 |
| HP-2026-07 | SAL | 6 (Sales HN) | 15/09/2026 | `IN_PROGRESS` | **35** → `EVT-hr.hiring_plan_delayed` |

---

### DOC-07 — Kế hoạch KPI/OKR Q4/2026 (`KPI_OKR`)

| Objective | Key result | Mục tiêu | Owner | Trụ |
|---|---|---|---|---|
| O1 Tăng trưởng doanh thu bền vững | KR1.1 Doanh thu Q4 | `81.000.000.000` (27 tỷ/tháng) | Lê Hoàng Giang | C, F |
| | KR1.2 Pipeline coverage | ≥ 3,0x | Lê Hoàng Giang | C |
| O2 Giữ dòng tiền an toàn | KR2.1 Cash runway | ≥ 9 tháng | Trần Thị Minh | F |
| | KR2.2 Công nợ quá hạn | ≤ 10% | Trần Thị Minh | F |
| O3 Đủ người, vận hành đúng hạn | KR3.1 Hoàn thành HP-2026-06/07 | 9 người trước 30/11 | Phạm Thị Hạnh | O |
| | KR3.2 Task đúng hạn | ≥ 85% | Hoàng Minh Tuấn | O |
| O4 ABC Order được dùng thật | KR4.1 MAU | ≥ 75% | Đỗ Quang Huy | U |
| | KR4.2 Churn | ≤ 1,5%/tháng | Đỗ Quang Huy | U |
| O5 Kiểm soát rủi ro trọng yếu | KR5.1 Rủi ro high chưa có chủ | 0 | Bùi Thu Trang | S |
| | KR5.2 Mitigation quá hạn | ≤ 10% | Bùi Thu Trang | S |

**KPI** (`ENT-KPI`, mỗi dòng có `metric_code` tồn tại trong 00 §4.2 — XD-04): METRIC-FIN-01, FIN-03, FIN-05, OPS-01, HR-04, CUS-01, CUS-02, PRD-01, PRD-02, RSK-02. Mục tiêu doanh thu Q4 `81.000.000.000` là mẫu số METRIC-CUS-01. **Seed Q3 (đã đóng):** 15 KR với tiến độ 100, 90, 60, 85, 70, 100, 50, 80, 75, 90, 60, 70, 80, 65, 88 (%) → METRIC-RSK-06 = **77,5%**.

---

### DOC-08 — Báo cáo chỉ số sản phẩm T9/2026 (`PRODUCT_REPORT`)

| Field | Ground truth | Ghi chú |
|---|---|---|
| `product_code` | `PRD-ORDER` (ABC Order) | Kèm phần tóm tắt ABC Care |
| `period` | `2026-09` | |
| `accounts_start` / `new` / `churned` / `end` | 1.950 / 63 / 47 / 1.966 | 1.950 + 63 − 47 = 1.966 |
| `monthly_active_accounts` | 1.392 | MAU = 70,8% |
| `churn_pct` | 2,41% | T6–T8: 1,5 · 1,4 · 1,6 (BQ 1,5) → tăng **60,7%** > 50% và ≥ 2% → `EVT-product.metric_anomaly` (BR churn anomaly) |
| `cohort_new_aug` / `retained_30d` | 60 / 41 | Retention 30 ngày 68,3% |
| `roadmap_due` / `roadmap_on_time` | 12 / 8 | 66,7%; 4 trễ do thiếu 2 backend dev (HP-2026-05) |
| `releases[]` | v3.4 "Báo giá nhanh" (04/09), v3.4.1 sửa lỗi thanh toán (12/09), v3.5 "Duyệt đơn nhiều cấp" (26/09) | 3 `ENT-Release`, `EVT-product.feature_released` |
| `top_churn_reason` | "Lỗi đồng bộ tồn kho", "Giá thuê bao" | Văn bản tự do — AI tóm tắt, không suy số |
| `abc_care_contracts_active` | 412 | ABC Care, tham khảo |

`ENT-ProductMetric` là append-only (05): mỗi lần duyệt tạo snapshot mới, không ghi đè.

---

### DOC-09 — Sổ rủi ro Q3/2026 (`RISK_REGISTER`, Excel 11 dòng)

Score = Likelihood × Impact (1–5); level theo 03 BR-RSK-02: **critical 16–25**, high 10–15, medium 5–9, low 1–4.

| Mã | Rủi ro | Liên kết entity | L | I | Score | Level | Owner | Mở từ | Mitigation |
|---|---|---|---|---|---|---|---|---|---|
| R-01 | Thiếu hụt dòng tiền Q4 do công nợ tăng | finance.invoices (HL-001), cash | 4 | 5 | **20** | **critical** | Trần Thị Minh | 10/09/2026 | 2 (1 quá hạn) |
| R-02 | Mất khách lớn Văn phòng Phẩm (14% doanh thu) | sales.clients | 4 | 3 | 12 | high | Lê Hoàng Giang | 01/09/2026 | 2 |
| R-03 | Nhà cung cấp mực in duy nhất | product PRD-SUP | 3 | 5 | 15 | high | Bùi Thu Trang | 01/08/2026 | **0** (> 30 ngày) |
| R-04 | Giao hàng khi hợp đồng HD-2026-002 hết hạn | sales.contracts | 4 | 4 | 16 | **critical** | Lê Hoàng Giang | 01/10/2026 | 1 |
| R-05 | Churn ABC Order tăng | product.product_metrics | 4 | 4 | 16 | **critical** | Đỗ Quang Huy | 05/10/2026 | 2 |
| R-06 | Rò rỉ dữ liệu khách hàng qua email cá nhân | platform | 3 | 5 | 15 | high | **—** | 15/09/2026 | 1 |
| R-07 | Biến động tỷ giá nhập máy in | finance.expenses | 2 | 5 | 10 | medium | Trần Thị Minh | 01/07/2026 | 2 (1 quá hạn) |
| R-08 | Quá tải kho Q4 | hr.departments LOG | 3 | 3 | 9 | medium | Hoàng Minh Tuấn | 01/09/2026 | 1 |
| R-09 | Nghỉ việc nhóm kỹ thuật SVC | hr.departments SVC | 3 | 3 | 9 | medium | Phạm Thị Hạnh | 15/08/2026 | 1 |
| R-10 | Chậm phê duyệt hóa đơn điện tử | finance.invoices | 2 | 4 | 8 | medium | Trần Thị Minh | 01/09/2026 | 1 (quá hạn) |
| R-11 | Thay đổi quy định NĐ 13 về dữ liệu cá nhân | platform | 2 | 3 | 6 | medium | Bùi Thu Trang | 01/07/2026 | 1 |

**R-12 (không có trong file — tự sinh từ event, `source='EVENT'`):** "Chậm tuyển 6 sales HN ảnh hưởng doanh thu Q4", liên kết HP-2026-07, L 3 × I 4 = **12 high**, owner **—** (chờ phân công), mở 20/10/2026, 0 mitigation (chưa tính vào RSK-03 vì < 30 ngày). Tổng **14 mitigation đang mở, 3 quá hạn**.

---

## 4. Quy tắc nhất quán liên tài liệu (XD)

| Mã | Quy tắc | Bên A | Bên B | Ground truth | Kết quả |
|---|---|---|---|---|---|
| XD-01 | Doanh thu tháng M trong BCTC khớp Σ subtotal hóa đơn tháng M, dung sai ±0,5% (DEC-030) | DOC-01 `revenue_by_month[2026-09]` | DOC-02 Σ subtotal | 25.500.000.000 vs 25.500.000.000 (0,0%) | MATCH |
| XD-02 | Tên + MST khách khớp giữa hóa đơn, báo cáo sales, hợp đồng (MST trước, tên fuzzy ≥ 0,90) | DOC-02 (14 khách) | DOC-03, DOC-04 | 14/14; 2 khách DOC-04 có trong DOC-02 | PASS |
| XD-03 | Người trong biên bản / OKR / sổ rủi ro tồn tại trong danh sách nhân sự | DOC-05, DOC-07, DOC-09 | DOC-06 (150) | 10 tên riêng đều có | PASS |
| XD-04 | `metric_code` trong KPI tồn tại trong registry | DOC-07 | 00 §4.2 (31 metric) | 10/10 | PASS |
| XD-05 | Quỹ lương × 3 ⊂ chi phí vận hành quý | DOC-06 | DOC-01 | 8.775.000.000 ≤ 10.200.000.000 | PASS |
| XD-06 | Doanh thu theo sản phẩm khớp doanh thu tháng | §1 bảng sản phẩm | DOC-01 T9 | 19,125 + 4,08 + 2,295 = 25,5 tỷ | PASS |
| XD-07 | `linked_entity` của rủi ro trỏ tới entity tồn tại | DOC-09 | DOC-02/04/06/08 | 11/11 | PASS |
| XD-08 | Sản phẩm trong báo cáo sản phẩm / hợp đồng có trong danh mục | DOC-04, DOC-08 | `product.products` | PRD-SUP, PRD-CARE, PRD-ORDER | PASS |

Bộ "tài liệu lệch" để demo MISMATCH: bản sao DOC-02 có HV-047 subtotal `1.020.000.000` thay vì `510.000.000` → Σ lệch +2,0% → XD-01 `MISMATCH` (vượt 0,5%) → review bắt buộc.

---

## 5. Master data và seed nền

| Nhóm | Số lượng | Ghi chú |
|---|---|---|
| `sales.clients` | 14 khách DOC-02 + 1 prospect (Hoàng Gia) + 25 khách lịch sử | Dedupe theo MST |
| `sales.deals` | 39 mở + 12 won T9 + 38 lost T9 + 140 lịch sử | |
| `hr.employees` | 150 ACTIVE + 20 TERMINATED (12 tháng) | Tên giả định |
| `execution.tasks` | 105 seed + 15 từ DOC-05; 243 task mở tổng cộng | |
| `execution.projects` | 6 (2 trễ: "Mở kho Bình Dương", "Tích hợp ABC Order – ERP") | |
| `product.products` / `features` / `roadmap_items` | 3 / 28 / 12 (T9 đến hạn) | |
| `risk.risks` | 11 (DOC-09) + 1 tự sinh (R-12) | |
| `finance.*` lịch sử | Doanh thu 12 tháng theo khách; HĐ T7/T8 tổng hợp; HL-001; ngân sách Q3; forecast 3 kịch bản Q4 | `source='SEED'`, drill-down P01 dừng ở bản ghi seed có nhãn "Dữ liệu seed lịch sử" |

---

## 6. Seed 31 metric tại `DEMO_REFERENCE_DATE` = 20/10/2026

Trend là giá trị cuối tháng T4→T9/2026 (6 kỳ); kỳ hiện tại = T9 (hoặc Q3 với metric quý). Ngưỡng là **biến cấu hình** (`platform.metrics.threshold_*`), giá trị mặc định ở cột "Ngưỡng".

| Metric | Tên | Công thức (theo 03 §2) | Đơn vị | Ngưỡng mặc định (03) | Trend T4→T9/2026 | Hiện tại | Nguồn seed | Trạng thái | Alert |
|---|---|---|---|---|---|---|---|---|---|
| METRIC-FIN-01 | Doanh thu vs kế hoạch | DT kỳ / SalesTarget kỳ × 100 | % | W < 90 · C < 80 | 96,2 · 94 · 93,1 · 91,5 · 90,4 · 88,5 | **88,5** | 25,5 tỷ / 28,8 tỷ (DOC-01, DOC-03) | Warning | ALERT-FIN-01 Warning |
| METRIC-FIN-02 | Biên LN gộp | (DT − giá vốn `cogs`) / DT × 100 | % | W giảm > 3 đ% so Δ3k · C giảm > 5 đ% | 19,6 · 19,2 · 19 · 18,8 · 18,6 · 18,4 | **18,4** | 13,5 / 73,5 tỷ (DOC-01); giảm 0,4 đ% so Δ3k | OK | — |
| METRIC-FIN-03 | Cash runway | số dư cuối kỳ / burn tháng (BR-FIN-01/02) | tháng | W < 12 · C < 6 | 11,8 · 11 · 10,4 · 9,6 · 8,7 · 8 | **8,0** | 20,4 tỷ / 2,55 tỷ (DOC-01) | Warning | ALERT-FIN-03 Warning |
| METRIC-FIN-04 | DSO | phải thu cuối kỳ / DT kỳ × số ngày | ngày | W tăng > 15% so Δ3k · C tăng > 30% | 41 · 42,5 · 43 · 44,2 · 46,1 · 47,8 | **47,8** | 39,0 / 73,5 tỷ × 90; +7,6% so Δ3k | OK | — |
| METRIC-FIN-05 | Công nợ quá hạn | phải thu quá hạn / tổng phải thu × 100 | % | W > 15 · C > 25 | 8,5 · 9,8 · 11,2 · 14 · 19,5 · 23,9 | **23,9** | 3,918 / 16,377 tỷ; HL-001 quá hạn 96 ngày (aging > 90) | Warning | ALERT-FIN-05 Warning |
| METRIC-FIN-06 | Chênh lệch ngân sách | MAX theo phòng ban [(thực chi − ngân sách) / ngân sách × 100], quý | % | W > 0 · C > 10 | 2,1 · 3 · 4,2 · 6,5 · 9,8 · 14,1 | **14,1** | Phòng SAL 3.650 / 3.200 triệu (§3 DOC-01) | **Critical** | ALERT-FIN-06 Critical |
| METRIC-FIN-07 | Net burn vs dự báo | (net burn dự kiến − dự báo) / \|dự báo\| × 100 | % | W > 10 · C > 25 | -4 · 0 · 2,5 · 6 · 12 · 20 | **20** | 3,0 vs 2,5 tỷ T9 | Warning | ALERT-FIN-07 Warning |
| METRIC-OPS-01 | Task đúng hạn | task xong đúng hạn / task đến hạn × 100 | % | W < 80 · C < 65 | 84 · 82,5 · 80 · 76 · 71 · 65 | **65** | 78 / 120 (15 DOC-05 + 105 seed) | Warning | ALERT-OPS-01 Warning |
| METRIC-OPS-02 | Dự án trễ | dự án lệch tiến độ > 10 đ% / dự án đang chạy × 100 | % | W > 20 · C > 35 | 0 · 0 · 16,7 · 16,7 · 33,3 · 33,3 | **33,3** | 2 / 6 dự án (seed) | Warning | ALERT-OPS-02 Warning |
| METRIC-OPS-03 | Thực thi quyết định | task từ quyết định xong / đến hạn × 100 | % | W < 70 · C < 50 | 100 · 90 · 85 · 80 · 75 · 66,7 | **66,7** | 2 / 3 (DOC-05) | Warning | ALERT-OPS-03 Warning |
| METRIC-HR-01 | Doanh thu / nhân sự | DT 12 tháng / headcount BQ; so `HR_REVENUE_PER_HEAD_PLAN` = 2,0 tỷ | tỷ/người/năm | W thấp hơn KH > 15% · C > 25% | 2,06 · 2,04 · 2,02 · 2 · 1,98 · 1,96 | **1,96** | 294 tỷ / 150; thấp hơn KH 2% | OK | — |
| METRIC-HR-02 | Turnover năm hóa | BR-HR-01 | % | W ≥ 15 · C ≥ 20 | 11,5 · 12 · 12,4 · 12,7 · 13 · 13,3 | **13,3** | 20 / 150 | OK | — |
| METRIC-HR-03 | Nhân sự quá tải | NV workload > 110% 2 tuần liên tiếp / NV active × 100 | % | W > 10 · C > 20 | 4,7 · 5,3 · 6 · 6,7 · 7,3 · 8,7 | **8,7** | 13 / 150 | OK | — |
| METRIC-HR-04 | Kế hoạch tuyển dụng trễ | đếm HiringPlan quá `target_date` chưa đủ người | kế hoạch | W ≥ 1 trễ 1–30 ngày · C ≥ 1 trễ > 30 ngày | 0 · 0 · 0 · 0 · 0 · 1 | **1** | HP-2026-07 trễ 35 ngày | **Critical** | ALERT-HR-04 Critical |
| METRIC-CUS-01 | Pipeline coverage | Σ deal_value mở đóng trong quý / mục tiêu quý (BR-SAL-04); kèm coverage có trọng số | x | W < 3,5 · C < 3,0 | 3,4 · 3,1 · 2,9 · 2,6 · 2,2 · 1,8 | **1,8** | 142,5 / 81,0 tỷ = 1,76x; trọng số 49,8 / 81,0 = 0,61x | **Critical** | ALERT-CUS-01 Critical |
| METRIC-CUS-02 | Win rate | won / (won + lost) × 100 | % | W giảm > 10 đ% so Δ3k · C > 20 đ% | 29 · 28 · 27,5 · 26 · 25,5 · 24 | **24** | 12 / 50 (DOC-03); giảm 2,3 đ% | OK | — |
| METRIC-CUS-03 | NRR | DT kỳ của nhóm khách kỳ gốc / DT kỳ gốc × 100 | % | W < 100 · C < 90 | 101 · 102,2 · 103 · 103,5 · 104 · 104,5 | **104,5** | 69,9 / 66,9 tỷ (Q3/2026 vs Q3/2025) | OK | — |
| METRIC-CUS-04 | Tập trung doanh thu top 5 | DT top 5 khách 12 tháng / tổng × 100 | % | W > 50 · C > 65 | 46 · 47,2 · 48,5 · 49,4 · 50,3 · 51 | **51** | 149,94 / 294 tỷ | Warning | ALERT-CUS-04 Warning |
| METRIC-CUS-05 | NPS | % promoter − % detractor | điểm | W < 30 · C < 0 | 28 · 30 · 31 · 33 · 32 · 32 | **32** | DOC-03, 214 phản hồi | OK | — |
| METRIC-CUS-06 | Chu kỳ bán TB | AVG(closed_at − created_at) deal won | ngày | W tăng > 20% so Δ3k · C > 40% | 52 · 53 · 54 · 58 · 63 · 68 | **68** | DOC-03; +16,6% so Δ3k | OK | — |
| METRIC-PRD-01 | Adoption (MAU) | MAU sản phẩm launched (+ adoption %) | người dùng | W MAU giảm > 10% so Δ3k · C > 20% | 1.540 · 1.560 · 1.575 · 1.560 · 1.548 · 1.392 | **1.392** | DOC-08 (adoption 70,8%); giảm 10,8% so Δ3k | Warning | ALERT-PRD-01 Warning |
| METRIC-PRD-02 | Churn | `churn_rate_pct` (sản phẩm xấu nhất) | %/tháng | W tăng > 25% tương đối & ≥ 2% · C > 50% & ≥ 2% (BR-PRD-01) | 1,4 · 1,5 · 1,5 · 1,4 · 1,6 · 2,41 | **2,41** | 47 / 1.950 (DOC-08); +60,7% so Δ3k | **Critical** | ALERT-PRD-02 Critical |
| METRIC-PRD-03 | Retention 30 ngày | `retention_30d_pct` | % | W < 40 · C < 25 | 72 · 71 · 70,5 · 70 · 69 · 68,3 | **68,3** | 41 / 60 (DOC-08) | OK | — |
| METRIC-PRD-04 | Roadmap đúng tiến độ | RoadmapItem không trễ / RoadmapItem của quý × 100 | % | W < 70 · C < 50 | 90 · 88 · 85 · 80 · 75 · 66,7 | **66,7** | 8 / 12 (DOC-08) | Warning | ALERT-PRD-04 Warning |
| METRIC-PRD-05 | Tính năng release trong kỳ | số feature released; attainment = released / planned × 100 | tính năng (+ %) | W attainment < 70 · C < 40 | 2 · 3 · 2 · 4 · 2 · 3 | **3 (75%)** | 3 release / 4 kế hoạch T9 (DOC-08) | OK | — |
| METRIC-RSK-01 | Rủi ro high/critical đang mở | đếm level ∈ {high, critical}, chưa closed/accepted | rủi ro | W ≥ 1 high · C ≥ 1 critical | 3 · 4 · 5 · 6 · 7 · 8 | **8** | R-01..07, R-12 (3 critical: R-01, R-04, R-05) | **Critical** | ALERT-RSK-01 Critical |
| METRIC-RSK-02 | Rủi ro high chưa có chủ | đếm level ≥ high, owner null | rủi ro | W ≥ 1 medium chưa chủ > 7 ngày · C ≥ 1 | 0 · 0 · 0 · 1 · 1 · 2 | **2** | R-06, R-12 | **Critical** | ALERT-RSK-02 Critical |
| METRIC-RSK-03 | Rủi ro high > 30 ngày không mitigation | level ≥ high, mở > 30 ngày, không có mitigation in_progress | rủi ro | W ≥ 1 · C ≥ 1 rủi ro critical | 0 · 0 · 0 · 0 · 1 · 1 | **1** | R-03 (high) | Warning | ALERT-RSK-03 Warning |
| METRIC-RSK-04 | Điểm rủi ro tổng hợp | Σ score rủi ro mở / số rủi ro mở (thang 1–25) | điểm | W ≥ 8 · C ≥ 12 | 9,5 · 10,1 · 10,6 · 11,2 · 11,8 · 12,3 | **12,3** | 148 / 12 | **Critical** | ALERT-RSK-04 Critical |
| METRIC-RSK-05 | Biện pháp quá hạn | đếm mitigation planned/in_progress quá hạn | biện pháp | W ≥ 1 · C ≥ 5 hoặc ≥ 1 thuộc rủi ro critical | 1 · 1 · 1 · 2 · 2 · 3 | **3** | 3 / 14 (R-01, R-07, R-10); 1 thuộc R-01 critical | **Critical** | ALERT-RSK-05 Critical |
| METRIC-RSK-06 | Strategy execution index | Σ weight × on_track / Σ weight × 100 (Objective Q3) | % | W < 70 · C < 50 | — · — · — · — · — · 66,7 | **66,7** | 4 / 6 Objective Q3 on track (weight bằng nhau) | Warning | ALERT-RSK-06 Warning |

### 6.1. Tổng hợp trạng thái

| Trụ | OK | Warning | Critical | Trạng thái trụ (03 §4: critical nếu có ≥ 1 metric critical) |
|---|---|---|---|---|
| PIL-F | 2 | 4 | 1 | **critical** (FIN-06) |
| PIL-O | 3 | 3 | 1 | **critical** (HR-04) |
| PIL-C | 4 | 1 | 1 | **critical** (CUS-01) |
| PIL-U | 2 | 2 | 1 | **critical** (PRD-02) |
| PIL-S | 0 | 2 | 4 | **critical** (RSK-01/02/04/05) |
| **Tổng 31** | **11** | **12** | **8** | |

Mỗi trụ có ≥ 1 Warning; trụ S có Critical. 20 alert đang mở (12 Warning + 8 Critical). Briefing CEO lấy tối đa 3 ngoại lệ ưu tiên: ALERT-RSK-02 (R-12 chờ phân công), ALERT-HR-04 (HP-2026-07), ALERT-CUS-01.

---

## 7. Seed sự kiện (`platform.outbox_events`)

Seed phát qua outbox như luồng thật (không ghi thẳng vào bảng consumer), để demo được chuỗi event → rủi ro → insight. Mỗi event có `event_id` cố định (UUID v5 từ mã dưới) để seed chạy lại vẫn idempotent.

| # | Thời điểm | Event | Payload chính | Consumer → kết quả |
|---|---|---|---|---|
| E1 | 30/09/2026 | `EVT-finance.budget_exceeded` | dept `SAL`, quý 2026-Q3, utilization 114,1% (6 phòng ban > 100% đều phát event; chỉ SAL > 10% được map sang rủi ro theo `RISK_EVENT_SCORING`, OQ-01) | risk: cập nhật R-02 · ai_core: insight "Chi phí kinh doanh vượt 14%" |
| E2 | 01/10/2026 | `EVT-finance.burn_over_forecast` | T9 burn 3,0 tỷ vs dự báo 2,5 tỷ (+20%) | risk: tăng L của R-01 (3→4) → `EVT-risk.risk_level_changed` (high → critical) |
| E3 | 05/10/2026 | `EVT-product.metric_anomaly` | PRD-ORDER churn 2,41% vs BQ 1,5% (+60,7%) | risk: tạo R-05 · ai_core: insight trụ U |
| E4 | 06/10/2026 | `EVT-risk.risk_level_changed` | R-01 high → critical | platform: ALERT-RSK-01 cập nhật · ai_core: đưa vào Briefing |
| E5 | 15/10/2026 | `EVT-sales.deal_closed_lost` | deal "Trang bị VP Tân Phú" 0,8 tỷ, lý do giá | risk: < `RISK_LOST_DEAL_MIN_VALUE` (1 tỷ), chỉ log |
| E6 | 20/10/2026 07:00 | `EVT-hr.hiring_plan_delayed` | HP-2026-07, trễ 35 ngày, 6 vị trí SAL | risk: **tự sinh R-12** (`source='EVENT'`, owner null, high) → `EVT-risk.risk_identified` |
| E7 | 20/10/2026 07:01 | `EVT-risk.risk_identified` | R-12, score 12 | platform: ALERT-RSK-02 lên Critical (2 rủi ro high chưa có chủ) · ai_core: insight liên miền "Chậm tuyển → rủi ro hụt KR1.1 doanh thu Q4" |
| E8 | 20/10/2026 07:05 | `EVT-execution.task_overdue` | 4 task DOC-05 quá hạn | platform: METRIC-OPS-01 tính lại |

Kiểm thử idempotency: chạy seed E6 hai lần → chỉ 1 R-12 (`processed_events`).

---

## 8. Kịch bản demo 20 phút (01 §11)

| Phút | Vai | Bước | Dữ liệu dùng | Kết quả mong đợi |
|---|---|---|---|---|
| 0–2 | CEO | F1: mở SCR-01 | §6.1 | "3 việc cần anh, 1 rủi ro mới"; 5 trụ đỏ (xem §6.1, OQ-07) |
| 2–5 | CEO | Bấm thẻ METRIC-FIN-01 (88,5%) → Panel AI → drill-down | DOC-01, DOC-02 | Nguyên nhân có source chip; ≤ 3 click tới trang 4 PDF DOC-01 và dòng HV-xxx |
| 5–7 | CEO | Hỏi AI "Rủi ro tuyển dụng chậm ảnh hưởng thế nào đến dự báo tài chính?" rồi "Runway nếu tháng sau không có doanh thu mới?" | R-12, HP-2026-07, forecast | Trả lời có `sources`; runway với doanh thu = 0 tính từ tool Finance, không bịa số |
| 7–9 | CEO | Chọn phương án → Action card L2 → xác nhận | QD-01 | 3 task tạo, toast hoàn tác 10 giây, quyết định mới ghi log |
| 9–11 | CFO → Risk Manager | Chuyển vai; SCR-21 what-if R-01 | R-01, cash 20,4 tỷ | Tác động lên runway/nhân sự/sản phẩm; gán owner R-12 và R-06 → METRIC-RSK-02 = 0, ALERT-RSK-02 đóng |
| 11–16 | CEO | UC-07: thả 9 tài liệu | DOC-01..09 | Phân loại đúng 9/9; trang 7 DOC-01 confidence Thấp |
| 16–18 | Reviewer | F2: duyệt DOC-02 trên SCR-10 | DOC-02 | Duyệt ≤ 60 giây; XD-01 MATCH; ghi vào `finance.invoices` qua Action Registry |
| 18–20 | CEO | Quay lại SCR-01 | lineage | Metric cập nhật, insight mới, lineage tới tài liệu vừa duyệt |

**Dự phòng:** nếu provider LLM lỗi → `MODEL_GATEWAY_MODE=fixture` trả kết quả ground truth ở §3; dashboard vẫn chạy (P08).

---

## 9. Kiểm tra số học (script, chạy lại trước khi seed)

| # | Kiểm tra | Phép tính | Kết quả |
|---|---|---|---|
| K1 | Σ subtotal 47 HĐ | cộng 47 dòng | 25.500.000.000 = DOC-01 T9 ✓ |
| K2 | Σ VAT | Σ(subtotal × VAT%) theo dòng | 2.436.000.000 ✓ |
| K3 | Σ thanh toán | K1 + K2 | 27.936.000.000 ✓ |
| K4 | PAID ⇒ đã thu = tổng | 22 HĐ | 0 lệch ✓ |
| K5 | Σ doanh thu theo khách | 14 khách | 25.500.000.000 / 47 HĐ ✓ |
| K6 | Doanh thu Q3 | 23,4 + 24,6 + 25,5 | 73,5 tỷ ✓ |
| K7 | LN | 73,5 − 60 = 13,5; 13,5 − 10,2 = 3,3; × 0,8 = 2,64 tỷ | ✓ |
| K8 | Headcount | 6 + 14 + 42 + 38 + 24 + 18 + 8 | 150 ✓ |
| K9 | Quỹ lương | Σ 7 phòng ban | 2.925.000.000; × 3 = 8.775.000.000 ✓ |
| K10 | Ngân sách | Σ 7 phòng ban | 9.450 / 10.200 triệu, +7,9% ✓ |
| K11 | Phải thu 30/09 | 27.936 + 726 + 10.338 (triệu) | 39.000 triệu; DSO 47,8 ✓ |
| K12 | Phải thu 20/10 | còn nợ 25 HĐ T9 15.651.300.000 + HL-001 726.000.000 | 16.377.300.000 ✓ |
| K13 | Quá hạn 20/10 | 5 HĐ 3.192.000.000 + HL-001 726.000.000 | 3.918.000.000 → 23,9% ✓ |
| K14 | Runway | 20,4 / ((2,1 + 2,55 + 3,0) / 3) | 8,0 tháng ✓ |
| K15 | Pipeline | 142,5 / 81 (trọng số: 3,6 + 7,5 + 14,4 + 24,3 = 49,8 / 81) | 1,76x → 1,8x; trọng số 0,61x ✓ |
| K16 | NRR | 69,9 / 66,9; 69,9 + 3,6 (khách mới) = 73,5 | 104,5% ✓ |
| K17 | Doanh thu theo sản phẩm | 19,125 + 4,08 + 2,295 | 25,5 tỷ ✓ |
| K18 | Tài khoản ABC Order | 1.950 + 63 − 47 | 1.966; MAU 70,8%; churn 2,41% ✓ |
| K19 | Rủi ro | 12 rủi ro, score = L × I, Σ 148 / 12 | index 12,3; 8 high+; 3 critical ✓ |
| K20 | Mitigation | 14 mở, 3 quá hạn (1 thuộc R-01 critical) | METRIC-RSK-05 = 3 → Critical ✓ |
| K21 | Trạng thái 31 metric | đánh giá theo ngưỡng 03 §2 | 11 OK · 12 W · 8 C, khớp cột "Trạng thái" ✓ |

---

## 10. Open questions

| # | Câu hỏi | Đề xuất | Ảnh hưởng |
|---|---|---|---|
| OQ-01 | Đã đối chiếu với 03 v2.0.0. Còn mở: 03 BR-FIN-05 phát `budget_exceeded` ở mọi phòng ban > 100%, nhưng ánh xạ event → rủi ro (`RISK_EVENT_SCORING`) chưa có ngưỡng; demo giả định chỉ chênh > 10% mới sinh/cập nhật rủi ro | Bổ sung ngưỡng vào 03 BR-RSK-03 | 03, 08 |
| OQ-02 | Tên env mật khẩu đổi từ v1 (`DEMO_SALES_PASSWORD`, `DEMO_HR_PASSWORD`) sang theo mã role | Đổi theo mã role, cập nhật `.env.example` ở T-014 | 07, `.env.example` |
| OQ-03 | NRR cần doanh thu Q3/2025 theo khách (66,9 tỷ) — chỉ có ở seed | Gắn nhãn "Dữ liệu seed lịch sử" (P01) | 03, 05 |
| OQ-04 | METRIC-RSK-06 dùng tiến độ KR Q3 (đã đóng) trong khi DOC-07 là Q4 | Seed Q3 riêng; từ T11 tính theo Q4 | 03 |
| OQ-05 | Chưa liệt kê đủ 150 nhân viên, 28 feature, 140 deal lịch sử | Sinh bằng script seed có seed ngẫu nhiên cố định, giữ các tổng ở §9 | T-510 |
| OQ-06 | R-12 sinh từ event; nếu demo chạy lại trong ngày, thời điểm E6–E8 có cố định 20/10 07:00 không | Cố định theo `DEMO_REFERENCE_DATE` | T-510 |
| OQ-07 | Với ngưỡng mặc định của 03 (vd CUS-01 C < 3,0x, RSK-04 C ≥ 12) cả 5 trụ đều critical — CEO thấy "toàn đỏ", giảm hiệu quả P07 | Human xem lại ngưỡng CUS-01/RSK-04 ở 03, hoặc chấp nhận cho demo | 03, 08 §6 |

---

## 11. Version

- **Version:** 2.0.0
- **Last updated:** 2026-10-19
- **Applies to:** Aureon v2
- **Maintainer:** @CyEyes
- **Change:** Viết lại theo DEC-136 (ABC ~150 NV, 9 tài liệu, 31 metric, 10 tài khoản, seed sự kiện); v1.0.0 lưu ở nhánh `v1`.

