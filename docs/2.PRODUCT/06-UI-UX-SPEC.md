# 06 — UI/UX Spec

> Đặc tả giao diện Aureon Demo: nguyên tắc UX, kiến trúc thông tin, danh sách màn hình `SCR-xx`, component, design system (§6 — màu AI, trạng thái AI L1/L2/L3), định dạng Việt Nam, i18n, responsive/PWA, a11y và mapping luồng demo 15 phút.
> Nguồn: `01-PROJECT-OVERVIEW.md` §2–§6, §11; `02-PERSONAS-PERMISSIONS.md` (quyền, §5 role switcher); `03-DASHBOARD-SPEC.md` (metric, alert, drill-down P01); `04-IDP-FEATURE-SPEC.md` (pipeline, state machine, autonomy, UC-07).
> File này là **nơi gán chính thức mã SCR-xx** (giải quyết 03 OQ-05 phần SCR).

---

## 1. Nguyên tắc UX

| Mã | Nguyên tắc | Hệ quả thiết kế | Liên kết |
|---|---|---|---|
| U2 | Hỏi ở bất kỳ đâu | Panel AI có mặt ở mọi màn hình chính (dashboard, metric detail, review); câu hỏi mang ngữ cảnh màn hình hiện tại | §5 |
| U3 | Mọi con số có nguồn | Mọi số đều click được → LineagePanel (công thức, nguồn, thời điểm cập nhật, bản ghi gốc, tài liệu gốc). Không có số "mồ côi" | P01, 03 §4 |
| U4 | AI hiển thị trạng thái thật | Mọi đầu ra AI gắn AIStateBadge L1/L2/L3 bằng màu AI riêng | P02, §6.3 |
| U5 | Nhập một lần, nhập ở đâu cũng được | Nút "Nạp dữ liệu" ở trạng thái empty của mọi trụ đưa về cùng SCR-08; không có form nhập lại dữ liệu đã có | P03 |
| U6 | Hành động ngay tại chỗ | Alert có hành động (xem chi tiết, acknowledge) ngay trên card; Review sửa field inline | 03 §3 |
| U7 | Hai mật độ (Thoáng/Gọn) | Toggle mật độ: Thoáng (mặc định) / Gọn (bảng dày, phù hợp Reviewer/CFO); lưu theo user | §6.5 |
| U8 | Tiếng Việt mặc định | Locale mặc định `vi-VN`, định dạng P04, xưng hô "anh/chị"; chuỗi qua i18n | P04, §7 |

> U1 của tài liệu nguồn không áp dụng cho bản demo (đã lược bỏ).

KPI UX bắt buộc (01 §4):

| KPI | Ngưỡng | Màn hình chịu trách nhiệm |
|---|---|---|
| Drill-down số → tài liệu gốc | ≤ 3 click | SCR-01..04 → SCR-09 → SCR-10 |
| Review 1 tài liệu (6 trường) | ≤ 60 giây | SCR-06 |
| Chuyển vai trò dashboard | ≤ 2 giây | SCR-12 → SCR-01..05 |
| Thời gian đến insight đầu tiên (CEO) | ≤ 10 giây | SCR-01 |
| Onboarding từ tập tài liệu | ≤ 15 phút | SCR-08 (UC-07) → SCR-05/06 |
| SUS score | ≥ 75 | Toàn bộ |

---

## 2. Kiến trúc thông tin (IA)

### 2.1. Điều hướng chính (sidebar)

| # | Mục | Màn hình | Role thấy mục (theo 02 §3) |
|---|---|---|---|
| 1 | Dashboard | SCR-01..04 (theo role active) | ROLE-01..04 |
| 2 | Hàng chờ (Inbox) | SCR-05 | ROLE-01 (chỉ xem), ROLE-02 (trụ FIN), ROLE-04 (trụ HR), ROLE-05 (tất cả) |
| 3 | Tài liệu | SCR-07 | ROLE-01..05 (lọc theo scope 02 §3.4) |
| 4 | Nạp dữ liệu | SCR-08 (Upload thường / Nạp doanh nghiệp UC-07) | Upload: ROLE-01..05; chế độ UC-07: chỉ ROLE-01, ROLE-05 |
| 5 | Schema tài liệu | SCR-11 (chỉ đọc, P1) | ROLE-05 |
| 6 | Nhật ký (Audit) | SCR-14 | ROLE-01 |

- Review (SCR-06), Metric Detail (SCR-09), Source Viewer (SCR-10) **không** nằm trên sidebar; chỉ vào qua ngữ cảnh (Inbox, MetricCard, link tài liệu).
- Role Switcher (SCR-12) nằm ở top bar, chỉ hiển thị khi cờ demo mode bật (02 §5.1).
- Mục "Analytics (chất lượng AI)" và "Settings (user/role)" của bản phác thảo cũ **không** có trong MVP: 02 §3.6 không có role Admin và không có UI quản trị; KPI IDP đo qua log (OQ-03).
- Mục không có quyền → **ẩn** khỏi sidebar; backend vẫn enforce (02 §4.1).

### 2.2. Top bar

`[Logo Aureon] [Breadcrumb] ……… [Ô hỏi AI (U2)] [Thông báo AI] [Toggle mật độ] [Role Switcher SCR-12] [Avatar]`

### 2.3. Route gợi ý (Next.js App Router)

| Route | SCR |
|---|---|
| `/login` | SCR-13 |
| `/dashboard` | SCR-01..04 (render theo role active) |
| `/dashboard/metrics/[metricId]` | SCR-09 |
| `/documents`, `/documents/[id]` | SCR-07 |
| `/documents/[id]/source` | SCR-10 |
| `/inbox` | SCR-05 |
| `/review/[documentId]` | SCR-06 |
| `/upload`, `/upload/onboarding` | SCR-08 (thường / UC-07) |
| `/schemas` | SCR-11 |
| `/audit` | SCR-14 |

