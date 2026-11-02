# Đối chiếu Code ↔ Docs trước khi rebuild stack (sau M4)

> Ngày: 2026-11-03 · Nhánh `v3/m4-doc-code-conformance` @ `5d7bcc6` (7 commit trên `main`, chưa push)
> Phạm vi: doc set `docs/` 00–14 + `docs/handover/` + `CLAUDE.md` ↔ code `apps/`, Dockerfile, Compose,
> worker/beat, frontend, DB đang chạy. **Chỉ đối chiếu — không rebuild, không đổi requirement/kiến trúc.**

## 1. Kết luận

| Câu hỏi | Trả lời |
|---|---|
| Code M4 có đúng tài liệu không? | **Có, về hành vi.** Contract test 3 chiều EP↔route↔permission 0 lệch; 2 job retention, 16 beat entry, 3 sửa WCAG đều có trong code và có test. |
| Stack đang chạy có code M4 không? | **Không.** Image api = HEAD **trừ đúng 7 file M4**; image web = HEAD **trừ đúng 2 file M4**. Mọi commit trước M4 đã có trong image. |
| Rebuild có an toàn không? | **Có, với 2 điều kiện** (§6): mạng ra ngoài khi build (tải lại model OCR + gói npm), và kiểm model OCR sau build. Không có migration DB; dữ liệu và file nằm trong volume. |
| Có sai lệch cần xử lý trước? | **Có — lỗi chú thích do chính M4 tạo ra** ở `10` §7.3 (16/29 số EP v2.1 sai, 1 ID trùng, 1 câu về quyền lương sai). Không ảnh hưởng runtime, nhưng là tài liệu sai → nên sửa trước khi merge. |
| Sai lệch tồn tại từ trước M4? | **Có 3 cái đáng chú ý:** không có rate limit AI 20 req/phút; không có timeout 5 s/tool; timeout chat 90 s ≠ 30 s/lượt trong 07. Cần human quyết (§7). |

## 2. Phương pháp & bằng chứng

Mọi kết luận dưới đây có bằng chứng máy; mục nào không đủ bằng chứng ghi **UNVERIFIED**.

| Lớp | Cách kiểm |
|---|---|
| API | `tests/contract/test_catalog_conformance.py` (41 test contract) + parse thủ công các dòng ngoài mẫu |
| Image ↔ source | `sha256` từng file tracked trong container vs `git show HEAD:<file>` (`var/m4/img_diff.sh`) — api 389 file, web 284 file + messages, alembic 29 file |
| Runtime | `beat_schedule`/`celery_app.tasks` trong container; CSS mà web **đang phục vụ** (`/_next/static/*.css`) và bundle JS |
| DB | `platform.alembic_version`, schema, extension, đếm dữ liệu IDP trên DB `aureon` |
| Env | hash `ADMIN_BOOTSTRAP_PASSWORD` dotenv vs biến môi trường trong container (chỉ so bằng, không in giá trị) |

## 3. Tổng hợp phân loại

| Phân loại | Số mục | Ghi chú |
|---|--:|---|
| MATCH | 32 | A1–A9, D1–D7, S1–S7, I1–I6, F1–F3 |
| MISMATCH | 9 | 3 do M4 (chú thích `10` §7.3: M-1..M-3) · 2 code↔doc từ trước (X-3 timeout chat, X-4 Dockerfile) · 4 doc↔doc trong `CLAUDE.md` (G-1..G-4) |
| MISSING | 3 | rate limit AI (X-1), timeout/tool (X-2), stack chưa chạy code M4 (§5) |
| UNDOCUMENTED | 4 | 45 entity, MinIO không dùng, file rác test, SCR id cũ trong code |
| UNVERIFIED | 3 | version doc chờ promote, R-DEC-147..152 chờ human, `check_env.sh` chưa tự kiểm Compose |

## 4. Chi tiết đối chiếu

### 4.1. Contract API & registry (`10`, `03`, `05`)

