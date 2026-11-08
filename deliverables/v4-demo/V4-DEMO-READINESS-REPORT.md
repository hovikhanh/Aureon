# Aureon v4 Demo — Báo cáo sẵn sàng demo

> Ngày 2026-11-08. Nhánh `v3/m8-crm` @ `9cad717` + thay đổi **chưa commit** (180 file sửa, 35 file mới).
> Kiểm chứng trên project Docker `aureon-verify` dựng từ trạng thái sạch; stack `aureon` không bị đụng (0 request trong mọi lần E2E cuối).
> Báo cáo kèm: `06-AI-INTEGRATION-REPORT.md`, `10-PRODUCTION-BACKLOG.md`, `docs/3.EXECUTION/16-OPERATIONS.md` (hướng dẫn Docker).

## 11. Đánh giá cuối (đọc trước)

**Sẵn sàng demo cho các luồng nghiệp vụ; chưa sẵn sàng demo AI trực tiếp.**

| Hạng mục | Đánh giá |
|---|---|
| Khởi chạy từ trạng thái sạch | Đạt: build, migrate, seed, 7 service healthy trong ~40 giây |
| Đăng nhập 10 tài khoản, phân quyền | Đạt |
| Số liệu tài chính, bán hàng, Home | Đạt: FIN-01 khớp Metric Store, funnel hợp lệ, Home dùng số thật |
| Workflow (IDP review → ghi, phê duyệt tuyển dụng, giao việc, OKR) | Đạt |
| AI chat, trích xuất trực tiếp | **Chưa**: model local trên CPU quá chậm (D-19) |
| Hardening production | Ngoài phạm vi (Phase 8) |

## 1. Phase Completion Matrix

| Phase | Trạng thái | Ghi chú |
|---|---|---|
| 1. Audit & baseline | Xong | `deliverables/v4-audit/` |
| 2. Product decisions | Một phần | R-DEC-177..197 ở PROPOSED trong `13` §2ter; còn mở D-17, D-18, D-19, D-20 |
| 3. Documentation | Một phần | Đã cập nhật: 00, 07, 08, 10, 12, 13, 14, README; mới: 16-OPERATIONS, DEC-REGISTRY. Chưa: 01, 02, 03, 05, 06, 09, 11; `CLAUDE.md` chỉ có bản đề xuất |
| 4. Codebase cleanup | Ít | Chỉ dọn phần liên quan sửa lỗi; chưa xóa code chết, `public`, MinIO (R-DEC-189) |
| 5. Implementation | Xong cho phạm vi đã chọn | §4 |
| 6. Functional testing | Xong, có ngoại lệ | §7 |
| 7. Demo readiness | Đạt trừ AI | §11 |
| 8. Production readiness | Chưa bắt đầu | `10-PRODUCTION-BACKLOG.md` |

## 2. Requirement – Implementation Traceability

| Yêu cầu / quyết định | Thực hiện | Test |
|---|---|---|
| D-15 / R-DEC-192: một ngày nghiệp vụ | `BUSINESS_DATE_OVERRIDE`; mọi module dùng `business_today()`; FE tổ chức dùng `businessToday()` | TC-V4-01, TC-V4-08 |
| D-09 / R-DEC-186: Finance là nguồn doanh thu; funnel tích lũy; Q4 = 20 tỷ | FIN-01 một công thức; `quota_attainment_pct` từ Finance; `closed_bookings`; `/sales/funnel` | TC-V4-02, TC-V4-03 |
| D-07 / R-DEC-183: RBAC đúng spec cho REV, MGR | Scope Finance + Sales; FE ẩn route 403 | TC-V4-04, TC-V4-05, TC-V4-14 |
| F6: Home số thật | Department, Employee tính từ dữ liệu | TC-V4-07 |
| TD-03: thanh toán đồng thời | Khóa dòng | TC-V4-06 |
| D-11 / R-DEC-188: dữ liệu nhạy cảm | Mức 3 mặc định, chỉ nâng; roster không tới model; demo chỉ local | TC-V4-09 |
| P05: không bịa số | Grounding siết lại | TC-V4-10 |
| F-C2: replay trung thực | `mode: "replay"` + nhãn UI | TC-V4-13 |
| D-13 / R-DEC-190: Deep Navy, UI | Token màu; ID thô, nhãn, enum, định dạng, dialog, sort, Reviewer nav | TC-V4-14 |
| F12: Strategy UI | `/goals/strategies` | TC-V4-15 |

