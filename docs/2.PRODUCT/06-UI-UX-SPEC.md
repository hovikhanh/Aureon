# 06 — UI/UX Spec (Aureon v3 — AI-EOS)

> **Nguồn chuẩn:** `_reference/SOURCE-UIUX.md` (AI-EOS UI/UX v1.0) + `SOURCE-BRD-v1.1.md` §11.6/§12.
> **Phụ thuộc:** 00, 01, 02, 03. **Trạng thái:** ✅ current — Aureon v3 (AI-EOS) CHÍNH THỨC. **Ngày:** 2026-10-23 · **Maintainer:** @CyEyes
> **Ghi chú:** Tách từ Aureon v2.1 (nay archived ở `docs/_archive/v2.1/`).

---

## 1. Persona thiết kế (UIUX §2.1)

Năm persona (UIUX §2.1), xây từ BRD 7 vai trò (ROLE-*, skeleton §5). Cảm nhận sản phẩm do **CEO** quyết; mức độ sử dụng thực tế do **Employee** và **Reviewer** quyết (UIUX §2.3). Thiết kế phải phục vụ cả hai cực: lãnh đạo cần tối giản, Reviewer cần mật độ cao.

| Persona | Role (skeleton §5) | Mục tiêu khi mở app | Thiết bị / nhịp dùng | Nỗi đau → nhu cầu UX | US then chốt (P0) |
|---|---|---|---|---|---|
| **CEO** — "Biết ngay, quyết nhanh" | ROLE-CEO | Biết công ty có ổn không, gì cần mình, giao việc | Mobile buổi sáng + giữa họp; desktop khi chuẩn bị HĐQT; 1–5 phút/lần | Phải hỏi từng người, số vênh nhau → **ngoại lệ trước, 1 câu tóm tắt, con số có nguồn** | US-CEO-001..008, US-KPI-007, US-OKR-005, US-STR-003 |
| **Director / Manager** — "Giữ team đúng hướng" | ROLE-DIR, ROLE-MGR | Theo dõi KPI/OKR, workload, duyệt việc, chuẩn bị báo cáo lên trên | Desktop chính; mobile để duyệt; 15–60 phút/ngày | Tốn công tổng hợp, không thấy ai quá tải → **briefing đơn vị, heatmap workload, hàng chờ duyệt** | US-TASK-001..004, US-KPI-002..006, US-OKR-007, US-MTG-002 |
| **Employee** — "Làm việc, ít khai báo" | ROLE-EMP | Biết hôm nay làm gì, cập nhật tiến độ, gửi chứng từ | Mobile + desktop xen kẽ; vài phút | Nhập lặp lại, báo cáo nhiều nơi → **check-in ≤30s, gửi file ≤3 chạm, nhập một lần** | US-TASK-002, US-OKR-006, US-DC-001..003, US-DC-009 |
| **Reviewer** (kế toán, thư ký) — "Duyệt nhanh, không sai" | ROLE-REV | Xử lý hàng chờ tài liệu AI trích xuất | Desktop lớn, bàn phím; nhiều giờ/ngày cao điểm | Nhập tay từ giấy, sợ sai số tiền → **chế độ Gọn, phím tắt, liên kết trường↔vùng gốc** | US-DC-006, US-DC-007, US-DC-010 |
| **Admin** — "Cấu hình an toàn" | ROLE-ADM | Thiết lập tổ chức, quyền, AI policy, schema tài liệu | Desktop; theo đợt | Sợ AI vượt quyền, khó kiểm quyền → **ma trận quyền, "xem như người dùng", AI Control Center + kill switch** | US-ORG-002..004, US-AI-004..008, US-DC-008 |

**ROLE-AI (AI Agent, skeleton §5)** không có persona người nhưng hiện diện khắp UI dưới dạng **nội dung do AI tạo** (màu `ai`, nhãn trạng thái, feed "AI đã làm"); mọi hành động của agent tuân Autonomy L0–L3 (§6) và quyền giao = agent ∩ người (P06/P08).

**Phát hiện dẫn dắt thiết kế (UIUX §2.3):** (1) CEO dùng nhịp ngắn → màn đầu trả lời "có gì cần tôi?" không cần cuộn/bấm. (2) Niềm tin quyết định mức dùng → nguồn/độ mới/độ tin cậy luôn hiện nhưng không chiếm chỗ. (3) Employee quyết chất lượng dữ liệu → mọi thao tác nhập ≤10s. (4) Reviewer là "người dùng chuyên nghiệp" → mật độ cao, phím tắt, xử lý hàng loạt. (5) AI làm việc cả khi không ai hỏi → luôn có chỗ cho "AI đã làm" / "AI đề xuất", tách khỏi thông báo thường.

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

Điều hướng theo **việc người dùng muốn làm**, không theo 28 domain kỹ thuật → **gộp 28 domain (D01–D28) vào 8 mục** + Quản trị riêng. Thanh trên cùng là nơi bắt đầu phần lớn tác vụ; sidebar trái dùng khi cần vào sâu một module.

### 3.1. 8 mục điều hướng ↔ domain nguồn (P0)

| Mục | Ý nghĩa người dùng | Domain P0 phủ |
|---|---|---|
| **Trang chủ** | Ngoại lệ, việc cần quyết, briefing theo vai trò | D27 CEO Assistant, D28 Reporting, D05 Notification |
| **Hỏi AI** | Hỏi tự nhiên, phân tích, mô phỏng, ra lệnh | D26 AI Platform, D27 |
| **Mục tiêu** | Chiến lược, OKR, KPI theo cây alignment | D07 Strategy, D08 KPI, D09 OKR, D10 Performance |
| **Công việc** | Task, workload, dự án | D11 Task/Workload |
| **Họp & lịch** | Cuộc họp, biên bản → việc, lịch | D12 Meeting, D13 Calendar |
| **Dữ liệu** | Gửi/duyệt tài liệu, Hộp thư dữ liệu, Review | D03 Data Capture & IDP, D14 Knowledge |
| **Kinh doanh** | Finance Lite, Sales Lite, HR cơ bản | D15 Finance, D16 HR, D17 Sales |
| **Tri thức / báo cáo** | Tài liệu, báo cáo, decision log | D14 Knowledge, D28 Reporting |
| **Quản trị** (riêng) | Tổ chức, quyền, AI policy, audit | D01 Organization, D02 Admin & Security, D26 (AI Control Center) |

### 3.2. Hiển thị theo vai trò (UIUX §4.1) — mỗi mục đổi nội dung theo role

| Mục | CEO | Director / Manager | Employee | Reviewer | Admin |
|---|---|---|---|---|---|
| Trang chủ | Briefing công ty, việc chờ quyết | Briefing đơn vị, hàng chờ duyệt | Việc hôm nay, mục tiêu của tôi | Hàng chờ review, SLA | Tình trạng hệ thống, sự cố AI |
| Hỏi AI | Toàn công ty | Trong đơn vị | Dữ liệu của tôi/team | Tài liệu được phân | Cấu hình, audit |
| Mục tiêu | Toàn bộ | Đơn vị + cấp dưới | Của tôi, xem mục tiêu cha | — | — |
| Công việc | Tổng quan thực thi | Team, workload | Task của tôi | — | — |
| Dữ liệu | Xem tài liệu gốc | Duyệt của đơn vị | Gửi lên, theo dõi | Toàn bộ hàng chờ được phân | Schema, ngưỡng |
| Kinh doanh | Toàn bộ | Theo quyền | Theo quyền | Theo quyền | — |
| Tri thức / báo cáo | Có | Có | Tri thức | Tri thức | Audit |

### 3.3. Quy tắc điều hướng

- **Default-deny hiển thị:** mục/trụ ngoài quyền **ẩn hẳn** (không hiện rồi báo lỗi); khớp data-scoping 02 §5. Trường mức nhạy cảm (lương, CCCD…) ngoài quyền trả `{ masked: true }`, không để trống gây hiểu lầm.
- Người nhiều vai trò (vd Director kiêm Reviewer) **đổi ngữ cảnh** ở thanh trên; Trang chủ và nội dung 8 mục đổi theo (P06).
- **Breadcrumb nghiệp vụ** luôn theo chuỗi: Chiến lược › Objective › KR › Dự án › Task — để người dùng thấy việc mình làm đóng góp vào đâu (P06 Traceability).
- **Bố cục trang chi tiết thống nhất** cho mọi entity: tiêu đề + trạng thái, chỉ số chính, tab (Tổng quan / Liên kết / Lịch sử / Tài liệu gốc / Hoạt động AI), panel AI bên phải. Tab "Tài liệu gốc" và "Hoạt động AI" hiện thực hóa P06 (lineage) và P07 (explainable AI).

### 3.4. Route, `SCR-*` và chuyển tiếp từ v2.1 (R-DEC-25, chốt ở Spec lock M1.1)

**Quy ước số:** màn hình còn dùng tiếp từ v2.1 **giữ `SCR-*` cũ** (để comment/test trong code không đổi nghĩa); màn hình mới của v3 đánh từ **`SCR-40`** trở đi. Locale theo cookie `NEXT_LOCALE` (không có segment `[locale]` trong URL). Route v2.1 → **redirect 308** sang route v3 trong `middleware.ts`.