Route chính thức chốt ở `07-TECH-ARCHITECTURE.md`; endpoint gọi từ mỗi màn ở `10-API-SPECIFICATION.md`.

---

## 3. Danh sách màn hình (SCR)

### 3.1. Bảng tổng hợp

| ID | Màn hình | Mục đích | Role | Ưu tiên | Nguồn spec |
|---|---|---|---|---|---|
| SCR-01 | Dashboard CEO | Bức tranh 4 trụ, "Cần anh/chị quyết" | ROLE-01 | P0 | 03 §5 |
| SCR-02 | Dashboard CFO | Tài chính + Vận hành (CUS, HR tổng hợp) | ROLE-02 | P0 | 03 §5.1 |
| SCR-03 | Dashboard Sales Director | Khách hàng + doanh thu (OPS tổng hợp) | ROLE-03 | P0 | 03 §5.1 |
| SCR-04 | Dashboard HR Manager | Con người + Vận hành | ROLE-04 | P0 | 03 §5.1 |
| SCR-05 | Hàng chờ IDP (Inbox) | Danh sách tài liệu `NEEDS_REVIEW`/`IN_REVIEW`/`FAILED`, lọc theo batch/trụ | ROLE-05 (tất cả), ROLE-02 (FIN), ROLE-04 (HR), ROLE-01 (xem, lương che) | P0 | 04 §8, 02 §3.4 |
| SCR-06 | Review (chi tiết duyệt) | So tài liệu gốc ↔ field trích xuất, sửa, Approve/Reject ≤ 60s | ROLE-05, ROLE-02 (FIN), ROLE-04 (HR) | P0 | 04 §7, §8 |
| SCR-07 | Tài liệu (danh sách + chi tiết) | Thư viện tài liệu, trạng thái, lịch sử, field, lineage tới metric, Undo | ROLE-01..05 (theo scope) | P0 | 04 §8 |
| SCR-08 | Upload / Nạp doanh nghiệp | Upload kênh C1–C5; chế độ UC-07 7 bước (checklist, progress, tổng hợp, đối chiếu XD) | Upload: ROLE-01..05; UC-07: ROLE-01, ROLE-05 | P0 | 04 §2, §11 |
| SCR-09 | Metric Detail (drill-down) | Panel P01 + xu hướng + BreakdownTable + bản ghi gốc | ROLE-01..04 (theo scope) | P0 | 03 §4 |
| SCR-10 | Source Viewer | Tài liệu gốc, mở đúng trang, tô vùng `source_location` | ROLE-01..04 (scope), ROLE-05 (ngữ cảnh review) | P0 | 03 §4.1, 02 §3.5 |
| SCR-11 | Extraction Schema (chỉ đọc) | Xem schema field của 7 doc type | ROLE-05 | P1 | 04 §5 |
| SCR-12 | Role Switcher | Chuyển vai trò demo ≤ 2 giây | ROLE-01..05 (demo mode) | P0 | 02 §5 |
| SCR-13 | Đăng nhập | Đăng nhập NextAuth + chọn user demo | Tất cả | P0 | 02 §5.2 R5 |
| SCR-14 | Nhật ký audit | Tra cứu audit log (chuyển role, duyệt, commit, mở tài liệu cá nhân) | ROLE-01 | P1 | 02 §3.6, §4.4 |
| SCR-15 | Cấu hình AI (chỉ đọc) | Hiển thị Autonomy theo doc type, trạng thái kill switch, ngưỡng confidence — **giá trị seed, không sửa qua UI** | ROLE-01, ROLE-05 (xem) | P1 | 04 §9, 02 §3.6 |

Ghi chú:
- SCR-15 là màn "Settings/cấu hình autonomy" mà 04 nhắc tới nhưng chưa gán ID. Vì 02 §3.6 quy định không role nào sửa cấu hình hệ thống, SCR-15 **chỉ đọc** trong MVP; quyền sửa qua UI chờ quyết định (04 OQ-04, OQ-01 ở file này).
- Bỏ "Schema Editor" (sửa) của bản phác thảo cũ — 02 §3.4 không role nào được sửa Extraction Schema → SCR-11 chỉ đọc.

### 3.2. Trạng thái chuẩn cho mọi màn hình

| Trạng thái | Quy ước hiển thị |
|---|---|
| Loading | Skeleton đúng hình dạng nội dung (card, bảng, viewer); không spinner toàn trang. Quá 10 giây → thông báo "Đang tải lâu hơn bình thường" + nút Thử lại |
| Empty | Minh họa nhẹ + 1 câu giải thích + hành động chính (VD: "Chưa có dữ liệu trụ Tài chính — Nạp dữ liệu" → SCR-08) |
| Error | Thông điệp tiếng Việt dễ hiểu theo `error.code` (10 §1) + nút Thử lại; giữ nguyên dữ liệu cũ nếu có, đánh dấu "Dữ liệu có thể đã cũ" |
| Forbidden (403) | "Nội dung thuộc phạm vi khác — anh/chị không có quyền xem" (không ẩn im lặng, 02 §4.1 mục 4) |
| Partial | Một phần dữ liệu lỗi → phần lỗi hiển thị Error cục bộ, phần còn lại vẫn render |

---

## 4. Đặc tả từng màn hình

### 4.1. SCR-01..04 — Dashboard theo role

