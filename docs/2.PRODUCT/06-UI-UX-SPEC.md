# 06 — UI/UX Spec (v2)

> Đặc tả trải nghiệm, kiến trúc thông tin, 31 màn hình `SCR-01..31` (28 v2.0 gốc + SCR-29..31 mới — 00 §4), bộ component AI, luồng F1–F5 và design system v2 của **Aureon v2**.
> Nguồn: `01-PROJECT-OVERVIEW.md` §2, §5, §6, §11; `02-PERSONAS-PERMISSIONS.md`; `03-DASHBOARD-SPEC.md`; `04-IDP-FEATURE-SPEC.md`; đề xuất UI/UX AI-EOS (hợp nhất theo DEC-124); DEC-127, DEC-128, DEC-132, DEC-133, DEC-134, DEC-135.
> **Canonical Source (DEC-144):** `_reference/SOURCE-BRD-v1.1.md` (màn hình phê duyệt, báo cáo, dòng tiền; TTFT; WCAG). Bổ sung 2.1.0 theo DEC-148 (dòng tiền 13 tuần), DEC-151 (review IDP), DEC-152 (TTFT), DEC-153 (Approval, Report, transcript mock), DEC-155 (ngưỡng 2 người duyệt).
> ID màn hình, role, metric theo registry `00-INDEX.md` §4. Stack UI: Next.js App Router + Tailwind + shadcn/ui (Radix) + Recharts + next-intl (07).

---

## 1. Nguyên tắc UX

### 1.1. Tám nguyên tắc giao diện (U1–U8)

Mọi màn hình được duyệt theo 8 nguyên tắc; vi phạm phải nêu lý do trong PR.

| # | Nguyên tắc | Ý nghĩa trên giao diện | Kiểm tra nhanh |
|---|---|---|---|
| U1 | **Ngoại lệ trước, chi tiết sau** | Màn hình đầu chỉ hiện điều lệch kế hoạch, việc cần quyết, rủi ro mới; mọi thứ "bình thường" gộp thành một dòng | CEO trả lời "có gì cần tôi?" trong 10 giây |
| U2 | **Hỏi ở bất kỳ đâu** | Thanh AI ⌘K luôn sẵn, hiểu ngữ cảnh màn hình hiện tại | Không cần chuyển trang để hỏi |
| U3 | **Mọi con số có nguồn** | Con số bấm được → popover công thức, nguồn, thời điểm cập nhật, bản ghi, tài liệu gốc | Không có con số "mồ côi" |
| U4 | **AI hiển thị trạng thái thật** | Phân biệt rõ AI gợi ý / AI soạn chờ xác nhận / AI đã làm | Người dùng trả lời được "AI vừa làm gì?" |
| U5 | **Nhập một lần, nhập ở đâu cũng được** | Thả file vào bất kỳ màn hình; AI đoán đích theo ngữ cảnh | Cập nhật task ≤ 10 giây; gửi chứng từ ≤ 3 chạm trên mobile |
| U6 | **Hành động ngay tại chỗ** | Mỗi insight/cảnh báo có nút giao việc, hỏi thêm, bỏ qua trên thẻ | Không có cảnh báo "chỉ để xem" |
| U7 | **Hai mật độ cho hai kiểu người** | Thoáng cho lãnh đạo; Gọn cho Reviewer, Finance, Admin; cùng component | Reviewer xử lý hoàn toàn bằng bàn phím |
| U8 | **Tiếng Việt là mặc định** | Nhãn, số, ngày chuẩn VN; thuật ngữ quản trị quen thuộc giữ EN (KPI, OKR, pipeline) | Không nhãn dịch máy gượng gạo |

### 1.2. Ánh xạ nguyên tắc sản phẩm P01–P09 (01 §6) → UI

| P | Nguyên tắc | Hiện thực UI |
|---|---|---|
| P01 | Every number traceable | `MetricValue` luôn là nút mở `LineagePopover`; biểu đồ bấm vào điểm dữ liệu (§6.5) |
| P02 | AI shows state | Mẫu cố định theo Autonomy (§5.2); token `ai` chỉ dùng cho nội dung AI |
| P03 | Capture once, use everywhere | `GlobalDropZone` ở mọi màn hình; không form nhập lại dữ liệu đã có |
| P04 | Vietnamese-first | §7 định dạng VN + i18n |
| P05 | AI never fabricates numbers | Số trong câu trả lời AI luôn kèm `SourceChip`; số không có nguồn không được render đậm/định dạng metric |
| P06 | AI within user's permission | Panel AI hiển thị "AI đang xem: …" và phạm vi dữ liệu của role; không gợi ý câu hỏi ngoài quyền |
| P07 | Exceptions first | = U1; SCR-01 theo role (§4.1) |
| P08 | Graceful degradation | Mỗi widget có `error` riêng; khi AI lỗi, mọi luồng còn đường làm tay (§5.4) |
| P09 | Event-driven, vendor-agnostic | Cập nhật realtime nhẹ (refetch 60 s, badge "Có dữ liệu mới"); không hiển thị tên nhà cung cấp LLM cho user thường |

### 1.3. Sáu quyết định UX chính

1. **Trang chủ theo vai trò, lấy ngoại lệ làm trung tâm** — CEO thấy Briefing và "Cần anh quyết", Manager thấy team và hàng chờ duyệt, Employee thấy việc hôm nay. Không có một dashboard chung cho mọi người (SCR-01).
2. **Một thanh AI dùng ở mọi màn hình (⌘K / Ctrl+K)** — hỏi, ra lệnh, nhập liệu bằng lời, thả file; AI biết người dùng đang ở đâu, xem gì (SCR-16).
3. **Mọi con số bấm được** để xem nguồn, thời điểm cập nhật, tài liệu gốc — cơ chế chính tạo niềm tin (SCR-07).
4. **Nhập liệu không có "màn hình nhập liệu"** — thả file ở bất kỳ đâu, chụp trên mobile, hoặc nói; mọi thứ về Hộp thư dữ liệu và màn Review song song (SCR-08, SCR-10).
5. **Mỗi Autonomy Level có một mẫu giao diện cố định** — gợi ý, bản nháp chờ xác nhận, đã làm + hoàn tác (§5).
6. **Mobile chỉ làm 4 việc thật tốt** — đọc Briefing, hỏi AI, chụp/gửi tài liệu, duyệt; cấu hình và phân tích sâu ở desktop (SCR-28).

### 1.4. Phát hiện thiết kế then chốt

- CEO dùng theo nhịp ngắn (< 5 phút/lượt) → màn đầu trả lời "có gì cần tôi?" không cần cuộn.
- Niềm tin quyết định mức sử dụng → nguồn, độ tươi, độ tin cậy luôn hiển thị nhưng không chiếm chỗ.
- Employee quyết định chất lượng dữ liệu → mọi cập nhật ≤ 10 giây.
- Reviewer là người dùng chuyên nghiệp → mật độ cao, phím tắt, xử lý hàng loạt.
- AI làm việc cả khi không ai hỏi → có chỗ riêng cho "AI đã làm" và "AI đề xuất", tách khỏi thông báo thường.

---

## 2. Kiến trúc thông tin (IA) và điều hướng

Điều hướng tổ chức theo **việc người dùng muốn làm**, không theo module kỹ thuật. Thanh trên cùng là nơi bắt đầu phần lớn tác vụ; sidebar dùng khi cần vào sâu một module.

### 2.1. Sidebar (mục cấp 1)

| # | Mục | Màn hình | Ghi chú |
|---|---|---|---|
| 1 | Trang chủ | SCR-01 | Nội dung theo role (§4.1) |
| 2 | Hỏi AI | SCR-16, SCR-17 | Chat + feed "AI đã làm" |
| 3 | Hộp thư dữ liệu | SCR-08, SCR-09, SCR-10, SCR-11, SCR-12 | Badge số tài liệu chờ |
| 4 | Mục tiêu | SCR-20 | OKR / KPI, check-in |
| 5 | Công việc | SCR-19 | Task, dự án, workload |
| 6 | Họp | SCR-18 | Biên bản → quyết định → việc |
| 7 | F.O.C.U.S | SCR-02..06, SCR-07 | Nhóm 5 trụ; chỉ hiện trụ role được xem |
| 8 | Nghiệp vụ | SCR-22, SCR-23, SCR-24, SCR-25, SCR-31 | Finance / Sales / HR / Product workspace; SCR-31 Dòng tiền 13 tuần dưới Finance |
| 9 | Rủi ro | SCR-21 | Sổ rủi ro & What-if |
| 10 | Phê duyệt | SCR-29 | Badge số request chờ; chỉ hiện với `platform:approve` hoặc `platform:admin` |
| 11 | Báo cáo | SCR-30 | Ẩn với ROLE-05, 09, 10 |
| — | Quản trị (tách riêng, cuối sidebar) | SCR-14, SCR-15, SCR-26, SCR-27 | Audit, AI Control Center, user & role, loại tài liệu |

### 2.2. Top bar

Logo · breadcrumb nghiệp vụ · **thanh AI ⌘K** (ở giữa, rộng nhất) · nút "+ Gửi dữ liệu" (SCR-09) · thông báo · chọn ngôn ngữ VI/EN · role switcher (chỉ khi `DEMO_MODE=true`) · avatar/menu (mật độ, sáng/tối, đăng xuất).

### 2.3. Hiển thị theo vai trò

| Mục | ROLE-01 CEO | ROLE-02 CFO | ROLE-03 VP_SALES | ROLE-04 HR_MANAGER | ROLE-05 REVIEWER | ROLE-06 CPO | ROLE-07 RISK_MANAGER | ROLE-08 MANAGER | ROLE-09 EMPLOYEE | ROLE-10 ADMIN |
|---|---|---|---|---|---|---|---|---|---|---|
| Trang chủ | Briefing công ty | Briefing F + S | Briefing C | Briefing O | Hàng chờ + SLA | Briefing U | Briefing S | Briefing đơn vị | Việc hôm nay | Tình trạng hệ thống |
| Hỏi AI | Toàn công ty | F, S | C | O | Tài liệu được phân | U | S | Trong đơn vị | Dữ liệu của tôi | Cấu hình, audit |
| Hộp thư dữ liệu | Xem nguồn, UC-07 | Duyệt trụ F | Gửi | Duyệt nhân sự | Toàn bộ hàng chờ | Gửi | Gửi | Duyệt của đơn vị | Gửi, theo dõi | Schema, ngưỡng |
| Mục tiêu | Toàn bộ | Toàn bộ (xem) | Khối KD | Toàn bộ (xem) | — | Khối SP | Toàn bộ (xem) | Đơn vị và cấp dưới | Của tôi + mục tiêu cha | — |
| Công việc | Tổng quan thực thi | Của khối | Của khối | Của khối | — | Của khối | Của khối | Team, workload | Task của tôi | — |
| Họp | ✅ | ✅ | ✅ | ✅ | — | ✅ | ✅ | ✅ | ✅ | — |
| F.O.C.U.S | F O C U S | F, S | C | O | — | U | S | — | — | — |
| Nghiệp vụ | Tất cả (xem) | Finance | Sales | HR | — | Product | — | Theo quyền đơn vị | — | — |
| Rủi ro | ✅ (chấp nhận rủi ro) | ✅ | Xem liên quan C | Xem liên quan O | — | Xem liên quan U | ✅ (quản lý) | Ghi nhận, mitigation | Xem danh mục | — |
| Quản trị | Audit, AI Control Center, user | — | — | — | — | — | — | — | — | Tất cả |

