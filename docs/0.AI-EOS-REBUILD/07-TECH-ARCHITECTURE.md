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

### 1.1. Modular Monolith (R-DEC-06) & ánh xạ 11 module `main`

Kiến trúc triển khai P0 là **một deployable** (app FastAPI + Celery worker/beat), trong đó 20 domain P0 (§12bis skeleton) được gom thành cụm module logic; AI Platform (D26/D27) là một cụm module trong cùng process, **không tách microservice** ở P0. Ranh giới module là ranh giới code + schema PostgreSQL, không phải ranh giới mạng.

- **Nguyên tắc liên module (P02 API First, P06 Traceability):** module chỉ gọi nhau qua `services` public hoặc **domain event qua Transactional Outbox**; cấm import `models`/`repositories` chéo module và cấm query schema của module khác. Cần transaction chéo module → truyền `AsyncSession` hiện tại vào service đích.
- **Event backbone (FR-DATA-05):** mọi ghi nghiệp vụ = bản ghi + audit + lineage (nếu có) + outbox event trong **một transaction** (`publish_in_tx`); consumer `acks_late` + dedupe theo `processed_events` → retry → DLQ. Đây là xương sống để Event Listener (AI chủ động) và metric store tiêu thụ event mà không khóa thời gian xử lý vào request.
- **Single-tenant + `tenant_id` (R-DEC-07):** mọi entity nghiệp vụ mang `tenant_id`; truy vấn áp bộ lọc tenant ở service layer để sẵn sàng mở multi-tenant (NFR-SEC-04) mà không đổi schema.

**Ánh xạ sang 11 module nền `main`** (giữ traceability §12 skeleton — AI-EOS gom nhiều domain BRD vào một module `main`):

| Module `main` | Schema | Domain AI-EOS P0 gom vào | Ghi chú |
|---|---|---|---|
| `auth` | `auth` | D02 (phần xác thực/JWT) | Chỉ module này đọc private key ký token |
| `platform` | `platform` | D02 (admin/security), D05 Notification, D06 Integration Hub, FR-DATA-01..08 | Metric store, alert, lineage, audit, outbox, user admin |
| `dashboard` | — (đọc `platform`) | D28 Reporting cơ bản (briefing/drill-down) | Không có schema riêng |
| `finance` | `finance` | D15 Finance Lite | PIL-F |
| `sales` | `sales` | D17 Sales Lite, (D18 Customer → P1) | PIL-C |
| `hr` | `hr` | D16 HR cơ bản, D01 Organization | PIL-O (con người) |
| `product` | `product` | (D22 Product → P1) | P0 chỉ khung |
| `risk` | `risk` | (D25 Risk → P1) | P0 chỉ khung |
| `execution` | `execution` | D07 Strategy, D08 KPI, D09 OKR, D10 Performance, D11 Task/Workload, D12 Meeting, D13 Calendar | Họp, quyết định, task, OKR/KPI |
| `idp` | `idp` | D03 Data Capture & IDP, D14 Knowledge | Pipeline tài liệu, review, Action Registry |
| `ai_core` | `ai` | D26 AI Platform, D27 CEO Assistant | 13 thành phần §2; Tool Registry, autonomy, chi phí |

> **Khác `main`:** `main`/v2.1 làm 6 domain + 5 trụ F.O.C.U.S; AI-EOS bám BRD đầy đủ (28 domain, 7 role + AI Agent) nhưng **chỉ đặc tả P0** (20 domain), P1/P2 vào backlog (09). Bảng ánh xạ cột role/kênh/autonomy ở §12 skeleton.

## 2. D26 — AI Platform: 13 thành phần (BRD §11.1)

Mọi tương tác của AI với dữ liệu và hành động đều đi qua tool đã đăng ký, được kiểm quyền, giới hạn theo Autonomy Level và ghi audit (BRD §11). 13 thành phần (đề xuất mã `AIC-01..14` — cấp ở file này theo §12bis skeleton):