| Thuộc tính | Nội dung |
|---|---|
| Mục đích | CEO đạt insight đầu tiên ≤ 10 giây; mỗi role thấy đúng trụ trong scope (03 §5.1) |
| Layout | Vùng 1: lời chào "Chào anh/chị {tên}" + tóm tắt 1 câu (AI gợi ý L1). Vùng 2: PillarSummary × số trụ trong scope. Vùng 3: "Cần anh/chị quyết" — AlertCard, Critical trước. Vùng 4: lưới MetricCard + TrendChart/GaugeChart theo trụ. Phải: AIPanel |
| Khác biệt theo role | SCR-01: 4 trụ, 18 metric, mọi alert. SCR-02: FIN + OPS đầy đủ, CUS/HR card tổng hợp (không click được tới bản ghi). SCR-03: CUS + METRIC-FIN-01; OPS tổng hợp. SCR-04: HR + OPS; doanh thu tổng (tổng hợp) |
| Thành phần | PillarSummary, MetricCard, AlertCard, TrendChart, GaugeChart, AIPanel, FreshnessLabel, DensityToggle |
| Tương tác | Click số → SCR-09 (click 1). Click AlertCard → SCR-09 đã lọc theo điều kiện alert. Acknowledge/dismiss theo quyền 02 §3.3 |
| Loading | Skeleton 4 PillarSummary + lưới card; số liệu chính (above the fold) render trước biểu đồ |
| Empty | Trụ chưa có dữ liệu: card `—` + "Chưa có dữ liệu nguồn" + nút "Nạp dữ liệu" (SCR-08); không sinh alert |
| Error | Card lỗi cục bộ "Không tải được chỉ số" + Thử lại; các card khác vẫn hiển thị |

**Trạng thái hiển thị của MetricCard (bắt buộc):**

| Trạng thái | Điều kiện | Hiển thị |
|---|---|---|
| Bình thường | Có giá trị, vùng xanh | Số + sparkline + FreshnessLabel |
| Cảnh báo | Chạm ngưỡng vàng | Viền/nhãn vàng + icon ⚠ (không chỉ dựa vào màu) |
| Nguy cấp | Chạm ngưỡng đỏ | Viền/nhãn đỏ + icon ⛔ |
| Chưa có dữ liệu | Không có bản ghi nguồn | `—` + "Chưa có dữ liệu nguồn" + nút Nạp dữ liệu |
| **Không tính được** | Mẫu số công thức = 0 hoặc âm, hoặc phép tính không xác định (VD: METRIC-CUS-01 khi chỉ tiêu còn lại ≤ 0; METRIC-FIN-04 khi doanh thu kỳ = 0; METRIC-HR-01/HR-02 khi headcount = 0; METRIC-OPS-01/OPS-03 khi không có task/quyết định đến hạn) | `N/A` + nhãn "Không tính được" + tooltip lý do ("Mẫu số bằng 0: chưa có task đến hạn trong kỳ"). Không tô màu ngưỡng, không sinh alert. Click vẫn mở SCR-09 với công thức và giá trị mẫu số (P01) |
| Ngoài giới hạn hiển thị | Giá trị có quy tắc riêng ở 03 (VD: METRIC-FIN-03 dòng tiền ròng ≥ 0) | Hiển thị theo 03 (VD: `> 24 tháng`) |
| Cũ | `computed_at` quá tần suất cập nhật dự kiến | FreshnessLabel màu trung tính + "Dữ liệu cập nhật lúc …" |

### 4.2. SCR-05 — Hàng chờ IDP (Inbox)

| Thuộc tính | Nội dung |
|---|---|
| Mục đích | Reviewer thấy việc cần duyệt, ưu tiên rõ; vào Review 1 click |
| Thành phần | Bộ lọc (trụ, doc type, trạng thái, batch UC-07, mức confidence), bảng QueueTable (tên file, doc type, trụ, trạng thái + AIStateBadge, confidence trung bình, số field cần kiểm tra, người upload, thời điểm `05/10/2026 08:30`, khóa "đang được … review") |
| Tương tác | Click dòng → SCR-06; FAILED → "Thử lại" / "Nhập tay (C1)" theo quyền 04 §8.2; DUPLICATE → "Vẫn xử lý" |
| Theo role | ROLE-05 tất cả; ROLE-02 chỉ trụ FIN; ROLE-04 chỉ trụ HR; ROLE-01 chỉ xem — với tài liệu chứa lương cá nhân chỉ thấy metadata, không nút mở/duyệt (02 §3.4) |
| Loading | Skeleton 8 dòng |
| Empty | "Không còn tài liệu cần duyệt 🎉" + link SCR-07 |
| Error | Banner lỗi + Thử lại; giữ danh sách cũ, đánh dấu "có thể đã cũ" |

### 4.3. SCR-06 — Review (chi tiết duyệt)

| Thuộc tính | Nội dung |
|---|---|
| Mục đích | Duyệt 1 tài liệu 6 trường ≤ 60 giây, không sai |
| Layout | Trái (≈ 55%): SourceViewer (trang, zoom, vùng tô field đang focus). Phải (≈ 45%): ExtractionForm — mỗi field: nhãn, giá trị, ConfidenceIndicator, nút "Xem trong tài liệu". Trên: tên tài liệu, doc type (có thể đổi), AIStateBadge, cờ conflict XD-*. Dưới: Approve / Sửa & Approve / Reject (bắt buộc lý do) |
| Confidence (04 §7.2) | Cao ≥ 0,90: xanh, điền sẵn. Trung bình 0,70–< 0,90: vàng, "nên kiểm tra", tự focus. Thấp < 0,70 hoặc `null` bắt buộc: đỏ, phải xác nhận trước khi Approve. Kèm icon + chữ, không chỉ màu |
| Bàn phím | `Tab`/`Shift+Tab` chuyển field, `Enter` xác nhận field, `Ctrl+Enter` Approve, `Ctrl+Backspace` Reject, `J/K` tài liệu kế/trước |
| Lương cá nhân | ROLE-05: thấy field lương trong ngữ cảnh review, không có nút tải xuống. ROLE-01 không vào được SCR-06 (chỉ xem Inbox); nếu field lương xuất hiện ở bất kỳ màn nào cho role chỉ có view-agg → hiển thị `••••` (§7.4) |
| Khóa | Mở → `IN_REVIEW`, khóa mềm 15 phút; người khác thấy "Đang được {tên} review" |
| Sau Approve | Toast "Đã duyệt · đang ghi vào hệ thống" → "Đã ghi · METRIC-xx cập nhật" + link SCR-09; tự chuyển tài liệu kế tiếp |
| Loading | Viewer skeleton + form skeleton; field hiển thị ngay khi có, trang tài liệu tải lũy tiến |
| Empty | Tài liệu không có field nào (doc type `OTHER`) → "Không có trường cần trích xuất" + chỉ cho Reject/đổi doc type |
| Error | Lỗi commit → giữ form, hiển thị lý do từ Action Registry, tài liệu về `NEEDS_REVIEW` (04 §10.2) |

