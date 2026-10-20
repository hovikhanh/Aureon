# 02 — Personas & Permissions

> Đặc tả **10 vai trò**, user stories hợp nhất, yêu cầu xác thực (FR-AUTH) và **ma trận quyền** dạng permission string `<domain>:<action>` của Aureon v2.
> **Canonical Source (DEC-144):** `_reference/SOURCE-BRD-v1.1.md` §3.2 (vai trò), §3.3 (RACI), §5.2 (D02 Admin & Security), §11.3 (phân loại tool), §15 (user story), §17.1 (AI governance). Kế thừa A-EMS (`SOURCE-BRD-v1.0` §I, §II.1, §III.2, §VI.3), UI/UX AI-EOS §2, §4.1. Quyết định: DEC-128 (10 role), DEC-129 (RS256), DEC-132, DEC-137, DEC-146 (mã US BRD), DEC-149/150 (AI governance), DEC-155 (ngưỡng duyệt).
> Phụ thuộc: `01-PROJECT-OVERVIEW.md`. Endpoint cụ thể do `10-API-SPECIFICATION.md` sở hữu — file này **chỉ** dùng permission string, không dùng số EP.

---

## 1. Tổng quan vai trò

| ID | Mã code | Tên | Trụ dashboard (00 §4.1) | Trang chủ (SCR-01) | Nhập liệu / hành động chính |
|---|---|---|---|---|---|
| ROLE-01 | `CEO` | Tổng giám đốc | PIL-F, PIL-O, PIL-C, PIL-U, PIL-S | Briefing công ty, 5 thẻ trụ, "Cần anh quyết", rủi ro mới, "AI đã làm" | Mục tiêu doanh thu, chấp nhận rủi ro, xác nhận cảnh báo, giao việc từ Briefing |
| ROLE-02 | `CFO` | Giám đốc tài chính | PIL-F, PIL-S | Briefing tài chính, trụ F + S, ngân sách, dự báo | Doanh thu, chi phí, ngân sách, tiền mặt, dự báo, hóa đơn; duyệt kế hoạch tuyển dụng; duyệt IDP trụ F |
| ROLE-03 | `VP_SALES` | Giám đốc kinh doanh | PIL-C | Trụ C, pipeline, deal sắp đóng | Deal, khách hàng, hợp đồng, mục tiêu doanh thu |
| ROLE-04 | `HR_MANAGER` | Trưởng phòng nhân sự | PIL-O | Trụ O (con người), tuyển dụng trễ | Phòng ban, nhân viên, lương, kế hoạch tuyển dụng; duyệt IDP nhân sự |
| ROLE-05 | `REVIEWER` | Người duyệt dữ liệu | — | Hàng chờ review (SCR-08) + SLA | Duyệt, sửa, từ chối, tách/gộp, chuyển tiếp extraction |
| ROLE-06 | `CPO` | Giám đốc sản phẩm | PIL-U | Trụ U, roadmap quý, release | Sản phẩm, tính năng, roadmap, release, chỉ số sản phẩm |
| ROLE-07 | `RISK_MANAGER` | Quản trị rủi ro | PIL-S | Trụ S, sổ rủi ro, cảnh báo chưa xác nhận | Rủi ro, đánh giá, biện pháp giảm thiểu, what-if |
| ROLE-08 | `MANAGER` | Trưởng bộ phận | Đơn vị của mình (không có dashboard điều hành) | Briefing đơn vị, hàng chờ duyệt của đơn vị, workload | Chi phí, hóa đơn, deal, khách hàng, tính năng, rủi ro, mitigation, task của bộ phận |
| ROLE-09 | `EMPLOYEE` | Nhân viên | — | Việc hôm nay, mục tiêu của tôi | Gửi chứng từ, cập nhật task, check-in KR; hỏi AI trong phạm vi của mình |
| ROLE-10 | `ADMIN` | Quản trị hệ thống | — | Tình trạng hệ thống, sự cố AI, AI Control Center (SCR-15) | User/role, loại tài liệu, schema, ngưỡng, autonomy, kill switch, provider AI |

Ghi chú:
- Mỗi user có đúng **một role chính** (`ENT-User.role`). Người kiêm nhiệm (vd. Manager kiêm Reviewer) dùng cơ chế đổi ngữ cảnh ở thanh trên (06) — v2 chỉ hỗ trợ qua chế độ demo §9; đa role thật là OQ-01.
- MANAGER và EMPLOYEE **không** có dashboard điều hành F.O.C.U.S; họ thấy dữ liệu đơn vị/cá nhân qua workspace và trang chủ riêng.
- Ánh xạ vai trò BRD §3.2 → 10 role: CEO → ROLE-01; Executive/Director → ROLE-02/03/04/06/07 theo trụ; Manager → ROLE-08; Employee → ROLE-09; Reviewer → ROLE-05; Admin → ROLE-10; **AI Agent** không phải role người dùng — danh tính riêng ở §7.3. Role tùy biến của BRD hoãn v2.1 (DEC-150; giữ 10 role DEC-128).

---

## 2. Chi tiết persona

### 2.1. ROLE-01 — CEO ("Biết ngay, quyết nhanh")

| Thuộc tính | Nội dung |
|---|---|
| Bối cảnh | 10–15 phút đầu ngày trên desktop; mobile giữa các cuộc họp; mỗi lượt 1–5 phút |
| Job-to-be-done | Khi bắt đầu ngày, tôi muốn biết "hôm nay có gì bất thường, việc gì cần tôi" để quyết và giao việc ngay |
| Nỗi đau | Phải hỏi từng người; số liệu vênh nhau; không biết việc đã giao đi đến đâu; không tin con số không rõ nguồn |
| Thành công khi | Trả lời "có gì cần tôi?" ≤ 10 giây (P07); F1 Briefing → giao việc ≤ 2 phút, ≤ 5 chạm; hỏi AI nhận câu trả lời có nguồn |
| Trang chủ | SCR-01 Briefing công ty: dòng tóm tắt 1 câu, 5 thẻ trụ, "Cần anh quyết", "Rủi ro", "AI đã làm", Panel AI |
| Màn hình chính | SCR-01..07, SCR-16, SCR-17, SCR-21, SCR-14 |

### 2.2. ROLE-02 — CFO ("Đủ tiền, tiêu hiệu quả")

| Thuộc tính | Nội dung |
|---|---|
| Bối cảnh | Desktop, hằng ngày; đóng sổ cuối tháng; chuẩn bị báo cáo HĐQT |
| Job-to-be-done | Khi dòng tiền hoặc chi tiêu lệch kế hoạch, tôi muốn biết sớm và biết nguyên nhân để điều chỉnh ngân sách/dự báo |
| Nỗi đau | Burn và runway tính tay; phòng ban vượt ngân sách mới biết; cam kết tuyển dụng không vào dự báo |
| Thành công khi | Runway, burn, ngân sách luôn cập nhật; cảnh báo burn vượt dự báo trong ngày; duyệt kế hoạch tuyển dụng trước khi đưa vào dự báo |
| Trang chủ | SCR-01 Briefing tài chính + SCR-02 trụ F + SCR-06 trụ S |
| Màn hình chính | SCR-02, SCR-06, SCR-07, SCR-22, SCR-21, SCR-10 (tài liệu trụ F) |

### 2.3. ROLE-03 — VP_SALES ("Giữ pipeline, giữ doanh thu")

| Thuộc tính | Nội dung |
|---|---|
| Bối cảnh | Desktop + mobile; họp sales hằng tuần |
| Job-to-be-done | Khi pipeline không đủ phủ mục tiêu quý, tôi muốn biết sớm deal nào, ai đang hụt để điều phối đội |
| Nỗi đau | Pipeline nằm rải rác trong Excel của từng sales; win rate không ai đo |
| Thành công khi | Pipeline coverage, win rate, hiệu suất cá nhân hiển thị theo thời gian thực; cảnh báo khi coverage < 3x |
| Trang chủ | SCR-01 Briefing kinh doanh + SCR-04 trụ C |
| Màn hình chính | SCR-04, SCR-07, SCR-23 |

### 2.4. ROLE-04 — HR_MANAGER ("Đủ người, giữ người")

| Thuộc tính | Nội dung |
|---|---|
| Bối cảnh | Desktop, hằng ngày |
| Job-to-be-done | Khi phòng ban thiếu người hoặc người giỏi nghỉ, tôi muốn biết trước để tuyển/giữ kịp |
| Nỗi đau | Kế hoạch tuyển dụng trễ không ai thấy; turnover tính cuối năm mới biết |
| Thành công khi | Cảnh báo tuyển dụng trễ > 30 ngày; turnover năm hóa và quá tải hiển thị theo tháng |
| Trang chủ | SCR-01 Briefing nhân sự + SCR-03 trụ O |
| Màn hình chính | SCR-03, SCR-07, SCR-24, SCR-19, SCR-10 (tài liệu nhân sự) |

### 2.5. ROLE-05 — REVIEWER ("Duyệt nhanh, không sai")

| Thuộc tính | Nội dung |
|---|---|
| Bối cảnh | Kế toán, thư ký, admin phòng ban; desktop màn hình lớn, bàn phím; nhiều giờ/ngày vào cao điểm |
| Job-to-be-done | Khi có tài liệu AI đã trích xuất, tôi muốn duyệt nhanh bằng bàn phím mà không sai số tiền |
| Nỗi đau | Nhập tay từ giấy; sợ sai trường tiền; phải dò vùng nguồn trên tài liệu |
| Thành công khi | Review một hóa đơn 6 trường ≤ 60 giây; SLA hàng chờ 1 ngày làm việc |
| Trang chủ | SCR-08 hàng chờ được phân + SLA |
| Màn hình chính | SCR-08, SCR-10, SCR-11, SCR-12 |

### 2.6. ROLE-06 — CPO ("Sản phẩm được dùng thật")

| Thuộc tính | Nội dung |
|---|---|
| Bối cảnh | Desktop; review roadmap hằng tuần, chỉ số hằng tháng |
| Job-to-be-done | Khi adoption giảm hoặc churn tăng bất thường, tôi muốn biết ngay để điều tra trước khi mất khách |
| Nỗi đau | Chỉ số sản phẩm nằm ở nhiều công cụ; roadmap trễ không ai tổng hợp |
| Thành công khi | MAU, churn, retention, roadmap đúng tiến độ hiển thị theo kỳ; cảnh báo churn bất thường (BR-PRD-01) |
| Trang chủ | SCR-01 Briefing sản phẩm + SCR-05 trụ U |
| Màn hình chính | SCR-05, SCR-07, SCR-25 |

### 2.7. ROLE-07 — RISK_MANAGER ("Không bỏ sót rủi ro")

| Thuộc tính | Nội dung |
|---|---|
| Bối cảnh | Desktop; rà sổ rủi ro hằng tuần, họp rủi ro hằng tháng |
| Job-to-be-done | Khi có sự kiện nghiệp vụ bất thường, tôi muốn rủi ro được tự ghi nhận, chấm điểm và có người chịu trách nhiệm |
| Nỗi đau | Sổ rủi ro Excel lỗi thời; rủi ro không có chủ; không đo được tác động liên miền |
| Thành công khi | Rủi ro tự sinh từ event; 0 rủi ro high chưa có chủ quá 7 ngày; what-if trả kết quả liên miền |
| Trang chủ | SCR-01 Briefing rủi ro + SCR-06 trụ S |
| Màn hình chính | SCR-06, SCR-07, SCR-21 |

