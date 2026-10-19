# GAP-ANALYSIS v2.1 — `_reference/` (Canonical, DEC-144) ↔ `docs/` v2.0.0

> **Loại:** `reference` (không thuộc chuỗi 00–14; không phải spec build, không dùng cho Gate A).
> **Ngày:** 2026-10-19 · **Maintainer:** @CyEyes · **Nguồn:** `_reference/SOURCE-BRD-v1.1.md` (sửa 2026-10-19 22:28, sha256 `7be8eb87…`) và `_reference/SOURCE-BRD-v1.1-Bổ sung.md` (`7affd07c…`, giống `SOURCE-BRD.md` commit `56f5ca5`).
> **Ký hiệu:** MT = MÂU THUẪN · THÊM · LT = LỖI THỜI · KHỚP. Cột "Xử lý" ghi gói quyết định G1–G7 (§E) hoặc "tự sửa". Quyết định của human ở §G; DEC tương ứng DEC-146..152 trong `13-DECISION-LOG.md`.

## 0. Inventory `_reference/`

| File | Sửa lần cuối | Kích thước | sha256 (16) | Tình trạng |
|---|---|---|---|---|
| `README.md` | 2026-10-16 22:17 | 1.421 B | `b01e37fc84e47e58` | Không đổi (vẫn ghi "AI không được đọc" — trái DEC-144; file của human, gitignored) |
| `SOURCE-BRD-v1.0.md` | 2026-10-06 08:51 | 58.516 B | `de1d52f88ab1b90c` | Không đổi |
| `SOURCE-BRD-v1.1-Bổ sung.md` | 2026-10-16 22:26 | 34.849 B | `7affd07ccd4f0fd1` | Tên mới; nội dung = `SOURCE-BRD.md` đã dùng viết v2 |
| `SOURCE-BRD-v1.1.md` | **2026-10-19 22:28** | 102.581 B | `7be8eb870949fb05` | **Nội dung mới** — BRD đầy đủ 28 domain, 1.264 dòng |
| `SOURCE-UIUX.md` | 2026-10-16 22:15 | 30.728 B | `cf7efbe1749a9e0c` | Không đổi |

Không có bản cũ của `SOURCE-BRD-v1.1.md` để diff (`_reference/` bị gitignore) → đối chiếu toàn văn.

## A. Phạm vi, nguyên tắc, vai trò, MVP (BRD §0–§5, §19–§21)

