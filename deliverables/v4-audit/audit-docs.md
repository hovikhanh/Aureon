# Audit tài liệu Aureon cho "v4"

Ngày audit: 2026-11-05. Nhánh `v3/m8-crm` @ `9cad717`. Vai trò: Technical Writer / doc auditor, chỉ đọc, không đổi gì trong repo.

## 0. Kết luận và phạm vi

### 0.1. Kết luận

1. **Chưa có định nghĩa "Aureon v4".** Grep toàn repo `Aureon v4|v4.0|AI-EOS v4` không ra file nào. Scope v4 phải được human quyết (xem D-01 ở §5.4).
2. **Bộ doc không dùng được như nguồn sự thật hiện tại.** Các spec chứa được hợp đồng kỹ thuật tốt (10, 05, 13, 14 cập nhật tới M8 một phần), nhưng lớp "điều hướng và governance" đã mục: 00, 01, 04, 07, 11, 12 dừng ở 2026-10-23; `12` khai sai version của 7 file; CLAUDE.md mô tả trạng thái trước khi code v3.
3. **Bốn điểm gãy gốc, cần xử lý trước khi viết lại:**
   - `docs/_reference/` bị `.gitignore:53` chặn: nguồn canonical không được version, clone mới không có. CLAUDE và 22 file khác trỏ tới `_reference/` ở gốc, đường dẫn này không tồn tại.
   - Định nghĩa `DEC-001…DEC-2xx` không có trong 13 v3 (0 dòng định nghĩa `DEC-nnn`). 591 tham chiếu trong docs/CLAUDE/STATE và 580 trong code/test/scripts (133 mã khác nhau). Theo R-DEC-81 (13:127) chúng nằm ở `docs/_archive/v2.1/4.GOVERNANCE/13-DECISION-LOG.md`, file đang bị xóa trong working tree. **Nếu commit việc xóa archive mà chưa di trú, toàn bộ DEC-* thành tham chiếu mồ côi** (git history vẫn còn).
   - `BRD_Newfeature.md` chưa được khai là nguồn canonical ở bất cứ đâu (CLAUDE:12, 00:3, AGENT.md:7 chỉ liệt kê 3 file) và mâu thuẫn trực tiếp với BRD v1.1 + 7 role + ID registry.
   - Gate B thực tế có **DEC open + blocking** (R-DEC-164, R-DEC-168), trong khi 12:56 và 09 vẫn báo gate đạt. Theo CLAUDE §6.1 thì mọi task chịu ảnh hưởng đang BLOCKED.
4. **Ba yêu cầu đã chốt nhưng code không có và không có quyết định hạ ưu tiên:** giới hạn 20 request AI/phút (07:145, 10:48, CLAUDE §5.5); 5 s/tool (07:145); **SSO + MFA** là FR-ADM-04 P0 (BRD:234, BRD:1029, 02:74,142). `RateLimitError` khai ở `core/errors.py:106` nhưng không nơi nào raise. Grep `wait_for` trong `modules/ai` rỗng. Grep `mfa|totp|sso|saml|oidc` trong `apps/api/src/app` chỉ trúng `seed/risk_seed.py`. SSO/MFA chỉ được nhắc là "backlog" trong một mệnh đề của R-DEC-36 (13:74), không có quyết định riêng hạ P0.
5. **CI backend chưa chạy từ 21/10** do job `api` `needs: secrets` (ci.yml:83) và job secrets đỏ liên tục (deliverables/GITLEAKS-AUDIT.md §2). `gh run list` hôm nay: 3 run gần nhất đều `failure`. Các con số "xanh" trong doc đều đến từ chạy cục bộ.

### 0.2. Phương pháp và giới hạn (đọc trước khi dùng số liệu)

| Đối tượng | Mức đọc |
|---|---|
| `docs/_reference/*` (4 file) | Đọc đủ. BRD_Newfeature bỏ dòng trống và 1 khối CSS mermaid ở dòng 1297 |
| 00, 12, AGENT.md, deliverables/M8-CRM-PLAN, M4-SYNC-AUDIT, T-906-DEC-PROPOSALS, 4 file handover (qua `git show HEAD:`) | Đọc đủ hoặc gần đủ |
| 13 | Toàn bộ dòng `R-DEC-*` được script parse trạng thái; đọc nội dung R-DEC-05..27, 80, 81, 89, 90, 95, 97, 124..176 |
| 01, 02, 03, 04, 05, 06, 07, 08, 09, 10, 11, 14, REBUILD-PLAN, REVIEW-REPORT, SKELETON, DEMO-SCRIPT, README, CLAUDE, STATE | **Đọc theo cấu trúc + grep có mục tiêu, không đọc từng dòng.** Kết luận "stale" là tìm được, không đảm bảo hết |
| M4-CONFORMANCE-PLAN, GITLEAKS-AUDIT, M5-GAPS, T-906-PILOT-CHECKLIST | Đọc phần tóm tắt và bảng chính |
| Không đọc | `.env`, `keys/`, `secrets/`, nội dung `docs/_archive/` (theo yêu cầu) |

Quy ước: `13:240` = file 13 dòng 240 (theo dòng hiện tại). Số đếm code là grep tĩnh, không chạy test. **UNVERIFIED** = chưa kiểm chứng được.

---

## 1. Inventory

`12 khai` = cột Version ở 12 §2 (12:20-36). `File khai` = dòng Version của chính file. `Đề xuất treo` = số dòng changelog "đề xuất" chưa promote. Mọi file tự nhận `✅ current — Aureon v3`.

| # | Đường dẫn | 12 khai | File khai | Lệch? | Đề xuất treo | Changelog cao nhất | git log -1 | Mục đích | Phụ thuộc chính | Nguồn |
|---|---|---|---|---|---|---|---|---|---|---|
| 00 | docs/1.CONTEXT/00-INDEX.md | 0.2.0 | 1.0.0 | **Có** | 0 | 1.0.0 | 2026-10-23 | Bản đồ doc, trỏ ID registry | SKELETON, REBUILD | BRD+Bổ sung+UIUX |
| 01 | docs/1.CONTEXT/01-PROJECT-OVERVIEW.md | 0.3.0 | 1.0.0 | **Có** | 0 | 1.0.0 | 2026-10-23 | Tầm nhìn, BO, P, 28 domain, MVP | SKELETON | BRD §0-2,4,18-20 |
| 02 | docs/2.PRODUCT/02-PERSONAS-PERMISSIONS.md | 0.3.0 | 1.0.0 | **Có** | 2 | 1.0.2 đề xuất | 2026-11-04 | Role, RBAC/ABAC, Autonomy, Approval | 00, 01 | BRD §3,5.2,11.3-6,17 |
| 03 | docs/2.PRODUCT/03-DASHBOARD-SPEC.md | 0.3.0 | 1.0.0 | **Có** | 2 | 1.2.0 đề xuất | 2026-11-03 | Dashboard, CEO Assistant, metric | 00, 01, 05 | BRD §11.8,12 |
| 04 | docs/2.PRODUCT/04-IDP-FEATURE-SPEC.md | 0.3.0 | 1.0.0 | **Có** | 0 | 1.0.0 | 2026-10-23 | D03 Data Capture | 00, 01 | BRD §6, Bổ sung §3 |
| 05 | docs/2.PRODUCT/05-DATA-MODEL.md | 1.2.0 | 1.2.0 | Không | 3 | 1.6.0 agent chốt | 2026-11-03 | Data Foundation, field-level | 00-04 | BRD §13 |
| 06 | docs/2.PRODUCT/06-UI-UX-SPEC.md | 1.1.0 | 1.1.0 | Không, nhưng changelog tới 1.5.0 **human duyệt** | 3 | 1.5.0 | 2026-11-03 | Persona, IA, SCR, design system | 00, 02, 03 | UIUX |
| 07 | docs/3.EXECUTION/07-TECH-ARCHITECTURE.md | 0.3.0 | 1.0.0 | **Có** | 0 | 1.0.0 | 2026-11-03 | Kiến trúc, AI Platform, NFR | 00, 01, 02, 05 | BRD §11,16-18 |
| 08 | docs/3.EXECUTION/08-DEMO-DATA-SPEC.md | 1.1.0 | 1.1.0 | Không | 0 | 1.1.0 | 2026-10-23 | Seed Công ty ABC | 00, 01, 05 | BRD §19.1,20.2 |
| 09 | docs/3.EXECUTION/09-BUILD-PLAN-TASKS.md | 1.1.0 | 1.1.0 | Không, changelog tới 1.5.0 | 4 | 1.5.0 | 2026-11-04 | Roadmap + T-* M1→M8 | toàn bộ | BRD §19 |
| 10 | docs/3.EXECUTION/10-API-SPECIFICATION.md | 1.1.0 | 1.1.0 | Không, changelog tới 1.7.0 | 3 | 1.7.0 agent chốt | 2026-11-04 | Contract API/Tool/Event | 00, 01, 02, 05, 07 | BRD §11, Bổ sung §3.9 |
| 11 | docs/3.EXECUTION/11-AGENT-WORKFLOW.md | 0.3.0 | 1.0.0 | **Có** | 0 | 1.0.0 | 2026-10-23 | EPCC, gate, loading matrix | 00-10 | BRD §11,17 |
| 12 | docs/4.GOVERNANCE/12-DOC-AUDIT.md | 1.1.0 | 1.1.0 | Không | 0 | 1.1.0 | 2026-11-03 | Gate A | toàn bộ | — |
| 13 | docs/4.GOVERNANCE/13-DECISION-LOG.md | 1.2.0 | 1.2.0 | Không, changelog tới **1.11.0** | 5 | 1.11.0 | 2026-11-04 | Gate B | toàn bộ | BRD §21.1 |
| 14 | docs/4.GOVERNANCE/14-TEST-TRACEABILITY.md | 1.1.0 | 1.1.0 | Không, changelog tới 1.8.0 | 4 | 1.8.0 | 2026-11-04 | Gate C | 00-10 | BRD §14-17 |
| — | docs/4.GOVERNANCE/REBUILD-PLAN.md | 0.2.0 | 1.0.0 | **Có** | 0 | 1.0.0 | 2026-10-23 | Kế hoạch rebuild docs R0-R3 | — | BRD+Bổ sung+UIUX |
| — | docs/4.GOVERNANCE/REVIEW-REPORT.md | **vắng** | 1.0.0 | **Có** | 0 | 1.0.0 | 2026-10-23 | Agent tự review doc 10/2026 | — | — |
| — | docs/4.GOVERNANCE/TRACEABILITY-SKELETON.md | 1.1.0 | 1.1.0 | Không | 1 | 1.1.1 đề xuất | 2026-10-31 | ID registry | — | BRD |
| — | docs/DEMO-SCRIPT.md | **vắng** | 3.0.0 | **Có** | — | 3.0.0 | 2026-11-02 | Kịch bản demo | 08, STATE | STATE, seed, e2e |
| — | README.md | **vắng** | không có | — | — | — | 2026-11-02 | Giới thiệu repo | — | — |
| — | CLAUDE.md | **vắng** | 3.0.0 (dòng 656-658) | — | — | 3.0.0, 2026-10-23 | 2026-10-31 | Hợp đồng agent | 00-14 | — |
| — | AGENT.md | vắng | không có | — | — | — | 2026-10-23 | Alias | CLAUDE | — |
| — | .github/copilot-instructions.md | vắng | không có | — | — | — | 2026-10-23 | Alias Copilot | CLAUDE | — |
| — | STATE.md | vắng | không có | — | — | Mục đầu = M6 | 2026-11-03 | Nhật ký build | — | — |
| — | deliverables/M8-CRM-PLAN.md | vắng | — | — | — | — | 2026-11-04 | Audit, kế hoạch CRM, deploy | BRD_Newfeature | — |
| — | deliverables/M4-SYNC-AUDIT.md | vắng | Draft 0.1 | — | — | — | 2026-11-03 | Đối chiếu code↔doc | — | — |
| — | deliverables/M4-CONFORMANCE-PLAN.md | vắng | — | — | — | — | 2026-11-03 | Kế hoạch M4 | — | — |
| — | deliverables/M5-PRODUCT-GAPS-REPORT.md | vắng | — | — | — | — | 2026-11-03 | Báo cáo M5 | — | — |
| — | deliverables/T-906-DEC-PROPOSALS.md | vắng | — | — | — | — | 2026-11-02 | Đề xuất dependency | — | — |
| — | deliverables/T-906-PILOT-CHECKLIST.md | vắng | — | — | — | — | 2026-11-02 | Checklist pilot | — | — |
| — | deliverables/GITLEAKS-AUDIT.md | vắng | — | — | — | — | **untracked** | Audit CI gitleaks | — | — |
| — | docs/_reference/SOURCE-BRD-v1.1.md | vắng | 1.1 Draft for review (dòng 11) | — | — | — | không version | Canonical | — | — |
| — | docs/_reference/SOURCE-BRD-v1.1-Bổ sung.md | vắng | không rõ | — | — | — | không version | Canonical | — | — |
| — | docs/_reference/SOURCE-UIUX.md | vắng | v1.0 | — | — | — | không version | Canonical | — | — |
| — | docs/_reference/BRD_Newfeature.md | vắng | không có | — | — | — | không version | CRM, **chưa khai canonical** | — | — |