### 2.8. ROLE-08 — MANAGER ("Giữ team đúng hướng")

| Thuộc tính | Nội dung |
|---|---|
| Bối cảnh | Desktop là chính, mobile để duyệt; hằng ngày 15–60 phút |
| Job-to-be-done | Khi team có người quá tải hoặc việc trễ, tôi muốn thấy và phân lại ngay; khi cần báo cáo lên trên, dữ liệu đã có sẵn |
| Nỗi đau | Tốn thời gian tổng hợp báo cáo; không thấy ai quá tải |
| Thành công khi | F5 xử lý quá tải ≤ 1 phút; dữ liệu bộ phận nhập một lần (P03) |
| Trang chủ | SCR-01 Briefing đơn vị: hàng chờ duyệt, workload, task trễ |
| Màn hình chính | SCR-19, SCR-20, SCR-18, SCR-08 (của đơn vị), SCR-09 |

### 2.9. ROLE-09 — EMPLOYEE ("Làm việc, ít khai báo")

| Thuộc tính | Nội dung |
|---|---|
| Bối cảnh | Mobile và desktop xen kẽ; vài phút mỗi lần |
| Job-to-be-done | Khi có chứng từ hoặc tiến độ, tôi muốn gửi trong ≤ 3 chạm / ≤ 10 giây rồi quay lại làm việc |
| Nỗi đau | Nhập liệu lặp lại, báo cáo nhiều nơi |
| Thành công khi | F4 check-in ≤ 30 giây; gửi chứng từ ≤ 3 chạm trên mobile |
| Trang chủ | SCR-01 "Việc hôm nay" + mục tiêu của tôi |
| Màn hình chính | SCR-09, SCR-19 (task của tôi), SCR-20 (KR của tôi), SCR-16, SCR-28 |

### 2.10. ROLE-10 — ADMIN ("Cấu hình an toàn")

| Thuộc tính | Nội dung |
|---|---|
| Bối cảnh | Desktop, theo đợt (thiết lập ban đầu, thay đổi chính sách) |
| Job-to-be-done | Khi cấu hình tổ chức, quyền, AI policy, tôi muốn chắc AI không vượt quyền và mọi thay đổi có audit |
| Nỗi đau | Sợ AI hành động vượt quyền; khó kiểm tra quyền thực tế |
| Thành công khi | Thêm doc type mới không cần code; một thao tác bật kill switch; xem được audit log đầy đủ |
| Trang chủ | SCR-01 tình trạng hệ thống, sự cố AI |
| Màn hình chính | SCR-15, SCR-26, SCR-27, SCR-14 |

**ADMIN không có quyền đọc dữ liệu nghiệp vụ** (không xem doanh thu, lương, deal) — tách người cấu hình khỏi người dùng dữ liệu (§6.2).

---

## 3. User stories hợp nhất

Quy ước: mã `US-<AREA>-nnn` theo registry 00 §4.11 (DEC-146): **001–099 = mã BRD §15**, **101+ = story chỉ có ở docs**; mã cũ v2.0.0 → mã mới ở 00 §4.13.1. Ưu tiên **Must / Should / Could** (A-EMS). Cột "Nguồn": `A` = A-EMS, `E` = AI-EOS / UIUX, `v2` = bổ sung khi hợp nhất. Cột "Phạm vi": `v2.0` · `v2.0 lite` · `[v2.1]` · `[OUT]` (01 §3). §3.1–3.11 giữ tiêu chí nghiệm thu chi tiết của 50 story đã có; §3.13 liệt kê 94 story BRD còn lại theo role. User story IDP (`US-DC-001..012`) do `04-IDP-FEATURE-SPEC.md` sở hữu — xem §3.12.

### 3.1. CEO (ROLE-01)

| ID | User story | Tiêu chí nghiệm thu chính | Ưu tiên | Nguồn | Phạm vi |
|---|---|---|---|---|---|
| US-CEO-101 | Là CEO, tôi muốn xem toàn cảnh 5 trụ F.O.C.U.S trên một màn hình, để không phải rà nhiều báo cáo rời rạc | 5 thẻ trụ, mỗi thẻ có KPI chính + trạng thái ok/warning/critical (FR-DSH-01/02) | Must | A | v2.0 |
| US-CEO-002 | Là CEO, tôi muốn thấy insight cảnh báo ngay đầu dashboard, để biết điều bất thường mà không phải tự tìm | Briefing ở đầu SCR-01; mục "bình thường" gộp 1 dòng (P07) | Must | A, E | v2.0 |
| US-CEO-001 | Là CEO, tôi muốn hỏi AI câu hỏi liên phòng ban và nhận câu trả lời kèm nguồn số liệu | Mọi số trong câu trả lời có source chip; AI chỉ dùng quyền của tôi (P05, P06) | Must | A | v2.0 |
| US-CEO-102 | Là CEO, tôi muốn hỏi "Runway bao nhiêu tháng nếu tháng sau không có doanh thu mới" | AI trả lời theo BR-FIN-06, có nguồn | Should | A | v2.0 |
| US-CEO-103 | Là CEO, tôi muốn drill-down từ mỗi trụ xuống dữ liệu chi tiết và tài liệu gốc | ≤ 3 click từ thẻ trụ → bản ghi → trang tài liệu (P01) | Must | A, E | v2.0 |
| US-CEO-104 | Là CEO, tôi muốn chạy what-if tác động của rủi ro lên tài chính, nhân sự, sản phẩm | Kết quả theo miền; miền lỗi trả `unavailable` (FR-RSK-06) | Should | A | v2.0 |
| US-CEO-105 | Là CEO, tôi muốn chấp nhận một rủi ro kèm lý do, để ghi nhận quyết định chính thức | Chỉ CEO đặt `accepted`; bắt buộc lý do; ghi audit + Decision log | Should | A | v2.0 |
| US-CEO-106 | Là CEO, tôi muốn đặt mục tiêu doanh thu theo kỳ, để hệ thống đo hoàn thành và pipeline coverage | `ENT-SalesTarget` kỳ month/quarter/year; dùng cho METRIC-FIN-01, METRIC-CUS-01 | Should | A | v2.0 |

### 3.2. CFO (ROLE-02)

| ID | User story | Tiêu chí nghiệm thu chính | Ưu tiên | Nguồn | Phạm vi |
|---|---|---|---|---|---|
| US-FIN-001 | Là CFO, tôi muốn ghi doanh thu, chi phí và số dư tiền mặt cuối kỳ, để hệ thống tính đúng lợi nhuận, burn, runway | BR-FIN-01..03 tính tự động | Must | A | v2.0 |
| US-FIN-002 | Là CFO, tôi muốn đặt ngân sách theo phòng ban và quý, và được cảnh báo khi phòng ban vượt ngân sách | `EVT-finance.budget_exceeded`; ALERT-FIN-06 | Must | A | v2.0 |
| US-FIN-101 | Là CFO, tôi muốn xem dự báo theo horizon và kịch bản lạc quan/cơ sở/bi quan | `ENT-Forecast` horizon 1m/3m/6m/1y × 3 kịch bản | Must | A | v2.0 |
| US-FIN-102 | Là CFO, tôi muốn được cảnh báo khi Net Burn dự kiến vượt dự báo quá ngưỡng (mặc định 10%) | ALERT-FIN-07, tối đa 1 lần/ngày | Should | A | v2.0 |
| US-FIN-103 | Là CFO, tôi muốn quản lý hóa đơn và trạng thái thanh toán, để theo dõi tiền thực thu | `EVT-finance.invoice_paid`; METRIC-FIN-04/05 | Should | A | v2.0 |
| US-FIN-104 | Là CFO, tôi muốn phê duyệt kế hoạch tuyển dụng trước khi chi phí lương dự kiến vào dự báo | §8; duyệt/từ chối bắt buộc lý do | Could | A | v2.0 |

### 3.3. VP_SALES (ROLE-03)

| ID | User story | Tiêu chí nghiệm thu chính | Ưu tiên | Nguồn | Phạm vi |
|---|---|---|---|---|---|
| US-SAL-002 | Là VP Sales, tôi muốn quản lý deal và chuyển giai đoạn trong pipeline | Lưu `ENT-DealStageHistory`; won/lost phát event | Must | A | v2.0 |
| US-SAL-101 | Là VP Sales, tôi muốn quản lý danh sách khách hàng, để gắn deal đúng khách | Tên khách duy nhất; khớp mờ khi nhập (IDP, 04) | Must | A | v2.0 |
| US-SAL-003 | Là VP Sales, tôi muốn xem pipeline theo giai đoạn, win rate và hiệu suất từng người | FR-SAL-04/05/07 | Must | A | v2.0 |
| US-SAL-102 | Là VP Sales, tôi muốn được cảnh báo khi pipeline < 2,8 lần mục tiêu quý (DEC-143) hoặc win rate giảm bất thường | ALERT-CUS-01, ALERT-CUS-02 | Should | A | v2.0 |

### 3.4. HR_MANAGER (ROLE-04)

| ID | User story | Tiêu chí nghiệm thu chính | Ưu tiên | Nguồn | Phạm vi |
|---|---|---|---|---|---|
| US-HR-101 | Là HR Manager, tôi muốn quản lý hồ sơ nhân viên và lịch sử lương | `ENT-Employee`, `ENT-SalaryHistory`; đổi lương phát `EVT-hr.salary_updated` | Must | A | v2.0 |
| US-HR-102 | Là HR Manager, tôi muốn tạo và theo dõi kế hoạch tuyển dụng theo phòng ban so với định biên | `ENT-HiringPlan` có `filled`/`headcount` | Must | A | v2.0 |
| US-HR-103 | Là HR Manager, tôi muốn hệ thống tự cảnh báo khi kế hoạch tuyển dụng trễ > 30 ngày | `EVT-hr.hiring_plan_delayed`; ALERT-HR-04 | Must | A | v2.0 |
| US-HR-104 | Là HR Manager, tôi muốn theo dõi turnover năm hóa và được cảnh báo khi vượt ngưỡng | BR-HR-01; ALERT-HR-02 | Should | A | v2.0 |

### 3.5. CPO (ROLE-06)

| ID | User story | Tiêu chí nghiệm thu chính | Ưu tiên | Nguồn | Phạm vi |
|---|---|---|---|---|---|
| US-PRD-001 | Là CPO, tôi muốn quản lý sản phẩm, tính năng, roadmap theo quý và release | FR-PRD-01..04 | Must | A | v2.0 |
| US-PRD-101 | Là CPO, tôi muốn ghi chỉ số sản phẩm theo kỳ (MAU, adoption, churn, retention, NPS, ARPU) | Snapshot chỉ thêm (`ENT-ProductMetric`) | Must | A | v2.0 |
| US-PRD-102 | Là CPO, tôi muốn được cảnh báo khi churn tăng bất thường | BR-PRD-01 (> 50% tương đối **và** ≥ 2%); ALERT-PRD-02 | Must | A | v2.0 |

### 3.6. RISK_MANAGER (ROLE-07)

