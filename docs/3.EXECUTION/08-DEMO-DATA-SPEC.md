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
| `budget_opex` | `9.600.000.000` | Trang 9, chi tiết theo phòng ban ở bảng dưới |
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
| SAL | 3.350 | 3.650 | **+9,0%** → `EVT-finance.budget_exceeded` |
| LOG | 1.850 | 1.980 | +7,0% |
| SVC | 1.200 | 1.270 | +5,8% |
| PRD | 800 | 850 | +6,2% |
| HRA | 400 | 400 | 0,0% |
| **Tổng** | **9.600** | **10.200** | **+6,3%** |

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
| `PROSPECTING` | 15 | `54.000.000.000` | 0,10 | `5.400.000.000` |
| `QUALIFICATION` | 10 | `52.500.000.000` | 0,25 | `13.125.000.000` |
| `PROPOSAL` | 8 | `60.000.000.000` | 0,40 | `24.000.000.000` |
| `NEGOTIATION` | 6 | `69.000.000.000` | 0,60 | `41.400.000.000` |
| **Cộng mở** | **39** | **`235.500.000.000`** | — | **`83.925.000.000`** |

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

Top 5 T9 = `13.410.000.000` / `25.500.000.000` = 52,6% (tham khảo). METRIC-CUS-04 dùng rolling 12 tháng: tổng `294.000.000.000` (9 tháng 10/2025–06/2026 seed `220.500.000.000` + Q3 `73.500.000.000`), Top 5 `146.700.000.000` → **49,9%**; khách lớn nhất (Văn phòng Phẩm) `41.160.000.000` = 14,0%.

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
| `accounts_start` / `new` / `churned` / `end` | 1.950 / 63 / 35 / 1.978 | 1.950 + 63 − 35 = 1.978 |
| `monthly_active_accounts` | 1.430 | MAU = 72,3% |
| `churn_pct` | 1,79% | T6–T8: 1,5 · 1,4 · 1,6 (BQ 1,5) → tăng 19,7% (< 25%) và < sàn 2% → **không** bất thường (BR-PRD-01), không phát `EVT-product.metric_anomaly` |
| `cohort_new_aug` / `retained_30d` | 60 / 41 | Retention 30 ngày 68,3% |
| `roadmap_due` / `roadmap_on_time` | 12 / 9 | 75,0%; 3 trễ do thiếu 2 backend dev (HP-2026-05) |
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