| # | Yêu cầu | Bằng chứng | KQ |
|---|---|---|---|
| A1 | Mọi `EP-*` trong `10` §7 có route | TC-M4-01 xanh | MATCH |
| A2 | Mọi route có `EP-*` | TC-M4-02 xanh, 328/328 | MATCH |
| A3 | Permission route ⊆ permission EP | TC-M4-03 xanh | MATCH |
| A4 | Endpoint public chỉ EP-01/02/06, không `/auth/register` | `test_api_contract` + grep | MATCH |
| A5 | Bảng 54 `TOOL-*` (§2.3) = registry | TC-M4-04a | MATCH |
| A6 | Bảng 34 `METRIC-*` (`03` §4.2) = catalog | TC-M4-04b | MATCH |
| A7 | Mọi `ACT-*` trong docs có trong code | TC-M4-04c | MATCH |
| A8 | Mọi event `publish_in_tx` nhận đều có trong docs | TC-M4-14 | MATCH |
| A9 | Shared types FE = OpenAPI | `gen_shared_types.py` → 561 type, diff 0 | MATCH |
| **M-1** | `10` §7.3 cột "EP v2.1" | So với chú thích route trong code: **16/29 dòng sai số** (vd PRD-01 ghi EP-95, đúng EP-90; RSK-01 ghi EP-106, đúng EP-100; HR-06 ghi EP-86, đúng EP-80; PLT-01/02 ghi EP-59, đúng EP-56). Bảng đúng ở §7.1 dưới. | **MISMATCH (M4)** |
| **M-2** | `10` §7.3 `EP-GOL-01` (milestones) | Route đã mang `EP-STR-17..21` (`10` dòng 470 + `summary` trong `execution/routes/goals.py`). Parser contract không nhận ID dạng dải `..` → M4 gán thêm ID mới → **2 ID cho 1 endpoint**. Số "69 route chưa có ID" thực ra là **64**. | **MISMATCH (M4)** |
| **M-3** | `10` §7.3 `EP-HR-07` ghi "mức 4 chỉ ROLE-CEO/ROLE-ADM" | Code `core/field_policy.sees_level4`: **CEO hoặc DIR khối O**; ADM không thấy (khớp 02 §6.2) | **MISMATCH (M4)** |

### 4.2. Dữ liệu & DB (`05`)

| # | Yêu cầu | Bằng chứng | KQ |
|---|---|---|---|
| D1 | Migration ở head, reversible | DB `aureon` & `aureon_m4` = `0027_external_event_link_c19` = head code; M4 **không** thêm migration | MATCH |
| D2 | Mỗi module một schema; dashboard đọc qua service | 10 schema: ai, auth, execution, finance, hr, idp, platform, product, risk, sales | MATCH (CLAUDE §2.2 ghi lẫn "11 schema"/"10 schema" — xem G-3) |
| D3 | pgvector | `vector 0.8.7`, `pgcrypto 1.3` | MATCH |
| D4 | Tiền BIGINT, không float | không có `Mapped[float]` cho cột tiền | MATCH |
| D5 | Retention `import_rows` (OQ-05-11) | `retention_service.py` + repository, 5 test | MATCH (code) |
| D6 | `ENT-Workload` không bảng, tính từ tasks (40 h/tuần, 110%, mặc định 4 h) | `execution/services/workload.py` đúng 3 hằng số | MATCH |
| D7 | `ENT-Milestone`, `ENT-ApprovalRule` | model `execution.milestones`, `platform.approval_rules` | MATCH |
| **U-1** | Danh mục entity | `05` nêu 41 `ENT-*`; toàn bộ doc v3 nêu 54; code gắn 91. **45 entity nền v2.1** (Budget, Invoice, Deal, Employee, Risk, Product, User, Role, …) không có trong doc v3 nào. CLAUDE §5.9 ghi "79 entity" — không khớp cả docs lẫn code. | **UNDOCUMENTED** (cùng loại GAP-02 trước M4) |

### 4.3. Bảo mật & giới hạn AI (`02`, `07` §145, CLAUDE §5.3–5.5)

