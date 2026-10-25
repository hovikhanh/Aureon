# 03 — Dashboard & Executive Intelligence Spec (Aureon v3 — AI-EOS)

> **Nguồn chuẩn:** `_reference/SOURCE-BRD-v1.1.md` §12 (D27 CEO Assistant, Daily Briefing, Management Loop, bộ chỉ số sức khỏe, D28 Reporting, Decision Log), §11.8 (insight 9 phần), §13.1 (Data Foundation FR-DATA-01..08); `SOURCE-BRD-v1.1-Bổ sung.md` §4.3–§4.4; `SOURCE-UIUX.md` §6.1 (Trang chủ CEO) + F1 (luồng CEO buổi sáng).
> **Phụ thuộc:** 00, 01, 02, `TRACEABILITY-SKELETON.md` §9 (AI Platform), §10 (bộ chỉ số), §12 (ánh xạ main). **Trạng thái:** ✅ current — Aureon v3 (AI-EOS) CHÍNH THỨC. **Ngày:** 2026-10-23 · **Maintainer:** @CyEyes

> **Phạm vi R-DEC-09 (docs-first):** File này chỉ đặc tả chiều **sản phẩm** (FR, UC, luồng, trạng thái, quy tắc nghiệp vụ, chỉ số, màn hình). Field-level DB (tên cột/kiểu/constraint per-entity), `METRIC-*` cụ thể, task `T-*` và test case `TC-*` chi tiết **hoãn sang đợt code** — các ghi chú "chi tiết hóa ở đợt code (R-DEC-09)" giữ nguyên.

---

## 1. Ba cấp dashboard (FR-RPT-03)

Dashboard là lớp trình bày của bộ chỉ số sức khỏe (§4) theo scope vai trò (ROLE-*, 02). Cả 3 cấp cùng đọc một **Metric Store** (FR-DATA-06); khác nhau ở phạm vi dữ liệu và tập widget, không khác nhau ở công thức.

| Dashboard | Người dùng | Nội dung | Scope dữ liệu |
|---|---|---|---|
| **Executive** | ROLE-CEO, ROLE-DIR | Doanh thu, tiền, pipeline, con người, KPI, OKR, rủi ro, dự án, **tiến độ chiến lược** | Toàn DN (CEO) / khối phụ trách (Director) |
| **Department** | ROLE-DIR, ROLE-MGR | Hiệu suất, workload, KPI, OKR, dự án, rủi ro của đơn vị | Phòng ban / team của mình |
| **Employee** | ROLE-EMP | Task, mục tiêu, KPI/OKR cá nhân, workload, lịch | Cá nhân |

### 1.1. Widget cụ thể mỗi cấp

**Executive (ROLE-CEO / ROLE-DIR)** — bố cục theo `SOURCE-UIUX.md` §6.1:

- **Dòng tóm tắt một câu** (U1): trả lời "có gì cần tôi?" trước mọi con số (VD "2 việc cần anh quyết, 1 rủi ro mới, doanh thu đạt 82% kế hoạch"). Sinh từ cùng logic Briefing (§3).
- **4 ô chỉ số sức khỏe** CEO tự chọn trong cài đặt; mặc định: **doanh thu, dòng tiền (cash runway), OKR công ty, task trễ**. Mỗi ô có nhãn độ tươi dữ liệu (FR-DATA-03) và trạng thái màu theo ngưỡng §4. Bấm ô → mở nguồn + công thức (drill-down FR-RPT-04).
- **Khối "Cần anh quyết"** (đứng trên rủi ro): danh sách quyết định đang chờ (nguồn Decision Log + Approval Engine), mỗi dòng có tóm tắt AI + nút hành động tại chỗ.
- **Khối "Rủi ro"**: rủi ro đang mở xếp theo mức, nối với Risk Engine (§4 dùng chung ngưỡng).
- **Khối "AI đã làm"** (nền khác biệt — U4): feed hành động L3 kèm lối hoàn tác (undo ≥24h, autonomy ở 02/07).
- **Panel AI bên phải** mở theo ngữ cảnh ô đang chọn; < 1280 px → ngăn kéo trượt.
- Widget chiến lược: **Strategy Execution Index** + cây initiative tóm tắt; widget KPI/OKR công ty (tỷ lệ đạt).

