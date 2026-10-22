# 04 — Data Capture & IDP Spec (D03, Aureon v3 — AI-EOS)

> **Nguồn chuẩn:** `_reference/SOURCE-BRD-v1.1.md` §6 (D03 đầy đủ: kênh §6.1, pipeline §6.2, doc type §6.3, FR-DC-01..23 §6.4–§6.6, vòng đời §6.7, học từ chỉnh sửa §6.8, bảo mật §6.9, tool/entity/agent §6.10); `SOURCE-BRD-v1.1-Bổ sung.md` §3; `SOURCE-UIUX.md` (màn review song song, nhập mobile).
> **Phụ thuộc:** 00, 01, 02, `docs/4.GOVERNANCE/TRACEABILITY-SKELETON.md` §4 (FR-DC), §6 (UC), §8 (C1–C10), §11 (ENT Data Capture). **Trạng thái:** ✅ current — Aureon v3 (AI-EOS) CHÍNH THỨC. **Ngày:** 2026-10-23 · **Maintainer:** @CyEyes · *(tách từ Aureon v2.1, nay archived ở `docs/_archive/v2.1/`)*

---

## 1. Vai trò domain

**D03 Data Capture & IDP là cửa vào dữ liệu duy nhất** của AI-EOS (BO-08, BO-09, P09 Capture Once Use Everywhere). Mọi dữ liệu — nhập tay, nói, tải file, email — đều được chuẩn hóa, kiểm tra, có người chịu trách nhiệm xác nhận, và **luôn truy ngược về tài liệu gốc** (P06). Đây là domain xuyên suốt (cross-cutting) phục vụ mọi domain khác; không có D03 thì mọi P0 khác thiếu nguồn dữ liệu.

**Mục tiêu nghiệp vụ gắn với D03 (BRD §3.1 Bổ sung):**
- **BO-08 — Frictionless Data Capture:** giảm thời gian nhập liệu ≥ 70% so với nhập tay hoàn toàn.
- Đảm bảo dữ liệu đạt chất lượng đủ để AI ra quyết định — trường trọng yếu đạt ≥ 99% chính xác **sau review**.
- Biến kho tài liệu hiện có (hợp đồng, hóa đơn, biên bản, báo cáo) thành dữ liệu có cấu trúc.
- Hiện thực **P09 — Capture Once, Use Everywhere:** một dữ liệu chỉ nhập một lần, mọi domain dùng chung.

> **Khác `main`:** `main`/v2.1 làm C1–C5, ~9 doc type. AI-EOS đủ **C1–C10** và **14 loại tài liệu**. P0 của AI-EOS theo skeleton §12bis: kênh **C1–C5**; UC-06, UC-07 P0 (UC-08 P1). Chi tiết field-level DB (tên cột/kiểu/constraint per-entity) **hoãn sang đợt code (R-DEC-09)** — tài liệu này mô tả chiều sản phẩm (FR/UC/flow/rule/chỉ số/trạng thái/màn hình).

## 2. Kênh nhập liệu C1–C10 (BRD §6.1)

| Mã | Kênh | Định dạng | Ưu tiên |
|---|---|---|---|
| C1 | Form thủ công (sinh từ schema, validate tức thì, AI gợi ý/tự điền) | — | P0 |
| C2 | Ngôn ngữ tự nhiên (gõ hoặc **nói**) | Text, voice | P0 |
| C3 | Tải file (kéo thả nhiều file) | PDF text/scan, DOC/DOCX, JPG/PNG/HEIC/WEBP, XLS/XLSX/CSV | P0 |
| C4 | Chụp ảnh mobile (căn góc, khử nghiêng) | Ảnh | P0 |
| C5 | Import hàng loạt (AI map cột) | XLSX, CSV | P0 |
| C6 | Email forwarding (hộp thư theo tenant/phòng ban) | Mọi định dạng trên | P1 |
| C7 | Chat (bot Zalo/Slack/Teams) | Mọi định dạng trên | P1 |
| C8 | Hóa đơn điện tử XML (NĐ 123/2020, đọc trực tiếp XML) | XML | P1 |
| C9 | Thư mục đồng bộ (Google Drive/SharePoint) | Mọi định dạng trên | P1 |
| C10 | API / Webhook | JSON, file | P1 |

### 2.1. Mô tả từng kênh (P0 = C1–C5)

