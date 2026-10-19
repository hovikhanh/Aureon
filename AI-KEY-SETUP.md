# 15 — HƯỚNG DẪN THÊM KEY AI (ĐỂ TEST AI THẬT)

---

> Tài liệu vận hành: cách bật AI thật cho IDP (phân loại + trích xuất tài liệu).
> Mặc định demo chạy ở chế độ **fixture** (phát lại 7 tài liệu mẫu, **không gọi AI thật, không cần key**).
> Khi muốn test AI thật, làm theo các bước dưới đây.

---

## 1. Hai chế độ của Model Gateway

Toàn bộ lời gọi LLM đi qua một điểm duy nhất là `ModelGateway` (07 §5.2, NFR-IDP-05).
Biến môi trường `MODEL_GATEWAY_MODE` quyết định nguồn AI:

| `MODEL_GATEWAY_MODE` | Hành vi | Cần key? |
|---|---|---|
| `fixture` (mặc định) | Phát lại kết quả của 7 tài liệu mẫu đã ghi sẵn trong `apps/api/tests/fixtures/model_gateway/`. Không có mạng, không có AI thật. | ❌ Không |
| `live` | Gọi LLM thật qua endpoint tương thích OpenAI tại `OMNIROUTE_BASE_URL`. | ✅ Có |

Ở chế độ `fixture`, nếu upload một tài liệu **không nằm trong 7 mẫu**, gateway trả lỗi
`FixtureNotFoundError` (đúng như thiết kế — fixture chỉ để demo tất định). Muốn xử lý
tài liệu tuỳ ý thì **phải** chuyển sang `live`.

---

## 2. Các biến môi trường liên quan (trong file `.env` ở gốc repo)

```bash
# Chế độ gateway: fixture (mặc định) hoặc live
MODEL_GATEWAY_MODE=fixture

# Endpoint LLM tương thích OpenAI. Gateway sẽ POST tới {BASE_URL}/chat/completions
OMNIROUTE_BASE_URL=http://localhost:20128/v1

# API key, được gửi dưới dạng:  Authorization: Bearer <OMNIROUTE_API_KEY>
OMNIROUTE_API_KEY=<dán-key-vào-đây>

# Tên model dùng cho 2 tác vụ (đặt theo tên model mà gateway/nhà cung cấp của bạn hỗ trợ)
MODEL_CLASSIFY=agent-free-cheap   # phân loại tài liệu (rẻ, nhanh)
MODEL_EXTRACT=agent-coding        # trích xuất field (mạnh hơn)

# Công tắc tắt khẩn cấp AI. Để false khi muốn chạy AI.
AI_KILL_SWITCH=false
```

> ⚠️ **An toàn (CLAUDE.md § Cấm lộ credentials):** chỉ đặt key thật trong `.env`
> (file này đã nằm trong `.gitignore`). **Không** commit key, **không** đặt key vào
> `.env.example`. File `.env.example` chỉ chứa placeholder `<change-me>`.

---

## 3. Các bước bật AI thật

### Bước 1 — Mở file `.env` ở gốc repo
Nếu chưa có, tạo từ mẫu:
```bash
cp .env.example .env
```

### Bước 2 — Sửa 3 dòng sau trong `.env`
```bash
MODEL_GATEWAY_MODE=live
OMNIROUTE_BASE_URL=<url-gateway-của-bạn>/v1
OMNIROUTE_API_KEY=<key-thật-của-bạn>
```

Có 2 lựa chọn cho endpoint:

- **A. Dùng OmniRoute (đúng thiết kế dự án):** chạy OmniRoute gateway local, lấy
  `BASE_URL` + `API_KEY` của nó, điền vào. OmniRoute sẽ tự route sang
  OpenAI/DeepSeek/Claude/Gemini.
- **B. Trỏ thẳng tới một nhà cung cấp tương thích OpenAI** (ví dụ OpenAI, DeepSeek):
  ```bash
  # Ví dụ OpenAI
  OMNIROUTE_BASE_URL=https://api.openai.com/v1
  OMNIROUTE_API_KEY=sk-...                 # key thật của bạn
  MODEL_CLASSIFY=gpt-4o-mini
  MODEL_EXTRACT=gpt-4o

  # Ví dụ DeepSeek
  OMNIROUTE_BASE_URL=https://api.deepseek.com/v1
  OMNIROUTE_API_KEY=sk-...
  MODEL_CLASSIFY=deepseek-chat
  MODEL_EXTRACT=deepseek-chat
  ```
  Yêu cầu duy nhất: endpoint phải hỗ trợ `POST {BASE_URL}/chat/completions` theo
  chuẩn OpenAI.

### Bước 3 — Khởi động lại API + worker để nạp lại biến môi trường
```bash
# Dừng tiến trình API/worker cũ, rồi chạy lại:
uv run uvicorn app.main:app --reload --port 4000
uv run celery -A app.worker worker --loglevel=info
```
Gateway được tạo một lần theo tiến trình, nên **bắt buộc restart** sau khi đổi `.env`.

### Bước 4 — Kiểm tra
Đăng nhập (ví dụ `reviewer@abc.demo`) rồi dùng màn hình **Nạp dữ liệu** (`/upload`):
- **Tab C2 (ngôn ngữ tự nhiên):** gõ mô tả tài liệu bất kỳ → AI sẽ phân loại +
  trích xuất → tài liệu xuất hiện ở **Hàng chờ** (`/inbox`) ở mức `L2` chờ duyệt.
- **Tab C3 (kéo-thả file):** tải lên PDF/ảnh/Excel bất kỳ → pipeline AI thật chạy.

Nếu vẫn thấy lỗi `FixtureNotFoundError` nghĩa là `MODEL_GATEWAY_MODE` vẫn là
`fixture` (chưa restart hoặc sửa nhầm file).

---

## 4. Xử lý sự cố nhanh

| Triệu chứng | Nguyên nhân thường gặp | Cách xử lý |
|---|---|---|
| `423 AI_DISABLED` khi upload | `AI_KILL_SWITCH=true` | Đặt `AI_KILL_SWITCH=false`, restart |
| `FixtureNotFoundError` | Còn ở chế độ `fixture` | Đặt `MODEL_GATEWAY_MODE=live`, restart |
| `401`/`403` từ gateway | Key sai hoặc thiếu | Kiểm tra `OMNIROUTE_API_KEY` |
| `IDP-E06` sau 3 lần thử | Gateway timeout/5xx | Kiểm tra `OMNIROUTE_BASE_URL` reachable |
| Model "không tồn tại" | Tên model sai | Đổi `MODEL_CLASSIFY`/`MODEL_EXTRACT` theo model gateway hỗ trợ |

---

## 5. Ghi chú

- Chế độ `fixture` vẫn là mặc định để demo/test tất định (TC-IDP-036) không tốn chi phí AI.
- Mọi lời gọi LLM đều đi qua `ModelGateway` (không gọi SDK trực tiếp) — đây là ràng buộc
  kiến trúc (CLAUDE.md § IDP Worker, 07 §5.2).
- Nội dung tài liệu luôn được bọc như **data**, không phải **lệnh** (chống prompt injection).
