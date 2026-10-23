# 09 — Build Plan & Tasks (Aureon v3 — AI-EOS)

> **Nguồn chuẩn:** `_reference/SOURCE-BRD-v1.1.md` §19 (MVP 90 ngày + 5 phase + ma trận ưu tiên) và §20.2 (kịch bản CEO — điều kiện thành công MVP). Bổ sung: `SOURCE-BRD-v1.1-Bổ sung.md`, `SOURCE-UIUX.md`.
> **Phụ thuộc:** toàn bộ 00–08, 10, 11. **Trạng thái:** ✅ current — Aureon v3 (AI-EOS) CHÍNH THỨC — sinh cuối theo CLAUDE.md §10.1 Phase 4. Tách từ Aureon v2.1 (nay archived ở `docs/_archive/v2.1/`). **Ngày:** 2026-10-23 · **Maintainer:** @CyEyes
> **Phạm vi file:** §1–§5 là **product roadmap P0** (mục tiêu/domain/năng lực mỗi mốc, cổng nghiệm thu, phụ thuộc, thứ tự sinh tài liệu). **§6 là task kỹ thuật `T-*` của đợt code** (R-DEC-15/19), sinh sau khi docs 00–14 được promote `current`.

---

## 1. Lộ trình theo BRD (khác S0–S5 của `main`)

> **Khác `main`:** `main` dùng sprint S0–S5d (đã xong, demo-ready). AI-EOS bám **MVP 90 ngày (3 giai đoạn M1–M3) + 5 phase** của BRD §19 — là lộ trình **sản phẩm**, không phải lộ trình đã-hoàn-thành.

Nguyên tắc dẫn hướng toàn bộ lộ trình: **P0 MVP first** (R-DEC-05) — chỉ 20 domain P0 (TRACEABILITY-SKELETON §12bis) được đặc tả đầy đủ ở đợt docs này; P1/P2 chỉ ghi backlog. Kiến trúc **Modular Monolith** (R-DEC-06), **single-tenant + `tenant_id` mọi entity** (R-DEC-07), **7 role BRD + AI Agent** (R-DEC-08). Lộ trình này là chiều **sản phẩm**; chi tiết hóa task kỹ thuật, migration, test hoãn sang đợt code (R-DEC-09).

### 1.1. Lời hứa MVP (BRD §19)

> **"CEO biết công ty đang đạt mục tiêu đến đâu, vì sao, và giao việc được ngay — với dữ liệu nhập vào dễ như gửi một file."**

Lời hứa này là tiêu chí phân xử ưu tiên: một năng lực thuộc P0 khi nó trực tiếp phục vụ một trong bốn mệnh đề — *biết đến đâu* (chỉ số sức khỏe + KPI/OKR), *vì sao* (AI có trích nguồn + root cause), *giao việc ngay* (khuyến nghị → phê duyệt → task L3), *nhập dễ như gửi file* (Data Capture C1–C5). Năng lực không phục vụ trực tiếp bốn mệnh đề → hạ P1/P2.

## 2. MVP 90 ngày (BRD §19.1)

Ba mốc nối tiếp, mỗi mốc là một cột năng lực tăng dần: M1 dựng **nền móng dữ liệu + bảo mật**, M2 thêm **trí tuệ có trích nguồn**, M3 đóng vòng **hành động có kiểm chứng**. Mỗi mốc có mục tiêu sản phẩm, domain kích hoạt, năng lực bàn giao và UC chứng minh.

| Giai đoạn | Mục tiêu sản phẩm | Domain kích hoạt (P0) | Năng lực bàn giao | UC chứng minh |
|---|---|---|---|---|
| **M1 Ngày 1–30 — Nền móng** | Có dữ liệu tổ chức/thực thi đáng tin trong hệ thống; nhập liệu không ma sát ở 3 kênh đầu; nền bảo mật + audit + autonomy sẵn sàng | D01 Organization · D02 Admin & Security · D11 Project/Task/Workload · D08 KPI (cơ bản) · D09 OKR (cơ bản) · D03 Data Capture (C1 nhập tay, C5 Excel, C3 Word/PDF) · D26 AI Platform (Tool Registry, audit, Autonomy L0–L2, kill switch) | Onboarding DN trong 1 ngày; CRUD tổ chức/nhân sự/task; import Excel + tải Word/PDF tài liệu tổ chức/nhân sự/KPI-OKR; Tool Registry + audit log mọi tool call; kill switch toàn cục | UC-07 |
| **M2 Ngày 31–60 — Trí tuệ** | CEO hỏi được và nhận câu trả lời tổng hợp **có trích nguồn**; dữ liệu vào thêm qua ảnh + lời; chỉ số sức khỏe P0 bật cảnh báo | D27 CEO Assistant (hỏi đáp có trích nguồn) · D15 Finance Lite · D17 Sales Lite · D12 Meeting (biên bản/transcript → task) · D03 Data Capture (C4 chụp ảnh, C2 nhập bằng lời) · D28 Reporting (chỉ số sức khỏe P0 + cảnh báo ngưỡng) · Metric Store (FR-DATA-06) | CEO Assistant trả lời có `SourceRef`; Finance Lite + Sales Lite dựng chỉ số nguồn; transcript → action item → task; chụp ảnh/nhập lời → trích xuất → review; Metric Store tính sẵn chỉ số + cảnh báo khi vượt ngưỡng | UC-02, UC-06, UC-03 |
| **M3 Ngày 61–90 — Hành động** | Đóng vòng OBSERVE→…→VERIFY: AI chủ động briefing, khuyến nghị → phê duyệt → task (L3), theo dõi và cập nhật Decision Log | D27 CEO Daily Briefing · D26 Autonomy L3 (khuyến nghị → phê duyệt → task) · D13 Calendar (Google/Outlook hai chiều) · D28 Decision Log · D26 Evaluation Engine · D14 Knowledge | CEO Daily Briefing hằng ngày; luồng khuyến nghị → approve → tạo task + owner + deadline + lịch + thông báo (L3, undo ≥24h); Calendar 2 chiều; Decision Log ghi quyết định có AI; Evaluation Engine với bộ test chuẩn; thí điểm 1 DN 50–200 NV | UC-01, UC-04 |

> **UC coverage MVP (SKELETON §6):** M1 chứng minh UC-07; M2 chứng minh UC-02/UC-06/UC-03; M3 chứng minh UC-01/UC-04. Tập UC P0 = {UC-01, UC-02 (transcript), UC-03, UC-04, UC-06, UC-07}. UC-05, UC-08, UC-02 (AI dự họp) là P1.

### 2.1. Phụ thuộc giữa domain trong MVP (thứ tự kích hoạt)

Các domain không độc lập; thứ tự kích hoạt trong M1–M3 phản ánh chuỗi phụ thuộc dưới đây (mũi tên = "cần có trước").

| Domain đích | Phụ thuộc trước | Lý do |
|---|---|---|
| D08 KPI / D09 OKR | D01 Organization | KPI/OKR gắn owner là Employee/Department/Team |
| D11 Task/Workload | D01 Organization | Task có owner + đơn vị; workload tính trên Employee |
| D03 Data Capture | D02 Admin & Security, D26 Tool Registry | Ghi dữ liệu qua Action Registry cần quyền + tool; audit mọi commit |
| D15 Finance Lite / D17 Sales Lite | D03 Data Capture, D01 Organization | Số liệu Finance/Sales vào qua tài liệu/import; gắn đơn vị |
| D12 Meeting | D11 Task, D03 Data Capture | Transcript → action item → **task**; transcript vào qua C2/C3 |
| D28 chỉ số sức khỏe | D08/D09, D15/D17, D11, Metric Store | Chỉ số tổng hợp từ KPI/OKR/Finance/Sales/Task |
| D27 CEO Assistant | D26 AI Platform, mọi domain nguồn số liệu | Assistant gọi tool đọc theo quyền, trích nguồn từ Metric Store/entity |
| D27 Daily Briefing (L3) | D27 Assistant, D28 chỉ số, D13 Calendar, D28 Decision Log | Briefing tổng hợp + khuyến nghị → task → lịch; ghi Decision Log |
| D26 Evaluation Engine | D27 Assistant | Chấm chất lượng câu trả lời Assistant trên bộ test chuẩn |

> Hệ quả thứ tự: **D01 + D02 + D26 (Tool Registry/audit)** là nền phải xong sớm nhất trong M1; **D03 Data Capture** là nút thắt cho mọi domain nghiệp vụ; **D27 Assistant** phải có đủ domain nguồn trước khi bật Daily Briefing L3 ở M3.

### 2.2. Cổng nghiệm thu MVP (BRD §19.1 + §20.2)

MVP chỉ được coi là qua khi **đồng thời** đạt 4 cổng định lượng dưới đây (BRD §19.1) **và** chạy trọn kịch bản CEO 7 bước (BRD §20.2).

**Cổng định lượng (BRD §19.1):**

| # | Cổng | Ngưỡng |
|---|---|---|
| G1 | CEO dùng Daily Briefing | ≥ 4 ngày/tuần trong **4 tuần liên tiếp** |
| G2 | KPI/OKR cập nhật đúng kỳ | ≥ 80% |
| G3 | Dữ liệu mới vào qua tài liệu hoặc ngôn ngữ tự nhiên | ≥ 60% |
| G4 | Sự cố AI ghi sai trường trọng yếu mà không bị phát hiện | **Không có** |

> G1 chứng minh adoption thật của CEO; G2 chứng minh chất lượng dữ liệu thực thi; G3 chứng minh "nhập dễ như gửi file" (P09 Capture Once); G4 là ràng buộc an toàn tuyệt đối (P04 Human in the Loop + trường trọng yếu luôn qua người — xem 04). G4 liên kết chỉ số hỗ trợ §20.1 (Data Quality Score ≥ 90/100 ở domain cốt lõi, 6 tháng sau go-live).

**Kịch bản CEO — vòng khép kín 7 bước (BRD §20.2):** đây là bài nghiệm thu "đường hạnh phúc" của MVP; mỗi bước map tới domain/UC/Autonomy cụ thể.

| Bước | Hành động | Domain / năng lực | Map |
|---|---|---|---|
| 1 Ask | CEO hỏi "Tình hình công ty?" | D27 CEO Assistant (⌘K/chat) | UC-01 |
| 2 Understand | AI tổng hợp Finance, Sales, People, KPI, OKR, Projects, Risks **có nguồn** | D27 + D15/D17/D16/D08/D09/D11 + Metric Store; P05/P07 | UC-01 |
| 3 Investigate | "Tại sao doanh thu thấp?" — AI tự gọi tool | D27 + Tool Registry (READ tool, lọc theo quyền P06); AI Operating Loop UNDERSTAND→REASON | UC-03 |
| 4 Decide | AI đề xuất các phương án (Insight 9 phần) | D27 + D26 Policy Engine; Insight Observation→…→Action | UC-03/UC-04 |
| 5 Act | "Thực hiện phương án 1" — AI tạo task, owner, deadline, lịch, thông báo | D11 Task + D13 Calendar + D05 Notification; Autonomy **L3** qua Action Registry (undo ≥24h); APPROVAL tool chờ người (P04) | UC-04 |
| 6 Follow-up | AI theo dõi thực thi | D11 + D28 chỉ số; AI Operating Loop ACT→VERIFY | UC-04 |
| 7 Verify | AI đánh giá kết quả + cập nhật Decision Log | D28 Decision Log + D26 Evaluation Engine; North Star §20.1 (action verified) | UC-01/UC-04 |

> Vòng 7 bước là hiện thực hóa **AI Operating Loop** OBSERVE→UNDERSTAND→REASON→RECOMMEND→APPROVE→ACT→VERIFY→LEARN (SKELETON §9). Bước 5 (Act) là điểm Autonomy L3 duy nhất bắt buộc trong MVP; mọi tool WRITE/EXECUTION đi qua Action Registry + audit + undo; tool APPROVAL thì AI **không** tự gọi.

## 3. 5 phase sau MVP (BRD §19.2)

Phase 1 = chính MVP (§2). Phase 2–5 là backlog P1/P2 — **không** đặc tả ở đợt docs này; chỉ nêu domain để giữ đường traceability lộ trình.

