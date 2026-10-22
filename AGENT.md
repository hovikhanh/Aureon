# Agent Instructions

Xem `CLAUDE.md` — file này chứa toàn bộ hướng dẫn vận hành.
File `AGENT.md` chỉ là alias cho các tool không đọc CLAUDE.md.

**Branch-aware (R-DEC-11):** repo có hai dòng sản phẩm song song. Xác định nhánh git hiện tại (`git rev-parse --abbrev-ref HEAD`) trước khi nạp nguồn:
- Nhánh `main` → **Aureon v2.1**; canonical `_reference/`; doc set nạp cho build = `docs/1.CONTEXT`–`docs/4.GOVERNANCE/`.
- Nhánh `ai-eos` → **Aureon v3 — AI-EOS P0**; canonical `_reference/SOURCE-BRD-v1.1.md` (+ `SOURCE-BRD-v1.1-Bổ sung.md`) + `SOURCE-UIUX.md`; doc set nạp cho build = `docs/0.AI-EOS-REBUILD/00-INDEX.md` → 00–14. Docs v2.1 + `SOURCE-BRD-v1.0.md` chỉ là baseline reference-only, **không nạp cho build AI-EOS**.

Mọi quy tắc an toàn (gates, cấm lộ secret, cấm tự quyết API/schema/stack, không force-push/tự-merge) áp dụng nguyên cho cả hai nhánh. Chi tiết: `CLAUDE.md` §0.
