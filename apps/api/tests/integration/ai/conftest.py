"""Shared fixtures for the AI integration tests.

`ceiling_l3` (R-DEC-72/78): M1 runs with `AI_AUTONOMY_CEILING=L2` and every seeded agent at
`max_autonomy_level=L2`, so a v2.1 L3 auto-execute test asserts the **L2** outcome by default
and its L3 variant opts into the M3.2 configuration here — ceiling L3 + agents raised to L3
inside the rolled-back test transaction (not skipped — 14 §1.10). `get_config` is
cache-cleared around every test (root conftest).
"""

from collections.abc import AsyncIterator

import pytest
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.fixture
async def ceiling_l3(
    monkeypatch: pytest.MonkeyPatch, db_session: AsyncSession
) -> AsyncIterator[None]:
    from app.core.config import get_config
    from app.modules.ai.models import AgentProfile

    monkeypatch.setenv("AI_AUTONOMY_CEILING", "L3")
    get_config.cache_clear()
    await db_session.execute(update(AgentProfile).values(max_autonomy_level="L3"))
    await db_session.flush()
    yield
    get_config.cache_clear()
