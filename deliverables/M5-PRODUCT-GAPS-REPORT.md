# M5 — 4 khoảng trống phát hiện khi kiểm thử giao diện: audit, root cause, sửa, kiểm thử

> Nhánh `v3/m5-product-gaps` (từ `origin/main` @ `9f3003a`). Ngày 2026-11-03.
> Không force-push, không merge, không deploy; stack compose đang chạy **không bị đụng** — mọi kiểm
> chứng thật chạy trên stack cô lập: API `:4600` (DB `aureon_m4`, provider Ollama `qwen2.5:7b-instruct`)
> + web production `:3600` (`next build` + `next start`).

## 1. Tóm tắt

| # | Vấn đề báo | Root cause | Đã sửa | Bằng chứng |
|---|---|---|---|---|
| 1 | AI Chat không tạo được Task (CEO) | RBAC **đúng**. (a) môi trường: OmniRoute — provider runtime duy nhất — không chạy → mọi chat live `AI_PROVIDER_ERROR`; (b) code: ngày `30/10/2026` bị `ACT-create_task` từ chối; `assignee_code` của AI bị **bỏ**; `project_code` bị bỏ qua; (c) SSE không phát `error` khi provider lỗi → stream đứt | (b), (c) — R-DEC-157 | API: task thật + audit `ai.action_proposed → execution.task_create → ai.action_executed`; **UI `/ask` thật**: thẻ "AI đã làm · Tạo việc", task hạn `2026-11-30` giao `NV-0001` |
| 2 | Chưa có Tạo KPI / Tạo OKR | Backend đủ CRUD; FE chỉ có 2 nút **disable cứng** "sắp có" | Dialog tạo/sửa/lưu trữ KPI, Objective, Key Result; chọn owner | E2E mock + real: tạo → chi tiết → sửa → lưu trữ; trùng mã → lỗi tại chỗ; EMP không thấy nút |
| 3 | AI Admin thiếu Model Calls / Token / Cost | UI 3 tab đã có. (a) demo replay không gọi model → 0 dòng (đúng bản chất); (b) **log lượt lỗi bị rollback mất**; (c) `MODEL_PRICING_JSON={}` → $0 như miễn phí; (d) thiếu lọc provider/model/trạng thái, không có tổng hợp | (b) R-DEC-154; (c) `unpriced_calls` R-DEC-155; (d) UI | Lượt timeout 90 s thật được ghi dù request bị huỷ; E2E lọc provider/trạng thái trên dữ liệu thật |
| 4 | `home/metrics/*` 404 | Link cảnh báo `/dashboard/metrics/{code}` → 308 `/home/metrics/{code}` không có trang. **Thêm 2 link hỏng cùng loại**: `/knowledge/decisions`, `/work/tasks/{id}` | Trang `/home/metrics/[code]`; route `/knowledge/[tab]`; link `/work?task=` — R-DEC-156 | Contract test quét mọi link backend ↔ cây trang web; E2E mock + real |

## 2. Đối chiếu tài liệu

| Hạng mục | Tài liệu | Implementation trước M5 | Sau M5 |
|---|---|---|---|
| Chat tạo task | 10 §2.3 `TOOL-create_task` (`execution:write` + `ai:write`), autonomy L3 + undo 24h | quyền/autonomy đúng; nhánh AI của ACT sai (date, assignee, project) | đúng + giải mã mã, `"me"` (R-DEC-41) |
| SSE | 10 §6: `start → … → done \| error` | thiếu `error` cho mọi `AppError` trừ AI_DISABLED | đủ |
| KPI/OKR | 10 EP-KPI-02/04/05, EP-OKR-02/04/05/07/09/10; 06 SCR-41/58/59 | API đủ, UI không có | UI đủ, gọi đúng EP, `version` lạc quan, lưu trữ = DELETE (soft) |
| Telemetry | 05 §2.8 ENT-ModelCallLog "log mọi lượt gọi"; 10 EP-AI-15/22/23; 06 SCR-65 | lượt lỗi mất khi rollback; giá 0 không phân biệt | lượt lỗi được giữ; `unpriced_calls`; lọc + tổng hợp |
| Metric drill / thông báo | 06 P01 (dialog), R-DEC-88 link cảnh báo, R-DEC-137 `/knowledge/decisions` | link trỏ trang không tồn tại | trang có thật + contract test |

## 3. Thay đổi

