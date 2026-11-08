# Aureon v4 — Báo cáo audit Phase 0–1 và danh sách quyết định

> Ngày 2026-11-05 · Nhánh `v3/m8-crm` @ `9cad717` · Phương thức: chỉ đọc code, tài liệu, DB; duyệt UI bằng 10 tài khoản demo.
> **Chưa sửa code, tài liệu hay dữ liệu nào.** Chưa push, chưa deploy, chưa migration.
> **Không commit file này lên repo khi C-1, C-2 chưa xử lý:** repo đang công khai. File chưa được gitignore.

## 1. Kết luận

**Nền kỹ thuật tốt, nhưng sản phẩm chưa sẵn sàng vận hành thật.** Cấu trúc code sạch và test dày. Vấn đề nằm ở 4 chỗ:

1. **Bảo mật vận hành:** ai vào được cổng 3000 cũng đăng nhập được bằng tài khoản demo, gồm admin và CEO.
2. **Niềm tin vào số liệu:** hai đồng hồ nghiệp vụ, một metric hai công thức, số 0 cứng trên Home, CRM và Tài chính lệch nhau.
3. **Vòng lặp chưa đóng:** Capture → Action → Measurement chỉ chạy trên seed. Dữ liệu mới không vào KPI, Briefing không sinh lại.
4. **AI bị báo cáo quá mức:** thực tế mới có **1 lượt gọi model thật** trên DB chính. Chat đang trả lời từ kịch bản viết sẵn.

**Hướng đề xuất cho v4:** không viết lại. Làm cứng vận hành → sửa số → đóng vòng lặp → dựng lại design system có mục tiêu → hoàn thiện CRM → làm AI thật có đo lường.

## 2. Baseline đã kiểm tra

| Mục | Kết quả | So với thông tin ban đầu |
|---|---|---|
| Nhánh / HEAD | `v3/m8-crm` @ `9cad717` | Khớp |
| Chưa push | **33 commit**, nhánh M7 và M8 không có trên remote | Báo cáo gốc chỉ ghi 2 commit |
| Local `main` | Sau `origin/main` 12 commit; `origin/main` là tổ tiên của HEAD | Không xung đột |
| DB revision | `0027_external_event_link_c19`, khớp head trên đĩa; M8 không có migration | Khớp |
| Stack | 10/10 healthy, `/health` trả `3.0.0` | Khớp |
| Chế độ chạy | `DEMO_MODE=true`, `AI_DEMO_REPLAY` bật, `DEMO_LOGIN_AUTOFILL=true` | **Khác:** báo cáo gọi đây là production |
| R-DEC-168 | Khóa JWT vẫn là bản 2026-10-21, host và container khớp nhau | Xác nhận còn mở |
| Repo | GitHub API: `public` | Quan trọng cho C-2 |
| Working tree | User xóa `docs/_archive/v2.1` (17 file), `docs/handover` (4 file); `.prompt/`, `deliverables/GITLEAKS-AUDIT.md` chưa track; `docs/_reference/` bị gitignore | Mục `docs/handover` là mới so với M8 plan |
| Dữ liệu chính | 154 nhân sự, 30 deal, 56 hóa đơn, 11 user: đều là seed | Không thấy thao tác nghiệp vụ thật từ 04/11 |

**Full gate trên DB cô lập (Postgres + Redis tạm trên tmpfs, đã xóa sau khi chạy):**

| Gate | Kết quả |
|---|---|
| ruff, format, mypy strict (389 file) | Pass |
| `alembic upgrade head` + seed từ DB rỗng | Pass |
| pytest | **1451 passed**, 0 failed, 54 warning, 10 phút 48 giây |
| contract | **44 passed** |
| ESLint, tsc | Pass |
| Vitest | **487 passed** (55 file) |
| Production build web | Pass |

**Không chạy trong phiên này:** E2E Playwright (số gần nhất 91/91 là theo báo cáo M8), test `live`, `alembic downgrade` round-trip, `pip-audit`/trivy (chưa có công cụ).

