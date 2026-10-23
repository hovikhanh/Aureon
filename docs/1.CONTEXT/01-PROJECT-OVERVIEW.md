# 01 — Project Overview (Aureon v3 — AI-EOS)

> **Nguồn chuẩn (Canonical):** `_reference/SOURCE-BRD-v1.1.md` (AI-EOS BRD v1.1) + `SOURCE-BRD-v1.1-Bổ sung.md` + `SOURCE-UIUX.md`. File này là tài liệu **đầy đủ theo AI-EOS**, tách từ Aureon v2.1 (nay archived ở `docs/_archive/v2.1/`).
> **Trạng thái:** ✅ current — Aureon v3 (AI-EOS) CHÍNH THỨC — Q1–Q6 **đã chốt** (R-DEC-05..10, 13 §1); phạm vi **docs-first P0** (R-DEC-09).
> **Phụ thuộc:** `TRACEABILITY-SKELETON.md` (ID registry). **Ngày:** 2026-10-22 · **Maintainer:** @CyEyes

---

## 1. Sản phẩm

**AI-EOS — AI-First Enterprise Operating System.** Không phải ERP/CRM/HRM/PM/BI/chatbot, mà là **hệ điều hành doanh nghiệp lấy AI làm trung tâm**, nối liền một vòng lặp:

```text
Capture → Data → Intelligence → Decision → Action → Measurement → Feedback
```

### 1.1. Tầm nhìn

> **One Enterprise. One Source of Truth. One AI Operating Layer.**

AI đóng vai Assistant, Analyst, Advisor, Planner, Orchestrator hoặc Agent tùy mức tự chủ (Autonomy L0–L4) doanh nghiệp cho phép.

### 1.2. Bốn câu hỏi hệ thống phải trả lời liên tục (BRD §1.2)

1. **Chúng ta muốn đạt gì?** — Strategy, KPI, OKR.
2. **Chúng ta đang làm gì để đạt nó?** — Initiative, Project, Task.
3. **Kết quả đang thế nào và tại sao?** — Measurement, Analytics, AI.
4. **Tiếp theo cần làm gì?** — Recommendation, Decision, Action, Follow-up.

### 1.3. Giá trị cốt lõi — 3 hệ thống hợp nhất (BRD §1.4)

- **System of Record** — sự thật về con người, tài chính, khách hàng, dự án, công việc, KPI/OKR, hợp đồng, cuộc họp, tài liệu gốc.
- **System of Intelligence** — phân tích, dự báo, phát hiện rủi ro, khuyến nghị.
- **System of Action** — task, workflow, phê duyệt, lịch, thông báo, API, agent.

Khác ERP: ERP dừng ở "dữ liệu → dashboard → người tự quyết"; AI-EOS đi tiếp "insight → khuyến nghị → quyết định → hành động → **xác minh kết quả**", và bắt đầu từ **tài liệu doanh nghiệp đang có** thay vì bắt nhập lại.

### 1.4. Vấn đề AI-EOS giải quyết (BRD §1.3)

Doanh nghiệp vận hành trên nhiều hệ thống rời rạc (kế toán, HRM, CRM, quản lý dự án, email, lịch, chat, bảng tính) + lượng lớn giấy tờ/PDF/Word/ảnh. P0 nhắm đúng 12 vấn đề gốc của CEO:

| # | Vấn đề | Tác động | Năng lực P0 trực tiếp xử lý |
|---|---|---|---|
| 1 | Dữ liệu phân tán, không có nguồn sự thật | Mỗi phòng báo một con số | D01/Data Foundation + Metric Store (một định nghĩa chỉ số) |
| 2 | Dữ liệu nằm trong tài liệu phi cấu trúc | Dữ liệu đến muộn, thiếu, sai | D03 Data Capture & IDP (C1–C5) |
| 3 | CEO phải tự tổng hợp thông tin | Mất nhiều giờ/tuần | D27 CEO Assistant + Daily Briefing |
| 4 | Phòng ban silo | Khó thấy phụ thuộc/xung đột nguồn lực | D11 Task/Workload, event backbone |
| 5 | Chiến lược không liên kết thực thi | Làm nhiều nhưng không đóng góp mục tiêu | D07/D08/D09 (Strategy→KPI/OKR→Initiative→Task) |
| 6 | KPI/OKR theo dõi thủ công trên Excel | Biết kết quả khi đã quá muộn | D08 KPI + D09 OKR + check-in (D10) |
| 7 | Cuộc họp không chuyển thành hành động | Quyết định không được thực thi | D12 Meeting Intelligence (transcript → ActionItem) |
| 8 | Task không phản ánh workload thực | Người giỏi quá tải | D11 Workload + chỉ số quá tải |
| 9 | Rủi ro phát hiện muộn | Xử lý khủng hoảng | Cảnh báo ngưỡng + insight AI (P1: D25 đầy đủ) |
| 10 | Báo cáo phụ thuộc con người | Chậm, dễ "làm đẹp" | D28 Reporting cơ bản + grounding |
| 11 | AI chỉ trả lời, không làm việc | AI không giảm khối lượng quản lý | Autonomy L0–L3 + Action/Tool Registry |
| 12 | Không có bối cảnh DN chung cho AI | AI trả lời chung chung | System of Record thống nhất + P03 Data First |