| # | File · mục | Loại | BRD (dòng) → docs | Xử lý | Mức |
|---|---|---|---|---|---|
| A-01 | 00 §4, 01 §6 | MT | P01–P11 (L112–124) khác nghĩa P01–P09 docs (01:132–140) | DEC G2 | lớn |
| A-02 | 00, 01, 04 header | LT | Data Capture = **D03**, D22 = Product (L198, L586) — docs ghi "Domain 22" | tự sửa | TB |
| A-03 | 01, 02, 03, 04 | LT | Trích số mục BRD cũ (01:24, 02:4, 04:4) | tự sửa | nhỏ |
| A-04 | 00 §7, §8 | LT | 00:216–218 còn "Không load `_reference/`" — trái DEC-144/145 | tự sửa | TB |
| A-05 | 01 §3, 02 §10, 07 | MT | MFA bắt buộc Admin/Tài chính (L234, P0) — docs OUT, chưa có DEC | DEC G1 | TB |
| A-06 | 01 §3, 03, 05 | MT | D04 Workflow & Approval **P0 cơ bản** (L244–251) — docs OUT | DEC G1 | lớn |
| A-07 | 01 §3, 09 | MT | Calendar Google/Outlook 2 chiều P0, MVP (L260, L1132) — docs không có | DEC G1 | lớn |
| A-08 | 05 hr, 03, 06, 09 | THÊM | D01 Organization P0: BU/Team/Position, ma trận, kiêm nhiệm, effective-dated, sơ đồ tổ chức (L208–227) | DEC G1/G3 | lớn |
| A-09 | 03 FR-NTF, 05 | THÊM | D05 mức ưu tiên, gộp + tóm tắt, kênh + giờ yên lặng (L253–258) | DEC G5 | TB |
| A-10 | 01 §3, 09 | THÊM | Knowledge P0, BO-07 (L1161, L105) — 09 không có task RAG | DEC G1 | TB |
| A-11 | 03, 05 | THÊM | AI-R10 / P11 verify outcome (L141, L1202) | DEC G5 | TB |
| A-12 | 01 §4 | THÊM | BO-01..10, North Star, cổng qua MVP (L97–108, L1176–1193) | tự sửa | TB |
| A-13 | 01 §10, 09 | MT | Thứ tự MVP 90 ngày (IDP + Tool Registry ngày 1–30) khác S0–S5 | DEC G1 (ghi rationale) | TB |
| A-14 | 00 §3 | THÊM | UC-01..03 thuộc MVP — docs chỉ có UC-06/07/08 | DEC G2 | TB |
| A-15 | 02 §6.3, 05 | MT | 4 mức Công khai/Nội bộ/Mật/Tuyệt mật quyết định model (L235) ≠ 4 mức docs | DEC G5 | TB |
| A-16 | 02 §1, §7 | MT | Role tùy biến; AI Agent có identity, quyền = agent ∩ người; kill switch theo agent (L147, L178, L237) — docs 10 role cố định (DEC-128) | DEC G5 | TB |
| A-17 | 02 OQ-05 | MT | FR-ADM-08 "Xem như người dùng" P0 (L238) | DEC G5 | nhỏ |
| A-18 | 13 | THÊM | §21.1 7 quyết định mở; chưa chốt: AI cloud (02 OQ-06), ngưỡng L3 mặc định | DEC G5 | TB |
| A-19 | 01 §3 | MT | Public API/webhook P1; tenant isolation P0 (L236) | gộp G1 (1 tenant) | nhỏ |
| A-20 | 01 §12 | THÊM | Thuật ngữ, tagline, vòng lặp, 4 câu hỏi (L45–60, L1246–1264) | tự sửa | nhỏ |
| A-21 | 01 | THÊM | Rủi ro sản phẩm, giả định, change management (L1205–1230) | tự sửa | nhỏ |
| A-22..24 | 01, 02, 09 | KHỚP | Nội dung MVP tổng; mục chủ ý OUT (Performance cycle, Meet bot, Procurement, L4, kế toán); stakeholder/role theo DEC-128 (RACI có thể thêm vào 02 — tự sửa) | — | — |

## B. Data Capture & IDP (BRD §6, BS toàn bộ)