- **C1 — Form thủ công (P0):** Mỗi entity nghiệp vụ có một form **sinh từ ExtractionSchema**, không hard-code. Validate tức thì tại chỗ (bắt buộc, định dạng, khoảng giá trị, tham chiếu master data). AI gợi ý/tự điền giá trị theo ngữ cảnh người nhập. Luồng nhanh nhất, không đi qua trích xuất; chỉ qua bước **kiểm tra** trước khi ghi.
- **C2 — Ngôn ngữ tự nhiên, gõ hoặc nói (P0):** Người dùng mô tả tự do ("Ghi chi phí tiếp khách 2,5 triệu hôm qua, khách ABC"). AI dựng **bản ghi dự kiến** và **luôn hiển thị để xác nhận** trước khi ghi (không auto-commit từ lời nói). Kênh nói (voice→text) nằm trong P0 theo R-DEC-05; chi tiết hiện thực STT thật vs mock là chi tiết hóa ở đợt code (R-DEC-09, OQ-04-02). Bắt đầu pipeline từ bước **trích xuất** (đã có văn bản).
- **C3 — Tải file (P0):** Kéo thả một hoặc nhiều file; AI phân loại và trích xuất. Đi qua **đủ pipeline**. Định dạng: PDF (text + scan), DOC/DOCX, ảnh (JPG/PNG/HEIC/WEBP), XLS/XLSX/CSV. Đây là kênh trung tâm của IDP.
- **C4 — Chụp ảnh mobile (P0):** Chụp hóa đơn, biên lai, danh thiếp, ảnh bảng trắng; tiền xử lý tự căn góc, khử nghiêng, tăng tương phản (FR-DC-08). Luồng như C3 nhưng tối ưu cho ảnh chụp tại hiện trường.
- **C5 — Import hàng loạt (P0):** Excel/CSV theo template hoặc tự do; AI tự map cột → trường, xem trước, báo lỗi theo dòng (FR-DC-18). Sinh một **ImportBatch** gom nhiều bản ghi.
- **C6 — Email forwarding (P1):** Hộp thư riêng theo tenant/phòng ban (vd. `invoices@...`); file đính kèm tự vào hàng xử lý như C3. Backlog.
- **C7 — Chat integration (P1):** Gửi file qua bot Zalo/Slack/Teams; xử lý như C3. Backlog.
- **C8 — Hóa đơn điện tử XML (P1):** Đọc trực tiếp XML theo NĐ 123/2020 thay vì OCR bản PDF — chính xác tuyệt đối, có chữ ký số; bỏ qua OCR, vào thẳng kiểm tra. Backlog.
- **C9 — Thư mục đồng bộ (P1):** Theo dõi Google Drive/SharePoint, xử lý file mới tự động như C3. Backlog.
- **C10 — API / Webhook (P1):** Hệ thống ngoài đẩy tài liệu/dữ liệu (JSON, file); xác thực và vào pipeline. Backlog.

## 3. Pipeline (BRD §6.2)

```text
Upload/Nhận → [Phân loại] → [Trích xuất] → [Kiểm tra] → Cổng duyệt (review) → Ghi qua Tool Registry
```

### 3.1. Điểm vào theo kênh

- **File & import (C3/C4/C5):** đi qua **đủ** các bước.
- **Nhập bằng lời (C2):** bắt đầu từ bước **trích xuất** (văn bản đã có, không cần phân loại OCR nhưng vẫn xác định doc type nếu mơ hồ).
- **Nhập tay (C1):** chỉ qua bước **kiểm tra** (validate) rồi tới cổng duyệt/ghi.

### 3.2. Các bước pipeline chi tiết

