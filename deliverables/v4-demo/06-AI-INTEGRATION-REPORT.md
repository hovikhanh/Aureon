# Aureon v4 — Báo cáo tích hợp AI

> Cập nhật 2026-11-09 (D-19). Phạm vi: AI Core (chat, tool, grounding), IDP (phân loại, trích xuất, OCR), Knowledge search.
> Ràng buộc đã duyệt D-11: tài liệu mặc định CONFIDENTIAL trước khi phân loại; roster không lên cloud; **không provider nào nhận dữ liệu INTERNAL**. Mọi AI thật trong demo chạy model local (Ollama). D-19 không thêm provider hay key cloud nào.

## 1. Kết luận

**AI thật dùng được trong demo trên máy hiện tại** (4 CPU, 12 GB RAM, không GPU), với `qwen2.5:3b-instruct` và luồng chat mới:

- Một câu hỏi CEO cần **một** lượt model thay vì hai, prompt khoảng 350 token thay vì 1.287 + 1.735.
- Thời gian một lượt chat qua API thật: **13–67 giây (trung vị 44 giây) khi máy bận** (load 8–10 do việc khác chạy song song); **2,0–2,8 giây** thời gian model khi prompt cache của Ollama còn ấm (load 3). Trước D-19: 7B mất 240 giây, vượt giới hạn 90 giây → `504`.
- Câu trả lời hiện dần từng câu qua SSE (`/ai/chat/stream`), mỗi câu đã qua grounding trước khi gửi.
- 8/8 spec E2E được giao đều pass trên stack `aureon-verify` (§7).

Giới hạn còn lại: khi máy bận, một lượt có thể quá 30 giây; chất lượng 3B đủ cho câu hỏi số liệu một trụ, yếu hơn ở câu tổng hợp (§6.3). Máy có GPU (phương án A) vẫn là hướng dài hạn.

## 2. Trạng thái từng năng lực

| Năng lực | Trạng thái | Bằng chứng |
|---|---|---|
| Chat CEO trên số liệu thật | **REAL, dùng được** | 8 câu hỏi demo qua API, 3B, không lỗi, không timeout (§6.2) |
| Streaming câu trả lời | **REAL** | `start` → tool → `token` từng câu đã grounding → `done` (§5.3) |
| Trích xuất biên bản họp (EP-DC-38, đồng bộ) | REAL | 3 trường: extract 10,5–11,8 s + classify 3–6 s trong stack (load ~4) |
| Trích xuất hóa đơn PDF có text layer | REAL, bất đồng bộ (worker) | 3B: 56 s; 1.5B: 45 s (load 7–8). Trước: 1.394 s với 7B khi máy tải nặng |
| Phân loại tài liệu | REAL, chủ yếu bằng luật | `confidence_kind` ghi rõ tầng |
| Bảng nhân sự (roster) | Chặn đúng D-11 | Không model nào được gọi |
| Chat kịch bản (replay) | MOCK, **có nhãn**, mặc định tắt | `mode: "replay"` + "Kịch bản demo"; chỉ bật ở cặp `web-replay`/`api-replay` riêng |
| Kết quả xử lý trước (pre-processed) | **Không làm** | Không cần: hóa đơn chạy xong trong worker < 1 phút (hạn 180 s) |
| Grounding (không bịa số) | REAL, mạnh hơn | Số không có nguồn bị gỡ trước khi hiển thị; mỗi số còn lại được server gắn `[n]` đúng nguồn |
| Lọc tool theo quyền | REAL | Intent routing chỉ thu hẹp trong tập tool người hỏi được dùng (TC-V4-21) |
| Scope bản ghi qua tool AI | REAL (sửa trong D-19) | `TOOL-list_invoices`: MGR chỉ hóa đơn mình tạo, REV `FORBIDDEN_SCOPE` (TC-V4-24) |
| Knowledge search | Keyword REAL; vector REAL | `bge-m3` 0,3–0,4 s/lần nhúng trong stack |
| STT giọng nói | Chưa có | R-DEC-166 hoãn |
| Đánh giá độ chính xác | Đánh giá tay 8 câu (§6.3) | Chưa có bộ nhãn vàng |

## 3. Chi phí và egress

