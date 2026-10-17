# 00 — INDEX

> File này là **bản đồ tài liệu** cho AI Agent.
> Mục đích: giúp agent biết file nào cần đọc cho task nào, KHÔNG đọc thừa.

---

## 1. Cấu trúc tài liệu

```
docs/
├── 1.CONTEXT/              ← Đọc đầu mọi session
├── 2.PRODUCT/              ← Đọc khi làm feature
├── 3.EXECUTION/            ← Đọc khi code/build
└── 4.GOVERNANCE/           ← Check trước mọi task
```

---

## 2. Bản đồ file

### 1.CONTEXT — Tầng ngữ cảnh

| File | Mục đích | Khi nào load |
|---|---|---|
| `00-INDEX.md` | File này — bản đồ tài liệu | Đầu mọi session |
| `01-PROJECT-OVERVIEW.md` | Tầm nhìn, scope, KPI, personas | Đầu mọi session |

### 2.PRODUCT — Tầng sản phẩm

| File | Mục đích | Khi nào load |
|---|---|---|
| `02-PERSONAS-PERMISSIONS.md` | 5 vai trò + ma trận quyền | Task liên quan auth, role, UI theo vai trò |
| `03-DASHBOARD-SPEC.md` | 4 trụ, 18 metric, 18 alert, drill-down | Task làm dashboard, biểu đồ, cảnh báo |
| `04-IDP-FEATURE-SPEC.md` | Upload → Extract → Review → Output | Task làm IDP, document processing |
| `05-DATA-MODEL.md` | ERD, 12 entity, quan hệ, indexing | Task làm DB, migration, schema |
| `06-UI-UX-SPEC.md` | Màn hình, component, design system, AI patterns | Task làm UI, component, layout |

### 3.EXECUTION — Tầng triển khai

| File | Mục đích | Khi nào load |
|---|---|---|
| `07-TECH-ARCHITECTURE.md` | Stack, cấu trúc thư mục, deployment | Đầu sprint, setup, quyết định kỹ thuật |
| `08-DEMO-DATA-SPEC.md` | Công ty ABC, 7 loại tài liệu mẫu, seed | Task seed data, demo data |
| `09-BUILD-PLAN-TASKS.md` | 4 sprint, ~40 task atomic, DoD | Plan sprint, nhận task |
| `10-API-SPECIFICATION.md` | **Contract nguồn duy nhất** cho API | Mọi task code API hoặc call API |
| `11-AGENT-WORKFLOW.md` | Doc loading matrix, prompt templates, gates | Đầu session, khi bị block |

### 4.GOVERNANCE — Tầng kiểm soát

| File | Mục đích | Khi nào check |
|---|---|---|
| `12-DOC-AUDIT.md` | Trạng thái tài liệu (current/stale/archived) | **Gate A** — trước mọi task |
| `13-DECISION-LOG.md` | Trạng thái quyết định (open/resolved/blocking) | **Gate B** — trước mọi task |
| `14-TEST-TRACEABILITY.md` | Ma trận spec ↔ task ↔ test | **Gate C** — trước mọi task |

---

## 3. Quy ước ID

Mọi reference trong dự án dùng ID chuẩn sau:

| Prefix | Loại | Ví dụ |
|---|---|---|
| `FR-DC-xx` | Functional Requirement (IDP) | FR-DC-07 |
| `US-DC-xxx` | User Story (IDP) | US-DC-003 |
| `UC-xx` | Use Case | UC-07 |
| `METRIC-FIN-xx` | Metric trụ Tài chính | METRIC-FIN-01 |
| `METRIC-CUS-xx` | Metric trụ Khách hàng | METRIC-CUS-03 |
| `METRIC-OPS-xx` | Metric trụ Vận hành | METRIC-OPS-02 |
| `METRIC-HR-xx` | Metric trụ Con người | METRIC-HR-01 |
| `ALERT-xxx` | Alert | ALERT-FIN-01 |
| `ENT-xxx` | Entity | ENT-SourceDocument |
| `SCR-xx` | Screen | SCR-06 |
| `EP-xx` | API Endpoint | EP-01 |
| `T-xxx` | Build Task | T-204 |
| `DEC-xxx` | Decision | DEC-003 |
| `ROLE-xx` | Role | ROLE-01 |

**Quy tắc:** Khi reference ID phải dùng đúng prefix. Không tự tạo ID mới — raise decision.

---

## 4. Doc Loading Matrix (tóm tắt)

Chi tiết đầy đủ ở `11-AGENT-WORKFLOW.md` §3.

| Task type | Bắt buộc load | Từ chối nếu thiếu |
|---|---|---|
| Plan sprint | 00, 01, 09, 13 | 13 |
| Code dashboard | 00, 01, 03, 06, 10 | 03, 10 |
| Code IDP | 00, 01, 04, 05, 10 | 04, 10 |
| Code auth | 00, 01, 02, 10 | 02, 10 |
| Seed data | 00, 01, 08 | 08 |
| Test | 10, 14 | 10, 14 |
| Audit doc | 12 | 12 |
| Review PR | 10, 14 + PR diff | 10, 14 |

---

## 5. 3 Gate bắt buộc

Trước mọi task, check đủ:

- **Gate A** — `12-DOC-AUDIT.md`: mọi file phải `current`
- **Gate B** — `13-DECISION-LOG.md`: không có `open + blocking`
- **Gate C** — `14-TEST-TRACEABILITY.md`: task có test mapping

Fail bất kỳ gate nào → task `BLOCKED`, không code.

Chi tiết ở `CLAUDE.md` § Gotchas.

---

## 6. ⛔ Không load

| Đường dẫn | Lý do |
|---|---|
| `_reference/SOURCE-*.md` | Tài liệu gốc, không dùng cho build |
| Bất kỳ file status `archived` | Đã thay thế |

Nếu cần thông tin không có trong `docs/` → raise vào `13-DECISION-LOG.md`.

---

## 7. Trạng thái hiện tại

| Mục | Trạng thái |
|---|---|
| Documentation | 🟡 Đang viết |
| Sprint hiện tại | S0 — Setup |
| Blocking decisions | Xem `13-DECISION-LOG.md` |
| Doc audit status | Xem `12-DOC-AUDIT.md` |

---

## 8. Version

- **Version:** 1.0.0
- **Last updated:** 2026-10-16
- **Maintainer:** @CyEyes