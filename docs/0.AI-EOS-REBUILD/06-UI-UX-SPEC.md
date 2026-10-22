# 06 — UI/UX Spec (AI-EOS, nhánh `ai-eos`)

> **Nguồn chuẩn:** `_reference/SOURCE-UIUX.md` (AI-EOS UI/UX v1.0) + `SOURCE-BRD-v1.1.md` §11.6/§12.
> **Phụ thuộc:** 00, 01, 02, 03. **Trạng thái:** 🟡 draft (Phase R2). **Ngày:** 2026-10-22 · **Maintainer:** @CyEyes

---

## 1. Persona thiết kế (UIUX §2.1)

CEO (Thoáng, di động, ngoại lệ) · Director/Manager (đơn vị, duyệt) · Employee (task, check-in nhanh) · Reviewer (Gọn, bàn phím) · Admin (cấu hình, audit). Ánh xạ 7 role: 02 §2.

## 2. 8 nguyên tắc UX (UIUX §3) — tiêu chí duyệt mọi màn hình

| # | Nguyên tắc | Kiểm tra nhanh |
|---|---|---|
| U1 | Ngoại lệ trước, chi tiết sau | CEO trả lời "có gì cần tôi?" trong 10s |
| U2 | Hỏi ở bất kỳ đâu (⌘K, hiểu ngữ cảnh) | Không cần chuyển trang để hỏi |
| U3 | Mọi con số có nguồn (popover: công thức/nguồn/cập nhật/tài liệu gốc) | Không có con số "mồ côi" |
| U4 | AI hiển thị trạng thái thật (gợi ý/soạn/đã làm) | Luôn trả lời "AI vừa làm gì?" |
| U5 | Nhập một lần, nhập ở đâu cũng được | Task ≤ 10s; gửi chứng từ ≤ 3 chạm mobile |
| U6 | Hành động ngay tại chỗ (nút trên mỗi insight/cảnh báo) | Không có cảnh báo "chỉ để xem" |
| U7 | Hai mật độ (Thoáng cho lãnh đạo / Gọn cho Reviewer, Finance, Admin) | Reviewer dùng bàn phím hoàn toàn |
| U8 | Tiếng Việt mặc định (1.250.000 đ; 05/10/2026; giữ KPI/OKR/pipeline EN) | Không nhãn dịch máy gượng |

## 3. Kiến trúc thông tin (UIUX §4)

Điều hướng theo **việc người dùng muốn làm**, không theo 28 domain kỹ thuật → **gộp 28 domain vào 8 mục** + Quản trị riêng: Trang chủ · Hỏi AI · Mục tiêu · Công việc · Họp & lịch · Dữ liệu · Kinh doanh · Tri thức/báo cáo (+ Quản trị).

- **Hiển thị theo vai trò** (UIUX §4.1): mỗi mục đổi nội dung theo CEO/Director-Manager/Employee/Reviewer/Admin.
- Mục không có quyền **ẩn hẳn** (không hiện rồi báo lỗi).
- Người nhiều vai trò đổi ngữ cảnh ở thanh trên; Trang chủ đổi theo.
- **Breadcrumb nghiệp vụ:** Chiến lược › Objective › KR › Dự án › Task (P06).
- Mọi entity có trang chi tiết cùng bố cục: tiêu đề+trạng thái, chỉ số chính, tab (Tổng quan/Liên kết/Lịch sử/Tài liệu gốc/Hoạt động AI), panel AI phải.

## 4. Luồng người dùng chính (UIUX §5)

| Flow | Mục tiêu |
|---|---|
| F1 CEO buổi sáng: Briefing → giao việc (UC-01, UC-03) | ≤ 2 phút, ≤ 5 chạm |
| F2 Gửi tài liệu → AI trích xuất (US-DC-003/006) | gửi ≤ 3 chạm, review ≤ 60s |
| F3 Biên bản họp → việc (UC-02, UC-06) | ≤ 10 phút kể cả duyệt |
| F4 Check-in KPI/OKR nhân viên (US-OKR-006) | ≤ 30s |
| F5 Manager xử lý cảnh báo quá tải (US-TASK-003/004) | ≤ 1 phút |

## 5. Wireframe màn hình chính (UIUX §6)

- **6.1 Trang chủ CEO (desktop):** Briefing ngoại lệ, việc chờ quyết, panel AI phải.
- **6.2 Review tài liệu (Reviewer, desktop):** tài liệu gốc trái + form phải, màu theo confidence, bàn phím hoàn toàn (khớp FR-DC-19/20).
- **6.3 Mobile (390px):** chụp chứng từ, check-in, hỏi AI, duyệt nhanh.

## 6. Mẫu tương tác AI theo Autonomy (UIUX §7.1) — cố định ở mọi module

