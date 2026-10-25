# 05 — Data Model & Data Foundation (Aureon v3 — AI-EOS)

> **Nguồn chuẩn:** `_reference/SOURCE-BRD-v1.1.md` §13 (Data Foundation FR-DATA-01..08, entity §13.2, quan hệ §13.3), §5–§12 (entity theo domain).
> **Phụ thuộc:** 00, 01, 02, 04, `TRACEABILITY-SKELETON.md` §11, §4.1. **Trạng thái:** ✅ current — Aureon v3 (AI-EOS) CHÍNH THỨC. **Ngày:** 2026-10-23 · **Maintainer:** @CyEyes
> Tài liệu chính thức v3, tách từ Aureon v2.1 (nay archived ở `docs/_archive/v2.1/`).

---

## 1. Data Foundation (BRD §13.1, P0)

"One Source of Truth" thành hiện thực khi **mỗi entity có nguồn gốc chỉ định, có owner, có điểm chất lượng, truy ngược được đến tài liệu gốc**. Data Foundation là lớp nền của AI-EOS: nó bảo đảm mọi con số AI đưa ra đều kiểm chứng được (BRD-P05 không bịa số, BRD-P01 mọi con số có nguồn), và là điều kiện của mục tiêu kinh doanh BO-07 (bộ nhớ doanh nghiệp ≥90%), BO-09 (Data Quality ≥90/100) trong `TRACEABILITY-SKELETON.md` §3.

Mỗi FR-DATA dưới đây mô tả hành vi + tiêu chí chấp nhận mức sản phẩm (field-level — tên cột/kiểu/constraint — chốt ở đợt code theo **R-DEC-09**):

| Mã | Yêu cầu | Hành vi & tiêu chí chấp nhận (mức sản phẩm, P0) |
|---|---|---|
| FR-DATA-01 | **Master Data Management (MDM)** | 6 master entity — Employee, Customer, Partner, Vendor, Product, Project — mỗi bản ghi có **nguồn gốc chỉ định** (`source` ∈ {manual, document, integration, ai}) và **data owner** (một người/role chịu trách nhiệm). Hệ thống phát hiện bản ghi nghi trùng theo khóa nghiệp vụ (ví dụ MST/email/mã NV) và đề xuất khử trùng/hợp nhất; hợp nhất là hành động có duyệt, ghi lineage. **Tiêu chí:** không có master entity thiếu owner; mọi lần hợp nhất lưu được bản ghi trước/sau và người quyết. Thuật toán khử trùng cụ thể + khóa trùng chi tiết hóa ở đợt code (R-DEC-09). |
| FR-DATA-02 | **Data Quality Score (DQ Score)** | Mỗi domain có điểm chất lượng tổng hợp từ 4 chiều: **đầy đủ** (completeness), **chính xác** (accuracy), **kịp thời** (timeliness), **nhất quán** (consistency). Ngưỡng cảnh báo < 80/100 (chỉ số Dữ liệu, skeleton §10); AI gắn cảnh báo khi một kết luận dựa trên domain có DQ thấp. **Tiêu chí:** DQ Score hiển thị được per-domain; Briefing/insight nêu rõ khi dữ liệu nền có DQ < ngưỡng. Công thức chi tiết 4 chiều → `METRIC-DQ-*` cấp ở 03. |
| FR-DATA-03 | **Data Freshness** | Mọi chỉ số/metric mang **thời điểm cập nhật cuối** (`last_refreshed_at` mức khái niệm). Nếu quá ngưỡng tươi của domain thì đánh dấu "dữ liệu cũ"; UC-01 Morning Briefing **nêu rõ** dữ liệu nào đã cũ. **Tiêu chí:** không có metric thiếu mốc cập nhật; nhãn độ tươi hiển thị ở ô chỉ số (SOURCE-UIUX U3). Ngưỡng tươi per-domain = cấu hình. |
| FR-DATA-04 | **Data Lineage** | Từ một con số trên dashboard/báo cáo truy ngược được: **bản ghi nghiệp vụ → người/agent nhập → các lần sửa (version) → trang tài liệu gốc**. `ENT-DataLineage` nối Business Record ↔ ExtractedField ↔ SourceDocument/DocumentPage. **Tiêu chí (US-CEO-007 P0):** mọi con số click được mở nguồn ≤ 3 bước tới tài liệu gốc; con số ngoài scope role trả `{ restricted: true, reason }` (đồng bộ 02). Khi nguồn mâu thuẫn → hiển thị cả hai, người chọn, ghi vào lineage (SOURCE-UIUX). |
| FR-DATA-05 | **Event backbone** | Mọi thay đổi nghiệp vụ phát một **domain event** (ví dụ `invoice.created`, `kpi.measured`, `task.overdue`, `document.committed`) để AI quan sát real-time và kích hoạt insight/alert. Event phát **cùng transaction** với ghi dữ liệu (nguyên tắc outbox — hiện thực chốt ở 07/10). **Tiêu chí:** không mất event khi rollback; payload **không chứa PII**; mỗi event có `correlation_id` truy được về request/lineage. Danh mục event đầy đủ ở §7 + 10 §8. |
| FR-DATA-06 | **Metric Store / Semantic layer** | Mỗi chỉ số **định nghĩa một lần** (công thức, nguồn, bộ lọc, owner, đơn vị, hướng tốt/xấu) và dùng chung cho dashboard, báo cáo, AI — tránh "mỗi nơi một công thức". KPI tham chiếu công thức trong Metric Store (BRD §8 "Formula (tham chiếu Metric Store)"). **Tiêu chí:** một chỉ số = một định nghĩa; dashboard, Report và AI tool đọc cùng giá trị; mọi metric có `lineage_url`. Xem §6bis. |
| FR-DATA-07 | **Lịch sử & thời điểm hiệu lực (effective-dated)** | Lưu lịch sử thay đổi của entity quan trọng để trả lời "tại thời điểm X thì sao" (ví dụ cơ cấu tổ chức tại quý trước, KPI target đã đổi). P0 tối thiểu áp cho Organization/cơ cấu (bám FR-ORG-04) và KPITarget; mở rộng chốt ở đợt code. **Tiêu chí:** truy vấn được trạng thái entity theo một mốc thời gian quá khứ. Xem §6ter. |
| FR-DATA-08 | **Xuất dữ liệu** | Doanh nghiệp xuất được **toàn bộ dữ liệu của mình** theo định dạng mở (ví dụ CSV/JSON/Excel) bất kỳ lúc nào — chống khóa nhà cung cấp. **Tiêu chí:** phạm vi xuất tôn trọng RBAC/data scope + mask dữ liệu nhạy cảm theo người yêu cầu; bản xuất kèm metadata nguồn khi có. Định dạng/endpoint cụ thể ở 10 (đợt code). |

## 2. Trường chung mọi bản ghi nghiệp vụ (BRD §13.3)

`tenant_id` (R-DEC-07: 1 tenant cho MVP nhưng có sẵn ở **mọi** business entity để nâng đa tenant sau) · `created_by` (người hoặc agent) · `source` ∈ {manual, document, integration, ai} · `source_document_id` · `data_classification` ∈ {Công khai, Nội bộ, Mật, Tuyệt mật} · `created_at` · `updated_at` · `version`.

> **`source` vs `*_source` (khác `main`):** `main`/DEC-154 đổi `source` → tên có hậu tố (`risk_source`, `data_source`…) để tránh trùng tên cột. Ở Aureon v3 (AI-EOS) giữ `source` theo BRD §13.3; việc có đổi sang quy ước hậu tố của `main` (khi tái dùng code) là **quyết định ở đợt code (R-DEC-09)**.

### 2.1. Data classification per nhóm entity (mức sản phẩm)

`data_classification` ∈ {Công khai, Nội bộ, Mật, Tuyệt mật} (BRD §13.3) quyết định quyền đọc, mask AI/log, và chính sách LLM (đồng bộ 02/07). Gán mặc định theo nhóm; override per-field chốt ở đợt code (R-DEC-09):

| Nhóm entity | Classification mặc định | Ghi chú nghiệp vụ |
|---|---|---|
| Tổ chức (lương, ngày sinh, địa chỉ, CCCD của Employee) | **Tuyệt mật** (trường nhạy cảm) / Nội bộ (phần còn lại) | Trường mức cao chỉ ROLE-CEO/HR phụ trách; mask trong audit, event payload, prompt LLM |
| Tài chính (Revenue, Expense, Invoice, Payment, CashBalance, Budget) | **Mật** | Số tiền là "trường trọng yếu" IDP — luôn qua người duyệt |
| Kinh doanh (Customer, Lead, Opportunity, Contract) | Mật / Nội bộ | Giá trị hợp đồng, MST là trường trọng yếu |
| Rủi ro & tuân thủ (Risk, Finding, Evidence) | **Mật** | Phát hiện/bằng chứng nhạy cảm |
| KPI / OKR / Hiệu suất | Nội bộ | PerformanceReview có phần Mật |
| Sản phẩm & thực thi, Chiến lược, Họp & quyết định, Tri thức | Nội bộ | MeetingTranscript có thể chứa Mật |
| Data Capture, AI, Workflow | Nội bộ | SourceDocument kế thừa classification của nội dung |

> Nguyên tắc classification (đồng bộ CLAUDE.md §2.2): Công khai/Nội bộ → có thể dùng cloud LLM; Mật → LLM local; Tuyệt mật → không đưa vào LLM. Hiện thực chính sách ở 07 (đợt code).

### 2.2. Field-level đợt code — Phase 1 (R-DEC-12, R-DEC-13)

> Chốt ở đợt code (R-DEC-09) khi refactor nền v2.1 → model v3. Áp cho hiện thực SQLAlchemy/Alembic; migration reversible.

**`tenant_id` (R-DEC-13):** `tenant_id UUID NOT NULL`, mặc định một tenant hệ thống cố định ở MVP (single-tenant), có ở **mọi business entity** (thêm qua `TenantMixin`, gộp vào `BusinessModel`); index theo `tenant_id`. Repository lọc `tenant_id` của principal; JWT mang claim `tenant_id`; backfill tenant mặc định cho dữ liệu hiện có khi migrate.

**`auth.role_code` enum (R-DEC-12):** 7 giá trị BRD + AI Agent (thay 10 giá trị F.O.C.U.S của nền v2.1):

