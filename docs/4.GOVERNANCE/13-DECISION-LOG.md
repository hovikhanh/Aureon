# 13 — Decision Log (Aureon v3 — AI-EOS)

> **Vai trò:** Gate B. Theo dõi quyết định cho AI-EOS P0 — tài liệu chính thức Aureon v3 (tách từ Aureon v2.1, nay archived ở `docs/_archive/v2.1/`). **Số DEC chính thức do human cấp**; `R-DEC-*` / `Q*` / `B*` là nhãn nội bộ cho tới khi human cấp DEC (CLAUDE.md §6.7).
> **Trạng thái:** ✅ current — Aureon v3 (AI-EOS) CHÍNH THỨC. **Ngày:** 2026-10-23 · **Maintainer:** @CyEyes

---

## 1. Quyết định nền Q1–Q6 — ĐÃ CHỐT (human, 2026-10-22)

Human đã chốt 6 quyết định nền (chọn mặc định đề xuất). Đây là cơ sở cho toàn bộ bộ tài liệu P0; mọi file 00–14 bám theo.

| ID | Câu hỏi | Quyết định đã chốt | Blocking | Ảnh hưởng |
|---|---|---|---|---|
| R-DEC-05 (Q1) | Viết full 28 domain hay tập P0 MVP trước | **P0 MVP trước**; khung 28 domain giữ ở 00/skeleton; P1/P2 ghi backlog ở 09, không triển khai đợt này | resolved | 01, 08, 09, 10 |
| R-DEC-06 (Q2) | Kiến trúc: Modular Monolith vs tách service | **Modular Monolith** (kế thừa DEC-125); AI Platform §11.1 là cụm module logic bên trong, không tách deployable | resolved | 05, 07 |
| R-DEC-07 (Q3) | Tenant: đa tenant vs 1 tenant | **1 tenant cho MVP; data model có `tenant_id`** sẵn ở mọi entity để nâng đa tenant sau | resolved | 05, 07, 08 |
| R-DEC-08 (Q4) | Role: 7 role BRD thuần vs ánh xạ 10 F.O.C.U.S | **7 role BRD + AI Agent actor**; Director (ROLE-DIR) có data scope thay 5 C-level; giữ **bảng ánh xạ** sang 10 role F.O.C.U.S của `main` (skeleton §12, 02) | resolved | 02 |
| R-DEC-09 (Q5) | Phạm vi đợt này: docs-only vs cả code | **Docs-first**: hoàn thiện 00–14 + governance đợt này; **code/app/migration/merge main là đợt sau** (plan riêng) sau khi docs được human promote `current` | resolved | toàn bộ (phạm vi) |
| R-DEC-10 (Q6) | ID scheme: theo BRD vs giữ ID `main` | **Theo BRD** (D01–D28, FR-*, ROLE-*, UC-*, US-*, C1–C10); giữ **bảng ánh xạ** sang METRIC-/EP-/ENT-/SCR-/TOOL- của `main` để truy nguyên (skeleton §12) | resolved | 00, mọi file |

## 2. Quyết định vận hành nhánh — ĐÃ CHỐT

| ID | Quyết định | Trạng thái |
|---|---|---|
| R-DEC-01 | Tách nhánh `ai-eos` từ `main` @ e394668; `main` giữ demo-ready v2.1 làm baseline | resolved (human) |
| R-DEC-02 | `_reference/` là nguồn Canonical chính thức của nhánh | resolved (human) |
| R-DEC-03 | Viết lại docs theo full AI-EOS (28 domain, 7 role + AI Agent, L0–L4), phạm vi P0 | resolved (human) |
| R-DEC-04 | Rebuild AI-EOS không ghi đè docs v2.1 (nay đã promote thành tài liệu chính thức Aureon v3 tại `docs/1.CONTEXT`–`docs/4.GOVERNANCE/`; v2.1 archived ở `docs/_archive/v2.1/`) | resolved (human) |
| R-DEC-11 | **Ủy quyền agent sửa `CLAUDE.md` / `AGENT.md` / `.github/copilot-instructions.md`** — chỉ trong phạm vi doc-loading AI-EOS: trỏ canonical `_reference/` + bộ docs chính thức Aureon v3 (`docs/1.CONTEXT`–`docs/4.GOVERNANCE/`), đánh dấu docs v2.1 là baseline reference-only, cập nhật branding Aureon — AI-EOS / release line Aureon v3. Giữ nguyên mọi quy tắc an toàn (gate A/B/C, cấm lộ secret, cấm tự quyết API/schema/stack). Bỏ ràng buộc CLAUDE.md §6.3(6)/§6.6(10) **chỉ cho đợt này**. Bản v2.1 lưu trong git history. | resolved (human, 2026-10-22) |

