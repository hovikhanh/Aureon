# 12 — Document Audit (AI-EOS, nhánh `ai-eos`)

> **Vai trò:** Gate A cho bộ tài liệu AI-EOS. Theo dõi trạng thái 00–14 viết lại.
> **Phụ thuộc:** toàn bộ. **Trạng thái:** 🟡 draft (Phase R3). **Ngày:** 2026-10-23 · **Maintainer:** @CyEyes

---

## 1. Bối cảnh

Bộ tài liệu AI-EOS được viết lại trên nhánh `ai-eos` trong `docs/0.AI-EOS-REBUILD/`, tách khỏi `main` (demo-ready v2.1). Mọi file vẫn ở trạng thái **🟡 draft** — chỉ human promote `current` + bump version (CLAUDE.md §10.3).

Vòng này (**spec-level P0, version 0.3.0**) nâng các file domain P0 từ "outline nén" lên **spec-level đầy đủ**: bổ sung mô tả hành vi per-FR, tiêu chí chấp nhận UC, luồng/trạng thái, quy tắc nghiệp vụ, ngoại lệ, chỉ số và mapping sang `main`. Bám canonical `_reference/SOURCE-BRD-v1.1.md` (+ Bổ sung) + `SOURCE-UIUX.md`; ID chỉ dùng registry trong `TRACEABILITY-SKELETON.md` (R-DEC-10). Tôn trọng R-DEC-09 (docs-first): KHÔNG field-level DB, KHÔNG task `T-*`, KHÔNG `TC-*` chi tiết — hoãn sang đợt code.

## 2. Trạng thái tài liệu (2026-10-23)

Cột **last_reviewed** = ngày rà soát/mở rộng gần nhất. Cột **Gate A** = ✅ đạt (đúng 1 H1, fence cân bằng, có `## N. Open questions` + `## Version`); — = file khung, không áp Gate A spec.

| # | File | Version | Status | Phase | last_reviewed | Gate A | Nguồn BRD |
|---|---|---|---|---|---|---|---|
| — | REBUILD-PLAN | 0.2.0 | 🟡 draft | — | 2026-10-22 | — | §4,§19 |
| — | TRACEABILITY-SKELETON | 0.3.0 | 🟡 draft | — | 2026-10-23 | — | §2,§3,§4,§11,§14,§15 |
| 00 | INDEX | 0.2.0 | 🟡 draft | R0 | 2026-10-22 | ✅ | — |
| 01 | PROJECT-OVERVIEW | 0.3.0 | 🟡 draft | R0 | 2026-10-23 | ✅ | §1,§2,§19,§20 |
| 02 | PERSONAS-PERMISSIONS | 0.3.0 | 🟡 draft | R1 | 2026-10-23 | ✅ | §3,§5.2,§11.6,§17 |
| 03 | DASHBOARD-SPEC | 0.3.0 | 🟡 draft | R1 | 2026-10-23 | ✅ | §11.8,§12 |
| 04 | IDP-FEATURE-SPEC | 0.3.0 | 🟡 draft | R1 | 2026-10-23 | ✅ | §6 |
| 05 | DATA-MODEL | 0.3.0 | 🟡 draft | R2 | 2026-10-23 | ✅ | §13 |
| 06 | UI-UX-SPEC | 0.3.0 | 🟡 draft | R2 | 2026-10-23 | ✅ | UIUX full |
| 07 | TECH-ARCHITECTURE | 0.3.0 | 🟡 draft | R2 | 2026-10-23 | ✅ | §11,§16,§17,§18 |
| 08 | DEMO-DATA-SPEC | 0.3.0 | 🟡 draft | R3 | 2026-10-23 | ✅ | §19.1,§20.2 |
| 09 | BUILD-PLAN-TASKS | 0.3.0 | 🟡 draft | R3 | 2026-10-23 | ✅ | §19 |
| 10 | API-SPECIFICATION | 0.3.0 | 🟡 draft | R2 | 2026-10-23 | ✅ | §11.2-4,§6.10 |
| 11 | AGENT-WORKFLOW | 0.3.0 | 🟡 draft | R3 | 2026-10-23 | ✅ | §11 |
| 12 | DOC-AUDIT (file này) | 0.3.0 | 🟡 draft | R3 | 2026-10-23 | ✅ | — |
| 13 | DECISION-LOG | 0.2.0 | 🟡 draft | R3 | 2026-10-22 | ✅ | §21.1 |
| 14 | TEST-TRACEABILITY | 0.3.0 | 🟡 draft | R3 | 2026-10-23 | ✅ | §14,§15 |

