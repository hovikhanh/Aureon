# M8 — Audit, kế hoạch CRM (BRD_Newfeature) và R-DEC-171

> Nhánh `v3/m8-crm` (từ `v3/m7-records`). Ngày 2026-11-04. Chưa push, chưa merge, **chưa deploy** stack chính.
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

**Điểm BRD phải chốt trước khi làm:** danh sách giai đoạn chuẩn (BRD có 3 phiên bản khác nhau); công thức Win Rate (theo số
hay giá trị), Forecast Accuracy, Slippage, Average Deal Size, Sales Cycle; 1 hay nhiều sản phẩm / cơ hội; trùng Lead/Contact
**chặn** hay **cảnh báo**; vai trò Sales Executive / Presales / Marketing ánh xạ vào 7 role Aureon (02) — không thêm role
nếu chưa có DEC; mã tự sinh (định dạng); tỷ giá đa tiền tệ.

## 6. Kiểm thử M8

| Gate | Kết quả |
|---|---|
| Backend (pytest đầy đủ + contract) | xem STATE / báo cáo phiên |
| Unit FE (Vitest) | +12 CRM, +1 hộp phê duyệt — xanh |
| E2E thật (stack cô lập) | M8 4/4 |
| lint / typecheck / ruff / mypy / build | xanh |

## 7. Kế hoạch triển khai & rollback (chỉ chạy khi được đồng ý)

1. Backup: `pg_dump -Fc` DB chính → `var/backup/aureon_prem8_<ts>.dump`; tag image `aureon-{api,web}:pre-m8`.
2. Migration: **không có** (rule phê duyệt tạo lười; không đổi schema). Kiểm `alembic current` = head.
3. Build `api` + `web`; recreate `api celery-worker celery-beat web` (`--no-deps`), tránh phút `:15` (job beat).
4. Kiểm: 10/10 healthy, `/app/keys` có 2 file ở api/worker/beat, mã trong container = HEAD, beat 16 lịch, log không lỗi,
   đăng nhập 10 tài khoản = 200, quét trang chỉ đọc theo role.
5. Rollback: `docker tag aureon-api:pre-m8 aureon-api:local` (+ web) → recreate 4 container. Dữ liệu: các yêu cầu
   `hiring_plan` tạo trong thời gian chạy M8 vẫn đọc được với code cũ, nhưng code cũ **không có hook** nên quyết định trên
   chúng không chuyển trạng thái kế hoạch — sau rollback, kế hoạch đang `submitted` duyệt lại bằng EP-86 (luật cũ: CFO).
   Khôi phục DB toàn phần (chỉ khi cần): `pg_restore` bản backup bước 1.
