# Aureon — Audit sản phẩm READ-ONLY (CPO + senior full-stack)

> Ngày: 2026-11-05 · Nhánh `v3/m8-crm` @ `9cad717` · Stack `docker-compose.full.yml` đang chạy (10 service).
> Không sửa repo, không ghi DB, không POST/PATCH/DELETE vào service đang chạy. Không đọc `.env`, `keys/`, `secrets/`.
> Cách làm: route table lấy bằng introspection trong container API (328 route, khớp `app.openapi()` — chênh duy nhất là `{storage_key:path}`); FE call bằng AST TypeScript; `canAccess()` chạy thật trên ma trận `permission_matrix.py`; số liệu DB bằng SELECT aggregate qua transaction read-only.
> Giới hạn: không đăng nhập được (login là POST) → mọi kết luận "API trả 403/200" là **phân tích tĩnh guard + scope code**, không phải quan sát runtime. Ghi rõ UNVERIFIED ở §8.
> Script + JSON gốc: `/tmp/claude-1000/-home-vika-Aureon/2b13532a-4cf7-4113-90e3-1f149a3f8ac1/scratchpad/audit/`.

## 0. Kết luận điều hành

**Sản phẩm là demo chạy tốt trên dữ liệu seed, chưa phải hệ điều hành doanh nghiệp vận hành được.** Lời hứa MVP "CEO biết công ty đạt mục tiêu đến đâu, vì sao, giao việc ngay" đúng trong kịch bản seed ngày 20/10/2026, nhưng vòng lặp Capture → Decision → Action → Measurement **không đóng** với dữ liệu mới: đồng hồ nghiệp vụ bị đóng băng, nhiều nguồn KPI không có đường nhập, bán hàng không nối sang tài chính, và không có người bán hàng trong mô hình quyền.

| Thước đo | Kết quả |
|---|---|
| Route BE | 328 · FE dùng 215 (65,5%) · 113 không có FE (34 có lý do doc R-DEC-16; 79 không) |
| FE gọi route không tồn tại | **0** (sau khi giải 7 path động) — contract FE→BE sạch |
| BRD_Newfeature Must (94) | Xong 25 (26,6%) · Một phần 25 · Chặn R-DEC-176: 36 · Thiếu dù làm được ngay: 7 · UNVERIFIED 1 |
| KPI (34 METRIC) | 34/34 có giá trị từ bảng thật; **6 xung đột nghiêm trọng (K1–K6)**; 13 mã không có đường cập nhật qua UI (chỉ seed/API) |
| 16 mảng chức năng | 4 đạt · 10 một phần · 2 đóng băng theo quyết định (§3) |

### Phát hiện xếp theo tác động kinh doanh

| # | Mức | Phát hiện | Bằng chứng chính |
|---|---|---|---|
| F1 | **Critical** | Stack "production" chạy `DEMO_MODE=true`: ngày nghiệp vụ đóng băng 2026-10-20 trong khi hôm nay 2026-11-05. Dữ liệu mới không vào KPI; Daily Briefing không bao giờ sinh lại; quá hạn hóa đơn/task đứng yên | env container; `core/clock.py:11-15`; `ai/services/briefing_service.py:48-50,89-91`; DB `ai.briefings` max date 2026-10-20 |
| F2 | **Critical** | Hai đồng hồ song song: Sales, HR dùng ngày thật; Finance, Metric, Execution, Product dùng ngày đóng băng. Cùng một công ty, cùng lúc, kỳ khác nhau | `sales/services/analytics.py:80-81`, `hr/services/hr_service.py:83-85`, `hr/services/org_service.py:57`, `ai/services/acceptance_service.py:71` vs `core/clock.py` |
| F3 | **Critical** | Scope `◑r` (REV) và `◑d` (MGR) không được thực thi ở Finance + Sales: Reviewer đọc được toàn bộ doanh thu, chi phí, hóa đơn, deal; MGR bất kỳ phòng ban tạo/sửa doanh thu, ngân sách toàn công ty | §5.3 |
| F4 | **Critical** | Anonymous lấy được mật khẩu 10 tài khoản demo (kể cả admin, ceo) qua `POST /api/demo-credentials` khi `DEMO_MODE=true` + `DEMO_LOGIN_AUTOFILL=true`; web publish `0.0.0.0:3000`. Không test bằng POST (đúng phạm vi) | `lib/demo-credentials.ts:22-34`, `app/api/demo-credentials/route.ts`, env web, `docker ps`; middleware không match route này |
| F5 | **Critical** | Cùng mã `METRIC-FIN-01` có 2 công thức: Store = doanh thu ÷ chỉ tiêu (86,4% YELLOW); `/finance/dashboard` = tăng trưởng YoY, status cứng `ok` | `sales/services/metric_provider.py:54-57` vs `finance/services/analytics_service.py:237-238` |
| F6 | **Critical** | Số giả trên trang thật: Home Department `OKR 0/0` luôn; Home Employee `0 KPI, 0 KR, tải 0%`, check-in chờ rỗng — hard-code ở BE | `dashboard/services/reporting_service.py:104,111-113,142-144`; `features/home/EmployeeView.tsx:26-27` |
| F7 | **Critical** | Deal thắng không tạo gì ở tài chính: không invoice/revenue/contract; không consumer `sales.deal_closed_won` ngoài recompute. Doanh thu CRM và doanh thu tài chính là 2 vũ trụ (T9: 8,7 tỷ vs 25,5 tỷ) | `workers/consumers.py`, `platform/events/consumers.py:26`, `finance/events/consumers.py` (không có), DB §4.3 |
| F8 | **High** | Funnel sai trên dữ liệu thật: 4→3→3→5→10 cho chuyển đổi 166,7% và 200%, rơi rụng **âm** −66,7%, −100% | `features/crm/crm.ts:32-41`; DB `sales.deals` |
| F9 | **High** | Runway 2 giá trị trên cùng trang `/business/finance`: 5,3 tháng (dựa tiền mặt) vs "—" (what-if dựa P&L, burn = 0) | `analytics_service.py:115-121,141-167`; DB §4.3 |
| F10 | **High** | 9/21 tool AI ghi không có `ACT-*` (7 đang quảng bá cho model, 2 `p1_frozen`): `TOOL-record_decision`, `upsert_deal`, `create_meeting`, `generate_report`, `request_approval`, `send_notification`, `submit_document`, `upsert_risk`, `create_mitigation` → luôn `NOT_FOUND`/lỗi tool | `tools.py` (script, chạy trong container); `ai/tools/registry.py:82`, `ai/services/action_service.py:79-81`, `ai/services/chat_service.py:327-338` |
| F11 | **High** | Decision Log (FR-DEC-01, P0) không có đường ghi: không UI, không ACT, tool hỏng; 3 quyết định đều từ seed; không xác nhận được outcome 30/60/90 | `POST /execution/decisions` không consumer; `features/knowledge/DecisionsPanel.tsx` không có mutation |
| F12 | **High** | D07 Strategy (P0 cơ bản) không có UI ghi: 20 route strategies/SO/initiatives/milestones không consumer; SEI trên Home CEO do đó chỉ phản ánh seed | `execution/routes/goals.py:114-349`; §4.4 |
| F13 | **High** | Không có người bán hàng: EMP không quyền sales; 2 MGR ở Vận hành/Hành chính; 30/30 deal thuộc `sales@` DIR; DIR không chọn được owner khác (chỉ "Tôi"); CEO không ghi deal → **không ai giao được deal cho người khác qua UI** | `features/records/RecordCrud.tsx:55,64`, `records-caps.ts`, `sales/services/scope.py:40-43`; DB |
| F14 | **High** | Giám đốc ngoài khối O (CFO, Sales, CPO) không giao việc được cho nhân viên của mình: `/org/tree` bị chặn → dropdown người nhận rỗng. Trực tiếp phá lời hứa "giao việc được ngay" | `features/work/WorkShell.tsx:17-19`, `BoardView.tsx:26,114`, `CreateTaskDialog.tsx:51-55` |
| F15 | **High** | Hub dẫn tới trang 403: EMP thấy thẻ Kinh doanh; REV thấy Tài chính, Kinh doanh, Nhân sự. CEO thấy nút Tạo/Sửa/Xóa khách hàng/deal/hợp đồng nhưng API luôn từ chối | §1.5 |
| F16 | **High** | Phê duyệt chỉ phủ 3 loại (`ai_action`, `task_reassign`, `hiring_plan`). Ngân sách, xóa dữ liệu quan trọng (2 người), đổi lương, đổi quyền theo 02 §7 không qua engine | `core/approval_hooks` đăng ký ở 3 nơi; `finance/services/budget_service.py:90-125` |
| F17 | **High** | Logout không thu hồi refresh token: `signOut` chỉ xóa cookie, `POST /auth/logout` không consumer | `components/shell/Header.tsx:66`; route `auth/routes/router.py:50` |
| F18 | **High** | Thiếu P0 bảo mật: MFA/SSO (FR-ADM-04), "Xem như người dùng" (FR-ADM-08), rate limit AI 20/phút, timeout 5s/tool. Còn mở R-DEC-168 (khóa JWT lộ một phần), lịch sử GitLeaks | grep rỗng; `core/errors.py:106` không nơi nào raise; `deliverables/M8-CRM-PLAN.md` §10 |
| F19 | **High** | Vòng đời tuyển dụng chết sau "Đã duyệt": form không có `filled`/`status`, không nối tạo nhân viên, nên METRIC-HR-04 không giảm được qua UI | `features/records/specs.ts:210-235`; `hr/schemas/__init__.py:194,200` |
| F20 | **High** | Chỉ tiêu Q4 = 20 tỷ nhưng tổng tháng T10–12 = 85 tỷ: `METRIC-CUS-01` 2,7× (vàng) đúng ra ~0,62× (đỏ) theo chỉ tiêu tháng | DB `sales.sales_targets`; seed |
| F21 | **Medium** | Freshness giả: `is_stale` so `computed_at`, mà seed chạy lại mỗi lần API khởi động → luôn "tươi" dù kỳ dữ liệu là T9 | `metric_query.py:94`; `docker-compose.full.yml:124`; `seed/__init__.py:100` |
| F22 | **Medium** | `/ask/activity` (feed "AI đã làm", hoàn tác 24h) không có link nào trỏ tới; `/home/pillar/*` chỉ tới được qua 1 link ở Workload | `links.py`; `app/(app)/work/workload/page.tsx:9` |
| F23 | **Medium** | Code chết + trùng: `DashboardView.tsx`, `PillarCard.tsx` không ai import; 2 view Pipeline, 2 view hóa đơn, 2 view nhân viên, 2 đường upload, 2 trang Finance | §3.13 |
| F24 | **Medium** | Ngưỡng KPI hard-code ngoài catalog: Finance + HR bỏ qua `THR_*`, vi phạm NFR-19 | `analytics_service.py:240-245`, `hr/services/metrics.py:27-29` |
| F25 | **Medium** | `hr.positions` = 0, 154/154 nhân viên `position_id` null: cơ cấu chức danh rỗng dù có màn hình quản trị | DB |
| F26 | **Low** | `/settings/integrations` không có rule + ngoài matcher middleware: `canAccess` nói cấm, thực tế mọi user vào được; REV/ADM vào rồi API 403 | `lib/permissions.ts`, `middleware.ts:37-42` |

## 1. Ma trận sinh bằng máy

Bảng đầy đủ ở Phụ lục A1 (route), A2 (page → API), A3 (page × tài khoản). Dưới đây là kết quả suy ra.

### 1.1. FE gọi route không tồn tại — **0**

213 lời gọi trực tiếp + 11 resource spec của `RecordCrud`. 7 path động được giải tay:

| Call | Giải |
|---|---|
| `features/admin/UsersView.tsx:54` | `/platform/users/{id}/deactivate\|reactivate` — có |
| `features/admin/ai/use-ai-admin.ts:29` | `/ai/tool-calls`, `/ai/model-calls` — có |
| `features/dashboard/use-pillar.ts:24` | `/{finance,hr,execution,sales,product,risk}/dashboard` — có |
| `features/finance/LineageDialog.tsx:44` | `/finance/revenues\|expenses\|budgets/status` — có |
| `features/records/RecordCrud.tsx:246,318,332` | `{spec.path}/{id}` + action `pay/stage/submit/approve` — có |

### 1.2. Route BE không có FE (113/328)

| Nhóm | Số | Route | Lý do doc | Đánh giá |
|---|---:|---|---|---|
| Product | 21 | catalog, feature, roadmap, release, metrics | R-DEC-16 đóng băng | Chấp nhận; nhưng 8 KPI + NPS dựa vào đây (§4.4) |
| Risk | 13 | risks, assessments, mitigations, scenarios | R-DEC-16 | Chấp nhận có rủi ro: **4 rủi ro `proposed` không ai xử lý được**, consumer vẫn sinh thêm |
| Strategy | 20 | `/goals/strategies*`, `strategic-objectives*`, `initiatives*`, milestones | **Không** — D07 P0 | **Gap P0** |
| Meeting/Decision CRUD | 7 | `POST/GET/PATCH/DELETE /execution/meetings/{id}`, `POST/GET/PATCH /execution/decisions` | **Không** | **Gap P0** |
| Finance forecast | 6 | `/finance/forecasts*`, `/finance/cash-flow-forecast*` | Không | FIN-07 thành seed-only |
| HR | 6 | `/hr/employees/{id}`, salary-history, `/hr/hiring-plans/{id}`, `/hr/workload` | Không | Không có hồ sơ nhân viên chi tiết, không có UI lương |
| Org | 7 | detail GET, `DELETE organizations/positions`, `PATCH teams`, `PATCH assignments` | Không | Không sửa được team đã tạo |
| Reporting | 2 | `GET/PUT /reporting/preferences/executive-tiles` | Không | CEO không tùy chỉnh được ô |
| AI | 4 | `POST /ai/chat`, `insights/{id}/dismiss`, `actions/{id}`, `GET /ai/briefings` | Sync dùng test | Không đóng được insight, không xem lịch sử briefing |
| Auth | 3 | `logout`, `me`, `GET /platform/users/{id}` | Không | `logout` là lỗi thật (F17) |
| Platform | 3 | dead-letters, OAuth callback | Callback = redirect ngoài, hợp lệ | Không có UI DLQ cho vận hành |
| Khác | 21 | detail GET finance/sales/kpis/objectives/calendar, `DELETE /work/tasks/{id}`, `PATCH/DELETE /work/projects/{id}`, `POST /dashboard/alerts/{id}/dismiss`, `/health`, review `reassign`/`merge`, `extraction` | Nhiều GET detail vô hại | `DELETE task`, reassign review là thiếu chức năng |

### 1.3. Trang không tới được từ nav

| Trang | Tình trạng | Mức |
|---|---|---|
| `/ask/activity` | 0 link trong FE lẫn BE | **Medium** — feed hoàn tác L3 bị mồ côi |
| `/home/pillar/[slug]` (5 trụ + `FinanceDrillView`) | Chỉ từ 1 link `metricHref` ở `/work/workload` rồi đi tab; 2 chỗ link còn lại nằm trong code chết | Medium |
| `/admin/acceptance` | CFO/Sales/CPO có quyền trang nhưng `/admin` bị chặn | Low |
| `/knowledge/[tab]` | Chỉ từ notification (đúng thiết kế R-DEC-137) | OK |
| `/home/metrics/[code]` | Từ `AlertsList` + notification | OK |
| `/settings/integrations` | Chỉ từ `/meetings/calendar`, ngoài rule route | Low |

Dead code: `features/dashboard/DashboardView.tsx`, `features/dashboard/PillarCard.tsx` (không file nào import).

### 1.4. Nav/hub dẫn tới 403 — đã lọc false-positive bằng đọc code

Bộ dự đoán tĩnh cho ra nhiều cảnh báo do import closure; các query bị gate `enabled:`/`visibleKnowledgeTabs`/`DataCaptureAdmin` đã loại. Còn lại:

