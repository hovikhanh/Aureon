# 07 — Tech Architecture & AI Platform (AI-EOS, nhánh `ai-eos`)

> **Nguồn chuẩn:** `_reference/SOURCE-BRD-v1.1.md` §11 (D26 AI Platform), §16 (NFR), §17 (governance), §18 (kiến trúc mục tiêu).
> **Phụ thuộc:** 00, 01, 02, 05. **Trạng thái:** 🟡 draft (Phase R2). **Ngày:** 2026-10-22 · **Maintainer:** @CyEyes

---

## 1. Kiến trúc mục tiêu (BRD §18)

**AI không truy cập DB trực tiếp:** mọi đọc/ghi/hành động đi qua **Tool Layer**, nơi áp quyền + Autonomy Level + phê duyệt + audit. 3 lớp nghiệp vụ:

- **System of Record** — domain services + dữ liệu (28 domain).
- **System of Intelligence** — điều phối AI + analytics.
- **System of Action** — tool, workflow, thông báo, agent.

Nối bởi vòng lặp Outcome → Feedback → System of Record.

> **Q2 — đã chốt (R-DEC-06):** hiện thực hóa trên **Modular Monolith** (FastAPI + Celery, 1 schema PostgreSQL/domain-group), AI Platform là cụm module logic bên trong (không tách deployable) — nhất quán nền `main` (kế thừa DEC-125). Mở sang tách service ở phase 5 nếu cần.

## 2. D26 — AI Platform: 13 thành phần (BRD §11.1)

| Thành phần | Trách nhiệm |
|---|---|
| AI Gateway | Điểm vào duy nhất; xác thực, rate limit, ngân sách, lọc dữ liệu nhạy cảm |
| AI Orchestrator | Hiểu ý định, lập kế hoạch, chọn agent, phối hợp nhiều agent |
| Agent Runtime | Chạy agent, quản lý trạng thái tác vụ dài, retry, timeout |
| Model Gateway | Định tuyến model theo tác vụ/chi phí/phân loại dữ liệu; fallback; **không khóa 1 nhà cung cấp; hỗ trợ on-premise** |
| Prompt & Instruction Mgmt | Quản lý phiên bản prompt, test trước phát hành, rollback |
| Tool Registry | Danh mục tool + schema, quyền, risk level |
| Knowledge Retrieval | Tìm kiếm ngữ nghĩa + graph; **lọc theo quyền trước khi đưa vào model** |
| Memory | Bộ nhớ hội thoại / người dùng / doanh nghiệp; xem & xóa được |
| Document AI Engine | Phân loại, OCR, trích xuất cấu trúc cho Data Capture |
| Policy Engine | Đánh giá quyền, data scope, Autonomy Level mỗi tool call |
| Approval Engine | Tạo & theo dõi yêu cầu phê duyệt cho hành động AI |
| Audit Engine | Ghi bất biến mọi tool call, input, output, quyết định |
| Evaluation Engine | Bộ test chuẩn, đo chất lượng, phản hồi, hiệu chỉnh confidence |
| Event Listener | Nhận event nghiệp vụ để AI chủ động quan sát & cảnh báo |

> **Khác `main`:** `main`/v2.1 làm ModelGateway + Tool Registry + autonomy + audit nhưng **hoãn** Orchestrator/multi-agent/Memory/Prompt versioning/Evaluation đầy đủ (DEC-150). AI-EOS gồm đủ 13 thành phần (MVP làm P0, còn lại theo phase).

## 3. Luồng thực thi & quyền (BRD §11.5)

```text
User/Event → Intent Detection → Context Retrieval → Planning → Tool Selection
→ Authorization (Policy Engine) → Tool Calling → Result Validation → Reasoning
→ Recommendation → Approval (theo Autonomy) → Execution → Verification → Audit
```

- **AI không vượt quyền người được phục vụ:** quyền hiệu lực = **giao của quyền agent ∩ quyền người dùng**.
- Ví dụ: CEO AI → Finance R/W, HR R, Strategy R/W; Employee AI → cá nhân R/W, task team R, Finance DENY.
- AI chạy theo event/lịch (không có người hỏi) dùng **danh tính service của agent**, quyền hẹp nhất.