Nhận xét:
- 7 file bị 12 khai sai version (00, 01, 02, 03, 04, 07, 11) và REBUILD-PLAN. 12 không theo dõi REVIEW-REPORT, DEMO-SCRIPT, CLAUDE, STATE.
- 27 dòng changelog ghi "đề xuất, chờ human duyệt" trong khi nội dung đã chạy trên code. M4-SYNC-AUDIT §4.7 V-1 đã nêu, chưa xử lý.
- Changelog 13 không tuần tự: 13:302 (1.0.0) nằm giữa 1.5.0 và 1.4.1.
- `last_reviewed` cũ nhất là 2026-10-22, tức đúng 14 ngày hôm nay; từ ngày mai Gate A bật cảnh báo cho 00 và REBUILD-PLAN, 2026-11-07 cho phần lớn file ghi 10-23.
- 12:56 là dòng cuối ghi "Gate B: 0 DEC open+blocking" (ngày 2026-10-23), đã sai.

---

## 2. Verdict từng file

Khuyến nghị dùng: **KEEP** giữ, **UPDATE** cập nhật cục bộ, **REWRITE** viết lại, **MERGE** gộp, **ARCHIVE** chuyển lịch sử.

### 2.1. Tổng hợp

| File | Cần? | Trùng | Mâu thuẫn nguồn | Mô tả đúng code? | Khuyến nghị |
|---|---|---|---|---|---|
| 00 | Có | Một phần với CLAUDE §9 | — | Sai trạng thái | **REWRITE** ngắn |
| 01 | Có | CLAUDE §1 | US count | Trạng thái sai | **REWRITE** cho v4 |
| 02 | Có | — | Thiếu persona CRM | Đúng phần lớn | **UPDATE** |
| 03 | Có | — | Thiếu CRM | Thiếu M6-M8 | **UPDATE** |
| 04 | Có | Handover (đã xóa) | Doc type P0 | Sai số doc type, thiếu as-built | **UPDATE** |
| 05 | Có | — | Không | 41 ENT so với 101 bảng | **REWRITE** phần catalog |
| 06 | Có | — | Không | Thiếu route M6-M8 | **UPDATE** |
| 07 | Có | CLAUDE §2, §4 | 13 vs 14 thành phần | Sai tên module; NFR chưa có | **UPDATE** |
| 08 | Có, xem lại | DEMO-SCRIPT | Không | Có thể lệch | **UPDATE** |
| 09 | Có | STATE | — | Đúng tới M8 | **MERGE/tách** |
| 10 | Có | — | 13 vs 14 metadata | Đúng nhất, có contract test | **KEEP + UPDATE** |
| 11 | Có | CLAUDE §6-8 | — | Sai quy trình hiện tại | **MERGE** với CLAUDE |
| 12 | Có, đổi cách làm | — | — | Sai | **REWRITE** thành sinh tự động |
| 13 | Có | STATE | — | Mở/đóng chưa sạch | **UPDATE + di trú DEC** |
| 14 | Có | — | — | Đúng tới M8, số TC-Planned treo | **KEEP + UPDATE** |
| REBUILD-PLAN | Không | 00, 13 §1 | — | Hết hiệu lực | **ARCHIVE** |
| REVIEW-REPORT | Không | 12 | — | Hết hiệu lực | **ARCHIVE** |
| SKELETON | Có | 00 §4 | Số US | Số đếm cũ | **UPDATE** |
| DEMO-SCRIPT | Có | 08 | — | Mâu thuẫn tự thân | **UPDATE** |
| README | Có | — | — | Sai nhiều | **REWRITE** phần trạng thái |
| CLAUDE | Có | 11 | — | Sai nhiều | **REWRITE** (chỉ human) |
| AGENT, copilot | Có | Alias | — | Trỏ file đã mất | **UPDATE** nhỏ |
| STATE | Có, thu gọn | 09, deliverables | — | Thiếu M7, M8 | **UPDATE + ARCHIVE** phần v2.1 |

### 2.2. Chi tiết bằng chứng

**00-INDEX**
- 00:66 "Docs-first P0 — code/app/migration ở đợt sau": sai, đã qua M1-M8 và deploy (M8-CRM-PLAN:4).
- 00:21-34 cột "Phase viết R0-R3" và thứ tự đọc 00:16 bắt đầu bằng REBUILD-PLAN: quy trình đã xong.
- 00:51 "~110 US": BRD thật có 108 mã US (đếm regex). CLAUDE:368 ghi 141, ba con số khác nhau.
- 00:3 không nêu BRD_Newfeature; 00:11,63 trỏ `docs/_archive/v2.1/` đã xóa.

**01-PROJECT-OVERVIEW**
- 01:4 "phạm vi docs-first P0"; 01:299 tương tự. Dùng `main` với nghĩa "v2.1" (01:298-300), trong khi `main` nay là v3 (`854606b`, có tag `v3.0.0-mvp`).
- Không ghi trạng thái MVP, không có M4-M8, không có CRM (R-DEC-175).
- OQ-01..03 ở 01:325-327: OQ-02 và OQ-03 đã đóng trên thực tế (03 §4.2, 07 AIC-*), chưa ghi.

**02-PERSONAS-PERMISSIONS**
- Đã có R-DEC-173 (02:132), tốt. Grep `Sales Executive|Presales|Marketing` trong 02/03/04/05/06/SKELETON rỗng: chưa có quyết định ánh xạ.
- 02:42 "Doanh nghiệp tạo thêm vai trò tùy biến" so với R-DEC-174 (13:250): ma trận chỉ đọc, custom role để DEC riêng. Doc nói có, sản phẩm chưa có.
- 02:186 OQ-02-04 còn ghi "hoãn sang đợt code" dù đợt code đã xong.
- OQ-13-M5-01 (13:235): RACI cho MGR mức C, API cho MGR tạo được.
- "7 role + AI Agent": BRD:147 nói **7 vai trò, trong đó AI Agent** (tức 6 người + 1 agent). Code `ROLE_REFS` có đúng 7 mã (permission_matrix.py). Cách nói "7 role + AI" ở CLAUDE:51, 02, 01, README:35 đếm dư 1.