| # | File · mục | Loại | BRD (dòng) → docs | Xử lý | Mức |
|---|---|---|---|---|---|
| B-01 | 04 §6, 09, 14, DEC-123/138 | MT | FR-DC-01..23 cùng mã khác nghĩa (BRD L315–343 vs 04:397–419) | DEC G2 | lớn |
| B-02 | 04 C2, DEC-050 | MT | Voice C2 **P0** (L276) — docs P1, DEC-050 open | DEC G1 | TB |
| B-03 | 04 FR-DC-08 | MT | Chọn trước loại → bỏ qua phân loại (L326) — docs vẫn phân loại | DEC G6 | nhỏ |
| B-04 | 04 §1.2/§4, 10 | MT | SOP/chính sách → Knowledge P0 (L302) — docs Phase 2 | DEC G1 | TB |
| B-05 | 04 §8, 05, 10 | THÊM | Trạng thái `SUPERSEDED` (L350) | DEC G6 | TB |
| B-06 | 10 EP-29..37, 05 | THÊM | Chuyển người duyệt; gộp khi review (L342) | DEC G6 | TB |
| B-07 | 04, EP-28 | THÊM | Nhắc việc + escalation quá SLA (L341) | DEC G6 | TB |
| B-08 | 04, 06 | THÊM | Sửa hàng loạt dạng lưới (L318) | DEC G6 | TB |
| B-09 | EP-30 | THÊM | Lý do bắt buộc khi sửa trường tài chính (L319) | DEC G6 | TB |
| B-10 | 05 enum, 04 §7.3 | THÊM | Checkbox, chữ ký/con dấu; viết tay luôn Review (L328) | DEC G6 | TB |
| B-11 | 04 §5.2 | THÊM | Chuẩn hóa địa chỉ (L330) | tự sửa (ghi OUT) | nhỏ |
| B-12 | 10 §7, 04 §10 | MT | 10 tool IDP, `commit_extraction` kế thừa risk_level (L379) vs 3 TOOL + ACT | DEC G5 | TB |
| B-13 | 04 §1 | THÊM | Data Capture Agent (L382) — hành vi tương đương | tự sửa | nhỏ |
| B-14 | 04 §7.4 | THÊM | Học theo NCC/mẫu (L355) | DEC G6 / OUT | TB |
| B-15 | 04 §17, EP-39 | THÊM | Chi phí / tài liệu (L366) | tự sửa 04; EP-39 → DEC G6 | nhỏ |
| B-16 | 02 §6.3 | THÊM | Dữ liệu sức khỏe là PII (L372) | DEC G5 | nhỏ |
| B-17 | 07, 13 | THÊM | Dependency parse PDF/HEIC/DOC/XLS cũ chưa có DEC | DEC G6 (T-002) | TB |
| B-18 | DEC-123 ↔ 04/10 | MT nội bộ | DEC-123: 1 file/req, hoãn deskew vs EP-20 `files[]`, deskew server | DEC G6 | TB |
| B-19 | 06 ↔ 04 | MT nội bộ | Phím tắt, preview 50 vs 20 dòng, nơi lưu correction | tự sửa (theo 10) | nhỏ |
| B-20 | 06 SCR-10 | THÊM | Nút "Chấp nhận tất cả HIGH" (API EP-31 đủ) | tự sửa | nhỏ |
| B-23 | 01/04 | LT | "Capture once" là P09 ở BS, P03 ở docs | gộp G2 | nhỏ |
| B-21..22 | 04, 05, 07 | KHỚP | C1–C5, giới hạn, pipeline, confidence, trường trọng yếu, lineage, KPI, bảo mật, 10 entity, autonomy, EPIC R, UC-06..08, NFR; C6–C10 & doc type P1 chủ ý OUT | — | — |

## C. Domain điều hành & kinh doanh (BRD §7–§10)