| # | Yêu cầu | Bằng chứng | KQ |
|---|---|---|---|
| S1 | JWT RS256, không HS256 | `ALGORITHM = "RS256"`; ký chỉ gọi từ `modules/auth/services/auth_service.py` | MATCH |
| S2 | Khóa riêng mount read-only | `./keys:/app/keys:ro`, container `rw=false` | MATCH (CLAUDE ghi `secrets/`, R-DEC-81 chuyển `./keys` — G-4) |
| S3 | 7 role + AI actor | `ROLE_PERMISSIONS` = ADM, AI, CEO, DIR, EMP, MGR, REV | MATCH |
| S4 | Mức 4 chỉ CEO + DIR khối O | `sees_level4` | MATCH |
| S5 | Không SDK vendor, không LlamaIndex | không import `openai/anthropic/llama_index/langchain` | MATCH (CLAUDE §2.2 vẫn ghi "LlamaIndex + pgvector" trái R-DEC-141 — G-2) |
| S6 | Autonomy trần L3, L4 khóa | `ai_autonomy_ceiling = "L3"` | MATCH |
| S7 | temperature 0,2 · ≤ 2048 token · ≤ 8 tool call/lượt · ngân sách tháng, cảnh báo 80% | config + `MAX_TOOL_CALLS = 8` | MATCH |
| **X-1** | **≤ 20 request AI/phút/người → `429 RATE_LIMIT_EXCEEDED`** (07 §145, 10 §1.4, CLAUDE §5.3 "middleware verify token + rate limit") | `RateLimitError` khai báo ở `core/errors.py` nhưng **không nơi nào raise**; middleware chỉ có Tenant + RequestId; không có `core/rate_limit.py`; contract test chỉ kiểm mã lỗi tồn tại | **MISSING (trước M4)** |
| **X-2** | **5 s/tool** (07 §145) | không có `wait_for`/`timeout` nào trong `modules/ai` | **MISSING (trước M4)** |
| **X-3** | **30 s/lượt** (07 §145) | `ai_turn_timeout_sec = 30` chỉ dùng cho task ≠ chat; task chat dùng `CHAT_TIMEOUT_SECONDS = 90` (`model_gateway/routing.py:106`), không có DEC | **MISMATCH (trước M4)** |

### 4.4. Hạ tầng (`07`, CLAUDE §2–3, handover)

| # | Yêu cầu | Bằng chứng | KQ |
|---|---|---|---|
| I1 | Celery `acks_late`, `result_expires=3600`, time limit, beat 1 instance | `acks_late=True`, `reject_on_worker_lost=True`, `3600`, `300/240`, 1 container beat (`replicas: 1`) | MATCH |
| I2 | Timezone job Asia/Ho_Chi_Minh | `celery_app.conf.timezone` | MATCH |
| I3 | Compose full stack | 10 service: postgres, redis, minio, ollama, clamav, mailpit, api, celery-worker, celery-beat, web | MATCH |
| I4 | File IDP bền qua recreate | `./var/idp-storage` bind-mount vào api/worker/beat | MATCH |
| I5 | OCR thật offline (R-DEC-146) | image hiện tại có `/home/aureon/.paddleocr` (det/en, rec/latin, cls — 16 MB) | MATCH (image hiện tại) |
| I6 | `.env` đọc giống nhau ở shell/dotenv/Compose | hash dotenv = hash env trong container | MATCH |
| **U-2** | Object store "MinIO (dev) / S3 (prod)" (CLAUDE §2.2, handover §1) | code chỉ có `LocalObjectStore`; MinIO chạy trong Compose nhưng **không được dùng** | **UNDOCUMENTED** (lệch mô tả) |
| **U-3** | Test không để lại rác | 25 file trong `var/idp-storage` (đều ngày 02/11) nhưng DB chỉ tham chiếu 1 → test integration ghi file vào thư mục dev dùng chung, DB rollback còn file thì không. Job sweep sẽ **báo cáo** 24 file mồ côi từ 09/11 (không xóa) | **UNDOCUMENTED** |
| **X-4** | Model OCR chắc chắn có trong image | `Dockerfile` bake model (dòng 42–44) **sau** `COPY apps/api` (dòng 29) → mọi đổi source phải tải lại model; tải lỗi → `|| echo "skipping"` → **build vẫn xanh nhưng không có model** | **MISMATCH** với R-DEC-146 "OCR chạy offline" (rủi ro build, không phải lỗi hiện tại) |

