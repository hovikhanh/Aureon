# 13 — Decision Log (AI-EOS, nhánh `ai-eos`)

> **Vai trò:** Gate B. Theo dõi quyết định cho bản rebuild AI-EOS P0. **Số DEC chính thức do human cấp**; `R-DEC-*` / `Q*` / `B*` là nhãn nội bộ nhánh cho tới khi human cấp DEC (CLAUDE.md §6.7).
> **Trạng thái:** 🟡 draft (Phase R3). **Ngày:** 2026-10-22 · **Maintainer:** @CyEyes

---

## 1. Quyết định nền Q1–Q6 — ĐÃ CHỐT (human, 2026-10-22)

Human đã chốt 6 quyết định nền (chọn mặc định đề xuất). Đây là cơ sở cho toàn bộ bộ tài liệu P0; mọi file 00–14 bám theo.

| ID | Câu hỏi | Quyết định đã chốt | Blocking | Ảnh hưởng |
|---|---|---|---|---|
| R-DEC-05 (Q1) | Viết full 28 domain hay tập P0 MVP trước | **P0 MVP trước**; khung 28 domain giữ ở 00/skeleton; P1/P2 ghi backlog ở 09, không triển khai đợt này | resolved | 01, 08, 09, 10 |
| R-DEC-06 (Q2) | Kiến trúc: Modular Monolith vs tách service | **Modular Monolith** (kế thừa DEC-125); AI Platform §11.1 là cụm module logic bên trong, không tách deployable | resolved | 05, 07 |
| R-DEC-07 (Q3) | Tenant: đa tenant vs 1 tenant | **1 tenant cho MVP; data model có `tenant_id`** sẵn ở mọi entity để nâng đa tenant sau | resolved | 05, 07, 08 |
| R-DEC-08 (Q4) | Role: 7 role BRD thuần vs ánh xạ 10 F.O.C.U.S | **7 role BRD + AI Agent actor**; Director (ROLE-DIR) có data scope thay 5 C-level; giữ **bảng ánh xạ** sang 10 role F.O.C.U.S của `main` (skeleton §12, 02) | resolved | 02 |
| R-DEC-09 (Q5) | Phạm vi đợt này: docs-only vs cả code | **Docs-first**: hoàn thiện 00–14 + governance đợt này; **code/app/migration/merge main là đợt sau** (plan riêng) sau khi docs được human promote `current` | resolved | toàn bộ (phạm vi) |
| R-DEC-10 (Q6) | ID scheme: theo BRD vs giữ ID `main` | **Theo BRD** (D01–D28, FR-*, ROLE-*, UC-*, US-*, C1–C10); giữ **bảng ánh xạ** sang METRIC-/EP-/ENT-/SCR-/TOOL- của `main` để truy nguyên (skeleton §12) | resolved | 00, mọi file |

## 2. Quyết định vận hành nhánh — ĐÃ CHỐT

| ID | Quyết định | Trạng thái |
|---|---|---|
| R-DEC-01 | Tách nhánh `ai-eos` từ `main` @ e394668; `main` giữ demo-ready v2.1 làm baseline | resolved (human) |
| R-DEC-02 | `_reference/` là nguồn Canonical chính thức của nhánh | resolved (human) |
| R-DEC-03 | Viết lại docs theo full AI-EOS (28 domain, 7 role + AI Agent, L0–L4), phạm vi P0 | resolved (human) |
| R-DEC-04 | Rebuild trong `docs/0.AI-EOS-REBUILD/` (không ghi đè docs v2.1 kế thừa) | resolved (human) |
| R-DEC-11 | **Ủy quyền agent sửa `CLAUDE.md` / `AGENT.md` / `.github/copilot-instructions.md`** — chỉ trong phạm vi doc-loading AI-EOS: trỏ canonical `_reference/` + `docs/0.AI-EOS-REBUILD/`, đánh dấu docs v2.1 là baseline reference-only, cập nhật branding Aureon — AI-EOS / release line Aureon v3. Giữ nguyên mọi quy tắc an toàn (gate A/B/C, cấm lộ secret, cấm tự quyết API/schema/stack). Bỏ ràng buộc CLAUDE.md §6.3(6)/§6.6(10) **chỉ cho đợt này**. Bản v2.1 lưu trong git history. | resolved (human, 2026-10-22) |

## 3. Quyết định mở từ BRD §21.1 — CHỜ CEO (không blocking cho docs P0)

Các quyết định này thuộc về CEO/chủ sản phẩm; không chặn việc hoàn thiện tài liệu P0 (docs ghi mặc định tạm + đánh dấu "chờ CEO"). Khi CEO chốt → nâng thành DEC chính thức và cập nhật file liên quan.

| ID | Quyết định | Mặc định tạm trong docs | Ảnh hưởng |
|---|---|---|---|
| B1 | SaaS đa tenant vs nội bộ 1 DN (dài hạn) | Thiết kế có `tenant_id`, chạy 1 tenant MVP (R-DEC-07) | 05, 07, UC-07, giá |
| B2 | Khách hàng mục tiêu đầu (quy mô/ngành) | Doanh nghiệp vừa VN, đa phòng ban | ưu tiên domain |
| B3 | Chính sách AI cloud (dữ liệu tài chính/nhân sự qua cloud quốc tế?) | Classification-based routing: Confidential → local; Secret → không LLM | 02, 07, NFR-DATA |
| B4 | Vai trò với phần mềm kế toán (chỉ đọc MISA/Fast vs nhập gốc) | P0: nhập gốc + IDP; tích hợp đọc là P1 (D06) | D06, D15 |
| B5 | Ngưỡng tự động L3 mặc định (giá trị tối đa) | Tài liệu hóa là cấu hình; mặc định thận trọng, quyết định trọng yếu luôn human | 02, 07, 11.6 |
| B6 | Kênh chat chính (Zalo/Slack/Teams) | P0 không có; C7 là P1 | D05, C7 |
| B7 | Mô hình giá (nếu SaaS) | Ngoài phạm vi docs sản phẩm | — |

## 4. Nguyên tắc

- Mâu thuẫn `docs/` ↔ `_reference/` → ưu tiên `_reference/` (kế thừa DEC-144/145).
- Agent không tự cấp số DEC chính thức; `Q*`/`B*`/`R-DEC-*` là nhãn nội bộ nhánh cho tới khi human cấp DEC.
- Mọi ID dùng trong 00–14 phải tồn tại trong `TRACEABILITY-SKELETON.md`; thêm ID → cập nhật skeleton trước.
- Không triển khai P1/P2 chỉ vì có trong BRD — phải theo backlog (09) + decision.

## Version
- **Version:** 0.2.0 (draft, Phase R3)
- **Last updated:** 2026-10-22
- **Maintainer:** @CyEyes
- **Change 0.2.0:** Human chốt Q1–Q6 → R-DEC-05..10 `resolved` (P0 MVP first, Modular Monolith, single-tenant + `tenant_id`, 7 role + AI Agent, docs-first, ID theo BRD + ánh xạ `main`). Thêm R-DEC-11 (ủy quyền sửa file bảo vệ cho doc-loading AI-EOS). Chuyển B1–B7 (BRD §21.1) thành quyết định mở của CEO, không blocking docs P0.
- **Change 0.1.0:** Tạo 13 cho nhánh `ai-eos` — gom Q1–Q6 + B1–B7 + R-DEC-01..04.
