# 09 — Build Plan & Tasks (AI-EOS, nhánh `ai-eos`)

> **Nguồn chuẩn:** `_reference/SOURCE-BRD-v1.1.md` §19 (MVP 90 ngày + 5 phase + ma trận ưu tiên) và §20.2 (kịch bản CEO — điều kiện thành công MVP). Bổ sung: `SOURCE-BRD-v1.1-Bổ sung.md`, `SOURCE-UIUX.md`.
> **Phụ thuộc:** toàn bộ 00–08, 10, 11. **Trạng thái:** 🟡 draft (Phase R3) — sinh cuối theo CLAUDE.md §10.1 Phase 4. **Ngày:** 2026-10-22 · **Maintainer:** @CyEyes
> **Phạm vi file:** đây là **product roadmap P0** (chiều lộ trình — mục tiêu/domain/năng lực mỗi mốc, cổng nghiệm thu, phụ thuộc, thứ tự sinh tài liệu). Task kỹ thuật `T-*` **không** sinh ở file này — chúng được sinh ở **đợt code** (R-DEC-09), sau khi docs 00–14 được human promote `current`.

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

## 6. Open questions

- OQ-09-01: Task breakdown `T-*` chi tiết — được sinh ở **đợt code** (R-DEC-09); doc 09 giữ vai trò product roadmap P0/P1/P2 (R-DEC-05). Giữ nguyên.
- OQ-09-02: Tái dùng code `main` (S0–S5d) làm nền M1–M3 — quyết định cụ thể ở đợt code (R-DEC-09), gồm cả merge main. Giữ nguyên.
- OQ-09-03: Ánh xạ chi tiết mỗi mốc M1/M2/M3 → tập `TC-*` nghiệm thu cổng G1–G4 — hoãn tới 14 + đợt code (R-DEC-09); hiện chỉ mô tả cổng ở §2.2.
- OQ-09-04: Thí điểm 1 DN 50–200 NV (M3) cần chọn DN thật ngoài công ty giả định ABC — quyết định CEO, không blocking docs P0 (theo 13 §3 B2 "khách hàng mục tiêu đầu").

## Version
- **Version:** 0.3.0 (draft, Phase R3)
- **Last updated:** 2026-10-22
- **Maintainer:** @CyEyes
- **Change 0.3.0:** Mở rộng lên spec-level P0 — chiều **roadmap**: §1.1 lời hứa MVP làm tiêu chí ưu tiên; §2 bảng M1/M2/M3 nêu mục tiêu+domain kích hoạt+năng lực bàn giao+UC; §2.1 bảng phụ thuộc giữa domain + thứ tự kích hoạt; §2.2 cổng nghiệm thu MVP (4 cổng định lượng G1–G4 + kịch bản CEO 7 bước map domain/UC/Autonomy); §3 5 phase sau nêu domain + autonomy theo phase; §4 ma trận ưu tiên đầy đủ 28 domain D01–D28 + Data Foundation + tổng kết đếm; §5 thứ tự sinh tài liệu dạng cây. Thêm OQ-09-03/04. Giữ nguyên quyết định P0/P1/P2 của BRD; giữ ghi chú "T-* sinh ở đợt code" (R-DEC-09); giữ status 🟡 draft.
- **Change 0.2.0:** Chốt Q1–Q6 (R-DEC-05..10) — cập nhật trạng thái quyết định, đóng OQ liên quan; phạm vi docs-first P0.
- **Change 0.1.0:** Viết lại 09 theo AI-EOS — MVP 90 ngày (M1–M3) + cổng MVP, 5 phase sau, ma trận ưu tiên P0/P1/P2, thứ tự sinh tài liệu; T-* chờ Q1/Q5.