| # | File · mục | Loại | BRD (dòng) → docs | Xử lý | Mức |
|---|---|---|---|---|---|
| C-01 | 05 §4.7, 10 §3.4, 00 | MT | D07 Strategy **P0 cơ bản**: Vision→Pillar→Objective→Initiative→Project (L388–395) — không có Initiative/Milestone | DEC G3 | lớn |
| C-02 | 03 METRIC-RSK-06 | MT | SEI = % initiative đúng tiến độ (L397) — docs tính theo Objective | DEC G3 | TB |
| C-03 | 05 ENT-Objective | LT nội bộ | 03:122 dùng `Objective.weight` nhưng 05 không có cột | DEC G3 | TB |
| C-04 | 03 (thiếu FR-EXE), 05 ENT-KPI | THÊM | D08 P0: baseline/min/stretch/weight, 5 dải, trần 150%, cascade 100%, khóa kỳ (L413–431) | DEC G3 | lớn |
| C-05 | 05 enum direction | MT | 4 hướng + 6 kiểu giá trị (L415) vs 2 hướng | DEC G3 | TB |
| C-06 | 03, 05 | THÊM | Khung KPI/OKR theo phòng ban, Overall score (L401–409) | DEC G3 | TB |
| C-07 | 05 OKR/CheckIn, EP-46/48 | THÊM | 2–5 KR, cấp Team, committed/aspirational, chấm 0–1, check-in blocker/hỗ trợ (L443–448) | DEC G3 | TB |
| C-08 | 05 ↔ 10 EP-48 | LT nội bộ | EP-48 nhận `kpi_id`, ENT-CheckIn không có | tự sửa (theo 10) | nhỏ |
| C-09 | 05 ENT-Task, EP-44 | MT | 7 trạng thái, owner≠assignee, estimate/actual, dependency, evidence (L477–479); 10 thiếu `blocked` | DEC G3 | TB |
| C-10 | 05, 06 SCR-19 | THÊM | Milestone, dependency + đường găng, task định kỳ, template (L481–484) | DEC G3 | TB |
| C-11 | 03 METRIC-HR-03 | MT | Capacity trừ nghỉ phép/lễ/họp; AI ước lượng estimate (L487, L497) vs 40h cố định, 4h mặc định | DEC G3 | TB |
| C-12 | 05 ENT-Employee | THÊM | Kỹ năng, nghỉ phép (L548) | DEC G3 | TB |
| C-13 | 04 MEETING_MINUTES, EP-42 | MT | Ghi âm + transcript Meet/Teams/Zoom P0 (L507) — docs chỉ biên bản | DEC G1 | TB |
| C-14 | 04 §5.8 | THÊM | Biên bản có rủi ro/vấn đề/cam kết; hạn mơ hồ → xác nhận; briefing trước họp (L508–513) | tự sửa 04; briefing → DEC G3 | nhỏ |
| C-15 | 05 ↔ 10 EP-42/43 | LT nội bộ | Tên field Meeting/Decision lệch (consent, participants, review_at[]) | tự sửa (theo 10) | nhỏ |
| C-16 | 01 §3 | MT | D13 Calendar P0 (L515–520) — trùng A-07 | DEC G1 | lớn |
| C-17 | 04 §1, 05 | MT | D14 Knowledge P0: hỏi đáp có trích dẫn, versioning (L522–527) — trùng A-10/B-04 | DEC G1 | TB |
| C-18 | 03 FR-FIN-05 | THÊM | Dòng tiền 13 tuần; chi phí đột biến (L539) | DEC G4 | nhỏ |
| C-19 | 05 ↔ 10 EP-78 | THÊM + LT | Contract xuyên domain (P1); field 05 ≠ EP-78 | tự sửa drift; xuyên domain → OQ | TB |
| C-20 | 03/05/10 risk category | MT + LT | 13 danh mục (L615); 3 file lệch nhau (product vs technology) | DEC G4 | TB |
| C-21 | 05 ENT-Risk, BR-RSK | THÊM | Velocity, risk appetite, vượt khẩu vị → Briefing (L617–620) | DEC G4 | TB |
| C-22 | 03 BR-RSK-03, 05 | MT | Rủi ro AI đề xuất ở trạng thái "đề xuất" chờ owner (L628) — docs vào thẳng register (ảnh hưởng story R-12) | DEC G4 | TB |
| C-23 | 02, 03 | THÊM | AI không chấm điểm nhân sự; kết quả đánh giá = Mật (L463–465, L551) | tự sửa | nhỏ |
| C-24 | 01 §3 OUT | LT | Partner, Technical, Customer 360 chưa liệt kê OUT | tự sửa | nhỏ |
| C-25 | 01, 03 | LT ưu tiên | MVP chỉ Finance Lite + Sales Lite P0; HR/Product/Risk P1 (L531) — docs Must | DEC G1 (xác nhận mở rộng) | TB |
| C-26..28 | — | KHỚP | Performance cycle, Procurement, Workflow nâng cao, Jira, Governance chủ ý OUT; Finance/Sales Lite, risk P×I, overload 110%, họp→task, what-if, consent | — | — |

## D. AI Platform, Executive Intelligence, Data Foundation, US, NFR (BRD §11–§18)

