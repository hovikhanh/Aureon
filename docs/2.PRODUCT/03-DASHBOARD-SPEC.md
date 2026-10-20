# 03 — Dashboard Spec (Executive Dashboard F.O.C.U.S & Domain modules)

> Đặc tả **5 trụ F.O.C.U.S**, **32 metric** (31 metric trụ + METRIC-DQ-01), **32 alert**, quy tắc trạng thái trụ, business rules (BR), yêu cầu chức năng của các module domain (Finance, Sales, HR, Product, Risk), dashboard, insight, Briefing CEO và thông báo.
> **Canonical Source (DEC-144):** `_reference/SOURCE-BRD-v1.1.md` §2.3 (AI-R01..R12), §7.1 (FR-STR-04 SEI), §11.7 (FR-AIQ-01 grounding), §11.8 (cấu trúc insight), §12.2 (Daily Briefing), §5.2 (FR-ADM-05 phân loại). Kế thừa A-EMS (`SOURCE-BRD-v1.0` §II.2–II.9, §III.3, §III.5, §IV), UI/UX AI-EOS. Quyết định: DEC-125, DEC-126, DEC-127, DEC-132, DEC-143, DEC-147 (Initiative), DEC-148 (DQ, risk `proposed`), DEC-149 (insight 9 phần, phân loại), DEC-152 (TTFT), DEC-154 (đổi tên cột).
> Phụ thuộc: `01-PROJECT-OVERVIEW.md`, `02-PERSONAS-PERMISSIONS.md`. ID theo registry `00-INDEX.md` §4. Endpoint do `10-API-SPECIFICATION.md` sở hữu — file này không dùng số EP.

---

## 1. Kiến trúc 5 trụ

### 1.1. Tổng quan

| Trụ | Tên | Câu hỏi lãnh đạo | Metric | Module nguồn chính | Role xem đầy đủ (02 §5.4) |
|---|---|---|---|---|---|
| **PIL-F** | Finance | "Có đủ tiền, và đang kiếm/tiêu tiền hiệu quả không?" | METRIC-FIN-01..07 (7) | `finance` (+ `sales` cho mục tiêu) | CEO, CFO |
| **PIL-O** | Operations & People | "Có đủ người và vận hành có ổn không?" | METRIC-OPS-01..03, METRIC-HR-01..04 (7) | `execution`, `hr` | CEO, HR_MANAGER |
| **PIL-C** | Customer & Growth | "Có đang giành và giữ được khách hàng không?" | METRIC-CUS-01..06 (6) | `sales`, `finance` (hóa đơn), `product` (NPS) | CEO, VP_SALES |
| **PIL-U** | Product & Innovation | "Sản phẩm có đang tiến lên và được dùng thật không?" | METRIC-PRD-01..05 (5) | `product` | CEO, CPO |
| **PIL-S** | Strategy & Risk | "Điều gì có thể làm hỏng kế hoạch, và đã xử lý tới đâu?" | METRIC-RSK-01..06 (6) | `risk`, `execution` (Initiative) | CEO, CFO, RISK_MANAGER |
| | | | **31** | | |
| *(nền tảng)* | Data Quality | "Dữ liệu có đáng tin để quyết định không?" | METRIC-DQ-01 (1) | `platform` (+ `idp`) | Mọi role có `dashboard:read` (theo scope) |
| | | | **32** | | |

Mỗi metric có đúng **một** alert cùng số (`ALERT-FIN-03` ↔ `METRIC-FIN-03`, `ALERT-DQ-01` ↔ `METRIC-DQ-01`) — §3 → **32 alert**. METRIC-DQ-01 không thuộc trụ và **không** tham gia quy tắc trạng thái trụ (§4); hiển thị ở dải "Độ tin cậy dữ liệu" trên Dashboard và trên từng metric.

### 1.2. Luồng dữ liệu vào dashboard

```
Nhập tay (C1) / IDP commit (Action Registry) / thao tác trong workspace
        ↓  ghi vào bảng của module domain (schema riêng — DEC-125)
Transactional Outbox → domain event (EVT-*, DEC-126)
        ↓
Metric store (module platform): tính lại các ENT-MetricValue phụ thuộc
        ↓  đánh giá ngưỡng → ENT-Alert (EVT-platform.alert_raised)
        ↓
Dashboard domain (5 endpoint /{domain}/dashboard, cache 60s) + Insight (ai_core) + Briefing
        ↓
UI: thẻ trụ, chi tiết metric (SCR-07), lineage tới trang tài liệu (P01)
```

- **Metric store là nguồn định nghĩa duy nhất** (AI-EOS §4.1 "semantic layer"): công thức, nguồn, bộ lọc khai báo một lần trong `ENT-Metric`; dashboard, Briefing và tool AI đều đọc `ENT-MetricValue` — AI **không** tự tính lại metric (P05).
- Metric được tính lại **theo event** (cột "Tính lại khi") và **theo lịch** (job Celery beat hằng ngày 01:00 cho metric phụ thuộc thời gian, vd. runway, quá hạn).
- Frontend **không** tự tính KPI (A-EMS §VII.4); chỉ hiển thị `summary` và chuỗi `*_trend`.

### 1.3. Quy ước đặc tả metric

| Thuộc tính | Quy ước |
|---|---|
| Kỳ (`period`) | `current_month` (mặc định) / `current_quarter` / `ytd`; Finance thêm `custom` (`start_date`, `end_date`) — FR-DSH-05. Metric có cửa sổ riêng (rolling 12 tháng, 3 kỳ…) ghi rõ trong công thức |
| Tiền | Lưu số nguyên VND + `currency`; hiển thị rút gọn `1,2 tỷ`, `850 tr` (P04) |
| Tỷ lệ | Hậu tố `_pct`, 1 chữ số thập phân, hiển thị `12,5%` |
| Ngưỡng | **Biến cấu hình** (yêu cầu NFR của A-EMS) tên `THR_<METRIC_ID>_WARN` / `THR_<METRIC_ID>_CRIT` (vd. `THR_FIN_03_CRIT`) lưu ở `ENT-SystemSetting`, ADMIN sửa qua `dashboard:admin`; giá trị trong bảng là **mặc định** |
| Hướng | `↑` = càng cao càng tốt (vi phạm khi **thấp hơn** ngưỡng); `↓` = càng thấp càng tốt (vi phạm khi **cao hơn** ngưỡng) |
| Trạng thái metric | `ok` / `warning` / `critical` / `no_data` (thiếu dữ liệu đầu vào hoặc mẫu số = 0) |
| Độ tươi | Mỗi `ENT-MetricValue` có `computed_at` và `source_updated_at`; quá `FRESHNESS_STALE_DAYS` (mặc định 7 ngày cho metric tháng, 2 ngày cho metric ngày) → nhãn "dữ liệu cũ" (AI-EOS §4.1) |
| Chất lượng dữ liệu | `data_quality_pct` của từng metric = thành phần **completeness** của METRIC-DQ-01 (§2.6) trên tập bản ghi cấu thành; một ngưỡng thống nhất với METRIC-DQ-01 (DEC-148): < 80 → nhãn "chất lượng thấp", < 60 → nhãn đỏ (vd. "Doanh thu T9 mới có 62% hóa đơn được nhập") |
| Phân loại dữ liệu | Mỗi metric/insight mang `data_classification` cao nhất của bản ghi cấu thành (05 C19, §10); quyết định model AI được dùng (§7.4) |
| "3 kỳ gần nhất" | 3 kỳ cùng loại liền trước kỳ đang xét, không gồm kỳ đang xét |
| Biểu đồ | `kpi` (số lớn + delta), `line`, `bar`, `stacked-bar`, `gauge`, `heatmap`, `funnel`, `donut`; mặc định trend 12 kỳ |

---

## 2. Đặc tả 32 metric

Ghi chú chung:
- Theo DEC-125, module `platform` **không đọc bảng** của module khác: mỗi module domain cung cấp hàm tính (metric provider) qua service interface; `platform` lưu `ENT-Metric` (định nghĩa) và `ENT-MetricValue` (giá trị theo kỳ, kèm `source_record_refs` cho lineage `ENT-DataLineage`).
- Cột "Ngưỡng" ghi **giá trị mặc định** của biến `THR_<id>_WARN` / `THR_<id>_CRIT` (§1.3). "Δ3k" = so với trung bình 3 kỳ gần nhất.

### 2.1. PIL-F — Finance (7)

| ID | Tên | Công thức | Đơn vị | Nguồn entity | Tính lại khi | Hướng | Warning (mặc định) | Critical (mặc định) | Biểu đồ |
|---|---|---|---|---|---|---|---|---|---|
| METRIC-FIN-01 | Doanh thu vs kế hoạch | `revenue_attainment_pct = SUM(Revenue.amount, kỳ) / SalesTarget.target_amount(scope=team, kỳ) × 100`; hiển thị kèm doanh thu tuyệt đối và tăng trưởng cùng kỳ `(DT kỳ − DT cùng kỳ năm trước) / DT cùng kỳ năm trước × 100` | % (+ VND) | ENT-Revenue, ENT-SalesTarget | Ghi/sửa Revenue; `EVT-finance.invoice_paid`; đổi SalesTarget | ↑ | < 90 (thấp hơn KH > 10%) | < 80 | `kpi` + `line` thực tế vs kế hoạch 12 kỳ |
| METRIC-FIN-02 | Biên lợi nhuận gộp | `gross_margin_pct = (DT kỳ − Giá vốn kỳ) / DT kỳ × 100`; Giá vốn = SUM(Expense.amount, category=`cogs`) | % | ENT-Revenue, ENT-Expense | Ghi Revenue/Expense | ↑ | Giảm > 3 điểm % so Δ3k | Giảm > 5 điểm % so Δ3k | `kpi` + `line` |
| METRIC-FIN-03 | Cash runway | BR-FIN-02 (`closing_balance` kỳ gần nhất ÷ `burn_thang` BR-FIN-01); `null` theo BR-FIN-03 | tháng (1 số thập phân) | ENT-CashPosition, ENT-Revenue, ENT-Expense | Ghi CashPosition/Revenue/Expense; job hằng ngày | ↑ | < 12 | < 6 | `gauge` + `line` số dư tiền mặt |
| METRIC-FIN-04 | DSO | `DSO = Phải thu cuối kỳ / DT kỳ × số ngày của kỳ`; Phải thu = SUM(Invoice.total − Invoice.paid_amount) với `status ∈ {issued, partially_paid, overdue}` | ngày | ENT-Invoice, ENT-Revenue | Tạo/cập nhật Invoice; `EVT-finance.invoice_paid` | ↓ | Tăng > 15% so Δ3k | Tăng > 30% so Δ3k | `kpi` + `line` |
| METRIC-FIN-05 | Công nợ quá hạn | `overdue_ar_pct = SUM(phải thu có due_date < hôm nay) / Tổng phải thu × 100`; hiển thị kèm aging 1–30 / 31–60 / 61–90 / > 90 ngày | % (+ VND) | ENT-Invoice | Cập nhật Invoice; job hằng ngày | ↓ | > 15 | > 25 | `kpi` + `stacked-bar` aging |
| METRIC-FIN-06 | Chênh lệch ngân sách | `budget_variance_pct = MAX theo phòng ban [(Thực chi − Ngân sách) / Ngân sách × 100]` (kỳ quý); `budget_utilization_pct` theo BR-FIN-05 hiển thị từng phòng ban | % | ENT-Budget, ENT-Expense, ENT-Department | Ghi Expense; đổi Budget; `EVT-finance.budget_exceeded` | ↓ | > 0 (utilization > 100% ở bất kỳ phòng ban) | > 10 | `bar` theo phòng ban (thực chi vs ngân sách) |
| METRIC-FIN-07 | Net burn vs dự báo | `burn_variance_pct = (Net burn dự kiến tháng − Net burn dự báo đầu tháng) / |Net burn dự báo| × 100`; Net burn dự kiến = (Chi MTD − Thu MTD) × số ngày tháng / số ngày đã qua; dự báo = `ForecastLine` kịch bản `base` bản đầu tháng | % | ENT-Revenue, ENT-Expense, ENT-Forecast, ENT-ForecastLine | Job hằng ngày (FR-FIN-08); `EVT-finance.forecast_updated` | ↓ | > 10 | > 25 | `line` dự kiến vs dự báo |

