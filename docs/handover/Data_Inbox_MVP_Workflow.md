# Data Inbox / IDP — MVP Workflow

> Handover note for the **Data Inbox** (SCR-45, `/data`) and the IDP pipeline behind it, as built
> on Aureon v3 — AI-EOS. Describes the real, running behaviour (verified live against the Docker
> stack on 2026-10-26), not a target design. Companion docs: `IDP_Extraction_Schema.md`,
> `IDP_Sample_Data.md`, `IDP_Operations.md`.

## 1. What the Data Inbox is

`/data` (SCR-45) is the single place a user drops data into the system. It covers the P0 capture
channels and shows the **real backend state** of every document the user is allowed to see — no
mock results. A document moves through classify → extract → validate → review → commit, and every
committed value is written to a downstream business table through the Action Registry.

| Channel | How | Endpoint | Where in UI |
|---|---|---|---|
| **C1** manual form | Type values into a schema form | `POST /idp/data-capture/manual` | "Thêm dữ liệu" → form (SCR-61) |
| **C3** file upload | Drag/drop or browse (PDF, image, Word, Excel, CSV) | `POST /idp/documents` | DropZone |
| **C4** photo capture | **Take a photo with the device camera** | `POST /idp/documents` | DropZone → "Chụp ảnh" |
| **C5** table import | Upload a spreadsheet, map columns, fix rows | `POST /idp/documents` → import flow | DropZone → "Import bảng" |

**C4 = C3 flow (04 §3).** A captured photo is an image `File` added to the same send list as an
uploaded file and posted to the **same** `POST /idp/documents` endpoint. There is **no separate
`channel` form field** — the endpoint accepts only `files[]` and an optional `document_type`;
the channel is decided server-side (default `C3`). Adding a channel field would be a contract
change requiring a DEC, so capture is intentionally contract-compliant without one.

## 2. End-to-end pipeline (what happens after upload/capture)

`EP-DC-01 POST /idp/documents` (permission `idp:write`) streams each file to object storage,
creates a `source_document` row, and enqueues the async pipeline (HTTP `202`). The Celery worker
runs `Pipeline.run`:

```
UPLOADED
  → malware scan (ClamAV; CLAMAV_REQUIRED=false in demo)
  → PREPROCESSING   text layer check → OCR only if no text layer (images always OCR)
  → EXTRACTING      classify doc type → ModelGateway structured extraction per schema
  → VALIDATING      field + cross-field validation rules
  → route:
       AUTO_APPROVED   (STP) — doc conf ≥ 0.95, required fields ≥ 0.90, no critical field, no error
       NEEDS_REVIEW    — anything below STP, OR any critical field present, OR a validation error
     exceptions: FAILED (pipeline error) · DUPLICATE (same SHA-256 as an existing doc)
```

- **Critical fields always force review** (FR-DC-16): invoice amounts/VAT, salary, national ID,
  bank account, date of birth, address. These never auto-commit.
- **No fabrication (BRD-P05):** a field the model cannot find is `null` with confidence `0`. An
  image whose OCR yields no text produces an honest `NEEDS_REVIEW` with empty fields and
  confidence `0` — it never invents values.
- Every LLM call is logged to `ai.model_call_logs` (provider, model, tokens, latency); prompts are
  not stored raw.

### Live verification (2026-10-26)

Uploading `data/DOC-09-hoa-don-gtgt-mau.pdf` as `INVOICE` through the running stack produced a real
`claude-sonnet-5` extraction (via the `omniroute` provider, 1274/437 tokens) with all 8 fields at
HIGH confidence (doc confidence 0.975) and correct routing to `NEEDS_REVIEW` because critical money
fields are present. The image sample `DOC-10-anh-hoa-don-gtgt.png` ran the OCR path
(`ocr_used=true`) and, with `OCR_PROVIDER=stub`, routed to `NEEDS_REVIEW` with empty fields — the
expected honest outcome.

## 3. Review → approve → commit (per department)

1. A document in `NEEDS_REVIEW` appears in the inbox and in the reviewer's queue. Opening it
   (SCR-18b) shows the extracted fields, confidence bands, and the **planned actions**
   (`EP-DC-05 planned_actions`) — the downstream writes that will happen on commit, each tagged
   with the permission it needs.
2. The reviewer corrects fields, confirms critical cells, and **approves** (`idp:approve`).
3. **Commit** runs the Action Registry chain for the document type in **one transaction**, writing
   to the downstream business tables, recording lineage per column, emitting
   `EVT-idp.document_committed`, and setting a **7-day undo deadline** (DEC-134).
4. Commit is **permission-gated per target domain.** Approving does not grant the downstream write:
   e.g. an HR roster needs `hr:write`/`hr:admin` to create employees; an invoice needs
   `finance:write`. A reviewer who lacks the target permission approves, but a user with that
   permission commits (R-DEC-61 pending permissions).