Quyền thực tế do backend enforce (02 §ma trận quyền); bảng này chỉ là hiển thị.

### 2.4. Quy tắc điều hướng

- Mục không có quyền thì **ẩn hẳn**, không hiện rồi báo lỗi; truy cập URL trực tiếp → `ForbiddenState`.
- Người có nhiều ngữ cảnh (vd. Manager kiêm Reviewer, hoặc demo) đổi ở top bar; Trang chủ đổi theo.
- Breadcrumb theo chuỗi nghiệp vụ: Chiến lược › Objective › KR › Dự án › Task; hoặc Trụ › Metric › Bản ghi › Tài liệu.
- Mọi entity có trang chi tiết cùng bố cục: tiêu đề + trạng thái, chỉ số chính, tab (Tổng quan · Liên kết · Lịch sử · Tài liệu gốc · Hoạt động AI), Panel AI bên phải.

### 2.5. Route gợi ý (Next.js App Router)

| Route | SCR | Route | SCR |
|---|---|---|---|
| `/login` | SCR-13 | `/ai` · `/ai/activity` | SCR-16 · SCR-17 |
| `/` | SCR-01 | `/meetings` · `/meetings/[id]` | SCR-18 |
| `/pillars/[f\|o\|c\|u\|s]` | SCR-02..06 | `/work` | SCR-19 |
| `/metrics/[metricCode]` | SCR-07 | `/goals` | SCR-20 |
| `/inbox` | SCR-08 | `/risks` · `/risks/[id]` | SCR-21 |
| `/inbox/new` | SCR-09 | `/finance` · `/sales` · `/hr` · `/product` | SCR-22..25 |
| `/inbox/[documentId]/review` | SCR-10 | `/admin/audit` | SCR-14 |
| `/inbox/imports/[batchId]` | SCR-11 | `/admin/ai` | SCR-15 |
| `/onboarding` | SCR-12 | `/admin/users` · `/admin/document-types` | SCR-26 · SCR-27 |
| `/approvals` · `/approvals/[id]` | SCR-29 | `/reports` | SCR-30 |
| `/finance/cash-flow` | SCR-31 | | |

SCR-28 (mobile shell) không có route riêng: là layout `< 768 px` của `/`, `/ai`, `/inbox/new`, `/inbox`, `/approvals`.

---

## 3. Danh sách màn hình (SCR-01..31)

### 3.1. Bảng tổng hợp

Ký hiệu role: số = ROLE-xx (00 §4.1). "Tất cả" = ROLE-01..10.

| SCR | Màn hình | Mục đích | Role | Thành phần chính | Ưu tiên |
|---|---|---|---|---|---|
| SCR-01 | Trang chủ theo vai trò (Briefing) | Trả lời "có gì cần tôi?" | Tất cả (nội dung theo role) | `BriefingSummary`, `PillarCard`×n, khối "Cần anh quyết", "Rủi ro", "AI đã làm", Panel AI | Must |
| SCR-02 | Trụ F — Finance | Sức khỏe tài chính | 01, 02 | 7 `MetricCard` FIN, trend, alert list, insight trụ | Must |
| SCR-03 | Trụ O — Operations & People | Vận hành & con người | 01, 04 | 3 OPS + 4 HR metric, workload mini-heatmap | Must |
| SCR-04 | Trụ C — Customer & Growth | Pipeline, khách hàng | 01, 03 | 6 CUS metric, funnel pipeline, top khách | Must |
| SCR-05 | Trụ U — Product & Innovation | Sản phẩm được dùng thật | 01, 06 | 5 PRD metric, roadmap progress, release timeline | Must |
| SCR-06 | Trụ S — Strategy & Risk | Rủi ro & thực thi chiến lược | 01, 02, 07 | 6 RSK metric, risk heatmap 5×5, top rủi ro | Must |
| SCR-07 | Chi tiết metric + lineage | Công thức → bản ghi → tài liệu | Role xem được trụ | Header metric, trend 6 kỳ, bảng bản ghi, `LineagePopover`, `SourceViewer` | Must |
| SCR-08 | Hộp thư dữ liệu | Theo dõi mọi dữ liệu gửi lên | Tất cả trừ 10 (10 xem cấu hình) | Tab Của tôi / Chờ duyệt / Đã ghi / Lỗi, bộ lọc doc type, SLA badge | Must |
| SCR-09 | Gửi dữ liệu | C1 form, C2 nói/gõ, C3 thả file, C4 chụp | Tất cả trừ 10 | `GlobalDropZone`, `CameraCapture`, `NaturalInput`, form C1 | Must |
| SCR-10 | Review song song | Duyệt trích xuất ≤ 60 giây | 02, 04, 05, 08 (theo đơn vị) | `DocumentViewer` + vùng tô, `ExtractedFieldForm`, `ConfidenceBadge`, phím tắt | Must |
| SCR-11 | Import grid (C5) | Map cột Excel/CSV, xem trước, ghi lô | 02, 03, 04, 05, 06, 07 | Bảng map cột, preview lỗi theo dòng, nút Ghi | Must |
| SCR-12 | Nạp doanh nghiệp (UC-07) | Từ tập tài liệu đến dashboard đầu tiên | 01, 05, 10 | Drop nhiều file, tiến độ theo doc type, tổng hợp XD | Must |
| SCR-13 | Đăng nhập | Xác thực | Public | Form email/mật khẩu, quick-login demo (khi `DEMO_MODE`) | Must |
| SCR-14 | Audit log | Ai làm gì, AI làm gì | 01, 10 | Bảng lọc theo actor (người/AI), entity, thời gian | Must |
| SCR-15 | AI Control Center | Autonomy, kill switch, ngân sách, provider | 01 (xem + kill switch), 10 | Ma trận autonomy, `KillSwitch`, budget meter, trạng thái provider, feedback tổng hợp | Must |
| SCR-16 | Hỏi AI (Chat) + thanh ⌘K + Panel AI | Hỏi đáp có nguồn | Tất cả | `CommandBar`, `AIPanel`, `ChatThread`, `ThinkingState`, `SourceChip` | Must |
| SCR-17 | Feed "AI đã làm" | Dòng thời gian hành động L3 + hoàn tác | Tất cả (phạm vi của mình); 01, 10 toàn bộ | `AIActivityItem`, bộ lọc module/người/mức | Must |
| SCR-18 | Họp, biên bản & transcript → việc (UC-02, UC-06) | Biên bản / transcript mock → quyết định → task (§4.15) | 01, 02, 03, 04, 06, 07, 08, 09 | Tóm tắt 3 khối, bảng action item sửa trực tiếp, "Giao việc" | Must |
| SCR-19 | Công việc & Workload heatmap | Task, dự án, quá tải | 01, 08, 09 (task của tôi) | Bảng task, Kanban, heatmap người × tuần | Must |
| SCR-20 | Mục tiêu OKR/KPI & check-in | Theo dõi mục tiêu, check-in ≤ 30 giây | Tất cả trừ 05, 10 | Cây mục tiêu, `CheckInCard`, thanh độ tự tin | Must |
| SCR-21 | Sổ rủi ro & What-if | Quản lý rủi ro, mô phỏng tác động | 01, 02, 07; xem: 03, 04, 06, 08, 09 | Bảng rủi ro, heatmap L×I, form mitigation, `WhatIfPanel` | Must |
| SCR-22 | Finance workspace | Doanh thu, chi phí, ngân sách, dự báo, hóa đơn, tiền mặt | 01 (xem), 02, 08 (chi phí, hóa đơn) | Tab theo entity, bảng sửa trực tiếp, form | Must |
| SCR-23 | Sales workspace | Khách hàng, deal, pipeline, mục tiêu, hợp đồng | 01 (xem), 03, 08 | Kanban deal theo stage, bảng khách | Must |
| SCR-24 | HR workspace | Phòng ban, nhân viên, lương, tuyển dụng | 01, 04; 02 duyệt tuyển dụng | Bảng nhân viên (lương che theo quyền), kế hoạch tuyển dụng | Must |
| SCR-25 | Product workspace | Sản phẩm, tính năng, roadmap, release, chỉ số | 01 (xem), 06, 08 | Roadmap timeline, bảng tính năng | Must |
| SCR-26 | Quản trị người dùng & vai trò | Tạo user, gán role (không self-register) | 01, 10 | Bảng user, gán role, khóa tài khoản | Must |
| SCR-27 | Cấu hình loại tài liệu / schema / ngưỡng | Doc type, field, ngưỡng confidence, validation | 10 (sửa); 05 (xem) | Danh sách doc type, editor field, slider ngưỡng | Should |
| SCR-28 | Mobile shell | 4 việc: Briefing, hỏi AI, chụp/gửi, duyệt | Tất cả | Tab bar dưới 4 mục + nút "+" giữa, `ApprovalCard` | Must |
| **SCR-29** | Phê duyệt (v2.1 spec, build v2.0 — DEC-153) | Hàng chờ ApprovalRequest, duyệt/từ chối/bình luận; cấu hình ApprovalRule | 01, 02, 04, 08 (duyệt); 10 (quy tắc); người gửi (tab "Tôi gửi") | `ApprovalList`, `ApprovalDetail`, `ApprovalActions`, `ApprovalRuleEditor`, `SlaBadge` | Must |
| **SCR-30** | Báo cáo (DEC-153) | Tạo/tải báo cáo tuần/tháng/HĐQT PDF + Excel | 01, 02, 03, 04, 06, 07, 08 | `ReportForm`, `ReportList`, `ReportPreview` | Must |
| **SCR-31** | Dòng tiền 13 tuần (DEC-148) | Thu/chi theo tuần, tuần chạm đáy, giả định | 01, 02 | `CashFlowSummary`, `CashFlowChart`, `CashFlowTable`, `AssumptionPanel` | Must |

Tổng **31 màn hình**; đặc tả SCR-29..31 ở §4.12–4.14.

### 3.2. Trạng thái chuẩn cho mọi màn hình

| Trạng thái | Hiển thị | Ghi chú |
|---|---|---|
| Loading | Skeleton đúng hình khối (không spinner toàn trang); mỗi widget tải độc lập | 5 thẻ trụ tải song song (FR-DSH-07) |
| Empty | Minh họa nhẹ + một câu + một hành động ("Chưa có dữ liệu doanh thu T9 · Gửi báo cáo tài chính") | Luôn chỉ đường nhập dữ liệu (U5) |
| Error (widget) | `WidgetError`: "Dịch vụ tạm thời không khả dụng" + Thử lại; không ảnh hưởng widget khác | P08 |
| Error (trang) | `PageError` với mã lỗi (10 §1) và `request_id` để báo hỗ trợ | |
| Forbidden | `ForbiddenState`: "Vai trò của bạn không có quyền xem mục này" | Không lộ dữ liệu |
| Stale | `FreshnessBadge` chuyển `stale` khi quá ngưỡng của metric | §5.1 |
| Offline (PWA) | Banner "Đang ngoại tuyến · dữ liệu lúc {thời điểm}"; thao tác ghi xếp hàng nhãn "chưa đồng bộ" | §8 |
| AI unavailable | Panel AI: "Trợ lý AI tạm thời không khả dụng — thao tác thủ công vẫn dùng được" | Không chặn thao tác |

---

## 4. Đặc tả màn hình trọng yếu

### 4.1. SCR-01 — Trang chủ theo vai trò (Briefing)

**Bố cục desktop 1440 px (CEO):**

