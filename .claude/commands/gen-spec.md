Hãy sinh tài liệu `$ARGUMENTS` dựa trên thông tin tại
`docs/1.CONTEXT/01-PROJECT-OVERVIEW.md` và các spec đã có.

Quy trình:

1. Đọc ngữ cảnh từ `docs/1.CONTEXT/01-PROJECT-OVERVIEW.md` và các file liên quan
   theo doc loading matrix trong `docs/1.CONTEXT/00-INDEX.md`.
2. Kiểm tra các governance gate trước khi viết:
   - Gate A: `docs/4.GOVERNANCE/12-DOC-AUDIT.md`
   - Gate B: `docs/4.GOVERNANCE/13-DECISION-LOG.md`
   - Gate C: `docs/4.GOVERNANCE/14-TEST-TRACEABILITY.md`
   Nếu có gate blocking hoặc thiếu thông tin bắt buộc, dừng và báo `BLOCKED`.
3. Lập bản Plan khung nội dung chi tiết trước khi triển khai.
4. Sinh đầy đủ nội dung chi tiết vào đúng đường dẫn file trong `docs/`.
5. Gọi subagent `doc-reviewer` để audit file vừa tạo.
6. Chỉ hoàn tất khi nhận được báo cáo audit; ghi nhận test mapping phù hợp vào
   `docs/4.GOVERNANCE/14-TEST-TRACEABILITY.md`.

Không đọc hoặc sửa các file trong `_reference/`. Không tự ý đổi API, database schema,
tech stack hoặc dependency; nếu cần, dừng và raise decision theo quy định dự án.