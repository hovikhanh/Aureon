# Audit lỗi GitLeaks trên CI (`secrets (gitleaks)`)

> Ngày: 2026-11-03 · Repo `hovikhanh/Aureon` (**public**) · `origin/main` @ `9f3003a`
> Phạm vi: **chỉ audit + đề xuất**. Chưa sửa file nào trong repo, chưa rewrite history, chưa
> force-push, chưa xóa/rotate gì. Phương án đề xuất đã được **chạy thử ngoài repo** (`var/gitleaks/`,
> gitignored) để chứng minh nó hoạt động.
> Không có giá trị secret nào trong báo cáo này; mọi quét đều dùng `--redact`.

## 1. Kết luận

| Câu hỏi | Trả lời |
|---|---|
| Tái hiện được lỗi CI? | **Có, chính xác**: cùng image `zricethezav/gitleaks:v8.24.3`, cùng lệnh, giới hạn `--log-opts=origin/main` → **418 commits, 7 leaks, exit 1** — khớp run `41573404841`. |
| Có secret thật không? | **Không.** 5 false positive + 2 mật khẩu test giả. Không cần rotate/revoke. |
| Credential thật có từng lọt vào git? | **Không** — `.env`, `.env.local`, `keys/jwt_private.pem`, `secrets/*` chưa từng được commit ở **bất kỳ ref nào**; toàn bộ lịch sử chỉ dính rule `generic-api-key`. |
| Có cần rewrite history? | **Không** (§6). |
| Phương án sửa đã kiểm chứng? | **Có** (chạy thử ngoài repo): 418 commits → **0 leak, exit 0**; mẫu âm chứng minh secret thật vẫn bị bắt (§5). |

## 2. Hiện trạng CI