```
┌ Top bar: breadcrumb · [⌘K Hỏi AI…] · + Gửi dữ liệu · 🔔 · VI/EN · avatar ┐
│ Chào anh Minh · Thứ Hai 20/10/2026                                       │
│ "2 việc cần anh quyết, 1 rủi ro mới ở trụ S; các trụ còn lại bình thường" │ ← BriefingSummary (1 câu, U1)
│ [F ◐] [O ●] [C ◐] [U ●] [S ○]   ← 5 PillarCard (status + 1 metric chính)   │  ┌ Panel AI ─┐
│ ┌ Cần anh quyết ──────────────┐ ┌ Rủi ro ───────────────────┐             │  │ AI đang   │
│ │ Insight + Suggestion chip   │ │ top 3 rủi ro high/critical │             │  │ xem: …    │
│ └─────────────────────────────┘ └───────────────────────────┘             │  │           │
│ ┌ AI đã làm (nền token ai-subtle) · Hoàn tác ┐                             │  └───────────┘
└──────────────────────────────────────────────────────────────────────────┘
```

**Quy tắc chung:**
- Thứ tự khối cố định: Dòng tóm tắt → Thẻ trụ/chỉ số → **Cần … quyết** → Rủi ro/cảnh báo → AI đã làm. "Cần quyết" đứng trên rủi ro vì đó là việc chỉ người đó làm được.
- Mỗi thẻ trụ có `StatusIcon` (● ok · ◐ warning · ○ critical, kèm chữ), một metric chính, `FreshnessBadge`; bấm → SCR-02..06; bấm số → `LineagePopover`.
- Bấm một insight/thẻ → Panel AI mở theo ngữ cảnh entity đó (U2).
- Briefing do AI Core tạo (03 §insight); khi AI lỗi, hiển thị danh sách alert thuần (P08).

**Nội dung theo role:**

| Role | Dòng tóm tắt | Khối chỉ số | "Cần … quyết" / hàng chờ | Khối phụ |
|---|---|---|---|---|
| ROLE-01 CEO | Công ty | 5 thẻ trụ F O C U S | Decision chờ CEO, rủi ro chờ chấp nhận, Action card L2 | Rủi ro top 3, AI đã làm |
| ROLE-02 CFO | Trụ F + S | Thẻ F, S + METRIC-FIN-03 runway, FIN-06 ngân sách | Kế hoạch tuyển dụng chờ duyệt, hóa đơn chờ review trụ F | Hàng chờ IDP trụ F |
| ROLE-03 VP_SALES | Trụ C | Thẻ C + METRIC-CUS-01 coverage, CUS-02 win rate | Deal lớn có rủi ro, mục tiêu kỳ | Pipeline theo stage |
| ROLE-04 HR_MANAGER | Trụ O (con người) | METRIC-HR-01..04 | Tài liệu nhân sự chờ review, tuyển dụng trễ | Quá tải theo phòng ban |
| ROLE-05 REVIEWER | Hàng chờ | Số chờ / quá SLA / đã duyệt hôm nay / accuracy cá nhân | Hàng chờ ưu tiên theo SLA (mở SCR-10) | Phím tắt, chế độ Gọn mặc định |
| ROLE-06 CPO | Trụ U | METRIC-PRD-01..05 | Release sắp tới, churn bất thường | Roadmap trễ |
| ROLE-07 RISK_MANAGER | Trụ S | METRIC-RSK-01..06 | Rủi ro tự sinh chờ phân công, mitigation quá hạn | Heatmap L×I mini |
| ROLE-08 MANAGER | Đơn vị | Task đúng hạn, workload, KPI đơn vị | Hàng chờ duyệt của đơn vị, cảnh báo quá tải (F5) | Team hôm nay |
| ROLE-09 EMPLOYEE | Cá nhân | Task hôm nay, KR của tôi | Check-in đến hạn (F4), tài liệu đã gửi cần bổ sung | Nút lớn "Gửi chứng từ" |
| ROLE-10 ADMIN | Hệ thống | Health API/worker/queue, chi phí AI tháng, tỷ lệ lỗi pipeline | Sự cố AI, DLQ event, provider lỗi | Lối tắt SCR-15, SCR-26, SCR-27 |

CEO chọn được 4–5 chỉ số trên thẻ trụ trong cài đặt cá nhân; mặc định là metric chính của mỗi trụ (03).

### 4.2. SCR-02..06 — Trang trụ F.O.C.U.S

Bố cục chung cho 5 trụ (cùng component `PillarPage`):

| Vùng | Nội dung |
|---|---|
| Header | Tên trụ, câu hỏi lãnh đạo (00 §4.2), `StatusIcon` trụ, bộ lọc kỳ (Tháng/Quý/Năm, so với kỳ trước / cùng kỳ năm trước) |
| Insight trụ | 1–3 `InsightCard` của trụ (L0) kèm `SuggestionChip` (L1) |
| Lưới metric | `MetricCard` cho mọi metric của trụ: giá trị, so kế hoạch, sparkline 6 kỳ, `StatusIcon`, `FreshnessBadge` |
| Biểu đồ chính | Tiêu đề là kết luận; luôn có đường kế hoạch/ngưỡng |
| Alert | Danh sách `ALERT-*` của trụ: xác nhận / bỏ qua (kèm lý do) / giao việc |
| Lối vào workspace | Liên kết SCR-22..25 / SCR-21 tương ứng |

| SCR | Trụ | Metric | Biểu đồ chính | Widget riêng |
|---|---|---|---|---|
| SCR-02 | F | METRIC-FIN-01..07 | Doanh thu vs kế hoạch (cột + đường) | Runway gauge, ngân sách theo phòng ban, dự báo 3 kịch bản |
| SCR-03 | O | METRIC-OPS-01..03, METRIC-HR-01..04 | Task đúng hạn theo tuần | Mini-heatmap workload, kế hoạch tuyển dụng trễ |
| SCR-04 | C | METRIC-CUS-01..06 | Pipeline theo stage vs mục tiêu | Top 5 khách (tập trung doanh thu), NPS trend |
| SCR-05 | U | METRIC-PRD-01..05 | MAU/adoption theo sản phẩm | Roadmap progress, release timeline, churn anomaly marker |
| SCR-06 | S | METRIC-RSK-01..06 | Điểm rủi ro tổng hợp theo tháng | Heatmap 5×5 (Likelihood × Impact), top rủi ro, strategy execution index |

Trụ lỗi chỉ widget đó báo `WidgetError`. Role không xem được trụ → không có trong sidebar, URL trực tiếp → `ForbiddenState`.

---

### 4.3. SCR-07 — Chi tiết metric + lineage (P01, ≤ 3 click)

| Click | Từ → đến | Nội dung |
|---|---|---|
| 1 | Con số trên SCR-01/02..06 → `LineagePopover` hoặc SCR-07 | Công thức (03), giá trị thành phần, kỳ, nguồn, thời điểm cập nhật, ngưỡng |
| 2 | SCR-07 → bảng bản ghi đóng góp | Bản ghi domain (hóa đơn, deal, nhân viên…) có cột "nguồn": nhập tay / IDP / import, người ghi |
| 3 | Bản ghi → `SourceViewer` | Mở trang tài liệu gốc, tô vùng chứa giá trị (`source_location`), kèm field confidence |

- Trend 6 kỳ có đường kế hoạch; bấm vào điểm dữ liệu → lọc bảng bản ghi theo kỳ + nút "Hỏi AI về điểm này".
- Khi nguồn mâu thuẫn (2 giá trị cho cùng dữ liệu): hiển thị cả hai cạnh nhau, người có quyền chọn → ghi lineage.
- Bản ghi chứa lương cá nhân: role không có quyền thấy `MaskedValue` (§7.4); API không trả giá trị.

### 4.4. SCR-08 — Hộp thư dữ liệu (Data Inbox)

| Thành phần | Mô tả |
|---|---|
| Tab | Của tôi · Chờ duyệt (theo quyền) · Đã ghi · Lỗi / Trùng |
| Dòng tài liệu | Tên, doc type (AI đoán + confidence), kênh (C1–C5), trạng thái (04 state machine), người gửi, `SLABadge`, trụ đích |
| Thẻ tiến trình | Góc màn hình mọi trang: "Đang đọc 3 file" → "2 biên bản, 1 KPI · 1 cần xem lại" |
| Hành động | Mở review (SCR-10), thử lại, đánh dấu trùng / vẫn xử lý, hoàn tác (≤ 7 ngày, DEC-134) |
| Bộ lọc | Doc type, trạng thái, kênh, người gửi, khoảng ngày; tìm theo tên/MST/số hóa đơn |
| Hàng loạt (Reviewer) | Chọn nhiều → duyệt hàng loạt chỉ với tài liệu đủ điều kiện STP-ready và không có trường trọng yếu chưa xem |

### 4.5. SCR-10 — Review song song

**Bố cục chế độ Gọn:** trái 60% `DocumentViewer` (zoom, xoay, chuyển trang, vùng tô) · phải 40% `ExtractedFieldForm` (nhóm theo section schema) · footer phím tắt.

| Quy tắc | Chi tiết |
|---|---|
| Liên kết 2 chiều | Trường đang focus tô cùng màu với vùng AI đã đọc; bấm vùng trên tài liệu nhảy tới trường |
| Confidence 3 mức (DEC-133) | `ConfidenceBadge` ● Cao ≥ 0,90 · ◐ Trung bình 0,60–< 0,90 · ○ Thấp < 0,60; ở màn này hiện thêm phần trăm; Admin chỉnh ngưỡng theo doc type (SCR-27) |
| Thứ tự con trỏ | Tự nhảy vào trường cần xem trước (Thấp → Trung bình → trọng yếu), không theo thứ tự trên-dưới |
| Trường trọng yếu | Tiền, MST, số tài khoản, lương, giá trị hợp đồng: **bắt buộc đi qua** (focus + Enter) dù confidence cao |
| Lý do không chắc | AI nêu lý do bằng chữ ("ký tự thứ 4 mờ", "hai giá trị tổng khác nhau") |
| Validation | Lỗi nghiệp vụ (tổng ≠ cộng dòng, MST sai checksum, trùng hóa đơn) hiện ngay dưới trường, chặn Duyệt nếu `severity = error` |
| Ghi nhận sửa | Mỗi lần sửa ghi `ExtractionReview` (giá trị cũ/mới, thời gian) để đo accuracy theo trường |
| Khóa | Mở review là khóa tài liệu; rời trang / hết hạn khóa → nhả |
| Sau Duyệt | Ghi qua Action Registry → toast "Đã ghi 1 hóa đơn · Xem bản ghi · Hoàn tác"; mở tài liệu kế tiếp ngay |
| **"Chấp nhận tất cả HIGH"** | Nút trên đầu form (FR-DC-20, GAP B-20): xác nhận mọi field band Cao **không trọng yếu** trong một lượt (EP-30); con trỏ nhảy ngay tới field Trung bình/Thấp/trọng yếu còn lại; hiện số field đã nhận ("Đã chấp nhận 9 trường") + hoàn tác trong phiên |
| Lý do sửa trường tài chính | Sửa field tiền/trọng yếu → ô **Lý do** bắt buộc ngay dưới trường (FR-DC-05); thiếu → không lưu được field |
| Trường mới | `checkbox` hiển thị ☑/☐; chữ ký/con dấu hiển thị "Có/Không" + vùng tô; field viết tay có nhãn "Viết tay — cần xem" |
| Chuyển / gộp / SLA | Menu "Chuyển người duyệt" (lý do bắt buộc) và "Gộp với…" (04 §8.3); `SlaBadge` còn/quá hạn, nhãn "Đã escalate" |
| Không có | **Sửa hàng loạt dạng lưới** (OUT — DEC-151) |

