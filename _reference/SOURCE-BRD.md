# BRD — Rà soát, bổ sung & Nhập liệu đa kênh

Oct 5, 2026 · @CyEyes

## 1. Tóm tắt điều hành

BRD v1.0 có tầm nhìn đúng và khung AI-first tốt, nhưng còn thiếu "đường ống dữ liệu đầu vào": hệ thống giả định dữ liệu đã có sẵn, trong khi phần lớn doanh nghiệp Việt Nam vẫn vận hành bằng giấy tờ, PDF, Word, Excel và ảnh chụp. Không giải quyết khâu này, AI sẽ phân tích trên dữ liệu rỗng hoặc sai, và toàn bộ vòng lặp Data → Intelligence → Action bị gãy ngay từ mắt xích đầu tiên.

BRD v1.1 đề xuất 5 thay đổi chính:

1. **Thêm Domain 22: Data Capture & Intelligent Document Processing (IDP)** cho phép nhập liệu thủ công, nhập file (PDF, Word, Excel/CSV, ảnh) và qua email/chat; AI tự phân loại tài liệu, trích xuất dữ liệu, kiểm tra, cho người duyệt rồi ghi vào đúng domain. Đây là yêu cầu mới, xếp **P0** trong MVP.
2. **Bổ sung lớp Data Foundation**: master data, data quality score, data lineage, data contract cho từng entity, để "One Source of Truth" là thực chất chứ không phải khẩu hiệu.
3. **Định nghĩa rõ AI Autonomy Levels (L0–L4)** và gắn vào Approval Matrix, thay cho mô tả định tính hiện tại.
4. **Bổ sung bộ chỉ số sức khỏe doanh nghiệp chuẩn** (tài chính, khách hàng, vận hành, con người) làm "ngôn ngữ chung" cho CEO Dashboard và AI.
5. **Bổ sung yêu cầu còn thiếu**: AI evaluation và chi phí AI, tuân thủ Nghị định 13/2023/NĐ-CP về dữ liệu cá nhân, hóa đơn điện tử, change management, và MVP được thu hẹp để ra giá trị trong 90 ngày.

Đề xuất cách dùng tài liệu này: Phần 2 là đánh giá, Phần 3 là nội dung BRD mới có thể chèn nguyên văn vào BRD làm Domain 22, Phần 4–6 là các bản sửa cho các mục hiện có.

## 2. Đánh giá BRD v1.0

BRD v1.0 mạnh ở tầm nhìn và kiến trúc AI, yếu ở dữ liệu đầu vào, định lượng và tính khả thi của MVP.

### 2.1. Điểm mạnh nên giữ

- Vòng lặp Strategy → KPI/OKR → Initiative → Project → Task → Measurement là xương sống đúng, và là điểm khác biệt thực sự so với ERP/PM truyền thống.
- AI được coi là actor có identity, permission, audit (mục 7.6, 38–42). Đây là thiết kế đúng cho agentic system.
- Tool Registry có metadata risk\_level, approval\_required: nền tảng tốt cho governance.
- North Star "quyết định và hành động có outcome được xác minh" thay vì số cuộc hội thoại là lựa chọn trưởng thành.
- Cấu trúc insight Observation → Evidence → Impact → Recommendation → Confidence (mục 46) giúp AI có thể kiểm chứng.

### 2.2. Khoảng trống và rủi ro

| # | Khoảng trống | Tác động kinh doanh | Mức độ | Xử lý ở |
| --- | --- | --- | --- | --- |
| G1 | Không có cơ chế nhập liệu từ tài liệu (PDF, Word, ảnh). "Import" chỉ được nhắc 1 lần ở mục 9.2 | Dashboard rỗng, AI phân tích thiếu dữ liệu, người dùng quay lại Excel | Cao | Phần 3 |
| G2 | Thiếu Data Foundation: master data, data quality, lineage, xử lý trùng lặp | "One Source of Truth" không thành hiện thực; AI đưa khuyến nghị sai do dữ liệu bẩn | Cao | Phần 4.1 |
| G3 | Mức tự chủ của AI chỉ mô tả định tính ("✓ / policy", "Có thể") | Không thể cấu hình, không thể audit; rủi ro AI hành động vượt quyền | Cao | Phần 4.2 |
| G4 | Chưa có bộ chỉ số sức khỏe doanh nghiệp chuẩn (công thức, nguồn, ngưỡng) | Mỗi phòng ban định nghĩa một kiểu; CEO Briefing không nhất quán | Trung bình | Phần 4.3 |
| G5 | Không có yêu cầu đánh giá chất lượng AI (accuracy, hallucination) và kiểm soát chi phí AI | Chi phí token vượt kiểm soát; mất niềm tin khi AI sai | Cao | Phần 4.4 |
| G6 | Thiếu tuân thủ pháp lý Việt Nam: NĐ 13/2023 (dữ liệu cá nhân), hóa đơn điện tử, lưu trữ chứng từ kế toán | Rủi ro pháp lý khi AI đọc CV, hợp đồng lao động, ghi âm cuộc họp | Cao | Phần 4.5 |
| G7 | Không có workflow engine tổng quát (chỉ có approval) | Khó mô hình hóa quy trình đặc thù (mua sắm, tạm ứng, thanh toán) | Trung bình | Phần 4.6 |
| G8 | MVP P0 quá rộng: 13 hạng mục P0 gồm cả Meeting bot, KPI, OKR, Performance Cycle | Thời gian ra giá trị kéo dài; rủi ro dự án cao | Cao | Phần 6 |
| G9 | Thiếu change management và đo lường adoption | Hệ thống được triển khai nhưng nhân viên không dùng | Trung bình | Phần 5.3 |
| G10 | Mâu thuẫn ưu tiên: mục 82 không có Finance/Sales nhưng MVP Success Criteria (mục 88) yêu cầu AI tổng hợp Finance, Sales | MVP không thể đạt tiêu chí thành công của chính nó | Cao | Phần 6 |
| G11 | Thiếu domain Procurement / Vendor và Contract lifecycle riêng | Chi phí và hợp đồng — nguồn tài liệu lớn nhất — không có nơi ghi nhận | Trung bình | Phần 4.6 |
| G12 | NFR thiếu RPO/RTO, data residency, đa ngôn ngữ, mobile | Không đủ cơ sở cho thiết kế hạ tầng | Trung bình | Phần 5.2 |

