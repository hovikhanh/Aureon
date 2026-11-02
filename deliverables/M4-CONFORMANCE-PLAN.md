# M4 — Doc ↔ Code Conformance & Hardening · Kế hoạch nhiệm vụ

> Nguồn: audit máy 2026-11-02 trên nhánh `v3/m4-doc-code-conformance` (sau M3.5 / tag `v3.0.0-mvp`).
> Human giao: phân tích toàn bộ `docs/` 00–14 vs codebase, kiểm API vs spec, hoàn thiện module,
> siết chất lượng, doc-sync. Ủy quyền: code + docs + dependency (tự chốt Spec lock, đề xuất R-DEC).

## 1. Kết quả audit (bằng chứng máy)

| ID | Phát hiện | Bằng chứng | Mức |
|---|---|---|---|
| GAP-01 | **0/216 EP row** trong `10` thiếu route | script `ep_audit2.py` §A | ✅ không lệch |
| GAP-02 | **71 route thật không có EP row** trong `10` (product 18, risk 13, execution/meeting-decision 8, hr 8, dashboard 5, goals/milestones 5, platform/dead-letter 2, idp/search 1, work/reassign 1, finance/sales phụ 10) | `ep_audit2.py` §C | 🔴 |
| GAP-03 | **Tool Registry v3 không có trong docs**: code 54 `TOOL-*`; `10` chỉ nhắc 29 id rải rác, không có bảng 13 metadata. CLAUDE §5.5 trỏ vào "bảng 10 §7" không tồn tại (bảng thật ở `_archive/v2.1`) | `registry.py::all_tools()` = 54 vs `grep TOOL- docs/3.EXECUTION/10` = 29 | 🔴 |
| GAP-04 | **Action Registry lệch**: code 20 `ACT-*` (IDP) vs docs 22 id | `actions/registry.py::action_names()` | 🟠 |
| GAP-05 | **Metric catalog lệch**: code 34 `METRIC-*` vs docs nhắc 17 id | `platform/services/catalog.py::CATALOG` | 🟠 |
| GAP-06 | **5 permission lệch spec↔code**: `EP-RPT-02/03` spec `dashboard:read` vs code `execution:read` (**code đúng** — MGR/EMP không có `dashboard:read`, theo spec sẽ 403); `EP-FIN-05`, `EP-FIN-10` ô permission thiếu `finance:read` cho nhánh GET | `ep_audit2.py` §B + `permission_matrix.ROLE_PERMISSIONS` | 🟠 |
| GAP-07 | **Không có kiểm chứng máy toàn catalog** — contract test chỉ theo phase, hard-code | `tests/contract/*` | 🔴 |
| GAP-08 | **`.env` không source được bằng shell** (`ADMIN_BOOTSTRAP_PASSWORD` chứa `"` không quote) — đứt quy trình `set -a; . ./.env` STATE.md yêu cầu | `bash: ./.env: line 93: unexpected EOF` | 🟠 |
| GAP-09 | **Job retention chưa có**: `05` §294 + OQ-05-11 chốt `idp.purge_import_rows` (xóa `import_rows` sau undo 7 ngày); `workers/` không có module retention (CLAUDE §4.2 liệt kê `workers/retention`) | `ls apps/api/src/app/workers/` | 🟠 |
| GAP-10 | **Cleanup tài liệu IDP chỉ là runbook SQL tay** (`docs/handover/IDP_Operations.md` §5) — không có cơ chế trong app (orphan storage sweep, FK-safe purge, dry-run, audit) | handover §5 | 🟠 |
| GAP-11 | **Chất lượng chưa đo được**: FE coverage chưa đo (thiếu `@vitest/coverage-v8`), a11y chỉ structural (thiếu `@axe-core/playwright`) — `14` §1.3 yêu cầu FE `features/`+`lib/` ≥ 70% | STATE.md "nợ M2/M3" | 🟠 |
| GAP-12 | **Test tiền tồn đỏ/flake**: `test_chat_demo_mode` (leak config cache), `inj02`/`inj03` (fixture classify), `goal_events_t629` (date-sensitive), `seed_s2` (đếm alert) | STATE.md gate M2/M3 | 🟠 |
| GAP-13 | **Doc drift trạng thái**: `09` còn 84 ô `☐` cho task đã làm; `12`/`13`/`14`/`DEMO-SCRIPT` chưa phản ánh M2/M3 + live cutover | `grep ☐ docs/3.EXECUTION/09` | 🟠 |
| GAP-14 | **6 event đang phát trong code không có trong doc nào** (`finance.cash_flow_forecast_updated`, `hr.salary_updated`, `idp.review_escalated`, `platform.alert_raised`, `product.product_launched`, `risk.risk_proposed`) + 1 đã khai nhưng chưa có publisher (`platform.report_generated`) — CLAUDE §5.4 chỉ cho dùng event có trong registry tài liệu | `core/events/registry.py` (40) vs grep docs | 🟠 |

