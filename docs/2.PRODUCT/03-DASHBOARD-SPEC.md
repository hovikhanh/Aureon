# 03 — Dashboard Spec

> Đặc tả Dashboard 4 trụ của Aureon Demo: 18 metric, 18 alert, drill-down số → chi tiết → tài liệu gốc, hiển thị theo vai trò.
> Nguồn: `01-PROJECT-OVERVIEW.md` §2.1, §3, §4, §5, §6, §8; quyền theo `02-PERSONAS-PERMISSIONS.md` §3, §4.

---

## 1. Kiến trúc 4 trụ

### 1.1. Tổng quan

| Trụ | Mã pillar | Số metric | Số alert | Metric ID | Tài liệu nguồn chính (01 §8) |
|---|---|---|---|---|---|
| **Tài chính** | FIN | 6 | 6 | METRIC-FIN-01..06 | #1 Báo cáo tài chính Q3, #2 Danh sách hóa đơn T9, #7 KPI/OKR |
| **Khách hàng** | CUS | 5 | 5 | METRIC-CUS-01..05 | #2 Hóa đơn, #3 Báo cáo sales T9, #4 Hợp đồng, #7 KPI/OKR |
| **Vận hành** | OPS | 4 | 4 | METRIC-OPS-01..04 | #5 Biên bản họp giao ban, #7 KPI/OKR |
| **Con người** | HR | 3 | 3 | METRIC-HR-01..03 | #6 Danh sách nhân sự, #1/#2 (doanh thu), #5 (workload) |
| **Tổng** | — | **18** | **18** | — | — |

Quy ước: mỗi metric có **đúng 1 alert** cùng pillar và cùng số thứ tự trong pillar ở mức logic (ví dụ METRIC-FIN-03 ↔ ALERT-FIN-03). Alert có 2 mức: **Warning (vàng)** và **Critical (đỏ)** theo ngưỡng của metric.

### 1.2. Luồng dữ liệu vào dashboard

```
Tài liệu gốc (ENT-SourceDocument)
   ↓ IDP: phân loại → trích xuất → kiểm tra → Reviewer duyệt (04-IDP-FEATURE-SPEC)
Entity nghiệp vụ (ENT-Invoice, ENT-Contract, ENT-Task, ENT-Employee, …) + giá trị KPI/target
   ↓ Commit qua Action Registry → job tính metric
ENT-MetricValue (giá trị theo kỳ, kèm lineage tới bản ghi + tài liệu gốc)
   ↓ Đánh giá ngưỡng
ENT-Alert (Warning/Critical) → Dashboard theo role
```

- Mọi giá trị metric lưu ở `ENT-MetricValue` kèm: kỳ (`period`), `computed_at`, danh sách bản ghi nguồn (lineage) — phục vụ P01.
- Định nghĩa metric (`ENT-Metric`: công thức, ngưỡng) là **cấu hình seed**, không sửa qua UI trong MVP (02 §3.3).
- Khi một tài liệu được commit, các metric phụ thuộc được tính lại và alert được đánh giá lại (event-driven); ngoài ra có job tính định kỳ theo cột "Tần suất".
- Tên entity nghiệp vụ dùng ở đây (ENT-Invoice, ENT-Contract, ENT-Customer, ENT-Opportunity, ENT-Task, ENT-Decision, ENT-Project, ENT-Employee, ENT-Budget, ENT-CashBalance, ENT-Survey) là **tên logic**; cấu trúc chính thức do `05-DATA-MODEL.md` quyết định (xem Open questions OQ-01).

### 1.3. Quy ước chung cho đặc tả metric

| Thuộc tính | Quy ước |
|---|---|
| Kỳ mặc định | Tháng hiện hành (dữ liệu demo: T9/2026, Q3/2026, KPI Q4/2026) |
| Định dạng tiền (P04) | `1.250.000 đ`; số lớn rút gọn `1,2 tỷ`, `850 tr` — dấu chấm phân cách nghìn, dấu phẩy thập phân |
| Định dạng % (P04) | `12,5%` (1 chữ số thập phân) |
| Định dạng ngày (P04) | `05/10/2026`; kỳ tháng `T9/2026`; quý `Q3/2026` |
| Ngưỡng | **Xanh** = bình thường; **Vàng** = Warning; **Đỏ** = Critical. Đánh giá theo thứ tự Đỏ trước, Vàng sau |
| Nhãn độ tươi | Mỗi MetricCard hiển thị "Cập nhật 05/10/2026 08:30" (`computed_at`) |
| Thiếu dữ liệu | Hiển thị `—` + nhãn "Chưa có dữ liệu nguồn", không hiển thị 0 giả; không sinh alert |
| Ngưỡng là giá trị seed | Các con số ngưỡng dưới đây là mặc định cho demo công ty ABC (xem OQ-02) |

---

## 2. Đặc tả 18 chỉ số

### 2.1. Trụ Tài chính (6 chỉ số)

#### METRIC-FIN-01 — Doanh thu tháng

