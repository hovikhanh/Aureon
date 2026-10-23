# 08 — Demo / Seed Data Spec (Aureon v3 — AI-EOS)

> **Nguồn chuẩn:** `_reference/SOURCE-BRD-v1.1.md` §19.1 (MVP 90 ngày), §20.2 (kịch bản CEO 7 bước), §14 (UC-01..08), §12.4 (bộ chỉ số sức khỏe P0); kế thừa doanh nghiệp giả định `main` (Công ty ABC).
> **Phụ thuộc:** 00, 01, 04, 05. **Trạng thái:** ✅ current — Aureon v3 (AI-EOS) CHÍNH THỨC. **Ngày:** 2026-10-23 · **Maintainer:** @CyEyes
> **Ghi chú:** tài liệu chính thức v3, tách từ Aureon v2.1 (nay archived ở `docs/_archive/v2.1/`).
> **Phạm vi R-DEC-09 (docs-first):** file này mô tả **chiều sản phẩm** của bộ dữ liệu demo — doanh nghiệp mẫu, bộ dữ liệu cần cho mỗi UC P0, khối lượng gợi ý, dữ liệu để mỗi chỉ số sức khỏe P0 có giá trị (kèm ≥ 1 chỉ số ở ngưỡng cảnh báo). **KHÔNG** viết seed code, **KHÔNG** field-level DB (tên cột/kiểu/constraint per-entity) — hoãn sang đợt code. Giữ **single tenant ABC** (R-DEC-07).

---

## 1. Phạm vi seed

Theo **R-DEC-05: phủ tập P0 MVP** trước — đủ chạy **UC-01, UC-02 (transcript), UC-03, UC-04, UC-06, UC-07** và **kịch bản CEO** (BRD §20.2), mở rộng P1 theo phase sau (backlog, không seed đợt này). Mục tiêu dữ liệu demo: mỗi use case P0 chạy được end-to-end ra kết quả **thật, có nguồn** (P06 Traceability), và mỗi chỉ số sức khỏe P0 (BRD §12.4) có **giá trị tính được** từ dữ liệu seed.

> **Khác `main`:** `main` seed Công ty ABC ~150 NV, 9 doc type, 5 trụ F.O.C.U.S. AI-EOS giữ **cùng doanh nghiệp giả định** (dữ liệu giả, không PII thật — nhất quán ràng buộc an toàn) nhưng tổ chức dữ liệu theo **28 domain / 7 role + AI Agent**. Seed đợt này chỉ phủ **20 domain P0** (skeleton §12bis).

### 1.1. Nguyên tắc dữ liệu demo

- **DD-01 — Tính truy nguyên:** mọi con số seed phải gắn được nguồn (bản ghi / tài liệu gốc / measurement) để AI trích dẫn (P06). Dữ liệu "mồ côi" (không nguồn) không đưa vào.
- **DD-02 — Phủ ngưỡng:** bộ dữ liệu phải làm mỗi nhóm chỉ số sức khỏe có cả trạng thái **ok / warning / critical** để Briefing (UC-01) nêu được ngoại lệ — không được "toàn xanh".
- **DD-03 — Dữ liệu giả:** không PII/dữ liệu thật trong seed/fixture/prompt; trường nhạy cảm (lương) là số giả, che theo quyền (§6).
- **DD-04 — Idempotent:** bộ seed chạy lại cho cùng kết quả; không nhân bản (chi tiết cơ chế hoãn R-DEC-09).
- **DD-05 — Mốc thời gian cố định:** mọi dữ liệu tương đối (hạn, kỳ, "hôm nay") neo theo `DEMO_REFERENCE_DATE=2026-10-20` để demo tái lập.

## 2. Doanh nghiệp giả định