| role_code (v3) | ROLE-* | Gộp từ 10 code F.O.C.U.S | Phân biệt scope |
|---|---|---|---|
| `CEO` | ROLE-CEO | CEO | Toàn doanh nghiệp |
| `DIR` | ROLE-DIR | CFO, VP_SALES, HR_MANAGER, CPO, RISK_MANAGER | Theo `department_id` + data scope (ABAC) |
| `MGR` | ROLE-MGR | MANAGER | Team |
| `EMP` | ROLE-EMP | EMPLOYEE | Cá nhân & việc được giao |
| `REV` | ROLE-REV | REVIEWER | Hàng chờ review được phân |
| `ADM` | ROLE-ADM | ADMIN | Cấu hình nền tảng (không mặc định đọc bản ghi nghiệp vụ) |
| `AI` | ROLE-AI | (mới — actor) | Quyền agent ∩ người được phục vụ |

- `DIR.permissions[]` = hợp quyền của 5 C-level cũ (ma trận: `auth/permission_matrix.py`, sinh từ 02 §5.3), **thu hẹp theo khối** bằng `auth.users.scope_pillars PILLAR[]` (R-DEC-12a, chống leo quyền): tập con ⊆ {F,O,C,U,S}; rỗng = không lọc (CEO, non-DIR). Tầng kiểm quyền ánh xạ domain↔pillar (finance↔F, hr↔O, sales↔C, product↔U, risk↔S; execution/idp/ai/dashboard/platform cross-pillar — không lọc) và từ chối domain nếu pillar ∉ `scope_pillars`. Phạm vi **hàng** vẫn thu hẹp bằng `department_id`/ownership (02 §5–§6).
- `scope_pillars` vào claim JWT + `Principal`; effective-dated không áp (thuộc identity).
- Giữ **bảng ánh xạ** 10→7 (R-DEC-08) ở `TRACEABILITY-SKELETON.md` §12 để truy nguyên test/seed nền v2.1.

### 2.3. Field-level đợt code — M1.1 (R-DEC-21)

**Thực thi lọc tenant (bổ sung R-DEC-13):** tenant hiện hành lấy từ **tenant context** (contextvar `current_tenant`), không truyền tay qua từng hàm. Request: set từ claim JWT `tenant_id`. Consumer Celery: set từ envelope `tenant_id`. Job beat: lặp theo từng tenant hoạt động (MVP: một tenant). Repository nghiệp vụ tự thêm `WHERE tenant_id = current_tenant` cho đọc và tự gán khi ghi; **thiếu tenant context → lỗi (fail closed)**, không mặc định ngầm.

| Bảng | Thay đổi | Kiểu | Ghi chú |
|---|---|---|---|
| `platform.outbox_events` | + `tenant_id` | `UUID NOT NULL`, default = tenant hệ thống MVP (backfill), index `(tenant_id)` | Relay đưa vào envelope (10 §9.1); `LogModel` không kế thừa `TenantMixin` nên thêm cột riêng |
| `platform.processed_events` | không đổi | — | Khóa dedupe `(event_id, consumer)` đã duy nhất toàn cục; DLQ (`processed_events` × `outbox_events`) lấy tenant qua join `outbox_events.tenant_id` |

- Migration reversible (`0010_tenant_outbox`), backfill tenant mặc định. Không đổi bảng nghiệp vụ (đã có `tenant_id` từ `0009`).
- Seed v3 (R-DEC-23) **không** đổi schema; DEC-230/231 hết hiệu lực, số liệu demo theo `08`.

### 2.4. Field-level đợt code — M1.2 (D01 Organization, D02 Admin, D05 Notification — đề xuất, chờ human duyệt bước S)

> Migration dự kiến `0011_org_assignments_notifications` (reversible, backfill). Nhóm cột theo §2.1 nền code: `BusinessModel` = id + `tenant_id` + timestamps + `deleted_at` + `created_by/updated_by` + `source` + `data_classification` + `version`. Endpoint ở 10 §7.2.1.

**ENT-Organization — `hr.organizations`** (mới, `BusinessModel`; R-DEC-24 — schema `hr`)

| Cột | Kiểu | Ràng buộc | Mức | Ghi chú |
|---|---|---|---|---|
| `code` | text | NOT NULL; unique `(tenant_id, code)` WHERE `deleted_at IS NULL` | Nội bộ | VD `ABC` |
| `name` | text | NOT NULL | Nội bộ | Tên giao dịch |
| `legal_name` | text | NULL | Nội bộ | Tên pháp lý |
| `tax_code` | text | NULL | Nội bộ | MST doanh nghiệp (công khai về pháp lý; không phải MST cá nhân) |
| `valid_from` | date | NOT NULL | Nội bộ | Ngày bắt đầu hiệu lực |
| `valid_to` | date | NULL; CHECK `valid_to IS NULL OR valid_to > valid_from` | Nội bộ | NULL = đang hiệu lực; set khi archive |

- **BusinessUnit** (T-611 "tùy chọn"): **không** tạo ở M1.2 — khối/phòng cấp cao biểu diễn bằng `departments.parent_id` (OQ-05-06).
- MVP single-tenant: một tenant có thể nhiều Organization (pháp nhân), seed ABC có **1**.

**ENT-Department — `hr.departments`** (sửa)

| Cột | Thay đổi | Kiểu | Ghi chú |
|---|---|---|---|
| `organization_id` | + mới | UUID NOT NULL FK `hr.organizations.id` (RESTRICT), index | Backfill = Organization seed của tenant (migration tạo 1 org mặc định cho tenant có phòng ban) |
| `parent_id` | giữ (đã có) | UUID NULL FK `hr.departments.id`, index | Service chặn vòng (chính nó/hậu duệ) và cha khác `organization_id` |
| `valid_from` | + mới | date NOT NULL | Backfill = `created_at::date` |
| `valid_to` | + mới | date NULL; CHECK `> valid_from` | Set khi archive cùng `deleted_at` |
| `code` | sửa unique | unique toàn cục → unique `(tenant_id, code)` WHERE `deleted_at IS NULL` (áp tương tự cho `teams.code`, `positions.code`) | Archive xong được dùng lại mã |

**ENT-Team — `hr.teams`** (sửa): + `valid_from date NOT NULL` (backfill `created_at::date`), + `valid_to date NULL`; ngữ nghĩa như Department. **ENT-Position** giữ nguyên (không effective-dated — lịch sử nằm ở phân công).

**ENT-EmployeeAssignment — `hr.employee_assignments`** (mới, `BusinessModel`; FR-ORG-04, FR-DATA-07, §6ter)

| Cột | Kiểu | Ràng buộc | Mức |
|---|---|---|---|
| `employee_id` | UUID | NOT NULL FK `hr.employees.id`, index | Nội bộ |
| `department_id` | UUID | NOT NULL FK `hr.departments.id`, index | Nội bộ |
| `team_id` | UUID | NULL FK `hr.teams.id`, index; team phải thuộc `department_id` (service) | Nội bộ |
| `position_id` | UUID | NULL FK `hr.positions.id`, index; position phải thuộc `department_id` (service) | Nội bộ |
| `manager_id` | UUID | NULL FK `hr.employees.id`, index; CHECK `manager_id <> employee_id` | Nội bộ |
| `valid_from` | date | NOT NULL | Nội bộ |
| `valid_to` | date | NULL; CHECK `valid_to IS NULL OR valid_to > valid_from` | Nội bộ |
| `reason` | text | NULL (≤ 500) | Nội bộ |

- **Khoảng nửa mở `[valid_from, valid_to)`**; `valid_to IS NULL` = phân công **hiện hành**. Hiệu lực tại ngày X ⇔ `valid_from <= X AND (valid_to IS NULL OR valid_to > X)` (index `(employee_id, valid_from)` và `(department_id, valid_from)`).
- **Không chồng khoảng cho cùng `employee_id`** (bỏ qua bản ghi `deleted_at`): (1) unique partial index `(employee_id) WHERE valid_to IS NULL AND deleted_at IS NULL` — tối đa một phân công hiện hành; (2) service kiểm chồng khoảng trong transaction sau `SELECT … FOR UPDATE` trên dòng `hr.employees` (tuần tự hóa ghi cùng nhân viên). Ràng buộc `EXCLUDE USING gist` cần extension `btree_gist` (chưa có trong `0001` EXTENSIONS) → **không dùng ở M1.2** (OQ-05-07).
- Đổi phân công = đóng bản hiện hành (`valid_to = valid_from` mới) + mở bản mới, một transaction, không tạo khoảng trống; không backdate trước `valid_from` hiện hành (sửa lịch sử = PATCH có audit, EP-ORG-23).
- **Cột cache trên `hr.employees`** (`department_id`, `team_id`, `position_id`, `manager_id`) giữ nguyên làm **giá trị hiện hành**, đồng bộ cùng transaction với phân công — code v2.1/scope/dashboard không đổi. Truy vấn quá khứ (`as_of`) **chỉ** đọc `employee_assignments`.
- Backfill migration: mỗi nhân viên live một dòng `valid_from = hire_date`, `valid_to = termination_date` (NULL nếu còn làm), lấy từ cột cache.
- **Giới hạn P0:** đổi `departments.parent_id` **không** effective-dated (cây `as_of` dùng `parent_id` hiện tại + khoảng tồn tại `valid_from/valid_to` của đơn vị); lịch sử tái cấu trúc cấp phòng ban truy qua audit (OQ-05-08).

**ENT-Notification — `platform.notifications`** (sửa; `LogModel`, không `deleted_at`)

| Cột | Thay đổi | Kiểu | Ghi chú |
|---|---|---|---|
| `tenant_id` | + mới | UUID NOT NULL, default tenant hệ thống (backfill), index | `LogModel` không có `TenantMixin` (như `outbox_events` §2.3); EP-NTF lọc tenant + `recipient_id` |
| `email_status` | + mới | enum `platform.email_status` ∈ `NOT_REQUIRED, PENDING, SENT, FAILED` NOT NULL default `NOT_REQUIRED`; index `(email_status, created_at)` | Set `PENDING` khi tạo nếu preference `email_enabled` của người nhận cho `kind` = true |
| `email_sent_at` | + mới | timestamptz NULL | Gửi thành công |
| `email_attempts` | + mới | smallint NOT NULL default 0 | Retry tối đa 3 (5 s/30 s/120 s) → `FAILED` |
| `title`, `body` | giữ | text | Không chứa dữ liệu mức 3–4 (người tạo chịu trách nhiệm; email **không** dùng hai cột này — template theo `kind`) |