### 1.4. Lời hứa MVP

> **"CEO biết công ty đang đạt mục tiêu đến đâu, vì sao, và giao việc được ngay — với dữ liệu nhập vào dễ như gửi một file."**

---

## 2. Mục tiêu kinh doanh — BO-01…BO-10 (BRD §2.1)

| Mã | Mục tiêu | Chỉ số | Mục tiêu 6 tháng |
|---|---|---|---|
| BO-01 | Quản trị tập trung trên một nền tảng | % quy trình cốt lõi chạy trên AI-EOS | ≥ 80% |
| BO-02 | Minh bạch gần thời gian thực | Độ trễ dữ liệu chỉ số điều hành | ≤ 24h tài chính; ≤ 1h task/sales |
| BO-03 | Liên kết chiến lược ↔ thực thi | % task/dự án gắn KPI/OKR/initiative | ≥ 70% |
| BO-04 | Ra quyết định có AI | % quyết định quan trọng có phân tích AI + bằng chứng | ≥ 50% |
| BO-05 | Thực thi có AI | Số hành động AI xác minh thành công/tháng | Tăng hàng tháng |
| BO-06 | Giảm chi phí quản lý | Giờ/tuần CEO & quản lý cho tổng hợp/báo cáo/follow-up | Giảm ≥ 50% (CEO ≥ 5h/tuần) |
| BO-07 | Bộ nhớ doanh nghiệp | % quyết định/họp/tài liệu quan trọng truy vấn được | ≥ 90% |
| BO-08 | Thu thập dữ liệu không ma sát | Thời gian nhập liệu vs nhập tay | Giảm ≥ 70% |
| BO-09 | Dữ liệu đáng tin cho AI | Data Quality Score domain cốt lõi | ≥ 90/100 |
| BO-10 | Phát hiện rủi ro sớm | Thời gian từ dấu hiệu → hành động | Giảm ≥ 50% |

> Các con số mục tiêu 6 tháng là đề xuất ban đầu, cần xác nhận với baseline thực tế tại khách hàng thí điểm (BRD §2). Mỗi BO gắn một chỉ số đo được để nghiệm thu, không đo bằng "số lần dùng AI" (P11).

**North Star (BRD §20.1):** *Tỷ lệ quyết định & hành động quan trọng được AI hỗ trợ và có kết quả được xác minh.* Phễu: Insights → Recommendations → Accepted → Executed → Verified → Successful Outcomes (nguồn: Decision Log + AIRecommendation).

**Chỉ số hỗ trợ North Star (BRD §20.1, mục tiêu 6 tháng sau go-live):** WAU/tổng user ≥ 70% · CEO mở Briefing ≥ 4 ngày/tuần · % dữ liệu mới vào qua tài liệu/ngôn ngữ tự nhiên ≥ 60% · Data Quality Score ≥ 90/100 · % KPI/OKR cập nhật đúng kỳ ≥ 90% · % action item họp hoàn thành đúng hạn ≥ 75% · tỷ lệ khuyến nghị được chấp nhận ≥ 40% · tỷ lệ câu trả lời đánh giá đúng ≥ 90% · CEO tiết kiệm ≥ 5h/tuần · thời gian tín hiệu rủi ro → hành động giảm ≥ 50%.

---

## 3. Nguyên tắc sản phẩm — P01…P11 (BRD §2.2)

11 nguyên tắc ràng buộc kiến trúc và thiết kế mọi module; đây là tiêu chí thiết kế bắt buộc, không phải khuyến nghị.

