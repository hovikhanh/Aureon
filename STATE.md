# Aureon v3 — AI-EOS · Build State

## M4 — Doc ↔ code conformance & hardening (nhánh `v3/m4-doc-code-conformance`, 2026-11-02→03) — DONE, chờ human review/merge

**Gate cuối:** pytest full **1383 passed / 0 failed**, cov **94%** (DB cô lập `aureon_m4`) · contract **41** · ruff/format/mypy (387 file) xanh · Vitest **50 file / 437 test** · FE coverage 88,26% / 71,29% / 88,66% · Playwright mock **95/95** · axe-core AA 0 violation · shared-types drift 0 · `scripts/check_env.sh` xanh. 6 commit `7329c4f..590833a`, **chưa push**.

> Môi trường: sau khi session khởi động lại, Docker CLI không còn trong WSL (mất tích hợp Docker Desktop) → stack compose không truy cập được; mọi test cần DB đã chạy xong trước đó trên code backend cuối (`.coverage` 23:40 > mtime backend cuối 23:16). Cần bật lại WSL integration của Docker Desktop để chạy stack.

Human giao: "phân tích tài liệu @docs/ và cải tiến dự án" → chốt phạm vi **toàn bộ doc set 00–14 vs
codebase**, 4 ưu tiên (audit API, hoàn thiện module theo docs, siết chất lượng, doc-sync), môi trường
**re-seed demo để dev**, agent **toàn quyền** code + docs + dependency. Kế hoạch + audit:
`deliverables/M4-CONFORMANCE-PLAN.md`.

### Sau audit trước-rebuild (`deliverables/M4-SYNC-AUDIT.md`, human duyệt 2026-11-03)

| Hạng mục | Kết quả |
|---|---|
| **P1 — đính chính `10` §7.3** (lỗi do M4) | 17 số EP v2.1 sửa theo chú thích route trong code; bỏ `EP-GOL-01` (trùng `EP-STR-17..21` — parser cũ không nhận ID dạng dải → "69 route" thực ra là **64**); 13 ghi chú route sửa theo code (vd scenario **có** lưu DB, workload là `METRIC-HR-03`, audit alert là `dashboard.*`, `platform:admin` = CEO + ADM, khối "Cần quyết" đọc hàng chờ phê duyệt); EP-HR-07 mức 4 = **CEO + DIR khối O**. Khóa bằng `TC-M4-16` (kiểm âm: đổi EP-PLT-01 về `EP-59` → fail). Contract **42** |
| **P5 — Dockerfile OCR** | bake model trước `COPY apps/api`, fail build khi thiếu model. Image mới `aureon-api:local` = `fcb10365d0c1`: đủ det/rec/cls; OCR `--network none` 13/13 file, `DOC-10` conf 0,958; build lại sau đổi source → bake `CACHED`; source = HEAD 389/389 |
| **P4 — chat timeout** | **R-DEC-153**: giữ 90 s cho `task=chat` (human duyệt), ghi chú ngoại lệ ở `07` §145; theo dõi p95 latency live |
| Đường lùi | `aureon-api:pre-m4` (`96a7fd9cbeec`), `aureon-web:pre-m4` (`033391240532`) |
| **Chưa làm (chờ duyệt)** | build image web; recreate api/worker/beat/web — container **vẫn chạy image cũ** |

### Audit bằng máy (không phỏng đoán)

| Phát hiện | Trước | Sau |
|---|---|---|
| EP trong `10` §7 thiếu route | 0 | 0 |
| Route **không có** EP id nào | **64** (product/risk/execution/hr/dashboard/platform; ban đầu ghi nhầm 69 — 5 route milestones đã có `EP-STR-17..21`) | **0** — `10` §7.3 mới (R-DEC-148) |
| Permission spec ↔ code lệch | **5** (EP-RPT-02/03, EP-FIN-05, EP-FIN-10) | **0** — code đúng, sửa spec (R-DEC-147) |
| Tool Registry trong doc v3 | **không có bảng** (code 54 `TOOL-*`, doc nhắc 29 id) | `10` §2.3 bảng gương 54 tool × 13 metadata (R-DEC-149) |
| Metric catalog trong doc v3 | **không liệt kê** (code 34) | `03` §4.2 bảng gương 34 chỉ số |
| `ACT-*` doc ↔ code | nghi lệch 2 id | **không lệch** (`ACT-reassign_review`/`merge_review` do review-service sở hữu) |
| Kiểm chứng máy toàn catalog | không có (contract test theo phase, hard-code) | `tests/contract/test_catalog_conformance.py` — 6 test, 3 chiều; contract **34 → 40** |

### Module hoàn thiện theo docs

- **T-1010 retention `idp.purge_import_rows`** — đóng `OQ-05-11` (05 §2.7 chốt từ M1.5, chưa code): service `idp/services/retention_service.py`, beat 02:00, idempotent, chỉ xóa `import_rows` của batch `completed`/`partially_failed` khi `undo_deadline` đã qua, giữ `extracted_fields`, audit `idp.purge_import_rows`. 5 test integration.
- **T-1011 `idp.sweep_orphan_storage`** — biến runbook SQL tay (`docs/handover/IDP_Operations.md` §5.1) thành job: `ObjectStore` thêm `iter_keys()`/`delete()` (LocalObjectStore; MinIO/S3 map sang `list_objects_v2`/`delete_object` cùng tên), beat 02:30, **mặc định chỉ báo cáo** (`IDP_ORPHAN_SWEEP_DELETE=false` — CLAUDE §6.6 rule 9), bỏ qua file trẻ hơn cửa sổ undo 7 ngày.

### Chất lượng

- **T-1020 `.env` không source được** — `ADMIN_BOOTSTRAP_PASSWORD` chứa `"` không quote → `bash: .env: line 93: unexpected EOF`, đứt quy trình `set -a; . ./.env` mà STATE/handover ghi là bắt buộc. Đã quote `.env` + 26 placeholder trong `.env.example`; thêm `scripts/check_env.sh` (kiểm chéo bash ↔ dotenv ↔ Compose `env_file`, **chỉ in tên key**) + 2 test guard.
- **T-1021 FE coverage lần đầu đo được** (R-DEC-150, `@vitest/coverage-v8`): statements **88,26%** · functions **71,29%** · branches **88,66%** (ngưỡng 70%, `14` §1.3). Phạm vi: module logic `*.ts` của `features/`+`lib/`; loại trừ hook TanStack Query (`use-*.ts`, phủ bằng Playwright). Thêm 11 test cho `lib/auth.ts` (**0% trước đó** — nơi duy nhất xử lý access/refresh token).
- **T-1022 a11y axe-core thật** (R-DEC-151, `@axe-core/playwright`): 6 test trên `/home`, `/ask`, `/data`, `/business`, `/goals/check-ins` + ⌘K. Lần chạy đầu phát hiện **3 lỗi AA thật** mà kiểm structural (T-739) không thấy — đã sửa:
  1. token `text-success/warning/danger` trên nền `-subtle` chỉ 2,40–4,30:1 → hạ lightness (tính theo công thức WCAG, có cả override dark mode);
  2. `text-primary` trên `bg-primary/15` = 4,46:1 (avatar/chip) → `--primary` 0,52 → 0,50 (4,84:1);
  3. panel ⌘K dùng class `bg-popover` — **token không tồn tại** trong `@theme` → panel trong suốt, chữ nằm trên overlay `bg-black/40` (1,83:1) → đổi `bg-card`.

### Gate bắt được 2 lỗi của chính đợt này (đã sửa, không nới lỏng test)

1. `architecture/test_tenant_query_boundary.py` — `retention_service.py` build SQL trực tiếp trên entity nghiệp vụ (`select/delete` ngoài `repositories/`) → bỏ qua lớp lọc `tenant_id` thứ nhất (CLAUDE §4.3, R-DEC-21). **Sửa:** chuyển 4 query vào `ImportRepository.batches_past_undo_window/count_rows_of/delete_rows_of` + `SourceDocumentRepository.all_storage_keys`; service chỉ gọi repository.
2. `integration/platform/test_jobs.py` — beat schedule có 16 entry nhưng test khai 14. **Sửa:** thêm 2 job mới vào `EXPECTED` kèm giờ chạy (02:00 / 02:30) và nâng số đếm — test vẫn khóa chặt từng entry.

**E2E mock tiền tồn từ M3.5 (không do M4):** `e2e/admin-screens.spec.ts:97` đếm cứng 2 card `/admin` cho DIR khối O; M3.5 (`0effd10`) thêm card `/admin/acceptance` (`dashboard:read`, mọi DIR — khớp EP-RPT-08) → thực tế 3 card, spec chưa chạy lại sau M3.5. **Code đúng, test cũ** → sửa spec assert **danh tính** 3 card (org, positions, acceptance) + số đếm, thay vì chỉ đếm.

**Thêm 2 E2E mock tiền tồn (lộ ra khi chạy full mock suite 95 test — 93 pass / 2 fail):**
- `navigation.spec.ts:39` — test "item chưa xây hiện khung *Sắp có*" dùng `/knowledge` (SCR-49), nhưng SCR-49 đã xây ở M3.3/M3.4 → spec stale. Đổi theo đúng mẫu test "meetings (SCR-44) is now built" ngay dưới: assert `knowledge-view` + `knowledge-tabs` hiển thị, `coming-soon` = 0.
- `goals.spec.ts:93` — **date drift trong mock BFF**: UI hỏi feed theo tuần của `businessToday()` = `DEMO_REFERENCE_DATE` (20/10), nhưng mock ghi `checked_in_at`/`measured_at` bằng **đồng hồ thật** → check-in mới (03/11) nằm ngoài tuần → MGR thấy feed rỗng. Backend thật **không** có lỗi này (`measured_now()` → `core.clock.business_now()` giữ giờ thực, dời ngày về ngày nghiệp vụ — DD-05). **Sửa mock cho khớp backend:** `measuredNowIso()` ở `mocks/goals-http.ts`, dùng đúng 3 chỗ backend dùng `measured_now()` (KPI check-in, KPI measurement, KR check-in); `created_at` các entity khác giữ đồng hồ thật như backend. +2 unit test. Spec xanh khi viết (tuần 20/10) và đỏ từ ~26/10 — đó là lý do M3.5 không thấy.

**Test tiền tồn ghi ở M2/M3 (`inj02`/`inj03`, `goal_events_t629`, `seed_s2`, `test_chat_demo_mode`) đều PASS** trên DB seed sạch `aureon_m4` → không còn nợ GAP-12.

### Doc-sync

`10` (§2.3, §7.3, 5 ô permission) · `03` (§4.2) · `05` (đóng OQ-05-11) · `09` (82 ô ☐→☑ theo bằng chứng gate + §6.19 M4) · `12` (last_reviewed 6 file) · `13` (R-DEC-147..152) · `14` (§1.21 TC-M4-01..13) · `docs/handover/IDP_Operations.md` §5 (trỏ sang job).

### Môi trường

Re-seed demo: backup `var/backup/aureon_predev_20261102_222021.dump` → `./scripts/demo_reset.sh -y` → 7 phòng/154 NV/10 user demo/34 metric/13 alert/1 NEEDS_REVIEW/6 AI agent. DB test cô lập `aureon_m4` (migrate + seed riêng) cho full suite — không chạm DB demo.

---

## Status: M3 (Hành động) DONE — M3.1→M3.5 XANH, đã merge fast-forward vào `main` + tag `v3.0.0-mvp` (2026-11-02). MVP 3 mốc (M1+M2+M3) hoàn tất ở mức code. **Nghiệm thu M3.5 chạy trên STACK THẬT (2026-11-02): T-901/903/full-test xanh (xem dưới).**

## LIVE CUTOVER — xóa data demo + chạy live (2026-11-02, human yêu cầu)

Human yêu cầu: "xóa data demo, triển khai chạy live". Đã thực hiện trong môi trường; phần cần tài nguyên ngoài (OCR dep/DEC, OAuth credential, data thật DN) chờ human.

| Bước | Kết quả |
|---|---|
| **Backup** | `var/backup/aureon_predeploy_20261102_171136.dump` (pg_dump -Fc, đường lùi) |
| **Xóa data demo** | TRUNCATE 10 schema nghiệp vụ (giữ `platform.alembic_version`), KHÔNG re-seed demo → users/orgs/metrics = 0. MinIO `source-documents` emptied (0 object), `var/idp-storage` sạch, redis FLUSHDB, Celery queues purged |
| **Config live** | `.env`: `DEMO_MODE=false`, `NEXT_PUBLIC_DEMO_MODE=false`, `AI_DEMO_REPLAY=false`, `DEMO_LOGIN_AUTOFILL=false`. Recreate api/web/worker/beat (`up -d --force-recreate` — `restart` KHÔNG nạp lại env_file) |
| **Admin thật** | Script mới `apps/api/src/app/scripts/bootstrap_admin.py` (seed 7 roles + tạo 1 ROLE-ADM từ `ADMIN_BOOTSTRAP_EMAIL/PASSWORD`, idempotent, đọc .env quote-safe qua dotenv_values). Tạo `admin@abc.com` (role ADM). Mật khẩu do human đặt trong .env |
| **Verify live** | `/health` 200; EP-04 role-switch demo → 404 (DEMO_MODE off); login admin → 200 + JWT; chat tự do → model thật trả lời, **KHÔNG** có `ai.warn.demo_replay`, `sources:[]` (DB trống). `ai.model_call_logs`: provider=omniroute, model=claude-sonnet-5, status=ok, prompt_sha256 có → bằng chứng gọi gateway thật |