| ID | User story | Tiêu chí nghiệm thu chính | Ưu tiên | Nguồn | Phạm vi |
|---|---|---|---|---|---|
| US-GOV-003 | Là Risk Manager, tôi muốn ghi rủi ro và để hệ thống tự chấm điểm, phân mức | BR-RSK-01 `score = likelihood × impact` | Must | A | v2.0 |
| US-GOV-101 | Là Risk Manager, tôi muốn hệ thống tự sinh rủi ro từ sự kiện nghiệp vụ | BR-RSK-03; idempotent theo `event_id` | Must | A | v2.0 |
| US-GOV-102 | Là Risk Manager, tôi muốn quản lý biện pháp giảm thiểu và xác nhận cảnh báo đến khi đóng | Không đóng rủi ro còn mitigation `in_progress` | Must | A | v2.0 |

### 3.7. MANAGER (ROLE-08)

| ID | User story | Tiêu chí nghiệm thu chính | Ưu tiên | Nguồn | Phạm vi |
|---|---|---|---|---|---|
| US-MGR-101 | Là Manager, tôi muốn nhập chi phí, hóa đơn, deal, tính năng, rủi ro của bộ phận mình | Bản ghi gắn `department_id` của tôi; ngoài đơn vị → 403 | Must | A | v2.0 |
| US-TASK-003 | Là Manager, tôi muốn thấy heatmap workload team và nhận gợi ý chuyển task khi có người quá tải | F5 ≤ 1 phút; gợi ý L1 (suggestion chip) | Should | E | v2.0 |
| US-MGR-102 | Là Manager, tôi muốn duyệt dữ liệu/check-in do nhân viên đơn vị gửi lên | Hàng chờ chỉ chứa tài liệu của đơn vị; trường trọng yếu tài chính vẫn cần REVIEWER/CFO | Should | E | v2.0 |

### 3.8. EMPLOYEE (ROLE-09)

| ID | User story | Tiêu chí nghiệm thu chính | Ưu tiên | Nguồn | Phạm vi |
|---|---|---|---|---|---|
| US-TASK-002 | Là nhân viên, tôi muốn thấy "việc hôm nay" và mục tiêu của tôi ngay khi mở app | SCR-01 chỉ dữ liệu `owner = tôi` | Must | E | v2.0 |
| US-DC-009 | Là nhân viên, tôi muốn gửi chứng từ (chụp/thả file/nói) trong ≤ 3 chạm | Tài liệu kế thừa quyền của tôi; tôi theo dõi được trạng thái | Must | E | v2.0 |
| US-OKR-006 | Là nhân viên, tôi muốn check-in KR và cập nhật task trong ≤ 30 giây | F4; giá trị AI điền sẵn, tôi xác nhận | Should | E | v2.0 lite — bằng lời nói v2.1 |

### 3.9. ADMIN (ROLE-10)

| ID | User story | Tiêu chí nghiệm thu chính | Ưu tiên | Nguồn | Phạm vi |
|---|---|---|---|---|---|
| US-ADM-101 | Là Admin, tôi muốn tạo user và gán/đổi role (không có self-register) | FR-AUTH-05; DEC-137; ghi audit | Must | A, v2 | v2.0 |
| US-AI-004 | Là Admin, tôi muốn cấu hình autonomy theo tool × role × ngưỡng giá trị | `ENT-AutonomyPolicy`; L4 bị khóa | Must | E | v2.0 lite — tool × role; theo agent v2.1 — DEC-150 |
| US-AI-007 | Là Admin, tôi muốn một thao tác bật kill switch tắt mọi hành động WRITE của AI | L3 → L2 toàn hệ thống; băng thông báo đầu app; ghi audit | Must | E | v2.0 |
| US-ADM-102 | Là Admin, tôi muốn xem audit log và "xem như người dùng" để kiểm tra quyền | SCR-14; công cụ preview quyền chỉ đọc (không xem dữ liệu nghiệp vụ thật) | Should | E | v2.0 |

### 3.10. Yêu cầu chung (mọi role)

| ID | User story | Tiêu chí nghiệm thu chính | Ưu tiên | Nguồn | Phạm vi |
|---|---|---|---|---|---|
| US-ALL-101 | Là người dùng, tôi chỉ thấy dữ liệu trong phạm vi quyền, kể cả khi hỏi qua AI | §5–§7; test leak theo từng role | Must | A | v2.0 |
| US-ALL-102 | Là người dùng, tôi muốn xem lại và xóa hội thoại AI của mình | Chỉ chủ hội thoại đọc/xóa | Should | A | v2.0 |
| US-ALL-103 | Là người dùng, tôi muốn đánh giá câu trả lời AI (hữu ích/không + lý do) | Lý do: `inaccurate_number`, `missing_context`, `too_verbose`, `not_relevant`, `other` | Could | A | v2.0 |
| US-ALL-104 | Là người dùng, tôi muốn dashboard vẫn dùng được khi AI hoặc một module lỗi | Chỉ widget lỗi báo "Dịch vụ tạm thời không khả dụng" (P08) | Must | A | v2.0 |

### 3.11. Trợ lý AI (mọi role có `ai:query`)

| ID | User story | Tiêu chí nghiệm thu chính | Ưu tiên | Nguồn | Phạm vi |
|---|---|---|---|---|---|
| US-AI-101 | Là người dùng, tôi muốn hỏi AI ở mọi màn hình (⌘K) và AI hiểu ngữ cảnh đang xem | Panel hiển thị "AI đang xem: …" | Must | E | v2.0 |
| US-AI-102 | Là người dùng, tôi muốn thấy AI đang làm gì (bước tra cứu thật) và dừng được | SSE `thinking/tool_call/tool_result`; nút Dừng | Must | A, E | v2.0 |
| US-AI-103 | Là người dùng, tôi muốn phân biệt rõ AI gợi ý / AI soạn chờ xác nhận / AI đã làm | Mẫu giao diện cố định theo L1/L2/L3 (P02) | Must | E | v2.0 |
| US-AI-104 | Là người dùng, tôi muốn hoàn tác hành động AI đã làm (L3) trong 24 giờ | Feed "AI đã làm" (SCR-17); DEC-134 | Must | E | v2.0 |
| US-AI-105 | Là người dùng, tôi muốn AI trả lời bằng ngôn ngữ câu hỏi và nói rõ khi thiếu dữ liệu | VI/EN (DEC-135); không bịa số (P05) | Should | A, E | v2.0 |

### 3.13. Story BRD còn lại theo role chính (94 story — 00 §4.11.1)

Tiêu chí nghiệm thu chi tiết của các story này do spec chức năng sở hữu (03 domain/dashboard, 04 IDP, 06 UI) và được bổ sung ở Phase 3c–3d. Cột "Role chính" ánh xạ actor BRD → 10 role DEC-128 ("Finance Manager" → CFO, "Sales/Legal" → VP_SALES, "Product Manager" → CPO, "Governance/Compliance/Risk Manager" → RISK_MANAGER, "Trưởng phòng/bộ phận" → MANAGER; "AI" = agent `assistant`, chạy bằng quyền người được phục vụ — §7). Tag: `v2.0` · `v2.0 lite` · `[v2.1]` · `[OUT]` (01 §3).