| Mã | Nguyên tắc | Ý nghĩa bắt buộc (1 câu) |
|---|---|---|
| P01 | AI First | Mọi module thiết kế để AI đọc, truy vấn và hành động được (theo AI-R01–R12). |
| P02 | API First | Mọi năng lực nghiệp vụ expose qua API + tool; UI dùng chính các API đó. |
| P03 | Data First | Dữ liệu có cấu trúc, có owner, có nguồn gốc và điểm chất lượng. |
| P04 | Human in the Loop | Hành động tác động cao cần người phê duyệt theo Autonomy Level. |
| P05 | Everything Actionable | Mọi insight chuyển được thành khuyến nghị → quyết định → task. |
| P06 | Traceability | Truy được Strategy → Objective → KPI/OKR → Initiative → Project → Task → Người → Kết quả, và từ con số về tài liệu gốc. |
| P07 | Explainable AI | AI nêu dữ liệu, nguồn, lập luận, khuyến nghị, độ tin cậy và hành động. |
| P08 | Security by Design | AI không bao giờ vượt quyền người dùng và policy doanh nghiệp. |
| P09 | Capture Once, Use Everywhere | Một dữ liệu nhập một lần, dùng chung mọi domain; ưu tiên thu từ tài liệu/tích hợp sẵn. |
| P10 | Graceful Degradation | Khi AI lỗi hoặc bị tắt, mọi nghiệp vụ cốt lõi vẫn làm được thủ công. |
| P11 | Measure Outcomes | Đo giá trị bằng kết quả kinh doanh được xác minh, không bằng số lần dùng AI. |

### 3.1. 12 yêu cầu AI-first cho mọi module — AI-R01…AI-R12 (BRD §2.3)

Mọi module mới phải thỏa đủ 12 yêu cầu; đây là "hợp đồng AI-readiness" của mỗi domain:

| Mã | Yêu cầu (1 câu) |
|---|---|
| AI-R01 | AI đọc dữ liệu module trong phạm vi quyền của người được phục vụ. |
| AI-R02 | AI truy vấn qua tool đã đăng ký, **không** truy cập DB trực tiếp. |
| AI-R03 | AI tạo khuyến nghị theo cấu trúc chuẩn 9 phần (BRD §11.8). |
| AI-R04 | AI tạo task từ insight hoặc tài liệu. |
| AI-R05 | AI kích hoạt được workflow. |
| AI-R06 | AI thực hiện hành động nếu được phép theo Autonomy Level. |
| AI-R07 | Log toàn bộ tool call. |
| AI-R08 | Kiểm authorization trước mọi tool call. |
| AI-R09 | Cung cấp bằng chứng + trích dẫn cho mọi khuyến nghị và con số. |
| AI-R10 | Xác minh kết quả sau hành động (verify). |
| AI-R11 | Module có Extraction Schema để nhận dữ liệu từ tài liệu qua Data Capture. |
| AI-R12 | Module phát sự kiện nghiệp vụ để AI quan sát gần thời gian thực. |

> Chi tiết ánh xạ ID: `TRACEABILITY-SKELETON.md` §1–§2. Field-level enforcement (bảng/cột/constraint per-entity) chi tiết hóa ở đợt code (R-DEC-09).

---

## 4. Bản đồ 28 domain / 5 lớp (BRD §4)

Lớp **Nền tảng** và lớp **Governance & Trí tuệ** phục vụ mọi domain; **D03 Data Capture là cửa vào dữ liệu duy nhất** (P09). Cột "Ưu tiên" theo ma trận BRD §19.3 và tập P0 đã khóa (`TRACEABILITY-SKELETON.md` §12bis).

