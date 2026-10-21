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
| 00 | `docs/1.CONTEXT/00-INDEX.md` | Context | 2.1.0 | **current** | 2026-10-19 | @CyEyes | CLAUDE.md | Navigation + ID registry v2 — viết lại theo DEC-124..137; promote bởi human (@CyEyes ủy quyền trong phiên 2026-10-19) · **2026-10-19 (DEC-144): tạm `draft` — chờ gap analysis với `_reference/` canonical, đích 2.1.0** |
| 01 | `docs/1.CONTEXT/01-PROJECT-OVERVIEW.md` | Context | 2.1.0 | **current** | 2026-10-19 | @CyEyes | — | Tầm nhìn v2, scope, KPI, roadmap S0–S5 — viết lại theo DEC-124..137; promote bởi human (@CyEyes ủy quyền trong phiên 2026-10-19) · **2026-10-19 (DEC-144): tạm `draft` — chờ gap analysis với `_reference/` canonical, đích 2.1.0** |
| 02 | `docs/2.PRODUCT/02-PERSONAS-PERMISSIONS.md` | 1 | 2.1.0 | **current** | 2026-10-19 | @CyEyes | 01 | 10 role, user stories, ma trận permission — viết lại theo DEC-124..137; promote bởi human (@CyEyes ủy quyền trong phiên 2026-10-19) · **2026-10-19 (DEC-144): tạm `draft` — chờ gap analysis với `_reference/` canonical, đích 2.1.0** |
| 03 | `docs/2.PRODUCT/03-DASHBOARD-SPEC.md` | 1 | 2.1.0 | **current** | 2026-10-19 | @CyEyes | 01, 02 | 5 trụ F.O.C.U.S, 31 metric/alert, FR domain — viết lại theo DEC-124..137; promote bởi human (@CyEyes ủy quyền trong phiên 2026-10-19) · **2026-10-19 (DEC-144): tạm `draft` — chờ gap analysis với `_reference/` canonical, đích 2.1.0** |
| 04 | `docs/2.PRODUCT/04-IDP-FEATURE-SPEC.md` | 1 | 2.1.0 | **current** | 2026-10-19 | @CyEyes | 01, 02 | IDP v2 (Domain 22): 5 kênh, review song song, 23 ACT — viết lại theo DEC-124..137; promote bởi human (@CyEyes ủy quyền trong phiên 2026-10-19) · **2026-10-19 (DEC-144): tạm `draft` — chờ gap analysis với `_reference/` canonical, đích 2.1.0** |
| 05 | `docs/2.PRODUCT/05-DATA-MODEL.md` | 2 | 2.1.0 | **current** | 2026-10-19 | @CyEyes | 01, 02, 03, 04 | ERD hợp nhất, 10 schema / 64 entity, outbox, lineage — viết lại theo DEC-124..137; promote bởi human (@CyEyes ủy quyền trong phiên 2026-10-19) · **2026-10-19 (DEC-144): tạm `draft` — chờ gap analysis với `_reference/` canonical, đích 2.1.0** |
| 06 | `docs/2.PRODUCT/06-UI-UX-SPEC.md` | 2 | 2.1.0 | **current** | 2026-10-19 | @CyEyes | 01, 02, 03, 04 | Design system v2, AI components, SCR-01..28, F1–F5 — viết lại theo DEC-124..137; promote bởi human (@CyEyes ủy quyền trong phiên 2026-10-19) · **2026-10-19 (DEC-144): tạm `draft` — chờ gap analysis với `_reference/` canonical, đích 2.1.0** |
| 07 | `docs/3.EXECUTION/07-TECH-ARCHITECTURE.md` | 2 | 2.1.0 | **current** | 2026-10-19 | @CyEyes | CLAUDE.md, 01, 02, 04 | Modular Monolith, event bus, RS256, ModelGateway đa provider — viết lại theo DEC-124..137; promote bởi human (@CyEyes ủy quyền trong phiên 2026-10-19) · **2026-10-19 (DEC-144): tạm `draft` — chờ gap analysis với `_reference/` canonical, đích 2.1.0** |
| 08 | `docs/3.EXECUTION/08-DEMO-DATA-SPEC.md` | 2 | 2.1.0 | **current** | 2026-10-19 | @CyEyes | 01, 02, 03, 04, 05, 07 | ABC ~150 NV, 9 tài liệu, seed 31 metric (đối chiếu 03 v2) — viết lại theo DEC-124..137; promote bởi human (@CyEyes ủy quyền trong phiên 2026-10-19) · **2026-10-19 (DEC-144): tạm `draft` — chờ gap analysis với `_reference/` canonical, đích 2.1.0** |
| 09 | `docs/3.EXECUTION/09-BUILD-PLAN-TASKS.md` | 4 | 2.1.0 | **current** | 2026-10-19 | @CyEyes | 00–08, 10–14 | Checklist task v2 S0–S5 — viết lại theo DEC-124..137; promote bởi human (@CyEyes ủy quyền trong phiên 2026-10-19) · **2026-10-19 (DEC-144): tạm `draft` — chờ gap analysis với `_reference/` canonical, đích 2.1.0** |
| 10 | `docs/3.EXECUTION/10-API-SPECIFICATION.md` | 2 | 2.1.0 | **current** | 2026-10-19 | @CyEyes | 02, 03, 04, 05, 07 | Contract API + event + Tool Registry v2 — viết lại theo DEC-124..137; promote bởi human (@CyEyes ủy quyền trong phiên 2026-10-19) · **2026-10-19 (DEC-144): tạm `draft` — chờ gap analysis với `_reference/` canonical, đích 2.1.0** |
| 11 | `docs/3.EXECUTION/11-AGENT-WORKFLOW.md` | 2 | 2.1.0 | **current** | 2026-10-19 | @CyEyes | CLAUDE.md, 00 | Agent workflow v2 — viết lại theo DEC-124..137; promote bởi human (@CyEyes ủy quyền trong phiên 2026-10-19) · **2026-10-19 (DEC-144): tạm `draft` — chờ gap analysis với `_reference/` canonical, đích 2.1.0** |
| 12 | `docs/4.GOVERNANCE/12-DOC-AUDIT.md` | 3 | 2.0.0 | current | 2026-10-19 | @CyEyes | 00–11, 13, 14 | File này — viết lại theo DEC-124..137; promote bởi human (@CyEyes ủy quyền trong phiên 2026-10-19) |
| 13 | `docs/4.GOVERNANCE/13-DECISION-LOG.md` | 3 | 2.0.0 | current | 2026-10-19 | @CyEyes | 02–11 (Open questions) | Thêm DEC-124..137; supersede DEC-016/018/039/072 (+ một phần 010/014/073) — viết lại theo DEC-124..137; promote bởi human (@CyEyes ủy quyền trong phiên 2026-10-19) |
| 14 | `docs/4.GOVERNANCE/14-TEST-TRACEABILITY.md` | 3 | 2.0.0 | current | 2026-10-19 | @CyEyes | 03, 04, 10 | Reset danh mục test v2 (108 TC Planned) — viết lại theo DEC-124..137; promote bởi human (@CyEyes ủy quyền trong phiên 2026-10-19) |

