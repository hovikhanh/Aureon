# DEMO-SCRIPT — Aureon v3 (AI-EOS) · Kịch bản demo theo vai trò

> **Trạng thái code:** mốc **M1 (M1.1 → M1.6) DONE** — nền móng dữ liệu + bảo mật + thực thi + Data Capture + AI Platform nền.
> M2 (Trí tuệ) và M3 (Hành động) **chưa build** → xem §8 "Chưa làm — hoàn thành ở phase nào".
> **Doanh nghiệp demo:** Công ty TNHH TM&DV ABC — 7 phòng ban, 154 nhân sự. `DEMO_REFERENCE_DATE=2026-10-20`, kỳ báo cáo mặc định **T9/2026**.
> **Ngày cập nhật:** 2026-10-26 · **Nguồn:** `STATE.md`, `09-BUILD-PLAN-TASKS.md` §6, e2e `apps/web/e2e/*.spec.ts` (real 75/75 — T-652), seed thật trên DB `aureon`.

**Ký hiệu:** 🟢 = đã chạy end-to-end trên stack thật (có E2E `real` hoặc đã kiểm chứng tay) · 🟡 = chạy được nhưng có giới hạn (ghi rõ) · ⛔ = chưa có, thuộc phase sau.

---

## 0. Demo này chứng minh điều gì

| # | Thông điệp | Chặng | Cơ sở |
|---|---|---|---|
| 1 | **Một nền quyền duy nhất** — 7 role, mỗi role chỉ thấy đúng phần của mình, default deny (403 thật) | 1, 4, 7, 8, 9 | RBAC+ABAC server-side, `scope_pillars` |
| 2 | **Nhập dữ liệu dễ như gửi một file** — C1 (form), C3 (tải file), C5 (import Excel) | 3, 5, 6 | D03 Data Capture, M1.5 |
| 3 | **Người vẫn quyết** — trường trọng yếu (tiền, lương, MST) luôn qua người; sửa trường tiền phải ghi lý do | 5, 6 | FR-DC-16, R-DEC-69 |
| 4 | **Ghi dữ liệu có đường về nguồn + hoàn tác** — mọi commit qua Action Registry, lineage tới trang tài liệu, undo 7 ngày | 5, 6 | ACT-*, ENT-DataLineage |
| 5 | **AI dùng quyền của người hỏi, không bịa số** — mọi con số có citation; tool ghi chỉ ra **thẻ chờ xác nhận** (L2) + undo | 1, 8, 9 | P05/P06, Autonomy L0–L2 |
| 6 | **Quản trị AI nhìn thấy được** — Tool Registry 53 tool, agent, autonomy, kill switch, log mọi tool/model call | 9 | SCR-64/65, M1.6 |
| 7 | **Mục tiêu → việc → đo lường nối liền nhau** | 1, 7, 8 | D07–D11, M1.3/M1.4 |

**Chưa demo được ở mốc này:** Daily Briefing, Insight 9 phần, Decision Log, Calendar 2 chiều, họp/transcript, Knowledge/RAG, dashboard 3 cấp cho MGR/EMP, Autonomy L3 (AI tự thực thi). → §8.

---

## 1. Khởi động project trên Docker

### 1.1. Điều kiện trước khi chạy

| Mục | Kiểm tra | Ghi chú |
|---|---|---|
| `.env` tồn tại | `cp .env.example .env` nếu chưa có | **Không commit** `.env` |
| Cờ demo | `DEMO_MODE=true`, `NEXT_PUBLIC_DEMO_MODE=true`, `DEMO_LOGIN_AUTOFILL=true` | Bật dropdown 10 tài khoản + autofill mật khẩu + chat replay |
| Mật khẩu demo | `DEMO_CEO_PASSWORD`, `DEMO_CFO_PASSWORD`, … (10 biến) | Có giá trị thật, không phải `<change-me>` |
| Khóa RS256 | `keys/jwt_private.pem`, `keys/jwt_public.pem` | Sinh: `./scripts/generate_keys.sh` · mount read-only vào container |
| LLM gateway | OmniRoute chạy trên **host** `:20128` | Chỉ cần cho câu hỏi AI **ngoài** 10 câu replay và cho trích xuất tài liệu tải lên |
| `MODEL_GATEWAY_MODE` | `live` (demo) | Test tự động luôn dùng `fixture` |
| `OCR_PROVIDER` | `stub` (mặc định) | ⚠️ Ảnh / PDF scan **không** trích xuất được — xem §3 lưu ý |

### 1.2. Lệnh khởi động

```bash
cd /home/vika/Aureon
docker compose -f docker-compose.full.yml up -d           # 10 service
docker compose -f docker-compose.full.yml ps              # chờ tất cả "healthy"
```

Nếu vừa đổi code → build lại image trước:

```bash
docker compose -f docker-compose.full.yml build api web
docker compose -f docker-compose.full.yml up -d api celery-worker celery-beat web
```

Container `api` tự chạy `alembic upgrade head && python -m app.seed && uvicorn` khi khởi động, nên lần đầu không cần migrate tay.

### 1.3. Kiểm tra sức khỏe (2 phút trước demo)

```bash
curl -s localhost:4000/health        | head -c 120    # {"status":"ok"...}
curl -s localhost:4000/health/ready  | head -c 200    # postgres/redis/minio/... up
curl -s -o /dev/null -w "%{http_code}\n" localhost:3000/login   # 200
```

| Service | Cổng | Dùng để |
|---|---|---|
| **web** (Next.js) | http://localhost:3000 | Toàn bộ demo |
| **api** (FastAPI) | http://localhost:4000 | `/health`, `/docs` |
| **Mailpit** | http://localhost:8025 | Xem e-mail thông báo (chặng 7) |
| MinIO console | http://localhost:9001 | Không dùng trong kịch bản |
| postgres / redis / ollama / clamav | 5432 / 6379 / 11434 / 3310 | Hạ tầng |
| celery-worker / celery-beat | — | Pipeline IDP, job nền, outbox relay (**beat đúng 1 instance**) |

> **Lần khởi động đầu tiên:** `clamav` tải chữ ký virus mất vài phút → `CLAMAV_REQUIRED=false` nên upload vẫn chạy.
> **Sau khi reboot WSL:** port-forward của Docker Desktop có thể đứt → `docker restart <container>` (dữ liệu giữ nguyên).

---

## 2. Dọn dữ liệu cũ trước demo (tránh trùng lặp)

> **Bắt buộc** nếu đã thử tay trước đó. Lý do: hóa đơn mẫu có **số cố định** (`HV-2026-0912`), import DOC-06 tạo **phòng ban + nhân sự cố định** → commit lần hai sẽ trả `DUPLICATE_RESOURCE` / `CONFLICT_STATE`, và Hộp thư dữ liệu sẽ lẫn tài liệu cũ.

```bash
cd /home/vika/Aureon
./scripts/demo_reset.sh -y
```

Script làm 6 việc (**không** xóa volume, **không** `docker compose down -v`):

