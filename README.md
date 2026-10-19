# Aureon

> **Dashboard CEO + Intelligent Document Processing (IDP) cho doanh nghiệp Việt Nam.**
> Từ tài liệu giấy → dữ liệu có cấu trúc → quyết định có nguồn.

---

## Aureon là gì

Aureon là một nền tảng quản trị doanh nghiệp lấy AI làm trung tâm, gồm 3 khối chính:

1. **Dashboard CEO** — 4 trụ sức khỏe doanh nghiệp (Tài chính, Khách hàng, Vận hành, Con người) với biểu đồ, cảnh báo, và khả năng drill-down đến tài liệu gốc.

2. **IDP Feature** — Tính năng trọng tâm: upload PDF/Word/Excel/ảnh → AI phân loại, trích xuất, kiểm tra → Reviewer duyệt → ghi vào metric/entity.

3. **Role-based Access** — 5 vai trò (CEO, CFO, Sales Director, HR Manager, Reviewer) với dashboard và quyền khác nhau.

**Điểm khác biệt:** Mọi con số trên dashboard đều **truy ngược được** đến tài liệu gốc và người nhập.

---

## Trạng thái dự án

| Mục | Trạng thái |
|---|---|
| Giai đoạn | **Demo-ready (MVP)** |
| Sprint hiện tại | **S3/S4 — Dashboard động + IDP hoàn chỉnh, đang polish** |
| Tech stack | **Next.js 15 + FastAPI (Python 3.12)** |
| Thời gian build | 8 tuần (5 mốc sprint S0–S4) |

**Đã có:** Dashboard 4 trụ (18 metric · 12 cảnh báo · drill-down P01) với **dynamic metric/alert engine**, IDP upload C1–C4 + **C4 gộp ảnh → PDF nhiều trang + chấm độ mờ** + Review + Source Viewer, **UC-07 batch onboarding**, **màn hình Audit SCR-14 (EP-52)**, 5 vai trò phân quyền, các endpoint theo `10-API-SPECIFICATION`. Chi tiết ở [`DEMO-READY-REPORT.md`](DEMO-READY-REPORT.md).

**Gate:**
- `pnpm test:web` **218 pass / 29 files** · `pnpm test:e2e` 12 pass (cần env — xem Known Issues) · typecheck/lint sạch.
- `uv run pytest` **366 pass / 1 fail** (coverage **88%**) · mypy/ruff sạch. 1 fail là test live OmniRoute (403) — xem Known Issues.
- **Gate A** (Doc Audit) ĐẠT · **Gate B** (Decision Log) ĐẠT — 0 DEC open+blocking · **Gate C** (Test Traceability) ĐẠT về mapping/coverage, còn **1 test backend fail chờ fix** (live OmniRoute, non-blocking cho demo).

### Known Issues

| # | Vấn đề | Mức | Ghi chú |
|---|---|---|---|
| KI-1 | 1 test backend fail — **HTTP 403 (live OmniRoute)** | Low | `apps/api/tests/model_gateway/test_live_omniroute.py` gọi OmniRoute thật; không ảnh hưởng tính năng demo. Sẽ tách khỏi suite mặc định (marker `live` + `RUN_LIVE_TESTS=true`) để `uv run pytest` mặc định = 366 pass. |
| KI-2 | **E2E chưa reproducible** do thiếu env vars | Low | `pnpm test:e2e` cần `DEMO_*_PASSWORD` + `E2E_BASE_URL`/`API_URL` nạp từ `.env`; hiện phải `set -a; source .env; set +a` thủ công. Sẽ cho Playwright tự nạp `.env` + chuẩn hoá script. |

> Cả hai thuộc Bước 1 (sửa lỗi test/E2E) đã chủ động hoãn; không mục nào chặn demo.

---

## Cấu trúc repo

```
Aureon/
├── CLAUDE.md                   # Hướng dẫn cho AI Agent (BẮT BUỘC đọc)
├── README.md                   # File này
│
├── docs/                       # 14 file spec + 1 index
│   ├── 1.CONTEXT/              # Tầm nhìn, scope
│   ├── 2.PRODUCT/              # Đặc tả sản phẩm
│   ├── 3.EXECUTION/            # Kiến trúc, kế hoạch, workflow
│   └── 4.GOVERNANCE/           # Audit, decisions, test trace
│
├── _reference/                 # Tài liệu gốc (KHÔNG dùng để build)
│
├── apps/                       # Source code
│   ├── web/                    # React frontend
│   └── api/                    # FastAPI backend
│
├── packages/                   # Shared packages
│   └── shared-types/           # DTO, types chung
│
├── data/                       # 7 tài liệu mẫu (DOC-01..07) nằm trực tiếp tại đây
│
└── docker-compose.yml          # PostgreSQL, Redis, MinIO
```

---

## Bắt đầu từ đâu

### Cho người mới

1. Đọc `docs/1.CONTEXT/01-PROJECT-OVERVIEW.md` — hiểu dự án làm gì
2. Đọc `docs/2.PRODUCT/03-DASHBOARD-SPEC.md` — hiểu dashboard
3. Đọc `docs/2.PRODUCT/04-IDP-FEATURE-SPEC.md` — hiểu IDP (tính năng trọng tâm)
4. Đọc `docs/3.EXECUTION/09-BUILD-PLAN-TASKS.md` — xem kế hoạch build

