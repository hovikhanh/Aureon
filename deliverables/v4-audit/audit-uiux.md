# Audit UI/UX Aureon: tóm tắt (toàn văn ở phần B)

**Giao nhận:** chưa có file `/tmp/claude-1000/-home-vika-Aureon/2b13532a-4cf7-4113-90e3-1f149a3f8ac1/scratchpad/audit-uiux.md`. Harness từ chối lệnh Write với lý do subagent phải trả kết quả dạng văn bản, và tôi không ghi vòng qua Bash. Vì vậy toàn văn nằm ngay trong tin này, vượt giới hạn 40 dòng; riêng phần A là bản tóm tắt ≤ 40 dòng. Nếu vẫn cần file, phiên chính lưu phần B vào đường dẫn trên.

**Kết luận: không redesign toàn bộ.** Nên dựng lại design system có mục tiêu, chuyển trang sang page template, và thiết kế mới 3 vùng: Home theo vai trò, khung mobile, bàn Reviewer.

**Kiểm chứng live (không phải fallback static):**
- Cả 10 tài khoản đăng nhập được. 487 lượt mở trang, 332 trang được phép, 69 pattern, 3 viewport; thêm pass EN 183 trang; 1.802 ảnh, xem trực tiếp 58.
- Chặn đúng 1 request non-GET: `POST .../review/open`.
- Không submit form, không chat AI, không chạm kill switch. Repo không đổi. 0 mật khẩu trong script, log, JSON.
- Tác dụng phụ: khoảng 28 lượt đăng nhập tạo dòng `auth.login` trong audit và đổi "đăng nhập gần nhất". Tôi không đăng xuất, nên các phiên còn lại đến khi hết hạn.
- Thiếu tài khoản: HR cấp nhân viên, Sales cấp nhân viên, khối S (rủi ro).

**P0:**
1. U-01: Reviewer không có đường vào hàng chờ review, UI không có link tới `/data/review` ngoài link quay lại từ chính trang chi tiết.
2. U-02: CFO thấy mã băm thay tên phòng ban (`FinanceLiteView.tsx:132`).
3. U-03: cùng một màn hình có runway 5,3 tháng và "Dòng tiền dương", burn 0 đ, trong khi trang trụ ghi burn 2,4 tỷ.
4. U-04: Home mâu thuẫn. Manager thấy "Quá tải 12%" cạnh "Không ai quá tải"; Employee thấy "0 KR" nhưng có KR ở check-in.
5. U-05: Home không theo vai trò. CPO chỉ thấy Doanh thu; "Cần anh quyết" chỉ là số đếm.
6. U-06: không có tab bar mobile; tràn ngang 36/332 trang-role ở 390 px, gồm `/work` và `/goals`.

**P1 nổi bật:**
- Form nhập hóa đơn hiện `seller_name`, `subtotal`.
- Dialog KPI mất tiêu đề, không cuộn trên mobile.
- Nav dẫn vào ngõ cụt lỗi quyền.
- 0/34 bảng sắp xếp được bằng cột.
- Enum thô `paid`, `active`.
- Lộ chữ nội bộ "03 §2 METRIC-FIN-01", "BRD §2.8 A".
- 6 trang chi tiết theo 4 kiểu.
- Phím tắt Reviewer chưa có.

**Scorecard (1–5):** Admin 3,2 · Sales 3,0 · CEO 2,8 · HR, Manager, Office 2,6 · CFO 2,4 · CPO 2,0 · Employee 1,8 · Reviewer 1,4. Vai trò dùng nhiều giờ nhất đang yếu nhất.

**Điểm mạnh nên giữ:** token màu gần như sạch, i18n 2.296 key khớp 100%, axe chỉ báo 1 rule, không `pageerror`, first content p50 217 ms, focus ring đạt trên Home CEO, bộ component AI ít trùng.

**Cảnh báo khi đọc:**
- `/work` 30 s là do đồng hồ WSL nhảy, không phải trang chậm.
- Banner lỗi ở màn review là do tôi chặn POST.
- Date `mm/dd/yyyy` có thể chỉ là hành vi của trình duyệt headless.
- Lỗi phía API của U-03, U-04 chưa truy tới nguyên nhân gốc.

---

# B. Báo cáo đầy đủ

Quy ước: `SHOTS` = `/tmp/claude-1000/-home-vika-Aureon/2b13532a-4cf7-4113-90e3-1f149a3f8ac1/scratchpad/uiux/shots`. Đường dẫn ảnh trong bảng đều viết tắt theo tiền tố này; đường dẫn đầy đủ của các ảnh chính được liệt kê ở mục 10. Đường dẫn code tính từ `/home/vika/Aureon/apps/web/src`, trừ khi ghi khác.

## 1. Lý do của kết luận

- **Nền móng tốt:** màu gần như sạch (2 class màu thô, 1 màu arbitrary), i18n khớp 100%, route và sidebar lọc đúng theo role, axe chỉ báo 1 rule trên 2 route, không lỗi JS runtime. 69 giá trị arbitrary còn lại chủ yếu là layout (`max-w-`, `min-w-`, `grid-cols-`), nhưng có 3 `text-[10px]` và 1 `text-[11px]` ngoài thang chữ.
- **Vấn đề ở tầng tổ chức:** 34 bảng viết tay trong 33 file, 13 tablist, 42 `<h1>`, 9 độ rộng trang, 6 trang chi tiết theo 4 kiểu. Đổi skin không sửa được; gom component thì sửa được hàng loạt.
- **Vấn đề nặng nhất không phải giao diện:** số liệu mâu thuẫn, ID thô, Reviewer không vào được hàng chờ. Redesign toàn bộ không giải quyết được, và cần API/spec cùng tham gia.

## 2. Phạm vi và sai số

**Script và dữ liệu thô** ở `/tmp/claude-1000/-home-vika-Aureon/2b13532a-4cf7-4113-90e3-1f149a3f8ac1/scratchpad/uiux/` (`crawl.mjs`, `crawl_en.mjs`, `pass2.mjs`, `pass3.mjs`, `agg.py`, `agg2.py`, `static1.py`, `static2.py`, thư mục `results/`).