## 3. Domain 22 mới: Data Capture & Intelligent Document Processing

Mọi dữ liệu vào AI-EOS đi qua một cửa duy nhất: dù nhập tay, tải file hay gửi qua email, dữ liệu đều được chuẩn hóa, kiểm tra, có người chịu trách nhiệm xác nhận, và luôn truy ngược được về tài liệu gốc. Domain này là nền tảng (cross-cutting) phục vụ tất cả 21 domain còn lại.

### 3.1. Mục tiêu nghiệp vụ

- **BO-08 — Frictionless Data Capture:** giảm thời gian nhập liệu ít nhất 70% so với nhập tay hoàn toàn.
- Đảm bảo dữ liệu vào hệ thống đạt chất lượng đủ để AI ra quyết định (trường trọng yếu đạt ≥ 99% chính xác sau review).
- Biến kho tài liệu hiện có (hợp đồng, hóa đơn, biên bản, báo cáo) thành dữ liệu có cấu trúc và tri thức cho Enterprise Knowledge Graph.
- Nguyên tắc mới **P09 — Capture Once, Use Everywhere:** một dữ liệu chỉ nhập một lần, mọi domain dùng chung.

### 3.2. Kênh nhập liệu

| Mã | Kênh | Mô tả | Định dạng | Phase |
| --- | --- | --- | --- | --- |
| C1 | Nhập thủ công qua form | Form theo từng entity, validate tức thì, AI gợi ý/tự điền trường | — | MVP |
| C2 | Nhập bằng ngôn ngữ tự nhiên | Gõ hoặc nói: "Ghi chi phí tiếp khách 2,5 triệu hôm qua, khách ABC"; AI dựng bản ghi để xác nhận | Text, voice | MVP |
| C3 | Tải file lên | Kéo thả 1 hoặc nhiều file; AI phân loại và trích xuất | PDF (text và scan), DOC/DOCX, JPG/PNG/HEIC/WEBP, XLS/XLSX/CSV | MVP |
| C4 | Chụp ảnh trên mobile | Chụp hóa đơn, biên lai, danh thiếp, bảng trắng; tự căn góc, khử nghiêng | Ảnh | MVP |
| C5 | Import hàng loạt | File Excel/CSV theo template hoặc tự do; AI tự map cột sang trường | XLSX, CSV | MVP |
| C6 | Email forwarding | Mỗi tenant/phòng ban có hộp thư riêng (vd. invoices@...); file đính kèm tự vào hàng xử lý | Mọi định dạng trên | Phase 2 |
| C7 | Chat integration | Gửi file vào Zalo/Slack/Teams bot | Mọi định dạng trên | Phase 2 |
| C8 | Hóa đơn điện tử XML | Đọc trực tiếp XML theo NĐ 123/2020 thay vì OCR bản PDF: chính xác tuyệt đối, có chữ ký số | XML | Phase 2 |
| C9 | Drive / thư mục đồng bộ | Theo dõi thư mục Google Drive/SharePoint, xử lý file mới | Mọi định dạng trên | Phase 2 |
| C10 | API / Webhook | Hệ thống ngoài đẩy tài liệu hoặc dữ liệu vào | JSON, file | Phase 2 |

### 3.3. Pipeline xử lý tài liệu

&#91;embedded content: pipeline nhập liệu · 4 kênh, 4 bước xử lý, 1 cổng duyệt\]

File và import đi qua đủ các bước; nhập bằng lời bắt đầu từ trích xuất, nhập tay chỉ qua kiểm tra. Dữ liệu chưa đạt ngưỡng tin cậy hoặc chứa trường trọng yếu luôn qua người duyệt, và mọi lần ghi đều đi qua Tool Registry nên chịu cùng permission, approval và audit như mọi hành động AI khác.

### 3.4. Danh mục loại tài liệu và đích đến