### 4.5. Frontend (`06`)

| # | Yêu cầu | Bằng chứng | KQ |
|---|---|---|---|
| F1 | i18n VI/EN đủ cặp | 1909 / 1909 key, lệch 0 | MATCH |
| F2 | Màn hình P0 có route | SCR-18a `/data/review`, SCR-47 `/business/finance/invoices`, SCR-48 `/business/hr/employees`… đều có `page.tsx` | MATCH |
| F3 | WCAG AA (axe) | `e2e/a11y-axe.spec.ts` 6/6 trên code | MATCH (code) |
| **U-4** | Dùng ID registry v3 | code còn gắn ID cũ của `main`: `SCR-02`, `SCR-12`, `SCR-28`, `SCR-0x` (06 dòng 383 nói `main` có SCR-01..28); không ảnh hưởng chạy | **UNDOCUMENTED** |

### 4.6. Tài liệu nội bộ mâu thuẫn nhau (không phải code)

| # | Chỗ | Mâu thuẫn | KQ |
|---|---|---|---|
| G-1 | CLAUDE §5.5 | "chỉ thêm `TOOL-*` có trong **bảng 10 §7**" — bảng thật ở `10` §2.3 | MISMATCH (doc↔doc) |
| G-2 | CLAUDE §2.2 | RAG "LlamaIndex + pgvector" — R-DEC-141/DEC-150 chốt **không** dùng LlamaIndex | MISMATCH (doc↔doc) |
| G-3 | CLAUDE §2.2, §1.6, §5.9 | "11/10 schema" lẫn lộn; trạng thái 2026-10-23 ("kế tiếp phân rã build v3") đã cũ; số đếm registry 79 ENT / 43 TOOL / 28 EVT / 32 METRIC / 31 SCR ≠ thực tế (54 TOOL, 40 EVT, 34 METRIC, 35 SCR ở 06) | MISMATCH (doc↔doc) |
| G-4 | CLAUDE §4.2, §6.5 | khóa ở `secrets/`; R-DEC-81 + Compose dùng `./keys` | MISMATCH (doc↔doc) |

> Các mục G-* nằm trong `CLAUDE.md` — CLAUDE §6.6 rule 10 **cấm agent tự sửa**, cần human.

### 4.7. UNVERIFIED

| # | Mục | Lý do |
|---|---|---|
| V-1 | Version 03/05/09/10/14 | M4 ghi "Change 1.2.0 (đề xuất)" nhưng trường Version giữ nguyên — chờ human promote ở `12` |
| V-2 | R-DEC-147..152 | agent tự chốt theo ủy quyền; human chưa xác nhận |
| V-3 | `scripts/check_env.sh` | thông báo nói "khớp với Compose `env_file`" nhưng script chỉ so bash ↔ dotenv; Compose được xác minh riêng hôm nay bằng hash (I6), script chưa tự kiểm |

## 5. Kiểm tra riêng M4

| Hạng mục | Trong code (HEAD) | Trong stack đang chạy | Bằng chứng |
|---|---|---|---|
| Job `purge_import_rows` | ✅ có, 5 test, cov 93% | ❌ không (`app.jobs.purge_import_rows` không có trong `celery_app.tasks` của worker) | `docker exec aureon-celery-worker-1 …` |
| Job `sweep_orphan_storage` | ✅ có, mặc định chỉ báo cáo | ❌ không | như trên |
| Beat schedule | ✅ **16** entry | ❌ **14** (thiếu `purge-import-rows`, `sweep-orphan-storage`) | `beat_schedule` trong container beat |
| Màu trạng thái AA | ✅ `--success 0.51`, `--warning 0.53`, `--danger 0.54` (+ dark) | ❌ CSS phục vụ: `58%`, `70%`, `56%` | `/_next/static/*.css` |
| Avatar AA (`--primary`) | ✅ `0.50` | ❌ `52%` | như trên |
| Panel ⌘K | ✅ `bg-card` | ❌ bundle còn `border bg-popover shadow-2xl` | `.next/static/chunks/app/(app)/layout-*.js` |
| Image api | — | build 02/11 19:59, lệch **7 file M4**: `core/config.py`, `core/storage.py`, `idp/repositories/__init__.py`, `idp/services/retention_service.py` (thiếu), `worker.py`, `workers/jobs.py`, `scripts/bootstrap_admin.py` | `img_diff.sh` |
| Image web | — | build 02/11 20:34, lệch **2 file M4**: `globals.css`, `CommandPalette.tsx` | `img_diff.sh` |