## 2bis. Quyết định đợt code (code round) — ĐÃ CHỐT (human)

> Đợt code bắt đầu (R-DEC-09: field-level chốt ở đợt code). Các quyết định dưới đây chốt field-level/schema để refactor codebase nền v2.1 sang model v3 theo phase (`09`). Human ủy quyền agent cập nhật `05-DATA-MODEL.md` (field-level) + file này trước khi đổi schema, trong phạm vi từng DEC.

| ID | Quyết định | Trạng thái |
|---|---|---|
| R-DEC-12 | **Phase 1 — Role enum v3 field-level.** `auth.role_code` (enum DB) đổi từ 10 giá trị F.O.C.U.S (CEO/CFO/VP_SALES/HR_MANAGER/REVIEWER/CPO/RISK_MANAGER/MANAGER/EMPLOYEE/ADMIN) → **7 giá trị BRD + AI Agent**: `CEO`, `DIR`, `MGR`, `EMP`, `REV`, `ADM`, `AI` (↔ ROLE-CEO/DIR/MGR/EMP/REV/ADM/AI). Ánh xạ 10→7 (R-DEC-08, 02 §2.1): CEO→CEO; **CFO/VP_SALES/HR_MANAGER/CPO/RISK_MANAGER → DIR**; MANAGER→MGR; EMPLOYEE→EMP; REVIEWER→REV; ADMIN→ADM; thêm **AI** (actor mới). Migration reversible. Field-level ghi ở `05-DATA-MODEL.md` §2.2. | resolved (human, 2026-10-23) |
| R-DEC-12a | **Phase 1 — DIR scope theo khối (chống leo quyền).** 5 C-level gộp vào một `DIR` role row với **permission set chuẩn = hợp các action domain của 5 C-level**, NHƯNG DIR bị **thu hẹp theo khối phụ trách**: thêm `auth.users.scope_pillars PILLAR[]` (tập ⊆ {F,O,C,U,S}; rỗng = toàn bộ, dùng cho ROLE-CEO). Claim JWT `scope_pillars`; `Principal.scope_pillars`. Tầng kiểm quyền ánh xạ domain↔pillar (finance↔F, hr↔O, sales↔C, product↔U, risk↔S; execution/idp/ai/dashboard/platform là cross-pillar — không lọc) và **từ chối** permission domain nếu pillar của domain ∉ `scope_pillars` (khi `scope_pillars` không rỗng). Kết quả: Finance-DIR (scope_pillars={F}) chỉ dùng `finance:*`; không thể ghi sales/hr/product/risk. CEO/non-DIR: `scope_pillars` rỗng → không lọc (hành vi như cũ). Field-level: `05-DATA-MODEL.md` §2.2. | resolved (human, 2026-10-23) |
| R-DEC-13 | **Phase 1 — `tenant_id` field-level (R-DEC-07).** Thêm cột `tenant_id UUID NOT NULL` vào **mọi business entity** (qua `TenantMixin` ở `core/base_model.py`), default = một tenant hệ thống cố định ở MVP (single-tenant); index theo `tenant_id`. Thêm claim `tenant_id` vào JWT + middleware gắn tenant hiện tại; repository enforce lọc `tenant_id`. Migration reversible, backfill tenant mặc định cho dữ liệu hiện có. Field-level ghi ở `05-DATA-MODEL.md` §2.1. | resolved (human, 2026-10-23) |
| R-DEC-14 | **Ủy quyền agent cập nhật `05-DATA-MODEL.md` + `13` (file này) cho đợt code**, trong phạm vi field-level của các DEC đợt code (R-DEC-12, R-DEC-13 và kế tiếp). Bỏ ràng buộc CLAUDE.md §6.3(2)/(6) và §6.6(1)/(10) **chỉ cho các DEC đã liệt kê**; mọi quy tắc an toàn khác giữ nguyên (gate A/B/C, cấm lộ secret, cấm tự thêm endpoint/field/tool/event ngoài 10, migration reversible). | resolved (human, 2026-10-23) |