Mỗi loại tài liệu có một **Extraction Schema** (danh sách trường, kiểu, bắt buộc, quy tắc kiểm tra) do Admin cấu hình, không hard-code.

| Loại tài liệu | Domain / Entity đích | Trường chính cần trích xuất | Hành động AI sau khi ghi | Phase |
| --- | --- | --- | --- | --- |
| Biên bản họp (Word/PDF/ảnh bảng trắng) | Meeting, Decision, ActionItem | Ngày, thành phần, quyết định, việc cần làm, người phụ trách, hạn | Tạo task, giao việc, đồng bộ lịch | MVP |
| Kế hoạch, OKR, KPI (Word/Excel/PDF) | Objective, KeyResult, KPI, KPITarget | Mục tiêu, chỉ số, baseline, target, owner, kỳ | Đề xuất cây alignment, phát hiện KR thiếu task | MVP |
| Báo cáo kết quả định kỳ | KPIMeasurement, KRMeasurement, CheckIn | Chỉ số, giá trị thực tế, kỳ báo cáo | Cập nhật achievement, cảnh báo lệch | MVP |
| Danh sách nhân sự, sơ đồ tổ chức | Employee, Department, Team, Position | Họ tên, chức danh, phòng ban, quản lý trực tiếp | Dựng cây tổ chức | MVP |
| Tài liệu quy trình, SOP, chính sách | Document, Knowledge, Policy | Tiêu đề, phiên bản, hiệu lực, chủ sở hữu | Đưa vào knowledge base để AI tra cứu | MVP |
| Hóa đơn GTGT đầu vào/đầu ra | Invoice, Expense, Revenue, Payable/Receivable | Ký hiệu, số, ngày, MST bên bán/mua, dòng hàng, tiền trước thuế, VAT, tổng | Ghi công nợ, nhắc hạn thanh toán | Phase 2 |
| Biên lai, phiếu chi, đề nghị tạm ứng | Expense, Budget, CostCenter | Người chi, số tiền, mục đích, cost center | Kiểm tra ngân sách, gửi duyệt | Phase 2 |
| Hợp đồng, phụ lục | Contract, Customer, Partner, Vendor | Các bên, giá trị, hiệu lực, điều khoản thanh toán, nghĩa vụ, phạt, gia hạn | Tạo mốc thanh toán, nhắc gia hạn, gắn rủi ro | Phase 2 |
| Báo giá, đơn đặt hàng (PO) | Opportunity, Proposal, Purchase Order | Khách/NCC, sản phẩm, số lượng, giá, hạn | Cập nhật pipeline | Phase 2 |
| Sao kê ngân hàng | Payment, Cash flow | Ngày, số tiền, nội dung, đối tác | Đối soát với hóa đơn | Phase 2 |
| CV ứng viên | Candidate | Họ tên, liên hệ, kinh nghiệm, kỹ năng | Map với job opening (có consent, xem 4.5) | Phase 2 |
| Danh thiếp | Contact, Lead | Họ tên, chức vụ, công ty, điện thoại, email | Tạo lead, khử trùng | Phase 2 |
| Bảng chấm công | Attendance, Leave | Nhân viên, ngày, giờ vào/ra, nghỉ | Cập nhật capacity cho workload | Phase 2 |

### 3.5. Yêu cầu chức năng

**Nhập thủ công (FR-DC-01 đến 06)**

- FR-DC-01: Mọi entity nghiệp vụ có form nhập sinh từ schema; validate tại chỗ (bắt buộc, định dạng, khoảng giá trị, tham chiếu master data).
- FR-DC-02: AI gợi ý giá trị (vd. gõ "ABC" gợi ý đúng khách hàng; tự điền cost center theo người nhập), cảnh báo bản ghi có khả năng trùng.
- FR-DC-03: Nhập bằng ngôn ngữ tự nhiên (text/voice) qua AI Assistant; AI luôn hiển thị bản ghi dự kiến để người dùng xác nhận trước khi ghi.
- FR-DC-04: Lưu nháp, nhập tiếp sau; chỉnh sửa hàng loạt dạng lưới (grid) như Excel.
- FR-DC-05: Mọi thay đổi thủ công ghi audit: ai, lúc nào, giá trị cũ, giá trị mới, lý do (bắt buộc với trường tài chính).
- FR-DC-06: Giao diện nhập trên mobile cho các tác vụ thường xuyên (check-in KPI/OKR, chi phí, task).

**Tải file và AI trích xuất (FR-DC-07 đến 18)**