**Cảnh báo:** `.env` trỏ `DATABASE_URL` vào DB chính. Chạy `uv run pytest` trần trên máy này sẽ đụng DB chính (TD-01).

## 3. Phát hiện chính

Cột **KC**: ✅ = tôi đã tự kiểm chứng trực tiếp; ◐ = chuyên gia kiểm ở mức code, tôi chưa lặp lại.

### 3.1. Critical

| ID | Phát hiện | Bằng chứng | KC |
|---|---|---|---|
| C-1 | Endpoint ẩn danh trả mật khẩu demo; `demo:"true"` + mật khẩu rỗng cũng đăng nhập được, web publish `0.0.0.0:3000` | `apps/web/src/app/api/demo-credentials/route.ts:14`, `lib/auth.ts:68`; gọi thử trên stack: HTTP 200 có dữ liệu | ✅ |
| C-2 | Cả 11 `DEMO_*_PASSWORD` hiện tại (5 giá trị, 17 ký tự) nằm trong history công khai từ `e6a887f`; `app.seed` ghi đè và kích hoạt lại tài khoản mỗi lần API khởi động | `git log -S` trên `origin/main`: 4 commit; `docker-compose.full.yml:124`, `seed/auth_seed.py:152-155`. Trái `GITLEAKS-AUDIT.md` §1 và R-DEC-167 | ✅ |
| F-C1 | IDP gửi tài liệu nhạy cảm lên cloud: mọi file gán cố định mức 2 (INTERNAL) trước khi biết loại; extractor gửi text thô, không lọc PII. Bảng lương, CCCD, STK đi qua OmniRoute. DB chính chưa có lượt roster | `idp/services/upload_service.py:164`, `pipeline.py:128`, `extractor.py:139` | ✅ phần gán mức |
| F-C2 | Replay đang bật: chat khớp câu hỏi và trả nhận định viết sẵn ("Dòng tiền ổn") bất kể số thật, bỏ qua LLM, grounding | `ai/services/chat_service.py:116-120`, `demo_replay.py:47`, cờ trong container | ✅ |
| F1 | Ngày nghiệp vụ đóng băng 2026-10-20: dữ liệu mới không vào KPI, Briefing không sinh lại | `core/clock.py:13`, `ai/services/briefing_service.py:89` | ✅ |
| F2 | Hai đồng hồ: Sales, HR dùng ngày thật; Finance, Metric, Execution dùng ngày đóng băng | `sales/services/analytics.py:80`, `hr/services/hr_service.py:83` | ✅ |
| F3 | Scope `r`/`d` không được thực thi ở Finance, Sales: REV đọc toàn bộ thu chi và deal; MGR phòng bất kỳ ghi được hóa đơn, ngân sách. `ROLE_SCOPES` chỉ dùng cho seed và hiển thị | `auth/permission_matrix.py:160`, `finance/routes/router.py:86` | ✅ code, chưa chạy với token |
| F5 | `METRIC-FIN-01` hai công thức: store 86,4% YELLOW, `/finance/dashboard` tính YoY với status cứng `ok` | `finance/.../analytics_service.py:237` | ✅ |
| F6 | Số cứng trên Home Department/Employee: OKR 0/0, 0 KPI, 0 KR | `dashboard/services/reporting_service.py:104,142` | ✅ |
| F7 | Deal thắng không tạo revenue, invoice, contract. T9: 8,7 tỷ CRM vs 25,5 tỷ Tài chính | `audit-product.md` §4.3 | ◐ |
| TD-01 | pytest không có DB riêng; test relay có thể đánh dấu event thật là `PUBLISHED` | `.env` trỏ DB chính; `tests/events/test_celery_tasks.py:80` | ✅ cấu hình |
| TD-02 | CI backend bị `skipped` từ 21/10 vì gitleaks đỏ; `main` không có branch protection, PR #6 merge khi CI đỏ | Run `41573404841`: `api = skipped`; `ci.yml:83` | ✅ |

### 3.2. High (chọn lọc)

