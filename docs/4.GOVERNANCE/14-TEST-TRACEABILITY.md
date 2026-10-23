# 14 — Test Traceability (Aureon v3 — AI-EOS)

> **Vai trò:** Gate C. Ma trận UC/US/FR ↔ test cho bản rebuild AI-EOS.
> **Nguồn chuẩn:** `_reference/SOURCE-BRD-v1.1.md` §14 (UC nghiệm thu), §15 (US), §16 (NFR), §17.3 (Approval Matrix), §17.5 (AI Operating Loop); `SOURCE-BRD-v1.1-Bổ sung.md`; `SOURCE-UIUX.md`.
> **Phụ thuộc:** 00–10, `TRACEABILITY-SKELETON.md`. **Trạng thái:** ✅ current — Aureon v3 (AI-EOS) CHÍNH THỨC. **Ngày:** 2026-10-23 · **Maintainer:** @CyEyes
> *Tách từ Aureon v2.1 (nay archived ở `docs/_archive/v2.1/`).*

---

## 1. Chiến lược test AI-EOS

Mỗi UC/US/FR P0 → ≥1 test case (`TC-*`). Test theo tầng: unit (service/FR), integration (API/event), contract, E2E (UC), AI-eval (fixture). Ngưỡng coverage giữ nguyên CLAUDE.md §6.1 (service ≥80%, bảo mật ≥90%, FE ≥70%).

### 1.1. Nguyên tắc chiến lược (bám P01–P11)

AI-EOS là sản phẩm **AI-first** (P01) với con người trong vòng lặp (P04), mọi số truy nguyên được (P06, P07) và graceful degradation khi AI tắt (P10). Do đó pyramid test không chỉ có unit/integration/e2e cổ điển mà thêm một trục **AI-eval** độc lập. Khung chiến lược:

| Trục | Mục đích | Áp cho | Chế độ chạy |
|---|---|---|---|
| **Unit** | Đúng logic FR mức service: rule nghiệp vụ, state machine, công thức metric, routing confidence | Mọi FR P0 | thuần, không provider |
| **Integration** | Đúng hợp đồng API (envelope, mã lỗi, phân trang, idempotency) + đúng luồng event (outbox → consumer, dedupe) | EP-* P0, EVT-* P0 | DB thật test, Redis test |
| **Contract** | Response khớp OpenAPI; type FE↔BE không lệch | Mọi EP-* có `response_model` | thuần |
| **E2E** | Một UC chạy end-to-end xuyên nhiều domain đạt tiêu chí nghiệm thu BRD §14 | UC-01..08 P0 | stack đầy đủ, AI fixture |
| **AI-eval** | Grounding, no-hallucination, confidence routing, anti-injection, insight 9 phần, autonomy gating | D26 AI Platform, D27 CEO Assistant, D03 IDP | `MODEL_GATEWAY_MODE=fixture` (bắt buộc, không gọi provider thật) |
| **NFR** | PERF/SEC/AV/UX/AUD theo BRD §16 | hệ thống | theo loại (load, pentest, a11y) |

### 1.2. Phạm vi test đợt này (R-DEC-05, R-DEC-09)

- **Chỉ đặc tả tập P0** (xem `TRACEABILITY-SKELETON.md` §12bis): 20 domain P0, kênh C1–C5, Autonomy L0–L3, UC-01/02/03/04/06/07. UC-05, UC-08 là P1 → giữ trong ma trận nhưng đánh dấu backlog, không mở rộng tiêu chí.
- **R-DEC-09 (docs-first):** file này mô tả **khung chiến lược + ma trận + tiêu chí nghiệm thu mức sản phẩm + loại test cần cho mỗi nhóm FR**. KHÔNG sinh `TC-*` chi tiết (từng input/assert cụ thể), KHÔNG sinh task `T-*`, KHÔNG viết test code. Những thứ đó **chi tiết hóa ở đợt code (R-DEC-09)**.
- `TC-*` trong các bảng dưới là **nhóm/namespace** test (ví dụ `TC-UC01-*`), không phải case cụ thể — dùng để map traceability, định nghĩa đầy đủ ở đợt code.

### 1.3. Ngưỡng coverage & gate

| Phạm vi | Ngưỡng | Ghi chú |
|---|---|---|
| Service mỗi domain P0 | ≥ 80% | theo CLAUDE.md §6.1 |
| Backend tổng | ≥ 75% | |
| Bảo mật (RBAC+ABAC, field-level, PII filter, Action Registry, autonomy, kill switch) | ≥ 90% | gap bảo mật = blocking |
| FE `features/` + `lib/` | ≥ 70% | |
| AI-eval grounding/no-hallucination | **0 câu khẳng định số không có `SourceRef`** (chỉ tiêu nhị phân, không phải %) | P05/P07 |

Gate C đạt khi: mỗi UC/FR P0 có ≥1 nhóm `TC-*` mapping; không có test gap blocking (bảo mật, event idempotency, Action Registry, grounding, exit criteria của mốc).

### 1.4. Phase 1 — Refactor role 10→7 + tenant_id + review autonomy (trạng thái đợt code)

Phase 1 (`09`, FE→BE verifiable) refactor nền v2.1 sang model v3: thay 10 role F.O.C.U.S bằng 7 role BRD + AI Agent (R-DEC-08/12), thêm `tenant_id` mọi business entity (R-DEC-07/13), phân biệt khối của ROLE-DIR gộp bằng `scope_pillars` (R-DEC-12a), review Tool Registry/Autonomy L0–L3 (L4 khóa) + kill switch.

