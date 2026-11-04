# M8 — Audit, kế hoạch CRM (BRD_Newfeature) và R-DEC-171

> Nhánh `v3/m8-crm` (từ `v3/m7-records`). Ngày 2026-11-04. Chưa push, chưa merge.
> **M8 Phase 1: DEPLOYED** lên stack chính (compose `docker-compose.full.yml`) 2026-11-04 17:42 ICT, mã = HEAD `6361081`,
> không migration (DB `0027_external_event_link_c19`) — kết quả §8.1. R-DEC-168, R-DEC-176, lịch sử GitLeaks vẫn **OPEN** (§10).
> Nguồn yêu cầu: `docs/BRD_Newfeature.md` (CRM – Sales Management, ~120 yêu cầu / 10 phân hệ). ID dưới đây là
> `CRM-*` (BRD tự dùng `ACT-001…`, `DEC-001…`, `NFR-001…` — trùng registry Aureon, nên không dùng lại).

## 1. Audit hiện trạng M7

| Mục | Kết quả |
|---|---|
| Nhánh / commit | `v3/m7-records` @ `44f522b` — 24 commit trước `origin/main`, chưa push |
| Stack chính | api / worker / beat image `7d1495617631`, web `a54b7ba12206` = HEAD M7 (đã đối chiếu từng file sau deploy), 10/10 healthy |
| Chức năng M7 | `/business/{finance,sales,hr}/records` CRUD theo role — giữ nguyên, M8 chỉ bổ sung liên kết chi tiết + quy tắc duyệt |
| Working tree | thay đổi của người dùng giữ nguyên: xóa `docs/_archive/v2.1/` (17 file), `docs/BRD_Newfeature.md`, `.prompt/` |

## 2. Đối chiếu BRD_Newfeature ↔ Aureon

Tài liệu chuẩn (`docs/_reference/SOURCE-BRD-v1.1.md` §9.3–9.7, 01, TRACEABILITY-SKELETON): D17 **Sales Pipeline Lite = P0**,
CRM đầy đủ (Lead/Account/Contact/Activity), D18 Customer 360, D21 Contract = **P1**. R-DEC-89/90/95 khóa Sales theo mô
hình Client/Deal (Client = Lead/Account, Deal = Opportunity, không endpoint/event mới). → Quyết định 2026-11-04
(R-DEC-175): làm ngay phần dựng được trên mô hình sẵn có; thực thể mới = R-DEC-176 (chờ duyệt).

### 2.1. Truy vết yêu cầu → code → test

| Phân hệ BRD | Yêu cầu | Trạng thái | Code | Test |
|---|---|---|---|---|
| Pipeline | PIPE-003 Kanban, 005 chuyển giai đoạn, 007 kiểm tra (tiến/không lùi, thua cần lý do), 008 giá trị/giai đoạn, 009 có trọng số | **Đã làm** | `features/crm/PipelineBoard.tsx`, `StageMove.tsx`, `crm.ts canMoveTo` | TC-M8-03, TC-M8-04 |
| Pipeline | PIPE-001/002/006 nhiều pipeline + cấu hình giai đoạn + xác suất mặc định; 010/011 aging, cảnh báo deal đứng | Chờ R-DEC-176 (cần cấu hình + hoạt động) | — | — |
| Opportunity | OPP-001..004 tạo/sửa/danh sách/chi tiết, 007/008 giá trị + xác suất, 013 lịch sử | **Đã làm** (M7 CRUD + M8 chi tiết, tiến trình, lịch sử) | `DealDetailView.tsx`, records `deals` | TC-M7-02, TC-M8-04 |
| Opportunity | OPP-005 BANT/MEDDIC, 006 nhiều sản phẩm, 009–012, 014 Win/Loss, next action bắt buộc, slippage | Chờ R-DEC-176 | — | — |
| Account | ACC-001..004 (CRUD), 007 liên hệ (1 người), 008 cơ hội, hợp đồng | **Đã làm** (Account 360) | `ClientDetailView.tsx` | TC-M8-04 |
| Account | ACC-005/006 phân loại/phân cấp, 009 hoạt động, 010 doanh thu cộng dồn, 011 import | Chờ R-DEC-176 / backlog | — | — |
| Lead, Contact, Activity | LEAD-*, CONT-*, ACT-* | Chờ R-DEC-176 (thực thể mới) | — | — |
| Funnel | FUN-001/002/003 phễu theo giai đoạn, chuyển đổi, rơi rụng (phương pháp A) | **Đã làm** (giai đoạn cơ hội; giai đoạn Lead cần R-DEC-176) | `SalesInsights.tsx`, `crm.ts funnel` | TC-M8-03/04 |
| Forecast | FC-001/002 kỳ + dự báo có trọng số (loại thua, theo ngày chốt dự kiến) | **Đã làm** | `crm.ts forecast` + `/sales/pipeline?period=` | TC-M8-03/04 |
| Forecast | FC-003/004 Category / Commit, 008 điều chỉnh, 009 snapshot, 010 Forecast vs Actual | Chờ R-DEC-176 | — | — |
| Performance | PERF-001..004 chỉ tiêu + đạt; 005 xếp hạng; 007 win rate | **Đã làm** (M7 chỉ tiêu + M8 xếp hạng theo người) | `SalesInsights.tsx`, `/sales/performance` | TC-M8-04 |
| Dashboard | DASH-001/002/003/005/007 (KPI, pipeline, hiệu suất, deal sắp đến hạn) | **Một phần** — trang KD + thẻ rủi ro trên Kanban; xuất Excel/PDF chưa | `/business/sales` | TC-M8-04 |
| Cross-cutting | RBAC + data scope, audit mọi thay đổi | **Đã làm** trên API sẵn có (audit `sales.*`) | — | TC-M7/M8 |