| Phase | Tên | Domain / năng lực (ưu tiên) | Backlog |
|---|---|---|---|
| 1 | AI Executive & Work Core (MVP) | §2 — 20 domain P0 | — |
| 2 | Business Operations | D15 Finance đầy đủ · D18 Customer/CRM · D19 Partner · D16 HR nâng cao · D20 Procurement · D21 Contract Lifecycle · capture hóa đơn/hợp đồng/email (C6/C8) · XML hóa đơn (C8) · D04 Workflow Engine nâng cao · KPI tự động từ tích hợp · D12 AI dự Google Meet · D10 Performance Cycle đầy đủ | P1 |
| 3 | Product & Technical | D22 Product · D23 Engineering · Git/CI/CD · Infrastructure · technical debt · product analytics | P1 |
| 4 | Governance & Strategy | D24 Governance & Compliance · D25 Risk Intelligence nâng cao · D07 Strategy nâng cao · scenario planning | P1/P2 |
| 5 | Autonomous Enterprise | Assistant → Copilot → Agent → Multi-Agent → Enterprise Orchestrator; mở **L4** cho tool đã chứng minh độ tin cậy; AI chủ động Detect→Analyze→Recommend→Request Approval→Execute→Verify→Report | P2 |

> **Autonomy theo phase:** MVP mở L0–L3 (undo ≥24h); **L4 chỉ mở ở phase 5** cho tool đã chứng minh độ tin cậy qua Evaluation Engine (R-DEC-05 giữ nguyên; SKELETON §12bis). Không bật L4 trong MVP dưới bất kỳ điều kiện nào.

## 4. Ma trận ưu tiên đầy đủ 28 domain (BRD §19.3 + SKELETON §4/§12bis)

Ma trận này ánh xạ **năng lực BRD §19.3** sang **28 domain D01–D28** của registry, giữ nguyên quyết định P0/P1/P2 của BRD. "P0 cơ bản / P1" nghĩa là lát P0 (Lite/cơ bản) vào MVP, phần nâng cao hoãn P1.

| Domain | Tên | Ưu tiên | Lát P0 trong MVP | Năng lực BRD §19.3 liên quan |
|---|---|---|---|---|
| D01 | Organization | **P0** | Org/BU/Dept/Team/Employee/Position/Role đầy đủ | Organization, Employee |
| D02 | Administration & Security | **P0** | RBAC+ABAC, field-level security, audit, kill switch | Admin & Security |
| D03 | Data Capture & IDP | **P0** | C1–C5, pipeline, review, Action Registry, 14 doc type | Data Capture & IDP (mới) |
| D04 | Workflow & Approval Engine | **P0 cơ bản** / P1 | Approval cơ bản (phê duyệt khuyến nghị → task) | Workflow nâng cao = P1 |
| D05 | Notification | **P0** | Thông báo task/approval/cảnh báo ngưỡng | — |
| D06 | Integration Hub | **P0** (Google/MS) / P1 | Google/Outlook Calendar 2 chiều | Integration khác = P1 |
| D07 | Strategy Management | **P0 cơ bản** / P1 | Strategy/Objective cơ bản (liên kết KPI/OKR) | Strategy nâng cao = P1 (phase 4) |
| D08 | KPI Management | **P0** | KPI/Target/Measurement/check-in | KPI |
| D09 | OKR Management | **P0** | Objective/KeyResult/check-in | OKR |
| D10 | Performance Management | **P0 check-in** / P1 | Chỉ check-in | Performance Cycle đầy đủ = P1 (hạ từ P0) |
| D11 | Project / Task / Workload | **P0** | Project/Task/Workload đầy đủ | Task, Project, Workload |
| D12 | Meeting Intelligence | **P0** (transcript) / P1 | Meeting từ biên bản/transcript → task | AI dự Google Meet = P1 (hạ từ P0) |
| D13 | Calendar | **P0** | Calendar + đồng bộ Google/Outlook | Calendar |
| D14 | Knowledge / Documents | **P0** | Knowledge/Document cơ bản + lineage | Knowledge |
| D15 | Finance | **P0 Lite** / P1 | Finance Lite (ngân sách/chi phí/dòng tiền nguồn) | Nâng từ P1; Finance đầy đủ = P1 |
| D16 | Human Resources | **P0 cơ bản** / P1 | HR cơ bản (danh sách NV, phòng ban) | HR nâng cao = P1 |
| D17 | Sales / Business | **P0 Lite** / P1 | Sales Pipeline Lite | Nâng từ P1; CRM = P1 |
| D18 | Customer | **P1** | — | CRM/Customer = P1 (phase 2) |
| D19 | Partner | **P1** | — | Partner = P1 (phase 2) |
| D20 | Procurement / Vendor | **P1** | — | Procurement = P1 (phase 2) |
| D21 | Contract Lifecycle | **P1** | — | Contract Lifecycle = P1 (phase 2) |
| D22 | Product | **P1** | — | Product = P1 (phase 3) |
| D23 | Technical / Engineering | **P1** | — | Engineering = P1 (phase 3) |
| D24 | Governance & Compliance | **P2** | — | Governance & Compliance = P2 (phase 4) |
| D25 | Risk Management | **P1** | — | Risk Intelligence = P1 (phase 4) |
| D26 | AI Platform | **P0** | Tool Registry, Autonomy L0–L3, Evaluation, audit, kill switch | AI Assistant/Tool Registry/Autonomy L0–L3/Evaluation |
| D27 | CEO AI Assistant | **P0** | CEO Assistant + Daily Briefing + Decision Log | CEO Dashboard, Daily Briefing, chỉ số sức khỏe, Decision Log |
| D28 | Reporting & Analytics | **P0 cơ bản** | Chỉ số sức khỏe P0 + cảnh báo + Decision Log + báo cáo cơ bản | Dashboard/Daily Briefing/chỉ số/Decision Log |

> **Data Foundation (FR-DATA-01..08, SKELETON §4.1)** = **P0** xuyên suốt (master data, Data Quality Score, freshness, lineage, event backbone, Metric Store/Semantic layer, effective-dated, export). Không là một domain riêng mà là nền chung cho mọi domain P0; kích hoạt sớm trong M1 (master data + lineage + event backbone) và hoàn chỉnh ở M2 (Metric Store).

**Tổng kết đếm (SKELETON §12bis):** P0 = 20 domain (D01–D17 trừ phần nâng cao, D26, D27, D28) + Data Foundation. P1 = 6 domain trọng tâm backlog (D18, D19, D20, D21, D22, D23, D25) + phần nâng cao D04/D06/D10/D12. P2 = D24. **Kênh:** C1–C5 (P0) / C6–C10 (P1). **Autonomy:** L0–L3 (P0) / L4 (phase 5).

## 5. Thứ tự sinh tài liệu (CLAUDE.md §10.1)

Tài liệu được sinh theo cây phụ thuộc, **không** theo thứ tự số file:

```
Phase 1 — Core Product   : 02 Personas/Permissions → 03 Dashboard → 04 IDP
Phase 2 — Technical/Data  : 05 Data Model → 06 UI/UX → 07 Tech Arch → 08 Demo Data → 10 API → 11 Agent Workflow
Phase 3 — Governance      : 12 Doc Audit → 13 Decision Log → 14 Test Traceability
Phase 4 — Task Breakdown  : 09 (file này) — sinh CUỐI, sau khi 00–08,10–14 hoàn tất
```

- Q1–Q6 đã chốt (13 §1 — R-DEC-05..10). File 09 giữ vai trò **product roadmap** của đợt docs-first.
- Mỗi phase chỉ chuyển tiếp sau khi phase trước `verified` (doc-reviewer Approved) — CLAUDE.md §10.1.
- **Task chi tiết `T-*` được sinh ở đợt code (R-DEC-09)**, sau khi docs 00–14 được human promote `current`. Đợt docs này **không** sinh `T-*`, không sinh `TC-*` chi tiết, không viết field-level DB (hoãn sang 05 + đợt code).

## 6. Task đợt code — build MVP v3 từ nền v2.1 (R-DEC-15, R-DEC-19)

> Sinh ở đợt code theo R-DEC-09/R-DEC-15. Quyết định nền của kế hoạch: 13 §2ter (R-DEC-15..27). Nền v2.1 (`apps/`) được **tái dùng và refactor**, không viết lại từ đầu. `M1.0` (role 10→7, `tenant_id`, `scope_pillars` — R-DEC-12/12a/13) **đã xong** (commit `8ec9cdb`, 14 §1.4).

### 6.0. Quy trình mỗi phase — vòng S → C → F → B → N → R

| Bước | Việc | Đầu ra | Dừng chờ human |
|---|---|---|---|
| **S — Spec lock** | Chốt vào docs những gì phase chạm tới: EP (10 §7.2), event/tool/mã lỗi (10), field-level (05), SCR (06 §3.4), `TC-*` (14), DEC mới (13) | diff docs | ⏸ **duyệt diff** |
| **C — Contract** | Pydantic schema + route stub `501`; sinh `packages/shared-types` từ OpenAPI (`scripts/gen_shared_types.py`); fixture mock có type | type FE = BE | — |
| **F — FE trên mock** | Màn hình + i18n vi/en + Vitest + Playwright project `mock`, chạy `API_MODE=mock` (không cần backend) | UI xem được | — |
| **B — BE** | model → migration reversible → repository (lọc tenant) → service → route → outbox/event → tool/ACT → seed; pytest unit/integration/event | API thật | — |
| **N — Nối** | Tắt mock cho domain, Playwright project `real` trên stack seed; đối chiếu số UI ↔ DB | E2E xanh | — |
| **R — Review + gate** | Gate DoD (CLAUDE.md §3.3), coverage (14 §1.3), 14 `Planned → Passed`, tick task ở 09 §6, STATE.md, `/code-review`; PR nhánh phase → `ai-eos` | PR | ⏸ **duyệt + merge** |

- **Git:** mỗi phase một nhánh `v3/<phase>-<slug>` tách từ `ai-eos`; mỗi task một Conventional Commit; agent không tự merge, không force push.
- Phase sau chỉ bắt đầu khi PR phase trước đã merge. Task size L hoặc đổi kiến trúc → chờ human (CLAUDE.md §7).
- **Không thêm dependency** ngoài DEC: mock FE = route handler BFF (không MSW); sinh type = script stdlib; OAuth = `httpx`; RAG = pgvector + embedding qua ModelGateway; email = `smtplib`; PWA = manifest + service worker tự viết.
- Cột "Trạng thái" của mọi bảng task: `☐` chưa làm · `◐` đang làm · `☑` xong (tick ở bước R).

### 6.0bis. Chạy tự động chuỗi M1.3 → M1.4 → M1.5 → M1.6 (R-DEC-38, R-DEC-39)

> Ngoại lệ có chủ đích với §6.0 cho **riêng** chuỗi này (human chốt 2026-10-24). M2.x trở đi quay lại vòng §6.0 chuẩn trừ khi có DEC mới.

| Mục | Quy tắc chuỗi auto |
|---|---|
| Bước S | Spec lock của **cả 4 phase** viết trước (nhánh `v3/m1.3-m1.6-speclock`: §6.4–§6.7, 05 §2.5–§2.8, 06 §3.4, 10 §7.2.2–§7.2.5, 13 R-DEC-38..79, 14 §1.7–§1.10) và **human duyệt một lần** trước khi chạy. Session auto **không** dừng ở S. Task trong Spec lock đã duyệt coi như đã được human duyệt plan (kể cả size L — CLAUDE §7) |
| Điều kiện bắt đầu | M1.2 đóng xong (T-618 ☑, commit cuối trên `v3/m1.2-org-admin`) **và** nhánh speclock đã merge/rebase vào tip M1.2 (docs không lệch) |
| Nhánh | **Xếp chồng**: `v3/m1.3-work` ← tip `v3/m1.2-org-admin`; `v3/m1.4-goals` ← tip `v3/m1.3-work`; `v3/m1.5-capture` ← tip m1.4; `v3/m1.6-ai-onboarding` ← tip m1.5. Phase sau bắt đầu khi phase trước xong bước R, **không chờ merge** |
| Bước R | Mỗi phase: kiểm tra nhanh xanh, `/code-review` + sửa finding, tick 09, 14 `Planned → Implemented`, STATE.md; PR (base = nhánh phase trước) chỉ mở khi human cho push; **không tự merge**. Human review/merge cả chuỗi ở cuối |
| Test | Mỗi task: kiểm tra nhanh — FE `pnpm lint && pnpm typecheck && pnpm test`; BE `uv run ruff check . && uv run ruff format --check . && uv run mypy` + `uv run pytest <file test liên quan>`; commit gắn `[full-test pending]`. **Full test một lần ở cuối chuỗi** (sau T-652): gate DoD CLAUDE §3.3 đầy đủ + `pytest --cov` (ngưỡng 14 §1.3) + `alembic downgrade -1 && upgrade head` qua từng migration mới + Playwright `mock` + `real` (stack seed, `demo_reset.sh -y`). Đỏ → sửa thật (không skip) tới khi xanh, rồi 14 `Implemented → Passed` |
| Song song (subagent) | Phase chạy **tuần tự**. Trong một phase, sau bước **C** (schema + stub `501` + `packages/shared-types` sinh lại): **F** (FE trên mock) và **B** (BE) chạy song song ở 2 worktree riêng; B giữ thứ tự migration/task trong bảng phase. Bước **N** (nối + E2E) sau khi cả F và B xong. Không cho 2 agent cùng sửa một file dùng chung (`messages/{vi,en}.json`, `permission_matrix.py`, `core/events/registry.py`, migration) — người điều phối gộp |
| Dừng → `BLOCKED` (CLAUDE §6.8) | Gate A/B/C fail; cần dependency/endpoint/field/event/tool **ngoài** Spec lock đã duyệt; spec mâu thuẫn; cùng một lỗi build/test sửa 3 lần không xong; phát hiện credential lộ; lệnh phá hủy. BLOCKED → ghi STATE.md + dừng chuỗi (không nhảy phase) |
| Tiến độ | Sau mỗi task: commit + dòng tiến độ STATE.md (task, commit, kiểm tra nhanh); sau mỗi phase: tóm tắt phase trong STATE.md |

