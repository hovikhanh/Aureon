# 13 — DECISION LOG

> Sổ quyết định của Aureon Demo. Đây là nguồn kiểm tra **Gate B** (`CLAUDE.md` § Gotchas): agent phải đọc file này trước mọi task. Nếu có DEC `open` + `blocking=true` ảnh hưởng task thì task `BLOCKED` và chờ human resolve.
> Nội dung gồm: (1) các quyết định thiết kế đã chốt trong spec 01–11 đã Approved; (2) mọi mục "Open questions" của 02–08, 10, 11 được chuyển thành DEC `open`; (3) chính sách routing model cho Agent Team và Model Routing Log.
> Agent **không** tự resolve DEC `open`. Cột "Đề xuất mặc định" chỉ là gợi ý của spec gốc để human chọn nhanh.

---

## 1. Quy ước

### 1.1. Schema một DEC

| Trường | Bắt buộc | Mô tả |
|---|---|---|
| `ID` | ✅ | `DEC-xxx` (3 chữ số, không tái sử dụng số đã cấp) |
| `Tiêu đề` | ✅ | Một dòng, nêu đúng câu hỏi/quyết định |
| `Bối cảnh` | ✅ | Vì sao cần quyết định; dẫn nguồn (file §, `OQ-xx` gốc) |
| `Lựa chọn` | ✅ | Các phương án (A/B/…) đã cân nhắc |
| `Quyết định` | ✅ | Phương án được chọn (DEC `resolved`) hoặc **đề xuất mặc định** (DEC `open`) |
| `Rationale` | ✅ | Lý do chọn; với DEC `open`: lý do đề xuất và hệ quả nếu chưa chốt |
| `Status` | ✅ | `open` \| `resolved` \| `superseded` (kèm `→ DEC-yyy` thay thế) |
| `Blocking` | ✅ | `true` \| `false` — `true` = task chịu ảnh hưởng không được bắt đầu khi DEC còn `open` |
| `Ảnh hưởng` | ✅ | File docs và nhóm task/màn hình/endpoint (`SCR-xx`, `EP-xx`, task trong 09) bị ảnh hưởng |
| `Ngày` | ✅ | Ngày raise (`open`) hoặc ngày resolve (`resolved`), ISO `yyyy-mm-dd` |
| `Người quyết` | ✅ | `@CyEyes` (human), hoặc "Spec Approved (reviewer)" khi quyết định nằm trong spec đã review; DEC `open` ghi `— (chờ human)` |

Để file gọn, các DEC được trình bày dạng bảng nhiều cột; mỗi dòng là một DEC đủ 11 trường trên. Hai cột "Ngày" và "Người quyết" được gộp vào cột cuối.

### 1.2. Quy tắc đánh giá `blocking`

| Đánh `blocking=true` khi | Đánh `blocking=false` khi |
|---|---|
| Spec mâu thuẫn nhau hoặc mâu thuẫn `CLAUDE.md` (bảng Escalation) | Đã có mặc định an toàn trong spec, đổi sau không phải sửa schema/API/stack |
| Cần đổi/thêm schema DB, API endpoint, stack hoặc dependency mới | Chỉ là giá trị cấu hình/seed, UX, chữ nghĩa |
| Quyết định phạm vi (scope) của một tính năng | Chỉ ảnh hưởng tài liệu, không ảnh hưởng code |
| Ảnh hưởng tính đúng của dữ liệu demo / test acceptance | Quy trình nội bộ của agent |

`blocking=true` chỉ chặn các task nằm trong cột "Ảnh hưởng", không chặn toàn dự án.

### 1.3. Dải số DEC

| Dải | Nhóm |
|---|---|
| DEC-001 → DEC-029 | Quyết định đã chốt (`resolved`) — stack, scope, quyền, IDP, dashboard, API, quy trình |
| DEC-030 → DEC-059 | Open — phạm vi, dữ liệu, IDP, dashboard (01–05, 08) |
| DEC-060 → DEC-079 | Open — kỹ thuật, kiến trúc (07) |
| DEC-080 → DEC-099 | Open — auth, API, UI/UX (02, 06, 10) |
| DEC-100 → DEC-119 | Open — governance, agent workflow (11, 12–14) |

---

## 2. Quy trình raise / resolve

### 2.1. Raise (agent hoặc human)

1. Agent phát hiện điểm cần quyết định (theo bảng Escalation `CLAUDE.md`): ghi vào mục "Open questions" của file spec đang viết **và** báo captain/maintainer. Agent không tự cấp số.
2. Maintainer file này (captain Agent Team hoặc @CyEyes) cấp số `DEC-xxx` kế tiếp trong dải phù hợp (§1.3) và thêm dòng `open` với đủ schema §1.1.
3. Đánh giá `blocking` theo §1.2. Nếu `true`: ghi rõ task/màn hình/endpoint bị chặn.
4. Spec nguồn giữ tham chiếu `OQ-xx` gốc; bảng §7 map `OQ-xx → DEC-xxx`.
5. Trường hợp phát hiện **credential bị lộ**: dừng task, raise DEC `blocking=true` ngay, thông báo human (không chờ cấp số theo lô).

### 2.2. Resolve (chỉ human)

