# 02 — Personas & Permissions

> Định nghĩa 5 vai trò (ROLE-01..ROLE-05) của Aureon Demo, ma trận quyền, quy tắc data scoping và cơ chế chuyển vai trò demo.
> Nguồn: `01-PROJECT-OVERVIEW.md` §2.3, §3, §4, §5, §6, §7.
> File này là nguồn chuẩn cho mọi task **Code auth** (xem Doc Loading Matrix trong `CLAUDE.md`). Backend enforce bằng `Depends(require_role(...))`; frontend chỉ ẩn/hiện UI, **không** là lớp bảo vệ.

---

## 1. Tổng quan vai trò

| Role | ID | Mục tiêu | Dashboard chính | Loại người dùng |
|---|---|---|---|---|
| **CEO** | ROLE-01 | Biết ngay, quyết nhanh | Toàn bộ 4 trụ | Ra quyết định |
| **CFO** | ROLE-02 | Kiểm soát tài chính | Tài chính + Vận hành | Ra quyết định + duyệt IDP tài chính |
| **Sales Director** | ROLE-03 | Giữ pipeline, doanh thu | Khách hàng + doanh thu | Ra quyết định (khối kinh doanh) |
| **HR Manager** | ROLE-04 | Giữ người, đo năng suất | Con người | Ra quyết định + duyệt IDP nhân sự |
| **Reviewer** | ROLE-05 | Duyệt nhanh, không sai | Hàng chờ IDP | Vận hành IDP |

Nguyên tắc chung:
- Mỗi user demo có **đúng 1 role active** tại một thời điểm.
- Quyền được xác định **chỉ** bởi role active (RBAC thuần, không có quyền gán riêng theo user trong MVP).
- Mọi con số hiển thị cho role nào thì role đó phải drill-down được đến nguồn trong phạm vi scope của mình (P01 — Every number traceable), trừ các giới hạn PII ở §4.3.

---

## 2. Chi tiết persona

### 2.1. ROLE-01 — CEO

| Thuộc tính | Nội dung |
|---|---|
| Đại diện tại ABC | Giám đốc điều hành Công ty TNHH TM&DV ABC |
| Mục tiêu | **Biết ngay, quyết nhanh** — có bức tranh tổng thể về sức khỏe doanh nghiệp |
| Dashboard chính | Toàn bộ 4 trụ: Tài chính, Khách hàng, Vận hành, Con người |
| Pain point | Mỗi phòng báo một kiểu; số liệu rải rác ở Excel/PDF/Zalo; quyết định dựa trên cảm tính, không có nguồn; mất thời gian chờ tổng hợp |
| Jobs-to-be-done | (1) Buổi sáng mở app, trong ≤ 10 giây biết việc cần quyết và rủi ro mới; (2) Click vào cảnh báo để hiểu nguyên nhân + nguồn; (3) Drill-down từ số đến tài liệu gốc để tin con số; (4) Theo dõi các quyết định đã giao có được thực thi không |
| KPI quan tâm | Toàn bộ metric 4 trụ (`METRIC-FIN-*`, `METRIC-CUS-*`, `METRIC-OPS-*`, `METRIC-HR-*`) và toàn bộ `ALERT-*`; đặc biệt: doanh thu, cash runway, pipeline coverage, dự án trễ, tỷ lệ nghỉ việc |
| KPI demo liên quan | Thời gian đến insight đầu tiên ≤ 10 giây; drill-down ≤ 3 click |
| Hành động chính | Xem, drill-down, xác nhận/bỏ qua alert, upload tài liệu (luồng "Nạp doanh nghiệp" UC-07), xem audit log |

### 2.2. ROLE-02 — CFO

