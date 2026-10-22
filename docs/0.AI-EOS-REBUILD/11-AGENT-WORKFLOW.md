# 11 — Agent Workflow (AI-EOS, nhánh `ai-eos`)

> **Nguồn chuẩn:** `_reference/SOURCE-BRD-v1.1.md` §11 (AI Platform); CLAUDE.md §6–§8 (gates, loading matrix, EPCC) — quy tắc vận hành giữ nguyên.
> **Phụ thuộc:** 00–10. **Trạng thái:** 🟡 draft (Phase R3). **Ngày:** 2026-10-22 · **Maintainer:** @CyEyes

---

## 1. Phạm vi

Quy tắc vận hành cho **build-agent** khi làm việc trên bộ tài liệu/code AI-EOS. Quy tắc an toàn/gate của CLAUDE.md (§6 3 gate, §6.3 cấm tự quyết, §10.3 agent chỉ đề xuất version) **vẫn áp dụng nguyên** trên nhánh `ai-eos`.

## 2. EPCC

```text
[1] Context → [2] Gate A/B/C → [3] Plan → [4] Implement → [5] Verify → [6] Update 14 → [7] Commit
                   │ fail
                   └──► BLOCKED
```

## 3. 3 Gate (giữ nguyên CLAUDE.md §6.1)
- **Gate A — Doc Audit** (12): file bắt buộc của task `current`.
- **Gate B — Decision Log** (13): không DEC open+blocking liên quan; dependency có DEC.
- **Gate C — Traceability** (14): task có ≥1 TC-* mapping; coverage đạt ngưỡng.

## 4. Doc Loading Matrix cho 28 domain

Khác `main` (6 domain module). Nạp bộ file theo loại task:

| Task type | Bắt buộc | Optional |
|---|---|---|
| Plan phase/MVP | 00, 01, 09, 13 | 11, 14 |
| Scaffold / hạ tầng | 00, 01, 07, 10 | 05, 13 |
| Code domain (bất kỳ D01–D28) | 00, 01, 03, 05, 10 | 02, 04, 07 §2 |
| Code Data Capture (D03) | 00, 01, 04, 05, 10 | 07, 08 |
| Code AI Platform (D26) | 00, 01, 02, 07, 10 | 03, 04, 05 |
| Code CEO Assistant/Reporting (D27/D28) | 00, 01, 03, 07, 10 | 02, 05 |
| Code auth/security (D02) | 00, 01, 02, 10 | 05, 07 |
| Code UI | 00, 06, 10 | 02, 03 |
| Seed | 00, 01, 08 | 05 |
| Test | 10, 14 | task spec |
| Audit doc | 12 | — |

## 5. Agent runtime (sản phẩm) vs build-agent
- **Build-agent** (bảng §4): agent AI viết code/docs.
- **Agent sản phẩm** (D26, BRD §11.4): CEO/Data Capture/Performance/Task/Meeting/Reporting (P0)… chạy trong Agent Runtime, chọn bởi Orchestrator (07 §2, 10 §4). **Hai loại tách bạch** (nhất quán CLAUDE.md §2.1).

## 6. Verify (giữ nguyên gate DoD)
Lệnh lint/typecheck/test/mypy/pytest/contract exit 0 trước commit; test AI `MODEL_GATEWAY_MODE=fixture`; không skip test. Số liệu tính bằng script.

## 7. Escalation / BLOCKED
Theo CLAUDE.md §6.7/§6.8. Số DEC do human cấp; agent chỉ đề xuất nội dung. Spec mâu thuẫn `docs/` ↔ `_reference/` → ưu tiên `_reference/`, ghi gap vào 13.

## 8. Open questions
- OQ-11-01: Loading matrix — giữ **ma trận gộp theo loại task** như §4 cho đợt docs; việc tách theo 5 lớp domain xem xét lại ở đợt code khi có task breakdown T-* (R-DEC-09).

## Version
- **Version:** 0.2.0 (draft, Phase R3)
- **Last updated:** 2026-10-22
- **Maintainer:** @CyEyes
- **Change 0.2.0:** Chốt Q1–Q6 (R-DEC-05..10) — cập nhật trạng thái quyết định, đóng OQ liên quan; phạm vi docs-first P0.
- **Change 0.1.0:** Viết lại 11 theo AI-EOS — EPCC, 3 gate (giữ CLAUDE.md), loading matrix cho 28 domain, tách build-agent vs agent sản phẩm (D26), verify/escalation giữ nguyên quy tắc an toàn.