- FR-DC-07: Nhận PDF (có lớp text và bản scan), DOC/DOCX, ảnh (JPG, PNG, HEIC, WEBP), XLSX/CSV; tối đa 50 MB/file, 100 file/lần tải, PDF tối đa 300 trang (configurable).
- FR-DC-08: Tiền xử lý: quét mã độc, phát hiện file trùng bằng hash, xoay/khử nghiêng/tăng tương phản ảnh, tách trang.
- FR-DC-09: AI tự phân loại loại tài liệu; người dùng có thể chọn trước loại để bỏ qua bước này.
- FR-DC-10: Tự tách một file chứa nhiều tài liệu (vd. 1 PDF scan 15 hóa đơn) thành nhiều bản ghi; tự gộp nhiều ảnh thành một tài liệu nhiều trang.
- FR-DC-11: Trích xuất trường đơn, bảng (line items), checkbox, chữ ký/con dấu (có/không), và văn bản tự do; hỗ trợ tiếng Việt có dấu và tiếng Anh; chữ viết tay ở mức best-effort, luôn chuyển review.
- FR-DC-12: Mỗi trường trích xuất có: giá trị, độ tin cậy (0–1), vị trí nguồn (trang, vùng tọa độ), đoạn văn bản gốc.
- FR-DC-13: Chuẩn hóa theo ngữ cảnh Việt Nam: ngày dd/mm/yyyy, số "1.250.000" và "1,25 triệu", VND/USD, MST 10 hoặc 13 số, số điện thoại, địa chỉ theo đơn vị hành chính mới.
- FR-DC-14: Kiểm tra nghiệp vụ: tổng dòng hàng + VAT = tổng thanh toán; ngày hợp lệ; MST đúng định dạng; khớp master data (khách hàng, nhà cung cấp, nhân viên) bằng so khớp mờ; phát hiện bản ghi trùng (cùng số hóa đơn + MST).
- FR-DC-15: Định tuyến theo ngưỡng tin cậy cấu hình được theo loại tài liệu và theo trường: đạt ngưỡng và policy cho phép thì tự ghi (straight-through), ngược lại vào hàng chờ review.
- FR-DC-16: **Trường trọng yếu** (số tiền, số tài khoản, MST, lương, giá trị hợp đồng) luôn cần người xác nhận trong giai đoạn đầu; chỉ nới lỏng khi độ chính xác thực tế đã được chứng minh (xem 3.8).
- FR-DC-17: Ghi vào domain đích **chỉ qua Tool Registry** (vd. create\_invoice, create\_task, record\_kpi\_measurement), áp dụng đầy đủ permission, approval và audit như mọi AI action khác.
- FR-DC-18: Import Excel/CSV: AI tự map cột sang trường, hiển thị bản xem trước, báo lỗi theo dòng, cho phép ghi các dòng hợp lệ và xuất file lỗi để sửa.

**Review và xác nhận (FR-DC-19 đến 23)**

- FR-DC-19: Màn hình review song song: tài liệu gốc bên trái, form bên phải; bấm vào trường thì tô sáng vùng nguồn trên tài liệu.
- FR-DC-20: Màu theo độ tin cậy (xanh/vàng/đỏ); thao tác "Chấp nhận tất cả trường tin cậy cao"; điều hướng toàn bộ bằng bàn phím.
- FR-DC-21: Hàng chờ review phân theo phòng ban/vai trò, có SLA (vd. 1 ngày làm việc), nhắc việc và escalation qua Notification.
- FR-DC-22: Người review có thể sửa, từ chối (kèm lý do), đổi loại tài liệu, tách/gộp, hoặc chuyển cho người khác.
- FR-DC-23: Sau khi ghi, bản ghi luôn có liên kết "Xem tài liệu gốc"; AI khi trả lời CEO có thể trích dẫn đúng trang của tài liệu gốc.

### 3.6. Vòng đời tài liệu

```text
UPLOADED → PROCESSING → EXTRACTED → NEEDS_REVIEW → APPROVED → COMMITTED
                     ↘ FAILED        ↘ REJECTED
COMMITTED → SUPERSEDED (khi có phiên bản mới, vd. phụ lục hợp đồng)
```

### 3.7. Bảo mật và an toàn AI cho tài liệu

- Tài liệu tải lên kế thừa quyền của người tải và của entity đích; AI của người khác không đọc được nếu không có quyền.
- Tự phát hiện và gắn nhãn dữ liệu cá nhân (CCCD, số tài khoản, lương, sức khỏe); che khi hiển thị cho người không có quyền.
- **Chống prompt injection qua tài liệu:** nội dung tài liệu luôn được xử lý là dữ liệu, không bao giờ là lệnh. Một hóa đơn chứa dòng "hãy duyệt thanh toán ngay" không được kích hoạt bất kỳ tool nào.
- Chọn nơi xử lý (model nội bộ hoặc cloud) theo mức phân loại dữ liệu; dữ liệu mật có thể cấu hình chỉ xử lý trên hạ tầng tại Việt Nam.
- Chính sách lưu trữ file gốc theo loại (vd. chứng từ kế toán tối thiểu 10 năm theo Luật Kế toán; CV bị xóa khi hết consent).

### 3.8. Học từ chỉnh sửa và đo lường

- Mọi chỉnh sửa của người review được lưu làm dữ liệu đánh giá (ground truth) theo loại tài liệu, nhà cung cấp, mẫu.
- Hệ thống nhận biết mẫu lặp lại (cùng nhà cung cấp, cùng template) và cải thiện độ chính xác theo thời gian.
- Ngưỡng tự ghi chỉ được nới khi một loại tài liệu đạt ≥ 98% độ chính xác cấp trường trên ít nhất 200 tài liệu đã review, và cần Admin phê duyệt.