| ID | User story (BRD §15) | Role chính | Ưu tiên BRD | Phạm vi | Ghi chú |
|---|---|---|---|---|---|
| US-ORG-001 | Là CEO, tôi muốn định nghĩa cơ cấu tổ chức (công ty, phòng ban, team, quản lý, nhân viên, reporting line) | CEO | P0 | v2.0 lite | Team/Position; không ma trận, không effective-dated — DEC-147 |
| US-ORG-002 | Là Admin, tôi muốn cấu hình vai trò và quyền | ADMIN | P0 | v2.0 lite | gán 10 role cố định; role tùy biến v2.1 — DEC-150 |
| US-ORG-003 | Là Admin, tôi muốn định nghĩa phạm vi truy cập của AI theo phòng ban và vai trò | ADMIN | P0 | [v2.1] | quyền agent ∩ người — DEC-150 |
| US-ORG-004 | Là Admin, tôi muốn dựng cơ cấu từ sơ đồ tổ chức và danh sách nhân sự có sẵn | ADMIN | P0 | v2.0 | UC-07 |
| US-DC-001 | Là Employee, tôi muốn nhập dữ liệu qua form có kiểm tra tức thì | EMPLOYEE | P0 | v2.0 |  |
| US-DC-002 | Là Manager, tôi muốn nói hoặc gõ một câu để AI tạo bản ghi, chỉ ghi sau khi tôi xác nhận | MANAGER | P0 | v2.0 lite | gõ v2.0; nói (C2) v2.1 — DEC-153 |
| US-DC-003 | Là User, tôi muốn tải PDF, Word, ảnh để AI tự trích xuất dữ liệu | Mọi role | P0 | v2.0 |  |
| US-DC-004 | Là Manager, tôi muốn tải biên bản họp để AI tạo task, giao người và đặt hạn | MANAGER | P0 | v2.0 |  |
| US-DC-005 | Là Manager, tôi muốn tải file kế hoạch KPI/OKR hiện có thay vì nhập lại | MANAGER | P0 | v2.0 |  |
| US-DC-006 | Là Reviewer, tôi muốn xem tài liệu gốc cạnh dữ liệu AI trích để duyệt nhanh | REVIEWER | P0 | v2.0 |  |
| US-DC-007 | Là Admin, tôi muốn import danh sách từ Excel với AI tự map cột | ADMIN | P0 | v2.0 |  |
| US-DC-008 | Là Admin, tôi muốn cấu hình loại tài liệu, schema và ngưỡng tự ghi không cần code | ADMIN | P0 | v2.0 |  |
| US-DC-010 | Là Finance, tôi muốn tải hoặc chuyển tiếp hóa đơn để AI ghi chi phí và công nợ | CFO | P1 | v2.0 | UC-08 bản demo |
| US-DC-011 | Là Legal/Sales, tôi muốn tải hợp đồng để AI trích giá trị, mốc thanh toán, hạn gia hạn | VP_SALES | P1 | v2.0 |  |
| US-DC-012 | Là bộ phận, tôi muốn chuyển tiếp email có đính kèm vào hệ thống | MANAGER | P1 | [OUT] | C6 email — 01 §3 |
| US-FIN-003 | Là CFO, tôi muốn theo dõi dòng tiền và runway | CFO | P0 | v2.0 | gồm dòng tiền 13 tuần — DEC-148 |
| US-FIN-004 | Là CEO, tôi muốn AI phân tích hiệu quả tài chính | CEO | P1 | [v2.1] |  |
| US-FIN-005 | Là CEO, tôi muốn AI phát hiện rủi ro tài chính | CEO | P1 | [v2.1] |  |
| US-HR-001 | Là HR, tôi muốn quản lý vòng đời nhân sự | HR_MANAGER | P1 | v2.0 lite | hồ sơ + lịch sử lương; vòng đời đầy đủ v2.1 |
| US-HR-002 | Là HR, tôi muốn quản lý vị trí trong tổ chức | HR_MANAGER | P0 | v2.0 | DEC-147 |
| US-HR-003 | Là Manager, tôi muốn xem workload của nhân viên | MANAGER | P0 | v2.0 |  |
| US-HR-004 | Là CEO, tôi muốn AI nhận diện rủi ro nhân lực | CEO | P1 | [v2.1] |  |
| US-HR-005 | Là HR, tôi muốn xác định thiếu hụt kỹ năng | HR_MANAGER | P1 | [v2.1] | dữ liệu kỹ năng có ở v2.0 (ENT-EmployeeSkill) |
| US-SAL-001 | Là Sales, tôi muốn quản lý lead | VP_SALES | P1 | [v2.1] |  |
| US-SAL-004 | Là CEO, tôi muốn AI dự báo doanh thu | CEO | P1 | [v2.1] |  |
| US-SAL-005 | Là Sales Manager, tôi muốn AI gợi ý next-best-action | VP_SALES | P1 | [v2.1] |  |
| US-CUS-001 | Là CEO, tôi muốn biết khách nào có nguy cơ churn hoặc cần tôi follow-up | CEO | P1 | [v2.1] |  |
| US-PTN-001 | Là Partner Manager, tôi muốn theo dõi hiệu quả và hoa hồng đối tác | — (OUT) | P1 | [OUT] | Partner — GAP C-24 |
| US-PRC-001 | Là Trưởng phòng, tôi muốn tạo đề nghị mua sắm và theo dõi phê duyệt | MANAGER | P1 | [OUT] | Procurement — 01 §3 |
| US-CTR-001 | Là CFO, tôi muốn được nhắc trước hạn thanh toán và gia hạn hợp đồng | CFO | P1 | [v2.1] | contract xuyên domain — DEC-148 |
| US-PRD-002 | Là Product Manager, tôi muốn quản lý yêu cầu | CPO | P1 | [v2.1] |  |
| US-PRD-003 | Là Product Manager, tôi muốn AI phân tích phản hồi khách hàng | CPO | P1 | [v2.1] |  |
| US-PRD-004 | Là CPO, tôi muốn AI nhận diện rủi ro sản phẩm | CPO | P1 | [v2.1] |  |
| US-ENG-001 | Là Engineering Manager, tôi muốn quản lý dự án kỹ thuật | — (OUT) | P1 | [OUT] | Technical domain — GAP C-24 |
| US-ENG-002 | Là Engineering Manager, tôi muốn theo dõi delivery | — (OUT) | P1 | [OUT] | Technical domain |
| US-ENG-003 | Là CTO, tôi muốn theo dõi technical debt | — (OUT) | P1 | [OUT] | Technical domain |
| US-ENG-004 | Là CTO, tôi muốn AI phát hiện rủi ro delivery | — (OUT) | P1 | [OUT] | Technical domain |
| US-GOV-001 | Là Governance Manager, tôi muốn quản lý chính sách và control | RISK_MANAGER | P2 | [OUT] | P2 |
| US-GOV-002 | Là Compliance Manager, tôi muốn theo dõi bằng chứng | RISK_MANAGER | P2 | [OUT] | P2 |
| US-GOV-004 | Là CEO, tôi muốn AI tóm tắt rủi ro quản trị | CEO | P1 | [v2.1] |  |
| US-STR-001 | Là CEO, tôi muốn định nghĩa mục tiêu chiến lược | CEO | P0 | v2.0 | DEC-147 |
| US-STR-002 | Là CEO, tôi muốn định nghĩa initiative chiến lược | CEO | P0 | v2.0 | ENT-Initiative — DEC-147 |
| US-STR-003 | Là CEO, tôi muốn theo dõi thực thi chiến lược | CEO | P0 | v2.0 |  |
| US-STR-004 | Là CEO, tôi muốn AI đánh giá thực thi chiến lược và chạy mô phỏng what-if | CEO | P1 | [v2.1] | what-if runway/rủi ro đã có (US-CEO-104) |
| US-KPI-001 | Là CEO/Manager, tôi muốn định nghĩa KPI | CEO | P0 | v2.0 |  |
| US-KPI-002 | Là Manager, tôi muốn cấu hình target KPI | MANAGER | P0 | v2.0 | ENT-KPITarget |
| US-KPI-003 | Là Manager, tôi muốn cấu hình trọng số KPI | MANAGER | P0 | v2.0 |  |
| US-KPI-004 | Là Manager, tôi muốn cấu hình phương pháp đo và nguồn dữ liệu KPI | MANAGER | P0 | v2.0 |  |
| US-KPI-005 | Là Manager, tôi muốn theo dõi giá trị thực tế KPI | MANAGER | P0 | v2.0 |  |
| US-KPI-006 | Là Manager, tôi muốn đánh giá KPI theo rule | MANAGER | P0 | v2.0 | evaluation bands — DEC-147 |
| US-KPI-007 | Là CEO, tôi muốn so sánh KPI giữa phòng ban | CEO | P0 | v2.0 |  |
| US-KPI-008 | Là AI, tôi muốn phát hiện bất thường KPI | AI | P0 | v2.0 | insight |
| US-KPI-009 | Là AI, tôi muốn xác định nguyên nhân gốc của KPI yếu | AI | P0 | v2.0 | insight 9 phần — DEC-149 |
| US-KPI-010 | Là AI, tôi muốn khuyến nghị hành động khắc phục | AI | P0 | v2.0 |  |
| US-OKR-001 | Là CEO, tôi muốn định nghĩa Objective công ty | CEO | P0 | v2.0 |  |
| US-OKR-002 | Là Manager, tôi muốn định nghĩa Objective phòng ban | MANAGER | P0 | v2.0 |  |
| US-OKR-003 | Là Manager, tôi muốn định nghĩa Key Result | MANAGER | P0 | v2.0 |  |
| US-OKR-004 | Là Manager, tôi muốn theo dõi tiến độ KR | MANAGER | P0 | v2.0 |  |
| US-OKR-005 | Là CEO, tôi muốn xem sơ đồ alignment OKR | CEO | P0 | v2.0 |  |
| US-OKR-007 | Là Manager, tôi muốn thực hiện check-in OKR | MANAGER | P0 | v2.0 |  |
| US-OKR-008 | Là AI, tôi muốn phát hiện OKR có rủi ro | AI | P0 | v2.0 |  |
| US-OKR-009 | Là AI, tôi muốn khuyến nghị hành động khắc phục | AI | P0 | v2.0 |  |
| US-PERF-001 | Là CEO/HR, tôi muốn chọn khung KPI, OKR hoặc hybrid cho từng phòng ban | CEO | P0 | [v2.1] | khung KPI/OKR theo phòng ban (GAP C-06) |
| US-PERF-002 | Là HR, tôi muốn định nghĩa chu kỳ đánh giá | HR_MANAGER | P1 | [v2.1] |  |
| US-PERF-003 | Là Employee, tôi muốn tự đánh giá | EMPLOYEE | P1 | [v2.1] |  |
| US-PERF-004 | Là Manager, tôi muốn đánh giá nhân viên với bằng chứng do AI tổng hợp | MANAGER | P1 | [v2.1] |  |
| US-PERF-005 | Là HR, tôi muốn thực hiện calibration | HR_MANAGER | P1 | [v2.1] |  |
| US-PERF-006 | Là CEO, tôi muốn AI phân tích hiệu suất toàn tổ chức | CEO | P0 | [v2.1] | AI không chấm điểm cá nhân — DEC-149 |
| US-TASK-001 | Là Manager, tôi muốn tạo và giao task | MANAGER | P0 | v2.0 |  |
| US-TASK-004 | Là AI, tôi muốn đề xuất phân bổ lại task | AI | P0 | v2.0 | gợi ý L1 |
| US-TASK-005 | Là AI, tôi muốn phát hiện task quá hạn và nhắc việc | AI | P0 | v2.0 |  |
| US-TASK-006 | Là CEO, tôi muốn xem tình trạng thực thi toàn doanh nghiệp | CEO | P0 | v2.0 |  |
| US-MTG-001 | Là User, tôi muốn AI tóm tắt cuộc họp từ transcript hoặc biên bản | Mọi role | P0 | v2.0 | transcript mock upload — DEC-153 |
| US-MTG-002 | Là Manager, tôi muốn AI trích quyết định và action item rồi giao việc | MANAGER | P0 | v2.0 |  |
| US-MTG-003 | Là User, tôi muốn AI tham gia Google Meet để ghi và tóm tắt | Mọi role | P1 | [OUT] | Meet bot |
| US-CAL-001 | Là User, tôi muốn đồng bộ Google/Outlook Calendar và thấy deadline trên lịch | Mọi role | P0 | [v2.1] | DEC-153 |
| US-CAL-002 | Là User, tôi muốn AI phát hiện trùng lịch và nhắc sự kiện quan trọng | Mọi role | P0 | [v2.1] | DEC-153 |
| US-AI-001 | Là AI Agent, tôi muốn khám phá các tool khả dụng | AI | P0 | v2.0 |  |
| US-AI-002 | Là AI Agent, tôi muốn truy xuất dữ liệu doanh nghiệp được phép | AI | P0 | v2.0 |  |
| US-AI-003 | Là AI Agent, tôi muốn thực hiện hành động được phép | AI | P0 | v2.0 |  |
| US-AI-005 | Là Admin, tôi muốn cấu hình phê duyệt cho tool tác động cao | ADMIN | P0 | v2.0 | 2 người duyệt cho finance > ngưỡng — DEC-149 |
| US-AI-006 | Là Admin, tôi muốn audit mọi tool call của AI | ADMIN | P0 | v2.0 |  |
| US-AI-008 | Là Admin, tôi muốn theo dõi chất lượng và chi phí AI theo agent | ADMIN | P0 | v2.0 lite | 1 agent profile — DEC-150 |
| US-CEO-003 | Là CEO, tôi muốn AI tóm tắt hiệu suất công ty và rủi ro | CEO | P0 | v2.0 |  |
| US-CEO-004 | Là CEO, tôi muốn AI khuyến nghị hành động chiến lược | CEO | P0 | v2.0 |  |
| US-CEO-005 | Là CEO, tôi muốn AI tạo task và nhắc cam kết | CEO | P0 | v2.0 |  |
| US-CEO-006 | Là CEO, tôi muốn biết quyết định nào đang chờ mình | CEO | P0 | v2.0 | hàng chờ phê duyệt — DEC-153 |
| US-CEO-007 | Là CEO, tôi muốn mọi con số AI báo cáo đều truy được nguồn gốc | CEO | P0 | v2.0 |  |
| US-CEO-008 | Là CEO, tôi muốn xem lại quyết định cũ và kết quả thực tế | CEO | P0 | v2.0 lite | Decision review_at |
| US-RPT-001 | Là CEO, tôi muốn tạo báo cáo điều hành và HĐQT | CEO | P0 | v2.0 lite | weekly/monthly PDF + Excel — DEC-153 |
| US-RPT-002 | Là Manager, tôi muốn tạo báo cáo phòng ban | MANAGER | P0 | v2.0 lite |  |
| US-RPT-003 | Là HR, tôi muốn báo cáo hiệu suất | HR_MANAGER | P1 | [v2.1] |  |
| US-RPT-004 | Là CFO, tôi muốn báo cáo tài chính quản trị | CFO | P1 | [v2.1] |  |
| US-RPT-005 | Là AI, tôi muốn tự tạo báo cáo định kỳ | AI | P0 | v2.0 | báo cáo định kỳ tự động |

### 3.12. Data Capture & IDP (tham chiếu)

`US-DC-001..012` (BRD epic B — form, nói/gõ, upload, biên bản → task, KPI/OKR, review song song, import Excel, cấu hình schema, chụp chứng từ, hóa đơn, hợp đồng, email `[OUT]`; danh sách ở §3.13) được đặc tả ở `04-IDP-FEATURE-SPEC.md`. Quyền thực hiện các story này theo domain `idp` ở §5.

---

## 4. Xác thực & tài khoản (FR-AUTH)