| Mảng | Phát hiện | KC |
|---|---|---|
| Bảo mật | H-1 khóa RS256 chưa xoay, và xoay không buộc đăng nhập lại: refresh token vẫn sống, `kid` không được đọc khi verify. R-DEC-168 mô tả sai hiệu ứng | ✅ phần mtime |
| Bảo mật | H-2 Redis không auth, Postgres (app dùng superuser), Ollama, MinIO, ClamAV, Mailpit đều bind `0.0.0.0` | ✅ cổng |
| Bảo mật | H-3 EP-DC-03 `/extraction` trả lương, CCCD, STK không mask; MGR, ADM đọc được mức 4 | ✅ không có mask ở `query_service.py` |
| Bảo mật | H-5 không có rate limit ở đâu; H-6 không TLS, cookie không `Secure` | ◐ |
| Kiến trúc | TD-03 `invoice_service.pay()` đọc rồi ghi, không khóa dòng: thanh toán đồng thời mất cập nhật tiền | ✅ |
| Kiến trúc | TD-07 lỗi pipeline IDP ngoài `AIError` làm tài liệu kẹt `UPLOADED` im lặng; TD-08 không có backup tự động; TD-09 idempotency get-rồi-set, 15/88 route không replay | ◐ |
| AI | F-H1 grounding bị vượt: số bịa viết bằng chữ, dung sai 2%; F-H2 RAG làm hỏng cả lượt chat khi live; F-H3 OCR PDF scan lỗi bị nuốt; F-H4 `source_location` luôn trang 1 | ◐ |
| AI | F-H6 6/14 doc type; F-H8 chỉ 12/54 tool dùng được qua chat; F-H11 ceiling tool ngược; F-H12 injection gián tiếp dẫn tới `create_task` L3; F-H13 chưa từng đo độ chính xác với model thật | ◐ |
| Sản phẩm | Reviewer không có đường vào hàng chờ (U-01); CFO thấy mã băm thay tên phòng (U-02); Decision Log không có đường ghi; Strategy không có UI | ◐ |
| Sản phẩm | BRD_Newfeature: 94 Must, xong 25, một phần 25, chặn bởi R-DEC-176 36, làm được ngay 7, chưa xác minh 1. Bảng M8 lạc quan ở 10 mục | ◐ |
| Vai trò | Thiết kế ngược: MGR có `finance/sales/product/risk:write` mọi phòng; EMP không có gì theo khối; 30/30 deal thuộc `sales@` | ✅ matrix |
| UI | Tràn ngang 36/332 trang-role ở 390 px; 0/34 bảng sắp xếp được; không có tab bar mobile; Employee 1,8 và Reviewer 1,4 điểm | ◐ |
| Tài liệu | 244 định nghĩa `DEC-*` chỉ còn trong archive đang xóa; 13 có 0 định nghĩa trong khi doc và code tham chiếu ~1.170 lần | ✅ |
| Tài liệu | 12 khai sai version 8 file; canonical không được version; "Aureon v4" chưa được định nghĩa ở đâu | ◐ |

### 3.3. AI: nói thật được gì

| Có bằng chứng | Không được quảng cáo |
|---|---|
| Trích xuất hóa đơn PDF có text layer bằng model thật (1 lượt, đang chờ review) | "Dữ liệu mật không rời on-prem" ở IDP |
| Mọi LLM call qua gateway có log token, chi phí | "AI không bịa số" như một bảo đảm |
| Lọc tool theo quyền, IDP không có tool, không lưu prompt thô | Mọi con số độ chính xác |
| Trường trọng yếu luôn qua người | RAG, STT, streaming thật, OCR PDF scan, 14 doc type, 54 tool, multi-agent |

Briefing là snapshot, không dùng LLM, nhưng đang gắn nhãn `source=AI`. Insight là template. Chat live, autonomy, undo, OCR ảnh: **chưa kiểm chứng**.

### 3.4. Điểm tốt nên giữ

