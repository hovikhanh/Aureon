"""E2E support (T-507/T-508): put one INVOICE document into NEEDS_REVIEW on the dev DB.

Mirrors `apps/api/tests/integration/idp/test_review_e2e_http.py` step 1: real UploadService +
Pipeline, with a fixture gateway (no live LLM — CLAUDE §6.6 #7). Dev DB only; fake demo data.
Prints `{"document_id": ..., "invoice_number": ...}` as the last stdout line.

Run: PYTHONPATH=apps/api/src:apps/api .venv/bin/python apps/web/e2e/support/seed_review_doc.py
"""

from __future__ import annotations

import asyncio
import json
import time
import uuid
from typing import Any

from app.core.config import get_config
from app.core.db import get_sessionmaker
from app.core.deps import Principal
from app.core.model_gateway import ChatResponse
from app.modules.auth.permission_matrix import ROLE_PERMISSIONS
from app.modules.idp.services.pipeline import Pipeline
from app.modules.idp.services.upload_service import UploadFile, UploadService
from tests.integration.idp.sample_docs import _pdf_with_text


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


async def main() -> None:
    get_config()
    number = f"E2E{int(time.time() * 1000) % 10_000_000_000:010d}"
    text = (
        "HOA DON GIA TRI GIA TANG\n"
        f"So hoa don: {number}\nNgay: 2026-09-15\n"
        "Nguoi ban: Cong ty Van phong Pham Sai Gon - MST: 0301234567\n"
        "Tien hang: 10000000\nThue suat: 10%\nTien thue: 1000000\nTong cong: 11000000\n"
    )
    data = _pdf_with_text(text)
    user = Principal(user_id=uuid.uuid4(), role="REVIEWER", permissions=frozenset(ROLE_PERMISSIONS["REVIEWER"]))
    async with get_sessionmaker()() as db:
        f = UploadFile(filename=f"hoa-don-{number}.pdf", content_type="application/pdf", chunks=iter([data]))
        res = await UploadService(db).upload(user, [f])
        doc_id = res.document_ids[0]
        outcome = await Pipeline(db, _FixtureInvoiceGateway(number)).run(doc_id)
        await db.commit()
    print(json.dumps({"document_id": str(doc_id), "invoice_number": number, "status": outcome.status}))


if __name__ == "__main__":
    asyncio.run(main())