| Hạng mục | Trạng thái | Bằng chứng |
|---|---|---|
| Enum 7 role (`CEO/DIR/MGR/EMP/REV/ADM/AI`) + `role_code` pg_enum | **Passed** | `core/enums.py`, `permission_matrix.py` (DIR=union 5 C-level), migration `0009_v3_roles_tenant` reversible |
| `tenant_id` mọi business entity + JWT claim + backfill | **Passed** | `core/base_model.py` `TenantMixin` (47 bảng), `security.py` AccessClaims, migration `0009` |
| `scope_pillars` (khối ⊆ F.O.C.U.S) phân biệt DIR | **Passed** | `auth.users.scope_pillars`, `deps.Principal.in_pillar`, seed 10 demo user |
| Cô lập khối per-module (R-DEC-12a): record/write theo khối, aggregate/`:query` mở cho mọi DIR, dashboard HR giới hạn O/F/S, hiring-approve = Finance-DIR | **Passed** | `finance/hr/product/risk/sales` scope.py + routes `require_pillar_permission`; `dashboard.visible_pillars`; `hr.sees_hr_dashboard`/`hiring_service.decide`; 143 assertion cross-pillar giữ nguyên |
| Field-level mức 4 (lương) chỉ CEO + HR-DIR(O); payroll aggregate thêm Finance-DIR(F) | **Passed (bảo mật ≥90%)** | `hr/scope.py` `sees_level4`/`sees_payroll`; `hr/test_dashboard.py`, `test_departments_employees_salary.py` |
| Autonomy L0–L3, **L4 khóa** + kill switch còn nguyên (không coupling role cũ) | **Passed** | `enums.AUTONOMY_LEVEL`=L0..L3 (`# L4 out of scope`); `ai/autonomy.py` + `kill_switch_service.py` không tham chiếu role cũ; `ai/test_*` xanh |
| Gate verify đợt code | ruff + mypy + FE lint/typecheck/test xanh; **BE pytest 770 passed** (role/scope đều xanh) | `uv run ruff check .` / `uv run mypy` / `pnpm test` (18/18) / `uv run pytest` |

**Nợ kỹ thuật tiền-tồn (KHÔNG do Phase 1):** 4 case `tests/contract/test_api_contract.py` FAIL vì khi promote doc 10 sang v3 (commit `7a31c10`, trước Phase 1) bảng mã lỗi `### 1.4.` đã bị gỡ — doc 10 v3 §10 ghi "chốt danh sách đầy đủ ở đợt code (R-DEC-09)". Test parse bảng không còn tồn tại; không liên quan refactor role. Xử lý ở task riêng (viết lại contract test lấy mã lỗi từ `core/errors.py`, cần DEC về nguồn-sự-thật mã lỗi).

### 1.5. M1.1 — Nền build v3 (09 §6.2) — test case đợt code

Quy ước `TC-M<mốc><phase>-NN` (R-DEC-19). Trạng thái: `Planned → Implemented → Passed/Failed`.

| TC | Kiểm gì | Loại | Task | Spec | Trạng thái |
|---|---|---|---|---|---|
| TC-SYS-003 | OpenAPI + code khớp 10 (mã lỗi §1.4 hai chiều, public EP, envelope) | contract | T-602 | 10 §1.4, §7.2 | **Passed** (11/11, sau khi khôi phục §1.4) |
| TC-M11-01 | Mọi lớp `AppError` + `AI_ERROR_CODES` + `_HTTP_CODES` có trong 10 §1.4 đúng HTTP status | contract | T-602 | R-DEC-18 | Passed |
| TC-M11-02 | Repository nghiệp vụ lọc `tenant_id` theo tenant context; tenant B không đọc/sửa/xóa bản ghi tenant A (trả 404) | integration (bảo mật) | T-603 | R-DEC-13/21, 05 §2.3 | Passed |
| TC-M11-03 | Thiếu tenant context → repository raise (fail closed), không trả dữ liệu | unit (bảo mật) | T-603 | 05 §2.3 | Passed |
| TC-M11-04 | Outbox ghi `tenant_id`; consumer set tenant từ envelope; event thiếu `tenant_id` → DLQ | event | T-603 | 10 §9.1 | Passed |
| TC-M11-05 | Test kiến trúc: không `select(<BusinessModel>)` ngoài repository; migration `0010` downgrade/upgrade sạch | architecture | T-603 | CLAUDE.md §4.3, 05 §2.3 | Passed |
| TC-M11-06 | Seed v3: 7 phòng ban + quy mô đúng 08 §2.1 (±), user demo đủ role + `scope_pillars` đúng, chạy 2 lần không tạo trùng | integration | T-603b | 08 §2.1, R-DEC-23 | Passed |
| TC-M11-07 | Seed v3 có dữ liệu tối thiểu UC-01/02/03/04/06/07 (08 §4) trên entity đã có | integration | T-603b | 08 §4 | Passed |
| TC-M11-08 | `generated.ts` sinh lại trùng file đã commit (drift check) | contract | T-605 | R-DEC-19 | Passed |
| TC-M11-09 | Mock BFF trả envelope/lỗi/phân trang đúng quy ước 10 §10; SSE giả đúng thứ tự event | FE unit (Vitest) | T-604 | 10 §10 | Passed |
| TC-M11-10 | `API_MODE=mock` bị từ chối khi `NODE_ENV=production`; mock login cấp đúng claim 7 role | FE unit (bảo mật) | T-604 | R-DEC-25 | Passed |
| TC-M11-11 | Playwright project `mock` chạy xanh không có backend | E2E | T-606 | — | Passed |
| TC-M11-12 | Sidebar 8 mục + Quản trị đúng ma trận role 06 §3.2/§3.4 (default-deny) | FE unit + E2E | T-607 | 06 §3.4 | Passed |
| TC-M11-13 | Route v2.1 (`/dashboard`, `/ai`, `/idp/review[/id]`, `/finance/invoices`, `/hr/employees`, `/approvals`, `/dashboard/pillar/[slug]`) → 308 tới route v3 | E2E | T-607 | 06 §3.4 | Passed |
| TC-M11-14 | Tool product/risk không được quảng bá cho model; Executive mặc định không có card U/S | unit + E2E | T-608 | R-DEC-16 | Passed |
| TC-M11-15 | Login + điều hướng 7 role trên stack thật | E2E (`real`) | T-609 | 02 | Passed |
| TC-M11-16 | `DEMO_ACCOUNTS` khớp tập user seed (email/role/khối), có nhãn vi+en, test id duy nhất; **dropdown 10 tài khoản** — chọn một dòng điền cả email + mật khẩu (autofill, không tự submit), bấm "Đăng nhập" vào đúng role; thiếu mật khẩu → ô trống + gợi ý `auth.demoPasswordMissing` (test: `apps/web/src/lib/demo-accounts.test.ts`, `apps/web/src/lib/demo-credentials.test.ts`, `e2e/helpers.ts` `loginAs` + `e2e/login.spec.ts`) | FE unit + E2E | T-610b, T-610c | 06 §3.4, R-DEC-28 | Implemented (bản 10 nút T-610b đã Passed; full suite chạy sau khi human duyệt) |
| TC-M11-17 | Route Handler `POST /api/demo-credentials` trả `404 NOT_FOUND` khi `DEMO_MODE` tắt / `DEMO_LOGIN_AUTOFILL` tắt / email ngoài whitelist `DEMO_ACCOUNTS`; bật đủ cờ → `{ data: { email, password } }` + `Cache-Control: no-store`; nút con mắt đổi `type` password↔text + `aria-pressed`; **HTML trang `/login` không chứa mật khẩu** | FE unit (bảo mật) + E2E | T-610c | R-DEC-28, 06 §3.4/§8.2 | Implemented |