**Chỉ đọc:**
- Mọi request ngoài GET/HEAD/OPTIONS bị chặn ở cấp context, trừ `/api/auth/*`; service worker bị tắt.
- 9 form được mở rồi đóng bằng Escape, không điền, không submit. Nút mở đã đọc code xác nhận chỉ đổi state cục bộ.
- Không loại trừ được việc một GET phía server có ghi dữ liệu: **UNVERIFIED**, tôi chỉ chứng minh được ở tầng trình duyệt.

**Sai số đã loại, không phải lỗi app:**

| Hiện tượng | Nguyên nhân |
|---|---|
| Banner "Đã có lỗi xảy ra" trên màn review của CFO | Tôi chặn POST `review/open` |
| `/work` 30,1 s, `/admin/ai/evaluation` 30,2 s, `METRIC-PRD-05` ttfb −28,8 s | Đồng hồ WSL nhảy; đã loại 3 mẫu |
| Ảnh `home__m`, `home__t` ở tab "Cá nhân" | Crawler bấm tab trước khi resize; dùng `LANDING__*` |
| Date `mm/dd/yyyy`, "Week 43, 2026" | Native theo locale headless, **UNVERIFIED** trên Chrome tiếng Việt thật; rủi ro thiết kế vẫn còn vì app không kiểm soát định dạng |
| Đường Actual dừng trước điểm cuối trên KPI chart | Có thể chụp giữa animation, **UNVERIFIED** |
| Cờ overflow khi mở dialog ở 390 px | Một phần kế thừa từ trang nền |
| Heuristic breadcrumb, input cạnh bảng, target size trong crawl đầu | Sai hoặc thổi phồng; đã thay bằng đọc code và `pass3` |

**Ánh xạ tài khoản:**

| Vai trò yêu cầu | Tài khoản | Role | Ghi chú |
|---|---|---|---|
| CEO | ceo | CEO | Có |
| CFO | cfo | DIR F | Có |
| Sales | sales | DIR C | Cấp giám đốc; **thiếu** nhân viên sales |
| HR Director | hr | DIR O | Có |
| HR nhân viên | — | — | **Thiếu** |
| Manager | manager, office | MGR | Có 2 |
| Employee | employee | EMP | Có 1, ít dữ liệu |
| Reviewer | reviewer | REV | Hàng chờ trống lúc audit |
| Admin | admin | ADM | Có |
| CPO | cpo | DIR U | Có |
| Khối S (rủi ro) | — | — | **Thiếu**, chưa kiểm được |

## 3. Issue theo mức độ

P0 = phá niềm tin số liệu hoặc chặn việc chính của vai trò · P1 = rộng, nên sửa trước thí điểm · P2 = thiếu nhất quán · P3 = dọn dẹp.

### P0

| ID | Vấn đề | Ảnh | Code | Hướng sửa |
|---|---|---|---|---|
| U-01 | Reviewer đáp vào `/data` là hộp "tài liệu bạn đã gửi"; sidebar không có Review; không có link tới `/data/review` ngoài link quay lại từ trang chi tiết; bấm Trang chủ lại về `/data` | `reviewer/data__d_fold.jpg` | `lib/permissions.ts` (`landingFor`, `NAV_ITEMS`), `features/capture/InboxView.tsx:46` | Đáp thẳng vào hàng chờ; Review thành mục nav |
| U-02 | Mã băm thay tên phòng ban; trang metric còn hiện nguyên UUID | `cfo/business_finance__d_fold.jpg` | `features/finance/FinanceLiteView.tsx:132`; cùng mẫu `slice(0, 8)` ở `crm/DealDetailView.tsx:36`, `crm/SalesInsights.tsx:85`, `records/RecordCrud.tsx:93`, `goals/KpiTabs.tsx:45` | Lấy tên từ API; lint cấm ID thô |
| U-03 | Runway "5,3 tháng" và "Dòng tiền dương", burn "0 đ", trong khi trang trụ ghi burn 2,4 tỷ. "Tỷ lệ dùng ngân sách —" dù bảng có số và trang trụ ghi 100,6% | `cfo/business_finance__d_fold.jpg`, `ceo/home_pillar_finance__d_fold.jpg` | `FinanceLiteView.tsx:64` (what-if tham số 0), `:82`, `:157` | Thống nhất nguồn và kỳ; chủ nghiệp vụ xác nhận số đúng |
| U-04 | Manager: "Quá tải 12,0%" cạnh "Không ai quá tải", "Dự án trễ 10,0%" cạnh "Không có dự án trễ". Employee: "0 KPI, 0 KR" nhưng check-in có KR. Tổng quan sales: "Tỷ lệ thắng —" dù có 10 thắng, 5 thua. Khả năng là trộn phạm vi công ty/đơn vị (**UNVERIFIED**) | `manager/home__d_fold.jpg`, `employee/home__d_fold.jpg`, `employee/goals_check-ins__d_fold.jpg`, `cpo/business_sales__d_fold.jpg` | `features/home/DepartmentView.tsx`, `EmployeeView.tsx:24` | Mọi thẻ ghi phạm vi + kỳ |
| U-05 | Mọi DIR chung bố cục: CPO chỉ thấy Doanh thu, HR Director thấy Doanh thu + Task, không có chỉ số khối mình. "Cần anh quyết" chỉ là thẻ đếm. Employee 3 thẻ chữ. Không có Panel AI | `cpo/LANDING__d.jpg`, `hr/LANDING__d.jpg`, `ceo/home__d_fold.jpg`, `employee/home__d_fold.jpg` | `features/home/ExecutiveView.tsx:36`, `EmployeeView.tsx:24` | Thiết kế mới, mục 8.6 |
| U-06 | Không có tab bar dưới, không có nút + nhập nhanh; nav là drawer đủ 9 mục. Tràn ngang 36/332 trang-role ở 390 px (9/69 pattern) | `ceo/work__m.jpg`, `ceo/goals__m.jpg`, `ceo/overlay_menu__m.jpg` | `components/shell/AppShell.tsx`, `Sidebar.tsx:43`, `features/work/MyTasksView.tsx:69`, `features/goals/GoalTreeView.tsx:80` | Shell mobile riêng, mục 8.2 |