1. `TRUNCATE` mọi bảng trong 10 schema module (giữ `platform.alembic_version`)
2. Seed lại (`python -m app.seed`, idempotent)
3. Dọn object storage (`var/idp-storage` + bucket MinIO) → **xóa mọi file đã tải lên**
4. Purge hàng đợi Celery + restart worker/beat
5. Tạo lại **1 hóa đơn `NEEDS_REVIEW`** (trích xuất bằng fixture, không gọi LLM)
6. Verify + xuất `seed_snapshot.json`

**Dòng verify phải ra đúng như sau:**

```
✔ departments: 7      ✔ employees: 154      ✔ demo users: 10     ✔ AI actor: 1
✔ metrics: 34         ✔ open alerts: 14     ✔ invoices NEEDS_REVIEW: 1
✔ AI agents: 6        ✔ autonomy policies: 0                     ✔ onboarding: completed
✅ demo reset complete
```

**Sau reset:** mọi phiên đăng nhập cũ không còn hợp lệ → đăng nhập lại ở từng tab.

### 2.1. Sinh lại bộ file mẫu (nếu `data/` trống hoặc đã sửa generator)

```bash
uv run --group demo python scripts/gen_demo_docs.py       # idempotent, byte-identical mỗi lần chạy
ls -la data/
```

### 2.2. Dọn có chọn lọc (không reset toàn bộ)

```bash
# chỉ xóa mềm các hóa đơn E2E còn treo ở NEEDS_REVIEW
set -a; . ./.env; set +a
PYTHONPATH=apps/api/src:apps/api .venv/bin/python apps/web/e2e/support/seed_review_doc.py --cleanup

# hoàn tác dữ liệu E2E của UC-07 onboarding (trả onboarding.state về completed)
PYTHONPATH=apps/api/src:apps/api .venv/bin/python apps/web/e2e/support/onboarding_e2e.py --cleanup
```

> ⚠️ **Môi trường:** shell của máy này có thể kế thừa biến `DATABASE_URL`/`REDIS_URL` ghi đè `.env`. Mọi lệnh Python chạy **trên host** phải nạp `.env` trước: `set -a; . ./.env; set +a`, rồi kiểm `echo $POSTGRES_DB` = `aureon`.
> Trong app, dữ liệu nghiệp vụ **không xóa cứng** (audit log append-only) — đường chính thức để dọn là `demo_reset.sh`.

---

## 3. Bộ file mẫu dùng để test với hệ thống (`data/`)

| File | Doc type | Kênh | Dùng ở chặng | Nội dung / điểm nhấn |
|---|---|---|---|---|
| `DOC-09-hoa-don-gtgt-mau.pdf` | **#1 INVOICE** | C3 | **6** | Hóa đơn `HV-2026-0912`, TechSoft, MST `0305551234`, 250.000.000 + VAT 25.000.000 = **275.000.000 đ**. Đủ 8 trường schema, giữ quy tắc VR-INV-05 (`subtotal + vat = total`). **Có lớp chữ** → trích xuất tốt |
| `DOC-06-danh-sach-nhan-su.xlsx` | **#4 HR_ROSTER** | C5 | **5** | **45 dòng hợp lệ** (ADMIN 10 · FIN 8 · CUS 12 · OPS 10 · HR 5) + **3 dòng lỗi cố ý**: quản lý không tồn tại `NV-999`, ngày sai `15/13/2026`, phòng ban ngoài công ty ("Phòng Marketing"). Cột **Lương** = trường trọng yếu (mức 4) → 45 ô phải xác nhận. Sheet 2 = người đã nghỉ |
| `ABC_DanhSachNhanSu_Onboarding.xlsx` | **#4 HR_ROSTER** | C5 | **9** (UC-07) | **24 dòng hợp lệ** (OB-BGD 2 · OB-KD 8 · OB-VH 7 · OB-TC 4 · OB-NS 3) + **3 dòng lỗi**: quản lý `OB9999`, ngày `31/02/2025`, **e-mail trùng** |
| `DOC-07-kpi-okr-q4-2026.xlsx` | **#2 PLAN_KPI_OKR** | C5 | 9 (tùy chọn) | Kế hoạch KPI/OKR Q4/2026 — bước `goals_import` của wizard (chỉ CEO/DIR) |
| `DOC-07-kpi-okr-q4-2026.docx` | #2 | C3 | tùy chọn | Bản Word của cùng kế hoạch |
| `DOC-08-bao-cao-ket-qua-q3-2026.pdf` | **#3 PERIOD_REPORT** | C3 | tùy chọn | Báo cáo kết quả Q3. 🟡 Phân loại tự động có thể trả `OTHER` → **chọn trước doc type** trong ô "Loại tài liệu" của vùng tải lên |
| `DOC-01-bao-cao-tai-chinh-q3-2026.pdf` | OTHER/#3 | C3 | tùy chọn | Báo cáo tài chính Q3 nhiều trang (P&L) |
| `DOC-02-danh-sach-hoa-don-t9-2026.xlsx` | — | C5 | ⛔ | 47 hóa đơn — doc type #6 (sổ hóa đơn/sao kê) **thuộc M2.2**, chưa import được |
| `DOC-03-bao-cao-sales-t9-2026.pdf`, `DOC-04-hop-dong-mau.pdf` | OTHER | C3 | tùy chọn | Minh họa phân loại + xem tài liệu gốc |
| `DOC-05-bien-ban-hop-giao-ban.docx` | #1 Biên bản họp | C3 | ⛔ | Doc type biên bản họp → task **thuộc M2.3** |
| `DOC-10-anh-hoa-don-gtgt.png` | #1 INVOICE | C4 | 🟡 | Ảnh hóa đơn (cùng nội dung DOC-09). **`OCR_PROVIDER=stub` → không có chữ → không trích xuất được**; chỉ dùng để trình diễn nút "Chụp ảnh"/kênh C4. OCR thật + tiền xử lý ảnh = M2.3 |

**Giới hạn upload (v2, 04 §15.1):** ≤ 50 MB/file · ≤ 300 trang · ≤ 100 file/lượt · **không hỗ trợ ZIP**.

---

## 4. Tài khoản demo (10 tài khoản, 7 role)

Ở màn `/login`, chọn trong dropdown **"Tài khoản demo"** → hệ thống tự điền **cả e-mail và mật khẩu** (mật khẩu giải ở server, không bao giờ có trong HTML) → bấm con mắt để xem → **Đăng nhập**.