**Tiến độ:** 00–14 đã có bản AI-EOS (15/15) + 2 file khung. Q1–Q6 **đã chốt** (13 §1, R-DEC-05..10) — không đảo quyết định. Vòng 0.3.0 **mở rộng spec-level P0** cho các file domain/sản phẩm (01–12, 14): bổ sung chiều SẢN PHẨM (FR/UC/flow/rule/trạng thái/màn hình), giữ nguyên các ghi chú "chi tiết hóa ở đợt code (R-DEC-09)". Các file 00/13 và 2 file khung giữ 0.2.0 (chưa thuộc diện mở rộng vòng này). Toàn bộ vẫn `🟡 draft` — chờ human promote `current` + bump version chính thức.

## 3. Định dạng (Gate A)

Chuẩn Gate A mỗi file spec: **đúng 1 H1** (`# …`), heading `##` phân mục rõ, **bảng** cho ma trận/registry, **code fence đủ cặp** (số dòng ```` ``` ```` chẵn), kết bằng mục `## N. Open questions` rồi `## Version`.

**Kết quả rà soát vòng 0.3.0 (2026-10-23):** mọi file **01–12 và 14 đạt Gate A** — 1 H1, fence cân bằng, có Open questions + Version. File 00/13 giữ nguyên định dạng Gate A đã có. Kiểm bằng script (đếm `^# `, đếm `^```` ``` ````, tìm `Open questions` + `Version`); chưa chạy `doc-reviewer` tự động (xem OQ-12-01).

## 4. Open questions / audit gaps
- OQ-12-01: Chưa chạy `doc-reviewer` (read-only 5 mục) trên bộ AI-EOS — nên chạy trước promote `current`.
- OQ-12-02: Mọi version/status do human promote; agent chỉ đề xuất 0.3.0, giữ `🟡 draft`.
- OQ-12-03: Cross-ref ID giữa các file verify sơ bộ (domain/role/FR/channel/UC/BO/entity); R-DEC-10 đã chốt (ID theo BRD + ánh xạ `main`), audit ID đầy đủ + numbering chi tiết hóa ở đợt code (R-DEC-09).
- OQ-12-04: Phần field-level DB, task `T-*` và `TC-*` chi tiết cố ý HOÃN sang đợt code (R-DEC-09); Gate B/C chi tiết sẽ bổ sung khi numbering + migration được chốt — hiện 14 chỉ giữ ma trận spec-level khung.

## Version
- **Version:** 0.3.0 (draft, Phase R3)
- **Last updated:** 2026-10-23
- **Maintainer:** @CyEyes
- **Change 0.3.0:** Phản ánh vòng mở rộng **spec-level P0** — bảng trạng thái bump 0.3.0 cho các file mở rộng (01–12, 14), thêm cột `last_reviewed` + `Gate A`; ghi nhận mọi file 01–12/14 đạt Gate A (1 H1, fence cân bằng, Open questions + Version); giữ `🟡 draft`, giữ Q1–Q6 đã chốt; đóng/cập nhật OQ, thêm OQ-12-04 (R-DEC-09 defer field-level/T-*/TC-*).
- **Change 0.2.0:** Chốt Q1–Q6 (R-DEC-05..10) — cập nhật trạng thái quyết định, đóng OQ liên quan; phạm vi docs-first P0.
- **Change 0.1.0:** Tạo 12 cho nhánh `ai-eos` — bảng trạng thái 00–14 (toàn draft 0.1.0) + 2 file khung, định dạng Gate A, audit gaps.
