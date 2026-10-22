# 01 — PROJECT OVERVIEW

> Tầm nhìn, phạm vi, KPI và lộ trình của **Aureon v2**.
> File này là "hợp đồng phạm vi" — mọi thứ ngoài đây là ngoài scope.
> **Canonical Source (DEC-144):** `_reference/SOURCE-BRD-v1.1.md` (AI-EOS) — mâu thuẫn với file này thì BRD thắng, trừ DEC mới hơn DEC-144. Hợp nhất (DEC-124): A-EMS (`SOURCE-BRD-v1.0`, "Digital Chief of Staff", 5 trụ F.O.C.U.S), AI-EOS (D03 Data Capture & IDP, Data Foundation, Autonomy L0–L4) và đề xuất UI/UX AI-EOS. Quyết định: DEC-125 → DEC-137 (kiến trúc), DEC-146 → DEC-155 (đợt v2.1).
> **Hai bản phát hành:** **v2.0 = demo-ready** (12 tuần, S0–S5) · **v2.1 = production-ready** (hạng mục hoãn ở §3.3).

---

## 1. Vấn đề

Doanh nghiệp Việt Nam vận hành bằng **giấy tờ, PDF, Word, Excel, ảnh chụp và Zalo**. Hệ quả:

- CEO không có bức tranh tổng thể — mỗi phòng báo một kiểu, số liệu vênh nhau.
- AI/BI không có gì để phân tích — dữ liệu rỗng hoặc sai ("vòng lặp Data → Intelligence → Action gãy ngay từ mắt xích đầu tiên", BRD §1.3 #2, #12).
- Quyết định dựa trên cảm tính; rủi ro chỉ phát hiện khi đã muộn.
- Quyết định đã giao không biết đi đến đâu; cuộc họp không thành hành động (BRD §1.3 #7).
- Chiến lược không nối với thực thi; KPI/OKR theo dõi bằng Excel nên biết kết quả khi đã muộn (BRD §1.3 #5, #6).

**Khoảng trống thị trường:** ERP (nặng, cứng), BI (chỉ đọc dữ liệu có sẵn), IDP thuần (đọc tài liệu, không ra quyết định), chatbot (không có dữ liệu thật, không có nguồn). Không sản phẩm nào đi **từ tài liệu giấy → dữ liệu có cấu trúc → insight có nguồn → quyết định → giao việc** trong một luồng.

---

## 2. Giải pháp — Aureon v2 "Digital Chief of Staff"

**Tagline (BRD §1.1):** *One Enterprise. One Source of Truth. One AI Operating Layer.*

**Lời hứa MVP (BRD §19):** *"CEO biết công ty đang đạt mục tiêu đến đâu, vì sao, và giao việc được ngay — với dữ liệu nhập vào dễ như gửi một file."*

Aureon v2 gồm 5 khối:

| # | Khối | Mô tả | Spec |
|---|---|---|---|
| 1 | **Executive Dashboard F.O.C.U.S** | 5 trụ — **F** Finance, **O** Operations & People, **C** Customer & Growth, **U** Product & Innovation, **S** Strategy & Risk; 31 metric trụ + METRIC-DQ-01 (= **32 metric**, 32 alert — DEC-148), trạng thái trụ ok/warning/critical, drill-down ≤ 3 click đến tài liệu gốc | 03 |
| 2 | **Domain modules** | Finance (+ dòng tiền 13 tuần), Sales, HR (team, vị trí, nghỉ phép), Product, Risk (rủi ro đề xuất), Execution (Strategy → Initiative → Project/Task, họp, quyết định, OKR/KPI) — CRUD, quy tắc nghiệp vụ, event | 03, 05, 10 |
| 3 | **Data Capture & IDP (D03)** | 5 kênh C1–C5, AI phân loại → trích xuất → kiểm tra → review song song → ghi qua Action Registry; lineage đến trang tài liệu | 04 |
| 4 | **AI Core — Trợ lý AI** | Thanh ⌘K + Panel ngữ cảnh + Chat streaming; tool calling lọc theo quyền; mọi con số có nguồn; insight 9 phần; Autonomy L0–L3 + kill switch (toàn hệ thống + theo agent); feed "AI đã làm"; phê duyệt (Approval) và báo cáo PDF/Excel | 03, 06, 07, 10 |
| 5 | **Data Foundation & Governance** | Master data, Data Quality Score (METRIC-DQ-01), freshness, lineage, metric store, audit, RBAC 10 vai trò, 4 mức phân loại dữ liệu | 02, 05, 07 |

### 2.1. Kiến trúc tóm tắt (DEC-125, DEC-126)

**Modular Monolith** — một ứng dụng FastAPI, chia module theo bounded context, mỗi module một schema PostgreSQL riêng; giao tiếp liên module qua service interface (đồng bộ) hoặc **domain event qua Transactional Outbox + Celery/Redis** (bất đồng bộ). Không có 17 container như A-EMS. Chi tiết ở `07-TECH-ARCHITECTURE.md`.

### 2.2. Pipeline dữ liệu end-to-end

```
Nhập tay / nói / thả file / chụp / import Excel   (C1–C5)
        ↓
IDP: phân loại → trích xuất → chuẩn hóa VN → kiểm tra nghiệp vụ
        ↓
Review song song (bắt buộc với trường trọng yếu / confidence thấp)
        ↓
Action Registry → ghi vào module domain (finance, sales, hr, product, risk, execution)
        ↓
Outbox → domain event → Risk tự sinh rủi ro · Metric store tính lại · AI làm mới insight
        ↓
Dashboard F.O.C.U.S + Briefing + Trợ lý AI (mọi con số có nguồn, truy về trang tài liệu)
```

### 2.3. Vòng lặp vận hành và 4 câu hỏi (BRD §1.1–1.2)

```
Capture → Data → Intelligence → Decision → Action → Measurement → Feedback
```

| # | Câu hỏi hệ thống phải trả lời liên tục | Aureon v2 trả lời bằng |
|---|---|---|
| 1 | Chúng ta muốn đạt gì? | Objective, KPI/KPITarget, OKR |
| 2 | Chúng ta đang làm gì để đạt nó? | Initiative → Project/Milestone → Task (DEC-147) |
| 3 | Kết quả đang thế nào và tại sao? | Dashboard F.O.C.U.S, metric store, insight 9 phần có nguồn |
| 4 | Tiếp theo cần làm gì? | Khuyến nghị → Decision → Approval → Task → **xác minh kết quả** (BRD-P11) |

Aureon là **System of Record + Intelligence + Action** (BRD §1.4): đi tiếp sau dashboard tới "insight → khuyến nghị → quyết định → hành động → xác minh kết quả".

---

## 3. Phạm vi v2

Chiến lược 2 bản (DEC-153): **v2.0 demo-ready** — đủ kịch bản CEO end-to-end "hỏi → hiểu → điều tra → quyết → giao việc → duyệt → báo cáo" trên dữ liệu ABC; **v2.1 production-ready** — các hạng mục §3.3. Tag phạm vi user story (02, 00 §4.11): `v2.0` · `v2.0 lite` · `[v2.1]` · `[OUT]`.

### 3.1. ✅ Trong phạm vi v2.0 (IN)

- Dashboard F.O.C.U.S: 5 trụ, **32 metric** (31 metric trụ + METRIC-DQ-01), 32 alert, trạng thái trụ, insight panel, briefing CEO, bộ lọc kỳ, cô lập lỗi theo widget.
- Module domain (BRD §19.3 xếp HR/Product/Risk là P1; DEC-153 **giữ Must cho v2.0** để demo đủ 5 trụ — GAP C-25):
  - Finance Lite+: doanh thu, chi phí, ngân sách, tiền mặt, dự báo 3 kịch bản, hóa đơn, **dòng tiền 13 tuần** (DEC-148).
  - Sales Pipeline Lite+: khách hàng, deal, pipeline, mục tiêu, hợp đồng.
  - HR: phòng ban, **team, vị trí**, nhân viên, kỹ năng, **nghỉ phép**, lịch sử lương, kế hoạch tuyển dụng (DEC-147).
  - Product: sản phẩm, tính năng, roadmap, release, chỉ số.
  - Risk: sổ rủi ro **13 danh mục**, chấm điểm, rủi ro tự sinh ở trạng thái **đề xuất** chờ owner xác nhận, mitigation, what-if (DEC-148).
  - Execution: **Strategy → Initiative → Project/Milestone → Task** (7 trạng thái), họp, quyết định (đối chiếu kết quả 30/60/90 ngày), OKR, KPI (band đánh giá), check-in (DEC-147).
- IDP 5 kênh C1–C5, 9 loại tài liệu MVP (§8), review song song (giao lại, escalation SLA), import Excel có map cột; UC-01, UC-02, UC-03, UC-06, UC-07, UC-08 (bản demo).
- **Meeting transcript mock:** upload thủ công file transcript → AI trích quyết định, action item (UC-02; không tích hợp Meet/Zoom/Teams — DEC-153).
- **Approval cơ bản:** rule theo giá trị + SLA; hành động tài chính > `APPROVAL_FINANCE_THRESHOLD_VND` (mặc định 500.000.000 đ) cần 2 người duyệt; còn lại 1 người (DEC-149, DEC-155).
- **Reporting tối thiểu:** báo cáo tuần/tháng xuất **PDF + Excel** (không BI đầy đủ — DEC-153).
- Trợ lý AI: chat + SSE, tool calling theo quyền, source chip, insight 9 phần, what-if runway, feedback, lọc PII trước khi gửi LLM; **1 agent profile dùng chung** `assistant` (DEC-150).
- AI Autonomy L0–L3 cấu hình theo tool × role × ngưỡng giá trị; tool liên quan tiền trần **L2** (DEC-150); hoàn tác; kill switch toàn hệ thống + theo agent (DEC-149).
- 10 vai trò (DEC-128), RBAC `<domain>:<action>`, data scoping, chuyển vai trò demo; **1 tenant** (tenant isolation BRD P0 thỏa bằng mô hình single-tenant — GAP A-19).
- 4 mức phân loại dữ liệu Công khai / Nội bộ / Mật / Tuyệt mật quyết định model được dùng (DEC-149).
- ModelGateway đa provider (OmniRoute, OpenRouter, 9router, DeepSeek, OpenAI, Anthropic) với fallback (DEC-131).
- Giao diện tiếng Việt mặc định + tiếng Anh (DEC-135); web responsive + PWA mobile (4 việc).
- Doanh nghiệp giả định ABC ~150 nhân sự, dữ liệu đủ 5 trụ (DEC-136).

### 3.2. ❌ Ngoài phạm vi (OUT — không thuộc v2.0 lẫn v2.1)

- Microservice tách deployable, database-per-service vật lý, RabbitMQ, API Gateway riêng (DEC-125/126).
- Kênh C6–C10 (email forwarding, Zalo/Slack/Teams bot, hóa đơn XML NĐ 123, Drive sync, API/Webhook).
- Integration thật: MISA, Fast, Bravo, ngân hàng, cổng hóa đơn điện tử, Google Meet bot.
- Procurement/Vendor, Workflow Engine tổng quát, chữ ký số, Performance Cycle đầy đủ, Contract Lifecycle.
- **D19 Partner** (đối tác, hoa hồng, pipeline đối tác), **D23 Technical / Engineering** (Git, CI/CD, incident, technical debt), **Customer 360 / CRM đầy đủ** (churn, health score khách hàng) — BRD P1, Phase 2–3 (GAP C-24).
- **Public API / webhook / MCP server** cho hệ thống ngoài (BRD FR-INT-04, P1 — GAP A-19).
- Autonomy L4; huấn luyện/fine-tune model riêng; **huấn luyện model bằng dữ liệu khách hàng**.
- Multi-tenant, đa pháp nhân, billing; SSO/LDAP; self-register (DEC-137).
- Mobile native app (chỉ PWA).

### 3.3. ⏭️ Hoãn sang v2.1 (production-ready)

| Hạng mục | Lý do hoãn | DEC |
|---|---|---|
| Knowledge / RAG (SOP, chính sách) — BO-07 | Cần 3–4 tuần ingest + tuning; v2.0 trích dẫn qua lineage metric/bản ghi | DEC-153 |
| MFA bắt buộc Admin/Tài chính | Không demo-able | DEC-153 |
| Calendar Google/Outlook 2 chiều | Cần OAuth thật | DEC-153 |
| Voice C2 (nhập bằng lời) | Cần STT thật (DEC-050) | DEC-153 |
| Orchestrator + 6 agent chuyên trách; prompt versioning; memory/evaluation; quyền agent ∩ người; role tùy biến | Giảm rủi ro build; v2.0 = 1 assistant, quyền người hỏi (P06) | DEC-150 |
| Tool tiền ở L3; service identity theo job | An toàn dữ liệu tiền; v2.0 = 1 service account | DEC-150 |
| Effective-dated org, ma trận kiêm nhiệm, export toàn bộ dữ liệu | Tránh phình schema | DEC-147 |
| Risk appetite theo danh mục; contract xuyên domain | P1 BRD | DEC-148 |
| "Xem như người dùng" thật (FR-ADM-08 — v2.0 chỉ có chuyển vai trò demo EP-04/05); mức ưu tiên / gộp + tóm tắt / giờ yên lặng của thông báo (BRD D05) | Ngoài kịch bản demo; impersonation cần audit kép | DEC-156 (đề xuất) |

**Thứ tự build khác BRD §19.1** (BRD: IDP + Tool Registry ở ngày 1–30): v2 làm nền tảng → domain → dashboard → AI → IDP (§10) vì Action Registry/IDP cần domain module có sẵn để ghi; tổng 12 tuần vẫn nằm trong khung 90 ngày (GAP A-13).

**Nếu agent thấy yêu cầu nằm ngoài danh sách IN → raise decision, không tự build.**

---

## 4. Mục tiêu kinh doanh, North Star và KPI v2

### 4.1. Mục tiêu kinh doanh BO-01..BO-10 (BRD §2.1)

Mục tiêu 6 tháng **sau go-live tại khách hàng thật** (v2.1). v2.0 chỉ chứng minh được trên dữ liệu ABC — cột "v2.0 demo" ghi cách thể hiện. Mã `BO-xx` là nhãn tham chiếu BRD (như `BRD-Pxx`), không phải prefix ID mới.

| Mã | Mục tiêu | Chỉ số đo | Mục tiêu 6 tháng | v2.0 demo |
|---|---|---|---|---|
| BO-01 | Quản trị tập trung trên một nền tảng | % quy trình quản trị cốt lõi chạy trên hệ thống | ≥ 80% | 5 trụ + Execution + Approval + Report trên một app |
| BO-02 | Minh bạch gần thời gian thực | Độ trễ dữ liệu chỉ số điều hành | ≤ 24 giờ (tài chính), ≤ 1 giờ (task, sales) | Metric tính lại theo event (05 §5) |
| BO-03 | Liên kết chiến lược với thực thi | % task/dự án gắn KPI/OKR hoặc initiative | ≥ 70% | `tasks.initiative_id/key_result_id/kpi_id` (DEC-147) |
| BO-04 | Quyết định có AI hỗ trợ | % quyết định quan trọng có phân tích AI kèm bằng chứng | ≥ 50% | `decisions.source_insight_id` |
| BO-05 | Thực thi có AI hỗ trợ | Hành động AI được xác minh thành công / tháng | Tăng hằng tháng | Feed "AI đã làm" + bước xác minh (03) |
| BO-06 | Giảm chi phí quản lý | Giờ/tuần CEO dành cho tổng hợp, báo cáo, follow-up | Giảm ≥ 50% (≥ 5 giờ/tuần) | Briefing + Report tự động |
| BO-07 | Bộ nhớ doanh nghiệp | % quyết định, cuộc họp, tài liệu quan trọng truy vấn được | ≥ 90% | Decision Log + lineage; RAG ở v2.1 (DEC-153) |
| BO-08 | Thu thập không ma sát | Thời gian nhập liệu so với nhập tay hoàn toàn | Giảm ≥ 70% | IDP C1–C5, UC-07 |
| BO-09 | Dữ liệu đáng tin cho AI | Data Quality Score domain cốt lõi | ≥ 90/100 | METRIC-DQ-01 (DEC-148) |
| BO-10 | Phát hiện rủi ro sớm | Thời gian từ dấu hiệu đến hành động | Giảm ≥ 50% | Rủi ro tự sinh `proposed` từ event |

### 4.2. North Star (BRD §20.1)

> **Tỷ lệ quyết định và hành động quan trọng được AI hỗ trợ và có kết quả được xác minh.**

Không dùng "số cuộc hội thoại với AI". Phễu: AI Insights → Khuyến nghị → Khuyến nghị được chấp nhận → Hành động thực thi → Hành động được xác minh → Kết quả thành công. Nguồn: `ai.insights`, `ai.ai_actions`, `execution.decisions` (`actual_outcome`, `outcome_verified_at`).

### 4.3. Cổng qua MVP (BRD §19.1, §20.2)

| # | Cổng (đo ở pilot v2.1) | v2.0 demo chứng minh bằng |
|---|---|---|
| 1 | CEO dùng Briefing ≥ 4 ngày/tuần trong 4 tuần liên tiếp | Briefing hằng ngày theo role (03) |
| 2 | ≥ 80% KPI/OKR cập nhật đúng kỳ | Check-in + nhắc kỳ |
| 3 | ≥ 60% dữ liệu mới vào qua tài liệu hoặc ngôn ngữ tự nhiên | Seed ABC nạp qua 9 tài liệu mẫu (UC-07) |
| 4 | Không sự cố AI ghi sai trường trọng yếu mà không bị phát hiện | Trường trọng yếu luôn qua người (FR-DC-16) |

**Kịch bản CEO 7 bước** phải chạy được end-to-end ở v2.0: Ask → Understand → Investigate → Decide → Act → Follow-up → Verify (§11).

### 4.4. KPI v2 (vận hành sản phẩm)

| Nhóm | KPI | Ngưỡng | Cách đo |
|---|---|---|---|
| CEO | Thời gian đến insight đầu tiên | ≤ 10 giây | Usability test |
| CEO | F1 Briefing → giao việc | ≤ 2 phút, ≤ 5 chạm | Usability test |
| Trust | Drill-down từ số → tài liệu gốc | ≤ 3 click | Log UI |
| Trust | Câu trả lời AI có số liệu kèm nguồn | 100% | Log AI |
| IDP | Field accuracy | ≥ 90% chung; ≥ 95% tài liệu có text layer | Đối chiếu ground truth |
| IDP | Straight-through rate | ≥ 50% sau 3 tháng | Log pipeline |
| IDP | Review 1 hóa đơn 6 trường | ≤ 60 giây | Log SCR-10 |
| IDP | Error leakage trường trọng yếu | < 0,5% | Hậu kiểm |
| IDP | Time to data (≤ 5 trang) | p50 ≤ 5 phút; p95 trích xuất ≤ 60 giây | Log pipeline |
| Onboarding | UC-07 từ tập tài liệu đến dashboard đầu tiên | ≤ 15 phút (demo) | Usability test |
| Hiệu năng | Endpoint dashboard p95 | < 800 ms; 5 trụ < 3 giây | Load test |
| Hiệu năng | AI chat token đầu tiên p50 / p95; hoàn tất lượt p95 | ≤ 2 giây / ≤ 5 giây; ≤ 30 giây | Log AI (DEC-152) |
| UX | SUS | ≥ 75 | Khảo sát |
| UX | Hoàn thành F1–F5 không cần hỗ trợ | ≥ 90% | Usability test |
| AI | Action card L2 xác nhận không sửa / hoàn tác L3 | ≥ 60% / ≤ 5% | Log AI |
| Adoption | WAU / tổng user | ≥ 70% | Analytics |
| Adoption | CEO mở Briefing | ≥ 4 ngày/tuần | Analytics (BRD §20.1) |
| Dữ liệu | Data Quality Score domain cốt lõi | ≥ 90/100 | METRIC-DQ-01 |
| Thực thi | % KPI/OKR cập nhật đúng kỳ / % action item họp xong đúng hạn | ≥ 90% / ≥ 75% | `check_ins`, `tasks` |
| AI | Khuyến nghị được chấp nhận / câu trả lời được đánh giá đúng | ≥ 40% / ≥ 90% | `ai_actions`, `feedback` |

---

## 5. Personas (10 vai trò — DEC-128)

| ID | Role | Mục tiêu | Trang chủ |
|---|---|---|---|
| ROLE-01 | **CEO** | Biết ngay, quyết nhanh | Briefing công ty, 5 trụ, "Cần anh quyết", rủi ro |
| ROLE-02 | **CFO** | Đủ tiền, chi tiêu hiệu quả | Trụ F + S, ngân sách, dự báo |
| ROLE-03 | **VP_SALES** | Giữ pipeline, doanh thu | Trụ C |
| ROLE-04 | **HR_MANAGER** | Đủ người, giữ người | Trụ O (con người) |
| ROLE-05 | **REVIEWER** | Duyệt nhanh, không sai | Hàng chờ review + SLA |
| ROLE-06 | **CPO** | Sản phẩm được dùng thật | Trụ U |
| ROLE-07 | **RISK_MANAGER** | Không bỏ sót rủi ro | Trụ S, sổ rủi ro |
| ROLE-08 | **MANAGER** | Giữ team đúng hướng | Briefing đơn vị, hàng chờ duyệt, workload |
| ROLE-09 | **EMPLOYEE** | Làm việc, ít khai báo | Việc hôm nay, mục tiêu của tôi, gửi chứng từ |
| ROLE-10 | **ADMIN** | Cấu hình an toàn | Tình trạng hệ thống, AI Control Center |

Chi tiết + user stories + ma trận quyền ở `02-PERSONAS-PERMISSIONS.md`.

## 5A. RACI cho quy trình cốt lõi (BRD §3.3 → 10 vai trò)

"Director" của BRD = 5 role phụ trách trụ (CFO, VP_SALES, HR_MANAGER, CPO, RISK_MANAGER) **trong trụ của mình**. R = thực hiện · A = chịu trách nhiệm cuối · C = tham vấn · I = được thông báo · — = không tham gia. **AI Agent không bao giờ là A.**

| Quy trình | CEO | Director (CFO · VP_SALES · HR_MANAGER · CPO · RISK_MANAGER) | MANAGER | EMPLOYEE | REVIEWER | ADMIN | AI (`assistant`) |
|---|---|---|---|---|---|---|---|
| Đặt chiến lược, Objective công ty, Initiative | A/R | C | I | I | — | — | C (gợi ý, phân tích) |
| Đặt KPI/OKR phòng ban | A | R | C | I | — | — | C |
| Check-in KPI/OKR | I | A | R | R | — | — | R (nhắc, tổng hợp) |
| Nhập và duyệt dữ liệu từ tài liệu | I | A | R (duyệt đơn vị) | R (tải lên) | R (duyệt hàng chờ) | C | R (trích xuất) |
| Giao việc và cân bằng workload | I | A | R | C | — | — | C (đề xuất) |
| Phát hiện và xử lý rủi ro | A | R (RISK_MANAGER chủ trì) | R | I | — | — | R (phát hiện → `proposed`) |
| Phê duyệt hành động (Approval) | A (tài chính > ngưỡng: người duyệt thứ 2) | R (trong trụ) | R (đơn vị) | I | — | — | — (chỉ gửi `request_approval`, không tự duyệt) |
| Báo cáo tuần/tháng | A | R | C | — | — | — | R (soạn, có nguồn) |
| Theo dõi và xác minh kết quả quyết định | A | R | R | I | — | — | R (đối chiếu expected vs actual) |
| Cấu hình quyền, policy AI, kill switch | A | C | I | — | — | R | — |

Ma trận quyền chi tiết (`<domain>:<action>`) ở 02 §5.

---

## 6. Nguyên tắc sản phẩm (bất biến)

### 6.1. Nguyên tắc BRD — canonical (BRD §2.2, DEC-144, DEC-146)

`BRD-P01..P11` là nhãn tham chiếu (00 §4.9). Cột "Áp dụng ở Aureon v2" ghi cách hiện thực và nguyên tắc docs tương ứng.

| BRD | Nguyên tắc | Ý nghĩa bắt buộc | Áp dụng ở Aureon v2 | docs-P |
|---|---|---|---|---|
| **BRD-P01** | AI First | Mọi module thiết kế để AI đọc, truy vấn và hành động được | Mỗi module expose tool (10 §7) + event; entity có `source`, `data_classification` (05 C19) | — (mới, §6.3) |
| **BRD-P02** | API First | Mọi năng lực expose qua API và tool; UI dùng chính API đó | Contract duy nhất ở 10; FE chỉ gọi API công khai | P09 (một phần) |
| **BRD-P03** | Data First | Dữ liệu có cấu trúc, có owner, nguồn gốc chỉ định, điểm chất lượng | Metric store, lineage, METRIC-DQ-01, `source` mọi bản ghi | — (mới, §6.3) |
| **BRD-P04** | Human in the Loop | Hành động tác động cao cần người phê duyệt theo Autonomy Level | L2 action card; Approval 1/2 người (DEC-149, DEC-155); tool tiền trần L2 | P02 |
| **BRD-P05** | Everything Actionable | Mọi insight chuyển được thành khuyến nghị, quyết định, task | Insight 9 phần → Decision → Task | P07 (một phần) |
| **BRD-P06** | Traceability | Strategy → Objective → KPI/OKR → Initiative → Project → Task → Người → Kết quả; số → tài liệu gốc | Chuỗi execution (DEC-147) + lineage ≤ 3 click | P01 |
| **BRD-P07** | Explainable AI | AI nêu dữ liệu, nguồn, lập luận, khuyến nghị, độ tin cậy, hành động | Source chip, `why`, `confidence` trong audit (DEC-149) | P02, P05 |
| **BRD-P08** | Security by Design | AI không vượt quyền người dùng và policy | Tool lọc theo `permissions[]`, PII filter, 4 mức phân loại | P06 |
| **BRD-P09** | Capture Once, Use Everywhere | Nhập một lần, dùng chung mọi domain | IDP + Action Registry + outbox event | P03 |
| **BRD-P10** | Graceful Degradation | AI lỗi/tắt → nghiệp vụ cốt lõi vẫn làm thủ công | Kill switch, widget lỗi tại chỗ, nhập tay C1 | P08 |
| **BRD-P11** | Measure Outcomes | Đo bằng kết quả kinh doanh được xác minh, không bằng số lần dùng AI | North Star §4.2; xác minh kết quả action L2+ và Decision 30/60/90 ngày | — (mới, §6.3) |

### 6.2. Nguyên tắc docs P01–P09 (giữ mã — CLAUDE.md, code review, test)

| # | Nguyên tắc | Kiểm tra | BRD |
|---|---|---|---|
| **P01** | **Every number traceable** — mọi con số click được: công thức, nguồn, thời điểm cập nhật, bản ghi gốc, tài liệu gốc (trang/vùng) | Không có con số "mồ côi" | BRD-P06 |
| **P02** | **AI shows state** — AI gợi ý (L1) / AI soạn · chờ xác nhận (L2) / AI đã làm (L3, hoàn tác được) | Người dùng luôn trả lời được "AI vừa làm gì?" | BRD-P04, BRD-P07 |
| **P03** | **Capture once, use everywhere** — dữ liệu nhập một lần, mọi module dùng chung qua event | Không màn hình nào yêu cầu nhập lại | BRD-P09 |
| **P04** | **Vietnamese-first** — `05/10/2026`, `1.250.000 đ`, `1,2 tỷ`, `12,5%`, MST 10/13 số, địa chỉ hành chính mới | Không nhãn dịch máy gượng gạo | — (riêng docs) |
| **P05** | **AI never fabricates numbers** — mọi số trong câu trả lời AI đến từ tool call hoặc tài liệu có trích dẫn; thiếu dữ liệu thì nói thiếu | Không có số ngoài `sources` | BRD-P07 |
| **P06** | **AI within user's permission** — AI gọi tool bằng chính JWT/quyền người hỏi; danh sách tool lọc theo role trước khi gửi model | AI không trả dữ liệu vượt quyền | BRD-P08 |
| **P07** | **Exceptions first** — màn hình đầu tiên chỉ hiện điều lệch kế hoạch, việc cần quyết, rủi ro mới | CEO trả lời "có gì cần tôi?" trong 10 giây | BRD-P05 (một phần) |
| **P08** | **Graceful degradation** — AI hoặc một module lỗi chỉ widget đó báo lỗi; nhập tay luôn hoạt động | Dashboard vẫn dùng được khi AI lỗi | BRD-P10 |
| **P09** | **Event-driven, vendor-agnostic** — thay đổi nghiệp vụ quan trọng phát event; không khóa vào một nhà cung cấp LLM | Đổi provider chỉ cần đổi env | BRD-P02 (một phần) |

### 6.3. Bổ sung cho BRD-P01, BRD-P03, BRD-P11 (chưa có docs-P)

Không cấp số P10+ (DEC-146 giữ P01–P09); kiểm tra review dùng nhãn BRD:

| BRD | Kiểm tra khi review spec / code |
|---|---|
| BRD-P01 AI First | Module mới có ≥ 1 tool đọc trong 10 §7 và phát event cho thay đổi quan trọng; entity có trường chung C19 |
| BRD-P03 Data First | Bản ghi có `source` + owner; metric có công thức trong metric store; dữ liệu nhập ảnh hưởng METRIC-DQ-01 |
| BRD-P11 Measure Outcomes | Action L2+/Decision có `expected_outcome` và mốc xác minh; báo cáo AI đo bằng kết quả, không bằng số lượt chat |

---

## 7. Ràng buộc

### Kỹ thuật
- Frontend Next.js 14+ App Router / React 18+; Backend Python 3.12 + FastAPI; PostgreSQL 16 + pgvector; Celery + Redis; MinIO/S3.
- Modular Monolith (DEC-125); JWT RS256 (DEC-129); mọi LLM call qua ModelGateway (DEC-131).
- Không mobile native (PWA); chạy được offline ở mức demo (fixture mode của ModelGateway).

### Vận hành
- Build bằng AI Agent qua DeepSeek Harness + OmniRoute (11 §9).
- 6 mốc S0–S5, mỗi mốc ~2 tuần (09).
- Mức "demo-grade+": đủ chặt về bảo mật dữ liệu và quyền, chưa yêu cầu HA production.

### Pháp lý
- NĐ 13/2023/NĐ-CP & Luật Bảo vệ dữ liệu cá nhân: consent (kể cả ghi âm/transcript cuộc họp), phân loại 4 mức Công khai/Nội bộ/Mật/Tuyệt mật, không gửi PII/lương cá nhân tới LLM bên ngoài, kiểm soát chuyển dữ liệu ra nước ngoài.
- AI **không** chấm điểm nhân sự, **không** quyết định tuyển dụng / sa thải / lương; **không** huấn luyện model bằng dữ liệu khách hàng (02 §7 — GAP C-23, D-10).
- Hóa đơn điện tử NĐ 123/2020 (Phase 2 cho XML); lưu chứng từ kế toán ≥ 10 năm (Luật Kế toán) — cấu hình retention theo doc type.
- Aureon là lớp quản trị, **không** thay phần mềm kế toán.

---

## 8. Doanh nghiệp giả định (DEC-136)

**Công ty TNHH Thương mại & Dịch vụ ABC** — phân phối thiết bị văn phòng + dịch vụ bảo trì + nền tảng đặt hàng trực tuyến "ABC Order".

| Thuộc tính | Giá trị |
|---|---|
| Quy mô | ~150 nhân sự, 7 phòng ban |
| Doanh thu | ~300 tỷ VNĐ/năm |
| Trụ sở | TP.HCM; chi nhánh Hà Nội |
| Sản phẩm/dịch vụ (trụ U) | ABC Order (B2B portal), ABC Care (gói bảo trì), ABC Supply (phân phối) |
| Kỳ demo | Tháng 9 / Q3 2026; `DEMO_REFERENCE_DATE = 2026-10-20` |

**9 loại tài liệu MVP** (chi tiết `08-DEMO-DATA-SPEC.md`, schema `04-IDP-FEATURE-SPEC.md` §5):

| # | Doc type | Trụ đích chính |
|---|---|---|
| 1 | `FINANCIAL_REPORT` — Báo cáo tài chính quý | F |
| 2 | `INVOICE` — Hóa đơn / danh sách hóa đơn | F, C |
| 3 | `SALES_REPORT` — Báo cáo sales tháng | C |
| 4 | `CONTRACT` — Hợp đồng khách hàng | C, F |
| 5 | `MEETING_MINUTES` — Biên bản họp | O, S |
| 6 | `EMPLOYEE_LIST` — Danh sách nhân sự / sơ đồ tổ chức | O |
| 7 | `KPI_OKR` — Kế hoạch KPI/OKR | O, cả 5 trụ |
| 8 | `PRODUCT_REPORT` — Báo cáo chỉ số sản phẩm tháng | U |
| 9 | `RISK_REGISTER` — Sổ/biên bản đánh giá rủi ro | S |

**Yêu cầu nhất quán:** doanh thu T9 trong #1 khớp SUM(subtotal #2, T9) ±0,5% (DEC-030); tên khách trong #2 khớp #3, #4; người trong #5, #7 khớp #6; sản phẩm trong #8 khớp danh mục; rủi ro trong #9 gắn với entity tồn tại.

---

## 9. Tech stack tóm tắt

| Layer | Công nghệ |
|---|---|
| Frontend | Next.js 14+ App Router, TypeScript strict, TanStack Query, react-hook-form + zod, next-intl, Recharts |
| UI | Tailwind + shadcn/ui + Radix; font Be Vietnam Pro |
| Backend | Python 3.12 + FastAPI (Modular Monolith), Pydantic v2 |
| ORM | SQLAlchemy 2.0 async + Alembic (schema per module) |
| Database | PostgreSQL 16 + pgvector |
| Async / Event | Celery + Redis; Transactional Outbox; DLQ |
| Storage | MinIO (dev) / S3 (prod) |
| Auth | NextAuth + JWT RS256 (PyJWT + cryptography) |
| OCR | PaddleOCR in-process |
| LLM | ModelGateway — OmniRoute / OpenRouter / 9router / DeepSeek / OpenAI / Anthropic |
| RAG | LlamaIndex + pgvector (tri thức SOP/chính sách) — **v2.1** (DEC-153) |
| Container | Docker Compose |

Chi tiết ở `07-TECH-ARCHITECTURE.md`.

---

## 10. Lộ trình build — 6 mốc

| Mốc | Tuần | Mục tiêu | Output |
|---|---|---|---|
| **S0** | 1–2 | Nền tảng v2 | Module skeleton, schema per module, RS256 + 10 role, outbox/event bus, ModelGateway đa provider, envelope/phân trang mới |
| **S1** | 3–4 | Domain F, C, O | Finance, Sales, HR, Execution CRUD + quy tắc + event |
| **S2** | 5–6 | Domain U, S + Dashboard F.O.C.U.S | Product, Risk, metric store, 5 dashboard, alert, drill-down |
| **S3** | 7–8 | Trợ lý AI + Autonomy | Tool Registry, chat SSE, insight, AI actions + undo, kill switch, ⌘K |
| **S4** | 9–10 | IDP v2 | 5 kênh, 9 doc type, review song song, import grid, UC-06/07/08, lineage |
| **S5** | 11–12 | UX, mobile, demo | Design system v2, trang chủ theo role, PWA, Approval + Report PDF/Excel, demo data ABC, E2E F1–F5, đo NFR |

Phân bổ task cho hạng mục mới v2.1 của đợt này (dòng tiền 13 tuần, Initiative, Approval, Report, transcript, DQ) do 09 chốt ở Phase 3d.

Checklist task chi tiết ở `09-BUILD-PLAN-TASKS.md`.

---

## 11. Câu chuyện demo (20 phút)

1. **(2') CEO mở app buổi sáng** (F1) → dòng tóm tắt "2 việc cần anh, 1 rủi ro mới"; 5 thẻ trụ, trụ S đỏ.
2. **(3') Bấm thẻ "Doanh thu T9 đạt 82% KH"** → Panel AI giải thích nguyên nhân có source chip → drill-down tới hóa đơn và trang PDF gốc.
3. **(2') Hỏi AI** "Rủi ro tuyển dụng chậm ảnh hưởng thế nào đến dự báo tài chính?" → trả lời liên miền có nguồn; "Runway nếu tháng sau không có doanh thu mới?".
4. **(2') Chọn phương án** → Action card L2 → xác nhận → 3 task gắn Initiative được tạo, toast hoàn tác, Decision log cập nhật (mốc xác minh 30/60/90 ngày).
   - **(1') Phê duyệt** → yêu cầu chi 600 triệu vượt ngưỡng → CFO duyệt lần 1, CEO duyệt lần 2 (DEC-155).
5. **(2') Chuyển vai CFO / Risk Manager** → dashboard đổi; chạy what-if rủi ro.
6. **(5') Nạp doanh nghiệp (UC-07)** → thả 9 tài liệu mẫu → AI phân loại, trích xuất.
7. **(2') Review song song** (F2) → duyệt hóa đơn ≤ 60 giây → dữ liệu vào module Finance.
8. **(2') Quay lại CEO** → metric cập nhật, insight mới, lineage tới tài liệu vừa duyệt; xuất báo cáo tuần PDF/Excel.

Kịch bản phủ đủ 7 bước BRD §20.2: Ask (1) → Understand (2) → Investigate (3) → Decide/Act (4) → Follow-up (phê duyệt ở 4, bước 8) → Verify (Decision Log, 8).

---

## 11A. Rủi ro sản phẩm, giả định và change management (BRD §20.3–20.5)

### Rủi ro sản phẩm

| Rủi ro | Tác động | Giảm thiểu trong Aureon v2 |
|---|---|---|
| Dữ liệu đầu vào thiếu hoặc bẩn | AI kết luận sai, mất niềm tin | IDP review, METRIC-DQ-01, cảnh báo dữ liệu cũ (freshness) |
| AI bịa số liệu | Quyết định sai | P05 grounding: số không có nguồn bị **chặn** (03), source chip, AI eval fixture |
| Trích xuất sai trường tài chính | Sai số liệu, gian lận | Trường trọng yếu luôn qua người, lý do bắt buộc khi sửa (DEC-151), phát hiện trùng |
| Người dùng không áp dụng | Hệ thống rỗng | Nhập liệu không ma sát (C1–C5), trang chủ theo role, CEO Briefing |
| Chi phí AI vượt dự toán | Biên âm | ModelGateway routing, `AI_MONTHLY_BUDGET_USD`, cảnh báo 80% |
| Vi phạm dữ liệu cá nhân | Phạt, uy tín | 4 mức phân loại; Mật/Tuyệt mật không gửi LLM cloud (DEC-149); NĐ 13/2023 |
| Phạm vi phình to | Trễ demo | Tách v2.0 / v2.1 (DEC-153); yêu cầu ngoài §3.1 → raise DEC |
| Tích hợp hệ thống cũ khó | Dữ liệu không đồng bộ | Ưu tiên import + tài liệu; connector thật OUT |

### Giả định và phụ thuộc

- Khách hàng dùng Google Workspace hoặc Microsoft 365 (Calendar sync ở v2.1).
- Model thương mại đạt chất lượng tiếng Việt cho hội thoại và trích xuất; có phương án model xử lý tại Việt Nam/local cho dữ liệu Mật (07).
- Doanh nghiệp thí điểm cử AI champion và reviewer dữ liệu.
- Phần mềm kế toán cho phép xuất dữ liệu (Excel/CSV qua C5).
- v2.0 chạy trên dữ liệu giả ABC (DEC-136); mọi chỉ số BO/North Star đo thật ở pilot v2.1.

### Change management (áp dụng khi pilot v2.1)

- CEO công bố Aureon là nguồn sự thật duy nhất cho KPI/OKR và task sau tối đa 4 tuần chạy song song với Excel.
- Mỗi phòng ban một AI champion; đào tạo 2 giờ cho nhân viên, 4 giờ cho quản lý và reviewer.
- Giao ban hằng tuần dùng dashboard + Report thay slide tự làm.
- Đo adoption theo phòng ban (WAU, Briefing) và can thiệp nơi thấp.


---

## 12. Thuật ngữ

| Thuật ngữ | Định nghĩa |
|---|---|
| **F.O.C.U.S** | 5 trụ: Finance, Operations & People, Customer & Growth, Product (U = Usage/Innovation), Strategy & Risk |
| **Modular Monolith** | Một deployable, nhiều module có ranh giới rõ (schema riêng, interface riêng) |
| **Outbox** | Bảng ghi event trong cùng transaction nghiệp vụ, relay publish sau commit |
| **IDP** | Intelligent Document Processing — D03 Data Capture (BRD §5) |
| **Action Registry** | Danh mục hành động ghi dữ liệu có idempotency, audit, undo — cửa duy nhất để IDP/AI ghi |
| **Tool Registry** | Danh mục tool AI được gọi (đọc/ghi), có `risk_level`, quyền, autonomy |
| **Autonomy Level** | L0 Inform · L1 Suggest · L2 Draft & Confirm · L3 Act & Notify · L4 Autonomous (ngoài scope) |
| **Kill switch** | Tắt hành động WRITE của AI — toàn hệ thống hoặc theo agent (DEC-149); L3 → L2 |
| **Briefing** | Tóm tắt ngoại lệ hằng ngày theo vai trò |
| **Lineage** | Truy vết metric → bản ghi → field trích xuất → trang tài liệu |
| **Straight-through (STP)** | Tài liệu ghi tự động không cần review |
| **Trường trọng yếu** | Số tiền, số tài khoản, MST, lương, giá trị hợp đồng — luôn qua người |
| **Agent** | Thành phần AI có danh tính, quyền và tool riêng; v2.0 có 1 profile `assistant` (ENT-AIAgentProfile, DEC-150) |
| **Tool** | Năng lực nghiệp vụ đăng ký để AI gọi, có schema, quyền, metadata (classification, reversible, cost) |
| **Extraction Schema** | Định nghĩa trường cần trích xuất cho một loại tài liệu |
| **Metric Store** | Nơi định nghĩa chỉ số một lần, dùng chung cho dashboard, báo cáo và AI |
| **Grounding** | AI chỉ đưa con số có nguồn từ tool hoặc tài liệu (P05) |
| **Initiative** | Sáng kiến chiến lược nối Objective công ty với Project/Task (DEC-147) |
| **Approval** | Yêu cầu phê duyệt theo rule giá trị + SLA; tài chính > ngưỡng cần 2 người (DEC-149, DEC-155) |
| **Data Quality Score** | METRIC-DQ-01 — điểm 0–100 từ đầy đủ, chính xác, độ tươi của dữ liệu (03) |
| **Data classification** | 4 mức Công khai / Nội bộ / Mật / Tuyệt mật — quyết định model và hiển thị (DEC-149) |
| **North Star** | Tỷ lệ quyết định/hành động quan trọng được AI hỗ trợ và có kết quả được xác minh (§4.2) |
| **Runway** / **NRR** / **MST** | Số tháng hoạt động với tiền mặt hiện có / Net Revenue Retention / Mã số thuế |

---

## 13. Liên kết

| Chủ đề | File |
|---|---|
| Personas & quyền | `02-PERSONAS-PERMISSIONS.md` |
| Dashboard F.O.C.U.S & domain | `03-DASHBOARD-SPEC.md` |
| IDP | `04-IDP-FEATURE-SPEC.md` |
| Data model | `05-DATA-MODEL.md` |
| UI/UX | `06-UI-UX-SPEC.md` |
| Kiến trúc | `07-TECH-ARCHITECTURE.md` |
| Demo data | `08-DEMO-DATA-SPEC.md` |
| Build plan | `09-BUILD-PLAN-TASKS.md` |
| API contract | `10-API-SPECIFICATION.md` |
| Agent workflow | `11-AGENT-WORKFLOW.md` |
| Governance | `12`, `13`, `14` |

---

## 13A. Open questions

| # | Câu hỏi | Đề xuất mặc định | DEC |
|---|---|---|---|
| OQ-01 | BRD §21.1 "Mô hình sản phẩm SaaS đa tenant hay nội bộ" | v2.0/v2.1 single-tenant; multi-tenant OUT (§3.2) | DEC-137 (giữ) |
| OQ-02 | BRD §21.1 "Chính sách AI cloud" cho dữ liệu tài chính/nhân sự | Mật/Tuyệt mật không gửi LLM cloud (DEC-149); chi tiết model local ở 07 (Phase 3c) | DEC-149 |
| OQ-03 | "Xem như người dùng" (FR-ADM-08) và thông báo nâng cao (BRD D05) | Hoãn v2.1; v2.0 giữ chuyển vai trò demo | DEC-156 (đề xuất, non-blocking) |
| OQ-04 | Ngưỡng L3 mặc định (BRD §21.1) | Theo `ENT-AutonomyPolicy` seed; tool tiền trần L2 (DEC-150) | DEC-150 |

---

## 14. Version

- **Version:** 2.1.0
- **Status:** current
- **Last updated:** 2026-10-21
- **Applies to:** Aureon v2 (v2.0 demo-ready / v2.1 production-ready)
- **Maintainer:** @CyEyes
- **Change 2.1.0 (Phase 3b — DEC-144, DEC-146..156):** BRD làm Canonical Source; tagline, vòng lặp, 4 câu hỏi (§2.3); phạm vi v2.0 theo DEC-153 + bảng hoãn v2.1 + OUT Partner/Technical/Customer 360/Public API (§3); BO-01..10, North Star, cổng qua MVP (§4); RACI 10 role (§5A); nguyên tắc BRD-P01..P11 canonical + mapping docs-P (§6); ràng buộc AI nhân sự (§7); rủi ro, giả định, change management (§11A); thuật ngữ BRD (§12); Open questions (§13A); 32 metric; D03 thay "Domain 22"; TTFT theo DEC-152.
- **Change 2.0.0:** Viết lại toàn bộ theo DEC-124..137 (v1.0.0 lưu ở nhánh `v1`).