| Mã | Thành phần | Trách nhiệm | Mô tả spec-level P0 |
|---|---|---|---|
| AIC-01 | AI Gateway | Điểm vào duy nhất; xác thực, rate limit, ngân sách, lọc dữ liệu nhạy cảm | Cổng vào mọi request AI (chat, event-driven, batch). Xác thực JWT, rate limit theo người/tenant, kiểm ngân sách AI (FR-AIQ-05) trước khi nhận; chạy PII filter (bỏ dữ liệu mức 4, thay mức 3 bằng mã) trước khi chuyển xuống. Nhất quán P08. |
| AIC-02 | AI Orchestrator | Hiểu ý định, lập kế hoạch, chọn agent, phối hợp nhiều agent | Nhận intent, lập kế hoạch bước, chọn agent P0 phù hợp; người dùng chỉ nói chuyện với **một** Assistant, orchestrator điều phối ngầm. P0: single-agent + routing đơn giản; điều phối multi-agent sâu để phase sau. |
| AIC-03 | Agent Runtime | Chạy agent, quản lý trạng thái tác vụ dài, retry, timeout | Thực thi vòng đời một lượt agent: giới hạn ≤8 tool call/lượt, timeout 30s/lượt + 5s/tool, retry provider; lưu trạng thái cho tác vụ dài (briefing, report). Tác vụ không người hỏi chạy dưới danh tính service agent (quyền hẹp nhất). |
| AIC-04 | Model Gateway | Định tuyến model theo tác vụ/chi phí/phân loại; fallback; **không khóa vendor; on-premise** | Xem §4. Mọi call LLM/STT/embedding đi qua đây; định tuyến theo tác vụ × chi phí × mức phân loại; fallback khi model chính lỗi (NFR-AV-03); log `ENT-ModelCallLog`. |
| AIC-05 | Prompt & Instruction Mgmt | Quản lý phiên bản prompt, test trước phát hành, rollback | Lưu prompt/instruction có phiên bản; chạy bộ test chuẩn (Evaluation) trước khi phát hành phiên bản mới; rollback được. P0: lưu version + gate test (FR-AIQ-02). |
| AIC-06 | Tool Registry | Danh mục tool + schema, quyền, risk level | Xem §2.1. Nguồn duy nhất khai báo năng lực AI; 13 metadata bắt buộc/tool; chỉ dùng `TOOL-*` đã đăng ký (cấp ở 10). |
| AIC-07 | Knowledge Retrieval | Tìm kiếm ngữ nghĩa + graph; **lọc theo quyền trước khi đưa vào model** | Tìm tài liệu/knowledge theo ngữ nghĩa (vector) + quan hệ; áp quyền + data scope người hỏi **TRƯỚC** khi đưa đoạn trích vào context (least privilege). Đoạn ngoài scope không vào prompt. |
| AIC-08 | Memory | Bộ nhớ hội thoại / người dùng / doanh nghiệp; xem & xóa được | Lưu ngữ cảnh hội thoại, sở thích người dùng, bộ nhớ doanh nghiệp (BO-07). Chủ thể dữ liệu xem & xóa được (NĐ 13/2023). Công nghệ store chốt ở đợt code (OQ-07-02). |
| AIC-09 | Document AI Engine | Phân loại, OCR, trích xuất cấu trúc cho Data Capture | Phục vụ D03 IDP: phân loại 14 loại tài liệu, OCR (kiểm `text_layer_exists` trước), trích xuất theo Extraction Schema; mỗi field `{ value, confidence, source_location }`, không bịa (AI-R11). IDP **không** có tool calling. |
| AIC-10 | Policy Engine | Đánh giá quyền, data scope, Autonomy Level mỗi tool call | Trung tâm enforcement: mỗi tool call tính quyền hiệu lực = quyền agent ∩ quyền người dùng (§3), xác định Autonomy Level theo tool × role × ngưỡng giá trị, default deny; quyết định ghi vào audit. |
| AIC-11 | Approval Engine | Tạo & theo dõi yêu cầu phê duyệt cho hành động AI | Khi Policy Engine yêu cầu duyệt (L2, hoặc L3 vượt ngưỡng), tạo `ENT-ApprovalRequest`, định tuyến tới người duyệt theo Approval Matrix (BRD §17.3), theo dõi trạng thái/SLA/escalate. AI **không** tự gọi tool APPROVAL. |
| AIC-12 | Audit Engine | Ghi bất biến mọi tool call, input, output, quyết định | Ghi append-only `ENT-AIAudit`/`ENT-AIToolCall`: Who/What/When/Why/Source/Data/Action/Result/Approval + (model & version, agent, prompt version, autonomy level, tool input/output, decision, confidence, chi phí, người được phục vụ). Giữ ≥2 năm (NFR-AUD-01). |
| AIC-13 | Evaluation Engine | Bộ test chuẩn, đo chất lượng, phản hồi, hiệu chỉnh confidence | Bộ test chuẩn/agent (FR-AIQ-02), nhận phản hồi đúng/sai (FR-AIQ-04), hiệu chỉnh confidence với kết quả thực tế (FR-AIQ-03); là gate nâng Autonomy Level của một tool. |
| AIC-14 | Event Listener | Nhận event nghiệp vụ để AI chủ động quan sát & cảnh báo | Tiêu thụ domain event qua event backbone (§1.1) để AI chủ động quan sát ngưỡng (KPI dưới mục tiêu, OKR at-risk, dòng tiền) và tạo insight/cảnh báo không cần người hỏi (AI-R12, UC-03/04). |