### 4.4. SCR-07 — Tài liệu (danh sách + chi tiết)

| Thuộc tính | Nội dung |
|---|---|
| Mục đích | Tra cứu mọi tài liệu đã nạp, trạng thái và dữ liệu đã ghi |
| Danh sách | Bảng: tên, doc type, trụ, kênh (C1–C5), trạng thái + AIStateBadge, người upload, thời điểm; lọc + tìm kiếm |
| Chi tiết | Tab Tổng quan (metadata, trạng thái, timeline chuyển trạng thái), Field trích xuất, Dữ liệu đã ghi (entity/metric bị ảnh hưởng + link SCR-09), Lịch sử (audit) |
| Hành động | Mở SCR-10; Undo (≤ 7 ngày) cho COMMITTED theo quyền 04 §8.2 — CEO không có; Mở lại REJECTED theo quyền |
| Lương cá nhân | Role không có quyền: field lương `••••`, không có nút mở/tải file, thông báo "Tài liệu chứa dữ liệu lương cá nhân — chỉ HR Manager được mở" |
| Loading / Empty / Error | Skeleton bảng / "Chưa có tài liệu — Nạp dữ liệu" / banner lỗi + Thử lại |

### 4.5. SCR-08 — Upload / Nạp doanh nghiệp (UC-07)

| Thuộc tính | Nội dung |
|---|---|
| Mục đích | Nạp dữ liệu qua C1–C5; chế độ UC-07 đưa CEO từ tập tài liệu rời → dashboard ≤ 15 phút |
| Chế độ thường | Tabs: C1 Form nhập tay, C2 Ngôn ngữ tự nhiên (text/voice), C3 Tải file (PDF/Word/ảnh/Excel/CSV), C4 Chụp ảnh (camera trên mobile), C5 Import Excel/CSV hàng loạt. Dropzone đa file, hiển thị kích thước/định dạng hợp lệ |
| Chế độ UC-07 (ROLE-01, ROLE-05) | Stepper 7 bước theo 04 §11.1: (1) Checklist 7 loại tài liệu; (2) Kéo thả tập tài liệu → tạo batch; (3) Progress từng file theo trạng thái 04 §8 + nhãn AI ("AI đang phân loại"…); (4) Bảng tổng hợp batch (doc type, số field, % confidence cao, STP vs cần review, checklist đủ/thiếu); (5) Đối chiếu chéo XD-01→05 (MATCH ✓ / MISMATCH ✗ / NOT_COMPARABLE "Không đối chiếu được – cần review"); (6) Nút "Đi tới Review" → SCR-05 lọc batch; (7) "Xem dashboard" → SCR-01 highlight metric mới |
| Thành phần | Stepper, Dropzone, ChannelTabs, FileProgressList, BatchSummaryTable, CrossCheckList, AIStateBadge |
| Loading | Progress từng file, không chặn UI; file lỗi không chặn batch |
| Empty | Checklist 7 loại với mô tả + file mẫu |
| Error | File sai định dạng/quá cỡ → báo ngay tại dòng; `FAILED` → lý do + "Thử lại"/"Nhập tay (C1)"; `DUPLICATE` → "Đã nạp trước đó" |

### 4.6. SCR-09 — Metric Detail (drill-down)

| Thuộc tính | Nội dung |
|---|---|
| Mục đích | Click 1–2 của chuỗi drill-down ≤ 3 click (03 §4.1) |
| Thành phần | Header (tên + ID METRIC-xx, giá trị, trạng thái ngưỡng), LineagePanel (5 thành phần P01: công thức, nguồn dữ liệu, thời điểm cập nhật, bản ghi gốc, tài liệu gốc), TrendChart, BreakdownTable (phân rã theo khách/kỳ/người/khoản mục; tổng khớp metric), RecordPanel (click 2: bản ghi gốc + link tài liệu), AIPanel |
| Breadcrumb | `Dashboard › METRIC-xx › Bản ghi › Tài liệu` |
| Theo quyền | view-agg: chỉ mục 1–3 của LineagePanel + tổng hợp, không bản ghi/link. Nguồn ngoài scope: "Nguồn thuộc phạm vi khác — không có quyền xem". Nguồn là tài liệu chứa lương cá nhân với CEO/CFO: dừng ở bản ghi tổng hợp (02 §3.5) |
| Không tính được | Hiển thị công thức + giá trị tử số/mẫu số + lý do |
| Loading / Empty / Error | Skeleton / "Chưa có bản ghi nguồn cho kỳ này" / lỗi cục bộ từng khối |

### 4.7. SCR-10 — Source Viewer

| Thuộc tính | Nội dung |
|---|---|
| Mục đích | Click 3: mở tài liệu gốc đúng trang, tô vùng chứa giá trị |
| Thành phần | Viewer PDF/ảnh/Word (render)/Excel (lưới, tô ô), HighlightOverlay theo `source_location`, panel thông tin (confidence, người duyệt, thời điểm duyệt, kênh) , nút Tải xuống (theo quyền 02 §3.5) |
| Quyền | Tài liệu chứa lương cá nhân: chỉ ROLE-04 mở/tải; ROLE-05 chỉ mở trong ngữ cảnh review; role khác → màn Forbidden "Tài liệu chứa dữ liệu lương cá nhân — chỉ HR Manager được mở". Mọi lượt mở/từ chối ghi audit log |
| Loading | Tải trang lũy tiến, trang có highlight tải trước |
| Empty | Dữ liệu nhập tay (C1): "Nhập tay bởi {tên} lúc {05/10/2026 08:30}" thay cho file |
| Error | "Không mở được tài liệu" + Thử lại; vẫn hiển thị metadata |