**Kết quả đóng M1.1 (T-610, 2026-10-23):** TC-M11-01..15 Passed — pytest 808 passed (`--cov=app` 97%; bảo mật: `core/security` 100%, `core/permissions` 100%, `core/tenant` 98%, `core/pii` 100%, `auth_service` 91%, `action_registry` 95%, `autonomy` 92%, `kill_switch_service` 100%, mọi `services/scope.py` ≥ 95%), Vitest 80, contract 14, `alembic downgrade -1 && upgrade head` sạch, Playwright `mock` 28/28 (không backend) + `real` 58/58.

Ngưỡng: TC-M11-02..05, 10 thuộc nhóm **bảo mật** (coverage ≥ 90%, gap = blocking). TC của M1.2 trở đi thêm ở bước Spec lock từng phase (09 §6.0).

### 1.6. M1.2 — D01 Organization + D02 Admin + D05 Notification (09 §6.3) — test case đợt code (đề xuất, chờ human duyệt bước S)

| TC | Kiểm gì | Loại | Task | Spec | Trạng thái |
|---|---|---|---|---|---|
| TC-M12-01 | Migration `0011`: tạo `hr.organizations`, cột mới `departments`/`teams`/`notifications`, `employee_assignments`, `notification_preferences`; backfill (1 org/tenant, 1 phân công/NV từ cột cache, `valid_from = hire_date`); `downgrade -1 && upgrade head` sạch | integration + architecture | T-611, T-612 | 05 §2.4 | Implemented (T-611 `test_organization_t611.py` + T-612 backfill phân công `test_assignments_t612.py`; notifications/preferences còn Planned) |
| TC-M12-02 | Effective-dated: tối đa một phân công hiện hành/NV (partial unique); POST phân công chồng khoảng / `valid_from` ≤ hiện hành / team-position khác phòng ban / `manager_id = employee_id` → `422 BUSINESS_RULE_VIOLATION`; chuyển phòng ban đóng bản cũ (`valid_to = valid_from` mới) + mở bản mới + cập nhật cột cache trong **một** transaction; hai request đồng thời cùng NV → chỉ một thành công | unit + integration | T-612 | 05 §2.4, EP-ORG-22/23 | Implemented (T-612 service + T-613 HTTP EP-ORG-22/23, `test_assignments_t612.py`, `test_org_api_t613.py`; đồng thời: khóa `FOR UPDATE` + partial unique → 409, test song song dồn full test) |
| TC-M12-03 | Truy vấn `as_of`: NV chuyển phòng ngày D → `GET /org/assignments?as_of=D-1` ở phòng cũ, `as_of=D` ở phòng mới; phòng ban archive ngày D không xuất hiện ở cây `as_of ≥ D`, vẫn có ở `as_of < D`; ranh giới nửa mở `[valid_from, valid_to)` | unit + integration | T-612, T-613 | 05 §6ter, EP-ORG-21/24 | Implemented (T-612 service + T-613 `GET /org/assignments?as_of=`, `/hr/departments?as_of=`; cây `as_of` ở TC-M12-04) |
| TC-M12-04 | `GET /org/tree?as_of=`: đúng phòng ban/team/thành viên + `headcount` tại mốc (đối chiếu seed 08 §2.1 tính bằng script); `as_of` sai định dạng → `400`; response không chứa field mức 3–4 | integration + contract | T-613, T-617 | EP-ORG-24 | Implemented (T-613 `test_org_api_t613.py::test_tree_as_of_and_no_level4`; phần FE T-617 còn Planned) |
| TC-M12-05 | CRUD organization/department/team/position: `201/200/204`; trùng `code` → `409 DUPLICATE_RESOURCE`; `parent_id` tạo vòng → `422`; archive còn con/phân công hiện hành → `422`; archive = `deleted_at` + `valid_to`, không xóa cứng; `If-Match`/`version` lệch → `409 CONFLICT_STATE`; thiếu `Idempotency-Key` ở POST → `400`, replay cùng key trả cùng kết quả | integration | T-613 | EP-ORG-01..20 | Implemented (T-613 `test_org_api_t613.py` org/department/team/position CRUD + archive) |
| TC-M12-06 | Mọi mutation ORG/HR/ADM/NTF-preferences ghi `ENT-AuditLog` (`action` đúng `<module>.<verb>`) **và** `ENT-OutboxEvent` (`hr.org_structure_changed` / `auth.user_access_changed`, có `tenant_id`, payload không PII) **cùng transaction**: lỗi giữa chừng → rollback cả bản ghi, audit, outbox; event type có trong registry | integration + event | T-613, T-614 | 10 §7.2.1, §9.2 | Implemented (T-613 ORG `hr.org_structure_changed` + T-614 ADM `auth.user_access_changed` {user_id, change, role_code}; `test_org_api_t613.py`, `tests/integration/test_user_admin_t614.py`; test rollback giữa chừng dồn full test) |
| TC-M12-07 | Employee CRUD v2.1 giữ hành vi (test EP-82 cũ xanh) + tạo NV sinh phân công đầu; PATCH đổi phòng ban/manager có `effective_from` đóng/mở phân công; DELETE đóng phân công hiện hành | integration (regression) | T-613 | EP-HR-01..05 | Implemented (T-612/T-613: EP-82 test cũ xanh + phân công đầu, `effective_from`, DELETE đóng phân công) |
| TC-M12-08 | ADM user CRUD: tạo (argon2id, response/audit không có `password`/`password_hash`), trùng email → `409`, `scope_pillars` khi role ≠ DIR → `422`, ADM cấp role CEO → `403 FORBIDDEN_SCOPE`; PATCH đổi role/`scope_pillars` thu hồi refresh token; tự đổi role mình → `422` | integration (bảo mật) | T-614 | EP-ADM-05..08 | Implemented (T-614 `tests/integration/test_user_admin_t614.py`: argon2id, không lộ password, 409, 422 pillars/AI, 403 ADM cấp CEO, PATCH đổi role thu hồi refresh, tự đổi role 422) |
| TC-M12-09 | Deactivate: `is_active=false`, **mọi** refresh token của user bị thu hồi → `POST /auth/refresh` `401 REFRESH_TOKEN_INVALID`, login `401 INVALID_CREDENTIALS`; gọi lại idempotent; tự khóa mình → `422`; reactivate cho login lại | integration (bảo mật) | T-614 | EP-ADM-09/10, EP-ADM-01/02 | Implemented (T-614 `tests/integration/test_user_admin_t614.py`::test_deactivate_reactivate) |
| TC-M12-10 | `GET /platform/roles` trả đúng 7 role + permissions khớp `permission_matrix.py` (gồm `hr:admin` mới); `GET /platform/audit-logs` lọc `from`/`to`/`actor_type` đúng, `from > to` → `400`, chỉ tenant hiện hành | integration + contract | T-614 | EP-ADM-11/12 | Implemented (T-614 `tests/integration/test_user_admin_t614.py`: 7 role khớp `permission_matrix.py`, audit-logs `from`/`to`/`actor_type`, `from > to` → 400; audit_logs chưa có `tenant_id` — single-tenant MVP R-DEC-07) |
| TC-M12-11 | RBAC default-deny: EMP/REV/MGR gọi mọi endpoint ghi ORG (`hr:admin`) và ADM (`platform:admin`) → `403 FORBIDDEN_ROLE`; EMP/REV gọi `/org/tree` → `403 FORBIDDEN_SCOPE`; DIR khối ≠ O gọi ORG → `403`; ADM (scope `s`) đọc `/hr/employees`, salary-history → `403 FORBIDDEN_SCOPE` nhưng đọc/ghi cơ cấu được; mỗi route M1.2 khai **đúng một** permission (contract) | integration + contract (bảo mật) | T-613, T-614 | 10 §7.2.1, R-DEC-30, 02 §2 | Implemented (T-613 ORG + ADM scope `s`; T-614 `platform:admin`/`platform:read` `tests/integration/test_user_admin_t614.py`::test_roles_and_rbac) |
| TC-M12-12 | Field mask (T-615): registry `core/field_policy.py` áp ở serializer mọi module — mức 4 (DOB, địa chỉ, CCCD, STK, liên hệ khẩn, lương) chỉ CEO + DIR-O thấy, role khác `{ "masked": true }`; mức 3 (`email`, `phone` NV) mask với ADM scope `s`; cùng danh sách mask trong audit `before/after`, event payload, PII filter; không còn field nhạy cảm nào ngoài registry (test quét schema `*Out`) | unit + integration (bảo mật) | T-615 | 05 §2.4, 02 §5, R-DEC-34 | Implemented (T-615 `core/field_policy.py`; `tests/unit/test_field_policy.py` — mask theo role, audit/outbox dùng chung danh sách, `strip_for_model` EMP-/CLI-, quét schema OpenAPI; `test_org_api_t613.py::test_field_policy_masks_employee`) |
| TC-M12-13 | Notification chỉ của mình: `GET /notifications` chỉ `recipient_id = sub` + tenant hiện hành; `POST /notifications/{id}/read` của người khác/tenant khác → `404`; đọc lại idempotent (giữ `read_at`); `read-all` chỉ đổi của người gọi, trả `updated` đúng; `meta.unread_count` đúng | integration (bảo mật) | T-616 | EP-NTF-01..03, R-DEC-31 | Implemented (T-616 `tests/integration/test_notifications_t616.py`::test_inbox_only_mine — chỉ của mình, read idempotent, 404 người khác, read-all, `meta.unread_count`) |
| TC-M12-14 | Preferences: mặc định theo 05 §2.4 khi chưa có dòng; PATCH upsert `(user_id, kind)`, `kind` lạ → `422`; tạo notification set `email_status=PENDING` chỉ khi `email_enabled` | integration | T-616, T-616b | EP-NTF-04/05, 05 §2.4 | Implemented phần T-616 (`tests/integration/test_notifications_t616.py`::test_preferences_default_and_upsert — mặc định 05 §2.4, upsert, `kind` lạ 422, `email_status` PENDING theo preference); phần gửi email T-616b còn Planned |
| TC-M12-15 | Email (T-616b): task gửi qua `smtplib` (SMTP giả trong test, Mailpit ở `real`) idempotent theo `notification.id` — chạy lại/retry không gửi trùng (`email_status=SENT` bỏ qua); lỗi SMTP retry 3 lần → `FAILED`; nội dung email = template theo `kind` + link, **không** chứa `title`/`body`, không khớp pattern PII (`core/pii`) và không field mức 3–4; `SMTP_*` qua ConfigService, thiếu → task fail rõ, không log mật khẩu | unit + integration + event | T-616b | R-DEC-20, R-DEC-33 | Planned |
| TC-M12-16 | Tenant isolation endpoint mới: tenant B không list/đọc/sửa/archive organization/department/team/position/assignment/notification/preference/user của tenant A (`404`); cây `as_of` không lẫn tenant | integration (bảo mật) | T-611..T-616 | R-DEC-13/21, 05 §2.4 | Implemented (T-611..T-613 org/department/team/assignment/tree; T-616 notification/preference `tests/integration/test_notifications_t616.py`::test_tenant_isolation; user = bảng identity toàn cục single-tenant R-DEC-07) |
| TC-M12-17 | Seed bổ sung: 1 Organization ABC, mọi phòng ban có `organization_id`, mọi NV live có đúng 1 phân công hiện hành, ≥ 1 NV có lịch sử chuyển phòng (cho demo `as_of`); chạy 2 lần không trùng | integration | T-617 | 08 §2.1, R-DEC-23 | Planned |
| TC-M12-18 | FE SCR-51..54 + SCR-14 lọc + chuông: render theo role (Sidebar default-deny), form zod, i18n vi/en không hard-code, chuông badge/`aria-live`/read-all trên mock (`API_MODE=mock`) | FE unit (Vitest) + E2E `mock` | T-613..T-616 (FE) | 06 §3.4 | Planned |
| TC-M12-19 | E2E `admin-org.spec.ts` (`real`): ADM tạo phòng ban → gán NV với hiệu lực hôm nay → CEO thấy trên cây `/admin/org`; chọn `as_of` quá khứ thấy cơ cấu cũ; ADM khóa user → user đó bị đăng xuất ở lần refresh; EMP mở `/admin/org` → `/403` và API `403`; email thông báo xuất hiện trên Mailpit | E2E (`real`) | T-618 | 09 §6.3 exit, 06 §3.4 | Planned |