> **Khác `main`:** `main`/v2.1 làm ModelGateway + Tool Registry + autonomy + audit nhưng **hoãn** Orchestrator/multi-agent/Memory/Prompt versioning/Evaluation đầy đủ (DEC-150). AI-EOS gồm đủ danh sách BRD (AI Gateway…Event Listener; BRD gọi "13 thành phần", danh sách tách Document AI Engine → đánh số AIC-01..14) — MVP làm P0, điều phối sâu theo phase.

### 2.1. Tool Registry (BRD §11.2) — metadata & ràng buộc

Mọi năng lực nghiệp vụ expose dưới dạng **tool** đăng ký trong registry; AI chỉ gọi tool đã đăng ký (AI-R02, không chạm DB trực tiếp). Mã `TOOL-*` cấp ở 10; file này chốt **13 thuộc tính metadata bắt buộc**:

`name` · `description` · `input_schema` · `output_schema` · `permission` (`<domain>:<action>`) · `risk_level` · `data_scope` · `data_classification` · `autonomy_level` mặc định · `approval_required` · `reversible` · `audit_required` · `cost_estimate` · `owner`.

- Ví dụ tool P0 (BRD §11.2): `get_financial_summary`, `get_kpi_status`, `get_okr_status`, `get_overdue_tasks`, `get_health_metrics`, `search_documents`, `get_source_document` (READ); `create_task`, `assign_task`, `update_task`, `record_kpi_measurement`, `commit_extraction`, `create_calendar_event`, `send_notification` (WRITE/EXECUTION); `request_approval`, `generate_report`, `log_decision`.
- **Ràng buộc:** thêm `TOOL-*` mới → cập nhật skeleton + 10 trước, không tự thêm (P06).

### 2.2. Phân loại tool (BRD §11.3) & Agent P0 (BRD §11.4)

| Loại tool | Ý nghĩa | Autonomy mặc định | Ví dụ |
|---|---|---|---|
| READ | Không thay đổi dữ liệu | L0 | `get_sales_pipeline`, `get_kpi_status`, `extract_document` |
| WRITE | Thay đổi dữ liệu nội bộ | L2/L3 theo ngưỡng | `create_task`, `update_task`, `commit_extraction` |
| APPROVAL | Thực hiện quyền phê duyệt | — (AI **không** tự gọi) | `approve_budget`, `approve_hiring` |
| EXECUTION | Tác động ra bên ngoài | L2 (xác nhận người gửi) | `send_email`, `send_customer_message`, `create_calendar_event` (khách ngoài) |