- `read_at` đã có; cập nhật `read_at`/`email_*` là UPDATE kỹ thuật được phép (bảng không thuộc diện append-only như `audit_logs`).

**ENT-NotificationPreference — `platform.notification_preferences`** (mới; nhóm config: id + `tenant_id` + timestamps + `version`, không `deleted_at`) — FR-NTF-04 tối thiểu cho T-616b

| Cột | Kiểu | Ràng buộc |
|---|---|---|
| `tenant_id` | UUID | NOT NULL, index |
| `user_id` | UUID | NOT NULL, soft-ref `auth.users.id` (C7, khác schema); unique `(user_id, kind)` |
| `kind` | `platform.notification_kind` | NOT NULL |
| `email_enabled` | boolean | NOT NULL |

- Không có dòng = **mặc định**: email bật cho `task_assigned`, `approval_requested`, `review_assigned`, `review_escalated`; tắt cho các `kind` còn lại (cấu hình trong code `notification_defaults`, đổi = qua DEC). In-app luôn bật. Giờ yên lặng/mức ưu tiên (FR-NTF-03/04 phần còn lại) → backlog.

**Field classification cho mask ở serializer (T-615, R-DEC-34)** — registry một nơi (`core/field_policy.py`), serializer mọi module dùng chung; trường bị che trả `{ "masked": true }` (10 §7.2.1), cùng danh sách dùng cho mask audit (`core/audit.MASKED_KEYS`), event payload và PII filter LLM.

| Bảng.cột | Mức | Ai thấy giá trị thật |
|---|---|---|
| `hr.employees.date_of_birth`, `address`, `national_id`, `bank_account`, `emergency_contact` | 4 Tuyệt mật | CEO, DIR khối O (+ REV trong phiên review được phân — khi IDP gán) |
| `hr.salary_history.base_salary` | 4 Tuyệt mật | như trên (đã có `FORBIDDEN_SALARY` ở list) |
| `hr.employees.email`, `phone` | 3 Mật | Người có data scope trên bản ghi (CEO, DIR-O toàn bộ; MGR phòng mình; EMP chính mình); ADM scope `s` và mọi kênh ra ngoài (email, event, prompt LLM cloud) → mask |
| `auth.users.email` | 3 Mật | ADM (`platform:read` — cần để quản trị tài khoản), chính chủ (`/auth/me`); không vào event payload/email body |
| `hr.organizations.*`, `departments.*`, `teams.*`, `positions.*`, `employee_assignments.*`, `employees.full_name/employee_code` | 2 Nội bộ | Theo permission + data scope; không mask |

### 2.5. Field-level đợt code — M1.3 (D11 Task/Project/Workload, D04 Approval cơ bản — đề xuất, chờ human duyệt bước S)

> Migration `0014_work_tasks_m13` (schema `execution`) và `0015_workflow_approvals_m13` (schema `platform`), reversible, có backfill; `downgrade -1 && upgrade head` sạch qua từng bản. Nhóm cột `BusinessModel` như §2.4. Classification: task/project/milestone/dependency = **Nội bộ** (§2.1 "Sản phẩm & thực thi"); approval = **Nội bộ**.

**ENT-Task — `execution.tasks`** (sửa)

| Cột | Thay đổi | Kiểu | Ghi chú |
|---|---|---|---|
| `parent_id` → `parent_task_id` | **đổi tên** (R-DEC-42) | UUID NULL FK `execution.tasks.id` (RESTRICT), index | Một cấp sub-task (cha không được có cha); service chặn chính nó/vòng. API v2.1 field `parent_id` đổi tên cùng path mới (đã breaking theo R-DEC-40). Seed v3 hiện không dùng cột → backfill không cần |
| `source_ref` | + mới | JSONB NULL; CHECK `source_ref IS NULL OR (source_ref ? 'kind' AND source_ref ? 'id')` | `{kind ∈ meeting/decision/ai_action/document/mitigation, id: uuid, page?: int}` — **con trỏ nguồn gốc** cho P06 lineage (task từ họp/AI/IDP). `kind` phải nhất quán `task_source` (meeting/decision→`meeting`, ai_action→`ai`, document→`document`, mitigation→`mitigation`) — service, sai → `422`. Backfill: `meeting_id`/`decision_id`/`source_document_id` có giá trị → `source_ref` tương ứng (ưu tiên decision > meeting > document). Giữ các cột FK cũ (không xóa; FK thật cho meeting/decision) |
| `assignee_id` | **đổi ngữ nghĩa** (R-DEC-41) | UUID NULL (soft ref) | = `hr.employees.id` (trước: lẫn `auth.users.id`). Backfill: giá trị trùng `auth.users.id` có `employee_id` → thay bằng `employee_id` (UPDATE qua join trong migration, downgrade đảo lại theo bảng tạm `_m13_assignee_backfill`). `owner_id` giữ = `auth.users.id` (người tạo/chịu trách nhiệm) |
| index | + mới | `(tenant_id, assignee_id, due_date)` WHERE `deleted_at IS NULL` | "Task của tôi" + workload; index cũ `ix_tasks_assignee_id_status_due_date` giữ |

**ENT-TaskDependency — `execution.task_dependencies`** (mới, `BusinessModel`; FR-TASK-02)

| Cột | Kiểu | Ràng buộc | Mức |
|---|---|---|---|
| `task_id` | UUID | NOT NULL FK `execution.tasks.id` (CASCADE), index — task **bị chặn** | Nội bộ |
| `depends_on_task_id` | UUID | NOT NULL FK `execution.tasks.id` (CASCADE), index — task **phải xong trước** | Nội bộ |
| `dependency_type` | enum `task_dependency_type` | NOT NULL DEFAULT `finish_to_start` (P0 chỉ một giá trị; enum để mở rộng `start_to_start` P1) | Nội bộ |
| — | CHECK | `task_id <> depends_on_task_id` | — |
| — | UNIQUE | `(tenant_id, task_id, depends_on_task_id)` WHERE `deleted_at IS NULL` | — |

- Không vòng: service BFS từ `depends_on_task_id` theo cạnh `depends_on` trong tx sau `SELECT … FOR UPDATE` trên hai dòng task (thứ tự id tăng để tránh deadlock); giới hạn độ sâu 50 (vượt → `422`). Dependency giữa **project** (FR-TASK-02 vế 2) và cảnh báo đường găng → **hoãn M3.x** (backlog FR-TASK-02b).
- Task cùng tenant bắt buộc; khác phòng ban được phép (dự án chéo phòng 08 §2.1).

**ENT-Milestone — `execution.milestones`** (không đổi schema): đã có `project_id` + CK `one_parent`; M1.3 chỉ mở API theo project. `late` là trường tính (không lưu).

**ENT-Project — `execution.projects`** (sửa, `0014`): **+ `initiative_id`** UUID NULL FK `execution.initiatives.id` (SET NULL), index `(tenant_id, initiative_id)` — liên kết Initiative → Project (FR-STR-01 "Strategic project"); M1.3 sở hữu cột + field API (EP-TASK-09..12, `ProjectOut`), M1.4 chỉ đọc (EP-STR-22, `/goals/tree`). Backfill NULL. Trường tính: `progress_pct`, `planned_pct`, `late` tính lúc đọc từ task (cùng hàm với METRIC-OPS-02 — tách `execution/services/project_rules.py` thuần để dùng chung, không lệch công thức).

**ENT-Workload** — **không tạo bảng** (R-DEC-44): tính lúc đọc từ `tasks` qua `services/workload.py` (Σ `estimate_hours`, thiếu → 4h; 40h/tuần; > 110% hai tuần liên tiếp). Thêm hàm `weekly_grid(db, dept, week_end, weeks)` dùng chung cho EP-TASK-18 và heatmap EP-49 (bỏ trùng `_heatmap`).

**ENT-ApprovalRequest — `platform.approval_requests`** (sửa, `0015`)

| Cột | Thay đổi | Kiểu | Ghi chú |
|---|---|---|---|
| `department_id` | + mới | UUID NULL (soft ref), index `(tenant_id, status, department_id)` | Data scope MGR `d` cho inbox. Backfill NULL (AI action v2.1 = cấp công ty) |
| `target_kind` | + mới | text NOT NULL | Backfill từ `approval_rules.target_kind` (`ai_action`); thôi trả hằng số trong `_to_out` |

**ENT-ApprovalRule — `platform.approval_rules`** (không đổi cột): thêm bản ghi `RULE-task_reassign` `{target_kind: task_reassign, condition: {}, approver_role_codes: [MGR], second_approver_role_codes: null, escalate_to_role_code: DIR, sla_hours: 8 (= DEFAULT_SLA_HOURS hiện có), priority: 100}` — tạo lười trong service như `_finance_rule` (không seed migration). `SINGLE_STEP_ROLES`/`FINANCE_STEP_ROLES` cứng → đọc từ rule (`approver_role_codes` bước 1, `second_approver_role_codes` bước 2); giá trị cho `ai_action` giữ nguyên (CEO,DIR / CEO→DIR).

**ENT-Notification** (không đổi schema/enum): kind dùng `task_assigned`, `approval_requested`, `approval_decided` (có sẵn) và **`reminder` cho task quá hạn** (R-DEC-46; không thêm giá trị enum). Email theo `notification_preferences` (mặc định: `task_assigned`, `approval_requested` bật; `reminder`, `approval_decided` tắt — giữ `EMAIL_DEFAULT_ON` M1.2). `ref_schema='execution'`, `ref_table='tasks'` / `'platform','approval_requests'`; `link` = `/work?task=<id>` / `/work/approvals?id=<id>`; `title`/`body` không chứa mức 3–4.

### 2.6. Field-level đợt code — M1.4 (D07 Strategy, D08 KPI, D09 OKR, D10 check-in — đề xuất, chờ human duyệt bước S)

Nhóm bảng theo 05 §2.1: **nghiệp vụ** (C3/C4/C19 + `tenant_id` + `deleted_at`, `BusinessModel`) hoặc **append-only** (`LogModel` + **`tenant_id`** — R-DEC-51 bổ sung tenant cho log mới). Schema `execution`. Tham chiếu chéo module là soft ref (C7, không FK chéo schema). Index mọi FK.