### Document type → department → downstream tables (live)

| Doc type | Pillar | Action chain (in order) | Target module | Commit permission |
|---|---|---|---|---|
| `INVOICE` | F (Finance) | `ACT-create_invoice` | finance | `finance:write` |
| `HR_ROSTER` | O (People) | `ACT-create_department` → `ACT-create_team` → `ACT-create_position` → `ACT-create_employee` | hr | `hr:write` + `hr:admin` (org: admin) |
| `PLAN_KPI_OKR` | F/O/C/U/S | `ACT-upsert_objective` → `ACT-upsert_key_result` → `ACT-upsert_kpi` → `ACT-upsert_kpi_target` → `ACT-create_task` | execution | `execution:write` |
| `PERIOD_REPORT` | F/O/C/U/S | `ACT-record_kpi_measurement` → `ACT-record_kr_checkin` | execution | `execution:write` |
| `OTHER` | — | *(none — metadata only, review-only)* | — | — |

> `OTHER` has no action chain: it commits metadata only and never writes to a business table. This
> is why a report misclassified as `OTHER` is a useful review case rather than a pipeline failure.

## 4. Roles that can act (live RBAC)

| Role | idp:read | idp:write (capture) | idp:approve (review) | Downstream commit perms held |
|---|:--:|:--:|:--:|---|
| CEO | ✔ | ✔ | — | hr:admin, execution:write |
| Director (DIR) | ✔ | ✔ | ✔ | hr:write/admin, finance:write, execution:write |
| Manager (MGR) | ✔ | ✔ | ✔ | finance:write, execution:write |
| Employee (EMP) | ✔ | ✔ | — | execution:write |
| Reviewer (REV) | ✔ | ✔ | ✔ | — (reviews only; cannot self-commit downstream) |
| Admin (ADM) | ✔ | ✔ | — | hr:admin |
| AI Agent | — | — | — | — |

Only **DIR, MGR, REV** hold `idp:approve`. The DropZone and the "Chụp ảnh" button render only when
the user has `idp:write`.

## 5. Camera capture (C4) — UX contract

- The **"Chụp ảnh"** button sits next to "Chọn file" in the DropZone.
- It opens a dialog that requests the device camera via `getUserMedia` (back camera preferred on
  mobile). Camera access requires a **secure context** (HTTPS or `localhost`); otherwise the dialog
  shows an `unsupported` message and tells the user to use "Chọn file" instead — it never silently
  falls back and pretends a file picker is the camera.
- States: live preview → **Chụp** (capture) → review the shot → **Dùng ảnh này** (keep) or
  **Chụp lại** (retake). Multiple photos per session (≤ 20, within the 100-file / 50-MB limits).
- **Xác nhận** adds the captured `.jpg` files to the DropZone send list; **Gửi** then uploads them
  through the normal `/idp/documents` pipeline. Permission denied / no camera / camera-in-use are
  shown as distinct, localized error states with a retry.
- Error/permission handling and the capture rules live in pure, unit-tested logic
  (`apps/web/src/features/capture/camera.ts`); the DOM flow has a Playwright test using a fake media
  device.

## 6. Key source files

| Concern | File |
|---|---|
| Inbox screen (SCR-45) | `apps/web/src/features/capture/InboxView.tsx` |
| Upload + camera entry (C3/C4) | `apps/web/src/features/capture/DropZone.tsx` |
| Camera dialog | `apps/web/src/features/capture/CameraCapture.tsx` |
| Camera pure logic (tested) | `apps/web/src/features/capture/camera.ts` / `camera.test.ts` |
| Upload endpoint (EP-DC-01) | `apps/api/src/app/modules/idp/routes/router.py` |
| Pipeline | `apps/api/src/app/modules/idp/services/pipeline.py` |
| Extraction (structured output) | `apps/api/src/app/modules/idp/services/extractor.py` |
| Commit + Action Registry plan | `apps/api/src/app/modules/idp/services/commit_service.py`, `services/actions/` |

## 7. Notes carried from this work

- **Fixed a live-only extraction bug:** the extractor called `gateway.chat()` and read `resp.data`,
  which is `None` for a live provider (only `gateway.extract()` parses structured JSON output).
  Live uploads therefore extracted every field as `null`. The extractor now uses the gateway's
  structured-output path (`extract()`), verified live, with a regression unit test. Fixture-mode
  tests were green before and after because fakes return `data` directly — the bug was invisible to
  the existing suite.
- The bug fix changed **no** API contract, DB schema, or dependency (`extract()` already exists on
  the gateway), so no DEC was required.

## Version

- Draft 0.1 — 2026-10-26. Author: capture/IDP handover. Reflects the running stack on that date.
