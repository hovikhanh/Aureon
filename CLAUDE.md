# CLAUDE.md — Aureon

> File này là **hợp đồng vận hành** giữa AI Agent và dự án.
> Đọc file này TRƯỚC mọi task. Vi phạm = task bị từ chối.

---

# Project

**Aureon Demo** — Dashboard CEO + tính năng IDP (Intelligent Document Processing).

Sản phẩm demo gồm 3 khối:
1. **Dashboard 4 trụ** (Tài chính, Khách hàng, Vận hành, Con người) với biểu đồ + cảnh báo, drill-down đến tài liệu gốc.
2. **IDP Feature** — upload PDF/Word/Excel/ảnh → AI phân loại, trích xuất, kiểm tra → Reviewer duyệt → ghi vào metric/entity.
3. **Role-based access** — 5 vai trò (CEO, CFO, Sales Director, HR Manager, Reviewer) với dashboard và quyền khác nhau.

**Phạm vi MVP:** 4 trụ + IDP + 5 vai trò + 7 loại tài liệu mẫu. Xem `@docs/1.CONTEXT/01-PROJECT-OVERVIEW.md`.

**Ngoài phạm vi:** 21 domain còn lại của Aureon, mobile native, integration thật (MISA/Zalo/email), multi-tenant, billing. Không tự ý build.

**Doanh nghiệp giả định cho demo:** Công ty TNHH TM&DV ABC (phân phối thiết bị văn phòng, 45 nhân sự, ~100 tỷ/năm). Chi tiết ở `@docs/3.EXECUTION/08-DEMO-DATA-SPEC.md`.

---

# Tech Stack

## Khung vận hành

| Thành phần | Vai trò | Ghi chú |
|---|---|---|
| **DeepSeek Harness** | Orchestration layer | Chạy nền, gate tasks, quản lý state |
| **OmniRoute** | Model gateway | Route request đến Claude/Free models(auto) |
| **VS Code** | IDE | Terminal, extension, agent chạy trong workspace |
| **Claude (Sonnet/Opus)** | Plan, review, refactor, kiến trúc, Code generation | Model chính cho reasoning và implementation |
| **Free models** | Test, docs, task nhỏ | Qua OmniRoute, dùng khi task đơn giản |

## Stack kỹ thuật

| Layer | Công nghệ | Version |
|---|---|---|
| Frontend | Next.js / React | 14+ / 18+ |
| UI | shadcn/ui + Radix + Tailwind | latest |
| Backend | FastAPI (Python) | 3.12+ |
| Package manager (BE) | uv | latest |
| Test (BE) | pytest + pytest-asyncio | latest |
| Lint/Format (BE) | ruff | latest |
| Type check (BE) | mypy | latest |
| DB | PostgreSQL | 16+ |
| Vector | pgvector | 0.7+ |
| ORM | SQLAlchemy | 2.0+ |
| Queue | Celery + Redis | latest |
| Storage | MinIO (dev) / S3 (prod) | latest |
| Auth | NextAuth + JWT | latest |
| OCR | PaddleOCR (self-host) hoặc Google Vision | latest |
| LLM Gateway | OmniRoute | latest |
| LLM Providers | OpenAI / DeepSeek / Claude / Gemini | latest |
| RAG Framework | LlamaIndex | latest |
| Container | Docker Compose | 24+ |

**Nguyên tắc:** Không đổi stack nếu không có quyết định mới trong `@docs/4.GOVERNANCE/13-DECISION-LOG.md`. Mọi đề xuất đổi stack → raise decision, không tự đổi.

---

# Commands

Chạy từ **root repo**. Mọi lệnh phải exit code 0 trước khi commit.

## Setup (1 lần)
pnpm install                # cài deps frontend
uv sync                     # cài deps backend Python
docker compose up -d postgres redis minio
uv run alembic upgrade head # SỬA từ pnpm db:migrate
pnpm db:seed                # giữ nếu seed làm ở frontend, hoặc uv run python -m app.seed
cp .env.example .env

## Development
pnpm dev                    # Chạy song song
pnpm dev:web                # frontend (port 3000)
uv run uvicorn app.main:app --reload --port 4000 
uv run celery -A app.worker worker --loglevel=info

