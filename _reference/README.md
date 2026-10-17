# _reference — Tài liệu gốc (không dùng để build)

## ⚠️ CẢNH BÁO

Thư mục này chứa **tài liệu gốc** — KHÔNG phải spec chính thức.
**AI Agent KHÔNG được đọc thư mục này.**

## Files

| File | Nguồn | Ngày | Vai trò |
|---|---|---|---|
| SOURCE-BRD.md | BRD gốc | 2026-10-05 | Tài liệu tham chiếu |
| SOURCE-UIUX.md | UI/UX gốc | 2026-10-05 | Tài liệu tham chiếu |

## Vì sao giữ

- **Traceability:** biết spec mới (docs/) đến từ đâu
- **Fallback:** khi spec mới thiếu chi tiết, tra ngược
- **Audit:** chứng minh quyết định có cơ sở

## Vì sao KHÔNG để agent đọc

- Chứa nội dung out-of-scope (21 domain khác)
- Có version conflict với spec mới
- Tham chiếu file không tồn tại (BRD v1.0)
- Làm loãng context window

## Khi nào dùng

✅ Con người đọc khi:
- Review spec mới
- Viết spec cho phase 2
- Trả lời stakeholder "tại sao thay đổi"

❌ KHÔNG dùng khi:
- Agent code
- CI/CD validate
- Viết test

## Mapping: file gốc → spec chính thức

| Nội dung gốc | Đã chuyển vào |
|---|---|
| BRD §3.5 FR-DC | docs/2.PRODUCT/04-IDP-FEATURE-SPEC.md |
| BRD §4.3 Bộ chỉ số | docs/2.PRODUCT/03-DASHBOARD-SPEC.md |
| BRD §4.4 AI Quality | docs/3.EXECUTION/07-TECH-ARCHITECTURE.md |
| UI/UX §6.2 Review | docs/2.PRODUCT/06-UI-UX-SPEC.md |
| ... | ... |