**Department (ROLE-DIR / ROLE-MGR):**

- Thẻ hiệu suất đơn vị (KPI/OKR phòng ban, % đạt), heatmap **workload người × tuần** (nối cảnh báo quá tải §4), danh sách dự án của đơn vị + cờ trễ, task đến hạn/quá hạn, rủi ro cấp đơn vị, khối "AI gợi ý" (L1) điều phối workload (luồng F5, `SOURCE-UIUX.md`).

**Employee (ROLE-EMP):**

- Danh sách **task của tôi** (theo hạn/trạng thái), mục tiêu & KPI/OKR cá nhân, thẻ **check-in KPI/OKR** (giá trị AI điền sẵn, thanh độ tự tin — luồng F4), workload tuần, lịch sắp tới. Không hiển thị dữ liệu ngoài scope cá nhân.

### 1.2. Quy tắc chung dashboard

- **FR-RPT-04:** mọi chỉ số hiển thị **thời điểm cập nhật (data freshness, FR-DATA-03)** + **drill-down ≤ nguồn** tới bản ghi và **tài liệu gốc** (P06/P07 Traceability, FR-DATA-04).
- **Widget độc lập:** mỗi widget lỗi chỉ báo tại chỗ, không sập cả trang (một query / widget).
- **Scope cứng:** trụ/đơn vị ngoài phạm vi vai trò **không xuất hiện** trong response (không trả `null`); lineage ngoài scope → `{ restricted: true, reason }` (đồng bộ 02).
- **Dữ liệu cũ:** chỉ số vượt ngưỡng freshness (SLA_FRESHNESS_*) gắn nhãn "dữ liệu đã cũ" và được Briefing nêu (FR-DATA-03).

> **Khác `main`:** `main` dùng 5 trụ F.O.C.U.S cố định. AI-EOS dùng 3 cấp dashboard theo vai trò + bộ chỉ số sức khỏe chuẩn §4. "View 5 trụ F.O.C.U.S" là **bố cục Executive tùy chọn (optional)**, không phải view chuẩn (OQ-03-01 đã chốt). Ánh xạ 5 trụ ↔ nhóm chỉ số: `TRACEABILITY-SKELETON.md` §12.

## 2. CEO AI Assistant — D27 (BRD §12.1)

Giao diện AI chính, dùng trên **web, mobile, chat, giọng nói**. Mọi con số **có nguồn** (P01/P07, FR-AIQ-01 grounding — không khớp nguồn thì gỡ số hoặc gắn nhãn "ước tính"). Tool lọc theo quyền người hỏi: AI dùng quyền ROLE-AI ∩ quyền người (AI-R01, AI-R08). 12 năng lực:

| # | Năng lực | Mô tả hành vi + ràng buộc | Ví dụ câu lệnh |
|---|---|---|---|
| 1 | **Hỏi** | Trả lời trạng thái tổng hợp từ Metric Store; mọi số kèm SourceRef. | "Tình hình công ty?" |
| 2 | **Phân tích** | Tìm root cause qua tool READ trên dữ liệu được phép; xuất theo insight 9 phần (§5). | "Tại sao doanh thu giảm?" |
| 3 | **So sánh** | Đối chiếu chỉ số giữa đơn vị/kỳ; chỉ trả đơn vị trong scope người hỏi. | "So sánh hiệu suất các phòng ban." |
| 4 | **Dự báo** | Chiếu xu hướng từ dữ liệu lịch sử; gắn confidence (FR-AIQ-03), nêu giả định. | "Dự báo doanh thu Q4." |
| 5 | **Mô phỏng (what-if)** | Chạy scenario trên dữ liệu thực (Bổ sung §4.6); không ghi dữ liệu, chỉ trả kịch bản. | "Nếu cắt 10% chi phí marketing thì runway thêm bao nhiêu?" |
| 6 | **Rủi ro** | Liệt kê rủi ro đang mở theo mức, nối Risk Engine + ngưỡng §4. | "Rủi ro lớn nhất hiện tại?" |
| 7 | **Khuyến nghị** | Đề xuất hành động theo insight 9 phần, có Expected Outcome + Confidence. | "Tôi nên làm gì?" |
| 8 | **Thực thi** | Tool WRITE/EXECUTION theo Autonomy: L2 action card chờ xác nhận, L3 thực thi + undo. Cần `ai:write` ∩ `<domain>:write`. | "Tạo task cho CFO." |
| 9 | **Nhập liệu (text/ảnh/file)** | Vào pipeline IDP (04); AI hiển thị bản ghi dự kiến, chỉ ghi sau xác nhận (US-DC-002). | "Ghi nhận: hợp đồng ABC ký 2 tỷ" / gửi ảnh, file |
| 10 | **Báo cáo** | Gọi D28 Reporting (§6), số liệu từ Metric Store có trích dẫn, sửa được trước khi gửi. | "Tạo báo cáo điều hành tuần." |
| 11 | **Nhắc việc** | Tạo reminder/follow-up gắn entity liên quan. | "Nhắc tôi follow-up ABC." |
| 12 | **Quyết định chờ** | Liệt kê việc chờ CEO quyết (Decision Log + Approval Engine), nối khối "Cần anh quyết" (§1.1). | "Việc gì đang chờ tôi quyết?" |