## Build
pnpm build                  
pnpm build:web              
# BỎ build:api — Python không cần build bước này
pnpm typecheck              # frontend
uv run mypy app/            # type check backend

## Test
pnpm test:web               # Vitest
uv run pytest               # test backend
pnpm test:e2e               # Playwright
uv run pytest --cov=app     # coverage backend

## Lint & Format
pnpm lint                   # ESLint frontend
uv run ruff check .         # lint Python
uv run ruff format .        # format Python

## Database
uv run alembic upgrade head
uv run alembic revision --autogenerate -m "..."
uv run python -m app.seed 
uv run python -m app.reset

---

# Code Style & Conventions

## Ngôn ngữ & naming

| Loại | Convention | Ví dụ |
|---|---|---|
| Folder | kebab-case | `idp-worker`, `metric-detail` |
| File component | PascalCase | `MetricCard.tsx` |
| File non-component | kebab-case | `metric.service.ts` |
| React component | PascalCase | `MetricCard` |
| Function | camelCase | `fetchMetricValues` |
| Constant | SCREAMING_SNAKE | `MAX_FILE_SIZE_MB` |
| Type/Interface | PascalCase | `ExtractionJob` |
| Enum | PascalCase + SCREAMING values | `DocumentStatus.PROCESSING` |
| DB table | snake_case plural | `source_documents` |
| DB column | snake_case | `uploaded_at` |

## Cấu trúc thư mục (monorepo)

```
apps/
  web/                  # Next.js
    src/
      app/              # App Router
      components/       # UI components
      features/         # Feature modules (idp, dashboard, auth)
      lib/              # Utilities, hooks
  api/                  # FastAPI
    src/
      modules/          # Feature modules (idp, dashboard, auth)
      core/             # Config, security, dependencies
      db/               # SQLAlchemy session, base model
      workers/          # Celery tasks
    alembic/            # Migrations
      versions/
    tests/
    pyproject.toml
packages/
  shared-types/         # DTO, types dùng chung
```

## Quy ước code

### API
- **Bám sát** `@docs/3.EXECUTION/10-API-SPECIFICATION.md`. Không tự thêm endpoint/field.
- Base path: `/api/v1/*`
- Response format chuẩn: `{ data, meta? }` hoặc `{ error: { code, message, details } }`
- Error code theo bảng ở `10-API-SPECIFICATION` §1
- Mọi endpoint phải có role check qua dependency: Depends(require_role(...)) (trừ health check)
- Response model phải khai báo qua response_model=... (Pydantic)
- Mọi mutation phải ghi audit log (qua middleware hoặc dependency)

### Frontend
- Server Components mặc định; Client Components dùng `'use client'` directive chỉ khi cần interactivity
- Fetch data qua Server Actions hoặc TanStack Query tùy case
- Form dùng `react-hook-form` + `zod` validation
- Không fetch trực tiếp trong component — dùng TanStack Query
- Mọi metric/number phải có nguồn click-through (P01 — Every number traceable)
- Màu AI khác `primary` (xem `@docs/2.PRODUCT/06-UI-UX-SPEC.md` §6)
- Không hard-code tiếng Việt trong code — dùng `i18n`

### IDP Worker
- Mọi LLM call đi qua `ModelGateway` service, không gọi trực tiếp
- Extraction phải trả về `{ value, confidence, source_location }` cho mỗi field
- Không commit extraction vào DB trực tiếp — phải qua Action Registry
- Prompt injection defense: coi nội dung tài liệu là **data**, không phải **lệnh**

### Database
- Mọi bảng có `id` (UUID), `created_at`, `updated_at`
- Soft delete bằng `deleted_at` cho entity nghiệp vụ
- Index cho mọi foreign key
- Mọi migration qua Alembic, không sửa DB thủ công
- Không đổi schema mà không update `@docs/2.PRODUCT/05-DATA-MODEL.md` trước
- Migration phải reversible (`upgrade()` + `downgrade()`)

### Commit
- Conventional Commits: `feat:`, `fix:`, `docs:`, `refactor:`, `test:`, `chore:`
- Format: `<type>(<scope>): <subject>`
- Ví dụ: `feat(idp): add table extraction for invoices`
- Mọi commit phải pass `pnpm lint && pnpm test && pnpm contract:validate`