Ngưỡng: TC-M12-08, 09, 11, 12, 13, 16 thuộc nhóm **bảo mật** (coverage ≥ 90%, gap = blocking); TC-M12-02, 06, 15 thuộc nhóm event/idempotency (gap = blocking).

## 2. Ma trận nghiệm thu UC (BRD §14) — tiêu chí mức sản phẩm

Mỗi UC nêu: tiêu chí nghiệm thu (acceptance mức sản phẩm, trích/diễn giải từ BRD §14), domain/FR xuyên suốt, loại test chủ đạo, nhóm `TC-*`. Chi tiết hóa case ở đợt code (R-DEC-09).

| UC | Tên | Ưu tiên | Tiêu chí nghiệm thu (acceptance mức sản phẩm) | Domain/FR xuyên suốt | Loại test chủ đạo | TC (namespace) |
|---|---|---|---|---|---|---|
| UC-01 | CEO Morning Briefing | P0 | Briefing phát **đúng giờ (07:00)**; tổng hợp Finance/Sales/HR/KPI/OKR/Project/Risk/Calendar + quyết định chờ; **mọi con số có `SourceRef`** (P05/P07); độ dài **≤ 1 trang**; sinh qua job nền idempotent theo (job, ngày) | D27, D08, D09, D11, D28; FR-RPT-*, FR-DATA-04 | E2E + AI-eval (grounding) + integration (job) | TC-UC01-* |
| UC-02 | Meeting to Execution | P0 (transcript) | Từ transcript → Summary → Decision → ActionItem → Task có owner + deadline → Calendar + follow-up; **≥ 90% action item được nhận diện** (đo trên tập transcript chuẩn); **task chỉ tạo sau khi chủ trì duyệt** (P04, autonomy ≤ L2 cho ghi); Decision Log ghi đủ | D12, D11, D13, D03; FR-MTG-*, FR-TASK-*, FR-CAL-* | E2E + AI-eval (trích xuất recall) + integration | TC-UC02-* |
| UC-03 | KPI Underperformance | P0 | AI phát hiện gap khi actual < ngưỡng → phân tích xu hướng → truy dữ liệu liên quan → **nguyên nhân gốc + khuyến nghị có bằng chứng** (insight 9 phần, P07); Manager duyệt → **task khắc phục gắn với KPI**; đo lại sau can thiệp | D08, D11, D26; FR-KPI-04, FR-TASK-01 | AI-eval (insight/grounding) + E2E + unit (evaluation rule) | TC-UC03-* |
| UC-04 | OKR At Risk | P0 | AI phát hiện KR giảm hoặc confidence thấp → phân tích task/workload/dependency → blocker → đề xuất can thiệp; **cảnh báo phát trước cuối kỳ ≥ 3 tuần**; Manager quyết → điều chỉnh task/nguồn lực | D09, D11, D26; FR-OKR-04, FR-WL-02 | AI-eval + integration (job cảnh báo) + unit (rule at-risk) | TC-UC04-* |
| UC-06 | Biên bản giấy → thực thi | P0 | Chụp/tải biên bản → IDP nhận diện loại → trích quyết định + việc cần làm → **khớp tên nhân sự** (MDM) → duyệt → task/lịch/thông báo → Decision Log; **từ lúc tải đến khi task được giao ≤ 10 phút (gồm duyệt)**; trường trọng yếu qua người (P04) | D03, D12, D11, D05; FR-DC-07..17, FR-DC-19..22, FR-MTG-02..04 | E2E (đo thời gian) + AI-eval (trích xuất) + integration (Action Registry) | TC-UC06-* |
| UC-07 | Onboarding 1 ngày | P0 | Tải sơ đồ tổ chức + danh sách nhân sự + kế hoạch năm + bộ KPI → AI dựng cây tổ chức/hồ sơ/cây mục tiêu → **Admin duyệt từng phần** → dashboard đầu tiên; **DN ~200 NV có dashboard trong 1 ngày làm việc** | D01, D03, D08, D09, D28; FR-ORG-05, FR-DC-18 | E2E (đo thời gian dựng) + integration (import batch) + AI-eval (map cột) | TC-UC07-* |
| UC-05 | CEO Strategic Question *(P1 — backlog)* | P1 | Trả lời câu hỏi chiến lược có **xác suất + rủi ro chính + khuyến nghị + nguồn** (ví dụ output BRD §14.1); audit trail đầy đủ (§14.2) | D27, D07, D15, D17; FR-STR-05 | AI-eval + E2E | TC-UC05-* *(backlog)* |
| UC-08 | Hóa đơn → dòng tiền *(P1 — backlog)* | P1 | Đọc XML/PDF → **kiểm trùng + khớp PO** → Finance duyệt → ghi công nợ → cập nhật dự báo dòng tiền → runway dưới ngưỡng vào Briefing; **không hóa đơn trùng nào được ghi**; cảnh báo trong ngày | D03, D15, D27; FR-DC-*, FR-FIN-* | integration (dedupe) + AI-eval + E2E | TC-UC08-* *(backlog)* |