**Agent P0 (`AGT-*` đề xuất — cấp ở 10/skeleton):** CEO Agent (tổng hợp liên domain, briefing — D27), Data Capture Agent (D03), Performance Agent (KPI/OKR/check-in — D08/09/10), Task Agent (D11), Meeting Agent (D12), Reporting Agent (D28); Finance/Sales Agent (Lite). Orchestrator chọn agent; người dùng chỉ thấy **một** Assistant. Agent P1/P2 (HR/Product/Engineering/Procurement/Strategy/Risk/Governance) vào backlog.

## 3. Luồng thực thi & quyền (BRD §11.5)

```text
User/Event → Intent Detection → Context Retrieval → Planning → Tool Selection
→ Authorization (Policy Engine) → Tool Calling → Result Validation → Reasoning
→ Recommendation → Approval (theo Autonomy) → Execution → Verification → Audit
```

- **AI không vượt quyền người được phục vụ:** quyền hiệu lực = **giao của quyền agent ∩ quyền người dùng**.
- Ví dụ: CEO AI → Finance R/W, HR R, Strategy R/W; Employee AI → cá nhân R/W, task team R, Finance DENY.
- AI chạy theo event/lịch (không có người hỏi) dùng **danh tính service của agent**, quyền hẹp nhất.

### 3.1. Mô tả từng bước luồng + điểm kiểm quyền (Policy Engine, AIC-10)

| Bước | Hành vi | Ràng buộc / nguyên tắc |
|---|---|---|
| Intent Detection | Phân tích câu hỏi/event thành ý định + thực thể (tác vụ, domain, khoảng thời gian). | Hỗ trợ câu trộn VI+EN (NFR-UX-01). |
| Context Retrieval | Knowledge Retrieval (AIC-07) + Memory (AIC-08) lấy ngữ cảnh. | **Lọc theo quyền người hỏi TRƯỚC** khi đưa vào context; đoạn ngoài scope không vào prompt. |
| Planning | Orchestrator (AIC-02) lập chuỗi bước, chọn agent. | ≤8 tool call/lượt; nếu vượt → cắt + báo `truncated`. |
| Tool Selection | Chọn tool từ Tool Registry (AIC-06) theo intent. | Lọc tool theo `permissions[]` người hỏi **trước** khi gửi model (least privilege). |
| **Authorization** | **Policy Engine (AIC-10)** đánh giá quyền hiệu lực = agent ∩ người dùng, data scope, Autonomy Level. | **Default deny**; không nhận role/permission từ body; dữ liệu mức 4 bị mask kể cả trong prompt. |
| Tool Calling | Tool chạy in-process qua service layer bằng `Principal` dựng từ JWT người hỏi. | Không HTTP loopback, không token hệ thống; tool ghi cần cả `ai:write` + `<domain>:write`. |
| Result Validation | Kiểm kết quả tool khớp schema; grounding mọi con số. | Số không có nguồn (`tool_result`/`MetricValue`) bị gỡ + warning (P05/FR-AIQ-01). |
| Reasoning → Recommendation | Dựng insight 9 phần (Observation→…→Action). | Giải thích được (P07); mọi số có `SourceRef`. |
| **Approval** | Theo Autonomy Level: L2 → action card chờ xác nhận; L3 vượt ngưỡng → Approval Engine (AIC-11). | Theo Approval Matrix BRD §17.3; AI không tự gọi tool APPROVAL. |
| Execution | Thực thi hành động `ACT-*` qua Action Registry, một transaction + phát event. | L3 có nút hoàn tác ≥24h khi bản chất cho phép. |
| Verification → Audit | Verify kết quả (AI-R10) + ghi audit bất biến (AIC-12). | Audit đủ trường AI (model/version, prompt version, autonomy level, tool I/O, confidence, chi phí). |

### 3.2. Autonomy enforcement (BRD §11.6, §17.3) — áp dụng P0