| Thuộc tính | Nội dung |
|---|---|
| Đại diện tại ABC | Giám đốc tài chính / Kế toán trưởng |
| Mục tiêu | **Kiểm soát tài chính** — dòng tiền, công nợ, ngân sách luôn trong ngưỡng |
| Dashboard chính | Tài chính + Vận hành |
| Pain point | Phải tự đối chiếu báo cáo tài chính với danh sách hóa đơn thủ công; công nợ quá hạn phát hiện muộn; chênh ngân sách chỉ biết khi chốt kỳ; nhập liệu lặp lại dễ sai |
| Jobs-to-be-done | (1) Theo dõi cash runway, DSO, công nợ quá hạn hằng ngày; (2) Xem chi tiết chênh ngân sách và nguyên nhân (theo luồng demo bước 3); (3) Duyệt kết quả trích xuất tài liệu tài chính (báo cáo tài chính, hóa đơn) trước khi vào metric; (4) Kiểm tra workload/tiến độ vận hành ảnh hưởng chi phí |
| KPI quan tâm | 6 metric trụ Tài chính (`METRIC-FIN-*`: doanh thu, biên LN gộp, cash runway, DSO, công nợ quá hạn, chênh ngân sách); 4 metric trụ Vận hành (`METRIC-OPS-*`); alert tương ứng `ALERT-FIN-*`, `ALERT-OPS-*` |
| Hành động chính | Xem + quản lý alert trụ Tài chính; xem trụ Vận hành; upload tài liệu; duyệt/sửa/từ chối extraction thuộc trụ Tài chính |

### 2.3. ROLE-03 — Sales Director

| Thuộc tính | Nội dung |
|---|---|
| Đại diện tại ABC | Giám đốc kinh doanh |
| Mục tiêu | **Giữ pipeline, doanh thu** — đủ cơ hội để đạt chỉ tiêu, không phụ thuộc vài khách lớn |
| Dashboard chính | Khách hàng + doanh thu |
| Pain point | Báo cáo sales tổng hợp tay từ nhiều file; không thấy sớm rủi ro tập trung doanh thu; hợp đồng nằm trong PDF scan khó tra cứu; không liên kết được doanh thu thực với pipeline |
| Jobs-to-be-done | (1) Theo dõi pipeline coverage và tỷ lệ chuyển đổi; (2) Phát hiện khách hàng chiếm tỷ trọng doanh thu quá cao; (3) Drill-down từ doanh thu đến báo cáo sales/hợp đồng gốc; (4) Upload báo cáo sales, hợp đồng để cập nhật số liệu |
| KPI quan tâm | 5 metric trụ Khách hàng (`METRIC-CUS-*`: pipeline coverage, tỷ lệ chuyển đổi, NRR, tập trung doanh thu, NPS); metric doanh thu thuộc trụ Tài chính (chỉ metric doanh thu, xem §4.2); alert `ALERT-CUS-*` |
| Hành động chính | Xem + quản lý alert trụ Khách hàng; xem metric doanh thu; upload tài liệu |

### 2.4. ROLE-04 — HR Manager

| Thuộc tính | Nội dung |
|---|---|
| Đại diện tại ABC | Trưởng phòng Nhân sự (quản lý 45 nhân sự) |
| Mục tiêu | **Giữ người, đo năng suất** — giảm nghỉ việc, phát hiện quá tải sớm |
| Dashboard chính | Con người |
| Pain point | Danh sách nhân sự và KPI/OKR nằm trong Excel/Word rời rạc; phát hiện quá tải khi đã muộn; khó gắn năng suất (doanh thu/nhân sự) với dữ liệu tài chính |
| Jobs-to-be-done | (1) Theo dõi tỷ lệ nghỉ việc, quá tải, doanh thu/nhân sự; (2) Xem workload trụ Vận hành để phát hiện người quá tải; (3) Duyệt trích xuất danh sách nhân sự, bảng KPI/OKR; (4) Bảo vệ dữ liệu cá nhân nhân viên (NĐ 13/2023) |
| KPI quan tâm | 3 metric trụ Con người (`METRIC-HR-*`: doanh thu/nhân sự, tỷ lệ nghỉ việc, quá tải); metric workload trụ Vận hành; alert `ALERT-HR-*` |
| Hành động chính | Xem + quản lý alert trụ Con người; xem Vận hành; upload tài liệu; duyệt/sửa/từ chối extraction thuộc trụ Con người |

### 2.5. ROLE-05 — Reviewer