1. Human chọn phương án (có thể là đề xuất mặc định), ghi `Quyết định`, `Rationale`, `Ngày`, `Người quyết`, đổi `Status → resolved`.
2. Nếu quyết định làm thay đổi spec: cập nhật file spec tương ứng (05 trước khi đổi schema, 10 trước khi đổi API) và bump version spec (chỉ human, `CLAUDE.md` § Cấm tự quyết #6).
3. Nếu quyết định thay một DEC cũ: DEC cũ đổi `superseded → DEC-yyy`, không xóa.
4. Cập nhật `12-DOC-AUDIT.md` (spec bị ảnh hưởng → kiểm tra lại `status`) và `14-TEST-TRACEABILITY.md` (test case mới nếu có).
5. Agent chỉ được dùng quyết định khi DEC đã `resolved`.

### 2.3. Gate B — cách agent kiểm tra

```
Với task T:
  lấy tập file/SCR/EP/nhóm task mà T chạm tới
  nếu tồn tại DEC có status=open AND blocking=true AND cột "Ảnh hưởng" giao với tập trên
      → BLOCKED (ghi DEC-xxx trong khối BLOCKED, 11 §6)
  ngược lại → Gate B đạt
```

---

## 3. Quyết định đã chốt (resolved)

Các quyết định dưới đây đã nằm trong `CLAUDE.md` v1.1.0 (hợp đồng do human duy trì) hoặc trong spec đã được review Approved. Agent được dùng ngay. Nếu muốn đổi, phải raise DEC mới và đánh dấu DEC cũ `superseded`.

### 3.1. Stack, phạm vi, kiến trúc

| ID | Tiêu đề | Bối cảnh | Lựa chọn | Quyết định | Rationale | Status | Blocking | Ảnh hưởng | Ngày · Người quyết |
|---|---|---|---|---|---|---|---|---|---|
| DEC-001 | Tech stack MVP | `CLAUDE.md` § Tech Stack, 07 §2 | A: theo bảng CLAUDE.md · B: stack khác | **A**: Next.js 14 + shadcn/ui, FastAPI (Python 3.12+, uv), PostgreSQL 16+ + pgvector 0.7+, SQLAlchemy 2.0 + Alembic, Celery + Redis, MinIO/S3, NextAuth + JWT, PaddleOCR, LlamaIndex, OmniRoute ModelGateway, Docker Compose | Stack là hợp đồng vận hành; mọi đổi stack phải có DEC (CLAUDE.md § Nguyên tắc) | resolved | false | 07, 09, mọi task code | 2026-10-17 · @CyEyes (CLAUDE.md v1.1.0) |
| DEC-002 | Queue: Celery + Redis (không ARQ) | 01 §9 ghi "Celery (hoặc ARQ)"; CLAUDE.md chỉ ghi Celery; 07 OQ-01 | A: Celery + Redis · B: ARQ | **A** | CLAUDE.md là nguồn stack chính thức; ARQ sẽ là đổi stack và cần DEC mới. Việc đồng bộ câu chữ 01 §9 xem DEC-060 | resolved | false | 07, IDP worker | 2026-10-17 · @CyEyes (CLAUDE.md) |
| DEC-003 | Phạm vi MVP | 01 §2–§3, CLAUDE.md § Project | — | Dashboard 4 trụ + IDP + 5 vai trò + 7 loại tài liệu mẫu; ngoài phạm vi: 21 domain còn lại, mobile, integration thật (MISA/Zalo/email), multi-tenant, billing, kênh C6–C10, autonomy L4 | Giữ demo 15 phút khả thi (01 §11) | resolved | false | Toàn bộ | 2026-10-17 · @CyEyes |
| DEC-004 | Single tenant — bỏ `tenant_id` | Stub 05 cũ có `tenant_id` trên `users` | A: giữ `tenant_id` · B: bỏ | **B** | Multi-tenant nằm ngoài phạm vi (DEC-003); bỏ cột thừa giúp query/scoping đơn giản | resolved | false | 05, 10 | 2026-10-17 · Spec Approved (05) |
| DEC-005 | Quy trình sinh tài liệu 4 phase | CLAUDE.md § Documentation Generation | — | Phase 1: 02–04 → Phase 2: 05–08, 10, 11 → Phase 3: 12–14 → Phase 4: 09; mỗi file sinh → review → repair đến Approved | Đúng thứ tự phụ thuộc; 09 chỉ sinh khi đã có đủ spec | resolved | false | 11, 12, 14, 09 | 2026-10-17 · @CyEyes |

### 3.2. Quyền và bảo mật

| ID | Tiêu đề | Bối cảnh | Lựa chọn | Quyết định | Rationale | Status | Blocking | Ảnh hưởng | Ngày · Người quyết |
|---|---|---|---|---|---|---|---|---|---|
| DEC-006 | Mô hình quyền 5 role × 5 mức | 02 §3–§4 | — | ROLE-01 CEO, ROLE-02 CFO, ROLE-03 Sales Director, ROLE-04 HR Manager, ROLE-05 Reviewer; mức `none / view-agg / view / edit / approve` theo trụ FIN/CUS/OPS/HR; enforce ở backend, default deny; không có Admin UI — user/role/metric/alert/schema/autonomy là **seed config** | Demo tập trung vào khác biệt dashboard theo role; không Admin giảm phạm vi | resolved | false | 02, 05, 06, 10, task auth | 2026-10-17 · Spec Approved (02, t29) |
| DEC-007 | Phân quyền duyệt / undo / UC-07 | 02 §3.4, 04 §8.2 | — | Duyệt + undo + retry/mở lại: Reviewer (mọi trụ), CFO (FIN), HR Manager (HR); CEO và Sales Director không duyệt, không undo; UC-07 chỉ CEO và Reviewer | Tách người ra quyết định và người nhập liệu; giữ đủ actor cho 6 bước demo (02 §5.3). Câu hỏi mở rộng xem DEC-041, DEC-042 | resolved | false | 02, 04, 10 (EP-28..35, EP-40..41) | 2026-10-17 · Spec Approved (02, 04) |
| DEC-008 | Dữ liệu lương cá nhân | 02 §3.4–3.5, §4.3; 04 §13.3 | — | "Tài liệu chứa lương cá nhân" = #6 và mọi tài liệu có field nhãn `sensitivity=salary`. CEO/CFO chỉ `view-agg`, không mở/tải file gốc, field hiển thị `••••` và **bị loại khỏi response API**; Reviewer chỉ xem trong ngữ cảnh review, không tải; HR Manager xem đầy đủ; mọi lần mở/bị từ chối đều ghi audit | Tuân thủ NĐ 13/2023 về dữ liệu cá nhân; chặn ở API, không chỉ ẩn ở UI | resolved | false | 02, 04, 05, 10, 14 | 2026-10-17 · Spec Approved (02 t29) |
| DEC-009 | Auth & API guard | CLAUDE.md § API, 10 §1 | — | NextAuth + JWT; mọi endpoint có `Depends(require_role(...))` (ngoại lệ public xem DEC-080); `response_model` Pydantic bắt buộc; mọi mutation ghi `ENT-AuditLog` (actor, active role, action, object, time) | Chống leak field (password_hash, salary) và đảm bảo truy vết | resolved | false | 07, 10, task auth/API | 2026-10-17 · @CyEyes (CLAUDE.md) |
| DEC-010 | Quy ước API chung | 10 §1 | — | Base `/api/v1`; envelope `{data, meta?}` / `{error:{code,message,details}}`; bảng error code 10 §1; phân trang `page/page_size/sort`; Idempotency-Key cho mutation; metric trả `value_state` OK / NO_DATA / NOT_COMPUTABLE khi mẫu số ≤ 0 | 10 là contract nguồn duy nhất cho FE/BE | resolved | false | 10, mọi task API/FE | 2026-10-17 · Spec Approved (10 t35) |

### 3.3. IDP, dữ liệu, dashboard

| ID | Tiêu đề | Bối cảnh | Lựa chọn | Quyết định | Rationale | Status | Blocking | Ảnh hưởng | Ngày · Người quyết |
|---|---|---|---|---|---|---|---|---|---|
| DEC-011 | Định dạng output extraction | CLAUDE.md § IDP Worker, 04 §5 | — | Mỗi field = `{value, confidence, source_location}`; `source_location.kind` ∈ manual / transcript / cell (sheet/row/col) / bbox (page) | P01: mọi số phải truy được về vị trí trong tài liệu gốc | resolved | false | 04, 05, 10 | 2026-10-17 · @CyEyes (CLAUDE.md) |
| DEC-012 | Commit chỉ qua Action Registry | CLAUDE.md, 04 §10 (FR-DC-17) | A: worker ghi DB trực tiếp · B: Action Registry | **B**: 8 action có idempotency key `hash(document_id, field_set_version, action_name)`, ghi audit, hỗ trợ undo | Ghi có kiểm soát, idempotent, hoàn tác được | resolved | false | 04, 05, 10 (EP-31) | 2026-10-17 · Spec Approved (04, 10) |
| DEC-013 | Mọi LLM call qua ModelGateway / OmniRoute; chống prompt injection | CLAUDE.md § IDP Worker, 04 PI-01..05 | — | Không gọi provider trực tiếp; nội dung tài liệu được bọc delimiter và coi là **data**; model trả `null` khi không tìm thấy | Kiểm soát chi phí/route; giảm rủi ro injection và hallucination | resolved | false | 04, 07, IDP worker | 2026-10-17 · @CyEyes (CLAUDE.md) |
| DEC-014 | Ngưỡng confidence & điều kiện STP (mặc định cấu hình được) | 04 §6–7 | — | Màu field: Cao ≥ 0,90 · Trung bình 0,70–<0,90 · Thấp < 0,70; phân loại < 0,80 → người chọn doc type; STP S1–S7 (gồm `classification_confidence ≥ 0,95`, field bắt buộc ≥ 0,90) | Dùng làm giá trị chạy demo; cấu hình theo doc type. **Việc business xác nhận con số vẫn mở ở DEC-033** | resolved | false | 04, 08, IDP worker | 2026-10-17 · Spec Approved (04 t31) |
| DEC-015 | Autonomy level mặc định | 04 §9, 02 §3.6 | — | L0–L3 trong MVP (L4 ngoài phạm vi); mặc định mọi doc type L2; `INVOICE`, `SALES_REPORT`, `KPI_OKR`, `MEETING_MINUTES` được nâng tối đa L3; `FINANCIAL_REPORT`, `CONTRACT`, `EMPLOYEE_LIST` tối đa L2; cấu hình bằng seed (không có UI chỉnh) | P02 AI hiện rõ trạng thái; tài liệu tài chính/pháp lý/cá nhân luôn cần người duyệt | resolved | false | 04, 06 (SCR-15 chỉ đọc), 08 | 2026-10-17 · Spec Approved (04 t31) |
| DEC-016 | Single-table `business_records` cho entity nghiệp vụ | 03 OQ-01, 04 OQ-01, 05 M1 | A: 11 bảng riêng (Invoice, Contract, …) · B: một bảng `business_records` + `record_type` | **B** — 12 entity vật lý; `ENT-Invoice`, `ENT-Contract`… ở 03/04 là tên logic = `business_records WHERE record_type=…`; bỏ ENT-Permission (M2) | MVP ít bản ghi; lineage/undo/soft delete đồng nhất; SQLAlchemy `polymorphic_on`. Các câu hỏi phụ còn mở: DEC-037, DEC-038 | resolved | false | 03, 04, 05, 10 | 2026-10-17 · Spec Approved (05) |
| DEC-017 | Tên cột chuẩn hóa đơn | 03 dùng `amount_before_vat`, `amount_due`; 04 dùng `subtotal`, `amount`; review t5 | — | Chuẩn theo 05 §8: `subtotal` (trước VAT), `vat_rate`, `total_amount`, `paid_amount`, `amount_due = total_amount − paid_amount`, `status` PAID/UNPAID/PARTIAL | Một tên duy nhất cho công thức METRIC-FIN-01/05 và XD-01 | resolved | false | 03, 04, 05, 08, 10 | 2026-10-17 · Spec Approved (05, 10) |
| DEC-018 | Lineage metric → bản ghi → tài liệu | 03 §4, 05 §7, M5 | A: bảng liên kết · B: `metric_values.source_record_ids uuid[]` | **B** (GIN index, kiểm toàn vẹn ở service + test). Nếu cần FK cứng → DEC-039 | Giữ đúng 12 bảng; đủ cho panel P01 5 thành phần | resolved | false | 03, 05, 10 (EP-12, EP-13) | 2026-10-17 · Spec Approved (05) |
| DEC-019 | 18 metric / 18 alert, 1-1 | 01 §2.1, 03 §2–3 | — | METRIC-FIN-01..06, CUS-01..05, OPS-01..04, HR-01..03; ALERT-<PILLAR>-xx 1-1 với metric, mức Warning (vàng) / Critical (đỏ), đánh giá Đỏ trước; drill-down ≤ 3 click | Bám đúng 01; ngưỡng cụ thể là mặc định seed — xác nhận ở DEC-032 | resolved | false | 03, 05, 06, 08, 10 | 2026-10-17 · Spec Approved (03 t5) |
| DEC-020 | Hằng số demo & dữ liệu ABC | 08 (Approved t37) | — | Công ty TNHH TM&DV ABC (45 NV, ~100 tỷ/năm, TP.HCM); 5 user seed `*@abc.demo`, mật khẩu chỉ qua env `DEMO_*_PASSWORD`; 47 hóa đơn T9 Σ subtotal = 8.500.000.000; kỳ demo T9/Q3 2026 | Một bộ số liệu tự nhất quán (08 §4.4 K1–K16) | resolved | false | 08, seed | 2026-10-17 · Spec Approved (08 t37) |

### 3.4. Vận hành Agent Team (routing model)

| ID | Tiêu đề | Bối cảnh | Lựa chọn | Quyết định | Rationale | Status | Blocking | Ảnh hưởng | Ngày · Người quyết |
|---|---|---|---|---|---|---|---|---|---|
| DEC-021 | Chính sách routing model cho Agent Team (sinh tài liệu và build) | CLAUDE.md § Khung vận hành; goal team aureon-doc-factory; 11 §9 | A: chỉ Claude · B: chỉ free model · C: chuỗi ưu tiên có fallback | **C** — **Ưu tiên 1:** `cc/claude-opus-5-5` qua OmniRoute (reasoning, viết spec, review, code). **Ưu tiên 2:** OmniRoute auto (`auto/coding`, `auto/cheap`, `auto/fast`) khi Ưu tiên 1 bị 429/quota hoặc lỗi lặp lại. **Ưu tiên 3:** OpenRouter (trả phí) — chỉ khi Ưu tiên 1 và 2 cùng không dùng được, phải có `OPENROUTER_API_KEY` qua env. Mỗi lần chuyển route, captain ghi một dòng vào §6 Model Routing Log | Chất lượng reasoning cao nhất cho spec/code; fallback giữ tiến độ; OpenRouter tốn tiền nên để cuối. Việc đưa OpenRouter vào bảng Tech Stack xem DEC-102 | resolved | false | 11 §9, captain, mọi agent | 2026-10-17 · @CyEyes (user chỉ đạo) |
| DEC-022 | Điều chỉnh routing sau sự cố stream stall (2026-10-17) | Model Routing Log §6 sự kiện #1–#6: Opus stall 3 lần, đều khi một lượt sinh ~15KB; bản 08 viết trên `auto/coding` có 9 lỗi số học | A: chuyển hẳn sang auto · B: giữ Opus, chia nhỏ output | **B** — giữ `cc/claude-opus-5-5` qua OmniRoute làm mặc định theo chỉ đạo trực tiếp của user; **chỉ fallback khi 429/quota** (không fallback vì stall); agent viết theo lượt nhỏ (< 8KB hoặc < 80 dòng mỗi lượt ghi), tính số liệu bằng script thay vì sinh bảng dài trong đầu | Stall do kích thước output mỗi lượt, không do model; route `auto/coding` cho chất lượng số liệu kém hơn rõ rệt | resolved | false | 11 §9, mọi agent | 2026-10-17 · @CyEyes (user chỉ đạo) |

---

## 4. Quyết định mở (open)

Mọi mục "Open questions" của 02–08, 10, 11 đều có DEC ở đây. Cột "Đề xuất mặc định" là gợi ý của spec gốc, **chưa có hiệu lực**, trừ khi spec ghi rằng đang tạm dùng mặc định trong lúc chờ. Ngày raise của tất cả DEC trong mục này: 2026-10-17. Người quyết: — (chờ human).

> **Cập nhật 2026-10-18 — Gate B đã ĐẠT.** Toàn bộ 10 DEC `open` + `blocking=true` của §5 đã được human resolve theo gói đề xuất (uỷ quyền captain ghi nhận). Các dòng tương ứng trong §4.1–§4.4 đã chuyển `status = resolved`, `blocking = false`. Các DEC `open` còn lại trong §4 đều có `blocking = false` nên **không chặn task nào**. Chi tiết quyết định và việc đồng bộ tài liệu còn nợ: xem §5.
>
> Từ đây mọi task S0–S4 được phép bắt đầu; không cần chờ human cho Gate B nữa.

### 4.1. Phạm vi, dữ liệu demo, IDP, dashboard (DEC-030 → DEC-059)

| ID | Tiêu đề | Bối cảnh (nguồn) | Lựa chọn | Đề xuất mặc định | Rationale / hệ quả nếu chưa chốt | Status | Blocking | Ảnh hưởng |
|---|---|---|---|---|---|---|---|---|
| DEC-030 | Kỳ đối chiếu XD-01: BCTC Q3 vs hóa đơn T9 | 01 §8 yêu cầu doanh thu #1 (Q3) = SUM(#2, T9) — khác kỳ. 04 OQ-12 = 08 OQ-01 (gộp) | A: so doanh thu **tháng 9** trong BCTC (`revenue_by_month`) với SUM(subtotal) T9, ±0,5% (04 §12.1) · B: mở rộng #2 thành hóa đơn cả Q3 · C: sửa 01 §8 | **A** (08 đã seed theo A: T9 = 8.500.000.000) | Spec mâu thuẫn với 01 nên phải có human (CLAUDE.md Escalation). Chưa chốt thì không được code rule XD-01 và test UC-07 bước 5 | **resolved** 2026-10-18 · @CyEyes | false | 01 §8, 04 §12.1, 08 §3–4, task IDP cross-check, test UC-07 |
| DEC-031 | Thời hạn undo 7 ngày, khóa Review 15 phút | 04 OQ-08 | Giữ / đổi số | Giữ 7 ngày / 15 phút | Chỉ là giá trị cấu hình | open | false | 04, 10 (EP-29, EP-33) |
| DEC-032 | Xác nhận ngưỡng vàng/đỏ 18 metric | 03 OQ-02, 08 OQ-05 | Giữ / business chỉnh | Giữ ngưỡng 03 §2 làm seed | Chỉ là seed; đổi ngưỡng thì phải tính lại alert demo ở 08 §5.1 | open | false | 03, 08 |
| DEC-033 | Xác nhận ngưỡng confidence (0,70/0,80/0,90/0,95) và dung sai XD-01 ±0,5% | 04 OQ-03 | Giữ / chỉnh | Giữ (đang chạy theo DEC-014) | Có thể cấu hình theo doc type | open | false | 04, 08 |
| DEC-034 | Seed lịch sử: kỳ gốc NRR, rolling 12 tháng (CUS-04, HR-01, HR-02) | 03 OQ-03, 05 OQ-07, 08 OQ-03, OQ-06 | A: seed thẳng `business_records`/`metric_values` với `computation='SEED'` · B: tạo thêm file tài liệu lịch sử | A (08 §5.2 đã seed) | Không chặn: 08 đã có số liệu đầu vào | open | false | 03, 05, 08 |
| DEC-035 | Nguồn NPS (METRIC-CUS-05) | 03 OQ-04, 08 OQ-04 | A: field `nps_score` trong DOC-03 và DOC-07 · B: thêm loại tài liệu khảo sát | A | Thêm doc type là đổi scope | open | false | 03, 04, 08 |
| DEC-036 | Mapping field → METRIC cụ thể | 04 OQ-11 (chờ 03) | — | Hoàn thiện theo 03 §2 (đã Approved) + 08 §5.1 | 03 đã Approved; chỉ cần đồng bộ lại 04 | open | false | 04 |
| DEC-037 | Action Registry chưa có action ghi `DECISION`, `FINANCIAL_LINE`, `OPPORTUNITY`, `BUDGET_LINE`, `PROJECT`, `SURVEY_RESPONSE` | 05 OQ-02 | A: mở rộng side effect của action hiện có · B: thêm action mới | A | Thêm action làm đổi contract của 04 và 10 | **resolved** 2026-10-18 · @CyEyes | false | 04 §10.2, 05, 10 (EP-31), task Action Registry |
| DEC-038 | Entity khách hàng riêng cho XD-02 | 04 OQ-02, 03 OQ-01 | A: `record_type=CUSTOMER` trong `business_records` (DEC-016) · B: so tên/MST trực tiếp | A (đã có ở 05) | Phần lớn đã giải quyết bởi DEC-016; chỉ còn xác nhận quy tắc khớp tên | open | false | 04, 05 |
| DEC-039 | Lineage `uuid[]` không FK có chấp nhận được không | 05 OQ-05 | A: `uuid[]` + GIN + test toàn vẹn · B: thêm bảng liên kết (bảng thứ 13) | A (đang chạy theo DEC-018) | Chọn B nghĩa là đổi schema | open | false | 05, 10 |
| DEC-040 | Nguồn "tổng chi phí nhân sự / quỹ lương" cho CFO (view-agg) | 05 OQ-04, review t29 | A: dòng `FINANCIAL_LINE PAYROLL_COST` từ #1 · B: SUM(salary) từ #6, chỉ trả tổng | A, fallback B | Liên quan tới dữ liệu lương (DEC-008) | open | false | 02, 05, 10 |
| DEC-041 | Sales Director có được duyệt tài liệu trụ CUS không | 02 OQ-1, 04 OQ-05 | A: không (chỉ Reviewer) · B: có | A | Đổi sang B thì phải sửa ma trận 02 và quyền EP-31 | open | false | 02, 04, 10 |
| DEC-042 | CEO có quyền duyệt extraction không | 02 OQ-2 | A: không · B: có | A | Tách người quyết và người nhập liệu | open | false | 02, 04 |
| DEC-043 | Giữ mức `view-agg` | 02 OQ-3 | A: giữ · B: rút gọn còn view/none | A | Đổi sẽ ảnh hưởng data scoping DS3 ở 10 | open | false | 02, 10 |
| DEC-044 | Ai duyệt tài liệu #7 (KPI/OKR, nhiều trụ) | 02 OQ-4 | A: chỉ Reviewer · B: duyệt theo field của từng trụ | A | B cần khóa review theo field | open | false | 02, 04 |
| DEC-045 | Phạm vi xem audit log | 02 OQ-5 | A: chỉ CEO · B: thêm CFO cho hành động FIN | A | Ảnh hưởng EP-52 | open | false | 02, 10 (EP-52) |
| DEC-046 | Mốc đo KPI chuyển vai trò ≤ 2 giây | 02 OQ-7 | A: số liệu chính above the fold · B: toàn bộ biểu đồ | A | Cần chốt để viết test E2E | open | false | 02, 14 |
| DEC-047 | Ngưỡng quá tải chung "> 8 task mở" cho OPS-04 và HR-03 | 03 OQ-06 | Giữ / tách theo vai trò | Giữ | Chỉ là công thức seed | open | false | 03 |
| DEC-048 | Phân phối ALERT-OPS (HR chỉ nhận ALERT-HR-*; Sales không nhận ALERT-OPS) | 03 OQ-07, 08 OQ-07, review t29 | A: giữ theo 02 §3.3 · B: mở rộng | A | 10 EP-10 đã lọc theo A | open | false | 02, 03, 10 |
| DEC-049 | Chế độ offline demo | 04 OQ-06 | A: fixture/replay extraction cho 7 tài liệu + PaddleOCR self-host · B: model local | A | B cần dependency mới | open | false | 04, 07, 08 |
| DEC-050 | STT cho kênh C2 voice | 04 OQ-07 | A: coi C2 voice là P1 · B: chọn provider ngay | A | Provider mới = dependency mới, phải có DEC | open | false | 04, 07 |
| DEC-051 | ZIP upload trong UC-07 | 04 OQ-09, 10 OQ-10 | A: hỗ trợ ZIP · B: không (EP-20 trả 415) | **Chốt B — không hỗ trợ ZIP trong MVP**: giữ 10 (EP-20 trả `415` với `.zip`), đồng bộ 04 | 04 và 10 lệch nhau; chọn B vì 10 là contract nguồn duy nhất, không phải sửa API | **resolved** 2026-10-18 · @CyEyes | false | 04, 10 (EP-20, EP-40), task upload |
| DEC-052 | `DEMO_REFERENCE_DATE` = 2026-10-20 | 08 OQ-08 | A: biến env `DEMO_REFERENCE_DATE` · B: hằng số trong code | A | Mọi metric phụ thuộc ngày (FIN-05, OPS-01..03) đều tính theo mốc này; thiếu thì alert demo lệch | open | false | 07, 08, 10, seed |
| DEC-053 | Seed không có tài liệu gốc (HL-001, T7/T8, 12 tháng, 66 task, doanh thu T10, KH T9) | 08 OQ-09 | A: gắn nhãn "Dữ liệu seed lịch sử" trong panel nguồn · B: tạo tài liệu nguồn | A | Ảnh hưởng nguyên tắc P01: drill-down dừng ở bản ghi seed | open | false | 03 §4, 05, 06, 08 |
| DEC-054 | Bổ sung còn thiếu ở 08 | 08 OQ-10; review t37 | — | Bổ sung khi viết script seed: danh sách đủ 45 NV, 15 action item và 5 quyết định DOC-05, số liệu 12 tháng chi tiết, bộ tài liệu lệch số để demo MISMATCH. Ghi chú review t37: hợp đồng Minh Phát hết hạn 30/09/2026 nhưng hóa đơn T9 vẫn áp điều khoản 60 ngày (cần xác nhận hoặc gia hạn hợp đồng); 04 nên thêm field `sales_target` cho `SALES_REPORT` | Thiếu thì task seed không đủ ground truth cho test MISMATCH | open | false | 04, 08, task seed |
| DEC-055 | Reset dữ liệu demo có xóa `audit_logs` không (mâu thuẫn append-only) | 05 OQ-08 | A: chỉ cho phép khi DEMO_MODE bật, qua `app.reset` · B: không xóa | A | Ảnh hưởng nguyên tắc audit | open | false | 05, 07 |
| DEC-056 | Tiền tố ID nội bộ chưa có trong 00 §3 | 04 OQ-10, 08 (DOC-xx), 07 (NFR) | A: công nhận XD-, PI-, IDP-E, VR-, DOC-, NFR-, OQ-, K- là nhãn nội bộ · B: đổi sang prefix chuẩn | A | 00 §3 cấm tự tạo prefix mới; muốn sửa 00 phải có human | open | false | 00, 04, 07, 08 |

### 4.2. Kỹ thuật, kiến trúc (DEC-060 → DEC-079)

| ID | Tiêu đề | Bối cảnh (nguồn) | Lựa chọn | Đề xuất mặc định | Rationale / hệ quả nếu chưa chốt | Status | Blocking | Ảnh hưởng |
|---|---|---|---|---|---|---|---|---|
| DEC-060 | Đồng bộ câu chữ 01 §9 "Celery (hoặc ARQ)" với CLAUDE.md | 07 OQ-01 | A: sửa 01 §9 bỏ "ARQ" · B: giữ | A (stack đã chốt ở DEC-002) | Chỉ sửa tài liệu; 01 do human sửa | open | false | 01 |
| DEC-061 | LLM provider: 01 "Claude + GPT" vs CLAUDE.md "OpenAI / DeepSeek / Claude / Gemini" | 07 OQ-02 | A: theo CLAUDE.md, tất cả route qua OmniRoute · B: rút gọn | A | Code chỉ gọi ModelGateway nên không chặn | open | false | 01, 07 |
| DEC-062 | Lệnh seed: `pnpm db:seed` hay `uv run python -m app.seed` | 07 OQ-03, 08 OQ-02 | A: `uv run python -m app.seed` (seed ở backend) · B: `pnpm db:seed` gọi wrapper | A | CLAUDE.md đang mâu thuẫn nội bộ; 09 cần một lệnh duy nhất cho task seed | **resolved** 2026-10-18 · @CyEyes | false | CLAUDE.md, 07, 08, 09, task seed |
| DEC-063 | PaddleOCR chạy service riêng hay in-process; có dùng Google Vision | 07 OQ-04 | A: in-process trong worker, không dùng Google Vision · B: service riêng | A | Ảnh hưởng docker-compose | open | false | 07 |
| DEC-064 | Thư viện i18n và thư viện chart cho Next.js | 06 OQ-02, 07 OQ-05 | **Chốt: `next-intl` (i18n) + `Recharts` (chart)** | `next-intl` hợp App Router/Server Component theo SCR của 06; `Recharts` theo brief Phase 2 | Dependency mới phải có DEC (CLAUDE.md Cấm tự quyết #4); CLAUDE.md cấm hard-code tiếng Việt nên i18n là bắt buộc | **resolved** 2026-10-18 · @CyEyes | false | 06, 07, task FE dashboard |
| DEC-065 | Realtime: polling hay SSE/WebSocket | 07 OQ-06, 10 OQ-08 | A: polling · B: SSE | A (10 đang giả định polling ở EP-25, EP-41, EP-11) | Đổi sang B thì phải thêm endpoint | open | false | 07, 10 |
| DEC-066 | Bảng `model_call_log` / job tracking có trong 12 entity không | 07 OQ-07 | A: log vào `audit_logs` hoặc log file · B: bảng mới | A | B nghĩa là đổi schema | open | false | 05, 07 |
| DEC-067 | Version Python/PostgreSQL: "3.12"/"16" (01) vs "3.12+"/"16+" (CLAUDE.md) | 07 OQ-08 | Pin 3.12 / 16 trong Docker, cho phép "+" | Pin trong Docker | Chỉ là câu chữ | open | false | 01, 07 |
| DEC-068 | Bản nháp 09 còn NestJS/Prisma | 07 OQ-09, 11 OQ-08 | Sinh lại 09 ở Phase 4 theo stack DEC-001 và template 11 §7 | Sinh lại | 09 cũ mâu thuẫn CLAUDE.md, không được dùng. **Đã resolved 2026-10-17 (t25):** 09 đã sinh lại đúng stack CLAUDE.md, Approved (t26), không còn chặn | resolved | false | 09 | 2026-10-17 · Spec Approved (09, t26) |
| DEC-069 | Embedding model cho pgvector/LlamaIndex; offline | 07 OQ-10, 05 OQ-06 | A: MVP không dùng embedding, chỉ bật extension · B: embedding qua ModelGateway | A | Không cần trong 18 metric/IDP MVP | open | false | 05, 07 |
| DEC-070 | Encryption at rest AES-256, TLS 1.3 có bắt buộc cho demo | 07 OQ-11 | A: không bắt buộc ở dev, ghi là khuyến nghị prod · B: bắt buộc | A | Không đổi code ứng dụng | open | false | 07 |
| DEC-071 | Module Python `app.*` vs cấu trúc `apps/api/src/...` | 07 OQ-12 | A: package `app` nằm trong `apps/api/src/app` · B: đổi lệnh trong CLAUDE.md | A | Lệnh uvicorn/celery/mypy/pytest phụ thuộc vào đây; scaffold không làm được nếu chưa chốt | **resolved** 2026-10-18 · @CyEyes | false | CLAUDE.md, 07, task scaffold BE |
| DEC-072 | Panel AI (hỏi đáp) có thuộc MVP không | 07 OQ-13, 06 U2, 10 OQ-09 | A: chỉ có tóm tắt AI read-only (EP-10 `summary`) · B: Panel AI hỏi đáp đầy đủ | **A — loại Panel AI hỏi đáp khỏi MVP**; chỉ giữ `summary` AI read-only ở EP-10 | Chọn B thì phải thêm endpoint và scope (01 §2–3 không có) | **resolved** 2026-10-18 · @CyEyes | false | 01, 03, 06, 07, 10 |
| DEC-073 | Cơ chế chuyển vai trò demo + JWT | 02 OQ-6, 07 OQ-14 + §8.1.1–8.1.2, 05 M6, 10 OQ-11 | A: 5 user seed; khi `DEMO_MODE=true` backend cấp JWT mới cho user đích, ghi audit `role.switch`; khi tắt, endpoint trả 404; HS256 `JWT_SECRET` · B: một user, đổi claim role | **A (05, 08, 10 đã bám theo) + thư viện verify là `PyJWT` (HS256)** | Chọn thư viện JWT Python là dependency mới, phải có DEC; ảnh hưởng EP-04 | **resolved** 2026-10-18 · @CyEyes | false | 02, 05, 07, 08, 10 (EP-03..05), task auth |

### 4.3. Auth, API, UI/UX (DEC-080 → DEC-099)

| ID | Tiêu đề | Bối cảnh (nguồn) | Lựa chọn | Đề xuất mặc định | Rationale / hệ quả nếu chưa chốt | Status | Blocking | Ảnh hưởng |
|---|---|---|---|---|---|---|---|---|
| DEC-080 | Public endpoint = {health, login}, ngoại lệ so với CLAUDE.md | 10 OQ-13 | A: chấp nhận EP-01 + EP-02 public, có rate limit và audit `auth.login` · B: login qua NextAuth ở FE | A | CLAUDE.md ghi "trừ health check" — lệch hợp đồng nên cần human xác nhận | **resolved** 2026-10-18 · @CyEyes | false | CLAUDE.md, 10 (EP-01, EP-02), task auth |
| DEC-081 | Quyền đọc EP-50 (extraction schema) cho ROLE-01..05 | 10 OQ-06 | A: `require_role(ROLE-01..05)`; ROLE-01..04 phải truyền `doc_type`, ẩn field SALARY · B: chỉ ROLE-05 | A | 02 §3.6 chưa có dòng này; nếu chọn A thì phải sửa 02 | open | false | 02, 06, 10 (EP-50) |
| DEC-082 | Quyền đọc cấu hình AI (EP-51, SCR-15) và ai chỉnh autonomy/kill switch | 10 OQ-01, 06 OQ-01, 04 OQ-04 | A: chỉ đọc (ROLE-01, ROLE-05), chỉnh qua seed · B: cho CFO chỉnh trụ FIN qua UI | A | B cần thêm endpoint ghi và quyền mới trong 02 | open | false | 02, 04, 06, 10 |
| DEC-083 | `value_state` / `not_computable_reason` tính khi đọc hay lưu cột | 10 OQ-02 | A: tính khi đọc · B: thêm cột ở `metric_values` | A | B nghĩa là đổi schema 05 | open | false | 05, 10 |
| DEC-084 | Lưu thông tin batch UC-07 (checklist, label) | 10 OQ-03, 05 M3 | A: `batch_id` + `audit_logs.metadata` · B: bảng batch | A | B nghĩa là đổi schema | open | false | 05, 10 (EP-40, EP-41) |
| DEC-085 | Idempotency-Key lưu Redis TTL 24h | 10 OQ-04 | A: Redis · B: bảng DB | A | Đủ cho demo | open | false | 07, 10 |
| DEC-086 | Danh mục `reject_reason_code` (EP-32) | 10 OQ-05 | Dùng danh mục 10 đề xuất | Dùng danh mục 10 | 04 chỉ yêu cầu "bắt buộc chọn lý do" | open | false | 04, 06, 10 |
| DEC-087 | Phím tắt Review: Enter/E/R (04 FR-DC-18) vs Ctrl+Enter/Ctrl+Backspace (06 §4.3) | 10 OQ-07 | A: theo 06 · B: theo 04 | A (tránh xung đột khi đang gõ vào field) | 04 và 06 lệch nhau; ảnh hưởng test E2E | open | false | 04, 06, 14 |
| DEC-088 | `ai_state` suy từ `autonomy_level` + `status` (không có cột) | 10 OQ-12 | A: suy ra · B: thêm cột | A | B nghĩa là đổi schema | open | false | 05, 10 |
| DEC-089 | Bỏ màn Analytics (chất lượng AI) | 06 OQ-03 | A: bỏ, KPI IDP chỉ đo qua log · B: thêm màn | A | B là mở rộng scope | open | false | 01, 06 |
| DEC-090 | Token màu (hex) theo thương hiệu Aureon | 06 OQ-04 | Dùng màu gợi ý / brand chính thức | Màu gợi ý | Chỉ là design | open | false | 06 |
| DEC-091 | Mật độ hiển thị mặc định theo role (06 §6.5) | 06 OQ-05 | Giữ / chỉnh | Giữ | Chỉ là UX | open | false | 06 |
| DEC-092 | Route FE và EP-xx gọi từ mỗi SCR | 06 OQ-06, 03 OQ-05 | Chốt theo 07/10 | Lấy ma trận SCR↔EP ở 10 §8 | 10 đã map, chỉ cần đồng bộ 06 | open | false | 03, 06, 10 |
| DEC-093 | Ngưỡng "Dữ liệu cũ" của FreshnessLabel | 06 OQ-07 | Ví dụ: 2 × tần suất cập nhật | 2 × tần suất | Chỉ là UX | open | false | 06 (SCR-01..04) |

### 4.4. Governance, agent workflow (DEC-100 → DEC-119)

| ID | Tiêu đề | Bối cảnh (nguồn) | Lựa chọn | Đề xuất mặc định | Rationale / hệ quả nếu chưa chốt | Status | Blocking | Ảnh hưởng |
|---|---|---|---|---|---|---|---|---|
| DEC-100 | Gate A/B/C = "N/A" cho task sinh tài liệu Phase 1–2 | 11 OQ-01 | A: cho phép N/A khi chưa có governance, chỉ với task sinh tài liệu · B: luôn bắt buộc | A (captain đã áp dụng trong lúc sinh tài liệu) | Lệch contract doc-reviewer; từ Phase 4 và với mọi task code, gate là bắt buộc | open | false | 11, 12, review |
| DEC-101 | Định nghĩa lệnh `pnpm contract:validate` | 11 OQ-02, CLAUDE.md § Commit | A: validate OpenAPI sinh từ FastAPI so với 10 · B: bỏ khỏi điều kiện commit | A | Lệnh này là điều kiện bắt buộc trước commit nhưng chưa tồn tại → mọi commit code đều bị chặn | **resolved** 2026-10-18 · @CyEyes | false | CLAUDE.md, 09, 10, task CI |
| DEC-102 | Đưa OpenRouter (fallback Ưu tiên 3) vào bảng Tech Stack | 11 OQ-05 | A: ghi vào Khung vận hành, chỉ cho agent build, không dùng runtime · B: không dùng | A | Hiện chưa dùng (`OPENROUTER_API_KEY` chưa thiết lập); DEC-021 đã cho phép theo điều kiện | open | false | CLAUDE.md, 11 |
| DEC-103 | Ai cấp số DEC | 11 OQ-03 | A: maintainer file 13 (captain / @CyEyes) cấp; agent chỉ đề xuất · B: agent tự tăng số | A (§2.1 đang áp dụng) | Tránh trùng số khi nhiều agent chạy song song | open | false | 11, 13 |
| DEC-104 | Budget chi phí model | 11 OQ-04 | Human đặt ngưỡng theo sprint | — | Chưa có ngưỡng thì không áp dụng được rule "Chi phí > budget" | open | false | 11, captain |
| DEC-105 | Đồng bộ cột Optional cho 00 §4 | 11 OQ-06 | A: 00 giữ tóm tắt, CLAUDE.md + 11 là bản đầy đủ · B: thêm cột vào 00 | A | Chỉ là tài liệu | open | false | 00, 11 |
| DEC-106 | `.claude/skills/SKILL.md` đang rỗng | 11 OQ-07 | Bỏ qua cho đến khi có nội dung | Bỏ qua | Không ảnh hưởng build | open | false | 11 |
| DEC-107 | Số task của 09: CLAUDE.md/00/01 ghi "~40 task atomic", 09 thực tế có 62 task (411 giờ, mỗi task 4–8 giờ) | 09 (Open question, bản mới) OQ-04 · 01 §10 · CLAUDE.md § References | A: giữ 62 task, sửa "~40" thành "~60" ở 00/01/CLAUDE.md · B: gộp bớt task về ~40 (task 8–12 giờ) | A | Lệch con số chỉ gây hiểu nhầm, không chặn build; effort là ước lượng chưa hiệu chỉnh velocity | open | false | 00, 01, CLAUDE.md, 09 |
| DEC-108 | "4 sprint" (01 §10, CLAUDE.md) vs bảng thực tế 5 mốc S0–S4 (S0 là tuần setup) | 09 OQ-01 · 01 §10 | A: giữ 5 mốc, sửa chữ "4 sprint" thành "5 mốc (S0 setup + 4 sprint chức năng)" · B: gộp S0 vào S1 | A | 09 đã bám đúng bảng 5 dòng của 01 §10; chỉ cần đồng bộ câu chữ | open | false | 01, CLAUDE.md, 09 |
| DEC-109 | Nhãn loại task `INFRA` chưa có trong Doc Loading Matrix (11 §3, CLAUDE.md) cho task scaffold/hạ tầng (T-001 → T-004, T-009) | 09 OQ-02 · 11 §3 | A: thêm dòng "Scaffold/hạ tầng" (bắt buộc 00, 01, 07, 10) vào ma trận · B: coi là "Code auth"/"Test" gần nhất | A | Không có dòng ma trận thì Gate A cho task hạ tầng thiếu chuẩn load; hiện 09 dùng tạm bộ 00, 01, 07, 10 | open | false | 11, CLAUDE.md, 00, 09 |
| DEC-110 | UC-07 (T-311, T-312) đặt ở S3 trong khi 01 §10 mô tả S3 là "Metric thật + lineage" | 09 OQ-03 · 01 §10, 04 FR-DC-23 | A: giữ ở S3 (cần pipeline S2 + dashboard thật cho bước 6 demo) · B: chuyển sang S2 hoặc S4 | A | Sprint S3 đã thêm 2 task so với mô tả; đổi sprint thì phải sửa phụ thuộc và đường găng ở 09 §6 | open | false | 01, 09 |
| DEC-111 | Nơi ghi nhận cập nhật cột Task (`TBD-09`) của 14 sau khi 09 Approved | 09 OQ-05 · 12 OQ-03 | A: agent cập nhật 14 ngay khi 09 Approved (CLAUDE.md cho phép) · B: human cập nhật | A | Đã thực hiện ở t27 (2026-10-17): 155/155 TC có `T-xxx`; cần human xác nhận theo A | open | false | 14, 09 |
| DEC-112 | Phạm vi test mobile C4 (T-222): thiết bị thật hay giả lập viewport | 09 OQ-06 · 14 TC-IDP-006 | A: giả lập viewport trong Playwright, thiết bị thật là manual · B: bắt buộc thiết bị thật | A | Ảnh hưởng chi phí QA và độ tin cậy của TC-IDP-006 | open | false | 04, 14, 09 |
| DEC-113 | Task/TC đo "Field accuracy ≥ 90%" và "STP ≥ 50%" (01 §4) chưa có trong 14/09 | 09 OQ-07 · 01 §4 · 14 §5 | A: thêm TC-KPI và task đo vào 14/09 · B: chỉ đo thủ công khi demo | A | Hai KPI này chưa kiểm chứng được nếu không có TC; hiện ghi nhận như test gap, chưa tạo task mới | open | false | 01, 14, 09 |

---

## 5. Tóm tắt DEC open + blocking (dùng cho Gate B)

### 5.1. Trạng thái hiện tại: **0 DEC open + blocking → Gate B ĐẠT**

Toàn bộ 10 DEC `open` + `blocking=true` đã được human (@CyEyes) resolve ngày **2026-10-18** theo gói đề xuất; captain ghi nhận. Từ đây mọi task S0–S4 được phép bắt đầu mà không cần chờ human cho Gate B.

| ID | Tiêu đề ngắn | **Quyết định đã chốt** | Ngày · Người quyết |
|---|---|---|---|
| DEC-030 | Kỳ đối chiếu XD-01 Q3 vs T9 | **A** — so doanh thu **tháng 9** trong BCTC (`revenue_by_month['2026-09']`) với SUM(`subtotal`) 47 hoá đơn T9, dung sai ±0,5% (04 §12.1) | 2026-10-18 · @CyEyes |
| DEC-037 | Action Registry thiếu action cho 6 `record_type` | **A** — mở rộng side effect của action hiện có; **không** thêm action mới (không đổi contract 04/10) | 2026-10-18 · @CyEyes |
| DEC-051 | ZIP upload (04 và 10 lệch nhau) | **B** — **không** hỗ trợ ZIP trong MVP; giữ 10 (EP-20 trả `415` với `.zip`); đồng bộ 04 | 2026-10-18 · @CyEyes |
| DEC-062 | Lệnh seed pnpm vs uv | **A** — lệnh duy nhất `uv run python -m app.seed` (và `uv run python -m app.reset`); gỡ `pnpm db:seed` | 2026-10-18 · @CyEyes |
| DEC-064 | Thư viện i18n + chart (dependency mới) | **`next-intl`** cho i18n + **`Recharts`** cho chart | 2026-10-18 · @CyEyes |
| DEC-071 | Module `app` vs `apps/api/src` | **A** — package Python `app` đặt tại `apps/api/src/app`; giữ nguyên mọi lệnh uvicorn/celery/mypy/pytest của CLAUDE.md | 2026-10-18 · @CyEyes |
| DEC-072 | Panel AI có thuộc MVP | **A** — loại Panel AI hỏi đáp khỏi MVP; chỉ giữ `summary` AI read-only ở EP-10 | 2026-10-18 · @CyEyes |
| DEC-073 | Cơ chế role switch + thư viện JWT | **A** — 5 user seed; khi `DEMO_MODE=true` backend cấp JWT mới qua EP-04 + audit `role.switch`; thư viện verify **`PyJWT`** (HS256) | 2026-10-18 · @CyEyes |
| DEC-080 | Public endpoint {health, login} | **A** — chấp nhận đúng {EP-01, EP-02} là ngoại lệ của CLAUDE.md § API, có rate limit + audit `auth.login` | 2026-10-18 · @CyEyes |
| DEC-101 | `pnpm contract:validate` chưa định nghĩa | **A** — script pytest `-m contract`: sinh OpenAPI từ FastAPI và so với 10 (envelope, error code, `response_model`, `require_role`) | 2026-10-18 · @CyEyes |

### 5.2. Nợ đồng bộ tài liệu (không chặn build)

Các quyết định dưới đây **không đổi schema (05) hay API contract (10)**, nên chỉ cần sửa câu chữ khi human chạm file tương ứng:

| DEC | File cần đồng bộ | Nội dung cần sửa |
|---|---|---|
| DEC-030 | 01 §8 | Ghi rõ kỳ đối chiếu là tháng 9 ↔ tháng 9 |
| DEC-051 | 04 §2, 04 OQ-09 | Bỏ nhánh ZIP; ghi EP-20 trả `415` với `.zip` |
| DEC-062 | CLAUDE.md § Commands | Gỡ `pnpm db:seed` |
| DEC-064 | CLAUDE.md § Tech Stack, 07 §2 | Ghi `next-intl`, `Recharts` |
| DEC-072 | 06 §U2, 07 §9 | Bỏ Panel AI khỏi MVP |
| DEC-073 | CLAUDE.md § Tech Stack, 07 §8.1.2 | Ghi `PyJWT` |
| DEC-080 | CLAUDE.md § API | Ghi ngoại lệ {EP-01, EP-02} |

> **Cảnh báo Gate A:** khi human sửa nội dung các file trên, phải cân nhắc đánh dấu `stale` các file phụ thuộc (12 §4 bước 5) rồi re-review. Hiện **chưa file nào bị đánh dấu** → Gate A vẫn ĐẠT.

> **Ghi chú lịch sử:** DEC-068 đã resolved ở t25/t26 (§4.2) trước đợt này.

---

## 6. Model Routing Log

Theo DEC-021 / DEC-022. Captain ghi tiếp một dòng mỗi lần đổi model/route (thêm vào cuối bảng, không sửa dòng cũ).

| # | Thời điểm | Task | Model cũ → mới | Lý do | Kết quả |
|---|---|---|---|---|---|
| 1 | 2026-10-17 | t7 (sinh 05) | writer-a `omni-route/cc/claude-opus-5-5` → writer-d `omni-route/cc/claude-opus-5-5` (retry cùng model) | Stream stall (PI_AI_ERROR, không có output trong 115 giây) | Retry thành công, 05 được sinh |
| 2 | 2026-10-17 | t10 (sinh 08) | writer-a `cc/claude-opus-5-5` → writer-e `omni-route auto/coding` | Opus stream stall lần 2 | Sinh được bản 08 nhưng sai số học (xem #5) |
| 3 | 2026-10-17 | t10 (sinh 08) | `auto/coding` → `auto/coding` (attempt 3) | Lỗi 402/400 ở model phụ trong route auto | Hoàn thành t10 |
| 4 | 2026-10-17 | t12 (sinh 10) | writer-b `cc/claude-opus-5-5` → writer-f `omni-route auto` | 429 rate limit Opus (reset khoảng 4 giờ) | writer-f kiểm tra lại và xác nhận verify pass |
| 5 | 2026-10-17 ~09:55 | t36 (sửa 08) | `auto/coding` → writer-d `cc/claude-opus-5-5` (Ưu tiên 1) | Bản 08 viết trên `auto/coding` có 9 lỗi số học (review t16); rate limit Opus đã reset | Gặp stall (xem #6) |
| 6 | 2026-10-17 ~10:10 | t36 (sửa 08) | writer-d `cc/claude-opus-5-5` → writer-a `omni-route/cc/claude-opus-5-5`, lượt output nhỏ (< 8KB mỗi lần ghi) | Opus stall lần 3 (PI_AI_ERROR), các lần đều khi một lượt sinh ~15KB; user chỉ đạo trực tiếp "dùng claude-opus thông qua omniroute" | Thành công; 08 Approved vòng 2 (t37) |
| 7 | 2026-10-17 | t19 (sinh 13) | writer-a `cc/claude-opus-5-5` → writer-f `omni-route auto` | 429 rate limit Opus | writer-f kiểm tra và submit, verify pass |
| 8 | 2026-10-17 | t23 (review 14) | reviewer-b `cc/claude-opus-5-5` → writer-e `omni-route auto/coding` → reviewer-c `omni-route auto` | Opus 429; `auto/coding` trả UNKNOWN_MODEL | reviewer-c hoàn thành review (pass) |
| 9 | 2026-10-17 | t22 (review 13) | reviewer-a `cc/claude-opus-5-5` → reviewer-d `kiro/auto` → reviewer-c `omni-route auto` | Opus 429; `kiro/auto` 429 | reviewer-c hoàn thành review (pass) |
| 10 | 2026-10-17 | t25 (sinh 09) | writer-c `cc/claude-opus-5-5` → writer-f `kiro/auto` → writer-g `omni-route/agent-execution` | Opus 429; `kiro/auto` 429 | writer-g hoàn thành 09 (pass) |
| 11 | 2026-10-17 | t26 (review 09) | → reviewer-e `omni-route/agent-execution` | Route agent-execution ổn định sau #10 | Review pass |
| 12 | 2026-10-17 | t27 (đồng bộ governance) | writer-f `omni-route auto` → writer-g `omni-route/agent-execution` | writer-f gặp 402 limit giữa chừng | writer-g hoàn thành t27 |
| 13 | 2026-10-18 | Gate B unblock (10 DEC) + chuyển sang orchestration đa agent | Captain giữ `xplabs/deepseek-v4.1-flash-uncensored`; sub-agent định tuyến qua `omni-route`: `agent-architecture` (planner), `agent-coding` (coder), `cc/claude-sonnet-5` (reviewer), `agent-execution` (tester) | Brief v2 của user: Orchestrator chạy xplabs trực tiếp, sub-agent chạy qua OmniRoute theo combo có sẵn | 4/4 route verify HTTP 200 (`agent-architecture`→claude-opus-5-5, `agent-coding`→gpt-6-luna-high, `cc/claude-sonnet-5`→claude-sonnet-5, `agent-execution`→claude-sonnet-5-5) |

**Bài học (đã đưa vào DEC-022):**
- Stall do **kích thước output mỗi lượt**, không do model. Cách xử lý là chia nhỏ lượt ghi chứ không phải đổi model.
- Route `auto/coding` cho chất lượng số liệu kém hơn rõ rệt; chỉ dùng khi Opus bị 429/quota.
- **OpenRouter chưa dùng lần nào** (`OPENROUTER_API_KEY` chưa thiết lập).

---

## 7. Bảng truy vết Open question → DEC

| File nguồn | OQ → DEC |
|---|---|
| 02-PERSONAS-PERMISSIONS | OQ-1→DEC-041 · OQ-2→DEC-042 · OQ-3→DEC-043 · OQ-4→DEC-044 · OQ-5→DEC-045 · OQ-6→DEC-073 · OQ-7→DEC-046 |
| 03-DASHBOARD-SPEC | OQ-01→DEC-016 (resolved), DEC-038 · OQ-02→DEC-032 · OQ-03→DEC-034 · OQ-04→DEC-035 · OQ-05→DEC-092 · OQ-06→DEC-047 · OQ-07→DEC-048 |
| 04-IDP-FEATURE-SPEC | OQ-01→DEC-016 (resolved) · OQ-02→DEC-038 · OQ-03→DEC-033 · OQ-04→DEC-082 · OQ-05→DEC-041 · OQ-06→DEC-049 · OQ-07→DEC-050 · OQ-08→DEC-031 · OQ-09→DEC-051 · OQ-10→DEC-056 · OQ-11→DEC-036 · OQ-12→DEC-030 |
| 05-DATA-MODEL | OQ-01→DEC-016 (resolved) · OQ-02→DEC-037 · OQ-03→DEC-017 (resolved; 08 đã có cột "Đã thu" và trạng thái PARTIAL) · OQ-04→DEC-040 · OQ-05→DEC-039 · OQ-06→DEC-069 · OQ-07→DEC-034 · OQ-08→DEC-055 |
| 06-UI-UX-SPEC | OQ-01→DEC-082 · OQ-02→DEC-064 · OQ-03→DEC-089 · OQ-04→DEC-090 · OQ-05→DEC-091 · OQ-06→DEC-092 · OQ-07→DEC-093 |
| 07-TECH-ARCHITECTURE | OQ-01→DEC-002 (resolved), DEC-060 · OQ-02→DEC-061 · OQ-03→DEC-062 · OQ-04→DEC-063 · OQ-05→DEC-064 · OQ-06→DEC-065 · OQ-07→DEC-066 · OQ-08→DEC-067 · OQ-09→DEC-068 · OQ-10→DEC-069 · OQ-11→DEC-070 · OQ-12→DEC-071 · OQ-13→DEC-072 · OQ-14→DEC-073 |
| 08-DEMO-DATA-SPEC | OQ-01→DEC-030 · OQ-02→DEC-062 · OQ-03→DEC-034 · OQ-04→DEC-035 · OQ-05→DEC-032 · OQ-06→DEC-034 · OQ-07→DEC-048 · OQ-08→DEC-052 · OQ-09→DEC-053 · OQ-10→DEC-054 |
| 10-API-SPECIFICATION | OQ-01→DEC-082 · OQ-02→DEC-083 · OQ-03→DEC-084 · OQ-04→DEC-085 · OQ-05→DEC-086 · OQ-06→DEC-081 · OQ-07→DEC-087 · OQ-08→DEC-065 · OQ-09→DEC-072 · OQ-10→DEC-051 · OQ-11→DEC-073 · OQ-12→DEC-088 · OQ-13→DEC-080 |
| 11-AGENT-WORKFLOW | OQ-01→DEC-100 · OQ-02→DEC-101 · OQ-03→DEC-103 · OQ-04→DEC-104 · OQ-05→DEC-102 · OQ-06→DEC-105 · OQ-07→DEC-106 · OQ-08→DEC-068 |
| 09-BUILD-PLAN-TASKS | OQ-01→DEC-108 · OQ-02→DEC-109 · OQ-03→DEC-110 · OQ-04→DEC-107 · OQ-05→DEC-111 · OQ-06→DEC-112 · OQ-07→DEC-113 · OQ-08→DEC-072 |

Ghi chú: 05 M1–M6 là quyết định thiết kế của 05, được ghi ở DEC-016 (M1, M2), DEC-018 (M5), DEC-084 (M3), DEC-073 (M6). M4 (định nghĩa alert nằm trong `metrics`) thuộc phạm vi DEC-019.

---

## 8. Open questions (của chính file này)

| # | Câu hỏi | Đề xuất |
|---|---|---|
| OQ-01 | Các DEC "resolved" lấy từ spec Approved (Người quyết = "Spec Approved") có cần @CyEyes ký xác nhận lại không? | Human rà soát nhanh §3 một lần; DEC nào không đồng ý thì chuyển thành `superseded` |
| OQ-02 | Một số OQ đã có mặc định đang được dùng tạm (DEC-030, DEC-073…). Agent có được code theo mặc định khi DEC còn blocking không? | Không — theo Gate B, chờ human resolve. **Đã áp dụng 2026-10-18:** agent dừng ở Gate B, trình gói 10 DEC và chờ human chốt trước khi viết dòng code đầu tiên |
| OQ-03 | Sau khi 09 được sinh (Phase 4), cột "Ảnh hưởng" cần bổ sung mã `T-xxx` cụ thể | Captain cập nhật khi 09 Approved |

---

## 9. Version

- **Version:** 1.0.0
- **Last updated:** 2026-10-17
- **Applies to:** Aureon Demo v1.0
- **Maintainer:** @CyEyes