Autonomy Level cấu hình theo **tool × vai trò × ngưỡng giá trị**; Policy Engine áp ở bước Authorization:

| Level | AI được làm | Enforcement P0 |
|---|---|---|
| L0 Inform | Chỉ đọc & trả lời | Mặc định mọi tool READ; không ghi. |
| L1 Suggest | Đề xuất, người tự làm | Hiển thị gợi ý ("AI gợi ý"); không chạm dữ liệu. |
| L2 Draft & Confirm | AI chuẩn bị, người xác nhận | Action card chờ xác nhận ("AI soạn"); mặc định cho ghi tài chính & giao tiếp ngoài. |
| L3 Act & Notify | AI tự làm trong policy, báo lại, hoàn tác được | Thực thi + notify ("AI đã làm"); **undo ≥24h**; mặc định task/lịch/nhắc việc nội bộ. |
| L4 Autonomous | Tự làm, chỉ audit | **Khóa ở MVP** (phase 5). Kill switch bật → L3 hạ thành L2. |

- **Ngưỡng ví dụ:** chi phí < 5 triệu → L3; ≥ 5 triệu → L2 + quản lý duyệt (BRD §11.6).
- **Ghi dữ liệu trọng yếu** (tiền, MST, số tài khoản, lương) luôn L2 + người duyệt bắt buộc.
- **AI không tự quyết về con người** (tuyển, sa thải, lương, điểm đánh giá) — BRD §17.1.11/17.3: không cho phép.
- Nâng Autonomy Level một tool cần số liệu chất lượng từ Evaluation Engine (AIC-13) + duyệt của Admin + chủ domain.

### 3.3. AI Operating Loop (BRD §17.5)
`OBSERVE → UNDERSTAND → REASON → RECOMMEND → APPROVE → ACT → VERIFY → LEARN → OBSERVE`

Vòng LEARN đưa phản hồi đúng/sai (FR-AIQ-04) về Evaluation Engine để hiệu chỉnh confidence và chất lượng; OBSERVE do Event Listener (AIC-14) cấp nguồn (event nghiệp vụ) cho quan sát chủ động.

## 4. Model Gateway (AIC-04, BRD §11.1, FR-AIQ)

- Đa provider, **không khóa vendor**, hỗ trợ **model on-premise/local**; fallback khi model chính lỗi (NFR-AV-03). Retry 5xx/timeout/429 vài lần rồi chuyển provider; lỗi 4xx nội dung không fallback.
- Định tuyến theo **tác vụ × chi phí × mức phân loại dữ liệu** (02 §5): Nội bộ/Công khai → cloud; **Mật → local-only**; **Tuyệt mật → không LLM**.
- Mọi call đi qua gateway; log `ENT-ModelCallLog` (token/chi phí/provider/fallback/`prompt_sha256` — **không lưu prompt thô**).
- Giới hạn lượt gọi: temperature thấp, ≤2048 output token, 30s/lượt, ≤8 tool call/lượt, 5s/tool; quá ngân sách tháng → chặn (`AI_QUOTA_EXCEEDED`, FR-AIQ-05).
- **Model governance (BRD §17.1.7):** chỉ dùng model trong danh mục đã duyệt; đánh giá (Evaluation) trước khi đưa model mới vào dùng. Thêm provider → DEC blocking.

## 5. Chất lượng & chi phí AI (BRD §11.7)