| Vai trò | Đường đi | Kết quả | Nguyên nhân |
|---|---|---|---|
| EMP | Business → thẻ Kinh doanh → `/business/sales` | Cả 3 widget 403 (`sales:query`, `sales:read` thiếu) | `/business/sales` không có rule riêng, rơi vào rule `/business` `anyOf hr:read` (`lib/permissions.ts:36`) |
| REV | Business → Tài chính | 3 widget 403 (`finance:query`) | `/business/finance` chỉ đòi `finance:read` |
| REV | Business → Kinh doanh | 403 (`sales:query`) | như trên |
| REV | Business → Nhân sự (Employees, HR records) | 403 `FORBIDDEN_SCOPE` | `hr/services/scope.py:26` |
| MGR | Home Department → bấm ô KPI | Panel "không có quyền" | Ô lấy qua `execution:read`, drill-down cần `dashboard:read` (MGR không có) |
| MGR/EMP/REV/ADM | URL `/home/alerts`, `/home/metrics/*` | Trang mở, widget 403 | `dashboard:read` thiếu; rule `/home` cho mọi role. Không có link nav, ngoại trừ `/home/metrics` qua notification chỉ gửi CEO/DIR |
| EMP | `/work` → Đề nghị chuyển giao | `/org/tree` 403 rồi fallback **ô nhập ID tay** | `ReassignDialog.tsx:27` gọi không gate; R-DEC-169 #1 |
| CEO | Business → Sales records → Tạo/Sửa/Xóa client, deal, contract | API `FORBIDDEN_SCOPE` sau khi điền form | `records-caps.ts` chỉ xét `canDomain`; `sales/services/scope.py:40-43`. M8 chỉ xử lý `canMove` ở Kanban |
| MGR | Sales records → Sửa client / Tạo target | API `FORBIDDEN_SCOPE` | `require_full_writer`, `require_target_writer` |
| REV/ADM | `/settings/integrations` | API `execution:write` 403 khi kết nối | không có rule route |

### 1.5. Chức năng chỉ có một phía

| Loại | Mục |
|---|---|
| **Chỉ BE** | Strategy/Initiative, Meeting/Decision CRUD, Forecast, 13-week cash flow, Salary history, Risk, Product, Executive tile preferences, Insight dismiss, DLQ replay, Review reassign/merge, AI briefing history |
| **Chỉ UI (tính toán client)** | Funnel conversion, Forecast "expected", tổng hợp Account 360, số ngày ở stage, rủi ro deal (`crm.ts`, `ClientDetailView.tsx:32-33`, `DealDetailView.tsx:71`) — trái ghi chú đầu file "every figure comes from the API" |
| **UI vô hiệu** | Ghi âm C2: `LIVE_STT_AVAILABLE=false` (`VoiceCapture.tsx:27`, R-DEC-166) — chấp nhận có quyết định |
| **Khai báo mà không chạy** | 9 tool AI ghi không có ACT; `MODEL_EMBED` trống → tìm kiếm tri thức chỉ `ILIKE` (`idp/services/knowledge_search.py:47,59-62`) |

## 2. Mock và dữ liệu giả

### 2.1. MSW / mock có lên production không

| Câu hỏi | Kết quả | Bằng chứng |
|---|---|---|
| Có MSW? | **Không.** `src/mocks` là router in-process, không có service worker | `app/api/backend/[...path]/route.ts:9-11` |
| Nằm trong client bundle? | **Không.** 0 file `.next/static` chứa `__mock/reset`, `handleMock`, `seed_snapshot`, `mockAuthorize` | grep trong container web |
| Nằm trong server bundle? | **Có**, import tĩnh: `.next/server/app/api/backend/[...path]/route.js` chứa `handleMock` | grep; rủi ro thấp nhưng tăng diện tấn công và kéo `seed_snapshot.json` (4.510 dòng) vào image |
| Bật được ở production? | **Không.** `API_MODE=mock` + `NODE_ENV=production` → throw | `lib/server-env.ts:45-51`; container: `NODE_ENV=production`, `API_MODE` trống |
| Fallback sang dữ liệu giả khi lỗi? | **Không có ở FE.** Lỗi hiện `QueryError`/thông báo. Nhưng BE có "fallback" khác: `AI_DEMO_REPLAY=true` trả câu trả lời ghi sẵn nếu khớp từ khóa (số vẫn lấy từ tool) | `ai/services/demo_replay.py:3-6,47`; env API |

### 2.2. Số cứng / placeholder trên trang thật

| Vị trí | Hiển thị | Mức |
|---|---|---|
| `reporting_service.py:104` | Home Department "OKR rủi ro 0/0" luôn | Critical |
| `reporting_service.py:142-144` | Home Employee "0 KPI, 0 KR", tải 0% (`?? 0` ở `EmployeeView.tsx:27`), không bao giờ có check-in chờ | Critical |
| `reporting_service.py:111-113` | `due_tasks.overdue` = số ô heatmap >110%, `today=0`, `this_week` = số ô — sai nghĩa (FE chưa render; AI/briefing có thể đọc) | High |
| `hr/services/dashboard_service.py:104` | `revenue_per_employee=None` dù METRIC-HR-01 có giá trị | Medium |
| `features/dashboard/pillars.ts:84`, `apps/web/Dockerfile:18-19` | Kỳ mặc định baked `2026-09`, ngày tham chiếu baked `2026-10-20` | Critical (F1) |
| `seed/finance_data.py:75,107` | 8 hóa đơn 2025 hạn `2027-12-31`, tổng ~40 tỷ, cố ý để luôn `sent`, tô DSO/AR | High |
| `app/(app)/home/page.tsx:21` | `ComingSoon` — chỉ khi role không có cả `dashboard:read` lẫn `execution:read` (không xảy ra với role hiện tại) | Low |
| `features/admin/onboarding/ImportStep.tsx:21` | Template `DOC-07-kpi-okr-q4-2026.xlsx` cố định năm | Low |
| i18n "Sắp có" | Chỉ 1 key, chỉ dùng ở dòng `ComingSoon` trên | OK |

Grep `TODO|FIXME|lorem|dummy` trong `src` ngoài mocks: 0 kết quả thực chất. **M5 đã xóa nút "sắp có" KPI/OKR — xác nhận đúng.**

## 3. Phán quyết từng module

Ký hiệu: ✅ hoàn tất đầu-cuối · ◐ một phần · ⛔ đứt · ❄ đóng băng theo quyết định. "Đầu-cuối" = đọc code qua `create → approve → effect → dashboard`, không chạy thật.

| Module | Phán quyết | Luồng cốt lõi | Điểm đứt |
|---|---|---|---|
| CEO Dashboard | ◐ | Home → tile → drill-down → lineage ✅; Approvals ✅; Alerts ✅ | F1, F5, F21; Insight rỗng; Briefing đóng băng |
| HR | ◐ | Employee CRUD ✅; Hiring trình → duyệt ✅ → tuyển ⛔ | Không hồ sơ, lương, nghỉ phép, đánh giá |
| Finance | ◐ | Hóa đơn/chi/thu/ngân sách CRUD ✅ → metric ◐ | CFO chỉ chọn được phòng mình; thanh toán không đổi tiền mặt |
| Sales/CRM | ◐ | Client → Deal → Stage ✅ → Thắng → Finance ⛔ | F7, F8, F13; thiếu Lead/Contact/Activity |
| Product | ❄ | Chỉ API + AI read (frozen) | NPS CEO lấy từ đây |
| Risk | ❄ | Event → `proposed` → triage ⛔ | 4 rủi ro treo, KPI đỏ không xử lý được |
| Approval Engine | ◐ | 3 loại ✅ | Thiếu ngân sách, xóa 2 người, lương, quyền |
| IDP/AI Document | ✅ | Upload → OCR → phân loại → trích xuất → review → commit → undo → metric | DOC-03 vượt token; SOP #5 không có loại riêng |
| Organization | ✅ (khuyết) | Dept/Team/Assignment/Tree ✅ | Không sửa team; `positions` rỗng |
| Reporting | ◐ | 3 báo cáo CSV/XLSX ✅ | Chỉ DIR/CEO; không PDF; Department/Employee số giả |
| RBAC/Role | ◐ | Gán vai trò ✅, ma trận chỉ đọc (R-DEC-174) ✅ | F3, F18 |
| Work | ✅ | Task/Project/Board/Workload/Reassign ✅ | Không sửa/xóa dự án, không xóa task; F14 |
| Goals | ◐ | KPI/OKR CRUD + check-in + SEI ✅ | Strategy/Initiative không UI (F12) |
| Knowledge | ◐ | Decision đọc, tài liệu tìm, báo cáo tải ✅ | Không ghi quyết định; tìm kiếm chỉ ILIKE |
| Calendar | ✅ | Sự kiện CRUD + Google/Outlook OAuth | Sync thật UNVERIFIED; DB 0 sự kiện |
| Meeting | ◐ | NL/biên bản → action item → task ✅ | Không tạo cuộc họp trực tiếp; không ghi quyết định |

### 3.1. CEO Dashboard

Tồn tại: `app/(app)/home/page.tsx` → `HomeView` → `ExecutiveView` gọi `/reporting/dashboards/executive` (`reporting_service.py:46-72`): 4 ô mặc định `FIN-01, FIN-03, STR-01, OPS-01` (`preference_service.py:20-21`), SEI, quyết định chờ, cảnh báo mở, AI đã làm, Briefing, Insight.

Nguồn số: **thật**, từ `platform.metric_values`. Giá trị hiện tại: FIN-01 86,4% YELLOW (T9), FIN-03 5,3 tháng RED, OPS-01 85% GREEN (T10). 13 alert mở (3 critical, 10 warning), chỉ gồm alert từ seed.

Đứt:
- `ai.insights` = 0 dòng; `generate_for_pillar` không có caller nào, chỉ sinh khi có event KPI/OKR (`ai/events/consumers.py:23-30`) → khối Insight 9 phần thường trống.
- Briefing: một dòng cho mỗi `(recipient, day)`, ngày = `business_today()` cố định → job hằng ngày vẫn chạy nhưng thoát sớm (`briefing_service.py:89-91`). 5 dòng, tất cả `2026-10-20`.
- "Rủi ro mở" thực chất là số alert (R-DEC-165), nhãn dễ hiểu nhầm.

### 3.2. HR

Có: `/business/hr/employees` (list tối giản), `/business/hr/records` (employees + hiring plans), `/hr/dashboard` chỉ qua trụ O. 154 nhân viên, 442 dòng lịch sử lương.

Trace tuyển dụng: `POST /hr/hiring-plans` → `submit` (`hiring_service.py:238`) → `RULE-hiring_plan` → `/work/approvals` → `_hook_approved` → `apply_decision` (`:298`) đặt `approved` → **hết**. Sau đó không có nút chuyển `in_progress`, nhập `filled`, không tạo nhân viên từ kế hoạch (`features/records/specs.ts:210-224` không có `filled`, `status`; API có ở `hr/schemas/__init__.py:194,200`). Job `detect_delayed` (`hiring_service.py:323`) vẫn đếm là trễ → METRIC-HR-04 không thể xanh qua UI.

Thiết kế duyệt: creator ≠ approver (`hiring_service.py:310`), `hr:write` chỉ DIR, CEO không có → hồ sơ do HR-DIR tạo luôn phải lên CEO. Nhánh "HR-DIR duyệt" trong R-DEC-173 chỉ xảy ra nếu có DIR khối O thứ hai, hiện không có.

Vắng: `hr.leaves`, `hr.employee_skills` có bảng nhưng 0 route; không trang chi tiết nhân viên; `salary-history` chỉ API; dashboard HR ngoài Home không có đường vào trực tiếp.

### 3.3. Finance

Có: `/business/finance` (`FinanceLiteView`), `/business/finance/invoices` (`InvoicesView`), `/business/finance/records` (5 tab), `/home/pillar/finance` (`FinanceDrillView` + `LineageDialog`).

Trace hóa đơn: `POST /finance/invoices` (`invoice_service.py:200` phát `finance.invoice_created`) → `POST .../pay` (`:284`) phát `finance.invoice_paid` → consumer recompute `{finance, sales}` + cash forecast ✅. Nhưng `pay` **không** tạo revenue, không đổi `cash_positions` — doanh thu, tiền mặt, công nợ là 3 sổ nhập tay rời.

Trace revenue/expense: `create_revenue` (`finance_service.py:128`) không phát event; `create_expense` chỉ gọi `on_expense_changed`. KPI chỉ cập nhật lúc 01:00 (`worker.py:97-98`) hoặc restart.