**ENT-Strategy → `execution.strategies` (mới, nghiệp vụ):** `code` text UQ (live), `name` text, `vision` text?, `mission` text?, `period_start` date, `period_end` date (CHECK `period_end > period_start`), `owner_id` uuid soft-ref `auth.users`, `status` enum `execution.strategy_status` (`draft, active, closed`). Ràng buộc "≤ 1 Strategy `active` chồng kỳ/tenant" kiểm ở service (khóa `SELECT … FOR UPDATE`).

**ENT-StrategicObjective → `execution.strategic_objectives` (mới, nghiệp vụ, R-DEC-50):** `strategy_id` FK `strategies.id`, `code` text UQ (live), `title`, `description`?, `pillar` `PILLAR`? (F/O/C/U/S — StrategicPillar P0 = enum pillar, không bảng riêng), `owner_id`, `department_id`? soft-ref `hr.departments`, `weight_pct` numeric(7,4) 0–100, `sort_order` int default 0, `status` `OKR_STATUS`, `progress_pct` numeric(7,4) hệ thống tính = trung bình trọng số `progress_pct` của Initiative live (trọng số `weight_pct`, tổng 0 → trung bình đều; không có initiative → trung bình progress Objective gắn trực tiếp; không có → 0). Index `(strategy_id, sort_order)`.

**Cột mới trên bảng có sẵn:**

| Bảng | Cột | Kiểu | Ghi chú |
|---|---|---|---|
| `objectives` | `strategic_objective_id` | uuid FK `strategic_objectives.id` NULL | Chỉ Objective gốc (`parent_id IS NULL`) — CHECK `parent_id IS NULL OR strategic_objective_id IS NULL` |
| `kpis` | `strategic_objective_id` | uuid FK NULL | Chỉ KPI gốc — CHECK tương tự với `parent_kpi_id` |
| `kpis` | `pillar` | `PILLAR` NULL | Phục vụ scope DIR theo khối (R-DEC-57) |
| `initiatives` | `strategic_objective_id` | uuid FK NULL | Backfill rồi giữ NULL được ở DB; **bắt buộc** ở API mới (EP-STR-13) |
| `initiatives` | `objective_id` | đổi NOT NULL → **NULL** | Initiative thuộc SO; Objective OKR là tùy chọn |
| `key_results` | `at_risk` | bool NOT NULL default false | Cờ tính sẵn (R-DEC-55) |
| `key_results` | `at_risk_since` | timestamptz NULL | Thời điểm chuyển `true` |
| `key_results` | `at_risk_reasons` | text[] NOT NULL default `{}` | ⊆ `declining, low_confidence, behind_plan` |
| `key_results` | `last_checked_in_at` | timestamptz NULL | Cập nhật ở EP-PRF-02 (nguồn G2 + `due`) |
| `kpi_targets` | `valid_from` | date NOT NULL | Backfill = ngày đầu kỳ `period_key` |
| `kpi_targets` | `valid_to` | date NULL | Nửa mở `[valid_from, valid_to)`, NULL = hiện hành (cùng mô hình 05 §2.4) |
| `kpi_targets` | `reason` | text NULL | Lý do đổi target giữa kỳ (audit) |
| `kpi_measurements` | `tenant_id`, `measured_by` (uuid NULL), `data_source` (`KPI_DATA_SOURCE` default `manual`), `note` text NULL, `check_in_id` uuid FK `check_ins.id` NULL | | Bỏ UQ `(kpi_id, period_key)` → index thường `(kpi_id, period_key, measured_at DESC)` (R-DEC-51) |
| `check_ins` | `tenant_id` | uuid NOT NULL | Backfill tenant hệ thống |

**KPITarget effective-dated (R-DEC-52):** thay partial UQ `(kpi_id, period_key) WHERE deleted_at IS NULL` bằng partial UQ `(kpi_id, period_key) WHERE deleted_at IS NULL AND valid_to IS NULL` (≤ 1 bản hiện hành/kỳ) + exclusion logic ở service (không chồng khoảng). Target "hiệu lực tại thời điểm đo" = bản có `valid_from ≤ ngày đo < valid_to` (ngày theo `Asia/Ho_Chi_Minh`); không có → tự tạo từ `kpis.target_value` (giữ hành vi v2.1). `locked_at` áp cho mọi bản của kỳ.

**ENT-KPIEvaluation → `execution.kpi_evaluations` (mới, nghiệp vụ, R-DEC-53):** `kpi_id` FK, `period_key`, `kpi_target_id` FK (target hiệu lực dùng để chấm), `measurement_id` FK `kpi_measurements.id` (lần đo mới nhất của kỳ), `actual_value` measure, `target` measure, `achievement_pct` numeric(7,4), `band` `KPI_BAND`, `previous_band` `KPI_BAND`?, `gap_value` measure (= target − actual theo `direction`, ≥ 0 khi chưa đạt), `measured_on_time` bool, `evaluated_at` ts, `locked_at` ts?. UQ partial `(kpi_id, period_key) WHERE deleted_at IS NULL`. Upsert khi đo/đổi target; là **nguồn đọc** cho chi tiết KPI, cây, G2, UC-03 (không tính lúc request).

**ENT-KRMeasurement → `execution.kr_measurements` (mới, append-only, R-DEC-53):** `tenant_id`, `key_result_id` FK, `check_in_id` FK `check_ins.id` UQ NULL (NULL = backfill/seed), `period_key` (kỳ Objective), `value` measure, `progress_pct` numeric(7,4), `previous_progress_pct` numeric(7,4)?, `confidence` `CONFIDENCE_BAND`, `measured_at` ts, `measured_by` uuid?. Index `(key_result_id, measured_at DESC)`. Chuẩn hóa từ `check_ins` (KR): mỗi check-in KR sinh đúng một dòng cùng transaction; backfill trong migration 0016 từ check-in KR có sẵn (sort `checked_in_at`, tính `progress_pct` theo baseline/target hiện tại).

**Quy tắc tính (service, có unit test):**
- **On-time KPI:** kỳ `P` của KPI `active` là *đúng kỳ* nếu có measurement với `measured_at < end(P) + GOALS_KPI_GRACE_DAYS` (mặc định 5 ngày; cấu hình qua `ConfigService`).
- **On-time KR:** KR `active` (Objective `active`, kỳ chứa ngày tính) là *đúng kỳ* nếu `last_checked_in_at ≥ ngày tính − GOALS_KR_CHECKIN_MAX_AGE_DAYS` (mặc định 7 — check-in tuần, FR-OKR-04).
- **`METRIC-STR-01` G2 — "KPI/OKR cập nhật đúng kỳ" (R-DEC-54):** `pct(#KPI-kỳ đúng hạn + #KR đúng hạn, #KPI-kỳ đến hạn + #KR active)`; KPI-kỳ đến hạn = kỳ đã kết thúc gần nhất (cộng grace) của mỗi KPI `active`. Hướng `LO`, warning **80** (cổng G2), critical 60; refresh trên `execution.kpi_measured`, `execution.okr_checked_in` + recompute hằng ngày; lineage → danh sách KPI/KR trễ (`records`).
- **SEI — Strategy Execution Index:** giữ công thức DEC-226 (`progress ≥ 0,9 × kế hoạch tuyến tính`, trọng số `weight_pct`), mã **giữ `METRIC-RSK-06`** ở M1.4 (đổi sang mã nhóm STR ở T-701/M2.1 cùng bảng ánh xạ 32 METRIC — mã cấp khi đó); thêm `refresh_events` `execution.kpi_measured`; `records` = initiative trễ (drill-down 03 §4). Cùng hàm dùng cho `on_track` ở EP-STR-01.
- **At-risk KR (R-DEC-55):** sau mỗi check-in KR và job beat hằng ngày 07:00: `reasons` = `declining` (progress < progress lần đo trước) ∪ `low_confidence` (`confidence = LOW`) ∪ `behind_plan` (progress < 0,7 × % thời gian đã trôi của kỳ — tham số `GOALS_KR_BEHIND_RATIO`); `at_risk = reasons ≠ ∅ ∧ days_to_period_end ≥ 21`. Chuyển false→true → `execution.okr_at_risk`.

**Migration dự kiến (dải M1.4):**
- **`0016_goals_strategy_m14`** (T-626, T-627a): enum `execution.strategy_status`; bảng `strategies`, `strategic_objectives`; cột `strategic_objective_id` (objectives/kpis/initiatives), `kpis.pillar`, `initiatives.objective_id` DROP NOT NULL; backfill: mỗi tenant có Initiative/Objective `level=company` → 1 Strategy `STR-<năm>` (`active`, kỳ = năm của Objective) + 1 StrategicObjective/Objective company năm (`SO-<code>`), gán `initiatives.strategic_objective_id`. Downgrade: chỉ đặt lại NOT NULL nếu không có dòng NULL (nếu có → raise rõ ràng).
- **`0017_goals_measure_m14`** (T-627): `kpi_targets.valid_from/valid_to/reason` (backfill `valid_from = đầu kỳ`), đổi UQ; `kpi_measurements` cột mới + bỏ UQ; `check_ins.tenant_id`; bảng `kpi_evaluations` (backfill từ measurement hiện có) và `kr_measurements` (backfill từ check-in KR); cột at-risk + `last_checked_in_at` trên `key_results` (backfill `max(checked_in_at)`). Downgrade: xóa bảng/cột mới; khôi phục UQ `kpi_measurements` bằng cách giữ dòng mới nhất mỗi `(kpi_id, period_key)` (mất lịch sử đo nhiều lần — ghi rõ trong docstring).
- Enum `platform.notification_kind`: **không đổi** (R-DEC-59).

### 2.7. Field-level đợt code — M1.5 (D03 Data Capture C1/C3/C5, Action Registry v2, lineage — đề xuất, chờ human duyệt bước S)

