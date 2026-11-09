# Aureon v4 Demo — Báo cáo sẵn sàng demo

> Ngày 2026-11-09. Nhánh `v4/demo-readiness` (tách từ `v3/m8-crm` @ `9cad717`), chưa push.
> Stack chính `aureon` đã chạy bản v4: `http://localhost:3000` (API `:4000`).
> Kèm: `06-AI-INTEGRATION-REPORT.md` (AI, D-19), `10-PRODUCTION-BACKLOG.md` (Phase 8), `docs/3.EXECUTION/16-OPERATIONS.md` (vận hành, triển khai, hoàn tác).

## 1. Đánh giá cuối

**Sẵn sàng demo, kể cả AI thật chạy local.** Môi trường là demo nội bộ (D-01); hardening production là backlog Phase 8, không chặn demo.

| Hạng mục | Kết quả |
|---|---|
| Dựng từ trạng thái sạch | Build, migrate tới `0028`, seed, 7 service healthy trong ~35 giây |
| Triển khai stack chính | Backup trước; migrate `0027 → 0028`; dữ liệu cũ giữ nguyên; smoke 16/16 |
| CEO toàn quyền dữ liệu nghiệp vụ (D-21) | Đạt ở backend và giao diện |
| Phân quyền các role khác | Không hồi quy; REV, MGR đúng D-07, D-20 |
| AI | Model local thật `qwen2.5:3b-instruct`; 13–67 giây/lượt khi máy tải, ~2–3 giây khi lặp lại câu hỏi |

## 2. Chức năng đã triển khai trong đợt này

| Nhóm | Nội dung | Quyết định |
|---|---|---|
| Quyền CEO | Thêm `finance:write`, `hr:write`, `hr:approve`, `product:write`, `risk:write`, `idp:approve`; bỏ giới hạn "Sales chỉ ghi chỉ tiêu"; CEO xóa được deal | D-21, R-DEC-198 |
| Giao diện quản lý dữ liệu | Trang Product, Risk, Điều hành (họp, quyết định, dự án); xóa task; lưu trữ vị trí; CEO chuyển giai đoạn deal; mục Review cho CEO | R-DEC-201 |
| CRM | Lead, Contact, Activity (migration `0028`), chuyển lead thành khách hàng + liên hệ + deal; cảnh báo trùng; hoạt động của lead đi theo khách hàng | R-DEC-176 (tập con), D-08 |
| Hóa đơn của Manager | MGR xem danh sách và chi tiết hóa đơn do mình tạo (kể cả ghi qua review IDP); không sửa, xóa hóa đơn công ty; áp cả cho tool AI | D-20, R-DEC-199 |
| AI demo | Adapter Ollama gốc (giữ model trong RAM, stream token và tool call), chọn tool theo ý định trong quyền người hỏi, stream từng câu đã kiểm số, timeout theo tác vụ, nạp sẵn model | D-19, R-DEC-200 |
| Tool AI theo scope | Tool hóa đơn, chi phí, ngân sách, deal áp đúng quy tắc REST (REV không đọc; MGR theo phòng/người tạo) | D-07, D-20 |
| Toàn vẹn dữ liệu | Không xóa khách hàng còn deal, hợp đồng, liên hệ, hoạt động; rủi ro, quyết định, phát hành, số dư tiền kết thúc bằng trạng thái thay vì xóa | — |
| Sửa lỗi giao diện | Ô chọn không còn tràn màn hình điện thoại; người phụ trách rủi ro bắt buộc ngay trên form (BR-RSK-02) | — |
| Dọn code | Gỡ `DashboardView`, `PillarCard`, `executivePillars` (lưới 5 trụ v2.1 không còn dùng) | — |

Đợt trước (đã commit `15f4139..432126f`): một ngày nghiệp vụ, số liệu Finance/Sales nhất quán, RBAC D-07, AI trung thực, Deep Navy, trang chiến lược.

## 3. Ma trận CRUD của CEO

Kiểm bằng `apps/api/tests/integration/test_ceo_full_crud_d21.py` (backend) và `e2e/m7-records.spec.ts` "CEO (D-21)" (giao diện). "Xóa" là xóa mềm (`deleted_at`, có audit).