**Phím tắt:** `Tab`/`Shift+Tab` trường kế/trước · `Enter` xác nhận trường · `Ctrl+Shift+A` Chấp nhận tất cả HIGH · `Ctrl+Enter` Duyệt tài liệu · `Ctrl+R` Từ chối (kèm lý do) · `Ctrl+→` tài liệu kế · `[` `]` trang trước/sau · `+`/`-` zoom · `?` bảng phím tắt.

**Chỉ tiêu:** hóa đơn 6 trường ≤ 60 giây (01 §4).

### 4.6. SCR-11 — Import grid (C5)

1. Tải Excel/CSV → AI gợi ý doc type đích và map cột (cột nguồn → field đích, kèm confidence).
2. Người dùng sửa map bằng dropdown; lưu map làm mẫu cho lần sau theo tên cột.
3. Xem trước **50 dòng** đầu (đồng bộ 04 FR-DC-18; 10 EP-23 `preview_rows` sửa ở 3d): dòng lỗi tô `danger` + lý do; dòng trùng tô `warning`.
4. Ghi lô: chỉ dòng hợp lệ; dòng lỗi xuất lại file để sửa. Kết quả: "Đã ghi 128 / 130 dòng · 2 lỗi · Hoàn tác lô".

---

### 4.7. SCR-15 — AI Control Center

| Khu vực | Nội dung | Quyền |
|---|---|---|
| Kill switch | Một công tắc lớn + xác nhận 2 bước + lý do; khi bật: mọi L3 → L2, chặn WRITE của AI, băng `KillSwitchBanner` trên toàn app | ROLE-01, ROLE-10 |
| Ma trận autonomy | Hàng = tool/action (TOOL-*, ACT-*), cột = role; ô = L0–L3 + ngưỡng giá trị (vd. "L3 nếu ≤ 20 tr, ngược lại L2") | ROLE-10 sửa; ROLE-01 xem |
| Ngân sách AI | Chi phí tháng / ngân sách, cảnh báo 80%, phân theo tác vụ (chat, classify, extract, insight) | ROLE-10; ROLE-01 xem |
| Provider | Trạng thái từng provider (primary/fallback), độ trễ p95, tỷ lệ lỗi; **không** hiển thị API key | ROLE-10 |
| Phân loại → provider (DEC-157) | Bảng 4 mức × provider hiệu lực (`INTERNAL` cloud · `CONFIDENTIAL` local `qwen2.5:7b-instruct` · `SECRET` không LLM); nút **"Cho phép cloud cho dữ liệu Mật"** → hộp thoại bắt buộc lý do + cảnh báo NĐ 13 → EP-129; băng vàng toàn trang SCR-15 khi override đang bật; `SECRET` không có nút | ROLE-10 sửa; ROLE-01 xem |
| Chất lượng AI | Accuracy trích xuất theo doc type/field, tỷ lệ L2 xác nhận không sửa, tỷ lệ hoàn tác L3, feedback 👎 gần nhất | ROLE-10; ROLE-01 xem |

Đổi autonomy/ngưỡng ghi audit log; nới ngưỡng tự ghi chỉ khi đạt ≥ 98% accuracy trên ≥ 200 tài liệu (04).

### 4.8. SCR-16 — Hỏi AI: thanh ⌘K, Panel AI, trang Chat

| Bề mặt | Khi dùng | Hành vi |
|---|---|---|
| `CommandBar` (⌘K / Ctrl+K) | Mọi màn hình | Một ô cho: tìm kiếm entity, hỏi, ra lệnh ("giao cho Lan báo cáo tuần"), thả file; gợi ý 3 câu theo màn hình đang mở |
| `AIPanel` | Bấm insight/metric/entity, hoặc mở từ ⌘K | Bên phải; tiêu đề "AI đang xem: {entity}"; thu gọn được; < 1280 px thành ngăn kéo |
| Trang Chat `/ai` | Phân tích dài, xem lại hội thoại | Danh sách hội thoại (xem/xóa — US-ALL), thread, gợi ý câu hỏi theo role |

**Luồng một câu trả lời:** gửi → `ThinkingState` hiển thị bước thật từ SSE (`tool_call`: "Đọc dashboard tài chính · So sánh T8 · Kiểm tra pipeline") → token streaming → `SourceChip` cuối mỗi khẳng định có số → `FeedbackBar`. Có nút **Dừng**. Nếu câu trả lời bị cắt (`truncated`) → ghi chú "Trả lời một phần do giới hạn tra cứu".

**Thời gian phản hồi (TTFT — DEC-152, FR-AI-03):** mục tiêu token đầu **p50 ≤ 2 s, p95 ≤ 5 s**.

| Mốc từ lúc gửi | Hiển thị |
|---|---|
| 0–300 ms | Tin nhắn người dùng hiện ngay (optimistic) + khung trả lời dạng **skeleton** 3 dòng (không spinner) |
| Có SSE `thinking`/`tool_call` | Thay skeleton bằng `ThinkingState` liệt kê bước thật ("Đọc dashboard tài chính…") |
| Token đầu | Bắt đầu streaming, `ThinkingState` thu gọn thành "Đã dùng 3 nguồn ▸" |
| > 5 s chưa có token | Dòng phụ "Đang tổng hợp nhiều nguồn — có thể mất thêm vài giây" + nút Dừng nổi bật |
| > 30 s (giới hạn lượt) | Dừng, hiển thị phần đã có + `truncated` + "Thử lại" |

**Khi AI không biết / sai:** "Tôi chưa có dữ liệu về X" + gợi ý bổ sung (gửi tài liệu, nhập tay); nguồn mâu thuẫn → hiển thị cả hai; lỗi hệ thống → `AI unavailable` (§3.2). Câu hỏi vượt quyền → "Câu này cần quyền {domain}; vai trò của bạn không xem được."

### 4.9. SCR-17 — Feed "AI đã làm"

- Dòng thời gian mọi hành động L3 (và L2 đã xác nhận) của AI; nền token `ai-subtle`.
- Mỗi dòng: thời điểm, hành động, đối tượng, lý do (1 câu + `SourceChip`), người bị ảnh hưởng, nút **Hoàn tác** (còn hạn 24 giờ, DEC-134; hết hạn → nút ẩn, ghi "Hết hạn hoàn tác").
- Lọc theo module, người, mức, trạng thái (đã làm / đã hoàn tác / lỗi).
- Phạm vi: người dùng thấy hành động trong phạm vi quyền của mình; ROLE-01, ROLE-10 thấy toàn bộ.

### 4.10. SCR-21 — Sổ rủi ro & What-if

| Vùng | Nội dung |
|---|---|
| Bảng rủi ro | Mã, tiêu đề, nguồn (`manual` / `event` — rủi ro tự sinh có nhãn "AI phát hiện từ {event}"), L, I, score = L × I, level, chủ sở hữu, mitigation, hạn |
| Heatmap 5×5 | Likelihood × Impact; bấm ô → lọc bảng |
| Chi tiết rủi ro | Lịch sử đánh giá, mitigation (tiến độ, quá hạn), entity liên quan (phòng ban, kế hoạch tuyển dụng, ngân sách, deal, sản phẩm) |
| Chấp nhận rủi ro | Chỉ ROLE-01; bắt buộc lý do; ghi Decision |
| `WhatIfPanel` | Chọn rủi ro hoặc nhập giả định → kết quả tác động tài chính (doanh thu, burn, runway), nhân sự, sản phẩm theo 3 kịch bản; mọi số có `SourceChip`; nút "Lưu kịch bản" |

### 4.11. SCR-28 — Mobile shell (< 768 px)

- **Tab bar dưới 4 mục + nút "+" ở giữa:** Trang chủ (Briefing) · Hỏi AI · [+] · Hộp thư · Duyệt. Nút "+" mở: Chụp chứng từ (C4), Ghi âm / nói (C2), Cập nhật task, Check-in.
- **Briefing** là trang cuộn ngắn, đọc hết trong 30 giây; hỏi bằng giọng nói ngay từ Trang chủ.
- **Chụp chứng từ chạy nền:** tự nhận cạnh, chụp nhiều trang liền; đóng app được; thông báo khi AI đọc xong hoặc cần xem lại.
- **`ApprovalCard`:** đủ thông tin để quyết không cần mở thêm (AI đã soạn gì, nguồn); hai nút lớn ≥ 44 px; vuốt để duyệt hàng loạt mục rủi ro thấp (luôn có nút thay thế cho vuốt); mục tài chính vượt ngưỡng cần xác thực lại (WebAuthn nếu thiết bị hỗ trợ, nếu không thì mật khẩu).
- **Ngoại tuyến:** ảnh chụp và cập nhật task xếp hàng, nhãn "chưa đồng bộ", tự gửi khi có mạng.
- Các màn khác trên mobile ở chế độ chỉ đọc; cấu hình, Review song song đầy đủ, quản trị chỉ trên desktop.

### 4.12. SCR-29 — Phê duyệt (Approval queue — DEC-153, DEC-155)

**Mục đích:** "Quyết định nào đang chờ tôi?" (US-CEO-006, FR-DSH-10). Hàng chờ `ENT-ApprovalRequest` của người dùng + tab cấu hình `ENT-ApprovalRule` cho ADMIN. Không phải workflow engine (01 §3 OUT).

**Role:** ROLE-01, 02, 04, 08 duyệt (theo `platform:approve` và phạm vi 02 §5.3); ROLE-10 chỉ tab Quy tắc (`platform:admin`), không thấy payload nghiệp vụ; người tạo request thấy request của mình (tab "Tôi gửi").

```
Desktop ≥ 1280 px
┌ Sidebar ┬──────────────────────────────────────────────┬────────────────────────────┐
│         │ Phê duyệt   [Chờ tôi (5)] [Tôi gửi] [Đã xử lý] [Quy tắc*] │ Chi tiết request   │
│         │ Lọc: loại ▾  trạng thái ▾  quá SLA ☐          │ Chi phí marketing Q4       │
│         │ ┌──────────────────────────────────────────┐ │ 620.000.000 đ · bước 1/2   │
│         │ │⚠ Chi phí marketing Q4  620 tr  1/2  còn 2h│◄┤ Người gửi: Trần B · 18/10  │
│         │ │  Tuyển 3 Sales HN      —      1/1  còn 6h│ │ Thay đổi đề xuất (diff)    │
│         │ │✦ AI soạn: gia hạn HĐ   80 tr   1/1  quá 1h│ │ Nguồn: [SourceChip]…       │
│         │ └──────────────────────────────────────────┘ │ Lịch sử: tạo → bước 1 …    │
│         │                                              │ Bình luận ________________ │
│         │                                              │ [Từ chối…]   [Duyệt]       │
└─────────┴──────────────────────────────────────────────┴────────────────────────────┘
* tab Quy tắc chỉ hiện với platform:admin
```