### 2.2. PIL-O — Operations & People (7)

| ID | Tên | Công thức | Đơn vị | Nguồn entity | Tính lại khi | Hướng | Warning (mặc định) | Critical (mặc định) | Biểu đồ |
|---|---|---|---|---|---|---|---|---|---|
| METRIC-OPS-01 | Task đúng hạn | `on_time_task_pct = COUNT(Task đến hạn trong kỳ, completed_at ≤ due_date) / COUNT(Task có due_date trong kỳ) × 100` | % | ENT-Task | Cập nhật Task; `EVT-execution.task_overdue` | ↑ | < 80 | < 65 | `kpi` + `bar` theo phòng ban |
| METRIC-OPS-02 | Dự án trễ | `late_project_pct = COUNT(Project đang chạy có (planned_progress_pct − actual_progress_pct) > 10) / COUNT(Project đang chạy) × 100`; `planned_progress_pct` nội suy tuyến tính theo `start_date`–`end_date` | % | ENT-Project, ENT-Task | Cập nhật Task/Project; job hằng ngày | ↓ | > 20 | > 35 | `kpi` + danh sách dự án trễ |
| METRIC-OPS-03 | Thực thi quyết định | `decision_execution_pct = COUNT(Task sinh từ Decision/Meeting, đến hạn trong kỳ, status=done) / COUNT(Task sinh từ Decision/Meeting, đến hạn trong kỳ) × 100` | % | ENT-Decision, ENT-Meeting, ENT-Task | Cập nhật Task; `EVT-idp.document_committed` (biên bản → task, UC-06) | ↑ | < 70 | < 50 | `kpi` + `funnel` quyết định → task → xong |
| METRIC-HR-01 | Doanh thu / nhân sự | `revenue_per_head = SUM(Revenue.amount, 12 tháng rolling) / headcount active bình quân 12 tháng`; so với kế hoạch `HR_REVENUE_PER_HEAD_PLAN` | VND/người/năm | ENT-Revenue, ENT-Employee | Ghi Revenue; `EVT-hr.employee_onboarded` / `employee_terminated` | ↑ | Thấp hơn kế hoạch > 15% | Thấp hơn kế hoạch > 25% | `kpi` + `line` |
| METRIC-HR-02 | Turnover năm hóa | BR-HR-01 | % | ENT-Employee | `EVT-hr.employee_terminated`; job hằng tháng | ↓ | ≥ 15 | ≥ 20 | `kpi` + `line` 12 tháng + `bar` theo phòng ban |
| METRIC-HR-03 | Quá tải | `overload_pct = COUNT(Employee active có workload_pct > 110 trong 2 tuần liên tiếp) / COUNT(Employee active) × 100`; `workload_pct (tuần) = SUM(Task.estimate_hours của task mở được giao trong tuần) / capacity_hours_per_week (mặc định 40) × 100` | % (+ số người) | ENT-Task, ENT-Employee | Giao/cập nhật Task; job hằng tuần | ↓ | > 10 | > 20 | `heatmap` người × tuần (SCR-19) |
| METRIC-HR-04 | Kế hoạch tuyển dụng trễ | `delayed_hiring_plans = COUNT(HiringPlan status ∈ {approved, in_progress}, target_date < hôm nay, filled < headcount)`; chia theo số ngày trễ | số kế hoạch | ENT-HiringPlan | Cập nhật HiringPlan; job hằng ngày; `EVT-hr.hiring_plan_delayed` | ↓ | ≥ 1 kế hoạch trễ 1–45 ngày | ≥ 1 kế hoạch trễ > 45 ngày (DEC-143; event FR-HR-04 vẫn phát khi > 30 ngày) | `kpi` + danh sách theo phòng ban |

### 2.3. PIL-C — Customer & Growth (6)

| ID | Tên | Công thức | Đơn vị | Nguồn entity | Tính lại khi | Hướng | Warning (mặc định) | Critical (mặc định) | Biểu đồ |
|---|---|---|---|---|---|---|---|---|---|
| METRIC-CUS-01 | Pipeline coverage | BR-SAL-04: `coverage_x = SUM(Deal.deal_value, stage mở, expected_close_date trong quý) / SalesTarget.target_amount(quarter, team)`; hiển thị kèm coverage có trọng số `SUM(weighted_value) / target` (BR-SAL-02) | lần (x, 1 số thập phân) | ENT-Deal, ENT-SalesTarget | Tạo/sửa Deal; chuyển giai đoạn; đổi SalesTarget | ↑ | < 2,8 (2,5–< 2,8; OK ≥ 2,8 — DEC-143) | < 2,5 | `kpi` + `funnel` theo giai đoạn |
| METRIC-CUS-02 | Win rate | BR-SAL-03: `win_rate_pct = won / (won + lost) × 100` trong kỳ | % | ENT-Deal, ENT-DealStageHistory | `EVT-sales.deal_closed_won` / `deal_closed_lost` | ↑ | Giảm > 10 điểm % so Δ3k | Giảm > 20 điểm % so Δ3k | `kpi` + `line` |
| METRIC-CUS-03 | NRR | `nrr_pct = DT kỳ này từ khách đã có doanh thu ở kỳ trước / DT kỳ trước của chính các khách đó × 100` (theo `Revenue.client_id`) | % | ENT-Revenue, ENT-Client | Ghi Revenue; `EVT-finance.invoice_paid` | ↑ | < 100 | < 90 | `kpi` + `line` |
| METRIC-CUS-04 | Tập trung doanh thu top 5 | `top5_concentration_pct = SUM(DT 5 khách lớn nhất, 12 tháng rolling) / SUM(DT, 12 tháng rolling) × 100` | % | ENT-Revenue, ENT-Client | Ghi Revenue | ↓ | > 50 | > 65 | `donut` top 5 vs còn lại |
| METRIC-CUS-05 | NPS | `nps = AVG có trọng số MAU của ProductMetric.nps (kỳ gần nhất mỗi sản phẩm)`; NPS sản phẩm = %promoter − %detractor (−100..100) | điểm | ENT-ProductMetric | Ghi ProductMetric | ↑ | < 30 | < 0 | `kpi` + `bar` theo sản phẩm |
| METRIC-CUS-06 | Chu kỳ bán TB | `avg_sales_cycle_days = AVG(closed_at − created_at)` của deal `closed_won` trong kỳ (FR-SAL-07) | ngày | ENT-Deal, ENT-DealStageHistory | `EVT-sales.deal_closed_won` | ↓ | Tăng > 20% so Δ3k | Tăng > 40% so Δ3k | `kpi` + `bar` ngày TB theo giai đoạn |

Điều kiện đánh giá METRIC-CUS-02: chỉ đánh giá ngưỡng khi kỳ có ≥ `WIN_RATE_MIN_CLOSED_DEALS` (mặc định 10) deal đã đóng; ít hơn → `ok` kèm nhãn "mẫu nhỏ" (A-EMS §II.8).

### 2.4. PIL-U — Product & Innovation (5)

| ID | Tên | Công thức | Đơn vị | Nguồn entity | Tính lại khi | Hướng | Warning (mặc định) | Critical (mặc định) | Biểu đồ |
|---|---|---|---|---|---|---|---|---|---|
| METRIC-PRD-01 | Adoption / MAU | `mau = SUM(ProductMetric.mau, kỳ gần nhất, sản phẩm launched)`; `adoption_pct = AVG(ProductMetric.adoption_pct)` có trọng số MAU | người dùng (+ %) | ENT-ProductMetric, ENT-Product | Ghi ProductMetric | ↑ | MAU giảm > 10% so Δ3k | MAU giảm > 20% so Δ3k | `kpi` + `line` theo sản phẩm |
| METRIC-PRD-02 | Churn | `churn_rate_pct` = ProductMetric.churn_rate_pct (từng sản phẩm; trụ lấy giá trị xấu nhất) | % | ENT-ProductMetric | Ghi ProductMetric; `EVT-product.metric_anomaly` | ↓ | Tăng > 25% tương đối so Δ3k **và** ≥ 2% | BR-PRD-01: tăng > 50% tương đối so Δ3k **và** ≥ 2% | `line` + điểm bất thường |
| METRIC-PRD-03 | Retention 30 ngày | `retention_30d_pct` = ProductMetric.retention_30d_pct (trọng số MAU) | % | ENT-ProductMetric | Ghi ProductMetric | ↑ | < 40 | < 25 | `line` |
| METRIC-PRD-04 | Roadmap đúng tiến độ | `roadmap_on_track_pct = COUNT(RoadmapItem của quý, không trễ) / COUNT(RoadmapItem của quý) × 100`; "trễ" = `target_date < hôm nay` và `status ≠ done`, hoặc `done` sau `target_date` | % | ENT-RoadmapItem | Cập nhật RoadmapItem; job hằng ngày | ↑ | < 70 (trễ > 30% — A-EMS) | < 50 | `kpi` + `stacked-bar` theo sản phẩm |
| METRIC-PRD-05 | Tính năng release trong kỳ | `features_released = COUNT(Feature status=released, released_at trong kỳ)`; `release_attainment_pct = features_released / COUNT(Feature planned_release trong kỳ) × 100` | số tính năng (+ %) | ENT-Feature, ENT-Release | `EVT-product.feature_released` | ↑ | attainment < 70 | attainment < 40 | `bar` theo tháng |

### 2.5. PIL-S — Strategy & Risk (6)