1. **Upload/Nhận:** nhận file/dữ liệu theo kênh; tạo `ENT-SourceDocument` (trạng thái `UPLOADED`); lưu file gốc; stream chunk, không đọc cả file vào RAM. Tiền xử lý **FR-DC-08**: quét mã độc (malware), phát hiện file trùng bằng **hash**, xoay/khử nghiêng/tăng tương phản, **tách trang** (`ENT-DocumentPage`). Trạng thái → `PROCESSING`.
2. **Phân loại (classify):** AI xác định loại tài liệu trong 14 doc type (`ENT-DocumentType`); người dùng **có thể chọn trước** để bỏ qua (FR-DC-09). Có thể **tách 1 file nhiều tài liệu** / **gộp nhiều ảnh thành 1 tài liệu nhiều trang** (FR-DC-10). READ-only, không ghi nghiệp vụ.
3. **Trích xuất (extract):** chọn `ENT-ExtractionSchema` theo doc type; tạo `ENT-ExtractionJob`; sinh các `ENT-ExtractedField` dạng `{ value, confidence 0–1, source_location, đoạn gốc }` (FR-DC-11, FR-DC-12). Trạng thái → `EXTRACTED`. Lỗi không khôi phục → `FAILED`.
4. **Kiểm tra (validate):** chuẩn hóa VN (FR-DC-13) + kiểm tra nghiệp vụ theo `ENT-ValidationRule` (FR-DC-14); định tuyến theo ngưỡng tin cậy (FR-DC-15/16). Đạt STP → thẳng tới ghi; ngược lại → `NEEDS_REVIEW`.
5. **Cổng duyệt (review):** `ENT-ExtractionReview`; màn hình song song, hàng chờ theo phòng ban/vai trò, SLA, reviewer xác nhận/sửa/từ chối (FR-DC-19..22). `APPROVED` hoặc `REJECTED`.
6. **Ghi qua Tool Registry:** **chỉ** qua tool đích (create_invoice, create_task, record_kpi_measurement…) — cùng permission/approval/audit như mọi hành động AI (FR-DC-17). Tạo `ENT-DataLineage`. Trạng thái → `COMMITTED`.

> **Nguyên tắc chốt:** dữ liệu chưa đạt ngưỡng **hoặc** chứa **trường trọng yếu** luôn qua người duyệt; **mọi lần ghi đi qua Tool Registry**. IDP **không có tool calling** nội tại (xem §9).

## 4. Vòng đời tài liệu — state machine (BRD §6.7)

```text
UPLOADED → PROCESSING → EXTRACTED → NEEDS_REVIEW → APPROVED → COMMITTED
                     ↘ FAILED        ↘ REJECTED
COMMITTED → SUPERSEDED (phiên bản mới, vd phụ lục hợp đồng)
```

### 4.1. Các trạng thái

| Trạng thái | Ý nghĩa | Vào từ | Ra tới |
|---|---|---|---|
| `UPLOADED` | Đã nhận file/dữ liệu, chờ tiền xử lý | (mới) | `PROCESSING`, `FAILED` |
| `PROCESSING` | Đang tiền xử lý + phân loại + trích xuất | `UPLOADED` | `EXTRACTED`, `FAILED` |
| `EXTRACTED` | Đã trích xuất xong các trường, chờ kiểm tra/định tuyến | `PROCESSING` | `NEEDS_REVIEW`, `COMMITTED` (nếu STP), `FAILED` |
| `NEEDS_REVIEW` | Vào hàng chờ, cần người xác nhận | `EXTRACTED` | `APPROVED`, `REJECTED` |
| `APPROVED` | Reviewer đã duyệt, chờ ghi qua Tool Registry | `NEEDS_REVIEW` | `COMMITTED` |
| `REJECTED` | Reviewer từ chối (kèm lý do) — kết thúc, không ghi | `NEEDS_REVIEW` | (kết thúc) |
| `FAILED` | Lỗi xử lý không khôi phục (mã độc, hỏng file, trích xuất thất bại) | `UPLOADED`/`PROCESSING`/`EXTRACTED` | (kết thúc, có thể tải lại) |
| `COMMITTED` | Đã ghi vào domain đích qua Tool Registry, có lineage | `EXTRACTED`(STP)/`APPROVED` | `SUPERSEDED` |
| `SUPERSEDED` | Bị thay bằng phiên bản mới (vd phụ lục hợp đồng); bản cũ giữ để truy vết | `COMMITTED` | (kết thúc) |

### 4.2. Quy tắc chuyển trạng thái

- Chuyển `EXTRACTED → COMMITTED` **chỉ khi** đủ điều kiện STP §7 (classification + mọi trường bắt buộc đạt ngưỡng, không có trường trọng yếu chưa xác nhận).
- `REJECTED` và `FAILED` là trạng thái kết thúc; tài liệu không tự quay lại — người dùng tải lại hoặc sửa nguồn.
- `SUPERSEDED` chỉ áp cho bản đã `COMMITTED`; khi có phiên bản mới ghi đè, bản cũ chuyển `SUPERSEDED` nhưng giữ nguyên lineage để truy vết.
- Mỗi chuyển trạng thái ghi audit (ai, lúc nào, lý do nếu reject/supersede).

## 5. 14 loại tài liệu + Extraction Schema (BRD §6.3)