### 6.1. Bản đồ phase ↔ mốc MVP

| Mốc (09 §2) | Phase | Domain | UC chứng minh | Nhánh |
|---|---|---|---|---|
| M1 Nền móng | M1.0 ☑ · M1.1 · M1.2 · M1.3 · M1.4 · M1.5 · M1.6 | D01, D02, D03 (C1/C3/C5), D04, D05, D07–D11, D26 | UC-07 | `v3/m1.x-*` |
| M2 Trí tuệ | M2.1 · M2.2 · M2.3 · M2.4 · M2.5 | D28, D15, D16, D17, D03 (C2/C4), D12, D27 | UC-02, UC-06, UC-03 | `v3/m2.x-*` |
| M3 Hành động | M3.1 · M3.2 · M3.3 · M3.4 · M3.5 | D06, D13, D26 (L3, Evaluation), D27 Briefing, D28 Decision Log, D14 | UC-01, UC-04, kịch bản CEO 7 bước | `v3/m3.x-*` |

```
M1.1 ─► M1.2 ─► M1.3 ─► M1.4 ─► M1.5 ─► M1.6 ─► M2.1 ─► M2.2 ─► M2.3 ─► M2.4 ─► M2.5 ─► M3.1 ─► M3.2 ─► M3.3 ─► M3.4 ─► M3.5
```

### 6.2. M1.1 — Nền build v3 (nhánh `v3/m1.1-foundation`)

**Mục tiêu:** khung để mọi phase sau chạy vòng S→R; trả nợ M1.0; seed v3; IA v3. **Không thêm endpoint backend** (10 §7.2).

| T | Việc | File chính | Spec | TC | Trạng thái |
|---|---|---|---|---|---|
| T-601 | Ghi DEC kế hoạch R-DEC-15..27 vào 13 §2ter | 13 | — | — | ☑ |
| T-601b | Ghi 09 §6 (file này); Spec lock M1.1: 10 §1.4/§7.1/§7.2/§9.1, 05 §2.3/§5/§7, 06 §3.4/§5.3, skeleton quy ước ID, 14 §1.5 | docs | R-DEC-15 | — | ☑ |
| T-602 | Sửa 4 contract test hỏng: khôi phục 10 §1.4 phản chiếu `core/errors.py`; cập nhật docstring test trỏ R-DEC-18 | `tests/contract/test_api_contract.py`, 10 §1.4 | R-DEC-18 | TC-SYS-003, TC-M11-01 | ☑ |
| T-603 | **Lọc tenant bắt buộc**: `core/tenant.py` (contextvar `current_tenant`, `tenant_scope()`); set ở dependency auth + wrapper consumer Celery + vòng lặp job beat; `BaseRepository` lọc/gán `tenant_id`, thiếu tenant → raise; migration `0010_tenant_outbox` (`platform.outbox_events.tenant_id`); `publish_in_tx` ghi tenant; relay đưa vào envelope; test kiến trúc cấm `select(<BusinessModel>)` ngoài repository; fixture test set tenant mặc định | `core/tenant.py`, `core/base_repository.py`, `core/deps.py`, `core/events/*`, `workers/*`, `alembic/versions/0010_*`, `tests/architecture/`, `tests/integration/test_tenant_isolation.py` | R-DEC-13/21, 05 §2.3, 10 §9.1 | TC-M11-02..05 | ☑ |
| T-603b | **Seed v3 toàn bộ theo 08**: ABC 7 phòng ban (08 §2.1), ~150 NV + quản lý trực tiếp + dự án chéo phòng; user demo: CEO; DIR Kinh doanh `{C}`, Tài chính `{F}`, Nhân sự `{O}`, Sản phẩm/Công nghệ `{U}`; MGR Vận hành & Dịch vụ, Hành chính; EMP; REV; ADM; actor AI (08 §2.1, R-DEC-27); dữ liệu UC-01/02/03/04/06/07 trên entity **đã có**; product/risk gắn vào ABC; tổng/tỷ lệ tính bằng script; idempotent; xuất `seed_snapshot.json` cho mock FE; sửa test assert số liệu v2.1 (DEC-230/231 superseded) | `apps/api/src/app/seed/**`, `scripts/demo_reset.sh`, test liên quan | R-DEC-23, 08 | TC-M11-06, TC-M11-07 | ☑ |
| T-605 | **Sinh shared types**: `scripts/gen_shared_types.py` (stdlib) đọc `create_app().openapi()` → `packages/shared-types/src/generated.ts`; contract test drift (file sinh lại phải trùng) | `scripts/gen_shared_types.py`, `packages/shared-types/src/` | R-DEC-19 | TC-M11-08 | ☑ |
| T-604 | **Mock harness BFF**: `API_MODE=mock` (env server) → `app/api/backend/[...path]` gọi `src/mocks/router.ts` (bảng `METHOD path → handler`, store in-memory theo phiên, envelope/lỗi như BE, SSE giả cho chat); `lib/auth.ts` `authorize()` nhánh mock với 7 role (claim như JWT thật); fixture lấy từ `seed_snapshot.json`; chặn `API_MODE=mock` khi `NODE_ENV=production` | `apps/web/src/app/api/backend/[...path]/route.ts`, `apps/web/src/lib/{auth,server-env}.ts`, `apps/web/src/mocks/**` | R-DEC-25 | TC-M11-09, TC-M11-10 | ☑ |
| T-606 | **Playwright 2 project**: `mock` (webServer `API_MODE=mock`, chạy mọi PR) và `real` (stack seed); tách helper login | `apps/web/playwright.config.ts`, `apps/web/e2e/helpers.ts` | — | TC-M11-11 | ☑ |
| T-607 | **IA v3 + chuyển route**: Sidebar 8 mục + Quản trị lọc theo role (06 §3.1/§3.2/§3.4); route khung SCR-40..50 (trang "Sắp có"); chuyển SCR-03/16/18a/18b/47/48/43 sang route v3; redirect 308 trong `middleware.ts`; i18n vi/en; sửa 9 spec E2E cũ | `components/shell/Sidebar.tsx`, `middleware.ts`, `lib/permissions.ts`, `app/(app)/**`, `messages/{vi,en}.json`, `e2e/*.spec.ts` | 06 §3.4, R-DEC-25 | TC-M11-12, TC-M11-13 | ☑ |
| T-608 | **Đóng băng product/risk**: bỏ khỏi Sidebar; Executive mặc định không hiện card U/S (bố cục 5 trụ chỉ ở SCR-03); tool AI product/risk gắn `p1_frozen` và không quảng bá cho model | `features/dashboard/*`, `modules/ai/tools/registry.py` | R-DEC-16 | TC-M11-14 | ☑ |
| T-609 | E2E login + điều hướng 7 role trên project `real` (nợ M1.0) | `e2e/login.spec.ts`, `e2e/roles.spec.ts` | 02 | TC-M11-15 | ☑ |
| T-610 | Đóng phase: 14 §1.5 → Passed, tick 09 §6.2, STATE.md, `/code-review`, PR → `ai-eos` | — | — | — | ◐ (PR/push chờ human) |
| T-610b | **Hoàn thiện đăng nhập demo + rebuild image** (human yêu cầu): rebuild `aureon-api:local` / `aureon-web:local`; `DEMO_ACCOUNTS` 5 → **10 tài khoản** (đủ 7 role, 4 khối DIR) khớp `auth_seed.DEMO_USERS`; dropdown → **lưới nút đăng nhập nhanh** một cú bấm (điền email + đăng nhập ngay; mật khẩu vẫn giải ở server qua cờ `demo`, **không** đưa vào `NEXT_PUBLIC_*` — CLAUDE §5.8/§6.4); `demoPasswordFor` phủ 10 email; gỡ khối `NEXT_PUBLIC_DEMO_PASSWORD_*` khỏi `.env.example`; i18n vi/en 10 nhãn; `loginAs` E2E bấm nút theo `demoTestId` | `apps/web/src/lib/{demo-accounts,server-env}.ts`, `features/auth/LoginForm.tsx`, `messages/{vi,en}.json`, `e2e/helpers.ts`, `.env.example` | 06 §3.4 | TC-M11-16 | ☑ |
| T-610c | **Đăng nhập demo: dropdown + autofill + con mắt** (human yêu cầu, sau T-610b): lưới 10 nút → **một dropdown** (native select) 10 tài khoản `DEMO_ACCOUNTS`; chọn → Route Handler `POST /api/demo-credentials` (`{email}` → `{ data: { email, password } }`) điền email + mật khẩu, **không tự submit** (submit `demo: "false"`; nhánh `demo: "true"` giữ làm fallback); thiếu mật khẩu → gợi ý `auth.demoPasswordMissing`; route chỉ bật khi `DEMO_MODE=true` **và** `DEMO_LOGIN_AUTOFILL=true` (server-only), email ngoài whitelist / cờ tắt → 404, `no-store`, không log mật khẩu, `API_MODE=mock` → `MOCK_LOGIN_PASSWORD`; nút con mắt Eye/EyeOff (`aria-pressed`, ≥ 44 px); `.env.example` thêm `DEMO_LOGIN_AUTOFILL=false`; i18n vi/en; `loginAs` E2E theo dropdown | `apps/web/src/app/api/demo-credentials/route.ts`, `apps/web/src/lib/{demo-accounts,demo-credentials,server-env}.ts`, `features/auth/LoginForm.tsx`, `messages/{vi,en}.json`, `e2e/{helpers.ts,login.spec.ts}`, `.env.example` | 06 §3.4, R-DEC-28 | TC-M11-16, TC-M11-17 | ◐ (chờ human test tay + full suite) |

**Thứ tự:** T-601 → T-601b → ⏸ duyệt → T-602 → T-603 → T-603b → T-605 → T-604 → T-606 → T-607 → T-608 → T-609 → T-610 ⏸.
**Exit M1.1:** gate DoD xanh (contract 11/11); `pnpm test:e2e --project=mock` chạy không cần backend; test chứng minh tenant B không đọc/ghi dữ liệu tenant A (cả request và worker); seed v3 đúng 08 §2.1; route v2.1 redirect 308 đúng; Sidebar đúng 7 role; coverage bảo mật ≥ 90%.

### 6.3. M1.2 — D01 Organization + D02 Admin & Security + D05 Notification (nhánh `v3/m1.2-org-admin`)

**FE (mock trước):** `/admin/org` cây Organization → Department → Team → Employee + panel chi tiết + chọn mốc ngày (`as_of`); `/admin/positions`; `/admin/users` (tạo/mời, gán role + `scope_pillars`, khóa/mở); `/admin/roles` (ma trận quyền, chỉ đọc); `/admin/audit` thêm lọc `from`/`to`/`actor_type`; chuông thông báo ở Header. Form rhf + zod; mọi chuỗi qua i18n. SCR (bước S, đề xuất): SCR-51 `/admin/org`, SCR-52 `/admin/positions`, SCR-53 `/admin/users`, SCR-54 `/admin/roles`, SCR-14 `/admin/audit`; chuông = component Header (06 §3.4).