**03-DASHBOARD-SPEC**
- Grep `Funnel|phễu|Forecast|dự báo có trọng số` trong 03 và 06 rỗng: M8 đã làm phễu, dự báo (R-DEC-175) nhưng spec không có.
- Bảng METRIC-* (03 §4.2) được contract test giữ 2 chiều (R-DEC-149): tin được.
- OQ-03-04 còn mở (4 ô mặc định).

**04-IDP-FEATURE-SPEC**
- Doc không đổi từ 10-23. 04:18 nói P0 có 14 loại chỉ phủ tập con; 08:156,165 nói 6 loại P0; code có **7** mã (`SEED_TYPES` 5 mã: PLAN_KPI_OKR, PERIOD_REPORT, HR_ROSTER, FINANCE_REPORT, MEETING_MINUTES, cộng INVOICE, OTHER ở migration trước, catalog/__init__.py:11, 0019_capture_seed_doctypes.py:9).
- 04:80-91 bảng trạng thái không có `AUTO_APPROVED`, `DUPLICATE`, `EXTRACTING`, `VALIDATING`, trong khi code dùng các trạng thái này (`idp/services/pipeline.py:6-8`, `inbox_service.py:42-44`, `upload_service.py:162`). Máy trạng thái trong spec khác code.
- OQ-04-02: STT đã có R-DEC-166 (hoãn STT thật), nhưng 04:25,38 vẫn nói C2 có voice P0. Lệch sản phẩm thật.
- Thiếu field schema as-built: đã nằm ở handover, đang bị xóa (xem §3.2).

**05-DATA-MODEL**
- 41 `ENT-*` so với 101 `__tablename__` trong code, M8-CRM-PLAN §8.1 đếm 115 bảng có dữ liệu trong dump. M4-SYNC U-1 nêu "45 entity nền v2.1 chưa có doc", P7 chưa làm. CLAUDE:370 ghi 79 ENT.
- `sales.deal_stage_history`, `DealStageHistory` không xuất hiện trong 05 lẫn 10.
- §2 có 12 mục field-level xếp theo phase (M1.1…M3.4) thay vì theo domain: file đọc như nhật ký.
- OQ-05-01 (05:646) đã bị CLAUDE §6.1 "DEC-154" trả lời ngược: hai nơi nói khác nhau, chưa đóng.

**06-UI-UX-SPEC**
- Grep route: `/business/sales/pipeline`, `/business/{finance,sales,hr}/records`, `/home/alerts` đều 0 lần trong 06. Code có 48 `page.tsx`, gồm 11 trang `/business/*`.
- Grep `SCR-` có 36 mã; M4-SYNC G-3 ghi 35; CLAUDE:370 ghi 31.
- 06:384 "`main` có SCR-01..28", dùng `main` nghĩa cũ.
- OQ-06-01, 04, 05 còn mở; OQ-06-06 theo 13 §3 B6.

**07-TECH-ARCHITECTURE**
- 07:43 module `ai_core`: thực tế thư mục là `modules/ai` (ls). CLAUDE:234,282,575 cũng sai.
- 07:19 "1 schema PostgreSQL/domain-group".
- 07:47 "13 thành phần" nhưng 07:66 có AIC-14, BRD:636-651 liệt kê **14**. CLAUDE §9 lặp "13 thành phần".
- 07:53,55,145: rate limit, 5 s/tool chưa hiện thực (§0.1).
- U-2 M4-SYNC: CLAUDE §2.2 ghi "MinIO (dev) / S3 (prod)" nhưng chỉ có `LocalObjectStore` (core/storage.py:41,124), MinIO chạy trong compose mà không dùng. Grep `MinIO|S3|object store` trong 07 rỗng: tài liệu kiến trúc không nói gì về lưu trữ file.
- 07:204-206 OQ-07-02, 03 còn mở.
- BRD NFR-PERF-05 "50 tenant × 1.000 user" chép ở 07:175, trái R-DEC-07 single-tenant.

**08-DEMO-DATA-SPEC**
- 08:156 "6 doc type"; 08:165 tương tự; code 7 mã.
- DEMO-SCRIPT:3-4 ghi 154 nhân sự; 08/CLAUDE ghi ~150. Chấp nhận được nhưng cần thống nhất.
- STATE:118-127 ghi LIVE CUTOVER 2026-11-02: DB bị xóa data demo, tạo `admin@abc.com`. M8-CRM-PLAN §8.1 sau đó lại đăng nhập 10 tài khoản demo trên stack chính. **Chưa rõ môi trường nào là "demo", môi trường nào là "live"** (UNVERIFIED).

**09-BUILD-PLAN-TASKS**
- §6.23 M8 đã có (09:589), tốt nhất nhóm governance.
- Còn 3 ô `☐` thật: T-1209 (R-DEC-168), T-1210, T-1405.
- File gom cả roadmap sản phẩm §1-§5 (lỗi thời, dùng `main`) và 470 dòng lịch sử task §6. Nên tách.
- OQ-09-04 (chọn DN pilot) còn mở.

**10-API-SPECIFICATION**
- Có contract test 3 chiều (TC-M4-01..04): phần EP, TOOL, METRIC, ACT là đáng tin nhất. Code 328 route; 248 mã `EP-<DOMAIN>-NN` và 84 mã legacy `EP-nn`.
- 10:5 tự nhận "chiều contract mức khái niệm" trong khi đã field-level.
- 10:77-98 "13 thuộc tính", bảng có 13 dòng đánh số **cộng** `owner` đánh dấu "—", BRD:668 liệt kê 14 tên. Doc chú thích "BRD liệt kê 13" là đếm sai.
- 10:75 "`main` (43 tool)": hiện 54. Không có EP mới cho M8 (đúng theo R-DEC-175).
- 10:48 429 đi kèm rate limit chưa có.

**11-AGENT-WORKFLOW**
- 11:5,28,30-36,46-48,105: toàn bộ logic "đợt docs vs đợt code" của R-DEC-09, đã hết hiệu lực.
- 11:13 "Branch-aware (CLAUDE.md §0)": CLAUDE 3.0.0 đã bỏ Branch-aware.
- Quy trình thực tế S→C→F→B→N→R (R-DEC-19) không có trong 11.
- Trùng CLAUDE §6-§8. Đang có 2 ma trận loading khác nhau (CLAUDE §8 theo T-1xx…T-5xx của v2.1, 11 §4 theo domain).

**12-DOC-AUDIT**
- 12:9-14 mô tả trạng thái R-DEC-09; bảng 12:20-36 sai (§1); 12:47-50 toàn OQ cũ.
- Phải thay bằng bảng **sinh từ script**: đọc Version, git log, đếm H1, fence.

**13-DECISION-LOG**
- Header 13:3: `R-DEC-*` là nhãn tạm "cho tới khi human cấp DEC". Thực tế: 178 dòng R-DEC, 0 dòng DEC. Human chưa bao giờ cấp số; cần chính thức hóa.
- Trùng số gây nhầm: R-DEC-138 (Evaluation) vs DEC-138 (ClamAV); R-DEC-141 (RAG) vs DEC-141 (argon2); R-DEC-125 vs DEC-125; R-DEC-153/154 vs DEC-153/154.
- Nguồn quyết: script đếm 90 dòng ghi "human", 39 ghi "agent", 49 không ghi người quyết.
- Header 13:4 vẫn ghi ngày 2026-10-23.
- 13:265-277 B1-B7 vẫn chờ CEO sau khi đã xong MVP.

**14-TEST-TRACEABILITY**
- 247 Passed, 133 Implemented, 9 Planned, 1 Failed (đếm từ khóa, có lẫn dòng quy ước và changelog).
- Các `Planned` treo: TC-M32-08, TC-M33-08, TC-M34-09 (14:337,352,368).
- 14:30 R-DEC-09; 14:565 OQ-14-02 "BE 777/FE 18/E2E 30".
- Số cuối theo M8-CRM-PLAN §7: **pytest 1450 pass, contract 44, Vitest 487/55 file, E2E 91/91** (chạy cục bộ). Grep tĩnh: 1182 hàm `test_`, 197 file; 340 `it/test` FE; 33 spec, 146 `test(`.

**REBUILD-PLAN, REVIEW-REPORT**
- REBUILD:12,74-76 so sánh `main` (v2.1) với `ai-eos`; REBUILD:115 "gitignored". REVIEW:78-81,97 là việc tháng 10. Không còn tác dụng vận hành, nhưng 00:16 còn trỏ.
- Một mục đáng giữ trước khi archive: REVIEW:78-79 A1, A2 (FR-PTN/PRD/ENG là prefix agent tự đặt; NFR-AUD/OBS/COST) chưa ai xác nhận.

**TRACEABILITY-SKELETON**
- SKELETON:98 "~110 US". Dữ liệu ID vẫn là registry, nhưng số đếm cũ.
- Chưa có namespace CRM. M8-CRM-PLAN:6 tự đặt `CRM-*`, chưa đăng ký.
- SKELETON:202-204 trỏ REBUILD-PLAN Q1-Q6, cần đổi khi archive REBUILD-PLAN.