| E-mail | Role | Khối / phòng | Mã NV | Mở được những gì |
|---|---|---|---|---|
| `ceo@abc.demo` | **CEO** | toàn DN | NV-0001 | Trang chủ (F/O/C) · drill-down · Mục tiêu · Công việc · Hộp thư dữ liệu · Hỏi AI · Quản trị (AI, users, audit) |
| `cfo@abc.demo` | **DIR** | **F** Tài chính | NV-0088 | Chỉ card **F** + drill-down 6 chỉ số · hóa đơn · duyệt tài liệu · Mục tiêu khối F |
| `sales@abc.demo` | **DIR** | **C** Kinh doanh | NV-0004 | Card **C** (+ F headline) · Mục tiêu khối C (SO-01, KPI-SAL-01) |
| `hr@abc.demo` | **DIR** | **O** Nhân sự | NV-0100 | Card **O** (+ F) · import C5 nhân sự · cơ cấu tổ chức · commit dữ liệu HR |
| `cpo@abc.demo` | **DIR** | **U** Sản phẩm | NV-0108 | 🟡 Khối U **đóng băng P1** → chỉ còn card F headline; dùng để minh họa cô lập khối |
| `manager@abc.demo` | **MGR** | Vận hành & Dịch vụ (SVC) | NV-0041 | Kanban nhóm · Workload · **Phê duyệt** · duyệt tài liệu · Hỏi AI |
| `office@abc.demo` | **MGR** | Hành chính (ADM) | NV-0139 | Tải hóa đơn lên · **commit hóa đơn** (có `finance:write`) |
| `employee@abc.demo` | **EMP** | SVC | NV-0046 | Task của tôi · KR của mình + check-in · nhập tay C1 · Hỏi AI |
| `reviewer@abc.demo` | **REV** | Hành chính (ADM) | NV-0141 | **Hàng chờ review** + duyệt/từ chối tài liệu (không được ghi nghiệp vụ) |
| `admin@abc.demo` | **ADM** | Sản phẩm (PRD) | NV-0112 | Cơ cấu tổ chức · chức danh · người dùng · vai trò · audit · cấu hình capture · **AI Control Center** · Onboarding |
| `ai-agent@abc.demo` | AI | — | — | Service account — **không đăng nhập được bằng mật khẩu** (minh họa ở chặng 9) |

> **Quan trọng để set kỳ vọng:** **chỉ CEO và DIR có trang chủ dashboard**. MGR/EMP/REV/ADM vào `/home` sẽ thấy khung **"Sắp có — M2.1"** (dashboard 3 cấp theo vai trò là việc của M2.1). Đây là trạng thái **đúng theo kế hoạch**, không phải lỗi.

---

## 5. Kịch bản demo theo vai trò

**Lối đi nhanh (~12 phút, 3 vai):** chặng 1 (CEO) → chặng 6 (office@ tải hóa đơn → reviewer@ duyệt → office@ ghi) → chặng 9.3 (ADM: kill switch + Tool Registry).
**Bản đầy đủ (~55 phút, 9 chặng):** theo đúng thứ tự dưới đây — dữ liệu chặng trước là đầu vào chặng sau.

Mở **2 tab** trình duyệt: tab A (vai chính), tab B ẩn danh (vai duyệt/đối chiếu). Đổi vai = đăng xuất ở tab tương ứng.

---

### Chặng 1 — CEO: "biết công ty đang ở đâu, vì sao" 🟢 (~10 phút)

**Đăng nhập:** `ceo@abc.demo`.

| # | Thao tác | Kết quả mong đợi | Câu nói |
|---|---|---|---|
| 1.1 | Vào `/home` | 3 card trụ **F · O · C** + nhãn kỳ **T9/2026** + danh sách **14 cảnh báo** (4 CRITICAL trước) | *"CEO chỉ thấy ngoại lệ thật, không phải 200 con số."* |
| 1.2 | Bấm **Acknowledge** 1 cảnh báo | Cảnh báo chuyển trạng thái, đếm giảm | Mọi mutation đều ghi audit log cùng transaction |
| 1.3 | Bấm liên kết **"Bố cục 5 trụ"** (góc trên) | Trang `/home/pillar/...` có tab 5 trụ — U và S có mặt nhưng **đóng băng P1** | *"U/S đã gỡ khỏi mặc định để MVP tập trung P0."* |
| 1.4 | Mở tab **F** (`/home/pillar/finance`) | 6 thẻ: Doanh thu · Chi phí · Sử dụng ngân sách · Runway · Số dư tiền mặt · Burn rate, mỗi thẻ có mũi tên xu hướng + sparkline 12 kỳ | |
| 1.5 | Bấm vào thẻ **Doanh thu** | Hộp thoại **lineage 3 cấp**: chỉ số → các bản ghi cấu thành → tài liệu gốc | *"Mọi con số đều truy ngược được tới tài liệu gốc."* |
| 1.6 | **Đổi kỳ:** `Tháng này` → `Q3` | URL mang `?period=` và toàn bộ thẻ nạp lại | |
| 1.7 | Vào **Mục tiêu** `/goals` | Cây **Chiến lược → 4 Mục tiêu chiến lược → KPI / OKR / Sáng kiến**; **KPI-SAL-01 ở băng CRITICAL** (UC-03); **đúng 1 KR "có rủi ro"** (UC-04); nhóm "chưa gắn mục tiêu" xếp cuối | *"Chiến lược, KPI và việc nằm trên một cây."* |
| 1.8 | Mở **KPI-SAL-01** (SCR-58) | Đồ thị theo kỳ + lịch sử target (effective-dated) + nút ghi số đo | Ghi 1 số đo → toast + lịch sử cập nhật |
| 1.9 | Mở **Objective của KR có rủi ro** (SCR-59) | Danh sách KR + lý do at-risk + lịch sử check-in có sparkline | |
| 1.10 | Vào **Công việc** → tab **Dự án** | 10 dự án, **1 dự án gắn cờ trễ (10%)**; mở chi tiết → mốc (milestone) | METRIC-OPS-02 |
| 1.11 | Tab **Workload** | Heatmap tuần — **3 người quá tải (12%)** có badge | METRIC-HR-03 |
| 1.12 | Vào **Hỏi AI** `/ask`, hỏi **"Doanh thu Q3?"** | Trả lời **< 1 giây** (demo replay): *"Doanh thu T9/2026 đạt 86,4% kế hoạch [1] … biên lợi nhuận gộp Q3 18,4% [2] … chi phí Q3 thấp hơn ngân sách 8% [3]"* + **3 citation** | *"Số luôn đến từ tool chạy bằng quyền của người hỏi — AI không bịa."* |
| 1.13 | Bấm **[1]**, rồi mở **"AI đang dùng tool"** | Popover nguồn + danh sách tool đã gọi (`TOOL-get_finance_dashboard`) | |
| 1.14 | Hỏi tiếp **"Top 5 khách hàng?"**, **"Pipeline?"** | Cùng dạng trả lời có nguồn | 10 câu replay: xem §7 |
| 1.15 | **Tool ghi → thẻ chờ xác nhận:** hỏi<br>`Tạo task "Gọi lại khách hàng ABC" cho nhân sự NV-0001, hạn 30/11/2026` | Sau ~6 s: **ActionCard** nhãn **"AI soạn"** (L2), trạng thái `proposed`, xem trước `{title, assignee_code, due_date}` | *"Mức tự chủ L2: AI soạn, người bấm xác nhận."* |
| 1.16 | Bấm **Xác nhận** trên thẻ | Thẻ → `executed`, task được tạo, **UndoToast 10 giây** (tạm dừng khi hover) | |
| 1.17 | Bấm **Hoàn tác** trên toast | Thẻ → `undone`, task biến mất khỏi `/work` | *"Mọi hành động AI đều hoàn tác được."* |

