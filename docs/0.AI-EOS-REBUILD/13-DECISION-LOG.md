# 13 — Decision Log (AI-EOS, nhánh `ai-eos`)

> **Vai trò:** Gate B. Theo dõi quyết định mở cho bản rebuild AI-EOS. **Số DEC do human cấp**; agent chỉ đề xuất nội dung (CLAUDE.md §6.7).
> **Trạng thái:** 🟡 draft (Phase R3). **Ngày:** 2026-10-22 · **Maintainer:** @CyEyes

---

## 1. Quyết định rebuild Q1–Q6 (đề xuất — chờ human)

| ID đề xuất | Câu hỏi | Mặc định tạm đang dùng | Blocking |
|---|---|---|---|
| Q1 | Viết full 28 domain hay tập P0 MVP trước | P0 MVP trước; khung 28 domain ở 00 | Có (ảnh hưởng 08/09 scope) |
| Q2 | Kiến trúc: Modular Monolith vs tách service | Modular Monolith; AI Platform = cụm module | Có (ảnh hưởng 07) |
| Q3 | Tenant: đa tenant vs 1 tenant | Data model có `tenant_id`; chạy 1 tenant MVP | Có (ảnh hưởng 05/08) |
| Q4 | Role: 7 BRD thuần vs ánh xạ 10 F.O.C.U.S | 7 role BRD; Director có scope | Không (02 có ánh xạ) |
| Q5 | Phạm vi: docs-only vs cả code | Rebuild tài liệu trước | Có (ảnh hưởng 09) |
| Q6 | ID scheme: theo BRD vs giữ ID `main` | BRD + bảng ánh xạ `main` | Không (skeleton có ánh xạ) |

## 2. Quyết định mở từ BRD §21.1 (chờ CEO)

| ID đề xuất | Quyết định | Ảnh hưởng |
|---|---|---|
| B1 | SaaS đa tenant vs nội bộ 1 DN | kiến trúc tenant, giá, UC-07 |
| B2 | Khách hàng mục tiêu đầu (quy mô/ngành) | ưu tiên domain |
| B3 | Chính sách AI cloud (tài chính/nhân sự qua cloud quốc tế?) | 02 §5, 07 §4, NFR-DATA |
| B4 | Vai trò với phần mềm kế toán (chỉ đọc MISA/Fast vs nhập gốc) | D06, D15 |
| B5 | Ngưỡng tự động L3 mặc định (giá trị tối đa) | 02 §6/§7 |
| B6 | Kênh chat chính (Zalo/Slack/Teams) | D05, C7 |
| B7 | Mô hình giá (nếu SaaS) | ngoài phạm vi docs |

## 3. Quyết định đã ghi nhận trong nhánh này

| ID | Quyết định | Trạng thái |
|---|---|---|
| R-DEC-01 | Tách nhánh `ai-eos` từ `main` @ e394668; `main` giữ demo-ready v2.1 | resolved (human yêu cầu) |
| R-DEC-02 | `_reference/` là nguồn chính; xóa `_reference/README.md` | resolved (human yêu cầu) |
| R-DEC-03 | Viết lại docs theo full AI-EOS (28 domain, 7 role+AI Agent, L0–L4) | resolved (human yêu cầu) |
| R-DEC-04 | Rebuild trong `docs/0.AI-EOS-REBUILD/` (không ghi đè docs v2.1 inherited) | đề xuất |

## 4. Nguyên tắc
- Mâu thuẫn `docs/` ↔ `_reference/` → ưu tiên `_reference/` (DEC-144/145 kế thừa).
- Agent không tự cấp số DEC chính thức; `Q*`/`B*`/`R-DEC-*` là nhãn nội bộ nhánh cho tới khi human cấp DEC.

## Version
- **Version:** 0.1.0 (draft, Phase R3)
- **Last updated:** 2026-10-22
- **Maintainer:** @CyEyes
- **Change 0.1.0:** Tạo 13 cho nhánh `ai-eos` — gom Q1–Q6 (rebuild) + B1–B7 (BRD §21.1) + R-DEC-01..04 (quyết định nhánh), nguyên tắc ưu tiên nguồn.