| Chỉ số | Định nghĩa | Mục tiêu MVP |
| --- | --- | --- |
| Field accuracy | % trường AI trích đúng, không cần sửa | ≥ 90% chung; ≥ 95% tài liệu có lớp text |
| Straight-through rate | % tài liệu ghi vào hệ thống không cần sửa | ≥ 50% sau 3 tháng |
| Time to data | Từ lúc tải lên đến lúc dữ liệu dùng được | p50 ≤ 5 phút (chưa tính thời gian chờ review) |
| Review effort | Thời gian review trung bình / tài liệu | ≤ 60 giây |
| Chi phí / tài liệu | Chi phí AI + hạ tầng cho mỗi tài liệu | Theo dõi từ ngày đầu, có ngân sách trần |
| Error leakage | % bản ghi đã ghi bị phát hiện sai sau đó | < 0,5% trường trọng yếu |

### 3.9. Tool, entity và agent bổ sung

- **Tools (bổ sung mục 38):** upload\_document(), classify\_document(), extract\_document(), validate\_extraction(), submit\_extraction\_for\_review(), approve\_extraction(), commit\_extraction(), import\_table(), search\_documents(), get\_source\_document().
- **Phân loại (mục 39):** classify/extract/validate là READ; commit\_extraction là WRITE, kế thừa risk\_level của tool đích (ghi hóa đơn rủi ro cao hơn ghi task).
- **Entities (bổ sung mục 50):** SourceDocument, DocumentPage, DocumentType, ExtractionSchema, ExtractionJob, ExtractedField, ExtractionReview, ValidationRule, ImportBatch, DataLineage.
- **Agent mới (mục 40):** Data Capture Agent, chịu trách nhiệm phân loại, trích xuất, kiểm tra và đề xuất ghi; không tự ghi dữ liệu tài chính.

## 4. Cải tiến cho các phần hiện có

Sáu cải tiến dưới đây biến các nguyên tắc định tính của v1.0 thành yêu cầu có thể cấu hình, kiểm thử và nghiệm thu.

### 4.1. Data Foundation (bổ sung vào mục 5 và 91)

- **Master Data Management:** mỗi entity cốt lõi (Employee, Customer, Partner, Vendor, Product, Project) có một nguồn gốc được chỉ định, một data owner, quy tắc khử trùng và hợp nhất bản ghi (merge).
- **Data Quality Score** cho từng domain: đầy đủ, chính xác, kịp thời, nhất quán. AI phải hiển thị cảnh báo khi kết luận dựa trên dữ liệu có điểm chất lượng thấp (vd. "Doanh thu tháng 9 mới có 62% hóa đơn được nhập").
- **Data Freshness:** mỗi chỉ số trên dashboard hiển thị thời điểm cập nhật cuối; CEO Briefing ghi rõ dữ liệu nào đã cũ.
- **Data Lineage:** từ một con số trên báo cáo, truy ngược được đến bản ghi, người nhập và tài liệu gốc (nối với Domain 22).
- **Event backbone:** mọi thay đổi nghiệp vụ phát sự kiện (vd. invoice.created, kpi.measured, task.overdue) để AI "Observe" theo thời gian thực thay vì quét định kỳ.
- **Semantic layer / Metric store:** định nghĩa chỉ số một lần (công thức, nguồn, bộ lọc), dùng chung cho dashboard, báo cáo và AI. Tránh việc AI tính "doanh thu" khác với Finance.

### 4.2. AI Autonomy Levels (thay thế cột "AI tự động" ở mục 77)

| Level | Tên | AI được làm gì | Ví dụ | Mặc định cho |
| --- | --- | --- | --- | --- |
| L0 | Inform | Chỉ đọc và trả lời | "Doanh thu tháng này?" | Mọi tool READ |
| L1 | Suggest | Đề xuất, người dùng tự thực hiện | Gợi ý chuyển task từ B sang C | Phân bổ nguồn lực |
| L2 | Draft & Confirm | AI chuẩn bị sẵn, người dùng bấm xác nhận | Dữ liệu trích từ hóa đơn, email gửi khách | Ghi dữ liệu tài chính, giao tiếp bên ngoài |
| L3 | Act & Notify | AI tự làm trong policy, báo lại, có thể hoàn tác | Tạo task từ biên bản họp, đặt lịch nhắc | Task, lịch, nhắc việc nội bộ |
| L4 | Autonomous | AI tự làm, chỉ ghi audit, báo cáo định kỳ | Cập nhật KPI từ nguồn tích hợp đã tin cậy | Không bật trong MVP |

Yêu cầu: level được cấu hình theo tool × vai trò × ngưỡng giá trị (vd. chi phí dưới 5 triệu: L3; từ 5 triệu: L2 + duyệt quản lý). Mọi hành động L3 trở lên phải có nút hoàn tác trong tối thiểu 24 giờ nếu bản chất hành động cho phép. Có "kill switch" tắt toàn bộ hành động WRITE/EXECUTION của AI chỉ bằng một thao tác của Admin.

### 4.3. Bộ chỉ số sức khỏe doanh nghiệp chuẩn (bổ sung mục 44 và 47)