Mỗi loại có **Extraction Schema** (`ENT-ExtractionSchema`: trường, kiểu, bắt buộc, quy tắc kiểm tra, ngưỡng tin cậy, tool ghi đích) do **Admin cấu hình, không hard-code**.

| # | Loại tài liệu | Entity đích | Trường chính trích xuất | Hành động sau ghi | Ưu tiên |
|---|---|---|---|---|---|
| 1 | Biên bản họp (Word/PDF/ảnh bảng trắng) | Meeting, Decision, ActionItem | Ngày, thành phần, quyết định, việc cần làm, người phụ trách, hạn | Tạo task, giao việc, đồng bộ lịch | P0 |
| 2 | Kế hoạch/OKR/KPI (Word/Excel/PDF) | Objective, KeyResult, KPI, KPITarget | Mục tiêu, chỉ số, baseline, target, owner, kỳ | Đề xuất cây alignment, phát hiện KR thiếu task | P0 |
| 3 | Báo cáo kết quả định kỳ | KPIMeasurement, KRMeasurement, CheckIn | Chỉ số, giá trị thực tế, kỳ báo cáo | Cập nhật achievement, cảnh báo lệch | P0 |
| 4 | Danh sách NS/sơ đồ tổ chức | Employee, Department, Team, Position | Họ tên, chức danh, phòng ban, quản lý trực tiếp | Dựng cây tổ chức | P0 |
| 5 | SOP/chính sách/quy trình | Document, Knowledge, Policy | Tiêu đề, phiên bản, hiệu lực, chủ sở hữu | Đưa vào knowledge base | P0 |
| 6 | BC tài chính/sao kê số dư (Finance Lite) | Revenue, Expense, Cash | Kỳ, doanh thu, chi phí, số dư tiền | Cập nhật runway, dashboard | P0 |
| 7 | Hóa đơn GTGT đầu vào/đầu ra | Invoice, Expense, Revenue, Payable/Receivable | Ký hiệu, số, ngày, MST hai bên, dòng hàng, tiền trước thuế, VAT, tổng | Ghi công nợ, nhắc hạn thanh toán | P1 |
| 8 | Biên lai/phiếu chi/tạm ứng | Expense, Budget, CostCenter | Người chi, số tiền, mục đích, cost center | Kiểm tra ngân sách, gửi duyệt | P1 |
| 9 | Hợp đồng/phụ lục | Contract, Customer, Partner, Vendor | Các bên, giá trị, hiệu lực, điều khoản thanh toán, nghĩa vụ, phạt, gia hạn | Tạo mốc thanh toán, nhắc gia hạn, gắn rủi ro | P1 |
| 10 | Báo giá/PO | Opportunity, Proposal, PurchaseOrder | Khách/NCC, sản phẩm, số lượng, giá, hạn | Cập nhật pipeline, đối chiếu hóa đơn | P1 |
| 11 | Sao kê ngân hàng chi tiết | Payment, Cash flow | Ngày, số tiền, nội dung, đối tác | Đối soát với hóa đơn | P1 |
| 12 | CV ứng viên | Candidate | Họ tên, liên hệ, kinh nghiệm, kỹ năng | Map với vị trí tuyển (có consent) | P1 |
| 13 | Danh thiếp | Contact, Lead | Họ tên, chức vụ, công ty, điện thoại, email | Tạo lead, khử trùng | P1 |
| 14 | Bảng chấm công | Attendance, Leave | Nhân viên, ngày, giờ vào/ra, nghỉ | Cập nhật capacity | P1 |

> Field-level (kiểu, constraint, ngưỡng cụ thể từng trường) **chi tiết hóa ở đợt code (R-DEC-09)**; ở đây chỉ nêu trường chính và đích để truy nguyên BRD §6.3.

## 6. Yêu cầu chức năng FR-DC-01..23

### 6.1. Nhập thủ công (FR-DC-01..06)

