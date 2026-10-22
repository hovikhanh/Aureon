# 00 — Index & Document Map (AI-EOS, nhánh `ai-eos`)

> **Nguồn chuẩn (Canonical):** `_reference/SOURCE-BRD-v1.1.md` + `SOURCE-BRD-v1.1-Bổ sung.md` + `SOURCE-UIUX.md`.
> **Vai trò:** bản đồ điều hướng + trỏ tới **ID registry** (`TRACEABILITY-SKELETON.md`). Đọc file này + 01 đầu mọi session trên nhánh `ai-eos`.
> **Trạng thái:** 🟡 draft (Phase R0). **Ngày:** 2026-10-22 · **Maintainer:** @CyEyes

---

## 1. Nhánh `ai-eos` là gì

Nhánh viết lại tài liệu cho **đúng AI-EOS đầy đủ** (28 domain, 7 role + AI Agent, Autonomy L0–L4, Data Capture C1–C10, Data Foundation, AI Platform orchestrator+agents, Executive Intelligence & Reporting, governance & pháp lý VN). Tách từ `main` @ `e394668` (bản demo-ready v2.1 — giữ nguyên làm baseline). Khác biệt `main` ↔ `ai-eos`: `REBUILD-PLAN.md` §5, `TRACEABILITY-SKELETON.md` §12.

## 2. Thứ tự đọc

1. `REBUILD-PLAN.md` — mục tiêu, delta, lộ trình R0–R3, Q1–Q6.
2. `TRACEABILITY-SKELETON.md` — ID registry xương sống (nguồn ID duy nhất).
3. `01-PROJECT-OVERVIEW.md` — tầm nhìn, BO, nguyên tắc, scope, lộ trình.
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

## 5. Trạng thái nhánh (2026-10-22)

| Mục | Trạng thái |
|---|---|
| Nhánh | `ai-eos` (từ `main` @ `e394668`); `main` giữ nguyên demo-ready v2.1 |
| Bộ 00–14 | ✅ bản AI-EOS đầu tiên đủ 15/15 (R0+R1+R2+R3) + 2 file khung — toàn **draft 0.1.0** |
| Phase kế | Human duyệt Q1–Q6 (13 §1) → `doc-reviewer` → promote `current` |
| Mặc định tạm | Q1–Q6 ở 01 §8 / REBUILD-PLAN §6 / 13 §1 |

## Version
- **Version:** 0.1.0 (draft, Phase R0)
- **Last updated:** 2026-10-22
- **Maintainer:** @CyEyes
- **Change 0.1.0:** Tạo 00-INDEX cho nhánh `ai-eos` — bản đồ 00–14 theo AI-EOS, thứ tự đọc, bảng trỏ ID registry, trạng thái nhánh.