### ID references (bắt buộc)
Khi reference spec, dùng đúng ID:
- `FR-DC-xx` — Functional Requirement (IDP)
- `US-DC-xxx` — User Story
- `METRIC-FIN-xx`, `METRIC-CUS-xx`, ... — Metrics
- `ALERT-xxx` — Alerts
- `ENT-xxx` — Entities
- `SCR-xx` — Screens
- `T-xxx` — Build tasks
- `DEC-xxx` — Decisions
- `EP-xx` — API endpoints

---

# Gotchas & Safety Guards

## 🚨 3 GATE BẮT BUỘC trước mọi task

Agent **PHẢI** check đủ 3 gate sau. Fail bất kỳ gate nào → trả về `BLOCKED`, không code.

### Gate A — Document Audit
- Đọc `@docs/4.GOVERNANCE/12-DOC-AUDIT.md`
- Mọi file trong doc loading matrix phải có `status: current`
- File có `last_reviewed` > 14 ngày → cảnh báo
- File `draft`, `stale`, `deprecated`, `archived` → **không được dùng**

### Gate B — Decision Log
- Đọc `@docs/4.GOVERNANCE/13-DECISION-LOG.md`
- Không có decision `open + blocking=true` ảnh hưởng task
- Nếu có → task `BLOCKED`, chờ human resolve

### Gate C — Test Traceability
- Đọc `@docs/4.GOVERNANCE/14-TEST-TRACEABILITY.md`
- Task phải có ≥ 1 test case mapping
- Endpoint/entity liên quan phải có coverage ≥ 70%
- Không có "test gap" blocking

**Sau khi làm task:** update `14-TEST-TRACEABILITY.md` với test mới.

## ⛔ Cấm đọc

| Đường dẫn | Lý do |
|---|---|
| `_reference/` | Tài liệu gốc, không dùng cho build |
| `_reference/SOURCE-*.md` | Có version conflict với spec chính thức |
| Bất kỳ file có status `archived` | Đã thay thế |

Nếu cần thông tin không có trong `docs/` → **raise vào `13-DECISION-LOG.md`**, không tự tra archive.

## ⛔ Cấm tự quyết

Agent **KHÔNG ĐƯỢC** tự:

1. **Thêm/sửa API endpoint** — phải update `10-API-SPECIFICATION.md` trước, hoặc raise `DEC-xxx`
2. **Đổi schema DB** — phải update `05-DATA-MODEL.md` trước
3. **Đổi tech stack** — phải có `DEC-xxx` resolved
4. **Thêm dependency mới** — phải raise decision
5. **Xóa file** trong `docs/` — chỉ con người được xóa
6. **Đổi version** của spec file — chỉ con người
7. **Bỏ qua gate** vì "task đơn giản" — gate là cứng
8. **Comment out code** để "fix tạm" — phải fix thật hoặc raise issue

## ⛔ Cấm lộ credentials

- **KHÔNG** hard-code API key, password, token, connection string vào code
- **KHÔNG** commit file `.env`, `.env.local`, `*.pem`, `*.key`
- **KHÔNG** log credential ra console, kể cả debug
- **KHÔNG** paste credential vào prompt gửi model
- Dùng `.env.example` với placeholder
- Mọi secret qua env var, đọc qua `ConfigService`

**Nếu phát hiện credential bị lộ:** dừng task ngay, raise `DEC-xxx` với mức `blocking`, thông báo human.

## 🪤 Bẫy kỹ thuật thường gặp

### Next.js
- **Bẫy:** fetch trong Server Component cache mặc định → data cũ. Dùng `{ cache: 'no-store' }` cho data real-time.
- **Bẫy:** import Server-only code vào Client Component → lỗi build. Tách rõ `server/` và `client/`.
- **Bẫy:** Server Action không dùng được trong Client Component không có `action` prop. Xác định rõ boundary server/client.

### FastAPI / Pydantic
- Bẫy: response_model không khai báo → leak field nhạy cảm (password_hash). Luôn khai báo rõ.
- Bẫy: dependency injection vòng tròn. Tách `deps.py` riêng.
- Bẫy: file upload lớn không stream → OOM. Dùng `UploadFile` + chunked read.
- Bẫy: Pydantic v1 vs v2 syntax khác nhau. Toàn dự án dùng v2 (`model_config`, `field_validator`).

