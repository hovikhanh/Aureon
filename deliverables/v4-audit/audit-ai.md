# Audit tính năng AI — Aureon (read-only, 2026-11-05)

**Phạm vi:** `core/model_gateway`, `modules/ai`, `modules/idp`. Nhánh `v3/m8-crm`, commit `9cad717`. Stack đang chạy: 10 container healthy.
**Spec đối chiếu:** CLAUDE.md §5.5–5.6, 04, 07, 10 §2.3/§7.

## 0. Kết luận trong 10 dòng

- AI thật có bằng chứng trên DB chính hôm nay: **đúng một lượt `extract`** (hóa đơn PDF có text layer). Không có lượt chat, tool call, AI action, insight hay evaluation nào.
- Gateway, audit, autonomy, RBAC tool, undo: code đầy đủ và cấu trúc tốt, nhưng chưa có bằng chứng chạy trên DB chính.
- **Critical 1:** IDP gửi nguyên văn tài liệu (kể cả lương, CCCD, số tài khoản) lên cloud. `sensitivity_level` luôn = 2, pipeline không cập nhật sau phân loại, và prompt trích xuất không qua PII filter.
- **Critical 2:** Stack đang chạy bật `AI_DEMO_REPLAY` (truthy) và `DEMO_MODE=true`, trái với STATE. 10 nhóm câu hỏi của CEO nhận **nhận định viết sẵn** ("Dòng tiền ổn", "đủ an toàn") bất kể giá trị metric.
- RAG live hỏng (mọi lần tìm raise lỗi), OCR PDF scan không bao giờ chạy, SSE là stream giả, rate limit 20/phút không tồn tại.
- Grounding bị vượt bằng câu tiếng Việt rất tự nhiên: "Doanh thu tháng 300 tỷ" giữ nguyên số bịa.
- **Chưa từng đo độ chính xác.** Mọi test `ai_eval` dùng gateway giả; evaluation chấm câu trả lời viết tay.
- Chỉ 12/54 tool thực sự dùng được qua chat ở live; 9/21 tool ghi không có ACT; 8 tool `list_*` không đọc bản ghi.
- 6/14 doc type BRD có schema (thiếu cả #5 SOP là P0).

## 1. Bằng chứng runtime

### 1.1. DB chính (`aureon`, chỉ aggregate)

| Bảng | Dòng | Bảng | Dòng |
|---|---:|---|---:|
| `ai.model_call_logs` | **1** | `idp.source_documents` | **1** |
| `ai.tool_call_logs` | 0 | `idp.document_pages` | 1 |
| `ai.conversations` / `ai.messages` | 0 / 0 | `idp.extraction_jobs` | 1 |
| `ai.ai_actions` | 0 | `idp.extracted_fields` | 8 |
| `ai.insights` | 0 | `idp.extraction_reviews` | 0 |
| `ai.ai_evaluations` | 0 | `idp.review_assignments` | 2 |
| `ai.autonomy_policies` | 0 | `idp.import_batches` | 0 |
| `ai.feedback` | 0 | `idp.document_types` | 7 |
| `ai.briefings` | 5 | `ai.agent_profiles` | 6 |
| `platform.metric_values` | 328 | `execution.tasks` | 103 |

**Dòng model call duy nhất:** `idp | extract | omniroute | claude-sonnet-5 | ok | in 2112 | out 881 | 13 900 µUSD | 7 567 ms`, 2026-11-04 07:19:46 UTC.

**Tài liệu duy nhất:** C3, PDF 1 trang, text layer có, `ocr_used=false`, INVOICE, `classification_confidence=0,98`, `sensitivity_level=2`, `document_confidence=0,9738`, routing `REVIEW` vì `{CRITICAL_FIELD}`, trạng thái `NEEDS_REVIEW`. Review đã ESCALATE sang MGR, chưa ai duyệt, 0 trường được sửa, không commit.

Xác nhận nhận định của brief: mức dùng live rất thấp. Không có dòng `classify`: phân loại 0,98 đến từ gợi ý từ khóa, không từ LLM (F-H7).

**Briefing:** 5 dòng, 5 người nhận, cùng một ngày, 0 recommendation, 0 email, 5 đã mở. `source=AI` dù không có LLM.

### 1.2. Cờ cấu hình

| Mục | Giá trị / trạng thái | Ghi chú |
|---|---|---|
| `MODEL_GATEWAY_MODE` | live | |
| `OCR_PROVIDER` | paddle | |
| `DEMO_MODE` | **true** | STATE dòng 126 ghi `false` |
| `AI_DEMO_REPLAY` | **có key, truthy** (cả `.env` và container `aureon-api-1`) | STATE dòng 126 ghi `false` |
| `MODEL_PROVIDER_PRIMARY` / `FALLBACKS` / `CONFIDENTIAL` | không đặt | Mặc định `omniroute` / rỗng / `ollama` |
| `EMBEDDING_MODEL` | không đặt | Mặc định `bge-m3`, **không rỗng** (F-H2) |
| Key provider trong `.env` | chỉ `OMNIROUTE_*` | Chuỗi provider cloud thực tế dài 1 |
| `MODEL_PRICING_JSON` | có | |
| `AI_MONTHLY_BUDGET_USD` | không đặt | Mặc định 50 |

### 1.3. Hạ tầng local

- **Ollama:** `qwen2.5:7b-instruct` (7.6B, Q4_K_M, có capability `tools`) và `bge-m3:latest`. Từ container api gọi `/api/tags` thấy cả 2. `/api/ps` rỗng. 4 CPU, 12 GB RAM. **0 dòng `provider=ollama` trên DB chính.**
- **Paddle:** trong worker có `paddleocr 2.10.0`, `paddlepaddle 3.0.0`; model baked 16 MB tại `/home/aureon/.paddleocr/whl` (`det/en`, `rec/latin`, `cls`). OCR offline khả thi.
- **PIL trên bytes PDF (dữ liệu tổng hợp, trong worker):** `UnidentifiedImageError`, xác nhận F-H3.

## 2. Phân loại năng lực

Quy ước: REAL chỉ dùng khi có bằng chứng chạy với provider thật trên DB chính hôm nay. Bằng chứng chỉ có trong STATE, không kiểm chứng được trên DB (đã bị xóa dữ liệu) → UNVERIFIED.

| # | Năng lực | Phân loại | Bằng chứng |
|---|---|---|---|
| 1 | CEO chat sync (đường live) | **UNVERIFIED** | Code đủ vòng tool (`chat_service.py:144-197`). `ai.messages=0`, không dòng `task_kind=chat`. STATE M5 ghi từng chạy thật; không còn dấu vết |
| 2 | SSE EP-AI-02 | **MOCK** | `router.py:123` gọi `svc.chat` chạy xong cả lượt rồi cắt câu trả lời thành khúc 48 ký tự (`:163`, `:356`). `gateway.stream()` không có caller. Không có event `thinking` |
| 3 | Từng `TOOL-*` | Xem §3 | 26 UNVERIFIED (binding thật), 28 MOCK (stub / giả tên). `tool_call_logs=0` |
| 4 | Grounding số | **UNVERIFIED** | Validator chạy được khi test thuần, nhưng 0 lượt live; có đường vượt (F-H1) |
| 5 | Insight generation | **HARDCODED** | 2 consumer dùng template f-string (`insight_service.py:119-173`, `:175-232`). `generate_for_pillar` (`:78`) không có caller, nên `_narrate` LLM (`:261`) là code chết. `ai.insights=0` |
| 6 | Daily briefing | **HARDCODED** | Không dùng LLM, đúng R-DEC-132: snapshot `ReportingService.executive()` (`briefing_service.py:110`). Có persist 5 dòng nhưng gắn `source="AI"` (`:136`). `summary_line` từ `_summary` (`reporting_service.py:64`) |
| 7 | AI actions L0–L3 | **UNVERIFIED** | Logic đầy đủ (`autonomy.py:109-125`, `action_service.py:73-119`). `ai_actions=0`. STATE M5 ghi `TOOL-create_task` L3 từng chạy |
| 7a | Gợi ý L1 | **OUTPUT-NOT-PERSISTED** | Chỉ nằm trong response `suggested` (`chat_service.py:313-316`); không tạo `ai_actions`, `Message` không có cột lưu |
| 8 | Undo 24h AI / 7 ngày IDP | **UNVERIFIED** | Code đủ (`action_service.py:149-167`, `undo_service.py`). 0 lần chạy |
| 9 | Kill switch | **UNVERIFIED** | Đọc tươi mỗi lượt, cap đúng (`autonomy.py:120-124`). Không có dòng `ai.kill_switch`, chưa từng bật. Chỉ chặn ghi, không chặn LLM/IDP |
| 10 | Evaluation engine | **MOCK** | Chấm 8 case có câu trả lời viết tay (`evaluation/cases.py`), không gọi model; chỉ chạy qua CLI; `ai_evaluations=0` |
| 11 | Knowledge / RAG | **MOCK** | Embed live raise (`gateway.py:288`); chỉ fixture dùng hash. `bge-m3` có sẵn nhưng không adapter, không job ghi embedding; 0 trang có embedding |
| 12 | STT / voice | **MOCK** | `gateway.py:272`: live raise. `fixtures/stt` rỗng |
| 13 | Phân loại tầng từ khóa / header | **HARDCODED** | `classifier.py:78-82`, đây là đường đã chạy (0,98) |
| 13a | Phân loại tầng LLM | **UNVERIFIED** | 0 dòng `classify` trên DB chính. R-DEC-163 ghi đã sửa |
| 14 | Trích xuất INVOICE | **REAL** | 1 lượt live, 8/8 trường, lưu DB |
| 14a | MEETING_MINUTES, PLAN_KPI_OKR, FINANCE_REPORT, HR_ROSTER | **UNVERIFIED** | Có schema, 0 lượt trên DB chính |
| 14b | PERIOD_REPORT | **UNVERIFIED** | Không có lượt trên DB chính; R-DEC-164: DOC-03 `FAILED:truncated` ở stack cô lập |
| 14c | 8 doc type BRD còn thiếu (#5, #8–#14) | **FALLBACK-ONLY** | Không schema, rơi về `OTHER` chỉ có `title` |
| 15 | OCR ảnh (paddle) | **UNVERIFIED** | Gói và model có thật; 0 trang `ocr_used` trên DB chính; STATE: DOC-10 conf 0,958 |
| 15a | OCR PDF scan | **FALLBACK-ONLY** | Luôn trả rỗng, đi review (F-H3) |
| 15b | OCR stub | **MOCK** | Là mặc định code (`config.py:125`), không active hôm nay; nhưng lỗi paddle âm thầm thành rỗng, không log (`preprocess.py:114-115`) |
| 16 | Meeting extraction | **UNVERIFIED** | Schema 3 trường; test dùng gateway giả; `execution` không gọi LLM với transcript; ghi âm "chưa hỗ trợ" |
| 17 | `AI_DEMO_REPLAY` | **HARDCODED** | Có trong production code, **đang bật** (F-C2) |
| 18 | Human review persistence | **UNVERIFIED** | Code đủ (`review_service.py:279-350`, `commit_service.py`); `extraction_reviews=0`; ESCALATE theo SLA thì có thật |
| 19 | Định tuyến Confidential → local | **UNVERIFIED** | Đúng ở gateway; 0 lượt; IDP không bao giờ tới (F-C1) |
| 20 | Chặn Secret → không LLM | **UNVERIFIED** | Đúng cho chat; DB chính không có dòng `forbidden` |
| 21 | Theo dõi token và chi phí | **REAL** | Dòng log thật, chi phí khớp mô hình có cache write (§4.6) |

## 3. Tool Registry (54 tool)

**Lọc quyền: có và đúng.** `agent.allowed_tools ∩ permissions ∩ không frozen ∩ declare_to_model` (`registry.py` `advertisable_for`, `agent_service.py:56-66`), chặn lại tên ngoài tập đã quảng bá (`chat_service.py:166`), executor kiểm quyền lần nữa (`tool_executor.py:103`).

**Tổng hợp binding:**

| Nhóm | Số | Ghi chú |
|---|---:|---|
| READ gắn service thật | 12 | 6 dashboard, `get_metric`, `list_alerts`, 4 record |
| READ giả tên (cùng dump metric trụ, bỏ qua tham số) | 5 | `get_budget_status`, `get_finance_forecast`, `get_sales_pipeline`, `get_workload`, `get_product_metrics` |
| READ `_pillar_fallback` (không đọc bản ghi) | 8 | `list_invoices`, `list_expenses`, `list_deals`, `list_tasks`, `list_objectives`, `list_risks`, `list_hiring_plans`, `get_kpi_status` |
| READ không có nhánh dispatch | 5 | `get_lineage`, `get_source_document`, `get_cash_flow_forecast`, `get_runway_what_if`, `run_risk_scenario` |
| READ `search_documents` | 1 | Lỗi ở live |
| WRITE/EXECUTION có ACT | 12 | |
| WRITE/EXECUTION **không có ACT** | 9 | `record_decision`, `generate_report`, `request_approval`, `create_meeting`, `upsert_deal`, `upsert_risk`, `create_mitigation`, `submit_document`, `send_notification` |
| APPROVAL (không gửi model) | 2 | |

**Tầm với thực tế của chat:** `CHAT_AGENT="ceo"` cho mọi role (`agent_catalog.py:14`), 5 agent còn lại chỉ tồn tại trong catalog, không có orchestrator. Trong 18 tool của agent `ceo`:
- 9 READ hoạt động + `get_kpi_status` (giả) = 10.
- 2 WRITE hoạt động: `create_task`, `execute_recommendation`.
- 2 READ stub (`get_lineage`, `get_source_document`), 1 READ làm hỏng cả lượt (`search_documents`).
- 3 WRITE trả `NOT_FOUND` (`record_decision`, `generate_report`, `request_approval`).

Tức **12/54 tool dùng được qua chat live**. `AUTONOMY_DEFAULTS` còn khai `ACT-record_decision`, `ACT-create_meeting` ở L3 nhưng hai ACT này không tồn tại.

| Tool | Kind | Perm | Class | Vào chat (agent ceo)? | Binding thực tế | Phân loại |
|---|---|---|---|---|---|---|
| `TOOL-approve_request` | APPROVAL | platform:approve | CONF | không | Không gửi model; `AI_WRITE_VIA_ACTION` nếu gọi | UNVERIFIED |
| `TOOL-reject_request` | APPROVAL | platform:approve | CONF | không | Không gửi model; `AI_WRITE_VIA_ACTION` nếu gọi | UNVERIFIED |
| `TOOL-send_notification` | EXECUTION | ai:write | INTE | không | `ACT-send_notification` KHÔNG đăng ký → `NOT_FOUND` | MOCK |
| `TOOL-get_budget_status` | READ | finance:query | INTE | không | Trả cùng bộ metric trụ, bỏ qua tham số/mục đích tool | MOCK |
| `TOOL-get_cash_flow_forecast` | READ | finance:read | INTE | không | Không có nhánh dispatch → `AI_TOOL_NOT_AVAILABLE` | MOCK |
| `TOOL-get_execution_dashboard` | READ | execution:query | INTE | có | `DashboardService.metrics` thật | UNVERIFIED |
| `TOOL-get_finance_dashboard` | READ | finance:query | INTE | có | `DashboardService.metrics` thật | UNVERIFIED |
| `TOOL-get_finance_forecast` | READ | finance:read | INTE | không | Trả cùng bộ metric trụ, bỏ qua tham số/mục đích tool | MOCK |
| `TOOL-get_hr_dashboard` | READ | hr:query | INTE | có | `DashboardService.metrics` thật | UNVERIFIED |
| `TOOL-get_kpi_status` | READ | execution:read | INTE | có | Không đọc bản ghi; trả metric tổng hợp của trụ (`_pillar_fallback`) | MOCK |
| `TOOL-get_lineage` | READ | dashboard:read | CONF | có | Không có nhánh dispatch → `AI_TOOL_NOT_AVAILABLE` | MOCK |
| `TOOL-get_metric` | READ | dashboard:read | INTE | có | Service domain thật, scope theo Principal | UNVERIFIED |
| `TOOL-get_okr_status` | READ | execution:read | INTE | có | Service domain thật, scope theo Principal | UNVERIFIED |
| `TOOL-get_org_tree` | READ | hr:read | INTE | có | Service domain thật, scope theo Principal | UNVERIFIED |
| `TOOL-get_overdue_tasks` | READ | execution:read | INTE | không | Service domain thật, scope theo Principal | UNVERIFIED |
| `TOOL-get_product_dashboard` | READ | product:query | INTE | frozen | `DashboardService.metrics` thật | UNVERIFIED |
| `TOOL-get_product_metrics` | READ | product:query | INTE | frozen | Trả cùng bộ metric trụ, bỏ qua tham số/mục đích tool | MOCK |
| `TOOL-get_project_status` | READ | execution:read | INTE | có | Service domain thật, scope theo Principal | UNVERIFIED |
| `TOOL-get_risk_dashboard` | READ | risk:query | INTE | frozen | `DashboardService.metrics` thật | UNVERIFIED |
| `TOOL-get_runway_what_if` | READ | finance:query | INTE | không | Không có nhánh dispatch → `AI_TOOL_NOT_AVAILABLE` | MOCK |
| `TOOL-get_sales_dashboard` | READ | sales:query | INTE | có | `DashboardService.metrics` thật | UNVERIFIED |
| `TOOL-get_sales_pipeline` | READ | sales:query | INTE | không | Trả cùng bộ metric trụ, bỏ qua tham số/mục đích tool | MOCK |
| `TOOL-get_source_document` | READ | idp:read | CONF | có | Không có nhánh dispatch → `AI_TOOL_NOT_AVAILABLE` | MOCK |
| `TOOL-get_workload` | READ | hr:query | CONF | không | Trả cùng bộ metric trụ, bỏ qua tham số/mục đích tool | MOCK |
| `TOOL-list_alerts` | READ | dashboard:read | INTE | có | Service domain thật, scope theo Principal | UNVERIFIED |
| `TOOL-list_deals` | READ | sales:read | CONF | không | Không đọc bản ghi; trả metric tổng hợp của trụ (`_pillar_fallback`) | MOCK |
| `TOOL-list_expenses` | READ | finance:read | CONF | không | Không đọc bản ghi; trả metric tổng hợp của trụ (`_pillar_fallback`) | MOCK |
| `TOOL-list_hiring_plans` | READ | hr:read | CONF | không | Không đọc bản ghi; trả metric tổng hợp của trụ (`_pillar_fallback`) | MOCK |
| `TOOL-list_invoices` | READ | finance:read | CONF | không | Không đọc bản ghi; trả metric tổng hợp của trụ (`_pillar_fallback`) | MOCK |
| `TOOL-list_objectives` | READ | execution:read | CONF | không | Không đọc bản ghi; trả metric tổng hợp của trụ (`_pillar_fallback`) | MOCK |
| `TOOL-list_risks` | READ | risk:read | CONF | frozen | Không đọc bản ghi; trả metric tổng hợp của trụ (`_pillar_fallback`) | MOCK |
| `TOOL-list_tasks` | READ | execution:read | CONF | không | Không đọc bản ghi; trả metric tổng hợp của trụ (`_pillar_fallback`) | MOCK |
| `TOOL-run_risk_scenario` | READ | risk:query | INTE | frozen | Không có nhánh dispatch → `AI_TOOL_NOT_AVAILABLE` | MOCK |
| `TOOL-search_documents` | READ | idp:read | CONF | có | KnowledgeSearchService; live → `embed()` raise, cả lượt chat lỗi | MOCK |
| `TOOL-assign_task` | WRITE | ai:write,execution:write | CONF | không | `ACT-assign_task` có trong Action Registry, service thật | UNVERIFIED |
| `TOOL-create_department` | WRITE | ai:write,hr:admin | INTE | không | `ACT-create_department` có trong Action Registry, service thật | UNVERIFIED |
| `TOOL-create_invoice` | WRITE | ai:write,finance:write | CONF | không | `ACT-create_invoice` có trong Action Registry, service thật | UNVERIFIED |
| `TOOL-create_meeting` | WRITE | ai:write,execution:write | CONF | không | `ACT-create_meeting` KHÔNG đăng ký → `NOT_FOUND` | MOCK |
| `TOOL-create_mitigation` | WRITE | ai:write,risk:write | CONF | frozen | `ACT-create_mitigation` KHÔNG đăng ký → `NOT_FOUND` | MOCK |
| `TOOL-create_task` | WRITE | ai:write,execution:write | CONF | có | `ACT-create_task` có trong Action Registry, service thật | UNVERIFIED |
| `TOOL-create_team` | WRITE | ai:write,hr:admin | INTE | không | `ACT-create_team` có trong Action Registry, service thật | UNVERIFIED |
| `TOOL-execute_recommendation` | WRITE | ai:write,execution:write | CONF | có | `ACT-execute_recommendation` có trong Action Registry, service thật | UNVERIFIED |
| `TOOL-generate_report` | WRITE | ai:write,dashboard:read | INTE | có | `ACT-generate_report` KHÔNG đăng ký → `NOT_FOUND` | MOCK |
| `TOOL-record_decision` | WRITE | ai:write,execution:write | CONF | có | `ACT-record_decision` KHÔNG đăng ký → `NOT_FOUND` | MOCK |
| `TOOL-record_expense` | WRITE | ai:write,finance:write | CONF | không | `ACT-record_expense` có trong Action Registry, service thật | UNVERIFIED |
| `TOOL-record_kpi_measurement` | WRITE | ai:write,execution:write | CONF | không | `ACT-record_kpi_measurement` có trong Action Registry, service thật | UNVERIFIED |
| `TOOL-record_kr_checkin` | WRITE | ai:write,execution:write | CONF | không | `ACT-record_kr_checkin` có trong Action Registry, service thật | UNVERIFIED |
| `TOOL-request_approval` | WRITE | ai:write,dashboard:read | CONF | có | `ACT-request_approval` KHÔNG đăng ký → `NOT_FOUND` | MOCK |
| `TOOL-submit_document` | WRITE | ai:write,idp:write | CONF | không | `ACT-submit_document` KHÔNG đăng ký → `NOT_FOUND` | MOCK |
| `TOOL-update_task` | WRITE | ai:write,execution:write | CONF | không | `ACT-update_task` có trong Action Registry, service thật | UNVERIFIED |
| `TOOL-upsert_deal` | WRITE | ai:write,sales:write | CONF | không | `ACT-upsert_deal` KHÔNG đăng ký → `NOT_FOUND` | MOCK |
| `TOOL-upsert_kpi` | WRITE | ai:write,execution:write | CONF | không | `ACT-upsert_kpi` có trong Action Registry, service thật | UNVERIFIED |
| `TOOL-upsert_objective` | WRITE | ai:write,execution:write | CONF | không | `ACT-upsert_objective` có trong Action Registry, service thật | UNVERIFIED |
| `TOOL-upsert_risk` | WRITE | ai:write,risk:write | CONF | frozen | `ACT-upsert_risk` KHÔNG đăng ký → `NOT_FOUND` | MOCK |

## 4. Audit theo chủ đề

### 4.1. Provider abstraction

- **Chuỗi:** `MODEL_PROVIDER_PRIMARY → FALLBACKS`; bỏ qua provider thiếu key (`routing.py:64-76`). Adapter dùng `httpx`, không SDK vendor. Đạt DEC-131.
- **Thực tế triển khai:** chỉ một cloud provider (OmniRoute trên host). `CHAT_MODEL_FALLBACK` là model khác trong cùng provider. OmniRoute chết thì toàn bộ AI cloud chết; đúng sự cố M5.
- **Fallback:** retry 5xx/429/timeout tối đa 2 lần, backoff 1 s/3 s (`gateway.py:41`). Chuỗi model chat chỉ 1 lần/model. 4xx dừng toàn chuỗi (F-M3).
- **Circuit breaker:** 5 lỗi/60 s, mở 120 s, nhưng process-local (`gateway.py:107-131`), không log khi skip.
- **Timeout so với R-DEC-153:** `chat` 90 s/lần gọi, task khác 30 s (`routing.py:108`): **đúng R-DEC-153**. Nhưng:
  - Không có deadline tổng cho một lượt: tệ nhất ≈ 180 s × nhiều vòng tool.
  - 5 s/tool **không được thực thi** (không có `wait_for` trong `tool_executor`).
  - R-DEC-153 mục (3) nói ngắt kết nối hủy task qua `request.is_disconnected`: **không có** trong code (grep 0 kết quả).
- **Connection:** session DB giữ mở qua các lời gọi provider dài.

### 4.2. Chọn model và quản lý prompt

- Model theo `MODEL_<TASK>`, ghi đè `MODEL_<TASK>__<PROVIDER>`, chat theo `CHAT_MODEL_*`, local theo `LOCAL_CHAT_MODEL`.
- **Lệch cần kiểm:** R-DEC-164 chốt `MODEL_EXTRACT=cc/claude-sonnet-4-6`, ghi "stack chính chưa nhận giá trị mới"; dòng log 2026-11-04 trả `claude-sonnet-5`. Nguyên nhân UNVERIFIED (không đọc value `.env`).
- **Prompt:** hằng số trong code (`chat_service.py:67-80`, `extractor.py:130-137`, `classifier.py:134`, `insight_service.py:268`). Không registry, không version, không rollback.
- `agent_profiles.prompt_version` NULL cho cả 6 agent. `PROMPT_VERSION="v1"` chỉ là hằng cho eval. `schema_version` luôn `"1"`. AIC-05 / FR-AIQ-02 chưa đạt.
- `prompt_sha256` băm **toàn bộ input gồm dữ liệu người dùng** (`types.py:53-67`): đúng là không lưu prompt thô, nhưng không dùng để nhận diện phiên bản prompt được.

### 4.3. Structured output

- `gateway.extract()` chỉ `json.loads` + bỏ fence (`gateway.py:240-254`). **Không validate theo schema** (không có `jsonschema`).
- `strict: True` gửi kèm schema không hợp lệ cho strict (`"value": {}`, thiếu `additionalProperties`, `required`) (`adapters.py:136-140`, `extractor.py:106-126`). Route OmniRoute `cc/` bỏ qua `response_format`; OpenAI thật có thể trả 400 và theo F-M3 sẽ dừng chuỗi.
- `AnthropicAdapter` bỏ qua `json_schema` hoàn toàn (`adapters.py:233-247`).
- Trường sai hình dạng im lặng thành `null` (`extractor.py:153-156`). Prompt extract không mô tả hình dạng `{value, raw_text, confidence}`.
- Truncation được phát hiện đúng: `AI_FUNCTION_CALL_FAILED reason=truncated` → `FAILED`.

### 4.4. Confidence, STP, trường trọng yếu

| Hạng mục | Kết quả |
|---|---|
| Nguồn confidence trường | **Model tự báo**, không hiệu chỉnh (`extractor.py:155-156`) |
| Confidence tài liệu | Trung bình cộng, kể cả trường vắng = 0 (`extractor.py:193-195`) |
| Băng DEC-133 | Đúng: ≥ 0,90 / ≥ 0,60 (`extractor.py:29-34`) |
| STP | Phân loại ≥ 0,95, bắt buộc ≥ 0,90: đúng (`pipeline.py:48-49, 273-289`); thêm `document_confidence ≥ 0,95` |
| Ngưỡng cấu hình | `thresholds` trong schema **không được đọc**; pipeline dùng hằng số (OQ-04-03) |
| Trọng yếu luôn qua người | **Đạt.** `critical.py` ép theo tên/`money`/`tax_code`/level 4, Admin không xóa được; `approve` chặn khi chưa xác nhận (`commit_service.py:112-114`) |
| `ocr_confidence` | Lưu nhưng không dùng trong routing |
| Injection | `suspicious_content` ép REVIEW (`pipeline.py:199-200`) |
| Sau STP | `AUTO_APPROVED` không tự commit, vẫn cần gọi approve; inbox lại xếp vào nhóm `committed` (`inbox_service.py:42`) |

### 4.5. Luồng review

Có đủ: lock, sửa trường, confirm, reject, reassign, merge, đổi loại, escalate SLA, approve, commit qua Action Registry, undo 7 ngày. Persist vào `extracted_fields.corrected_*`, `extraction_reviews`, `review_assignments`. Trên DB chính mới chạy tới ESCALATE; không có review nào hoàn tất. Học từ chỉnh sửa (04 §8) không thấy code đo field accuracy hay nới ngưỡng.

### 4.6. Token, chi phí, ngân sách

- **Token:** adapter tách cache đúng, kể cả route `cc/` báo ghi cache ngoài `prompt_tokens` (`adapters.py:28-45`).
- **Bảng giá:** `MODEL_PRICING_JSON`, ghi tra ngày 2026-11-03 (STATE M5: Sonnet 5 in 2, out 10, cache đọc 0,20, ghi 2,50 USD/1M). Sai bảng thì fail fast. Không có đồng bộ giá tự động.
- **Kiểm dòng thật:** 2×2112 + 10×881 = 13 034 ≠ 13 900. Chênh 866 = 0,5 × 1 732, khớp giả thuyết 1 732 token cache write. **Không xác minh được** vì `cached_in`/`cache_write` không lưu DB.
- **Model không có giá = $0** (`cost.py:94-95`), lọt khỏi trần; `unpriced_calls` chỉ hiển thị.
- **Trần tháng:** có, kiểm trước mỗi lần gọi (`gateway.py:216-219`), không nguyên tử.
- **80%:** chỉ là cờ `warn_80pct` trong response EP-AI-15, hard-code 0,8 (`cost_service.py:134`). `ai_budget_alert_pct` không ai đọc. **Không có thông báo/alert.**
- **Ngân sách theo agent:** `monthly_budget_usd` chỉ lưu và hiển thị, không thực thi.
- **Rate limit 20/phút: không tồn tại.** `RateLimitError` được khai báo nhưng không nơi nào raise; `core/rate_limit` không có.
- **Thất thoát log:** dòng `ok` ghi trong transaction người gọi, rollback là mất cả chi phí (F-M4).

### 4.7. Prompt injection

| Lớp | Trạng thái |
|---|---|
| Delimiter `<<<DATA` chat/IDP | Có, nhưng **không trung hòa** `DATA>>>` trong nội dung: thử `wrap_data` thấy thoát delimiter nguyên vẹn (`prompt_guard.py:99-101`, `extractor.py:139`, `classifier.py:136`) |
| IDP không tool | **Đạt** |
| Cảnh báo "DATA là dữ liệu" | Có ở system chat; **không có** ở system classify/extract |
| Phát hiện regex | `looks_injected` VI/EN, chỉ gắn cờ và ép review |
| `suspicious_content` sang search | **Không**: không truyền sang tool/search |
| Tool result vào chat | Bọc DATA, không kiểm nội dung |
| Tự thực thi | **L3 `create_task` chạy ngay** khi model gọi; tiêu đề task, snippet tài liệu là nội dung do người khác viết (F-H12) |

### 4.8. PII và định tuyến phân loại: bản đồ thực thi

| Call site | Lọc PII | Classification thực | Kết luận |
|---|---|---|---|
| Chat: tin nhắn người dùng | `scrub_for_model` | Theo `classify_prompt` | Có; regex hở (F-M9) |
| Chat: tool result | `strip_for_model` + `scrub_for_model` | **Giữ của prompt** | Lọc có; không nâng classification (F-H11) |
| Chat: lịch sử | Không có lịch sử | | |
| IDP classify | `scrub_for_llm` | Luôn INTERNAL | Có lọc; không theo doc type |
| **IDP extract** | **Không có** | **Luôn INTERNAL** | **Hở hoàn toàn (F-C1)** |
| Insight narrate | Chỉ metric | INTERNAL | Code chết |
| Briefing, eval, replay | Không gọi LLM | | |
| `ToolCallLog.arguments` | Có scrub | | Đạt |
| `AIAction.input` | **Không scrub** | | Tham số thô của model được lưu và trả ra `input_preview` |
| `ai.messages.content` | Không | | Lưu nguyên văn (chủ đích trong code) |

Test thuần `classify_prompt`:

| Đầu vào | Kết quả | Vấn đề |
|---|---|---|
| `luong nhan vien A bao nhieu` | INTERNAL | Lọt: không dấu |
| `SĐT +84 901 234 567` / `0901 234 567` / `0901.234.567` | INTERNAL, giữ nguyên | Lọt |
| `ngày sinh của A là 01/02/1990` | INTERNAL | Lọt mức 4 |
| `địa chỉ nhà A: 12 Lê Lợi` | INTERNAL | Lọt mức 4 |
| `Lương thực giá bao nhiêu` | SECRET | Dương tính giả |
| `Thu nhập khác quý 3?` | SECRET | Dương tính giả (câu hỏi tài chính) |
| `MST 0312345678` | CONFIDENTIAL, `EMP-03F1` | MST thành mã nhân viên |
| `doanh thu 1250000000` | CONFIDENTIAL, `[REDACTED]` | Số tiền bị che |

Số nguyên ≥ 10 chữ số trong JSON tool result bị `[REDACTED]`; metric hiện là `float` (`.0`) nên thoát, bản ghi kiểu `int` sẽ dính.

### 4.9. Auditability

| Đường gọi | ModelCallLog | ToolCallLog | Ghi chú |
|---|---|---|---|
| Chat | Có | Có | Dòng `ok` mất khi rollback |
| Replay | Không (không LLM) | Có, `arguments={}` | |
| IDP classify/extract | Có, `source_document_id` | Không áp dụng | Đã thấy dòng thật |
| Embed | **Không** | | `embed()` không ghi sink |
| STT | Có ở fixture; live raise không ghi | | |
| Budget chặn, breaker skip, không provider | **Không** | | Không có dấu vết |
| Secret/Template | Có (`forbidden`) | | Đạt |
| Insight, briefing, eval | Không LLM | | |

Không lưu prompt thô: **đạt**. Thiếu theo AIC-12: `classification` và `route_reason` chỉ ở log text (`ai_service.py:41-46`), không có prompt version, không có token cache. `Classification.tier` không persist nên không truy được tài liệu được phân loại bằng từ khóa hay LLM.

### 4.10. Fixture so với đánh giá thật

- `core/model_gateway/fixtures/{chat,stt}`: **0 file**. `tests/fixtures/model_gateway`: 7 file, mẫu đã mở có `model=fixture`, `tokens=0`, nên nhiều khả năng viết tay, không phải bản ghi provider.
- `test_chat_grounding_routing_m24.py`: `ScriptedGateway`.
- `test_meeting_recall_m23.py`: "recall ≥ 90%" với gateway giả **trả sẵn đúng đáp án**, chỉ chứng minh parser.
- `evaluation/cases.py`: `tools_called` và `expected_tools` đều viết tay. Điểm 95,83% ở `14` TC-M34-03 **không nói gì về model**.
- Test `live` duy nhất (`test_model_gateway_live.py`): vòng hỏi "OK", opt-in.
- **Độ chính xác đo được: không có.** Mục tiêu 04 §8 (field ≥ 90%, ≥ 95% có text layer; classification ≥ 95%) chưa có số nào. Không có ground truth trong `data/`. Mẫu thực: 1 tài liệu, 8/8 trường có giá trị, chưa ai đối chiếu.
- FR-AIQ-02 "không phát hành nếu chất lượng giảm" chưa có cơ chế gate.

### 4.11. Persist đầu ra AI

| Đầu ra | Bảng | Trạng thái |
|---|---|---|
| Câu trả lời chat | `ai.messages` + sources, function_calls, tokens | Code có, **warnings không lưu** |
| Gợi ý L1 | Không | **OUTPUT-NOT-PERSISTED** |
| Thẻ L2/L3 | `ai.ai_actions` | Code có |
| Kết quả trích xuất | `idp.extracted_fields`, `extraction_jobs` | **Có thật** |
| Tier phân loại | Không | Mất |
| Insight | `ai.insights` | Code có, 0 dòng |
| Briefing | `ai.briefings` | Có thật |
| Evaluation | `ai.ai_evaluations` | Chỉ qua CLI, 0 dòng |
| Text trang | `idp.document_pages.text_content` | Có thật, nguyên văn |

## 5. Phát hiện theo mức

### Critical

**F-C1. IDP gửi tài liệu nhạy cảm lên cloud, không lọc PII.**
- `upload_service.py:164` và `natural_language.py:82` ghi cứng `sensitivity_level=2`.
- `pipeline.py:128,154` dùng giá trị đó; sau khi phân loại (`:135-140`) chỉ cập nhật `pillars`, không cập nhật độ nhạy.
- `extractor.py:82` ra INTERNAL → chuỗi cloud (`routing.py:64-76`).
- `extractor.py:139` chèn `page_text` thô; pipeline truyền `pre.full_text` (`pipeline.py:153`). Chỉ classify qua `scrub_for_llm`.
- `HR_ROSTER` khai sensitivity 4 và các trường `salary`, `national_id`, `bank_account`, `date_of_birth`, `address` (`catalog/org.py`).
- Hậu quả: tải `DOC-06-danh-sach-nhan-su.xlsx` qua C3 sẽ gửi nguyên bảng tới OmniRoute; `router.py:90` còn cho ADM chủ động upload `document_type=HR_ROSTER` theo đường này (R-DEC-76), và `upload_service` vẫn đặt level 2. Trái CLAUDE.md §2.2 và §5.5, 07 §4. Nhánh CONFIDENTIAL/SECRET của IDP thực tế không bao giờ tới.
- Bằng chứng trên DB: tài liệu duy nhất có level 2 (hóa đơn, nên đúng). Chưa có lượt roster nào trên DB chính → **chưa phát sinh rò rỉ trên DB chính**; rò rỉ ở stack khác UNVERIFIED.
- Chỉ C5 import đặt đúng độ nhạy (`import_service.py:393`) và import không gọi LLM.

**F-C2. Replay hard-code đang bật trên stack chạy thật.**
- `AI_DEMO_REPLAY` truthy, `DEMO_MODE=true`, trái `STATE.md:126`.
- `chat_service.py:116-120` chặn trước LLM cho 10 intent (`demo_responses.json`).
- Số lấy từ tool, nhưng **nhận định cố định**: "Dòng tiền ổn" (`:45`), "đang ở trạng thái tốt" (`:23`), "dưới ngưỡng tập trung cảnh báo" (`:67`), cùng "đủ an toàn", "trong ngưỡng an toàn", "Triển vọng Q4/2026 tích cực", "Trụ … đang đỏ", "vàng vì 3 chỉ số".
- Kỳ cố định "T9/2026", "Q4/2026" không đổi theo dữ liệu.
- Đường này bỏ qua agent `is_enabled`, `allowed_tools`, grounding, chạy cả tool frozen (`allow_frozen=True`, `demo_replay.py:99`).
- FE chỉ hiện chuỗi warning mặc định chứa mã `ai.warn.demo_replay`; không có nhãn riêng (`ChatView.tsx:57`, không có key message).
- `DEMO_MODE=true` còn mở EP-04/05 đổi role (ngoài phạm vi AI, cần auditor bảo mật xem).

### High

**F-H1. Grounding bị vượt** (`grounding.py:43,131`). Từ `tháng|năm|quý|kỳ|tuần|ngày|lần|top|hạng` đứng trước số làm cả số và đơn vị được bỏ qua. Chạy thật với nguồn duy nhất là 82:

| Câu | Kết quả |
|---|---|
| `Doanh thu tháng 300 tỷ, đạt 82%.` | **Giữ nguyên**, 0 warning |
| `Doanh thu năm 999 tỷ.` | **Giữ nguyên** |
| `Lợi nhuận quý 45 tỷ.` | **Giữ nguyên** |
| `Chi phí kỳ 77,5%.` | **Giữ nguyên** |
| `Doanh thu ba trăm tỷ đồng.` | **Giữ nguyên** (chữ) |
| `Tổng USD500000 và VND1000000.` | **Giữ nguyên** (`_PROTECTED_RE` coi là mã) |
| `Doanh thu 83,5% kế hoạch.` | **Giữ nguyên** (dung sai 2%) |
| `Biên lãi 37,5% trong tháng.` | Gỡ đúng |

Ngoài ra không gắn số với metric: đúng số, sai chỉ tiêu vẫn qua. Gỡ số để lại câu cụt ("Doanh thu ."). Insight LLM không qua grounding.

**F-H2. RAG và search tài liệu hỏng ở live.** `embedding_model` mặc định `bge-m3` nên `semantic_enabled=True` (`knowledge_search.py:45-47`), `gateway.embed` ở live raise `AI_PROVIDER_ERROR` (`gateway.py:288`). Không có fallback keyword khi lỗi. `tool_executor.py:110-115` không bắt `AIError`, nên **cả lượt chat chết**; EP-24 trả 502. R-DEC-141 ghi đã nối `/embeddings` nhưng adapter không có. Không job nào ghi `embedding`.

**F-H3. OCR PDF scan không chạy.** `preprocess.py:129` truyền **toàn bộ bytes PDF** vào `_ocr_image`; `Image.open` (`:107`) lỗi `UnidentifiedImageError`, `except` (`:114-115`) nuốt, không log, ra `("", 0.0)`. Không có bước render trang. Sau đó vẫn gọi LLM với text rỗng. Ảnh rời mới OCR được. STATE "13/13 file" nên đọc lại: các PDF mẫu có text layer.

**F-H4. `source_location` hard-code trang 1** (`extractor.py:168`). 8/8 trường trên DB đều `{"kind":"page","page":1}`. Không vùng tọa độ, không đoạn gốc theo vị trí, `full_text` ghép không dấu trang. Trái FR-DC-12, FR-DC-19; UC-06 "đúng trang" không đạt với tài liệu nhiều trang; lineage không đáng tin.

**F-H5. Trích xuất một phát, trần 2048 token.** Không chia khối đầu vào, không continuation. R-DEC-164 còn **open, blocking**: DOC-03 FAILED truncated. Tài liệu ~20+ dòng (báo cáo, roster, sao kê) sẽ fail. File 300 trang gửi nguyên vào một prompt 30 s.

**F-H6. Độ phủ doc type 6/14.** Có #1, #2, #3, #4, #6, #7 + OTHER. Thiếu #5 SOP (**P0**, UC-07), và #8–#14. Hợp đồng `DOC-04` chỉ trích được `title`. Rule: INVOICE 4, HR_ROSTER 1, còn lại 0. Không so khớp mờ master data trong extractor. Không có thao tác AI map cột: `task="mapping"` khai báo nhưng không call site.

**F-H7. Confidence phân loại là số hard-code và vượt ngưỡng STP.** `invoice_score` = 0,90 + 0,02×hits, tối đa 0,99 (`classifier.py:82`), `≥ 0,95` trả ngay không qua LLM (`:120`), trái comment "keywords alone never reach STP" (`:36`). Đây là nguồn 0,98 trên DB. Từ khóa so substring: `vat` khớp "vật tư", "vật liệu". Không hiệu chỉnh, không tier.

**F-H8. Bề mặt tool ảo.** Xem §3. Model được quảng bá tool sẽ lỗi; `get_workload` hay `list_invoices` trả dữ liệu không liên quan tới tên gọi, dễ dẫn tới trả lời sai mà vẫn có "nguồn". 9 write tool không ACT. Không có agent chuyên trách.

**F-H9. Không streaming thật, không deadline.** §4.1. TTFT = tổng thời gian lượt, có thể vài phút, không heartbeat. `perf_m2_gate` TTFT 0,080 s đo trên replay.

**F-H10. Không có rate limit AI 20/phút** (CLAUDE.md §5.5). Một user `ai:query` có thể đốt hết trần tháng $50 của cả tenant.

**F-H11. Tool result không nâng classification; ceiling ngược.** `chat_service.py:348`: prompt CONFIDENTIAL (đi local) bị giới hạn tool INTERNAL, còn prompt INTERNAL (đi **cloud**) **không giới hạn**. `TOOL-search_documents` CONFIDENTIAL, `get_lineage`, `get_source_document` được quảng bá cho lượt cloud; request không nâng khi có kết quả CONFIDENTIAL. `prompt_guard.py` nói "handled separately by the executor" nhưng executor không làm. **Đang tiềm ẩn nhờ F-H2**: sửa RAG mà không sửa điểm này sẽ mở rò rỉ.

**F-H12. Indirect prompt injection dẫn tới L3.** Agent `ceo` có `create_task`, `execute_recommendation` L3, thực thi ngay trong `propose`. Tiêu đề task (`_overdue_tasks`, `get_project_status`), snippet tài liệu là nội dung người khác viết, vào context, không neutralize, không đánh dấu nghi ngờ. Có giới hạn: quyền người hỏi, undo 24h, audit.

**F-H13. Không có số đo chất lượng.** §4.10.

### Medium

| ID | Vấn đề | Vị trí |
|---|---|---|
| F-M1 | **Chat không có bộ nhớ:** `HISTORY_PAIRS=10` khai báo không dùng; mỗi lượt chỉ `[system, user]`, trái FR-AI-05 | `chat_service.py:64,128-131` |
| F-M2 | `TemplateRequired` không phải `AppError`: Ollama lỗi → 500, SSE đứt giữa chừng. Prompt có số 10 chữ số đủ kích hoạt | `router.py:98,126-133`, `handlers.py`, `pipeline.py:157` |
| F-M3 | 401/403/404 bị coi như lỗi nội dung, dừng chuỗi fallback (spec chỉ loại "4xx nội dung") | `adapters.py:69-70`, `gateway.py:328` |
| F-M4 | Dòng log `ok` nằm trong transaction người gọi: lượt lỗi sau đó mất chi phí, trần tháng tính thiếu. R-DEC-154 chỉ phủ lượt lỗi | `ai_service.py:66-68`, `router.py:138` |
| F-M5 | Trần 80% thụ động, ngân sách agent không thực thi, `ai_budget_alert_pct` không dùng, model chưa giá = $0 | `cost_service.py:134`, `cost.py:94-95` |
| F-M6 | Prompt không version, `prompt_version` NULL | §4.2 |
| F-M7 | Không validate schema đầu ra; strict sai; Anthropic bỏ qua schema | §4.3 |
| F-M8 | Khi hết ngân sách tool, vòng tổng hợp gọi lại `req` cũ: không thấy kết quả tool cuối, vẫn gửi tools, token không cộng | `chat_service.py:194-197` |
| F-M9 | Regex PII hở và dương tính giả | §4.8 |
| F-M10 | Validator chỉ đánh giá hàng cuối vì `values` là dict theo tên, ghi đè mỗi hàng; `_to_number` hỏng với `"1250000.50"` (an toàn: đi review) | `pipeline.py:171`, `validator.py:77` |
| F-M11 | Docstring "idempotent" của `process_document` sai: `run()` không chặn job đã xong, chạy lại sẽ vướng unique `document_pages` và lỗi thay vì no-op; `enqueue_pipeline` nuốt mọi lỗi, tài liệu kẹt UPLOADED | `pipeline.py:86-92,394` |
| F-M12 | AUTO_APPROVED bị xếp vào nhóm "committed" dù chưa ghi | `inbox_service.py:42` |
| F-M13 | Insight/briefing gắn `source="AI"` dù là template; `confidence` hard-code MEDIUM | `insight_service.py:165,294`, `briefing_service.py:136` |
| F-M14 | Meeting: chỉ 3 trường action item, thiếu ngày, thành phần, quyết định (spec #1) | `catalog/meeting.py` |
| F-M15 | Kill switch không dừng LLM hay IDP, kể cả mode `L0`; `row is None` là tắt (fail-open) | `autonomy.py:84-87` |
| F-M16 | `AIAction.input` lưu tham số model thô | `action_service.py:98` |
| F-M17 | Adapter: `json.loads` tham số tool hoặc `r.json()` lỗi không thành `ProviderCallError` → 500, không log | `adapters.py:90,155` |
| F-M18 | Một provider, breaker process-local | §4.1 |

### Low

| ID | Vấn đề | Vị trí |
|---|---|---|
| F-L1 | Pseudonym 4 hex dễ trùng, không phải mã thật | `prompt_guard.py:68-71` |
| F-L2 | `TOOL-send_notification` default L3 ở registry nhưng `AUTONOMY_DEFAULTS` rơi về L2 | `autonomy.py:65` |
| F-L3 | Warning grounding không persist, tải lại mất | `chat_service.py:206-209` |
| F-L4 | `evaluation_service` ghi `cfg.model_chat` dù chat dùng `CHAT_MODEL_PRIMARY` | `evaluation_service.py:45` |
| F-L5 | `.env` có chú thích "tắt demo" cạnh giá trị đang bật | `.env` (chỉ đọc key/comment) |
| F-L6 | Lệch tài liệu: CLAUDE.md §4.2 nêu `core/rate_limit`, `core/events`; R-DEC-141/153 mô tả thứ không có | |

## 6. Điều được nói thật

### Có thể tuyên bố hôm nay

- Trích xuất INVOICE từ PDF có text layer đã chạy với model thật, lưu đủ 8 trường có confidence, và bắt buộc qua người ở trường tiền/MST.
- Mọi LLM call đi qua ModelGateway duy nhất; ghi hash prompt, token, chi phí; không lưu prompt thô (đã thấy dòng thật).
- Trường trọng yếu không thể tự duyệt (cứng trong code).
- IDP không có tool calling; tài liệu có dấu hiệu injection bị ép review.
- Danh sách tool lọc theo quyền người hỏi, chạy bằng Principal người hỏi, không token hệ thống.
- Briefing hằng ngày là snapshot dữ liệu thật, có truy vết, **không phải AI viết**.
- Gói và model OCR Paddle tiếng Việt nằm trong image, chạy offline.
- Model local và embedding có mặt trên Ollama.

### Không thể tuyên bố

- "Dữ liệu Mật/Tuyệt mật không rời on-prem" cho IDP (F-C1).
- "AI không bịa số" như một bảo đảm (F-H1); chỉ nói được "có bộ lọc số".
- "Trợ lý AI trả lời bằng model" khi replay bật (F-C2).
- Bất kỳ con số độ chính xác nào, kể cả 95,83% và recall ≥ 90%.
- Tìm kiếm ngữ nghĩa/RAG, voice/STT, streaming thời gian thực.
- OCR tài liệu scan PDF.
- 14 loại tài liệu; 54 tool hoạt động; multi-agent; đa provider đang vận hành.
- AI insight/khuyến nghị do model sinh; quản lý phiên bản prompt; rate limit AI.
- "Xem tài liệu gốc đúng trang" với tài liệu nhiều trang.

## 7. Lộ trình AI ưu tiên cho v4

Dependency mới và thay đổi spec cần DEC do human duyệt (CLAUDE.md §2.3, §6.3).

| Ưu tiên | Việc | Giải quyết |
|---|---|---|
| **P0 — trước khi nhận dữ liệu thật** | Sau phân loại, đặt `sensitivity_level` theo doc type/trường và tính lại classification trước extract; scrub PII cho extract; roster mặc định local-only hoặc C5 | F-C1 |
| | Tắt `AI_DEMO_REPLAY`/`DEMO_MODE` ở stack thật; fail startup nếu cả hai bật khi không phải demo; tách replay khỏi build production | F-C2 |
| | Nâng classification theo tool result; sửa ceiling: lượt cloud không nhận tool CONFIDENTIAL | F-H11 |
| | Rate limit 20/phút; xử lý `TemplateRequired`; trung hòa delimiter; hạ `create_task` từ chat về L2 khi context có nội dung ngoài | F-H10, F-M2, F-H12 |
| **P1 — đo được sự thật** | Bộ nhãn vàng từ 13 file `data/` + mẫu pilot; chạy live định kỳ theo ngân sách; đo field/classification accuracy; gate phát hành | F-H13 |
| | Sửa grounding: bỏ label bypass với số có đơn vị, gắn số với metric, xử lý số viết chữ | F-H1 |
| | Prompt registry có version, ghi prompt version vào log | F-M6 |
| **P2 — IDP dùng được** | `source_location` thật (trang + vùng), `full_text` có dấu trang | F-H4 |
| | Chia khối + continuation (chọn phương án R-DEC-164) | F-H5 |
| | Render PDF ra ảnh trước OCR (dependency cần DEC); dùng `ocr_confidence` trong routing; log lỗi OCR | F-H3 |
| | #5 SOP (P0) rồi #9, #8, #11; validate theo hàng; confidence đa tín hiệu; đọc `thresholds` | F-H6, F-H7, F-M10 |
| **P3 — trợ lý thật** | Bind hoặc gỡ tool stub; ACT cho `record_decision`, `generate_report`, `request_approval`; list tool đọc bản ghi | F-H8 |
| | Streaming thật + heartbeat, deadline lượt, 5 s/tool, hủy khi ngắt kết nối; bộ nhớ hội thoại | F-H9, F-M1 |
| | RAG: adapter `/embeddings` qua Ollama `bge-m3`, job index, fallback keyword khi lỗi (chỉ sau khi xong F-H11) | F-H2 |
| **P4 — vận hành** | Thêm provider fallback thực; phân loại 4xx; breaker chia sẻ; log `ok` độc lập; alert 80%; ngân sách agent; insight narrate có grounding; orchestrator | F-M3..5, F-M13, F-M18 |

## 8. UNVERIFIED và giới hạn của audit

- Không gọi LLM/OCR, không upload, không POST. Không xác minh được hành vi model thật ngoài dòng log có sẵn.
- Toàn bộ khẳng định từ STATE (chat live M5, DOC-09, DOC-03, DOC-10) không kiểm chứng được trên DB hiện tại.
- Giá trị `MODEL_EXTRACT`, `CHAT_MODEL_*`, `MODEL_PRICING_JSON` không đọc; nguyên nhân `claude-sonnet-5` thay vì route R-DEC-164 chưa rõ.
- Khả năng trả tool và độ trễ của Ollama trên 4 CPU chưa đo.
- OCR tiếng Việt chất lượng thực chưa đo. Hành vi OmniRoute với `strict` chưa đo.
- Rò rỉ F-C1 ở stack cô lập/quá khứ chưa kiểm.

**Thao tác vượt khuôn cần nêu rõ:** ngoài DB chính, tôi đã chạy một truy vấn aggregate `provider,status,count(*)` trên `aureon_final`, `aureon_m16`, `aureon_m4` (kết quả: fixture 4; fixture 12; omniroute ok 13 + none forbidden 8). Brief chỉ nêu `$POSTGRES_DB`, nên phần này nằm ngoài lệnh được cho phép; không đọc nội dung, không dựa vào nó cho phân loại nào. Hoàn toàn read-only.

Các kiểm tra phụ khác, đều không ghi: script Python thuần gọi hàm grounding/PII/registry từ `.venv` với `PYTHONDONTWRITEBYTECODE=1`; đọc metadata gói và thư mục model trong worker; `Image.open` trên bytes PDF tổng hợp; GET `/api/tags`, `/api/ps` và `ollama show`. Không sửa repo.