- **FR-DC-01 — Form sinh từ schema:** Mọi entity nghiệp vụ có form nhập sinh từ `ENT-ExtractionSchema`; validate **tại chỗ** (bắt buộc, định dạng, khoảng giá trị, tham chiếu master data). Không hard-code form. Ràng buộc: form hiển thị đúng trường theo doc type/entity; lỗi validate hiện ngay tại trường.
- **FR-DC-02 — Gợi ý & chống trùng:** AI gợi ý giá trị theo ngữ cảnh (gõ "ABC" → gợi ý đúng khách hàng; tự điền cost center theo người nhập) và **cảnh báo bản ghi có khả năng trùng** trước khi lưu. Ràng buộc: gợi ý chỉ trong phạm vi quyền người nhập.
- **FR-DC-03 — Nhập ngôn ngữ tự nhiên:** Qua AI Assistant (text/voice); AI **luôn hiển thị bản ghi dự kiến để xác nhận trước khi ghi** — không ghi trực tiếp từ câu nói. Ràng buộc: xác nhận bắt buộc, kể cả khi confidence cao.
- **FR-DC-04 — Nháp & sửa lưới:** Lưu nháp, nhập tiếp sau; chỉnh sửa hàng loạt dạng lưới (grid) như Excel. Ràng buộc: nháp không phát event nghiệp vụ; sửa lưới vẫn qua validate.
- **FR-DC-05 — Audit thay đổi:** Mọi thay đổi thủ công ghi audit (ai, lúc nào, giá trị cũ, giá trị mới, **lý do bắt buộc với trường tài chính**). Ràng buộc: audit append-only, không sửa/xóa.
- **FR-DC-06 — Nhập mobile:** Giao diện nhập trên mobile cho tác vụ thường xuyên (check-in KPI/OKR, chi phí, task). Ràng buộc: tối ưu thao tác nhanh, một tay.

### 6.2. Tải file & trích xuất (FR-DC-07..18)

- **FR-DC-07 — Định dạng & giới hạn:** Nhận PDF (text + scan), DOC/DOCX, ảnh (JPG/PNG/HEIC/WEBP), XLSX/CSV; mặc định **50 MB/file, 100 file/lần, 300 trang/PDF** (cấu hình). Ràng buộc: whitelist MIME + magic bytes; vượt giới hạn → báo lỗi rõ.
- **FR-DC-08 — Tiền xử lý:** Quét mã độc; phát hiện file trùng bằng **hash**; xoay/khử nghiêng/tăng tương phản; **tách trang** → `ENT-DocumentPage`. Ràng buộc: file nhiễm mã độc → `FAILED` + cô lập; file trùng → cảnh báo, không tạo bản ghi mới mặc định.
- **FR-DC-09 — Tự phân loại:** AI tự phân loại 14 doc type; người dùng **chọn trước** để bỏ qua bước. Ràng buộc: classification kèm confidence; dưới ngưỡng → yêu cầu người chọn.
- **FR-DC-10 — Tách/gộp:** Tự tách 1 file nhiều tài liệu (vd 1 PDF scan 15 hóa đơn) thành nhiều bản ghi; gộp nhiều ảnh thành 1 tài liệu nhiều trang. Ràng buộc: mỗi bản ghi tách ra có lineage về file gốc.
- **FR-DC-11 — Loại nội dung trích:** Trích trường đơn, bảng (line items), checkbox, có/không chữ ký & con dấu, văn bản tự do; VI có dấu + EN; **chữ viết tay best-effort → luôn review**. Ràng buộc: handwriting không bao giờ STP.
- **FR-DC-12 — Cấu trúc trường:** Mỗi `ENT-ExtractedField` có `{ value, confidence 0–1, source_location (trang, vùng tọa độ), đoạn văn bản gốc }`. Ràng buộc: không thấy → `null`, **không bịa** (P05).
- **FR-DC-13 — Chuẩn hóa VN:** Ngày dd/mm/yyyy; số "1.250.000" / "1,25 triệu"; VND/USD; MST 10/13 số; SĐT; địa chỉ theo đơn vị hành chính hiện hành. Ràng buộc: chuẩn hóa không làm mất giá trị gốc (lưu đoạn gốc).
- **FR-DC-14 — Kiểm tra nghiệp vụ:** Tổng dòng hàng + VAT = tổng thanh toán; ngày hợp lệ; MST đúng định dạng; khớp master data (khách/NCC/NV) bằng **so khớp mờ**; phát hiện trùng (cùng số hóa đơn + MST). Ràng buộc: vi phạm kiểm tra → hạ confidence/chuyển review, không tự sửa số.
- **FR-DC-15 — Định tuyến theo ngưỡng:** Cấu hình theo **loại tài liệu và theo trường**; đạt ngưỡng + policy cho phép → ghi thẳng (STP), ngược lại → hàng chờ review. Ràng buộc: ngưỡng là cấu hình (Admin), không hard-code.
- **FR-DC-16 — Trường trọng yếu:** Số tiền, số tài khoản, MST, lương, giá trị hợp đồng **luôn cần người xác nhận** cho tới khi đạt điều kiện nới lỏng §8. Ràng buộc: cứng — không override bằng confidence cao.
- **FR-DC-17 — Ghi qua Tool Registry:** Ghi vào domain đích **chỉ qua Tool Registry** (create_invoice, create_task, record_kpi_measurement…) với đủ permission/approval/audit. Ràng buộc: một transaction/tài liệu; tool ghi kế thừa risk_level tool đích.
- **FR-DC-18 — Import Excel/CSV:** Tự map cột → trường, xem trước, báo lỗi theo dòng, ghi dòng hợp lệ, **xuất file lỗi** để sửa. Ràng buộc: gom thành `ENT-ImportBatch`; dòng lỗi không chặn dòng hợp lệ.