| Mục | Hiện trạng |
|---|---|
| Stack kiểm chứng | `MODEL_PROVIDER_PRIMARY=ollama`, không fallback, không key cloud |
| Model | `LOCAL_CHAT_MODEL=qwen2.5:3b-instruct` (chat, classify, extract), `bge-m3` (embed). Đổi bằng env, không sửa code |
| Chốt chặn egress trong code | Chưa có (Phase 8, R-DEC-188) — D-19 không đổi điểm này |

## 4. Quyết định D-19 (R-DEC-200)

Chọn phương án **B (model local nhỏ hơn) cộng tối ưu luồng chat**, giữ D-11. Lý do và số đo ở §6.

| Thành phần | Quyết định |
|---|---|
| Model | `qwen2.5:3b-instruct` cho máy CPU. 7B quá chậm (240 s/lượt). 1.5B nhanh gấp đôi 3B nhưng đưa ra nhận định sai (vd "bán hàng rất tốt" khi pipeline đang cảnh báo; "turnover tăng so với năm trước" không có dữ liệu) |
| API Ollama | Native `/api/chat`: `keep_alive=30m`, `num_ctx=4096`, đo `prompt_eval` / `eval` theo từng lượt |
| Intent routing | Câu hỏi → nhóm ý định (luật, bỏ dấu). Tool đọc hiển nhiên chạy trước bằng quyền người hỏi; tool gửi model chỉ là phần giao giữa ý định và quyền. Không khớp → toàn bộ tool được phép như cũ |
| Dữ liệu cho model | Thẻ chỉ số gọn một dòng (`Doanh thu vs kế hoạch: 86.4% (warning, 2026-09)`), có tên chỉ số |
| Prompt | Ngắn, có ngày nghiệp vụ (trước đó model đoán kỳ "2023-Q2") |
| Trích nguồn | Server gắn `[n]` theo giá trị khớp; bỏ `[n]` model tự viết |
| Streaming | Từng câu đã grounding; `done.answer` là bản cuối |
| Timeout | Chat 90 s, trích xuất 180 s (worker), khác 30 s; tất cả là hạn toàn lượt |
| Warm-up | API và worker nạp model khi khởi động |
| Replay | Giữ nguyên, tắt mặc định, nhãn "Kịch bản demo" |
| Pre-processed | Không làm (không cần theo số đo) |

## 5. Thiết kế

### 5.1. Luồng một lượt chat

1. `classify_prompt` (PII/SECRET) như cũ.
2. Tool được phép: agent `allowed_tools` ∩ quyền ∩ ceiling (như cũ).
3. `select_tools` (`intent.py`): thu hẹp trong tập trên; chạy trước tool đọc không cần tham số (vd `TOOL-get_finance_dashboard` cho "doanh thu"), ghi `ToolCallLog` L0 như model tự gọi. Ý định ghi ("giao việc") không chạy trước gì.
4. Một lượt model (stream). Nếu model gọi thêm tool, vòng lặp cũ chạy tiếp (≤ 8 tool).
5. Grounding toàn bộ câu trả lời, gắn trích nguồn, lưu, gửi `done`.

### 5.2. Ba chế độ, phân biệt rõ

| `mode` | Nguồn câu chữ | Nhãn UI | Bật khi |
|---|---|---|---|
| `live` | Model local thật | Nhãn AI thường | Mặc định |
| `fixture` | Bản ghi cố định trong test | — | `MODEL_GATEWAY_MODE=fixture` (CI) |
| `replay` | Câu viết sẵn quanh số thật | "Kịch bản demo: … Không phải câu trả lời của AI." | `AI_DEMO_REPLAY=true` |

Không có chế độ "pre-processed". Replay không bao giờ được trình bày như suy luận trực tiếp.

### 5.3. Sự kiện SSE

Không thêm loại sự kiện (10 §EP-AI-02). Lượt live gửi `start` ngay, `tool_call`/`tool_result` khi tool chạy, `token` khi một câu hoàn tất và đã grounding, `done` với câu trả lời cuối. Replay và gateway không stream giữ cách gửi cũ. Client ngắt kết nối → lượt bị hủy.

## 6. Số đo

### 6.1. Ollama trực tiếp, cùng prompt thật (2026-11-09, sau khởi động lại; load 6–11 do việc khác)

