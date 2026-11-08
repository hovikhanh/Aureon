# Aureon v4 Demo — Implementation backlog

Phạm vi: DEMO/MVP chạy Docker. Hardening production là backlog Phase 8, không chặn demo.

## Nguyên tắc đã áp dụng

| Chủ đề | Quyết định kỹ thuật | Lý do |
|---|---|---|
| W-1 (bỏ dropdown demo) | Không áp, chuyển Phase 8 | R-DEC-28 vẫn hiệu lực cho demo |
| D-11 | Demo dùng model local (Ollama); không gọi cloud | Tôn trọng quyết định đã duyệt, vẫn có AI thật |
| Stack `aureon` | Không đụng khi phát triển; kiểm chứng trên project Docker riêng | Không mất dữ liệu, bằng chứng |
| Test | Mọi test chạy DB tạm (`iso_env.sh`) | `.env` trỏ DB chính |

## Thứ tự

| Nhóm | Mục | Nguồn | Trạng thái |
|---|---|---|---|
| A. Số liệu đúng | Một đồng hồ, tách business date (D-15) | F1, F2 | Đang làm |
| | FIN-01 một công thức; runway; win rate | F5, F9, K1, K3, K6 | Đang làm |
| | Home Department, Employee dùng số thật | F6 | Đang làm |
| | Funnel tích lũy (D-09) | F8, K4 | Đang làm |
| B. Quyền | Scope REV, MGR ở Finance, Sales (D-07) | F3 | Đang làm |
| C. Workflow | Decision Log có đường ghi; tuyển dụng sau duyệt; race thanh toán | F11, F19, TD-03 | Đang làm |
| D. UI | Reviewer, ID thô, enum, định dạng, nhãn, dialog, ngõ cụt, Deep Navy | U-01..U-13, U-34, D-13 | Đang làm |
| E. AI | Model local, grounding, OCR PDF scan, source_location, RAG, tool hỏng | F-H1..F-H8 | Đang làm |
| F. Tài liệu | 00–14, DEC-REGISTRY, runbook, traceability | A-01..A-14, C-01..C-11 | Sau code |
| G. Demo | Stack sạch, E2E, báo cáo | Phase 6–7 | Sau cùng |

## Chờ quyết định nghiệp vụ (không tự làm)

| Mục | Vì sao |
|---|---|
| Deal thắng sinh doanh thu dự kiến | PROPOSED, chưa duyệt |
| Danh bạ tối thiểu, quyền EMP theo khối | Đổi RBAC (R-DEC-184) |
| 3 dòng chỉ tiêu tháng + KR tổng 85 tỷ | Mâu thuẫn với Q4 = 20 tỷ (D-09) |
| Thực thể CRM (R-DEC-176) | D-08: sau V4.0 |