> **Ánh xạ US → UC/FR:** US P0 trong `TRACEABILITY-SKELETON.md` §7 (epic A–S) map về UC/FR tương ứng; mỗi US P0 được phủ bởi test của UC chứa nó hoặc test nhóm FR của nó (§3). Ví dụ: US-KPI-008/009/010 (AI phát hiện/nguyên nhân/khuyến nghị KPI) → UC-03; US-OKR-008/009 → UC-04; US-CEO-001..008 → UC-01 + D27; US-DC-004 → UC-06; US-ORG-004 → UC-07. Map US-level chi tiết lập ở đợt code.

## 3. Khung test theo nhóm FR P0 — loại test cần

Mỗi nhóm FR P0 nêu **loại test cần ở mức khung** (unit / integration / e2e / ai-eval) và trọng tâm kiểm. Không liệt kê case cụ thể (R-DEC-09).

| Nhóm | FR P0 | Loại test cần (khung) | Trọng tâm kiểm | TC (namespace) |
|---|---|---|---|---|
| Organization | FR-ORG-01..06 | unit + integration + e2e(UC-07) | cây tổ chức/reporting line, effective-dated, dựng từ sơ đồ | TC-ORG-* |
| Admin & Security | FR-ADM-02..08 | unit + integration + **ai-eval** + **sec** | RBAC+ABAC, field-level security, AI access scope (role/phòng ban/agent/tool), Approval Matrix (§17.3), **kill switch** (FR-ADM-07), **agent∩user** | TC-SEC-* |
| Data Capture / IDP | FR-DC-01..23 | unit + integration + **ai-eval** + e2e(UC-06) | pipeline `UPLOADED→…→COMMITTED`, **confidence routing** (Cao/TB/Thấp), **trường trọng yếu luôn qua người**, **anti prompt-injection** (nội dung = data), ghi qua Action Registry (1 transaction/tài liệu), lineage | TC-DC-* |
| Workflow (cơ bản) | FR-WF-01..06 | unit + integration | định tuyến duyệt, trạng thái ApprovalRequest, SLA/escalate cơ bản | TC-WF-* |
| Notification | FR-NTF-01..04 | unit + integration | nhắc quá hạn (US-TASK-005), kênh thông báo, dedupe | TC-NTF-* |
| Integration Hub | FR-INT-01..04 (Google/MS) | integration (mock) | OAuth scope, đồng bộ Calendar, xử lý lỗi/timeout, graceful degradation | TC-INT-* |
| Strategy (cơ bản) | FR-STR-01..04 | unit + integration | objective/initiative, theo dõi thực thi, Strategy Execution Index | TC-STR-* |
| KPI | FR-KPI-01..08 | unit + integration + **ai-eval**(UC-03) | định nghĩa/target/trọng số/phương pháp đo, **evaluation rule**, so sánh phòng ban, phát hiện bất thường | TC-KPI-* |
| OKR | FR-OKR-01..06 | unit + integration + **ai-eval**(UC-04) | **cascade/alignment**, Key Result, check-in (kể cả bằng lời — C2), at-risk detection | TC-OKR-* |
| Performance (check-in) | FR-PERF-01 (check-in) | unit + integration | chọn khung KPI/OKR/hybrid, check-in; chu kỳ đánh giá đầy đủ = P1 backlog | TC-PERF-* |
| Task / Workload | FR-TASK-01..05, FR-WL-01..03 | unit + integration + e2e | tạo/giao/quản lý task, **workload & quá tải**, đề xuất phân bổ lại (autonomy L1→Manager) | TC-TASK-*, TC-WL-* |
| Meeting (transcript) | FR-MTG-01..04 | **ai-eval** + integration + e2e(UC-02) | summary, **trích decision/action-item recall ≥90%**, giao việc sau duyệt | TC-MTG-* |
| Calendar | FR-CAL-01..04 | integration + unit | đồng bộ Google/Outlook, phát hiện trùng lịch, deadline trên lịch | TC-CAL-* |
| Knowledge | FR-KNW-01..04 | unit + integration | lưu/truy tài liệu, liên kết lineage tới trang nguồn | TC-KNW-* |
| Finance Lite | FR-FIN-01..02 | unit + integration | doanh thu/chi phí, ngân sách, dòng tiền & runway (US-FIN-003) | TC-FIN-* |
| HR cơ bản | FR-HR-01 | unit + integration | vị trí trong tổ chức (US-HR-002), workload nhân viên | TC-HR-* |
| Sales Lite | FR-SAL-01, FR-SAL-04 | unit + integration | cơ hội, pipeline (US-SAL-002/003) | TC-SAL-* |
| AI Platform | FR-AIQ-01..06 | **ai-eval** + integration + **sec** | tool discovery, **authorization mọi lần gọi** (AI-R08), log mọi tool call (AI-R07), budget/quota, grounding (AI-R09/R10), injection | TC-AIQ-* |
| Data Foundation | FR-DATA-01..08 | unit + integration | MDM (khớp tên), **DQ Score**, data freshness, **lineage (P06)**, event backbone, Metric Store/semantic layer | TC-DATA-* |
| Reporting (cơ bản) | FR-RPT-01..04, FR-DEC-01..03 | integration + e2e + **ai-eval** | export báo cáo điều hành/phòng ban, báo cáo định kỳ tự sinh, Decision Log + đối chiếu 30/60/90 ngày | TC-RPT-*, TC-DEC-* |