| Thành phần | Chi tiết |
|---|---|
| `ApprovalList` | Hàng: tiêu đề, giá trị (`1,2 tỷ`), bước `1/2`, `SlaBadge` (còn/quá hạn theo `due_at`), nhãn **"AI soạn"** nếu `ai_action_id` có giá trị; sắp quá SLA trước |
| `ApprovalDetail` | Payload dạng diff (trước/sau, mask mức 4), `SourceChip` tới bản ghi/tài liệu, dòng thời gian bước 1 → bước 2 → escalation |
| `ApprovalActions` | **Duyệt** / **Từ chối** (lý do bắt buộc, ≥ 10 ký tự) / **Bình luận**; tài chính > `APPROVAL_FINANCE_THRESHOLD_VND` (mặc định 500.000.000 đ — DEC-155) hiện "Cần 2 người duyệt"; người đã duyệt bước 1 hoặc người gửi **không** thấy nút ở bước 2 |
| `ApprovalRuleEditor` (tab Quy tắc) | Bảng rule: đối tượng, điều kiện đơn (field · op · giá trị), role bước 1/2, SLA giờ, escalate tới; không biểu thức tự do |
| Xác nhận | Duyệt tài chính vượt ngưỡng: hộp thoại tóm tắt + nhập lại mật khẩu/WebAuthn (OQ-04); tool APPROVAL của AI **không** tự bấm (02 §7.3) |

| Trạng thái | Hiển thị |
|---|---|
| Loading | Skeleton 5 hàng + khung chi tiết |
| Empty | "Không có yêu cầu nào chờ bạn" + link tab "Đã xử lý" |
| Error | `WidgetError` tại danh sách; duyệt lỗi `409 CONFLICT_STATE` (người khác đã xử lý) → toast + tải lại hàng |
| Success | Toast "Đã duyệt · bước 2 chuyển cho CFO" hoặc "Đã từ chối"; hàng rời tab Chờ tôi |

**Responsive:** desktop chia 60/40 danh sách–chi tiết · tablet (768–1279) danh sách toàn chiều rộng, chi tiết mở `Sheet` phải · mobile < 768 (SCR-28 tab "Duyệt") `ApprovalCard` xếp dọc, nút Duyệt/Từ chối cố định đáy, vùng chạm ≥ 44 px.
**A11y:** danh sách là `role="list"`, SLA đọc thành chữ ("quá hạn 1 giờ"); diff có nhãn "trước/sau" không chỉ bằng màu; focus chuyển vào chi tiết khi chọn hàng; phím `J/K` hàng kế/trước, `A` duyệt, `R` từ chối (mở hộp lý do).
**EP:** danh sách, chi tiết, duyệt, từ chối, CRUD rule — **EP mới dải EP-120..129, thêm ở 3d** (10); sự kiện `EVT-platform.approval_requested` / `EVT-platform.approval_decided` → badge sidebar + `ENT-Notification`.

### 4.13. SCR-30 — Báo cáo (DEC-153)

**Mục đích:** tạo, xem và tải báo cáo điều hành (US-RPT-001, US-RPT-002, US-RPT-005; FR-DSH-09). Nguồn số = `ENT-MetricValue` (snapshot `metric_snapshot`) + insight có nguồn; không BI tự do.

**Role:** ROLE-01 (công ty), ROLE-02/03/04/06/07 (trụ của mình), ROLE-08 (phòng ban); nội dung lọc theo scope người yêu cầu (02 §6). ROLE-05, 09, 10 không thấy mục này.

```
Desktop ≥ 1280 px
┌ Sidebar ┬──────────────────────────────────────────────────────────────────┐
│         │ Báo cáo                                         [+ Tạo báo cáo]  │
│         │ ┌ Tạo báo cáo ───────────────────────────────────────────────┐  │
│         │ │ Mẫu:  (•) Tuần  ( ) Tháng  ( ) HĐQT (mẫu tháng mở rộng)    │  │
│         │ │ Kỳ:   [2026-W42 ▾]   Phạm vi: [Công ty ▾]                   │  │
│         │ │ Định dạng: ☑ PDF  ☑ Excel     Kèm tóm tắt AI ☑              │  │
│         │ │                                              [Tạo]         │  │
│         │ └────────────────────────────────────────────────────────────┘  │
│         │ Lịch sử                                                         │
│         │ Kỳ        Mẫu   Phạm vi   Định dạng  Trạng thái     Tải         │
│         │ 2026-09   Tháng Công ty   PDF·XLSX   ● Sẵn sàng     ⬇ ⬇        │
│         │ 2026-W42  Tuần  Sales     PDF        ◌ Đang tạo…               │
└─────────┴──────────────────────────────────────────────────────────────────┘
```

| Thành phần | Chi tiết |
|---|---|
| `ReportForm` | Mẫu **Tuần / Tháng / HĐQT**; kỳ (`period_key` `2026-W42` / `2026-09`); phạm vi `company` hoặc phòng ban; định dạng **PDF + Excel**; tùy chọn tóm tắt AI (insight có `SourceChip`) |
| `ReportList` | Bảng lịch sử, `StatusIcon` theo `QUEUED → GENERATING → READY / FAILED`, nút tải (presigned URL ≤ 15 phút), nhãn "Tự động" cho báo cáo do job định kỳ |
| `ReportPreview` | Xem trước trang 1 PDF; mỗi số trong bản xem trước có link về SCR-07 (P01) |

Ghi chú phạm vi: **báo cáo ngày** = Briefing SCR-01 (không trùng mẫu); **HĐQT** là mẫu tháng mở rộng (thêm 5 trụ + quyết định lớn + rủi ro top), dùng cùng `report_kind = MONTHLY` — đề xuất ở OQ-08; **Word (.docx)** không có trong DEC-153 (PDF + Excel) → OQ-08.

| Trạng thái | Hiển thị |
|---|---|
| Loading | Skeleton bảng; sau khi bấm Tạo: hàng mới `◌ Đang tạo…` cập nhật qua polling 5 giây hoặc thông báo `EVT-platform.report_generated` |
| Empty | "Chưa có báo cáo nào · Tạo báo cáo tuần đầu tiên" |
| Error | Hàng `FAILED` + lý do + "Thử lại"; kỳ chưa có dữ liệu → cảnh báo trước khi tạo ("Tuần 42 thiếu dữ liệu trụ U") |
| Success | Toast "Báo cáo tháng 9 đã sẵn sàng · Tải PDF" |

**Responsive:** desktop form + bảng · tablet form thu gọn thành nút mở `Sheet` · mobile < 768: chỉ xem danh sách và tải (tạo báo cáo ở desktop, theo §1.3 quyết định 6).
**A11y:** radio mẫu/định dạng có nhãn; trạng thái tạo thông báo qua `aria-live="polite"`; link tải ghi rõ định dạng và dung lượng.
**EP:** tạo, liệt kê, tải báo cáo — **EP mới dải EP-120..129, thêm ở 3d** (10); `TOOL-generate_report` cho phép tạo từ chat (L2 — action card).

### 4.14. SCR-31 — Dòng tiền 13 tuần (DEC-148)

**Mục đích:** CFO xem dòng tiền vào/ra 13 tuần tới, tuần chạm đáy và tác động của hóa đơn mới (US-FIN-003, UC-08). Nguồn `ENT-CashFlowForecast` + `ENT-CashFlowForecastLine` (05); AI đọc qua `TOOL-get_cash_flow_forecast`.

**Role:** ROLE-01, ROLE-02 (đầy đủ); ROLE-08 không thấy (lương tổng hợp vẫn là dữ liệu tài chính công ty).

```
Desktop ≥ 1280 px
┌ Sidebar ┬──────────────────────────────────────────────────────────────────┐
│         │ Dòng tiền 13 tuần  · cập nhật 06:45 [FreshnessBadge]  [Tính lại] │
│         │ Đầu kỳ 18,4 tỷ │ Đáy 3,1 tỷ (tuần 7) ⚠ │ Cuối kỳ 9,8 tỷ │ ◐ TB   │
│         │ ┌ Biểu đồ: cột vào/ra theo tuần + đường số dư cuối tuần ───────┐ │
│         │ │ ▇▇ ▇▇ ▇▇ ...                ─── ngưỡng an toàn ─ ─ ─ ─ ─   │ │
│         │ └──────────────────────────────────────────────────────────────┘ │
│         │ Tuần │ Thu công nợ │ Thu khác │ Trả NCC │ Lương │ Opex │ Ròng │ Số dư │
│         │  W43 │  4,2 tỷ     │  0,3 tỷ  │ 2,1 tỷ  │ 3,0   │ 0,8  │ −1,4 │ 17,0  │
│         │ Giả định: thu đúng hạn 85% · chi cố định … [Sửa giả định]       │
│         │ [AI] "Tuần 7 chạm đáy do 3 hóa đơn NCC đến hạn…" [SourceChip]   │
└─────────┴──────────────────────────────────────────────────────────────────┘
```

| Thành phần | Chi tiết |
|---|---|
| `CashFlowSummary` | 4 ô: tiền đầu kỳ, đáy + tuần chạm đáy, cuối kỳ, `ConfidenceBadge` (`confidence_level`); đáy dưới ngưỡng → `StatusIcon` warning/critical |
| `CashFlowChart` (Recharts) | Cột chồng vào/ra theo tuần + đường `closing_cash`; có **bảng thay thế** cho screen reader |
| `CashFlowTable` | 13 hàng × nhóm thu/chi; ô bấm được → danh sách hóa đơn/khoản chi nguồn (SCR-07/SCR-22); lương chỉ hiện tổng (không lương cá nhân) |
| `AssumptionPanel` | Giả định (`assumptions`) — CFO sửa → tạo bản dự báo mới (`is_current`), bản cũ giữ lịch sử |
| `InsightCard` | Nhận định AI L0 có nguồn; "Mô phỏng nếu khách X trả trễ 2 tuần" → mở `WhatIfPanel` |

| Trạng thái | Hiển thị |
|---|---|
| Loading | Skeleton 4 ô + khung biểu đồ + 13 hàng |
| Empty | "Chưa có số dư tiền mặt · Nhập số dư hoặc gửi sao kê/BCTC" (chỉ đường C1/C3) |
| Error | `WidgetError` từng khối (biểu đồ lỗi không ảnh hưởng bảng) |
| Stale | `FreshnessBadge` stale khi dự báo cũ hơn hóa đơn mới nhất → nút "Tính lại" nổi bật |
| Success | Sau "Tính lại": toast "Đã cập nhật dự báo · đáy mới 3,1 tỷ (tuần 7)" |

**Responsive:** desktop đầy đủ · tablet biểu đồ trên, bảng cuộn ngang trong khung (cột Tuần cố định) · mobile < 768: chỉ 4 ô tóm tắt + biểu đồ đơn giản (số dư cuối tuần), bảng chi tiết ở desktop.
**A11y:** màu thu/chi kèm ký hiệu `+`/`−` và nhãn; số âm hiển thị dấu `−` (không chỉ màu đỏ); biểu đồ có `aria-describedby` tóm tắt đáy.
**EP:** đọc dự báo hiện hành + dòng, tính lại, sửa giả định — **EP mới (dải EP-120..129 hoặc dải finance nếu còn), thêm ở 3d** (10); `EVT-finance.cash_flow_forecast_updated` → làm mới màn hình.

### 4.15. SCR-18 — Upload transcript họp (mock — UC-02, GAP C-13)

Không phải màn hình mới: luồng con của SCR-18 (00 §4: "Họp, biên bản & transcript → việc"). v2.0 không có bot Meet/Zoom/Teams (DEC-153).