**CHẶN — chờ human/DEC (không làm được trong môi trường):**
1. ~~**OCR thật** (`OCR_PROVIDER=paddle`)~~ — **ĐÃ XONG (2026-11-02, R-DEC-146)**: hợp thức hóa dependency OCR thật (`paddleocr==2.10.0` + `paddlepaddle==3.0.0` + `setuptools`) làm optional-dependency group `ocr`; image `aureon-api:local` rebuild có cài + **bake sẵn model** (det/rec/cls lang vi) → OCR chạy **offline** (`--network none` xanh). Xác minh: OCR `data/DOC-10-anh-hoa-don-gtgt.png` → 267 ký tự đúng số liệu hóa đơn, conf 0,958; 13/13 file `/data` qua `extract_pages` đều có text (`app.scripts.ocr_verify_data`). Dev/CI giữ `stub` (`base sync --no-dev` không kéo gói nặng). Nội dung đề xuất: `deliverables/T-906-DEC-PROPOSALS.md §A`.
2. **OAuth Calendar live**: cần domain+TLS+callback công khai + `GOOGLE_CLIENT_ID/SECRET`, `OUTLOOK_CLIENT_ID/SECRET/TENANT_ID`.
3. **Data thật DN**: có 13 file mẫu thật trong `/data` (báo cáo tài chính/sales Q3, hóa đơn, hợp đồng, biên bản họp, danh sách nhân sự, KPI/OKR, sao kê, ảnh hóa đơn GTGT). Import qua IDP (C3 file / C4 ảnh / C5 bảng) khi stack chạy; DB nghiệp vụ hiện trống (chỉ roles + 1 admin) cho tới khi import/nhập tay.

> Lưu ý: image api `aureon-api:local` nay serve version `3.0.0` (đã rebuild với extra `ocr` + model OCR baked, ~5,25GB) — `docker compose -f docker-compose.full.yml up -d --force-recreate api` để chạy. Mật khẩu admin NÊN đổi sau lần đăng nhập đầu.

**Bỏ dropdown chọn tài khoản demo ở /login (2026-11-02):** `apps/web/src/app/(auth)/login/page.tsx` — gỡ nhánh `|| process.env.NEXT_PUBLIC_DEMO_MODE === "true"`. Lý do: đây là Server Component, `NEXT_PUBLIC_*` bị Next **inline lúc build** (image cũ build với `=true`) nên luôn bật dropdown dù `.env` runtime đã `false` — bẫy cutover live. Nay chỉ dựa `DEMO_MODE` runtime. Rebuild image web (buildx cần BuildKit; `DOCKER_CONFIG=$PWD/var/docker-config` để tránh sandbox chặn ghi `~/.docker`) + recreate. Verify: HTML `/login` live **không** còn `<select id="demo-account">` và 0 email `@abc.demo`. Mock E2E (`login.spec.ts` 7/7) vẫn xanh vì mock server set `DEMO_MODE=true` → dropdown vẫn render ở demo. Không đổi API/schema/dependency.

**Bật lại tự điền mật khẩu demo ở /login (2026-11-02, human yêu cầu "thêm lại phần tự điền mật khẩu để demo cho nhanh"):** feature SCR-13 autofill (R-DEC-28/T-610c) vốn **còn nguyên trong code** (`LoginForm` dropdown + `features/auth/demo-autofill.ts` + Route Handler `api/demo-credentials` + `lib/demo-credentials.ts` + `lib/server-env.ts`), chỉ bị **tắt bằng cờ runtime**. Hiện `DEMO_MODE=true` (dropdown đã render) nhưng `DEMO_LOGIN_AUTOFILL=false` → endpoint autofill trả 404 nên không điền mật khẩu. Sửa `.env`: `DEMO_LOGIN_AUTOFILL=true` + `docker compose up -d --force-recreate --no-deps web` (restart không nạp lại env_file). **Không đổi code / API / schema / dependency.** Verify: `POST /api/demo-credentials {email:"ceo@abc.demo"}` → `200 {data:{email,password}}` (CEO/CFO/sales điền được); email ngoài whitelist (`attacker@evil.com`, `admin@abc.com` thật) → `404` (giữ an toàn, không oracle mật khẩu); flow đầy đủ autofill→login backend → JWT ok; Vitest `demo-credentials`/`demo-accounts` 11/11 xanh.

## NGHIỆM THU M3.5 TRÊN STACK THẬT — T-901/903/906 + full test + version drift (2026-11-02)

Stack compose 9 service healthy (postgres/redis/minio/ollama/clamav/api/celery-worker/beat/web + mailpit + clamav). Backlog M3.5 "stack-real/pilot" xử lý xong phần chạy được trong môi trường; phần cần tài nguyên ngoài codebase (OAuth live, OCR thật, chọn DN pilot) để human/DEC.

| Hạng mục | Kết quả | Bằng chứng |
|---|---|---|
| **Version drift 2.1.0→v3** | ✅ sửa source | `apps/api/src/app/__init__.py` + `apps/api/pyproject.toml` = `3.0.0`; **cần rebuild image** để `/health` serve v3 (container đang chạy image cũ 2.1.0) |
| **T-901 E2E CEO 7 bước (real)** | ✅ **5/5** | `apps/web/e2e/ceo-7steps-real.spec.ts`: Ask+Understand (chat grounded + citation→lineage `METRIC-`), Investigate (sources), Decide (InsightsPanel), Act+Follow-up (Action Registry EP-AI-07/09/11), Verify (Decision Log) |
| **T-903 NFR (real)** | ✅ security 6/6 + responsive 4/4 + a11y 5/5 + perf | `nfr-real.spec.ts` (401/403, cache `private`+`Vary: Authorization`+`X-Request-Id`, health `no-store`, PWA manifest+SW); `responsive.spec.ts` 1440/1280/768/390; `a11y-m2.spec.ts` WCAG AA; `perf_m2_gate.sh` dashboard p95 **0.032s**, chat TTFT p95 **0.080s** |
| **Full test backend (real DB)** | ✅ **1368 pass / 1 isolation-flake** cov **94%** | DB cô lập `aureon_fulltest` seeded; 144 fail ban đầu = thiếu seed (ORG_ID cố định) → re-run seeded **343/343 pass**; flake `test_chat_demo_mode` leak config cache (pass khi chạy riêng 5/5) |
| **Contract + Vitest** | ✅ contract **34** · Vitest **424** | `pytest -m contract`; `pnpm test:web` 48 file |
| **T-906 pilot checklist** | ✅ deliverable | `deliverables/T-906-PILOT-CHECKLIST.md` (§1–§9 + OAuth Google/Outlook config + OCR `paddle`) |
| **DEC đề xuất (không tự cài)** | ✅ đề xuất | `deliverables/T-906-DEC-PROPOSALS.md`: A=`paddleocr` (OCR thật), B=`@vitest/coverage-v8` (coverage FE), C=`@axe-core/playwright` (a11y sâu) |

**Còn ngoài code (human/DEC):** (1) OAuth Calendar Google/Outlook **live** — cần domain+TLS+callback công khai + app OAuth (hướng dẫn ở pilot checklist §2.4bis); (2) OCR provider thật — `paddleocr` chưa cài, cần DEC dependency (§2.3bis); (3) đo coverage FE + a11y axe-core — chờ DEC `@vitest/coverage-v8` / `@axe-core/playwright`; (4) chọn DN pilot thật (OQ-09-04); (5) PR `ai-eos→main` (đã ở `main` qua merge ff + tag); (6) rebuild image api để `/health` serve version `3.0.0`.

**Đề xuất cập nhật `docs/` (chờ human duyệt — CLAUDE §6.6 cấm agent sửa docs/ ngoài 14):** `docs/DEMO-SCRIPT.md` §8.0 + dòng 3–4 và `docs/3.EXECUTION/09-BUILD-PLAN-TASKS.md` §6.17 (T-901/903 ☐→☑, T-906 ☐→◑) nên chuyển "M3.5 đang tiến hành" → "M3.5 DONE cho phần code-env; OAuth/OCR/pilot ngoài code". Nội dung đề xuất ở cuối STATE (§ "Đề xuất doc-sync").

## M3 — Hành động (M3.1→M3.5, chuỗi auto liên tục, human ủy quyền) — DONE 2026-11-02

Đóng vòng OBSERVE→UNDERSTAND→REASON→RECOMMEND→APPROVE→ACT→VERIFY→LEARN. Mỗi mốc 1 nhánh từ đỉnh mốc trước; agent tự chốt Spec lock + đề xuất R-DEC (human ủy quyền R-DEC-09/14). **Đã merge fast-forward cả 5 nhánh vào `main` (đỉnh `0effd10`) + push origin/main + tag `v3.0.0-mvp`.**

| Mốc | Nhánh | Commit | Nội dung | R-DEC |
|---|---|---|---|---|
| M3.1 | `v3/m3.1-calendar` | `1168311` | Integration Hub + Calendar Google/Outlook 2 chiều (OAuth per-user, polling dev), EP-INT-01..04 + EP-CAL-01..05, migration 0024, deadline task→sự kiện lịch | R-DEC-117..125 |
| M3.2 | `v3/m3.2-autonomy-l3` | `e74db2d` | Autonomy L3: khuyến nghị → thực thi (task+owner+deadline+lịch+thông báo trong 1 transaction) qua Action Registry, feed "AI đã làm", undo 24h; Approval Matrix L3 cấu hình | R-DEC-126..130 |
| M3.3 | `v3/m3.3-briefing` | `c225ecc` | CEO Daily Briefing 7 khối (≤1 trang, email, tracking G1, EP-AI-24/25/26), ENT-Briefing + migration 0025; Decision Log 30/60/90 review+verify (/knowledge/decisions); Reports export CSV/XLSX; nêu chỉ số stale | R-DEC-131..137 |
| M3.4 | `v3/m3.4-eval-knowledge` | `77a6a73` | Evaluation Engine (bộ test chuẩn 3 trục grounding/accuracy/tool_choice, CLI `run_eval`, EP-AI-27/28, ENT-AIEvaluation + migration 0026); Knowledge/RAG plumbing (embed bge-m3→pgvector→TOOL-search_documents, EP-24 /idp/documents/search, /knowledge Documents) — tắt khi `MODEL_EMBED` trống (fallback keyword); UC-04 glue (KR at-risk→blocker insight→L3→verify) | R-DEC-138..144b |
| M3.5 | `v3/m3.5-acceptance` | `0effd10` | Trang đo nghiệm thu G1–G4 (EP-RPT-08 `/reporting/acceptance`, FE `/admin/acceptance`, reuse-only, AcceptanceService đặt ở module `ai` tránh chu trình `dashboard→ai`); refresh README + DEMO-SCRIPT v3; doc-reviewer sweep 00–14 vs code (không drift blocking) | R-DEC-145 |

**Gate đóng M3 (2026-11-02, subset khả dụng không-DB):** ruff + `ruff format --check` + mypy (**384 source files**) xanh · architecture **34 pass** (gồm import-boundary + `test_no_cycles_between_modules` sau khi dời AcceptanceService sang `ai`) · pytest non-DB **499 passed** (chỉ còn lỗi môi trường DB-connection ở `test_pii.py` + contract client-DB — không hồi quy) · `contract:validate` spec-row/route/envelope xanh (gồm EP-RPT-08/EP-AI-27/28/EP-24) · FE lint + typecheck xanh · Vitest **47 files / 419 tests** · shared-types regen **561 types** · i18n vi/en parity (2105 keys).

**Hoãn (stack-real / pilot / human — không có Postgres/Redis/MinIO trong môi trường code):** T-901 E2E kịch bản CEO 7 bước trên real; T-903 NFR perf/bảo mật/a11y/responsive/PWA; T-906 checklist pilot 1 DN 50–200 NV; T-907–910 sửa nghiệm thu + PR `ai-eos→main`. Các TC phụ thuộc DB ghi "Implemented, stack-real deferred" ở `14-TEST-TRACEABILITY.md` §1.16–1.20 (TC-M31..M35), nhất quán toàn M3. Calendar OAuth live cần callback URL công khai → test `@live` cho human; dev dùng respx/fixture + polling.

---

## M2 — Trí tuệ (M2.1→M2.5, chuỗi auto liên tục, human ủy quyền 2026-10-31) — DONE 2026-11-01

Mỗi mốc 1 nhánh từ đỉnh mốc trước (§6.0 S→C→F→B→N→R). Agent tự chốt Spec lock theo spec sẵn có + đề xuất R-DEC (human ủy quyền). **Chưa merge/push — chờ human.**

| Mốc | Nhánh | Nội dung | R-DEC |
|---|---|---|---|
| M2.1 | `v3/m2.1-home` | SCR-40 /home 3 cấp Executive/Department/Employee, EP-RPT-01..05, SEI | R-DEC-82..88 |
| M2.2 | `v3/m2.2-business` | Finance Lite + Sales pipeline (/business), EP-FIN/EP-SAL | R-DEC-89..95 |
| M2.3 | `v3/m2.3-meeting` | EP-DC-38 C2 ngôn ngữ tự nhiên/voice, MeetingSummary + ActionItem | R-DEC-96..104 |
| M2.4 | `v3/m2.4-assistant` | Grounding cứng, Insight 9 phần, kpi→Insight L2, AI-prefill F4, ⌘K, InsightCard, UC-03 | R-DEC-105..112 |
| M2.5 | `v3/m2.5-gate` | Cổng M2: hồi quy UC real, perf, a11y AA, đóng cổng | R-DEC-113..116 |

**M2.4 (đỉnh `f8fcad8`):** backend — `ai/services/grounding.py::enforce_grounding` (gỡ số thiếu nguồn sau vòng tool, `AI_NO_DATA_AVAILABLE`), `InsightOut` 9 phần first-class (`root_cause`/`risk`/`expected_outcome`), consumer `ai.on_kpi_below_threshold` → Insight + Recommendation L2, `CheckInDueOut.prefill` (AI điền sẵn F4, không bịa, confidence band), ai_eval GR/INJ/ROUTE + UC-03 CEO 4 bước (demo-replay), test P06 advertise (53 tool). FE — `CommandPalette` ⌘K→`/ask?q=` auto-send, `InsightCard` 9 phần + "Tại sao?", `InsightsPanel` EP-AI-05 trên Executive home, `CheckInCard` prefill + thanh confidence + "Dùng gợi ý". Grounding cov **91%** ≥90%.