## 3. R-DEC-171 — root cause, phương án, kết quả

| | Root cause | Quyết định (human 2026-11-04) | Đã triển khai |
|---|---|---|---|
| A. Vai trò / quyền | Quyền JWT đọc từ `auth.roles`, nhưng seed ghi đè từ `permission_matrix.py` mỗi lần API khởi động → sửa DB sẽ mất | R-DEC-174: ma trận chỉ đọc + gán vai trò | SCR-54 nhãn dễ hiểu theo hành động, ghi chú khối, liên kết gán vai trò |
| B. Duyệt tuyển dụng | Code v2.1 chỉ cho CFO duyệt (trái 02 §7), CFO lại không mở được kế hoạch (khối O) | R-DEC-173: HR-DIR khối O hoặc CEO qua engine phê duyệt | Rule `RULE-hiring_plan`, hook duyệt + **hook từ chối**, EP-HR-09/10, hộp `/work/approvals` hiểu `hiring_plan` |
| C. Hóa đơn OUT của CFO | OUT bắt buộc `client_id`; danh sách khách hàng là bản ghi khối C | R-DEC-172: gắn khách hàng theo MST | `core/client_directory` + `sales` đăng ký; không mở quyền đọc |

## 4. Danh sách R-DEC

| R-DEC | Nội dung | Trạng thái |
|---|---|---|
| 172 | Hóa đơn OUT theo MST | resolved |
| 173 | Duyệt tuyển dụng HR-DIR / CEO qua engine | resolved |
| 174 | Ma trận vai trò chỉ đọc + gán vai trò | resolved |
| 175 | CRM giai đoạn 1 trên mô hình sẵn có | resolved |
| **176** | **Thực thể CRM mới (đề xuất §5)** | **open — cần duyệt trước migration** |

## 5. Đề xuất R-DEC-176 — thực thể CRM mới (chưa triển khai)

Nguyên tắc: migration **chỉ thêm** (không xóa/đổi cột cũ), giữ `clients`/`deals` làm Account/Opportunity, cập nhật 05 + 10 + 02 trước khi code.