| SCR | Route v3 | Mục IA (§3.1) | Role thấy | Phase xây đầy đủ | Route v2.1 (redirect 308) |
|---|---|---|---|---|---|
| SCR-13 | `/login` | — | public | có sẵn | (giữ) |
| SCR-40 | `/home` | Trang chủ — Executive / Department / Employee / Reviewer / Admin theo role | mọi role | M2.1 (M1.1: khung + dashboard v2.1 tạm cho CEO/DIR) | `/dashboard` |
| SCR-03 | `/home/pillar/[slug]` | Trang chủ — bố cục 5 trụ **tùy chọn** (R-DEC-16) | CEO, DIR | có sẵn (lite) | `/dashboard/pillar/[slug]` |
| SCR-16 | `/ask` | Hỏi AI | mọi role trừ AI actor | M2.4 | `/ai` |
| SCR-41 | `/goals` | Mục tiêu — cây alignment Strategy → StrategicObjective → {KPI \| Objective → KR} + Initiative → Project | CEO, DIR, MGR, EMP | M1.4 | — |
| SCR-42 | `/work` | Công việc — **Task của tôi** (tab mặc định) + **Kanban nhóm** (tab, `?view=board`) | CEO, DIR, MGR, EMP | M1.3 | — |
| SCR-43 | `/work/approvals` | Công việc — hộp chờ duyệt | CEO, DIR, MGR | M1.3 | `/approvals` |
| SCR-44 | `/meetings` | Họp & lịch | CEO, DIR, MGR, EMP | M2.3 / M3.1 | — |
| SCR-45 | `/data` | Dữ liệu — Hộp thư dữ liệu (**sửa**: từ khung `ComingSoon` → đầy đủ) | CEO, DIR, MGR, EMP, REV (ADM: chỉ link schema) | M1.5 | — |
| SCR-18a | `/data/review` | Dữ liệu — hàng chờ review (**giữ**, thêm lọc `APPROVED`) | REV, DIR, MGR (CEO không có `idp:approve` → ẩn mục) | có sẵn | `/idp/review` |
| SCR-18b | `/data/review/[documentId]` | Dữ liệu — review chi tiết (**sửa**: lưới dòng + `planned_actions`) | REV, DIR, MGR | có sẵn | `/idp/review/[documentId]` |
| SCR-46 | `/business` | Kinh doanh (Finance/Sales/HR Lite) | theo quyền domain | M2.2 | — |
| SCR-47 | `/business/finance/invoices` | Kinh doanh — hóa đơn | quyền `finance:read` | có sẵn (lite) | `/finance/invoices` |
| SCR-48 | `/business/hr/employees` | Kinh doanh — nhân sự | quyền `hr:read` | có sẵn (lite) | `/hr/employees` |
| SCR-49 | `/knowledge` | Tri thức / báo cáo | mọi role (Admin: audit) | M3.3 / M3.4 | — |
| SCR-50 | `/admin` | Quản trị — tổng quan | ADM (CEO xem) | M1.2 | — |
| SCR-14 | `/admin/audit` | Quản trị — audit log (M1.2: thêm lọc `from`/`to`/`actor_type`, EP-ADM-12) | ADM | có sẵn (lite) → M1.2 | (giữ) |
| SCR-51 | `/admin/org` | Quản trị — cơ cấu tổ chức (cây + panel + mốc `as_of`) | ADM, CEO, DIR khối O (sửa); MGR không thấy mục | M1.2 | — |
| SCR-52 | `/admin/positions` | Quản trị — vị trí / định biên | ADM, CEO, DIR khối O | M1.2 | — |
| SCR-53 | `/admin/users` | Quản trị — người dùng & phân quyền | ADM (CEO xem) | M1.2 | — |
| SCR-54 | `/admin/roles` | Quản trị — ma trận vai trò × quyền (chỉ đọc) | ADM (CEO xem) | M1.2 | — |
| SCR-55 | `/work/projects` | Công việc — danh sách dự án (cờ trễ) | CEO, DIR, MGR, EMP (EMP: dự án có task của mình) | M1.3 | — |
| SCR-56 | `/work/projects/[id]` | Công việc — chi tiết dự án (milestone, task) | CEO, DIR, MGR, EMP (trong scope) | M1.3 | — |
| SCR-57 | `/work/workload` | Công việc — heatmap workload người × tuần | CEO, DIR, MGR (`execution:query`) | M1.3 | — |
| SCR-58 | `/goals/kpis/[id]` | Mục tiêu — chi tiết KPI | CEO, DIR, MGR, EMP (KPI trong scope) | M1.4 | — |
| SCR-59 | `/goals/objectives/[id]` | Mục tiêu — chi tiết Objective (OKR) | CEO, DIR, MGR, EMP (trong scope) | M1.4 | — |
| SCR-60 | `/goals/check-ins` | Mục tiêu — check-in (F4 cho EMP; tổng hợp team cho MGR/DIR/CEO) | CEO, DIR, MGR, EMP | M1.4 | — |
| SCR-61 | `/data/new/[documentType]` | Dữ liệu — nhập tay C1 (form sinh từ schema) | CEO, DIR, MGR, EMP, REV | M1.5 | — |
| SCR-62 | `/data/imports/[batchId]` | Dữ liệu — import Excel C5 (preview, map cột, lỗi dòng, xác nhận) | CEO, DIR, MGR, EMP, REV | M1.5 | — |
| SCR-63 | `/admin/data-capture` | Quản trị — loại tài liệu, ExtractionSchema, ValidationRule | ADM | M1.5 | — |
| SCR-64 | `/admin/ai` | Quản trị — **AI Control Center** (tab Tổng quan · Agent · Autonomy · Tool Registry) | ADM, CEO (`ai:admin`) | M1.6 | — |
| SCR-65 | `/admin/ai/logs` | Quản trị — AI Control Center: audit tool call / model call + chi phí | ADM, CEO (`ai:admin`) | M1.6 | — |
| SCR-66 | `/admin/onboarding` | Quản trị — Wizard Onboarding UC-07 | ADM, CEO (`platform:admin`) | M1.6 | — |
| — | `/403` | Không có quyền | — | có sẵn | (giữ) |