Chi tiết: `docs/4.GOVERNANCE/14-TEST-TRACEABILITY.md` §1.26.

## 3. Document-Code Conformance

| Tài liệu | Trạng thái |
|---|---|
| `10` API | Khớp: EP-SAL-09, thay đổi EP-FIN-08, EP-SAL-07 (breaking), EP-RPT-01, EP-AI-02, scope Finance/Sales; contract 44 pass |
| `07`, `08` | Có cấu hình demo v4, ngày nghiệp vụ |
| `12` | Cột version khớp file (sửa 8 dòng) |
| `13` | DEC-* có nơi định nghĩa (DEC-REGISTRY, 219 mã, 96/96 mã đang dùng); R-DEC v4 ở PROPOSED |
| `00`, README | Cập nhật trạng thái, vai trò, số test |
| `CLAUDE.md` | **Chưa sửa**; bản đề xuất `var/v4-audit/proposals/CLAUDE-md-R-DEC-188.diff`. Còn khẳng định cũ (A-05..A-09 trong `deliverables/v4-audit/`) |
| `01`, `02`, `03`, `05`, `06`, `09`, `11` | Chưa cập nhật theo v4 |

## 4. Module Functional Status

| Module | Trạng thái | Ghi chú |
|---|---|---|
| Auth, phân quyền | Hoạt động | Đăng nhập demo giữ nguyên (R-DEC-28) |
| Tổ chức, HR | Hoạt động | Cây tổ chức theo ngày nghiệp vụ; tuyển dụng duyệt qua engine |
| Finance | Hoạt động | Số liệu khớp store; MGR không xem hóa đơn cấp công ty (D-20) |
| Sales/CRM | Hoạt động (giai đoạn 1) | Funnel tích lũy; Lead/Contact/Activity chờ R-DEC-176 |
| Product, Risk | Đóng băng | R-DEC-16 |
| Workflow, phê duyệt | Hoạt động | 3 loại yêu cầu |
| Dashboard, KPI, Home | Hoạt động | |
| Mục tiêu, chiến lược | Hoạt động | Thêm UI chiến lược |
| IDP | Hoạt động | Review, ghi, undo; trích xuất live chậm |
| AI chat | Logic đúng, **không kịp thời gian** trên máy này | `06-AI-INTEGRATION-REPORT.md` |
| Reporting | Hoạt động | |

## 5. Database and API Consistency

| Mục | Kết quả |
|---|---|
| Migration | Không có migration mới; DB sạch lên `0027_external_event_link_c19` |
| Schema | Không đổi |
| API mới | `GET /sales/funnel` |
| API breaking | `/sales/dashboard`: `closed_revenue` → `closed_bookings` (FE, mock đã cập nhật) |
| Shared types | Sinh lại (564 type), test khớp OpenAPI |
| Contract test | 44/44 |

## 6. AI Integration

Xem `06-AI-INTEGRATION-REPORT.md`. Tóm tắt: trích xuất hóa đơn bằng model local là thật; roster bị chặn đúng; chat live hết giờ sau 90 giây do phần cứng (4 CPU, không GPU, ~2 token/giây).

## 7. Test Results and E2E Evidence

| Bộ | Kết quả |
|---|---|
| ruff, format, mypy (394 file) | Sạch |
| pytest (DB cô lập) | **1656 passed, 0 failed** |
| Contract | 44 passed |
| ESLint, tsc | Sạch |
| Vitest | 566 passed |
| E2E `real`, stack sạch, một lần chạy | 125 / 136 pass |
| Sau khi sửa 3 spec, chạy lại riêng | m7-records, goals, m8-crm: 12/12 pass |
| **Tổng E2E** | **128 pass, 8 fail có nguyên nhân** |

8 test fail còn lại:

| Test | Nguyên nhân | Loại |
|---|---|---|
| `ceo-7steps` (2), `uc03` | Chat live hết giờ: phần cứng | AI |
| `chat` "demo mode" | Stack kiểm chứng tắt replay; test cần replay bật | Cấu hình |
| `meetings` (2) | Cần model trả lời nhanh | AI |
| `m5-ai-telemetry` | Không có lượt gọi model nào trên DB sạch | Dữ liệu |
| `onboarding` L2/L3 | Image chưa vá cũng fail y hệt; chưa truy nguyên nhân | Có sẵn từ trước |

Các test được sửa theo quyết định (không nới assertion): reviewer không còn liệt kê hóa đơn công ty (D-07); kiểm tra hóa đơn do CFO; "hôm qua" theo ngày nghiệp vụ (D-15); helper đăng nhập chờ hydrate (flaky dưới tải).

**Hai hồi quy do chính đợt này gây ra, đã sửa:** đóng phòng ban khi undo không hiện đúng (TC-V4-08); gán nhân viên vào phòng ban mới bị 422 do frontend dùng ngày thật.

## 8. Docker Demo Deployment Guide

Xem `docs/3.EXECUTION/16-OPERATIONS.md`. Lệnh kiểm chứng đã chạy thành công:

```bash
V=var/v4-audit/verify
C="docker compose -p aureon-verify --env-file $V/.env.verify -f docker-compose.full.yml -f $V/docker-compose.verify.yml"
$C build api web
$C up -d postgres redis mailpit api celery-worker celery-beat web
python3 -I var/v4-audit/tools/verify_login.py http://127.0.0.1:4700 $V/.env.verify
```

Web: `http://127.0.0.1:3700`. Stack kiểm chứng đang chạy; dừng bằng `$C down -v` (chỉ xóa dữ liệu của project này).

**Stack chính `aureon` vẫn chạy image cũ** (`aureon-*:local`). Đưa v4 lên stack chính cần build lại và tạo lại container, khi bạn duyệt.

## 9. Known Issues and Technical Debt

| # | Vấn đề | Mức |
|---|---|---|
| 1 | AI live quá chậm trên máy demo | High (demo) |
| 2 | MGR ghi được hóa đơn qua IDP nhưng không xem được hóa đơn cấp công ty (D-20) | Medium (nghiệp vụ) |
| 3 | `onboarding` L2/L3 sai so với kỳ vọng test | Medium |
| 4 | 3 dòng chỉ tiêu tháng + KR tổng 85 tỷ mâu thuẫn Q4 = 20 tỷ | Medium |
| 5 | Win rate kỳ có thể 100% với mẫu 2 deal, không cảnh báo cỡ mẫu | Low |
| 6 | `PerformanceRow.attainment_pct` theo deal, chưa đổi tên thành bookings | Low |
| 7 | Tài liệu 01, 02, 03, 05, 06, 09, 11 và `CLAUDE.md` chưa cập nhật | Medium |
| 8 | Chưa xóa code chết, chưa dọn `public`, MinIO | Low |
| 9 | 180 file thay đổi chưa commit trên nhánh `v3/m8-crm` | **Cần quyết định** |

## 10. Production Readiness Backlog

Xem `10-PRODUCTION-BACKLOG.md`. P0 trước người dùng thật: repo private, đổi mật khẩu demo, xoay khóa + secret + thu hồi phiên, đóng cổng hạ tầng, chốt egress AI trong code, khôi phục CI.

## Quyết định cần bạn

| ID | Câu hỏi | Đề xuất |
|---|---|---|
| D-19 | AI thật cho demo: GPU, model nhỏ, xử lý trước, hay đổi D-11 cho dữ liệu demo giả? | Xử lý trước cho buổi demo gần; GPU hoặc model nhỏ lâu dài |
| D-20 | MGR có được xem hóa đơn cấp công ty mà mình đã ghi qua IDP? | Cho xem hóa đơn do chính MGR ghi (theo lineage) |
| — | Commit 180 file trên nhánh nào? | Nhánh mới `v4/demo-readiness`, chia commit theo nhóm: số liệu, quyền, AI, UI, tài liệu |
| — | Đưa v4 lên stack chính? | Sau khi commit; backup trước |
| — | Duyệt R-DEC-177..197 và bản `CLAUDE.md` 3.1.0 | Duyệt theo `13` §2ter |