| Bảng (schema `sales`) | Trường chính | Ghi chú |
|---|---|---|
| `leads` | code, company_name, full_name, job_title, email, phone (≥1 kênh), industry, lead_source, need, budget, score, status, owner_id, next_action(+date), converted_client_id / contact_id / deal_id | Vòng đời New→Contacted→Engaged→Qualified→Converted; Nurturing; Disqualified (kết thúc) |
| `contacts` | client_id, first/last name, job_title, department, email, phone, roles[] (Decision Maker, Economic Buyer, …), decision_authority, influence_level, owner_id | Thay cột liên hệ phẳng của `clients` (dữ liệu cũ chuyển sang 1 contact, cột cũ giữ) |
| `deal_contacts` | deal_id, contact_id, role | Buying committee |
| `activities` | type (Call/Email/Meeting/Demo/Workshop/POC/Proposal/Follow-up/Other), subject, description, client_id / contact_id / deal_id, owner_id, start/end, status (Planned/Completed/Cancelled), outcome, next_action | Timeline Account/Opportunity; nhắc việc qua notification |
| `pipelines`, `pipeline_stages` | tên, thứ tự, xác suất mặc định, tiêu chí thoát, ngưỡng aging | `deals.pipeline_id` (mặc định New Business) |
| `deals` (+cột) | next_action, next_action_date, budget_status, pain_point, forecast_category, win_loss_reason (enum) | BANT + forecast category |
| `forecast_snapshots` | kỳ, owner/team, pipeline/weighted/commit/best_case, locked_at | Không ghi đè khi đã khóa |
| `sales_targets` (+cột) | target_type (Revenue/Deals/Activities), status (Draft/Approved/Active/Closed) | Duyệt chỉ tiêu qua engine phê duyệt |

### 5.1. Nguyên tắc nghiệp vụ đã thống nhất (human 2026-11-04 — R-DEC-176 vẫn OPEN)

| Chỉ số / quy tắc | Định nghĩa thống nhất | Ánh xạ dữ liệu (đề xuất) | Khác hiện trạng |
|---|---|---|---|
| Win Rate | Số cơ hội **thắng** ÷ tổng cơ hội **đã đóng** (thắng + thua) × 100 | `count(closed_won) / count(closed_won ∪ closed_lost)` trong kỳ theo `closed_at` | **Đã khớp** `calculations.win_rate_pct` (theo số) — giữ |
| Forecast Accuracy | So **forecast đã khóa** của kỳ với **doanh thu thực tế** của kỳ | `forecast_snapshots.locked_at` (bất biến sau khóa) ↔ doanh thu thực tế (xem 5.2-a) | Mới (cần snapshot) |
| Slippage | **Số ngày** ngày chốt dự kiến bị lùi | mỗi lần `expected_close_date` tăng: `new − old` (ngày) → `deal_close_date_changes` (cũ, mới, người, lúc, lý do) | Mới (hiện chỉ có audit) |
| Average Deal Size | Giá trị trung bình các cơ hội **thắng** | `avg(deal_value) where closed_won` | **Đã khớp** `analytics.avg_deal_value` (chỉ cơ hội thắng) — giữ |
| Sales Cycle | Thời gian từ **tạo** đến **thắng** | `closed_at − created_at` (ngày) của cơ hội thắng | **Đã khớp** `analytics.avg_sales_cycle_days` — giữ |
| Nhiều sản phẩm | Một cơ hội có nhiều sản phẩm | bảng `deal_products` (deal_id, product_id, số lượng, đơn giá, tiền tệ, thành tiền); `deals.deal_value` = tổng dòng | Thay `deals.product_id` đơn (giữ cột cũ, ngừng ghi) |
| Trùng Lead / Contact | **Cảnh báo**, người có quyền **xác nhận** để lưu tiếp | API trả danh sách nghi trùng (như `similar_clients`); lưu khi có cờ xác nhận + audit `*.duplicate_confirmed` | Hiện Client: trùng tên/MST **chặn** — giữ cho Client |
| Mã định danh | Tự sinh, duy nhất | sequence theo loại + unique index (`lead_code`, `contact_code`, `deal_code`, `activity_code`) | Mới |
| Tiền tệ | Lưu **mã tiền tệ + giá trị gốc** | cột `currency` + số tiền nguyên (đơn vị nhỏ nhất) đã có trên deals/contracts; giữ cho bảng mới | Không cộng khác tiền tệ khi chưa quy đổi (BRD L602) |

### 5.2. Cần xác nhận trước migration