### P1

| ID | Vấn đề | Ảnh | Code | Hướng sửa |
|---|---|---|---|---|
| U-07 | Form hóa đơn hiện khóa thô `seller_name`, `subtotal`, `vat_rate_pct`, `vat_amount` | `manager/form_invoice__d.jpg` | `features/capture/SchemaFormField.tsx` | Thêm nhãn; test cấm nhãn `snake_case` |
| U-08 | Dialog Tạo KPI cao 914 px trong viewport 844, mất tiêu đề, không cuộn; 1/9 form đo được | `ceo/form_goal_kpi__m.jpg` | `components/ui/dialog.tsx:16`, `features/goals/GoalEditors.tsx:89` | `max-h` trong primitive; mobile dùng sheet |
| U-09 | Nav vào ngõ cụt: Reviewer vào Tài chính gặp 3 khối lỗi quyền; Employee gặp lỗi Sales và thẻ quản lý nhân sự dẫn tới trang trống; `/home/alerts` lỗi quyền với 5 tài khoản. Trái §3.3 | `reviewer/business_finance__d_fold.jpg`, `employee/business__d_fold.jpg` | `lib/permissions.ts`, `components/shell/BusinessHub.tsx` | Rule route theo quyền API thật; test ma trận role × route |
| U-10 | 0/34 bảng sắp xếp được (`aria-sort` 0 lần); chỉ 4 file có tìm kiếm | `cfo/business_finance_invoices__d_fold.jpg` | Mục 5 | `DataTable` |
| U-11 | Enum thô `paid`, `active`, `terminated`; cột Chức danh toàn "—" | `cfo/business_finance_invoices__d_fold.jpg`, `hr/business_hr_employees__d_fold.jpg` | `finance/InvoicesView.tsx:69`, `hr/EmployeesView.tsx:60` | Map enum qua i18n |
| U-12 | Sai P04: `66.7%`, `166.7%`, `81.5%`, `0.3 d/wk`, `86.4`, `2026-Q4`, `2026-W40`, `2026-09-12`, `250000000`, "Dòng 0"; runway "5,3" mất đơn vị | `ceo/admin_acceptance__d_fold.jpg`, `ceo/work_workload__d_fold.jpg`, `cfo/data_review_[id]__d_fold.jpg` | `crm/SalesInsights.tsx:50-51`, `admin/acceptance/logic.ts:22-23`, `dashboard/MetricDetailContent.tsx:122`, `idp/RowGrid.tsx:22,36`, `home/MetricTile.tsx:44`, `execution/calendar.ts:21`, `capture/logic.ts:34` | Lint cấm format ngoài `lib/format.ts` |
| U-13 | Lộ chữ nội bộ: "03 §2 METRIC-FIN-01", "ENT-Revenue…", "BRD §2.8 A", "BRD §19.1", "02 §5.3", "R-DEC-174", "Finance Lite", "Nguồn: /ai/briefings", `missing permission execution:read` | `ceo/overlay_metric__d.jpg`, `cpo/business_sales__d_fold.jpg` | `dashboard/MetricDetailContent.tsx:67`, `admin/IntegrationsView.tsx:55`, `apps/web/messages/vi.json:37,813,814,2515,2840` | Ngôn ngữ nghiệp vụ; quy tắc copy |
| U-14 | Phễu hiện 166,7%, 200%, −66,7%, −100%. Đúng công thức theo ghi chú BRD §2.8 A, không phải bug code, nhưng người đọc không dùng được | `cpo/business_sales__d_fold.jpg` | `crm/crm.ts:39-40` | Quyết định nghiệp vụ |
| U-15 | 6 trang chi tiết theo 4 kiểu: KPI 5 tab, Dự án 3 tab, Objective/Deal/Client/Review không tab; 3 dạng lối quay lại; breadcrumb thật chỉ ở `AdminHeader` và trang Dự án | `sales/business_sales_deals_[id]__d_fold.jpg`, `sales/goals_kpis_[id]__d_fold.jpg`, `manager/work_projects_[id]__d_fold.jpg` | `crm/DealDetailView.tsx:40`, `goals/KpiDetailView.tsx:42`, `work/ProjectDetailView.tsx:49` | Template Detail |
| U-16 | Màn Review: 0 phím tắt trong `features/idp`, không trang `?`, không chế độ Gọn; lưới 9 cột cuộn ngang trong cột hẹp; nguồn dạng text, dấu bị tách trong font mono; tràn ở 768 và 390 px | `cfo/data_review_[id]__d_fold.jpg` | `features/idp/ReviewDetailView.tsx`, `RowGrid.tsx`, `SourceViewer.tsx` | Thiết kế mới, mục 8.7 |

### P2