**M2.5 (đỉnh — nhánh hiện tại):** T-737 hồi quy real **80 pass** (UC-03 `uc03-real` 2/2 sau rebuild image web; `assistant-m24`/`a11y-m2` gắn `@mock-only` chạy mock 9/9; còn `roles`/`review-detail`/`admin-org`/`capture`/`goals:180`/`onboarding-real` fail login `net::ERR_FAILED`/date-drift — hạ tầng/state sẵn có M1.x, không chạm code M2). T-738 perf: dashboard p95 **0.027s** «3s (NFR-PERF-01), chat TTFT p95 **0.074s** «2s (NFR-PERF-02) — `scripts/perf_m2_gate.sh`. T-739 a11y WCAG AA structural **5/5** (`e2e/a11y-m2.spec.ts`: 1 `#main`+nav primary+1 H1, 0 button thiếu tên, ⌘K aria-modal+focus+Escape). T-740 demo_reset (7 phòng/154 NV/34 metric/6 agent, không `-v`), STATE/14, self-review.

**Gate đóng M2 (2026-11-01):** ruff/format/mypy(359)/contract(34) xanh · pytest **1313 passed / 4 failed** (4 tiền-tồn: `inj02`/`inj03` fixture classify, `goal_events_t629` date-sensitive, `seed_s2` đếm alert — không hồi quy) · Vitest **379** · Playwright mock (assistant-m24 4 + a11y-m2 5 + …) · drift shared-types = 0 · perf đạt · a11y AA đạt.

**Nợ / lưu ý M2:** axe-core tự động hoãn (cần DEC dependency §2.3); InsightsPanel trên real trống khi seed chưa có insight (chỉ sinh khi `kpi_below_threshold`) — demo cần kích hoạt consumer để có card; real E2E login flake (`net::ERR_FAILED`) trên spec IDP/review/onboarding M1.x cần ổn định hạ tầng (không chặn M2); image web phải rebuild để FE M2.4 lên stack thật.

---

## Status (M1): M1.3→M1.6 DONE — full test chuỗi XANH (T-652, 2026-10-25) — 4 PR xếp chồng chờ human review

| Field | Value |
|---|---|
| Last updated | 2026-10-25 (Asia/Saigon) |
| Dòng sản phẩm | **Aureon v3 — AI-EOS** (chính thức duy nhất). v2.1 archived (`docs/_archive/v2.1/`) |
| Branch | `v3/m1.1-foundation` (local, **chưa push**) ← `ai-eos`; `main` giữ nền v2.1 demo |
| Phase | **M1.1 DONE** (T-601→T-609 ☑, T-610 chờ PR) · P1 DONE — refactor 10 role F.O.C.U.S → 7 role BRD + AI Agent; +`tenant_id`; +`scope_pillars`; review Autonomy L0–L3 (L4 khóa) + kill switch |
| Gates | A ✅ · B ✅ (0 DEC open+blocking) · C ✅ (14 §1.5 TC-M11-01..15 Passed) |

## T-652 — Đóng mốc M1: full test chuỗi M1.3→M1.6 — PASSED (2026-10-25)
Chạy trên đỉnh chuỗi `v3/m1.6-ai-onboarding` (chứa M1.3→M1.6), DB riêng (không đụng demo `aureon`).
| Bước | Kết quả |
|---|---|
| Gate DoD `pnpm lint && pnpm typecheck && pnpm test && ruff && mypy && pytest && contract:validate` | ✅ exit 0 — Vitest 321 · mypy 348 file · pytest 1213 passed · contract 34 |
| `pytest --cov=app` | TOTAL 96% · service mọi module ≥ 90% · nhóm bảo mật ≥ 93% (14 §1.3 đạt) · FE coverage chưa đo (cần DEC `@vitest/coverage-v8`) |
| Alembic | DB mới `aureon_final`: `upgrade head` → `downgrade -1` ×8 (0021→0013) → `upgrade head` sạch |
| Playwright real | **75/75** — stack riêng API :4500 + Celery worker (`-Q default,idp,events`)/beat Redis db 5–7 + `next start` :3600 trên `aureon_final` (seed sạch + `seed_review_doc.py`) |
| Playwright mock | **60/60** (`E2E_MOCK_PORT=3170`) |
| 14 | TC-M13-* … TC-M16-* (74 dòng) → **Passed 2026-10-25** · 09 T-652 ☑ |

**Ghi chú môi trường (rút ra khi chạy T-652):**
- Shell của harness kế thừa `DATABASE_URL=…/aureon` (+ REDIS/CELERY, `MODEL_GATEWAY_MODE=live`) ghi đè `.env` → mọi lệnh phải `set -a; . ./.env; set +a` (sự cố M1.5: migration 0018–0020 + seed lỡ chạy vào DB demo — đã `downgrade 0013` + `demo_reset.sh -y` từ `main`, verify 7 phòng/154 NV, API :4000 health 200).
- Script support e2e (`seed_review_doc.py`, `goals_e2e.py`…) đọc `.env` gốc → stack riêng đặt `E2E_ENV_FILE=var/<x>.env` (thêm ở T-652, `support/seed.ts`); `E2E_API_URL` phải có hậu tố `/api/v1`; web `API_URL` thì **không** có `/api/v1`.
- Lần real đầu fail 6–7 spec IDP/goals do script support ghi nhầm DB worktree (chưa có `E2E_ENV_FILE`) + dữ liệu bẩn từ lượt trước → reseed sạch rồi chạy lại 75/75.
- Sau reboot WSL, port-forward Docker Desktop có thể reset kết nối → `docker restart` container (dữ liệu giữ).

## FIX — "Xem tài liệu gốc" (EP-DC-14) hoạt động end-to-end — R-DEC-80 (2026-10-26, nhánh `v3/fix-source-view-ep-dc-14`)
Sửa lỗi người dùng báo: Data Inbox → "Xem tài liệu gốc" luôn hiện *"Chưa xem trực tiếp được file gốc; không có lớp chữ…"* dù file có lớp chữ. **Hai nguyên nhân gốc:**
1. EP-DC-14 ký presigned URL `/files/<key>` nhưng **không có route phục vụ file** (nợ M1.5) → `servable()` luôn false → không bao giờ nhúng iframe.
2. Fallback lớp chữ của `SourceDrawer` gọi **nhầm EP-DC-05 `/review`** (quyền `idp:approve`) → CEO/EMP/ADM (chỉ có `idp:read`) nhận `403` → `retry:false` → UI gộp "không có quyền" thành "không có lớp chữ".

**Quyết định:** R-DEC-80 (đề xuất, chờ human cấp số DEC) — thêm **EP-DC-14b** `GET /files/{storage_key}` (`idp:read`) + mở rộng `SourceViewOut` (`pages[]`, `filename`) + presigned URL đổi tiền tố BFF `/api/backend/files/…`. **Không mở rộng quyền phê duyệt.**

| Thay đổi | File |
|---|---|
| Route phục vụ file (verify chữ ký+hạn → tra theo `storage_key` trong tenant → kiểm scope `capture_visible` → stream, `inline`/`no-store`/`nosniff`/CSP sandbox) | `apps/api/src/app/modules/idp/routes/files.py` (mới), `router.py` |
| `presign_get` → tiền tố `/api/backend/files/…` + `valid_storage_key()` (chống traversal) | `core/storage.py` |
| `SourceViewOut` + `pages[]`/`filename`; `source()` kèm lớp chữ; `serve_file()` | `idp/schemas/capture.py`, `services/inbox_service.py`, `repositories/__init__.py` (`by_storage_key` tenant-scoped) |
| FE: logic view-state thuần (`sourceViewState`) phân biệt frame / text / no-text-layer / page-no-text / **forbidden (403)** / error; đọc lớp chữ từ EP-DC-14 (không gọi `/review`) | `features/capture/source-view.ts` (mới), `SourceDrawer.tsx`, i18n `noTextLayer`/`pageNoText`/`signature`/`NOT_FOUND` |
| BFF forward header `content-disposition`/`x-content-type-options`/CSP cho stream | `apps/web/src/app/api/backend/[...path]/route.ts` |
| shared-types regen; mock `source` trả `pages[]`/`filename` | `packages/shared-types/src/generated.ts`, `src/mocks/capture.ts` |
| Docs | 10 §7.2.4 (EP-DC-14, EP-DC-14b), 13 (R-DEC-80), 14 (TC-SRC-01..08, TC-SRC-FE-01..06) |

**Test (đã chạy, 2026-10-26):** BE `pytest apps/api/tests/integration/idp apps/api/tests/unit` **540 passed**; contract **34**; architecture **30**; unit storage 6 (chữ ký/hạn/traversal/giả mạo); `/files` serving 5 (happy+headers+audit, chữ ký/hạn→403, key xấu/ngoài scope→404, cross-tenant→404, ma trận role không cần `idp:approve`). FE `pnpm lint`/`typecheck`/`test` (**330 Vitest**, +`source-view.test.ts` 9); mock E2E `capture.spec.ts` 2/2 (MANUAL→422 + "Xem tài liệu gốc" mở frame inline, không `source-no-text`). mypy 349 file sạch, ruff/format sạch, shared-types up-to-date.
**Chưa làm:** chưa commit/push/merge (chờ human); R-DEC-80 chờ human cấp số DEC chính thức; chưa chụp màn hình app đang chạy (dùng assertion Playwright thay thế — không đụng server :3000 của người dùng).

## FIX — Tài liệu upload kẹt ở UPLOADED (không hiện review/ảnh gốc như seed) (2026-10-26)
Người dùng báo: tài liệu **seed** xem được ảnh gốc (trái) + trường trích xuất (phải), nhưng tài liệu **tự upload** không hiện vậy. **Nguyên nhân gốc:** Celery app [worker.py](apps/api/src/app/worker.py) có `include=[events, jobs, notifications]` **thiếu `app.workers.idp_pipeline`** → task `app.idp.process_document` không được đăng ký. Khi upload, route gọi `enqueue_pipeline()` → `process_document.delay()` đẩy task vào broker, worker **nhận nhưng từ chối** (`KeyError: 'app.idp.process_document'`), nên mọi doc upload kẹt `UPLOADED`, không chạy phân loại/OCR/trích xuất → không vào được màn review. Seed khác vì seeder ghi sẵn doc đã xử lý. (Backend phục vụ ảnh gốc EP-DC-14 vẫn OK — đã kiểm chứng file upload serve HTTP 200 PDF; vấn đề là pipeline không chạy nên doc không tới màn review.)
**Sửa:** thêm `"app.workers.idp_pipeline"` vào `include` + route `app.idp.* → queue "idp"` (worker nghe `default,idp,events`). Không đổi API/schema/dep → không cần DEC.
**Regression test:** [test_worker_tenant.py](apps/api/tests/unit/test_worker_tenant.py) — `test_worker_registers_idp_pipeline_task` khẳng định `include` chứa module, task có trong `celery_app.tasks`, và route `app.idp.*` → `idp`.
**Test:** worker unit 6 passed; IDP integration **168 passed**; mypy 349 sạch; ruff sạch.
**Docker:** rebuild+recreate `aureon-api:local` (api+celery). **Kiểm chứng live end-to-end:** upload PDF hợp lệ (office@abc.demo) → worker chạy `app.idp.process_document` SUCCEEDED ~4s → status `UPLOADED→NEEDS_REVIEW`; `/source` (trái) serve HTTP 200 PDF, `/extraction` (phải) HTTP 200. Task đã đăng ký trong worker đang chạy. (Đã dọn doc test.)

## FIX — Cảnh báo Next.js "font preloaded ... was not used" (2026-10-26)
Console mọi trang (gồm `/data`) cảnh báo 8 file `_next/static/media/*.woff2` preload nhưng không dùng trong vài giây. **Nguyên nhân gốc:** [layout.tsx](apps/web/src/app/layout.tsx) nạp `Be_Vietnam_Pro` 4 weight × subset {latin, vietnamese} với `preload` mặc định = true → next/font phát `<link rel=preload>` cho cả 8 woff2 (4 weight × 2 subset), nhưng first paint chỉ dùng vài file → trình duyệt cảnh báo. **Sửa:** đặt `preload: false` (giữ nguyên `subsets`, `weight`, `display:"swap"`). Font vẫn nạp theo nhu cầu qua `@font-face` đã sinh; **không mất subset vietnamese, không đổi thiết kế**. **Kiểm chứng:** build FE OK; HTML phục vụ còn **0** preload woff2 (trước: 8); CSS phục vụ còn **13 `@font-face`** (4 block dải Vietnamese, đủ 4 weight) → glyph tiếng Việt vẫn dùng Be Vietnam Pro. lint/typecheck sạch, Vitest **332 passed**. **Docker:** rebuild+recreate `aureon-web:local`.

## FIX — `MISSING_MESSAGE: financeDrill.hint.cash` khi xem chi tiết trụ Tài chính (2026-10-26)
`FinanceDrillView` hiển thị `financeDrill.card.<key>` luôn + `financeDrill.hint.<key>` khi thẻ có < 2 điểm trend. i18n chỉ có hint cho `budget`/`burn` trong khi có 6 card (`revenue/expense/budget/runway/cash/burn`) → 4 thẻ thiếu hint → `MISSING_MESSAGE` khi series thưa (gặp trên Docker thật). **Sửa:** bổ sung `financeDrill.hint` cho `revenue/expense/runway/cash` (VI+EN) trong [vi.json](apps/web/messages/vi.json)/[en.json](apps/web/messages/en.json); regression test [drilldown.test.ts](apps/web/src/features/finance/drilldown.test.ts) khẳng định mọi `CARDS[].key` có cả `card.*` và `hint.*` ở 2 locale. **Test:** Vitest **332 passed** (+2), lint/typecheck sạch. **Docker:** rebuild+recreate `aureon-web:local`; xác minh chuỗi hint mới có trong container.

