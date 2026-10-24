# Aureon v3 — AI-EOS · Build State

## Status: M1.1 DONE (nền build v3) — chờ human review/PR

| Field | Value |
|---|---|
| Last updated | 2026-10-23 (Asia/Saigon) |
| Dòng sản phẩm | **Aureon v3 — AI-EOS** (chính thức duy nhất). v2.1 archived (`docs/_archive/v2.1/`) |
| Branch | `v3/m1.1-foundation` (local, **chưa push**) ← `ai-eos`; `main` giữ nền v2.1 demo |
| Phase | **M1.1 DONE** (T-601→T-609 ☑, T-610 chờ PR) · P1 DONE — refactor 10 role F.O.C.U.S → 7 role BRD + AI Agent; +`tenant_id`; +`scope_pillars`; review Autonomy L0–L3 (L4 khóa) + kill switch |
| Gates | A ✅ · B ✅ (0 DEC open+blocking) · C ✅ (14 §1.5 TC-M11-01..15 Passed) |

## M1.5 — D03 Data Capture (chuỗi auto) — DONE `[full-test pending]` (2026-10-25, nhánh `v3/m1.5-capture`)
| Task | Commit | Nội dung |
|---|---|---|
| T-634S | `38c9067` | Spec lock M1.3–M1.6 (R-DEC-60..69 cho M1.5) |
| (contract) | `83f7f08` | Contract EP-DC-01..37 + stub 501 |
| T-636 | `406dbc1`, `5844a06` | Action Registry v2 (12 ACT) + `document_actions` + EP-DC-23; `DocumentOut`/`DocumentTypeOut.version` (R-DEC-60bis) |
| T-634 | `15d95b5`, `944eaed` | Doc type #2/#3/#4 + schema registry DB + admin EP-DC-27..35 + classifier 4 tầng; ADM `idp:read/write` scope `s` (R-DEC-76 kéo sớm) |
| T-635 | `bd63bda` | C1 form/submit, C5 import EP-DC-17..22, Data Inbox EP-DC-13, source view EP-DC-14, EP-DC-01 chọn trước |
| T-637 | `53986f4` | Lineage mọi commit + EP-DC-26 |
| T-640 | `bebe01f` | Trường trọng yếu (R-DEC-69) + incident EP-DC-36/37 |
| T-638 | `416c067` | Undo 7 ngày EP-DC-24/25 + `idp.document_rolled_back` + incident G4 khi undo |
| T-639 | `afb4b74`, `1e05149` | `METRIC-DQ-02` (G3) + `dq_domain_scores` (migration `0020_capture_dq`) + `platform.on_capture_share` |
| T-641 | `99e1496` | File mẫu DOC-06 (dòng lỗi cố ý) / DOC-07 xlsx+docx / DOC-08 pdf, deterministic |
| T-642 | `75a6e03` | Anti-injection: `suspicious_content`, scrub prompt classify, ai_eval INJ-01..03 |
| T-634F..T-638F | `f8dfcf1`, `55b9819`, `71bf35a`, `a180717`, `5f8ea4a`, `3330ba0`, `fd42425` | FE mock BFF EP-DC-01..37 + SCR-45/61/62/18a-b/63 |
| T-643 | `0817d97`, `deda0fc`, `6062cad`, `2673512` | Nối FE↔BE, E2E `capture.spec.ts` mock + real (`support/capture_e2e.py`) |
| review | `11e442b`, `80bb6ff` | 2 vòng review (dưới) |