| Model | Trường hợp | Prompt token | Đọc prompt (s) | Token sinh | Sinh (s) | Tổng (s) |
|---|---|---|---|---|---|---|
| 7B | Trước, lượt 1 (16 tool) | 1.287 | 111,7 | 38 | 14,7 | 138,1 |
| 7B | Trước, lượt 2 (trả lời) | 1.735 | 45,1 | 66 | 48,5 | 101,9 |
| 7B | Sau, một lượt, cache lạnh | 889 | 107,1 | 35 | 19,0 | 137,5 |
| 3B | Trước, lượt 1 | 1.287 | 56,4 | 24 | 4,5 | 66,4 |
| 3B | Trước, lượt 2 | 1.735 | 21,9 | 177 | 63,7 | 93,9 |
| 3B | Sau, một lượt, cache lạnh | 889 | 32,5 | 19 | 3,2 | 38,5 |
| 1.5B | Trước, lượt 1 | 1.287 | 28,3 | 35 | 3,6 | 34,7 (không gọi tool) |
| 1.5B | Sau, một lượt, cache lạnh | 889 | 16,2 | 59 | 6,6 | 22,9 |

Nạp model lạnh: 7B 18,4 s, 3B 5,1 s, 1.5B 3,6 s. Lần đo trước (00:20, load 30–100): 7B đọc 1.287 token mất 265,7 s; 3B đọc prefix đã cache chỉ 1,0 s. Số "sau" ở bảng trên còn 5 tool và thẻ JSON; bản cuối gọn hơn (§6.2: 349–361 token).

Trích xuất (prompt thật của `Extractor`):

| Model | Tài liệu | Prompt token | Token sinh | Tổng (s) | Load |
|---|---|---|---|---|---|
| 1.5B | Biên bản họp, 3 trường | 208 | 108 | 22,8 | 5,9 |
| 3B | Biên bản họp | 208 | 85 | 33,8 (gồm nạp 5,2) | 7,5 |
| 1.5B | Hóa đơn DOC-09, 8 trường | 407 | 258 | 45,5 | 8,0 |
| 3B | Hóa đơn DOC-09 | 407 | 212 | 56,4 | 6,8 |
| 7B | — | — | — | Không đo xong: máy lên load 98 do việc khác, phiên bị ngắt | — |

### 6.2. Qua API thật (`aureon-verify`, SSE, CEO, replay tắt)

| Câu hỏi | 3B tổng (s) | 3B token vào/ra | 1.5B tổng (s) |
|---|---|---|---|
| Doanh thu quý này so với mục tiêu thế nào? | 31,9 (câu đầu 15,4) | 568 / 32 | 23,6 |
| Doanh thu Q3? | 23,1 | 349 / 16 | 14,7 |
| Vì sao dòng tiền căng? | 27,8 | 351 / 13 | 15,8 |
| Tình hình bán hàng tháng này ra sao? | 61,6 | 329 / 56 | 17,2 |
| Tình hình nhân sự thế nào? | 66,8 | 361 / 68 | 26,5 |
| Có cảnh báo nào cần chú ý không? | 44,3 | 605 / 30 | 21,2 |
| Tình hình công ty? | 64,3 | 976 / 30 | 29,0 |
| Biên lợi nhuận gộp hiện bao nhiêu? | 13,2 | 355 / 16 | 5,3 |

Load trong lúc đo: 3B 7,9–9,5; 1.5B 6,1–8,3. Khi máy rảnh (load 3) và prompt cache ấm, lượt chat 3B trong E2E mất 2,0–2,8 s thời gian model (`ai.model_call_logs`, 349 token vào, 16–22 ra).

### 6.3. Chất lượng (đánh giá tay, 8 câu)

| Model | Đúng số, có nguồn | Nhận định sai | Ghi chú |
|---|---|---|---|
| 3B | 8/8 câu không có số bịa lọt qua; 1 số bị grounding gỡ ("Doanh thu nhân sự") | 0 nhận định sai rõ | Ngắn; câu tổng hợp hơi sơ sài |
| 1.5B | Số đúng nguồn | ≥ 4 câu: "bán hàng rất tốt" khi pipeline cảnh báo, "turnover tăng so với năm trước", "Net burn giảm… duy trì hoạt động", liệt kê mã cảnh báo thô | Grounding chỉ bảo vệ con số, không bảo vệ nhận định |