| ID | Tên | Công thức | Đơn vị | Nguồn entity | Tính lại khi | Hướng | Warning (mặc định) | Critical (mặc định) | Biểu đồ |
|---|---|---|---|---|---|---|---|---|---|
| METRIC-RSK-01 | Rủi ro high/critical đang mở | `COUNT(Risk level ∈ {high, critical}, status ∉ {closed, accepted})` | số rủi ro | ENT-Risk | `EVT-risk.risk_identified` / `risk_level_changed` / `risk_mitigated` | ↓ | ≥ 1 rủi ro `high` | ≥ 1 rủi ro `critical` | `kpi` + `heatmap` 5×5 likelihood × impact |
| METRIC-RSK-02 | Rủi ro high chưa có chủ | `COUNT(Risk level ∈ {high, critical}, owner_id IS NULL, status mở)` | số rủi ro | ENT-Risk | `EVT-risk.risk_identified`; gán owner | ↓ | ≥ 1 rủi ro `medium` chưa có chủ > 7 ngày | ≥ 1 (A-EMS: "chờ phân công") | `kpi` + danh sách |
| METRIC-RSK-03 | Rủi ro high > 30 ngày không có mitigation | `COUNT(Risk level ≥ high, mở > 30 ngày, không có Mitigation status=in_progress)` | số rủi ro | ENT-Risk, ENT-Mitigation | Cập nhật Mitigation; job hằng ngày | ↓ | ≥ 1 (A-EMS) | ≥ 1 rủi ro `critical` thỏa điều kiện | `kpi` + danh sách |
| METRIC-RSK-04 | Điểm rủi ro tổng hợp | `risk_index = SUM(risk_score của rủi ro mở) / COUNT(rủi ro mở)` (thang 1–25); trend theo tuần | điểm (1 số thập phân) | ENT-Risk, ENT-RiskAssessment | Mọi `EVT-risk.*` | ↓ | ≥ 10 (10–< 15; OK < 10 — DEC-143) | ≥ 15 | `line` + `heatmap` |
| METRIC-RSK-05 | Biện pháp quá hạn | `COUNT(Mitigation status ∈ {planned, in_progress}, due_date < hôm nay)` | số biện pháp | ENT-Mitigation | Cập nhật Mitigation; job hằng ngày | ↓ | ≥ 1 | ≥ 5, hoặc ≥ 1 thuộc rủi ro `critical` | `kpi` + danh sách |
| METRIC-RSK-06 | Strategy execution index (SEI) | **Theo Initiative (BRD FR-STR-04, GAP C-02, DEC-147):** `sei_pct = Σ(Initiative.weight_pct × on_track) / Σ(Initiative.weight_pct) × 100` trên Initiative `status ∈ {active, at_risk}` có kỳ giao với kỳ xét; `on_track = 1` khi `progress_pct ≥ expected_progress_pct × 0,9` (`SEI_ON_TRACK_RATIO`), `expected_progress_pct` nội suy tuyến tính `start_date → planned_end_date`; `progress_pct` từ Milestone/Task (05 ENT-Initiative). Σ trọng số = 0 → trọng số bằng nhau. Không có Initiative → `no_data` | % | ENT-Initiative, ENT-Milestone, ENT-Task, ENT-Objective | Cập nhật Task/Milestone/Initiative; `EVT-execution.kpi_measured`; job hằng tuần | ↑ | < 70 (AI-EOS §4.3) | < 50 | `gauge` + cây Objective → Initiative |

### 2.6. Nền tảng — Data Quality (1) — DEC-148

| ID | Tên | Công thức | Đơn vị | Nguồn entity | Tính lại khi | Hướng | Warning (mặc định) | Critical (mặc định) | Biểu đồ |
|---|---|---|---|---|---|---|---|---|---|
| METRIC-DQ-01 | Data Quality Score | **Trung bình có trọng số:** `dq_score = completeness × 0,3 + accuracy × 0,4 + freshness × 0,3` (thang 0–100, 1 số thập phân), tính theo `scope_type ∈ {company, department}` cho các domain cốt lõi (finance, sales, hr, product, risk, execution) trong kỳ | điểm 0–100 | ENT-MetricValue (`data_quality_score`), ENT-ImportBatch (`quality_score`), ENT-ExtractedField, bản ghi domain | `EVT-idp.document_committed` / `document_rolled_back`; ghi bản ghi domain; job hằng ngày 01:00 | ↑ | < 80 | < 60 | `gauge` + `bar` theo domain/phòng ban |

Thành phần (mỗi thành phần 0–100):

| Thành phần | Trọng số | Công thức | Ghi chú |
|---|---|---|---|
| `completeness` | 0,3 (`DQ_WEIGHT_COMPLETENESS`) | `bản ghi trong kỳ có đủ trường bắt buộc / tổng bản ghi trong kỳ × 100` | Trường bắt buộc theo schema entity (05) và ExtractionSchema (04) |
| `accuracy` | 0,4 (`DQ_WEIGHT_ACCURACY`) | `(1 − (bản ghi lỗi validate nghiệp vụ + field IDP bị reviewer sửa/từ chối) / tổng bản ghi và field được kiểm) × 100` | Lỗi validate theo FR-DC-14; batch import dùng `ENT-ImportBatch.quality_score` |
| `freshness` | 0,3 (`DQ_WEIGHT_FRESHNESS`) | `nguồn dữ liệu cập nhật đúng hạn / tổng nguồn × 100`; đúng hạn = `source_updated_at` trong SLA BO-02 (tài chính ≤ 24 giờ, task/sales ≤ 1 giờ, còn lại `FRESHNESS_STALE_DAYS`) | Dùng chung nhãn "dữ liệu cũ" §1.3 |

- Trọng số là cấu hình, tổng phải bằng 1 (kiểm khi lưu). Ngưỡng `THR_DQ_01_WARN = 80`, `THR_DQ_01_CRIT = 60`; mục tiêu BO-09 ≥ 90 (01 §4.1).
- Domain không có bản ghi trong kỳ bị loại khỏi trung bình (không kéo điểm về 0); mọi domain trống → `no_data`.
- Lineage của METRIC-DQ-01 trỏ tới danh sách bản ghi thiếu trường / lỗi / nguồn quá hạn (P01).


---

## 3. Đặc tả 32 alert

### 3.1. Quy tắc chung

| # | Quy tắc |
|---|---|
| 1 | Alert sinh khi metric cùng số chuyển sang `warning` hoặc `critical` (ngưỡng §2); tạo `ENT-Alert` và phát `EVT-platform.alert_raised` |
| 2 | **Khử trùng lặp**: tối đa 1 alert **mở** cho mỗi cặp (metric, phạm vi — vd. phòng ban/sản phẩm/rủi ro); metric xấu đi `warning → critical` thì nâng mức alert hiện có, không tạo mới |
| 3 | **Tần suất tối đa**: alert sinh bởi job hằng ngày tối đa 1 lần/ngày/phạm vi (vd. ALERT-FIN-07 — FR-FIN-08) |
| 4 | **Tự đóng**: metric về `ok` trong `ALERT_AUTO_RESOLVE_PERIODS` (mặc định 1) lần tính liên tiếp → alert `resolved` (ghi `resolved_reason = auto`) |
| 5 | Vòng đời: `open → acknowledged → resolved`, hoặc `open → dismissed` (bắt buộc lý do). Acknowledge/dismiss cần `dashboard:write` trong trụ (02 §5.3) |
| 6 | Người nhận = role có quyền xem trụ (02 §5.4) + cột "Nhận thêm"; kênh in-app (FR-NTF-01), email cho `critical` khi bật FR-NTF-02 |
| 7 | Mỗi alert có link tới SCR-07 (chi tiết metric + lineage) và nút "Hỏi AI vì sao" (Panel AI với ngữ cảnh alert) |
| 8 | Alert `critical` luôn xuất hiện trong Briefing (§7) cho tới khi acknowledged |
| 9 | Rủi ro ở trạng thái `proposed` (tự sinh, chờ owner xác nhận — DEC-148) **không** sinh ALERT-RSK-01..05; chỉ hiện ở hàng chờ "Rủi ro đề xuất" của RISK_MANAGER/owner |

### 3.2. Bảng alert

| Alert | Metric | Trụ | Điều kiện warning | Điều kiện critical | Nhận thêm (ngoài role xem trụ) | Hành động gợi ý |
|---|---|---|---|---|---|---|
| ALERT-FIN-01 | METRIC-FIN-01 | F | Đạt < 90% kế hoạch | < 80% | VP_SALES | Xem deal sắp đóng, hỏi AI nguyên nhân |
| ALERT-FIN-02 | METRIC-FIN-02 | F | Biên LN gộp giảm > 3 điểm % so Δ3k | > 5 điểm % | — | Xem chi phí giá vốn theo hạng mục |
| ALERT-FIN-03 | METRIC-FIN-03 | F | Runway < 12 tháng | < 6 tháng | — | What-if runway (BR-FIN-06), rà chi phí |
| ALERT-FIN-04 | METRIC-FIN-04 | F | DSO tăng > 15% so Δ3k | > 30% | VP_SALES | Danh sách khách chậm trả |
| ALERT-FIN-05 | METRIC-FIN-05 | F | Công nợ quá hạn > 15% | > 25% | VP_SALES | Aging, giao task thu hồi nợ |
| ALERT-FIN-06 | METRIC-FIN-06 | F | Phòng ban vượt ngân sách (> 100%) | Vượt > 10% | MANAGER của phòng ban | Xem chi phí phòng ban; phát `EVT-finance.budget_exceeded` |
| ALERT-FIN-07 | METRIC-FIN-07 | F | Net burn dự kiến vượt dự báo > 10% | > 25% | — | Xem chi phí bất thường tháng; phát `EVT-finance.burn_over_forecast` |
| ALERT-OPS-01 | METRIC-OPS-01 | O | Task đúng hạn < 80% | < 65% | MANAGER (phòng ban dưới ngưỡng) | Workload heatmap, phân lại task |
| ALERT-OPS-02 | METRIC-OPS-02 | O | Dự án trễ > 20% | > 35% | MANAGER chủ dự án | Danh sách dự án trễ |
| ALERT-OPS-03 | METRIC-OPS-03 | O | Thực thi quyết định < 70% | < 50% | — | Danh sách quyết định chưa xong |
| ALERT-HR-01 | METRIC-HR-01 | O | DT/nhân sự thấp hơn KH > 15% | > 25% | CFO | Xem headcount vs doanh thu |
| ALERT-HR-02 | METRIC-HR-02 | O | Turnover ≥ 15%/năm | ≥ 20% | — | Phòng ban có nghỉ việc cao |
| ALERT-HR-03 | METRIC-HR-03 | O | Quá tải > 10% nhân sự | > 20% | MANAGER của người quá tải | F5: gợi ý chuyển task (L1) |
| ALERT-HR-04 | METRIC-HR-04 | O | Kế hoạch trễ 1–45 ngày | Trễ > 45 ngày (DEC-143) | CFO, RISK_MANAGER | Xem kế hoạch; rủi ro tự sinh (BR-RSK-03) |
| ALERT-CUS-01 | METRIC-CUS-01 | C | Coverage < 2,8x | < 2,5x (DEC-143) | CEO | Deal cần thúc đẩy |
| ALERT-CUS-02 | METRIC-CUS-02 | C | Win rate giảm > 10 điểm % so Δ3k (≥ 10 deal đã đóng) | > 20 điểm % | — | Phân tích deal thua |
| ALERT-CUS-03 | METRIC-CUS-03 | C | NRR < 100% | < 90% | CFO | Khách giảm chi tiêu |
| ALERT-CUS-04 | METRIC-CUS-04 | C | Top 5 > 50% doanh thu | > 65% | CFO, RISK_MANAGER | Rủi ro tập trung khách hàng |
| ALERT-CUS-05 | METRIC-CUS-05 | C | NPS < 30 | < 0 | CPO | Phản hồi khách theo sản phẩm |
| ALERT-CUS-06 | METRIC-CUS-06 | C | Chu kỳ bán tăng > 20% so Δ3k | > 40% | — | Giai đoạn bị tắc |
| ALERT-PRD-01 | METRIC-PRD-01 | U | MAU giảm > 10% so Δ3k | > 20% | — | Sản phẩm giảm sử dụng |
| ALERT-PRD-02 | METRIC-PRD-02 | U | Churn tăng > 25% tương đối và ≥ 2% | BR-PRD-01 (> 50% và ≥ 2%) | RISK_MANAGER, VP_SALES | Điều tra; phát `EVT-product.metric_anomaly` (chỉ mức critical) |
| ALERT-PRD-03 | METRIC-PRD-03 | U | Retention 30 ngày < 40% | < 25% | — | Phân tích cohort |
| ALERT-PRD-04 | METRIC-PRD-04 | U | Roadmap đúng tiến độ < 70% | < 50% | — | Hạng mục trễ |
| ALERT-PRD-05 | METRIC-PRD-05 | U | Release đạt < 70% kế hoạch | < 40% | — | Tính năng bị lùi |
| ALERT-RSK-01 | METRIC-RSK-01 | S | Có rủi ro `high` mở | Có rủi ro `critical` mở | CFO; owner rủi ro | Mở sổ rủi ro, what-if |
| ALERT-RSK-02 | METRIC-RSK-02 | S | Rủi ro `medium` chưa có chủ > 7 ngày | Rủi ro ≥ `high` chưa có chủ | — | Gán chủ sở hữu |
| ALERT-RSK-03 | METRIC-RSK-03 | S | Rủi ro ≥ `high` mở > 30 ngày không có mitigation `in_progress` | Như trên với `critical` | Owner rủi ro | Tạo biện pháp |
| ALERT-RSK-04 | METRIC-RSK-04 | S | Điểm rủi ro TB ≥ 10 | ≥ 15 (DEC-143) | — | Heatmap |
| ALERT-RSK-05 | METRIC-RSK-05 | S | ≥ 1 biện pháp quá hạn | ≥ 5 hoặc thuộc rủi ro `critical` | Owner biện pháp | Cập nhật tiến độ |
| ALERT-RSK-06 | METRIC-RSK-06 | S | SEI < 70% | < 50% | Owner Initiative trễ | Xem Initiative lệch tiến độ, tạo task gỡ |
| ALERT-DQ-01 | METRIC-DQ-01 | — (nền tảng) | DQ Score < 80 | < 60 | ADMIN; người phụ trách domain có điểm thấp nhất | Mở danh sách bản ghi thiếu/lỗi/quá hạn, nạp lại dữ liệu (UC-07) |

