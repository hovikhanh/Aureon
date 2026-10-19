# 12 — Doc Audit

> Sổ trạng thái của mọi tài liệu **Aureon Demo**. Đây là nguồn dữ liệu cho **Gate A — Document Audit** (`CLAUDE.md` § Gotchas, `11-AGENT-WORKFLOW.md` §4).
> Agent đọc file này trước mọi task. Chỉ con người (@CyEyes) hoặc Captain của đợt sinh tài liệu được đổi `status`, `version`, `last_reviewed`.

---

## 1. Quy ước status

| Status | Ý nghĩa | Agent được dùng cho build? | Chuyển tiếp hợp lệ |
|---|---|---|---|
| `draft` | Đang soạn hoặc chưa qua review Approved | ❌ Không — Gate A fail | → `current` (sau review Approved) |
| `current` | Đã review **Approved**, là nguồn chuẩn hiện hành | ✅ Có | → `stale`, `deprecated` |
| `stale` | Từng `current`, nhưng có thay đổi phụ thuộc chưa được đồng bộ, hoặc không được review lại quá hạn và bị đánh dấu | ❌ Không — Gate A fail | → `current` (sau re-review) |
| `deprecated` | Bị thay thế bởi file khác, còn giữ để tham chiếu lịch sử | ❌ Không | → `archived` |
| `archived` | Lưu trữ; **cấm load** (`CLAUDE.md` § Cấm đọc) | ❌ Không — cấm đọc | — |

### 1.1. Ngưỡng `last_reviewed`

| Điều kiện | Kết quả Gate A |
|---|---|
| `status = current` và `last_reviewed` ≤ 14 ngày tính đến ngày làm task | Đạt |
| `status = current` và `last_reviewed` > 14 ngày | Đạt kèm **cảnh báo** — nên re-review; Captain/human quyết định chuyển `stale` |
| `status` ≠ `current`, hoặc file không có trong bảng §2 | **Không đạt** → task `BLOCKED` (định dạng ở `11-AGENT-WORKFLOW.md` §6) |

Mốc audit đợt này: **2026-10-17**. Ngưỡng cảnh báo tiếp theo: **2026-10-31**.

---

## 2. Bảng trạng thái tài liệu