| # | File · mục | Loại | BRD (dòng) → docs | Xử lý | Mức |
|---|---|---|---|---|---|
| D-01 | 13 DEC-143 | MT quy trình | Pipeline coverage gợi ý < 3x (L784–804); DEC-143 (< 2,5/2,8) có số nhỏ hơn DEC-144 | DEC G7 (tái xác nhận) | nhỏ |
| D-02 | 10 §7 | THÊM | Metadata tool: schema, data_scope, classification, reversible, cost… (L668) | DEC G5 | TB |
| D-03 | 10 §7 | THÊM | Tool assign/update_task, get_kpi/okr_status, send_notification, generate_report, request_approval… (L657–665) | DEC G5 | TB |
| D-04 | 10 §7, 02 §7 | THÊM | Nhóm APPROVAL ("AI không tự gọi") và EXECUTION (L672–677) | tự sửa | nhỏ |
| D-05 | 07 §3–5, 05 | THÊM | Orchestrator + 6 agent P0 (L640–693) — docs 1 luồng chat | DEC G5 (agent = profile trong `ai_core`) | lớn |
| D-06 | 07, 05 | THÊM | Prompt versioning, Memory, Evaluation, hiệu chỉnh confidence (L642–650) | DEC G5 | TB |
| D-07 | 02 §7, 10 §2 | THÊM | Quyền = agent ∩ người; job theo lịch dùng service identity hẹp (L703–705) | DEC G5 | TB |
| D-08 | 10 EP-117 | MT | Đổi autonomy policy cần Admin + chủ domain (L719, L1099) — docs chỉ `ai:admin` | DEC G5 | TB |
| D-09 | 10 §7.2, 04 §9 | MT (BRD tự mâu thuẫn) | Chi phí < 5 tr L3 (L717) vs dữ liệu tiền L2 bắt buộc (L1091) | DEC G5 — mặc định: trần L2 cho tool tiền | TB |
| D-10 | 02 §7, 03 | THÊM | AI không quyết tuyển/sa thải/lương; không huấn luyện bằng dữ liệu khách (L1071) | tự sửa | nhỏ |
| D-11 | 05, 10 | THÊM | Xóa dữ liệu quan trọng cần 2 người (L1098) | DEC G5 | TB |
| D-12 | 05 AuditLog/ModelCallLog | THÊM | why, approval, prompt_version, agent, autonomy, confidence (L1103–1105) | DEC G5 | TB |
| D-13 | 03, 06 SCR-15, EP-119 | THÊM | Báo cáo AI governance tháng; ngân sách theo phòng ban/agent (L727, L1108) | tự sửa báo cáo; ngân sách → DEC G5 | TB |
| D-14 | 03 §7.1, 05 Insight, 06 | MT | Insight 9 phần (Root cause, Risk, Expected outcome, Action) vs 5 phần (L732) | DEC G5 | TB |
| D-15 | 03, 07 | KHỚP + chi tiết | Số không nguồn: chặn hoặc nhãn "ước tính" (L723) | tự sửa (ghi v2 = chặn) | nhỏ |
| D-16 | 03 FR-AI-09 | THÊM | What-if theo tham số chi phí; nhắc việc; giọng nói (L740–754) | DEC G5 | TB |
| D-17 | 03 §7.2, EP-10 | MT nhỏ | Briefing 07:00 cấu hình được; khối "Hôm nay", KPI/OKR % (L759–768) vs 06:00 | tự sửa (`BRIEFING_TIME`) | nhỏ |
| D-18 | 07 §5.3 | THÊM | Bước Verification sau Execution (L700, L1113) — trùng A-11 | tự sửa | nhỏ |
| D-19 | 03 §2, 00 | MT | Data Quality Score là chỉ số P0 (< 80) (L804); docs không có metric, ngưỡng 80 vs 60 | DEC G4 | TB |
| D-20 | 03 RSK-06 | MT | Trùng C-02 | gộp G3 | nhỏ |
| D-21 | 01, 05, 10 | THÊM | **Reporting D28 P0**: báo cáo ngày/tuần/tháng/HĐQT, xuất PDF/Word/Excel (L806–811) — không có DEC OUT | DEC G1 | lớn |
| D-22 | 05 ↔ 10 Decision | MT nội bộ + THÊM | Nguồn từ khuyến nghị AI; đối chiếu 30/60/90 ngày (L815–817); `review_date` vs `review_at[]` | DEC G3 | TB |
| D-23 | 05 §1 | THÊM | Mọi bản ghi có `source`, `data_classification`, `version` (L867) | DEC G3 | lớn |
| D-24 | 05 §2, 00 §4.3 | THÊM | Team, Position, Strategy/Initiative, KPITarget, MeetingTranscript, ApprovalRequest, AIAgent… (L836–851) | DEC G3 | lớn |
| D-25 | 05, 07 | THÊM | Lịch sử "tại thời điểm X"; xuất toàn bộ dữ liệu (L831–832) | DEC G3 | TB |
| D-26 | 10 §8.3 | THÊM | `invoice.created` (L829) | DEC G4 hoặc map event có sẵn | nhỏ |
| D-27 | 00, 01 | THÊM | UC-01..05 (UC-01/02/03 MVP, UC-04 P0) (L871–882) — trùng A-14 | DEC G2 | lớn |
| D-28 | 02 §3, 00 §4 | MT | US ID 3 chữ số, 20+ area; **US-CEO-0x trùng mã khác nghĩa** (L912–1021) | DEC G2 | lớn |
| D-29 | 02 §3 | THÊM | US P0 chưa có: ORG, KPI-001..010, OKR, STR, PERF, RPT, AI-004/005/008 | DEC G2 + G3 | lớn |
| D-30 | 01 §3 | MT | US-CAL-001/002 P0 — trùng A-07 | DEC G1 | TB |
| D-31 | 07 NFR-02 | MT | Token đầu < 2 s (L1036) vs ≤ 5 s | DEC G7 | TB |
| D-32 | 01, 07 | MT | MFA bắt buộc — trùng A-05 | DEC G1 | TB |
| D-33 | 07 §11 | THÊM | p95 < 2 s, 99,9%, backup 30 ngày, diễn tập quý, audit export (L1031–1049) | tự sửa (map NFR, ghi OUT) | nhỏ |
| D-34 | 07 §9.3 | LT | Luật BVDLCN, DPIA, thông báo vi phạm, Luật ANM (L1075–1079) | tự sửa | nhỏ |
| K1–K3 | — | KHỚP | Autonomy L0–L3, undo 24h, kill switch, grounding, ModelGateway, lineage, RBAC/mask, IDP NFR; Modular Monolith, multi-tenant, webhook, fine-tune chủ ý OUT; 12.4 chỉ số P0 phần lớn có trong 31 metric | — | — |