**DEMO-SCRIPT**
- DEMO:3-4 nói M3.5 "đang tiến hành"; STATE:744-761 đã đề xuất sửa, chưa làm.
- DEMO:548 "Áp dụng cho: code tại mốc M1 DONE", mâu thuẫn dòng 3.
- DEMO:48 "10 service" nhưng DEMO:448 "9 service + Mailpit".
- DEMO:508 R-DEC-80 chờ số DEC.
- Chưa có M5-M8: **UNVERIFIED** từng chặng (R-DEC-173 đổi người duyệt tuyển dụng; grep `CFO.*duyệt|hiring` trong DEMO-SCRIPT không ra, nên kịch bản có thể đã không nói về CFO).

**README**
- README:30-31 "9 service": compose có 10 (`postgres redis minio ollama clamav api celery-worker celery-beat mailpit web`).
- README:56 "cfo@ … duyệt kế hoạch tuyển dụng (cổng ngân sách)": **trái R-DEC-173** (13:249).
- README:55 "13 alert"; DEMO:105 "14"; STATE:610 "13 OPEN"; STATE:591 "25 OPEN" (lịch sử).
- README:136-137 "770 passed, 18": cũ.
- README:66 chỉ tới M3. README:71 "Dashboard F.O.C.U.S" trong khi 03 dùng 3 cấp, trụ F.O.C.U.S là tùy chọn (OQ-03-01).
- README:11 "đang refactor dần".
- README:16 `_reference/` và `docs/_archive/v2.1/`.

**CLAUDE.md** (chỉ human sửa, CLAUDE §6.6 rule 10)

| Dòng | Sai | Thực tế |
|---|---|---|
| 12, 16, 19, 412, 414, 611 | `_reference/` ở gốc | `docs/_reference/`, gitignored |
| 16, 412 | Cấm đọc `_reference/SOURCE-BRD-v1.0.md` | File không tồn tại |
| 16, 18, 79, 410 | `docs/_archive/v2.1/` | Đã xóa khỏi working tree |
| 74-81 §1.6 | Trạng thái 2026-10-23, "Kế tiếp: phân rã build v3" | M1-M8 xong, deploy M8 |
| 80 | pytest ~777, Vitest 18, E2E 30, 9 service | 1450 / 487 / 91, 10 service |
| 68 | "Nền code v2.1 hiện mang 10 role" | Enum đã 7 mã (R-DEC-12); chỉ còn `LEGACY_ROLE_MAP` phục vụ seed/test |
| 112 | Hàng lỗi 2 ô "DB \| DB", vừa "11 schema" vừa "10 schema" | 10 schema có bảng; `dashboard` không có schema |
| 119 | RAG "LlamaIndex + pgvector" | Không dùng (grep pyproject rỗng; M4-SYNC S5) |
| 117 | "PaddleOCR (mặc định) / Google Vision" | Mặc định `stub`, Vision chưa có code (R-DEC-146) |
| 234, 282, 575 | `ai_core` | `modules/ai` |
| 241 | `app/(app)/[locale]/...` | Không có segment locale (R-DEC-25) |
| 252 | `core/rate_limit` | Không tồn tại |
| 253 | `db/` | `core/db.py` |
| 255 | `routes.py schemas.py...` | Thư mục `routes/ schemas/ services/` |
| 261, 477 | `secrets/`, "Mount ./secrets" | `keys/` (R-DEC-81) |
| 312 | "chỉ ROLE-01, ROLE-04 (ROLE-05…)" | ID v2.1; §1.4 dùng ROLE-CEO…; đúng phải là CEO + DIR khối O (`field_policy.sees_level4`) |
| 368-370 | 141 US, 79 ENT, 32 METRIC, 31 SCR, 28 EVT, 43 TOOL | 108 US; 41 ENT doc/101 bảng; 34 METRIC; 36 SCR; 40 EVT (M4-SYNC G-3); 54 TOOL |
| §5.5 | "bảng 10 §7" | Bảng ở 10 §2.3 |
| 575-578 | Dải T-1xx…T-5xx, "Seed S0/S5" | T-6xx…T-14xx, M1-M8 |
| 592 | "P01–P09, roadmap S0–S5" | P01-P11, M1-M3 + 5 phase |
| §2.1 | DeepSeek Harness, OmniRoute `cc/claude-opus-5-5` | **UNVERIFIED**; chưa thấy dấu vết harness trong repo |
| §1.1-1.3 | "13 thành phần" | 14 |

---

## 3. Tham chiếu treo

### 3.1. Bảng tổng hợp

| Mục tiêu đã mất/sai | Tham chiếu sống | Mức | Xử lý đề xuất |
|---|---|---|---|
| `docs/_archive/v2.1/*` | **25 file:** CLAUDE, AGENT, README, STATE, copilot-instructions, M4-CONFORMANCE, M8-CRM-PLAN, 15 file 00-14, REBUILD, REVIEW, SKELETON | Cao, nhất là 13:127 trỏ §DEC-169 của file đã mất | Đổi thành "lịch sử trong git tag `v1-main-final`/commit trước xóa", hoặc giữ một file di trú DEC |
| `docs/handover/*` | **Code:** `idp/services/retention_service.py:4,67`, `tests/integration/idp/test_retention_t1010.py:7`, `scripts/check_env.sh:4`. **Doc:** 13:228, 09:542 ("handover §5.1"), STATE:82,86, M4-CONFORMANCE:20, M4-SYNC §4.4 | Cao, code trỏ tới file đã mất | Khôi phục nội dung vào runbook mới rồi sửa docstring |
| `docs/BRD_Newfeature.md` | deliverables/M8-CRM-PLAN.md:5 | Trung bình | Sửa thành `docs/_reference/` |
| `@docs/BRD_newfeature.md` (sai hoa-thường) | .prompt/prompt_update_feature.md | Thấp | File tạm |
| `BRD_Newfeature` không đường dẫn | 13:252, `apps/web/src/features/crm/crm.ts` | Thấp | OK nếu tên đổi thì sửa |
| `_reference/` ở gốc | **23 file** (chưa tính `.gitignore`): CLAUDE (9 dòng), 11 (8), AGENT (2), copilot (2), README, 00-14, REBUILD, REVIEW, SKELETON, `.claude/commands/gen-spec.md` | Cao | Đổi hàng loạt hoặc chốt symlink |
| `_reference/SOURCE-BRD-v1.0.md` | CLAUDE:16,412, AGENT:9, copilot:8 | Thấp | Bỏ dòng |
| `secrets/` (nơi để khóa) | CLAUDE:261,477; `docker-compose.yml:25`; `scripts/generate_keys.sh:3,5`; `core/config.py:44-45` | **Cao**, xem §5.3 | Làm follow-up R-DEC-81 |
| `gen_jwt_keys` | Đã sửa ở CLAUDE §3.1 | — | — |
| `DEC-xxx` | 591 doc + 580 code | **Rất cao** | Di trú trước khi commit xóa |
| Lệnh Gate "Từ chối đọc `_reference`" | gen-spec.md:19 "Không đọc hoặc sửa các file trong `_reference/`" **trái** CLAUDE:414 (không cấm đọc) | Trung bình | Sửa gen-spec |
| `doc-reviewer.md`, `gen-spec.md` | Chạm lần cuối 2026-10-17, trước v3 | Trung bình | Rà lại |

### 3.2. Nội dung handover có bị mất không?

Các file vẫn lấy lại được bằng `git show HEAD:docs/handover/<file>`. Sau khi commit xóa thì chỉ còn trong history. So với doc sống:

| File handover | Nội dung | Còn ở đâu | Chưa có ở đâu khác |
|---|---|---|---|
| **IDP_Extraction_Schema** | Bảng field 5 doc type (8/17/7/13/1 trường, `req`, `CRIT`), VR rules, action chain | Field nằm trong code (`catalog/*.py`, migration); action chain ở 09:303 sơ lược | **Bảng spec dạng đọc được chỉ có ở đây.** 04/05/10 không có `HR_ROSTER` (grep chỉ ở 09:303, DEMO-SCRIPT). Snapshot đã cũ: thiếu FINANCE_REPORT, MEETING_MINUTES |
| | Quy tắc STP "không có trường CRIT nào", chuỗi lỗi live `chat()` vs `extract()` | Một phần R-DEC-163 | Giải thích vì sao INVOICE/HR_ROSTER luôn qua review |
| **Data_Inbox_MVP_Workflow** | Ma trận vai trò ↔ `idp:*` live; UX contract camera C4 (secure context, ≤ 20 ảnh, trạng thái lỗi); bảng file nguồn | 02/10 có quyền; `camera.ts` có logic | **UX contract C4** không thấy ở 06 (UNVERIFIED chi tiết); bảng doc type ↔ action ↔ permission gộp |
| **IDP_Operations** | Bảng container/port, `.env` IDP, smoke test, **SQL FK-safe §5.2-5.3**, troubleshooting §6 | Job tự động (R-DEC-152), DEMO-SCRIPT một phần | **Không có runbook vận hành nào khác** trong doc set. SQL escape hatch, bảng troubleshooting, quy tắc xóa an toàn chỉ có ở đây |
| **IDP_Sample_Data** | Manifest `data/`, doc type ánh xạ, hành vi kỳ vọng, cách sinh lại | DEMO-SCRIPT §3 (manifest), §2.1 (sinh lại) | Bảng "hành vi pipeline kỳ vọng"; thiếu `DOC-11-sao-ke-so-du-q3-2026.xlsx` nên cũng đã cũ |

