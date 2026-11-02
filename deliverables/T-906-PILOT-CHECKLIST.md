# T-906 — Checklist sẵn sàng thí điểm (Pilot Readiness) · Aureon v3 — AI-EOS

> **Phạm vi:** 1 doanh nghiệp thí điểm 50–200 nhân sự (OQ-09-04). Bài nghiệm thu = **kịch bản CEO 7 bước** (09 §2.2) + cổng định lượng **G1–G4** + North Star 6 tháng (01 §BO). Tài liệu này là **đề xuất của agent** (deliverable ngoài `docs/`); số DEC và việc promote vào `docs/3.EXECUTION/` do human quyết (CLAUDE §6.6).
>
> Trạng thái cột: ☐ chưa làm · ◑ đang làm · ☑ xong · N/A không áp dụng.

---

## 0. Tóm tắt điều kiện "sẵn sàng thí điểm"

Pilot bắt đầu khi **toàn bộ mục P0 (🔴)** ở §1–§7 = ☑ và không có rủi ro mức blocking mở. Mục P1 (🟠) nên xong trước go-live; P2 (🟡) có thể làm trong tuần đầu pilot.

| Nhóm | P0 bắt buộc | Ghi chú |
|---|---|---|
| Hạ tầng & vận hành | §1 | 9 service healthy, backup, secret, domain |
| Dữ liệu & tích hợp | §2 | Seed dữ liệu thật DN, OCR thật, Calendar OAuth live |
| Bảo mật & tuân thủ | §3 | RBAC/ABAC/PII, RS256 rotation, audit, kill switch |
| AI governance | §4 | Autonomy ceiling, budget, grounding, evaluation |
| Nghiệm thu chức năng | §5 | CEO 7 bước + UC-01/03/04 pass trên stack thật |
| NFR | §6 | perf, a11y, responsive, PWA, security headers |
| Đào tạo & hỗ trợ | §7 | onboarding CEO, runbook, kênh hỗ trợ |

---

## 1. Hạ tầng & vận hành (P0)

| # | Hạng mục | Ưu tiên | Trạng thái | Bằng chứng / lệnh |
|---|---|---|---|---|
| 1.1 | 9 service compose healthy (postgres, redis, minio, ollama, clamav, api, worker, beat, web) | 🔴 | ☑ (dev) | `docker compose -f docker-compose.full.yml ps` tất cả `healthy` |
| 1.2 | API version đúng v3 (không còn 2.1.0) | 🔴 | ☑ (code) — cần **rebuild image** để endpoint `/health` trả `3.0.0` | `curl $API/health \| jq .data.version` → `3.0.0` |
| 1.3 | Alembic `upgrade head` sạch + reversible kiểm 1 vòng | 🔴 | ☑ | `alembic upgrade head` (0027) · `downgrade -1 && upgrade head` |
| 1.4 | Backup Postgres + MinIO định kỳ (RPO ≤ 24h) | 🔴 | ☐ | cron `pg_dump` + `mc mirror`; thử restore 1 lần |
| 1.5 | Secret ngoài repo: `jwt_private.pem`/`jwt_public.pem` mount read-only; `.env` không commit | 🔴 | ☑ | `./scripts/generate_keys.sh`; `secrets/` gitignored |
| 1.6 | Beat **đúng 1 instance** (outbox relay + job hằng ngày) | 🔴 | ☑ | compose `celery-beat` replicas=1 |
| 1.7 | Domain + TLS (reverse proxy) cho web + api + callback OAuth công khai | 🔴 | ☐ | §2.4 phụ thuộc mục này |
| 1.8 | SMTP thật cho Briefing email (thay Mailpit dev) | 🟠 | ☐ | `SMTP_*`; thử gửi 1 Briefing |
| 1.9 | Log tập trung + retention; log filter che `KEY\|SECRET\|PASSWORD\|TOKEN` | 🟠 | ☑ (filter) / ☐ (tập trung) | kiểm `core/` log formatter |
| 1.10 | Monitoring uptime + alert khi service unhealthy | 🟠 | ☐ | healthcheck `/health` + `/metrics` (text/plain 0.0.4) |

---

## 2. Dữ liệu & tích hợp (P0)

