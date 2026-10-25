"""E2E support (T-507/T-508): put one INVOICE document into NEEDS_REVIEW on the dev DB.

Mirrors `apps/api/tests/integration/idp/test_review_e2e_http.py` step 1: real UploadService +
Pipeline, with a fixture gateway (no live LLM — CLAUDE §6.6 #7). Dev DB only; fake demo data.
Prints `{"document_id": ..., "invoice_number": ...}` as the last stdout line.

Run: PYTHONPATH=apps/api/src:apps/api .venv/bin/python apps/web/e2e/support/seed_review_doc.py
`--commit` also approves it (EP-31 service, ACT-create_invoice) so the finance lineage has an
IDP-sourced invoice — the v3 seed (T-603b) no longer ships one.
`--cleanup` soft-deletes E2E documents still waiting for review (`hoa-don-E2E*`, NEEDS_REVIEW /
IN_REVIEW) so backend queue tests see a clean dev DB; committed / rejected ones are kept.
"""

from __future__ import annotations

import asyncio
import json
import sys
import time
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select, update
from tests.integration.idp.sample_docs import _pdf_with_text

from app.core.base_model import DEFAULT_TENANT_ID
from app.core.config import get_config
from app.core.db import get_sessionmaker
from app.core.deps import Principal
from app.core.model_gateway import ChatResponse
from app.core.tenant import tenant_scope
from app.modules.auth.permission_matrix import ROLE_PERMISSIONS
from app.modules.auth.repositories import UserRepository
from app.modules.idp.models import ExtractedField, ExtractionJob, SourceDocument
from app.modules.idp.schemas import FieldCorrectionIn, FieldPatchIn
from app.modules.idp.services.commit_service import CommitService
from app.modules.idp.services.pipeline import Pipeline
from app.modules.idp.services.review_service import ReviewService
from app.modules.idp.services.upload_service import UploadFile, UploadService


class _FixtureInvoiceGateway:
    def __init__(self, number: str) -> None:
        self.data: dict[str, Any] = {
            "invoice_number": {"value": number, "raw_text": number, "confidence": 0.98},
            "issue_date": {"value": "2026-09-15", "confidence": 0.95},
            "seller_name": {"value": "Cong ty Van phong Pham Sai Gon", "confidence": 0.72},
            "seller_tax_code": {"value": "0301234567", "confidence": 0.92},
            "subtotal": {"value": 10000000, "confidence": 0.96},
            "vat_rate_pct": {"value": 10, "confidence": 0.95},
            "vat_amount": {"value": 1000000, "confidence": 0.95},
            "total_amount": {"value": 11000000, "confidence": 0.96},
        }

    async def chat(self, req: Any) -> ChatResponse:
        return ChatResponse(content="", provider="fixture", model="e2e", data=self.data)


async def main(*, commit: bool = False) -> None:
    get_config()
    number = f"E2E{int(time.time() * 1000) % 10_000_000_000:010d}"
    text = (
        "HOA DON GIA TRI GIA TANG\n"
        f"So hoa don: {number}\nNgay: 2026-09-15\n"
        "Nguoi ban: Cong ty Van phong Pham Sai Gon - MST: 0301234567\n"
        "Tien hang: 10000000\nThue suat: 10%\nTien thue: 1000000\nTong cong: 11000000\n"
    )
    data = _pdf_with_text(text)
    async with get_sessionmaker()() as db:
        # Upload as the seeded reviewer so the doc is in that reviewer's department queue
        # (EP-28 is department-scoped, 04 §8.2; REV has a department since seed v3, T-603b).
        # `--commit`: the CFO (DIR khối F — idp:approve + finance:write) uploads and approves,
        # so approve commits at once (R-DEC-61: REV lacks finance:write → approve stays APPROVED).
        email, role = ("cfo@abc.demo", "DIR") if commit else ("reviewer@abc.demo", "REV")
        rev = await UserRepository(db).by_email(email)
        if rev is None:
            raise SystemExit(f"{email} missing — run the seed first")
        user = Principal(
            user_id=rev.id,
            role=role,
            permissions=frozenset(ROLE_PERMISSIONS[role]),
            department_id=rev.department_id,
            tenant_id=DEFAULT_TENANT_ID,
        )
        f = UploadFile(
            filename=f"hoa-don-{number}.pdf", content_type="application/pdf", chunks=iter([data])
        )
        res = await UploadService(db).upload(user, [f])
        doc_id = res.document_ids[0]
        outcome = await Pipeline(db, _FixtureInvoiceGateway(number)).run(doc_id)
        await db.commit()
        status = outcome.status
        if commit:  # `--commit`: approve through EP-31's service (Action Registry → finance)
            # FR-DC-16 / R-DEC-69: critical fields must be confirmed one by one before approve
            await _confirm_critical(db, user, doc_id)
            await CommitService(db).approve(user, doc_id, comment="e2e lineage fixture")
            await db.commit()
            status = (await db.get(SourceDocument, doc_id)).status  # type: ignore[union-attr]
    print(json.dumps({"document_id": str(doc_id), "invoice_number": number, "status": status}))


async def _confirm_critical(db: Any, user: Principal, doc_id: uuid.UUID) -> None:
    """EP-29 open + EP-30 `confirm` for every critical field, as a reviewer would."""
    review = ReviewService(db)
    await review.open(user, doc_id)
    ids = (
        (
            await db.execute(
                select(ExtractedField.id)
                .join(ExtractionJob, ExtractionJob.id == ExtractedField.extraction_job_id)
                .where(ExtractionJob.source_document_id == doc_id, ExtractedField.is_critical)
            )
        )
        .scalars()
        .all()
    )
    edits = [FieldCorrectionIn(field_id=i, action="confirm") for i in ids]
    await review.patch_fields(user, doc_id, FieldPatchIn(fields=edits))


async def cleanup() -> None:
    get_config()
    async with get_sessionmaker()() as db:
        res = await db.execute(
            update(SourceDocument)
            .where(
                SourceDocument.original_filename.like("hoa-don-E2E%"),
                SourceDocument.status.in_(("NEEDS_REVIEW", "IN_REVIEW")),
                SourceDocument.deleted_at.is_(None),
            )
            .values(deleted_at=datetime.now(UTC), locked_by=None, locked_until=None)
        )
        await db.commit()
    print(json.dumps({"cleaned": res.rowcount}))  # type: ignore[attr-defined]


if __name__ == "__main__":
    with tenant_scope(DEFAULT_TENANT_ID):  # R-DEC-21: repositories fail closed without tenant
        if "--cleanup" in sys.argv:
            asyncio.run(cleanup())
        else:
            asyncio.run(main(commit="--commit" in sys.argv))