- 0 vi phạm import giữa module, 0 chu trình; 0/123 FK thiếu index; model khớp catalog; 27/27 migration có downgrade; tiền là BIGINT.
- RBAC 328/328 route có guard, đúng 3 route public; JWT pin RS256, kiểm `iss`/`aud`, refresh rotation có phát hiện tái sử dụng.
- Không có SQL injection, XSS sink, SSRF, path traversal, open redirect. FE không gọi route không tồn tại (0), không fallback dữ liệu giả.
- Kill switch thực thi ở server; người duyệt ≠ người yêu cầu; i18n khớp 100% key; token màu gần như sạch.

## 4. Định hướng Aureon v4 (bản nháp, chờ D-02)

**Tầm nhìn đề xuất:** giữ *One Enterprise. One Source of Truth. One AI Operating Layer*; đổi trọng tâm từ "demo đủ tính năng" sang **"vận hành thật được, số tin được, AI đo được"**.

**Phân loại tính năng:**

| Loại | Tính năng |
|---|---|
| Core | Executive Home + Metric Store + lineage; Data Capture C1–C5 + Review + Action Registry; AI Chat có grounding + Tool Registry + Autonomy + Kill switch; Task/Project/Workload/Approval; KPI/OKR/Check-in; Finance Lite; Sales Pipeline; RBAC/Auth/Audit; Decision Log |
| Important | Daily Briefing, Insight, Reporting, Calendar, Meeting → Action, Knowledge, Org admin, Onboarding, Notification |
| Optional | AI Evaluation, Acceptance G1–G4, What-if runway, 5-trụ F.O.C.U.S, tile preferences |
| Deprecated | `DashboardView`, `PillarCard`, 10 role F.O.C.U.S + `require_role`, `InvoicesView`/`EmployeesView` (gộp vào records), MinIO nếu chốt D-12, schema `public` tàn dư |
| Blocked | Lead/Contact/Activity/Forecast (R-DEC-176); Product + Risk UI (R-DEC-16); STT (R-DEC-166); xoay khóa, history Git |

**Roadmap đề xuất** (ước lượng thô, cần xác nhận khi lập kế hoạch chi tiết):

| Phase | Mục tiêu | Nội dung | Cổng hoàn thành | Ước lượng |
|---|---|---|---|---|
| V4.0 Làm cứng | Không còn đường vào trái phép | D-04, D-05; tách DB test + guard; sửa CI + `.gitleaks.toml`; rate limit, security headers, TLS; role DB thường; backup tự động; di trú 244 DEC | Không còn Critical bảo mật; CI backend chạy lại | 1–2 tuần |
| V4.1 Số tin được | Cùng một câu hỏi, một đáp án | Một đồng hồ; thực thi scope; FIN-01; Home thật; funnel; ID thô, enum, P04; tắt replay; sửa F-C1, ceiling, grounding | Test ma trận role × route; đối chiếu số giữa các màn | 2–3 tuần |
| V4.2 Đóng vòng lặp | Dữ liệu mới chạy hết vòng | Deal → Contract/Revenue; danh bạ tối thiểu; Decision Log; Strategy UI; 9 ACT; race thanh toán; pipeline IDP chịu lỗi | E2E: dữ liệu mới → KPI → Briefing → hành động | 3–4 tuần |
| V4.3 Design system | Một ngôn ngữ giao diện | Token, DataTable, FormField, PageHeader, shell mobile, nav theo role, Home theo role, bàn Reviewer, migration trang | 0 tràn 390 px; bảng sắp xếp được; a11y | 12–17 tuần, chạy song song |
| V4.4 CRM đầy đủ | Đủ Must BRD_Newfeature | R-DEC-176: migration chỉ thêm; 02/05/10 trước; role theo khối | 94 Must có TC | Sau D-08 |
| V4.5 AI thật | AI đo được | Bộ nhãn vàng + đo accuracy; streaming thật; bộ nhớ chat; RAG; doc type; đa provider | Số accuracy thật theo doc type | 4–6 tuần |
| V4.6 Release | Sẵn sàng phát hành | Spec, migration plan, deploy/rollback checklist, release notes | Toàn bộ gate + E2E | 1–2 tuần |