### 2ter. Quyết định kế hoạch build MVP v3 (M1–M3) — ĐÃ CHỐT (human, phiên 2026-10-23)

> Human trả lời trực tiếp 16 câu hỏi kế hoạch (phiên lập plan build v3, 2026-10-23). Các quyết định dưới đây là căn cứ cho `09` §6 (task đợt code) và mọi phase M1.1→M3.5.

| ID | Quyết định | Ảnh hưởng | Trạng thái |
|---|---|---|---|
| R-DEC-15 | **Mở rộng R-DEC-14 sang `09`, `10`, `06`, `14`** (cùng `05`, `13`, skeleton): ở **bước S (Spec lock)** đầu mỗi phase, agent được chốt vào docs: task `T-*` (09 §6), endpoint `EP-<DOMAIN>-NN` + path/method/permission/schema, `TOOL-*`, event, mã lỗi (10), `SCR-*` (06), `TC-*` (14), field-level (05). **Bắt buộc human duyệt diff docs (⏸) trước khi code phase đó.** Không đổi version/status file (human promote); mọi quy tắc an toàn khác giữ nguyên. | 05, 06, 09, 10, 14, skeleton | resolved (human, 2026-10-23) |
| R-DEC-16 | **Đóng băng module `product` (D22) và `risk` (D25)** — P1: giữ code/test/schema/seed, **không phát triển thêm**; ẩn khỏi Sidebar + Executive mặc định; view 5 trụ F.O.C.U.S chỉ là bố cục Executive tùy chọn (03 §1); tool AI product/risk gắn cờ `p1_frozen`, không quảng bá cho model ở P0. Widget "Rủi ro" của Executive đọc rủi ro tự sinh từ alert/metric (`platform`). | 03, 06, 10 §2 | resolved (human, 2026-10-23) |
| R-DEC-17 | **D06/D13 Calendar: đồng bộ Google Calendar + Microsoft Outlook (Graph) 2 chiều thật trong MVP (M3.1)**, OAuth **delegated theo từng user** (code + PKCE, `offline_access`); adapter qua `httpx` (DEC-140), test `respx` (DEC-139), test live chỉ khi human cho phép. Token lưu **mã hóa** (pgcrypto, như mức 4); nội dung lịch = **Confidential** (không gửi LLM cloud). Kéo về bằng incremental sync (syncToken/deltaLink) qua Celery beat; đẩy ra qua outbox; webhook chỉ bật khi có URL public. Người chưa kết nối dùng lịch nội bộ. **Điều kiện:** human cấp OAuth client Google + Entra app trước M3.1. | 05, 07, 10, 14 | resolved (human, 2026-10-23) |
| R-DEC-18 | **Nguồn sự thật mã lỗi = `apps/api/src/app/core/errors.py`** (+ `AI_ERROR_CODES`, `core/handlers._HTTP_CODES`). 10 §1.4 là **bảng phản chiếu** sinh từ code; contract test (TC-SYS-003) đối chiếu hai chiều. Thêm mã mới = thêm vào code + bảng 10 §1.4 trong cùng commit, qua bước S. | 10 §1.4, tests/contract | resolved (human, 2026-10-23) |
| R-DEC-19 | **Quy ước đánh số & quy trình đợt code:** phase `M1.x/M2.x/M3.x` (theo mốc 09 §2; khác "Phase 2–5" BRD §19.2); task `T-6xx` (M1), `T-7xx` (M2), `T-8xx` (M3), `T-9xx` (nghiệm thu) — không trùng T-1xx..5xx của v2.1; endpoint `EP-<DOMAIN>-NN` (domain code ở 10 §7.1), giữ path v2.1 khi hành vi khớp; nhóm test `TC-M<x><y>-*`. Mỗi phase: vòng **S→C→F→B→N→R** (09 §6.0); **một nhánh git mỗi phase** `v3/<phase>-<slug>` tách từ `ai-eos` → PR → human merge; human duyệt sau **S** và sau **R**. | 09, 10, 14, skeleton | resolved (human, 2026-10-23) |
| R-DEC-20 | **Kênh thông báo P0 = in-app + email.** Email gửi qua `smtplib` (stdlib, không thêm dependency) trong Celery task (retry, idempotent theo notification id); cấu hình `SMTP_*` qua ConfigService; **container `axllent/mailpit` cho dev** trong `docker-compose.yml` (hạ tầng mới — được chấp thuận bởi DEC này). Nội dung email không chứa dữ liệu mức 3–4; Briefing qua email là bản tóm tắt + link. Zalo/Slack/Teams (C7) vẫn P1 (B6). | 02, 06, 07, 10 | resolved (human, 2026-10-23) |
| R-DEC-21 | **`tenant_id` trong event envelope + tenant context** (bổ sung R-DEC-13): envelope event (10 §9.1) thêm `tenant_id`; contextvar `current_tenant` set từ JWT (request) hoặc envelope (consumer Celery); repository **fail closed** khi thiếu tenant; job beat chạy lặp theo từng tenant hoạt động. | 05 §7, 07, 10 §9.1 | resolved (human, 2026-10-23) |
| R-DEC-22 | **STT P0:** giọng nói nhập liệu ngắn (C2) gắn classification **Internal** → STT cloud qua ModelGateway (`task=stt`), giới hạn thời lượng/kích thước, không lưu audio thô sau STT, PII filter áp lên văn bản kết quả. **Ghi âm cuộc họp bị chặn ở P0**; UC-02 nhận transcript dạng **văn bản** hoặc **ảnh biên bản** (C3/C4). STT local (whisper) = backlog, cần DEC dependency. | 04 §2, 06, 07, 10 | resolved (human, 2026-10-23) |
| R-DEC-23 | **Seed v3 thay toàn bộ seed v2.1 ngay ở M1.1** theo `08` (Công ty ABC ~150 NV, 7 phòng ban, dữ liệu UC P0); số liệu tính bằng script, idempotent, `demo_reset.sh` chạy được; entity mới seed bổ sung ở phase tạo ra nó. Seed product/risk giữ nhưng gắn vào ABC. **DEC-230 (bố cục demo F🟢 C🟢 U🟡 O🟡 S🔴) và DEC-231 "≥10 alerts" superseded** bởi số liệu 08. | 08, tests | resolved (human, 2026-10-23) |
| R-DEC-24 | **D01 Organization giữ ở schema `hr`** (cùng Department/Team/Position/Employee hiện có) — thêm `Organization`, không di chuyển bảng; 05 §5 sửa ánh xạ "org → `hr`; admin → `platform`+`auth`". | 05 §5, 07 §1.1 | resolved (human, 2026-10-23) |
| R-DEC-25 | **FE đổi route sang IA v3** (06 §3.1): `/home`, `/ask`, `/goals`, `/work`, `/meetings`, `/data`, `/business`, `/knowledge`, `/admin`; route v2.1 **redirect 308** (bảng 06 §3.4); locale giữ cơ chế cookie `NEXT_LOCALE` (không thêm segment `[locale]`). **PWA P0 = installable, không offline queue** (manifest + service worker tự viết, chỉ cache app shell). **Mock FE** ở tầng BFF khi `API_MODE=mock` (env server). | 06, e2e | resolved (human, 2026-10-23) |
| R-DEC-26 | **Định nghĩa "đạt MVP" của đợt code = code-complete + đo được:** kịch bản CEO 7 bước + UC-01/02/03/04/06/07 pass E2E (AI fixture); cổng G1–G4 có instrumentation + trang đo. Ngưỡng G1–G4 thật (4 tuần dùng thật) xác nhận ở **giai đoạn thí điểm**, ngoài đợt code (OQ-09-04). | 09 §2.2, 14 | resolved (human, 2026-10-23) |
| R-DEC-27 | **Quyền mức 4 (lương) & trưởng phòng ban demo** (đóng OQ-09-05): trưởng **Nhân sự = ROLE-DIR `scope_pillars={O}`** (khối O ↔ domain `hr`; giữ quy tắc M1.0: mức 4 chỉ CEO + DIR khối O). Trưởng **Vận hành & Dịch vụ = ROLE-MGR** phạm vi phòng ban ở MVP, vì `scope_pillars` rỗng nghĩa là toàn khối nên không biểu diễn được "DIR không thuộc khối F.O.C.U.S nào". Nâng thành DIR cần một cơ chế scope mới (DEC riêng, backlog). Sửa `08` §2.1 (human cho phép trong quyết định này). | 02, 08 §2.1, seed | resolved (human, 2026-10-23) |

