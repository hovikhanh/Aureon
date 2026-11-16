# Aureon v4 — Đối chiếu Tài liệu ↔ Codebase (Documentation-to-Codebase Conformance Audit)

> **Ngày audit:** 2026-11-09 · **Nhánh:** `v4/demo-readiness` · **Commit:** `8645c27` (working tree sạch, chỉ `.prompt/` chưa theo dõi)
> **Loại:** chỉ đọc. Không sửa code, tài liệu nguồn, DB, Docker; không gọi ứng dụng đang chạy; không chạy test hay migration. Truy cập DB chỉ bằng `SELECT`.
> **Người đọc:** Product Owner, Tech Lead, nhóm phát triển Aureon.
> **Ký hiệu đường dẫn:** `api/` = `apps/api/src/app/`, `web/` = `apps/web/src/`, `tests/` = `apps/api/tests/`, `e2e/` = `apps/web/e2e/`.

---

## 1. Executive Summary

**Kết luận chính:** Aureon v4 có nền kỹ thuật vững (API khớp spec 100% ở cấp endpoint, DB khớp ORM, 1709 test backend xanh), nhưng **mức hoàn thành theo tính năng nghiệp vụ là 62%** và **chỉ 58% tính năng có bằng chứng kiểm thử**. Có **2 lỗi CRITICAL** và **19 lỗi HIGH** cần xử lý trước khi coi bản demo là đúng nghiệp vụ.

| Chỉ số (feature-level, mô-đun nghiệp vụ) | Giá trị | Công thức |
|---|---:|---|
| Tính năng được tài liệu hiện hành yêu cầu | **421** | Documented − Doc gap (không tính OUT OF SCOPE, NEEDS CLARIFICATION) |
| Implementation coverage | **62%** (262/421) | (Verified + Implemented) ÷ 421 |
| Verified feature coverage | **58%** (246/421) | Verified ÷ 421 |
| Có ít nhất một phần code | 93% (393/421) | (V + I + Partial + Spec mismatch + Broken) ÷ 421 |
| Test coverage (tính năng đã làm có test kiểm đúng hành vi) | 94% (246/262) | Verified ÷ (Verified + Implemented) |
| Documentation coverage (code có tài liệu) | 99% | (tất cả − Doc gap) ÷ tất cả |
| Code coverage (pytest --cov) | **NOT VERIFIED** | Đo lần cuối 2026-10-23 (97%); chưa đo cho v4 |
| Chưa làm / hỏng / lệch spec | 30 / 14 / 17 | |
| NEEDS CLARIFICATION (báo riêng) | 15 | |
| OUT OF SCOPE (P1/P2, theo quyết định đã duyệt) | 66 | |

**Yêu cầu bắt buộc "CEO toàn quyền CRUD dữ liệu nghiệp vụ" (D-21, R-DEC-198): PARTIALLY IMPLEMENTED.**
- **API:** đạt ở hầu hết module. CEO gọi được 337/345 thao tác API; chỉ bị chặn ở 8 route cấu hình IDP (`idp:admin`). Có test tích hợp `tests/integration/test_ceo_full_crud_d21.py` cho từng module.
- **Giao diện:** chưa đạt. CEO **không** tạo/sửa/khóa được người dùng (`web/app/(app)/admin/users/page.tsx:9`), không có màn hình lịch sử lương hay trường mức 4, không sửa/xóa được Chiến lược và Mục tiêu chiến lược, không có UI cho Initiative, dự báo P&L hay dòng tiền 13 tuần.
- **Toàn vẹn dữ liệu:** xóa deal có hợp đồng sống làm hợp đồng mồ côi, kể cả với CEO (`api/modules/sales/services/sales_service.py:371`).
- **Đính chính:** báo cáo `deliverables/v4-demo/V4-DEMO-READINESS-REPORT.md` §3 trước đây ghi CEO quản lý được tài khoản và mọi bản ghi qua giao diện. **Ghi nhận đó không đúng** (chi tiết §10).

**Năm rủi ro lớn nhất:**
1. **CRITICAL — lộ dữ liệu mức 4 (lương, CCCD) qua IDP.**
   - EP-DC-03, EP-DC-05/14 (`pages[]`) và tìm kiếm EP-24 trả giá trị hoặc văn bản thô.
   - EMP và MGR cùng phòng đọc được.
   - Giá trị mức 4 lưu dạng plaintext JSONB, trái 05 §2.7.
2. **CRITICAL — tài liệu đi luồng STP báo "đã ghi" nhưng không ghi.**
   - Tài liệu dừng ở `AUTO_APPROVED`, không bao giờ commit vào module đích.
   - Hộp thư vẫn xếp nhóm "committed" (`api/modules/idp/services/inbox_service.py:43`).
3. **HIGH — chức năng giả trên giao diện.**
   - Nút "Duyệt" việc cần làm từ biên bản họp chỉ đổi trạng thái hiển thị, không tạo task (`web/features/execution/PredictedActionList.tsx:42`).
   - Đăng xuất không thu hồi refresh token: 208 lượt đăng nhập, 0 lượt đăng xuất được ghi.
4. **HIGH — phân quyền lệch.**
   - MGR xem được số liệu tài chính toàn công ty qua `/finance/dashboard` và what-if (`api/modules/finance/routes/router.py:424-446`).
   - Lưới tự chủ AI (D-11) chỉ dựa vào cấu hình: mặc định trong code và `.env.example` vẫn là provider cloud.
5. **HIGH — trí tuệ điều hành chưa trọn.**
   - Không có drill-down từ chỉ số tới bản ghi và tài liệu (vẫn hiện "0 bản ghi").
   - Chỉ số chất lượng dữ liệu (DQ) không hiển thị cho ai.
   - 7/13 cảnh báo đang mở thuộc module đã đóng băng (Product/Risk) nhưng vẫn cộng vào ô "Rủi ro" của CEO.

**Về quản trị tài liệu:** nhiều thay đổi v4 đang chạy trên các quyết định **chưa được duyệt** (R-DEC-176, 183, 185, 186, 188, 192 ở trạng thái PROPOSED/open; R-DEC-199..202 do agent tự quyết theo ủy quyền). Migration `0028` đã áp lên DB chính. Bảng ma trận quyền theo role mà code trích dẫn ("02 §5.2/§5.3") **không còn tồn tại** trong 02 hiện hành.

---

## 2. Audit Scope và Methodology

**Phạm vi:**
- Toàn bộ 11 module backend, frontend Next.js, 28 migration, Docker Compose.
- Tài liệu `docs/` (trừ `_archive`), `docs/_reference/` (canonical), `deliverables/` (chỉ là tuyên bố cần kiểm chứng), `README.md`, `CLAUDE.md`.

**Cách làm:**
1. **Xác định nguồn yêu cầu hiện hành** (thứ tự ưu tiên):
   - Canonical: `docs/_reference/SOURCE-BRD-v1.1.md` (+ Bổ sung), `SOURCE-UIUX.md`; `BRD_Newfeature.md` chỉ canonical cho Sales (D-06).
   - Living spec 00–14.
   - Quyết định trong `13-DECISION-LOG.md`.
   - Yêu cầu bị thay hoặc hoãn bởi R-DEC đã resolved không tính là hiện hành. R-DEC PROPOSED được báo cáo riêng, không coi là đã duyệt.
2. **Chia 8 nhóm audit song song:**
   - Tài chính
   - Kinh doanh/CRM
   - Tổ chức/Nhân sự/Quyền
   - Mục tiêu–Công việc–Họp
   - IDP/Dữ liệu
   - AI
   - Dashboard/Báo cáo/Product/Risk
   - Kiến trúc–API–DB

   Mỗi nhóm truy vết **implementation thực tế** (route, service, model, migration, component gọi API, test), không dựa vào tên file hay comment.
3. **Phân loại** từng tính năng theo 9 trạng thái của yêu cầu audit, cộng thêm `OUT OF SCOPE (P1/P2)` cho mục bị hoãn bởi quyết định đã duyệt (R-DEC-05: phạm vi P0; R-DEC-16: đóng băng Product/Risk).
4. **Chuẩn bằng chứng:**
   - Một tính năng chỉ được tính `IMPLEMENTED & VERIFIED` khi có test thật sự kiểm hành vi đó (đã đọc nội dung test).
   - Kết quả chạy lấy từ log có sẵn, không chạy lại:
     - pytest 1709 passed: `var/v4-audit/restore/pytest-full2.log`, commit `67c7218`; mã test không đổi tới HEAD.
     - Contract 44 passed.
     - Vitest 590 passed (commit `cdc794a`).
     - E2E `real` 135/136 passed: `var/v4-audit/dev/final2/e2e-full3.log`; test còn lại đã sửa và pass 2 lượt riêng.
5. **Tự kiểm lại** mọi phát hiện CRITICAL/HIGH trực tiếp trong code hoặc DB trước khi đưa vào báo cáo.
6. **Tự đếm lại** các bảng số liệu mà tổng của nhóm audit không khớp danh sách chi tiết (API: 15 mục, Kiến trúc: 19, Metric store: 12).

**Giới hạn chính:** xem §24. Đặc biệt: không gọi ứng dụng (vì đăng nhập cũng ghi audit), nên hành vi giao diện được suy ra từ code và E2E.

---

## 3. Repository và Version Information

| Mục | Giá trị kiểm chứng |
|---|---|
| Nhánh / commit | `v4/demo-readiness` @ `8645c27`; 65 commit sau `main` (`854606b`) |
| Commit gần nhất | `8645c27` docs README · `67c7218` test không phụ thuộc `.env` host · `595e613` fix(ops) preflight + compose |
| Working tree | sạch (chỉ `.prompt/` chưa theo dõi, của người dùng) |
| Phiên bản API tự báo | `3.0.0` (`GET /health`); tài liệu gọi bản này là "v4 demo" |
| Alembic | head = DB = `0028_crm_leads_contacts_activity` (28 migration, tất cả có `downgrade()`) |
| DB | 103 bảng module, khớp tuyệt đối với metadata ORM; 131 FK đều có index; schema `public` còn 12 bảng v1 có dữ liệu |
| Docker | project `aureon`, 10 service healthy, cùng mạng `aureon-net`; `docker-compose.yml` include `docker-compose.full.yml` (R-DEC-202) |
| Backend | FastAPI modular monolith: 11 module (`ai, auth, dashboard, execution, finance, hr, idp, platform, product, risk, sales`); 345 thao tác API |
| Frontend | Next.js 15 + next-intl + NextAuth (BFF `/api/backend/*`); 63 file Vitest; 33 spec E2E |
| Test backend | 211 file `test_*.py` (unit, integration, contract, events, architecture, ai_eval) |
| Nền | Celery worker + beat (1 instance), Redis, Postgres 16 + pgvector, Ollama (`qwen2.5:3b-instruct`, `bge-m3`), ClamAV, Mailpit, MinIO (chạy nhưng code không dùng) |

---

## 4. Documentation Inventory

