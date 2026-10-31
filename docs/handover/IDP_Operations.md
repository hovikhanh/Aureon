# IDP Operations

> Operational runbook for the Data Inbox / IDP feature: how to run it, configure it, verify it, and
> safely clean up documents. Written against the running Docker stack (2026-10-26). Companion:
> `Data_Inbox_MVP_Workflow.md`, `IDP_Extraction_Schema.md`, `IDP_Sample_Data.md`.

## 1. Running stack (Docker)

| Service | Container | Port (host) | Role |
|---|---|---|---|
| Web (Next.js) | `aureon-web-1` | 3000 | UI, incl. `/data` inbox |
| API (FastAPI) | `aureon-api-1` | 4000 | REST, `/idp/*` endpoints |
| Celery worker | `aureon-celery-worker-1` | — | runs the IDP pipeline + outbox relay |
| Celery beat | `aureon-celery-beat-1` | — | schedules (exactly 1 instance) |
| PostgreSQL 16 | `aureon-postgres-1` | 5432 | `idp` + 10 other schemas |
| Redis | `aureon-redis-1` | 6379 | Celery broker / result |
| MinIO | `aureon-minio-1` | 9000 / 9001 | object storage (prod path) |
| (local LLM, ClamAV, Mailpit) | — | — | optional / dev support |

Bring the pipeline services up after a code change (API + workers must share the image):

```bash
docker compose -f docker-compose.full.yml build api
docker compose -f docker-compose.full.yml up -d --no-deps api celery-worker celery-beat
```

## 2. Relevant configuration (`.env`)

| Variable | Current (demo) | Effect |
|---|---|---|
| `MODEL_GATEWAY_MODE` | `live` | `live` calls the configured provider chain; `fixture` replays saved fixtures (default for tests/CI); `record` saves masked fixtures |
| `OCR_PROVIDER` | `stub` | `stub` returns empty text + conf 0 (no fabrication); `paddle` runs PaddleOCR in-process |
| `CLAMAV_REQUIRED` | `false` | when false, malware scan is best-effort in demo |
| IDP storage dir | `/app/var/idp-storage` (container) = `var/idp-storage` (host) | `LocalObjectStore` root; `storage_key = <bucket>/<uuid4>`, default bucket `documents` |

> The product-runtime model routing (`MODEL_*`, ModelGateway) is **separate** from the build-agent
> routing. Do not cross the two. Extraction in `live` mode goes through the provider chain
> (`omniroute` → …) and is logged to `ai.model_call_logs`.

## 3. Verifying the pipeline end-to-end

```bash
# 1. upload a known-good invoice (see IDP_Sample_Data.md §5 for the login snippet)
#    → returns {"data":{"document_ids":[...],"job_ids":[...]}} with HTTP 202

# 2. watch status transition (UPLOADED → NEEDS_REVIEW | AUTO_APPROVED | FAILED | DUPLICATE)
docker exec aureon-postgres-1 psql -U aureon -d aureon -c \
  "SELECT original_filename, status, channel FROM idp.source_documents ORDER BY created_at;"

# 3. inspect the extraction result
docker exec aureon-postgres-1 psql -U aureon -d aureon -c "
  SELECT ef.field_name, ef.value, ef.confidence, ef.confidence_band
  FROM idp.extracted_fields ef
  JOIN idp.extraction_jobs j ON j.id = ef.extraction_job_id
  WHERE j.source_document_id = '<DOC_ID>' ORDER BY ef.field_name;"

# 4. confirm the model was really called (live mode)
docker exec aureon-postgres-1 psql -U aureon -d aureon -c "
  SELECT provider, model, status, tokens_in, tokens_out, latency_ms
  FROM ai.model_call_logs WHERE source_document_id = '<DOC_ID>' ORDER BY created_at DESC;"
```

A healthy live INVOICE run shows provider `omniroute`, model `claude-sonnet-5`, `status=ok`,
non-zero tokens, and 8 populated fields at HIGH band.

> **Gotcha:** `Idempotency-Key` on `POST /idp/documents` **must be a UUID**, else the API returns
> `400 BAD_REQUEST`.

## 4. Test gates (DoD)

Run from repo root; all must pass before commit (CLAUDE.md §3.3).

```bash
# Frontend
pnpm lint && pnpm typecheck && pnpm test
pnpm --filter @aureon/web exec playwright test --project=mock -g "Chụp ảnh"   # camera C4 e2e

# Backend (fixture mode)
uv run ruff check . && uv run ruff format --check . && uv run mypy
MODEL_GATEWAY_MODE=fixture uv run pytest apps/api/tests/unit apps/api/tests/integration/idp apps/api/tests/ai_eval
```

Current status after this work: FE Vitest 339 ✓ (incl. `camera.test.ts`), FE lint/typecheck ✓,
camera Playwright ✓; BE ruff/format/mypy ✓, pytest 547 ✓ (unit + idp + ai_eval), incl. the new
`test_extractor_uses_structured_output_for_live_gateway` regression.