Đứt:
- CFO `canReadDepartments=false` (`records-caps.ts`: `hrReader` đòi khối O) → ô phòng ban chỉ có "Phòng tôi": **CFO không lập được ngân sách/chi phí cho phòng khác** (M8 §10 #6 ghi Backlog, thực tế là High).
- Forecast + 13-week cash flow: API có, UI không; `TOOL-get_cash_flow_forecast` đọc được.
- Không có luồng duyệt ngân sách (02 §7: CEO/CFO).

### 3.4. Sales/CRM

Trace: `POST /sales/clients` → `POST /sales/deals` → `POST /sales/deals/{id}/stage` (`sales_service.py:375-403`) → `closed_won` đặt probability 100 + `closed_at` → `sales.deal_closed_won` → chỉ `platform.on_sales_event` recompute (`platform/events/consumers.py:26`).

| Bước BRD | Thực tế |
|---|---|
| Close Won → cập nhật doanh thu (UAT-010) | ⛔ Không tạo revenue/invoice/contract |
| `closed_at = now_utc()` | Ngày thật 11/2026; metric chỉ xét kỳ `2026-09` → deal mới **không vào** METRIC-CUS-02/06 (F1) |
| Bằng chứng khi thắng (BR-010) | ⛔ Không có |
| Next Action bắt buộc (BR-009) | ⛔ Chờ R-DEC-176 |
| Lịch sử stage | ◐ `changed_by=None` cứng (`sales_service.py:432`) dù BRD đòi người đổi |
| Tên người phụ trách | ◐ Hiện 8 ký tự UUID (`PipelineBoard.tsx:69`, `SalesInsights.tsx:85`, `DealDetailView.tsx:36`) |

Phân tích client: Kanban chỉ lấy 100 deal (`use-crm.ts:30`, `crm.first100`), tổng cột lấy từ API → cột có thể lệch số thẻ.

### 3.5. Product & 3.6. Risk

R-DEC-16 đóng băng hợp lệ, nhưng còn hệ quả chưa quyết:
- `METRIC-CUS-05` NPS thuộc nhóm CUS (không frozen) lại tính từ `product.product_metrics`, kỳ cuối 2026-09, không đường nhập (`product/services/metrics.py:99`).
- Consumer Risk vẫn chạy: `risk/events/consumers.py:16-46` sinh rủi ro `proposed` (DB: 4), không màn hình triage. METRIC-RSK-01/02 RED trên store; `/home/pillar/strategy` hiển thị nếu vào được.
- CEO có `risk:approve` nhưng không có chỗ dùng.

### 3.7. Approval Engine

`platform/services/approval_service.py`: rule-based 2 bước, SLA, audit, hook cùng transaction, ràng buộc DB `distinct_approvers`. Chất lượng kỹ thuật tốt. Hook đăng ký: `ai_action` (`action_service.py:325`), `task_reassign` (`task_service.py:564`), `hiring_plan` (`hiring_service.py:367`). `platform.approval_rules` chỉ có 1 dòng (khác tạo lazy) và 1 yêu cầu PENDING.

Thiếu so với 02 §7: phê duyệt ngân sách, ghi trọng yếu ngoài IDP (form records ghi thẳng tiền), đổi lương, xóa dữ liệu quan trọng 2 người, đổi policy AI. Hai đường cho cùng một việc: EP-86 và `/workflow/approval-requests`.

Kế hoạch tuyển dụng `submitted` trước M8 vẫn không có yêu cầu duyệt (M8 §8 #13) → không hiện ở hộp thư CEO.

### 3.8. IDP/AI Document

Mạnh nhất hệ thống. Trace: `POST /idp/documents` → `workers/idp_pipeline` (malware, MIME, OCR paddle, classify, extract, validate) → `/data/review/[id]` → commit qua Action Registry (`commit_service.py:206` phát `idp.document_committed`) → `platform.on_idp_event` recompute 7 module + `on_capture_share` → undo 7 ngày (`undo_service.py:182`).

| Hạng mục | Thực tế |
|---|---|
| Kênh P0 | C1 form, C2 NL (không giọng nói), C3 upload, C4 camera, C5 import ✅ |
| Doc type P0 (#1–6) | 6 loại có, nhưng #5 SOP dùng chung `OTHER`, không có ACT Knowledge. Thêm #7 INVOICE (P1) |
| Nhập liệu thật | DB: 2 tài liệu (1 `NEEDS_REVIEW`, 1 `SUCCEEDED`) → chưa có khối lượng thực |
| Lỗi đã biết | DOC-03 FAILED do trần 2048 token (STATE M6) |

Trùng: `features/idp` (review) và `features/capture` (inbox, import) phụ thuộc lẫn nhau, không phải bản sao, nhưng có 2 đường upload: `UploadButton` (`idp/ReviewQueueView.tsx:50`) và `DropZone`.

### 3.9. Organization

`/admin/org`, `/admin/positions`, `/org/tree`, `HR_ROSTER` import, onboarding wizard. 11 team, 156 assignment. `hr.positions` = 0 và `position_id` null toàn bộ → cột "chức danh" dựa vào dữ liệu khác; `PATCH /org/teams/{id}` không consumer → không sửa được team.

### 3.10. Reporting

3 báo cáo cố định (`report_service.py:30-34`): `executive-summary`, `decisions`, `metrics-health`, CSV + XLSX. Không PDF (có ghi rõ). `dashboard:read` nên MGR/EMP không có tab Báo cáo. Không có báo cáo tuần/tháng tự động, không định kỳ gửi.

### 3.11. RBAC/Role management

- Ma trận chỉ đọc đúng R-DEC-174. `/admin/users` gán vai trò, khối, kích hoạt ✅.
- `ROLE_SCOPES` chỉ dùng cho seed/snapshot, **không tham gia enforce** (`grep`: `auth_seed.py`, `snapshot.py`, `user_admin_service.py`) → scope được code tay từng module, nguyên nhân gốc F3.
- `pillar_allows()` luôn `True` (`core/permissions.py`), cô lập khối nằm ở từng service.
- Tham chiếu tài liệu đã lệch: code ghi `02 §5.3`, `02 §6.2`, nhưng 02 hiện tại §5 là phân loại dữ liệu, §6 là Autonomy; ma trận chi tiết không còn trong 02.

### 3.12. Work / Goals / Knowledge / Calendar / Meeting

| Mảng | Có | Đứt |
|---|---|---|
| Work | Task của tôi, board, dự án, milestone, phụ thuộc, workload heatmap, duyệt chuyển giao, e-mail giao việc | `PATCH/DELETE /work/projects/{id}`, `DELETE /work/tasks/{id}`, `GET milestones` không consumer |
| Goals | Cây alignment, KPI/Objective/KR editor, check-in, đo lường | Tạo Strategy, SO, Initiative chỉ qua API. Owner KPI chỉ CEO/ADM chọn được (M5 §5 #4) |
| Knowledge | Decision Log đọc, tìm tài liệu, xuất báo cáo | `MODEL_EMBED` trống → không RAG; không có màn SOP |
| Calendar | Lịch tuần/tháng, sự kiện, OAuth Google/Outlook | Sync thật chưa kiểm; `execution.calendar_events` = 0 |
| Meeting | Danh sách, dán transcript → NL preview → commit action item → task | Tạo cuộc họp bằng tay ⛔; DB 1 cuộc họp, 6 action item |

### 3.13. Bản trùng cần gom

| Cặp | Hiện trạng | Đề xuất |
|---|---|---|
| `/home` (`features/home`) vs `features/dashboard/DashboardView` | DashboardView chết | Xóa DashboardView, PillarCard |
| `/home` vs `/home/pillar/*` vs `/business/finance` | 3 lớp, `FinanceDrillView` tốt hơn `FinanceLiteView` nhưng khó tới | Gộp vào `/business/finance` |
| `features/sales/SalesPipelineView` vs `features/crm/PipelineBoard` | Cả hai hiện cột stage; `/business/sales` ghép view cũ + Insights | Giữ summary, bỏ cột trùng |
| `InvoicesView` vs `records?tab=invoices` | Hai danh sách hóa đơn, chỉ records có thanh toán | Gộp |
| `EmployeesView` vs `records?tab=employees` | Hai danh sách nhân viên | Gộp |
| `/dashboard/*` vs `/reporting/*` | BE song song, v2.1 + v3 | Giữ cả (khác trách nhiệm), ghi rõ |
| EP-86 vs `/workflow/*` | 2 đường duyệt | Chỉ dùng engine |
| `features/idp` vs `features/capture` | Đặt tên lệch, không trùng logic | Đổi tên khi rảnh |
| `features/briefing` | Banner trong Executive, không trùng | Giữ |

## 4. Toàn vẹn KPI

### 4.1. Trạng thái dữ liệu

| Hạng mục | Giá trị |
|---|---|
| Giờ hệ thống | 2026-11-05 08:30 UTC |
| `business_today()` | **2026-10-20** (`DEMO_MODE=true`) |
| Kỳ current trong store | `2026-09`, `2026-10`, `2026-Q3`, `2026-Q4` |
| `computed_at` mới nhất | 2026-11-05 08:14 (lúc API restart chạy seed, `docker-compose.full.yml:124`) |
| Tổng `metric_values` | 328 |
| Dữ liệu nghiệp vụ sau 20/10 | Revenue/expense kỳ cuối 2026-10; audit log từ 04/11 chỉ có login, seed, alert — **0 thao tác nghiệp vụ người dùng** |
| Khoảng trống | Dashboard hiển thị T9 trong khi hôm nay đã qua giữa T11 |

Mọi số tile có dòng dữ liệu thật trong bảng domain (đã đếm: 154 NV, 30 deal, 56 hóa đơn, 103 task, 12 KPI, 6 Objective). **Nhưng bộ dữ liệu là seed**: chưa có bằng chứng số nào phát sinh từ vận hành.

### 4.2. Danh mục 34 METRIC

Provider: `finance/services/metrics.py`, `sales/services/metric_provider.py`, `hr/services/metric_provider.py`, `execution/services/metrics.py`, `product/services/metrics.py`, `risk/services/metrics.py` + `analytics.py`, `platform/services/metrics.py`, `capture_metrics.py`. Catalog `platform/services/catalog.py` (docstring ghi "32", thực tế 34).

| Metric | Tính ở | Kỳ hiện tại | Giá trị | Đường cập nhật sống | Bản tính thứ hai |
|---|---|---|---|---|---|
| FIN-01 | sales provider:54 | 2026-09 | 86,4 Y | Revenue UI + target UI; không event khi CRUD | **`analytics_service:237` khác công thức** |
| FIN-02 | finance:48 | 2026-Q3 | G | Revenue/expense UI | `:239` status cứng `ok` |
| FIN-03 | finance:74 | 2026-09 | 5,3 R | Cash UI / doc #6 | `:240` ngưỡng cứng; what-if khác cơ sở |
| FIN-04 | finance:53 | 2026-Q3 | G | Invoice UI; có 40 tỷ AR padding seed | `:242` status cứng |
| FIN-05 | finance:88 | 2026-10 | G | Job overdue (ngày đóng băng) | `:243` ngưỡng cứng |
| FIN-06 | finance:91 | 2026-Q3 | 8,0 Y | Budget + expense UI | `:244` trung bình vs worst |
| FIN-07 | finance:108 | 2026-10 | G | **Forecast chỉ API → seed-only** | `:245` |
| OPS-01/02/03 | execution | 2026-10 | G | Task/project UI | `execution/dashboard_service` dùng cùng hàm ✅ |
| HR-03 | execution | 2026-10 | Y | Task UI | `/hr/workload` cùng nguồn ✅ |
| STR-01 | execution | 2026-10 | G | KPI/KR UI | — |
| STR-02 SEI | execution | 2026-10 | G | **Initiative chỉ API → seed-only** | — |
| HR-01 | hr provider | 2026-09 | 2,0 tỷ/người | Revenue + roster | `/hr/dashboard` trả `None` |
| HR-02 | hr provider | 2026-09 | 4,2 G | Employee UI | Dashboard theo kỳ, cùng công thức |
| HR-04 | hr provider | 2026-10 | Y | Plan UI nhưng `filled` không nhập được | `hr/metrics.py:29` ngưỡng cứng |
| CUS-01 | sales provider | 2026-Q4 | 2,7 Y | Deal + target UI | `analytics.py` pipeline cùng công thức |
| CUS-02 | sales provider | 2026-09 | 100 G | Deal UI (nhưng kỳ đóng băng) | `/sales/dashboard` tháng thật → `null` |
| CUS-03 | sales provider | 2026-09 | 103,7 G | Revenue UI. Thực là tháng/tháng, không phải NRR | — |
| CUS-04 | sales provider | ROLLING_12M | G | Revenue UI | — |
| CUS-05 NPS | product | 2026-09 | 33,2 G | **Chỉ API → seed-only** | — |
| CUS-06 | sales provider | 2026-09 | G | Deal UI (kỳ đóng băng) | `/sales/dashboard` |
| PRD-01..05 | product | 2026-09 | G/Y | **Chỉ API → seed-only** | — |
| RSK-01..05 | risk | 2026-10 | R/Y | Consumer sinh `proposed`; **không UI** | — |
| DQ-01 | platform | 2026-10 | G | Sống theo commit IDP | — |
| DQ-02 | capture | 2026-10 | G | Sống theo commit IDP | — |

**13 mã không có đường cập nhật qua UI:** PRD-01..05, CUS-05, RSK-01..05, STR-02, FIN-07.

### 4.3. Công thức xung đột (đã tính lại từ DB)

| # | Xung đột | Số thực | Tác động | Mức |
|---|---|---|---|---|
| K1 | **FIN-01** store = revenue/target; `/finance/dashboard` = YoY growth, `ok` cứng | Store 86,4% YELLOW = 25,5/29,5 tỷ ✓. Dashboard mang cùng mã khác nghĩa, status `ok`. FE `statusOf("METRIC-FIN-01")` trong `FinanceDrillView` lấy status sai → thẻ Doanh thu xanh trong khi Home vàng | CEO thấy 2 màu cho cùng chỉ số | Critical |
| K2 | **Đạt chỉ tiêu** FIN-01 dùng revenue tài chính; `quota_attainment_pct` dùng deal thắng | T9: 86,4% vs 8,7/29,5 = **29,5%**. Câu hỏi 5.2-a của R-DEC-176 chưa chốt | AI (`TOOL-get_sales_dashboard`) có thể trả 29,5% | Critical |
| K3 | **Runway** store dựa cash delta: tháng 7–9 giảm 2,4 tỷ/tháng → 12,6/2,4 = 5,3. What-if dựa expense − revenue: 3 tháng đều lãi → burn 0 → `null` | Cùng trang `/business/finance`: 5,3 tháng và "—". Gốc: seed cash giảm trong khi P&L lãi 1,3 tỷ/tháng | CFO không tin được | High |
| K4 | **Funnel** chia số deal hiện tại giữa các stage (Method A), gồm cả Closed Won tích lũy | 4 → 3 → 3 → 5 → 10: 75%, 100%, **166,7%**, **200%**; rơi rụng −66,7%, −100% | Vô nghĩa trên dữ liệu thật; BRD còn đòi theo Lead | High |
| K5 | **CUS-01** chỉ tiêu Q4 20 tỷ vs tháng 27+28+30 = 85 tỷ | 53/20 = 2,65 → 2,7 (Y); theo tháng 0,62 (đáng R) | Sai kết luận pipeline | High |
| K6 | **Win rate kỳ**: CUS-02 kỳ 2026-09 = 100% (2/0), `/sales/dashboard` tháng 2026-11 = `null` | Strip `/business/sales` hiện "—" | Mất tin cậy; mẫu 2 deal không có cảnh báo | High |
| K7 | **FIN-06** store = phòng vượt nhiều nhất; dashboard = utilization tổng | Giá trị dashboard UNVERIFIED | Cùng thẻ khác nghĩa | Medium |
| K8 | **Ngưỡng** hard-code: `analytics_service.py:240-245`, `hr/services/metrics.py:27-29` | `THR_*` chỉ có hiệu lực ở store | Vi phạm NFR-19 | Medium |
| K9 | **`crm.ts` tính số ở client** (funnel, forecast `expected`) | Trái CORE-06 mà chính file trích dẫn | Không audit được | Medium |

### 4.4. Độ tươi và phụ thuộc seed

- `is_stale = now - computed_at > max_age` (`metric_query.py:94`): đo lúc **tính**, không phải tuổi dữ liệu. Vì seed recompute mỗi restart + 01:00 hằng đêm → cờ "cũ" gần như không bao giờ bật. BO-02 (≤24h tài chính, ≤1h task/sales) không đo được.
- Revenue/expense CRUD không phát event → trễ tới 01:00; Deal/task/invoice paid thì gần thời gian thực (nếu ngày nằm trong kỳ).
- Provider dùng `as_of = business_today()`; period = tháng đóng trước đó → khi đóng băng, mọi bản ghi tháng 11 nằm ngoài cửa sổ tính. **Đây là chặn số một của vòng lặp Measurement.**
- Seed-hack: 8 hóa đơn `2027-12-31` (AR), `Q4 target`, cash dốc xuống đều (5,3 tháng được dựng để ra RED).

## 5. Ma trận vai trò – công việc

### 5.1. 10 tài khoản ↔ 7 role

| Tài khoản | Role | Khối | Phòng ban |
|---|---|---|---|
| ceo | CEO | — | Ban Giám đốc |
| cfo / sales / hr / cpo | DIR | F / C / O / U | Tài chính / Kinh doanh / Nhân sự / Sản phẩm |
| manager / office | MGR | — | Vận hành / Hành chính |
| employee | EMP | — | Vận hành |
| reviewer | REV | — | Hành chính |
| admin | ADM | — | Sản phẩm |

Không có: Risk-DIR (S), MGR/EMP Kinh doanh, MGR/EMP Tài chính, MGR/EMP Nhân sự. **Mô hình vai trò có đủ tầng trên giấy, nhưng 3 khối nghiệp vụ chính chỉ có đúng một người là Giám đốc.**

### 5.2. Theo vai trò

| Vai trò | Công việc hằng ngày | Trang vào | Hoàn tất được | Thiếu / vướng |
|---|---|---|---|---|
| **CEO** | Xem sức khỏe, quyết, giao việc | `/home` Executive | Đọc mọi trụ, duyệt, tạo task/dự án/KPI, đặt target, hỏi AI | Không di chuyển deal (`crm-caps.ts:14`, đúng scope `t`); nút Tạo Sales vẫn hiện; không vào `/data/review` (rule có CEO, thiếu `idp:approve`) ; không vào `/admin/audit`; không duyệt ngân sách; Briefing cũ |
| **CFO** (DIR-F) | Thu chi, hóa đơn, ngân sách | `/home` | Invoice, expense, revenue, cash, thanh toán, review IDP | Không chọn phòng khác (F-3.3); không forecast UI; không giao việc (F14); OUT invoice phải gõ MST (R-DEC-172) |
| **Sales DIR** (DIR-C) | Pipeline, chỉ tiêu | `/home` | Client, Deal, Kanban, target, xếp hạng | Không Lead/Contact/Activity; owner chỉ "Tôi"; tên người là UUID; không giao việc; chỉ tiêu cá nhân chỉ cho mình |
| **Sales MGR** | Quản đội | — | **Không có tài khoản.** Quyền `sales:read/write d` hợp lệ nếu có | Không đặt target (`require_target_writer`), không sửa client |
| **Sales EMP** | Theo deal, gọi khách | — | **Không có quyền sales nào** (`permission_matrix.py:120-128`); thẻ Kinh doanh 403 | Toàn bộ CRM; R-DEC-176 câu h |
| **HR Director** (DIR-O) | Nhân sự, tuyển dụng, cơ cấu | `/home` | Employee CRUD, hiring, `/admin/org`, lương (qua API) | Không UI lương, nghỉ phép, đánh giá; plan chết sau duyệt; duyệt được plan của người khác nhưng không ai khác tạo được |
| **HR** (nhân viên HR) | Nhập hồ sơ | — | **Không có role**: EMP phòng Nhân sự chỉ thấy bản thân | Toàn bộ HR ops phụ thuộc 1 tài khoản |
| **Manager** | Giao việc team, check-in | `/home` Department | Board, assign, workload, duyệt chuyển giao, review IDP | OKR 0/0 giả; bấm ô KPI bị cấm; **quyền quá rộng**: `finance:write`, `sales:write`, `product:write`, `risk:write`; manager Vận hành thấy 0 deal |
| **Employee** | Làm task, cập nhật mục tiêu | `/home` Employee | Task, check-in, upload, hỏi AI | Số Home giả; không danh bạ (`/org/tree` 403, `/hr/employees` chỉ mình); chuyển giao phải gõ ID; thẻ Kinh doanh chết |
| **Reviewer** | Duyệt tài liệu | `/data` | Queue, review, commit, từ chối | **Đọc được toàn bộ finance + sales** (F3); 3 thẻ hub 403 |
| **Admin** | Cấu hình | `/admin` | User, gán role, audit, AI control, kill switch, capture config, onboarding | Không có DLQ UI, "Xem như người dùng", MFA; Home redirect về Admin |

### 5.3. Thực thi scope — kiểm code từng domain

| Quyền (scope) | Mong đợi | Thực tế | Bằng chứng |
|---|---|---|---|
| `finance:read ◑r` (REV) | Chỉ trong phiên review | **Đọc tất cả** revenue, expense, invoice, budget, cash | `finance/routes/router.py:86-88` `_: Reader`; `finance_service.py:104`; `list_expenses` chỉ lọc MGR |
| `sales:read ◑r` (REV) | Như trên | **Đọc tất cả** client, deal, contract, target | `sales/routes/router.py:81`, `sales_service.py:281`; route FE `/business/sales/records` mở cho REV (`permissions.ts:68`) |
| `finance:read ◑d` (MGR) | Phòng mình | Revenue, invoice, budget, cash **toàn công ty**; chỉ expense lọc | như trên |
| `finance:write ◑d` (MGR) | Phòng mình | Tạo revenue, invoice, cash, **ngân sách mọi phòng** | `finance_service.py:128`, `budget_service.py:90-125` |
| `hr:read ◑r/◑s/◑o` | Đúng | ✅ | `hr/services/scope.py` |
| `product:read ◑r`, `risk:read ◑r` | Đúng | ✅ | `product/services/scope.py:15-25`, `risk/services/scope.py:25` |
| `sales:read ◑d`, deal/contract | Đúng | ✅ | `sales_service.py:281,526` |
| `finance:query agg` (DIR ngoài F) | Tổng hợp | `/finance/dashboard` trả đủ net profit, runway, burn; trong khi `metric_visible` chỉ cho FIN-01 | `finance/routes/router.py:383`; `dashboard/services/dashboard_service.py:64-69` |

Tất cả là phân tích tĩnh; M8 §6 kiểm "REV/EMP không có route CRM" chỉ ở 3 route mới, chưa phủ `/records`.

### 5.4. Vấn đề thiết kế vai trò

| # | Vấn đề | Đề xuất cần DEC |
|---|---|---|
| R1 | EMP nghĩa là "cá nhân", không có khái niệm nhân viên khối | Thêm scope `own` theo domain (EMP sales: deal của mình; EMP finance: nhập chi), hoặc role tùy biến (02 §2 cho phép) |
| R2 | MGR nhận union mọi domain từ v2.1, không theo phòng ban | Giới hạn theo khối phòng ban, như `scope_pillars` |
| R3 | DIR 28 quyền union, cô lập phân tán trong từng service, `pillar_allows` no-op | Enforce tập trung một chỗ, lấy từ `ROLE_SCOPES` |
| R4 | R-DEC-169 #1/#2: danh bạ là điều kiện của giao việc, owner KPI, tên người trên Kanban, chuyển giao | Một endpoint danh bạ tối thiểu (`id, code, tên, phòng`) theo scope, giải 5 vướng cùng lúc |
| R5 | 10 tài khoản ≠ 7 role: không kiểm được tầng MGR/EMP theo khối nên UAT bỏ sót | Bổ sung seed: Sales MGR, Sales EMP, Finance EMP, HR EMP, Risk DIR |
| R6 | HR Director vs HR: một người vừa nhập vừa duyệt, phân tách nhiệm vụ không thực hiện được | Sau R1, HR EMP tạo, HR-DIR duyệt |

## 6. Bao phủ BRD_Newfeature

Đếm lại 177 dòng ID: **94 Must** (10 phân hệ + NFR), 31 Should. Phân loại do audit này chấm lại bằng code, không chép từ M8.

| Phân hệ | Must | Xong | Một phần | Chặn R-DEC-176 | Thiếu (làm được ngay) | UNVERIFIED |
|---|---:|---:|---:|---:|---:|---:|
| Dashboard | 8 | 2 | 5 | 0 | 1 | 0 |
| Lead | 9 | 0 | 0 | 9 | 0 | 0 |
| Account | 8 | 4 | 3 | 1 | 0 | 0 |
| Contact | 8 | 0 | 0 | 8 | 0 | 0 |
| Opportunity | 11 | 6 | 2 | 3 | 0 | 0 |
| Pipeline | 9 | 5 | 1 | 3 | 0 | 0 |
| Activity | 7 | 0 | 0 | 7 | 0 | 0 |
| Funnel | 7 | 0 | 3 | 1 | 3 | 0 |
| Forecast | 8 | 2 | 0 | 4 | 2 | 0 |
| Performance | 7 | 4 | 3 | 0 | 0 | 0 |
| NFR | 12 | 2 | 8 | 0 | 1 | 1 |
| **Tổng** | **94** | **25 (26,6%)** | **25 (26,6%)** | **36 (38,3%)** | **7 (7,4%)** | **1** |

Chấm theo mức tối thiểu: "Xong" = dùng được qua UI đúng nghĩa BRD; "Một phần" = có API hoặc bản rút gọn.

### 6.1. Sai khác so với bảng M8 §2

| Mục M8 ghi | Đánh giá lại | Lý do |
|---|---|---|
| ACC-001..004 Đã làm | ACC-004 **Một phần** | API có `q`, nhưng spec clients không `searchable` (`specs.ts:129`) |
| ACC-007 liên hệ Đã làm | **Một phần** | Hiển thị được, nhưng form records không có trường liên hệ → không nhập được qua UI |
| FUN-001/002/003 Đã làm | **Một phần** | Bảng, không biểu đồ; sai toán (K4) |
| PIPE-007 Đã làm | **Một phần** | Không có Exit Criteria; chỉ tiến-không-lùi + lý do thua |
| OPP-013 Đã làm | **Một phần** | Chỉ stage, `changed_by=None` |
| PERF-001..004 Đã làm | PERF-002 **Một phần** | Sales DIR chỉ phân cho chính mình |
| PERF-008/009 | **Một phần** | API trả, không UI (`SUMMARY_KEYS` 4 mục) |
| DASH-002 | **Một phần** | `closed_revenue` không render ở `/business/sales` |
| DASH-009, FUN-006, FC-005 | **Thiếu, không phải Chờ** | `owner_id` filter đã có API, không cần R-DEC-176 |
| ACC-005 Chờ R-DEC-176 | **Một phần** | `size`, `industry`, `status` đã là phân loại cơ bản |

### 6.2. BR và UAT nổi bật

| ID | Trạng thái |
|---|---|
| UAT-010 Close Won cập nhật doanh thu | ⛔ Đứt (F7) |
| UAT-012 Funnel Conversion đúng | ⛔ Sai (K4) |
| UAT-007 Exit Criteria | ⛔ Chưa có |
| UAT-009 Deal quá hạn cảnh báo | ✅ Nhưng dùng ngày trình duyệt khác ngày BE |
| UAT-006 Weighted Value, UAT-011 Close Lost, UAT-014 Target, UAT-016/017 | ✅ / ◐ UAT-016 lỗi ở REV |
| BR-009 Next Action, BR-010 bằng chứng, BR-013 Snapshot, BR-015 tiền tệ | ⛔ |

## 7. Phân loại tính năng

| Tính năng | Loại | Ghi chú |
|---|---|---|
| Executive Home, Metric Store, drill-down + lineage | **Core** | Sửa F1, F5 |
| Data Capture C1–C5 + Review + Action Registry + Undo | **Core** | Tài sản mạnh nhất |
| AI Chat có grounding, Tool Registry, Autonomy L0–L3, Kill switch | **Core** | Sửa 9 tool, rate limit |
| Task / Project / Workload / Approval | **Core** | Sửa F14 |
| KPI / OKR / Check-in / SEI | **Core** | Thêm Strategy UI |
| Finance Lite CRUD + Invoice | **Core** | Sửa scope, department picker |
| Sales Pipeline Lite (Client, Deal, Stage, Target) | **Core** | Sửa F7, F13 |
| RBAC, Auth RS256, Audit | **Core** | Sửa F3, F17, F18 |
| Decision Log | **Core** | Hiện chỉ đọc → **chặn** |
| Daily Briefing | **Important** | Mở khóa khi tắt demo clock |
| Insight 9 phần | **Important** | Cần trigger |
| Reporting CSV/XLSX | **Important** | Mở rộng cho MGR |
| Calendar + Google/Outlook | **Important** | UNVERIFIED sync |
| Meeting NL → Action | **Important** | Thêm tạo họp, ghi quyết định |
| Knowledge search | **Important** | Cần chọn embedding |
| Org admin, Onboarding wizard | **Important** | |
| Notification + e-mail | **Important** | |
| AI Evaluation, Acceptance G1–G4 | **Optional** | Nội bộ |
| What-if runway | **Optional** | Sửa K3 trước |
| Calendar sync 2 chiều, Period picker, 5-trụ F.O.C.U.S | **Optional** | R-DEC-16 |
| Executive tile preferences | **Optional** | Có API, chưa UI |
| `DashboardView`, `PillarCard` | **Deprecated** | Xóa (qua DEC) |
| 10 role F.O.C.U.S, `require_role`, EP-04/05, legacy routes | **Deprecated** | Legacy 308 giữ tới khi hết bookmark |
| `InvoicesView`, `EmployeesView`, cột `SalesPipelineView` | **Deprecated** (đề xuất) | Gộp vào records |
| MinIO container | **Deprecated** | Không dùng (`M4` U-2) |
| Lead, Contact, Activity, Pipeline config, Forecast snapshot | **Blocked** | R-DEC-176 |
| Product, Risk UI | **Blocked** | R-DEC-16 |
| Live STT | **Blocked** | R-DEC-166 |
| Xoay khóa JWT, xử lý lịch sử Git | **Blocked** | R-DEC-168, GitLeaks |

### 7.1. Năng lực còn thiếu so với P0 (20 domain)

| Domain | Thiếu | Mức |
|---|---|---|
| D02 Admin & Security | MFA, SSO, xem-như-người-dùng, session list, rate limit | High |
| D04 Workflow | Ngân sách, lương, xóa 2 người; designer rule | High |
| D07 Strategy | UI tạo Strategy, SO, Initiative | High |
| D10 Performance | Check-in có; đánh giá chưa (P1) | Low |
| D12 Meeting | Tạo họp tay, ghi quyết định, Decision 30/60/90 | High |
| D14 Knowledge | SOP doc type, RAG (MODEL_EMBED) | Medium |
| D15 Finance Lite | Forecast UI, phân bổ ngân sách đa phòng, thanh toán ↔ tiền mặt | High |
| D16 HR cơ bản | Hồ sơ chi tiết, nghỉ phép, tuyển dụng sau duyệt | High |
| D17 Sales Lite | Deal → Revenue/Contract, giao owner, tìm khách, tên người | High |
| D26 AI Platform | 9 ACT thiếu, timeout 5s, rate limit, Insight theo trụ, RAG | High |
| D27 CEO Assistant | Briefing mỗi ngày, Insight proactive | High |
| D28 Reporting | Báo cáo định kỳ, PDF | Medium |
| D01, D03, D05, D06, D08, D09, D11, D13 | Đạt mức P0 về code | — |

### 7.2. Thứ tự sửa đề xuất

| Đợt | Việc | Lý do |
|---|---|---|
| 0 — trước khi cho người thật dùng | Tắt `DEMO_LOGIN_AUTOFILL`; chốt chính sách `DEMO_MODE` (cần DEC + phương án dữ liệu); thống nhất `business_today`; sửa scope REV/MGR Finance + Sales; gọi `/auth/logout`; R-DEC-168 | Rủi ro bảo mật + đo lường |
| 1 — tin được số | Bỏ FIN-01 ở `/finance/dashboard`; chốt 5.2-a; sửa funnel; sửa target Q4; thay hard-code Home Department/Employee bằng số thật; freshness theo tuổi dữ liệu | Niềm tin CEO |
| 2 — đóng vòng lặp | Deal thắng → Contract/Revenue; danh bạ tối thiểu; chọn owner; `filled`; Decision ghi + verify; Strategy UI; 9 ACT | Hết dead-end |
| 3 — mở rộng | R-DEC-176, role EMP theo khối, Approval ngân sách, Forecast UI | Theo BRD |

## 8. UNVERIFIED

| Mục | Vì sao |
|---|---|
| Mọi kết luận 403/200 theo role | Không đăng nhập được (cấm POST). Suy từ guard + scope code. Khuyến nghị 1 phiên test có phép với token 10 tài khoản |
| `POST /api/demo-credentials` thực trả mật khẩu | Không gọi; suy từ code + env. Biến `DEMO_*_PASSWORD` có trong web chưa kiểm (không in env) |
| Stack có lộ ra Internet không | Chỉ thấy `0.0.0.0:3000/4000` trên WSL; phụ thuộc mạng ngoài. Mức F4 giả định có người ngoài truy cập được |
| OmniRoute đang sống / chat live | `MODEL_PROVIDER_PRIMARY=omniroute`; `ai.model_call_logs` = 1, `ai.conversations` = 0; chưa gọi |
| Giá trị `/finance/dashboard`, `/sales/dashboard` runtime | Tính lại từ DB + code, chưa đọc response |
| Giá trị dashboard FIN-06 (K7) | Không chạy |
| Google/Outlook sync | Cần OAuth |
| TLS, backup tự động, NFR-001 hiệu năng | Compose không có TLS terminator; có thể ở reverse proxy ngoài repo |
| Mã hóa at-rest ngoài cột mức 4 | Chỉ thấy ghi chú seed, chưa đọc lớp mã hóa |
| Field-level contract FE↔BE | Chỉ so path + method; shared types đã có test M4 |
| Mock router có route lệch API thật | Không so |
| Worker thực chạy job `generate_briefings` hằng ngày | Suy từ `worker.py:113` + DB; không đọc log |

## Version

- Audit 1.0 — 2026-11-05 · Claude (read-only). Không thay đổi repo.

## Phụ lục — ma trận sinh bằng máy

### A3. Page × 10 demo account — canAccess() (lib/permissions.ts) chạy thật trên ma trận quyền

| Page | Rule | ceo | cfo | sales | hr | cpo | manager | office | employee | reviewer | admin | Inbound link (số file) |
|---|---|---|---|---|---|---|---|---|---|---|---|---:|
| `/admin/acceptance` | /admin/acceptance | ✓ | ✓ | ✓ | ✓ | ✓ | · | · | · | · | · | 1 |
| `/admin/ai/evaluation` | /admin/ai | ✓ | · | · | · | · | · | · | · | · | ✓ | 1 |
| `/admin/ai/logs` | /admin/ai | ✓ | · | · | · | · | · | · | · | · | ✓ | 2 |
| `/admin/ai` | /admin/ai | ✓ | · | · | · | · | · | · | · | · | ✓ | 4 |
| `/admin/audit` | /admin/audit | · | · | · | · | · | · | · | · | · | ✓ | 2 |
| `/admin/data-capture` | /admin/data-capture | · | · | · | · | · | · | · | · | · | ✓ | 2 |
| `/admin/onboarding` | /admin/onboarding | ✓ | · | · | · | · | · | · | · | · | ✓ | 2 |
| `/admin/org` | /admin/org | ✓ | · | · | ✓ | · | · | · | · | · | ✓ | 2 |
| `/admin` | /admin | ✓ | · | · | ✓ | · | · | · | · | · | ✓ | 2 |
| `/admin/positions` | /admin/positions | ✓ | · | · | ✓ | · | · | · | · | · | ✓ | 1 |
| `/admin/roles` | /admin/roles | ✓ | · | · | · | · | · | · | · | · | ✓ | 1 |
| `/admin/users` | /admin/users | ✓ | · | · | · | · | · | · | · | · | ✓ | 2 |
| `/ask/activity` | /ask | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | 0 |
| `/ask` | /ask | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | 2 |
| `/business/finance/invoices` | /business/finance/invoices | ✓ | ✓ | · | · | · | ✓ | ✓ | · | ✓ | · | 2 |
| `/business/finance` | /business/finance | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | · | ✓ | · | 1 |
| `/business/finance/records` | /business/finance/records | ✓ | ✓ | · | · | · | ✓ | ✓ | · | ✓ | · | 1 |
| `/business/hr/employees` | /business/hr | ✓ | · | · | ✓ | · | ✓ | ✓ | ✓ | ✓ | · | 1 |
| `/business/hr/records` | /business/hr | ✓ | · | · | ✓ | · | ✓ | ✓ | ✓ | ✓ | · | 2 |
| `/business` | /business | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | · | 0 |
| `/business/sales/clients/[id]` | /business/sales/clients | ✓ | · | ✓ | · | · | ✓ | ✓ | · | · | · | 2 |
| `/business/sales/deals/[id]` | /business/sales/deals | ✓ | · | ✓ | · | · | ✓ | ✓ | · | · | · | 3 |
| `/business/sales` | /business | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | · | 1 |
| `/business/sales/pipeline` | /business/sales/pipeline | ✓ | · | ✓ | · | · | ✓ | ✓ | · | · | · | 2 |
| `/business/sales/records` | /business/sales/records | ✓ | · | ✓ | · | · | ✓ | ✓ | · | ✓ | · | 4 |
| `/data/imports/[batchId]` | /data/imports | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | 2 |
| `/data/new/[documentType]` | /data/new | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | 1 |
| `/data` | /data | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | 5 |
| `/data/review/[documentId]` | /data/review | · | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | · | ✓ | · | 2 |
| `/data/review` | /data/review | · | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | · | ✓ | · | 1 |
| `/goals/check-ins` | /goals/check-ins | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | · | · | 4 |
| `/goals/kpis/[id]` | /goals/kpis | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | · | · | 3 |
| `/goals/objectives/[id]` | /goals/objectives | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | · | · | 3 |
| `/goals` | /goals | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | · | · | 4 |
| `/home/alerts` | /home | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | 1 |
| `/home/metrics/[code]` | /home | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | 1 |
| `/home` | /home | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | 8 |
| `/home/pillar/[slug]` | /home/pillar | ✓ | ✓ | ✓ | ✓ | ✓ | · | · | · | · | · | 4 |
| `/knowledge/[tab]` | /knowledge | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | 0 |
| `/knowledge` | /knowledge | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | 1 |
| `/meetings/calendar` | /meetings | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | · | · | 1 |
| `/meetings` | /meetings | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | · | · | 3 |
| `/settings/integrations` | — | · | · | · | · | · | · | · | · | · | · | 1 |
| `/work/approvals` | /work/approvals | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | · | · | · | 1 |
| `/work` | /work | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | · | · | 5 |
| `/work/projects/[id]` | /work/projects | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | · | · | 4 |
| `/work/projects` | /work/projects | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | · | · | 4 |
| `/work/workload` | /work/workload | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | · | · | · | 1 |
| `/login` | — | · | · | · | · | · | · | · | · | · | · | 0 |
| `/403` | — | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | 0 |
| `/` | — | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | 0 |

### A2. Page → API calls (static import closure; over-approximates conditional calls)

| Page | # API | API calls (method path) |
|---|---:|---|
| `/` | 2 | POST /auth/login; POST /auth/refresh |
| `/403` | 0 |  |
| `/admin` | 6 | GET /org/organizations; GET /platform/onboarding; GET /platform/users; PATCH /platform/onboarding; POST /auth/login; POST /auth/refresh |
| `/admin/acceptance` | 1 | GET /reporting/acceptance |
| `/admin/ai` | 18 | DELETE /ai/autonomy-policies/{policy_id}; GET /ai/actions; GET /ai/agents; GET /ai/autonomy-policies; GET /ai/kill-switch; GET /ai/model-calls; GET /ai/tool-calls; GET /ai/tools; GET /ai/usage; PATCH /ai/agents/{code}; PATCH /ai/autonomy-policies/{policy_id}; POST /ai/actions/{action_id}/confirm; POST /ai/actions/{action_id}/reject; POST /ai/actions/{action_id}/undo … |
| `/admin/ai/evaluation` | 2 | GET /ai/evaluations; GET /ai/evaluations/{evaluation_id} |
| `/admin/ai/logs` | 17 | DELETE /ai/autonomy-policies/{policy_id}; GET /ai/actions; GET /ai/agents; GET /ai/autonomy-policies; GET /ai/kill-switch; GET /ai/model-calls; GET /ai/tool-calls; GET /ai/tools; GET /ai/usage; GET /platform/users; PATCH /ai/agents/{code}; PATCH /ai/autonomy-policies/{policy_id}; POST /ai/actions/{action_id}/confirm; POST /ai/actions/{action_id}/reject … |
| `/admin/audit` | 1 | GET /platform/audit-logs |
| `/admin/data-capture` | 23 | GET /data-capture/document-types; GET /data-capture/documents/{document_id}/actions; GET /data-capture/documents/{document_id}/source; GET /data-capture/extraction-schemas; GET /data-capture/forms/{document_type}; GET /data-capture/imports/{batch_id}; GET /data-capture/imports/{batch_id}/error-file; GET /data-capture/imports/{batch_id}/rows; GET /data-capture/inbox; GET /data-capture/incidents; GET /data-capture/validation-rules; GET /idp/documents/{document_id}; GET /lineage/{entity}/{record_id}; PATCH /data-capture/document-types/{type_id} … |
| `/admin/onboarding` | 29 | GET /data-capture/document-types; GET /data-capture/documents/{document_id}/actions; GET /data-capture/documents/{document_id}/source; GET /data-capture/forms/{document_type}; GET /data-capture/imports/{batch_id}; GET /data-capture/imports/{batch_id}/error-file; GET /data-capture/imports/{batch_id}/rows; GET /data-capture/inbox; GET /hr/departments; GET /idp/documents/{document_id}; GET /lineage/{entity}/{record_id}; GET /org/assignments; GET /org/organizations; GET /org/positions … |
| `/admin/org` | 25 | DELETE /hr/departments/{department_id}; DELETE /org/teams/{team_id}; GET /data-capture/document-types; GET /data-capture/documents/{document_id}/actions; GET /data-capture/documents/{document_id}/source; GET /data-capture/forms/{document_type}; GET /data-capture/imports/{batch_id}; GET /data-capture/imports/{batch_id}/error-file; GET /data-capture/imports/{batch_id}/rows; GET /data-capture/inbox; GET /hr/departments; GET /idp/documents/{document_id}; GET /lineage/{entity}/{record_id}; GET /org/assignments … |
| `/admin/positions` | 9 | GET /hr/departments; GET /org/assignments; GET /org/positions; GET /org/teams; GET /org/tree; PATCH /org/positions/{position_id}; POST /auth/login; POST /auth/refresh; POST /org/positions |
| `/admin/roles` | 1 | GET /platform/roles |
| `/admin/users` | 12 | GET /hr/departments; GET /org/assignments; GET /org/positions; GET /org/teams; GET /org/tree; GET /platform/users; PATCH /platform/users/{user_id}; POST /auth/login; POST /auth/refresh; POST /platform/users; POST /platform/users/{user_id}/deactivate; POST /platform/users/{user_id}/reactivate |
| `/ask` | 21 | DELETE /ai/autonomy-policies/{policy_id}; GET /ai/actions; GET /ai/agents; GET /ai/autonomy-policies; GET /ai/conversations; GET /ai/conversations/{conversation_id}/messages; GET /ai/kill-switch; GET /ai/model-calls; GET /ai/tool-calls; GET /ai/tools; GET /ai/usage; PATCH /ai/agents/{code}; PATCH /ai/autonomy-policies/{policy_id}; POST /ai/actions/{action_id}/confirm … |
| `/ask/activity` | 18 | DELETE /ai/autonomy-policies/{policy_id}; GET /ai/actions; GET /ai/agents; GET /ai/autonomy-policies; GET /ai/kill-switch; GET /ai/model-calls; GET /ai/tool-calls; GET /ai/tools; GET /ai/usage; PATCH /ai/agents/{code}; PATCH /ai/autonomy-policies/{policy_id}; POST /ai/actions/{action_id}/confirm; POST /ai/actions/{action_id}/reject; POST /ai/actions/{action_id}/undo … |
| `/business` | 2 | POST /auth/login; POST /auth/refresh |
| `/business/finance` | 4 | GET /finance/budgets/status; GET /finance/budgets/{budget_id}; GET /finance/dashboard; GET /finance/what-if/runway |
| `/business/finance/invoices` | 1 | GET /finance/invoices |
| `/business/finance/records` | 49 | DELETE /finance/budgets/{budget_id}; DELETE /finance/expenses/{expense_id}; DELETE /finance/invoices/{invoice_id}; DELETE /finance/revenues/{revenue_id}; DELETE /hr/employees/{employee_id}; DELETE /hr/hiring-plans/{plan_id}; DELETE /sales/clients/{client_id}; DELETE /sales/contracts/{contract_id}; DELETE /sales/deals/{deal_id}; DELETE /sales/targets/{target_id}; GET /finance/budgets; GET /finance/cash-positions; GET /finance/expenses; GET /finance/invoices … |
| `/business/hr/employees` | 1 | GET /hr/employees |
| `/business/hr/records` | 49 | DELETE /finance/budgets/{budget_id}; DELETE /finance/expenses/{expense_id}; DELETE /finance/invoices/{invoice_id}; DELETE /finance/revenues/{revenue_id}; DELETE /hr/employees/{employee_id}; DELETE /hr/hiring-plans/{plan_id}; DELETE /sales/clients/{client_id}; DELETE /sales/contracts/{contract_id}; DELETE /sales/deals/{deal_id}; DELETE /sales/targets/{target_id}; GET /finance/budgets; GET /finance/cash-positions; GET /finance/expenses; GET /finance/invoices … |
| `/business/sales` | 12 | GET /sales/clients; GET /sales/clients/{client_id}; GET /sales/contracts; GET /sales/dashboard; GET /sales/deals; GET /sales/deals/{deal_id}; GET /sales/deals/{deal_id}/stage-history; GET /sales/performance; GET /sales/pipeline; POST /auth/login; POST /auth/refresh; POST /sales/deals/{deal_id}/stage |
| `/business/sales/clients/[id]` | 9 | GET /sales/clients; GET /sales/clients/{client_id}; GET /sales/contracts; GET /sales/deals; GET /sales/deals/{deal_id}; GET /sales/deals/{deal_id}/stage-history; GET /sales/performance; GET /sales/pipeline; POST /sales/deals/{deal_id}/stage |
| `/business/sales/deals/[id]` | 11 | GET /sales/clients; GET /sales/clients/{client_id}; GET /sales/contracts; GET /sales/deals; GET /sales/deals/{deal_id}; GET /sales/deals/{deal_id}/stage-history; GET /sales/performance; GET /sales/pipeline; POST /auth/login; POST /auth/refresh; POST /sales/deals/{deal_id}/stage |
| `/business/sales/pipeline` | 11 | GET /sales/clients; GET /sales/clients/{client_id}; GET /sales/contracts; GET /sales/deals; GET /sales/deals/{deal_id}; GET /sales/deals/{deal_id}/stage-history; GET /sales/performance; GET /sales/pipeline; POST /auth/login; POST /auth/refresh; POST /sales/deals/{deal_id}/stage |
| `/business/sales/records` | 49 | DELETE /finance/budgets/{budget_id}; DELETE /finance/expenses/{expense_id}; DELETE /finance/invoices/{invoice_id}; DELETE /finance/revenues/{revenue_id}; DELETE /hr/employees/{employee_id}; DELETE /hr/hiring-plans/{plan_id}; DELETE /sales/clients/{client_id}; DELETE /sales/contracts/{contract_id}; DELETE /sales/deals/{deal_id}; DELETE /sales/targets/{target_id}; GET /finance/budgets; GET /finance/cash-positions; GET /finance/expenses; GET /finance/invoices … |
| `/data` | 17 | GET /data-capture/document-types; GET /data-capture/documents/{document_id}/actions; GET /data-capture/documents/{document_id}/source; GET /data-capture/forms/{document_type}; GET /data-capture/imports/{batch_id}; GET /data-capture/imports/{batch_id}/error-file; GET /data-capture/imports/{batch_id}/rows; GET /data-capture/inbox; GET /idp/documents/{document_id}; GET /lineage/{entity}/{record_id}; POST /auth/login; POST /auth/refresh; POST /data-capture/documents/{document_id}/commit; POST /data-capture/documents/{document_id}/undo … |
| `/data/imports/[batchId]` | 14 | GET /data-capture/document-types; GET /data-capture/documents/{document_id}/actions; GET /data-capture/documents/{document_id}/source; GET /data-capture/forms/{document_type}; GET /data-capture/imports/{batch_id}; GET /data-capture/imports/{batch_id}/error-file; GET /data-capture/imports/{batch_id}/rows; GET /data-capture/inbox; GET /idp/documents/{document_id}; GET /lineage/{entity}/{record_id}; PATCH /data-capture/imports/{batch_id}/mapping; POST /data-capture/documents/{document_id}/commit; POST /data-capture/documents/{document_id}/undo; POST /data-capture/imports/{batch_id}/submit |
| `/data/new/[documentType]` | 13 | GET /data-capture/document-types; GET /data-capture/documents/{document_id}/actions; GET /data-capture/documents/{document_id}/source; GET /data-capture/forms/{document_type}; GET /data-capture/imports/{batch_id}; GET /data-capture/imports/{batch_id}/error-file; GET /data-capture/imports/{batch_id}/rows; GET /data-capture/inbox; GET /idp/documents/{document_id}; GET /lineage/{entity}/{record_id}; POST /data-capture/documents/{document_id}/commit; POST /data-capture/documents/{document_id}/undo; POST /data-capture/manual |
| `/data/review` | 4 | GET /idp/review-queue; POST /auth/login; POST /auth/refresh; POST /idp/documents |
| `/data/review/[documentId]` | 18 | GET /data-capture/document-types; GET /data-capture/documents/{document_id}/actions; GET /data-capture/documents/{document_id}/source; GET /data-capture/forms/{document_type}; GET /data-capture/imports/{batch_id}; GET /data-capture/imports/{batch_id}/error-file; GET /data-capture/imports/{batch_id}/rows; GET /data-capture/inbox; GET /idp/documents/{document_id}; GET /idp/documents/{document_id}/review; GET /lineage/{entity}/{record_id}; PATCH /idp/documents/{document_id}/fields; POST /data-capture/documents/{document_id}/commit; POST /data-capture/documents/{document_id}/undo … |
| `/goals` | 33 | DELETE /key-results/{kr_id}; DELETE /kpis/{kpi_id}; DELETE /objectives/{objective_id}; GET /goals/check-ins; GET /goals/check-ins/due; GET /goals/strategies; GET /goals/tree; GET /hr/departments; GET /key-results/{kr_id}/check-ins; GET /kpis/{kpi_id}; GET /kpis/{kpi_id}/check-ins; GET /kpis/{kpi_id}/evaluations; GET /kpis/{kpi_id}/measurements; GET /kpis/{kpi_id}/targets … |
| `/goals/check-ins` | 32 | DELETE /key-results/{kr_id}; DELETE /kpis/{kpi_id}; DELETE /objectives/{objective_id}; GET /goals/check-ins; GET /goals/check-ins/due; GET /goals/strategies; GET /goals/tree; GET /hr/departments; GET /key-results/{kr_id}/check-ins; GET /kpis/{kpi_id}; GET /kpis/{kpi_id}/check-ins; GET /kpis/{kpi_id}/evaluations; GET /kpis/{kpi_id}/measurements; GET /kpis/{kpi_id}/targets … |
| `/goals/kpis/[id]` | 33 | DELETE /key-results/{kr_id}; DELETE /kpis/{kpi_id}; DELETE /objectives/{objective_id}; GET /goals/check-ins; GET /goals/check-ins/due; GET /goals/strategies; GET /goals/tree; GET /hr/departments; GET /key-results/{kr_id}/check-ins; GET /kpis/{kpi_id}; GET /kpis/{kpi_id}/check-ins; GET /kpis/{kpi_id}/evaluations; GET /kpis/{kpi_id}/measurements; GET /kpis/{kpi_id}/targets … |
| `/goals/objectives/[id]` | 33 | DELETE /key-results/{kr_id}; DELETE /kpis/{kpi_id}; DELETE /objectives/{objective_id}; GET /goals/check-ins; GET /goals/check-ins/due; GET /goals/strategies; GET /goals/tree; GET /hr/departments; GET /key-results/{kr_id}/check-ins; GET /kpis/{kpi_id}; GET /kpis/{kpi_id}/check-ins; GET /kpis/{kpi_id}/evaluations; GET /kpis/{kpi_id}/measurements; GET /kpis/{kpi_id}/targets … |
| `/home` | 9 | GET /ai/briefings/today; GET /ai/insights; GET /dashboard/metrics/{metric_code}; GET /reporting/dashboards/department; GET /reporting/dashboards/employee; GET /reporting/dashboards/executive; POST /ai/briefings/{briefing_id}/open; POST /auth/login; POST /auth/refresh |
| `/home/alerts` | 5 | GET /dashboard/alerts; GET /dashboard/metrics; POST /auth/login; POST /auth/refresh; POST /dashboard/alerts/{id}/acknowledge |
| `/home/metrics/[code]` | 1 | GET /dashboard/metrics/{metric_code} |
| `/home/pillar/[slug]` | 12 | GET /dashboard/metrics/{metric_code}; GET /execution/dashboard; GET /finance/cash-positions; GET /finance/dashboard; GET /finance/invoices; GET /hr/dashboard; GET /idp/documents/{document_id}; GET /product/dashboard; GET /risk/dashboard; GET /sales/dashboard; POST /auth/login; POST /auth/refresh |
| `/knowledge` | 7 | GET /execution/decisions; GET /idp/documents/search; GET /idp/documents/{document_id}; GET /reporting/reports; GET /reporting/reports/{code}/export; POST /auth/login; POST /auth/refresh |
| `/knowledge/[tab]` | 7 | GET /execution/decisions; GET /idp/documents/search; GET /idp/documents/{document_id}; GET /reporting/reports; GET /reporting/reports/{code}/export; POST /auth/login; POST /auth/refresh |
| `/login` | 0 |  |
| `/meetings` | 4 | GET /execution/meetings; POST /auth/login; POST /auth/refresh; POST /data-capture/natural-language |
| `/meetings/calendar` | 4 | DELETE /calendar/events/{event_id}; GET /calendar/events; PATCH /calendar/events/{event_id}; POST /calendar/events |
| `/settings/integrations` | 3 | DELETE /integrations/{provider}/disconnect; GET /integrations/providers; POST /integrations/{provider}/connect |
| `/work` | 29 | DELETE /work/tasks/{task_id}/dependencies/{dependency_id}; GET /data-capture/document-types; GET /data-capture/documents/{document_id}/actions; GET /data-capture/documents/{document_id}/source; GET /data-capture/forms/{document_type}; GET /data-capture/imports/{batch_id}; GET /data-capture/imports/{batch_id}/error-file; GET /data-capture/imports/{batch_id}/rows; GET /data-capture/inbox; GET /idp/documents/{document_id}; GET /lineage/{entity}/{record_id}; GET /org/tree; GET /platform/audit-logs; GET /work/projects … |
| `/work/approvals` | 14 | GET /org/tree; GET /platform/audit-logs; GET /work/projects; GET /work/projects/{project_id}; GET /work/tasks; GET /work/tasks/{task_id}; GET /work/tasks/{task_id}/dependencies; GET /work/workload; GET /workflow/approval-requests; GET /workflow/approval-requests/{id}; PATCH /work/tasks/{task_id}; POST /auth/login; POST /auth/refresh; POST /workflow/approval-requests/{id}/decide |
| `/work/projects` | 14 | GET /org/tree; GET /platform/audit-logs; GET /work/projects; GET /work/projects/{project_id}; GET /work/tasks; GET /work/tasks/{task_id}; GET /work/tasks/{task_id}/dependencies; GET /work/workload; GET /workflow/approval-requests; GET /workflow/approval-requests/{id}; PATCH /work/tasks/{task_id}; POST /auth/login; POST /auth/refresh; POST /work/projects |
| `/work/projects/[id]` | 32 | DELETE /work/tasks/{task_id}/dependencies/{dependency_id}; GET /data-capture/document-types; GET /data-capture/documents/{document_id}/actions; GET /data-capture/documents/{document_id}/source; GET /data-capture/forms/{document_type}; GET /data-capture/imports/{batch_id}; GET /data-capture/imports/{batch_id}/error-file; GET /data-capture/imports/{batch_id}/rows; GET /data-capture/inbox; GET /idp/documents/{document_id}; GET /lineage/{entity}/{record_id}; GET /org/tree; GET /platform/audit-logs; GET /work/projects … |
| `/work/workload` | 13 | GET /org/tree; GET /platform/audit-logs; GET /work/projects; GET /work/projects/{project_id}; GET /work/tasks; GET /work/tasks/{task_id}; GET /work/tasks/{task_id}/dependencies; GET /work/workload; GET /workflow/approval-requests; GET /workflow/approval-requests/{id}; PATCH /work/tasks/{task_id}; POST /auth/login; POST /auth/refresh |

### A1. FastAPI routes (328) — method · path · permission (● = `require_pillar_permission`) · FE consumer

| Module | Method | Path | Permission | Handler | FE consumer (file) |
|---|---|---|---|---|---|
| ai | GET | `/reporting/acceptance` | dashboard:read | ai/routes/acceptance.py:22 | admin/acceptance/use-acceptance.ts |
| ai | GET | `/ai/agents` | ai:query | ai/routes/admin.py:43 | admin/ai/use-ai-admin.ts |
| ai | PATCH | `/ai/agents/{code}` | ai:admin | ai/routes/admin.py:51 | admin/ai/use-ai-admin.ts |
| ai | GET | `/ai/autonomy-policies` | ai:admin | ai/routes/admin.py:59 | admin/ai/use-ai-admin.ts |
| ai | POST | `/ai/autonomy-policies` | ai:admin | ai/routes/admin.py:76 | admin/ai/use-ai-admin.ts |
| ai | DELETE | `/ai/autonomy-policies/{policy_id}` | ai:admin | ai/routes/admin.py:100 | admin/ai/use-ai-admin.ts |
| ai | PATCH | `/ai/autonomy-policies/{policy_id}` | ai:admin | ai/routes/admin.py:88 | admin/ai/use-ai-admin.ts |
| ai | GET | `/ai/model-calls` | ai:admin | ai/routes/admin.py:135 | admin/ai/use-ai-admin.ts |
| ai | GET | `/ai/tool-calls` | ai:admin | ai/routes/admin.py:116 | admin/ai/use-ai-admin.ts |
| ai | GET | `/ai/actions` | ai:query | ai/routes/router.py:220 | admin/ai/use-ai-admin.ts, ai/use-ai-feed.ts |
| ai | GET | `/ai/actions/{action_id}` | ai:query | ai/routes/router.py:230 | **—** |
| ai | POST | `/ai/actions/{action_id}/confirm` | ai:write | ai/routes/router.py:235 | admin/ai/use-ai-admin.ts |
| ai | POST | `/ai/actions/{action_id}/reject` | ai:write | ai/routes/router.py:244 | admin/ai/use-ai-admin.ts |
| ai | POST | `/ai/actions/{action_id}/undo` | ai:write | ai/routes/router.py:253 | admin/ai/use-ai-admin.ts |
| ai | GET | `/ai/briefings` | ai:query | ai/routes/router.py:269 | **—** |
| ai | GET | `/ai/briefings/today` | ai:query | ai/routes/router.py:262 | briefing/use-briefing.ts |
| ai | POST | `/ai/briefings/{briefing_id}/open` | ai:query | ai/routes/router.py:280 | briefing/use-briefing.ts |
| ai | POST | `/ai/chat` | ai:query | ai/routes/router.py:89 | **—** |
| ai | POST | `/ai/chat/stream` | ai:query | ai/routes/router.py:106 | ai/use-chat.ts, ai/use-chat.ts:52 |
| ai | GET | `/ai/conversations` | ai:query | ai/routes/router.py:183 | ai/ChatView.tsx |
| ai | GET | `/ai/conversations/{conversation_id}/messages` | ai:query | ai/routes/router.py:188 | ai/ChatView.tsx |
| ai | GET | `/ai/evaluations` | ai:admin | ai/routes/router.py:289 | admin/ai/evaluation/use-evaluations.ts |
| ai | GET | `/ai/evaluations/{evaluation_id}` | ai:admin | ai/routes/router.py:302 | admin/ai/evaluation/use-evaluations.ts |
| ai | GET | `/ai/insights` | ai:query | ai/routes/router.py:198 | ai/InsightsPanel.tsx |
| ai | POST | `/ai/insights/{insight_id}/dismiss` | ai:query | ai/routes/router.py:209 | **—** |
| ai | GET | `/ai/kill-switch` | ai:query | ai/routes/router.py:313 | admin/ai/use-ai-admin.ts |
| ai | PUT | `/ai/kill-switch` | ai:admin | ai/routes/router.py:318 | admin/ai/use-ai-admin.ts |
| ai | GET | `/ai/tools` | ai:query | ai/routes/router.py:327 | admin/ai/use-ai-admin.ts |
| ai | GET | `/ai/usage` | ai:admin | ai/routes/router.py:341 | admin/ai/use-ai-admin.ts |
| auth | POST | `/auth/login` | authenticated/public | auth/routes/router.py:34 | lib/auth.ts, lib/auth.ts:72 |
| auth | POST | `/auth/logout` | authenticated/public | auth/routes/router.py:44 | **—** |
| auth | GET | `/auth/me` | authenticated/public | auth/routes/router.py:55 | **—** |
| auth | POST | `/auth/refresh` | authenticated/public | auth/routes/router.py:39 | lib/auth.ts, lib/auth.ts:37 |
| auth | GET | `/platform/roles` | platform:read | auth/routes/users.py:89 | admin/RolesView.tsx |
| auth | GET | `/platform/users` | platform:read | auth/routes/users.py:28 | admin/UsersView.tsx, admin/ai/logs/parts.tsx +2 |
| auth | POST | `/platform/users` | platform:admin | auth/routes/users.py:39 | admin/UsersView.tsx, admin/onboarding/UsersStep.tsx |
| auth | GET | `/platform/users/{user_id}` | platform:read | auth/routes/users.py:49 | **—** |
| auth | PATCH | `/platform/users/{user_id}` | platform:admin | auth/routes/users.py:54 | admin/UsersView.tsx |
| auth | POST | `/platform/users/{user_id}/deactivate` | platform:admin | auth/routes/users.py:75 | admin/UsersView.tsx |
| auth | POST | `/platform/users/{user_id}/reactivate` | platform:admin | auth/routes/users.py:82 | admin/UsersView.tsx |
| dashboard | GET | `/reporting/dashboards/department` | execution:read | dashboard/routes/reporting.py:53 | home/DepartmentView.tsx |
| dashboard | GET | `/reporting/dashboards/employee` | execution:read | dashboard/routes/reporting.py:63 | home/EmployeeView.tsx |
| dashboard | GET | `/reporting/dashboards/executive` | dashboard:read | dashboard/routes/reporting.py:45 | home/ExecutiveView.tsx |
| dashboard | GET | `/reporting/preferences/executive-tiles` | dashboard:read | dashboard/routes/reporting.py:71 | **—** |
| dashboard | PUT | `/reporting/preferences/executive-tiles` | dashboard:write | dashboard/routes/reporting.py:80 | **—** |
| dashboard | GET | `/reporting/reports` | dashboard:read | dashboard/routes/reporting.py:100 | knowledge/use-knowledge.ts |
| dashboard | GET | `/reporting/reports/{code}/export` | dashboard:read | dashboard/routes/reporting.py:106 | knowledge/use-knowledge.ts |
| dashboard | GET | `/dashboard/alerts` | dashboard:read | dashboard/routes/router.py:60 | dashboard/AlertsList.tsx |
| dashboard | POST | `/dashboard/alerts/{id}/acknowledge` | dashboard:write | dashboard/routes/router.py:74 | dashboard/AlertsList.tsx |
| dashboard | POST | `/dashboard/alerts/{id}/dismiss` | dashboard:write | dashboard/routes/router.py:86 | **—** |
| dashboard | GET | `/dashboard/metrics` | dashboard:read | dashboard/routes/router.py:40 | dashboard/AlertsPageView.tsx, dashboard/DashboardView.tsx |
| dashboard | GET | `/dashboard/metrics/{metric_code}` | dashboard:read | dashboard/routes/router.py:50 | dashboard/use-metric-detail.ts, finance/LineageDialog.tsx |
| execution | GET | `/calendar/events` | execution:read | execution/routes/calendar.py:37 | execution/use-calendar.ts |
| execution | POST | `/calendar/events` | execution:write | execution/routes/calendar.py:49 | execution/use-calendar.ts |
| execution | DELETE | `/calendar/events/{event_id}` | execution:write | execution/routes/calendar.py:75 | execution/use-calendar.ts |
| execution | GET | `/calendar/events/{event_id}` | execution:read | execution/routes/calendar.py:60 | **—** |
| execution | PATCH | `/calendar/events/{event_id}` | execution:write | execution/routes/calendar.py:65 | execution/use-calendar.ts |
| execution | GET | `/goals/check-ins` | execution:read | execution/routes/goals.py:77 | goals/use-goals.ts |
| execution | GET | `/goals/check-ins/due` | execution:read | execution/routes/goals.py:95 | goals/use-goals.ts |
| execution | GET | `/goals/initiatives` | execution:read | execution/routes/goals.py:226 | **—** |
| execution | POST | `/goals/initiatives` | execution:write | execution/routes/goals.py:242 | **—** |
| execution | DELETE | `/goals/initiatives/{initiative_id}` | execution:write | execution/routes/goals.py:274 | **—** |
| execution | GET | `/goals/initiatives/{initiative_id}` | execution:read | execution/routes/goals.py:254 | **—** |
| execution | PATCH | `/goals/initiatives/{initiative_id}` | execution:write | execution/routes/goals.py:261 | **—** |
| execution | GET | `/goals/initiatives/{initiative_id}/milestones` | execution:read | execution/routes/goals.py:288 | **—** |
| execution | POST | `/goals/initiatives/{initiative_id}/milestones` | execution:write | execution/routes/goals.py:297 | **—** |
| execution | DELETE | `/goals/initiatives/{initiative_id}/milestones/{milestone_id}` | execution:write | execution/routes/goals.py:336 | **—** |
| execution | GET | `/goals/initiatives/{initiative_id}/milestones/{milestone_id}` | execution:read | execution/routes/goals.py:312 | **—** |
| execution | PATCH | `/goals/initiatives/{initiative_id}/milestones/{milestone_id}` | execution:write | execution/routes/goals.py:322 | **—** |
| execution | GET | `/goals/initiatives/{initiative_id}/projects` | execution:read | execution/routes/goals.py:349 | **—** |
| execution | GET | `/goals/strategic-objectives` | execution:read | execution/routes/goals.py:160 | **—** |
| execution | POST | `/goals/strategic-objectives` | execution:write | execution/routes/goals.py:175 | **—** |
| execution | DELETE | `/goals/strategic-objectives/{so_id}` | execution:write | execution/routes/goals.py:212 | **—** |
| execution | GET | `/goals/strategic-objectives/{so_id}` | execution:read | execution/routes/goals.py:190 | **—** |
| execution | PATCH | `/goals/strategic-objectives/{so_id}` | execution:write | execution/routes/goals.py:198 | **—** |
| execution | GET | `/goals/strategies` | execution:read | execution/routes/goals.py:104 | goals/use-goals.ts |
| execution | POST | `/goals/strategies` | execution:write | execution/routes/goals.py:114 | **—** |
| execution | DELETE | `/goals/strategies/{strategy_id}` | execution:write | execution/routes/goals.py:146 | **—** |
| execution | GET | `/goals/strategies/{strategy_id}` | execution:read | execution/routes/goals.py:127 | **—** |
| execution | PATCH | `/goals/strategies/{strategy_id}` | execution:write | execution/routes/goals.py:134 | **—** |
| execution | GET | `/goals/tree` | execution:read | execution/routes/goals.py:65 | goals/use-goals.ts |
| execution | GET | `/kpis` | execution:read | execution/routes/kpis.py:48 | **—** |
| execution | POST | `/kpis` | execution:write | execution/routes/kpis.py:63 | goals/use-goals.ts |
| execution | DELETE | `/kpis/{kpi_id}` | execution:write | execution/routes/kpis.py:89 | goals/use-goals.ts |
| execution | GET | `/kpis/{kpi_id}` | execution:read | execution/routes/kpis.py:73 | goals/use-goals.ts |
| execution | PATCH | `/kpis/{kpi_id}` | execution:write | execution/routes/kpis.py:79 | goals/use-goals.ts |
| execution | GET | `/kpis/{kpi_id}/check-ins` | execution:read | execution/routes/kpis.py:171 | goals/use-goals.ts |
| execution | POST | `/kpis/{kpi_id}/check-ins` | execution:write | execution/routes/kpis.py:186 | goals/use-goals.ts |
| execution | GET | `/kpis/{kpi_id}/evaluations` | execution:read | execution/routes/kpis.py:156 | goals/use-goals.ts |
| execution | GET | `/kpis/{kpi_id}/measurements` | execution:read | execution/routes/kpis.py:99 | goals/use-goals.ts |
| execution | POST | `/kpis/{kpi_id}/measurements` | execution:write | execution/routes/kpis.py:112 | goals/use-goals.ts |
| execution | GET | `/kpis/{kpi_id}/targets` | execution:read | execution/routes/kpis.py:128 | goals/use-goals.ts |
| execution | POST | `/kpis/{kpi_id}/targets` | execution:write | execution/routes/kpis.py:140 | goals/use-goals.ts |
| execution | DELETE | `/key-results/{kr_id}` | execution:write | execution/routes/okr.py:148 | goals/use-goals.ts |
| execution | GET | `/key-results/{kr_id}` | execution:read | execution/routes/okr.py:133 | **—** |
| execution | PATCH | `/key-results/{kr_id}` | execution:write | execution/routes/okr.py:138 | goals/use-goals.ts |
| execution | GET | `/key-results/{kr_id}/check-ins` | execution:read | execution/routes/okr.py:173 | goals/use-goals.ts |
| execution | POST | `/key-results/{kr_id}/check-ins` | execution:write | execution/routes/okr.py:188 | goals/use-goals.ts |
| execution | GET | `/key-results/{kr_id}/measurements` | execution:read | execution/routes/okr.py:158 | **—** |
| execution | GET | `/objectives` | execution:read | execution/routes/okr.py:49 | **—** |
| execution | POST | `/objectives` | execution:write | execution/routes/okr.py:64 | goals/use-goals.ts |
| execution | DELETE | `/objectives/{objective_id}` | execution:write | execution/routes/okr.py:95 | goals/use-goals.ts |
| execution | GET | `/objectives/{objective_id}` | execution:read | execution/routes/okr.py:76 | goals/use-goals.ts |
| execution | PATCH | `/objectives/{objective_id}` | execution:write | execution/routes/okr.py:82 | goals/use-goals.ts |
| execution | GET | `/objectives/{objective_id}/key-results` | execution:read | execution/routes/okr.py:106 | goals/use-goals.ts |
| execution | POST | `/objectives/{objective_id}/key-results` | execution:write | execution/routes/okr.py:118 | goals/use-goals.ts |
| execution | GET | `/execution/dashboard` | execution:query | execution/routes/router.py:59 | dashboard/use-pillar.ts |
| execution | GET | `/execution/decisions` | execution:read | execution/routes/router.py:122 | knowledge/use-knowledge.ts |
| execution | POST | `/execution/decisions` | execution:write | execution/routes/router.py:136 | **—** |
| execution | GET | `/execution/decisions/{decision_id}` | execution:read | execution/routes/router.py:146 | **—** |
| execution | PATCH | `/execution/decisions/{decision_id}` | execution:write | execution/routes/router.py:151 | **—** |
| execution | GET | `/execution/meetings` | execution:read | execution/routes/router.py:76 | execution/MeetingList.tsx |
| execution | POST | `/execution/meetings` | execution:write | execution/routes/router.py:89 | **—** |
| execution | DELETE | `/execution/meetings/{meeting_id}` | execution:write | execution/routes/router.py:114 | **—** |
| execution | GET | `/execution/meetings/{meeting_id}` | execution:read | execution/routes/router.py:99 | **—** |
| execution | PATCH | `/execution/meetings/{meeting_id}` | execution:write | execution/routes/router.py:104 | **—** |
| execution | GET | `/work/projects` | execution:read | execution/routes/work.py:211 | work/use-work.ts |
| execution | POST | `/work/projects` | execution:write | execution/routes/work.py:226 | work/CreateProjectDialog.tsx |
| execution | DELETE | `/work/projects/{project_id}` | execution:write | execution/routes/work.py:257 | **—** |
| execution | GET | `/work/projects/{project_id}` | execution:read | execution/routes/work.py:238 | work/use-work.ts |
| execution | PATCH | `/work/projects/{project_id}` | execution:write | execution/routes/work.py:245 | **—** |
| execution | GET | `/work/projects/{project_id}/milestones` | execution:read | execution/routes/work.py:271 | **—** |
| execution | POST | `/work/projects/{project_id}/milestones` | execution:write | execution/routes/work.py:280 | work/Milestones.tsx |
| execution | DELETE | `/work/projects/{project_id}/milestones/{milestone_id}` | execution:write | execution/routes/work.py:307 | **—** |
| execution | PATCH | `/work/projects/{project_id}/milestones/{milestone_id}` | execution:write | execution/routes/work.py:294 | work/Milestones.tsx |
| execution | GET | `/work/tasks` | execution:read | execution/routes/work.py:98 | work/use-work.ts |
| execution | POST | `/work/tasks` | execution:write | execution/routes/work.py:125 | work/CreateTaskDialog.tsx, work/TaskRelations.tsx |
| execution | DELETE | `/work/tasks/{task_id}` | execution:write | execution/routes/work.py:201 | **—** |
| execution | GET | `/work/tasks/{task_id}` | execution:read | execution/routes/work.py:185 | work/use-work.ts |
| execution | PATCH | `/work/tasks/{task_id}` | execution:write | execution/routes/work.py:191 | work/use-work.ts |
| execution | GET | `/work/tasks/{task_id}/dependencies` | execution:read | execution/routes/work.py:135 | work/use-work.ts |
| execution | POST | `/work/tasks/{task_id}/dependencies` | execution:write | execution/routes/work.py:143 | work/TaskRelations.tsx |
| execution | DELETE | `/work/tasks/{task_id}/dependencies/{dependency_id}` | execution:write | execution/routes/work.py:158 | work/TaskRelations.tsx |
| execution | POST | `/work/tasks/{task_id}/reassign-requests` | execution:write | execution/routes/work.py:170 | work/ReassignDialog.tsx |
| execution | GET | `/work/workload` | execution:query | execution/routes/work.py:67 | work/use-work.ts |
| finance | GET | `/finance/budgets` | ●finance:read | finance/routes/router.py:236 | records/RecordCrud.tsx |
| finance | POST | `/finance/budgets` | ●finance:write | finance/routes/router.py:249 | records/RecordCrud.tsx |
| finance | GET | `/finance/budgets/status` | finance:query | finance/routes/router.py:227 | finance/FinanceLiteView.tsx |
| finance | DELETE | `/finance/budgets/{budget_id}` | ●finance:write | finance/routes/router.py:274 | records/RecordCrud.tsx |
| finance | GET | `/finance/budgets/{budget_id}` | ●finance:read | finance/routes/router.py:259 | finance/FinanceLiteView.tsx |
| finance | PATCH | `/finance/budgets/{budget_id}` | ●finance:write | finance/routes/router.py:264 | records/RecordCrud.tsx |
| finance | GET | `/finance/cash-flow-forecast` | ●finance:read | finance/routes/router.py:409 | **—** |
| finance | POST | `/finance/cash-flow-forecast/recompute` | ●finance:write | finance/routes/router.py:414 | **—** |
| finance | GET | `/finance/cash-positions` | ●finance:read | finance/routes/router.py:177 | finance/LineageDialog.tsx, finance/use-finance-drilldown.ts +1 |
| finance | POST | `/finance/cash-positions` | ●finance:write | finance/routes/router.py:188 | records/RecordCrud.tsx |
| finance | GET | `/finance/cash-positions/{position_id}` | ●finance:read | finance/routes/router.py:198 | **—** |
| finance | PATCH | `/finance/cash-positions/{position_id}` | ●finance:write | finance/routes/router.py:204 | records/RecordCrud.tsx |
| finance | GET | `/finance/dashboard` | finance:query | finance/routes/router.py:386 | dashboard/use-pillar.ts, finance/FinanceLiteView.tsx +1 |
| finance | GET | `/finance/expenses` | ●finance:read | finance/routes/router.py:131 | records/RecordCrud.tsx |
| finance | POST | `/finance/expenses` | ●finance:write | finance/routes/router.py:144 | records/RecordCrud.tsx |
| finance | DELETE | `/finance/expenses/{expense_id}` | ●finance:write | finance/routes/router.py:169 | records/RecordCrud.tsx |
| finance | GET | `/finance/expenses/{expense_id}` | ●finance:read | finance/routes/router.py:154 | **—** |
| finance | PATCH | `/finance/expenses/{expense_id}` | ●finance:write | finance/routes/router.py:159 | records/RecordCrud.tsx |
| finance | GET | `/finance/forecasts` | ●finance:read | finance/routes/router.py:282 | **—** |
| finance | POST | `/finance/forecasts` | ●finance:write | finance/routes/router.py:295 | **—** |
| finance | GET | `/finance/forecasts/{forecast_id}` | ●finance:read | finance/routes/router.py:305 | **—** |
| finance | PATCH | `/finance/forecasts/{forecast_id}` | ●finance:write | finance/routes/router.py:311 | **—** |
| finance | GET | `/finance/invoices` | ●finance:read | finance/routes/router.py:322 | finance/InvoicesView.tsx, finance/LineageDialog.tsx +1 |
| finance | POST | `/finance/invoices` | ●finance:write | finance/routes/router.py:337 | records/RecordCrud.tsx |
| finance | DELETE | `/finance/invoices/{invoice_id}` | ●finance:write | finance/routes/router.py:363 | records/RecordCrud.tsx |
| finance | GET | `/finance/invoices/{invoice_id}` | ●finance:read | finance/routes/router.py:347 | **—** |
| finance | PATCH | `/finance/invoices/{invoice_id}` | ●finance:write | finance/routes/router.py:353 | records/RecordCrud.tsx |
| finance | POST | `/finance/invoices/{invoice_id}/pay` | ●finance:write | finance/routes/router.py:370 | records/RecordCrud.tsx |
| finance | GET | `/finance/revenues` | ●finance:read | finance/routes/router.py:85 | records/RecordCrud.tsx |
| finance | POST | `/finance/revenues` | ●finance:write | finance/routes/router.py:98 | records/RecordCrud.tsx |
| finance | DELETE | `/finance/revenues/{revenue_id}` | ●finance:write | finance/routes/router.py:123 | records/RecordCrud.tsx |
| finance | GET | `/finance/revenues/{revenue_id}` | ●finance:read | finance/routes/router.py:108 | **—** |
| finance | PATCH | `/finance/revenues/{revenue_id}` | ●finance:write | finance/routes/router.py:113 | records/RecordCrud.tsx |
| finance | GET | `/finance/what-if/runway` | finance:query | finance/routes/router.py:395 | finance/FinanceLiteView.tsx |
| hr | GET | `/org/assignments` | ●hr:read | hr/routes/org.py:201 | admin/org/use-org.ts |
| hr | POST | `/org/assignments` | ●hr:admin | hr/routes/org.py:214 | admin/org/OrgForms.tsx |
| hr | PATCH | `/org/assignments/{assignment_id}` | ●hr:admin | hr/routes/org.py:228 | **—** |
| hr | GET | `/org/organizations` | ●hr:read | hr/routes/org.py:69 | admin/onboarding/use-onboarding.ts |
| hr | POST | `/org/organizations` | ●hr:admin | hr/routes/org.py:79 | admin/onboarding/CompanyStep.tsx |
| hr | DELETE | `/org/organizations/{organization_id}` | ●hr:admin | hr/routes/org.py:105 | **—** |
| hr | GET | `/org/organizations/{organization_id}` | ●hr:read | hr/routes/org.py:89 | **—** |
| hr | PATCH | `/org/organizations/{organization_id}` | ●hr:admin | hr/routes/org.py:94 | admin/onboarding/CompanyStep.tsx |
| hr | GET | `/org/positions` | ●hr:read | hr/routes/org.py:157 | admin/org/use-org.ts |
| hr | POST | `/org/positions` | ●hr:admin | hr/routes/org.py:168 | admin/PositionsView.tsx |
| hr | DELETE | `/org/positions/{position_id}` | ●hr:admin | hr/routes/org.py:193 | **—** |
| hr | GET | `/org/positions/{position_id}` | ●hr:read | hr/routes/org.py:178 | **—** |
| hr | PATCH | `/org/positions/{position_id}` | ●hr:admin | hr/routes/org.py:183 | admin/PositionsView.tsx |
| hr | GET | `/org/teams` | ●hr:read | hr/routes/org.py:113 | admin/org/use-org.ts |
| hr | POST | `/org/teams` | ●hr:admin | hr/routes/org.py:124 | admin/org/OrgForms.tsx |
| hr | DELETE | `/org/teams/{team_id}` | ●hr:admin | hr/routes/org.py:149 | admin/org/OrgView.tsx |
| hr | GET | `/org/teams/{team_id}` | ●hr:read | hr/routes/org.py:134 | **—** |
| hr | PATCH | `/org/teams/{team_id}` | ●hr:admin | hr/routes/org.py:139 | **—** |
| hr | GET | `/org/tree` | ●hr:read | hr/routes/org.py:243 | admin/org/use-org.ts, work/use-work.ts |
| hr | GET | `/hr/dashboard` | hr:query | hr/routes/router.py:73 | dashboard/use-pillar.ts |
| hr | GET | `/hr/departments` | ●hr:read | hr/routes/router.py:91 | admin/org/use-org.ts |
| hr | POST | `/hr/departments` | ●hr:admin | hr/routes/router.py:103 | admin/org/OrgForms.tsx |
| hr | DELETE | `/hr/departments/{department_id}` | ●hr:admin | hr/routes/router.py:131 | admin/org/OrgView.tsx |
| hr | GET | `/hr/departments/{department_id}` | ●hr:read | hr/routes/router.py:115 | **—** |
| hr | PATCH | `/hr/departments/{department_id}` | ●hr:admin | hr/routes/router.py:120 | admin/org/OrgForms.tsx |
| hr | GET | `/hr/employees` | ●hr:read | hr/routes/router.py:139 | hr/EmployeesView.tsx, records/RecordCrud.tsx |
| hr | POST | `/hr/employees` | ●hr:write | hr/routes/router.py:152 | records/RecordCrud.tsx |
| hr | DELETE | `/hr/employees/{employee_id}` | ●hr:write | hr/routes/router.py:177 | records/RecordCrud.tsx |
| hr | GET | `/hr/employees/{employee_id}` | ●hr:read | hr/routes/router.py:162 | **—** |
| hr | PATCH | `/hr/employees/{employee_id}` | ●hr:write | hr/routes/router.py:167 | records/RecordCrud.tsx |
| hr | GET | `/hr/employees/{employee_id}/salary-history` | ●hr:read | hr/routes/router.py:185 | **—** |
| hr | POST | `/hr/employees/{employee_id}/salary-history` | ●hr:write | hr/routes/router.py:194 | **—** |
| hr | GET | `/hr/hiring-plans` | ●hr:read | hr/routes/router.py:209 | records/RecordCrud.tsx |
| hr | POST | `/hr/hiring-plans` | ●hr:write | hr/routes/router.py:222 | records/RecordCrud.tsx |
| hr | DELETE | `/hr/hiring-plans/{plan_id}` | ●hr:write | hr/routes/router.py:247 | records/RecordCrud.tsx |
| hr | GET | `/hr/hiring-plans/{plan_id}` | ●hr:read | hr/routes/router.py:232 | **—** |
| hr | PATCH | `/hr/hiring-plans/{plan_id}` | ●hr:write | hr/routes/router.py:237 | records/RecordCrud.tsx |
| hr | POST | `/hr/hiring-plans/{plan_id}/approve` | hr:approve | hr/routes/router.py:266 | records/RecordCrud.tsx |
| hr | POST | `/hr/hiring-plans/{plan_id}/submit` | ●hr:write | hr/routes/router.py:255 | records/RecordCrud.tsx |
| hr | GET | `/hr/workload` | hr:query | hr/routes/router.py:82 | **—** |
| idp | GET | `/data-capture/document-types` | idp:read | idp/routes/data_capture.py:273 | capture/use-capture.ts |
| idp | PATCH | `/data-capture/document-types/{type_id}` | idp:admin | idp/routes/data_capture.py:281 | capture/admin/TypesTab.tsx |
| idp | GET | `/data-capture/documents/{document_id}/actions` | idp:read | idp/routes/data_capture.py:264 | capture/use-capture.ts |
| idp | POST | `/data-capture/documents/{document_id}/commit` | idp:write | idp/routes/data_capture.py:234 | capture/use-capture.ts |
| idp | GET | `/data-capture/documents/{document_id}/source` | idp:read | idp/routes/data_capture.py:221 | capture/use-capture.ts |
| idp | POST | `/data-capture/documents/{document_id}/undo` | idp:write | idp/routes/data_capture.py:249 | capture/use-capture.ts |
| idp | GET | `/data-capture/extraction-schemas` | idp:admin | idp/routes/data_capture.py:294 | capture/admin/RulesTab.tsx, capture/admin/SchemasTab.tsx |
| idp | POST | `/data-capture/extraction-schemas` | idp:admin | idp/routes/data_capture.py:304 | capture/admin/SchemasTab.tsx |
| idp | PATCH | `/data-capture/extraction-schemas/{schema_id}` | idp:admin | idp/routes/data_capture.py:317 | capture/admin/SchemaEditor.tsx |
| idp | POST | `/data-capture/extraction-schemas/{schema_id}/publish` | idp:admin | idp/routes/data_capture.py:329 | capture/admin/SchemasTab.tsx |
| idp | GET | `/data-capture/forms/{document_type}` | idp:write | idp/routes/data_capture.py:101 | capture/use-capture.ts |
| idp | POST | `/data-capture/imports` | idp:write | idp/routes/data_capture.py:135 | admin/onboarding/ImportStep.tsx, capture/DropZone.tsx |
| idp | GET | `/data-capture/imports/{batch_id}` | idp:read | idp/routes/data_capture.py:158 | capture/use-capture.ts |
| idp | GET | `/data-capture/imports/{batch_id}/error-file` | idp:read | idp/routes/data_capture.py:192 | capture/use-capture.ts |
| idp | PATCH | `/data-capture/imports/{batch_id}/mapping` | idp:write | idp/routes/data_capture.py:165 | admin/onboarding/ImportStep.tsx, capture/ImportWizard.tsx |
| idp | GET | `/data-capture/imports/{batch_id}/rows` | idp:read | idp/routes/data_capture.py:176 | capture/use-capture.ts |
| idp | POST | `/data-capture/imports/{batch_id}/submit` | idp:write | idp/routes/data_capture.py:205 | admin/onboarding/ImportStep.tsx, capture/ImportWizard.tsx |
| idp | GET | `/data-capture/inbox` | idp:read | idp/routes/data_capture.py:85 | capture/use-capture.ts |
| idp | GET | `/data-capture/incidents` | idp:approve | idp/routes/data_capture.py:393 | capture/admin/IncidentsTab.tsx |
| idp | POST | `/data-capture/incidents` | idp:approve | idp/routes/data_capture.py:380 | capture/IncidentDialog.tsx |
| idp | POST | `/data-capture/manual` | idp:write | idp/routes/data_capture.py:106 | capture/SchemaForm.tsx |
| idp | POST | `/data-capture/natural-language` | idp:write | idp/routes/data_capture.py:121 | execution/use-meetings.ts |
| idp | GET | `/data-capture/validation-rules` | idp:admin | idp/routes/data_capture.py:345 | capture/admin/RulesTab.tsx |
| idp | POST | `/data-capture/validation-rules` | idp:admin | idp/routes/data_capture.py:356 | capture/admin/RuleForm.tsx |
| idp | PATCH | `/data-capture/validation-rules/{rule_id}` | idp:admin | idp/routes/data_capture.py:369 | capture/admin/RulesTab.tsx |
| idp | GET | `/files/{storage_key:path}` | idp:read | idp/routes/files.py:35 | capture/source-view.ts (presigned→BFF) |
| idp | GET | `/lineage/{entity}/{record_id}` | idp:read | idp/routes/lineage.py:24 | capture/use-capture.ts |
| idp | POST | `/idp/documents` | idp:write | idp/routes/router.py:77 | capture/DropZone.tsx, idp/UploadButton.tsx |
| idp | GET | `/idp/documents/search` | idp:read | idp/routes/router.py:109 | knowledge/use-knowledge.ts |
| idp | GET | `/idp/documents/{document_id}` | idp:read | idp/routes/router.py:126 | capture/use-capture.ts, finance/LineageDialog.tsx +1 |
| idp | GET | `/idp/documents/{document_id}/extraction` | idp:read | idp/routes/router.py:138 | **—** |
| idp | PATCH | `/idp/documents/{document_id}/fields` | idp:approve | idp/routes/router.py:209 | idp/ReviewDetailView.tsx |
| idp | GET | `/idp/documents/{document_id}/review` | idp:approve | idp/routes/router.py:185 | idp/use-review.ts |
| idp | POST | `/idp/documents/{document_id}/review/approve` | idp:approve | idp/routes/router.py:227 | idp/ReviewDetailView.tsx |
| idp | POST | `/idp/documents/{document_id}/review/open` | idp:approve | idp/routes/router.py:196 | idp/use-review.ts |
| idp | POST | `/idp/documents/{document_id}/review/reassign` | idp:approve | idp/routes/router.py:280 | **—** |
| idp | POST | `/idp/documents/{document_id}/review/reject` | idp:approve | idp/routes/router.py:255 | idp/ReviewDetailView.tsx |
| idp | POST | `/idp/documents/{document_id}/review/release` | idp:approve | idp/routes/router.py:268 | idp/use-review.ts |
| idp | GET | `/idp/review-queue` | idp:approve | idp/routes/router.py:157 | idp/ReviewQueueView.tsx |
| idp | POST | `/idp/review-queue/merge` | idp:approve | idp/routes/router.py:299 | **—** |
| platform | GET | `/health` | authenticated/public | platform/routes/health.py:41 | **—** |
| platform | GET | `/integrations/providers` | execution:read | platform/routes/integrations.py:31 | admin/use-integrations.ts |
| platform | GET | `/integrations/{provider}/callback` | execution:write | platform/routes/integrations.py:47 | **—** |
| platform | POST | `/integrations/{provider}/connect` | execution:write | platform/routes/integrations.py:36 | admin/use-integrations.ts |
| platform | DELETE | `/integrations/{provider}/disconnect` | execution:write | platform/routes/integrations.py:61 | admin/use-integrations.ts |
| platform | GET | `/notifications` | authenticated/public | platform/routes/notifications.py:28 | components/shell/NotificationBell.tsx |
| platform | GET | `/notifications/preferences` | authenticated/public | platform/routes/notifications.py:52 | components/shell/NotificationBell.tsx |
| platform | PATCH | `/notifications/preferences` | authenticated/public | platform/routes/notifications.py:57 | components/shell/NotificationBell.tsx |
| platform | POST | `/notifications/read-all` | authenticated/public | platform/routes/notifications.py:42 | components/shell/NotificationBell.tsx |
| platform | POST | `/notifications/{notification_id}/read` | authenticated/public | platform/routes/notifications.py:64 | components/shell/NotificationBell.tsx |
| platform | GET | `/platform/onboarding` | platform:read | platform/routes/onboarding.py:23 | admin/onboarding/use-onboarding.ts |
| platform | PATCH | `/platform/onboarding` | platform:admin | platform/routes/onboarding.py:28 | admin/onboarding/use-onboarding.ts |
| platform | GET | `/platform/audit-logs` | platform:read | platform/routes/router.py:45 | admin/AuditLogView.tsx, work/use-work.ts |
| platform | GET | `/platform/dead-letters` | platform:admin | platform/routes/router.py:72 | **—** |
| platform | POST | `/platform/dead-letters/{id}/replay` | platform:admin | platform/routes/router.py:85 | **—** |
| platform | GET | `/workflow/approval-requests` | platform:approve | platform/routes/workflow.py:29 | work/use-work.ts |
| platform | GET | `/workflow/approval-requests/{id}` | platform:approve | platform/routes/workflow.py:49 | work/use-work.ts |
| platform | POST | `/workflow/approval-requests/{id}/decide` | platform:approve | platform/routes/workflow.py:57 | work/ApprovalDetail.tsx |
| product | GET | `/product/features` | product:read | product/routes/catalog.py:77 | **—** |
| product | POST | `/product/features` | ●product:write | product/routes/catalog.py:90 | **—** |
| product | DELETE | `/product/features/{feature_id}` | ●product:write | product/routes/catalog.py:115 | **—** |
| product | GET | `/product/features/{feature_id}` | product:read | product/routes/catalog.py:100 | **—** |
| product | PATCH | `/product/features/{feature_id}` | ●product:write | product/routes/catalog.py:105 | **—** |
| product | GET | `/product/products` | product:read | product/routes/catalog.py:31 | **—** |
| product | POST | `/product/products` | ●product:write | product/routes/catalog.py:44 | **—** |
| product | DELETE | `/product/products/{product_id}` | ●product:write | product/routes/catalog.py:69 | **—** |
| product | GET | `/product/products/{product_id}` | product:read | product/routes/catalog.py:54 | **—** |
| product | PATCH | `/product/products/{product_id}` | ●product:write | product/routes/catalog.py:59 | **—** |
| product | GET | `/product/dashboard` | product:query | product/routes/metrics.py:50 | dashboard/use-pillar.ts |
| product | GET | `/product/products/{product_id}/metrics` | product:query | product/routes/metrics.py:19 | **—** |
| product | POST | `/product/products/{product_id}/metrics` | ●product:write | product/routes/metrics.py:28 | **—** |
| product | GET | `/product/releases` | product:read | product/routes/planning.py:76 | **—** |
| product | POST | `/product/releases` | ●product:write | product/routes/planning.py:88 | **—** |
| product | GET | `/product/releases/{release_id}` | product:read | product/routes/planning.py:98 | **—** |
| product | PATCH | `/product/releases/{release_id}` | ●product:write | product/routes/planning.py:103 | **—** |
| product | GET | `/product/roadmap-items` | product:read | product/routes/planning.py:30 | **—** |
| product | POST | `/product/roadmap-items` | ●product:write | product/routes/planning.py:43 | **—** |
| product | DELETE | `/product/roadmap-items/{item_id}` | ●product:write | product/routes/planning.py:68 | **—** |
| product | GET | `/product/roadmap-items/{item_id}` | product:read | product/routes/planning.py:53 | **—** |
| product | PATCH | `/product/roadmap-items/{item_id}` | ●product:write | product/routes/planning.py:58 | **—** |
| risk | GET | `/risk/dashboard` | risk:query | risk/routes/router.py:59 | dashboard/use-pillar.ts |
| risk | GET | `/risk/mitigations` | risk:read | risk/routes/router.py:157 | **—** |
| risk | POST | `/risk/mitigations` | ●risk:write | risk/routes/router.py:170 | **—** |
| risk | GET | `/risk/mitigations/{mitigation_id}` | risk:read | risk/routes/router.py:180 | **—** |
| risk | PATCH | `/risk/mitigations/{mitigation_id}` | ●risk:write | risk/routes/router.py:185 | **—** |
| risk | GET | `/risk/risks` | risk:read | risk/routes/router.py:69 | **—** |
| risk | POST | `/risk/risks` | ●risk:write | risk/routes/router.py:87 | **—** |
| risk | GET | `/risk/risks/{risk_id}` | risk:read | risk/routes/router.py:97 | **—** |
| risk | PATCH | `/risk/risks/{risk_id}` | ●risk:write | risk/routes/router.py:102 | **—** |
| risk | POST | `/risk/risks/{risk_id}/accept` | risk:approve | risk/routes/router.py:131 | **—** |
| risk | GET | `/risk/risks/{risk_id}/assessments` | risk:read | risk/routes/router.py:113 | **—** |
| risk | POST | `/risk/risks/{risk_id}/assessments` | ●risk:write | risk/routes/router.py:118 | **—** |
| risk | POST | `/risk/risks/{risk_id}/status` | ●risk:write | risk/routes/router.py:144 | **—** |
| risk | POST | `/risk/scenarios` | risk:query | risk/routes/router.py:197 | **—** |
| sales | GET | `/sales/clients` | ●sales:read | sales/routes/router.py:79 | crm/use-crm.ts, records/RecordCrud.tsx |
| sales | POST | `/sales/clients` | ●sales:write | sales/routes/router.py:89 | records/RecordCrud.tsx |
| sales | DELETE | `/sales/clients/{client_id}` | ●sales:write | sales/routes/router.py:114 | records/RecordCrud.tsx |
| sales | GET | `/sales/clients/{client_id}` | ●sales:read | sales/routes/router.py:99 | crm/use-crm.ts |
| sales | PATCH | `/sales/clients/{client_id}` | ●sales:write | sales/routes/router.py:104 | records/RecordCrud.tsx |
| sales | GET | `/sales/contracts` | ●sales:read | sales/routes/router.py:259 | crm/use-crm.ts, records/RecordCrud.tsx |
| sales | POST | `/sales/contracts` | ●sales:write | sales/routes/router.py:275 | records/RecordCrud.tsx |
| sales | DELETE | `/sales/contracts/{contract_id}` | ●sales:write | sales/routes/router.py:300 | records/RecordCrud.tsx |
| sales | GET | `/sales/contracts/{contract_id}` | ●sales:read | sales/routes/router.py:285 | **—** |
| sales | PATCH | `/sales/contracts/{contract_id}` | ●sales:write | sales/routes/router.py:290 | records/RecordCrud.tsx |
| sales | GET | `/sales/dashboard` | sales:query | sales/routes/router.py:252 | dashboard/use-pillar.ts, sales/SalesPipelineView.tsx |
| sales | GET | `/sales/deals` | ●sales:read | sales/routes/router.py:122 | crm/use-crm.ts, records/RecordCrud.tsx |
| sales | POST | `/sales/deals` | ●sales:write | sales/routes/router.py:139 | records/RecordCrud.tsx |
| sales | DELETE | `/sales/deals/{deal_id}` | ●sales:write | sales/routes/router.py:164 | records/RecordCrud.tsx |
| sales | GET | `/sales/deals/{deal_id}` | ●sales:read | sales/routes/router.py:149 | crm/use-crm.ts |
| sales | PATCH | `/sales/deals/{deal_id}` | ●sales:write | sales/routes/router.py:154 | records/RecordCrud.tsx |
| sales | POST | `/sales/deals/{deal_id}/stage` | ●sales:write | sales/routes/router.py:172 | crm/use-crm.ts, records/RecordCrud.tsx |
| sales | GET | `/sales/deals/{deal_id}/stage-history` | ●sales:read | sales/routes/router.py:184 | crm/use-crm.ts |
| sales | GET | `/sales/performance` | sales:query | sales/routes/router.py:245 | crm/use-crm.ts |
| sales | GET | `/sales/pipeline` | sales:query | sales/routes/router.py:238 | crm/use-crm.ts, sales/SalesPipelineView.tsx |
| sales | GET | `/sales/targets` | ●sales:read | sales/routes/router.py:194 | records/RecordCrud.tsx |
| sales | POST | `/sales/targets` | ●sales:write | sales/routes/router.py:205 | records/RecordCrud.tsx |
| sales | DELETE | `/sales/targets/{target_id}` | ●sales:write | sales/routes/router.py:230 | records/RecordCrud.tsx |
| sales | GET | `/sales/targets/{target_id}` | ●sales:read | sales/routes/router.py:215 | **—** |
| sales | PATCH | `/sales/targets/{target_id}` | ●sales:write | sales/routes/router.py:220 | records/RecordCrud.tsx |