- **FR-AIQ-01 — Grounding bắt buộc:** mọi con số AI đưa ra phải đến từ tool call hoặc tài liệu có trích dẫn; con số không nguồn bị chặn hoặc gắn nhãn "ước tính" (P05).
- **FR-AIQ-02 — Bộ test chuẩn:** mỗi agent + loại câu hỏi cốt lõi có bộ test; chạy lại trước mọi đổi model/prompt; **không phát hành nếu chất lượng giảm** (gate của AIC-05/AIC-13).
- **FR-AIQ-03 — Confidence hiệu chỉnh:** confidence hiệu chỉnh với kết quả thực tế; chưa đủ dữ liệu → dùng thang Cao/Trung bình/Thấp kèm lý do thay vì %.
- **FR-AIQ-04 — Phản hồi:** mọi câu trả lời/khuyến nghị có nút đúng/sai + lý do → Evaluation Engine (vòng LEARN §3.3).
- **FR-AIQ-05 — Ngân sách AI:** trần theo tenant/phòng ban/agent; **cảnh báo ở 80%**; báo cáo chi phí AI/quyết định được hỗ trợ và /tài liệu xử lý (NFR-COST-01).
- **FR-AIQ-06 — Chống prompt injection:** phát hiện & chặn prompt injection từ mọi nguồn ngoài (tài liệu, email, web, dữ liệu tích hợp); nội dung ngoài bọc delimiter, coi là **data** không phải lệnh (P08/BRD §17.1.8).

## 6. NFR (BRD §16) — baseline MVP

Các con số là baseline MVP, xác nhận ở SRS + kiểm thử tải. Mỗi NFR một dòng, nhóm theo chủ đề:

### 6.1. Bảo mật (SEC)
- **NFR-SEC-01 Xác thực:** SSO (Google, Microsoft, SAML/OIDC); MFA bắt buộc với Admin, CEO, Finance.
- **NFR-SEC-02 Phân quyền:** RBAC + ABAC + data scope + field-level; AI authorization & tool permission kiểm ở **mọi** lần gọi.
- **NFR-SEC-03 Mã hóa:** TLS 1.2+ khi truyền; AES-256 khi lưu; khóa qua KMS; khóa do khách hàng quản lý (P1).
- **NFR-SEC-04 Cách ly:** tenant isolation cho dữ liệu/file/vector index/bộ nhớ AI; pentest trước go-live.
- **NFR-SEC-05 API:** API authentication, rate limiting, ghi log truy cập.
- **NFR-SEC-06 File tải lên:** quét mã độc, kiểm loại file thật (magic bytes), cách ly file lỗi.

### 6.2. Hiệu năng & quy mô (PERF, SCALE)
- **NFR-PERF-01 Giao diện:** thao tác chuẩn p95 < 2s; tải dashboard p95 < 3s.
- **NFR-PERF-02 AI hội thoại:** token đầu < 2s (streaming); câu hỏi nhiều tool trả trong 30s p90, hiển thị tiến trình.
- **NFR-PERF-03 Xử lý tài liệu:** tài liệu ≤ 5 trang có kết quả p95 ≤ 60s; bất đồng bộ, thông báo khi xong.
- **NFR-PERF-04 Thông lượng:** ≥ 1.000 trang/giờ/tenant ở MVP, mở rộng ngang.
- **NFR-PERF-05 Quy mô:** MVP 50 tenant × 1.000 user; kiến trúc mở tới 10.000 user/tenant.

### 6.3. Độ tin cậy & khả dụng (AV)
- **NFR-AV-01 Khả dụng:** ≥ 99,9% core (≤ 43 phút gián đoạn/tháng).
- **NFR-AV-02 Phục hồi:** RPO ≤ 15 phút, RTO ≤ 4 giờ; sao lưu hằng ngày, giữ 30 ngày, diễn tập khôi phục hằng quý.
- **NFR-AV-03 AI dự phòng:** model chính lỗi → tự chuyển model dự phòng; nghiệp vụ cốt lõi vẫn làm thủ công khi AI tắt (P10 Graceful Degradation).

### 6.4. Dữ liệu & lưu trữ (DATA)
- **NFR-DATA-01 Lưu trữ:** cấu hình vùng lưu trữ; tùy chọn lưu & xử lý tại Việt Nam.
- **NFR-DATA-02 Thời hạn lưu:** theo loại dữ liệu & quy định (chứng từ kế toán, dữ liệu cá nhân, ghi âm); xóa tự động khi hết hạn.

### 6.5. Audit (AUD)
- **NFR-AUD-01 Audit:** log bất biến, giữ tối thiểu 2 năm (cấu hình được), tìm kiếm & xuất được.