## E. Gói DEC đề xuất (để human quyết trước Phase 3)

| Gói | Câu hỏi cho human | Gap | Mặc định đề xuất |
|---|---|---|---|
| **G1 — Scope v2.1** (MT với P0 BRD) | Giữ OUT hay kéo vào: Calendar, Workflow/Approval cơ bản, MFA, Reporting D28, Knowledge/RAG, Voice C2, transcript họp; xác nhận HR/Product/Risk vẫn Must; thứ tự S0–S5 | A-05..07, A-10, A-13, A-19, B-02, B-04, C-13, C-16, C-17, C-25, D-21, D-30, D-32 | **Kéo vào:** Approval cơ bản (rule theo giá trị + SLA), Reporting tối thiểu (tuần/tháng, xuất PDF), Knowledge RAG trên SOP (đã có DEC-142). **Giữ OUT có rationale:** Calendar sync, MFA, voice, transcript (demo, chưa có integration thật) |
| **G2 — ID registry** | Mã P, US, UC, FR-DC trùng mã khác nghĩa với BRD | A-01, A-14, B-01, B-23, D-27..29 | **Áp mã BRD** cho US/UC/FR-DC (BRD là canonical) + bảng ánh xạ cũ → mới trong 00; nguyên tắc docs đổi thành `PR-xx`? → *cần tạo prefix mới qua 00 §4* — hoặc giữ P docs và gọi BRD là `BRD-P` |
| **G3 — Data model Execution / Org / Strategy** | Thêm Initiative/Pillar/Milestone, KPI evaluation, OKR type, Task 7 trạng thái + dependency, Team/Position, effective-dated org, trường chung `source/data_classification/version` | A-08, C-01..12, C-14, D-22..25, D-29 | Thêm **lite**: Initiative + Milestone, KPI evaluation band + direction 4 hướng, Task 7 trạng thái + owner/estimate/actual, Team + Position; trường `source` chung; **hoãn** effective-dated, ma trận, export toàn bộ |
| **G4 — Risk & Data Quality** | Trạng thái `proposed`, 13 danh mục, appetite, DQ Score metric, dòng tiền 13 tuần | C-18, C-20..22, D-19, D-26 | Thêm `proposed` (R-12 vẫn tự sinh nhưng chờ owner — **khớp story** "chờ phân công"), 13 danh mục, DQ Score metric thứ 32 (cần ID), hoãn appetite/13 tuần |
| **G5 — AI governance & agent** | Agent model, quyền agent ∩ người, service identity cho job, tool metadata/danh mục, insight 9 phần, approval 2 bên, tool tiền L2/L3, phân loại 4 mức, role tùy biến | A-09, A-11, A-15..18, B-12, B-16, D-02..16 | Agent = profile (prompt + tool subset) trong `ai_core`; giữ 10 role (DEC-128); **tool tiền trần L2**; insight 9 phần; prompt_version + agent trong log; đổi phân loại theo BRD |
| **G6 — IDP chi tiết** | SUPERSEDED, reassign, escalation SLA, lý do sửa tài chính, checkbox/chữ ký, bỏ qua phân loại, dependency parse, DEC-123 lệch | B-03, B-05..10, B-14, B-15, B-17, B-18 | Nhận tất cả trừ sửa hàng loạt lưới và học theo NCC (OUT); dependency parse gom vào T-002 |
| **G7 — Ngưỡng & NFR** | Tái xác nhận DEC-143 sau DEC-144; TTFT 2 s vs 5 s | D-01, D-31 | Giữ DEC-143 (ghi supersede BRD gợi ý); TTFT p50 ≤ 2 s / p95 ≤ 5 s |