| Thuộc tính | Nội dung |
|---|---|
| Đại diện tại ABC | Nhân viên vận hành dữ liệu / kế toán viên được giao duyệt kết quả AI |
| Mục tiêu | **Duyệt nhanh, không sai** |
| Dashboard chính | Hàng chờ IDP (review queue) — không có dashboard 4 trụ |
| Pain point | Phải so từng trường với tài liệu gốc; không biết trường nào AI không chắc; sửa xong không biết dữ liệu đi đâu |
| Jobs-to-be-done | (1) Mở hàng chờ, ưu tiên tài liệu có field confidence thấp; (2) So sánh field trích xuất với vị trí nguồn (`source_location`) trên tài liệu; (3) Sửa field sai, duyệt hoặc từ chối; (4) Sau khi duyệt, thấy dữ liệu đã ghi vào metric/entity nào |
| KPI quan tâm | Review 1 tài liệu (6 trường) ≤ 60 giây; field accuracy ≥ 90%; straight-through rate; số tài liệu tồn trong hàng chờ |
| Hành động chính | Upload tài liệu; xem hàng chờ; duyệt/sửa/từ chối mọi loại tài liệu MVP; xem tài liệu gốc trong ngữ cảnh review |

---

## 3. Ma trận quyền

### 3.1. Định nghĩa mức quyền

| Mức | Ký hiệu | Ý nghĩa |
|---|---|---|
| **none** | — | Không thấy trong UI; API trả lỗi quyền (403) |
| **view** | V | Xem dữ liệu, biểu đồ, drill-down trong phạm vi scope |
| **view-agg** | VA | Chỉ xem số tổng hợp (không xem bản ghi cá nhân/chi tiết nhạy cảm) |
| **edit** | E | view + thao tác thay đổi trạng thái (ví dụ: acknowledge/dismiss alert, upload, sửa field extraction) |
| **approve** | A | edit + duyệt cuối, kích hoạt ghi dữ liệu (commit qua Action Registry) |

Mức quyền tăng dần: none < view-agg < view < edit < approve.

### 3.2. Ma trận role × dashboard 4 trụ

| Trụ dashboard | ROLE-01 CEO | ROLE-02 CFO | ROLE-03 Sales Dir | ROLE-04 HR Mgr | ROLE-05 Reviewer |
|---|---|---|---|---|---|
| Tài chính (`METRIC-FIN-*`) | V | V | V (chỉ metric doanh thu) | VA (chỉ doanh thu tổng — phục vụ doanh thu/nhân sự) | — |
| Khách hàng (`METRIC-CUS-*`) | V | VA | V | — | — |
| Vận hành (`METRIC-OPS-*`) | V | V | VA | V | — |
| Con người (`METRIC-HR-*`) | V | VA (tổng chi phí nhân sự, không xem lương cá nhân) | — | V | — |

### 3.3. Ma trận role × metric / alert

| Hành động | ROLE-01 CEO | ROLE-02 CFO | ROLE-03 Sales Dir | ROLE-04 HR Mgr | ROLE-05 Reviewer |
|---|---|---|---|---|---|
| Xem metric (trong scope §3.2) | V | V | V | V | — |
| Xem công thức / nguồn / thời điểm cập nhật metric (P01) | V | V | V | V | — |
| Xem alert | V (tất cả `ALERT-*`) | V (`ALERT-FIN-*`, `ALERT-OPS-*`) | V (`ALERT-CUS-*`) | V (`ALERT-HR-*`) | — |
| Acknowledge / dismiss alert | E (tất cả) | E (`ALERT-FIN-*`) | E (`ALERT-CUS-*`) | E (`ALERT-HR-*`) | — |
| Sửa định nghĩa metric / ngưỡng alert | — | — | — | — | — |

> Định nghĩa metric và ngưỡng alert là cấu hình seed, không role nào sửa qua UI trong MVP (xem `03-DASHBOARD-SPEC.md`).

### 3.4. Ma trận role × IDP