---

## 4. Trạng thái trụ (FR-DSH-02)

| Trạng thái | Điều kiện (đánh giá theo thứ tự) |
|---|---|
| `critical` | Có **ít nhất một** metric của trụ ở `critical` |
| `warning` | Không có `critical`, có ít nhất một metric `warning` |
| `ok` | Mọi metric có dữ liệu đều `ok` (A-EMS: trạng thái trụ = mức cao nhất trong các ngưỡng đang vi phạm) |
| `no_data` | ≥ 50% metric của trụ ở `no_data` (`PILLAR_NO_DATA_RATIO`); hiển thị "Chưa đủ dữ liệu" + CTA nạp dữ liệu (UC-07) |
| `unavailable` | Module nguồn lỗi/timeout — chỉ thẻ trụ đó báo "Dịch vụ tạm thời không khả dụng" (FR-DSH-07) |

Quy tắc phụ:
- METRIC-DQ-01 không thuộc trụ nào nên không vào quy tắc trên; DQ < 60 hạ `confidence` của insight trụ liên quan (§7.1 #6).
- Metric `no_data` không làm trụ xấu đi, nhưng được đếm và hiển thị "x/y chỉ số có dữ liệu".
- Thẻ trụ hiển thị: trạng thái (biểu tượng ● ◐ ○ kèm màu — không dùng màu đơn thuần), KPI chính (metric đầu tiên của trụ, vd. METRIC-FIN-01), 2 metric xấu nhất, số alert mở, thời điểm cập nhật.
- Trạng thái trụ được ghi lịch sử theo ngày để vẽ dải trạng thái 30 ngày.

---

## 5. Business rules (BR)

### 5.1. Finance

| Mã | Quy tắc | Ví dụ |
|---|---|---|
| BR-FIN-01 | `burn_thang` = trung bình `(tổng chi − tổng thu)` của **3 kỳ tháng gần nhất**, **chỉ tính kỳ dương**; kỳ có lãi (chi − thu ≤ 0) không vào tử số lẫn mẫu số. Không có kỳ dương nào → `burn_thang = 0` | (chi − thu) 3 kỳ: 400 tr, 500 tr, 600 tr → burn 500 tr |
| BR-FIN-02 | `runway_months = closing_balance (ENT-CashPosition kỳ gần nhất) ÷ burn_thang`, làm tròn 1 chữ số | Số dư 3.000.000.000 ÷ 500 tr → **6,0 tháng** |
| BR-FIN-03 | `burn_thang ≤ 0` → `runway_months = null`, hiển thị "Không áp dụng (đang có lãi)" — **không** hiển thị vô hạn. Chưa có CashPosition → `runway_months = null`, `runway_status = no_data` | |
| BR-FIN-04 | `burn_rate_monthly` hiển thị trên dashboard = **gross burn** = tổng chi phí của kỳ (phân biệt với net burn BR-FIN-01) | |
| BR-FIN-05 | `budget_utilization_pct = Thực chi ÷ Ngân sách phân bổ × 100`, theo phòng ban × kỳ (quý) × hạng mục; > 100 → `EVT-finance.budget_exceeded` (1 lần/phòng ban/kỳ) | Chi 1,1 tỷ / ngân sách 1,0 tỷ → 110% |
| BR-FIN-06 | Runway kịch bản "không có doanh thu mới" = `closing_balance ÷ AVG(tổng chi 3 kỳ tháng gần nhất)` (bỏ phần thu) — dùng cho US-CEO-102, tool AI what-if runway | Số dư 3 tỷ, chi TB 1,5 tỷ → 2,0 tháng |

Ràng buộc dữ liệu Finance: `Revenue.amount > 0`; hạng mục doanh thu `product_sales, service, consulting, other`; hạng mục chi `cogs, salary, infrastructure, marketing, office, travel, other`; `CashPosition` duy nhất theo kỳ `YYYY-MM`, `closing_balance ≥ 0`, nguồn `bank_statement, manual, imported`; Invoice ≥ 1 dòng, VAT mặc định 10%, `due_date` > ngày lập.

### 5.2. Sales

| Mã | Quy tắc | Ví dụ |
|---|---|---|
| BR-SAL-01 | `probability_pct` do người dùng nhập (0–100); tự đặt **100** khi `closed_won`, **0** khi `closed_lost` | |
| BR-SAL-02 | `weighted_value = deal_value × probability_pct / 100` | 800 tr × 20% = 160 tr |
| BR-SAL-03 | `win_rate_pct = deal thắng ÷ (deal thắng + deal thua) × 100` trong kỳ (theo `closed_at`) | 6 thắng, 14 thua → 30,0% |
| BR-SAL-04 | Pipeline coverage = tổng `deal_value` của deal đang mở có `expected_close_date` trong quý ÷ mục tiêu doanh thu quý (team) | 30 tỷ / 10 tỷ → 3,0x |

Giai đoạn deal: `prospecting → qualification → proposal → negotiation → closed_won | closed_lost`; mỗi lần chuyển lưu `ENT-DealStageHistory`; `closed_won` phát `EVT-sales.deal_closed_won`, `closed_lost` phát `EVT-sales.deal_closed_lost` (bắt buộc `lost_reason`).

### 5.3. HR

| Mã | Quy tắc | Ví dụ |
|---|---|---|
| BR-HR-01 | `turnover_rate_pct` (năm hóa) = `(số nghỉ việc trong kỳ ÷ headcount trung bình trong kỳ) × (12 ÷ số tháng của kỳ) × 100`; headcount trung bình = (đầu kỳ + cuối kỳ) / 2 | 3 người nghỉ trong 1 tháng, headcount TB 150 → **24,0%** |

Ràng buộc HR: trạng thái nhân viên `probation, active, on_leave, terminated`; hợp đồng `full_time, part_time, contract, intern`; chuyển `active` phát `EVT-hr.employee_onboarded`, nghỉ việc phát `EVT-hr.employee_terminated`; HiringPlan `headcount ≥ 1`, `salary_max ≥ salary_min > 0`, `target_date > start_date`. Mọi module dùng `department_id` do HR cấp.

### 5.4. Product

| Mã | Quy tắc | Ví dụ |
|---|---|---|
| BR-PRD-01 | **Churn bất thường**: `churn_rate_pct` kỳ hiện tại > `AVG(3 kỳ gần nhất) × (1 + CHURN_ANOMALY_REL_PCT/100)` (mặc định 50) **và** `churn_rate_pct ≥ CHURN_ANOMALY_FLOOR_PCT` (mặc định 2) → phát `EVT-product.metric_anomaly` (ALERT-PRD-02 critical) | TB 3 kỳ 1,2%, kỳ này 2,0% → +66,7% và ≥ 2% → bất thường. TB 1,0%, kỳ này 1,8% → +80% nhưng < 2% → **không** |

Ràng buộc Product: `Product.code` duy nhất; trạng thái `ideation, in_development, beta, launched, sunset`; vòng đời `introduction, growth, maturity, decline`; không xóa sản phẩm còn Feature `in_progress` hoặc Release `planned/in_progress`; xóa sản phẩm đã `launched` = xóa mềm → `sunset`; `ProductMetric` chỉ thêm, không sửa đè; doanh thu theo sản phẩm tổng hợp từ `EVT-finance.invoice_paid` (không đọc bảng Finance — DEC-125).

### 5.5. Risk

| Mã | Quy tắc |
|---|---|
| BR-RSK-01 | **Chấm điểm**: `risk_score = likelihood × impact`, `likelihood`, `impact` ∈ 1..5 → `risk_score` ∈ 1..25. Hệ thống tự sinh `risk_score`, `level`, mã `RSK-YYYY-NNN`; người dùng không nhập trực tiếp điểm |
| BR-RSK-02 | **Mức độ & hệ quả** (bảng dưới). Vòng đời (05 `risk.risk_status`, DEC-148): `proposed` (chỉ rủi ro tự sinh) `→ identified → assessed → mitigating → monitoring → closed`, `proposed → rejected` (owner bác bỏ, bắt buộc lý do); chỉ CEO (`risk:approve`) đặt `accepted` (bắt buộc người chấp nhận + lý do, ghi `ENT-Decision`). Rủi ro nhập tay có `risk_score ≥ 5` bắt buộc có owner. Không đóng rủi ro còn Mitigation `in_progress`. Mỗi lần đổi level tạo `ENT-RiskAssessment` và phát `EVT-risk.risk_level_changed`; sang `monitoring`/`closed` phát `EVT-risk.risk_mitigated`. Nhóm (13 danh mục BRD — DEC-148): `financial, operational, strategic, people, business, customer, product, technology, security, compliance, legal, partner_supplier, ai` |
| BR-RSK-03 | **Rủi ro tự sinh từ event**: consumer của module `risk` tạo `ENT-Risk` ở trạng thái **`proposed`** với `risk_source = event` (DEC-154) và phát `EVT-risk.risk_proposed` khi nhận `EVT-hr.hiring_plan_delayed`, `EVT-finance.budget_exceeded`, `EVT-finance.burn_over_forecast`, `EVT-sales.deal_closed_lost` (deal ≥ `RISK_LOST_DEAL_MIN_VALUE`, mặc định 1 tỷ), `EVT-product.metric_anomaly`, `EVT-finance.forecast_updated` (khi kịch bản `base` giảm lợi nhuận > 20%). Idempotent theo `event_id` (`ENT-ProcessedEvent`) — event trùng không tạo rủi ro trùng; cùng thực thể liên quan đang có rủi ro mở cùng nhóm → cập nhật đánh giá thay vì tạo mới. Rủi ro `proposed` được phép **chưa có owner**, không tính vào METRIC-RSK-01..05; owner (hoặc RISK_MANAGER) xác nhận → `identified` (bắt buộc owner) và phát `EVT-risk.risk_identified` theo bảng level dưới. `likelihood`/`impact` mặc định theo bảng ánh xạ event → điểm (cấu hình `RISK_EVENT_SCORING`) |

| `risk_score` | Level | Hệ quả |
|---|---|---|
| 1–4 | `low` | Chỉ lưu sổ |
| 5–9 | `medium` | Hiển thị trên dashboard, bắt buộc có owner (trừ khi còn `proposed`) |
| 10–15 | `high` | Phát `EVT-risk.risk_identified`; bắt buộc ≥ 1 Mitigation trong 7 ngày |
| 16–25 | `critical` | Phát `EVT-risk.risk_identified` và tạo alert critical cho CEO (ALERT-RSK-01) |

---

## 6. Yêu cầu chức năng theo domain (FR)

Actor ghi theo permission ở `02-PERSONAS-PERMISSIONS.md` §5.3. Mọi thao tác ghi phát audit; ghi từ IDP đi qua Action Registry (`04-IDP-FEATURE-SPEC.md`).

### 6.1. Finance — module `finance` (PIL-F)

| ID | Tính năng | Mô tả / quy tắc | Permission | Ưu tiên |
|---|---|---|---|---|
| FR-FIN-01 | Doanh thu | CRUD `ENT-Revenue` theo hạng mục, gắn `client_id`, `product_id` (tùy chọn); `amount > 0` | `finance:write` | Must |
| FR-FIN-02 | Chi phí | CRUD `ENT-Expense` theo phòng ban × hạng mục; hỗ trợ chi phí định kỳ (tháng); MANAGER tạo cho phòng ban mình | `finance:write` | Must |
| FR-FIN-03 | Ngân sách | `ENT-Budget` theo phòng ban × năm tài chính × quý × hạng mục; vượt → `EVT-finance.budget_exceeded` (BR-FIN-05) | `finance:write` | Must |
| FR-FIN-04 | Số dư tiền mặt | `ENT-CashPosition` theo kỳ `YYYY-MM` (duy nhất, ≥ 0); nguồn `bank_statement / manual / imported` | `finance:write` | Must |
| FR-FIN-05 | Dự báo | `ENT-Forecast` + `ENT-ForecastLine`: doanh thu, chi phí, lợi nhuận theo tháng; horizon `1m / 3m / 6m / 1y`; kịch bản `optimistic / base / pessimistic`; `confidence_pct` và nhận định AI (L0, có nguồn); tạo/cập nhật → `EVT-finance.forecast_updated`. Kế hoạch tuyển dụng `approved` cộng chi phí lương dự kiến vào dòng chi (02 §8) | `finance:write` | Must |
| FR-FIN-06 | Hóa đơn | `ENT-Invoice` + `ENT-InvoiceLine` (≥ 1 dòng, VAT mặc định 10%); trạng thái `draft → issued → partially_paid → paid`, `overdue` tự đặt theo job; `void`; thanh toán → `EVT-finance.invoice_paid` | `finance:write` | Should |
| FR-FIN-07 | Finance dashboard | `summary`: tổng doanh thu, tổng chi, lợi nhuận ròng, biên LN, gross burn (BR-FIN-04), net burn, runway, tăng trưởng, `budget_utilization_pct`; trend 12 tháng; METRIC-FIN-01..07 | `finance:query` | Must |
| FR-FIN-08 | Cảnh báo burn vượt dự báo | Job hằng ngày so net burn dự kiến tháng với dự báo đầu tháng (METRIC-FIN-07); vượt `THR_FIN_07_WARN` → ALERT-FIN-07 cho CFO + CEO, tối đa 1 lần/ngày; phát `EVT-finance.burn_over_forecast` | hệ thống | Should |

### 6.2. Sales — module `sales` (PIL-C)

| ID | Tính năng | Mô tả / quy tắc | Permission | Ưu tiên |
|---|---|---|---|---|
| FR-SAL-01 | Quản lý deal | CRUD `ENT-Deal`; bắt buộc tên, `client_id`, `deal_value > 0`, `expected_close_date` > hôm nay (khi tạo), `owner_id`; xóa (mềm) chỉ VP_SALES | `sales:write` | Must |
| FR-SAL-02 | Chuyển giai đoạn | Theo §5.2; lưu `ENT-DealStageHistory`; won/lost phát event; BR-SAL-01 | `sales:write` | Must |
| FR-SAL-03 | Khách hàng | CRUD `ENT-Client` (tên duy nhất, MST, ngành, quy mô, người liên hệ — PII mức 3); khớp mờ tên khi nhập/IDP | `sales:write` | Must |
| FR-SAL-04 | Pipeline | Số lượng, giá trị, giá trị có trọng số, số ngày TB ở mỗi giai đoạn | `sales:query` | Must |
| FR-SAL-05 | Hiệu suất | Doanh thu đóng, quota, % hoàn thành theo đội và cá nhân | `sales:query` | Must |
| FR-SAL-06 | Mục tiêu doanh thu | `ENT-SalesTarget` theo `month / quarter / year`, phạm vi `team / individual` (`owner_id` bắt buộc khi individual); CEO đặt mục tiêu team (US-CEO-106) | `sales:write` | Must |
| FR-SAL-07 | Sales dashboard | Giá trị pipeline, số deal (thắng/thua/đang chạy), win rate, giá trị deal TB, doanh thu đóng, % quota, chu kỳ bán TB; METRIC-CUS-01..06 | `sales:query` | Must |

Hợp đồng `ENT-Contract` (giá trị, kỳ hạn, ngày hết hạn, gắn Client/Deal) được ghi qua IDP (`CONTRACT`) hoặc nhập tay trong Sales workspace (SCR-23); chi tiết ở 04 và 05.

### 6.3. HR — module `hr` (PIL-O)

| ID | Tính năng | Mô tả / quy tắc | Permission | Ưu tiên |
|---|---|---|---|---|
| FR-HR-01 | Hồ sơ nhân viên | CRUD `ENT-Employee` (§5.3); event onboard/terminate | `hr:write` | Must |
| FR-HR-02 | Lịch sử lương | `ENT-SalaryHistory` chỉ thêm; mỗi lần đổi lương phát `EVT-hr.salary_updated` (payload **không** chứa số lương cá nhân — chỉ `employee_id`, `department_id`, delta quỹ lương) | `hr:write`; đọc: CEO, HR_MANAGER (dữ liệu mức 4) | Must |
| FR-HR-03 | Kế hoạch tuyển dụng | `ENT-HiringPlan` theo phòng ban × vị trí: headcount, khung lương, ngày bắt đầu, ngày mục tiêu, ưu tiên, ngân sách; theo dõi `filled` và còn thiếu | `hr:write` | Must |
| FR-HR-04 | Phát hiện tuyển dụng trễ | Job hằng ngày: kế hoạch trễ > 30 ngày so `target_date` → `EVT-hr.hiring_plan_delayed` (consumer: `risk`, `finance`); 1 lần/kế hoạch/mốc trễ | hệ thống | Must |
| FR-HR-05 | Phòng ban | CRUD `ENT-Department` (cây cha–con, `manager_id`); nguồn `department_id` cho mọi module | `hr:write` | Must |
| FR-HR-06 | HR dashboard | Tổng nhân sự, đang làm, nghỉ phép, đã nghỉ, tuyển mới tháng, turnover năm hóa, thâm niên TB, quỹ lương tháng (tổng hợp), tăng trưởng headcount, vị trí trống theo phòng ban, pipeline tuyển dụng; METRIC-HR-01..04 | `hr:query` | Must |
| FR-HR-07 | Phê duyệt kế hoạch tuyển dụng | Workflow `draft → submitted → approved/rejected` (02 §8); duyệt → chi phí lương dự kiến vào Forecast; hủy kế hoạch đã duyệt → hoàn tác phần dự báo | `hr:write` (gửi), `hr:approve` (CFO) | Could |

### 6.4. Product — module `product` (PIL-U)

| ID | Tính năng | Mô tả / quy tắc | Permission | Ưu tiên |
|---|---|---|---|---|
| FR-PRD-01 | Danh mục sản phẩm | CRUD `ENT-Product` (§5.4) | `product:write` | Must |
| FR-PRD-02 | Tính năng | CRUD `ENT-Feature`; chuyển `released` phát `EVT-product.feature_released` | `product:write` | Must |
| FR-PRD-03 | Roadmap | `ENT-RoadmapItem` theo quý, `target_date`, trạng thái `planned / in_progress / done / dropped` | `product:write` | Must |
| FR-PRD-04 | Release | `ENT-Release` (`release_version` duy nhất theo sản phẩm — DEC-154; `planned / in_progress / released / rolled_back`); release đầu tiên của sản phẩm phát `EVT-product.product_launched` | `product:write` | Must |
| FR-PRD-05 | Chỉ số sản phẩm | `ENT-ProductMetric` snapshot theo kỳ, chỉ thêm: MAU, `adoption_pct`, `churn_rate_pct`, `retention_30d_pct`, NPS, ARPU; nhập tay, import (C5) hoặc IDP `PRODUCT_REPORT` | `product:write` | Must |
| FR-PRD-06 | Phát hiện churn bất thường | BR-PRD-01 khi có snapshot mới | hệ thống | Must |
| FR-PRD-07 | Product dashboard | Số sản phẩm, đang hoạt động, đang phát triển, MAU, adoption, churn, retention 30 ngày, NPS, ARPU, tính năng release trong kỳ, % roadmap đúng tiến độ; METRIC-PRD-01..05 | `product:query` | Must |

### 6.5. Risk — module `risk` (PIL-S)

| ID | Tính năng | Mô tả / quy tắc | Permission | Ưu tiên |
|---|---|---|---|---|
| FR-RSK-01 | Sổ đăng ký rủi ro | Ghi rủi ro thủ công: tiêu đề, nhóm, `likelihood`, `impact`, owner, `linked_entities` (department, hiring_plan, budget, deal, product…); hệ thống sinh điểm, level, mã (BR-RSK-01) | `risk:write` | Must |
| FR-RSK-02 | Rủi ro tự sinh | BR-RSK-03 | hệ thống | Must |
| FR-RSK-03 | Đánh giá | Mỗi lần level đổi tạo `ENT-RiskAssessment`, phát `EVT-risk.risk_level_changed` | `risk:write` | Must |
| FR-RSK-04 | Biện pháp giảm thiểu | CRUD `ENT-Mitigation` (owner, `due_date`, `progress_pct`, trạng thái `planned / in_progress / done / cancelled`) | `risk:write` | Must |
| FR-RSK-05 | Cảnh báo rủi ro | Danh sách alert trụ S đang mở; CEO và RISK_MANAGER acknowledge | `dashboard:write` (trụ S) | Must |
| FR-RSK-06 | What-if | `ENT-Scenario`: 1–10 rủi ro × horizon 1–24 tháng → tác động ước lượng lên `finance` (doanh thu, chi, runway), `sales` (pipeline), `hr` (headcount), `product` (roadmap); mỗi miền gọi qua service interface với timeout 5 s; miền lỗi trả `unavailable`, không làm hỏng cả kết quả | `risk:query` | Should |
| FR-RSK-07 | Risk dashboard | Tổng rủi ro mở, số critical/high, điểm tổng hợp, xu hướng, mở/đóng trong kỳ, biện pháp đang chạy/quá hạn, alert chưa xác nhận, heatmap 5×5; METRIC-RSK-01..06 | `risk:query` | Must |

METRIC-RSK-06 (SEI) lấy dữ liệu Initiative/Milestone/Task từ module `execution` qua service interface (DEC-147); đặc tả OKR/KPI/check-in ở 04 (US-DC-005) và 05.

### 6.6. Executive Dashboard — module `dashboard`

| ID | Tính năng | Mô tả / quy tắc | Permission | Ưu tiên |
|---|---|---|---|---|
| FR-DSH-01 | Tổng quan 5 trụ | SCR-01 / trang Dashboard: 5 thẻ trụ (§4), **chỉ hiển thị trụ người dùng có quyền** (02 §5.4); trụ "chỉ tổng hợp" hiển thị số nhưng tắt drill-down | `dashboard:read` | Must |
| FR-DSH-02 | Trạng thái trụ | `ok / warning / critical / no_data / unavailable` theo §4; ngưỡng là biến cấu hình | hệ thống | Must |
| FR-DSH-03 | Drill-down | Mỗi trụ có trang chi tiết (SCR-02..06): bảng phân trang, biểu đồ, lọc theo kỳ, phòng ban, sản phẩm; chuỗi ≤ 3 click tới tài liệu gốc (§8) | `dashboard:read` + `<domain>:read` | Must |
| FR-DSH-04 | Insight panel | Insight AI ở đầu trang và theo từng trụ (§7.1) | `ai:query` | Must |
| FR-DSH-05 | Bộ lọc kỳ | `current_month / current_quarter / ytd`; Finance thêm `custom` | `dashboard:read` | Must |
| FR-DSH-06 | Tự làm mới | Tự làm mới mỗi 60 giây (`DASHBOARD_REFRESH_SEC`); dữ liệu trễ tối đa 60 giây so với nguồn (§9) | hệ thống | Should |
| FR-DSH-07 | Cô lập lỗi | Module hoặc AI lỗi → chỉ widget liên quan báo "Dịch vụ tạm thời không khả dụng" + nút thử lại; trụ khác vẫn hiển thị (P08, US-ALL-104) | hệ thống | Must |
| FR-DSH-08 | Giao diện chat | Trang Hỏi AI (SCR-16) với streaming, trạng thái tra cứu thật, khối "Nguồn dữ liệu"; mở từ thẻ metric/alert với ngữ cảnh đã điền sẵn | `ai:query` | Must |
| FR-DSH-09 | Báo cáo điều hành | Báo cáo weekly/monthly PDF + Excel (`ENT-Report`) từ `ENT-MetricValue` + insight, nội dung lọc theo scope người yêu cầu; job định kỳ sinh báo cáo công ty cho CEO, phát `EVT-platform.report_generated` (US-RPT-001, US-RPT-002, US-RPT-005 — DEC-153) | `dashboard:read` | Must |
| FR-DSH-10 | Hàng chờ phê duyệt | Danh sách `ENT-ApprovalRequest` chờ người dùng (bước 1/2, SLA `due_at`), duyệt/từ chối bắt buộc lý do; tài chính > `APPROVAL_FINANCE_THRESHOLD_VND` cần 2 người (DEC-155) (US-CEO-006) | `platform:approve` | Must |

### 6.7. Thông báo — module `platform`

| ID | Tính năng | Mô tả / quy tắc | Permission | Ưu tiên |
|---|---|---|---|---|
| FR-NTF-01 | Thông báo trong ứng dụng | `ENT-Notification` cho alert, insight critical, action card chờ xác nhận, task được giao, kế hoạch tuyển dụng chờ duyệt, yêu cầu phê duyệt (`EVT-platform.approval_requested`), báo cáo đã sinh; thông báo nâng cao BRD D05 (quy tắc, digest) hoãn v2.1 (DEC-156); chuông + đếm chưa đọc; người nhận theo §3.1 #6 | mọi user | Must |
| FR-NTF-02 | Email | Gửi alert `critical` qua email cho người nhận theo trụ; gom tối đa 1 email/giờ/người; tắt mặc định ở demo (`NOTIFY_EMAIL_ENABLED=false`) | hệ thống | Could |

---

### 6.8. Trợ lý AI — module `ai_core` (DEC-132)

| ID | Tính năng | Mô tả / quy tắc | Permission | Ưu tiên |
|---|---|---|---|---|
| FR-AI-01 | Hỏi đáp ngôn ngữ tự nhiên | Câu hỏi VI/EN → câu trả lời theo ngôn ngữ câu hỏi; ngữ cảnh màn hình (SCR, metric, kỳ) từ Panel/⌘K | `ai:query` | Must |
| FR-AI-02 | Tool calling theo quyền | Chỉ gửi model các TOOL-* mà role có permission (P06); tool chạy bằng JWT người hỏi; ≤ 8 call, 5 s/call, 30 s/lượt; tool bị từ chối → AI nói rõ không có quyền | `ai:query` + quyền domain | Must |
| FR-AI-03 | Streaming SSE | Trạng thái `thinking`/`tool_call` theo bước thật; token đầu (TTFT) **p50 ≤ 2 s, p95 ≤ 5 s** (DEC-152) | `ai:query` | Must |
| FR-AI-04 | Nguồn cho mọi con số | `sources[]` trỏ tới metric/bản ghi/tài liệu; số không có nguồn bị **chặn** (gỡ + warning), không gắn nhãn "ước tính" (§7.1, BRD FR-AIQ-01); thiếu dữ liệu → nói thiếu | `ai:query` | Must |
| FR-AI-05 | Lịch sử hội thoại | Lưu `ENT-Conversation`/`ENT-Message` của chính người dùng; xóa được | `ai:query` | Should |
| FR-AI-06 | Feedback | 👍/👎 + lý do cho câu trả lời và insight (`ENT-Feedback`) | `ai:query` | Should |
| FR-AI-07 | Insight chủ động & Briefing | Event domain → làm mới `ENT-Insight` (9 phần §7.1); Briefing theo role lúc `BRIEFING_TIME` (§7.2) | hệ thống; đọc `ai:query` | Must |
| FR-AI-08 | Hành động AI (L1–L3) | Gợi ý / Action card L2 chờ xác nhận / L3 làm và báo, ghi qua Action Registry (`ENT-AIAction`); hoàn tác L3 trong 24 h; kill switch (DEC-134, DEC-149); Verification 24h/7d cho L2+ (§7.3); vượt `ENT-ApprovalRule` → tạo `ENT-ApprovalRequest` | `ai:write` + quyền domain | Must |
| FR-AI-09 | What-if | Runway khi doanh thu = 0 / kịch bản rủi ro, gọi tool Finance/Risk, không tự tính ngoài tool | `ai:query` + `finance:read` / `risk:read` | Should |
| FR-AI-10 | An toàn dữ liệu | Chọn model theo `data_classification` (§7.4); lọc PII/lương (mức 3–4, 02 §6) trước khi gửi LLM; chống prompt injection (dữ liệu ≠ lệnh); rate limit 20 req/phút/người; ngân sách chi phí cảnh báo 80% | hệ thống | Must |
| FR-AI-11 | Ràng buộc nhân sự | AI không chấm điểm nhân sự, không quyết định tuyển/sa thải/lương; không huấn luyện trên dữ liệu khách (02 §7.4) | hệ thống | Must |

---

## 7. Insight & Briefing CEO

### 7.1. Cấu trúc insight 9 phần (BRD §11.8, AI-R03 — DEC-149, GAP A-11)

Mỗi `ENT-Insight` có **Observation** (`title` + `body`, một câu: điều gì lệch) và khối `structured` gồm **9 phần**. Bắt buộc đủ 9 phần với `kind ∈ {anomaly, risk, recommendation}`; `trend`/`briefing` chỉ bắt buộc Evidence + Confidence.

| # | Phần | Key `structured` (05 ENT-Insight) | Nội dung | Ví dụ |
|---|---|---|---|---|
| 1 | Root cause | `root_cause` | Nguyên nhân gốc có bằng chứng; chưa xác định được → ghi rõ "chưa rõ" + dữ liệu còn thiếu | "3 deal lớn (tổng 4,2 tỷ) trượt sang T10 do khách lùi ngân sách." |
| 2 | Risk | `risk` | Rủi ro / tác động nếu không xử lý, lên trụ khác (nếu có) — có nguồn | "Runway giảm từ 9,1 xuống 8,4 tháng nếu kéo dài 2 tháng." |
| 3 | Expected outcome | `expected_outcome` | Kết quả kỳ vọng nếu làm theo Action, **định lượng được** (metric + giá trị + mốc) — dùng cho bước Verification §7.3 | `{metric_id: METRIC-FIN-01, target: ≥ 90, by: +7d}` |
| 4 | Action | `action` | 1–3 hành động; mỗi hành động là suggestion chip (L1) hoặc action card (L2) gắn `TOOL-*` | "Giao VP Sales rà 3 deal (TOOL-create_task)." |
| 5 | Evidence | `evidence` | Danh sách số liệu kèm **source chip** (`SourceRef` tới metric value / bản ghi / trang tài liệu) | METRIC-FIN-01 = 82%; 3 deal `negotiation` quá hạn |
| 6 | Confidence | `confidence` | `high / medium / low` + lý do (độ tươi, METRIC-DQ-01, cỡ mẫu) — FR-AIQ-03 | "Trung bình — DQ tài chính 74, mới có 62% hóa đơn T9." |
| 7 | Alternative | `alternatives` | ≥ 1 phương án thay thế kèm đánh đổi (hoặc "không làm gì" + hệ quả) | "Lùi 20% chi marketing Q4 thay vì đẩy deal." |
| 8 | Timeline | `timeline` | Thời hạn hành động và mốc kiểm tra | "Trong 48 giờ; kiểm tra 24h/7d." |
| 9 | Owner | `owner` | Người/role đề xuất chịu trách nhiệm (con người — AI không bao giờ là owner, 01 §5A) | ROLE-03 VP_SALES |

Thứ tự hiển thị trên `InsightCard` theo BRD §11.8: Observation → Evidence → Risk → Root cause → Action → Expected outcome → Confidence (Alternative, Timeline, Owner ở phần mở rộng).

**Đồng bộ 05:** key `structured` v2.0.0 của 05 (`finding, evidence, root_cause, impact, recommendation, confidence, alternatives, owner_suggestion, next_action`) được thay bằng 9 key trên (05 cập nhật cùng Phase 3b): `finding` → `title/body`; `impact` → `risk`; `recommendation` + `next_action` → `action`; `owner_suggestion` → `owner`; thêm `expected_outcome`, `timeline`.

Quy tắc:
- Insight sinh bởi `ai_core` khi nhận event hoặc alert mới (debounce 5 phút/trụ), và theo lịch `BRIEFING_TIME` hằng ngày cho Briefing. **Mọi con số phải đến từ `ENT-MetricValue` hoặc tool call** (P05, FR-AIQ-01).
- **Số không có nguồn bị CHẶN ở v2.0 (GAP D-15):** validator gỡ mọi số không khớp `SourceRef`; insight còn lại < 1 Evidence → bị loại. **Không** dùng nhãn "ước tính" để giữ số không nguồn (BRD FR-AIQ-01 cho phép nhãn — Aureon v2.0 chọn chặn; số dự báo hợp lệ khi đến từ tool dự báo, ví dụ `TOOL-get_finance_forecast`, và mang nhãn kịch bản).
- Insight gắn trụ, mức `info / warning / critical`, `expires_at`; lọc theo quyền người xem (02 §6) — Evidence ngoài scope bị ẩn và insight đó không hiển thị nếu Observation phụ thuộc dữ liệu ngoài scope.
- Insight là L0 (Inform); hành động trong Action tuân theo `ENT-AutonomyPolicy` (02 §7). AI không tự gọi tool APPROVAL (02 §7.3).
- Feedback 👍/👎 trên từng insight (US-ALL-103).
- AI lỗi → panel insight báo "Trợ lý AI tạm thời không khả dụng"; dashboard vẫn chạy (P08).

### 7.2. Briefing CEO (F1) — BRD §12.2, GAP D-17

Briefing là trang chủ SCR-01 của ROLE-01 (biến thể theo role ở §10), **tính sẵn lúc `BRIEFING_TIME`** (mặc định `06:00` giờ `Asia/Ho_Chi_Minh`; BRD mặc định 07:00 — Aureon chọn 06:00 để sẵn trước giờ làm, cấu hình được qua env, đăng ký ở 07 Phase 3c). Thứ tự khối (P07 — ngoại lệ trước):

| # | Khối | Nội dung | Giới hạn |
|---|---|---|---|
| 1 | Dòng tóm tắt | Một câu: "2 việc cần anh, 1 rủi ro mới, 3/5 trụ ổn" | 1 dòng |
| 2 | 5 thẻ trụ | §4; trụ xấu nhất đứng đầu | 5 |
| 3 | Hiệu suất | **KPI công ty %** (trung bình achievement có trọng số các `ENT-KPI` cấp company) · **OKR công ty %** (trung bình `progress_pct` Objective cấp company) · SEI (METRIC-RSK-06) | 1 dòng, 3 số có nguồn |
| 4 | Hôm nay | Cuộc họp hôm nay (`ENT-Meeting`), task đến hạn hôm nay của CEO, hạn phê duyệt (`ENT-ApprovalRequest.due_at`) trong ngày; lịch ngoài (Calendar) hoãn v2.1 (DEC-153) | ≤ 5 |
| 5 | Cần anh quyết | `ENT-ApprovalRequest` chờ mình, action card L2 chờ xác nhận, rủi ro chờ chấp nhận, kế hoạch/ngân sách chờ duyệt (US-CEO-006) | ≤ 5, "xem thêm" |
| 6 | Thay đổi đáng chú ý | Insight `warning/critical` mới từ Briefing trước | ≤ 5 |
| 7 | Rủi ro | Rủi ro mới/đổi level trong 24 giờ (không gồm `proposed`) | ≤ 3 |
| 8 | AI đã làm | Hành động L3 trong 24 giờ, nút hoàn tác (SCR-17); kết quả Verification 24h/7d (§7.3) | ≤ 3 |
| 9 | 4 chỉ số ghim | Người dùng tự chọn 4 metric (`dashboard:write`) | 4 |
| 10 | Độ tươi & chất lượng | "Dữ liệu cũ: …" (metric quá `FRESHNESS_STALE_DAYS`) + METRIC-DQ-01 khi < 80 | 1 dòng |

- Mục "bình thường" gộp 1 dòng ("Các chỉ số khác trong ngưỡng"); không liệt kê.
- Mục tiêu: trả lời "có gì cần tôi?" ≤ 10 giây; F1 Briefing → giao việc ≤ 2 phút, ≤ 5 chạm (01 §4).
- Briefing cập nhật gia tăng khi có alert critical; mở trang không gọi LLM đồng bộ. Kênh: in-app (+ email critical khi bật FR-NTF-02); kênh ngoài là OQ-07.

### 7.3. Verification sau hành động (AI-R10 — GAP D-14)

Mọi `ENT-AIAction` mức **L2 trở lên** đã `executed` có bước **Verification** sau Action:

| Bước | Thời điểm | Việc | Kết quả |
|---|---|---|---|
| 0 | Lúc tạo action | Ghi `expected_outcome` (từ insight §7.1 #3, hoặc mặc định theo `ACT-*`: VD task tạo → task tồn tại và có assignee) | `ENT-AIAction.verification.expected_outcome` |
| 1 | `executed_at + 24h` | Job `daily_jobs` so expected vs actual (đọc `ENT-MetricValue` / bản ghi đích qua service) | `met` / `partially_met` / `not_met` / `not_measurable` |
| 2 | `executed_at + 7d` | Lặp lại với cùng tiêu chí | Như trên |

- Kết quả hiển thị trên feed "AI đã làm" (SCR-17) và khối 8 của Briefing; `not_met` ở mốc 7d → sinh insight `recommendation` mới cho owner (không tự hành động lại).
- Kết quả là đầu vào Evaluation Engine (BRD §11.7, v2.1) và cho số liệu "tỷ lệ khuyến nghị đạt kỳ vọng".
- Hành động bị hoàn tác (`undone`) bỏ qua Verification. Job idempotent theo (action_id, mốc).
- Lưu ở cột `verification` (jsonb) của 05 ENT-AIAction; không thêm event mới (dùng audit + feed).

### 7.4. Phân loại dữ liệu quyết định model (BRD FR-ADM-05 — DEC-149, GAP A-15)

| `data_classification` cao nhất của dữ liệu trong ngữ cảnh | Model sinh nội dung (insight, trả lời, briefing) | Embedding / RAG |
|---|---|---|
| `PUBLIC`, `INTERNAL` | Provider chain ModelGateway bình thường | `bge-m3` local (DEC-142) |
| `CONFIDENTIAL` (Mật) | **Không gửi LLM cloud** trừ provider ADMIN bật rõ cho mức này; mặc định dùng **template** (insight sinh từ quy tắc + số từ tool, không câu chữ LLM) | `bge-m3` local |
| `SECRET` (Tuyệt mật) | **Không gửi LLM** dưới mọi cấu hình; chỉ template; giá trị mức 4 bị PII filter loại | Không embed |

- Phân loại lấy mức cao nhất của mọi `tool_result`/`MetricValue` trong lượt (05 §10); quyết định trước khi gọi ModelGateway, ghi vào `ENT-ModelCallLog`.
- Hạ cấp xuống template phải báo rõ trên UI ("Tóm tắt tự động — dữ liệu Mật không gửi AI bên ngoài"); không làm mất source chip.
- Danh mục provider và cờ cho phép theo mức ở 07 §6 (Phase 3c).

---

## 8. Drill-down & lineage (P01)

### 8.1. Chuỗi drill-down ≤ 3 click

| Click | Từ | Đến | Nội dung |
|---|---|---|---|
| 0 | SCR-01 / thẻ trụ | — | Giá trị metric + trạng thái |
| 1 | Thẻ metric | SCR-07 Chi tiết metric | Công thức, giá trị, trend, ngưỡng, độ tươi, chất lượng dữ liệu, alert liên quan, bảng **thành phần** (phòng ban/sản phẩm/khách hàng) |
| 2 | Dòng thành phần | Bản ghi domain (Invoice, Deal, Employee…) trong panel bên | Trường dữ liệu, người nhập, thời điểm, kênh nhập (C1–C5), lịch sử sửa |
| 3 | Nút "Tài liệu gốc" | Trình xem tài liệu tại **trang và vùng** (bounding box) của field | `ENT-DocumentPage` + highlight vùng nguồn |

### 8.2. Panel P01 (bắt buộc cho mọi con số)

Bấm vào **bất kỳ** con số (thẻ trụ, bảng, biểu đồ, câu trả lời AI) mở popover gồm: tên metric/field, công thức (dạng chữ), giá trị và đơn vị, `computed_at`, nguồn (module + entity), số bản ghi cấu thành, nhãn độ tươi, nhãn chất lượng, link "Xem chi tiết" (SCR-07).

### 8.3. Lineage

- `ENT-DataLineage` nối `ENT-MetricValue → bản ghi domain → ENT-ExtractedField → ENT-DocumentPage` (thay `source_record_ids` của v1). Bản ghi nhập tay dừng ở bản ghi domain + người nhập.
- Hoàn tác commit IDP (`EVT-idp.document_rolled_back`) → metric phụ thuộc được tính lại và lineage cập nhật.
- Lineage tôn trọng scope (02 §6.1 #4): nút ngoài quyền hiển thị "Nguồn thuộc phạm vi khác — không có quyền xem"; tài liệu mức 4 chỉ mở cho role được phép (02 §6.3).

---

## 9. Hợp đồng dữ liệu dashboard, cache & NFR

| Hạng mục | Yêu cầu |
|---|---|
| Endpoint | 5 endpoint `/{domain}/dashboard` (`finance`, `hr` + `execution` cho PIL-O, `sales`, `product`, `risk`) — **không có endpoint tổng hợp chung** để đảm bảo cô lập lỗi; Briefing và metric/lineage có endpoint riêng (10) |
| Tham số | `period` = `current_month / current_quarter / ytd` (Finance thêm `custom` với `start_date`, `end_date`) |
| Cấu trúc | `summary` (KPI số phẳng + `status` từng metric) + ≥ 1 chuỗi `*_trend` (mảng phẳng, key ổn định, tăng dần theo thời gian) để vẽ trực tiếp; mỗi metric kèm `metric_id`, `computed_at`, `freshness`, `data_quality_pct`, `data_classification` |
| Cache | `Cache-Control: private, max-age=60` + **bắt buộc `Vary: Authorization`**; cache server theo (user scope, period) TTL 60 s, xóa khi metric liên quan tính lại |
| Frontend | Gọi song song 5 endpoint (TanStack Query, mỗi widget một query); không tự tính KPI; đổi role → xóa cache (02 §9.2 R3) |
| NFR-dashboard-1 | Endpoint dashboard **p95 < 800 ms** |
| NFR-dashboard-2 | Cả 5 trụ tải xong **< 3 giây** (desktop, mạng văn phòng) |
| NFR-dashboard-3 | Độ trễ dữ liệu tối đa **60 giây** so với nguồn |
| NFR-dashboard-4 | Một module hoặc AI lỗi không làm hỏng dashboard (FR-DSH-07) |
| NFR-dashboard-5 | Mọi ngưỡng là biến cấu hình, không hard-code |
| NFR-dashboard-6 | Đọc được trên màn ≥ 1280 px không cuộn ngang; mobile hiển thị Briefing + thẻ trụ dạng danh sách (SCR-28) |
| NFR-dashboard-7 | Hai tài khoản trên cùng trình duyệt không đọc chung cache |

Mã NFR chính thức (`NFR-xx`) do `07-TECH-ARCHITECTURE.md` cấp; các dòng trên là nhãn nội bộ của file này.

---

## 10. Hiển thị theo role

| Role | Trang chủ (SCR-01) | Trụ trên Dashboard | Ghi chú |
|---|---|---|---|
| ROLE-01 CEO | Briefing công ty (§7.2) | F, O, C, U, S | Đầy đủ drill-down; lương cá nhân chỉ ở HR workspace |
| ROLE-02 CFO | Briefing tài chính: F + S, ngân sách, dự báo, kế hoạch tuyển dụng chờ duyệt | F, S đầy đủ; O, C, U chỉ tổng hợp | |
| ROLE-03 VP_SALES | Briefing kinh doanh: C, pipeline, deal sắp đóng | C đầy đủ; U tổng hợp; F chỉ METRIC-FIN-01 | |
| ROLE-04 HR_MANAGER | Briefing nhân sự: O, tuyển dụng trễ, quá tải | O đầy đủ | METRIC-HR-01 dùng doanh thu tổng |
| ROLE-05 REVIEWER | Hàng chờ review + SLA (SCR-08) | — | Không có dashboard |
| ROLE-06 CPO | Briefing sản phẩm: U, roadmap quý | U đầy đủ; C tổng hợp | |
| ROLE-07 RISK_MANAGER | Briefing rủi ro: S, alert chưa xác nhận | S đầy đủ; F, O, C, U tổng hợp | |
| ROLE-08 MANAGER | Briefing đơn vị: hàng chờ duyệt, workload, task trễ, chi tiêu vs ngân sách phòng ban | — | Số liệu đơn vị ở workspace |
| ROLE-09 EMPLOYEE | Việc hôm nay, mục tiêu của tôi | — | |
| ROLE-10 ADMIN | Tình trạng hệ thống, sự cố AI, ngân sách AI, METRIC-DQ-01 theo domain (chỉ điểm, không bản ghi) | — | Không xem số nghiệp vụ |

Layout desktop trang Dashboard: hàng 1 dòng tóm tắt + bộ lọc kỳ; hàng 2 năm thẻ trụ; hàng 3 insight panel (trái) + alert mở (phải); Panel AI trượt bên phải. Chi tiết component ở `06-UI-UX-SPEC.md`.

---

## 11. Open questions

| # | Câu hỏi | Đề xuất mặc định | Ảnh hưởng |
|---|---|---|---|
| OQ-01 | METRIC-FIN-02 cần hạng mục chi `cogs` (A-EMS không có) — chấp nhận thêm hạng mục này? | Có; giá vốn = Expense `cogs`; dữ liệu demo ABC phân bổ giá vốn hàng bán | 05 `ENT-Expense.category`, 08 |
| OQ-02 | Giá trị kế hoạch `HR_REVENUE_PER_HEAD_PLAN` (METRIC-HR-01) lấy từ đâu? | Biến cấu hình do CEO/HR nhập; demo = 2,0 tỷ/người/năm | 08, SCR-15/27 |
| OQ-03 | METRIC-HR-03 cần `Task.estimate_hours` — nếu thiếu thì tính workload thế nào? | Thiếu estimate → mỗi task mở = 4 giờ (`DEFAULT_TASK_HOURS`) | 05 `ENT-Task` |
| OQ-04 | METRIC-CUS-05 NPS lấy từ ProductMetric (sản phẩm) hay khảo sát khách hàng riêng? | Từ `ENT-ProductMetric.nps` (v2 không có entity Survey) | 05, 08 |
| OQ-05 | ✅ **Resolved — DEC-143** (CUS-01 W < 2,8 · C < 2,5; RSK-04 W ≥ 10 · C ≥ 15; HR-04 C > 45 ngày). Câu hỏi gốc: Ngưỡng warning của các metric A-EMS chỉ có 1 mức (vd. METRIC-CUS-01 < 3x là critical) — mức warning bổ sung (3,5x, Δ…) có cần human duyệt? | Dùng giá trị trong §2 làm mặc định, cấu hình được | §2, §3 |
| OQ-06 | Rủi ro tự sinh từ `EVT-finance.forecast_updated`: điều kiện "lợi nhuận base giảm > 20%" có đúng ý không? | Giữ mặc định, cấu hình `RISK_FORECAST_DROP_PCT` | BR-RSK-03 |
| OQ-07 | Briefing có gửi qua kênh ngoài (Zalo/Slack/email) không? | Không ở v2; chỉ in-app (+ email critical nếu bật FR-NTF-02) | FR-NTF |
| OQ-08 | ✅ **Đóng — SEI tính theo Initiative** (`ENT-Initiative.weight_pct`, DEC-147; §2.5). Câu hỏi gốc: METRIC-RSK-06 cần `Objective.weight` — mặc định khi không nhập? | Σ trọng số = 0 → trọng số bằng nhau | 05 `ENT-Initiative` |
| OQ-09 | `BRIEFING_TIME` mặc định 06:00 (lệch BRD 07:00) — giữ 06:00? | Giữ 06:00, env cấu hình được; đăng ký ở 07 §env (Phase 3c) | 07, 10 EP Briefing |
| OQ-10 | Trọng số DQ Score 0,3/0,4/0,3 và SLA freshness theo domain có cần human duyệt riêng không? | Dùng mặc định §2.6 (theo yêu cầu Phase 3b), cấu hình `DQ_WEIGHT_*` | 05 ENT-Metric, 08 seed |
| OQ-11 | Kết quả Verification (§7.3) lưu ở cột mới `ai.ai_actions.verification` (jsonb) — chấp nhận thêm cột? | Có; 05 cập nhật cùng Phase 3b, không thêm event | 05 ENT-AIAction, 10 EP-11x |

Các OQ này chưa có DEC; captain cấp số ở `13-DECISION-LOG.md` khi đồng bộ governance.

---

## 12. Liên kết

| Chủ đề | File |
|---|---|
| Tầm nhìn, nguyên tắc P01–P09 | `01-PROJECT-OVERVIEW.md` |
| Role, permission, scope, tool filter | `02-PERSONAS-PERMISSIONS.md` |
| IDP, Action Registry, OKR/KPI capture, US-DC | `04-IDP-FEATURE-SPEC.md` |
| ENT-Metric, ENT-MetricValue, ENT-Alert, ENT-DataLineage, entity domain | `05-DATA-MODEL.md` |
| SCR-01..07, thẻ trụ, Panel P01, mẫu L1/L2/L3 | `06-UI-UX-SPEC.md` |
| Metric store, outbox, Celery beat, NFR-xx | `07-TECH-ARCHITECTURE.md` |
| Dữ liệu demo ABC cho 32 metric | `08-DEMO-DATA-SPEC.md` |
| Endpoint dashboard, metric, alert, briefing, event | `10-API-SPECIFICATION.md` |
| Quyết định | `13-DECISION-LOG.md` (DEC-125, DEC-126, DEC-127, DEC-132, DEC-143, DEC-147, DEC-148, DEC-149, DEC-152, DEC-154) |

---

## 13. Version

- **Version:** 2.1.0 (đề xuất — human promote ở 12)
- **Status:** draft (Phase 3b)
- **Last updated:** 2026-10-20
- **Applies to:** Aureon v2 (v2.0 demo-ready / v2.1 production-ready)
- **Maintainer:** @CyEyes
- **Change 2.1.0 (Phase 3b — DEC-144, DEC-147..149, DEC-152, DEC-154):** BRD làm Canonical Source; **32 metric / 32 alert** — thêm METRIC-DQ-01 / ALERT-DQ-01 với công thức `completeness × 0,3 + accuracy × 0,4 + freshness × 0,3`, < 80 warning, < 60 critical (§2.6); SEI (METRIC-RSK-06) tính theo **Initiative** (§2.5, GAP C-02); risk `proposed` + 13 danh mục, rủi ro `proposed` không sinh alert (§3.1, §5.5); insight **9 phần** + đồng bộ key 05 (§7.1, GAP A-11); chặn số không nguồn ở v2.0 (GAP D-15); Briefing `BRIEFING_TIME` 06:00 + khối "Hiệu suất" (KPI/OKR %) và "Hôm nay" (§7.2, GAP D-17); Verification 24h/7d cho L2+ (§7.3, GAP D-14); 4 mức `data_classification` quyết định model (§7.4, GAP A-15); TTFT p50 ≤ 2 s / p95 ≤ 5 s (DEC-152); FR-AI-11; FR-PRD-04 `release_version` (DEC-154); mã US mới (DEC-146); OQ-08 đóng, OQ-09..11.
- **Change 2.0.0:** Viết lại toàn bộ theo DEC-124, DEC-127 (5 trụ F.O.C.U.S, 31 metric/alert, BR và FR domain từ A-EMS, bộ chỉ số sức khỏe AI-EOS). Bản 1.0.0 (4 trụ, 18 metric) lưu ở nhánh `v1`.
- **Change (2026-10-19, DEC-143):** chốt ngưỡng METRIC-CUS-01 (W < 2,8x · C < 2,5x), METRIC-RSK-04 (W ≥ 10 · C ≥ 15), METRIC-HR-04 (C > 45 ngày) và ALERT tương ứng; đóng OQ-05.