| ID | Tính năng | Mô tả / quy tắc | Actor | Ưu tiên |
|---|---|---|---|---|
| FR-AUTH-01 | Đăng nhập | Email + mật khẩu; trả JWT **RS256** (DEC-129) với payload `sub, email, role, permissions[], iat, exp`; access token ngắn hạn | Mọi user | Must |
| FR-AUTH-02 | Refresh / Logout | Refresh token (`ENT-RefreshToken`) xoay vòng; logout thu hồi refresh token | Mọi user | Must |
| FR-AUTH-03 | Hồ sơ cá nhân | Xem/cập nhật hồ sơ; đổi mật khẩu ≥ 8 ký tự, đủ chữ hoa, chữ thường, số, ký tự đặc biệt | Mọi user | Must |
| FR-AUTH-04 | Không đăng ký công khai | **Không** có self-register (DEC-137); mọi tài khoản do ADMIN/CEO tạo | — | Must |
| FR-AUTH-05 | Gán và đổi role | Chỉ ROLE-10 ADMIN và ROLE-01 CEO tạo user, gán/đổi role trong 10 role; không ai tự đổi role của chính mình; mọi thay đổi ghi audit | ADMIN, CEO | Must |

Quy tắc bổ sung:
- Public chỉ gồm: health check và login (giữ ngoại lệ DEC-080). Mọi request khác bắt buộc Bearer token.
- `permissions[]` trong JWT được sinh từ ma trận §5 tại thời điểm cấp token; đổi role → token cũ bị thu hồi ở lần refresh kế tiếp.
- Rate limit login theo IP + email; khóa tạm sau 5 lần sai liên tiếp (giá trị cấu hình).

---

## 5. Ma trận quyền

### 5.1. Định nghĩa action

Permission string có dạng `<domain>:<action>` (A-EMS §III.2, mở rộng `approve`, `admin`). Domain ∈ `finance, sales, hr, product, risk, execution, idp, ai, dashboard, platform` (khớp module DEC-125; `ai` = module `ai_core`).

| Action | Ý nghĩa | Ví dụ |
|---|---|---|
| `read` | Đọc **bản ghi chi tiết** của domain (danh sách, chi tiết, lịch sử) | Danh sách hóa đơn, hồ sơ nhân viên |
| `write` | Tạo / sửa / xóa (mềm) bản ghi của domain | Tạo deal, ghi chi phí |
| `query` | Đọc **dữ liệu tổng hợp**: dashboard domain, KPI, chuỗi trend, chạy mô hình (what-if). Không trả bản ghi cá nhân | Finance dashboard, what-if rủi ro |
| `approve` | Duyệt một đối tượng trong workflow của domain | CFO duyệt kế hoạch tuyển dụng; CEO chấp nhận rủi ro; duyệt extraction |
| `admin` | Cấu hình domain: danh mục, ngưỡng, policy | Schema tài liệu, ngưỡng alert, autonomy |

### 5.2. Danh mục permission hợp lệ

Chỉ các permission dưới đây tồn tại; mọi tổ hợp khác coi là không định nghĩa (default deny).

| Permission | Cho phép | Ghi chú |
|---|---|---|
| `finance:read` | Đọc doanh thu, chi phí, ngân sách, dự báo, hóa đơn, số dư tiền mặt | |
| `finance:write` | Ghi các entity finance | Ghi qua IDP vẫn phải đi Action Registry |
| `finance:query` | Finance dashboard, trend, metric PIL-F | |
| `sales:read` / `sales:write` / `sales:query` | Khách hàng, deal, lịch sử giai đoạn, mục tiêu, hợp đồng / ghi / dashboard PIL-C | |
| `hr:read` / `hr:write` / `hr:query` | Phòng ban, nhân viên, lịch sử lương, kế hoạch tuyển dụng / ghi / dashboard HR | Lương chịu thêm quy tắc §6.3 |
| `hr:approve` | Duyệt/từ chối `ENT-HiringPlan` | §8 |
| `product:read` / `product:write` / `product:query` | Sản phẩm, tính năng, roadmap, release, chỉ số / ghi / dashboard PIL-U | |
| `risk:read` / `risk:write` / `risk:query` | Sổ rủi ro, đánh giá, mitigation / ghi / dashboard PIL-S + chạy what-if | |
| `risk:approve` | Đặt rủi ro `accepted` (bắt buộc lý do) | BR-RSK-02 ở 03 (mức độ & vòng đời rủi ro) |
| `execution:read` / `execution:write` / `execution:query` | Họp, quyết định, task, dự án, OKR/KPI, check-in / ghi / workload, tổng hợp thực thi | |
| `idp:read` | Xem tài liệu nguồn, extraction, lineage tới trang tài liệu | |
| `idp:write` | Gửi dữ liệu (C1–C5), sửa extraction nháp, tách/gộp | |
| `idp:approve` | Duyệt / từ chối / commit / hoàn tác extraction | Phạm vi theo trụ §5.3 |
| `idp:admin` | Loại tài liệu, extraction schema, validation rule, ngưỡng confidence/STP | |
| `ai:query` | Dùng trợ lý AI (⌘K, Panel, Chat), xem insight | Tool khả dụng lọc theo các permission khác (§7) |
| `ai:write` | Xác nhận action card L2, hoàn tác hành động L3 | Vẫn cần `write` của domain đích |
| `ai:admin` | Autonomy policy, kill switch, provider, ngân sách AI | |
| `dashboard:read` | Xem trang trụ F.O.C.U.S, metric, alert, Briefing | Lọc theo trụ (§5.4) |
| `dashboard:write` | Xác nhận (acknowledge) / bỏ qua alert, chọn 4 chỉ số Briefing cá nhân | |
| `dashboard:admin` | Cấu hình ngưỡng warning/critical của metric/alert (biến cấu hình) | |
| `platform:read` | Xem audit log | |
| `platform:approve` | Duyệt / từ chối yêu cầu phê duyệt (`ENT-ApprovalRequest`) theo rule | Mới v2.0 (DEC-153) — §5.6 |
| `platform:admin` | Quản trị user & role, system setting | FR-AUTH-05 |

### 5.3. Ma trận permission × role

Ký hiệu: **●** toàn bộ · **◑** có phạm vi (ghi chú chữ: `d` = phòng ban của mình, `o` = của chính mình / được giao, `p` = trụ của mình, `r` = trong ngữ cảnh review được phân, `l` = liên kết với domain của mình, `t` = chỉ mục tiêu doanh thu, `k` = chỉ kill switch, `u` = chỉ tạo user/gán role) · **○** chỉ tổng hợp · **—** không có.

| Permission | CEO | CFO | VP_SALES | HR_MGR | REVIEWER | CPO | RISK_MGR | MANAGER | EMPLOYEE | ADMIN |
|---|---|---|---|---|---|---|---|---|---|---|
| `finance:read` | ● | ● | — | — | ◑r | — | — | ◑d | — | — |
| `finance:write` | — | ● | — | — | — | — | — | ◑d | — | — |
| `finance:query` | ● | ● | ○ | ○ | — | ○ | ○ | ◑d | — | — |
| `sales:read` | ● | — | ● | — | ◑r | — | — | ◑d | — | — |
| `sales:write` | ◑t | — | ● | — | — | — | — | ◑d | — | — |
| `sales:query` | ● | ○ | ● | — | — | ○ | ○ | ◑d | — | — |
| `hr:read` | ● | — | — | ● | ◑r | — | — | ◑d | ◑o | — |
| `hr:write` | — | — | — | ● | — | — | — | — | — | — |
| `hr:query` | ● | ○ | — | ● | — | — | ○ | ◑d | — | — |
| `hr:approve` | — | ● | — | — | — | — | — | — | — | — |
| `product:read` | ● | — | — | — | ◑r | ● | — | ◑d | — | — |
| `product:write` | — | — | — | — | — | ● | — | ◑d | — | — |
| `product:query` | ● | ○ | ● | — | — | ● | ○ | ◑d | — | — |
| `risk:read` | ● | ● | ◑l | ◑l | ◑r | ◑l | ● | ◑d | — | — |
| `risk:write` | — | — | — | — | — | — | ● | ◑d | — | — |
| `risk:query` | ● | ● | — | — | — | — | ● | — | — | — |
| `risk:approve` | ● | — | — | — | — | — | — | — | — | — |
| `execution:read` | ● | ◑d | ◑d | ◑d | — | ◑d | ◑d | ◑d | ◑o | — |
| `execution:write` | ● | ◑d | ◑d | ◑d | — | ◑d | ◑d | ◑d | ◑o | — |
| `execution:query` | ● | ◑d | ◑d | ● | — | ◑d | ◑d | ◑d | — | — |
| `idp:read` | ● | ◑p | ◑p | ◑p | ◑r | ◑p | ◑p | ◑d | ◑o | — |
| `idp:write` | ● | ◑p | ◑p | ◑p | ◑r | ◑p | ◑p | ◑d | ◑o | — |
| `idp:approve` | — | ◑p | — | ◑p | ● | — | — | ◑d | — | — |
| `idp:admin` | — | — | — | — | — | — | — | — | — | ● |
| `ai:query` | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● |
| `ai:write` | ● | ● | ● | ● | ◑r | ● | ● | ● | ● | — |
| `ai:admin` | ◑k | — | — | — | — | — | — | — | — | ● |
| `dashboard:read` | ● | ◑p | ◑p | ◑p | — | ◑p | ◑p | — | — | — |
| `dashboard:write` | ● | ◑p | ◑p | ◑p | — | ◑p | ◑p | — | — | — |
| `dashboard:admin` | — | — | — | — | — | — | — | — | — | ● |
| `platform:read` | ● | — | — | — | — | — | — | — | — | ● |
| `platform:approve` | ● | ◑p | ◑p | ◑p | — | ◑p | ◑p | ◑d | — | — |
| `platform:admin` | ◑u | — | — | — | — | — | — | — | — | ● |

Ghi chú ma trận:
- `ai:query` của ADMIN chỉ mở tool cấu hình/audit (ADMIN không có permission đọc dữ liệu nghiệp vụ nên tool filter §7 tự loại).
- `idp:approve` của MANAGER (`d`) chỉ với tài liệu của phòng ban mình và **không** gồm trường trọng yếu (số tiền, số tài khoản, MST, lương, giá trị hợp đồng) — trường trọng yếu phải do REVIEWER hoặc người có `◑p` của trụ tương ứng duyệt.
- `idp:approve` của CFO (`p`) = tài liệu trụ F (`FINANCIAL_REPORT`, `INVOICE`); của HR_MANAGER (`p`) = `EMPLOYEE_LIST` và field nhân sự của `KPI_OKR`.
- CEO và VP_SALES **không** duyệt extraction (giữ DEC-041, DEC-042 phương án A) — tách người quyết khỏi người nhập.
- Danh mục dùng chung (danh sách phòng ban, nhóm rủi ro, danh mục sản phẩm) được mọi user đã đăng nhập đọc dạng tham chiếu (id + tên), không cần permission domain.

### 5.4. Quyền theo trụ F.O.C.U.S