- **SCR-13 `/login` (T-610c, R-DEC-28):** form email + mật khẩu; khi `DEMO_MODE=true` có **một dropdown** (native `select`) liệt kê 10 tài khoản demo (`DEMO_ACCOUNTS`: đủ 7 role, DIR 4 khối F/O/C/U), nhãn `<tên role i18n> — <email>` (+ khối cho DIR). Chọn một dòng → FE gọi Route Handler `POST /api/demo-credentials` (body `{email}`) → điền **cả** ô email và ô mật khẩu (giá trị thật, thấy được, sửa được); **không tự submit** — người dùng tự bấm "Đăng nhập" (submit `demo: "false"`). Route tắt/không có mật khẩu → chỉ điền email, ô mật khẩu trống + gợi ý `auth.demoPasswordMissing`. Ô mật khẩu có **nút con mắt** (Eye/EyeOff, `type="button"`) đổi `password`↔`text`, `aria-label` `auth.showPassword`/`auth.hidePassword`, `aria-pressed`, dùng được bằng bàn phím, vùng chạm ≥ 44 px (§8.2), áp cả khi tự gõ. HTML `/login` không chứa mật khẩu; không dùng `NEXT_PUBLIC_*` cho mật khẩu.
- Mục chưa xây (phase sau) hiện trạng thái **"Sắp có"** trong khung trang, không ẩn khỏi IA của role được thấy.
- Sidebar lọc theo cột "Role thấy" + permission (default-deny §3.3); product/risk **không** có mục riêng (R-DEC-16).
- Màn hình mới của phase sau (VD `/goals/kpis/[id]`) được cấp `SCR-5x+` ở bước Spec lock của phase đó và thêm vào bảng này.
- **Trang con Quản trị = SCR riêng (M1.2, R-DEC-37 đề xuất):** theo tiền lệ SCR-14 `/admin/audit` và SCR-43 `/work/approvals` (route con có SCR riêng, không là tab của SCR cha) → SCR-51..54; SCR-50 `/admin` là trang tổng quan + điều hướng tới các trang con (thẻ: Tổ chức, Vị trí, Người dùng, Vai trò, Audit, lọc theo quyền). Mỗi trang con là URL riêng (deep-link, test E2E, breadcrumb Quản trị › …).
- **SCR-51 `/admin/org`:** trái = cây Organization → Department (theo `parent_id`) → Team → Employee (EP-ORG-24, headcount mỗi nút); trên = bộ chọn ngày `as_of` (mặc định hôm nay; ngày quá khứ → cây chỉ đọc + nhãn "Cơ cấu tại dd/MM/yyyy"); phải = panel chi tiết nút chọn (thông tin, trưởng đơn vị, lịch sử phân công EP-ORG-21) + hành động: thêm/sửa/archive phòng ban/team (EP-ORG-07..15), gán/chuyển nhân viên với "hiệu lực từ" (EP-ORG-22). Archive cần hộp xác nhận nêu lý do bị chặn (`details.reason`). Không hiển thị field mức 3–4. DIR ngoài khối O, MGR, EMP: mục ẩn khỏi Sidebar; vào URL trực tiếp → `/403`.
- **SCR-52 `/admin/positions`:** bảng vị trí lọc theo phòng ban (EP-ORG-16) — cột mã, chức danh, cấp, định biên, đang có, **trống** (FR-ORG-06); form tạo/sửa (rhf + zod).
- **SCR-53 `/admin/users`:** bảng người dùng (EP-ADM-05) lọc role/trạng thái/phòng ban/tìm kiếm; form tạo (email, họ tên, role, `scope_pillars` chỉ hiện khi role = DIR, phòng ban, liên kết nhân viên, mật khẩu ban đầu kèm con mắt §8.2) và sửa (EP-ADM-06/08); nút **Khóa / Mở khóa** có xác nhận + lý do (EP-ADM-09/10) — toast nêu "phiên đăng nhập của người này đã bị thu hồi". Không cho tự khóa/tự đổi role chính mình (nút disabled + tooltip). CEO xem chỉ đọc.
- **SCR-54 `/admin/roles`:** ma trận 7 role × permission `<domain>:<action>` (EP-ADM-11) dạng lưới ✓/—, kèm ghi chú scope (`d/o/p/r/s/…`); chỉ đọc ở P0 (vai trò tùy biến — backlog).
- **Chuông thông báo (Header, mọi role trừ AI actor — không phải SCR):** icon chuông + badge `meta.unread_count` (ẩn khi 0, "99+" khi > 99); poll EP-NTF-01 `unread_only=true&limit=10` mỗi 60 giây và khi focus cửa sổ (không SSE ở P0); mở popover danh sách 10 mới nhất (tiêu đề, thời gian tương đối, chấm chưa đọc), bấm một mục → EP-NTF-02 + điều hướng `link`; nút "Đánh dấu đã đọc tất cả" (EP-NTF-03); liên kết "Cài đặt email" mở dialog tùy chọn theo loại (EP-NTF-04/05). `aria-label` có số chưa đọc, `aria-live="polite"` khi số tăng, điều khiển bằng bàn phím (§8.2).
- **Spec lock M1.3 (đề xuất, chờ human duyệt):**
  - **Kanban là tab của SCR-42, không phải SCR riêng (R-DEC-48):** cùng nguồn EP-TASK-01, khác cách trình bày; trang con có URL riêng (SCR-55..57) theo tiền lệ R-DEC-37. Thanh tab trong `/work`: Task của tôi · Nhóm (ẩn với EMP) · Dự án · Workload (ẩn nếu thiếu `execution:query`) · Phê duyệt (ẩn nếu thiếu `platform:approve`, badge `meta.pending_count`).
  - **SCR-42 "Task của tôi":** EP-TASK-01 `mine=true`; nhóm theo hạn: **Quá hạn** (đỏ, `overdue=true`) · Hôm nay · Tuần này · Sau đó · Không hạn; lọc trạng thái (multi-select 7 trạng thái DEC-147, mặc định ẩn `done/cancelled`) + khoảng hạn (`due_from/due_to`) — lọc phản ánh lên query string (deep-link). Mỗi dòng: tiêu đề, dự án (link SCR-56), hạn `dd/MM/yyyy`, ưu tiên, chip nguồn (`source_ref.kind`: Họp/AI/Tài liệu → link tới nguồn, P06), số sub-task, biểu tượng "bị chặn bởi N task". Đổi trạng thái tại chỗ (menu theo `TRANSITIONS`; `blocked` mở ô lý do bắt buộc; `done` bị chặn dependency → toast nêu task chặn). Panel chi tiết (`?task=<id>`): sửa field (rhf + zod), sub-task, dependency (thêm/bỏ — EP-TASK-06..08), lịch sử (audit). EMP có nút "Đề nghị chuyển người" (EP-TASK-19) thay vì sửa người nhận.
  - **SCR-42 tab "Nhóm" (kanban):** MGR/DIR/CEO; cột = `backlog, todo, in_progress, blocked, in_review, done` (`cancelled` ẩn, bật bằng toggle); lọc phòng ban (MGR ghim phòng mình), người nhận, dự án. Kéo thả thẻ = PATCH `status` + `version` (sai luật → thẻ bật về + toast lỗi i18n theo `error.code`; `409` → tải lại thẻ). Có hỗ trợ bàn phím (nút "Chuyển sang…" trên thẻ — WCAG AA, không chỉ kéo thả). Nút "Giao việc" mở form tạo task (người nhận chọn từ thành viên phòng — EP-ORG-24 `members[]`). Cột hiển thị tối đa 50 thẻ + "Xem thêm".
  - **SCR-55 `/work/projects`:** bảng: mã, tên, phòng ban, trạng thái, tiến độ (`progress_pct` thanh) vs kế hoạch (`planned_pct` vạch), **cờ "Trễ"** khi `late` (chênh > 10 điểm, 03 §4), số task quá hạn, hạn kết thúc; lọc `late=true`, trạng thái, phòng ban. Tạo dự án (MGR+). Số click được → SCR-56 (P01).
  - **SCR-56 `/work/projects/[id]`:** bố cục chi tiết thống nhất §3.3: tiêu đề + trạng thái + cờ trễ; chỉ số chính (tiến độ, kế hoạch, task theo trạng thái, quá hạn); tab **Tổng quan** (timeline milestone: chấm theo `due_date`, `late` đỏ, `done` xanh; thêm/sửa milestone EP-TASK-15/16), **Task** (danh sách EP-TASK-01 `project_id`), **Lịch sử**. Breadcrumb Công việc › Dự án › <mã>.
  - **SCR-57 `/work/workload`:** heatmap hàng = người, cột = tuần ISO (mặc định 4 tuần tới `week` hiện tại, chọn tuần/số tuần), ô = `load_pct` (thang màu: ≤ 80 nhạt, 80–110 vừa, > 110 cam/đỏ; giá trị hiển thị `112,5%`); cột cuối **"Quá tải"** badge khi `overloaded` (> 110% hai tuần liên tiếp, ngưỡng từ response `threshold_pct` — không hard-code); dòng tóm tắt `overloaded_count` / `people` (`overloaded_pct` khớp METRIC-HR-03, click → lineage metric). Sắp người quá tải lên đầu. Bấm ô → danh sách task mở của người đó trong tuần (EP-TASK-01 `assignee_id` + `due_from/due_to`) — điểm vào F5 (§4.5). Tên người ghép từ EP-ORG-24; không có quyền đọc cơ cấu → hiện mã NV.
  - **SCR-43 `/work/approvals`:** danh sách EP-WF-01 `assigned_to=me`: loại (rule, i18n), tiêu đề theo `title_key`+`params`, người yêu cầu, số tiền (nếu có, `1,2 tỷ`), hạn `due_at` (quá hạn đỏ), bước 1/2; lọc trạng thái (mặc định Chờ duyệt) + loại. Panel chi tiết (EP-WF-02): `payload_diff` (trước/sau), timeline bước; nút **Duyệt** / **Từ chối** (từ chối bắt buộc lý do) → EP-WF-03 với `Idempotency-Key`; `409` → banner "Yêu cầu đã được xử lý/hết hạn" + tải lại. Mobile: thẻ dọc, nút cố định đáy (persona DIR/MGR "mobile để duyệt").
  - Mọi chuỗi qua `next-intl` (vi/en, nhóm khóa `work.*`, `approvals.*`); trạng thái trống/lỗi từng widget riêng (FR-DSH-07).