- Mọi lượt gọi tool ghi audit (AI-R07); authorization kiểm trước tool call (AI-R08); kết quả được verify (AI-R10).
- Phản hồi đúng/sai + lý do cho mỗi câu trả lời → Evaluation Engine (FR-AIQ-04, Bổ sung §4.4).

## 3. CEO Daily Briefing (BRD §12.2, UC-01, US-CEO-001)

AI tự tổng hợp lúc **07:00** (cấu hình được), gửi qua kênh CEO chọn. Chỉ nêu **ngoại lệ & thay đổi đáng kể**; mọi dòng bấm được để xem chi tiết + nguồn (FR-RPT-04). Mục tiêu ≤ 1 trang (UC-01); trên mobile là trang cuộn ngắn đọc trong 30 giây (`SOURCE-UIUX.md` §6.3).

### 3.1. Cấu trúc 7 khối

| Khối | Nội dung | Nguồn dữ liệu |
|---|---|---|
| **COMPANY STATUS** | Trạng thái tổng: tăng trưởng DT, cash runway, pipeline — số + so với kế hoạch. | Chỉ số Tài chính + Khách hàng §4 |
| **DATA FRESHNESS** | Thời điểm cập nhật cuối của từng domain; cảnh báo dữ liệu đã cũ; số tài liệu chờ duyệt. | FR-DATA-03, pipeline IDP (04) |
| **RISKS** | Rủi ro đang mở xếp theo mức (🔴/🟠), chỉ ngoại lệ mới/đáng kể. | Risk Engine + ngưỡng §4 |
| **PERFORMANCE** | % đạt KPI công ty, % đạt OKR công ty. | Chỉ số KPI/OKR, Strategy Execution Index §4 |
| **TODAY** | Lịch họp/sự kiện quan trọng trong ngày. | Calendar (D13) |
| **DECISIONS WAITING** | Việc đang chờ CEO quyết (duyệt tuyển, duyệt ngân sách…). | Decision Log (§7) + Approval Engine |
| **RECOMMENDATIONS** | 1–3 khuyến nghị ưu tiên, mỗi mục nối insight 9 phần (§5). | AI khuyến nghị (AI-R03) |

### 3.2. Ví dụ Briefing (minh họa, số giả định)

```text
COMPANY STATUS            Revenue +12% | Cash runway 7,4 tháng | Pipeline 28 tỷ
DATA FRESHNESS            Finance cập nhật 06:00 | 3 hóa đơn chờ duyệt
RISKS                     🔴 Dự án A trễ | 🟠 Sales dưới kế hoạch | 🟠 Kỹ thuật quá tải
PERFORMANCE               Company KPI 91% | Company OKR 82%
TODAY                     09:00 HĐQT | 11:00 Khách ABC | 15:00 Product review
DECISIONS WAITING         Duyệt tuyển 2 sales | Duyệt ngân sách Q4 marketing
RECOMMENDATIONS           1. Review dự án A  2. Follow-up ABC  3. Duyệt tuyển dụng
```

### 3.3. Tiêu chí chấp nhận (UC-01)

