# Aureon v4 — Báo cáo tích hợp AI

> Ngày 2026-11-08. Phạm vi: AI Core (chat, tool, grounding), IDP (phân loại, trích xuất, OCR), Knowledge search.
> Ràng buộc đã duyệt D-11: tài liệu mặc định CONFIDENTIAL trước khi phân loại; roster không lên cloud; **không provider nào nhận dữ liệu INTERNAL**. Vì vậy mọi AI thật trong demo chạy model local (Ollama).

## 1. Kết luận

**Logic AI đã trung thực và an toàn hơn; AI thật chưa dùng được để trình diễn trực tiếp trên máy hiện tại.**

Máy demo có 4 nhân CPU, 12 GB RAM, không GPU. `qwen2.5:7b-instruct` chạy 100% CPU: đọc prompt khoảng 9 token/giây, sinh khoảng 1,6–2,3 token/giây. Một lượt chat kèm schema tool dài hàng nghìn token vượt giới hạn 90 giây và trả `504 AI_PROVIDER_TIMEOUT`. Hệ thống báo lỗi rõ ràng, không bịa câu trả lời.

## 2. Trạng thái từng năng lực

| Năng lực | Trạng thái | Bằng chứng |
|---|---|---|
| Trích xuất hóa đơn PDF có text layer | **REAL**, chậm | DOC-09: provider `ollama`, kết quả `NEEDS_REVIEW` (trường trọng yếu luôn qua người). Mất 1.394 giây khi máy đang tải nặng; chưa đo lại lúc nhàn |
| Phân loại tài liệu | REAL nhưng chủ yếu bằng luật | Tầng `header`/`keyword` trước; `confidence_kind` ghi rõ là heuristic, không phải xác suất của model |
| Bảng nhân sự (roster) | **Chặn đúng D-11** | DOC-06: mức nhạy cảm 4, `forbidden`, không model nào được gọi, chuyển review thủ công |
| Mức nhạy cảm tài liệu | REAL | Mới tạo = 3 (CONFIDENTIAL), chỉ nâng theo loại tài liệu, không bao giờ hạ (TC-V4-09) |
| Chat CEO trên số liệu thật | Logic REAL; **không chạy được trong 90 giây** trên máy này | `504 AI_PROVIDER_TIMEOUT` ×2 trên stack sạch |
| Chat kịch bản (replay) | MOCK, **có nhãn** | Số lấy từ tool thật; câu chữ viết sẵn; `mode: "replay"` + cảnh báo "Kịch bản demo" trên UI. Mặc định tắt |
| Grounding (không bịa số) | REAL | Số viết bằng chữ, số gần đúng không có nguồn bị gỡ (TC-V4-10) |
| Lọc tool theo quyền + ceiling | REAL | Ceiling theo chuỗi provider thực tế, không theo cảm nhận prompt; tool không chạy được không quảng bá cho model (TC-V4-13) |
| Lịch sử chat | REAL | 10 cặp gần nhất, đã lọc PII, tin nhắn SECRET bị loại |
| Timeout tool | REAL | `statement_timeout` theo savepoint cho tool đọc |
| Knowledge search | Keyword: REAL. Vector: có code, chưa kiểm live | Không còn 502 khi thiếu embedding (TC-V4-11); index `bge-m3` local có job backfill |
| OCR PDF scan | REAL có trạng thái | Lỗi không còn bị nuốt; `ocr_status` thật (TC-V4-12). Chất lượng OCR tiếng Việt chưa đo |
| `source_location` | REAL | Trang thật chứa giá trị, hoặc `null` (không còn cố định trang 1) |
| STT giọng nói | Chưa có | R-DEC-166 hoãn |
| Đánh giá độ chính xác | **Chưa có số thật** | `ai_eval` chạy fixture; chưa có bộ nhãn vàng |

## 3. Chi phí và egress

| Mục | Hiện trạng |
|---|---|
| Lượt gọi cloud trên DB chính | 1 (`omniroute/extract`, 2026-11-04), trước khi có D-11 |
| Stack kiểm chứng | `MODEL_PROVIDER_PRIMARY=ollama`, không fallback, không key cloud → `routing.chain_has_cloud` = false |
| Chốt chặn egress trong code | **Chưa có** (Phase 8, R-DEC-188). Thực nghiệm cho thấy chỉ đổi primary là chưa đủ: có fallback cloud thì lỗi Ollama vẫn đẩy dữ liệu INTERNAL sang cloud |
| Classification trong `ModelCallLog` | Chưa lưu: không chứng minh được D-11 bằng log |

## 4. Cần quyết định (D-19, mới)

Muốn AI thật trong demo, phải chọn một hướng:

| Phương án | Ưu | Nhược |
|---|---|---|
| A. Máy có GPU cho Ollama | Giữ D-11, tốc độ đủ demo | Chi phí phần cứng |
| B. Model local nhỏ hơn (1,5B–3B) | Không tốn thêm | Chất lượng tiếng Việt, tool calling kém hơn; cần đo |
| C. Xử lý trước tài liệu, trình diễn kết quả đã lưu | Demo ổn định | Không phải AI trực tiếp |
| D. Cho phép cloud cho dữ liệu demo giả (DEC-136) | Nhanh, chất lượng cao | **Đổi D-11**; cần quyết định của bạn |

Đề xuất: **C cho buổi demo gần nhất, A hoặc B cho lâu dài.** D chỉ khi bạn chủ động đổi D-11.

## 5. Thay đổi code (tóm tắt)

| Vùng | Thay đổi |
|---|---|
| `core/model_gateway/routing.py` | Mô tả lại chuỗi theo D-11; `chain_has_cloud()` |
| `core/model_gateway/gateway.py`, `adapters.py` | Ollama structured output, timeout theo tác vụ, embed local |
| `modules/idp/services/pipeline.py`, `upload_service.py` | Mức nhạy cảm mặc định 3, chỉ nâng; `TemplateRequired` → review thủ công thay vì 500 |
| `modules/idp/services/preprocess.py`, `extractor.py` | OCR PDF scan có trạng thái; `source_location` thật |
| `modules/idp/services/knowledge_index.py`, `knowledge_search.py` | Index `bge-m3`; fallback keyword |
| `modules/ai/services/grounding.py` | Bắt số viết chữ, siết dung sai |
| `modules/ai/services/chat_service.py`, `tool_executor.py` | Ceiling, lịch sử, tool không chạy được bị ẩn, replay có `mode` |
| `apps/web/src/features/ai/*` | Hiển thị nhãn "Kịch bản demo", giữ nhãn khi tải lại lịch sử |