| Mục | Hiện trạng |
|---|---|
| Workflow | `.github/workflows/ci.yml`, trigger `push`/`pull_request` vào `main`. Job `secrets` chạy `gitleaks git --redact --exit-code 1 .` trên `fetch-depth: 0` |
| Cấu hình gitleaks | **không có `.gitleaks.toml`** (dùng rule mặc định); chỉ có `.gitleaksignore` = 6 fingerprint (DEC-177, 2026-10-21) |
| 6 fingerprint cũ | **không khớp finding nào** với v8.24.3 (quét với file ignore rỗng vẫn ra đúng 7 finding như có ignore) → lỗi thời, vô hại |
| Lịch sử xanh/đỏ | xanh lần cuối **2026-10-21 10:38**; đỏ liên tục từ **2026-10-21 20:05** — 81/92 run gần nhất fail |
| Branch protection `main` | **không có** (`404 Branch not protected`) → PR vẫn merge được khi job đỏ (PR #6 đã merge với CI đỏ) |
| Hệ quả phụ | job `api` có `needs: secrets` → **bị skip ở mọi run đỏ**: ruff/mypy/migrate/pytest/contract backend **chưa chạy trên CI kể từ 21/10**. Job `web` vẫn chạy (xanh) |
| `.gitignore` | chặn `.env`, `.env.*` (trừ `.env.example`), `*.pem`, `*.key`, `secrets/`, `keys/` ✅ |
| File nhạy cảm bị track | không — chỉ `.env.example`, `apps/web/.env.local.example` (placeholder) ✅ |
| `.env.example` | khóa tên `*KEY*/*SECRET*/*PASSWORD*/*TOKEN*` chỉ chứa placeholder `<change-me>`, đường dẫn (`JWT_*_KEY_PATH`), mã `kid`, số giây, tên provider ✅ |

## 3. Bảy findings (đã redact)

Tất cả: rule **`generic-api-key`** (heuristic: từ khóa `key`/`api`/`password`… + phép gán + chuỗi ≥ 10 ký tự, entropy ≥ 3,5). Giá trị chỉ mô tả hình dạng.

| # | File : dòng (cột) | Commit (ngày) | Fingerprint | Nội dung (redact) | Phân loại | Bằng chứng |
|---|---|---|---|---|---|---|
| 1 | `apps/api/src/app/modules/ai/services/acceptance_service.py:85` (14) | `0effd10` (02/11) | `0effd10…:acceptance_service.py:generic-api-key:85` | `threshold_key="acc…"` (23 ký tự, `a-z0-9._`) | **False positive** | giá trị là **i18n key** có thật trong `apps/web/messages/*.json`; trường `threshold_key` thuộc schema `AcceptanceSnapshotOut` (EP-RPT-08) |
| 2 | `…/acceptance_service.py:86` (14) | `0effd10` | `…:86` | `detail_key="acc…"` (20) | **False positive** | như #1 |
| 3 | `…/acceptance_service.py:122` (14) | `0effd10` | `…:122` | `threshold_key="acc…"` (23) | **False positive** | như #1 |
| 4 | `…/acceptance_service.py:123` (14) | `0effd10` | `…:123` | `detail_key="acc…"` (20) | **False positive** | như #1 |
| 5 | `apps/web/src/mocks/onboarding.test.ts:68` (103) | `b8d231c` (24/10) | `b8d231c…:onboarding.test.ts:generic-api-key:68` | object body có `initial_password: "…"` (12 ký tự) | **Test/demo credential** | chỉ xuất hiện trong đúng file test này; Vitest chạy với mock BFF in-memory; **không** trùng giá trị nào trong `.env`/`.env.example` |
| 6 | `apps/api/tests/integration/test_user_admin_t614.py:20` (2) | `8e63057` (23/10) | `8e63057…:test_user_admin_t614.py:generic-api-key:20` | `PASSWORD = "Mat…"` (18, `aA9_`) | **Test/demo credential** | chỉ trong file test này; tạo user trong transaction bị rollback (`db_session`); không trùng `.env`/`.env.example` |
| 7 | `apps/api/tests/integration/finance/test_cash_flow.py:66` (28) | `7caeb29` (21/10) | `7caeb29…:test_cash_flow.py:generic-api-key:66` | `fc = await _recompute(api, fixed_opex_weekly=100 * M, …)` | **False positive** | từ khóa `api` = tên fixture test client, theo sau là dấu `,` → regex coi `fixed_opex_weekly=100` là "secret" |

"Historical secret": **không có** — cả 7 dòng vẫn còn trên `origin/main` và không cái nào là credential.

### 3.1. Ngoài phạm vi CI (quét `--all`, mọi ref local)

21 findings = 7 ở trên + 14 bản sao **cùng các dòng đó** ở commit khác (rebase/checkpoint) + `onboarding.test.ts:87` (`initial_password`, test). Sau phương án §5 còn 7, **toàn bộ nằm ở ref chỉ có local**: `refs/agents/*/checkpoints/*` (checkpoint của agent) và tag local `bak/m16-fe` — `git ls-remote` xác nhận **không có trên GitHub**, CI không quét. Không cần xử lý.

> Minh bạch: trong lúc audit, một lần che giá trị bằng regex bị lọt nên **literal mật khẩu test của #5 hiện đầy đủ trên terminal local** (không vào CI log, không vào báo cáo). Đó là chuỗi giả, đã xác minh không trùng cấu hình thật.

## 4. Root cause

1. **Rule heuristic `generic-api-key` bắt nhầm tên định danh**: biến có chữ `key` (`threshold_key`, `detail_key`) chứa i18n key, và fixture tên `api` đứng trước dấu phẩy. Không có `.gitleaks.toml` để mô tả các mẫu hợp lệ của dự án.
2. **Mật khẩu test viết thẳng dạng literal** trong 2 file test.
3. **Cơ chế ignore duy nhất là fingerprint theo commit** (`.gitleaksignore`) — mỗi lần dòng đó xuất hiện ở commit mới (sửa, rebase, cherry-pick) sinh fingerprint mới → dễ vỡ (cùng dòng `test_cash_flow.py:66` bị bắt ở 4 commit khác nhau trên các ref).
4. **Không có branch protection** trên `main` → các commit trên đi vào `main` qua merge dù job đỏ; lỗi tồn tại ~13 ngày, và kéo theo job `api` bị skip.

## 5. Phương án khắc phục (đã chạy thử, chưa áp dụng)

| Finding | Phương án đề xuất | Vì sao không chọn cách khác |
|---|---|---|
| #1–#4 | Thêm `.gitleaks.toml` (`[extend] useDefault = true`) với **allowlist gắn riêng vào rule `generic-api-key`**, điều kiện **AND**: `paths = ^apps/api/src/app/modules/ai/services/acceptance_service\.py$` **và** dòng khớp toàn bộ `^\s*(?:threshold\|detail)_key="acceptance\.[a-z0-9_.]+",\s*$` | Đổi tên trường = đổi contract EP-RPT-08 (cấm tự đổi); fingerprint = vỡ ở lần sửa file kế tiếp |
| #7 | Cùng cơ chế: path `^apps/api/tests/integration/finance/test_cash_flow\.py$` **và** dòng khớp toàn bộ `^\s*fc = await _recompute\(api, fixed_opex_weekly=\d[\d_]* \* M, payroll_monthly_override=\d[\d_]* \* M\)\s*$` | Regex neo hai đầu → token thật đặt trên dòng đó không lọt |
| #5, #6 | (a) **2 fingerprint chính xác** vào `.gitleaksignore` cho commit lịch sử `b8d231c` (`onboarding.test.ts:68`) và `8e63057` (`test_user_admin_t614.py:20`); (b) *khuyến nghị thêm*: 2 test sinh mật khẩu lúc chạy (vd `secrets.token_urlsafe` + hậu tố thỏa policy) để không còn literal mới (dòng `onboarding.test.ts:87` cũng là literal tương tự, hiện chưa bị bắt trên `main`) | Allowlist theo path cho file test = rộng hơn mức cần; lịch sử không đổi được nếu không rewrite nên (a) vẫn cần dù làm (b) |
| CI | **Không sửa workflow**: gitleaks tự nạp `.gitleaks.toml` ở thư mục được quét (`.`) — xác nhận ở run CI đầu tiên sau khi áp dụng | Giữ nguyên job `web`/`api` như yêu cầu |
| Quy trình | (khuyến nghị, việc của chủ repo trên GitHub) bật branch protection `main`: required checks `secrets (gitleaks)`, `web`, `api` | Ngăn tái diễn merge khi đỏ |
| 6 fingerprint cũ | giữ nguyên (vô hại), ghi chú "không khớp với v8.24.3" | Xóa không đổi kết quả; giữ phòng khi đổi version |

### 5.1. Bằng chứng chạy thử (ngoài repo, `var/gitleaks/proto/`)

| Kiểm | Kết quả |
|---|---|
| Lịch sử `origin/main` với config + ignore đề xuất | **418 commits, no leaks found, exit 0** |
| Chỉ config (chưa thêm 2 fingerprint) | còn đúng 2 finding #5, #6 → allowlist không che test credential |
| Mẫu âm (`gitleaks dir`, giá trị giả sinh ngẫu nhiên, không in) — cấu hình **mặc định** | bắt 7/7 dòng mẫu |
| Mẫu âm — cấu hình **đề xuất** | **chỉ bỏ** 2 dòng false-positive thật ở đúng file; **vẫn bắt**: `api_key = "<giả>"` và `threshold_key="<chuỗi ngẫu nhiên>"` trong `acceptance_service.py`, `secret_token = "<giả>"` trong `test_cash_flow.py`, và **chính 2 dòng false-positive đó khi đặt ở file khác** (allowlist đúng phạm vi path) |
| Giới hạn sẵn có của rule mặc định | `_recompute(api, token="<giả>")` không bị rule mặc định bắt (cả trước và sau) — không do allowlist |

## 6. Đánh giá rewrite history (không đề xuất)

Không có secret thật → rewrite **không mang lại lợi ích bảo mật** (các giá trị giả vẫn nằm trong clone/fork/cache công khai), nhưng chi phí lớn: repo **public**, 17 nhánh remote, 6 ref PR, tag `v3.0.0-mvp`, `v1-main-final`; SHA của mọi commit từ 21/10 sẽ đổi → vỡ PR, tag, clone của cộng tác viên, và mọi fingerprint/SHA được ghi trong docs (`STATE.md`, `09`, `13`). **Khuyến nghị: không rewrite, không force-push.**

## 7. Rotate / revoke

**Không cần** — không finding nào là credential thật. (Nếu sau này phát hiện credential thật: dừng, rotate ở provider trước, rồi mới bàn xử lý history.)

## 8. Các file sẽ thay đổi khi áp dụng (chưa thay đổi)

| File | Thay đổi |
|---|---|
| `.gitleaks.toml` (mới) | `[extend] useDefault = true` + 2 allowlist gắn rule `generic-api-key` như §5 |
| `.gitleaksignore` | + 2 fingerprint (#5, #6) kèm chú thích |
| `apps/api/tests/integration/test_user_admin_t614.py`, `apps/web/src/mocks/onboarding.test.ts` | *(tùy chọn 5(b))* sinh mật khẩu lúc chạy thay vì literal |
| `docs/4.GOVERNANCE/13-DECISION-LOG.md` | R-DEC mới cho cấu hình gitleaks (CLAUDE §2.3 xếp gitleaks là mục cần DEC; DEC-177 đã có cho CI) |
| `docs/4.GOVERNANCE/14-TEST-TRACEABILITY.md` | TC cho mẫu âm của allowlist |
| `.github/workflows/ci.yml` | **không đổi** |

## 9. Kết quả sau sửa

| Mục | Trạng thái |
|---|---|
| GitLeaks local sau sửa | ✅ trên bản chạy thử: 418 commits, 0 leak (§5.1) — sẽ chạy lại trên commit thật khi áp dụng |
| CI xác nhận | ☐ **chưa có** — chỉ có sau khi được duyệt áp dụng + push PR. Lưu ý: run xanh đầu tiên cũng là lần đầu job `api` chạy lại sau ~13 ngày, có thể lộ lỗi backend khác trên môi trường CI |

## 10. Cần quyết định

1. Duyệt phương án §5 cho #1–#4, #7 (allowlist gắn rule, path + regex cả dòng)?
2. #5/#6: chỉ fingerprint (a), hay (a) + đổi test sinh mật khẩu lúc chạy (b)?
3. Xác nhận **không** rewrite history.
4. Bật branch protection `main` (thao tác trên GitHub, chủ repo).

## Version

- Draft 0.1 — 2026-11-03. Audit-only.
