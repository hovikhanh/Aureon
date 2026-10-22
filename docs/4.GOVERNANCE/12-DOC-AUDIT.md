# 12 — Document Audit (Aureon v3 — AI-EOS)

> **Vai trò:** Gate A cho bộ tài liệu AI-EOS. Theo dõi trạng thái 00–14.
> **Phụ thuộc:** toàn bộ. **Trạng thái:** ✅ current — Aureon v3 (AI-EOS) CHÍNH THỨC. **Ngày:** 2026-10-23 · **Maintainer:** @CyEyes

---

## 1. Bối cảnh

Bộ tài liệu AI-EOS là tài liệu CHÍNH THỨC **Aureon v3 — AI-EOS** để code, đặt tại vị trí docs chuẩn (`docs/1.CONTEXT`, `2.PRODUCT`, `3.EXECUTION`, `4.GOVERNANCE`). Tách từ Aureon v2.1 (nay archived ở `docs/_archive/v2.1/`). Các file đã được human promote `current`.

Vòng này (**spec-level P0**) nâng các file domain P0 từ "outline nén" lên **spec-level đầy đủ**: bổ sung mô tả hành vi per-FR, tiêu chí chấp nhận UC, luồng/trạng thái, quy tắc nghiệp vụ, ngoại lệ, chỉ số và mapping sang v2.1. Bám canonical `_reference/SOURCE-BRD-v1.1.md` (+ Bổ sung) + `SOURCE-UIUX.md`; ID chỉ dùng registry trong `docs/4.GOVERNANCE/TRACEABILITY-SKELETON.md` (R-DEC-10). Tôn trọng R-DEC-09 (docs-first): KHÔNG field-level DB, KHÔNG task `T-*`, KHÔNG `TC-*` chi tiết — hoãn sang đợt code.

## 2. Trạng thái tài liệu (2026-10-23)

Cột **last_reviewed** = ngày rà soát/mở rộng gần nhất. Cột **Gate A** = ✅ đạt (đúng 1 H1, fence cân bằng, có `## N. Open questions` + `## Version`); — = file khung, không áp Gate A spec.

| # | File | Version | Status | Phase | last_reviewed | Gate A | Nguồn BRD |
|---|---|---|---|---|---|---|---|
| — | REBUILD-PLAN | 0.2.0 | ✅ current | — | 2026-10-22 | — | §4,§19 |
| — | TRACEABILITY-SKELETON | 0.3.0 | ✅ current | — | 2026-10-23 | — | §2,§3,§4,§11,§14,§15 |
| 00 | INDEX | 0.2.0 | ✅ current | R0 | 2026-10-22 | ✅ | — |
| 01 | PROJECT-OVERVIEW | 0.3.0 | ✅ current | R0 | 2026-10-23 | ✅ | §1,§2,§19,§20 |
| 02 | PERSONAS-PERMISSIONS | 0.3.0 | ✅ current | R1 | 2026-10-23 | ✅ | §3,§5.2,§11.6,§17 |
| 03 | DASHBOARD-SPEC | 0.3.0 | ✅ current | R1 | 2026-10-23 | ✅ | §11.8,§12 |
| 04 | IDP-FEATURE-SPEC | 0.3.0 | ✅ current | R1 | 2026-10-23 | ✅ | §6 |
| 05 | DATA-MODEL | 0.3.0 | ✅ current | R2 | 2026-10-23 | ✅ | §13 |
| 06 | UI-UX-SPEC | 0.3.0 | ✅ current | R2 | 2026-10-23 | ✅ | UIUX full |
| 07 | TECH-ARCHITECTURE | 0.3.0 | ✅ current | R2 | 2026-10-23 | ✅ | §11,§16,§17,§18 |
| 08 | DEMO-DATA-SPEC | 0.3.0 | ✅ current | R3 | 2026-10-23 | ✅ | §19.1,§20.2 |
| 09 | BUILD-PLAN-TASKS | 0.3.0 | ✅ current | R3 | 2026-10-23 | ✅ | §19 |
| 10 | API-SPECIFICATION | 0.3.0 | ✅ current | R2 | 2026-10-23 | ✅ | §11.2-4,§6.10 |
| 11 | AGENT-WORKFLOW | 0.3.0 | ✅ current | R3 | 2026-10-23 | ✅ | §11 |
| 12 | DOC-AUDIT (file này) | 1.0.0 | ✅ current | R3 | 2026-10-23 | ✅ | — |
| 13 | DECISION-LOG | 0.2.0 | ✅ current | R3 | 2026-10-22 | ✅ | §21.1 |
| 14 | TEST-TRACEABILITY | 0.3.0 | ✅ current | R3 | 2026-10-23 | ✅ | §14,§15 |