| Thuộc tính | Giá trị |
|---|---|
| Định nghĩa | Tổng doanh thu (chưa VAT) ghi nhận theo hóa đơn bán ra trong tháng, so với kế hoạch tháng |
| Công thức | `SUM(ENT-Invoice.amount_before_vat) WHERE issue_date ∈ tháng`; `% KH = Doanh thu / Kế hoạch tháng × 100` |
| Nguồn dữ liệu | ENT-Invoice (tài liệu #2); kế hoạch từ #7 KPI/OKR; đối chiếu tổng quý với #1 (#1 = SUM(#2)) |
| Tần suất | Khi commit hóa đơn mới + job hằng ngày |
| Đơn vị / định dạng | VNĐ, rút gọn `8,4 tỷ`; kèm `% KH` dạng `92,5%` |
| Loại biểu đồ | Bar (doanh thu theo tháng) + line (kế hoạch) |
| Ngưỡng vàng / đỏ | Vàng: `< 90%` kế hoạch; Đỏ: `< 80%` kế hoạch |
| Alert | ALERT-FIN-01 |
| Drill-down | Số → bảng doanh thu theo khách/tháng → danh sách hóa đơn → tài liệu #2 (dòng tương ứng) |

#### METRIC-FIN-02 — Biên lợi nhuận gộp

| Thuộc tính | Giá trị |
|---|---|
| Định nghĩa | Tỷ lệ lợi nhuận gộp trên doanh thu thuần của kỳ |
| Công thức | `(Doanh thu thuần − Giá vốn hàng bán) / Doanh thu thuần × 100` |
| Nguồn dữ liệu | Báo cáo tài chính (tài liệu #1: doanh thu, giá vốn, LN gộp) |
| Tần suất | Khi commit báo cáo tài chính (tháng/quý) |
| Đơn vị / định dạng | %, `18,5%` |
| Loại biểu đồ | Line (xu hướng theo kỳ) + sparkline trên card |
| Ngưỡng vàng / đỏ | Vàng: `< 15%`; Đỏ: `< 10%` |
| Alert | ALERT-FIN-02 |
| Drill-down | Số → bảng doanh thu / giá vốn theo kỳ → trang P&L trong tài liệu #1 |

#### METRIC-FIN-03 — Cash runway

| Thuộc tính | Giá trị |
|---|---|
| Định nghĩa | Số tháng doanh nghiệp duy trì hoạt động với số dư tiền hiện có, theo tốc độ đốt tiền ròng bình quân |
| Công thức | `Số dư tiền cuối kỳ / Dòng tiền ra ròng bình quân 3 tháng gần nhất`; nếu dòng tiền ròng ≥ 0 → hiển thị `> 24 tháng` |
| Nguồn dữ liệu | Báo cáo tài chính #1 (tiền & tương đương tiền, lưu chuyển tiền tệ) → ENT-CashBalance (logic) |
| Tần suất | Khi commit báo cáo tài chính; job hằng tuần |
| Đơn vị / định dạng | Tháng, 1 chữ số thập phân: `7,5 tháng` |
| Loại biểu đồ | Gauge (0–24 tháng, vùng xanh/vàng/đỏ) |
| Ngưỡng vàng / đỏ | Vàng: `< 9 tháng`; Đỏ: `< 6 tháng` |
| Alert | ALERT-FIN-03 |
| Drill-down | Số → bảng số dư tiền + dòng tiền ra theo tháng → trang lưu chuyển tiền tệ tài liệu #1 |

#### METRIC-FIN-04 — DSO (Days Sales Outstanding)

| Thuộc tính | Giá trị |
|---|---|
| Định nghĩa | Số ngày bình quân để thu tiền bán hàng |
| Công thức | `Phải thu khách hàng cuối kỳ / Doanh thu kỳ × Số ngày trong kỳ` (kỳ 90 ngày) |
| Nguồn dữ liệu | ENT-Invoice (trạng thái thanh toán, tài liệu #2); phải thu từ #1 |
| Tần suất | Job hằng ngày |
| Đơn vị / định dạng | Ngày, số nguyên: `52 ngày` |
| Loại biểu đồ | Line (xu hướng 6 kỳ) + sparkline |
| Ngưỡng vàng / đỏ | Vàng: `> 45 ngày`; Đỏ: `> 60 ngày` |
| Alert | ALERT-FIN-04 |
| Drill-down | Số → bảng phải thu theo khách → danh sách hóa đơn chưa thu → tài liệu #2 |

#### METRIC-FIN-05 — Công nợ quá hạn

| Thuộc tính | Giá trị |
|---|---|
| Định nghĩa | Tổng giá trị hóa đơn đã quá hạn thanh toán chưa thu, và tỷ trọng trên tổng phải thu |
| Công thức | `SUM(ENT-Invoice.amount_due) WHERE due_date < hôm nay AND status ≠ PAID`; `Tỷ lệ = Quá hạn / Tổng phải thu × 100` |
| Nguồn dữ liệu | ENT-Invoice (tài liệu #2: số, ngày, hạn thanh toán, khách, tiền); điều khoản hạn TT từ ENT-Contract (#4) |
| Tần suất | Job hằng ngày |
| Đơn vị / định dạng | VNĐ rút gọn `1,8 tỷ` + tỷ lệ `12,5%` |
| Loại biểu đồ | Stacked bar theo tuổi nợ (1–30, 31–60, 61–90, > 90 ngày) |
| Ngưỡng vàng / đỏ | Vàng: tỷ lệ quá hạn `> 10%`; Đỏ: `> 20%` hoặc có khoản quá hạn `> 90 ngày` |
| Alert | ALERT-FIN-05 |
| Drill-down | Số → bảng tuổi nợ theo khách → hóa đơn quá hạn → tài liệu #2 / hợp đồng #4 |

#### METRIC-FIN-06 — Chênh lệch ngân sách

| Thuộc tính | Giá trị |
|---|---|
| Định nghĩa | Mức chi phí thực tế vượt/thấp hơn ngân sách kỳ |
| Công thức | `(Chi phí thực tế − Ngân sách) / Ngân sách × 100` (dương = vượt ngân sách) |
| Nguồn dữ liệu | Chi phí thực tế từ #1; ngân sách từ #7 KPI/OKR → ENT-Budget (logic) |
| Tần suất | Khi commit #1 hoặc #7; job hằng tháng |
| Đơn vị / định dạng | %, có dấu: `+8,2%`; kèm số tiền chênh `+420 tr` |
| Loại biểu đồ | Bar (thực tế vs ngân sách theo khoản mục) |
| Ngưỡng vàng / đỏ | Vàng: vượt `> 5%`; Đỏ: vượt `> 10%` |
| Alert | ALERT-FIN-06 |
| Drill-down | Số → bảng khoản mục chi phí vs ngân sách → trang chi phí tài liệu #1 / dòng ngân sách tài liệu #7 |

### 2.2. Trụ Khách hàng (5 chỉ số)

#### METRIC-CUS-01 — Pipeline coverage

| Thuộc tính | Giá trị |
|---|---|
| Định nghĩa | Bội số giá trị pipeline đang mở (có trọng số) so với chỉ tiêu doanh thu còn lại của kỳ |
| Công thức | `SUM(ENT-Opportunity.value × probability) WHERE stage mở AND close_date ∈ quý / (Chỉ tiêu quý − Doanh thu đã ghi nhận)` |
| Nguồn dữ liệu | Báo cáo sales #3 (pipeline theo giai đoạn) → ENT-Opportunity (logic); chỉ tiêu từ #7 |
| Tần suất | Khi commit #3; job hằng tuần |
| Đơn vị / định dạng | Bội số, 1 chữ số thập phân: `2,8x` |
| Loại biểu đồ | Funnel/bar theo giai đoạn pipeline + sparkline coverage |
| Ngưỡng vàng / đỏ | Vàng: `< 3,0x`; Đỏ: `< 2,0x` |
| Alert | ALERT-CUS-01 |
| Drill-down | Số → bảng cơ hội theo giai đoạn → chi tiết cơ hội → bảng pipeline trong tài liệu #3 |

#### METRIC-CUS-02 — Tỷ lệ chuyển đổi

| Thuộc tính | Giá trị |
|---|---|
| Định nghĩa | Tỷ lệ cơ hội chốt thắng trên tổng cơ hội đã đóng (thắng + thua) trong kỳ |
| Công thức | `COUNT(Opportunity stage = WON) / COUNT(stage ∈ {WON, LOST}) × 100` trong kỳ |
| Nguồn dữ liệu | Báo cáo sales #3 → ENT-Opportunity; hợp đồng đã ký #4 xác nhận WON |
| Tần suất | Khi commit #3/#4; job hằng tuần |
| Đơn vị / định dạng | %, `24,0%` |
| Loại biểu đồ | Line theo tháng + bar số cơ hội thắng/thua |
| Ngưỡng vàng / đỏ | Vàng: `< 25%`; Đỏ: `< 15%` |
| Alert | ALERT-CUS-02 |
| Drill-down | Số → danh sách cơ hội thắng/thua → chi tiết cơ hội → tài liệu #3 / hợp đồng #4 |

#### METRIC-CUS-03 — NRR (Net Revenue Retention)

| Thuộc tính | Giá trị |
|---|---|
| Định nghĩa | Tỷ lệ doanh thu giữ lại từ nhóm khách hàng hiện hữu (cùng kỳ năm trước), đã tính mở rộng và sụt giảm |
| Công thức | `Doanh thu kỳ này từ khách đã có ở kỳ gốc / Doanh thu kỳ gốc của chính nhóm khách đó × 100` (kỳ gốc: cùng quý năm trước) |
| Nguồn dữ liệu | ENT-Invoice (#2) group theo ENT-Customer; dữ liệu kỳ gốc từ seed lịch sử (xem OQ-03) |
| Tần suất | Job hằng tháng |
| Đơn vị / định dạng | %, `104,5%` |
| Loại biểu đồ | Line theo quý + waterfall (giữ lại / mở rộng / sụt giảm / mất khách) |
| Ngưỡng vàng / đỏ | Vàng: `< 100%`; Đỏ: `< 90%` |
| Alert | ALERT-CUS-03 |
| Drill-down | Số → bảng doanh thu theo khách hiện hữu (kỳ gốc vs kỳ này) → hóa đơn của khách → tài liệu #2 |

#### METRIC-CUS-04 — Tập trung doanh thu

| Thuộc tính | Giá trị |
|---|---|
| Định nghĩa | Tỷ trọng doanh thu của Top 5 khách hàng lớn nhất trên tổng doanh thu kỳ (rủi ro phụ thuộc khách) |
| Công thức | `SUM(doanh thu Top 5 khách) / Tổng doanh thu × 100` trong 12 tháng gần nhất (rolling) |
| Nguồn dữ liệu | ENT-Invoice (#2) group theo ENT-Customer; đối chiếu tên khách #3, #4 |
| Tần suất | Job hằng tháng; tính lại khi commit #2 |
| Đơn vị / định dạng | %, `46,3%`; kèm tỷ trọng khách lớn nhất |
| Loại biểu đồ | Pareto (bar doanh thu theo khách + line lũy kế %) |
| Ngưỡng vàng / đỏ | Vàng: Top 5 `> 40%` hoặc 1 khách `> 15%`; Đỏ: Top 5 `> 50%` hoặc 1 khách `> 25%` |
| Alert | ALERT-CUS-04 |
| Drill-down | Số → bảng doanh thu theo khách → hóa đơn/hợp đồng của khách → tài liệu #2 / #4 |

#### METRIC-CUS-05 — NPS (Net Promoter Score)

| Thuộc tính | Giá trị |
|---|---|
| Định nghĩa | Mức sẵn sàng giới thiệu của khách hàng, thang điểm 0–10 |
| Công thức | `% Promoter (9–10) − % Detractor (0–6)` |
| Nguồn dữ liệu | Kết quả khảo sát khách hàng ghi trong #7 KPI/OKR hoặc nhập tay C1 → ENT-Survey (logic) (xem OQ-04) |
| Tần suất | Theo quý (khi commit kết quả khảo sát) |
| Đơn vị / định dạng | Điểm, số nguyên có dấu: `+32` |
| Loại biểu đồ | Gauge (−100..+100) + stacked bar Promoter/Passive/Detractor |
| Ngưỡng vàng / đỏ | Vàng: `< 30`; Đỏ: `< 0` |
| Alert | ALERT-CUS-05 |
| Drill-down | Số → phân bố điểm khảo sát → danh sách phản hồi → tài liệu/bản ghi nhập tay nguồn |

### 2.3. Trụ Vận hành (4 chỉ số)

#### METRIC-OPS-01 — Tỷ lệ task đúng hạn

| Thuộc tính | Giá trị |
|---|---|
| Định nghĩa | Tỷ lệ task (action item) hoàn thành đúng hoặc trước hạn trên tổng task có hạn trong kỳ |
| Công thức | `COUNT(Task done AND done_at ≤ due_date) / COUNT(Task có due_date ∈ kỳ) × 100` |
| Nguồn dữ liệu | Biên bản họp giao ban #5 (action items: việc, người phụ trách, hạn) → ENT-Task; trạng thái cập nhật qua C1 |
| Tần suất | Khi commit #5 / cập nhật task; job hằng ngày |
| Đơn vị / định dạng | %, `78,0%` |
| Loại biểu đồ | Line theo tuần + sparkline |
| Ngưỡng vàng / đỏ | Vàng: `< 85%`; Đỏ: `< 70%` |
| Alert | ALERT-OPS-01 |
| Drill-down | Số → danh sách task trễ/đúng hạn theo người → chi tiết task → đoạn action item trong biên bản #5 |

#### METRIC-OPS-02 — Số dự án trễ

| Thuộc tính | Giá trị |
|---|---|
| Định nghĩa | Số dự án/đầu việc lớn đang mở có mốc đã quá hạn hoặc dự báo trễ |
| Công thức | `COUNT(ENT-Project WHERE status mở AND (milestone_due < hôm nay chưa xong OR có task quan trọng trễ > 7 ngày))` |
| Nguồn dữ liệu | #7 KPI/OKR (dự án/OKR, mốc) + #5 (tiến độ) → ENT-Project (logic), ENT-Task |
| Tần suất | Job hằng ngày |
| Đơn vị / định dạng | Số dự án: `2 / 9 dự án` |
| Loại biểu đồ | Bar ngang (dự án theo số ngày trễ) / bảng trạng thái |
| Ngưỡng vàng / đỏ | Vàng: `≥ 1` dự án trễ; Đỏ: `≥ 3` dự án trễ hoặc 1 dự án trễ `> 30 ngày` |
| Alert | ALERT-OPS-02 |
| Drill-down | Số → danh sách dự án trễ → mốc/task trễ của dự án → tài liệu #7 / biên bản #5 |

#### METRIC-OPS-03 — Tỷ lệ thực thi quyết định

| Thuộc tính | Giá trị |
|---|---|
| Định nghĩa | Tỷ lệ quyết định được ghi trong biên bản họp đã được thực thi (đóng) đúng hạn |
| Công thức | `COUNT(Decision status = DONE AND done_at ≤ due_date) / COUNT(Decision có due_date ≤ hôm nay) × 100` |
| Nguồn dữ liệu | Biên bản họp giao ban #5 (mục "Quyết định") → ENT-Decision (logic) liên kết ENT-Task |
| Tần suất | Khi commit #5; job hằng ngày |
| Đơn vị / định dạng | %, `66,7%` |
| Loại biểu đồ | Gauge + bảng quyết định chưa thực thi |
| Ngưỡng vàng / đỏ | Vàng: `< 80%`; Đỏ: `< 60%` |
| Alert | ALERT-OPS-03 |
| Drill-down | Số → danh sách quyết định theo trạng thái → task liên quan → đoạn quyết định trong biên bản #5 |

#### METRIC-OPS-04 — Workload

| Thuộc tính | Giá trị |
|---|---|
| Định nghĩa | Mức tải công việc bình quân: số task đang mở trên mỗi người phụ trách, và số người vượt mức chuẩn |
| Công thức | `COUNT(Task mở) / COUNT(DISTINCT assignee)`; người quá tải = assignee có `> 8` task mở |
| Nguồn dữ liệu | ENT-Task (#5) + ENT-Employee (#6, khớp tên người phụ trách) |
| Tần suất | Job hằng ngày |
| Đơn vị / định dạng | Task/người, 1 chữ số thập phân: `5,4 task/người`; kèm `3 người > 8 task` |
| Loại biểu đồ | Bar ngang theo người (heatmap mức tải) |
| Ngưỡng vàng / đỏ | Vàng: bình quân `> 6` hoặc `≥ 1` người `> 8` task; Đỏ: bình quân `> 8` hoặc `≥ 3` người `> 8` task |
| Alert | ALERT-OPS-04 |
| Drill-down | Số → bảng tải theo người → danh sách task của người → biên bản #5 nguồn của task |

### 2.4. Trụ Con người (3 chỉ số)

#### METRIC-HR-01 — Doanh thu / nhân sự

| Thuộc tính | Giá trị |
|---|---|
| Định nghĩa | Năng suất: doanh thu 12 tháng gần nhất trên số nhân sự bình quân |
| Công thức | `Doanh thu 12 tháng rolling (từ METRIC-FIN-01) / Số nhân sự đang làm việc bình quân kỳ` |
| Nguồn dữ liệu | Doanh thu tổng từ ENT-Invoice (#2)/#1; headcount từ Danh sách nhân sự #6 → ENT-Employee |
| Tần suất | Job hằng tháng; tính lại khi commit #2 hoặc #6 |
| Đơn vị / định dạng | VNĐ/người/năm rút gọn: `2,2 tỷ/người` |
| Loại biểu đồ | Line theo quý + sparkline |
| Ngưỡng vàng / đỏ | Vàng: `< 2,0 tỷ/người`; Đỏ: `< 1,7 tỷ/người` (baseline ABC ~100 tỷ / 45 người ≈ 2,2 tỷ) |
| Alert | ALERT-HR-01 |
| Drill-down | Số → bảng doanh thu và headcount theo tháng → danh sách nhân sự (tổng hợp) → tài liệu #6 (chỉ ROLE-04 mở file, xem §4.4) |

#### METRIC-HR-02 — Tỷ lệ nghỉ việc

| Thuộc tính | Giá trị |
|---|---|
| Định nghĩa | Tỷ lệ nhân sự nghỉ việc (tự nguyện + không tự nguyện) trên headcount bình quân, quy năm |
| Công thức | `COUNT(Employee end_date ∈ 12 tháng gần nhất) / Headcount bình quân 12 tháng × 100` |
| Nguồn dữ liệu | Danh sách nhân sự #6 (ngày vào, ngày nghỉ, trạng thái) → ENT-Employee |
| Tần suất | Khi commit #6; job hằng tháng |
| Đơn vị / định dạng | %/năm, `13,3%` |
| Loại biểu đồ | Line theo tháng + bar số người nghỉ theo phòng ban |
| Ngưỡng vàng / đỏ | Vàng: `> 15%`; Đỏ: `> 25%` |
| Alert | ALERT-HR-02 |
| Drill-down | Số → bảng nghỉ việc theo phòng ban → danh sách người nghỉ (họ tên, phòng ban, ngày nghỉ; không lương) → tài liệu #6 |

#### METRIC-HR-03 — Tỷ lệ nhân sự quá tải

| Thuộc tính | Giá trị |
|---|---|
| Định nghĩa | Tỷ lệ nhân sự đang ở trạng thái quá tải (nhiều task mở và/hoặc nhiều task trễ) — góc nhìn rủi ro con người, khác METRIC-OPS-04 (góc nhìn năng lực vận hành) |
| Công thức | `COUNT(Employee có > 8 task mở OR ≥ 3 task trễ) / COUNT(Employee đang làm việc) × 100` |
| Nguồn dữ liệu | ENT-Task (#5) join ENT-Employee (#6) |
| Tần suất | Job hằng ngày |
| Đơn vị / định dạng | %, `8,9%`; kèm `4 / 45 người` |
| Loại biểu đồ | Gauge + danh sách người quá tải theo phòng ban |
| Ngưỡng vàng / đỏ | Vàng: `> 10%`; Đỏ: `> 20%` |
| Alert | ALERT-HR-03 |
| Drill-down | Số → danh sách người quá tải → task mở/trễ của người → biên bản #5 nguồn |

---

## 3. Đặc tả 18 cảnh báo

### 3.1. Quy tắc chung

| Quy tắc | Mô tả |
|---|---|
| Sinh alert | Mỗi lần `ENT-MetricValue` mới được tính, hệ thống đánh giá ngưỡng của metric → tạo/cập nhật `ENT-Alert` |
| Mức độ | **Warning** (vàng) khi chạm ngưỡng vàng; **Critical** (đỏ) khi chạm ngưỡng đỏ. Một alert chỉ có 1 bản ghi đang mở/metric/kỳ; nâng cấp Warning → Critical cập nhật cùng bản ghi |
| Tự đóng | Metric về vùng xanh ở lần tính kế tiếp → alert chuyển `RESOLVED` (ghi audit log, actor = hệ thống) |
| Acknowledge / dismiss | Theo quyền 02 §3.3: CEO mọi alert; CFO `ALERT-FIN-*`; Sales Director `ALERT-CUS-*`; HR Manager `ALERT-HR-*`. Mọi thao tác ghi audit log |
| Role nhận | Tuân thủ quyền xem alert 02 §3.3: ROLE-01 xem tất cả; ROLE-02 xem `ALERT-FIN-*`, `ALERT-OPS-*`; ROLE-03 xem `ALERT-CUS-*`; ROLE-04 xem `ALERT-HR-*`; ROLE-05 không nhận alert dashboard |
| Hiển thị | Alert hiện ở vùng "Cần anh/chị quyết" (§5), sắp xếp Critical trước, rồi theo thời điểm sinh mới nhất |
| AI state (P02) | Hành động đề xuất là **AI gợi ý (L1)**; không tự thực hiện hành động nghiệp vụ |
| Trạng thái | `OPEN` → `ACKNOWLEDGED` → `RESOLVED` / `DISMISSED` |

### 3.2. Bảng 18 alert

| Alert ID | Metric | Tên alert | Điều kiện kích hoạt | Mức độ | Role nhận | Hành động đề xuất (AI gợi ý L1) |
|---|---|---|---|---|---|---|
| ALERT-FIN-01 | METRIC-FIN-01 | Doanh thu dưới kế hoạch | `% KH < 90%` → Warning; `< 80%` → Critical | Warning / Critical | ROLE-01, ROLE-02 | Xem doanh thu theo khách, so với pipeline |
| ALERT-FIN-02 | METRIC-FIN-02 | Biên LN gộp giảm | `< 15%` → Warning; `< 10%` → Critical | Warning / Critical | ROLE-01, ROLE-02 | Xem cơ cấu giá vốn theo nhóm hàng |
| ALERT-FIN-03 | METRIC-FIN-03 | Cash runway thấp | `< 9 tháng` → Warning; `< 6 tháng` → Critical | Warning / Critical | ROLE-01, ROLE-02 | Đề xuất họp CFO rà soát dòng tiền |
| ALERT-FIN-04 | METRIC-FIN-04 | DSO kéo dài | `> 45 ngày` → Warning; `> 60 ngày` → Critical | Warning / Critical | ROLE-01, ROLE-02 | Xem khách có kỳ thu tiền dài nhất |
| ALERT-FIN-05 | METRIC-FIN-05 | Công nợ quá hạn cao | Tỷ lệ `> 10%` → Warning; `> 20%` hoặc có khoản `> 90 ngày` → Critical | Warning / Critical | ROLE-01, ROLE-02 | Xem danh sách hóa đơn quá hạn cần đòi |
| ALERT-FIN-06 | METRIC-FIN-06 | Vượt ngân sách | Vượt `> 5%` → Warning; `> 10%` → Critical | Warning / Critical | ROLE-01, ROLE-02 | Xem khoản mục vượt ngân sách lớn nhất |
| ALERT-CUS-01 | METRIC-CUS-01 | Pipeline không đủ phủ chỉ tiêu | `< 3,0x` → Warning; `< 2,0x` → Critical | Warning / Critical | ROLE-01, ROLE-03 | Xem giai đoạn pipeline thiếu hụt |
| ALERT-CUS-02 | METRIC-CUS-02 | Tỷ lệ chuyển đổi thấp | `< 25%` → Warning; `< 15%` → Critical | Warning / Critical | ROLE-01, ROLE-03 | Xem lý do thua các cơ hội gần nhất |
| ALERT-CUS-03 | METRIC-CUS-03 | NRR dưới 100% | `< 100%` → Warning; `< 90%` → Critical | Warning / Critical | ROLE-01, ROLE-03 | Xem khách hiện hữu giảm mua |
| ALERT-CUS-04 | METRIC-CUS-04 | Doanh thu tập trung | Top 5 `> 40%` hoặc 1 khách `> 15%` → Warning; Top 5 `> 50%` hoặc 1 khách `> 25%` → Critical | Warning / Critical | ROLE-01, ROLE-03 | Xem khách chiếm tỷ trọng lớn, rủi ro phụ thuộc |
| ALERT-CUS-05 | METRIC-CUS-05 | NPS thấp | `< 30` → Warning; `< 0` → Critical | Warning / Critical | ROLE-01, ROLE-03 | Xem phản hồi Detractor |
| ALERT-OPS-01 | METRIC-OPS-01 | Task trễ hạn nhiều | `< 85%` → Warning; `< 70%` → Critical | Warning / Critical | ROLE-01, ROLE-02 | Xem task trễ theo người phụ trách |
| ALERT-OPS-02 | METRIC-OPS-02 | Dự án trễ | `≥ 1` dự án → Warning; `≥ 3` dự án hoặc trễ `> 30 ngày` → Critical | Warning / Critical | ROLE-01, ROLE-02 | Xem mốc dự án bị trễ |
| ALERT-OPS-03 | METRIC-OPS-03 | Quyết định chưa được thực thi | `< 80%` → Warning; `< 60%` → Critical | Warning / Critical | ROLE-01, ROLE-02 | Xem quyết định quá hạn và người phụ trách |
| ALERT-OPS-04 | METRIC-OPS-04 | Workload mất cân bằng | Bình quân `> 6` hoặc `≥ 1` người `> 8` task → Warning; bình quân `> 8` hoặc `≥ 3` người → Critical | Warning / Critical | ROLE-01, ROLE-02 | Gợi ý phân bổ lại task |
| ALERT-HR-01 | METRIC-HR-01 | Năng suất doanh thu/nhân sự giảm | `< 2,0 tỷ/người` → Warning; `< 1,7 tỷ/người` → Critical | Warning / Critical | ROLE-01, ROLE-04 | Xem xu hướng headcount vs doanh thu |
| ALERT-HR-02 | METRIC-HR-02 | Tỷ lệ nghỉ việc cao | `> 15%` → Warning; `> 25%` → Critical | Warning / Critical | ROLE-01, ROLE-04 | Xem phòng ban có nghỉ việc cao |
| ALERT-HR-03 | METRIC-HR-03 | Nhân sự quá tải | `> 10%` → Warning; `> 20%` → Critical | Warning / Critical | ROLE-01, ROLE-04 | Xem danh sách người quá tải |

> Ví dụ hiển thị trên card (P04): "⚠ Doanh thu T9/2026 đạt **7,6 tỷ** — **84,4%** kế hoạch (9,0 tỷ). Cập nhật 05/10/2026 08:30."

---

## 4. Drill-down & truy vết (P01)

### 4.1. Chuỗi drill-down tối đa 3 click

KPI demo (01 §4): **từ số → tài liệu gốc ≤ 3 click**.

| Click | Từ | Đến | Nội dung hiển thị | Màn hình |
|---|---|---|---|---|
| 0 | — | MetricCard trên dashboard | Giá trị, % so kế hoạch/ngưỡng, sparkline, màu ngưỡng, nhãn độ tươi | Dashboard theo role |
| 1 | MetricCard / AlertCard | **Metric Detail** | Panel P01 (§4.2) + biểu đồ xu hướng + BreakdownTable (phân rã theo khách/kỳ/người/khoản mục) | Metric Detail (drill-down) |
| 2 | Một dòng BreakdownTable | **Bản ghi gốc** | Bản ghi entity (hóa đơn, cơ hội, task, nhân sự…) với các field, lineage tới extraction và tài liệu | Metric Detail (panel bản ghi) / Document Detail |
| 3 | Link "Tài liệu gốc" | **Source Viewer** | File gốc, mở đúng trang, **tô vùng** chứa giá trị (`source_location`), confidence, người duyệt, thời điểm duyệt | Source Viewer |

Quy tắc:
- Click thẳng từ AlertCard vào Metric Detail đã lọc theo điều kiện alert (ví dụ ALERT-FIN-05 → bảng hóa đơn quá hạn) — vẫn ≤ 3 click.
- Từ Metric Detail có thể bỏ qua bước 2 bằng link "Xem tài liệu gốc" khi metric chỉ có 1 tài liệu nguồn (ví dụ METRIC-FIN-02 → trang P&L của #1) → 2 click.
- Breadcrumb luôn hiển thị: `Dashboard › METRIC-xx › Bản ghi › Tài liệu`; nút quay lại giữ bộ lọc.
- Mã màn hình (SCR-xx) chính thức do `06-UI-UX-SPEC.md` gán (xem OQ-05).

### 4.2. Panel P01 — nội dung bắt buộc

Mọi con số trên dashboard (card, trục biểu đồ, ô bảng, số trong alert) đều click được và mở panel chứa:

| # | Thành phần P01 | Nội dung | Nguồn dữ liệu |
|---|---|---|---|
| 1 | **Công thức tính** | Công thức dạng đọc được (tiếng Việt) + biểu thức kỹ thuật (như cột "Công thức" §2) | `ENT-Metric.formula` |
| 2 | **Nguồn dữ liệu** | Entity nguồn + loại tài liệu (ví dụ "ENT-Invoice — Danh sách hóa đơn T9") | `ENT-Metric.source_entity` + lineage |
| 3 | **Thời điểm cập nhật** | `computed_at` dạng `05/10/2026 08:30` + kỳ dữ liệu (`T9/2026`) + nhãn độ tươi | `ENT-MetricValue` |
| 4 | **Bản ghi gốc** | Danh sách bản ghi tham gia phép tính (có phân trang, tổng khớp con số) | Lineage `ENT-MetricValue` → entity |
| 5 | **Tài liệu gốc (nếu có)** | Link tới `ENT-SourceDocument` + trang + vùng tô; nếu nhập tay (C1) ghi "Nhập tay bởi … lúc …" | `ENT-ExtractedField.source_location` |

Kiểm tra: **không có con số "mồ côi"** — số không có lineage không được render (hiển thị `—` + "Chưa có nguồn").

### 4.3. Lineage

```
ENT-MetricValue ──(n)──► bản ghi entity (ENT-Invoice / ENT-Task / ENT-Employee / …)
                             └──► ENT-ExtractedField ──► ENT-ExtractionJob ──► ENT-SourceDocument (+ page, bbox)
                             └──► ENT-ExtractionReview (người duyệt, thời điểm)
```

- Lineage được ghi tại thời điểm commit qua Action Registry (không tính lại khi xem).
- Tổng các bản ghi gốc phải khớp giá trị metric (sai lệch do làm tròn chỉ ở hiển thị).

### 4.4. Drill-down theo quyền

Tuân thủ 02 §3.5 và §4:

| Tình huống | Hành vi |
|---|---|
| Bản ghi gốc thuộc trụ ngoài scope role | Hiển thị "Nguồn thuộc phạm vi khác — không có quyền xem" (không ẩn im lặng) |
| Role có mức view-agg cho trụ | Chỉ thấy panel P01 mục 1–3 + tổng hợp; không có bản ghi chi tiết, không link tài liệu |
| CEO/CFO drill-down metric dùng tài liệu #6 (lương cá nhân) | Dừng ở bản ghi tổng hợp; link file hiển thị "Tài liệu chứa dữ liệu lương cá nhân — chỉ HR Manager được mở" |
| Danh sách nhân sự trong drill-down HR | Hiển thị họ tên, phòng ban, chức danh, ngày vào/nghỉ; **không** hiển thị lương với role không có quyền |
| Mở tài liệu gốc chứa dữ liệu cá nhân | Ghi audit log; bị từ chối cũng ghi audit log |

---

## 5. Hiển thị dashboard theo role

### 5.1. Bảng role × trụ × metric

Mức quyền theo 02 §3.2/§3.7: **V** = view đầy đủ (gồm drill-down trong scope); **Agg** = view-agg (chỉ số tổng hợp); **—** = không hiển thị.

| Role | Dashboard chính | FIN (01–06) | CUS (01–05) | OPS (01–04) | HR (01–03) | Alert nhận | Mặc định khi đăng nhập |
|---|---|---|---|---|---|---|---|
| ROLE-01 CEO | Toàn bộ 4 trụ | V (6) | V (5) | V (4) | V (3; lương cá nhân chỉ tổng hợp) | 18 alert | Dashboard CEO 4 trụ |
| ROLE-02 CFO | Tài chính + Vận hành | V (6) | Agg (5) | V (4) | Agg (3; chi phí nhân sự tổng) | ALERT-FIN-*, ALERT-OPS-* | Trụ Tài chính mở rộng |
| ROLE-03 Sales Director | Khách hàng + doanh thu | Chỉ METRIC-FIN-01 (V) | V (5) | Agg (4) | — | ALERT-CUS-* | Trụ Khách hàng mở rộng |
| ROLE-04 HR Manager | Con người | Chỉ doanh thu tổng (Agg, phục vụ METRIC-HR-01) | — | V (4) | V (3) | ALERT-HR-* | Trụ Con người mở rộng |
| ROLE-05 Reviewer | Hàng chờ IDP | — | — | — | — | Không | Hàng chờ IDP (không có dashboard 4 trụ) |

- Chuyển vai trò demo phải render dashboard mới **≤ 2 giây** (01 §4).
- Metric ngoài scope **không render** (không hiển thị card khóa) để tránh gây nhiễu; API không trả giá trị (enforce ở backend).

### 5.2. Layout dashboard (desktop)

```
┌───────────────────────────────────────────────────────────┬──────────────┐
│ Vùng 1: Lời chào "Chào anh/chị …" + tóm tắt 1 câu AI (L1)│              │
├───────────────────────────────────────────────────────────┤  Panel AI    │
│ Vùng 2: 4 ô tổng quan trụ (FIN | CUS | OPS | HR)          │  (hỏi đáp,   │
│   mỗi ô: metric chủ lực + số alert đang mở + màu sức khỏe │   gợi ý L1,  │
├───────────────────────────────────────────────────────────┤   trạng thái │
│ Vùng 3: "Cần anh/chị quyết" — AlertCard (Critical trước)  │   AI P02)    │
├───────────────────────────────────────────────────────────┤              │
│ Vùng 4: Lưới MetricCard + biểu đồ chi tiết theo trụ       │              │
└───────────────────────────────────────────────────────────┴──────────────┘
```

- Ô tổng quan trụ có màu theo alert nặng nhất trong trụ (đỏ > vàng > xanh).
- Role chỉ thấy các ô trụ trong scope (§5.1); Reviewer được điều hướng thẳng tới hàng chờ IDP.
- Responsive: mobile xếp 1 cột, Panel AI chuyển thành nút nổi (chi tiết ở `06-UI-UX-SPEC.md`).

### 5.3. Component cần build

| Component | Mô tả | Yêu cầu |
|---|---|---|
| MetricCard | Số + sparkline + màu ngưỡng + nhãn độ tươi | Click → Metric Detail (P01); định dạng P04 |
| AlertCard | Mức độ + mô tả + hành động đề xuất (AI gợi ý L1) | Acknowledge/dismiss theo quyền; click → Metric Detail đã lọc |
| PillarSummary | Ô tổng quan 1 trụ | Màu theo alert nặng nhất |
| TrendChart | Bar / line / bar + line kế hoạch | Mọi điểm dữ liệu click được |
| GaugeChart | Gauge có vùng xanh/vàng/đỏ | Dùng cho FIN-03, CUS-05, OPS-03, HR-03 |
| BreakdownTable | Bảng phân rã drill-down | Phân trang; tổng khớp metric |
| LineagePanel | Panel P01 5 thành phần (§4.2) | Hiển thị thông báo chặn quyền (§4.4) |
| SourceViewer | Tài liệu gốc + vùng tô `source_location` | Mở đúng trang; ghi audit log |

---

## 6. Yêu cầu phi chức năng dashboard

| Yêu cầu | Ngưỡng | Nguồn |
|---|---|---|
| Drill-down số → tài liệu gốc | ≤ 3 click | 01 §4 |
| Chuyển vai trò dashboard | ≤ 2 giây | 01 §4 |
| Thời gian đến insight đầu tiên (CEO) | ≤ 10 giây | 01 §4 |
| Cập nhật dashboard sau khi Reviewer duyệt tài liệu | Metric phụ thuộc tính lại và hiển thị ở lần tải kế tiếp (không cache dữ liệu cũ) | 01 §2.2, §11 |
| Định dạng số/ngày | Theo P04 cho mọi nhãn, trục, tooltip | 01 §6 |
| Chuỗi hiển thị | Qua i18n, không hard-code | CLAUDE.md |

---

## 7. Open questions

| ID | Câu hỏi | Ảnh hưởng | Đề xuất tạm |
|---|---|---|---|
| OQ-01 | Các entity logic ENT-Opportunity, ENT-Decision, ENT-Project, ENT-Budget, ENT-CashBalance, ENT-Survey, ENT-Customer không nằm trong danh sách 12 entity hiện tại của `05-DATA-MODEL.md`. Mô hình hóa thành entity riêng hay lưu dạng giá trị KPI/MetricValue nhập từ #3, #5, #7? | Data model, IDP output mapping | Captain raise DEC; tạm thời coi là tên logic, `05` quyết định |
| OQ-02 | Ngưỡng vàng/đỏ của 18 metric là giá trị mặc định do writer đề xuất cho công ty ABC; cần xác nhận từ business owner | Alert, seed data | Dùng làm seed demo; chỉnh trong `08-DEMO-DATA-SPEC.md` |
| OQ-03 | METRIC-CUS-03 (NRR) cần dữ liệu doanh thu kỳ gốc (cùng quý năm trước), không có trong 7 tài liệu mẫu | Seed data | Seed dữ liệu lịch sử tổng hợp theo khách trong `08` |
| OQ-04 | METRIC-CUS-05 (NPS) chưa có tài liệu nguồn rõ ràng trong 7 tài liệu mẫu | Seed data, IDP | Đưa kết quả khảo sát NPS vào #7 KPI/OKR hoặc nhập tay C1 |
| OQ-05 | Mã SCR-xx cho Metric Detail / Source Viewer / Document Detail và EP-xx cho API metric/alert/lineage chưa được chốt | 06, 10 | `06-UI-UX-SPEC.md` và `10-API-SPECIFICATION.md` gán ID và tham chiếu ngược về spec này |
| OQ-06 | METRIC-OPS-04 và METRIC-HR-03 dùng chung ngưỡng "> 8 task mở"; cần xác nhận có tách định nghĩa quá tải theo vai trò công việc không | Công thức | Giữ chung một ngưỡng trong MVP |
| OQ-07 | Phạm vi alert OPS: theo 02 §3.3 ROLE-04 (HR) có view trụ OPS nhưng chỉ nhận `ALERT-HR-*`; ROLE-03 view-agg OPS không nhận `ALERT-OPS-*`. Giữ nguyên hay mở rộng? | Phân phối alert | Giữ đúng 02 §3.3 |

---

## 8. Liên kết

| Chủ đề | File |
|---|---|
| Phạm vi, KPI, nguyên tắc P01–P04 | `01-PROJECT-OVERVIEW.md` |
| Quyền theo role, data scoping | `02-PERSONAS-PERMISSIONS.md` |
| Pipeline IDP ghi vào metric/entity | `04-IDP-FEATURE-SPEC.md` |
| ENT-Metric, ENT-MetricValue, ENT-Alert | `05-DATA-MODEL.md` |
| Màn hình, component, design system | `06-UI-UX-SPEC.md` |
| Dữ liệu demo, giá trị ngưỡng seed | `08-DEMO-DATA-SPEC.md` |
| API metric / alert / lineage | `10-API-SPECIFICATION.md` |

---

## 9. Version

- **Version:** 1.0.0
- **Last updated:** 2026-10-17
- **Applies to:** Aureon Demo v1.0
- **Maintainer:** @CyEyes