```
┌ Cuộc họp: Giao ban tuần 42 ─────────────────────────────────────────────┐
│ [Tải biên bản] [Tải transcript .txt/.vtt/.docx]                          │
│ ☑ Tôi xác nhận đã có đồng ý ghi âm của người tham dự (NĐ 13/2023)        │
│ ── Kết quả AI (AI soạn) ───────────────────────────────────────────────  │
│ Tóm tắt │ Quyết định (4) │ Việc cần làm (7) │ Rủi ro/Vấn đề/Cam kết (3)  │
│ Việc            Người        Hạn          Nguồn                          │
│ Báo giá ABC     [Lan ▾] ✓    25/10/2026   "…Lan gửi báo giá thứ Sáu" ⧉   │
│ Rà hợp đồng     [?  ▾]  ⚠    [cần xác nhận hạn]  "…sớm nhé…" ⧉            │
│                                  [Giao việc (ActionCard L2)]             │
└──────────────────────────────────────────────────────────────────────────┘
```

| Bước | Hành vi |
|---|---|
| Upload | Checkbox consent bắt buộc trước khi nút Tải bật; file > 50 MB hoặc định dạng khác → lỗi tại chỗ |
| Trích xuất | Hiện `ThinkingState` theo trạng thái pipeline (04 §8); kết quả 4 tab, nhãn **"AI soạn"** |
| Gán owner | Dropdown nhân viên đã khớp danh bạ (XD-03); không khớp → `⚠` bắt buộc chọn |
| Hạn mơ hồ | Ô hạn trống + nhãn "cần xác nhận hạn" — chặn "Giao việc" tới khi điền hoặc bỏ dòng |
| Xác nhận | "Giao việc" → `ActionCard` L2 tóm tắt N task / M quyết định / K rủi ro `proposed` → Xác nhận → `UndoToast` |

**Trạng thái:** loading (skeleton bảng + bước pipeline) · empty ("Chưa có biên bản/transcript") · error (transcript `FAILED` → "Nhập biên bản tay") · success (toast "Đã giao 7 việc · Hoàn tác"). **Responsive:** mobile chỉ xem + xác nhận từng việc (không upload). **A11y:** trích đoạn nguồn đọc được bằng screen reader; nhãn "?" có `aria-label` "chưa khớp nhân viên". **EP:** EP-20 (upload, `doc_type_hint = MEETING_MINUTES`), EP-25/EP-26 (kết quả), EP-30/EP-31 (sửa/duyệt) — đã có ở 10; trường consent trên EP-20 **thêm ở 3d**.

---

## 5. Mẫu tương tác AI

Người dùng chỉ tin AI khi luôn biết AI đang ở trạng thái nào, dựa vào đâu và có rút lại được không. Mỗi Autonomy Level gắn **một mẫu giao diện cố định**, dùng nhất quán ở mọi module (P02, U4).

### 5.1. Bộ component AI

| Component | Props chính | Hành vi |
|---|---|---|
| `CommandBar` | `contextEntity?`, `suggestions[]` | ⌘K/Ctrl+K mở; Esc đóng; phân loại input thành tìm kiếm / câu hỏi / lệnh; nhận file thả vào |
| `AIPanel` | `contextEntity`, `conversationId?`, `open` | Tiêu đề "AI đang xem: …"; giữ hội thoại theo entity; thu gọn; ngăn kéo khi < 1280 px |
| `InsightCard` (L0) | `title`, `observation`, `evidence[]`, `impact`, `recommendation?`, `confidence`, `sources[]` | Tiêu đề 1 câu là kết luận; mở rộng xem Observation → Evidence → Impact → Recommendation → Confidence |
| `SuggestionChip` (L1) | `options[1..3]` (`label`, `actionPreview`) | Bấm → mở `ActionCard` (L2) hoặc thực hiện điều hướng; có "Bỏ qua" |
| `ActionCard` (L2) | `actions[]` (loại, đối tượng, giá trị), `editable`, `sources[]` | Viền token `ai`, nhãn **"AI soạn · chờ xác nhận"**; xem trước kết quả; sửa từng dòng; nút Xác nhận / Sửa / Hủy |
| `UndoToast` (L3) | `message`, `undoUntil`, `link?` | Hiện 10 giây, **tạm dừng khi hover/focus**; "Hoàn tác" gọi undo; sau đó vào feed SCR-17 |
| `AIActivityItem` | `action`, `reason`, `sources[]`, `undoUntil` (24 h) | Dòng feed; nút Hoàn tác khi còn hạn |
| `SourceChip` | `sourceType` (record/document/metric/tool), `ref`, `updatedAt` | Chip nhỏ cuối câu; bấm → popover bản ghi gốc, tài liệu (nhảy đúng trang/vùng), thời điểm cập nhật |
| `ConfidenceBadge` | `value` (0–1), `showPercent` | ● Cao ≥ 0,90 · ◐ Trung bình 0,60–< 0,90 · ○ Thấp < 0,60 (DEC-133); chữ + biểu tượng; % chỉ hiện ở SCR-10 |
| `FreshnessBadge` | `updatedAt`, `staleAfter` | "cập nhật 06:45"; quá ngưỡng → token `stale` + "dữ liệu cũ" |
| `ThinkingState` | `steps[]` (từ SSE `thinking`/`tool_call`) | Hiện bước thật, không spinner vô nghĩa; nút Dừng; trình đọc màn hình chỉ thông báo khi xong |
| `FeedbackBar` | `targetType` (message/extraction), `targetId` | 👍 / 👎 + "Sai ở đâu?" (chọn nhanh + 1 câu); gửi vào AI Control Center |
| `KillSwitchBanner` | `activatedAt`, `by` | Băng cố định đầu app: "Đã tạm dừng hành động tự động của AI — mọi đề xuất cần xác nhận" |

Quy tắc: nhãn trạng thái dùng đúng một từ vựng ở mọi nơi — **"AI gợi ý"**, **"AI soạn"**, **"AI đã làm"**; token `ai` chỉ dùng cho nội dung do AI tạo, không dùng cho nút thường.

### 5.2. Autonomy Level → mẫu giao diện

| Mức | AI làm gì | Mẫu UI | Người dùng phải làm | Ví dụ |
|---|---|---|---|---|
| L0 Thông tin | Hiển thị, tóm tắt | `InsightCard` | Không | "Doanh thu T9 đạt 82% KH" |
| L1 Gợi ý | Đưa 1–3 phương án | `SuggestionChip` dưới insight | Chọn hoặc bỏ qua | "Chuyển 2 task sang C" |
| L2 Soạn & chờ xác nhận | Soạn hành động đầy đủ | `ActionCard` | Xác nhận, có thể sửa | Tạo 3 task từ biên bản họp |
| L3 Làm rồi báo | Tự làm trong ngưỡng policy | `UndoToast` 10 giây → feed SCR-17, hoàn tác 24 giờ | Không, trừ khi hoàn tác | Nhắc deadline; ghi hóa đơn STP |
| L4 Tự chủ | — | **Ngoài phạm vi v2** (01 §3) | — | — |

Kill switch bật → mọi thẻ L3 hiển thị như L2 (`ActionCard`) cho tới khi tắt.

### 5.3. Ngân sách & giới hạn hiển thị

- Một lượt AI tối đa 8 tool call / 30 giây (DEC-131): `ThinkingState` hiển thị tiến độ; quá giới hạn → câu trả lời một phần + ghi chú.
- Vượt rate limit (20 yêu cầu/phút/người) → thông báo thân thiện kèm thời gian chờ.

### 5.4. Khi AI lỗi (P08)

Lỗi AI (timeout, provider không phản hồi, kill switch) **không chặn thao tác thủ công**: mọi luồng có đường làm tay (form C1, sửa trực tiếp, tạo task thủ công). IDP lỗi trích xuất → tài liệu sang trạng thái cần nhập tay trong SCR-10 với trường rỗng.

---

## 6. Năm luồng người dùng chính (F1–F5)

Mỗi luồng có chỉ tiêu số chạm và thời gian để kiểm thử khả dụng (E2E T-520, usability test). Tổng hợp:

| Luồng | Role | Chỉ tiêu | SCR |
|---|---|---|---|
| F1 | ROLE-01 CEO | ≤ 2 phút, ≤ 5 chạm | SCR-01, SCR-16 (Panel), SCR-07, SCR-17 |
| F2 | ROLE-09 / mọi role gửi; ROLE-05 duyệt | Gửi ≤ 3 chạm; review ≤ 60 giây | SCR-09, SCR-08, SCR-10, SCR-28 |
| F3 | Người chủ trì họp (ROLE-01..04, 06..08) | ≤ 10 phút kể cả duyệt | SCR-18, SCR-19 |
| F4 | ROLE-09 EMPLOYEE | ≤ 30 giây | SCR-20, SCR-28 |
| F5 | ROLE-08 MANAGER | ≤ 1 phút | SCR-01, SCR-19 |

### F1 — CEO buổi sáng: từ Briefing đến giao việc

1. 07:00 nhận thông báo "Briefing sẵn sàng: 2 việc cần anh, 1 rủi ro mới".
2. Mở SCR-01: dòng tóm tắt, 5 thẻ trụ, khối "Cần anh quyết", "Rủi ro".
3. Chạm thẻ "Doanh thu T9 đạt 82% KH" → Panel AI mở: nguyên nhân, bằng chứng, `SourceChip` (có thể đi tiếp SCR-07 → tài liệu gốc).
4. Chọn `SuggestionChip` "Phương án 1: CEO tham gia 2 deal lớn" → `ActionCard` có sẵn task, owner, hạn.
5. Bấm Xác nhận → toast "Đã tạo 3 task · Hoàn tác"; quyết định ghi vào Decision (execution).

### F2 — Gửi tài liệu và AI trích xuất

1. Thả file vào bất kỳ màn hình (hoặc "+" → Chụp trên mobile).
2. Ngay lập tức: thẻ tiến trình "Đang đọc 3 file" ở góc; người dùng làm việc khác bình thường.
3. AI phân loại xong: "2 biên bản họp, 1 báo cáo KPI · 1 cần xem lại".
4. Reviewer mở SCR-10: tài liệu trái, trường phải; trường ◐/○ và trường trọng yếu được đưa lên trước; Tab qua từng trường.
5. `Ctrl+Enter` duyệt → dữ liệu ghi vào module đích qua Action Registry; toast "Xem bản ghi · Hoàn tác" (7 ngày).

### F3 — Biên bản họp thành việc (UC-06)

1. Người chủ trì tải biên bản/transcript vào cuộc họp (SCR-18).
2. AI trả về tóm tắt 3 khối: Quyết định · Việc cần làm · Vấn đề mở.
3. Bảng action item: tên người đã khớp danh bạ nhân sự (avatar), hạn quy ra ngày; mục chưa chắc gắn "?".
4. Sửa trực tiếp trong bảng → "Giao việc" (`ActionCard` L2).
5. Mỗi người nhận task kèm trích đoạn biên bản gốc (`SourceChip`).

### F4 — Check-in KPI/OKR của nhân viên

1. Thứ Sáu, thông báo "Check-in tuần: 2 KR của bạn".
2. Mở `CheckInCard`: giá trị AI điền sẵn từ dữ liệu đã có hoặc task đã xong (nhãn "AI gợi ý").
3. Kéo thanh độ tự tin; ghi blocker bằng giọng nói hoặc gõ một câu.
4. Gửi → Manager thấy trong tổng hợp team.

### F5 — Manager xử lý cảnh báo quá tải

1. SCR-01 Manager: "B quá tải 130% trong 2 tuần" (METRIC-HR-03 / ALERT-HR-03).
2. Mở SCR-19 Workload: heatmap người × tuần.
3. AI gợi ý (L1): "Chuyển 2 task sang C (50%), C đã làm việc tương tự".
4. Kéo thả hoặc bấm Áp dụng → B và C nhận thông báo kèm lý do.