- **Spec lock M1.4 (đề xuất, chờ human duyệt):**
  - **SCR-41 `/goals`:** thanh trên = chọn Strategy (mặc định `active`) + kỳ OKR (mặc định quý hiện tại) + lọc phòng ban (CEO/DIR) + bộ lọc nhanh "Chỉ mục at-risk / dưới ngưỡng". Thân = cây thu gọn được (EP-STR-01): Strategy → StrategicObjective (badge pillar, `progress_pct`) → 3 nhóm con **KPI** (chip band màu CRITICAL/BELOW/NEAR/MEETS/EXCEEDS + `achievement_pct` kỳ gần nhất, KPI con lồng) · **OKR** (Objective → KR với thanh progress, `ConfidenceBadge`, cờ "At risk" đỏ) · **Initiative** (progress, nhãn "Đúng tiến độ/Trễ" theo quy tắc SEI, danh sách Project con là link `/work/projects/{id}` của M1.3). Nhóm "Chưa gắn chiến lược" ở cuối. Node `restricted` hiển thị tên rút gọn, không click (EMP xem mục tiêu cha). Breadcrumb 06 §3.3 "Chiến lược › Objective › KR › Dự án › Task". Mọi số click được tới chi tiết (P01). CEO: nút "Thêm Strategy / Mục tiêu chiến lược"; DIR (khối của mình) thêm SO; MGR/CEO/DIR: "Thêm KPI / Objective / Initiative" theo scope; EMP: chỉ xem + nút "Check-in" trên KR/KPI của mình. Rỗng → trạng thái trống có CTA theo role; lỗi widget chỉ báo tại chỗ.
  - **SCR-58 `/goals/kpis/[id]`:** tiêu đề + owner + phòng ban + direction/unit + liên kết SO/KR/Initiative. Tabs 06 §3.3: **Tổng quan** — thẻ trạng thái ngưỡng kỳ hiện tại (band, achievement, gap so target), đồ thị Recharts actual vs target theo kỳ (EP-KPI-10, đường target theo bản hiệu lực, vạch ngưỡng NEAR/BELOW), bảng target theo kỳ (EP-KPI-08, bản đã đóng hiện "đổi ngày dd/MM/yyyy — lý do"); **Liên kết** — KPI con, task gắn KPI; **Lịch sử** — measurement + check-in (EP-KPI-06/PRF-03, ai/khi nào/nguồn); **Tài liệu gốc** — link `source_document_id` nếu có; **Hoạt động AI** — placeholder (M2.4). Hành động: "Ghi số đo" (form period + giá trị + ghi chú, Idempotency-Key), "Đặt target kỳ" (không EMP). Kỳ khóa → nút disable + tooltip.
  - **SCR-59 `/goals/objectives/[id]`:** Objective (kỳ, level, loại committed/aspirational, progress, SO cha, Objective cha/con). Danh sách KR: baseline → current → target, thanh progress, `ConfidenceBadge`, cờ at-risk kèm lý do (i18n `goals.atRisk.reasons.*`), "check-in gần nhất x ngày trước". Chọn KR (query `?kr=`) → panel lịch sử check-in (EP-PRF-01: giá trị, độ tự tin, ghi chú/blocker/hỗ trợ cần/hành động tiếp) + sparkline KRMeasurement (EP-OKR-11). Initiative đóng góp. Nút "Check-in" (owner KR; MGR/DIR trong scope ghi hộ).
  - **SCR-60 `/goals/check-ins`:** **EMP** — danh sách thẻ F4 (EP-PRF-06) cho KR/KPI của mình đến hạn trước: ô giá trị (số), thanh trượt độ tự tin 3 nấc HIGH/MEDIUM/LOW, ô ghi chú + "Vướng mắc" (một câu; nút micro C2 **ẩn** ở M1.4), Gửi ≤ 30 s (06 §2 F4) → toast + thẻ chuyển "Đã check-in". Vùng "AI điền sẵn" = **placeholder** `prefill: null` (nhãn "AI gợi ý" sẽ có ở M2.4), không gọi AI. **MGR/DIR/CEO** — tab "Của tôi" (như EMP nếu có) + tab "Team" = feed EP-PRF-05 lọc tuần/phòng ban/confidence, đánh dấu người chưa check-in tuần này. Thông báo nhắc thứ Sáu (kind `reminder`) và cảnh báo `execution.okr_at_risk`/`execution.kpi_below_threshold` (kind `alert`) mở link tới SCR-59/SCR-58.
  - **Quyền FE:** mục Sidebar `goals` giữ `anyOf: ["execution:read"]`; nút tạo/sửa ẩn theo role + scope (BE vẫn chặn). Route con thêm vào `lib/permissions.ts` (prefix `/goals`), không thêm mục Sidebar mới.
- **Spec lock M1.5 (đề xuất, chờ human duyệt):**
  - **SCR-45 `/data`:** tab nhóm trạng thái (EP-DC-13 `group`, đếm từ `meta.counts`): Đang xử lý · Cần duyệt · Đã duyệt chờ ghi · Đã ghi · Từ chối · Lỗi/Trùng · Đã hoàn tác; lọc kênh (C1/C3/C5), loại tài liệu, "Của tôi", khoảng ngày, tìm tên file; bảng phân trang 20 dòng. Vùng **kéo thả** (C3) trên đầu (thay `UploadButton`, **sửa** gọi EP-DC-01; chấp nhận `.pdf,.png,.jpg,.jpeg,.webp,.heic,.docx,.xlsx,.csv`; kiểm trước ở client: ≤ 100 file, ≤ 50 MB/file → lỗi inline theo file, không gửi); chọn trước loại tài liệu (tùy chọn). File `.xlsx/.csv` kéo vào có lựa chọn "Import bảng (C5)" → EP-DC-17 → điều hướng SCR-62; mặc định C3. Nút "Nhập tay" → menu loại tài liệu (EP-DC-27, chỉ loại có `permitted`) → SCR-61. Trạng thái đang xử lý tự refetch 5 s tới khi rời nhóm `processing`. Mỗi dòng: hành động "Xem tài liệu gốc" (EP-DC-14, mở `SourceViewer` ở drawer, ẩn với `kind=MANUAL`), "Mở review" (nếu có quyền), "Hoàn tác" khi `can_undo` (dialog lý do + `reason_code`, hiện hạn `undo_deadline` dạng `dd/mm/yyyy HH:mm`), "Lịch sử ghi" (EP-DC-25). Rỗng → empty state + CTA kéo thả. ADM vào → thông báo + link SCR-63.
  - **Toast Undo:** sau commit thành công (EP-DC-08/16/23) hiện `UndoToast` (06 §5.1, 10 s, dừng khi hover/focus) "Đã ghi N bản ghi · Hoàn tác" → EP-DC-24 với `reason_code=mistake`; sau 10 s vẫn hoàn tác được từ SCR-45 trong 7 ngày. Undo `409 CONFLICT_STATE` → dialog liệt kê bản ghi đã sửa sau commit (link tới màn đích).
  - **SCR-61 `/data/new/[documentType]`:** form sinh từ EP-DC-15 (rhf + zod sinh từ `fields[]`: `required`, `value_type` → input date `dd/mm/yyyy` / số VN `1.250.000` / enum select / `master_ref` combobox gọi API đọc của module đích trong scope); nhóm `repeatable_group` → lưới thêm/xóa dòng (FR-DC-04 sửa lưới); trường trọng yếu đánh dấu khiên + chú thích "luôn qua người duyệt"; mức 4 chỉ hiện nếu có quyền. Lỗi `422` map về từng field. Khi `permitted=false` hiện banner "Bạn gửi được, người có quyền sẽ duyệt và ghi". Kết quả: `COMMITTED` → toast Undo + link "Xem bản ghi"; `NEEDS_REVIEW` → toast info + về SCR-45 tab Cần duyệt. Nháp (FR-DC-04) **hoãn M2.3**.
  - **SCR-62 `/data/imports/[batchId]`:** stepper 3 bước. (1) **Map cột**: chọn sheet + dòng tiêu đề; bảng cột Excel → select field (gợi ý AI/heuristic có `ConfidenceBadge`, nhãn "AI gợi ý"), field bắt buộc chưa map tô đỏ; đổi → EP-DC-19. (2) **Xem trước**: tổng/hợp lệ/lỗi; tab Lỗi (EP-DC-20 `invalid`) hiện ô lỗi tô đỏ + message i18n theo `rule_code`; nút "Tải file lỗi" (EP-DC-21). (3) **Xác nhận**: "Gửi N dòng hợp lệ (bỏ M dòng lỗi)" → EP-DC-22 → điều hướng SCR-18b nếu caller có `idp:approve`, ngược lại SCR-45. Rời trang không mất batch (resume qua EP-DC-18).
  - **SCR-18b (sửa):** tài liệu dạng bảng hiện **lưới dòng** (mỗi `row_index` 1 dòng, ô = field, màu confidence, chọn ô → highlight sheet/ô nguồn trong `SourceViewer`); panel "Sẽ ghi" liệt kê `planned_actions` (ACT, số bản ghi, ✓/✗ quyền). Thiếu quyền đích → nút "Duyệt" đổi nhãn "Duyệt (chờ người có quyền ghi)" + gợi ý reassign `to_role_code`. Tài liệu `APPROVED` + caller đủ quyền → nút "Ghi dữ liệu" (EP-DC-23). Trường trọng yếu chưa xác nhận → nút Duyệt disabled + đếm.
  - **"Xem tài liệu gốc" trên bản ghi đích:** component `LineageChip` (mới, `components/ai` cạnh `SourceChip`) gọi EP-DC-26, mở drawer: tên file, loại, trang/sheet/dòng, field, giá trị gốc; `restricted` → "Bạn không có quyền xem nguồn". Gắn ở SCR-51 (panel nhân viên/phòng ban), danh sách task `/work/tasks` (M1.3), KPI/OKR (M1.4) khi `source_document_id` ≠ null.
  - **SCR-63 `/admin/data-capture`:** trái = danh sách doc type (bật/tắt, từ khóa classifier); phải = phiên bản schema (draft/published/retired), editor bảng field (tên, kiểu, bắt buộc, trọng yếu — khóa với tiền/MST, mức nhạy cảm, đích `action.param`, alias header), ngưỡng (không cho nhập dưới 0,95/0,90), danh sách rule (op, severity); "Tạo bản nháp từ bản hiện hành", "Publish" (dialog xác nhận). Chỉ đọc khi `published`.
  - i18n: namespace `capture.*` (VI/EN) cho mọi chuỗi mới; mã `rule_code`/`reason` → key `capture.errors.<code>`.
  - Mock BFF (`API_MODE=mock`): thêm handler `/data-capture/*`, `/lineage/*` trong `mocks/capture.ts` (mới) + `mocks/router.ts` (sửa) để Playwright `mock` chạy.