### Cho AI Agent

**BẮT BUỘC** đọc `CLAUDE.md` ở root trước mọi task.

`CLAUDE.md` chứa:
- Tech stack đầy đủ
- Commands (build, test, lint)
- 3 gate bắt buộc phải check
- Quy tắc an toàn, cấm đọc, cấm tự quyết
- Doc loading matrix

### Cho contributor

Trước khi mở PR:
- [ ] Đọc `docs/3.EXECUTION/10-API-SPECIFICATION.md` (nếu đụng API)
- [ ] Check 3 gate ở `docs/4.GOVERNANCE/`
- [ ] Chạy `pnpm lint && pnpm test && pnpm contract:validate`
- [ ] Update `14-TEST-TRACEABILITY.md` với test mới

---

## Quick start (development)

```bash
# 1. Clone + cài dependencies
git clone <repo-url> && cd Aureon
pnpm install
uv sync --all-packages

# 2. Khởi động hạ tầng
docker compose up -d postgres redis minio

# 3. Setup môi trường
cp .env.example .env
# Điền: DATABASE_URL, REDIS_URL, MINIO_*, OMNIROUTE_API_KEY

# 4. Migrate + seed (DEC-062: dùng uv, không dùng pnpm db:*)
uv run alembic upgrade head
uv run python -m app.seed        # chạy LẠI sau mỗi lần pytest (reset-suite drop/recreate DB)

# 5. Chạy dev (3 tiến trình)
uv run uvicorn app.main:app --port 4000               # API
uv run celery -A app.worker worker --loglevel=info    # Worker IDP
pnpm dev:web                                          # Web (3000) → proxy /api/v1/* sang :4000
```

Mở **http://127.0.0.1:3000**. Chi tiết lệnh ở `CLAUDE.md` § Commands.

### Tài khoản demo

| Vai trò | Email | Mật khẩu |
|---|---|---|
| CEO (ROLE-01) | ceo@abc.demo | `Demo-mi-GsAKV9PaC` |
| CFO (ROLE-02) | cfo@abc.demo | `Demo-H2LoFloiNv5T` |
| Sales (ROLE-03) | sales@abc.demo | `Demo-8gtajs092QwK` |
| HR (ROLE-04) | hr@abc.demo | `Demo-VmVpzbsQ9NeA` |
| Reviewer (ROLE-05) | reviewer@abc.demo | `Demo-WixV_XvcOLZ7` |

---

## Tech stack tóm tắt

| Layer | Công nghệ |
|---|---|
| Frontend | Next.js 15 (App Router) + React 18 + TypeScript + Tailwind + shadcn/ui |
| i18n / Chart | next-intl + Recharts (DEC-064) |
| Backend | Python 3.12 + FastAPI + SQLAlchemy 2.0 + Pydantic v2 |
| Auth | PyJWT HS256 (DEC-073) |
| Database | PostgreSQL 16 + pgvector |
| Queue | Redis + Celery |
| Storage | MinIO (dev) / S3 (prod) |
| OCR | PaddleOCR / Google Vision |
| LLM | Claude + GPT qua OmniRoute |

Chi tiết đầy đủ ở `docs/3.EXECUTION/07-TECH-ARCHITECTURE.md`.

---

## Governance

Dự án dùng **3 gate bắt buộc** trước khi giao task cho AI Agent:

| Gate | File | Mục đích |
|---|---|---|
| A — Doc Audit | `docs/4.GOVERNANCE/12-DOC-AUDIT.md` | Chống đọc tài liệu stale |
| B — Decision Log | `docs/4.GOVERNANCE/13-DECISION-LOG.md` | Chống agent tự quyết lại |
| C — Test Traceability | `docs/4.GOVERNANCE/14-TEST-TRACEABILITY.md` | Chống ship code không test |

---

## Nguyên tắc thiết kế

Bốn nguyên tắc không được vi phạm:

1. **Every number traceable** — mọi con số trên UI đều click được để xem nguồn
2. **AI shows state** — AI luôn nói rõ đang gợi ý / soạn / đã làm
3. **Capture once, use everywhere** — dữ liệu chỉ nhập 1 lần
4. **Vietnamese-first** — ngày, số, địa chỉ theo chuẩn Việt Nam

Chi tiết ở `docs/1.CONTEXT/01-PROJECT-OVERVIEW.md` §6.

---

## Không thuộc phạm vi

Demo này **KHÔNG** bao gồm:
- 21 domain khác của hệ sinh thái Aureon đầy đủ
- Mobile native app
- Integration thật (MISA, Zalo, email, ngân hàng)
- Multi-tenant, billing, subscription

Nếu agent thấy yêu cầu nằm ngoài scope → raise decision, không tự build.

---

## Tài liệu gốc

Thư mục `_reference/` chứa tài liệu gốc (BRD v1.1, UI/UX v1.0). **Chỉ dành cho con người đọc.**

**AI Agent KHÔNG được đọc thư mục này.**

---

## Liên hệ

- **Maintainer:** @CyEyes
- **Repo:** (nội bộ)
- **Ngày khởi tạo:** 2026-10-16