CEO cần một bộ chỉ số cố định, có công thức và ngưỡng cảnh báo, dùng chung cho Dashboard, Briefing và AI. Đề xuất bộ mặc định (doanh nghiệp tinh chỉnh được):

| Nhóm | Chỉ số | Công thức tóm tắt | Ngưỡng cảnh báo gợi ý |
| --- | --- | --- | --- |
| Tài chính | Tăng trưởng doanh thu | (DT kỳ này − DT cùng kỳ) / DT cùng kỳ | Thấp hơn kế hoạch > 10% |
| Tài chính | Biên lợi nhuận gộp, biên EBITDA | Lợi nhuận / Doanh thu | Giảm > 3 điểm % so với trung bình 3 kỳ |
| Tài chính | Cash runway | Tiền mặt / Burn ròng hàng tháng | < 6 tháng |
| Tài chính | DSO, DPO, vòng quay tiền (CCC) | DSO + DIO − DPO | DSO tăng > 15% |
| Tài chính | Công nợ quá hạn | Phải thu quá hạn / Tổng phải thu | > 15% |
| Tài chính | Chênh lệch ngân sách | (Thực chi − Ngân sách) / Ngân sách | > 10% |
| Khách hàng | Pipeline coverage | Pipeline có trọng số / Chỉ tiêu còn lại | < 3x |
| Khách hàng | Tỷ lệ chuyển đổi, chu kỳ bán hàng | Won / Tổng cơ hội đã đóng | Giảm > 20% |
| Khách hàng | Giữ chân doanh thu (NRR), churn | DT khách cũ kỳ này / kỳ trước | NRR < 100% |
| Khách hàng | Mức độ tập trung doanh thu | DT top 5 khách / Tổng DT | > 50% |
| Khách hàng | CAC, LTV/CAC, NPS | Theo định nghĩa chuẩn | LTV/CAC < 3 |
| Vận hành | Tỷ lệ hoàn thành đúng hạn | Task xong đúng hạn / Task đến hạn | < 80% |
| Vận hành | Dự án trễ tiến độ | Số dự án trễ > 10% / Tổng dự án | > 20% |
| Vận hành | Thực thi quyết định | Action item từ cuộc họp đã xong / Tổng | < 70% |
| Con người | Doanh thu / nhân sự, chi phí nhân sự / doanh thu | Theo kỳ | Lệch > 15% so với kế hoạch |
| Con người | Tỷ lệ nghỉ việc (đặc biệt nhân sự giỏi) | Nghỉ việc / Bình quân nhân sự, năm hóa | > 15%/năm |
| Con người | Quá tải | Số người workload > 110% trong 2 tuần liên tiếp | > 10% nhân sự |
| Chiến lược | Strategy execution index | % initiative đúng tiến độ có trọng số | < 70% |

### 4.4. AI Quality, Evaluation & Cost (bổ sung mục 37 và 76)

- **Evaluation Engine có bộ test chuẩn:** mỗi agent và mỗi loại câu hỏi cốt lõi ("Tình hình công ty?", "Tại sao KPI X thấp?") có bộ câu hỏi mẫu với đáp án đã biết; chạy lại trước mọi thay đổi model/prompt.
- **Grounding bắt buộc:** mọi con số AI đưa ra phải đến từ tool call hoặc tài liệu có trích dẫn; con số không có nguồn bị chặn hoặc gắn nhãn "ước tính".
- **Confidence có hiệu chỉnh:** "Confidence 84%" (mục 46) phải được đối chiếu với kết quả thực tế theo thời gian; nếu chưa hiệu chỉnh được thì dùng thang Cao/Trung bình/Thấp kèm lý do.
- **Phản hồi người dùng:** mọi câu trả lời và khuyến nghị có nút đúng/sai, lý do; dữ liệu này vào Evaluation Engine.
- **Model routing và chi phí:** tác vụ đơn giản dùng model nhỏ, tác vụ suy luận dùng model lớn; ngân sách AI theo tenant/phòng ban/agent, cảnh báo khi đạt 80%; báo cáo chi phí AI trên mỗi quyết định được hỗ trợ.
- **Model-agnostic:** Model Gateway không khóa vào một nhà cung cấp; hỗ trợ model on-premise cho dữ liệu mật.

### 4.5. Tuân thủ pháp lý Việt Nam (bổ sung mục 75 và 76)

- **Bảo vệ dữ liệu cá nhân (NĐ 13/2023/NĐ-CP và Luật Bảo vệ dữ liệu cá nhân):** quản lý consent (ứng viên, nhân viên, người tham gia họp), phân loại dữ liệu cá nhân nhạy cảm, quyền truy cập/xóa của chủ thể dữ liệu, hồ sơ đánh giá tác động xử lý dữ liệu, kiểm soát chuyển dữ liệu ra nước ngoài khi dùng AI cloud.
- **Ghi âm cuộc họp (mục 34):** thông báo rõ cho mọi người tham gia, có cơ chế từ chối, chính sách lưu trữ và xóa bản ghi âm.
- **Kế toán và hóa đơn:** hóa đơn điện tử theo NĐ 123/2020 và các văn bản sửa đổi; lưu trữ chứng từ theo Luật Kế toán; AI-EOS là lớp quản trị, không thay thế phần mềm kế toán theo chuẩn mực (tích hợp MISA, Fast, Bravo...).
- **Chữ ký số** cho các phê duyệt có giá trị pháp lý (Phase 2+).