### 4.8. SCR-11 — Extraction Schema (chỉ đọc, P1)

| Thuộc tính | Nội dung |
|---|---|
| Mục đích | Reviewer tra cứu field bắt buộc/kiểu dữ liệu của 7 doc type (04 §5) |
| Thành phần | Danh sách doc type, bảng field (tên, kiểu, bắt buộc, quy tắc chuẩn hóa P04) |
| Loading / Empty / Error | Skeleton / "Chưa cấu hình schema" / banner lỗi |

### 4.9. SCR-12 — Role Switcher

| Thuộc tính | Nội dung |
|---|---|
| Mục đích | Chuyển vai trò demo ≤ 2 giây (02 §5) |
| Thành phần | Dropdown top bar: 5 role cố định "CEO · ROLE-01" … "Reviewer · ROLE-05"; nhãn "Chế độ demo" |
| Hành vi | Chọn → backend xác lập role → xóa cache TanStack Query → điều hướng dashboard chính của role (ROLE-05 → SCR-05); prefetch dữ liệu role đích (02 §5.2 R2, R3, R8) |
| Xác nhận | Có thao tác dở (form review chưa lưu) → dialog xác nhận (R7) |
| Loading | Overlay mờ + "Đang chuyển sang {role}…" tối đa 2 giây |
| Error | Giữ role cũ, toast "Không chuyển được vai trò" (R6) |
| Ẩn | Cờ demo mode tắt → không render |

### 4.10. SCR-13 — Đăng nhập

| Thuộc tính | Nội dung |
|---|---|
| Mục đích | Đăng nhập NextAuth; trong demo cho chọn nhanh 5 user seed |
| Thành phần | Form email/mật khẩu (react-hook-form + zod), danh sách user demo (khi demo mode bật) |
| Loading / Error | Nút loading / "Email hoặc mật khẩu không đúng" (không tiết lộ email có tồn tại) |

### 4.11. SCR-14 — Nhật ký audit (P1)

| Thuộc tính | Nội dung |
|---|---|
| Mục đích | CEO tra cứu ai làm gì, AI làm gì (actor `ai:idp`) |
| Thành phần | Bảng (thời điểm, actor, hành động, đối tượng, trước/sau), bộ lọc thời gian/actor/loại hành động |
| Loading / Empty / Error | Skeleton / "Chưa có hoạt động" / banner lỗi |

### 4.12. SCR-15 — Cấu hình AI (chỉ đọc, P1)

| Thuộc tính | Nội dung |
|---|---|
| Mục đích | Minh bạch AI đang chạy ở mức nào (P02): autonomy theo doc type, kill switch, ngưỡng confidence/STP |
| Thành phần | Bảng doc type × autonomy mặc định/tối đa (04 §9), trạng thái kill switch, ngưỡng 0,70/0,90/0,95; ghi chú "Cấu hình bằng seed — không chỉnh sửa trong bản demo" |
| Loading / Empty / Error | Skeleton / — / banner lỗi |

---

## 5. Mẫu tương tác AI

| Mẫu | Mô tả | Nơi dùng | Trạng thái AI |
|---|---|---|---|
| AI Summary | 1 câu tóm tắt đầu dashboard, mỗi số trong câu click được (P01) | SCR-01..04 | L1 |
| AI Suggestion chip | Gợi ý giá trị/hành động; người bấm "Chấp nhận" mới áp dụng | SCR-06 (doc type L1), AlertCard | L1 |
| AI Draft form | Form điền sẵn, chờ Approve/Sửa/Reject | SCR-06 | L2 |
| AI Done toast | "AI đã ghi 47 hóa đơn · Hoàn tác" (nút Hoàn tác theo quyền) | SCR-05, SCR-07, SCR-08 | L3 |
| AI Progress | Nhãn tiến trình theo 04 §8.1 ("AI đang phân loại"…) | SCR-05, SCR-08 | — (đang xử lý) |
| AI Panel (U2) | Hỏi đáp theo ngữ cảnh màn hình; trả lời luôn kèm nguồn (link SCR-09/SCR-10); không tự thực hiện hành động nghiệp vụ | Mọi màn chính | L1 |
| AI Failure | "AI không xử lý được — cần nhập tay" + nút C1 | SCR-05, SCR-07, SCR-08 | — |

Quy tắc:
- Mọi nội dung do AI sinh ra phải có AIStateBadge (§6.3) và dùng màu AI — người dùng luôn trả lời được "AI vừa làm gì?" (P02).
- Câu trả lời AI không chứa số không có nguồn; số trong câu trả lời là link tới SCR-09.
- AI xưng hô "anh/chị" theo hồ sơ user (P04).
- Kill switch bật (L0) → AIPanel và chip ẩn, hiển thị banner "AI đang tắt — nhập liệu thủ công".

---

## 6. Design system

### 6.1. Nền tảng

| Hạng mục | Lựa chọn |
|---|---|
| Component library | **shadcn/ui** (copy-in components) trên **Radix UI** primitives |
| Styling | **Tailwind CSS**, token qua CSS variables (`--primary`, `--ai`, …) trong `tailwind.config` |
| Biểu đồ | Thư viện chart tương thích React/shadcn — lựa chọn cụ thể chốt ở 07 (OQ-02) |
| Icon | Bộ icon mặc định của shadcn/ui |
| Font | **Be Vietnam Pro** (UI, hỗ trợ đầy đủ dấu tiếng Việt); **JetBrains Mono** (số liệu bảng, mã ID, `METRIC-xx`) — dùng `font-variant-numeric: tabular-nums` cho cột số |
| Theme | Light mặc định; dark mode P1 |