| Role | PIL-F | PIL-O | PIL-C | PIL-U | PIL-S |
|---|---|---|---|---|---|
| ROLE-01 CEO | Đầy đủ | Đầy đủ (lương chỉ tổng hợp ở dashboard) | Đầy đủ | Đầy đủ | Đầy đủ + chấp nhận rủi ro |
| ROLE-02 CFO | Đầy đủ | Chỉ tổng hợp (quỹ lương, chi phí nhân sự) | Chỉ tổng hợp | Chỉ tổng hợp | Đầy đủ + what-if |
| ROLE-03 VP_SALES | Chỉ METRIC-FIN-01 (doanh thu) | — | Đầy đủ | Chỉ tổng hợp (chỉ số sản phẩm) | Rủi ro liên kết deal/khách hàng |
| ROLE-04 HR_MANAGER | Chỉ doanh thu tổng (cho METRIC-HR-01) | Đầy đủ | — | — | Rủi ro liên kết nhân sự/tuyển dụng |
| ROLE-05 REVIEWER | — | — | — | — | — |
| ROLE-06 CPO | Chỉ doanh thu theo sản phẩm | — | Chỉ tổng hợp | Đầy đủ | Rủi ro liên kết sản phẩm |
| ROLE-07 RISK_MANAGER | Chỉ tổng hợp | Chỉ tổng hợp | Chỉ tổng hợp | Chỉ tổng hợp | Đầy đủ + what-if |
| ROLE-08 MANAGER | — (dashboard điều hành); xem số của đơn vị ở workspace | | | | |
| ROLE-09 EMPLOYEE | — | — | — | — | — |
| ROLE-10 ADMIN | — | — | — | — | — |

"Chỉ tổng hợp" = role thấy giá trị metric và trend của trụ (qua `<domain>:query`) nhưng **không** drill-down tới bản ghi chi tiết hay tài liệu gốc của trụ đó; lineage dừng ở "Nguồn thuộc phạm vi khác — không có quyền xem" (§6.1 quy tắc 4). Trụ "—" bị ẩn hẳn khỏi điều hướng (`06-UI-UX-SPEC.md`).

### 5.5. Ma trận tóm tắt 10 role × 12 domain nghiệp vụ

Tóm tắt §5.3 theo **domain nghiệp vụ** (BRD §4, §3.2) để đọc nhanh; khi lệch, §5.3 (permission string) là chuẩn. Ký hiệu: **F** = đầy đủ (read + write + query), **R** = đọc chi tiết, **Q** = chỉ tổng hợp, **A** = phê duyệt, **C** = cấu hình, hậu tố phạm vi `d`/`o`/`p`/`r` như §5.3, **—** = không.

| Role | Finance | Sales | HR | Product | Risk | Execution (Strategy · Initiative · KPI/OKR · Task) | Meeting & Decision | Data Capture (IDP) | AI Assistant | Dashboard & Report | Approval | Admin & Audit |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| CEO | R Q | R Q (ghi mục tiêu) | R Q (lương mức 4) | R Q | R Q A (chấp nhận) | F | F | R + gửi (không duyệt) | F + kill switch | F | A (bước 2 tài chính) | R audit, tạo user |
| CFO | F | Q | Q + A (tuyển dụng) | Q | R Q | F `d` | F `d` | Ap (trụ F) | F | F `p` | A (bước 1 tài chính) | — |
| VP_SALES | Q | F | — | Q | R `l` | F `d` | F `d` | gửi `p` | F | F `p` | A (sales) | — |
| HR_MANAGER | Q | — | F (lương mức 4) | — | R `l` | F `d`, Q toàn công ty | F `d` | Ap (nhân sự) | F | F `p` | A (nhân sự) | — |
| REVIEWER | R `r` | R `r` | R `r` | R `r` | R `r` | — | — | F `r` (duyệt) | F `r` | — | — | — |
| CPO | Q | Q | — | F | R `l` | F `d` | F `d` | gửi `p` | F | F `p` | A (product) | — |
| RISK_MANAGER | Q | Q | Q | Q | F | F `d` | F `d` | gửi `p` | F | F `p` | A (risk) | — |
| MANAGER | F `d` | F `d` | R Q `d` | F `d` | F `d` | F `d` | F `d` | Ad (trừ trường trọng yếu) | F | — (workspace đơn vị; báo cáo phòng ban) | A `d` | — |
| EMPLOYEE | — | — | R `o` | — | — | F `o` | F `o` | gửi `o` | F `o` | — | — | — |
| ADMIN | — | — | — | — | — | — | — | C (schema, ngưỡng) | C (autonomy, provider, kill switch) | C (ngưỡng) | C (rule, SLA) | F |

Domain "Approval" và "Report" (mới v2.0 — DEC-153) dùng permission ở §5.6.

### 5.6. Permission cho Approval và Report (DEC-149, DEC-153, DEC-155)

| Permission | Cho phép | Role | Ghi chú |
|---|---|---|---|
| `platform:approve` | Duyệt / từ chối `ENT-ApprovalRequest` khi role của mình nằm trong `approver_role_codes` (bước 1) hoặc `second_approver_role_codes` (bước 2) của rule | CEO, CFO, VP_SALES, HR_MANAGER, CPO, RISK_MANAGER, MANAGER (`d`) | Người duyệt ≠ người yêu cầu; bước 2 ≠ bước 1 (05 CK); từ chối bắt buộc lý do; **AI không có quyền này** (§7.3) |
| `platform:admin` | Cấu hình `ENT-ApprovalRule` (điều kiện, SLA, escalation) | ADMIN | Ngưỡng 2 người duyệt tài chính đọc từ env `APPROVAL_FINANCE_THRESHOLD_VND` (mặc định 500.000.000 đ), Admin override qua `ENT-AutonomyPolicy` (DEC-155) |
| `dashboard:read` | Tạo / tải báo cáo weekly/monthly PDF + Excel (`ENT-Report`) | Role có `dashboard:read`; MANAGER chỉ báo cáo phòng ban (`d`) | Nội dung lọc theo trụ trong scope (§6) lúc sinh; job định kỳ chạy bằng service account và chỉ sinh báo cáo cấp công ty cho CEO |

Permission `platform:approve` được thêm vào danh mục §5.2; endpoint EP-123..125 (Approval), EP-120..122 (Report) — `required_permission` ở 10 §3.12.

---

## 6. Data scoping

### 6.1. Nguyên tắc chung

1. **Enforce ở backend, hai lớp** (A-EMS §III.2): (a) middleware xác thực JWT RS256 và từ chối thiếu token; (b) mỗi route khai báo permission cần có qua dependency `require_permission("<domain>:<action>")`; (c) service lọc bản ghi theo scope (§6.2) **trước** khi trả về. Frontend ẩn UI chỉ là UX.
2. **Default deny**: permission không có trong JWT hoặc không có trong §5.2 → `403 FORBIDDEN`.
3. **Scope theo trụ**: mỗi metric, alert, tài liệu nguồn, extraction gắn với ≥ 1 trụ PIL-x. Role chỉ truy cập nếu có ít nhất một trụ trong §5.4; tài liệu đa trụ (`KPI_OKR`) chỉ trả field thuộc trụ trong scope.
4. **Lineage nhất quán với scope**: drill-down không dẫn ra ngoài scope. Bản ghi gốc ngoài scope hiển thị "Nguồn thuộc phạm vi khác — không có quyền xem" thay vì ẩn im lặng (giữ P01).
5. **Tổng hợp an toàn**: với `<domain>:query` không kèm `<domain>:read`, API chỉ trả giá trị tổng hợp; không trả danh sách cá nhân, bản ghi chi tiết hay link tài liệu.
6. **Response model tường minh**: field nhạy cảm không nằm trong response model của role không có quyền (không chỉ che ở frontend).
7. **Một nguồn sự thật cho scope**: hàm scope dùng chung cho REST, dashboard, export và **tool AI** — không có đường đọc dữ liệu nào bỏ qua scope.

### 6.2. Scope theo role

| Role | Phạm vi bản ghi | Ghi chú |
|---|---|---|
| ROLE-01 CEO | Toàn công ty | Lương cá nhân: xem được (mức 4 "rất nhạy cảm" §6.3) — chỉ CEO và HR_MANAGER |
| ROLE-02 CFO | Toàn công ty với `finance`, `risk`; tổng hợp với domain khác | Không xem lương cá nhân, chỉ quỹ lương/chi phí nhân sự |
| ROLE-03 VP_SALES | Toàn bộ `sales`; rủi ro liên kết deal/khách hàng | Không xem biên LN, cash, công nợ, ngân sách |
| ROLE-04 HR_MANAGER | Toàn bộ `hr`; toàn bộ `execution` ở mức workload | Doanh thu tổng chỉ dùng cho METRIC-HR-01 |
| ROLE-05 REVIEWER | Chỉ tài liệu/extraction **được phân** cho mình và các bản ghi đích của chúng (`r`) | Không có dashboard; field rất nhạy cảm chỉ xem trong phiên review, không tải file |
| ROLE-06 CPO | Toàn bộ `product`; doanh thu theo sản phẩm | |
| ROLE-07 RISK_MANAGER | Toàn bộ `risk`; tổng hợp các trụ khác | Đọc được `linked_entities` ở dạng tham chiếu (id + tên) |
| ROLE-08 MANAGER | Bản ghi có `department_id` = phòng ban của mình (`d`) | Ghi bản ghi mới luôn gán `department_id` của mình; sửa bản ghi đơn vị khác → 403 |
| ROLE-09 EMPLOYEE | Bản ghi `owner_id`/`assignee_id`/`uploaded_by` = chính mình (`o`) | Hồ sơ nhân sự của chính mình (không gồm lịch sử lương — xem qua HR) |
| ROLE-10 ADMIN | Không đọc bản ghi nghiệp vụ | Chỉ cấu hình, user/role, audit log |

### 6.3. Bốn mức nhạy cảm dữ liệu (A-EMS §VI.3, NĐ 13/2023) và 4 mức phân loại BRD

**Hai thang cùng tồn tại (DEC-149, 05 §10):** mức nhạy cảm 1–4 dưới đây gắn **field** (mask, field-level security); `data_classification` 4 mức BRD FR-ADM-05 gắn **bản ghi** và **quyết định model AI được xử lý**:

| `data_classification` | Tương ứng mức field | Model được phép |
|---|---|---|
| `PUBLIC` — Công khai | — | Mọi provider |
| `INTERNAL` — Nội bộ | 1 | Mọi provider được bật |
| `CONFIDENTIAL` — Mật | 2, 3 | **Không** gửi LLM cloud trừ provider ADMIN bật rõ; mặc định dùng model local hoặc template (03 §7) |
| `SECRET` — Tuyệt mật | 4 | **Không** gửi LLM; chỉ model local/template |


| Mức | Dữ liệu | Ai được xem chi tiết | Gửi tới LLM? | Hiển thị cho người khác |
|---|---|---|---|---|
| **Mức 4 — Rất nhạy cảm** | Lương, lịch sử lương, ngày sinh, địa chỉ, CCCD, số tài khoản cá nhân | ROLE-01 CEO, ROLE-04 HR_MANAGER; ROLE-05 REVIEWER chỉ trong phiên review được phân | **Không** (lọc trước khi gửi model) | `••••`; API không trả giá trị |
| **Mức 3 — Nhạy cảm** | Họ tên, email, số điện thoại nhân viên và người liên hệ khách hàng | Theo RBAC (§5.3) | **Không** — thay bằng mã giả danh (vd. `EMP-0042`) trước khi gửi model | Theo RBAC |
| **Mức 2 — Bí mật kinh doanh** | Số liệu tài chính, deal, dự báo, rủi ro, hợp đồng | Theo RBAC | Có — chỉ dữ liệu người hỏi được xem; provider phải được ADMIN bật cho dữ liệu mức 2 | Theo RBAC |
| **Mức 1 — Nội bộ** | Danh mục phòng ban, sản phẩm, nhóm rủi ro, metric tổng hợp | Mọi user đã đăng nhập (tham chiếu) | Có | — |
| (Bảo mật hệ thống) | Mật khẩu (chỉ hash), khóa JWT, API key | Không ai | **Không bao giờ** | Không log, không trả trong response |