## F. Ước lượng Phase 3

| File | Tự sửa | Phụ thuộc DEC | Mức |
|---|---|---|---|
| 00-INDEX | A-02, A-04 | G2 (registry), G3/G4 (ID entity/metric) | **lớn** |
| 01-OVERVIEW | A-02, A-03, A-12, A-20, A-21, C-24 | G1 scope, G2 nguyên tắc | **lớn** |
| 02-PERSONAS | A-03, C-23, D-04, D-10, A-24 RACI | G2 US, G5 | **lớn** |
| 03-DASHBOARD | D-15, D-17 | G3 (FR-EXE, SEI, HR-03), G4, G5 insight | **lớn** |
| 04-IDP | A-02, B-11, B-13, B-15, B-19, B-20, C-14 | G1 (voice/SOP), G2 (FR-DC), G6 | **lớn** |
| 05-DATA-MODEL | C-08, C-15, C-19 | G3, G4, G5, G6 | **lớn** |
| 06-UI-UX | B-19, B-20 | G1 (Report/Approval SCR), G3, G5 | TB |
| 07-ARCH | D-18, D-33, D-34 | G1, G5, G6 (dependency), G7 | TB |
| 08-DEMO-DATA | — | G3/G4 (seed Initiative, proposed risk, DQ) | TB |
| 09-BUILD-PLAN | — | G1 (task mới), G3–G6 | TB |
| 10-API | C-08, C-15, C-19 | G3–G6 (EP/TOOL/EVT mới) | **lớn** |
| 11-WORKFLOW | — | G2 (ID) | nhỏ |

**Tổng:** 12/12 file cần sửa — 8 lớn, 3 TB, 1 nhỏ. ~25 gap tự sửa được; ~70 gap cần quyết định, gom thành **7 gói DEC (G1–G7)**. Nên chốt G1 → G2 trước (scope + ID quyết định mọi file khác).

## G. Quyết định của human (2026-10-19, @CyEyes) — chiến lược 2 bản

- **v2.0 — Demo-ready:** giữ scope gần S0–S5 hiện tại + bổ sung tối thiểu để demo mạch lạc.
- **v2.1 — Production-ready:** kéo phần lớn P0 BRD còn lại (Knowledge RAG, MFA, Calendar, Voice, multi-agent…).