### 6.2. Token màu

| Token | Vai trò | Gợi ý giá trị (light) | Ghi chú |
|---|---|---|---|
| `--primary` | Hành động chính, nút, link, focus | Xanh dương đậm (VD `#1D4ED8`) | Thương hiệu Aureon |
| `--ai` | **Mọi nội dung/thao tác do AI** | Tím (VD `#7C3AED`) | **Phải khác `--primary`** (CLAUDE.md) |
| `--ai-muted` | Nền nhẹ cho khối AI | Tím rất nhạt (VD `#F5F3FF`) | |
| `--status-ok` | Metric vùng xanh, confidence cao | Xanh lá (VD `#15803D`) | |
| `--status-warn` | Ngưỡng vàng, confidence trung bình | Hổ phách (VD `#B45309`) | |
| `--status-critical` | Ngưỡng đỏ, confidence thấp, lỗi | Đỏ (VD `#B91C1C`) | |
| `--neutral-*` | Nền, viền, chữ phụ, trạng thái "Không tính được" | Thang xám | |

- Giá trị hex là gợi ý; mọi cặp chữ/nền phải đạt tương phản WCAG AA (§9).
- Màu trạng thái metric **không** được dùng cho nội dung AI và ngược lại.

### 6.3. Màu AI và 3 trạng thái AI (P02)

**Quy tắc cứng:** mọi thành phần thể hiện hành vi AI dùng token `--ai`, **không bao giờ** dùng `--primary`. Nút hành động của người dùng (Approve, Lưu) dùng `--primary`; gợi ý/nháp của AI dùng `--ai`. Như vậy người dùng phân biệt bằng mắt "việc của tôi" và "việc của AI".

| Level | Nhãn UI (i18n key) | AIStateBadge | Hành vi UI | Hành động người dùng |
|---|---|---|---|---|
| L0 | "AI tắt" (`ai.state.off`) | Viền xám, icon AI gạch chéo | Không có gợi ý | Nhập tay |
| **L1** | **"AI gợi ý"** (`ai.state.suggest`) | Viền `--ai`, nền trắng, icon ✦ | Chip gợi ý viền tím đứt nét; form trống | Bấm "Chấp nhận" từng gợi ý |
| **L2** | **"AI soạn · chờ xác nhận"** (`ai.state.draft`) | Nền `--ai-muted`, chữ `--ai`, icon ✎ | Field điền sẵn có gạch chân tím; nút Approve (primary) | Approve / Sửa / Reject |
| **L3** | **"AI đã làm"** (`ai.state.done`) | Nền `--ai` đặc, chữ trắng, icon ✓ | Toast + mục trong thông báo AI, nút **Hoàn tác** (nếu có quyền và ≤ 7 ngày) | Hoàn tác (tùy chọn) |

Yêu cầu:
- AIStateBadge luôn có **chữ + icon**, không chỉ màu (a11y).
- Badge xuất hiện tại: dòng Inbox (SCR-05), header Review (SCR-06), chi tiết tài liệu (SCR-07), progress UC-07 (SCR-08), toast/thông báo, AI Summary (SCR-01..04).
- Field do người sửa sau gợi ý AI chuyển sang style thường (không còn tím) + ghi chú "Đã sửa bởi {tên}".

### 6.4. Typography & spacing

| Token | Giá trị gợi ý | Dùng cho |
|---|---|---|
| `text-display` | 32/40, semibold | Số chính MetricCard |
| `text-h1` / `h2` / `h3` | 24 / 20 / 16, semibold | Tiêu đề màn / khối / card |
| `text-body` | 14/20 | Nội dung |
| `text-caption` | 12/16 | FreshnessLabel, chú thích |
| Spacing | Thang 4 px (Tailwind mặc định) | |
| Radius | `rounded-lg` card, `rounded-md` input | |

### 6.5. Mật độ (U7)

| Mật độ | Hàng bảng | Padding card | Mặc định cho |
|---|---|---|---|
| Thoáng | 48 px | 24 px | ROLE-01, ROLE-03, ROLE-04 |
| Gọn | 36 px | 16 px | ROLE-02, ROLE-05 |

### 6.6. Danh mục component

| Component | Nền shadcn/Radix | Dùng ở | Yêu cầu chính |
|---|---|---|---|
| MetricCard | Card | SCR-01..04 | Số + sparkline + ngưỡng + FreshnessLabel; các trạng thái §4.1 (gồm "Không tính được"); click → SCR-09 |
| PillarSummary | Card | SCR-01..04 | Màu theo alert nặng nhất của trụ |
| AlertCard | Alert, Button | SCR-01..04 | Mức độ (icon + chữ), hành động đề xuất (AI L1), acknowledge/dismiss theo quyền |
| TrendChart / GaugeChart | (chart lib) | SCR-01..04, SCR-09 | Mọi điểm dữ liệu click được; định dạng P04 trên trục/tooltip |
| LineagePanel | Sheet / Popover | Mọi số | 5 thành phần P01; thông báo chặn quyền |
| BreakdownTable / QueueTable | Table, DataTable | SCR-05, SCR-07, SCR-09 | Phân trang, sort, lọc; cột số căn phải, tabular-nums |
| SourceViewer + HighlightOverlay | ScrollArea | SCR-06, SCR-10 | Mở đúng trang, tô `source_location` |
| ExtractionForm + ConfidenceIndicator | Form (react-hook-form + zod), Input, Tooltip | SCR-06 | Màu + icon + % confidence; tự focus field cần kiểm tra |
| AIStateBadge | Badge | Nhiều màn | §6.3 |
| AIPanel | Sheet | Mọi màn chính | U2, kèm nguồn |
| Stepper, Dropzone, FileProgressList, BatchSummaryTable, CrossCheckList | Tabs, Progress, Table | SCR-08 | UC-07 |
| RoleSwitcher | DropdownMenu, Dialog | Top bar | SCR-12 |
| MaskedValue | — | SCR-05, SCR-07, SCR-09 | Hiển thị `••••` cho field lương (§7.4) |
| FreshnessLabel | — | MetricCard, SCR-09 | "Cập nhật 05/10/2026 08:30" |
| EmptyState / ErrorState / ForbiddenState / Skeleton | Skeleton | Mọi màn | §3.2 |

