# Agent Instructions

Xem `CLAUDE.md` — file này chứa toàn bộ hướng dẫn vận hành.
File `AGENT.md` chỉ là alias cho các tool không đọc CLAUDE.md.

**Dòng sản phẩm chính thức:** dự án chỉ còn **Aureon v3 — AI-EOS** (AI-First Enterprise Operating System).
- Canonical: `_reference/SOURCE-BRD-v1.1.md` (+ `SOURCE-BRD-v1.1-Bổ sung.md`) + `SOURCE-UIUX.md`.
- Doc set chính thức (`current`, v1.0.0) nạp cho build: `docs/1.CONTEXT/00-INDEX.md` → 00–14 (`docs/1.CONTEXT`–`docs/4.GOVERNANCE/`).
- **KHÔNG nạp cho build:** `docs/_archive/v2.1/` (Aureon v2.1 cũ — archived) và `_reference/SOURCE-BRD-v1.0.md` (historical baseline); chỉ tra cứu lịch sử khi human yêu cầu rõ.
- Codebase `apps/` là nền v2.1 **tái sử dụng**, refactor dần sang model v3 theo từng phase (`docs/3.EXECUTION/09-BUILD-PLAN-TASKS.md`).

Mọi quy tắc an toàn (gates A/B/C, cấm lộ secret, cấm tự quyết API/schema/stack/dependency, không force-push/tự-merge) áp dụng nguyên. Chi tiết: `CLAUDE.md` §0.