Kết luận: **không mất quyết định nào** (không chứa DEC riêng), nhưng **có mất tri thức vận hành** và 3 tham chiếu trong code/script. Khuyến nghị: khôi phục nội dung vào `15-OPERATIONS-RUNBOOK` và 04 §as-built, cập nhật theo code, rồi mới commit việc xóa.

---

## 4. Mâu thuẫn nội bộ nguồn (`docs/_reference`)

Không đề xuất sửa `_reference`. Giải pháp đề xuất là một quyết định ưu tiên ghi ở 13. Tên viết tắt: **BRD** = SOURCE-BRD-v1.1.md, **BS** = Bổ sung, **UX** = SOURCE-UIUX.md, **NF** = BRD_Newfeature.md.

### 4.1. Thứ bậc nguồn

| # | Mâu thuẫn | Vị trí | Cách hiểu cạnh tranh | Đề xuất | Tác động |
|---|---|---|---|---|---|
| S-01 | NF không có trạng thái | CLAUDE:12 vs thư mục | (a) canonical mới; (b) yêu cầu đầu vào cho một phase | **(b):** NF là requirement input, thứ bậc dưới BRD; phần được duyệt mới vào spec | Nghiệp vụ: phạm vi CRM. Governance: quy tắc "docs ↔ _reference ưu tiên _reference" nếu áp cho NF sẽ lật R-DEC-05/08/10 |
| S-02 | BS tự nhận chỉ là bản rà soát của v1.0, BRD đã hợp nhất nó | BS:17; BRD:14,20 | (a) BS còn hiệu lực; (b) BS là lịch sử | **(b):** BRD thắng khi khác BS; BS chỉ giữ rationale | Hết mâu thuẫn §4.2 |
| S-03 | BRD là "Draft for review" | BRD:11 | Canonical nhưng chưa duyệt | Human xác nhận bản chốt, hash vào manifest | Pháp lý nội bộ |

### 4.2. BRD v1.1 ↔ Bổ sung

| # | Mâu thuẫn | BS | BRD | Đề xuất | Tác động |
|---|---|---|---|---|---|
| S-04 | Mã domain Data Capture | BS:11,48 **Domain 22**, "21 domain còn lại" (BS:50) | BRD:240 **D03**; BRD:586 D22 = Product | BRD | Không có; đã dùng D03 |
| S-05 | Số doc type | BS:86-98: 13 loại, 5 MVP | BRD:298-311: 14 loại, 6 P0 (thêm Finance Lite tóm tắt BRD:303) | BRD | 04, 08 |
| S-06 | Mã US-DC khác nghĩa | BS:261 US-DC-009 Finance hóa đơn, P1; BS:262 010 Legal/Sales; BS:263 011 CEO lineage **P0** | BRD:926 009 Employee chụp ảnh **P0**; BRD:927 010 Finance; BRD:928 011 Legal/Sales | BRD; lineage thuộc US-CEO-007 (BRD:1015) | Test traceability; UX:29 dùng US-DC-010 cho Reviewer, không khớp bản nào |
| S-07 | Tên epic | BS:249 "EPIC R" | BRD:918 "B. Data Capture"; BRD:1009 R = CEO Assistant | BRD | Nhỏ |
| S-08 | Nhãn ưu tiên | BS dùng MVP/Phase 2 (BS:63-72) | BRD dùng P0/P1 (BRD:275-284) | BRD | Nhỏ |
| S-09 | Workflow Engine thuộc đâu | BS:240 "bổ sung Domain 21" | BRD:244 D04; BRD:580 D21 = Contract | BRD | Không |
| S-10 | BS tham chiếu số mục BRD v1.0 ("mục 38, 39, 77") | BS:167-170,185 | v1.0 không có trên đĩa | Coi là lịch sử | Không truy được |

### 4.3. BRD nội bộ

| # | Mâu thuẫn | Vị trí | Đề xuất | Tác động |
|---|---|---|---|---|
| S-11 | UC MVP: câu dẫn liệt kê 01,02,03,06,07; bảng đánh UC-04 **P0** | BRD:871 vs BRD:878 | Bảng thắng (đã làm UC-04, R-DEC-143) | Đã giải quyết thực tế, chưa ghi |
| S-12 | 7 vai trò gồm AI hay cộng AI | BRD:147,170-178 "7, trong đó AI Agent" | Dùng cách nói "6 role người + ROLE-AI" | Sửa văn bản toàn doc |
| S-13 | "50 tenant × 1.000 user" vs một doanh nghiệp thí điểm | BRD:1039 vs BRD:1132, BRD:1236 mở | Phụ thuộc B1 | Kiến trúc tenant, NFR tải |
| S-14 | "13 thành phần", "13 metadata" do doc phái sinh đếm; BRD có 14 | BRD:636-651, BRD:668 | Đính chính doc thành 14 | 07, 10, CLAUDE, 00, 01 |
| S-15 | Phạm vi "CRM" nằm trong tích hợp ngoài lẫn domain nội bộ | BRD:29,262 vs BRD:553 | NF chọn tự xây; cần quyết định "CRM ngoài vs CRM trong" | FR-INT, D06 |
| S-16 | SSO/MFA ghi P0 nhưng BRD §19.1 không xếp vào mốc nào | BRD:206,234,1029 vs BRD:1130-1132 | Coi là P0 chưa làm, hoặc hạ bằng DEC. Hiện **không có code**, chỉ nhắc backlog ở R-DEC-36 (13:74); 09, 14, T-906 không nhắc | Bảo mật, điều kiện pilot |

### 4.4. BRD ↔ UIUX

| # | Mâu thuẫn | UX | BRD | Đề xuất | Tác động |
|---|---|---|---|---|---|
| S-17 | Ai bật kill switch; bật xong thế nào | UX:204 Admin **và CEO**; L3/L4 **chuyển L2** | BRD:237, BRD:1007, BS:195 Admin; **tắt toàn bộ** WRITE/EXECUTION | Code có 2 mode: `WRITE_OFF` hạ về L2, `L0` tắt hẳn (autonomy.py:11,71). Ghi chính thức cả hai vào 02 | Hành vi bảo mật; câu "tắt" trong BRD chỉ đúng mode `L0` |
| S-18 | Ví dụ L3 ghi tiền | UX:189 "nhập hóa đơn đã duyệt" | BRD:713,1091 ghi tài chính L2 | BRD | Nếu làm theo UX là vượt quyền |
| S-19 | Ví dụ L4 | UX:190 phân loại email, gắn nhãn | BRD:715 cập nhật KPI từ nguồn tin cậy | Không chặn; L4 khóa. Quyết khi mở Phase 5 | Thấp |
| S-20 | 5 persona vs vai trò | UX:20-30 (gộp Director/Manager) | BRD:172-178 | Không mâu thuẫn thật; ghi ánh xạ ở 02 | Thấp |
| S-21 | Employee hỏi AI phạm vi nào | UX:80 "dữ liệu của tôi và team" | BRD:175 cá nhân; BRD:704 task team READ | BRD:704 + scope 02 | RBAC AI |
| S-22 | Offline mobile | UX:176 offline queue; UX:175 sinh trắc | R-DEC-25 "PWA không offline" | R-DEC-25 cho P0; UX cho backlog | Backlog |
| S-23 | Số US | UX:9,34 "khoảng 100" | BRD thật 108 | Đếm thực | Nhỏ |

### 4.5. BRD ↔ BRD_Newfeature