| Lớp | ID | Domain | Ưu tiên | Vai trò trong P0 |
|---|---|---|---|---|
| Nền tảng | D01 | Organization | **P0** | Cây tổ chức, Employee, Position — gốc của scope dữ liệu |
| Nền tảng | D02 | Administration & Security | **P0** | User/role/permission, RBAC+ABAC, audit, AI policy |
| Nền tảng | D03 | Data Capture & IDP | **P0** | Cửa vào dữ liệu duy nhất (C1–C5), pipeline trích xuất |
| Nền tảng | D04 | Workflow & Approval | **P0 cơ bản** / P1 | Approval cơ bản cho action AI (L2/L3); engine đầy đủ P1 |
| Nền tảng | D05 | Notification | **P0** | Thông báo alert, approval, action AI đã làm |
| Nền tảng | D06 | Integration Hub | **P0** (Google/MS) / P1 | Calendar + email nền tảng; connector khác P1 |
| Điều hành | D07 | Strategy Management | **P0 cơ bản** / P1 | Pillar/Objective/Initiative; scenario planning P1 |
| Điều hành | D08 | KPI Management | **P0** | KPI/Target/Measurement/Evaluation, cảnh báo ngưỡng |
| Điều hành | D09 | OKR Management | **P0** | Objective/KeyResult/check-in, cảnh báo at-risk |
| Điều hành | D10 | Performance Management | **P0 check-in** / P1 | Check-in P0; chu kỳ đánh giá đầy đủ P1 |
| Thực thi | D11 | Project / Task / Workload | **P0** | Giao việc, tiến độ, cân bằng workload |
| Thực thi | D12 | Meeting Intelligence | **P0 transcript** / P1 | Transcript → summary → ActionItem; AI dự họp P1 |
| Thực thi | D13 | Calendar | **P0** | Lịch 2 chiều Google/Outlook, đặt deadline/follow-up |
| Thực thi | D14 | Knowledge / Documents | **P0** | Lưu & truy vấn tài liệu, liên kết lineage |
| Vận hành KD | D15 | Finance | **P0 Lite** / P1 | Hóa đơn/chi phí/dòng tiền cơ bản; kế toán đầy đủ P1 |
| Vận hành KD | D16 | Human Resources | **P0 cơ bản** / P1 | Hồ sơ nhân sự cơ bản; vòng đời đầy đủ P1 |
| Vận hành KD | D17 | Sales / Business | **P0 Lite** / P1 | Pipeline Lite; CRM đầy đủ P1 |
| Vận hành KD | D18 | Customer | P1 | — (backlog) |
| Vận hành KD | D19 | Partner | P1 | — (backlog) |
| Vận hành KD | D20 | Procurement / Vendor | P1 | — (backlog) |
| Vận hành KD | D21 | Contract Lifecycle | P1 | — (backlog) |
| Vận hành KD | D22 | Product | P1 | — (backlog) |
| Vận hành KD | D23 | Technical / Engineering | P1 | — (backlog) |
| Governance & Trí tuệ | D24 | Governance & Compliance | P2 | — (backlog) |
| Governance & Trí tuệ | D25 | Risk Management | P1 | — (backlog; cảnh báo rủi ro cơ bản nằm ở chỉ số sức khỏe P0) |
| Governance & Trí tuệ | D26 | AI Platform | **P0** | Tool Registry, Autonomy, Policy/Approval/Audit/Eval Engine |
| Governance & Trí tuệ | D27 | CEO AI Assistant | **P0** | Hỏi đáp có nguồn, Daily Briefing, Management Loop |
| Governance & Trí tuệ | D28 | Reporting & Analytics | **P0 cơ bản** / P1 | Báo cáo cơ bản + Decision Log; analytics nâng cao P1 |

**Tổng P0:** 20 domain (12 đầy đủ/cơ bản + phần Lite); **P1 backlog:** D18–D23, D25, phần nâng cao của D04/D06/D07/D10/D12/D15/D16/D17; **P2 backlog:** D24. Ưu tiên chi tiết + FR prefix: `TRACEABILITY-SKELETON.md` §4 / §12bis.

### 4.1. Data Foundation (FR-DATA-01…08, BRD §13.1, P0)

Nền dữ liệu cắt ngang mọi domain, là điều kiện để AI tin cậy (BO-09): **MDM** (master data có owner) · **Data Quality Score** · **Data Freshness** (cảnh báo dữ liệu cũ) · **Data Lineage** (số → bản ghi → tài liệu gốc) · **Event backbone** (phát event cho AI quan sát) · **Metric Store / semantic layer** (định nghĩa chỉ số một lần) · **Lịch sử & effective-dated** · **Data export**. Chi tiết entity/field: 05 (R-DEC-09).

---

## 5. Vai trò (BRD §3.2)

7 vai trò chuẩn + **AI Agent là actor độc lập** (có Identity/Role/Permission/Scope/Tools/Policies/Budget/Audit); doanh nghiệp tạo thêm vai trò tùy biến:

ROLE-CEO · ROLE-DIR (Executive/Director) · ROLE-MGR · ROLE-EMP · ROLE-REV (Reviewer) · ROLE-ADM · **ROLE-AI**. RACI 7 quy trình cốt lõi ở BRD §3.3 (AI Agent không bao giờ là A). Chi tiết quyền/scope: 02.

---

## 6. Kiến trúc mục tiêu (BRD §18)

