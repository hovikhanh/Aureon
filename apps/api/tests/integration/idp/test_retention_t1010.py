"""T-1010 / T-1011 — IDP retention: purge C5 `import_rows`, sweep orphan storage.

`05` §2.7 + OQ-05-11: once a C5 batch is finished **and** its document's 7-day undo window has
closed, the preview/error rows are dead weight — they are hard-deleted while
`extracted_fields` (the lineage source) stay. Rows of a batch still inside its undo window, or
of a batch still `open`/`processing`, must survive. The orphan sweep is the code form of
`docs/handover/IDP_Operations.md` §5.1: files with no `source_documents` row are reported, and
only deleted when asked (`IDP_ORPHAN_SWEEP_DELETE`), never for files younger than the undo
window.
"""

import os
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import select

from app.core.storage import LocalObjectStore
from app.modules.idp.models import ImportBatch, ImportRow, SourceDocument
from app.modules.idp.services.retention_service import purge_import_rows, sweep_orphan_storage
from app.modules.platform.models import AuditLog

pytestmark = pytest.mark.integration

NOW = datetime.now(UTC)


async def _batch(
    db: Any, *, status: str, undo_deadline: datetime | None, rows: int = 3
) -> ImportBatch:
    doc = SourceDocument(
        channel="C5", kind="FILE", original_filename="import.xlsx",
        mime_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        storage_key=f"documents/{uuid.uuid4()}", scan_status="CLEAN", pillars=[],
        status="COMMITTED", sensitivity_level=2, source="IDP", data_classification="INTERNAL",
        submitted_by=uuid.uuid4(), submitted_at=NOW, undo_deadline=undo_deadline, page_count=1,
    )  # fmt: skip
    db.add(doc)
    await db.flush()
    batch = ImportBatch(
        kind="excel_import", submitted_by=doc.submitted_by, status=status, header_row=1,
        source_document_id=doc.id, rows_total=rows, rows_valid=rows, rows_invalid=0,
    )  # fmt: skip
    db.add(batch)
    await db.flush()
    for n in range(1, rows + 1):
        row = ImportRow(
            import_batch_id=batch.id, row_number=n, raw={"col": n}, values={"col": n},
            errors=[], status="valid",
        )  # fmt: skip
        db.add(row)
    await db.flush()
    return batch


async def _row_count(db: Any, batch: ImportBatch) -> int:
    rows = (
        await db.execute(select(ImportRow.id).where(ImportRow.import_batch_id == batch.id))
    ).scalars()
    return len(list(rows))


async def test_purge_drops_only_rows_past_the_undo_window(db_session: Any) -> None:
    """TC-M4-05 — expired + finished → purged; fresh or unfinished → kept."""
    expired = await _batch(db_session, status="completed", undo_deadline=NOW - timedelta(days=1))
    fresh = await _batch(db_session, status="completed", undo_deadline=NOW + timedelta(days=6))
    running = await _batch(db_session, status="processing", undo_deadline=NOW - timedelta(days=9))
    no_deadline = await _batch(db_session, status="completed", undo_deadline=None)

    out = await purge_import_rows(db_session)

    assert out == {"batches": 1, "rows": 3}
    assert await _row_count(db_session, expired) == 0
    assert await _row_count(db_session, fresh) == 3
    assert await _row_count(db_session, running) == 3
    assert await _row_count(db_session, no_deadline) == 3
    # the batch row itself is kept: it is the import's log entry (05 §2.1)
    assert (
        await db_session.execute(select(ImportBatch.id).where(ImportBatch.id == expired.id))
    ).scalar_one() == expired.id


async def test_purge_is_idempotent_and_audited(db_session: Any) -> None:
    """TC-M4-06 — a second run is a no-op; the first writes one audit row with the counters."""
    await _batch(db_session, status="completed", undo_deadline=NOW - timedelta(days=2), rows=2)

    first = await purge_import_rows(db_session)
    second = await purge_import_rows(db_session)

    assert first == {"batches": 1, "rows": 2}
    assert second == {"batches": 0, "rows": 0}
    audits = (
        (
            await db_session.execute(
                select(AuditLog).where(AuditLog.action == "idp.purge_import_rows")
            )
        )
        .scalars()
        .all()
    )
    assert len(audits) == 1
    assert audits[0].metadata_["rows"] == 2


async def test_purge_dry_run_reports_without_deleting(db_session: Any) -> None:
    """TC-M4-07 — `dry_run` answers "what would go" and leaves the rows in place."""
    batch = await _batch(db_session, status="completed", undo_deadline=NOW - timedelta(days=3))

    out = await purge_import_rows(db_session, dry_run=True)

    assert out == {"batches": 1, "rows": 3}
    assert await _row_count(db_session, batch) == 3


async def test_orphan_sweep_reports_unreferenced_files(db_session: Any, tmp_path: Path) -> None:
    """TC-M4-08 — a file with no document row is an orphan; a referenced one never is."""
    store = LocalObjectStore(root=tmp_path)
    bucket = tmp_path / "documents"
    bucket.mkdir()
    orphan = bucket / str(uuid.uuid4())
    orphan.write_bytes(b"left over")
    old = NOW - timedelta(days=30)
    os.utime(orphan, (old.timestamp(), old.timestamp()))
    batch = await _batch(db_session, status="completed", undo_deadline=NOW)
    referenced_key = (
        await db_session.execute(
            select(SourceDocument.storage_key).where(SourceDocument.id == batch.source_document_id)
        )
    ).scalar_one()
    referenced = bucket / referenced_key.split("/", 1)[1]
    referenced.write_bytes(b"real document")
    os.utime(referenced, (old.timestamp(), old.timestamp()))

    out = await sweep_orphan_storage(db_session, store=store, delete_files=False)

    assert out["scanned"] == 2
    assert out["orphans"] == 1
    assert out["deleted"] == 0
    assert out["keys"] == [f"documents/{orphan.name}"]
    assert orphan.is_file() and referenced.is_file()


async def test_orphan_sweep_skips_fresh_files_and_deletes_when_asked(
    db_session: Any, tmp_path: Path
) -> None:
    """TC-M4-09 — a file inside the undo window is never swept; `delete_files` removes the rest."""
    store = LocalObjectStore(root=tmp_path)
    bucket = tmp_path / "documents"
    bucket.mkdir()
    fresh = bucket / str(uuid.uuid4())
    fresh.write_bytes(b"just uploaded")
    stale = bucket / str(uuid.uuid4())
    stale.write_bytes(b"orphan")
    old = (NOW - timedelta(days=10)).timestamp()
    os.utime(stale, (old, old))

    out = await sweep_orphan_storage(db_session, store=store, delete_files=True)

    assert out["orphans"] == 1
    assert out["deleted"] == 1
    assert fresh.is_file()
    assert not stale.exists()
    assert store.delete(f"documents/{stale.name}") is False  # idempotent