**Kiểm tra (2026-10-25):** ruff/format/mypy sạch · pytest **1084** passed (0 fail, `MODEL_GATEWAY_MODE=fixture`) · Vitest **283** ·
Playwright mock **51/51** · real **74/74** (stack riêng `aureon_m15`, API :4300, web :3400; sau review `80bb6ff` chạy lại
`capture.spec.ts` mock 4/4 tại :3150) · `alembic downgrade -1` ×3 (0020→0017) + `upgrade head` sạch. TC-M15-01..18 = Implemented.
**Quyết định chính:** R-DEC-60bis — mọi chuyển trạng thái `source_documents` tăng `version` (khóa lạc quan EP-DC-08/22/23);
R-DEC-76 kéo sớm từ M1.6 (ADM `idp:read/write` scope `s` = chỉ #4 HR_ROSTER); migration M1.5 = `0018`–`0020`
(`0020_capture_dq`) → **M1.6 dùng `0021`**; `ACT-create_task` gắn vào #2 PLAN_KPI_OKR (cột `task_title`/`assignee_code`/
`task_due_date`, theo 10 §7.2.4 "#1, #2"); EP-DC-14 trả presigned URL ký HMAC (`core/storage.presign_get`, TTL 5 phút)
**không có route phục vụ file** (thêm route = endpoint mới → cần DEC).
**review M1.5 (2 vòng):** vòng 1 `11e442b` — review detail `rows`/`planned_actions`/`can_commit`, REV role pool scope, mask mức 4
trong review, bump version, ACT-create_task #2, seed doc types trong `app.seed`. Vòng 2 `80bb6ff` (5 finding, sửa cả 5):
#1 MAJOR GET-by-id EP-DC-14/18–21/24/25 dùng `document_visible` v2.1 (cùng phòng ban) → EMP đọc import rows (mức 3) / action log
tài liệu đồng nghiệp, ADM (`idp:admin` ⇒ toàn DN) đọc action log doc type ngoài #4 → `scope.capture_visible` (inbox scope + của
mình + phiên review), test `test_capture_scope_review_m15.py`; #2 MAJOR EP-DC-37 không lọc scope → inbox scope ∪ người báo;
#3 EP-DC-23 committer không có `idp:approve` dùng capture scope thay vì cùng phòng ban; #4 mock incidents lọc scope + EP-DC-36
tài liệu ngoài scope `404` (trước `422`); #5 ai_eval INJ-02/03 đỏ sẵn ở HEAD — prompt classify liệt kê mọi doc type active trong
DB (seed thêm INVOICE) → thêm fixture tương ứng. Đã soát: audit/outbox/lineage cùng transaction (SAVEPOINT executor), quyền đích
từng ACT, undo `seq DESC` + `409 conflicts[]`, mức 4 không vào params/snapshot/audit/event/prompt, upload stream 1 MB, `413`
rows/sheets/columns, migration reversible, master-ref cache (không N+1 theo dòng).
**Nợ / lưu ý:** EP-DC-14 cần DEC cho route phục vụ file presigned (hiện URL ký nhưng không route đọc); ADM xem incident (EP-DC-37
cần `idp:approve`) → OQ M3.x; SCR-63 `classifier_keywords` không trả trong `DocumentTypeOut`; reviewer@ thuộc phòng ADM → người ghi
hoá đơn trên demo là office@ — xem lại UX/seed; SCR-18b không highlight ô nguồn trên trang; rule form validation chỉ single-field;
fixture classify phụ thuộc tập doc type active (thêm doc type → ghi lại fixture INJ).
**Môi trường:** shell kế thừa env DB demo ghi đè `.env` → mọi lệnh `set -a; . ./.env; set +a` + kiểm `aureon_m15`; `.env` đặt
`MODEL_GATEWAY_MODE=live` → chạy pytest với `MODEL_GATEWAY_MODE=fixture`; sau TRUNCATE/reset chạy `uv run python -m app.seed`
để có lại doc types (#2/#3/#4).

## M1.4 — D07–D10 (chuỗi auto) — DONE `[full-test pending]` (2026-10-24, nhánh `v3/m1.4-goals`)
| Task | Commit | Nội dung |
|---|---|---|
| T-626S | `38c9067` | Spec lock M1.3–M1.6 (R-DEC-50..59 cho M1.4) |
| T-626C | `e5bc81d` | Contract `/goals/*` `/kpis/*` `/objectives/*` `/key-results/*` + stub 501, gỡ `/execution/{kpis,objectives,check-ins,initiatives}` |
| T-626 | `46b2c0b` | Strategy + StrategicObjective, migration `0016` + backfill, `goal_scope` khung |
| T-627 | `2e5bebb` | KPITarget effective-dated, KPIMeasurement lịch sử, KPIEvaluation, KRMeasurement (migration `0017`) |
| T-628 | `ad9886a` | EP-STR/KPI/OKR/PRF thay stub, `/goals/tree` một lượt query, check-ins due |
| T-629 | `8e8e5b6` | Event `kpi_measured/kpi_below_threshold/okr_checked_in/okr_at_risk`, consumer `execution.on_goal_alert`, job at-risk + nhắc check-in |
| T-630 | `80a0e96` | `METRIC-STR-01` (G2) + SEI drill-down |
| T-631 | `78513ee`, `369b887` | Seed Strategy/4 SO/INI/check-in (UC-03 KPI-SAL-01 CRITICAL, UC-04 đúng 1 KR at-risk) |
| T-632 | `4166c6e` | Scope R-DEC-57 (cây con phòng ban, DIR theo pillar, EMP của mình + tổ tiên restricted) |
| T-626F..T-628F | `9147b64`, `51937d2`, `1e0069d`, `ba75ab6`, `4991db8` | FE SCR-41/58/59/60 trên mock |
| T-633 | `0fd0294`, `0508cd1` (review) | Nối FE↔BE: mock goals seed **từ `seed_snapshot.json`** (Strategy STR-2026-2027, SO-01..04, INI theo SO, KPI cha, owner/check-in như seed BE), E2E real `goals.spec.ts` + `support/goals_e2e.py` |

**Kiểm tra (2026-10-24):** ruff/format/mypy sạch · pytest **946** (945 + 1 flaky `risk/test_replay_scope.py::test_idempotent_replays`
xanh khi chạy lại riêng) · Vitest **253** · Playwright mock **47/47** · real **72/72** (stack riêng: API :4200 + Celery worker/beat
(Redis db 9–11, `SMTP_HOST=localhost:1025`) trên DB `aureon_m14`, web `next start` :3300). TC-M14-01..18 = Implemented.
**Quyết định chính:** BE là nguồn sự thật — mock goals bỏ dữ liệu bịa (SO-C/F/U/O, KPI EMP, đổi target giữa kỳ, CONFIDENCE_FIX);
EMP chỉ sở hữu KR "Giao hàng TB ≤ 1,8 ngày" (không KPI) như seed thật; `details.reason` lỗi bổ sung ở BE (`period_locked`, `kr_count`)
thay vì đổi FE — không thêm mã lỗi.
**Nợ / lưu ý:** `next dev` (mock) và `next start` (real) dùng chung `apps/web/.next` → chạy mock xong phải build lại trước khi chạy real;
worker cần `SMTP_HOST` (Mailpit) cho test e-mail M1.2/M1.3; stack riêng phải đặt `E2E_API_URL` (mặc định :4000 — cleanup `admin-org` mở khóa nhầm API); `check_ins` append-only ở API nên cleanup E2E xóa ở DB rồi chạy lại `seed_goals`.

**review: 7 finding, đã sửa 6, nợ #7** (2026-10-24, commit `0508cd1`):
#1 MAJOR `/goals/tree` bỏ KR của EMP nằm dưới Objective ngoài scope → cây EMP rỗng (sửa `_Forest` anchor + KR thấy được dưới Objective restricted, test);
#2 MAJOR contract `details` thiếu `reason` (`period_locked` đo/target kỳ khóa, `kr_count` kích hoạt/thêm KR) mà FE `goalErrorKey` dựa vào (bổ sung BE + test);
#3 MAJOR mock: `previous_progress_pct` lấy từ cột KR thay vì KRMeasurement trước (BE) → null khi chưa có lần đo;
#4 mock consumer `on_goal_alert`: người nhận/tiêu đề lệch BE (KR → owner KR + owner Objective + MGR phòng; KPI → owner + MGR/DIR; tiêu đề `KPI <code> <band> kỳ <kỳ>` / `KR có rủi ro kỳ <kỳ>`);
#5 mock EP-KPI-09: EMP ngoài scope nhận `FORBIDDEN_ROLE` trước scope (BE: scope trước) ; #6 mock xóa Objective còn KR cascade (BE `409`), `details` xung đột xóa KPI/Objective/Initiative theo BE (`kpi_id`/`objective_id`/`initiative_id`).
**Nợ #7:** `AtRiskService.daily` / `checkin_reminder` gọi `refresh`/`user_id_for_ref` từng KR (N+1 trong job nền, ~10 KR ở seed) — gom truy vấn khi số KR lớn (M2.x).

## M1.3 — D11/D04 (chuỗi auto) — DONE `[full-test pending]` (2026-10-24, nhánh `v3/m1.3-work`)
| Task | Commit | Nội dung |
|---|---|---|
| T-619S | `38c9067` | Spec lock M1.3–M1.6 (R-DEC-38..79 resolved) |
| T-619C | `96a1dfc` | Contract `/work/*` `/workflow/*` + stub 501 + shared-types |
| T-619 | `f929ded` | Claim `employee_id` (R-DEC-41), migration `0014`, sub-task 1 cấp, dependency chặn vòng/done |
| T-620 | `5d01df2` | Workload `weekly_grid` (EP-TASK-18), project progress/late, milestone EP-TASK-14..17 |
| T-621 | `163d357` | Event `execution.task_created/task_completed` + `task_overdue.days_late` |
| T-622 | `57c0446` | Migration `0015`, rule từ DB, inbox EP-WF-01/02, EP-WF-03, `RULE-task_reassign` + EP-TASK-19 |
| T-623 | `84c93f3` | Notification in-tx (task_assigned/reminder/system, approval_requested/decided) |
| T-624 | `3009231` | Seed dependency/sub-task/source_ref/milestone, 1 `task_reassign` PENDING ở SVC |
| T-625F | `86aae84`, `9dfaf00` (merge `300c92c`) | FE SCR-42/43/55/56/57 trên mock |
| T-625 | `43d96c6` | Nối FE↔BE (title_key/params theo BE, `?id=`, claim `employee_id` trong mock) + E2E real `work.spec.ts` + `support/work_e2e.py` |

**Kiểm tra (2026-10-24):** ruff/format/mypy sạch · pytest **877** passed · Vitest **205** · Playwright mock **41/41** ·
real **69/69** (stack riêng: API host :4100 + Celery worker/beat (Redis db 6–8) trên DB `aureon_m1x`, web `next start` :3200,
Mailpit dùng chung :8025). TC-M13-01..14 = Implemented (Passed sau full test cuối chuỗi).
**Quyết định chính:** BE là nguồn sự thật cho `ApprovalRequestOut` — FE ghép tên từ `members[]` (người không đọc được → mã rút gọn);
EMP nhập ID nhân viên khi đề nghị chuyển (OQ-13-09 ghi vào 13, chốt M2.x); heatmap 3 quá tải kiểm bằng CEO (MGR SVC không có người quá tải).
**Nợ / lưu ý:** DB `aureon_m1x` phải truncate + seed lại sau T-624 (seed execution bỏ qua khi đã có task SEED → thiếu dependency/milestone/approval);
`next start` cũ sau rebuild trả 400 chunk tĩnh → khởi động lại sau mỗi build; mock project đôi khi timeout lần compile đầu (`next dev`), chạy lại xanh;
audit log append-only nên cleanup E2E chỉ soft-delete task/approval.

**review: 14 finding, đã sửa 12, nợ #9** (2026-10-24, commit `fix(work): M1.3 review …`):
`approval_service.can_decide` (một luật duy nhất cho inbox/detail/decide/notification — R-DEC-45: role ∈ step hiện tại,
CEO miễn scope không miễn role, DIR theo pillar rule, DIR `escalate_to_role_code` khi phòng không có MGR / `department_id` NULL);
parent ngoài scope → 404; reassign khóa task + `to_assignee_id` qua `core.directory` (hr đăng ký, tránh vòng `hr→execution`);
workload summary = METRIC-HR-03 (`min(week_end, today)`); `details` BE↔FE↔mock (`blocking[]`, `reason=has_subtasks|self_approval|
distinct_approvers|same_assignee|not_found`, `field=reason|to_assignee_id`); seed reassign `emit=False`; ACT-create_task
`task_source=ai` + `source_ref`; `_brief` một query; `rule()` ON CONFLICT; alembic env bỏ `_m13_assignee_backfill` khỏi autogenerate.
#14 giữ `core/stub.py` (M1.4 dùng). **Nợ #9:** tiêu đề notification (approval_requested/decided, task_assigned) vẫn lưu text thô
(`title` = tên task / status), chưa có i18n key — chốt cùng M2.x notification i18n.

## M1.1 — Nền build v3 (09 §6.2) — đã làm
| Task | Commit | Nội dung |
|---|---|---|
| T-602 | `6dc3d7c` | 10 §1.4 phản chiếu `core/errors.py`; contract test xanh |
| T-603 | `a4687a6` | Lọc `tenant_id` fail-closed (repo + outbox/consumer, migration `0010`) |
| T-603b | `4059b5e` | Seed v3 ABC theo 08 §2.1 (7 phòng ban, 154 NV, 10 user + `ai-agent`), `seed_snapshot.json` |
| T-605 | `4ee0d8e` | `packages/shared-types` sinh từ OpenAPI + drift check |
| T-604 | `77201b5` | Mock BFF `API_MODE=mock` (cấm ở production), mock login 7 role |
| T-606 | `d80bde8` | Playwright 2 project `mock` / `real`; tag `@mock`, `@mock-only` |
| T-607 | `12f8170` | IA v3: Sidebar 8 mục + Quản trị, route v3, 308 từ route v2.1, "Sắp có"; fix IDP CEO-scope |
| T-608 | `b112bc9` | Đóng băng product/risk: `p1_frozen`, Executive mặc định F/O/C, 5 trụ chỉ ở SCR-03 |
| T-609 | `65072d3` | E2E login + điều hướng 7 role trên `real` |
| T-610b | `3673bac` | Rebuild image `api`/`web`; **đăng nhập nhanh 10 role** bằng nút (mật khẩu giải ở server, không ra browser); gỡ `NEXT_PUBLIC_DEMO_PASSWORD_*` khỏi `.env.example` |
| T-610c | (commit này) | SCR-13 quay lại **dropdown 10 tài khoản**; chọn → Route Handler `POST /api/demo-credentials` (chỉ khi `DEMO_MODE=true` **và** `DEMO_LOGIN_AUTOFILL=true`, whitelist `DEMO_ACCOUNTS`, `no-store`) điền **cả email và mật khẩu**; không tự submit; nút con mắt Eye/EyeOff (aria-pressed, 44px). R-DEC-28 |

**Verify đóng phase (2026-10-23):** gate DoD xanh · pytest 808 (`--cov` 97%, bảo mật ≥ 91%) · Vitest 80 ·
contract 14 · alembic `downgrade -1 && upgrade head` sạch · Playwright `mock` 28/28 (không backend) · `real` 58/58
(web `next start` :3200 + API host :4100 trên DB dev — container `web`/`api` :3000/:4000 còn image cũ).


**Verify T-610b (2026-10-23):** lint/typecheck sạch · Vitest **84** (thêm `demo-accounts.test.ts`) ·
Playwright `real` **58/58** trên stack docker `:3000`/`:4000` (image mới) · HTML `/login` không chứa mật khẩu ·
9 service compose healthy.

**Verify T-610c (2026-10-23):** lint/typecheck sạch · Vitest **94** (+`demo-credentials.test.ts` 7, +`password-toggle.test.ts` 3) ·
image `web` rebuild, curl :3000 (200 cho email demo, 404 `NOT_FOUND` ngoài whitelist, `no-store`, HTML `/login` không chứa mật khẩu) ·
**human thử tay 8 bước: OK**. pytest/contract/Playwright **chưa chạy** (xem chính sách test bên dưới); TC-M11-16/17 = Implemented.

**Chính sách test (human chốt 2026-10-23):** mỗi task chỉ chạy kiểm tra nhanh (lint/typecheck/Vitest; BE thêm ruff/mypy)
+ rebuild image + hướng dẫn thử tay → human test và phản hồi → commit (`[full-test pending]`). **Full test** (pytest,
contract, Playwright `mock` + `real`) dồn đến cuối phase khi human xác nhận ổn hết; lúc đó mới đổi TC sang Passed.
Lưu ý môi trường: `.env` cần `DEMO_LOGIN_AUTOFILL=true` để autofill chạy trên stack demo (production: `false`, `DEMO_MODE=false`).

**Rủi ro / nợ còn lại:** FIN-06 ≈ 8% (08 ghi ~12%,
human chốt giữ); DQ-01 phụ thuộc giờ hệ thống; `scripts/gen_demo_docs.py` còn assert 45 NV; mock router chỉ phủ
dashboard + ai; dashboard 3 cấp theo role vẫn là "Sắp có" cho MGR/EMP/REV/ADM (M2.1); bộ tài liệu mẫu
`data/DOC-01..07` vẫn là bản v2.1, chưa khớp seed ABC mới.

## Phase 1 — đã làm (R-DEC-07/08/12/12a/13)
- **7 role v3** (`CEO/DIR/MGR/EMP/REV/ADM/AI`) thay 10 role F.O.C.U.S. `DIR` = union quyền 5 C-level cũ.
- **`scope_pillars`** (⊆ F.O.C.U.S) phân biệt khối của DIR, enforce server-side mỗi request (R-DEC-12a):
  Finance-DIR={F}, Sales-DIR={C}, HR-DIR={O}, Product-DIR={U}, Risk-DIR={S}.
- **`tenant_id`** mọi business entity (`TenantMixin`, 47 bảng) + JWT claim; migration `0009_v3_roles_tenant` reversible + backfill.
- **Cô lập khối per-module**: record/write theo khối; aggregate (`:query`) mở cho mọi DIR; dashboard HR giới hạn
  khối O/F/S; hiring-approve = Finance-DIR (cổng ngân sách); mức 4 (lương) chỉ CEO + HR-DIR, payroll aggregate thêm Finance-DIR.
- **Autonomy L0–L3 (L4 khóa) + kill switch**: xác nhận còn nguyên, không coupling role cũ.
- **FE**: messages vi/en role.*, LoginForm demoAccount.*, pillars (CEO+DIR = all 5), demo-accounts → v3 codes.
- **Docs** (R-DEC-14 cho đợt code): 05 field-level; 13 R-DEC-12/12a/13/14; 14 §1.4 trạng thái Phase 1.

## Gate verify (phiên code Phase 1)
- BE `uv run pytest`: **770 passed** (toàn bộ role/scope xanh; gồm `test_auth` login + `test_seed` 7 role/10 user).
- FE: `pnpm lint` ✅ · `pnpm typecheck` ✅ · `pnpm test` **18/18** ✅.
- `uv run ruff check .` ✅ · `uv run mypy` ✅ (263 files).
- **E2E Playwright: CHƯA chạy lại** trong phiên resume (docker DOWN) — chờ môi trường có docker rồi `pnpm test:e2e`.

## Nợ kỹ thuật tiền-tồn (KHÔNG do Phase 1)
- 4 case `tests/contract/test_api_contract.py` FAIL: khi promote doc 10 sang v3 (commit `7a31c10`, trước Phase 1),
  bảng mã lỗi `### 1.4.` bị gỡ ("chốt danh sách đầy đủ ở đợt code — R-DEC-09"). Test parse bảng không còn tồn tại.
  Xử lý ở task riêng: viết lại contract test lấy mã lỗi từ `core/errors.py` (cần DEC về nguồn-sự-thật mã lỗi).

## Kế tiếp
- **Kế hoạch build MVP v3: `docs/3.EXECUTION/09-BUILD-PLAN-TASKS.md` §6** (M1.1→M3.5, vòng S→C→F→B→N→R; quyết định 13 §2ter R-DEC-15..27).
- **M1.1 xong** trên nhánh `v3/m1.1-foundation` (chưa push). Kế: human review → PR → `ai-eos`, rồi Spec lock M1.2 (09 §6.0).
- (Tuỳ chọn) P1.6 enforce `tenant_id` filtering trong repositories/services (mới có model + migration + JWT claim).
- Chạy E2E login 7 role khi docker sẵn sàng; nếu fail → fix rồi mới đóng hẳn.
- Phase 2 theo `docs/3.EXECUTION/09-BUILD-PLAN-TASKS.md` (review + fix gate giữa các phase).

---

# Lịch sử nền v2.1 (archived — chỉ tra cứu)

> Dưới đây là nhật ký build của **nền Aureon v2.1** (5 trụ F.O.C.U.S, 10 role, demo-ready, sprint S0→S5d,
> push lên `main`). Nền này được **tái sử dụng** làm điểm xuất phát cho v3 và refactor dần theo phase.
> Các con số (777 test, 5/10 demo account role cũ, DEC-2xx) phản ánh trạng thái v2.1, KHÔNG phải v3 hiện tại.

## [v2.1] T-518 final verification checklist (2026-10-22)
- [x] `docker compose -f docker-compose.full.yml up` → 9 services healthy (cold start 26 s)
- [x] Login CEO → dashboard F🟢 C🟢 U🟡 O🟡 S🔴 with 13 alerts (E2E `dashboard.spec.ts`, `roles.spec.ts`)
- [x] Chat "Doanh thu Q3?" → 1,32 s total (TTFB 0,25 s) with citations [1][2][3]; "Top 5 khách hàng?" 1,17 s
- [x] Login reviewer → queue → approve → invoice committed (E2E `roles.spec.ts`, `review-detail.spec.ts`)
- [x] `pytest --cov` → 777 passed, 96%
- [x] `pnpm build` → 0 errors · lint / typecheck / ruff / mypy clean · contract 11 passed
- [x] `README.md` root + `docs/DEMO-SCRIPT.md` present
- [x] `scripts/demo_reset.sh` works (~13 s, verified 5 users · 32 metrics · 13 alerts · 1 NEEDS_REVIEW)
- [x] Git clean, pushed to main

## [v2.1] S5d demo polish + release (done 2026-10-22, direct route)
- **Governance** `929b167`: S5b-lite accepted, DEC-241 approved, S5b-full deferred.
- **T-513** `cc54910` `docker-compose.full.yml`: postgres, redis, minio, ollama, clamav, api, celery-worker, celery-beat, web on `aureon-net`; healthchecks on all 9; persistent volumes pg/minio/ollama/clamav (+redis); `env_file: .env` + in-network host overrides; `api` = `alembic upgrade head && python -m app.seed && uvicorn`; worker/beat wait for api healthy; JWT keys `./keys:ro`; OmniRoute via `host.docker.internal`. New `apps/web/Dockerfile` (Next 15 build, NEXT_PUBLIC_* non-secret build args only). Fixed api image perms (`pyproject.toml` unreadable for uid 1000).
- **T-514** `5c40d05` root `README.md` rewritten for v2.1 (quick start, accounts, features, mermaid, tests, license) + `docs/DEMO-SCRIPT.md` (5-min walkthrough + pre-demo checklist + troubleshooting).
- **T-515** `2e94206` `core/health.py` probes (2 s timeout each, never raise) + `core/ops_routes.py` (`/health`, `/health/ready`, `/health/live`, `/metrics` Prometheus text, no new dependency) + EP-01 `/api/v1/health` envelope; web `/api/health` proxy. Ollama down → `degraded` + 200 (verified live by stopping the container). DEC-242.
- **T-516** `a50c82e` `e2e/roles.spec.ts` (5 roles). Needed minimal screens: `/hr/employees` (EP-82) and `/admin/audit` (EP-52 implemented — was in 10, missing in code). DEC-243. Flaky fix: wait for pillar `data-status` before click.
- **T-517** `6511778` `scripts/demo_reset.sh`: TRUNCATE 10 module schemas (keeps alembic_version) → seed → clear IDP store + MinIO → purge Celery + restart worker/beat → 1 invoice NEEDS_REVIEW → verify.
- **T-518** final verification (this file). Fix: IDP integration tests now hide pre-existing dev-DB queue docs inside the rolled-back transaction (they failed after a demo reset left 1 NEEDS_REVIEW invoice).

### S5d notes / gaps
- Brief numbering T-513..T-518 ≠ 09 (09 T-513 = seed v2.1, still pending).
- MinIO not used by the app in demo (local-FS IDP store, DEC-234); reset clears both anyway.
- `/metrics` exposes build info, uptime, dependency up/down and HTTP response counters only.
- EP-52 filters `from`/`to`/`actor_type` not implemented yet; SCR-26 user admin not built.
- Demo passwords for ADMIN are not in the login dropdown (5 accounts only, by design).

## S5b-lite ACCEPTED (human, 2026-10-22 — S5d brief, DEC-241 approved)
- Lineage drill-down simplified (uses finance list endpoints; EP-13/14 deferred).
- Sparklines: 12 monthly points (no daily series).
- `/dashboard/focus` not built — per-pillar endpoints sufficient.
- Live model 9–13 s accepted (Claude Sonnet standard latency).
- T-512 (O/C/U/S drill-downs) deferred → S5b-full post-demo.
- Next: **S5d demo polish + release (T-513..T-518)**.

## S5b-lite demo polish (done 2026-10-22, direct route; 4 commits, pushed)
- **Governance** `585e77a`: DEC-237..240 APPROVED (human); backend S4c deferred for all of S5.
- **T-509** `17d2adb` chat fix (DEC-241): chat model chain `CHAT_MODEL_PRIMARY=cc/claude-sonnet-5` → `CHAT_MODEL_FALLBACK=cl/deepseek/deepseek-v4.1-flash` (brief named `deepseek-v4.1-flash-uncensored` — not routable on OmniRoute without provider prefix), 1 attempt/model, `CHAT_TIMEOUT_SECONDS=90` (chat only). `AI_DEMO_REPLAY` (default = `DEMO_MODE`) replays 10 recorded intents from `apps/api/src/app/modules/ai/demo_responses.json` — **numbers always from live tools run as the asker** (no fake numbers; missing permission/value → real model), warning `ai.warn.demo_replay`. System prompt tuned for ≤ 2 tool rounds. FE: `streamSse(..., timeoutMs)` 120 s → `AI_STREAM_TIMEOUT`; `WaitHint` 10 s "AI đang suy nghĩ..." / 30 s "Đang xử lý phức tạp, vui lòng đợi..." / 90 s "AI đang mất nhiều thời gian, thử lại sau". Side fixes: cost-service test baseline-relative (dev DB has live logs); gateway unit tests pin chat chain empty; E2E review specs clean up leftover `hoa-don-E2E*` docs (`seed_review_doc.py --cleanup`).
- **T-510** `316a0c4` period picker: `PeriodPicker` "Kỳ báo cáo: T9/2026" + [Tháng này | Tháng trước | Q3 | Q4] relative to `NEXT_PUBLIC_DEMO_REFERENCE_DATE=2026-10-20` (not a secret); period in URL `?period=` (kept across drill-down). No new endpoint: `/dashboard/focus` does not exist in 10 — the 6 pillar endpoints (EP-49/60/70/80/90/100) already take `period`; contract test `test_dashboard_period_picker.py` covers 2026-10/09/Q3/Q4 on all 6. **Bug fixed:** `/finance/dashboard?period=2026-13` returned 500 → now 400.
- **T-511** `134d7a5` Finance drill-down `/dashboard/pillar/finance`: "Trụ Tài chính" + status badge + period picker; 6 cards (Doanh thu 25,5 tỷ, Chi phí, Sử dụng ngân sách 97,3%, Runway 13,6 tháng, Số dư tiền mặt 20,4 tỷ, Burn rate 1,5 tỷ) with trend arrow + 12-period sparkline (monthly series from EP-60 `revenue_trend`/`runway_trend` + EP-63 cash positions — no daily 30-day series exists in the data model). Click → `LineageDialog` 3 levels: metric (EP-12) → component records (finance lists for the month) → source doc (EP-25 via IDP-committed invoice). EP-13/EP-14 not implemented → simplified per brief; seed records show "chưa gắn tài liệu gốc".
- **T-512** (O/C/U/S drill-downs) skipped — optional; other pillars keep the S5a stub list.

### S5b-lite notes / gaps
- Live chat 9–13 s on multi-tool questions (target 3–10 s met for simple ones only); demo replay covers the 10 scripted questions. Further: cap tool rounds per turn, or pre-warm.
- Sparklines are monthly (12 points), not 30 daily points — no daily finance series in 05.
- Budget / Burn cards have no series in EP-60 (hint text instead).
- Finance cards are not period-scoped for cash (latest closing ≤ selected month).

## S5a FE foundation + 4 MUST screens (done 2026-10-22, direct route; 8 commits, pushed)
- **S4c deferred** — internal polish (full doc-type catalogue, ENT-DataLineage 4-cấp, EP-33 rollback). Defer to post-S5 if scope permits. S4d (C2/C4/C5 breadth) deferred, optional (DEC-240). Backend IDP not touched this sprint.
- **T-501** `16492d0` Next.js 15.5 App Router in `apps/web` (TS strict + `noUncheckedIndexedAccess`), Tailwind 4 tokens (`ai` violet ≠ `primary` blue), shadcn-style ui (button/input/label/card/badge/select/dialog/popover/checkbox/collapsible/tooltip/dropdown/toast), next-intl vi/en (251 keys each, cookie `NEXT_LOCALE`), `lib/{api-client,sse,format,query-keys}.ts`.
- **T-502** `4578cd0` NextAuth Credentials → EP-02; backend access+refresh token only inside the encrypted httpOnly NextAuth JWT. BFF `app/api/backend/[...path]` adds Bearer, single-flight refresh (EP-06 rotation), streams SSE (`X-Accel-Buffering: no`). `middleware.ts` → `/login?callbackUrl` / rewrite `/403`; `lib/permissions.ts` route rules + nav + role landing.
- **T-503** `ca3f3f8` SCR-13 login (rhf+zod), demo dropdown (5 accounts) fills email; password resolved server-side from `DEMO_*_PASSWORD` when `DEMO_MODE` (never `NEXT_PUBLIC_*`). Error from `{error:{code}}` mapped via i18n.
- **T-504** `52af5cf` App shell: role-filtered sidebar (Dashboard/IDP/AI/Approvals), header avatar/role badge/logout/VI-EN switcher (server action). ≥1280 full (collapsible), 768–1279 icons, <768 drawer.
- **T-505** `e5be7fe` SCR-02: 5 pillar cards (5/2/1 cols), one query per domain endpoint (O = hr + execution worst), 60 s refetch, failed source → "Không khả dụng" + retry; Recharts sparkline from `*_trend`; 13 alerts critical-first + Acknowledge (EP alert ack, Idempotency-Key). Period `2026-09` (DEC-237) → 2g/2y/1r. `/dashboard/pillar/[slug]` stub (metrics list) for S5b.
- **T-506** `822a17f` SCR-16 chat: SSE over POST via `lib/sse.ts`, pure reducer (start/tool_call/tool_result/token/done/error), `ThinkingState` collapsible "AI đang dùng tool: …", `SourceChip` `[n]` popover, new chat + history (EP-112). E2E stubs SSE (DEC-238); live transport verified via curl through BFF.
- **T-507** `e46b658` SCR-18a queue: table (filename/type/confidence/critical/assigned/age/Review), filters status/doc_type/assigned(me), pagination limit/offset, empty state + Upload (EP-20 multipart).
- **T-508** `d738e65` SCR-18b: 2 columns (text-layer source viewer + highlight/bbox | field form: ConfidenceBadge, confirm checkbox, correction input, reason for money fields, red border + tooltip), EP-29 open / EP-35 release, EP-30 patch → EP-31 approve → toast "Đã ghi vào Finance" → queue; reject dialog (reason). `/finance/invoices` list (direction filter) shows the committed invoice. `/approvals` placeholder.
- **E2E seed:** `apps/web/e2e/support/seed_review_doc.py` (UploadService + Pipeline, fixture gateway; unique invoice number per run) called from Playwright via `.venv/bin/python`.

## S5a exit criteria
| Criterion | Result |
|---|---|
| `pnpm build` / `next start` :3000 | ✅ |
| Login 3 demo accounts (CEO, CFO, REVIEWER) | ✅ |
| Dashboard 5 cards 2g/2y/1r + 13 alerts | ✅ |
| Chat streaming + citation | ✅ (fixture SSE, DEC-238) |
| Queue + filters | ✅ |
| Detail + approve → invoice visible | ✅ |
| Role nav + 403 | ✅ |
| Responsive 1440/1280/768/390 | ✅ (`responsive.spec.ts`, screenshots `apps/web/test-results/screens/`, gitignored) |
| 4 Playwright flows (login, dashboard, chat, review) | ✅ 20 tests passed |
| TS strict, ESLint 0 warnings, no `any` (`no-explicit-any: error`) | ✅ |

**FE routes:** 10 pages (`/`, `/login`, `/403`, `/dashboard`, `/dashboard/pillar/[slug]`, `/ai`, `/idp/review`, `/idp/review/[documentId]`, `/finance/invoices`, `/approvals`) + 2 route handlers (`/api/auth/[...nextauth]`, `/api/backend/[...path]`).

### Run E2E
API :4000 + Postgres seeded, then `pnpm --filter @aureon/web build && pnpm --filter @aureon/web start` and `E2E_NO_SERVER=1 pnpm test:e2e` (or let Playwright start `pnpm start`). `apps/web/.env.local` (gitignored) carries NEXTAUTH_* + demo passwords copied from root `.env`.

### S5a notes / gaps
- Chat live: OmniRoute `auto/coding` ~39 s/answer > 30 s turn limit → `AI_PROVIDER_TIMEOUT` in live mode; pick faster `MODEL_CHAT` or record fixtures (T-321).
- Optimistic lock: review detail has no `version`/`ETag`; FE sends `If-Match` only if ETag appears (DEC-237 note). Soft lock EP-29 + 409 cover concurrency today.
- Dashboard period fixed to T9/2026; period picker + full drill-downs SCR-02..06 = S5b.
- Not yet: axe-core (TC-UI-020/027), TTFT measurement, ⌘K panel, dark-mode toggle, PWA.

## Done
- S0, S0b, S1 (Finance/Sales/HR) — see git history (`ed1836a`).
- S2 (`a0fd762`):
  - T-220 metric store (`platform.services.metric_store.MetricStore.recompute`, providers `@metric_provider` per module), METRIC-DQ-01 (`core/data_quality.py` + `register_dq` per domain, DEC-209).
  - T-221 alert engine; budget_exceeded → alert < 60 s test.
  - T-222 pillar dashboards EP-60/70/80/90/100 + EP-49 from store (`pillar_snapshot`), partial-failure isolation.
  - T-131..133 execution, T-201/202 product, T-211..216 risk (merged worktrees `/home/vika/aureon-wt/{exec,prdrisk,risk}`).
  - T-234 pgcrypto level-4 PII, migration `0008_pgcrypto`; T-235 Celery beat (7 entries incl. outbox relay, detect-overdue-tasks 08:30).
  - T-236 seed: auth + finance + hr + sales + product + risk + execution (reduced, DEC-208). Dev DB: 32/32 metrics valued, 25 OPEN alerts, all dashboards 200.
- Shared: `core/periods.py` (period resolution, breaks hr↔execution cycle); metric provider registry tolerates re-import of same function.

## S2 exit criteria
| Criterion | Result |
|---|---|
| 5 pillar endpoints 200 | ✅ (+EP-49) |
| ≥ 10 alerts from seed | ✅ 25 OPEN |
| revenue → budget_exceeded → alert ≤ 60 s | ✅ `tests/events/test_alert_sla.py` |
| beat jobs registered | ✅ 7 entries |
| 3 pgcrypto tests | ✅ |
| Sales/HR dashboards non-zero | ✅ |
| 32 metrics populated | ✅ |
| Coverage ≥ 95 %, gates A/B/C | ✅ 98 % |

## T-237 seed rebalance (done 2026-10-22, direct route cc/claude-sonnet-5; 3 commits)
- **Step 1** (analysis, no edits): identified per-pillar levers vs DEC-143.
- **Step 2** `b0cefa4` feat(s2): seed data → **F,C green · U,O yellow · S red**. Edited `finance_data.py` (cash flatter→runway 13.6, Q3 budget ≤ alloc, Oct MTD trimmed, 8 carried-forward open invoices `HISTORICAL_OPEN_INVOICES` + `HV_PAID_IN_FULL`), `sales_seed.py` (Sep target 26.0tỷ, Q4 18.0tỷ, `attribute_revenue` splits big row over 5 anchor clients + frozen window for NRR), `product_seed.py` (Sep churn 1.79, retention 43, NPS lift), `hr_seed.py` (1 plan 40d late). Updated 3 finance_seed assertions.
- **Step 3** `3bdee1f` feat(platform): `SEED_PASSWORD_CPO`/`SEED_PASSWORD_RISK_MANAGER` aliases on config + `.env.example`. Dev `.env` got CPO/RISK/MANAGER/EMPLOYEE/ADMIN passwords → seed creates all 10 users; product owner=CPO, risk owner=RISK_MANAGER.
- **Verified** (clean-DB `python -m app.seed` + in-process API as CEO): F green · C green · O yellow · U yellow · S red; 13 OPEN alerts (11 WARNING + 2 CRITICAL). `probe3.py` harness truncates domain schemas in a rolled-back tx.
- **DEC-230 APPROVED** (human 2026-10-22): F🟢 C🟢 U🟡 O🟡 S🔴 is the official demo layout; DEC-143/152 "demo layout" superseded_by DEC-230 (thresholds unchanged, NFR-19).
- **DEC-231 APPROVED**: alert severity enum = WARNING|CRITICAL only (INFO = log level). "≥10 alerts" = ≥10 alerts **any severity** (met 11W + 2C = 13).
- Gate: ruff ✅ · mypy ✅ (226 files) · pytest 585 ✅.

## S3 AI Core (done 2026-10-22, direct route; 10 commits incl. DEC governance)
- **DEC-230/231 governance** `ad5c598` — demo layout + alert-severity enum approved (gate prelude).
- **T-301** `1212181` Tool Registry: 43 `TOOL-*` with §7.4 metadata (27 QUERY + 13 WRITE + 2 APPROVAL + 1 EXECUTION), `advertisable_for`/`available_for` permission + classification filters.
- **T-302** `9413b9e` Chat orchestration EP-110 + SSE EP-111 (`start→thinking|tool_call→tool_result→token→done`, `X-Accel-Buffering: no`); tool-calling loop (≤ 8 calls, budget warning); prompt_guard classification routing (salary→SECRET no-LLM, PII→CONFIDENTIAL local-only); `<<<DATA … DATA>>>` injection guard.
- **T-303** `c0bf68c` Proactive insights: 9-part grounded `ENT-Insight` from worst-status metric, evidence-gated (≥1 SourceRef), EP-114 list/dismiss with pillar-scope hiding.
- **T-304/305/306** `db9447c` AI action lifecycle (`ENT-AIAction`: propose→L3 auto-exec | L2 confirm card; undo 24h via `TaskService.delete`), Action Registry single write gate, 2-sided approval (finance ≥500M → CEO step1 + CFO step2, distinct approvers), kill switch per-agent/global WRITE_OFF|L0 (L3→L2). Cross-module via `core/approval_hooks.py` (breaks platform↔ai cycle, DEC-125).
- **T-307** `63ecc31` Outcome verification 24h/7d: scores metric status movement (improved/worsened/unchanged/not_measurable) vs baseline captured at propose time, reading current status via platform `MetricQueryService`.
- **T-308** `6a413d4` Cost & usage EP-119 `/ai/usage` (`ai:admin`): aggregates `ENT-ModelCallLog` → budget/used/used_pct + per-key rows (calls/tokens/cost/error_rate/p95_ms) grouped provider|model|task_kind|user; warn 80% / over 100% vs `AI_MONTHLY_BUDGET_USD` (DEC-131).
- **T-309** `ea9866e`+`b954f47` PII filter: `scrub_for_model` drops level-4 PII, tokenises level-3 contacts to stable `EMP-`/`CLI-` codes before every model call (5.5, FR-AI-10).
- **T-310** `0e4d8aa` E2E + coverage: HTTP sweep of EP-110..119 via overridable `get_chat_gateway` dep + service edge branches → **ai coverage 95%** (S3 exit met).
- **Gate:** ruff ✅ · format ✅ · mypy ✅ (242 files) · pytest **667 passed**.

## S3 exit criteria
| Criterion | Result |
|---|---|
| Chat SSE EP-110/111 event order | ✅ |
| Tool Registry 43 tools, permission-filtered | ✅ |
| 9-part grounded insight, no fabricated numbers | ✅ (evidence-gated) |
| Autonomy L0–L3 + undo 24h + kill switch | ✅ |
| 2-sided approval ≥500M (CEO→CFO) | ✅ |
| PII scrub + classification routing | ✅ |
| Cost log + EP-119 usage | ✅ |
| ai coverage ≥ 95%, gates A/B/C | ✅ 95% |

## S4a IDP pipeline core (done 2026-10-22, direct route; 3 commits)
- **T-401** `0ee6214` EP-20 `POST /idp/documents` (1..100 file, 50MB/file, MIME whitelist + magic bytes, stream chunk 1MB), sha256 dedupe → `DUPLICATE` linked to original, `ImportBatch` for multi-file, `ExtractionJob` QUEUED, audit `idp.upload`. New `core/storage.py` (local-FS `ObjectStore`, `quarantine` bucket — prod swaps MinIO/S3 same interface). `schema_registry.py` seeds DocumentType/ExtractionSchema/ValidationRule (INVOICE 04 §5.5 + OTHER) idempotently. `query_service.py` EP-25/26 + dept scoping. Config: `IDP_STORAGE_DIR`, `IDP_MAX_FILE_SIZE_MB/PAGES/FILES`, `OCR_PROVIDER`.
- **T-402..T-405** `cddb33e` pipeline core:
  - malware_scan (T-402): clamd TCP + EICAR local detect; INFECTED→`FAILED` `status_reason=MALWARE` + `quarantine` bucket; `CLAMAV_REQUIRED=false`→`SKIPPED` (DEC-138).
  - preprocess (T-403): text-layer check before OCR; PDF(pypdf)/DOCX/XLSX/CSV/image; `DocumentPage` per page; `OCR_PROVIDER` stub|paddle (paddle lazy-imported, DEC-049).
  - extractor (T-404): ModelGateway `task=extract`, classification by sensitivity (4→SECRET no-LLM, 3→CONFIDENTIAL local, ≤2→cloud), schema-driven prompt, field result `{value, confidence, source_location, confidence_band}`, bands HIGH≥0.90/MEDIUM 0.60/LOW (DEC-133), null not fabricated (P05). Gateway injected (DI, DEC-233).
  - validator (T-405): ValidationRule ops required/gt/lte/in/`date_not_future`/`sum_equals`; VN number/date parsing; errors → `ExtractionJob.xd_results.validation_errors`.
  - pipeline orchestrator: `UPLOADED→PREPROCESSING→CLASSIFYING→EXTRACTING→VALIDATING→NEEDS_REVIEW|AUTO_APPROVED` (MALWARE→FAILED). STP routing (04 §7.3): doc conf ≥0.95 + required fields ≥0.90 + no critical field + no validation error, else REVIEW. Keyword classifier picks INVOICE vs OTHER (full 9-type LLM classify = later sub-sprint). Celery `app.idp.process_document` (idempotent, time_limit).
- **Tests** `17d26f4`: 43 new (`tests/unit/test_idp_*.py` + `tests/integration/idp/`); `sample_docs.py` builds in-memory PDF(text+scan)/DOCX/XLSX/EICAR/PNG from runtime deps only (no reportlab).
- **Gate:** ruff ✅ · format ✅ · mypy ✅ (254 files) · pytest **710 passed**.

## S4a exit criteria
| Criterion | Result |
|---|---|
| EP-20 upload C1/C3/C4 → job created | ✅ |
| malware blocks EICAR (quarantine) | ✅ |
| OCR/text extract (PDF text + scan + DOCX/XLSX) | ✅ |
| LLM extract field results + confidence bands | ✅ |
| validation rejects invalid (neg amount, future date, bad sum) | ✅ |
| pipeline upload→scan→OCR→extract→validate → `NEEDS_REVIEW` | ✅ |
| coverage `modules/idp/services` ≥ 90% | ✅ 96% |
| gates A/B/C | ✅ |

### End-to-end sample (invoice.pdf, in-process pipeline)
upload → `UPLOADED` + QUEUED job → scan `SKIPPED/CLEAN` → text-layer extracted (1 page, pypdf) → classify `INVOICE` (0.99) → extract 8 fields (subtotal/vat/total HIGH, critical) → validate (VR-INV-02/03/SUB/05 pass) → route `REVIEW` (reason `CRITICAL_FIELD`) → **`NEEDS_REVIEW`**.

## S4b IDP review workflow (done 2026-10-22, direct route)
- **New services:** `modules/idp/services/review_service.py` (queue EP-28, detail, open/release EP-29/35, patch_fields EP-30, reject EP-32, reassign EP-126, merge EP-127), `commit_service.py` (approve EP-31 → `finance.Invoice` via Action Registry pattern, `idp.document_committed`, undo_deadline +7d), `sla_service.py` (T-412 `check_review_sla` → `idp.review_escalated` + Notification, manager @>SLA / dept-head @>2×SLA, idempotent). `modules/platform/services/notification_service.py` (public cross-module Notification writer, DEC-125). `auth.AuthService.find_user_by_role` (escalation routing lookup).
- **Routes** (idp router, all guarded `idp:approve`): `GET /idp/review-queue`, `GET /idp/documents/{id}/review`, `POST .../review/open`, `PATCH .../fields`, `POST .../review/approve|reject|release|reassign`, `POST /idp/review-queue/merge`.
- **Config:** `review_sla_hours` default 24 (env `REVIEW_SLA_HOURS`). **Beat:** `check-review-sla` hourly at :15 (worker.py + jobs.py). No schema change (all tables existed from S4a) → no migration.
- **Pipeline:** on entering `NEEDS_REVIEW`, creates the initial `ReviewAssignment(kind=ASSIGN, to_role_code=REVIEWER, due_at=now+SLA)` driving the queue + SLA clock.
- **Approve→commit mapping (INVOICE→finance.Invoice):** direction=IN (received supplier invoice); number←invoice_number, issued_on←issue_date, counterparty←seller_name/seller_tax_code, due_date=issued_on+30d (derived — not an extracted field), one aggregate line subtotal/vat_pct; finance business-rule failure (e.g. duplicate number) → `ACTION_REJECTED` (doc stays `APPROVED`). OTHER doc type → metadata-only commit (`actions=[]`). Full doc-type catalogue + undo (EP-33) = S4c.
- **Field correction:** confirm persists AI value into `corrected_value` (so `effective_value` is unambiguous vs `clear`→None); money field edit requires `reason`→422; `accept_all_high` confirms HIGH non-critical only.
- **8-step integration** `test_review_e2e_http.py` over the real HTTP app (upload→queue→detail→correct+reason→recompute→approve→`finance.Invoice`→dashboard) — Passed.
- **Gate:** ruff ✅ · format ✅ · mypy ✅ (258 files) · pytest **741 passed** · contract ✅.
- **Errors/DTOs** (added earlier this session): `ReviewLockedError`/`UndoExpiredError`/`ActionRejectedError`; review DTOs in `idp/schemas/__init__.py`.
- **Stopped at S4b exit per brief — did NOT enter S4c.**

## S4b exit criteria
| Criterion | Status |
|---|---|
| EP-28..35 + EP-126/127 built | ✅ (EP-33 rollback = S4c) |
| coverage `review*` ≥ 90% | ✅ 90/90/91% |
| gates A/B/C | ✅ |
| 8-step integration verified | ✅ |

## S4b pre-flight (2026-10-22, 3 checks)
- **Check 1 PaddleOCR:** `paddleocr` NOT installed; dev `.env` was `OCR_PROVIDER=paddle` → set to `stub` (reality). Code degrades gracefully (`except → "",0.0`); text-layer invoice.pdf unaffected. → **DEC-236** non-blocking (stub for demo, paddle for prod, DEC-049 still open).
- **Check 2 ClamAV:** ✅ REAL. Container `clamav` (ClamAV 1.5.4) reachable; live clamd `CLEAN` clean bytes, `INFECTED/Eicar-Test-Signature` on EICAR. `CLAMAV_REQUIRED` unset=false. → **DEC-235** confirms demo fallback + verified live.
- **Check 3 samples:** ✅ 7/9 doc types in `data/` (financial/invoice-xlsx/sales/contract/meeting/employee/kpi) + in-memory `sample_docs.py`. No new fixtures needed for S4b.
- **DEC-234** storage local-FS confirmed non-blocking. Baseline: 31 IDP integ/unit tests green after stub change.

## Remaining (in order)
1. **S4c** — commit + lineage + Action Registry v2 (full ACT-* catalogue to all domain services, rollback/undo 7d EP-33, `EVT-idp.document_rolled_back`, `ENT-DataLineage` field→record→metric, TC-IDP-008/009/020; detailed invoice line items; derived due_date policy). **Do NOT start without a new RESUME brief.**
2. **S4d** (optional) — C2 voice/transcript (T-416), C5 Excel import (T-407), UC-06/07/08 (T-408), full 9-type LLM classification + accuracy harness (T-403/T-414).
3. S5 FE/UX/Release; S2 FE tasks T-224..227, T-231/232, T-142/143 still open.
4. `[DEFERRED to S5]` T-223 lineage drill-down, T-233 + FE S2 (DEC-229).

## Next task
**S5b-full (O/C/U/S drill-downs, same pattern as T-511) or S5c (breadth)** — awaiting human RESUME brief. (Former next task, now deferred per DEC-240:) **S4c commit + lineage + Action Registry v2** — on next RESUME: read 09 §S4, 04 §10 (Action Registry, undo, lineage), 05 §ENT-DataLineage, 10 EP-33, gates A/B/C. Extend `commit_service.py` with the full doc-type→domain catalogue, `ENT-DataLineage` rows per committed field, and the 7-day rollback (EP-33) emitting `idp.document_rolled_back`. S4b review workflow sits ready: approved docs reach `COMMITTED` with `undo_deadline`.

## S4b notes / deferred (for S4c)
- **Commit path:** only INVOICE→finance.Invoice wired (reference path). OTHER = metadata-only. Remaining doc-type→domain maps (sales report→deals, employee list→hr, risk register→risks, etc.) + `ENT-DataLineage` field→record rows are S4c.
- **due_date derivation:** invoice commit sets `due_date = issue_date + 30d` because due_date is not an extracted INVOICE field; revisit in S4c if a payment-term field/policy is added.
- **Invoice line:** one aggregate line (subtotal as unit_price, extracted `vat_rate_pct`); finance recomputes vat_amount from pct (extracted vat_amount kept for lineage only). Detailed multi-line commit = S4c.
- **Escalation recipient:** `find_user_by_role` picks an active user by role (MANAGER then CEO as dept-head stand-in), preferring the doc's department; the ESCALATE assignment also carries `to_role_code` so routing works even if no concrete user resolves.
- **Approve authority:** `idp:approve` on the review is the authority to commit (Action Registry gate); the reviewer's Principal is passed to `finance.InvoiceService.create` as `created_by` even without `finance:write` — matches 04 §10.4 Action Registry pattern. Worth a DEC if prod wants a separate finance-write check on commit.
- **No new deps / no schema change / no new events beyond registered** (`idp.document_committed`, `idp.review_escalated` already registered).

## S3 notes / findings
- EP-125 approval executes the AI action with the **approver's** Principal as actor (04 §10.4). A finance approver (CFO, department-scoped for execution) cannot create a cross-department task — the on-behalf-of requester's authority is not reconstructed. Covered at service level by passing a full-scope actor; worth a DEC if finance approvals must create execution writes in prod. Non-blocking for S3.
- `get_chat_gateway` FastAPI dependency added so chat/stream routes are testable without a provider (`app.dependency_overrides`).

## Key files
- `apps/api/src/app/modules/platform/services/{metric_store,pillar_snapshot,metrics}.py`, `core/{metrics,data_quality,periods}.py`
- `apps/api/src/app/seed/{__init__,finance_seed,hr_seed,sales_seed,product_seed,risk_seed,execution_seed,ids}.py`
- `apps/api/src/app/workers/{consumers,jobs}.py`, `apps/api/src/app/worker.py`
- Env: `export PYTHONPATH=$PWD/apps/api/src:$PWD/apps/api PATH=$PWD/.venv/bin:$PATH` (never `uv sync`).

## Human decisions (2026-10-22)
- DEC-227 (human "DEC-210"): DQ-01 = 87.0 accepted; 77.1 aspirational; calibration S4.
- DEC-228 (human "DEC-211"): sub-agents = single code tasks only; seed / cross-file / orchestration by DSH.
- DEC-229: deferrals above. (Numbers 210/211 were already taken by Product DECs → renumbered.)

## Known issues / gaps
- EP-74 `changed_by` null (DEC-191); MANAGER quota null; no log-redaction filter yet.
- ~~Dev DB only 5 users~~ **fixed by T-237**: dev `.env` now has all 10 demo passwords; product owner=CPO, risk owner=RISK_MANAGER.
- Risk: EP-104 doesn't create ENT-Decision; what-if product unavailable; `hr.employee_terminated` not consumed.
- Product BR-PRD-01 thresholds constants; execution constants not in config (DEC-226).
- METRIC-DQ-01 accuracy = validation proxy; IDP-correction component comes with S4c (commit/lineage).
- 09 task checkboxes not ticked (docs edit outside 14).

## S4a notes / deferred (for S4b/S4c)
- **EP path:** spec 10 §3.3 canonical is `POST /idp/documents` (brief said `/idp/documents/upload`); followed the spec. `channel` defaults to C3 (file); C1 manual form = EP-21, C2 = EP-22, C5 = EP-23 (not built in S4a).
- **Storage:** `core/storage.py` is a **local-filesystem** demo store (`var/idp-storage/`, gitignored) behind an `ObjectStore` Protocol — prod swaps MinIO/S3 without touching callers. No MinIO client dependency added (none in config; non-blocking demo infra).
- **OCR:** `OCR_PROVIDER=stub` default (deterministic empty text + 0.0 conf for image/scan pages) so CI needs no PaddleOCR. `paddle` path is lazy-imported and only runs if the package is present (DEC-049 fixture/replay demo still `open`, non-blocking). Scan-PDF/image → `ocr_used=True, text_layer_exists=False`.
- **Classification:** S4a uses a keyword classifier (INVOICE vs OTHER) to pick the schema. Full LLM 9-type classification + accuracy harness (TC-IDP-004/013) is S4d.
- **Schema catalog:** only INVOICE (full 8 fields + 4 VR) and OTHER seeded. Remaining 7 doc-type schemas + ADMIN CRUD (TC-IDP-001 full, T-413) deferred.
- **Extractor DI:** `Pipeline(db, gateway)` / `Extractor(gateway)` take an injected gateway (like chat, DEC-233) → testable with a fake returning `ChatResponse.data`; prod uses `pipeline_gateway(db)` = `AiService(db).gateway()`.
- **mypy:** added `[[tool.mypy.overrides]]` for `clamd`/`openpyxl`/`paddleocr` (no stubs; approved deps DEC-138/DEC-120).
- **Status mapping:** brief's `READY_FOR_REVIEW` = real enum `NEEDS_REVIEW` (05 §6 `document_status`). STP path → `AUTO_APPROVED` (commit itself is S4c).
- Celery worker/beat restarted after S2 merge (2026-10-22 06:25).
