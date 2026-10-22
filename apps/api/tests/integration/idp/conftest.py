"""Fixtures for IDP integration tests: a temp object store so uploads never touch the repo.

`idp_store` also hides review-queue documents already in the dev DB (e.g. the demo invoice that
`scripts/demo_reset.sh` leaves in NEEDS_REVIEW, T-517) by soft-deleting them inside the test's
outer transaction — rolled back afterwards, so the dev/demo data is untouched.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import UTC, datetime
from pathlib import Path

import pytest
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.fixture
async def idp_store(tmp_path: Path, db_session: AsyncSession) -> AsyncIterator[None]:
    import app.core.storage as storage
    from app.modules.idp.models import SourceDocument

    await db_session.execute(
        update(SourceDocument)
        .where(SourceDocument.deleted_at.is_(None))
        .values(deleted_at=datetime.now(UTC))
    )
    await db_session.flush()
    prev = storage._store
    storage._store = storage.LocalObjectStore(root=tmp_path)
    try:
        yield
    finally:
        storage._store = prev