| # | Câu hỏi | Vì sao chặn | Đề xuất mặc định |
|---|---|---|---|
| a | "Doanh thu thực tế" cho Forecast Accuracy là **giá trị cơ hội thắng** (bookings) hay **doanh thu ghi nhận** ở Tài chính (`finance.revenues`)? Công thức: `1 − |thực tế − forecast| ÷ thực tế`? Kỳ khóa (tháng/quý), ai khóa? | Quyết định nguồn + bảng snapshot | Bookings của kỳ; công thức trên; khóa theo quý bởi DIR khối C / CEO |
| b | Slippage: tổng số ngày lùi / cơ hội hay trung bình mỗi lần lùi; ngưỡng cảnh báo? | Định nghĩa chỉ số + alert | Tổng ngày lùi / cơ hội; cảnh báo khi lùi sang kỳ sau (BR-017) |
| c | Danh sách giai đoạn chuẩn (BRD có 3 phiên bản) và ánh xạ enum hiện có `lead/qualified/proposal/negotiation/closed_won/closed_lost` | Đổi enum/cấu hình pipeline ảnh hưởng dữ liệu cũ | Giữ 6 giai đoạn hiện có làm pipeline "New Business" mặc định; pipeline khác cấu hình thêm |
| d | Tiêu chí nghi trùng (email / điện thoại / MST / tên gần giống) và **ai** được xác nhận | Quyền xác nhận = RBAC | Email hoặc điện thoại trùng chính xác + tên ≥ 0,8; người có `sales:write` trong phạm vi |
| e | Định dạng mã (vd `LD-000001`, `OPP-000001`) | Unique index + hiển thị | `LD-`, `CT-`, `OPP-`, `ACT-` (tránh trùng tiền tố `ACT-*` Action Registry → dùng `SA-` cho Sales Activity) |
| f | Quy đổi tiền tệ: nguồn tỷ giá, tiền tệ báo cáo, thời điểm quy đổi | Tổng hợp dashboard | VND là tiền báo cáo; bảng tỷ giá do Tài chính nhập; quy đổi theo ngày chốt |
| g | Lead tách khỏi Client: client `prospect` hiện có chuyển thành Lead hay giữ? Liên hệ phẳng của client chuyển sang `contacts`? | Di trú dữ liệu cũ (chỉ thêm, không xóa) | Giữ client `prospect`; sao 1 contact từ cột phẳng (cột cũ giữ nguyên) |
| h | Vai trò Sales Executive / Presales / Marketing ánh xạ vào 7 role Aureon; nhân viên kinh doanh (EMP) hiện **không** có quyền sales | Thay đổi RBAC → DEC riêng | Chưa đổi; chỉ DIR khối C / MGR / CEO như hiện tại |
| i | Hoạt động bán hàng tái dùng Task/Lịch (execution) hay bảng `activities` riêng | Tránh trùng nghiệp vụ | Bảng riêng + tạo Task/Lịch khi có "next action" |
| j | Duyệt chỉ tiêu (Draft→Approved): người duyệt | Engine phê duyệt + RBAC | `RULE-sales_target`: CEO |

Nguyên tắc chung giữ nguyên: migration **chỉ thêm**, cập nhật 05/10/02 trước khi code, không đổi permission matrix nếu chưa có DEC.

## 6. Báo cáo kiểm chứng M8 Phase 1 (2026-11-04, stack cô lập: API :4600 + worker + beat + web production :3600, DB `aureon_m4`, SMTP → Mailpit)

> §6–§7 = kiểm chứng chức năng + regression **trước deploy**, trên stack cô lập (có ghi dữ liệu thử vào `aureon_m4`).
> Kiểm chứng **sau deploy** trên stack chính (chỉ đọc, không ghi DB) ở §8.1 — hai bộ bằng chứng tách biệt.

| Hạng mục | Bằng chứng | Kết quả |
|---|---|---|
| CFO tạo hóa đơn OUT theo MST | E2E: CFO nhập MST của khách hàng do DIR KD tạo → hóa đơn hiện trong danh sách; DB: 1 hóa đơn OUT có `client_id`, MST hóa đơn = MST khách hàng; API: MST lạ → 422 trường MST; CFO GET `/sales/clients` → 403 | PASS |
| Duyệt / từ chối kế hoạch tuyển dụng qua engine | E2E: HR-DIR trình → CEO duyệt ở `/work/approvals` → "Đã duyệt"; integration: từ chối ở hộp phê duyệt → `rejected` + lý do; CFO → 403 SCOPE; CEO/MGR ở EP-86 → 403 ROLE; người duyệt ≠ người tạo; **kế hoạch trình trước M8 (chưa có yêu cầu) vẫn duyệt được** (test mới); DB: trạng thái yêu cầu khớp trạng thái kế hoạch (APPROVED↔approved, PENDING↔submitted) | PASS |
| Ma trận vai trò / quyền | E2E: nhãn "Tài chính · Tạo / sửa / lưu trữ", "Nhân sự · Phê duyệt", ghi chú khối, liên kết `/admin/users`; permission matrix không đổi | PASS |
| CRM Pipeline / Opportunity / Account 360 | E2E: Kanban chuyển `lead → qualified`, chi tiết có 2 bước lịch sử, thua bắt buộc lý do, Account 360 liệt kê cơ hội; DB: 3 dòng lịch sử giai đoạn | PASS |
| Funnel / Forecast / Performance | E2E: 5 bước phễu, dự báo có giá trị, bảng xếp hạng hiện cho DIR KD, ẩn với CFO; unit: công thức phễu / WP / rủi ro | PASS |
| RBAC | CFO: Kanban = trang 403, không xếp hạng; REV/EMP không có route CRM; CEO không chuyển giai đoạn (scope `t`) | PASS |
| Audit | DB (30 phút chạy): `finance.invoice_create`, `sales.client_create`, `sales.deal_create`, `sales.deal_stage_change`, `hr.hiring_plan_submit/approve`, `platform.approval_requested/decided` | PASS |