**R-12 (không có trong file — tự sinh từ event, `risk_source='event'`, `status='proposed'` — DEC-148, DEC-154):** "Chậm tuyển 6 sales HN ảnh hưởng doanh thu Q4", liên kết HP-2026-07, L 3 × I 4 = **12 high**, owner **—** (chờ phân công), đề xuất 20/10/2026, 0 mitigation; **không** tính vào METRIC-RSK-01..05 cho tới khi owner xác nhận (§10.2).

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
| `execution.tasks` | 105 seed + 15 từ DOC-05 + 15 Initiative (§10.1); 243 task mở trước v2.1 (+13 chưa `done`) | `task_source` (DEC-154) |
| `execution.initiatives` / `milestones` | 5 / 13 (§10.1) | DEC-147 |
| `finance.cash_flow_forecasts` / `_lines` | 3 / 39 (§10.4) | DEC-148 |
| `platform.approval_rules` / `approval_requests` / `reports` | 4 / 8 / 5 (§10.5–12.6) | DEC-153 |
| `execution.projects` | 6 (2 trễ: "Mở kho Bình Dương", "Tích hợp ABC Order – ERP") | |
| `product.products` / `features` / `roadmap_items` | 3 / 28 / 12 (T9 đến hạn) | |
| `risk.risks` | 11 (DOC-09) + 3 `proposed` (R-12 event, R-13 ai, R-14 document — §10.2) | 13 danh mục DEC-148 |
| `finance.*` lịch sử | Doanh thu 12 tháng theo khách; HĐ T7/T8 tổng hợp; HL-001; ngân sách Q3; forecast 3 kịch bản Q4 | C19 `source='SEED'`, drill-down P01 dừng ở bản ghi seed có nhãn "Dữ liệu seed lịch sử" |

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
| METRIC-FIN-06 | Chênh lệch ngân sách | MAX theo phòng ban [(thực chi − ngân sách) / ngân sách × 100], quý | % | W > 0 · C > 10 | 2,1 · 3 · 4,2 · 6,5 · 7,8 · 9,0 | **9,0** | Phòng SAL 3.650 / 3.350 triệu (§3 DOC-01) | Warning | ALERT-FIN-06 Warning |
| METRIC-FIN-07 | Net burn vs dự báo | (net burn dự kiến − dự báo) / \|dự báo\| × 100 | % | W > 10 · C > 25 | -4 · 0 · 2,5 · 6 · 12 · 20 | **20** | 3,0 vs 2,5 tỷ T9 | Warning | ALERT-FIN-07 Warning |
| METRIC-OPS-01 | Task đúng hạn | task xong đúng hạn / task đến hạn × 100 | % | W < 80 · C < 65 | 84 · 82,5 · 80 · 76 · 71 · 65 | **65** | 78 / 120 (15 DOC-05 + 105 seed) | Warning | ALERT-OPS-01 Warning |
| METRIC-OPS-02 | Dự án trễ | dự án lệch tiến độ > 10 đ% / dự án đang chạy × 100 | % | W > 20 · C > 35 | 0 · 0 · 16,7 · 16,7 · 33,3 · 33,3 | **33,3** | 2 / 6 dự án (seed) | Warning | ALERT-OPS-02 Warning |
| METRIC-OPS-03 | Thực thi quyết định | task từ quyết định xong / đến hạn × 100 | % | W < 70 · C < 50 | 100 · 90 · 85 · 80 · 75 · 66,7 | **66,7** | 2 / 3 (DOC-05) | Warning | ALERT-OPS-03 Warning |
| METRIC-HR-01 | Doanh thu / nhân sự | DT 12 tháng / headcount BQ; so `HR_REVENUE_PER_HEAD_PLAN` = 2,0 tỷ | tỷ/người/năm | W thấp hơn KH > 15% · C > 25% | 2,06 · 2,04 · 2,02 · 2 · 1,98 · 1,96 | **1,96** | 294 tỷ / 150; thấp hơn KH 2% | OK | — |
| METRIC-HR-02 | Turnover năm hóa | BR-HR-01 | % | W ≥ 15 · C ≥ 20 | 11,5 · 12 · 12,4 · 12,7 · 13 · 13,3 | **13,3** | 20 / 150 | OK | — |
| METRIC-HR-03 | Nhân sự quá tải | NV workload > 110% 2 tuần liên tiếp / NV active × 100 | % | W > 10 · C > 20 | 4,7 · 5,3 · 6 · 6,7 · 7,3 · 8,7 | **8,7** | 13 / 150 | OK | — |
| METRIC-HR-04 | Kế hoạch tuyển dụng trễ | đếm HiringPlan quá `target_date` chưa đủ người | kế hoạch | W ≥ 1 trễ 1–45 ngày · C ≥ 1 trễ > 45 ngày (DEC-143) | 0 · 0 · 0 · 0 · 0 · 1 | **1** | HP-2026-07 trễ 35 ngày (> 30 → vẫn phát event E6) | Warning | ALERT-HR-04 Warning |
| METRIC-CUS-01 | Pipeline coverage | Σ deal_value mở đóng trong quý / mục tiêu quý (BR-SAL-04); kèm coverage có trọng số | x | W < 2,8 · C < 2,5 (DEC-143) | 3,4 · 3,3 · 3,1 · 3,0 · 2,9 · 2,9 | **2,9** | 235,5 / 81,0 tỷ = 2,91x; trọng số 83,9 / 81,0 = 1,04x | OK | — |
| METRIC-CUS-02 | Win rate | won / (won + lost) × 100 | % | W giảm > 10 đ% so Δ3k · C > 20 đ% | 29 · 28 · 27,5 · 26 · 25,5 · 24 | **24** | 12 / 50 (DOC-03); giảm 2,3 đ% | OK | — |
| METRIC-CUS-03 | NRR | DT kỳ của nhóm khách kỳ gốc / DT kỳ gốc × 100 | % | W < 100 · C < 90 | 101 · 102,2 · 103 · 103,5 · 104 · 104,5 | **104,5** | 69,9 / 66,9 tỷ (Q3/2026 vs Q3/2025) | OK | — |
| METRIC-CUS-04 | Tập trung doanh thu top 5 | DT top 5 khách 12 tháng / tổng × 100 | % | W > 50 · C > 65 | 46 · 47,2 · 48,5 · 49,4 · 49,8 · 49,9 | **49,9** | 146,70 / 294 tỷ | OK | — |
| METRIC-CUS-05 | NPS | % promoter − % detractor | điểm | W < 30 · C < 0 | 28 · 30 · 31 · 33 · 32 · 32 | **32** | DOC-03, 214 phản hồi | OK | — |
| METRIC-CUS-06 | Chu kỳ bán TB | AVG(closed_at − created_at) deal won | ngày | W tăng > 20% so Δ3k · C > 40% | 52 · 53 · 54 · 58 · 63 · 68 | **68** | DOC-03; +16,6% so Δ3k | OK | — |
| METRIC-PRD-01 | Adoption (MAU) | MAU sản phẩm launched (+ adoption %) | người dùng | W MAU giảm > 10% so Δ3k · C > 20% | 1.540 · 1.560 · 1.575 · 1.560 · 1.548 · 1.430 | **1.430** | DOC-08 (adoption 72,3%); giảm 8,4% so Δ3k | OK | — |
| METRIC-PRD-02 | Churn | `churn_rate_pct` (sản phẩm xấu nhất) | %/tháng | W tăng > 25% tương đối & ≥ 2% · C > 50% & ≥ 2% (BR-PRD-01) | 1,4 · 1,5 · 1,5 · 1,4 · 1,6 · 1,79 | **1,79** | 35 / 1.950 (DOC-08); +19,7% so Δ3k, < sàn 2% | OK | — |
| METRIC-PRD-03 | Retention 30 ngày | `retention_30d_pct` | % | W < 40 · C < 25 | 72 · 71 · 70,5 · 70 · 69 · 68,3 | **68,3** | 41 / 60 (DOC-08) | OK | — |
| METRIC-PRD-04 | Roadmap đúng tiến độ | RoadmapItem không trễ / RoadmapItem của quý × 100 | % | W < 70 · C < 50 | 90 · 88 · 85 · 80 · 78 · 75 | **75,0** | 9 / 12 (DOC-08) | OK | — |
| METRIC-PRD-05 | Tính năng release trong kỳ | số feature released; attainment = released / planned × 100 | tính năng (+ %) | W attainment < 70 · C < 40 | 2 · 3 · 2 · 4 · 2 · 3 | **3 (75%)** | 3 release / 4 kế hoạch T9 (DOC-08) | OK | — |
| METRIC-RSK-01 | Rủi ro high/critical đang mở | đếm level ∈ {high, critical}, chưa closed/accepted | rủi ro | W ≥ 1 high · C ≥ 1 critical | 3 · 4 · 5 · 6 · 7 · 7 | **7** | R-01..07 (3 critical: R-01, R-04, R-05); R-12 `proposed` không đếm (DEC-148) | **Critical** | ALERT-RSK-01 Critical |
| METRIC-RSK-02 | Rủi ro high chưa có chủ | đếm level ≥ high, owner null | rủi ro | W ≥ 1 medium chưa chủ > 7 ngày · C ≥ 1 | 0 · 0 · 0 · 1 · 1 · 1 | **1** | R-06 (R-12 `proposed` không đếm) | **Critical** | ALERT-RSK-02 Critical |
| METRIC-RSK-03 | Rủi ro high > 30 ngày không mitigation | level ≥ high, mở > 30 ngày, không có mitigation in_progress | rủi ro | W ≥ 1 · C ≥ 1 rủi ro critical | 0 · 0 · 0 · 0 · 1 · 1 | **1** | R-03 (high) | Warning | ALERT-RSK-03 Warning |
| METRIC-RSK-04 | Điểm rủi ro tổng hợp | Σ score rủi ro mở / số rủi ro mở (thang 1–25) | điểm | W ≥ 10 · C ≥ 15 (DEC-143) | 9,5 · 10,1 · 10,6 · 11,2 · 11,8 · 12,4 | **12,4** | 136 / 11 | Warning | ALERT-RSK-04 Warning |
| METRIC-RSK-05 | Biện pháp quá hạn | đếm mitigation planned/in_progress quá hạn | biện pháp | W ≥ 1 · C ≥ 5 hoặc ≥ 1 thuộc rủi ro critical | 1 · 1 · 1 · 2 · 2 · 3 | **3** | 3 / 14 (R-01, R-07, R-10); 1 thuộc R-01 critical | **Critical** | ALERT-RSK-05 Critical |
| METRIC-RSK-06 | Strategy execution index | Σ weight × on_track / Σ weight × 100 (Objective Q3) | % | W < 70 · C < 50 | — · — · — · — · — · 66,7 | **66,7** | 4 / 6 Objective Q3 on track (weight bằng nhau) | Warning | ALERT-RSK-06 Warning |

