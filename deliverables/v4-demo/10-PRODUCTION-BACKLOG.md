# Aureon v4 — Production Readiness Backlog (Phase 8)

> Theo R-DEC-196 (đề xuất): các mục dưới đây **không chặn demo**, nhưng **chặn production**. Thứ tự là đề xuất.
> Chi tiết kỹ thuật và bằng chứng nằm ngoài repo (`var/v4-audit/`, gitignore) vì repo còn public.

## P0 — trước khi có bất kỳ người dùng thật nào

| # | Hạng mục | Vì sao | Quyết định liên quan |
|---|---|---|---|
| 1 | Chuyển repository sang private | Repo đang public | R-DEC-181 |
| 2 | Đổi toàn bộ mật khẩu demo; gỡ đường đăng nhập demo ở môi trường production | Mật khẩu demo đã nằm trong lịch sử Git public | R-DEC-180, W-1 (`var/v4-audit/w1/W-1.patch`, đã dry-run) |
| 3 | Xoay khóa RS256 **cùng lúc** với `NEXTAUTH_SECRET` và thu hồi refresh token | Chỉ xoay khóa không kết thúc phiên (đã chứng minh bằng dry-run) | R-DEC-168, R-DEC-180 |
| 4 | Không publish cổng hạ tầng ra ngoài; Redis có mật khẩu; Postgres dùng role thường | Cổng đang mở trên mọi interface | R-DEC-191, R-DEC-195 |
| 5 | Chốt chặn egress AI trong code + lưu classification trong log | Hiện chỉ dựa vào cấu hình | R-DEC-188 |
| 6 | Khôi phục CI backend; branch protection `main`; DB test riêng có guard | CI backend đang bị skip; `pytest` có thể chạy trên DB thật | — |

## P1 — trước khi go-live

| # | Hạng mục |
|---|---|
| 7 | Rate limit (đăng nhập, AI 20/phút); đổi/đặt lại mật khẩu; MFA cho Admin, CEO, Finance (R-DEC-187) |
| 8 | Logout gọi EP-07; BFF refresh khi `401`; verify JWT theo `kid` với nhiều public key |
| 9 | TLS, cookie `Secure`, security headers, ẩn `/docs`, `/metrics` |
| 10 | Mask dữ liệu mức 4 trên mọi endpoint IDP; four-eyes cho review |
| 11 | Quét CVE Python, npm, image; ghim tag image (bỏ `latest`) |
| 12 | Backup tự động, thử restore, RPO ≤ 15 phút; runbook xoay khóa 90 ngày |
| 13 | Audit đăng nhập thất bại; audit log chặn cả TRUNCATE |
| 14 | Không đóng gói `.env.local` vào image web (`**/.env*` trong dockerignore) |
| 15 | Ghi IP client thật qua BFF để truy vết |

## P2 — vận hành

| # | Hạng mục |
|---|---|
| 16 | Kiểm thử tải, hiệu năng; tách worker IDP; giảm kích thước image API (5,25 GB) |
| 17 | Quyết định MinIO và schema `public` sau khi đánh giá dữ liệu (R-DEC-189) |
| 18 | Firewall log, giám sát, cảnh báo |