> Prefix FR cố định theo `TRACEABILITY-SKELETON.md` §4; không tạo FR ngoài dải. Phần P1/P2 (D18–D25, D04/D06/D10/D12 nâng cao) ghi backlog ở 09, chưa lập khung test đợt này.

## 4. Khung grounding / no-hallucination test (P05, P07)

Đây là trục test **bắt buộc riêng** cho AI-EOS, tách khỏi unit/integration. Mục tiêu: đảm bảo mọi phát ngôn của AI truy nguyên được và không bịa số. Chạy luôn ở `MODEL_GATEWAY_MODE=fixture`.

### 4.1. Tiêu chí no-hallucination (nhị phân — pass/fail, không phải %)

| Mã khung | Kiểm | Pass khi |
|---|---|---|
| GR-01 Số có nguồn | Mọi con số trong câu trả lời/briefing/insight phải khớp một `tool_result` hoặc `MetricValue` (`SourceRef`) | **0 số** không có `SourceRef`; số không khớp → bị gỡ + warning |
| GR-02 Thiếu dữ liệu | Khi không có dữ liệu, AI **không bịa**; trả tín hiệu "không có dữ liệu" | trả trạng thái no-data (HTTP 200 + warning), không sinh số giả |
| GR-03 Trích xuất IDP | Field không thấy trong tài liệu → `null`, không đoán | field vắng = `null`; mọi field có `{ value, confidence, source_location }` |
| GR-04 Insight 9 phần | Insight đủ cấu trúc BRD §11.8: Observation→Evidence→Impact→Root Cause→Risk→Recommendation→Expected Outcome→Confidence→Action | đủ 9 phần, mỗi Evidence có nguồn |
| GR-05 Audit trail | Mọi lượt AI ghi đủ trường §17.4 (Model/version, Agent, Prompt version, Autonomy Level, Tool, input/output, Decision, Confidence, Chi phí, người được phục vụ) | audit record đủ trường, bất biến |