| Gói | DEC | Kéo vào v2.0 | Hoãn sang v2.1 / OUT (lý do) |
|---|---|---|---|
| G1 Scope | DEC-153 ¹ | Approval cơ bản (rule theo giá trị + SLA) — A-06; Reporting tối thiểu weekly/monthly PDF + Excel — D-21; Meeting transcript mock upload thủ công (không Meet/Zoom/Teams) — C-13; HR/Product/Risk giữ Must — C-25 | Knowledge RAG (A-10, B-04, C-17): cần 3–4 tuần ingest SOP + tuning, v2.0 trích dẫn qua lineage metric/record · MFA (A-05): không demo-able · Calendar sync (A-07, C-16, D-30): cần OAuth Google/Microsoft thật · Voice C2 (B-02): cần STT thật |
| G2 ID registry | DEC-146 | Áp mã BRD cho US / UC / FR-DC; bảng mapping "mã cũ → mã mới" ở 00 §4; giữ `P01–P09` của docs, nguyên tắc BRD gọi `BRD-P01..P11` (không tạo prefix mới) | — |
| G3 Data model lite | DEC-147 | Initiative, Milestone, Team, Position, KPI evaluation bands, Task 7 trạng thái + owner/estimate/actual; trường chung `source`, `data_classification`, `version` (D-23) | Effective-dated org, ma trận kiêm nhiệm, export toàn bộ dữ liệu |
| G4 Risk & DQ | DEC-148 | Trạng thái `proposed` (R-12 tự sinh, chờ owner), 13 danh mục, DQ Score = metric thứ 32, **dòng tiền 13 tuần** (C-18, CFO demo) | Risk appetite; contract xuyên domain (P1) |
| G5 AI governance | DEC-149, DEC-150 (hoãn) | Tool metadata (D-02); danh mục tool approve/reject/report/notify/request_approval (D-03); insight 9 phần (D-14); kill switch per-agent; 4 mức classification BRD (A-15); AI không chấm điểm nhân sự (D-10); log `why/approval/agent/autonomy/confidence` (D-12); 2-sided approval **chỉ** finance action > ngưỡng, còn lại 1 approver (D-11) | Orchestrator + 6 agent (v2.0 = 1 chat assistant + Tool Registry); prompt versioning; memory/evaluation; service identity theo job (v2.0 = 1 service account); quyền agent ∩ người (v2.0 = quyền người); role tùy biến (giữ DEC-128); L3 cho tool tiền (v2.0 trần L2) |
| G6 IDP | DEC-151 | `SUPERSEDED`, reassign reviewer, escalation SLA, lý do bắt buộc khi sửa trường tài chính, checkbox/signature, bỏ qua phân loại khi đã chọn loại; dependency parse PDF/HEIC/DOC/XLS gom vào T-002; EP-20 giữ `files[]`, DEC-123 chỉ áp dụng upload đơn | Bulk grid edit; học theo vendor pattern |
| G7 Ngưỡng & NFR | DEC-152 | Tái xác nhận DEC-143 sau DEC-144 (pipeline coverage 2,5x/2,8x thay gợi ý < 3x BRD); TTFT p50 ≤ 2 s / p95 ≤ 5 s | — |

¹ Human không gán số DEC cho G1; agent đề xuất **DEC-153** (số tiếp theo sau DEC-152) — human có thể đổi số.

**Kế hoạch Phase 3 (4 sub-phase):** 3a = 00, 05 (G2, G3, G4) · 3b = 01, 02, 03 (G1, G2, G5) · 3c = 04, 06, 07 (G1, G6) · 3d = 08, 09, 10, 11 (G3–G6). Gap "tự sửa" (§A–§D) thực hiện cùng sub-phase của file đích.

## Version

- **Version:** 1.0.0 (reference)
- **Last updated:** 2026-10-19
- **Maintainer:** @CyEyes
- **Change:** Tạo mới — lưu gap analysis Phase 2 và quyết định G1–G7 của human.