## 6. Ảnh hưởng & rủi ro khi rebuild/recreate

| Rủi ro | Mức | Chi tiết | Giảm thiểu |
|---|---|---|---|
| R1 Mất model OCR | 🔴 | Đổi source → chạy lại bước bake model (cần mạng). Tải lỗi → image **không có model** mà build vẫn xanh (X-4) | Kiểm mạng trước; sau build chạy `docker run --rm aureon-api:local ls /home/aureon/.paddleocr/whl` và `--network none` OCR thử `data/DOC-10-anh-hoa-don-gtgt.png` |
| R2 Build web cần npm | 🟠 | `pnpm-lock.yaml` đổi (2 devDep) → layer `pnpm install` build lại, cần registry; 2 devDep đi vào image runtime (Dockerfile copy cả `/repo`), không được import ở runtime | Kiểm mạng; chấp nhận tăng size nhỏ |
| R3 `NEXT_PUBLIC_*` bị inline lúc build | 🟠 | `NEXT_PUBLIC_DEMO_MODE`, `NEXT_PUBLIC_DEMO_REFERENCE_DATE` lấy từ `.env` lúc build (hiện `true`, `2026-10-20`) | Đúng cho demo; khi chuyển live phải **build lại** với `false` (bẫy đã ghi ở STATE) |
| R4 Job purge chạy lần đầu | 🟢 | DB demo: `import_batches = 0` → lần chạy 02:00 xóa **0 dòng** | — |
| R5 Job sweep chạy lần đầu | 🟢 | chỉ báo cáo; 25 file đều < 7 ngày → báo 0 đến 09/11, sau đó báo 24 file rác test (U-3), **không xóa** (`IDP_ORPHAN_SWEEP_DELETE=false`) | Dọn rác test trước (§7 P6) |
| R6 Task đang chạy khi recreate worker | 🟢 | `acks_late` + `reject_on_worker_lost` → task được giao lại; job idempotent | Recreate ngoài giờ job (tránh 01:00–02:30, các phút :05/:15) |
| R7 Phiên người dùng | 🟢 | khóa RS256 và `NEXTAUTH_SECRET` không đổi; refresh token trong DB → phiên **giữ được**; chỉ request đang bay bị cắt | — |
| R8 Dữ liệu | 🟢 | không migration; Postgres/Redis/MinIO không recreate; file IDP trong bind-mount | backup `pg_dump` trước (cũ nhất: `var/backup/aureon_predev_20261102_222021.dump`) |
| R9 Đường lùi | 🟢 | image cũ bị ghi đè tag `:local` | `docker tag aureon-api:local aureon-api:pre-m4` và `aureon-web:local aureon-web:pre-m4` **trước** khi build |

## 7. Phương án xử lý sai lệch

Nguyên tắc: không tự đổi requirement/kiến trúc/quyết định kỹ thuật. Sửa chú thích sai **do M4 tạo** là
đính chính; mọi mục còn lại đề xuất phương án + người quyết.

