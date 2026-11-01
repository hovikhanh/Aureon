"""Shared fixtures for the AI integration tests.

The system default is `AI_AUTONOMY_CEILING=L3` (M3.2, R-DEC-126 — flipped from the M1 L2). Most
seeded agents keep `max_autonomy_level=L2` (`ai_seed`), but the **`ceo` agent is now seeded L3**
(R-DEC-127) — so the default `ceo` chat agent auto-executes a seed-L3 action (e.g. ACT-create_task
→ L3 executed with 24h undo) rather than drafting an L2 card. Only agents left at L2 cap their
seed-L3 defaults to an **L2** proposed card by default.

`ceiling_l3` (R-DEC-72/78/126): the M3.2 config — ceiling L3 **and** all agents raised to L3
inside the rolled-back test transaction, so a v2.1 L3 auto-execute path can actually reach L3.

`ceiling_l2` (R-DEC-126/127): pins the historical M1 L2-ceiling **behaviour** — ceiling L2 and
**all** agents forced to L2 (including `ceo`) — for tests that assert the L2-ceiling capping logic
or the L2 proposed-card UX itself (still valid and reachable via config). Both are rolled back;
`get_config` is cache-cleared around every test (root conftest).
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


@pytest.fixture
async def ceiling_l2(
    monkeypatch: pytest.MonkeyPatch, db_session: AsyncSession
) -> AsyncIterator[None]:
    """Pin the M1 L2 ceiling (R-DEC-126): since the default is now L3, a test that asserts the
    L2-ceiling capping logic must set it explicitly. Agents stay at the seeded `max=L2`."""
    from app.core.config import get_config
    from app.modules.ai.models import AgentProfile

    monkeypatch.setenv("AI_AUTONOMY_CEILING", "L2")
    get_config.cache_clear()
    await db_session.execute(update(AgentProfile).values(max_autonomy_level="L2"))
    await db_session.flush()
    yield
    get_config.cache_clear()