## 7. Báo cáo regression

| Gate | Kết quả |
|---|---|
| Backend pytest đầy đủ (không tiến trình nào khác dùng DB thử) | **1450 passed, 0 failed**; + test kế hoạch trước M8 → `test_hiring_plans.py` 9/9 |
| Contract | **44 passed** |
| Vitest | **55 file / 487 test** |
| E2E thật — M8 + toàn bộ hồi quy (14 spec) | **91/91 passed** (không skip, không nới assertion) |
| lint / typecheck / ruff / format / mypy / production build | xanh |
| gitleaks (commit M8) | không phát hiện |

**3 E2E trước đó chưa PASS — nguyên nhân và xử lý:**

| Test | Nguyên nhân | Xử lý | Kết quả |
|---|---|---|---|
| `m7-records` HR DIR | Assertion cũ "HR-DIR không có nút duyệt" (luật CFO v2.1) mâu thuẫn R-DEC-173 đã duyệt | Cập nhật kỳ vọng: HR-DIR **có** nút duyệt (không nới, đổi theo quyết định) | PASS |
| `work.spec` assign → e-mail → reassign | Stack cô lập thiếu SMTP: compose cấp `SMTP_HOST=mailpit` cho worker, `.env` để trống → `EmailNotConfiguredErr` | Env stack cô lập `SMTP_HOST=localhost SMTP_PORT=1025` (Mailpit publish 1025) + chạy beat cô lập (sweep e-mail) | PASS (e-mail tới Mailpit) |
| `work.spec` test kế tiếp ("did not run") | Nhóm `serial` dừng khi test trước lỗi | Theo test trên | PASS |

## 8. Checklist triển khai (human duyệt 2026-11-04 — đã chạy, kết quả §8.1)