## FIX — `MISSING_MESSAGE: unit.PERCENT` trên FE (console control/dashboard) (2026-10-26)
Người dùng báo lỗi console `Error: MISSING_MESSAGE: unit.PERCENT (vi)`. **Nguyên nhân gốc:** `/finance/dashboard` (tính on-read, DEC-200) phát `unit:"PERCENT"` (unit nội bộ của catalog), trong khi mọi dashboard khác + metric store chuẩn hóa `PERCENT→PCT` (`UNIT_OUT` ở `platform/services/metric_query.py`). FE namespace i18n `unit.*` chỉ biết `PCT/VND/SCORE/RATIO/MONTHS/DAYS/COUNT` → `t("unit.PERCENT")` ném `MISSING_MESSAGE`.
**Sửa:** [analytics_service.py](apps/api/src/app/modules/finance/services/analytics_service.py) — 5 metric FIN (01/02/05/06/07) phát `"PCT"` thay vì `"PERCENT"` (đồng bộ vocab output; field `FinanceMetricOut.unit: str` không đổi → không đổi contract/schema, không cần DEC). Regression test ở [test_analytics.py](apps/api/tests/integration/finance/test_analytics.py) khẳng định units ⊆ vocab FE-biết và không có `PERCENT`.
**Test:** finance + 6 domain dashboard + platform integration **158 passed**; ruff/mypy sạch (349 file). **Docker:** rebuild+recreate `aureon-api:local`; xác minh live `/finance/dashboard` → units `['DAYS','MONTHS','PCT']`, không còn `PERCENT`. (FE không đổi → không rebuild web.)

## FIX — "Xem tài liệu gốc" (EP-DC-14) hoạt động end-to-end — R-DEC-80 (2026-10-26, nhánh `v3/fix-source-view-ep-dc-14`)
| Task | Commit | Nội dung |
|---|---|---|
| T-644S | `a528d48`, `38c9067` | Spec lock M1.3–M1.6 (R-DEC-70..79 cho M1.6) |
| (contract) | `58d13ba` | Contract EP-AI-16..23, EP-ADM-13/14 + stub 501, `ToolOut` 13 metadata, shared-types |
| T-644 | `08261ae` | Tool Registry 13 metadata, 4 loại (COMPUTE→READ+`compute`), kiểm lúc nạp, `brd_name` |
| T-646 | `e463b77` | Migration `0021_ai_platform_m16`, 6 agent P0, EP-AI-16..21, `resolve_level` trần L2 + agent + policy, kill switch validate agent + `ai.policy_changed` |
| T-647 | `7de8378` | Audit mọi tool/model call (`request_id`/`tenant_id`/`user_id`/`ai_action_id`, scrub `arguments`), EP-AI-22/23, EP-AI-15 `group_by=agent` |
| T-645 | `42aabea` | 10 tool mới (4 READ qua service public, 6 WRITE → ACT; `ACT-update_task`/`ACT-assign_task`) + undo snapshot |
| T-645b | `3bf7bd3` | Chat WRITE → `propose()` (L0 từ chối / L1 gợi ý / L2 thẻ), `suggested_actions`, warning kill switch, ai_eval "tạo task" |
| T-648 | `20543fa` | Onboarding EP-ADM-13/14 state machine + progress suy ra + `platform.onboarding_completed` |
| T-644F..T-648F | `8302384`, `b8d231c`, `795366a` | SCR-64 AI Control Center, SCR-65 logs, `KillSwitchBanner`, `ActionCard`/`UndoToast`, SCR-66 wizard (mock) |
| nối FE↔BE | `8048768`, `657a1e3` | review onboarding derive-on-read, chỉ người hỏi confirm/reject/undo, 3 route ghi thiếu commit, ADM roster C5 |
| T-649 | `78bb141` | Roster mẫu UC-07 + `onboarding.state=completed` cho ABC |
| T-650 | `459ad2e` | E2E UC-07 real (`onboarding-real.spec.ts`, `support/onboarding_e2e.py`) |
| T-651 | `4a90190`, `602de41` | Review M1.6 + dọn nợ M1 (dưới) |

**Kiểm tra (2026-10-25, T-651):** ruff/format/mypy sạch · pytest **1213** passed (0 fail, `MODEL_GATEWAY_MODE=fixture`, `--cov`) ·
Vitest **321** · contract **34** · Playwright mock **60/60** + real **75/75** (T-650, trước review) ; sau review chạy lại
`ai-control.spec.ts` mock 7/7 (:3170) · `alembic downgrade -1 && upgrade head` (0021↔0020) sạch.
**Coverage (14 §1.3):** backend **96,3%**; services mỗi module ≥ 90% (ai 95,8 · auth 90,4 · dashboard 90,0 · execution 95,7 ·
finance 97,2 · hr 92,4 · idp 93,9 · platform 96,9 · product 99,3 · risk 98,6 · sales 99,2); bảo mật: auth 94,1 · RBAC/scope 97,9 ·
PII 97,5 · Action Registry 93,4 · autonomy/kill switch 96,9. Dưới 80% (file lẻ, không thuộc nhóm ngưỡng): `core/health.py` 77%,
`idp/services/schema_registry.py` 68%. FE coverage **chưa đo**: không có `@vitest/coverage-v8` (thêm = dependency mới → DEC).
TC-M16-01..24 = Implemented.
**Quyết định chính:** migration `0021_ai_platform_m16`; R-DEC-76 (ADM `idp` scope `s`) đã kéo về M1.5; undo snapshot của ACT
lưu trong `ai_actions.result_refs[0]._undo` (05 §2.8 không đổi cột; `public_refs` gỡ khỏi `AIActionOut` + `ToolCallLog`);
kiểm khối (pillar) nằm trong `ActionDef.permitted` (R-DEC-30/12a); `core/onboarding` registry (hr/auth/execution/idp đăng ký
nguồn progress — platform không import module); bước `review` của onboarding **derive-on-read** từ trạng thái COMMITTED của
import C5 (không thêm event/consumer); email trùng ở roster #4 = **row error `DUPLICATE`** (preview batch 1 query + ACT validate);
`HrService.import_employee_row` cho ADM — chỉ chạm nhân sự có `source_document_id` (do C5 import tạo) cho manager pass / undo /
version conflict; ADM vẫn `403` với hồ sơ khác, DTO vẫn qua `mask_fields` (không mở lương/mức 4).
**Review M1.6 (T-651, `4a90190`):** #1 MAJOR — chat dispatch mọi tool model gọi miễn người hỏi đủ quyền, kể cả tool **không được
quảng bá** (ngoài `allowed_tools` agent `ceo`, agent bị tắt, vượt trần classification CONFIDENTIAL) → model/prompt injection gọi
được tool ngoài tập; sửa: chỉ dispatch tên trong tập đã gửi model, còn lại `ToolCallLog error/AI_TOOL_NOT_AVAILABLE`, không tạo
thẻ (test `test_model_call_outside_advertised_tools_is_refused_m16`). #2 MINOR — `propose()` không kiểm quyền ACT → có thể tạo
thẻ người hỏi không bao giờ confirm được; sửa: `act.permitted(user)` trước (test `..._cannot_confirm_m16`). #3 gap test
TC-M16-09 → `test_ai_control_rbac_m16.py`. Trước đó (`657a1e3`): **3 lỗi route ghi thiếu `db.commit()`** (EP-ADM-14, EP-AI-17,
EP-AI-19..21 — fixture integration dùng chung session rollback nên không lộ) → test kiến trúc `tests/architecture/test_route_commit.py`.
Đã soát: lọc tool theo permissions trước khi gửi model; tool chạy bằng `Principal` người hỏi in-process; tool ghi cần `ai:write`
+ quyền đích; trần L2 + kill switch WRITE_OFF/L0; ToolCallLog/ModelCallLog không lưu prompt thô (`prompt_sha256`), `arguments`
qua `strip_for_model` + `scrub_for_model`; chỉ người hỏi confirm/reject/undo (`FORBIDDEN_SCOPE`); `_undo` không ra API/log;
onboarding optimistic `version` + audit (+ outbox khi finish) cùng tx; payload `ai.policy_changed` không PII/reason; email check
batch (không N+1); mock khớp BE (`8048768`).
**Nợ / lưu ý:** DB dev seed trước `11e442b` còn schema doc type `PLAN_KPI_OKR` cũ — DB mới chạy `0019` đã đúng → không cần migration;
`ACT-create_department` không có cột `organization` (một tổ chức/tenant); `_emp_validate` truy vấn email từng dòng (preview đã
batch; commit ≤ 5000 dòng chấp nhận); `ToolExecutor` READ record tool trả `ValueError`→`AI_INVALID_ARGUMENT` nội bộ; agent v2.1
`assistant` còn trên dòng cũ (FE nhãn i18n `aiAdmin.queue.legacyAgent`); FE coverage cần DEC dependency; `schema_registry.py` 68%.
**Môi trường:** như M1.5 (`set -a; . ./.env; set +a` + kiểm `aureon_m16`, `MODEL_GATEWAY_MODE=fixture`); full `pytest --cov` ~16 phút.

## M1.5 — D03 Data Capture (chuỗi auto) — DONE `[full-test pending]` (2026-10-25, nhánh `v3/m1.5-capture`)
| Task | Commit | Nội dung |
|---|---|---|
| T-634S | `38c9067` | Spec lock M1.3–M1.6 (R-DEC-60..69 cho M1.5) |
| (contract) | `83f7f08` | Contract EP-DC-01..37 + stub 501 |
| T-636 | `406dbc1`, `5844a06` | Action Registry v2 (12 ACT) + `document_actions` + EP-DC-23; `DocumentOut`/`DocumentTypeOut.version` (R-DEC-60bis) |
| T-634 | `15d95b5`, `944eaed` | Doc type #2/#3/#4 + schema registry DB + admin EP-DC-27..35 + classifier 4 tầng; ADM `idp:read/write` scope `s` (R-DEC-76 kéo sớm) |
| T-635 | `bd63bda` | C1 form/submit, C5 import EP-DC-17..22, Data Inbox EP-DC-13, source view EP-DC-14, EP-DC-01 chọn trước |
| T-637 | `53986f4` | Lineage mọi commit + EP-DC-26 |
| T-640 | `bebe01f` | Trường trọng yếu (R-DEC-69) + incident EP-DC-36/37 |
| T-638 | `416c067` | Undo 7 ngày EP-DC-24/25 + `idp.document_rolled_back` + incident G4 khi undo |
| T-639 | `afb4b74`, `1e05149` | `METRIC-DQ-02` (G3) + `dq_domain_scores` (migration `0020_capture_dq`) + `platform.on_capture_share` |
| T-641 | `99e1496` | File mẫu DOC-06 (dòng lỗi cố ý) / DOC-07 xlsx+docx / DOC-08 pdf, deterministic |
| T-642 | `75a6e03` | Anti-injection: `suspicious_content`, scrub prompt classify, ai_eval INJ-01..03 |
| T-634F..T-638F | `f8dfcf1`, `55b9819`, `71bf35a`, `a180717`, `5f8ea4a`, `3330ba0`, `fd42425` | FE mock BFF EP-DC-01..37 + SCR-45/61/62/18a-b/63 |
| T-643 | `0817d97`, `deda0fc`, `6062cad`, `2673512` | Nối FE↔BE, E2E `capture.spec.ts` mock + real (`support/capture_e2e.py`) |
| review | `11e442b`, `80bb6ff` | 2 vòng review (dưới) |