Tài liệu: giữ số 00–14 vì code và test trích `10 §7.2`; viết lại 00, 01, 12, README; thêm `15-CRM-SPEC`, `16-OPERATIONS`, `STATUS.md`, `_reference/MANIFEST.md`, `docs/_history/`. Danh sách delete/archive ở phụ lục `audit-docs.md` §6 (chỉ là đề xuất).

## 5. Danh sách quyết định

Trả lời ngắn được, ví dụ: `D-01 demo; D-02 A; D-03 A; còn lại theo đề xuất`.

### Nhóm A — cần trước khi làm bất cứ gì

**D-01. Stack hiện tại có phải production thật không?**
- *Bằng chứng:* `DEMO_MODE=true`, ngày đóng băng 20/10, dữ liệu đều là seed, chạy trên WSL, nhưng M8 plan gọi là production.
- *A — Là demo/staging:* giữ, làm cứng, dựng profile production riêng. Ít rủi ro, nhưng cần thêm môi trường.
- *B — Là production:* C-1, C-2 thành sự cố cần xử lý ngay; phải rà có ai đã truy cập.
- **Đề xuất:** A, kèm validator chặn khởi động khi profile production còn cờ demo.
- **Câu hỏi:** có người dùng hoặc dữ liệu thật nào trên stack này không? Cổng 3000 có mở ra ngoài không?

**D-02. "Aureon v4" là gì?**
- *Bằng chứng:* không tài liệu nào định nghĩa; BRD vẫn là v1.1.
- *A — v3 hoàn thiện:* giữ phạm vi đã duyệt + CRM, ưu tiên vận hành thật. Nhanh, ít rủi ro.
- *B — Sản phẩm mở rộng:* thêm P1/P2 hoặc SaaS đa tenant. Lớn hơn nhiều, cần BRD mới.
- **Đề xuất:** A, ghi thành R-DEC.

**D-03. Quyền cho tác tử trong v4 so với CLAUDE.md**
- *Bằng chứng:* yêu cầu của bạn cho phép sửa version/status, xóa tài liệu; CLAUDE.md §6.3 mục 5–6, §6.6 cấm, và ghi rõ quy tắc vận hành thắng khi mâu thuẫn. File này cũng có hơn 20 khẳng định đã cũ.
- *A:* tạo một R-DEC ủy quyền (phạm vi, thời hạn, kiểu DEC-124) và cho phép tôi đề xuất bản CLAUDE.md mới để bạn duyệt. Rõ ràng, audit được.
- *B:* tôi giữ nguyên quy tắc cũ, mọi thay đổi doc đều chờ bạn. Chậm.
- **Đề xuất:** A.

### Nhóm B — bảo mật khẩn, cần bạn cho phép chạm stack

**D-04. Xử lý C-1, C-2, H-1, H-2**
- *Gói đề xuất, làm trong một cửa sổ bảo trì:* (1) tắt `DEMO_LOGIN_AUTOFILL`, bỏ nhánh `demo`; (2) tách `app.seed` khỏi lệnh `api`; (3) đổi cả 11 mật khẩu demo; (4) xoay RS256 + `NEXTAUTH_SECRET` + thu hồi mọi refresh token; (5) bỏ `ports:` của Redis, Postgres, Ollama, MinIO, ClamAV, Mailpit hoặc bind `127.0.0.1`.
- *Tác động:* mọi phiên bị đăng xuất; test/E2E phụ thuộc mật khẩu demo phải đổi env.
- *Thay thế:* chỉ làm (1)–(3), hoãn xoay khóa. Không khuyến nghị vì R-DEC-168 đang blocking.
- **Câu hỏi:** chấp thuận gói này không, và chạy lúc nào? Bạn tự xoay khóa hay giao tôi theo kế hoạch riêng?