Vì vậy chọn 3B. 1.5B chỉ nên dùng cho trích xuất nếu cần nhanh hơn (`MODEL_EXTRACT__OLLAMA`).

## 7. Kiểm chứng

| Hạng mục | Kết quả |
|---|---|
| pytest (DB cô lập slot 7): `unit` | 596 passed |
| `integration/ai` + `ai_eval` | 224 passed |
| `integration/idp` | 207 passed |
| `-m contract` | 44 passed |
| `architecture` | 30 passed |
| ruff, ruff format, mypy | Sạch (399 file) |
| Web: lint, typecheck, Vitest | Sạch; 590 test / 63 file |
| E2E `ceo-7steps-real` (5 test, gồm 2 test AI) | Pass |
| E2E `uc03-real` (2 test) | Pass |
| E2E `meetings` (4 test) | Pass (preview 16,6 s và 20,4 s) |
| E2E `m5-ai-telemetry` | Pass, tự tạo một lượt chat thật trước |
| E2E `chat` (4 test, "demo mode" trên cặp replay) | Pass |

Thay đổi spec, không nới assertion:

- `uc03-real`, `ceo-7steps-real`: chỉ sửa chú thích (trước ghi "demo-replay"; nay chạy model thật).
- `chat.spec` "demo mode": chạy trên deployment có replay (`E2E_REPLAY_BASE_URL`, cặp `web-replay` :3701 → `api-replay` :4701, cùng DB); thêm assertion nhãn "Kịch bản demo". Thiếu biến → test fail có thông báo, không giả lập.
- `m5-ai-telemetry`: ở project `real` gọi `POST /ai/chat` thật trước (DB sạch chưa có log). Hạn test 240 s.
- `meetings`: project `real` chờ preview tối đa 150 s (đo 15–60 s tùy tải); mock vẫn 15 s.

Lệnh bật cặp replay: `$C --profile replay up -d api-replay web-replay` (override `var/v4-audit/verify/docker-compose.verify.yml`).

## 8. Thay đổi code

| Vùng | Thay đổi |
|---|---|
| `core/model_gateway/adapters.py` | `OllamaAdapter` native (`keep_alive`, `num_ctx`, `format`, tool, NDJSON stream, hạn toàn lượt, `warm`); stream OpenAI gom tool call |
| `core/model_gateway/gateway.py`, `routing.py`, `types.py` | Log `model_timing`; `warm()`; timeout theo tác vụ; `ChatChunk.tool_calls`, `timings` |
| `core/config.py`, `.env.example` | `OLLAMA_KEEP_ALIVE`, `OLLAMA_NUM_CTX`, `EXTRACT_TIMEOUT_SECONDS`, `CHAT_MAX_OUTPUT_TOKENS`, `CHAT_INTENT_ROUTING`, `AI_WARMUP_ON_START`; `.env.example` đề xuất 3B |
| `modules/ai/services/intent.py` (mới) | Chọn tool theo ý định, chạy trước tool đọc |
| `modules/ai/services/chat_service.py` | Prompt có ngày, routing, prefetch, stream + grounding từng câu, thẻ gọn |
| `modules/ai/services/grounding.py` | `attach_citations` |
| `modules/ai/services/tool_executor.py` | Tên chỉ số trong thẻ; scope REST cho tool hóa đơn, chi phí, ngân sách, deal |
| `modules/ai/routes/router.py` | SSE theo thời gian thực; warm-up khi API khởi động |
| `workers/idp_pipeline.py` | Warm-up model trích xuất khi worker sẵn sàng |
| Test | `unit/test_chat_intent_d19.py`, `integration/ai/test_chat_intent_d19.py`, `integration/ai/test_tool_scope_d07.py`, test adapter Ollama + citation; 2 fixture `chat_actions` đổi khóa (prompt đổi, nội dung giữ nguyên) |

## 9. Chưa đạt

- Lượt chat không đảm bảo < 30 s khi máy đang chạy việc khác (đo 13–67 s ở load 8–10). Trong demo nên tránh chạy test song song.
- Trích xuất không hiển thị tiến độ từng bước: pipeline commit một lần. Muốn hiện tiến độ cần commit trung gian (rủi ro lặp trang khi worker chết) hoặc thêm trường API — chưa làm.
- 7B không đo được trích xuất trong phiên này (máy quá tải, phiên bị ngắt).