| Hành động IDP | ROLE-01 CEO | ROLE-02 CFO | ROLE-03 Sales Dir | ROLE-04 HR Mgr | ROLE-05 Reviewer |
|---|---|---|---|---|---|
| Upload tài liệu / nhập liệu (kênh C1–C5) | E | E | E | E | E |
| Luồng "Nạp doanh nghiệp từ tập tài liệu" (UC-07) | E | — | — | — | E |
| Xem trạng thái tài liệu đã upload | V (tất cả) | V (tài liệu trụ Tài chính + của mình) | V (tài liệu của mình) | V (tài liệu trụ Con người + của mình) | V (tất cả) |
| Xem hàng chờ review | V (tất cả, field lương cá nhân bị che — §4.3) | V (trụ Tài chính) | — | V (trụ Con người) | V (tất cả) |
| Xem field extraction chứa lương cá nhân (tài liệu #6, hoặc tài liệu bất kỳ có field được gắn nhãn lương) | — (che `••••`) | — | — | V | V (chỉ khi review tài liệu đó) |
| Sửa field extraction | — | E (trụ Tài chính) | — | E (trụ Con người) | E (tất cả) |
| Duyệt / từ chối extraction | — | A (trụ Tài chính) | — | A (trụ Con người) | A (tất cả) |
| Commit vào metric/entity (qua Action Registry) | — | A (trụ Tài chính) | — | A (trụ Con người) | A (tất cả) |
| Hoàn tác hành động AI L3 trên tài liệu | — | A (trụ Tài chính) | — | A (trụ Con người) | A (tất cả) |
| Sửa Extraction Schema | — | — | — | — | — |

Ghi chú:
- **Commit không tách rời duyệt**: thao tác "Duyệt" của role có quyền A sẽ kích hoạt commit qua Action Registry; không có đường ghi trực tiếp vào DB (xem `CLAUDE.md` § IDP Worker).
- Phân trụ của tài liệu theo bảng 7 loại tài liệu mẫu (`01-PROJECT-OVERVIEW.md` §8): #1, #2 → Tài chính; #3, #4 → Khách hàng; #5 → Vận hành; #6 → Con người; #7 (KPI/OKR) → cả 4 trụ.
- Tài liệu trụ Khách hàng, Vận hành và tài liệu #7 chỉ do **ROLE-05** duyệt trong MVP.
- Tài liệu straight-through (không cần review) vẫn ghi audit log với actor là hệ thống.
- **Hàng chờ và extraction view với tài liệu chứa lương cá nhân**: CEO chỉ thấy metadata (loại tài liệu, trạng thái, người upload, thời điểm, số field, confidence trung bình). Giá trị field lương hiển thị `••••` và không có nút mở file gốc. API không trả giá trị field này (§4.1 mục 6).

### 3.5. Ma trận role × drill-down tài liệu gốc

| Hành động | ROLE-01 CEO | ROLE-02 CFO | ROLE-03 Sales Dir | ROLE-04 HR Mgr | ROLE-05 Reviewer |
|---|---|---|---|---|---|
| Drill-down số → chi tiết → bản ghi gốc | V (4 trụ) | V (Tài chính, Vận hành) | V (Khách hàng, metric doanh thu) | V (Con người, Vận hành) | — |
| Mở tài liệu gốc (file + vị trí trích xuất) | V (4 trụ), **trừ tài liệu chứa lương cá nhân → none** | V (Tài chính, Vận hành) | V (Khách hàng, metric doanh thu) | V (Con người, Vận hành; gồm cả #6) | V (chỉ trong ngữ cảnh review) |
| Tải xuống tài liệu gốc | V, **trừ tài liệu chứa lương cá nhân → none** | V (trong scope) | V (trong scope) | V (trong scope; gồm cả #6) | — |
| Mở/tải tài liệu chứa lương cá nhân (#6 Danh sách nhân sự, hoặc tài liệu bất kỳ có field lương) | — | — | — | V | V (chỉ mở trong ngữ cảnh review, không tải xuống) |

> Khi CEO drill-down metric trụ Con người (ví dụ doanh thu/nhân sự) và nguồn là tài liệu #6, chuỗi drill-down dừng ở **bản ghi tổng hợp** (công thức, số nhân sự, thời điểm cập nhật, tên tài liệu nguồn). Link mở file gốc hiển thị "Tài liệu chứa dữ liệu lương cá nhân — chỉ HR Manager được mở". P01 vẫn được giữ: con số có nguồn rõ ràng, chỉ file gốc bị chặn quyền (§4.1 mục 4).

### 3.6. Ma trận role × chuyển vai trò demo, admin/audit

| Hành động | ROLE-01 CEO | ROLE-02 CFO | ROLE-03 Sales Dir | ROLE-04 HR Mgr | ROLE-05 Reviewer |
|---|---|---|---|---|---|
| Chuyển vai trò demo (role switcher) | E | E | E | E | E |
| Xem audit log | V | — | — | — | — |
| Quản lý user / gán role | — | — | — | — | — |
| Sửa cấu hình hệ thống (metric, alert, schema) | — | — | — | — | — |

> MVP **không có role Admin**. User, role, metric, alert, Extraction Schema được tạo bằng seed (`08-DEMO-DATA-SPEC.md`) và migration; không có UI quản trị.

### 3.7. Tóm tắt nhanh (role × nhóm chức năng)

| Nhóm chức năng | ROLE-01 CEO | ROLE-02 CFO | ROLE-03 Sales Dir | ROLE-04 HR Mgr | ROLE-05 Reviewer |
|---|---|---|---|---|---|
| Dashboard Tài chính | view | view | view (doanh thu) | view-agg | none |
| Dashboard Khách hàng | view | view-agg | view | none | none |
| Dashboard Vận hành | view | view | view-agg | view | none |
| Dashboard Con người | view | view-agg | none | view | none |
| Metric / alert | edit (alert) | edit (alert FIN) | edit (alert CUS) | edit (alert HR) | none |
| IDP upload | edit | edit | edit | edit | edit |
| IDP UC-07 "Nạp doanh nghiệp" | edit | none | none | none | edit |
| IDP review | view (field lương bị che) | approve (FIN) | none | approve (HR) | approve (all) |
| IDP commit | none | approve (FIN) | none | approve (HR) | approve (all) |
| Drill-down tài liệu gốc | view (4 trụ, trừ tài liệu chứa lương cá nhân) | view (FIN, OPS) | view (CUS, doanh thu) | view (HR, OPS, gồm #6) | view (review) |
| Tài liệu/field lương cá nhân | none | none | none | view | view (review) |
| Chuyển vai trò demo | edit | edit | edit | edit | edit |
| Admin / audit | view (audit) | none | none | none | none |

---

## 4. Quy tắc data scoping theo role

### 4.1. Nguyên tắc chung

1. **Enforce ở backend**: mọi endpoint (trừ health check) có `Depends(require_role(...))`; truy vấn metric, alert, tài liệu, extraction được lọc theo scope của role active trước khi trả về. Frontend ẩn UI chỉ là UX.
2. **Default deny**: tài nguyên không được liệt kê trong §3 → mức `none`.
3. **Scope theo trụ**: mỗi metric, alert, tài liệu nguồn và extraction gắn với 1 hoặc nhiều trụ (FIN/CUS/OPS/HR). Role được truy cập tài nguyên nếu có ít nhất một trụ trong scope; tài liệu đa trụ (#7 KPI/OKR) chỉ hiển thị phần field thuộc trụ trong scope.
4. **Lineage nhất quán với scope**: drill-down không được dẫn ra ngoài scope. Nếu bản ghi gốc thuộc trụ ngoài scope, UI hiển thị "Nguồn thuộc phạm vi khác — không có quyền xem" thay vì ẩn im lặng (giữ P01: con số vẫn có nguồn, chỉ bị chặn quyền).
5. **Tổng hợp an toàn (view-agg)**: role có mức `view-agg` chỉ nhận giá trị tổng hợp; API không trả bản ghi chi tiết, danh sách cá nhân hoặc link tài liệu gốc cho trụ đó.
6. **Response model tường minh**: field nhạy cảm (lương, thông tin cá nhân) không nằm trong response model của role không có quyền (tránh leak qua `response_model`).

### 4.2. Scope cụ thể theo role

| Role | Trụ trong scope (view) | Trụ view-agg | Ngoài scope | Ghi chú |
|---|---|---|---|---|
| ROLE-01 CEO | FIN, CUS, OPS, HR | Lương cá nhân (chỉ tổng hợp) | File gốc tài liệu chứa lương cá nhân | Field lương bị che; không mở/tải tài liệu #6 (§4.3) |
| ROLE-02 CFO | FIN, OPS | CUS, HR | — | HR: chỉ tổng chi phí nhân sự/quỹ lương, không lương cá nhân |
| ROLE-03 Sales Director | CUS, metric doanh thu (FIN) | OPS | HR, FIN ngoài doanh thu | Không xem biên LN, cash, công nợ, ngân sách |
| ROLE-04 HR Manager | HR, OPS | FIN (chỉ doanh thu tổng) | CUS | Doanh thu tổng dùng để tính doanh thu/nhân sự |
| ROLE-05 Reviewer | Hàng chờ IDP | — | Toàn bộ dashboard 4 trụ | Thấy tài liệu + field extraction chỉ trong ngữ cảnh review |

### 4.3. Dữ liệu cá nhân (NĐ 13/2023/NĐ-CP)

- Dữ liệu cá nhân trong danh sách nhân sự (#6) và biên bản họp (#5): họ tên, lương, số điện thoại, CCCD, địa chỉ.
- **Tài liệu chứa lương cá nhân** = tài liệu #6 (Danh sách nhân sự) và mọi tài liệu khác có ít nhất một field extraction được gắn nhãn lương cá nhân. Nhãn này lưu ở cấp tài liệu/field (cấu trúc ở `05-DATA-MODEL.md`).
- **Lương cá nhân — quyền chi tiết** chỉ có ở:
  - ROLE-04 (HR Manager): xem field lương, mở và tải file gốc.
  - ROLE-05 (Reviewer): xem field lương và mở file gốc **chỉ trong ngữ cảnh review** tài liệu đó; không tải xuống.
- **ROLE-01 (CEO) và ROLE-02 (CFO) chỉ có `view-agg` với lương** (tổng quỹ lương, chi phí nhân sự):
  - **Không** được mở hoặc tải file gốc của tài liệu chứa lương cá nhân, kể cả qua drill-down (§3.5).
  - Trong hàng chờ IDP và extraction view, field lương hiển thị `••••`; API không trả giá trị (loại khỏi response model, không chỉ che ở frontend).
  - ROLE-02 không có tài liệu #6 trong hàng chờ (ngoài scope FIN), nên quy tắc trên áp dụng khi CFO gặp field lương qua bất kỳ đường nào khác.
- ROLE-03 (Sales Director): none với mọi dữ liệu lương.
- Họ tên nhân sự được hiển thị cho role có scope OPS/HR (phục vụ workload, quá tải).
- Mọi lượt mở tài liệu gốc chứa dữ liệu cá nhân được ghi audit log; mọi lần bị từ chối mở tài liệu chứa lương cũng ghi audit log.
- Dữ liệu demo là dữ liệu giả định của công ty ABC, nhưng quy tắc vẫn áp dụng để mô phỏng đúng sản phẩm.

### 4.4. Audit log

Ghi audit log cho: mọi mutation (upload, sửa field, duyệt, từ chối, commit, hoàn tác, acknowledge/dismiss alert), mỗi lần chuyển vai trò demo, mỗi lần mở tài liệu gốc chứa PII. Mỗi bản ghi tối thiểu gồm: actor (user), role active, hành động, đối tượng, thời điểm. Cấu trúc chi tiết ở `05-DATA-MODEL.md`.

---

## 5. Cơ chế chuyển vai trò demo

### 5.1. Mô tả

- **Vị trí**: dropdown ở góc phải thanh trên (top bar), hiển thị role active (tên + ID).
- **Hành vi**: chọn role → dashboard tải lại theo role mới → điều hướng về dashboard chính của role (ROLE-05 → hàng chờ IDP).
- **Không cần logout/login lại**.
- **Chỉ phục vụ demo**: đây không phải tính năng sản phẩm; chỉ bật trong môi trường demo bằng cờ cấu hình (đặt tên/vị trí cờ theo `07-TECH-ARCHITECTURE.md`). Khi tắt cờ, dropdown không hiển thị và backend từ chối yêu cầu chuyển vai trò.
- Phục vụ kịch bản demo 15 phút (`01-PROJECT-OVERVIEW.md` §11), bước 3: "Chuyển vai CFO → dashboard đổi". Mapping đầy đủ các bước ở §5.3.

### 5.2. Quy tắc

| # | Quy tắc |
|---|---|
| R1 | **KPI: chuyển vai trò dashboard ≤ 2 giây** — đo từ lúc chọn role trong dropdown đến khi dashboard của role mới render xong số liệu chính (above the fold); đo bằng log UI (`01-PROJECT-OVERVIEW.md` §4) |
| R2 | Role mới phải được **xác lập ở backend** (session/JWT mang claim role mới qua NextAuth + JWT); không chỉ đổi state ở client. Endpoint cụ thể do `10-API-SPECIFICATION.md` định nghĩa |
| R3 | Sau khi chuyển, **xóa toàn bộ cache dữ liệu client** (TanStack Query cache) của role cũ để không rò dữ liệu ngoài scope |
| R4 | Mỗi lần chuyển ghi **audit log** (role cũ → role mới, thời điểm) |
| R5 | Danh sách role trong dropdown cố định 5 role ROLE-01..ROLE-05, tương ứng 5 user demo được seed (`08-DEMO-DATA-SPEC.md`) |
| R6 | Nếu chuyển thất bại (lỗi mạng/timeout), giữ nguyên role cũ, hiển thị thông báo lỗi; không để UI ở trạng thái lẫn lộn 2 role |
| R7 | Thao tác đang dở (ví dụ form review chưa lưu) → hỏi xác nhận trước khi chuyển |
| R8 | Để đạt ≤ 2 giây: dashboard của mỗi role đọc metric đã tính sẵn (không tính lại khi chuyển); có thể prefetch dữ liệu role đích sau khi xác lập role mới — chi tiết kỹ thuật ở `06-UI-UX-SPEC.md` / `07-TECH-ARCHITECTURE.md` |

### 5.3. Mapping kịch bản demo 15 phút → role active

Kịch bản theo `01-PROJECT-OVERVIEW.md` §11. Mỗi bước đều khả thi theo ma trận §3 **mà không cần điều chỉnh ma trận**. Không cấp UC-07 cho CFO, vì luồng "Nạp doanh nghiệp" nạp cả 4 trụ, vượt scope FIN/OPS của CFO.

| Bước | Thời lượng | Hành động demo | Role active | Chuyển vai? | Quyền cho phép (tham chiếu §3) |
|---|---|---|---|---|---|
| 1 | 2' | CEO mở app buổi sáng → thấy 2 việc cần quyết, 1 rủi ro mới | ROLE-01 CEO | Bắt đầu với CEO | §3.2 view 4 trụ; §3.3 xem tất cả `ALERT-*` |
| 2 | 2' | Click cảnh báo doanh thu → xem nguyên nhân + nguồn | ROLE-01 CEO | Không | §3.3 xem alert + công thức/nguồn; §3.5 drill-down FIN (tài liệu #1, #2 không chứa lương → mở được) |
| 3 | 2' | Chuyển vai CFO → dashboard đổi → xem chi tiết ngân sách | ROLE-02 CFO | CEO → CFO (≤ 2 giây, §5.2 R1) | §3.2 view FIN + OPS; §3.5 drill-down FIN |
| 4 | 5' | Vào "Nạp doanh nghiệp" → upload 7 tài liệu mẫu → AI xử lý | ROLE-01 CEO (phương án chính) | CFO → CEO | §3.4 UC-07: CEO = E. Phương án phụ: chuyển sang ROLE-05 (cũng có UC-07 = E) rồi giữ nguyên Reviewer cho bước 5 |
| 5 | 2' | Vào Review → duyệt 1 tài liệu → thấy dữ liệu vào hệ thống | ROLE-05 Reviewer (phương án chính) | CEO → Reviewer | §3.4 duyệt + commit tất cả = A. Phương án phụ: ROLE-02 CFO duyệt tài liệu FIN (#1 hoặc #2), A (trụ Tài chính). **Không** chọn tài liệu #6 khi demo để tránh lộ lương trên màn chiếu |
| 6 | 2' | Quay lại CEO dashboard → thấy dữ liệu mới + drill-down đến tài liệu gốc | ROLE-01 CEO | Reviewer/CFO → CEO | §3.2 view; §3.5 drill-down. Nên drill-down đến tài liệu FIN/CUS vừa duyệt; nếu nguồn là #6 thì dừng ở bản ghi tổng hợp (§3.5) |

Ghi chú:
- Tổng cộng 4 lần chuyển vai trò (bước 3, 4, 5, 6). Mỗi lần ≤ 2 giây và ghi audit log (§5.2 R1, R4).
- CEO **không** duyệt ở bước 5 (§3.4: CEO không có quyền duyệt; xem OQ-2). Người trình diễn phải chuyển sang Reviewer hoặc CFO.

---

## 6. Ràng buộc scope MVP

- Chỉ 5 role cố định; không có role tùy biến, không phân quyền theo phòng ban/chi nhánh, không multi-tenant.
- Không có SSO, không có UI quản trị user/role.
- Không có quyền theo bản ghi riêng lẻ (row-level ownership) ngoài các quy tắc theo trụ ở §4.
- AI Autonomy chỉ L0–L3; hoàn tác (undo) hành động L3 thuộc quyền approve tương ứng ở §3.4.

---

## 7. Open questions

| # | Câu hỏi | Đề xuất mặc định | Ảnh hưởng |
|---|---|---|---|
| OQ-1 | Sales Director có được duyệt extraction tài liệu trụ Khách hàng (báo cáo sales, hợp đồng) không? Hiện chỉ ROLE-05 duyệt | Giữ: chỉ ROLE-05 duyệt trụ CUS/OPS trong MVP | §3.4, `04-IDP-FEATURE-SPEC.md` |
| OQ-2 | CEO có quyền duyệt extraction không? Hiện CEO chỉ view hàng chờ | Giữ: CEO không duyệt (tách người quyết và người nhập liệu) | §3.4 |
| OQ-3 | Mức `view-agg` (CFO xem CUS/HR, Sales xem OPS, HR xem doanh thu tổng) có cần không, hay đơn giản hóa thành `view`/`none`? | Giữ `view-agg` như §4.2 | §3.2, API response model |
| OQ-4 | Tài liệu #7 (KPI/OKR, đa trụ): duyệt theo field từng trụ bởi nhiều role hay chỉ ROLE-05 duyệt toàn bộ? | Chỉ ROLE-05 duyệt toàn bộ | §3.4, `04-IDP-FEATURE-SPEC.md` |
| OQ-5 | Ai được xem audit log ngoài CEO (ví dụ CFO cho hành động tài chính)? | Chỉ CEO trong MVP | §3.6 |
| OQ-6 | Cơ chế kỹ thuật chuyển vai trò: cấp lại JWT với claim role mới, hay 5 user demo riêng và chuyển session? Tên cờ cấu hình bật demo mode | Quyết trong `07-TECH-ARCHITECTURE.md` / `10-API-SPECIFICATION.md` | §5.2 R2 |
| OQ-7 | Định nghĩa đo KPI ≤ 2 giây: đến khi render số liệu chính hay đến khi render toàn bộ biểu đồ? | Số liệu chính above the fold | §5.2 R1, `14-TEST-TRACEABILITY.md` |

---

## 8. Liên kết

| Chủ đề | File |
|---|---|
| Tầm nhìn, scope, KPI | `01-PROJECT-OVERVIEW.md` |
| Metric, alert theo trụ | `03-DASHBOARD-SPEC.md` |
| Luồng IDP, review, commit | `04-IDP-FEATURE-SPEC.md` |
| Entity user/role/audit log | `05-DATA-MODEL.md` |
| Role switcher, màn hình theo role | `06-UI-UX-SPEC.md` |
| Auth, cờ demo mode | `07-TECH-ARCHITECTURE.md` |
| 5 user demo | `08-DEMO-DATA-SPEC.md` |
| Endpoint auth/role | `10-API-SPECIFICATION.md` |

---

## 9. Version

- **Version:** 1.0.0
- **Last updated:** 2026-10-17
- **Applies to:** Aureon Demo v1.0
- **Maintainer:** @CyEyes