---

## 7. Định dạng Việt Nam (P04) & i18n

### 7.1. Quy ước định dạng

| Loại | Định dạng | Ví dụ | Ghi chú |
|---|---|---|---|
| Ngày | `dd/MM/yyyy` | `05/10/2026` | Ngày giờ: `05/10/2026 08:30` (24 giờ) |
| Kỳ | `T{m}/yyyy`, `Q{q}/yyyy` | `T9/2026`, `Q3/2026` | |
| Tiền đầy đủ | dấu chấm nghìn + ` đ` | `1.250.000 đ` | Bảng, form, Review |
| Tiền rút gọn | dấu phẩy thập phân + `tr`/`tỷ` | `850 tr`, `1,2 tỷ` | MetricCard, trục biểu đồ; tooltip hiển thị số đầy đủ |
| Phần trăm | 1 chữ số thập phân, dấu phẩy | `12,5%` | Chênh lệch có dấu: `+8,2%` |
| Số thường | dấu chấm nghìn, dấu phẩy thập phân | `5,4 task/người` | |
| Bội số | `2,8x` | | |
| MST | 10 hoặc 13 số | `0312345678`, `0312345678-001` | Validate ở form C1 |
| Địa chỉ | Theo đơn vị hành chính mới | | |
| Xưng hô | "anh/chị" theo hồ sơ | "Chào anh Minh" | |

### 7.2. i18n

- **Không hard-code tiếng Việt trong code** (CLAUDE.md): mọi chuỗi UI qua file message `vi` (mặc định), cấu trúc key sẵn cho `en`.
- Key theo namespace: `dashboard.*`, `metric.<METRIC-ID>.name`, `alert.<ALERT-ID>.title`, `idp.status.<STATUS>`, `ai.state.*`, `error.<code>`.
- Định dạng số/ngày/tiền qua một helper dùng chung (`Intl.NumberFormat('vi-VN')`, `Intl.DateTimeFormat('vi-VN')` + rút gọn tr/tỷ) — không tự format trong component.
- Tên metric/alert lấy từ i18n theo ID, không lấy chuỗi tiếng Việt từ API (API trả ID + giá trị).
- Thư viện i18n cụ thể chốt ở 07 (OQ-02).

### 7.3. Văn phong

- Câu ngắn, chủ động, không dịch máy gượng gạo; thuật ngữ giữ nguyên EN khi phổ biến (DSO, NPS, NRR, pipeline) kèm tooltip giải thích.
- Thông báo lỗi nói nguyên nhân + cách xử lý ("Không tải được tài liệu. Anh/chị thử lại sau ít phút.").

### 7.4. Che dữ liệu lương cá nhân

Theo 02 §3.4, §3.5, §4.3:

| Role | Field lương cá nhân | File gốc tài liệu chứa lương |
|---|---|---|
| ROLE-01 CEO | `••••` (MaskedValue) + tooltip "Chỉ HR Manager xem được lương cá nhân" | Không mở/tải; hiển thị ForbiddenState |
| ROLE-02 CFO | `••••` (chỉ thấy tổng chi phí nhân sự) | Không mở/tải |
| ROLE-03 Sales Director | Không hiển thị | Không mở/tải |
| ROLE-04 HR Manager | Giá trị đầy đủ | Mở + tải |
| ROLE-05 Reviewer | Giá trị đầy đủ **chỉ trong SCR-06** của tài liệu đó | Mở trong ngữ cảnh review, không nút tải |

- `••••` chỉ là hiển thị: API **không trả** giá trị cho role không có quyền (02 §4.1 mục 6) — frontend không nhận giá trị thật để che.
- Độ dài `••••` cố định, không phản ánh số chữ số thật.
- Tổng hợp (quỹ lương, chi phí nhân sự) vẫn hiển thị số bình thường cho role có view-agg.

---

## 8. Responsive & PWA

| Breakpoint | Bố cục |
|---|---|
| ≥ 1280 px (desktop) | Sidebar + nội dung + AIPanel cố định bên phải |
| 768–1279 px (tablet) | Sidebar thu gọn icon; AIPanel dạng Sheet |
| < 768 px (mobile) | 1 cột; sidebar → menu dưới (bottom nav 4 mục); AIPanel → nút nổi; SCR-06 chuyển tab "Tài liệu / Trường" thay cho chia đôi |

- **PWA**: manifest + service worker; cài lên màn hình chính; cache shell + metric đã xem gần nhất để chạy offline mức demo (01 §7) — hiển thị banner "Đang ngoại tuyến · dữ liệu lúc {thời điểm}"; thao tác ghi bị vô hiệu khi offline.
- **C4 (chụp ảnh)**: trên mobile, SCR-08 mở camera qua `<input type="file" accept="image/*" capture>`; không có app native (01 §3).
- Ưu tiên mobile: SCR-01..04 (xem), SCR-08 (C4), thông báo; SCR-06 dùng được nhưng tối ưu cho desktop.

---

## 9. Accessibility (a11y)