**Tiến độ:** 00–14 đã có bản AI-EOS (15/15) + 2 file khung. Q1–Q6 **đã chốt** (13 §1, R-DEC-05..10) — không đảo quyết định. Vòng spec-level P0 **mở rộng spec-level** cho các file domain/sản phẩm (01–12, 14): bổ sung chiều SẢN PHẨM (FR/UC/flow/rule/trạng thái/màn hình), giữ nguyên các ghi chú "chi tiết hóa ở đợt code (R-DEC-09)". Toàn bộ đã được human promote **✅ current — Aureon v3 (AI-EOS) CHÍNH THỨC**.

## 3. Định dạng (Gate A)

Chuẩn Gate A mỗi file spec: **đúng 1 H1** (`# …`), heading `##` phân mục rõ, **bảng** cho ma trận/registry, **code fence đủ cặp** (số dòng ```` ``` ```` chẵn), kết bằng mục `## N. Open questions` rồi `## Version`.

**Kết quả rà soát spec-level P0 (2026-10-23):** mọi file **01–12 và 14 đạt Gate A** — 1 H1, fence cân bằng, có Open questions + Version. File 00/13 giữ nguyên định dạng Gate A đã có. Kiểm bằng script (đếm `^# `, đếm `^```` ``` ````, tìm `Open questions` + `Version`); chưa chạy `doc-reviewer` tự động (xem OQ-12-01).

## 4. Open questions / audit gaps
- OQ-12-01: Nên chạy `doc-reviewer` (read-only 5 mục) trên bộ AI-EOS để rà soát định kỳ sau promote.
- OQ-12-02: Version/status do human quản lý; bộ tài liệu đã được human promote `✅ current — Aureon v3 (AI-EOS)`.
- OQ-12-03: Cross-ref ID giữa các file verify sơ bộ (domain/role/FR/channel/UC/BO/entity); R-DEC-10 đã chốt (ID theo BRD + ánh xạ v2.1), audit ID đầy đủ + numbering chi tiết hóa ở đợt code (R-DEC-09).
- OQ-12-04: Phần field-level DB, task `T-*` và `TC-*` chi tiết cố ý HOÃN sang đợt code (R-DEC-09); Gate B/C chi tiết sẽ bổ sung khi numbering + migration được chốt — hiện 14 chỉ giữ ma trận spec-level khung.

## Version
- **Version:** 1.0.0 (current)
- **Last updated:** 2026-10-23
- **Maintainer:** @CyEyes
- **Change 1.0.0 (promote):** Promote tài liệu AI-EOS lên CHÍNH THỨC Aureon v3; di chuyển vào vị trí docs chuẩn; v2.1 archived (docs/_archive/v2.1/).
- **Change 0.3.0:** Phản ánh vòng mở rộng **spec-level P0** — bảng trạng thái bump 0.3.0 cho các file mở rộng (01–12, 14), thêm cột `last_reviewed` + `Gate A`; ghi nhận mọi file 01–12/14 đạt Gate A (1 H1, fence cân bằng, Open questions + Version); giữ Q1–Q6 đã chốt; đóng/cập nhật OQ, thêm OQ-12-04 (R-DEC-09 defer field-level/T-*/TC-*).
- **Change 0.2.0:** Chốt Q1–Q6 (R-DEC-05..10) — cập nhật trạng thái quyết định, đóng OQ liên quan; phạm vi docs-first P0.
- **Change 0.1.0:** Tạo 12 cho bộ AI-EOS — bảng trạng thái 00–14 + 2 file khung, định dạng Gate A, audit gaps.