### 6.1. Tổng hợp trạng thái

| Trụ | OK | Warning | Critical | Trạng thái trụ (03 §4: critical nếu có ≥ 1 metric critical) |
|---|---|---|---|---|
| PIL-F | 2 | 5 | 0 | **warning** |
| PIL-O | 3 | 4 | 0 | **warning** (HR-04 trễ 35 ngày < 45) |
| PIL-C | 6 | 0 | 0 | **ok** |
| PIL-U | 5 | 0 | 0 | **ok** |
| PIL-S | 0 | 3 | 3 | **critical** (RSK-01/02/05) |
| **Tổng 31** | **16** | **12** | **3** | **2 ok · 2 warning · 1 critical** (DEC-143) |

Ngoại lệ dồn vào trụ S (đúng câu chuyện "rủi ro mới chưa có chủ"). 15 alert đang mở (12 Warning + 3 Critical). Briefing CEO lấy tối đa 3 ngoại lệ ưu tiên: ALERT-RSK-02 (R-06 chưa có chủ; kèm khối "Rủi ro đề xuất" R-12 chờ phân công — §10.2), ALERT-RSK-01 (R-01 thiếu hụt dòng tiền, critical), ALERT-HR-04 (HP-2026-07 — nguyên nhân R-12).

---

## 7. Seed sự kiện (`platform.outbox_events`)

Seed phát qua outbox như luồng thật (không ghi thẳng vào bảng consumer), để demo được chuỗi event → rủi ro → insight. Mỗi event có `event_id` cố định (UUID v5 từ mã dưới) để seed chạy lại vẫn idempotent.