Quy tắc bổ sung:
- Mức nhạy cảm gắn ở cấp **field** (schema entity, `ExtractionSchema`) và lan sang tài liệu: tài liệu có ≥ 1 field mức 4 là "tài liệu mức 4" (vd. `EMPLOYEE_LIST`). Cấu trúc ở `05-DATA-MODEL.md`.
- Tài liệu mức 4: chỉ ROLE-01, ROLE-04 mở/tải file gốc; ROLE-05 mở trong phiên review, không tải; mọi lượt mở và mọi lần bị từ chối đều ghi audit.
- Chuyển dữ liệu mức 2 ra provider LLM ngoài lãnh thổ phải được ADMIN bật theo provider (NĐ 13/2023 — kiểm soát chuyển dữ liệu ra nước ngoài); mặc định tắt với provider chưa đánh dấu.
- Dữ liệu demo là dữ liệu giả định của công ty ABC nhưng quy tắc vẫn áp dụng để mô phỏng đúng sản phẩm.

### 6.4. Audit log

Ghi `ENT-AuditLog` cho: mọi mutation (kể cả qua IDP và AI), đổi role/user, chuyển vai trò demo, mở tài liệu mức 4, bị từ chối quyền khi truy cập dữ liệu mức 4, xác nhận/hoàn tác hành động AI, thay đổi autonomy policy, bật/tắt kill switch. Tối thiểu: actor (user hoặc `ai` + user ủy quyền), role active, hành động, đối tượng, thời điểm, `request_id`. Hành động của AI ghi `actor_type = ai` kèm `on_behalf_of` (AI-EOS: AI là actor có identity).

---

## 7. AI dùng quyền người hỏi (P06)

### 7.1. Quy tắc