### 6.6. Trải nghiệm (UX)
- **NFR-UX-01 Ngôn ngữ:** giao diện & AI VI + EN; AI hiểu câu trộn hai ngôn ngữ.
- **NFR-UX-02 Thiết bị:** web responsive; mobile (PWA/app) cho chụp tài liệu, duyệt, check-in, hỏi AI.
- **NFR-UX-03 Khả năng truy cập:** WCAG 2.1 AA cho màn hình chính.
- **NFR-UX-04 Dễ học:** nhân viên mới hoàn thành tác vụ cơ bản sau ≤ 30 phút hướng dẫn.

### 6.7. Tích hợp, giám sát, chi phí (INT/OBS/COST)
- **NFR-INT-01 Tích hợp:** mọi năng lực có API công khai có phiên bản; webhook cho sự kiện (P02).
- **NFR-OBS-01 Giám sát:** theo dõi độ trễ, lỗi, chi phí AI, độ chính xác trích xuất theo thời gian thực; cảnh báo vận hành.
- **NFR-COST-01 Chi phí AI:** ngân sách trần theo tenant; chi phí AI/user/tháng theo dõi & nằm trong biên lợi nhuận gói bán.

## 7. Secret & cấu hình
Mọi cấu hình qua config service (fail-fast khi thiếu biến bắt buộc); không hard-code/commit secret; log filter che khóa chứa `KEY|SECRET|PASSWORD|TOKEN`; JWT ký khóa riêng (RS256 nếu tái dùng nền `main` — chỉ `auth` đọc private key); PII filter trước mọi call model (bỏ mức 4, thay mức 3 bằng mã). Tách bạch routing **build-agent** và routing **runtime** (ModelGateway) — không dùng chung key. (Chi tiết env chốt khi code hóa — R-DEC-09.)

## 8. Open questions
- OQ-07-01: Modular Monolith vs tách service cho Agent Runtime/Orchestrator — ĐÃ CHỐT: R-DEC-06 — Modular Monolith, AI Platform là cụm module logic bên trong (không tách deployable).
- OQ-07-02: Memory store (conversation/user/enterprise) công nghệ — chờ chi tiết hóa ở đợt code (R-DEC-09).
- OQ-07-03: Chính sách model on-prem cho dữ liệu Mật (BRD §21.1 AI cloud) — chờ CEO (B3).

## Version
- **Version:** 0.3.0 (draft, Phase R2)
- **Last updated:** 2026-10-22
- **Maintainer:** @CyEyes
- **Change 0.3.0:** Mở rộng lên spec-level P0: thêm §1.1 Modular Monolith (R-DEC-06) + ánh xạ 11 module `main` + event backbone + `tenant_id` (R-DEC-07); mô tả chi tiết 13(/14) thành phần AI Platform (AIC-01..14) với mô tả spec-level mỗi thành phần; thêm §2.1 Tool Registry 13 metadata, §2.2 phân loại tool + agent P0; §3.1 mô tả từng bước luồng + điểm kiểm quyền Policy Engine, §3.2 Autonomy enforcement L0–L4 (áp dụng P0, L4 khóa); FR-AIQ-01..06 mô tả per-mã; NFR §16 tách theo 7 nhóm, mỗi NFR một dòng; secret/config bổ sung. Giữ 🟡 draft, không promote, không field-level DB / T-* / TC-* (R-DEC-09).
- **Change 0.2.0:** Chốt Q1–Q6 (R-DEC-05..10) — cập nhật trạng thái quyết định, đóng OQ liên quan; phạm vi docs-first P0.
- **Change 0.1.0:** Viết lại 07 theo AI-EOS — kiến trúc 3 hệ thống + Tool Layer, D26 AI Platform 13 thành phần, luồng thực thi & quyền (agent ∩ người), AI Operating Loop, Model Gateway đa provider + on-prem, chất lượng/chi phí AI (FR-AIQ), NFR baseline đầy đủ, secret/config.
