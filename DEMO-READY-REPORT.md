# Aureon Demo — Demo Ready Report (Final)

> **Phase 4 — Polish & Final Demo** · 2026-10-19
> Công ty giả định: **TNHH TM&DV ABC** (phân phối thiết bị văn phòng, 45 nhân sự, ~100 tỷ/năm)

---

## 1. Tổng quan

Aureon Demo MVP đã sẵn sàng trình diễn. Sản phẩm gồm **3 khối** đúng phạm vi MVP:

1. **Dashboard 4 trụ** (Tài chính / Khách hàng / Vận hành / Con người) — 18 metric thật, 12 cảnh báo, drill-down tới tài liệu gốc.
2. **IDP Feature** — upload PDF/Word/Excel/ảnh/camera → AI phân loại → trích xuất (value + confidence + source_location) → Reviewer duyệt → ghi vào metric/entity qua Action Registry.
3. **Role-based access** — 5 vai trò (CEO, CFO, Sales Director, HR Manager, Reviewer) với dashboard và quyền khác nhau.

**Trạng thái tổng:** S1 (nền tảng), S2 (IDP), S3 (Dashboard core) hoàn tất và verify live. Toàn bộ gate FE + BE xanh.

---

## 2. Tính năng đã có (MVP)

### 2.1 Dashboard (S3 core)
| Hạng mục | Trạng thái |
|---|---|
| 18 metric thật, 4 trụ (FIN/CUS/OPS/HR) | ✅ EP-10/EP-11 |
| 12 cảnh báo (4 Critical + 8 Warning, 08 §5.1) | ✅ `alerts_top` ≤5 Critical-first |
| Tóm tắt điều hành AI (read-only, màu AI riêng) | ✅ DEC-072 |
| Chi tiết metric + lineage panel P01 (SCR-09) | ✅ EP-12 |
| Drill-down ≤3 click: metric → record → source | ✅ EP-12 → EP-13 → EP-14/EP-27 |
| Acknowledge / Dismiss cảnh báo (có audit) | ✅ EP-16/EP-17 |
| Phân quyền metric/alert theo vai trò (03 §5.1) | ✅ verify 5 role |

### 2.2 IDP (S2)
| Hạng mục | Trạng thái |
|---|---|
| Upload C1 (nhập tay) / C2 (ngôn ngữ tự nhiên) / C3 (file) / **C4 (camera PWA)** | ✅ EP-20/21/22 |
| Phân loại tài liệu + trích xuất field (value/confidence/source_location) | ✅ pipeline Celery |
| Hàng đợi review, khóa tài liệu, duyệt/sửa/từ chối | ✅ EP-24..26 |
| **Source Viewer (SCR-10)** — ảnh trang + highlight bounding box | ✅ EP-27 |
| Kiểm tra chéo tài liệu, normalizer, table extraction | ✅ |
| Action Registry (ghi entity + lineage, idempotent) | ✅ |
| Kill switch tự chủ (L0–L2), cấu hình AI | ✅ |

### 2.3 Auth & nền tảng (S1)
| Hạng mục | Trạng thái |
|---|---|
| Đăng nhập JWT + rate limit, 5 tài khoản demo | ✅ |
| Chuyển vai trò nhanh (demo) | ✅ |
| `require_role(...)` mọi endpoint; audit mọi mutation | ✅ |
| Envelope `{data,meta}` / `{error}`, response_model | ✅ |
| i18n next-intl (vi/en), không hard-code tiếng Việt | ✅ (test enforce) |
| Design system shadcn/Tailwind, màu AI ≠ primary | ✅ (06 §6.3) |

**Backend:** 35 endpoint theo 10-API-SPECIFICATION. **Frontend:** 10 route App Router.

---

## 3. Chất lượng & kiểm thử

| Gate | Kết quả |
|---|---|
| `pnpm typecheck` | ✅ sạch |
| `pnpm lint` (ESLint + tsc) | ✅ sạch |
| `pnpm test:web` (Vitest + axe) | ✅ **204 pass / 26 files** (ổn định sau fix pool) |
| `pnpm build:web` | ✅ sạch |
| `uv run ruff check` | ✅ sạch |
| `uv run mypy` | ✅ **74 files**, strict |
| `uv run pytest --cov=app` | ✅ **353 pass**, **coverage TOTAL 87%** |