### 6.3. Review & xác nhận (FR-DC-19..23)

- **FR-DC-19 — Review song song:** Tài liệu gốc bên trái, form bên phải; chọn trường → **tô sáng vùng nguồn** (từ `source_location`). Ràng buộc: mọi trường có vùng nguồn tương ứng hoặc đánh dấu "không xác định".
- **FR-DC-20 — Màu & phím:** Màu theo độ tin cậy (xanh/vàng/đỏ); "Chấp nhận tất cả trường tin cậy cao"; thao tác **hoàn toàn bằng bàn phím**. Ràng buộc: "chấp nhận tất cả" **không** áp cho trường trọng yếu.
- **FR-DC-21 — Hàng chờ & SLA:** Hàng chờ theo phòng ban/vai trò; SLA mặc định **1 ngày làm việc**; nhắc việc + escalation qua Notification. Ràng buộc: quá SLA → escalate theo cấu hình; chỉ người có quyền thấy tài liệu trong hàng chờ.
- **FR-DC-22 — Thao tác reviewer:** Sửa / từ chối (**kèm lý do**) / đổi loại tài liệu / **tách–gộp** / **chuyển người (reassign)**. Ràng buộc: từ chối bắt buộc lý do; đổi loại → chạy lại schema tương ứng; mọi thao tác ghi audit.
- **FR-DC-23 — Truy nguồn:** Bản ghi đã ghi luôn có "Xem tài liệu gốc"; AI **trích dẫn đúng trang** khi trả lời. Ràng buộc: lineage tồn tại suốt vòng đời bản ghi (P06).

### 6.4. Review song song, reassign & merge (chi tiết)

- **Review song song:** Panel trái render tài liệu gốc theo trang (`ENT-DocumentPage`); panel phải là form trường. Chọn trường ở form → highlight bounding box trên trang; ngược lại click vùng trên trang → focus trường. Hỗ trợ zoom/xoay ảnh.
- **Reassign (chuyển người):** Reviewer chuyển `ENT-ExtractionReview` sang người/nhóm khác kèm lý do; hàng chờ và SLA tính lại cho người nhận; audit ghi chuỗi chuyển.
- **Đổi loại:** Khi phân loại sai, reviewer đổi doc type → hệ thống áp `ENT-ExtractionSchema` mới và trích xuất lại; trường cũ không khớp được đánh dấu để rà.
- **Tách/gộp tại review:** Reviewer tách một tài liệu bị gộp nhầm thành nhiều bản ghi, hoặc gộp nhiều trang/ảnh thành một; mỗi kết quả giữ lineage về nguồn gốc.
- **Merge dữ liệu:** Khi phát hiện bản ghi trùng (FR-DC-14), reviewer chọn hợp nhất vào bản ghi hiện có thay vì tạo mới; quyết định merge ghi audit + lineage.

## 7. Độ tin cậy & định tuyến (confidence & STP)

Confidence mỗi trường 0–1. Phân mức hiển thị (nhất quán `main`, chốt chi tiết ở đợt code — R-DEC-09): **Cao** (xanh), **Trung bình** (vàng), **Thấp** (đỏ).

**Quy tắc STP (straight-through):**
- Classification đạt ngưỡng cấu hình của loại tài liệu; **và**
- Mọi **trường bắt buộc** đạt ngưỡng cấu hình theo trường; **và**
- **Không** có trường trọng yếu chưa xác nhận (FR-DC-16).

Đạt cả ba → ghi thẳng (`EXTRACTED → COMMITTED`). Thiếu bất kỳ → `NEEDS_REVIEW`. **Trường trọng yếu** (số tiền, số tài khoản, MST, lương, giá trị HĐ) luôn qua người cho tới khi đạt điều kiện nới lỏng §8. Ngưỡng là **cấu hình** per-loại/per-trường, không hard-code.