### SQLAlchemy / Alembic
- Bẫy: session không close → connection leak. Dùng context manager `with SessionLocal() as db:`
- Bẫy: lazy load N+1 query trong loop. Dùng `joinedload()` hoặc `selectinload()`
- Bẫy: Alembic autogenerate bỏ sót thay đổi (index, constraint). Review migration trước khi apply.
- Bẫy: async session dùng sai — không share session giữa các request. Dùng dependency injection.

### Celery
- Bẫy: task không idempotent → retry tạo duplicate. Mọi task phải idempotent (dùng `task_id`).
- Bẫy: task blocking → worker chết. Set `time_limit` và `soft_time_limit`.
- Bẫy: kết quả task không expire → Redis đầy. Set `result_expires`.
- Bẫy: Celery beat chạy 2 instance → duplicate schedule. Chỉ chạy 1 beat.

### LLM calls
- **Bẫy:** prompt injection từ tài liệu (hóa đơn chứa "ignore previous instructions"). **Luôn** wrap document content trong delimiters rõ ràng, coi là data.
- **Bẫy:** token overflow với PDF dài. Chunk tài liệu, extract từng phần.
- **Bẫy:** model hallucinate field không có trong tài liệu. Yêu cầu model trả `null` nếu không tìm thấy, không bịa.

### OCR
- **Bẫy:** PDF scan chất lượng thấp → OCR sai. Luôn trả `confidence` cho mỗi field, field thấp → review.
- **Bẫy:** PDF có lớp text nhưng là scan ảnh → extract rỗng. Kiểm tra `text_layer_exists` trước khi OCR.

### Docker
- **Bẫy:** volume không mount đúng → data mất khi recreate. Kiểm tra `docker-compose.yml` trước `docker compose down`.

## 🛡️ Quy tắc an toàn khi sửa code

1. **Không xóa file** trừ khi task yêu cầu rõ + có `DEC-xxx`
2. **Không sửa file trong `docs/`** — chỉ đọc. Ngoại lệ: `14-TEST-TRACEABILITY.md` (agent được update)
3. **Không force push** lên `main` hoặc `develop`
4. **Không merge** PR của chính mình
5. **Không skip test** bằng `.skip` / `xit` (frontend) hoặc `@pytest.mark.skip` / `pytest.skip()` (backend)
6. **Không disable** ESLint rule (FE) hoặc `# noqa` Ruff (BE) mà không có comment giải thích + `DEC-xxx`
7. **Không commit** file > 10MB (dùng Git LFS nếu cần)

## 📋 Escalation rules

| Tình huống | Hành động |
|---|---|
| Cần đổi API | Raise `DEC-xxx` blocking, chờ human |
| Cần đổi schema | Raise `DEC-xxx` blocking, chờ human |
| Spec mâu thuẫn | Raise `DEC-xxx` blocking + tag human |
| Model fail 3 lần | Raise `DEC-xxx` non-blocking, log lại |
| Chi phí > budget | Raise `DEC-xxx` blocking |
| Phát hiện credential lộ | Dừng task, raise `DEC-xxx` blocking ngay |
| Không hiểu task | Hỏi human, không tự diễn giải |

---

# References

## Bắt buộc đọc đầu session

- `@docs/1.CONTEXT/00-INDEX.md` — Navigation toàn bộ tài liệu
- `@docs/1.CONTEXT/01-PROJECT-OVERVIEW.md` — Tầm nhìn, scope, KPI

## Product specs

- `@docs/2.PRODUCT/02-PERSONAS-PERMISSIONS.md` — 5 vai trò, ma trận quyền
- `@docs/2.PRODUCT/03-DASHBOARD-SPEC.md` — 4 trụ, 18 metric, 18 alert
- `@docs/2.PRODUCT/04-IDP-FEATURE-SPEC.md` — Upload → Extract → Review → Output
- `@docs/2.PRODUCT/05-DATA-MODEL.md` — ERD, 12 entity
- `@docs/2.PRODUCT/06-UI-UX-SPEC.md` — Màn hình, component, design system

## Execution specs