**Công ty TNHH TM&DV ABC** — phân phối thiết bị văn phòng + bảo trì + nền tảng "ABC Order"; ~150 nhân sự, 7 phòng ban, ~300 tỷ VNĐ/năm; TP.HCM + chi nhánh Hà Nội. `DEMO_REFERENCE_DATE=2026-10-20`; kỳ demo T9 / Q3 2026.

### 2.1. Cấu trúc tổ chức mẫu (D01)

| Phòng ban | Trưởng (role) | Quy mô gợi ý | Dùng cho UC/chỉ số |
|---|---|---|---|
| Ban Giám đốc | CEO (ROLE-CEO) | 2–3 | UC-01, UC-02, kịch bản CEO |
| Kinh doanh (Sales) | Director (ROLE-DIR, `scope_pillars={C}`) | ~35 | UC-03, pipeline coverage, win rate |
| Vận hành & Dịch vụ | Manager (ROLE-MGR, phạm vi phòng ban — R-DEC-27) | ~45 | hoàn thành đúng hạn, dự án trễ |
| Tài chính — Kế toán | Director (ROLE-DIR, `scope_pillars={F}`) | ~12 | runway, chênh lệch ngân sách, UC-06 (hóa đơn) |
| Nhân sự (HR) | Director (ROLE-DIR, `scope_pillars={O}` — R-DEC-27) | ~8 | quá tải, UC-07 onboarding |
| Sản phẩm/Công nghệ (ABC Order) | Director (ROLE-DIR, `scope_pillars={U}`) | ~30 | OKR at risk (UC-04), dự án trễ |
| Hành chính — Trợ lý | Manager (ROLE-MGR) + Reviewer (ROLE-REV) | ~15 | UC-06 chụp biên bản, hàng chờ review |

- **Reporting line ma trận:** mỗi Employee có 1 quản lý trực tiếp; vài nhân sự tham gia dự án chéo phòng (phục vụ chỉ số quá tải & workload).
- **User demo mỗi role:** 1 tài khoản demo cho ROLE-CEO/DIR/MGR/EMP/REV/ADMIN + 1 AI Agent actor (ROLE-AI) — phục vụ kiểm chứng scoping theo quyền (D02).

## 3. Seed theo domain P0

Bảng liệt kê **chiều sản phẩm** của dữ liệu cần cho từng domain P0; khối lượng là **gợi ý tối thiểu** để UC chạy và chỉ số có giá trị (không phải ràng buộc cứng).

