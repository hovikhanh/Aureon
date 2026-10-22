# Aureon v2.1 — Enterprise OS với IDP + AI Assistant

> **"Digital Chief of Staff"** cho CEO doanh nghiệp Việt Nam: *biết công ty đang đạt mục tiêu
> đến đâu, vì sao, và giao việc được ngay — với dữ liệu nhập vào dễ như gửi một file.*

Aureon hợp nhất **Executive Dashboard F.O.C.U.S**, **Intelligent Document Processing (IDP)** và
**Trợ lý AI có nguồn** trên một Modular Monolith (FastAPI + Next.js). Mọi con số truy ngược được
tới bản ghi và tài liệu gốc. Dữ liệu demo: công ty giả định **TNHH TM&DV ABC** (~150 NV, kỳ Q3/2026).

---

## Quick start

```bash
git clone https://github.com/hovikhanh/Aureon.git && cd Aureon
cp .env.example .env                    # điền giá trị dev (mật khẩu demo, NEXTAUTH_SECRET, ...)
./scripts/generate_keys.sh keys         # cặp khóa RS256 cho JWT (gitignored)
docker compose -f docker-compose.full.yml up -d --build
open http://localhost:3000              # Web · API: http://localhost:4000/health
```

Service `api` tự chạy `alembic upgrade head` + seed (idempotent) khi khởi động. 9 service
(`postgres, redis, minio, ollama, clamav, api, celery-worker, celery-beat, web`) healthy trong
~2 phút (ClamAV lần đầu tải signature lâu hơn). Reset dữ liệu demo: `./scripts/demo_reset.sh`.
Kịch bản trình diễn 5 phút: [docs/DEMO-SCRIPT.md](docs/DEMO-SCRIPT.md).

## Demo accounts

Mật khẩu lấy từ `.env` (`DEMO_<ROLE>_PASSWORD`) — không commit, không đặt vào `NEXT_PUBLIC_*`.
Ở `DEMO_MODE=true` màn hình login có dropdown chọn nhanh tài khoản (mật khẩu điền phía server).

| Email | Vai trò | Thấy gì |
|---|---|---|
| `ceo@abc.demo` | CEO | Cả 5 trụ F.O.C.U.S, 13 alert, AI Chat, phê duyệt |
| `cfo@abc.demo` | CFO | Trụ F + S, Finance drill-down, hóa đơn |
| `sales@abc.demo` | VP_SALES | Trụ C (Customer & Growth) |
| `hr@abc.demo` | HR_MANAGER | Trụ O (Operations & People) |
| `reviewer@abc.demo` | REVIEWER | Hàng chờ review IDP |

Seed còn 5 tài khoản khác (`cpo@`, `risk@`, `manager@`, `employee@`, `admin@abc.demo`) cho đủ 10 vai trò.

## Tính năng

| Khối | Nội dung |
|---|---|
| **Dashboard F.O.C.U.S** | 5 trụ: **F** Finance · **O** Operations & People · **C** Customer & Growth · **U** Product & Innovation · **S** Strategy & Risk. **32 metric** tính sẵn (metric store), **13 alert** mở trong seed demo (11 WARNING + 2 CRITICAL). Layout demo: F🟢 C🟢 U🟡 O🟡 S🔴 |
| **Finance drill-down** | 6 metric với sparkline 12 tháng, lineage 3 cấp: metric → bản ghi → tài liệu gốc |
| **AI Assistant** | Chat SSE, **43 tool** lọc theo quyền người hỏi, citation `[n]` → nguồn, không bịa số (P05), PII filter, Autonomy L0–L3 + undo + kill switch |
| **IDP (Domain 22)** | **5 kênh upload C1–C5**, quét malware (ClamAV), text-layer/OCR, trích xuất + confidence band, validation, review song song → commit qua Action Registry vào Finance |
| **Governance** | RBAC 10 vai trò (`<domain>:<action>`), JWT RS256, audit log append-only, Transactional Outbox + Celery |

## Kiến trúc

```mermaid
flowchart LR
  B[Browser] --> W[Next.js 15 web :3000<br/>NextAuth + BFF /api/backend]
  W --> A[FastAPI :4000<br/>11 module · Modular Monolith]
  A --> P[(PostgreSQL 16 + pgvector<br/>10 schema)]
  A --> R[(Redis)]
  R --> C[Celery worker + beat<br/>outbox relay · jobs]
  C --> P
  A --> G[ModelGateway]
  G --> O[Ollama local<br/>CONFIDENTIAL]
  G --> X[OmniRoute / cloud LLM]
  A --> V[ClamAV malware scan]
  A --> S[(MinIO / object store)]
```

Health: `GET /health` (tổng + dependency), `/health/ready` (DB + Redis), `/health/live`, `/metrics` (Prometheus).

## Phát triển (app chạy trên host)

```bash
pnpm install && uv sync
docker compose up -d postgres redis minio ollama clamav
uv run alembic upgrade head && uv run python -m app.seed
uv run uvicorn app.main:app --reload --port 4000   # API
pnpm dev:web                                        # Web :3000
```

Gate: `pnpm lint && pnpm typecheck && pnpm test && uv run ruff check . && uv run mypy && uv run pytest && pnpm contract:validate`.

Reset dữ liệu demo (không xoá volume/schema): `./scripts/demo_reset.sh -y`.

## Chế độ AI (ModelGateway)

Mọi lời gọi LLM đi qua một điểm duy nhất là `ModelGateway`. Biến `MODEL_GATEWAY_MODE` trong `.env` quyết định nguồn:

| `MODEL_GATEWAY_MODE` | Hành vi | Cần key? |
|---|---|---|
| `fixture` (mặc định dev/CI) | Phát lại kết quả đã ghi sẵn; không có mạng, không gọi AI thật. Thiếu fixture → lỗi rõ ràng. | ❌ Không |
| `live` | Gọi LLM thật qua endpoint tương thích OpenAI tại `OMNIROUTE_BASE_URL`. | ✅ Có |

Chat demo (`DEMO_MODE=true`) phát lại các câu hỏi kịch bản trong ~1,2–1,3 s — **số liệu luôn lấy từ tool thật**, không bịa. Bật AI/chat thật:

```bash
# .env
MODEL_GATEWAY_MODE=live
OMNIROUTE_BASE_URL=<url-gateway>/v1       # vd http://localhost:20128/v1
OMNIROUTE_API_KEY=<key>                   # gửi dạng Authorization: Bearer <key>
CHAT_MODEL_PRIMARY=cc/claude-sonnet-5     # model chat chính (xem DEC-241)
```

Test gọi provider thật chỉ chạy khi cho phép: `RUN_LIVE_TESTS=true uv run pytest -m live`. Không commit key (`.env` đã gitignore).

## Test

| Bộ | Số lượng |
|---|---|
| Backend pytest | **777** (coverage 96%) |
| Frontend Vitest | **18** |
| E2E Playwright | **30** |

## Tài liệu

Spec sống ở `docs/` (00–14); hợp đồng vận hành agent ở `CLAUDE.md`; trạng thái build ở `STATE.md`;
quyết định ở `docs/4.GOVERNANCE/13-DECISION-LOG.md`.

## License

Proprietary — © CyEyes. All rights reserved. Dữ liệu demo hoàn toàn giả định (DEC-136).