| # | Sai lệch | Phương án đề xuất | Ai quyết | Chặn rebuild? |
|---|---|---|---|---|
| P1 | M-1, M-2, M-3 (lỗi chú thích M4 ở `10` §7.3) | (a) sửa 16 số EP v2.1 theo bảng §7.1; (b) xóa `EP-GOL-01`, giữ `EP-STR-17..21`; (c) EP-HR-07: "mức 4 chỉ CEO + DIR khối O (02 §6.2); role khác bị mask"; (d) parser contract hỗ trợ ID dạng dải `EP-X-NN..MM` + test kiểm cột EP v2.1 so với `summary` route; (e) sửa "69" → "64" trong 13/14/STATE | Agent (đính chính) | Không — nhưng nên làm trước merge |
| P2 | X-1 rate limit AI | Thêm limiter 20 req/phút/người cho EP `/ai/*` theo 07 §145 (Redis đã có, không cần dependency mới) — **cần R-DEC**: phạm vi (chỉ AI hay mọi API), khóa (user/IP), cửa sổ (sliding/fixed) | Human (R-DEC) | Không |
| P3 | X-2 timeout 5 s/tool | `asyncio.wait_for` quanh executor tool, hết giờ → `tool_result` lỗi + log `ToolCallLog` | Human duyệt (đã có trong 07, chỉ thiếu code) | Không |
| P4 | X-3 chat 90 s vs 30 s | Chọn một: (a) đưa `CHAT_TIMEOUT_SECONDS` về 30 theo 07; (b) giữ 90 cho model live + ghi R-DEC và sửa 07 §145 | Human (R-DEC) | Không |
| P5 | X-4 Dockerfile bake model sau COPY src | (a) đưa bước bake model lên **trước** `COPY apps/api` (model chỉ phụ thuộc gói, không phụ thuộc source); (b) bỏ `|| echo` để build **fail** khi tải model lỗi với `UV_EXTRAS=ocr` | Human duyệt (hạ tầng) | **Nên làm trước rebuild** — nếu không, ít nhất kiểm R1 sau build |
| P6 | U-3 rác test trong `var/idp-storage` | test integration đặt `IDP_STORAGE_DIR` = `tmp_path` qua fixture; dọn 24 file hiện có bằng chính `sweep_orphan_storage(delete_files=True)` sau khi backup | Agent | Không |
| P7 | U-1 45 entity chưa có doc | bảng gương `ENT-*` ↔ model (giống §2.3/§4.2) vào `05` + test | Human duyệt phạm vi | Không |
| P8 | U-2 MinIO không dùng | (a) ghi rõ trong 07/handover "dev/demo dùng LocalObjectStore, MinIO dự phòng"; hoặc (b) hiện thực `S3ObjectStore` (dependency mới → R-DEC) | Human | Không |
| P9 | U-4 SCR id cũ | đổi comment/`data-scr` sang ID v3 theo bảng ánh xạ 06 | Agent | Không |
| P10 | G-1..G-4 `CLAUDE.md` | human sửa (agent không được sửa — rule 10) | Human | Không |
| P11 | V-1, V-2 | human promote version ở `12` và xác nhận R-DEC-147..152 | Human | Không |
| P12 | V-3 | `check_env.sh` thêm bước so với `docker compose config` (chỉ so hash) hoặc sửa câu thông báo | Agent | Không |

### 7.1. Số EP v2.1 đúng cho `10` §7.3 (theo chú thích route trong code)

| EP v3 | Ghi trong §7.3 | Đúng (code) | | EP v3 | Ghi | Đúng |
|---|---|---|---|---|---|---|
| EP-PRD-01 dashboard | EP-95 | **EP-90** | | EP-RSK-05 assessments | EP-101 | **EP-102** |
| EP-PRD-02 features | EP-92 | EP-92 | | EP-RSK-06 status | EP-102 | **EP-106** |
| EP-PRD-03 products | EP-90 | **EP-91** | | EP-RSK-07 scenarios | EP-105 | EP-105 |
| EP-PRD-04 metrics | EP-91 | **EP-95** | | EP-HR-06 dashboard | EP-86 | **EP-80** |
| EP-PRD-05 releases | EP-93 | **EP-94** | | EP-HR-07 salary | EP-84 | **EP-83** |
| EP-PRD-06 roadmap | EP-94 | **EP-93** | | EP-HR-08 hiring | EP-85 | **EP-84** |
| EP-RSK-01 dashboard | EP-106 | **EP-100** | | EP-HR-09 approve | EP-87 | **EP-86** |
| EP-RSK-02 mitigations | EP-103 | EP-103 | | EP-HR-10 submit | EP-87 | **EP-85** |
| EP-RSK-03 risks | EP-100 | **EP-101** | | EP-HR-11 workload | EP-83 | **EP-87** |
| EP-RSK-04 accept | EP-104 | EP-104 | | EP-PLT-01/02 | EP-59 | **EP-56** |