## 2. Nhiệm vụ

### Nhóm 1 — API & registry conformance (máy kiểm được)

| ID | Việc | Chạm | Gate |
|---|---|---|---|
| T-1001 | Sửa 5 permission lệch trong `10` (GAP-06): RPT-02/03 → `execution:read` + ghi rationale; FIN-05/10 thêm `finance:read` | `docs/3.EXECUTION/10` | contract |
| T-1002 | Thêm `10` §7.3 "EP catalog nền v2.1" gán EP id v3 cho 71 route (GAP-02), cột permission = permission thật trong code, đánh dấu P1-frozen (product/risk) | `docs/3.EXECUTION/10` | contract |
| T-1003 | Thêm `10` §7.4 Tool Registry đầy đủ 54 `TOOL-*` + 13 metadata (GAP-03), sinh từ `registry.py` | `docs/3.EXECUTION/10` | contract |
| T-1004 | Thêm bảng Action Registry 20 `ACT-*` + Metric catalog 34 `METRIC-*` (GAP-04/05) | `docs/3.EXECUTION/10`, `docs/2.PRODUCT/03` | contract |
| T-1005 | **Contract test tổng** `test_catalog_conformance.py`: EP↔route↔permission (cả 3 chiều), TOOL doc↔code, ACT doc↔code, METRIC doc↔code → mọi drift tương lai fail test | `apps/api/tests/contract/` | pytest -m contract |

### Nhóm 2 — Hoàn thiện module theo tài liệu

| ID | Việc | Chạm | Gate |
|---|---|---|---|
| T-1010 | Job retention `idp.purge_import_rows` (GAP-09) theo `05` §294 + OQ-05-11: idempotent, chỉ batch `completed` + hết undo 7 ngày, giữ `extracted_fields`, audit + beat schedule | `workers/`, `idp/services`, `worker.py` | pytest |
| T-1011 | Cleanup tài liệu IDP trong app (GAP-10): sweep orphan storage + purge FK-safe có dry-run + audit, thay runbook SQL tay | `idp/services`, `workers/` | pytest |

### Nhóm 3 — Siết chất lượng

| ID | Việc | Chạm | Gate |
|---|---|---|---|
| T-1020 | `.env` source-safe (GAP-08): quote giá trị + test guard | `.env.example`, `scripts/` | test |
| T-1021 | FE coverage đo được: `@vitest/coverage-v8` (dependency — R-DEC mới), ngưỡng `14` §1.3 | `apps/web`, `package.json` | pnpm test |
| T-1022 | a11y thật: `@axe-core/playwright` (dependency — R-DEC mới) trên SCR chính | `apps/web/e2e` | playwright |
| T-1023 | Dọn test đỏ/flake tiền tồn (GAP-12) | `apps/api/tests` | pytest |

### Nhóm 4 — Doc-sync & đóng mốc

| ID | Việc | Chạm | Gate |
|---|---|---|---|
| T-1030 | `09` ☐→☑ cho task đã làm; `12` doc-audit; `13` thêm R-DEC mới; `14` TC mới; `DEMO-SCRIPT`; `STATE.md` | `docs/`, `STATE.md` | doc-reviewer |
| T-1031 | Gate DoD đầy đủ + `pytest --cov` + Playwright mock/real + commit theo Conventional Commits | — | §3.3 |

## 3. R-DEC đề xuất (agent tự chốt theo ủy quyền, human xác nhận sau)

| ID | Nội dung |
|---|---|
| R-DEC-147 | `EP-RPT-02/03` permission chuẩn = `execution:read` (không phải `dashboard:read`) — MGR/EMP không giữ `dashboard:read` (02 §5.2); đổi theo spec sẽ phá dashboard Department/Employee. Spec `10` sửa theo code. |
| R-DEC-148 | `10` §7.3 — gán EP id v3 cho 71 route nền v2.1 (giữ nguyên path/permission/hành vi; **không** đổi contract), để catalog EP đầy đủ và kiểm được bằng máy. |
| R-DEC-149 | `10` §7.4 — Tool Registry 54 `TOOL-*` + 13 metadata sinh từ code (`registry.py` là nguồn, doc là bảng gương, contract test giữ đồng bộ 2 chiều). |
| R-DEC-150 | Dependency dev-only `@vitest/coverage-v8` (đo coverage FE theo `14` §1.3) — không vào bundle runtime. |
| R-DEC-151 | Dependency dev-only `@axe-core/playwright` (a11y WCAG AA tự động) — chỉ dùng trong `e2e/`. |
| R-DEC-152 | Job `idp.purge_import_rows` + `idp.sweep_orphan_storage` (retention/cleanup trong app) — đóng OQ-05-11, thay runbook SQL tay. |

## Version

- Draft 0.1 — 2026-11-02. Agent: audit + plan. Trạng thái thực thi cập nhật ở `STATE.md`.