| ID | Vấn đề | Ảnh | Code |
|---|---|---|---|
| U-17 | 9 giá trị `max-w`; `h1` cỡ 2xl/xl/lg; `/work` giấu H1; tab khi trên khi dưới tiêu đề; dải tab `/home/pillar` lệch 64 px | `ceo/home_pillar_finance__d_fold.jpg`, `ceo/meetings__d_fold.jpg` | `dashboard/PillarTabs.tsx`, `work/WorkShell.tsx:37` |
| U-18 | 13 tablist theo 3 kiểu, không có primitive `Tabs`; chỉ AI Control Center thấy xử lý bàn phím riêng | — | `admin/ai/AiControlCenter.tsx:47` |
| U-19 | Nhiều thang trạng thái cùng nghĩa ("Đúng kế hoạch/Có nguy cơ/Lệch nghiêm trọng", "Vượt/Đạt/Gần đạt/Dưới ngưỡng", "Nghiêm trọng/Cảnh báo", "Đúng tiến độ/Trễ"). "Chi phí tăng" mũi tên đỏ cạnh nhãn "Đúng kế hoạch" | `ceo/goals__d_fold.jpg`, `ceo/home_alerts__d_fold.jpg` | `components/StatusBadge.tsx`, `goals/common.tsx` |
| U-20 | Sai từ vựng AI: "AI phát hiện", "AI điền sẵn", "AI gợi ý loại…", "AI đã thực hiện thao tác bạn xác nhận". Briefing màu `ai` không có nhãn. Không có phản hồi thích/không thích | `ceo/home__d_fold.jpg`, `employee/goals_check-ins__d_fold.jpg` | `apps/web/messages/vi.json:292,1332,1797,2145`, `briefing/BriefingBanner.tsx:32` |
| U-21 | Token `ai` dùng cho hành động người hoặc nav: nút Gửi, nút Xác nhận, link tài liệu, mục Hỏi AI | `ceo/ask__d_fold.jpg` | `ai/ChatView.tsx:156`, `components/ai/ActionCard.tsx:84`, `execution/PredictedActionList.tsx:81`, `knowledge/DocumentsPanel.tsx:58`, `components/shell/Sidebar.tsx:72,75` |
| U-22 | ⌘K chỉ 3 mục cố định, không tìm bản ghi, không ngữ cảnh, header không gợi ý; tự viết dialog | `ceo/overlay_palette__d.jpg` | `components/shell/CommandPalette.tsx:53` |
| U-23 | Mobile: 107/110 phần tử trên màn hình cao dưới 44 px (7 màn của Manager); checkbox trạng thái dưới 24 px | `results/pass3.json` | `components/ui/button.tsx:18` |
| U-24 | Chữ trắng trên ô quá tải 3,5:1 (cần 4,5:1); cột "Thua" mờ. 13 trang-role, 89 node | `ceo/work_workload__d_fold.jpg` | `work/WorkloadView.tsx`, `sales/SalesPipelineView.tsx` |
| U-25 | Ngày có 2 kiểu (native và text `dd/mm/yyyy`); tuần dùng `type=week`; `select` native trên từng thẻ pipeline | `sales/business_sales_pipeline__d_fold.jpg`, `manager/form_invoice__d.jpg` | `components/ui/select.tsx`, `crm/StageMove.tsx` |
| U-26 | Form: 0/62 trường đo được có `required`/`aria-required`, 8 có dấu `*`; form KPI, Dự án, Người dùng, Phòng ban, Vị trí không đánh dấu bắt buộc; `aria-invalid` 15/66 file, `aria-describedby` 4 file | `ceo/form_goal_kpi__d.jpg`, `cfo/form_record__d.jpg` | `goals/GoalEditors.tsx`, `work/CreateProjectDialog.tsx`, `admin/org/OrgForms.tsx` |
| U-27 | 55 trạng thái trống tự viết; Reviewer thấy "Gửi tài liệu" hai lần trên hàng chờ trống | `reviewer/data_review__d_fold.jpg` | `idp/ReviewQueueView.tsx` |
| U-28 | Loading chữ trên Home, 45 skeleton với 14 tổ hợp class. Home gộp một query nên lỗi là cả trang lỗi, trái FR-DSH-07. Nhận định từ code | — | `home/ExecutiveView.tsx:21-22`, `home/EmployeeView.tsx:17-18` |
| U-29 | "Hôm nay" nhưng briefing tạo 04/11 khi đang 05/11; câu tóm tắt in hai lần | `ceo/LANDING__m.jpg` | `briefing/BriefingBanner.tsx:40`, `home/ExecutiveView.tsx:27` |
| U-30 | Key EN khớp 100% nhưng 83/183 trang còn tiếng Việt. Đa số là dữ liệu hợp lệ; lỗi thật là API trả câu tiếng Việt (trái CLAUDE §5.2): câu tóm tắt, "Lấy từ số liệu nguồn mới nhất…", đơn vị "ngày" | `results/ceo.en.jsonl` | `apps/api/src/app/modules/dashboard/services/reporting_service.py:85`, `apps/api/src/app/modules/execution/services/goal_tree.py:111` |
| U-31 | Pipeline lặp tên khách trên mỗi thẻ, mobile dài 5.800 px. Board có nút trạng thái trùng tên cột, cột cuối bị cắt không có dấu hiệu cuộn | `sales/business_sales_pipeline__m.jpg`, `ceo/work_view_board__d_fold.jpg` | `crm/PipelineBoard.tsx:69`, `work/BoardView.tsx:96` |
| U-32 | `/business`, `/admin` chỉ là thẻ link; Admin home thiếu tình trạng hệ thống; có "Kinh doanh › Kinh doanh" | `admin/admin__d_fold.jpg`, `employee/business__d_fold.jpg` | `components/shell/BusinessHub.tsx`, `app/(app)/admin/page.tsx` |
| U-33 | Thẻ check-in đã gửi vẫn hiện nguyên form; "Cao" và "Trung bình" cùng lúc | `employee/goals_check-ins__d_fold.jpg` | `goals/CheckInCard.tsx:99-105` |

### P3

| ID | Vấn đề | Ảnh | Code |
|---|---|---|---|
| U-34 | **Bug:** bước "Thắng" luôn bị tô như đã đạt, vì `closed_won` ngoài `OPEN_STAGES` nên `indexOf` trả −1 | `sales/business_sales_deals_[id]__d_fold.jpg` | `crm/DealDetailView.tsx:50` |
| U-35 | Title luôn "Aureon", không có skip link, `aria-label="primary"` chưa dịch | — | `app/layout.tsx:22`, `components/shell/Sidebar.tsx:56` |
| U-36 | Dark token có nhưng không có nút bật; JetBrains Mono không được nạp dù `font-mono` dùng 34 lần | — | `app/globals.css`, `app/layout.tsx` |
| U-37 | `text-amber-600` ×2, màu arbitrary trong badge, `ring-ring` không có token ×5, thiếu `neutral-0…900` | — | `home/MetricTile.tsx:47`, `dashboard/MetricDetailContent.tsx:59`, `components/ui/badge.tsx:10` |
| U-38 | Tool Registry 13 cột, cột tự chủ vỡ nhiều dòng, trang cao khoảng 6.300 px | `admin/admin_ai__tab3__d.jpg` | `admin/ai/ToolRegistryTab.tsx` |
| U-39 | Audit hiện mã role thay tên, đích `users · 44aae6b3` | `admin/admin_audit__d_fold.jpg` | `admin/AuditLogView.tsx:83` |
| U-40 | Nút Nói bị vô hiệu kèm 2 dòng giải thích; họp không có trang chi tiết | `ceo/meetings__d_fold.jpg` | `execution/VoiceCapture.tsx`, `MeetingsView.tsx` |
| U-41 | Mở trang review tự gửi POST; nên có chế độ xem không khóa | — | `idp/use-review.ts:28` |
| U-42 | Reviewer có link client/deal dẫn tới route 403; Manager gặp review 404 | `results/reviewer.jsonl` | `records/RecordCrud.tsx:282` |