| # | File | Phase | Version | Status | last_reviewed | Owner | Phụ thuộc (đầu vào) | Ghi chú |
|---|---|---|---|---|---|---|---|---|
| — | `CLAUDE.md` | Hợp đồng vận hành | 1.1.0 | current | 2026-10-17 | @CyEyes | — | Chỉ con người sửa |
| 00 | `docs/1.CONTEXT/00-INDEX.md` | Context | 1.0.0 | current | 2026-10-17 | @CyEyes | CLAUDE.md | Navigation, quy ước ID |
| 01 | `docs/1.CONTEXT/01-PROJECT-OVERVIEW.md` | Context | 1.0.0 | current | 2026-10-17 | @CyEyes | — | Nguồn gốc mọi spec |
| 02 | `docs/2.PRODUCT/02-PERSONAS-PERMISSIONS.md` | 1 | 1.0.0 | current | 2026-10-17 | @CyEyes | 01 | Approved (review round 2) |
| 03 | `docs/2.PRODUCT/03-DASHBOARD-SPEC.md` | 1 | 1.0.0 | current | 2026-10-17 | @CyEyes | 01, 02 | Approved |
| 04 | `docs/2.PRODUCT/04-IDP-FEATURE-SPEC.md` | 1 | 1.0.0 | current | 2026-10-17 | @CyEyes | 01, 02 | Approved (review round 2) |
| 05 | `docs/2.PRODUCT/05-DATA-MODEL.md` | 2 | 1.0.0 | current | 2026-10-17 | @CyEyes | 01, 02, 03, 04 | Approved |
| 06 | `docs/2.PRODUCT/06-UI-UX-SPEC.md` | 2 | 1.0.0 | current | 2026-10-17 | @CyEyes | 01, 02, 03, 04 | Approved |
| 07 | `docs/3.EXECUTION/07-TECH-ARCHITECTURE.md` | 2 | 1.0.0 | current | 2026-10-17 | @CyEyes | CLAUDE.md, 01, 02, 04 | Approved (review round 2) |
| 08 | `docs/3.EXECUTION/08-DEMO-DATA-SPEC.md` | 2 | 1.0.0 | current | 2026-10-17 | @CyEyes | 01, 02, 03, 04, 05, 07 | Approved (review round 2) |
| 09 | `docs/3.EXECUTION/09-BUILD-PLAN-TASKS.md` | 4 | 1.0.0 | current | 2026-10-17 | @CyEyes | 00–08, 10–14 | Approved (review round 1) — 62 task, 5 mốc sprint S0–S4; dòng "Status: draft" trong 09 §8 là câu chữ cũ, 12 là nguồn trạng thái |
| 10 | `docs/3.EXECUTION/10-API-SPECIFICATION.md` | 2 | 1.0.0 | current | 2026-10-17 | @CyEyes | 02, 03, 04, 05, 07 | Approved (review round 2) — contract nguồn duy nhất |
| 11 | `docs/3.EXECUTION/11-AGENT-WORKFLOW.md` | 2 | 1.0.0 | current | 2026-10-17 | @CyEyes | CLAUDE.md, 00 | Approved |
| 12 | `docs/4.GOVERNANCE/12-DOC-AUDIT.md` | 3 | 1.0.0 | current | 2026-10-17 | @CyEyes | 00–11, 13, 14 | File này; Approved (review round 2) |
| 13 | `docs/4.GOVERNANCE/13-DECISION-LOG.md` | 3 | 1.0.0 | current | 2026-10-17 | @CyEyes | 02–11 (Open questions) | Approved (review round 1); t27 thêm DEC-107..113 và Routing Log #7–12 |
| 14 | `docs/4.GOVERNANCE/14-TEST-TRACEABILITY.md` | 3 | 1.0.0 | current | 2026-10-17 | @CyEyes | 03, 04, 10 | Approved (review round 1); t27 điền cột Task `T-xxx` từ 09; agent được cập nhật khi làm task |

> Toàn bộ 15 file (00–14) + CLAUDE.md đều ở status `current`, `last_reviewed` 2026-10-17; không còn file `draft`. 09, 13, 14 đã Approved (t26, t22, t23) và được promote ở t27. **Kết luận Gate A: ĐẠT.** Gate B: 10 DEC open + blocking (13 §5; DEC-068 đã resolved sau khi 09 Approved) chặn các task ghi ở 09 §2. Gate C: 14 map đủ spec ↔ TC ↔ T-xxx.

---

## 3. Kiểm tra định dạng Markdown

