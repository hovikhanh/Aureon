"""IDP retention & storage hygiene (05 §2.7 note + OQ-05-11; T-1010/T-1011).

Two daily, idempotent sweeps that replace the manual SQL runbook in
`docs/handover/IDP_Operations.md` §5:

* `purge_import_rows` — C5 preview/error rows (`ENT-ImportRow`) are only needed while the user
  can still look at the import or undo it. Once the batch is `completed`/`partially_failed`
  **and** its source document's `undo_deadline` has passed (7 days, DEC-134), the rows are
  hard-deleted. `extracted_fields` stay untouched: they are the lineage source (05 §2.7).
* `sweep_orphan_storage` — a file left in the object store with no `source_documents` row
  (a failed upload, a deleted test artifact). Reporting is always safe; **deletion happens only
  when `IDP_ORPHAN_SWEEP_DELETE=true`** (CLAUDE.md §6.6 rule 9 — a scheduled job does not
  destroy data on its own), and even then only for files older than the undo window, so a file
  whose `source_documents` row is still being written is never touched.

Both write an audit row (`idp.purge_import_rows` / `idp.sweep_orphan_storage`) in the caller's
transaction with the counters, so a retention run is itself auditable.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import record_audit
from app.core.config import get_config
from app.core.storage import ObjectStore, get_object_store
from app.modules.idp.repositories import ImportRepository, SourceDocumentRepository


def _now() -> datetime:
    return datetime.now(UTC)


async def purge_import_rows(db: AsyncSession, *, dry_run: bool = False) -> dict[str, int]:
    """Delete `import_rows` of finished batches whose undo window has closed (05 §2.7).

    Idempotent: a second run finds nothing left to delete. Returns
    `{"batches": n, "rows": m}` — with `dry_run=True` the counts are what *would* go. All SQL
    goes through `ImportRepository` so the tenant filter of layer 1 applies (CLAUDE §4.3).
    """
    repo = ImportRepository(db)
    batch_ids = await repo.batches_past_undo_window(_now())
    row_count = await repo.count_rows_of(batch_ids)
    if not row_count:
        return {"batches": 0, "rows": 0}
    if dry_run:
        return {"batches": len(batch_ids), "rows": row_count}

    await repo.delete_rows_of(batch_ids)
    out = {"batches": len(batch_ids), "rows": row_count}
    await record_audit(
        db,
        action="idp.purge_import_rows",
        target_schema="idp",
        target_table="import_rows",
        metadata={"batches": out["batches"], "rows": out["rows"], "reason": "undo_window_over"},
    )
    return out


async def sweep_orphan_storage(
    db: AsyncSession, *, store: ObjectStore | None = None, delete_files: bool | None = None
) -> dict[str, Any]:
    """Find object-store files with no `source_documents` row (handover §5.1 as code).

    Returns `{"scanned": n, "orphans": m, "deleted": k, "keys": [...]}` (`keys` capped at 50 so
    the audit row and the job log stay small). Deletion is opt-in via
    `IDP_ORPHAN_SWEEP_DELETE`; `delete_files` overrides it for an explicit, human-run sweep.
    """
    cfg = get_config()
    obj = store or get_object_store()
    keys = getattr(obj, "iter_keys", None)
    if keys is None:  # a store without listing (e.g. a test double) — nothing to do
        return {"scanned": 0, "orphans": 0, "deleted": 0, "keys": []}

    cutoff = _now() - timedelta(days=7)  # undo window (DEC-134): never touch a fresh upload
    on_disk = {k: mtime for k, mtime in keys()}
    # includes soft-deleted rows — a rolled-back document keeps its file for lineage
    known = set(await SourceDocumentRepository(db).all_storage_keys())
    orphans = sorted(k for k, mtime in on_disk.items() if k not in known and mtime < cutoff)

    should_delete = cfg.idp_orphan_sweep_delete if delete_files is None else delete_files
    deleted = 0
    if should_delete:
        remove = getattr(obj, "delete", None)
        for key in orphans:
            if remove is not None:
                remove(key)
                deleted += 1
    out: dict[str, Any] = {
        "scanned": len(on_disk),
        "orphans": len(orphans),
        "deleted": deleted,
        "keys": orphans[:50],
    }
    if orphans:
        await record_audit(
            db,
            action="idp.sweep_orphan_storage",
            target_schema="idp",
            target_table="source_documents",
            metadata=out,
        )
    return out