| Mức | Mẫu giao diện | Người dùng |
|---|---|---|
| L0 Thông tin | **Insight card** (1 câu + số + nguồn) | Không |
| L1 Gợi ý | **Suggestion chip** (1–3 phương án) | Chọn/bỏ qua |
| L2 Soạn & chờ | **Action card** viền `ai`, "AI soạn · chờ xác nhận", xem trước, Xác nhận/Sửa | Xác nhận, sửa từng dòng |
| L3 Làm rồi báo | **Undo toast 10s** → feed "AI đã làm", Hoàn tác **24h** | Không (trừ khi hoàn tác) |
| L4 Tự chủ | **Báo cáo hoạt động** tuần, lọc & hoàn tác theo lô | Đọc tổng hợp |

Nhãn trạng thái một từ vựng ("AI gợi ý"/"AI soạn"/"AI đã làm"); màu `ai` chỉ cho nội dung AI.

### 6.1. Bộ thành phần AI (UIUX §7.2)
Thanh AI toàn cục (⌘K) · Panel AI ngữ cảnh ("AI đang xem: …") · Trạng thái đang nghĩ (bước thật + streaming + Dừng) · Source chip · Nhãn độ tin cậy (Cao/TB/Thấp — % chỉ ở Review) · Nhãn độ tươi ("cập nhật 06:45") · Feed "AI đã làm" · Phản hồi 👍/👎 + "Sai ở đâu?" · Kill switch banner.

### 6.2. Khi AI sai/không biết (UIUX §7.3)
"Tôi chưa có dữ liệu về X" + cách bổ sung (không bịa) · nguồn mâu thuẫn → hiện cả hai, hỏi người chọn, ghi DataLineage · lỗi AI không chặn thao tác tay (P10).

## 7. Design system (UIUX §8)

- **Font:** Be Vietnam Pro (UI) + JetBrains Mono (số/mã); dự phòng Inter. Cỡ 12/14/16/20/24/32 (14 Gọn, 16 Thoáng, line-height 1,5). Số tabular. Lưới 4px. Bo góc 4/8/16/tròn. 3 mức bóng. Chuyển động 150/250ms, tôn trọng reduce-motion.
- **Màu ngữ nghĩa:** `primary` · **`ai`** (nội dung AI, khác hẳn primary) · `success/warning/danger` · `info` · `neutral-0…900` · `stale`. Màu trạng thái luôn kèm chữ/biểu tượng (● ◐ ○, ↑ ↓); kiểm mù màu.
- **Thành phần:** Cơ bản / Dữ liệu (bảng sửa trực tiếp, thẻ chỉ số, sparkline, heatmap workload, Gantt, cây mục tiêu) / AI / Nhập liệu (vùng thả file toàn cục, thẻ tiến trình, trình xem tài liệu có vùng tô, camera, ghi âm) / Điều hướng. Đề xuất shadcn/ui trên Radix; tự làm nhóm AI + Nhập liệu.
- **Trực quan hóa:** tiêu đề biểu đồ là kết luận; luôn có đường kế hoạch; ưu tiên cột/đường; đơn vị VN (1,2 tỷ; 450 tr; 12,5%); mọi điểm dữ liệu bấm được.

## 8. Đa thiết bị, truy cập, bản địa hóa (UIUX §9)

- Breakpoint: ≥1440 (sidebar + panel AI cố định) · desktop · tablet · **mobile 390px** (PWA: chụp/check-in/hỏi/duyệt).
- **WCAG 2.1 AA** cho màn hình chính (NFR-UX-03).
- **VI mặc định + EN**; AI hiểu câu trộn 2 ngôn ngữ (NFR-UX-01).

> **Khác `main`:** `main` có SCR-01..28 cụ thể cho 5 trụ F.O.C.U.S. AI-EOS dùng IA 8 mục theo vai trò. Theo R-DEC-10 (ID theo BRD + bảng ánh xạ sang SCR-* của `main`); mã `SCR-*` cho AI-EOS gán khi chi tiết hóa ở đợt code (R-DEC-09).

## 9. Open questions
- OQ-06-01: Màu thương hiệu `primary` cụ thể (UIUX §10 bỏ ngỏ) — chờ human/design.
- OQ-06-02: ⌘K + Panel + Chat SSE của `main` làm hiện thực cho "Thanh AI toàn cục" — ĐÃ CHỐT: giữ làm chuẩn hiện thực; chi tiết UI gán khi chi tiết hóa ở đợt code (R-DEC-09).
- OQ-06-03: SCR numbering — ĐÃ CHỐT: R-DEC-10 — đánh số theo BRD + bảng ánh xạ sang SCR-01..28 của `main`; SCR-* cụ thể gán ở đợt code (R-DEC-09).

## Version
- **Version:** 0.2.0 (draft, Phase R2)
- **Last updated:** 2026-10-22
- **Maintainer:** @CyEyes
- **Change 0.2.0:** Chốt Q1–Q6 (R-DEC-05..10) — cập nhật trạng thái quyết định, đóng OQ liên quan; phạm vi docs-first P0.
- **Change 0.1.0:** Viết lại 06 theo AI-EOS UI/UX — 8 nguyên tắc UX, IA 8 mục theo vai trò, 5 flow F1–F5, wireframe CEO/Review/Mobile, mẫu AI theo Autonomy L0–L4 + bộ component AI, design system (token/màu/thành phần/trực quan hóa), đa thiết bị + WCAG 2.1 AA + VI/EN.