**Backend**
- `idp/services/actions/work.py` — `TaskParams` nhận `dd/mm/yyyy`; `_ai_refs` giải mã `assignee_code` (`"me"`) và `project_code`, mã lạ → `NOT_FOUND {field}`.
- `execution/services/meeting_service.py` — `ProjectService.project_id_by_code` (theo phạm vi đọc).
- `ai/tools/registry.py` — mô tả tham số `TOOL-create_task` (chỉ mã từ tool hoặc `"me"`).
- `ai/routes/router.py` — SSE phát `error {code}` cho `AppError`.
- `ai/services/ai_service.py` — `ModelCallLogWriter`: lượt lỗi commit độc lập (`message_id=NULL`).
- `ai/schemas` + `ai/services/cost_service.py` — `CostRowOut.unpriced_calls`.
- `platform/services/metric_store.py`, `idp/services/actions/recommendation.py` — link thông báo v3.

**Frontend**
- `features/goals/GoalEditors.tsx`, `goal-forms.ts`, `use-goals.ts` (mutation), `GoalTreeView`, `KpiDetailView`, `ObjectiveDetailView`, `GoalsShell` (`canPickOwner`).
- `features/admin/ai/logs/UsageSummary.tsx`, `ModelCallsTab.tsx` (lọc), `CostTab.tsx`, `log-logic.ts`.
- `app/(app)/home/metrics/[code]/page.tsx`, `features/dashboard/MetricDetailContent.tsx` (tách từ `MetricDetailPanel`), `MetricLandingView.tsx`, `use-metric-detail.ts` (`errorCode`).
- `app/(app)/knowledge/[tab]/page.tsx`, `features/knowledge/tabs.ts`, `KnowledgeView` (`initialTab`).
- i18n vi/en (parity giữ nguyên), mock BFF EP-AI-15 `unpriced_calls`.

**Tài liệu**: `10` (EP-AI-15), `13` (R-DEC-154..157), `14` (§1.22 TC-M5-01..09), `09` (§6.20), `06` (SCR-12 trang).

Không migration, không dependency mới, không đổi quyền/autonomy.

## 4. Kiểm thử

| Gate | Kết quả |
|---|---|
| Backend test mới | `test_ai_create_task_m5` 5 · `test_model_call_log_failures_m5` 3 · `test_cost_unpriced_m5` 1 · `test_chat_stream_errors_m5` 3 (kiểm âm: router cũ fail) · `test_notification_links` 2 (kiểm âm: bỏ trang → fail) |
| Full backend | xem STATE (chạy trên `aureon_m4`) |
| Contract | xem STATE |
| Vitest | 50 file / 448 test (thêm `goal-forms` 8, `log-logic` +3) |
| E2E mới (9) | mock 9/9 · real (stack cô lập, production build) 3 lần liên tiếp 9/9 |
| Production build | `pnpm build:web` xanh, có `/home/metrics/[code]`, `/knowledge/[tab]` |
| lint / typecheck / ruff / mypy | xanh |

## 5. Còn tồn đọng (cần quyết định / ngoài code)

| # | Việc | Ghi chú |
|---|---|---|
| 1 | **OmniRoute không chạy** trên host → mọi chat live của stack compose lỗi `AI_PROVIDER_ERROR` (giờ hiện thông báo rõ thay vì stream đứt) | Bật lại OmniRoute, hoặc quyết định `MODEL_PROVIDER_FALLBACKS` (vd `ollama` — an toàn hơn về dữ liệu nhưng chậm trên CPU). Đổi chuỗi provider là quyết định chính sách, chưa tự đổi |
| 2 | **Stack compose đang chạy chưa có code M5** | Cần build lại image `api` + `web` và recreate (như quy trình M4) — chờ duyệt |
| 3 | `MODEL_PRICING_JSON={}` | Chủ hệ thống cấu hình giá `provider:model`; UI hiện báo "chưa có giá" thay vì $0 |
| 4 | Owner KPI/OKR cho DIR/MGR | Chỉ CEO/ADM chọn được owner khác (`/platform/users` cần `platform:read`); role khác owner = chính mình. Muốn mở rộng cần endpoint danh bạ user theo phạm vi → R-DEC |
| 5 | Model local trên CPU chậm | FE cắt stream ở 120 s; Ollama lạnh có lượt 90 s timeout → lần UI đầu báo "quá 120 giây". Với provider cloud không gặp |
| 6 | `/dashboard/alerts` (v2.1) → `/home/alerts` | Không còn link nào trỏ tới, nhưng bookmark cũ sẽ 404 |
| 7 | Vitest thỉnh thoảng timeout 5 s ngẫu nhiên khi máy tải nặng | Tiền tồn, không liên quan M5 (5/6 lần xanh) |
| 8 | `login()` trong E2E không chờ redirect sau đăng nhập | Thêm `loginSettled()` dùng cho spec M5; spec cũ dùng `login()` + `goto()` ngay có thể gặp cùng race dưới tải |

## Version

- Draft 0.1 — 2026-11-03.