**Chuyển review bảo mật (UNVERIFIED, tôi chưa đối chiếu `02` §5):** Reviewer đọc được hóa đơn, doanh thu, khách hàng toàn công ty; Manager thấy Tài chính cấp công ty.

## 4. Scorecard theo vai trò

Thang 1–5, là đánh giá chuyên môn, không phải kiểm thử người dùng. Office chỉ đo tự động, ảnh chưa xem.

| Role | Màn đầu | Việc kế tiếp | Mật độ | Điều hướng | IA nhất quán | TB | Nhận xét |
|---|---|---|---|---|---|---|---|
| Admin | 2 | 3 | 4 | 3 | 4 | 3,2 | Trang con tốt nhất app; home thiếu tình trạng hệ thống |
| Sales | 3 | 3 | 3 | 3 | 3 | 3,0 | Pipeline tốt; Home chỉ 1 thẻ |
| CEO | 3 | 2 | 3 | 3 | 3 | 2,8 | Có tóm tắt nhưng lặp; "Cần anh quyết" là số đếm |
| HR Director | 2 | 2 | 3 | 3 | 3 | 2,6 | Home không có chỉ số nhân sự; `/admin/org` tốt |
| Manager | 2 | 2 | 3 | 3 | 3 | 2,6 | Thẻ mâu thuẫn; Workload tốt nhưng không nổi trên Home |
| Office | 2 | 2 | 3 | 3 | 3 | 2,6 | Như Manager |
| CFO | 2 | 2 | 3 | 3 | 2 | 2,4 | ID thô, số mâu thuẫn |
| CPO | 1 | 2 | 3 | 2 | 2 | 2,0 | Không có chỉ số sản phẩm trên Home |
| Employee | 1 | 2 | 2 | 2 | 2 | 1,8 | Không task cụ thể, nhiều ngõ cụt |
| Reviewer | 1 | 1 | 2 | 1 | 2 | 1,4 | Không có đường vào hàng chờ |

## 5. Audit từng bảng

Sắp xếp: **không bảng nào**. `aria-sort` 0 lần, nút trong `thead` 0 trên 23 bảng đo live; thứ tự là `sort_by` cố định trong code.

| Bảng | File | Tìm | Lọc | Trang | Ghi chú |
|---|---|---|---|---|---|
| Hóa đơn | `finance/InvoicesView.tsx` | Không | Tab chiều | Có | Enum thô |
| Nhân viên | `hr/EmployeesView.tsx` | Có | Không | Có | Enum thô |
| Records | `records/RecordCrud.tsx` | Một phần | Theo spec | Có | Tràn mobile; Sửa/Lưu trữ lặp từng dòng |
| Hộp thư | `capture/InboxView.tsx` | Có | Có | Có | Tốt |
| Hàng chờ review | `idp/ReviewQueueView.tsx` | Không | Có | Có | Spec cần xử lý hàng loạt |
| Dự án | `work/ProjectsView.tsx` | Không | Có | Không | Trình bày tốt nhất |
| Workload | `work/WorkloadView.tsx` | Không | Có | Không | |
| Người dùng | `admin/UsersView.tsx` | Có | Có | Có | Tràn tablet, mobile |
| Vị trí | `admin/PositionsView.tsx` | Có | Có | Không | |
| Audit | `admin/AuditLogView.tsx` | Theo hành động | Có | Có | |
| Vai trò | `admin/RolesView.tsx` | Không | Không | Không | Ma trận chỉ đọc, hợp lý |
| Agent, Autonomy | `admin/ai/AgentsTab.tsx`, `AutonomyTab.tsx` | Không | Không | Không | |
| Tool Registry | `admin/ai/ToolRegistryTab.tsx` | Không | Có | Không | Có ẩn/hiện cột |
| Tool/Model calls | `admin/ai/logs/ToolCallsTab.tsx`, `ModelCallsTab.tsx` | Không | Có | Có | |
| Chi phí | `admin/ai/logs/CostTab.tsx` | Không | Có | Không | |
| Ngân sách | `finance/FinanceLiteView.tsx` | Không | Không | Không | ID thô |
| Phễu, xếp hạng | `crm/SalesInsights.tsx` | Không | Kỳ | Không | |
| Cấu hình nhập liệu | `capture/admin/TypesTab.tsx`, `SchemasTab.tsx`, `RulesTab.tsx`, `IncidentsTab.tsx` | Không | Có | Không | |
| Import, Mapper, lưới | `capture/ImportRowsTable.tsx`, `ColumnMapper.tsx`, `idp/RowGrid.tsx` | Không | Một phần | Một phần | Import chưa thấy live |
| Bảng phụ | `goals/KpiDetailView.tsx`, `goals/KpiTabs.tsx`, `work/ApprovalDetail.tsx`, `capture/ActionsHistory.tsx`, `admin/onboarding/UsersStep.tsx`, `capture/SchemaForm.tsx`, `capture/admin/SchemaEditor.tsx` | Không | Không | Không | Chấp nhận được |

## 6. Inventory component

Quy mô: 13.618 dòng `.tsx` trong `features` + `components`, không tính test.