| # | Hạng mục | Ưu tiên | Trạng thái | Ghi chú |
|---|---|---|---|---|
| 2.1 | Seed **dữ liệu thật** của DN pilot (phòng ban, nhân sự, KPI/OKR, finance/sales) thay ABC demo | 🔴 | ☐ | import qua IDP (C5 bảng tính) + nhập tay C1; **không** dùng seed demo ABC |
| 2.2 | 7 role v3 ánh xạ đúng người thật của DN (CEO/DIR/MGR/EMP/REV/ADM + AI) | 🔴 | ☐ | tạo user qua EP user-admin; `DEMO_MODE=false` ở pilot |
| 2.3 | **OCR provider thật** bật (`OCR_PROVIDER=paddle`) — xem §2.3bis | 🔴 | ☐ | hiện `stub`; cần cài PaddleOCR hoặc DEC Google Vision |
| 2.4 | **Calendar OAuth live** (Google + Outlook), callback URL công khai — xem §2.4bis | 🔴 | ☐ | cần app OAuth + domain TLS (mục 1.7) |
| 2.5 | ClamAV signature cập nhật; `CLAMAV_REQUIRED=true` ở pilot | 🟠 | ☐ | lần đầu tải signature lâu |
| 2.6 | RAG embedding `MODEL_EMBED=bge-m3` bật (nếu dùng Knowledge/RAG) | 🟡 | ☐ | trống → fallback keyword (DEC-142) |
| 2.7 | `DEMO_REFERENCE_DATE` gỡ/đổi sang thời gian thực của pilot | 🟠 | ☐ | demo dùng `2026-10-20` |

### 2.3bis. Bật OCR thật (xem DEC đề xuất `deliverables/T-906-DEC-PROPOSALS.md` §A)

Mã đã hỗ trợ `OCR_PROVIDER ∈ {stub, paddle}` (DEC-049), import lazy. Hai lựa chọn:

- **A. PaddleOCR in-process (mặc định BRD, không thêm provider mới):**
  1. Cài optional dep: `uv add paddleocr` (hoặc nhóm optional) — **cần DEC dependency** (CLAUDE §2.3).
  2. `OCR_PROVIDER=paddle` trong `.env`; restart `api` + `celery-worker`.
  3. Smoke: upload 1 ảnh hóa đơn có chữ → kiểm field trả `confidence > 0` và `ocr_used=true`.
- **B. Google Vision (adapter mới):** **chưa có code** — cần (1) DEC provider mới, (2) adapter `httpx` trong `preprocess.py`, (3) `GOOGLE_VISION_*` credentials. Chỉ làm nếu PaddleOCR không đủ chất lượng tiếng Việt.

> **Trường trọng yếu luôn qua người** (G4): số tiền, số tài khoản, MST, lương, giá trị hợp đồng — dù OCR confidence cao vẫn review. Không nới ngưỡng confidence khi pilot (CLAUDE §6.3.10).

### 2.4bis. Cấu hình Calendar OAuth live (Google + Outlook)

Mã M3.1 đã có luồng OAuth per-user + polling dev (R-DEC-117..125, EP-CAL/EP-INT). Để chạy **live** cần tài nguyên ngoài codebase:

**Chung:**
- Mục 1.7 (domain + TLS) phải xong — callback URL **phải công khai https**.
- Callback dạng: `https://<domain>/api/v1/integrations/calendar/<provider>/callback` (xác nhận path thực tế ở EP-CAL trong 10-API-SPECIFICATION).
- Secret đặt qua `ConfigService` (`.env`), **không** vào `NEXT_PUBLIC_*`, không commit.

**Google Calendar:**
1. Google Cloud Console → tạo project → bật *Google Calendar API*.
2. OAuth consent screen (Internal nếu Workspace của DN) → scope `https://www.googleapis.com/auth/calendar.events`.
3. Credentials → OAuth client ID (Web) → Authorized redirect URI = callback ở trên.
4. Điền `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` (tên biến theo config thực tế).
5. Test `@live`: 1 user CEO connect → tạo task có deadline → kiểm sự kiện xuất hiện 2 chiều.

**Outlook / Microsoft 365:**
1. Entra ID (Azure AD) → App registrations → New registration.
2. Redirect URI (Web) = callback Outlook.
3. API permissions → Microsoft Graph → `Calendars.ReadWrite` (delegated) → grant admin consent.
4. Certificates & secrets → client secret → điền `OUTLOOK_CLIENT_ID` / `OUTLOOK_CLIENT_SECRET` / `OUTLOOK_TENANT_ID`.
5. Test `@live` tương tự Google.

> Trong môi trường code hiện tại **không test live** (không có callback công khai). Giữ polling/respx fixture ở dev; test `@live` chỉ chạy khi human cấp phép (`RUN_LIVE_TESTS=true`).

---

## 3. Bảo mật & tuân thủ (P0)