| # | Mâu thuẫn | NF | BRD / repo | Đề xuất | Tác động nghiệp vụ, kiến trúc, code |
|---|---|---|---|---|---|
| S-24 | **D17 P0 Lite vs CRM đầy đủ** | NF:1457-1468 Lead, Account, Contact, Activity là **Phase 1 MVP** | BRD:553,559-560: Lead/Account/Contact P1; BRD:940 US-SAL-001 P1; BRD:1141 Phase 2 | Với v4: nâng D17 lên phạm vi v4 bằng DEC, không gọi là MVP | Phase 1 thực tế chỉ làm một phần (R-DEC-175). R-DEC-176 là cửa chính |
| S-25 | **Persona vs 7 role** | NF:68-76 Sales Director, Sales Manager, Sales Executive, Presales, Marketing, CRM Admin; NF:950 Marketing Manager không có trong bảng | BRD:172-178; R-DEC-08 | **Không tăng role.** Ánh xạ: Director→DIR{C}; Manager→MGR; Executive→EMP + quyền `sales:*` scope `own`; Presales→EMP + scope `assigned`; Marketing→EMP/DIR{C} + scope riêng; CRM Admin→ADM | Hiện **EMP không có quyền sales** (M8-CRM-PLAN §5.2-h). Muốn làm phải đổi `permission_matrix.py`, thêm scope `own/assigned/limited`, đổi 02 |
| S-26 | **CEO có sửa sales không** | NF:1328,1331-1333 CEO: Yes (Edit, Stage, Close) | R-DEC-175 (13:251) CEO không chuyển giai đoạn; `sales:write` scope `t` | **Giữ R-DEC-175** nếu CEO là người xem; hoặc mở theo NF. Cần human chọn | Đổi RBAC + E2E `m8-*` |
| S-27 | Sales Director "All" vs DIR "khối" | NF:1323-1335 | BRD:173 | DIR{C} đọc toàn bộ khối C là tương đương | Không đổi |
| S-28 | **AI ở Phase 3 vs AI-first mọi module** | NF:1496-1497, DEC-010 (NF:1517) AI Assistant Phase 3 | BRD:128-143 AI-R01..12 bắt buộc mọi module; BRD:561 FR-SAL-03 | BRD: mọi thực thể CRM mới phải có tool đọc, event | Mỗi bảng CRM cần `TOOL-*`, event, Extraction Schema. R-DEC-176 **chưa có mục này**: thiếu |
| S-29 | Calendar Phase 3 | NF:1493, DEC-009 | BRD:1158 P0, đã làm (R-DEC-17) | Activity dùng Calendar sẵn có | R-DEC-176 §5.2-i |
| S-30 | **3+ danh sách stage** (M8-CRM-PLAN §5.2-c ghi 3, thực tế 6) | (a) NF:567-570 Qualified, Proposal, Closed Won/Lost. (b) NF:745-770 Qualification, Discovery, Proposal, Negotiation, Contract, Won. (c) NF:1395-1398 Discovery, Demo/POC, Proposal, Negotiation. (d) NF:1305-1316 12 bước. (e) NF:914-919 funnel 6 bậc. (f) NF:1020-1024 Forecast Category cũng dùng Closed Won/Lost | (g) BRD:556. (h) Code `lead/qualified/proposal/negotiation/closed_won/closed_lost` (sales/models:39). (i) R-DEC-90 ghi `open/closed_won/closed_lost` | Phân biệt 3 khái niệm: **Stage** (cấu hình theo pipeline, mặc định 6 giá trị code + thêm Discovery, Demo/POC, Contract theo cấu hình), **Forecast Category**, **Funnel step**. Sửa R-DEC-90 | Enum DB `deal_stage` phải thành bảng `pipeline_stages`; ảnh hưởng dữ liệu cũ, `crm.ts`, metric win rate |
| S-31 | Thứ tự chuyển đổi Lead | NF:81 Lead → Account/Contact/Opportunity | BRD:556 Lead → Contact → Account | NF chi tiết hơn | Thấp |
| S-32 | **Lead = Client hay thực thể riêng** | NF:79-81, NF:196-214 | R-DEC-90 alias; 05:552 "Không tạo entity Lead" | R-DEC-176 thay thế R-DEC-90 cho v4; ghi supersede | Migration, 05, 10 |
| S-33 | **Một hay nhiều sản phẩm** | NF:542 `product_id` đơn, bắt buộc; vs NF:525, NF:582, NF:1511 nhiều | Human chốt nhiều (R-DEC-176) | `deal_products` | Migration |
| S-34 | Contact role đơn hay nhiều | NF:455 Enum; NF:480 "một hoặc nhiều" | — | Nhiều (M8 §5 `roles[]`) | Thấp |
| S-35 | Trường bắt buộc khác nhau | NF:544 `pain_point` Yes vs NF:581 chỉ Account + Owner; NF:555 Next Action luôn bắt buộc vs NF:1381 chỉ khi đang mở | Theo Stage (NF:1377 BR-005) | Validation |
| S-36 | Thiếu `pipeline_id`, `stage_entered_at`, `forecast_category` | NF:536-557 vs NF:583, NF:786, NF:1017 | Bổ sung ở R-DEC-176 (đã có một phần) | Schema |
| S-37 | Export Must hay Should | NF:1364 NFR-016 Must vs NF:101,905,1121 Should | Must ở mức API, Should ở mỗi màn | Backlog M8 §10 #5 |
| S-38 | Funnel A vs Cohort | NF:908-935 "cần hỗ trợ hai phương pháp", B "quan trọng" nhưng FUN-008 Should (NF:903) | M8 mới làm A | Cohort cần Lead | Metric |
| S-39 | Hiệu năng | NF:1349 < 3 s mọi màn; NF:1350 P95 500 ms | BRD:1035 p95 < 2 s, dashboard < 3 s | BRD + giữ NF:1350 làm mục tiêu CRUD | NFR test |
| S-40 | MFA, ngôn ngữ, responsive | NF:1357,1361,1362 **Should** | BRD:1029 MFA **bắt buộc**; BRD:1046-1047 bắt buộc | BRD | Thấp |
| S-41 | SLA | NF:1352 "nếu được chọn" | BRD:1040 ≥ 99,9% | BRD | Thấp |
| S-42 | Multi-tenant | NF:1508 DEC-001 "Có, nếu SaaS" | R-DEC-07; B1 mở | Chờ B1 | Kiến trúc |
| S-43 | Nhiều pipeline | NF:1509, NF:683-688 | R-DEC-89/90 stage cố định | R-DEC-176 | Schema |
| S-44 | Multi-currency, kiểu Decimal | NF:547,1513, kiểu Decimal (NF:108-111) | CLAUDE §5.2 BIGINT + `currency`; `deals` đã có | Giữ BIGINT | Cấm dùng Decimal lưu tiền |
| S-45 | Module thương mại | NF:1519-1540 License, Commission, ARR, Bookings vs Billings | BRD:31 ngoài phạm vi kế toán; D19, D21 P1 | Backlog riêng, cần DEC | Có thể đụng Finance |
| S-46 | IA | NF:1203-1250 menu Dashboard/Sales/Analytics/Management/Admin; "Executive Dashboard" | UX:69 8 mục theo việc; BRD:810 3 cấp | **Giữ IA UX**; CRM nằm trong "Kinh doanh" | 06. Sidebar không tách CRM |
| S-47 | Màu trạng thái | NF:1268-1276 (Qualified = Purple) | UX:230-237 token ngữ nghĩa, `ai` riêng | Dùng token; không thêm màu trùng `ai` (UNVERIFIED giá trị token `ai`) | UI |
| S-48 | Ngữ cảnh mẫu | NF:1303-1317 Cybersecurity, ABC Bank, PrivaGuard | Công ty ABC phân phối thiết bị văn phòng (CLAUDE §1.5) | Không dùng dữ liệu NF cho seed | 08 |
| S-49 | Thứ tự làm | NF:1506 không code trước khi chốt 10 quyết định | M8 đã làm Phase 1 trước (R-DEC-175) | Ghi nhận, các DEC-001..010 NF phải trả lời ở R-DEC-176 | Governance |
| S-50 | Thuật ngữ | NF Account vs BRD Customer (BRD:839) vs code `Client` | 3 tên cho 1 thực thể | Chốt thuật ngữ | Tài liệu, UI |

### 4.6. Trùng ID

| Tiền tố NF | Vị trí NF | Trùng với | Hậu quả | Đề xuất |
|---|---|---|---|---|
| `ACT-001..009` | NF:793-801 | `ACT-*` Action Registry (CLAUDE §5.5) | **Trùng ngữ nghĩa nguy hiểm** | `CRM-ACT-*` (M8 dùng `CRM-`), mã runtime `SA-` (M8 §5.2-e) |
| `DEC-001..010` | NF:1508-1517 | `DEC-001..` repo | Rất dễ nhầm; DEC-001 repo = stack | `CRM-Q-01..10` |
| `NFR-001..018` | NF:1349-1366 | NFR-xx legacy (NFR-07, NFR-16, NFR-19 trong CLAUDE) và NFR-SEC-… | Nhầm | `CRM-NFR-*` |
| `PERF-001..010`, `US-PERF-001/002` | NF:1112,1138,1148 | `FR-PERF-*`, **`US-PERF-001/002` trùng hẳn mã** BRD:984-985 | Cùng mã, khác nghĩa | `CRM-PERF-*`, `US-CRM-…` |
| `BR-001..019` | NF:1373-1420 | `BR-FIN-*`, `BR-SAL-*` (05:552) | Khác tiền tố con, nhầm nhẹ | `BR-CRM-*` |
| `US-ACT-*` | NF:832,843 | Không trùng US, nhưng trùng từ `ACT` | Thấp | `US-CRM-ACT-*` |
| `UAT-*`, `UX-*`, `DASH-*` | NF:1282,1425,92 | Chưa đăng ký | — | Đăng ký SKELETON |

---

## 5. Quyết định

### 5.1. R-DEC có trạng thái không phải resolved

Nguồn: script parse cột cuối 178 dòng. 167 resolved, 6 (R-DEC-05..10) dùng cột "Blocking = resolved", còn 5 dòng dưới.

| R-DEC | Dòng | Trạng thái thực | Chủ đề | Hành động cần |
|---|---|---|---|---|
| R-DEC-168 | 13:244 | **open, blocking** (CLAUDE §6.4) | Xoay cặp khóa JWT RS256 sau khi lộ một phần trong output phiên agent | Human xoay khóa, T-1209 |
| R-DEC-164 | 13:240 | **open, blocking cho DOC-03** | Trần 2048 token với tài liệu nhiều dòng; 4 phương án (a-d) | Chọn phương án. Đụng giới hạn AI đã khóa (CLAUDE §6.3.10) |
| R-DEC-176 | 13:252 | **open** chờ duyệt | Thực thể CRM mới; 10 câu ở M8-CRM-PLAN §5.2 | Xem D-02 |
| R-DEC-169 | 13:245 | open, non-blocking | Backlog: EMP picker, danh bạ DIR ngoài khối O, Risk P1-frozen | Quyết với R-DEC-176 (S-25) |
| R-DEC-80 | 13:126 | **đề xuất chờ human duyệt**, code đã chạy | EP-DC-14b `/files/{storage_key}` | Hợp thức hóa; đây là endpoint bảo mật đã ship khi DEC chưa duyệt |

Trạng thái "resolved" nhưng còn đuôi:

| R-DEC | Dòng | Còn lại |
|---|---|---|
| R-DEC-81 | 13:127 | Follow-up (a)-(d) "chờ human duyệt", xóa `secrets/`. Chưa làm |
| R-DEC-159 | 13:235 | OQ-13-M5-01 RACI MGR |
| R-DEC-166 | 13:242 | STT thật là backlog; trái 04 C2 |
| R-DEC-171 | 13:247 | Mục (4) ngân sách CFO, (5) form còn backlog |
| R-DEC-117..125 | 13:189,200 | OAuth live, `/security-review` live hoãn tới khi có secret |
| R-DEC-145 | 13:221 | Phần stack-real đã làm sau, nội dung dòng chưa cập nhật |
| R-DEC-147..152 | M4-SYNC V-2 | "human chưa xác nhận" |
| R-DEC-153 | 13:229 | Chưa có số đo latency live |
| R-DEC-157 | 13:233 | Quyết định `MODEL_PROVIDER_FALLBACKS`, OmniRoute là provider duy nhất |

13 §3 còn mở toàn bộ: **B1** SaaS đa tenant, **B2** khách hàng đầu, **B3** chính sách AI cloud, **B4** vai trò với kế toán, **B5** ngưỡng L3, **B6** kênh chat, **B7** giá.

### 5.2. Quyết định có trong deliverables/STATE nhưng thiếu trong 13

So khớp mã R-DEC: STATE, deliverables, code không có mã nào ngoài 13. Thiếu là **quyết định chưa có mã**:

| Nội dung | Nguồn | Trạng thái |
|---|---|---|
| SSO + MFA (FR-ADM-04, NFR-SEC-01) | Phát hiện ở audit này; R-DEC-36 (13:74) chỉ gọi là backlog | Chưa có quyết định riêng, code chưa có |
| Rate limit AI 20 req/phút: phạm vi, khóa, cửa sổ | M4-SYNC X-1, P2 "cần R-DEC" | Chưa có mã, code chưa có |
| Timeout 5 s/tool | M4-SYNC X-2, P3 | Chưa có mã, code chưa có |
| Bảng gương `ENT-*` ↔ model | M4-SYNC U-1, P7 | Chưa quyết |
| MinIO không dùng: ghi nhận hay hiện thực S3 | M4-SYNC U-2, P8 | Chưa quyết |
| Sửa CLAUDE G-1..G-4 | M4-SYNC P10 | Chưa làm |
| Xử lý gitleaks: allowlist, branch protection, không rewrite history | GITLEAKS-AUDIT §10 (4 câu) | Chưa quyết; `.gitleaks.toml` chưa có. M8-CRM-PLAN §10 #3b **ghi "OPEN — chưa có quyết định xử lý lịch sử"** trong khi audit kết luận không cần rewrite |
| `needs: secrets` làm job `api` bị skip | GITLEAKS-AUDIT §2 | Chưa quyết |
| Trạng thái demo vs live | STATE:118-139 vs M8-CRM-PLAN §8.1 | Chưa rõ |
| Chọn DN pilot; OAuth live; data thật | STATE:130-133, T-906 §9, OQ-09-04 | Chờ human |
| DEC-177, `DEC-241` và các DEC-2xx | GITLEAKS, STATE:525, R-DEC-23 | Định nghĩa nằm ở archive |
| Trạng thái BRD_Newfeature trong thứ bậc nguồn | §4.1 S-01 | Chưa có mã |
| Backlog M8: tên người phụ trách, DASH-010 | M8-CRM-PLAN §10 #4-5 | Chưa có mã |
| Rủi ro rollback duyệt tuyển dụng | M8-CRM-PLAN §9 | Vận hành |

### 5.3. Quyết định đã resolved mà code trái

| R-DEC | Nội dung | Bằng chứng trái | Mức |
|---|---|---|---|
| **R-DEC-81** | `keys/` là chuẩn | `core/config.py:44-45` default `secrets/`; `docker-compose.yml:25` mount `./secrets`; `scripts/generate_keys.sh:3,5` default `secrets`. Compose thường không dùng cùng đường dẫn với compose full | Cao: follow-up đã biết, chưa làm |
| **R-DEC-90** | stage `open/closed_won/closed_lost` | Code 6 stage (`sales/models/__init__.py:39`), 05:552 cũng 6 stage. Dòng R-DEC sai | Trung bình: sửa văn bản |
| **R-DEC-173** ↔ README | HR-DIR/CEO duyệt | README:56 còn ghi CFO | Doc sai, code đúng |
| **R-DEC-23** | Seed v3, DEC-231 superseded | Nhiều số alert khác nhau | Thấp, **UNVERIFIED** |
| **R-DEC-141** ↔ CLAUDE:119 | Không LlamaIndex | CLAUDE sai, code đúng | Doc sai |
| **07 §145 + CLAUDE §5.5** (giới hạn đã chốt, không phải R-DEC) | 20 req/phút; 5 s/tool | Không có code | **Cao** |
| **02:74,142** (FR-ADM-04, spec, không phải R-DEC) | SSO, MFA bắt buộc | Không có code | **Cao** nếu pilot |
| **R-DEC-16** | product/risk đóng băng, tool gắn `p1_frozen` | README:71 còn quảng bá 5 trụ | Doc |
| **R-DEC-175** | Không event/endpoint mới | Tuân thủ. Nhưng S-26 trái NF | Cần human |

Không phát hiện trái ở: 7 role (`ROLE_REFS`), Autonomy trần L3 (M4 S6), kill switch (autonomy.py), 328 route có EP (TC-M4-02), 54 tool, 34 metric.

### 5.4. OQ quan trọng cho v4

| Mã | Nội dung | Vì sao chặn |
|---|---|---|
| OQ-01 / B1-B7 | 7 quyết định CEO | B1 đổi kiến trúc tenant; B3 đổi routing model; B5 đổi autonomy |
| OQ-02-02 (02:184) | Ngưỡng giá trị L3 | Chưa có số mặc định sau khi đã bật L3 thật |
| OQ-02-03, OQ-07-03 | Mật local-only hay cloud VN | Bằng B3 |
| OQ-02-04 | ENT-AIAgent/AIAudit | BRD:180 Agent có identity đủ 9 thuộc tính |
| OQ-03-04 | 4 ô chỉ số theo khối | UI |
| OQ-05-01 | `source` vs `*_source` | Ảnh hưởng mọi bảng CRM mới |
| OQ-05-03 | Effective-dated | Forecast snapshot, target history |
| OQ-06-01 | Màu thương hiệu | Rebrand v4? |
| OQ-06-04, 06-05 | PWA vs native; xưng hô | |
| OQ-07-02 | Memory store | Agent Runtime |
| OQ-09-04 | Pilot | Cổng G1-G4 thật |
| OQ-10-03 | MCP server | FR-INT-04 |
| OQ-10-10, 10-11 | Permission tool, tool ghi nhân sự | Ghi "đề xuất, chọn nếu human duyệt" |
| OQ-13-M5-01 | RACI MGR | RBAC |
| OQ-14-03 | AI-eval golden set | FR-AIQ-02 |
| OQ-08-03, 08-04 | Số seed | Thấp |

Nhiều OQ-M1.x còn nhãn "phương án đề xuất, chọn nếu human duyệt" dù đã thực thi (05:654-657, 06:393-395, 09:606-607, 10:1008-1012, 14:567-568). Nên đóng hàng loạt.

**Quyết định mới cần tạo trước khi viết doc v4 (đề xuất, số do human cấp):**

| Mã tạm | Câu hỏi | Mặc định đề xuất |
|---|---|---|
| D-01 | v4 là gì: bump sau CRM, hay cột mốc pilot, hay đổi lớn? Có phải sản phẩm mới không? | Coi v4 = "post-MVP: CRM đầy đủ + nợ NFR + sẵn sàng pilot", giữ kiến trúc |
| D-02 | Duyệt R-DEC-176 với 10 câu §5.2 + S-25, S-26, S-28, S-30 | Như M8 §5.2 + thêm tool/event |
| D-03 | Thứ bậc nguồn, trạng thái NF | §4.1 |
| D-04 | Version `_reference`: un-ignore hay manifest hash? | Un-ignore nếu không vướng pháp lý; repo **public** (GITLEAKS:3) nên phải xem nội dung trước. Mặc định: manifest SHA-256 + lưu ở kho riêng |
| D-05 | Hệ DEC: bỏ `R-` prefix, hay giữ `R-DEC` là chuẩn duy nhất; xử lý DEC-* cũ | Giữ `R-DEC` chuẩn; thêm "phụ lục DEC v2.1 còn hiệu lực" gồm chỉ những DEC còn được trích |
| D-06 | Giữ hay bỏ archive v2.1 | Xem §6 |
| D-07 | Đánh số doc 00-14 | §7 |

---

## 6. Danh sách đề xuất xóa/archive (chỉ đề xuất)

Giả định thư mục lịch sử: `docs/_history/` (được git track). User-provided = do người dùng đưa vào, không phải agent sinh.