| Module | Bản ghi | Tạo | Xem | Sửa | Xóa / kết thúc |
|---|---|---|---|---|---|
| Tổ chức | Tổ chức, phòng ban, team, vị trí | ✓ | ✓ | ✓ | ✓ khi không còn người/đơn vị con (phòng ban còn nhân viên → 422) |
| Tổ chức | Gán nhân sự | ✓ | ✓ | ✓ | Đóng bằng `valid_to` (lịch sử theo ngày hiệu lực) |
| Nhân sự | Nhân viên | ✓ | ✓ (cả dữ liệu mức 4) | ✓ | ✓ |
| Nhân sự | Lịch sử lương | ✓ | ✓ | — | — (chỉ thêm, theo ngày hiệu lực) |
| Nhân sự | Kế hoạch tuyển dụng | ✓ | ✓ | ✓ | ✓; gửi, duyệt qua engine |
| Người dùng | Tài khoản, vai trò | ✓ | ✓ | ✓ (gán vai trò) | Vô hiệu hóa / kích hoạt lại (không xóa cứng) |
| Tài chính | Doanh thu, chi phí, ngân sách | ✓ | ✓ | ✓ | ✓ |
| Tài chính | Hóa đơn | ✓ | ✓ | ✓ + ghi thanh toán | ✓ nếu chưa thanh toán (đã trả → 409) |
| Tài chính | Số dư tiền, dự báo | ✓ | ✓ | ✓ | — (không có DELETE) |
| Kinh doanh | Khách hàng | ✓ | ✓ | ✓ | ✓ nếu không còn deal, hợp đồng, liên hệ, hoạt động (409) |
| Kinh doanh | Deal, hợp đồng, chỉ tiêu | ✓ | ✓ | ✓ (+ chuyển giai đoạn) | ✓ |
| CRM | Lead, liên hệ, hoạt động | ✓ | ✓ | ✓ (lead đã chuyển thì chỉ đọc) | ✓; chuyển lead |
| Sản phẩm | Sản phẩm, tính năng, lộ trình | ✓ | ✓ | ✓ | ✓ (sản phẩm còn phát hành mở → 422) |
| Sản phẩm | Phát hành; chỉ số | ✓ | ✓ | ✓ / — | — |
| Rủi ro | Rủi ro, biện pháp | ✓ | ✓ | ✓ (+ đánh giá, chấp nhận) | Đóng / hủy qua trạng thái |
| Điều hành | Chiến lược, mục tiêu, OKR, KR, KPI, task, dự án, lịch | ✓ | ✓ | ✓ | ✓ (mục tiêu còn KR, task còn việc con → từ chối) |
| Điều hành | Cuộc họp | ✓ | ✓ | ✓ | ✓ nếu chưa có quyết định |
| Điều hành | Quyết định | ✓ | ✓ | ✓ | Đóng bằng `cancelled` (giữ Decision Log) |
| Tài liệu | Tài liệu IDP | ✓ | ✓ | Duyệt, sửa trường | Hoàn tác trong 7 ngày |

Thay đổi của CEO đi qua cùng service, audit và outbox như mọi role. Test xác nhận một doanh thu CEO tạo làm `METRIC-FIN-01` đổi trên dashboard tài chính và Metric Store.

## 4. Kết quả kiểm thử

| Bộ | Trước đợt (2026-11-08) | Sau đợt (2026-11-09) |
|---|---|---|
| Backend pytest (DB tạm) | 1656 passed | **1703 passed, 0 failed** |
| Contract | 44 | 44 |
| ruff, format, mypy | Sạch (394 file) | Sạch (399 file) |
| ESLint, tsc | Sạch | Sạch |
| Vitest | 566 | **590** |
| E2E `real` (136 test) | 128 pass, 8 fail | Lượt đầy đủ cuối **135 pass**; test còn lại đã sửa, pass 2 lượt riêng |
| Request lọt vào stack chính trong lúc E2E | 0 | 0 |
| Smoke stack chính sau triển khai | — | **16/16** |

8 test fail trước đây (7 AI, 1 onboarding) đều pass, không nới assertion:
- **AI:** chạy model thật; riêng `meetings` và UC-07 chờ tối đa 150 giây theo số đo.
- **Onboarding L2/L3:** test viết khi trần autonomy là L2; nay test tự cấu hình policy L2 thật.
- **"demo mode":** chạy trên cặp replay riêng có nhãn.

Các lỗi E2E phát sinh trong đợt này và cách xử lý:

| Lỗi | Nguyên nhân | Xử lý |
|---|---|---|
| Tạo rủi ro bị 422 | Form để trống người phụ trách, quy tắc BR-RSK-02 bắt buộc | Form bắt buộc trường này |
| Bảng Kanban tràn 17 px trên điện thoại | Ô chọn rộng theo lựa chọn dài nhất | Giới hạn chiều rộng ô chọn |
| `ERR_ABORTED` khi đổi tài khoản | Ứng dụng tự chuyển trang chồng lệnh của test | Fixture thử lại một lần |
| Duyệt tuyển dụng chờ trạng thái | Khung chi tiết đóng sau khi duyệt (theo thiết kế) | Test kiểm toast và hàng chờ |

