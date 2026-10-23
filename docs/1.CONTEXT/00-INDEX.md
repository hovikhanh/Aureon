# 00 — Index & Document Map (Aureon v3 — AI-EOS)

> **Nguồn chuẩn (Canonical):** `_reference/SOURCE-BRD-v1.1.md` + `SOURCE-BRD-v1.1-Bổ sung.md` + `SOURCE-UIUX.md`.
> **Vai trò:** bản đồ điều hướng + trỏ tới **ID registry** (`docs/4.GOVERNANCE/TRACEABILITY-SKELETON.md`). Đọc file này + 01 đầu mọi session.
> **Trạng thái:** ✅ current — Aureon v3 (AI-EOS) CHÍNH THỨC. **Ngày:** 2026-10-23 · **Maintainer:** @CyEyes

---

## 1. Aureon v3 — AI-EOS là gì

Bộ tài liệu chính thức cho **AI-EOS đầy đủ** (28 domain, 7 role + AI Agent, Autonomy L0–L4, Data Capture C1–C10, Data Foundation, AI Platform orchestrator+agents, Executive Intelligence & Reporting, governance & pháp lý VN). Tách từ Aureon v2.1 (nay archived ở `docs/_archive/v2.1/`). So sánh delta với baseline v2.1: `docs/4.GOVERNANCE/REBUILD-PLAN.md` §5, `docs/4.GOVERNANCE/TRACEABILITY-SKELETON.md` §12.

## 2. Thứ tự đọc

1. `docs/4.GOVERNANCE/REBUILD-PLAN.md` — mục tiêu, delta, lộ trình R0–R3, Q1–Q6.
2. `docs/4.GOVERNANCE/TRACEABILITY-SKELETON.md` — ID registry xương sống (nguồn ID duy nhất).
3. `docs/1.CONTEXT/01-PROJECT-OVERVIEW.md` — tầm nhìn, BO, nguyên tắc, scope, lộ trình.
4. File 02–14 (viết dần theo phase).

## 3. Bản đồ tài liệu đích (00–14 theo AI-EOS)

| # | File | Phase viết | Nội dung chính |
|---|---|---|---|
| 00 | INDEX | R0 ✅ | Điều hướng + trỏ ID registry |
| 01 | PROJECT-OVERVIEW | R0 ✅ | Tầm nhìn, BO-01..10, P01..P11, 28 domain, 7 role, MVP 90 ngày + 5 phase |
| 02 | PERSONAS-PERMISSIONS | R1 | 7 role + AI Agent, RBAC+ABAC+field-level, RACI, phân loại dữ liệu/model, AI access scope |
| 03 | DASHBOARD-SPEC | R1 | Executive/Dept/Employee dashboard, bộ chỉ số sức khỏe (§12.4), insight 9 phần, Daily Briefing, Management Loop |
| 04 | IDP-FEATURE-SPEC | R1 | D03: C1–C10, pipeline, 14 doc type, FR-DC-01..23, review song song, Extraction Schema, lineage, học từ chỉnh sửa |
| 05 | DATA-MODEL | R2 | Entity BRD §13.2 (13 nhóm), Data Foundation §13.1 (MDM/Metric Store/lineage/freshness/event/effective-dated/export), quan hệ §13.3 |
| 06 | UI-UX-SPEC | R2 | `SOURCE-UIUX.md`: 5 persona, IA theo vai trò, F1–F5, wireframe CEO/Review/Mobile, mẫu AI theo Autonomy, design system, WCAG 2.1 AA |
| 07 | TECH-ARCHITECTURE | R2 | AI Platform §11.1 (13 thành phần), Model Gateway đa provider + on-prem, Agent Runtime, Policy/Approval/Audit/Evaluation Engine, event backbone, NFR §16 |
| 08 | DEMO-DATA-SPEC | R3 | Dữ liệu mẫu phủ tập P0 MVP (mở rộng sau) |
| 09 | BUILD-PLAN-TASKS | R3 | MVP 90 ngày (3 giai đoạn) + 5 phase |
| 10 | API-SPECIFICATION | R2 | Tool Registry §11.2 (danh mục + 13 metadata), READ/WRITE/APPROVAL/EXECUTION, EP theo domain, event |
| 11 | AGENT-WORKFLOW | R3 | Loading matrix 28 domain, gates, EPCC |
| 12 | DOC-AUDIT | R3 | Trạng thái bộ tài liệu AI-EOS |
| 13 | DECISION-LOG | R3 | DEC cho Q1–Q6 + quyết định mở BRD §21.1 |
| 14 | TEST-TRACEABILITY | R3 | Ma trận test theo US/UC/FR BRD |

