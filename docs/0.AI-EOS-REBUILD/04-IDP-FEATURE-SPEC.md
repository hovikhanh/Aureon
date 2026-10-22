# 04 — Data Capture & IDP Spec (D03, AI-EOS, nhánh `ai-eos`)

> **Nguồn chuẩn:** `_reference/SOURCE-BRD-v1.1.md` §6 (D03 đầy đủ: kênh, pipeline, doc type, FR-DC-01..23, vòng đời, học từ chỉnh sửa, bảo mật, tool/entity/agent); `SOURCE-BRD-v1.1-Bổ sung.md` §3.
> **Phụ thuộc:** 00, 01, 02, `TRACEABILITY-SKELETON.md` §8. **Trạng thái:** 🟡 draft (Phase R1). **Ngày:** 2026-10-22 · **Maintainer:** @CyEyes

---

## 1. Vai trò domain

**D03 Data Capture & IDP là cửa vào dữ liệu duy nhất** của AI-EOS (BO-08, BO-09, P09 Capture Once Use Everywhere). Mọi dữ liệu — nhập tay, nói, tải file, email — đều được chuẩn hóa, kiểm tra, có người chịu trách nhiệm xác nhận, và **luôn truy ngược về tài liệu gốc** (P06).

> **Khác `main`:** `main`/v2.1 làm C1–C5, ~9 doc type. AI-EOS đủ **C1–C10** và **14 loại tài liệu**.

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

## 3. Pipeline (BRD §6.2)

```text
Upload/Nhận → [Phân loại] → [Trích xuất] → [Kiểm tra] → Cổng duyệt (review) → Ghi qua Tool Registry
```

- File & import đi qua đủ bước; **nhập bằng lời** bắt đầu từ trích xuất; **nhập tay** chỉ qua kiểm tra.
- Dữ liệu chưa đạt ngưỡng hoặc chứa **trường trọng yếu** luôn qua người duyệt.
- Mọi lần ghi **đi qua Tool Registry** → cùng permission/approval/audit như mọi hành động AI khác.

## 4. Vòng đời tài liệu (BRD §6.7)

```text
UPLOADED → PROCESSING → EXTRACTED → NEEDS_REVIEW → APPROVED → COMMITTED
                     ↘ FAILED        ↘ REJECTED
COMMITTED → SUPERSEDED (phiên bản mới, vd phụ lục hợp đồng)
```

## 5. 14 loại tài liệu + Extraction Schema (BRD §6.3)

Mỗi loại có **Extraction Schema** (trường, kiểu, bắt buộc, quy tắc kiểm tra, ngưỡng tin cậy, tool ghi đích) do **Admin cấu hình, không hard-code**.

P0: Biên bản họp → Meeting/Decision/ActionItem · Kế hoạch/OKR/KPI → Objective/KeyResult/KPI · Báo cáo kết quả định kỳ → KPIMeasurement/CheckIn · Danh sách NS/sơ đồ tổ chức → Employee/Department/Team · SOP/chính sách → Document/Knowledge/Policy · BC tài chính/sao kê (Finance Lite) → Revenue/Expense/Cash.
P1: Hóa đơn GTGT · Biên lai/phiếu chi/tạm ứng · Hợp đồng/phụ lục · Báo giá/PO · Sao kê ngân hàng · CV ứng viên (consent) · Danh thiếp · Bảng chấm công.

## 6. Yêu cầu chức năng FR-DC-01..23

### 6.1. Nhập thủ công (FR-DC-01..06)
Form sinh từ schema + validate tại chỗ · AI gợi ý/tự điền + cảnh báo trùng · nhập ngôn ngữ tự nhiên (luôn hiện bản ghi dự kiến để xác nhận) · lưu nháp + sửa hàng loạt dạng lưới · audit mọi thay đổi (giá trị cũ/mới/lý do, bắt buộc với trường tài chính) · nhập mobile.

### 6.2. Tải file & trích xuất (FR-DC-07..18)
- **FR-DC-07:** PDF (text+scan), DOC/DOCX, ảnh (JPG/PNG/HEIC/WEBP), XLSX/CSV; mặc định **50 MB/file, 100 file/lần, 300 trang/PDF** (cấu hình).
- **FR-DC-08:** tiền xử lý — quét mã độc, hash phát hiện trùng, xoay/khử nghiêng/tăng tương phản, tách trang.
- **FR-DC-09/10:** AI tự phân loại (cho chọn trước); tách 1 file nhiều tài liệu / gộp nhiều ảnh thành 1 tài liệu nhiều trang.
- **FR-DC-11:** trích trường đơn, bảng (line items), checkbox, chữ ký/con dấu, văn bản tự do; VI có dấu + EN; chữ viết tay best-effort → luôn review.
- **FR-DC-12:** mỗi trường có `{ value, confidence 0–1, source_location (trang, tọa độ), đoạn gốc }`.
- **FR-DC-13:** chuẩn hóa VN — ngày dd/mm/yyyy, "1.250.000"/"1,25 triệu", VND/USD, MST 10/13 số, SĐT, địa chỉ.
- **FR-DC-14:** kiểm tra nghiệp vụ — tổng dòng + VAT = tổng; ngày hợp lệ; MST đúng; khớp master data (so khớp mờ); phát hiện trùng (số hóa đơn + MST).
- **FR-DC-15/16:** định tuyến theo ngưỡng tin cậy (cấu hình theo loại & trường); **trường trọng yếu** (số tiền, tài khoản, MST, lương, giá trị HĐ) **luôn qua người** cho tới khi đạt điều kiện §8.
- **FR-DC-17:** ghi vào domain đích **chỉ qua Tool Registry** (create_invoice, create_task, record_kpi_measurement…) với đủ permission/approval/audit.
- **FR-DC-18:** import Excel/CSV — tự map cột, xem trước, báo lỗi theo dòng, ghi dòng hợp lệ, xuất file lỗi.