| Nhóm | Hiện có | Trùng lặp | Hành động |
|---|---|---|---|
| Primitive | 13: badge, button, card, checkbox, collapsible, dialog, dropdown-menu, input, label, popover, select native, toast, tooltip | — | Giữ |
| Thiếu primitive | Tabs, Table, Skeleton, Sheet, Breadcrumb, Pagination, Progress, Combobox, DatePicker, Avatar, EmptyState, StatCard, PageHeader | Tự viết rải rác | Bổ sung |
| Bảng | 34 `<table>` trong 33 file | ≥ 6 kiểu `thead` | `DataTable` |
| Tab | 13 tablist + 4 tab link (`WorkTabs`, `GoalsShell`, `MeetingsTabs`, `PillarTabs`) | 3 kiểu | `Tabs` |
| Header | 42 `<h1>` | Chỉ `AdminHeader` dùng lại | `PageHeader` |
| Phân trang | 5 inline + `Pager` (`admin/ai/logs/parts.tsx:27`) | Trùng logic | `Pagination` |
| Thẻ chỉ số | `MetricTile`, `PillarCard`, thẻ Finance, Sales, Dự án, Client, giai đoạn | ≥ 7 biến thể | `StatCard` |
| Tiến độ | `goals/common.tsx:53`, `CheckInCard.tsx:105`, `ProjectsView.tsx:26`, `OverviewTab.tsx:108` | 4 bản | `Progress` |
| Trạng thái | `StatusBadge`, `BandChip`, `ConfidenceBadge`, Badge inline | Nhiều thang | Một bảng ngữ nghĩa |
| Trống | 55 chỗ inline | Không có component | `EmptyState` |
| Skeleton | 45 `div`, 14 tổ hợp | | `Skeleton` |
| Lỗi | `QueryError`, `LoadError`, `<p>` trên Home | 3 cách | Giữ `QueryError` |
| Drawer | `work/TaskDetail.tsx:33`, `SourceDrawer`, `LineageChip`, `ToolCallsTab`, `ImportWizard` | Mỗi nơi một kiểu | `Sheet` |
| Dialog | 28 file, `ConfirmDialog` dùng chung | `RecordCrud` có dialog riêng | Sửa cuộn trong primitive |
| Field | `admin/common.tsx:86`, `SchemaFormField`, `FieldInput`, 33 `<label>` + 49 `<Label>` | 4 cách | `FormField` |
| Kanban | `BoardView`, `PipelineBoard` | 2 bản | `Board` |
| Biểu đồ | `Sparkline`, `KpiChart`, `CostTab`, `MetricDetailContent` | Không theme chung | `ChartFrame` |
| AI | `ActionCard`, `InsightCard`, `SourceChip`, `LineageChip`, `ThinkingState`, `UndoToast` | Ít trùng, tốt | Giữ; thiếu `AiPanel`, `SuggestionChip`, `FreshnessLabel`, `FeedbackButtons` |

## 7. Số đo và đối chiếu spec

**Điểm tốt nên giữ:**
- `globals.css` có token ngữ nghĩa, tách `primary`/`ai`, `tabular-nums`, `prefers-reduced-motion`.
- Trang làm chuẩn: `/work/projects`, `/work/workload`, `/home/alerts`, `/admin/org`, `/data`, `/admin/users`.
- `StatusBadge` kèm ký hiệu ● ◐ ○, màu không đứng một mình.
- Bàn phím: 22/22 lần Tab trên Home CEO có outline rõ, phần tử đều có tên.

| Chỉ số | Kết quả |
|---|---|
| First content | p50 217 ms, p95 499 ms, n = 329, localhost không throttle |
| FCP | p50 180 ms |
| Tràn 1440 / 768 / 390 | 0 / 8 / 36 trên 332 |
| Pattern tràn ở 390 | `/admin/users`, 3 trang `/business/*/records`, `/business/sales/records?tab`, `/data/review/[id]`, `/goals`, `/work`, `/work?view=board` |
| HTTP ≥ 400 | 403 theo vai trò + 1 lỗi 404 |
| axe | 1 rule `color-contrast`, trên `/work/workload`, `/business/sales` |
| Cỡ chữ thực | 14 và 12 px đa số; có 10 và 11 px ngoài thang |
| Chiều cao nút | 32 px đa số; có cả 20, 24, 28, 34, 38, 40 |

| Yêu cầu spec | Trạng thái |
|---|---|
| IA 8 mục + Quản trị | Đạt |
| Trang đích theo vai trò | Một phần |
| ⌘K hiểu ngữ cảnh | Một phần |
| Panel AI ngữ cảnh | **Chưa có** |
| Hai mật độ Thoáng/Gọn | **Chưa có** |
| Breadcrumb nghiệp vụ | Chỉ Quản trị + Dự án |
| Bố cục chi tiết thống nhất | Chưa đạt |
| Vùng thả file toàn cục | Chưa có |
| Tab bar mobile + nút + | **Chưa có** |
| Phím tắt Reviewer, trang `?` | **Chưa có** |
| Biểu đồ có bảng thay thế | Không thấy trong code đã xem |
| Tiêu đề biểu đồ là kết luận | Chưa |
| Phản hồi một chạm | **Chưa có** |
| Đổi vai trò ở thanh trên | Chưa có |
| Nhãn độ tươi | Một phần: chỉ hiện khi stale |

## 8. Hướng đề xuất v4

Mọi mục là đề xuất. Chạm API, schema, dependency hoặc spec phải qua DEC theo CLAUDE §6.3.

### 8.1. Token

| Nhóm | Đề xuất |
|---|---|
| Màu | Giữ ngữ nghĩa; thêm `neutral-0…900`, `chart-1…6`, `focus`; chốt `primary` (OQ-06-01) |
| Chữ | 12/14/16/20/24/32, cấm 10–11 px; nạp JetBrains Mono và kiểm dấu tiếng Việt, hoặc bỏ khỏi spec |
| Mật độ | `data-density` trên shell: dòng bảng 44/32, ô nhập 40/32, thân 16/14. Reviewer, Finance, Admin mặc định Gọn |
| Bo góc | 4/8/16/full như spec; nút trong bảng Gọn dùng 8 |
| Layout | 3 độ rộng: `form` 720, `content` 1200, `wide` tới 1600 |
| Trạng thái | `on_track`, `at_risk`, `critical`, `exceeded`, `no_data`, `stale`; nhãn domain qua i18n |

