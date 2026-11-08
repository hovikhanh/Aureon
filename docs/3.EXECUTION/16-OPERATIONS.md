# 16 — Operations: chạy, kiểm tra và reset Aureon demo trên Docker

> **Vai trò:** runbook vận hành stack demo v4. Gộp phần vận hành chung; runbook riêng của IDP giữ ở `docs/handover/IDP_Operations.md`.
> **Trạng thái:** đề xuất (R-DEC-177). Mọi lệnh ở đây đã chạy được trên stack kiểm chứng ngày 2026-11-08.
> **Phạm vi:** DEMO/MVP. Hardening production (mạng, secret, TLS, CI security) thuộc Phase 8, xem `deliverables/v4-demo/10-PRODUCTION-BACKLOG.md`.

## 1. Thành phần

| Service | Image | Cổng host (stack `aureon`) | Vai trò |
|---|---|---|---|
| `web` | `aureon-web:*` | 3000 | Next.js, BFF `/api/backend/*` |
| `api` | `aureon-api:*` | 4000 | FastAPI; khi khởi động chạy `alembic upgrade head` rồi `python -m app.seed` |
| `celery-worker` | như `api` | — | Pipeline IDP, outbox relay, email |
| `celery-beat` | như `api` | — | Lịch; **đúng 1 instance** |
| `postgres` | `pgvector/pgvector:pg16` | 5432 | 10 schema nghiệp vụ + `public` (tàn dư v1, giữ theo R-DEC-189) |
| `redis` | `redis:7-alpine` | 6379 | Broker, kết quả Celery, idempotency |
| `mailpit` | `axllent/mailpit` | 1025, 8025 | Hộp thư dev |
| `ollama` | `ollama/ollama` | 11434 | Model local `qwen2.5:7b-instruct`, `bge-m3` (D-11) |
| `clamav` | `clamav/clamav` | 3310 | Quét file upload |
| `minio` | chainguard | 9000, 9001 | Có trong compose, code chưa dùng (lưu file ở `var/idp-storage`) |

Cổng host đang publish trên mọi interface. Đóng cổng thuộc Phase 8 (R-DEC-191).

## 2. Cấu hình demo v4

Trong `.env` (không commit):

| Biến | Giá trị demo | Ghi chú |
|---|---|---|
| `DEMO_MODE` | `true` | Tài khoản demo, dropdown đăng nhập (R-DEC-28) |
| `BUSINESS_DATE_OVERRIDE` | `2026-10-20` | Ngày nghiệp vụ duy nhất (R-DEC-192); giữ `DEMO_REFERENCE_DATE` cùng giá trị |
| `MODEL_GATEWAY_MODE` | `live` | Gọi model thật |
| `MODEL_PROVIDER_PRIMARY` | `ollama` | D-11: không provider cloud nào nhận INTERNAL |
| `MODEL_PROVIDER_FALLBACKS` | rỗng | |
| `MODEL_PROVIDER_CONFIDENTIAL` | `ollama` | |
| Key provider cloud (`OMNIROUTE_API_KEY`...) | rỗng | Lớp chặn thực sự cho tới khi có chốt egress trong code |
| `AI_DEMO_REPLAY` | `false` | `true` chỉ khi trình diễn kịch bản; câu trả lời có nhãn "Kịch bản demo" |
| `DEMO_*_PASSWORD` | giá trị riêng | **Không** dùng `DEMO_VP_SALES_PASSWORD`, `DEMO_HR_MANAGER_PASSWORD`: config ưu tiên 2 alias này hơn `DEMO_SALES_PASSWORD`, `DEMO_HR_PASSWORD` |

`NEXT_PUBLIC_*` được nhúng lúc build image web: đổi `DEMO_REFERENCE_DATE` hay `NEXT_PUBLIC_DEMO_MODE` cần build lại `web`.

## 3. Khởi chạy

### 3.1. Stack chính `aureon`

```bash
cp .env.example .env                 # điền giá trị dev, theo §2
./scripts/generate_keys.sh keys      # cặp khóa RS256 (R-DEC-81: thư mục keys/)
docker compose -f docker-compose.full.yml up -d --build
curl -s localhost:4000/health        # {"status":"ok", ...}
```

Không bao giờ dùng `down -v` trên stack có dữ liệu demo. Reset dữ liệu: §6.

### 3.2. Stack kiểm chứng từ trạng thái sạch (không đụng stack chính)

Dùng project, volume, network, tag image và secret riêng; AI local. File override: `var/v4-audit/verify/docker-compose.verify.yml` (gitignore).

```bash
V=var/v4-audit/verify
C="docker compose -p aureon-verify --env-file $V/.env.verify -f docker-compose.full.yml -f $V/docker-compose.verify.yml"
$C build api web                    # tag aureon-api:v4demo, aureon-web:v4demo
$C up -d postgres redis mailpit api celery-worker celery-beat web
curl -s http://127.0.0.1:4700/health
python3 -I var/v4-audit/tools/verify_login.py http://127.0.0.1:4700 $V/.env.verify   # 10 dòng "200"
```