- Briefing sẵn sàng đúng giờ cấu hình; thông báo tóm tắt số việc cần quyết + rủi ro mới ("Briefing sẵn sàng: 2 việc cần anh, 1 rủi ro mới", `SOURCE-UIUX.md` F1).
- Chỉ xuất hiện ngoại lệ/thay đổi đáng kể (không lặp lại số ổn định).
- Mọi dòng drill-down tới bản ghi + tài liệu gốc; mọi số có nguồn.
- Luồng F1 đạt: từ Briefing đến giao việc ≤ 2 phút, ≤ 5 chạm (chạm thẻ → panel AI nguyên nhân/bằng chứng/nguồn → chọn phương án → Action card → Xác nhận → toast "Đã tạo task, đặt lịch · Hoàn tác", quyết định vào Decision Log).

### 3.4. CEO Management Loop (BRD §12.3)

Briefing và Assistant hỗ trợ vòng quản trị của CEO — AI phục vụ từng mắt xích (quan sát, khuyến nghị, delegation, follow-up):

```text
Observe → Company Status → Performance → Risk → Opportunity → Recommendation
→ Decision → Delegation → Execution → Follow-up → Result
```

## 4. Bộ chỉ số sức khỏe doanh nghiệp chuẩn (BRD §12.4)

Cố định, có công thức + ngưỡng cảnh báo, dùng chung cho Dashboard / Briefing / AI / Risk Engine (FR-DATA-06 Metric Store). Tinh chỉnh được; MVP **bắt buộc các chỉ số P0**. Mỗi chỉ số P0 có **một alert 1-1**: khi giá trị vượt ngưỡng cấu hình → sinh cảnh báo (feed Briefing khối RISKS/PERFORMANCE + Risk Engine), nối drill-down tới bản ghi nguồn.