## 4. ID Registry — trỏ `TRACEABILITY-SKELETON.md`

| Nhóm ID | Dải | Mục skeleton |
|---|---|---|
| Nguyên tắc | P01–P11 | §1 |
| AI-first | AI-R01–AI-R12 | §2 |
| Mục tiêu KD | BO-01–BO-10 | §3 |
| Domain | D01–D28 (5 lớp) | §4 |
| FR | FR-ORG/ADM/DC/WF/NTF/INT/STR/KPI/OKR/PERF/TASK/MTG/CAL/KNW/FIN/HR/SAL/CUS/PRC/CTR/GOV/RSK/AIQ/RPT/DEC/DATA-* | §4, §4.1 |
| Vai trò | ROLE-CEO/DIR/MGR/EMP/REV/ADM/AI | §5 |
| Use case | UC-01–UC-08 | §6 |
| User story | US-<EPIC>-nnn (19 epic A–S, ~110 US) | §7 |
| Kênh nhập | C1–C10 | §8 |
| AI Platform | 13 thành phần, L0–L4, AGT-*, tool metadata, insight 9 phần | §9 |
| Chỉ số sức khỏe | (METRIC-* cấp khi viết 03) | §10 |
| Entity | ENT-<Name> (13 nhóm) | §11 |

**Quy tắc:** mọi spec chỉ dùng ID trong skeleton; thêm ID mới → cập nhật skeleton trước.

## 5. Trạng thái tài liệu (2026-10-23)

| Mục | Trạng thái |
|---|---|
| Dòng sản phẩm | **Aureon v3 — AI-EOS** CHÍNH THỨC; tách từ Aureon v2.1 (nay archived ở `docs/_archive/v2.1/`) |
| Bộ 00–14 | ✅ bản AI-EOS đủ 15/15 (R0+R1+R2+R3) + 2 file khung — tài liệu chính thức v3 |
| Quyết định nền | **Q1–Q6 đã chốt** (13 §1, R-DEC-05..10): P0 MVP first · Modular Monolith · single-tenant + `tenant_id` · 7 role + AI Agent · docs-first · ID theo BRD + ánh xạ v2.1 |
| Phạm vi đợt này | **Docs-first P0** (R-DEC-09) — hoàn thiện 00–14 + governance; code/app/migration ở đợt sau |
| Mở còn lại | B1–B7 (BRD §21.1, CEO) — không blocking docs P0 (13 §3) |

## Version
- **Version:** 1.0.0 (current)
- **Last updated:** 2026-10-23
- **Maintainer:** @CyEyes
- **Change 1.0.0 (promote):** Promote tài liệu AI-EOS lên CHÍNH THỨC Aureon v3; di chuyển vào vị trí docs chuẩn; v2.1 archived (docs/_archive/v2.1/).
- **Change 0.2.0:** Cập nhật trạng thái sau khi human chốt Q1–Q6 (R-DEC-05..10); ghi rõ phạm vi docs-first P0; B1–B7 còn mở (CEO, không blocking).
- **Change 0.1.0:** Tạo 00-INDEX cho nhánh `ai-eos` — bản đồ 00–14 theo AI-EOS, thứ tự đọc, bảng trỏ ID registry, trạng thái nhánh.