Tiêu chí (`CLAUDE.md` § Documentation Generation §2–3):
- **H1:** đúng 1 tiêu đề `#` ở đầu file.
- **Heading:** có các mục `##` rõ ràng.
- **Bảng:** dùng bảng cho ma trận, data model và endpoint.
- **Code fence:** các khối ```` ``` ```` đóng/mở đủ cặp.
- **Version:** có mục `Version` kèm số version.

Kết quả kiểm tra tự động bằng script đếm heading, bảng và fence, ngày 2026-10-17:

| # | File | Dòng | H1 | Số `##` | Số bảng | Fence cân | Mục Version | Kết quả |
|---|---|---|---|---|---|---|---|---|
| — | `CLAUDE.md` | 422 | 11 ⚠️ | 26 | 6 | ✅ | ✅ 1.1.0 | Đạt — dùng nhiều `#` làm section cấp 1; dòng `# …` trong khối lệnh không bọc fence (OQ-02) |
| 00 | `00-INDEX.md` | 141 | 1 | 8 | 8 | ✅ | ✅ 1.0.0 | Đạt |
| 01 | `01-PROJECT-OVERVIEW.md` | 328 | 1 | 14 | 9 | ✅ | ✅ 1.0.0 | Đạt |
| 02 | `02-PERSONAS-PERMISSIONS.md` | 319 | 1 | 9 | 18 | ✅ | ✅ 1.0.0 | Đạt |
| 03 | `03-DASHBOARD-SPEC.md` | 516 | 1 | 9 | 30 | ✅ | ✅ 1.0.0 | Đạt |
| 04 | `04-IDP-FEATURE-SPEC.md` | 690 | 1 | 19 | 36 | ✅ | ✅ 1.0.0 | Đạt |
| 05 | `05-DATA-MODEL.md` | 718 | 1 | 15 | 29 | ✅ | ✅ 1.0.0 | Đạt |
| 06 | `06-UI-UX-SPEC.md` | 492 | 1 | 13 | 33 | ✅ | ✅ 1.0.0 | Đạt |
| 07 | `07-TECH-ARCHITECTURE.md` | 576 | 1 | 15 | 27 | ✅ | ✅ 1.0.0 | Đạt |
| 08 | `08-DEMO-DATA-SPEC.md` | 626 | 1 | 8 | 34 | ✅ | ✅ 1.0.0 | Đạt |
| 09 | `09-BUILD-PLAN-TASKS.md` | 465 | 1 | 8 | 22 | ✅ | ✅ 1.0.0 | Đạt |
| 10 | `10-API-SPECIFICATION.md` | 923 | 1 | 11 | 60 | ✅ | ✅ 1.0.0 | Đạt |
| 11 | `11-AGENT-WORKFLOW.md` | 395 | 1 | 12 | 12 | ✅ | ✅ 1.0.0 | Đạt |
| 12 | `12-DOC-AUDIT.md` | 139 | 1 | 7 | 7 | ✅ | ✅ 1.0.0 | Đạt (bản này) |
| 13 | `13-DECISION-LOG.md` | 305 | 1 | 9 | 15 | ✅ | ✅ 1.0.0 | Đạt |
| 14 | `14-TEST-TRACEABILITY.md` | 482 | 1 | 11 | 25 | ✅ | ✅ 1.0.0 | Đạt |

Kiểm tra bổ sung:
- Không file spec nào (00–11) tự ghi `last_reviewed` trong nội dung → cột `last_reviewed` ở bảng §2 là nguồn duy nhất.
- Cả 02–08, 10, 11 kết thúc bằng mục Version 1.0.0, 2026-10-17, @CyEyes.

---

## 4. Quy trình audit

| Bước | Khi nào | Ai | Việc làm |
|---|---|---|---|
| 1. Đăng ký | File mới được tạo | Captain / human | Thêm dòng vào §2 với `status = draft` |
| 2. Review | File viết xong hoặc được sửa | `doc-reviewer` (`.claude/agents/doc-reviewer.md`) | Audit 5 section; kết luận Approved / Requires Changes |
| 3. Repair | Requires Changes | Writer | Sửa theo finding; quay lại bước 2 |
| 4. Promote | Approved | Captain / human | Chuyển `current`, cập nhật `version`, `last_reviewed`; chạy lại §3 |
| 5. Lan truyền | Một file `current` thay đổi nội dung | Captain / human | Đánh dấu các file phụ thuộc (cột "Phụ thuộc") là `stale` nếu bị ảnh hưởng, rồi re-review |
| 6. Định kỳ | Mỗi 14 ngày (lần tới 2026-10-31) hoặc trước sprint mới | Human | Rà `last_reviewed`, xử lý cảnh báo §1.1 |
| 7. Archive | File bị thay thế hoàn toàn | Human | Chuyển `deprecated` → `archived`, chuyển xuống mục X |

Quy tắc:
- Agent làm task code **không** sửa file này. Agent chỉ đọc để check Gate A; thấy sai lệch thì raise `DEC-xxx` trong 13.
- Thay đổi phiên bản theo SemVer: sửa chữ hoặc làm rõ → patch; thêm yêu cầu → minor; thay đổi phá vỡ contract (đặc biệt 05, 10) → major.

### 4.1. Đợt audit đồng bộ tài liệu — 2026-10-19