| # | Bước | Lệnh / kiểm tra | Kỳ vọng |
|---|---|---|---|
| 0 | Nhánh / working tree | `git branch --show-current` · `git status --short` | `v3/m8-crm`; chỉ còn thay đổi của người dùng (`docs/_archive/v2.1` xóa, `docs/BRD_Newfeature.md`, `.prompt/`, `deliverables/GITLEAKS-AUDIT.md`) — **không đụng** |
| 1 | Migration | DB chính `alembic current` = `0027_external_event_link_c19 (head)`; repo `alembic heads` = cùng; `git diff --name-only 44f522b HEAD -- apps/api/alembic` = rỗng | Không migration |
| 2 | Giờ chạy | tránh phút `:15` (job beat) và 01:00–02:30 | |
| 3 | Backup DB | `docker compose -f docker-compose.full.yml exec -T postgres sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc' > var/backup/aureon_prem8_$(date +%Y%m%d_%H%M%S).dump` rồi `pg_restore -l` đếm `TABLE DATA` | file > 0, ~115 bảng |
| 4 | Tag image hiện tại | `docker tag aureon-api:local aureon-api:pre-m8` · `docker tag aureon-web:local aureon-web:pre-m8` | pre-m8 = `7d1495617631` / `a54b7ba12206` |
| 5 | Build | `DOCKER_BUILDKIT=1 docker compose -f docker-compose.full.yml build api web` | exit 0, OCR model baked |
| 6 | Recreate | `docker compose -f docker-compose.full.yml up -d --no-deps --force-recreate api celery-worker celery-beat web` | postgres/redis/minio không bị đụng |
| 7 | Healthcheck | `docker compose ... ps` | 10/10 healthy |
| 8 | Khóa JWT | `docker exec aureon-api-1 sh -c 'ls /app/keys \| wc -l'` (cả worker, beat) | 2 |
| 9 | Mã = HEAD | `var/m4/img_diff.sh aureon-api-1 /app apps/api/src`, `... aureon-web-1 /repo apps/web/src` | diff=0 missing=0 |
| 10 | Beat / log | beat 16 lịch; `docker logs` api/worker/beat/web: không `Traceback` / `Logging error` | |
| 11 | Đăng nhập | 10 tài khoản demo → 200 (chỉ in mã trạng thái) | 10/10 |
| 12 | Quét chỉ đọc | CFO/KD/HR/CEO mở `/business/sales`, `/business/sales/pipeline` (KD), `/work/approvals` (CEO), `/admin/roles` — không lỗi trang / 4xx ngoài dự kiến; **không tạo dữ liệu** | |
| 13 | Kế hoạch tuyển dụng đang `submitted` từ trước (DB chính: **1**) | Không có yêu cầu duyệt → **không hiện** trong `/work/approvals`; HR-DIR quyết định ở trang Nhân sự (EP-86 tự mở yêu cầu — đã test) | Ghi chú vận hành, không sửa dữ liệu |

### 8.1. Kết quả triển khai stack chính (2026-11-04)

Kiểm chứng triển khai = mã đúng bản, hạ tầng khỏe, đăng nhập và mở trang không lỗi; **không** chạy lại test chức năng
(đã PASS ở §6–§7) và **không** ghi dữ liệu vào DB chính.

| # | Hạng mục | Kết quả thực tế | Đạt |
|---|---|---|---|
| 0 | Nhánh / commit | `v3/m8-crm` @ `6361081`; working tree chỉ còn thay đổi của người dùng (không đụng) | ✅ |
| 1 | Migration | DB chính `alembic current` = repo `alembic heads` = `0027_external_event_link_c19 (head)`; 0 file migration đổi từ `44f522b` → **không migration** | ✅ |
| 2 | Giờ chạy | backup 17:39, recreate 17:42 ICT (10:42Z) — ngoài phút `:15` và 01:00–02:30 | ✅ |
| 3 | Backup DB | `var/backup/aureon_prem8_20261104_173919.dump` (pg_dump -Fc, 694 527 byte), `pg_restore -l` = **115** `TABLE DATA` | ✅ |
| 4 | Tag rollback | `aureon-api:pre-m8` = `sha256:7d1495617631013184aa1314d9ccdb46f2e8c71ccfd6ce0a2346ba60fca4ef98`; `aureon-web:pre-m8` = `sha256:a54b7ba12206951779bca21be923387c98d8f309f7bbd1690d5e39e79808ccc4` (image M7) | ✅ |
| 5 | Build | exit 0; image M8: api / worker / beat `sha256:078654df7fa7f1c7bdf858ab54e40e1ac958c6969da5e9a71c76b2799eb8fe30`, web `sha256:5d813a3b23d23a4bbf8eabb61763d38ff58806afec21fabdf8c676b583b5eb50` (image ID local, không có registry digest) | ✅ |
| 6 | Recreate | `api`, `celery-worker`, `celery-beat`, `web` (`--no-deps`); postgres / redis / minio / mailpit / ollama / clamav không bị đụng | ✅ |
| 7 | Healthcheck | **10/10** healthy | ✅ |
| 8 | Khóa JWT | `/app/keys` = 2 file ở api, worker, beat | ✅ |
| 9 | Mã = HEAD `6361081` | `img_diff.sh`: api `apps/api/src` 391 same / 0 diff / 0 missing; web `apps/web/src` 372 / 0 / 0; `apps/web/messages` 2 / 0 / 0 | ✅ |
| 10 | Beat / log | beat **16** lịch; log api / worker / beat / web: 0 `Traceback`, 0 `Logging error` (kiểm lại sau lượt quét) | ✅ |
| 11 | Đăng nhập | **10/10** tài khoản demo → 200 (admin, ceo, cfo, cpo, employee, hr, manager, office, reviewer, sales; chỉ in mã trạng thái) | ✅ |
| 12 | Quét chỉ đọc | **6 role / 17 lượt trang**, 0 lỗi console, 0 API ≥ 400: Sales DIR (`/business/sales`, `/pipeline`, chi tiết deal, Account 360, records deals); CEO (`/business/sales`, `/pipeline`, chi tiết deal, Account 360, `/work/approvals?kind=hiring_plan`, `/admin/roles`); CFO (`/business/sales`, hóa đơn); HR-DIR (kế hoạch tuyển dụng, `/work/approvals`); MGR (`/business/sales`, `/work`); EMP (`/work`). Script chỉ điều hướng — **không ghi DB** | ✅ |
| 13 | Kế hoạch tuyển dụng cũ | DB chính (đọc): 1 `submitted` (trước M8, không có yêu cầu duyệt), 1 `approved`, 3 `in_progress`. Không sửa dữ liệu. Xử lý: HR-DIR quyết định trực tiếp ở trang kế hoạch (`/business/hr/records?tab=hiringPlans`, EP-86) → hệ thống tự tạo yêu cầu `RULE-hiring_plan` rồi quyết định (TC-M8-02) | ℹ️ vận hành |