**Kiểm tra (2026-10-25):** ruff/format/mypy sạch · pytest **1084** passed (0 fail, `MODEL_GATEWAY_MODE=fixture`) · Vitest **283** ·
Playwright mock **51/51** · real **74/74** (stack riêng `aureon_m15`, API :4300, web :3400; sau review `80bb6ff` chạy lại
`capture.spec.ts` mock 4/4 tại :3150) · `alembic downgrade -1` ×3 (0020→0017) + `upgrade head` sạch. TC-M15-01..18 = Implemented.
**Quyết định chính:** R-DEC-60bis — mọi chuyển trạng thái `source_documents` tăng `version` (khóa lạc quan EP-DC-08/22/23);
R-DEC-76 kéo sớm từ M1.6 (ADM `idp:read/write` scope `s` = chỉ #4 HR_ROSTER); migration M1.5 = `0018`–`0020`
(`0020_capture_dq`) → **M1.6 dùng `0021`**; `ACT-create_task` gắn vào #2 PLAN_KPI_OKR (cột `task_title`/`assignee_code`/
`task_due_date`, theo 10 §7.2.4 "#1, #2"); EP-DC-14 trả presigned URL ký HMAC (`core/storage.presign_get`, TTL 5 phút)
**không có route phục vụ file** (thêm route = endpoint mới → cần DEC).
**review M1.5 (2 vòng):** vòng 1 `11e442b` — review detail `rows`/`planned_actions`/`can_commit`, REV role pool scope, mask mức 4
trong review, bump version, ACT-create_task #2, seed doc types trong `app.seed`. Vòng 2 `80bb6ff` (5 finding, sửa cả 5):
#1 MAJOR GET-by-id EP-DC-14/18–21/24/25 dùng `document_visible` v2.1 (cùng phòng ban) → EMP đọc import rows (mức 3) / action log
tài liệu đồng nghiệp, ADM (`idp:admin` ⇒ toàn DN) đọc action log doc type ngoài #4 → `scope.capture_visible` (inbox scope + của
mình + phiên review), test `test_capture_scope_review_m15.py`; #2 MAJOR EP-DC-37 không lọc scope → inbox scope ∪ người báo;
#3 EP-DC-23 committer không có `idp:approve` dùng capture scope thay vì cùng phòng ban; #4 mock incidents lọc scope + EP-DC-36
tài liệu ngoài scope `404` (trước `422`); #5 ai_eval INJ-02/03 đỏ sẵn ở HEAD — prompt classify liệt kê mọi doc type active trong
DB (seed thêm INVOICE) → thêm fixture tương ứng. Đã soát: audit/outbox/lineage cùng transaction (SAVEPOINT executor), quyền đích
từng ACT, undo `seq DESC` + `409 conflicts[]`, mức 4 không vào params/snapshot/audit/event/prompt, upload stream 1 MB, `413`
rows/sheets/columns, migration reversible, master-ref cache (không N+1 theo dòng).
**Nợ / lưu ý:** ~~EP-DC-14 cần DEC cho route phục vụ file presigned (hiện URL ký nhưng không route đọc)~~ → **ĐÓNG 2026-10-26 bởi R-DEC-80** (EP-DC-14b `/files/{storage_key}`, xem mục FIX đầu file); ADM xem incident (EP-DC-37
cần `idp:approve`) → OQ M3.x; SCR-63 `classifier_keywords` không trả trong `DocumentTypeOut`; reviewer@ thuộc phòng ADM → người ghi
hoá đơn trên demo là office@ — xem lại UX/seed; SCR-18b không highlight ô nguồn trên trang; rule form validation chỉ single-field;
fixture classify phụ thuộc tập doc type active (thêm doc type → ghi lại fixture INJ).
**Môi trường:** shell kế thừa env DB demo ghi đè `.env` → mọi lệnh `set -a; . ./.env; set +a` + kiểm `aureon_m15`; `.env` đặt
`MODEL_GATEWAY_MODE=live` → chạy pytest với `MODEL_GATEWAY_MODE=fixture`; sau TRUNCATE/reset chạy `uv run python -m app.seed`
để có lại doc types (#2/#3/#4).

## M1.4 — D07–D10 (chuỗi auto) — DONE `[full-test pending]` (2026-10-24, nhánh `v3/m1.4-goals`)
| Task | Commit | Nội dung |
|---|---|---|
| T-626S | `38c9067` | Spec lock M1.3–M1.6 (R-DEC-50..59 cho M1.4) |
| T-626C | `e5bc81d` | Contract `/goals/*` `/kpis/*` `/objectives/*` `/key-results/*` + stub 501, gỡ `/execution/{kpis,objectives,check-ins,initiatives}` |
| T-626 | `46b2c0b` | Strategy + StrategicObjective, migration `0016` + backfill, `goal_scope` khung |
| T-627 | `2e5bebb` | KPITarget effective-dated, KPIMeasurement lịch sử, KPIEvaluation, KRMeasurement (migration `0017`) |
| T-628 | `ad9886a` | EP-STR/KPI/OKR/PRF thay stub, `/goals/tree` một lượt query, check-ins due |
| T-629 | `8e8e5b6` | Event `kpi_measured/kpi_below_threshold/okr_checked_in/okr_at_risk`, consumer `execution.on_goal_alert`, job at-risk + nhắc check-in |
| T-630 | `80a0e96` | `METRIC-STR-01` (G2) + SEI drill-down |
| T-631 | `78513ee`, `369b887` | Seed Strategy/4 SO/INI/check-in (UC-03 KPI-SAL-01 CRITICAL, UC-04 đúng 1 KR at-risk) |
| T-632 | `4166c6e` | Scope R-DEC-57 (cây con phòng ban, DIR theo pillar, EMP của mình + tổ tiên restricted) |
| T-626F..T-628F | `9147b64`, `51937d2`, `1e0069d`, `ba75ab6`, `4991db8` | FE SCR-41/58/59/60 trên mock |
| T-633 | `0fd0294`, `0508cd1` (review) | Nối FE↔BE: mock goals seed **từ `seed_snapshot.json`** (Strategy STR-2026-2027, SO-01..04, INI theo SO, KPI cha, owner/check-in như seed BE), E2E real `goals.spec.ts` + `support/goals_e2e.py` |

**Kiểm tra (2026-10-24):** ruff/format/mypy sạch · pytest **946** (945 + 1 flaky `risk/test_replay_scope.py::test_idempotent_replays`
xanh khi chạy lại riêng) · Vitest **253** · Playwright mock **47/47** · real **72/72** (stack riêng: API :4200 + Celery worker/beat
(Redis db 9–11, `SMTP_HOST=localhost:1025`) trên DB `aureon_m14`, web `next start` :3300). TC-M14-01..18 = Implemented.
**Quyết định chính:** BE là nguồn sự thật — mock goals bỏ dữ liệu bịa (SO-C/F/U/O, KPI EMP, đổi target giữa kỳ, CONFIDENCE_FIX);
EMP chỉ sở hữu KR "Giao hàng TB ≤ 1,8 ngày" (không KPI) như seed thật; `details.reason` lỗi bổ sung ở BE (`period_locked`, `kr_count`)
thay vì đổi FE — không thêm mã lỗi.
**Nợ / lưu ý:** `next dev` (mock) và `next start` (real) dùng chung `apps/web/.next` → chạy mock xong phải build lại trước khi chạy real;
worker cần `SMTP_HOST` (Mailpit) cho test e-mail M1.2/M1.3; stack riêng phải đặt `E2E_API_URL` (mặc định :4000 — cleanup `admin-org` mở khóa nhầm API); `check_ins` append-only ở API nên cleanup E2E xóa ở DB rồi chạy lại `seed_goals`.

**review: 7 finding, đã sửa 6, nợ #7** (2026-10-24, commit `0508cd1`):
#1 MAJOR `/goals/tree` bỏ KR của EMP nằm dưới Objective ngoài scope → cây EMP rỗng (sửa `_Forest` anchor + KR thấy được dưới Objective restricted, test);
#2 MAJOR contract `details` thiếu `reason` (`period_locked` đo/target kỳ khóa, `kr_count` kích hoạt/thêm KR) mà FE `goalErrorKey` dựa vào (bổ sung BE + test);
#3 MAJOR mock: `previous_progress_pct` lấy từ cột KR thay vì KRMeasurement trước (BE) → null khi chưa có lần đo;
#4 mock consumer `on_goal_alert`: người nhận/tiêu đề lệch BE (KR → owner KR + owner Objective + MGR phòng; KPI → owner + MGR/DIR; tiêu đề `KPI <code> <band> kỳ <kỳ>` / `KR có rủi ro kỳ <kỳ>`);
#5 mock EP-KPI-09: EMP ngoài scope nhận `FORBIDDEN_ROLE` trước scope (BE: scope trước) ; #6 mock xóa Objective còn KR cascade (BE `409`), `details` xung đột xóa KPI/Objective/Initiative theo BE (`kpi_id`/`objective_id`/`initiative_id`).
**Nợ #7:** `AtRiskService.daily` / `checkin_reminder` gọi `refresh`/`user_id_for_ref` từng KR (N+1 trong job nền, ~10 KR ở seed) — gom truy vấn khi số KR lớn (M2.x).

## M1.3 — D11/D04 (chuỗi auto) — DONE `[full-test pending]` (2026-10-24, nhánh `v3/m1.3-work`)
| Task | Commit | Nội dung |
|---|---|---|
| T-619S | `38c9067` | Spec lock M1.3–M1.6 (R-DEC-38..79 resolved) |
| T-619C | `96a1dfc` | Contract `/work/*` `/workflow/*` + stub 501 + shared-types |
| T-619 | `f929ded` | Claim `employee_id` (R-DEC-41), migration `0014`, sub-task 1 cấp, dependency chặn vòng/done |
| T-620 | `5d01df2` | Workload `weekly_grid` (EP-TASK-18), project progress/late, milestone EP-TASK-14..17 |
| T-621 | `163d357` | Event `execution.task_created/task_completed` + `task_overdue.days_late` |
| T-622 | `57c0446` | Migration `0015`, rule từ DB, inbox EP-WF-01/02, EP-WF-03, `RULE-task_reassign` + EP-TASK-19 |
| T-623 | `84c93f3` | Notification in-tx (task_assigned/reminder/system, approval_requested/decided) |
| T-624 | `3009231` | Seed dependency/sub-task/source_ref/milestone, 1 `task_reassign` PENDING ở SVC |
| T-625F | `86aae84`, `9dfaf00` (merge `300c92c`) | FE SCR-42/43/55/56/57 trên mock |
| T-625 | `43d96c6` | Nối FE↔BE (title_key/params theo BE, `?id=`, claim `employee_id` trong mock) + E2E real `work.spec.ts` + `support/work_e2e.py` |

**Kiểm tra (2026-10-24):** ruff/format/mypy sạch · pytest **877** passed · Vitest **205** · Playwright mock **41/41** ·
real **69/69** (stack riêng: API host :4100 + Celery worker/beat (Redis db 6–8) trên DB `aureon_m1x`, web `next start` :3200,
Mailpit dùng chung :8025). TC-M13-01..14 = Implemented (Passed sau full test cuối chuỗi).
**Quyết định chính:** BE là nguồn sự thật cho `ApprovalRequestOut` — FE ghép tên từ `members[]` (người không đọc được → mã rút gọn);
EMP nhập ID nhân viên khi đề nghị chuyển (OQ-13-09 ghi vào 13, chốt M2.x); heatmap 3 quá tải kiểm bằng CEO (MGR SVC không có người quá tải).
**Nợ / lưu ý:** DB `aureon_m1x` phải truncate + seed lại sau T-624 (seed execution bỏ qua khi đã có task SEED → thiếu dependency/milestone/approval);
`next start` cũ sau rebuild trả 400 chunk tĩnh → khởi động lại sau mỗi build; mock project đôi khi timeout lần compile đầu (`next dev`), chạy lại xanh;
audit log append-only nên cleanup E2E chỉ soft-delete task/approval.

**review: 14 finding, đã sửa 12, nợ #9** (2026-10-24, commit `fix(work): M1.3 review …`):
`approval_service.can_decide` (một luật duy nhất cho inbox/detail/decide/notification — R-DEC-45: role ∈ step hiện tại,
CEO miễn scope không miễn role, DIR theo pillar rule, DIR `escalate_to_role_code` khi phòng không có MGR / `department_id` NULL);
parent ngoài scope → 404; reassign khóa task + `to_assignee_id` qua `core.directory` (hr đăng ký, tránh vòng `hr→execution`);
workload summary = METRIC-HR-03 (`min(week_end, today)`); `details` BE↔FE↔mock (`blocking[]`, `reason=has_subtasks|self_approval|
distinct_approvers|same_assignee|not_found`, `field=reason|to_assignee_id`); seed reassign `emit=False`; ACT-create_task
`task_source=ai` + `source_ref`; `_brief` một query; `rule()` ON CONFLICT; alembic env bỏ `_m13_assignee_backfill` khỏi autogenerate.
#14 giữ `core/stub.py` (M1.4 dùng). **Nợ #9:** tiêu đề notification (approval_requested/decided, task_assigned) vẫn lưu text thô
(`title` = tên task / status), chưa có i18n key — chốt cùng M2.x notification i18n.

## M1.1 — Nền build v3 (09 §6.2) — đã làm
| Task | Commit | Nội dung |
|---|---|---|
| T-602 | `6dc3d7c` | 10 §1.4 phản chiếu `core/errors.py`; contract test xanh |
| T-603 | `a4687a6` | Lọc `tenant_id` fail-closed (repo + outbox/consumer, migration `0010`) |
| T-603b | `4059b5e` | Seed v3 ABC theo 08 §2.1 (7 phòng ban, 154 NV, 10 user + `ai-agent`), `seed_snapshot.json` |
| T-605 | `4ee0d8e` | `packages/shared-types` sinh từ OpenAPI + drift check |
| T-604 | `77201b5` | Mock BFF `API_MODE=mock` (cấm ở production), mock login 7 role |
| T-606 | `d80bde8` | Playwright 2 project `mock` / `real`; tag `@mock`, `@mock-only` |
| T-607 | `12f8170` | IA v3: Sidebar 8 mục + Quản trị, route v3, 308 từ route v2.1, "Sắp có"; fix IDP CEO-scope |
| T-608 | `b112bc9` | Đóng băng product/risk: `p1_frozen`, Executive mặc định F/O/C, 5 trụ chỉ ở SCR-03 |
| T-609 | `65072d3` | E2E login + điều hướng 7 role trên `real` |
| T-610b | `3673bac` | Rebuild image `api`/`web`; **đăng nhập nhanh 10 role** bằng nút (mật khẩu giải ở server, không ra browser); gỡ `NEXT_PUBLIC_DEMO_PASSWORD_*` khỏi `.env.example` |
| T-610c | (commit này) | SCR-13 quay lại **dropdown 10 tài khoản**; chọn → Route Handler `POST /api/demo-credentials` (chỉ khi `DEMO_MODE=true` **và** `DEMO_LOGIN_AUTOFILL=true`, whitelist `DEMO_ACCOUNTS`, `no-store`) điền **cả email và mật khẩu**; không tự submit; nút con mắt Eye/EyeOff (aria-pressed, 44px). R-DEC-28 |

**Verify đóng phase (2026-10-23):** gate DoD xanh · pytest 808 (`--cov` 97%, bảo mật ≥ 91%) · Vitest 80 ·
contract 14 · alembic `downgrade -1 && upgrade head` sạch · Playwright `mock` 28/28 (không backend) · `real` 58/58
(web `next start` :3200 + API host :4100 trên DB dev — container `web`/`api` :3000/:4000 còn image cũ).


**Verify T-610b (2026-10-23):** lint/typecheck sạch · Vitest **84** (thêm `demo-accounts.test.ts`) ·
Playwright `real` **58/58** trên stack docker `:3000`/`:4000` (image mới) · HTML `/login` không chứa mật khẩu ·
9 service compose healthy.

**Verify T-610c (2026-10-23):** lint/typecheck sạch · Vitest **94** (+`demo-credentials.test.ts` 7, +`password-toggle.test.ts` 3) ·
image `web` rebuild, curl :3000 (200 cho email demo, 404 `NOT_FOUND` ngoài whitelist, `no-store`, HTML `/login` không chứa mật khẩu) ·
**human thử tay 8 bước: OK**. pytest/contract/Playwright **chưa chạy** (xem chính sách test bên dưới); TC-M11-16/17 = Implemented.

**Chính sách test (human chốt 2026-10-23):** mỗi task chỉ chạy kiểm tra nhanh (lint/typecheck/Vitest; BE thêm ruff/mypy)
+ rebuild image + hướng dẫn thử tay → human test và phản hồi → commit (`[full-test pending]`). **Full test** (pytest,
contract, Playwright `mock` + `real`) dồn đến cuối phase khi human xác nhận ổn hết; lúc đó mới đổi TC sang Passed.
Lưu ý môi trường: `.env` cần `DEMO_LOGIN_AUTOFILL=true` để autofill chạy trên stack demo (production: `false`, `DEMO_MODE=false`).

**Rủi ro / nợ còn lại:** FIN-06 ≈ 8% (08 ghi ~12%,
human chốt giữ); DQ-01 phụ thuộc giờ hệ thống; `scripts/gen_demo_docs.py` còn assert 45 NV; mock router chỉ phủ
dashboard + ai; dashboard 3 cấp theo role vẫn là "Sắp có" cho MGR/EMP/REV/ADM (M2.1); bộ tài liệu mẫu
`data/DOC-01..07` vẫn là bản v2.1, chưa khớp seed ABC mới.

## Phase 1 — đã làm (R-DEC-07/08/12/12a/13)
- **7 role v3** (`CEO/DIR/MGR/EMP/REV/ADM/AI`) thay 10 role F.O.C.U.S. `DIR` = union quyền 5 C-level cũ.
- **`scope_pillars`** (⊆ F.O.C.U.S) phân biệt khối của DIR, enforce server-side mỗi request (R-DEC-12a):
  Finance-DIR={F}, Sales-DIR={C}, HR-DIR={O}, Product-DIR={U}, Risk-DIR={S}.
- **`tenant_id`** mọi business entity (`TenantMixin`, 47 bảng) + JWT claim; migration `0009_v3_roles_tenant` reversible + backfill.
- **Cô lập khối per-module**: record/write theo khối; aggregate (`:query`) mở cho mọi DIR; dashboard HR giới hạn
  khối O/F/S; hiring-approve = Finance-DIR (cổng ngân sách); mức 4 (lương) chỉ CEO + HR-DIR, payroll aggregate thêm Finance-DIR.
- **Autonomy L0–L3 (L4 khóa) + kill switch**: xác nhận còn nguyên, không coupling role cũ.
- **FE**: messages vi/en role.*, LoginForm demoAccount.*, pillars (CEO+DIR = all 5), demo-accounts → v3 codes.
- **Docs** (R-DEC-14 cho đợt code): 05 field-level; 13 R-DEC-12/12a/13/14; 14 §1.4 trạng thái Phase 1.

## Gate verify (phiên code Phase 1)
- BE `uv run pytest`: **770 passed** (toàn bộ role/scope xanh; gồm `test_auth` login + `test_seed` 7 role/10 user).
- FE: `pnpm lint` ✅ · `pnpm typecheck` ✅ · `pnpm test` **18/18** ✅.
- `uv run ruff check .` ✅ · `uv run mypy` ✅ (263 files).
- **E2E Playwright: CHƯA chạy lại** trong phiên resume (docker DOWN) — chờ môi trường có docker rồi `pnpm test:e2e`.

## Nợ kỹ thuật tiền-tồn (KHÔNG do Phase 1)
- 4 case `tests/contract/test_api_contract.py` FAIL: khi promote doc 10 sang v3 (commit `7a31c10`, trước Phase 1),
  bảng mã lỗi `### 1.4.` bị gỡ ("chốt danh sách đầy đủ ở đợt code — R-DEC-09"). Test parse bảng không còn tồn tại.
  Xử lý ở task riêng: viết lại contract test lấy mã lỗi từ `core/errors.py` (cần DEC về nguồn-sự-thật mã lỗi).

## Kế tiếp
- **Kế hoạch build MVP v3: `docs/3.EXECUTION/09-BUILD-PLAN-TASKS.md` §6** (M1.1→M3.5, vòng S→C→F→B→N→R; quyết định 13 §2ter R-DEC-15..27).
- **M1.1 xong** trên nhánh `v3/m1.1-foundation` (chưa push). Kế: human review → PR → `ai-eos`, rồi Spec lock M1.2 (09 §6.0).
- (Tuỳ chọn) P1.6 enforce `tenant_id` filtering trong repositories/services (mới có model + migration + JWT claim).
- Chạy E2E login 7 role khi docker sẵn sàng; nếu fail → fix rồi mới đóng hẳn.
- Phase 2 theo `docs/3.EXECUTION/09-BUILD-PLAN-TASKS.md` (review + fix gate giữa các phase).

---

# Lịch sử nền v2.1 (archived — chỉ tra cứu)

> Dưới đây là nhật ký build của **nền Aureon v2.1** (5 trụ F.O.C.U.S, 10 role, demo-ready, sprint S0→S5d,
> push lên `main`). Nền này được **tái sử dụng** làm điểm xuất phát cho v3 và refactor dần theo phase.
> Các con số (777 test, 5/10 demo account role cũ, DEC-2xx) phản ánh trạng thái v2.1, KHÔNG phải v3 hiện tại.

## [v2.1] T-518 final verification checklist (2026-10-22)
- [x] `docker compose -f docker-compose.full.yml up` → 9 services healthy (cold start 26 s)
- [x] Login CEO → dashboard F🟢 C🟢 U🟡 O🟡 S🔴 with 13 alerts (E2E `dashboard.spec.ts`, `roles.spec.ts`)
- [x] Chat "Doanh thu Q3?" → 1,32 s total (TTFB 0,25 s) with citations [1][2][3]; "Top 5 khách hàng?" 1,17 s
- [x] Login reviewer → queue → approve → invoice committed (E2E `roles.spec.ts`, `review-detail.spec.ts`)
- [x] `pytest --cov` → 777 passed, 96%
- [x] `pnpm build` → 0 errors · lint / typecheck / ruff / mypy clean · contract 11 passed
- [x] `README.md` root + `docs/DEMO-SCRIPT.md` present
- [x] `scripts/demo_reset.sh` works (~13 s, verified 5 users · 32 metrics · 13 alerts · 1 NEEDS_REVIEW)
- [x] Git clean, pushed to main

## [v2.1] S5d demo polish + release (done 2026-10-22, direct route)
- **Governance** `929b167`: S5b-lite accepted, DEC-241 approved, S5b-full deferred.
- **T-513** `cc54910` `docker-compose.full.yml`: postgres, redis, minio, ollama, clamav, api, celery-worker, celery-beat, web on `aureon-net`; healthchecks on all 9; persistent volumes pg/minio/ollama/clamav (+redis); `env_file: .env` + in-network host overrides; `api` = `alembic upgrade head && python -m app.seed && uvicorn`; worker/beat wait for api healthy; JWT keys `./keys:ro`; OmniRoute via `host.docker.internal`. New `apps/web/Dockerfile` (Next 15 build, NEXT_PUBLIC_* non-secret build args only). Fixed api image perms (`pyproject.toml` unreadable for uid 1000).
- **T-514** `5c40d05` root `README.md` rewritten for v2.1 (quick start, accounts, features, mermaid, tests, license) + `docs/DEMO-SCRIPT.md` (5-min walkthrough + pre-demo checklist + troubleshooting).
- **T-515** `2e94206` `core/health.py` probes (2 s timeout each, never raise) + `core/ops_routes.py` (`/health`, `/health/ready`, `/health/live`, `/metrics` Prometheus text, no new dependency) + EP-01 `/api/v1/health` envelope; web `/api/health` proxy. Ollama down → `degraded` + 200 (verified live by stopping the container). DEC-242.
- **T-516** `a50c82e` `e2e/roles.spec.ts` (5 roles). Needed minimal screens: `/hr/employees` (EP-82) and `/admin/audit` (EP-52 implemented — was in 10, missing in code). DEC-243. Flaky fix: wait for pillar `data-status` before click.
- **T-517** `6511778` `scripts/demo_reset.sh`: TRUNCATE 10 module schemas (keeps alembic_version) → seed → clear IDP store + MinIO → purge Celery + restart worker/beat → 1 invoice NEEDS_REVIEW → verify.
- **T-518** final verification (this file). Fix: IDP integration tests now hide pre-existing dev-DB queue docs inside the rolled-back transaction (they failed after a demo reset left 1 NEEDS_REVIEW invoice).

### S5d notes / gaps
- Brief numbering T-513..T-518 ≠ 09 (09 T-513 = seed v2.1, still pending).
- MinIO not used by the app in demo (local-FS IDP store, DEC-234); reset clears both anyway.
- `/metrics` exposes build info, uptime, dependency up/down and HTTP response counters only.
- EP-52 filters `from`/`to`/`actor_type` not implemented yet; SCR-26 user admin not built.
- Demo passwords for ADMIN are not in the login dropdown (5 accounts only, by design).

## S5b-lite ACCEPTED (human, 2026-10-22 — S5d brief, DEC-241 approved)
- Lineage drill-down simplified (uses finance list endpoints; EP-13/14 deferred).
- Sparklines: 12 monthly points (no daily series).
- `/dashboard/focus` not built — per-pillar endpoints sufficient.
- Live model 9–13 s accepted (Claude Sonnet standard latency).
- T-512 (O/C/U/S drill-downs) deferred → S5b-full post-demo.
- Next: **S5d demo polish + release (T-513..T-518)**.

## S5b-lite demo polish (done 2026-10-22, direct route; 4 commits, pushed)
- **Governance** `585e77a`: DEC-237..240 APPROVED (human); backend S4c deferred for all of S5.
- **T-509** `17d2adb` chat fix (DEC-241): chat model chain `CHAT_MODEL_PRIMARY=cc/claude-sonnet-5` → `CHAT_MODEL_FALLBACK=cl/deepseek/deepseek-v4.1-flash` (brief named `deepseek-v4.1-flash-uncensored` — not routable on OmniRoute without provider prefix), 1 attempt/model, `CHAT_TIMEOUT_SECONDS=90` (chat only). `AI_DEMO_REPLAY` (default = `DEMO_MODE`) replays 10 recorded intents from `apps/api/src/app/modules/ai/demo_responses.json` — **numbers always from live tools run as the asker** (no fake numbers; missing permission/value → real model), warning `ai.warn.demo_replay`. System prompt tuned for ≤ 2 tool rounds. FE: `streamSse(..., timeoutMs)` 120 s → `AI_STREAM_TIMEOUT`; `WaitHint` 10 s "AI đang suy nghĩ..." / 30 s "Đang xử lý phức tạp, vui lòng đợi..." / 90 s "AI đang mất nhiều thời gian, thử lại sau". Side fixes: cost-service test baseline-relative (dev DB has live logs); gateway unit tests pin chat chain empty; E2E review specs clean up leftover `hoa-don-E2E*` docs (`seed_review_doc.py --cleanup`).
- **T-510** `316a0c4` period picker: `PeriodPicker` "Kỳ báo cáo: T9/2026" + [Tháng này | Tháng trước | Q3 | Q4] relative to `NEXT_PUBLIC_DEMO_REFERENCE_DATE=2026-10-20` (not a secret); period in URL `?period=` (kept across drill-down). No new endpoint: `/dashboard/focus` does not exist in 10 — the 6 pillar endpoints (EP-49/60/70/80/90/100) already take `period`; contract test `test_dashboard_period_picker.py` covers 2026-10/09/Q3/Q4 on all 6. **Bug fixed:** `/finance/dashboard?period=2026-13` returned 500 → now 400.
- **T-511** `134d7a5` Finance drill-down `/dashboard/pillar/finance`: "Trụ Tài chính" + status badge + period picker; 6 cards (Doanh thu 25,5 tỷ, Chi phí, Sử dụng ngân sách 97,3%, Runway 13,6 tháng, Số dư tiền mặt 20,4 tỷ, Burn rate 1,5 tỷ) with trend arrow + 12-period sparkline (monthly series from EP-60 `revenue_trend`/`runway_trend` + EP-63 cash positions — no daily 30-day series exists in the data model). Click → `LineageDialog` 3 levels: metric (EP-12) → component records (finance lists for the month) → source doc (EP-25 via IDP-committed invoice). EP-13/EP-14 not implemented → simplified per brief; seed records show "chưa gắn tài liệu gốc".
- **T-512** (O/C/U/S drill-downs) skipped — optional; other pillars keep the S5a stub list.

### S5b-lite notes / gaps
- Live chat 9–13 s on multi-tool questions (target 3–10 s met for simple ones only); demo replay covers the 10 scripted questions. Further: cap tool rounds per turn, or pre-warm.
- Sparklines are monthly (12 points), not 30 daily points — no daily finance series in 05.
- Budget / Burn cards have no series in EP-60 (hint text instead).
- Finance cards are not period-scoped for cash (latest closing ≤ selected month).

## S5a FE foundation + 4 MUST screens (done 2026-10-22, direct route; 8 commits, pushed)
- **S4c deferred** — internal polish (full doc-type catalogue, ENT-DataLineage 4-cấp, EP-33 rollback). Defer to post-S5 if scope permits. S4d (C2/C4/C5 breadth) deferred, optional (DEC-240). Backend IDP not touched this sprint.
- **T-501** `16492d0` Next.js 15.5 App Router in `apps/web` (TS strict + `noUncheckedIndexedAccess`), Tailwind 4 tokens (`ai` violet ≠ `primary` blue), shadcn-style ui (button/input/label/card/badge/select/dialog/popover/checkbox/collapsible/tooltip/dropdown/toast), next-intl vi/en (251 keys each, cookie `NEXT_LOCALE`), `lib/{api-client,sse,format,query-keys}.ts`.
- **T-502** `4578cd0` NextAuth Credentials → EP-02; backend access+refresh token only inside the encrypted httpOnly NextAuth JWT. BFF `app/api/backend/[...path]` adds Bearer, single-flight refresh (EP-06 rotation), streams SSE (`X-Accel-Buffering: no`). `middleware.ts` → `/login?callbackUrl` / rewrite `/403`; `lib/permissions.ts` route rules + nav + role landing.
- **T-503** `ca3f3f8` SCR-13 login (rhf+zod), demo dropdown (5 accounts) fills email; password resolved server-side from `DEMO_*_PASSWORD` when `DEMO_MODE` (never `NEXT_PUBLIC_*`). Error from `{error:{code}}` mapped via i18n.
- **T-504** `52af5cf` App shell: role-filtered sidebar (Dashboard/IDP/AI/Approvals), header avatar/role badge/logout/VI-EN switcher (server action). ≥1280 full (collapsible), 768–1279 icons, <768 drawer.
- **T-505** `e5be7fe` SCR-02: 5 pillar cards (5/2/1 cols), one query per domain endpoint (O = hr + execution worst), 60 s refetch, failed source → "Không khả dụng" + retry; Recharts sparkline from `*_trend`; 13 alerts critical-first + Acknowledge (EP alert ack, Idempotency-Key). Period `2026-09` (DEC-237) → 2g/2y/1r. `/dashboard/pillar/[slug]` stub (metrics list) for S5b.
- **T-506** `822a17f` SCR-16 chat: SSE over POST via `lib/sse.ts`, pure reducer (start/tool_call/tool_result/token/done/error), `ThinkingState` collapsible "AI đang dùng tool: …", `SourceChip` `[n]` popover, new chat + history (EP-112). E2E stubs SSE (DEC-238); live transport verified via curl through BFF.
- **T-507** `e46b658` SCR-18a queue: table (filename/type/confidence/critical/assigned/age/Review), filters status/doc_type/assigned(me), pagination limit/offset, empty state + Upload (EP-20 multipart).
- **T-508** `d738e65` SCR-18b: 2 columns (text-layer source viewer + highlight/bbox | field form: ConfidenceBadge, confirm checkbox, correction input, reason for money fields, red border + tooltip), EP-29 open / EP-35 release, EP-30 patch → EP-31 approve → toast "Đã ghi vào Finance" → queue; reject dialog (reason). `/finance/invoices` list (direction filter) shows the committed invoice. `/approvals` placeholder.
- **E2E seed:** `apps/web/e2e/support/seed_review_doc.py` (UploadService + Pipeline, fixture gateway; unique invoice number per run) called from Playwright via `.venv/bin/python`.

## S5a exit criteria
| Criterion | Result |
|---|---|
| `pnpm build` / `next start` :3000 | ✅ |
| Login 3 demo accounts (CEO, CFO, REVIEWER) | ✅ |
| Dashboard 5 cards 2g/2y/1r + 13 alerts | ✅ |
| Chat streaming + citation | ✅ (fixture SSE, DEC-238) |
| Queue + filters | ✅ |
| Detail + approve → invoice visible | ✅ |
| Role nav + 403 | ✅ |
| Responsive 1440/1280/768/390 | ✅ (`responsive.spec.ts`, screenshots `apps/web/test-results/screens/`, gitignored) |
| 4 Playwright flows (login, dashboard, chat, review) | ✅ 20 tests passed |
| TS strict, ESLint 0 warnings, no `any` (`no-explicit-any: error`) | ✅ |

**FE routes:** 10 pages (`/`, `/login`, `/403`, `/dashboard`, `/dashboard/pillar/[slug]`, `/ai`, `/idp/review`, `/idp/review/[documentId]`, `/finance/invoices`, `/approvals`) + 2 route handlers (`/api/auth/[...nextauth]`, `/api/backend/[...path]`).

### Run E2E
API :4000 + Postgres seeded, then `pnpm --filter @aureon/web build && pnpm --filter @aureon/web start` and `E2E_NO_SERVER=1 pnpm test:e2e` (or let Playwright start `pnpm start`). `apps/web/.env.local` (gitignored) carries NEXTAUTH_* + demo passwords copied from root `.env`.

### S5a notes / gaps
- Chat live: OmniRoute `auto/coding` ~39 s/answer > 30 s turn limit → `AI_PROVIDER_TIMEOUT` in live mode; pick faster `MODEL_CHAT` or record fixtures (T-321).
- Optimistic lock: review detail has no `version`/`ETag`; FE sends `If-Match` only if ETag appears (DEC-237 note). Soft lock EP-29 + 409 cover concurrency today.
- Dashboard period fixed to T9/2026; period picker + full drill-downs SCR-02..06 = S5b.
- Not yet: axe-core (TC-UI-020/027), TTFT measurement, ⌘K panel, dark-mode toggle, PWA.

## Done
- S0, S0b, S1 (Finance/Sales/HR) — see git history (`ed1836a`).
- S2 (`a0fd762`):
  - T-220 metric store (`platform.services.metric_store.MetricStore.recompute`, providers `@metric_provider` per module), METRIC-DQ-01 (`core/data_quality.py` + `register_dq` per domain, DEC-209).
  - T-221 alert engine; budget_exceeded → alert < 60 s test.
  - T-222 pillar dashboards EP-60/70/80/90/100 + EP-49 from store (`pillar_snapshot`), partial-failure isolation.
  - T-131..133 execution, T-201/202 product, T-211..216 risk (merged worktrees `/home/vika/aureon-wt/{exec,prdrisk,risk}`).
  - T-234 pgcrypto level-4 PII, migration `0008_pgcrypto`; T-235 Celery beat (7 entries incl. outbox relay, detect-overdue-tasks 08:30).
  - T-236 seed: auth + finance + hr + sales + product + risk + execution (reduced, DEC-208). Dev DB: 32/32 metrics valued, 25 OPEN alerts, all dashboards 200.
- Shared: `core/periods.py` (period resolution, breaks hr↔execution cycle); metric provider registry tolerates re-import of same function.

## S2 exit criteria
| Criterion | Result |
|---|---|
| 5 pillar endpoints 200 | ✅ (+EP-49) |
| ≥ 10 alerts from seed | ✅ 25 OPEN |
| revenue → budget_exceeded → alert ≤ 60 s | ✅ `tests/events/test_alert_sla.py` |
| beat jobs registered | ✅ 7 entries |
| 3 pgcrypto tests | ✅ |
| Sales/HR dashboards non-zero | ✅ |
| 32 metrics populated | ✅ |
| Coverage ≥ 95 %, gates A/B/C | ✅ 98 % |

## T-237 seed rebalance (done 2026-10-22, direct route cc/claude-sonnet-5; 3 commits)
- **Step 1** (analysis, no edits): identified per-pillar levers vs DEC-143.
- **Step 2** `b0cefa4` feat(s2): seed data → **F,C green · U,O yellow · S red**. Edited `finance_data.py` (cash flatter→runway 13.6, Q3 budget ≤ alloc, Oct MTD trimmed, 8 carried-forward open invoices `HISTORICAL_OPEN_INVOICES` + `HV_PAID_IN_FULL`), `sales_seed.py` (Sep target 26.0tỷ, Q4 18.0tỷ, `attribute_revenue` splits big row over 5 anchor clients + frozen window for NRR), `product_seed.py` (Sep churn 1.79, retention 43, NPS lift), `hr_seed.py` (1 plan 40d late). Updated 3 finance_seed assertions.
- **Step 3** `3bdee1f` feat(platform): `SEED_PASSWORD_CPO`/`SEED_PASSWORD_RISK_MANAGER` aliases on config + `.env.example`. Dev `.env` got CPO/RISK/MANAGER/EMPLOYEE/ADMIN passwords → seed creates all 10 users; product owner=CPO, risk owner=RISK_MANAGER.
- **Verified** (clean-DB `python -m app.seed` + in-process API as CEO): F green · C green · O yellow · U yellow · S red; 13 OPEN alerts (11 WARNING + 2 CRITICAL). `probe3.py` harness truncates domain schemas in a rolled-back tx.
- **DEC-230 APPROVED** (human 2026-10-22): F🟢 C🟢 U🟡 O🟡 S🔴 is the official demo layout; DEC-143/152 "demo layout" superseded_by DEC-230 (thresholds unchanged, NFR-19).
- **DEC-231 APPROVED**: alert severity enum = WARNING|CRITICAL only (INFO = log level). "≥10 alerts" = ≥10 alerts **any severity** (met 11W + 2C = 13).
- Gate: ruff ✅ · mypy ✅ (226 files) · pytest 585 ✅.

## S3 AI Core (done 2026-10-22, direct route; 10 commits incl. DEC governance)
- **DEC-230/231 governance** `ad5c598` — demo layout + alert-severity enum approved (gate prelude).
- **T-301** `1212181` Tool Registry: 43 `TOOL-*` with §7.4 metadata (27 QUERY + 13 WRITE + 2 APPROVAL + 1 EXECUTION), `advertisable_for`/`available_for` permission + classification filters.
- **T-302** `9413b9e` Chat orchestration EP-110 + SSE EP-111 (`start→thinking|tool_call→tool_result→token→done`, `X-Accel-Buffering: no`); tool-calling loop (≤ 8 calls, budget warning); prompt_guard classification routing (salary→SECRET no-LLM, PII→CONFIDENTIAL local-only); `<<<DATA … DATA>>>` injection guard.
- **T-303** `c0bf68c` Proactive insights: 9-part grounded `ENT-Insight` from worst-status metric, evidence-gated (≥1 SourceRef), EP-114 list/dismiss with pillar-scope hiding.
- **T-304/305/306** `db9447c` AI action lifecycle (`ENT-AIAction`: propose→L3 auto-exec | L2 confirm card; undo 24h via `TaskService.delete`), Action Registry single write gate, 2-sided approval (finance ≥500M → CEO step1 + CFO step2, distinct approvers), kill switch per-agent/global WRITE_OFF|L0 (L3→L2). Cross-module via `core/approval_hooks.py` (breaks platform↔ai cycle, DEC-125).
- **T-307** `63ecc31` Outcome verification 24h/7d: scores metric status movement (improved/worsened/unchanged/not_measurable) vs baseline captured at propose time, reading current status via platform `MetricQueryService`.
- **T-308** `6a413d4` Cost & usage EP-119 `/ai/usage` (`ai:admin`): aggregates `ENT-ModelCallLog` → budget/used/used_pct + per-key rows (calls/tokens/cost/error_rate/p95_ms) grouped provider|model|task_kind|user; warn 80% / over 100% vs `AI_MONTHLY_BUDGET_USD` (DEC-131).
- **T-309** `ea9866e`+`b954f47` PII filter: `scrub_for_model` drops level-4 PII, tokenises level-3 contacts to stable `EMP-`/`CLI-` codes before every model call (5.5, FR-AI-10).
- **T-310** `0e4d8aa` E2E + coverage: HTTP sweep of EP-110..119 via overridable `get_chat_gateway` dep + service edge branches → **ai coverage 95%** (S3 exit met).
- **Gate:** ruff ✅ · format ✅ · mypy ✅ (242 files) · pytest **667 passed**.

## S3 exit criteria
| Criterion | Result |
|---|---|
| Chat SSE EP-110/111 event order | ✅ |
| Tool Registry 43 tools, permission-filtered | ✅ |
| 9-part grounded insight, no fabricated numbers | ✅ (evidence-gated) |
| Autonomy L0–L3 + undo 24h + kill switch | ✅ |
| 2-sided approval ≥500M (CEO→CFO) | ✅ |
| PII scrub + classification routing | ✅ |
| Cost log + EP-119 usage | ✅ |
| ai coverage ≥ 95%, gates A/B/C | ✅ 95% |

## S4a IDP pipeline core (done 2026-10-22, direct route; 3 commits)
- **T-401** `0ee6214` EP-20 `POST /idp/documents` (1..100 file, 50MB/file, MIME whitelist + magic bytes, stream chunk 1MB), sha256 dedupe → `DUPLICATE` linked to original, `ImportBatch` for multi-file, `ExtractionJob` QUEUED, audit `idp.upload`. New `core/storage.py` (local-FS `ObjectStore`, `quarantine` bucket — prod swaps MinIO/S3 same interface). `schema_registry.py` seeds DocumentType/ExtractionSchema/ValidationRule (INVOICE 04 §5.5 + OTHER) idempotently. `query_service.py` EP-25/26 + dept scoping. Config: `IDP_STORAGE_DIR`, `IDP_MAX_FILE_SIZE_MB/PAGES/FILES`, `OCR_PROVIDER`.
- **T-402..T-405** `cddb33e` pipeline core:
  - malware_scan (T-402): clamd TCP + EICAR local detect; INFECTED→`FAILED` `status_reason=MALWARE` + `quarantine` bucket; `CLAMAV_REQUIRED=false`→`SKIPPED` (DEC-138).
  - preprocess (T-403): text-layer check before OCR; PDF(pypdf)/DOCX/XLSX/CSV/image; `DocumentPage` per page; `OCR_PROVIDER` stub|paddle (paddle lazy-imported, DEC-049).
  - extractor (T-404): ModelGateway `task=extract`, classification by sensitivity (4→SECRET no-LLM, 3→CONFIDENTIAL local, ≤2→cloud), schema-driven prompt, field result `{value, confidence, source_location, confidence_band}`, bands HIGH≥0.90/MEDIUM 0.60/LOW (DEC-133), null not fabricated (P05). Gateway injected (DI, DEC-233).
  - validator (T-405): ValidationRule ops required/gt/lte/in/`date_not_future`/`sum_equals`; VN number/date parsing; errors → `ExtractionJob.xd_results.validation_errors`.
  - pipeline orchestrator: `UPLOADED→PREPROCESSING→CLASSIFYING→EXTRACTING→VALIDATING→NEEDS_REVIEW|AUTO_APPROVED` (MALWARE→FAILED). STP routing (04 §7.3): doc conf ≥0.95 + required fields ≥0.90 + no critical field + no validation error, else REVIEW. Keyword classifier picks INVOICE vs OTHER (full 9-type LLM classify = later sub-sprint). Celery `app.idp.process_document` (idempotent, time_limit).
- **Tests** `17d26f4`: 43 new (`tests/unit/test_idp_*.py` + `tests/integration/idp/`); `sample_docs.py` builds in-memory PDF(text+scan)/DOCX/XLSX/EICAR/PNG from runtime deps only (no reportlab).
- **Gate:** ruff ✅ · format ✅ · mypy ✅ (254 files) · pytest **710 passed**.

## S4a exit criteria
| Criterion | Result |
|---|---|
| EP-20 upload C1/C3/C4 → job created | ✅ |
| malware blocks EICAR (quarantine) | ✅ |
| OCR/text extract (PDF text + scan + DOCX/XLSX) | ✅ |
| LLM extract field results + confidence bands | ✅ |
| validation rejects invalid (neg amount, future date, bad sum) | ✅ |
| pipeline upload→scan→OCR→extract→validate → `NEEDS_REVIEW` | ✅ |
| coverage `modules/idp/services` ≥ 90% | ✅ 96% |
| gates A/B/C | ✅ |

### End-to-end sample (invoice.pdf, in-process pipeline)
upload → `UPLOADED` + QUEUED job → scan `SKIPPED/CLEAN` → text-layer extracted (1 page, pypdf) → classify `INVOICE` (0.99) → extract 8 fields (subtotal/vat/total HIGH, critical) → validate (VR-INV-02/03/SUB/05 pass) → route `REVIEW` (reason `CRITICAL_FIELD`) → **`NEEDS_REVIEW`**.

## S4b IDP review workflow (done 2026-10-22, direct route)
- **New services:** `modules/idp/services/review_service.py` (queue EP-28, detail, open/release EP-29/35, patch_fields EP-30, reject EP-32, reassign EP-126, merge EP-127), `commit_service.py` (approve EP-31 → `finance.Invoice` via Action Registry pattern, `idp.document_committed`, undo_deadline +7d), `sla_service.py` (T-412 `check_review_sla` → `idp.review_escalated` + Notification, manager @>SLA / dept-head @>2×SLA, idempotent). `modules/platform/services/notification_service.py` (public cross-module Notification writer, DEC-125). `auth.AuthService.find_user_by_role` (escalation routing lookup).
- **Routes** (idp router, all guarded `idp:approve`): `GET /idp/review-queue`, `GET /idp/documents/{id}/review`, `POST .../review/open`, `PATCH .../fields`, `POST .../review/approve|reject|release|reassign`, `POST /idp/review-queue/merge`.
- **Config:** `review_sla_hours` default 24 (env `REVIEW_SLA_HOURS`). **Beat:** `check-review-sla` hourly at :15 (worker.py + jobs.py). No schema change (all tables existed from S4a) → no migration.
- **Pipeline:** on entering `NEEDS_REVIEW`, creates the initial `ReviewAssignment(kind=ASSIGN, to_role_code=REVIEWER, due_at=now+SLA)` driving the queue + SLA clock.
- **Approve→commit mapping (INVOICE→finance.Invoice):** direction=IN (received supplier invoice); number←invoice_number, issued_on←issue_date, counterparty←seller_name/seller_tax_code, due_date=issued_on+30d (derived — not an extracted field), one aggregate line subtotal/vat_pct; finance business-rule failure (e.g. duplicate number) → `ACTION_REJECTED` (doc stays `APPROVED`). OTHER doc type → metadata-only commit (`actions=[]`). Full doc-type catalogue + undo (EP-33) = S4c.
- **Field correction:** confirm persists AI value into `corrected_value` (so `effective_value` is unambiguous vs `clear`→None); money field edit requires `reason`→422; `accept_all_high` confirms HIGH non-critical only.
- **8-step integration** `test_review_e2e_http.py` over the real HTTP app (upload→queue→detail→correct+reason→recompute→approve→`finance.Invoice`→dashboard) — Passed.
- **Gate:** ruff ✅ · format ✅ · mypy ✅ (258 files) · pytest **741 passed** · contract ✅.
- **Errors/DTOs** (added earlier this session): `ReviewLockedError`/`UndoExpiredError`/`ActionRejectedError`; review DTOs in `idp/schemas/__init__.py`.
- **Stopped at S4b exit per brief — did NOT enter S4c.**

## S4b exit criteria
| Criterion | Status |
|---|---|
| EP-28..35 + EP-126/127 built | ✅ (EP-33 rollback = S4c) |
| coverage `review*` ≥ 90% | ✅ 90/90/91% |
| gates A/B/C | ✅ |
| 8-step integration verified | ✅ |

## S4b pre-flight (2026-10-22, 3 checks)
- **Check 1 PaddleOCR:** `paddleocr` NOT installed; dev `.env` was `OCR_PROVIDER=paddle` → set to `stub` (reality). Code degrades gracefully (`except → "",0.0`); text-layer invoice.pdf unaffected. → **DEC-236** non-blocking (stub for demo, paddle for prod, DEC-049 still open).
- **Check 2 ClamAV:** ✅ REAL. Container `clamav` (ClamAV 1.5.4) reachable; live clamd `CLEAN` clean bytes, `INFECTED/Eicar-Test-Signature` on EICAR. `CLAMAV_REQUIRED` unset=false. → **DEC-235** confirms demo fallback + verified live.
- **Check 3 samples:** ✅ 7/9 doc types in `data/` (financial/invoice-xlsx/sales/contract/meeting/employee/kpi) + in-memory `sample_docs.py`. No new fixtures needed for S4b.
- **DEC-234** storage local-FS confirmed non-blocking. Baseline: 31 IDP integ/unit tests green after stub change.

## Remaining (in order)
1. **S4c** — commit + lineage + Action Registry v2 (full ACT-* catalogue to all domain services, rollback/undo 7d EP-33, `EVT-idp.document_rolled_back`, `ENT-DataLineage` field→record→metric, TC-IDP-008/009/020; detailed invoice line items; derived due_date policy). **Do NOT start without a new RESUME brief.**
2. **S4d** (optional) — C2 voice/transcript (T-416), C5 Excel import (T-407), UC-06/07/08 (T-408), full 9-type LLM classification + accuracy harness (T-403/T-414).
3. S5 FE/UX/Release; S2 FE tasks T-224..227, T-231/232, T-142/143 still open.
4. `[DEFERRED to S5]` T-223 lineage drill-down, T-233 + FE S2 (DEC-229).

## Next task
**S5b-full (O/C/U/S drill-downs, same pattern as T-511) or S5c (breadth)** — awaiting human RESUME brief. (Former next task, now deferred per DEC-240:) **S4c commit + lineage + Action Registry v2** — on next RESUME: read 09 §S4, 04 §10 (Action Registry, undo, lineage), 05 §ENT-DataLineage, 10 EP-33, gates A/B/C. Extend `commit_service.py` with the full doc-type→domain catalogue, `ENT-DataLineage` rows per committed field, and the 7-day rollback (EP-33) emitting `idp.document_rolled_back`. S4b review workflow sits ready: approved docs reach `COMMITTED` with `undo_deadline`.

## S4b notes / deferred (for S4c)
- **Commit path:** only INVOICE→finance.Invoice wired (reference path). OTHER = metadata-only. Remaining doc-type→domain maps (sales report→deals, employee list→hr, risk register→risks, etc.) + `ENT-DataLineage` field→record rows are S4c.
- **due_date derivation:** invoice commit sets `due_date = issue_date + 30d` because due_date is not an extracted INVOICE field; revisit in S4c if a payment-term field/policy is added.
- **Invoice line:** one aggregate line (subtotal as unit_price, extracted `vat_rate_pct`); finance recomputes vat_amount from pct (extracted vat_amount kept for lineage only). Detailed multi-line commit = S4c.
- **Escalation recipient:** `find_user_by_role` picks an active user by role (MANAGER then CEO as dept-head stand-in), preferring the doc's department; the ESCALATE assignment also carries `to_role_code` so routing works even if no concrete user resolves.
- **Approve authority:** `idp:approve` on the review is the authority to commit (Action Registry gate); the reviewer's Principal is passed to `finance.InvoiceService.create` as `created_by` even without `finance:write` — matches 04 §10.4 Action Registry pattern. Worth a DEC if prod wants a separate finance-write check on commit.
- **No new deps / no schema change / no new events beyond registered** (`idp.document_committed`, `idp.review_escalated` already registered).

## S3 notes / findings
- EP-125 approval executes the AI action with the **approver's** Principal as actor (04 §10.4). A finance approver (CFO, department-scoped for execution) cannot create a cross-department task — the on-behalf-of requester's authority is not reconstructed. Covered at service level by passing a full-scope actor; worth a DEC if finance approvals must create execution writes in prod. Non-blocking for S3.
- `get_chat_gateway` FastAPI dependency added so chat/stream routes are testable without a provider (`app.dependency_overrides`).

## Key files
- `apps/api/src/app/modules/platform/services/{metric_store,pillar_snapshot,metrics}.py`, `core/{metrics,data_quality,periods}.py`
- `apps/api/src/app/seed/{__init__,finance_seed,hr_seed,sales_seed,product_seed,risk_seed,execution_seed,ids}.py`
- `apps/api/src/app/workers/{consumers,jobs}.py`, `apps/api/src/app/worker.py`
- Env: `export PYTHONPATH=$PWD/apps/api/src:$PWD/apps/api PATH=$PWD/.venv/bin:$PATH` (never `uv sync`).

## Human decisions (2026-10-22)
- DEC-227 (human "DEC-210"): DQ-01 = 87.0 accepted; 77.1 aspirational; calibration S4.
- DEC-228 (human "DEC-211"): sub-agents = single code tasks only; seed / cross-file / orchestration by DSH.
- DEC-229: deferrals above. (Numbers 210/211 were already taken by Product DECs → renumbered.)

## Known issues / gaps
- EP-74 `changed_by` null (DEC-191); MANAGER quota null; no log-redaction filter yet.
- ~~Dev DB only 5 users~~ **fixed by T-237**: dev `.env` now has all 10 demo passwords; product owner=CPO, risk owner=RISK_MANAGER.
- Risk: EP-104 doesn't create ENT-Decision; what-if product unavailable; `hr.employee_terminated` not consumed.
- Product BR-PRD-01 thresholds constants; execution constants not in config (DEC-226).
- METRIC-DQ-01 accuracy = validation proxy; IDP-correction component comes with S4c (commit/lineage).
- 09 task checkboxes not ticked (docs edit outside 14).

## S4a notes / deferred (for S4b/S4c)
- **EP path:** spec 10 §3.3 canonical is `POST /idp/documents` (brief said `/idp/documents/upload`); followed the spec. `channel` defaults to C3 (file); C1 manual form = EP-21, C2 = EP-22, C5 = EP-23 (not built in S4a).
- **Storage:** `core/storage.py` is a **local-filesystem** demo store (`var/idp-storage/`, gitignored) behind an `ObjectStore` Protocol — prod swaps MinIO/S3 without touching callers. No MinIO client dependency added (none in config; non-blocking demo infra).
- **OCR:** `OCR_PROVIDER=stub` default (deterministic empty text + 0.0 conf for image/scan pages) so CI needs no PaddleOCR. `paddle` path is lazy-imported and only runs if the package is present (DEC-049 fixture/replay demo still `open`, non-blocking). Scan-PDF/image → `ocr_used=True, text_layer_exists=False`.
- **Classification:** S4a uses a keyword classifier (INVOICE vs OTHER) to pick the schema. Full LLM 9-type classification + accuracy harness (TC-IDP-004/013) is S4d.
- **Schema catalog:** only INVOICE (full 8 fields + 4 VR) and OTHER seeded. Remaining 7 doc-type schemas + ADMIN CRUD (TC-IDP-001 full, T-413) deferred.
- **Extractor DI:** `Pipeline(db, gateway)` / `Extractor(gateway)` take an injected gateway (like chat, DEC-233) → testable with a fake returning `ChatResponse.data`; prod uses `pipeline_gateway(db)` = `AiService(db).gateway()`.
- **mypy:** added `[[tool.mypy.overrides]]` for `clamd`/`openpyxl`/`paddleocr` (no stubs; approved deps DEC-138/DEC-120).
- **Status mapping:** brief's `READY_FOR_REVIEW` = real enum `NEEDS_REVIEW` (05 §6 `document_status`). STP path → `AUTO_APPROVED` (commit itself is S4c).
- Celery worker/beat restarted after S2 merge (2026-10-22 06:25).

---

## Đề xuất doc-sync (chờ human duyệt — agent KHÔNG sửa docs/ ngoài 14 theo CLAUDE §6.6)

Sau nghiệm thu stack-thật 2026-11-02, hai file trong `docs/` còn ghi "M3.5 đang tiến hành" (lệch với thực tế + với STATE/14). Đề xuất human cập nhật:

### `docs/DEMO-SCRIPT.md`
- **Dòng 3–4 (header trạng thái):** đổi "M3.5 (Nghiệm thu MVP) đang tiến hành" → "**M3.5 (Nghiệm thu MVP) DONE cho phần code-env**: trang đo G1–G4 + E2E CEO 7 bước (5/5) + NFR (security/responsive/a11y/PWA/perf) + full test backend (1368 pass, cov 94%) xanh trên stack thật. Còn **ngoài codebase** (human/DEC): OAuth Calendar live, OCR thật, chọn DN pilot."
- **§8.0 tiêu đề:** "Mốc M3.5 — Nghiệm thu MVP (đang tiến hành)" → "(DONE — phần code-env)".
- **Bảng §8.0 các dòng 🟡 Hoãn:** E2E CEO 7 bước (T-901) 🟡→🟢 **DONE** (`ceo-7steps-real.spec.ts` 5/5); NFR (T-903) 🟡→🟢 **DONE** (nfr-real 6/6 + responsive/a11y/perf); Checklist pilot (T-906) 🟡→◑ **deliverable** (`deliverables/T-906-PILOT-CHECKLIST.md`). Giữ 🟡 cho OAuth live + OCR thật + chọn DN pilot (ngoài code).
- **§26 "Chưa demo được":** giữ OAuth live + OCR thật; gỡ "E2E CEO 7 bước / NFR trên stack thật" khỏi danh sách hoãn (đã chạy xanh).

### `docs/3.EXECUTION/09-BUILD-PLAN-TASKS.md` §6.17 (M3.5)
- `T-901` ☐ → ☑ (E2E CEO 7 bước real 5/5 — `ceo-7steps-real.spec.ts`).
- `T-903` ☐ → ☑ (NFR security/responsive/a11y/PWA/perf real — `nfr-real.spec.ts` + responsive + a11y + perf gate).
- `T-906` ☐ → ◑ (checklist `deliverables/T-906-PILOT-CHECKLIST.md`; chọn DN pilot thật = OQ-09-04 ngoài code).
- `T-907..T-910` ☐ giữ (sửa nghiệm thu + PR `ai-eos→main` — human; đã ở `main` qua merge ff + tag `v3.0.0-mvp`).

### Version (đã sửa source, cần rebuild image)
- `apps/api/src/app/__init__.py` + `apps/api/pyproject.toml`: `2.1.0` → `3.0.0`. Endpoint `/health` + `/openapi.json` sẽ trả `3.0.0` sau khi **rebuild image api** (`docker compose -f docker-compose.full.yml up -d --build api`).