- `@docs/3.EXECUTION/07-TECH-ARCHITECTURE.md` — Stack, deployment, cấu trúc thư mục
- `@docs/3.EXECUTION/08-DEMO-DATA-SPEC.md` — Công ty ABC, 7 loại tài liệu mẫu
- `@docs/3.EXECUTION/09-BUILD-PLAN-TASKS.md` — 4 sprint, ~40 task atomic
- `@docs/3.EXECUTION/10-API-SPECIFICATION.md` — **Contract nguồn duy nhất**
- `@docs/3.EXECUTION/11-AGENT-WORKFLOW.md` — Doc loading matrix, prompt templates

## Governance (check trước mọi task)

- `@docs/4.GOVERNANCE/12-DOC-AUDIT.md` — Trạng thái tài liệu
- `@docs/4.GOVERNANCE/13-DECISION-LOG.md` — Trạng thái quyết định
- `@docs/4.GOVERNANCE/14-TEST-TRACEABILITY.md` — Truy vết test

## Không đọc (xem mục Cấm đọc)

- `@_reference/SOURCE-BRD.md` ⛔
- `@_reference/SOURCE-UIUX.md` ⛔

---

# Doc Loading Matrix

Khi nhận task, load đúng bộ file dưới đây. **Không load thừa** (tốn context).

| Task type | Bắt buộc | Optional | Từ chối nếu thiếu |
|---|---|---|---|
| Plan sprint | 00, 01, 09, 13 | 11, 14 | 13 |
| Code dashboard | 00, 01, 03, 06, 10 | 05, 07 | 03, 10 |
| Code IDP | 00, 01, 04, 05, 10 | 07 | 04, 10 |
| Code auth | 00, 01, 02, 10 | 05 | 02, 10 |
| Seed data | 00, 01, 08 | 05 | 08 |
| Test | 10, 14 | task spec | 10, 14 |
| Audit doc | 12 | — | 12 |
| Review PR | 10, 14, PR diff | 11 | 10, 14 |

---

# Documentation Generation & Governance Rules

## 1. Document Dependency Tree

Tài liệu phải được sinh theo đúng thứ tự phụ thuộc dưới đây; chỉ chuyển sang phase
tiếp theo sau khi phase hiện tại hoàn tất và được verified:

- **Phase 1 — Core Product Specs:** Sinh `02-PERSONAS-PERMISSIONS.md`,
  `03-DASHBOARD-SPEC.md`, `04-IDP-FEATURE-SPEC.md` dựa trên
  `01-PROJECT-OVERVIEW.md`.
- **Phase 2 — Technical & Data:** Sinh `05-DATA-MODEL.md`, `06-UI-UX-SPEC.md`,
  `07-TECH-ARCHITECTURE.md`, `08-DEMO-DATA-SPEC.md`,
  `10-API-SPECIFICATION.md`, `11-AGENT-WORKFLOW.md`.
- **Phase 3 — Governance & Audit:** Sinh `12-DOC-AUDIT.md`,
  `13-DECISION-LOG.md`, `14-TEST-TRACEABILITY.md`.
- **Phase 4 — Task Breakdown:** Chỉ sinh `09-BUILD-PLAN-TASKS.md` sau khi 13 file
  tài liệu trước đó hoàn tất và được verified.

## 2. Verification Gates

- **Gate A — Doc Audit:** Đảm bảo mọi file không ở trạng thái stale và tuân thủ
  định dạng Markdown chuẩn.
- **Gate B — Decision Log:** Mọi quyết định thiết kế lớn phải có rationale rõ ràng
  trong `13-DECISION-LOG.md`.
- **Gate C — Traceability:** Mỗi feature/API spec phải map 1-1 với ít nhất một
  task và một test case trong `14-TEST-TRACEABILITY.md`.

Không được chuyển sang bước tiếp theo nếu gate tương ứng chưa đạt hoặc còn blocking
issue chưa được xử lý.

## 3. Formatting & Style Guidelines

- **Ngôn ngữ:** Tiếng Việt kỹ thuật; giữ nguyên thuật ngữ chuyên ngành tiếng Anh
  như ERD, API, Hook và Spec.
- **Cấu trúc:** Luôn dùng heading rõ ràng; dùng bảng cho ma trận, Data Model và API
  Endpoint.

---

# Version

- **CLAUDE.md version:** 1.1.0
- **Last updated:** 2026-10-17
- **Applies to:** Aureon Demo v1.0
- **Maintainer:** @CyEyes

Mọi thay đổi file này phải qua review. Agent **không tự sửa** `CLAUDE.md`.