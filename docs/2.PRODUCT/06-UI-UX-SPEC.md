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
| SCR-41 | `/goals` | Mục tiêu | CEO, DIR, MGR, EMP | M1.4 | — |
| SCR-42 | `/work` | Công việc | CEO, DIR, MGR, EMP | M1.3 | — |
| SCR-43 | `/work/approvals` | Công việc — hộp chờ duyệt | CEO, DIR, MGR | M1.3 | `/approvals` |
| SCR-44 | `/meetings` | Họp & lịch | CEO, DIR, MGR, EMP | M2.3 / M3.1 | — |
| SCR-45 | `/data` | Dữ liệu — Hộp thư dữ liệu | mọi role trừ AI actor (Admin: schema) | M1.5 | — |
| SCR-18a | `/data/review` | Dữ liệu — hàng chờ review | REV, DIR, MGR, CEO | có sẵn | `/idp/review` |
| SCR-18b | `/data/review/[documentId]` | Dữ liệu — review chi tiết | REV, DIR, MGR, CEO | có sẵn | `/idp/review/[documentId]` |
| SCR-46 | `/business` | Kinh doanh (Finance/Sales/HR Lite) | theo quyền domain | M2.2 | — |
| SCR-47 | `/business/finance/invoices` | Kinh doanh — hóa đơn | quyền `finance:read` | có sẵn (lite) | `/finance/invoices` |
| SCR-48 | `/business/hr/employees` | Kinh doanh — nhân sự | quyền `hr:read` | có sẵn (lite) | `/hr/employees` |
| SCR-49 | `/knowledge` | Tri thức / báo cáo | mọi role (Admin: audit) | M3.3 / M3.4 | — |
| SCR-50 | `/admin` | Quản trị — tổng quan | ADM (CEO xem) | M1.2 | — |
| SCR-14 | `/admin/audit` | Quản trị — audit log | ADM | có sẵn (lite) | (giữ) |
| — | `/403` | Không có quyền | — | có sẵn | (giữ) |

- Mục chưa xây (phase sau) hiện trạng thái **"Sắp có"** trong khung trang, không ẩn khỏi IA của role được thấy.
- Sidebar lọc theo cột "Role thấy" + permission (default-deny §3.3); product/risk **không** có mục riêng (R-DEC-16).
- Màn hình mới của phase sau (VD `/admin/org`, `/goals/kpis/[id]`) được cấp `SCR-5x+` ở bước Spec lock của phase đó và thêm vào bảng này.

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

## Version
- **Version:** 1.1.0 (current)
- **Last updated:** 2026-10-23
- **Maintainer:** @CyEyes
- **Change 1.1.0 (human duyệt 2026-10-23 — Spec lock M1.1, R-DEC-15/16/22/25):** thêm §3.4 bảng route v3 ↔ `SCR-*` ↔ redirect từ route v2.1 (giữ SCR v2.1 cho màn hình dùng tiếp, màn hình mới từ SCR-40); §5.3 ghi rõ P0 không offline/sinh trắc học, giọng nói chỉ nhập liệu ngắn, không ghi âm họp; đóng OQ-06-03.
- **Change 1.0.0 (promote):** Promote tài liệu AI-EOS lên CHÍNH THỨC Aureon v3; di chuyển vào vị trí docs chuẩn; v2.1 archived (docs/_archive/v2.1/).
- **Change 0.3.0:** Mở rộng lên spec-level P0 bám `_reference/SOURCE-UIUX.md` + BRD §12: bảng 5 persona (role/thiết bị/nỗi đau→nhu cầu/US) + 5 phát hiện thiết kế; IA 8 mục ↔ domain P0 + ma trận hiển thị theo vai trò + quy tắc điều hướng (default-deny, breadcrumb, bố cục trang chi tiết); mô tả bước-bước F1–F5 kèm ngoại lệ; wireframe CEO/Review/Mobile dạng text đầy đủ; bảng hành vi bộ component AI + quy tắc Autonomy L0–L3 (L4 khóa) + kill switch + xử lý AI sai/không biết; design system (token/màu/5 nhóm thành phần/trực quan hóa) + WCAG 2.1 AA chi tiết + định dạng VI/EN + chỉ số UX mục tiêu. Bổ sung OQ-06-04/05/06. Giữ nguyên ngữ nghĩa Q1–Q6/R-DEC.
- **Change 0.2.0:** Chốt Q1–Q6 (R-DEC-05..10) — cập nhật trạng thái quyết định, đóng OQ liên quan; phạm vi docs-first P0.
- **Change 0.1.0:** Viết lại 06 theo AI-EOS UI/UX — 8 nguyên tắc UX, IA 8 mục theo vai trò, 5 flow F1–F5, wireframe CEO/Review/Mobile, mẫu AI theo Autonomy L0–L4 + bộ component AI, design system (token/màu/thành phần/trực quan hóa), đa thiết bị + WCAG 2.1 AA + VI/EN.