| T | Việc | File chính | Spec | TC | Trạng thái |
|---|---|---|---|---|---|
| T-611S | **Spec lock M1.2** (bước S): 10 §7.2.1 (EP-ORG-01..24, EP-HR-01..05, EP-ADM-05..12, EP-NTF-01..05) + §9.2 (2 event); 05 §2.4/§6ter; 06 §3.4 (SCR-51..54, chuông); 14 §1.6; 13 R-DEC-29..37 | docs | R-DEC-15 | — | ☑ (`928cdcf`; R-DEC-29..37 còn proposed) |
| T-611 | ENT-Organization trong schema `hr` (R-DEC-24; **BusinessUnit hoãn** — OQ-05-06); `Department.organization_id` + `valid_from/valid_to`, `parent_id` (đã có) chặn vòng; `teams.valid_from/valid_to`; unique `code` theo tenant; migration reversible `0011` + backfill | `modules/hr/models`, `alembic/versions/0011_*` | 05 §2.4 | TC-M12-01, TC-M12-16 | ◐ (`a96036a`, full test dồn cuối phase) |
| T-612 | Effective-dated cơ cấu (FR-ORG-04, 05 §6ter): `hr.employee_assignments(employee_id, department_id, team_id, position_id, manager_id, valid_from, valid_to)` nửa mở, ≤ 1 hiện hành/NV, không chồng (service + khóa dòng); cột cache `employees.*` đồng bộ; truy vấn "tại ngày X" | `modules/hr/{models,repositories,services/org_service.py}` | 05 §2.4, EP-ORG-21..23 | TC-M12-02, TC-M12-03 | ◐ (`12eb43c`, full test dồn cuối phase) |
| T-613 | API ORG: CRUD organization/team/position (`/org/*`), department giữ `/hr/departments` (R-DEC-29) + archive; `GET /org/tree?as_of=`; assignments; employee CRUD v2.1 nối phân công; ghi cơ cấu `hr:admin` (R-DEC-30) — sửa `core/permissions.py` + `permission_matrix.py`; audit + outbox `hr.org_structure_changed` | `modules/hr/{routes,schemas,services}`, `core/permissions.py`, `auth/permission_matrix.py`, `core/events/registry.py` | 10 §7.2.1, §9.2 | TC-M12-04..07, TC-M12-11 | ◐ (`3a9bbfc`, full test dồn cuối phase) |
| T-614 | API ADM: `GET/POST/PATCH /platform/users`, `POST /platform/users/{id}/deactivate` + `/reactivate` (R-DEC-36), `GET /platform/roles`; audit-logs EP-52 thêm `from`/`to`/`actor_type`; thu hồi refresh token khi khóa/đổi role; audit + outbox `auth.user_access_changed` mọi mutation | `modules/auth/{routes/users.py,services/user_admin_service.py,repositories}`, `modules/platform/{routes,services/audit_query.py}` | 10 §7.2.1 | TC-M12-06, TC-M12-08..11 | ◐ (`8e63057`, full test dồn cuối phase) |
| T-615 | Field-level security tổng quát: registry `core/field_policy.py` mask mức 3/4 ở serializer mọi module (không chỉ HR), dùng chung cho audit/event/PII filter (R-DEC-34) | `core/field_policy.py`, `core/audit.py`, `modules/*/schemas` | 05 §2.4, 02 §5 | TC-M12-12 | ◐ (`ed55aa5`, full test dồn cuối phase) |
| T-616 | Notification in-app: `GET /notifications`, `POST /notifications/{id}/read`, `POST /notifications/read-all`, `GET/PATCH /notifications/preferences` (quyền `(token)` — R-DEC-31); `notifications.tenant_id` | `modules/platform/{routes/notifications.py,services/notification_service.py,models}` | 10 §7.2.1, 05 §2.4 | TC-M12-13, TC-M12-14, TC-M12-16 | ◐ (`97791c2`, full test dồn cuối phase) |
| T-616b | Email (R-DEC-20/33): `platform/services/email_sender.py` (`smtplib`) + Celery task retry 3 lần, idempotent theo `notification.id` (`email_status`), job beat quét `PENDING`; template theo `kind` + link, không `title/body`, không mức 3–4; `SMTP_*` qua ConfigService + `.env.example` placeholder; Mailpit trong `docker-compose.yml`; tùy chọn theo loại (`notification_preferences`, R-DEC-32) | `modules/platform/services/email_sender.py`, `workers/*`, `core/config.py`, `.env.example`, `docker-compose.yml` | R-DEC-20, 05 §2.4 | TC-M12-14, TC-M12-15 | ◐ (`95d81c7`, full test dồn cuối phase) |
| T-617 | Seed bổ sung Organization ABC + phân công effective-dated (≥ 1 NV có lịch sử chuyển phòng); `seed_snapshot.json` cho mock | `apps/api/src/app/seed/**` | 08 §2.1, R-DEC-23 | TC-M12-17 | ✓ `aa4905b` Passed 2026-10-24 |
| T-617F | FE trên mock: SCR-51 `/admin/org`, SCR-52 `/admin/positions`, SCR-53 `/admin/users`, SCR-54 `/admin/roles`, SCR-14 lọc, chuông Header; mock router + i18n vi/en | `apps/web/src/{app/(app)/admin/**,features/admin/**,components/shell/Header.tsx,mocks/**}`, `messages/{vi,en}.json` | 06 §3.4 | TC-M12-18 | ✓ `086ed8d`,`e383819` Passed 2026-10-24 |
| T-618 | Nối + E2E `admin-org.spec.ts` (ADM tạo phòng ban → gán NV → CEO thấy trên cây; `as_of` quá khứ; khóa user; EMP bị 403; email trên Mailpit); đóng phase | `apps/web/e2e/admin-org.spec.ts` | 09 §6.3 | TC-M12-19 | ✓ `343e0ef` Passed 2026-10-24 |

**Thứ tự:** T-611S ⏸ → T-611 → T-612 → T-615 → T-613 → T-614 → T-616 → T-616b → T-617 → T-617F (song song sau C) → T-618 ⏸.

**Exit:** dựng cây tổ chức bằng tay (một phần UC-07); xem cơ cấu tại mốc quá khứ; email nhận được trên Mailpit; service ≥ 80%, bảo mật ≥ 90%.

### 6.4. M1.3 — D11 Project/Task/Workload + D04 Approval cơ bản (nhánh `v3/m1.3-work`)

**FE (mock trước):** `/work` Task của tôi (lọc hạn/trạng thái) + tab Nhóm (kanban), `/work/projects` (+ cờ trễ), `/work/projects/[id]` (milestone), `/work/workload` (heatmap người × tuần, ngưỡng 110%/2 tuần), `/work/approvals` (inbox + duyệt). **BE:** path `/work/*`, `/workflow/*` (R-DEC-39/40), dependency, sub-task, `source_ref`, event, notification, rule approval cơ bản.

| T | Việc | File chính | Spec | TC | Trạng thái |
|---|---|---|---|---|---|
| T-619S | **Spec lock M1.3** (bước S, gộp chuỗi M1.3–M1.6): 10 §7.2.2 (EP-TASK-01..19, EP-WF-01..03) + §9.2 (`execution.task_created`, `execution.task_completed`, `execution.task_overdue` cập nhật, `platform.approval_*`) + claim `employee_id` (§7.2.2); 05 §2.5; 06 §3.4 (SCR-42/43 đầy đủ, SCR-55..57); 14 §1.7; 13 R-DEC-40..49 | docs | R-DEC-15, R-DEC-38 | — | ☐ |
| T-619C | **Bước C:** schema Pydantic mới/đổi (`TaskCreate/Update/Out` + `parent_task_id`, `source_ref`; `TaskDependency*`, `ProjectDetailOut`, `WorkloadOut`, `ApprovalRequestOut` + `target_kind/title_key/params/...`), route `/work/*`, `/workflow/*` stub `501` (EP-TASK-06..08, 14..19, EP-WF-01/02), chuyển path EP-TASK-01..05, 09..13, EP-WF-03 (hành vi giữ), `shared-types` sinh lại, sửa test path | `modules/execution/{schemas,routes/work.py}`, `modules/platform/{schemas,routes/workflow.py}`, `packages/shared-types`, `tests/integration/execution/**`, `tests/integration/ai/**` | 10 §7.2.2, R-DEC-40 | TC-M13-14 | ☐ |
| T-619 | Task: claim `employee_id` + scope "chính mình" (R-DEC-41); migration `0014` (`parent_task_id`, `source_ref` + backfill, `task_dependencies`, backfill assignee, `projects.initiative_id`); `TaskService.create` nhận `source_ref` + `parent_task_id` (dùng bởi `ACT-create_task` M1.5); service sub-task 1 cấp, dependency chặn vòng + chặn `done` | `core/{security,deps}.py`, `modules/auth/services/auth_service.py`, `modules/execution/{models,repositories,services/task_service.py,services/scope.py,services/task_rules.py}`, `alembic/versions/0014_work_tasks_m13.py` | 05 §2.5, R-DEC-41/42/43 | TC-M13-01, 02, 03 | ☐ |
| T-620 | `GET /work/workload?week=` (`weekly_grid` dùng chung heatmap EP-49) + project `progress/planned/late` + milestone theo project (`project_rules.py` dùng chung OPS-02) | `modules/execution/services/{workload.py,project_rules.py,metrics.py,dashboard_service.py,meeting_service.py}`, `routes/work.py` | EP-TASK-09..18, R-DEC-44/49 | TC-M13-05 | ☐ |
| T-621 | Event `execution.task_created` / `task_completed` (extension registry) + `task_overdue.days_late`; xác minh beat 08:30 (test cấu hình); `AFFECTS` thêm 2 event | `core/events/registry.py`, `modules/execution/services/task_service.py`, `modules/platform/events/consumers.py`, `tests/events/**` | 10 §9.2, R-DEC-47 | TC-M13-04 | ☐ |
| T-622 | Approval: migration `0015` (`target_kind`, `department_id`); rule đọc DB; inbox `assigned_to=me` + scope; detail; decide EP-WF-03; `RULE-task_reassign` + EP-TASK-19 + hook `task_reassign`; outbox `platform.approval_*`; sửa chuỗi EP trong AI tool registry | `modules/platform/{models,repositories,services/approval_service.py,routes/workflow.py}`, `core/approval_hooks.py`, `modules/execution/services/task_service.py`, `modules/ai/tools/registry.py`, `alembic/versions/0015_workflow_approvals_m13.py` | EP-WF-01..03, EP-TASK-19, R-DEC-45 | TC-M13-06, 07, 08 | ☐ |
| T-623 | Notification in-tx: `task_assigned` (tạo/đổi người), `reminder` (job overdue), task hoàn thành → báo người giao (`owner_id`, kind `system`, R-DEC-46), `approval_requested`/`approval_decided`; map employee→user qua `auth` public service | `modules/execution/services/task_service.py`, `modules/platform/services/{approval_service,notification_service}.py`, `modules/auth/services/**` (hàm public `user_id_for_employee`), `workers/jobs.py` | R-DEC-46 | TC-M13-09, 10 | ☐ |
| T-624 | Seed bổ sung: dependency, sub-task, `source_ref` (họp/tài liệu), milestone 3 dự án (1 trễ), 1 approval `task_reassign` PENDING ở SVC cho inbox MGR; xác minh OPS-01/OPS-02/HR-03 giữ 08 §5; sinh lại `seed_snapshot.json` | `apps/api/src/app/seed/{exec_data,execution_seed,snapshot}.py`, `tests/integration/test_seed_v3.py`, `apps/web/src/mocks/seed_snapshot.json` | 08 §3/§5, R-DEC-23 | TC-M13-11 | ☐ |
| T-625F | FE trên mock: SCR-42 (Task của tôi + kanban), SCR-55, SCR-56, SCR-57, SCR-43; mock router `/work/*`, `/workflow/*` (cùng luật scope/409/422); `permissions.ts` (route con + tab); i18n vi/en; cập nhật `roles.spec.ts` | `apps/web/src/{app/(app)/work/**,features/work/**,mocks/{work,workflow,router}.ts,lib/{permissions,query-keys}.ts}`, `messages/{vi,en}.json`, `e2e/roles.spec.ts` | 06 §3.4, R-DEC-48 | TC-M13-12 | ☐ |
| T-625 | Nối + E2E `work.spec.ts` (MGR giao task → EMP thấy + có thông báo + email Mailpit; heatmap hiện 3 người quá tải; EMP đề nghị chuyển → MGR duyệt; EMP bị `/403`); dọn dữ liệu E2E; đóng phase (09 tick, 14 `Implemented`, STATE.md) | `apps/web/e2e/work.spec.ts`, `apps/web/e2e/support/work_e2e.py` | 09 §6.4 | TC-M13-13, 14 | ☐ |