| Ứng viên | Loại | Được tham chiếu bởi | Chứa quyết định chưa di trú? | User-provided? | Đề xuất |
|---|---|---|---|---|---|
| `docs/_reference/SOURCE-BRD-v1.1.md` | source | 23 file | — | Có | **KEEP**, xử lý version |
| `docs/_reference/SOURCE-BRD-v1.1-Bổ sung.md` | source | 23 file | Rationale | Có | **KEEP** |
| `docs/_reference/SOURCE-UIUX.md` | source | 06, CLAUDE | — | Có | **KEEP** |
| `docs/_reference/BRD_Newfeature.md` | source | M8-PLAN, 13:252, crm.ts | 10 câu DEC riêng | Có | **KEEP**, khai trạng thái |
| `docs/_archive/v2.1/` (17 file, đã xóa, chưa commit) | history | 25 file | **Có: định nghĩa DEC-*, chưa di trú** | Không (agent sinh) nhưng user chủ động xóa | **Đừng commit việc xóa khi chưa có phụ lục DEC.** Có 2 đường: giữ trong git (`git restore`) tại `_history`, hoặc commit xóa sau D-05. Tôn trọng quyết định xóa của user; chỉ yêu cầu di trú trước |
| `docs/handover/*` (4 file, đã xóa, chưa commit) | active (runbook) | 3 file code/script, 13:228, 09:542 | Không có DEC; có tri thức vận hành | Không | **Khôi phục nội dung vào runbook rồi xóa** |
| `docs/4.GOVERNANCE/REBUILD-PLAN.md` | history | CLAUDE §9, 00:16, 12:20, REVIEW-REPORT, SKELETON:202 | Không (Q1-Q6 đã ở 13) | Không | **ARCHIVE** |
| `docs/4.GOVERNANCE/REVIEW-REPORT.md` | history | CLAUDE §9; 12 không có | A1, A2 chưa xác nhận | Không | **ARCHIVE** sau khi chép A1, A2 thành OQ |
| `deliverables/M8-CRM-PLAN.md` | active + history | 13:251-252, 14 | **Có:** §5, §5.2 chỉ có ở đây | Không | **KEEP** tới khi R-DEC-176 đóng, rồi ARCHIVE. §8-9 chuyển runbook |
| `deliverables/M4-SYNC-AUDIT.md` | test report | 13:229, 09, `apps/api/Dockerfile`, STATE | **Có:** X-1, X-2, U-1, U-2, G-* | Không | **ARCHIVE** sau khi chuyển thành R-DEC/OQ |
| `deliverables/M4-CONFORMANCE-PLAN.md` | history | 09:515, 03, STATE | Không rõ | Không | **ARCHIVE** |
| `deliverables/M5-PRODUCT-GAPS-REPORT.md` | test report | STATE | Không (R-DEC-154..159) | Không | **ARCHIVE** |
| `deliverables/T-906-DEC-PROPOSALS.md` | history | STATE, 14, T-906-PILOT-CHECKLIST | Không: A→R-DEC-146, B→150, C→151 đã xử lý | Không | **DELETE** hoặc ARCHIVE; đề xuất archive vì rẻ |
| `deliverables/T-906-PILOT-CHECKLIST.md` | active | 14:383, README, STATE | Có việc pilot | Không | **KEEP**, chuyển runbook/pilot |
| `deliverables/GITLEAKS-AUDIT.md` | active, **untracked** | M8-PLAN:§10 | **Có:** 4 câu §10 | Không rõ (untracked) | **KEEP**, cần human commit hoặc chuyển |
| `.prompt/prompt_update_feature.md` | temp, untracked | không | Không | **Có** | User quyết; không commit (đường dẫn sai) |
| `STATE.md` dòng 492-761 (v2.1 + S0-S5) | history | Chưa thấy trích theo dòng | Không | Không | **ARCHIVE** phần này; dòng 744-761 "đề xuất doc-sync" đọc rồi xử lý |
| `docs/DEMO-SCRIPT.md` | active | README:33 | Không | Không | **KEEP**, update |
| `BRD_Newfeature.md:Zone.Identifier` (gốc repo) | temp, gitignored | không | Không | Có (Windows ADS) | **DELETE** |
| `.coverage`, `var/m4/*`, `var/backup/*` | temp | M8-PLAN | Không | Không | Không commit (đã ignore); backup giữ theo chính sách |
| `secrets/` (thư mục rỗng, root) | temp | compose | R-DEC-81 | Không | Xóa sau follow-up, cần human (13:127) |
| `AGENT.md`, `.github/copilot-instructions.md` | duplicate | — | Không | Không | **KEEP** dạng alias 3 dòng, chỉ trỏ CLAUDE |

---

## 7. Cấu trúc doc đề xuất cho v4

### 7.1. Nguyên tắc

1. **Một sự thật, một nơi.** Trạng thái chỉ ở `STATUS.md`; số đếm không chép vào CLAUDE, chỉ trỏ script.
2. **Sinh tự động cái sinh được.** 12, các bảng count, bảng gương TOOL/METRIC/EP/ENT.
3. **Giữ số 00-14.** Code và test đang trích kiểu "10 §7.2", "05 §2.8", "14 §1.3". Đổi số gây chi phí không đáng. Thêm số mới, không dồn số. Số file dùng cũ: 442 file code/script có `R-DEC`/`DEC-`.
4. **Spec theo domain, không theo phase.** Lịch sử phase nằm ở changelog.
5. **Từ vựng:** bỏ `main` nghĩa v2.1; dùng "nền v2.1". Bỏ "đợt docs/đợt code".

### 7.2. Bộ tối thiểu

```text
CLAUDE.md                      hợp đồng agent, ngắn (<250 dòng); gộp 11 vào đây hoặc ngược lại
AGENT.md, copilot-instructions alias 3 dòng
README.md                      giới thiệu + quick start; không chứa số test
STATUS.md                      (thay STATE) 1 trang: mốc, stack, số test mới nhất, blocker, link
docs/
  00-INDEX.md                  bản đồ + thứ bậc nguồn + từ vựng
  _reference/                  canonical; có MANIFEST.md (hash, trạng thái từng file)
  1.CONTEXT/  01-OVERVIEW      tầm nhìn + scope v4 + trạng thái sản phẩm thật
  2.PRODUCT/  02 Permissions · 03 Dashboard/Reporting · 04 IDP · 05 Data model · 06 UX
              15-CRM-SPEC      MỚI: D17/D18; nhận BRD_Newfeature đã duyệt
  3.EXECUTION/07 Architecture · 08 Demo data+script · 09 Roadmap v4 · 10 API
              16-OPERATIONS    MỚI: runbook (deploy, rollback, cleanup, troubleshooting, pilot)
  4.GOVERNANCE/ 12 (sinh) · 13 Decisions · 14 Tests · REGISTRY (đổi tên SKELETON)
  _history/                    REBUILD, REVIEW, deliverables đóng, phần lịch sử của 09/STATE,
                               phụ lục DEC v2.1
```

### 7.3. Việc từng file

| File | Hành động | Ghi chú |
|---|---|---|
| 00 | Viết lại, ≤ 60 dòng | Thêm từ vựng, thứ bậc nguồn. Bỏ cột R0-R3 |
| 01 | Viết lại | Trạng thái sản phẩm thật, scope v4 sau D-01 |
| 02 | Cập nhật | 6 role người + ROLE-AI; scope `own/assigned` nếu duyệt; kill switch 2 mode; bỏ `main` |
| 03 | Cập nhật | Metric CRM: funnel, forecast; alert |
| 04 | Cập nhật | Thêm §as-built field schema từ handover, sửa số doc type, STT, trạng thái `AUTO_APPROVED/DUPLICATE` |
| 05 | Tái cấu trúc | Sắp theo domain; bảng gương ENT sinh từ model + contract test (P7) |
| 06 | Cập nhật | Bảng route↔SCR sinh từ `page.tsx`; thêm SCR M6-M8 |
| 07 | Cập nhật | `modules/ai`, 14 AIC, storage thực, NFR thật + gap |
| 08 | Gộp DEMO-SCRIPT | Hoặc giữ 2 file nhưng DEMO-SCRIPT cập nhật tới M8 |
| 09 | Tách | §1-5 thành roadmap v4; §6 sang `_history/09-tasks-M1-M8.md`; task mới giữ ở 09 |
| 10 | Giữ | Sửa 13→14 metadata; đổi header "mức khái niệm" |
| 11 | Gộp | Giữ một trong hai; khuyến nghị giữ 11 đầy đủ, CLAUDE chỉ quy tắc cứng + link |
| 12 | Sinh tự động | Script đọc version, git log, Gate A, tham chiếu treo; chạy trong CI |
| 13 | Dọn | Tách `open` lên đầu; thêm cột Người quyết; đóng R-DEC-80; sửa R-DEC-90; phụ lục DEC |
| 14 | Giữ | Đóng TC-Planned; cập nhật số; bỏ R-DEC-09 |
| SKELETON | Đổi tên REGISTRY | Thêm namespace `CRM-*`, sửa đếm |
| CLAUDE | Human viết lại | Bỏ §1.6 trạng thái, §2.2 version chi tiết → trỏ pyproject/package.json; đổi §4.2 theo cây thật |

### 7.4. Thứ tự thực hiện đề xuất

1. Human: D-01, D-03, D-04, D-05; xử lý R-DEC-168.
2. Trước khi commit xóa: di trú DEC, khôi phục handover vào 16.
3. Sửa đường dẫn hàng loạt (`_reference`, `_archive`, `secrets`), đồng thời follow-up R-DEC-81.
4. Dựng script sinh 12 + kiểm tham chiếu treo trong CI; xử lý gitleaks để job `api` chạy lại.
5. Chốt R-DEC-176 + 15-CRM-SPEC, rồi 05/10/02/06/14 mới migration.
6. Viết lại 00, 01, 09 roadmap, CLAUDE.

**Rủi ro nếu bỏ qua bước 2:** commit xóa archive làm mọi `DEC-xxx` không còn nơi tra trong working tree, mặc dù vẫn phục hồi được từ history.