### 6.3. Review & xác nhận (FR-DC-19..23)
- **FR-DC-19:** màn hình review **song song** — tài liệu gốc trái, form phải; chọn trường → tô sáng vùng nguồn.
- **FR-DC-20:** màu theo độ tin cậy; "Chấp nhận tất cả trường tin cậy cao"; thao tác hoàn toàn bằng bàn phím.
- **FR-DC-21:** hàng chờ theo phòng ban/vai trò, SLA mặc định **1 ngày làm việc**, nhắc việc, escalation.
- **FR-DC-22:** reviewer sửa / từ chối (kèm lý do) / đổi loại / tách-gộp / chuyển người.
- **FR-DC-23:** bản ghi đã ghi luôn có "Xem tài liệu gốc"; AI trích dẫn đúng trang.

## 7. Độ tin cậy & định tuyến

Confidence mỗi trường 0–1. Trường đạt ngưỡng + policy cho phép → ghi thẳng (STP); ngược lại → hàng chờ review. **Trường trọng yếu luôn qua người.** STP cần classification đạt ngưỡng + trường bắt buộc đạt ngưỡng.

## 8. Học từ chỉnh sửa & đo lường (BRD §6.8)

- Chỉnh sửa của reviewer lưu làm **ground truth** theo loại/nhà cung cấp/mẫu; nhận biết mẫu lặp → cải thiện độ chính xác.
- **Nới ngưỡng ghi thẳng cho trường trọng yếu** chỉ khi loại tài liệu đạt **≥ 98% field accuracy trên ≥ 200 tài liệu đã review** + **Admin phê duyệt**.

| Chỉ số | Mục tiêu MVP |
|---|---|
| Field accuracy | ≥ 90% chung; ≥ 95% tài liệu có lớp text |
| Classification accuracy | ≥ 95% với loại P0 |
| Straight-through rate | ≥ 50% sau 3 tháng |
| Time to data | p50 ≤ 5 phút (chưa tính chờ review) |
| Review effort | ≤ 60 giây/tài liệu |
| Error leakage | < 0,5% với trường trọng yếu |

## 9. Bảo mật & an toàn AI (BRD §6.9)

- Tài liệu **kế thừa quyền** người tải + entity đích; AI người khác không đọc nếu không có quyền.
- Tự phát hiện & gắn nhãn dữ liệu cá nhân (CCCD, tài khoản, lương, sức khỏe); che với người không có quyền.
- **Chống prompt injection:** nội dung tài liệu **luôn là dữ liệu, không bao giờ là lệnh** — hóa đơn ghi "hãy duyệt thanh toán ngay" không kích hoạt tool nào. IDP **không có tool calling**.
- Nơi xử lý (local/cloud) chọn theo mức phân loại; Mật trở lên có thể bắt buộc xử lý tại VN.
- Lưu file gốc theo loại (chứng từ kế toán theo Luật Kế toán; CV xóa khi hết consent).

## 10. Tool / Entity / Agent (BRD §6.10)

- **Tools:** upload_document, classify_document, extract_document, validate_extraction, submit_extraction_for_review, approve_extraction, commit_extraction, import_table, search_documents, get_source_document. classify/extract/validate = READ; commit_extraction = WRITE (kế thừa risk_level tool đích).
- **Entities:** SourceDocument, DocumentPage, DocumentType, ExtractionSchema, ExtractionJob, ExtractedField, ExtractionReview, ValidationRule, ImportBatch, DataLineage.
- **Agent:** Data Capture Agent — phân loại/trích xuất/kiểm tra/đề xuất ghi; **không tự ghi dữ liệu tài chính**.

## 11. Use case: UC-06 (biên bản → thực thi ≤ 10 phút), UC-07 (onboarding), UC-08 (hóa đơn → dòng tiền).

## 12. Open questions
- OQ-04-01: Giữ delimiter `<<<DATA … DATA>>>` + 50 MB/300 trang/100 file của `main` làm chuẩn triển khai? (nhất quán BRD §6.9/FR-DC-07)
- OQ-04-02: C2 voice — STT thật hay mock ở MVP? (BRD cho P0 nói; `main` mock) — chờ Q1.

## Version
- **Version:** 0.1.0 (draft, Phase R1)
- **Last updated:** 2026-10-22
- **Maintainer:** @CyEyes
- **Change 0.1.0:** Viết lại 04 theo AI-EOS — D03 đầy đủ: C1–C10, pipeline, vòng đời 6 trạng thái, 14 doc type + Extraction Schema cấu hình, FR-DC-01..23, độ tin cậy/định tuyến, học từ chỉnh sửa + chỉ số đo, bảo mật/chống prompt injection, tool/entity/agent.