**Thứ tự:** T-619S ⏸ (duyệt chung chuỗi) → T-619C → {**B:** T-619 → T-620 → T-621 → T-622 → T-623 → T-624} ‖ {**F:** T-625F} (song song sau C, 2 worktree; `permission_matrix.py` không đổi, `core/events/registry.py` + `messages/*.json` + migration do người điều phối gộp) → T-625 (N). Mỗi task kiểm tra nhanh + `[full-test pending]`; full test dồn cuối chuỗi (sau T-652).

**Exit:** METRIC-OPS-01 (hoàn thành đúng hạn), METRIC-OPS-02 (dự án trễ), METRIC-HR-03 (quá tải) tính được từ dữ liệu và **khớp** số hiển thị ở SCR-55/SCR-57 (85% / 1 dự án = 10% / 3 người = 12% trên seed); MGR giao task → EMP thấy + có thông báo; inbox duyệt chạy; service ≥ 80%, bảo mật ≥ 90%.

### 6.5. M1.4 — D07 Strategy · D08 KPI · D09 OKR · D10 check-in (nhánh `v3/m1.4-goals`)

**FE:** `/goals` cây alignment Strategy → StrategicObjective → {KPI | Objective → KR} kèm Initiative → Project; chi tiết KPI (target theo kỳ, đồ thị measurement, trạng thái ngưỡng); chi tiết OKR (KR, confidence, lịch sử check-in); thẻ **check-in F4** cho EMP (giá trị, độ tự tin, ghi chú; phần "AI điền sẵn" nối ở M2.4).

**Danh sách file FE/test/khác phải sửa do đổi path (R-DEC-39/58) — đã grep toàn repo:**
- BE route: `apps/api/src/app/modules/execution/routes/router.py` (tách `routes/goals.py`, `routes/kpis.py`, `routes/okr.py`; gỡ handler `/execution/{objectives,kpis,check-ins,initiatives}*`).
- Docstring/label EP: `execution/services/{kpi_service,okr_service,initiative_service,meeting_service}.py`, `execution/schemas/{okr,initiatives,meetings}.py` (nhãn EP-45/46/47/48 → EP-STR/KPI/OKR/PRF).
- AI: `apps/api/src/app/modules/ai/tools/registry.py` (nhãn `endpoint` của `TOOL-list_objectives`, `TOOL-get_kpi_status`, `TOOL-record_kpi_measurement`) + `tests/unit/test_ai_tool_registry.py` nếu assert nhãn.
- Test BE: `apps/api/tests/integration/execution/test_okr_kpi.py` (37 chỗ), `test_initiatives.py` (15), `test_metrics_provider.py` (2); `tests/integration/execution/helpers.py` (thêm factory `make_objective/make_kpi/make_strategic_objective`); test mới `tests/integration/goals/test_*_t62x.py`; `tests/unit/test_execution_kpi.py`, `test_execution_rules.py` (đo nhiều dòng, at-risk, G2).
- Sinh type: `packages/shared-types/src/generated.ts` (29 path `/execution/{kpis,objectives,check-ins,initiatives}`) — sinh lại bằng `scripts/gen_shared_types.py`, contract drift test.
- Event/metric: `core/events/registry.py`, `platform/services/catalog.py`, `platform/events/consumers.py` (AFFECTS).
- FE + mock: **hiện không có** caller `/execution/{kpis,…}` trong `apps/web/src` hay `apps/web/e2e` (đã grep) → không có file FE "sửa path"; chỉ **thêm** `src/mocks/goals.ts`, sửa `src/mocks/router.ts` (gộp `GOALS_ROUTES`), `src/mocks/router.test.ts`, `src/mocks/fixtures.ts`/`seed_snapshot.json` (sinh lại từ `app/seed/snapshot.py` — thêm strategies/SO/initiatives/check-ins/evaluations), `src/lib/permissions.ts` (+test) cho route con, `app/(app)/goals/page.tsx` (thay `ComingSoon`), `messages/{vi,en}.json`, `e2e/goals.spec.ts` (mới), `e2e/support/seed.ts` nếu cần reset check-in.
- Seed: `app/seed/exec_data.py`, `execution_seed.py`, `snapshot.py`; `tests/integration/test_seed_v3.py`, `tests/unit/test_seed_v3_data.py`.

| T | Việc | File chính | Spec | TC | Trạng thái |
|---|---|---|---|---|---|
| T-626S | Spec lock M1.4: 10 §7.2.3/§9.2, 05 §2.6/§6ter, 06 §3.4 (SCR-41, 58..60), 13 R-DEC-50..59, 14 §1.8, 09 §6.5 | docs | R-DEC-38 | — | ☐ |
| T-626 | ENT-Strategy + StrategicObjective (R-DEC-50): model, repo, migration `0016` + backfill (`projects.initiative_id` đã có từ M1.3/0014), `initiatives.strategic_objective_id`/`objective_id` nullable; `goal_scope.py` khung | `execution/models`, `alembic/versions/0016_goals_strategy_m14.py`, `execution/services/{strategy_service,goal_scope}.py` | 05 §2.6 | TC-M14-01, 06 | ☐ |
| T-626C | Bước C: schema Pydantic + router mới (`/goals/*`, `/kpis/*`, `/objectives/*`, `/key-results/*`) stub `501`, gỡ path `/execution/*` tương ứng, sửa test path, sinh lại `shared-types` | `execution/routes/{goals,kpis,okr}.py`, `execution/schemas/{strategy,okr,kpi}.py`, `packages/shared-types` | 10 §7.2.3 | TC-M14-05 | ☐ |
| T-626F | FE cây `/goals` (SCR-41) trên mock: `features/goals/GoalTree.tsx`, `goal-tree.ts`, `use-goals.ts`, `src/mocks/goals.ts` + snapshot | `apps/web/src/features/goals/*`, `src/mocks/*` | SCR-41 | TC-M14-17 | ☐ |
| T-627 | KPITarget effective-dated, KPIMeasurement lịch sử, KPIEvaluation, KRMeasurement, `tenant_id` log, cột at-risk KR; migration `0017` + backfill; **service public cho Action Registry v2 (M1.5 undo):** `KpiTargetService.upsert`, `KpiService.delete_measurement`, `KpiService.delete_check_in` (soft delete + chấm lại KPIEvaluation/progress cùng transaction caller) | `execution/models`, `alembic/versions/0017_goals_measure_m14.py`, `kpi_service.py`, `kpi_target_service.py` (mới), `kpi_rules.py`, `okr_service.py` | R-DEC-51..53 | TC-M14-02, 07, 08, 09 | ☐ |
| T-627F | FE chi tiết KPI (SCR-58: đồ thị Recharts, target theo kỳ, ghi số đo) + chi tiết Objective (SCR-59: KR, confidence, lịch sử check-in) trên mock | `features/goals/{KpiDetailView,ObjectiveDetailView}.tsx`, `app/(app)/goals/{kpis,objectives}/[id]/page.tsx` | SCR-58, SCR-59 | TC-M14-17 | ☐ |
| T-628 | API EP-STR-01..22, EP-KPI-01..10, EP-OKR-01..11, EP-PRF-01..06 thay stub; `/goals/tree` một lượt query; nhãn EP trong AI tool registry | `execution/routes/*`, `execution/services/{goal_tree_service,strategy_service,initiative_service}.py`, `ai/tools/registry.py` | 10 §7.2.3 | TC-M14-03..06, 08, 09 | ☐ |
| T-628F | FE thẻ check-in F4 + feed team (SCR-60), placeholder "AI điền sẵn"; form tạo Strategy/SO/KPI/Objective/Initiative theo role | `features/goals/{CheckInCard,CheckInFeed,GoalForms}.tsx`, `app/(app)/goals/check-ins/page.tsx` | SCR-60, F4 | TC-M14-17 | ☐ |
| T-629 | Event `execution.kpi_measured`, `execution.kpi_below_threshold`, `execution.okr_checked_in`, `execution.okr_at_risk` (R-DEC-55/56) + consumer `execution.on_goal_alert` → Notification `alert`; beat at-risk hằng ngày + nhắc check-in thứ Sáu (`reminder`) | `core/events/registry.py`, `execution/events/consumers.py`, `execution/services/at_risk.py`, `worker.py` (beat) | 10 §9.2, R-DEC-59 | TC-M14-10, 11, 12 | ☐ |
| T-630 | Metric `METRIC-STR-01` (G2) + SEI refresh/drill-down; config `GOALS_*` | `execution/services/metrics.py`, `platform/services/catalog.py`, `platform/events/consumers.py`, `core/config.py`, `.env.example` | R-DEC-54, 03 §4 | TC-M14-13 | ☐ |
| T-631 | Seed: 1 Strategy "Tăng trưởng bền vững 2026–2027", 4 SO (C/F/U/O) gắn KPI gốc/Objective/INI-01..04; Project gắn Initiative; KPIEvaluation 3 kỳ; ~10 check-in + KRMeasurement 2 lần cho KR UC-04 (2,58 → 2,52, LOW); check-in KR của employee@; nâng confidence 2 KR "Runway ≥ 6 tháng" (OKR-CO) và "Ra mắt ABC Insight beta" (OKR-PRD) LOW → MEDIUM để chỉ KR UC-04 at-risk (08 §4.4 cần ≥ 1); xác minh UC-03/UC-04 + G2; sinh lại snapshot | `app/seed/{exec_data,execution_seed,snapshot}.py`, `tests/integration/test_seed_v3.py` | 08 §3/§4.3/§4.4 | TC-M14-16 | ☐ |
| T-632 | Quyền: `goal_scope.py` (DIR khối, MGR phòng ban + con, EMP của mình + tổ tiên restricted), check-in EMP chỉ của mình, chặn ghi Strategy/SO; mock FE cùng quy tắc. **Sửa file M1.2:** `StructureService.subtree_ids(root_ids)` public trong `hr` (bọc `DeptRepository.subtree_ids`), đăng ký vào registry mới `core/org_scope.py` (`register_subtree_provider`/`department_subtree`, mẫu `core/data_quality.py`) — `execution` chỉ đọc qua `core`, **không** import `hr` (tránh vòng `hr → execution` đã có) | `execution/services/goal_scope.py`, `core/org_scope.py` (mới), `hr/services/structure_service.py`, `hr/__init__` (đăng ký), `src/mocks/goals.ts`, `tests/architecture/test_import_boundaries.py` | R-DEC-57, 02 §5.3 | TC-M14-14, 15 | ☐ |
| T-633 | Nối FE ↔ BE thật + E2E `goals.spec.ts` (EMP check-in → MGR thấy; at-risk → chuông `alert`); `/code-review`; 14 §1.8 → Implemented; tick 09; STATE.md; đóng phase | `apps/web/e2e/goals.spec.ts`, `features/goals/*` | F4, UC-03, UC-04 | TC-M14-18 | ☐ |

**Thứ tự:** T-626S → T-626 → T-627 (2 migration nối tiếp `0015` của M1.3) → **T-626C** (schema + stub + shared-types) → song song **F** (T-626F → T-627F → T-628F, trên mock) ‖ **B** (T-628 → T-629 → T-630 → T-632 → T-631) → **N** T-633. File dùng chung (`registry.py`, `catalog.py`, `messages/*.json`, migration, `permission_matrix.py` — không đổi ở M1.4) do người điều phối gộp (09 §6.0bis).

**Exit:** G2 đo được (`METRIC-STR-01` có giá trị + lineage trên seed, ngưỡng 80%); dữ liệu UC-03 (`KPI-SAL-01` CRITICAL kỳ 2026-09, giảm 3 kỳ, có task/workload liên quan) và UC-04 (KR pipeline OKR-SAL at-risk, ≥ 21 ngày tới 31/12/2026) sẵn sàng; `/goals` + SCR-58..60 chạy với 4 role; path `/execution/{kpis,objectives,key-results,check-ins,initiatives}` đã gỡ, test chuyển path xanh; TC-M14-01..18 Implemented.