| # | Quy tắc |
|---|---|
| 1 | AI Core gọi tool **bằng chính JWT của người hỏi** (A-EMS §VII.2 #4); không có service account "siêu quyền" cho AI đọc dữ liệu nghiệp vụ |
| 2 | **Tool filter trước khi gửi model**: chỉ tool mà người hỏi có đủ permission mới được khai báo cho model trong lượt đó; model không biết tới tool ngoài quyền |
| 3 | Kết quả tool đi qua lớp scope (§6.1 #7) và **lọc mức 3–4** trước khi trả về model |
| 4 | Câu hỏi ngoài quyền → AI trả lời "Bạn không có quyền xem dữ liệu này", gợi ý người có quyền; không suy đoán số |
| 5 | Hành động ghi của AI (L2/L3) yêu cầu **cả** `ai:write` **và** `<domain>:write` của người dùng; mức autonomy tối đa theo `ENT-AutonomyPolicy` (tool × role × ngưỡng giá trị) — L4 bị khóa |
| 6 | Kill switch (`ai:admin`, CEO có `◑k`) chuyển mọi hành động L3 về L2 ngay lập tức — toàn hệ thống hoặc theo agent (DEC-149, §7.3) |
| 7 | Nội dung tài liệu/kết quả tool là **data, không phải lệnh** (chống prompt injection); tool ghi không được kích hoạt từ chỉ dẫn nằm trong tài liệu |

### 7.2. Tool filter theo permission

Danh mục tool cụ thể (`TOOL-<name>`) do `10-API-SPECIFICATION.md` sở hữu. Mỗi tool khai báo `required_permission` và `risk_level`; bảng dưới quy định nhóm tool theo permission.

| Nhóm tool | Permission bắt buộc | Role có (tối thiểu một phần) |
|---|---|---|
| Đọc dashboard/KPI tài chính, runway, what-if runway | `finance:query` | CEO, CFO, VP_SALES (○), HR_MGR (○), CPO (○), RISK_MGR (○), MANAGER (d) |
| Đọc chi tiết hóa đơn, chi phí, ngân sách | `finance:read` | CEO, CFO, MANAGER (d) |
| Pipeline, win rate, hiệu suất | `sales:query` | CEO, CFO (○), VP_SALES, CPO (○), RISK_MGR (○), MANAGER (d) |
| Nhân sự, tuyển dụng, turnover | `hr:query` | CEO, CFO (○), HR_MGR, RISK_MGR (○), MANAGER (d) |
| Chỉ số sản phẩm, roadmap | `product:query` | CEO, CFO (○), VP_SALES (○), CPO, RISK_MGR (○), MANAGER (d) |
| Sổ rủi ro, what-if rủi ro | `risk:query` | CEO, CFO, RISK_MGR |
| Task, OKR, workload, quyết định | `execution:read` / `execution:query` | Mọi role nghiệp vụ theo scope `d`/`o` |
| Tìm tài liệu, trích dẫn trang | `idp:read` | Theo scope `p`/`d`/`o`/`r` |
| Tạo task, giao việc, ghi nhận quyết định (L2/L3) | `ai:write` + `execution:write` | Theo §5.3 |
| Cấu hình, audit (không đọc dữ liệu nghiệp vụ) | `ai:admin` / `platform:read` | ADMIN |
| Tạo yêu cầu phê duyệt, báo cáo (L2) | `ai:write` + `dashboard:read` | Role có `dashboard:read` |
| Duyệt / từ chối (APPROVAL) | `platform:approve` — **không khai báo cho model** | Người dùng bấm xác nhận (§7.3) |

### 7.3. Danh tính AI Agent và nhóm tool (BRD §11.3, §3.2 — GAP D-04, A-16)

**Danh tính (v2.0 — DEC-150):** một profile `assistant` (`ENT-AIAgentProfile`) phục vụ mọi role; quyền thực tế = **quyền của người đang được phục vụ** (P06, §7.1 #1). Job định kỳ (briefing, insight, báo cáo) chạy bằng **1 service account** chỉ có quyền đọc tổng hợp + ghi `ai.insights`/`platform.reports`. Mọi lượt gọi tool ghi `agent_profile_code`, `why`, `autonomy_level`, `confidence`, `approval_request_id` (DEC-149). Kill switch theo agent tắt WRITE/EXECUTION của riêng agent đó; kill switch toàn hệ thống giữ như §7.1 #6.

**v2.1:** quyền agent ∩ quyền người, 6 agent chuyên trách + Orchestrator, service identity theo job (DEC-150).

| Nhóm | Ý nghĩa | Ai kích hoạt | Mức autonomy tối đa v2.0 | Tool (43 — 00 §4.8) |
|---|---|---|---|---|
| **QUERY** (lớp 10: READ, COMPUTE) | Không đổi dữ liệu nghiệp vụ | AI tự gọi trong lượt hỏi | L0 | `TOOL-get_finance_dashboard`, `TOOL-get_finance_forecast`, `TOOL-get_cash_flow_forecast`, `TOOL-list_expenses`, `TOOL-get_budget_status`, `TOOL-list_invoices`, `TOOL-get_runway_what_if`, `TOOL-get_sales_dashboard`, `TOOL-list_deals`, `TOOL-get_sales_pipeline`, `TOOL-get_hr_dashboard`, `TOOL-list_hiring_plans`, `TOOL-get_workload`, `TOOL-get_product_dashboard`, `TOOL-get_product_metrics`, `TOOL-get_risk_dashboard`, `TOOL-list_risks`, `TOOL-run_risk_scenario`, `TOOL-get_execution_dashboard`, `TOOL-list_tasks`, `TOOL-list_objectives`, `TOOL-get_kpi_status`, `TOOL-get_metric`, `TOOL-list_alerts`, `TOOL-get_lineage`, `TOOL-search_documents`, `TOOL-get_source_document` (27) |
| **WRITE** | Thay đổi dữ liệu nội bộ, hoàn tác được | AI đề xuất → action card (L2) hoặc tự làm (L3) theo `ENT-AutonomyPolicy` | L3; **tool tiền trần L2** (DEC-150) | `TOOL-create_task`, `TOOL-assign_task`, `TOOL-record_decision`, `TOOL-create_meeting`, `TOOL-record_kpi_measurement`, `TOOL-record_expense`, `TOOL-create_invoice`, `TOOL-upsert_deal`, `TOOL-upsert_risk`, `TOOL-create_mitigation`, `TOOL-submit_document`, `TOOL-generate_report`, `TOOL-request_approval` (13) |
| **APPROVAL** | Thực hiện quyền phê duyệt | **Chỉ người dùng** bấm Duyệt/Từ chối; tool chỉ là đường gọi từ UI chat | — (**AI không tự gọi APPROVAL**) | `TOOL-approve_request`, `TOOL-reject_request` (2) |
| **EXECUTION** | Tác động ra ngoài hệ thống (email, người nhận ngoài) | Luôn action card, người xác nhận | L2 | `TOOL-send_notification` khi kênh `email` (kênh in-app = WRITE) (1) |

Quy tắc cứng:
1. **AI không tự gọi tool APPROVAL** — tool lớp APPROVAL không được khai báo cho model trong lượt chat; chỉ server gọi khi có thao tác xác nhận của người dùng có `platform:approve`. AI chỉ được tạo yêu cầu qua `TOOL-request_approval`.
2. Hành động WRITE vượt rule `ENT-ApprovalRule` (VD chi > ngưỡng) → AI tạo `ENT-ApprovalRequest` thay vì thực thi; thực thi sau khi đủ người duyệt.
3. AI **không bao giờ** là người chịu trách nhiệm cuối (RACI "A" — 01 §5A).
4. Lớp QUERY/WRITE/APPROVAL/EXECUTION và metadata tool (`data_scope`, `classification`, `reversible`, `cost_estimate`) ghi ở 10 §7.3–§7.4 (DEC-149).

### 7.4. Ràng buộc AI về con người và dữ liệu (BRD §17.1 #11–12, FR-PERF-03/05 — GAP C-23, D-10)

| # | Ràng buộc | Hiện thực |
|---|---|---|
| 1 | AI **không chấm điểm nhân sự** — chỉ tổng hợp bằng chứng (task hoàn thành, KPI, check-in); mọi điểm số do con người quyết | Không có tool ghi điểm đánh giá; prompt hệ thống cấm; câu hỏi "chấm điểm nhân viên X" → từ chối lịch sự + trả bằng chứng có nguồn |
| 2 | AI **không quyết định tuyển dụng, sa thải, lương** | Không tool WRITE nào chạm `hr.salary_history`, trạng thái nhân viên, quyết định `ENT-HiringPlan`; duyệt tuyển dụng chỉ CFO (§8) |
| 3 | Kết quả đánh giá hiệu suất là **Mật** (`CONFIDENTIAL`): chỉ nhân viên, quản lý trực tiếp, HR và cấp được ủy quyền xem | Áp mức `data_classification` (§6.3) khi Performance Cycle có ở v2.1 |
| 4 | **Không huấn luyện / fine-tune model bằng dữ liệu khách hàng** khi chưa có đồng ý bằng văn bản | ModelGateway chỉ gọi inference; provider phải bật cờ không lưu/không train; fine-tune OUT (01 §3.2) |
| 5 | Dữ liệu `CONFIDENTIAL` trở lên không gửi LLM cloud chưa được duyệt; `SECRET` không gửi LLM | §6.3, 05 §10; dùng model local hoặc template (03) |
| 6 | AI phát hiện thiên lệch / rủi ro nhân lực chỉ ở dạng insight tổng hợp, không nêu tên cá nhân với role không có `hr:read` | Lọc mức 3 (mã giả danh) |

Kiểm thử: TC-AI-017 (từ chối chấm điểm / quyết định nhân sự), TC-AI-018 (tool APPROVAL không có trong danh sách tool gửi model) — 14 §2.1.1.


---

## 8. Phê duyệt kế hoạch tuyển dụng (FR-HR-03, FR-HR-07 ở 03)

| Bước | Actor | Permission | Trạng thái `ENT-HiringPlan` |
|---|---|---|---|
| 1. Tạo kế hoạch (phòng ban, vị trí, headcount, ngày mục tiêu, lương dự kiến) | HR_MANAGER | `hr:write` | `draft` |
| 2. Gửi duyệt | HR_MANAGER | `hr:write` | `draft → submitted` |
| 3. Duyệt hoặc từ chối (bắt buộc lý do) | CFO | `hr:approve` | `submitted → approved` / `submitted → rejected` |
| 4. Tuyển (cập nhật `filled`) | HR_MANAGER | `hr:write` | `approved → in_progress → completed` |

- Chỉ kế hoạch `approved` mới được đưa chi phí lương dự kiến vào `ENT-Forecast` (`EVT-finance.forecast_updated`).
- `rejected` có thể sửa và gửi lại (`rejected → draft`). CFO không sửa nội dung kế hoạch, chỉ duyệt.
- Kế hoạch `approved`/`in_progress` quá ngày mục tiêu > 30 ngày mà `filled < headcount` → `EVT-hr.hiring_plan_delayed` (ALERT-HR-04, BR-RSK-03 ở 03).
- Mọi chuyển trạng thái ghi audit; người duyệt ≠ người tạo.

---

## 9. Chuyển vai trò demo (`DEMO_MODE`)

### 9.1. Mô tả

- **Chỉ phục vụ demo**, không phải tính năng sản phẩm. Bật bằng cờ `DEMO_MODE=true` (backend) và `NEXT_PUBLIC_DEMO_MODE=true` (frontend); tên biến và vị trí cấu hình theo `07-TECH-ARCHITECTURE.md`.
- **Vị trí**: dropdown ở góc phải thanh trên, hiển thị role active (tên + ROLE-xx); màn đăng nhập (SCR-13) có quick-login cho 10 user demo.
- **Hành vi**: chọn role → backend cấp JWT RS256 mới cho **user seed của role đó** (giữ cơ chế DEC-073, thuật toán đổi theo DEC-129) → điều hướng về trang chủ của role (§1).
- Khi `DEMO_MODE=false`: dropdown và quick-login không render; route chuyển vai trò và danh sách user demo **không được đăng ký** (trả 404).

### 9.2. Quy tắc

| # | Quy tắc |
|---|---|
| R1 | Chuyển vai trò ≤ 2 giây (từ lúc chọn đến khi trang chủ role mới render số liệu chính) |
| R2 | Role mới xác lập ở backend (JWT mới mang `role` + `permissions[]` của role đích); không chỉ đổi state client |
| R3 | Sau khi chuyển: xóa toàn bộ cache dữ liệu client (TanStack Query) và đóng Panel AI / hội thoại đang mở của role cũ |
| R4 | Mỗi lần chuyển ghi audit `role.switch` (user gốc, role cũ → role mới, thời điểm) |
| R5 | Danh sách cố định 10 role ROLE-01..ROLE-10 tương ứng 10 user demo seed (`08-DEMO-DATA-SPEC.md`) |
| R6 | Chuyển thất bại → giữ role cũ, báo lỗi; không để UI ở trạng thái lẫn hai role |
| R7 | Thao tác đang dở (form review, action card chưa xác nhận) → hỏi xác nhận trước khi chuyển |
| R8 | Trang chủ đọc metric đã tính sẵn (metric store), không tính lại khi chuyển |

### 9.3. Mapping kịch bản demo 20 phút (01 §11) → role active

| Bước | Nội dung | Role active |
|---|---|---|
| 1–4 | Briefing, drill-down doanh thu, hỏi AI liên miền, Action card L2 tạo task | ROLE-01 CEO |
| 5 | Dashboard đổi theo vai; what-if rủi ro | ROLE-02 CFO → ROLE-07 RISK_MANAGER |
| 6 | Nạp doanh nghiệp UC-07 (thả 9 tài liệu) | ROLE-01 CEO (`idp:write`) |
| 7 | Review song song hóa đơn | ROLE-05 REVIEWER (CEO không có `idp:approve`) |
| 4 (phê duyệt) | Yêu cầu chi vượt `APPROVAL_FINANCE_THRESHOLD_VND`: duyệt bước 1 → bước 2 | ROLE-02 CFO → ROLE-01 CEO |
| 8 | Quay lại CEO, metric cập nhật, lineage, xuất báo cáo PDF/Excel | ROLE-01 CEO |

Không mở tài liệu mức 4 (`EMPLOYEE_LIST`) trên màn chiếu khi demo.

---

## 10. Ràng buộc phạm vi v2

- Đúng 10 role cố định; **không** có role tùy biến, không multi-tenant, không phân quyền theo chi nhánh. Scope phòng ban chỉ áp dụng cho MANAGER (`d`).
- **Không** self-register (DEC-137); không SSO; **MFA hoãn v2.1** (BRD FR-ADM-04 — DEC-153).
- "Xem như người dùng" (FR-ADM-08) hoãn v2.1 — v2.0 chỉ preview quyền/tool (OQ-05, DEC-156).
- AI agent: 1 profile `assistant`, quyền = người được phục vụ (DEC-150).
- Mỗi user một role chính; đa role/ủy quyền tạm thời là OQ-01.
- Quyền theo bản ghi riêng lẻ chỉ ở dạng `o` (chủ sở hữu/người được giao) và `r` (được phân review).

---

## 11. Open questions

| # | Câu hỏi | Đề xuất mặc định | Ảnh hưởng |
|---|---|---|---|
| OQ-01 | Có hỗ trợ một user nhiều role (vd. Manager kiêm Reviewer) hoặc ủy quyền tạm thời khi vắng mặt không? | v2: không; dùng role chính + chế độ demo. Phase sau: bảng `user_roles` + ủy quyền có thời hạn | 05 `ENT-User`, JWT `permissions[]` |
| OQ-02 | MANAGER có được duyệt trường trọng yếu tài chính của đơn vị mình (vd. hóa đơn ≤ 20 triệu) không? | Không; trường trọng yếu luôn do REVIEWER hoặc CFO duyệt | 04 review routing |
| OQ-03 | CEO có cần `idp:approve` để tự duyệt khi demo không? | Không (giữ tách người quyết/người nhập); demo chuyển sang REVIEWER | 04, kịch bản demo |
| OQ-04 | EMPLOYEE có được xem lịch sử lương của chính mình trong app không? | Không ở v2; xem qua HR | `hr:read` scope `o` |
| OQ-05 | ADMIN có công cụ "xem như người dùng" hiển thị dữ liệu thật không? | Chỉ preview **danh sách quyền và tool** của role, không hiển thị dữ liệu nghiệp vụ; FR-ADM-08 thật hoãn v2.1 → **DEC-156** (open, non-blocking) | US-ADM-102, SCR-26 |
| OQ-06 | Provider LLM nào được đánh dấu "trong nước / được phép nhận dữ liệu mức 2" mặc định? | Mặc định tắt cho mọi provider; ADMIN bật từng provider khi demo. `CONFIDENTIAL`+ không gửi cloud chưa duyệt (DEC-149) — chi tiết model local ở 07 Phase 3c | 07 ModelGateway, §6.3 |
| OQ-07 | Ngưỡng khóa đăng nhập (5 lần sai) và thời hạn access/refresh token cụ thể? | Access 15 phút, refresh 7 ngày, khóa 15 phút sau 5 lần sai | 07, 10 §auth |
| OQ-08 | ✅ **Duyệt (human 2026-10-20):** dùng `platform:approve`, không thêm domain. Câu hỏi gốc: permission `platform:approve` (§5.6) có cần domain riêng `approval` không? | Không — dùng domain `platform` sẵn có (module `platform` sở hữu `ENT-ApprovalRequest`); 10 chốt `required_permission` ở Phase 3d | 10 EP-120..129, 05 |

Các OQ này chưa có DEC; captain cấp số ở `13-DECISION-LOG.md` khi đồng bộ governance.

---

## 12. Liên kết

| Chủ đề | File |
|---|---|
| Tầm nhìn, nguyên tắc P01–P09, kịch bản demo | `01-PROJECT-OVERVIEW.md` |
| Trụ, metric, alert, BR, FR domain | `03-DASHBOARD-SPEC.md` |
| User story IDP `US-DC-xxx`, review, Action Registry | `04-IDP-FEATURE-SPEC.md` |
| `ENT-User`, `ENT-Role`, mức nhạy cảm field, `ENT-AuditLog`, `ENT-AutonomyPolicy` | `05-DATA-MODEL.md` |
| Trang chủ theo role, role switcher, mẫu L1/L2/L3 | `06-UI-UX-SPEC.md` |
| RS256, `DEMO_MODE`, ModelGateway | `07-TECH-ARCHITECTURE.md` |
| 10 user demo | `08-DEMO-DATA-SPEC.md` |
| Endpoint, `required_permission` của tool | `10-API-SPECIFICATION.md` |
| Quyết định | `13-DECISION-LOG.md` (DEC-128, DEC-129, DEC-132, DEC-134, DEC-137, DEC-146, DEC-149, DEC-150, DEC-153, DEC-155, DEC-156) |

---

## 13. Version

- **Version:** 2.1.0 (đề xuất — human promote ở 12)
- **Status:** draft (Phase 3b)
- **Last updated:** 2026-10-20
- **Applies to:** Aureon v2 (v2.0 demo-ready / v2.1 production-ready)
- **Maintainer:** @CyEyes
- **Change 2.1.0 (Phase 3b — DEC-144, DEC-146, DEC-149, DEC-150, DEC-153, DEC-155, DEC-156):** BRD làm Canonical Source; ánh xạ vai trò BRD §3.2 → 10 role (§1); đổi mã 47 user story theo 00 §4.13.1 + cột Phạm vi (§3.1–3.11); thêm 94 story BRD còn lại theo role (§3.13) → đủ 141 US; ma trận 10 role × 12 domain (§5.5); permission `platform:approve` + quyền Approval/Report (§5.6); 4 mức `data_classification` quyết định model (§6.3); danh tính AI agent + nhóm QUERY/WRITE/APPROVAL/EXECUTION, "AI không tự gọi APPROVAL" (§7.3); ràng buộc AI không chấm điểm / quyết định nhân sự / huấn luyện trên dữ liệu khách (§7.4); MFA và FR-ADM-08 hoãn v2.1 (§10); OQ-08.
- **Change 2.0.0:** Viết lại toàn bộ theo DEC-124, DEC-128 (10 role, permission string thay ma trận theo trụ v1). Bản 1.0.0 (5 role) lưu ở nhánh `v1`.