| Tài liệu | Version / trạng thái khai báo | Hiệu lực | Phản ánh v4? | Ghi chú |
|---|---|---|---|---|
| `_reference/SOURCE-BRD-v1.1.md` (+ Bổ sung) | canonical | **hiện hành** | — | Nguồn gốc yêu cầu D01–D28, FR-*, US-*, UC-* |
| `_reference/SOURCE-UIUX.md` | canonical | hiện hành | — | |
| `_reference/BRD_Newfeature.md` | canonical cho Sales (D-06) | hiện hành **nếu** R-DEC-182 được duyệt (đang PROPOSED) | — | 107 tính năng (82 Must), 19 BR, 17 UAT |
| 00-INDEX | 1.0.0 current | hiện hành | một phần | §5.1 ghi thay đổi v4 "chưa commit" (lỗi thời); không có §4.5 mà CLAUDE.md trích |
| 01-PROJECT-OVERVIEW | 1.0.0 (Change 1.1.0 đề xuất) | hiện hành | có (§7.6) | phần v4 ở mức đề xuất |
| 02-PERSONAS-PERMISSIONS | 1.0.0 current | hiện hành | D-20/21 (đề xuất) | **thiếu ma trận role × quyền**; FR-ADM-04 MFA/SSO vẫn ghi P0 |
| 03-DASHBOARD-SPEC | 1.0.0 (Change 1.3.0 đề xuất) | hiện hành | một phần | |
| 04-IDP-FEATURE-SPEC | 1.0.0 current | hiện hành | không | ghi MinIO, code dùng file cục bộ |
| 05-DATA-MODEL | khai 1.2.0, liệt kê Change 1.3–1.6 | hiện hành | CRM 0028 (đề xuất) | **39/103 bảng không được mô tả** |
| 06-UI-UX-SPEC | 1.1.0 (Change 1.6.0 đề xuất) | hiện hành | có (§3.5) | SCR-53 ghi "CEO xem", trái D-21 |
| 07-TECH-ARCHITECTURE | 1.0.0 current | hiện hành | §7.1 (đề xuất) | ghi qwen 7b; tên module `ai_core` |
| 08-DEMO-DATA-SPEC | 1.1.0 current | hiện hành | không | |
| 09-BUILD-PLAN-TASKS | 1.1.0 (Change 1.3.0 đề xuất) | hiện hành | có (§6.24) | |
| 10-API-SPECIFICATION | 1.1.0 current | hiện hành | EP-SAL-10..13 (đề xuất) | danh mục route đầy đủ; version/ngày chưa nâng |
| 11-AGENT-WORKFLOW | 1.0.0 (1.1.0 đề xuất) | hiện hành | một phần | |
| 12-DOC-AUDIT / 13-DECISION-LOG / 14-TEST-TRACEABILITY | 1.1.0 / 1.2.0 / 1.1.0 | hiện hành | có | 13: R-DEC-177..197 PROPOSED; 14 có vài TC "Passed" sai (§15) |
| 16-OPERATIONS | 0.3.0 **đề xuất** | đề xuất | có | ghi "migrate tới 0027" (nay 0028) |
| DEC-REGISTRY | 0.1.0 **đề xuất** | tham chiếu lịch sử | có | định nghĩa DEC-* nền v2.1 |
| TRACEABILITY-SKELETON | 1.1.0 current | hiện hành | không | chưa có ID cho CRM/SalesActivity |
| REBUILD-PLAN, REVIEW-REPORT | 1.0.0 | **lịch sử** | không | |
| DEMO-SCRIPT, handover/* | không version | hướng dẫn | không | nhiều mô tả lỗi thời (CEO không có `idp:approve`, readiness có MinIO) |
| `CLAUDE.md` | 3.0.0 (2026-10-23) | hợp đồng vận hành | **không** | số test, số service, `secrets/` vs `keys/`, `ai_core`, qwen 7b, registry không tồn tại (§16) |
| `README.md` | 2026-11-09 | hướng dẫn | có | viết lại sau sự cố khởi động lại |
| `docs/_archive/v2.1/`, `SOURCE-BRD-v1.0` | archived | **không phải yêu cầu** | — | |
| `deliverables/**` | báo cáo | **không phải yêu cầu** | — | chỉ là tuyên bố; một số sai (§15) |

---

## 5. Business Requirements Inventory

**Mục tiêu kinh doanh (01 §2):** BO-01..BO-10, gồm:
- quản trị tập trung ≥ 80%;
- độ trễ chỉ số ≤ 24h (tài chính), ≤ 1h (task/sales);
- ≥ 70% task gắn KPI/OKR;
- ≥ 50% quyết định có AI;
- giảm ≥ 50% giờ tổng hợp của CEO;
- ≥ 90% tri thức truy vấn được;
- giảm ≥ 70% thời gian nhập liệu;
- DQ ≥ 90;
- giảm ≥ 50% thời gian phát hiện rủi ro.

Các chỉ số kết quả này **chưa đo được trên demo**, vì không có dữ liệu vận hành thật. Hệ thống có trang `/admin/acceptance` cho G1–G4, nhưng G1 đang tính sai (§19).

**Nguyên tắc sản phẩm P01–P11** (01 §3) — đánh giá tóm tắt:
- **P02 API First:** đạt (mọi năng lực có API).
- **P06 Traceability:** chưa đạt ở chiều chỉ số → bản ghi → tài liệu.
- **P07 Explainable AI:** một phần (có trích dẫn nguồn, không có panel ngữ cảnh).
- **P08 Security by Design:** một phần (lộ dữ liệu mức 4, không có rate limit).
- **P10 Graceful Degradation:** đạt (nghiệp vụ chạy được khi tắt AI).

**28 domain (01 §4) và phạm vi P0 (R-DEC-05):**

| Phạm vi | Domain |
|---|---|
| P0 | D01, D02, D03, D05, D06 (Google/MS), D08, D09, D11, D13, D14, D26, D27 |
| P0 cơ bản / Lite | D04, D07, D10 (check-in), D12 (transcript), D15, D16, D17, D28 |
| P1 / P2 (backlog) | D18–D25 |

Riêng D22 Product và D25 Risk có code nhưng **đóng băng** (R-DEC-16).

**Use case nghiệm thu P0:** UC-01 Briefing, UC-02 Họp → việc, UC-03 KPI dưới ngưỡng, UC-04 OKR rủi ro, UC-06 Biên bản giấy → việc, UC-07 Onboarding 1 ngày. UC-05 và UC-08 là P1.

| UC | Trạng thái |
|---|---|
| UC-01 | Một phần: briefing chỉ hiện dòng tóm tắt, không có 7 khối và hành động |
| UC-02 / UC-06 | **Hỏng ở bước cuối:** duyệt việc cần làm không tạo task (§19 H-03) |
| UC-03 | Đạt (E2E `uc03-real`), insight trên demo DB = 0 |
| UC-04 | Đạt (phát hiện at-risk) |
| UC-07 | Đạt (E2E `onboarding-real`), trừ phần SOP → kho tri thức (chưa làm) |

**Vai trò (02 §2):** CEO, DIR, MGR, EMP, REV, ADM + AI actor. Ma trận chi tiết ở §11.

**Yêu cầu bắt buộc mới:** D-21 / R-DEC-198 — CEO thêm, xem, sửa, xóa mọi dữ liệu nghiệp vụ (APPROVED bởi PO ngày 2026-11-09).

---

## 6. System Architecture Comparison

| Hạng mục | Tài liệu yêu cầu | Thực tế | Trạng thái | Bằng chứng |
|---|---|---|---|---|
| Kiến trúc | Modular Monolith, 11 module, 1 schema / module (R-DEC-06, 07 §1.1) | 11 module, 10 schema (dashboard không có schema) | IMPLEMENTED & VERIFIED | `tests/architecture/test_modules_discovered`, `test_all_module_schemas_exist` |
| Ranh giới module | Chỉ gọi service public hoặc event (CLAUDE §4.3) | Đúng; không có SQL chéo schema | IMPLEMENTED & VERIFIED | `tests/architecture/test_import_boundaries.py` (8 test) |
| Lọc tenant | Chỉ trong repository (R-DEC-21) | Đúng | IMPLEMENTED & VERIFIED | `test_tenant_query_boundary.py` |
| `tenant_id` mọi entity | R-DEC-07/13, 05 §2.2 | **22/103 bảng thiếu**, gồm `hr.salary_history`, `ai.conversations/messages`, `sales.deal_stage_history`, bảng job/review của IDP | PARTIALLY IMPLEMENTED | information_schema |
| Transactional outbox + Celery | DEC-126; retry 5/30/120 s → DLQ; `acks_late`; beat 1 instance | Đúng; 40 loại event, 23 consumer | IMPLEMENTED & VERIFIED | `tests/events/*`, `api/core/events/consumer.py:32`, `api/worker.py:40` |
| ModelGateway đa provider | DEC-131; Public/Internal → cloud, Confidential → local | Đúng theo tài liệu đã duyệt; D-11 (không provider nào nhận INTERNAL) chỉ ở cấu hình `.env` | Theo spec: VERIFIED. D-11: NEEDS CLARIFICATION | `api/core/model_gateway/routing.py`; `config.py:68` mặc định `omniroute` |
| Lưu trữ file | MinIO (dev) / S3 (prod), bucket quarantine (CLAUDE §2.2, §5.6) | **Chỉ hệ thống file cục bộ** `./var/idp-storage`; MinIO chạy nhưng không dùng | SPEC MISMATCH | `api/core/storage.py:41,121` |
| JWT RS256 | `kid`, xoay khóa 90 ngày | RS256 + `kid`; chỉ một cặp khóa, không verify nhiều khóa | PARTIALLY IMPLEMENTED | `api/core/security.py` |
| Rate limit | 20 req/phút/người cho AI; NFR-SEC-05 | **Không có** (`RateLimitError` không bao giờ được raise) | NOT IMPLEMENTED | `api/core/errors.py:106` |
| SSO / MFA | FR-ADM-04 (P0 trong 02) | Không có | NOT IMPLEMENTED | R-DEC-187 (hoãn) đang PROPOSED |
| Audit log append-only | NFR-AUD-01 | Trigger chặn UPDATE/DELETE, nhưng ứng dụng kết nối bằng superuser có TRUNCATE | PARTIALLY IMPLEMENTED | `pg_roles`; trigger `trg_audit_logs_immutable` |
| Observability | `/health*`, `/metrics` (07 §6.7) | Có; `/metrics` không xác thực, không có chỉ số độ trễ hay chi phí AI | PARTIALLY IMPLEMENTED | `api/core/ops_routes.py` |
| Hiệu năng | NFR-PERF-02: token đầu < 2 s, p90 30 s | Model local trên CPU: 13–67 s/lượt; số đo "Passed" trong 14 lấy từ chế độ replay | SPEC MISMATCH | `14` TC-M25-02; `06-AI-INTEGRATION-REPORT.md` |
| Docker | Compose 24+, healthcheck | 10 service `restart: unless-stopped`, 9 có healthcheck (mailpit không có), preflight ở `api`/worker/beat; image `:latest` cho minio/ollama/clamav/mailpit; cổng mở trên mọi interface | IMPLEMENTED | `docker-compose.full.yml` |
| Coverage | services ≥ 80%, backend ≥ 75%, bảo mật ≥ 90% (14 §1.3) | Chưa đo cho v4 | NOT VERIFIED | `14` dòng 86 (97% ở M1.1) |

---

## 7. Module-by-Module Comparison

Mỗi mục dưới đây gồm:
- Mục tiêu nghiệp vụ
- Tính năng tài liệu yêu cầu (số lượng)
- Đã triển khai và kiểm chứng
- Chưa đầy đủ
- Chưa làm
- Đang lỗi
- Sai lệch tài liệu ↔ code
- Test
- Việc cần làm

Ma trận chi tiết ở §8, số liệu ở §20.

### 7.1. Tổ chức (D01)

- **Mục tiêu:** cây tổ chức theo ngày hiệu lực, làm gốc phạm vi dữ liệu.
- **Yêu cầu:** 11 tính năng.
- **Đã kiểm chứng (6):** tổ chức, vị trí, gán nhân sự theo ngày hiệu lực, cây `as_of`, onboarding UC-07, phân quyền cấu trúc.
- **Chưa đầy đủ (3):** đội nhóm (không sửa được trên UI), sơ đồ thiếu workload, import có nhưng không export.
- **Chưa làm (1):** báo cáo ma trận và kiêm nhiệm (FR-ORG-02).
- **Đang lỗi (1):** sửa phòng ban trên SCR-51 luôn thất bại vì không gửi `version` (`web/features/admin/org/OrgForms.tsx:64`).
- **Sai lệch:** demo không có vị trí nào (`hr.positions` = 0 dòng).
- **Test:** `tests/integration/hr/test_org_api_t613.py`, `test_assignments_t612.py`, E2E `admin-org`, `onboarding-real`.
- **Việc cần làm:**
  - sửa lỗi sửa phòng ban;
  - dialog sửa đội nhóm, sửa gán nhân sự, lưu trữ tổ chức;
  - quyết định về kiêm nhiệm.

### 7.2. Nhân sự (D16)

- **Mục tiêu:** hồ sơ nhân sự cơ bản, kế hoạch tuyển dụng, che dữ liệu mức 4.
- **Yêu cầu:** 15 tính năng.
- **Đã kiểm chứng (10):** CRUD nhân viên, che mức 4 ở API, kế hoạch tuyển dụng + duyệt qua engine, cảnh báo trễ, dashboard HR, workload, METRIC-HR, danh sách SCR-48, phạm vi theo role.
- **Chưa đầy đủ (2):**
  - lịch sử lương có API nhưng không có màn hình;
  - vòng đời kế hoạch sau khi duyệt chỉ có ở API.
- **Chưa làm (2):** **nghỉ phép** (FR-HR-01 P0; bảng `hr.leaves` có nhưng không dùng), kỹ năng.
- **Doc gap:** quy tắc ai xem được dashboard HR và tổng quỹ lương.
- **Việc cần làm:**
  - màn hình chi tiết nhân viên có mức 4 và lịch sử lương;
  - nghỉ phép (hoặc hoãn chính thức).

### 7.3. Người dùng, vai trò, quản trị (D02)

- **Đã kiểm chứng (7):** danh sách, tạo, sửa, khóa/mở người dùng (vai ADM); ma trận vai trò chỉ đọc; nhật ký audit; onboarding.
- **Sai lệch (1):** CEO chỉ xem được trang người dùng; trang chỉ cho ADM sửa (`web/app/(app)/admin/users/page.tsx:9`), trái D-21. E2E `admin-screens.spec.ts:85-89` còn khẳng định CEO chỉ đọc.
- **Chưa làm (1):** "Xem như người dùng" (FR-ADM-08).

### 7.4. Xác thực (D02)

- **Đã kiểm chứng (7):** đăng nhập + khóa sau 5 lần sai, xoay refresh token, `/auth/me`, JWT RS256, đăng nhập demo, không có `/auth/register`, cô lập tenant.
- **Đang lỗi (1):** đăng xuất không gọi `/auth/logout`, nên refresh token 7 ngày vẫn hợp lệ.
  - Code: `web/components/shell/Header.tsx:66`.
  - DB: 208 `auth.login`, 0 `auth.logout`.
- **Chưa làm (2):** rate limit; SSO/MFA/quản lý phiên.

### 7.5. RBAC

- **Đã kiểm chứng (4):** ma trận trong code = DB = JWT; quy tắc route mặc định từ chối.
- **Sai lệch (2):**
  - cơ chế cô lập khối khác R-DEC-12a;
  - Reviewer không đọc được hồ sơ HR trong phiên review như 02 §5 mô tả.
- **Doc gap (1):** ma trận role × quyền vắng mặt trong 02.
- **Chưa đầy đủ (1):** CRUD toàn quyền của CEO ở UI.

### 7.6. Tài chính (D15)

- **Mục tiêu:** Finance Lite — doanh thu, chi phí, hóa đơn, ngân sách, dòng tiền, runway.
- **Yêu cầu:** 34 tính năng.
- **Đã kiểm chứng (20):** CRUD doanh thu/chi phí/ngân sách/hóa đơn, thanh toán có khóa dòng, hóa đơn OUT theo MST, job quá hạn, runway, what-if, FIN-01 theo D-09, METRIC-FIN-*, drill-down, D-07, D-20, cô lập khối, audit.
- **Chưa đầy đủ (8):**
  - không cảnh báo ngân sách ngay khi ghi chi phí;
  - dự báo P&L không có UI;
  - không có thực thể Payment;
  - dòng tiền 13 tuần không có màn hình;
  - Metric Store không cập nhật ngay sau khi ghi tay;
  - Finance Lite thiếu lineage, độ tươi dữ liệu và chọn kỳ;
  - CEO không xóa được số dư tiền và dự báo;
  - nhãn độ tươi dữ liệu.
- **Sai lệch (4):**
  - số dư tiền không có DELETE dù 10 ghi "CRUD";
  - dashboard tính lại số liệu lúc request, trái 03 §4.3;
  - MGR xem được số liệu tài chính toàn công ty;
  - thiếu bộ lọc `source`.
- **Cần làm rõ (3):** chỉ tiêu Q4 20 tỷ so với tổng 3 tháng 85 tỷ; đồng bộ phần mềm kế toán; duyệt ngân sách.
- **Test:** `tests/integration/finance/*`, `test_metric_meaning_v4.py`, `test_ceo_full_crud_d21.py`; E2E `finance-drill`, `business`, `m7-records`, `roles`.

### 7.7. Kinh doanh / CRM (D17 + BRD_Newfeature)

- **Mục tiêu:** pipeline Lite (P0); CRM đầy đủ là P1.
- **Theo spec Aureon (22 mục):**
  - **Đã kiểm chứng (18):** CRUD khách hàng, deal, hợp đồng, chỉ tiêu, lead, liên hệ, hoạt động, chuyển lead, chuyển giai đoạn, lịch sử giai đoạn, funnel, dashboard, phạm vi theo role, CEO CRUD qua API.
  - **Đang lỗi (1):** xóa deal có hợp đồng sống làm hợp đồng mồ côi; sau đó hợp đồng trả 422 với mọi role.
  - **Sai lệch (1):** lead chưa đạt "Qualified" vẫn chuyển được (BR-002).
  - **Doc gap (1):** ma trận phạm vi sales trong 02.
- **Theo BRD_Newfeature (107 tính năng + 19 BR):**
  - 75 tính năng thuộc phạm vi hiện hành: 47 đã kiểm chứng, 3 đã làm, 25 làm một phần.
  - 32 tính năng là P1 / bị hoãn (OUT OF SCOPE), trong đó 15 mục Must; nếu R-DEC-179/182 được duyệt, 15 mục này chuyển thành NOT IMPLEMENTED.
- **Demo:** chưa thể hiện được CRM: `deal_stage_history` = 0 dòng, `contracts` = 0, chỉ một người phụ trách deal, không có tài khoản MGR/EMP Sales.

### 7.8. Mục tiêu và chiến lược (D07–D10)

- **Chiến lược:** 2/7 đã kiểm chứng. API CRUD đầy đủ, nhưng UI chỉ tạo được Chiến lược và Mục tiêu chiến lược; không có UI cho Initiative và mốc.
- **KPI:** 5/9. Chưa có:
  - kiểm tổng trọng số = 100%;
  - so sánh phòng ban;
  - khóa kỳ: API chặn khi đã khóa nhưng không có gì khóa được kỳ.
- **OKR + check-in:** 9/12. Chưa có:
  - kiểm chất lượng OKR bằng AI;
  - phát hiện O/KR không có hành động;
  - khung đánh giá theo phòng ban.

### 7.9. Công việc, dự án, workload (D11)

- **Kết quả:** 11/17 đã làm.
- **Chưa làm:** task định kỳ / mẫu; AI gợi ý điều chuyển việc; ước lượng giờ có nhãn.
- **Chưa đầy đủ:** bắt buộc bằng chứng; xem dạng timeline; sửa/xóa mốc dự án trên UI.
- **Cần làm rõ:** công thức năng lực làm việc (BRD) so với 40h cố định (R-DEC-44).

### 7.10. Họp và Decision Log (D12/D28)

- **Kết quả:** 6/11 đã làm.
- **Đang lỗi:** nút duyệt việc cần làm không tạo task. Trong DB, 6 action item, 0 có `task_id`.
- **Chưa làm:** quyết định rút từ biên bản; briefing trước họp.
- **Chưa đầy đủ:**
  - tóm tắt họp bằng AI không có caller thật;
  - không có UI "xác minh kết quả" cho quyết định;
  - job nhắc review vẫn nhắc cả quyết định đã hủy.

### 7.11. Lịch và tích hợp (D13/D06)

- **Đang lỗi (2):**
  - sự kiện hạn chót của task gán `owner_id = assignee_id` (mã nhân viên) nên người được giao không thấy (`api/modules/execution/services/task_service.py:236-241`);
  - callback OAuth Google/Outlook đòi Bearer token nên không hoàn tất kết nối được (`api/modules/platform/routes/integrations.py:47-55`).
- **Cần làm rõ (3):** AI hỏi lịch, gợi ý khung giờ, phân tích thời gian họp — BRD ghi P0, xung đột với R-DEC-123.

### 7.12. Phê duyệt, thông báo (D04/D05)

- **Phê duyệt:** 2/3 đã kiểm chứng. SLA hay escalation chưa có; yêu cầu quá hạn không quyết được (lỗi đặt `EXPIRED` rồi rollback).
- **Thông báo:** 3/4 đã kiểm chứng. Chưa nhắc việc sắp đến hạn.

### 7.13. Thu thập dữ liệu / IDP (D03)

- **Yêu cầu:** 52 tính năng.
- **Đã kiểm chứng (26):** form C1, upload C3, import C5, quét malware, chống trùng, OCR, phân loại, schema và quy tắc admin, confidence band, trường trọng yếu, commit qua Action Registry, hoàn tác 7 ngày, xem nguồn, hộp thư, sự cố G4, roster SECRET, lineage, chống prompt injection, UC-07.
- **Đang lỗi (4):**
  - STP không bao giờ commit;
  - HEIC luôn bị từ chối;
  - đổi loại tài liệu khi review bị bỏ qua;
  - **lộ dữ liệu mức 4**.
- **Chưa làm (6):** gợi ý / cảnh báo trùng khi nhập; nháp và lưới; tách/gộp file; gộp vào bản ghi sẵn có; học từ sửa lỗi và KPI IDP; loại tài liệu #5 SOP vào kho tri thức.
- **Sai lệch (3):** hàng chờ review lệch phạm vi hộp thư; mặc định CONFIDENTIAL theo đề xuất chưa duyệt; MinIO.
- **Chưa đầy đủ (12):** xem chi tiết §8.

### 7.14. Tri thức (D14) và Data Foundation (FR-DATA)

- **Tìm kiếm tài liệu:** 3/3 đã kiểm chứng (ngữ nghĩa + từ khóa); qua HTTP vẫn lộ đoạn trích mức 4.
- **FR-DATA:** 3/9 đã kiểm chứng (event backbone, lineage khi commit, ngày hiệu lực). Chưa đầy đủ:
  - MDM chỉ chống trùng khách hàng;
  - DQ thiếu chiều nhất quán và domain IDP;
  - lineage không đọc được cho doanh thu, chi phí, deal;
  - export chỉ 3 báo cáo.

### 7.15. AI Platform và CEO Assistant (D26/D27)

- **Yêu cầu:** 50 tính năng.
- **Đã kiểm chứng (27):** gateway đa provider + fallback, định tuyến theo phân loại, chế độ fixture/live/record, ngân sách, PII, grounding, lọc tool theo quyền, registry 54 tool, policy autonomy, kill switch, xác nhận/từ chối/hoàn tác, phê duyệt tài chính, audit, chi phí, insight theo event, chat SSE, intent routing, replay có nhãn.
- **Đang lỗi (2):**
  - 12/54 tool không chạy được (không có binding hoặc ACT);
  - Evaluation Engine chấm điểm câu trả lời viết sẵn nhưng gắn nhãn model đang chạy.
- **Chưa làm (6):** rate limit; prompt versioning; agent Lite tài chính/kinh doanh; phản hồi 👍/👎; panel AI ngữ cảnh; kiểm bằng chứng đánh giá trước khi nâng autonomy.
- **Chưa đầy đủ (10):** chỉ chạy một agent `ceo` cho mọi role; briefing chỉ hiện dòng tóm tắt; ngân sách theo agent không được áp; v.v.
- **Sai lệch:** NFR hiệu năng.
- **Cần làm rõ:** D-11 so với 02 §5 / CLAUDE §2.2.
- **Demo DB:** 0 insight, 0 AI action, 0 lượt đánh giá.

### 7.16. Dashboard, báo cáo, Metric Store (D28)

- **Dashboard và báo cáo:** 9/26 đã làm.
  - Đã kiểm chứng: điều hướng theo role, API Executive, ô chỉ số, trang trụ cột, panel P01, cache.
  - Chưa làm: dialog tùy chỉnh ô (TC-M21-12 ghi Passed là sai), drill-down tới bản ghi, báo cáo AI theo lịch.
  - Đang lỗi: trang nghiệm thu G1 dùng ngày đồng hồ thật thay vì ngày nghiệp vụ.
  - Lệch spec: KPI phòng ban là số toàn công ty; mỗi trang dùng một query thay vì mỗi widget một query.
- **Metric Store:** 6/12 đã kiểm chứng. 34 chỉ số đều tính từ dữ liệu thật, không có số hardcode.
  - Đang lỗi: nhóm DQ không ai xem được (kể cả CEO, 403).
  - Lệch spec: chỉ số và cảnh báo của module đóng băng vẫn hiện.
  - Chưa làm: tăng trưởng doanh thu cùng kỳ.
  - Chưa đầy đủ: ngưỡng chỉ sửa được trực tiếp trong DB; cảnh báo không gửi MGR.

### 7.17. Product và Risk (đóng băng)

- **Kết quả:** 5/5 mục trong phạm vi D-21 đã kiểm chứng (CRUD API + trang bản ghi mới).
- **Phạm vi:** dashboard, kịch bản, chỉ số sản phẩm là OUT OF SCOPE.
- **Ngoại lệ đóng băng:** chỉ số và cảnh báo vẫn lọt lên dashboard (§7.16); METRIC-CUS-05 (NPS) phụ thuộc provider của module đóng băng.

---

## 8. Feature-level Implementation Matrix

**Ký hiệu trạng thái:**
- **V** = `IMPLEMENTED & VERIFIED`
- **I** = `IMPLEMENTED`
- **P** = `PARTIALLY IMPLEMENTED`
- **NI** = `NOT IMPLEMENTED`
- **B** = `IMPLEMENTED BUT BROKEN`
- **DG** = `DOCUMENTATION GAP`
- **SM** = `SPEC MISMATCH`
- **NC** = `NEEDS CLARIFICATION`
- **OOS** = `OUT OF SCOPE (P1/P2)`

**Cột:**
- FE = giao diện (✗ = không có).
- BE = API / service.
- DB = bảng.
- Test = bằng chứng kiểm thử.

### 8.1. Tổ chức, Nhân sự, Người dùng, Xác thực, RBAC

| ID | Module | Feature | Doc ref | FE | BE/API | DB | Test | Status | Evidence |
|---|---|---|---|---|---|---|---|---|---|
| AUD-ORG-01 | Org | Tổ chức C/R/U/lưu trữ | EP-ORG-01..05 | SCR-66 tạo/sửa; không lưu trữ | `hr/routes/org.py:69-110` | hr.organizations | test_org_api_t613, D-21 | V | lưu trữ chỉ có API |
| AUD-ORG-02 | Org | Phòng ban C/R/U/lưu trữ + `as_of` | EP-ORG-06..10 | SCR-51; **sửa không gửi `version`** | `hr/routes/router.py` | hr.departments | API test; không test UI sửa | B | `OrgForms.tsx:64` vs `core/concurrency.py:38` → 422 |
| AUD-ORG-03 | Org | Đội nhóm C/R/U/D | EP-ORG-11..15 | tạo + lưu trữ; không sửa | `org.py:113-155` | hr.teams | test_team_and_position_crud | P | EP-ORG-14 không có UI |
| AUD-ORG-04 | Org | Vị trí + định biên/trống | EP-ORG-16..20 | SCR-52 C/R/U/D | `org.py:157-199` | hr.positions (0 dòng) | API + E2E admin-screens | V | demo không có vị trí |
| AUD-ORG-05 | Org | Gán nhân sự theo ngày hiệu lực | EP-ORG-21..23 | AssignDialog; không sửa (EP-ORG-23) | structure_service | employee_assignments | test_assignments_t612, E2E admin-org | V | |
| AUD-ORG-06 | Org | Cây `as_of`, không lộ mức 3–4 | EP-ORG-24 | OrgView | `org.py:243` | — | test_tree_as_of_and_no_level4 | V | |
| AUD-ORG-07 | Org | Sơ đồ tương tác có workload | FR-ORG-06 | headcount; không workload | — | — | — | P | |
| AUD-ORG-08 | Org | Báo cáo ma trận / kiêm nhiệm | FR-ORG-02 (P0) | ✗ | một gán nhân sự hiện hành / người | DB unique | test khẳng định điều ngược lại | NI | không có quyết định hoãn |
| AUD-ORG-09 | Org | Import / export cơ cấu | FR-ORG-03 | import SCR-66; ✗ export | ✗ export | — | — | P | |
| AUD-ORG-10 | Org | Wizard onboarding UC-07 | FR-ORG-05, R-DEC-76/79 | admin/onboarding | EP-ADM-13/14 + IDP C5 | — | E2E onboarding-real | V | |
| AUD-ORG-11 | Org | Business Unit | FR-ORG-01 | — | — | — | — | OOS | OQ-05-06 |
| AUD-ORG-12 | Org | Ghi cơ cấu = `hr:admin`; phạm vi ADM `s` | R-DEC-30 | route rules | `require_pillar_permission` | — | test_rbac, permissions.test | V | |
| AUD-HR-01 | HR | Nhân viên CRUD + chuyển `effective_from` | EP-HR-01..05 | /business/hr/records | router EP-82 | hr.employees (154) | test_employee_crud*, E2E m7 | V | |
| AUD-HR-02 | HR | Che mức 3/4 | 02 §5, R-DEC-34 | UI không hiện mức 4 | `core/field_policy.py:90` | pgcrypto | test_level4_masking_by_role | V | |
| AUD-HR-03 | HR | Lịch sử lương (mức 4, chỉ thêm) | EP-HR-07, D-21 | **✗** | `hr_service.py:565-611` | salary_history (442) | test_salary_history_rules | P | API không có UI |
| AUD-HR-04 | HR | Kế hoạch tuyển dụng CRUD | EP-HR-08 | records tab | hiring_service | hiring_plans | test_plan_* | V | form thiếu khoảng lương |
| AUD-HR-05 | HR | Gửi → engine → duyệt (≠ người gửi) | EP-HR-09/10, R-DEC-173 | action + /work/approvals | approval_service | approval_requests | test_submit_approve_reject, E2E m8 | V | |
| AUD-HR-06 | HR | Vòng đời sau duyệt | EP-HR-08 | ✗ | PATCH_TRANSITIONS | — | test_lifecycle_after_approval | P | chỉ API |
| AUD-HR-07 | HR | Phát hiện trễ tuyển dụng | METRIC-HR-04 | — | detect_delayed | — | test_delayed_detection | V | |
| AUD-HR-08 | HR | Dashboard HR | EP-HR-06 | không có màn hình gọi | dashboard_service | — | test_dashboard (6) | V | `revenue_per_employee` luôn None |
| AUD-HR-09 | HR | Workload METRIC-HR-03 | EP-HR-11 | màn hình work | workload | — | test_workload_* | V | bỏ qua nghỉ phép |
| AUD-HR-10 | HR | METRIC-HR-01..04 | 03 PPL | pillar O | metric_provider | metric_values | unit + E2E roles | V | |
| AUD-HR-11 | HR | Danh sách SCR-48 | 06 | EmployeesView | EP-HR-01 | — | E2E roles | V | |
| AUD-HR-12 | HR | Phạm vi EMP/MGR/REV/ADM | DEC-196, R-DEC-30 | canReadHrDirectory | `hr/services/scope.py` | — | test_employee_scoping | V | |
| AUD-HR-13 | HR | **Nghỉ phép** (đầu vào năng lực) | FR-HR-01 P0 | ✗ | ✗ | hr.leaves (0 dòng, không trong 05) | ✗ | NI | bảng chết |
| AUD-HR-14 | HR | Kỹ năng | FR-HR-01 | ✗ | ✗ | employee_skills (0) | ✗ | NI | |
| AUD-HR-15 | HR | Ai xem dashboard HR, quỹ lương | — | — | `scope.py:36-52` | — | test có | DG | |
| AUD-HR-16/17 | HR | Chấm công, lương, AI nhân sự | FR-HR-02..04 | — | — | — | — | OOS | P1 |
| AUD-ADM-01..04 | Admin | Người dùng: list/create/update/khóa-mở | EP-ADM-05..10, R-DEC-36 | UsersView (ADM) | user_admin_service | auth.users | test_create_rules, test_role_change_revokes_refresh, E2E admin-org | V ×4 | DIR `scope_pillars=[]` được chấp nhận (F-07) |
| AUD-ADM-05 | Admin | CEO quản lý người dùng (D-21) | R-DEC-198 vs 06 SCR-53 | `canEdit = role==="ADM"` | API cho phép CEO | — | E2E khẳng định CEO chỉ đọc | SM | `admin/users/page.tsx:9` |
| AUD-ADM-06 | Admin | Ma trận vai trò chỉ đọc | R-DEC-174 | RolesView | EP-ADM-11 | auth.roles | test_roles_and_rbac | V | chú giải thiếu `l/k/u` |
| AUD-ADM-07 | Admin | Vai trò tùy biến | FR-ADM-01 | — | — | — | — | OOS | R-DEC-174 |
| AUD-ADM-08 | Admin | Nhật ký audit | EP-ADM-12 | /admin/audit (chỉ ADM) | platform router | audit_logs | test_audit_log_filters | V | CEO có quyền API nhưng không có route UI |
| AUD-ADM-09 | Admin | Xem như người dùng | FR-ADM-08 | ✗ | ✗ | — | — | NI | |
| AUD-ADM-10 | Admin | Trạng thái onboarding | EP-ADM-13/14 | SCR-66 | onboarding_service | system_settings | E2E | V | |
| AUD-AUTH-01 | Auth | Đăng nhập, khóa 5 lần / 15 phút | EP-ADM-01 | /login | auth_service.login | users | test_auth | V | ngưỡng chưa vào tài liệu |
| AUD-AUTH-02 | Auth | Xoay refresh, tái dùng → thu hồi chuỗi | EP-ADM-02 | BFF | auth_service.refresh | refresh_tokens | test_refresh_rotates_and_reuse | V | |
| AUD-AUTH-03 | Auth | Đăng xuất thu hồi refresh | EP-ADM-03 | **chỉ `signOut()`** | logout có | 208 login / 0 logout | API test; E2E mock | B | `Header.tsx:66` |
| AUD-AUTH-04..07 | Auth | `/auth/me`; JWT RS256 + claims; đăng nhập demo; không `/register` | EP-ADM-04, DEC-129, R-DEC-28, DEC-137 | có | `core/security.py` | — | test_security (16), login.spec | V ×4 | |
| AUD-AUTH-08 | Auth | Rate limit | NFR-SEC-05, CLAUDE §5.5 | — | ✗ | — | ✗ | NI | R-DEC-187 PROPOSED |
| AUD-AUTH-09 | Auth | SSO / MFA / phiên | FR-ADM-04 | ✗ | ✗ | — | ✗ | NI | |
| AUD-AUTH-10 | Auth | Đổi / đặt lại mật khẩu | R-DEC-36 | — | — | — | — | OOS | backlog |
| AUD-AUTH-11 | Auth | Cô lập tenant | FR-ADM-06 | — | repository | tenant_id | test_tenant_isolation | V | |
| AUD-RBAC-01 | RBAC | Ma trận code = DB = JWT | R-DEC-12 | — | permission_matrix | auth.roles | test_roles_and_rbac | V | CEO 32, DIR 28, MGR 22, EMP 7, REV 10, ADM 10, AI 2 |
| AUD-RBAC-02 | RBAC | Ma trận role × quyền trong 02 | 02 (§5.2/5.3 bị trích) | — | code trích mục không tồn tại | — | — | DG | |
| AUD-RBAC-03 | RBAC | Cô lập khối DIR | R-DEC-12a | dirPillars | theo endpoint, không ở tầng quyền | — | test | SM | `core/permissions.py:49-61` |
| AUD-RBAC-04 | RBAC | CEO CRUD toàn quyền (UI) | R-DEC-198 | một phần | đủ | — | test D-21 | P | §10 |
| AUD-RBAC-05 | RBAC | Route mặc định từ chối | 06 §3.3 | permissions.ts | — | — | permissions.test, E2E | V | |
| AUD-RBAC-06 | RBAC | REV đọc HR / mức 4 trong phiên review | 02 §5 | — | luôn 403 | — | test khẳng định 403 | SM | R-DEC-183 PROPOSED |
| AUD-RBAC-07 | RBAC | ADM không đọc dữ liệu nghiệp vụ | 02 §2 | — | STRUCTURE_ONLY | — | test_rbac | V | |
| AUD-RBAC-08 | RBAC | EMP xem mức 4 của chính mình | 02 / ND 13 | — | bị che | — | — | NC | |

### 8.2. Tài chính

| ID | Feature | Doc ref | FE | BE/API | DB | Test | Status | Evidence |
|---|---|---|---|---|---|---|---|---|
| AUD-FIN-01 | Doanh thu CRUD | EP-FIN-01/02 | records | `finance/routes/router.py:109-155` | revenues | test_revenues_expenses_cash, E2E m7 | V | |
| AUD-FIN-02 | Chi phí CRUD + phạm vi MGR | EP-FIN-03 | records | router:159-201 | expenses | test_scope_d07 | V | |
| AUD-FIN-03 | Số dư tiền | EP-FIN-04 "CRUD" | records (không lưu trữ) | không có DELETE (405) | cash_positions | D-21 test khẳng định 405 | SM | service có `delete_cash_position` nhưng không có route |
| AUD-FIN-04/05 | Ngân sách CRUD + trạng thái + cảnh báo vượt | EP-FIN-05 | records + Lite | budget_service | budgets | test_budgets | V ×2 | |
| AUD-FIN-06 | Kiểm ngân sách khi ghi chi phí | FR-FIN-02 | ✗ | chỉ event bất đồng bộ | — | — | P | |
| AUD-FIN-07 | Dự báo P&L | EP-FIN-06 | **✗** | router:313-353 | forecasts | test_forecasts | P | |
| AUD-FIN-08/09 | Hóa đơn CRUD; thanh toán có khóa dòng | EP-FIN-07 | records + SCR-47 | invoice_service | invoices | test_invoices, concurrent test, E2E | V ×2 | |
| AUD-FIN-10 | Thực thể Payment | 05 §3 | — | gộp vào `paid_amount` | **không có bảng** | — | P | |
| AUD-FIN-11 | Hóa đơn OUT theo MST | R-DEC-172 | field | client_directory | — | test_invoice_client_by_mst | V | |
| AUD-FIN-12 | Job quá hạn | 03 | — | worker | — | test_overdue | V | |
| AUD-FIN-13 | Dòng tiền 13 tuần | EP-FIN-10 | **✗** | router:450-468 | cash_flow_forecasts | test_cash_flow | P | tool AI đăng ký nhưng không bind |
| AUD-FIN-14 | What-if runway | EP-FIN-09 | chỉ đọc 0/0/0 | router:436 | — | test_what_if_baseline | V | |
| AUD-FIN-15 | Quy tắc burn / runway | 03 §6 | — | rules.py | — | unit + test_analytics | V | |
| AUD-FIN-16 | Dashboard tài chính đọc Metric Store | 03 §4.3 | drill + Lite | **tính lại lúc request**; `freshness` luôn "fresh" | — | test chỉ so ngay sau recompute | SM | analytics_service:229-284 |
| AUD-FIN-17/18 | METRIC-FIN-01..07; FIN-01 theo D-09 | 03 §4, R-DEC-186 | tiles | metrics.py | metric_values | test_store_and_dashboard_agree, test_fin01 | V ×2 | D-09 vẫn PROPOSED |
| AUD-FIN-19 | Store cập nhật sau ghi tay | 03 §4.3 | — | không phát event | — | test gọi recompute thủ công | P | |
| AUD-FIN-20 | Chỉ tiêu Q4 = 20 tỷ | R-DEC-186 | — | FIN-01 dùng chỉ tiêu tháng | Q4 = 20 tỷ vs 3 tháng = 85 tỷ | — | NC | sales_seed.py:58-65 |
| AUD-FIN-21 | Finance Lite SCR-46 | 06, TC-M22-07 | thiếu lineage, độ tươi, chọn kỳ | — | — | E2E chỉ kiểm có hiện | P | |
| AUD-FIN-22 | Drill-down + lineage 3 cấp | 06 SCR-03 | FinanceDrillView | — | — | E2E finance-drill | V | ghép thẻ ↔ chỉ số sai (F-15) |
| AUD-FIN-23 | Danh sách hóa đơn SCR-47 | 06 | InvoicesView | EP-FIN-07 | — | không có test UI tích cực | I | |
| AUD-FIN-24 | Trang bản ghi tài chính | R-DEC-170 | RecordCrud | — | — | E2E m7 | V | |
| AUD-FIN-25/26 | D-07 REV/MGR; D-20 MGR đọc hóa đơn mình tạo | R-DEC-183/199 | route rules | `finance/services/scope.py` | — | test_scope_d07, test_mgr_invoice_read_d20 | V ×2 | quyết định chưa duyệt |
| AUD-FIN-27 | CEO CRUD tài chính (D-21) | R-DEC-198 | records | đủ, trừ DELETE số dư tiền / dự báo | — | test_ceo_finance_crud, E2E | P | |
| AUD-FIN-28 | Cô lập khối F | R-DEC-12a | dirPillars | require_pillar_permission | — | test_business_scope_m22 | V | |
| AUD-FIN-29 | MGR `finance:query ◑d` | permission_matrix:193 | thẻ hub MGR | dashboard / what-if không có phạm vi | — | ✗ | SM | router.py:424-446 |
| AUD-FIN-30 | Nguồn + thời gian + cảnh báo thiếu dữ liệu | FR-FIN-04 | thiếu | freshness hardcode | — | — | P | |
| AUD-FIN-31 | Lọc `source` doanh thu | EP-FIN-01 | — | ✗ | — | — | SM | |
| AUD-FIN-32 | Đồng bộ phần mềm kế toán | FR-FIN-01 | — | chỉ upload báo cáo qua IDP | — | — | NC | |
| AUD-FIN-33/34 | Phát hiện bất thường bằng AI; tài chính đầy đủ | US-FIN-004/005 | — | — | — | — | OOS | P1 |
| AUD-FIN-35 | Tool AI tài chính theo phạm vi REST | TC-V4-24 | — | tool_executor:333-428 | — | test_tool_scope_d07 | V | |
| AUD-FIN-36 | Mô tả field-level 10 bảng tài chính | 05 | — | models | 0002 | — | DG | |
| AUD-FIN-37/38 | Audit mọi mutation; METRIC-FIN-07 burn vs dự báo | 10, 03 | — | — | — | test_audit, test_burn_over_forecast | V ×2 | |
| AUD-FIN-39 | Phê duyệt ngân sách CEO/CFO | 02 §7 | — | ghi thẳng | — | — | NC | |

### 8.3. Kinh doanh / CRM

**Theo spec Aureon:**

| ID | Feature | Doc ref | FE | BE/API | DB | Test | Status | Evidence |
|---|---|---|---|---|---|---|---|---|
| AUD-SAL-A01 | Cơ hội Lite | FR-SAL-01, EP-SAL-02 | records deals | sales_service:315-377 | deals | test_deal_crud_rules, E2E m7 | V | |
| AUD-SAL-A02 | Coverage, win rate, chu kỳ trong Metric Store | FR-SAL-04 | tiles | metric_provider | store | unit + test_providers | V | |
| AUD-SAL-A03 | AI Sales | FR-SAL-03 | — | tool pipeline / list_deals | — | — | NC | |
| AUD-SAL-A04 | Dashboard v4 (bookings, attainment) | EP-SAL-07 | **không hiển thị** | analytics:214-256 | — | test_dashboard_contract | V (API) | UI thiếu (F-08) |
| AUD-SAL-A05 | Funnel tích lũy | EP-SAL-09 vs BRD_NF §2.8 | bảng | analytics:155 | stage_history | test_funnel_*, E2E m8 | NC | |
| AUD-SAL-A06..A08 | Event thắng/thua; khách hàng duy nhất; chặn xóa khách hàng có con | 10 §9.2, 04 §13.1, R-DEC-198 | — | — | — | test có | V ×3 | |
| AUD-SAL-A09 | **Xóa deal giữ toàn vẹn** | R-DEC-198 | archive | **không kiểm con** | — | test xóa hợp đồng trước | B | sales_service:371-377 |
| AUD-SAL-A10..A16 | Hợp đồng; chỉ tiêu; chuyển giai đoạn tiến; lịch sử; D-07; cô lập khối; CEO CRUD qua API | EP-SAL-03/04/08, DEC-191..193, R-DEC-183/198 | có | có | có | test_contracts, test_target_crud, test_stage_*, test_scope_d07, test_ceo_sales_crud | V ×7 | |
| AUD-SAL-A17 | CEO CRUD qua UI | R-DEC-198 | records, Kanban | — | — | E2E chỉ kiểm nút tạo | I | |
| AUD-SAL-A18 | Chuyển lead (1 transaction) | EP-SAL-13 | action | crm_service:247 | — | TC-V4-CRM-06/07 | V | không có E2E |
| AUD-SAL-A19 | Lead phải Qualified mới chuyển | BRD_NF BR-002 | mọi trạng thái | crm:254 | — | ✗ | SM | |
| AUD-SAL-A20..A23 | Migration 0028; hoạt động theo lead; màn hình CRM; hóa đơn OUT theo MST | 05 §2.13, TC-V4-CRM-13, 06 §3.5, R-DEC-172 | có | có | có | test có | V ×4 | 0028 dựa trên R-DEC chưa duyệt |
| AUD-SAL-A24 | Ma trận phạm vi sales trong 02 | 02 (bị trích) | — | — | — | — | DG | |

**Theo BRD_Newfeature** (107 tính năng; Must / Should như BRD; OOS = P1 theo R-DEC-05/09 hoặc bị hoãn bởi tập con D-08):

| Nhóm | V | I | P | OOS | Chi tiết |
|---|---|---|---|---|---|
| Dashboard (DASH-001..010) | 2 (003, 006) | — | 6 (001, 002, 004, 005, 007, 008) | 2 (009, 010) | UI thiếu attainment, bookings, bộ lọc |
| Lead (LEAD-001..012) | 6 (001–004, 009, 010) | — | 5 (005, 006, 007, 011, 012) | 1 (008) | không có trang Lead Detail |
| Account (ACC-001..011) | 7 (001–004, 007–009) | — | 2 (005, 010) | 2 (006, 011) | |
| Contact (CONT-001..009) | 6 (001–005, 009) | 1 (008) | 2 (006, 007) | — | vai trò 6 so với BRD 8 |
| Opportunity (OPP-001..014) | 7 (001–004, 007, 008, 013) | — | 2 (006, 014) | 5 (005, 009, 010, 011, 012) | BANT, liên hệ ↔ deal hoãn |
| Pipeline (PIPE-001..012) | 5 (003, 004, 005, 008, 009) | — | 3 (007, 010, 012) | 4 (001, 002, 006, 011) | cấu hình pipeline hoãn |
| Activity (ACT-001..009) | 4 (001, 002, 004, 006) | 2 (003, 007) | 1 (009) | 2 (005, 008) | |
| Funnel (FUN-001..010) | 2 (002, 003) | — | 2 (001, 007) | 6 (004, 005, 006, 008, 009, 010) | |
| Forecast (FC-001..010) | 2 (001, 002) | — | — | 8 (003–010) | snapshot hoãn |
| Performance (PERF-001..010) | 6 (001–005, 007) | — | 2 (008, 009) | 2 (006, 010) | |
| Business rules (BR-001, 003..019) | 6 (001, 003, 004, 007, 011, 012) | — | 5 (008, 014, 015, 018, 019) | 7 (005, 006, 009, 010, 013, 016, 017) | BR-002 tính ở A19 |
| **Tổng** | **53** | **3** | **30** | **39** | 15 mục Must thuộc OOS |

### 8.4. Mục tiêu, Công việc, Họp, Lịch, Phê duyệt, Thông báo

| ID | Feature | Doc ref | FE | BE/API | DB | Test | Status | Evidence |
|---|---|---|---|---|---|---|---|---|
| AUD-STR-01/02 | Chiến lược / Mục tiêu chiến lược CRUD | EP-STR-02..11 | **chỉ tạo + xem** | strategy_service | strategies, SO | test_strategy_t626, D-21 | P ×2 | `StrategyEditors.tsx:33,77` |
| AUD-STR-03/04 | Initiative + mốc | EP-STR-12..21 | **✗** (chỉ nút trong cây) | initiative_service | initiatives, milestones | test_initiatives | P ×2 | |
| AUD-STR-05/06 | Cây mục tiêu; SEI | EP-STR-01/22, METRIC-STR | SCR-41, home | goal_tree, metrics | — | test_tree_t628, test_metrics_t630 | V ×2 | |
| AUD-STR-07 | Import kế hoạch chiến lược | FR-STR-06 | /data | chỉ PLAN_KPI_OKR | — | — | P | |
| AUD-STR-08 | What-if chiến lược | FR-STR-05 | — | — | — | — | OOS | |
| AUD-KPI-01..04, 09 | KPI CRUD; target theo ngày hiệu lực; lịch sử đo; ngưỡng + đánh giá; cảnh báo dưới ngưỡng | EP-KPI-01..10 | /goals, SCR-58 | kpi_* services | kpis, targets, measurements | test_measure_t627, test_goal_events_t629, E2E m5 | V ×5 | |
| AUD-KPI-05 | Cascade, tổng trọng số = 100% | FR-KPI-06 | — | không kiểm tổng | — | — | P | |
| AUD-KPI-06 | So sánh phòng ban | FR-KPI-07 | chỉ lọc | — | — | — | P | |
| AUD-KPI-07 | Khóa kỳ | FR-KPI-08 | — | chỉ chặn; không có thao tác khóa | locked_at (0/36) | — | P | `kpi_target_service.py:129` |
| AUD-KPI-08 | Nguồn dữ liệu tự động | FR-KPI-02 | form | — | — | — | P | |
| AUD-OKR-01..04, 06 | Objective (2–5 KR); KR; lịch sử KR; căn chỉnh; at-risk | EP-OKR-01..11 | /goals, SCR-59 | okr_service, at_risk | — | test_okr_kpi, E2E goals | V ×5 | |
| AUD-OKR-05 | Committed / aspirational | FR-OKR-03 | form | okr_type | — | — | I | |
| AUD-OKR-07/08 | AI kiểm chất lượng OKR; O/KR không có hành động | FR-OKR-05/06 | ✗ | ✗ | — | — | NI ×2 | |
| AUD-PRF-01/02/04 | Check-in; feed + thẻ đến hạn; nhắc thứ Sáu | EP-PRF-01..06 | SCR-60 | — | check_ins | test_check_ins_due, test_weekly_checkin_reminder | V ×3 | |
| AUD-PRF-05 | Khung KPI/OKR theo phòng ban | US-PERF-001 | ✗ | ✗ | — | — | NI | |
| AUD-PRF-03/06 | Check-in giọng nói; chu kỳ đánh giá | R-DEC-166, FR-PERF | — | — | — | — | OOS ×2 | |
| AUD-TSK-01..06 | Task CRUD (7 trạng thái); task con 1 cấp; phụ thuộc; Kanban; xin chuyển → duyệt; quá hạn | EP-TASK-01..08, 19 | SCR-42 | task_service | tasks | test_tasks, test_dependencies, E2E work | V ×6 | |
| AUD-TSK-07 | Bắt buộc bằng chứng | FR-TASK-04 | — | chỉ lưu | — | — | P | |
| AUD-TSK-08 | Task định kỳ / mẫu | FR-TASK-03 | ✗ | ✗ | — | — | NI | |
| AUD-TSK-09 | Xem timeline / lịch | FR-TASK-01 | list + Kanban | — | — | — | P | |
| AUD-TSK-12 | Xóa task từ panel | R-DEC-201 | TaskDelete | — | — | chỉ API | I | |
| AUD-PRJ-01/02 | Dự án CRUD; cờ trễ | EP-TASK-09..13 | SCR-55 + records | ProjectService | projects | test_project_crud | V ×2 | |
| AUD-PRJ-03 | Mốc dự án | EP-TASK-14..17 | thêm + đánh dấu xong | — | — | test | P | `Milestones.tsx:27` |
| AUD-WL-01/02 | Heatmap; quá tải > 110% | EP-TASK-18 | SCR-57 | workload | — | test, E2E | V ×2 | |
| AUD-WL-03/05 | AI gợi ý điều chuyển; ước lượng có nhãn | FR-WL-02/03 | ✗ | ✗ | — | — | NI ×2 | |
| AUD-WL-04 | Năng lực trừ nghỉ phép / họp | BRD §8.1 vs R-DEC-44 | — | 40h cố định | — | — | NC | |
| AUD-MTG-01, 02, 06 | Họp CRUD; transcript → preview; ghép tên gần đúng | EP-EXE-03, EP-DC-38 | records, /meetings | — | meetings | D-21, E2E meetings, TC-M23-06 | V ×3 | |
| AUD-MTG-03 | **Duyệt việc cần làm → Task** | FR-MTG-04, R-DEC-101/104 | **chỉ đổi state cục bộ** | ACT không có caller | action_items (6, 0 có task_id) | E2E chỉ kiểm nhãn | B | `PredictedActionList.tsx:42` |
| AUD-MTG-04 | Tóm tắt họp bằng AI | FR-MTG-02 | — | chỉ test gọi | 1 dòng seed | unit | P | |
| AUD-MTG-05/07 | Quyết định từ biên bản; briefing trước họp | FR-MTG-05/07 | ✗ | ✗ | — | — | NI ×2 | |
| AUD-MTG-08 | Bot dự họp / ghi âm | FR-MTG-01/06 | — | 422 | — | — | OOS | |
| AUD-DEC-01/02 | Quyết định C/R/U; log 30/60/90 | R-DEC-135 | records, /knowledge/decisions | meeting_service | decisions | D-21, test_decision_log | V ×2 | |
| AUD-DEC-03 | Job nhắc review | R-DEC-135 | — | có; nhắc cả quyết định đã hủy | — | ✗ | I | |
| AUD-DEC-04 | Xác minh kết quả | R-DEC-135 | ✗ | PATCH có | — | — | P | |
| AUD-CAL-01 | Sự kiện lịch của mình | EP-CAL-01..05 | C/R/D (không sửa) | calendar_service | calendar_events | D-21 | V | |
| AUD-CAL-02 | **Hạn task → sự kiện của người được giao** | R-DEC-122 | — | `owner_id = assignee_id` (mã nhân viên) | — | test khẳng định mã nhân viên | B | task_service:236-241 |
| AUD-CAL-03 | **OAuth Google / Outlook** | EP-INT-01..04 | /settings/integrations | callback đòi Bearer | calendar_accounts | chỉ unit | B | integrations.py:47-55 |
| AUD-CAL-04/05 | Đồng bộ 2 chiều; token hết hạn | R-DEC-121 | — | calendar_sync | — | unit | V / I | chưa chạy live |
| AUD-CAL-06..08 | AI hỏi lịch; gợi ý khung giờ; phân tích họp | FR-CAL-02..04 | — | — | — | — | NC ×3 | xung đột R-DEC-123 |
| AUD-WF-01/02 | Hộp duyệt; quy tắc, 2 bước, phạm vi | EP-WF-01..03 | SCR-43 | approval_service | approval_requests | test_workflow_m13, E2E | V ×2 | |
| AUD-WF-03 | SLA / escalation / hết hạn | FR-WF-04 | cờ quá hạn | không có job; EXPIRED bị rollback | — | — | P | approval_service:385 |
| AUD-WF-04/05 | Workflow cấu hình; CEO quyết `task_reassign` | FR-WF-02.., D-21 vs R-DEC-45 | — | — | — | — | OOS / NC | |
| AUD-NTF-01..03 | Danh sách / đọc; email + tùy chọn; event cảnh báo | EP-NTF-01..05 | bell | — | notifications | test_notifications_t616, Mailpit | V ×3 | |
| AUD-NTF-04 | Nhắc việc sắp đến hạn | FR-NTF-02 | — | chỉ quá hạn | — | — | P | |
| AUD-EXE-01/02 | Dashboard điều hành; trang bản ghi điều hành | EP-49, R-DEC-201 | home, records | — | — | test_dashboard, E2E m7 | V ×2 | |

### 8.5. Thu thập dữ liệu / IDP, Tri thức, Data Foundation

| ID | Feature | Doc ref | FE | BE/API | DB | Test | Status | Evidence |
|---|---|---|---|---|---|---|---|---|
| AUD-CAP-01 | C1: form sinh từ schema | FR-DC-01 | SCR-61 SchemaForm | manual_service | source_documents | test_manual_c1_t635, E2E capture | V | |
| AUD-CAP-02 | Gợi ý + cảnh báo trùng khi nhập | FR-DC-02 | ✗ | ✗ | — | — | NI | |
| AUD-CAP-03 | C2 văn bản tự nhiên → preview | FR-DC-03 | chỉ /meetings | natural_language | — | test_natural_language_m23 | P | không có lối nhập chung |
| AUD-CAP-04 | C2 giọng nói (STT live) | OQ-04-02 | nút tắt | chỉ fixture | — | — | OOS | R-DEC-166 |
| AUD-CAP-05 | Nháp + sửa hàng loạt dạng lưới | FR-DC-04 | ✗ | ✗ | — | — | NI | |
| AUD-CAP-06 | Audit sửa + bắt buộc lý do với trường tiền | FR-DC-05 | ReviewDetail | review_service:311 | audit_logs | test_correct_financial_field_requires_reason | V | |
| AUD-CAP-07 | Nhập trên di động | FR-DC-06 | PWA | — | — | E2E mock | P | |
| AUD-CAP-08 | C3 upload 1..100 file | FR-DC-07/09 | DropZone | upload_service | — | test_upload_* | V | |
| AUD-CAP-09 | Định dạng + giới hạn | FR-DC-07 | nhận .heic | `mime.py:81` | — | ✗ HEIC | B | HEIC luôn 415; giới hạn 300 trang không áp; .doc/.xls không đọc được |
| AUD-CAP-10/11 | Quét malware + quarantine; chống trùng SHA-256 | FR-DC-08 | — | malware_scan, upload_service | — | test có | V ×2 | SKIPPED không chặn STP (F-11) |
| AUD-CAP-12 | Ảnh: xoay / nắn thẳng / tương phản | FR-DC-08 | CameraCapture | chỉ xoay EXIF + autocontrast | — | unit | P | |
| AUD-CAP-13/14 | Kiểm text layer → OCR; tách trang | 04 §3 | — | preprocess, pipeline | document_pages | test có | V ×2 | |
| AUD-CAP-15 | Tách 1 file thành nhiều tài liệu / gộp ảnh | FR-DC-10 | ✗ | ✗ (SPLIT trong enum không dùng) | — | — | NI | |
| AUD-CAP-16 | Phân loại 4 tầng | FR-DC-09 | — | classifier | — | test_classifier_t634 (9) | V | |
| AUD-CAP-17 | Loại tài liệu P0 #1–#6 | 04 §5 | — | catalog | 7 loại | test | P | thiếu #5 SOP/Policy |
| AUD-CAP-18/19 | Admin schema + quy tắc kiểm tra | EP-DC-27..35 | SCR-63 | admin_service | — | test_capture_admin_t634 | V ×2 | |
| AUD-CAP-20 | Field = value / confidence / vị trí; checkbox / chữ ký | FR-DC-11/12 | FieldRow | extractor | — | test vị trí | P | FR-DC-11 chưa có |
| AUD-CAP-21 | Chuẩn hóa tiếng Việt | FR-DC-13 | — | validator | — | test | V | |
| AUD-CAP-22 | Kiểm nghiệp vụ (tổng + VAT, MST, trùng) | FR-DC-14 | — | một phần | — | test | P | |
| AUD-CAP-23 | Confidence band 0,90 / 0,60 | DEC-133 | Badge | extractor:37 | — | test_confidence_bands | V | |
| AUD-CAP-24 | **STP → COMMITTED** | FR-DC-15, 04 §4 | hiện là "committed" | dừng ở `AUTO_APPROVED`; ngưỡng hardcode | — | không test commit STP | B | `pipeline.py:260`, `inbox_service.py:43`, `schemas/capture.py:102` |
| AUD-CAP-25/26 | Trường trọng yếu luôn qua người; commit qua Registry v2 | FR-DC-16/17 | — | critical, commit_service | document_actions | test_critical_t640, test_action_registry_v2 | V ×2 | |
| AUD-CAP-27 | C5 import (map, preview, lỗi dòng, file lỗi) | FR-DC-18 | SCR-62 | import_service | import_batches | test_import_c5_t635, E2E | V | |
| AUD-CAP-28 | Review song song + tô sáng nguồn | FR-DC-19 | text layer, không ảnh trang | EP-DC-05 | — | E2E | P | |
| AUD-CAP-29 | Màu, "chấp nhận tất cả mức cao", bàn phím | FR-DC-20 | ✗ | API có | — | test API | P | |
| AUD-CAP-30 | Hàng chờ theo phòng / vai + SLA 1 ngày làm việc | FR-DC-21 | SCR-18a | queue, sla_service | — | test SLA | SM | 24 giờ lịch; DIR không theo khối |
| AUD-CAP-31/32 | Khóa mềm 15 phút; duyệt / từ chối | EP-DC-06..10 | có | review_service | — | test + E2E | V ×2 | |
| AUD-CAP-33/34 | Giao lại reviewer; gộp tài liệu | EP-DC-11/12 | **✗** | có | — | test | P ×2 | |
| AUD-CAP-35 | Gộp vào bản ghi có sẵn | 04 §6.4 | ✗ | ✗ | — | — | NI | |
| AUD-CAP-36 | Đổi loại tài liệu khi review | FR-DC-22 | ✗ | field nhận nhưng bỏ qua | — | — | B | `schemas/__init__.py:206` |
| AUD-CAP-37..41 | Commit 2 bước; hoàn tác 7 ngày; xem gốc; hộp thư; sự cố G4 | EP-DC-13..37 | có | có | có | test + E2E | V ×5 | CEO không có UI sự cố |
| AUD-CAP-42 | Mặc định CONFIDENTIAL (D-11) | R-DEC-188 PROPOSED vs 02 FR-ADM-05 | — | pipeline:66 | — | test_d11_sensitivity | SM | theo đề xuất chưa duyệt |
| AUD-CAP-43 | Roster SECRET: không model, không embedding | R-DEC-188 | — | extractor, knowledge_index | — | test có | V | |
| AUD-CAP-44 | **Che mức 4 trên mọi đường đọc IDP; mã hóa lưu trữ** | CLAUDE §5.3, 04 §9, 05 §2.7 | — | che ở review field; **không** ở EP-DC-03, pages, EP-24 | `extracted_fields.value` jsonb plaintext | chỉ test field review | B | `query_service.py:58`, `review_service.py:191`, `inbox_service.py:176` |
| AUD-CAP-45 | Chống prompt injection | 04 §9 | — | prompt_safety | — | test có | V | |
| AUD-CAP-46/47 | Lưu giữ theo loại; state SUPERSEDED | 04 §9, §4 | — | một phần | — | — | P ×2 | |
| AUD-CAP-48 | Học từ sửa lỗi; nới STP; KPI IDP | 04 §8 | ✗ | ✗ | — | — | NI | |
| AUD-CAP-49 | UC-06 biên bản → việc | 04 §11 | /meetings | actions/meeting | — | E2E (tag mock) | I | bước tạo task hỏng (AUD-MTG-03) |
| AUD-CAP-50 | UC-07 import roster | 04 §11 | SCR-66 | có | — | E2E onboarding-real | V | |
| AUD-CAP-51 | SOP → kho tri thức | 04 §5/§11 | ✗ | ✗ | — | — | NI | |
| AUD-CAP-52/53 | Kênh C6–C10; loại tài liệu #7–#14 | 04 | — | — | — | — | OOS ×2 | |
| AUD-CAP-54 | Lưu trữ MinIO / S3 | CLAUDE §2.2 | — | chỉ file cục bộ | — | unit storage | SM | |
| AUD-CAP-55 | Lineage khi commit | FR-DATA-04 | — | lineage.py:39 | data_lineage | test_lineage_t637 | V | |
| AUD-KB-01..03 | Tìm tài liệu ngữ nghĩa + từ khóa; index bge-m3; tool AI giới hạn mức ≤ 3 | EP-24, DEC-142 | /knowledge | knowledge_search / index | embedding (0 vector trên demo) | test_knowledge_fallback, test_index_*, test_level_4_excluded_for_ai | V ×3 | HTTP lộ đoạn trích mức 4 (C-01) |
| AUD-DF-01 | MDM (owner, chống trùng 6 master) | FR-DATA-01 | — | chỉ khách hàng | — | — | P | |
| AUD-DF-02 | DQ 4 chiều theo domain + cảnh báo | FR-DATA-02 | — | 3 chiều, thiếu domain idp | dq_domain_scores | test_capture_dq_t639 | P | |
| AUD-DF-03 | METRIC-DQ-02 (G3) | R-DEC-68 | acceptance | capture_metrics | — | test | V | |
| AUD-DF-04 | Độ tươi dữ liệu | FR-DATA-03 | tiles | briefing_service | — | chưa đọc test | I | |
| AUD-DF-05 | Đọc lineage ≤ 3 click tới trang nguồn | FR-DATA-04 | LineageChip ở 2 nơi | whitelist thiếu bảng finance/sales | — | test_lineage | P | `lineage_service.py:20` |
| AUD-DF-06 | Event backbone | FR-DATA-05 | — | core/events | — | tests/events | V | |
| AUD-DF-07 | Metric store | FR-DATA-06 | — | catalog | — | (xem §8.7) | I | |
| AUD-DF-08 | Ngày hiệu lực | FR-DATA-07 | as_of | org, kpi_targets | valid_from/to | test_org_api, test_assignments | V | |
| AUD-DF-09 | Export toàn bộ dữ liệu | FR-DATA-08 | Reports | 3 báo cáo | — | — | P | |

### 8.6. AI Platform và CEO Assistant

| ID | Feature | Doc ref | FE | BE/API | DB | Test | Status | Evidence |
|---|---|---|---|---|---|---|---|---|
| AUD-AI-01 | AIC-01 AI Gateway (JWT, rate limit, ngân sách, PII) | 07 AIC-01 | — | thiếu rate limit | — | ngân sách, PII | P | |
| AUD-AI-02 | AIC-02 chọn agent | 07 AIC-02 | /ask | luôn `ceo` | agent_profiles | intent tests | P | `agent_catalog.py:15` |
| AUD-AI-03 | ≤ 8 tool / lượt; 5 s / tool | 07 §4 | ThinkingState | có | — | 5 s có test; ≤ 8 chưa | I | |
| AUD-AI-04/05 | Gateway đa provider, retry, fallback, circuit breaker; định tuyến theo phân loại | 07 §4, 02 §5 | — | gateway, routing | model_call_logs | test_model_gateway | V ×2 | |
| AUD-AI-06 | D-11: INTERNAL không lên cloud | R-DEC-188/194 PROPOSED | — | **chỉ bằng cấu hình**; mặc định code + `.env.example` = cloud | — | test_chat_v4_honesty | NC | `config.py:68`, `.env.example:67-68` |
| AUD-AI-07/08 | Chế độ fixture / live / record; ngân sách tháng → 429 | CLAUDE §5.5 | usage | gateway | — | test có | V ×2 | |
| AUD-AI-09 | Ngân sách theo agent / phòng; cảnh báo 80% | FR-AIQ-05 | sửa được | không áp | — | flag | P | |
| AUD-AI-10 | Rate limit 20 / phút / người | CLAUDE §5.5 | — | ✗ | — | — | NI | |
| AUD-AI-11..14 | PII filter; grounding + trích dẫn; lọc tool theo quyền; registry 54 tool | P05, P06, 10 §2.3 | SourceChip | prompt_guard, grounding, registry | — | test_pii_filter, test_grounding*, test_tool_advertise, contract catalog | V ×4 | |
| AUD-AI-15 | Tool đăng ký chạy được | 10 §2.3 | — | **12/54 không chạy được** | — | contract chỉ kiểm tên | B | `tool_executor.py:81,517-530` |
| AUD-AI-16 | Truy xuất tri thức theo quyền | R-DEC-141 | /knowledge | KnowledgeSearchService | — | unit | V | vector chưa kiểm (0 embedding) |
| AUD-AI-17 | Bộ nhớ (xem + xóa) | 07 AIC-08 | danh sách hội thoại | không có DELETE | — | test history | P | |
| AUD-AI-18 | Versioning prompt + gate + rollback | 07 AIC-05 | — | prompt hardcode | — | — | NI | |
| AUD-AI-19..22 | Policy engine; policy CRUD; kill switch; agent profile | R-DEC-71..73 | /admin/ai | autonomy, policy_service, kill_switch | — | test_agents_autonomy_m16, E2E onboarding (kill switch) | V ×4 | |
| AUD-AI-23 | Agent Lite tài chính / kinh doanh | 10 §4.2 | — | không seed | — | — | NI | |
| AUD-AI-24..28 | Tool ghi → L0..L3; xác nhận / từ chối / hoàn tác 24h; phê duyệt ngưỡng; audit; chi phí và log | DEC-134/155, R-DEC-74 | ActionCard, /ask/activity, logs | action_service | ai_actions | test_chat_actions_m16, E2E onboarding, m5-telemetry | V ×5 | |
| AUD-AI-29 | Evaluation Engine | R-DEC-138..140 | /admin/ai/evaluation | chấm câu trả lời viết sẵn, gắn nhãn model thật | ai_evaluations (0) | unit chấm điểm | B | `evaluation_service.py` |
| AUD-AI-30 | Phản hồi 👍 / 👎 | FR-AIQ-04 | ✗ | ✗ | ai.feedback (0) | — | NI | |
| AUD-AI-31 | Hiệu chỉnh độ tin cậy | FR-AIQ-03 | band | tĩnh | — | — | P | |
| AUD-AI-32 | Event → insight | R-DEC-108 | — | consumers | insights (0 trên demo) | test_ai_kpi_insight_m24 | V | |
| AUD-AI-33 | Insight 9 phần | 03 §5 | InsightCard | phần Action không thực thi được | — | test | P | |
| AUD-AI-34..39 | Xác minh 24h / 7d; chat sync; SSE; lịch sử; intent routing; replay có nhãn | AI-R10, 10 §7.2.5, R-DEC-200 | ChatView | chat_service, intent | conversations | test có + E2E ceo-7steps | V ×6 | |
| AUD-AI-40 | CEO Daily Briefing 7 khối | 03 §3 | **chỉ dòng tóm tắt** | briefing_service + job | briefings (5) | test grounding | P | `BriefingBanner.tsx:40` |
| AUD-AI-41 | CEO Assistant 12 năng lực | 03 §2 | /ask | thiếu dự báo, what-if, báo cáo, nhắc, nhập liệu | — | — | P | |
| AUD-AI-42 | ⌘K | R-DEC-112 | CommandPalette | — | — | E2E mock | I | |
| AUD-AI-43 | Component + nhãn "AI gợi ý / soạn / đã làm" | 06 §6 | components/ai | — | — | Vitest + E2E | V | |
| AUD-AI-44/48 | Panel AI ngữ cảnh; nâng autonomy cần bằng chứng + 2 bên | 06 §6.1, 02 §6/§7 | ✗ | ✗ | — | — | NI ×2 | |
| AUD-AI-45 | Nút Dừng | 06 §6.1 | chỉ "chat mới" | — | — | — | P | |
| AUD-AI-46 | AI Control Center SCR-64 | R-DEC-79 | /admin/ai | admin routes | — | test RBAC; E2E mock | V | |
| AUD-AI-47 | Embedding bge-m3 local | R-DEC-141 | — | gateway.embed | 0 vector | fixture | I | |
| AUD-AI-49 | Phạm vi AI theo phòng × vai × agent × tool | FR-ADM-03 | — | không có chiều phòng ban | — | — | P | |
| AUD-AI-50 | NFR-PERF-02 | 07 §6.2 | — | 13–67 s | — | — | SM | chỉ R-DEC-200 (chưa duyệt) chấp nhận |
| AUD-AI-51 | Circuit breaker | — | — | gateway.CircuitBreaker | — | test | DG | |
| AUD-AI-52 | Phân loại mặc định | FR-ADM-05 vs D-11 | — | IDP = CONFIDENTIAL, chat = INTERNAL | — | — | NC | |
| AUD-AI-53..55 | STT; L4; đa agent sâu | R-DEC-166, 02 §6 | — | — | — | — | OOS ×3 | |

### 8.7. Dashboard, Báo cáo, Metric Store, Platform, Product, Risk

| ID | Feature | Doc ref | FE | BE/API | DB | Test | Status | Evidence |
|---|---|---|---|---|---|---|---|---|
| AUD-RPT-01..04 | Điều hướng theo vai; API Executive; dòng tóm tắt i18n; 4 ô + stale + mở P01 | 06 SCR-40, EP-RPT-01 | home | reporting_service | metric_values | test_reporting, E2E home, nfr-real | V ×4 | |
| AUD-RPT-05 | Ô hiện "cập nhật dd/MM HH:mm" | 06, FR-DATA-03 | chỉ cờ stale | computed_at có | — | — | P | |
| AUD-RPT-06 | API tùy chọn ô | R-DEC-87 | — | preference_service | user_preferences | test_executive_tiles (8) | V | |
| AUD-RPT-07 | **Dialog tùy chỉnh ô** | 06 SCR-40 | ✗ (chỉ trong mock) | — | — | TC-M21-12 ghi Passed | NI | tuyên bố trong 14 sai |
| AUD-RPT-08..11, 13 | Widget SEI + cây; "Cần anh quyết" có hành động; khối Rủi ro; "AI đã làm" có hoàn tác; panel AI | 03 §1.1 | chỉ số đếm + link | — | — | — | P ×4; Rủi ro = SM | khối Rủi ro gồm cảnh báo của module đóng băng |
| AUD-RPT-12 | Mỗi widget một query | FR-DSH-07 | mỗi trang một query | — | — | — | SM | |
| AUD-RPT-14/16 | API Department / Employee | EP-RPT-02/03 | — | KPI phòng là số toàn công ty; thiếu field | — | test | SM ×2 | |
| AUD-RPT-15/17 | UI Department / Employee | 03 §1.1 | thiếu chọn phòng, rủi ro, lịch | — | — | E2E home | P ×2 | |
| AUD-RPT-18 | Briefing 7 khối trên home | 03 §3.1 | chỉ dòng tóm tắt | — | — | Vitest | P | |
| AUD-RPT-19/20 | Trang trụ cột; panel P01 + trang chỉ số | R-DEC-16, R-DEC-156 | có | — | — | E2E dashboard, m5-routes | V ×2 | |
| AUD-RPT-21 | **Drill-down chỉ số → bản ghi → tài liệu** | FR-RPT-04, P06 | chỉ hiện đường dẫn API | `record_count = 0` hardcode | 1787 dòng lineage chưa đọc | — | NI | `dashboard_service.py:143` |
| AUD-RPT-22 | Trang cảnh báo + ack / dismiss | EP-DSH-01..03 | chỉ ack | có | alerts | test API | P | |
| AUD-RPT-23 | Danh mục báo cáo + CSV / XLSX | R-DEC-136 | /knowledge/reports | report_service | — | chỉ unit encoder | I | |
| AUD-RPT-24 | Báo cáo AI theo lịch, sửa trước khi gửi | FR-RPT-01/02 | ✗ | tool không bind | — | — | NI | |
| AUD-RPT-25 | PDF / Word | FR-RPT-02 | — | — | — | — | OOS | |
| AUD-RPT-26 | Nghiệm thu G1–G4 | R-DEC-145 | /admin/acceptance | acceptance_service | — | unit | B | G1 dùng ngày đồng hồ thật (`acceptance_service.py:71`) |
| AUD-RPT-27 | Cache NFR-07 | CLAUDE §5.2 | — | `_cache()` | — | nfr-real | V | |
| AUD-MET-01/02 | Catalog 34 chỉ số; tính từ dữ liệu thật | 03 §4.2 | — | 8 provider | 34 giá trị COMPUTED | contract catalog, test_metric_store | V ×2 | không có số hardcode |
| AUD-MET-03 | Tăng trưởng doanh thu cùng kỳ | 03 §4 | — | chỉ % so kế hoạch | — | — | NI | |
| AUD-MET-04..06, 11 | Recompute (event + job 01:00); độ tươi SLA; vòng đời cảnh báo; field `group` | 03, R-DEC-82/86 | — | metric_store | alerts | test có | V ×4 | |
| AUD-MET-07 | Cảnh báo → thông báo (CEO + DIR + MGR) | R-DEC-88 | bell | thiếu MGR | — | unit | P | |
| AUD-MET-08 | Ngưỡng cấu hình được | NFR-19 | ✗ | chỉ qua dòng `THR_*` trong DB | — | test override | P | |
| AUD-MET-09 | **Nhóm DQ hiện cho CEO / ADM** | 03 §4.1 | ✗ | `metric_visible` loại `pillar=None`; 403 | DQ-01 = 88,7 đã tính | test khẳng định DQ vắng | B | `dashboard_service.py:64-66` |
| AUD-MET-10 | Ẩn chỉ số / cảnh báo module đóng băng | R-DEC-16/82 | hiện với CEO | không lọc FROZEN_CODES | 7/13 cảnh báo mở là RSK/PRD | — | SM | |
| AUD-MET-12 | Mô tả field-level bảng chỉ số | 05 §6bis | — | — | — | — | DG | |
| AUD-MET-13 | Một ngày nghiệp vụ | R-DEC-192 PROPOSED | FE dùng kỳ cứng `"2026-09"` | core/clock | — | TC-V4-01 | NC | |
| AUD-PLT-01..03 | Nhật ký audit; outbox + dedupe; DLQ + replay | EP-ADM-12, DEC-126 | AuditLogView (ADM) | có | có | test có | V ×3 | replay không audit / Idempotency-Key |
| AUD-PLT-04 | Quản trị cài đặt hệ thống | FR-ADM-01 | ✗ | chỉ kill switch, onboarding | — | — | P | |
| AUD-PLT-05 | Quản trị quy tắc thông báo | FR-ADM-01 | — | — | — | — | NC | |
| AUD-PRD-01/02, AUD-RSK-01..03 | CRUD Product (sản phẩm, tính năng, lộ trình, phát hành); CRUD rủi ro + biện pháp; trang bản ghi | D-21, R-DEC-201 | /business/{product,risk}/records | catalog, planning, risk router | có | integration product/risk, D-21, E2E m7 | V ×5 | |
| AUD-PRD-03/04, AUD-RSK-04..06 | Chỉ số sản phẩm; dashboard; kịch bản; rủi ro tự sinh | R-DEC-16 | — | có | có | test | OOS ×5 | |
| AUD-FRZ-01 | Tôn trọng đóng băng | R-DEC-16 | không có sidebar | tool `p1_frozen` | — | test registry | V | trừ chỉ số / cảnh báo lọt ra (AUD-MET-10) |

### 8.8. Cross-cutting (API, DB, kiến trúc, ID)

Xem §6 (kiến trúc) và §12 (API & DB).

| Nhóm | Mục | Kết quả |
|---|---|---|
| API | AUD-API-01..16 | 8 V, 2 I, 2 P, 1 NI (rate limit), 2 DG (ops routes; contract field-level của FIN/SAL/PRD/RSK), 1 NC (route chỉ cần token) |
| DB | AUD-DB-01..11 | 3 V, 2 I, 3 P (tenant_id, thực thể P0, audit TRUNCATE), 1 DG (39 bảng không có trong 05), 2 NC (schema `public`, cột `source`) |
| Kiến trúc / NFR | AUD-ARC-01..20 | 5 V, 6 I, 2 P, 4 NI (verify JWT nhiều `kid`, SSO/MFA, egress AI, TLS/mạng), 2 SM (lưu trữ, hiệu năng AI), 1 NOT VERIFIED (coverage) |
| ID registry | AUD-ID-01..05 | 2 V, 1 SM (SCR-28), 1 DG (18 tên ENT-*), 1 NC (EVT registry) |

---

## 9. CRUD Capability Matrix

**Ký hiệu:** ✓ có; ✗ không có; "arch" = lưu trữ (xóa mềm `deleted_at`); "status" = kết thúc bằng trạng thái (không có DELETE theo thiết kế); "API" = chỉ có ở API, không có UI.

**Quyền:**
- W = vai có quyền ghi.
- Phạm vi:
  - MGR = phòng mình
  - REV = chỉ trong phiên review (thực tế: 403)
  - EMP = của mình

| Module | Entity | C | R | U | D | Search / Filter | Validation | Permission (ghi) |
|---|---|---|---|---|---|---|---|---|
| Org | Organization | ✓ | ✓ | ✓ | arch (API) | `q`, archived | mã trùng 409, version | hr:admin (CEO, ADM, DIR-O) |
| Org | Department | ✓ | ✓ `as_of` | ✓ (**UI lỗi**) | arch (422 nếu còn NV) | `as_of`, parent | vòng lặp, mã trùng | hr:admin |
| Org | Team | ✓ | ✓ | API | arch | department | còn người giữ → 422 | hr:admin |
| Org | Position | ✓ | ✓ | ✓ | arch | department, `q` | đang giữ → 422 | hr:admin |
| Org | Employee assignment | ✓ | ✓ | API | đóng `valid_to` | employee, `as_of` | chồng lấn → 422 | hr:admin |
| HR | Employee | ✓ | ✓ | ✓ | arch | department, status, `q` | mã / email trùng, quy tắc nghỉ việc | hr:write (CEO, DIR-O); MGR đọc phòng |
| HR | Salary history | API | API | — (chỉ thêm) | — | — | > 0, trùng ngày | hr:write + quyền mức 4 |
| HR | Hiring plan | ✓ | ✓ | ✓ (+ gửi, duyệt) | arch (draft / rejected / cancelled) | department, status, delayed | khoảng lương, trạng thái | hr:write; duyệt hr:approve + engine |
| HR | Leave / Skill | ✗ | ✗ | ✗ | ✗ | — | — | — |
| Admin | User | ✓ (ADM) | ✓ | ✓ (ADM) | khóa / mở (không xóa cứng) | role, active, department, `q` | pw ≥ 12, ADM không cấp CEO | platform:admin (CEO, ADM) |
| Finance | Revenue / Expense / Budget | ✓ | ✓ | ✓ | arch | period, category, department | > 0, enum, version | finance:write (CEO, DIR-F; MGR chi phí / ngân sách phòng) |
| Finance | Cash position | ✓ | ✓ | ✓ | **✗ (405)** | from / to | kỳ duy nhất | finance:write |
| Finance | Forecast | API | API | API | ✗ | scenario, horizon | horizon, kỳ | finance:write |
| Finance | Invoice + pay | ✓ | ✓ (MGR: của mình) | ✓ + pay | arch (đã trả → 409) | status, client, overdue, direction | dòng, VAT, MST, trạng thái | finance:write |
| Finance | Cash-flow forecast | API recompute | API | — | — | as_of | — | finance:write |
| Sales | Client | ✓ | ✓ | ✓ | arch (409 nếu còn con) | `q`, industry | tên / MST trùng | sales:write (MGR: chỉ tạo) |
| Sales | Deal + stage | ✓ | ✓ | ✓ + stage | arch (**không kiểm con**) | stage, owner, client, ngày | value > 0, chỉ tiến | sales:write; xóa: DIR-C, CEO |
| Sales | Contract / Target | ✓ | ✓ | ✓ | arch | client, status / period | ngày, mã duy nhất | sales:write (target: không MGR) |
| Sales | Lead / Contact / Activity + convert | ✓ | ✓ | ✓ | arch | `q`, status, owner / client | email hoặc phone, trùng → 409 xác nhận | sales:write (MGR theo phòng; contact chỉ tạo) |
| Execution | Strategy / Strategic objective | ✓ | ✓ | API | API | status, pillar | mã trùng, ngày | execution:write (Strategy: CEO; SO: CEO, DIR khối) |
| Execution | Initiative + milestone | API | ✓ (cây) | API | API | objective, status | SO bắt buộc | execution:write |
| Execution | KPI / target / measurement | ✓ | ✓ | ✓ / version / — | arch / — | owner, metric, band | trùng, khóa kỳ | execution:write (EMP: đo KPI của mình) |
| Execution | Objective / Key result / Check-in | ✓ | ✓ | ✓ / — | arch / — | period, owner, at_risk | 2–5 KR | execution:write |
| Execution | Task / dependency | ✓ | ✓ | ✓ | ✓ (EMP xóa task của mình qua API) | status, due, assignee, project | state machine, vòng phụ thuộc | execution:write |
| Execution | Project / milestone | ✓ | ✓ | ✓ / UI một phần | ✓ / API | status, late | mã trùng; còn task → 409 | execution:write |
| Execution | Meeting / Decision | ✓ | ✓ | ✓ | arch / status | from / to, status | còn quyết định → 409 | execution:write |
| Execution | ActionItem | chỉ qua IDP | lineage | ACT không có caller | undo | **không có endpoint** | — | — |
| Calendar | Event | ✓ | ✓ (của mình) | API | ✓ | from / to | ends ≥ starts | chỉ owner, mọi role |
| Workflow | Approval request | service | ✓ | decide | — | status, rule | lý do khi từ chối | platform:approve theo bước |
| IDP | Source document | ✓ (C1–C5) | ✓ | chuyển trạng thái | undo (không xóa) | group, channel, type, `q` | MIME, 50 MB, SHA | idp:write / approve |
| IDP | Schema / Rule / DocType | ✓ | ✓ | ✓ | retire / inactive | — | ngưỡng DEC-133 | idp:admin (chỉ ADM) |
| IDP | Incident | ✓ | ✓ | — | — | period | — | idp:approve |
| Product | Product / Feature / Roadmap / Release | ✓ | ✓ | ✓ | arch / release: ✗ | status, product | mã / phiên bản trùng | product:write (CEO, DIR-U) |
| Risk | Risk / Mitigation | ✓ | ✓ | ✓ (+ đánh giá, chấp nhận) | status | status, category, owner | 1–5, owner khi score ≥ 5 | risk:write; chấp nhận risk:approve (CEO) |
| AI | Autonomy policy | ✓ | ✓ | ✓ | arch | tool, agent, role | quy tắc mức | ai:admin (CEO, ADM) |
| AI | Conversation | ngầm | ✓ (của mình) | — | **✗** | — | — | ai:query |
| Platform | Alert | hệ thống | ✓ | ack / dismiss (UI chỉ ack) | — | status, severity | — | dashboard:write |
| Platform | Executive tile preference | API | API | API | — | — | ≤ 4, trong phạm vi | dashboard:write (**không có UI**) |

---

## 10. CEO Permission Audit

**Nguồn:**
- **Yêu cầu:** R-DEC-198 / D-21 (APPROVED bởi PO 2026-11-09): CEO thêm, xem, sửa, xóa mọi dữ liệu nghiệp vụ, không bị giới hạn theo người tạo hay phòng ban; ràng buộc toàn vẹn vẫn giữ.
- **Quyền trong code:** `api/modules/auth/permission_matrix.py:39-72`. CEO có 32 quyền; `ROLE_SCOPES["CEO"]` không có giới hạn dữ liệu (chỉ `ai:admin ◑k`, `platform:admin ◑u`, mà code không diễn giải).
- **Phạm vi trong code:** CEO không bị lọc theo phòng hay chủ ở:
  - `finance/services/scope.py` (chỉ MGR, REV bị giới hạn)
  - `sales/services/scope.py:24`
  - `hr/services/scope.py:38`
  - `execution/services/scope.py:33` và `goal_scope.py:55`
  - `risk/services/scope.py:36`
  - `product/services/scope.py:19-28`
  - `idp/services/scope.py:23,69,77`
  - `approval_service.py:104`

| Câu hỏi audit | Kết quả | Bằng chứng |
|---|---|---|
| Thêm dữ liệu ở mọi module nghiệp vụ? | **API: có** (trừ cấu hình IDP `idp:admin`). **UI: chưa đủ** — thiếu tạo người dùng, Initiative, dự báo P&L, lịch sử lương, ngưỡng cảnh báo | `test_ceo_full_crud_d21.py`; `admin/users/page.tsx:9`; `StrategyEditors.tsx` |
| Xem dữ liệu toàn công ty? | **Có**, trừ hai ngoại lệ: nhóm chỉ số DQ (403 ngay cả với CEO); lịch của người khác (riêng tư theo R-DEC-123) | `dashboard_service.py:64-66`; `calendar_service.py:61` |
| Sửa dữ liệu do người khác tạo? | **API: có.** UI: thiếu sửa Chiến lược / SO, Initiative, đội nhóm, gán nhân sự; sửa phòng ban lỗi | §8.1, §8.4 |
| Xóa dữ liệu do người khác tạo? | **API: có** cho phần lớn entity. Không có DELETE: số dư tiền, dự báo, quyết định, rủi ro, biện pháp, phát hành (theo thiết kế hoặc R-DEC-201 chưa duyệt). **Xóa deal có hợp đồng làm hợp đồng mồ côi** | `router.py:205-242`; `sales_service.py:371` |
| Bị giới hạn theo phòng ban / owner? | **Không**, trừ ba ngoại lệ hợp lý: AI action (chỉ xác nhận thẻ của mình), hội thoại AI (của mình), lịch (của mình); và CEO không duyệt được `task_reassign` (R-DEC-45) | `action_service._require_owner`; `approval_service.py:53` |
| Frontend có đủ thao tác? | **Chưa đủ** | Bảng dưới |
| Backend có thực thi quyền? | **Có** | test D-21; contract |
| Thay đổi ghi xuống DB? | **Có** (audit + outbox trong cùng transaction) | test D-21 kiểm bản ghi và audit |
| Dashboard / báo cáo cập nhật theo dữ liệu mới? | **Một phần.** `/finance/dashboard` cập nhật ngay vì tính lại lúc request (lệch spec), nhưng Metric Store / ô Home chỉ cập nhật ở job 01:00 với dữ liệu ghi tay (không phát event) | `test_ceo_full_crud_d21.py:180` phải gọi recompute thủ công |

**Khoảng trống UI của CEO** (API có, giao diện không):

| Module | Thiếu trên UI |
|---|---|
| Người dùng | Tạo, sửa, khóa: trang chỉ cho ADM (**trái D-21**; 06 SCR-53 cũng trái D-21) |
| Tổ chức | Sửa phòng ban (lỗi `version`), sửa đội nhóm, sửa gán nhân sự, lưu trữ tổ chức |
| Nhân sự | Lịch sử lương, trường mức 4, vòng đời kế hoạch tuyển dụng sau duyệt |
| Chiến lược | Sửa / xóa Chiến lược và SO; toàn bộ Initiative và mốc |
| Dự án | Sửa / xóa mốc dự án |
| Tài chính | Dự báo P&L, dòng tiền 13 tuần, hủy hóa đơn |
| Lịch | Sửa sự kiện |
| IDP | Báo sự cố G4, danh sách sự cố, giao lại / gộp review |
| Dashboard | Tùy chỉnh ô, dismiss cảnh báo, ngưỡng, nhật ký audit (CEO có quyền API) |

**Đính chính báo cáo trước:**
- `V4-DEMO-READINESS-REPORT.md` §3 ghi CEO "Người dùng: Tài khoản, vai trò ✓ ✓ ✓" và "Chiến lược … ✓ ✓ ✓ ✓". Hai dòng này chỉ đúng ở API, **không đúng ở giao diện**.
- E2E `m7-records` "CEO (D-21)" chỉ kiểm doanh thu, sản phẩm, rủi ro, cuộc họp và sự hiện diện nút tạo ở HR / Sales.

**Đánh giá: D-21 = PARTIALLY IMPLEMENTED** (API đạt và đã kiểm chứng; UI và toàn vẹn khi xóa deal chưa đạt).

---

## 11. Role & Permission Comparison

**Ma trận quyền thực tế** (`permission_matrix.py`, khớp `auth.roles` trong DB):
- r = read, w = write, q = query, ap = approve, ad = admin.
- Phạm vi trong ngoặc: d = phòng, o = của mình, p = khối, r = phiên review, s = cấu trúc, l = liên kết, agg = tổng hợp.

| Role | finance | sales | hr | product | risk | execution | idp | ai | dashboard | platform |
|---|---|---|---|---|---|---|---|---|---|---|
| CEO | r w q | r w q | r w q ap ad | r w q | r w q ap | r w q | r w ap | q w ad | r w | r ap ad |
| DIR | r w q(agg) | r w q(agg) | r w q(agg) ap ad | r w q(agg) | r(l) w q | r w q (d) | r w ap (p) | q w | r w (p) | ap (p) |
| MGR | r w q (d) | r w q (d) | r q (d) | r w q (d) | r w (d) | r w q (d) | r w ap (d) | q w | — | ap (d) |
| EMP | — | — | r (o) | — | — | r w (o) | r w (o) | q w | — | — |
| REV | r (r) | r (r) | r (r) | r (r) | r (r) | — | r w (r) ap | q w (r) | — | — |
| ADM | — | — | r (s) ad | — | — | — | r w (s) ad | q ad | ad | r ad |
| AI | — | — | — | — | — | — | — | q w | — | — |

**So với tài liệu:** 02 hiện hành **không có** ma trận role × quyền. Code, 05 §2.2, 10 và R-DEC-30/147 đều trích "02 §5.2 / §5.3 / §6.2", nay không tồn tại. Nguồn duy nhất còn lại: danh sách quyền CEO và ghi chú MGR (D-20) trong 02 §2, rải rác trong DEC / R-DEC.

**Sai lệch chính:**

| # | Role | Sai lệch | Mức | Bằng chứng |
|---|---|---|---|---|
| 1 | MGR | `finance:query ◑d` không được áp ở `/finance/dashboard`, what-if, `TOOL-get_finance_dashboard`: MGR thấy doanh thu, lợi nhuận, tiền mặt, runway toàn công ty | HIGH | `finance/routes/router.py:424-446` |
| 2 | MGR | Ghi doanh thu / số dư tiền / hóa đơn công ty qua IDP Action Registry (chỉ kiểm `finance:write`) | MEDIUM | `idp/services/actions/finance.py:120,192,288` |
| 3 | MGR | Quyền "chết": `product:write`, một phần `finance:write`, `sales:write` có trong JWT nhưng service luôn từ chối | LOW | `product/services/scope.py:26` |
| 4 | MGR | Không nhận thông báo cảnh báo chỉ số (R-DEC-88) | LOW | `metric_store.py:262` |
| 5 | DIR | `scope_pillars = []` (= mọi khối, kể cả lương) được ADM cấp qua API; R-DEC-12a dành "rỗng" cho CEO | MEDIUM | `user_admin_service.py:140-147` |
| 6 | DIR | Task / dự án theo phòng (d), mục tiêu theo khối: không nhất quán | LOW | `execution/services/scope.py` vs `goal_scope.py` |
| 7 | DIR | Chỉ số STR (SEI) chỉ DIR khối S thấy; demo không có DIR-S | LOW | `dashboard_service.py:33,58` |
| 8 | REV | 02 §5: xem HR / mức 4 trong phiên review; code luôn 403 | MEDIUM | `hr/services/scope.py` NO_RECORD_ROLES |
| 9 | EMP | Đọc tài liệu IDP cùng phòng và giá trị trích xuất không che (10 ghi "chỉ tài liệu mình gửi") | **CRITICAL** (gộp vào C-01) | `idp/services/scope.py:27-30` |
| 10 | EMP | Xóa task của mình qua API (UI ẩn); tự động thực thi L3 khi chat tạo task / ghi quyết định | LOW / NC | `task_service.py:367`; `autonomy.py` |
| 11 | ADM | 10 §7.2.4 ghi ADM không có `idp:write`; code có (R-DEC-76 đã resolved) | LOW (tài liệu) | |
| 12 | ADM | Có `dashboard:admin` nhưng không endpoint nào dùng; không có `dashboard:read` nên lời hứa "DQ cho CEO / ADM" không đạt | LOW | |

**Frontend vs backend:** route rules trong `web/lib/permissions.ts` khớp backend (test `role-routes.test.ts`). Ngoại lệ:
- Trang người dùng chặn CEO dù API cho phép.
- `/admin/audit` chỉ cho ADM dù CEO có `platform:read`.
- `/settings/integrations` không có rule cho REV / ADM.
- Trang records hiện nút ghi cho MGR ở tab mà API trả 403.

---

## 12. API & Database Conformance

**API:**

| Kiểm tra | Kết quả |
|---|---|
| EP trong 10 §7 ↔ route trong code | **252/252 EP có route; 345/345 thao tác có EP** (GET 164, POST 95, PATCH 49, DELETE 35, PUT 2) |
| Permission route ∈ dòng EP | 0 lệch |
| Envelope + `response_model` | Đạt (5 ngoại lệ có tài liệu: SSE, 3 file nhị phân, 1 redirect OAuth) |
| Chỉ 3 endpoint public; không có `/auth/register` | Đạt |
| Idempotency-Key | 90/95 POST + 2/2 PUT. Thiếu ở EP-DC-10 (release review) và EP-PLT-02 (DLQ replay). Login / refresh / logout không cần |
| Phân trang `limit / offset` | 62/86 danh sách; 24 danh sách không phân trang (10 cũng không yêu cầu) |
| Tiền BIGINT + currency; `_pct` 0–100 | Đạt (ngoại lệ có lý do: `monthly_budget_usd` NUMERIC, `base_salary` BYTEA mã hóa) |
| Cache header | Dashboard đúng; **không có `no-store` mặc định**; EP-AI-25 thiếu `no-store` |
| X-Request-Id | Đạt |
| Route vận hành `/health*`, `/metrics` | Không có trong 10 (DG); `/metrics` không xác thực |
| Contract field-level FIN / SAL / PRD / RSK | 10 dùng dòng `*` gộp phương thức; shape chỉ có trong v2.1 (archive) → DG |
| Rate limit | Không có |
| Contract test (44) | Kiểm path + permission + catalog (tool, metric, ACT); **không** kiểm idempotency, phân trang, cache, tiền, hay tool có chạy được |

**Database:**

| Kiểm tra | Kết quả |
|---|---|
| Live DB = head = ORM | Đạt: `0028_crm_leads_contacts_activity`, 103 bảng, cột giống hệt (`test_db_tables_match_metadata`) |
| FK có index; không FK chéo schema | Đạt (131 FK) |
| `id`, timestamp, `deleted_at` | Đạt theo nhóm bảng (`test_c19_columns_by_group`) |
| `tenant_id` | **22 bảng thiếu** (danh sách: `ai.conversations / feedback / messages`, `auth.refresh_tokens / roles / users`, `hr.salary_history`, `idp.document_pages / document_types / extraction_jobs / extraction_reviews / extraction_schemas / review_assignments / validation_rules`, `platform.approval_rules / audit_logs / metrics / processed_events / system_settings`, `product.product_metrics`, `risk.risk_assessments`, `sales.deal_stage_history`) |
| Migration reversible | 28/28 có `downgrade()`; **không có test round-trip** |
| Tài liệu 05 | **39/103 bảng không được nhắc** (toàn bộ finance, product, risk; sales contracts / targets / stage_history; ai insights / conversations; platform metrics / alerts / reports; hr hiring_plans / leaves / skills …) |
| Thực thể BRD §13.2 P0 | Thiếu bảng: PerformanceCycle (P0), Payment (chỉ cột `paid_amount`), Workload / StrategicPillar / Knowledge (tính toán hoặc enum) |
| Schema `public` | 12 bảng v1 **có dữ liệu**, gồm `public.users` (5 dòng có `password_hash`); `public.alembic_version` = `37728110ccb4` (không có trong repo) |
| Audit append-only | Trigger chặn UPDATE / DELETE; ứng dụng kết nối bằng superuser `aureon` (có TRUNCATE); role `app_audit_writer` không được dùng |
| Mã hóa mức 4 | `hr.salary_history.base_salary` BYTEA (mã hóa); `idp.extracted_fields.value` / `import_rows` **plaintext JSONB** (trái 05 §2.7) |
| Cột `source` | Tên trần trên mọi bảng nghiệp vụ; CLAUDE §6.1 (DEC-154) yêu cầu hậu tố; 05 OQ-05-01 còn mở → NC |
| Bảng chết | `hr.leaves`, `hr.employee_skills`, `ai.feedback` (0 dòng, không có API); `execution._m13_assignee_backfill` (artifact migration 0014) |

---

## 13. AI & External Integration Status

| Năng lực | Trạng thái | Bằng chứng |
|---|---|---|
| Provider runtime | Chỉ Ollama local trên stack demo (cấu hình `.env`); 3 lượt `ollama/qwen2.5:3b-instruct` ngày 2026-11-09; 1 lượt `omniroute/extract` ngày 2026-11-04 (trước D-11) | `ai.model_call_logs` (SELECT) |
| Mặc định code và `.env.example` | `MODEL_PROVIDER_PRIMARY=omniroute`, fallback `openrouter,deepseek` → copy `.env.example` + có key = dữ liệu INTERNAL lên cloud | `config.py:68`, `.env.example:67-68` |
| Chính sách phân loại | 02 §5, 07 §4, CLAUDE §2.2 (đã duyệt): Internal → cloud. D-11 / R-DEC-188 (PROPOSED, blocking): không provider nào nhận INTERNAL. Code tuân theo bản đã duyệt, demo tuân theo D-11 bằng cấu hình | NC |
| Chat AI thật | Hoạt động (SSE, grounding, trích dẫn, intent routing); 13–67 s / lượt trên CPU; 2–3 s khi prompt cache ấm | E2E ceo-7steps-real; R-DEC-200 |
| Trích xuất IDP | Thật với model local; hóa đơn ~45–56 s | 06-AI report (chưa đo lại) |
| Embedding / RAG | Code có; demo DB 0 vector → chỉ có tìm kiếm từ khóa thật sự chạy | `idp.document_pages` |
| Insight / briefing | Có code; demo DB 0 insight; briefing chỉ hiện dòng tóm tắt | `ai.insights` = 0 |
| Tool | 54 đăng ký; **12 không chạy được** (6 READ thiếu binding: what-if runway, cash flow, forecast, product metrics, list risks, risk scenario; 6 WRITE thiếu ACT: generate_report, request_approval, send_notification, submit_document, create_mitigation, upsert_risk) | `tool_executor.py` |
| Đánh giá chất lượng | 0 lượt; engine chấm điểm câu trả lời tĩnh | AUD-AI-29 |
| STT giọng nói | Hoãn (R-DEC-166), chỉ có fixture | |
| OCR | Provider theo `.env` (PaddleOCR trong image); chất lượng OCR tiếng Việt chưa đo | NOT VERIFIED |
| Google / Outlook Calendar | Code đồng bộ 2 chiều có unit test; **callback OAuth hỏng**; chưa chạy live | AUD-CAL-03 |
| Email | Mailpit (dev) nhận thông báo; chưa có SMTP thật | E2E Mailpit |
| Phần mềm kế toán | Không có tích hợp (chỉ upload báo cáo qua IDP) | NC |
| MinIO / S3 | Không dùng | SM |

---

## 14. UI/UX Implementation Status

| Hạng mục | Trạng thái |
|---|---|
| Màn hình theo 06 §3.4 / §3.5 | Có đủ route chính: SCR-40..66, `/business/*/records`, CRM, strategies. Thiếu: chi tiết Lead, chi tiết nhân viên (mức 4), dòng tiền 13 tuần, dự báo, Initiative, panel AI ngữ cảnh |
| Form + validation | Bộ CRUD chung (`web/features/records/*`) dùng rhf + zod, lỗi theo trường, cảnh báo trùng; form riêng ở goals / work / admin. Lỗi: sửa phòng ban thiếu `version` |
| CRUD trên UI | §9, §10 |
| Gọi API thật | Có (BFF). Mock chỉ dùng khi `API_MODE=mock` (bị chặn ở production); không thấy số hardcode trên dashboard, trừ kỳ mặc định `"2026-09"` và `record_count = 0` |
| Loading / error / empty / success | Có ở records, goals, work, admin (skeleton, LoadError, empty text, toast). Home dùng một query cho cả trang nên một lỗi làm trống cả trang (lệch FR-DSH-07) |
| Dashboard / biểu đồ | Ô chỉ số, sparkline, trụ cột, pipeline Kanban, funnel dạng bảng (không phải biểu đồ), ranking hiện UUID chủ sở hữu |
| Điều hướng | Sidebar theo role, mặc định từ chối, Review cho CEO; Product / Risk chỉ vào từ `/business` (R-DEC-16) |
| Chức năng giả / hiển thị sai | Nút "Duyệt" action item (chỉ state cục bộ); hộp thư IDP xếp `AUTO_APPROVED` vào "committed"; "0 bản ghi" ở panel chỉ số |
| i18n | VI / EN đầy đủ cho records; briefing hiện `summary_line` tiếng Việt cả khi chọn EN |
| Responsive / a11y | E2E responsive (real) đạt; a11y-axe chỉ chạy project mock — NOT VERIFIED trên real |
| Design system | Deep Navy (D-13); token `ai` tách `primary` |

---

## 15. Testing & Verification Status

| Bộ | Kết quả | Nguồn |
|---|---|---|
| Backend pytest | 1709 passed, 0 failed (DB tạm) | `var/v4-audit/restore/pytest-full2.log` |
| Contract | 44 passed | log |
| Vitest | 590 passed | log commit `cdc794a` |
| E2E `real` (136) | 135 passed lượt đầy đủ cuối; 1 sửa xong pass 2 lượt riêng | `var/v4-audit/dev/final2/e2e-full3.log` |
| E2E chỉ chạy mock | `a11y-axe`, `a11y-m2`, `admin-screens`, `assistant-m24`, `ai-control` (lọc `@mock-only`) | config Playwright |
| Code coverage | **NOT VERIFIED** cho v4 (lần cuối 97% ở M1.1, 2026-10-23) | 14 dòng 86 |
| Hiệu năng | Đo bằng replay gateway (TTFT 0,074 s), không đại diện cấu hình hiện tại | TC-M25-02 |
| Migration round-trip | Không có test | |

**Test có nhưng không kiểm đúng nghiệp vụ (tuyên bố "Passed" sai hoặc yếu):**

| Test / TC | Vấn đề |
|---|---|
| TC-M23-11 / `meetings.spec.ts:62-64` | Chỉ kiểm nhãn "đã tạo" trên UI; không có task nào được tạo |
| TC-M21-12 | Ghi "4 ô + dialog tùy chỉnh" Passed; dialog không tồn tại |
| TC-M22-07 | "Số click → lineage" trên Finance Lite: không có |
| `e2e/home.spec.ts:15` | Assertion SEI bọc `.catch(() => {})` nên không bao giờ fail |
| `ceo-7steps-real` bước 5–6 | Chỉ kiểm `GET /ai/actions` = 200, không kiểm hành động L3 thực thi |
| `test_every_advertised_tool_can_run` | Bỏ qua 12 tool không chạy được (vì không được quảng bá) |
| `test_ceo_sales_crud` | Xóa hợp đồng trước deal, nên không phát hiện mồ côi |
| `test_ceo_full_crud_d21` (finance) | Gọi `MetricStore.recompute` thủ công, che việc store không tự cập nhật |
| `admin-screens.spec.ts:85-89` | Khẳng định CEO chỉ đọc người dùng, trái D-21 |
| `test_execute_recommendation_l3.py:104` | Khẳng định sự kiện lịch thuộc mã nhân viên (đúng là lỗi) |
| `test_metric_store.py:158` | Khẳng định DQ vắng mặt (đúng là lỗi) |

**Tính năng chưa có test:** HEIC upload, STP commit, đổi loại tài liệu, truncate ≤ 8 tool, kiểm tổng trọng số KPI, job nhắc review quyết định, EP-RPT-06/07/08 qua HTTP, E2E lead / contact / activity / convert, E2E CEO chuyển giai đoạn hoặc xóa deal trên UI, xóa task trên UI.

---

## 16. Documentation Gaps

| ID | Nội dung thiếu hoặc lỗi thời | Vị trí | Mức |
|---|---|---|---|
| DG-01 | Ma trận role × quyền × phạm vi không còn trong 02; code, 05, 10 và R-DEC-30/147 đều trích "02 §5.2/§5.3/§6.2" | 02; `permission_matrix.py:1-9` | MEDIUM |
| DG-02 | 39/103 bảng không được mô tả trong 05 (toàn bộ finance, product, risk, một phần sales/ai/platform/hr) | 05 | MEDIUM |
| DG-03 | Contract field-level của FIN/SAL/PRD/RSK chỉ còn ở v2.1 (archive, cấm đọc); 10 chỉ có dòng `*` | 10 §7.2.7, §7.3 | MEDIUM |
| DG-04 | `CLAUDE.md` lỗi thời:<br>• §1.6: 777/18/30 test (thực tế 1709/590/136), 9 service (thực tế 10)<br>• `secrets/` thay vì `keys/`; tên module `ai_core` thay vì `ai`<br>• qwen 7b (thực tế 3b); MinIO<br>• Registry không tồn tại: `00 §4.5`, `§4.13.2`; con số "TOOL 43", "METRIC 32", "EVT 28" (thực tế 54 tool, 34 metric, 40 event)<br>• Dùng ROLE-01/04/05 kiểu v2.1<br>Agent không được tự sửa file này. | `CLAUDE.md` | MEDIUM |
| DG-05 | Version header không phản ánh nội dung: 05 khai 1.2.0 nhưng liệt kê thay đổi 1.3–1.6; 10 vẫn ghi 1.1.0, cập nhật lần cuối 2026-11-02; phần lớn thay đổi v4 mới ở dạng "đề xuất" | 05, 10, 12 | MEDIUM |
| DG-06 | Route vận hành `/health*`, `/metrics`, ngưỡng khóa đăng nhập (5 lần / 15 phút), quy tắc xem dashboard HR / quỹ lương, circuit breaker của AI gateway: có trong code, không có trong 10 / 02 / 07 | | LOW |
| DG-07 | 18 tên `ENT-*` trong code không có trong registry; `ENT-SalesActivity` mới ở trạng thái đề xuất; frontend vẫn dùng SCR-28 (v2.1) | skeleton §11; `web/app/manifest.ts:4` | LOW |
| DG-08 | Thông tin sai trong 16-OPERATIONS ("migrate tới 0027"), DEMO-SCRIPT (readiness có MinIO), 00 §5.1 (v4 "chưa commit"), các tài liệu `handover/*` (CEO không có `idp:approve`), dòng ADM trong 10 §7.2.4 | | LOW |
| DG-09 | 14 có một số TC ghi "Passed" không đúng thực tế (§15): TC-M23-11, TC-M21-12, TC-M22-07, TC-M25-02 | 14 | MEDIUM |
| DG-10 | 10 §7.2.10 trích "EP-DEC-01/02" (không tồn tại); `TOOL-request_approval` trỏ tới EP-123.C (không tồn tại) | 10 | LOW |

## 17. Codebase Gaps

Những yêu cầu đã có trong tài liệu hiện hành nhưng code chưa có (NOT IMPLEMENTED), theo module:

| Module | Thiếu |
|---|---|
| Tổ chức | Kiêm nhiệm / báo cáo ma trận (FR-ORG-02) |
| Nhân sự | Nghỉ phép (FR-HR-01 P0), kỹ năng |
| Quản trị | Xem như người dùng (FR-ADM-08) |
| Xác thực | Rate limit; SSO / MFA / quản lý phiên (FR-ADM-04) |
| Mục tiêu | Kiểm chất lượng OKR bằng AI (FR-OKR-05); phát hiện O/KR không có hành động (FR-OKR-06); khung KPI/OKR theo phòng (US-PERF-001) |
| Công việc | Task định kỳ / mẫu (FR-TASK-03); AI gợi ý điều chuyển (FR-WL-02); ước lượng có nhãn (FR-WL-03) |
| Họp | Quyết định rút từ biên bản (FR-MTG-05); briefing trước họp (FR-MTG-07) |
| IDP | Gợi ý / cảnh báo trùng khi nhập (FR-DC-02); nháp + lưới (FR-DC-04); tách / gộp file (FR-DC-10); gộp vào bản ghi có sẵn; học từ sửa lỗi + KPI IDP (04 §8); SOP → kho tri thức (UC-07, doc type #5) |
| AI | Rate limit AI; prompt versioning (AIC-05); agent Lite tài chính / kinh doanh; phản hồi 👍/👎 (FR-AIQ-04); panel AI ngữ cảnh; kiểm bằng chứng + 2 bên khi nâng autonomy |
| Dashboard | Dialog tùy chỉnh ô; drill-down chỉ số → bản ghi → tài liệu (FR-RPT-04, P06); báo cáo AI / theo lịch (FR-RPT-01/02); tăng trưởng doanh thu cùng kỳ |
| Kiến trúc | Verify JWT nhiều `kid` / xoay khóa; chốt egress AI trong code; TLS / tách mạng (Phase 8) |

**Bảng có nhưng không có nghiệp vụ:** `hr.leaves`, `hr.employee_skills`, `ai.feedback`, `execution.meeting_transcripts` (không có ghi thật), `ai.ai_evaluations` (0 dòng).

**API có nhưng frontend không dùng:**
- EP-STR-12..21 (Initiative)
- EP-HR-06 (dashboard HR), EP-HR-07 (lương)
- EP-FIN-06 / 10 (dự báo, dòng tiền)
- EP-ORG-05 / 14 / 23
- EP-DC-11 / 12 (giao lại, gộp)
- EP-RPT-04 / 05 (tùy chọn ô)
- EP-DSH-03 (dismiss)
- EP-ADM-12 cho CEO
- `useUpdateCalendarEvent`

## 18. Specification Mismatches

| ID | Tài liệu nói | Code làm | Nguồn quy định hiện hành |
|---|---|---|---|
| SM-01 | 03 §4.3: dashboard đọc Metric Store, không tính lúc request | `/finance/dashboard` tính lại lúc request; `freshness` luôn "fresh" | 03 + CLAUDE §5.4 |
| SM-02 | 10: số dư tiền "CRUD"; D-21: CEO xóa số dư tiền, dự báo | Không có DELETE | 10 / D-21 (R-DEC-201 về "kết thúc bằng trạng thái" chưa duyệt) |
| SM-03 | 02 §2 / D-21: CEO quản lý người dùng | UI chỉ cho ADM; 06 SCR-53 ghi "CEO xem" | D-21 (APPROVED) — 06 cần sửa |
| SM-04 | 02 §5: REV xem HR / mức 4 trong phiên review | Luôn 403 | 02 (R-DEC-183 PROPOSED muốn đổi) |
| SM-05 | BRD_NF BR-002: lead phải Qualified mới chuyển | Chuyển ở mọi trạng thái trừ converted / disqualified | BRD_NF (canonical theo D-06, R-DEC-182 PROPOSED) |
| SM-06 | 10 §7.2.4 / FR-DC-21: hàng chờ review theo khối / cây phòng; SLA 1 ngày làm việc | Theo phòng, 24 giờ lịch | 10, 04 |
| SM-07 | CLAUDE §2.2 / 04: MinIO / S3 | File cục bộ | CLAUDE / 04 (R-DEC-189 PROPOSED) |
| SM-08 | 07 §6.2 NFR-PERF-02: token đầu < 2 s | 13–67 s / lượt | 07 (R-DEC-200 chưa duyệt chấp nhận lệch) |
| SM-09 | 02 FR-ADM-05: mặc định phân loại "Nội bộ" | IDP mặc định CONFIDENTIAL (theo D-11 đề xuất) | 02 (R-DEC-188 PROPOSED) |
| SM-10 | 03 §1.1, R-DEC-16 / 82: không hiện chỉ số / cảnh báo module đóng băng | Hiện cho CEO, cộng vào ô Rủi ro | 03, R-DEC-16 |
| SM-11 | FR-DSH-07: mỗi widget một query | Mỗi trang một query | 06 / 03 |
| SM-12 | 10 §7.2.6: shape EP-RPT-02 / 03 (`department_name`, `okrs.items`, `workload_week`, `blocked`, `upcoming`; `freshness` là object) | Khác | 10 |
| SM-13 | R-DEC-12a: lọc khối ở tầng kiểm quyền | Lọc theo endpoint / service (`pillar_allows` luôn True) | Kết quả đúng; tài liệu cần mô tả lại |
| SM-14 | 10 EP-DC-10 / EP-PLT-02: bắt buộc Idempotency-Key | Không bắt buộc | 10 |
| SM-15 | CLAUDE §5.2: mỗi endpoint đúng một permission | 10 cho phép route chỉ cần token (R-DEC-31); 10 route không có permission | NC giữa CLAUDE và 10 |

**Chạy trên quyết định chưa duyệt** (không phải mismatch kỹ thuật, nhưng là rủi ro quản trị):
- R-DEC-176 (status "open"): migration 0028 + EP-SAL-10..13 đã áp lên DB chính.
- R-DEC-183, 185, 186, 188, 192 đang PROPOSED.
- R-DEC-199..202 do agent tự quyết theo ủy quyền, chưa được PO xác nhận.

## 19. Critical Findings và Risk Assessment

| ID | Mức | Module | Mô tả | Tài liệu | Code | Bằng chứng | Tác động | Đề xuất |
|---|---|---|---|---|---|---|---|---|
| C-01 | **CRITICAL** | IDP | Lộ dữ liệu mức 4 (lương, CCCD, tài khoản) qua: EP-DC-03 (giá trị thô); `pages[].text_content` ở EP-DC-05/14; đoạn trích tìm kiếm EP-24 qua HTTP. EMP / MGR cùng phòng đọc được | CLAUDE §5.3; 04 §9; 10 §7.2.4 | `idp/services/query_service.py:58`, `review_service.py:191`, `inbox_service.py:176`, `knowledge_search.py:94-108`, `scope.py:27` | `FieldResultOut` không che; test chỉ phủ field ở review | Vi phạm phân loại dữ liệu và NĐ 13/2023 | Che mức 4 ở mọi đường đọc; EMP chỉ đọc tài liệu mình gửi; test cho từng endpoint |
| C-02 | **CRITICAL** | IDP | STP dừng ở `AUTO_APPROVED`, không commit vào module đích, nhưng hộp thư hiện "đã ghi" | 04 §4/§7; 10 EP-DC-13 | `pipeline.py:260`; `inbox_service.py:43`; `schemas/capture.py:102` | Không có đường commit tự động; 4 loại tài liệu không có trường trọng yếu nên đi STP được | Người dùng tin dữ liệu đã ghi trong khi module đích không nhận; không có lineage / event / undo | Commit STP qua Action Registry (hoặc đưa vào hàng chờ "sẵn sàng ghi") + test |
| H-01 | HIGH | IDP | Giá trị mức 4 lưu plaintext JSONB trong `extracted_fields` / `import_rows` | 05 §2.7 | `idp/models/__init__.py:363,388`; `import_service.py:628` | information_schema | Rò rỉ khi lộ bản dump | Mã hóa cột (DEC + 05 + migration) |
| H-02 | HIGH | Finance | MGR xem số liệu tài chính toàn công ty qua dashboard / what-if / tool AI | permission_matrix:193; 10 §741 | `finance/routes/router.py:424-446` | Không có kiểm phạm vi; thẻ hub hiện cho MGR | Phá D-07 | Từ chối hoặc lọc theo phòng; ẩn thẻ; test |
| H-03 | HIGH | Meeting | Nút duyệt action item không gọi API, không tạo task (chức năng giả) | FR-MTG-04; UC-02 / 06 | `web/features/execution/PredictedActionList.tsx:42` | DB 6 action item, 0 task | UC-02 / 06 hỏng ở bước cuối; TC-M23-11 sai | API danh sách + duyệt (chủ trì), E2E kiểm task tồn tại |
| H-04 | HIGH | Auth | Đăng xuất không thu hồi refresh token | EP-ADM-03; FR-ADM-04 | `web/components/shell/Header.tsx:66` | 208 login, 0 logout; 208/211 token còn sống | Phiên không kết thúc được | Gọi `/auth/logout` ở `events.signOut` / BFF |
| H-05 | HIGH | Admin | CEO không quản lý được người dùng trên UI (trái D-21) | R-DEC-198 | `web/app/(app)/admin/users/page.tsx:9` | E2E khẳng định chỉ đọc | D-21 chưa đạt | `canEdit` theo `platform:admin`; sửa 06 và E2E |
| H-06 | HIGH | Org | Sửa phòng ban trên SCR-51 luôn lỗi (thiếu `version`) | EP-ORG-09 | `OrgForms.tsx:64` | Mock che lỗi | Không đổi tên / đổi cha phòng ban được | Gửi `version`; E2E trên API thật |
| H-07 | HIGH | Sales | Xóa deal có hợp đồng / hoạt động làm chúng mồ côi; sau đó hợp đồng trả 422 với mọi role | R-DEC-198 (toàn vẹn) | `sales_service.py:371-377` | Test xóa hợp đồng trước | Mất khả năng sửa / xóa hợp đồng | 409 khi còn con + test |
| H-08 | HIGH | Calendar | Sự kiện hạn task gán `owner_id` = mã nhân viên, người được giao không thấy, không đẩy sang Google / Outlook | R-DEC-122 | `task_service.py:236-241` | Test khẳng định mã NV | Tính năng lịch cho hạn chót hỏng | Map employee → user |
| H-09 | HIGH | Integration | Callback OAuth đòi Bearer, provider không gửi được | EP-INT-03 | `integrations.py:47-55` | Đọc code; chưa chạy live | Không kết nối lịch được (D13 P0) | Xác thực bằng `state` |
| H-10 | HIGH | AI | D-11 chỉ dựa vào `.env`; mặc định code + `.env.example` gửi INTERNAL lên cloud; tài liệu mâu thuẫn (02 §5 / CLAUDE §2.2 vs 01 §7.6 / 07 §7.1) | R-DEC-188 PROPOSED | `config.py:68`; `.env.example:67-68` | 1 lượt cloud ngày 2026-11-04 | Dữ liệu nội bộ có thể rời máy khi cài mới | PO duyệt R-DEC-188 → chốt egress trong code + đổi mặc định |
| H-11 | HIGH | Metric | Nhóm DQ (DQ-01 / 02) không ai xem được, kể cả CEO (403) | 03 §4.1 | `dashboard_service.py:64-66` | Test khẳng định DQ vắng | Chỉ số P0 không có UI | Rule hiển thị cho CEO / ADM |
| H-12 | HIGH | Metric / Executive | Chỉ số + cảnh báo của module đóng băng hiện cho CEO, chiếm 7/13 cảnh báo mở | R-DEC-16 / 82 | `metric_query.py:126-146,195-209` | DB alerts | Ô "Rủi ro" bị thổi phồng | Lọc FROZEN_CODES |
| H-13 | HIGH | Dashboard | Không có drill-down chỉ số → bản ghi → tài liệu; panel hiện "0 bản ghi" | FR-RPT-04; P06 | `dashboard_service.py:143` | 1787 dòng lineage chưa đọc | Lời hứa truy vết cốt lõi chưa đạt | Endpoint chỉ số → bản ghi (DEC) + link EP-DC-26 |
| H-14 | HIGH | Auth / Core | Không có rate limit (đăng nhập, API, AI 20 / phút) | CLAUDE §5.5; NFR-SEC-05 | `core/errors.py:106` | Không bao giờ raise | Lạm dụng, quá tải máy CPU | Ratify hoãn (R-DEC-187) hoặc làm |
| H-15 | HIGH | Auth | SSO / MFA (FR-ADM-04 P0) không có; 02 vẫn ghi P0 | 02 §4, §8 | — | — | Spec tuyên bố kiểm soát không tồn tại | Quyết định R-DEC-187; sửa 02 |
| H-16 | HIGH | Governance | Schema / API CRM chạy trên R-DEC-176 "open"; nhiều R-DEC PROPOSED đang được code tuân theo | CLAUDE §6.3 | migration 0028 | 13 dòng 251-252, 279 | Thẩm quyền spec không rõ | PO duyệt hoặc điều chỉnh |
| H-17 | HIGH | Finance | Chỉ tiêu Q4 = 20 tỷ mâu thuẫn tổng 3 tháng 85 tỷ và KR 85 tỷ | R-DEC-186 | `sales_seed.py:58-65` | DB | Số attainment vô nghĩa trên demo | PO chốt số; sửa seed |
| H-18 | HIGH | AI | 12/54 tool không chạy được; 10 §2.3 liệt kê ACT không tồn tại | 10 §2.3 | `tool_executor.py:81,517-530` | grep | CEO hỏi what-if, dự báo, báo cáo không được | Bind / thêm ACT hoặc đánh dấu planned |
| H-19 | HIGH | Strategy | CEO không có UI sửa / xóa Chiến lược / SO, CRUD Initiative + mốc | R-DEC-198; FR-STR-01/02 | `StrategyEditors.tsx`; `Milestones.tsx:27` | grep | D-21 chỉ đạt ở API | Thêm editor |
| M-01 | MEDIUM | Finance | Store không cập nhật ngay sau ghi tay; hai giá trị FIN-01 khác nhau trong cùng ngày | 03 §4.3 | finance_service (không event) | Test gọi recompute tay | Số không nhất quán | Event hoặc recompute sau ghi |
| M-02 | MEDIUM | Finance | Thiếu UI dự báo P&L, dòng tiền 13 tuần; không có thực thể Payment | EP-FIN-06/10; 05 §3 | specs.ts | — | Chức năng chỉ có API | Thêm màn hình; DEC Payment |
| M-03 | MEDIUM | Finance / IDP | MGR ghi doanh thu / tiền / hóa đơn công ty qua IDP | 10 §741 | `idp/actions/finance.py` | — | Vượt D-07 | Kiểm phạm vi trong ACT |
| M-04 | MEDIUM | HR | Nghỉ phép P0 chưa làm; workload bỏ qua nghỉ phép | FR-HR-01 | `hr.leaves` | 0 dòng | Năng lực bị tính cao | Làm hoặc hoãn chính thức |
| M-05 | MEDIUM | HR | Không có UI lịch sử lương / mức 4 | R-DEC-198 | — | — | D-21 một phần | Màn hình chi tiết nhân viên |
| M-06 | MEDIUM | RBAC | DIR `scope_pillars = []` cấp được qua API (= mọi khối + lương) | R-DEC-12a | `user_admin_service.py:140` | — | Leo thang đặc quyền quanh luật "ADM không cấp CEO" | 422 khi DIR không có khối |
| M-07 | MEDIUM | RBAC | Thiếu ma trận quyền trong 02 (DG-01) | 02 | — | — | Không audit được quyền | Sinh từ code + test so khớp |
| M-08 | MEDIUM | KPI | Khóa kỳ không thao tác được | FR-KPI-08 | `kpi_target_service.py:129` | 0/36 locked | — | Thao tác đóng kỳ |
| M-09 | MEDIUM | Workflow | Yêu cầu quá hạn không quyết được (EXPIRED rollback); không có escalation | FR-WF-04 | `approval_service.py:385` | 1 yêu cầu seed quá hạn | Hộp duyệt kẹt | Job hết hạn / escalation |
| M-10 | MEDIUM | Meeting | Biên bản chỉ sinh action item mồ côi: không meeting, decision, summary | FR-MTG-02/05 | catalog/meeting.py | — | Decision Log không được nuôi từ họp | Mở rộng ACT |
| M-11 | MEDIUM | Decision | Không xác minh kết quả trên UI; job nhắc cả quyết định đã hủy | R-DEC-135 | `meeting_service.py:248` | — | Nhắc vô tận | UI verify + lọc trạng thái |
| M-12 | MEDIUM | IDP | HEIC luôn bị từ chối; giới hạn 300 trang không áp; .doc / .xls không đọc được | FR-DC-07 | `mime.py:81` | — | Ảnh iPhone lỗi | Sniff HEIC; áp giới hạn |
| M-13 | MEDIUM | IDP | Đổi loại tài liệu khi review bị bỏ qua; ngưỡng STP hardcode | FR-DC-09/15/22 | `schemas/__init__.py:206`; `pipeline.py:63` | — | Admin chỉnh ngưỡng không có tác dụng | Làm re-extract; đọc `schema.thresholds` |
| M-14 | MEDIUM | IDP | Hàng chờ review lệch phạm vi hộp thư | 10 §7.2.4 | `review_service.py:116` | — | CFO không thấy tài liệu khối F | Dùng `inbox_filter` |
| M-15 | MEDIUM | IDP / UI | Giao lại / gộp / chấp nhận tất cả / bàn phím chỉ có API | FR-DC-20/22 | — | — | UX review dưới P0 | Thêm UI |
| M-16 | MEDIUM | Data | Lineage không đọc được cho doanh thu, chi phí, deal, quyết định | FR-DATA-04 | `lineage_service.py:20` | 422 | Không truy được nguồn | Mở whitelist (DEC) |
| M-17 | MEDIUM | AI | Chỉ chạy agent `ceo` cho mọi role; ngân sách theo agent không áp; Evaluation Engine gây hiểu nhầm; 0 insight trên demo; briefing chỉ dòng tóm tắt; không có phản hồi | 07, 03 | — | DB | Năng lực D27 hẹp hơn tài liệu | Theo roadmap §22 |
| M-18 | MEDIUM | Dashboard | Không có UI tùy chỉnh ô; KPI phòng = số toàn công ty; một query / trang; G1 nghiệm thu dùng ngày thật | 03, R-DEC-145 | `ExecutiveView.tsx`; `acceptance_service.py:71` | TC-M21-12 sai | Màn hình điều hành chưa đúng spec | §22 |
| M-19 | MEDIUM | DB | Schema `public` còn dữ liệu v1 (có `password_hash`); 22 bảng thiếu `tenant_id`; audit có thể TRUNCATE | R-DEC-189 / 07 / 13 | — | SELECT | Rác dữ liệu, rủi ro audit | Quyết định R-DEC-189; role DB thường |
| M-20 | MEDIUM | Sales / Seed | Demo không thể hiện CRM: 0 lịch sử giai đoạn, 0 hợp đồng, 1 chủ deal, không có MGR / EMP Sales; sales page thiếu attainment / bookings | 08; BRD_NF DASH | `sales_seed.py`; `SalesPipelineView.tsx:13` | DB | Demo gây hiểu nhầm | Seed + KPI cards |
| M-21 | MEDIUM | QA | Coverage chưa đo cho v4; hiệu năng đo bằng replay | 14 §1.3 | — | — | Gate C chưa chứng minh | Đo lại |
| L-xx | LOW | nhiều | 40+ điểm nhỏ: chú giải vai trò thiếu `l / k / u`; ranking hiện UUID; dismiss cảnh báo; Idempotency-Key 2 endpoint; `no-store` mặc định; image `:latest`; mailpit không healthcheck; `/metrics` không xác thực; tên trường lỗi thời; xóa lead / contact để hoạt động mồ côi; `owner_id` không kiểm user tồn tại; `similar()` không lọc tenant; v.v. | | | | | Chi tiết trong các bảng §8 và báo cáo nhóm (`var/v4-audit/restore/`) |

**Đánh giá rủi ro tổng thể:**

| Rủi ro | Mức | Lý do |
|---|---|---|
| Bảo mật dữ liệu nhạy cảm | **Cao** | C-01, H-01, H-02, H-04, H-14 |
| Toàn vẹn dữ liệu | **Cao** | C-02, H-07, M-01 |
| Đúng nghiệp vụ trên demo | **Trung bình – Cao** | H-03, H-08, H-12, H-17, M-20 |
| Đáp ứng D-21 | **Trung bình** | API đạt; UI thiếu (H-05, H-06, H-19, M-05) |
| Quản trị tài liệu / quyết định | **Trung bình** | H-16, DG-01..05 |
| Kỹ thuật nền (API, DB, kiến trúc) | **Thấp** | Contract và DB khớp; test backend xanh |

## 20. Module Completion Statistics

**Công thức:**
- **Documented** = số tính năng tài liệu yêu cầu, không tính OOS và NEEDS CLARIFICATION.
- **Required** = Documented − DOCUMENTATION GAP (mục DG là code không có yêu cầu nên không vào mẫu số).
- **Completion %** = (Verified + Implemented) ÷ Required.
- Partial, Spec mismatch, Missing, Broken **không** tính là hoàn thành.
- Cột "Partial" trong bảng cuối gồm cả SPEC MISMATCH.

| Nhóm | Documented | Required | V | I | P | SM | M | B | DG | NC | OOS |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Mô-đun nghiệp vụ (27 dòng) | 427 | 421 | 246 | 16 | 98 | 17 | 30 | 14 | 6 | 15 | 66 |
| Cross-cutting (API, DB, kiến trúc, ID) | 47 | 43 | 18 | 10 | 7 | 3 | 5 | 0 | 4 | 4 | 0 |

**Các độ phủ** (mô-đun nghiệp vụ):
- Implementation coverage **62%**
- Verified feature coverage **58%**
- Có ít nhất một phần code **93%**
- Test coverage cấp tính năng **94%**
- Documentation coverage **99%**

Nếu bỏ dòng BRD_Newfeature (P1 mở rộng): 61% hoàn thành, 58% đã kiểm chứng.

**Cross-cutting:** 65% hoàn thành, 42% đã kiểm chứng.

## 21. Overall Project Completion Assessment

| Phương diện | Đánh giá |
|---|---|
| **Hoàn thành nghiệp vụ (P0 + v4 hiện hành)** | **62%** tính năng đã làm, **58%** có bằng chứng kiểm thử; 93% có ít nhất một phần code |
| Nền kỹ thuật | Mạnh: API ↔ spec 100%, DB ↔ ORM 100%, kiến trúc module được test canh giữ, 1709 test backend |
| Yêu cầu D-21 (CEO CRUD) | PARTIALLY IMPLEMENTED: API đạt, UI và toàn vẹn chưa |
| Sẵn sàng demo | Chạy được và đăng nhập ổn định. Các luồng UC-02 / UC-06 (họp → việc), lịch, drill-down chỉ số, chất lượng dữ liệu **không nên trình diễn** cho tới khi sửa H-03, H-08, H-13, H-11 |
| Sẵn sàng production | **Chưa**: C-01, C-02, H-01, H-04, H-14, H-15 cộng backlog Phase 8 |
| Quản trị tài liệu | Cần PO duyệt / điều chỉnh R-DEC-176..202 và cập nhật `CLAUDE.md`, 02 (ma trận quyền), 05 (39 bảng) |

**Kết luận:** dự án ở mức **MVP demo có nền tốt nhưng chưa hoàn thiện nghiệp vụ**. Cần một đợt P0 khoảng 15 hạng mục (bảng dưới) để đạt "đúng nghiệp vụ, không lộ dữ liệu, không có chức năng giả".

## 22. Recommended Development Roadmap

| Task ID | Module | Công việc | Lý do | Priority | Dependencies | Acceptance Criteria |
|---|---|---|---|---|---|---|
| RM-01 | IDP | Che mức 4 trên EP-DC-03, `pages[]` (EP-DC-05/14), đoạn trích EP-24; EMP chỉ đọc tài liệu mình gửi | C-01 | P0 | — | EMP / MGR nhận `{masked:true}` hoặc không có snippet cho tài liệu HR_ROSTER mức 4; CEO / DIR-O thấy giá trị; integration test cho từng endpoint |
| RM-02 | IDP | Commit STP qua Action Registry (hoặc hàng chờ "sẵn sàng ghi") | C-02 | P0 | R-DEC về actor commit STP | Tài liệu STP → COMMITTED; bản ghi đích + lineage + `idp.document_committed`; hộp thư không còn xếp `AUTO_APPROVED` vào "committed" |
| RM-03 | Finance | Phạm vi MGR cho `/finance/dashboard`, what-if, tool AI; ẩn thẻ hub | H-02 | P0 | DEC | MGR gọi dashboard → 403 hoặc chỉ số phòng; test integration + E2E |
| RM-04 | Meeting | API danh sách / duyệt action item (chủ trì) → tạo task thật | H-03 | P0 | DEC (EP mới) | E2E: dán biên bản → duyệt → task xuất hiện ở "Task của tôi"; `action_items.task_id` có giá trị; người không chủ trì → 403 |
| RM-05 | Auth | Đăng xuất gọi `/auth/logout` | H-04 | P0 | — | Sau đăng xuất: refresh token bị thu hồi, có audit `auth.logout`, dùng lại token cũ → 401 |
| RM-06 | Admin | CEO tạo / sửa / khóa người dùng trên UI; sửa 06 SCR-53 + E2E | H-05 | P0 | — | E2E: CEO tạo, sửa, khóa user; ADM vẫn không cấp được CEO (403) |
| RM-07 | Org | Sửa phòng ban gửi `version` | H-06 | P0 | — | E2E API thật: đổi tên phòng ban → 200, cây hiện tên mới; version cũ → 409 |
| RM-08 | Sales | Chặn xóa deal còn hợp đồng / hoạt động / lead đã chuyển | H-07 | P0 | — | DELETE deal có hợp đồng sống → 409; hợp đồng GET vẫn 200; test |
| RM-09 | Calendar | Sửa owner sự kiện hạn chót (employee → user); callback OAuth xác thực bằng `state` | H-08, H-09 | P0 | Secret OAuth (người) | Người được giao thấy sự kiện "Hạn: …"; callback không có Authorization + state hợp lệ → kết nối thành công |
| RM-10 | Metric | Lọc chỉ số / cảnh báo đóng băng; hiện nhóm DQ cho CEO / ADM | H-11, H-12 | P0 | DEC (ADM) | `open_risks` của CEO không chứa RSK / PRD; `/home/metrics/METRIC-DQ-01` → 200 với CEO |
| RM-11 | Governance | PO duyệt / điều chỉnh R-DEC-176, 183, 185, 186, 188, 192, 199..202; chốt số chỉ tiêu Q4 | H-16, H-17, H-10 | P0 | PO | 13 không còn PROPOSED liên quan code đang chạy; seed Q4 = tổng tháng (hoặc quy tắc được ghi) |
| RM-12 | AI | Chốt egress trong code + mặc định Ollama trong `.env.example` / config (nếu R-DEC-188 được duyệt) | H-10 | P0 | RM-11 | Unit: `route(INTERNAL)` có key cloud vẫn không chứa provider cloud; `.env.example` primary = ollama |
| RM-13 | IDP | Mã hóa giá trị mức 4 khi lưu | H-01 | P0 | DEC + 05 + migration | Cột mã hóa; bản dump DB không có lương dạng chữ |
| RM-14 | Dashboard | Drill-down chỉ số → bản ghi → trang tài liệu; `record_count` thật | H-13, M-16 | P1 | DEC (EP, whitelist lineage) | Bấm FIN-01 ra danh sách bản ghi đóng góp; tới trang nguồn ≤ 3 click |
| RM-15 | Strategy / HR / Finance UI | Editor Chiến lược / SO / Initiative / mốc; chi tiết nhân viên mức 4 + lịch sử lương; dự báo P&L + dòng tiền 13 tuần; sửa đội nhóm / gán nhân sự | H-19, M-02, M-05 | P1 | — | E2E: CEO C/R/U/D từng entity từ UI; 409 / 422 hiện tại chỗ |
| RM-16 | Auth / AI | Rate limit (đăng nhập, API, AI 20 / phút) | H-14 | P1 | R-DEC-187 | Lần thứ 21 trong 60 s → 429 `RATE_LIMIT_EXCEEDED` + Retry-After |
| RM-17 | Finance | Metric Store cập nhật sau ghi tay; dashboard đọc store; DELETE số dư tiền / dự báo (hoặc sửa 02 / 10) | M-01, SM-01, SM-02 | P1 | DEC | Sau POST doanh thu, FIN-01 ở `/dashboard/metrics` đổi không cần recompute tay |
| RM-18 | RBAC / Docs | Ma trận quyền trong 02 sinh từ code + test so khớp; 422 cho DIR không có khối; scope IDP finance ACT cho MGR | M-06, M-07, M-03 | P1 | PO review | 02 có bảng 7 role × quyền; test parse bảng = `ROLE_PERMISSIONS` |
| RM-19 | IDP | HEIC, giới hạn trang, đổi loại tài liệu, ngưỡng STP theo schema, phạm vi hàng chờ, UI giao lại / gộp / chấp nhận tất cả | M-12..M-15 | P1 | — | HEIC → 202; PDF 301 trang → 413; PATCH `doc_type` re-extract; DIR-F thấy tài liệu khối F trong hàng chờ |
| RM-20 | AI | Bind 12 tool hoặc đánh dấu planned; agent theo vai; Evaluation qua gateway thật; insight trên demo; briefing 7 khối + hành động | H-18, M-17 | P1 | DEC | Contract kiểm mọi tool được quảng bá đều chạy được; seed sạch → ≥ 1 insight; E2E briefing hiện TODAY + RECOMMENDATIONS |
| RM-21 | Workflow / KPI / Decision | Job hết hạn + escalation; thao tác đóng kỳ KPI; UI xác minh quyết định | M-08, M-09, M-11 | P1 | DEC (EP đóng kỳ) | PENDING quá hạn → EXPIRED / escalated + thông báo; kỳ khóa → ghi 409 |
| RM-22 | Seed / Sales UI | Lịch sử giai đoạn, hợp đồng, nhiều chủ deal, tài khoản MGR / EMP Sales, vị trí; KPI cards attainment / bookings | M-20 | P1 | 08 | Detail deal có lịch sử; ranking ≥ 3 dòng; sales page hiện attainment = `/sales/dashboard` |
| RM-23 | QA | Đo coverage; đo lại hiệu năng với cấu hình live; test round-trip migration; sửa các TC "Passed" sai | M-21, DG-09 | P1 | — | 14 có bảng coverage theo module; số đo perf mới; TC-M23-11 / M21-12 / M22-07 / M25-02 đúng trạng thái |
| RM-24 | Docs | Cập nhật `CLAUDE.md` (người duyệt), 05 cho 39 bảng, version 00–14, 10 field-level FIN / SAL | DG-02..05 | P1 | Human | `12` khớp header file; mọi bảng trong metadata có trong 05 (script) |
| RM-25 | HR / Org | Nghỉ phép + năng lực; kiêm nhiệm; export cơ cấu; xem như người dùng | M-04, AUD-ORG-08 | P2 | DEC | Nghỉ phép được duyệt giảm năng lực workload; CRUD có test phạm vi |
| RM-26 | Dashboard | Dialog tùy chỉnh ô; widget độc lập; KPI theo phòng; G1 dùng ngày nghiệp vụ; báo cáo theo mẫu / lịch | M-18 | P2 | DEC | E2E: lưu 4 ô và tải lại vẫn còn; một widget lỗi không làm trống trang |
| RM-27 | CRM phase 2 | Cấu hình pipeline, BANT, deal ↔ contact, forecast category / snapshot, aging, win / loss | BRD_NF (OOS hiện tại) | P2 | R-DEC-176 / 179 / 182 | UAT-007 / 009 / 012 / 013 / 015 đạt |
| RM-28 | DB / Infra | Quyết định schema `public`; role DB thường, chặn TRUNCATE audit; tenant_id hoặc danh sách miễn trừ; pin image | M-19 | P2 | R-DEC-189 | Không còn bảng `public`; TRUNCATE audit bằng role app → lỗi |
| RM-29 | UI | Chú giải vai trò, tên chủ deal thay UUID, dismiss cảnh báo, nút Dừng chat, panel AI ngữ cảnh, sửa sự kiện lịch, Idempotency-Key 2 endpoint, `no-store` mặc định | L-xx | P3 | — | Từng mục có test đơn vị / E2E tương ứng |

## 23. Evidence & Source References

**Tài liệu đã đọc:**
- `docs/_reference/SOURCE-BRD-v1.1.md` (+ Bổ sung), `SOURCE-UIUX.md`, `BRD_Newfeature.md`
- `docs/1.CONTEXT/00, 01`; `docs/2.PRODUCT/02–06`; `docs/3.EXECUTION/07–11, 16`
- `docs/4.GOVERNANCE/12–14, DEC-REGISTRY, TRACEABILITY-SKELETON`; `docs/handover/*`; `docs/DEMO-SCRIPT.md`
- `CLAUDE.md`, `README.md`; `deliverables/M8-CRM-PLAN.md`, `deliverables/v4-demo/*` (đối chiếu tuyên bố)

**Code chính:**
- `api/modules/*/{routes,services,models,schemas,repositories}`
- `api/core/{security,deps,permissions,field_policy,health,ops_routes,storage,errors,idempotency,events}`
- `api/modules/auth/permission_matrix.py`; `apps/api/alembic/versions/0001..0028`
- `web/lib/permissions.ts`; `web/features/{records,crm,sales,finance,admin,goals,work,execution,idp,capture,knowledge,ai,home,dashboard,briefing}`
- `docker-compose.yml`, `docker-compose.full.yml`, `.env.example`

**Test:**
- `tests/{unit,integration,contract,events,architecture,ai_eval}`
- `e2e/*.spec.ts`
- Log `var/v4-audit/restore/pytest-full2.log`, `var/v4-audit/dev/final2/e2e-full2.log`, `e2e-full3.log`

**DB (chỉ SELECT):**
- `platform.alembic_version`, `information_schema`
- `auth.roles`, `platform.audit_logs` (đếm login / logout)
- `platform.alerts` × `platform.metrics`, `platform.metric_values`
- `execution.action_items`, `execution.kpi_targets.locked_at`, `hr.positions`, `hr.leaves`
- `sales.deal_stage_history`, `sales.contracts`, `sales.sales_targets`
- `ai.model_call_logs`, `ai.insights`, `ai.ai_evaluations`
- `idp.document_types`, `idp.document_pages.embedding`, schema `public`

**Tự kiểm lại bởi người tổng hợp** (đọc trực tiếp code / DB): C-01 (`query_service.py:58`), C-02 (`inbox_service.py:43`, `schemas/capture.py:102`), H-02 (`router.py:424-446`), H-03 (`PredictedActionList.tsx:42`), H-04 (208 login / 0 logout), H-05 (`admin/users/page.tsx:9`), H-06 (`OrgForms.tsx:64`), H-07 (`sales_service.py:371-377`), H-08 (`task_service.py:236-241`), H-09 (`integrations.py:47-55`), H-10 (`config.py:68`, `.env.example:67-68`), H-12 (alerts PRD 2 + RSK 5 / 13), H-13 (`dashboard_service.py:143`), H-18 (grep binding).

**Báo cáo nhóm chi tiết** (đầu vào của báo cáo này, chứa thêm bằng chứng dòng-cấp): lưu ngoài repo tại `var/v4-audit/restore/` (gitignore).

## 24. Audit Limitations và Unverified Items

- **Không gọi ứng dụng đang chạy:** hành vi giao diện được suy từ code, route rule và kết quả E2E có sẵn. Một số lỗi (sửa phòng ban, PATCH null → 500, MGR xem `/business/finance`) là kết luận ở mức code, chưa tái hiện trực tiếp.
- **Không chạy test:** số liệu test lấy từ log tại commit `67c7218` (pytest; mã test không đổi tới HEAD) và `cdc794a` (Vitest, E2E).
- **NOT VERIFIED:**
  - code coverage v4
  - hiệu năng với cấu hình live
  - a11y trên project real
  - vector search (0 embedding)
  - OAuth Google / Outlook live
  - OCR tiếng Việt
  - email thật
  - quyền giao nhau agent ∩ người dùng ở runtime cho event-driven AI
  - thời gian lưu audit ≥ 2 năm
  - lịch beat thực tế
- **Không đọc `.env`** (chứa secret): giá trị runtime chỉ suy từ DB và compose.
- **NEEDS CLARIFICATION (15 mục nghiệp vụ + 4 cross-cutting)** không vào mẫu số; cần PO trả lời trước khi tính lại tỷ lệ. Các mục lớn:
  - chỉ tiêu Q4
  - D-11 với 02 §5
  - funnel theo R-DEC-186 hay BRD_NF
  - AI hỏi lịch so với R-DEC-123
  - CEO có quyết `task_reassign` không
  - EMP xem mức 4 của chính mình
  - schema `public`
- **Phạm vi BRD_Newfeature:** 32 tính năng tính là OUT OF SCOPE theo R-DEC-05 / 09 ("CRM = P1"). Nếu PO duyệt R-DEC-179 / 182 (v4 = v3 + CRM đầy đủ), 15 mục Must sẽ chuyển thành NOT IMPLEMENTED và tỷ lệ Sales giảm.
- **Quyết định PROPOSED** được ghi nhận là chưa duyệt; báo cáo không tự phê duyệt.

---

## Bảng tổng hợp cuối

Completion % = (Verified + Implemented) ÷ (Documented − Doc gap). "Partial" gồm cả SPEC MISMATCH. Priority = mức ưu tiên của việc cần làm tiếp theo cho module.

| Module | Documented Features | Verified | Implemented | Partial | Missing | Broken | Completion % | Priority |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| Strategy (D07) | 7 | 2 | 0 | 5 | 0 | 0 | 29% | P1 |
| KPI (D08) | 9 | 5 | 0 | 4 | 0 | 0 | 56% | P1 |
| OKR + Check-in (D09/D10) | 12 | 8 | 1 | 0 | 3 | 0 | 75% | P2 |
| Task / Project / Workload (D11) | 17 | 10 | 1 | 3 | 3 | 0 | 65% | P2 |
| Meeting / Decision Log (D12/D28) | 11 | 5 | 1 | 2 | 2 | 1 | 55% | P0 |
| Calendar / Integration (D13/D06) | 5 | 2 | 1 | 0 | 0 | 2 | 60% | P0 |
| Workflow & Approval (D04) | 3 | 2 | 0 | 1 | 0 | 0 | 67% | P1 |
| Notification (D05) | 4 | 3 | 0 | 1 | 0 | 0 | 75% | P2 |
| Execution dashboard / records | 2 | 2 | 0 | 0 | 0 | 0 | 100% | P3 |
| Finance (D15) | 34 | 20 | 1 | 12 | 0 | 0 | 64% | P0 |
| Sales/CRM — Aureon spec (D17) | 22 | 18 | 1 | 1 | 0 | 1 | 90% | P0 |
| Sales/CRM — BRD_Newfeature (feat + BR) | 86 | 53 | 3 | 30 | 0 | 0 | 65% | P1 |
| Organization (D01) | 11 | 6 | 0 | 3 | 1 | 1 | 55% | P0 |
| HR (D16) | 15 | 10 | 0 | 2 | 2 | 0 | 71% | P1 |
| Users / Roles / Admin (D02) | 9 | 7 | 0 | 1 | 1 | 0 | 78% | P0 |
| Authentication (D02) | 10 | 7 | 0 | 0 | 2 | 1 | 70% | P0 |
| RBAC / permission model | 8 | 4 | 0 | 3 | 0 | 0 | 57% | P1 |
| Data Capture / IDP (D03) | 52 | 26 | 1 | 15 | 6 | 4 | 52% | P0 |
| Knowledge search (D14) | 3 | 3 | 0 | 0 | 0 | 0 | 100% | P0 |
| Data Foundation FR-DATA | 9 | 3 | 2 | 4 | 0 | 0 | 56% | P1 |
| AI Platform + CEO Assistant (D26/D27) | 50 | 27 | 3 | 11 | 6 | 2 | 61% | P0 |
| Dashboards & Reporting (D28) | 26 | 8 | 1 | 13 | 3 | 1 | 35% | P0 |
| Metric store / Alerts | 12 | 6 | 0 | 3 | 1 | 1 | 55% | P0 |
| Platform services | 4 | 3 | 0 | 1 | 0 | 0 | 75% | P2 |
| Product (frozen D22) | 2 | 2 | 0 | 0 | 0 | 0 | 100% | P3 |
| Risk (frozen D25) | 3 | 3 | 0 | 0 | 0 | 0 | 100% | P3 |
| Freeze governance (R-DEC-16) | 1 | 1 | 0 | 0 | 0 | 0 | 100% | P3 |
| API contract (cross-cutting) | 15 | 8 | 2 | 2 | 1 | 0 | 77% | P2 |
| Database (cross-cutting) | 9 | 3 | 2 | 3 | 0 | 0 | 62% | P1 |
| Architecture / NFR (cross-cutting) | 19 | 5 | 6 | 4 | 4 | 0 | 58% | P1 |
| ID registry (cross-cutting) | 4 | 2 | 0 | 1 | 0 | 0 | 67% | P3 |
| **Subtotal — functional modules** | **427** | **246** | **16** | **115** | **30** | **14** | **62%** | — |
| **Subtotal — cross-cutting conformance** | **47** | **18** | **10** | **10** | **5** | **0** | **65%** | — |