| Yêu cầu | Chi tiết |
|---|---|
| Chuẩn | WCAG 2.1 AA |
| Tương phản | Chữ thường ≥ 4,5:1; chữ lớn/icon ≥ 3:1 — kiểm cho mọi token §6.2 |
| Không chỉ dựa vào màu | Ngưỡng metric, confidence, trạng thái AI luôn có icon + chữ |
| Bàn phím | Mọi thao tác dùng được bằng bàn phím; focus ring `--primary` rõ ràng; phím tắt SCR-06 (§4.3) có trang trợ giúp `?` |
| Screen reader | Radix primitives giữ ARIA; MetricCard có `aria-label` đọc đủ "Doanh thu tháng 9, 7,6 tỷ, 84,4% kế hoạch, cảnh báo"; biểu đồ có bảng dữ liệu thay thế |
| Live region | Toast, progress UC-07, chuyển role dùng `aria-live="polite"` |
| Chuyển động | Tôn trọng `prefers-reduced-motion` |
| Ngôn ngữ | `<html lang="vi">` |

---

## 10. Luồng demo 15 phút → SCR

Nguồn: `01-PROJECT-OVERVIEW.md` §11; role active theo `02-PERSONAS-PERMISSIONS.md` §5.3.

| Bước | Thời lượng | Hành động demo | Role active | Màn hình (chuỗi SCR) | Điểm UI cần thể hiện |
|---|---|---|---|---|---|
| 1 | 2' | CEO mở app buổi sáng → thấy 2 việc cần quyết, 1 rủi ro mới | ROLE-01 CEO | SCR-13 → SCR-01 | AI Summary (L1); vùng "Cần anh quyết" với AlertCard; insight ≤ 10 giây |
| 2 | 2' | Click cảnh báo doanh thu → xem nguyên nhân + nguồn | ROLE-01 CEO | SCR-01 (ALERT-FIN-01) → SCR-09 → SCR-10 | ≤ 3 click; LineagePanel đủ 5 thành phần P01; tô vùng doanh thu trong tài liệu #1/#2 |
| 3 | 2' | Chuyển vai CFO → dashboard đổi → xem chi tiết ngân sách | ROLE-02 CFO | SCR-12 → SCR-02 → SCR-09 (METRIC-FIN-06) | Chuyển ≤ 2 giây; layout đổi theo scope FIN + OPS |
| 4 | 5' | Vào "Nạp doanh nghiệp" → upload 7 tài liệu mẫu → AI xử lý | ROLE-01 CEO (phụ: ROLE-05) | SCR-12 → SCR-08 (chế độ UC-07, bước 1–5) | Progress + nhãn AI; L3 "AI đã làm" cho tài liệu STP; đối chiếu XD |
| 5 | 2' | Vào Review → duyệt 1 tài liệu → thấy dữ liệu vào hệ thống | ROLE-05 Reviewer (phụ: ROLE-02 với tài liệu FIN) | SCR-12 → SCR-05 (lọc batch) → SCR-06 | L2 "AI soạn · chờ xác nhận"; duyệt ≤ 60 giây; toast "Đã ghi · METRIC-xx cập nhật". **Không** chọn tài liệu #6 |
| 6 | 2' | Quay lại CEO dashboard → dữ liệu mới + drill-down đến tài liệu gốc | ROLE-01 CEO | SCR-12 → SCR-01 → SCR-09 → SCR-10 | Highlight metric mới; drill-down tới tài liệu FIN/CUS vừa duyệt |

- 4 lần chuyển vai trò (bước 3, 4, 5, 6), mỗi lần ≤ 2 giây qua SCR-12.
- Bước 4 với phương án phụ: chuyển sang ROLE-05 ngay ở bước 4 và giữ nguyên cho bước 5 (02 §5.3).

---

## 11. Open questions

| ID | Câu hỏi | Ảnh hưởng | Đề xuất tạm |
|---|---|---|---|
| OQ-01 | SCR-15 (Cấu hình AI) chỉ đọc vì 02 §3.6 không có Admin; có cần cho một role (VD CFO trụ FIN) chỉnh autonomy/kill switch qua UI không? (liên quan 04 OQ-04) | 02, 04, 10 | Giữ chỉ đọc trong MVP |
| OQ-02 | Thư viện chart và thư viện i18n cụ thể (chưa có trong tech stack CLAUDE.md) | 07, dependency mới cần DEC | 07 đề xuất, captain raise DEC |
| OQ-03 | Bỏ mục "Analytics (chất lượng AI)" của phác thảo cũ; KPI IDP (accuracy, STP) chỉ đo qua log. Có cần màn Analytics cho demo không? | Scope | Không có trong MVP |
| OQ-04 | Giá trị hex của token màu là gợi ý; cần nhận diện thương hiệu Aureon chính thức | Design | Dùng giá trị gợi ý §6.2 |
| OQ-05 | Mật độ mặc định theo role (§6.5) là đề xuất của writer | UX | Giữ đề xuất; người dùng đổi được |
| OQ-06 | Route `/…` ở §2.3 là gợi ý; route chính thức và EP-xx gọi từ từng SCR cần 07/10 chốt | 07, 10 | 10 tham chiếu ngược SCR-xx |
| OQ-07 | Ngưỡng "Dữ liệu cũ" của FreshnessLabel (bao lâu so với tần suất cập nhật) | SCR-01..04 | Gấp 2 lần tần suất cập nhật ở 03 §2 |

---

## 12. Liên kết

| Chủ đề | File |
|---|---|
| Phạm vi, KPI, P01–P04, kịch bản demo | `01-PROJECT-OVERVIEW.md` |
| Quyền, che lương, role switcher | `02-PERSONAS-PERMISSIONS.md` |
| Metric, alert, drill-down | `03-DASHBOARD-SPEC.md` |
| Pipeline IDP, trạng thái, autonomy, UC-07 | `04-IDP-FEATURE-SPEC.md` |
| Stack, route, thư viện | `07-TECH-ARCHITECTURE.md` |
| Endpoint, error code | `10-API-SPECIFICATION.md` |

---

## 13. Version

- **Version:** 1.0.0
- **Last updated:** 2026-10-17
- **Applies to:** Aureon Demo v1.0
- **Maintainer:** @CyEyes