**D-05. History Git chứa mật khẩu**
- *A — Đổi mật khẩu, không rewrite:* giá trị cũ thành vô dụng. An toàn nhất, không phá ai.
- *B — Rewrite + force-push:* không xóa được bản đã bị fork/cache, phá các nhánh và worktree.
- *C — Chuyển repo private:* giảm phơi bày về sau, không thu hồi được quá khứ.
- **Đề xuất:** A + C; sửa `GITLEAKS-AUDIT.md` §1, §7 và R-DEC-167; thêm `.gitleaks.toml` để gỡ CI.

**D-06. Ai làm chủ nguồn và file đã xóa**
- `docs/_reference/` bị `.gitignore:53` loại trừ: 4 tài liệu canonical chỉ có trên máy này. *Đề xuất:* commit sau khi repo private; trước đó thêm `MANIFEST.md` + sao lưu.
- `BRD_Newfeature` chưa được khai là canonical, và mâu thuẫn BRD ở 50 điểm (S-01..S-50). *Đề xuất:* canonical riêng cho domain Sales, thắng D17 qua R-DEC, các domain khác giữ BRD v1.1.
- Đề nghị **chưa commit** việc xóa `docs/_archive/v2.1` và `docs/handover`: trước đó di trú 244 DEC sang `docs/4.GOVERNANCE/`, chuyển runbook sang `16-OPERATIONS`, sửa tham chiếu trong `retention_service.py:4,67`, `check_env.sh:4`.

### Nhóm C — nghiệp vụ, RBAC, schema

**D-07. Thực thi scope và thiết kế lại role**
- Spec `02` §5.3 đã định scope `d`/`r` nhưng code không thực thi. *Đề xuất:* thực thi đúng spec cho REV, MGR (không đổi spec); làm test ma trận role × route.
- MGR có quyền ghi tài chính mọi phòng, EMP không có quyền theo khối. *Đề xuất:* MGR chỉ trong phòng; thêm permission EMP theo khối qua R-DEC riêng; thêm một endpoint danh bạ tối thiểu (giải được 5 vướng, R-DEC-169).
- Seed thêm tài khoản Sales MGR/EMP, Finance EMP, HR EMP, Risk DIR.

**D-08. R-DEC-176 (10 điểm a–j, M8 plan §5.2), S-26, S-30**
- *Đề xuất:* chấp nhận toàn bộ phương án mặc định a–j; CEO chỉ đọc Sales (giữ R-DEC-175); tách Stage / Forecast Category / Funnel step; bổ sung tool + event còn thiếu trước khi migration. Migration chỉ thêm, cập nhật 02/05/10 trước.

**D-09. Nguồn số liệu**
- *Doanh thu thật:* đề xuất Tài chính là nguồn duy nhất; deal thắng sinh contract và doanh thu dự kiến, Tài chính xác nhận.
- *FIN-01:* giữ công thức store (đạt so với kế hoạch), đổi tên chỉ số YoY.
- *Funnel:* code đúng BRD §2.8 Method A nhưng ra 166,7%, −66,7%, người đọc không dùng được. Đề xuất đổi sang phễu tích lũy từ `deal_stage_history`; đây là thay đổi so với BRD nên cần bạn duyệt.
- *Chỉ tiêu:* Q4 20 tỷ vs tổng tháng 85 tỷ, bạn xác nhận số đúng.

**D-10. MFA, SSO, rate limit**
- BRD P0, spec đã khóa, code chưa có, chưa có quyết định hạ ưu tiên.
- *Đề xuất:* rate limit + đổi/reset mật khẩu ở V4.0 (không cần dependency mới); MFA TOTP V4.1; SSO sau v4. Cần R-DEC vì đổi ưu tiên P0.

**D-11. AI**
- Tắt replay ở mọi môi trường không phải demo (F-C2).
- IDP: mặc định CONFIDENTIAL cho tới khi phân loại xong, phân loại bằng model local, roster không bao giờ lên cloud (F-C1). Hiệu năng Ollama chưa đo, cần thử trước.
- Đóng R-DEC-164 (đang open, blocking) và đặt ngân sách đo bộ nhãn vàng.