---

## 7. Design system v2

Xây theo token ngay từ đầu để hỗ trợ hai mật độ, sáng/tối và đổi thương hiệu. Nền tảng: shadcn/ui trên Radix (có sẵn a11y) + Tailwind (token qua CSS variables); chỉ tự xây nhóm AI và Nhập liệu.

### 7.1. Token nền tảng

| Nhóm | Giá trị | Ghi chú |
|---|---|---|
| Font | **Be Vietnam Pro** (UI); **JetBrains Mono** (mã, số liệu bảng — tùy chọn); dự phòng Inter | Không chồng dấu tiếng Việt ở cỡ nhỏ |
| Cỡ chữ | `12 · 14 · 16 · 20 · 24 · 32` px | 14 thân chữ chế độ Gọn; 16 chế độ Thoáng; line-height 1,5 |
| Số | `font-variant-numeric: tabular-nums` trong bảng, `MetricCard`, trục biểu đồ | Cột số thẳng hàng |
| Khoảng cách | Lưới 4 px: `4 · 8 · 12 · 16 · 24 · 32 · 48` | Gọn giảm một bậc |
| Bo góc | `4` ô nhập · `8` thẻ · `16` panel · `full` nút, chip | |
| Độ sâu | 3 mức bóng: thẻ · menu nổi · hộp thoại | Chế độ tối dùng viền thay bóng |
| Chuyển động | 150 ms hover · 250 ms panel | Tôn trọng `prefers-reduced-motion` |

### 7.2. Màu theo ngữ nghĩa

| Token | Ý nghĩa | Dùng cho |
|---|---|---|
| `primary` | Màu thương hiệu | Nút chính, liên kết, mục đang chọn, focus ring |
| `ai` (+ `ai-subtle` nền) | Nội dung do AI tạo | Viền `ActionCard`, nhãn "AI soạn", Panel AI, feed "AI đã làm". **Khác hẳn `primary`** (khác hue, không chỉ khác độ đậm) |
| `success` | Đúng kế hoạch / ok / confidence Cao | `StatusIcon` ●, badge |
| `warning` | Có nguy cơ / confidence Trung bình | ◐ |
| `danger` | Lệch / critical / confidence Thấp / lỗi | ○, lỗi validation |
| `info` | Thông tin trung tính | Thông báo hệ thống |
| `neutral-0…900` | Thang xám 10 bậc | Nền, viền, chữ phụ |
| `stale` | Dữ liệu cũ | `FreshnessBadge` quá ngưỡng |

- Mỗi token có biến thể sáng và tối (`--color-<token>` / `.dark`); tương phản kiểm theo §10.
- Màu thương hiệu cụ thể (giá trị hex) chờ bộ nhận diện — OQ-01; token đặt tên trước, giá trị thay sau không đổi code.
- **Màu trạng thái không bao giờ đứng một mình:** luôn kèm chữ hoặc biểu tượng.

### 7.3. Biểu tượng trạng thái

| Biểu tượng | Nghĩa | Dùng cho |
|---|---|---|
| ● | ok / Cao | Trụ, metric, confidence |
| ◐ | warning / Trung bình | |
| ○ | critical / Thấp | |
| ↑ ↓ | Xu hướng so kỳ trước | Kèm dấu và %: `↑ +8,2%`; màu theo hướng tốt/xấu của metric, không theo chiều lên/xuống |

### 7.4. Hai mật độ (U7)

| Thuộc tính | Thoáng (mặc định ROLE-01..04, 06..09) | Gọn (mặc định ROLE-05, ROLE-10; tùy chọn mọi role) |
|---|---|---|
| Thân chữ | 16 px | 14 px |
| Hàng bảng | 44 px | 32 px |
| Padding thẻ | 24 px | 16 px |
| Mục tiêu | Đọc nhanh, ít thông tin | Mật độ cao, bàn phím |

Người dùng đổi trong menu avatar; lưu theo tài khoản.

### 7.5. Trực quan hóa dữ liệu (Recharts)

- Tiêu đề biểu đồ là **kết luận** ("Doanh thu online giảm 18% từ tháng 7"), không phải tên chỉ số.
- Luôn có đường kế hoạch/mục tiêu/ngưỡng để so sánh; màu trạng thái chỉ dùng cho phần lệch.
- Ưu tiên cột và đường; tránh biểu đồ tròn > 4 phần; không 3D.
- Đơn vị rút gọn kiểu Việt trên trục: `1,2 tỷ`, `450 tr`, `12,5%`; tooltip hiện số đầy đủ.
- Mọi điểm dữ liệu bấm được → bản ghi gốc (SCR-07) và "Hỏi AI về điểm này" (P01).
- Dữ liệu lấy trực tiếp từ chuỗi `*_trend` của API; **frontend không tự tính KPI**.
- Mỗi biểu đồ có bảng dữ liệu thay thế + mô tả một câu (a11y).

### 7.6. Danh mục component

| Nhóm | Component |
|---|---|
| Cơ bản | Button, Input, Select, DatePicker, `CurrencyInput` (VNĐ), Tabs, Menu, Dialog, Toast, Avatar, Badge, `MaskedValue` |
| Dữ liệu | `DataTable` (sắp xếp, lọc, sửa trực tiếp, chọn nhiều), `MetricCard`, `PillarCard`, Sparkline, `WorkloadHeatmap`, `RiskHeatmap`, Timeline/Gantt, `GoalTree`, `LineagePopover` |
| AI | §5.1 |
| Nhập liệu | `GlobalDropZone`, `UploadProgressCard`, `DocumentViewer` (vùng tô), `ExtractedFieldForm`, `CameraCapture`, `VoiceInput` (ghi âm/tải WAV — v2.0 mock STT), `TranscriptUpload`, `NaturalInput`, `ImportMappingGrid` |
| Trạng thái | `Skeleton`, `EmptyState`, `WidgetError`, `PageError`, `ForbiddenState`, `OfflineBanner` |
| Điều hướng | Sidebar thu gọn, Breadcrumb nghiệp vụ, `MobileTabBar`, `RoleSwitcher` (demo), `LocaleSwitcher` |

---

## 8. Định dạng Việt Nam (P04) & i18n (DEC-135)

### 8.1. Quy ước định dạng

| Loại | Tiếng Việt (mặc định) | Tiếng Anh | Ghi chú |
|---|---|---|---|
| Ngày | `05/10/2026` · `Thứ Hai` | `Oct 5, 2026` · `Mon` | Ngày giờ VI: `05/10/2026 08:30` (24 giờ) |
| Kỳ | `T9/2026`, `Q3/2026` | `Sep 2026`, `Q3 2026` | |
| Tiền đầy đủ | `1.250.000 đ` | `VND 1,250,000` | Bảng, form, Review |
| Tiền rút gọn | `850 tr`, `1,2 tỷ` | `VND 850M`, `VND 1.2B` | `MetricCard`, trục biểu đồ; tooltip số đầy đủ |
| Phần trăm | `12,5%`; chênh lệch `+8,2%` | `12.5%`; `+8.2%` | 1 chữ số thập phân |
| Số thường | `5,4 task/người` | `5.4 tasks/person` | |
| Bội số | `2,8x` | `2.8x` | |
| MST | 10 hoặc 13 số: `0312345678`, `0312345678-001` | như VI | Validate ở form C1 |
| Địa chỉ | Theo đơn vị hành chính mới | như VI | |
| Xưng hô của AI | "anh/chị" theo hồ sơ, mặc định "bạn" (Admin cấu hình) | you | OQ-03 |

### 8.2. i18n với next-intl

- **Không hard-code chuỗi** trong code (CLAUDE.md): mọi chuỗi qua message `vi` (mặc định) và `en`.
- Key theo namespace: `nav.*`, `pillar.<F|O|C|U|S>.*`, `metric.<METRIC-ID>.name`, `alert.<ALERT-ID>.title`, `idp.status.<STATUS>`, `ai.state.*`, `ai.autonomy.<L0..L3>`, `error.<code>`.
- Định dạng số/ngày/tiền qua một helper dùng chung (`Intl.NumberFormat`, `Intl.DateTimeFormat` theo locale + rút gọn tr/tỷ) — không tự format trong component.
- Tên metric/alert lấy từ i18n theo ID; API trả ID + giá trị, không trả nhãn hiển thị.
- Ngôn ngữ giao diện theo cài đặt tài khoản (`LocaleSwitcher`); **AI trả lời theo ngôn ngữ của câu hỏi**.
- Nhãn tiếng Việt dài hơn tiếng Anh 20–30%: nút và cột bảng thiết kế theo bản tiếng Việt.
- `<html lang>` đổi theo locale.

### 8.3. Văn phong

- Câu ngắn, chủ động; thuật ngữ phổ biến giữ EN (KPI, OKR, DSO, NPS, NRR, pipeline, runway, churn) kèm tooltip giải thích.
- Thông báo lỗi nói nguyên nhân + cách xử lý ("Không tải được tài liệu. Anh/chị thử lại sau ít phút.").
- Không dùng "AI" để chỉ hành động của người; không dùng "đã làm" cho việc AI chỉ mới soạn.

### 8.4. Che dữ liệu nhạy cảm

Theo mức nhạy cảm và ma trận quyền ở 02:

| Dữ liệu | Hiển thị đầy đủ cho | Role khác |
|---|---|---|
| Lương cá nhân, lịch sử lương | ROLE-01 CEO, ROLE-04 HR_MANAGER; ROLE-05 REVIEWER chỉ trong SCR-10 của tài liệu được phân (không nút tải) | `MaskedValue` `••••` + tooltip lý do, hoặc ẩn cột |
| Ngày sinh, địa chỉ, CCCD | ROLE-01, ROLE-04 | Ẩn |
| SĐT, email cá nhân | Theo phạm vi quyền (02) | Ẩn hoặc che một phần |
| Tổng hợp (quỹ lương, chi phí nhân sự) | Mọi role có quyền xem trụ liên quan | — |

- `••••` chỉ là hiển thị: **API không trả** giá trị cho role không có quyền — frontend không nhận giá trị thật để che. Độ dài `••••` cố định.
- Panel AI không bao giờ hiển thị dữ liệu "rất nhạy cảm" (lương cá nhân, ngày sinh, địa chỉ) — dữ liệu này không được gửi tới LLM (P06, 07).

---

## 9. Responsive & PWA

### 9.1. Điểm ngắt

| Điểm ngắt | Thiết bị | Bố cục |
|---|---|---|
| ≥ 1440 px | Màn hình lớn | Sidebar mở · nội dung · Panel AI cố định bên phải |
| 1280–1439 px | Laptop | Sidebar mở · Panel AI trượt ra khi cần |
| 768–1279 px | Tablet, laptop nhỏ | Sidebar thu thành biểu tượng · Panel AI phủ lên nội dung (Sheet); SCR-10 vẫn chia đôi nếu ≥ 1024 px |
| < 768 px | Điện thoại | SCR-28: tab bar dưới, 4 việc cốt lõi; màn khác chỉ đọc; SCR-10 chuyển tab "Tài liệu / Trường" |

Màn ≥ 1280 px không cuộn ngang (NFR usability). Ba nhóm kiểm thử chuẩn cho mọi màn hình mới: **mobile < 768 · tablet 768–1279 · desktop ≥ 1280** (SCR-29..31 theo §4.12–4.14).