| # | Thời điểm | Event | Payload chính | Consumer → kết quả |
|---|---|---|---|---|
| E1 | 30/09/2026 | `EVT-finance.budget_exceeded` | dept `SAL`, quý 2026-Q3, utilization 109,0% (6 phòng ban > 100% đều phát event; không phòng nào > 10% nên không map sang rủi ro theo `RISK_EVENT_SCORING`, OQ-01) | risk: chỉ log · ai_core: insight "Chi phí kinh doanh vượt 9%" |
| E2 | 01/10/2026 | `EVT-finance.burn_over_forecast` | T9 burn 3,0 tỷ vs dự báo 2,5 tỷ (+20%) | risk: tăng L của R-01 (3→4) → `EVT-risk.risk_level_changed` (high → critical) |
| E3 | — | (không phát) | PRD-ORDER churn 1,79% < sàn 2% (BR-PRD-01) | R-05 lấy từ DOC-09; demo BR-PRD-01 bằng fixture TC-PRD-002 |
| E4 | 06/10/2026 | `EVT-risk.risk_level_changed` | R-01 high → critical | platform: ALERT-RSK-01 cập nhật · ai_core: đưa vào Briefing |
| E5 | 15/10/2026 | `EVT-sales.deal_closed_lost` | deal "Trang bị VP Tân Phú" 0,8 tỷ, lý do giá | risk: < `RISK_LOST_DEAL_MIN_VALUE` (1 tỷ), chỉ log |
| E6 | 20/10/2026 07:00 | `EVT-hr.hiring_plan_delayed` | HP-2026-07, trễ 35 ngày, 6 vị trí SAL | risk: **tự sinh R-12** (`risk_source='event'`, `status='proposed'`, owner null, high) → `EVT-risk.risk_proposed` (BR-RSK-03, DEC-148) |
| E7 | 20/10/2026 07:01 | `EVT-risk.risk_proposed` | R-12, category `people`, severity high | platform: thông báo RISK_MANAGER (không alert — 03 §3.1 #9) · ai_core: insight liên miền "Chậm tuyển → rủi ro hụt KR1.1 doanh thu Q4"; `EVT-risk.risk_identified` chỉ phát khi owner xác nhận ở phút 9–11 (§8) |
| E8 | 20/10/2026 07:05 | `EVT-execution.task_overdue` | 4 task DOC-05 quá hạn | platform: METRIC-OPS-01 tính lại |
| E9 | 20/10/2026 07:10 | `EVT-finance.cash_flow_forecast_updated` | bản base: đáy 3,1 tỷ tuần 7 (§10.4) | risk: R-13 `proposed` (kịch bản bi quan âm tuần 9) · ai_core: insight SCR-31 |

Kiểm thử idempotency: chạy seed E6 hai lần → chỉ 1 R-12 (`processed_events`).

---

## 8. Kịch bản demo 20 phút (01 §11)

| Phút | Vai | Bước | Dữ liệu dùng | Kết quả mong đợi |
|---|---|---|---|---|
| 0–2 | CEO | F1: mở SCR-01 | §6.1 | "3 việc cần anh, 1 rủi ro mới"; 2 trụ xanh (C, U) · 2 vàng (F, O) · 1 đỏ (S) — §6.1 |
| 2–5 | CEO | Bấm thẻ METRIC-FIN-01 (88,5%) → Panel AI → drill-down | DOC-01, DOC-02 | Nguyên nhân có source chip; ≤ 3 click tới trang 4 PDF DOC-01 và dòng HV-xxx |
| 5–7 | CEO | Hỏi AI "Rủi ro tuyển dụng chậm ảnh hưởng thế nào đến dự báo tài chính?" rồi "Runway nếu tháng sau không có doanh thu mới?" | R-12, HP-2026-07, forecast | Trả lời có `sources`; runway với doanh thu = 0 tính từ tool Finance, không bịa số |
| 7–9 | CEO | Chọn phương án → Action card L2 → xác nhận | QD-01 | 3 task tạo, toast hoàn tác 10 giây, quyết định mới ghi log |
| 9–11 | CFO → Risk Manager | Chuyển vai; SCR-21 what-if R-01 | R-01, cash 20,4 tỷ | Tác động lên runway/nhân sự/sản phẩm; xác nhận R-12 (`proposed` → `identified`, owner Lê Hoàng Giang) và gán owner R-06 → METRIC-RSK-02 = 0, ALERT-RSK-02 đóng; CFO mở SCR-31 (đáy 3,1 tỷ tuần 7) và SCR-29 duyệt AR-02 |
| 11–16 | CEO | UC-07: thả 9 tài liệu | DOC-01..09 | Phân loại đúng 9/9; trang 7 DOC-01 confidence Thấp |
| 16–18 | Reviewer | F2: duyệt DOC-02 trên SCR-10 | DOC-02 | Duyệt ≤ 60 giây; XD-01 MATCH; ghi vào `finance.invoices` qua Action Registry |
| 18–20 | CEO | Quay lại SCR-01; SCR-29 duyệt bước 2 AR-01 (620 triệu ≥ 500 triệu — DEC-155); SCR-30 tạo báo cáo `BOARD` | lineage, §10.5–12.6 | Metric cập nhật, insight mới, lineage tới tài liệu vừa duyệt |

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
| K10 | Ngân sách | Σ 7 phòng ban | 9.600 / 10.200 triệu, +6,3%; SAL 3.650 / 3.350 = +9,0% ✓ |
| K11 | Phải thu 30/09 | 27.936 + 726 + 10.338 (triệu) | 39.000 triệu; DSO 47,8 ✓ |
| K12 | Phải thu 20/10 | còn nợ 25 HĐ T9 15.651.300.000 + HL-001 726.000.000 | 16.377.300.000 ✓ |
| K13 | Quá hạn 20/10 | 5 HĐ 3.192.000.000 + HL-001 726.000.000 | 3.918.000.000 → 23,9% ✓ |
| K14 | Runway | 20,4 / ((2,1 + 2,55 + 3,0) / 3) | 8,0 tháng ✓ |
| K15 | Pipeline | 235,5 / 81 (trọng số: 5,4 + 13,125 + 24,0 + 41,4 = 83,925 / 81) | 2,91x → 2,9x; trọng số 1,04x ✓ |
| K16 | NRR | 69,9 / 66,9; 69,9 + 3,6 (khách mới) = 73,5 | 104,5% ✓ |
| K17 | Doanh thu theo sản phẩm | 19,125 + 4,08 + 2,295 | 25,5 tỷ ✓ |
| K18 | Tài khoản ABC Order | 1.950 + 63 − 35 | 1.978; MAU 1.430 / 1.978 = 72,3%; churn 35 / 1.950 = 1,79% ✓ |
| K19 | Rủi ro | 11 rủi ro mở (R-12..14 `proposed` không đếm — DEC-148), score = L × I, Σ 136 / 11 | index 12,4 (Warning, DEC-143); 7 high+; 3 critical ✓ (xem K28) |
| K20 | Mitigation | 14 mở, 3 quá hạn (1 thuộc R-01 critical) | METRIC-RSK-05 = 3 → Critical ✓ |
| K21 | Trạng thái 31 metric | đánh giá theo ngưỡng 03 §2 | 16 OK · 12 W · 3 C, khớp cột "Trạng thái"; trụ 2 ok · 2 warning · 1 critical ✓ |

---

## 10. Seed bổ sung v2.1 (Phase 3d — DEC-147, DEC-148, DEC-153, DEC-155, DEC-157)

Mọi số trong mục này tính bằng script (DEC-022); kiểm tra ở §10.8. `source = 'SEED'`, `data_classification` theo 03 §7.4 (DEC-157).

### 10.1. Initiative / Milestone / Task (`ENT-Initiative`, `ENT-Milestone`, `ENT-Task` — DEC-147)

Mỗi trụ một Initiative, gắn Objective Q4 (DOC-07); `weight_pct` trong Objective = 100 (một Initiative / Objective). `progress_pct` = milestone `done` / tổng milestone × 100 (hệ thống tính; seed ghi sẵn để khớp).

| Mã | Initiative | Trụ | Objective | Owner | Phòng ban | Bắt đầu → Kết thúc dự kiến | Trạng thái | Ngân sách |
|---|---|---|---|---|---|---|---|---|
| `INI-2026-01` | Thu hồi công nợ quá hạn ≤ 10% | F | O2 | Trần Thị Minh | FIN | 01/10/2026 → 31/12/2026 | `active` | 150.000.000 |
| `INI-2026-02` | Tuyển đủ 9 sales HN + đào tạo nhập môn | O | O3 | Phạm Thị Hạnh | HRA | 15/09/2026 → 30/11/2026 | `at_risk` | 420.000.000 |
| `INI-2026-03` | Giữ chân top 5 khách hàng | C | O1 | Lê Hoàng Giang | SAL | 01/10/2026 → 31/12/2026 | `active` | 300.000.000 |
| `INI-2026-04` | ABC Order 2.0 — giảm churn | U | O4 | Đỗ Quang Huy | PRD | 01/09/2026 → 15/01/2027 | `active` | 1.200.000.000 |
| `INI-2026-05` | Đa dạng hóa nhà cung cấp mực in | S | O5 | Bùi Thu Trang | BOD | 01/10/2026 → 31/12/2026 | `planned` | 80.000.000 |

| Initiative | Milestone (hạn · trạng thái) | Task (assignee · hạn · trạng thái · `task_source`) |
|---|---|---|
| INI-2026-01 | M1 Phân loại 39 khoản phải thu theo tuổi nợ (10/10 · `done`) · M2 Thu HL-001 + 5 HĐ quá hạn (15/11 · `planned`) · M3 Áp điều khoản thanh toán mới (15/12 · `planned`) | Gọi điện 5 khách quá hạn (Vũ Đức Thắng · 25/10 · `in_progress` · manual) · Gửi thư nhắc HL-001 lần 2 (Trần Thị Minh · 22/10 · `todo` · ai) · Cập nhật mẫu hợp đồng điều khoản 30 ngày (Trần Thị Minh · 30/11 · `backlog` · manual) |
| INI-2026-02 | M1 Đăng tuyển 3 kênh (25/09 · `done`) · M2 Phỏng vấn vòng 2 (25/10 · `missed`) · M3 Nhận việc 9 người (30/11 · `planned`) | Sàng lọc 120 CV (Phạm Thị Hạnh · 05/10 · `done` · manual) · Đặt lịch phỏng vấn HN (Phạm Thị Hạnh · 18/10 · `blocked` "thiếu người phỏng vấn SAL" · meeting) · Chuẩn bị chương trình onboarding (Phạm Thị Hạnh · 20/11 · `todo` · meeting) |
| INI-2026-03 | M1 Họp QBR với 5 khách (31/10 · `planned`) · M2 Gia hạn HD-2026-002 (15/11 · `planned`) | Chuẩn bị QBR Văn phòng Phẩm (Ngô Thị Lan · 28/10 · `in_progress` · manual) · Đề xuất giá gia hạn HD-2026-002 (Lê Hoàng Giang · 05/11 · `todo` · document) · Khảo sát hài lòng top 5 (Ngô Thị Lan · 15/11 · `backlog` · ai) |
| INI-2026-04 | M1 Phỏng vấn 20 khách rời bỏ (30/09 · `done`) · M2 Phát hành onboarding mới (15/11 · `planned`) · M3 Thông báo trong app (15/12 · `planned`) | Tổng hợp lý do churn (Đỗ Quang Huy · 05/10 · `done` · manual) · Thiết kế luồng onboarding (Đỗ Quang Huy · 30/10 · `in_review` · manual) · Đo MAU sau phát hành (Đỗ Quang Huy · 30/11 · `todo` · ai) |
| INI-2026-05 | M1 Danh sách 3 NCC thay thế (31/10 · `planned`) · M2 Ký hợp đồng NCC thứ hai (15/12 · `planned`) | Xin báo giá 3 NCC (Bùi Thu Trang · 28/10 · `todo` · mitigation) · Đánh giá rủi ro NCC (Bùi Thu Trang · 10/11 · `backlog` · mitigation) · Đề xuất ngân sách thử nghiệm (Trần Thị Minh · 15/11 · `backlog` · manual) |

**Đếm:** 5 Initiative · **13 Milestone** (3 `done`, 1 `missed`, 9 `planned`) · **15 Task** (2 `done`, 2 `in_progress`, 1 `in_review`, 1 `blocked`, 5 `todo`, 4 `backlog`). Task này **bổ sung** vào 105 + 15 task §5 (`execution.tasks` = 135); mọi hạn từ 05/10 trở đi (ngoài kỳ T9) nên METRIC-OPS-01 kỳ T9 không đổi. `progress_pct`: INI-01 33,3 · INI-02 33,3 · INI-03 0 · INI-04 33,3 · INI-05 0.

### 10.2. Rủi ro đề xuất (`status = proposed` — DEC-148)

R-12 đổi từ "tự sinh `identified`" sang **`proposed`** (BR-RSK-03 2.1.0): rủi ro tự sinh chờ owner xác nhận, **không** tính vào METRIC-RSK-01..05.

| Mã | Rủi ro | `risk_source` | Nguồn | Danh mục (13 — DEC-148) | L × I | Level | Owner đề xuất | Đề xuất lúc |
|---|---|---|---|---|---|---|---|---|
| R-12 | Chậm tuyển 6 sales HN ảnh hưởng doanh thu Q4 | `event` | E6 `EVT-hr.hiring_plan_delayed` (HP-2026-07) | `people` | 3 × 4 = 12 | high | — (chờ phân công) | 20/10/2026 07:00 |
| R-13 | Dòng tiền âm tuần 9 ở kịch bản bi quan | `ai` | E9 `EVT-finance.cash_flow_forecast_updated` (§10.4, `pessimistic` đáy −1,984 tỷ) | `financial` | 2 × 5 = 10 | high | Trần Thị Minh | 20/10/2026 07:10 |
| R-14 | Hợp đồng HD-2026-002 thiếu điều khoản phạt chậm thanh toán | `document` | DOC-04 (IDP, trường `penalty_clause = null`) | `legal` | 2 × 3 = 6 | medium | Lê Hoàng Giang | 20/10/2026 07:20 |

Kịch bản demo (phút 9–11): Risk Manager xác nhận R-12 → `identified` + owner Lê Hoàng Giang → `EVT-risk.risk_identified` (high) — METRIC-RSK-01 7 → 8 (vẫn Critical), METRIC-RSK-02 không đổi (R-12 có chủ ngay khi xác nhận). Bác bỏ R-14 → `rejected` (bắt buộc lý do).

### 10.3. Data Quality Score theo domain (METRIC-DQ-01 — 03 §2.6)

`dq_score = completeness × 0,3 + accuracy × 0,4 + freshness × 0,3`; ngưỡng warning < 80, critical < 60 (`THR_DQ_01_*`). Seed vào `ENT-MetricValue` (`scope_type = company` + bản ghi theo domain trong `metric_snapshot` lineage — 05 không có `scope_type = domain`, OQ-10).

| Domain | Completeness | Accuracy | Freshness | DQ Score | Trạng thái | Nguyên nhân seed |
|---|---|---|---|---|---|---|
| finance | 96 | 92 | 100 | **95,6** | ok | DOC-01/02 duyệt đủ; 8% field tiền bị reviewer sửa |
| sales | 91 | 86 | 80 | **85,7** | ok | 1/5 nguồn quá SLA (pipeline cập nhật 30 giờ trước) |
| hr | 84 | 78 | 60 | **74,4** | warning | 16% hồ sơ thiếu `position`; DOC-06 nạp 4 ngày trước |
| product | 88 | 82 | 70 | **80,2** | ok | DOC-08 nạp 5 ngày trước (≤ 72 giờ: không) |
| risk | 62 | 58 | 50 | **56,8** | critical | 4/12 rủi ro thiếu `review_date`; R-06 thiếu owner; sổ rủi ro chưa cập nhật 6 ngày |
| execution | 79 | 74 | 55 | **69,8** | warning | 21% task thiếu `estimate_hours`; check-in KR quá hạn |
| **Công ty** | | | | **77,1** | **warning** | Trung bình 6 domain (không trọng số) → ALERT-DQ-01 Warning |

METRIC-DQ-01 **không** tham gia trạng thái trụ (03 §4) → §6.1 giữ nguyên 2 ok · 2 warning · 1 critical. Tổng metric seed: **32** (31 trụ + DQ-01); alert mở: **16** (15 + ALERT-DQ-01 Warning).

**Data Quality Freshness SLA theo domain (DEC-158 — nguồn cho thành phần `freshness` của DQ Score):**

| Domain | SLA (giờ) | Env |
|---|---|---|
| finance | 24 | `SLA_FRESHNESS_FINANCE_HOURS` |
| sales | 24 | `SLA_FRESHNESS_SALES_HOURS` |
| hr | 72 | `SLA_FRESHNESS_HR_HOURS` |
| product | 72 | `SLA_FRESHNESS_PRODUCT_HOURS` |
| risk | 48 | `SLA_FRESHNESS_RISK_HOURS` |
| execution | 24 | `SLA_FRESHNESS_EXECUTION_HOURS` |

Freshness thành phần = nguồn cập nhật trong SLA / tổng nguồn × 100. Đây **không** phải Operational Freshness SLA (nhãn "dữ liệu cũ" trên dashboard: execution/sales 1 giờ, finance/risk 4 giờ, hr/product 24 giờ — `SLA_OPERATIONAL_<DOMAIN>_HOURS`, 03 §2.6); hai loại khác mục đích, không xung đột (DEC-158).

### 10.4. Dòng tiền 13 tuần (`ENT-CashFlowForecast` + 13 `ENT-CashFlowForecastLine` × 3 kịch bản — DEC-148)

`start_week` = 19/10/2026 (Thứ Hai tuần chứa `DEMO_REFERENCE_DATE`); `opening_cash` = **18.400.000.000** (số dư 30/09 20,4 tỷ − chi ròng 01–18/10 2,0 tỷ, `ENT-CashPosition` 18/10). Đơn vị bảng: **triệu đồng** (seed lưu VND × 1.000.000). Kịch bản chỉ khác **tỷ lệ thu công nợ đúng hạn** (`assumptions.collection_on_time_pct`): lạc quan 95% · **cơ sở 85%** · bi quan 75%; dòng thu công nợ = cơ sở × (tỷ lệ / 85), làm tròn triệu. Chi giữ nguyên. Lương: tổng tháng 2.925 (DOC-06), trả tuần 1/5/9 (không lương cá nhân — 05).

**Kịch bản cơ sở (`is_current = true`, `confidence_level = MEDIUM`):**

| Tuần | Bắt đầu | Thu công nợ | Thu khác | Trả NCC | Lương | Opex | Chi khác | Ròng | Số dư cuối |
|---|---|---|---|---|---|---|---|---|---|
| 1 | 19/10 | 4.200 | 300 | 2.100 | 2.925 | 800 | 900 | −2.225 | 16.175 |
| 2 | 26/10 | 5.200 | 100 | 6.200 | 0 | 800 | 660 | −2.360 | 13.815 |
| 3 | 02/11 | 4.800 | 100 | 5.400 | 0 | 800 | 0 | −1.300 | 12.515 |
| 4 | 09/11 | 5.000 | 150 | 5.200 | 0 | 800 | 0 | −850 | 11.665 |
| 5 | 16/11 | 4.600 | 100 | 4.300 | 2.925 | 800 | 900 | −4.225 | 7.440 |
| 6 | 23/11 | 4.400 | 100 | 5.900 | 0 | 800 | 0 | −2.200 | 5.240 |
| 7 | 30/11 | 3.800 | 100 | 5.240 | 0 | 800 | 0 | −2.140 | **3.100** (đáy) |
| 8 | 07/12 | 7.600 | 200 | 4.300 | 0 | 800 | 0 | 2.700 | 5.800 |
| 9 | 14/12 | 6.800 | 100 | 4.600 | 2.925 | 800 | 900 | −2.325 | 3.475 |
| 10 | 21/12 | 7.400 | 150 | 4.100 | 0 | 800 | 0 | 2.650 | 6.125 |
| 11 | 28/12 | 6.900 | 100 | 4.500 | 0 | 800 | 0 | 1.700 | 7.825 |
| 12 | 04/01 | 7.200 | 100 | 4.400 | 0 | 800 | 0 | 2.100 | 9.925 |
| 13 | 11/01 | 4.725 | 150 | 4.200 | 0 | 800 | 0 | −125 | **9.800** |

Chi khác tuần 1/5/9 = BHXH + thuế TNCN nộp hộ 900; tuần 2 = thuế TNDN tạm nộp Q3 660 (= `income_tax` DOC-01).

**Tổng hợp 3 kịch bản** (bản `optimistic`/`pessimistic` lưu `is_current = false`, `assumptions.scenario`):

| Kịch bản | Thu đúng hạn | Σ thu 13 tuần | Σ chi 13 tuần | Đáy (tuần) | Số dư tuần 13 |
|---|---|---|---|---|---|
| `optimistic` | 95% | 82.920 | 82.975 | 6.865 (tuần 7) | 18.345 |
| `base` | 85% | 74.375 | 82.975 | **3.100 (tuần 7)** | **9.800** |
| `pessimistic` | 75% | 65.830 | 82.975 | **−1.984 (tuần 9)** | 1.255 |

Khớp wireframe SCR-31 (06 §4.14: đầu kỳ 18,4 tỷ · đáy 3,1 tỷ tuần 7 · cuối kỳ 9,8 tỷ). Bi quan âm tuần 9 → E9 + R-13 (§10.2).

**Event seed bổ sung (§7):** E9 20/10/2026 07:10 `EVT-finance.cash_flow_forecast_updated` `{ min_projected_cash: 3100000000, min_cash_week: 7 }` (bản base) → risk: R-13 `proposed` (từ kịch bản bi quan, `RISK_EVENT_SCORING`) · ai_core: insight SCR-31.

### 10.5. Mẫu báo cáo (`ENT-Report` — DEC-153; 10 EP-120)

| Mẫu (`template_code`) | `kind` lưu | Kỳ seed | Phạm vi | Định dạng | Trạng thái seed | Nội dung |
|---|---|---|---|---|---|---|
| `DAILY` | — (Briefing EP-10, không lưu `ENT-Report`) | 20/10/2026 | công ty / theo role | màn hình | — | §6.1 + 3 ngoại lệ Briefing |
| `WEEKLY` | `WEEKLY` | `2026-W42` | công ty + phòng ban LOG | PDF | `READY` ×2 | 31 metric + DQ, alert mới, task quá hạn, rủi ro mới |
| `MONTHLY` | `MONTHLY` | `2026-09` | công ty | PDF + XLSX | `READY` ×2 | P&L T9 (DOC-01), ngân sách (§3), pipeline, nhân sự, rủi ro |
| `BOARD` | `MONTHLY` (`metric_snapshot.template_code = BOARD`) | `2026-Q3` → kỳ `2026-09` | công ty | PDF | `QUEUED` (demo bấm tạo → `READY`) | MONTHLY + 5 Initiative (§10.1), dòng tiền 13 tuần (§10.4), quyết định cần HĐQT |

Đếm seed `ENT-Report`: **5** bản ghi (4 `READY`, 1 `QUEUED`). Word (.docx) hoãn v2.1 (DEC-153).

### 10.6. Yêu cầu phê duyệt (`ENT-ApprovalRule`, `ENT-ApprovalRequest` — DEC-153, DEC-155)

**Rule (4):**

| Code | `target_kind` | Điều kiện | Bước 1 | Bước 2 | SLA |
|---|---|---|---|---|---|
| `APR-EXPENSE-LARGE` | `ACT-record_expense` | `amount ≥ 50.000.000` | `CFO` | `CEO` khi `amount ≥ APPROVAL_FINANCE_THRESHOLD_VND` (500.000.000) | 8 giờ |
| `APR-INVOICE-IN` | `ACT-create_invoice` | `amount ≥ 100.000.000` | `CFO` | `CEO` khi ≥ 500.000.000 | 8 giờ |
| `APR-HIRING` | `hiring_plan` | `headcount ≥ 1` | `CFO` | — | 16 giờ |
| `APR-AI-POLICY` | `ai_action` | nâng autonomy (10 EP-117) | chủ domain (`CFO` / `VP_SALES` / `HR_MANAGER` / `CPO` / `RISK_MANAGER`) | — | 24 giờ |

**Request (8):**

| # | Rule | Nội dung | Giá trị | Người gửi | Trạng thái | Bước | Hạn / ghi chú |
|---|---|---|---|---|---|---|---|
| AR-01 | APR-EXPENSE-LARGE | Mua 40 máy in nhập khẩu (kho LOG) | 620.000.000 | Hoàng Minh Tuấn | `PENDING` | 2 (CFO đã duyệt 19/10) | Chờ CEO, hạn 21/10 08:00 — "quyết định đang chờ anh" (US-CEO-006) |
| AR-02 | APR-INVOICE-IN | HĐ NCC mực in T10 | 180.000.000 | Vũ Đức Thắng | `PENDING` | 1 | Chờ CFO, hạn 20/10 16:00 |
| AR-03 | APR-HIRING | HP-2026-07 bổ sung 2 vị trí | 2 người | Phạm Thị Hạnh | `PENDING` | 1 | **Quá SLA** → `escalated_at` 20/10 06:00 tới CEO |
| AR-04 | APR-EXPENSE-LARGE | Hội nghị khách hàng Q4 (do AI soạn — `ai_action_id`, `TOOL-request_approval`) | 95.000.000 | Lê Hoàng Giang | `PENDING` | 1 | Chờ CFO, nhãn "AI soạn" |
| AR-05 | APR-EXPENSE-LARGE | Gia hạn bản quyền phần mềm kế toán | 72.000.000 | Trần Thị Minh | `APPROVED` | 1 | CEO duyệt 15/10 (người gửi là CFO → bước 1 dùng `escalate_to_role_code`) |
| AR-06 | APR-INVOICE-IN | HĐ vận chuyển T9 | 540.000.000 | Vũ Đức Thắng | `APPROVED` | 2 | CFO 10/10 → CEO 11/10 |
| AR-07 | APR-EXPENSE-LARGE | Quà tặng khách VIP | 150.000.000 | Ngô Thị Lan | `REJECTED` | 1 | CFO từ chối 14/10, lý do "vượt định mức chi tiếp khách Q4" |
| AR-08 | APR-AI-POLICY | Nâng `ACT-create_task` → L3 cho phòng SAL | — | Trịnh Văn Khoa | `APPROVED` | 1 | VP Sales xác nhận 12/10 (GAP D-08) |

Đếm: **8** request — 4 `PENDING` (1 bước 2, 1 escalated, 1 do AI soạn), 3 `APPROVED`, 1 `REJECTED`. Badge SCR-29 của CEO = 2 (AR-01, AR-03 escalated); CFO = 2 (AR-02, AR-04).

### 10.7. Phân loại dữ liệu seed (DEC-157)

| Dữ liệu seed | `data_classification` | Provider AI khi demo |
|---|---|---|
| `platform.metric_values` (32 metric × 6 kỳ), `platform.reports`, Briefing | `INTERNAL` | Cloud (chain 07 §6.1) |
| Từng hóa đơn DOC-02, deal, hợp đồng DOC-04, rủi ro DOC-09, approval request | `CONFIDENTIAL` | Local `qwen2.5:7b-instruct`; ADMIN override cloud qua EP-129 nếu máy demo không chạy được Ollama |
| Lương cá nhân, ngày sinh, địa chỉ DOC-06 | `SECRET` | Không LLM |

### 10.8. Kiểm tra số học bổ sung

| # | Kiểm tra | Phép tính | Kết quả |
|---|---|---|---|
| K22 | Đếm Initiative / Milestone / Task | 5 · (3+3+2+3+2) · 5 × 3 | 5 · 13 · 15 ✓ |
| K23 | Dòng tiền base | 18.400 + Σ ròng (−8.600) | 9.800; đáy tuần 7 = 3.100 ✓ |
| K24 | Σ thu / chi base | 74.375 − 82.975 | −8.600 = 9.800 − 18.400 ✓ |
| K25 | Kịch bản | thu công nợ × 95/85 và × 75/85 | đáy 6.865 (T7) · −1.984 (T9) ✓ |
| K26 | DQ domain | c × 0,3 + a × 0,4 + f × 0,3 | 95,6 · 85,7 · 74,4 · 80,2 · 56,8 · 69,8 ✓ |
| K27 | DQ công ty | Σ 6 domain / 6 = 462,5 / 6 | 77,1 → warning ✓ |
| K28 | Rủi ro mở (không gồm `proposed`) | 11 rủi ro, Σ score 136 | index 12,4 (Warning); RSK-01 = 7 (3 critical); RSK-02 = 1 (R-06) ✓ |
| K29 | Approval | 4 + 3 + 1 | 8 request ✓ |

---

## 11. Open questions

| # | Câu hỏi | Đề xuất | Ảnh hưởng |
|---|---|---|---|
| OQ-01 | Đã đối chiếu với 03 v2.0.0. Còn mở: 03 BR-FIN-05 phát `budget_exceeded` ở mọi phòng ban > 100%, nhưng ánh xạ event → rủi ro (`RISK_EVENT_SCORING`) chưa có ngưỡng; demo giả định chỉ chênh > 10% mới sinh/cập nhật rủi ro | Bổ sung ngưỡng vào 03 BR-RSK-03 | 03, 08 |
| OQ-02 | Tên env mật khẩu đổi từ v1 (`DEMO_SALES_PASSWORD`, `DEMO_HR_PASSWORD`) sang theo mã role | Đổi theo mã role, cập nhật `.env.example` ở T-014 | 07, `.env.example` |
| OQ-03 | NRR cần doanh thu Q3/2025 theo khách (66,9 tỷ) — chỉ có ở seed | Gắn nhãn "Dữ liệu seed lịch sử" (P01) | 03, 05 |
| OQ-04 | METRIC-RSK-06 dùng tiến độ KR Q3 (đã đóng) trong khi DOC-07 là Q4 | Seed Q3 riêng; từ T11 tính theo Q4 | 03 |
| OQ-05 | Chưa liệt kê đủ 150 nhân viên, 28 feature, 140 deal lịch sử | Sinh bằng script seed có seed ngẫu nhiên cố định, giữ các tổng ở §9 | T-510 |
| OQ-06 | R-12 sinh từ event; nếu demo chạy lại trong ngày, thời điểm E6–E8 có cố định 20/10 07:00 không | Cố định theo `DEMO_REFERENCE_DATE` | T-510 |
| OQ-07 | ✅ **Resolved — DEC-143** (ngưỡng mới + hiệu chỉnh seed → 2 ok · 2 warning · 1 critical). Câu hỏi gốc: Với ngưỡng mặc định của 03 (vd CUS-01 C < 3,0x, RSK-04 C ≥ 12) cả 5 trụ đều critical — CEO thấy "toàn đỏ", giảm hiệu quả P07 | Human xem lại ngưỡng CUS-01/RSK-04 ở 03, hoặc chấp nhận cho demo | 03, 08 §6 |
| OQ-08 | R-12 đổi sang `proposed` (DEC-148) làm METRIC-RSK-01 8 → 7, RSK-02 2 → 1, RSK-04 12,3 → 12,4 — trạng thái không đổi | Chấp nhận (đã cập nhật §6, K19/K28); demo xác nhận R-12 tại phút 9–11 | 03, 14 TC-RSK-006 |
| OQ-09 | Task của Initiative có ảnh hưởng METRIC-OPS-01 kỳ T9 không | Không — hạn từ 05/10 (ngoài kỳ T9) | 03 |
| OQ-10 | DQ Score theo domain: 05 `platform.scope_type` chỉ có `company, department, product` | Lưu domain trong `metric_snapshot`/lineage của bản `company`; thêm `domain` vào enum nếu cần drill-down → DEC (Phase 4) | 05, 03 §2.6 |
| OQ-11 | ✅ **Resolved bằng DEC-158** (2 loại SLA khác mục đích, không xung đột): §10.3 = Data Quality Freshness SLA (`SLA_FRESHNESS_<DOMAIN>_HOURS`, execution 24 giờ); 03 §2.6 = Operational Freshness SLA (`SLA_OPERATIONAL_<DOMAIN>_HOURS`); 12 env đăng ký ở 07 §7. Câu hỏi gốc: SLA freshness theo domain lệch 03 §2.6 (BO-02) và chưa có trong 07 §7 | — | 03, 07, `.env.example` (T-014) |

---

## 12. Version

- **Version:** 2.1.0 (đề xuất — human promote ở 12)
- **Status:** draft (Phase 3d)
- **Last updated:** 2026-10-20
- **Applies to:** Aureon v2 (v2.0 demo-ready / v2.1 production-ready)
- **Maintainer:** @CyEyes
- **Change:** Viết lại theo DEC-136 (ABC ~150 NV, 9 tài liệu, 31 metric, 10 tài khoản, seed sự kiện); v1.0.0 lưu ở nhánh `v1`.
- **Change 2.1.0 (DEC-158, 2026-10-20):** §10.3 đổi thành Data Quality Freshness SLA một ngưỡng / domain (execution 48 → 24 giờ, bỏ mức critical 48 giờ của finance/sales); đóng OQ-11.
- **Change 2.1.0 (Phase 3d — DEC-147, DEC-148, DEC-153..155, DEC-157):** §10 seed v2.1 — 5 Initiative / 13 Milestone / 15 Task (mỗi trụ một), 3 rủi ro `proposed` (R-12 event, R-13 ai, R-14 document), DQ Score 6 domain (3 ok · 2 warning · 1 critical; công ty 77,1 warning), dòng tiền 13 tuần × 3 kịch bản (base đáy 3,1 tỷ tuần 7), 4 mẫu báo cáo / 5 report, 4 approval rule / 8 request, SLA freshness theo domain, phân loại seed; R-12 → `proposed` (RSK-01 7, RSK-02 1, RSK-04 12,4); event E6/E7 + E9; kiểm tra K22–K29; OQ-08..11.
- **Change (2026-10-19, DEC-143):** ngưỡng CUS-01/RSK-04/HR-04 mới; hiệu chỉnh seed (ngân sách SAL 3.350, pipeline 235,5 tỷ, top 5 146,7 tỷ, churn 35 → 1,79%, MAU 1.430, roadmap 9/12); §6.1 = 16 OK · 12 W · 3 C, trụ 2 ok · 2 warning · 1 critical; đóng OQ-07.