**Nguyên tắc nền:** AI **không** truy cập DB trực tiếp — mọi đọc/ghi/hành động đi qua **Tool Layer**, nơi lớp kiểm soát AI áp **quyền + Autonomy Level + phê duyệt + audit** (P08, AI-R02/R08). Về nghiệp vụ, hệ thống là 3 lớp hợp nhất nối bởi vòng lặp Outcome → Feedback → System of Record:

| Lớp nghiệp vụ | Thành phần | Ghi chú P0 |
|---|---|---|
| System of Record | Domain services + dữ liệu (D01, D03, D08/09, D11, D15–17, …) | Nguồn sự thật; mọi entity có `tenant_id` (R-DEC-07) |
| System of Intelligence | Orchestration AI, analytics, Metric Store, insight | D26 AI Platform + D28 Reporting cơ bản |
| System of Action | Tool, workflow, thông báo, lịch, agent | D04/D05/D13 + Action/Tool Registry |
| **Lớp kiểm soát AI** | Policy Engine, Approval Engine, Audit Engine | Cắt ngang mọi tool call (AI-R07/R08) |

**Quyết định kiến trúc (R-DEC-06):** **Modular Monolith** — AI Platform là cụm module logic bên trong, không tách microservice ở P0. Thiết kế kỹ thuật chi tiết (schema, deployment, NFR) thuộc tài liệu kiến trúc 07 và chi tiết hóa ở đợt code (R-DEC-09); BRD/01 chỉ chốt chiều sản phẩm.

---

## 7. Phạm vi MVP & lộ trình (BRD §19)

### 7.1. MVP 90 ngày — 3 mốc M1/M2/M3 (BRD §19.1)

Lời hứa MVP: *"CEO biết công ty đang đạt mục tiêu đến đâu, vì sao, và giao việc được ngay — với dữ liệu nhập vào dễ như gửi một file."* Ba mốc xây tuần tự theo vòng lặp Capture → Intelligence → Action:

| Mốc | Tên | Domain/năng lực chính | UC phủ |
|---|---|---|---|
| **M1 — Ngày 1–30: Nền móng** | System of Record | D01 Organization + Employee · D11 Project/Task · D08/D09 KPI/OKR cơ bản · D02 Admin & Security; nhập tay (C1) + import Excel (C5) + tải Word/PDF (C3) cho tài liệu tổ chức/nhân sự/KPI-OKR; D26 Tool Registry + audit + **Autonomy L0–L2** + kill switch | UC-07 |
| **M2 — Ngày 31–60: Trí tuệ** | System of Intelligence | D27 CEO Assistant hỏi đáp **có trích nguồn** · D15 Finance Lite · D17 Sales Pipeline Lite · D12 biên bản/transcript → task · C4 chụp ảnh mobile + C2 nhập bằng lời; **bộ chỉ số sức khỏe P0 + cảnh báo ngưỡng**; Metric Store | UC-02, UC-03, UC-04, UC-06 |
| **M3 — Ngày 61–90: Hành động** | System of Action | D27 **CEO Daily Briefing** · khuyến nghị → phê duyệt → tạo task (**Autonomy L3**, undo ≥24h) · D06/D13 Google/Outlook Calendar 2 chiều · D28 **Decision Log** · D26 Evaluation Engine (bộ test chuẩn); thí điểm 1 DN 50–200 NV | UC-01 |

**Cổng qua MVP (BRD §19.1):** CEO dùng Briefing ≥ 4 ngày/tuần trong 4 tuần liên tiếp; ≥ 80% KPI/OKR cập nhật đúng kỳ; ≥ 60% dữ liệu mới vào qua tài liệu hoặc ngôn ngữ tự nhiên; **không có sự cố AI ghi sai trường trọng yếu mà không bị phát hiện**.

### 7.2. 5 phase sau MVP (BRD §19.2)

| Phase | Tên | Nội dung chính |
|---|---|---|
| 1 | AI Executive & Work Core (MVP) | Như §7.1 (M1–M3) |
| 2 | Business Operations | Finance đầy đủ, CRM, Customer (D18), Partner (D19), HR nâng cao, Procurement (D20), Contract Lifecycle (D21), capture hóa đơn/hợp đồng/email (C6/C8), Workflow Engine nâng cao, KPI tự động từ tích hợp, AI tham gia Google Meet, Performance Cycle đầy đủ |
| 3 | Product & Technical | D22 Product, D23 Engineering, Git/CI-CD, Infrastructure, technical debt, product analytics |
| 4 | Governance & Strategy | D24 Governance & Compliance, D25 Risk Intelligence nâng cao, D07 Strategy nâng cao, scenario planning |
| 5 | Autonomous Enterprise | Assistant → Copilot → Agent → Multi-Agent → Enterprise Orchestrator; **mở L4** cho các tool đã chứng minh độ tin cậy. AI chủ động: Detect → Analyze → Recommend → Request Approval → Execute → Verify → Report |