### 4.6. Bổ sung domain và năng lực

- **Workflow Engine tổng quát** (bổ sung Domain 21): quy trình nhiều bước cấu hình bằng giao diện hoặc bằng ngôn ngữ tự nhiên ("Khi có đề nghị mua sắm trên 20 triệu, gửi Trưởng phòng rồi CFO"); AI là một bước trong workflow.
- **Domain Procurement / Vendor:** nhà cung cấp, đề nghị mua sắm, PO, nghiệm thu, đánh giá nhà cung cấp. Đây là nguồn chi phí lớn và nguồn tài liệu lớn cho Domain 22.
- **Contract Lifecycle:** tách Contract thành entity xuyên domain (khách hàng, đối tác, nhà cung cấp, lao động) với nghĩa vụ, mốc, gia hạn; AI nhắc trước hạn và cảnh báo điều khoản bất lợi.
- **Decision Log** (nâng cấp entity Decision): ghi quyết định, lý do, phương án đã loại, người quyết, kết quả kỳ vọng; sau 30/60/90 ngày AI đối chiếu kết quả thực tế. Đây là cách đo North Star ở mục 89.
- **Scenario planning:** CEO hỏi "Nếu tuyển thêm 3 sales thì runway và doanh thu Q1 thay đổi thế nào?"; AI chạy mô hình what-if trên dữ liệu thực.
- **Tích hợp phổ biến tại Việt Nam:** Zalo/Zalo OA, MISA, ngân hàng (sao kê), cổng hóa đơn điện tử, Microsoft 365 bên cạnh Google Workspace.

## 5. User stories, use case và NFR bổ sung

### 5.1. EPIC R — DATA CAPTURE & DOCUMENT AI

| ID | User story | Tiêu chí nghiệm thu chính | Ưu tiên |
| --- | --- | --- | --- |
| US-DC-001 | Là Employee, tôi muốn nhập dữ liệu qua form có kiểm tra tức thì để không nhập sai | Trường sai báo lỗi trước khi lưu; cảnh báo trùng; lưu nháp | P0 |
| US-DC-002 | Là Manager, tôi muốn nói hoặc gõ một câu để AI tạo bản ghi | AI hiển thị bản ghi dự kiến; chỉ ghi sau khi tôi xác nhận | P0 |
| US-DC-003 | Là User, tôi muốn tải PDF, Word, ảnh để AI tự trích xuất dữ liệu | Nhận đủ định dạng FR-DC-07; phân loại đúng ≥ 95% loại tài liệu MVP | P0 |
| US-DC-004 | Là Manager, tôi muốn tải biên bản họp Word để AI tạo task, giao người và đặt hạn | Mỗi action item thành 1 task có owner, deadline, link về đoạn gốc | P0 |
| US-DC-005 | Là Manager, tôi muốn tải file kế hoạch KPI/OKR hiện có để không phải nhập lại | AI dựng KPI/Objective/KR với baseline, target, owner; tôi duyệt trước khi kích hoạt | P0 |
| US-DC-006 | Là Reviewer, tôi muốn xem tài liệu gốc cạnh dữ liệu AI trích để duyệt nhanh | Tô sáng vùng nguồn; màu theo độ tin cậy; review ≤ 60 giây/tài liệu | P0 |
| US-DC-007 | Là Admin, tôi muốn import danh sách nhân sự từ Excel | AI tự map cột; báo lỗi theo dòng; ghi dòng hợp lệ | P0 |
| US-DC-008 | Là Admin, tôi muốn cấu hình loại tài liệu, schema và ngưỡng tự ghi | Thêm loại mới không cần code; ngưỡng theo trường | P0 |
| US-DC-009 | Là Finance, tôi muốn chụp hoặc tải hóa đơn để AI ghi chi phí và công nợ | Tổng tiền khớp; phát hiện hóa đơn trùng; trường tiền luôn qua review | P1 |
| US-DC-010 | Là Legal/Sales, tôi muốn tải hợp đồng để AI trích giá trị, mốc thanh toán, hạn gia hạn | Tạo mốc và nhắc việc; gắn hợp đồng với khách hàng/đối tác | P1 |
| US-DC-011 | Là CEO, tôi muốn mọi con số AI báo cáo đều bấm vào xem được nguồn gốc | Lineage tới bản ghi và trang tài liệu | P0 |
| US-DC-012 | Là bộ phận, tôi muốn chuyển tiếp email có file đính kèm vào hệ thống | File tự vào hàng xử lý đúng phòng ban | P1 |

### 5.2. Use case mới