| Domain | Dữ liệu seed (chiều sản phẩm) | Khối lượng gợi ý |
|---|---|---|
| D01 Organization | Company ABC, 7 Department, Team, ~150 Employee, Position, reporting line (ma trận) | 7 dept · ~150 NV |
| D02 Admin & Security | 7 role + AI Agent actor, 1 user demo/role, data policy, 4 mức phân loại, AI access scope | 6 user + 1 AI actor |
| D03 Data Capture | 1 hóa đơn NEEDS_REVIEW, 1 biên bản họp mẫu, Extraction Schema cho 6 doc type P0 (#1–#6) | 2 tài liệu mồi + 6 schema |
| D05 Notification | Vài notification mẫu (task giao, cảnh báo ngưỡng, review chờ) | ~5 |
| D06 Integration Hub | Mock sự kiện lịch Google/MS cho CEO (không tích hợp thật) | 1 nguồn mock |
| D07 Strategy | 1 Strategy, 3–4 StrategicPillar, StrategicObjective, Initiative | 1 cây chiến lược |
| D08 KPI | Cây KPI công ty→phòng ban→cá nhân; KPITarget; KPIMeasurement vài kỳ (có 1 KPI dưới ngưỡng cho UC-03) | ~12 KPI · 3 kỳ |
| D09 OKR | Objective công ty + phòng ban; KeyResult; KRMeasurement (có ≥ 1 KR at-risk cho UC-04) | ~6 Obj · ~15 KR |
| D10 Performance | 1 PerformanceCycle đang mở, vài CheckIn | 1 cycle · ~10 check-in |
| D11 Task/Project | 2–3 Project, Task có owner/hạn, Workload (có người quá tải >110% để kích chỉ số & UC F5) | ~3 dự án · ~60 task |
| D12 Meeting | 1 Meeting + MeetingTranscript + MeetingSummary + Decision + ActionItem (UC-02/06) | 1 cuộc họp đầy đủ |
| D13 Calendar | Sự kiện lịch CEO hôm `DEMO_REFERENCE_DATE` (UC-01 "TODAY") + deadline từ task | ~5 sự kiện |
| D14 Knowledge | Vài Document/Knowledge (SOP, chính sách) nạp từ doc type #5 | ~5 tài liệu |
| D15 Finance Lite | Revenue/Expense/CashBalance theo kỳ → runway < ngưỡng (kích cảnh báo) + chênh lệch ngân sách | ~3 kỳ |
| D16 HR | Position, phân bổ nhân sự, workload (nguồn chỉ số quá tải) | theo D01 |
| D17 Sales Lite | Pipeline, Opportunity (giai đoạn khác nhau), win/lost lịch sử → coverage & win rate | ~25 cơ hội |
| D26 AI Platform | AIAgent P0 (CEO, Data Capture, Performance, Task, Meeting, Reporting), AITool đã đăng ký, AIBudget tháng | 6 agent |
| D27 CEO Assistant | Lịch sử hội thoại mồi (tùy chọn) + insight mẫu cho Briefing | — |
| D28 Reporting | Dữ liệu đủ cho Briefing (UC-01) + Decision Log (quyết định mồi với kết quả kỳ vọng) | ~2 quyết định |

> Field, kiểu, constraint của mỗi `ENT-<Name>` **chi tiết hóa ở đợt code (R-DEC-09)**; ở đây chỉ nêu bản ghi cần có và vai trò nghiệp vụ.

## 4. Bộ dữ liệu theo từng UC P0

Mỗi UC P0 cần một **tập dữ liệu tối thiểu** để chạy end-to-end. Bảng dưới gắn UC ↔ dữ liệu ↔ kết quả nghiệm thu (BRD §14) để dữ liệu demo "đủ chạy, có nguồn".

### 4.1. UC-01 — CEO Morning Briefing (P0)

- **Dữ liệu cần:** số liệu Finance (Revenue/Expense/CashBalance), Sales (pipeline, win rate), People (workload/quá tải), KPI/OKR (measurement gần nhất), Project (tiến độ, task trễ), Risk (≥ 1 critical), Calendar (sự kiện hôm `DEMO_REFERENCE_DATE`), ≥ 1 quyết định chờ.
- **Ràng buộc để demo:** ít nhất **1 chỉ số ở ngưỡng cảnh báo** (xem §5) để Briefing nêu ngoại lệ; mọi số có nguồn (P06); Briefing ≤ 1 trang.
- **Kết quả nghiệm thu (BRD §14):** Briefing tổng hợp đúng giờ; mỗi con số click được tới bản ghi/tài liệu gốc.

### 4.2. UC-02 — Meeting to Execution (P0, transcript)

- **Dữ liệu cần:** 1 Meeting + MeetingTranscript (văn bản mẫu) chứa ≥ 3 quyết định và ≥ 5 action item có người phụ trách + hạn; danh sách nhân sự để khớp tên (D01).
- **Ràng buộc để demo:** ≥ 90% action item được nhận diện; task chỉ tạo **sau khi chủ trì duyệt** (P04 Human in the Loop); đồng bộ Calendar.
- **Kết quả nghiệm thu:** Decision/ActionItem/Task tạo đúng, gắn owner + deadline, có "Xem tài liệu gốc".

### 4.3. UC-03 — KPI Underperformance (P0)

- **Dữ liệu cần:** ≥ 1 KPI có KPITarget và KPIMeasurement nhiều kỳ, trong đó kỳ gần nhất **thực tế < ngưỡng** (gap rõ); dữ liệu liên quan (task, workload) để AI phân tích nguyên nhân gốc.
- **Ràng buộc để demo:** khuyến nghị có bằng chứng; task khắc phục gắn đúng KPI; Manager duyệt trước khi tạo.
- **Kết quả nghiệm thu:** gap phát hiện tự động → khuyến nghị có nguồn → task gắn KPI.

### 4.4. UC-04 — OKR At Risk (P0)

- **Dữ liệu cần:** ≥ 1 Objective có KeyResult với KRMeasurement **giảm hoặc confidence thấp**; task/dependency/workload liên quan để lộ blocker; kỳ OKR còn ≥ 3 tuần tới hạn tính từ `DEMO_REFERENCE_DATE`.
- **Ràng buộc để demo:** cảnh báo trước cuối kỳ ≥ 3 tuần; đề xuất can thiệp có bằng chứng.
- **Kết quả nghiệm thu:** KR at-risk được phát hiện sớm; đề xuất điều chỉnh task/nguồn lực.

### 4.5. UC-06 — Biên bản giấy → thực thi (P0)

- **Dữ liệu cần:** 1 tài liệu biên bản họp (doc type #1) ở trạng thái đầu pipeline (ảnh/PDF mẫu, dữ liệu giả); Extraction Schema #1; danh sách nhân sự để khớp tên.
- **Ràng buộc để demo:** từ lúc tải tới khi task được giao ≤ 10 phút (gồm duyệt); mọi action item có người phụ trách + hạn; mỗi bản ghi có lineage tới trang tài liệu gốc.
- **Kết quả nghiệm thu:** Meeting/Decision/ActionItem/Task ghi qua Tool Registry; Decision Log cập nhật.

### 4.6. UC-07 — Onboarding doanh nghiệp (P0)

- **Dữ liệu cần:** 1 file import C5 (danh sách NS + sơ đồ tổ chức, doc type #4) kèm vài dòng **lỗi cố ý** (thiếu quản lý, sai định dạng) để demo tách dòng lỗi; 1 tài liệu SOP/chính sách (doc type #5) cho knowledge base.
- **Ràng buộc để demo:** dựng được cây tổ chức từ file; dòng lỗi xuất ra file sửa, không chặn dòng hợp lệ; dữ liệu nhạy cảm (lương) che theo quyền.
- **Kết quả nghiệm thu:** cây tổ chức + hồ sơ + knowledge dựng được; dashboard đầu tiên hiển thị.

### 4.7. Kịch bản CEO 7 bước (BRD §20.2)

Dữ liệu seed phải làm mỗi bước ra kết quả thật, có nguồn:

1. **Ask** ("Tình hình công ty?") → cần đủ Finance/Sales/People/KPI/OKR/Projects/Risks (§3).
2. **Understand** → AI tổng hợp có nguồn (P06).
3. **Investigate** ("Tại sao doanh thu thấp?") → cần dữ liệu doanh thu dưới kế hoạch + nguyên nhân truy được (pipeline giảm, nhân sự nghỉ…).
4. **Decide** → AI đề xuất phương án (cần đủ dữ liệu để so sánh).
5. **Act** ("Thực hiện phương án 1") → AI tạo task/owner/deadline/lịch/thông báo (L3, undo ≥ 24h) — cần nhân sự + dự án hợp lệ để giao.
6. **Follow-up** → cần task vừa tạo để theo dõi.
7. **Verify** → cập nhật Decision Log (cần quyết định mồi có kết quả kỳ vọng đo được).

## 5. Chỉ số sức khỏe demo (BRD §12.4)

Seed để **mỗi chỉ số P0 có giá trị tính được** từ dữ liệu, và bộ chỉ số phủ cả ok/warning/critical (DD-02). Bảng dưới gắn chỉ số P0 ↔ dữ liệu nguồn ↔ trạng thái mục tiêu cho demo.

| Nhóm | Chỉ số P0 (BRD §12.4) | Ngưỡng cảnh báo | Dữ liệu nguồn cần seed | Trạng thái demo |
|---|---|---|---|---|
| Tài chính | Tăng trưởng DT, % đạt kế hoạch | thấp hơn kế hoạch > 10% | Revenue nhiều kỳ + kế hoạch | 🟠 dưới kế hoạch (mồi UC-03 Investigate) |
| Tài chính | **Cash runway** | < 6 tháng | CashBalance + burn ròng hàng tháng | 🔴 **< 6 tháng (chỉ số cảnh báo chính của demo)** |
| Tài chính | Chênh lệch ngân sách | > 10% | Budget vs Expense theo cost center | 🟠 vượt ~12% |
| Khách hàng | Pipeline coverage | < 3x | Opportunity có trọng số vs chỉ tiêu còn lại | 🟠 ~2.5x |
| Khách hàng | Win rate, chu kỳ bán hàng | giảm > 20% | Won/lost lịch sử | 🟢 ổn định |
| Vận hành | Hoàn thành đúng hạn | < 80% | Task đến hạn vs xong đúng hạn | 🟢 ~85% |
| Vận hành | Dự án trễ tiến độ | > 20% | Project có tiến độ thực | 🟢 ~10% |
| Vận hành | Thực thi quyết định | < 70% | ActionItem đến hạn vs đã xong | 🟢 ~75% |
| Con người | **Quá tải** | > 10% | Workload > 110% trong 2 tuần vs tổng NS | 🟠 **~12% (kích UC F5 / điều phối)** |
| Chiến lược | Strategy Execution Index | < 70% | Initiative đúng tiến độ (có trọng số) | 🟢 ~72% |
| Dữ liệu | Data Quality Score | < 80/100 | đầy đủ/chính xác/kịp thời/nhất quán | 🟢 ~88/100 |

- **Chỉ số cảnh báo chính của demo:** **Cash runway 🔴 < 6 tháng** — là ngoại lệ số 1 trong Briefing (UC-01) và điểm vào cho kịch bản CEO Investigate (BRD §20.2). Kèm **Quá tải 🟠** và **Pipeline coverage 🟠** để Briefing nêu ≥ 2–3 ngoại lệ.
- Các chỉ số còn lại giữ ở trạng thái ok để demo không "toàn đỏ"; dữ liệu đủ để mọi chỉ số có giá trị + timestamp (FR-DATA-03 freshness), không có chỉ số "N/A".
- **SLA freshness vs operational:** dữ liệu demo gắn `last_updated` để Briefing nêu dữ liệu đã cũ khi cần (không lẫn với SLA vận hành — nhất quán §6.1 CLAUDE.md).

## 6. Ràng buộc an toàn

- **Dữ liệu giả:** không PII/dữ liệu thật trong seed/fixture/prompt (DD-03). Trường mức 4 (lương, ngày sinh…) là số giả; AI/role không đủ quyền nhận `{ masked: true }` — phục vụ demo kiểm chứng field-level security (D02).
- **Single tenant ABC (R-DEC-07):** seed đúng **1 tenant ABC** cho MVP; mọi entity nghiệp vụ có `tenant_id` sẵn để nâng đa tenant sau (chi tiết hoãn R-DEC-09).
- **Idempotent (DD-04):** cơ chế seed/reset chi tiết hóa ở đợt code (R-DEC-09); ở đây chỉ chốt yêu cầu "chạy lại cho cùng kết quả".
- **Nhất quán §6.6 / §6.8 CLAUDE.md:** không đưa secret/mật khẩu vào dữ liệu demo hay prompt.

## 7. Mapping sang `main`

| Khía cạnh | `main` v2.1 | `ai-eos` (file này) |
|---|---|---|
| Doanh nghiệp | ABC ~150 NV, 9 doc type, 5 trụ | ABC ~150 NV, **6 doc type P0** (#1–#6), **20 domain P0** |
| Hóa đơn mồi | 1 hóa đơn NEEDS_REVIEW | giữ (D03) + 1 biên bản họp (UC-06) |
| Chỉ số cảnh báo demo | F🟢 C🟢 U🟡 O🟡 S🔴 (13 alert) | **Cash runway 🔴** + Quá tải 🟠 + Pipeline coverage 🟠 |
| Role | 10 role F.O.C.U.S | 7 role + AI Agent actor (ROLE-AI) |

> Ánh xạ chi tiết: TRACEABILITY-SKELETON §12.

## Open questions

- OQ-08-01: Doc type trong seed — ĐÃ CHỐT: R-DEC-05 — dùng tập doc type P0 theo 04 (6 loại #1–#6); 14 doc type BRD đầy đủ là backlog phase sau.
- OQ-08-02: Seed đa tenant vs 1 tenant — ĐÃ CHỐT: R-DEC-07 — seed **1 tenant ABC** cho MVP; data model có `tenant_id` sẵn để nâng đa tenant sau.
- OQ-08-03: Khối lượng seed cụ thể (số bản ghi chính xác mỗi entity) — **mở, không blocking**: §3/§4 nêu khối lượng *gợi ý tối thiểu*; con số chốt (và script sinh dữ liệu idempotent) để **đợt code (R-DEC-09)**.
- OQ-08-04: Giá trị số của chỉ số ở ngưỡng cảnh báo (burn rate, hệ số coverage, % quá tải cụ thể) — **mở, không blocking**: §5 chốt *trạng thái mục tiêu* (🔴/🟠/🟢) và dữ liệu nguồn; số cụ thể tính bằng script ở đợt code để tránh "tính nhẩm".

## Version
- **Version:** 1.0.0 (current)
- **Last updated:** 2026-10-23
- **Maintainer:** @CyEyes
- **Change 1.1.0 (đề xuất — R-DEC-27):** §2.1 trưởng Nhân sự = ROLE-DIR `{O}` (giữ quyền mức 4 đúng người), trưởng Vận hành & Dịch vụ = ROLE-MGR phạm vi phòng ban; ghi `scope_pillars` cho từng DIR.
- **Change 1.0.0 (promote):** Promote tài liệu AI-EOS lên CHÍNH THỨC Aureon v3; di chuyển vào vị trí docs chuẩn; v2.1 archived (docs/_archive/v2.1/).
- **Change 0.3.0:** Mở rộng spec-level P0 — thêm nguyên tắc dữ liệu demo DD-01..05 (§1.1); cấu trúc tổ chức mẫu ABC theo 7 phòng ban ↔ role ↔ UC/chỉ số (§2.1); seed theo 20 domain P0 kèm khối lượng gợi ý (§3); **bộ dữ liệu cần cho từng UC P0 UC-01/02/03/04/06/07 + kịch bản CEO 7 bước** với tiêu chí chấp nhận (§4); bảng chỉ số sức khỏe P0 ↔ dữ liệu nguồn ↔ trạng thái demo, chốt **Cash runway 🔴** là chỉ số cảnh báo chính + Quá tải 🟠 + Pipeline coverage 🟠 (§5); ràng buộc an toàn + single tenant ABC (§6); mapping sang `main` (§7); thêm OQ-08-03/04. (spec-level, chưa promote ở thời điểm đó); không viết seed code/field-level DB (R-DEC-09).
- **Change 0.2.0:** Chốt Q1–Q6 (R-DEC-05..10) — cập nhật trạng thái quyết định, đóng OQ liên quan; phạm vi docs-first P0.
- **Change 0.1.0:** Viết lại 08 theo AI-EOS — phạm vi seed P0 MVP, Công ty ABC theo 28 domain/7 role+AI Agent, seed theo domain, kịch bản CEO 7 bước, chỉ số sức khỏe demo, ràng buộc an toàn.
