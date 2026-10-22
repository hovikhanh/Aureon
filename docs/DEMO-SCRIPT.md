# Aureon v2.1 — Kịch bản demo 5 phút

> Đối tượng: stakeholder / ban điều hành. Dữ liệu: công ty giả định ABC, kỳ báo cáo **T9/2026 (Q3)**.
> Chuẩn bị: `./scripts/demo_reset.sh` (trạng thái sạch: 13 alert, 1 hóa đơn chờ review) →
> mở 2 tab trình duyệt `http://localhost:3000` (tab 2 ẩn danh cho Reviewer).

## 0. Checklist trước demo (2 phút trước giờ)

- [ ] `docker compose -f docker-compose.full.yml ps` → 9 service `healthy`
- [ ] `curl -s localhost:4000/health` → `"status":"ok"`
- [ ] `DEMO_MODE=true` trong `.env` (dropdown tài khoản + chat replay 1,4–2,6 s)
- [ ] Đã chạy `./scripts/demo_reset.sh` → in ra `5 users ✔ 32 metrics ✔ 13 alerts ✔ 1 NEEDS_REVIEW ✔`

## 1. Login (30 s)

- Mở `localhost:3000` → dropdown **Tài khoản demo** → chọn **CEO (ceo@abc.demo)** → **Đăng nhập**.
- Nói: *"Không có self-register; 10 vai trò, mỗi vai trò chỉ thấy trụ được phép."*

## 2. Dashboard Overview (60 s)

- Chỉ 5 thẻ trụ: **F🟢 C🟢 U🟡 O🟡 S🔴** và nhãn "Kỳ báo cáo: T9/2026".
- Click thẻ **S** → 2 rủi ro critical. Story: *"AI phát hiện rủi ro — CEO chỉ thấy ngoại lệ thật."*
- Quay lại, chỉ danh sách **13 alert**, sắp xếp critical trước; Acknowledge 1 alert.

## 3. Finance Drill-down (60 s)

- Click thẻ **F** → "Trụ Tài chính": 6 metric (Doanh thu, Chi phí, Sử dụng ngân sách, Runway,
  Số dư tiền mặt, Burn rate) với sparkline 12 tháng.
- Click **Doanh thu** → hộp thoại lineage: metric → các bản ghi hóa đơn cấu thành → tài liệu gốc.
  (Ground-truth: doanh thu Q3 = **73,5 tỷ**.)
- Story: *"Mọi con số truy ngược được tới tài liệu gốc."*

## 4. AI Chat (60 s)

- Sidebar **AI Chat** → hỏi **"Doanh thu Q3?"**.
- Streaming trả lời < 2–3 s (demo replay; số liệu vẫn lấy từ tool chạy bằng quyền CEO) kèm citation **[1]**.
- Click **[1]** → popover nguồn. Mở "AI đang dùng tool" để thấy tool đã gọi.
- Hỏi tiếp **"Top 5 khách hàng?"**.
- Nói: *"AI dùng quyền của người hỏi; không có nguồn thì không trả số."*

## 5. IDP Review (90 s)

- Tab 2: login **Reviewer (reviewer@abc.demo)** → **Hàng chờ review** → hóa đơn `NEEDS_REVIEW`.
- Mở hóa đơn → 2 cột: tài liệu gốc (highlight) | 8 trường với ConfidenceBadge, **3 trường trọng yếu**
  (tiền) viền đỏ — luôn qua người.
- Sửa 1 trường số tiền + nhập **lý do** (bắt buộc với trường tiền).
- **Approve** → toast **"Đã ghi vào Finance"** → hóa đơn xuất hiện ở `/finance/invoices`.
- Quay tab CEO → dashboard trụ F làm mới (refetch 60 s hoặc F5).

## 6. Wrap-up (30 s)

- AI grounded (mọi số có nguồn) · IDP end-to-end (upload → review → ghi Finance qua Action Registry)
  · 5 trụ F.O.C.U.S · **752 BE + 17 FE + 25 E2E test**.
- Q&A.

## Xử lý sự cố nhanh

| Triệu chứng | Cách xử lý |
|---|---|
| Thẻ trụ báo "Không khả dụng" | Nút Thử lại; kiểm `curl localhost:4000/health/ready` |
| Chat chậm (9–13 s) | Câu hỏi ngoài 10 câu replay → model live; dùng đúng câu trong kịch bản |
| Hàng chờ trống | `./scripts/demo_reset.sh` (tạo lại 1 hóa đơn chờ review) |
| Approve báo trùng số hóa đơn | Đã approve trước đó → reset |