### 9.2. PWA

- Manifest + service worker; cài lên màn hình chính; push notification (Briefing, cần duyệt, AI đọc xong).
- Camera cho C4 qua `<input type="file" accept="image/*" capture>` và `getUserMedia` khi có; không có app native (01 §3).
- Cache shell + Briefing/metric đã xem gần nhất; ngoại tuyến: banner + hàng đợi ghi (ảnh chụp, cập nhật task, check-in) nhãn "chưa đồng bộ"; thao tác khác bị vô hiệu.

---

## 10. Accessibility (WCAG 2.1 AA)

| Yêu cầu | Chi tiết |
|---|---|
| Tương phản | Chữ ≥ 4,5:1; chữ lớn (≥ 18,66 px đậm / 24 px) và thành phần UI, focus ring, đường biểu đồ ≥ 3:1 — kiểm mọi token §7.2 ở cả sáng và tối; token `ai` (tím) trên nền trắng phải đạt 4,5:1 khi dùng làm chữ; CI chạy axe-core trong Playwright (không thêm dependency ngoài DEC — kiểm ở T-002) |
| Không chỉ dựa vào màu | Trạng thái trụ/metric, confidence, trạng thái AI luôn có biểu tượng + chữ; kiểm với các dạng mù màu phổ biến |
| Bàn phím | Mọi thao tác dùng được bằng bàn phím; focus ring rõ (`primary`); phím tắt có trang tra cứu (`?`); ⌘K/Ctrl+K toàn cục |
| Screen reader | Radix giữ ARIA; `MetricCard` có `aria-label` đầy đủ ("Doanh thu tháng 9, 7,6 tỷ, 84,4% kế hoạch, cảnh báo"); biểu đồ có bảng thay thế |
| Streaming AI | Câu trả lời đang truyền dần được thông báo **khi hoàn tất**, không đọc từng token (`aria-live="polite"` trên vùng kết quả cuối) |
| Live region | Toast, tiến trình upload/UC-07, chuyển role dùng `aria-live="polite"` |
| Thời gian | `UndoToast` 10 giây, tạm dừng khi hover/focus |
| Chạm | Vùng chạm ≥ 44 × 44 px trên mobile (WCAG 2.5.5 AAA áp làm chuẩn nội bộ; tối thiểu 24 × 24 px theo 2.5.8 ở desktop); khoảng cách giữa 2 nút ≥ 8 px; không dùng vuốt làm cách duy nhất |
| Chuyển động | Tôn trọng `prefers-reduced-motion` |
| Ngôn ngữ | `<html lang="vi">` / `"en"` theo locale |
| Thông báo chờ | TTFT > 5 s và báo cáo đang tạo thông báo qua `aria-live="polite"` một lần, không lặp |

---

## 11. Chỉ số UX

| Chỉ số | Mục tiêu | Cách đo |
|---|---|---|
| Thời gian đến insight đầu tiên (CEO mở app → biết việc cần làm) | ≤ 10 giây | Usability test, phân tích phiên |
| Review một hóa đơn 6 trường | ≤ 60 giây | Log SCR-10 |
| Hoàn thành F1–F5 không cần hỗ trợ | ≥ 90% | Usability test |
| SUS | ≥ 75 | Khảo sát sau 30 ngày |
| Quản lý dùng hằng tuần | ≥ 80% | Analytics |
| `ActionCard` L2 được xác nhận không sửa | ≥ 60% và tăng dần | Log AI |
| Tỷ lệ hoàn tác hành động L3 | ≤ 5% | Feed SCR-17 |
| Tỷ lệ câu trả lời AI được mở nguồn | Theo dõi, không đặt ngưỡng | Log `SourceChip` |
| Drill-down số → tài liệu gốc | ≤ 3 click | Log UI |
| TTFT chat (DEC-152) | p50 ≤ 2 s, p95 ≤ 5 s | Đo `first_token_at − sent_at` phía client + log SSE |
| Tải màn hình dashboard | p95 < 800 ms API (03 NFR-dashboard-1); LCP ≤ 2,5 s, INP ≤ 200 ms (desktop, mạng văn phòng) | Web Vitals + log API |
| Tạo báo cáo (SCR-30) | READY ≤ 60 giây cho báo cáo công ty | `generated_at − created_at` |

Chỉ số L2/L3 là căn cứ để nâng hoặc hạ autonomy từng loại hành động (SCR-15).

---

## 12. Câu chuyện demo 20 phút → SCR

Nguồn: `01-PROJECT-OVERVIEW.md` §11; chuyển role bằng `RoleSwitcher` (`DEMO_MODE=true`, 02).

| # | Thời lượng | Bước | Role | SCR | Component chính |
|---|---|---|---|---|---|
| 1 | 2' | CEO mở app buổi sáng (F1): tóm tắt, 5 thẻ trụ, trụ S đỏ | ROLE-01 | SCR-01 | `BriefingSummary`, `PillarCard`, `StatusIcon` |
| 2 | 3' | Bấm "Doanh thu T9 đạt 82% KH" → Panel AI giải thích → drill-down tới hóa đơn và trang PDF | ROLE-01 | SCR-16 (Panel), SCR-07 | `AIPanel`, `SourceChip`, `LineagePopover`, `SourceViewer` |
| 3 | 2' | Hỏi AI câu liên miền (tuyển dụng chậm → dự báo); hỏi runway khi không có doanh thu mới | ROLE-01 | SCR-16 | `CommandBar`, `ThinkingState`, `SourceChip` |
| 4 | 2' | Chọn phương án → Action card L2 → xác nhận → 3 task, toast hoàn tác, Decision cập nhật | ROLE-01 | SCR-01, SCR-17 | `SuggestionChip`, `ActionCard`, `UndoToast` |
| 5 | 2' | Chuyển CFO / Risk Manager → dashboard đổi; chạy what-if | ROLE-02, ROLE-07 | SCR-01, SCR-02, SCR-21 | `RoleSwitcher`, `WhatIfPanel` |
| 6 | 5' | Nạp doanh nghiệp: thả 9 tài liệu mẫu → AI phân loại, trích xuất | ROLE-01 | SCR-12, SCR-08 | `GlobalDropZone`, `UploadProgressCard` |
| 7 | 2' | Review song song (F2) — duyệt hóa đơn ≤ 60 giây | ROLE-05 | SCR-10 | `DocumentViewer`, `ExtractedFieldForm`, `ConfidenceBadge` |
| 8 | 2' | Quay lại CEO: metric cập nhật, insight mới, lineage tới tài liệu vừa duyệt | ROLE-01 | SCR-01, SCR-07 | `FreshnessBadge`, `InsightCard`, `LineagePopover` |

Kịch bản dự phòng: nếu provider AI lỗi khi demo, bật `MODEL_GATEWAY_MODE=fixture` (07) — UI không đổi.

---

## 13. Open questions

| # | Câu hỏi | Đề xuất mặc định |
|---|---|---|
| OQ-01 | Bộ nhận diện thương hiệu (logo, giá trị hex `primary`) đã có chưa? Có dùng `logo_CyEyes.webp` ở repo không? | Dùng token tạm (primary xanh dương, ai tím), thay khi có brand — không ảnh hưởng code |
| OQ-02 | Briefing và duyệt có đẩy qua Zalo/Slack/Teams không? | Không trong v2 (C7 là Phase 2); chỉ in-app + push PWA |
| OQ-03 | AI xưng hô "anh/chị" hay "bạn" với nhân viên? | Mặc định "bạn"; "anh/chị" theo hồ sơ; Admin cấu hình |
| OQ-04 | Xác thực lại khi duyệt tài chính vượt ngưỡng trên mobile: WebAuthn có cần DEC dependency không? | Dùng Web API chuẩn (không thêm dependency); fallback nhập lại mật khẩu |
| OQ-05 | ✅ **DEC-153** — `VoiceInput` v2.0 gửi audio/WAV qua EP-22, ModelGateway `stt` chạy **mock** (fixture); STT thật v2.1. Câu hỏi gốc: Web Speech API hay STT server? | — |
| OQ-06 | Người dùng thử cho usability test (≥ 2 người mỗi persona) là ai? | Human chỉ định trước S5 |
| OQ-07 | SCR-27 (cấu hình doc type/schema) là Should — nếu cắt, ADMIN chỉnh ngưỡng ở đâu? | Giữ tối thiểu slider ngưỡng trong SCR-15 nếu SCR-27 bị dời |
| OQ-08 | ✅ **Duyệt (human 2026-10-20) — DEC-153:** Word export hoãn v2.1. Mẫu HĐQT dùng template tháng mở rộng (spec ở 06 §4.13 SCR-30). Câu hỏi gốc: mẫu HĐQT và xuất Word (.docx) | — |
| OQ-09 | SCR-31 có cần cho ROLE-08 xem dòng tiền phòng ban? | Không ở v2.0 (chỉ CEO, CFO) |

---

## 14. Liên kết

| Chủ đề | File |
|---|---|
| Tầm nhìn, nguyên tắc P01–P09, câu chuyện demo | `01-PROJECT-OVERVIEW.md` |
| ID registry (ROLE, SCR, METRIC, ENT) | `00-INDEX.md` §4 |
| Persona, quyền, data scoping | `02-PERSONAS-PERMISSIONS.md` |
| 5 trụ, metric, alert, insight, briefing | `03-DASHBOARD-SPEC.md` |
| IDP, review, Action Registry, autonomy | `04-IDP-FEATURE-SPEC.md` |
| Stack FE, ModelGateway, fixture mode | `07-TECH-ARCHITECTURE.md` |
| Tài khoản và tài liệu demo | `08-DEMO-DATA-SPEC.md` |
| Task FE (T-142, T-143, T-224..227, T-320..323, T-410..413, T-501..506, T-520; task SCR-29..31 bổ sung ở 3d) | `09-BUILD-PLAN-TASKS.md` |
| Endpoint, SSE event | `10-API-SPECIFICATION.md` |
| Test UI/E2E | `14-TEST-TRACEABILITY.md` |

---

## 15. Version

- **Version:** 2.1.0 (đề xuất — human promote ở 12)
- **Status:** draft (Phase 3c)
- **Last updated:** 2026-10-20
- **Applies to:** Aureon v2 (v2.0 demo-ready / v2.1 production-ready)
- **Maintainer:** @CyEyes
- **Change 2.1.0 (Phase 3c — DEC-144, DEC-148, DEC-151..153, DEC-155):** 31 màn hình — thêm **SCR-29 Phê duyệt**, **SCR-30 Báo cáo**, **SCR-31 Dòng tiền 13 tuần** (wireframe, component, 4 trạng thái, responsive 3 điểm ngắt, a11y, EP) theo đúng 00 §4 (human chọn giữ số 00, 2026-10-20); luồng con upload transcript mock trong SCR-18 (§4.15, GAP C-13); SCR-10 "Chấp nhận tất cả HIGH" (B-20), lý do sửa trường tài chính, trường checkbox/chữ ký/viết tay, chuyển/gộp/SLA, OUT bulk grid; preview 50 dòng (B-19); TTFT skeleton → thinking → stream (D-31, DEC-152); chỉ số p95/LCP/INP (D-33); touch target + tương phản chi tiết (D-34); sidebar/route mới; OQ-05 đóng, OQ-08/09 mới.
- **Change 2.0.0:** Viết lại toàn bộ theo DEC-124..137 — 28 màn hình, AI components, F1–F5, design system v2 (v1.0.0 lưu ở nhánh `v1`).