## 8. Học từ chỉnh sửa & đo lường (BRD §6.8)

- Chỉnh sửa của reviewer lưu làm **ground truth** theo loại/nhà cung cấp/mẫu; hệ thống nhận biết **mẫu lặp** (cùng NCC, cùng template) → cải thiện độ chính xác theo thời gian.
- **Nới ngưỡng ghi thẳng cho trường trọng yếu** chỉ khi loại tài liệu đạt **≥ 98% field accuracy trên ≥ 200 tài liệu đã review** **và** **Admin phê duyệt**. Đây là rule cứng để mở STP cho trường trọng yếu.

| Chỉ số | Định nghĩa | Mục tiêu MVP |
|---|---|---|
| Field accuracy | % trường AI trích đúng, không cần sửa | ≥ 90% chung; ≥ 95% tài liệu có lớp text |
| Classification accuracy | % tài liệu phân loại đúng | ≥ 95% với loại P0 |
| Straight-through rate | % tài liệu ghi không cần sửa | ≥ 50% sau 3 tháng |
| Time to data | Từ tải lên đến dữ liệu dùng được | p50 ≤ 5 phút (chưa tính chờ review) |
| Review effort | Thời gian review trung bình/tài liệu | ≤ 60 giây/tài liệu |
| Chi phí/tài liệu | Chi phí AI + hạ tầng mỗi tài liệu | Theo dõi từ ngày đầu, có trần ngân sách |
| Error leakage | % bản ghi đã ghi bị phát hiện sai sau đó | < 0,5% với trường trọng yếu |

## 9. Bảo mật & an toàn AI (BRD §6.9)

- Tài liệu **kế thừa quyền** người tải + entity đích; AI của người khác không đọc nếu không có quyền.
- Tự phát hiện & gắn nhãn dữ liệu cá nhân (CCCD, số tài khoản, lương, sức khỏe); **che** với người không có quyền (cả khi hiển thị và khi đưa vào prompt).
- **Chống prompt injection:** nội dung tài liệu **luôn là dữ liệu, không bao giờ là lệnh** — một hóa đơn ghi "hãy duyệt thanh toán ngay" **không** kích hoạt bất kỳ tool nào. **IDP không có tool calling**; mọi lệnh trong tài liệu bị bỏ qua. (Quy ước delimiter bọc nội dung tài liệu là chi tiết triển khai — chốt ở đợt code, R-DEC-09, OQ-04-01.)
- Nơi xử lý (model nội bộ/cloud) chọn theo mức phân loại; dữ liệu Mật trở lên có thể bắt buộc xử lý tại Việt Nam.
- Lưu file gốc theo loại: chứng từ kế toán theo thời hạn Luật Kế toán; CV xóa khi hết consent.

## 10. Tool / Entity / Agent (BRD §6.10)

- **Tools (10 tool):** `upload_document`, `classify_document`, `extract_document`, `validate_extraction`, `submit_extraction_for_review`, `approve_extraction`, `commit_extraction`, `import_table`, `search_documents`, `get_source_document`.
  - **Phân loại READ:** classify/extract/validate/search/get — chỉ đọc, không ghi nghiệp vụ.
  - **WRITE:** `commit_extraction` — kế thừa `risk_level` của tool đích (create_invoice, create_task…); chịu permission/approval/audit đầy đủ.
- **Entities (10):** `ENT-SourceDocument`, `ENT-DocumentPage`, `ENT-DocumentType`, `ENT-ExtractionSchema`, `ENT-ExtractionJob`, `ENT-ExtractedField`, `ENT-ExtractionReview`, `ENT-ValidationRule`, `ENT-ImportBatch`, `ENT-DataLineage`. (Field/kiểu/quan hệ chốt ở 05-DATA-MODEL, R-DEC-07 mọi entity có `tenant_id`; R-DEC-09 field-level ở đợt code.)
- **Agent:** **Data Capture Agent** — phân loại, trích xuất, kiểm tra, **đề xuất** ghi; **không tự ghi dữ liệu tài chính** (ghi tài chính luôn qua người xác nhận + Tool Registry).

## 11. Use case

