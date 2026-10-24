"""Seed the 6 P0 AI agents (R-DEC-71, 05 §2.8, TC-M16-05) — idempotent upsert by `code`.

A row never edited through EP-AI-17 (`version == 1`) is refreshed to the catalog (so tools
registered later — T-645 — reach the seed); an admin-edited row is left untouched.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.ai.models import AgentProfile
from app.modules.ai.services.agent_catalog import AGENTS, seed_tools


async def seed_agents(session: AsyncSession) -> dict[str, int]:
    out = {"created": 0, "updated": 0, "unchanged": 0}
    for spec in AGENTS:
        values = {
            "agent_ref": spec.agent_ref, "name_vi": spec.name_vi, "name_en": spec.name_en,
            "description_vi": spec.description_vi, "description_en": spec.description_en,
            "model_task": spec.model_task, "allowed_tools": seed_tools(spec),
        }  # fmt: skip
        row = (
            await session.execute(select(AgentProfile).where(AgentProfile.code == spec.code))
        ).scalar_one_or_none()
        if row is None:
            session.add(AgentProfile(code=spec.code, max_autonomy_level="L2", is_enabled=True,
                                     **values))  # fmt: skip
            out["created"] += 1
            continue
        changed = [k for k, v in values.items() if getattr(row, k) != v]
        if row.version != 1 or not changed:
            out["unchanged"] += 1
            continue
        for k in changed:
            setattr(row, k, values[k])
        out["updated"] += 1
    await session.flush()
    return out