Đo ngày 2026-11-08: build `api` + `web` khoảng 4 phút (có cache); từ `up` tới `/health` 200: 38 giây; `/login` 200: 41 giây; migrate sạch tới `0027_external_event_link_c19`; seed tạo 18 bản ghi xác thực.

Sinh `.env.verify` bằng `var/v4-audit/tools/rotate_env.py` (secret ngẫu nhiên, không in). Lưu ý YAML anchor: `api` và worker, beat dùng chung anchor **không** kèm `ports`, nếu không worker sẽ tranh cổng của `api`.

Dừng và xóa (dữ liệu chỉ trong volume của project này): `$C down -v`. **Chỉ** dùng `-v` với project `aureon-verify`.

## 4. Chạy test an toàn

`.env` trỏ DB của stack đang chạy, và pytest đọc `.env`. Luôn chạy trên DB tạm:

```bash
var/v4-audit/tools/iso_env.sh 5            # Postgres + Redis trên tmpfs, cổng 55505/55605, đã migrate + seed
source var/v4-audit/dev/env5.sh
.venv/bin/pytest -q -p no:cacheprovider    # ~14 phút
.venv/bin/pytest -q -m contract
docker rm -f v4dev-pg5 v4dev-redis5
```

E2E thật phải đặt **đủ** các biến đích; 3 spec dùng mặc định `localhost:4000`, `localhost:8025` nếu thiếu:

```bash
E2E_BASE_URL=http://127.0.0.1:3700 E2E_API_URL=http://127.0.0.1:4700/api/v1 \
E2E_MAILPIT_URL=http://127.0.0.1:58700 E2E_NO_SERVER=1 E2E_ENV_FILE=$PWD/$V/.env.verify \
DATABASE_URL=<url DB kiểm chứng> REDIS_URL=redis://127.0.0.1:56700/0 \
pnpm --dir apps/web exec playwright test --project=real
```

## 5. Kiểm tra sau khởi chạy

| # | Kiểm tra | Kỳ vọng |
|---|---|---|
| 1 | `docker compose ... ps` | Mọi service `healthy`; worker `celery inspect ping` → `1 node online` |
| 2 | `verify_login.py` | 10/10 → 200 |
| 3 | `/finance/dashboard` (CFO) và `/dashboard/metrics/METRIC-FIN-01` | Cùng giá trị, trạng thái, kỳ |
| 4 | `/sales/funnel` | Mỗi bậc 0–100%, không âm |
| 5 | Reviewer `GET /finance/invoices` | `403 FORBIDDEN_SCOPE` (D-07) |
| 6 | `/finance/what-if/runway?revenue_change_pct=0&expense_change_pct=0&extra_monthly_cost=0` | Bằng METRIC-FIN-03. Mặc định của endpoint là kịch bản stress −100% doanh thu |
| 7 | Upload hóa đơn PDF có text layer | `NEEDS_REVIEW`, provider `ollama` |

## 6. Reset dữ liệu demo

```bash
./scripts/demo_reset.sh -y     # không xóa volume, không xóa schema
```

Trước khi reset stack có dữ liệu cần giữ: `pg_dump -Fc` vào `var/backup/` (đã gitignore).

## 7. Sự cố thường gặp

| Hiện tượng | Nguyên nhân | Xử lý |
|---|---|---|
| `docker: command not found` trong WSL | Docker Desktop đã dừng | Mở Docker Desktop; stack `aureon` tự chạy lại do `restart: unless-stopped` |
| 2/10 tài khoản demo 401 sau đổi mật khẩu | Còn alias `DEMO_VP_SALES_PASSWORD`, `DEMO_HR_MANAGER_PASSWORD` | Xóa alias, khởi động lại `api` (seed ghi hash mới) |
| `/health` 200 nhưng đăng nhập 500 | Khóa RS256 nạp lười, file khóa thiếu hoặc sai quyền | Kiểm tra `keys/` và mount; luôn thử đăng nhập thật |
| Trích xuất IDP rất chậm | `qwen2.5:7b-instruct` chạy CPU | Xem `deliverables/v4-demo/06-AI-INTEGRATION-REPORT.md`; trình diễn bằng tài liệu đã xử lý trước |
| Phòng ban đã xóa vẫn hiện | Truy vấn lịch sử theo ngày | Đã sửa (TC-V4-08): từ ngày nghiệp vụ hôm nay trở đi, bản ghi đã xóa không hiện |

## 8. Open questions

- OQ-16-01: Có giữ `minio` trong compose khi code chưa dùng (R-DEC-189)?
- OQ-16-02: Cách trình diễn AI khi model local quá chậm: tài liệu xử lý trước, GPU, hay model nhỏ hơn?

## Version

- **Version:** 0.1.0 (đề xuất)
- **Last updated:** 2026-11-08