**Coverage module cốt lõi (≥70%):** auth, dashboard (detail.py nâng 45%→81% ở Phase 4), idp extraction/cross_doc/models, core gateway/idempotency/storage… đều ≥70%.
**Dưới 70% (ghi nhận):** `core/health.py` 43% (probe hạ tầng, ngoài phạm vi Gate C), `idp/action_registry.py` 68% (có sẵn, không đổi).

**UI/UX (rà DOM, 3 breakpoint 1440/820/390):** không horizontal overflow trên Dashboard/Detail/Upload; 0 console error; màu AI `#7c3aed` ≠ primary `#1d4ed8`; 18/18 metric card click-through (P01).

---

## 4. Việc còn lại (ngoài phạm vi stop condition)

| Hạng mục | Lý do hoãn |
|---|---|
| **C4 gộp ảnh → 1 tài liệu nhiều trang + auto crop/deskew/blur** | Cần thư viện xử lý ảnh FE+BE → **chờ DEC mới** (user đã quyết tạm hoãn). Hiện mỗi ảnh C4 upload thành 1 tài liệu đúng contract. |
| Metric/Alert engine tính từ `business_records` (T-302..305) | Dashboard hiện dùng dữ liệu seed thật (đủ cho demo). |
| UC-07 "Nạp doanh nghiệp" batch (T-311/312) | Ngoài stop condition. |
| Màn hình Audit (T-404) | Placeholder. |

Không có DEC `blocking` nào đang mở chặn demo.

---

## 5. Hướng dẫn chạy demo

### 5.1 Dịch vụ nền
```bash
docker compose up -d postgres redis minio
uv run alembic upgrade head
uv run python -m app.seed      # QUAN TRỌNG: seed SAU khi chạy test suite (test reset DB)
```

### 5.2 Khởi động
```bash
# API (port 4000)
uv run uvicorn app.main:app --port 4000
# Worker IDP
uv run celery -A app.worker worker --loglevel=info
# Web (port 3000)
pnpm dev:web
```
Mở **http://127.0.0.1:3000** (web proxy `/api/v1/*` → :4000).

### 5.3 Tài khoản demo
| Vai trò | Email | Mật khẩu |
|---|---|---|
| CEO (ROLE-01) | ceo@abc.demo | `Demo-mi-GsAKV9PaC` |
| CFO (ROLE-02) | cfo@abc.demo | `Demo-H2LoFloiNv5T` |
| Sales (ROLE-03) | sales@abc.demo | `Demo-8gtajs092QwK` |
| HR (ROLE-04) | hr@abc.demo | `Demo-VmVpzbsQ9NeA` |
| Reviewer (ROLE-05) | reviewer@abc.demo | `Demo-WixV_XvcOLZ7` |

### 5.4 Kịch bản trình diễn gợi ý
1. **CEO** đăng nhập → Dashboard 4 trụ, 18 metric, tóm tắt AI, 5 cảnh báo nổi bật.
2. Click **METRIC-FIN-01** → chi tiết + lineage (công thức, nguồn, xu hướng) → click bản ghi → Source Viewer highlight ô số trên ảnh gốc (drill-down P01 ≤3 click).
3. **Upload** → tab C3 kéo-thả file, hoặc tab **C4** mở camera (mobile) chụp trang.
4. **Reviewer** duyệt tài liệu trong hàng đợi; HR mở được tài liệu lương, vai trò khác bị chặn (DS4).
5. Đổi vai trò (CFO/Sales/HR) → thấy dashboard thu hẹp theo quyền; Reviewer không có dashboard.

---

## 6. Phân quyền (verify live)

| Role | Pillars | Metrics | Alerts |
|---|---|---|---|
| CEO | 4 | 18 | 12 |
| CFO | 4 | 18 (CUS+HR = AGG) | 9 |
| Sales | 3 (no HR) | 10 | 3 |
| HR | 3 (no CUS) | 8 | 0 (HR đều Xanh) |
| Reviewer | — | `FORBIDDEN_ROLE` | — |

---

*Báo cáo do AI Agent sinh theo hợp đồng `CLAUDE.md`. Nguồn contract: `docs/3.EXECUTION/10-API-SPECIFICATION.md`. Truy vết test: `docs/4.GOVERNANCE/14-TEST-TRACEABILITY.md`.*