### 6.6. M1.5 — D03 Data Capture C1/C3/C5 + Action Registry v2 + lineage (nhánh `v3/m1.5-capture`)

**FE:** `/data` Hộp thư dữ liệu (mọi submission theo trạng thái); upload kéo thả (C3); **form C1** sinh động từ ExtractionSchema; **import Excel C5** (preview, map cột → trường, lỗi từng dòng, xác nhận); review song song (SCR-18a/b có sẵn); toast Undo 7 ngày; "Xem tài liệu gốc".

| T | Việc | File chính | Spec | TC | Trạng thái |
|---|---|---|---|---|---|
| T-634S | Spec lock M1.5 (bước S, gộp chuỗi M1.3–M1.6): 10 §7.2.4 (EP-DC-01..37, 12 ACT) + §9.2, 05 §2.7, 06 §3.4 (SCR-45, 18a, 18b, 61..63), 13 R-DEC-60..69, 14 §1.9, 09 §6.6 | docs | R-DEC-38 | — | ☐ |
| T-634 | Doc type P0 #2 `PLAN_KPI_OKR`, #3 `PERIOD_REPORT`, #4 `HR_ROSTER` (seed 0019; giữ `INVOICE`, `OTHER`); schema registry đọc DB thay hard-code (**sửa** `schema_registry.py`: hard-code chỉ còn làm seed); Admin CRUD schema/rule; classifier 4 tầng | `idp/services/schema_registry.py`, `classifier.py` (mới), `admin_service.py` (mới), `routes/data_capture.py`, `alembic/versions/0019_capture_seed_doctypes.py`, FE `app/(app)/admin/data-capture/**`, `features/capture/admin/**` | EP-DC-27..35, R-DEC-65, 05 §2.7 | TC-M15-01..03 | ☐ |
| T-635 | C1 form + submit; C5 upload/preview/mapping/rows/error-file/submit; Hộp thư + xem nguồn; giới hạn import cấu hình | `idp/services/manual_service.py`, `import_service.py`, `inbox_service.py` (mới), `upload_service.py` (sửa `document_type`), `core/config.py` (3 biến), FE `app/(app)/data/page.tsx`, `data/new/[documentType]`, `data/imports/[batchId]`, `features/capture/{DropZone,SchemaForm,ColumnMapper,ImportRowsTable,InboxView}.tsx` | EP-DC-01, 13..22, R-DEC-62 | TC-M15-04..06, 18 | ☐ |
| T-636 | Action Registry v2 (12 ACT) + `document_actions`; **sửa file M1.2:** service `hr` (`HrService.create_department/create_employee`, `StructureService.create_team/create_position`, `OrgService.assign`) nhận tham số `source` + `source_document_id` (mặc định giữ `MANUAL`); `commit_service` dispatch qua Registry (bỏ `_commit_invoice`); EP-DC-23; tách `idp/services/gateway.py` khỏi `ai` | `idp/services/actions/{registry,org,goals,work,finance}.py`, `commit_service.py`, `ai/services/action_registry.py` (re-export), `ai/services/action_service.py` (`_undo_from_refs` → Registry), `alembic/versions/0018_capture_registry.py` | bảng ACT 10 §7.2.4, R-DEC-60/61/63 | TC-M15-07, 08, 11 | ☐ |
| T-637 | Lineage ghi mọi commit + `GET /lineage/{entity}/{id}`; pipeline gán `document_page_id` theo trang/sheet; `LineageChip` FE | `platform/services/lineage_service.py` (mới), `platform/models` (sửa DataLineage), `idp/routes/lineage.py`, `idp/services/pipeline.py`, FE `components/ai/LineageChip.tsx` | EP-DC-26, R-DEC-64 | TC-M15-09 | ☐ |
| T-638 | Undo 7 ngày + EP-DC-25; event `idp.document_rolled_back`; `UndoToast` + dialog | `idp/services/undo_service.py` (mới), FE `features/capture/UndoDialog.tsx` | EP-DC-24/25, R-DEC-63/66/67 | TC-M15-10, 11 | ☐ |
| T-639 | `METRIC-DQ-02` (G3) + DQ per-domain + consumer | `platform/services/catalog.py`, `platform/services/capture_metrics.py` (mới), `core/capture_share.py` (mới, kiểu `register_dq`), `*/services/metrics.py` (đăng ký nguồn), `platform/services/metrics.py` (ghi `dq_domain_scores`) | R-DEC-68 | TC-M15-12 | ☐ |
| T-640 | Cứng hóa trường trọng yếu + incident G4 | `idp/services/critical.py` (mới), `incident_service.py` (mới), `review_service.py`, `commit_service.py` | EP-DC-36/37, R-DEC-69, FR-DC-16 | TC-M15-13 | ☐ |
| T-641 | File mẫu: sửa DOC-06 (thêm dòng lỗi cố ý + cột "Quản lý trực tiếp", "Mã phòng"), DOC-07 thêm `.docx`, mới DOC-08 `bao-cao-ket-qua-q3-2026.pdf`; xuất vào `data/` | `scripts/gen_demo_docs.py`, `data/DOC-0{6,7,8}*` | 08 §4.6, DEC-120 | TC-M15-15 | ☐ |
| T-642 | AI-eval anti-injection IDP (classify + map cột + extract) | `apps/api/tests/ai_eval/test_idp_injection.py` (mới), fixture `tests/fixtures/model_gateway/idp_*` | 14 §4.2 | TC-M15-14 | ☐ |
| T-643 | Nối FE↔BE, mock BFF, i18n, Vitest, E2E `capture.spec.ts`; cập nhật 14; đóng phase | `apps/web/src/mocks/capture.ts`, `mocks/router.ts`, `messages/{vi,en}.json`, `e2e/capture.spec.ts` | 09 §6.6 Exit | TC-M15-16, 17 | ☐ |

**Thứ tự** (theo 09 §6.0/§6.0bis): S (Spec lock chuỗi, T-634S) → C: T-636 (Registry + 0018) trước vì T-635/637/638 phụ thuộc → T-634 (0019 seed, cần schema JSONB mới) → song song **B**: T-635, T-637, T-640, T-639; **F**: SCR-45/61/62/63 trên mock (T-643 phần mock) song song B sau khi chốt schema Pydantic → T-638 (cần T-636 + T-637) → T-641, T-642 → N: nối real + E2E T-643 → R: full test + coverage. File dùng chung giữa agent song song (`routes/data_capture.py`, `mocks/router.ts`, `messages/*.json`, `core/config.py`) do coordinator gộp.

**Exit:** C1/C3/C5 end-to-end trên project `real` (TC-M15-17); Action Registry/undo/lineage/scope coverage ≥ 90% (TC-M15-07/09/10/13); pytest + Vitest + contract + Playwright mock/real xanh; `alembic downgrade -1 && upgrade head` sạch; không thêm mã lỗi/dependency/event mới; 14 §1.9 cập nhật Passed.

### 6.7. M1.6 — D26 AI Platform nền + UC-07 Onboarding + cổng M1 (nhánh `v3/m1.6-ai-onboarding`)

**FE:** `/admin/ai` SCR-64 (kill switch, agent, autonomy L0–L2, Tool Registry 13 metadata) + SCR-65 (`/admin/ai/logs` tool/model call + chi phí); `KillSwitchBanner` toàn app; `ActionCard`/`UndoToast` trong `/ask`; Wizard Onboarding UC-07 SCR-66 (thông tin DN → tải sơ đồ/DS nhân sự → review → tạo user + role → import KPI/OKR → xong, đồng hồ "trong 1 ngày").