> 🟡 **Lưu ý câu hỏi AI:** 10 câu trong kịch bản trả lời tức thì (replay, nhưng **số vẫn lấy từ tool thật**). Câu **ngoài** danh sách đi tới model live qua OmniRoute → **5–13 giây**. Câu tạo task phải có **mã nhân sự** (`NV-xxxx`) và **ngày cụ thể**, nếu không model sẽ hỏi lại thay vì soạn thẻ.

---

### Chặng 2 — DIR Tài chính (cfo@): cô lập khối 🟢 (~4 phút)

**Tab B, đăng nhập:** `cfo@abc.demo`.

| # | Thao tác | Kết quả mong đợi |
|---|---|---|
| 2.1 | `/home` | **Chỉ card F** — không có O, không có C (`scope_pillars={F}`, enforce ở server mỗi request) |
| 2.2 | Drill-down F → lineage | Như 1.4–1.5 |
| 2.3 | `/business/finance/invoices` | Danh sách hóa đơn (lọc theo chiều IN/OUT), 56 hóa đơn seed |
| 2.4 | Thử vào `/admin/ai` | Trang **403** — DIR không bao giờ được quản trị AI (R-DEC-79) |
| 2.5 | (tùy chọn) đăng nhập `cpo@abc.demo` | Khối U đóng băng P1 → chỉ còn F headline; minh họa "quyền hẹp hơn vai trò" |

---

### Chặng 3 — DIR Nhân sự (hr@): nhập 45 nhân sự bằng một file Excel (C5) 🟢 (~8 phút)

**Tab A, đăng nhập:** `hr@abc.demo`.