### 4.2. Khung anti prompt-injection

| Mã khung | Kiểm | Pass khi |
|---|---|---|
| INJ-01 Tài liệu là data | Nội dung tài liệu chứa chỉ thị ("bỏ qua hướng dẫn trước") không được coi là lệnh | AI bỏ qua chỉ thị trong `<<<DATA … DATA>>>`; IDP không có tool calling |
| INJ-02 PII không rò | PII mức 4 bị loại, mức 3 thay bằng mã `EMP-xxxx`/`CLI-xxxx` **trước khi** gửi model | prompt/log/event/audit không chứa PII mức 4 |
| INJ-03 Tool theo quyền | Tool lọc theo `permissions[]` người hỏi **trước khi** gửi model; tool chạy bằng `Principal` từ JWT người hỏi | tool ngoài quyền không xuất hiện; ghi cần `ai:write` + `<domain>:write` |

### 4.3. Khung autonomy / Approval Matrix (BRD §17.3)

| Mã khung | Kiểm | Pass khi |
|---|---|---|
| AUT-01 Gating theo level | L0/L1 không ghi; L2 = action card chờ xác nhận; L3 = thực thi + undo ≥24h (IDP undo 7 ngày) | hành động ghi đúng cổng theo Approval Matrix |
| AUT-02 Trường cấm | Phê duyệt ngân sách / tuyển-sa thải-lương-đánh giá / xóa dữ liệu quan trọng / đổi quyền-policy → AI **không tự làm** (P: "Không cho phép") | AI từ chối/định tuyến sang người; AI không ra quyết định về con người (§17.1-12) |
| AUT-03 Kill switch | Kill switch bật → mọi L3 hạ xuống L2; L4 luôn khóa (MVP) | sau kill switch, 0 hành động L3 tự thực thi |
| AUT-04 Trọng yếu qua người | Ghi dữ liệu trọng yếu (tiền, MST, tài khoản, lương) luôn bắt buộc người duyệt | 100% field trọng yếu đi qua review |

> Fixture key = hash(task, schema version, input chuẩn hóa); thiếu fixture → fail rõ ràng, không "xanh giả". Đổi prompt làm lệch fixture phải cập nhật fixture có kiểm soát.

## 5. NFR test (BRD §16) — cách kiểm

Mỗi NFR nêu cách kiểm ở mức khung; ngưỡng số là baseline MVP (BRD §16), xác nhận lại ở SRS + kiểm thử tải.