EP-EXE-01..03 (EP-49/43/42) và EP-DSH-01..04 (EP-15/16/17/11–12) đúng. EP-GOL-01 → xóa (trùng EP-STR-17..21).

## 8. Thứ tự triển khai đề xuất

| Bước | Việc | Điều kiện qua bước |
|---|---|---|
| 0 | Human duyệt báo cáo này; chọn phương án P4, P5 | — |
| 1 | **P1** đính chính `10` §7.3 + parser dải ID + test cột EP v2.1; P12; P6 (fixture `tmp_path`) | `pnpm contract:validate` xanh; test mới fail trên bản sai, pass trên bản sửa |
| 2 | **P5** (nếu duyệt) sửa thứ tự Dockerfile | `docker build` xanh; build lại lần 2 không tải model (cache) |
| 3 | Backup: `pg_dump` DB `aureon`; `docker tag … :pre-m4` cho api + web | file dump + 2 tag tồn tại |
| 4 | Build `api` + `web` (có mạng) | build xanh; model OCR có trong image (R1); OCR `--network none` đọc được `DOC-10` |
| 5 | Recreate `api`, `celery-worker`, `celery-beat`, `web` (`--force-recreate --no-deps`), **ngoài khung 01:00–02:30** | 4 container healthy; `/health` 200 |
| 6 | Kiểm runtime: worker có 2 task mới; beat **16**; CSS phục vụ `--primary` 50% / `--success` 51%; bundle `bg-card` cho ⌘K; image diff vs HEAD = 0 file | `img_diff.sh` tóm tắt `diff=0 missing=0` cho api + web |
| 7 | Hồi quy trên stack thật: Playwright `real` (T-901 7 bước, `nfr-real`, `a11y-axe` chạy cả `real`), gọi tay `purge_import_rows` + `sweep_orphan_storage` 1 lần (`celery call`) xem audit | E2E real xanh; 2 audit row có counters |
| 8 | Doc-sync: STATE + 14 (TC-M4 "Passed on stack"), human promote version (P11), push nhánh + PR | PR mở, human review/merge (agent không tự merge) |
| 9 | Backlog sau merge (cần R-DEC): P2 rate limit, P3 timeout tool, P4, P7, P8, P9, P10 | theo R-DEC |

Đường lùi bước 5: `docker tag aureon-api:pre-m4 aureon-api:local && docker tag aureon-web:pre-m4 aureon-web:local`
rồi recreate lại 4 container (không có migration nên không cần downgrade DB).

## 9. Trạng thái xử lý (2026-11-03, sau khi human duyệt P1/P4/P5)

| Mục | Trạng thái | Bằng chứng |
|---|---|---|
| P1 (M-1, M-2, M-3) | ✅ xong — sửa 17 số EP (bảng §7.1 đếm EP-PLT-01/02 là 1 dòng), bỏ `EP-GOL-01`, viết lại 13 ghi chú route + EP-HR-07; parser nhận ID dạng dải; `TC-M4-16` | contract 42 xanh; kiểm âm fail đúng |
| P4 (X-3) | ✅ R-DEC-153 — giữ 90 s, ghi ngoại lệ ở `07` §145 | `13`, `07` |
| P5 (X-4) | ✅ Dockerfile sửa; image api build lại, model đủ, OCR offline xanh, bake `CACHED` khi đổi source | `TC-M4-17`, `var/m4/build_api*.log` |
| Bước 3 (backup) | ◑ đã tag `:pre-m4` cho api + web; **chưa** `pg_dump` mới | — |
| Bước 4 (build) | ◑ api xong; **web chưa build** | — |
| Bước 5–7 (recreate + kiểm runtime + E2E real) | ☐ chờ human duyệt | — |

## Version

- Draft 0.1 — 2026-11-03. Báo cáo đối chiếu trước rebuild; không thay đổi code/docs ngoài file này.