### 3.1. AI Operating Loop (BRD §17.5)
`OBSERVE → UNDERSTAND → REASON → RECOMMEND → APPROVE → ACT → VERIFY → LEARN → OBSERVE`

## 4. Model Gateway (BRD §11.1, FR-AIQ)

- Đa provider, **không khóa vendor**, hỗ trợ **model on-premise/local**; fallback khi model chính lỗi (NFR-AV-03).
- Định tuyến theo **tác vụ × chi phí × mức phân loại dữ liệu** (02 §5): Mật → local-only; Tuyệt mật → không LLM.
- Mọi call đi qua gateway; log `ModelCallLog` (token/chi phí/provider/fallback/prompt hash — không lưu prompt thô).

## 5. Chất lượng & chi phí AI (BRD §11.7)

FR-AIQ-01 grounding bắt buộc · FR-AIQ-02 bộ test chuẩn/agent, chạy lại trước mọi đổi model/prompt, không phát hành nếu chất lượng giảm · FR-AIQ-03 confidence hiệu chỉnh (Cao/TB/Thấp khi chưa đủ) · FR-AIQ-04 nút đúng/sai → Evaluation Engine · FR-AIQ-05 ngân sách theo tenant/phòng ban/agent, cảnh báo 80% · FR-AIQ-06 **chống prompt injection** từ mọi nguồn ngoài.

## 6. NFR (BRD §16) — baseline MVP

| Nhóm | Mục tiêu nổi bật |
|---|---|
| SEC | SSO + MFA (Admin/CEO/Finance); RBAC+ABAC+field-level; TLS1.2+/AES-256/KMS; tenant isolation; quét mã độc file |
| PERF | UI p95 <2s, dashboard p95 <3s; AI token đầu <2s (streaming), đa-tool p90 <30s; tài liệu ≤5 trang p95 ≤60s; ≥1.000 trang/giờ/tenant |
| Scale | MVP 50 tenant × 1.000 user; mở tới 10.000 user/tenant |
| AV | ≥99,9% core; RPO ≤15', RTO ≤4h; **AI dự phòng** (P10 graceful degradation) |
| DATA | lưu trữ cấu hình vùng (tùy chọn tại VN); thời hạn lưu theo loại; xóa tự động |
| AUD | log bất biến ≥2 năm, tìm & xuất được |
| UX | VI+EN (hiểu câu trộn); web responsive + mobile PWA; WCAG 2.1 AA; onboard ≤30' |
| INT/OBS/COST | API versioned + webhook; giám sát latency/lỗi/chi phí AI/độ chính xác; ngân sách AI trần/tenant |

## 7. Secret & cấu hình
Mọi cấu hình qua config service (fail-fast khi thiếu); không hard-code/commit secret; JWT ký khóa riêng (RS256 nếu tái dùng nền `main`); PII filter trước mọi call model. (Chi tiết env chốt khi code hóa.)

## 8. Open questions
- OQ-07-01: Modular Monolith vs tách service cho Agent Runtime/Orchestrator — ĐÃ CHỐT: R-DEC-06 — Modular Monolith, AI Platform là cụm module logic bên trong (không tách deployable).
- OQ-07-02: Memory store (conversation/user/enterprise) công nghệ — chờ chi tiết hóa ở đợt code (R-DEC-09).
- OQ-07-03: Chính sách model on-prem cho dữ liệu Mật (BRD §21.1 AI cloud) — chờ CEO (B3).

## Version
- **Version:** 0.2.0 (draft, Phase R2)
- **Last updated:** 2026-10-22
- **Maintainer:** @CyEyes
- **Change 0.2.0:** Chốt Q1–Q6 (R-DEC-05..10) — cập nhật trạng thái quyết định, đóng OQ liên quan; phạm vi docs-first P0.
- **Change 0.1.0:** Viết lại 07 theo AI-EOS — kiến trúc 3 hệ thống + Tool Layer, D26 AI Platform 13 thành phần, luồng thực thi & quyền (agent ∩ người), AI Operating Loop, Model Gateway đa provider + on-prem, chất lượng/chi phí AI (FR-AIQ), NFR baseline đầy đủ, secret/config.