- **Spec lock M1.6 (đề xuất, chờ human duyệt):**
  - **`lib/permissions.ts`:** thêm sub-route `{ prefix: "/admin/ai", roles: ["ADM","CEO"], anyOf: ["ai:admin"] }` (bao cả `/admin/ai/logs`), `{ prefix: "/admin/onboarding", roles: ["ADM","CEO"], anyOf: ["platform:admin"] }`. SCR-50 `/admin` thêm 2 thẻ "AI Control Center", "Onboarding" (thẻ Onboarding nổi bật khi `status ≠ completed`).
  - **SCR-64 Tổng quan:** thẻ kill switch lớn (trạng thái, chế độ `WRITE_OFF`/`L0`, phạm vi toàn bộ/agent đã chọn, người + thời điểm + lý do đổi gần nhất); nút "Dừng AI khẩn cấp" → dialog xác nhận (chọn chế độ, agent đa chọn hoặc "Tất cả", lý do bắt buộc) → EP-AI-13; tắt cũng cần lý do. Thẻ "Mức tự chủ tối đa: L2 (M1)" chỉ đọc. Thẻ chi phí tháng (EP-AI-15: đã dùng/ngân sách, thanh % — vàng ≥ 80%, đỏ ≥ 100%) + liên kết SCR-65. Thẻ "Hàng chờ AI soạn" = số `ai_actions` `proposed` (EP-AI-07) liên kết danh sách thẻ.
  - **SCR-64 Agent:** bảng 6 agent P0 (tên, mô tả, số tool, mức tối đa, ngân sách/đã dùng, bật/tắt, cờ "đang bị kill switch"); panel sửa (rhf + zod): bật/tắt, `max_autonomy_level` (select L0–L2; L3/L4 hiện disabled kèm tooltip "Mở ở M3"), ngân sách, chọn tool (chỉ tool hợp lệ), lý do bắt buộc → EP-AI-17. `409` → toast "Dữ liệu đã đổi, tải lại".
  - **SCR-64 Autonomy:** ma trận **tool (hàng, chỉ WRITE/EXECUTION) × cột {Mặc định, ghi đè theo agent/role/ngưỡng}**; mỗi ô hiển thị nhãn chuẩn L0 "Chỉ thông tin" · L1 "AI gợi ý" · L2 "AI soạn" (L3 "AI đã làm" chỉ xuất hiện ở mặc định gốc, gạch ngang + "hạ theo trần M1"). Thêm/sửa/xóa dòng ghi đè (EP-AI-18..21) bằng dialog (tool, agent?, role?, ngưỡng tiền `1.250.000 đ`?, level, max_level, lý do); lỗi `422 details.reason` map i18n (`above_ceiling`, `above_tool_max`, `critical_field`, `not_configurable`, `execution_max_l2`).
  - **SCR-64 Tool Registry:** bảng 53 tool đủ **13 metadata** (cột ẩn/hiện được), lọc loại READ/WRITE/APPROVAL/EXECUTION, domain, agent, "chỉ tool tôi dùng được"; badge `P1 — đóng băng` cho tool frozen; dòng mở rộng hiện `input_schema`/`output_schema` (JSON, font mono), tên BRD, `owner`, EP tham chiếu. Chỉ đọc.
  - **SCR-65 Logs:** 2 tab — **Tool call** (EP-AI-22: thời gian, người được phục vụ (tên qua `/platform/users`), agent, tool, loại, trạng thái, mức tự chủ hiệu lực, độ trễ, `request_id` có nút copy; bấm dòng → drawer hiện `arguments` (đã lọc PII), `result_refs` dạng `SourceChip`, liên kết tới thẻ AIAction) và **Model call** (EP-AI-23: provider/model, fallback, token in/out, chi phí USD 4 số lẻ, độ trễ, trạng thái, `prompt_sha256` rút gọn). Lọc khoảng thời gian (mặc định 7 ngày), lọc `request_id` → cùng một `request_id` hiển thị chuỗi model call + tool call + audit (liên kết SCR-14 `?request_id=` — lọc FE theo `metadata.request_id`). Tab **Chi phí**: bảng/biểu đồ Recharts EP-AI-15 theo `provider/model/task_kind/agent/user`. Mỗi bảng một query, lỗi tại chỗ; phân trang 20.
  - **`KillSwitchBanner` (component Shell, không phải SCR):** render trong `AppShell` trên Header cho **mọi role người**; poll EP-AI-12 60 s + khi focus; `enabled=true` → băng màu cảnh báo (không dùng token `ai`) "AI đang tạm dừng ghi dữ liệu — các đề xuất cần bạn xác nhận" (`WRITE_OFF`) / "AI chỉ trả lời, không soạn thao tác" (`L0`), kèm phạm vi agent; ADM/CEO có liên kết "Mở AI Control Center". `role="status"` `aria-live="polite"`; không đóng được khi còn bật. Lỗi tải → không hiển thị (không chặn app).
  - **`ActionCard` (`components/ai/ActionCard.tsx`, 06 §5.1):** hiển thị `suggested_actions[]` trong SCR-16 `/ask` + danh sách hàng chờ ở SCR-64: nhãn level ("AI gợi ý"/"AI soạn"), tên thao tác i18n theo `action_name`, `input_preview` dạng key–value (tiền định dạng P04), nút **Xác nhận** (EP-AI-09, cho sửa trường trước khi xác nhận) / **Từ chối** (EP-AI-10, lý do) — chỉ hiện khi người xem là `on_behalf_of`; L1 chỉ có "Tự làm" (deep link màn hình nghiệp vụ). Sau xác nhận → `UndoToast` 10 s (tạm dừng khi hover/focus) gọi EP-AI-11; ở M1 không có L3 nên không có "AI đã làm" tự động.
  - **SCR-66 Wizard Onboarding** (stepper ngang 6 bước, trạng thái lưu EP-ADM-13/14; tải lại trang tiếp tục đúng bước; **đồng hồ "trong 1 ngày"** góc phải: đếm thời gian từ `started_at`, xanh ≤ 8 h, vàng ≤ 24 h, đỏ > 24 h):
    1. **Thông tin doanh nghiệp** — form `code, name, legal_name, tax_code` → EP-ORG-02 (chưa có org) hoặc EP-ORG-04 → `complete_step company` với `refs.organization_id`.
    2. **Tải sơ đồ tổ chức / DS nhân sự** — tải file mẫu (file tĩnh từ `data/DOC-06*` do T-641 sinh, phục vụ qua FE public asset — không thêm endpoint) hoặc file của DN; upload qua import C5 M1.5 (EP-DC-17..22, doc type #4) → preview map cột (AI gợi ý map, người sửa) → hiện dòng hợp lệ/dòng lỗi + nút tải file lỗi; `refs.org_import_id`.
    3. **Review** — xem trước cây tổ chức sẽ tạo (từ preview import) + danh sách lỗi; xác nhận → commit import (Action Registry M1.5, một transaction, undo 7 ngày) → hiển thị cây thật EP-ORG-24 cạnh nút "Hoàn tác import" (undo M1.5). `complete_step review`.
    4. **Tạo user + role** — bảng từ `members[]` EP-ORG-24 (ADM không đọc hồ sơ NV — R-DEC-30): gợi ý role (trưởng phòng ban → DIR với khối theo phòng hoặc MGR; còn lại EMP), mỗi dòng nhập email + mật khẩu ban đầu (≥ 12 ký tự, có nút sinh ngẫu nhiên hiển thị một lần); tạo tuần tự EP-ADM-06 (mỗi dòng một `Idempotency-Key`, tối đa 30 dòng/lượt, lỗi từng dòng không chặn dòng khác). Bắt buộc ≥ 1 CEO đã tồn tại hoặc được CEO tạo (ADM không cấp CEO — R-DEC-36). `complete_step users` khi ≥ 1 user mới hoặc người dùng chọn "Đủ".
    5. **Import KPI/OKR** (tùy chọn, `skip_step` được) — import C5 doc type #2 (Kế hoạch/OKR/KPI) như bước 2–3; bước này cần `execution:write` → với ADM hiển thị "Bước này do CEO/Director thực hiện" + nút bỏ qua (CEO mở wizard thấy bước đang chờ).
    6. **Xong** — tóm tắt `progress` (số phòng ban/NV/user theo role/KPI/OKR, thời gian), nút "Hoàn tất" → `finish` (lỗi `missing_steps` → đưa về bước thiếu) → liên kết `/home` (dashboard đầu tiên) và `/admin/org`.
  - Mọi chuỗi qua `next-intl` (vi/en); form rhf + zod; desktop ≥ 1280 px không cuộn ngang; stepper điều khiển bằng bàn phím, `aria-current="step"`.

## 4. Luồng người dùng chính (UIUX §5)

Năm luồng F1–F5 bao phủ use case MVP (UC-01/02/03/04/06/07). Mỗi luồng có **mục tiêu số thao tác + thời gian** làm tiêu chí usability (§10). Mô tả bước-bước dưới đây là mức spec sản phẩm; mã màn hình `SCR-*` cụ thể gán ở đợt code (R-DEC-09).

| Flow | Mục tiêu | UC / US nguồn |
|---|---|---|
| F1 CEO buổi sáng: Briefing → giao việc | ≤ 2 phút, ≤ 5 chạm | UC-01, UC-03 |
| F2 Gửi tài liệu → AI trích xuất | gửi ≤ 3 chạm, review ≤ 60s | US-DC-003, US-DC-006 |
| F3 Biên bản họp → việc | ≤ 10 phút kể cả duyệt | UC-02, UC-06 |
| F4 Check-in KPI/OKR nhân viên | ≤ 30s | US-OKR-006 |
| F5 Manager xử lý cảnh báo quá tải | ≤ 1 phút | US-TASK-003/004 |

### 4.1. F1 — CEO buổi sáng: Briefing → giao việc (UC-01, UC-03)

1. **07:00** CEO nhận thông báo (D05) "Briefing sẵn sàng: 2 việc cần anh, 1 rủi ro mới" qua kênh đã chọn (BRD §12.2).
2. Mở **Trang chủ**: 4 ô chỉ số sức khỏe (có nhãn độ tươi), khối **"Cần anh quyết"**, khối **"Rủi ro"**, khối **"AI đã làm"** (nền khác).
3. Chạm thẻ "Doanh thu T9 đạt 82% KH" → **Panel AI** mở: nguyên nhân (Insight 9 phần, skeleton §9), bằng chứng, Source chip (U3/P07).
4. Chọn gợi ý L1 "Phương án 1: CEO tham gia 2 deal lớn" → **Action card** (L2) hiện sẵn task, owner, hạn, lịch; CEO xem trước, sửa từng dòng nếu cần.
5. Bấm **Xác nhận** → Undo toast "Đã tạo 3 task, đặt 2 lịch · Hoàn tác"; quyết định ghi vào **Decision Log** (BRD §12.6, FR-DEC-01).
- **Ngoại lệ:** nếu AI không đủ dữ liệu → thẻ hiện "Tôi chưa có dữ liệu về X" + cách bổ sung, không bịa (§6.2); CEO vẫn giao việc tay được (P10).

### 4.2. F2 — Gửi tài liệu → AI trích xuất (US-DC-003, US-DC-006)

1. **Gửi** (≤3 chạm): thả file vào bất kỳ màn hình nào (vùng thả toàn cục), hoặc Chụp trên mobile (C4), hoặc Import Excel/CSV (C5).
2. Hiện ngay **thẻ tiến trình** ở góc ("Đang đọc 3 file"); người dùng làm việc khác bình thường (xử lý nền).
3. AI phân loại xong → thông báo "2 biên bản họp, 1 báo cáo KPI. 1 cần anh xem lại" (vòng đời tài liệu `UPLOADED→…→NEEDS_REVIEW`, skeleton §8).
4. Mở **Review song song** (mô tả wireframe §5.2): tài liệu gốc trái + trường trích xuất phải; trường vàng/đỏ (confidence TB/Thấp) cần xem; Tab đi qua từng trường; **trường trọng yếu luôn phải đi qua** dù confidence cao (khớp FR-DC-19/20).
5. **Enter** để duyệt → ghi dữ liệu vào domain đích **qua Action Registry** (một transaction/tài liệu, P05/AI-R12); toast có link "Xem bản ghi" + "Hoàn tác" (undo ≥7 ngày IDP).
- **Ngoại lệ:** nguồn mâu thuẫn → hiện cả hai giá trị, hỏi người chọn, ghi DataLineage (P06).

### 4.3. F3 — Biên bản họp → việc (UC-02, UC-06)

1. Chủ trì tải biên bản/transcript vào cuộc họp trên **Họp & lịch** (C3/C4; MVP = từ transcript, không AI dự họp).
2. AI trả tóm tắt 3 khối: **Quyết định · Việc cần làm · Vấn đề mở** (D12).
3. Bảng action item: tên người khớp danh bạ (avatar), hạn quy ra ngày; mục chưa chắc gắn dấu hỏi (confidence Thấp).
4. Chủ trì sửa trực tiếp trong bảng (chế độ Gọn), bấm **"Giao việc"** (L2 Action card xác nhận hàng loạt).
5. Mỗi người nhận task kèm **trích đoạn biên bản gốc** (P06 traceability tới Tài liệu gốc).

### 4.4. F4 — Check-in KPI/OKR nhân viên (US-OKR-006)

1. Thứ Sáu, thông báo "Check-in tuần: 2 KR của bạn" (D05).
2. Mở thẻ check-in: giá trị **AI điền sẵn (L1/L2)** từ dữ liệu tích hợp hoặc task đã xong — người dùng chỉ xác nhận/sửa.
3. Kéo thanh độ tự tin, ghi blocker bằng giọng nói (C2) hoặc một câu.
4. Gửi (≤30s) → Manager thấy trong tổng hợp team (D10 Performance).

### 4.5. F5 — Manager xử lý cảnh báo quá tải (US-TASK-003/004)

1. Trang chủ Manager: cảnh báo "B quá tải 130% trong 2 tuần" (chỉ số Con người §7, ngưỡng >110%).
2. Mở **Workload**: heatmap người × tuần.
3. AI gợi ý **L1** "Chuyển 2 task sang C (50%), C đã làm việc tương tự".
4. Manager kéo-thả hoặc bấm **Áp dụng** → B và C nhận thông báo kèm lý do (hành động ngay tại chỗ, U6).

## 5. Wireframe màn hình chính (UIUX §6)

Mô tả mức mid-fi (bố cục + thứ tự ưu tiên thông tin + hành động), chưa phải màu/thương hiệu. `SCR-*` cụ thể gán ở đợt code (R-DEC-09, OQ-06-03).

### 5.1. Trang chủ CEO (desktop 1440px) — chế độ Thoáng

- **Dòng tóm tắt 1 câu** ngay dưới lời chào, trả lời "có gì cần tôi?" trước mọi con số (U1).
- **4 ô chỉ số sức khỏe**, mỗi ô có nhãn độ tươi ("06:45 hôm nay"); bấm mở nguồn + công thức (U3). Mặc định: doanh thu, dòng tiền, OKR, task trễ — CEO tự chọn trong cài đặt.
- **"Cần anh quyết"** đứng trên "Rủi ro" (việc chỉ CEO làm được); mỗi dòng có tóm tắt AI + nút hành động tại chỗ (U6).
- **"AI đã làm"** nền khác để tách việc AI với việc người (U4), kèm lối hoàn tác (feed L3).
- **Panel AI bên phải** mở theo ngữ cảnh (bấm ô doanh thu → panel giải thích doanh thu); thu gọn được; < 1280px chuyển thành ngăn kéo trượt.

### 5.2. Review tài liệu (desktop, Reviewer) — chế độ Gọn

- **Liên kết hai chiều trường ↔ vùng gốc:** trường đang xem tô cùng màu vùng AI đọc trên tài liệu; bấm vùng gốc nhảy tới trường tương ứng (không phải tự dò).
- **Độ tin cậy 3 mức bằng màu + hình** (● cao ≥90% · ◐ TB 60–89% · ○ thấp <60%) để người mù màu vẫn phân biệt; Admin chỉnh ngưỡng theo loại tài liệu.
- **Con trỏ tự nhảy vào trường cần xem trước** (không theo thứ tự trên-xuống). **Trường trọng yếu (tiền, MST, số tài khoản)** luôn phải đi qua dù confidence cao (khớp FR-DC-19/20, BRD §6).
- **AI nói rõ lý do không chắc** ("ký tự thứ 4 mờ", "ảnh mờ") thay vì chỉ hiện % (P07).
- **Bàn phím hoàn toàn**; duyệt xong tài liệu kế mở ngay. Mục tiêu: hóa đơn 6 trường ≤ 60s (§10).
- **Mỗi lần sửa của Reviewer được ghi lại** để đo độ chính xác AI theo từng trường (P11 Measure Outcomes).

### 5.3. Mobile (390px) — PWA, 4 việc cốt lõi

- **Thanh tab dưới 4 mục + nút + giữa.** Nút + mở nhập nhanh: chụp chứng từ, ghi âm, cập nhật task, check-in. Cấu hình/báo cáo sâu/quản trị chỉ ở desktop.
- **Briefing là trang cuộn ngắn**, đọc hết ≤ 30s; hỏi AI bằng giọng nói ngay Trang chủ (C2).
- **Chụp chứng từ chạy nền:** camera tự nhận cạnh, chụp nhiều trang; người dùng đóng app được; AI báo bằng thông báo khi xong hoặc cần xem lại.
- **Thẻ duyệt đủ để quyết tại chỗ:** AI soạn gì, nguồn từ đâu, 2 nút lớn (vùng chạm ≥ 44px). Vuốt duyệt hàng loạt mục rủi ro thấp; mục tài chính trên ngưỡng phải xác thực sinh trắc học.
- **Chế độ ngoại tuyến:** ảnh chụp + cập nhật task xếp hàng, gửi khi có mạng, nhãn "chưa đồng bộ" (P10). **P0 (R-DEC-25): chưa làm** — PWA P0 cài được (manifest + service worker chỉ cache app shell), mất mạng thì báo "cần kết nối"; hàng đợi ngoại tuyến là backlog. Xác thực sinh trắc học cũng là backlog (OQ-06-04).
- **Giọng nói P0 (R-DEC-22):** chỉ nhập liệu/hỏi AI ngắn, xử lý bằng STT cloud (có thông báo cho người dùng); **không ghi âm cuộc họp** — biên bản họp nhập bằng văn bản hoặc ảnh.

## 6. Mẫu tương tác AI theo Autonomy (UIUX §7.1) — cố định ở mọi module

| Mức | Mẫu giao diện | Người dùng |
|---|---|---|
| L0 Thông tin | **Insight card** (1 câu + số + nguồn) | Không |
| L1 Gợi ý | **Suggestion chip** (1–3 phương án) | Chọn/bỏ qua |
| L2 Soạn & chờ | **Action card** viền `ai`, "AI soạn · chờ xác nhận", xem trước, Xác nhận/Sửa | Xác nhận, sửa từng dòng |
| L3 Làm rồi báo | **Undo toast 10s** → feed "AI đã làm", Hoàn tác **24h** | Không (trừ khi hoàn tác) |
| L4 Tự chủ | **Báo cáo hoạt động** tuần, lọc & hoàn tác theo lô | Đọc tổng hợp |

**Quy tắc cố định ở MỌI module:**
- **P0 chỉ bật L0–L3** (undo ≥24h cho L3; IDP undo ≥7 ngày). **L4 khóa** (phase 5 — skeleton §12bis); UI vẫn định nghĩa mẫu để sẵn sàng.
- Nhãn trạng thái dùng **đúng một từ vựng**: "AI gợi ý" (L1) · "AI soạn" (L2) · "AI đã làm" (L3). Không biến thể.
- Màu `ai` **chỉ** cho nội dung do AI tạo (viền action card, nhãn, panel AI); không dùng cho nút thường (tránh nhầm AI với hành động người).
- **Kill switch (Admin/CEO):** bật → mọi thẻ L3/L4 hạ về **L2** (soạn chờ xác nhận) + băng cảnh báo trên đầu ứng dụng. UI không bao giờ để AI "âm thầm" đổi dữ liệu (U4/P04 Human in the Loop).
- L2 phải cho **sửa từng dòng + xem trước kết quả** trước khi Xác nhận; không có action card nào "xác nhận mù".

### 6.1. Bộ thành phần AI (UIUX §7.2) — đặc tả hành vi

| Thành phần | Hành vi bắt buộc | Nguyên tắc |
|---|---|---|
| **Thanh AI toàn cục (⌘K)** | Vừa tìm kiếm, vừa hỏi, vừa ra lệnh ("giao cho Lan báo cáo tuần"); gợi ý câu hỏi theo màn hình đang mở | U2 Hỏi ở bất kỳ đâu |
| **Panel AI ngữ cảnh** | Mở bên phải, tự nạp ngữ cảnh entity đang xem; hiện "AI đang xem: KPI Doanh thu T9" để người dùng biết phạm vi | P07 |
| **Trạng thái đang nghĩ** | Hiện bước thật ("Đọc 3 báo cáo · So sánh T8 · Kiểm pipeline"), streaming câu trả lời, có nút **Dừng** | P07, không "spinner vô nghĩa" |
| **Source chip** | Mỗi khẳng định có chip nguồn cuối câu; chạm mở popover: bản ghi gốc, tài liệu gốc (nhảy đúng đoạn), thời điểm cập nhật | U3/P06; **mọi số phải có nguồn, không bịa (P05)** |
| **Nhãn độ tin cậy** | 3 mức Cao/TB/Thấp bằng chữ + biểu tượng; **% chỉ ở màn Review**, không dùng % trong câu trả lời hội thoại | U7 |
| **Nhãn độ tươi** | "cập nhật 06:45"; chuyển cảnh báo (token `stale`) khi dữ liệu cũ hơn ngưỡng của chỉ số | BO-02, P11 |
| **Feed "AI đã làm"** | Dòng thời gian mọi hành động L3/L4; lọc theo module/người/mức; mỗi dòng có lý do + nút **Hoàn tác** | U4, undo ≥24h |
| **Phản hồi một chạm** | 👍/👎 + "Sai ở đâu?" trên mọi câu trả lời và mọi bản trích xuất; đi vào AI Control Center | P11, P07 |
| **Kill switch banner** | Băng trên đầu app khi kill switch bật; AI Control Center cho Admin/CEO | P08, P04 |

### 6.2. Khi AI sai hoặc không biết (UIUX §7.3)

- AI nói **"Tôi chưa có dữ liệu về X"** + gợi ý cách bổ sung (kết nối nguồn, tải tài liệu) — **không bịa** (P05); API trả `AI_NO_DATA_AVAILABLE` tương ứng.
- **Nguồn mâu thuẫn:** hiện cả hai giá trị cạnh nhau, hỏi người chọn, ghi vào **DataLineage** (P06).
- **Lỗi hệ thống AI** (timeout, model không phản hồi) **không chặn thao tác tay**: mọi luồng có đường làm tay (P10 Graceful Degradation).

## 7. Design system (UIUX §8)

Xây theo **token** từ đầu để hỗ trợ hai mật độ (Thoáng/Gọn), sáng/tối và đổi thương hiệu. Màu `primary` cụ thể chờ quyết (OQ-06-01).

### 7.1. Token nền tảng

- **Font:** Be Vietnam Pro (UI — thiết kế cho dấu tiếng Việt, không chồng dấu cỡ nhỏ) + JetBrains Mono (số/mã); dự phòng Inter.
- **Cỡ chữ:** 12/14/16/20/24/32 — **14 là thân mặc định chế độ Gọn, 16 cho Thoáng**; line-height 1,5 (dấu tiếng Việt cần khoảng trên).
- **Số:** tabular figures trong bảng và chỉ số (cột số thẳng hàng, dễ so sánh).
- **Khoảng cách:** lưới 4px (4/8/12/16/24/32/48); chế độ Gọn giảm một bậc (hàng bảng 32px thay 44px).
- **Bo góc:** 4 (ô nhập) · 8 (thẻ) · 16 (panel) · tròn (nút, chip). **Độ sâu:** 3 mức bóng (thẻ/menu/hộp thoại); chế độ tối dùng viền thay bóng.
- **Chuyển động:** 150ms (hover) · 250ms (panel); **tôn trọng "giảm chuyển động"** của hệ điều hành (WCAG).

### 7.2. Màu theo ngữ nghĩa

| Token | Ý nghĩa | Dùng cho |
|---|---|---|
| `primary` | Màu thương hiệu (chờ OQ-06-01) | Nút chính, liên kết, mục đang chọn |
| **`ai`** | **Nội dung do AI tạo** | Viền action card, nhãn "AI soạn", panel AI — **khác hẳn `primary`** để không nhầm AI với nút thường |
| `success`/`warning`/`danger` | Đúng kế hoạch / nguy cơ / lệch | Trạng thái KPI, OKR, task, độ tin cậy Cao/TB/Thấp |
| `info` | Trung tính | Thông báo hệ thống |
| `neutral-0…900` | Thang xám 10 bậc | Nền, viền, chữ phụ |
| `stale` | Dữ liệu cũ | Nhãn độ tươi khi quá ngưỡng |

Màu trạng thái **không bao giờ đứng một mình** — luôn kèm chữ/biểu tượng (● ◐ ○, ↑ ↓); xanh lá và đỏ kiểm với các dạng mù màu phổ biến.

### 7.3. Thành phần (5 nhóm)

- **Cơ bản:** nút, ô nhập, chọn, ngày, tiền tệ VNĐ, tab, menu, hộp thoại, toast, avatar, badge.
- **Dữ liệu:** bảng (sắp xếp/lọc/**sửa trực tiếp**/chọn nhiều), thẻ chỉ số, sparkline, heatmap workload, timeline/Gantt, cây mục tiêu (Chiến lược › OKR › Task).
- **AI:** thanh AI, panel AI, insight card, suggestion chip, action card, undo toast, source chip, nhãn độ tin cậy/độ tươi, trạng thái đang nghĩ, feed "AI đã làm", nút phản hồi (§6.1).
- **Nhập liệu:** vùng thả file toàn cục, thẻ tiến trình, trình xem tài liệu có vùng tô, form trường trích xuất, camera, ghi âm.
- **Điều hướng:** sidebar thu gọn, breadcrumb nghiệp vụ, thanh tab mobile, đổi vai trò.

Đề xuất xây trên shadcn/ui + Radix (đã có khả năng truy cập), **tự làm nhóm AI + Nhập liệu**; stack chờ team kỹ thuật xác nhận (OQ-06-02 — ⌘K/Panel/Chat SSE của `main` là chuẩn hiện thực).

### 7.4. Quy tắc trực quan hóa dữ liệu

- **Tiêu đề biểu đồ là kết luận** ("Doanh thu online giảm 18% từ T7"), không phải tên chỉ số.
- Luôn có **đường kế hoạch/mục tiêu**; màu trạng thái chỉ cho phần lệch.
- Ưu tiên cột/đường; tránh pie >4 phần và 3D.
- **Đơn vị rút gọn kiểu Việt:** 1,2 tỷ · 450 tr · 12,5% (định dạng P04).
- Mọi điểm dữ liệu **bấm được** để xem bản ghi gốc và hỏi AI (U3/P05).

## 8. Đa thiết bị, truy cập, bản địa hóa (UIUX §9)

### 8.1. Điểm ngắt màn hình

| Điểm ngắt | Thiết bị | Bố cục |
|---|---|---|
| ≥ 1440px | Màn hình lớn | Sidebar mở + panel AI cố định phải |
| 1280–1439px | Laptop | Sidebar mở, panel AI trượt ra khi cần |
| 768–1279px | Tablet | Sidebar thu thành biểu tượng, panel AI phủ lên nội dung |
| < 768px | Điện thoại | Thanh tab dưới, 4 việc cốt lõi (§5.3); màn khác chỉ đọc |

**MVP = web responsive + PWA** (cài màn hình chính, nhận thông báo, dùng camera), **chưa làm native**; native cân nhắc sau nếu cần sinh trắc học / ngoại tuyến sâu (OQ-06-04).

### 8.2. Khả năng truy cập (WCAG 2.1 AA — NFR-UX-03)

- Tương phản chữ ≥ 4,5:1, thành phần giao diện ≥ 3:1 (kiểm cả sáng và tối).
- **Toàn bộ thao tác dùng được bằng bàn phím**; vòng focus rõ; trang tra phím tắt (phím `?`). Đặc biệt quan trọng cho Reviewer (chế độ Gọn).
- Câu trả lời AI streaming được **thông báo cho screen reader khi hoàn tất**, không đọc từng từ.
- Biểu đồ có **bảng dữ liệu thay thế** + mô tả một câu.
- Vùng chạm ≥ 44×44px trên mobile; **không dựa vào vuốt làm cách duy nhất**.
- **Undo toast** đủ lâu (10s) và **tạm dừng khi hover/focus**.

### 8.3. Ngôn ngữ và định dạng

| Loại | Tiếng Việt (mặc định) | Tiếng Anh |
|---|---|---|
| Tiền | 1.250.000 đ · 1,2 tỷ | VND 1,250,000 · VND 1.2B |
| Ngày | 05/10/2026 · Thứ Hai | Oct 5, 2026 · Mon |
| Phần trăm | 12,5% | 12.5% |
| Xưng hô AI | "anh/chị" theo hồ sơ, mặc định "bạn" | you |

- **VI mặc định + EN**; AI hiểu câu trộn 2 ngôn ngữ, trả lời theo ngôn ngữ người hỏi (NFR-UX-01); giao diện theo cài đặt tài khoản.
- Nhãn VI dài hơn EN 20–30% → nút/cột bảng thiết kế theo bản tiếng Việt.
- Cách AI xưng hô (anh/chị hay bạn) là quyết định văn hóa doanh nghiệp, Admin cấu hình (OQ-06-05).

### 8.4. Chỉ số UX mục tiêu (UIUX §10.1, P11 Measure Outcomes)

| Chỉ số | Mục tiêu MVP |
|---|---|
| Thời gian đến insight đầu (CEO mở app → biết việc cần làm) | ≤ 10s |
| Review một hóa đơn 6 trường | ≤ 60s |
| Hoàn thành 5 luồng F1–F5 không cần hỗ trợ | ≥ 90% |
| Điểm SUS | ≥ 75 |
| Action card L2 được xác nhận không sửa | ≥ 60% và tăng dần |
| Hoàn tác hành động L3 | ≤ 5% |

Hai chỉ số L2/L3 cũng là căn cứ nâng/hạ mức tự chủ của từng loại hành động (feedback loop Autonomy).

> **Khác `main`:** `main` có SCR-01..28 cụ thể cho 5 trụ F.O.C.U.S. AI-EOS dùng IA 8 mục theo vai trò. Theo R-DEC-10 (ID theo BRD + bảng ánh xạ sang SCR-* của `main`); mã `SCR-*` cho AI-EOS gán khi chi tiết hóa ở đợt code (R-DEC-09).

## 9. Open questions
- OQ-06-01: Màu thương hiệu `primary` cụ thể (UIUX §10.3 câu 1) — chờ human/design.
- OQ-06-02: ⌘K + Panel + Chat SSE của `main` làm hiện thực cho "Thanh AI toàn cục" — ĐÃ CHỐT: giữ làm chuẩn hiện thực; chi tiết UI gán khi chi tiết hóa ở đợt code (R-DEC-09).
- OQ-06-03: SCR numbering — ĐÃ CHỐT: R-DEC-10 + R-DEC-25 — giữ `SCR-*` v2.1 cho màn hình dùng tiếp, màn hình mới từ `SCR-40`; bảng ở §3.4, bổ sung theo phase.
- OQ-06-04: Nền tảng MVP — web + PWA như đề xuất, hay cần app native ngay (sinh trắc học/ngoại tuyến sâu)? (UIUX §10.3 câu 2) — chờ human.
- OQ-06-05: Cách AI xưng hô với nhân viên ("anh/chị" hay "bạn") — quyết định văn hóa doanh nghiệp, Admin cấu hình được (UIUX §10.3 câu 5) — chờ human.
- OQ-06-06: Kênh đẩy briefing/duyệt (Zalo/Slack/Teams = C7, P1 backlog) ảnh hưởng thiết kế thông báo (UIUX §10.3 câu 4) — ngoài phạm vi P0; theo dõi ở 13-DECISION-LOG §3.
- OQ-06-07 (M1.3): Kanban là tab `?view=board` của SCR-42 hay SCR riêng — **phương án đề xuất — chọn nếu human duyệt:** tab của SCR-42 (R-DEC-48); trang con dự án/workload có SCR riêng (SCR-55..57).
- OQ-06-08 (M1.4): Vùng "AI điền sẵn" trên thẻ check-in SCR-60 — **phương án đề xuất — chọn nếu human duyệt:** placeholder `prefill: null` ở M1.4, bật ở M2.4.
- OQ-06-09 (M1.6): Wizard UC-07 (SCR-66) có bước nạp SOP/chính sách vào knowledge base — **phương án đề xuất — chọn nếu human duyệt:** không ở M1 (D14 Knowledge ở M3.4), hiển thị "Sắp có".

## Version
- **Version:** 1.1.0 (current)
- **Last updated:** 2026-10-23
- **Maintainer:** @CyEyes
- **Change 1.4.0 (đề xuất — Spec lock M1.3–M1.6, chờ human duyệt):** §3.4 sửa SCR-41/42/43/45/18a/18b; thêm SCR-55 `/work/projects`, SCR-56 `/work/projects/[id]`, SCR-57 `/work/workload` (M1.3, R-DEC-48), SCR-58 `/goals/kpis/[id]`, SCR-59 `/goals/objectives/[id]`, SCR-60 `/goals/check-ins` (M1.4), SCR-61 `/data/new/[documentType]`, SCR-62 `/data/imports/[batchId]`, SCR-63 `/admin/data-capture` (M1.5), SCR-64 `/admin/ai`, SCR-65 `/admin/ai/logs`, SCR-66 `/admin/onboarding` (M1.6, R-DEC-79) + bullet hành vi từng phase. Open questions: thêm OQ-06-07..09.
- **Change 1.3.0 (đề xuất — Spec lock M1.2, R-DEC-37, chờ human duyệt bước S):** §3.4 thêm SCR-51 `/admin/org`, SCR-52 `/admin/positions`, SCR-53 `/admin/users`, SCR-54 `/admin/roles` (trang con Quản trị = SCR riêng theo tiền lệ SCR-14/SCR-43); SCR-14 thêm lọc `from`/`to`/`actor_type`; mô tả hành vi từng màn hình + chuông thông báo ở Header (component, không phải SCR).
- **Change 1.2.0 (đề xuất — T-610c, R-DEC-28):** §3.4 thêm mô tả SCR-13: dropdown 10 tài khoản demo + autofill email/mật khẩu qua Route Handler `/api/demo-credentials` (không tự submit), gợi ý `auth.demoPasswordMissing` khi thiếu mật khẩu, nút con mắt hiện/ẩn mật khẩu (WCAG AA §8.2).
- **Change 1.1.0 (human duyệt 2026-10-23 — Spec lock M1.1, R-DEC-15/16/22/25):** thêm §3.4 bảng route v3 ↔ `SCR-*` ↔ redirect từ route v2.1 (giữ SCR v2.1 cho màn hình dùng tiếp, màn hình mới từ SCR-40); §5.3 ghi rõ P0 không offline/sinh trắc học, giọng nói chỉ nhập liệu ngắn, không ghi âm họp; đóng OQ-06-03.
- **Change 1.0.0 (promote):** Promote tài liệu AI-EOS lên CHÍNH THỨC Aureon v3; di chuyển vào vị trí docs chuẩn; v2.1 archived (docs/_archive/v2.1/).
- **Change 0.3.0:** Mở rộng lên spec-level P0 bám `_reference/SOURCE-UIUX.md` + BRD §12: bảng 5 persona (role/thiết bị/nỗi đau→nhu cầu/US) + 5 phát hiện thiết kế; IA 8 mục ↔ domain P0 + ma trận hiển thị theo vai trò + quy tắc điều hướng (default-deny, breadcrumb, bố cục trang chi tiết); mô tả bước-bước F1–F5 kèm ngoại lệ; wireframe CEO/Review/Mobile dạng text đầy đủ; bảng hành vi bộ component AI + quy tắc Autonomy L0–L3 (L4 khóa) + kill switch + xử lý AI sai/không biết; design system (token/màu/5 nhóm thành phần/trực quan hóa) + WCAG 2.1 AA chi tiết + định dạng VI/EN + chỉ số UX mục tiêu. Bổ sung OQ-06-04/05/06. Giữ nguyên ngữ nghĩa Q1–Q6/R-DEC.
- **Change 0.2.0:** Chốt Q1–Q6 (R-DEC-05..10) — cập nhật trạng thái quyết định, đóng OQ liên quan; phạm vi docs-first P0.
- **Change 0.1.0:** Viết lại 06 theo AI-EOS UI/UX — 8 nguyên tắc UX, IA 8 mục theo vai trò, 5 flow F1–F5, wireframe CEO/Review/Mobile, mẫu AI theo Autonomy L0–L4 + bộ component AI, design system (token/màu/thành phần/trực quan hóa), đa thiết bị + WCAG 2.1 AA + VI/EN.