| # | Hạng mục | Ưu tiên | Trạng thái | Bằng chứng |
|---|---|---|---|---|
| 3.1 | RBAC default-deny: no-token → 401, role sai → 403 | 🔴 | ☑ | `nfr-real.spec.ts` (401/403 xanh trên stack thật) |
| 3.2 | ABAC data scoping: EMP không thấy pillar ngoài scope | 🔴 | ☑ | EMP→finance = 403; HR employees scoped |
| 3.3 | PII level-4 (lương, CCCD, STK, ngày sinh) mask trừ ROLE-CEO/ADM (+REV trong phiên) | 🔴 | ☑ | field không lộ trong list; mask cả audit/event/prompt |
| 3.4 | PII filter trước mọi lượt gọi model | 🔴 | ☑ | `ai/services/pii.py` (coverage ≥ 90% nhóm bảo mật) |
| 3.5 | JWT RS256, access 15', refresh xoay vòng + thu hồi chuỗi khi tái dùng | 🔴 | ☑ | `auth` module |
| 3.6 | Key rotation 90 ngày, private key không leak | 🔴 | ☐ | lịch rotation + `kid`; kiểm secret mount |
| 3.7 | Audit append-only mọi mutation trong cùng transaction | 🔴 | ☑ | `ENT-AuditLog` |
| 3.8 | Kill switch hoạt động (L3→L2 khi bật), L4 khóa | 🔴 | ☑ | `GET/PUT /ai/kill-switch`; ceiling L3 |
| 3.9 | Malware scan upload (ClamAV) bật bắt buộc | 🟠 | ☐ | `CLAMAV_REQUIRED=true` |
| 3.10 | Classification: Confidential → không fallback cloud; Secret → không LLM | 🔴 | ☑ | ModelGateway routing |
| 3.11 | Prompt injection: nội dung tài liệu bọc delimiter, coi là data | 🔴 | ☑ | ai_eval INJ suite |

---

## 4. AI governance (P0)

| # | Hạng mục | Ưu tiên | Trạng thái | Ghi chú |
|---|---|---|---|---|
| 4.1 | Autonomy ceiling pilot = **L3** (L4 khóa); Approval Matrix cấu hình đúng | 🔴 | ☑ | `/ai/autonomy-policies` |
| 4.2 | `AI_MONTHLY_BUDGET_USD` đặt + cảnh báo 80% + chặn 100% (`429 AI_QUOTA_EXCEEDED`) | 🔴 | ☐ | đặt theo ngân sách DN |
| 4.3 | ModelGateway provider chain live + fallback; mọi call qua gateway | 🔴 | ☑ | `MODEL_PROVIDER_PRIMARY`/`FALLBACKS` |
| 4.4 | Grounding: không bịa số, mọi số khớp `tool_result`/`MetricValue` | 🔴 | ☑ | `grounding.py` cov 91%; ai_eval GR suite |
| 4.5 | Evaluation Engine chạy bộ test chuẩn trước go-live (grounding/accuracy/tool_choice) | 🟠 | ☐ | `python -m app.scripts.run_eval`; `/admin/ai/evaluation` |
| 4.6 | Undo: L3 action undo 24h, IDP commit undo 7 ngày | 🔴 | ☑ | EP-AI-11; IDP undo |
| 4.7 | Log `ModelCallLog`/`ToolCallLog` (token/chi phí/provider), không lưu prompt thô | 🔴 | ☑ | `/ai/model-calls`, `/ai/tool-calls` |

---

## 5. Nghiệm thu chức năng — CEO 7 bước + UC (P0)

Chạy trên **stack thật đã seed dữ liệu DN**. (Môi trường dev dùng demo-replay cho câu hỏi canonical; pilot dùng ModelGateway live.)

| Bước / UC | Hạng mục | Trạng thái | Bằng chứng |
|---|---|---|---|
| 1–2 Ask/Understand | CEO hỏi → tổng hợp có nguồn + lineage (P05/P07) | ☑ | `ceo-7steps-real.spec.ts` step 1–2 |
| 3 Investigate | "Vì sao…" → AI gọi read tool, grounded | ☑ | step 3 |
| 4 Decide | Insight 9 phần / panel insight | ☑ | step 4 |
| 5 Act | L3 propose→confirm→execute qua Action Registry | ☑ | step 5–6 (EP-AI-07/09/11) |
| 6 Follow-up | Action xuất hiện feed "AI đã làm"/task | ☑ | step 5–6 |
| 7 Verify | Decision Log review/verify (D28) | ☑ | step 7 |
| UC-01/03/04 | pass E2E trên real | ☑ | `uc03-real.spec.ts` + chuỗi M1/M2/M3 |
| G1 | CEO mở Briefing ≥ 4 ngày/tuần (adoption) | ☐ pilot | instrumentation sẵn; đo trong pilot |
| G2 | % KPI/OKR cập nhật đúng kỳ ≥ 90% (METRIC-STR-01) | ☐ pilot | trang `/admin/acceptance` |
| G3 | % dữ liệu vào qua tài liệu/NL ≥ 60% (METRIC-DQ-02) | ☐ pilot | trang `/admin/acceptance` |
| G4 | 0 sự cố trường trọng yếu lọt lưới | ☐ pilot | ràng buộc cứng; audit |