### 7.3. Điều kiện thành công MVP — kịch bản CEO 7 bước (BRD §20.2)

1. **Ask:** "Tình hình công ty?"
2. **Understand:** AI tổng hợp Finance, Sales, People, KPI, OKR, Projects, Risks **có nguồn**.
3. **Investigate:** "Tại sao doanh thu thấp?" — AI tự gọi tool.
4. **Decide:** AI đề xuất các phương án.
5. **Act:** "Thực hiện phương án 1" — AI tạo task, owner, deadline, lịch, thông báo.
6. **Follow-up:** AI theo dõi thực thi.
7. **Verify:** AI đánh giá kết quả và cập nhật Decision Log.

### 7.4. Change management (BRD §20.3)

- CEO công bố AI-EOS là **nguồn sự thật duy nhất** cho KPI/OKR và task sau tối đa 4 tuần chạy song song với Excel.
- Mỗi phòng ban có một **AI champion**; đào tạo 2h cho nhân viên, 4h cho quản lý và reviewer.
- Giao ban hằng tuần dùng dashboard AI-EOS thay slide tự làm.
- Đo adoption theo phòng ban và can thiệp nơi thấp.

### 7.5. Giả định & phụ thuộc (BRD §20.5)

- Khách hàng dùng Google Workspace hoặc Microsoft 365 làm nền tảng email/lịch.
- Model AI thương mại đủ chất lượng tiếng Việt cho hội thoại + trích xuất; có phương án model chạy tại Việt Nam cho dữ liệu Mật.
- DN thí điểm cam kết cử AI champion + reviewer dữ liệu.
- Phần mềm kế toán của khách hàng cho phép xuất/tích hợp dữ liệu.

---

## 8. Use case nghiệm thu (BRD §14)

8 use case end-to-end dùng làm tiêu chí nghiệm thu; UC P0 phủ toàn bộ vòng lặp Capture → Decision → Action của MVP:

| ID | Tên | Giá trị cho CEO | Ưu tiên |
|---|---|---|---|
| UC-01 | CEO Morning Briefing | Mở app thấy ngay tình hình công ty + ngoại lệ cần quyết | **P0** (M3) |
| UC-02 | Meeting to Execution | Biên bản/transcript họp → ActionItem → task có owner/deadline | **P0** transcript (M2) / P1 AI dự họp |
| UC-03 | KPI Underperformance | Phát hiện KPI dưới ngưỡng → phân tích root cause → khuyến nghị | **P0** (M2) |
| UC-04 | OKR At Risk | Cảnh báo OKR có nguy cơ không đạt → đề xuất can thiệp | **P0** (M2) |
| UC-05 | CEO Strategic Question | Câu hỏi chiến lược mở, AI tổng hợp đa domain | P1 |
| UC-06 | Biên bản giấy → thực thi | Chụp ảnh biên bản giấy (C4) → trích xuất → task | **P0** (M2) |
| UC-07 | Onboarding doanh nghiệp 1 ngày | Import tổ chức/nhân sự/KPI từ tài liệu trong 1 ngày | **P0** (M1) |
| UC-08 | Hóa đơn → cảnh báo dòng tiền | Hóa đơn (C3/C4) → Finance → cảnh báo runway | P1 |

**MVP (P0):** UC-01, UC-02 (transcript), UC-03, UC-04, UC-06, UC-07. Tiêu chí chấp nhận chi tiết + flow/trạng thái/ngoại lệ mỗi UC đặc tả ở 04 (IDP), 03 (dashboard/metric) và 06 (UI flow); 01 chốt phạm vi + giá trị. Ví dụ output UC-05 và audit trail mẫu: BRD §14.1–14.2.

---

## 9. Bộ chỉ số sức khỏe doanh nghiệp P0 (BRD §12.4)

Bộ chỉ số điều hành chuẩn, nhóm theo 6 trụ dữ liệu; P0 chốt **danh sách chỉ số + ngưỡng cảnh báo gợi ý**, mã `METRIC-*` và công thức cấp ở 03 (R-DEC-10). Ngưỡng là cấu hình được (Metric Store):