| # | Thao tác | Kết quả mong đợi |
|---|---|---|
| 3.1 | Vào **Dữ liệu** `/data` | **Hộp thư dữ liệu** (SCR-45): nhóm trạng thái có số đếm (Đang xử lý / Chờ review / Đã ghi / Đã hoàn tác), bộ lọc kênh + loại + "của tôi", vùng kéo-thả |
| 3.2 | Kéo `data/DOC-06-danh-sach-nhan-su.xlsx` vào vùng tải lên → bấm **"Nhập theo bảng"** | Chuyển sang **wizard import** `/data/imports/<id>` (SCR-62) |
| 3.3 | Bước **Loại tài liệu** | Hệ thống **gợi ý "Danh sách nhân sự"** (#4 HR_ROSTER) kèm độ tin cậy |
| 3.4 | Bước **Ánh xạ cột** | Các cột được **AI ánh xạ sẵn** (badge). Thử bỏ ánh xạ cột **"Mã NV"** → hiện cảnh báo "còn cột bắt buộc chưa ánh xạ" và nút Lưu **bị khóa** → gán lại `employee_code` |
| 3.5 | Bước **Xem trước** | **45 dòng hợp lệ · 3 dòng lỗi**; dòng lỗi tô đỏ, chỉ rõ ô sai (quản lý `NV-999` không tồn tại · ngày `15/13/2026` · phòng "Marketing" ngoài công ty) |
| 3.6 | Bấm **"Tải file lỗi"** | Tải về `.xlsx` chỉ chứa 3 dòng lỗi để sửa và nhập lại |
| 3.7 | Bấm **Tiếp** → **Gửi** | Về `/data`, dòng tài liệu ở trạng thái **`NEEDS_REVIEW`**. Lý do định tuyến = `C5_REVIEW` |
| 3.8 | Mở menu **⋯** của dòng đó → **"Xem tài liệu gốc"** | Ngăn bên mở **nhúng file gốc inline** (R-DEC-80, EP-DC-14b). Tài liệu nhập tay (C1) thì không có mục này |

*Câu nói:* "Gửi một file Excel bẩn — hệ thống tự nhận loại, tự ánh xạ cột, tách dòng lỗi ra file riêng, và **không ghi gì vào hệ thống** cho tới khi có người duyệt."

---

### Chặng 4 — Reviewer (reviewer@): người kiểm, không được ghi 🟢 (~7 phút)

**Tab B, đăng nhập:** `reviewer@abc.demo`.

| # | Thao tác | Kết quả mong đợi |
|---|---|---|
| 4.1 | Vào **Dữ liệu → Hàng chờ review** `/data/review` | Danh sách tài liệu chờ: tài liệu import ở chặng 3 + 1 hóa đơn seed |
| 4.2 | Mở tài liệu import (SCR-18b) | Lưới **25 dòng/trang**, **"Còn 45 trường trọng yếu"** (cột Lương = dữ liệu mức 4), 3 **hành động dự kiến** hiện nhãn *không được phép* (REV không có `hr:write`) |
| 4.3 | Xem nút **Duyệt** | Nhãn **"chờ người có quyền ghi"** → REV duyệt nhưng **không commit** |
| 4.4 | Xác nhận các ô Lương rồi bấm **Duyệt** | Tài liệu → `APPROVED`, về hàng chờ. *(45 ô có thể xác nhận nhanh theo dòng; trong demo thường chỉ cần demo 2–3 ô rồi nói rõ nguyên tắc)* |
| 4.5 | Mở hóa đơn seed, bấm **Từ chối** không điền lý do | Hộp thoại chặn: **"Vui lòng nhập lý do"** |
| 4.6 | Thử vào `/goals` hoặc `/work` | Trang **403** — REV chỉ có phạm vi review |

*Câu nói:* "Phân tách nhiệm vụ: người duyệt nội dung **không** phải người ghi vào hệ thống. Trường trọng yếu — tiền, lương, mã số thuế — **luôn** qua người."

---

### Chặng 5 — hr@ ghi dữ liệu + lineage + hoàn tác 7 ngày 🟢 (~6 phút)

**Về tab A (`hr@abc.demo`).**

| # | Thao tác | Kết quả mong đợi |
|---|---|---|
| 5.1 | Mở lại tài liệu ở `/data/review/<id>` | Khối **"Đã duyệt — chờ ghi"** + nút **Ghi vào hệ thống** |
| 5.2 | Bấm **Ghi vào hệ thống** | **UndoToast**; tài liệu → `COMMITTED`. Một transaction duy nhất: bản ghi + audit + lineage + outbox event (`idp.document_committed`) |
| 5.3 | Vào `/admin/org`, mở nhánh **Vận hành (OPS)** | Phòng ban + nhân sự mới xuất hiện trên cây tổ chức |
| 5.4 | Bấm **LineageChip** cạnh một bản ghi | Popover **đường về nguồn**: bản ghi → tài liệu → **đúng trang/sheet** |
| 5.5 | Về `/data` → nhóm **Đã ghi** → **⋯ → Hoàn tác** | Hộp thoại yêu cầu **lý do** (ví dụ "Nhập nhầm file") |
| 5.6 | Xác nhận hoàn tác | Tài liệu → `ROLLED_BACK`; vào lại `/admin/org` thì **nhánh OPS đã biến mất** |

*Câu nói:* "Mỗi lần ghi là một giao dịch có nhật ký, có đường về nguồn, và hoàn tác được trong **7 ngày**."

> 🟡 Nếu muốn giữ dữ liệu import lại để nói tiếp — **bỏ qua 5.5/5.6** và nhớ chạy `demo_reset.sh -y` sau demo (lần import thứ hai cùng file sẽ báo trùng).

---

### Chặng 6 — Vòng hóa đơn đầy đủ: office@ tải lên → reviewer@ duyệt → office@ ghi → cfo@ thấy 🟢 (~8 phút)

Đây là chặng **nên demo nếu chỉ có 12 phút** — nó chạm đủ 5 thông điệp.

| # | Vai | Thao tác | Kết quả mong đợi |
|---|---|---|---|
| 6.1 | `office@abc.demo` | `/data` → chọn **"Loại tài liệu: Hóa đơn GTGT"** → kéo `data/DOC-09-hoa-don-gtgt-mau.pdf` → **Gửi** | Toast "đã gửi"; dòng mới ở nhóm **Đang xử lý** |
| 6.2 | | Chờ **~4 giây**, làm mới | Worker chạy `app.idp.process_document`: phân loại → đọc lớp chữ → trích xuất → kiểm tra → `UPLOADED` → **`NEEDS_REVIEW`** |
| 6.3 | `reviewer@abc.demo` (tab B) | `/data/review` → mở hóa đơn | **2 cột**: tài liệu gốc bên trái, **8 trường** trích xuất bên phải, mỗi trường có **ConfidenceBadge** |
| 6.4 | | Trỏ chuột vào trường **Số hóa đơn** | Dòng tương ứng **sáng lên trên tài liệu gốc** |
| 6.5 | | Xem **4 trường trọng yếu** (MST bên bán + 3 trường tiền) | Viền đỏ + phải **tick xác nhận từng trường**; đếm "còn N trường trọng yếu" về 0 |
| 6.6 | | Sửa **Tiền thuế** rồi bấm Duyệt **không** ghi lý do | Viền đỏ + **"Trường tiền cần ghi lý do sửa"**, chặn duyệt → trả lại giá trị đúng |
| 6.7 | | Sửa 1 trường **không phải tiền** (ví dụ Tên đơn vị bán, confidence MEDIUM) + ghi lý do "OCR thiếu dấu" → **Duyệt** | Toast **"Đã duyệt — chờ người có quyền ghi (finance:write)"** |
| 6.8 | `office@abc.demo` (tab A) | Mở lại `/data/review/<id>` → **Ghi vào hệ thống** | UndoToast; hóa đơn rời hàng chờ |
| 6.9 | | `/business/finance/invoices` | **Hóa đơn `HV-2026-0912` 275.000.000 đ** có trong danh sách (chiều IN, mới nhất) |
| 6.10 | `cfo@abc.demo` | `/home` → drill-down F → lineage **Chi phí** | Lineage chạm tới **đúng tài liệu nguồn vừa ghi** |

> 🟡 **Trường hợp dùng ảnh (`DOC-10`):** `OCR_PROVIDER=stub` → không có chữ → các trường trả `null`, confidence thấp, tài liệu vào hàng chờ với trường rỗng. Chỉ dùng để nói về kênh C4 + nút "Chụp ảnh"; OCR thật là **M2.3**.

---

### Chặng 7 — MGR (manager@): giao việc, phê duyệt, thông báo 🟢 (~7 phút)

**Đăng nhập:** `manager@abc.demo` (phòng Vận hành & Dịch vụ).

| # | Thao tác | Kết quả mong đợi |
|---|---|---|
| 7.1 | `/home` | Khung **"Sắp có — M2.1"** (MGR chưa có dashboard — đúng kế hoạch) |
| 7.2 | `/work` → tab **Nhóm** | **Kanban**: kéo thẻ đổi trạng thái, di chuyển bằng bàn phím; chuyển sai luật → thẻ **tự bật về** cột cũ + thông báo lý do |
| 7.3 | Giao 1 task cho **Ngô Thị Lan (NV-0046)** | Task hiện ở cột To-do; hệ thống tạo **Notification** + **e-mail** trong cùng transaction |
| 7.4 | Mở http://localhost:8025 (Mailpit) | E-mail "task được giao" đã tới (template theo `kind`, có link, không chứa dữ liệu mức 3–4) |
| 7.5 | Tab **Workload** | Heatmap tuần của phòng; người quá tải có badge |
| 7.6 | Tab **Phê duyệt** `/work/approvals` | **1 yêu cầu `task_reassign` đang chờ** (seed) — hiện người đề nghị, task, lý do |
| 7.7 | Bấm **Duyệt** | Task đổi người thực hiện; phát `platform.approval_decided`; người đề nghị nhận thông báo |
| 7.8 | Mở `/data/review` | MGR **cũng** duyệt được tài liệu trong phạm vi phòng (`idp:approve` scope `d`) |

---

### Chặng 8 — EMP (employee@): phạm vi cá nhân + nhập tay C1 🟢 (~6 phút)

**Đăng nhập:** `employee@abc.demo` (Ngô Thị Lan, NV-0046).

| # | Thao tác | Kết quả mong đợi |
|---|---|---|
| 8.1 | `/work` | **Chỉ task của mình**, nhóm theo hạn; bộ lọc ghi vào URL; **không có** tab Nhóm / Workload / Phê duyệt. Thấy task vừa được giao ở 7.3 + chuông thông báo có số |
| 8.2 | `/goals` | **Chỉ KR của mình** ("Giao hàng TB ≤ 1,8 ngày"); các cấp trên hiện **"ngoài phạm vi"** (không bấm được); không có nút tạo mới |
| 8.3 | `/goals/check-ins` | Thẻ **check-in F4**; nhập giá trị + độ tự tin → **"Đã check-in"**. (Ô "AI điền sẵn" là placeholder → M2.4) |
| 8.4 | `/data` → **Nhập tay** → **"Kế hoạch / OKR / KPI"** | Form C1 (SCR-61) sinh từ schema trong DB |
| 8.5 | Điền kỳ `2026-Q4`, mã NV `NV-0046`, tên việc, hạn **`31/13/2026`** (sai cố ý) | Lỗi hiện ngay dưới ô ngày |
| 8.6 | Sửa hạn thành `30/11/2026` → **Gửi** | Tài liệu vào thẳng **`COMMITTED`** (không có trường trọng yếu) + **UndoToast**; hành động `ACT-create_task` → `execution.tasks` |
| 8.7 | `/work` → mở task vừa tạo → **LineageChip** | Task có **đường về nguồn** tới bản nhập tay |
| 8.8 | `/data` → nhóm **Đã ghi** → **Hoàn tác** (lý do "Nhập nhầm") | Task biến mất khỏi `/work` |
| 8.9 | `/ask`: hỏi **"Doanh thu Q3?"** | 🟡 Trả lời **không có số doanh thu** (EMP không có `finance:query`) → chứng minh **AI dùng quyền của người hỏi** |
| 8.10 | Gõ URL `/work/approvals` hoặc `/admin/org` | Trang **403** |

---

### Chặng 9 — ADM (admin@): quản trị nền tảng + quản trị AI 🟢 (~9 phút)

**Đăng nhập:** `admin@abc.demo`.

#### 9.1. Tổ chức & người dùng

| # | Thao tác | Kết quả mong đợi |
|---|---|---|
| 9.1.1 | `/admin` | Các thẻ quản trị (ADM không có dashboard nghiệp vụ) |
| 9.1.2 | `/admin/org` | Cây tổ chức 7 phòng ban / 154 NV. Đổi **`as_of`** về mốc quá khứ → **cơ cấu cũ** hiện ra (effective-dated) |
| 9.1.3 | Tạo 1 phòng ban mới + gán 1 nhân sự | Xuất hiện trên cây; CEO ở tab khác cũng thấy |
| 9.1.4 | `/admin/positions` | Danh mục chức danh |
| 9.1.5 | `/admin/users` → **khóa** 1 user (có lý do) | Refresh token bị thu hồi → user đó **bị đăng xuất ở lần làm mới sau**; mở khóa thì đăng nhập lại được. Không tự khóa chính mình |
| 9.1.6 | `/admin/roles` | Ma trận 7 role × permission (chỉ đọc) |
| 9.1.7 | `/admin/audit` | Audit log append-only; lọc theo khoảng thời gian / loại chủ thể (người vs AI) → **tìm lại đúng hành động vừa làm ở chặng 5/6** |
| 9.1.8 | Thử đăng nhập `ai-agent@abc.demo` | **Bị từ chối** — service account không đăng nhập bằng mật khẩu |

#### 9.2. Cấu hình Data Capture

| # | Thao tác | Kết quả mong đợi |
|---|---|---|
| 9.2.1 | `/data` với vai ADM | **Không có hộp thư** (theo thiết kế R-DEC-76) — chỉ có liên kết sang cấu hình + vùng tải roster |
| 9.2.2 | `/admin/data-capture` (SCR-63) | Danh mục 5 doc type, schema theo phiên bản, rule kiểm tra. Thử sửa schema đã publish → **bị chặn**, phải tạo bản nháp mới rồi publish |

#### 9.3. AI Control Center (SCR-64/65) — điểm nhấn của M1.6

| # | Thao tác | Kết quả mong đợi |
|---|---|---|
| 9.3.1 | `/admin/ai` → tab **Tổng quan** | Trạng thái kill switch · chi phí AI tháng · hàng chờ thẻ hành động |
| 9.3.2 | Tab **Tool Registry** | **53 tool**, 4 loại (READ / WRITE / EXECUTION / APPROVAL), **13 metadata** mỗi tool; lọc theo domain; mở rộng xem schema + ánh xạ tên BRD. Tool `product`/`risk` gắn **`p1_frozen`** → không quảng bá cho model |
| 9.3.3 | Tab **Agent** | 6 agent P0; **L3 bị khóa** (trần MVP = L2) |
| 9.3.4 | Tab **Autonomy** | Chính sách theo tool/agent; mức **L3 bị gạch**, **L4 khóa hoàn toàn** (chỉ mở ở phase 5) |
| 9.3.5 | **Bật kill switch** chế độ **L0** + ghi lý do | **Banner đỏ hiện cho mọi người, mọi phiên**: *"AI chỉ trả lời, không soạn thao tác"* |
| 9.3.6 | Sang tab khác với vai `employee@`, hỏi câu tạo task | Có cảnh báo **"Kill switch đang bật"**, **không** sinh ActionCard |
| 9.3.7 | Quay lại ADM, **tắt kill switch** | Banner mất; vai EMP hỏi lại → ActionCard L2 trở lại |
| 9.3.8 | `/admin/ai/logs` (SCR-65) | Log **tool call** + **model call**: lọc theo `request_id`, mở drawer xem chi tiết, tab chi phí theo provider. **Không lưu prompt thô** — chỉ `prompt_sha256` |

#### 9.4. (Tùy chọn, ~10 phút) UC-07 Onboarding một doanh nghiệp trong 1 ngày

ABC trong seed đã ở trạng thái `onboarding.state = completed`, nên `/admin/onboarding` hiển thị **đã hoàn tất**. Muốn diễn lại toàn bộ wizard 6 bước:

1. ADM gọi `reset` onboarding (trong trang, có xác nhận + lý do) → wizard về bước **Công ty**.
2. Bước **Nhập cơ cấu**: tải `data/ABC_DanhSachNhanSu_Onboarding.xlsx` → **24 dòng hợp lệ / 3 dòng lỗi** (có dòng **e-mail trùng**) → tải file lỗi → Gửi.
3. `reviewer@` duyệt tài liệu đó → ADM bấm **Ghi** → cây tổ chức thật hiện **5 phòng OB-\*** với đúng headcount (OB-BGD 2 · OB-KD 8 · OB-VH 7 · OB-TC 4 · OB-NS 3 = 24 người).
4. Bước **Người dùng**: tạo 3 tài khoản DIR/MGR/EMP từ chính danh sách vừa nhập → đăng nhập thử.
5. Bước **Mục tiêu**: ADM thấy "việc này do CEO/Director làm" → đổi sang `ceo@` tải `DOC-07-kpi-okr-q4-2026.xlsx`.
6. Bấm **Hoàn tất** → event `platform.onboarding_completed` ghi `within_one_day = true` → liên kết "dashboard đầu tiên" → `/home`.

> ⚠️ Chặng này tạo dữ liệu thật (tổ chức, nhân sự, tài khoản). **Chạy `onboarding_e2e.py --cleanup` hoặc `demo_reset.sh -y` sau đó.**
> Giới hạn đã biết: `ACT-create_department` chưa có cột `organization` → phòng ban nhập vào nằm trong tổ chức đầu tiên của tenant.

---

## 6. Số liệu đối chiếu (ground truth sau `demo_reset.sh -y`)

Dùng để kiểm "UI có khớp dữ liệu không" khi bị hỏi.

| Hạng mục | Giá trị |
|---|---|
| Phòng ban / nhân sự / tài khoản demo | **7 / 154 / 10** (+1 actor AI) |
| Chỉ số trong Metric Store | **34** |
| Cảnh báo đang mở | **14** (4 CRITICAL · 10 WARNING) |
| Task / dự án / KPI / Objective / KR | **100 / 10 / 12 / 6 / 15** |
| Hóa đơn (seed) / tài liệu chờ review | **56 / 1** |
| Yêu cầu phê duyệt đang chờ | **1** (`task_reassign`, phòng SVC) |
| Agent AI / chính sách autonomy | **6 / 0** (dùng mặc định) |
| METRIC-FIN-01 Doanh thu so kế hoạch (T9/2026) | **86,4%** |
| METRIC-FIN-05 (T10/2026) | **7,9%** · METRIC-FIN-04 **54,4 ngày** (Q3) |
| METRIC-OPS-01 hoàn thành đúng hạn | **85%** · METRIC-OPS-02 dự án trễ **10%** |
| METRIC-HR-03 quá tải | **12%** (3 người) |
| METRIC-STR-01 Strategy Execution Index | **81,5%** (cổng G2 ≥ 80%) |
| METRIC-DQ-01 Data Quality | **89,2** |
| Tool Registry | **53 tool** · 13 metadata · product/risk `p1_frozen` |
| Test ở mốc M1 | pytest **1213** · Vitest **332** · contract **34** · Playwright real **75/75**, mock **60/60** · coverage BE **96%** |

---

## 7. Xử lý sự cố nhanh

| Triệu chứng | Nguyên nhân thường gặp | Cách xử lý |
|---|---|---|
| Thẻ trụ báo "Không khả dụng" | 1 endpoint domain lỗi (cô lập theo widget, FR-DSH-07) | Bấm **Thử lại**; `curl localhost:4000/health/ready` |
| Dropdown tài khoản demo không điền mật khẩu | Thiếu `DEMO_MODE=true` **và** `DEMO_LOGIN_AUTOFILL=true`, hoặc e-mail ngoài whitelist | Sửa `.env` → `docker compose … up -d web` |
| Hàng chờ review trống | Chưa reset, hoặc đã duyệt hết | `./scripts/demo_reset.sh -y` (tạo lại 1 hóa đơn chờ) |
| Tài liệu tải lên **kẹt ở `UPLOADED`** | Worker không đăng ký task `app.idp.process_document` (image cũ) | `docker compose -f docker-compose.full.yml build api && up -d api celery-worker celery-beat`; kiểm log worker thấy `app.idp.process_document` |
| Commit hóa đơn báo **trùng số** | Đã commit `HV-2026-0912` ở lượt demo trước | `./scripts/demo_reset.sh -y` |
| Import DOC-06 báo xung đột phòng ban/nhân sự | Đã commit lượt trước mà chưa hoàn tác | Hoàn tác tài liệu cũ, hoặc reset |
| Chat AI chờ 9–13 giây | Câu hỏi **ngoài** 10 câu replay → model live | Dùng đúng câu trong kịch bản; hoặc chờ (có WaitHint 10 s / 30 s / 90 s) |
| Chat trả lời "cần mã nhân sự / cần ngày cụ thể" | Prompt thiếu `assignee_code` hoặc hạn | Dùng nguyên văn: `Tạo task "…" cho nhân sự NV-0001, hạn 30/11/2026` |
| Ảnh / PDF scan trích xuất rỗng | `OCR_PROVIDER=stub` | Dùng PDF có lớp chữ (DOC-09/01/03/04/08); OCR thật = M2.3 |
| Tài liệu bị phân loại sai (`OTHER`) | Phân loại tự động theo từ khóa + model | **Chọn trước "Loại tài liệu"** ở vùng tải lên (EP-DC-01) |
| Không có e-mail trong Mailpit | `celery-worker` down, hoặc chưa phát sinh thông báo | `docker compose … ps`; làm lại bước giao task |
| Vào trang nào cũng "Sắp có" | Đang dùng vai MGR/EMP/REV/ADM trên `/home` | Đúng thiết kế — dashboard 3 cấp là **M2.1** |
| 403 bất ngờ | Default deny đang làm việc | Đối chiếu §4; `/data/review` cần `idp:approve` nên **CEO không vào được** (đúng theo ma trận quyền) |

**10 câu hỏi AI trả lời tức thì (replay, số lấy từ tool thật):** "Doanh thu Q3?" · "Cash flow?" · "Top 5 khách hàng?" · "Rủi ro lớn nhất?" · "Turnover?" · "Pipeline?" · "AI đã làm gì hôm nay?" · "Vì sao trụ O vàng?" · "Dự báo Q4?" · "So sánh F và S?"

---

## 8. Tính năng CHƯA làm được — và sẽ hoàn thành ở phase nào

Nguồn: `09-BUILD-PLAN-TASKS.md` §6.8–§6.17 (MVP) và §3 (phase 2–5 sau MVP).

### 8.1. Mốc M2 — Trí tuệ (ngày 31–60)

| Tính năng chưa có | Hiện trạng trong demo | Phase | Task |
|---|---|---|---|
| **Dashboard 3 cấp theo vai trò** (Executive / Department / Employee): dòng tóm tắt 1 câu, 4 ô CEO tự chọn, "Cần anh quyết", "Rủi ro", "AI đã làm", Strategy Execution Index trên trang chủ | MGR/EMP/REV/ADM thấy "Sắp có"; CEO/DIR dùng dashboard 5 trụ tạm của nền v2.1 | **M2.1** | T-701..T-709 |
| Catalog METRIC v3 đầy đủ + ngưỡng là cấu hình + freshness theo `SLA_FRESHNESS_*` | 34 chỉ số, ngưỡng còn cứng theo seed | **M2.1** | T-701/702 |
| `GET /reporting/dashboards/{executive · department · employee}` | Chưa có endpoint | **M2.1** | T-704 |
| **Trang `/business` đầy đủ**: Finance Lite (ngân sách, chi phí, dòng tiền, runway), Sales pipeline kanban, HR list | Chỉ có `/business/finance/invoices` + `/business/hr/employees` | **M2.2** | T-710..T-716 |
| Doc type **#6 báo cáo tài chính / sao kê số dư** → Revenue/Expense/CashBalance (nhập `DOC-02`) | Chưa nhập được | **M2.2** | T-711 |
| Lead / Opportunity (CRM Lite) + event `opportunity.*` | Chưa có | **M2.2** | T-712/713 |
| **Kênh C2 — nhập bằng lời / ngôn ngữ tự nhiên** (STT qua ModelGateway) | Chưa có | **M2.3** | T-717 |
| **Kênh C4 — chụp ảnh đầy đủ** (tiền xử lý ảnh, khử nghiêng, OCR thật) | Nút "Chụp ảnh" có, nhưng `OCR_PROVIDER=stub` → không trích xuất | **M2.3** | T-718 |
| **PWA cài được trên điện thoại**, layout 390 px | Chưa có manifest/service worker | **M2.3** | T-717..T-719 |
| **Họp (`/meetings`)**: transcript/biên bản → action item → task, ENT-MeetingSummary, khớp tên → nhân sự | Trang hiện "Sắp có"; `DOC-05` chưa dùng được | **M2.3** | T-719..T-726 |
| **CEO Assistant đầy đủ**: grounding validator cứng, **Insight 9 phần**, panel **⌘K** toàn app, chuỗi "Tại sao?" | Chat có citation + tool, nhưng chưa có Insight/⌘K/validator cứng | **M2.4** | T-728..T-736 |
| AI điền sẵn check-in (F4) | Chỉ là placeholder trên UI | **M2.4** | T-732 |
| Bộ AI-eval `GR-*` (grounding), routing classification | Có `INJ-*` (anti-injection) ở M1.5 | **M2.4** | T-733 |
| Đo hiệu năng TTFT chat + a11y WCAG AA tự động | Chưa đo | **M2.5** | T-738/739 |

### 8.2. Mốc M3 — Hành động (ngày 61–90)

| Tính năng chưa có | Phase | Task |
|---|---|---|
| **Calendar Google/Outlook 2 chiều** (OAuth theo từng user, đồng bộ 5 phút, xử lý xung đột), `/meetings/calendar`, `/settings/integrations` | **M3.1** | T-801..T-811 |
| Deadline task → sự kiện trên lịch của người thực hiện | **M3.1** | T-807 |
| **Autonomy L3**: AI tự thực thi (tạo task + owner + deadline + lịch + thông báo trong 1 transaction), feed **"AI đã làm"**, **undo 24 giờ** | **M3.2** | T-812..T-818 |
| Approval Matrix với ngưỡng L3 là cấu hình | **M3.2** | T-813 |
| **CEO Daily Briefing** (7 khối, ≤ 1 trang, gửi e-mail, tracking cổng G1) | **M3.3** | T-819..T-826 |
| **Decision Log 30/60/90** + nhắc review + verify kết quả (`/knowledge/decisions`) | **M3.3** | T-821 |
| Báo cáo + export CSV/XLSX; nêu chỉ số stale trong Briefing | **M3.3** | T-822/823 |
| **Evaluation Engine** (bộ test chuẩn, điểm theo phiên bản prompt/model, `/admin/ai/evaluation`) | **M3.4** | T-827 |
| **Knowledge / RAG**: doc type #5 → embedding bge-m3 → pgvector → `TOOL-search_knowledge` có nguồn tới trang (`/knowledge`) | **M3.4** | T-828 |
| UC-04 đầy đủ: KR at-risk → phân tích blocker → can thiệp L3 → follow-up → verify | **M3.4** | T-829/830 |
| Nghiệm thu: kịch bản CEO 7 bước E2E, **trang đo G1–G4**, NFR hiệu năng/bảo mật/a11y/responsive/PWA | **M3.5** | T-901..T-910 |

### 8.3. Sau MVP (phase 2–5 theo BRD §19.2)

| Nhóm | Nội dung | Phase |
|---|---|---|
| **Business Operations** | D15 Finance đầy đủ · D18 Customer/CRM · D19 Partner · D20 Procurement · D21 Contract Lifecycle · kênh **C6–C10** (e-mail, hóa đơn XML, API…) · Workflow Engine nâng cao · AI dự Google Meet · D10 Performance Cycle đầy đủ | **Phase 2** |
| **Product & Technical** | D22 Product · D23 Engineering · Git/CI-CD · product analytics — **gỡ đóng băng trụ U** | **Phase 3** |
| **Governance & Strategy** | D24 Governance & Compliance · D25 Risk Intelligence nâng cao — **gỡ đóng băng trụ S** · scenario planning · Strategy nâng cao | **Phase 4** |
| **Autonomous Enterprise** | Multi-Agent / Enterprise Orchestrator · **mở Autonomy L4** cho tool đã chứng minh độ tin cậy qua Evaluation Engine | **Phase 5** |

### 8.4. Nợ kỹ thuật / giới hạn đã biết ở M1 (không chặn demo)

| Mục | Ảnh hưởng khi demo | Xử lý dự kiến |
|---|---|---|
| `OCR_PROVIDER=stub` (PaddleOCR chưa cài) | Ảnh/PDF scan không trích xuất | M2.3 |
| Phân loại tự động đôi khi trả `OTHER` (vd DOC-08) | Chọn trước doc type | tinh chỉnh ở M2.x |
| Trụ **U (product)** và **S (risk)** đóng băng P1 | Không có card U/S mặc định; tool product/risk không quảng bá cho model | Phase 3 / 4 |
| Dashboard cố định kỳ T9/2026 (có picker tương đối) | Nói rõ "kỳ báo cáo demo" | M2.1 |
| Tiêu đề thông báo còn text thô, chưa có i18n key | E-mail/chuông hiển thị tên task thô | M2.x (nợ #9 của M1.3) |
| `reviewer@` thuộc phòng Hành chính | Người **ghi** hóa đơn trong demo là `office@` | xem lại seed/UX ở M2.x |
| SCR-18b chưa highlight ô nguồn trên trang với lưới C5 | Chỉ highlight ở tài liệu 1 bản ghi (hóa đơn) | M2.x |
| ADM xem incident (EP-DC-37) cần `idp:approve` | ADM không mở được tab sự cố | OQ M3.x |
| `ACT-create_department` không có cột `organization` | Phòng ban nhập vào nằm ở tổ chức đầu tiên của tenant | 10 §7.2.5 |
| Coverage FE chưa đo (thiếu `@vitest/coverage-v8` — cần DEC) | Chỉ ảnh hưởng báo cáo chất lượng | DEC dependency |
| Agent `assistant` của nền v2.1 còn trên dòng cũ | Nhãn i18n `aiAdmin.queue.legacyAgent` | dọn ở M2.x |
| R-DEC-80 (EP-DC-14b phục vụ file gốc) **chờ human cấp số DEC chính thức** | Tính năng đã chạy; chỉ là việc governance | 13-DECISION-LOG |

---

## 9. Phụ lục — lệnh nhanh

```bash
# Khởi động / trạng thái / log
docker compose -f docker-compose.full.yml up -d
docker compose -f docker-compose.full.yml ps
docker compose -f docker-compose.full.yml logs -f celery-worker | grep idp

# Dọn + seed lại toàn bộ dữ liệu demo (không xóa volume)
./scripts/demo_reset.sh -y

# Sinh lại bộ file mẫu trong data/
uv run --group demo python scripts/gen_demo_docs.py

# Đối chiếu số trong DB
docker compose -f docker-compose.full.yml exec -T postgres \
  psql -U aureon -d aureon -c "select status, count(*) from idp.source_documents where deleted_at is null group by 1;"

# Kiểm nhanh API (dùng mật khẩu từ .env, không in ra màn hình)
set -a; . ./.env; set +a
TOK=$(curl -s -X POST localhost:4000/api/v1/auth/login -H 'Content-Type: application/json' \
  -d "{\"email\":\"ceo@abc.demo\",\"password\":\"$DEMO_CEO_PASSWORD\"}" \
  | python3 -c "import sys,json;print(json.load(sys.stdin)['data']['access_token'])")
curl -s localhost:4000/api/v1/finance/dashboard?period=2026-09 -H "Authorization: Bearer $TOK" | head -c 300
```

> ⚠️ Mọi `POST` tạo/commit/hành động và mọi endpoint AI ghi **bắt buộc** header `Idempotency-Key` **dạng UUID** (thiếu hoặc sai định dạng → `400`).

**KHÔNG dùng khi demo:** `docker compose down -v` (xóa volume dữ liệu), `alembic downgrade base`, `app.reset` trên môi trường không phải dev.

---

## 10. Version

- **DEMO-SCRIPT version:** 3.0.0 (viết lại cho Aureon v3 — AI-EOS; bản 2.1 cũ là kịch bản 5 phút của nền v2.1)
- **Áp dụng cho:** code tại mốc **M1 DONE** (M1.1→M1.6) + bản sửa `source view` EP-DC-14/14b (R-DEC-80, 2026-10-26)
- **Cập nhật khi:** đóng mỗi phase M2.x / M3.x (bước R của vòng S→C→F→B→N→R), và ở **T-904** (M3.5) cho bản nghiệm thu MVP