**D-12. Hạ tầng**
- *MinIO:* không có client nào trong code. Đề xuất gỡ container, giữ file system + backup, ghi DEC; viết adapter khi triển khai nhiều node.
- *`tenant_id`:* 22 bảng thiếu. Đề xuất giữ single-tenant, chỉnh `05` cho khớp, không đổi schema.
- *Schema `public`:* 13 bảng tàn dư v1, có `users.password_hash`. Đề xuất dump lưu trữ rồi DROP trong cửa sổ bảo trì, có migration + rollback.

**D-13. UI/UX**
- *Kết luận:* không redesign toàn bộ. Dựng lại design system có mục tiêu + page template, thiết kế mới 3 vùng: Home theo role, shell mobile, bàn Reviewer.
- *Cần chốt:* màu `primary` (OQ-06-01); Review là mục nav riêng (đề xuất có); "Khối của tôi" thay `/business` cho DIR; API trả mã + i18n thay câu tiếng Việt (đổi contract `10`).
- *Dependency:* `@radix-ui/react-tabs`, `@tanstack/react-table`, date picker, `cmdk` mỗi mục cần một DEC. Đề xuất: Tabs và cmdk có; bảng tự viết trên TanStack nếu 34 bảng cần sort server-side.

## 6. Tác động của chính audit lên hệ thống

| Việc | Tác động |
|---|---|
| Duyệt UI 10 tài khoản | ~28 lượt đăng nhập tạo dòng `auth.login` trong audit, đổi "đăng nhập gần nhất"; phiên không đăng xuất nên tồn tại tới khi hết hạn. 1 POST `review/open` bị chặn. GET phía server có ghi hay không: chưa xác minh |
| Gọi thử `POST /api/demo-credentials` | Một mật khẩu demo trả về, chỉ in tên khóa, file tạm đã xóa |
| Tác tử AI | Vượt phạm vi giao: 1 truy vấn aggregate trên `aureon_final`, `aureon_m16`, `aureon_m4`. Chỉ đọc, không chạm nội dung |
| Full gate | Container tạm đã xóa; `pnpm build` ghi `apps/web/.next` local (gitignore), không ảnh hưởng image đang chạy |

## 7. Giới hạn của audit

- Mọi kết luận 403/200 theo role về API là phân tích tĩnh; chưa chạy test BOLA có token thật. Đề nghị một phiên có phép trên stack cô lập.
- Các race condition chỉ phân tích tĩnh, chưa tái hiện.
- Chưa quét CVE Python và image. Tầm với từ LAN qua WSL2 chưa đo.
- Tài liệu 01–11, 14, STATE đọc theo cấu trúc + grep có mục tiêu, không phải từng dòng.
- UI: 58/1.802 ảnh được xem trực tiếp; chỉ Chromium headless, không có screen reader, Safari, thiết bị thật, hay kiểm thử người dùng.
- Các mục ◐ chưa được kiểm chứng độc lập; phụ lục có file:line để xác minh.

## 8. Phụ lục

| File | Nội dung |
|---|---|
| `deliverables/v4-audit/audit-product.md` | Ma trận route, module, KPI, role, BRD_Newfeature, phân loại tính năng |
| `deliverables/v4-audit/audit-arch.md` | 35 mục nợ kỹ thuật TD-01..35, must / worth it / not worth it |
| `deliverables/v4-audit/audit-ai.md` | Phân loại REAL/MOCK/HARDCODED từng năng lực, lộ trình AI |
| `deliverables/v4-audit/audit-docs.md` | Kiểm kê 00–14, S-01..S-50, đề xuất delete/archive, cấu trúc doc v4 |
| `deliverables/v4-audit/audit-uiux.md` | U-01..U-42, scorecard, audit bảng, design system v4 |
| `var/v4-audit/audit-security.md` | 35 phát hiện bảo mật, có chi tiết khai thác; đặt trong `var/` (gitignore) có chủ đích |