### 8.2. Layout shell

- ≥ 1440: sidebar + nội dung + `AiPanel` cố định phải.
- 1280–1439: `AiPanel` trượt ra.
- 768–1279: sidebar icon, panel phủ.
- < 768: tab bar 4 mục + nút **+** (chụp chứng từ, cập nhật task, check-in, ghi âm); màn cấu hình chỉ đọc.
- Top bar: ô ⌘K luôn hiển thị, breadcrumb nghiệp vụ, đổi ngữ cảnh vai trò, chuông, tài khoản.
- ⌘K có 3 nhóm: Hỏi AI, Tìm bản ghi, Đi tới, kèm gợi ý theo màn hình.

### 8.3. Điều hướng theo vai trò

| Role | Đáp vào | Sidebar | Tab mobile |
|---|---|---|---|
| CEO | Trang chủ điều hành | Trang chủ · Hỏi AI · Mục tiêu · Công việc · Họp · Dữ liệu · Kinh doanh · Báo cáo · Quản trị | Trang chủ, Duyệt, Hỏi AI, Mục tiêu |
| DIR | Trang chủ theo khối | Trang chủ · Hỏi AI · **Khối của tôi** · Mục tiêu · Công việc · Họp · Dữ liệu · Báo cáo | Trang chủ, Duyệt, Hỏi AI, Công việc |
| Manager | Trang chủ team | Trang chủ · Hỏi AI · Công việc · Mục tiêu · Họp · Dữ liệu · Báo cáo | Trang chủ, Duyệt, Công việc, Hỏi AI |
| Employee | Hôm nay | Hôm nay · Việc của tôi · Mục tiêu · Họp · Gửi dữ liệu · Hỏi AI · Tri thức | Hôm nay, Việc, Check-in, Hỏi AI |
| Reviewer | Hàng chờ | **Hàng chờ** · Đã xử lý · Hỏi AI · Tri thức | Chỉ xem hàng chờ |
| Admin | Sức khỏe hệ thống | Tổng quan · Tổ chức · Người dùng & quyền · Dữ liệu vào · AI Control Center · Audit | Chỉ đọc |

### 8.4. Page template và chuẩn bảng

| Template | Áp dụng | Khung |
|---|---|---|
| WorkspaceHome | `/home` | Tóm tắt → Cần bạn → Chỉ số → AI đề xuất |
| List | Hóa đơn, Nhân viên, Dự án, Records, Audit | PageHeader + FilterBar + DataTable + Pagination |
| Detail | KPI, Objective, Project, Deal, Client | Breadcrumb, tiêu đề + trạng thái, StatCard, 5 tab §3.3, `AiPanel` |
| Form | SCR-61, form dài | Trang riêng, footer dính; dialog chỉ cho form dưới 6 trường |
| Split Review | SCR-18b, Phê duyệt | Nguồn trái, trường phải, thanh hành động dính |
| Board | Task, Pipeline | Cột có tổng, thay thế bằng bàn phím; mobile là tab giai đoạn |
| Analytics | Pillar, Finance, Sales | Lọc kỳ, tiêu đề kết luận, biểu đồ + bảng thay thế |
| Settings | Quản trị | Gốc từ `AdminHeader`, master-detail |

**DataTable:**
- Cột khai báo kiểu `text/money/pct/date/period/status/ref`, render tự động qua `lib/format.ts`; nhờ đó loại U-11, U-12.
- Bắt buộc: `aria-sort`, `scope`, header dính, 3 trạng thái, phân trang `limit/offset`, trạng thái trong URL.
- Hành động dòng: tối đa 1 nút chính, còn lại vào menu `⋯`.
- Mobile chuyển thành thẻ theo cột ưu tiên, không cuộn ngang toàn trang.

### 8.5. Chuẩn form

- Chỉ dùng `FormField` có label, hint, error, `aria-describedby`, `aria-invalid`, `aria-required`.
- Một cách đánh dấu bắt buộc duy nhất.
- `MoneyField`, `DateField`, `PeriodField`, `EntityCombobox`.
- Lỗi 422 map về từng trường; focus nhảy tới lỗi đầu tiên.
- Dialog có `max-h` + vùng cuộn; mobile là sheet toàn màn hình, nút dính đáy.

### 8.6. Dashboard theo vai trò

Mỗi widget một query, ghi rõ phạm vi, kỳ, giờ cập nhật; mọi số mở được nguồn.

| Role | Thứ tự ưu tiên | Chỉ số mặc định |
|---|---|---|
| CEO | Tóm tắt → Cần anh quyết có nút tại chỗ → Rủi ro → Chỉ số → AI đã làm | Doanh thu, dòng tiền, OKR, task trễ |
| CFO | Cảnh báo → Duyệt chi → Dòng tiền → Ngân sách theo phòng | Doanh thu vs KH, runway, chênh lệch ngân sách, DSO |
| DIR Sales | Deal rủi ro → Pipeline → Dự báo quý → Xếp hạng | Pipeline trọng số, tỷ lệ thắng, doanh số vs chỉ tiêu |
| HR Director | Tuyển dụng trễ → Quá tải → Nghỉ việc → Định biên | Turnover, quá tải, kế hoạch tuyển dụng |
| CPO | Sự cố → Roadmap trễ → Phát hành | Roadmap đúng tiến độ, sự cố, tỷ lệ đơn ABC Order |
| Manager | Quá tải có gợi ý chuyển việc → Hàng chờ duyệt → Team hôm nay → OKR rủi ro | Heatmap thu nhỏ, task quá hạn |
| Employee | Task hôm nay, đổi trạng thái tại chỗ → Check-in đến hạn → Lịch → Mục tiêu | Không dùng thẻ KPI lớn |
| Reviewer | Chính là hàng chờ: SLA, số chờ, tiếp tục xử lý | Chờ, quá SLA, đã xử lý hôm nay |
| Admin | Sức khỏe hệ thống → Sự cố AI → Sự cố nhập liệu → Chi phí AI | Uptime, DLQ, ngân sách AI |