> ~~Toàn bộ 15 file (00–14) + CLAUDE.md đều ở status `current`~~ (trạng thái đến 2026-10-18).
>
> ~~Cập nhật 2026-10-19 — Nâng cấp Aureon v2 (DEC-124): 9 file 01, 02, 03, 04, 05, 06, 07, 09, 10 chuyển `draft` (đang tái cấu trúc). `version` giữ nguyên 1.0.0 — human bump khi promote. 00, 08, 11, 12, 13, 14 giữ `current` (sẽ đồng bộ sau Phase 3 nếu bị ảnh hưởng). Kết luận Gate A: KHÔNG ĐẠT cho mọi task code chạm các file `draft` cho tới khi human promote về `current`. Chỉ task tài liệu v2 theo DEC-124 được phép làm việc trên các file này.~~
>
> **Hoàn tất Phase 3 — 2026-10-19 (DEC-124..137):** 00–14 đã viết lại cho Aureon v2 và được promote về `current`, **version 2.0.0** (human @CyEyes ủy quyền trực tiếp trong phiên). Ngoại lệ DEC-124 (đọc `_reference/`, agent sửa docs) **hết hiệu lực** sau commit Phase 3. **Gate A: ĐẠT** cho task v2. ⚠️ `CLAUDE.md` 1.1.0 vẫn mô tả v1 — human cần cập nhật (13 §5.2); khi mâu thuẫn, spec v2 trong `docs/` + DEC-125..137 thắng.
>
> **Đợt audit 2026-10-19 (tối) — Tái phân loại `_reference/` (DEC-144, DEC-145):** human bổ sung `_reference/SOURCE-BRD-v1.1-Bổ sung.md` (mới) và cập nhật `_reference/SOURCE-BRD-v1.1.md`; `_reference/` thành **Canonical Source**. 12 file spec 00–11 có thể bị ảnh hưởng → tạm **`draft`** (version giữ 2.0.0, đích 2.1.0 sau Phase 3 của đợt). 12, 13, 14 giữ `current`. **Gate A: KHÔNG ĐẠT cho task code** (S0 tạm hoãn); chỉ task tài liệu của đợt DEC-144 được làm việc trên các file này.