## 3. Quyết định mở từ BRD §21.1 — CHỜ CEO (không blocking cho docs P0)

Các quyết định này thuộc về CEO/chủ sản phẩm; không chặn việc hoàn thiện tài liệu P0 (docs ghi mặc định tạm + đánh dấu "chờ CEO"). Khi CEO chốt → nâng thành DEC chính thức và cập nhật file liên quan.

| ID | Quyết định | Mặc định tạm trong docs | Ảnh hưởng |
|---|---|---|---|
| B1 | SaaS đa tenant vs nội bộ 1 DN (dài hạn) | Thiết kế có `tenant_id`, chạy 1 tenant MVP (R-DEC-07) | 05, 07, UC-07, giá |
| B2 | Khách hàng mục tiêu đầu (quy mô/ngành) | Doanh nghiệp vừa VN, đa phòng ban | ưu tiên domain |
| B3 | Chính sách AI cloud (dữ liệu tài chính/nhân sự qua cloud quốc tế?) | Classification-based routing: Confidential → local; Secret → không LLM | 02, 07, NFR-DATA |
| B4 | Vai trò với phần mềm kế toán (chỉ đọc MISA/Fast vs nhập gốc) | P0: nhập gốc + IDP; tích hợp đọc là P1 (D06) | D06, D15 |
| B5 | Ngưỡng tự động L3 mặc định (giá trị tối đa) | Tài liệu hóa là cấu hình; mặc định thận trọng, quyết định trọng yếu luôn human | 02, 07, 11.6 |
| B6 | Kênh chat chính (Zalo/Slack/Teams) | P0 không có; C7 là P1 | D05, C7 |
| B7 | Mô hình giá (nếu SaaS) | Ngoài phạm vi docs sản phẩm | — |