| T | Việc | File chính | Spec | TC | Trạng thái |
|---|---|---|---|---|---|
| T-644S | Spec lock M1.6 (file này) gộp vào 10 §2.1/§2.2/§7/§7.2.5/§9.2, 05 §2.8, 06 §3.4, 13 R-DEC-70..79, 14 §1.10, 00 §4.8 + skeleton (53 TOOL, AGT-*, event) | docs | R-DEC-38 | — | ☐ |
| T-644 | Tool Registry đủ **13 metadata** (`spec.py` + `registry.py`), 4 loại (`COMPUTE`→READ+`compute`), kiểm lúc nạp, bảng ánh xạ BRD↔TOOL (`brd_name`); `ToolOut` mở rộng + EP-AI-14 lọc; migration `0020` phần `tool_kind` | `modules/ai/tools/*`, `schemas`, `routes/router.py`, `tests/unit/ai/test_tool_registry_m16.py` | 10 §2, R-DEC-70 | TC-M16-01, 02, 12 | ☐ |
| T-644F | SCR-64 khung tab + tab Tool Registry; route guard `/admin/ai*`; thẻ ở SCR-50; mock `/ai/tools`, `/ai/kill-switch`, `/ai/agents`, `/ai/autonomy-policies` | `app/(app)/admin/ai/**`, `features/admin/ai/**`, `mocks/ai_admin.ts`, `lib/permissions.ts`, `messages/*` | SCR-64 | TC-M16-16, 20 | ☐ |
| T-645 | 10 tool mới: 4 READ trong `ToolExecutor` (gọi service public `hr`/`work`/`goals` M1.2–M1.4), 6 WRITE map ACT M1.5 + **`ACT-update_task`, `ACT-assign_task` mới ở M1.6** (không thuộc 12 ACT M1.5; snapshot undo; `TOOL-assign_task` chuyển sang `ACT-assign_task`) | `tools/registry.py`, `services/tool_executor.py`, `idp/services/actions/work.py` (Registry v2 M1.5 — thêm `ACT-update_task`, `ACT-assign_task`), test | R-DEC-70 | TC-M16-03, 04 | ☐ |
| T-645b | Chat → `propose()` cho tool ghi (L1/L2), `suggested_actions` ở EP-AI-01/02, warning kill switch; fixture AI-eval "tạo task" | `services/chat_service.py`, `routes/router.py`, `core/model_gateway/fixtures/*`, `tests/ai_eval/` | R-DEC-78 | TC-M16-18 | ☐ |
| T-645F | `ActionCard` + `UndoToast` trong `/ask`; hàng chờ thẻ ở SCR-64 | `components/ai/{ActionCard,UndoToast}.tsx`, `features/ai/*` | 06 §5.1 | TC-M16-19 | ☐ |
| T-646 | `AIAgent`: migration `0020` (agent_profiles + autonomy_policies + tenant), seed 6 agent P0, EP-AI-16/17; `resolve_level` trần L2 + agent + policy theo tool/agent; EP-AI-18..21; kill switch validate agents + event `ai.policy_changed`; `AI_AUTONOMY_CEILING` trong `ConfigService` + `.env.example` | `models`, `alembic/versions/0020_ai_platform_m16.py`, `services/{autonomy,agent_service,policy_service,kill_switch_service}.py`, `seed/ai_seed.py`, `core/events/registry.py` | R-DEC-71..73, 77 | TC-M16-05..09, 17 | ☐ |
| T-646F | SCR-64 tab Tổng quan (kill switch, chi phí, hàng chờ), Agent, Autonomy; `KillSwitchBanner` trong `AppShell` | `features/admin/ai/**`, `components/shell/KillSwitchBanner.tsx` | SCR-64 | TC-M16-16, 20 | ☐ |
| T-647 | Audit mọi tool call: cột mới `tool_call_logs`/`model_call_logs`, ghi `request_id`/`tenant_id`/`user_id`/`ai_action_id`/scrub `arguments` ở mọi call site (chat, SSE, replay, propose); `CallRecord` + `request_id`/agent; EP-AI-22/23; EP-AI-15 `group_by=agent`, `period` | `services/chat_service.py`, `core/model_gateway/gateway.py`, `repositories`, `services/log_query_service.py`, test kiến trúc call site | R-DEC-74 | TC-M16-10..12 | ☐ |
| T-647F | SCR-65 logs (tool/model/chi phí), lọc `request_id`, drawer | `app/(app)/admin/ai/logs/**`, `features/admin/ai/logs/**` | SCR-65 | TC-M16-21 | ☐ |
| T-648 | Onboarding BE: `onboarding.state` qua `SystemSettingService` (optimistic `version`), EP-ADM-13/14, `progress` qua service public `hr`/`auth`/`goals`; ADM `idp:write` scope `s` (doc type #4, bỏ cột mức 4); event `platform.onboarding_completed` | `modules/platform/{routes,services/onboarding_service.py}`, `permission_matrix.py`, import C5 M1.5 (guard scope) | R-DEC-75/76/77 | TC-M16-13, 14, 17 | ☐ |
| T-648F | Wizard SCR-66 (6 bước, đồng hồ), orchestration FE gọi EP-ORG/EP-ADM/`/data-capture/imports`; mock | `app/(app)/admin/onboarding/**`, `features/admin/onboarding/**`, `mocks/onboarding.ts` | SCR-66 | TC-M16-15 | ☐ |
| T-649 | Rà seed sau M1 (agent, policy rỗng, `onboarding.state=completed` ABC, số liệu M1.2–M1.5 nhất quán 08); file mẫu UC-07 (`gen_demo_docs.py`); `seed_snapshot.json` cho mock; `demo_reset.sh -y` | `seed/**`, `scripts/gen_demo_docs.py`, `scripts/demo_reset.sh` | 08 §4.6, R-DEC-79 | TC-M16-22 | ☐ |
| T-650 | E2E **UC-07** project `real` + kill switch banner chéo phiên; `e2e/support/onboarding_e2e.py --cleanup` | `apps/web/e2e/real/onboarding.spec.ts`, `e2e/support/*` | UC-07 | TC-M16-23 | ☐ |
| T-651 | Review toàn M1 (`/code-review` diff M1.1→M1.6), coverage 14 §1.3, dọn nợ (TODO, path v2.1 còn sót, `assistant` hard-code) | toàn repo | 09 §6.0bis | TC-M16-24 | ☐ |
| T-652 | Đóng mốc M1: full test chuỗi (§6.0bis), 14 `Implemented → Passed`, STATE.md, PR chuỗi M1.3→M1.6; push `ai-eos` khi human đồng ý | STATE.md, 14 | — | TC-M16-24 | ☐ |

**Thứ tự:** T-644S → **C** (schema Pydantic `ToolOut`/`AIAgentOut`/`AutonomyPolicyOut`/`ToolCallLogOut`/`ModelCallLogOut`/`OnboardingStateOut` + stub `501` EP-AI-16..23, EP-ADM-13/14; sinh shared-types) → song song **F** (T-644F → T-646F → T-647F → T-645F → T-648F) ‖ **B** (T-644 → T-646 (migration `0020`) → T-647 → T-645 → T-645b → T-648) → T-649 → **N** T-650 → **R** T-651 → T-652.

**Exit M1:** UC-07 pass E2E `real` (TC-M16-23); Tool Registry 13 metadata + audit tool/model call theo `request_id` + Autonomy L0–L2 + kill switch dùng được trên SCR-64/65 + banner; gate A/B/C; full test chuỗi xanh (TC-M16-24).

### 6.8. M2.1 — D28 Health metrics v3 + Metric Store + 3 cấp dashboard (nhánh `v3/m2.1-home`)

**FE:** `/home` theo role (03 §1.1, 06 §5.1) — **Executive**: dòng tóm tắt 1 câu, 4 ô sức khỏe CEO tự chọn (mặc định doanh thu, runway, OKR công ty, task trễ), "Cần anh quyết", "Rủi ro", "AI đã làm", panel AI phải, Strategy Execution Index; **Department**: KPI/OKR đơn vị, heatmap workload, dự án trễ, task đến hạn; **Employee**: task, mục tiêu, check-in, lịch. Nhãn độ tươi; drill-down P01 → bản ghi → tài liệu gốc; mỗi widget một query.

| T | Việc | Trạng thái |
|---|---|---|
| T-701 | Catalog METRIC v3 (FIN/CUS/OPS/PPL/STR/DQ) đủ danh sách P0 skeleton §10 + bảng ánh xạ 32 METRIC v2.1 | ☐ |
| T-702 | Ngưỡng là cấu hình; freshness theo `SLA_FRESHNESS_*` | ☐ |
| T-703 | Provider metric mới (execution/okr/kpi/decision) | ☐ |
| T-704 | `GET /reporting/dashboards/{executive|department|employee}` theo scope; `Cache-Control: private, max-age=60` + `Vary: Authorization` | ☐ |
| T-705 | Cài đặt 4 ô của CEO (user preference) | ☐ |
| T-706 | Alert ngưỡng → Notification | ☐ |
| T-707 | Xác minh seed có ≥ 1 chỉ số ở ngưỡng cảnh báo (08 §5) | ☐ |
| T-708 | E2E `home-*.spec.ts` 3 cấp × role | ☐ |
| T-709 | Đóng phase | ☐ |

### 6.9. M2.2 — D15 Finance Lite · D17 Sales Lite · D16 HR cơ bản (nhánh `v3/m2.2-business`)

**FE:** `/business/finance` (ngân sách, chi phí, dòng tiền, runway — tái dùng `FinanceDrillView`), `/business/sales` (kanban pipeline, target, win rate), `/business/hr` (danh sách NV, phòng ban, mức 4 masked).

| T | Việc | Trạng thái |
|---|---|---|
| T-710 | Rà Finance/Sales/HR v2.1 theo phạm vi Lite; gán EP-FIN/SAL/HR ở 10 §7.2 | ☐ |
| T-711 | Doc type #6 BC tài chính/sao kê số dư → Revenue/Expense/CashBalance (ACT-record_*) | ☐ |
| T-712 | Lead/Opportunity ↔ Client/Deal hiện có (đổi tên hay alias — chốt ở bước S) | ☐ |
| T-713 | Event `opportunity.*` → metric | ☐ |
| T-714 | Seed bổ sung Lead/Opportunity + mẫu doc type #6; xác minh doanh thu ~300 tỷ/năm bằng script | ☐ |
| T-715 | E2E `business.spec.ts` | ☐ |
| T-716 | Đóng phase | ☐ |

### 6.10. M2.3 — C2 nói/NL · C4 chụp ảnh · D12 Meeting transcript → việc (nhánh `v3/m2.3-capture-meeting`)

**FE:** **PWA installable** (`app/manifest.ts` + service worker chỉ cache app shell, R-DEC-25); layout 390 px cho 4 việc cốt lõi; chụp ảnh (căn góc); **nói để nhập liệu ngắn** (`MediaRecorder`, giới hạn thời lượng, thông báo "xử lý bằng dịch vụ AI cloud"); gõ NL; `/meetings`: danh sách họp, dán/tải transcript văn bản hoặc ảnh biên bản (**không ghi âm họp**, R-DEC-22); AI tóm tắt → Decision + ActionItem dạng **ActionCard L2**, chủ trì duyệt → tạo task.

| T | Việc | Trạng thái |
|---|---|---|
| T-717 | C2 `POST /data-capture/natural-language` (text) + voice ngắn → STT qua ModelGateway `task=stt` (Internal → cloud, không lưu audio thô, PII filter trên văn bản, từ chối `context=meeting` → `BUSINESS_RULE_VIOLATION`); chọn `MODEL_STT` thật ở bước S | ☐ |
| T-718 | C4 qua EP upload `channel=C4` + tiền xử lý ảnh (khử nghiêng; nếu cần `pillow` ở runtime → raise DEC) | ☐ |
| T-719 | Doc type #1 Biên bản họp → Meeting/Decision/ActionItem | ☐ |
| T-720 | ENT-MeetingSummary, ActionItem (05) | ☐ |
| T-721 | Khớp tên → Employee (fuzzy + confidence; mơ hồ → review) | ☐ |
| T-722 | ACT-create_action_item / create_task_from_action_item — task chỉ tạo **sau khi chủ trì duyệt** | ☐ |
| T-723 | Event `meeting.summarized`, `action_item.created` | ☐ |
| T-724 | Lineage Task → ActionItem → trang transcript | ☐ |
| T-725 | AI-eval: nhận diện ≥ 90% action item trên transcript mẫu (08 §4.2) | ☐ |
| T-726 | E2E UC-02 + UC-06 | ☐ |
| T-727 | Đóng phase | ☐ |

### 6.11. M2.4 — D27 CEO Assistant có trích nguồn + Insight 9 phần (nhánh `v3/m2.4-assistant`)

**FE:** `/ask` + panel **⌘K** toàn app (SSE, `SourceChip`, `ThinkingState`); `InsightCard` 9 phần; "Tại sao?" mở chuỗi điều tra; check-in F4 có AI điền sẵn + thanh độ tự tin.

| T | Việc | Trạng thái |
|---|---|---|
| T-728 | Grounding validator cứng (10 §8): số không khớp `SourceRef` → gỡ + warning; thiếu dữ liệu → `AI_NO_DATA_AVAILABLE` | ☐ |
| T-729 | Tool READ phủ Finance/Sales/People/KPI/OKR/Projects/Risk-alert, lọc theo quyền người hỏi (P06) | ☐ |
| T-730 | Schema Insight 9 phần | ☐ |
| T-731 | Consumer `kpi.below_threshold` → root cause (task/workload) → Insight + khuyến nghị L2 (MGR duyệt tạo task gắn KPI) | ☐ |
| T-732 | AI điền sẵn check-in từ dữ liệu nguồn | ☐ |
| T-733 | Bộ AI-eval `tests/ai_eval/`: `GR-*` (0 số thiếu nguồn), `INJ-*`, routing classification | ☐ |
| T-734 | Fixture cho intent kịch bản CEO bước 1–4 | ☐ |
| T-735 | E2E UC-03 | ☐ |
| T-736 | Đóng phase | ☐ |

### 6.12. M2.5 — Cổng M2 (nhánh `v3/m2.5-gate`)

| T | Việc | Trạng thái |
|---|---|---|
| T-737 | E2E hồi quy UC-02/03/06/07 trên `real` | ☐ |
| T-738 | Hiệu năng: TTFT chat, dashboard theo 07 §6.2 | ☐ |
| T-739 | A11y WCAG AA (kiểm tay + snapshot; axe tự động cần DEC) | ☐ |
| T-740 | Demo reset, STATE, 14, review, PR; push khi được phép | ☐ |

### 6.13. M3.1 — D06 Integration Hub + D13 Calendar Google/Outlook 2 chiều (nhánh `v3/m3.1-calendar`)

**Mô hình (R-DEC-17):** OAuth **delegated theo từng user**; người chưa kết nối dùng lịch nội bộ + Notification "kết nối lịch để đồng bộ".
**Điều kiện human trước phase** (thiếu → BLOCKED): Google Cloud OAuth client (Calendar API) + Microsoft Entra app (Graph `Calendars.ReadWrite`, `offline_access`); redirect URI dev; secret trong `.env` (`GOOGLE_OAUTH_CLIENT_ID/SECRET`, `MS_OAUTH_CLIENT_ID/SECRET/TENANT`) — `.env.example` chỉ placeholder.
**FE:** `/meetings/calendar` (tuần/tháng, sự kiện nội bộ + đồng bộ); `/settings/integrations` (kết nối/ngắt, trạng thái, lần sync cuối, lỗi).

| T | Việc | Trạng thái |
|---|---|---|
| T-801 | ENT-CalendarEvent, CalendarAccount (token mã hóa qua `core/crypto_columns.py`), SyncState (syncToken/deltaLink), ExternalEventLink | ☐ |
| T-802 | `CalendarProvider` + `GoogleCalendarProvider` + `OutlookCalendarProvider` (`httpx`); OAuth code + PKCE, refresh, thu hồi | ☐ |
| T-803 | API `/integrations/{provider}/connect|callback|disconnect`; CRUD `/calendar/events` | ☐ |
| T-804 | Đồng bộ 2 chiều: kéo về beat 5 phút (incremental); đẩy ra qua outbox `calendar.event_changed`; webhook chỉ khi có URL public | ☐ |
| T-805 | Xung đột: last-writer-wins theo `updated`/`etag` + audit; idempotent qua ExternalEventLink | ☐ |
| T-806 | Retry/backoff 429 → DLQ; token hết hạn → Notification "kết nối lại" | ☐ |
| T-807 | Deadline task → sự kiện lịch của owner (bước 5 kịch bản CEO) | ☐ |
| T-808 | Test `respx` đủ nhánh 2 provider; `-m live` chỉ khi human cho phép | ☐ |
| T-809 | Classification lịch = Confidential, không gửi LLM cloud | ☐ |
| T-810 | E2E với provider fake (mock BFF) + 1 lần live thủ công có xác nhận | ☐ |
| T-811 | `/security-review` + đóng phase | ☐ |

### 6.14. M3.2 — Autonomy L3: khuyến nghị → phê duyệt → task + lịch + thông báo (nhánh `v3/m3.2-autonomy-l3`)

**FE:** `ActionCard` (L2 chờ xác nhận), feed **"AI đã làm"** (L3) + `UndoToast` 10 s (tạm dừng khi hover/focus), undo ≥ 24 h; nhãn "AI gợi ý" / "AI soạn" / "AI đã làm".

| T | Việc | Trạng thái |
|---|---|---|
| T-812 | ACT-execute_recommendation: một transaction tạo Task + owner + deadline + CalendarEvent + Notification; tool APPROVAL thì AI không tự gọi | ☐ |
| T-813 | Approval Matrix 02 (ngưỡng L3 là cấu hình, mặc định thận trọng — B5); kill switch hạ L3 → L2 | ☐ |
| T-814 | Undo 24 h đảo cả sự kiện lịch đã đẩy ra provider | ☐ |
| T-815 | Ghi `AIDecision` / `AIAudit` | ☐ |
| T-816 | AI-eval `AUT-*` (14 §4.3) | ☐ |
| T-817 | E2E bước 4–5 kịch bản CEO | ☐ |
| T-818 | Đóng phase | ☐ |

### 6.15. M3.3 — D27 Daily Briefing + D28 Decision Log 30/60/90 + báo cáo (nhánh `v3/m3.3-briefing`)

**FE:** Briefing 7 khối (03 §3.1), ≤ 1 trang, mọi số click được, trên `/home` của CEO + mobile; `/knowledge/decisions` (Decision Log, theo dõi 30/60/90); `/knowledge/reports` (báo cáo cơ bản + export).

| T | Việc | Trạng thái |
|---|---|---|
| T-819 | Job beat Briefing (theo `briefing_time`, idempotent theo (user, ngày)) từ Metric Store + Calendar + Decision + Approval + Insight; lưu ENT-Briefing (05) | ☐ |
| T-819b | Gửi Briefing qua email (T-616b): tóm tắt + link, không chứa dữ liệu mức 3–4 | ☐ |
| T-820 | Tracking mở Briefing (app + link email) → cổng **G1** | ☐ |
| T-821 | Decision Log: job theo `review_at` 30/60/90 → nhắc + verify outcome (`ai/services/verification.py`) | ☐ |
| T-822 | Report + export CSV/XLSX (`openpyxl`); PDF cần `reportlab` runtime → raise DEC hoặc hoãn | ☐ |
| T-823 | Nêu chỉ số stale (freshness) trong Briefing | ☐ |
| T-824 | AI-eval Briefing grounding | ☐ |
| T-825 | E2E UC-01 | ☐ |
| T-826 | Đóng phase | ☐ |

### 6.16. M3.4 — D26 Evaluation Engine + D14 Knowledge + Follow-up/Verify UC-04 (nhánh `v3/m3.4-eval-knowledge`)

**FE:** `/knowledge` thư viện tài liệu/SOP (doc type #5) + tìm kiếm; `/admin/ai/evaluation` bộ test chuẩn + điểm theo phiên bản prompt/model.

| T | Việc | Trạng thái |
|---|---|---|
| T-827 | ENT-AIEvaluation + runner bộ test chuẩn (fixture), chấm grounding/accuracy/tool-choice; `uv run python -m app.scripts.run_eval` | ☐ |
| T-828 | Knowledge: ingest doc type #5 → chunk theo trang → embedding bge-m3 qua gateway (DEC-142) → pgvector; tool `search_knowledge` có SourceRef tới trang; tắt khi `MODEL_EMBED` trống (không dùng LlamaIndex) | ☐ |
| T-829 | UC-04: `okr.at_risk` → phân tích blocker (dependency/workload) → đề xuất can thiệp → L3 (M3.2) → follow-up | ☐ |
| T-830 | ACT→VERIFY: theo dõi task, cập nhật Decision Log | ☐ |
| T-831 | E2E UC-04 | ☐ |
| T-832 | Coverage + review | ☐ |
| T-833 | Cập nhật 14 | ☐ |
| T-834 | Đóng phase | ☐ |

### 6.17. M3.5 — Nghiệm thu MVP (nhánh `v3/m3.5-acceptance`)

**Định nghĩa "đạt MVP" của đợt code (R-DEC-26):** kịch bản CEO 7 bước (§2.2) + UC-01/02/03/04/06/07 pass E2E trên stack thật (AI fixture); G1–G4 có instrumentation + trang đo. Ngưỡng G1–G4 thật xác nhận ở thí điểm (OQ-09-04), ngoài đợt code.

| T | Việc | Trạng thái |
|---|---|---|
| T-901 | E2E kịch bản CEO 7 bước trên `real` | ☐ |
| T-902 | Trang đo nội bộ G1–G4 | ☐ |
| T-903 | NFR: hiệu năng, bảo mật (RBAC/ABAC/tenant/PII), a11y AA, responsive 1440/1280/768/390, PWA | ☐ |
| T-904 | `docker-compose.full.yml` (+ Mailpit), `demo_reset.sh`, README + DEMO-SCRIPT v3 | ☐ |
| T-905 | `doc-reviewer` rà 00–14 so với code (OQ-12-01) | ☐ |
| T-906 | Checklist sẵn sàng thí điểm 1 DN 50–200 NV | ☐ |
| T-907..T-910 | Sửa lỗi nghiệm thu; PR `ai-eos → main` chờ human merge | ☐ |

### 6.18. Rủi ro đợt code

| Rủi ro | Giảm thiểu |
|---|---|
| Spec chưa chốt → phase BLOCKED | Bước S đầu phase (R-DEC-15), diff ngắn để human duyệt nhanh |
| Lọc tenant làm vỡ ~770 test | T-603 ở M1.1; fixture test set tenant mặc định; sửa theo lô |
| Seed v3 làm vỡ test assert số v2.1 | T-603b sau T-603; số liệu tính bằng script; liệt kê test đã đổi trong PR |
| Đổi route làm vỡ 9 spec E2E | Redirect 308 + sửa spec trong cùng T-607 |
| Mock lệch BE | Type sinh từ OpenAPI + drift check + bước N bắt buộc trên `real` |
| OAuth lịch cần credential + URL public | Điều kiện human trước M3.1; polling cho dev; `respx` |
| Thiếu dependency (PDF report, axe, xử lý ảnh runtime, STT local) | Raise DEC khi tới phase; có phương án hoãn |

## 7. Open questions

- OQ-09-01: Task breakdown `T-*` — **ĐÃ CHỐT** (R-DEC-15/19): sinh ở §6.
- OQ-09-02: Tái dùng code `main` (S0–S5d) làm nền M1–M3 — **ĐÃ CHỐT**: tái dùng + refactor trên nhánh `ai-eos` theo §6; merge về `main` ở T-907..T-910 (human merge).
- OQ-09-03: Ánh xạ mốc M1/M2/M3 → `TC-*` nghiệm thu G1–G4 — một phần: G1–G4 là instrumentation (R-DEC-26, T-630/T-639/T-640/T-820/T-902); `TC-*` chi tiết cấp ở 14 theo bước Spec lock từng phase.
- OQ-09-05: **ĐÃ CHỐT (R-DEC-27)**: trưởng Nhân sự = DIR `{O}`, trưởng Vận hành & Dịch vụ = MGR. Bối cảnh: 08 §2.1 đặt trưởng Nhân sự là ROLE-MGR và trưởng Vận hành & Dịch vụ là ROLE-DIR, nhưng M1.0 gắn khối `O` (hr) cho "HR-DIR" và quyền mức 4 (lương) cho CEO + DIR khối `O`. Nếu Vận hành-DIR mang `{O}` thì sẽ thấy lương. Cần chọn: (a) trưởng Nhân sự = DIR `{O}`, Vận hành-DIR không mang `O` (sửa 08), hay (b) giữ 08 và tách quyền mức 4 khỏi `scope_pillars` (thêm điều kiện phòng ban Nhân sự).
- OQ-09-04: Thí điểm 1 DN 50–200 NV (M3) cần chọn DN thật ngoài công ty giả định ABC — quyết định CEO, không blocking docs P0 (theo 13 §3 B2 "khách hàng mục tiêu đầu").
- OQ-09-06 (M1.3–M1.6): Sửa file thuộc M1.2 trong chuỗi (hr `StructureService.subtree_ids` public + `core/org_scope.py` ở T-632; tham số `source`/`source_document_id` cho service `hr` ở T-636) — **phương án đề xuất — chọn nếu human duyệt:** cho phép, mỗi chỗ ghi nhãn "sửa file M1.2" trong commit + test M1.2 chạy lại.
- OQ-09-07 (M1.6): `ACT-update_task`, `ACT-assign_task` thêm ở T-645 (không thuộc 12 ACT M1.5) — **phương án đề xuất — chọn nếu human duyệt:** có, đăng ký vào Registry v2 `idp/services/actions/work.py`.

## Version
- **Version:** 1.1.0 (current)
- **Last updated:** 2026-10-23
- **Maintainer:** @CyEyes
- **Change 1.4.0 (đề xuất — Spec lock M1.3–M1.6, chờ human duyệt):** §6.0bis quy trình chuỗi auto (R-DEC-38); §6.4–§6.7 thay bảng task bằng bảng mở rộng `T | Việc | File chính | Spec | TC | Trạng thái` (T-619S..T-625 M1.3, T-626S..T-633 M1.4, T-634S..T-643 M1.5, T-644S..T-652 M1.6) + dòng **Thứ tự** và **Exit** chi tiết; phụ thuộc liên phase chốt khi gộp (`projects.initiative_id` ở T-619, service public M1.4 cho undo ở T-627, subtree qua `core/org_scope.py` ở T-632, `ACT-update_task`/`ACT-assign_task` ở T-645). Open questions: thêm OQ-09-06/07.
- **Change 1.3.0 (đề xuất — Spec lock M1.2, chờ human duyệt bước S):** §6.3 mở rộng bảng task theo cột §6.2 (File chính | Spec | TC); thêm T-611S (bước S, ◐) và T-617F (FE trên mock); ghi rõ BusinessUnit hoãn, giữ `/hr/departments`, ghi cơ cấu `hr:admin`, reactivate, preferences email, thứ tự task; FE ghi SCR-51..54.
- **Change 1.2.0 (đề xuất — T-610c, R-DEC-28):** §6.2 thêm dòng T-610c (dropdown 10 tài khoản demo + autofill email/mật khẩu qua Route Handler `/api/demo-credentials` bật bằng `DEMO_MODE` + `DEMO_LOGIN_AUTOFILL`, nút con mắt); trạng thái ◐ chờ human test tay + full suite.
- **Change 1.1.0 (human duyệt 2026-10-23 — đợt code, R-DEC-15/19):** thêm §6 Task đợt code: quy trình S→C→F→B→N→R, bản đồ phase M1.0–M3.5, bảng T-601..T-910 theo phase (FE trên mock → BE → nối), rủi ro; Open questions chuyển thành §7, đóng OQ-09-01/02, cập nhật OQ-09-03, thêm OQ-09-05.
- **Change 1.0.0 (promote):** Promote tài liệu AI-EOS lên CHÍNH THỨC Aureon v3; di chuyển vào vị trí docs chuẩn; v2.1 archived (docs/_archive/v2.1/).
- **Change 0.3.0:** Mở rộng lên spec-level P0 — chiều **roadmap**: §1.1 lời hứa MVP làm tiêu chí ưu tiên; §2 bảng M1/M2/M3 nêu mục tiêu+domain kích hoạt+năng lực bàn giao+UC; §2.1 bảng phụ thuộc giữa domain + thứ tự kích hoạt; §2.2 cổng nghiệm thu MVP (4 cổng định lượng G1–G4 + kịch bản CEO 7 bước map domain/UC/Autonomy); §3 5 phase sau nêu domain + autonomy theo phase; §4 ma trận ưu tiên đầy đủ 28 domain D01–D28 + Data Foundation + tổng kết đếm; §5 thứ tự sinh tài liệu dạng cây. Thêm OQ-09-03/04. Giữ nguyên quyết định P0/P1/P2 của BRD; giữ ghi chú "T-* sinh ở đợt code" (R-DEC-09).
- **Change 0.2.0:** Chốt Q1–Q6 (R-DEC-05..10) — cập nhật trạng thái quyết định, đóng OQ liên quan; phạm vi docs-first P0.
- **Change 0.1.0:** Viết lại 09 theo AI-EOS — MVP 90 ngày (M1–M3) + cổng MVP, 5 phase sau, ma trận ưu tiên P0/P1/P2, thứ tự sinh tài liệu; T-* chờ Q1/Q5.