## 5. Safe document cleanup

> **Rules:** dry-run first; back up before any delete; never delete `auth.*` audit or
> `ENT-AuditLog` history; delete DB rows in FK-safe order **and** remove the matching storage file;
> verify no dangling references afterwards.

### 5.1 Orphan storage files (file with no DB record)

```bash
# list DB-referenced storage keys vs files on disk; anything on disk not in DB is an orphan
docker exec aureon-postgres-1 psql -U aureon -d aureon -t -A -c \
  "SELECT split_part(storage_key,'/',2) FROM idp.source_documents;"
docker exec aureon-api-1 ls /app/var/idp-storage/documents/
# back up, then remove each confirmed orphan
docker cp "aureon-api-1:/app/var/idp-storage/documents/<KEY>" "var/cleanup-backup-<date>/<KEY>"
docker exec aureon-api-1 rm -f "/app/var/idp-storage/documents/<KEY>"
```

### 5.2 A document (record + file), FK-safe

`idp.source_documents` is referenced by: `extracted_fields` (via `extraction_jobs`),
`extraction_reviews`, `document_actions`, `review_assignments`, `document_pages`,
`extraction_jobs`, and self-FKs `duplicate_of_id` / `parent_id` / `superseded_by_id`. A
`DUPLICATE` document points at its original via `duplicate_of_id`, so **delete the duplicate before
the original**.

```bash
# back up the rows first
docker exec aureon-postgres-1 psql -U aureon -d aureon -t -A -c "
  SELECT json_build_object(
    'source_documents',(SELECT json_agg(row_to_json(s)) FROM idp.source_documents s WHERE id='<ID>'),
    'extraction_jobs', (SELECT json_agg(row_to_json(j)) FROM idp.extraction_jobs j WHERE source_document_id='<ID>'),
    'extracted_fields',(SELECT json_agg(row_to_json(f)) FROM idp.extracted_fields f WHERE extraction_job_id IN (SELECT id FROM idp.extraction_jobs WHERE source_document_id='<ID>'))
  );" > var/cleanup-backup-<date>/<ID>.json

# delete children → parent, in one statement
docker exec aureon-postgres-1 psql -U aureon -d aureon -c "
  DELETE FROM idp.extracted_fields WHERE extraction_job_id IN (SELECT id FROM idp.extraction_jobs WHERE source_document_id='<ID>');
  DELETE FROM idp.extraction_reviews WHERE source_document_id='<ID>';
  DELETE FROM idp.document_actions   WHERE source_document_id='<ID>';
  DELETE FROM idp.review_assignments WHERE source_document_id='<ID>';
  DELETE FROM idp.document_pages     WHERE source_document_id='<ID>';
  DELETE FROM idp.extraction_jobs    WHERE source_document_id='<ID>';
  DELETE FROM idp.source_documents   WHERE id='<ID>';"

# remove the storage file for the deleted doc, then verify no dangling refs
```

### 5.3 Verify integrity

```bash
for f in $(docker exec aureon-postgres-1 psql -U aureon -d aureon -t -A -c \
  "SELECT split_part(storage_key,'/',2) FROM idp.source_documents;"); do
  docker exec aureon-api-1 sh -c "test -f /app/var/idp-storage/documents/$f && echo OK:$f || echo DANGLING:$f"
done
```

Prefer the application's **undo** (7-day window) or review-reject paths over manual SQL whenever the
document is still within its lifecycle — manual deletion is for stale test/orphan artifacts only.

### 5.4 Cleanup performed in this work (2026-10-26)

- Removed 6 orphan storage files (backed up to `var/cleanup-backup-20261026/`).
- Removed two test artifacts (record + file, FK-safe): an E2E invoice (`NEEDS_REVIEW`) and its
  `DUPLICATE` `test.pdf`.
- Removed transient storage files left by duplicate upload attempts during live verification.
- Final state: `idp.source_documents` holds only intended valid docs, every `storage_key` has a
  matching file, no orphan files, no dangling references. Audit history untouched.

## 6. Troubleshooting

| Symptom | Likely cause | Action |
|---|---|---|
| All extracted fields `null`, conf 0, live mode | provider returned text but it wasn't parsed as structured output | ensure the extractor uses the gateway **`extract()`** path (fixed in this work); check `ai.model_call_logs.status` |
| Field `null` for an **image**, `ocr_used=true` | `OCR_PROVIDER=stub` returns no text | set `OCR_PROVIDER=paddle` for real OCR; stub behaviour is the honest default |
| Upload returns `400` "Idempotency-Key must be a UUID" | non-UUID key | send a UUID |
| Re-upload returns `DUPLICATE` | SHA-256 dedup | expected; change the file or delete the original first |
| Document stuck in `UPLOADED` | worker not running / not rebuilt | `docker compose ... up -d celery-worker` after rebuilding the shared image |

## Version

- Draft 0.1 — 2026-10-26. Reflects the running stack and the cleanup performed that day.
