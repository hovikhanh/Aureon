# Đề xuất DEC — dependency cho pilot / đo lường (agent proposes, human assigns DEC-xxx)

> CLAUDE §2.3 + §6.3.4 + §6.7: agent **không** tự cài/merge dependency khi chưa có `DEC-xxx` resolved trong `docs/4.GOVERNANCE/13-DECISION-LOG.md`. Dưới đây là **nội dung đề xuất** để human cấp số DEC và tự ghi vào 13. Không có dependency nào được cài trong phiên này.

---

## A. `paddleocr` — OCR provider thật cho pilot (phương án mặc định BRD)

| Trường | Nội dung |
|---|---|
| **Vấn đề** | `OCR_PROVIDER=stub` ở mọi môi trường → ảnh/scan trả text rỗng, confidence 0. Pilot cần OCR thật (C4 ảnh, PDF scan không có text layer). |
| **Đề xuất** | Thêm `paddleocr` làm **optional dependency** (import lazy, đã có nhánh `provider == "paddle"` trong `apps/api/src/app/modules/idp/services/preprocess.py`, mypy đã khai ở `pyproject.toml` ignore-missing-imports). Bật bằng `OCR_PROVIDER=paddle`. |
| **Phạm vi** | Runtime optional group (vd `[project.optional-dependencies] ocr`). Không đổi mã nghiệp vụ (nhánh đã tồn tại từ DEC-049). Không đổi API/schema. |
| **Rủi ro** | Gói nặng (PaddlePaddle). Cô lập trong optional group, chỉ cài ở image pilot. CI/dev giữ `stub`. |
| **Mặc định nếu bác** | Giữ `stub`; không demo được OCR thật — pilot chặn hạng mục 2.3. |
| **Liên quan** | DEC-049 (OCR backend), 07 §OCR, FR-DC-08, R-DEC-98 |
| **Blocking** | Không (pilot-only; dev/CI không cần). |

**Thay thế (B'):** nếu PaddleOCR không đủ chất lượng tiếng Việt → DEC riêng cho **Google Vision adapter** (code mới + `GOOGLE_VISION_*` credentials + provider mới) — lớn hơn, cần DEC provider, không làm trừ khi A không đạt.

---

## B. `@vitest/coverage-v8` — đo coverage frontend (NFR-16 FE ≥ 70%)

| Trường | Nội dung |
|---|---|
| **Vấn đề** | Backlog "Đo coverage frontend — chưa đo vì thiếu dependency/DEC". `pnpm test` (Vitest 424 pass) chạy được nhưng `--coverage` cần provider `v8` chưa cài. Ngưỡng 14 §1.3: FE `features/` + `lib/` ≥ 70%. |
| **Đề xuất** | Thêm `@vitest/coverage-v8` vào `apps/web` **devDependencies** (pin version khớp `vitest` hiện tại). Cấu hình `coverage.provider = 'v8'`, `include` = `src/features/**`, `src/lib/**`; thresholds 70%. |
| **Phạm vi** | Dev-only, không vào bundle runtime. Chỉ thêm script `test:coverage`. Không đổi mã sản phẩm. |
| **Rủi ro** | Rất thấp (dev tool chuẩn của Vitest). |
| **Mặc định nếu bác** | FE coverage vẫn "chưa đo"; dựa vào 424 unit test làm proxy chất lượng. |
| **Liên quan** | CLAUDE §2.3 (dependency chưa DEC), 14 §1.3 (ngưỡng), NFR-16 |
| **Blocking** | Không (đo lường, không chặn chức năng). |

> Sau khi human resolve: `pnpm add -D @vitest/coverage-v8 --filter @aureon/web` rồi `pnpm --filter @aureon/web test -- --coverage`.

---

## C. `@axe-core/playwright` — a11y automation sâu (tùy chọn, NFR WCAG AA)

| Trường | Nội dung |
|---|---|
| **Vấn đề** | a11y hiện kiểm **structural** (landmark/H1/nav/⌘K — `a11y-m2.spec.ts` 5/5). Rule-level sâu (contrast, ARIA, form labels) chưa tự động. STATE/M2 ghi "axe-core tự động hoãn (cần DEC dependency §2.3)". |
| **Đề xuất** | Thêm `@axe-core/playwright` vào `apps/web` **devDependencies**; spec `a11y-axe.spec.ts` chạy `AxeBuilder` trên các SCR chính, fail khi có vi phạm `serious`/`critical`. |
| **Phạm vi** | Dev/test-only (Playwright). Không đổi mã sản phẩm. |
| **Rủi ro** | Thấp; có thể lộ vi phạm a11y cần sửa UI (kỳ vọng — đó là mục tiêu). |
| **Mặc định nếu bác** | Giữ a11y structural; rule-level kiểm thủ công trong pilot. |
| **Liên quan** | 06 §WCAG AA, NFR a11y, §6.7 pilot checklist |
| **Blocking** | Không. |

---

## Tổng kết

| DEC đề xuất | Dependency | Loại | Blocking | Cần cho |
|---|---|---|---|---|
| A | `paddleocr` | runtime optional | Không | Pilot OCR thật (2.3) |
| B | `@vitest/coverage-v8` | dev | Không | Đo coverage FE (6.8) |
| C | `@axe-core/playwright` | dev | Không | a11y automation sâu (6.7) |

*Agent chỉ đề xuất nội dung; số DEC do người duy trì `13-DECISION-LOG.md` cấp (CLAUDE §6.7). Không cài trước khi resolve.*