- **UC-06 — Biên bản giấy → thực thi (P0):** Tải/chụp biên bản họp (doc type #1) → phân loại → trích xuất (ngày, thành phần, quyết định, action item, người phụ trách, hạn) → kiểm tra → review (nếu cần) → ghi qua Tool Registry tạo Meeting/Decision/ActionItem và **tạo task, giao việc**. **Tiêu chí chấp nhận:** từ lúc tải tới khi task được tạo ≤ 10 phút (p50); mọi action item có người phụ trách + hạn; mỗi bản ghi có "Xem tài liệu gốc" đúng trang.
- **UC-07 — Onboarding doanh nghiệp (P0):** Import C5 danh sách nhân sự + sơ đồ tổ chức (doc type #4) → AI map cột → xem trước → ghi dòng hợp lệ → dựng cây tổ chức; kèm nạp SOP/chính sách (doc type #5) vào knowledge base. **Tiêu chí chấp nhận:** dựng được cây tổ chức từ file; dòng lỗi xuất ra file sửa, không chặn dòng hợp lệ; dữ liệu NS nhạy cảm (lương) được che theo quyền.
- **UC-08 — Hóa đơn → cảnh báo dòng tiền (P1):** Tải hóa đơn GTGT (doc type #7) → trích xuất + kiểm tra (tổng = dòng + VAT, MST, chống trùng) → review (trường trọng yếu luôn qua người) → ghi công nợ → cập nhật dòng tiền/cảnh báo. **Tiêu chí chấp nhận:** số tiền/MST luôn qua xác nhận người; phát hiện hóa đơn trùng; lineage tới hóa đơn gốc. *(UC-08 là P1 theo skeleton §12bis — backlog sau P0.)*

## 12. Open questions
- OQ-04-01: Delimiter `<<<DATA … DATA>>>` + giới hạn 50 MB/300 trang/100 file của `main` — là quy ước triển khai, chốt chi tiết ở đợt code (R-DEC-09); nhất quán BRD §6.9/FR-DC-07.
- OQ-04-02: C2 voice — P0 có kênh nói (voice) theo BRD (R-DEC-05: phủ tập P0); chi tiết hiện thực STT thật vs mock là chi tiết hóa ở đợt code (R-DEC-09).
- OQ-04-03: Ngưỡng confidence cụ thể per-loại/per-trường (Cao/TB/Thấp, STP classification + trường bắt buộc) là cấu hình Admin — giá trị số mặc định chốt ở đợt code (R-DEC-09), không hard-code trong spec.
- OQ-04-04: Mã `TOOL-*` cho 10 tool IDP (upload/classify/extract/validate/submit/approve/commit/import/search/get) cấp ở **10** (Tool Registry); skeleton chưa gán số TOOL — giữ tên hành vi, chờ 10 cấp ID.

## Version
- **Version:** 1.0.0 (current)
- **Last updated:** 2026-10-23
- **Maintainer:** @CyEyes
- **Change 1.0.0 (promote):** Promote tài liệu AI-EOS lên CHÍNH THỨC Aureon v3; di chuyển vào vị trí docs chuẩn; v2.1 archived (docs/_archive/v2.1/).
- **Change 0.3.0:** Mở rộng spec-level P0 — mô tả từng kênh C1–C10 (§2.1, P0=C1–C5), chi tiết 6 bước pipeline + điểm vào theo kênh (§3), state machine vòng đời tài liệu đầy đủ (bảng trạng thái + quy tắc chuyển §4), bảng 14 doc type với trường chính & đích (§5), mô tả hành vi + ràng buộc cho từng FR-DC-01..23 (§6.1–6.3), review song song/reassign/đổi loại/tách-gộp/merge (§6.4), quy tắc confidence & STP (§7), rule nới ngưỡng + chỉ số đo (§8), prompt-injection safety (§9), tool/entity/agent với ENT-* (§10), tiêu chí chấp nhận UC-06/07/08 (§11, UC-08=P1). Thêm OQ-04-03/04. (Khi đó chưa promote; không viết field-level DB — R-DEC-09.)
- **Change 0.2.0:** Chốt Q1–Q6 (R-DEC-05..10) — cập nhật trạng thái quyết định, đóng OQ liên quan; phạm vi docs-first P0.
- **Change 0.1.0:** Viết lại 04 theo AI-EOS — D03 đầy đủ: C1–C10, pipeline, vòng đời 6 trạng thái, 14 doc type + Extraction Schema cấu hình, FR-DC-01..23, độ tin cậy/định tuyến, học từ chỉnh sửa + chỉ số đo, bảo mật/chống prompt injection, tool/entity/agent.