Đường lùi: §9 (tag `:pre-m8` + recreate; M8 không đổi schema nên **không** cần khôi phục DB — backup chỉ dùng khi có sự cố dữ liệu thật + quyết định).

## 9. Checklist rollback (chỉ khi có sự cố + quyết định)

| # | Bước | Ghi chú |
|---|---|---|
| 1 | `docker tag aureon-api:pre-m8 aureon-api:local` · `docker tag aureon-web:pre-m8 aureon-web:local` | |
| 2 | `docker compose -f docker-compose.full.yml up -d --no-deps --force-recreate api celery-worker celery-beat web` | tránh phút `:15` |
| 3 | Kiểm 10/10 healthy, khóa JWT, đăng nhập 10/10 | |
| 4 | **Rủi ro yêu cầu duyệt tuyển dụng** | Yêu cầu `hiring_plan` tạo trong thời gian chạy M8: code M7 không có hook → quyết định ở `/work/approvals` **không** chuyển trạng thái kế hoạch, FE M7 hiển thị như "AI action"; EP-86 (M7) chỉ cho CFO và **không** đóng yêu cầu → yêu cầu treo PENDING. Đếm trước khi rollback: `select status, count(*) from platform.approval_requests where target_kind='hiring_plan' group by 1`. Xử lý (cần quyết định riêng, ghi DB): hủy các yêu cầu PENDING đó + quyết định kế hoạch theo luật M7 |
| 5 | Hóa đơn OUT tạo bằng MST | Đã có `client_id` thật → vẫn hợp lệ với M7, không cần xử lý |
| 6 | DB | **Không** khôi phục DB trừ khi có sự cố dữ liệu thực sự + quyết định; bản backup bước 3 dùng cho `pg_restore` |

## 10. Blocker / tồn đọng

| # | Hạng mục | Loại |
|---|---|---|
| 1 | Deploy M8 Phase 1 (§8) | **DONE** — human duyệt, deployed 2026-11-04 (§8.1) |
| 2 | **R-DEC-176** — 10 điểm §5.2 cần xác nhận trước migration | **OPEN** — chờ human; chưa có bảng / migration |
| 3 | **R-DEC-168** — xoay khóa JWT RS256 (lộ một phần trong output phiên trước) | **OPEN — SECURITY BLOCKER**, chờ human (M8 deploy dùng khóa hiện có, không xoay) |
| 3b | **Lịch sử Git — GitLeaks** (`deliverables/GITLEAKS-AUDIT.md`) | **OPEN** — chưa có quyết định xử lý lịch sử; không rewrite / force-push |
| 4 | Tên người phụ trách trên Kanban / xếp hạng hiện "Tôi" hoặc mã rút gọn (KD không đọc danh bạ) | Backlog (R-DEC-169 danh bạ) |
| 5 | Xuất Excel/PDF dashboard KD (DASH-010) | Backlog |
| 6 | Ngân sách: CFO chỉ chọn phòng ban của mình (R-DEC-171 mục 4) | Backlog |
| 7 | EMP gọi `/org/tree` trong hộp đề nghị chuyển giao (R-DEC-169) | Backlog |
