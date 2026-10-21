"""DEC-205 provider registry: one provider per module; re-importing the same function is fine."""

from datetime import date

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.metrics import MetricReading, ProviderRegistry


async def first(_db: AsyncSession, _d: date) -> list[MetricReading]:
    return []


async def second(_db: AsyncSession, _d: date) -> list[MetricReading]:
    return []


def test_register_same_function_twice_is_idempotent() -> None:
    reg = ProviderRegistry()
    reg.register("x", first)
    reg.register("x", first)  # cold re-import of the module defining it
    assert reg.providers == {"x": first}
    with pytest.raises(ValueError, match="registered twice"):
        reg.register("x", second)