## 4. Nguyên tắc

- Mâu thuẫn `docs/` ↔ `_reference/` → ưu tiên `_reference/` (kế thừa DEC-144/145).
- Agent không tự cấp số DEC chính thức; `Q*`/`B*`/`R-DEC-*` là nhãn nội bộ nhánh cho tới khi human cấp DEC.
- Mọi ID dùng trong 00–14 phải tồn tại trong `TRACEABILITY-SKELETON.md`; thêm ID → cập nhật skeleton trước.
- Không triển khai P1/P2 chỉ vì có trong BRD — phải theo backlog (09) + decision.

## Version
- **Version:** 1.0.0 (current)
- **Last updated:** 2026-10-23
- **Maintainer:** @CyEyes
- **Change 1.0.0 (promote):** Promote tài liệu AI-EOS lên CHÍNH THỨC Aureon v3; di chuyển vào vị trí docs chuẩn; v2.1 archived (docs/_archive/v2.1/).
- **Change 1.2.0 (đề xuất — kế hoạch build v3, 2026-10-23):** Thêm §2ter R-DEC-15..27 (human chốt trong phiên lập kế hoạch): mở rộng ủy quyền docs sang 09/10/06/14 ở bước Spec lock, đóng băng product/risk, Calendar Google/MS thật per-user, nguồn mã lỗi = `core/errors.py`, quy ước T-6xx..9xx + nhánh mỗi phase, email + Mailpit, `tenant_id` trong envelope, STT cloud cho voice Internal, seed v3 thay seed v2.1 (DEC-230/231 superseded), Org ở `hr`, route IA v3 + PWA installable + mock BFF, định nghĩa đạt MVP.
- **Change 1.1.0 (code round — human ủy quyền, 2026-10-23):** Thêm §2bis Quyết định đợt code: R-DEC-12 (role enum v3 7 giá trị + ánh xạ 10→7, Phase 1), R-DEC-13 (`tenant_id` field-level, Phase 1), R-DEC-14 (ủy quyền agent cập nhật 05 + 13 cho field-level đợt code). Bắt đầu đợt code refactor nền v2.1 → model v3 theo phase (09).
- **Change 0.2.0:** Human chốt Q1–Q6 → R-DEC-05..10 `resolved` (P0 MVP first, Modular Monolith, single-tenant + `tenant_id`, 7 role + AI Agent, docs-first, ID theo BRD + ánh xạ `main`). Thêm R-DEC-11 (ủy quyền sửa file bảo vệ cho doc-loading AI-EOS). Chuyển B1–B7 (BRD §21.1) thành quyết định mở của CEO, không blocking docs P0.
- **Change 0.1.0:** Tạo 13 cho nhánh `ai-eos` — gom Q1–Q6 + B1–B7 + R-DEC-01..04.