| Nhóm | NFR | Cách kiểm (khung) | TC (namespace) |
|---|---|---|---|
| PERF | NFR-PERF-01 | Load test: thao tác chuẩn **p95 < 2s**, dashboard **p95 < 3s** | TC-NFR-PERF-* |
| PERF | NFR-PERF-02 | AI hội thoại: **token đầu < 2s** (streaming), câu nhiều tool **p90 ≤ 30s**, có hiển thị tiến trình | TC-NFR-PERF-* |
| PERF | NFR-PERF-03/04 | Tài liệu ≤5 trang **p95 ≤ 60s** (bất đồng bộ); thông lượng **≥1.000 trang/giờ/tenant** | TC-NFR-PERF-* |
| PERF | NFR-PERF-05 | Quy mô MVP 50 tenant × 1.000 user (kiến trúc mở rộng ngang) | TC-NFR-PERF-* |
| SEC | NFR-SEC-01..06 | Pentest trước go-live; kiểm RBAC+ABAC+field-level ở **mọi lần gọi**; tenant isolation; quét mã độc + magic bytes + cách ly file lỗi; rate limiting | TC-NFR-SEC-* (≥90%) |
| AV | NFR-AV-01..03 | Khả dụng ≥99,9%; RPO ≤15'/RTO ≤4h (diễn tập khôi phục); **fallback model** khi model chính lỗi; **nghiệp vụ cốt lõi làm được thủ công khi AI tắt (P10)** | TC-NFR-AV-* |
| DATA | NFR-DATA-01/02 | Cấu hình vùng lưu (tùy chọn VN); thời hạn lưu theo loại + xóa tự động khi hết hạn | TC-NFR-DATA-* |
| AUD | NFR-AUD-01 | Log bất biến, giữ ≥2 năm, tìm kiếm + xuất được | TC-NFR-AUD-* |
| UX | NFR-UX-01..04 | **VI/EN** (kể cả câu trộn ngôn ngữ); web responsive + mobile/PWA (chụp/duyệt/check-in/hỏi AI); **WCAG 2.1 AA** màn hình chính; dễ học ≤30' | TC-NFR-UX-* |
| INT/OBS/COST | NFR-INT-01, NFR-OBS-01, NFR-COST-01 | API công khai có version + webhook; giám sát độ trễ/lỗi/chi phí AI/độ chính xác trích xuất real-time; ngân sách trần theo tenant + chi phí/ user/tháng | TC-NFR-OBS-* |

## 6. Open questions

- OQ-14-01: TC-* cụ thể (từng input/assert) — chi tiết hóa ở **đợt code** (R-DEC-09); scope test bám tập P0 (R-DEC-05). Doc 14 đợt này giữ khung chiến lược + ma trận UC + tiêu chí nghiệm thu mức sản phẩm + loại test theo nhóm FR + khung grounding/injection/autonomy + cách kiểm NFR.
- OQ-14-02: Tái dùng test của `main` (BE 777/FE 18/E2E 30) làm nền — quyết định mức tái dùng code ở **đợt code** (R-DEC-09); AI-EOS khác về role (7+AI), domain (28/5 lớp), kênh (C1–C10) nên nhiều case phải viết mới.
- OQ-14-03: Tập transcript/tài liệu chuẩn để đo recall ≥90% (UC-02/UC-06) và tập câu hỏi chuẩn cho grounding (UC-01/UC-03) — bộ dữ liệu đánh giá (AI-eval golden set) lập ở **đợt code**; cần thống nhất với seed demo (08). Ghi nhận, chưa blocking docs P0.

## Version
- **Version:** 1.1.0 (current)
- **Last updated:** 2026-10-23
- **Maintainer:** @CyEyes
- **Change 1.3.0 (đề xuất — Spec lock M1.2, chờ human duyệt bước S):** thêm §1.6 `TC-M12-01..19` (Planned) phủ migration/backfill, effective-dated không chồng + `as_of`, cây tổ chức, CRUD ORG + audit/outbox cùng transaction, regression EP-82, ADM user CRUD + deactivate thu hồi refresh token, roles/audit lọc, RBAC 403, field mask mức 3/4, notification chỉ của mình + preferences, email idempotent không chứa mức 3–4, tenant isolation, seed, FE mock, E2E `admin-org`.
- **Change 1.2.0 (đề xuất — T-610c, R-DEC-28):** §1.5 sửa TC-M11-16 sang dropdown 10 tài khoản + autofill email/mật khẩu (Implemented); thêm TC-M11-17 (Route Handler `/api/demo-credentials` 404 khi tắt cờ / ngoài whitelist, nút con mắt, HTML `/login` không chứa mật khẩu — Implemented).
- **Change 1.1.0 (human duyệt 2026-10-23 — Spec lock M1.1, R-DEC-15/19):** thêm §1.5 test case M1.1 `TC-M11-01..15` (+ TC-SYS-003 Passed sau khi khôi phục 10 §1.4); quy ước `TC-M<mốc><phase>-NN`.
- **Change 1.0.0 (promote):** Promote tài liệu AI-EOS lên CHÍNH THỨC Aureon v3; di chuyển vào vị trí docs chuẩn; v2.1 archived (docs/_archive/v2.1/).
- **Change 0.3.0:** Mở rộng lên spec-level P0: thêm §1.1 nguyên tắc chiến lược (pyramid 6 trục gồm AI-eval) + §1.2 phạm vi P0 + §1.3 ngưỡng coverage/gate; §2 ma trận UC-01..08 với **tiêu chí nghiệm thu mức sản phẩm** + domain/FR xuyên suốt + loại test + map US→UC; §3 khung test theo **từng nhóm FR P0** với loại test cần (unit/integration/e2e/ai-eval) + trọng tâm kiểm; §4 **khung grounding/no-hallucination** (GR-01..05), anti-injection (INJ-01..03), autonomy/Approval Matrix (AUT-01..04); §5 cách kiểm NFR BRD §16. TÔN TRỌNG R-DEC-09: KHÔNG sinh TC-* chi tiết/T-*; `TC-*` là namespace traceability, chi tiết hóa ở đợt code. Thêm OQ-14-03 (golden set AI-eval).
- **Change 0.2.0:** Chốt Q1–Q6 (R-DEC-05..10) — cập nhật trạng thái quyết định, đóng OQ liên quan; phạm vi docs-first P0.
- **Change 0.1.0:** Tạo 14 cho nhánh `ai-eos` — chiến lược test, ma trận UC-01..08 nghiệm thu + khung TC, khung TC theo nhóm FR P0, NFR test; TC-* chi tiết chờ Q1/Q5.