> Ngưỡng G1–G4 **thật** xác nhận trong pilot (OQ-09-04); trang đo `/admin/acceptance` (EP-RPT-08) đã sẵn.

---

## 6. NFR (P0/P1)

| # | NFR | Trạng thái | Bằng chứng (stack thật) |
|---|---|---|---|
| 6.1 | Dashboard p95 < 3s (NFR-PERF-01) | ☑ | `perf_m2_gate.sh` → p95 ≈ 0.03s |
| 6.2 | Chat TTFT < 2s (NFR-PERF-02) | ☑ | → p95 ≈ 0.08s |
| 6.3 | Responsive 1440/1280/768/390, không cuộn ngang | ☑ | `responsive.spec.ts` 4/4 |
| 6.4 | WCAG AA structural (landmark, 1 H1, nav tên, ⌘K modal) | ☑ | `a11y-m2.spec.ts` 5/5 |
| 6.5 | PWA installable (manifest + service worker) | ☑ | `nfr-real.spec.ts` PWA 2/2 |
| 6.6 | Cache NFR-07 (`private` + `Vary: Authorization`) | ☑ | `nfr-real.spec.ts` |
| 6.7 | a11y axe-core tự động (độ sâu rule) | ☐ | cần dep `@axe-core/playwright` → **DEC** |
| 6.8 | FE coverage ≥ 70% (features/ + lib/) | ☐ | cần dep `@vitest/coverage-v8` → **DEC** (§B) |

---

## 7. Đào tạo & hỗ trợ (P1)

| # | Hạng mục | Ưu tiên | Trạng thái |
|---|---|---|---|
| 7.1 | Onboarding CEO (luồng SCR onboarding + Daily Briefing) | 🟠 | ☐ |
| 7.2 | Hướng dẫn 7 role (1 trang/role) + video demo 7 bước | 🟠 | ☐ |
| 7.3 | Runbook vận hành: restart service, reset, rotate key, kill switch | 🔴 | ☐ |
| 7.4 | Kênh hỗ trợ + SLA phản hồi trong pilot | 🟠 | ☐ |
| 7.5 | Lịch review pilot hằng tuần + KPI adoption | 🟠 | ☐ |

---

## 8. Rủi ro pilot & giảm thiểu

| Rủi ro | Mức | Giảm thiểu |
|---|---|---|
| OCR tiếng Việt chất lượng thấp trên scan xấu | Cao | PaddleOCR + preprocess khử nghiêng; field trọng yếu luôn review (G4) |
| Chi phí LLM vượt ngân sách | Cao | `AI_MONTHLY_BUDGET_USD` + cảnh báo 80% + chặn 100% |
| AI bịa số | Cao | grounding validator + ai_eval GR gate trước go-live |
| OAuth callback không công khai | Trung | dựng domain TLS (1.7) trước khi bật Calendar live |
| Dữ liệu DN nhạy cảm lộ qua prompt | Cao | PII filter + classification routing + audit |
| Beat 2 instance → job trùng | Trung | replicas=1; job idempotent theo (job, ngày) |

---

## 9. Phụ thuộc cần human / DEC trước pilot

1. **DEC dependency OCR** (PaddleOCR optional) — nếu chọn phương án A (§2.3bis). Đề xuất ở `deliverables/T-906-DEC-PROPOSALS.md §A`.
2. **DEC dependency FE coverage** (`@vitest/coverage-v8`) — để đo coverage FE (§6.8). Đề xuất §B.
3. **DEC dependency a11y axe** (`@axe-core/playwright`) — a11y tự động sâu (§6.7). Đề xuất §C (tùy chọn).
4. **Chọn DN pilot thật** (OQ-09-04) — quyết định CEO, ngoài codebase.
5. **Domain + TLS + OAuth app** (Google/Outlook) — hạ tầng DN, ngoài codebase.
6. **Ngân sách LLM tháng** — quyết định tài chính DN.

---

*Deliverable do agent soạn (T-906). Không sửa `docs/`. Human xem xét, cấp số DEC cho các dependency, và promote vào `docs/3.EXECUTION/` nếu phù hợp.*