> Migration `0018_capture_registry` (idp + platform.data_lineage) và `0019_capture_seed_doctypes` (data: doc type #2/#3/#4 + schema v1 published + rule). Cả hai reversible; `downgrade` của 0019 xóa schema/rule seed **chỉ khi** chưa có `extraction_jobs` tham chiếu (ngược lại raise). Thứ tự phụ thuộc: sau `0014..0017` của M1.3/M1.4.
>
> + `0020_capture_dq` (platform.dq_domain_scores) — làm rõ khi code; M1.6 dời sang 0021.

**ENT-SourceDocument — `idp.source_documents`** (sửa)

| Cột | Kiểu | Ràng buộc | Mức | Ghi chú |
|---|---|---|---|---|
| `committed_by` | uuid | NULL | Nội bộ | **mới**; người thực thi ACT (khác `reviewed_by` khi qua EP-DC-23) |
| `rolled_back_at` | timestamptz | NULL | Nội bộ | **mới** |
| `rolled_back_by` | uuid | NULL | Nội bộ | **mới** |
| `rollback_reason_code` | text | NULL; CHECK IN (`mistake`,`critical_field_wrong`,`duplicate`,`other`) | Nội bộ | **mới** |
| `row_count` | integer | NULL; CHECK `row_count >= 0` | Nội bộ | **mới**; số dòng đưa vào tài liệu (C5/bảng) |
| index | | `ix_source_documents_submitted_by_status (submitted_by, status)`; `ix_source_documents_department_id_status (department_id, status)` | | **mới** cho Hộp thư |

**ENT-ImportBatch — `idp.import_batches`** (sửa; `LogModel` → thêm `tenant_id`)

| Cột | Kiểu | Ràng buộc | Mức | Ghi chú |
|---|---|---|---|---|
| `tenant_id` | uuid | NOT NULL, server_default tenant hệ thống (backfill), index | Nội bộ | **mới** (R-DEC-21) |
| `source_document_id` | uuid | NULL, FK `idp.source_documents.id` ON DELETE RESTRICT, index | Nội bộ | **mới**; C5: 1 batch ↔ 1 tài liệu |
| `document_type_id` | uuid | NULL, FK `idp.document_types.id`, index | Nội bộ | **mới** |
| `sheet_name` / `header_row` | text / smallint | NULL; CHECK `header_row BETWEEN 1 AND 50` | Nội bộ | **mới** |
| `rows_total` / `rows_valid` / `rows_invalid` | integer | NOT NULL default 0; CHECK ≥ 0 | Nội bộ | **mới** |
| `column_mapping` | jsonb | giữ; shape `{columns: [{index, header, field, confidence, origin: AI\|HEURISTIC\|USER}]}` | Nội bộ | **sửa** shape |
| `version` | integer | NOT NULL default 1 | — | **mới**; khóa lạc quan EP-DC-19/22 |

**ENT-ImportRow — `idp.import_rows`** (mới, `LogModel` + `tenant_id`; chỉ phục vụ preview/error file — R-DEC-62)

| Cột | Kiểu | Ràng buộc | Mức | Ghi chú |
|---|---|---|---|---|
| `tenant_id` | uuid | NOT NULL, index | Nội bộ | |
| `import_batch_id` | uuid | NOT NULL, FK `idp.import_batches.id` ON DELETE CASCADE | Nội bộ | |
| `row_number` | integer | NOT NULL; unique `(import_batch_id, row_number)` | Nội bộ | số dòng Excel gốc |
| `raw` | jsonb | NOT NULL | theo cột | giá trị gốc theo header; cột mức 4 lưu **mã hóa** như `extracted_fields.value` |
| `values` | jsonb | NULL | theo cột | sau chuẩn hóa VN (FR-DC-13) |
| `errors` | jsonb | NOT NULL default `[]` | Nội bộ | `[{field, rule_code, message_key, params}]` |
| `status` | text | NOT NULL; CHECK IN (`valid`,`invalid`) | Nội bộ | index `(import_batch_id, status)` |

- Retention: `import_rows` xóa cứng bởi job `idp.purge_import_rows` khi batch `completed` + `undo_deadline` qua (giữ `extracted_fields` làm nguồn lineage). Hoãn nếu job retention chung chưa có → ghi OQ.

**ENT-DocumentAction — `idp.document_actions`** (mới, `LogModel` + `tenant_id`; R-DEC-63)

| Cột | Kiểu | Ràng buộc | Mức | Ghi chú |
|---|---|---|---|---|
| `tenant_id` | uuid | NOT NULL, index | Nội bộ | |
| `source_document_id` | uuid | NOT NULL, FK `idp.source_documents.id` ON DELETE RESTRICT, index | Nội bộ | |
| `seq` | integer | NOT NULL; unique `(source_document_id, seq)` | Nội bộ | thứ tự chạy; undo theo `seq DESC` |
| `action_name` | text | NOT NULL | Nội bộ | `ACT-*` trong Registry |
| `row_index` | integer | NULL | Nội bộ | dòng nguồn |
| `params` | jsonb | NOT NULL | ≤ 3 | tham số đã validate; field mức 4 **không** lưu (thay `{masked:true}`) |
| `result_refs` | jsonb | NOT NULL | Nội bộ | `[{schema, table, id, reused: bool}]` |
| `snapshot` | jsonb | NULL | ≤ 3 | trạng thái trước (upsert) để undo; không chứa mức 4 |
| `target_version` | integer | NULL | Nội bộ | `version` bản ghi đích sau ghi — so khi undo (sửa sau commit → conflict) |
| `status` | text | NOT NULL; CHECK IN (`applied`,`reverted`) | Nội bộ | |
| `executed_by` / `executed_at` | uuid / timestamptz | NOT NULL | Nội bộ | |
| `reverted_at` / `reverted_by` | timestamptz / uuid | NULL | Nội bộ | |

**ENT-DataLineage — `platform.data_lineage`** (sửa)

| Cột | Kiểu | Ràng buộc | Mức | Ghi chú |
|---|---|---|---|---|
| `tenant_id` | uuid | NOT NULL, server_default tenant hệ thống (backfill), index | Nội bộ | **mới** (R-DEC-21) |
| `document_action_id` | uuid | NULL (không FK chéo schema — DEC-125; tham chiếu logic) | Nội bộ | **mới**; revoke theo action |
| `row_index` | integer | NULL | Nội bộ | **mới** |
| index | | `ix_data_lineage_source_document_id (source_document_id)`; partial `ix_data_lineage_target_live (target_schema, target_table, target_id) WHERE revoked_at IS NULL` | | **mới** |

- Ghi: mỗi cột đích được set từ field → 1 dòng `link_kind=RECORD_FROM_FIELD` `{target_schema, target_table, target_id, target_column, extracted_field_id, document_page_id, source_document_id, action_name, row_index}`. `document_page_id` lấy từ `extracted_fields.document_page_id` (**sửa** pipeline: gán theo `source_location.page`/`sheet`, không cố định trang 1). C1: `extracted_field_id` của field manual, `document_page_id` NULL. Undo → `revoked_at = now()` (không xóa — P06).
- Ghi lineage qua **service public** `platform.services.lineage_service.LineageService.record_many(db, links)` (mới) — idp không import model platform.

**ENT-CaptureIncident — `idp.capture_incidents`** (mới, `BusinessModel`; G4 — R-DEC-69)

| Cột | Kiểu | Ràng buộc | Mức | Ghi chú |
|---|---|---|---|---|
| `source_document_id` | uuid | NOT NULL, FK, index | Nội bộ | |
| `extracted_field_id` | uuid | NULL, FK `idp.extracted_fields.id` | Nội bộ | |
| `field_name` | text | NOT NULL | Nội bộ | |
| `is_critical` | boolean | NOT NULL | Nội bộ | sao từ field/schema |
| `detected_by` | text | NOT NULL; CHECK IN (`review`,`post_commit`,`undo`) | Nội bộ | `review` = bắt được trước commit (không tính G4) |
| `undetected` | boolean | NOT NULL | Nội bộ | = `detected_by <> 'review'` AND field đã qua người hoặc STP |
| `target_table` / `target_id` | text / uuid | NULL | Nội bộ | |
| `description` | text | NOT NULL, ≤ 2000 | ≤ 3 | |
| `reported_by` / `reported_at` | uuid / timestamptz | NOT NULL | Nội bộ | |
| index | | `(undetected, reported_at)` | | |

- Tự tạo incident (không qua EP-DC-36) khi undo `reason_code=critical_field_wrong` (một dòng/field trọng yếu của tài liệu, `detected_by=undo`).

**ENT-ExtractionSchema — `idp.extraction_schemas`** (sửa shape JSONB, không đổi cột)
- `fields[]`: `{name, label_key, value_type, required, is_critical, sensitivity_level, group?: "row", target: {action, param}, enum?, master_ref?: "hr.department_code"|"hr.employee_code"|"execution.kpi_code", header_aliases[]}`.
- `thresholds`: `{classification_confidence_min ≥ 0.95, required_field_min ≥ 0.90}` (DEC-133, chỉ được **tăng**).
- `action_names`: thứ tự ACT; **thêm** cột `classifier_keywords text[] NOT NULL default '{}'` ở `idp.document_types` (R-DEC-65).

**ENT-DQDomainScore — `platform.dq_domain_scores`** (mới, `LogModel` + `tenant_id`; R-DEC-68)

| Cột | Kiểu | Ràng buộc | Mức | Ghi chú |
|---|---|---|---|---|
| `tenant_id` | uuid | NOT NULL | Nội bộ | |
| `domain` | text | NOT NULL | Nội bộ | `finance, sales, hr, product, risk, execution, idp` |
| `period_key` | text | NOT NULL; unique `(tenant_id, domain, period_key)` | Nội bộ | tháng |
| `completeness` / `accuracy` / `freshness` / `score` | numeric(5,2) | NOT NULL; CHECK 0..100 | Nội bộ | |
| `rows` | integer | NOT NULL | Nội bộ | |
| `computed_at` | timestamptz | NOT NULL | Nội bộ | |

### 2.8. Field-level đợt code — M1.6 (D26 AI Platform nền, UC-07 Onboarding — đề xuất, chờ human duyệt bước S)

> Migration `0020_ai_platform_m16` (reversible; `downgrade` xóa cột/bảng mới, khôi phục `message_id NOT NULL` sau khi xóa dòng log có `message_id IS NULL` — chỉ dev). `0021_*` để trống (dự phòng). Không bảng mới cho onboarding (R-DEC-75). Endpoint ở 10 §7.2.5.

**ENT-ToolCallLog — `ai.tool_call_logs`** (sửa; `LogModel` append-only — R-DEC-74)

| Cột | Thay đổi | Kiểu | Ghi chú |
|---|---|---|---|
| `tenant_id` | + mới | UUID NOT NULL, backfill tenant mặc định, index `(tenant_id, created_at DESC)` | Log không kế thừa `TenantMixin` → cột riêng (tiền lệ `outbox_events`, R-DEC-21) |
| `request_id` | + mới | UUID NULL, index | = `X-Request-Id` (`current_request_id()`); NULL chỉ với job beat/consumer → khi đó lấy `correlation_id` của event |
| `user_id` | + mới | UUID NULL (soft ref `auth.users`), index | Người được phục vụ (`on_behalf_of`); NULL = agent chạy theo lịch |
| `message_id` | sửa | NOT NULL → **NULL** | Tool call ngoài chat (event/onboarding/demo replay) |
| `ai_action_id` | + mới | UUID NULL FK `ai.ai_actions.id` (RESTRICT), index | Tool WRITE tạo thẻ |
| `tool_kind` | + mới | `ai.tool_kind` enum `READ/WRITE/APPROVAL/EXECUTION` NOT NULL, backfill từ registry (không tìm thấy → `READ`) | Lọc EP-AI-22 |
| `error_code` | + mới | text NULL | `FORBIDDEN_ROLE`, `AI_DISABLED`, `AI_WRITE_VIA_ACTION`… (nội bộ) |
| `result_refs` | + mới | JSONB NOT NULL default `'[]'` | `SourceRef[]` rút gọn `{type,id,label}` — không giá trị thô |
| `arguments` | giữ | JSONB | **Phải qua `scrub_for_model`/field_policy trước khi ghi** (mức 4 bỏ, mức 3 mã hóa) |
| `autonomy_level` | sửa ngữ nghĩa | — | = level **hiệu lực** sau `resolve_level` (không còn `autonomy_default`) |

**ENT-ModelCallLog — `ai.model_call_logs`** (sửa): + `tenant_id` UUID NOT NULL (backfill, index `(tenant_id, created_at DESC)`); + `request_id` UUID NULL index; + `agent_profile_code` text NULL (index — `group_by=agent`). `CallRecord` (`core/model_gateway/gateway.py`) thêm `request_id`, `agent_profile_code`; `core` đọc `current_request_id()` (không import modules).

**ENT-AIAgent — `ai.agent_profiles`** (sửa; giữ tên bảng, ENT-AIAgent ≡ ENT-AIAgentProfile — R-DEC-71): + `agent_ref` text NOT NULL unique (`AGT-CEO`, `AGT-DATA_CAPTURE`, `AGT-PERFORMANCE`, `AGT-TASK`, `AGT-MEETING`, `AGT-REPORTING`); + `description_vi`, `description_en` text NOT NULL; + `tenant_id` UUID NOT NULL (backfill), unique đổi `code` → `(tenant_id, code)`; CHECK `max_autonomy_level <> 'L4'` (enum đã không có L4 — giữ). `allowed_tools text[]` phải ⊆ registry (kiểm ở service, không FK).

| `code` | `max_autonomy_level` (seed) | `model_task` | `allowed_tools` (seed, ⊆ registry; tool `p1_frozen`/APPROVAL loại) |
|---|---|---|---|
| `ceo` | L2 | `chat` | mọi READ P0 (finance/sales/hr dashboard, `get_kpi_status`, `get_okr_status`, `get_project_status`, `get_metric`, `list_alerts`, `get_lineage`, `get_org_tree`, `search_documents`, `get_source_document`) + `generate_report`, `record_decision`, `create_task`, `request_approval` |
| `data_capture` | L2 | `extract` | `search_documents`, `get_source_document`, `get_lineage`, `submit_document`, `create_department`, `create_team` |
| `performance` | L2 | `chat` | `get_kpi_status`, `get_okr_status`, `list_objectives`, `get_metric`, `record_kpi_measurement`, `record_kr_checkin`, `upsert_kpi`, `upsert_objective` |
| `task` | L2 | `chat` | `list_tasks`, `get_overdue_tasks`, `get_project_status`, `get_workload`, `get_org_tree`, `create_task`, `assign_task`, `update_task`, `send_notification` |
| `meeting` | L2 | `chat` | `record_decision`, `create_meeting`, `create_task`, `send_notification`, `get_org_tree` |
| `reporting` | L2 | `report` | `get_execution_dashboard`, `get_metric`, `list_alerts`, `get_kpi_status`, `get_okr_status`, `generate_report` |

- Agent `assistant` v2.1 (hard-code) → ánh xạ `ceo` (R-DEC-71): chat dùng `ceo` cho CEO/DIR, và **agent theo role** ở M1.6 = `ceo` cho mọi người (Orchestrator chọn agent = M2.4); quyền hiệu lực = `allowed_tools(agent)` ∩ `available_for(permissions người)`. Bản ghi cũ `agent_profile_code='assistant'` giữ nguyên (log append-only), FE hiển thị nhãn "Trợ lý (v2.1)".
- `monthly_budget_usd` NULL = dùng ngân sách chung `AI_MONTHLY_BUDGET_USD`; vượt 100% budget agent → `429 AI_QUOTA_EXCEEDED` cho agent đó (cảnh báo 80% hiển thị ở SCR-64) — FR-AIQ-05.

**ENT-AutonomyPolicy — `ai.autonomy_policies`** (sửa): + `tool_name` text NOT NULL (backfill: tool có `action_name` khớp; không khớp → `TOOL-` + phần sau `ACT-`), index; + `agent_profile_code` text NULL (NULL = mọi agent); + `reason` text NOT NULL default `''` (bắt buộc ở API); + `tenant_id` UUID NOT NULL (backfill). Unique partial đổi thành `(tenant_id, action_name, agent_profile_code, role_code, max_amount) NULLS NOT DISTINCT WHERE deleted_at IS NULL`. CHECK `level <= max_level` (theo thứ tự enum). `AutonomyPolicyOut {id, tool_name, action_name, agent_profile_code, role_code, max_amount, currency, level, max_level, is_active, reason, version, updated_by, updated_at}`.

**ENT-AIAction — `ai.ai_actions`**: không đổi cột (đã có `agent_profile_code`, `request_id`, `idempotency_key`); `agent_profile_code` giờ lấy từ agent thật.

**Trạng thái onboarding — `platform.system_settings` key `onboarding.state`** (không bảng mới — R-DEC-75; `ConfigModel`, `is_secret=false`). `value` JSONB:

| Khóa | Kiểu | Ghi chú |
|---|---|---|
| `status` | `not_started/in_progress/completed` | |
| `started_at`, `completed_at` | ISO 8601 UTC \| null | Đồng hồ "trong 1 ngày" = `completed_at - started_at` (hoặc `now - started_at`) ≤ 24 h → `within_one_day` (FE đếm ngược 24:00:00; mục tiêu BRD "trong 1 ngày làm việc" hiển thị ≤ 8 h là "xanh") |
| `started_by` | UUID | user ADM/CEO |
| `steps` | object `{company, org_import, review, users, goals_import, finish}` → `{status ∈ pending/in_progress/done/skipped, updated_at, refs{}}` | `goals_import` được `skipped` (tùy chọn); `review` tự `done` khi import `org_import` đã commit |
| `refs` | `{organization_id?, org_import_id?, goals_import_id?, document_ids[]?}` | Chỉ mã; không tên/email |
| `version` | int | Dùng `system_settings.version` (đã có `VersionMixin`) cho optimistic lock |

- `SystemSettingService` thêm `set(..., expected_version)` → lệch → `ConflictStateError` (409). Key mới khai trong whitelist key setting (`ai.kill_switch`, `onboarding.state`).
- Phân loại: `onboarding.state` mức 2 Nội bộ; `tool_call_logs.arguments` mức 2 sau scrub (mức 3/4 không bao giờ lưu); `model_call_logs.prompt_sha256` mức 1.

## 3. 13 nhóm entity (BRD §13.2)

Mỗi nhóm nêu **vai trò nghiệp vụ**, **entity P0 chính** (tập con phục vụ domain P0 trong `TRACEABILITY-SKELETON.md` §12bis), và **liên kết lineage/event** chính. Tham chiếu `ENT-<Name>`. Field/kiểu/ràng buộc chi tiết chốt khi chi tiết hóa per-domain (R-DEC-09; giữ nguyên tắc: UUID id, created_at/updated_at, soft delete nghiệp vụ, index mọi FK — nhất quán `main` §5.7).

| Nhóm | Entity (đầy đủ BRD §13.2) | Vai trò nghiệp vụ | Entity P0 chính | Lineage / Event chính |
|---|---|---|---|---|
| Tổ chức | Organization, BusinessUnit, Department, Team, Employee, Position, Role | Khung tổ chức & con người — nền của scope RBAC và data ownership (D01) | Organization, Department, Team, Employee, Position, Role | effective-dated cho cơ cấu (FR-ORG-04); Employee là đích khớp tên trong UC-02/UC-06 |
| Kinh doanh | Customer, Contact, Lead, Opportunity, Partner, Vendor, Contract, ContractObligation, PurchaseOrder | Quan hệ khách hàng/đối tác & pipeline bán hàng (D17 Sales Lite P0; D18–D21 P1) | Lead, Opportunity (Sales Lite); Customer cơ bản | `opportunity.*` → Metric Store (pipeline coverage, win rate); phần lớn P1 |
| Sản phẩm & thực thi | Product, Feature, Project, Milestone, Task, Workload | Chuyển chiến lược thành việc thực thi được đo (D11 P0) | Project, Milestone, Task, Workload | `task.overdue`, `task.created`; Task là đích của Decision→ActionItem và của IDP commit |
| Chiến lược | Strategy, StrategicPillar, StrategicObjective, Initiative | Cây mục tiêu chiến lược, liên kết chiến lược↔thực thi (D07 cơ bản P0) | Strategy, StrategicObjective, Initiative | Strategy Execution Index (chỉ số, skeleton §10); liên kết tới KPI/OKR |
| KPI | KPI, KPITarget, KPIMeasurement, KPIEvaluation, Metric | Đo lường hiệu quả theo mục tiêu (D08 P0) | KPI, KPITarget, KPIMeasurement, KPIEvaluation, Metric | `kpi.measured`, `kpi.below_threshold`; KPIMeasurement là SourceRef cho grounding AI |
| OKR | Objective, KeyResult, KRMeasurement | Mục tiêu & kết quả then chốt theo chu kỳ (D09 P0) | Objective, KeyResult, KRMeasurement | `okr.at_risk` (UC-04); KRMeasurement là nguồn grounding |
| Hiệu suất | PerformanceCycle, PerformanceReview, CheckIn | Theo dõi hiệu suất qua check-in (D10 check-in P0, review P1) | CheckIn (P0); PerformanceCycle | CheckIn phát event feed hiệu suất; PerformanceReview chứa trường Mật |
| Họp & quyết định | Meeting, MeetingTranscript, MeetingSummary, Decision, ActionItem | Biến họp/transcript thành quyết định & việc (D12 từ transcript P0) | Meeting, MeetingTranscript, MeetingSummary, Decision, ActionItem | UC-02/UC-06: Transcript → Summary → Decision → ActionItem → Task; `document.committed` |
| Rủi ro & tuân thủ | Risk, RiskAssessment, Mitigation, Policy, Control, Evidence, Finding | Nhận diện & giảm thiểu rủi ro, lưu bằng chứng (D25 Risk P1, D24 Governance P2) | (P1 — ghi backlog 09) | `risk.detected` (observe từ event khác); Evidence nối lineage tới SourceDocument |
| Tài chính | Budget, CostCenter, Revenue, Expense, Invoice, Payment, CashBalance | Dòng tiền, công nợ, ngân sách (D15 Finance Lite P0) | Invoice, Payment, Revenue, Expense, CashBalance, Budget (Lite) | `invoice.created`; Invoice là đích IDP commit (UC-08 P1); số tiền = trường trọng yếu |
| Tri thức | Document, Knowledge, Report | Bộ nhớ doanh nghiệp & báo cáo (D14 Knowledge, D28 Reporting cơ bản P0) | Document, Report (Knowledge/RAG tối thiểu) | Report dùng số từ Metric Store + trích dẫn lineage (FR-RPT-02) |
| Data Capture | SourceDocument, DocumentPage, DocumentType, ExtractionSchema, ExtractionJob, ExtractedField, ExtractionReview, ValidationRule, ImportBatch, DataLineage | Nhập liệu không ma sát → trích xuất → review → ghi (D03 P0, chi tiết ở 04) | Toàn bộ (lõi IDP P0) | **Nguồn gốc của mọi lineage**: SourceDocument→ExtractionJob→ExtractedField→Review→Business Record; `document.committed` |
| AI | AIAgent, AITool, AIToolCall, AIRecommendation, AIDecision, AIAudit, AIEvaluation, AIBudget | Hạ tầng AI có thể audit & kiểm chi phí (D26 P0, chi tiết 02 §9/07) | AIAgent, AITool, AIToolCall, AIRecommendation, AIDecision, AIAudit, AIEvaluation, AIBudget | AIToolCall.result là SourceRef cho grounding (FR-AIQ-01); AIDecision/AIAudit cho autonomy L0–L3 |
| Workflow | Workflow, WorkflowStep, ApprovalRequest, Notification | Duyệt & thông báo (D04 cơ bản + D05 P0) | ApprovalRequest, Notification (Workflow cơ bản) | ApprovalRequest gắn autonomy L2 (chờ xác nhận); Notification là đích của alert/event |

## 4. Quan hệ cốt lõi (BRD §13.3)

Sơ đồ khái niệm dưới đây mô tả 5 chuỗi quan hệ cốt lõi với **cardinality mức khái niệm** (`1` = một, `N`/`*` = nhiều); cardinality & khóa chi tiết chốt ở đợt code (R-DEC-09):

```text
[1] Cây tổ chức (effective-dated — FR-DATA-07/FR-ORG-04)
Organization 1─N Department 1─N Team 1─N Employee
                                   Employee N─1 Position
                                   Employee N─1 Role

[2] Chiến lược → thực thi (liên kết chiến lược↔thực thi — BO-03)
Strategy 1─N StrategicObjective 1─N {KPI | OKR}
StrategicObjective 1─N Initiative 1─N Project 1─N Task N─1 Employee
KPI 1─N KPITarget ; KPI 1─N KPIMeasurement ; Objective 1─N KeyResult 1─N KRMeasurement

[3] Họp → quyết định → việc (UC-02 / UC-06)
Meeting 1─1 MeetingTranscript 1─1 MeetingSummary
Meeting 1─N Decision 1─N ActionItem 1─1 Task ──► Deadline ──► Calendar

[4] Data Capture → bản ghi nghiệp vụ (lineage — FR-DATA-04)
SourceDocument 1─N DocumentPage
SourceDocument 1─N ExtractionJob 1─N ExtractedField N─1 ExtractionReview
ExtractedField ──► (qua Review, 1 txn/tài liệu) ──► BusinessRecord {Invoice | Task | KPIMeasurement | ...}
DataLineage N─1 BusinessRecord ; DataLineage N─1 ExtractedField ; DataLineage N─1 DocumentPage

[5] Vòng lặp AI (AI Operating Loop — BRD §17.5)
Data ──► AI(Insight) ──► Recommendation ──► Decision ──► Action ──► Measurement ──► Feedback
AIToolCall 1─1 (result = SourceRef) ──► {Metric | KPIMeasurement}   # grounding FR-AIQ-01
```

**Giải thích chuỗi lineage (trọng tâm P0):** một con số trên dashboard (ví dụ Doanh thu T9) trỏ tới một `Metric`/`KPIMeasurement`; giá trị đó lần ngược qua `DataLineage` về `BusinessRecord` (Invoice/Revenue) → `ExtractedField` (nếu nhập từ tài liệu) → `DocumentPage` của `SourceDocument`, kèm người/agent nhập và lịch sử `version`. Đây là hiện thực của FR-DATA-04 + BRD-P01/P05 và tiêu chí US-CEO-007.

## 5. Phân vùng lưu trữ theo domain (ánh xạ sang schema)

AI-EOS 28 domain / 5 lớp, hiện thực hóa theo **R-DEC-06 (Modular Monolith)** + **R-DEC-10** (ID theo BRD + ánh xạ `main`): nhóm entity ánh xạ sang schema PostgreSQL theo domain. Bảng ánh xạ 13 nhóm → schema: **tổ chức (Organization/BusinessUnit/Department/Team/Employee/Position) → `hr`** (R-DEC-24 — giữ nơi các bảng đang ở, không di chuyển); admin/security (user, role, refresh token) → `auth`, audit/setting → `platform`; data capture → `idp`; AI → `ai`; workflow → `platform`; finance → `finance`; sales/customer/partner → `sales`; hr → `hr`; product/engineering → `product`; risk/governance → `risk`; strategy/kpi/okr/performance/meeting/task → `execution`; knowledge/report → `platform`/`dashboard`. Chi tiết schema chốt ở đợt code (R-DEC-09).

## 6. AI entity & grounding

Mọi con số AI đưa ra phải khớp một `AIToolCall` result hoặc `Metric`/`KPIMeasurement` (SourceRef) — **grounding** (FR-AIQ-01, BRD-P05 "không bịa số"). Không khớp → gỡ số + warning; thiếu dữ liệu → trả rõ "chưa có dữ liệu" (SOURCE-UIUX §208) thay vì bịa. `AIToolCall`, `AIAudit`, `AIDecision`, `AIRecommendation`, `AIEvaluation`, `AIBudget` ghi đủ cho audit AI (02 §9):
- `AIToolCall` — mỗi lượt gọi tool: tool, input (đã lọc PII), result, nguồn; là bằng chứng của mọi số AI đưa ra.
- `AIRecommendation` / `AIDecision` — khuyến nghị 9 phần (Observation→…→Action, skeleton §9) và quyết định (người hoặc AI theo autonomy L0–L3); gắn undo ≥24h cho hành động L3.
- `AIAudit` — vết audit đầy đủ chuỗi OBSERVE→…→VERIFY→LEARN; `AIEvaluation` — đánh giá chất lượng/độ chính xác; `AIBudget` — chi phí AI theo kỳ (chặn khi vượt ngân sách).

`ENT-DataLineage` nối Business Record → ExtractedField → SourceDocument/trang; khi AI trích dẫn một con số, source chip trỏ qua cùng lineage này (một đường truy nguồn duy nhất cho cả người và AI).

## 6bis. Metric Store / Semantic layer (FR-DATA-06)

Metric Store là **nơi định nghĩa chỉ số một lần**, chia sẻ cho dashboard, Report và AI tool — chống tình trạng "mỗi nơi một công thức". Mỗi định nghĩa (mức khái niệm) gồm: tên, mô tả, **công thức**, **nguồn dữ liệu**, **bộ lọc**, **owner**, đơn vị, hướng tốt/xấu, tần suất/kỳ, ngưỡng cảnh báo. Giá trị tính sẵn (precompute qua consumer của event backbone) lưu vào `Metric`/`KPIMeasurement`, không tính lúc request.

- **Semantic layer:** KPI tham chiếu công thức trong Metric Store (BRD §8: "Formula (tham chiếu Metric Store)") — một KPI không tự định nghĩa lại công thức.
- **Dùng chung:** dashboard (03), Report (FR-RPT-02 "dùng số liệu từ Metric Store, có trích dẫn"), và AI tool đọc **cùng** giá trị → mọi kênh nhất quán.
- **Lineage bắt buộc:** mỗi metric có `lineage_url` để click ra nguồn (FR-DATA-04, BRD-P01).
- Mã `METRIC-<NHÓM>-NN` (NHÓM ∈ FIN/CUS/OPS/PPL/STR/DQ) + công thức cụ thể **cấp ở 03** theo nhóm chỉ số (skeleton §10); 05 chỉ chốt vai trò entity `Metric` trong semantic layer. Field-level của `Metric` chốt ở đợt code (R-DEC-09).

## 6ter. Lịch sử & effective-dated (FR-DATA-07) — scope P0

Để trả lời "tại thời điểm X thì sao", entity quan trọng lưu lịch sử thay đổi theo thời điểm hiệu lực (effective-dated). **Phạm vi P0 (tối thiểu):**
- **Cơ cấu tổ chức** (Organization/Department/Team/Employee–Position–Role) — bám FR-ORG-04: truy được sơ đồ tổ chức tại một mốc quá khứ; phục vụ UC-07 onboarding và báo cáo lịch sử.
- **KPITarget** — target có thể đổi giữa kỳ; cần biết target "đang hiệu lực" tại thời điểm đo để KPIEvaluation đúng.

**Mô hình đã chốt cho cơ cấu (M1.2, §2.4):** cột `valid_from`/`valid_to` (nửa mở, `valid_to NULL` = hiện hành) trên `hr.organizations`, `hr.departments`, `hr.teams` và bảng `hr.employee_assignments`; KPITarget chốt ở M1.4.

Entity còn lại (ngoài P0) dùng `version` + audit để truy vết thay đổi; mở rộng effective-dated sang entity khác và **mô hình lưu lịch sử cụ thể** (bitemporal, bảng history hay cột valid_from/valid_to) chốt ở đợt code (R-DEC-09). Giữ nguyên tắc: không ghi field-level DB ở vòng docs này.

## 7. Event backbone (FR-DATA-05)

Event backbone biến mọi thay đổi nghiệp vụ thành dòng sự kiện để AI **quan sát real-time** (bước OBSERVE của AI Operating Loop) và để metric tính sẵn. Event mẫu: `invoice.created`, `kpi.measured`, `task.overdue`, `document.committed`, `kpi.below_threshold`, `okr.at_risk`, `risk.detected`.

**Envelope (mức khái niệm):** `event_id, event_type, occurred_at, version, correlation_id, tenant_id, payload` — `tenant_id` để consumer chạy đúng tenant context (R-DEC-21; field-level ở §2.3); payload **không chứa PII** (đồng bộ chính sách classification §2.1). `correlation_id` nối event về request/lineage để truy nguồn.

**Nguyên tắc nghiệp vụ (hiện thực chốt ở 07/10, R-DEC-09):**
- Event phát **cùng transaction** với ghi dữ liệu (nguyên tắc outbox) → không mất/không phát nhầm event khi rollback.
- Consumer xử lý **idempotent** (một event xử lý một lần cho mỗi consumer) → không nhân đôi metric/alert khi retry.
- Breaking change schema event → tạo phiên bản mới (ví dụ `_v2`), không phá consumer cũ.

**Event → tác động (mẫu P0):** `kpi.below_threshold`/`okr.at_risk` → insight + ApprovalRequest (UC-03/UC-04); `task.overdue` → Notification + feed CEO; `document.committed` → cập nhật Business Record + metric liên quan; `invoice.created` → cập nhật công nợ/dòng tiền (chuẩn bị cho UC-08 P1).

Danh mục event đầy đủ (mã `EVT-*`) + cặp publish/consume chốt ở **10 §8** (đợt code). *(Spec lock M1.3–M1.6, đề xuất)* Tên event ở đây là nhãn khái niệm BRD; mã phát thật theo registry code `<module>.<entity>_<verb>` (vd `kpi.measured` → `execution.kpi_measured`) — bảng ánh xạ ở 10 §9.2.

## 8. Open questions
- OQ-05-01: Quy ước `source` (BRD) vs hậu tố `*_source` (DEC-154 `main`) — giữ `source` theo BRD ở docs; chốt quy ước cột khi tái dùng code ở đợt code (R-DEC-09).
- OQ-05-02: Tập entity chính xác cho MVP P0 (tập con của §13.2) — theo R-DEC-05 (phủ tập P0); §3 đã nêu entity P0 chính per nhóm, danh sách field-level cụ thể chi tiết hóa ở đợt code (R-DEC-09).
- OQ-05-03: effective-dated (FR-DATA-07) cho entity nào ở MVP — §6ter chốt tối thiểu cơ cấu tổ chức (FR-ORG-04) + KPITarget; mở rộng & mô hình lưu lịch sử (bitemporal / valid_from-to) chốt ở đợt code (R-DEC-09).
- OQ-05-04: DQ Score (FR-DATA-02) — công thức tổng hợp 4 chiều (đầy đủ/chính xác/kịp thời/nhất quán) per-domain + ngưỡng tươi dữ liệu per-domain (FR-DATA-03) chốt ở 03 (`METRIC-DQ-*`); chưa gán số ở vòng này.
- OQ-05-05: Data classification mặc định per nhóm (§2.1) là đề xuất mức khái niệm; override per-field + chính sách LLM theo mức chốt ở 07/đợt code (R-DEC-09). M1.2: override per-field cho Tổ chức/Identity ở §2.4 (R-DEC-34).
- OQ-05-06 (M1.2) — ĐÃ CHỐT (human 2026-10-23, theo đề xuất): BusinessUnit (FR-ORG-01) — hoãn; khối biểu diễn bằng `departments.parent_id`. Cần entity riêng khi có báo cáo theo khối khác cây phòng ban → DEC.
- OQ-05-07 (M1.2) — ĐÃ CHỐT (human 2026-10-23, theo đề xuất): Không chồng khoảng phân công bằng `EXCLUDE USING gist` cần extension PostgreSQL `btree_gist` (contrib, không phải package mới) — M1.2 dùng partial unique + kiểm ở service dưới khóa dòng; bật extension = hạ tầng mới → chờ human.
- OQ-05-08 (M1.2) — ĐÃ CHỐT (human 2026-10-23, theo đề xuất): Tái cấu trúc cấp phòng ban (đổi `parent_id`) chưa effective-dated — cây `as_of` quá khứ dùng `parent_id` hiện tại. Cần bảng `department_versions` nếu UC-07/báo cáo đòi đúng cây cha tại quá khứ.
- OQ-05-09 (M1.3): `tasks.assignee_id` lưu `hr.employees.id` (R-DEC-41) trong khi `owner_id` KPI/OKR giữ `auth.users.id` — **phương án đề xuất — chọn nếu human duyệt:** giữ hai ngữ nghĩa như hiện tại ở M1 (scope so cả `employee_id` và `user_id`); hợp nhất định danh người xét ở M2.x.
- OQ-05-10 (M1.4): StrategicObjective bảng riêng (R-DEC-50) hay `level=strategic` trên Objective — **phương án đề xuất — chọn nếu human duyệt:** bảng riêng `execution.strategic_objectives`.
- OQ-05-11 (M1.5): Retention `idp.import_rows` — **phương án đề xuất — chọn nếu human duyệt:** job `idp.purge_import_rows` hằng ngày, idempotent, xóa sau hết cửa sổ undo 7 ngày.
- OQ-05-12 (M1.5): Lưu lương từ import #4 — **phương án đề xuất — chọn nếu human duyệt:** ghi `salary_history` qua `add_salary` chỉ khi người commit có quyền đọc/ghi mức 4 (CEO, DIR-O); ngược lại bỏ cột + cảnh báo; cột mức 4 không bao giờ gửi LLM.

## Version
- **Version:** 1.2.0 (current)
- **Last updated:** 2026-10-23
- **Maintainer:** @CyEyes
- **Change 1.4.0 (đề xuất — Spec lock M1.3–M1.6, chờ human duyệt):** §2.5 field-level M1.3 (task `parent_task_id`/`source_ref`, `task_dependencies`, `projects.initiative_id`, `approval_rules` — migration `0014`/`0015`); §2.6 M1.4 (`strategies`, `strategic_objectives`, KPITarget effective-dated, KPIMeasurement lịch sử, `kpi_evaluations`, KR measurement/at-risk — `0016`/`0017`); §2.7 M1.5 (`import_batches`/`import_rows`, `document_actions`, schema/rule, incident, `data_lineage` mở rộng — `0018`/`0019`); §2.8 M1.6 (`tool_call_logs`/`model_call_logs` + `request_id`/`tenant_id`, agent, autonomy policy, onboarding state — `0020`, `0021` để trống). §7 ghi chú ánh xạ tên event BRD ↔ mã code. Open questions: thêm OQ-05-09..12.
- **Change 1.3.0 (đề xuất — Spec lock M1.2, R-DEC-24/32/33/34, chờ human duyệt bước S):** §2.4 field-level M1.2: `hr.organizations` (ENT-Organization, effective-dated), `hr.departments` + `organization_id`/`valid_from`/`valid_to` + unique `code` theo tenant, `hr.teams` + `valid_from`/`valid_to`, `hr.employee_assignments` (ENT-EmployeeAssignment, nửa mở, tối đa một hiện hành/NV, không chồng khoảng; cột cache trên `employees`), `platform.notifications` + `tenant_id`/`email_status`/`email_sent_at`/`email_attempts`, `platform.notification_preferences` (mới), bảng classification per-field mức 3/4 cho mask serializer (T-615); §6ter ghi mô hình `valid_from/valid_to`; thêm OQ-05-06..08.
- **Change 1.2.0 (human duyệt 2026-10-23 — Spec lock M1.1):** §2.3 field-level M1.1: tenant context + `tenant_id` trên `platform.outbox_events` (R-DEC-21); §5 ánh xạ tổ chức → `hr` (R-DEC-24); §7 envelope thêm `tenant_id`.
- **Change 1.1.0 (code round — human ủy quyền R-DEC-14, 2026-10-23):** Thêm §2.2 field-level đợt code Phase 1: `tenant_id UUID NOT NULL` + `TenantMixin` (R-DEC-13); `auth.role_code` enum 7 giá trị v3 (`CEO/DIR/MGR/EMP/REV/ADM/AI`) + bảng gộp 10→7 (R-DEC-12). Chi tiết schema/migration ở code; mọi thay đổi reversible.
- **Change 1.0.0 (promote):** Promote tài liệu AI-EOS lên CHÍNH THỨC Aureon v3; di chuyển vào vị trí docs chuẩn; v2.1 archived (docs/_archive/v2.1/).
- **Change 0.3.0:** Mở rộng lên spec-level P0 (docs-first R-DEC-09 — không field-level DB): mỗi FR-DATA-01..08 thêm mô tả hành vi + tiêu chí chấp nhận; §2.1 data classification per nhóm entity; §3 bổ sung vai trò nghiệp vụ + entity P0 chính + liên kết lineage/event cho 13 nhóm; §4 sơ đồ quan hệ cốt lõi với cardinality mức khái niệm + giải thích chuỗi lineage; §6 mở rộng AI entity/grounding; §6bis Metric Store/Semantic layer; §6ter effective-dated scope P0; §7 event backbone (envelope, nguyên tắc outbox/idempotent, event→tác động); thêm OQ-05-04/05.
- **Change 0.2.0:** Chốt Q1–Q6 (R-DEC-05..10) — cập nhật trạng thái quyết định, đóng OQ liên quan; phạm vi docs-first P0.
- **Change 0.1.0:** Viết lại 05 theo AI-EOS — Data Foundation FR-DATA-01..08, trường chung, 13 nhóm entity BRD §13.2, quan hệ cốt lõi, ánh xạ nhóm→schema, AI entity/grounding, event backbone.