Note: mở lại Gate A để quyết luôn trạng thái của 12, 13, 14

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

## X. Nguồn gốc chính thức `_reference/` (Canonical Source — DEC-144)

| File | Kích thước | Sửa lần cuối | Trạng thái đợt này | Vai trò |
|---|---|---|---|---|
| `_reference/SOURCE-BRD-v1.0.md` | 58.516 B · 691 dòng | 2026-10-06 | Đã hợp nhất (DEC-124) | A-EMS |
| `_reference/SOURCE-BRD-v1.1.md` | 102.581 B · 1.264 dòng | **2026-10-19 22:28** | **Đã sửa — cần đọc lại** | AI-EOS |
| `_reference/SOURCE-BRD-v1.1-Bổ sung.md` | 34.849 B · 308 dòng | 2026-10-16 22:26 | **MỚI — chưa đọc** | Bổ sung AI-EOS |
| `_reference/SOURCE-UIUX.md` | 30.728 B · 332 dòng | 2026-10-16 | Đã hợp nhất (DEC-124) | Đề xuất UI/UX |
| `_reference/README.md` | 1.421 B · 47 dòng | 2026-10-16 | Bỏ qua (theo human) | — |

Thứ tự ưu tiên khi mâu thuẫn: DEC mới hơn DEC-144 > `_reference/` > `docs/`. Thư mục `_reference/` vẫn nằm trong `.gitignore` (không commit nội dung nguồn).

### X.1. Tài liệu `reference` trong `docs/` (ngoài chuỗi 00–14)

| File | Version | Status | Ngày | Ghi chú |
|---|---|---|---|---|
| `docs/4.GOVERNANCE/GAP-ANALYSIS-v2.1.md` | 1.0.0 | **reference** | 2026-10-19 | Gap analysis Phase 2 (`_reference/` ↔ `docs/` v2.0.0) + quyết định G1–G7 (DEC-146..153). Không phải spec build, không xét ở Gate A; tra cứu khi làm Phase 3a–3d |

Cập nhật bảng trên: `SOURCE-BRD-v1.1.md` và `SOURCE-BRD-v1.1-Bổ sung.md` **đã đọc** trong Phase 2 (2026-10-19) — kết quả ở file trên.

~~Quy tắc archive cũ (`SOURCE-BRD.md`, `SOURCE-UIUX.md` = `archived`) — **superseded bởi DEC-144**.~~

**Quy tắc:** 
- Status `archived` → agent KHÔNG được load
- Nếu cần update → tạo file mới trong docs/, không sửa file archive
- Archive chỉ để đọc, không để tham chiếu trong code

---

## Version

- **Version:** 2.0.0
- **Last updated:** 2026-10-19
- **Applies to:** Aureon v2
- **Maintainer:** @CyEyes
