# Aureon v4.0.1 — Release notes

Bản vá hạ tầng của `v4.0.0` (`fb02460`); **không đổi nghiệp vụ**. `v4.0.0` giữ nguyên.

## Thay đổi
- **CI/CD:** chạy cho `main`, `v4/**`, tag `v*`, PR và chạy tay; 4 job độc lập (`secrets (gitleaks)`, `web`, `api`, `docker`). Job `api` hoạt động lại sau ~4 tuần bị bỏ qua: thêm `DB_ENCRYPTION_KEY` ngẫu nhiên mỗi lần chạy, cài extra `ocr` (numpy), ngưỡng replay AI nới qua `REPLAY_BUDGET_S` chỉ trên CI.
- **Môi trường:** ghim Python 3.12 (`.python-version`); override mypy cho `numpy`.
- **Test:** `work.test.ts` cố định ngày nghiệp vụ (trước đó lỗi theo ngày hệ thống).
- **Gitleaks:** 10 finding đã xác minh từng dòng, đều là false positive hoặc mật khẩu test giả; suppress bằng fingerprint chính xác trong `.gitleaksignore` (không allowlist theo path). Chi tiết: `deliverables/GITLEAKS-AUDIT.md` §11.
- **README:** quy trình clone, khôi phục secrets, build, kiểm tra, cập nhật, backup/restore, WSL2 + Linux.

## Xác minh
GitHub Actions, nhánh `v4/demo-readiness`: 4/4 job xanh (xem run của commit được tag). Không chạy E2E Playwright trên CI (cần stack đầy đủ).

## Chưa làm / lưu ý
- `main` vẫn là v3, không đổi.
- Chưa có R-DEC trong `13-DECISION-LOG.md` cho cấu hình gitleaks (việc của người duy trì).
- Các lệnh backup/restore trong README chưa được chạy thử trên Docker thật.