| Nhóm | Chỉ số P0 (ngưỡng cảnh báo gợi ý) |
|---|---|
| Tài chính | Tăng trưởng DT & % kế hoạch · Cash runway (< 6 tháng) · Chênh lệch ngân sách (> 10%) |
| Khách hàng | Pipeline coverage (< 3×) · Win rate & chu kỳ bán hàng |
| Vận hành | Hoàn thành đúng hạn (< 80%) · Dự án trễ (> 20%) · Thực thi quyết định (< 70%) |
| Con người | Quá tải (> 10% nhân sự) |
| Chiến lược | Strategy Execution Index (< 70%) |
| Dữ liệu | Data Quality Score (< 80/100) |

**P1 (backlog):** biên lợi nhuận, DSO/DPO, công nợ quá hạn, NRR/churn, tập trung DT, CAC/LTV/NPS, nghỉ việc, DT/nhân sự.

---

## 10. AI Platform & Autonomy — khung P0 (BRD §11)

- **Autonomy Levels (BRD §11.6):** L0 Inform · L1 Suggest · L2 Draft & Confirm · L3 Act & Notify (**undo ≥ 24h**). **L4 Autonomous khóa ở MVP** (mở ở phase 5). Kill switch bật → hạ L3 về L2.
- **Phân loại tool (BRD §11.3):** READ · WRITE · APPROVAL (AI **không** tự gọi) · EXECUTION.
- **Insight 9 phần (BRD §11.8):** Observation → Evidence → Impact → Root Cause → Risk → Recommendation → Expected Outcome → Confidence → Action.
- **AI Operating Loop (BRD §17.5):** OBSERVE → UNDERSTAND → REASON → RECOMMEND → APPROVE → ACT → VERIFY → LEARN.
- **Agent P0:** CEO, Data Capture, Performance, Task, Meeting, Reporting (+ Finance/Sales Lite). Tool metadata 13 thuộc tính, 13 thành phần AI Platform: `TRACEABILITY-SKELETON.md` §9. Contract chi tiết (tool/EP/AIC) ở 07/10 (R-DEC-09).

---

## 11. Quyết định nền (Q1–Q6 đã chốt) + quyết định mở CEO (BRD §21.1)

> ✅ Q1–Q6 **đã chốt** (R-DEC-05..10, 13 §1). Các mục dưới ghi quyết định chính thức; BRD-OQ (B1–B7) còn chờ CEO nhưng không blocking docs P0.

| # | Quyết định | Đã chốt |
|---|---|---|
| Q1 | Toàn bộ 28 domain vs tập P0 MVP | **R-DEC-05:** P0 MVP trước; khung 28 domain giữ đủ ở 00; P1/P2 là backlog (09) |
| Q2 | Kiến trúc | **R-DEC-06:** Modular Monolith; AI Platform là cụm module logic bên trong |
| Q3 | Tenant | **R-DEC-07:** 1 tenant cho MVP; data model có `tenant_id` sẵn ở mọi entity |
| Q4 | Role | **R-DEC-08:** 7 role BRD + AI Agent; Director có data scope thay 5 C-level; giữ bảng ánh xạ 10 role F.O.C.U.S của `main` |
| Q5 | Phạm vi nhánh | **R-DEC-09:** Docs-first — hoàn thiện 00–14 đợt này; code/app/migration/merge main là đợt sau |
| Q6 | ID scheme | **R-DEC-10:** Theo BRD + bảng ánh xạ sang METRIC-/EP-/ENT-/SCR-/TOOL- của `main` |
| BRD-OQ | SaaS đa tenant / AI cloud / ngưỡng L3 / phần mềm kế toán / kênh chat / giá | Chờ CEO (B1–B7, BRD §21.1) — không blocking docs P0 |

---

## 12. Rủi ro dự án & giảm thiểu (BRD §20.4)

7 rủi ro dự án trọng yếu + biện pháp giảm thiểu đã thiết kế vào P0:

| # | Rủi ro | Tác động | Giảm thiểu (P0) |
|---|---|---|---|
| 1 | Dữ liệu đầu vào thiếu hoặc bẩn | AI kết luận sai, mất niềm tin | Data Capture P0 (D03), Data Quality Score (BO-09), cảnh báo dữ liệu cũ (Data Freshness) |
| 2 | AI bịa số (hallucination) | Quyết định sai | Grounding bắt buộc (P07/AI-R09), trích dẫn nguồn, Evaluation Engine (M3) |
| 3 | Trích xuất sai trường tài chính | Sai số liệu, rủi ro gian lận | Trường trọng yếu **luôn qua người** (P04), kiểm tra chéo, phát hiện trùng (D03) |
| 4 | Người dùng không áp dụng | Hệ thống rỗng | Change management (§7.4), nhập liệu không ma sát (BO-08), CEO làm gương |
| 5 | Chi phí AI vượt dự toán | Biên lợi nhuận âm | Model routing, ngân sách trần (AIBudget), theo dõi chi phí/tài liệu |
| 6 | Vi phạm dữ liệu cá nhân | Phạt, uy tín | Phân loại dữ liệu, consent, xử lý tại VN cho dữ liệu Mật (NĐ 13/2023) |
| 7 | Phạm vi phình to | Trễ MVP | MVP 90 ngày + cổng nghiệm thu rõ (§7.1); yêu cầu mới qua đánh giá ưu tiên (R-DEC-05) |

> Rủi ro bổ sung (BRD §20.4): tích hợp hệ thống cũ khó → ưu tiên import + tài liệu trước, connector sau (nhất quán với phân kỳ C1–C5 P0, C6–C10 P1).

---

## Open questions

- **OQ-01:** BRD-OQ B1–B7 (BRD §21.1) chờ CEO chốt — không blocking docs P0 nhưng ảnh hưởng P1+: mô hình sản phẩm (SaaS đa tenant vs nội bộ), khách hàng mục tiêu đầu, chính sách AI cloud cho dữ liệu tài chính/nhân sự, vai trò với phần mềm kế toán, **ngưỡng giá trị tối đa AI được tự thực hiện ở L3** (cần trước khi bật L3 thật ở M3/đợt code), kênh chat chính (Zalo/Slack/Teams), mô hình giá. Theo dõi ở 13-DECISION-LOG §3.
- **OQ-02:** Mã `METRIC-*` cụ thể + công thức cho bộ chỉ số sức khỏe P0 (§9) sẽ cấp ở 03; 01 mới chốt danh sách chỉ số nguồn + ngưỡng gợi ý từ BRD §12.4.
- **OQ-03:** Mã `AIC-*` (13 thành phần AI Platform) và `AGT-*` (agent) là đề xuất trong skeleton §9; chốt chính thức ở 07 — nếu cần thêm, cập nhật `TRACEABILITY-SKELETON.md` trước.

## Version
- **Version:** 1.0.0 (current)
- **Last updated:** 2026-10-23
- **Maintainer:** @CyEyes
- **Change 1.0.0 (promote):** Promote tài liệu AI-EOS lên CHÍNH THỨC Aureon v3; di chuyển vào vị trí docs chuẩn; v2.1 archived (docs/_archive/v2.1/).
- **Change 0.3.0:** Mở rộng lên **spec-level P0 đầy đủ** (giữ 🟡 draft, bám canonical BRD §0–§2/§4/§18/§19/§20): §1.4 bảng 12 vấn đề ↔ năng lực P0; §2 ghi chú chỉ số BO + chỉ số hỗ trợ North Star; §3 bảng P01–P11 (ý nghĩa 1 câu) + §3.1 bảng AI-R01–R12; §4 bảng 28 domain đủ cột lớp+ưu tiên+vai trò P0 + §4.1 Data Foundation FR-DATA; §6 kiến trúc mục tiêu 3 lớp + lớp kiểm soát AI (R-DEC-06); §7 lộ trình 3 mốc M1/M2/M3 (domain+năng lực+UC) + bảng 5 phase + kịch bản CEO + change mgmt + giả định; §8 bảng UC-01..08 (giá trị+ưu tiên+mốc); §9 bộ chỉ số sức khỏe P0; §10 khung AI Platform/Autonomy P0; §12 bảng 7 rủi ro dự án + giảm thiểu; thêm **## Open questions** (OQ-01..03). Giữ nguyên ngữ nghĩa Q1–Q6/R-DEC, không promote current.
- **Change 0.2.0:** Chốt Q1–Q6 (R-DEC-05..10) — cập nhật trạng thái quyết định, đóng OQ liên quan; phạm vi docs-first P0.
- **Change 0.1.0:** Viết lại 01 theo AI-EOS đầy đủ — tầm nhìn/4 câu hỏi/3 hệ thống, BO-01..10 + North Star, P01..P11 + AI-R, bản đồ 28 domain/5 lớp, 7 role + AI Agent, MVP 90 ngày + 5 phase, kịch bản CEO 7 bước, UC-01..08, quyết định mở + mặc định tạm Q1–Q6.