### 8.7. Bàn làm việc Reviewer

- Hàng chờ Gọn, chọn nhiều, sắp theo SLA; xong tài liệu tự mở tài liệu kế.
- Nguồn PDF thật có vùng tô, liên kết hai chiều trường ↔ vùng gốc.
- Phím đề xuất: `J/K` đi trường, `Enter` xác nhận, `E` sửa, `R` từ chối, `?` tra phím. Cần kiểm xung đột với screen reader.
- Trường trọng yếu và độ tin cậy thấp lên đầu; AI nêu lý do không chắc.
- Đo theo mục tiêu hóa đơn 6 trường ≤ 60 giây.

### 8.8. Lộ trình gợi ý

Ước lượng thô, cần team xác nhận.

| Giai đoạn | Nội dung | Ước lượng |
|---|---|---|
| 0. Vá nóng | U-01, 02, 07, 08, 11, 12, 13, 34 và làm rõ số U-03, 04 | 1–2 tuần |
| 1. Nền DS | Token, density, PageShell, PageHeader, Tabs, Skeleton, EmptyState, FormField, StatusBadge, StatCard, DataTable, Sheet, lint chống tái phát | 3–4 tuần |
| 2. Shell | Mobile, ⌘K, top bar, khung AiPanel, nav theo vai trò | 2–3 tuần |
| 3. Thiết kế mới | Home theo vai trò, bàn Reviewer | 4–6 tuần |
| 4. Di chuyển | List → Detail → Form → Board → Analytics | 4–6 tuần |
| 5. Hoàn thiện | Nhãn AI, EN, dark, a11y thủ công, SUS | 2 tuần |

### 8.9. Quyết định cần human

1. Màu `primary` (OQ-06-01).
2. Review là mục nav riêng hay tab trong Dữ liệu; khuyến nghị mục riêng.
3. "Khối của tôi" thay hub `/business` cho DIR; đổi `06` §3.1.
4. Dependency, mỗi mục một DEC: `@radix-ui/react-tabs`, `@tanstack/react-table` hoặc tự viết, date picker, `cmdk`. Mặc định không thêm.
5. Phương pháp phễu (U-14) và nguồn runway (U-03).
6. API trả mã/kỳ/phạm vi thay câu tiếng Việt (U-04, U-13, U-30); đổi contract `10`.
7. Thêm tài khoản demo khối S, nhân viên HR, nhân viên Sales.
8. Mục Hỏi AI có được dùng màu `ai` không (U-21).

## 9. Chưa kiểm chứng (UNVERIFIED)

| Hạng mục | Lý do |
|---|---|
| Lỗi validate khi submit | Cấm submit; chỉ đọc code |
| Toast, Undo, action card thật, AI streaming | Cấm gửi; không có dữ liệu chờ |
| `KillSwitchBanner` khi bật | Cấm bật |
| Loading skeleton thực tế | Tải quá nhanh trên localhost |
| Màn review đầy đủ | POST bị chặn; hàng chờ Reviewer trống; chỉ thấy dưới CFO |
| Import wizard, onboarding từng bước, camera, kéo thả | Cần tương tác ghi; onboarding đã xong |
| Chế độ tối | Không có nút bật |
| Screen reader, Safari, iOS, thiết bị thật | Chỉ Chromium headless |
| Bàn phím toàn app | Chỉ đo Home CEO |
| Usability test, SUS, thời gian F1–F5 | Đây là audit chuyên gia |
| Tab Agent/Autonomy, Logs, Evaluation, Lịch, Tích hợp, ảnh Office | Chỉ có số đo tự động, chưa xem bằng mắt; 58/1.802 ảnh đã xem |
| Nguyên nhân gốc U-03, U-04 | Thấy ở UI, chưa truy API |

## 10. Đường dẫn đầy đủ của ảnh chính

- /tmp/claude-1000/-home-vika-Aureon/2b13532a-4cf7-4113-90e3-1f149a3f8ac1/scratchpad/uiux/shots/reviewer/data__d_fold.jpg
- /tmp/claude-1000/-home-vika-Aureon/2b13532a-4cf7-4113-90e3-1f149a3f8ac1/scratchpad/uiux/shots/cfo/business_finance__d_fold.jpg
- /tmp/claude-1000/-home-vika-Aureon/2b13532a-4cf7-4113-90e3-1f149a3f8ac1/scratchpad/uiux/shots/manager/home__d_fold.jpg
- /tmp/claude-1000/-home-vika-Aureon/2b13532a-4cf7-4113-90e3-1f149a3f8ac1/scratchpad/uiux/shots/cpo/LANDING__d.jpg
- /tmp/claude-1000/-home-vika-Aureon/2b13532a-4cf7-4113-90e3-1f149a3f8ac1/scratchpad/uiux/shots/ceo/work__m.jpg
- /tmp/claude-1000/-home-vika-Aureon/2b13532a-4cf7-4113-90e3-1f149a3f8ac1/scratchpad/uiux/shots/manager/form_invoice__d.jpg
- /tmp/claude-1000/-home-vika-Aureon/2b13532a-4cf7-4113-90e3-1f149a3f8ac1/scratchpad/uiux/shots/ceo/form_goal_kpi__m.jpg
- /tmp/claude-1000/-home-vika-Aureon/2b13532a-4cf7-4113-90e3-1f149a3f8ac1/scratchpad/uiux/shots/ceo/overlay_metric__d.jpg
- /tmp/claude-1000/-home-vika-Aureon/2b13532a-4cf7-4113-90e3-1f149a3f8ac1/scratchpad/uiux/shots/cpo/business_sales__d_fold.jpg
- /tmp/claude-1000/-home-vika-Aureon/2b13532a-4cf7-4113-90e3-1f149a3f8ac1/scratchpad/uiux/results/pass3.json