## 5. Docker

| Mục | Giá trị |
|---|---|
| Demo | `http://localhost:3000` (API `http://localhost:4000`) |
| Revision DB | `0028_crm_leads_contacts_activity` |
| Image | `aureon-api:local`, `aureon-web:local` (bản v4); bản cũ gắn tag `pre-v4-20261109-160626` |
| Backup | `var/backup/v4-20261109-160626/` (dump DB, file IDP, `.env`, số dòng trước triển khai) |
| Hoàn tác | `var/v4-audit/deploy/deploy_main.sh rollback 20261109-160626` + `pg_restore` (16-OPERATIONS §6.1) |
| Cấu hình AI | `MODEL_PROVIDER_PRIMARY=ollama`, không fallback, `AI_DEMO_REPLAY=false`, `LOCAL_CHAT_MODEL=qwen2.5:3b-instruct`, `BUSINESS_DATE_OVERRIDE=2026-10-20` |
| Stack kiểm chứng `aureon-verify` | Đã dừng (giữ volume) để nhường CPU cho demo |

Người đang đăng nhập cần đăng nhập lại để nhận quyền mới (quyền nằm trong JWT).

## 6. Lỗi và hạn chế còn tồn tại

| # | Vấn đề | Mức | Ghi chú |
|---|---|---|---|
| 1 | Chat AI 13–67 giây khi máy đang tải; không đảm bảo dưới 30 giây | Trung bình (demo) | Không chạy việc nặng trong lúc demo; hỏi một câu khởi động trước. GPU sẽ cho phép dùng `7b` |
| 2 | Trích xuất IDP không hiện tiến độ từng bước | Thấp | Cần commit giữa pipeline hoặc field API mới |
| 3 | MGR tải hóa đơn lên nhưng REV commit thì MGR không thấy (theo người tạo) | Thấp | Muốn mở rộng cần truy vấn lineage IDP |
| 4 | Pipeline cấu hình, snapshot dự báo, deal nhiều sản phẩm, duyệt chỉ tiêu (phần còn lại R-DEC-176) | Theo lộ trình | Chưa làm |
| 5 | 3 dòng chỉ tiêu tháng + KR 85 tỷ mâu thuẫn Q4 = 20 tỷ | Trung bình | Cần PO chỉ định cách xử lý dữ liệu |
| 6 | `ENT-SalesActivity` là ID mới, đang ở mức đề xuất | Thấp | Cần cấp trong registry |
| 7 | `CLAUDE.md` chưa cập nhật (agent không được tự sửa) | Trung bình | Bản đề xuất: `var/v4-audit/proposals/CLAUDE-md-R-DEC-188.diff` |
| 8 | Chưa xóa schema `public`, chưa gỡ MinIO (R-DEC-189 chờ đánh giá) | Thấp | Giữ theo D-12 |
| 9 | Key provider cloud vẫn còn trong `.env` chính, nhưng chuỗi provider không có cloud | Thấp (demo) | PO xóa key khi xoay secret; chốt egress trong code thuộc Phase 8 |

## 7. Quyết định

| ID | Nội dung | Trạng thái |
|---|---|---|
| D-21 / R-DEC-198 | CEO toàn quyền CRUD dữ liệu nghiệp vụ | APPROVED bởi PO 2026-11-09; IMPLEMENTED |
| D-20 / R-DEC-199 | MGR xem hóa đơn do mình tạo | Agent quyết theo ủy quyền PO; IMPLEMENTED |
| D-19 / R-DEC-200 | AI local `qwen2.5:3b-instruct` + intent routing + streaming | Agent quyết theo ủy quyền PO; IMPLEMENTED |
| R-DEC-201 | Trang quản lý Product, Risk, Điều hành (thay một phần R-DEC-16) | Agent quyết theo ủy quyền PO; IMPLEMENTED |
| R-DEC-177..197 | Các quyết định v4 trước đó | Vẫn PROPOSED, chờ PO duyệt |

## 8. Tài liệu đã cập nhật

`01`, `02`, `03`, `05`, `06`, `09`, `10`, `11`, `13`, `14`, `16-OPERATIONS`, `DEC-REGISTRY`, `README.md`, `06-AI-INTEGRATION-REPORT.md`, báo cáo này. Mọi thay đổi version tài liệu ở mức đề xuất; human promote ở `12`.