| Nhóm | Chỉ số | Công thức tóm tắt | Ngưỡng cảnh báo | Ưu tiên | Ngữ nghĩa alert (P0: 1-1) |
|---|---|---|---|---|---|
| Tài chính | Tăng trưởng DT, % đạt kế hoạch | (DT kỳ − DT cùng kỳ)/DT cùng kỳ | < kế hoạch > 10% | P0 | Cảnh báo khi DT thực thấp hơn kế hoạch > 10% → RISKS + gợi ý phân tích root cause (năng lực 2). |
| Tài chính | Cash runway | Tiền mặt / Burn ròng tháng | < 6 tháng | P0 | Cảnh báo khi runway < 6 tháng → RISKS mức cao; nối what-if cắt chi phí (năng lực 5). |
| Tài chính | Chênh lệch ngân sách | (Thực chi − NS)/NS | > 10% | P0 | Cảnh báo khi vượt ngân sách > 10% theo cost center → RISKS. |
| Tài chính | Biên LN gộp/EBITDA | LN/DT | giảm > 3đ% vs TB 3 kỳ | P1 | (chi tiết hóa ở đợt code — R-DEC-09) |
| Tài chính | DSO/DPO/vòng quay tiền | DSO+DIO−DPO | DSO tăng > 15% | P1 | (chi tiết hóa ở đợt code — R-DEC-09) |
| Tài chính | Công nợ quá hạn | Phải thu quá hạn/Tổng | > 15% | P1 | (chi tiết hóa ở đợt code — R-DEC-09) |
| Khách hàng | Pipeline coverage | Pipeline trọng số/Chỉ tiêu còn lại | < 3x | P0 | Cảnh báo khi coverage < 3x → RISKS; gợi ý tập trung deal lớn. |
| Khách hàng | Win rate, chu kỳ bán | Won/Cơ hội đóng | giảm > 20% | P0 | Cảnh báo khi win rate giảm > 20% so kỳ trước → PERFORMANCE/RISKS. |
| Khách hàng | NRR, churn | DT khách cũ kỳ/kỳ trước | NRR < 100% | P1 | (chi tiết hóa ở đợt code — R-DEC-09) |
| Khách hàng | Tập trung DT | DT top5/Tổng | > 50% | P1 | (chi tiết hóa ở đợt code — R-DEC-09) |
| Khách hàng | CAC, LTV/CAC, NPS | chuẩn | LTV/CAC < 3 | P1 | (chi tiết hóa ở đợt code — R-DEC-09) |
| Vận hành | Hoàn thành đúng hạn | Task đúng hạn/đến hạn | < 80% | P0 | Cảnh báo khi tỷ lệ đúng hạn < 80% → PERFORMANCE; drill-down task quá hạn. |
| Vận hành | Dự án trễ | Dự án trễ>10%/Tổng | > 20% | P0 | Cảnh báo khi > 20% dự án trễ → RISKS; nối UC điều phối. |
| Vận hành | Thực thi quyết định | Action item xong/đến hạn | < 70% | P0 | Cảnh báo khi < 70% action item đến hạn hoàn thành → RISKS; nối Decision Log. |
| Con người | Quá tải | Người >110% workload 2 tuần/Tổng | > 10% | P0 | Cảnh báo khi > 10% nhân sự quá tải 2 tuần liên tiếp → RISKS; gợi ý điều phối (F5). |
| Con người | Nghỉ việc | Nghỉ/NS bình quân (năm hóa) | > 15%/năm | P1 | (chi tiết hóa ở đợt code — R-DEC-09) |
| Con người | DT/nhân sự; CP nhân sự/DT | theo kỳ | lệch > 15% kế hoạch | P1 | (chi tiết hóa ở đợt code — R-DEC-09) |
| Chiến lược | **Strategy Execution Index** | % initiative đúng tiến độ (trọng số) | < 70% | P0 | Cảnh báo khi index < 70% → RISKS + widget chiến lược Executive; drill-down tới initiative trễ. |
| Dữ liệu | **Data Quality Score** | Đầy đủ/chính xác/kịp thời/nhất quán | < 80/100 | P0 | Cảnh báo khi DQ Score < 80/100 → AI gắn cảnh báo "kết luận dựa trên dữ liệu chất lượng thấp" (FR-DATA-02). |
| Chiến lược | **KPI/OKR cập nhật đúng kỳ** — `METRIC-STR-01` (cổng G2, đề xuất R-DEC-54 — Spec lock M1.4) | (#KPI-kỳ đo đúng hạn + #KR check-in đúng hạn) / (#KPI-kỳ đến hạn + #KR active); grace `GOALS_KPI_GRACE_DAYS`, check-in ≤ `GOALS_KR_CHECKIN_MAX_AGE_DAYS` | < 80% (critical < 60%) | P0 | Cảnh báo khi < 80% → PERFORMANCE; drill-down danh sách KPI/KR trễ (05 §2.6). |
| Dữ liệu | **Bản ghi mới vào qua tài liệu/NL** — `METRIC-DQ-02` (cổng G3, đề xuất R-DEC-68 — Spec lock M1.5) | Bản ghi đích tạo trong tháng có nguồn `IDP`/`IMPORT`/`AI` ÷ tổng bản ghi tạo trong tháng (tập bảng whitelist lineage; C1 form không tính) | < 60% (critical < 40%) | P0 | Cảnh báo khi < 60% → DATA; drill-down theo kênh/doc type. |

- **Grounding:** mọi giá trị hiển thị là `MetricValue` tính sẵn, có `lineage_url` (FR-DATA-04, FR-DATA-06); dashboard/AI không tính lúc request.
- **Ngưỡng là cấu hình** (không hard-code); doanh nghiệp tinh chỉnh được, mặc định theo bảng trên.
- **Mã đã cấp (Spec lock M1.3–M1.6, đề xuất):** `METRIC-STR-01` (G2) và `METRIC-DQ-02` (G3) đăng ký ở skeleton §10. Strategy Execution Index giữ mã nền `METRIC-RSK-06` tới T-701 (M2.1, bảng ánh xạ 32 METRIC); Data Quality Score theo domain là breakdown của `METRIC-DQ-01` (không cấp mã riêng).

> `METRIC-*` cụ thể + mã alert 1-1 cấp khi chi tiết hóa ở đợt code (00/14, R-DEC-09). Ngưỡng freshness (SLA_FRESHNESS_*) tách khỏi SLA vận hành (08). Danh sách chỉ số nguồn: `TRACEABILITY-SKELETON.md` §10.

## 5. Insight & khuyến nghị — cấu trúc 9 phần (BRD §11.8)

Mọi insight của AI (Briefing khối RECOMMENDATIONS, panel phân tích, khuyến nghị) theo đúng cấu trúc 9 phần; thiếu phần nào thì nêu rõ thiếu, không bịa:

| # | Phần | Ý nghĩa |
|---|---|---|
| 1 | **Observation** | Phát hiện/triệu chứng đang quan sát. |
| 2 | **Evidence** | Bằng chứng định lượng có SourceRef (metric, bản ghi, tài liệu). |
| 3 | **Impact** | Ảnh hưởng tới mục tiêu/chỉ số. |
| 4 | **Root Cause** | Nguyên nhân gốc suy ra từ dữ liệu. |
| 5 | **Risk** | Rủi ro nếu không hành động. |
| 6 | **Recommendation** | Hành động đề xuất cụ thể. |
| 7 | **Expected Outcome** | Kết quả kỳ vọng đo được. |
| 8 | **Confidence** | Độ tin cậy: thang Cao/Trung bình/Thấp + lý do khi chưa hiệu chỉnh đủ (FR-AIQ-03). |
| 9 | **Action** | Nút/Action card để thực thi (theo Autonomy). |

**Ví dụ (BRD §11.8):** *"Dự án A có thể trễ 18 ngày. Bằng chứng: velocity −22%, 3 blocker, utilization kỹ thuật 112%. Khuyến nghị: điều thêm 1 kỹ sư. Kỳ vọng: giảm trễ còn 5–7 ngày. Độ tin cậy: Cao."*

- Grounding bắt buộc (FR-AIQ-01); mọi con số trong insight khớp `tool_result`/`MetricValue`.
- Mỗi insight có nút đúng/sai + lý do → Evaluation Engine (FR-AIQ-04).

## 6. D28 — Reporting & Analytics (BRD §12.5)

- **FR-RPT-01:** AI tạo báo cáo **ngày/tuần/tháng/HĐQT/phòng ban/KPI/OKR/dự án/rủi ro/tài chính**; theo **lịch** hoặc theo **yêu cầu** (năng lực 10 của Assistant). Mỗi loại có template cố định; phạm vi dữ liệu theo scope người tạo.
- **FR-RPT-02:** số liệu lấy từ **Metric Store** (FR-DATA-06), **có trích dẫn** nguồn (P07); xuất **PDF/Word/Excel/Google Docs**; **sửa được trước khi gửi**. Số không có nguồn bị chặn hoặc gắn nhãn "ước tính".
- **FR-RPT-03:** 3 cấp dashboard (§1).
- **FR-RPT-04:** mọi chỉ số dashboard hiển thị thời điểm cập nhật + drill-down tới bản ghi và tài liệu gốc (§1.2).

**Quy tắc nghiệp vụ / ngoại lệ:**

- Báo cáo theo lịch idempotent theo (loại, kỳ) — không sinh trùng khi chạy lại.
- Dữ liệu cũ quá ngưỡng freshness → báo cáo ghi rõ "dữ liệu tính đến <thời điểm>".
- Người tạo chỉnh nội dung trước khi gửi; bản chỉnh không ghi đè số nguồn (giữ lineage).

## 7. Decision Log (BRD §12.6)

- **FR-DEC-01:** ghi quyết định với: **nội dung, lý do, phương án đã loại, người quyết, ngày, kết quả kỳ vọng đo được, nguồn** (họp / khuyến nghị AI / phê duyệt). Quyết định tạo từ luồng F1 (chọn phương án trong Action card) tự vào Decision Log.
- **FR-DEC-02:** sau **30/60/90 ngày** AI đối chiếu kết quả thực tế vs kỳ vọng và **đánh dấu quyết định cần xem lại**. Mốc đối chiếu chạy định kỳ (idempotent theo (quyết định, mốc)); kết quả nối khối "Cần anh quyết"/RISKS khi lệch.
- **FR-DEC-03:** Decision Log là **nguồn chính đo North Star** (01 §2; BO-04 quyết định có AI ≥ 50%).

**Trạng thái quyết định (vòng đời):** `GHI_NHẬN → ĐANG_THEO_DÕI → ĐÃ_ĐỐI_CHIẾU(30/60/90) → {ĐẠT_KỲ_VỌNG | CẦN_XEM_LẠI}`. Mỗi lần đối chiếu gắn SourceRef tới chỉ số/kết quả thực tế (grounding P07).

## 8. Use case liên quan

| UC | Tên | Vai trò file 03 | Ưu tiên |
|---|---|---|---|
| **UC-01** | CEO Morning Briefing | Briefing §3 + Management Loop; tiêu chí ≤ 1 trang, luồng F1 | P0 |
| **UC-03** | KPI Underperformance | Alert chỉ số Vận hành/KPI §4 → insight 9 phần §5 → khuyến nghị | P0 |
| **UC-04** | OKR At Risk | Alert OKR/Strategy Execution Index §4 → widget chiến lược Executive | P0 |
| **UC-05** | CEO Strategic Question | Assistant năng lực 1–7 §2 trên dashboard + Decision Log | P1 |

- **Tiêu chí chấp nhận chung:** mọi con số có nguồn + drill-down; alert nối đúng khối Briefing; khuyến nghị theo cấu trúc 9 phần; quyết định phát sinh ghi Decision Log.

## 9. Open questions

- OQ-03-01: Giữ "view 5 trụ F.O.C.U.S" của `main` — **ĐÃ CHỐT:** R-DEC-10 giữ bảng ánh xạ sang `main`; "view 5 trụ" là bố cục Executive tùy chọn (optional), không phải view chuẩn — view chuẩn là 3 cấp dashboard BRD.
- OQ-03-02: METRIC-* numbering — **ĐÃ CHỐT:** R-DEC-10 — đánh số theo nhóm BRD + giữ bảng ánh xạ sang METRIC-<DOMAIN>-xx của `main`; METRIC-* cụ thể gán khi 03 được chi tiết hóa ở đợt code (R-DEC-09).
- OQ-03-03: Mã alert 1-1 cho mỗi chỉ số P0 (prefix + numbering) — hoãn gán ở đợt code (R-DEC-09); ngữ nghĩa alert đã đặc tả ở §4 (cột "Ngữ nghĩa alert").
- OQ-03-04: Bộ 4 ô chỉ số mặc định của Executive (doanh thu, dòng tiền, OKR, task trễ) có cho phép Director override theo khối hay cố định toàn DN — đề xuất cấu hình per-role; chốt khi chi tiết hóa màn hình ở đợt code.

## Version
- **Version:** 1.0.0 (current)
- **Last updated:** 2026-10-23
- **Maintainer:** @CyEyes
- **Change 1.0.1 (đề xuất — Spec lock M1.3–M1.6, chờ human duyệt):** §4 thêm dòng `METRIC-STR-01` (G2, R-DEC-54) và `METRIC-DQ-02` (G3, R-DEC-68) + ghi chú mã đã cấp (SEI giữ `METRIC-RSK-06`, DQ theo domain = breakdown `METRIC-DQ-01`).
- **Change 1.0.0 (promote):** Promote tài liệu AI-EOS lên CHÍNH THỨC Aureon v3; di chuyển vào vị trí docs chuẩn; v2.1 archived (docs/_archive/v2.1/).
- **Change 0.3.0:** Mở rộng lên spec-level P0 bám BRD §12 + §11.8 + §13.1 (docs-first, R-DEC-09): mô tả hành vi + ràng buộc 12 năng lực CEO Assistant (§2); cấu trúc đầy đủ 7 khối Daily Briefing + bảng nguồn + ví dụ + tiêu chí chấp nhận UC-01 + luồng F1 (§3); ngữ nghĩa alert 1-1 cho từng chỉ số P0 (§4); mô tả 9 phần insight + ví dụ (§5); widget cụ thể cho 3 cấp dashboard theo `SOURCE-UIUX.md` §6.1 (§1.1); vòng đời Decision Log 30/60/90 (§7); bảng UC liên quan + tiêu chí (§8); thêm OQ-03-03/04. METRIC-* + mã alert cụ thể giữ hoãn đợt code.
- **Change 0.2.0:** Chốt Q1–Q6 (R-DEC-05..10) — cập nhật trạng thái quyết định, đóng OQ liên quan; phạm vi docs-first P0.
- **Change 0.1.0:** Viết lại 03 theo AI-EOS — 3 cấp dashboard (Executive/Department/Employee), CEO Assistant 12 năng lực đa kênh, Daily Briefing + Management Loop, bộ chỉ số sức khỏe chuẩn đầy đủ (P0/P1), insight 9 phần, D28 Reporting (PDF/Word/Excel/Google Docs), Decision Log 30/60/90 ngày.