**UC-06 — Từ biên bản họp giấy đến thực thi.** Thư ký chụp biên bản giao ban viết tay hoặc tải file Word → AI nhận dạng là biên bản họp → trích 4 quyết định và 7 việc cần làm → khớp tên người với danh bạ nhân sự → thư ký duyệt → AI tạo task, đồng bộ lịch, gửi thông báo → Decision Log cập nhật. Đây là phiên bản không phụ thuộc Google Meet của UC-02, dùng được ngay từ ngày đầu.

**UC-07 — Onboarding doanh nghiệp trong một ngày.** Admin tải sơ đồ tổ chức (ảnh hoặc PDF), danh sách nhân sự (Excel), kế hoạch năm và bộ KPI (Word/Excel) → AI dựng cây tổ chức, hồ sơ nhân sự, cây mục tiêu → Admin duyệt từng phần → CEO có dashboard đầu tiên trong ngày. Use case này quyết định tốc độ bán hàng và time-to-value của sản phẩm.

**UC-08 — Hóa đơn đến cảnh báo dòng tiền.** NCC gửi email hóa đơn → AI đọc XML/PDF → kiểm tra trùng và khớp PO → Finance duyệt → ghi công nợ phải trả → cập nhật dự báo dòng tiền → nếu runway giảm dưới ngưỡng, đưa vào CEO Briefing.

### 5.3. NFR và chỉ số bổ sung

| Hạng mục | Yêu cầu |
| --- | --- |
| Hiệu năng xử lý tài liệu | Tài liệu ≤ 5 trang: kết quả trích xuất p95 ≤ 60 giây; xử lý bất đồng bộ, có thông báo khi xong |
| Thông lượng | ≥ 1.000 trang/giờ/tenant ở MVP, mở rộng ngang |
| Phục hồi | RPO ≤ 15 phút, RTO ≤ 4 giờ cho core platform |
| Lưu trữ dữ liệu | Cấu hình được vùng lưu trữ; tùy chọn lưu trữ và xử lý tại Việt Nam |
| Ngôn ngữ | Giao diện và AI tiếng Việt, tiếng Anh; AI hiểu câu hỏi trộn hai ngôn ngữ |
| Mobile | Chụp tài liệu, duyệt, check-in, hỏi AI trên mobile (PWA hoặc app) |
| Khả dụng AI | Khi model chính lỗi, tự chuyển model dự phòng; nhập liệu thủ công luôn hoạt động kể cả khi AI lỗi |
| Adoption | WAU/tổng user ≥ 70%; % KPI cập nhật đúng hạn ≥ 90%; % dữ liệu vào qua AI capture |
| Giá trị cho CEO | Giờ/tuần CEO tiết kiệm cho tổng hợp báo cáo (mục tiêu ≥ 5 giờ); thời gian từ phát hiện rủi ro đến hành động |

**Change management (mới):** mỗi phòng ban có một "AI champion"; chương trình đào tạo 2 giờ cho nhân viên; giai đoạn chạy song song với Excel tối đa 4 tuần, sau đó AI-EOS là nguồn duy nhất cho KPI/OKR và task. Quyết định này cần CEO công bố, không phải bộ phận IT.

## 6. Cập nhật MVP, ưu tiên và câu hỏi mở

MVP nên thu hẹp về một lời hứa duy nhất: **"CEO biết công ty đang đạt mục tiêu đến đâu, vì sao, và giao việc được ngay — với dữ liệu nhập vào dễ như gửi một file"**. Data Capture lên P0 vì không có nó thì mọi P0 khác thiếu dữ liệu.

### 6.1. Điều chỉnh ma trận ưu tiên (mục 87)

| Năng lực | v1.0 | v1.1 đề xuất | Lý do |
| --- | --- | --- | --- |
| Data Capture: nhập tay, nhập NL, upload PDF/Word/ảnh/Excel, review | Không có | P0 | Nguồn dữ liệu cho toàn bộ MVP |
| Data Foundation cơ bản (master data, freshness, lineage) | Không có | P0 | Điều kiện để AI đáng tin |
| AI Autonomy Levels L0–L3 + kill switch | Không có | P0 | Kiểm soát rủi ro từ ngày đầu |
| Finance Lite (doanh thu, chi phí, tiền mặt, runway — nhập tay hoặc import) | P1 | P0 | MVP Success Criteria (mục 88) cần Finance; giải quyết mâu thuẫn G10 |
| Sales Pipeline Lite | P1 | P0 | Như trên; CEO luôn hỏi pipeline |
| Meeting: AI join Google Meet | P0 | P1 | Phức tạp kỹ thuật và pháp lý; UC-06 (tải biên bản/transcript) thay thế ở MVP |
| Performance Cycle đầy đủ (self-assessment, calibration) | P0 | P1 | MVP giữ KPI/OKR + check-in; đánh giá nhân sự cần chính sách HR rõ trước |
| Risk Intelligence | P1 | P1 | Giữ; dùng ngưỡng chỉ số sức khỏe (4.3) làm bản đầu |
| Hóa đơn, hợp đồng, email capture, XML hóa đơn | — | P1 | Phase 2 cùng Finance đầy đủ |
| Procurement / Vendor, Workflow Engine | Không có | P1 | Phục vụ kiểm soát chi phí |
| Governance | P2 | P2 | Giữ |