Rà soát nội dung các tài liệu không-spec (báo cáo/README/traceability/build-plan) để **đồng bộ với code hiện tại** sau khi hoàn thành engine động, UC-07, Audit, E2E, C4 merge/blur và phần auth. **Chỉ cập nhật nội dung; cột `status`/`version`/`last_reviewed` ở §2 do con người (@CyEyes) sở hữu — không đổi trong đợt này.**

| File | Loại rà | Kết quả |
|---|---|---|
| `README.md` | Số liệu test, đường dẫn demo data, Gate A/B/C, Known Issues | Cập nhật: FE 218 / BE 366 pass + 1 fail / coverage 88%; `data/` (bỏ `data/demo-docs/`); thêm mục Known Issues (KI-1 403 live OmniRoute, KI-2 E2E env) |
| `DEMO-READY-REPORT.md` | Trạng thái tính năng + số liệu + Known Issues | Đánh dấu Dynamic engine / UC-07 / Audit SCR-14 / C4 merge+blur đã xong; số liệu mới; thêm §7 Known Issues |
| `docs/3.EXECUTION/09-BUILD-PLAN-TASKS.md` | Trạng thái task | T-302..305, T-311/312, T-404, T-405 → Done (T-405 ghi chú "Implemented, E2E env pending") |
| `docs/4.GOVERNANCE/14-TEST-TRACEABILITY.md` | Bảng tổng hợp + Status entity + GAP + TC-KPI | 366/218/88%; ENT-Metric/MetricValue/Alert → Implemented, ENT-AuditLog → Passed; đóng GAP-08 (DEC-030), thêm GAP-10/GAP-11; TC-KPI-004/005/006 "manual pending" |
| `docs/1.CONTEXT/00-INDEX.md` | §7 Trạng thái | Sprint S0 → **S3/S4 Demo-ready**; thêm dòng Test + Known issues |
| `docs/3.EXECUTION/10-API-SPECIFICATION.md` | Đối chiếu code (Audit/Dynamic/UC-07) | Xem kết quả đối chiếu ở change-log 14 §6 và phần spec tương ứng |

**Kết luận Gate A đợt này:** nội dung các tài liệu trên đã khớp code; không phát hiện mâu thuẫn mới cần raise DEC. Các spec 02–11 giữ nguyên `current` theo §2.

---

## 5. Open questions

| # | Câu hỏi | Đề xuất mặc định |
|---|---|---|
| OQ-01 | Ai có quyền promote `draft` → `current`: Captain đợt sinh tài liệu hay chỉ human (@CyEyes)? | Captain được promote trong đợt sinh tự động theo yêu cầu user; human xác nhận khi kết thúc đợt |
| OQ-02 | `CLAUDE.md` có nhiều H1 và khối lệnh (`# cài deps…`) không bọc code fence, nên render như heading | Human cân nhắc bọc fence ở lần sửa `CLAUDE.md` tiếp theo (agent không tự sửa) |
| OQ-03 | 13 và 14 sinh song song với 12, nên chưa kiểm được định dạng ở §3 | **Đã xử lý ở t27 (2026-10-17):** script đã chạy lại và §3 đã cập nhật cho 09, 13, 14 |
| OQ-04 | 01 §9 / 07 OQ-01 có điểm lệch với CLAUDE.md (Celery "hoặc ARQ") — có cần đánh dấu 01 `stale`? | Giữ `current`; xử lý qua DEC trong 13 |

---

## X. Archived documents (không dùng cho build)

| File | Version | Status | Lý do archive |
|---|---|---|---|
| _reference/SOURCE-BRD.md | 1.0 | archived | Đã distill vào 14 spec files |
| _reference/SOURCE-UIUX.md | 1.0 | archived | Đã distill vào 14 spec files |

**Quy tắc:** 
- Status `archived` → agent KHÔNG được load
- Nếu cần update → tạo file mới trong docs/, không sửa file archive
- Archive chỉ để đọc, không để tham chiếu trong code

---

## Version

- **Version:** 1.0.0
- **Last updated:** 2026-10-17
- **Applies to:** Aureon Demo v1.0
- **Maintainer:** @CyEyes
